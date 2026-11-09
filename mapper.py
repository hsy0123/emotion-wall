"""mapper.py - 감정 확률(scores) -> 색 그라데이션(gradient)

순수 함수로만 구성되어 있어 분석 모델/하드웨어와 독립적으로 테스트할 수 있습니다.
색 보간은 sRGB가 아닌 OKLab에서 수행합니다 (중간색이 탁해지지 않음).
"""
import json
import math
from pathlib import Path

PALETTE_PATH = Path(__file__).with_name("palette.json")


def load_palette(path=PALETTE_PATH):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------- 색공간
def _to_lin(c):
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _to_srgb(c):
    c = max(0.0, min(1.0, c))
    return 255 * (12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055)


def rgb_to_oklab(r, g, b):
    r, g, b = _to_lin(r), _to_lin(g), _to_lin(b)
    l = max(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b, 0) ** (1 / 3)
    m = max(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b, 0) ** (1 / 3)
    s = max(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b, 0) ** (1 / 3)
    return (
        0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
        1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
        0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s,
    )


def hex_to_oklab(h):
    h = h.lstrip("#")
    return rgb_to_oklab(*(int(h[i:i + 2], 16) for i in (0, 2, 4)))


def oklab_to_rgb(L, a, b):
    l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bl = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return [int(round(_to_srgb(v))) for v in (r, g, bl)]


# ---------------------------------------------------------------- 매퍼
def map_emotion(scores, intensity=1.0, palette=None, tuning=None):
    """scores(합=1) -> gradient stop 리스트.

    반환: [{"pos": 0.0~1.0, "rgb": [r,g,b], "white": 0.0~1.0}, ...]
    - white: RGBW의 W 채널 힌트 (따뜻한 화이트 비중). 변환 방식은 Output 쪽에서 결정.
    """
    palette = palette or load_palette()
    cfg = palette["mapper"]
    tuning = tuning or palette.get("tuning", {})
    sat = tuning.get("saturation", 1.0)
    lit = tuning.get("lightness", 1.0)

    # 1) 상위 k개 + 임계값 필터 후 재정규화 (모든 감정을 섞으면 색이 탁해짐)
    top = sorted(scores.items(), key=lambda kv: -kv[1])[: cfg["top_k"]]
    kept = [(e, p) for e, p in top if p >= cfg["threshold"]] or [top[0]]
    total = sum(p for _, p in kept)
    kept = [(e, p / total) for e, p in kept]

    # 2) 확률 비중만큼 구간을 차지하도록 앵커 배치 (구간 중앙 기준 -> 감정 사이가 부드럽게 이어짐)
    anchors, start = [], 0.0
    for emo, p in kept:
        info = palette["emotions"][emo]
        n = len(info["colors"])
        for i, hx in enumerate(info["colors"]):
            anchors.append((start + p * (i + 0.5) / n, hex_to_oklab(hx), info["white"]))
        start += p
    anchors.insert(0, (0.0, anchors[0][1], anchors[0][2]))
    anchors.append((1.0, anchors[-1][1], anchors[-1][2]))

    # 3) intensity -> 명도, tuning -> 실물 LED 보정용 채도/명도 계수
    scale = (cfg["intensity_floor"] + (1 - cfg["intensity_floor"]) * intensity) * lit
    stops = []
    for pos, (L, a, b), w in anchors:
        stops.append({
            "pos": round(pos, 3),
            "rgb": oklab_to_rgb(L * scale, a * sat, b * sat),
            "white": round(w, 2),
        })
    return stops


def _lab_stops(stops):
    return [(s["pos"], rgb_to_oklab(*s["rgb"]), s["white"]) for s in stops]


def _color_at(lab, t):
    """그라데이션 위의 위치 t(0~1)의 색을 OKLab 보간으로 구함."""
    j = 0
    while j < len(lab) - 2 and t > lab[j + 1][0]:
        j += 1
    (p0, c0, w0), (p1, c1, w1) = lab[j], lab[j + 1]
    u = 0.0 if p1 == p0 else min(max((t - p0) / (p1 - p0), 0.0), 1.0)
    mix = [c0[k] + (c1[k] - c0[k]) * u for k in range(3)]
    return {"rgb": oklab_to_rgb(*mix), "white": round(w0 + (w1 - w0) * u, 2)}


def sample_gradient(stops, n_leds):
    """일렬 LED(스트립)용: n_leds개로 그라데이션 샘플링."""
    lab = _lab_stops(stops)
    return [_color_at(lab, i / (n_leds - 1) if n_leds > 1 else 0.0) for i in range(n_leds)]


# ---------------------------------------------------------------- 격자(말랑이 판)
DEFAULT_GRID = {"rows": 3, "cols": 4, "angle": 45, "serpentine": False}


def grid_config(palette=None, override=None):
    """palette.json의 grid 설정 + 호출 시 덮어쓰기."""
    palette = palette or load_palette()
    return {**DEFAULT_GRID, **palette.get("grid", {}), **(override or {})}


def build_grid(stops, rows=3, cols=4, angle=45, serpentine=False):
    """gradient를 rows x cols 판에 펼쳐서 LED(공) 하나하나의 색을 구함.

    - angle: 그라데이션 진행 방향(도). 0=왼쪽->오른쪽, 90=위->아래, 45=왼쪽 위->오른쪽 아래.
      (화면 좌표계 기준, y는 아래로 증가)
    - 각 공의 중심을 방향 벡터에 투영해 0~1 위치(t)를 얻고, 그 위치의 색을 사용.
      첫/마지막 공이 정확히 gradient의 처음/끝 색이 되도록 공 중심 범위로 정규화.
    - serpentine=True: 홀수 행은 오른쪽->왼쪽으로 배선된 판 (index 순서에 반영).
    반환: 배선 순서(index)대로의 LED 리스트 [{index, row, col, rgb, white}, ...]
    """
    lab = _lab_stops(stops)
    th = math.radians(angle)
    dx, dy = math.cos(th), math.sin(th)

    def proj(r, c):
        return (c + 0.5) * dx + (r + 0.5) * dy

    corners = [proj(r, c) for r in (0, rows - 1) for c in (0, cols - 1)]
    lo, hi = min(corners), max(corners)
    span = hi - lo

    leds, index = [], 0
    for r in range(rows):
        cs = range(cols - 1, -1, -1) if serpentine and r % 2 == 1 else range(cols)
        for c in cs:
            t = 0.0 if span < 1e-9 else (proj(r, c) - lo) / span
            t = round(min(max(t, 0.0), 1.0), 6)
            leds.append({"index": index, "row": r, "col": c, **_color_at(lab, t)})
            index += 1
    return leds
