# read_gmail.py
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import base64
import html

# Load credentials
creds = Credentials.from_authorized_user_file("token.json")

# Build Gmail service
service = build("gmail", "v1", credentials=creds)

def get_latest_email():
    """
    Fetch the most recent Gmail (sender, subject, snippet of body)
    """
    results = service.users().messages().list(userId='me', maxResults=1).execute()
    messages = results.get('messages', [])
    if not messages:
        return None

    message = messages[0]
    msg = service.users().messages().get(userId='me', id=message['id']).execute()

    headers = msg['payload']['headers']
    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "(No Subject)")
    sender = next((h['value'] for h in headers if h['name'] == 'From'), "(Unknown Sender)")

    body = ""
    payload = msg['payload']

    # Check simple body
    if 'body' in payload and 'data' in payload['body']:
        body = base64.urlsafe_b64decode(payload['body']['data']).decode("utf-8", errors='ignore')
    # Check multi-part emails
    elif 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                body = base64.urlsafe_b64decode(part['body']['data']).decode("utf-8", errors='ignore')
                break
            elif part['mimeType'] == 'text/html' and 'data' in part['body']:
                body = base64.urlsafe_b64decode(part['body']['data']).decode("utf-8", errors='ignore')
                body = html.unescape(body)  # decode HTML entities
                break

    snippet = body[:300]  # show only first 300 characters
    return sender, subject, snippet
