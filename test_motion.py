import unittest
from emotion_motion import flow_period_ms

class MotionTests(unittest.TestCase):
    def test_real_model_schema_including_zero_scores(self):
        scores={'joy':.526,'love':.32,'surprise':0.,'sadness':0.,'anger':0.,'fear':0.,'neutral':.154}
        self.assertTrue(900<=flow_period_ms(scores)<=6000)
        for dominant in scores:
            full={key:float(key==dominant) for key in scores}
            self.assertTrue(900<=flow_period_ms(full)<=6000)
    def test_every_palette_emotion(self):
        from color_mapper import EMOTION_COLORS
        for key in EMOTION_COLORS:
            self.assertTrue(900<=flow_period_ms({key:1})<=6000)
    def test_anger_is_faster(self):
        periods=[flow_period_ms({'anger':v,'joy':1-v,'sadness':0}) for v in [0,.25,.5,.75,1]]
        self.assertTrue(all(a>b for a,b in zip(periods,periods[1:])))

if __name__=='__main__':unittest.main()
