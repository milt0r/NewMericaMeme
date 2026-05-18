"""Shared model + aggregation: load rounds.json, replay merger forest, compute aggregates."""
from __future__ import annotations

import json
from pathlib import Path

from state_data import STATES, METRIC_GROUPS

ROOT = Path(__file__).parent
ROUNDS_JSON = ROOT / "data" / "rounds.json"
IMG_AREA_JSON = ROOT / "data" / "image_area_round42.json"

PLOTLY_COLORS = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#bcbd22", "#17becf", "#7f7f7f",
]


def load_rounds() -> dict:
    return json.loads(ROUNDS_JSON.read_text(encoding="utf-8"))


def aggregate(members: list[str]) -> dict:
    """Sum + weighted-mean aggregation over an empire's member states."""
    pop = sum(STATES[m]["population"] for m in members)
    land = sum(STATES[m]["land_area_sq_mi"] for m in members)
    water = sum(STATES[m]["water_area_sq_mi"] for m in members)
    total = land + water
    out = {
        "members": members,
        "population": pop,
        "land_area_sq_mi": land,
        "water_area_sq_mi": water,
        "total_area_sq_mi": total,
        "water_pct": (water / total * 100.0) if total else 0,
    }
    # GDP — sum
    out["gdp_million_usd"] = sum(STATES[m]["gdp_million_usd"] for m in members)
    out["gdp_per_capita_usd"] = (out["gdp_million_usd"] * 1_000_000 / pop) if pop else 0
    # All other numeric fields — population-weighted means
    pop_weighted_fields = [
        "median_household_income_usd", "unemployment_pct", "poverty_pct",
        "hs_or_higher_pct", "bachelors_or_higher_pct", "advanced_degree_pct",
        "adult_obesity_pct", "life_expectancy_years", "renewable_electricity_pct",
        "christian_pct", "unaffiliated_pct",
        "median_age", "foreign_born_pct",
        "white_alone_pct", "black_alone_pct", "hispanic_pct", "asian_alone_pct",
    ]
    if pop:
        for f in pop_weighted_fields:
            out[f] = sum(STATES[m][f] * STATES[m]["population"] for m in members) / pop
    else:
        for f in pop_weighted_fields:
            out[f] = 0
    return out


def build_model(rounds: list[dict]) -> dict:
    """Replay rounds; return merger forest + per-round per-empire aggregates.
    DC is excluded — the meme map only shows the 50 states.
    """
    states_in_play = [u for u in STATES if u != "DC"]
    ownership: dict[str, str] = {u: u for u in states_in_play}

    def resolve(u: str) -> str:
        seen = []
        while ownership[u] != u:
            seen.append(u)
            u = ownership[u]
        for s in seen:
            ownership[s] = u
        return u

    # children[parent] = ordered list of (round, child_root) when child_root joined parent
    children: dict[str, list[tuple[int, str]]] = {u: [] for u in states_in_play}
    # event log: per round, the state-level absorption that actually occurred
    events: list[dict] = []
    timeline: list[dict] = []

    for r in rounds:
        rnd = r["round"]
        elim = r["eliminated_state"]
        emp = r["empire_root"]
        event = {"round": rnd, "eliminated": elim, "absorbed_into_root_at_event": None,
                 "final_root_of_eliminated": None}
        if elim and emp:
            elim_root = resolve(elim)
            emp_root = resolve(emp)
            event["absorbed_into_root_at_event"] = emp_root
            if elim_root != emp_root:
                children[emp_root].append((rnd, elim_root))
                ownership[elim_root] = emp_root
        events.append(event)
        # snapshot
        empires: dict[str, list[str]] = {}
        for usps in states_in_play:
            empires.setdefault(resolve(usps), []).append(usps)
        snap = {"round": rnd, "empires": {}}
        for root, members in empires.items():
            snap["empires"][root] = aggregate(members)
        timeline.append(snap)

    # Final-root for each original state (where each state ended up)
    final_root_of: dict[str, str] = {u: resolve(u) for u in states_in_play}
    # Update events to record final root of the eliminated state
    for e in events:
        if e["eliminated"]:
            e["final_root_of_eliminated"] = final_root_of[e["eliminated"]]

    return {
        "ownership": ownership,
        "children": children,
        "events": events,
        "timeline": timeline,
        "final": timeline[-1]["empires"],
        "final_root_of": final_root_of,
        "states_in_play": states_in_play,
    }
