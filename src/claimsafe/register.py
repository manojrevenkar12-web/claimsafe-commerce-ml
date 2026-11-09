"""The authorised health claims (Regulation (EU) No 432/2012) and which of them a product may carry.

Eligibility is decided from the product's composition per recommended daily dose, never from its marketing text.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from pathlib import Path

import yaml

from claimsafe.settings import ROOT, load

COMPOSITE = {"epa_dha": ("epa", "dha")}


@dataclass(frozen=True)
class Nutrient:
    key: str
    name: str
    unit: str
    nrv: float | None
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class Claim:
    id: str
    nutrient: str
    text: str
    kind: str  # source_nrv | min_daily
    amounts: tuple[tuple[str, float], ...] = ()
    statement: str | None = None
    not_for_children: bool = False


@dataclass(frozen=True)
class Register:
    nutrients: dict[str, Nutrient]
    claims: tuple[Claim, ...]
    source_share: float
    source: str

    def claims_for(self, nutrient: str) -> list[Claim]:
        return [c for c in self.claims if c.nutrient == nutrient]

    def amount(self, composition: dict[str, float], key: str) -> float:
        if "+" in key:
            return sum(composition.get(k, 0.0) for k in key.split("+"))
        return composition.get(key, 0.0)

    def condition_met(
        self, claim: Claim, composition: dict[str, float], for_children: bool = False
    ) -> tuple[bool, str]:
        if claim.not_for_children and for_children:
            return False, "this claim may not be used for products aimed at children"
        if claim.kind == "source_nrv":
            n = self.nutrients[claim.nutrient]
            have = composition.get(claim.nutrient, 0.0)
            need = self.source_share * float(n.nrv or 0)
            if have + 1e-12 < need:
                share = have / n.nrv if n.nrv else 0
                return False, (
                    f"{n.name}: {have:g} {n.unit} per daily dose is {share:.0%} of the NRV; "
                    f"a claim needs at least {self.source_share:.0%} ({need:g} {n.unit})"
                )
            return True, f"{n.name} {have:g} {n.unit} per daily dose ({have / n.nrv:.0%} NRV)"
        for key, need in claim.amounts:
            have = self.amount(composition, key)
            if have + 1e-12 < need:
                return False, f"{key.upper()}: {have:g} mg per daily dose; this claim needs {need:g} mg"
        return True, "daily amount met"

    def eligible(self, composition: dict[str, float], for_children: bool = False) -> list[Claim]:
        return [c for c in self.claims if self.condition_met(c, composition, for_children)[0]]

    def alias_index(self) -> list[tuple[str, str]]:
        """(alias, nutrient key), longest alias first so 'vitamin d3' wins over 'vitamin d'."""
        out = [(a, n.key) for n in self.nutrients.values() for a in n.aliases]
        out += [("epa and dha", "epa_dha"), ("dha and epa", "epa_dha"), ("omega-3", "epa_dha"), ("omega 3", "epa_dha")]
        return sorted(out, key=lambda x: -len(x[0]))


@cache
def load_register(path: str | None = None) -> Register:
    p = Path(path) if path else ROOT / load().claims.register_file
    raw = yaml.safe_load(p.read_text())
    nutrients = {
        k: Nutrient(k, v["name"], v["unit"], v["nrv"], tuple(v["aliases"])) for k, v in raw["nutrients"].items()
    }
    claims = []
    for c in raw["claims"]:
        cond = c["condition"]
        claims.append(
            Claim(
                id=c["id"],
                nutrient=c["nutrient"],
                text=c["text"],
                kind=cond["kind"],
                amounts=tuple((k, float(v)) for k, v in (cond.get("amounts") or {}).items()),
                statement=cond.get("statement"),
                not_for_children=bool(cond.get("not_for_children", False)),
            )
        )
    return Register(
        nutrients, tuple(claims), float(raw["source_condition"]["significant_amount_share_of_nrv"]), raw["source"]
    )
