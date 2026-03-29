# src/ingestion/clause_segmentor.py

import re
import spacy
from typing import List, Dict

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Run: python -m spacy download en_core_web_sm")
    raise


def clean_policy_text(text: str) -> str:
    """Aggressively clean policy text — remove all HTML, normalize whitespace."""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Remove HTML entities
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&quot;', '"', text)
    text = re.sub(r'&#\d+;', ' ', text)
    text = re.sub(r'&[a-zA-Z]+;', ' ', text)
    # Remove CSS class remnants
    text = re.sub(r'\{[^}]*\}', ' ', text)
    # Remove URLs
    text = re.sub(r'https?://\S+', ' ', text)
    # Remove email addresses (keep the text around them)
    text = re.sub(r'\S+@\S+\.\S+', '[email]', text)
    # Normalize whitespace
    text = re.sub(r'\t', ' ', text)
    text = re.sub(r' {2,}', ' ', text)
    # Normalize line endings
    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(r'\r', '\n', text)
    return text.strip()


def is_junk_line(text: str) -> bool:
    """
    Returns True if this line should be skipped.
    Catches headings, navigation items, cookie banners, etc.
    """
    text = text.strip()

    # Too short
    if len(text) < 20:
        return True

    # All caps heading
    if text.isupper() and len(text) < 100:
        return True

    # Looks like a heading (short, no period/comma, title case)
    words = text.split()
    if len(words) <= 5:
        return True

    # Numbered section header like "1." or "1.1" alone
    if re.match(r'^\d+(\.\d+)*\.?\s*$', text):
        return True

    # Cookie / navigation fragments
    junk_patterns = [
        r'^(accept|decline|close|ok|yes|no|continue|back|next|submit)$',
        r'^\d+$',                          # just a number
        r'^[\W]+$',                        # only punctuation/symbols
        r'©', r'cookie policy', r'terms of use',
        r'all rights reserved',
    ]
    text_lower = text.lower()
    for pattern in junk_patterns:
        if re.search(pattern, text_lower):
            return True

    return False


def segment_into_clauses(text: str) -> List[Dict]:
    """
    Split any privacy policy text into individual clauses.
    Handles: double newline, single newline, no newlines.
    Aggressively filters junk lines.
    """

    # Clean first
    text = clean_policy_text(text)

    # Detect format and choose splitting strategy
    double_nl = text.count('\n\n')
    single_nl = text.count('\n')

    if double_nl >= 3:
        raw_chunks = re.split(r'\n\n+', text)
    elif single_nl >= 3:
        raw_chunks = text.split('\n')
    else:
        doc = nlp(text[:500000])
        raw_chunks = [sent.text for sent in doc.sents]

    # Process each chunk
    all_clauses = []
    for chunk in raw_chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        if is_junk_line(chunk):
            continue

        words = len(chunk.split())

        # Long paragraph — split into sentences
        if words > 70:
            doc = nlp(chunk)
            for sent in doc.sents:
                s = sent.text.strip()
                if len(s.split()) >= 6 and not is_junk_line(s):
                    all_clauses.append(s)
        else:
            all_clauses.append(chunk)

    # If spaCy sentence splitting gave only 1, force split
    if len(all_clauses) <= 1 and text:
        doc = nlp(text[:500000])
        all_clauses = [
            s.text.strip() for s in doc.sents
            if len(s.text.split()) >= 6 and not is_junk_line(s.text.strip())
        ]

    # Final deduplication — remove exact duplicates
    seen      = set()
    deduped   = []
    for clause in all_clauses:
        normalized = ' '.join(clause.lower().split())
        if normalized not in seen:
            seen.add(normalized)
            deduped.append(clause)

    # Structure output
    result = []
    for i, clause in enumerate(deduped):
        result.append({
            "clause_id":  i,
            "text":       clause.strip(),
            "word_count": len(clause.split())
        })

    return result


if __name__ == "__main__":
    print("TEST 1 — Single newline")
    t1 = "We collect your name and email.\nWe share your data with advertisers.\nYou can delete your account.\nWe may change this policy at any time without notice."
    r1 = segment_into_clauses(t1)
    print(f"Clauses: {len(r1)}")
    for c in r1: print(f"  [{c['clause_id']}] {c['text']}")

    print("\nTEST 2 — Double newline")
    t2 = "We collect your name and email.\n\nWe share your data with advertisers.\n\nYou can delete your account.\n\nWe may change this policy at any time."
    r2 = segment_into_clauses(t2)
    print(f"Clauses: {len(r2)}")
    for c in r2: print(f"  [{c['clause_id']}] {c['text']}")

    print("\nTEST 3 — HTML contaminated text")
    t3 = "<div>We collect your name</div>\n&nbsp;We share data with partners.\nYou can delete your account within 30 days by contacting support."
    r3 = segment_into_clauses(t3)
    print(f"Clauses: {len(r3)}")
    for c in r3: print(f"  [{c['clause_id']}] {c['text']}")