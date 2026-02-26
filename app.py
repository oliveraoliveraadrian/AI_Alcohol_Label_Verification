import streamlit as st
import pandas as pd
from lib_system import SystemLib
import datetime
import time

st.set_page_config(page_title="AI Alcohol Label Verification", layout="wide")

if "slib" not in st.session_state:
    with st.spinner("Initializing Local OCR & CV Engine..."):
        st.session_state.slib = SystemLib()

if "all_results" not in st.session_state:
    st.session_state.all_results = []

if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

if "editing_mode" not in st.session_state:
    st.session_state.editing_mode = {}

st.title("AI-Powered Alcohol Label Verification")
st.markdown("Automated Compliance Audit with **Stroke Width Analysis** for Bold Detection.")

tab1, tab2 = st.tabs(["Step 1: Upload Applications", "Step 2: Label Verification"])

with tab1:
    st.header("1. Document Ingestion")
    app_files = st.file_uploader(
        "Upload TTB Form (PDF/DOCX/TXT/Images)",
        accept_multiple_files=True,
        key=f"apps_{st.session_state.uploader_key}"
    )
    if st.button("Build Application Library", type="primary"):
        if app_files:
            progress_bar = st.progress(0)
            status_text = st.empty()
            start_time = time.time()
            
            # Use batch processing for faster ingestion
            if len(app_files) > 5:
                status_text.text(f"Batch processing {len(app_files)} applications...")
                st.session_state.slib.ingest_documents_batch(app_files)
                progress_bar.progress(1.0)
            else:
                for i, f in enumerate(app_files):
                    status_text.text(f"Indexing {f.name}...")
                    st.session_state.slib.ingest_document(f)
                    progress_bar.progress((i + 1) / len(app_files))
            
            elapsed = time.time() - start_time
            status_text.success(f"Uploaded {len(app_files)} applications in {elapsed:.2f}s")
        else: st.error("Please upload documents.")

with tab2:
    st.header("2. Label Verification")
    with st.expander("Compliance Logic Guide", expanded=False):
        st.markdown("""
        ### **Verification Rules**
        *   **Standard Fields:** Brand, ABV, and Class are matched using fuzzy logic (>70%).
        *   **Health Warning (HWS):**
            *   **Text:** Matches the 1988 Statutory wording.
            *   **Formatting:** Specifically checks for **ALL CAPS** and **BOLD** on the phrase 'GOVERNMENT WARNING'.
        *   **Performance:**
            *   Batch processing for 300+ labels
            *   Local Computer Vision (Distance Transforms) for bold detection
            *   Supports blurry images with automatic enhancement
            *   Multi-format support: JPG, PNG, BMP, TIFF, WEBP
        """)

    label_files = st.file_uploader(
        "Upload Label Images (Supports: JPG, PNG, BMP, TIFF, WEBP)",
        type=["jpg", "jpeg", "png", "bmp", "tiff", "tif", "webp"],
        accept_multiple_files=True,
        key=f"labels_{st.session_state.uploader_key}"
    )
    
    if st.button("Start Analysis", type="primary"):
        if label_files and st.session_state.slib.applications:
            st.session_state.all_results = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            start_time = time.time()
            
            # Use batch processing for better performance
            if len(label_files) > 5:
                status_text.text(f"Batch processing {len(label_files)} labels...")
                st.session_state.all_results = st.session_state.slib.verify_labels_batch(label_files)
                progress_bar.progress(1.0)
            else:
                for i, f in enumerate(label_files):
                    status_text.text(f"Analyzing {f.name}...")
                    st.session_state.all_results.append(st.session_state.slib.verify_label(f))
                    progress_bar.progress((i + 1) / len(label_files))
            
            elapsed = time.time() - start_time
            #avg_time = elapsed / len(label_files)

            avg_time = sum(r.get("processing_time", 0) for r in st.session_state.all_results) / len(label_files)
            
            #status_text.success(f"Processed {len(label_files)} labels in {elapsed:.2f}s (avg: {avg_time:.2f}s/label)")
            #time.sleep(10)
            st.rerun()
        else: st.error("Upload labels and ensure library is built.")

    if st.session_state.all_results:
        avg_t = sum(r.get("processing_time", 0) for r in st.session_state.all_results) / len(st.session_state.all_results)
        pending = len([r for r in st.session_state.all_results if r.get("ai_status") == "Fail" and not r.get("is_human_decision")])
        
        if len(label_files) > 5:
            avg_t=avg_t / len(label_files)

        c1, c2, c3 = st.columns(3)
        c1.metric("Avg. Speed", f"{avg_t:.2f}s")
        c2.metric("Batch Size", len(st.session_state.all_results))
        c3.metric("Review Required", pending)
        
        st.divider()

        for idx, res in enumerate(st.session_state.all_results):
            # Show all results, but expand the ones that failed
            is_fail = res.get("ai_status") == "Fail" and not res.get("is_human_decision")
            with st.expander(f"{'⚠️' if is_fail else '✅'} Label: {res['label_file']} (Result: {res['final_status']})", expanded=is_fail):
                col1, col2 = st.columns([1, 2])
                with col1:
                    img_file = next((f for f in label_files if f.name == res['label_file']), None)
                    if img_file: st.image(img_file, caption="Uploaded Label")
                with col2:
                    # Check if in editing mode
                    is_editing = st.session_state.editing_mode.get(idx, False)
                    
                    if is_editing:
                        st.subheader("✏️ Edit Fields")
                        edited_comparisons = []
                        for i, comp in enumerate(res["comparisons"]):
                            st.markdown(f"**{comp['field']}**")
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.text_input("Reference", value=comp['app'], key=f"ref_{idx}_{i}", disabled=True)
                            with col_b:
                                new_val = st.text_input("Detected Value", value=comp['label_val'], key=f"edit_{idx}_{i}")
                            
                            # Recalculate status based on edited value
                            if comp['field'] == "HEALTH WARNING":
                                new_status = comp['status']  # Keep original for HWS
                            else:
                                from thefuzz import fuzz
                                match_score = fuzz.partial_ratio(comp['app'].lower(), new_val.lower())
                                new_status = "Match" if match_score > 70 else "Fail"
                            
                            edited_comparisons.append({
                                "field": comp['field'],
                                "app": comp['app'],
                                "label_val": new_val,
                                "status": new_status
                            })
                        
                        col_save, col_cancel = st.columns(2)
                        if col_save.button("Save & Re-submit", key=f"save_{idx}"):
                            # Update the result with edited values
                            st.session_state.all_results[idx]["comparisons"] = edited_comparisons
                            new_ai_status = "Pass" if all(c["status"] == "Match" for c in edited_comparisons) else "Fail"
                            st.session_state.all_results[idx].update({
                                "ai_status": new_ai_status,
                                "final_status": new_ai_status,
                                "is_human_decision": True
                            })
                            st.session_state.editing_mode[idx] = False
                            st.success("Changes saved and re-submitted!")
                            st.rerun()
                        
                        if col_cancel.button("Cancel", key=f"cancel_{idx}"):
                            st.session_state.editing_mode[idx] = False
                            st.rerun()
                    else:
                        df_preview = pd.DataFrame(res["comparisons"])
                        df_preview.columns = ["Requirement", "Reference (App)", "Detected on Label", "Status"]
                        st.table(df_preview)
                        
                        if not res.get("is_human_decision"):
                            b1, b2, b3 = st.columns(3)
                            if b1.button("✅ OVERRIDE", key=f"p_{idx}"):
                                st.session_state.all_results[idx].update({"final_status": "Pass", "is_human_decision": True})
                                st.rerun()
                            if b2.button("❌ CONFIRM FAIL", key=f"f_{idx}"):
                                st.session_state.all_results[idx].update({"final_status": "Fail", "is_human_decision": True})
                                st.rerun()
                            if b3.button("✏️ EDIT FIELDS", key=f"e_{idx}"):
                                st.session_state.editing_mode[idx] = True
                                st.rerun()
                        else:
                            st.info(f"Human Decision Recorded: {res['final_status']}")
                            if st.button("✏️ Edit Again", key=f"edit_again_{idx}"):
                                st.session_state.editing_mode[idx] = True
                                st.session_state.all_results[idx]["is_human_decision"] = False
                                st.rerun()

        if st.button("Step 3. Generate Audit Report"):
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            report = []
            for r in st.session_state.all_results:
                report.append({
                    "Timestamp": current_time,
                    "Label": r["label_file"],
                    "Matched_App": r["app_file"],
                    "AI_Initial": r["ai_status"],
                    "Human_Override": "Yes" if r["ai_status"] != r["final_status"] else "No",
                    "Final_Decision": r["final_status"],
                    "HWS_Detail": next((c["label_val"] for c in r["comparisons"] if c["field"] == "HEALTH WARNING"), "N/A"),
                    "Latency": f"{r['processing_time']:.2f}s"
                })
            
            df_report = pd.DataFrame(report)
            st.download_button("Step 4.Download CSV Report", df_report.to_csv(index=False), "Audit_Report.csv", "text/csv")

with st.sidebar:
    st.header("System")
    if st.button("Clear Cache & Library"):
        st.session_state.slib.clear_library()
        st.session_state.all_results = []
        st.session_state.uploader_key += 1 
        st.rerun()