# src/models/simplifier.py

import re
import spacy

# Load once at module level — not per call
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Run: python -m spacy download en_core_web_sm")
    raise

# ── DATA TYPE KEYWORDS ───────────────────────────────────────
# spaCy won't catch privacy-specific terms — we handle them manually
DATA_TYPES = [
    "location", "gps", "email", "name", "phone", "address",
    "payment", "credit card", "financial", "biometric",
    "fingerprint", "facial", "health", "medical", "browsing",
    "search history", "device", "ip address", "cookies",
    "photos", "contacts", "messages", "voice", "camera",
    "personal information", "personal data", "user data",
    "sensitive data", "private data", "account information",
    "usage data", "behavioral data", "inferred data",
    "demographic", "age", "gender", "religion", "political",
    "sexual orientation", "racial", "ethnic"
]

RECIPIENT_TERMS = [
    "advertising partners", "ad partners", "ad networks",
    "marketing partners", "marketing firms", "data brokers",
    "analytics companies", "analytics providers",
    "third parties", "third-party", "affiliates",
    "subsidiaries", "business partners", "service providers",
    "trusted partners", "selected partners", "vendors",
    "contractors", "law enforcement", "government",
    "courts", "regulators", "other companies",
    "partner companies", "group companies"
]

ACTION_MAP = {
    "sell":       "sells",
    "share":      "shares",
    "transfer":   "transfers",
    "disclose":   "discloses",
    "distribute": "distributes",
    "provide":    "provides",
    "send":       "sends",
    "give":       "gives",
    "collect":    "collects",
    "gather":     "gathers",
    "store":      "stores",
    "retain":     "retains",
    "keep":       "keeps",
    "process":    "processes",
    "use":        "uses",
    "access":     "accesses",
    "monitor":    "monitors",
    "track":      "tracks",
    "record":     "records",
}


def extract_entities(text: str) -> dict:
    """
    Extract key privacy entities from clause text.
    Returns dict with data_types, recipients, actions found.
    """
    text_lower = text.lower()
    doc        = nlp(text)

    # Extract data types mentioned
    found_data = [dt for dt in DATA_TYPES if dt in text_lower]

    # Extract recipients mentioned
    found_recipients = [rt for rt in RECIPIENT_TERMS if rt in text_lower]

    # Extract actions using spaCy dependency parsing
    found_actions = []
    for token in doc:
        if token.lemma_.lower() in ACTION_MAP:
            found_actions.append(ACTION_MAP[token.lemma_.lower()])

    # Extract named entities (companies, organizations)
    named_orgs = [
        ent.text for ent in doc.ents
        if ent.label_ in ("ORG", "GPE", "PERSON")
        and len(ent.text) > 2
    ]

    return {
        "data_types":  found_data[:3],        # top 3 most relevant
        "recipients":  found_recipients[:2],   # top 2 recipients
        "actions":     found_actions[:2],      # top 2 actions
        "named_orgs":  named_orgs[:2]
    }


def _format_list(items: list) -> str:
    """Format list naturally: 'a, b and c' or 'a and b' or 'a'"""
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def simplify_clause(
    clause_text: str,
    risk_label:  str,
    category:    str = "general"
) -> str:
    """
    Generate plain-English explanation using spaCy entity extraction.
    Falls back to honest general explanation when entities not found.
    Zero API calls. Runs in under 50ms.
    """
    entities   = extract_entities(clause_text)
    has_data   = bool(entities['data_types'])
    has_recip  = bool(entities['recipients'])
    has_action = bool(entities['actions'])

    # If specific entities found — build targeted explanation
    if has_data or has_recip or has_action:
        return _build_explanation(
            clause_text, risk_label, category,
            _format_list(entities['data_types']),
            _format_list(entities['recipients']),
            _format_list(entities['actions']),
            entities
        )

    # If nothing found — honest fallback
    # Never fabricates specific claims about what it cannot identify
    return _honest_fallback(clause_text, risk_label, category)  
def _honest_fallback(
    clause_text: str,
    risk_label:  str,
    category:    str
) -> str:
    """
    Used when entity extraction finds nothing specific.
    Always accurate — never fabricates claims.
    Handles novel language, unusual phrasing, anything templates miss.
    """
    cat_plain = category.replace('_', ' ')

    if risk_label == "red":
        return (
            f"This {cat_plain} clause contains language that may not be "
            f"in your best interest as a user. "
            f"The specific terms used here give the company significant "
            f"control — read this clause carefully before agreeing."
        )
    elif risk_label == "green":
        return (
            f"This {cat_plain} clause works in your favor as a user. "
            f"It places a clear obligation on the company to protect "
            f"your interests."
        )
    else:
        return (
            f"This {cat_plain} clause uses language whose implications "
            f"are not entirely clear. "
            f"When privacy clauses are ambiguous, they typically give "
            f"the company more flexibility than users expect."
        )

def _build_explanation(
    clause_text:   str,
    risk_label:    str,
    category:      str,
    data_str:      str,
    recipient_str: str,
    action_str:    str,
    entities:      dict
) -> str:
    """
    Build a specific, accurate explanation using extracted entities.
    Falls back gracefully when entities are not found.
    """

    # ── RED CLAUSES ──────────────────────────────────────────
    if risk_label == "red":

        if category == "data_sharing":
            if data_str and recipient_str:
                return (
                    f"This company {action_str or 'shares'} your {data_str} "
                    f"with {recipient_str}. "
                    f"You may not be able to stop this — check their privacy settings for an opt-out option."
                )
            elif recipient_str:
                return (
                    f"This company shares your personal data with {recipient_str}. "
                    f"This may include information you did not knowingly provide for this purpose."
                )
            else:
                return (
                    "This company can share your personal data with outside companies. "
                    "The policy does not clearly specify who receives your data or why."
                )

        elif category == "data_collection":
            if data_str:
                return (
                    f"This company collects your {data_str}. "
                    f"This type of data is sensitive and could be used for profiling or targeted advertising."
                )
            else:
                return (
                    "This company collects personal information about you beyond what is necessary. "
                    "Review your account settings to limit what data is gathered."
                )

        elif category == "user_rights":
            return (
                "This clause restricts your ability to control your own data. "
                "You may have limited or no ability to delete, correct, or opt out of certain data practices."
            )

        elif category == "data_retention":
            return (
                "This company keeps your data for an extended or undefined period of time. "
                "Your information may persist even after you delete your account."
            )

        elif category == "policy_changes":
            return (
                "This company can change its privacy rules without asking your permission first. "
                "By continuing to use the service, you automatically agree to any new terms."
            )

        elif category == "legal_jurisdiction":
            return (
                "This clause removes your right to take the company to court. "
                "If a dispute arises, you may be forced into private arbitration with limited options."
            )

        elif category == "security":
            return (
                "This company does not guarantee the security of your personal data. "
                "In the event of a data breach, you may have limited recourse."
            )

        elif category == "childrens_data":
            return (
                "This clause may allow collection of data from minors without proper parental consent. "
                "If you have children using this service, review this carefully."
            )

        else:
            return (
                "This clause may not be in your best interest as a user. "
                "Read it carefully — it gives the company significant control over your data."
            )

    # ── GREEN CLAUSES ────────────────────────────────────────
    elif risk_label == "green":

        if category == "data_sharing":
            return (
                "This company does not share your personal data with advertisers or unrelated third parties. "
                "This is a user-friendly privacy practice."
            )

        elif category == "data_collection":
            if data_str:
                return (
                    f"This company only collects your {data_str} when necessary for the service. "
                    f"Your data collection is transparent and limited."
                )
            return (
                "This company limits data collection to what is necessary for the service. "
                "This is a positive privacy practice."
            )

        elif category == "user_rights":
            return (
                "You have clear rights over your personal data. "
                "You can request access, correction, or deletion of your information by contacting the company."
            )

        elif category == "data_retention":
            return (
                "Your data will be deleted within a defined timeframe after you stop using the service. "
                "The company does not hold your information longer than necessary."
            )

        elif category == "policy_changes":
            return (
                "This company will notify you before making any changes to their privacy policy. "
                "You will have an opportunity to review changes before they take effect."
            )

        elif category == "security":
            return (
                "This company uses strong technical measures to protect your personal data. "
                "This is a positive commitment that reduces the risk of unauthorized access."
            )

        else:
            return (
                "This clause protects your privacy rights as a user. "
                "It places a clear obligation on the company in your favor."
            )

    # ── GRAY CLAUSES ─────────────────────────────────────────
    else:
        if category == "data_sharing":
            if recipient_str:
                return (
                    f"This clause mentions sharing data with {recipient_str} "
                    f"but does not clearly specify for what purpose. "
                    f"Vague sharing language often means broader data use than you might expect."
                )
            return (
                "This clause is unclear about who your data is shared with or why. "
                "When sharing language is vague, assume your data reaches more parties than stated."
            )

        elif category == "data_collection":
            if data_str:
                return (
                    f"This clause mentions collecting {data_str} but is unclear about "
                    f"exactly how it will be used. "
                    f"When collection scope is vague, assume more data is gathered than you expect."
                )
            return (
                "This clause is vague about what personal data is collected and why. "
                "Consider what information you share with this service."
            )

        elif category == "legal_jurisdiction":
            return (
                "This clause defines the legal framework that governs disputes. "
                "Its impact on your rights depends on where you are located and which laws apply."
            )

        elif category == "data_retention":
            return (
                "This clause does not clearly state how long your data is kept. "
                "Undefined retention periods typically mean data is stored longer than necessary."
            )

        elif category == "policy_changes":
            return (
                "This clause is unclear about how you will be informed of privacy policy changes. "
                "Check whether you have agreed to receive notifications about future updates."
            )

        else:
            return (
                "This clause uses language that makes its exact meaning unclear. "
                "When a privacy clause is ambiguous, it typically gives the company more flexibility."
            )


# Keep this as fallback for direct imports from other files
def _rule_based_simplification(
    clause_text: str,
    risk_label:  str,
    category:    str
) -> str:
    """Alias for simplify_clause — maintains backward compatibility."""
    return simplify_clause(clause_text, risk_label, category)


if __name__ == "__main__":
    print("Testing local spaCy-based simplifier...\n")

    test_cases = [
        ("We may share your location data and browsing history with advertising partners without your explicit consent.", "red",   "data_sharing"),
        ("We sell aggregated user profiles to third-party data brokers for marketing purposes.",                         "red",   "data_sharing"),
        ("You have the right to request deletion of your account and all associated data within 30 days.",               "green", "user_rights"),
        ("We collect your precise GPS location continuously when the app is running in the background.",                 "red",   "data_collection"),
        ("We will never share your personal information with any third party without your explicit consent.",            "green", "data_sharing"),
        ("We may retain certain information at our sole discretion for as long as we deem necessary.",                   "gray",  "data_retention"),
        ("Any disputes shall be resolved through binding arbitration in the state of Karnataka.",                        "red",   "legal_jurisdiction"),
        ("We use SSL encryption and conduct regular security audits to protect your data.",                              "green", "security"),
        ("We may share your data with certain trusted partners for various purposes.",                                   "gray",  "data_sharing"),
        ("This policy may change from time to time — continued use means you accept the new terms.",                    "red",   "policy_changes"),
    ]

    import time
    start = time.time()

    print("=" * 70)
    for clause, risk, cat in test_cases:
        expl = simplify_clause(clause, risk, cat)
        print(f"\n[{risk.upper()}] [{cat}]")
        print(f"Clause:      {clause[:75]}...")
        print(f"Explanation: {expl}")

    elapsed = time.time() - start
    print(f"\n{'='*70}")
    print(f"Processed {len(test_cases)} clauses in {elapsed:.3f} seconds")
    print(f"Average: {elapsed/len(test_cases)*1000:.1f}ms per clause")
