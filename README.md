# Emotion Wall

문장을 입력하면 감정 비율을 분석하고, 색과 움직임으로 표현하는 웹 프로젝트입니다.
ESP32를 USB로 연결하면 같은 분석 결과를 실제 RGBW LED에도 보낼 수 있습니다.

**흐름:** 문장 입력 → KOTE 감정 분석 → 감정색·속도 계산 → 웹 미리보기 / 선택적 USB LED 출력

## 처음 볼 파일

| 궁금한 내용 | 파일 |
|---|---|
| 웹 화면의 시작과 분석 버튼 흐름 | `frontend/src/main.js` |
| 화면의 문구와 HTML | `frontend/src/app-template.js` |
| 감정 차트·말랑이·눌림 효과 | `frontend/src/result-view.js` |
| 색 혼합·미리보기 속도 계산 | `frontend/src/led-model.js` |
| 화면 스타일 | `frontend/src/style.scss` |
| HTTP API의 시작과 응답 | `api.py` |
| 감정 분석 파이프라인 / 실제 AI 모델 | `analyzer.py` / `model_analyzer.py` |
| LED 대표색 / 속도 / 상위 감정 선택 | `color_mapper.py` / `emotion_motion.py` / `emotion_ranked.py` |
| USB 연결 관리 / 통신 명령 | `led_controller.py` / `serial_sender.py` |

## 로컬 실행

Python 3.11과 Node.js 22.12 이상을 권장합니다. 첫 터미널에서 백엔드를 실행합니다.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn api:app --host 127.0.0.1 --port 8000
```

다른 터미널에서 웹 화면을 실행합니다.

```sh
cd frontend
npm ci
npm run dev
```

출력된 웹 주소로 접속합니다. 모델을 처음 받을 때는 백엔드 시작에 시간이 걸릴 수 있습니다.
기본 실행은 보드 없이 감정 분석·웹 미리보기만 제공합니다.
`main.py`는 감정색 문자열만 출력하는 별도 CLI 예제이며 서버 진입점은 `api.py`입니다.

## 배포와 환경변수

| 변수 | 설정 위치 | 용도 |
|---|---|---|
| `VITE_API_URL` | 프론트엔드 빌드 환경 | 공개 백엔드 주소. 개발 기본값 `http://127.0.0.1:8000`, 배포 기본값 `https://yebeen23-emotion-wall-api.hf.space` |
| `ALLOWED_ORIGINS` | 백엔드 실행 환경 | 접근할 웹 origin을 쉼표로 구분. 예: `https://your-site.example` |
| `EMOTION_WALL_PORT` | ESP32를 연결한 컴퓨터 | 실제 USB 포트. **클라우드에서는 미설정** |

웹 배포 빌드는 `cd frontend && npm run build`입니다. `VITE_API_URL` 변경 후에는 다시 빌드합니다.
백엔드 Dockerfile은 Hugging Face Spaces용 7860 포트를 유지합니다.
API는 `GET /`, `POST /analyze`를 제공하며 `/docs`에서 요청·응답 형식을 확인할 수 있습니다.
`POST /analyze` 요청 예: `{"text":"오늘 정말 행복해"}`.
응답의 `scores`는 감정 비율, `motion`은 표현 계획, `led`는 실제 USB 전송 결과입니다.

## LED와 미리보기

최신 보드 코드는 [`firmware/emotion_wall_top3/emotion_wall_top3.ino`](firmware/emotion_wall_top3/emotion_wall_top3.ino)입니다.
실제 배선, 줄별 동작, USB 명령, 웹과 실제 LED의 차이는 [LED 가이드](docs/LED.md)를 참고하세요.

## 검사

```sh
python -m unittest discover -s tests -v
npm --prefix frontend test
npm --prefix frontend run build
```

검사는 모델·실제 보드 없이 실행합니다. 실제 모델 추론과 보드 발광은 별도로 확인합니다.
백업 폴더·가상환경·모델 캐시·`.env`·빌드 결과는 Git에 포함하지 않습니다.

## 한국어와 영어 입력

입력 언어 선택은 기본적으로 자동 감지이며, 한국어 또는 English로 직접 지정할 수 있습니다.
프론트엔드는 `/analyze`에 `{"text":"I feel happy", "language":"auto"}` 형태로 요청하고,
응답의 `language`가 `ko` 또는 `en`이면 결과에 분석 언어를 표시합니다.
화면 문구 전체의 영문 번역과는 별개인 입력 언어 지원입니다.

현재 한·영 API: `https://yebeen23-emotion-wall-api.hf.space`.
Vercel에 `VITE_API_URL`이 이미 설정되어 있다면 이 주소로 변경하고 재배포해야 합니다.
로컬에서도 영어 분석을 확인하려면 아래처럼 실행합니다.

```sh
cd frontend
VITE_API_URL=https://yebeen23-emotion-wall-api.hf.space npm run dev
```

로컬 USB LED를 사용할 때는 한·영 백엔드 변경이 포함된 로컬 서버를 실행하고
`VITE_API_URL=http://127.0.0.1:8000`을 사용합니다. 클라우드 API는 노트북 USB를 제어하지 않습니다.
