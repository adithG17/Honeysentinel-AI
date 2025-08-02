from email import policy
from email.parser import BytesParser

def extract_email_content(raw_bytes: bytes) -> dict:
    msg = BytesParser(policy=policy.default).parsebytes(raw_bytes)
    subject = msg['subject']
    sender = msg['from']

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
        "subject": subject,
        "from": sender,
        "html": html_content or "",
        "text": plain_text or "",
    }



def extract_email_metadata(file_path: str):
    with open(file_path, 'rb') as f:
        msg = BytesParser(policy=policy.default).parse(f)

    metadata = {
        "from": msg["from"],
        "to": msg["to"],
        "subject": msg["subject"],
        "date": msg["date"],
        "body": msg.get_body(preferencelist=('html', 'plain')).get_content()
    }

    return metadata

def analyze_email_html(content: str) -> float:
    """Basic heuristic analyzer for email HTML content."""
    if "click here" in content.lower() or "urgent" in content.lower():
        return 0.85
    return 0.2
