# utils.py
import os
import joblib
import requests
import json
import re
from pathlib import Path

# ---------------- Spam model ----------------
MODEL_PATH = os.getenv("SPAM_MODEL_PATH", "models/spam_model_v2.joblib")
if not Path(MODEL_PATH).exists():
    if Path("models/spam_model.pkl").exists():
        MODEL_PATH = "models/spam_model.pkl"

try:
    clf = joblib.load(MODEL_PATH)
    print("Loaded spam classifier from:", MODEL_PATH)
except Exception as e:
    clf = None
    print("⚠️ Could not load spam classifier:", e)

def classify_email(subject, body):
    if clf is None:
        return "UNKNOWN"
    text = f"{subject or ''} {body or ''}"
    try:
        pred = clf.predict([text])[0]
        return "SPAM 🚨" if int(pred) == 1 else "HAM ✅"
    except Exception as e:
        return f"ERROR: {e}"

# -------------- Social engineering model & heuristics --------------
SOCIAL_MODEL_PATH = os.getenv("SOCIAL_MODEL_PATH", "models/social_model.pkl")
SOCIAL_THRESHOLD_PATH = os.getenv("SOCIAL_THRESHOLD_PATH", "models/social_threshold.json")
# Combined score weight: alpha * model_prob + (1-alpha) * rule_score
COMBINE_ALPHA = float(os.getenv("SOCIAL_COMBINE_ALPHA", 0.7))

try:
    social_clf = joblib.load(SOCIAL_MODEL_PATH)
    print("Loaded social engineering classifier from:", SOCIAL_MODEL_PATH)
except Exception as e:
    social_clf = None
    print("⚠️ Could not load social engineering model:", e)

# Default threshold changed to 0.45 (can be overridden by saved file or env var)
DEFAULT_SOCIAL_THRESHOLD = 0.45

# Try to load an auto-computed threshold (created by train_social.py).
# If present, it will be used. If an env var SOCIAL_THRESHOLD is provided, that takes precedence.
_loaded_threshold = None
try:
    if Path(SOCIAL_THRESHOLD_PATH).exists():
        with open(SOCIAL_THRESHOLD_PATH, "r") as f:
            _loaded_threshold = float(json.load(f)["threshold"])
        print("Loaded saved social engineering threshold from file:", _loaded_threshold)
except Exception:
    _loaded_threshold = None

# If env var set, it overrides the loaded threshold.
_env_thresh = os.getenv("SOCIAL_THRESHOLD")
if _env_thresh is not None:
    try:
        SOCIAL_THRESHOLD = float(_env_thresh)
        print("Using SOCIAL_THRESHOLD from environment:", SOCIAL_THRESHOLD)
    except Exception:
        SOCIAL_THRESHOLD = _loaded_threshold if _loaded_threshold is not None else DEFAULT_SOCIAL_THRESHOLD
        print("Invalid SOCIAL_THRESHOLD env var; falling back to:", SOCIAL_THRESHOLD)
else:
    SOCIAL_THRESHOLD = _loaded_threshold if _loaded_threshold is not None else DEFAULT_SOCIAL_THRESHOLD
    print("Using social engineering threshold:", SOCIAL_THRESHOLD)

# ----- Rule-based indicators -----
RULE_INDICATORS = {
    "layoff_terms": {
        "pattern": re.compile(r"\b(layoff|layoffs|downsiz|downsizings|firing|fired|laid off|we may let|we may be letting|position is at risk)\b", re.I),
        "weight": 2.5,
        "description": "Layoff / job insecurity phrasing"
    },
    "cred_request": {
        "pattern": re.compile(r"\b(password|credentials|login|ssn|social security|bank details|account number|confirm your identity|verify your identity|verify your account|confirm your details)\b", re.I),
        "weight": 2.0,
        "description": "Request for credentials / personal info"
    },
    "urgency": {
        "pattern": re.compile(r"\b(urgent|immediately|right now|asap|today|this minute|immediate action|required now|must)\b", re.I),
        "weight": 1.2,
        "description": "Urgency pressure"
    },
    "emotional_appeal": {
        "pattern": re.compile(r"\b(so upset|devastated|terrible news|shocking|can't believe|sorry to hear|must be hard|feeling stressed|worried about)\b", re.I),
        "weight": 1.3,
        "description": "Emotional appeal / sympathy"
    },
    "reward": {
        "pattern": re.compile(r"\b(congratulations|you've won|exclusive offer|selected for|prize|claim your reward|pre-approved)\b", re.I),
        "weight": 1.6,
        "description": "Reward / prize lure"
    },
    "impersonation": {
        "pattern": re.compile(r"\b(i'm (from|with) |this is .* from|on behalf of|im from)\b", re.I),
        "weight": 1.0,
        "description": "Impersonation / sender claim"
    },
    "link_indicator": {
        "pattern": re.compile(r"https?://", re.I),
        "weight": 0.8,
        "description": "Presence of (possibly malicious) links"
    }
}

_MAX_RULE_SCORE = sum(ind["weight"] for ind in RULE_INDICATORS.values())

def rule_score_and_triggers(text):
    if not text:
        return 0.0, []
    total = 0.0
    triggers = []
    for key, ind in RULE_INDICATORS.items():
        if ind["pattern"].search(text):
            total += ind["weight"]
            triggers.append(ind["description"])
    normalized = min(1.0, total / _MAX_RULE_SCORE) if _MAX_RULE_SCORE > 0 else 0.0
    return normalized, list(set(triggers))

def model_social_prob(text):
    if social_clf is None:
        return None
    try:
        prob = social_clf.predict_proba([text])[0][1]
        return float(prob)
    except Exception:
        return None

def classify_social_combined(text):
    txt = text or ""
    model_prob = model_social_prob(txt)
    rscore, triggers = rule_score_and_triggers(txt)

    if model_prob is None:
        combined = rscore
    else:
        combined = COMBINE_ALPHA * model_prob + (1.0 - COMBINE_ALPHA) * rscore

    combined = max(0.0, min(1.0, float(combined)))

    try:
        label = "Attack 🎭" if combined >= SOCIAL_THRESHOLD else "No Attack 🙂"
    except Exception:
        label = "ERROR"

    return {
        "model_prob": model_prob,
        "rule_score": float(rscore),
        "combined_prob": float(combined),
        "threshold": float(SOCIAL_THRESHOLD),
        "label": label,
        "triggers": triggers
    }

# ---------------- Google Safe Browsing (original auth style) ----------------
def scan_url_google(url):
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
