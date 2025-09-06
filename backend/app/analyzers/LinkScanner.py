import os
from dotenv import load_dotenv
import aiohttp
import joblib
import pandas as pd
from backend.app.services.gmail_reader import extract_features   # reuse your feature extractor
from backend.app.ML.url_classifier.training.predict import predict_url_category
# Load environment variables
load_dotenv()
GSB_API_KEY = os.getenv("GSB_API_KEY")

# Load ML model once (not inside function, so it doesn’t reload every request)
model = joblib.load("backend\\app\\ML\\url_classifier\\url_model.pkl")

# ---------- ML SCANNER OLD ONLY SCAM OR BEGNIN----------
def scan_url_with_ml(url: str) -> dict:
    """Scan a URL with the trained ML model"""
    features = extract_features(url)
    X = pd.DataFrame([features])

    pred = model.predict(X)[0]
    prob = model.predict_proba(X)[0][pred]

    return {
        "status": "unsafe" if pred == 1 else "safe",
        "details": [f"ML:{'malicious' if pred == 1 else 'benign'}"],
        "confidence": round(float(prob), 3)
    }


# ---------ML SCANNER NEW MULTICLASS----------


def scan_url_with_ml_new(url: str) -> dict:
    result = predict_url_category(url)
    # You can map categories into 'unsafe' vs 'safe' if needed
    category = result["category"]
    probs = result["probs"]
    # simple mapping for final_status; tune thresholds later
    if category in ("phishing", "malware"):
        final = "unsafe"
    else:
        final = "safe"  # marketing/general/trusted => safe but categorized
    return {
        "status": final,
        "category": category,
        "confidence": max(probs.values()),
        "probs": probs
    }


# ---------- GSB SCANNER ----------
async def scan_url_with_gsb(url: str) -> dict:
    """Scan a URL with Google Safe Browsing API"""
    if not GSB_API_KEY:
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
                if "matches" in data:
                    return {
                        "status": "unsafe",
                        "details": [m["threatType"] for m in data["matches"]],
                    }
                else:
                    return {"status": "safe", "details": []}
    except Exception as e:
        return {"status": "error", "details": [str(e)]}


# ---------- HYBRID SCANNER ----------
async def scan_url_hybrid(url: str) -> dict:
    ml_result = scan_url_with_ml(url)
    gsb_result = await scan_url_with_gsb(url)

    return {
        "url": url,
        "ml_status": ml_result["status"],
        "ml_confidence": ml_result.get("confidence"),
        "gsb_status": gsb_result["status"],
        "gsb_details": gsb_result.get("details", []),
        # Final decision: unsafe if either says unsafe
        "final_status": "unsafe" if (
            ml_result["status"] == "unsafe" or gsb_result["status"] == "unsafe"
        ) else "safe"
    }
