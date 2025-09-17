# src/app.py
import streamlit as st
from read_gmail import get_latest_email
from main import classify_email, scan_url_urlscan   # your phishing logic

st.title("📩 PhishNet – Email Phishing Detector")

latest = get_latest_email()

if latest:
    sender = latest["sender"]
    subject = latest["subject"]
    body = latest["body"]
    links = latest["links"]

    st.subheader("📧 Latest Email")
    st.write(f"**From:** {sender}")
    st.write(f"**Subject:** {subject}")
    st.write(f"**Body:** {body[:500]}...")

    # classify email content
    classification = classify_email(sender, subject, body)
    st.write(f"🔎 Classification: {classification}")

    if links:
        st.subheader("🔗 Links found in email")
        for url in links:
            st.write(f"Checking: {url}")
            safe, verdict, result_url = scan_url_urlscan(url)

            if safe:
                st.success(f"✅ SAFE – {url} ({verdict})")
            else:
                st.error(f"⚠️ MALICIOUS – {url} ({verdict})")

            if result_url:
                st.write(f"[View full report]({result_url})")
