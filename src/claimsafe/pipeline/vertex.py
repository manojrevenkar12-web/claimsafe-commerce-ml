"""The replenishment pipeline for Vertex AI Pipelines (KFP v2). No `from __future__ import annotations` here: KFP reads
the real annotation objects.

Each component is a thin wrapper around a function in claimsafe.pipeline.steps, run inside the project image.
`compile_pipeline` writes the pipeline spec that `scripts/submit_vertex.py` (or the Bitbucket deploy step) submits as a
`google.cloud.aiplatform.PipelineJob`. In this repository the spec is compiled and checked in CI, not submitted.
"""

from pathlib import Path

from kfp import compiler, dsl

IMAGE = "europe-west3-docker.pkg.dev/PROJECT/claimsafe/claimsafe:latest"


@dsl.component(base_image=IMAGE)
def extract_orders(source: str, project: str, dataset: str, orders: dsl.Output[dsl.Dataset]) -> str:
    from claimsafe.pipeline import steps

    return str(steps.extract_orders(orders.path, source, project, dataset))


@dsl.component(base_image=IMAGE)
def build_features(orders: dsl.Input[dsl.Dataset], features: dsl.Output[dsl.Dataset]) -> str:
    from claimsafe.pipeline import steps

    return str(steps.build_features(orders.path, features.path))


@dsl.component(base_image=IMAGE)
def train(features: dsl.Input[dsl.Dataset], as_of_day: int, model: dsl.Output[dsl.Model]) -> str:
    from claimsafe.pipeline import steps

    return str(steps.train(features.path, model.path, as_of_day))


@dsl.component(base_image=IMAGE)
def evaluate(
    features: dsl.Input[dsl.Dataset], model: dsl.Input[dsl.Model], as_of_day: int, metrics: dsl.Output[dsl.Metrics]
) -> bool:
    import json

    from claimsafe.pipeline import steps

    res = steps.evaluate(features.path, model.path, as_of_day, metrics.path + ".json")
    for k, v in res["challenger"].items():
        metrics.log_metric(f"challenger_{k}", v)
    for k, v in res["rule"].items():
        metrics.log_metric(f"rule_{k}", v)
    del json
    return steps.gate(metrics.path + ".json")


@dsl.component(base_image=IMAGE)
def register(model: dsl.Input[dsl.Model], project: str, region: str) -> str:
    """Upload to the Vertex AI Model Registry as a new version; serving promotion is a separate, gated step."""
    if not project:
        return "skipped: no project"
    from google.cloud import aiplatform

    aiplatform.init(project=project, location=region)
    m = aiplatform.Model.upload(
        display_name="replenishment-run-out",
        artifact_uri=model.uri.rsplit("/", 1)[0],
        serving_container_image_uri=IMAGE.replace(":latest", "-serve:latest"),
    )
    return m.resource_name


@dsl.pipeline(name="replenishment-run-out", description="Features, training, evaluation, gate, registration.")
def replenishment_pipeline(
    source: str = "bigquery",
    project: str = "",
    dataset: str = "commerce",
    region: str = "europe-west3",
    as_of_day: int = 360,
):
    orders = extract_orders(source=source, project=project, dataset=dataset)
    feats = build_features(orders=orders.outputs["orders"])
    model = train(features=feats.outputs["features"], as_of_day=as_of_day)
    ev = evaluate(features=feats.outputs["features"], model=model.outputs["model"], as_of_day=as_of_day)
    with dsl.If(ev.outputs["Output"] == True, name="passes-gate"):  # noqa: E712 - KFP condition syntax
        register(model=model.outputs["model"], project=project, region=region)


def compile_pipeline(path: Path) -> Path:
    compiler.Compiler().compile(replenishment_pipeline, str(path))
    return path
