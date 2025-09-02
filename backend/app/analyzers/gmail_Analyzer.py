import re
import asyncio
import dkim
from urllib.parse import urlparse
import dns.asyncresolver
from email.utils import parseaddr
from email import message_from_bytes
from typing import Dict, Any, List, Tuple
import time
import hashlib
from backend.app.analyzers.LinkScanner import scan_url_with_gsb

# Store email data and authenticity results
email_store = {
    "emails": [],
    "authenticity_results": {},
    "processing_status": {}
}

# ----------------------------
# Helpers
# ----------------------------

def extract_domain(email_address: str) -> str:
    """Safely extract domain from an email address using parseaddr."""
    _, addr = parseaddr(email_address)
    if not addr or "@" not in addr:
        return ""
    return addr.split("@")[-1].lower()

def validate_email_syntax(email_address: str) -> bool:
    """
    Validate email syntax by first extracting the email from header format.
    Returns True for valid email syntax, False otherwise.
    """
    _, parsed_email = parseaddr(email_address)
    
    if not parsed_email:
        parsed_email = email_address.strip()
    
    if not parsed_email or '@' not in parsed_email:
        return False
    
    email_regex = r'^[a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*$'
    
    return re.match(email_regex, parsed_email) is not None

async def dns_lookup(record_type: str, name: str) -> Tuple[List[str], bool]:
    """Perform DNS lookup without caching."""
    resolver = dns.asyncresolver.Resolver()
    resolver.nameservers = ["1.1.1.1", "8.8.8.8", "9.9.9.9"]
    
    try:
        answers = await asyncio.wait_for(
            resolver.resolve(name, record_type),
            timeout=2.0
        )
        records = [str(r) for r in answers]
        return records, True
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, 
            dns.resolver.NoNameservers, dns.exception.Timeout,
            asyncio.TimeoutError):
        return [], False
    except Exception as e:
        return [f"Lookup failed: {str(e)}"], False

def has_valid_spf(records: List[str]) -> bool:
    """Check if SPF records are valid."""
    if not records:
        return False
    return any("v=spf1" in record.lower() for record in records)

def has_valid_dkim(records: List[str]) -> bool:
    """Check if DKIM records are valid."""
    if not records:
        return False
    return any("v=dkim1" in record.lower() for record in records)

def has_valid_dmarc(records: List[str]) -> bool:
    """Check if DMARC records are valid and have a reject policy."""
    if not records:
        return False
    
    for record in records:
        record_lower = record.lower()
        if "v=dmarc1" in record_lower:
            if "p=reject" in record_lower:
                return True
            elif "p=quarantine" in record_lower:
                return True
    return False

def get_dmarc_policy(records: List[str]) -> str:
    """Extract the DMARC policy from records."""
    if not records:
        return "none"
    
    for record in records:
        record_lower = record.lower()
        if "v=dmarc1" in record_lower:
            if "p=reject" in record_lower:
                return "reject"
            elif "p=quarantine" in record_lower:
                return "quarantine"
            elif "p=none" in record_lower:
                return "none"
    return "none"

def extract_links(html_content):
    """Extract all hyperlinks from HTML content with enhanced validation."""
    if not html_content:
        return []

    link_pattern = re.compile(
        r'<a\s+(?:[^>]*?\s+)?href=(["\'])(.*?)\1',
        re.IGNORECASE | re.MULTILINE,
    )

    links = []
    for match in link_pattern.finditer(html_content):
        url = match.group(2)

        if url.startswith(("javascript:", "data:", "vbscript:")):
            continue

        try:
            parsed = urlparse(url)
            if parsed.scheme in ("http", "https", "mailto", "ftp"):
                links.append(
                    {
                        "url": url,
                        "domain": parsed.netloc,
                        "is_external": bool(parsed.netloc),
                        "scheme": parsed.scheme,
                        "path": parsed.path,
                        "query": parsed.query,
                        "fragment": parsed.fragment,
                    }
                )
        except Exception:
            continue

    return links

def get_email_parts(msg):
    """Extract both HTML and plain text parts from an email message."""
    html_body = None
    text_body = None

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/html" and html_body is None:
                html_body = part.get_payload(decode=True).decode(errors="ignore")
            elif content_type == "text/plain" and text_body is None:
                text_body = part.get_payload(decode=True).decode(errors="ignore")
    else:
        content_type = msg.get_content_type()
        payload = msg.get_payload(decode=True).decode(errors="ignore")
        if content_type == "text/html":
            html_body = payload
        else:
            text_body = payload

    return html_body, text_body

# ----------------------------
# Authenticity analyzer
# ----------------------------
async def get_gmail_authenticity(raw_email_bytes: bytes):
    """
    Check SPF, DKIM, DMARC, Email Syntax, Domain, and MX records for a Gmail message.
    """
    msg = message_from_bytes(raw_email_bytes)
    from_header = msg.get("From", "")
    domain = extract_domain(from_header)

    results = {
        "domain": domain,
        "email_syntax": validate_email_syntax(from_header),
        "spf": {"status": "not_configured", "records": []},
        "dkim": {"status": "not_configured", "records": []},
        "dmarc": {"status": "not_configured", "policy": "none", "records": []},
        "mx": {"status": "not_configured", "records": []},
        "overall_status": "untrustworthy",
        "last_updated": time.time(),
        "request_id": hashlib.md5(f"{time.time()}{from_header}".encode()).hexdigest()[:12]
    }

    spf_task = asyncio.create_task(dns_lookup("TXT", domain))
    dmarc_task = asyncio.create_task(dns_lookup("TXT", f"_dmarc.{domain}"))
    mx_task = asyncio.create_task(dns_lookup("MX", domain))
    
    results["email_syntax"] = validate_email_syntax(from_header)

    # DKIM check
    try:
        if dkim.verify(raw_email_bytes):
            results["dkim"]["status"] = "pass"
            results["dkim"]["records"] = ["DKIM verification passed"]
        else:
            results["dkim"]["status"] = "fail"
            results["dkim"]["records"] = ["DKIM verification failed"]
    except Exception as e:
        results["dkim"]["status"] = "error"
        results["dkim"]["records"] = [f"Error: {str(e)}"]

    # SPF lookup
    try:
        spf_records, success = await spf_task
        results["spf"]["records"] = spf_records
        
        if has_valid_spf(spf_records):
            results["spf"]["status"] = "configured"
        else:
            results["spf"]["status"] = "not_configured"
    except Exception as e:
        results["spf"]["status"] = "error"
        results["spf"]["records"] = [f"Resolver error: {str(e)}"]

    # DMARC lookup
    try:
        dmarc_records, success = await dmarc_task
        results["dmarc"]["records"] = dmarc_records
        
        dmarc_policy = get_dmarc_policy(dmarc_records)
        results["dmarc"]["policy"] = dmarc_policy
        
        if dmarc_policy == "reject":
            results["dmarc"]["status"] = "reject"
        elif dmarc_policy == "quarantine":
            results["dmarc"]["status"] = "quarantine"
        elif dmarc_policy == "none":
            results["dmarc"]["status"] = "none"
        else:
            results["dmarc"]["status"] = "not_configured"
    except Exception as e:
        results["dmarc"]["status": "error"]
        results["dmarc"]["records"] = [f"Resolver error: {str(e)}"]

    # MX Record check
    try:
        mx_records, success = await mx_task
        results["mx"]["records"] = mx_records
        
        if mx_records:
            results["mx"]["status"] = "configured"
        else:
            results["mx"]["status"] = "not_configured"
    except Exception as e:
        results["mx"]["status"] = "error"
        results["mx"]["records"] = [f"MX lookup failed: {str(e)}"]

    # Overall status
    if (
        results["spf"]["status"] == "configured" and
        results["dkim"]["status"] == "pass" and
        results["dmarc"]["status"] == "reject"
    ):
        results["overall_status"] = "highly_trustworthy"
    elif (
        results["spf"]["status"] == "configured" or
        results["dkim"]["status"] == "pass" or
        results["dmarc"]["status"] in ["reject", "quarantine"]
    ):
        results["overall_status"] = "moderately_trustworthy"
    else:
        results["overall_status"] = "untrustworthy"

    return results

async def analyze_gmail_message(raw_email: bytes) -> Dict[str, Any]:
    """Extract email metadata + run link scanning"""
    msg = message_from_bytes(raw_email)
    from_address = msg.get("From", "")
    to_address = msg.get("To", "")
    subject = msg.get("Subject", "")
    date = msg.get("Date", "")
    
    html_body, text_body = get_email_parts(msg)
    links = extract_links(html_body) if html_body else []

    scanned_links = []
    
    if links:
        try:
            tasks = [scan_url_with_gsb(link["url"]) for link in links]
            scan_results = await asyncio.gather(*tasks)
            
            for i, (original_link, scan_result) in enumerate(zip(links, scan_results)):
                scanned_link = original_link.copy()
                scanned_link["scan_status"] = scan_result.get("status", "unknown")
                scanned_link["scan_details"] = scan_result.get("details", [])
                scanned_links.append(scanned_link)
                
        except Exception as e:
            scanned_links = links
            for link in scanned_links:
                link["scan_status"] = "error"
                link["scan_details"] = [str(e)]
    else:
        scanned_links = links

    return {
        "metadata": {
            "from": from_address,
            "to": to_address,
            "subject": subject,
            "date": date,
        },
        "body_html": html_body,
        "body_text": text_body,
        "links": scanned_links,
    }

async def process_authenticity(email_index: int):
    """Process authenticity for a specific email."""
    try:
        raw_email = b""
        authenticity = await get_gmail_authenticity(raw_email)
        email_store["authenticity_results"][email_index] = authenticity
    except Exception as e:
        email_store["authenticity_results"][email_index] = {"error": str(e)}
    finally:
        email_store["processing_status"][email_index] = False