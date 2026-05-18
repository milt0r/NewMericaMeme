"""Build the multi-page static report under docs/.

Emits:
  docs/index.html    — Overview (current state + headline charts)
  docs/history.html  — Post-by-post timeline
  docs/pivots.html   — Sankey + chord + per-metric breakdowns + animated map
  docs/sources.html  — Data lineage + methodology
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import plotly.graph_objects as go

from layout import page
from model import (IMG_AREA_JSON, PLOTLY_COLORS, ROOT, aggregate, build_model,
                   load_rounds)
from state_data import METRIC_GROUPS, SOURCES, STATES

DOCS = ROOT / "docs"
DOCS_MAPS = DOCS / "assets" / "maps"


# ============================================================
# Shared helpers
# ============================================================

def display_name_of(root: str, names: dict) -> str:
    return names.get(root, STATES[root]["name"])


def copy_maps(rounds: list[dict]) -> dict[int, str]:
    DOCS_MAPS.mkdir(parents=True, exist_ok=True)
    out: dict[int, str] = {}
    for r in rounds:
        src = r.get("image_local")
        if not src:
            continue
        src_p = ROOT / src
        if not src_p.exists():
            continue
        dst = DOCS_MAPS / src_p.name
        if not dst.exists() or dst.stat().st_size != src_p.stat().st_size:
            shutil.copy2(src_p, dst)
        out[r["round"]] = f"assets/maps/{src_p.name}"
    return out


# ============================================================
# Charts (shared helpers)
# ============================================================

def line_chart(timeline, final_roots, metric, title, yaxis, names, div_id) -> str:
    fig = go.Figure()
    rounds = [s["round"] for s in timeline]
    for i, root in enumerate(final_roots):
        ys = [snap["empires"].get(root, {}).get(metric) for snap in timeline]
        fig.add_trace(go.Scatter(
            x=rounds, y=ys, mode="lines+markers",
            name=display_name_of(root, names),
            line=dict(color=PLOTLY_COLORS[i % len(PLOTLY_COLORS)], width=2),
            hovertemplate="Round %{x}<br>%{y:,.2f}<extra>%{fullData.name}</extra>",
        ))
    fig.update_layout(
        title=title, xaxis_title="Round", yaxis_title=yaxis,
        template="plotly_dark", paper_bgcolor="#161a22", plot_bgcolor="#161a22",
        height=460, margin=dict(l=50, r=20, t=60, b=40),
        legend=dict(orientation="h", y=-0.18),
    )
    return fig.to_html(full_html=False, include_plotlyjs=False, div_id=div_id)


def bar_chart(final, final_roots, metric, title, yaxis, names, fmt=",.0f", div_id="bar") -> str:
    sorted_roots = sorted(final_roots, key=lambda r: final[r][metric], reverse=True)
    xs = [display_name_of(r, names) for r in sorted_roots]
    ys = [final[r][metric] for r in sorted_roots]
    fig = go.Figure(go.Bar(
        x=xs, y=ys,
        marker_color=[PLOTLY_COLORS[i % len(PLOTLY_COLORS)] for i in range(len(xs))],
        text=[f"{y:{fmt}}" for y in ys], textposition="outside",
        hovertemplate="%{x}<br>%{y:" + fmt + "}<extra></extra>",
    ))
    fig.update_layout(
        title=title, yaxis_title=yaxis,
        template="plotly_dark", paper_bgcolor="#161a22", plot_bgcolor="#161a22",
        height=400, margin=dict(l=50, r=20, t=60, b=80), showlegend=False,
    )
    return fig.to_html(full_html=False, include_plotlyjs=False, div_id=div_id)


# ============================================================
# Merger tree rendering
# ============================================================

def _subtree_members(node, children):
    members = [node]
    for _, ch in children.get(node, []):
        members.extend(_subtree_members(ch, children))
    return members


def _render_node(node, round_absorbed, children, names) -> str:
    own_pop = STATES[node]["population"]
    sub_members = _subtree_members(node, children)
    sub_pop = sum(STATES[m]["population"] for m in sub_members)
    badge = (f'<span class="round-badge">#{round_absorbed}</span>'
             if round_absorbed is not None else '<span class="root-badge">root</span>')
    if len(sub_members) > 1:
        extra = f' <span class="pop">(self {own_pop:,}; subtree {sub_pop:,} across {len(sub_members)} states)</span>'
    else:
        extra = f' <span class="pop">({own_pop:,})</span>'
    kids = children.get(node, [])
    inner = ""
    if kids:
        inner = "<ul class='absorb-list'>" + "".join(
            _render_node(ch, rnd, children, names) for rnd, ch in kids
        ) + "</ul>"
    return f"<li>{badge} {STATES[node]['name']}{extra}{inner}</li>"


def render_tree(root, children, names) -> str:
    name = display_name_of(root, names)
    members = _subtree_members(root, children)
    pop = sum(STATES[m]["population"] for m in members)
    body = "<ul class='absorb-list root-list'>" + _render_node(root, None, children, names) + "</ul>"
    return f"""<div class="empire-card">
      <h3>{name}</h3>
      <p class="empire-meta">{len(members)} states · pop {pop:,}</p>
      {body}
    </div>"""


def image_slider(rounds, image_rel) -> str:
    """Round-image slider showing the actual map at each round.
    Far more accurate than the Plotly choropleth because it preserves the OP's
    mid-state splits exactly as drawn.
    """
    have = [r for r in rounds if image_rel.get(r["round"])]
    if not have:
        return '<em class="note">(no images available)</em>'
    slides = []
    for r in have:
        rnd = r["round"]
        img = image_rel[rnd]
        elim = (STATES[r["eliminated_state"]]["name"]
                if r["eliminated_state"] else "—")
        slides.append({
            "round": rnd,
            "img": img,
            "elim": elim,
            "title": r.get("post_title") or "",
        })
    slides_json = json.dumps(slides)
    return f"""
<div class="img-slider">
  <div class="img-slider-controls">
    <button class="is-btn" id="is-play">▶ Play</button>
    <button class="is-btn" id="is-pause" style="display:none;">⏸ Pause</button>
    <input type="range" id="is-range" min="0" max="{len(slides) - 1}" value="{len(slides) - 1}" step="1"/>
    <span class="is-label">Round <span id="is-round-label">{slides[-1]['round']}</span></span>
    <button class="is-btn" id="is-prev">◀</button>
    <button class="is-btn" id="is-next">▶</button>
    <label class="is-speed"><span>Speed</span>
      <select id="is-speed">
        <option value="1500">Slow</option>
        <option value="800" selected>Med</option>
        <option value="350">Fast</option>
      </select>
    </label>
  </div>
  <div class="img-slider-stage">
    <img id="is-img" src="{slides[-1]['img']}" alt="round {slides[-1]['round']} map"/>
  </div>
  <div class="img-slider-caption">
    <strong id="is-title">{slides[-1]['title']}</strong>
    <span class="note" id="is-elim">eliminated: {slides[-1]['elim']}</span>
  </div>
</div>
<script>
(() => {{
  const SLIDES = {slides_json};
  const img = document.getElementById('is-img');
  const range = document.getElementById('is-range');
  const lbl = document.getElementById('is-round-label');
  const title = document.getElementById('is-title');
  const elim = document.getElementById('is-elim');
  const playBtn = document.getElementById('is-play');
  const pauseBtn = document.getElementById('is-pause');
  const speedSel = document.getElementById('is-speed');
  let i = SLIDES.length - 1;
  let timer = null;
  function paint() {{
    const s = SLIDES[i];
    img.src = s.img;
    lbl.textContent = s.round;
    title.textContent = s.title;
    elim.textContent = 'eliminated: ' + s.elim;
    range.value = i;
  }}
  range.addEventListener('input', e => {{ i = +e.target.value; paint(); }});
  document.getElementById('is-prev').addEventListener('click', () => {{ i = (i - 1 + SLIDES.length) % SLIDES.length; paint(); }});
  document.getElementById('is-next').addEventListener('click', () => {{ i = (i + 1) % SLIDES.length; paint(); }});
  function play() {{
    playBtn.style.display = 'none';
    pauseBtn.style.display = '';
    timer = setInterval(() => {{
      i = (i + 1) % SLIDES.length;
      paint();
      if (i === SLIDES.length - 1) {{ stop(); }}
    }}, +speedSel.value);
  }}
  function stop() {{
    playBtn.style.display = '';
    pauseBtn.style.display = 'none';
    if (timer) {{ clearInterval(timer); timer = null; }}
  }}
  playBtn.addEventListener('click', () => {{
    if (i === SLIDES.length - 1) i = 0;
    play();
  }});
  pauseBtn.addEventListener('click', stop);
  speedSel.addEventListener('change', () => {{ if (timer) {{ stop(); play(); }} }});
}})();
</script>
"""


def state_journey_table(model, rounds, names) -> str:
    """For every state: USPS, name, eliminated-round (or 'survived'), top-comment-author-ish, final empire."""
    elim_round_of = {}
    for r in rounds:
        if r["eliminated_state"]:
            elim_round_of[r["eliminated_state"]] = r
    rows = []
    for usps in sorted(model["states_in_play"], key=lambda u: STATES[u]["name"]):
        st = STATES[usps]
        elim_event = elim_round_of.get(usps)
        if elim_event:
            elim_html = (f'<td class="num">#{elim_event["round"]:02d}</td>'
                         f'<td><a href="history.html#round-{elim_event["round"]}">post</a></td>')
            note = elim_event.get("note", "")
        else:
            elim_html = '<td class="num"><span class="root-badge">root</span></td><td>—</td>'
            note = "Survived as an empire root."
        final_root = model["final_root_of"][usps]
        emp = display_name_of(final_root, names)
        emp_self = " (self)" if final_root == usps else ""
        rows.append(f"""<tr>
          <td>{st['usps']}</td>
          <td>{st['name']}</td>
          <td class="num">{st['population']:,}</td>
          {elim_html}
          <td>{emp}{emp_self}</td>
          <td class="note">{note}</td>
        </tr>""")
    return ('<table id="journey"><thead><tr>'
            '<th>USPS</th><th>State</th><th class="num">2020 pop</th>'
            '<th class="num">Round eliminated</th><th>Source</th>'
            '<th>Final empire</th><th>Note</th>'
            '</tr></thead><tbody>' + "".join(rows) + "</tbody></table>")


def treemap_chart(model, names) -> str:
    final = model["final"]
    final_roots = sorted(final.keys(), key=lambda r: final[r]["population"], reverse=True)
    empire_color = {r: PLOTLY_COLORS[i % len(PLOTLY_COLORS)] for i, r in enumerate(final_roots)}

    labels = ["NewMerica"]
    parents = [""]
    values = [0]
    colors = ["#0f1115"]
    for root in final_roots:
        emp_name = display_name_of(root, names)
        labels.append(emp_name)
        parents.append("NewMerica")
        values.append(0)
        colors.append(empire_color[root])
        for m in sorted(final[root]["members"], key=lambda s: -STATES[s]["population"]):
            labels.append(STATES[m]["name"])
            parents.append(emp_name)
            values.append(STATES[m]["population"])
            colors.append(empire_color[root])

    fig = go.Figure(go.Treemap(
        labels=labels, parents=parents, values=values, marker=dict(colors=colors, line=dict(width=1, color="#0f1115")),
        branchvalues="total",
        textinfo="label+value+percent parent",
        hovertemplate="<b>%{label}</b><br>%{value:,}<extra></extra>",
    ))
    fig.update_layout(
        title="Treemap — population of each surviving empire, broken down by state",
        template="plotly_dark", paper_bgcolor="#161a22",
        height=620, margin=dict(l=10, r=10, t=60, b=10),
    )
    return fig.to_html(full_html=False, include_plotlyjs=False, div_id="treemap")


# ============================================================
# Page 1: Overview (index.html)
# ============================================================

def build_index(model, rounds, names, image_rel) -> str:
    final = model["final"]
    final_roots = sorted(final.keys(), key=lambda r: final[r]["population"], reverse=True)
    n = len(final_roots)
    trees = "".join(render_tree(r, model["children"], names) for r in final_roots)
    final_map = image_rel.get(42, "")

    line_pop = line_chart(model["timeline"], final_roots, "population",
                          "Empire population over rounds", "Population", names, "chart-pop")
    line_gdp = line_chart(model["timeline"], final_roots, "gdp_million_usd",
                          "Empire GDP over rounds", "GDP (millions USD)", names, "chart-gdp")
    line_land = line_chart(model["timeline"], final_roots, "land_area_sq_mi",
                           "Empire land area over rounds", "Land area (sq mi)", names, "chart-land")

    # final metrics table
    rows = []
    for r in final_roots:
        a = final[r]
        rows.append(f"""<tr>
          <td><strong>{display_name_of(r, names)}</strong><br><span class="note">root: {STATES[r]['name']}</span></td>
          <td class="num">{len(a['members'])}</td>
          <td class="num">{a['population']:,}</td>
          <td class="num">{a['land_area_sq_mi']:,}</td>
          <td class="num">${a['gdp_million_usd']:,.0f}M</td>
          <td class="num">${a['gdp_per_capita_usd']:,.0f}</td>
          <td class="num">{a['bachelors_or_higher_pct']:.1f}%</td>
        </tr>""")
    table = ("<table><thead><tr><th>Empire</th><th class='num'>States</th>"
             "<th class='num'>Population</th><th class='num'>Land (mi²)</th>"
             "<th class='num'>GDP</th><th class='num'>GDP/capita</th><th class='num'>Bachelor's+</th>"
             "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>")

    final_map_html = (f'<img src="{final_map}" alt="round 42 map" '
                      'style="width:100%;max-width:900px;border-radius:8px;border:1px solid #2a2f3a;display:block;margin:16px auto;"/>'
                      if final_map else "")

    # Sample-points overlay (verification image)
    overlay_path = DOCS_MAPS / "round_42_overlay.png"
    overlay_html = ""
    if overlay_path.exists():
        overlay_html = """
<h2>Sample-point overlay — image-based ground truth</h2>
<p class="note">Each red dot marks the pixel where we sampled the round-42 image to determine that state's final empire (via nearest empire-color anchor). This is the "image ground truth" that drives the merger-tree composition below: each state is assigned to the empire whose color it visually sits in on the OP's final map.</p>
<img src="assets/maps/round_42_overlay.png" alt="state sample-point overlay" style="width:100%;max-width:1000px;border-radius:8px;border:1px solid #2a2f3a;display:block;margin:16px auto;"/>
"""

    header = f"""
    <h1>NewMericaMeme</h1>
    <p class="lede">A data report on the r/geographymemes voting series <em>"Top comment deletes a US State"</em>.
      After 42 rounds and 41 absorptions, <strong>{n} empires</strong> remain — built from 50 states.</p>
    <details class="rules"><summary>How the game worked</summary>
      <p>Each round, the OP posted a US map showing the current empires. Whoever's comment got the most upvotes
      chose a state to delete — that state was absorbed into one or more neighboring empires (with the OP picking
      how to slice it if multiple empires were named). After 42 rounds, every state but the surviving 9 had been
      absorbed into one of those 9 empires. Use the nav above to dig into the round-by-round history, multi-metric
      pivots, and source data.</p>
    </details>
    """

    body = f"""
{final_map_html}
{overlay_html}

<h2>Surviving empires — final ranking</h2>
{table}

<h2>Merger trees</h2>
<p class="note">Each tree shows how a surviving empire grew. Children are listed in absorption order with round number.</p>
<div class="empire-grid">{trees}</div>

<h2>Empire metrics over rounds</h2>
<div class="chart-block">{line_pop}</div>
<div class="chart-block">{line_gdp}</div>
<div class="chart-block">{line_land}</div>

<h2>What's next</h2>
<div class="next-cards">
  <div class="next-card"><h3>📜 History</h3><p>Every round, post by post — map, OP's commentary, and the top comment that drove the next vote.</p><a href="history.html">Go to History →</a></div>
  <div class="next-card"><h3>📊 Pivots</h3><p>Sankey of how 50 states funneled into 9 empires, plus per-empire deep dives across economy, education, health, energy, religion, and demographics.</p><a href="pivots.html">Go to Pivots →</a></div>
  <div class="next-card"><h3>📚 Sources</h3><p>Every metric's source, vintage, and methodology notes.</p><a href="sources.html">Go to Sources →</a></div>
</div>
"""
    return page("index.html", "Overview", header, body)


# ============================================================
# Page 2: History (history.html)
# ============================================================

def build_history(model, rounds, names, image_rel) -> str:
    jump = "".join(f'<a href="#round-{r["round"]}">#{r["round"]}</a>' for r in rounds)
    items = []
    for i, r in enumerate(rounds):
        rnd = r["round"]
        img = image_rel.get(rnd)
        img_html = (f'<a href="{img}" target="_blank"><img class="tl-img" src="{img}" alt="Round {rnd} map"/></a>'
                    if img else '<div class="note">(no image)</div>')

        elim_html = ""
        if r["eliminated_state"]:
            elim_state = STATES[r["eliminated_state"]]["name"]
            emp_root = r["empire_root"]
            emp_name = display_name_of(emp_root, names) if emp_root else "—"
            elim_html = (f'<div class="tl-elim">Eliminated: <strong>{elim_state}</strong>'
                         f'<span class="arrow">→</span><span class="empire">{emp_name}</span>'
                         f'<span class="source-pill">{r["source"]}</span></div>')
        else:
            elim_html = '<div class="tl-elim"><em>Kickoff — initial map, no elimination.</em></div>'

        body_text = (r.get("post_body") or "").strip()
        body_quote = f'<blockquote>{body_text}</blockquote>' if body_text else ""

        # Top comment drives the NEXT round
        next_round_label = rounds[i + 1]["round"] if i + 1 < len(rounds) else None
        top = r.get("top_comment_body") or ""
        top_html = ""
        if top and next_round_label:
            top_short = top[:400] + ("…" if len(top) > 400 else "")
            top_html = (f'<div class="tl-top"><span class="lbl">Top comment (drove round #{next_round_label})</span>'
                        f'{top_short}</div>')

        date = ""
        if r.get("created_utc"):
            date = datetime.fromtimestamp(r["created_utc"], tz=timezone.utc).strftime("%Y-%m-%d")
        post_url = r.get("post_url")
        post_link = f' · <a href="{post_url}" target="_blank">reddit post</a>' if post_url else ""

        items.append(f"""
<article class="tl-item" id="round-{rnd}">
  <header>
    <span class="rnd-num">#{rnd:02d}</span>
    <h3>{r.get("post_title") or "(post missing)"}</h3>
    <span class="meta">{date}{post_link}</span>
  </header>
  <div class="tl-grid">
    <div>{img_html}</div>
    <div class="tl-body">
      {elim_html}
      {body_quote}
      {top_html}
      <p class="note" style="margin-top:8px;">{r.get("note", "")}</p>
    </div>
  </div>
</article>""")

    header = """
    <h1>History</h1>
    <p class="lede">All 42 rounds in order. Each entry shows the round's map, the OP's caption, the elimination event,
    and the top comment that became the prompt for the next round.</p>
    """

    body = (f'<div class="jump-strip">{jump}</div>'
            f'<div class="timeline">{"".join(items)}</div>')

    return page("history.html", "History", header, body, include_plotly=False)


# ============================================================
# Page 3: Pivots (pivots.html)
# ============================================================

def sankey_chart(model, names) -> str:
    """50 original states -> 9 final empires."""
    final = model["final"]
    final_roots = sorted(final.keys(), key=lambda r: final[r]["population"], reverse=True)
    final_root_of = model["final_root_of"]
    states = sorted(model["states_in_play"], key=lambda s: STATES[s]["name"])

    state_nodes = [STATES[s]["name"] for s in states]
    empire_nodes = [display_name_of(r, names) for r in final_roots]
    nodes = state_nodes + empire_nodes
    # color empires distinctly; states inherit destination color
    empire_color = {r: PLOTLY_COLORS[i % len(PLOTLY_COLORS)] for i, r in enumerate(final_roots)}
    node_colors = [empire_color[final_root_of[s]] for s in states] + [empire_color[r] for r in final_roots]

    srcs, tgts, vals, link_colors = [], [], [], []
    for i, s in enumerate(states):
        dest_root = final_root_of[s]
        srcs.append(i)
        tgts.append(len(states) + final_roots.index(dest_root))
        vals.append(STATES[s]["population"])
        # translucent destination color
        c = empire_color[dest_root]
        link_colors.append(_hex_to_rgba(c, 0.35))

    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(label=nodes, color=node_colors, pad=10, thickness=14,
                  line=dict(color="rgba(0,0,0,0)", width=0)),
        link=dict(source=srcs, target=tgts, value=vals, color=link_colors,
                  hovertemplate="%{source.label} → %{target.label}<br>pop %{value:,}<extra></extra>"),
    ))
    fig.update_layout(
        title="Sankey: 50 original states → 9 surviving empires (flow width = population)",
        font=dict(color="#e6e8ec", size=11),
        template="plotly_dark", paper_bgcolor="#161a22",
        height=900, margin=dict(l=20, r=20, t=60, b=20),
    )
    return fig.to_html(full_html=False, include_plotlyjs=False, div_id="sankey")


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def chord_like_chart(model, names) -> str:
    """A 'who absorbed whom' bubble-arc chart isn't trivial in Plotly; use a stacked-bar
    by absorbing-empire showing each round's transfer instead — same information density."""
    final = model["final"]
    final_roots = sorted(final.keys(), key=lambda r: final[r]["population"], reverse=True)
    empire_color = {r: PLOTLY_COLORS[i % len(PLOTLY_COLORS)] for i, r in enumerate(final_roots)}
    final_root_of = model["final_root_of"]

    # For each round event, where did the eliminated state's *final empire* end up?
    fig = go.Figure()
    rounds_seen = []
    for ev in model["events"]:
        if not ev["eliminated"]:
            continue
        elim = ev["eliminated"]
        final_dest = final_root_of[elim]
        round_num = ev["round"]
        rounds_seen.append(round_num)
        fig.add_trace(go.Bar(
            x=[round_num], y=[STATES[elim]["population"]],
            name=STATES[elim]["name"],
            marker_color=empire_color.get(final_dest, "#888"),
            showlegend=False,
            hovertemplate=f"<b>{STATES[elim]['name']}</b><br>Round %{{x}}<br>Pop %{{y:,}}<br>Eventually in: {display_name_of(final_dest, names)}<extra></extra>",
        ))
    fig.update_layout(
        title="Population eliminated per round (bar color = final empire that the eliminated state ended up in)",
        barmode="stack", template="plotly_dark", paper_bgcolor="#161a22", plot_bgcolor="#161a22",
        xaxis=dict(title="Round", dtick=1), yaxis=dict(title="Population eliminated"),
        height=420, margin=dict(l=50, r=20, t=60, b=40), showlegend=False,
    )
    # legend swatches as an HTML strip below
    swatches = "".join(
        f'<span style="display:inline-flex;align-items:center;gap:6px;margin:0 12px 6px 0;">'
        f'<span style="width:14px;height:14px;border-radius:3px;background:{empire_color[r]};display:inline-block;"></span>'
        f'<span style="font-size:.85rem;">{display_name_of(r, names)}</span></span>'
        for r in final_roots
    )
    return (fig.to_html(full_html=False, include_plotlyjs=False, div_id="chord")
            + f'<div class="note" style="margin-top:6px;">{swatches}</div>')


def animated_map_chart(model, names) -> str:
    """Plotly choropleth animation: per round, color each state by its current empire."""
    final_roots = sorted(model["final"].keys(),
                         key=lambda r: model["final"][r]["population"], reverse=True)
    empire_color = {r: PLOTLY_COLORS[i % len(PLOTLY_COLORS)] for i, r in enumerate(final_roots)}
    states_in_play = model["states_in_play"]

    # Build per-round ownership snapshot
    frames = []
    # We need to re-derive ownership from timeline snapshots
    for snap in model["timeline"]:
        owner_by_state = {}
        for root, agg in snap["empires"].items():
            for m in agg["members"]:
                owner_by_state[m] = root
        locations = []
        colors = []
        texts = []
        for s in states_in_play:
            owner = owner_by_state.get(s, s)
            locations.append(s)
            colors.append(empire_color.get(owner, "#444"))
            texts.append(f"{STATES[s]['name']}<br>Empire: {display_name_of(owner, names)}")
        frames.append(go.Frame(
            data=[go.Choropleth(
                locations=locations, locationmode="USA-states",
                z=[final_roots.index(owner_by_state.get(s, s)) if owner_by_state.get(s, s) in final_roots else -1 for s in states_in_play],
                colorscale=[[i / max(1, len(final_roots) - 1), empire_color[r]] for i, r in enumerate(final_roots)],
                showscale=False, text=texts, hovertemplate="%{text}<extra></extra>",
                marker_line_color="#0f1115", marker_line_width=0.5,
            )],
            name=str(snap["round"]),
        ))

    init = frames[-1].data[0]
    fig = go.Figure(data=[init], frames=frames)
    fig.update_layout(
        title="Round-by-round empire ownership (use slider or Play)",
        geo=dict(scope="usa", bgcolor="#161a22", lakecolor="#0f1115",
                 landcolor="#1a1f29", showlakes=True),
        template="plotly_dark", paper_bgcolor="#161a22",
        height=560, margin=dict(l=10, r=10, t=60, b=10),
        updatemenus=[dict(type="buttons", showactive=False, y=0, x=0.08, xanchor="right", yanchor="bottom",
                          buttons=[
                              dict(label="▶ Play", method="animate",
                                   args=[None, dict(frame=dict(duration=500, redraw=True),
                                                    fromcurrent=True, transition=dict(duration=0))]),
                              dict(label="⏸ Pause", method="animate",
                                   args=[[None], dict(frame=dict(duration=0, redraw=False),
                                                      mode="immediate", transition=dict(duration=0))]),
                          ])],
        sliders=[dict(active=len(frames) - 1, currentvalue=dict(prefix="Round: "),
                      pad=dict(t=40),
                      steps=[dict(method="animate",
                                  args=[[f.name],
                                        dict(mode="immediate",
                                             frame=dict(duration=0, redraw=True),
                                             transition=dict(duration=0))],
                                  label=f.name)
                             for f in frames])],
    )
    return fig.to_html(full_html=False, include_plotlyjs=False, div_id="animap")


def build_pivots(model, rounds, names, image_rel) -> str:
    final = model["final"]
    final_roots = sorted(final.keys(), key=lambda r: final[r]["population"], reverse=True)

    sankey = sankey_chart(model, names)
    chord = chord_like_chart(model, names)
    animap = animated_map_chart(model, names)
    slider = image_slider(rounds, image_rel)
    treemap = treemap_chart(model, names)
    journey = state_journey_table(model, rounds, names)

    # Per-metric tabs
    tab_btns = []
    panels = []
    for i, (group_name, metrics) in enumerate(METRIC_GROUPS.items()):
        cls = " active" if i == 0 else ""
        tab_btns.append(f'<button class="tab-btn{cls}" data-group="g{i}">{group_name}</button>')
        # build a bar chart per metric in this group
        charts = []
        for field, label, agg_kind, prefix, suffix in metrics:
            fmt = ",.0f"
            if "%" in suffix or field.endswith("_pct"):
                fmt = ",.1f"
            elif field.endswith("_years") or field == "median_age":
                fmt = ",.1f"
            sorted_roots = sorted(final_roots, key=lambda r: final[r].get(field, 0), reverse=True)
            xs = [display_name_of(r, names) for r in sorted_roots]
            ys = [final[r].get(field, 0) for r in sorted_roots]
            text = [f"{prefix}{y:{fmt}}{suffix}" for y in ys]
            fig = go.Figure(go.Bar(
                x=xs, y=ys,
                marker_color=[PLOTLY_COLORS[j % len(PLOTLY_COLORS)] for j in range(len(xs))],
                text=text, textposition="outside",
                hovertemplate="%{x}<br>" + prefix + "%{y:" + fmt + "}" + suffix + "<extra></extra>",
            ))
            fig.update_layout(
                title=f"{label} — final empires ({agg_kind})",
                template="plotly_dark", paper_bgcolor="#161a22", plot_bgcolor="#161a22",
                height=360, margin=dict(l=40, r=20, t=50, b=80), showlegend=False,
            )
            charts.append(fig.to_html(full_html=False, include_plotlyjs=False, div_id=f"bar-{field}"))
        panel_cls = " active" if i == 0 else ""
        panels.append(f'<div class="metric-panel{panel_cls}" id="g{i}">'
                      f'<div class="metric-grid">'
                      + "".join(f'<div class="chart-block">{c}</div>' for c in charts)
                      + "</div></div>")

    tabs_html = ('<div class="metric-tabs">' + "".join(tab_btns) + "</div>"
                 + "".join(panels))

    # Image-vs-model area share chart
    area_html = ""
    if IMG_AREA_JSON.exists():
        img_data = json.loads(IMG_AREA_JSON.read_text(encoding="utf-8"))
        total_land = sum(a["land_area_sq_mi"] for a in final.values())
        sorted_roots = sorted(final_roots, key=lambda r: final[r]["land_area_sq_mi"], reverse=True)
        xs = [display_name_of(r, names) for r in sorted_roots]
        model_pct = [final[r]["land_area_sq_mi"] / total_land * 100 for r in sorted_roots]
        img_pct = [img_data["shares_pct"].get(r, 0) for r in sorted_roots]
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Whole-state model %", x=xs, y=model_pct, marker_color="#6cb1ff",
                             text=[f"{v:.1f}%" for v in model_pct], textposition="outside"))
        fig.add_trace(go.Bar(name="Image-derived %", x=xs, y=img_pct, marker_color="#ffae6c",
                             text=[f"{v:.1f}%" for v in img_pct], textposition="outside"))
        fig.update_layout(
            title="Map area share: whole-state model vs. round-42 image segmentation",
            barmode="group", template="plotly_dark", paper_bgcolor="#161a22", plot_bgcolor="#161a22",
            height=460, margin=dict(l=50, r=20, t=60, b=80),
            legend=dict(orientation="h", y=-0.22),
        )
        area_html = fig.to_html(full_html=False, include_plotlyjs=False, div_id="area-compare")

    header = """
    <h1>Pivots</h1>
    <p class="lede">Multiple lenses on the same data. The Sankey shows where every state ended up;
    the round-by-round bar shows when each elimination happened and where the population eventually landed;
    the animated map shows empire boundaries growing over time; and the metric tabs slice the final empires by
    economy, education, health, energy, religion, demographics, and geography.</p>
    """

    body = f"""
<h2>Map slider — actual round maps</h2>
<p class="note">The OP's actual map at each round. Mid-state splits the OP drew (e.g., Hawaii eating part of SoCal, Cascadia extending into Jefferson) are preserved here exactly, unlike the schematic choropleth below.</p>
<div class="chart-block">{slider}</div>

<h2>Sankey — 50 states → 9 empires</h2>
<div class="chart-block">{sankey}</div>

<h2>Treemap — empires by population, broken down by state</h2>
<div class="chart-block">{treemap}</div>

<h2>Round-by-round transfers</h2>
<p class="note">Each bar is one round's eliminated state; bar height = its population; color = the final empire that the eliminated state eventually ended up in (after possible chained absorptions).</p>
<div class="chart-block">{chord}</div>

<h2>Animated choropleth — whole-state model</h2>
<p class="note">Schematic version: each whole state is colored by its current empire. Splits the OP drew mid-state are <em>not</em> shown here (use the actual-map slider above for that fidelity).</p>
<div class="chart-block">{animap}</div>

<h2>Per-metric breakdowns</h2>
<p class="note">Sums where appropriate (population, GDP, land area), otherwise population-weighted means. Click a category.</p>
{tabs_html}

<h2>State journey table</h2>
<p class="note">Type to filter by state name, USPS code, or final empire.</p>
<input type="text" id="journey-filter" placeholder="Filter states (e.g. 'tex', 'NM', 'cascadia')..." class="filter-input"/>
{journey}

<h2>Splits sanity check — model vs. image</h2>
<p class="note">The whole-state model assigns each absorbed state to one empire. In reality the round-42 map shows states <strong>split</strong> between empires (e.g., California sliced between New Mexico, Hawaii, Cascadia, and Colorado). Below: each empire's share of the colored map by model vs. by pixel-counting the actual round-42 image.</p>
<div class="chart-block">{area_html or '<em class="note">(run image_analysis.py first)</em>'}</div>

<script>
document.querySelectorAll('.tab-btn').forEach(btn => {{
  btn.addEventListener('click', () => {{
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.metric-panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(btn.dataset.group).classList.add('active');
    window.dispatchEvent(new Event('resize'));
  }});
}});

// Journey table filter
(() => {{
  const inp = document.getElementById('journey-filter');
  const table = document.getElementById('journey');
  if (!inp || !table) return;
  inp.addEventListener('input', () => {{
    const q = inp.value.trim().toLowerCase();
    table.querySelectorAll('tbody tr').forEach(tr => {{
      tr.style.display = !q || tr.textContent.toLowerCase().includes(q) ? '' : 'none';
    }});
  }});
}})();
</script>
"""
    return page("pivots.html", "Pivots", header, body)


# ============================================================
# Page 4: Sources (sources.html)
# ============================================================

def build_sources() -> str:
    rows = []
    for field, (src, url) in SOURCES.items():
        rows.append(f'<tr><td>{field}</td><td>{src}</td><td><a href="{url}" target="_blank">link</a></td></tr>')
    src_table = ('<table class="src-table"><thead><tr><th>Field</th><th>Source</th><th>URL</th></tr></thead><tbody>'
                 + "".join(rows) + "</tbody></table>")

    header = """
    <h1>Sources & methodology</h1>
    <p class="lede">Every per-state metric in this report is hard-coded from an authoritative public source.
    No live API calls are made when building the site. Below: the source + vintage for each field, and notes on
    the methodology behind the merger model.</p>
    """

    body = f"""
<h2>Per-field data sources</h2>
{src_table}

<h2>Methodology</h2>
<h3>Round ledger</h3>
<p>All 42 series posts are cached locally under <code>data/cache/posts/</code> with their map images under <code>data/images/</code>. For each round, the OP's post body names the eliminated state and (usually) the absorbing empires. Where multiple empires share a state, we pick the dominant absorber; the splits sanity-check chart on the Pivots page surfaces these approximations.</p>

<h3>Merger forest</h3>
<p>We use a union-find over the 50 states (DC excluded — it is not on the meme map). Each round, the eliminated state's current empire root is pointed at the absorbing empire's current root, producing a tree. The resulting forest contains exactly 9 surviving roots, matching the on-map "REMAINING: 9" label on round-42's image.</p>

<h3>Aggregation rules</h3>
<ul>
  <li><strong>Sums:</strong> population, land area, water area, GDP.</li>
  <li><strong>Population-weighted means:</strong> income, education %s, unemployment, poverty, life expectancy, obesity, renewable %, religion %s, demographic %s, median age.</li>
  <li><strong>Derived:</strong> GDP per capita = total GDP ÷ total population; water % = water area ÷ total area.</li>
</ul>

<h3>Image-derived area share</h3>
<p>The round-42 map is color-segmented in <code>image_analysis.py</code>: pixels are classified to the nearest of nine hand-tuned empire anchor colors (after masking near-white background). Resulting per-empire pixel shares are saved to <code>data/image_area_round42.json</code> and compared against the whole-state model on the Pivots page. Caveats: Wisconsin/Minnesota/Michigan use very similar greens and may be partially misclassified between each other; Hawaii's apparent share is understated because Alaska is rendered as a small inset on the OP's map.</p>

<h3>Reproducing this report</h3>
<pre style="background:#1a1f29;border:1px solid #232a36;border-radius:6px;padding:14px;overflow:auto;">python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1   # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python fetch.py          # populates data/cache/ and data/images/ (set USER in fetch.py first)
python parse.py          # builds data/rounds.json from cache + overrides
python image_analysis.py # produces data/image_area_round42.json
python build_report.py   # writes docs/*.html
</pre>
"""
    return page("sources.html", "Sources", header, body, include_plotly=False)


# ============================================================
# Main
# ============================================================

def main() -> int:
    DOCS.mkdir(parents=True, exist_ok=True)
    data = load_rounds()
    rounds = data["rounds"]
    names = data["empire_display_names"]
    model = build_model(rounds)
    image_rel = copy_maps(rounds)

    pages = {
        "index.html":   build_index(model, rounds, names, image_rel),
        "history.html": build_history(model, rounds, names, image_rel),
        "pivots.html":  build_pivots(model, rounds, names, image_rel),
        "sources.html": build_sources(),
    }
    for name, html in pages.items():
        out = DOCS / name
        out.write_text(html, encoding="utf-8")
        print(f"  wrote {out}  ({out.stat().st_size:,} bytes)")

    # Touch .nojekyll so GH Pages serves as-is
    (DOCS / ".nojekyll").touch()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
