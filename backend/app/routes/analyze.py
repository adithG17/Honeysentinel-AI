from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from backend.app.services.message_analyzer import analyze_message
from backend.app.services.image_analyzer import analyze_image
from backend.app.services.audio_analyzer import analyze_audio
from backend.app.services.video_analyzer import analyze_video
from backend.app.services.gmail_reader import fetch_gmail_messages
from backend.app.services.email_analyzer import (
    extract_email_content,
    extract_msg_content
)

router = APIRouter()

class MessageInput(BaseModel):
    message: str


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
async def analyze_email_upload(file: UploadFile = File(...)):
    content = await file.read()

    if file.filename.lower().endswith(".msg"):
        parsed = extract_msg_content(content)
    else:
        parsed = extract_email_content(content)

    return {
        "from": parsed.get("from", ""),
        "to": parsed.get("to", ""),
        "subject": parsed.get("subject", ""),
        "date": parsed.get("date", ""),
        "html": parsed.get("html", "")
    }



@router.post("/analyze/image")
async def analyze_image_route(file: UploadFile = File(...)):
    file_path = f"temp/{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())
    score = analyze_image(file_path)
    return {"risk_score": score}


@router.post("/analyze/audio")
async def analyze_audio_route(file: UploadFile = File(...)):
    file_path = f"temp/{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())
    score = analyze_audio(file_path)
    return {"risk_score": score}


@router.post("/analyze/video")
async def analyze_video_route(file: UploadFile = File(...)):
    file_path = f"temp/{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())
    score = analyze_video(file_path)
    return {"risk_score": score}
