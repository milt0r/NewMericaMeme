"""Per-state color sampling on the OP's round-42 map.

Approach:
  * Map US lat/lon centroids of each state to pixel coords via a simple linear
    affine fit calibrated to the OP's 1508x1043 base map.
  * Sample the dominant color in a 3x3 patch grid around each centroid (median
    of each patch then majority vote across patches) — robust to text labels
    and state-border pixels.
  * Classify each state's color to the nearest of nine empire anchor colors.
  * Output: per-(state, final_empire) ground-truth table.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).parent
IMG = ROOT / "data" / "images" / "round_42_1tfrme9.jpeg"

# Empire anchor colors (median RGB sampled from clearly-in-empire regions of round 42).
EMPIRE_ANCHORS: dict[str, tuple[int, int, int]] = {
    "NM": (144, 155, 247),  # light lavender — Gulf of New Mexico bloc
    "CO": (53, 88, 213),    # darker blue (CO/CA bloc)
    "OR": (177, 142, 244),  # light purple — Cascadia
    "MN": (80, 176, 0),     # bright lime — Greater Minnesota
    "WI": (8, 72, 8),       # very dark green — Wisconsin alone
    "MI": (96, 177, 48),    # medium olive-green — Michigan + OH + IN + IL
    "MD": (2, 105, 146),    # teal — Great Maryland Empire
    "VT": (0, 56, 71),      # dark navy — The Vermomster
    "HI": (1, 96, 183),     # mid-blue — Hawaii (incl. Alaska + SoCal slice)
}


# Approximate US-state lat/lon centroids (decimal degrees) — Census 2020 internal points
STATE_LATLON: dict[str, tuple[float, float]] = {
    "AL": (32.806, -86.791), "AZ": (33.729, -111.431), "AR": (34.969, -92.373),
    "CA": (36.116, -119.681), "CO": (39.060, -105.311), "CT": (41.598, -72.755),
    "DE": (39.318, -75.508), "FL": (27.766, -81.687), "GA": (33.040, -83.643),
    "ID": (44.240, -114.479), "IL": (40.349, -88.986), "IN": (39.849, -86.258),
    "IA": (42.011, -93.210), "KS": (38.526, -96.726), "KY": (37.668, -84.670),
    "LA": (31.169, -91.867), "ME": (44.693, -69.381), "MD": (39.063, -76.802),
    "MA": (42.230, -71.530), "MI": (43.326, -84.536), "MN": (45.694, -93.900),
    "MS": (32.741, -89.678), "MO": (38.456, -92.288), "MT": (46.921, -110.454),
    "NE": (41.125, -98.268), "NV": (38.313, -117.055), "NH": (43.452, -71.563),
    "NJ": (40.298, -74.521), "NM": (34.840, -106.248), "NY": (42.165, -74.948),
    "NC": (35.630, -79.806), "ND": (47.528, -99.784), "OH": (40.388, -82.764),
    "OK": (35.565, -96.928), "OR": (44.572, -122.071), "PA": (40.590, -77.210),
    "RI": (41.680, -71.512), "SC": (33.856, -80.945), "SD": (44.299, -99.439),
    "TN": (35.747, -86.692), "TX": (31.054, -97.563), "UT": (40.150, -111.862),
    "VT": (44.045, -72.710), "VA": (37.769, -78.170), "WA": (47.400, -121.490),
    "WV": (38.491, -80.954), "WI": (44.268, -89.616), "WY": (42.756, -107.302),
    # Insets — separate region of the map, not lat/lon-based; use direct pixels
    "AK": None, "HI": None,
}

# Direct pixel coords for inset states (Alaska bottom-left, Hawaii inset)
INSET_PIXELS: dict[str, tuple[int, int]] = {
    "AK": (820, 130),
    "HI": (940, 320),
}


def latlon_to_pixel(lat: float, lon: float) -> tuple[int, int]:
    """Map lat/lon to pixel (y, x) on the OP's 1508x1043 base map.
    Calibrated from visible landmarks: WA NW corner, FL Keys, Maine, S TX.
    """
    # X: lon -124.5 -> x=40, lon -67 -> x=1400
    x = 40 + (lon - (-124.5)) / (-67 - (-124.5)) * (1400 - 40)
    # Y: lat 49.0 -> y=20, lat 25.0 -> y=720
    y = 20 + (49.0 - lat) / (49.0 - 25.0) * (720 - 20)
    return int(round(y)), int(round(x))


STATE_PIXELS: dict[str, tuple[int, int]] = {}
for usps, ll in STATE_LATLON.items():
    if ll is None:
        STATE_PIXELS[usps] = INSET_PIXELS[usps]
    else:
        STATE_PIXELS[usps] = latlon_to_pixel(*ll)


def classify(rgb: tuple[int, int, int]) -> str:
    arr = np.array(rgb, dtype=np.int32)
    best = min(EMPIRE_ANCHORS.items(),
               key=lambda kv: int(np.sum((np.array(kv[1], dtype=np.int32) - arr) ** 2)))
    return best[0]


def sample_state(im: np.ndarray, y: int, x: int, half: int = 8) -> tuple[int, int, int]:
    H, W, _ = im.shape
    y0, y1 = max(0, y - half), min(H, y + half + 1)
    x0, x1 = max(0, x - half), min(W, x + half + 1)
    patch = im[y0:y1, x0:x1].reshape(-1, 3)
    if patch.size == 0:
        return (0, 0, 0)
    br = patch.mean(axis=1)
    keep = (br > 30) & (br < 235)
    if keep.sum() == 0:
        return (0, 0, 0)
    median = np.median(patch[keep], axis=0).astype(int)
    return tuple(int(v) for v in median)


def classify_at(im: np.ndarray, y: int, x: int) -> tuple[str | None, tuple[int, int, int]]:
    rgb = sample_state(im, y, x, half=5)
    if rgb == (0, 0, 0):
        return None, rgb
    return classify(rgb), rgb


def vote(im: np.ndarray, y: int, x: int) -> tuple[str, dict]:
    """Vote across a 3x3 grid of sample points; majority wins. Skip near-bg patches."""
    votes: Counter[str] = Counter()
    detail = {}
    for dy in (-18, 0, 18):
        for dx in (-18, 0, 18):
            emp, rgb = classify_at(im, y + dy, x + dx)
            detail[f"({dy:+d},{dx:+d})"] = {"rgb": list(rgb), "empire": emp}
            if emp is not None:
                votes[emp] += 1
    if not votes:
        return "??", detail
    return votes.most_common(1)[0][0], detail


def main() -> int:
    im = np.array(Image.open(IMG).convert("RGB"))
    H, W, _ = im.shape
    print(f"Image: {W}x{H}")
    rows = []
    by_empire: Counter[str] = Counter()
    for usps, (y, x) in STATE_PIXELS.items():
        if not (0 <= y < H and 0 <= x < W):
            print(f"  WARN {usps}: pixel ({y},{x}) out of bounds")
            continue
        emp, detail = vote(im, y, x)
        rgb = sample_state(im, y, x)
        by_empire[emp] += 1
        rows.append({"usps": usps, "y": y, "x": x, "rgb": list(rgb),
                     "empire": emp, "votes": detail})

    print(f"\nPer-state final empire (3x3 vote sampling):")
    for r in sorted(rows, key=lambda r: r["usps"]):
        print(f"  {r['usps']:3s} pixel({r['y']:4d},{r['x']:4d}) "
              f"rgb({r['rgb'][0]:3d},{r['rgb'][1]:3d},{r['rgb'][2]:3d}) -> {r['empire']}")
    print(f"\nEmpire counts: {dict(by_empire.most_common())}")
    print(f"Total: {sum(by_empire.values())} states classified")

    out = ROOT / "data" / "image_state_empire_round42.json"
    out.write_text(json.dumps({
        "anchors": {k: list(v) for k, v in EMPIRE_ANCHORS.items()},
        "state_assignments": {r["usps"]: r["empire"] for r in rows},
        "samples": rows,
    }, indent=2), encoding="utf-8")
    print(f"\nWrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# Hand-picked pixel centroids (y, x) for each state on the OP's 1508x1043 base map.
# Coords nudged to avoid text labels, state borders, and the OP's mid-state splits.
# We sample a 21x21 patch around each pixel and take the median color.
STATE_PIXELS: dict[str, tuple[int, int]] = {
    # Pacific / Mountain West
    "WA": (110, 220),
    "OR": (200, 180),
    "CA": (430, 130),   # central CA (around Fresno area) — north was Cascadia/NM, south Hawaii
    "NV": (320, 230),
    "ID": (200, 290),
    "MT": (130, 380),
    "WY": (250, 380),
    "UT": (320, 320),
    "CO": (340, 410),
    "AZ": (450, 280),
    "NM": (470, 410),
    # Plains
    "ND": (160, 540),
    "SD": (230, 540),
    "NE": (290, 560),
    "KS": (370, 570),
    "OK": (450, 580),
    "TX": (570, 540),
    "MN": (170, 640),
    "IA": (290, 640),
    "MO": (370, 670),
    "AR": (440, 700),
    "LA": (510, 720),
    # Upper Midwest
    "WI": (200, 740),   # nudge up to hit the dark-green WI proper
    "IL": (380, 770),   # nudge south, avoid the IL label
    "MI": (220, 850),
    "IN": (340, 850),   # nudge to interior, avoid IN label
    "OH": (270, 920),   # nudge north of OH label
    "KY": (380, 900),
    "TN": (440, 850),
    "MS": (480, 790),
    "AL": (500, 870),
    # Southeast
    "GA": (510, 920),
    "FL": (620, 970),
    "SC": (470, 970),
    "NC": (430, 1020),
    # Mid-Atlantic / Northeast
    "WV": (350, 980),
    "VA": (400, 1040),
    "MD": (370, 1080),  # nudge east to actual MD, not the panhandle
    "DE": (340, 1100),
    "PA": (290, 1050),  # nudge to interior PA
    "NJ": (300, 1110),
    "NY": (230, 1100),  # nudge east of NY label
    "CT": (270, 1190),
    "RI": (260, 1240),
    "MA": (240, 1220),
    "VT": (190, 1180),  # nudge south of VT label
    "NH": (200, 1220),  # nudge to NH interior, avoid label
    "ME": (130, 1280),
    # Insets
    "AK": (820, 130),
    "HI": (940, 320),
}


def classify(rgb: tuple[int, int, int]) -> str:
    arr = np.array(rgb, dtype=np.int32)
    best = min(EMPIRE_ANCHORS.items(),
               key=lambda kv: int(np.sum((np.array(kv[1], dtype=np.int32) - arr) ** 2)))
    return best[0]


def sample_state(im: np.ndarray, y: int, x: int, half: int = 10) -> tuple[int, int, int]:
    """Sample a 21x21 patch (median, ignoring near-bg pixels)."""
    H, W, _ = im.shape
    y0, y1 = max(0, y - half), min(H, y + half + 1)
    x0, x1 = max(0, x - half), min(W, x + half + 1)
    patch = im[y0:y1, x0:x1].reshape(-1, 3)
    if patch.size == 0:
        return (0, 0, 0)
    br = patch.mean(axis=1)
    keep = (br > 30) & (br < 235)
    if keep.sum() == 0:
        return (0, 0, 0)
    median = np.median(patch[keep], axis=0).astype(int)
    return tuple(int(v) for v in median)


def classify_at(im: np.ndarray, y: int, x: int) -> tuple[str | None, tuple[int, int, int]]:
    rgb = sample_state(im, y, x, half=5)
    if rgb == (0, 0, 0):
        return None, rgb
    return classify(rgb), rgb


def vote(im: np.ndarray, y: int, x: int) -> tuple[str, dict]:
    """Vote across a 3x3 grid of sample points (each a small patch)."""
    votes = Counter()
    detail = {}
    for dy in (-22, 0, 22):
        for dx in (-22, 0, 22):
            emp, rgb = classify_at(im, y + dy, x + dx)
            key = f"({dy:+d},{dx:+d})"
            detail[key] = {"rgb": list(rgb), "empire": emp}
            if emp is not None:
                votes[emp] += 1
    if not votes:
        return "??", detail
    return votes.most_common(1)[0][0], detail


def main() -> int:
    im = np.array(Image.open(IMG).convert("RGB"))
    H, W, _ = im.shape
    print(f"Image: {W}x{H}")
    rows = []
    by_empire: Counter[str] = Counter()
    for usps, (y, x) in STATE_PIXELS.items():
        if not (0 <= y < H and 0 <= x < W):
            print(f"  WARN {usps}: pixel ({y},{x}) out of bounds")
            continue
        emp, detail = vote(im, y, x)
        # also keep the median of the center patch as the representative rgb
        rgb = sample_state(im, y, x)
        by_empire[emp] += 1
        rows.append({"usps": usps, "y": y, "x": x, "rgb": list(rgb), "empire": emp, "votes": detail})

    print(f"\nPer-state final empire (3x3 vote sampling):")
    for r in sorted(rows, key=lambda r: r["usps"]):
        print(f"  {r['usps']:3s} pixel({r['y']:4d},{r['x']:4d}) "
              f"rgb({r['rgb'][0]:3d},{r['rgb'][1]:3d},{r['rgb'][2]:3d}) -> {r['empire']}")
    print(f"\nEmpire counts: {dict(by_empire.most_common())}")
    print(f"Total: {sum(by_empire.values())} states classified")

    out = ROOT / "data" / "image_state_empire_round42.json"
    out.write_text(json.dumps({
        "anchors": {k: list(v) for k, v in EMPIRE_ANCHORS.items()},
        "state_assignments": {r["usps"]: r["empire"] for r in rows},
        "samples": rows,
    }, indent=2), encoding="utf-8")
    print(f"\nWrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
