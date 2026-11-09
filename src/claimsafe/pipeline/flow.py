"""The same steps orchestrated by Prefect, for scheduled runs next to the dbt and BigQuery flows."""

from __future__ import annotations

import tempfile
from pathlib import Path

from prefect import flow, task

from claimsafe.pipeline import steps


@task(retries=2, retry_delay_seconds=10)
def extract_orders(path: str, source: str) -> dict:
    return steps.extract_orders(path, source)


@task
def build_features(orders: str, path: str) -> dict:
    return steps.build_features(orders, path)


@task
def train(features: str, path: str, as_of_day: int) -> dict:
    return steps.train(features, path, as_of_day)


@task
def evaluate(features: str, model: str, as_of_day: int, path: str) -> dict:
    return steps.evaluate(features, model, as_of_day, path)


@task
def gate(metrics: str) -> bool:
    return steps.gate(metrics)


@flow(name="replenishment-run-out")
def replenishment_flow(as_of_day: int = 360, source: str = "simulated", workdir: str | None = None) -> dict:
    wd = Path(workdir or tempfile.mkdtemp(prefix="claimsafe-"))
    orders, feats, model, metrics = (
        str(wd / n) for n in ("orders.parquet", "features.parquet", "model.json", "metrics.json")
    )
    o = extract_orders(orders, source)
    f = build_features(orders, feats)
    t = train(feats, model, as_of_day)
    e = evaluate(feats, model, as_of_day, metrics)
    passed = gate(metrics)
    return {"orders": o, "features": f, "train": t, "evaluate": e, "passed_gate": passed, "workdir": str(wd)}
