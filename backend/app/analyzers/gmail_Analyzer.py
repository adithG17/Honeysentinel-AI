import asyncio
import re
import dns.asyncresolver
from urllib.parse import urlparse


def validate_email_syntax(email_address):
    """Validate email syntax using RFC 5322 compliant regex"""
    # Comprehensive email validation regex (RFC 5322 compliant)
    email_regex = r'^[a-zA-Z0-9.!#$%&’*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*$'
    return re.match(email_regex, email_address) is not None


async def get_gmail_authenticity(gmail_address):
    """Check SPF, DKIM, DMARC, A records, and MX records for sender's domain."""

    # First validate email syntax
    if not validate_email_syntax(gmail_address):
        return {
            "domain": "",
            "SPF": ["Invalid email syntax"],
            "DKIM": ["Invalid email syntax"],
            "DMARC": ["Invalid email syntax"],
            "A_Records": ["Invalid email syntax"],
            "MX_Records": ["Invalid email syntax"],
            "syntax_valid": False,
            # ✅ Always include security_summary so frontend never breaks
            "security_summary": {
                "spf_status": "no_spf",
                "dkim_status": "no_dkim",
                "dmarc_status": "no_dmarc",
                "mx_status": "no_mx",
                "a_record_status": "no_a_record",
                "overall_status": "untrustworthy",
            },
        }

    domain_match = re.search(r'@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', gmail_address)

    if not domain_match:
        return {
            "domain": "",
            "SPF": ["Invalid email format"],
            "DKIM": ["Invalid email format"],
            "DMARC": ["Invalid email format"],
            "A_Records": ["Invalid email format"],
            "MX_Records": ["Invalid email format"],
            "syntax_valid": False,
            # ✅ Always include security_summary so frontend never breaks
            "security_summary": {
                "spf_status": "no_spf",
                "dkim_status": "no_dkim",
                "dmarc_status": "no_dmarc",
                "mx_status": "no_mx",
                "a_record_status": "no_a_record",
                "overall_status": "untrustworthy",
            },
        }

    domain = domain_match.group(1)
    resolver = dns.asyncresolver.Resolver()
    resolver.nameservers = ["1.1.1.1", "8.8.8.8"]
    resolver.lifetime = 3

    async def lookup(record_type, name):
        try:
            answers = await resolver.resolve(name, record_type)
            return [str(r) for r in answers]
        except dns.resolver.NXDOMAIN:
            return ["No record found"]
        except dns.resolver.NoAnswer:
            return ["No answer"]
        except dns.resolver.Timeout:
            return ["DNS lookup timed out"]
        except Exception as e:
            return [f"Lookup error: {str(e)}"]

    # Run all DNS lookups in parallel
    spf_task = lookup("TXT", domain)
    dkim_task = lookup("TXT", f"default._domainkey.{domain}")
    dmarc_task = lookup("TXT", f"_dmarc.{domain}")
    a_record_task = lookup("A", domain)
    mx_record_task = lookup("MX", domain)

    spf, dkim, dmarc, a_records, mx_records = await asyncio.gather(
        spf_task, dkim_task, dmarc_task, a_record_task, mx_record_task
    )

    # Analyze the results
    spf_status = analyze_spf(spf)
    dkim_status = analyze_dkim(dkim)
    dmarc_status = analyze_dmarc(dmarc)
    mx_status = analyze_mx(mx_records)
    a_record_status = analyze_a_records(a_records)

    return {
        "domain": domain,
        "SPF": spf,
        "DKIM": dkim,
        "DMARC": dmarc,
        "A_Records": a_records,
        "MX_Records": mx_records,
        "syntax_valid": True,
        "security_summary": {
            "spf_status": spf_status,
            "dkim_status": dkim_status,
            "dmarc_status": dmarc_status,
            "mx_status": mx_status,
            "a_record_status": a_record_status,
            "overall_status": determine_overall_status(spf_status, dkim_status, dmarc_status),
        },
    }


def analyze_spf(spf_records):
    """Analyze SPF records for security"""
    if "No record found" in spf_records:
        return "no_spf"
    if any("v=spf1" in record for record in spf_records):
        return "spf_configured"
    return "spf_invalid"


def analyze_dkim(dkim_records):
    """Analyze DKIM records"""
    if "No record found" in dkim_records:
        return "no_dkim"
    if any("v=DKIM1" in record or "k=rsa" in record for record in dkim_records):
        return "dkim_configured"
    return "dkim_invalid"


def analyze_dmarc(dmarc_records):
    """Analyze DMARC records"""
    if "No record found" in dmarc_records:
        return "no_dmarc"
    if any("v=DMARC1" in record for record in dmarc_records):
        # Check for policy strength
        for record in dmarc_records:
            if "p=reject" in record:
                return "dmarc_reject"
            elif "p=quarantine" in record:
                return "dmarc_quarantine"
            elif "p=none" in record:
                return "dmarc_none"
    return "dmarc_invalid"


def analyze_mx(mx_records):
    """Analyze MX records"""
    if "No record found" in mx_records:
        return "no_mx"
    if any(record for record in mx_records if "No record found" not in record):
        return "mx_configured"
    return "mx_invalid"


def analyze_a_records(a_records):
    """Analyze A records"""
    if "No record found" in a_records:
        return "no_a_record"
    if any(record for record in a_records if "No record found" not in record):
        return "a_records_exist"
    return "a_records_invalid"


def determine_overall_status(spf_status, dkim_status, dmarc_status):
    """Determine overall email authenticity status"""
    if (
        spf_status == "spf_configured"
        and dkim_status == "dkim_configured"
        and dmarc_status in ["dmarc_reject", "dmarc_quarantine"]
    ):
        return "highly_trustworthy"
    elif (
        spf_status == "spf_configured" or dkim_status == "dkim_configured"
    ):
        return "moderately_trustworthy"
    elif dmarc_status == "dmarc_none":
        return "low_trust"
    else:
        return "untrustworthy"


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


# Example usage and testing
async def test_email_authenticity():
    """Test function to demonstrate the enhanced email authenticity checker"""
    test_emails = [
        "test@gmail.com",
        "user@example.com",
        "invalid-email",
        "admin@google.com",
    ]

    for email in test_emails:
        print(f"\nChecking: {email}")
        result = await get_gmail_authenticity(email)
        print(f"Domain: {result.get('domain')}")
        print(f"Syntax Valid: {result['syntax_valid']}")
        print(f"SPF: {result['SPF']}")
        print(f"DKIM: {result['DKIM']}")
        print(f"DMARC: {result['DMARC']}")
        print(f"A Records: {result['A_Records']}")
        print(f"MX Records: {result['MX_Records']}")
        print(f"Security Summary: {result['security_summary']}")


if __name__ == "__main__":
    asyncio.run(test_email_authenticity())
