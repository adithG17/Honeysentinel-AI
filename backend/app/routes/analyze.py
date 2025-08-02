from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional
import os


from backend.app.services.message_analyzer import analyze_message
from backend.app.services.image_analyzer import analyze_image
from backend.app.services.audio_analyzer import analyze_audio
from backend.app.services.video_analyzer import analyze_video
from backend.app.services.gmail_reader import fetch_gmail_messages
from backend.app.services.email_analyzer import extract_email_content, analyze_email



router = APIRouter()

class MessageInput(BaseModel):
    message: str

class EmailInput(BaseModel):
    content: str

@router.get("/")
def analyze_root():
    return {"message": "Welcome to HoneyBadger AI Analyzer!"}

@router.get("/analyze/gmail")
def analyze_gmail():
    try:
        emails = fetch_gmail_messages()
        return {"emails": emails}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/message")
def analyze_message_route(input: MessageInput):
    score = analyze_message(input.message)
    return {"risk_score": score}

@router.post("/analyze/email")
async def analyze_email_route(file: UploadFile = File(...)):
    try:
        # Save the uploaded file
        temp_dir = "temp"
        os.makedirs(temp_dir, exist_ok=True)
        file_path = os.path.join(temp_dir, file.filename)

        with open(file_path, "wb") as f:
            f.write(await file.read())

        score = analyze_email(file_path)
        return {"risk_score": score}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/analyze/email/file")
async def analyze_email_file(file: UploadFile = File(...)):
    file_content = await file.read()
    try:
        from backend.app.services.email_analyzer import extract_email_content, analyze_email

        email_data = extract_email_content(file_content)
        risk_score = analyze_email(email_data.get("html", "") + email_data.get("text", ""))
        return {
            "subject": email_data.get("subject", "No subject"),
            "from": email_data.get("from", "Unknown sender"),
            "html": email_data.get("html", ""),
            "risk_score": risk_score,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))





@router.post("/analyze/image")
async def analyze_image_route(file: UploadFile = File(...)):
    file_path = f"temp/{file.filename}"
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    score = analyze_image(file_path)
    return {"risk_score": score}

@router.post("/analyze/audio")
async def analyze_audio_route(file: UploadFile = File(...)):
    file_path = f"temp/{file.filename}"
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    score = analyze_audio(file_path)
    return {"risk_score": score}

@router.post("/analyze/video")
async def analyze_video_route(file: UploadFile = File(...)):
    file_path = f"temp/{file.filename}"
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    score = analyze_video(file_path)
    return {"risk_score": score}
