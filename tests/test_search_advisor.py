"""Search grounded in eligible claims, and an advisor whose drafts never reach a customer unchecked."""

from __future__ import annotations

import json

import httpx
import pytest
import yaml

from claimsafe.advisor import Advisor, LLMDrafter, UnreliableDrafter
from claimsafe.search import Search, evaluate
from claimsafe.settings import ROOT


@pytest.fixture(scope="module")
def search():
    return Search()


@pytest.fixture(scope="module")
def queries():
    return yaml.safe_load((ROOT / "data" / "eval" / "queries.yaml").read_text())["queries"]


def test_claims_index_finds_what_may_lawfully_be_recommended(search, queries):
    res = evaluate(search, queries, 5)
    assert res["claims"]["precision_at_k"] > res["marketing"]["precision_at_k"] + 0.2
    assert (
        res["claims"]["results_without_a_lawful_claim_for_the_need"]
        < res["marketing"]["results_without_a_lawful_claim_for_the_need"]
    )


def test_products_without_any_claim_never_rank_in_hybrid(search):
    ids = {h.product.id for q in ("stress", "sleep", "joints", "detox") for h in search.search(q, "hybrid")}
    assert not ids & {"P28", "P29", "P30", "P31", "P33", "P35", "P40"}


def test_advisor_shows_only_text_that_passes_the_checker(search, queries, ck, products):
    adv = Advisor(search)
    for item in queries:
        ans, _ = adv.answer(item["q"])
        for shown in ans.shown:
            assert ck.check(shown["text"], products[shown["product"]]).verdict == "ok"


def test_embellishing_drafter_leaks_nothing(search, queries):
    drafter = UnreliableDrafter(rate=0.6, seed=3)
    adv = Advisor(search, drafter)
    shown = []
    for item in queries:
        shown += [s["text"] for s in adv.answer(item["q"])[0].shown]
    assert len(drafter.injected) > 20
    assert not [bad for bad in drafter.injected for text in shown if bad in text]


def test_llm_output_is_checked_like_any_draft(search):
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert "word for word" in body["messages"][0]["content"]
        return httpx.Response(
            200,
            json={
                "content": [
                    {
                        "type": "text",
                        "text": "Magnesium contributes to a reduction of tiredness and fatigue. "
                        "It also cures insomnia.",
                    }
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adv = Advisor(search, LLMDrafter(api_key="test", client=client))
    ans, trace = adv.answer("always tired")
    assert trace and all("insomnia" not in s["text"] for s in ans.shown)
    assert any(r.verdict == "block" for _, r in trace)
