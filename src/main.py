# main.py
import os
import time
import re
from read_gmail import get_latest_email
from bs4 import BeautifulSoup
import utils  # centralized classifiers & helpers

# ---------- CONFIG ----------
URLSCAN_API_KEY = os.getenv("URLSCAN_API_KEY")
URLSCAN_SUBMIT = "https://urlscan.io/api/v1/scan/"
URLSCAN_RESULT = "https://urlscan.io/api/v1/result/{uuid}/"

POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 30))
ATTACHMENT_SAVE_FOLDER = os.path.join(os.path.dirname(__file__), "..", "attachments")
os.makedirs(ATTACHMENT_SAVE_FOLDER, exist_ok=True)

URL_REGEX = re.compile(r"https?://[^\s)>\]]+")

# ---------- helpers ----------
def clean_text(text):
    text = BeautifulSoup(text or "", "html.parser").get_text()
    return re.sub(r"\s+", " ", text).strip()

def extract_urls(text):
    return URL_REGEX.findall(text or "")

def submit_urlscan(url):
    if not URLSCAN_API_KEY:
        return {"error": "URLSCAN_API_KEY not set in environment"}
    import requests
    headers = {"API-Key": URLSCAN_API_KEY, "Content-Type": "application/json"}
    payload = {"url": url, "visibility": "public"}
    try:
        r = requests.post(URLSCAN_SUBMIT, headers=headers, json=payload, timeout=20)
        if r.status_code in (200, 201):
            return {"uuid": r.json().get("uuid")}
        else:
            return {"error": f"submit failed HTTP {r.status_code}: {r.text}"}
    except Exception as e:
        return {"error": str(e)}

def fetch_urlscan_result(uuid):
    import requests
    try:
        r = requests.get(URLSCAN_RESULT.format(uuid=uuid), timeout=20)
        if r.status_code == 200:
            return r.json()
        elif r.status_code == 404:
            return None
        else:
            return {"error": f"HTTP {r.status_code}: {r.text}"}
    except Exception as e:
        return {"error": str(e)}

def save_attachment(filename, data):
    path = os.path.join(ATTACHMENT_SAVE_FOLDER, filename)
    base, ext = os.path.splitext(filename)
    i = 1
    while os.path.exists(path):
        path = os.path.join(ATTACHMENT_SAVE_FOLDER, f"{base}_{i}{ext}")
        i += 1
    with open(path, "wb") as f:
        f.write(data)
    return path

def handle_urls_with_urlscan(urls, timeout_seconds=30):
    results = []
    submissions = {}
    for url in urls:
        sub = submit_urlscan(url)
        r = {"url": url, "submit": sub, "verdict": "Unknown", "detail": None}
        results.append(r)
        if "uuid" in sub:
            submissions[sub["uuid"]] = r

    deadline = time.time() + timeout_seconds
    while submissions and time.time() < deadline:
        uuids = list(submissions.keys())
        for uuid in uuids:
            res = fetch_urlscan_result(uuid)
            r_entry = submissions.get(uuid)
            if r_entry is None:
                submissions.pop(uuid, None)
                continue
            if isinstance(res, dict) and res.get("error"):
                r_entry["verdict"] = "Error"
                r_entry["detail"] = res["error"]
                submissions.pop(uuid, None)
            elif res is None:
                continue
            else:
                verdicts = res.get("verdicts") or {}
                overall = verdicts.get("overall") or {}
                malicious = overall.get("malicious")
                suspicious = overall.get("suspicious")
                if malicious:
                    r_entry["verdict"] = "Malicious ❌"
                    r_entry["detail"] = overall
                elif suspicious:
                    r_entry["verdict"] = "Suspicious ⚠️"
                    r_entry["detail"] = overall
                else:
                    r_entry["verdict"] = "Safe ✅"
                    r_entry["detail"] = overall or res.get("page") or {}
                submissions.pop(uuid, None)
        if submissions:
            time.sleep(4)
    return results

# ---------- main loop ----------
def main_loop():
    seen = set()
    print("🔄 Monitoring inbox continuously...\n(Press Ctrl+C to stop)\n")
    while True:
        try:
            latest = get_latest_email()
            if latest is None:
                print("No messages found.")
                time.sleep(POLL_INTERVAL)
                continue

            # unpack returned value from read_gmail.get_latest_email (original code returns tuple)
            if len(latest) == 3:
                sender, subject, body = latest
                attachments = []
            elif len(latest) == 4:
                sender, subject, body, attachments = latest
            else:
                print("⚠️ Unexpected message format; skipping.")
                time.sleep(POLL_INTERVAL)
                continue

            email_id = (subject or "") + "|" + (sender or "")
            if email_id in seen:
                time.sleep(POLL_INTERVAL)
                continue

            snippet = (body or "")[:300].replace("\n", " ")
            spam_label = utils.classify_email(subject or "", body or "")
            social = utils.classify_social(body or "")

            print(f"\n📩 From: {sender}")
            print(f"📌 Subject: {subject}")
            print(f"📝 Snippet: {snippet}")
            print(f"🔎 Spam Classification: {spam_label}")
            if social.get("prob") is not None:
                print(
                    f"🎭 Social Engineering Probability: {social['prob']:.2f} "
                    f"(threshold={social.get('threshold', utils.SOCIAL_THRESHOLD)}) → {social['label']}"
                )
            else:
                print(f"🎭 Social Engineering: {social['label']}")

            # --- URL handling (summary only; do not print individual URLs) ---
            urls = extract_urls(body or "")
            unique_urls = list(set(urls))
            if unique_urls:
                url_results = handle_urls_with_urlscan(unique_urls, timeout_seconds=30)

                safe_count = 0
                malicious_count = 0
                suspicious_count = 0
                error_count = 0

                for r in url_results:
                    if r.get("submit", {}).get("uuid"):
                        verdict = r["verdict"]
                        if "Safe" in verdict:
                            safe_count += 1
                        elif "Malicious" in verdict:
                            malicious_count += 1
                        elif "Suspicious" in verdict:
                            suspicious_count += 1
                        else:
                            error_count += 1
                    else:
                        error_count += 1

                print(
                    f"📊 URL Summary: {safe_count} Safe ✅ | "
                    f"{malicious_count} Malicious ❌ | "
                    f"{suspicious_count} Suspicious ⚠️ | "
                    f"{error_count} Error(s) ⚠️"
                )
            # --- end URL handling ---

            if attachments:
                for fname, data in attachments:
                    path = save_attachment(fname, data)
                    print(f"📎 Attachment saved: {path}")

            seen.add(email_id)

        except KeyboardInterrupt:
            print("\nStopping monitor (KeyboardInterrupt).")
            break
        except Exception as e:
            print("⚠️ Error in main loop:", e)

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main_loop()
