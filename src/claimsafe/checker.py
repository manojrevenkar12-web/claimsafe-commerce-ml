"""The claim checker: every sentence a customer could read, checked against the register and the product.

Verdicts per sentence:
  ok       no health claim, or an authorised claim in register wording whose conditions the product meets
  rewrite  a health claim the product may make, but not in authorised wording or without a required statement;
           the suggestion is register text only
  block    a disease claim, a claim for a substance with no authorised claim, or a claim the product's composition
           does not support

The checker is deterministic code. An LLM may draft copy; it never decides what is allowed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Literal

import yaml

from claimsafe.catalog import Product
from claimsafe.register import Claim, Register, load_register
from claimsafe.settings import ROOT, load

Verdict = Literal["ok", "rewrite", "block"]
SPLIT = re.compile(r"(?<=[.!?])\s+")
WORD = re.compile(r"[a-z0-9]+(?:[-'][a-z0-9]+)*")


@dataclass(frozen=True)
class Finding:
    sentence: str
    verdict: Verdict
    reason: str
    claim_ids: tuple[str, ...] = ()
    suggestion: str | None = None


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)

    @property
    def verdict(self) -> Verdict:
        vs = {f.verdict for f in self.findings}
        return "block" if "block" in vs else "rewrite" if "rewrite" in vs else "ok"

    def safe_text(self) -> str:
        """The text with blocked sentences removed and rewrites applied: what a customer may see."""
        out = []
        for f in self.findings:
            if f.verdict == "ok":
                out.append(f.sentence)
            elif f.verdict == "rewrite" and f.suggestion:
                out.append(f.suggestion)
        return " ".join(out)


@dataclass(frozen=True)
class Policy:
    link_verbs: frozenset[str]
    link_phrases: tuple[str, ...]
    function_terms: frozenset[str]
    disease_terms: frozenset[str]
    no_claim_substances: tuple[str, ...]
    synonyms: dict[str, str]
    generic_terms: frozenset[str]
    standalone_claim_terms: frozenset[str]
    approved: dict[str, str]


@cache
def load_policy() -> Policy:
    raw = yaml.safe_load((ROOT / "data" / "claims" / "policy.yaml").read_text())
    para = yaml.safe_load((ROOT / load().claims.paraphrases).read_text()) or {}
    return Policy(
        link_verbs=frozenset(raw["link_verbs"]),
        link_phrases=tuple(raw["link_phrases"]),
        function_terms=frozenset(raw["function_terms"]),
        disease_terms=frozenset(raw["disease_terms"]),
        no_claim_substances=tuple(raw["no_claim_substances"]),
        synonyms=dict(raw["synonyms"]),
        generic_terms=frozenset(raw["generic_terms"]),
        standalone_claim_terms=frozenset(raw["standalone_claim_terms"]),
        approved={k.lower(): v for k, v in (para.get("approved") or {}).items()},
    )


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().replace("’", "'")).strip().rstrip(".!? ")


def words(text: str) -> list[str]:
    return WORD.findall(text.lower())


def _stem(w: str) -> str:
    for suf in ("ing", "es", "s"):
        if len(w) > 4 and w.endswith(suf) and not w.endswith("ss"):
            return w[: -len(suf)]
    return w


class Checker:
    def __init__(
        self, register: Register | None = None, policy: Policy | None = None, rewrite_floor: float | None = None
    ):
        self.reg = register or load_register()
        self.pol = policy or load_policy()
        self.floor = load().claims.min_rewrite_similarity if rewrite_floor is None else rewrite_floor
        self.aliases = self.reg.alias_index()
        self.by_text = {norm(c.text): c for c in self.reg.claims}

    # ---- pieces ------------------------------------------------------------------------------------------

    def nutrients_in(self, sentence: str) -> list[str]:
        s = " " + norm(sentence) + " "
        found: list[str] = []
        for alias, key in self.aliases:
            pat = re.compile(r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])")
            if pat.search(s):
                s = pat.sub(" ", s)
                if key not in found:
                    found.append(key)
        return found

    def is_health_claim(self, sentence: str) -> bool:
        ws = set(words(sentence))
        if ws & self.pol.standalone_claim_terms:
            return True
        if not ws & (self.pol.function_terms | self.pol.disease_terms):
            return False
        low = " " + norm(sentence) + " "
        return bool(ws & self.pol.link_verbs) or any(p in low for p in self.pol.link_phrases)

    def disease_terms_in(self, sentence: str) -> list[str]:
        return sorted(set(words(sentence)) & self.pol.disease_terms)

    def substances_in(self, sentence: str) -> list[str]:
        low = norm(sentence)
        return [s for s in self.pol.no_claim_substances if re.search(r"(?<![a-z])" + re.escape(s) + r"(?![a-z])", low)]

    def function_tokens(self, text: str, drop_nutrients: bool = True) -> set[str]:
        low = norm(text)
        if drop_nutrients:
            for alias, _ in self.aliases:
                low = re.sub(r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])", " ", low)
        out = set()
        for w in words(low):
            w = self.pol.synonyms.get(w, w)
            if w in self.pol.generic_terms:
                continue
            out.add(_stem(w))
        return out

    def similarity(self, sentence: str, claim: Claim) -> float:
        """Share of the claim's function words that the sentence names."""
        want = self.function_tokens(claim.text)
        have = self.function_tokens(sentence)
        return len(want & have) / len(want) if want else 0.0

    # ---- the decision ------------------------------------------------------------------------------------

    def check_sentence(self, sentence: str, product: Product, full_text: str = "") -> Finding:
        s = sentence.strip()
        if not self.is_health_claim(s):
            return Finding(s, "ok", "no health claim")
        diseases = self.disease_terms_in(s)
        if diseases:
            return Finding(
                s,
                "block",
                f"medicinal claim: names {', '.join(diseases)}; food may not claim to prevent, "
                "treat or cure a disease (Reg. (EU) 1169/2011 Art. 7(3))",
            )
        nutrients = self.nutrients_in(s)
        approved = self.pol.approved.get(norm(s))
        if approved:
            claim = next(c for c in self.reg.claims if c.id == approved)
            return self._authorised([claim], s, product, full_text, "approved paraphrase")
        exact = self._exact(s, nutrients)
        if exact:
            return self._authorised(exact, s, product, full_text, "authorised wording")
        subs = self.substances_in(s)
        if subs and not nutrients:
            return Finding(s, "block", f"no authorised health claim exists for {', '.join(subs)}")
        return self._closest(s, nutrients, product)

    def _exact(self, s: str, nutrients: list[str]) -> list[Claim]:
        low = norm(s)
        if low in self.by_text:
            return [self.by_text[low]]
        # "Vitamin C, zinc and vitamin D contribute to X" = one authorised claim per nutrient.
        m = re.match(r"^(.*?)\s+(contribute|contributes|contribute to|has a role|have a role)\b(.*)$", low)
        if m and len(nutrients) > 1:
            rest = m.group(3).strip()
            claims = []
            for n in nutrients:
                name = self.reg.nutrients[n].name.lower() if n in self.reg.nutrients else ""
                c = self.by_text.get(norm(f"{name} contributes {rest}"))
                if c is None:
                    return []
                claims.append(c)
            return claims
        return []

    def _authorised(self, claims: list[Claim], s: str, product: Product, full_text: str, how: str) -> Finding:
        for c in claims:
            ok, why = self.reg.condition_met(c, product.per_daily_dose, product.for_children)
            if not ok:
                return Finding(
                    s, "block", f"{how}, but the product does not qualify: {why}", tuple(x.id for x in claims)
                )
        missing = [c.statement for c in claims if c.statement and norm(c.statement) not in norm(full_text or s)]
        ids = tuple(c.id for c in claims)
        if missing:
            return Finding(
                s, "rewrite", "required statement missing", ids, suggestion=f"{s.rstrip('.')}. {missing[0]}."
            )
        return Finding(s, "ok", how, ids)

    def _closest(self, s: str, nutrients: list[str], product: Product) -> Finding:
        if "epa_dha" in nutrients:
            nutrients = [*nutrients, "epa", "dha"]
        candidates = [
            c
            for c in self.reg.claims
            if not nutrients or c.nutrient in nutrients or any(part in nutrients for part in c.nutrient.split("_"))
        ]
        if not nutrients:
            # A claim about "it" or "this product" is a claim for what the product contains.
            present = set(product.per_daily_dose)
            candidates = [
                c for c in candidates if c.nutrient in present or (c.nutrient == "epa_dha" and present & {"epa", "dha"})
            ]
        scored = sorted(((self.similarity(s, c), c) for c in candidates), key=lambda x: -x[0])
        if not scored or scored[0][0] < self.floor:
            target = (
                ", ".join(self.reg.nutrients[n].name for n in nutrients if n in self.reg.nutrients) or "this product"
            )
            return Finding(s, "block", f"no authorised claim for {target} matches this wording")
        best = scored[0][0]
        # Prefer claims the product may make; one per nutrient, as close to the wording as possible.
        picks: dict[str, Claim] = {}
        refusal = ""
        for score, c in scored:
            if score < max(self.floor, best - 0.25):
                break
            ok, why = self.reg.condition_met(c, product.per_daily_dose, product.for_children)
            if ok and c.nutrient not in picks:
                picks[c.nutrient] = c
            elif not ok and not refusal:
                refusal = why
        if not picks:
            return Finding(
                s, "block", f"closest authorised claim does not apply to this product: {refusal}", (scored[0][1].id,)
            )
        chosen = list(picks.values())
        text = " ".join(c.text + "." for c in chosen)
        statements = [c.statement + "." for c in chosen if c.statement]
        if statements:
            text += " " + " ".join(dict.fromkeys(statements))
        return Finding(s, "rewrite", "health claim not in authorised wording", tuple(c.id for c in chosen), text)

    def check(self, text: str, product: Product) -> Report:
        sentences = [x for x in SPLIT.split(text.strip()) if x.strip()]
        return Report([self.check_sentence(x, product, text) for x in sentences])


@cache
def default_checker() -> Checker:
    return Checker()


def sentences(text: str) -> list[str]:
    return [x for x in SPLIT.split(text.strip()) if x.strip()]


def paraphrase_file() -> Path:
    return ROOT / load().claims.paraphrases
