"""Pseudonymisation and erasure.

Customer identity (email, name) lives in one table only. Every other store, from events and features to training
manifests and the personalisation index, holds a keyed pseudonym (HMAC-SHA256). Erasure removes the identity and the
customer's rows from every store, and proves it with an audit that searches each store for the pseudonym.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import warnings

from claimsafe.settings import load

DEV_KEY = b"claimsafe-dev-key-do-not-use-in-production"


def key() -> bytes:
    env = os.environ.get(load().gdpr.pseudonym_key_env)
    if env:
        return env.encode()
    warnings.warn("pseudonym key not set; using the development key", stacklevel=2)
    return DEV_KEY


def pseudonym(email: str, k: bytes | None = None) -> str:
    """Stable, keyed, not reversible without the key. Lower-cased and trimmed so one person is one pseudonym."""
    msg = email.strip().lower().encode()
    return "c_" + hmac.new(k or key(), msg, hashlib.sha256).hexdigest()[:24]


def anonymise_email(email: str) -> str:
    local, _, domain = email.partition("@")
    return f"{local[:1]}***@{domain}"
