"""Per-state metrics for 50 states + DC.

Values hard-coded from authoritative US government sources so this works offline
and is reproducible. Each field's vintage is recorded in `VINTAGES` for footnotes.

Fields per record (keys are USPS abbreviations):
  name                          full state name
  population                    Population (2020 Decennial Census)
  land_area_sq_mi               Land area in square miles (Census Gazetteer 2020)
  water_area_sq_mi              Water area in square miles (Census Gazetteer 2020)
  gdp_million_usd               Nominal GDP, current dollars (BEA 2023)
  median_household_income_usd   Median household income (ACS 2022 5-year)
  bachelors_or_higher_pct       % of adults 25+ with bachelor's degree or higher (ACS 2022 5-year)

Derived fields are computed in code (gdp_per_capita_usd, water_pct, total_area).
"""
from __future__ import annotations

VINTAGES = {
    "population": "US Census 2020 (Decennial)",
    "land_area_sq_mi": "US Census Gazetteer 2020",
    "water_area_sq_mi": "US Census Gazetteer 2020",
    "gdp_million_usd": "US BEA, current-dollar GDP 2023",
    "median_household_income_usd": "US Census ACS 2022 5-year",
    "bachelors_or_higher_pct": "US Census ACS 2022 5-year",
}

# Each row: usps, name, population, land_sq_mi, water_sq_mi, gdp_million_2023, median_hh_inc, bachelors_pct
_RAW = [
    ("AL", "Alabama",       5024279,  50645,  1775,  302224, 59674, 27.7),
    ("AK", "Alaska",         733391, 570641, 91316,   69570, 86631, 31.4),
    ("AZ", "Arizona",       7151502, 113594,   396,  537969, 72581, 32.3),
    ("AR", "Arkansas",      3011524,  52035,  1143,  175574, 56335, 25.0),
    ("CA", "California",   39538223, 155779,  7916, 3897614, 91551, 36.5),
    ("CO", "Colorado",      5773714, 103642,   376,  528090, 87598, 45.7),
    ("CT", "Connecticut",   3605944,   4842,   698,  342375, 90213, 41.0),
    ("DE", "Delaware",       989948,   1949,   536,   91118, 79325, 35.0),
    ("DC", "District of Columbia", 689545, 61,  7,   178391,101027, 64.7),
    ("FL", "Florida",      21538187,  53624, 12133, 1647739, 67917, 32.3),
    ("GA", "Georgia",      10711908,  57513,  1912,  819532, 71355, 34.1),
    ("HI", "Hawaii",        1455271,   6423,  4509,  104077, 94814, 35.4),
    ("ID", "Idaho",         1839106,  82643,   926,  124903, 70214, 30.6),
    ("IL", "Illinois",     12812508,  55519,  2441, 1132513, 78433, 37.4),
    ("IN", "Indiana",       6785528,  35826,   593,  490608, 67173, 28.6),
    ("IA", "Iowa",          3190369,  55857,   415,  256715, 70571, 30.4),
    ("KS", "Kansas",        2937880,  81759,   520,  237522, 69747, 35.4),
    ("KY", "Kentucky",      4505836,  39486,   921,  280030, 60183, 26.5),
    ("LA", "Louisiana",     4657757,  43204,  8283,  306334, 57852, 25.9),
    ("ME", "Maine",         1362359,  30843,  4537,   85925, 71139, 34.4),
    ("MD", "Maryland",      6177224,   9707,  2633,  522017, 98461, 42.7),
    ("MA", "Massachusetts", 7029917,   7800,  2715,  734222,101341, 47.8),
    ("MI", "Michigan",      10077331, 56539, 40175,  679436, 71149, 32.0),
    ("MN", "Minnesota",     5706494,  79627,  7309,  494569, 84313, 39.1),
    ("MS", "Mississippi",   2961279,  46923,  1521,  156470, 52985, 24.0),
    ("MO", "Missouri",      6154913,  68742,   811,  423689, 65920, 31.4),
    ("MT", "Montana",       1084225, 145546,  1494,   77793, 70804, 35.2),
    ("NE", "Nebraska",      1961504,  76824,   481,  175111, 71722, 34.5),
    ("NV", "Nevada",        3104614, 109781,   790,  244829, 76364, 27.4),
    ("NH", "New Hampshire", 1377529,   8953,   382,  120307, 90845, 40.5),
    ("NJ", "New Jersey",    9288994,   7354,  1304,  836132, 97126, 43.3),
    ("NM", "New Mexico",    2117522, 121298,   292,  131877, 62268, 30.0),
    ("NY", "New York",     20201249,  47126,  7429, 2297159, 84578, 40.2),
    ("NC", "North Carolina",10439388, 48618,  5201,  828083, 70804, 36.4),
    ("ND", "North Dakota",   779094,  69001,  1698,   76366, 75949, 32.0),
    ("OH", "Ohio",         11799448,  40861,  3877,  840312, 67769, 31.0),
    ("OK", "Oklahoma",      3959353,  68595,  1281,  255206, 63603, 28.4),
    ("OR", "Oregon",        4237256,  95988,  2391,  315098, 79224, 38.7),
    ("PA", "Pennsylvania", 13002700,  44743,  1312,  974628, 76081, 35.7),
    ("RI", "Rhode Island",  1097379,   1034,   511,   82197, 84972, 39.0),
    ("SC", "South Carolina", 5118425, 30061,  1960,  348127, 67804, 32.1),
    ("SD", "South Dakota",   886667,  75811,  1318,   80175, 71306, 31.4),
    ("TN", "Tennessee",     6910840,  41235,   926,  535340, 67631, 31.5),
    ("TX", "Texas",        29145505, 261232,  7365, 2660105, 75780, 33.6),
    ("UT", "Utah",          3271616,  82170,  2727,  264470, 89168, 38.4),
    ("VT", "Vermont",        643077,   9217,   400,   42819, 76079, 41.7),
    ("VA", "Virginia",      8631393,  39490,  3180,  701767, 89393, 41.7),
    ("WA", "Washington",    7705281,  66456,  4845,  819051, 91306, 40.0),
    ("WV", "West Virginia", 1793716,  24038,   192,   97349, 55948, 23.2),
    ("WI", "Wisconsin",     5893718,  54158,  9342,  428049, 72458, 32.7),
    ("WY", "Wyoming",        576851,  97093,   727,   53066, 72495, 30.6),
]

STATES: dict[str, dict] = {}
NAME_TO_USPS: dict[str, str] = {}
for usps, name, pop, land, water, gdp_m, mhi, bach in _RAW:
    total = land + water
    rec = {
        "usps": usps,
        "name": name,
        "population": pop,
        "land_area_sq_mi": land,
        "water_area_sq_mi": water,
        "total_area_sq_mi": total,
        "water_pct": (water / total) * 100.0 if total else 0.0,
        "gdp_million_usd": gdp_m,
        "gdp_per_capita_usd": (gdp_m * 1_000_000) / pop,
        "median_household_income_usd": mhi,
        "bachelors_or_higher_pct": bach,
    }
    STATES[usps] = rec
    NAME_TO_USPS[name.lower()] = usps


# Common aliases / misspellings encountered in post bodies and image labels.
ALIASES = {
    "west virgina": "WV",  # OP typo in post #6
    "washington dc": "DC",
    "d.c.": "DC",
    "dc": "DC",
}


def lookup(s: str) -> str | None:
    """Resolve a free-text state reference (full name or USPS) to a USPS code."""
    if not s:
        return None
    key = s.strip().lower()
    if key in ALIASES:
        return ALIASES[key]
    if len(key) == 2 and key.upper() in STATES:
        return key.upper()
    return NAME_TO_USPS.get(key)


if __name__ == "__main__":
    assert len(STATES) == 51, len(STATES)
    print(f"Loaded {len(STATES)} state records")
    print(f"  total US population: {sum(s['population'] for s in STATES.values()):,}")
    print(f"  total US GDP:        ${sum(s['gdp_million_usd'] for s in STATES.values()):,}M")
