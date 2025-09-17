# src/app.py
"""
PhishNet — Streamlit demo app
- urlscan.io for links
- VirusTotal lookup by SHA256 for attachments (demo mode, free API flow)
"""

import os
import time
import hashlib
import json
import re
import streamlit as st
from pathlib import Path
from bs4 import BeautifulSoup
import requests
import ssl
from requests.adapters import HTTPAdapter

from read_gmail import get_latest_email
import utils

# ---------------- Config ----------------
st.set_page_config(page_title="PhishNet — Demo (urlscan + VT lookup)", layout="wide")

URLSCAN_API_KEY = os.getenv("URLSCAN_API_KEY")
URLSCAN_SUBMIT = "https://urlscan.io/api/v1/scan/"
URLSCAN_RESULT = "https://urlscan.io/api/v1/result/{uuid}/"

VIRUSTOTAL_API_KEY = os.getenv("VIRUSTOTAL_API_KEY")  # free key: lookup only
VT_REPORT_URL = "https://www.virustotal.com/vtapi/v2/file/report"
VT_CACHE_DIR = Path("vt_cache")
VT_CACHE_DIR.mkdir(exist_ok=True)

URL_REGEX = re.compile(r"https?://[^\s)>\]]+")

# ---------------- TLS Adapter ----------------
class TLSAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        ctx = ssl.create_default_context()
        pool_kwargs["ssl_context"] = ctx
        return super().init_poolmanager(connections, maxsize, block=block, **pool_kwargs)

session = requests.Session()
session.mount("https://", TLSAdapter())

# ---------------- Helpers ----------------
def safe_render_html(html_text):
    return BeautifulSoup(html_text or "", "html.parser").get_text()

def extract_unique_urls(text):
    urls = URL_REGEX.findall(text or "")
    seen = set()
    unique = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    return unique

# ----- urlscan.io helpers -----
def submit_urlscan(url):
    if not URLSCAN_API_KEY:
        return {"error": "URLSCAN_API_KEY not set in environment"}
    headers = {"API-Key": URLSCAN_API_KEY, "Content-Type": "application/json"}
    payload = {"url": url, "visibility": "public"}
    try:
        r = session.post(URLSCAN_SUBMIT, headers=headers, json=payload, timeout=20)
        if r.status_code in (200, 201):
            return {"uuid": r.json().get("uuid")}
        else:
            return {"error": f"submit failed HTTP {r.status_code}: {r.text}"}
    except Exception as e:
        return {"error": str(e)}

def fetch_urlscan_result(uuid):
    try:
        r = session.get(URLSCAN_RESULT.format(uuid=uuid), timeout=20)
        if r.status_code == 200:
            return r.json()
        elif r.status_code == 404:
            return None
        else:
            return {"error": f"HTTP {r.status_code}: {r.text}"}
    except Exception as e:
        return {"error": str(e)}

def poll_urlscan(uuid, timeout=25, poll_interval=2):
    deadline = time.time() + timeout
    while time.time() < deadline:
        res = fetch_urlscan_result(uuid)
        if isinstance(res, dict) and res.get("error"):
            return {"error": res.get("error")}
        if res is None:
            time.sleep(poll_interval)
            continue
        return res
    return {"error": "timeout waiting for urlscan result"}

def verdict_from_urlscan(res):
    if not isinstance(res, dict):
        return "Unknown", {}
    verdicts = res.get("verdicts") or {}
    overall = verdicts.get("overall") or {}
    if overall.get("malicious"):
        return "Malicious ❌", overall
    if overall.get("suspicious"):
        return "Suspicious ⚠️", overall
    return "Safe ✅", overall or res.get("page") or {}

# ----- VirusTotal helpers (lookup only) -----
def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def vt_cache_path(sha256: str) -> Path:
    return VT_CACHE_DIR / f"{sha256}.json"

def vt_lookup_by_hash(sha256: str):
    cache = vt_cache_path(sha256)
    if cache.exists():
        try:
            return json.loads(cache.read_text(encoding="utf-8"))
        except Exception:
            pass
    if not VIRUSTOTAL_API_KEY:
        return {"error": "VIRUSTOTAL_API_KEY not set (VT lookup unavailable)"}
    params = {"apikey": VIRUSTOTAL_API_KEY, "resource": sha256}
    try:
        r = session.get(VT_REPORT_URL, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        try:
            cache.write_text(json.dumps(data), encoding="utf-8")
        except Exception:
            pass
        return data
    except Exception as e:
        return {"error": str(e)}

# ---------------- UI ----------------
st.title("📩 PhishNet — Demo (urlscan + VirusTotal lookup)")
col_main, col_side = st.columns([3, 1])

with col_side:
    st.header("Controls")
    if st.button("Fetch latest email"):
        st.session_state["fetched"] = True
    if st.button("Re-scan links (force)"):
        st.session_state["force_rescan"] = True
    st.markdown("---")
    st.write("Configuration")
    st.text(f"urlscan key set: {'Yes' if URLSCAN_API_KEY else 'No'}")
    st.text(f"VirusTotal key set: {'Yes' if VIRUSTOTAL_API_KEY else 'No (lookup disabled)'}")
    st.caption("VT free API cannot upload new files. Lookup only.")

if "fetched" not in st.session_state:
    st.session_state["fetched"] = False
if "force_rescan" not in st.session_state:
    st.session_state["force_rescan"] = False
if "email" not in st.session_state:
    st.session_state["email"] = None
if "urlscan_checks" not in st.session_state:
    st.session_state["urlscan_checks"] = None

if st.session_state["fetched"] or st.session_state["force_rescan"]:
    try:
        latest = get_latest_email()
        if latest is None:
            st.warning("No email found.")
            st.session_state["email"] = None
        else:
            if len(latest) == 3:
                sender, subject, body = latest
                attachments = []
            else:
                sender, subject, body, attachments = latest
            st.session_state["email"] = {
                "sender": sender,
                "subject": subject,
                "body": body,
                "attachments": attachments,
            }
            st.session_state["urlscan_checks"] = None
            st.session_state["force_rescan"] = False
            st.success("Latest email fetched.")
    except Exception as e:
        st.error(f"Error fetching email: {e}")
        st.session_state["email"] = None
    st.session_state["fetched"] = False

email = st.session_state.get("email")
if not email:
    st.info("No email loaded. Click 'Fetch latest email' to begin.")
    st.stop()

# ---- Main column ----
with col_main:
    st.subheader("Email")
    st.markdown(f"**From:** {email.get('sender')}")
    st.markdown(f"**Subject:** {email.get('subject') or '(no subject)'}")
    body_text = safe_render_html(email.get("body") or "")
    st.text_area("Body", value=body_text, height=220)

    st.markdown("---")
    st.subheader("Classification")

    # Spam
    spam_label = utils.classify_email(email.get("subject"), email.get("body"))
    if spam_label.startswith("SPAM"):
        st.error(f"🔎 Spam Classification: {spam_label}")
    elif spam_label.startswith("HAM"):
        st.success("🔎 Spam Classification: NOT SPAM ✅")
    else:
        st.warning(f"🔎 Spam Classification: {spam_label}")

    # Social engineering
    combined = utils.classify_social_combined(email.get("body") or "")
    model_prob = combined.get("model_prob")
    rule_score = combined.get("rule_score", 0.0)
    combined_prob = combined.get("combined_prob", 0.0)
    threshold = combined.get("threshold", utils.SOCIAL_THRESHOLD)
    label = combined.get("label", "UNKNOWN")
    triggers = combined.get("triggers", [])

    st.markdown("**Social Engineering (combined)**")
    cols = st.columns([2, 2, 2])
    with cols[0]:
        st.write(f"Model prob: {model_prob:.2f}" if model_prob else "Model prob: N/A")
        st.progress(min(1.0, max(0.0, model_prob or 0)))
    with cols[1]:
        st.write(f"Rule score: {rule_score:.2f}")
        st.progress(rule_score)
    with cols[2]:
        st.write(f"Combined: {combined_prob:.2f} (thr {threshold:.2f})")
        st.progress(combined_prob)

    if "Attack" in label:
        st.error(f"🎭 Final decision: {label}")
    elif "No Attack" in label:
        st.success(f"🎭 Final decision: {label}")
    else:
        st.info(f"🎭 Final decision: {label}")

    if triggers:
        st.markdown("**Rule triggers:**")
        for t in triggers:
            st.write(f"- {t}")
    else:
        st.write("**Rule triggers:** none")

# ---- Side column ----
with col_side:
    st.subheader("Links")
    urls = extract_unique_urls(email.get("body") or "")
    if not urls:
        st.write("No links found.")
    else:
        st.write(f"{len(urls)} link(s) found:")
        for u in urls:
            st.write(f"- {u}")

        if st.button("Check all links with urlscan.io"):
            st.session_state["urlscan_checks"] = []
            with st.spinner("Scanning links..."):
                for u in urls:
                    sub = submit_urlscan(u)
                    if sub.get("error"):
                        st.session_state["urlscan_checks"].append((u, {"error": sub["error"]}))
                        continue
                    uuid = sub.get("uuid")
                    if not uuid:
                        st.session_state["urlscan_checks"].append((u, {"error": "no uuid"}))
                        continue
                    res = poll_urlscan(uuid, timeout=25, poll_interval=2)
                    if isinstance(res, dict) and res.get("error"):
                        st.session_state["urlscan_checks"].append((u, {"error": res.get("error")}))
                    else:
                        verdict, detail = verdict_from_urlscan(res)
                        st.session_state["urlscan_checks"].append((u, {"verdict": verdict, "detail": detail}))

    if st.session_state.get("urlscan_checks"):
        st.subheader("urlscan.io results")
        for u, res in st.session_state["urlscan_checks"]:
            if res.get("error"):
                st.write(f"- {u} → Error: {res['error']}")
            else:
                st.write(f"- {u} → {res.get('verdict', 'Unknown')}")
                with st.expander("Details"):
                    st.json(res.get("detail"))

    st.markdown("---")
    st.subheader("Attachments (VirusTotal lookup)")
    attachments = email.get("attachments") or []
    if not attachments:
        st.write("No attachments.")
    else:
        for idx, (fname, data) in enumerate(attachments):
            st.write(f"- {fname} ({len(data)} bytes)")
            st.download_button(label=f"Download {fname}", data=data, file_name=fname)

            sha = sha256_bytes(data)
            st.write(f"SHA256: `{sha}`")

            if st.button(f"Lookup on VirusTotal: {fname}", key=f"vt_{idx}"):
                with st.spinner("Querying VT..."):
                    vt_resp = vt_lookup_by_hash(sha)
                if vt_resp.get("error"):
                    st.error(vt_resp["error"])
                elif vt_resp.get("response_code") == 1:
                    positives = vt_resp.get("positives", 0)
                    total = vt_resp.get("total", 0)
                    st.write(f"🔎 VT: {positives}/{total} engines flagged this file.")
                    with st.expander("Full VT JSON"):
                        st.json(vt_resp)
                else:
                    st.warning("No VT record (free API cannot upload new files).")
