"""The local warehouse (DuckDB standing in for BigQuery), the personalisation index, and erasure across both.

Erasure of one customer: identity row, order rows, feature rows and personalisation vector are deleted; model
versions trained on the customer are marked for retraining by a due date; the audit then searches every store for
the pseudonym and reports what is left, which must be nothing except those marked model manifests until retraining.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb
import faiss
import numpy as np
import pandas as pd

from claimsafe.gdpr import pseudonym
from claimsafe.replenish.features import build
from claimsafe.replenish.registry import Registry


@dataclass
class Erasure:
    customer: str
    deleted: dict[str, int]
    models_marked: list[int]
    retrain_due_day: int


class Warehouse:
    def __init__(self, path: Path | str = ":memory:"):
        self.con = duckdb.connect(str(path))
        self.ids: dict[str, int] = {}
        self.index: faiss.IndexIDMap | None = None

    def load(self, identities: pd.DataFrame, orders: pd.DataFrame) -> None:
        self.con.execute("CREATE OR REPLACE TABLE identities AS SELECT * FROM identities_df")
        self.con.execute("CREATE OR REPLACE TABLE orders AS SELECT * FROM orders_df")
        self.con.execute("CREATE OR REPLACE TABLE features AS SELECT * FROM features_df")

    @classmethod
    def from_frames(cls, identities: pd.DataFrame, orders: pd.DataFrame, path: Path | str = ":memory:") -> Warehouse:
        w = cls(path)
        features_df = build(orders)
        w.con.register("identities_df", identities)
        w.con.register("orders_df", orders)
        w.con.register("features_df", features_df)
        w.load(identities, orders)
        for name in ("identities_df", "orders_df", "features_df"):
            w.con.unregister(name)
        w.build_index()
        return w

    def build_index(self) -> None:
        """One vector per customer: the share of each product in their orders (for 'more like what you buy')."""
        df = self.con.execute("SELECT customer, product, SUM(qty) AS n FROM orders GROUP BY 1, 2").df()
        piv = df.pivot_table(index="customer", columns="product", values="n", fill_value=0)
        vecs = piv.to_numpy(dtype="float32")
        faiss.normalize_L2(vecs)
        self.ids = {c: i for i, c in enumerate(piv.index)}
        self.products = list(piv.columns)
        self.index = faiss.IndexIDMap(faiss.IndexFlatIP(vecs.shape[1]))
        self.index.add_with_ids(vecs, np.arange(len(piv), dtype="int64"))

    def count(self, table: str, customer: str) -> int:
        return int(self.con.execute(f"SELECT COUNT(*) FROM {table} WHERE customer = ?", [customer]).fetchone()[0])

    def in_index(self, customer: str) -> bool:
        """Read the index's own id map, so the audit checks what FAISS holds, not what we think it holds."""
        if customer not in self.ids or self.index is None:
            return False
        return bool(np.isin(self.ids[customer], faiss.vector_to_array(self.index.id_map)))

    def erase(self, email: str, key: bytes, registry: Registry | None, today: int, retrain_days: int) -> Erasure:
        c = pseudonym(email, key)
        deleted = {t: self.count(t, c) for t in ("identities", "orders", "features")}
        for t in deleted:
            self.con.execute(f"DELETE FROM {t} WHERE customer = ?", [c])
        if self.in_index(c):
            self.index.remove_ids(np.array([self.ids[c]], dtype="int64"))
            deleted["personalisation_index"] = 1
        marked = []
        if registry:
            for v in registry.versions:
                if c in v.customers:
                    v.retrain_due_day = (
                        today + retrain_days
                        if v.retrain_due_day is None
                        else min(v.retrain_due_day, today + retrain_days)
                    )
                    marked.append(v.version)
        return Erasure(c, deleted, marked, today + retrain_days)

    def audit(self, customer: str, registry: Registry | None = None) -> dict:
        found = {t: self.count(t, customer) for t in ("identities", "orders", "features")}
        found["personalisation_index"] = int(self.in_index(customer))
        found["model_manifests"] = [
            v.version for v in (registry.versions if registry else []) if customer in v.customers
        ]
        return found


def purge_superseded(registry: Registry, erased: set[str]) -> list[int]:
    """Once a champion trained without the erased customers is live, versions that still learned from them are
    retired: their model artifacts are deleted and the pseudonyms removed from their manifests."""
    purged = []
    champion = registry.champion()
    if erased & set(champion.customers):
        raise RuntimeError("the champion still contains erased customers; retrain first")
    for v in registry.versions:
        if erased & set(v.customers):
            v.customers = [c for c in v.customers if c not in erased]
            v.status = "retired" if v.status == "champion" else v.status
            v.retrain_due_day = None
            registry.models.pop(v.version, None)
            purged.append(v.version)
    return purged
