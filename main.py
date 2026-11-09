# main.py

from color_mapper import emotion_to_rgbw, rgbw_to_serial

def main():
    print("=== Emotion Wall RGBW Test ===")

    while True:
        emotion = input(
            "\n감정을 입력하세요 "
            "(joy/sadness/anger/fear/calm/neutral, 종료: q): "
        ).strip().lower()

        if emotion == "q":
            print("프로그램 종료")
            break

        try:
            rgbw = emotion_to_rgbw(emotion)
            message = rgbw_to_serial(rgbw)

            print(f"감정: {emotion}")
            print(f"RGBW: {rgbw}")
            print(f"ESP32 전송 예정: {message.strip()}")

        except ValueError as e:
            print(f"오류: {e}")


if __name__ == "__main__":
    main()