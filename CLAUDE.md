# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A competition entry for the **Advanced Technology Pioneers 2026 (ATP2026)** challenge, DCT Abu Dhabi
track. Source of truth for the brief:
<https://challengeon.atrc.ae/en/challenges/atp2026/pages/dct-challenge-statement?lang=en>

Everything in this repo exists to satisfy that brief. **Before planning or proposing work, re-read
the "Challenge brief" section below and tie the proposal to a specific success criterion,
deliverable, or evaluation weight.** Technical rigour is 40% of the score, so modelling/validation
work outranks polish.

**`plan_3.md` is the modelling plan** — top-down from the five simulator questions, then data
cleaning/feature engineering, then model selection. Read it before touching the model. It supersedes
`plan_2.md`, which stays only as the longer draft.

**`plan.md` is the delivery plan** — problems, methods, day-by-day sprint, back-test protocol.
Read it before proposing work and keep it current as things land.

**Deadlines** (from the official timeline page): application closes **11 Oct 2026, 23:59 GMT+4**
(10-slide PDF + 1–2 min video + a working prototype — concept-only submissions are rejected);
shortlist announced 25 Oct; mentoring 26 Oct onward with a final submission in Nov; Demo Days
10–12 Nov and awards 13 Nov at ADNEC Al Ain.

## Challenge brief (DCT Abu Dhabi track)

**Ask:** an *interactive simulator* that links aviation supply to Abu Dhabi hotel demand. A user
adjusts aviation factors and immediately sees the effect on hotel guests / guest nights. Driving
questions: "how many hotel nights does a new twice-weekly route produce?", "what happens to
occupancy if an airline cuts frequency?"

**Core conversion chain to model and expose:**
`scheduled seats → arriving passengers (load factor) → inbound visitors → hotel guest nights`

**Exposure levers the UI should offer:** new/discontinued routes, weekly frequency, aircraft type,
seat capacity, load factor, origin-market mix, month/season, event calendar, transfer/transit share,
average length of stay.

**The central data problem (called out explicitly in the brief):** flight data keys country by
*departure origin*; hotel data keys it by *guest nationality*. These must be reconciled — see
"Country ↔ nationality bridge" below.

**Seven success criteria:**
1. Working simulator — outputs update as inputs change.
2. Transparent conversion chain — every assumption visible from seats to guest nights.
3. Historical validation — back-test with honest error metrics (WMAPE named in the brief).
4. Sensitivity analysis — identify the highest-impact factors.
5. Useful granularity — results segmented by source market and season.
6. Decision relevance — non-technical guidance for DCT planners.
7. Reproducibility — documented code, stated assumptions, acknowledged limitations.

**Suggested approach (hybrid, as the brief recommends):** a *parametric layer* for the auditable
conversion chain **plus** an *ML layer* (gradient boosting / regression) for seasonality and
non-linearities. Suggested stack, guidance only: Python, pandas/Polars, DuckDB, statsmodels,
LightGBM/XGBoost; SALib for sensitivity, SimPy optional; Streamlit or FastAPI + Plotly; Docker for
submission.

**Deliverables:** a 10-page PDF (problem, solution, system design/diagram, working demo, real-world
implementation plan) and a 1–2 minute video of the prototype. The expected output is a **functional
prototype, not a concept deck**.

**Evaluation:** technical accuracy & modelling rigour 40%, creativity 20%, feasibility 20%, clarity
of presentation 20%.

**Ground rules:** all supplied data is aggregated — no passenger-level or personal records; state
assumptions and show uncertainty ranges; data is licensed for competition use only. Teams are 3–4
people (UAE university students / recent graduates).

## Commands

The environment is a `uv`-managed venv at `.venv` (Python 3.14). There is **no** `pyproject.toml` or
root `requirements.txt` yet — packages were installed ad hoc. Installed: pandas, numpy, matplotlib,
openpyxl, pyarrow, ipykernel/jupyter. Not yet installed and needed for Plan B: lightgbm,
scikit-learn, statsmodels, SALib, streamlit, plotly.

**`experiments/notebooks/01_cleaning_features.ipynb` is the Plan A implementation** — runs top to
bottom, builds `data/features/panel.parquet` (51,975 rows = 1,155 days × 45 markets, 35 model
variables), and writes `reference/{bridge,events,markets}.csv` plus `reports/cleaning_log.md`.
`data/` and `reports/` are gitignored and rebuilt by running it; `reference/` is committed because
those three files are stated assumptions that must stay reviewable. The first run reads the `.xlsx`
files and caches `data/clean/*.raw.parquet`; delete those to force a re-read.

```bash
uv pip install <pkg>                      # add a dependency to .venv
.venv/bin/python script.py                # run a script (or `source .venv/bin/activate`)
.venv/bin/jupyter lab                     # notebooks; kernel is named "ATRC_challenge (3.14.7)"
```

`.xlsx` reads need `openpyxl`. `dataset/01a - DCT Dataset/Data_Dictionary.pdf` uses subset fonts and
will not yield text via `strings`/zlib — reading it requires poppler (`brew install poppler`).

Teammate prototype (see below), run from `DCT-Challenge-/`:

```bash
pip install -r requirements.txt && streamlit run streamlit_app.py
```

There are no tests, linters, or build steps in the repo yet.

## Repository layout

- `dataset/01a - DCT Dataset/` — the supplied competition data (committed, ~18MB).
- `experiments/notebooks/exploratory.ipynb` — the only analysis code so far: loads `flight_data.xlsx`,
  groups `Total P2P` by year / departure country / city / airline, plots monthly seasonality.
  Caveat: it has unfinished cells and a `plot_bar_chart` helper with a syntax error (`kwargs=`), and
  its `Config` points at `"data internation_test.xlsx"` (typo — real file is `international`).
- `paper/` — empty; intended for the written deliverable.
- `DCT-Challenge-/` — **gitignored**, and a separate git repo with its own remote
  (`jasmeenalzarooni3-netizen/DCT-Challenge-`). It is a teammate's prototype, not part of this
  repo's history. Do not commit it here; do not assume edits there land in this project.

## The data (verified by inspection, not just the dictionary)

All files have a single sheet named `Export`. Flight and hotel data are **not** pre-joined — doing
that join is the project.

**`flight_data.xlsx`** — 117,608 rows, 26 cols, `2022-01-01 → 2026-02-28`. Arrival is always Abu
Dhabi (`Arrival City` = "Abu Dhabi", `Destination` = "AUH"), so every row is an *inbound* flow.
33 `Departure Country Name`, 130 `Departure City`, 59 `Airline Name`; `(Date, Departure City,
Airline Name)` is unique.

**The grain changes mid-file.** 2022 holds only 12 dates (the 1st of each month), 1,213 rows,
~6,077 seats/row — those rows are *monthly* totals. 2023 onward is genuinely daily (365/366 dates,
~350 seats/row); 2026 has 59 days. Train daily models on 2023+ only; aggregate to month before
joining to hotel data.

Three identities verified across all rows:
- `Load Factor` == `Total PAX` / `Total Seats`, exactly. 9,896 rows (8.4%) exceed 1.0 but only 72
  exceed 1.05 (max 1.857) — mostly trivial overshoot, but cap to 1.0 in a *new* column and keep a
  flag rather than editing the raw value.
- `Total PAX` == `Total P2P` + `Total Transfer` + `Total Transit`, exactly. **Transfer is 49.5% of
  all arriving PAX**; transit is ~0. So `Total P2P` is the only hotel-relevant passenger count.
- `Average Weekly Frequency` is **not** a weekly count. On a daily row,
  `flights that day = AWF × days_in_month / 7` — an exact integer in all 116,395 non-2022 rows
  (max deviation 9e-16). Summing AWF over a month's days gives that route-month's true average
  weekly frequency. `Total Seats / flights` then lands on real gauges (174, 186, 230, 239, 290,
  327, 371; median 196). AWF is null for all of 2022.

**Hotel data** — four files, `Date` + `Residence (groups)` + metrics:
| file | rows | period | has `Guests` | `Nationality` |
|---|---|---|---|---|
| `data international_train.xlsx` | 58,622 | 2022-01-01 → 2025-07-31 | yes | 45 values |
| `data international_test.xlsx` | 9,202 | 2025-08-01 → 2026-02-28 | **no** | 45 values |
| `data domestic_train.xlsx` | 1,308 | 2022-01-01 → 2025-07-31 | yes | n/a |
| `data domestic_test.xlsx` | 212 | 2025-08-01 → 2026-02-28 | **no** | n/a |

Both test files carry `New Arrivals` and `Same-Day Guests` but drop `Guests`. **`Guests` (guest
nights) is therefore the quantity to predict over 2025-08 → 2026-02**, and flight data conveniently
extends through exactly that horizon — flights are the exogenous feature set for the test period.
`Residence (groups)` is constant per file (`International` / `Domestic`) and only distinguishes the
two streams.

### Country ↔ nationality bridge

The 33 flight departure countries are a strict **subset** of the 45 hotel nationalities (uppercased
comparison; zero flight-only names). The 12 nationalities with no direct origin in the flight file —
Australia, Brazil, Czechia, Denmark, Finland, Mexico, Morocco, Norway, Pakistan, Romania, South
Africa, Sweden — must be reached indirectly (transfer/transit share, or a fallback seasonal profile).
Any bridge must be an explicit, inspectable weight matrix (origin × nationality, ideally × month),
because criterion 2 requires the assumption be visible.

## Prior art: the Air2Stay prototype (`DCT-Challenge-/`)

Useful as a reference baseline for what a passing answer looks like, and for its vocabulary. It is a
single self-contained `Air2Stay_Prototype.html` (vanilla JS, hand-rolled SVG charts) that
`streamlit_app.py` merely embeds via `components.html` — Streamlit does no computation. All inputs
are **precomputed** into one `EMBEDDED_DATA` JSON blob in the HTML, so the app never touches the
`.xlsx` files; regenerating that blob from the dataset is a manual step with no script in the repo.

Its chain is literally `seats × loadFactor × p2pShare × conversionRate × averageStay`
(`chain()` / `runScenario()`), keyed by (origin, month) over 396 route-months, with a per-origin
`bridge` to nationalities and a monthly `fallbackBridge`. Calibrated defaults: capture rate 0.4246,
average stay 3.6 nights, P10/P90 multipliers 0.90/1.07. Reported back-test: train 2022-01→2024-12,
validate 2025-01→2025-07; WMAPE 0.0724 hybrid flight→check-ins, 0.0691 transparent chain, 0.1128
stay model. Note it validates on 2025-01→07 (inside the train window of the supplied split) and
ignores the actual 2025-08→2026-02 test period — a gap worth closing in our version.

## Modelling facts established so far

These came from measurement, and they shape the approach (details and method in `plan.md`):

- **The capture rate is not a constant.** Hotel `New Arrivals` for nationality X ÷ direct P2P
  arrivals from country X, measured per country-month over 2023-01→2025-07, has a median ranging
  from 0.08 (Azerbaijan) to 6.15 (China). 278 of 1,023 country-months exceed 1.0, which proves those
  guests reach Abu Dhabi by paths the AUH-only flight file cannot see. The teammate prototype's
  single global 0.4246 cannot be right for both ends of that range.
- **The aviation signal survives seasonality removal, in every market.** `log(guest nights)` on
  `log(P2P)` at market-month level with market×month-of-year fixed effects gives elasticity 0.586
  (r=0.656); per-market, after removing that market's own month-of-year mean, all 33 elasticities
  are positive, median 0.63. Median 0.63 *is* the non-linearity — diminishing returns, not 1:1.
  Elastic: Armenia 1.53, Qatar 1.42, USA 1.15, Spain 1.11, UK 0.91. Weak: Oman 0.02, Italy 0.03,
  Lebanon 0.12, Jordan 0.17, Philippines 0.22, Poland 0.27.
  Note: raw *level* correlations are much more pessimistic (Saudi 0.01, Turkey 0.04) and were
  misleading — Saudi and Turkey respond fine in log/de-seasonalized terms (0.82, 0.69). Use the
  de-seasonalized log-log elasticity for tiering, not level correlation.
- **`Guests` ÷ `New Arrivals` is the length of stay** — 3.26–3.75 recently (mean 3.69 over the
  window; 2022 reaches 5.47), domestic ~2.50. Derive it, don't assume 3.6.
- **The test files keep `New Arrivals`.** So a model fed the given arrivals will beat a flight-only
  model. Keep the two separate: the flight-only model is the simulator and the arrivals-fed model is
  the reference ceiling. Reporting both honestly is a rigour point.
- **Domestic is 38.6% of guest nights** (5.80M vs 9.24M international over the last 12 training
  months) and has no flight link. Model it separately; keep aviation levers off it.
- **No event calendar was supplied**, despite the brief listing one. The folder holds 5 data files
  plus the dictionary. Build `reference/events.csv` (Ramadan/Eid, F1 weekend, National Day, source
  markets' holidays) with a `source` column.
- Hotel nulls: intl train `New Arrivals` 262, `Same-Day Guests` 35,026 of 58,622 (59.7%); intl test
  `New Arrivals` 2. The date × nationality grid is 58,860 cells against 58,622 rows.
