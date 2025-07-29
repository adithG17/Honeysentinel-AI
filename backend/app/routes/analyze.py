import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional

from app.services.message_analyzer import analyze_message
from app.services.email_analyzer import analyze_email
from app.services.image_analyzer import analyze_image
from app.services.audio_analyzer import analyze_audio
from app.services.video_analyzer import analyze_video

router = APIRouter()


# ==== Request Models ====
class MessageInput(BaseModel):
    message: str


class EmailInput(BaseModel):
    content: str


# ==== Routes ====

@router.get("/")
def analyze_root():
    return {"message": "Welcome to HoneyBadger AI Analyzer!"}


@router.post("/analyze/message")
def analyze_message_route(input: MessageInput):
    try:
        result = analyze_message(input.message)
        return {"status": "success", "type": "message", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/email")
def analyze_email_route(input: EmailInput):
    try:
        result = analyze_email(input.content)
        return {"status": "success", "type": "email", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/image")
async def analyze_image_route(file: UploadFile = File(...)):
    try:
        os.makedirs("temp", exist_ok=True)
        file_path = f"temp/{file.filename}"
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        result = analyze_image(file_path)
        return {"status": "success", "type": "image", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/audio")
async def analyze_audio_route(file: UploadFile = File(...)):
    try:
        os.makedirs("temp", exist_ok=True)
        file_path = f"temp/{file.filename}"
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        result = analyze_audio(file_path)
        return {"status": "success", "type": "audio", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/video")
async def analyze_video_route(file: UploadFile = File(...)):
    try:
        os.makedirs("temp", exist_ok=True)
        file_path = f"temp/{file.filename}"
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        result = analyze_video(file_path)
        return {"status": "success", "type": "video", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
