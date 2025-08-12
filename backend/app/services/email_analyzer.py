import tempfile
import extract_msg
from email import message_from_bytes


def extract_email_content(content: bytes):
    """Extract details from a .eml email file."""
    msg = message_from_bytes(content)
    return {
        "from": msg.get("From", ""),
        "to": msg.get("To", ""),
        "subject": msg.get("Subject", ""),
        "date": msg.get("Date", ""),
        "html": get_html_from_eml(msg)
    }


def get_html_from_eml(msg):
    """Extract HTML body from .eml email."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                return part.get_payload(decode=True).decode(errors="ignore")
    elif msg.get_content_type() == "text/html":
        return msg.get_payload(decode=True).decode(errors="ignore")
    return ""


def extract_msg_content(content: bytes):
    """Extract details from a .msg Outlook file."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".msg") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    msg = extract_msg.Message(tmp_path)
    html_body = msg.htmlBody or msg.body or ""

    return {
        "from": msg.sender or "",
        "to": ", ".join(msg.to) if msg.to else "",
        "subject": msg.subject or "",
        "date": msg.date or "",
        "html": html_body
    }
