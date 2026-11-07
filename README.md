# Emotion Wall

문장을 분석해 감정 비율과 색을 보여주고, 선택적으로 USB ESP32 RGBW LED에 전송합니다.

## 웹 화면

```sh
cd frontend
npm ci
npm run dev
```

배포 빌드에는 `VITE_API_URL`을 공개 백엔드 주소로 설정하세요. 미설정 시 로컬 `http://127.0.0.1:8000`을 사용합니다.
이 값은 Vite 빌드 시 포함되므로 변경 후 다시 빌드해야 합니다. 기존 배포 환경변수는 유지하세요.

```sh
VITE_API_URL=https://YOUR-BACKEND.example npm run build
```

기존 감정 차트와 말랑이 화면은 유지하며 다음을 추가했습니다.

- 최근 분석 요청의 LED 전송 결과: 수신 확인 / 실패 / 미리보기 / 상태 정보 없음
- 실제 전송값이 제공되면 해당 감정색과 속도로 22·21·21개 효과 미리보기
- USB 비활성 또는 이전 API에서는 예상값으로 표현 예시 표시
- 일시정지/재생 및 OS 움직임 줄이기 설정 지원
- 전송 실패 시 분석 결과는 유지하며 연결 안내 표시

미리보기는 효과 설명용이며 실제 밝기·배선 방향·기기 연결 상태를 실시간 측정하지 않습니다.
화면의 수신 확인은 해당 요청의 ESP32 ACK이며 LED 발광 성공을 보장하지 않습니다.
감정 차트의 부드러운 팔레트와 실제 LED의 선명한 팔레트는 별개입니다.

## 백엔드 / 클라우드 배포

`requirements.txt`와 기존 Dockerfile을 사용합니다. Hugging Face Docker 포트는 기존 7860입니다.
`ALLOWED_ORIGINS`에 배포된 프론트엔드 origin을 쉼표로 구분해 설정하세요.

클라우드에는 `EMOTION_WALL_PORT`를 설정하지 마세요. 미설정 시 감정 분석만 수행하고
`led.enabled=false`를 반환합니다. 클라우드 서버가 개인 Mac의 USB 포트를 직접 사용할 수는 없습니다.
USB 제어를 원하면 ESP32가 연결된 컴퓨터에서 이 백엔드를 실행해야 합니다.

## 로컬 USB LED

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
EMOTION_WALL_PORT=/dev/cu.YOUR-ACTUAL-PORT python -m uvicorn api:app --host 127.0.0.1 --port 8000 --workers 1
```

실제 포트는 `python -m serial.tools.list_ports`로 확인합니다.
Arduino 시리얼 모니터와 동시에 포트를 열지 말고 한 worker, reload 없이 실행하세요.
서버 코드/환경변수를 바꾸면 실행 중인 서버도 재시작해야 합니다.

최신 펌웨어는 `firmware/emotion_wall_top3/emotion_wall_top3.ino`입니다.
총64개(22·21·21개), GPIO18, RGBW GRBW 순서, 115200 baud.
첫 구간은 상위 세 감정의 연속 그라데이션을 더 빠르게, 나머지 두 구간은 대표감정으로 표시합니다.
외부 전원과 공통 GND가 필요하며 전원 정격/배선은 별도 확인하세요.
펌웨어 변경은 GitHub 업로드와 별개로 Arduino IDE에서 직접 보드에 업로드해야 합니다.

## 검증

```sh
node --test frontend/tests/led-model.test.js
cd frontend && npm run build
```

프로젝트 루트에서 Python 의존성 설치 후:

```sh
python -m unittest test_motion.py
python -m unittest discover -s tests
```

실제 감정 모델 및 LED 없이 수행하는 단위검사이며 실제 하드웨어 시험은 별도입니다.
`backup-*`, `.venv`, 모델 캐시, `.env`, `node_modules`는 GitHub에 올리지 않습니다.

## 화면과 감정 강도

주요 감정에는 OS 이모지 대신 감정색 표시를 사용합니다. 말랑이 다음에 빛 효과가 배치됩니다.
LED 개수는 사용자 화면에 표시하지 않으며 내부 배선 구간은 유지합니다.
감정별 가중 속도에 모델 intensity(0~1)를 반영합니다. 같은 감정 비율에서는 강도가 높을수록 빠릅니다.
차분함은 분노보다 느린 기본 속도를 유지합니다. API motion에는 USB 유무와 관계없이 계산한 주기를 제공합니다.
기존 TOP/ROW 명령에 실제 주기를 전송하므로 최신 top3 펌웨어는 재업로드 없이 이 속도를 적용합니다.
미리보기 재생/멈추기는 웹에서만 동작하며 실제 LED를 멈추지 않습니다.
