"""The run-out model: days until a customer reorders the same product, and the reminder timing it implies."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

import lightgbm as lgb
import numpy as np
import pandas as pd

from claimsafe.replenish.features import CATEGORICAL, NUMERIC
from claimsafe.settings import Settings, load


@dataclass
class RunOutModel:
    booster: lgb.Booster | None
    categories: dict[str, list[str]]
    name: str = "lightgbm"

    def frame(self, df: pd.DataFrame) -> pd.DataFrame:
        x = df[NUMERIC + CATEGORICAL].copy()
        for c in CATEGORICAL:
            x[c] = pd.Categorical(x[c].astype(str), categories=self.categories[c])
        return x

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        if self.booster is None:  # the rule the shop uses today: the pack lasts as long as the label says
            return df["supply_days"].to_numpy(dtype=float)
        return np.expm1(self.booster.predict(self.frame(df)))


def rule() -> RunOutModel:
    return RunOutModel(None, {}, name="pack-size rule")


def labelled(df: pd.DataFrame, as_of_day: int | None = None) -> pd.DataFrame:
    """Rows whose label is known (by `as_of_day`, if given)."""
    out = df[df["label_days"].notna()]
    if as_of_day is not None:
        out = out[out["label_known_day"] <= as_of_day]
    return out


def train(df: pd.DataFrame, settings: Settings | None = None, corrupt_labels: bool = False) -> RunOutModel:
    s = (settings or load()).replenish
    data = labelled(df)
    cats = {c: sorted(df[c].astype(str).unique().tolist()) for c in CATEGORICAL}
    m = RunOutModel(None, cats)
    y = np.log1p(data["label_days"].to_numpy(dtype=float))
    if corrupt_labels:  # used only to rehearse a bad release and its rollback
        y = np.random.default_rng(0).permutation(y)
    params = {
        "objective": "l1",
        "learning_rate": s.lgbm_learning_rate,
        "num_leaves": s.lgbm_num_leaves,
        "min_data_in_leaf": 40,
        "verbose": -1,
        "seed": s.seed,
        "deterministic": True,
        "num_threads": 1,
    }
    m.booster = lgb.train(params, lgb.Dataset(m.frame(data), y), num_boost_round=s.lgbm_rounds)
    return m


def metrics(model: RunOutModel, df: pd.DataFrame, settings: Settings | None = None) -> dict:
    s = (settings or load()).replenish
    data = labelled(df)
    if data.empty:
        return {"n": 0}
    pred = model.predict(data)
    actual = data["label_days"].to_numpy(dtype=float)
    err = np.abs(pred - actual)
    reminder = pred - s.reminder_lead_days
    on_time = (actual >= reminder) & (actual <= reminder + s.on_time_window_days)
    late = actual < reminder  # the customer had already reordered (or run out) before we wrote
    return {
        "n": len(data),
        "mae_days": round(float(err.mean()), 3),
        "within_7_days": round(float((err <= 7).mean()), 4),
        "reminders_on_time": round(float(on_time.mean()), 4),
        "reminders_too_late": round(float(late.mean()), 4),
    }


def fingerprint(df: pd.DataFrame) -> str:
    cols = ["order_id", "customer", "product", "day", "label_days"]
    h = hashlib.sha256(pd.util.hash_pandas_object(df[cols], index=False).values.tobytes()).hexdigest()
    return h[:16]


def model_bytes(m: RunOutModel) -> bytes:
    if m.booster is None:
        return b'{"rule": true}'
    return json.dumps({"booster": m.booster.model_to_string(), "categories": m.categories}, sort_keys=True).encode()


def from_bytes(raw: bytes) -> RunOutModel:
    d = json.loads(raw)
    if d.get("rule"):
        return rule()
    return RunOutModel(lgb.Booster(model_str=d["booster"]), d["categories"])
