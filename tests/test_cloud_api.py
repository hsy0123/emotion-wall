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
        with patch.object(api,'analyze_text',return_value={'scores':{'joy':1},'dominant':'joy','intensity':.8}), patch.object(api,'SerialSender') as sender:
            result=api.analyze_emotion(api.EmotionRequest(text='행복해'))
            self.assertEqual(result['led'],{'enabled':False,'sent':False})
            sender.assert_not_called()
            self.assertEqual(result['motion']['flow_period_ms'],api.flow_period_ms({'joy':1},.8))
            self.assertLess(result['motion']['top_flow_period_ms'],result['motion']['flow_period_ms'])
        self.assertIn('https://emotion.example',api.EXTRA_ORIGINS)
        excluded=(ROOT/'.dockerignore').read_text().splitlines()
        self.assertNotIn('serial_sender.py',excluded)
        for name in ['emotion_motion.py','emotion_ranked.py','serial_sender.py']:
            self.assertTrue((ROOT/name).is_file())

class LedMotionRoutingTests(unittest.TestCase):
    def test_intensity_reaches_actual_top_and_row_commands(self):
        fake_model=types.ModuleType('model_analyzer')
        fake_model.KoteAnalyzer=lambda:object()
        with patch.dict(os.environ, {'EMOTION_WALL_PORT':'FAKE'}, clear=True), patch.dict(sys.modules, {'model_analyzer':fake_model}):
            spec=importlib.util.spec_from_file_location('led_routing_test',ROOT/'api.py')
            api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api)
        outputs=[]
        with patch.object(api,'SerialSender') as sender_type:
            sender=sender_type.return_value
            sender.send_top3.return_value='OK,TOP'
            for intensity in [.2,.9]:
                with patch.object(api,'analyze_text',return_value={'scores':{'anger':.7,'joy':.3},'dominant':'anger','intensity':intensity}):
                    result=api.analyze_emotion(api.EmotionRequest(text='test'))
                self.assertTrue(result['led']['sent'])
                self.assertEqual(sender.send_top3.call_args.args[1],result['motion']['top_flow_period_ms'])
                self.assertEqual(sender.send_row.call_args.args[2],result['motion']['flow_period_ms'])
                outputs.append(result['motion']['flow_period_ms'])
            self.assertGreater(outputs[0],outputs[1])
            self.assertEqual([c.args[0] for c in sender.send_row.call_args_list],[2,3,2,3])

if __name__=='__main__':unittest.main()
