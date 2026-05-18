"""Image-derived empire area analysis for the final round-42 map.

Approach:
  * Load the round-42 PNG.
  * Mask out near-white background.
  * k-means cluster the non-background colored pixels into N clusters.
  * Manually map cluster centroids to empire roots (after inspecting output).
  * Report pixel-area share per empire as a corrective sanity check against the
    whole-state attribution in build_report.py — large discrepancies indicate
    split states (e.g., Hawaii eating part of SoCal, CO reaching the Pacific).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.cluster.vq import kmeans2

ROOT = Path(__file__).parent
IMG = ROOT / "data" / "images" / "round_42_1tfrme9.jpeg"
OUT = ROOT / "data" / "image_area_round42.json"

# Empire palette anchors picked from inspecting round-42 image (median RGB of
# hand-picked map regions where each empire dominates).
# NOTE: MN/WI use identical lime-green on this map so are color-ambiguous;
# pixels assigned to "MN" here represent the *combined* Greater Minnesota + WI region.
# MI's olive-green is similarly close to MN's. This is documented in the report.
EMPIRE_ANCHORS: dict[str, tuple[int, int, int]] = {
    "NM": (144, 155, 247),  # light lavender — Gulf of New Mexico bloc
    "CO": (82, 108, 221),   # mid blue
    "OR": (177, 142, 244),  # light purple — Cascadia
    "MN": (80, 176, 0),     # bright lime — Greater Minnesota
    "WI": (40, 100, 10),    # dark green (best guess; may overlap MN)
    "MI": (84, 146, 65),    # olive-green
    "MD": (2, 105, 146),    # teal — Great Maryland Empire
    "VT": (0, 56, 71),      # dark navy — The Vermomster
    "HI": (1, 96, 183),     # mid-blue — Hawaii (incl. Alaska, SoCal slice)
}


def classify(pixel_rgb: np.ndarray) -> list[str]:
    """Return empire-root label for each pixel; '' = background/text."""
    H, W = pixel_rgb.shape[:2]
    flat = pixel_rgb.reshape(-1, 3).astype(np.int32)
    # Background mask: near-white or near-black (text/borders) -> ignore.
    brightness = flat.mean(axis=1)
    is_bg = (brightness > 235) | (brightness < 15)
    # For non-bg pixels, nearest anchor (Euclidean in RGB).
    anchors = np.array(list(EMPIRE_ANCHORS.values()), dtype=np.int32)
    labels_list = list(EMPIRE_ANCHORS.keys())
    # squared distance from each pixel to each anchor
    dists = np.sum((flat[:, None, :] - anchors[None, :, :]) ** 2, axis=2)
    nearest = np.argmin(dists, axis=1)
    out = np.array([labels_list[i] for i in nearest])
    out[is_bg] = ""
    return out.reshape(H, W).tolist(), out  # also return flat


def main() -> int:
    im = np.array(Image.open(IMG).convert("RGB"))
    H, W, _ = im.shape
    print(f"Image: {W}x{H}")

    # Discover dominant colors via k-means for reference / future tuning.
    flat = im.reshape(-1, 3).astype(np.float64)
    brightness = flat.mean(axis=1)
    colored = flat[(brightness > 30) & (brightness < 235)]
    if len(colored) > 200_000:
        idx = np.random.default_rng(0).choice(len(colored), 200_000, replace=False)
        sample = colored[idx]
    else:
        sample = colored
    centroids, _ = kmeans2(sample, 12, seed=0, minit="++")
    print("Top 12 k-means centroids (RGB):")
    for c in sorted(centroids.tolist(), key=lambda v: -sum(v)):
        print(f"  #{int(c[0]):02x}{int(c[1]):02x}{int(c[2]):02x}  ({int(c[0]):3d},{int(c[1]):3d},{int(c[2]):3d})")

    # Classify every pixel against our anchors.
    _, flat_labels = classify(im)
    counts: dict[str, int] = {}
    for lbl in flat_labels:
        counts[lbl] = counts.get(lbl, 0) + 1
    total_colored = sum(v for k, v in counts.items() if k)
    print(f"\nClassified pixels (colored only, total={total_colored:,}):")
    shares: dict[str, float] = {}
    for emp, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        if not emp:
            continue
        pct = n / total_colored * 100
        shares[emp] = pct
        print(f"  {emp}: {n:>9,} ({pct:5.2f}%)")

    OUT.write_text(json.dumps({"shares_pct": shares, "anchors": EMPIRE_ANCHORS, "total_pixels_classified": total_colored}, indent=2), encoding="utf-8")
    print(f"\nWrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
