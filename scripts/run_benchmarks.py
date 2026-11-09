"""Run every measurement and write reports/*.json (the held-out claim run is separate and runs once).

python scripts/run_benchmarks.py
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("DO_NOT_TRACK", "1")
os.environ.setdefault("PREFECT_LOGGING_LEVEL", "WARNING")

from claimsafe.advisor import Advisor, UnreliableDrafter  # noqa: E402
from claimsafe.catalog import load_catalog  # noqa: E402
from claimsafe.checker import default_checker  # noqa: E402
from claimsafe.gdpr import DEV_KEY, pseudonym  # noqa: E402
from claimsafe.pipeline.vertex import compile_pipeline  # noqa: E402
from claimsafe.register import load_register  # noqa: E402
from claimsafe.replenish import model as M  # noqa: E402
from claimsafe.replenish.features import bigquery_sql, build  # noqa: E402
from claimsafe.replenish.monitor import replay  # noqa: E402
from claimsafe.replenish.simulate import simulate  # noqa: E402
from claimsafe.search import Search, evaluate  # noqa: E402
from claimsafe.settings import load  # noqa: E402
from claimsafe.warehouse import Warehouse, purge_superseded  # noqa: E402

REPORTS = ROOT / "reports"


def write(name: str, data: dict) -> None:
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / f"{name}.json").write_text(json.dumps(data, indent=1, ensure_ascii=False, default=str) + "\n")
    print(f"reports/{name}.json")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def claims_and_search() -> None:
    ck, reg = default_checker(), load_register()
    audit = []
    for p in load_catalog():
        rep = ck.check(p.marketing, p)
        audit.append(
            {
                "product": p.id,
                "name": p.name,
                "verdict": rep.verdict,
                "eligible_claims": len(p.eligible_claims(reg)),
                "findings": [
                    {"sentence": f.sentence, "verdict": f.verdict, "reason": f.reason, "suggestion": f.suggestion}
                    for f in rep.findings
                    if f.verdict != "ok"
                ],
                "sentences": [{"text": f.sentence, "verdict": f.verdict} for f in rep.findings],
                "safe_text": rep.safe_text(),
            }
        )
    queries = yaml.safe_load((ROOT / "data" / "eval" / "queries.yaml").read_text())["queries"]
    search = Search()
    k = load().search.k
    guard = []
    for rate in (0.2, 0.5, 0.8):
        drafter = UnreliableDrafter(rate, seed=7)
        adv = Advisor(search, drafter)
        shown, rewrites, blocks, sentences = [], 0, 0, 0
        for item in queries:
            ans, trace = adv.answer(item["q"])
            shown += [s["text"] for s in ans.shown]
            for _, rep in trace:
                sentences += len(rep.findings)
                rewrites += sum(f.verdict == "rewrite" for f in rep.findings)
                blocks += sum(f.verdict == "block" for f in rep.findings)
        leaked = sum(1 for bad in drafter.injected if any(bad in t for t in shown))
        guard.append(
            {
                "embellish_rate": rate,
                "made_up_sentences": len(drafter.injected),
                "reached_customer": leaked,
                "sentences_checked": sentences,
                "rewritten": rewrites,
                "blocked": blocks,
                "answers_shown": len(shown),
            }
        )
    examples = []
    for q in ("something for when I'm always tired", "omega 3 for my heart", "I'm pregnant, what should I take"):
        examples.append({"q": q, "answers": Advisor(search).answer(q)[0].shown})
    write(
        "claims",
        {
            "register": {"claims": len(reg.claims), "nutrients": len(reg.nutrients), "source": reg.source},
            "catalogue": {
                "products": len(audit),
                "with_findings": sum(a["verdict"] != "ok" for a in audit),
                "blocked": sum(a["verdict"] == "block" for a in audit),
                "rewrite_only": sum(a["verdict"] == "rewrite" for a in audit),
                "without_any_eligible_claim": sum(a["eligible_claims"] == 0 for a in audit),
                "rows": audit,
            },
            "search": {"k": k, "queries": len(queries), "methods": evaluate(search, queries, k)},
            "guard": guard,
            "examples": examples,
        },
    )


def ml() -> None:
    s = load()
    t = time.perf_counter()
    world = simulate(s)
    df = build(world.orders)
    res = replay(s, bad_release_month=17, df=df)
    reg = res.pop("registry")
    hold = res["release"]
    write(
        "replenishment",
        {
            "world": {
                "customers": int(world.orders.customer.nunique()),
                "orders": len(world.orders),
                "products": int(world.orders["product"].nunique()),
                "months": s.replenish.months,
                "train_months": s.replenish.train_months,
            },
            "release": hold,
            "months": res["months"],
            "served_mae_days": res["served_mae_days"],
            "served_rule_mae_days": res["served_rule_mae_days"],
            "versions": [
                {
                    "version": v.version,
                    "status": v.status,
                    "trained_through_day": v.trained_through_day,
                    "reason": v.reason,
                    "release_metrics": v.release_metrics,
                    "data_fingerprint": v.data_fingerprint,
                    "model_sha256": v.model_sha256,
                    "training_customers": len(v.customers),
                }
                for v in reg.versions
            ],
            "events": reg.events,
            "seconds": round(time.perf_counter() - t, 1),
        },
    )
    # Erasure at full scale, through retraining.
    wh = Warehouse.from_frames(world.identities, world.orders)
    feats = wh.con.execute("SELECT * FROM features").df()
    from claimsafe.replenish.registry import Registry

    r2 = Registry()
    rows = M.labelled(feats[feats.day < 360], as_of_day=330)
    r2.add(M.train(rows, s), "champion", 360, M.fingerprint(rows), {}, "v1", rows.customer.tolist())
    emails = world.identities.email.iloc[[3, 77, 512]].tolist()
    erased = {pseudonym(e, DEV_KEY) for e in emails}
    t = time.perf_counter()
    results = [wh.erase(e, DEV_KEY, r2, today=400, retrain_days=s.gdpr.retrain_after_erasure_days) for e in emails]
    after_delete = {c: wh.audit(c, r2) for c in erased}
    feats = wh.con.execute("SELECT * FROM features").df()
    rows = M.labelled(feats[feats.day < 400], as_of_day=370)
    v2 = r2.add(
        M.train(rows, s), "challenger", 400, M.fingerprint(rows), {}, "retrain after erasure", rows.customer.tolist()
    )
    r2.promote(v2.version, 400, "erasure retrain")
    purged = purge_superseded(r2, erased)
    after_retrain = {c: wh.audit(c, r2) for c in erased}
    write(
        "gdpr",
        {
            "erased_customers": len(erased),
            "deleted": [r.deleted for r in results],
            "after_delete": list(after_delete.values()),
            "retrain_due_day": results[0].retrain_due_day,
            "purged_versions": purged,
            "after_retrain": list(after_retrain.values()),
            "seconds": round(time.perf_counter() - t, 1),
        },
    )


def pipeline() -> None:
    out = compile_pipeline(ROOT / "pipelines" / "replenishment.yaml")
    (ROOT / "pipelines" / "features.bigquery.sql").write_text(bigquery_sql("commerce"))
    from claimsafe.pipeline.flow import replenishment_flow

    t = time.perf_counter()
    run = replenishment_flow()
    lineage = {
        "nodes": [
            {
                "id": "register",
                "kind": "source",
                "label": "EU claim register (432/2012)",
                "hash": sha(ROOT / "data/claims/register.yaml"),
            },
            {
                "id": "catalogue",
                "kind": "source",
                "label": "Product catalogue",
                "hash": sha(ROOT / "data/catalog/products.yaml"),
            },
            {
                "id": "orders",
                "kind": "dataset",
                "label": f"Orders ({run['orders']['rows']:,} rows)",
                "hash": run["orders"]["fingerprint"],
            },
            {
                "id": "features",
                "kind": "dataset",
                "label": f"Features ({run['features']['labelled']:,} labelled)",
                "hash": sha(ROOT / "pipelines/features.bigquery.sql"),
            },
            {
                "id": "training_set",
                "kind": "dataset",
                "label": f"Training set ({run['train']['trained_on']:,} rows)",
                "hash": run["train"]["data_fingerprint"],
            },
            {
                "id": "model",
                "kind": "model",
                "label": "Run-out model",
                "hash": sha(Path(run["workdir"]) / "model.json"),
            },
            {
                "id": "gate",
                "kind": "check",
                "label": f"Gate: {'passed' if run['passed_gate'] else 'failed'}",
                "hash": "",
            },
            {"id": "claims_index", "kind": "index", "label": "Claims search index", "hash": ""},
            {
                "id": "checker",
                "kind": "check",
                "label": "Claim checker",
                "hash": sha(ROOT / "src/claimsafe/checker.py"),
            },
        ],
        "edges": [
            ["orders", "features"],
            ["features", "training_set"],
            ["training_set", "model"],
            ["model", "gate"],
            ["register", "claims_index"],
            ["catalogue", "claims_index"],
            ["register", "checker"],
            ["catalogue", "checker"],
            ["catalogue", "orders"],
        ],
    }
    write(
        "pipeline",
        {
            "vertex_spec": str(out.relative_to(ROOT)),
            "vertex_spec_sha256": sha(out),
            "bigquery_sql": "pipelines/features.bigquery.sql",
            "prefect_run": {k: v for k, v in run.items() if k != "workdir"},
            "prefect_seconds": round(time.perf_counter() - t, 1),
            "lineage": lineage,
        },
    )


if __name__ == "__main__":
    claims_and_search()
    ml()
    pipeline()
