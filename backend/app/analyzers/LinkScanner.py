import os
from dotenv import load_dotenv
import aiohttp

# Load environment variables from .env
load_dotenv()

GSB_API_KEY = os.getenv("GSB_API_KEY")

print("✅ linkscanner.py module loaded successfully!")

async def scan_url_with_gsb(url: str) -> dict:
    """Scan a URL with Google Safe Browsing API"""
    print(f"🔍 Scanning URL: {url}")
    
    if not GSB_API_KEY:
        print("❌ WARNING: GSB_API_KEY not found in environment variables!")
        return {
            "status": "error",
            "details": ["GSB_API_KEY not configured"],
        }
    
    gsb_url = f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={GSB_API_KEY}"
    payload = {
        "client": {"clientId": "honeysentinel-ai", "clientVersion": "1.0"},
        "threatInfo": {
            "threatTypes": [
                "MALWARE",
                "SOCIAL_ENGINEERING",
                "UNWANTED_SOFTWARE",
                "POTENTIALLY_HARMFUL_APPLICATION"
            ],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": url}],
        },
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(gsb_url, json=payload) as resp:
                data = await resp.json()

                # Google returns {"matches": [...]} if threats are found
                if "matches" in data:
                    return {
                        "status": "unsafe",
                        "details": [m["threatType"] for m in data["matches"]],
                    }
                else:
                    return {
                        "status": "safe",
                        "details": [],
                    }
    except Exception as e:
        return {
            "status": "error",
            "details": [str(e)],
        }
