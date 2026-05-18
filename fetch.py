"""Fetch and cache all posts in the 'Top comment deletes a US State #N' series.

Cache layout:
  data/cache/posts.json       -> ordered list of post stubs (round_num, id, title, url, ...)
  data/cache/posts/<id>.json  -> full post + top comments
  data/images/round_NN_<id>.<ext> -> post image

Re-runs read from cache; pass --refresh to force a re-fetch from Reddit.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).parent
CACHE_DIR = ROOT / "data" / "cache"
POSTS_DIR = CACHE_DIR / "posts"
IMG_DIR = ROOT / "data" / "images"
POSTS_INDEX = CACHE_DIR / "posts.json"

USER = "redacted"  # set to the OP's reddit username to refresh from source
# Match any of: "Top comment deletes/deleted/removes/removed [a] US State #N" (case-insensitive)
TITLE_RE = re.compile(
    r"^Top\s+[Cc]omment\s+(?:deletes?|deleted|removes?|removed)\s+(?:a\s+)?US\s+[Ss]tate\s*#?\s*(\d+)\s*$",
    re.I,
)

# Posts not returned by the user's submitted feed (Reddit caps unauth listings ~100).
# Discovered via /r/geographymemes search. round -> post id.
EXTRA_POSTS = {
    1: "1se3qj2",  # titled "Top Comment Deletes a US state" (no #)
}
UA = "geo-meme-report/0.1 (by u/script-user)"
SLEEP = 1.2  # seconds between requests, Reddit is grumpy


def _get(url: str, params: dict | None = None) -> dict:
    r = requests.get(url, params=params, headers={"User-Agent": UA}, timeout=30)
    r.raise_for_status()
    return r.json()


def list_series_posts(refresh: bool = False) -> list[dict]:
    """Walk the OP's submitted feed; keep posts whose titles match the series."""
    if POSTS_INDEX.exists() and not refresh:
        return json.loads(POSTS_INDEX.read_text(encoding="utf-8"))

    print(f"Walking /user/{USER}/submitted ...", file=sys.stderr)
    out: list[dict] = []
    after: str | None = None
    page = 0
    while True:
        page += 1
        params = {"limit": 100, "sort": "new"}
        if after:
            params["after"] = after
        data = _get(f"https://www.reddit.com/user/{USER}/submitted.json", params=params)
        children = data["data"]["children"]
        if not children:
            break
        for ch in children:
            d = ch["data"]
            m = TITLE_RE.match(d.get("title", ""))
            if not m:
                continue
            out.append(
                {
                    "round": int(m.group(1)),
                    "id": d["id"],
                    "title": d["title"],
                    "created_utc": d["created_utc"],
                    "permalink": "https://www.reddit.com" + d["permalink"],
                    "url": d.get("url_overridden_by_dest") or d.get("url"),
                    "selftext": d.get("selftext", ""),
                    "score": d.get("score", 0),
                    "num_comments": d.get("num_comments", 0),
                    "subreddit": d.get("subreddit"),
                }
            )
        after = data["data"].get("after")
        print(f"  page {page}: +{len(children)} (kept {len(out)} total)", file=sys.stderr)
        if not after:
            break
        time.sleep(SLEEP)

    # backfill posts not returned by the submitted feed (e.g. older than the 100-post cap)
    have = {p["round"] for p in out}
    for rnd, pid in EXTRA_POSTS.items():
        if rnd in have:
            continue
        try:
            d = _get(f"https://www.reddit.com/comments/{pid}.json", params={"limit": 1})[0]["data"]["children"][0]["data"]
        except Exception as exc:  # noqa: BLE001
            print(f"  extra round {rnd} id={pid}: fetch failed ({exc})", file=sys.stderr)
            continue
        out.append(
            {
                "round": rnd,
                "id": d["id"],
                "title": d["title"],
                "created_utc": d["created_utc"],
                "permalink": "https://www.reddit.com" + d["permalink"],
                "url": d.get("url_overridden_by_dest") or d.get("url"),
                "selftext": d.get("selftext", ""),
                "score": d.get("score", 0),
                "num_comments": d.get("num_comments", 0),
                "subreddit": d.get("subreddit"),
            }
        )
        time.sleep(SLEEP)

    # sort by round ascending for stable ordering
    out.sort(key=lambda r: r["round"])
    POSTS_INDEX.parent.mkdir(parents=True, exist_ok=True)
    POSTS_INDEX.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {POSTS_INDEX} with {len(out)} posts (rounds {out[0]['round']}-{out[-1]['round']})", file=sys.stderr)
    return out


def fetch_post_details(post_id: str, refresh: bool = False) -> dict:
    """Fetch a post's full JSON + top comments. Cached per id."""
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    cache = POSTS_DIR / f"{post_id}.json"
    if cache.exists() and not refresh:
        return json.loads(cache.read_text(encoding="utf-8"))

    data = _get(
        f"https://www.reddit.com/comments/{post_id}.json",
        params={"limit": 25, "sort": "top"},
    )
    cache.write_text(json.dumps(data, indent=2), encoding="utf-8")
    time.sleep(SLEEP)
    return data


def download_image(round_num: int, post_id: str, url: str, refresh: bool = False) -> Path | None:
    """Download a post's image into data/images/. Returns local path or None on skip."""
    if not url or "i.redd.it" not in url:
        # galleries, videos, etc. -- skip for now
        return None
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(urlparse(url).path).suffix or ".jpg"
    out = IMG_DIR / f"round_{round_num:02d}_{post_id}{ext}"
    if out.exists() and not refresh:
        return out
    r = requests.get(url, headers={"User-Agent": UA}, timeout=60)
    r.raise_for_status()
    out.write_bytes(r.content)
    time.sleep(SLEEP)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--refresh", action="store_true", help="Force re-fetch from Reddit")
    ap.add_argument("--skip-comments", action="store_true", help="Don't fetch per-post details")
    ap.add_argument("--skip-images", action="store_true", help="Don't download images")
    args = ap.parse_args()

    posts = list_series_posts(refresh=args.refresh)
    print(f"Series has {len(posts)} posts.", file=sys.stderr)

    for p in posts:
        if not args.skip_comments:
            fetch_post_details(p["id"], refresh=args.refresh)
        if not args.skip_images:
            local = download_image(p["round"], p["id"], p.get("url", ""), refresh=args.refresh)
            if local is None:
                print(f"  round {p['round']:02d}: NO image (url={p.get('url')!r})", file=sys.stderr)
            else:
                print(f"  round {p['round']:02d}: {local.name}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
