from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional
import os
from email import message_from_bytes


from backend.app.services.message_analyzer import analyze_message
from backend.app.services.image_analyzer import analyze_image
from backend.app.services.audio_analyzer import analyze_audio
from backend.app.services.video_analyzer import analyze_video
from backend.app.services.gmail_reader import fetch_gmail_messages
from backend.app.services.email_analyzer import extract_email_content
from backend.app.services.email_analyzer import extract_email_metadata
from backend.app.services.email_analyzer import analyze_email_html



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
async def analyze_email_upload(file: UploadFile = File(...)):
    content = await file.read()
    msg = message_from_bytes(content)

    # Extract metadata
    subject = msg.get("Subject", "")
    from_ = msg.get("From", "")
    to = msg.get("To", "")
    date = msg.get("Date", "")

    # Extract HTML body
    html_body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/html":
                html_body = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8")
                break
    else:
        if msg.get_content_type() == "text/html":
            html_body = msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8")

    # Analyze
    risk_score = analyze_email_html(html_body)

    return {
        "from": from_,
        "to": to,
        "subject": subject,
        "date": date,
        "html": html_body,
        "risk_score": risk_score,
    }


@router.post("/analyze/email/file")
async def analyze_email_file(file: UploadFile = File(...)):
    file_path = f"temp/{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())

    metadata = extract_email_metadata(file_path)
    score = analyze_email(metadata["body"])

    return {
        "risk_score": score,
        "metadata": metadata
    }


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
