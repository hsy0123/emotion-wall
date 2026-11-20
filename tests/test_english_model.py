"""영어(GoEmotions) 모델 연동 검사. 모델·torch 없이 실행됩니다."""
from pathlib import Path
import unittest
from unittest.mock import patch

from analyzer import analyze_text
from language import detect_language, resolve_language
from mapper import load_palette
from model_analyzer import (
    GoEmotionsAnalyzer,
    KoteAnalyzer,
    aggregate_probs,
    load_mapping,
    probabilities_from_logits,
)

ROOT = Path(__file__).resolve().parents[1]
EMOTIONS = list(load_palette()["emotions"])
GO_CONFIG = load_mapping(ROOT / "goemotions_map.json")
GO_MAP = GO_CONFIG["labels"]
KOTE_MAP = load_mapping(ROOT / "kote_map.json")["labels"]

# SamLowe/roberta-base-go_emotions 모델 카드의 28개 레이블
GOEMOTIONS_LABELS = [
    "admiration", "amusement", "anger", "annoyance", "approval", "caring", "confusion", "curiosity",
    "desire", "disappointment", "disapproval", "disgust", "embarrassment", "excitement", "fear",
    "gratitude", "grief", "joy", "love", "nervousness", "optimism", "pride", "realization", "relief",
    "remorse", "sadness", "surprise", "neutral",
]


def quiet(**high):
    """28개 레이블을 낮은 확률(0.01)로 깔고, 지정한 레이블만 높게 둔 모델 출력."""
    probs = {label: 0.01 for label in GOEMOTIONS_LABELS}
    probs.update(high)
    return probs


class LanguageDetectionTests(unittest.TestCase):
    def test_pure_languages(self):
        self.assertEqual(detect_language("오늘 정말 행복해"), "ko")
        self.assertEqual(detect_language("I am really happy today"), "en")
        self.assertEqual(detect_language("I'm so tired, it's been a long day..."), "en")

    def test_korean_slang_and_jamo_are_korean(self):
        self.assertEqual(detect_language("ㅋㅋㅋ"), "ko")
        self.assertEqual(detect_language("ㅠㅠ 너무 속상해"), "ko")

    def test_mixed_text_follows_the_majority_of_words(self):
        self.assertEqual(detect_language("오늘 meeting 때문에 너무 stressed"), "ko")
        self.assertEqual(detect_language("I am so 행복해 today"), "en")
        self.assertEqual(detect_language("I love you 사랑해"), "en")

    def test_tie_prefers_korean(self):
        self.assertEqual(detect_language("행복해 happy"), "ko")

    def test_no_letters_uses_default(self):
        for text in ("", "   ", "123", "😊😊", "!!!"):
            self.assertEqual(detect_language(text), "ko")
        self.assertEqual(detect_language("😊", default="en"), "en")

    def test_resolve_language(self):
        self.assertEqual(resolve_language("auto", "I am happy"), "en")
        self.assertEqual(resolve_language("auto", "행복해"), "ko")
        self.assertEqual(resolve_language("en", "행복해"), "en")
        self.assertEqual(resolve_language("ko", "I am happy"), "ko")
        self.assertEqual(resolve_language(None, "I am happy"), "en")


class GoEmotionsMappingTests(unittest.TestCase):
    def test_every_model_label_is_mapped_exactly_once(self):
        self.assertEqual(len(GOEMOTIONS_LABELS), 28)
        self.assertEqual(set(GO_MAP), set(GOEMOTIONS_LABELS))

    def test_weights_are_valid_and_use_only_palette_emotions(self):
        for label, weights in GO_MAP.items():
            self.assertAlmostEqual(sum(weights.values()), 1.0, msg=label)
            self.assertTrue(set(weights) <= set(EMOTIONS), msg=label)
            self.assertTrue(all(w > 0 for w in weights.values()), msg=label)

    def test_every_emotion_color_is_reachable(self):
        reachable = {emotion for weights in GO_MAP.values() for emotion in weights}
        self.assertEqual(reachable, set(EMOTIONS))

    def test_model_settings(self):
        self.assertEqual(GO_CONFIG["model_id"], "SamLowe/roberta-base-go_emotions")
        self.assertEqual(GO_CONFIG["language"], "en")
        self.assertEqual(GO_CONFIG["activation"], "sigmoid")
        self.assertGreater(GO_CONFIG["min_prob"], 0)

    def test_english_and_korean_labels_with_the_same_meaning_share_a_color(self):
        """같은 뜻의 감정은 한국어/영어에서 같은 색(대표 감정)으로 가야 합니다."""
        same_meaning = {
            "joy": "기쁨", "excitement": "즐거움/신남", "optimism": "기대감", "pride": "뿌듯함",
            "love": "흐뭇함(귀여움/예쁨)", "admiration": "존경", "caring": "아껴주는", "gratitude": "고마움",
            "surprise": "놀람", "curiosity": "신기함/관심", "confusion": "당황/난처",
            "sadness": "슬픔", "grief": "서러움", "disappointment": "안타까움/실망", "remorse": "죄책감",
            "embarrassment": "부끄러움",
            "anger": "화남/분노", "annoyance": "짜증", "disgust": "역겨움/징그러움", "disapproval": "불평/불만",
            "fear": "공포/무서움", "nervousness": "불안/걱정",
            "neutral": "없음", "relief": "안심/신뢰", "realization": "깨달음",
        }
        for english, korean in same_meaning.items():
            main = lambda weights: max(weights, key=weights.get)
            self.assertEqual(main(GO_MAP[english]), main(KOTE_MAP[korean]), msg=f"{english} vs {korean}")


class EnglishAggregationTests(unittest.TestCase):
    def aggregate(self, probs):
        return aggregate_probs(probs, GO_MAP, EMOTIONS, min_prob=GO_CONFIG["min_prob"])

    def test_sad_sentence(self):
        scores, intensity = self.aggregate(quiet(sadness=0.82, disappointment=0.41, neutral=0.05))
        self.assertEqual(max(scores, key=scores.get), "sadness")
        self.assertAlmostEqual(sum(scores.values()), 1.0, places=3)
        self.assertGreater(intensity, 0.8)

    def test_secondary_emotions_blend(self):
        scores, _ = self.aggregate(quiet(excitement=0.7, nervousness=0.5))
        self.assertGreater(scores["joy"], scores["fear"])
        self.assertGreater(scores["fear"], 0.3)
        self.assertEqual(scores["sadness"], 0.0)

    def test_synonyms_do_not_outweigh_the_strongest_label(self):
        """max 집계: anger 계열 레이블이 여러 개여도 합산되지 않아야 합니다."""
        scores, _ = self.aggregate(quiet(joy=0.8, anger=0.3, annoyance=0.3, disapproval=0.3, disgust=0.3))
        self.assertEqual(max(scores, key=scores.get), "joy")

    def test_split_label(self):
        scores, _ = self.aggregate(quiet(approval=0.8))
        self.assertEqual(scores["joy"], scores["neutral"])
        self.assertAlmostEqual(scores["joy"], 0.5, places=3)

    def test_nothing_above_threshold_is_neutral(self):
        scores, intensity = self.aggregate({label: 0.05 for label in GOEMOTIONS_LABELS})
        self.assertEqual(scores["neutral"], 1.0)
        self.assertEqual(intensity, 0.35)

    def test_neutral_only(self):
        scores, intensity = self.aggregate(quiet(neutral=0.9))
        self.assertEqual(max(scores, key=scores.get), "neutral")
        self.assertEqual(intensity, 0.35)

    def test_unknown_model_label_is_ignored(self):
        scores, _ = self.aggregate({"not-a-label": 0.99, "joy": 0.6})
        self.assertEqual(scores["joy"], 1.0)


class ProbabilityTests(unittest.TestCase):
    def test_sigmoid(self):
        self.assertAlmostEqual(probabilities_from_logits([0.0])[0], 0.5)
        low, high = probabilities_from_logits([-1000.0, 1000.0])
        self.assertEqual((low, high), (0.0, 1.0))  # overflow 없이 계산
        a, b = probabilities_from_logits([-2.0, 2.0])
        self.assertAlmostEqual(a + b, 1.0)

    def test_softmax_sums_to_one_and_keeps_order(self):
        probs = probabilities_from_logits([1.0, 3.0, 2.0], "softmax")
        self.assertAlmostEqual(sum(probs), 1.0)
        self.assertEqual(sorted(range(3), key=probs.__getitem__), [0, 2, 1])
        self.assertAlmostEqual(sum(probabilities_from_logits([1000.0, 999.0], "softmax")), 1.0)

    def test_unknown_activation_is_rejected(self):
        with self.assertRaises(ValueError):
            probabilities_from_logits([0.0], "relu")


class EnglishAnalyzerPipelineTests(unittest.TestCase):
    """torch 없이 GoEmotionsAnalyzer의 분석 흐름(모델 출력 -> 7감정 -> 전체 JSON)을 확인합니다."""

    def make_analyzer(self):
        analyzer = GoEmotionsAnalyzer.__new__(GoEmotionsAnalyzer)  # 모델을 불러오지 않음
        analyzer.mapping, analyzer.emotions = GO_MAP, EMOTIONS
        analyzer.agg, analyzer.min_prob = "max", GO_CONFIG["min_prob"]
        return analyzer

    def test_english_sentence_reaches_the_shared_schema(self):
        analyzer = self.make_analyzer()
        with patch.object(analyzer, "predict_probs", return_value=quiet(sadness=0.8, disappointment=0.5)):
            result = analyze_text("I failed my exam and I feel so sad", analyzer=analyzer)
        self.assertEqual(result["dominant"], "sadness")
        self.assertEqual(set(result["scores"]), set(EMOTIONS))
        self.assertAlmostEqual(sum(result["scores"].values()), 1.0, places=3)
        self.assertEqual(len(result["leds"]), 12)
        self.assertTrue(result["gradient"])

    def test_blank_text_is_neutral_without_running_the_model(self):
        analyzer = self.make_analyzer()
        with patch.object(analyzer, "predict_probs") as predict:
            scores, intensity = analyzer.analyze("   ")
        predict.assert_not_called()
        self.assertEqual((scores["neutral"], intensity), (1.0, 0.35))

    def test_korean_and_english_use_their_own_mapping_and_defaults(self):
        self.assertEqual(KoteAnalyzer.default_map_path.name, "kote_map.json")
        self.assertEqual(GoEmotionsAnalyzer.default_map_path.name, "goemotions_map.json")
        self.assertIsNotNone(KoteAnalyzer.fallback_labels)
        self.assertIsNone(GoEmotionsAnalyzer.fallback_labels)


if __name__ == "__main__":
    unittest.main()
