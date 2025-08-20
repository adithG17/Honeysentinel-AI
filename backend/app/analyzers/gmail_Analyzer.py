import re
import asyncio
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
async def get_gmail_authenticity(email_address: str, msg=None) -> Dict[str, Any]:
    """Check SPF, DKIM, DMARC, MX, and A records for a given email sender."""

    domain = extract_domain(email_address)

    if not domain:
        return {
            "domain": "",
            "SPF": ["Invalid email format"],
            "DKIM": ["Invalid email format"],
            "DMARC": ["Invalid email format"],
            "A_Records": ["Invalid email format"],
            "MX_Records": ["Invalid email format"],
            "syntax_valid": False,
            "security_summary": {
                "spf_status": "no_spf",
                "dkim_status": "no_dkim",
                "dmarc_status": "no_dmarc",
                "mx_status": "no_mx",
                "a_record_status": "no_a_record",
                "overall_status": "untrustworthy",
            },
        }

    # Step 1: try parsing headers (Gmail already validates auth)
    header_results = parse_authentication_headers(msg) if msg else {}

    # Step 2: DNS lookups for completeness
    spf_task = asyncio.create_task(dns_lookup("TXT", domain))
    dkim_task = asyncio.create_task(dns_lookup("TXT", f"selector1._domainkey.{domain}"))
    # Try multiple common DKIM selectors
    dkim_task2 = asyncio.create_task(dns_lookup("TXT", f"default._domainkey.{domain}"))
    dkim_task3 = asyncio.create_task(dns_lookup("TXT", f"dkim._domainkey.{domain}"))
    dmarc_task = asyncio.create_task(dns_lookup("TXT", f"_dmarc.{domain}"))
    mx_task = asyncio.create_task(dns_lookup("MX", domain))
    a_task = asyncio.create_task(dns_lookup("A", domain))

    SPF, DKIM1, DKIM2, DKIM3, DMARC, MX, A_records = await asyncio.gather(
        spf_task, dkim_task, dkim_task2, dkim_task3, dmarc_task, mx_task, a_task
    )

    # Combine all DKIM results
    DKIM = DKIM1 + DKIM2 + DKIM3

    # Determine status based on headers first, then fall back to DNS
    def get_status(header_key: str, dns_records: List[str], validation_func) -> str:
        header_status = header_results.get(header_key, "unknown")
        
        if header_status != "unknown":
            return header_status
        
        # Fall back to DNS validation
        if validation_func(dns_records):
            return "pass"
        elif any("Lookup failed" in record for record in dns_records):
            return "no_record"
        else:
            return "fail"

    spf_status = get_status("spf", SPF, has_valid_spf)
    dkim_status = get_status("dkim", DKIM, has_valid_dkim)
    dmarc_status = get_status("dmarc", DMARC, has_valid_dmarc)
    mx_status = "pass" if MX and not any("Lookup failed" in record for record in MX) else "no_mx"
    a_record_status = "pass" if A_records and not any("Lookup failed" in record for record in A_records) else "no_a_record"

    # Overall trust assessment
    if (spf_status == "pass" and dmarc_status == "pass" and 
        dkim_status in ["pass", "unknown"] and mx_status == "pass" and a_record_status == "pass"):
        overall_status = "trustworthy"
    elif (spf_status in ["no_spf", "fail"] or dmarc_status in ["no_dmarc", "fail"] or 
          mx_status == "no_mx" or a_record_status == "no_a_record"):
        overall_status = "suspicious"
    else:
        overall_status = "partially_trustworthy"

    security_summary = {
        "spf_status": spf_status,
        "dkim_status": dkim_status,
        "dmarc_status": dmarc_status,
        "mx_status": mx_status,
        "a_record_status": a_record_status,
        "overall_status": overall_status,
    }

    return {
        "domain": domain,
        "SPF": SPF,
        "DKIM": DKIM,
        "DMARC": DMARC,
        "A_Records": A_records,
        "MX_Records": MX,
        "syntax_valid": validate_email_syntax(email_address),
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

    authenticity = await get_gmail_authenticity(from_address, msg)

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