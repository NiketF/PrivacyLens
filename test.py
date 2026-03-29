import sys
sys.path.insert(0, '.')
from src.ingestion.clause_segmentor import segment_into_clauses

text = """We collect your name, email address, precise location, and device identifiers when you use our app.

We may share your personal data with advertising partners and analytics companies without your explicit consent. We reserve the right to sell aggregated user profiles to third-party marketing firms.

You have the right to request deletion of your data within 30 days. You can opt out of marketing emails at any time.

We may retain your data indefinitely for legal and business purposes. Backup copies may persist for up to 90 days after account deletion.

We reserve the right to modify this policy at any time without prior notice. Continued use of our service constitutes acceptance of any changes made.

Any disputes shall be resolved through binding arbitration. You waive your right to participate in class action lawsuits against us.
"""

clauses = segment_into_clauses(text)
print(f"Total clauses found: {len(clauses)}")
for c in clauses:
    print(f"  [{c['clause_id']}] ({c['word_count']} words) {c['text'][:80]}")