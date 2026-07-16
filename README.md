# PrivacyLens

**A Universal Privacy Policy Translator — DPDPA 2023-Aligned Clause-Level Risk Classification for Indian Privacy Policies**

PrivacyLens reads any privacy policy and tells you, in plain English, what it actually means. It segments the policy into individual clauses, classifies each one as high-risk (🔴), protective (🟢), or ambiguous (🟡), flags user rights that are conspicuously absent, and produces a single 0–100 risk score you can act on in seconds.

Built as a final-year research project aligned with India's Digital Personal Data Protection Act (DPDPA) 2023.

---

## Why This Exists

Privacy policies are long, vague by design, and nobody reads them. Existing tools like [Polisis](https://pribot.org/polisis/) (USENIX 2018) analyze English-language policies against GDPR/CCPA-style frameworks, but nothing does this for Indian consumers under DPDPA 2023. PrivacyLens is, to our knowledge, the first clause-level risk classifier trained specifically on Indian privacy policy language and DPDPA-aligned annotations.

**What makes it different:**
- **DPDPA-aligned** — every clause is checked against Indian data protection law, not just GDPR/CCPA
- **Vagueness detection** — quantifies deliberately obscure language (hedge words, passive voice, undefined third parties) instead of just flagging keywords
- **Absence detection** — flags rights that are *missing* from a policy, not just risky language that's present. No existing tool does this.
- **Plain-English explanations** — every clause gets a human-readable explanation, not just a label

---

## How It Works

```
Privacy Policy (paste text or URL)
              │
              ▼
   Clause Segmentor            → splits into individual clauses
              │
              ▼
   Category Classifier (SVM)   → 8 data-practice categories, Macro F1 0.80
              │
              ▼
   Risk Classifier (RoBERTa)   → Red / Green / Gray per clause
              │
              ▼
   Vagueness Detector          → hedge-word & passive-voice scoring
              │
              ▼
   Simplifier                  → plain-English explanation per clause
              │
              ▼
   Absence Detector            → checks 6 expected user rights
              │
              ▼
   Risk Score (0–100)          → weighted composite score
              │
              ▼
   Streamlit Dashboard         → 3-column flag view + detailed breakdown
```

---

## Model Performance

| Component | Model | Metric | Score |
|---|---|---|---|
| Category classification | TF-IDF + SVM (OPP-115, 8,777 clauses) | Macro F1 | 0.80 |
| Risk classification | RoBERTa-base (DPDPA corpus, 816 clauses) | Macro F1 | *in progress* |
| Risk classification (red class) | RoBERTa-base | F1 | *in progress* |

We evaluated Legal-BERT (`nlpaueb/legal-bert-base-uncased`) as an alternative to RoBERTa and found it underperformed — its pretraining corpus (EU legislation, US case law) doesn't match the register of Indian consumer-facing privacy disclosures. This negative result is documented and discussed in the accompanying paper.

---

## Dataset

**DPDPA-Annotated Indian Privacy Policy Corpus** — 816 manually annotated clauses from 9 major Indian companies (Zomato, Flipkart, Swiggy, PhonePe, Razorpay, BigBasket, Nykaa, UIDAI, Ola), labeled for risk (red/green/gray) and mapped to DPDPA 2023 sections.

📦 Dataset available on Kaggle: https://www.kaggle.com/datasets/niketfuladi/dpdpa-2023-indian-privacy-policy-clause-level-risk

---

## Tech Stack

- **Backend:** Python 3.11, FastAPI (planned), Streamlit (current)
- **ML:** scikit-learn, PyTorch, HuggingFace Transformers, spaCy
- **Models:** TF-IDF+SVM (category), RoBERTa-base (risk), spaCy (entity extraction for explanations)
- **Data:** OPP-115 (category pretraining), custom DPDPA corpus (risk fine-tuning)

---

## Project Structure

```
privacy-lens/
├── data/
│   ├── raw/                        # scraped policy texts
│   ├── opp115/                     # OPP-115 dataset (category classifier training)
│   ├── labeled/                    # DPDPA-annotated risk corpus
│   └── processed/                  # model predictions, evaluation outputs
├── src/
│   ├── ingestion/
│   │   ├── clause_segmentor.py     # HTML-aware clause splitting
│   │   ├── data_loader.py
│   │   └── url_scraper.py
│   ├── models/
│   │   ├── baseline_svm.py         # category classifier training
│   │   ├── risk_classifier.py      # risk classification logic
│   │   └── simplifier.py           # plain-English explanation generator
│   └── pipeline.py                 # orchestrates the full analysis flow
├── training/
│   ├── build_dataset/
│   └── notebooks/                  # Colab training notebooks (RoBERTa fine-tuning)
├── frontend/
│   └── app.py                      # Streamlit dashboard
├── models/checkpoints/             # trained model artifacts
├── requirements.txt
└── README.md
```

---

## Getting Started

### Prerequisites
- Python 3.11+
- ~2 GB disk space for models and dependencies

### Installation

```bash
git clone https://github.com/<your-username>/privacy-lens.git
cd privacy-lens

python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### Run the app

```bash
streamlit run frontend/app.py
```

Navigate to `http://localhost:8501`, paste a privacy policy (or a URL), and click **Analyze**.

---

## Roadmap

- [x] Category classifier (SVM, Macro F1 0.80)
- [x] Rule-based risk classifier + vagueness/absence detection
- [x] DPDPA-annotated training corpus (816 clauses)
- [x] RoBERTa fine-tuning for risk classification
- [ ] Replace rule-based risk classifier with fine-tuned RoBERTa in production pipeline
- [ ] PDF upload support
- [ ] FastAPI backend + REST API
- [ ] Containerized deployment (Docker)
- [ ] Public deployment (Hugging Face Spaces / Railway)
- [ ] Multilingual support (Hindi, other Indian languages via XLM-RoBERTa)
- [ ] Browser extension for real-time policy analysis
- [ ] Research paper publication (arXiv → FIRE 2025 / LREC-COLING)

---

## Contributions & Research
1. First DPDPA 2023 clause-level annotated corpus of Indian privacy policies
2. A vagueness detection metric for quantifying deliberate linguistic obfuscation
3. Absence detection — flagging user rights missing from a policy (not found in prior work, including Polisis)

---

## Contributing

This is currently a solo academic project, but suggestions and issues are welcome. If you spot a bug, have a dataset contribution, or want to discuss the methodology, open an issue.

---

## License

CC BY-SA 4.0


---

## Acknowledgements

- [OPP-115 Corpus](https://usableprivacy.org/data) — Usable Privacy Policy Project, CMU
- [Polisis](https://pribot.org/polisis/) (Harkous et al., USENIX 2018) — closest prior work, used as baseline comparison
- India's Digital Personal Data Protection Act, 2023

---

## Contact

Niket Fuladi
Final Year B.Tech CSE (Cyber Security), Nagpur, India
https://linkedin.com.in/niket-fuladi · fuladiniket.work@gmail.com
