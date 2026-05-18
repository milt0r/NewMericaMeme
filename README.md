# NewMericaMeme

A data report on the r/geographymemes voting series ["Top comment deletes a US State"](https://www.reddit.com/r/geographymemes/) — each round, the top comment chose a state to be absorbed into a neighboring "empire". After 42 rounds, 9 empires remain.

🌎 **Live report:** https://milt0r.github.io/NewMericaMeme/

## What's in the report
- **Merger trees** for each surviving empire, showing which states it absorbed and in what order
- **Cumulative empire population over time** (Plotly line chart)
- Cumulative GDP and land area over time
- **Final empire ranking** across population, GDP, GDP/capita, land area, median income, education
- **Round-by-round ledger** — every round's map, top comment, and the state that fell
- Population-weighted attribution for split states (some empires sliced states mid-round, not on state lines), using a US population-density raster

## How it works
| step | script | output |
|---|---|---|
| 1 | `fetch.py` | Caches every series post + its map image from Reddit |
| 2 | `parse.py` | Extracts `(round, eliminated_state, absorbing_empire)` from each post body |
| 3 | `image_analysis.py` | Geo-registers each map, color-segments empire regions, masks water, intersects with state polygons + population raster to attribute split states |
| 4 | `build_report.py` | Joins the round ledger with the per-state metrics dataset and renders `docs/index.html` |

All Reddit data is cached under `data/` so the report can be rebuilt without re-hitting Reddit.

## Local rebuild
```pwsh
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python fetch.py            # populates data/cache/ and data/images/  (skip with --skip-images for a quick run)
python build_report.py     # writes docs/index.html
```

## Data sources
- Reddit JSON API (post + image)
- US Census 2020 population, Census TIGER state polygons, Census Gazetteer (land area, water %)
- US BEA (state nominal GDP)
- US Census ACS 5-year (median household income, bachelor's-or-higher %)
- Kontur Population (Release 2023) or GHSL-POP 2020 for the population-density raster

## Missing rounds
Posts for rounds **#2–#5, #13, #18, #24, #25, #29, #30, #31** are no longer available on Reddit (likely deleted — post #41's body mentions re-uploads). The image-analysis step recovers each missing absorption event by diffing the surrounding rounds' maps.

## License
Code: MIT. Map images and post text are © the original Reddit author and embedded under fair-use commentary.
