import brandLogo from './assets/emotion-wall-logo.png'

export const appTemplate = `
  <main class="emotion-app">
    <header class="app-header">
      <div class="brand">
        <img class="brand-icon" src="${brandLogo}" alt="" width="36" height="36" aria-hidden="true">
        <strong>Emotion Wall</strong>
      </div>
      <span class="menu-icon" aria-hidden="true">☰</span>
    </header>
    <section class="intro">
      <h1>오늘 당신의 감정을<br>분석해볼까요?</h1>
    </section>
    <section class="input-section">
      <textarea
        id="emotionText"
        maxlength="500"
        placeholder="오늘 기분이나 생각을 자유롭게 적어주세요..."
        aria-label="감정 입력"
      ></textarea>
      <div class="char-count">
        <span id="count">0</span> / 500
      </div>
      <button id="submitButton" type="button">
        감정 분석하기
      </button>
    </section>
    <p id="analysisError" class="analysis-error" role="alert" hidden></p>
    <section id="resultSection" class="result-section" hidden>
      <div class="result-header">
        <h2>분석 결과</h2>
        <span id="resultDate"></span>
      </div>
      <div class="result-content">
        <div class="donut-wrapper">
          <div
            class="donut-chart"
            id="donutChart"
            role="img"
            aria-label="감정 비율 도넛 차트"
          >
            <div class="donut-center">
              <span class="emotion-marker" id="emotionMarker" aria-hidden="true"></span>
              <small>주요 감정</small>
              <strong id="mainEmotion">-</strong>
            </div>
          </div>
        </div>
        <div class="emotion-list" id="emotionList"></div>
      </div>
      <h3>나의 감정 말랑이</h3>
      <p class="ball-caption">나의 감정 말랑이를 화면에서 미리 확인하세요. 말랑이를 눌러보세요.</p>
      <div
        id="ballGrid"
        class="ball-grid"
        aria-label="감정별 색상이 적용된 말랑이 12개"
      ></div>
      <section id="ledSection" class="led-section" hidden aria-label="LED 전송 결과와 효과 미리보기"></section>
    </section>
  </main>
`
