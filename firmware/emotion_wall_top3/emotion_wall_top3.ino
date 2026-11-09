#include <Adafruit_NeoPixel.h>
#include <string.h>
#include <math.h>

constexpr uint8_t LED_PIN = 18;
constexpr uint16_t LED_COUNT = 64;
constexpr uint8_t ROW_COUNT = 3;
// Assumption: DIN chain visits left, middle, right in that order.
constexpr uint16_t ROW_START[ROW_COUNT] = {0, 22, 43};
constexpr uint16_t ROW_LENGTH[ROW_COUNT] = {22, 21, 21};
// Local data-order direction. Set an entry true to reverse that row visually.
constexpr bool ROW_REVERSED[ROW_COUNT] = {false, false, false};
static_assert(22 + 21 + 21 == LED_COUNT, "Row lengths must match total LEDs");
// Raise ONLY after checking the actual RGBW supply, wiring and fuse ratings.
// This is a software ceiling, NOT a current limiter.
constexpr uint8_t MAX_BRIGHTNESS = 96;
constexpr uint16_t PIXEL_CHANNEL_SUM_LIMIT = 160; // RGBW PWM sum, not measured current.
constexpr uint32_t FRAME_MS = 10;          // About 100 frames/sec.
constexpr uint32_t TRANSITION_MS = 2600;   // Gentle color transition.

constexpr float TAU = 6.28318530718f;

struct RowState {
  float fromColor[4] = {0, 0, 0, 0};
  float targetColor[4] = {0, 0, 0, 0};
  uint32_t transitionStart = 0;
  float targetRate = 1.0f / 3200.0f;
  float currentRate = 1.0f / 3200.0f;
  float phase = 0.0f;
};
RowState rows[ROW_COUNT];
uint32_t lastFrame = 0;
Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRBW + NEO_KHZ800);

bool topEnabled = false;
float topFromHue[3] = {0, 0, 0};
float topTargetHue[3] = {0, 0, 0};
uint32_t topTransitionStart = 0;
char line[64];
size_t used = 0;
bool overflowed = false;
unsigned long lastByte = 0;

// Strictly four decimal integers, 0..255; no signs, spaces or extra fields.
bool parseRGBW(const char *s, uint8_t out[4]) {
  for (uint8_t channel = 0; channel < 4; ++channel) {
    unsigned int value = 0;
    uint8_t digits = 0;
    while (*s >= '0' && *s <= '9') {
      if (++digits > 3) return false;
      value = value * 10 + (*s++ - '0');
      if (value > 255) return false;
    }
    if (!digits) return false;
    out[channel] = value;
    if (channel < 3) {
      if (*s++ != ',') return false;
    } else if (*s != '\0') return false;
  }
  return true;
}

float smoothStep(float x) {
  return x * x * (3.0f - 2.0f * x);
}

void currentColor(uint8_t row, uint32_t now, float out[4]) {
  RowState &state = rows[row];
  uint32_t elapsed = now - state.transitionStart;
  float t = elapsed >= TRANSITION_MS ? 1.0f :
            smoothStep((float)elapsed / TRANSITION_MS);
  for (uint8_t ch = 0; ch < 4; ++ch) {
    out[ch] = state.fromColor[ch] + (state.targetColor[ch] - state.fromColor[ch]) * t;
  }
}

void setTarget(uint8_t row, const uint8_t rgbw[4], uint32_t now) {
  if (row == 0) topEnabled = false;
  RowState &state = rows[row];
  // Preserve relative RGBW proportions, make the strongest channel full scale.
  // The hardware output still cannot exceed MAX_BRIGHTNESS per channel.
  uint8_t peak = 0;
  for (uint8_t ch = 0; ch < 4; ++ch) {
    if (rgbw[ch] > peak) peak = rgbw[ch];
  }
  float next[4];
  bool changed = false;
  for (uint8_t ch = 0; ch < 4; ++ch) {
    next[ch] = peak ? (float)rgbw[ch] * 255.0f / peak : 0.0f;
    if (fabsf(next[ch] - state.targetColor[ch]) > 0.001f) changed = true;
  }
  if (!changed) return;
  currentColor(row, now, state.fromColor);
  for (uint8_t ch = 0; ch < 4; ++ch) state.targetColor[ch] = next[ch];
  state.transitionStart = now;
}

// RGB <-> HSV helpers use hue in turns (0..1).
float wrapHue(float hue) {
  return hue - floorf(hue);
}

void hueToRGB(float hue, float saturation, float rgb[3]) {
  float h = wrapHue(hue) * 6.0f;
  int sector = (int)floorf(h);
  float fraction = h - sector;
  float low = 1.0f - saturation;
  float falling = 1.0f - saturation * fraction;
  float rising = 1.0f - saturation * (1.0f - fraction);
  switch (sector % 6) {
    case 0: rgb[0]=1; rgb[1]=rising; rgb[2]=low; break;
    case 1: rgb[0]=falling; rgb[1]=1; rgb[2]=low; break;
    case 2: rgb[0]=low; rgb[1]=1; rgb[2]=rising; break;
    case 3: rgb[0]=low; rgb[1]=falling; rgb[2]=1; break;
    case 4: rgb[0]=rising; rgb[1]=low; rgb[2]=1; break;
    default: rgb[0]=1; rgb[1]=low; rgb[2]=falling; break;
  }
}

float colorHue(float r, float g, float b) {
  float hi = fmaxf(r, fmaxf(g, b));
  float lo = fminf(r, fminf(g, b));
  float delta = hi - lo;
  if (delta <= 0.001f) return 0.11f;
  if (hi == r) return wrapHue((g - b) / delta / 6.0f);
  if (hi == g) return wrapHue(((b - r) / delta + 2.0f) / 6.0f);
  return wrapHue(((r - g) / delta + 4.0f) / 6.0f);
}

float blendHue(float a, float b, float t) {
  float difference = b - a;
  if (difference > 0.5f) difference -= 1.0f;
  if (difference < -0.5f) difference += 1.0f;
  return wrapHue(a + difference * t);
}

void currentTopHues(uint32_t now, float out[3]) {
  uint32_t elapsed = now - topTransitionStart;
  float t = elapsed >= TRANSITION_MS ? 1.0f : smoothStep((float)elapsed / TRANSITION_MS);
  for (uint8_t i = 0; i < 3; ++i) out[i] = blendHue(topFromHue[i], topTargetHue[i], t);
}

uint8_t outputChannel(float value) {
  // Round directly, without alternating frames (temporal dithering).
  if (value <= 0.0f) return 0;
  if (value >= MAX_BRIGHTNESS) return MAX_BRIGHTNESS;
  return (uint8_t)lroundf(value);
}

void renderFlow(uint32_t now) {
  uint32_t elapsed = now - lastFrame;
  if (elapsed < FRAME_MS) return;
  lastFrame = now;
  for (uint8_t row = 0; row < ROW_COUNT; ++row) {
    RowState &state = rows[row];
    float alpha = (float)elapsed / (700.0f + elapsed);
    state.currentRate += (state.targetRate - state.currentRate) * alpha;
    state.phase = wrapHue(state.phase + (float)elapsed * state.currentRate);
    float paletteHues[3];
    if (row == 0 && topEnabled) currentTopHues(now, paletteHues);
    float base[4];
    currentColor(row, now, base);
    float high = fmaxf(base[0], fmaxf(base[1], base[2]));
    float low = fminf(base[0], fminf(base[1], base[2]));
    float delta = high - low;
    float envelope = fmaxf(high, base[3]) / 255.0f;
    if (envelope <= 0.0f) {
      for (uint16_t i = 0; i < ROW_LENGTH[row]; ++i)
        strip.setPixelColor(ROW_START[row] + i, 0);
      continue;
    }
    float centerHue = 0.11f; // Warm center for neutral/white-only input.
    if (delta > 0.001f) {
      if (high == base[0]) centerHue = (base[1] - base[2]) / delta / 6.0f;
      else if (high == base[1]) centerHue = ((base[2] - base[0]) / delta + 2.0f) / 6.0f;
      else centerHue = ((base[0] - base[1]) / delta + 4.0f) / 6.0f;
      centerHue = wrapHue(centerHue);
    }
    // Full saturation, no W mixing: keep the representative emotion distinct.
    // White-only legacy input is rendered as saturated warm amber.
    constexpr float saturation = 1.0f;
    for (uint16_t i = 0; i < ROW_LENGTH[row]; ++i) {
      // Each row gets a complete moving gradient in its local coordinates.
      // An 85% floor keeps the color gradient luminous without on/off pulses.
      uint16_t local = ROW_REVERSED[row] ? ROW_LENGTH[row] - 1 - i : i;
      float position = (float)local / ROW_LENGTH[row] - state.phase;
      float crest = smoothStep(0.5f + 0.5f * sinf(TAU * position));
      float shade = 0.85f + 0.15f * crest;
      float rgb[3];
      // Approximately +/-14 degrees: related colors, recognizable emotion.
      float hue = centerHue + 0.035f * sinf(TAU * position)
                            + 0.008f * sinf(2.0f * TAU * position);
      if (row == 0 && topEnabled) {
        // One full 1st -> 2nd -> 3rd -> 1st palette travels along 22 pixels.
        float palettePosition = wrapHue(-position) * 3.0f;
        uint8_t anchor = (uint8_t)floorf(palettePosition);
        float t = smoothStep(palettePosition - anchor);
        hue = blendHue(paletteHues[anchor], paletteHues[(anchor + 1) % 3], t);
        shade = 1.0f; // Motion comes from color, no brightness flashing.
      }
      hueToRGB(hue, saturation, rgb);
      float level = MAX_BRIGHTNESS * envelope * shade;
      float raw[4] = {rgb[0] * level, rgb[1] * level, rgb[2] * level, 0.0f};
      float sum = raw[0] + raw[1] + raw[2] + raw[3];
      float scale = sum > PIXEL_CHANNEL_SUM_LIMIT ? PIXEL_CHANNEL_SUM_LIMIT / sum : 1.0f;
      uint8_t out[4];
      uint16_t actualSum = 0;
      for (uint8_t ch = 0; ch < 4; ++ch) {
        out[ch] = outputChannel(raw[ch] * scale);
        actualSum += out[ch];
      }
      // Account for rounding so even the actual integer PWM sum stays bounded.
      while (actualSum > PIXEL_CHANNEL_SUM_LIMIT) {
        uint8_t largest = 0;
        for (uint8_t ch = 1; ch < 4; ++ch) if (out[ch] > out[largest]) largest = ch;
        --out[largest];
        --actualSum;
      }
      strip.setPixelColor(ROW_START[row] + i, strip.Color(out[0], out[1], out[2], out[3]));
    }
  }
  strip.show();
}

bool parseSpeed(const char *text, uint16_t &period) {
  uint32_t value = 0;
  uint8_t digits = 0;
  while (*text >= '0' && *text <= '9') {
    if (++digits > 4) return false;
    value = value * 10 + (*text++ - '0');
  }
  if (*text || !digits || value < 900 || value > 6000) return false;
  period = (uint16_t)value;
  return true;
}

bool parseRow(const char *text, uint16_t out[6]) {
  for (uint8_t field = 0; field < 6; ++field) {
    uint32_t value = 0;
    uint8_t digits = 0;
    while (*text >= '0' && *text <= '9') {
      if (++digits > 4) return false;
      value = value * 10 + (*text++ - '0');
    }
    if (!digits) return false;
    out[field] = (uint16_t)value;
    if (field < 5) {
      if (*text++ != ',') return false;
    } else if (*text) return false;
  }
  if (out[0] < 1 || out[0] > ROW_COUNT) return false;
  for (uint8_t i = 1; i < 5; ++i) if (out[i] > 255) return false;
  return out[5] >= 900 && out[5] <= 6000;
}

bool parseTop(const char *text, uint16_t out[10]) {
  for (uint8_t field = 0; field < 10; ++field) {
    uint32_t value = 0;
    uint8_t digits = 0;
    while (*text >= '0' && *text <= '9') {
      if (++digits > 4) return false;
      value = value * 10 + (*text++ - '0');
    }
    if (!digits) return false;
    out[field] = (uint16_t)value;
    if (field < 9) { if (*text++ != ',') return false; }
    else if (*text) return false;
  }
  for (uint8_t i = 0; i < 9; ++i) if (out[i] > 255) return false;
  for (uint8_t i = 0; i < 9; i += 3)
    if (out[i] == 0 && out[i+1] == 0 && out[i+2] == 0) return false;
  return out[9] >= 600 && out[9] <= 2400;
}

void processLine() {
  line[used] = '\0';
  // Permit a single CR immediately before LF (Arduino Serial Monitor).
  if (used && line[used - 1] == '\r') line[--used] = '\0';
  if (!strcmp(line, "PING")) {
    Serial.println("READY");
    return;
  }
  if (!strncmp(line, "TOP,", 4)) {
    uint16_t fields[10];
    if (!parseTop(line + 4, fields)) { Serial.println("ERR,TOP"); return; }
    uint32_t now = millis();
    float previous[3];
    if (topEnabled) currentTopHues(now, previous);
    else {
      float base[4]; currentColor(0, now, base);
      float hue = colorHue(base[0], base[1], base[2]);
      for (uint8_t i = 0; i < 3; ++i) previous[i] = hue;
    }
    float next[3]; bool changed = !topEnabled;
    for (uint8_t i = 0; i < 3; ++i) {
      next[i] = colorHue(fields[3*i], fields[3*i+1], fields[3*i+2]);
      if (fabsf(next[i] - topTargetHue[i]) > 0.001f) changed = true;
    }
    uint8_t primary[4] = {(uint8_t)fields[0], (uint8_t)fields[1], (uint8_t)fields[2], 0};
    setTarget(0, primary, now);
    if (changed) {
      for (uint8_t i = 0; i < 3; ++i) {
        topFromHue[i] = previous[i]; topTargetHue[i] = next[i];
      }
      topTransitionStart = now;
    }
    topEnabled = true;
    rows[0].targetRate = 1.0f / fields[9];
    Serial.print("OK,TOP");
    for (uint8_t i = 0; i < 10; ++i) { Serial.print(','); Serial.print(fields[i]); }
    Serial.println();
    return;
  }
  if (!strncmp(line, "SPEED,", 6)) {
    uint16_t period;
    if (!parseSpeed(line + 6, period)) {
      Serial.println("ERR,SPEED");
      return;
    }
    for (uint8_t row = 0; row < ROW_COUNT; ++row) rows[row].targetRate = 1.0f / period;
    Serial.print("OK,SPEED,");
    Serial.println(period);
    return;
  }
  if (!strncmp(line, "ROW,", 4)) {
    uint16_t fields[6];
    if (!parseRow(line + 4, fields)) { Serial.println("ERR,ROW"); return; }
    uint8_t row = fields[0] - 1;
    uint8_t color[4];
    for (uint8_t ch = 0; ch < 4; ++ch) color[ch] = fields[ch + 1];
    setTarget(row, color, millis());
    rows[row].targetRate = 1.0f / fields[5];
    Serial.print("OK,ROW");
    for (uint8_t i = 0; i < 6; ++i) { Serial.print(','); Serial.print(fields[i]); }
    Serial.println();
    return;
  }
  uint8_t color[4];
  if (!parseRGBW(line, color)) {
    Serial.println("ERR,FORMAT");
    return;
  }
  for (uint8_t row = 0; row < ROW_COUNT; ++row) setTarget(row, color, millis());
  // ACK means target accepted; the visible transition finishes in 2.6 seconds.
  Serial.print("OK,");
  for (uint8_t i = 0; i < 4; ++i) {
    if (i) Serial.print(',');
    Serial.print(color[i]);
  }
  Serial.println();
}

void setup() {
  strip.begin();
  // Full library scale; our renderer applies the ceiling to every channel.
  // Never repeatedly rescale the NeoPixel buffer with setBrightness().
  strip.setBrightness(255);
  strip.clear();
  strip.show();
  lastFrame = millis();
  for (uint8_t row = 0; row < ROW_COUNT; ++row) rows[row].transitionStart = lastFrame;
  Serial.begin(115200);
  Serial.println("READY");
}

void loop() {
  uint16_t budget = 64;
  while (budget-- && Serial.available()) {
    char c = (char)Serial.read();
    lastByte = millis();
    if (c == '\n') {
      if (overflowed) Serial.println("ERR,LINE");
      else processLine();
      used = 0;
      overflowed = false;
    } else if (!overflowed) {
      // Reject NUL/control/non-ASCII bytes, discard until newline.
      if (c == '\0' || (c != '\r' && (c < 32 || c > 126)) || used >= sizeof(line) - 1) {
        overflowed = true;
      } else line[used++] = c;
    }
  }
  // Incomplete frames are discarded, never applied as partial colors.
  if ((used || overflowed) && millis() - lastByte > 1000) {
    used = 0;
    overflowed = false;
    Serial.println("ERR,TIMEOUT");
  }
  renderFlow(millis());
}
