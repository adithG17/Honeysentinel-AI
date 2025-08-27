import asyncio
from concurrent.futures import ProcessPoolExecutor
import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
from googleapiclient.discovery import build
import base64
import requests
from sqlalchemy.orm import Session

from backend.app.services.message_analyzer import analyze_message
from backend.app.services.image_analyzer import analyze_image
from backend.app.services.audio_analyzer import analyze_audio
from backend.app.services.video_analyzer import analyze_video
from backend.app.services.gmail_reader import fetch_gmail_messages, fetch_gmail_raw_message
from backend.app.analyzers.gmail_analyzer import get_gmail_authenticity, extract_links
from backend.app.services.email_reader import extract_email_content, extract_msg_content_fast
from backend.app.db.database import get_db ,engine, SessionLocal
from backend.app.db.init_db import init_db, load_domains
from backend.app.db import models, schemas, crud


router = APIRouter()
EXECUTOR = ProcessPoolExecutor(max_workers=os.cpu_count() or 2)

# Store authenticity results
authenticity_results = {}

class MessageInput(BaseModel):
    message: str


@router.get("/")
def analyze_root():
    return {"message": "Welcome to HoneyBadger AI Analyzer! 🛡️"}


@router.get("/analyze/gmail")
async def analyze_gmail(max_results: int = 10):
    try:
        gmails = fetch_gmail_messages(max_results=max_results)
        analyzed_gmails = []

        for g in gmails:
            links = extract_links(g["body_html"]) if g["body_html"] else []

            analyzed_gmails.append({
                "id": g["id"],
                "metadata": g["metadata"],
                "body_html": g["body_html"],
                "body_text": g["body_text"],
                "attachments": g["attachments"],
                "links": links,
                # Don't include authenticity in initial load
                "authenticity_ready": False
            })

            # Initialize empty slot for authenticity results
            authenticity_results[g["id"]] = {
                "status": "pending",
                "data": None
            }

        return {"gmail_messages": analyzed_gmails}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analyze/gmail/{message_id}/authenticity")
async def get_email_authenticity(message_id: str, background_tasks: BackgroundTasks):
    """Get authenticity data for a specific email, processing if needed."""
    if message_id not in authenticity_results:
        return {"error": "Email not found"}
    
    # Check if we already have the result
    if authenticity_results[message_id]["status"] == "completed":
        return authenticity_results[message_id]["data"]
    
    # Check if already processing
    if authenticity_results[message_id]["status"] == "processing":
        return {"status": "processing"}
    
    # Start processing in background
    authenticity_results[message_id]["status"] = "processing"
    background_tasks.add_task(process_authenticity, message_id)
    
    return {"status": "processing"}


async def process_authenticity(message_id: str):
    """Process authenticity for a specific email."""
    try:
        raw_email_bytes = fetch_gmail_raw_message(message_id)
        authenticity = await get_gmail_authenticity(raw_email_bytes)
        authenticity_results[message_id] = {
            "status": "completed",
            "data": authenticity
        }
    except Exception as e:
        authenticity_results[message_id] = {
            "status": "error",
            "data": {"error": str(e)}
        }


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

@router.on_event("startup")
def on_startup():
    init_db()

@router.get("/load-domains")
def load_disposable_domains():
    load_domains()
    return {"message": "Domains loaded successfully!"}

@router.get("/check-domain/{email}")
def check_domain(email: str, db: Session = Depends(get_db)):
    domain = email.split("@")[-1]
    if crud.is_disposable(db, domain):
        return {"email": email, "domain": domain, "status": "Disposable email"}
    return {"email": email, "domain": domain, "status": "Legit email"}