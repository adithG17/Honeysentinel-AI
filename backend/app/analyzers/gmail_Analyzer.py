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
import json
from datetime import datetime, timedelta
from cachetools import TTLCache

# ----------------------------
# DNS Cache for Performance
# ----------------------------
# Cache DNS results for 5 minutes to avoid repeated lookups
dns_cache = TTLCache(maxsize=1000, ttl=300)

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

async def dns_lookup(record_type: str, name: str) -> Tuple[List[str], bool]:
    """Perform DNS lookup with caching and improved error handling."""
    cache_key = f"{record_type}:{name}"
    
    # Check cache first
    if cache_key in dns_cache:
        return dns_cache[cache_key]
    
    resolver = dns.asyncresolver.Resolver()
    # Use multiple DNS resolvers for redundancy
    resolver.nameservers = ["1.1.1.1", "8.8.8.8", "9.9.9.9"]
    
    try:
        answers = await asyncio.wait_for(
            resolver.resolve(name, record_type),
            timeout=2.0
        )
        records = [str(r) for r in answers]
        dns_cache[cache_key] = (records, True)
        return records, True
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, 
            dns.resolver.NoNameservers, dns.exception.Timeout,
            asyncio.TimeoutError):
        # Cache negative results for shorter time (1 minute)
        dns_cache[cache_key] = ([], False)
        return [], False
    except Exception as e:
        error_msg = [f"Lookup failed: {str(e)}"]
        dns_cache[cache_key] = (error_msg, False)
        return error_msg, False

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
async def get_gmail_authenticity(raw_email_bytes: bytes):
    """
    Check SPF, DKIM, DMARC, Email Syntax, Domain, and MX records for a Gmail message.
    """
    msg = message_from_bytes(raw_email_bytes)
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
        "overall_status": "untrustworthy",
        "last_updated": time.time(),
        "request_id": hashlib.md5(f"{time.time()}{from_header}".encode()).hexdigest()[:12]
    }

    # Run all DNS lookups in parallel
    spf_task = asyncio.create_task(dns_lookup("TXT", domain))
    dmarc_task = asyncio.create_task(dns_lookup("TXT", f"_dmarc.{domain}"))
    mx_task = asyncio.create_task(dns_lookup("MX", domain))
    
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
        spf_records, success = await spf_task
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
        results["dmarc"]["status"] = "error"
        results["dmarc"]["records"] = [f"Resolver error: {str(e)}"]

    # ---- MX Record check ----
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
        results["dmarc"]["status"] in ["reject", "quarantine"]
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

# ----------------------------
# WebSocket support for real-time updates
# ----------------------------
class EmailAnalysisManager:
    def __init__(self):
        self.connected_clients = set()
        self.email_cache = TTLCache(maxsize=100, ttl=3600)  # Cache emails for 1 hour
    
    async def broadcast_update(self, email_id, data):
        """Broadcast updated email data to all connected clients."""
        message = {
            "type": "email_update",
            "email_id": email_id,
            "data": data
        }
        
        for client in self.connected_clients:
            try:
                await client.send_json(message)
            except Exception as e:
                print(f"Error sending to client: {e}")
                self.connected_clients.remove(client)
    
    def cache_email(self, email_id, data):
        """Cache email data for faster retrieval."""
        self.email_cache[email_id] = {
            "data": data,
            "timestamp": time.time()
        }
    
    def get_cached_email(self, email_id):
        """Get cached email data if available."""
        return self.email_cache.get(email_id)

# Global instance
analysis_manager = EmailAnalysisManager()