"""model_analyzer.py - 실제 한국어 감정 모델(KOTE) 분석기

KOTE(KcELECTRA 기반, 44개 감정 다중 라벨)의 출력을 우리 7개 레이블로 집계합니다.
analyzer.py의 인터페이스(analyze(text) -> (scores, intensity))를 그대로 따르므로
기존 파이프라인(mapper, 웹 JSON 스키마)은 변경 없이 동작합니다.

필요 패키지: pip install torch transformers   (requirements.txt 참고)

사용:
    from analyzer import analyze_text
    from model_analyzer import KoteAnalyzer
    result = analyze_text("오늘 시험 망쳐서 너무 속상해", analyzer=KoteAnalyzer())

    python analyzer.py --kote "오늘 시험 망쳐서 너무 속상해"

집계 방식 (aggregate_probs)
  1) KOTE는 감정별 독립 시그모이드 확률(합이 1이 아님)을 냅니다.
  2) min_prob 미만은 노이즈로 보고 버립니다.
  3) 7개 감정 각각에 대해 매핑된 레이블의 (가중치 x 확률) 중 최댓값(agg="max")을 사용합니다.
     합산("sum")은 레이블 수가 많은 감정(분노 등)에 유리해져서 기본값으로 쓰지 않습니다.
  4) 7개 값을 합이 1이 되도록 정규화 -> scores.
  5) intensity는 neutral을 제외한 감정의 최대 강도로 정합니다 (0.35~1.0).
"""
import json
import re
from pathlib import Path

from mapper import load_palette

MAP_PATH = Path(__file__).with_name("kote_map.json")

# HF config의 id2label이 LABEL_0... 형태일 때만 쓰는 대비용 목록 (Spark NLP 이식본 기준 순서, 미검증).
FALLBACK_LABELS = [
    "깨달음", "놀람", "기쁨", "부담/안_내킴", "우쭐댐/무시함", "공포/무서움", "흐뭇함(귀여움/예쁨)", "환영/호의",
    "부끄러움", "화남/분노", "패배/자기혐오", "귀찮음", "짜증", "불쌍함/연민", "증오/혐오", "기대감",
    "안심/신뢰", "행복", "재미없음", "절망", "비장함", "어이없음", "지긋지긋", "불평/불만",
    "고마움", "안타까움/실망", "불안/걱정", "즐거움/신남", "한심함", "뿌듯함", "슬픔", "죄책감",
    "경악", "없음", "역겨움/징그러움", "힘듦/지침", "신기함/관심", "편안/쾌적", "당황/난처", "의심/불신",
    "감동/감탄", "아껴주는", "존경", "서러움",
]


def load_mapping(path=MAP_PATH):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def aggregate_probs(probs, mapping, emotions, agg="max", min_prob=0.1):
    """KOTE 라벨 확률 dict -> (7개 감정 scores(합=1), intensity). torch 없이 테스트 가능한 순수 함수."""
    parts = {e: [] for e in emotions}
    for label, p in probs.items():
        if p < min_prob:
            continue
        for emo, w in mapping.get(label, {}).items():
            if emo in parts:
                parts[emo].append(w * p)

    raw = {}
    for e, xs in parts.items():
        if not xs:
            raw[e] = 0.0
        else:
            raw[e] = max(xs) if agg == "max" else min(1.0, sum(xs))

    total = sum(raw.values())
    if total == 0:  # 아무 감정도 임계값을 넘지 못함 -> 중립
        scores = {e: 0.0 for e in emotions}
        scores["neutral"] = 1.0
        return scores, 0.35

    scores = {e: round(v / total, 3) for e, v in raw.items()}
    top = max(scores, key=scores.get)  # 반올림 오차 보정: 합 = 1
    scores[top] = round(1 - sum(v for k, v in scores.items() if k != top), 3)

    strength = max((v for e, v in raw.items() if e != "neutral"), default=0.0)
    intensity = round(max(0.35, min(1.0, 0.35 + 0.65 * strength)), 2)
    return scores, intensity


class KoteAnalyzer:
    def __init__(self, model_id=None, mapping_path=MAP_PATH, palette=None, device=None,
                 agg="max", min_prob=0.1, max_length=256):
        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except ImportError as e:  # pragma: no cover
            raise ImportError("KoteAnalyzer에는 torch, transformers가 필요합니다: pip install torch transformers") from e

        cfg = load_mapping(mapping_path)
        self.mapping = cfg["labels"]
        self.model_id = model_id or cfg["model_id"]
        self.emotions = list((palette or load_palette())["emotions"].keys())
        self.agg, self.min_prob, self.max_length = agg, min_prob, max_length
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        self.tok = AutoTokenizer.from_pretrained(self.model_id)
        self.model = AutoModelForSequenceClassification.from_pretrained(self.model_id).to(self.device).eval()
        self.labels = self._resolve_labels()
        self._check_mapping()

    def _resolve_labels(self):
        id2label = self.model.config.id2label
        labels = [str(id2label[i]) for i in range(len(id2label))]
        if all(re.fullmatch(r"LABEL_\d+", name) for name in labels):
            if len(labels) != len(FALLBACK_LABELS):
                raise RuntimeError("모델 레이블 수가 44개가 아니라서 대체 목록을 쓸 수 없습니다.")
            print("[경고] 모델 config에 레이블 이름이 없어 대체 목록(순서 미검증)을 사용합니다. "
                  "결과가 이상하면 모델 카드의 레이블 순서와 대조하세요.")
            return FALLBACK_LABELS
        return labels

    def _check_mapping(self):
        unmapped = [name for name in self.labels if name not in self.mapping]
        if unmapped:
            print(f"[경고] kote_map.json에 없는 레이블 {len(unmapped)}개는 무시됩니다: {unmapped}")
        unknown = [e for m in self.mapping.values() for e in m if e not in self.emotions]
        if unknown:
            raise ValueError(f"kote_map.json이 palette.json에 없는 감정을 참조합니다: {sorted(set(unknown))}")

    def predict_probs(self, text):
        """KOTE 44개 라벨별 시그모이드 확률."""
        import torch
        enc = self.tok(text, return_tensors="pt", truncation=True, max_length=self.max_length)
        enc = {k: v.to(self.device) for k, v in enc.items()}
        with torch.no_grad():
            logits = self.model(**enc).logits[0]
        return {name: p for name, p in zip(self.labels, torch.sigmoid(logits).tolist())}

    def analyze(self, text):
        if not text.strip():
            return aggregate_probs({}, self.mapping, self.emotions)
        return aggregate_probs(self.predict_probs(text), self.mapping, self.emotions, self.agg, self.min_prob)
