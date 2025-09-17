# read_gmail.py
# Fetch latest Gmail message: (sender, subject, body_text, attachments)
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import base64
from bs4 import BeautifulSoup

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def _get_service(token_path='token.json'):
    """
    Load credentials from token.json (created by OAuth flow) and build Gmail service.
    """
    creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    service = build('gmail', 'v1', credentials=creds)
    return service

def _get_text_from_part(part):
    data = part.get('body', {}).get('data')
    if not data:
        return ''
    text = base64.urlsafe_b64decode(data.encode('utf-8')).decode('utf-8', errors='ignore')
    return text

def _extract_body_from_payload(payload):
    # Try payload.body -> parts -> nested parts
    if payload.get('body', {}).get('data'):
        return _get_text_from_part(payload)
    parts = payload.get('parts') or []
    texts = []
    for part in parts:
        mime = part.get('mimeType', '')
        if mime == 'text/plain' and part.get('body', {}).get('data'):
            texts.append(_get_text_from_part(part))
        elif mime == 'text/html' and part.get('body', {}).get('data'):
            html_txt = _get_text_from_part(part)
            texts.append(BeautifulSoup(html_txt, "html.parser").get_text())
        else:
            # nested parts
            subparts = part.get('parts') or []
            for sp in subparts:
                if sp.get('body', {}).get('data'):
                    if sp.get('mimeType') == 'text/plain':
                        texts.append(_get_text_from_part(sp))
                    elif sp.get('mimeType') == 'text/html':
                        html_txt = _get_text_from_part(sp)
                        texts.append(BeautifulSoup(html_txt, "html.parser").get_text())
    return "\n".join(texts).strip()

def _collect_attachments(service, user_id, msg):
    """
    Return list of (filename, bytes) for attachments in the message.
    """
    attachments = []
    payload = msg.get('payload', {})
    parts = payload.get('parts') or []
    for part in parts:
        filename = part.get('filename')
        body = part.get('body', {})
        if filename and (body.get('attachmentId') or body.get('data')):
            attachment_data = None
            if body.get('attachmentId'):
                att_id = body['attachmentId']
                att = service.users().messages().attachments().get(userId=user_id, messageId=msg['id'], id=att_id).execute()
                data = att.get('data')
                if data:
                    attachment_data = base64.urlsafe_b64decode(data.encode('utf-8'))
            elif body.get('data'):
                attachment_data = base64.urlsafe_b64decode(body['data'].encode('utf-8'))
            if attachment_data is not None:
                attachments.append((filename, attachment_data))
        # nested parts
        if part.get('parts'):
            for sp in part.get('parts'):
                fn = sp.get('filename')
                b = sp.get('body', {})
                if fn and (b.get('attachmentId') or b.get('data')):
                    attachment_data = None
                    if b.get('attachmentId'):
                        att_id = b['attachmentId']
                        att = service.users().messages().attachments().get(userId=user_id, messageId=msg['id'], id=att_id).execute()
                        data = att.get('data')
                        if data:
                            attachment_data = base64.urlsafe_b64decode(data.encode('utf-8'))
                    elif b.get('data'):
                        attachment_data = base64.urlsafe_b64decode(b['data'].encode('utf-8'))
                    if attachment_data is not None:
                        attachments.append((fn, attachment_data))
    return attachments

def get_latest_email(token_path='token.json'):
    """
    Fetch the most recent email.
    Returns: (sender, subject, body_text, attachments)
      - attachments: list of (filename, bytes). Empty list if none.
    """
    service = _get_service(token_path)
    res = service.users().messages().list(userId='me', maxResults=1).execute()
    msgs = res.get('messages', [])
    if not msgs:
        return None

    msg_id = msgs[0]['id']
    msg = service.users().messages().get(userId='me', id=msg_id, format='full').execute()

    headers = msg.get('payload', {}).get('headers', [])
    subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), "(No Subject)")
    sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), "(Unknown Sender)")

    body = _extract_body_from_payload(msg.get('payload', {}))
    if not body:
        # fallback to snippet
        body = msg.get('snippet', '')

    attachments = _collect_attachments(service, 'me', msg)

    return sender, subject, body, attachments
# read_gmail.py
# Fetch latest Gmail message: (sender, subject, body_text, attachments)
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import base64
from bs4 import BeautifulSoup

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def _get_service(token_path='token.json'):
    """
    Load credentials from token.json (created by OAuth flow) and build Gmail service.
    """
    creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    service = build('gmail', 'v1', credentials=creds)
    return service

def _get_text_from_part(part):
    data = part.get('body', {}).get('data')
    if not data:
        return ''
    text = base64.urlsafe_b64decode(data.encode('utf-8')).decode('utf-8', errors='ignore')
    return text

def _extract_body_from_payload(payload):
    # Try payload.body -> parts -> nested parts
    if payload.get('body', {}).get('data'):
        return _get_text_from_part(payload)
    parts = payload.get('parts') or []
    texts = []
    for part in parts:
        mime = part.get('mimeType', '')
        if mime == 'text/plain' and part.get('body', {}).get('data'):
            texts.append(_get_text_from_part(part))
        elif mime == 'text/html' and part.get('body', {}).get('data'):
            html_txt = _get_text_from_part(part)
            texts.append(BeautifulSoup(html_txt, "html.parser").get_text())
        else:
            # nested parts
            subparts = part.get('parts') or []
            for sp in subparts:
                if sp.get('body', {}).get('data'):
                    if sp.get('mimeType') == 'text/plain':
                        texts.append(_get_text_from_part(sp))
                    elif sp.get('mimeType') == 'text/html':
                        html_txt = _get_text_from_part(sp)
                        texts.append(BeautifulSoup(html_txt, "html.parser").get_text())
    return "\n".join(texts).strip()

def _collect_attachments(service, user_id, msg):
    """
    Return list of (filename, bytes) for attachments in the message.
    """
    attachments = []
    payload = msg.get('payload', {})
    parts = payload.get('parts') or []
    for part in parts:
        filename = part.get('filename')
        body = part.get('body', {})
        if filename and (body.get('attachmentId') or body.get('data')):
            attachment_data = None
            if body.get('attachmentId'):
                att_id = body['attachmentId']
                att = service.users().messages().attachments().get(userId=user_id, messageId=msg['id'], id=att_id).execute()
                data = att.get('data')
                if data:
                    attachment_data = base64.urlsafe_b64decode(data.encode('utf-8'))
            elif body.get('data'):
                attachment_data = base64.urlsafe_b64decode(body['data'].encode('utf-8'))
            if attachment_data is not None:
                attachments.append((filename, attachment_data))
        # nested parts
        if part.get('parts'):
            for sp in part.get('parts'):
                fn = sp.get('filename')
                b = sp.get('body', {})
                if fn and (b.get('attachmentId') or b.get('data')):
                    attachment_data = None
                    if b.get('attachmentId'):
                        att_id = b['attachmentId']
                        att = service.users().messages().attachments().get(userId=user_id, messageId=msg['id'], id=att_id).execute()
                        data = att.get('data')
                        if data:
                            attachment_data = base64.urlsafe_b64decode(data.encode('utf-8'))
                    elif b.get('data'):
                        attachment_data = base64.urlsafe_b64decode(b['data'].encode('utf-8'))
                    if attachment_data is not None:
                        attachments.append((fn, attachment_data))
    return attachments

def get_latest_email(token_path='token.json'):
    """
    Fetch the most recent email.
    Returns: (sender, subject, body_text, attachments)
      - attachments: list of (filename, bytes). Empty list if none.
    """
    service = _get_service(token_path)
    res = service.users().messages().list(userId='me', maxResults=1).execute()
    msgs = res.get('messages', [])
    if not msgs:
        return None

    msg_id = msgs[0]['id']
    msg = service.users().messages().get(userId='me', id=msg_id, format='full').execute()

    headers = msg.get('payload', {}).get('headers', [])
    subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), "(No Subject)")
    sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), "(Unknown Sender)")

    body = _extract_body_from_payload(msg.get('payload', {}))
    if not body:
        # fallback to snippet
        body = msg.get('snippet', '')

    attachments = _collect_attachments(service, 'me', msg)

    return sender, subject, body, attachments
