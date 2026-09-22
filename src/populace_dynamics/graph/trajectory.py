"""Synthetic annual mortality transport with immutable period history.

The fitted law and ageing step are the existing Dynamics implementations.
This optional graph supplies typed transition edges, stable person draws,
and explicit annual engineering diagnostics. It certifies no population.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
from microcosm.frame import Weights
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
from microcosm.graph.kernel import KernelResult, source_hash
from microcosm.graph.store import ContentStore

from . import runtime as rt
from .model import MortalityArtifact, json_bytes, parse_json, read_json

TRANSITION_TYPE = ArtifactType("populace-dynamics.mortality-transition", 1)
SNAPSHOT_TYPE = ArtifactType("populace-dynamics.mortality-population", 1)
_TRANSITION_FIELDS = {
    "person_id",
    "observation_id",
    "death_probability",
    "survives",
}


def _risk_rows(context):
    observations = context.tables[rt.OBS]
    periods = rt._periods(context, observations)
    return observations.loc[periods == context.params["year"] - 1].sort_values(
        rt.PID
    )


def _model(context):
    artifact = MortalityArtifact.from_bytes(context.artifacts["model"].payload)
    if artifact.boundary_year != context.params["boundary_year"]:
        raise ValueError("mortality fit and trajectory boundary years differ")
    return artifact.model


def _check_age_support(frame, model):
    age = frame.age.to_numpy(dtype=np.int64)
    if ((age < model.bands[0][0]) | (age > model.bands[-1][1])).any():
        raise ValueError(
            "mortality application age exceeds the fitted age support "
            f"[{model.bands[0][0]}, {model.bands[-1][1]}]"
        )


def _outcome(
    year, status, *, records=(), completed_year=None, diagnostic=None
):
    return {
        "format": TRANSITION_TYPE.name,
        "schema_version": 1,
        "from_year": year - 1,
        "year": year,
        "status": status,
        "completed_year": year if completed_year is None else completed_year,
        "records": list(records),
        "diagnostic": diagnostic,
    }


def _apply_complete(context):
    model = _model(context)
    risk = _risk_rows(context)
    initial = rt._slice(context, risk)
    _check_age_support(initial, model)
    year = context.params["year"]
    survived = rt.apply_mortality(
        initial,
        rt._GraphPeriodContext(
            {"boundary_year": year - 1, "stream": context.params["stream"]}
        ),
        context.rng,
        model=model,
    )
    probability = model.probabilities(initial)
    survivors = set(survived.person_id)
    records = [
        {
            "person_id": int(pid),
            "observation_id": int(oid),
            "death_probability": float(p),
            "survives": int(pid) in survivors,
        }
        for pid, oid, p in zip(
            risk[rt.PID], risk[rt.OID], probability, strict=True
        )
    ]
    return _outcome(year, "complete", records=records)


def _apply(context):
    year = context.params["year"]
    completed_year = context.params["boundary_year"]
    try:
        previous = context.artifacts.get("previous_transition")
        if previous is not None:
            previous = _decode_transition(previous.payload, year - 1)
            if previous["completed_year"] < completed_year:
                raise ValueError(
                    "prior transition predates the model boundary"
                )
            completed_year = previous["completed_year"]
        if previous is not None and previous["status"] != "complete":
            outcome = _outcome(
                year,
                "blocked",
                completed_year=previous["completed_year"],
                diagnostic={
                    "blocked_by": f"apply_{year - 1}",
                    "message": "previous mortality transition did not complete",
                },
            )
        else:
            outcome = _apply_complete(context)
    except Exception as error:
        # The exact pinned core requires every declared artifact even on a
        # failed gate. Publish an explicit typed failure, never survivor data.
        outcome = _outcome(
            year,
            "failed",
            completed_year=completed_year,
            diagnostic={
                "exception_type": type(error).__name__,
                "message": str(error),
            },
        )
    complete = outcome["status"] == "complete"
    return KernelResult(
        artifacts={"transition": json_bytes(outcome)},
        receipt={
            "outcome": (
                ("pass" if outcome["records"] else "not_applicable")
                if complete
                else "fail"
            ),
            "application_status": outcome["status"],
            "completed_year": outcome["completed_year"],
            "evidence": outcome["diagnostic"]
            or {"year": year, "risk_records": len(outcome["records"])},
        },
    )


def _decode_transition(payload, year):
    raw = parse_json(payload)
    if (
        not isinstance(raw, dict)
        or set(raw)
        != {
            "format",
            "schema_version",
            "from_year",
            "year",
            "records",
            "status",
            "completed_year",
            "diagnostic",
        }
        or raw["format"] != TRANSITION_TYPE.name
        or type(raw["schema_version"]) is not int
        or raw["schema_version"] != 1
        or type(raw["year"]) is not int
        or type(raw["from_year"]) is not int
        or raw["year"] != year
        or raw["from_year"] != year - 1
        or not isinstance(raw["records"], list)
        or raw["status"] not in ("complete", "failed", "blocked")
        or type(raw["completed_year"]) is not int
    ):
        raise ValueError("invalid annual mortality transition contract")
    if raw["status"] == "complete":
        if raw["completed_year"] != year or raw["diagnostic"] is not None:
            raise ValueError("invalid completed mortality transition")
    elif (
        raw["records"]
        or raw["completed_year"] >= year
        or not isinstance(raw["diagnostic"], dict)
        or not isinstance(raw["diagnostic"].get("message"), str)
    ):
        raise ValueError("invalid failed or blocked mortality transition")
    return raw


def _transition(context):
    """Validate both the byte contract and the recipient observation binding."""
    raw = _decode_transition(
        context.artifacts["transition"].payload, context.params["year"]
    )
    risk = _risk_rows(context)
    if raw["status"] != "complete":
        return risk, raw
    expected = list(zip(risk[rt.PID], risk[rt.OID], strict=True))
    records = raw["records"]
    if len(records) != len(expected):
        raise ValueError("mortality transition differs from the risk set")
    for row, (person_id, observation_id) in zip(
        records, expected, strict=True
    ):
        if (
            not isinstance(row, dict)
            or set(row) != _TRANSITION_FIELDS
            or type(row["person_id"]) is not int
            or type(row["observation_id"]) is not int
            or row["person_id"] != person_id
            or row["observation_id"] != observation_id
            or type(row["survives"]) is not bool
        ):
            raise ValueError(
                "invalid mortality transition observation binding"
            )
        p = row["death_probability"]
        if (
            isinstance(p, bool)
            or not isinstance(p, (int, float))
            or not np.isfinite(p)
            or not 0 <= p <= 1
        ):
            raise ValueError("invalid mortality transition probability")
    return risk, raw


def _mass(weights, strata, periods):
    frame = pd.DataFrame(
        {"weight": weights, "stratum": strata, "period": periods}
    )
    totals = {
        str(key): float(value)
        for key, value in frame.groupby("stratum", observed=True)
        .weight.sum()
        .items()
    }
    partition = {
        str(year): {
            str(key): float(value)
            for key, value in part.groupby("stratum", observed=True)
            .weight.sum()
            .items()
        }
        for year, part in frame.groupby("period", observed=True)
    }
    return totals, partition


def _advance(context):
    observations = context.tables[rt.OBS]
    risk, outcome = _transition(context)
    complete = outcome["status"] == "complete"
    records = outcome["records"]
    mask = np.asarray([row["survives"] for row in records], dtype=bool)
    surviving = risk.loc[mask] if complete else risk.iloc[:0]
    year = context.params["year"]
    aged = (
        rt.advance_age(
            rt._slice(context, surviving),
            SimpleNamespace(year=year, metadata={}),
            context.rng,
        )
        if complete
        else rt._slice(context, surviving)
    )
    old_ids = observations[rt.OID].tolist()
    new_ids = list(range(max(old_ids) + 1, max(old_ids) + 1 + len(surviving)))
    target_ids = old_ids + new_ids
    period_ids = context.tables["period"].period_id.tolist()
    period_values = context.tables["period"].period.tolist()
    next_period = [year] if len(new_ids) else []
    weights = context.weights[rt.OBS].values
    position = pd.Series(np.arange(len(observations)), index=old_ids)
    source_positions = position.loc[surviving[rt.OID]].to_numpy(dtype=int)
    survivor_weights = weights[source_positions]
    expanded_weights = np.concatenate([weights, survivor_weights])
    strata = context.strata.to_numpy()
    periods = rt._periods(context, observations).to_numpy()
    before, partitions_before = _mass(weights, strata, periods)
    after, partitions_after = _mass(
        expanded_weights,
        np.concatenate([strata, strata[source_positions]]),
        np.concatenate([periods, np.full(len(new_ids), year, dtype=int)]),
    )
    return KernelResult(
        expand={
            rt.OBS: rt._series(surviving[rt.OID].tolist(), new_ids),
            "person": rt._series([], [], "person"),
            "period": rt._series(
                [pd.NA] * len(next_period), next_period, "period", "Int64"
            ),
        },
        columns={
            (rt.OBS, rt.PERIOD_ID): rt._series(
                observations[rt.PERIOD_ID].tolist() + [year] * len(new_ids),
                target_ids,
            ),
            (rt.OBS, "age"): rt._series(
                observations.age.tolist() + aged.age.tolist(), target_ids
            ),
            ("period", "period"): rt._series(
                period_values + next_period, period_ids + next_period, "period"
            ),
        },
        weights=Weights(expanded_weights, context.weights[rt.OBS].kind),
        receipt={
            "application_status": "complete" if complete else "blocked",
            "completed_year": outcome["completed_year"],
            "mass": {
                "policy": "declared",
                "before": float(weights.sum()),
                "after": float(expanded_weights.sum()),
                "stratum_before": before,
                "stratum_after": after,
                "partition": {
                    "entity": "period",
                    "column": "period",
                    "stratum_before": partitions_before,
                    "stratum_after": partitions_after,
                },
            },
        },
    )


def _holdout(context):
    year = context.params["year"]
    raw = read_json(context.sources[f"holdout_{year}"])
    if (
        not isinstance(raw, dict)
        or set(raw)
        != {
            "scope",
            "year",
            "expected_death_rate",
            "fixture_max_abs_death_rate_gap",
        }
        or raw["scope"] != "synthetic_engineering"
        or type(raw["year"]) is not int
        or raw["year"] != year
    ):
        raise ValueError(
            "holdout requires the matching year and synthetic engineering "
            "aggregate contract"
        )
    for key in ("expected_death_rate", "fixture_max_abs_death_rate_gap"):
        value = raw[key]
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not np.isfinite(value)
            or not 0 <= value <= 1
        ):
            raise ValueError(f"holdout {key} must be finite and in [0, 1]")
    return raw


def _snapshot(context):
    """Transport the actual executor population to an isolated evaluation."""
    return KernelResult(
        artifacts={
            "snapshot": json_bytes(
                {
                    "format": SNAPSHOT_TYPE.name,
                    "schema_version": 1,
                    "year": context.params["year"],
                    "observations": context.tables[rt.OBS].to_dict(
                        orient="records"
                    ),
                    "periods": context.tables["period"].to_dict(
                        orient="records"
                    ),
                    "weights": context.weights[rt.OBS].values.tolist(),
                }
            )
        }
    )


def _evaluation_context(context):
    raw = parse_json(context.artifacts["snapshot"].payload)
    if (
        not isinstance(raw, dict)
        or set(raw)
        != {
            "format",
            "schema_version",
            "year",
            "observations",
            "periods",
            "weights",
        }
        or raw["format"] != SNAPSHOT_TYPE.name
        or type(raw["schema_version"]) is not int
        or raw["schema_version"] != 1
        or type(raw["year"]) is not int
        or raw["year"] != context.params["year"]
        or not isinstance(raw["observations"], list)
        or not isinstance(raw["periods"], list)
        or not isinstance(raw["weights"], list)
    ):
        raise ValueError("invalid annual mortality population snapshot")
    observations = pd.DataFrame(raw["observations"])
    periods = pd.DataFrame(raw["periods"])
    if (
        set(observations.columns)
        != {rt.OID, rt.PID, rt.PERIOD_ID, "age", "sex"}
        or set(periods.columns) != {"period_id", "period"}
        or len(observations) != len(raw["weights"])
        or not observations[rt.OID].is_unique
        or not periods.period_id.is_unique
        or not observations[rt.PERIOD_ID].isin(periods.period_id).all()
    ):
        raise ValueError("invalid annual mortality snapshot row binding")
    for column in (rt.OID, rt.PID, rt.PERIOD_ID, "age"):
        rt._integer_column(observations, column)
    for column in ("period_id", "period"):
        rt._integer_column(periods, column)
    if not observations.sex.isin(["female", "male"]).all():
        raise ValueError("invalid annual mortality snapshot sex")
    return SimpleNamespace(
        tables={rt.OBS: observations, "period": periods},
        weights={rt.OBS: rt._weights(raw["weights"])},
        params=context.params,
        artifacts=context.artifacts,
        sources=context.sources,
    )


def _evaluate(context):
    context = _evaluation_context(context)
    risk, outcome = _transition(context)
    if outcome["status"] != "complete":
        report = {
            "scope": "synthetic_engineering",
            "from_year": context.params["year"] - 1,
            "year": context.params["year"],
            "application_status": outcome["status"],
            "completed_year": outcome["completed_year"],
            "engineering_verdict": "not_evaluated",
            "fixture_verdict": "not_evaluated",
            "application_gate": {
                "node_id": f"apply_{context.params['year']}",
                "kernel_ref": "dynamics.trajectory.mortality.apply@1",
                "outcome": "fail",
                "evidence": outcome["diagnostic"],
            },
        }
        return KernelResult(
            artifacts={"report": json_bytes(report)},
            receipt={"outcome": "evidence_absent", "evidence": report},
        )
    holdout = _holdout(context)
    model = _model(context)
    records = outcome["records"]
    observations = context.tables[rt.OBS]
    year = context.params["year"]
    future = observations.loc[
        rt._periods(context, observations) == year
    ].sort_values(rt.PID)
    initial = rt._slice(context, risk)
    _check_age_support(initial, model)
    probability = model.probabilities(initial)
    stream = tuple(context.params["stream"])
    uniforms = rt.mortality_uniforms(
        initial.person_id.tolist(),
        experiment_id=stream[1],
        replicate=stream[2],
        base_seed=stream[3],
        period=year,
    )
    survives = uniforms >= probability
    expected_ids = initial.loc[survives, "person_id"].tolist()
    weights = pd.Series(
        context.weights[rt.OBS].values,
        index=observations[rt.OID],
    )
    start_weights = weights.loc[risk[rt.OID]].to_numpy()
    next_weights = weights.loc[future[rt.OID]].to_numpy()
    start_mass = float(start_weights.sum())
    expected_deaths = float(np.dot(start_weights, probability))
    generated_deaths = float(
        start_weights[~risk[rt.PID].isin(future[rt.PID]).to_numpy()].sum()
    )
    expected_ages = initial.loc[survives, "age"].to_numpy() + 1
    transition_parity = [
        row["survives"] for row in records
    ] == survives.tolist() and np.array_equal(
        [row["death_probability"] for row in records], probability
    )
    engineering_pass = (
        transition_parity
        and expected_ids == future[rt.PID].tolist()
        and np.array_equal(expected_ages, future.age.to_numpy())
        and np.array_equal(start_weights[survives], next_weights)
        and observations[rt.OID].is_unique
        and not observations.duplicated([rt.PID, rt.PERIOD_ID]).any()
    )
    rate_gap = (
        abs(expected_deaths / start_mass - holdout["expected_death_rate"])
        if start_mass
        else None
    )
    fixture_pass = (
        rate_gap <= holdout["fixture_max_abs_death_rate_gap"]
        if rate_gap is not None
        else True
    )
    report = {
        "scope": "synthetic_engineering",
        "application_status": "complete",
        "completed_year": year,
        "from_year": year - 1,
        "year": year,
        "initial_records": len(risk),
        "survivor_records": len(future),
        "expected_deaths": expected_deaths,
        "generated_deaths": generated_deaths,
        "start_mass": start_mass,
        "next_period_mass": float(next_weights.sum()),
        "absolute_death_rate_gap": rate_gap,
        "fixture_expected_death_rate": holdout["expected_death_rate"],
        "fixture_max_abs_death_rate_gap": holdout[
            "fixture_max_abs_death_rate_gap"
        ],
        "engineering_verdict": (
            ("pass" if len(risk) else "not_applicable")
            if engineering_pass
            else "fail"
        ),
        "fixture_verdict": (
            ("pass" if fixture_pass else "fail")
            if len(risk)
            else "not_applicable"
        ),
    }
    return KernelResult(
        artifacts={"report": json_bytes(report)},
        receipt={
            "outcome": (
                ("pass" if len(risk) else "not_applicable")
                if engineering_pass and fixture_pass
                else "fail"
            ),
            "evidence": report,
        },
    )


class _TrajectoryKernel(rt._Kernel):
    def implementation_hash(self):
        # source_hash includes complete defining modules, including helpers.
        # Keep these new wrappers separate from the unchanged fit/root hashes.
        return source_hash(
            self.function,
            rt,
            rt.model_module,
            rt.fit_mortality_model,
            rt.prepare_mortality_refit_inputs,
            rt.apply_mortality,
            rt.advance_age,
            rt.keyed_uniform,
            rt.canonical_json,
            dependencies=self.capabilities.dependencies,
        )


def build_trajectory_graph(
    *,
    end_year,
    boundary_year=2014,
    external_vintage_year=2014,
    experiment_id="mortality",
    replicate=0,
    base_seed=0,
):
    """Declare one fit and independent annual transition/evaluation nodes."""
    if type(end_year) is not int or end_year <= boundary_year:
        raise ValueError("end_year must be an integer after boundary_year")
    original, registry = rt.build_graph(
        boundary_year=boundary_year,
        external_vintage_year=external_vintage_year,
        experiment_id=experiment_id,
        replicate=replicate,
        base_seed=base_seed,
    )
    nodes = list(original.nodes[:3])
    sources = list(original.sources[:3])
    for kernel in (
        _TrajectoryKernel(
            "dynamics.trajectory.mortality.apply@1",
            _apply,
            seeded=True,
            gate=True,
        ),
        _TrajectoryKernel(
            "dynamics.trajectory.advance@1",
            _advance,
            structural=StructuralDelta.EXPAND,
        ),
        _TrajectoryKernel(
            "dynamics.trajectory.snapshot@1",
            _snapshot,
        ),
        _TrajectoryKernel(
            "dynamics.trajectory.mortality.evaluate@1",
            _evaluate,
            seeded=True,
            gate=True,
        ),
    ):
        registry.register(kernel)
    model_binding = ArtifactInput("model", "fit", "model", rt.MODEL_TYPE)
    stream = ("sha256-u53-v1", experiment_id, replicate, base_seed)
    base = "initial"
    previous_transition = ()
    for year in range(boundary_year + 1, end_year + 1):
        source = f"holdout_{year}"
        sources.append(SourceRef(source, rt.CODEC))
        params = {
            "year": year,
            "boundary_year": boundary_year,
            "stream": stream,
        }
        apply_id, advance_id = f"apply_{year}", f"advance_{year}"
        transition_binding = ArtifactInput(
            "transition", apply_id, "transition", TRANSITION_TYPE
        )
        slices = (Slice(rt.OBS, ("age", "sex")), Slice("period", ("period",)))
        nodes.extend(
            (
                Node(
                    apply_id,
                    "dynamics.trajectory.mortality.apply@1",
                    population=base,
                    inputs=slices,
                    params=params,
                    artifact_inputs=(model_binding, *previous_transition),
                    artifact_outputs=(
                        ArtifactOutput("transition", TRANSITION_TYPE),
                    ),
                ),
                Node(
                    advance_id,
                    "dynamics.trajectory.advance@1",
                    base=base,
                    structural=StructuralDelta.EXPAND,
                    entrants=True,
                    mass="declared",
                    inputs=slices,
                    artifact_inputs=(transition_binding,),
                    params={
                        "year": year,
                        "expand_cells": (
                            (rt.OBS, rt.PERIOD_ID, "int64"),
                            (rt.OBS, "age", "int64"),
                            ("period", "period", "int64"),
                        ),
                        "expand_weight_entity": rt.OBS,
                        "expand_weight_kind": "design",
                    },
                ),
                Node(
                    f"age_{year}",
                    "dynamics.age-claim@1",
                    population=advance_id,
                    inputs=(Slice(rt.OBS, ("age",)),),
                    outputs=(Owned(rt.OBS, "age", "int64", rewrite=True),),
                ),
                Node(
                    f"snapshot_{year}",
                    "dynamics.trajectory.snapshot@1",
                    population=advance_id,
                    inputs=slices,
                    params={"year": year},
                    artifact_outputs=(
                        ArtifactOutput("snapshot", SNAPSHOT_TYPE),
                    ),
                ),
                Node(
                    f"evaluate_{year}",
                    "dynamics.trajectory.mortality.evaluate@1",
                    # The exact pinned compiler makes EXPAND depend on all
                    # ordinary members of its base. Evaluate an actual
                    # population snapshot on a separate existing version so
                    # its holdout never enters the next transition's key.
                    population="training",
                    sources=(source,),
                    artifact_inputs=(
                        model_binding,
                        transition_binding,
                        ArtifactInput(
                            "snapshot",
                            f"snapshot_{year}",
                            "snapshot",
                            SNAPSHOT_TYPE,
                        ),
                    ),
                    params=params,
                ),
            )
        )
        base = advance_id
        previous_transition = (
            ArtifactInput(
                "previous_transition", apply_id, "transition", TRANSITION_TYPE
            ),
        )
    return (
        Graph(
            "dynamics-mortality-trajectory",
            tuple(sources),
            tuple(nodes),
            mass_partition=original.mass_partition,
        ),
        registry,
    )


@dataclass(frozen=True)
class MortalityTrajectoryRun:
    manifest: object
    report: dict
    model_payload: bytes
    trajectory: pd.DataFrame


def _gate_diagnostic(node_id, node):
    return {
        "node_id": node_id,
        "kernel_ref": node.kernel_ref,
        "outcome": node.receipt.get("outcome"),
        "evidence": dict(node.receipt.get("evidence", {})),
    }


def _rollup(periods, field):
    verdicts = {period[field] for period in periods.values()}
    if "fail" in verdicts:
        return "fail"
    if "not_evaluated" in verdicts:
        return "not_evaluated"
    return "pass" if "pass" in verdicts else "not_applicable"


def run_mortality_trajectory(
    *,
    training,
    rates,
    initial,
    holdouts,
    end_year,
    output_dir,
    boundary_year=2014,
    external_vintage_year=2014,
    experiment_id="mortality",
    replicate=0,
    base_seed=0,
    household_accounting=False,
):
    """Run the optional annual DAG, retaining explicit engineering evidence."""
    if household_accounting:
        raise ValueError("household accounting is unsupported by this graph")
    graph, registry = build_trajectory_graph(
        end_year=end_year,
        boundary_year=boundary_year,
        external_vintage_year=external_vintage_year,
        experiment_id=experiment_id,
        replicate=replicate,
        base_seed=base_seed,
    )
    years = range(boundary_year + 1, end_year + 1)
    if (
        not isinstance(holdouts, dict)
        or any(type(year) is not int for year in holdouts)
        or set(holdouts) != set(years)
    ):
        raise ValueError("holdouts must supply exactly one source per year")
    sources = {
        "training": Path(training).resolve(),
        "rates": Path(rates).resolve(),
        "initial": Path(initial).resolve(),
        **{
            f"holdout_{year}": Path(holdouts[year]).resolve() for year in years
        },
    }
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    store = ContentStore(output / "store")
    manifest = run_graph(
        compile_graph(graph), sources=sources, store=store, kernels=registry
    )
    (output / "manifest.json").write_text(manifest.to_json(), encoding="utf-8")
    model_key = manifest.nodes["fit"].opaque_artifacts["model"]
    model_payload = store.load_bytes(model_key)
    periods = {}
    last_population = "initial"
    for year in years:
        evaluation = manifest.nodes[f"evaluate_{year}"]
        key = evaluation.opaque_artifacts.get("report")
        if key is not None:
            periods[str(year)] = parse_json(store.load_bytes(key))
        else:
            period = {
                "scope": "synthetic_engineering",
                "from_year": year - 1,
                "year": year,
                "engineering_verdict": "not_evaluated",
                "fixture_verdict": "not_evaluated",
            }
            application = manifest.nodes[f"apply_{year}"]
            if application.receipt.get("outcome") == "fail":
                period["application_gate"] = _gate_diagnostic(
                    f"apply_{year}", application
                )
            elif evaluation.receipt.get("outcome") == "fail":
                period["evaluation_gate"] = _gate_diagnostic(
                    f"evaluate_{year}", evaluation
                )
            periods[str(year)] = period
        advance = manifest.nodes[f"advance_{year}"]
        if advance.frame_key is not None:
            last_population = f"advance_{year}"
    population = manifest.population(last_population)
    observations = population.table(rt.OBS)
    period_values = population.table("period").set_index("period_id").period
    trajectory = (
        pd.DataFrame(
            {
                "person_id": observations[rt.PID].to_numpy(dtype=np.int64),
                "age": observations.age.to_numpy(dtype=np.int64),
                "year": observations[rt.PERIOD_ID]
                .map(period_values)
                .to_numpy(dtype=np.int64),
                "weight": population.weights_for(rt.OBS).values,
            }
        )
        .sort_values(["year", "person_id"])
        .reset_index(drop=True)
    )
    report = {
        "scope": "synthetic_engineering",
        "boundary_year": boundary_year,
        "end_year": end_year,
        "completed_year": max(
            boundary_year,
            *(
                node.receipt.get("completed_year", boundary_year)
                for name, node in manifest.nodes.items()
                if name.startswith("apply_")
            ),
        ),
        "periods": periods,
        "engineering_verdict": _rollup(periods, "engineering_verdict"),
        "fixture_verdict": _rollup(periods, "fixture_verdict"),
        "execution_status": (
            "failed"
            if any(
                period["engineering_verdict"] == "not_evaluated"
                for period in periods.values()
            )
            else "complete"
        ),
        "model_artifact_key": model_key,
        "node_keys": {name: node.key for name, node in manifest.nodes.items()},
        "cache_hits": {
            name: node.hit for name, node in manifest.nodes.items()
        },
        "limitations": [
            "Synthetic engineering fixture; no scientific or national-population certification.",
            "The mortality fit's external-rate factor cancels in the fitted-window level.",
            "Household accounting, births, immigration, and the full M6 loop are outside this graph.",
            "The pinned core executes guarded descendants after a typed failure; application-level blocked does not mean native executor unreached.",
        ],
    }
    (output / "report.json").write_bytes(json_bytes(report))
    (output / "model.json").write_bytes(model_payload)
    trajectory.to_csv(output / "trajectory.csv", index=False)
    return MortalityTrajectoryRun(manifest, report, model_payload, trajectory)
