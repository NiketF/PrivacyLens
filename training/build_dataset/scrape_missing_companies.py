# training/build_dataset/scrape_missing_companies.py
#
# Scrapes 5 missing Indian companies, cleans clauses, merges into
# dpdpa_clean_merged.csv → produces dpdpa_final.csv
#
# ALSO removes confirmed junk from existing dataset.
#
# Usage:
#   cd E:\Niket\Privacy-Policy-Analyzer
#   venv\Scripts\activate
#   python training/build_dataset/scrape_missing_companies.py
#
# Known scrape challenges documented inline per company.

import sys, os, re, csv, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import requests
from bs4 import BeautifulSoup
from src.ingestion.clause_segmentor import segment_into_clauses

# ── TARGET COMPANIES ─────────────────────────────────────────
# Each entry: (url, expected_difficulty, fallback_note)
MISSING_COMPANIES = {
    "swiggy": (
        "https://www.swiggy.com/privacy-policy",
        "MEDIUM",
        # Swiggy uses server-side rendering — usually scrapable with standard requests.
        # If fails: manually visit, Ctrl+A → Ctrl+C → paste into data/raw/swiggy.txt
    ),
    "flipkart": (
        "https://www.flipkart.com/pages/privacypolicy",
        "EASY",
        # Flipkart privacy page is static HTML — should work fine.
        # Backup URL: https://www.flipkart.com/pages/privacypolicy?otracker=privacy
    ),
    "cred": (
        "https://www.cred.club/privacy-policy",
        "HARD",
        # CRED uses heavy JavaScript (Next.js). requests will likely get a blank shell.
        # RECOMMENDATION: Use manual paste fallback (see below).
        # Backup: Try https://help.cred.club/hc/en-in/articles/360060396711-Privacy-Policy
    ),
    "byjus": (
        "https://byjus.com/privacy-policy/",
        "MEDIUM",
        # BYJU's policy is usually static. May have Cloudflare protection.
        # If blocked: try adding more browser-like headers (see HEADERS_ADVANCED below)
    ),
    "groww": (
        "https://groww.in/privacy-policy",
        "HARD",
        # Groww is a React SPA — main content loads via JS after page load.
        # requests will return a near-empty shell.
        # RECOMMENDATION: Manual paste or use Selenium (not included here to keep zero-dep).
        # Backup URL: https://groww.in/privacy  (sometimes static)
    ),
    "zomato": (
        "https://www.zomato.com/policies/privacy/",
        "EASY",
        # Zomato is a React SPA — main content loads via JS after page load.
        # requests will return a near-empty shell.
        # RECOMMENDATION: Manual paste or use Selenium (not included here to keep zero-dep).
        # Backup URL: https://zomato.com/privacy  (sometimes static)
    ),
}

# ── REQUEST HEADERS ──────────────────────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}

# ── PRIVACY KEYWORDS ─────────────────────────────────────────
PRIVACY_KW = [
    'data', 'information', 'personal', 'collect', 'share', 'use',
    'privacy', 'policy', 'right', 'consent', 'access', 'delete',
    'retain', 'store', 'process', 'disclose', 'transfer', 'security',
    'cookie', 'third part', 'partner', 'purpose', 'account',
    'grievance', 'officer', 'notify', 'breach', 'protect', 'location',
    'device', 'identifier', 'profile', 'marketing', 'tracking'
]

# ── JUNK DETECTION ────────────────────────────────────────────
JUNK_PATTERNS = [
    r'keyboard_arrow', r'sitemap', r'^\s*\d+\s*$',
    r'floor\s+\d|block[-\s]v|wing\s+[a-z]',
    r'(download|get it on|available on).*(app|store|play)',
    r'^(accept|ok|yes|no|back|next|close|submit|cancel)\s*$',
    r'all rights reserved',
    r'©\s*\d{4}',
    r'terms of use\s*$',
    r'cookie policy\s*$',
    r'^section \d+[\.\(]',                 # changelog headers like "Section 2 - Updated..."
    r'investment.*risk|securities.*market', # financial disclaimers (not privacy)
    r'cashback|buying power|margin trading',# marketing copy
    r'access denied',
    r"you don.t have permission",
]

DEFINITE_JUNK_WC_THRESHOLD = 8  # below this, always junk regardless


def is_junk(text: str, wc: int) -> tuple[bool, str]:
    """Returns (is_junk, reason)"""
    if wc < DEFINITE_JUNK_WC_THRESHOLD:
        return True, "TOO_SHORT"
    t = text.lower().strip()
    for pat in JUNK_PATTERNS:
        if re.search(pat, t):
            return True, f"PATTERN:{pat[:30]}"
    if text.count('\n') >= 2 and wc < 12:
        return True, "MULTILINE_ADDRESS_FRAGMENT"
    return False, ""


def is_privacy_relevant(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in PRIVACY_KW)


# ── SCRAPER ──────────────────────────────────────────────────
def scrape_url(url: str, company: str) -> tuple[str, str]:
    """
    Returns (text, status_message).
    status_message explains what happened — useful for debugging.
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)

        if resp.status_code == 403:
            return "", f"BLOCKED_403 — {company} is blocking scrapers. Use manual paste."
        if resp.status_code == 404:
            return "", f"NOT_FOUND_404 — URL may have changed for {company}."
        if resp.status_code != 200:
            return "", f"HTTP_{resp.status_code} — unexpected status for {company}."

        soup = BeautifulSoup(resp.text, 'html.parser')
        for tag in soup.find_all(['nav', 'header', 'footer', 'script', 'style', 'aside', 'noscript']):
            tag.decompose()

        # Try increasingly broad selectors
        content = (
            soup.find('main') or
            soup.find('article') or
            soup.find('div', {'id': re.compile(r'privacy|content|main|policy', re.I)}) or
            soup.find('div', {'class': re.compile(r'privacy|content|main|policy', re.I)}) or
            soup.find('body')
        )
        text = content.get_text(separator='\n', strip=True) if content else ""

        # Quality check
        privacy_hits = sum(1 for kw in PRIVACY_KW if kw in text.lower())
        if len(text) < 500:
            return "", f"TOO_SHORT ({len(text)} chars) — likely JS-rendered. Use manual paste for {company}."
        if privacy_hits < 3:
            return "", f"LOW_PRIVACY_SIGNAL (only {privacy_hits} privacy keywords) — may be wrong page for {company}."

        return text, f"OK — {len(text):,} chars, {privacy_hits} privacy keywords"

    except requests.exceptions.ConnectionError:
        return "", f"CONNECTION_ERROR — Check internet connection or {company} may be blocking."
    except requests.exceptions.Timeout:
        return "", f"TIMEOUT — {company} did not respond within 20 seconds."
    except Exception as e:
        return "", f"ERROR — {e}"


def load_manual_fallback(company: str) -> str:
    """
    If auto-scrape fails, check for manually saved text file.
    User should save policy text as data/raw/{company}.txt
    """
    path = f"data/raw/{company}.txt"
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            return f.read()
    return ""


# ── JUNK CLEANER FOR EXISTING DATASET ────────────────────────
def clean_existing_dataset(input_path: str) -> tuple[list, int]:
    """Load existing CSV and remove confirmed junk rows."""
    rows = []
    with open(input_path, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    clean_rows = []
    removed = 0
    for r in rows:
        wc = int(r['word_count'])
        junk, reason = is_junk(r['text'], wc)
        if junk:
            print(f"  REMOVING [{reason}] [{r['company']}]: {r['text'][:70]}")
            removed += 1
        else:
            clean_rows.append(r)

    return clean_rows, removed


# ── MAIN ──────────────────────────────────────────────────────
def main():
    os.makedirs("data/raw",     exist_ok=True)
    os.makedirs("data/labeled", exist_ok=True)

    INPUT_CSV  = "data/labeled/dpdpa_clean.csv"
    OUTPUT_CSV = "data/labeled/dpdpa_final.csv"

    if not os.path.exists(INPUT_CSV):
        print(f"ERROR: {INPUT_CSV} not found. Run build_dpdpa_dataset.py first.")
        return

    # ── STEP 1: Clean existing dataset ────────────────────────
    print("=" * 60)
    print("STEP 1: Cleaning existing dataset...")
    print("=" * 60)
    existing_rows, removed_count = clean_existing_dataset(INPUT_CSV)
    print(f"\nExisting dataset: {len(existing_rows) + removed_count} → {len(existing_rows)} rows ({removed_count} junk removed)")

    existing_texts = set()
    for r in existing_rows:
        existing_texts.add(' '.join(r['text'].lower().split()))

    # ── STEP 2: Scrape missing companies ──────────────────────
    print("\n" + "=" * 60)
    print("STEP 2: Scraping missing companies...")
    print("=" * 60)

    scrape_report = {}
    new_rows      = []

    for company, (url, difficulty, *_) in MISSING_COMPANIES.items():
        print(f"\n[{difficulty}] Scraping {company.upper()} from {url}")

        text, status = scrape_url(url, company)
        print(f"  Status: {status}")

        # Try manual fallback if auto-scrape failed
        if not text:
            text = load_manual_fallback(company)
            if text:
                print(f"  Using manual fallback: data/raw/{company}.txt ({len(text):,} chars)")

        if not text:
            scrape_report[company] = {
                "status":  "FAILED",
                "reason":  status,
                "clauses": 0,
                "advice":  f"Manually visit {url}, Ctrl+A, Ctrl+C, paste into data/raw/{company}.txt, re-run script."
            }
            time.sleep(1)
            continue

        # Save raw text
        raw_path = f"data/raw/{company}.txt"
        with open(raw_path, 'w', encoding='utf-8') as f:
            f.write(text)

        # Segment into clauses
        clauses   = segment_into_clauses(text)
        added     = 0
        skipped   = 0

        for clause in clauses:
            t  = clause['text']
            wc = clause['word_count']
            norm = ' '.join(t.lower().split())

            # Skip duplicates
            if norm in existing_texts:
                skipped += 1
                continue

            # Skip junk
            junk, reason = is_junk(t, wc)
            if junk:
                skipped += 1
                continue

            # Skip non-privacy content
            if not is_privacy_relevant(t):
                skipped += 1
                continue

            new_rows.append({
                "clause_id":     f"{company}_{clause['clause_id']}",
                "company":       company,
                "text":          t,
                "word_count":    wc,
                "category":      "",
                "risk_label":    "",
                "dpdpa_section": "",
                "notes":         ""
            })
            existing_texts.add(norm)
            added += 1

        scrape_report[company] = {
            "status":  "OK",
            "reason":  status,
            "clauses": added,
            "skipped": skipped,
        }
        print(f"  Added: {added} clauses | Skipped: {skipped}")
        time.sleep(2)

    # ── STEP 3: Merge and write final CSV ─────────────────────
    print("\n" + "=" * 60)
    print("STEP 3: Writing final dataset...")
    print("=" * 60)

    all_rows   = existing_rows + new_rows
    fieldnames = ["clause_id", "company", "text", "word_count",
                  "category", "risk_label", "dpdpa_section", "notes"]

    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    # ── STEP 4: Report ─────────────────────────────────────────
    from collections import Counter
    company_counts = Counter(r['company'] for r in all_rows)

    print(f"\nFinal dataset: {len(all_rows)} clauses")
    print(f"\nBy company:")
    for co, cnt in sorted(company_counts.items(), key=lambda x: -x[1]):
        status = "✅" if cnt >= 50 else "⚠️" if cnt >= 15 else "❌"
        print(f"  {status} {co:15s}: {cnt:4d} clauses")

    print(f"\nScrape report for new companies:")
    for company, report in scrape_report.items():
        st = report['status']
        icon = "✅" if st == "OK" else "❌"
        print(f"\n  {icon} {company.upper()}")
        print(f"     Status  : {st}")
        print(f"     Detail  : {report['reason']}")
        if st == "OK":
            print(f"     Clauses : {report['clauses']} added, {report.get('skipped',0)} skipped")
        else:
            print(f"     Fix     : {report.get('advice','')}")

    # ── STEP 5: Dataset sufficiency assessment ─────────────────
    print("\n" + "=" * 60)
    print("DATASET SUFFICIENCY ASSESSMENT")
    print("=" * 60)
    assess_dataset(all_rows, scrape_report)

    print(f"\nSaved to: {OUTPUT_CSV}")


def assess_dataset(rows: list, scrape_report: dict):
    """
    Honest assessment of whether this dataset is sufficient
    for Legal-BERT fine-tuning and research paper.
    """
    from collections import Counter
    n = len(rows)
    companies = Counter(r['company'] for r in rows)
    n_companies = len(companies)

    # Legal-BERT fine-tuning needs: minimum 300, good at 500+, strong at 1000+
    # Research paper corpus: minimum 5 companies, good at 8+

    print(f"\nDataset size       : {n} clauses")
    print(f"Unique companies   : {n_companies}")

    print("\n--- For Legal-BERT fine-tuning ---")
    if n >= 800:
        print(f"  ✅ SUFFICIENT ({n} clauses) — strong fine-tuning signal")
    elif n >= 500:
        print(f"  ✅ SUFFICIENT ({n} clauses) — good for fine-tuning")
    elif n >= 300:
        print(f"  ⚠️  MARGINAL ({n} clauses) — will work but expect higher variance")
        print(f"     Recommendation: annotate all, then augment with OPP-115 transfer")
    else:
        print(f"  ❌ INSUFFICIENT ({n} clauses) — need at least 300 annotated clauses")

    print("\n--- For research paper (FIRE 2025 / arXiv) ---")
    if n_companies >= 8:
        print(f"  ✅ COMPANY DIVERSITY: {n_companies} companies — good for generalizability claim")
    elif n_companies >= 5:
        print(f"  ⚠️  COMPANY DIVERSITY: {n_companies} companies — acceptable, mention as limitation")
    else:
        print(f"  ❌ COMPANY DIVERSITY: only {n_companies} companies — reviewers will question generalizability")

    # Check sector coverage
    fintech   = {'phonepe','paytm','razorpay','groww','cred'}
    ecomm     = {'flipkart','meesho','nykaa','bigbasket'}
    food      = {'zomato','swiggy'}
    health    = {'practo','byjus'}
    govt      = {'uidai','digilocker'}
    present   = set(companies.keys())

    covered_sectors = []
    if present & fintech:   covered_sectors.append(f"Fintech ({', '.join(present & fintech)})")
    if present & ecomm:     covered_sectors.append(f"E-commerce ({', '.join(present & ecomm)})")
    if present & food:      covered_sectors.append(f"Food-tech ({', '.join(present & food)})")
    if present & health:    covered_sectors.append(f"Edtech/Health ({', '.join(present & health)})")
    if present & govt:      covered_sectors.append(f"Government ({', '.join(present & govt)})")

    print(f"\n--- Sector coverage ---")
    for s in covered_sectors:
        print(f"  ✅ {s}")

    missing_sectors = []
    if not (present & fintech):   missing_sectors.append("Fintech (add PhonePe/Razorpay manually if needed)")
    if not (present & food):      missing_sectors.append("Food-tech (Swiggy/Zomato)")
    if not (present & govt):      missing_sectors.append("Government (UIDAI)")
    for s in missing_sectors:
        print(f"  ❌ Missing: {s}")

    print("\n--- Bottom line ---")
    if n >= 500 and n_companies >= 6 and len(covered_sectors) >= 3:
        print("  ✅ READY TO ANNOTATE AND TRAIN")
        print("  Proceed to: python training/build_dataset/auto_annotate.py")
    elif n >= 300:
        print("  ⚠️  PROCEED WITH ANNOTATION but note dataset size as limitation in paper")
        print("  This is sufficient for initial results — expand after BERT baseline")
    else:
        print("  ❌ ADD MORE DATA before annotation")
        print("  Priority: manually paste Swiggy, CRED, Groww policies")
        print("  Each policy adds ~60-120 clauses")


if __name__ == "__main__":
    main()