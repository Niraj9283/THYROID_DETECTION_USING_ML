# 🔬 ThyroScan AI — AI-Assisted Thyroid Risk Screening Platform

> **Clinical-Grade AI Risk Stratification, Multi-Model Ensemble, Conversational Screening, Lab Report OCR, and Decision Support Platform.**

---

## 🌟 Key Platform Capabilities

- 🤖 **Multi-Model Ensemble Engine:** Parallel soft-voting consensus across **Gradient Boosting (45%)**, **Random Forest (40%)**, and **SVM (15%)** with probability calibration and model agreement alerts.
- 🎙️ **Conversational Voice & Chat Screening:** Natural language speech-to-text entity extractor that converts spoken or typed patient dialog into structured clinical payloads in real time.
- ⚖️ **Longitudinal Lab Report Comparator:** Compares Baseline (Report A) and Follow-up (Report B) blood tests to calculate exact percentage shifts ($\Delta \%$), hormone velocity, and questions for physician consultation.
- 🧪 **Interactive "What-If" Biomarker Simulator:** Real-time hormone sliders (TSH, T3, TT4, Age, Levothyroxine) for exploring clinical decision boundaries.
- 🩺 **Doctor Mode & SOAP Note Generator:** Dual-view clinician portal with EHR-ready **SOAP (Subjective, Objective, Assessment, Plan)** progress notes and 1-click clipboard export.
- 📄 **Diagnostic Lab PDF OCR Extractor:** Automatically extracts TSH, T3, and TT4 from uploaded lab reports with interactive confirmation before analysis.
- 📥 **Clinical Medical PDF Reports:** Generates professional printable screening reports with biomarker reference intervals, multiclass distributions, and action plans via ReportLab.
- 💬 **Context-Aware ThyroBot AI Copilot:** Medical RAG assistant grounded in ATA, NHS, and WHO clinical guidelines with verified citations.
- 🛡️ **Clinical Safety Gateway:** Intercepts dangerous self-treatment suggestions, unmonitored medication dosage alterations, and acute emergency signs with urgent triage advisories.
- 📱 **Progressive Web App (PWA):** Offline shell caching and desktop/mobile installability.

---

## 📊 Multi-Model Performance & Evaluation

| Model Architecture | Accuracy | F1 Score | Ensemble Role |
|--------------------|----------|----------|---------------|
| **Gradient Boosting** | **97.00%** | **96.96%** | Primary Classifier (45% Wt) |
| **Random Forest** | **96.38%** | **96.39%** | Secondary Classifier (40% Wt) |
| **SVM (RBF Kernel)** | **87.08%** | **87.73%** | Probability Calibrator (15% Wt) |

*Trained on 30,000 anonymized clinical records with an 80/20 stratified validation split.*

---

## 🗂 Project Architecture

```
thyroid_detection/
├── backend/
│   ├── app.py                      # Flask REST API & Web Application
│   ├── database.py                 # SQLite/PostgreSQL Schema & CRUD
│   ├── auth.py                     # PBKDF2 Hashing & JWT Auth
│   ├── predict_service.py          # Feature normalization & Explainability
│   ├── ensemble_service.py         # Multi-Model Ensemble Agreement
│   ├── copilot_service.py          # Lab Report A vs B Comparator
│   ├── safety_gateway.py           # Clinical Safety & Triage Gateway
│   ├── conversational_screening.py # Natural language entity extraction
│   ├── doctor_service.py           # SOAP Note & EHR Summarizer
│   ├── report_service.py           # ReportLab PDF Report Generator
│   ├── ocr_service.py              # Lab Report PDF/Text Extractor
│   ├── rag_service.py              # Medical Guidelines RAG & Citations
│   └── train.py                    # Model Training Pipeline
├── frontend/
│   ├── index.html                  # Responsive Web & Doctor Portal UI
│   ├── manifest.json               # PWA App Manifest
│   ├── sw.js                       # Service Worker for Offline Caching
│   └── static/
│       ├── css/style.css           # Healthcare SaaS Design System
│       └── js/app.js               # Client Logic & Reactive State
├── models/
│   ├── best_model.pkl              # Primary Model
│   ├── gb_model.pkl                # Gradient Boosting
│   ├── rf_model.pkl                # Random Forest
│   ├── svm_model.pkl               # Support Vector Machine
│   ├── label_encoder.pkl           # Target Class Encoder
│   ├── feature_names.json          # Feature Registry
│   └── model_comparison.json       # Benchmarks
├── tests/
│   ├── test_api.py                 # Core API & Auth Test Suite
│   └── test_advanced_features.py   # Ensemble, Comparison & Safety Tests
├── requirements.txt                # Python Dependencies
├── run.py                          # One-click Server Launcher
└── README.md                       # Documentation
```

---

## 🚀 Quick Start

### 1. Set Up Virtual Environment

```bash
# Create and activate virtual environment
python -m venv .venv

# Windows:
.venv\Scripts\activate

# Linux / Mac:
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Train Models (Optional - Pre-trained Models Included)

```bash
python backend/train.py
```

### 4. Run Automated Test Suite

```bash
python -m unittest discover -s tests -p "test_*.py"
```

### 5. Launch the Platform

```bash
python run.py
```

Open your browser at: **http://localhost:5000**

---

## 🔌 API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `POST /api/predict` | POST | Multi-Model Ensemble Screening & Risk Stratification |
| `POST /api/simulator/simulate` | POST | Interactive What-If Biomarker Slider Simulation |
| `POST /api/lab-report/compare` | POST | Compare Report A vs Report B ($\Delta \%$ & Trajectory) |
| `POST /api/conversational/extract` | POST | Extract Screening Parameters from Conversational Dialogue |
| `GET /api/doctor/summary/<id>` | GET | Generate Clinical SOAP Note & EHR Summary |
| `POST /api/lab-report/extract` | POST | Upload and Parse Diagnostic Lab Report (PDF/Text) |
| `GET /api/reports/<id>/pdf` | GET | Download Official Medical PDF Screening Report |
| `POST /api/chat` | POST | Context-Aware ThyroBot AI Copilot with Safety Gateway |
| `GET /api/trends` | GET | Longitudinal Biomarker & BMI Health Timeline |
| `GET /api/health` | GET | Platform & Ensemble Health Verification |

---

## ⚖️ Medical Disclaimer

*ThyroScan AI is an educational and clinical decision-support screening tool designed for statistical risk stratification. It does NOT constitute a medical diagnosis or treatment prescription. Always consult a qualified endocrinologist or physician regarding clinical laboratory interpretation and medical management.*
