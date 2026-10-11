# Flight / Stay

**An interpretable simulator linking flights into Abu Dhabi to international hotel demand.**
Built for the [ATP 2026 DCT Abu Dhabi challenge](https://challengeon.atrc.ae/en/challenges/atp2026/pages/dct-challenge-statement?lang=en)
by Aaviskar Gautam, Srijan Sthapit (NYU Abu Dhabi), Abdulrahman Alsharhan and Sarthak Malla (MBZUAI).

A planner picks a source market and month, changes flights per week, seats per flight, load
factor or connecting share, and immediately sees the predicted hotel guest-days, the passenger
chain behind them, the daily profile and the learned response curve.

## Try it in 10 seconds

Open **`demo/index.html`** in any modern browser. It is a single offline file: no server,
install or network needed.

## Results

Models were fitted on Jan 2023–Dec 2024, chosen on Jan–Apr 2025, and audited once on
Jun–Jul 2025, months never used for fitting or selection.

| June–July 2025 audit | Calendar-only baseline | Flight model (selected) |
|---|---:|---:|
| WMAPE, per nationality per day | 35.0% | **27.7%** |
| WMAPE, per market per month | 28.9% | **23.1%** |
| WMAPE, all nationalities per day | 17.7% | **6.5%** |

WMAPE = Σ|prediction − actual| / Σ actual.

Adding flight data reduces error by about a fifth relative to calendar patterns alone. The
monthly market figure is computed from `reports/models/all_predictions.parquet`.

## How it works

```
flights/week × seats/flight ─► seats ─► × load factor ─► passengers ─► × (1 − connecting share) ─► P2P arrivals
                                                                                                        │
                       month + weekday + trend (per nationality) ───────────────────────────────────────┤
                                                                                                        ▼
                                                                                              hotel Guests (daily)
```

1. **Transparent arithmetic.** The flight levers are converted to point-to-point (P2P)
   passengers using identities verified in the flight file. Total PAX = P2P + transfer +
   transit, and load factor = PAX / seats.
2. **Interpretable model**, one per hotel nationality:

   `log(1 + Guests) = α + β·log(1 + P2P₇) + month + weekday + trend`, with **β ≥ 0**.

   P2P₇ is the trailing 7-day mean of P2P arrivals. β is that market's passenger
   sensitivity: roughly, +10% passengers gives β × 10% more guests. It ranges from 0.07
   (Lebanon) through 0.91 (UK) to 1.87 (Qatar).
3. **Model choice by evidence.** Five candidates were compared: calendar-only, proportional
   chain, monotonic regression, and two monotonic GAMs. The simplest shape-safe model within
   1 point of the best selection WMAPE wins. The GAMs gave no gain, so the regression was
   selected.
4. **Sensitivity.** Frequency, aircraft size and load factor act identically, because they
   multiply into total seats. Connecting share is the strongest lever per point when most
   passengers transfer. For example, the UK in July 2025 has 83% connecting traffic.

## Reproduce everything

Requirements:
- Python 3.14;
- Node.js 18 or later, for the browser parity tests;
- the organiser's data pack.

1. **Data.** The competition data is licensed for challenge use only and is not included in
   this repository. Copy the DCT files into `dataset/01a - DCT Dataset/`:
   - `flight_data.xlsx`
   - `data international_train.xlsx` and `data international_test.xlsx`
   - `data domestic_train.xlsx` and `data domestic_test.xlsx`
   - `Data_Dictionary.pdf`
2. **Environment.**
   ```bash
   python3.14 -m venv .venv
   .venv/bin/python -m pip install -r requirements-modeling.txt
   ```
3. **Run.**
   ```bash
   ./reproduce.sh
   ```
   This executes notebooks 01 → 02 → 03 (about 5 minutes). It writes:
   - the cleaned data to `data/`;
   - the tables, figures and checks to `reports/`;
   - a rebuilt `demo/index.html`.

   Executed copies of the notebooks go to `reports/executed/`.

Runs are deterministic. `reports/models/run_manifest.json` records input file hashes and
package versions, and `reports/models/verification.json` records the checks:
- 7,398 Python checks, covering split order, the seats→passengers identity, and finite,
  monotone scenarios;
- over 200,000 JavaScript assertions confirming the browser matches Python, with differences
  below 1e-9.

## Repository layout

| Path | What it is |
|---|---|
| `demo/index.html` | Generated offline simulator (open this) |
| `demo/template.html`, `engine.js`, `ui.js` | Editable simulator sources. Rebuild with notebook 03 rather than editing `index.html` |
| `src/models.py` | Panel construction, the five candidate models, selection, calibration and audit |
| `src/scenario.py` | Scenario engine and export of the demo payload and HTML |
| `src/verify.py`, `tests/scenario.test.cjs` | Python integration checks and the JavaScript parity tests |
| `experiments/notebooks/01_cleaning_features.ipynb` | Reads the spreadsheets, caches them and builds the cleaned panel and reference tables |
| `experiments/notebooks/02_domain_analysis.ipynb` | Data audit: definitions, coverage, timing, seasonality and conditional relationships |
| `experiments/notebooks/03_interpretable_models.ipynb` | Model comparison, audit, plots, verification and demo build |
| `reference/` | Stated assumptions: origin↔nationality bridge, event list and market list |
| `proposal/flight_proposal_v2.pdf` | 10-slide proposal (LaTeX source alongside) |

## Assumptions and limitations

- **Origin ≠ nationality.** The flight file records the departure country; the hotel file
  records the guest's nationality. We link them by name: 33 of 45 nationalities match. The
  other 12 get a calendar-only forecast and their flight sliders are disabled rather than
  invented.
- **Target.** `Guests` is used as supplied. Monthly sums are called *reported guest-days*. We
  do not claim occupancy, rooms or length of stay, because the data has no room inventory.
- **Association, not causation.** The slider shows the response the model learned from past
  patterns, not a proven effect of adding a route. Scenarios outside a market's training range
  show a warning.
- **Not yet supported:**
  - new routes from unserved countries;
  - an event calendar;
  - calibrated uncertainty bands. A first empirical band covered 61% of audit days against a
    nominal 80%, so it is reported but not shown as a confidence interval.
- The supplied Aug 2025–Feb 2026 test files contain no `Guests` column, so forecasts for
  those months cannot be scored.

## License

Code: see `LICENSE`. The DCT data is the property of the organisers and is not redistributed here.
