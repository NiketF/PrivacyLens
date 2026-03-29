import sys
sys.path.insert(0, '.')

print("Step 1: Importing pipeline...")
from src.pipeline import PrivacyPolicyAnalyzer

print("Step 2: Loading analyzer...")
analyzer = PrivacyPolicyAnalyzer()

print("Step 3: Testing segmentor directly...")
from src.ingestion.clause_segmentor import segment_into_clauses

test_text = """We collect your name and email address when you register.

We may share your personal data with advertising partners without consent.

You have the right to delete your data within 30 days.

We reserve the right to modify this policy without notice."""

clauses = segment_into_clauses(test_text)
print(f"Clauses found: {len(clauses)}")
for c in clauses:
    print(f"  [{c['clause_id']}] {c['text'][:80]}")

print("\nStep 4: Running full pipeline...")
result = analyzer.analyze(test_text, simplify_red=False)
print(f"Risk score: {result['risk_score']}")
print(f"Total clauses: {result['total_clauses']}")
print(f"Red: {result['red_count']}, Green: {result['green_count']}, Gray: {result['gray_count']}")