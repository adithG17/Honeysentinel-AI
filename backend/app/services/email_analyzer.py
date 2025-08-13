import io
import extract_msg
from concurrent.futures import ProcessPoolExecutor
from email import message_from_bytes

def process_attachment(attachment):
    """Process a single attachment into previewable form."""
    try:
        filename = attachment.longFilename or attachment.shortFilename or "unnamed"
        data = attachment.data
        return {"filename": filename, "size": len(data), "data": data}
    except Exception as e:
        return {"error": str(e)}

def extract_msg_content_fast(msg_bytes):
    """Faster .msg parsing with parallelized attachment extraction."""
    msg_stream = io.BytesIO(msg_bytes)
    msg = extract_msg.Message(msg_stream)

    # Extract metadata
    result = {
        "from": msg.sender or "",
        "to": msg.to or "",
        "subject": msg.subject or "",
        "date": msg.date or "",
        "html": msg.htmlBody or msg.body or "",
        "attachments": []
    }

    attachments = msg.attachments
    if attachments:
        with ProcessPoolExecutor() as executor:
            results = list(executor.map(process_attachment, attachments))
        result["attachments"] = results

    return result

def extract_email_content(content: bytes):
    """Parse .eml file bytes -> dict with metadata + html/text (no attachments here)."""
    msg = message_from_bytes(content)

    html = ""
    text = ""

    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/html":
                payload = part.get_payload(decode=True)
                if payload:
                    html = payload.decode(errors="ignore")
            elif ctype == "text/plain" and not html:  # keep as fallback
                payload = part.get_payload(decode=True)
                if payload:
                    text = payload.decode(errors="ignore")
    else:
        ctype = msg.get_content_type()
        payload = msg.get_payload(decode=True)
        if payload:
            if ctype == "text/html":
                html = payload.decode(errors="ignore")
            else:
                text = payload.decode(errors="ignore")

    return {
        "from": msg.get("From", "") or "",
        "to": msg.get("To", "") or "",
        "subject": msg.get("Subject", "") or "",
        "date": msg.get("Date", "") or "",
        "html": html,
        "text": text,
        "attachments": [],  # .eml attachments can be added later if needed
    }
