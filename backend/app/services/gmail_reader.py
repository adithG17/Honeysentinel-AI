import os
import base64
import asyncio
import re
from email.utils import parsedate_to_datetime
from email import message_from_bytes
import dns.asyncresolver
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

def get_email_body(payload):
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

    # Heuristic: ignore fallback "cannot display HTML" placeholders
    def is_placeholder(content):
        return ("email client cannot display HTML" in content.lower() or 
                "view web version" in content.lower())

    html_parts = [html for html in html_parts if not is_placeholder(html)]

    return {
        "html": html_parts[0] if html_parts else None,
        "text": plain_parts[0] if plain_parts else None
    }

def get_email_body_from_raw(raw_msg):
    """Extract body from raw email message."""
    if raw_msg.is_multipart():
        for part in raw_msg.get_payload():
            content_type = part.get_content_type()
            if content_type == "text/html":
                return part.get_payload(decode=True).decode(errors="ignore")
            elif content_type == "text/plain":
                return part.get_payload(decode=True).decode(errors="ignore")
            else:
                result = get_email_body_from_raw(part)
                if result:
                    return result
    else:
        content_type = raw_msg.get_content_type()
        if content_type in ["text/html", "text/plain"]:
            return raw_msg.get_payload(decode=True).decode(errors="ignore")
    return ""

async def get_email_authenticity(email_address):
    """Check SPF, DKIM, and DMARC records with improved domain extraction."""
    # Improved email pattern that handles various formats:
    # user@domain.com, "Name" <user@domain.com>, user@sub.domain.com
    email_pattern = r'@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
    domain_match = re.search(email_pattern, email_address)
    
    if not domain_match:
        return {
            "SPF": ["Invalid email format"],
            "DKIM": ["Invalid email format"], 
            "DMARC": ["Invalid email format"]
        }

    domain = domain_match.group(1)
    
    resolver = dns.asyncresolver.Resolver()
    resolver.nameservers = ["1.1.1.1", "8.8.8.8"]  # Cloudflare + Google DNS
    resolver.lifetime = 3  # Timeout in seconds

    async def lookup(record_type, name):
        try:
            answers = await resolver.resolve(name, record_type)
            return [str(r) for r in answers]
        except dns.resolver.NXDOMAIN:
            return ["No record found"]
        except dns.resolver.NoAnswer:
            return ["No answer"]
        except dns.resolver.Timeout:
            return ["DNS lookup timed out"]
        except Exception as e:
            return [f"Lookup error: {str(e)}"]

    # Run all DNS lookups in parallel
    spf_task = lookup("TXT", domain)
    dkim_task = lookup("TXT", f"default._domainkey.{domain}")
    dmarc_task = lookup("TXT", f"_dmarc.{domain}")

    spf, dkim, dmarc = await asyncio.gather(spf_task, dkim_task, dmarc_task)

    return {
        "domain": domain,  # Include the detected domain for debugging
        "SPF": spf,
        "DKIM": dkim,
        "DMARC": dmarc
    }
async def fetch_gmail_messages(max_results=10, include_authenticity=False):
    service = get_gmail_service()
    result = service.users().messages().list(
        userId='me',
        maxResults=max_results,
        q='in:inbox -in:sent'
    ).execute()
    messages = result.get('messages', [])

    emails = []
    for msg in messages:
        # Get both full and raw message data
        msg_data = service.users().messages().get(
            userId='me',
            id=msg['id'],
            format='full'
        ).execute()

        # Always get the From address from headers
        headers = msg_data['payload'].get('headers', [])
        from_addr = next((h['value'] for h in headers if h['name'].lower() == 'from'), '')

        # Only get raw message if needed for authenticity checks
        if include_authenticity:
            raw_msg = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='raw'
            ).execute()
            raw_data = base64.urlsafe_b64decode(raw_msg['raw'].encode("UTF-8"))
            email_msg = message_from_bytes(raw_data)
        else:
            email_msg = None

        metadata = {
            'from': from_addr,
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

        # Perform authenticity checks if requested
        authenticity = None
        if include_authenticity and from_addr:
            authenticity = await get_email_authenticity(from_addr)

        emails.append({
            'id': msg['id'],
            'metadata': metadata,
            'body_html': body_data["html"],
            'body_text': body_data["text"],
            'attachments': attachments,
            'authenticity': authenticity
        })

    return emails