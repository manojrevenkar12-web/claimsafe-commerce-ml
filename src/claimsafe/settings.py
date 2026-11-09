"""Settings from config/claimsafe.toml, validated strictly."""

from __future__ import annotations

import tomllib
from functools import cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parents[2]


class _S(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Claims(_S):
    register_file: str
    paraphrases: str
    min_rewrite_similarity: float = Field(ge=0, le=1)


class Catalog(_S):
    seed: int


class Search(_S):
    k: int = Field(ge=1)
    lsa_components: int = Field(ge=2)
    hybrid_weight_dense: float = Field(ge=0, le=1)


class Advisor(_S):
    max_products: int = Field(ge=1)
    llm_model: str
    llm_max_tokens: int = Field(ge=50, le=2000)
    llm_timeout_s: float = Field(gt=0)


class Replenish(_S):
    seed: int
    customers: int = Field(ge=100)
    months: int = Field(ge=6)
    train_months: int = Field(ge=3)
    reminder_lead_days: int = Field(ge=0)
    on_time_window_days: int = Field(ge=1)
    lgbm_rounds: int = Field(ge=10)
    lgbm_learning_rate: float = Field(gt=0)
    lgbm_num_leaves: int = Field(ge=2)


class Monitoring(_S):
    psi_alert: float = Field(gt=0)
    mae_degradation_alert: float = Field(gt=0)
    rollback_degradation: float = Field(gt=0)
    min_labels_for_decision: int = Field(ge=1)
    drift_months_before_retrain: int = Field(ge=1)


class Gate(_S):
    min_mae_improvement: float = Field(ge=0)


class Gdpr(_S):
    pseudonym_key_env: str
    retrain_after_erasure_days: int = Field(ge=1)


class Store(_S):
    root: str


class Settings(_S):
    claims: Claims
    catalog: Catalog
    search: Search
    advisor: Advisor
    replenish: Replenish
    monitoring: Monitoring
    gate: Gate
    gdpr: Gdpr
    store: Store

    def path(self, rel: str) -> Path:
        return ROOT / rel

    def replace(self, **sections: dict) -> Settings:
        data = self.model_dump()
        for k, v in sections.items():
            data[k] = {**data[k], **v}
        return Settings.model_validate(data)


@cache
def load(path: str | None = None) -> Settings:
    with open(path or ROOT / "config" / "claimsafe.toml", "rb") as fh:
        return Settings.model_validate(tomllib.load(fh))
