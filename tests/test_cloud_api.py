import importlib.util
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch

from pydantic import ValidationError

from emotion_ranked import build_motion
from led_controller import LedController

ROOT = Path(__file__).resolve().parents[1]


def load_api(environment):
    fake_model = types.ModuleType('model_analyzer')
    fake_model.KoteAnalyzer = lambda: object()
    fake_model.GoEmotionsAnalyzer = lambda: object()
    with patch.dict(os.environ, environment, clear=True), patch.dict(sys.modules, {'model_analyzer': fake_model}):
        spec = importlib.util.spec_from_file_location('api_under_test', ROOT / 'api.py')
        api = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(api)
    return api


class CloudApiTests(unittest.TestCase):
    def test_cloud_analysis_without_usb_and_deployed_cors(self):
        api = load_api({'ALLOWED_ORIGINS': 'https://emotion.example/'})
        analysis = {'scores': {'joy': 1}, 'dominant': 'joy', 'intensity': .8}
        with patch.object(api, 'analyze_text', return_value=analysis):
            result = api.analyze_emotion(api.EmotionRequest(text='행복해'))
        self.assertEqual(result['led'], {'enabled': False, 'sent': False})
        self.assertEqual(result['motion'], build_motion(analysis['scores'], .8))
        self.assertEqual(result['emotions'], analysis['scores'])
        self.assertEqual(result['main_emotion'], 'joy')
        self.assertEqual(result['language'], 'ko')
        self.assertIn('https://emotion.example', api.EXTRA_ORIGINS)
        excluded = (ROOT / '.dockerignore').read_text().splitlines()
        for name in ['emotion_motion.py', 'emotion_ranked.py', 'serial_sender.py', 'led_controller.py',
                     'language.py', 'goemotions_map.json', 'kote_map.json', 'preload_models.py']:
            self.assertNotIn(name, excluded)
            self.assertTrue((ROOT / name).is_file())


class LanguageRoutingTests(unittest.TestCase):
    def setUp(self):
        self.api = load_api({})
        self.analysis = {'scores': {'joy': 1}, 'dominant': 'joy', 'intensity': .8}

    def analyze(self, **request):
        with patch.object(self.api, 'analyze_text', return_value=self.analysis) as analyze_text:
            result = self.api.analyze_emotion(self.api.EmotionRequest(**request))
        return result, analyze_text.call_args.kwargs['analyzer']

    def test_each_language_has_its_own_model(self):
        self.assertEqual(set(self.api.analyzers), {'ko', 'en'})
        self.assertIsNot(self.api.analyzers['ko'], self.api.analyzers['en'])

    def test_auto_picks_the_model_from_the_text(self):
        result, analyzer = self.analyze(text='오늘 정말 행복해')
        self.assertEqual(result['language'], 'ko')
        self.assertIs(analyzer, self.api.analyzers['ko'])
        result, analyzer = self.analyze(text='I am really happy today')
        self.assertEqual(result['language'], 'en')
        self.assertIs(analyzer, self.api.analyzers['en'])

    def test_requests_without_language_keep_working(self):
        self.assertEqual(self.api.EmotionRequest(text='hello').language, 'auto')

    def test_explicit_language_overrides_detection(self):
        result, analyzer = self.analyze(text='오늘 정말 행복해', language='en')
        self.assertEqual(result['language'], 'en')
        self.assertIs(analyzer, self.api.analyzers['en'])

    def test_unknown_language_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.api.EmotionRequest(text='hello', language='fr')

    def test_response_keeps_the_keys_existing_frontends_read(self):
        result, _ = self.analyze(text='I am really happy today')
        for key in ('scores', 'emotions', 'dominant', 'main_emotion', 'motion', 'led'):
            self.assertIn(key, result)


class LedMotionRoutingTests(unittest.TestCase):
    def setUp(self):
        self.sender = Mock()
        self.sender.__enter__ = Mock(return_value=self.sender)
        self.sender.__exit__ = Mock()
        self.sender.send_top3.return_value = 'OK,TOP'
        self.factory = Mock(return_value=self.sender)
        self.controller = LedController('FAKE', self.factory)

    def test_intensity_reaches_commands_and_connection_is_reused(self):
        periods = []
        for intensity in [.2, .9]:
            motion = build_motion({'anger': .7, 'joy': .3}, intensity)
            status = self.controller.display(motion)
            self.assertTrue(status['sent'])
            self.assertEqual(self.sender.send_top3.call_args.args[1], motion['top_flow_period_ms'])
            self.assertEqual(self.sender.send_row.call_args.args[2], motion['flow_period_ms'])
            periods.append(motion['flow_period_ms'])
        self.assertGreater(periods[0], periods[1])
        self.assertEqual([call.args[0] for call in self.sender.send_row.call_args_list], [2, 3, 2, 3])
        self.factory.assert_called_once_with('FAKE')
        self.controller.close()
        self.sender.__exit__.assert_called_once()

    def test_failed_write_disconnects_and_next_request_reconnects(self):
        motion = build_motion({'joy': 1})
        self.sender.send_row.side_effect = OSError('disconnected')
        status = self.controller.display(motion)
        self.assertFalse(status['sent'])
        self.assertEqual(status['error'], 'disconnected')
        self.sender.__exit__.assert_called_once()
        self.sender.send_row.side_effect = None
        self.assertTrue(self.controller.display(motion)['sent'])
        self.assertEqual(self.factory.call_count, 2)

    def test_disabled_usb_never_opens_a_port(self):
        controller = LedController(sender_factory=self.factory)
        self.assertEqual(controller.display(build_motion({'joy': 1})), {'enabled': False, 'sent': False})
        self.factory.assert_not_called()


if __name__ == '__main__':
    unittest.main()
