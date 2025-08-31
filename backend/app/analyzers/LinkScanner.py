import os
import httpx
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GSB_API_KEY")
GSB_URL = f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={API_KEY}"

async def scan_url_with_gsb(url: str) -> dict:
    """
    Scan a URL with Google Safe Browsing API.
    Returns threat details if found, otherwise safe.
    """
    payload = {
        "client": {
            "clientId": "honeysentinel-ai",
            "clientVersion": "1.0"
        },
        "threatInfo": {
            "threatTypes": [
                "MALWARE",
                "SOCIAL_ENGINEERING",
                "UNWANTED_SOFTWARE",
                "POTENTIALLY_HARMFUL_APPLICATION"
            ],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": url}]
        }
    }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(GSB_URL, json=payload)
        data = resp.json()

        if data and "matches" in data:
            return {
                "url": url,
                "status": "malicious",
                "details": data["matches"]
            }
        else:
            return {
                "url": url,
                "status": "safe",
                "details": []
            }
