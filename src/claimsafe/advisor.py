"""The product advisor: retrieve, draft, check. Nothing reaches the customer without passing the checker.

Drafting is pluggable. `TemplateDrafter` writes only register text. `LLMDrafter` asks a hosted model for friendlier
copy (used when an API key is configured). `UnreliableDrafter` simulates a model that embellishes claims at a set
rate, to measure what the guard lets through.
"""

from __future__ import annotations

import os
import random
from dataclasses import dataclass, field
from typing import Protocol

import httpx

from claimsafe.catalog import Product
from claimsafe.checker import Checker, Report, default_checker
from claimsafe.register import Claim
from claimsafe.search import Search
from claimsafe.settings import load


@dataclass(frozen=True)
class Draft:
    product: Product
    text: str
    claims: tuple[Claim, ...]


class Drafter(Protocol):
    def draft(self, query: str, product: Product, claims: list[Claim]) -> str: ...


def best_claims(query: str, product: Product, n: int = 2) -> list[Claim]:
    """The product's eligible claims that share the most words with the question."""
    ck = default_checker()
    q = ck.function_tokens(query)
    scored = []
    for c in product.eligible_claims():
        overlap = len(q & ck.function_tokens(c.text))
        scored.append((overlap, c.id, c))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [c for o, _, c in scored[:n] if o > 0] or [c for *_, c in scored[:1]]


def product_facts(p: Product) -> str:
    return (
        f"{p.name}: {p.daily_units:g} {p.form} a day; one pack lasts {p.days_of_supply:.0f} days, "
        f"{p.price_eur:.2f} EUR."
    )


class TemplateDrafter:
    def draft(self, query: str, product: Product, claims: list[Claim]) -> str:
        parts = [product_facts(product)]
        parts += [c.text + "." for c in claims]
        parts += [s + "." for s in sorted({c.statement for c in claims if c.statement})]
        return " ".join(parts)


class UnreliableDrafter:
    """Rewrites each authorised claim into marketing language with probability `rate`, and adds an unprompted
    benefit sentence with probability `rate`: the failure modes seen when a model writes shop copy."""

    EMBELLISH = (
        "{n} boosts your {f}.",
        "Strengthens your {f} naturally.",
        "Your {f} will thank you.",
        "{n} keeps your {f} strong.",
        "Clinically proven support for your {f}.",
    )
    EXTRA = (
        "Prevents colds all winter long.",
        "Fights fatigue in days.",
        "Detoxes your body.",
        "Helps against stress and anxiety.",
        "For radiant skin and stronger hair.",
    )

    FUNCTIONS = (
        "immune",
        "bones",
        "teeth",
        "muscle",
        "energy",
        "fatigue",
        "brain",
        "vision",
        "heart",
        "skin",
        "hair",
        "nails",
        "thyroid",
        "blood",
        "cells",
        "pregnancy",
        "metabolism",
    )

    def __init__(self, rate: float, seed: int = 0):
        self.rate = rate
        self.rng = random.Random(seed)
        self.injected: list[str] = []  # every sentence it made up, for scoring the guard

    def draft(self, query: str, product: Product, claims: list[Claim]) -> str:
        parts = [product_facts(product)]
        for c in claims:
            if self.rng.random() < self.rate:
                name = c.text.split(" contribute")[0].split(" has ")[0].split(" is ")[0].split(" increases")[0]
                terms = [w for w in c.text.lower().replace("-", " ").split() if w in self.FUNCTIONS]
                func = terms[0] if terms else "health"
                bad = self.rng.choice(self.EMBELLISH).format(n=name, f=func)
                self.injected.append(bad)
                parts.append(bad)
            else:
                parts.append(c.text + ".")
                if c.statement:
                    parts.append(c.statement + ".")
        if self.rng.random() < self.rate:
            bad = self.rng.choice(self.EXTRA)
            self.injected.append(bad)
            parts.append(bad)
        return " ".join(parts)


class LLMDrafter:
    """Anthropic Messages API. Its output is a draft like any other: the checker decides what is shown."""

    def __init__(self, model: str | None = None, api_key: str | None = None, client: httpx.Client | None = None):
        cfg = load().advisor
        self.model = model or cfg.llm_model
        self.max_tokens = cfg.llm_max_tokens
        self.key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.client = client or httpx.Client(timeout=cfg.llm_timeout_s)

    def draft(self, query: str, product: Product, claims: list[Claim]) -> str:
        allowed = "\n".join(f"- {c.text}" + (f" ({c.statement})" if c.statement else "") for c in claims)
        prompt = (
            f"Customer question: {query}\nProduct facts: {product_facts(product)}\n"
            f"You may only use these health statements, word for word:\n{allowed}\n"
            "Write two or three friendly sentences. Do not add any other health benefit."
        )
        r = self.client.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": self.key, "anthropic-version": "2023-06-01"},
            json={
                "model": self.model,
                "max_tokens": self.max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        r.raise_for_status()
        return "".join(b.get("text", "") for b in r.json()["content"])


@dataclass
class Answer:
    query: str
    shown: list[dict] = field(default_factory=list)

    def text(self) -> str:
        return "\n".join(s["text"] for s in self.shown)


class Advisor:
    def __init__(self, search: Search | None = None, drafter: Drafter | None = None, checker: Checker | None = None):
        self.search = search or Search()
        self.drafter = drafter or TemplateDrafter()
        self.checker = checker or default_checker()
        self.max_products = load().advisor.max_products

    def answer(self, query: str) -> tuple[Answer, list[tuple[Draft, Report]]]:
        hits = self.search.search(query, "claims", self.max_products)
        trace = []
        ans = Answer(query)
        for h in hits:
            claims = best_claims(query, h.product)
            if not claims:
                continue
            text = self.drafter.draft(query, h.product, claims)
            report = self.checker.check(text, h.product)
            trace.append((Draft(h.product, text, tuple(claims)), report))
            safe = report.safe_text()
            if safe:
                ans.shown.append(
                    {"product": h.product.id, "name": h.product.name, "text": safe, "verdict": report.verdict}
                )
        return ans, trace
