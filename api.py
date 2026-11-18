"""HTTP entry point: analyze text, plan the light effect, optionally send USB output."""
import os
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from analyzer import analyze_text
from emotion_ranked import build_motion
from language import resolve_language
from led_controller import LedController
from model_analyzer import GoEmotionsAnalyzer, KoteAnalyzer

# A cloud deployment leaves EMOTION_WALL_PORT unset and only returns analysis.
led_output = LedController(os.environ.get("EMOTION_WALL_PORT"))
# One model per input language; both map their emotions onto the same 7 labels.
analyzers = {"ko": KoteAnalyzer(), "en": GoEmotionsAnalyzer()}


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
    # "auto" picks the model from the text; "ko"/"en" force one.
    language: Literal["auto", "ko", "en"] = "auto"


@app.get("/")
def home():
    return {"message": "Emotion Wall API is running"}


@app.post("/analyze")
def analyze_emotion(request: EmotionRequest):
    language = resolve_language(request.language, request.text)
    result = analyze_text(request.text, analyzer=analyzers[language])
    motion = build_motion(result["scores"], result.get("intensity"))
    return {
        "led": led_output.display(motion),
        **result,
        "motion": motion,
        # Preserve the response keys consumed by existing deployed frontends.
        "emotions": result["scores"],
        "main_emotion": result["dominant"],
        "language": language,
    }
