"""Integration checks on real fits, temporal boundaries and exported predictions."""
import json
import subprocess

import numpy as np

from .models import ROOT, OUT
from .scenario import scenario


def verify(result, payload):
    checks = []
    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        checks.append(name)

    panel = result["panel"]
    check("raw missing targets remain missing in audit", panel.loc[panel.split.eq("audit"), "target"].isna().sum() > 0)
    check("45 nationality models / 33 direct matches", len(payload["markets"]) == 45 and sum(m["linked"] for m in payload["markets"].values()) == 33)
    check("all candidate response gates pass", result["gates"].passed.all())
    check("training precedes selection", panel.loc[panel.split.eq("train"), "date"].max() < panel.loc[panel.split.eq("selection"), "date"].min())
    check("calibration precedes audit", panel.loc[panel.split.eq("calibration"), "date"].max() < panel.loc[panel.split.eq("audit"), "date"].min())
    fixtures = []
    selected = result["summary"]["selected"]
    for market, m in payload["markets"].items():
        model = result["fits"][selected][market]
        market_panel = panel.loc[panel.market.eq(market)]
        for month, p in m["months"].items():
            d = market_panel.loc[market_panel.date.dt.strftime("%Y-%m").eq(month)]
            baseline = np.array(p["prediction"])
            check(f"{market}/{month}: export baseline matches direct fitted model",
                  np.allclose(baseline, model.predict(d), rtol=1e-9, atol=1e-7))
            b = p["baseline"]
            reconstructed = b["frequency"] / 7 * len(d) * b["gauge"] * b["load"] * b["infant_multiplier"] * (1-b["nonlocal"])
            check(f"{market}/{month}: seat-passenger identity", np.isclose(reconstructed, d.p2p.sum(), rtol=1e-9, atol=1e-7))
            previous = None
            for multiplier in [0, .5, 1, 1.2, 2]:
                prediction, x = scenario(model, d, p["history"], multiplier)
                check(f"{market}/{month}/{multiplier}: finite nonnegative", np.isfinite(prediction).all() and (prediction >= 0).all())
                if previous is not None:
                    check(f"{market}/{month}/{multiplier}: schedule monotonicity", (prediction >= previous-1e-5).all())
                previous = prediction
                if multiplier == 0 and model.linked and model.feature == "p2p_7d":
                    check(f"{market}/{month}: pre-scenario history persists then expires", np.isclose(x[6:], 0).all() and (sum(p["history"][-6:]) == 0 or x[0] > 0))
                fixtures.append({"market": market, "month": month, "multiplier": multiplier, "prediction": prediction.tolist()})
    fixture_path = OUT / "scenario_fixtures.json"
    fixture_path.write_text(json.dumps(fixtures, allow_nan=False))
    executed = subprocess.run(["node", str(ROOT / "tests/scenario.test.cjs"), str(OUT / "demo_payload.json"), str(fixture_path)], check=True, capture_output=True, text=True)
    print(executed.stdout)
    check("JavaScript predictions and four-slider sweeps", executed.returncode == 0)
    (OUT / "verification.json").write_text(json.dumps({"python_checks": len(checks), "node": json.loads(executed.stdout), "passed": True}, indent=2))
    print(f"Passed {len(checks):,} Python integration checks.")
    return {"checks": len(checks), "passed": True}
