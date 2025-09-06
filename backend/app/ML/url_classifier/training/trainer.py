# backend/ml/trainer.py
import joblib
import pandas as pd
from backend.app.ML.url_classifier.training.db import fetch_all_for_training
from urllib.parse import urlparse
import re
import os

from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report

def numeric_features_from_url(url):
    parsed = urlparse(url)
    path = parsed.path or ""
    query = parsed.query or ""
    # numeric features we want
    return {
        "url_length": len(url),
        "num_dots": url.count("."),
        "num_params": 0 if query == "" else len(query.split("&")),
        "has_https": 1 if parsed.scheme == "https" else 0,
        "has_tracking": 1 if re.search(r"(utm_|utm=|clickid|fbclid|gclid|ref=|affiliate|promo|campaign)", url, re.I) else 0
    }

def build_dataframe(rows):
    # rows is list of (url, label)
    urls = []
    labels = []
    nums = []
    for url, label in rows:
        urls.append(url)
        labels.append(label)
        nums.append(numeric_features_from_url(url))
    df = pd.DataFrame({
        "url": urls,
        "label": labels
    })
    # append numeric columns
    nums_df = pd.DataFrame(nums)
    df = pd.concat([df, nums_df], axis=1)
    return df

def get_next_model_version(base_path, base_name):
    version = 1
    while os.path.exists(f"{base_path}/{base_name}v{version}.pkl"):
        version += 1
    return version

MODEL_BASE_NAME = "url_classifier_pipeline"
MODEL_DIR = "backend/app/ML/url_classifier/training/db"

def train_and_save():
    rows = fetch_all_for_training()
    if not rows or len(rows) < 50:
        print("Not enough training samples. Need at least ~50 labeled rows.")
        return

    df = build_dataframe(rows)
    # drop any rows with missing label
    df = df.dropna(subset=["label"]).reset_index(drop=True)

    X = df.drop(columns=["label"])
    y = df["label"]

    # ColumnTransformer: tfidf on 'url' + scaler on numeric columns
    numeric_cols = ["url_length", "num_dots", "num_params", "has_https", "has_tracking"]
    preprocessor = ColumnTransformer([
        ("tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(3,5)), "url"),
        ("num", StandardScaler(), numeric_cols)
    ], remainder="drop")

    pipeline = Pipeline([
        ("pre", preprocessor),
        ("clf", LogisticRegression(multi_class="multinomial", solver="lbfgs", max_iter=400, class_weight="balanced"))
    ])

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    pipeline.fit(X_train, y_train)

    # Evaluate
    y_pred = pipeline.predict(X_test)
    print(classification_report(y_test, y_pred))

    # Determine next model version
    next_version = get_next_model_version(MODEL_DIR, MODEL_BASE_NAME)
    model_path = f"{MODEL_DIR}/{MODEL_BASE_NAME}v{next_version}.pkl"

    # Save pipeline
    joblib.dump(pipeline, model_path)
    print("Saved model to", model_path)

if __name__ == "__main__":
    train_and_save()
