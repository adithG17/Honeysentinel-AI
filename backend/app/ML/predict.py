import joblib
import pandas as pd
from url_classifier.test_url_model import extract_features  

# Load the trained model (change path if needed)
model = joblib.load("C:\\Users\\adhit\\OneDrive\\Documents\\Visual studio Codes\\Codes\\Python\\Honeysentinel-AI\\backend\\app\\ML\\url_classifier\\url_model.pkl")

def scan_url(url: str) -> dict:
    """
    Scan a URL and return prediction and confidence.
    """
    features = extract_features(url)
    X = pd.DataFrame([features])
    
    # Get prediction
    pred = model.predict(X)[0]
    
    # Optional: get probability
    prob = model.predict_proba(X)[0][pred]
    
    return {
        "url": url,
        "prediction": "malicious" if pred == 1 else "benign",
        "confidence": round(prob, 3)
    }
