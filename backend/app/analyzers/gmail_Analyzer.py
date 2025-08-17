import asyncio
import re
import dns.asyncresolver
from urllib.parse import urlparse


async def get_gmail_authenticity(gmail_address):
    """Check SPF, DKIM, and DMARC records for sender's domain."""
    gmail_pattern = r'@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
    domain_match = re.search(gmail_pattern, gmail_address)

    if not domain_match:
        return {
            "SPF": ["Invalid gmail format"],
            "DKIM": ["Invalid gmail format"], 
            "DMARC": ["Invalid gmail format"]
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

    spf_task = lookup("TXT", domain)
    dkim_task = lookup("TXT", f"default._domainkey.{domain}")
    dmarc_task = lookup("TXT", f"_dmarc.{domain}")

    spf, dkim, dmarc = await asyncio.gather(spf_task, dkim_task, dmarc_task)

    return {
        "domain": domain,
        "SPF": spf,
        "DKIM": dkim,
        "DMARC": dmarc
    }


def extract_links(html_content):
    """Extract all hyperlinks from HTML content."""
    if not html_content:
        return []

    link_pattern = re.compile(r'<a\s+(?:[^>]*?\s+)?href="([^"]*)"', re.IGNORECASE)
    links = link_pattern.findall(html_content)

    parsed_links = []
    for link in links:
        try:
            parsed = urlparse(link)
            if parsed.scheme in ('http', 'https', 'mailto'):
                parsed_links.append({
                    'url': link,
                    'domain': parsed.netloc,
                    'is_external': bool(parsed.netloc)
                })
        except:
            continue

    return parsed_links
