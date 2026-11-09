"""Model registry: versions with their data fingerprint, metrics, training manifest and status.

The training manifest records which pseudonymous customers a version learned from, so an erasure request can be
traced to every model it touches.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from claimsafe.replenish.model import RunOutModel, model_bytes


@dataclass
class Version:
    version: int
    status: str  # champion | challenger | rejected | retired | rolled_back
    trained_through_day: int
    data_fingerprint: str
    model_sha256: str
    release_metrics: dict
    reason: str
    customers: list[str] = field(default_factory=list)
    retrain_due_day: int | None = None


class Registry:
    def __init__(self, path: Path | None = None):
        self.path = path
        self.versions: list[Version] = []
        self.models: dict[int, RunOutModel] = {}
        self.events: list[dict] = []

    def add(
        self, model: RunOutModel, status: str, day: int, fp: str, metrics: dict, reason: str, customers: list[str]
    ) -> Version:
        v = Version(
            len(self.versions) + 1,
            status,
            day,
            fp,
            hashlib.sha256(model_bytes(model)).hexdigest()[:16],
            metrics,
            reason,
            sorted(set(customers)),
        )
        self.versions.append(v)
        self.models[v.version] = model
        self.log(day, "registered", v.version, f"{status}: {reason}")
        return v

    def champion(self) -> Version:
        return next(v for v in reversed(self.versions) if v.status == "champion")

    def promote(self, version: int, day: int, reason: str) -> None:
        for v in self.versions:
            if v.status == "champion":
                v.status = "retired"
        self.get(version).status = "champion"
        self.log(day, "promoted", version, reason)

    def rollback(self, day: int, reason: str) -> Version:
        bad = self.champion()
        bad.status = "rolled_back"
        prev = next(v for v in reversed(self.versions) if v.status == "retired")
        prev.status = "champion"
        self.log(day, "rolled back", bad.version, f"{reason}; champion is v{prev.version} again")
        return prev

    def get(self, version: int) -> Version:
        return self.versions[version - 1]

    def log(self, day: int, event: str, version: int, detail: str) -> None:
        self.events.append({"day": day, "event": event, "version": version, "detail": detail})

    def save(self) -> None:
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps({"versions": [asdict(v) for v in self.versions], "events": self.events}, indent=1)
            )
