"""Select the emotion palette and movement periods used by web and USB output."""
from color_mapper import emotion_to_rgbw
from emotion_motion import flow_period_ms


def build_motion(scores, intensity=None):
    period = flow_period_ms(scores, intensity)  # Also validates the model scores.
    ranked = sorted(scores, key=scores.get, reverse=True)
    ranked = [name for name in ranked if name != "neutral" and scores[name] > 0][:3]
    if not ranked:
        ranked = ["neutral"]
    while len(ranked) < 3:
        ranked.append(ranked[0])
    return {
        "flow_period_ms": period,
        "top_flow_period_ms": max(600, min(2400, round(period * 0.55))),
        "top_emotions": ranked,
        "top_colors": [emotion_to_rgbw(name) for name in ranked],
    }


def ranked_plan(scores, intensity=None):
    """Keep the original tuple interface for scripts using this helper."""
    motion = build_motion(scores, intensity)
    return motion["top_emotions"], motion["top_colors"], motion["top_flow_period_ms"]
