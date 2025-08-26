from transformers import pipeline

# Load model once when the service starts
classifier = pipeline("text-classification", model="distilbert-base-uncased")

def analyze_message(message: str):
    result = classifier(message)[0]

    # Simple honeytrap keyword detection
    keywords = ["alone", "private", "meet", "trust me", "secret"]
    keyword_hits = [word for word in keywords if word in message.lower()]

    return {
        "label": result['label'],
        "score": result['score'],
        "keywords_detected": keyword_hits,
        "honeytrap_risk": len(keyword_hits) > 1
    } //updated basic logic in message analyzer 

