"""Pipeline steps as plain functions over files. Vertex AI Pipelines (pipeline/vertex.py) and Prefect
(pipeline/flow.py) both call these, so the code that runs in the cloud is the code the tests run."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from claimsafe.replenish import model as M
from claimsafe.replenish.features import build
from claimsafe.replenish.simulate import DAYS_PER_MONTH, simulate
from claimsafe.settings import load


def extract_orders(out_path: str, source: str = "simulated", project: str = "", dataset: str = "") -> dict:
    """Production reads `<dataset>.orders` from BigQuery; here the simulated history stands in."""
    if source == "bigquery":  # pragma: no cover - needs a GCP project
        from google.cloud import bigquery

        df = bigquery.Client(project=project).query(f"SELECT * FROM `{dataset}.orders`").to_dataframe()
    else:
        df = simulate().orders
    df.to_parquet(out_path, index=False)
    return {"rows": len(df), "fingerprint": M.fingerprint(df.assign(label_days=0))}


def build_features(orders_path: str, out_path: str) -> dict:
    feats = build(pd.read_parquet(orders_path))
    feats.to_parquet(out_path, index=False)
    return {"rows": len(feats), "labelled": int(feats.label_days.notna().sum())}


def train(features_path: str, model_path: str, as_of_day: int) -> dict:
    df = pd.read_parquet(features_path)
    rows = M.labelled(df[df.day < as_of_day], as_of_day=as_of_day - DAYS_PER_MONTH)
    model = M.train(rows, load())
    Path(model_path).write_bytes(M.model_bytes(model))
    return {"trained_on": len(rows), "data_fingerprint": M.fingerprint(rows)}


def evaluate(features_path: str, model_path: str, as_of_day: int, out_path: str) -> dict:
    df = pd.read_parquet(features_path)
    hold = df[(df.label_known_day >= as_of_day - DAYS_PER_MONTH) & (df.label_known_day < as_of_day)]
    model = load_model(model_path, df)
    res = {"challenger": M.metrics(model, hold), "rule": M.metrics(M.rule(), hold)}
    Path(out_path).write_text(json.dumps(res))
    return res


def gate(metrics_path: str) -> bool:
    m = json.loads(Path(metrics_path).read_text())
    need = 1 - load().gate.min_mae_improvement
    return m["challenger"]["mae_days"] <= m["rule"]["mae_days"] * need


def load_model(path: str, df: pd.DataFrame | None = None) -> M.RunOutModel:
    return M.from_bytes(Path(path).read_bytes())
