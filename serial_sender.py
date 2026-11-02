# serial_sender.py

import serial
from color_mapper import rgbw_to_serial


def send_rgbw(rgbw, port, baudrate=115200):
    """RGBW 값을 ESP32로 전송"""

    message = rgbw_to_serial(rgbw)

    with serial.Serial(
        port=port,
        baudrate=baudrate,
        timeout=1
    ) as esp32:
        esp32.write(message.encode("utf-8"))
        esp32.flush()

    print("전송 완료:", message.strip())


if __name__ == "__main__":
    # ESP32 연결 전 테스트
    test_rgbw = (255, 180, 0, 0)

    message = rgbw_to_serial(test_rgbw)

    print("전송 예정 데이터:", repr(message))