"""HTTP entry point: analyze text, plan the light effect, optionally send USB output."""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from analyzer import analyze_text
from emotion_ranked import build_motion
from led_controller import LedController
from model_analyzer import KoteAnalyzer

# A cloud deployment leaves EMOTION_WALL_PORT unset and only returns analysis.
led_output = LedController(os.environ.get("EMOTION_WALL_PORT"))
kote_analyzer = KoteAnalyzer()


@asynccontextmanager
async def lifespan(app):
    try:
        yield
    finally:
        led_output.close()


app = FastAPI(title="Emotion Wall API", lifespan=lifespan)
LOCAL_ORIGINS = [
    f"http://{host}:{port}"
    for host in ("localhost", "127.0.0.1")
    for port in (5173, 5180, 4173)
]
EXTRA_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in os.environ.get("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=LOCAL_ORIGINS + EXTRA_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class EmotionRequest(BaseModel):
    text: str


@app.get("/")
def home():
    return {"message": "Emotion Wall API is running"}


@app.post("/analyze")
def analyze_emotion(request: EmotionRequest):
    result = analyze_text(request.text, analyzer=kote_analyzer)
    motion = build_motion(result["scores"], result.get("intensity"))
    return {
        "led": led_output.display(motion),
        **result,
        "motion": motion,
        # Preserve the response keys consumed by existing deployed frontends.
        "emotions": result["scores"],
        "main_emotion": result["dominant"],
    }
