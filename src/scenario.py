"""Portable scenario engine: preserve daily schedule shape and pre-scenario history."""
import json
from pathlib import Path

import numpy as np

from .models import ROOT, OUT


def exposure(p2p, feature):
    if feature == "p2p_7d":
        return np.convolve(p2p, np.ones(7) / 7, mode="full")[:len(p2p)]
    w = .75 ** np.arange(28)
    return np.convolve(p2p, w / w.sum(), mode="full")[:len(p2p)]


def scenario(model, d, history, multiplier):
    changed = d.copy()
    values = np.r_[history, d.p2p.to_numpy() * multiplier]
    changed[model.feature] = exposure(values, model.feature)[len(history):]
    return model.predict(changed), changed[model.feature].to_numpy()


def build_payload(result):
    selected = result["summary"]["selected"]
    payload = {"summary": result["summary"], "scores": result["scores"].to_dict("records"),
               "markets": {}, "months": sorted(result["panel"].loc[result["panel"].date.ge("2025-01-01"), "date"].dt.strftime("%Y-%m").unique())}
    for market, d in result["panel"].groupby("market"):
        model = result["fits"][selected][market]
        if model.kind == "gam":
            grid = np.linspace(0, np.log1p(max(d.p2p.max(), model.train_range[1]) * 100 + 1), 4097)
            curve = {"log_x": grid.tolist(), "effect": model.effect(np.expm1(grid)).tolist()}
        else:
            curve = None
        entry = {"linked": model.linked, "kind": model.kind, "feature": model.feature,
                 "training_range": model.train_range, "curve": curve,
                 "elasticity": float(model.coef[-1]) if model.kind == "linear" else None,
                 "months": {}}
        for month, period in d.loc[d.date.ge("2025-01-01")].groupby(d.date.dt.strftime("%Y-%m")):
            prior = d.loc[d.date.lt(period.date.min()), "p2p"].tail(27).to_numpy()
            base_pred, base_exposure = scenario(model, period, prior, 1)
            seats, pax, ex, flights = [float(period[v].sum()) for v in ["seats", "pax", "pax_ex_infant", "flights"]]
            incomplete_infants = int(period.infant_count_missing.sum()) > 0
            if incomplete_infants:
                ex = pax
            base = {"frequency": flights / len(period) * 7,
                    "gauge": seats / flights if flights else 0,
                    "load": ex / seats if seats else 0,
                    "nonlocal": float((period.transfer.sum() + period.transit.sum()) / pax) if pax else 0,
                    "infant_multiplier": pax / ex if ex else 1,
                    "infant_fallback": incomplete_infants}
            entry["months"][month] = {"dates": period.date.dt.strftime("%Y-%m-%d").tolist(),
                "split": period.split.iloc[0], "baseline": base,
                "p2p": period.p2p.tolist(), "history": prior.tolist(), "exposure": base_exposure.tolist(),
                "prediction": base_pred.tolist(),
                "actual": [float(x) if np.isfinite(x) else None for x in period.target],
                "chain_ratio": model.ratios[int(month[-2:])] if model.kind == "chain" else None}
        payload["markets"][market] = entry
    # Strict JSON also catches non-finite forecasts before shipping a demo.
    json.dumps(payload, allow_nan=False)
    return payload


def export_demo(result):
    payload = build_payload(result)
    demo = ROOT / "demo"
    demo.mkdir(exist_ok=True)
    raw = json.dumps(payload, separators=(",", ":"), allow_nan=False)
    (OUT / "demo_payload.json").write_text(raw)
    html = (demo / "template.html").read_text()
    html = html.replace("/*__ENGINE__*/", (demo / "engine.js").read_text())
    html = html.replace("/*__UI__*/", (demo / "ui.js").read_text())
    html = html.replace("/*__DATA__*/", "const DATA=" + raw.replace("</", "<\\/") + ";")
    (demo / "index.html").write_text(html)
    return payload
