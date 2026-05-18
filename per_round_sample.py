"""Per-round per-state image sampling.

For every round image, sample the dominant color at each state's pixel centroid
and classify to the nearest empire anchor. Output a per-(round, state) ownership
table that the report uses to drive an accurate animated choropleth and to
compute the actual ground-truth merger chain.

Anchor handling: the OP refreshed the color palette around round 17. Pre-#17
rounds use original colors; post-#17 use the brighter palette. We use a UNION of
anchors so that a state can match either era's color for its eventual empire.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

from sample_states import STATE_PIXELS, EMPIRE_ANCHORS as POST17_ANCHORS, sample_state

ROOT = Path(__file__).parent
IMAGES = ROOT / "data" / "images"
OUT_JSON = ROOT / "data" / "image_per_round_ownership.json"


# Pre-#17 anchor colors (from inspecting round 5-16 images).
# Same nine empires don't yet all exist; this maps to plausible "root state" colors that
# eventually become each empire's identity. Each anchor maps to a final empire.
PRE17_ANCHORS: dict[str, tuple[int, int, int]] = {
    "OR": (170, 130, 220),   # purple (Cascadia-to-be)
    "WA": (70, 35, 110),     # darker purple WA proper
    "CO": (60, 70, 170),     # darker blue
    "NM": (175, 165, 220),   # lavender
    "MN": (90, 160, 80),     # green
    "WI": (50, 100, 50),     # dark green
    "MI": (120, 170, 90),    # medium green
    "IL": (180, 210, 130),   # light yellow-green (will become MI)
    "MO": (70, 130, 60),     # mid green
    "MD": (50, 130, 140),    # teal (already MD-ish)
    "VT": (40, 80, 130),     # darker blue VT-ish
    "NY": (50, 90, 180),     # blue
    "PA": (90, 160, 220),    # light blue (will become MD)
    "HI": (30, 110, 200),    # mid-blue
    "AK": (110, 175, 230),   # AK's own light-blue (will be HI)
    "GA": (220, 130, 130),   # salmon (will be NM via #30 chain)
    "NC": (230, 150, 150),   # salmon-NC
    "VA": (220, 150, 145),   # salmon-VA
    "TN": (210, 80, 80),     # red
    "AL": (200, 90, 90),     # red-AL (with TN)
    "LA": (140, 90, 60),     # brown
    "OK": (140, 95, 60),     # brown OK
    "TX": (150, 100, 70),    # brown TX
    "MS": (240, 150, 80),    # orange
    "FL": (220, 140, 140),   # salmon FL
    "AR": (220, 145, 100),   # peach AR
}

# Which final-empire each pre-17 anchor color eventually rolls up to.
PRE17_TO_FINAL = {
    "OR": "OR", "WA": "OR",
    "CO": "CO",
    "NM": "NM", "GA": "MD", "NC": "MD", "VA": "MD",
    "TN": "MI", "AL": "NM",
    "LA": "NM", "OK": "NM", "TX": "NM",
    "MS": "NM", "FL": "NM", "AR": "NM",
    "MN": "MN", "WI": "WI", "MI": "MI", "IL": "MI", "MO": "NM",
    "MD": "MD", "PA": "MD",
    "VT": "VT", "NY": "VT",
    "HI": "HI", "AK": "HI",
}


def _classify_pre17(rgb: tuple[int, int, int]) -> str:
    arr = np.array(rgb, dtype=np.int32)
    best = min(PRE17_ANCHORS.items(),
               key=lambda kv: int(np.sum((np.array(kv[1], dtype=np.int32) - arr) ** 2)))
    return PRE17_TO_FINAL[best[0]]


def _classify_post17(rgb: tuple[int, int, int]) -> str:
    arr = np.array(rgb, dtype=np.int32)
    best = min(POST17_ANCHORS.items(),
               key=lambda kv: int(np.sum((np.array(kv[1], dtype=np.int32) - arr) ** 2)))
    return best[0]


def vote(im: np.ndarray, y: int, x: int, classify) -> str:
    votes: Counter[str] = Counter()
    for dy in (-12, 0, 12):
        for dx in (-12, 0, 12):
            rgb = sample_state(im, y + dy, x + dx, half=4)
            if rgb == (0, 0, 0):
                continue
            votes[classify(rgb)] += 1
    if not votes:
        return "??"
    return votes.most_common(1)[0][0]


def main() -> int:
    rounds_index = json.loads((ROOT / "data" / "cache" / "posts.json").read_text(encoding="utf-8"))
    rounds_index.sort(key=lambda r: r["round"])
    out: dict[int, dict[str, str]] = {}
    for r in rounds_index:
        rnd = r["round"]
        candidates = list(IMAGES.glob(f"round_{rnd:02d}_*.jpeg"))
        if not candidates:
            print(f"  round {rnd:02d}: no image")
            continue
        img_path = candidates[0]
        im = np.array(Image.open(img_path).convert("RGB"))
        classify = _classify_pre17 if rnd <= 16 else _classify_post17
        per_state = {}
        for usps, (y, x) in STATE_PIXELS.items():
            if not (0 <= y < im.shape[0] and 0 <= x < im.shape[1]):
                continue
            per_state[usps] = vote(im, y, x, classify)
        out[rnd] = per_state
        # crude verification: count unique empires this round
        n = len(set(per_state.values()))
        print(f"  round {rnd:02d}: {n} distinct empire-classes "
              f"({img_path.name})")

    OUT_JSON.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nWrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
