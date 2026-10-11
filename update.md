# Flight / Stay: Codex session handoff

**Last updated:** 11 October 2026  
**Repository:** `/home/srijan/Desktop/hack/ATRC_challenge`  
**Purpose of this file:** Give a new Claude Code session enough context to continue the DCT Abu Dhabi challenge work without repeating the investigation or treating old plans as current results.

## 1. Read this first: current position

We have a working, offline, browser-based aviation-to-hotel scenario prototype; two executed analysis/modeling notebooks; an auditable five-model comparison; and a rendered 10-slide proposal deck. The selected model is a **per-nationality monotonic regression** using seven-day point-to-point (P2P) passenger exposure, month, weekday, and a regularized time trend. This is an interpretable conditional prediction model. Its browser slider response is **not a measured causal effect** of adding flights.

The most honest headline result is on the frozen June–July 2025 audit: **27.72% nationality-day WMAPE** for the selected flight model versus **34.96%** for the calendar-only seasonal baseline. The model improves prediction, but an error around 28% is material for individual market decisions. The **6.46% aggregate daily WMAPE** looks much smaller because errors in different nationalities can cancel. A major unresolved measurement problem is that the flight file keys a **departure country** and the hotel file keys a guest's **nationality**. Same-name matching is only a provisional assumption.

Open `demo/index.html` directly in a browser for the sliders. Read `experiments/notebooks/02_domain_analysis.ipynb` before changing feature definitions; read `experiments/notebooks/03_interpretable_models.ipynb` for the models, plots, results, and rebuild steps. The current proposal is `proposal/flight_stay_proposal.tex` with a compiled `proposal/flight_stay_proposal.pdf`.

**Precedence warning:** `plan_3.md` and parts of `CLAUDE.md` contain earlier hypotheses and claims that later analysis corrected. The original plan called `Guests` guest nights, treated arrivals/P2P as a capture probability, and expected to score the supplied Aug 2025–Feb 2026 test file. We subsequently found that the supplied hotel test files **do not include `Guests`**, the target's relationship with same-day guests is ambiguous, and the country definitions do not support an individual capture probability. The executed notebooks, `reports/domain_analysis/data_issues.csv`, `reports/models/run_manifest.json`, and this handoff take precedence for factual claims about the current implementation. Do not silently copy outdated numbers from `plan_3.md` into a new deck or model card.

## 2. User goal and how the work evolved

The user first asked us to understand the [ATRC/ATP 2026 DCT Abu Dhabi challenge statement](https://challengeon.atrc.ae/en/challenges/atp2026/pages/dct-challenge-statement?lang=en) carefully, then debate complex models versus interpretability. The end goal is a useful and visually clear HTML tool where a planner moves aviation sliders and sees hotel-demand predictions change. This is for a hackathon, but technical rigor matters: the official challenge weights it at 40% and asks for a working simulator, an explicit seats-to-passengers-to-visitors-to-hotel chain, historical validation, sensitivity, market/season granularity, decision relevance, and reproducibility. It also asks about new/discontinued routes, although the current prototype only supports existing directly matched origin markets.

The user pointed to `/home/srijan/Desktop/hack/Probability-of-Default-Model`, especially `GOLDENROD - Pitch Deck.pdf` and the term-project instructions. Goldenrod's modeling idea was to use domain knowledge before model fitting: financial ratios instead of raw totals, accounting identities and careful time alignment, monotonic/interpretable transformations, then a GAM that can be inspected. Its `estimator.py` also uses empirical LOWESS transformations. We took the **philosophy**, not the finance variables: verify aviation accounting identities, represent the supply chain explicitly, compare plausible timing transformations, enforce a non-decreasing aviation response, and examine the response curve. We did **not** use target-derived LOWESS transformations as model inputs here; those could leak labels or make slider behavior harder to interpret. The domain transformation is the arithmetic seat/passenger/P2P chain and a lagged P2P exposure.

The user asked for an analysis notebook, ran it, and saved it. We then built the comparison notebook and the HTML demo in the existing **`cursor`** environment. After reviewing the results, the user asked whether the model helps at all. Our conclusion was nuanced: adding aviation data beats the calendar-only baseline in the held-out periods, and the simple model is appropriate for an inspectable first prototype; the present data link and validation do not justify pitching the slider delta as the true number of hotel stays *caused* by a changed flight plan. Finally, the user asked for a concise student-style 10-slide LaTeX proposal. That deck exists and has been rendered and visually checked.

## 3. Repository and source data

The organizer data pack is in `dataset/01a - DCT Dataset/`:

- `flight_data.xlsx` and `Data_Dictionary.pdf`;
- international and domestic train spreadsheets;
- international and domestic test spreadsheets.

The earlier `01_cleaning_features.ipynb` created Parquet caches in `data/clean/` and a pre-existing panel in `data/features/panel.parquet`. The modeling code reads **`data/clean/flight_data.raw.parquet`** and **`data/clean/data international_train.raw.parquet`** so it can preserve the raw `Guests` target rather than using imputed target values from the older panel. The original `flight_data.raw.parquet` has 117,608 rows. The international train raw Parquet has 58,622 rows. `reference/bridge.csv`, `reference/events.csv`, and `reference/markets.csv` are older assumption/reference files. `reports/` is ignored by Git and can be rebuilt.

Some relevant data facts from the executed domain audit:

1. **Mixed flight grain.** The 2022 flight file has 12 distinct dates (monthly observations), while 2023 has 365 dates and 2024 has 366. The implemented daily relationship starts in 2023. There are 33,349 flight rows in 2023 and 37,607 in 2024.
2. **Flight identities hold.** Recorded total PAX equals P2P + transfer + transit, and reported load factor equals total PAX / seats. The `Average Weekly Frequency` field can be converted to recorded daily flight count as `frequency * days_in_month / 7` in the 2023+ records. Frequency, seats, load, and connection share should therefore be scenario arithmetic levers, not four unconstrained competing model features.
3. **Load factor anomalies.** 5,186 analyzed flight rows have recorded `PAX/seats > 1`. Excluding infants resolves 3,257; 1,929 remain above one. We did not silently clip the historic data. In the UI the baseline occupied-seat load generally uses infant-excluded PAX and a fixed infant adjustment; source exceptions above 100% are flagged.
4. **Hotel target semantics.** `Guests` is the supplied daily target. We call monthly sums **reported guest-days** until the organizer confirms exactly how same-day visitors relate to this count. We cannot infer true overnight guest nights, average length of stay, visitor capture, room occupancy, or a number of rooms from this field alone. Same-day blanks are unknown, not zero.
5. **Missing hotel observations.** There are 33 absent nationality-date rows in the 2023–24 analysis grid. The older cleaned panel had introduced 29 target values on absent hotel rows. The new analysis/modeling path leaves unknown `Guests` as missing and excludes them from fitting and scoring. Do not use imputed targets to claim validation accuracy.
6. **Origin versus nationality.** There are 45 hotel nationalities and 33 same-name departure-country matches. The other 12 nationalities account for about **7.6%** of observed international guest-days in the analysis window, so zero direct flights in this data do not mean zero hotel demand. Flight-origin country does not establish the passengers' nationality, travel purpose, airport, or lodging.
7. **Ratios are not capture probabilities.** In 196 of 787 complete same-name origin-month comparisons, hotel arrivals / P2P exceeds one. This is possible because the populations and coverage differ. Do not clamp this ratio to one or call it an individual probability.
8. **Timing signal.** For the 33 matched markets, median calendar/trend-adjusted within-market correlation with hotel demand for the trailing seven-day P2P mean was **0.444 in 2023** and **0.453 in 2024**; same-day P2P gave only **0.202** and **0.164**. An assumed four-day geometric stay kernel also looked plausible (**0.471** and **0.409**). The conditional seven-day slopes were positive for all 33 matched markets in both years. These are descriptive associations, not identified stay lengths or causal lags.
9. **Unverified event dates.** The existing `reference/events.csv` contains estimated/unverified spans. We did not put event flags into the fitted model or claim measured event effects. Only two complete training years are available for seasonal learning.
10. **The supplied test period has no hotel target.** The international and domestic test schemas covering Aug 2025–Feb 2026 lack `Guests`. They keep `New Arrivals`, which is itself a hotel outcome and would be an improper simulator input if the goal is flight-only planning. Forecasts for these months can be exported, but they have no measurable error yet.

The executed domain notebook `02_domain_analysis.ipynb` contains source inventory, measurement checks, flight and hotel coverage, timing comparisons, conditional associations, and a feature-evidence handoff. Its generated evidence is in `reports/domain_analysis/`: `sources.csv`, `hypotheses.csv`, `feature_evidence.csv`, `data_issues.csv`, `market_coverage.csv`, `timing_summary.csv`, `shape_comparison.csv`, `load_factor_audit.csv`, `verification.csv`, plots, and `run_manifest.json` with input hashes and package versions. **All 75 recorded domain-analysis checks passed.** The user reran/saved this notebook; do not overwrite its outputs casually. Its current notebook metadata may show `python3`, even though the project uses the `cursor` kernel for reproduction; explicitly select `cursor` when rerunning.

## 4. Modeling question, assumptions, and exact split

The estimand currently available is **conditional expected daily reported `Guests` for a nationality**, given a time/calendar pattern and observed P2P passenger history from the same-name origin. It is not an independently measured flights-to-visitors-to-room-nights conversion. The current UI's counterfactual scenarios hold calendar terms and the earlier passenger history fixed while changing one market's aviation inputs. That gives a model-implied response, not a causal effect.

`src/models.py` builds a complete nationality-by-date panel, joins raw hotel targets without filling them, aggregates 2023+ flight rows by uppercased origin/date, and computes:

- `p2p_7d`: mean of current-day and previous six days' P2P counts.
- `p2p_stay4`: a normalized 28-day geometric kernel with weights proportional to `0.75^lag`. The implied four-day mean is an assumption; no individual stays are observed here.
- Calendar month, weekday, and years since 1 January 2023.
- An indicator for whether a nationality has a same-name flight origin.

All candidates get the same first-27-day warm-up exclusion. `Guests` nulls are excluded from fit/metrics; missing flight rows on the constructed grid are represented as zero *recorded service*, which is not proof of complete traffic coverage. No current/historic hotel arrivals, target lags, cleaned-panel `season_index`, `capture_rate_hist`, or target-derived rolling features are supplied as predictors.

The time partition is **not random**:

| Stage | Dates | Role |
|---|---|---|
| Fit | 28 Jan 2023–31 Dec 2024 | Fit all per-market models; 27-day common warm-up. |
| Selection | Jan–Apr 2025 | Compare candidates on observed `Guests`; 5,400 nationality-days. |
| Calibration | May 2025 | Estimate descriptive per-market daily log-error quantiles; not used to choose the model. |
| Frozen audit | Jun–Jul 2025 | Evaluate the selected model once; 2,743 observed nationality-days. |
| Unlabeled | Aug 2025–Feb 2026 | Produce conditional predictions; do not report accuracy. |

The selected model and audit have now been inspected. Any future change motivated by the audit must **not** be called validated on an untouched version of the same audit. Use predeclared earlier rolling folds for iteration, and acquire new labeled periods for a fresh final test if possible.

## 5. Candidate models and why the simpler one was selected

Five candidate names and exact implementation are in `SPECS` in `src/models.py`. There are separate models for 45 nationalities. For a nationality without a direct same-name origin, every candidate falls back to its seasonal model; this prevents a fabricated direct-flight response.

| Candidate | Form and interpretation |
|---|---|
| **Seasonal baseline** | Per-nationality regression on `log1p(Guests)` using intercept, month dummies, weekday dummies, and regularized linear trend. It has **no flight feature**. This is a benchmark to see whether flight data adds predictive signal, not a challenge-organizer supplied figure. |
| **Proportional chain** | Per-nationality/month ratio of summed reported guest-days to summed lagged daily P2P, multiplied by current exposure. The coefficient is empirical and may exceed one; **it is not hotel capture probability**. |
| **Monotonic regression** | Seasonal design plus `log1p(p2p_7d)` with a **nonnegative coefficient** per linked market. This is the selected model. |
| **Monotonic GAM, seven days** | `LinearGAM` on `log1p(Guests)`, with a six-basis `monotonic_inc` spline on `log1p(p2p_7d)`, month factor, weekday factor, and linear trend. Fixed exposure smoothness penalty 10, seasonal penalty 1, trend penalty 10. |
| **Monotonic GAM, stay kernel** | Same GAM, replacing seven-day exposure with the geometric `p2p_stay4` exposure. |

The seasonal and monotonic linear models use bounded least squares with ridge penalties: intercept unpenalized, trend penalty 10, other terms penalty 1; the aviation coefficient in the monotonic version has lower bound zero. In symbolic shorthand for market `m` and date `t`:

```text
z_mt = log(1 + Guests_mt)
z_hat_mt = intercept_m + beta_m * log(1 + trailing_P2P_7d_mt)
           + month_effect_m + weekday_effect_m + trend_m * time_t
beta_m >= 0
Guests_hat_mt = max(0, exp(z_hat_mt) * train_residual_smearing_m - 1)
```

The additive form and a single `beta_m` make the selected model inspectable. `beta_m` is an elasticity in shifted variables and is approximately an ordinary elasticity at larger counts; it should not be described as a causal response coefficient. Example: the exported United Kingdom coefficient is approximately **0.906**. GAM fits are also retransformed with training-residual smearing. All candidate response shapes were swept for finite, nonnegative, nondecreasing behavior; all passed the recorded gate.

Selection rule, frozen before reading the final audit: among scenario-capable candidates that pass the response shape gate, choose lowest Jan–Apr nationality-day WMAPE; if another candidate lies within **one percentage point**, choose the simpler candidate. The calendar-only baseline is a reference forecast but cannot operate aviation sliders, so it is not simulator eligible. The monotonic regression had the lowest primary selection error anyway. We did not search a large hyperparameter grid or retune from June–July.

This decision reflects what the domain work suggested: the lagged aviation exposure helps; month and market behavior matter; frequency/aircraft seats/load are best exposed through arithmetic; and a complex curve needs to show measured gain before it is worth the added explanation burden. The GAMs gave slightly worse selection WMAPE, so there is no demonstrated payoff from adding spline complexity in this experiment. This does **not** prove a linear log response is universally optimal; we have one main selection period and one audit period.

## 6. Metrics: exact definitions and measured performance

The primary error is **nationality-day WMAPE**:

```text
WMAPE = sum_over_observed_market_days(abs(prediction - Guests))
        / sum_over_observed_market_days(Guests)
```

It is weighted by volume because higher-Guest markets contribute more to the numerator and denominator. We also report `MAE = mean(abs(error))` per nationality-day; **bias** `= sum(prediction - Guests) / sum(Guests)`; **aggregate daily WMAPE**, which sums nationalities *before* taking each date's absolute error; and median of per-market WMAPEs. Aggregate daily WMAPE can look much better because opposite nationality errors offset.

The generated selection score table is `reports/models/selection_scores.csv`. Exact source predictions are `reports/models/all_predictions.parquet`; `metrics()` in `src/models.py` computes the values.

| Candidate | Jan–Apr selection WMAPE | Jun–Jul audit WMAPE | Jan–Apr aggregate WMAPE | Jun–Jul aggregate WMAPE |
|---|---:|---:|---:|---:|
| Seasonal baseline | **31.90%** | **34.96%** | 14.13% | 17.70% |
| Proportional chain | 28.68% | 28.21% | 10.40% | 8.16% |
| **Monotonic regression (selected)** | **25.03%** | **27.72%** | **8.65%** | **6.46%** |
| Monotonic GAM, seven days | 25.51% | 29.10% | 8.59% | 6.59% |
| Monotonic GAM, stay kernel | 25.56% | 29.01% | 8.33% | 6.39% |

Audit comparison: the selected model improves on the seasonal baseline by about **7.24 WMAPE percentage points**, or about **20.7% of the baseline error**. Its audit **MAE is 138.01 Guests per nationality-day**, **bias is +1.32%**, and **median per-market WMAPE is 25.38%**. There are 2,743 labeled nationality-days in the 45-market, 61-day audit grid; two are missing. Selection MAE is 153.41, bias +1.28%, and median market WMAPE 29.30%.

May was held out for error calibration, not model choice. For transparency, the selected model's May WMAPE was **31.51%**; the proportional chain's was **26.97%**. This is a reminder that rankings vary by period. We estimated each market's 10th/90th quantile of May log residuals and checked the resulting illustrative daily band on June–July. Actual audit coverage was only **61.39%**, far below a nominal 80% interpretation. We therefore **do not display a calibrated 80% confidence interval** in the UI. The notebook and `reports/models/run_manifest.json` record this shortfall.

Interpretation we gave the user: **yes, the model helps relative to a calendar-only reference**, both in selection and the frozen audit. **No, it is not ready to support a precise claim that a particular new flight will generate a particular number of hotel stays.** It measures conditional predictive association using observed aviation inputs. The relatively low aggregate error is not the right headline for an individual route/nationality decision. A stronger benchmark suite and route-change validation are needed before making high-confidence planning recommendations.

## 7. Browser simulator: implementation and semantics

The editable sources are `demo/template.html`, `demo/engine.js`, and `demo/ui.js`. `src/scenario.py` reads the fitted model results, exports a strict JSON payload, and embeds that payload plus JavaScript into a self-contained `demo/index.html` (~1.3 MB). It needs no web server, CDN, external font, or remote API. **Edit the sources and rerun notebook 03 to rebuild `index.html`; do not edit only the generated HTML.** `reports/models/demo_payload.json` is the reproducible intermediate. The Python source also supports exporting a dense GAM response lookup curve if a GAM wins on a future rebuild; the currently selected regression exports its exact passenger coefficient.

The browser offers four controls per supported origin market and month:

```text
monthly_seats = flights_per_week / 7 * days_in_month * seats_per_flight
total_passengers = monthly_seats * occupied_seat_load * observed_infant_multiplier
scenario_P2P = total_passengers * (1 - transfer_and_transit_share)
```

For each month, the scenario engine scales the **observed within-month daily P2P profile** to the new monthly P2P total. It leaves the previous **27 days** of passenger history unchanged, recomputes the chosen trailing exposure, and changes only that nationality's model predictions while calendar/time terms stay fixed. Consequently a flight cut at the start of a month can have a decaying effect from previous passenger arrivals; it should not instantly erase all reported hotel demand. The daily predictions are summed to monthly **reported guest-days**. The arithmetic is exact relative to the supplied monthly totals at the observed baseline; it does not simulate individual flights or visitors. **Frequency and seats per flight are separate controls but enter as a product.** Two scenarios with the same total seats, load and connecting share give the same passenger volume and, because the daily profile is only scaled, the same predicted demand. This is a known simplification relative to the older `plan_3.md` ambition to distinguish schedule patterns at equal monthly seats; the training diagnostics did not justify learning a separate frequency response after controlling for seats.

The UI shows scenario guest-days, an **observed-flight baseline prediction** from the **selected aviation model**, the delta, monthly seats/passengers/P2P, a daily prediction/actual plot where labels exist, a learned exposure-response curve, an explanation/formula, candidate comparison, audit scores, and assumptions. **Do not confuse the UI's observed-flight baseline with the separate calendar-only seasonal baseline candidate** in the comparison table. For dates Aug 2025–Feb 2026, the UI marks the period unlabeled and plots no invented actual `Guests`.

The UI flags scenario exposure outside that market's training range, preserves load-factor exceptions instead of silently clipping, and disables aviation controls for the 12 unmatched nationalities. New-route responses and room occupancy are intentionally absent because the required cross-market prior and room inventory have not been validated. A route closure is a strong extrapolation and can leave residual background hotel demand in this model.

The visual design is a responsive local HTML dashboard with a dark header, large scenario/result cards, left-side sliders, passenger-chain card, daily and learned-response SVG charts, comparison table, and inspectable assumptions. It was rendered and checked in headless Firefox on desktop and mobile widths. From the project root, `firefox demo/index.html` opens it locally.

## 8. Verification already performed

`src/verify.py` and `tests/scenario.test.cjs` run integration checks over the fitted markets/months. The saved result is `reports/models/verification.json`:

- **7,398 Python checks**: split boundaries, preservation of missing targets, 45/33 coverage, response-shape gate, baseline reconstruction from frequency/seats/load/connection share, exported baseline parity with the fitted Python model, finite nonnegative scenario predictions, monotonic response as flight volume changes, and prior-history lag behavior.
- **214,722 JavaScript assertions**: exported Python-vs-browser prediction parity for scale factors 0, 0.5, 1, 1.2, and 2 across market-months; baseline reset; four-slider sweeps; correct positive or negative direction; invalid input handling; and invariance of unmatched markets. Largest saved absolute Python/JS prediction difference is about **3.0 × 10^-11**.
- Browser smoke check in headless Firefox: for UK/July 2025 the baseline was 40,152 predicted reported guest-days and the +20% frequency preset showed 46,665; reset restored baseline, flight closure produced an extrapolation warning, Pakistan controls were disabled, Feb 2026 was marked unlabeled, and no horizontal overflow occurred at desktop or 390 px mobile width. Screenshots are in ignored `reports/models/demo_desktop.png` and `demo_mobile.png`.
- The domain notebook recorded 75 passing source and feature checks. The modeling notebook is executed and saved; its plots include selection error bars, nationality variation, aggregate audit actual-versus-predicted, and learned response curves.

These checks establish arithmetic and software consistency; they do **not** establish that the slider delta is a causal aviation effect.

## 9. Proposal deck created in this session

The user requested a **10-slide LaTeX proposal**, clear and student-like, following the challenge's required executive summary, team intro, problem, solution, system design, impact, feasibility, shortlist testing, and visuals. The result is `proposal/flight_stay_proposal.tex` with `proposal/assets/demo_baseline.png` and rendered `proposal/flight_stay_proposal.pdf`. The visual treatment adapts the user-selected Design Report template's white canvas, large black sans-serif headings, restrained warm accent, fine rules, image-led cover, and quiet footer. The template source itself was not changed. The rendered PDF has **exactly 10 pages** and was visually checked after fixing layout overflows. The source was compiled with **Tectonic 0.17.0**; another XeLaTeX-capable installation should also work.

Deck slides: (1) cover/executive summary, (2) team and prototype status, (3) planning question, (4) source data and bridge assumptions, (5) system diagram, (6) candidate models and readable response, (7) selection/audit metrics, (8) current HTML screenshot, (9) intended impact and real-life data needs, (10) shortlist demo/test plan and sources. `\TeamName`, `\MemberOne`, `\MemberTwo`, `\MemberThree`, and `\University` near the top of the `.tex` file are deliberate placeholders; **real names and affiliations are still needed before submission**. The current screenshot is a baseline view. A more persuasive second screenshot would show one concrete changed scenario (for example UK/July 2025, +20% frequency) with the slider, changed guest-days card, and curve visible. This is an optional improvement; the deck already builds and includes a prototype image.

The deck does not claim occupancy or new-route capability. It states the measured predictive result and the known bridge/causality limit instead of inventing conversion rates. The [official challenge statement](https://challengeon.atrc.ae/en/challenges/atp2026/pages/dct-challenge-statement?lang=en) was checked again while drafting it.

## 10. Files a new session should know

| Path | Role |
|---|---|
| `experiments/notebooks/01_cleaning_features.ipynb` | Earlier cleaning/features notebook; user changes exist, avoid overwriting. |
| `experiments/notebooks/exploratory.ipynb` | Earlier exploratory notebook; user changes exist, avoid overwriting. |
| `experiments/notebooks/02_domain_analysis.ipynb` | Executed and saved domain/measurement analysis. |
| `experiments/notebooks/03_interpretable_models.ipynb` | Executed comparison notebook; builds `reports/models/` and demo. |
| `src/models.py` | Raw panel construction, five model fits, selection, calibration, audit, artifacts. |
| `src/scenario.py` | Scenario timing and HTML/JSON export. |
| `src/verify.py`, `tests/scenario.test.cjs` | Python/JS parity and sensitivity/invariant checks. |
| `demo/template.html`, `demo/engine.js`, `demo/ui.js` | Editable prototype sources. |
| `demo/index.html` | Generated self-contained offline prototype; directly openable. |
| `reports/domain_analysis/` | Generated domain tables, figures, sources and input manifest. Ignored by Git. |
| `reports/models/selection_scores.csv` | Primary Jan–Apr candidate comparison. Ignored by Git. |
| `reports/models/all_predictions.parquet` | All candidate forecasts, including audit baseline. Ignored by Git. |
| `reports/models/selected_predictions.parquet` | Chosen model forecasts and descriptive bands. Ignored by Git. |
| `reports/models/run_manifest.json`, `verification.json` | Split/assumption/package/input-hash and check records. Ignored by Git. |
| `proposal/flight_stay_proposal.tex`, `.pdf`, `assets/demo_baseline.png` | Reviewable 10-slide deck and its existing screenshot. |
| `requirements-analysis.in/.txt`, `requirements-modeling.in/.txt` | Python 3.14 analysis/modeling dependencies; modeling lock includes pyGAM 0.12.0 and SciPy 1.16.3. |
| `README.md`, `CLAUDE.md`, `plan_3.md` | Project orientation, recent implementation note, and older historical plan; see the precedence warning above. |

`git status` currently shows modified `CLAUDE.md`, `README.md`, `01_cleaning_features.ipynb`, and `exploratory.ipynb`, plus untracked new notebooks, code, demo, proposal, and requirements. **No commit was made in this session.** The existing notebooks 01 and exploratory were already modified; do not reset or rewrite user work just to clean the tree. `reports/` is ignored, so a fresh checkout without the report artifacts must rerun the notebooks. Source spreadsheets and data caches are present in this working tree.

## 11. Environment and reproduction

The project environment is `.venv/bin/python` (Python **3.14.7**) and the existing Jupyter kernel named **`cursor`** points to it. Node.js is needed for notebook 03's JavaScript verification. Firefox is optional for opening/checking the demo. The domain notebook originally ran with SciPy 1.18.1; installing pyGAM 0.12.0 required a downgrade to **SciPy 1.16.3**. `pip check` passed after that change. The current requirements files reflect the combined environment.

From `/home/srijan/Desktop/hack/ATRC_challenge`:

```bash
.venv/bin/python -m pip install -r requirements-modeling.txt

# Rebuild the domain evidence. The user's saved outputs already exist, so only rerun if needed.
.venv/bin/jupyter nbconvert --to notebook --execute --inplace \
  experiments/notebooks/02_domain_analysis.ipynb \
  --ExecutePreprocessor.kernel_name=cursor --ExecutePreprocessor.timeout=240

# Refit models, score candidates, export the HTML and run parity/sensitivity checks.
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/jupyter nbconvert \
  --to notebook --execute --inplace \
  experiments/notebooks/03_interpretable_models.ipynb \
  --ExecutePreprocessor.kernel_name=cursor --ExecutePreprocessor.timeout=300

# Open the existing offline prototype.
firefox demo/index.html

# If Tectonic is installed, rebuild the PDF after editing the team details:
cd proposal && tectonic flight_stay_proposal.tex
```

The modeling run is deterministic; the `run_manifest.json` records SHA-256 hashes and package versions. The dataset is competition licensed, so avoid publishing raw data or a public service that exposes it. The HTML embeds derived historical/model payloads and should be reviewed against the competition's data-use terms before public deployment.

## 12. Main unresolved work, in priority order

1. **Confirm data definitions and bridge.** Ask the organizer/DCT whether `Guests` includes same-day guests, whether hotel nationality can be mapped to flight origin using approved aggregate origin/nationality cross-tabs, and whether room inventory and verified event dates are available. Without these, do not call reported guest-days true guest nights or occupancy and do not claim a measured capture rate.
2. **Validate changes, not only levels.** Find actual route/frequency/capacity changes, define treated and comparison periods/markets, and evaluate whether predicted *direction and magnitude of change* match observed hotel changes. Keep causal language conservative because route decisions and tourism demand may share causes.
3. **Strengthen baselines and period robustness.** Compare against a seasonal naive or same-month-prior-year forecast, recent hotel-history baseline (as a separate operational ceiling, not a flight-only simulator input), and multiple predeclared rolling temporal folds. Examine market-weighted and worst-market errors; selection was not universally best in May.
4. **Make the bridge and unsupported markets explicit.** A proposed new-route prior would need geographic/travel similarity, traceable assumptions, and leave-one-market-out evaluation. The current model cannot answer a never-before-served route question honestly; do not merely enable those sliders.
5. **Improve uncertainty.** May's 31 days of per-market residuals undercovered in the audit. Use more calibration periods or a conformal design with sufficient data and report empirical coverage by market and scenario regime before showing an interval as calibrated.
6. **Add real operational inputs only when validated.** Room supply would allow occupancy; hotel check-in/guest-night clarification would allow a true nights target; verified events and holidays may improve seasonal errors; domestic demand should remain a separate series with no aviation lever.
7. **Finish submission details.** Replace deck team placeholders, make a short prototype video, and optionally capture a clearer changed-scenario screenshot. Keep the proposal claims synchronized with the executed notebook and current demo.

### Decision rule for the next collaborator

Preserve the interpretability objective. Add complexity only to resolve a measured error or a missing challenge requirement, and re-evaluate it on a valid time split with slider shape checks. The existing model is a useful association-based prototype with demonstrated uplift over a calendar baseline; it is **not** the final causal aviation-to-hotel planning tool. Always label which stage of the seats-to-passengers-to-visitors-to-guest-nights chain is observed, computed, assumed, or not identified.
