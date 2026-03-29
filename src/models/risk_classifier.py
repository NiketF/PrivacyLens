# src/models/risk_classifier.py

import re
from typing import Tuple

# ── NEGATION WORDS ───────────────────────────────────────────
NEGATION_WORDS = [
    'never', 'not', 'no ', "won't", "don't", "doesn't",
    "will not", "do not", "does not", "cannot", "can't",
    "without your consent", "only with your consent",
    "shall not", "may not", "must not"
]

# ── EXPANDED RISK RULES ──────────────────────────────────────
RISK_RULES = {

    "data_collection": {
        "red": [
            "biometric", "facial recognition", "precise location",
            "real-time location", "exact location", "gps",
            "without consent", "without your permission",
            "infer", "inferred", "emotional state", "mood",
            "microphone", "camera access", "fingerprint",
            "behavioral profiling", "track your", "monitor your",
            "background location", "continuously collect",
            "sensitive personal", "special category",
            "health data", "financial data", "political",
            "religious", "sexual orientation", "racial",
            "unique identifier", "device fingerprint",
            "cross-device tracking", "third-party tracking",
            "without limitation", "any information",
            "all information you provide"
        ],
        "green": [
            "only what you provide", "minimum necessary",
            "with your consent", "with your explicit consent",
            "anonymized", "aggregated only", "you choose to provide",
            "voluntarily provide", "upon your request",
            "you can choose not to", "optional",
            "we limit collection", "data minimization",
            "necessary for the service", "strictly necessary"
        ]
    },

    "data_sharing": {
        "red": [
            "sell", "sold", "selling", "monetize", "monetise",
            "advertising partner", "ad partner", "ad network",
            "data broker", "marketing partner", "marketing firm",
            "without your consent", "without notice",
            "without your explicit consent",
            "may share", "reserve the right to share",
            "may disclose", "may transfer",
            "affiliated compan", "affiliate", "subsidiaries",
            "third part", "selected partners", "trusted partners",
            "business partners", "service ecosystem",
            "growth partners", "collaborate with",
            "further distribute", "wider audience",
            "commercial purposes", "revenue sharing",
            "joint venture", "co-branded", "co-marketing",
            "analytics partner", "measurement partner",
            "social media partner", "without restriction"
        ],
        "green": [
            "will not sell", "never sell", "do not sell",
            "never share", "will not share", "do not share",
            "only with your consent", "only when required by law",
            "law enforcement only", "legal obligation only",
            "strictly for service delivery", "service providers only",
            "under strict confidentiality", "bound by confidentiality",
            "gdpr compliant", "dpdpa compliant",
            "you can opt out", "opt-out available"
        ]
    },

    "user_rights": {
        "red": [
            "no right to", "cannot delete", "cannot opt out",
            "sole discretion", "we may refuse",
            "waive your right", "waive the right",
            "arbitration", "class action",
            "continued use constitutes acceptance",
            "by continuing to use", "deemed to have accepted",
            "constitutes your acceptance", "accept any changes",
            "no refund", "non-refundable",
            "irrevocable", "irrevocably grant",
            "perpetual license", "worldwide license",
            "sublicense", "we own", "we retain all rights",
            "you waive", "binding on you"
        ],
        "green": [
            "you may delete", "right to erasure",
            "right to access", "right to deletion",
            "opt out", "withdraw consent",
            "data portability", "right to correct",
            "you can request", "right to request",
            "request deletion", "within 30 days",
            "we will respond", "lodge a complaint",
            "data protection officer", "grievance officer",
            "grievance redressal", "contact our privacy",
            "you retain ownership", "you own your content",
            "your data belongs to you", "right to erasure",
            "right to restrict", "right to object",
            "right to be forgotten", "dpdpa", "gdpr rights"
        ]
    },

    "data_retention": {
        "red": [
            "indefinitely", "may retain", "retain indefinitely",
            "after deletion", "after account deletion",
            "no fixed period", "as long as we deem",
            "as long as necessary", "sole discretion",
            "backup copies may persist", "archived copies",
            "legal hold", "retain for business purposes",
            "as long as permitted by law",
            "may be retained", "could be retained",
            "we keep", "stored indefinitely"
        ],
        "green": [
            "deleted within 30 days", "deleted within 90 days",
            "deleted upon request", "specific retention period",
            "defined retention", "automatically deleted",
            "limited retention", "data minimization",
            "we do not retain", "immediately deleted",
            "no longer than necessary", "retention schedule"
        ]
    },

    "security": {
        "red": [
            "cannot guarantee", "no warranty", "reasonable efforts",
            "as-is", "not responsible for breach",
            "not liable for", "cannot ensure",
            "no guarantee of security", "best efforts",
            "commercially reasonable", "we are not responsible"
        ],
        "green": [
            "ssl", "tls", "encryption", "two-factor",
            "multi-factor", "security audit", "penetration test",
            "iso 27001", "soc 2", "regular security review",
            "industry standard", "aes-256", "end-to-end",
            "data breach notification", "notify you within",
            "breach notification", "72 hours", "incident response"
        ]
    },

    "policy_changes": {
        "red": [
            "without notice", "without prior notice",
            "at any time", "at our discretion",
            "sole discretion", "continued use constitutes acceptance",
            "by continuing to use", "deemed to have accepted",
            "constitutes your acceptance", "accept any changes",
            "effective immediately", "without your consent",
            "unilaterally", "reserve the right to modify",
            "subject to change without notice"
        ],
        "green": [
            "30 days notice", "15 days notice", "advance notice",
            "notify you", "email notification", "prominent notice",
            "your consent required", "explicit consent",
            "will inform you", "we will alert you",
            "material changes", "you will be notified"
        ]
    },

    "childrens_data": {
        "red": [
            "may collect children", "no age verification",
            "without parental consent", "collect from minors",
            "children under 18", "children under 13",
            "knowingly collect from children",
            "not verify age"
        ],
        "green": [
            "not directed to children", "do not knowingly collect",
            "parental consent required", "coppa compliant",
            "children's privacy", "age verification",
            "parental consent", "guardian consent",
            "18 years or older", "13 years or older"
        ]
    },

    "legal_jurisdiction": {
        "red": [
            "binding arbitration", "waive right to sue",
            "class action waiver", "no jury trial",
            "waive your right", "you waive", "arbitration",
            "waive the right", "right to participate",
            "mandatory arbitration", "final and binding",
            "no class action", "individual basis only",
            "governing law of", "exclusive jurisdiction"
        ],
        "green": [
            "dpdpa", "gdpr", "ccpa", "pdpb",
            "your local law applies",
            "applicable data protection law",
            "your statutory rights",
            "consumer protection law"
        ]
    }
}

# ── VAGUENESS INDICATORS ─────────────────────────────────────
HEDGE_WORDS = [
    'may', 'might', 'could', 'certain', 'select', 'appropriate',
    'reasonable', 'relevant', 'necessary', 'sole discretion',
    'as we deem', 'as appropriate', 'in our judgment',
    'reserve the right', 'at our discretion', 'from time to time',
    'in some cases', 'under certain circumstances',
    'where applicable', 'as required', 'as needed',
    'various', 'several', 'some', 'other purposes'
]

VAGUE_ENTITIES = [
    'third parties', 'affiliates', 'partners', 'vendors',
    'service providers', 'selected companies', 'trusted partners',
    'certain companies', 'business partners', 'other companies',
    'group companies', 'related entities', 'associated companies',
    'contractors', 'agents', 'representatives'
]


def _has_negation_before_keyword(text_lower: str, keyword: str) -> bool:
    idx = text_lower.find(keyword)
    if idx == -1:
        return False
    prefix = text_lower[max(0, idx - 80): idx]
    return any(neg in prefix for neg in NEGATION_WORDS)


def classify_risk(text: str, category: str) -> Tuple[str, float]:
    """
    Classify clause as red / green / gray.
    Negation-aware — handles 'we will never sell' correctly.
    Returns: (label, confidence)
    """
    text_lower = text.lower()
    rules      = RISK_RULES.get(category, {})

    red_hits   = 0
    green_hits = 0

    for kw in rules.get("red", []):
        if kw in text_lower:
            if _has_negation_before_keyword(text_lower, kw):
                green_hits += 1   # negated red = protective signal
            else:
                red_hits += 1

    for kw in rules.get("green", []):
        if kw in text_lower:
            green_hits += 1

    if red_hits > green_hits:
        confidence = min(0.60 + red_hits * 0.06, 0.95)
        return "red", round(confidence, 3)
    elif green_hits > 0:
        confidence = min(0.60 + green_hits * 0.06, 0.95)
        return "green", round(confidence, 3)
    else:
        # No keyword match — use category-based default
        # Some categories are inherently higher risk when ambiguous
        high_risk_default = ["legal_jurisdiction", "policy_changes", "data_retention"]
        if category in high_risk_default:
            return "gray", 0.55
        return "gray", 0.52


def compute_vagueness(text: str) -> float:
    """Score how vague a clause is — 0.0 (explicit) to 1.0 (maximally vague)."""
    text_lower = text.lower()
    words      = text_lower.split()
    total      = max(len(words), 1)

    hedge_count  = sum(1 for hw in HEDGE_WORDS   if hw in text_lower)
    entity_count = sum(1 for ve in VAGUE_ENTITIES if ve in text_lower)

    passive_patterns = [r'\b(is|are|was|were|be|been|being)\s+\w+ed\b']
    passive_count = sum(len(re.findall(p, text_lower)) for p in passive_patterns)

    vagueness = (
        (hedge_count  * 0.12) +
        (entity_count * 0.18) +
        (passive_count * 0.04)
    )
    return round(min(vagueness, 1.0), 3)


def get_risk_display(risk_label: str, vagueness: float) -> str:
    icons = {"red": "🔴", "green": "🟢", "gray": "🟡"}
    icon  = icons.get(risk_label, "⚪")
    vague = " ⚠️ (vague)" if vagueness > 0.35 else ""
    return f"{icon} {risk_label.upper()}{vague}"


if __name__ == "__main__":
    tests = [
        ("We may share your personal data with advertising partners.", "data_sharing"),
        ("We will never sell your personal information to third parties.", "data_sharing"),
        ("We may retain certain information indefinitely at our sole discretion.", "data_retention"),
        ("You have the right to request deletion of your data within 30 days.", "user_rights"),
        ("We use SSL encryption and conduct regular security audits.", "security"),
        ("By continuing to use our service you accept any changes to this policy.", "policy_changes"),
        ("We collect precise GPS location data continuously when the app is open.", "data_collection"),
        ("We only collect information you voluntarily provide to us.", "data_collection"),
        ("Any disputes shall be resolved through binding arbitration.", "legal_jurisdiction"),
        ("This policy may change from time to time at our sole discretion.", "policy_changes"),
        ("We share your data with certain trusted partners for various purposes.", "data_sharing"),
    ]

    print("RISK CLASSIFICATION TEST")
    print("=" * 70)
    for text, cat in tests:
        risk, conf  = classify_risk(text, cat)
        vague       = compute_vagueness(text)
        display     = get_risk_display(risk, vague)
        print(f"\nText:     {text[:70]}")
        print(f"Category: {cat}")
        print(f"Risk:     {display} | conf: {conf} | vagueness: {vague}")