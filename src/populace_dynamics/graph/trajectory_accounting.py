"""Optional accounting of the existing annual mortality graph's artifacts.

No population or transition is changed. Death declarations come from the
typed mortality transition, never from the difference between two rosters.
Import this optional module only with the reviewed graph dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import pandas as pd
from microcosm.graph.decl import (
    ArtifactInput,
    ArtifactOutput,
    ArtifactType,
    Node,
    compile_graph,
)
from microcosm.graph.executor import run_graph
from microcosm.graph.kernel import KernelResult, source_hash
from microcosm.graph.store import ContentStore

from populace_dynamics.engine import accounting

from . import trajectory
from ._compat import require_graph
from .model import json_bytes, parse_json

ACCOUNT_TYPE = ArtifactType("populace-dynamics.mortality-stock-flow", 1)
ACCOUNT_KERNEL = "dynamics.trajectory.stock-flow@1"


def _validate_raw_snapshot(payload):
    """Apply the accountant's scalar domain before pandas can coerce values."""
    raw = parse_json(payload)
    rt = trajectory.rt
    if (
        not isinstance(raw, dict)
        or not isinstance(raw.get("observations"), list)
        or not isinstance(raw.get("periods"), list)
        or not isinstance(raw.get("weights"), list)
        or len(raw["observations"]) != len(raw["weights"])
    ):
        raise ValueError("invalid accounting snapshot row/weight structure")
    accounting._as_year(raw.get("year"), "snapshot.year")
    for row in raw["observations"]:
        if not isinstance(row, dict) or set(row) != {
            rt.OID,
            rt.PID,
            rt.PERIOD_ID,
            "age",
            "sex",
        }:
            raise ValueError("invalid annual mortality snapshot row binding")
        for column in (rt.OID, rt.PID, rt.PERIOD_ID, "age"):
            accounting._as_person_id(row[column], f"snapshot.{column}")
    for row in raw["periods"]:
        if not isinstance(row, dict) or set(row) != {"period_id", "period"}:
            raise ValueError("invalid accounting snapshot period structure")
        for column in ("period_id", "period"):
            accounting._as_year(row[column], f"snapshot.{column}")
    for value in raw["weights"]:
        accounting._as_weight(value, "snapshot.weight")


def _period_frames(context):
    """Copy endpoint rows, retaining columns and positional weight binding."""
    rt = trajectory.rt
    observations = context.tables[rt.OBS]
    periods = rt._periods(context, observations)
    calendar = context.tables["period"].period
    if (
        not calendar.is_unique
        or (calendar > context.params["year"]).any()
        or (calendar < context.params["boundary_year"]).any()
        or pd.DataFrame({"person_id": observations[rt.PID], "year": periods})
        .duplicated()
        .any()
    ):
        raise ValueError("invalid accounting snapshot person-period history")
    frames = []
    for year in (context.params["year"] - 1, context.params["year"]):
        mask = periods == year
        frame = observations.loc[mask].copy()
        frame["person_id"] = frame[rt.PID].to_numpy(copy=True)
        frame["year"] = periods.loc[mask].to_numpy(copy=True)
        frame["weight"] = context.weights[rt.OBS].values[mask.to_numpy()]
        frames.append(frame)
    return frames


def _account(context):
    year = context.params["year"]
    report = {
        "format": ACCOUNT_TYPE.name,
        "schema_version": 1,
        "scope": "synthetic_engineering",
        "from_year": year - 1,
        "year": year,
        "application_status": None,
        "completed_year": None,
        "accounting_status": "failed",
        "account": None,
        "diagnostic": None,
        "transition_node": f"apply_{year}",
        "snapshot_node": f"snapshot_{year}",
    }
    try:
        outcome = trajectory._decode_transition(
            context.artifacts["transition"].payload, year
        )
        if outcome["completed_year"] < context.params["boundary_year"]:
            raise ValueError("transition predates the model boundary")
        # JSON exponent overflow can produce infinity despite parse_constant.
        # Refuse it before copying arbitrary diagnostic fields into a report.
        json_bytes(outcome["diagnostic"])
        report.update(
            application_status=outcome["status"],
            completed_year=outcome["completed_year"],
        )
        if outcome["status"] != "complete":
            # Do not reconcile a stale snapshot or parse it after failure.
            report.update(
                accounting_status="not_evaluated",
                diagnostic=outcome["diagnostic"],
            )
        else:
            _validate_raw_snapshot(context.artifacts["snapshot"].payload)
            frozen = trajectory._evaluation_context(context)
            _, outcome = trajectory._transition(frozen)
            opening, closing = _period_frames(frozen)
            exits = tuple(
                accounting.PopulationEvent(
                    person_id=row["person_id"],
                    kind=accounting.PopulationEventKind.DEATH,
                    year=year,
                    source=f"apply_{year}:mortality-transition@1",
                )
                for row in outcome["records"]
                if not row["survives"]
            )
            account = accounting.reconcile_period(
                opening,
                closing,
                opening_year=year - 1,
                closing_year=year,
                exits=exits,
            )
            report.update(
                accounting_status="complete", account=account.to_dict()
            )
    except Exception as error:
        # Keep an accounting refusal inspectable without changing mortality
        # gates or stopping another year's already declared transition.
        report["diagnostic"] = {
            "exception_type": type(error).__name__,
            "message": str(error),
        }
        if isinstance(error, accounting.PopulationReconciliationError):
            report["diagnostic"]["reconciliation"] = error.to_dict()
    return KernelResult(
        artifacts={"account": json_bytes(report)},
        receipt={
            "accounting_status": report["accounting_status"],
            "application_status": report["application_status"],
            "completed_year": report["completed_year"],
        },
    )


class _AccountingKernel(trajectory.rt._Kernel):
    def implementation_hash(self):
        return source_hash(
            self.function,
            accounting,
            trajectory,
            trajectory.rt,
            trajectory.rt.model_module,
            dependencies=self.capabilities.dependencies,
        )


def build_accounted_trajectory_graph(**kwargs):
    """Append isolated accounting nodes to the unchanged trajectory graph."""
    require_graph()
    graph, registry = trajectory.build_trajectory_graph(**kwargs)
    registry.register(_AccountingKernel(ACCOUNT_KERNEL, _account))
    boundary = kwargs.get("boundary_year", 2014)
    nodes = tuple(
        Node(
            f"account_{year}",
            ACCOUNT_KERNEL,
            # EXPAND consumes ordinary members of its base. This separate
            # population keeps accounting outside all later transition keys.
            population="training",
            params={"year": year, "boundary_year": boundary},
            artifact_inputs=(
                ArtifactInput(
                    "transition",
                    f"apply_{year}",
                    "transition",
                    trajectory.TRANSITION_TYPE,
                ),
                ArtifactInput(
                    "snapshot",
                    f"snapshot_{year}",
                    "snapshot",
                    trajectory.SNAPSHOT_TYPE,
                ),
            ),
            artifact_outputs=(ArtifactOutput("account", ACCOUNT_TYPE),),
        )
        for year in range(boundary + 1, kwargs["end_year"] + 1)
    )
    return replace(graph, nodes=(*graph.nodes, *nodes)), registry


@dataclass(frozen=True)
class AccountedTrajectoryRun:
    """Accounting summaries and the actual graph's unmodified receipts."""

    manifest: object
    report: dict


def run_accounted_mortality_trajectory(
    *, training, rates, initial, holdouts, output_dir, **kwargs
):
    """Run once and export accounting separately from mortality evaluations.

    Graph coordinates are those of ``build_trajectory_graph``. Inputs retain
    its exact synthetic schemas; arbitrary household/location columns are
    unsupported and refused by the original source reader.
    """
    graph, registry = build_accounted_trajectory_graph(**kwargs)
    boundary = kwargs.get("boundary_year", 2014)
    years = range(boundary + 1, kwargs["end_year"] + 1)
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
    periods = {
        str(year): parse_json(
            store.load_bytes(
                manifest.nodes[f"account_{year}"].opaque_artifacts["account"]
            )
        )
        for year in years
    }
    statuses = {period["accounting_status"] for period in periods.values()}
    report = {
        "scope": "synthetic_engineering",
        "boundary_year": boundary,
        "end_year": kwargs["end_year"],
        "accounting_status": (
            "failed"
            if "failed" in statuses
            else (
                "not_evaluated" if "not_evaluated" in statuses else "complete"
            )
        ),
        "periods": periods,
    }
    (output / "manifest.json").write_text(manifest.to_json(), encoding="utf-8")
    (output / "accounting-report.json").write_bytes(json_bytes(report))
    return AccountedTrajectoryRun(manifest, report)
