from email import policy
from email.parser import BytesParser
import extract_msg
import tempfile
import os


def extract_email_content(raw_bytes: bytes) -> dict:
    """
    Extract metadata and content from .eml email bytes.
    """
    msg = BytesParser(policy=policy.default).parsebytes(raw_bytes)
    subject = msg['subject']
    sender = msg['from']
    to = msg['to']
    date = msg['date']

    html_content = None
    plain_text = None

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))

            if "attachment" in content_disposition:
                continue

            payload = part.get_payload(decode=True)
            if content_type == "text/html" and payload:
                html_content = payload.decode(errors="ignore")
            elif content_type == "text/plain" and payload:
                plain_text = payload.decode(errors="ignore")
    else:
        payload = msg.get_payload(decode=True)
        content_type = msg.get_content_type()
        if content_type == "text/html":
            html_content = payload.decode(errors="ignore")
        else:
            plain_text = payload.decode(errors="ignore")

    return {
        "from": sender or "",
        "to": to or "",
        "subject": subject or "",
        "date": date or "",
        "html": html_content or "",
        "text": plain_text or "",
    }


def extract_msg_content(raw_bytes: bytes) -> dict:
    """
    Extract metadata and content from .msg (Outlook) email bytes.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".msg") as temp_msg_file:
        temp_msg_file.write(raw_bytes)
        temp_msg_file_path = temp_msg_file.name

    try:
        msg = extract_msg.Message(temp_msg_file_path)
        msg.process()

        subject = msg.subject or ""
        sender = msg.sender or ""
        to = msg.to or ""
        date = msg.date or ""
        html_content = msg.htmlBody or ""
        plain_text = msg.body or ""

        return {
            "from": sender,
            "to": to,
            "subject": subject,
            "date": date,
            "html": html_content,
            "text": plain_text,
        }
    finally:
        os.unlink(temp_msg_file_path)


def analyze_email_html(content: str) -> float:
    """Basic heuristic analyzer for email HTML content."""
    if "click here" in content.lower() or "urgent" in content.lower():
        return 0.85
    return 0.2
