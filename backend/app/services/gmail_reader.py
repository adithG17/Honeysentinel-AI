import os
import base64
from email import message_from_bytes
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Gmail API scope
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
TOKEN_PATH = os.path.abspath("token.json")
CREDENTIALS_PATH = os.path.abspath("credentials.json")


def get_gmail_service():
    """Authenticate and return Gmail service."""
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

    return build('gmail', 'v1', credentials=creds)

def fetch_gmail_raw_message(message_id):
    """Fetch full raw RFC822 Gmail message"""
    service = get_gmail_service()   # <-- use your existing function
    raw_msg = service.users().messages().get(
        userId="me",
        id=message_id,
        format="raw"
    ).execute()
    raw_bytes = base64.urlsafe_b64decode(raw_msg["raw"].encode("UTF-8"))
    return raw_bytes



def get_gmail_body(payload):
    """Recursively search for best HTML or text/plain body from Gmail API payload."""
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

    return {
        "html": html_parts[0] if html_parts else None,
        "text": plain_parts[0] if plain_parts else None
    }


def get_gmail_body_from_raw(raw_msg):
    """Extract body from raw gmail message."""
    if raw_msg.is_multipart():
        for part in raw_msg.get_payload():
            content_type = part.get_content_type()
            if content_type == "text/html":
                return part.get_payload(decode=True).decode(errors="ignore")
            elif content_type == "text/plain":
                return part.get_payload(decode=True).decode(errors="ignore")
            else:
                result = get_gmail_body_from_raw(part)
                if result:
                    return result
    else:
        content_type = raw_msg.get_content_type()
        if content_type in ["text/html", "text/plain"]:
            return raw_msg.get_payload(decode=True).decode(errors="ignore")
    return ""


def fetch_gmail_messages(max_results=10):
    """Fetch Gmail messages metadata, body, attachments, and raw MIME (for DKIM/DMARC)."""
    service = get_gmail_service()
    result = service.users().messages().list(
        userId="me",
        maxResults=max_results,
        q="in:inbox -in:sent"
    ).execute()
    messages = result.get("messages", [])

    gmails = []
    for msg in messages:
        # Full fetch (for metadata, body, attachments)
        msg_data = service.users().messages().get(
            userId="me",
            id=msg["id"],
            format="full"
        ).execute()

        # Raw fetch (for authenticity checks)
        raw_msg_data = service.users().messages().get(
            userId="me",
            id=msg["id"],
            format="raw"
        ).execute()
        raw_email = base64.urlsafe_b64decode(raw_msg_data["raw"])

        headers = msg_data["payload"].get("headers", [])
        metadata = {
            "from": next((h["value"] for h in headers if h["name"].lower() == "from"), ""),
            "to": next((h["value"] for h in headers if h["name"].lower() == "to"), ""),
            "subject": next((h["value"] for h in headers if h["name"].lower() == "subject"), ""),
            "date": next((h["value"] for h in headers if h["name"].lower() == "date"), ""),
        }

        body_data = get_gmail_body(msg_data["payload"])

        attachments = []
        for part in msg_data["payload"].get("parts", []):
            if part.get("filename") and part["body"].get("attachmentId"):
                attachment = service.users().messages().attachments().get(
                    userId="me", messageId=msg["id"], id=part["body"]["attachmentId"]
                ).execute()

                attachment_data = attachment["data"]
                try:
                    standard_base64 = attachment_data.replace("-", "+").replace("_", "/")
                    decoded_data = base64.b64decode(standard_base64)
                    clean_base64 = base64.b64encode(decoded_data).decode("utf-8")
                except Exception:
                    clean_base64 = attachment_data

                attachments.append({
                    "filename": part["filename"],
                    "mime_type": part["mimeType"],
                    "data_base64": clean_base64,
                    "size": part.get("body", {}).get("size", 0),
                })

        gmails.append({
            "id": msg["id"],
            "metadata": metadata,
            "body_html": body_data["html"],
            "body_text": body_data["text"],
            "attachments": attachments,
            "raw_email": raw_email,  # ✅ added for authenticity checks
        })

    return gmails
