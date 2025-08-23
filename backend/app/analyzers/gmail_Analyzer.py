import re
import asyncio
import dkim
from urllib.parse import urlparse
import dns.asyncresolver
from email.utils import parseaddr
from email import message_from_bytes
from typing import Dict, Any, List


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
    """Validate email syntax using RFC 5322 regex."""
    email_regex = r'^[a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*$'
    return re.match(email_regex, email_address) is not None


async def dns_lookup(record_type: str, name: str) -> List[str]:
    """Perform DNS lookup for a given record type using reliable resolvers."""
    resolver = dns.asyncresolver.Resolver()
    resolver.nameservers = ["1.1.1.1", "8.8.8.8"]  # Cloudflare + Google
    try:
        answers = await resolver.resolve(name, record_type, lifetime=3.0)
        return [str(r) for r in answers]
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers, dns.exception.Timeout):
        return []
    except Exception as e:
        return [f"Lookup failed: {str(e)}"]


def has_valid_spf(records: List[str]) -> bool:
    """Check if SPF records are valid."""
    if not records:
        return False
    return any("v=spf1" in record.lower() for record in records)


def has_valid_dkim(records: List[str]) -> bool:
    """Check if DKIM records are valid."""
    if not records:
        return False
    # Check for DKIM records (v=DKIM1 or contains DKIM-related content)
    return any("v=dkim1" in record.lower() for record in records)


def has_valid_dmarc(records: List[str]) -> bool:
    """Check if DMARC records are valid and have a reject policy."""
    if not records:
        return False
    
    for record in records:
        record_lower = record.lower()
        # Check if it's a DMARC record
        if "v=dmarc1" in record_lower:
            # Check if it has a reject policy (most secure)
            if "p=reject" in record_lower:
                return True
            # Also accept quarantine policy
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


# ----------------------------
# Email body extractor
# ----------------------------
def get_email_body(msg) -> str:
    """Extract the plain text or HTML body from an email message."""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/html":
                return part.get_payload(decode=True).decode(errors="ignore")
            elif content_type == "text/plain":
                return part.get_payload(decode=True).decode(errors="ignore")
    else:
        return msg.get_payload(decode=True).decode(errors="ignore")
    return ""


# ----------------------------
# Header-based authenticity
# ----------------------------
def parse_authentication_headers(msg) -> Dict[str, str]:
    """Extract SPF, DKIM, DMARC results from Gmail headers if available."""
    results = {"spf": "unknown", "dkim": "unknown", "dmarc": "unknown"}

    # SPF: Gmail usually sets "Received-SPF"
    spf_header = msg.get("Received-SPF")
    if spf_header:
        spf_header_lower = spf_header.lower()
        if "pass" in spf_header_lower:
            results["spf"] = "pass"
        elif "fail" in spf_header_lower:
            results["spf"] = "fail"
        elif "softfail" in spf_header_lower:
            results["spf"] = "softfail"
        elif "neutral" in spf_header_lower:
            results["spf"] = "neutral"

    # DKIM/DMARC: Gmail sets "Authentication-Results"
    auth_results = msg.get("Authentication-Results", "")
    auth_results_lower = auth_results.lower()
    
    if auth_results:
        # DKIM check
        if "dkim=pass" in auth_results_lower:
            results["dkim"] = "pass"
        elif "dkim=fail" in auth_results_lower:
            results["dkim"] = "fail"
        elif "dkim=neutral" in auth_results_lower:
            results["dkim"] = "neutral"

        # DMARC check
        if "dmarc=pass" in auth_results_lower:
            results["dmarc"] = "pass"
        elif "dmarc=fail" in auth_results_lower:
            results["dmarc"] = "fail"
        elif "dmarc=neutral" in auth_results_lower:
            results["dmarc"] = "neutral"

    return results


def extract_links(html_content):
    """Extract all hyperlinks from HTML content with enhanced validation."""
    if not html_content:
        return []

    # Improved regex to capture various link formats
    link_pattern = re.compile(
        r'<a\s+(?:[^>]*?\s+)?href=(["\'])(.*?)\1',
        re.IGNORECASE | re.MULTILINE,
    )

    links = []
    for match in link_pattern.finditer(html_content):
        url = match.group(2)

        # Skip javascript: and data: URLs for security
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
        except Exception as e:
            print(f"Error parsing URL {url}: {e}")
            continue

    return links


# ----------------------------
# Authenticity analyzer
# ----------------------------
def extract_dkim_info(msg) -> List[str]:
    """Extract DKIM selector(s) and domains from DKIM-Signature headers."""
    selectors = []
    for header in msg.get_all("DKIM-Signature", []):
        selector_match = re.search(r"s=([^;]+)", header)
        domain_match = re.search(r"d=([^;]+)", header)
        if selector_match and domain_match:
            selector = selector_match.group(1).strip()
            domain = domain_match.group(1).strip()
            selectors.append(f"{selector}._domainkey.{domain}")
    return selectors


async def get_gmail_authenticity(raw_email_bytes: bytes):
    """
    Check SPF, DKIM, DMARC, Email Syntax, Domain, and MX records for a Gmail message.
    """
    import email
    msg = email.message_from_bytes(raw_email_bytes)
    from_header = msg.get("From", "")
    domain = extract_domain(from_header)

    # Initialize results with consistent structure
    results = {
        "domain": domain,
        "email_syntax": validate_email_syntax(from_header),
        "spf": {"status": "not_configured", "records": []},
        "dkim": {"status": "not_configured", "records": []},
        "dmarc": {"status": "not_configured", "policy": "none", "records": []},
        "mx": {"status": "not_configured", "records": []},
        "overall_status": "untrustworthy"
    }

    # ---- Email Syntax ----
    results["email_syntax"] = validate_email_syntax(from_header)

    # ---- DKIM check ----
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

    # ---- SPF lookup ----
    try:
        spf_records = await dns_lookup("TXT", domain)
        results["spf"]["records"] = spf_records
        
        if has_valid_spf(spf_records):
            results["spf"]["status"] = "configured"
        else:
            results["spf"]["status"] = "not_configured"
    except Exception as e:
        results["spf"]["status"] = "error"
        results["spf"]["records"] = [f"Resolver error: {str(e)}"]

    # ---- DMARC lookup ----
    try:
        dmarc_records = await dns_lookup("TXT", f"_dmarc.{domain}")
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
        results["dmarc"]["status"] = "error"
        results["dmarc"]["records"] = [f"Resolver error: {str(e)}"]

    # ---- MX Record check ----
    try:
        mx_records = await dns_lookup("MX", domain)
        results["mx"]["records"] = mx_records
        
        if mx_records:
            results["mx"]["status"] = "configured"
        else:
            results["mx"]["status"] = "not_configured"
    except Exception as e:
        results["mx"]["status"] = "error"
        results["mx"]["records"] = [f"MX lookup failed: {str(e)}"]

    # ---- Overall status ----
    if (
        results["spf"]["status"] == "configured" and
        results["dkim"]["status"] == "pass" and
        results["dmarc"]["status"] == "reject"
    ):
        results["overall_status"] = "highly_trustworthy"
    elif (
        results["spf"]["status"] == "configured" or
        results["dkim"]["status"] == "pass" or
        results["dmarc"]["status"] == "reject" or
        results["dmarc"]["status"] == "quarantine"
    ):
        results["overall_status"] = "moderately_trustworthy"
    else:
        results["overall_status"] = "untrustworthy"

    return results

# ----------------------------
# Email body extractor
# ----------------------------
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
# Main service
# ----------------------------
async def analyze_gmail_message(raw_email: bytes) -> Dict[str, Any]:
    """Full Gmail analysis: metadata, body, authenticity."""
    msg = message_from_bytes(raw_email)

    from_address = msg.get("From", "")
    to_address = msg.get("To", "")
    subject = msg.get("Subject", "")
    date = msg.get("Date", "")
    
    # Extract both HTML and text parts
    html_body, text_body = get_email_parts(msg)
    
    # Extract links from HTML content
    links = extract_links(html_body) if html_body else []

    authenticity = await get_gmail_authenticity(raw_email)

    return {
        "metadata": {
            "from": from_address,
            "to": to_address,
            "subject": subject,
            "date": date,
        },
        "body_html": html_body,
        "body_text": text_body,
        "links": links,
        "authenticity": authenticity,
    }