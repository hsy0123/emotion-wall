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

class IntensityTests(unittest.TestCase):
    def test_same_emotions_stronger_intensity_is_faster(self):
        for scores in [{'anger':.6,'joy':.4},{'surprise':1},{'joy':1}]:
            periods=[flow_period_ms(scores,i) for i in [0,.25,.5,.75,1]]
            self.assertTrue(all(a>=b for a,b in zip(periods,periods[1:])))
            self.assertGreater(periods[0],periods[-1])
    def test_calm_stays_slower_than_anger(self):
        for intensity in [0,.5,1]:
            self.assertGreater(flow_period_ms({'calm':1},intensity),flow_period_ms({'anger':1},intensity))
    def test_invalid_intensity(self):
        for intensity in [True,-1,2,float('nan')]:
            with self.assertRaises(ValueError):flow_period_ms({'joy':1},intensity)


class RankedPaletteTests(unittest.TestCase):
    def test_neutral_not_ranked_as_an_emotion(self):
        from emotion_ranked import ranked_plan
        names,colors,_=ranked_plan({'love':.5,'neutral':.3,'joy':.2})
        self.assertEqual(names,['love','joy','love'])
        self.assertEqual(colors[0],colors[2])
    def test_no_clear_emotion_has_a_safe_fallback(self):
        from emotion_ranked import ranked_plan
        self.assertEqual(ranked_plan({'neutral':1})[0],['neutral']*3)

if __name__=='__main__':unittest.main()
