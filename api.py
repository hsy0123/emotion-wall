import os


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from analyzer import analyze_text
from model_analyzer import KoteAnalyzer

app = FastAPI(title="Emotion Wall API")

# 로컬 개발용 주소 + 배포 시 ALLOWED_ORIGINS 환경변수(쉼표로 구분)로 받은 프론트 주소
LOCAL_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5180",
    "http://127.0.0.1:5180",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
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

    return {
        **result,
        "emotions": result["scores"],
        "main_emotion": result["dominant"],
    }
