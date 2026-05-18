"""Build the static HTML report at docs/index.html.

Steps:
  1. Load canonical round ledger (data/rounds.json).
  2. Load per-state metrics (state_data.py).
  3. Replay rounds -> merger forest (root state -> list of absorbed states in order).
  4. Compute per-round per-empire aggregates (pop sums, GDP sums, weighted means).
  5. Render Plotly charts (cumulative pop, GDP, land area; final-ranking bars).
  6. Render merger trees + ledger table + final metrics table into index.html.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import plotly.graph_objects as go

from state_data import STATES, VINTAGES

ROOT = Path(__file__).parent
ROUNDS_JSON = ROOT / "data" / "rounds.json"
IMG_AREA_JSON = ROOT / "data" / "image_area_round42.json"
IMG_SRC = ROOT / "data" / "images"
DOCS = ROOT / "docs"
DOCS_IMG = DOCS / "assets" / "maps"
OUT = DOCS / "index.html"

PLOTLY_COLORS = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
]


# ---------- model ----------------------------------------------------------

def build_model(rounds: list[dict]) -> dict:
    """Replay rounds; return merger forest + per-round aggregates.

    DC is excluded — the meme map only shows the 50 states and DC was never in play.
    """
    states_in_play = [u for u in STATES if u != "DC"]
    ownership: dict[str, str] = {u: u for u in states_in_play}

    def resolve(u: str) -> str:
        # path-compress for speed and to keep ownership flat
        seen = []
        while ownership[u] != u:
            seen.append(u)
            u = ownership[u]
        for s in seen:
            ownership[s] = u
        return u

    # For each absorbed state, record the *direct* parent at time of absorption
    # (i.e. the empire-root the eliminated state's own empire merged into).
    # children[parent] = ordered list of (round, child_root) where child_root
    # was, at that round, a root of its own sub-empire.
    children: dict[str, list[tuple[int, str]]] = {u: [] for u in states_in_play}
    timeline: list[dict] = []

    for r in rounds:
        rnd = r["round"]
        elim = r["eliminated_state"]
        emp = r["empire_root"]
        if elim and emp:
            elim_root = resolve(elim)
            emp_root = resolve(emp)
            if elim_root != emp_root:
                children[emp_root].append((rnd, elim_root))
                ownership[elim_root] = emp_root
        # snapshot: group every state by its current resolved root
        empires: dict[str, list[str]] = {}
        for usps in states_in_play:
            empires.setdefault(resolve(usps), []).append(usps)
        snap = {"round": rnd, "empires": {}}
        for root, members in empires.items():
            agg = aggregate(members)
            agg["members"] = members
            snap["empires"][root] = agg
        timeline.append(snap)

    final = timeline[-1]["empires"]
    return {"ownership": ownership, "children": children, "timeline": timeline, "final": final}


def aggregate(members: list[str]) -> dict:
    pop = sum(STATES[m]["population"] for m in members)
    land = sum(STATES[m]["land_area_sq_mi"] for m in members)
    water = sum(STATES[m]["water_area_sq_mi"] for m in members)
    total = land + water
    gdp = sum(STATES[m]["gdp_million_usd"] for m in members)
    mhi = sum(STATES[m]["median_household_income_usd"] * STATES[m]["population"] for m in members) / pop if pop else 0
    bach = sum(STATES[m]["bachelors_or_higher_pct"] * STATES[m]["population"] for m in members) / pop if pop else 0
    return {
        "population": pop,
        "land_area_sq_mi": land,
        "water_area_sq_mi": water,
        "water_pct": (water / total * 100.0) if total else 0,
        "gdp_million_usd": gdp,
        "gdp_per_capita_usd": (gdp * 1_000_000 / pop) if pop else 0,
        "median_household_income_usd": mhi,
        "bachelors_or_higher_pct": bach,
    }


# ---------- charts ---------------------------------------------------------

def line_chart(timeline: list[dict], final_roots: list[str], metric: str, title: str, yaxis: str, display_names: dict) -> str:
    """Plot one line per final surviving empire, traced backward through rounds.
    For each surviving empire, its value at round R = sum of metric over the
    *current* members of that empire at round R (since each member was an
    independent empire until it was absorbed).
    """
    # owner-at-round-R for each surviving root
    fig = go.Figure()
    rounds = [s["round"] for s in timeline]
    # for each surviving root, figure out which states map into it through history.
    # at round R, the contributing states = members of empire `root` AT round R.
    for i, root in enumerate(final_roots):
        ys = []
        for snap in timeline:
            # find the empire snapshot that contains `root` (which by definition is `root` itself)
            agg = snap["empires"].get(root)
            ys.append(agg[metric] if agg else None)
        fig.add_trace(go.Scatter(
            x=rounds, y=ys, mode="lines+markers",
            name=display_names.get(root, STATES[root]["name"]),
            line=dict(color=PLOTLY_COLORS[i % len(PLOTLY_COLORS)], width=2),
            hovertemplate="Round %{x}<br>%{y:,.0f}<extra>%{fullData.name}</extra>",
        ))
    fig.update_layout(
        title=title, xaxis_title="Round", yaxis_title=yaxis,
        template="plotly_white", height=460, margin=dict(l=40, r=20, t=60, b=40),
        legend=dict(orientation="h", y=-0.18),
    )
    return fig.to_html(full_html=False, include_plotlyjs=False, div_id=f"chart-{metric}")


def bar_chart(final: dict, final_roots: list[str], metric: str, title: str, yaxis: str, display_names: dict, fmt: str = ",.0f") -> str:
    sorted_roots = sorted(final_roots, key=lambda r: final[r][metric], reverse=True)
    xs = [display_names.get(r, STATES[r]["name"]) for r in sorted_roots]
    ys = [final[r][metric] for r in sorted_roots]
    fig = go.Figure(go.Bar(
        x=xs, y=ys,
        marker_color=[PLOTLY_COLORS[i % len(PLOTLY_COLORS)] for i in range(len(xs))],
        hovertemplate="%{x}<br>%{y:" + fmt + "}<extra></extra>",
        text=[f"{y:{fmt}}" for y in ys], textposition="outside",
    ))
    fig.update_layout(
        title=title, yaxis_title=yaxis, template="plotly_white",
        height=420, margin=dict(l=40, r=20, t=60, b=80), showlegend=False,
    )
    return fig.to_html(full_html=False, include_plotlyjs=False, div_id=f"bar-{metric}")


def scatter_chart(final: dict, final_roots: list[str], display_names: dict) -> str:
    fig = go.Figure()
    for i, root in enumerate(final_roots):
        agg = final[root]
        fig.add_trace(go.Scatter(
            x=[agg["gdp_per_capita_usd"]],
            y=[agg["bachelors_or_higher_pct"]],
            mode="markers+text",
            name=display_names.get(root, STATES[root]["name"]),
            marker=dict(
                size=max(15, (agg["population"] / 3_000_000) ** 0.6 * 10),
                color=PLOTLY_COLORS[i % len(PLOTLY_COLORS)],
                line=dict(width=1, color="white"),
            ),
            text=[display_names.get(root, STATES[root]["name"])],
            textposition="top center",
            hovertemplate=(
                "<b>%{fullData.name}</b><br>"
                "GDP/capita: $%{x:,.0f}<br>"
                "Bachelor's+: %{y:.1f}%<br>"
                f"Population: {agg['population']:,}<extra></extra>"
            ),
        ))
    fig.update_layout(
        title="Final empires: GDP per capita vs. Bachelor's-or-higher % (bubble = population)",
        xaxis_title="GDP per capita (USD, 2023)",
        yaxis_title="Bachelor's degree or higher % (ACS 2022)",
        template="plotly_white", height=480, showlegend=False,
        margin=dict(l=60, r=20, t=60, b=50),
    )
    return fig.to_html(full_html=False, include_plotlyjs=False, div_id="chart-scatter")


# ---------- tree rendering -------------------------------------------------

def _subtree_members(node: str, children: dict) -> list[str]:
    members = [node]
    for _, ch in children.get(node, []):
        members.extend(_subtree_members(ch, children))
    return members


def _render_node(node: str, round_absorbed: int | None, children: dict, display_names: dict) -> str:
    """Recursively render one node in the merger tree (ul/li)."""
    own_pop = STATES[node]["population"]
    sub_members = _subtree_members(node, children)
    sub_pop = sum(STATES[m]["population"] for m in sub_members)
    label_state = STATES[node]["name"]
    badge = f'<span class="round-badge">#{round_absorbed}</span>' if round_absorbed is not None else '<span class="root-badge">root</span>'
    extra = ""
    if len(sub_members) > 1:
        extra = f' <span class="pop">(self {own_pop:,}; subtree {sub_pop:,} across {len(sub_members)} states)</span>'
    else:
        extra = f' <span class="pop">({own_pop:,})</span>'
    kids = children.get(node, [])
    inner = ""
    if kids:
        # render in round order
        inner = "<ul class='absorb-list'>" + "".join(
            _render_node(ch, rnd, children, display_names) for rnd, ch in kids
        ) + "</ul>"
    return f"<li>{badge} {label_state}{extra}{inner}</li>"


def render_tree(root: str, children: dict, display_names: dict) -> str:
    name = display_names.get(root, STATES[root]["name"])
    members = _subtree_members(root, children)
    pop = sum(STATES[m]["population"] for m in members)
    body = "<ul class='absorb-list root-list'>" + _render_node(root, None, children, display_names) + "</ul>"
    return f"""
    <div class="empire-card">
      <h3>{name}</h3>
      <p class="empire-meta">{len(members)} states · pop {pop:,}</p>
      {body}
    </div>
    """


def area_compare_chart(final: dict, final_roots: list[str], image_shares: dict[str, float], display_names: dict) -> str:
    """Side-by-side bars: model area share vs image-derived area share per empire.
    Highlights where the visual map differs from the whole-state attribution (i.e. splits).
    """
    total_land = sum(agg["land_area_sq_mi"] for agg in final.values())
    sorted_roots = sorted(final_roots, key=lambda r: final[r]["land_area_sq_mi"], reverse=True)
    xs = [display_names.get(r, STATES[r]["name"]) for r in sorted_roots]
    model_pct = [final[r]["land_area_sq_mi"] / total_land * 100 for r in sorted_roots]
    img_pct = [image_shares.get(r, 0.0) for r in sorted_roots]
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Whole-state model %", x=xs, y=model_pct, marker_color="#6cb1ff",
                         text=[f"{v:.1f}%" for v in model_pct], textposition="outside"))
    fig.add_trace(go.Bar(name="Image-derived %", x=xs, y=img_pct, marker_color="#ffae6c",
                         text=[f"{v:.1f}%" for v in img_pct], textposition="outside"))
    fig.update_layout(
        title="Area share per empire — whole-state attribution vs. round-42 image segmentation",
        yaxis_title="Share of map (%)",
        barmode="group", template="plotly_white", height=460,
        margin=dict(l=40, r=20, t=70, b=80),
        legend=dict(orientation="h", y=-0.22),
    )
    return fig.to_html(full_html=False, include_plotlyjs=False, div_id="chart-area-compare")


# ---------- main report ----------------------------------------------------

CSS = """
:root { color-scheme: dark; }
* { box-sizing: border-box; }
body { font: 16px/1.55 -apple-system, "Segoe UI", Roboto, sans-serif; margin: 0; background: #0f1115; color: #e6e8ec; }
header { padding: 48px 24px 24px; max-width: 1100px; margin: 0 auto; }
h1 { font-size: 2.4rem; margin: 0 0 8px; }
h2 { border-bottom: 1px solid #2a2f3a; padding-bottom: 8px; margin-top: 56px; }
h3 { margin: 0 0 4px; font-size: 1.15rem; }
.lede { color: #a9b0bd; font-size: 1.05rem; max-width: 700px; }
main { max-width: 1100px; margin: 0 auto; padding: 0 24px 80px; }
.empire-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }
.empire-card { background: #161a22; border: 1px solid #232a36; border-radius: 10px; padding: 16px; }
.empire-card .root-pop { font-size: .75rem; color: #7a8294; font-weight: normal; margin-left: 6px; }
.empire-meta { color: #8b93a7; font-size: .85rem; margin: 0 0 8px; }
.absorb-list { padding-left: 18px; margin: 0; font-size: .92rem; }
.absorb-list li { margin: 3px 0; }
.absorb-list ul { padding-left: 18px; margin: 3px 0; border-left: 2px solid #2a3142; }
.root-list { padding-left: 0; list-style: none; }
.root-list > li { font-weight: 600; }
.root-badge { background: #3a4a66; color: #d6e0f5; padding: 1px 6px; border-radius: 4px; font-size: .7rem; margin-right: 6px; text-transform: uppercase; letter-spacing: .03em; }
.round-badge { background: #2a3142; color: #c6cfe2; padding: 1px 6px; border-radius: 4px; font-size: .75rem; margin-right: 6px; font-variant-numeric: tabular-nums; }
.pop { color: #7a8294; font-size: .8rem; }
table { width: 100%; border-collapse: collapse; margin-top: 12px; font-size: .92rem; }
th, td { border-bottom: 1px solid #232a36; padding: 8px 6px; text-align: left; vertical-align: top; }
th { background: #1a1f29; font-weight: 600; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
.thumb { width: 120px; height: auto; border-radius: 4px; border: 1px solid #2a2f3a; display: block; }
.thumb-link { display: inline-block; }
.note { font-size: .8rem; color: #8b93a7; }
.source-pill { display: inline-block; font-size: .7rem; padding: 1px 6px; border-radius: 999px; background: #243044; color: #a8b6cf; margin-left: 6px; }
footer { color: #7a8294; font-size: .8rem; margin-top: 60px; border-top: 1px solid #232a36; padding-top: 16px; }
footer ul { padding-left: 18px; }
.chart-block { margin: 24px 0 48px; }
.metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(380px, 1fr)); gap: 16px; }
a { color: #6cb1ff; }
"""

HEADER = """
<header>
  <h1>NewMericaMeme</h1>
  <p class="lede">A data report on the r/geographymemes voting series <em>"Top comment deletes a US State"</em>.
    After 42 rounds and 41 absorptions, {n_empires} empires remain. This report shows the merger trees,
    cumulative population/GDP timelines, final rankings, a round-by-round ledger of every state that fell,
    and an image-based check on the splits the OP drew between empires.
  </p>
  <p class="note">Posts for rounds <strong>#2–#5, #13, #18, #24, #25, #29, #30, #31</strong> are no longer on Reddit (likely deleted — post #41 mentions re-uploads). Eliminations for those rounds were deduced from each surrounding post's top comment and OP's running removal lists; the three states with no signal at all (rounds 25, 30, 31) had to be Iowa, Georgia, and Nevada because those were the only states unaccounted for at the end.</p>
</header>
"""


def main() -> int:
    DOCS.mkdir(parents=True, exist_ok=True)
    DOCS_IMG.mkdir(parents=True, exist_ok=True)

    data = json.loads(ROUNDS_JSON.read_text(encoding="utf-8"))
    rounds = data["rounds"]
    display_names = data["empire_display_names"]
    model = build_model(rounds)

    final = model["final"]
    final_roots = sorted(final.keys(), key=lambda r: final[r]["population"], reverse=True)
    n_empires = len(final_roots)
    print(f"Surviving empires ({n_empires}): {', '.join(display_names.get(r, STATES[r]['name']) for r in final_roots)}")

    # copy round images into docs/assets/maps so the report is self-contained for GH Pages
    image_rel: dict[int, str] = {}
    for r in rounds:
        src = r.get("image_local")
        if not src:
            continue
        src_p = ROOT / src
        if not src_p.exists():
            continue
        dst = DOCS_IMG / src_p.name
        if not dst.exists() or dst.stat().st_size != src_p.stat().st_size:
            shutil.copy2(src_p, dst)
        image_rel[r["round"]] = f"assets/maps/{src_p.name}"

    # charts
    line_pop = line_chart(model["timeline"], final_roots, "population", "Cumulative empire population over rounds", "Population", display_names)
    line_gdp = line_chart(model["timeline"], final_roots, "gdp_million_usd", "Cumulative empire GDP over rounds", "GDP (millions USD)", display_names)
    line_land = line_chart(model["timeline"], final_roots, "land_area_sq_mi", "Cumulative empire land area over rounds", "Land area (sq mi)", display_names)
    bar_pop = bar_chart(final, final_roots, "population", "Final empire population", "Population", display_names)
    bar_gdp = bar_chart(final, final_roots, "gdp_million_usd", "Final empire GDP (USD millions)", "GDP", display_names)
    bar_land = bar_chart(final, final_roots, "land_area_sq_mi", "Final empire land area (sq mi)", "Land area", display_names)
    scatter = scatter_chart(final, final_roots, display_names)

    # image-derived area share (if image_analysis.py was run)
    area_compare_html = ""
    if IMG_AREA_JSON.exists():
        img_data = json.loads(IMG_AREA_JSON.read_text(encoding="utf-8"))
        area_compare_html = area_compare_chart(final, final_roots, img_data["shares_pct"], display_names)

    # merger trees
    trees_html = "".join(render_tree(r, model["children"], display_names) for r in final_roots)

    # round ledger table
    ledger_rows = []
    for r in rounds:
        img = image_rel.get(r["round"])
        thumb = f'<a class="thumb-link" href="{img}" target="_blank"><img class="thumb" src="{img}" alt="round {r["round"]} map"/></a>' if img else '<span class="note">no image</span>'
        elim = STATES[r["eliminated_state"]]["name"] if r["eliminated_state"] else "—"
        emp_root = r["empire_root"]
        emp_name = display_names.get(emp_root, STATES[emp_root]["name"] if emp_root else "—") if emp_root else "—"
        post_link = f'<a href="{r["post_url"]}" target="_blank">post</a>' if r["post_url"] else '<span class="note">missing</span>'
        top = r.get("top_comment_body") or ""
        if len(top) > 200:
            top = top[:200] + "…"
        ledger_rows.append(f"""
          <tr>
            <td class="num">#{r['round']:02d}</td>
            <td>{thumb}</td>
            <td><strong>{elim}</strong><br><span class="note">→ {emp_name}<span class="source-pill">{r['source']}</span></span></td>
            <td>{r['post_title'] or '<em>(post missing)</em>'} · {post_link}<br><span class="note">{(r['post_body'] or '')[:240]}</span></td>
            <td><span class="note">{top}</span></td>
          </tr>
        """)
    ledger = "<table><thead><tr><th>Round</th><th>Map</th><th>Eliminated → Empire</th><th>OP post</th><th>Top comment (drove next round)</th></tr></thead><tbody>" + "".join(ledger_rows) + "</tbody></table>"

    # final empires metrics table
    metric_rows = []
    for r in final_roots:
        agg = final[r]
        metric_rows.append(f"""
          <tr>
            <td><strong>{display_names.get(r, STATES[r]['name'])}</strong><br><span class="note">root: {STATES[r]['name']}</span></td>
            <td class="num">{len(agg['members'])}</td>
            <td class="num">{agg['population']:,}</td>
            <td class="num">{agg['land_area_sq_mi']:,}</td>
            <td class="num">{agg['water_pct']:.1f}%</td>
            <td class="num">${agg['gdp_million_usd']:,.0f}M</td>
            <td class="num">${agg['gdp_per_capita_usd']:,.0f}</td>
            <td class="num">${agg['median_household_income_usd']:,.0f}</td>
            <td class="num">{agg['bachelors_or_higher_pct']:.1f}%</td>
          </tr>
        """)
    final_table = (
        "<table><thead><tr><th>Empire</th><th class='num'>States</th><th class='num'>Population</th>"
        "<th class='num'>Land area (mi²)</th><th class='num'>Water %</th><th class='num'>GDP</th>"
        "<th class='num'>GDP / capita</th><th class='num'>Median HH income</th><th class='num'>Bachelor's+ %</th>"
        "</tr></thead><tbody>" + "".join(metric_rows) + "</tbody></table>"
    )

    # data vintages footer
    vint = "".join(f"<li><strong>{k}</strong>: {v}</li>" for k, v in VINTAGES.items())

    html = f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>NewMericaMeme — data report</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>{CSS}</style>
</head><body>
{HEADER.format(n_empires=n_empires)}
<main>

<h2>Surviving empires</h2>
<div class="empire-grid">{trees_html}</div>

<h2>Cumulative empire metrics over rounds</h2>
<p class="note">Each line is one of the {n_empires} surviving empires. The value at round R = sum of that empire's
current members at round R. As a state is absorbed into an empire, its metric joins that empire's line.</p>
<div class="chart-block">{line_pop}</div>
<div class="chart-block">{line_gdp}</div>
<div class="chart-block">{line_land}</div>

<h2>Final empire rankings</h2>
<div class="metric-grid">
  <div class="chart-block">{bar_pop}</div>
  <div class="chart-block">{bar_gdp}</div>
</div>
<div class="chart-block">{bar_land}</div>
<div class="chart-block">{scatter}</div>

<h2>Final empires — metrics table</h2>
{final_table}

<h2>Splits sanity check — model vs. image</h2>
<p class="note">The whole-state attribution above treats each absorbed state as one indivisible unit assigned to a single empire. In reality the meme's round-42 map shows states <strong>split</strong> between empires (e.g. California sliced between New Mexico, Hawaii, Cascadia, and Colorado; Texas mostly going to New Mexico). The bars below compare each empire's share of the colored map by whole-state model vs. by pixel-counting the round-42 image. Large gaps highlight where image-based attribution would refine the population/GDP estimates above.</p>
<p class="note"><em>Caveats:</em> Hawaii's apparent share is understated because Alaska's enormous real-world area is shown in a small inset; Wisconsin/Minnesota/Michigan all use very similar greens on this palette and may be partially misclassified between each other.</p>
<div class="chart-block">{area_compare_html or '<em class="note">(run <code>python image_analysis.py</code> first to populate data/image_area_round42.json)</em>'}</div>

<h2>Round-by-round ledger</h2>
<p class="note">Round 1 is the kickoff (no elimination). Sources: <code>body</code> = parsed from OP's post body; <code>prev-top</code> = top comment of the previous round; <code>list</code> = OP's running removal list (#20/#21); <code>deduced</code> = only unaccounted state remaining; <code>guess</code> = editorial guess (low confidence).</p>
{ledger}

<footer>
  <p><strong>Data vintages</strong></p>
  <ul>{vint}</ul>
  <p>Built locally; no live API calls. Source: <a href="https://github.com/milt0r/NewMericaMeme">milt0r/NewMericaMeme</a>. Map images © the original Reddit author.</p>
</footer>

</main>
</body></html>
"""
    OUT.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT}  ({OUT.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
