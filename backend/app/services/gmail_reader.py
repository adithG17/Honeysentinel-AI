import os
import base64
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
TOKEN_PATH = os.path.abspath("token.json")
CREDENTIALS_PATH = os.path.abspath("credentials.json")

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

        body = ''
        parts = msg_data['payload'].get('parts', [])
        attachments = []

        for part in parts:
            if part['mimeType'] == 'text/html':
                data = part['body'].get('data')
                if data:
                    body = base64.urlsafe_b64decode(data).decode()
            elif part['filename']:
                attach_id = part['body'].get('attachmentId')
                if attach_id:
                    attachment = service.users().messages().attachments().get(
                        userId='me', messageId=msg['id'], id=attach_id
                    ).execute()
                    file_data = attachment['data']
                    attachments.append({
                        'filename': part['filename'],
                        'mime_type': part['mimeType'],
                        'data_base64': file_data
                    })

        emails.append({
            'metadata': metadata,
            'body': body,
            'attachments': attachments
        })

    return emails
