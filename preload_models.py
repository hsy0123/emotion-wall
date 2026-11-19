"""Docker 빌드 중 한국어(KOTE)·영어(GoEmotions) 모델을 미리 내려받아 서버 시작을 빠르게 합니다.

모델 ID는 *_map.json에서 읽으므로 모델을 바꿀 때 이 파일은 수정하지 않아도 됩니다.
"""
import json
from pathlib import Path

from transformers import AutoModelForSequenceClassification, AutoTokenizer

ROOT = Path(__file__).resolve().parent

for name in ("kote_map.json", "goemotions_map.json"):
    model_id = json.loads((ROOT / name).read_text(encoding="utf-8"))["model_id"]
    AutoTokenizer.from_pretrained(model_id)
    AutoModelForSequenceClassification.from_pretrained(model_id)
    print(f"preloaded {model_id}")
