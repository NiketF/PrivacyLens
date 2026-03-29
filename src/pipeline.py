# src/pipeline.py

import sys, os, pickle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ingestion.clause_segmentor import segment_into_clauses
from src.models.risk_classifier     import classify_risk, compute_vagueness
from src.models.simplifier          import simplify_clause, _rule_based_simplification

EXPECTED_RIGHTS = [
    ("Right to delete your data",
     ["delet", "erasure", "remove account", "right to erasure"]),
    ("Right to access your data",
     ["access your data", "download your data", "data portability",
      "right to access", "access to your"]),
    ("Right to correct your data",
     ["correct", "rectif", "update your information", "right to correct"]),
    ("Right to opt out of marketing",
     ["opt out", "unsubscribe", "marketing preference", "opt-out"]),
    ("Breach notification commitment",
     ["data breach", "security incident", "notify you", "breach notification"]),
    ("How to contact for privacy issues",
     ["contact us", "privacy@", "data protection officer",
      "grievance", "dpo@", "privacy team"]),
]


class PrivacyPolicyAnalyzer:

    def __init__(self, model_path: str = "models/checkpoints/baseline_stage1.pkl"):
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Model not found at {model_path}. "
                f"Run: python src/models/baseline_svm.py"
            )
        with open(model_path, "rb") as f:
            self.category_model = pickle.load(f)
        print(f"Model loaded from {model_path}")

    def predict_category(self, text: str) -> tuple:
        pred  = self.category_model.predict([text])[0]
        proba = self.category_model.predict_proba([text])[0]
        conf  = round(float(max(proba)), 3)
        return pred, conf

    def check_missing_rights(self, full_text: str) -> list:
        text_lower = full_text.lower()
        missing    = []
        for right_name, keywords in EXPECTED_RIGHTS:
            if not any(kw in text_lower for kw in keywords):
                missing.append(right_name)
        return missing

    def compute_risk_score(self, classified_clauses: list) -> float:
        if not classified_clauses:
            return 50.0
        weights = {"red": 2.0, "gray": 1.0, "green": 0.0}
        total   = sum(
            weights[c['risk_label']] *
            c['risk_confidence'] *
            (1.0 + c['vagueness'] * 0.5)
            for c in classified_clauses
        )
        max_possible = 2.0 * len(classified_clauses)
        return round(min((total / max_possible) * 100, 100), 1)

    def analyze(
        self,
        policy_text:  str,
        simplify_red: bool = True
    ) -> dict:
        """
        Full analysis pipeline.
        Stage 1: Classify ALL clauses (fast — no API calls).
        Stage 2: Gemini only for Red clauses, rule-based for everything else.
        """

        # ── Stage 1: Segment ─────────────────────────────────
        clauses = segment_into_clauses(policy_text)
        print(f"Segmented: {len(clauses)} clauses — analyzing all")

        # ── Stage 2: Classify (no API calls here) ────────────
        classified = []

        for i, clause in enumerate(clauses):
            try:
                text = clause['text']

                # Skip very short fragments
                if len(text.split()) < 6:
                    continue

                # Skip heading-like lines
                if len(text.split()) < 8 and not text.endswith('.'):
                    continue

                category, cat_conf    = self.predict_category(text)
                risk_label, risk_conf = classify_risk(text, category)
                vagueness             = compute_vagueness(text)

                classified.append({
                    "clause_id":       i,
                    "text":            text,
                    "category":        category,
                    "cat_confidence":  cat_conf,
                    "risk_label":      risk_label,
                    "risk_confidence": risk_conf,
                    "vagueness":       vagueness,
                    "explanation":     "",   # filled in Stage 3
                    "word_count":      clause['word_count']
                })

                if (i + 1) % 25 == 0:
                    print(f"  Classified {i+1}/{len(clauses)}...")

            except Exception as e:
                print(f"  Skipping clause {i}: {e}")
                continue

        print(f"Classification done: {len(classified)} clauses")
        print(f"  Red: {sum(1 for c in classified if c['risk_label']=='red')} | "
              f"Green: {sum(1 for c in classified if c['risk_label']=='green')} | "
              f"Gray: {sum(1 for c in classified if c['risk_label']=='gray')}")

        # ── Stage 3: Explanations ─────────────────────────────
        # Gemini ONLY for Red clauses (typically 5-15 per policy)
        # Rule-based fallback for everything else — instant, no API
        if simplify_red:
            red_clauses = [c for c in classified if c['risk_label'] == 'red']
            print(f"Calling Gemini for {len(red_clauses)} Red clauses only...")

            for c in classified:
                if c['risk_label'] == 'red':
                    # Gemini for Red — specific, high quality explanation
                    c['explanation'] = simplify_clause(
                        c['text'], c['risk_label'], c['category']
                    )
                else:
                    # Instant rule-based for Green and Gray — no API call
                    c['explanation'] = _rule_based_simplification(
                        c['text'], c['risk_label'], c['category']
                    )
        else:
            # simplify_red=False → rule-based for everything, zero API calls
            for c in classified:
                c['explanation'] = _rule_based_simplification(
                    c['text'], c['risk_label'], c['category']
                )

        # ── Stage 4: Missing rights check ────────────────────
        missing_rights = self.check_missing_rights(policy_text)

        # ── Stage 5: Risk score ───────────────────────────────
        risk_score = self.compute_risk_score(classified)

        # ── Stage 6: Structured output ────────────────────────
        return {
            "risk_score":     risk_score,
            "risk_level":     _score_to_level(risk_score),
            "total_clauses":  len(classified),
            "red_count":      sum(1 for c in classified if c['risk_label'] == 'red'),
            "green_count":    sum(1 for c in classified if c['risk_label'] == 'green'),
            "gray_count":     sum(1 for c in classified if c['risk_label'] == 'gray'),
            "missing_rights": missing_rights,
            "data_collected": [c for c in classified if c['category'] == 'data_collection'],
            "data_shared":    [c for c in classified if c['category'] == 'data_sharing'],
            "user_rights":    [c for c in classified if c['category'] == 'user_rights'],
            "watch_out":      [c for c in classified
                               if c['risk_label'] == 'red' or c['vagueness'] > 0.35],
            "all_clauses":    classified
        }


def _score_to_level(score: float) -> str:
    if score <= 20: return "LOW RISK"
    if score <= 45: return "MODERATE RISK"
    if score <= 70: return "HIGH RISK"
    return "VERY HIGH RISK"


if __name__ == "__main__":
    sample = """We collect your name, email, location, and browsing history when you use our app.
We also collect biometric data including your fingerprint for authentication.

We may share your personal information with advertising partners and data brokers
without your explicit consent. We reserve the right to sell aggregated user data.

You have the right to request deletion of your personal data within 30 days.
You can opt out of marketing communications at any time.

We may retain backup copies of your data for up to 90 days after account deletion.
We may keep certain records indefinitely for legal compliance purposes.

We reserve the right to modify this policy at any time without prior notice.
Continued use of our service constitutes acceptance of any changes.

Any disputes shall be resolved through binding arbitration.
You waive your right to participate in class action lawsuits."""

    analyzer = PrivacyPolicyAnalyzer()
    results  = analyzer.analyze(sample, simplify_red=False)

    print(f"\n{'='*60}")
    print(f"RISK SCORE:    {results['risk_score']} / 100  —  {results['risk_level']}")
    print(f"Total Clauses: {results['total_clauses']}")
    print(f"Red: {results['red_count']}  |  Green: {results['green_count']}  |  Gray: {results['gray_count']}")
    print(f"\nMISSING RIGHTS:")
    for r in results['missing_rights']:
        print(f"  - {r}")
    print(f"\nWATCH OUT FOR ({len(results['watch_out'])} clauses):")
    for c in results['watch_out'][:5]:
        print(f"  {c['risk_label'].upper()}: {c['text'][:80]}...")
    print(f"\nSAMPLE EXPLANATIONS:")
    for c in results['all_clauses'][:3]:
        print(f"\n  [{c['risk_label'].upper()}] {c['text'][:60]}...")
        print(f"  → {c['explanation']}")