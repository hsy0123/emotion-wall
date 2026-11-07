# Emotion Wall 백엔드 (Hugging Face Spaces - Docker)
FROM python:3.11-slim

# Spaces는 uid 1000 사용자로 실행하므로 그 사용자를 만들어 둠
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface \
    PYTHONUNBUFFERED=1
WORKDIR /home/user/app

# CPU 전용 torch 먼저 설치 (GPU 버전보다 훨씬 작음)
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user torch --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir --user -r requirements.txt

COPY --chown=user . .

# KOTE 모델을 이미지에 미리 받아 둬서 서버 시작을 빠르게 함
RUN python -c "import json; from transformers import AutoTokenizer, AutoModelForSequenceClassification as M; m=json.load(open('kote_map.json'))['model_id']; AutoTokenizer.from_pretrained(m); M.from_pretrained(m)"

EXPOSE 7860
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "7860"]
