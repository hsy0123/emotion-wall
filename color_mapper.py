
# color_mapper.py

# 실제 LED용 대표색: 색이 희게 섞이지 않도록 W=0. 웹 팔레트와 독립적입니다.
EMOTION_COLORS = {
    "joy": (255, 210, 0, 0),       # 선명한 노랑
    "love": (255, 0, 90, 0),       # 진한 핑크
    "surprise": (0, 220, 255, 0),  # 청록/시안
    "sadness": (0, 25, 255, 0),    # 진한 파랑
    "anger": (255, 0, 0, 0),       # 순수 빨강
    "fear": (125, 0, 255, 0),      # 보라
    "calm": (0, 255, 65, 0),      # 초록
    "neutral": (255, 85, 0, 0),    # 앰버
}


# 1. 감정을 RGBW 값으로 변환
def emotion_to_rgbw(emotion):
    if emotion not in EMOTION_COLORS:
        raise ValueError(f"지원하지 않는 감정: {emotion}")

    return EMOTION_COLORS[emotion]


# 2. RGBW 값을 Serial 통신용 문자열로 변환
def rgbw_to_serial(rgbw):
    if len(rgbw) != 4:
        raise ValueError("RGBW 값은 4개여야 합니다.")

    if any(
        type(v) is not int or not 0 <= v <= 255
        for v in rgbw
    ):
        raise ValueError("RGBW 값은 0~255의 정수여야 합니다.")

    return ",".join(map(str, rgbw)) + "\n"


# 3. 감정 비율에 따른 RGBW 색상 혼합
def mix_emotions(emotion_scores):
    """
    감정별 비율을 이용해 RGBW 색상을 혼합합니다.

    입력 예시:
    {"joy": 0.7, "sadness": 0.2, "calm": 0.1}

    반환값:
    (R, G, B, W)
    """

    if not emotion_scores:
        raise ValueError("감정 데이터가 비어 있습니다.")

    # 감정 점수 유효성 검사
    for emotion, score in emotion_scores.items():
        if emotion not in EMOTION_COLORS:
            raise ValueError(f"지원하지 않는 감정: {emotion}")

        if (
            not isinstance(score, (int, float))
            or isinstance(score, bool)
            or not 0 <= score <= 1
        ):
            raise ValueError(
                f"{emotion}의 점수는 0~1 사이여야 합니다."
            )

    total = sum(emotion_scores.values())

    if total <= 0:
        raise ValueError("감정 점수의 합은 0보다 커야 합니다.")

    # RGBW 각 채널의 가중평균 계산
    mixed = [0.0, 0.0, 0.0, 0.0]

    for emotion, score in emotion_scores.items():
        color = EMOTION_COLORS[emotion]
        weight = score / total

        for i in range(4):
            mixed[i] += color[i] * weight

    # 0~255 정수로 변환
    return tuple(
        max(0, min(255, round(value)))
        for value in mixed
    )


# 4. 실행 테스트
if __name__ == "__main__":

    print("=== 단일 감정 테스트 ===")

    test_emotions = ["joy", "sadness", "anger", "calm"]

    for emotion in test_emotions:
        rgbw = emotion_to_rgbw(emotion)
        message = rgbw_to_serial(rgbw)

        print(f"감정: {emotion}")
        print(f"RGBW: {rgbw}")
        print(f"Serial: {message.strip()}")
        print("------------------------")

    print("\n=== 복합 감정 테스트 ===")

    emotion_scores = {
        "joy": 0.7,
        "sadness": 0.2,
        "calm": 0.1
    }

    mixed_rgbw = mix_emotions(emotion_scores)

    print("감정 비율:", emotion_scores)
    print("혼합 RGBW:", mixed_rgbw)
    print("Serial:", rgbw_to_serial(mixed_rgbw).strip())
