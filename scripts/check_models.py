"""실제 모델(KOTE·GoEmotions)로 한국어/영어 문장 쌍을 분석해 결과를 나란히 보여 줍니다.

모델을 내려받아야 하므로 torch, transformers와 인터넷이 필요합니다 (처음 실행 시 수백 MB).
단위 테스트(tests/)는 모델 없이 돌아가므로, 모델을 바꾸거나 매핑(*_map.json)을 고친 뒤에는 이 스크립트로 확인하세요.

    python scripts/check_models.py

출력 읽는 법
  - dominant: 7개 감정 중 가장 높은 것. 기대한 감정과 같으면 OK, 다르면 확인 필요(오류는 아님).
  - 확률합: 모델 원본 확률의 합. 다중 라벨(sigmoid) 모델은 1이 아닌 값이 나옵니다.
    영어 모델에서 합이 항상 1.0에 가깝다면 softmax 모델이라는 뜻이므로 goemotions_map.json의 activation을 확인하세요.
  - 한국어와 영어 쌍이 서로 다른 감정이면 매핑 기준이 어긋난 것일 수 있습니다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from language import detect_language  # noqa: E402
from model_analyzer import GoEmotionsAnalyzer, KoteAnalyzer  # noqa: E402

# (기대 감정, 한국어, 영어)
PAIRS = [
    ("joy", "오늘 시험에 합격해서 너무 행복해!", "I passed my exam today and I'm so happy!"),
    ("sadness", "오늘 시험 망쳐서 너무 속상해", "I failed my exam today and I feel so sad."),
    ("anger", "진짜 너무 짜증나고 화가 나", "I'm so annoyed and angry right now."),
    ("fear", "내일 발표가 너무 무섭고 불안해", "I'm terrified and anxious about tomorrow's presentation."),
    ("surprise", "갑자기 깜짝 놀랐어! 믿을 수 없어", "Wow, that was such a surprise! I can't believe it!"),
    ("love", "항상 곁에 있어 줘서 정말 고맙고 사랑해", "Thank you for always being there for me, I love you."),
    ("neutral", "그냥 평범한 하루였어", "It was just an ordinary day."),
]


def top(scores, count=3):
    ranked = sorted(scores.items(), key=lambda item: -item[1])[:count]
    return ", ".join(f"{name} {value:.2f}" for name, value in ranked if value > 0)


def main():
    analyzers = {"ko": KoteAnalyzer(), "en": GoEmotionsAnalyzer()}
    hits = {"ko": 0, "en": 0}
    same_color = 0
    for expected, korean, english in PAIRS:
        dominants = {}
        print(f"\n[기대: {expected}]")
        for language, text in (("ko", korean), ("en", english)):
            detected = detect_language(text)
            analyzer = analyzers[language]
            raw = analyzer.predict_probs(text)
            scores, intensity = analyzer.analyze(text)
            dominant = max(scores, key=scores.get)
            dominants[language] = dominant
            hits[language] += dominant == expected
            note = "" if detected == language else f"  (언어 판별 불일치: {detected})"
            print(f"  {language} {'OK ' if dominant == expected else '확인'} {dominant:<8} "
                  f"강도 {intensity:.2f}  확률합 {sum(raw.values()):.2f}  {top(scores)}{note}")
            print(f"       {text}")
        same_color += dominants["ko"] == dominants["en"]

    total = len(PAIRS)
    print(f"\n기대 감정과 일치: 한국어 {hits['ko']}/{total}, 영어 {hits['en']}/{total}")
    print(f"한국어·영어 쌍이 같은 감정: {same_color}/{total}")


if __name__ == "__main__":
    main()
