# training/build_dataset/clean_dataset.py
# Cleans the raw dpdpa_to_annotate.csv — removes junk, keeps real policy clauses

import csv
import re

INPUT  = "data/labeled/dpdpa_to_annotate.csv"
OUTPUT = "data/labeled/dpdpa_clean.csv"

# Patterns that indicate junk — marketing copy, navigation, UI text
JUNK_PATTERNS = [
    r'^\d+x\d+',                          # "24x7"
    r'^(download|sign up|login|register)', # CTAs
    r'cashback|offer|discount|deal',       # promotional
    r'upi|net banking|credit card offer',  # payment promos
    r'^\d+[\+\-\*\/]',                    # numbers/math
    r'^(home|about|contact|faq|help)',     # navigation
    r'click here|tap here|learn more',     # UI prompts
    r'app store|google play|download now', # app store
    r'follow us|social media|instagram|twitter|facebook',
    r'copyright|all rights reserved',
    r'^\s*[-–—•]\s*$',                    # lone bullets
    r'scheme|cashback|reward point',       # loyalty programs
]

JUNK_COMPILED = [re.compile(p, re.IGNORECASE) for p in JUNK_PATTERNS]

# Words that MUST appear for it to be a real privacy clause
PRIVACY_SIGNALS = [
    'data', 'information', 'personal', 'privacy', 'collect',
    'share', 'store', 'process', 'user', 'account', 'access',
    'security', 'consent', 'right', 'delete', 'retain', 'third',
    'policy', 'purpose', 'disclose', 'transfer', 'protect',
    'cookie', 'device', 'location', 'contact', 'identity',
    'profile', 'service', 'platform', 'agreement', 'terms'
]

def is_junk(text: str, word_count: int) -> bool:
    """Returns True if this clause should be removed."""
    text_lower = text.lower().strip()

    # Too short to be a policy clause
    if word_count < 10:
        return True

    # Too long — probably merged paragraphs
    if word_count > 200:
        return True

    # Matches junk patterns
    for pattern in JUNK_COMPILED:
        if pattern.search(text_lower):
            return True

    # No privacy-related words at all
    if not any(signal in text_lower for signal in PRIVACY_SIGNALS):
        return True

    return False

def clean_csv():
    with open(INPUT, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows   = list(reader)

    print(f"Input:  {len(rows)} clauses")

    kept    = []
    removed = []

    for row in rows:
        text       = row['text'].strip()
        word_count = int(row['word_count']) if row['word_count'].isdigit() else len(text.split())

        if is_junk(text, word_count):
            removed.append(row)
        else:
            kept.append(row)

    print(f"Removed: {len(removed)} junk clauses")
    print(f"Kept:    {len(kept)} valid policy clauses")

    # Company distribution after cleaning
    from collections import Counter
    companies = Counter(r['company'] for r in kept)
    print(f"\nClauses per company after cleaning:")
    for company, count in sorted(companies.items(), key=lambda x: -x[1]):
        print(f"  {company}: {count}")

    # Write cleaned CSV
    fieldnames = ['clause_id','company','text','word_count',
                  'category','risk_label','dpdpa_section','notes']

    with open(OUTPUT, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(kept)

    print(f"\nSaved cleaned dataset to: {OUTPUT}")
    print(f"\nSample valid clauses:")
    for row in kept[:5]:
        print(f"  [{row['company']}] {row['text'][:90]}...")

if __name__ == "__main__":
    clean_csv()