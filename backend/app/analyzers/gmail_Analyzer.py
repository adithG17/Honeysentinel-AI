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
    email_regex = r'^[a-zA-Z0-9.!#$%&’*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*$'
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
    return any("v=dkim1" in record.lower() or "dkim" in record.lower() for record in records)


def has_valid_dmarc(records: List[str]) -> bool:
    """Check if DMARC records are valid."""
    if not records:
        return False
    return any("v=dmarc1" in record.lower() for record in records)


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
    results = {"SPF": "", "DKIM": "", "DMARC": "", "MX": ""}  # Changed to empty strings
    security_summary = {
        "spf_status": "no_spf",
        "dkim_status": "no_dkim",
        "dmarc_status": "no_dmarc",
        "overall_status": "untrustworthy"
    }

    import email
    msg = email.message_from_bytes(raw_email_bytes)
    from_header = msg.get("From", "")
    domain = extract_domain(from_header)

    # ---- Email Syntax ----
    email_syntax_valid = validate_email_syntax(from_header)
    results["Email Syntax"] = "Valid" if email_syntax_valid else "Invalid"

    # ---- DKIM check ----
    try:
        if dkim.verify(raw_email_bytes):
            results["DKIM"] = "Pass"  # Changed from append to assignment
            security_summary["dkim_status"] = "dkim_configured"
        else:
            results["DKIM"] = "Fail"  # Changed from append to assignment
            security_summary["dkim_status"] = "dkim_invalid"
    except Exception as e:
        results["DKIM"] = f"Error: {str(e)}"  # Changed from append to assignment
        security_summary["dkim_status"] = "dkim_invalid"

    # ---- SPF & DMARC ----
    try:
        # SPF lookup
        spf_records = await dns_lookup("TXT", domain)
        if has_valid_spf(spf_records):
            results["SPF"] = "Found SPF record"  # Changed from append to assignment
            security_summary["spf_status"] = "spf_configured"
        else:
            results["SPF"] = "No valid SPF record"  # Changed from append to assignment
            security_summary["spf_status"] = "no_spf"

        # DMARC lookup
        dmarc_records = await dns_lookup("TXT", f"_dmarc.{domain}")
        if has_valid_dmarc(dmarc_records):
            results["DMARC"] = "Found DMARC record"  # Changed from append to assignment
            security_summary["dmarc_status"] = "dmarc_reject"
        else:
            results["DMARC"] = "No valid DMARC record"  # Changed from append to assignment
            security_summary["dmarc_status"] = "no_dmarc"

    except Exception as e:
        results["SPF"] = f"Resolver error: {str(e)}"  # Changed from append to assignment
        results["DMARC"] = f"Resolver error: {str(e)}"  # Changed from append to assignment

    # ---- MX Record check ----
    try:
        mx_records = await dns_lookup("MX", domain)
        if mx_records:
            results["MX"] = "Valid MX record(s) found"  # Changed from append to assignment
        else:
            results["MX"] = "No MX records found"  # Changed from append to assignment
    except Exception as e:
        results["MX"] = f"MX lookup failed: {str(e)}"  # Changed from append to assignment

    # ---- Overall status ----
    if (
        security_summary["spf_status"] == "spf_configured" and
        security_summary["dkim_status"] == "dkim_configured" and
        security_summary["dmarc_status"] == "dmarc_reject"
    ):
        security_summary["overall_status"] = "highly_trustworthy"
    elif (
        security_summary["spf_status"] == "spf_configured" or
        security_summary["dkim_status"] == "dkim_configured"
    ):
        security_summary["overall_status"] = "moderately_trustworthy"
    else:
        security_summary["overall_status"] = "untrustworthy"

    results["Domain"] = domain
    results["Email Syntax"] = "Valid" if email_syntax_valid else "Invalid"

    return {
        "results": results,
        "security_summary": security_summary,
    }




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
    body = get_email_body(msg)

    authenticity = await get_gmail_authenticity(raw_email)

    return {
        "metadata": {
            "from": from_address,
            "to": to_address,
            "subject": subject,
            "date": date,
        },
        "body": body,
        "authenticity": authenticity,
    }