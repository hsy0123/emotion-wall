"""Map normalized emotion proportions to an LED traversal period."""
import math

def flow_period_ms(scores, intensity=None):
    weights = {"anger": 1.0, "fear": 0.75, "surprise": 0.45,
               "sadness": -0.25, "neutral": 0.10, "love": -0.35, "joy": -0.55, "calm": -0.70}
    if not scores:
        raise ValueError("Emotion scores are empty")
    total = 0.0
    activation = 0.0
    for emotion, score in scores.items():
        if emotion not in weights:
            raise ValueError(f"Unknown emotion: {emotion}")
        if isinstance(score, bool) or not isinstance(score, (float, int)) or not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError("Emotion scores must be finite numbers in 0..1")
        total += score
        activation += weights[emotion] * score
    if total <= 0:
        raise ValueError("Emotion scores sum to zero")
    activation /= total
    # Interpolate rate, rather than period: more anger always speeds up motion.
    if activation >= 0:
        rate = 1 / 3.2 + activation * (1 / 0.9 - 1 / 3.2)
    else:
        rate = 1 / 3.2 + (-activation / 0.7) * (1 / 6.0 - 1 / 3.2)
    # Model intensity is a separate signal from the emotion proportions.
    # At fixed proportions, stronger intensity always increases speed (until capped).
    if intensity is not None:
        if isinstance(intensity, bool) or not isinstance(intensity, (int, float)) or not math.isfinite(intensity) or not 0 <= intensity <= 1:
            raise ValueError("Intensity must be a finite number in 0..1")
        rate *= 0.55 + 0.45 * intensity
    return max(900, min(6000, round(1000 / rate)))
