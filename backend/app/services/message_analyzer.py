# backend/app/services/message_analyzer.py

from transformers import pipeline
import re

# Load model once at startup (finetuned for sentiment classification)
classifier = pipeline("text-classification", model="distilbert-base-uncased-finetuned-sst-2-english")

def analyze_message(message: str):
    result = classifier(message)[0]

    # Keywords commonly associated with honeytrap manipulation
    keywords = ["alone", "private", "meet", "trust me", "secret"]
    keyword_hits = [kw for kw in keywords if re.search(rf"\b{re.escape(kw)}\b", message.lower())]

    # Simple honeytrap risk score logic
    risk_score = min(10, len(keyword_hits) * 2 + (result['score'] * 5))

    return {
        "label": result['label'],
        "score": round(result['score'], 3),
        "keywords_detected": keyword_hits,
        "honeytrap_risk": len(keyword_hits) > 1,
        "risk_score": round(risk_score, 2)
    }
