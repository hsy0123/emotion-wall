import importlib.util
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
class CloudApiTests(unittest.TestCase):
    def test_cloud_analysis_without_usb_and_deployed_cors(self):
        fake_model=types.ModuleType('model_analyzer')
        fake_model.KoteAnalyzer=lambda:object()
        with patch.dict(os.environ, {'ALLOWED_ORIGINS':'https://emotion.example/'}, clear=True), patch.dict(sys.modules, {'model_analyzer':fake_model}):
            spec=importlib.util.spec_from_file_location('cloud_api_test',ROOT/'api.py')
            api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api)
        with patch.object(api,'analyze_text',return_value={'scores':{'joy':1},'dominant':'joy'}), patch.object(api,'SerialSender') as sender:
            result=api.analyze_emotion(api.EmotionRequest(text='행복해'))
            self.assertEqual(result['led'],{'enabled':False,'sent':False})
            sender.assert_not_called()
        self.assertIn('https://emotion.example',api.EXTRA_ORIGINS)
        excluded=(ROOT/'.dockerignore').read_text().splitlines()
        self.assertNotIn('serial_sender.py',excluded)
        for name in ['emotion_motion.py','emotion_ranked.py','serial_sender.py']:
            self.assertTrue((ROOT/name).is_file())

if __name__=='__main__':unittest.main()
