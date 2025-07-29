import cv2
import torch
from PIL import Image
from torchvision import transforms
import os

# Optional: load a nudity/NSFW model if available
try:
    from nsfw_detector import predict
    nsfw_model = predict.load_model()  # Automatically downloads and loads model
except:
    nsfw_model = None
    print("[WARN] NSFW model not loaded.")

# Load Haar cascade for face detection (OpenCV)
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

def detect_faces(image_path: str) -> bool:
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5)
    return len(faces) > 0

def detect_nsfw(image_path: str) -> float:
    if nsfw_model:
        predictions = predict.classify(nsfw_model, image_path)
        nsfw_score = predictions[image_path].get("porn", 0) + predictions[image_path].get("sexy", 0)
        return nsfw_score  # Between 0 and 1
    else:
        return 0.0  # Assume safe if model is not available

def analyze_image(image_path: str) -> float:
    print(f"[INFO] Analyzing image at {image_path}")
    
    # Check if file exists
    if not os.path.exists(image_path):
        print("[ERROR] Image file not found.")
        return 0.0

    # Step 1: Detect face
    has_face = detect_faces(image_path)
    print(f"  ➤ Face detected: {has_face}")

    # Step 2: NSFW detection
    nsfw_score = detect_nsfw(image_path)
    print(f"  ➤ NSFW score: {nsfw_score}")

    # Step 3: Risk scoring logic
    if nsfw_score > 0.7 and has_face:
        risk = 0.95  # Very risky (explicit + face)
    elif nsfw_score > 0.5:
        risk = 0.8   # Risky (possibly seductive)
    elif has_face:
        risk = 0.4   # Just face
    else:
        risk = 0.2   # Probably safe

    print(f"  ➤ Final risk score: {risk}")
    return round(risk, 2)
