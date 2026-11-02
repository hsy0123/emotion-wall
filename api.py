
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from analyzer import analyze_text
from model_analyzer import KoteAnalyzer

app = FastAPI(title="Emotion Wall API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5180",
        "http://127.0.0.1:5180",
    ],
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
