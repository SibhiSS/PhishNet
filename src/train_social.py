# src/train_social.py
"""
Robust trainer for social-engineering (emotional attack) classifier.

Features:
- Removes exact duplicates
- Ensures no overlap between train/test (retries if overlap found)
- Compares LogisticRegression and MultinomialNB using cross-validation
- Evaluates on a held-out test set, selects best model, picks threshold by maximizing F1 on test
- Saves model and threshold to models/
- Prints warnings if perfect scores are observed (possible data leakage / templating)

Usage:
    # from project root
    $env:SOCIAL_CSV_PATH="Dataset/social_synthetic_1000.csv"
    python src/train_social.py
"""
import os
import json
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score, StratifiedShuffleSplit
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import classification_report, accuracy_score, precision_recall_curve, f1_score
import warnings
warnings.filterwarnings("ignore")

# Paths
DATA_PATH = os.getenv("SOCIAL_CSV_PATH", "Dataset/social_synthetic_1000.csv")
MODEL_DIR = os.getenv("MODEL_DIR", "models")
MODEL_PATH = os.path.join(MODEL_DIR, "social_model.pkl")
THRESHOLD_PATH = os.path.join(MODEL_DIR, "social_threshold.json")
Path(MODEL_DIR).mkdir(parents=True, exist_ok=True)

print("📂 Loading dataset:", DATA_PATH)
df = pd.read_csv(DATA_PATH, dtype=str)

# normalize column names / selection
if "Message" in df.columns and "Label" in df.columns:
    texts = df["Message"].astype(str)
    labels = df["Label"].astype(str)
else:
    # fallback: take first two columns
    texts = df.iloc[:, 0].astype(str)
    labels = df.iloc[:, 1].astype(str)

# Normalize labels to binary 1 = Attack, 0 = No Attack
labels_bin = labels.str.strip().str.lower().apply(lambda x: 1 if x == "attack" else 0)

# ------------- deduplicate exact duplicates -------------
before = len(texts)
dedup_df = pd.DataFrame({"text": texts, "label": labels_bin})
dedup_df = dedup_df.drop_duplicates(subset=["text", "label"]).reset_index(drop=True)
after = len(dedup_df)
print(f"🧹 Removed exact duplicates: {before - after} rows (kept {after})")

X_all = dedup_df["text"].values
y_all = dedup_df["label"].values

# ------------- ensure train/test no-overlap -------------
# We'll repeatedly attempt a stratified split until there are no identical texts present in both sets.
def make_nonoverlapping_split(X, y, test_size=0.20, max_tries=10, random_state=42):
    rs = StratifiedShuffleSplit(n_splits=max_tries, test_size=test_size, random_state=random_state)
    for i, (train_idx, test_idx) in enumerate(rs.split(X, y)):
        X_train, X_test = X[train_idx], X[test_idx]
        # check overlap
        set_train = set(X_train)
        set_test = set(X_test)
        overlap = set_train.intersection(set_test)
        if len(overlap) == 0:
            return X_train, X_test, y[train_idx], y[test_idx]
    # fallback: remove duplicates between train/test by forcing unique test examples
    print("⚠️ Could not find a split without overlap after retries; removing overlapping examples from test set.")
    # take a single split then remove overlap from test
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, stratify=y, random_state=random_state)
    set_train = set(X_train)
    mask = [x not in set_train for x in X_test]
    X_test = X_test[mask]
    y_test = y_test[mask]
    return X_train, X_test, y_train, y_test

X_train, X_test, y_train, y_test = make_nonoverlapping_split(X_all, y_all, test_size=0.2, max_tries=20, random_state=42)
print(f"🔀 Train size: {len(X_train)} | Test size: {len(X_test)}")

# If test set is very small after dedupe, warn
if len(X_test) < 20:
    print("⚠️ Test set is small (<20). Consider creating a larger held-out test set for reliable estimates.")

# ------------- define pipelines -------------
pipeline_lr = Pipeline([
    ("tfidf", TfidfVectorizer(ngram_range=(1,2), min_df=2)),
    ("clf", LogisticRegression(max_iter=400, class_weight="balanced")),
])

pipeline_nb = Pipeline([
    ("tfidf", TfidfVectorizer(ngram_range=(1,2), min_df=2)),
    ("clf", MultinomialNB()),
])

# ------------- cross-validate on training set -------------
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

print("\n🔁 Cross-validating models on training set (F1)...")
lr_scores = cross_val_score(pipeline_lr, X_train, y_train, cv=cv, scoring="f1", n_jobs=-1)
nb_scores = cross_val_score(pipeline_nb, X_train, y_train, cv=cv, scoring="f1", n_jobs=-1)
print(f"LogisticRegression CV F1: {lr_scores.mean():.3f} ± {lr_scores.std():.3f}")
print(f"MultinomialNB CV F1:      {nb_scores.mean():.3f} ± {nb_scores.std():.3f}")

# ------------- fit both on full training set and evaluate on held-out test -------------
print("\n🔧 Training final models on full training set and evaluating on held-out test set...")
pipeline_lr.fit(X_train, y_train)
pipeline_nb.fit(X_train, y_train)

def eval_on_test(pipe, X_test, y_test):
    y_pred = pipe.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    rep = classification_report(y_test, y_pred, target_names=["No Attack", "Attack"])
    probs = None
    try:
        probs = pipe.predict_proba(X_test)[:,1]
    except Exception:
        probs = None
    return {"acc": acc, "report": rep, "probs": probs, "pred": y_pred}

res_lr = eval_on_test(pipeline_lr, X_test, y_test)
res_nb = eval_on_test(pipeline_nb, X_test, y_test)

print("\n--- Logistic Regression on test ---")
print("Accuracy:", res_lr["acc"])
print(res_lr["report"])

print("\n--- MultinomialNB on test ---")
print("Accuracy:", res_nb["acc"])
print(res_nb["report"])

# Warn if perfect scores (likely data leakage / templating)
if res_lr["acc"] == 1.0 or res_nb["acc"] == 1.0:
    print("⚠️ Perfect accuracy on test detected. This usually indicates data leakage or trivial separability. Inspect data and duplicates.")

# ------------- pick best model by F1 on test set -------------
# compute test F1
f1_lr = f1_score(y_test, pipeline_lr.predict(X_test))
f1_nb = f1_score(y_test, pipeline_nb.predict(X_test))
print(f"\nTest F1 - LR: {f1_lr:.3f} | NB: {f1_nb:.3f}")

if f1_lr >= f1_nb:
    best_pipe = pipeline_lr
    best_name = "LogisticRegression"
    best_probs = res_lr["probs"]
else:
    best_pipe = pipeline_nb
    best_name = "MultinomialNB"
    best_probs = res_nb["probs"]

print(f"\n✅ Selected best model: {best_name}")

# ------------- threshold selection (maximize F1 on test probs) -------------
if best_probs is not None:
    prec, rec, thresh = precision_recall_curve(y_test, best_probs)
    # compute F1 for each thresh index (prec/rec arrays lengths differ by 1)
    f1s = 2 * (prec[:-1] * rec[:-1]) / (prec[:-1] + rec[:-1] + 1e-8)
    if len(f1s) > 0:
        best_idx = int(np.nanargmax(f1s))
        best_thresh = float(thresh[best_idx])
    else:
        best_thresh = 0.7
else:
    # if no probs available (rare), fallback to 0.7
    best_thresh = 0.7

print(f"🎯 Chosen threshold (test-set F1 max): {best_thresh:.3f}")

# ------------- Save final model and threshold -------------
print(f"\n💾 Saving model to: {MODEL_PATH}")
joblib.dump(best_pipe, MODEL_PATH)
with open(THRESHOLD_PATH, "w") as fh:
    json.dump({"threshold": best_thresh}, fh)

print("💾 Saved threshold at:", THRESHOLD_PATH)

# ------------- final note/warnings -------------
if res_lr["acc"] == 1.0 or res_nb["acc"] == 1.0:
    print(
        "\n⚠️ IMPORTANT: Perfect test accuracy detected. Possible causes:\n"
        " - Your synthetic templates leak label words or have deterministic differences between Attack and No Attack templates.\n"
        " - Train/test overlap (some exact duplicates slipped through).\n"
        " - The classification task is trivially separable given current features.\n\n"
        "Recommendations:\n"
        " - Inspect sample pairs from train/test to confirm there is no overlap.\n"
        " - Add more variation / paraphrases / noise to make model generalize.\n"
        " - Evaluate on a fully separate human-labeled test set if possible.\n"
    )

print("\nDone.")
