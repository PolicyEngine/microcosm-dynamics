"""Fit the existing mortality law, transport it, and retain two periods.

This module is imported only after the optional capability check. Its graph
is a synthetic engineering integration, separate from the locked M6 loop.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
from microcosm.frame import EntitySchema, Frame, WeightKind, Weights
from microcosm.graph.canonical import canonical_json
from microcosm.graph.codecs import SOURCE_CODECS
from microcosm.graph.decl import (
    ArtifactInput,
    ArtifactOutput,
    ArtifactType,
    Graph,
    Node,
    Owned,
    Slice,
    SourceRef,
    StructuralDelta,
    compile_graph,
)
from microcosm.graph.executor import run_graph
from microcosm.graph.kernel import (
    Capabilities,
    Determinism,
    KernelRegistry,
    KernelResult,
    KernelRole,
    Numeric,
    SeedSource,
    source_hash,
)
from microcosm.graph.randomness import keyed_uniform
from microcosm.graph.store import ContentStore

from populace_dynamics.engine.refit import (
    fit_mortality_model,
    prepare_mortality_refit_inputs,
)
from populace_dynamics.engine.steps import advance_age, apply_mortality

from . import model as model_module
from .model import (
    MortalityArtifact,
    fit_mortality,
    json_bytes,
    parse_json,
    read_json,
)

OBS = "person_period"
PID = "person_period_person_id"
PERIOD_ID = "person_period_period_id"
OID = "person_period_id"
MODEL_TYPE = ArtifactType("populace-dynamics.mortality", 1)
CODEC = "dynamics-mortality-json-v1"
DEPENDENCIES = ("numpy", "pandas")
TRAIN_COLUMNS = (
    ("age_band", "string"),
    ("sex", "string"),
    ("required_interview_year", "int64"),
    ("exposure", "float64"),
    ("death", "float64"),
)


def _json_source_marker(path, *, store=None):
    """Raw declared sources are read by domain kernels, never as Frames."""
    del path, store
    raise ValueError("Dynamics JSON sources need their declared domain kernel")


def _series(values, ids, entity=OBS, dtype="int64"):
    return pd.Series(
        values,
        index=pd.Index(ids, name=f"{entity}_id", dtype="int64"),
        dtype=dtype,
    )


def _records(path, expected):
    raw = read_json(path)
    if not isinstance(raw, list) or not raw:
        raise ValueError(f"{path.name} must contain nonempty record inputs")
    if any(
        not isinstance(row, dict) or set(row) != set(expected) for row in raw
    ):
        raise ValueError(
            f"{path.name} has unsupported fields; expected {expected}"
        )
    return pd.DataFrame(raw)


def _integer_column(frame, column):
    if any(type(v) is not int for v in frame[column].tolist()):
        raise ValueError(f"{column} must contain integer identifiers/years")
    frame[column] = frame[column].astype("int64")


def _weights(values):
    result = np.asarray(values, dtype=np.float64)
    if not np.isfinite(result).all() or (result <= 0).any():
        raise ValueError("source weights must be positive and finite")
    return Weights(result, WeightKind.DESIGN)


def _frame(records, periods, weights, columns):
    """Give observations an explicit persistent-person and period partition."""
    observations = pd.DataFrame(
        {
            OID: np.arange(1, len(records) + 1, dtype=np.int64),
            PID: records["person_id"].to_numpy(dtype=np.int64),
            PERIOD_ID: np.asarray(periods, dtype=np.int64),
        }
    )
    for column, dtype in columns:
        observations[column] = records[column].astype(dtype).array
    person_ids = np.sort(observations[PID].unique())
    period_ids = np.sort(observations[PERIOD_ID].unique())
    return Frame(
        {
            OBS: observations,
            "person": pd.DataFrame({"person_id": person_ids}),
            "period": pd.DataFrame(
                {"period_id": period_ids, "period": period_ids}
            ),
        },
        EntitySchema(person_entity=OBS, group_entities=("person", "period")),
        {OBS: weights},
        pd.Series(["synthetic"] * len(observations), dtype=object),
    )


def _create_training(context):
    fields = ["person_id", "event_year", "start_weight", *dict(TRAIN_COLUMNS)]
    data = _records(context.sources["training"], fields)
    for column in ("person_id", "event_year", "required_interview_year"):
        _integer_column(data, column)
    if data.duplicated(["person_id", "event_year"]).any():
        raise ValueError("training source repeats a person-period")
    if not data.sex.isin(["female", "male"]).all():
        raise ValueError("training sex must be female or male")
    for column in ("exposure", "death"):
        numeric = data[column].to_numpy(dtype=np.float64)
        if not np.isfinite(numeric).all() or (numeric < 0).any():
            raise ValueError(
                f"training {column} must be finite and nonnegative"
            )
    if (data.death > 1).any():
        raise ValueError("training death must lie in [0, 1]")
    data = data.sort_values(["person_id", "event_year"]).reset_index(drop=True)
    return KernelResult(
        frame=_frame(
            data, data.event_year, _weights(data.start_weight), TRAIN_COLUMNS
        )
    )


def _create_initial(context):
    data = _records(
        context.sources["initial"], ("person_id", "age", "sex", "weight")
    )
    for column in ("person_id", "age"):
        _integer_column(data, column)
    if data.person_id.duplicated().any():
        raise ValueError("initial population repeats a person_id")
    if not data.age.between(0, 120).all():
        raise ValueError("initial ages must lie in [0, 120]")
    if not data.sex.isin(["female", "male"]).all():
        raise ValueError("initial sex must be female or male")
    data = data.sort_values("person_id").reset_index(drop=True)
    return KernelResult(
        frame=_frame(
            data,
            [context.params["boundary_year"]] * len(data),
            _weights(data.weight),
            (("age", "int64"), ("sex", "string")),
        )
    )


def _periods(context, observations):
    periods = context.tables["period"].set_index("period_id")["period"]
    return observations[PERIOD_ID].map(periods).astype("int64")


def _fit(context):
    observations = context.tables[OBS]
    exposure = observations[[column for column, _ in TRAIN_COLUMNS]].copy()
    exposure["person_id"] = observations[PID].to_numpy()
    exposure["event_year"] = _periods(context, observations).to_numpy()
    exposure["start_weight"] = context.weights[OBS].values
    rates = pd.DataFrame(read_json(context.sources["rates"]))
    artifact = fit_mortality(
        exposure,
        rates,
        boundary_year=context.params["boundary_year"],
        external_vintage_year=context.params["external_vintage_year"],
    )
    return KernelResult(
        artifacts={"model": artifact.to_bytes()},
        receipt={
            "fit_rows": artifact.fit_rows,
            "boundary_year": artifact.boundary_year,
        },
    )


def mortality_uniforms(
    person_ids,
    *,
    experiment_id="mortality",
    replicate=0,
    base_seed=0,
    period=2015,
    draw_index=0,
):
    """Stable original-person draws, independent of observation row ordinals."""
    if any(
        isinstance(pid, (bool, np.bool_))
        or not isinstance(pid, (int, np.integer))
        for pid in person_ids
    ):
        raise ValueError("person identities must be integers")
    if (
        type(period) is not int
        or type(draw_index) is not int
        or draw_index < 0
    ):
        raise ValueError("period and nonnegative draw index must be integers")
    return keyed_uniform(
        stream=("sha256-u53-v1", experiment_id, replicate, base_seed),
        keys=[
            (int(pid), "mortality", int(period), int(draw_index))
            for pid in person_ids
        ],
    )


class _PersonGenerator:
    def __init__(self, person_id, module, period, stream):
        self.person_id = person_id
        self.module = getattr(module, "value", str(module))
        self.period = period
        self.stream = stream
        self.draw_index = 0

    def random(self):
        value = keyed_uniform(
            stream=self.stream,
            keys=[
                (
                    int(self.person_id),
                    self.module,
                    self.period,
                    self.draw_index,
                )
            ],
        )[0]
        self.draw_index += 1
        return float(value)


class _GraphPeriodContext:
    """Adapter for existing steps, intentionally bypassing ordinal mapping."""

    def __init__(self, params):
        self.year = int(params["boundary_year"]) + 1
        self.metadata = {}
        self.rng_registry = self  # Existing apply_mortality tests for None.
        self.stream = tuple(params["stream"])

    def person_generator(self, module, person_id):
        return _PersonGenerator(person_id, module, self.year, self.stream)


def _slice(context, observations=None):
    observations = (
        context.tables[OBS] if observations is None else observations
    )
    return pd.DataFrame(
        {
            "person_id": observations[PID].to_numpy(dtype=np.int64),
            "age": observations.age.to_numpy(dtype=np.int64),
            "sex": observations.sex.astype(str).to_numpy(),
            "year": _periods(context, observations).to_numpy(),
        }
    )


def _apply(context):
    artifact = MortalityArtifact.from_bytes(context.artifacts["model"].payload)
    if artifact.boundary_year != context.params["boundary_year"]:
        raise ValueError("mortality fit and application boundary years differ")
    model = artifact.model
    initial = _slice(context)
    survived = apply_mortality(
        initial, _GraphPeriodContext(context.params), context.rng, model=model
    )
    ids = context.tables[OBS][OID].tolist()
    return KernelResult(
        columns={
            (OBS, "death_probability"): _series(
                model.probabilities(initial), ids, dtype="float64"
            ),
            (OBS, "survives"): _series(
                initial.person_id.isin(survived.person_id).to_numpy(),
                ids,
                dtype="bool",
            ),
        }
    )


def _mass(weights, survivor_weights, strata, survivor_strata, boundary_year):
    def totals(values, labels):
        frame = pd.DataFrame({"weight": values, "stratum": list(labels)})
        return {
            str(label): float(value)
            for label, value in frame.groupby("stratum", observed=True)
            .weight.sum()
            .items()
        }

    before = totals(weights, strata)
    future = totals(survivor_weights, survivor_strata)
    after = totals(
        np.concatenate([weights, survivor_weights]),
        [*strata, *survivor_strata],
    )
    partition_after = {str(boundary_year): before}
    if len(survivor_weights):
        partition_after[str(boundary_year + 1)] = future
    return {
        "policy": "declared",
        "before": float(np.sum(weights)),
        "after": float(np.sum(np.concatenate([weights, survivor_weights]))),
        "stratum_before": before,
        "stratum_after": after,
        "partition": {
            "entity": "period",
            "column": "period",
            "stratum_before": {str(boundary_year): before},
            "stratum_after": partition_after,
        },
    }


def _advance(context):
    observations = context.tables[OBS]
    mask = observations.survives.to_numpy(dtype=bool)
    surviving = observations.loc[mask]
    boundary = int(context.params["boundary_year"])
    # The existing adapter's year is used for the entrant period group only;
    # it is never written back onto an incumbent observation.
    aged = advance_age(
        _slice(context, surviving),
        SimpleNamespace(year=boundary + 1, metadata={}),
        context.rng,
    )
    old_ids = observations[OID].tolist()
    new_ids = list(range(max(old_ids) + 1, max(old_ids) + 1 + len(surviving)))
    target_ids = old_ids + new_ids
    period_ids = context.tables["period"].period_id.tolist()
    period_values = context.tables["period"].period.tolist()
    next_period = [boundary + 1] if len(new_ids) else []
    weights = context.weights[OBS].values
    survivor_weights = weights[mask]
    return KernelResult(
        expand={
            OBS: _series(surviving[OID].tolist(), new_ids),
            "person": _series([], [], "person"),
            "period": _series(
                [pd.NA] * len(next_period), next_period, "period", "Int64"
            ),
        },
        columns={
            (OBS, PERIOD_ID): _series(
                observations[PERIOD_ID].tolist()
                + [boundary + 1] * len(new_ids),
                target_ids,
            ),
            (OBS, "age"): _series(
                observations.age.tolist() + aged.age.tolist(), target_ids
            ),
            ("period", "period"): _series(
                period_values + next_period, period_ids + next_period, "period"
            ),
        },
        weights=Weights(
            np.concatenate([weights, survivor_weights]),
            context.weights[OBS].kind,
        ),
        receipt={
            "mass": _mass(
                weights,
                survivor_weights,
                context.strata.tolist(),
                context.strata.to_numpy()[mask],
                boundary,
            )
        },
    )


def _age_claim(context):
    observations = context.tables[OBS]
    return KernelResult(
        columns={
            (OBS, "age"): _series(
                observations.age.tolist(), observations[OID].tolist()
            )
        }
    )


def _evaluate(context):
    observations = context.tables[OBS]
    boundary = int(context.params["boundary_year"])
    periods = _periods(context, observations)
    initial = observations.loc[periods == boundary].copy()
    future = observations.loc[periods == boundary + 1].copy()
    truth_document = read_json(context.sources["holdout"])
    if (
        not isinstance(truth_document, dict)
        or set(truth_document)
        != {"scope", "fixture_max_abs_death_rate_gap", "outcomes"}
        or truth_document["scope"] != "synthetic_engineering"
    ):
        raise ValueError(
            "holdout requires an explicit synthetic engineering contract"
        )
    truth = pd.DataFrame(truth_document["outcomes"])
    if set(truth.columns) != {"person_id", "year", "age", "death"}:
        raise ValueError("invalid held-out outcome columns")
    for column in truth.columns:
        _integer_column(truth, column)
    if truth.person_id.duplicated().any() or set(truth.person_id) != set(
        initial[PID]
    ):
        raise ValueError(
            "held-out identities must match the initial population exactly"
        )
    if (
        not (truth.year == boundary + 1).all()
        or not truth.death.isin([0, 1]).all()
    ):
        raise ValueError(
            "held-out outcomes must be binary deaths in the next period"
        )
    truth = truth.set_index("person_id").loc[initial[PID]]
    weights = context.weights[OBS].values
    start_weights = weights[(periods == boundary).to_numpy()]
    next_weights = weights[(periods == boundary + 1).to_numpy()]
    mass = _mass(
        start_weights,
        next_weights,
        context.strata[(periods == boundary).to_numpy()].tolist(),
        context.strata[(periods == boundary + 1).to_numpy()].tolist(),
        boundary,
    )
    mass["next_period"] = float(next_weights.sum())
    probability = initial.death_probability.to_numpy()
    expected_deaths = float(np.dot(start_weights, probability))
    observed_deaths = float(np.dot(start_weights, truth.death.to_numpy()))
    generated_deaths = float(
        np.dot(start_weights, ~initial.survives.to_numpy(dtype=bool))
    )
    discrepancy = abs(expected_deaths - observed_deaths) / float(
        start_weights.sum()
    )
    threshold = truth_document["fixture_max_abs_death_rate_gap"]
    if (
        isinstance(threshold, bool)
        or not isinstance(threshold, (int, float))
        or not np.isfinite(threshold)
        or not 0 <= threshold <= 1
    ):
        raise ValueError("fixture death-rate gap must be finite and in [0, 1]")
    artifact = MortalityArtifact.from_bytes(context.artifacts["model"].payload)
    original = _slice(context, initial).sort_values("person_id")
    stream = tuple(context.params["stream"])
    uniforms = mortality_uniforms(
        original.person_id.tolist(),
        experiment_id=stream[1],
        replicate=stream[2],
        base_seed=stream[3],
        period=boundary + 1,
    )
    expected_ids = original.loc[
        uniforms >= artifact.model.probabilities(original), "person_id"
    ].tolist()
    actual_ids = sorted(future[PID].tolist())
    expected_ages = original.set_index("person_id").age + 1
    age_parity = all(
        int(row.age) == int(expected_ages.loc[getattr(row, PID)])
        for row in future.itertuples(index=False)
    )
    engineering_pass = (
        expected_ids == actual_ids
        and age_parity
        and not observations[OID].duplicated().any()
    )
    heldout_age_error = float(
        np.abs(truth.age.to_numpy() - (initial.age.to_numpy() + 1)).mean()
    )
    fixture_pass = discrepancy <= threshold and heldout_age_error == 0
    report = {
        "scope": "synthetic_engineering",
        "boundary_year": boundary,
        "next_period": boundary + 1,
        "fit_rows": artifact.fit_rows,
        "initial_records": len(initial),
        "survivor_records": len(future),
        "heldout_records": len(truth),
        "expected_deaths": expected_deaths,
        "observed_deaths": observed_deaths,
        "generated_deaths": generated_deaths,
        "absolute_death_rate_gap": discrepancy,
        "fixture_max_abs_death_rate_gap": float(threshold),
        "heldout_mean_absolute_age_error": heldout_age_error,
        "fixture_verdict": "pass" if fixture_pass else "fail",
        "engineering_verdict": "pass" if engineering_pass else "fail",
        "mass": mass,
        "limitations": [
            "Synthetic engineering fixture; no scientific or national-population certification.",
            "The mortality fit's external-rate factor cancels in the fitted-window level.",
            "Household accounting, births, immigration, and the full M6 loop are outside this slice.",
        ],
    }
    return KernelResult(
        artifacts={"report": json_bytes(report)},
        receipt={
            "outcome": "pass" if engineering_pass and fixture_pass else "fail",
            "evidence": report,
        },
    )


class _Kernel:
    def __init__(
        self,
        ref,
        function,
        *,
        structural=StructuralDelta.NONE,
        numeric=Numeric.PLATFORM_BITWISE,
        seeded=False,
        gate=False,
    ):
        self.ref = ref
        self.function = function
        self.capabilities = Capabilities(
            Determinism.SEEDED if seeded else Determinism.DETERMINISTIC,
            numeric=numeric,
            structural=structural,
            seed_source=SeedSource.KEYED if seeded else SeedSource.NONE,
            role=KernelRole.GATE if gate else KernelRole.COMPUTE,
            dependencies=DEPENDENCIES,
        )

    def implementation_hash(self):
        return source_hash(
            self.function,
            model_module,
            fit_mortality_model,
            prepare_mortality_refit_inputs,
            apply_mortality,
            advance_age,
            keyed_uniform,
            canonical_json,
            dependencies=self.capabilities.dependencies,
        )

    def run(self, context):
        return self.function(context)


def build_graph(
    *,
    boundary_year=2014,
    external_vintage_year=2014,
    experiment_id="mortality",
    replicate=0,
    base_seed=0,
):
    """Return the declared graph and registered existing-operation wrappers."""
    stream = ("sha256-u53-v1", experiment_id, replicate, base_seed)
    keyed_uniform(stream=stream, keys=[])  # Validate even an empty population.
    if (
        type(boundary_year) is not int
        or type(external_vintage_year) is not int
    ):
        raise ValueError(
            "fit boundary and external vintage must be integer years"
        )
    params = {"boundary_year": boundary_year, "stream": stream}
    binding = (ArtifactInput("model", "fit", "model", MODEL_TYPE),)
    roots = (
        Node(
            "training",
            "dynamics.training@1",
            sources=("training",),
            structural=StructuralDelta.CREATE,
            outputs=tuple(
                Owned(OBS, column, dtype) for column, dtype in TRAIN_COLUMNS
            )
            + (Owned("period", "period", "int64"),),
        ),
        Node(
            "fit",
            "dynamics.mortality.fit@1",
            population="training",
            sources=("rates",),
            inputs=(
                Slice(OBS, tuple(dict(TRAIN_COLUMNS))),
                Slice("period", ("period",)),
            ),
            params={
                "boundary_year": boundary_year,
                "external_vintage_year": external_vintage_year,
            },
            artifact_outputs=(ArtifactOutput("model", MODEL_TYPE),),
        ),
        Node(
            "initial",
            "dynamics.initial@1",
            sources=("initial",),
            structural=StructuralDelta.CREATE,
            params={"boundary_year": boundary_year},
            outputs=(
                Owned(OBS, "age", "int64"),
                Owned(OBS, "sex", "string"),
                Owned("period", "period", "int64"),
            ),
        ),
        Node(
            "apply",
            "dynamics.mortality.apply@1",
            population="initial",
            artifact_inputs=binding,
            inputs=(Slice(OBS, ("age", "sex")), Slice("period", ("period",))),
            params=params,
            outputs=(
                Owned(OBS, "death_probability", "float64"),
                Owned(OBS, "survives", "bool"),
            ),
        ),
        Node(
            "advance",
            "dynamics.advance@1",
            base="initial",
            structural=StructuralDelta.EXPAND,
            entrants=True,
            mass="declared",
            inputs=(
                Slice(OBS, ("age", "sex", "survives")),
                Slice("period", ("period",)),
            ),
            params={
                "boundary_year": boundary_year,
                "expand_cells": (
                    (OBS, PERIOD_ID, "int64"),
                    (OBS, "age", "int64"),
                    ("period", "period", "int64"),
                ),
                "expand_weight_entity": OBS,
                "expand_weight_kind": "design",
            },
        ),
        Node(
            "age",
            "dynamics.age-claim@1",
            population="advance",
            inputs=(Slice(OBS, ("age",)),),
            outputs=(Owned(OBS, "age", "int64", rewrite=True),),
        ),
        Node(
            "evaluate",
            "dynamics.mortality.evaluate@1",
            population="advance",
            sources=("holdout",),
            artifact_inputs=binding,
            params=params,
            inputs=(
                Slice(OBS, ("age", "sex", "survives", "death_probability")),
                Slice("period", ("period",)),
            ),
        ),
    )
    registry = KernelRegistry()
    for kernel in (
        _Kernel(
            "dynamics.training@1",
            _create_training,
            structural=StructuralDelta.CREATE,
            numeric=Numeric.BITWISE,
        ),
        _Kernel("dynamics.mortality.fit@1", _fit),
        _Kernel(
            "dynamics.initial@1",
            _create_initial,
            structural=StructuralDelta.CREATE,
            numeric=Numeric.BITWISE,
        ),
        _Kernel("dynamics.mortality.apply@1", _apply, seeded=True),
        _Kernel(
            "dynamics.advance@1", _advance, structural=StructuralDelta.EXPAND
        ),
        _Kernel("dynamics.age-claim@1", _age_claim),
        _Kernel(
            "dynamics.mortality.evaluate@1", _evaluate, seeded=True, gate=True
        ),
    ):
        registry.register(kernel)
    SOURCE_CODECS.register(CODEC, _json_source_marker)
    return (
        Graph(
            "dynamics-mortality",
            tuple(
                SourceRef(name, CODEC)
                for name in ("training", "rates", "initial", "holdout")
            ),
            roots,
            mass_partition=("period", "period"),
        ),
        registry,
    )


@dataclass(frozen=True)
class MortalityGraphRun:
    manifest: object
    report: dict
    model_payload: bytes
    next_slice: pd.DataFrame


def run_mortality_graph(
    *,
    training,
    rates,
    initial,
    holdout,
    output_dir,
    boundary_year=2014,
    external_vintage_year=2014,
    experiment_id="mortality",
    replicate=0,
    base_seed=0,
    household_accounting=False,
):
    """Run/reuse the graph and write artifacts only in the explicit directory."""
    if household_accounting:
        raise ValueError(
            "household accounting is unsupported by this person-period slice"
        )
    output = Path(output_dir).resolve()
    sources = {
        name: Path(path).resolve()
        for name, path in (
            ("training", training),
            ("rates", rates),
            ("initial", initial),
            ("holdout", holdout),
        )
    }
    graph, registry = build_graph(
        boundary_year=boundary_year,
        external_vintage_year=external_vintage_year,
        experiment_id=experiment_id,
        replicate=replicate,
        base_seed=base_seed,
    )
    output.mkdir(parents=True, exist_ok=True)
    store = ContentStore(output / "store")
    manifest = run_graph(
        compile_graph(graph), sources=sources, store=store, kernels=registry
    )
    model_payload = store.load_bytes(
        manifest.nodes["fit"].opaque_artifacts["model"]
    )
    report = parse_json(
        store.load_bytes(manifest.nodes["evaluate"].opaque_artifacts["report"])
    )
    report["node_keys"] = {
        name: node.key for name, node in manifest.nodes.items()
    }
    report["cache_hits"] = {
        name: node.hit for name, node in manifest.nodes.items()
    }
    report["model_artifact_key"] = manifest.nodes["fit"].opaque_artifacts[
        "model"
    ]
    population = manifest.population("advance")
    observations = population.table(OBS)
    next_rows = observations.loc[observations[PERIOD_ID] == boundary_year + 1]
    next_slice = (
        pd.DataFrame(
            {
                "person_id": next_rows[PID].to_numpy(dtype=np.int64),
                "age": next_rows.age.to_numpy(dtype=np.int64),
                "year": np.full(
                    len(next_rows), boundary_year + 1, dtype=np.int64
                ),
            }
        )
        .sort_values("person_id")
        .reset_index(drop=True)
    )
    (output / "report.json").write_bytes(json_bytes(report))
    (output / "manifest.json").write_text(manifest.to_json(), encoding="utf-8")
    (output / "model.json").write_bytes(model_payload)
    for entity in (OBS, "person", "period"):
        population.table(entity).to_csv(output / f"{entity}.csv", index=False)
    next_slice.to_csv(output / "next_period.csv", index=False)
    return MortalityGraphRun(manifest, report, model_payload, next_slice)
