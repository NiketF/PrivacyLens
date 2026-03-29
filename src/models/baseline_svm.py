# src/models/baseline_svm.py

import pandas as pd
import numpy as np
import pickle
import os
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, f1_score
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

def build_pipeline():
    """Build TF-IDF + SVM classification pipeline."""
    return Pipeline([
        ('tfidf', TfidfVectorizer(
            ngram_range=(1, 3),       # unigrams, bigrams, trigrams
            max_features=40000,
            sublinear_tf=True,        # log-normalize term frequency
            strip_accents='unicode',
            analyzer='word',
            min_df=2                  # ignore terms appearing < 2 times
        )),
        ('clf', CalibratedClassifierCV(
            LinearSVC(
                class_weight='balanced',  # handle class imbalance
                max_iter=5000,
                C=1.0
            ),
            cv=3
        ))
    ])

def plot_confusion_matrix(y_true, y_pred, labels, save_path):
    """Save confusion matrix as PNG."""
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    plt.figure(figsize=(12, 9))
    sns.heatmap(
        cm, annot=True, fmt='d', cmap='Blues',
        xticklabels=labels, yticklabels=labels
    )
    plt.title('Confusion Matrix — TF-IDF + SVM Baseline', fontsize=14)
    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()
    print(f"Confusion matrix saved: {save_path}")

def train_and_evaluate(data_path: str = "data/processed/stage1_ready.csv"):
    """Full training + evaluation pipeline."""

    # ── Load data ────────────────────────────────────────────
    print("Loading data...")
    df = pd.read_csv(data_path)
    print(f"Dataset: {len(df)} samples, {df['category'].nunique()} categories")

    X = df['text'].values
    y = df['category'].values

    # ── Split ────────────────────────────────────────────────
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.20,
        stratify=y,
        random_state=42
    )
    print(f"Train: {len(X_train)} | Test: {len(X_test)}")

    # ── Train ────────────────────────────────────────────────
    print("\nTraining TF-IDF + SVM...")
    model = build_pipeline()
    model.fit(X_train, y_train)
    print("Training complete.")

    # ── Evaluate ─────────────────────────────────────────────
    y_pred = model.predict(X_test)
    labels = sorted(df['category'].unique().tolist())

    print("\n" + "="*65)
    print("CLASSIFICATION REPORT — TF-IDF + SVM BASELINE")
    print("="*65)
    print(classification_report(y_test, y_pred, target_names=labels))

    macro_f1 = f1_score(y_test, y_pred, average='macro')
    print(f"MACRO F1 SCORE: {macro_f1:.4f}  ← Write this down")
    print("="*65)

    # ── Confusion matrix ─────────────────────────────────────
    os.makedirs("outputs", exist_ok=True)
    plot_confusion_matrix(
        y_test, y_pred, labels,
        "outputs/baseline_confusion_matrix.png"
    )

    # ── Cross-validation ─────────────────────────────────────
    print("\nRunning 5-fold cross-validation (this takes ~1 minute)...")
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(
        build_pipeline(), X, y,
        cv=cv, scoring='f1_macro', n_jobs=-1
    )
    print(f"CV Macro F1: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")

    # ── Save model ───────────────────────────────────────────
    os.makedirs("models/checkpoints", exist_ok=True)
    model_path = "models/checkpoints/baseline_stage1.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    print(f"\nModel saved: {model_path}")

    # ── Quick inference test ─────────────────────────────────
    print("\n--- INFERENCE TEST ---")
    test_clauses = [
        "We collect your name, email address, and precise location data.",
        "We may share your personal data with advertising partners without consent.",
        "You have the right to request deletion of all your personal information.",
        "We reserve the right to modify this policy at any time without notice.",
        "We use industry-standard encryption to protect your data.",
    ]
    predictions   = model.predict(test_clauses)
    probabilities = model.predict_proba(test_clauses)

    for clause, pred, prob in zip(test_clauses, predictions, probabilities):
        confidence = max(prob)
        print(f"\nText:       {clause[:70]}...")
        print(f"Predicted:  {pred}  (confidence: {confidence:.2f})")

    return model, macro_f1


if __name__ == "__main__":
    model, f1 = train_and_evaluate()