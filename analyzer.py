"""analyzer.py - 텍스트 -> 감정 데이터(JSON)

KeywordAnalyzer는 스키마를 먼저 고정하기 위한 '더미(키워드 기반)' 분석기입니다.
실제 모델(KOTE, KcELECTRA, LLM 등)은 아래 인터페이스만 지키면 그대로 교체할 수 있습니다.

    class MyAnalyzer:
        def analyze(self, text) -> (scores: dict[label, float], intensity: float | None)

사용:
    python analyzer.py "오늘 시험 망쳐서 너무 속상해"
    python analyzer.py                       # 데모 문장 실행
    python analyzer.py --kote "문장"         # 실제 모델(KOTE) 사용, model_analyzer.py 참고
"""
import json
import sys
from pathlib import Path

from mapper import build_grid, grid_config, load_palette, map_emotion

LEXICON_PATH = Path(__file__).with_name("lexicon.json")
SCHEMA_VERSION = "1.1"


class KeywordAnalyzer:
    def __init__(self, lexicon=None, palette=None):
        if lexicon is None:
            with open(LEXICON_PATH, encoding="utf-8") as f:
                lexicon = json.load(f)
        self.lex = lexicon
        self.labels = list((palette or load_palette())["emotions"].keys())

    def analyze(self, text):
        lex = self.lex
        weights = {e: 0.0 for e in self.labels}
        emotional_hits = 0
        for emo, keywords in lex["emotions"].items():
            for kw in keywords:
                c = text.count(kw)
                if c:
                    weights[emo] += c
                    if emo != "neutral":
                        emotional_hits += c

        boost = 1.5 if any(w in text for w in lex["intensifiers"]) else 1.0
        for e in weights:
            if e != "neutral":
                weights[e] *= boost
        weights["neutral"] += lex["neutral_base"]

        total = sum(weights.values())
        scores = {e: round(w / total, 3) for e, w in weights.items()}
        top = max(scores, key=scores.get)  # 반올림 오차 보정: 합 = 1
        scores[top] = round(1 - sum(v for k, v in scores.items() if k != top), 3)

        intensity = 0.35 + 0.2 * emotional_hits * boost + 0.05 * min(text.count("!"), 3)
        return scores, round(max(0.35, min(1.0, intensity)), 2)


def analyze_text(text, analyzer=None, prev_scores=None, palette=None, tuning=None, grid=None):
    """전체 파이프라인: text -> scores -> gradient. 반환값이 곧 전달 스키마(dict)."""
    palette = palette or load_palette()
    analyzer = analyzer or KeywordAnalyzer(palette=palette)
    scores, intensity = analyzer.analyze(text)

    # 연속 입력 안정화 (EMA): 색이 갑자기 튀지 않게
    if prev_scores:
        a = palette["mapper"]["ema_alpha"]
        scores = {e: round(a * scores[e] + (1 - a) * prev_scores.get(e, 0.0), 3) for e in scores}

    dominant = max(scores, key=scores.get)
    if intensity is None:
        intensity = scores[dominant]
    stops = map_emotion(scores, intensity, palette, tuning)
    cfg = grid_config(palette, grid)
    return {
        "schema_version": SCHEMA_VERSION,
        "text": text,
        "dominant": dominant,
        "scores": scores,
        "intensity": intensity,
        "gradient": stops,
        "grid": cfg,                       # rows, cols, angle, serpentine
        "leds": build_grid(stops, **cfg),  # 배선 순서(index)대로 공 하나당 색 하나
    }


def to_json(result, **kw):
    return json.dumps(result, ensure_ascii=False, **kw)


if __name__ == "__main__":
    args = sys.argv[1:]
    analyzer = None  # None이면 키워드 더미 분석기
    if args and args[0] == "--kote":  # 실제 모델 (torch, transformers 필요)
        from model_analyzer import KoteAnalyzer
        analyzer = KoteAnalyzer()
        args = args[1:]
    demos = args or [
        "오늘 시험 합격했어!! 진짜 너무 행복해",
        "오늘 시험 망쳐서 너무 속상해",
        "갑자기 깜짝 놀랐는데 한편으론 무서웠어",
        "그냥 평범한 하루였어",
    ]
    for t in demos:
        print(to_json(analyze_text(t, analyzer=analyzer), indent=2))
        print()
