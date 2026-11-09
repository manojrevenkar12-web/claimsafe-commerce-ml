# AGENTS.md

How to work in this repository, for people and coding agents.

## Fast feedback

```bash
make lint        # ruff format --check and ruff check
make test        # all Python tests on a small simulated world; about 10 seconds
make web-test    # vitest for the dashboard
make lock-check  # the held-out lock still verifies
make dev         # the claim checker on the dev set
make report      # RESULTS.md and web/public/data/dashboard.json from reports/*.json
```

`make bench` reruns every benchmark (claims, search, guard, the 20-month replay, erasure, the Prefect run) in about a
minute and overwrites `reports/`. Set `DO_NOT_TRACK=1` to keep Prefect from trying to send telemetry.

## Invariants (tests enforce them)

1. **Nothing that serves reads the labelled sets.** `data/eval/` holds the dev and held-out labels and the search
   relevance judgements; nothing under `src/` names it (`test_nothing_in_src_reads_the_evaluation_labels`).
2. **Only register wording reaches a customer.** A rewrite uses the text of an authorised claim from
   `data/claims/register.yaml`, or a wording in `data/claims/paraphrases.yaml`, and only for a nutrient the product
   contains at a qualifying dose. Medicinal claims are removed, never rewritten.
3. **Models draft, the checker decides.** Every advisor answer, from the template, an LLM or the deliberately
   unreliable test drafter, is checked sentence by sentence before it is shown (`reports/claims.json`, guard).
4. **Point-in-time features.** A feature row for an order uses only orders before it; labels exist only once the
   next order has happened by the as-of day (`test_features_use_only_the_past`).
5. **The gate decides releases.** A model is registered as champion only if it beats the champion (or the
   pack-size rule) by `gate.min_mae_improvement` on the same holdout. A release that skipped the gate and is worse
   by `monitoring.rollback_degradation` is rolled back automatically.
6. **Erasure reaches every store.** Identity, orders, features and the personalisation index are deleted at once;
   model versions whose manifest names the customer are marked for retraining and purged after it
   (`test_erasure_reaches_every_store`).
7. **Settings in config.** Every threshold lives in `config/claimsafe.toml`; the dashboard's sizes and colours live
   in `web/src/theme/tokens.ts`.
8. **Generated reports.** `RESULTS.md`, `web/public/data/dashboard.json` and `pipelines/*` come from scripts; do not
   edit them by hand. CI regenerates them and fails on a difference.

## The held-out rule

`data/eval/heldout.yaml` was written and hashed before the checker had run on anything. The checker's vocabulary was
tuned on `data/eval/dev.yaml` only, then the checker, register, policy, catalogue and config were pinned in
`config/heldout.lock`. `scripts/evaluate_claims.py heldout` checks the lock, refuses a second run, and its output
(`reports/claims_heldout.json`) is published as it came out, including its ten false passes.

The lock has been re-pinned three times after that run, each with a comment in the file: a new `[monitoring]`
setting, ruff reflowing two pinned files (layout only), and the LLM drafter's settings in `[advisor]`. None of these
touch what the checker reads; `test_checker_settings_are_those_of_the_held_out_run` holds the `[claims]` values.

Changing what the checker does needs a new dev round and a new, unseen held-out set. The current one is spent.

## Layout

```
config/            claimsafe.toml (every setting), heldout.lock
data/claims/       register.yaml (Reg. 432/2012, 14 nutrients), policy.yaml (vocabulary), paraphrases.yaml
data/catalog/      products.yaml (invented, from scripts/make_catalog.py)
data/eval/         dev.yaml, heldout.yaml, queries.yaml (labels; never read by src/)
src/claimsafe/     register, catalog, checker, search, advisor, gdpr, warehouse, api
  replenish/       simulate, features (DuckDB SQL, BigQuery transpile), model, registry, monitor
  pipeline/        steps (plain functions), vertex (KFP v2), flow (Prefect 3)
pipelines/         compiled Vertex AI spec and BigQuery SQL
scripts/           evaluate_claims, run_benchmarks, report, make_catalog
web/               the dashboard (React, TypeScript, Framer Motion)
```
