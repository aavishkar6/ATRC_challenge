"""Interpretable, temporal-holdout models. No hotel-derived predictor is used."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
from pathlib import Path

import numpy as np
import pandas as pd
from pygam import LinearGAM, f, l, s
from scipy.optimize import lsq_linear

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/models"
SPECS = {
    "Seasonal baseline": ("seasonal", "p2p_7d"),
    "Proportional chain": ("chain", "p2p_7d"),
    "Monotonic regression": ("linear", "p2p_7d"),
    "Monotonic GAM · 7 days": ("gam", "p2p_7d"),
    "Monotonic GAM · stay kernel": ("gam", "p2p_stay4"),
}
COMPLEXITY = {name: i for i, name in enumerate(SPECS)}


def load_panel():
    """Use unfilled raw targets and daily flight observations from 2023 onward."""
    paths = sorted((ROOT / "data/clean").glob("*.raw.parquet"))
    flights = pd.read_parquet(ROOT / "data/clean/flight_data.raw.parquet")
    hotels = pd.read_parquet(ROOT / "data/clean/data international_train.raw.parquet")
    hotels = hotels.rename(columns={"Date": "date", "Nationality": "market", "Guests": "target"})
    assert not hotels.duplicated(["date", "market"]).any()
    flights = flights.loc[flights.Date.ge("2023-01-01")].copy()
    flights["market"] = flights["Departure Country Name"].str.upper()
    flights["flights"] = flights["Average Weekly Frequency"] * flights.Date.dt.days_in_month / 7
    names = {"Date": "date", "Total P2P": "p2p", "Total Seats": "seats",
             "Total PAX": "pax", "Total PAX Excluding Infant": "pax_ex_infant",
             "Total Transfer": "transfer", "Total Transit": "transit"}
    flights = flights.rename(columns=names)
    # Missing infant-excluded observations are flagged, never replaced by invented counts.
    flights["infant_count_missing"] = flights.pax_ex_infant.isna().astype(int)
    values = list(names.values())[1:] + ["flights", "infant_count_missing"]
    daily = flights.groupby(["market", "date"])[values].sum(min_count=1)
    markets = sorted(hotels.market.unique())
    dates = pd.date_range("2023-01-01", flights.date.max())
    index = pd.MultiIndex.from_product([markets, dates], names=["market", "date"])
    panel = daily.reindex(index, fill_value=0).reset_index()
    panel["linked"] = panel.market.isin(flights.market.unique())
    panel = panel.merge(hotels[["market", "date", "target"]], how="left", on=["market", "date"], validate="1:1")
    panel["p2p_7d"] = panel.groupby("market").p2p.transform(lambda x: x.rolling(7, min_periods=7).mean())
    kernel = .75 ** np.arange(28)
    kernel /= kernel.sum()
    panel["p2p_stay4"] = panel.groupby("market").p2p.transform(
        lambda x: pd.Series(np.convolve(x, kernel, mode="full")[:len(x)], index=x.index))
    # Both candidates receive the same 28-day warm-up exclusion.
    panel["usable"] = panel.date.ge("2023-01-28")
    panel["month"] = panel.date.dt.month
    panel["dow"] = panel.date.dt.dayofweek
    panel["time"] = (panel.date - pd.Timestamp("2023-01-01")).dt.days / 365.25
    panel["split"] = np.select([
        panel.date.lt("2025-01-01"), panel.date.lt("2025-05-01"),
        panel.date.lt("2025-06-01"), panel.date.lt("2025-08-01")],
        ["train", "selection", "calibration", "audit"], default="unlabeled")
    manifest = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    return panel, manifest


def calendar_design(d):
    # Reference month/weekday removed; ridge regularizes seasonal factors and trend.
    return np.column_stack([np.ones(len(d)), d.time,
                            *[(d.month == i).astype(float) for i in range(2, 13)],
                            *[(d.dow == i).astype(float) for i in range(1, 7)]])


class MarketModel:
    def __init__(self, kind, feature, linked):
        self.kind = kind if linked else "seasonal"
        self.feature = feature
        self.linked = linked

    def fit(self, d):
        assert d.date.max() < pd.Timestamp("2025-01-01")
        assert d.target.notna().all()
        self.train_range = [float(d[self.feature].min()), float(d[self.feature].max())]
        z = np.log1p(d.target.to_numpy(float))
        if self.kind == "chain":
            # Ratio of sums of guest-days to lagged daily P2P; NOT capture probability.
            by = d.groupby("month").agg(y=("target", "sum"), x=(self.feature, "sum"))
            self.ratios = (by.y / by.x.replace(0, np.nan)).fillna(d.target.sum() / d[self.feature].sum()).to_dict()
            self.smear = 1.
        elif self.kind == "gam":
            X = self.gam_design(d)
            self.estimator = LinearGAM(
                s(0, n_splines=6, constraints="monotonic_inc", lam=10)
                + f(1, lam=1) + f(2, lam=1) + l(3, lam=10), max_iter=200).fit(X, z)
            self.smear = float(np.mean(np.exp(z - self.estimator.predict(X))))
        else:
            X = calendar_design(d)
            if self.kind == "linear":
                X = np.column_stack([X, np.log1p(d[self.feature])])
            penalty = np.ones(X.shape[1]); penalty[0] = 0; penalty[1] = 10
            A = np.vstack([X, np.diag(np.sqrt(penalty))])
            b = np.r_[z, np.zeros(X.shape[1])]
            lower = np.full(X.shape[1], -np.inf)
            if self.kind == "linear":
                lower[-1] = 0
            self.coef = lsq_linear(A, b, bounds=(lower, np.inf), tol=1e-10).x
            self.smear = float(np.mean(np.exp(z - X @ self.coef)))
        return self

    def gam_design(self, d):
        return np.column_stack([np.log1p(d[self.feature]), d.month, d.dow, d.time])

    def effect(self, exposure):
        exposure = np.asarray(exposure, dtype=float)
        if self.kind == "gam":
            X = np.column_stack([np.log1p(exposure), np.ones(len(exposure)), np.zeros(len(exposure)), np.zeros(len(exposure))])
            return self.estimator.partial_dependence(term=0, X=X)
        if self.kind == "linear":
            return self.coef[-1] * np.log1p(exposure)
        return np.zeros(len(exposure))

    def predict(self, d):
        if self.kind == "chain":
            return d[self.feature].to_numpy() * d.month.map(self.ratios).to_numpy()
        if self.kind == "gam":
            log_mu = self.estimator.predict(self.gam_design(d))
        else:
            X = calendar_design(d)
            if self.kind == "linear":
                X = np.column_stack([X, np.log1p(d[self.feature])])
            log_mu = X @ self.coef
        return np.maximum(0, np.exp(log_mu) * self.smear - 1)


def metrics(d):
    observed = d.dropna(subset=["target", "prediction"])
    error = observed.prediction - observed.target
    total = observed.target.sum()
    daily = observed.groupby("date")[["target", "prediction"]].sum()
    per = observed.assign(ae=error.abs()).groupby("market").agg(ae=("ae", "sum"), target=("target", "sum"))
    return {"wmape": float(error.abs().sum() / total),
            "bias": float(error.sum() / total), "mae": float(error.abs().mean()),
            "aggregate_wmape": float((daily.prediction - daily.target).abs().sum() / daily.target.sum()),
            "median_market_wmape": float((per.ae / per.target).median()), "observations": len(observed)}


def shape_gate(model):
    if not model.linked:
        return True
    x = np.expm1(np.linspace(0, np.log1p(max(model.train_range[1] * 10, 1)), 600))
    if model.kind == "chain":
        return all(np.isfinite(v) and v >= 0 for v in model.ratios.values())
    response = model.effect(x)
    return bool(np.isfinite(response).all() and np.diff(response).min() >= -1e-6)


def run_comparison():
    OUT.mkdir(parents=True, exist_ok=True)
    panel, hashes = load_panel()
    fits, predictions, rows, gates = {}, [], [], []
    for name, (kind, feature) in SPECS.items():
        fits[name] = {}
        for market, d in panel.groupby("market", sort=True):
            train = d.loc[d.split.eq("train") & d.usable & d.target.notna()]
            model = MarketModel(kind, feature, bool(d.linked.iloc[0])).fit(train)
            fits[name][market] = model
            gates.append({"model": name, "market": market, "passed": shape_gate(model)})
            future = d.loc[~d.split.eq("train")].copy()
            future["prediction"] = model.predict(future)
            future["model"] = name
            predictions.append(future[["market", "date", "split", "target", "prediction", "model", "linked"]])
        print(f"Fitted {name}: {len(fits[name])} markets", flush=True)
    pred = pd.concat(predictions, ignore_index=True)
    gate_df = pd.DataFrame(gates)
    # Choose only on Jan-Apr; calibration/audit never select or tune models.
    for name, d in pred.loc[pred.split.eq("selection")].groupby("model"):
        rows.append({"model": name, **metrics(d), "gate": bool(gate_df.loc[gate_df.model.eq(name), "passed"].all()),
                     "simulator_eligible": name != "Seasonal baseline"})
    scores = pd.DataFrame(rows).sort_values("wmape")
    eligible = scores.loc[scores.gate & scores.simulator_eligible]
    if eligible.empty:
        raise RuntimeError("No scenario model passed shape checks")
    near_best = eligible.loc[eligible.wmape <= eligible.wmape.min() + .01]
    selected = min(near_best.model, key=COMPLEXITY.get)
    # Freeze choice, then estimate descriptive daily error multipliers on May only.
    chosen = pred.loc[pred.model.eq(selected)].copy()
    cal = chosen.loc[chosen.split.eq("calibration") & chosen.target.notna()].copy()
    cal["log_error"] = np.log1p(cal.target) - np.log1p(cal.prediction)
    bands = cal.groupby("market").log_error.quantile([.1, .9]).unstack()
    bands.columns = ["q10", "q90"]
    chosen = chosen.join(bands, on="market")
    chosen["lower"] = np.maximum(0, np.expm1(np.log1p(chosen.prediction) + chosen.q10))
    chosen["upper"] = np.maximum(0, np.expm1(np.log1p(chosen.prediction) + chosen.q90))
    audit = chosen.loc[chosen.split.eq("audit") & chosen.target.notna()]
    audit_result = metrics(audit)
    audit_result["daily_band_coverage"] = float(((audit.target >= audit.lower) & (audit.target <= audit.upper)).mean())
    by_market = []
    for (name, market), d in pred.loc[pred.split.eq("selection")].groupby(["model", "market"]):
        by_market.append({"model": name, "market": market, **metrics(d)})
    summary = {"selected": selected, "selection_rule": "Lowest Jan-Apr WMAPE among shape-safe scenario models; simpler model within 1 percentage point wins.",
               "train": "2023-01-28 to 2024-12-31", "selection": "2025-01-01 to 2025-04-30",
               "calibration": "2025-05-01 to 2025-05-31", "audit_period": "2025-06-01 to 2025-07-31",
               "audit": audit_result, "input_sha256": hashes,
               "packages": {p: importlib.metadata.version(p) for p in ["numpy", "pandas", "scipy", "pygam"]},
               "target": "Guests; monthly sums are reported guest-days", "seed": "deterministic (no random search)",
               "bridge": "Identity on same-name origins/nationalities; 12 unsupported nationalities use seasonal fallback. This is an assumption, not estimated routing.",
               "evaluation": "Conditional on observed aviation supply; not an ex-ante flight schedule forecast. No hotel-derived predictors."}
    scores.to_csv(OUT / "selection_scores.csv", index=False)
    pd.DataFrame(by_market).to_csv(OUT / "selection_by_market.csv", index=False)
    gate_df.to_csv(OUT / "shape_gates.csv", index=False)
    chosen.to_parquet(OUT / "selected_predictions.parquet", index=False)
    pred.to_parquet(OUT / "all_predictions.parquet", index=False)
    (OUT / "run_manifest.json").write_text(json.dumps(summary, indent=2))
    return {"panel": panel, "fits": fits, "predictions": pred, "chosen": chosen, "scores": scores,
            "gates": gate_df, "bands": bands, "summary": summary}


if __name__ == "__main__":
    result = run_comparison()
    print(result["scores"].to_string(index=False))
    print(json.dumps(result["summary"], indent=2))
