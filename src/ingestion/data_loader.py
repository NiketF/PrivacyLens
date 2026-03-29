# src/ingestion/data_loader.py

import pandas as pd
import os
import json
import re

CATEGORY_MAP = {
    "First Party Collection/Use":           "data_collection",
    "Third Party Sharing/Collection":        "data_sharing",
    "User Choice/Control":                   "user_rights",
    "User Access, Edit and Deletion":        "user_rights",
    "Do Not Track":                          "user_rights",
    "Data Retention":                        "data_retention",
    "Data Security":                         "security",
    "Policy Change":                         "policy_changes",
    "International and Specific Audiences":  "childrens_data",
    "Other":                                 "legal_jurisdiction",
}

def clean_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_text_from_annotation(annotation_json: str) -> tuple:
    """
    Extract selected text and category from OPP-115 annotation JSON.
    Returns (text, raw_category)
    """
    try:
        data = json.loads(annotation_json)
        # The category is the top-level key
        category_raw = list(data.keys())[0]
        inner        = data[category_raw]
        text         = inner.get("selectedText", "")
        return text, category_raw
    except Exception:
        return "", ""

def load_opp115(data_dir: str = "data/opp115/OPP-115/annotations") -> pd.DataFrame:
    """
    Load OPP-115 from the annotations folder.
    Each CSV file = one privacy policy.
    Each row = one annotation.
    """
    if not os.path.exists(data_dir):
        print(f"OPP-115 not found at {data_dir}")
        print("Using sample dataset instead...")
        return _create_sample_dataset()

    csv_files = [
        f for f in os.listdir(data_dir)
        if f.endswith('.csv')
    ]

    if not csv_files:
        print("No CSV files found in annotations folder.")
        return _create_sample_dataset()

    print(f"Found {len(csv_files)} policy annotation files...")

    all_records = []

    for filename in csv_files:
        filepath = os.path.join(data_dir, filename)
        policy_name = filename.replace('.csv', '')

        try:
            # OPP-115 CSV has no header row
            df = pd.read_csv(
                filepath,
                header=None,
                on_bad_lines='skip',
                encoding='utf-8'
            )

            # Column 5 = category, Column 6 = annotation JSON
            if df.shape[1] < 7:
                continue

            for _, row in df.iterrows():
                try:
                    category_raw    = str(row.iloc[5]).strip()
                    annotation_json = str(row.iloc[6]).strip()

                    text, _ = extract_text_from_annotation(annotation_json)

                    if not text:
                        # Fallback: use raw category column text
                        text = annotation_json[:300]

                    text     = clean_text(text)
                    category = CATEGORY_MAP.get(category_raw, "")

                    if text and category and len(text) > 20:
                        all_records.append({
                            "text":         text,
                            "category":     category,
                            "policy":       policy_name,
                            "category_raw": category_raw
                        })

                except Exception:
                    continue

        except Exception as e:
            print(f"  Skipping {filename}: {e}")
            continue

    if not all_records:
        print("Could not parse any records. Using sample dataset.")
        return _create_sample_dataset()

    df_final = pd.DataFrame(all_records)

    # Remove duplicates
    df_final = df_final.drop_duplicates(subset=['text'])

    # Remove very short or very long clauses
    df_final = df_final[
        (df_final['text'].str.len() > 30) &
        (df_final['text'].str.len() < 2000)
    ]

    print(f"\nSuccessfully loaded {len(df_final)} clauses")
    print(f"From {df_final['policy'].nunique()} policies")
    print(f"\nCategory distribution:")
    print(df_final['category'].value_counts())

    return df_final[['text', 'category']]


def _create_sample_dataset() -> pd.DataFrame:
    """Small fallback dataset for testing."""
    samples = [
        ("We collect your name, email address, and location data when you register.", "data_collection"),
        ("We automatically collect your IP address, device type, and browsing history.", "data_collection"),
        ("We collect precise geolocation from your device when the app is open.", "data_collection"),
        ("We collect payment information including credit card and UPI details.", "data_collection"),
        ("We only collect information you voluntarily provide to us.", "data_collection"),
        ("We may share your personal information with third-party advertisers.", "data_sharing"),
        ("We sell aggregated user data to marketing companies.", "data_sharing"),
        ("We will never sell your personal data to any third party.", "data_sharing"),
        ("We share your data with service providers who process it on our behalf.", "data_sharing"),
        ("We disclose information to law enforcement when required by law.", "data_sharing"),
        ("You may request deletion of your personal data at any time.", "user_rights"),
        ("You have the right to access and download your personal information.", "user_rights"),
        ("You can opt out of marketing communications at any time.", "user_rights"),
        ("Users have no right to request deletion of submitted data.", "user_rights"),
        ("You may withdraw your consent to data processing at any time.", "user_rights"),
        ("We retain your data as long as your account is active.", "data_retention"),
        ("Data is deleted within 30 days of account closure.", "data_retention"),
        ("We may retain information indefinitely for legal purposes.", "data_retention"),
        ("Backup copies may persist for up to 90 days after deletion.", "data_retention"),
        ("We retain transaction records for 7 years as required by law.", "data_retention"),
        ("We use SSL encryption to protect your data in transit.", "security"),
        ("We cannot guarantee the security of data transmitted over the internet.", "security"),
        ("We conduct regular security audits and penetration testing.", "security"),
        ("We will notify you within 72 hours of a data breach.", "security"),
        ("We reserve the right to modify this policy without prior notice.", "policy_changes"),
        ("We will notify you by email 30 days before making changes.", "policy_changes"),
        ("Continued use constitutes acceptance of any policy changes.", "policy_changes"),
        ("Our service is not directed to children under 18.", "childrens_data"),
        ("We do not knowingly collect data from children under 13.", "childrens_data"),
        ("Parents may request deletion of their child's data.", "childrens_data"),
        ("This policy is governed by the laws of India.", "legal_jurisdiction"),
        ("Disputes shall be resolved through binding arbitration.", "legal_jurisdiction"),
        ("This agreement is subject to the DPDPA 2023.", "legal_jurisdiction"),
    ]
    df = pd.DataFrame(samples, columns=['text', 'category'])
    print(f"Using sample dataset: {len(df)} clauses")
    return df


if __name__ == "__main__":
    df = load_opp115()
    os.makedirs("data/processed", exist_ok=True)
    df.to_csv("data/processed/stage1_ready.csv", index=False)
    print(f"\nSaved {len(df)} clauses to data/processed/stage1_ready.csv")