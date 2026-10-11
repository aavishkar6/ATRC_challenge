# ATRC challenge — aviation and hotel demand

Analysis for the [DCT Abu Dhabi challenge](https://challengeon.atrc.ae/en/challenges/atp2026/pages/dct-challenge-statement?lang=en): an interpretable simulator linking aviation supply to hotel demand.

## Notebooks

- `experiments/notebooks/01_cleaning_features.ipynb` builds the existing cleaned data and feature panel.
- **`experiments/notebooks/02_domain_analysis.ipynb`** contains the research-informed analysis: source definitions, measurement checks, market coverage, seasonality, conversion ratios, passenger/check-in timing, conditional relationships, and a feature-evidence handoff. It includes executed outputs and uses the **cursor** kernel.
- **`experiments/notebooks/03_interpretable_models.ipynb`** fits and compares five interpretable candidates, audits the selected model, plots its responses, verifies the browser calculations, and rebuilds the offline demo.
- `experiments/notebooks/exploratory.ipynb` is the earlier exploratory work.

The domain analysis uses **2023–2024 only** for demand relationships. January–July 2025 is reserved for later model validation. It reads original spreadsheets and audits the existing panel without changing either. No GAM or production forecast is fitted in this notebook; small regressions support conditional diagnostics.

## Environment and execution

The existing `cursor` Jupyter kernel points to `.venv/bin/python`. The tested environment is Python **3.14.7**. Direct dependencies are listed in `requirements-analysis.in`; `requirements-analysis.txt` pins their installed dependency closure.

For a fresh checkout:

```bash
python3.14 -m venv .venv
.venv/bin/python -m pip install -r requirements-analysis.txt
.venv/bin/python -m ipykernel install --user --name cursor --display-name cursor
.venv/bin/jupyter lab
```

Select **cursor**, open the domain-analysis notebook, and run all cells. It discovers the repository root from the working directory and can run from the root or `experiments/notebooks/`.

To execute it from the command line:

```bash
.venv/bin/jupyter nbconvert --to notebook --execute --inplace experiments/notebooks/02_domain_analysis.ipynb --ExecutePreprocessor.kernel_name=cursor --ExecutePreprocessor.timeout=240
```

The notebook runs without network access once dependencies are installed. Its source registry includes links, findings, scope limitations, and the date the web research was reviewed.

## Analysis outputs

Running the notebook generates ignored artifacts under `reports/domain_analysis/`:

- `sources.csv`, `hypotheses.csv`, and `feature_evidence.csv` connect research and hypotheses to proposed variables.
- `data_issues.csv` records ambiguous definitions and proposed cleaning corrections.
- Timing, conversion, conditional-slope, and coverage tables contain the numbers behind the plots.
- `figures/` contains PNG figures; `verification.csv` records checks; `run_manifest.json` records input hashes and package versions.

The executed notebook is the reviewable artifact in Git. Generated reports can be rebuilt from it. The final section reports conclusions directly from the calculations.

## Interpretation

`Guests` is retained as the supplied daily target. Its sum is called **reported guest-days** until the treatment of same-day visitors is clarified. A hotel nationality and an identically named flight origin do not identify the same population. Hotel check-ins divided by same-name P2P passengers is therefore a diagnostic ratio, not an identified hotel-capture probability.

The notebook preserves missing hotel observations, examines infant-excluded passenger counts before considering load-factor clipping, and separates descriptive associations from causal scenario claims. The existing modeling proposal is in `plan_3.md`; the new analysis documents assumptions that need revisiting before implementation.

## Models and interactive demo

Open **`demo/index.html`** directly in a browser. It is self-contained and works offline. Select an origin market and month, then adjust frequency, seats per flight, occupied-seat load factor, and transfer/transit share. The interface shows predicted reported guest-days, the change from baseline, the passenger arithmetic, daily demand, and the learned response.

The current comparison selected **monotonic regression** over two monotonic GAMs, a proportional chain and a seasonal baseline. Jan–Apr 2025 selection WMAPE is **25.0%** by nationality-day, versus **31.9%** for the seasonal baseline. On the untouched Jun–Jul audit, the selected model has **27.7%** nationality-day WMAPE and **6.5%** aggregate daily WMAPE. Aggregation allows market errors to offset. Models fit 2023–2024 after a 27-day warm-up; May 2025 is reserved for empirical error-band calibration. The resulting band had only 61.4% audit coverage, so the UI does not call it an 80% confidence interval.

To reproduce in the existing cursor environment:

```bash
.venv/bin/python -m pip install -r requirements-modeling.txt
.venv/bin/jupyter nbconvert --to notebook --execute --inplace experiments/notebooks/03_interpretable_models.ipynb --ExecutePreprocessor.kernel_name=cursor --ExecutePreprocessor.timeout=300
```

**Node.js** must be on PATH for the notebook's Python/JavaScript integration checks. Modeling uses pyGAM 0.12.0; the shared SciPy pin is 1.16.3 to satisfy pyGAM's supported version range. `pip check` passes in the cursor environment.

Implementation:

- `src/models.py`: raw-target panel, constrained model fits, temporal evaluation, selection and error-band audit.
- `src/scenario.py`: scenario timing and portable HTML export.
- `src/verify.py` and `tests/scenario.test.cjs`: fitted-model/export parity, arithmetic identities, lag behavior and four-slider sweeps across every market-month.
- `demo/template.html`, `demo/engine.js`, `demo/ui.js`: editable demo sources; regenerate `demo/index.html` through notebook 03 after changing them.
- `reports/models/`: generated score tables, all model predictions, selected forecasts through February 2026, elasticities, input hashes/package versions and verification results. These reports are ignored and reproducible.

The origin-to-nationality bridge is a visible **same-name assumption**, not learned routing. Twelve nationalities without direct origins use seasonal forecasts with aviation controls disabled. Domestic demand is excluded. Aviation validation is conditional on observed flight inputs; altered flight plans are associative scenarios, not proven causal effects. Extreme scenarios are flagged as extrapolation. The prototype does not calculate occupancy or unsupported new-route demand.
