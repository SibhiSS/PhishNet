# utils.py
import os
import joblib
import requests
import json
from pathlib import Path

# ---------------- Spam model ----------------
# Default path prefers a recent joblib name used earlier; override with SPAM_MODEL_PATH env var.
MODEL_PATH = os.getenv("SPAM_MODEL_PATH", "models/spam_model_v2.joblib")
if not Path(MODEL_PATH).exists():
    # fallback to an older name if present
    if Path("models/spam_model.pkl").exists():
        MODEL_PATH = "models/spam_model.pkl"

try:
    clf = joblib.load(MODEL_PATH)
    print("Loaded spam classifier from:", MODEL_PATH)
except Exception as e:
    clf = None
    print("⚠️ Could not load spam classifier:", e)

def classify_email(subject, body):
    """
    Classify email as SPAM or HAM using the spam model.
    Returns a short label string.
    """
    if clf is None:
        return "UNKNOWN"

    text = f"{subject or ''} {body or ''}"
    try:
        pred = clf.predict([text])[0]
        return "SPAM 🚨" if int(pred) == 1 else "HAM ✅"
    except Exception as e:
        return f"ERROR: {e}"

# -------------- Social engineering model --------------
SOCIAL_MODEL_PATH = os.getenv("SOCIAL_MODEL_PATH", "models/social_model.pkl")
SOCIAL_THRESHOLD_PATH = os.getenv("SOCIAL_THRESHOLD_PATH", "models/social_threshold.json")

try:
    social_clf = joblib.load(SOCIAL_MODEL_PATH)
    print("Loaded social engineering classifier from:", SOCIAL_MODEL_PATH)
except Exception as e:
    social_clf = None
    print("⚠️ Could not load social engineering model:", e)

# Try to load an auto-computed threshold (created by train_social.py). If missing, fall back to env var or default.
try:
    with open(SOCIAL_THRESHOLD_PATH, "r") as f:
        SOCIAL_THRESHOLD = float(json.load(f)["threshold"])
    print("Using saved social engineering threshold:", SOCIAL_THRESHOLD)
except Exception:
    SOCIAL_THRESHOLD = float(os.getenv("SOCIAL_THRESHOLD", 0.7))
    print("⚠️ Using default social engineering threshold:", SOCIAL_THRESHOLD)

def classify_social(text):
    """
    Return a dict with:
      - label: "Attack 🎭" or "No Attack 🙂" (or UNKNOWN/ERROR)
      - prob: probability (float) or None
      - threshold: threshold used
    """
    if social_clf is None:
        return {"label": "UNKNOWN", "prob": None, "threshold": SOCIAL_THRESHOLD}

    try:
        prob = social_clf.predict_proba([text])[0][1]  # probability of "Attack" class
        label = "Attack 🎭" if prob >= SOCIAL_THRESHOLD else "No Attack 🙂"
        return {"label": label, "prob": float(prob), "threshold": SOCIAL_THRESHOLD}
    except Exception as e:
        return {"label": "ERROR", "prob": None, "threshold": SOCIAL_THRESHOLD, "reason": str(e)}

# ---------------- Google Safe Browsing (original auth style) ----------------
def scan_url_google(url):
    """
    Check URL against Google Safe Browsing API (API key in env var GOOGLE_SAFE_BROWSING_KEY).
    Returns dict with 'status' or 'error'.
    """
    api_key = os.getenv("GOOGLE_SAFE_BROWSING_KEY")
    if not api_key:
        return {"error": "GOOGLE_SAFE_BROWSING_KEY not set"}

    endpoint = f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={api_key}"
    payload = {
        "client": {"clientId": "phishnet", "clientVersion": "1.0"},
        "threatInfo": {
            "threatTypes": [
                "MALWARE",
                "SOCIAL_ENGINEERING",
                "UNWANTED_SOFTWARE",
                "POTENTIALLY_HARMFUL_APPLICATION",
            ],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": url}],
        },
    }

    try:
        r = requests.post(endpoint, json=payload, timeout=10)
        r.raise_for_status()
        data = r.json()
        if "matches" in data:
            return {"url": url, "status": "unsafe", "matches": data["matches"]}
        return {"url": url, "status": "safe"}
    except Exception as e:
        return {"error": str(e)}
