import joblib
import re

# Reload model
model = joblib.load("url_model.pkl")

# Feature extraction (reuse function)
def extract_features(url):
    features = {}
    features["url_length"] = len(url)
    features["num_dots"] = url.count(".")
    features["has_https"] = 1 if url.startswith("https") else 0
    features["has_login"] = 1 if "login" in url.lower() else 0
    features["has_verify"] = 1 if "verify" in url.lower() else 0
    features["has_secure"] = 1 if "secure" in url.lower() else 0
    features["is_ip"] = 1 if re.match(r"^https?://\d+\.\d+\.\d+\.\d+", url) else 0
    return features

# Test URLs
urls = [
    "http://paypal.com.verify-login.ru",
    "https://google.com",
    "http://192.168.1.1/login",
    "https://secure-update.net"
]

for url in urls:
    pred = model.predict([list(extract_features(url).values())])[0]
    print(f"{url} --> {'Malicious' if pred == 1 else 'Safe'}")
