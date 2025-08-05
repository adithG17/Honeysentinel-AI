import base64
from typing import Tuple, List, Dict
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import os

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
TOKEN_PATH = "token.json"
CREDS_PATH = "credentials.json"


# ----------  helpers  -------------------------------------------------
def _decode(b64: str) -> str:
    """URL-safe base64 → str, tolerant of padding."""
    if b64 is None:
        return ""
    padding = 4 - (len(b64) % 4)
    if padding and padding != 4:
        b64 += "=" * padding
    return base64.urlsafe_b64decode(b64.encode()).decode(errors="ignore")


def _walk_parts(part, svc, msg_id) -> Tuple[str, List[Dict]]:
    """
    Depth-first search until we find the first text/html (or text/plain) part.
    Collect attachments on the way.
    Returns: html_body, [attachments]
    """
    html_body = ""
    attachments: List[Dict] = []

    # 1️⃣ If this part is itself a leaf with data…
    mime = part.get("mimeType", "")
    body_data = part.get("body", {}).get("data")

    if mime in {"text/html", "text/plain"} and body_data:
        html_body = _decode(body_data)  # prefer html, but plain is OK

    # 2️⃣ Attachment?
    filename = part.get("filename")
    attach_id = part.get("body", {}).get("attachmentId")
    if filename and attach_id:
        raw = (
            svc.users()
            .messages()
            .attachments()
            .get(userId="me", messageId=msg_id, id=attach_id)
            .execute()
        )
        attachments.append(
            {
                "filename": filename,
                "mime_type": mime,
                "data_base64": raw["data"],
            }
        )

    # 3️⃣ Recurse into children (if any) **after** leaf check to keep
    #     the first text/html we find.
    for child in part.get("parts", []):
        child_html, child_atts = _walk_parts(child, svc, msg_id)
        if not html_body and child_html:
            html_body = child_html
        attachments.extend(child_atts)

    return html_body, attachments


# ----------  main entry  ---------------------------------------------
def fetch_gmail_messages(max_results: int = 5):
    # ---- auth boilerplate ----
    creds = (
        Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        if os.path.exists(TOKEN_PATH)
        else None
    )
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())

    svc = build("gmail", "v1", credentials=creds)

    # ---- pull the latest messages ----
    msg_list = (
        svc.users().messages().list(userId="me", maxResults=max_results).execute()
    ).get("messages", [])

    emails = []
    for m in msg_list:
        msg = svc.users().messages().get(userId="me", id=m["id"], format="full").execute()

        # grab header fields once
        headers = {h["name"].lower(): h["value"] for h in msg["payload"]["headers"]}
        metadata = {
            "from": headers.get("from", ""),
            "to": headers.get("to", ""),
            "subject": headers.get("subject", ""),
            "date": headers.get("date", ""),
        }

        # dig through the MIME tree ⛏️
        html_body, atts = _walk_parts(msg["payload"], svc, m["id"])

        emails.append(
            {
                "metadata": metadata,
                "body_html": html_body,  # note: we use body_html so React can `dangerouslySetInnerHTML`
                "attachments": atts,
            }
        )

    return emails
