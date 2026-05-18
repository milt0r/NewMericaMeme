"""Shared layout: top nav, dark CSS, header/footer for all report pages."""
from __future__ import annotations

PAGES = [
    ("index.html",   "Overview"),
    ("history.html", "History"),
    ("pivots.html",  "Pivots"),
    ("sources.html", "Sources"),
]

CSS = """
:root { color-scheme: dark; }
* { box-sizing: border-box; }
body { font: 16px/1.55 -apple-system, "Segoe UI", Roboto, sans-serif; margin: 0; background: #0f1115; color: #e6e8ec; }
.topnav { background: #161a22; border-bottom: 1px solid #232a36; position: sticky; top: 0; z-index: 50; }
.topnav-inner { max-width: 1180px; margin: 0 auto; padding: 12px 24px; display: flex; align-items: center; gap: 24px; flex-wrap: wrap; }
.topnav-brand { font-weight: 700; font-size: 1.05rem; letter-spacing: .02em; }
.topnav-links { display: flex; gap: 4px; flex-wrap: wrap; }
.topnav-links a { color: #c6cfe2; text-decoration: none; padding: 6px 12px; border-radius: 6px; font-size: .95rem; }
.topnav-links a:hover { background: #1e2531; color: #fff; }
.topnav-links a.current { background: #2a3142; color: #fff; }
.topnav-repo { margin-left: auto; font-size: .85rem; color: #7a8294; }
.topnav-repo a { color: #6cb1ff; text-decoration: none; }
header.page { padding: 40px 24px 16px; max-width: 1180px; margin: 0 auto; }
h1 { font-size: 2.2rem; margin: 0 0 8px; }
h2 { border-bottom: 1px solid #2a2f3a; padding-bottom: 8px; margin-top: 48px; }
h3 { margin: 0 0 4px; font-size: 1.1rem; }
.lede { color: #a9b0bd; font-size: 1.02rem; max-width: 740px; }
main { max-width: 1180px; margin: 0 auto; padding: 0 24px 80px; }
table { width: 100%; border-collapse: collapse; margin-top: 12px; font-size: .92rem; }
th, td { border-bottom: 1px solid #232a36; padding: 8px 6px; text-align: left; vertical-align: top; }
th { background: #1a1f29; font-weight: 600; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
.note { font-size: .85rem; color: #8b93a7; }
a { color: #6cb1ff; }
footer { color: #7a8294; font-size: .8rem; margin-top: 60px; border-top: 1px solid #232a36; padding-top: 16px; }
.chart-block { margin: 20px 0 40px; }
.empire-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }
.empire-card { background: #161a22; border: 1px solid #232a36; border-radius: 10px; padding: 16px; }
.empire-meta { color: #8b93a7; font-size: .85rem; margin: 0 0 8px; }
.absorb-list { padding-left: 18px; margin: 0; font-size: .92rem; }
.absorb-list li { margin: 3px 0; }
.absorb-list ul { padding-left: 18px; margin: 3px 0; border-left: 2px solid #2a3142; }
.root-list { padding-left: 0; list-style: none; }
.root-list > li { font-weight: 600; }
.round-badge { background: #2a3142; color: #c6cfe2; padding: 1px 6px; border-radius: 4px; font-size: .75rem; margin-right: 6px; font-variant-numeric: tabular-nums; }
.root-badge { background: #3a4a66; color: #d6e0f5; padding: 1px 6px; border-radius: 4px; font-size: .7rem; margin-right: 6px; text-transform: uppercase; }
.pop { color: #7a8294; font-size: .8rem; }
.source-pill { display: inline-block; font-size: .7rem; padding: 1px 6px; border-radius: 999px; background: #243044; color: #a8b6cf; margin-left: 6px; }
.metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(380px, 1fr)); gap: 16px; }
.next-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; margin-top: 16px; }
.next-card { background: #161a22; border: 1px solid #232a36; border-radius: 10px; padding: 18px; }
.next-card a { display: inline-block; margin-top: 8px; font-weight: 600; }

/* History page */
.timeline { position: relative; margin: 0; padding: 0; }
.tl-item { background: #161a22; border: 1px solid #232a36; border-radius: 10px; padding: 18px; margin: 18px 0; scroll-margin-top: 80px; }
.tl-item header { display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap; margin-bottom: 8px; padding: 0; max-width: none; }
.tl-item .rnd-num { font-size: 1.8rem; font-weight: 800; color: #6cb1ff; min-width: 60px; }
.tl-item h3 { font-size: 1.1rem; margin: 0; }
.tl-item .meta { color: #7a8294; font-size: .85rem; margin-left: auto; }
.tl-grid { display: grid; grid-template-columns: 1fr 1.2fr; gap: 20px; align-items: start; }
@media (max-width: 720px) { .tl-grid { grid-template-columns: 1fr; } }
.tl-img { width: 100%; height: auto; border-radius: 6px; border: 1px solid #2a2f3a; display: block; }
.tl-body { font-size: .95rem; }
.tl-body blockquote { margin: 8px 0; padding: 8px 12px; border-left: 3px solid #3a4a66; color: #c6cfe2; background: #1a1f29; border-radius: 0 6px 6px 0; }
.tl-elim { background: #2a3142; border-radius: 6px; padding: 8px 12px; margin: 8px 0; font-size: .95rem; }
.tl-elim strong { color: #ff9b9b; }
.tl-elim .arrow { color: #7a8294; margin: 0 6px; }
.tl-elim .empire { color: #a8e6c1; font-weight: 600; }
.tl-top { background: #1a2330; border-radius: 6px; padding: 8px 12px; margin-top: 8px; font-size: .9rem; color: #c6cfe2; }
.tl-top .lbl { color: #7a8294; font-size: .75rem; text-transform: uppercase; letter-spacing: .05em; display: block; margin-bottom: 2px; }

/* Anchor jump strip */
.jump-strip { background: #161a22; padding: 10px 24px; border-bottom: 1px solid #232a36; position: sticky; top: 50px; z-index: 40; display: flex; gap: 6px; overflow-x: auto; white-space: nowrap; max-width: 100%; }
.jump-strip a { color: #6cb1ff; padding: 3px 8px; border-radius: 4px; text-decoration: none; font-size: .82rem; font-variant-numeric: tabular-nums; }
.jump-strip a:hover { background: #2a3142; }

/* Pivots tabs */
.metric-tabs { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 16px; }
.metric-tabs button { background: #161a22; border: 1px solid #232a36; color: #c6cfe2; padding: 6px 14px; border-radius: 999px; cursor: pointer; font-size: .9rem; }
.metric-tabs button.active { background: #2a3142; color: #fff; border-color: #3a4a66; }
.metric-panel { display: none; }
.metric-panel.active { display: block; }

/* Sources */
.src-table td:first-child { font-weight: 600; }

/* Image-based map slider */
.img-slider { background: #161a22; border: 1px solid #232a36; border-radius: 10px; padding: 14px; }
.img-slider-controls { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 12px; }
.img-slider-controls input[type=range] { flex: 1; min-width: 200px; accent-color: #6cb1ff; }
.is-btn { background: #2a3142; color: #fff; border: 1px solid #3a4a66; border-radius: 6px; padding: 6px 12px; cursor: pointer; font-size: .9rem; }
.is-btn:hover { background: #3a4a66; }
.is-label { color: #c6cfe2; font-size: .9rem; font-variant-numeric: tabular-nums; }
.is-speed { display: flex; align-items: center; gap: 6px; color: #8b93a7; font-size: .85rem; }
.is-speed select { background: #1a1f29; color: #e6e8ec; border: 1px solid #2a2f3a; border-radius: 4px; padding: 4px 6px; }
.img-slider-stage { background: #0f1115; border-radius: 6px; overflow: hidden; }
.img-slider-stage img { display: block; width: 100%; height: auto; }
.img-slider-caption { margin-top: 8px; display: flex; gap: 16px; flex-wrap: wrap; }

/* Filter input + journey table */
.filter-input { width: 100%; max-width: 480px; background: #1a1f29; color: #e6e8ec; border: 1px solid #2a2f3a; border-radius: 6px; padding: 8px 12px; font-size: .95rem; margin-top: 8px; }
.filter-input:focus { outline: none; border-color: #6cb1ff; }
#journey tbody tr:hover { background: #1a1f29; }

/* Rules accordion on index */
.rules { margin-top: 12px; max-width: 740px; }
.rules summary { cursor: pointer; color: #6cb1ff; font-size: .95rem; padding: 6px 0; }
.rules p { color: #a9b0bd; font-size: .95rem; margin: 8px 0; }
"""


def nav_html(current: str) -> str:
    links = "".join(
        f'<a href="{href}" class="{ "current" if href == current else "" }">{label}</a>'
        for href, label in PAGES
    )
    return f"""<nav class="topnav"><div class="topnav-inner">
  <span class="topnav-brand">NewMericaMeme</span>
  <span class="topnav-links">{links}</span>
  <span class="topnav-repo"><a href="https://github.com/milt0r/NewMericaMeme">GitHub</a></span>
</div></nav>"""


def page(current_href: str, title: str, header_html: str, body_html: str, include_plotly: bool = True) -> str:
    plotly = '<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>' if include_plotly else ""
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{title} — NewMericaMeme</title>
{plotly}
<style>{CSS}</style>
</head><body>
{nav_html(current_href)}
<header class="page">{header_html}</header>
<main>
{body_html}
<footer>
  <p>Source: <a href="https://github.com/milt0r/NewMericaMeme">milt0r/NewMericaMeme</a> · static report, no live API calls · map images from the original Reddit posts</p>
</footer>
</main>
</body></html>
"""
