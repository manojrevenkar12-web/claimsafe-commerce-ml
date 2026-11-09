"""Monitoring and the production replay: drift, delayed labels, retraining triggers, the gate and rollback."""

from __future__ import annotations

import numpy as np
import pandas as pd

from claimsafe.replenish import model as M
from claimsafe.replenish.features import CATEGORICAL, NUMERIC, build
from claimsafe.replenish.registry import Registry
from claimsafe.replenish.simulate import DAYS_PER_MONTH, simulate
from claimsafe.settings import Settings, load

PSI_FEATURES = ["channel", "supply_days", "last_ratio", "customer_mean_ratio", "subscriber", "qty"]
EPS = 1e-4


def psi(expected: pd.Series, actual: pd.Series, bins: int = 10) -> float:
    if expected.name in CATEGORICAL or expected.dtype == object:
        cats = sorted(set(expected.astype(str)) | set(actual.astype(str)))
        e = expected.astype(str).value_counts(normalize=True).reindex(cats, fill_value=0).to_numpy()
        a = actual.astype(str).value_counts(normalize=True).reindex(cats, fill_value=0).to_numpy()
    else:
        ex, ac = expected.dropna().to_numpy(dtype=float), actual.dropna().to_numpy(dtype=float)
        if len(ex) == 0 or len(ac) == 0:
            return 0.0
        edges = np.unique(np.quantile(ex, np.linspace(0, 1, bins + 1)))
        if len(edges) < 3:
            return 0.0
        e = np.histogram(np.clip(ex, edges[0], edges[-1]), edges)[0] / len(ex)
        a = np.histogram(np.clip(ac, edges[0], edges[-1]), edges)[0] / len(ac)
    e, a = np.clip(e, EPS, None), np.clip(a, EPS, None)
    return float(np.sum((a - e) * np.log(a / e)))


def replay(
    settings: Settings | None = None, bad_release_month: int | None = 17, df: pd.DataFrame | None = None
) -> dict:
    s = settings or load()
    r, mon, gate = s.replenish, s.monitoring, s.gate
    if df is None:
        df = build(simulate(s).orders)
    t0 = r.train_months * DAYS_PER_MONTH
    reg = Registry()
    # Release v1: train on labels known a month before t0, judge on the last month's matured labels.
    hold = df[(df.label_known_day >= t0 - DAYS_PER_MONTH) & (df.label_known_day < t0)]
    train_rows = M.labelled(df[df.day < t0], as_of_day=t0 - DAYS_PER_MONTH)
    v1_model = M.train(train_rows, s)
    rule_hold = M.metrics(M.rule(), hold, s)
    v1_hold = M.metrics(v1_model, hold, s)
    v1_hold["skill"] = round(v1_hold["mae_days"] / rule_hold["mae_days"], 4)
    reg.add(
        v1_model,
        "champion",
        t0,
        M.fingerprint(train_rows),
        v1_hold,
        f"MAE {v1_hold['mae_days']} vs {rule_hold['mae_days']} for the pack-size rule",
        train_rows.customer.tolist(),
    )
    reference = df[df.day < t0]
    preds = pd.Series(np.nan, index=df.index)
    served_by = pd.Series(0, index=df.index)
    months = []
    for m in range(r.train_months + 1, r.months + 1):
        start, end = (m - 1) * DAYS_PER_MONTH, m * DAYS_PER_MONTH
        actions = []
        if bad_release_month and m == bad_release_month:
            bad = M.train(M.labelled(df[df.day < start], as_of_day=start), s, corrupt_labels=True)
            v = reg.add(bad, "challenger", start, "corrupted", {}, "hotfix release that skipped the gate", [])
            reg.promote(v.version, start, "deployed without the gate (rehearsal of a bad release)")
            actions.append(f"v{v.version} deployed without the gate")
        champ = reg.champion()
        idx = df.index[(df.day >= start) & (df.day < end)]
        preds.loc[idx] = reg.models[champ.version].predict(df.loc[idx])
        served_by.loc[idx] = champ.version
        # Labels that arrived this month, for orders this replay served.
        matured = df[(df.label_known_day >= start) & (df.label_known_day < end) & preds.notna()]
        live = {}
        if len(matured):
            err = np.abs(preds[matured.index] - matured.label_days)
            rule_err = np.abs(matured.supply_days - matured.label_days)
            live = {
                "n": len(matured),
                "mae_days": round(float(err.mean()), 3),
                "rule_mae_days": round(float(rule_err.mean()), 3),
            }
            live["skill"] = round(live["mae_days"] / live["rule_mae_days"], 4)
            by_version = {}
            for ver in sorted(set(served_by[matured.index])):
                sel = matured.index[served_by[matured.index] == ver]
                e = float(np.abs(preds[sel] - matured.label_days[sel]).mean())
                rule_e = float(np.abs(matured.supply_days[sel] - matured.label_days[sel]).mean())
                by_version[int(ver)] = {"n": len(sel), "mae_days": round(e, 3), "skill": round(e / rule_e, 4)}
            live["by_version"] = {str(k): v for k, v in by_version.items()}
        current = df.loc[idx]
        drift = {f: round(psi(reference[f], current[f]), 4) for f in PSI_FEATURES}
        alerts = [f for f, v in drift.items() if v > mon.psi_alert]
        # Rollback: the version serving now is clearly worse than the one before it, on its own labels.
        champ = reg.champion()
        own = live.get("by_version", {}).get(str(champ.version))
        prev = [v for v in reg.versions if v.status == "retired"]
        if own and prev and own["n"] >= mon.min_labels_for_decision:
            prev_skill = prev[-1].release_metrics.get("skill")
            if prev_skill and own["skill"] > prev_skill * (1 + mon.rollback_degradation):
                back = reg.rollback(
                    end,
                    f"live error {own['skill']:.2f}x the rule's vs {prev_skill:.2f}x for "
                    f"v{prev[-1].version} at release",
                )
                actions.append(f"rolled back v{champ.version} to v{back.version}")
        # Retrain: the champion's live error has drifted away from what it was released with.
        champ = reg.champion()
        own = live.get("by_version", {}).get(str(champ.version))
        released = champ.release_metrics.get("skill")
        degraded = bool(
            own
            and released
            and own["n"] >= mon.min_labels_for_decision
            and own["skill"] > released * (1 + mon.mae_degradation_alert)
        )
        recent = (
            [x["psi_alerts"] for x in months[-(mon.drift_months_before_retrain - 1) :]]
            if mon.drift_months_before_retrain > 1
            else []
        )
        drifted = (
            bool(alerts)
            and all(recent)
            and len(recent) == mon.drift_months_before_retrain - 1
            and champ.trained_through_day < start
        )
        if degraded or drifted:
            why = (
                f"live error {own['skill']:.2f}x the rule's vs {released:.2f}x at release"
                if degraded
                else f"drift in {', '.join(alerts)} for {mon.drift_months_before_retrain} months"
            )
            holdout = df[(df.label_known_day >= end - DAYS_PER_MONTH) & (df.label_known_day < end)]
            rows = M.labelled(df[df.day < end], as_of_day=end - DAYS_PER_MONTH)
            challenger = M.train(rows, s)
            ch_m, champ_m = M.metrics(challenger, holdout, s), M.metrics(reg.models[champ.version], holdout, s)
            ch_m["skill"] = round(ch_m["mae_days"] / M.metrics(M.rule(), holdout, s)["mae_days"], 4)
            better = ch_m["mae_days"] <= champ_m["mae_days"] * (1 - gate.min_mae_improvement)
            v = reg.add(
                challenger,
                "challenger",
                end,
                M.fingerprint(rows),
                ch_m,
                f"retrain ({why}); holdout MAE {ch_m['mae_days']:.1f} vs champion {champ_m['mae_days']:.1f}",
                rows.customer.tolist(),
            )
            if better:
                reg.promote(v.version, end, "passed the gate")
                actions.append(
                    f"retrained: v{v.version} promoted (holdout MAE {ch_m['mae_days']:.1f} vs "
                    f"{champ_m['mae_days']:.1f})"
                )
            else:
                v.status = "rejected"
                actions.append(f"retrained: v{v.version} rejected by the gate")
        months.append(
            {
                "month": m,
                "orders": len(idx),
                "live": live,
                "psi": drift,
                "psi_alerts": alerts,
                "champion": reg.champion().version,
                "actions": actions,
            }
        )
    served = df[preds.notna() & df.label_days.notna()]
    return {
        "release": {"rule_holdout": rule_hold, "v1_holdout": v1_hold},
        "months": months,
        "registry": reg,
        "served_mae_days": round(float(np.abs(preds[served.index] - served.label_days).mean()), 3),
        "served_rule_mae_days": round(float(np.abs(served.supply_days - served.label_days).mean()), 3),
        "numeric_features": NUMERIC,
    }
