"""모델 로딩·레이블 해석·확률 변환 코드를 가짜 torch/transformers로 검사합니다 (실제 모델 다운로드 없음)."""
import contextlib
import io
import json
import math
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import model_analyzer
from model_analyzer import GoEmotionsAnalyzer, KoteAnalyzer

GO_LABELS = [
    "admiration", "amusement", "anger", "annoyance", "approval", "caring", "confusion", "curiosity",
    "desire", "disappointment", "disapproval", "disgust", "embarrassment", "excitement", "fear",
    "gratitude", "grief", "joy", "love", "nervousness", "optimism", "pride", "realization", "relief",
    "remorse", "sadness", "surprise", "neutral",
]


class FakeRow(list):
    def tolist(self):
        return list(self)


class FakeEncoding(dict):
    pass


class FakeTensor:
    def to(self, device):
        return self


class FakeModel:
    """id2label과 로짓만 흉내 내는 모델."""

    def __init__(self, id2label, logits):
        self.config = types.SimpleNamespace(id2label=id2label)
        self.logits = logits

    def to(self, device):
        return self

    def eval(self):
        return self

    def __call__(self, **inputs):
        return types.SimpleNamespace(logits=[FakeRow(self.logits)])


def fake_libraries(id2label, logits):
    """sys.modules에 넣을 가짜 torch, transformers."""
    torch = types.ModuleType("torch")
    torch.cuda = types.SimpleNamespace(is_available=lambda: False)
    torch.no_grad = contextlib.nullcontext
    transformers = types.ModuleType("transformers")
    transformers.AutoTokenizer = types.SimpleNamespace(
        from_pretrained=lambda model_id: (lambda text, **kwargs: FakeEncoding(input_ids=FakeTensor())))
    transformers.AutoModelForSequenceClassification = types.SimpleNamespace(
        from_pretrained=lambda model_id: FakeModel(id2label, logits))
    return {"torch": torch, "transformers": transformers}


def go_logits(**high):
    logits = [-4.0] * len(GO_LABELS)
    for label, value in high.items():
        logits[GO_LABELS.index(label)] = value
    return logits


def build(analyzer_class, id2label, logits, **kwargs):
    output = io.StringIO()
    with patch.dict(sys.modules, fake_libraries(id2label, logits)), contextlib.redirect_stdout(output):
        analyzer = analyzer_class(**kwargs)
        analyzer._libraries = fake_libraries(id2label, logits)
    return analyzer, output.getvalue()


def run(analyzer, text):
    with patch.dict(sys.modules, analyzer._libraries):
        return analyzer.analyze(text)


class EnglishModelLoadingTests(unittest.TestCase):
    def setUp(self):
        self.id2label = dict(enumerate(GO_LABELS))

    def test_loads_with_label_names_from_the_model_config(self):
        analyzer, output = build(GoEmotionsAnalyzer, self.id2label, go_logits())
        self.assertEqual(analyzer.model_id, "SamLowe/roberta-base-go_emotions")
        self.assertEqual(analyzer.language, "en")
        self.assertEqual(analyzer.activation, "sigmoid")
        self.assertEqual(analyzer.labels, GO_LABELS)
        self.assertEqual(output, "")  # 매핑 누락 경고 없음

    def test_logits_become_probabilities_and_seven_emotions(self):
        analyzer, _ = build(GoEmotionsAnalyzer, self.id2label, go_logits(sadness=3.0, disappointment=0.5))
        with patch.dict(sys.modules, analyzer._libraries):
            probs = analyzer.predict_probs("I failed my exam")
        self.assertAlmostEqual(probs["sadness"], 1 / (1 + math.exp(-3.0)))
        self.assertAlmostEqual(probs["joy"], 1 / (1 + math.exp(4.0)))
        scores, intensity = run(analyzer, "I failed my exam")
        self.assertEqual(max(scores, key=scores.get), "sadness")
        self.assertAlmostEqual(sum(scores.values()), 1.0, places=3)
        self.assertGreater(intensity, 0.8)

    def test_a_different_emotion_changes_the_result(self):
        analyzer, _ = build(GoEmotionsAnalyzer, self.id2label, go_logits(anger=2.5, annoyance=1.0))
        scores, _ = run(analyzer, "I am furious")
        self.assertEqual(max(scores, key=scores.get), "anger")

    def test_config_without_label_names_is_reported_instead_of_guessed(self):
        id2label = {i: f"LABEL_{i}" for i in range(28)}
        with self.assertRaisesRegex(RuntimeError, "레이블 이름"):
            build(GoEmotionsAnalyzer, id2label, go_logits())

    def test_korean_model_still_uses_its_fallback_labels(self):
        id2label = {i: f"LABEL_{i}" for i in range(44)}
        analyzer, output = build(KoteAnalyzer, id2label, [-4.0] * 44)
        self.assertEqual(analyzer.labels, model_analyzer.FALLBACK_LABELS)
        self.assertEqual(analyzer.language, "ko")
        self.assertIn("대체 목록", output)

    def test_an_unmapped_model_label_only_warns(self):
        id2label = dict(enumerate(GO_LABELS + ["new_label"]))
        analyzer, output = build(GoEmotionsAnalyzer, id2label, go_logits() + [-4.0])
        self.assertIn("new_label", output)
        self.assertIn("goemotions_map.json", output)


class MappingFileValidationTests(unittest.TestCase):
    def write_map(self, directory, **overrides):
        config = {"model_id": "x/y", "language": "en", "labels": {"a": {"joy": 1.0}}}
        config.update(overrides)
        path = Path(directory) / "custom_map.json"
        path.write_text(json.dumps(config), encoding="utf-8")
        return path

    def test_mapping_to_an_unknown_emotion_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_map(directory, labels={"a": {"not_an_emotion": 1.0}})
            with self.assertRaisesRegex(ValueError, "not_an_emotion"):
                build(GoEmotionsAnalyzer, {0: "a"}, [0.0], mapping_path=path)

    def test_unknown_activation_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_map(directory, activation="relu")
            with self.assertRaisesRegex(ValueError, "activation"):
                build(GoEmotionsAnalyzer, {0: "a"}, [0.0], mapping_path=path)

    def test_softmax_models_are_supported_through_the_mapping_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_map(directory, activation="softmax")
            analyzer, _ = build(GoEmotionsAnalyzer, {0: "a", 1: "b"}, [2.0, 0.0], mapping_path=path)
            with patch.dict(sys.modules, analyzer._libraries):
                probs = analyzer.predict_probs("hello")
        self.assertAlmostEqual(sum(probs.values()), 1.0)
        self.assertGreater(probs["a"], probs["b"])

    def test_min_prob_can_be_set_in_the_file_or_overridden(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_map(directory, min_prob=0.3)
            analyzer, _ = build(GoEmotionsAnalyzer, {0: "a"}, [0.0], mapping_path=path)
            self.assertEqual(analyzer.min_prob, 0.3)
            analyzer, _ = build(GoEmotionsAnalyzer, {0: "a"}, [0.0], mapping_path=path, min_prob=0.5)
            self.assertEqual(analyzer.min_prob, 0.5)


if __name__ == "__main__":
    unittest.main()
