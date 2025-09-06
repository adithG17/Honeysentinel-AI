
import joblib
import pandas as pd
from urllib.parse import urlparse
import re

MODEL_PATH = "backend/app/ML/url_classifier/training/db/url_classifier_pipeline.pkl"

def numeric_features_from_url(url):
    parsed = urlparse(url)
    path = parsed.path or ""
    query = parsed.query or ""
    return {
        "url_length": len(url),
        "num_dots": url.count("."),
        "num_params": 0 if query == "" else len(query.split("&")),
        "has_https": 1 if parsed.scheme == "https" else 0,
        "has_tracking": 1 if re.search(r"(utm_|utm=|clickid|fbclid|gclid|ref=|affiliate|promo|campaign)", url, re.I) else 0
    }

# Lazy load model
_pipeline = None
def load_pipeline():
    global _pipeline
    if _pipeline is None:
        _pipeline = joblib.load(MODEL_PATH)
    return _pipeline

def predict_url_category(url: str):
    pipeline = load_pipeline()
    nums = numeric_features_from_url(url)
    df = pd.DataFrame([{"url": url, **nums}])
    pred = pipeline.predict(df)[0]
    probs = pipeline.predict_proba(df)[0]
    classes = pipeline.named_steps["clf"].classes_
    prob_map = {cls: float(probs[i]) for i, cls in enumerate(classes)}
    return {"url": url, "category": pred, "probs": prob_map}
