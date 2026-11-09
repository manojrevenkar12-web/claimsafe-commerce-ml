from __future__ import annotations

import pytest

from claimsafe.catalog import by_id
from claimsafe.checker import default_checker
from claimsafe.settings import load


@pytest.fixture(scope="session")
def products():
    return by_id()


@pytest.fixture(scope="session")
def ck():
    return default_checker()


@pytest.fixture(scope="session")
def small():
    """Settings for a small simulated world, so model tests run in seconds."""
    return load().replace(replenish={"customers": 1500, "lgbm_rounds": 120})
