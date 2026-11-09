PY ?= python3
export PYTHONPATH := src
export DO_NOT_TRACK := 1

.PHONY: check lint test web-test bench report dev heldout lock-check api pipeline
check: lint lock-check test web-test
lint:
	ruff format --check src tests scripts && ruff check src tests scripts
test:
	$(PY) -m pytest -q
web-test:
	cd web && npx vitest run
lock-check:
	grep -v '^#' config/heldout.lock | sha256sum -c --quiet -
bench:
	$(PY) scripts/run_benchmarks.py
report:
	$(PY) scripts/report.py
dev:
	$(PY) scripts/evaluate_claims.py dev
heldout:
	$(PY) scripts/evaluate_claims.py heldout
api:
	$(PY) -m uvicorn claimsafe.api:create_app --factory --reload
pipeline:
	$(PY) -c 'from pathlib import Path; from claimsafe.pipeline.vertex import compile_pipeline; compile_pipeline(Path("pipelines/replenishment.yaml"))'
