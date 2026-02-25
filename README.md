# AI-Powered Alcohol Label Verification App

An intelligent compliance verification system that automates the review of alcohol beverage labels against TTB (Alcohol and Tobacco Tax and Trade Bureau) application forms using advanced OCR, computer vision, and fuzzy matching algorithms.

## System Architecture

```mermaid
flowchart LR
    subgraph INPUT[" INPUT "]
        A[PDF/DOCX<br/>Forms]
        B[Label<br/>Images]
    end
    
    subgraph CORE[" CORE ENGINE "]
        C[Document<br/>Parser]
        D[EasyOCR]
        E[CV Bold<br/>Detection]
        F[Fuzzy<br/>Matcher]
    end
    
    subgraph VERIFY[" VERIFICATION "]
        G[(App<br/>Library)]
        H{Field Match<br/>70%}
        I{Health Warning<br/>80% + CAPS + BOLD}
    end
    
    subgraph OUTPUT[" OUTPUT "]
        J[AI Decision]
        K[Human<br/>Override]
        L[CSV<br/>Report]
    end
    
    A --> C --> G
    B --> D --> H
    B --> E --> I
    G --> F --> H --> I
    I --> J --> K --> L
    
    style INPUT fill:#e3f2fd
    style CORE fill:#fff3e0
    style VERIFY fill:#fce4ec
    style OUTPUT fill:#f3e5f5
```

## Overview

This application streamlines the alcohol label compliance audit process by:
- **Extracting** structured data from TTB application forms (PDF/DOCX)
- **Analyzing** label images using OCR and computer vision
- **Verifying** compliance with regulatory requirements including health warning formatting
- **Detecting** bold text styling using Stroke Width Analysis via Distance Transform
- **Generating** comprehensive audit reports with human-in-the-loop override capabilities

## Key Features

### 1. **Document Ingestion**
- Supports **multiple formats**: PDF, DOCX, TXT, and images (JPG, PNG, BMP, TIFF, WEBP)
- **Batch processing** for 300+ documents
- Automatic text extraction and structured data parsing
- Intelligent categorization (Beer, Wine, Spirits)

### 2. **Advanced Label Verification**
- **High-Performance OCR**: EasyOCR with batch processing (300 labels < 5 seconds)
- **Blurry Image Enhancement**: Automatic sharpening and contrast adjustment
- **Multi-Format Support**: JPG, PNG, BMP, TIFF, WEBP
- **Fuzzy Matching**: 70%+ similarity threshold for field validation
- **Computer Vision**: Local CV-based bold detection without cloud dependencies
- **Health Warning Compliance**:
  - Validates 1988 statutory wording (80%+ match)
  - Checks for ALL CAPS formatting
  - Detects BOLD styling on "GOVERNMENT WARNING" using Distance Transform

### 3. **Human-in-the-Loop Workflow**
- AI provides initial pass/fail assessment
- **Field Editing**: Edit detected values and re-submit for failed assessments
- Human reviewers can override decisions
- Audit trail tracks all decisions

### 4. **Audit Reporting**
- Downloadable CSV reports with timestamps
- Detailed field-by-field comparison
- Processing time metrics
- Human override tracking

### 5. **Performance & Scalability**
- **Batch Processing**: Handle 300+ inputs efficiently
- **Parallel Processing**: Multi-threaded for faster results
- **Cloud-Ready**: Optimized for Streamlit Cloud deployment
- **Average Speed**: < 2 seconds per label

## Quick Start

### Prerequisites
- Python 3.8+
- pip package manager

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd BCK2_Ai-Powered\ Alcohol\ Label\ Verification\ App\ v2
```

2. **Create a virtual environment** (recommended)
```bash
python -m venv label
source label\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

### Running the Application

```bash
streamlit run app.py
```

The application will open in your default browser at `http://localhost:8501`

## Usage Guide

### Step 1: Upload Applications
1. Navigate to the **"Step 1: Upload Applications"** tab
2. Upload TTB application forms (PDF or DOCX format)
3. Click **"Build Application Library"** to process and index documents

### Step 2: Label Verification
1. Switch to the **"Step 2: Label Verification"** tab
2. Upload label images (JPG, PNG formats)
3. Click **"Start Analysis"** to begin verification
4. Review results:
   - ✅ Green checkmark = Pass
   - ⚠️ Warning icon = Requires review
5. Use **Override** or **Confirm Fail** buttons for human decisions

### Step 3: Generate Report
1. Click **"Step 3. Generate Audit Report"**
2. Download the CSV file containing:
   - Timestamp
   - Label filename
   - Matched application
   - AI initial decision
   - Human override status
   - Final decision
   - Health warning details
   - Processing latency

## Verification Rules

### Standard Fields (70%+ Fuzzy Match)
- Brand Name
- Class/Type Designation
- Alcohol Content (ABV)
- Net Contents
- Address
- Country of Origin

### Health Warning (Specialized Check)
- **Text Match**: 80%+ similarity to 1988 statutory wording
- **Formatting Requirements**:
  - "GOVERNMENT WARNING" must be in ALL CAPS
  - "GOVERNMENT WARNING" must be in BOLD
- **Bold Detection**: Uses Distance Transform algorithm to analyze stroke width

## Technical Architecture

### Core Components

#### [`app.py`](app.py)
- Streamlit-based user interface
- Session state management
- Multi-tab workflow orchestration
- Results visualization and export

#### [`rag_system.py`](rag_system.py)
- **RAGSystem Class**: Core verification engine
- **OCR Processing**: EasyOCR integration
- **Bold Detection**: CV-based stroke width analysis using Distance Transform
- **Fuzzy Matching**: thefuzz library for text comparison
- **Document Parsing**: PDF and DOCX text extraction

### Key Technologies
- **Frontend**: Streamlit
- **OCR**: EasyOCR (CPU-optimized)
- **Computer Vision**: OpenCV
- **Image Processing**: Pillow, NumPy
- **Text Matching**: thefuzz, python-Levenshtein
- **Document Parsing**: PyPDF2, python-docx
- **Deep Learning**: PyTorch (EasyOCR backend)

## Performance

- **Batch Processing**: 300+ labels in under 5 seconds (parallel processing)
- **Average Processing Time**: ~1-2 seconds per label
- **Accuracy**: 70%+ fuzzy match threshold for standard fields
- **Health Warning Detection**: 80%+ text match + formatting validation
- **Local Processing**: No cloud API dependencies for core functionality
- **Blurry Image Handling**: Automatic enhancement for low-quality images

## Test Data

Sample test data is provided in the `Test_data/` directory:
- **Test_Data_Pass/**: Examples that should pass verification
- **Test_Data_Fail/**: Examples that should fail verification

## Dependencies

See [`requirements.txt`](requirements.txt) for complete list. Key dependencies:
- streamlit >= 1.35.0
- easyocr >= 1.7.1
- opencv-python >= 4.10.0
- thefuzz >= 0.22.1
- torch == 2.2.2

## Configuration

### Field Configuration
Modify `FIELD_CONFIG` in [`rag_system.py`](rag_system.py:14-22) to adjust:
- Field extraction keywords
- Field labels
- Extraction order

### Health Warning Text
Update `HWS_MASTER_TEXT` in [`rag_system.py`](rag_system.py:24-29) to match current regulatory requirements.

### Bold Detection Sensitivity
Adjust the ratio threshold in [`_is_bold()`](rag_system.py:73) method:
```python
return ratio > 0.04  # Increase for stricter bold detection
```
### Scaling for Enterprise
To scale the system for wider use, the following integrations are proposed:
*   **Azure AI Document Intelligence:** To automate the extraction of complex, multi-page COLA (Certificate of Label Approval) forms.
*   **Vector Search (ChromaDB):** Implementing semantic search to handle libraries with thousands of applications efficiently.
*   **FedRAMP Compliance:** Transitioning from this local prototype to a **FedRAMP Authorized** cloud environment for centralized auditing and PIV/CAC card secure login.

## Future-State Architecture

```mermaid
flowchart LR

%% =============================
%% USER ACCESS LAYER
%% =============================
subgraph USER_LAYER["User Access Layer"]
    U1["TTB Reviewer"]
    U2["Compliance Officer"]
    U3["Administrator"]
end

subgraph AUTH_LAYER["Identity and Access Management"]
    A1["Azure AD Entra ID"]
    A2["PIV CAC Authentication"]
    A3["Role Based Access Control"]
end

U1 --> A1
U2 --> A1
U3 --> A1
A1 --> A2
A2 --> A3

%% =============================
%% APPLICATION LAYER
%% =============================
subgraph APP_LAYER["Application Layer Containerized"]
    S1["Frontend UI Streamlit or React"]
    S2["API Gateway"]
    S3["Compliance Verification Engine"]
    S4["Human Override Workflow Engine"]
end

A3 --> S1
S1 --> S2
S2 --> S3
S3 --> S4

%% =============================
%% PROCESSING LAYER
%% =============================
subgraph PROCESSING_LAYER["AI and Document Processing Layer"]
    P1["Azure AI Document Intelligence"]
    P2["EasyOCR Engine"]
    P3["Computer Vision Stroke Width Analysis"]
    P4["Fuzzy Matching Service"]
    P5["Health Warning Validation Module"]
end

S3 --> P1
S3 --> P2
S3 --> P3
S3 --> P4
S3 --> P5

%% =============================
%% DATA LAYER
%% =============================
subgraph DATA_LAYER["Secure Data Layer"]
    D1["Azure Blob Storage Encrypted"]
    D2["Application Metadata Database Azure SQL"]
    D3["Vector Database ChromaDB or Azure AI Search"]
    D4["Immutable Audit Log Store"]
end

P1 --> D1
P2 --> D1
P4 --> D3
S3 --> D2
S4 --> D4

%% =============================
%% GOVERNANCE AND MONITORING
%% =============================
subgraph GOVERNANCE_LAYER["Governance Security and Monitoring"]
    G1["Azure Monitor"]
    G2["SIEM Security Information and Event Management"]
    G3["Model Risk Management Dashboard"]
    G4["Compliance Reporting Engine"]
end

S3 --> G1
S3 --> G2
D4 --> G2
G1 --> G3
G3 --> G4

%% =============================
%% INFRASTRUCTURE
%% =============================
subgraph INFRA_LAYER["Infrastructure FedRAMP Environment"]
    I1["Azure Kubernetes Service"]
    I2["Private Virtual Network"]
    I3["Key Vault"]
    I4["TLS Encryption in Transit"]
end

S1 --> I1
S2 --> I1
S3 --> I1
D1 --> I2
D2 --> I2
I1 --> I3
I1 --> I4
```

**Note**: This application is designed for compliance verification assistance. Final approval decisions should always involve qualified human reviewers familiar with TTB regulations.