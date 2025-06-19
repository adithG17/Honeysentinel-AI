# backend/app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="HoneySentinel AI",
    description="Detects potential honey trap threats across social platforms, messages, audio, video, and more.",
    version="1.0.0"
)

# Allow frontend (if built) or Postman/Curl
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "HoneySentinel AI is alive!"}
