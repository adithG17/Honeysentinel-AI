import os.path
import base64
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

CREDENTIALS_PATH = os.path.abspath("credentials.json")
TOKEN_PATH = os.path.abspath("token.json")

def extract_html_from_parts(parts):
    for part in parts:
        if part.get("mimeType") == "text/html":
            data = part["body"].get("data")
            if data:
                return base64.urlsafe_b64decode(data.encode()).decode()
        elif "parts" in part:  # Check nested parts
            html = extract_html_from_parts(part["parts"])
            if html:
                return html
    return None

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
    results = service.users().messages().list(userId='me', maxResults=5).execute()
    messages = results.get('messages', [])

    email_bodies = []
    for msg in messages:
        msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        payload = msg_data.get("payload", {})
        parts = payload.get("parts", [])
        html = extract_html_from_parts(parts)

        if html:
            email_bodies.append({"html": html})
        else:
            # fallback to snippet if no HTML found
            email_bodies.append({"html": f"<pre>{msg_data.get('snippet', 'No content')}</pre>"})

    return email_bodies
