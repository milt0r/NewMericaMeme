"""Combine cached Reddit posts with the manual overrides ledger into a canonical
round-by-round dataset (data/rounds.json).

Each record has:
  round, post_id, post_url, post_title, post_body, post_score, post_num_comments,
  created_utc, image_local (or null), top_comment_body, top_comment_score,
  eliminated_state, empire_root, source, note
"""
from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).parent
CACHE = ROOT / "data" / "cache"
POSTS = CACHE / "posts"
IMG = ROOT / "data" / "images"
OVERRIDES = ROOT / "data" / "overrides.json"
OUT = ROOT / "data" / "rounds.json"


def _top_comment(post_id: str) -> tuple[str | None, int | None]:
    fp = POSTS / f"{post_id}.json"
    if not fp.exists():
        return None, None
    try:
        d = json.loads(fp.read_text(encoding="utf-8"))
        for c in d[1]["data"]["children"]:
            if c.get("kind") != "t1":
                continue
            body = (c["data"].get("body") or "").strip()
            if not body or body.startswith("![gif"):
                continue
            return body, c["data"].get("score")
    except Exception:  # noqa: BLE001
        pass
    return None, None


def _image_path(round_num: int) -> str | None:
    for ext in (".jpeg", ".jpg", ".png", ".webp"):
        for p in IMG.glob(f"round_{round_num:02d}_*{ext}"):
            return str(p.relative_to(ROOT)).replace("\\", "/")
    return None


def build() -> list[dict]:
    posts_index = {p["round"]: p for p in json.loads((CACHE / "posts.json").read_text(encoding="utf-8"))}
    overrides = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    out = []
    for entry in overrides["rounds"]:
        rnd = entry["round"]
        post = posts_index.get(rnd)
        rec = {
            "round": rnd,
            "eliminated_state": entry["eliminated"],
            "empire_root": entry["empire"],
            "source": entry["source"],
            "note": entry["note"],
            "post_id": post["id"] if post else None,
            "post_url": post["permalink"] if post else None,
            "post_title": post["title"] if post else None,
            "post_body": (post.get("selftext") or "").strip() if post else "",
            "post_score": post.get("score") if post else None,
            "post_num_comments": post.get("num_comments") if post else None,
            "created_utc": post.get("created_utc") if post else None,
            "image_local": _image_path(rnd),
            "image_url": post.get("url") if post else None,
        }
        if post:
            body, score = _top_comment(post["id"])
            rec["top_comment_body"] = body
            rec["top_comment_score"] = score
        else:
            rec["top_comment_body"] = None
            rec["top_comment_score"] = None
        out.append(rec)
    out.sort(key=lambda r: r["round"])
    OUT.write_text(json.dumps({"rounds": out, "empire_display_names": overrides["empire_display_names"]}, indent=2), encoding="utf-8")
    return out


def main() -> int:
    rounds = build()
    print(f"Wrote {OUT}: {len(rounds)} rounds")
    have_post = sum(1 for r in rounds if r["post_id"])
    have_img = sum(1 for r in rounds if r["image_local"])
    print(f"  rounds with cached Reddit post: {have_post}")
    print(f"  rounds with downloaded image:   {have_img}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
