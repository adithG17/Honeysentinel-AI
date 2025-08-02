import os.path
import base64
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email import message_from_bytes
from bs4 import BeautifulSoup

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

CREDENTIALS_PATH = os.path.abspath("credentials.json")
TOKEN_PATH = os.path.abspath("token.json")

def extract_email_metadata(msg_data):
    headers = msg_data.get("payload", {}).get("headers", [])
    metadata = {"from": "", "to": "", "subject": "", "date": ""}
    for header in headers:
        name = header.get("name", "").lower()
        if name in metadata:
            metadata[name] = header.get("value", "")
    return metadata

def get_html_content(msg_data):
    payload = msg_data.get("payload", {})
    parts = payload.get("parts", [])

    # Traverse recursively to find HTML part
    def find_html(parts):
        for part in parts:
            if part.get("mimeType") == "text/html":
                data = part["body"].get("data")
                if data:
                    return base64.urlsafe_b64decode(data.encode()).decode()
            elif "parts" in part:
                result = find_html(part["parts"])
                if result:
                    return result
        return None

    html = find_html(parts)
    if html:
        return html

    # fallback: return snippet if no HTML found
    return msg_data.get("snippet", "[No HTML content]")

def fetch_gmail_messages():
    creds = None

    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())

    service = build('gmail', 'v1', credentials=creds)
    result = service.users().messages().list(userId='me', maxResults=10).execute()
    messages = result.get('messages', [])

    email_data = []
    for msg in messages:
        msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        meta = extract_email_metadata(msg_data)
        html_body = get_html_content(msg_data)
        email_data.append({**meta, "html": html_body})

    return email_data
