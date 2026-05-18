"""Per-state metrics for 50 states + DC (DC excluded from the meme map but kept here for completeness).

All values are hard-coded from authoritative US government / non-profit sources so this
works offline and is reproducible. Each field's vintage + source is recorded in `SOURCES`
and surfaced on the report's Sources page.

Fields per record (keys are USPS abbreviations):
  Geography
    name, population, land_area_sq_mi, water_area_sq_mi
  Economy
    gdp_million_usd, median_household_income_usd, unemployment_pct, poverty_pct
  Education
    hs_or_higher_pct, bachelors_or_higher_pct, advanced_degree_pct
  Health
    adult_obesity_pct, life_expectancy_years
  Energy
    renewable_electricity_pct
  Religion
    christian_pct, unaffiliated_pct
  Demographics
    median_age, foreign_born_pct, white_alone_pct, black_alone_pct, hispanic_pct, asian_alone_pct

Derived: gdp_per_capita_usd, water_pct, total_area_sq_mi (computed at load time).
"""
from __future__ import annotations

SOURCES = {
    "population":                   ("US Census 2020 Decennial",                          "https://www.census.gov/data/tables/2020/dec/2020-apportionment-data.html"),
    "land_area_sq_mi":              ("US Census Gazetteer 2020",                          "https://www.census.gov/geographies/reference-files/2020/geo/gazetteer-files.html"),
    "water_area_sq_mi":             ("US Census Gazetteer 2020",                          "https://www.census.gov/geographies/reference-files/2020/geo/gazetteer-files.html"),
    "gdp_million_usd":              ("BEA, current-dollar state GDP 2023",                "https://www.bea.gov/data/gdp/gdp-state"),
    "median_household_income_usd":  ("US Census ACS 2022 5-year",                          "https://data.census.gov/table?q=S1901"),
    "unemployment_pct":             ("BLS, state annual unemployment 2023",                "https://www.bls.gov/lau/staadata.htm"),
    "poverty_pct":                  ("US Census ACS 2022 5-year, all-ages SAIPE",          "https://www.census.gov/data-tools/demo/saipe/"),
    "hs_or_higher_pct":             ("US Census ACS 2022 5-year, adults 25+",              "https://data.census.gov/table?q=S1501"),
    "bachelors_or_higher_pct":      ("US Census ACS 2022 5-year, adults 25+",              "https://data.census.gov/table?q=S1501"),
    "advanced_degree_pct":          ("US Census ACS 2022 5-year, adults 25+ (grad/pro)",   "https://data.census.gov/table?q=S1501"),
    "adult_obesity_pct":            ("CDC BRFSS 2022",                                     "https://www.cdc.gov/obesity/data/prevalence-maps.html"),
    "life_expectancy_years":        ("CDC NCHS, US Life Expectancy 2020",                  "https://www.cdc.gov/nchs/data-visualization/state-life-expectancy/index.htm"),
    "renewable_electricity_pct":    ("US EIA State Electricity Profiles 2022, renewables share of generation", "https://www.eia.gov/electricity/state/"),
    "christian_pct":                ("Pew Religious Landscape Study 2014",                 "https://www.pewresearch.org/religion/religious-landscape-study/"),
    "unaffiliated_pct":             ("Pew Religious Landscape Study 2014",                 "https://www.pewresearch.org/religion/religious-landscape-study/"),
    "median_age":                   ("US Census ACS 2022 5-year",                          "https://data.census.gov/table?q=S0101"),
    "foreign_born_pct":             ("US Census ACS 2022 5-year",                          "https://data.census.gov/table?q=B05002"),
    "white_alone_pct":              ("US Census 2020 Decennial, white alone, not Hispanic","https://www.census.gov/quickfacts/"),
    "black_alone_pct":              ("US Census 2020 Decennial, Black alone",              "https://www.census.gov/quickfacts/"),
    "hispanic_pct":                 ("US Census 2020 Decennial, Hispanic or Latino",       "https://www.census.gov/quickfacts/"),
    "asian_alone_pct":              ("US Census 2020 Decennial, Asian alone",              "https://www.census.gov/quickfacts/"),
}

# Each row, in column order matching FIELDS below.
FIELDS = [
    "usps", "name", "population", "land_area_sq_mi", "water_area_sq_mi",
    "gdp_million_usd", "median_household_income_usd", "unemployment_pct", "poverty_pct",
    "hs_or_higher_pct", "bachelors_or_higher_pct", "advanced_degree_pct",
    "adult_obesity_pct", "life_expectancy_years", "renewable_electricity_pct",
    "christian_pct", "unaffiliated_pct",
    "median_age", "foreign_born_pct",
    "white_alone_pct", "black_alone_pct", "hispanic_pct", "asian_alone_pct",
]

_RAW = [
    ("AL", "Alabama",       5024279,  50645,  1775,  302224, 59674, 2.4, 16.0, 87.3, 27.7, 10.6, 39.0, 73.5, 12.4, 86, 12, 39.6, 3.7, 63.1, 25.6,  5.3, 1.6),
    ("AK", "Alaska",         733391, 570641, 91316,   69570, 86631, 4.3,  9.6, 93.7, 31.4, 11.6, 33.5, 78.6, 32.5, 79, 16, 35.4, 8.0, 57.5,  3.0,  7.4, 6.4),
    ("AZ", "Arizona",       7151502, 113594,   396,  537969, 72581, 4.0, 12.5, 88.8, 32.3, 12.3, 31.3, 76.2, 17.3, 67, 27, 38.8,13.2, 53.4,  4.6, 31.7, 3.7),
    ("AR", "Arkansas",      3011524,  52035,  1143,  175574, 56335, 3.0, 16.2, 87.3, 25.0,  9.0, 36.5, 73.9, 13.4, 79, 18, 38.6, 4.7, 68.5, 15.0,  8.5, 1.7),
    ("CA", "California",   39538223, 155779,  7916, 3897614, 91551, 5.1, 12.0, 84.5, 36.5, 14.1, 26.5, 79.0, 49.9, 63, 27, 38.3,26.7, 34.7,  5.4, 40.2,15.4),
    ("CO", "Colorado",      5773714, 103642,   376,  528090, 87598, 3.4,  9.6, 92.1, 45.7, 16.4, 25.1, 78.5, 35.7, 64, 29, 37.6, 9.8, 65.1,  3.9, 22.0, 3.6),
    ("CT", "Connecticut",   3605944,   4842,   698,  342375, 90213, 3.8,  9.8, 91.0, 41.0, 18.6, 28.4, 79.2, 41.4, 70, 23, 41.0,15.1, 62.1, 10.8, 18.2, 5.3),
    ("DE", "Delaware",       989948,   1949,   536,   91118, 79325, 4.2, 11.4, 90.7, 35.0, 14.0, 33.6, 78.6, 27.4, 76, 19, 41.4,11.0, 56.5, 21.5, 11.3, 4.7),
    ("DC", "District of Columbia", 689545, 61,  7,   178391,101027, 5.6, 14.0, 92.6, 64.7, 36.2, 24.0, 76.5, 21.6, 65, 24, 34.4,15.2, 39.6, 41.4, 11.5, 4.9),
    ("FL", "Florida",      21538187,  53624, 12133, 1647739, 67917, 2.9, 12.7, 89.0, 32.3, 11.7, 28.4, 77.5, 30.0, 70, 24, 42.3,21.6, 51.5, 14.5, 26.5, 3.0),
    ("GA", "Georgia",      10711908,  57513,  1912,  819532, 71355, 3.2, 13.4, 88.7, 34.1, 13.2, 34.1, 76.4, 27.6, 79, 18, 37.5,10.8, 50.1, 30.6,  9.8, 4.4),
    ("HI", "Hawaii",        1455271,   6423,  4509,  104077, 94814, 3.3,  8.9, 92.6, 35.4, 12.7, 25.4, 80.7, 23.5, 63, 26, 39.8,18.2, 21.5,  1.6, 10.3,37.0),
    ("ID", "Idaho",         1839106,  82643,   926,  124903, 70214, 3.2, 10.4, 91.4, 30.6, 10.6, 30.7, 79.5, 81.4, 67, 27, 37.1, 6.0, 80.7,  0.9, 12.9, 1.6),
    ("IL", "Illinois",     12812508,  55519,  2441, 1132513, 78433, 4.7, 11.5, 90.3, 37.4, 15.0, 32.4, 77.0, 12.8, 71, 22, 39.3,14.4, 59.7, 14.1, 17.5, 6.0),
    ("IN", "Indiana",       6785528,  35826,   593,  490608, 67173, 3.4, 11.4, 89.7, 28.6, 11.0, 36.1, 76.0,  9.3, 72, 26, 38.3, 5.5, 76.9, 10.0,  7.7, 2.7),
    ("IA", "Iowa",          3190369,  55857,   415,  256715, 70571, 2.9, 10.8, 92.7, 30.4, 11.0, 34.5, 78.4, 60.7, 77, 21, 38.9, 5.7, 83.6,  4.5,  6.9, 2.7),
    ("KS", "Kansas",        2937880,  81759,   520,  237522, 69747, 2.8, 11.0, 91.7, 35.4, 12.7, 36.0, 78.0, 47.0, 76, 20, 37.4, 7.4, 73.9,  6.1, 12.7, 3.4),
    ("KY", "Kentucky",      4505836,  39486,   921,  280030, 60183, 3.9, 16.0, 87.7, 26.5,  9.7, 36.6, 75.3, 12.2, 76, 22, 39.5, 4.1, 81.3,  8.5,  4.2, 1.7),
    ("LA", "Louisiana",     4657757,  43204,  8283,  306334, 57852, 3.8, 18.6, 86.0, 25.9, 10.4, 39.1, 75.9,  8.4, 84, 13, 37.8, 4.5, 56.5, 31.4,  6.9, 1.9),
    ("ME", "Maine",         1362359,  30843,  4537,   85925, 71139, 2.9, 10.3, 93.4, 34.4, 13.6, 30.4, 78.7, 78.8, 60, 31, 45.1, 4.5, 90.2,  1.9,  2.0, 1.4),
    ("MD", "Maryland",      6177224,   9707,  2633,  522017, 98461, 2.5,  9.1, 91.4, 42.7, 19.6, 33.8, 78.5, 14.4, 69, 23, 39.6,15.7, 47.2, 31.1, 12.0, 7.2),
    ("MA", "Massachusetts", 7029917,   7800,  2715,  734222,101341, 3.4,  9.4, 92.8, 47.8, 21.4, 25.4, 80.6, 30.0, 58, 32, 40.1,17.7, 67.6,  9.0, 13.0, 7.6),
    ("MI", "Michigan",      10077331, 56539, 40175,  679436, 71149, 3.9, 12.6, 91.4, 32.0, 12.7, 33.0, 77.0, 12.3, 70, 24, 40.3, 6.7, 73.9, 13.7,  5.6, 3.3),
    ("MN", "Minnesota",     5706494,  79627,  7309,  494569, 84313, 2.9,  9.0, 94.4, 39.1, 13.5, 30.1, 80.4, 33.4, 74, 20, 38.7, 8.6, 79.4,  6.9,  5.8, 5.2),
    ("MS", "Mississippi",   2961279,  46923,  1521,  156470, 52985, 3.4, 18.7, 85.6, 24.0,  9.0, 38.7, 74.0, 15.8, 83, 14, 38.0, 2.5, 56.5, 37.0,  3.5, 1.1),
    ("MO", "Missouri",      6154913,  68742,   811,  423689, 65920, 2.9, 12.5, 90.5, 31.4, 12.0, 34.4, 76.8, 12.7, 80, 16, 39.1, 4.4, 76.5, 11.5,  4.7, 2.4),
    ("MT", "Montana",       1084225, 145546,  1494,   77793, 70804, 3.0, 12.1, 94.0, 35.2, 11.7, 31.3, 78.4, 60.4, 72, 23, 40.5, 2.4, 85.4,  0.6,  4.4, 0.9),
    ("NE", "Nebraska",      1961504,  76824,   481,  175111, 71722, 2.5, 10.5, 92.0, 34.5, 12.3, 35.8, 78.6, 41.4, 75, 20, 36.9, 7.7, 75.5,  4.8, 12.0, 2.7),
    ("NV", "Nevada",        3104614, 109781,   790,  244829, 76364, 5.5, 12.6, 87.6, 27.4, 10.0, 26.1, 78.0, 39.7, 66, 28, 38.6,19.3, 45.9,  9.8, 29.2, 9.0),
    ("NH", "New Hampshire", 1377529,   8953,   382,  120307, 90845, 2.7,  7.5, 93.8, 40.5, 16.4, 30.4, 79.0, 30.6, 60, 36, 43.4, 6.4, 87.2,  1.6,  4.3, 3.0),
    ("NJ", "New Jersey",    9288994,   7354,  1304,  836132, 97126, 4.2, 10.2, 90.6, 43.3, 18.6, 27.0, 80.7, 28.2, 67, 23, 40.4,23.4, 51.9, 15.1, 21.6,10.2),
    ("NM", "New Mexico",    2117522, 121298,   292,  131877, 62268, 3.5, 18.4, 87.5, 30.0, 12.5, 33.4, 76.0, 47.5, 76, 18, 39.5, 9.4, 36.5,  2.6, 50.1, 1.7),
    ("NY", "New York",     20201249,  47126,  7429, 2297159, 84578, 4.1, 13.7, 88.3, 40.2, 17.3, 27.3, 78.9, 31.6, 60, 27, 39.8,23.6, 53.7, 17.6, 19.5, 9.5),
    ("NC", "North Carolina",10439388, 48618,  5201,  828083, 70804, 3.6, 13.6, 88.7, 36.4, 12.6, 33.7, 76.6, 17.2, 77, 20, 39.6, 8.4, 60.5, 22.2, 10.7, 3.5),
    ("ND", "North Dakota",   779094,  69001,  1698,   76366, 75949, 2.0, 10.2, 93.0, 32.0, 10.0, 35.2, 77.1, 53.4, 77, 20, 35.6, 4.4, 83.1,  3.4,  4.4, 1.7),
    ("OH", "Ohio",         11799448,  40861,  3877,  840312, 67769, 3.6, 13.4, 90.6, 31.0, 12.3, 35.9, 76.5,  8.6, 73, 22, 39.6, 5.0, 75.5, 13.1,  4.5, 2.7),
    ("OK", "Oklahoma",      3959353,  68595,  1281,  255206, 63603, 3.0, 15.6, 88.6, 28.4, 10.0, 36.2, 75.4, 13.5, 79, 18, 36.9, 6.3, 64.4,  7.8, 11.9, 2.4),
    ("OR", "Oregon",        4237256,  95988,  2391,  315098, 79224, 3.9, 11.5, 91.6, 38.7, 14.9, 29.6, 78.8, 67.7, 61, 31, 40.7,10.0, 72.5,  2.2, 13.4, 4.8),
    ("PA", "Pennsylvania", 13002700,  44743,  1312,  974628, 76081, 3.6, 11.7, 91.4, 35.7, 14.7, 33.1, 77.5,  4.2, 73, 21, 40.8, 7.4, 73.5, 12.2,  8.6, 4.0),
    ("RI", "Rhode Island",  1097379,   1034,   511,   82197, 84972, 3.4, 11.0, 90.1, 39.0, 16.3, 30.7, 79.1, 34.1, 73, 20, 40.4,14.0, 66.3,  8.5, 17.1, 3.9),
    ("SC", "South Carolina", 5118425, 30061,  1960,  348127, 67804, 3.0, 13.1, 89.4, 32.1, 11.4, 36.0, 76.2, 13.4, 78, 19, 40.4, 5.5, 62.6, 26.0,  7.0, 2.0),
    ("SD", "South Dakota",   886667,  75811,  1318,   80175, 71306, 1.9, 12.3, 93.1, 31.4, 10.6, 33.8, 77.7, 81.7, 79, 18, 37.5, 4.1, 80.1,  2.6,  4.6, 2.0),
    ("TN", "Tennessee",     6910840,  41235,   926,  535340, 67631, 3.2, 13.4, 89.8, 31.5, 11.7, 36.6, 76.0,  6.8, 81, 14, 39.0, 5.6, 70.9, 16.1,  7.2, 2.2),
    ("TX", "Texas",        29145505, 261232,  7365, 2660105, 75780, 4.0, 13.4, 85.8, 33.6, 12.5, 30.6, 76.5, 31.4, 77, 18, 35.5,17.2, 39.7, 12.1, 40.2, 5.4),
    ("UT", "Utah",          3271616,  82170,  2727,  264470, 89168, 2.9,  8.6, 94.2, 38.4, 13.9, 31.6, 78.6, 13.5, 79, 16, 31.9, 9.0, 76.4,  1.5, 15.1, 2.7),
    ("VT", "Vermont",        643077,   9217,   400,   42819, 76079, 2.4,  9.8, 94.2, 41.7, 16.6, 28.7, 79.0, 99.6, 54, 37, 43.0, 4.7, 89.4,  1.4,  2.4, 2.0),
    ("VA", "Virginia",      8631393,  39490,  3180,  701767, 89393, 2.9, 10.1, 91.4, 41.7, 18.4, 32.5, 78.0, 11.0, 73, 20, 39.0,12.9, 58.6, 18.6, 10.5, 7.1),
    ("WA", "Washington",    7705281,  66456,  4845,  819051, 91306, 4.1, 10.2, 92.6, 40.0, 16.4, 27.3, 79.2, 76.0, 61, 32, 38.4,14.5, 63.8,  3.8, 13.7, 9.6),
    ("WV", "West Virginia", 1793716,  24038,   192,   97349, 55948, 4.0, 16.7, 87.4, 23.2,  9.0, 39.5, 74.1,  9.0, 78, 18, 42.9, 1.7, 91.5,  3.4,  1.7, 0.8),
    ("WI", "Wisconsin",     5893718,  54158,  9342,  428049, 72458, 3.1, 10.7, 92.4, 32.7, 12.1, 32.0, 79.4, 27.5, 71, 25, 39.8, 5.2, 80.4,  6.4,  7.6, 3.1),
    ("WY", "Wyoming",        576851,  97093,   727,   53066, 72495, 3.7, 10.1, 93.2, 30.6, 10.6, 30.4, 77.0, 21.6, 71, 26, 38.6, 3.6, 83.2,  1.3, 10.5, 1.2),
]

STATES: dict[str, dict] = {}
NAME_TO_USPS: dict[str, str] = {}
for row in _RAW:
    rec = dict(zip(FIELDS, row))
    pop = rec["population"]
    land = rec["land_area_sq_mi"]
    water = rec["water_area_sq_mi"]
    total = land + water
    rec["total_area_sq_mi"] = total
    rec["water_pct"] = (water / total * 100.0) if total else 0.0
    rec["gdp_per_capita_usd"] = (rec["gdp_million_usd"] * 1_000_000 / pop) if pop else 0
    STATES[rec["usps"]] = rec
    NAME_TO_USPS[rec["name"].lower()] = rec["usps"]


ALIASES = {
    "west virgina": "WV",  # OP typo in post #6
    "washington dc": "DC",
    "d.c.": "DC",
    "dc": "DC",
}


def lookup(s: str) -> str | None:
    if not s:
        return None
    key = s.strip().lower()
    if key in ALIASES:
        return ALIASES[key]
    if len(key) == 2 and key.upper() in STATES:
        return key.upper()
    return NAME_TO_USPS.get(key)


# Back-compat: older VINTAGES dict pointed at this; SOURCES is the new structure.
VINTAGES = {k: src for k, (src, _) in SOURCES.items()}


# Metric groupings for the Pivots page.
METRIC_GROUPS = {
    "Economy": [
        ("gdp_million_usd",            "GDP",                     "sum",       "$",  "M USD"),
        ("gdp_per_capita_usd",         "GDP per capita",          "weighted",  "$",  ""),
        ("median_household_income_usd","Median household income", "weighted",  "$",  ""),
        ("unemployment_pct",           "Unemployment",            "weighted",  "",   "%"),
        ("poverty_pct",                "Poverty",                 "weighted",  "",   "%"),
    ],
    "Education": [
        ("hs_or_higher_pct",           "High-school+",            "weighted",  "",   "%"),
        ("bachelors_or_higher_pct",    "Bachelor's+",             "weighted",  "",   "%"),
        ("advanced_degree_pct",        "Advanced degree",         "weighted",  "",   "%"),
    ],
    "Health": [
        ("adult_obesity_pct",          "Adult obesity",           "weighted",  "",   "%"),
        ("life_expectancy_years",      "Life expectancy",         "weighted",  "",   " yrs"),
    ],
    "Energy": [
        ("renewable_electricity_pct",  "Renewable electricity",   "weighted",  "",   "%"),
    ],
    "Religion": [
        ("christian_pct",              "Christian",               "weighted",  "",   "%"),
        ("unaffiliated_pct",           "Religiously unaffiliated","weighted",  "",   "%"),
    ],
    "Demographics": [
        ("median_age",                 "Median age",              "weighted",  "",   ""),
        ("foreign_born_pct",           "Foreign-born",            "weighted",  "",   "%"),
        ("white_alone_pct",            "White (non-Hispanic)",    "weighted",  "",   "%"),
        ("black_alone_pct",            "Black",                   "weighted",  "",   "%"),
        ("hispanic_pct",               "Hispanic",                "weighted",  "",   "%"),
        ("asian_alone_pct",            "Asian",                   "weighted",  "",   "%"),
    ],
    "Geography": [
        ("population",                 "Population",              "sum",       "",   ""),
        ("land_area_sq_mi",            "Land area",               "sum",       "",   " mi²"),
        ("water_pct",                  "Water %",                 "area-weighted","","%"),
    ],
}


if __name__ == "__main__":
    assert len(STATES) == 51, len(STATES)
    print(f"Loaded {len(STATES)} state records, {len(FIELDS)} fields each")
    print(f"  total US population: {sum(s['population'] for s in STATES.values()):,}")
    print(f"  total US GDP:        ${sum(s['gdp_million_usd'] for s in STATES.values()):,}M")
