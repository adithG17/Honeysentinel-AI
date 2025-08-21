import asyncio
from concurrent.futures import ProcessPoolExecutor
import os
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from googleapiclient.discovery import build
import base64

from backend.app.services.message_analyzer import analyze_message
from backend.app.services.image_analyzer import analyze_image
from backend.app.services.audio_analyzer import analyze_audio
from backend.app.services.video_analyzer import analyze_video
from backend.app.services.gmail_reader import fetch_gmail_messages,fetch_gmail_raw_message
from backend.app.analyzers.gmail_analyzer import get_gmail_authenticity, extract_links
from backend.app.services.email_reader import extract_email_content
from backend.app.services.email_reader import extract_msg_content_fast

router = APIRouter()
EXECUTOR = ProcessPoolExecutor(max_workers=os.cpu_count() or 2)

class MessageInput(BaseModel):
    message: str


@router.get("/")
def analyze_root():
    return {"message": "Welcome to HoneyBadger AI Analyzer! 🛡️"}


from googleapiclient.discovery import build
import base64

@router.get("/analyze/gmail")
async def analyze_gmail(max_results: int = 10, include_authenticity: bool = True):
    try:
        gmails = fetch_gmail_messages(max_results=max_results)
        analyzed_gmails = []

        for g in gmails:
            links = extract_links(g["body_html"]) if g["body_html"] else []

            authenticity = None
            if include_authenticity:
                raw_email_bytes = fetch_gmail_raw_message(g["id"])
                authenticity = await get_gmail_authenticity(raw_email_bytes)

            analyzed_gmails.append({
                "id": g["id"],
                "metadata": g["metadata"],
                "body_html": g["body_html"],
                "body_text": g["body_text"],
                "attachments": g["attachments"],
                "links": links,
                "authenticity": authenticity or {
                "spf_status": "unknown",
                "dkim_status": "unknown",
                "dmarc_status": "unknown",
                "score": 0,
                "details": []
            }
            })

        return {"gmail_messages": analyzed_gmails}

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
        parsed = extract_msg_content_fast(content)
    else:
        parsed = extract_email_content(content)

    return parsed

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
