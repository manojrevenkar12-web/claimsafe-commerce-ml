"""A simulated order history for the supplement catalogue, with known ground truth.

Each customer buys one to three supplements. How long a pack lasts depends on the pack (units / daily dose), how many
packs were bought, and how faithfully this customer takes the dose (adherence, unknown to the model). Subscribers
reorder on schedule; promotions pull orders forward; customers churn. From month 15 an influencer campaign brings in
customers who take their supplements far less regularly, and after a price rise every non-subscriber stretches each
pack by a quarter: the shifts the monitoring has to catch.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from claimsafe.catalog import Product, load_catalog
from claimsafe.gdpr import DEV_KEY, pseudonym
from claimsafe.settings import Settings, load

DAYS_PER_MONTH = 30
SHIFT_MONTH = 15
PROMO_MONTHS = (11, 23)
STRETCH = 1.25
CHANNELS = ("search", "newsletter", "social", "influencer")


@dataclass(frozen=True)
class World:
    identities: pd.DataFrame  # pseudonym, email, name: the only table with identity
    orders: pd.DataFrame  # one row per order line, pseudonymised


def _supplements(products: tuple[Product, ...]) -> list[Product]:
    return [p for p in products if p.category not in ("tea", "protein") and p.days_of_supply <= 200]


def simulate(settings: Settings | None = None, products: tuple[Product, ...] | None = None) -> World:
    s = (settings or load()).replenish
    rng = np.random.default_rng(s.seed)
    prods = _supplements(products or load_catalog())
    horizon = s.months * DAYS_PER_MONTH
    ident, rows = [], []
    oid = 0
    for c in range(s.customers):
        email = f"customer{c:05d}@example.org"
        pid = pseudonym(email, DEV_KEY)
        ident.append({"customer": pid, "email": email, "name": f"Customer {c:05d}"})
        start = int(rng.integers(0, horizon - 45))
        late = start >= (SHIFT_MONTH - 1) * DAYS_PER_MONTH
        channel = "influencer" if late and rng.random() < 0.55 else str(rng.choice(CHANNELS[:3]))
        adherence = float(np.clip(rng.normal(0.62 if channel == "influencer" else 0.9, 0.15), 0.3, 1.3))
        subscriber = bool(rng.random() < (0.12 if channel == "influencer" else 0.22))
        churn = 0.06 if subscriber else (0.32 if channel == "influencer" else 0.16)
        for p in rng.choice(prods, size=int(rng.integers(1, 4)), replace=False):
            t = start + int(rng.integers(0, 20))
            while t < horizon:
                qty = 2 if rng.random() < 0.12 else 1
                month = t // DAYS_PER_MONTH + 1
                promo = month in PROMO_MONTHS
                rows.append(
                    {
                        "order_id": oid,
                        "customer": pid,
                        "product": p.id,
                        "qty": qty,
                        "day": t,
                        "channel": channel,
                        "subscriber": subscriber,
                        "promo": promo,
                        "price_eur": p.price_eur,
                        "supply_days": p.days_of_supply * qty,
                    }
                )
                oid += 1
                if rng.random() < churn:
                    break
                supply = p.days_of_supply * qty
                if subscriber:
                    gap = supply - 5 + rng.normal(0, 1.5)
                else:
                    winter = 1.1 if (p.id in ("P01", "P02", "P04") and month % 12 in (10, 11, 0, 1, 2)) else 1.0
                    gap = supply / (adherence * winter) + rng.gamma(2.0, 3.0) - 2
                    if month >= SHIFT_MONTH:
                        gap *= STRETCH  # after the price rise, customers make each pack last longer
                nxt = t + max(7, int(round(gap)))  # noqa: RUF046 - gap may be a numpy float
                promo_next = (nxt // DAYS_PER_MONTH + 1) in PROMO_MONTHS
                if promo_next and not subscriber and rng.random() < 0.5:
                    nxt -= int(rng.integers(3, 12))  # bought early in the sale
                t = max(t + 7, nxt)
    orders = pd.DataFrame(rows).sort_values(["day", "order_id"]).reset_index(drop=True)
    return World(pd.DataFrame(ident), orders)
