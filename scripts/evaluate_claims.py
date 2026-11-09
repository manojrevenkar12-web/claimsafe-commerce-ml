"""Score the claim checker on the labelled sets.

    python scripts/evaluate_claims.py dev       # any time
    python scripts/evaluate_claims.py heldout   # once: checks config/heldout.lock, refuses a second run

The dangerous error is a false pass: text the law does not allow that the checker lets through.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from claimsafe.catalog import by_id  # noqa: E402
from claimsafe.checker import default_checker  # noqa: E402


def wilson(k: int, n: int, z: float = 1.96) -> list[float] | None:
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0.0, c - h), 4), round(min(1.0, c + h), 4)]


def score(name: str) -> dict:
    items = yaml.safe_load((ROOT / "data" / "eval" / f"{name}.yaml").read_text())["items"]
    cat, ck = by_id(), default_checker()
    rows = []
    for it in items:
        rep = ck.check(it["text"], cat[it["product"]])
        rows.append(
            {
                "product": it["product"],
                "text": it["text"],
                "allowed": it["allowed"],
                "verdict": rep.verdict,
                "reasons": [f.reason for f in rep.findings if f.verdict != "ok"],
            }
        )
    bad = [r for r in rows if not r["allowed"]]
    good = [r for r in rows if r["allowed"]]
    false_pass = [r for r in bad if r["verdict"] == "ok"]
    false_flag = [r for r in good if r["verdict"] != "ok"]
    correct = len(rows) - len(false_pass) - len(false_flag)
    return {
        "set": name,
        "items": len(rows),
        "not_allowed": len(bad),
        "allowed": len(good),
        "accuracy": round(correct / len(rows), 4),
        "accuracy_ci95": wilson(correct, len(rows)),
        "false_passes": len(false_pass),
        "false_pass_rate": round(len(false_pass) / len(bad), 4) if bad else None,
        "false_pass_rate_ci95": wilson(len(false_pass), len(bad)),
        "false_flags": len(false_flag),
        "false_flag_rate": round(len(false_flag) / len(good), 4) if good else None,
        "false_flag_rate_ci95": wilson(len(false_flag), len(good)),
        "errors": false_pass + false_flag,
        "verdicts": {v: sum(r["verdict"] == v for r in rows) for v in ("ok", "rewrite", "block")},
    }


def check_lock() -> list[str]:
    bad = []
    for ln in (ROOT / "config" / "heldout.lock").read_text().splitlines():
        if not ln.strip() or ln.startswith("#"):
            continue
        digest, path = ln.split(maxsplit=1)
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != digest:
            bad.append(path)
    return bad


def main() -> None:
    name = sys.argv[1]
    out = ROOT / "reports" / f"claims_{name}.json"
    if name == "heldout":
        if out.exists():
            sys.exit("the held-out set has already been scored once; see reports/claims_heldout.json")
        bad = check_lock()
        if bad:
            sys.exit(f"changed since the held-out lock: {', '.join(bad)}")
    res = score(name)
    if name == "heldout":
        res["run_once"] = True
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n")
    print(
        f"{name}: {res['items']} items, accuracy {res['accuracy']:.1%}, false passes {res['false_passes']}/"
        f"{res['not_allowed']}, false flags {res['false_flags']}/{res['allowed']}"
    )


if __name__ == "__main__":
    main()
