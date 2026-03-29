# PrivacyLens — DPDPA 2023 Privacy Policy Analyzer

AI-powered web application that analyzes privacy policies clause-by-clause and classifies risk using India's Digital Personal Data Protection Act 2023 (DPDPA).

## Research Contributions
1. First DPDPA-annotated clause-level corpus of Indian privacy policies
2. Vagueness detection — quantifies deliberate linguistic obfuscation
3. Absence detection — flags user rights missing from policy

**Baseline comparison:** Polisis (USENIX 2018) — no DPDPA alignment, no vagueness/absence detection

---

## Setup

```bash
git clone <repo-url>
cd Privacy-Policy-Analyzer
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

Create a `.env` file (never commit this):
```
GROQ_API_KEY=your_key_here
```
Get a free Groq key at: https://console.groq.com

---

## Run

**Main app (Privacy Policy Analyzer):**
```bash
streamlit run frontend/app.py
```

**Annotation Assistant:**
```bash
streamlit run training/annotation_app.py
```

**Train baseline SVM:**
```bash
python src/models/baseline_svm.py
```

---

## Project Structure

```
├── data/
│   ├── raw/                        # scraped policy texts (not in git)
│   ├── labeled/                    # DPDPA annotated CSV corpus
│   └── processed/
│       └── stage1_ready.csv        # 8,777 OPP-115 clauses
├── src/
│   ├── ingestion/
│   │   ├── clause_segmentor.py
│   │   ├── data_loader.py
│   │   └── url_scraper.py
│   ├── models/
│   │   ├── baseline_svm.py         # TF-IDF + SVM (Macro F1: 0.80)
│   │   ├── risk_classifier.py
│   │   └── simplifier.py
│   └── pipeline.py
├── training/
│   ├── build_dataset/
│   │   ├── build_dpdpa_dataset.py
│   │   └── scrape_missing_companies.py
│   ├── annotation_app.py           # Streamlit annotation tool
│   ├── auto_annotate.py            # Groq batch annotator
│   └── merge_annotations.py
├── frontend/
│   └── app.py                      # Main Streamlit dashboard
└── models/checkpoints/             # trained models (not in git)
```

---

## Results (Baseline)

| Metric | Value |
|--------|-------|
| Training samples | 8,777 clauses |
| SVM Macro F1 | 0.8027 |
| CV Macro F1 | 0.7945 ± 0.017 |
| Zomato risk score | 31.3 / 100 |
| Zomato clauses analyzed | 207 |

---

## Dataset

- **OPP-115**: 8,777 clauses, 8 categories (Princeton/CMU)
- **DPDPA Corpus**: 770 clauses from 9 Indian companies (Zomato, PhonePe, Nykaa, BigBasket, Razorpay, Flipkart, Swiggy, UIDAI, OLA)

---

## Tech Stack

Python 3.11 · scikit-learn · transformers · spaCy · Streamlit · Groq API (Llama 3.3 70B)

---

## Team

Final year B.Tech CSE (Cyber Security) — Nagpur, India · Graduating 2027