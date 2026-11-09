"""Run-out model, point-in-time features, BigQuery SQL, drift and the release policy."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import sqlglot

from claimsafe.replenish import features as F
from claimsafe.replenish import model as M
from claimsafe.replenish.monitor import psi, replay
from claimsafe.replenish.simulate import simulate


@pytest.fixture(scope="module")
def world(small):
    return simulate(small)


@pytest.fixture(scope="module")
def feats(world):
    return F.build(world.orders)


def test_features_use_only_the_past(world, feats):
    cut = 300
    early = F.build(world.orders[world.orders.day < cut])
    cols = ["order_id", "last_ratio", "customer_mean_ratio", "customer_prior_orders", "n_this_product"]
    a = feats[feats.day < cut][cols].set_index("order_id").sort_index()
    b = early[cols].set_index("order_id").sort_index()
    pd.testing.assert_frame_equal(a, b, check_dtype=False)


def test_bigquery_sql_parses_as_bigquery():
    sql = F.bigquery_sql("commerce")
    tree = sqlglot.parse_one(sql, read="bigquery")
    assert "commerce.orders" in sql and "NULLS LAST" not in sql and tree is not None


def test_model_beats_the_pack_size_rule_and_round_trips(feats, small):
    t0 = 360
    model = M.train(M.labelled(feats[feats.day < t0], as_of_day=t0 - 30), small)
    hold = feats[(feats.label_known_day >= t0 - 30) & (feats.label_known_day < t0)]
    assert M.metrics(model, hold, small)["mae_days"] < M.metrics(M.rule(), hold, small)["mae_days"]
    again = M.from_bytes(M.model_bytes(model))
    assert np.allclose(again.predict(hold), model.predict(hold))


def test_psi():
    rng = np.random.default_rng(0)
    a = pd.Series(rng.normal(0, 1, 5000), name="x")
    assert psi(a, pd.Series(rng.normal(0, 1, 5000), name="x")) < 0.02
    assert psi(a, pd.Series(rng.normal(1.5, 1, 5000), name="x")) > 0.5
    c = pd.Series(["a"] * 90 + ["b"] * 10, name="channel")
    assert psi(c, pd.Series(["a"] * 40 + ["b"] * 60, name="channel")) > 0.2


def test_replay_rolls_back_a_bad_release_and_retrains_on_drift(small, feats):
    res = replay(small.replace(monitoring={"min_labels_for_decision": 60}), bad_release_month=17, df=feats)
    events = [e["event"] for e in res["registry"].events]
    assert "rolled back" in events
    bad = next(v for v in res["registry"].versions if v.data_fingerprint == "corrupted")
    assert bad.status == "rolled_back"
    assert any("retrain" in v.reason for v in res["registry"].versions)
    assert res["served_mae_days"] < res["served_rule_mae_days"]
