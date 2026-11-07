from color_mapper import emotion_to_rgbw
from emotion_motion import flow_period_ms


def ranked_plan(scores):
    period = flow_period_ms(scores)  # Validate the full model schema first.
    ranked = [name for name, value in sorted(scores.items(), key=lambda item: item[1], reverse=True) if value > 0][:3]
    while len(ranked) < 3:
        ranked.append(ranked[0])
    return ranked, [emotion_to_rgbw(name) for name in ranked], max(600, min(2400, round(period * 0.55)))
