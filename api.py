
import os
from threading import Lock

from color_mapper import emotion_to_rgbw
from serial_sender import SerialSender
from emotion_motion import flow_period_ms
from emotion_ranked import ranked_plan

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from analyzer import analyze_text
from model_analyzer import KoteAnalyzer

# Disabled by default; run ONE worker, without --reload, when enabled.
LED_PORT = os.environ.get("EMOTION_WALL_PORT")
led_lock = Lock()
led_sender = None


def send_led_rgbw(rgbw, period_ms, ranked_colors, top_period):
    global led_sender
    with led_lock:
        try:
            # Keep the port open: avoid resetting the board between emotions.
            if led_sender is None:
                candidate = SerialSender(LED_PORT)
                candidate.__enter__()
                led_sender = candidate
            # Left 22 LEDs receive a looping three-color palette.
            # Middle/right retain the existing dominant color and speed.
            ack = led_sender.send_top3(ranked_colors, top_period)
            led_sender.send_row(2, rgbw, period_ms)
            led_sender.send_row(3, rgbw, period_ms)
            return ack
        except Exception:
            if led_sender is not None:
                try:
                    led_sender.__exit__(None, None, None)
                finally:
                    led_sender = None
            raise

app = FastAPI(title="Emotion Wall API")


@app.on_event("shutdown")
def close_led_connection():
    global led_sender
    with led_lock:
        if led_sender is not None:
            try:
                led_sender.__exit__(None, None, None)
            finally:
                led_sender = None


LOCAL_ORIGINS = [
    "http://localhost:5173", "http://127.0.0.1:5173",
    "http://localhost:5180", "http://127.0.0.1:5180",
    "http://localhost:4173", "http://127.0.0.1:4173",
]
EXTRA_ORIGINS = [origin.strip().rstrip("/")
                 for origin in os.environ.get("ALLOWED_ORIGINS", "").split(",")
                 if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=LOCAL_ORIGINS + EXTRA_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# 실제 KOTE AI 모델을 서버 시작 시 한 번만 로드
kote_analyzer = KoteAnalyzer()


class EmotionRequest(BaseModel):
    text: str


@app.get("/")
def home():
    return {"message": "Emotion Wall API is running"}


@app.post("/analyze")
def analyze_emotion(request: EmotionRequest):

    # 키워드 분석 대신 실제 KOTE AI 모델 사용
    result = analyze_text(
        request.text,
        analyzer=kote_analyzer
    )

    intensity = result.get("intensity")
    period_ms = flow_period_ms(result["scores"], intensity)
    ranked, ranked_colors, top_period = ranked_plan(result["scores"], intensity)

    # Explicit opt-in: analysis still succeeds if hardware is unavailable.
    led = {"enabled": bool(LED_PORT), "sent": False}
    if LED_PORT:
        try:
            # Use the dominant emotion for a clear, saturated physical color.
            rgbw = emotion_to_rgbw(result["dominant"])
            ack = send_led_rgbw(rgbw, period_ms, ranked_colors, top_period)
            led.update(sent=True, rgbw=rgbw, ack=ack, flow_period_ms=period_ms,
                       top_emotions=ranked, top_colors=ranked_colors,
                       left_flow_period_ms=top_period)
        except (OSError, ValueError, RuntimeError, ImportError, KeyError, TypeError) as exc:
            led["error"] = str(exc)

    return {
        "led": led,
        **result,
        "motion": {"flow_period_ms": period_ms, "top_flow_period_ms": top_period},
        "emotions": result["scores"],
        "main_emotion": result["dominant"],
    }
