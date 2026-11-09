"""Erasure across every store, the Vertex AI pipeline spec, the Prefect flow, and the HTTP API."""

from __future__ import annotations

import pytest
import yaml
from fastapi.testclient import TestClient

from claimsafe.api import create_app
from claimsafe.gdpr import DEV_KEY, pseudonym
from claimsafe.pipeline import steps
from claimsafe.pipeline.flow import replenishment_flow
from claimsafe.pipeline.vertex import compile_pipeline
from claimsafe.replenish import model as M
from claimsafe.replenish.registry import Registry
from claimsafe.replenish.simulate import simulate
from claimsafe.settings import ROOT
from claimsafe.warehouse import Warehouse, purge_superseded


def test_pseudonyms_are_keyed_and_normalised():
    assert pseudonym(" Ann@Example.org ", DEV_KEY) == pseudonym("ann@example.org", DEV_KEY)
    assert pseudonym("ann@example.org", DEV_KEY) != pseudonym("ann@example.org", b"other-key")


def test_erasure_reaches_every_store(small):
    world = simulate(small)
    wh = Warehouse.from_frames(world.identities, world.orders)
    feats = wh.con.execute("SELECT * FROM features").df()
    reg = Registry()
    rows = M.labelled(feats[feats.day < 360], as_of_day=330)
    reg.add(M.train(rows, small), "champion", 360, M.fingerprint(rows), {}, "v1", rows.customer.tolist())
    email = world.identities.email.iloc[3]
    c = pseudonym(email, DEV_KEY)
    assert wh.count("orders", c) > 0 and c in reg.get(1).customers and wh.in_index(c)
    er = wh.erase(email, DEV_KEY, reg, today=400, retrain_days=30)
    assert er.deleted["personalisation_index"] == 1
    audit = wh.audit(c, reg)
    assert audit["identities"] == audit["orders"] == audit["features"] == audit["personalisation_index"] == 0
    assert audit["model_manifests"] == [1] and reg.get(1).retrain_due_day == 430 and er.models_marked == [1]
    with pytest.raises(RuntimeError):
        purge_superseded(reg, {c})  # the champion still learned from the customer
    feats = wh.con.execute("SELECT * FROM features").df()
    rows = M.labelled(feats[feats.day < 400], as_of_day=370)
    v2 = reg.add(
        M.train(rows, small),
        "challenger",
        400,
        M.fingerprint(rows),
        {},
        "retrain after erasure",
        rows.customer.tolist(),
    )
    reg.promote(v2.version, 400, "erasure retrain")
    assert purge_superseded(reg, {c}) == [1]
    assert wh.audit(c, reg)["model_manifests"] == [] and 1 not in reg.models


def test_vertex_pipeline_compiles_to_the_committed_spec(tmp_path):
    out = compile_pipeline(tmp_path / "p.yaml")
    spec = yaml.safe_load(out.read_text())
    committed = yaml.safe_load((ROOT / "pipelines" / "replenishment.yaml").read_text())
    assert spec["root"] == committed["root"] and spec["components"].keys() == committed["components"].keys()
    assert {"comp-train", "comp-evaluate", "comp-register", "comp-condition-1"} <= set(spec["components"])


def test_pipeline_steps_end_to_end(tmp_path, small, monkeypatch):
    monkeypatch.setattr(steps, "simulate", lambda: simulate(small))
    o, f, m, e = (str(tmp_path / n) for n in ("o.parquet", "f.parquet", "m.json", "e.json"))
    assert steps.extract_orders(o)["rows"] > 1000
    steps.build_features(o, f)
    steps.train(f, m, 360)
    res = steps.evaluate(f, m, 360, e)
    assert res["challenger"]["mae_days"] < res["rule"]["mae_days"] and steps.gate(e)


def test_prefect_flow_wraps_the_same_steps():
    assert replenishment_flow.name == "replenishment-run-out"
    assert replenishment_flow.fn.__module__ == "claimsafe.pipeline.flow"


def test_http_api():
    client = TestClient(create_app())
    r = client.post(
        "/api/check", json={"product": "P07", "text": "Magnesium contributes to a reduction of tiredness and fatigue."}
    )
    assert r.json()["verdict"] == "block" and r.json()["safe_text"] == ""
    assert client.post("/api/check", json={"product": "X", "text": "hi"}).status_code == 404
    ans = client.post("/api/advise", json={"q": "omega 3 for my heart"}).json()["answers"]
    assert ans and all("heart" in a["text"] for a in ans)
    assert client.post("/api/search", json={"q": "x"}).status_code == 422  # too short
    assert client.post("/api/search", json={"q": "bones"}).json()["results"]


def test_nothing_in_src_reads_the_evaluation_labels():
    for p in (ROOT / "src").rglob("*.py"):
        assert "data/eval" not in p.read_text() and "heldout.yaml" not in p.read_text(), p
