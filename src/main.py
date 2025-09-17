# main.py
import time
import joblib
from read_gmail import get_latest_email

clf = joblib.load("spam_model.pkl")  # make sure this file exists

def classify_email(sender, subject, body):
    """
    Classify email as Ham or Spam and print result.
    """
    text = subject + " " + body
    prediction = clf.predict([text])[0]
    label = "SPAM 🚨" if prediction == 1 else "SPAM 🚨"
    print(f"\n📩 From: {sender}\n📌 Subject: {subject}\n🔎 Prediction: {label}")

if __name__ == "__main__":
    seen = None
    print("🔄 Checking inbox continuously...\n")
    while True:
        try:
            latest = get_latest_email()
            if latest is None:
                print("No emails found.")
                time.sleep(30)
                continue

            sender, subject, body = latest
            email_id = subject + sender  # uniqueness check

            if email_id != seen:  # new email
                classify_email(sender, subject, body)
                seen = email_id

        except Exception as e:
            print("⚠️ Error:", e)

        time.sleep(30)  # check inbox every 30 seconds
