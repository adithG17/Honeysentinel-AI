import os
import base64
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
TOKEN_PATH = os.path.abspath("token.json")
CREDENTIALS_PATH = os.path.abspath("credentials.json")


def get_email_body(payload):
    """Recursively search for best HTML or text/plain body."""
    html_parts = []
    plain_parts = []

    def extract_parts(part):
        if part.get("parts"):
            for subpart in part["parts"]:
                extract_parts(subpart)
        else:
            mime_type = part.get("mimeType")
            data = part.get("body", {}).get("data")
            if data:
                decoded = base64.urlsafe_b64decode(data).decode(errors='replace').strip()
                if mime_type == "text/html":
                    html_parts.append(decoded)
                elif mime_type == "text/plain":
                    plain_parts.append(decoded)

    extract_parts(payload)

    # Heuristic: ignore fallback "cannot display HTML" placeholders
    def is_placeholder(content):
        return "email client cannot display HTML" in content.lower() or "view web version" in content.lower()

    html_parts = [html for html in html_parts if not is_placeholder(html)]

    return {
        "html": html_parts[0] if html_parts else None,
        "text": plain_parts[0] if plain_parts else None
    }


def fetch_gmail_messages():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=8080)
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())

    service = build('gmail', 'v1', credentials=creds)
    result = service.users().messages().list(userId='me', maxResults=5).execute()
    messages = result.get('messages', [])

    emails = []
    for msg in messages:
        msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()

        headers = msg_data['payload'].get('headers', [])
        metadata = {
            'from': next((h['value'] for h in headers if h['name'].lower() == 'from'), ''),
            'to': next((h['value'] for h in headers if h['name'].lower() == 'to'), ''),
            'subject': next((h['value'] for h in headers if h['name'].lower() == 'subject'), ''),
            'date': next((h['value'] for h in headers if h['name'].lower() == 'date'), '')
        }

        body_data = get_email_body(msg_data['payload'])

        attachments = []
        for part in msg_data['payload'].get("parts", []):
            if part.get("filename") and part["body"].get("attachmentId"):
                attachment = service.users().messages().attachments().get(
                    userId='me', messageId=msg['id'], id=part['body']['attachmentId']
                ).execute()
                attachments.append({
                    'filename': part['filename'],
                    'mime_type': part['mimeType'],
                    'data_base64': attachment['data']
                })

        emails.append({
            'metadata': metadata,
            'body_html': body_data["html"],
            'body_text': body_data["text"],
            'attachments': attachments
        })

    return emails
