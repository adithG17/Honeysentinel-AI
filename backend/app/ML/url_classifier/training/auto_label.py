# backend/ml/heuristics.py
from urllib.parse import urlparse
TRACKING_KEYWORDS = ["utm_", "utm=", "clickid", "fbclid", "gclid", "ref=", "affiliate", "aff_id", "campaign", "coupon", "promo", "newsletter"]

# Expand this list with domains you trust
TRUSTED_DOMAINS = {
    "google.com", "gmail.com", "github.com", "openai.com", "linkedin.com",
    "facebook.com", "twitter.com", "amazon.com", "paypal.com"
}

def domain_of(url):
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return None

def has_tracking_params(url):
    lower = url.lower()
    return any(k in lower for k in TRACKING_KEYWORDS)

def auto_label_url(url):
    dom = domain_of(url)
    if not dom:
        return None
    # If exactly in trusted list => trusted
    for t in TRUSTED_DOMAINS:
        if dom.endswith(t):
            return "trusted"
    # If has known tracking keywords => marketing
    if has_tracking_params(url):
        return "marketing"
    # simple heuristic for possible phishing suspicious words
    suspicious = ["verify", "account", "login", "banking", "secure", "reset-password", "update"]
    lower = url.lower()
    if any(s in lower for s in suspicious):
        # we mark as 'phishing_suspect' not definitive phishing
        return "phishing"
    return None
