"""The product catalogue and what each product may legally claim."""

from __future__ import annotations

from functools import cache
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

from claimsafe.register import Claim, Register, load_register
from claimsafe.settings import ROOT

CATALOG = ROOT / "data" / "catalog" / "products.yaml"


class Product(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    name: str
    form: str
    units_per_pack: int
    daily_units: float
    price_eur: float
    category: str
    for_children: bool
    per_daily_dose: dict[str, float]
    marketing: str

    @property
    def days_of_supply(self) -> float:
        return self.units_per_pack / self.daily_units

    def eligible_claims(self, register: Register | None = None) -> list[Claim]:
        reg = register or load_register()
        return reg.eligible(self.per_daily_dose, self.for_children)

    def required_statements(self, claims: list[Claim]) -> list[str]:
        return sorted({c.statement for c in claims if c.statement})


@cache
def load_catalog(path: str | None = None) -> tuple[Product, ...]:
    raw = yaml.safe_load(Path(path or CATALOG).read_text())
    return tuple(Product.model_validate(p) for p in raw["products"])


def by_id(products: tuple[Product, ...] | None = None) -> dict[str, Product]:
    return {p.id: p for p in (products or load_catalog())}
