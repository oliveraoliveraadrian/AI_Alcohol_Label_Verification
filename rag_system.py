import io
import re
import time
import easyocr
import numpy as np
import cv2
from PIL import Image
from thefuzz import fuzz
from typing import List, Dict
from docx import Document as DocxDocument
from PyPDF2 import PdfReader
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing

class RAGSystem:
    FIELD_CONFIG = [
        {"id": "brand", "label": "Brand Name", "keywords": ["brand name"]},
        {"id": "type", "label": "Class/Type", "keywords": ["class/type designation", "class/type"]},
        {"id": "abv", "label": "Alcohol Content", "keywords": ["alcohol content"]},
        {"id": "net_contents", "label": "Net Contents", "keywords": ["net contents"]},
        {"id": "address", "label": "Address", "keywords": ["name and address"]},
        {"id": "origin", "label": "Origin", "keywords": ["country of origin"]},
        {"id": "hws", "label": "Health Warning", "keywords": ["government health warning", "government warning"]}
    ]

    HWS_MASTER_TEXT = (
        "GOVERNMENT WARNING: (1) According to the Surgeon General, women "
        "should not drink alcoholic beverages during pregnancy because of the risk of "
        "birth defects. (2) Consumption of alcoholic beverages impairs your ability to "
        "drive a car or operate machinery, and may cause health problems."
    )

    def __init__(self):
        # Using GPU=False, optimized for batch processing
        self.reader = easyocr.Reader(['en'], gpu=False)
        self.applications = []
        self.max_workers = min(multiprocessing.cpu_count(), 4)  # Limit to 4 workers for stability

    def _preprocess_image(self, pil_img):
        """Preprocess image to handle blurry images and various formats"""
        # Convert to RGB if needed
        if pil_img.mode != 'RGB':
            pil_img = pil_img.convert('RGB')
        
        img_arr = np.array(pil_img)
        
        # Check if image is blurry using Laplacian variance
        gray = cv2.cvtColor(img_arr, cv2.COLOR_RGB2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        # If blurry (variance < 100), apply sharpening
        if laplacian_var < 100:
            kernel = np.array([[-1,-1,-1],
                             [-1, 9,-1],
                             [-1,-1,-1]])
            img_arr = cv2.filter2D(img_arr, -1, kernel)
        
        # Enhance contrast
        lab = cv2.cvtColor(img_arr, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        l = clahe.apply(l)
        img_arr = cv2.cvtColor(cv2.merge([l,a,b]), cv2.COLOR_LAB2RGB)
        
        return img_arr
    
    def _get_ocr_data(self, pil_img):
        """Returns both full text and raw EasyOCR results (with bounding boxes)"""
        img_arr = self._preprocess_image(pil_img)
        results = self.reader.readtext(img_arr, detail=1, paragraph=False)
        full_text = " ".join([res[1] for res in results])
        return full_text, results, img_arr

    def _is_bold(self, img_arr, bbox):
        """
        Analyzes a crop of the image to determine if text is bold.
        Uses Stroke Width analysis via Distance Transform.
        """
        try:
            # bbox is [[x,y], [x,y], [x,y], [x,y]]
            xs = [p[0] for p in bbox]
            ys = [p[1] for p in bbox]
            crop = img_arr[int(min(ys)):int(max(ys)), int(min(xs)):int(max(xs))]
            
            if crop.size == 0: return False
            
            # Pre-processing
            gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
            # Threshold to get binary text (black text on white or vice versa)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            
            # If the background is dark, invert (we want white text for distance transform)
            if np.mean(thresh) > 127:
                thresh = cv2.bitwise_not(thresh)

            # Distance Transform calculates distance to closest zero pixel for each pixel
            dist_trans = cv2.distanceTransform(thresh, cv2.DIST_L2, 5)
            
            # The peak value in dist_trans represents half the thickness of the thickest stroke
            max_thickness = np.max(dist_trans)
            height = crop.shape[0]
            
            ratio = max_thickness / height
            return ratio > 0.04 
        except:
            return False

    def _extract_structural_data(self, text: str) -> Dict:
        extracted = {}
        clean_text = re.sub(r'\s+', ' ', text) 
        for i, cfg in enumerate(self.FIELD_CONFIG):
            found_val = "not found"
            start_pos = -1
            for kw in cfg["keywords"]:
                pattern = re.compile(re.escape(kw), re.IGNORECASE)
                match = pattern.search(clean_text)
                if match:
                    start_pos = match.end()
                    break
            
            if start_pos != -1:
                end_pos = len(clean_text)
                if i + 1 < len(self.FIELD_CONFIG):
                    next_cfg = self.FIELD_CONFIG[i+1]
                    for nkw in next_cfg["keywords"]:
                        next_match = re.search(re.escape(nkw), clean_text[start_pos:], re.IGNORECASE)
                        if next_match:
                            end_pos = start_pos + next_match.start()
                            break
                
                raw_val = clean_text[start_pos:end_pos].strip()
                raw_val = re.sub(r'^[:\-\s\t\.]+', '', raw_val) 
                extracted[cfg["id"]] = raw_val if raw_val else "not found"
        return extracted

    def ingest_document(self, file):
        suffix = file.name.lower().split(".")[-1]
        file_bytes = file.read()
        
        # Support multiple image formats
        if suffix in ["jpg", "jpeg", "png", "bmp", "tiff", "tif", "webp"]:
            raw_text, _, _ = self._get_ocr_data(Image.open(io.BytesIO(file_bytes)))
        else:
            raw_text = self._extract_text_from_doc(file_bytes, suffix)

        data = self._extract_structural_data(raw_text)
        data["file_name"] = file.name
        raw_lower = raw_text.lower()
        
        if any(kw in raw_lower for kw in ["whiskey", "vodka", "rum", "gin", "tequila"]):
            data["category"] = "Spirits"
        elif "wine" in raw_lower:
            data["category"] = "Wine"
        else:
            data["category"] = "Beer"
        
        self.applications.append(data)
        return data["category"]
    
    def ingest_documents_batch(self, files):
        """Batch process multiple documents for faster ingestion"""
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_file = {executor.submit(self.ingest_document, f): f for f in files}
            for future in as_completed(future_to_file):
                try:
                    results.append(future.result())
                except Exception as e:
                    print(f"Error processing file: {e}")
        return results

    def _verify_single_label(self, label_file, force_category=None) -> Dict:
        """Internal method for single label verification"""
        start_time = time.perf_counter()
        img = Image.open(label_file)
        label_text, ocr_results, img_arr = self._get_ocr_data(img)
        
        best_app, highest_score = None, 0
        for app in self.applications:
            score = fuzz.partial_ratio(app.get("brand", "").lower(), label_text.lower())
            if score > highest_score:
                highest_score, best_app = score, app

        res = {"label_file": label_file.name, "processing_time": 0, "is_human_decision": False,
               "ai_status": "Fail", "final_status": "Fail", "app_file": "None",
               "category": force_category or "Unknown", "comparisons": []}
        
        if not best_app:
            res["processing_time"] = time.perf_counter() - start_time
            return res

        comparisons = []
        for cfg in self.FIELD_CONFIG:
            if cfg["id"] == "hws": continue
            app_val = best_app.get(cfg["id"], "not found")
            match_score = fuzz.partial_ratio(app_val.lower(), label_text.lower())
            is_match = match_score > 70 if app_val != "not found" else False
            label_val = app_val if is_match else "Mismatch/Missing"
            
            comparisons.append({
                "field": cfg["label"], 
                "app": app_val, 
                "label_val": label_val, 
                "status": "Match" if is_match else "Fail"
            })

        # --- SPECIALIZED HEALTH WARNING CHECK (Words + Caps + Bold) ---
        hws_score = fuzz.token_set_ratio(self.HWS_MASTER_TEXT.lower(), label_text.lower())
        
        # 1. Caps Check
        has_caps = "GOVERNMENT WARNING" in label_text 
        
        # 2. Bold Check
        is_bold_found = False
        for bbox, text, conf in ocr_results:
            if "GOVERNMENT" in text.upper():
                if self._is_bold(img_arr, bbox):
                    is_bold_found = True
                    break

        hws_status = "Match" if (hws_score > 80 and has_caps and is_bold_found) else "Fail"
        
        bold_str = "BOLD" if is_bold_found else "NOT BOLD"
        caps_str = "CAPS" if has_caps else "NOT CAPS"
        
        comparisons.append({
            "field": "HEALTH WARNING", 
            "app": "Regulatory Text + CAPS + BOLD", 
            "label_val": f"{hws_score}% Text Match | {caps_str} | {bold_str}",
            "status": hws_status
        })

        ai_status = "Pass" if all(c["status"] == "Match" for c in comparisons) else "Fail"
        res.update({"ai_status": ai_status, "final_status": ai_status, "app_file": best_app["file_name"],
                    "category": force_category or best_app["category"], "comparisons": comparisons,
                    "processing_time": time.perf_counter() - start_time})
        return res
    
    def verify_label(self, label_file, force_category=None) -> Dict:
        """Public method for single label verification"""
        return self._verify_single_label(label_file, force_category)
    
    def verify_labels_batch(self, label_files, force_category=None) -> List[Dict]:
        """Batch process multiple labels with parallel processing"""
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_file = {
                executor.submit(self._verify_single_label, f, force_category): f
                for f in label_files
            }
            for future in as_completed(future_to_file):
                try:
                    results.append(future.result())
                except Exception as e:
                    print(f"Error verifying label: {e}")
                    # Add error result
                    results.append({
                        "label_file": "error",
                        "processing_time": 0,
                        "is_human_decision": False,
                        "ai_status": "Error",
                        "final_status": "Error",
                        "app_file": "None",
                        "category": "Unknown",
                        "comparisons": []
                    })
        return results

    def _extract_text_from_doc(self, bytes_data, suffix):
        """Extract text from various document formats"""
        if suffix == "pdf":
            reader = PdfReader(io.BytesIO(bytes_data))
            return " ".join([p.extract_text() for p in reader.pages if p.extract_text()])
        elif suffix in ["doc", "docx"]:
            doc = DocxDocument(io.BytesIO(bytes_data))
            return " ".join([p.text for p in doc.paragraphs])
        elif suffix == "txt":
            return bytes_data.decode('utf-8', errors='ignore')
        return ""
    
    def clear_library(self):
        self.applications = []