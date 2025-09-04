import pandas as pd
import re
from urllib.parse import urlparse
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
import joblib

# -------- Feature Extraction --------
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

# -------- Load Data --------
df = pd.read_csv("data/urls.csv")

# Extract features for each URL
feature_list = [extract_features(url) for url in df["url"]]
X = pd.DataFrame(feature_list)

# Convert labels to binary (0=benign, 1=malicious)
y = df["label"].apply(lambda x: 1 if x in ["malicious", 1, "1"] else 0)

# -------- Train-Test Split --------
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# -------- Train Model with Full CPU Usage --------
model = RandomForestClassifier(
    n_estimators=1000,     # more trees for accuracy
    max_features="sqrt",  # balance performance
    random_state=42,
    n_jobs=-1,            # use all CPU cores
    verbose=1             # print progress
)
model.fit(X_train, y_train)

# -------- Evaluate --------
y_pred = model.predict(X_test)
print(classification_report(y_test, y_pred))

# -------- Save Model --------
joblib.dump(model, "url_model.pkl")
print("✅ Model saved as url_model.pkl")
