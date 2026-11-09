"""HTTP API: check copy, search, ask the advisor. Every text it returns has passed the checker."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from claimsafe.advisor import Advisor
from claimsafe.catalog import by_id
from claimsafe.checker import default_checker


class CheckRequest(BaseModel):
    product: str
    text: str = Field(min_length=1, max_length=5000)


class Question(BaseModel):
    q: str = Field(min_length=2, max_length=500)


def create_app(advisor: Advisor | None = None) -> FastAPI:
    app = FastAPI(title="claimsafe-commerce-ml")
    adv = advisor or Advisor()
    products = by_id()

    @app.get("/api/health")
    def health() -> dict:
        return {"ok": True, "products": len(products)}

    @app.post("/api/check")
    def check(req: CheckRequest) -> dict:
        p = products.get(req.product)
        if p is None:
            raise HTTPException(404, f"unknown product {req.product}")
        rep = default_checker().check(req.text, p)
        return {
            "verdict": rep.verdict,
            "safe_text": rep.safe_text(),
            "findings": [
                {
                    "sentence": f.sentence,
                    "verdict": f.verdict,
                    "reason": f.reason,
                    "claims": list(f.claim_ids),
                    "suggestion": f.suggestion,
                }
                for f in rep.findings
            ],
        }

    @app.post("/api/search")
    def search(req: Question) -> dict:
        hits = adv.search.search(req.q, "claims")
        return {
            "results": [{"product": h.product.id, "name": h.product.name, "score": round(h.score, 4)} for h in hits]
        }

    @app.post("/api/advise")
    def advise(req: Question) -> dict:
        ans, _ = adv.answer(req.q)
        return {"query": ans.query, "answers": ans.shown}

    return app
