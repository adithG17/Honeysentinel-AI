
# Train a URL classification model using RandomForest that can classify URLs as benign or malicious and save it as url_model.pkl

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
import joblib

from backend.app.services.gmail_reader import extract_features

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
