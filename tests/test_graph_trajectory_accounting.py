"""Invented-source checks of accounting on the actual optional graph."""

import copy
import json
import math
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from populace_dynamics.graph.synthetic import write_synthetic_inputs


@pytest.fixture
def runtime():
    from populace_dynamics.graph._compat import require_graph

    try:
        require_graph()
    except ImportError as error:
        pytest.skip(str(error))
    from populace_dynamics.graph import trajectory_accounting

    return trajectory_accounting


def _read(path):
    return json.loads(path.read_text())


def _write(path, value):
    path.write_text(json.dumps(value))


@pytest.fixture
def inputs(tmp_path):
    sources = write_synthetic_inputs(tmp_path / "inputs")
    sources.pop("holdout")
    holdouts = {}
    for year in range(2015, 2019):
        path = tmp_path / "inputs" / f"annual-{year}.json"
        _write(
            path,
            {
                "scope": "synthetic_engineering",
                "year": year,
                "expected_death_rate": 0.2,
                "fixture_max_abs_death_rate_gap": 0.25,
            },
        )
        holdouts[year] = path
    return {**sources, "holdouts": holdouts}


def _sources(inputs, end_year):
    return {
        **inputs,
        "holdouts": {
            year: path
            for year, path in inputs["holdouts"].items()
            if year <= end_year
        },
    }


def _run(runtime, inputs, tmp_path, *, end_year=2017, **kwargs):
    return runtime.run_accounted_mortality_trajectory(
        **_sources(inputs, end_year),
        end_year=end_year,
        output_dir=tmp_path / "output",
        **kwargs,
    )


def _regime(inputs, *, all_die):
    training = _read(inputs["training"])
    for row in training:
        row["death"] = 1.0 if all_die else 0.0
        row["exposure"] = 1e-9 if all_die else 1.0
    _write(inputs["training"], training)


def _artifact(runtime, result, tmp_path, node, name):
    store = runtime.ContentStore(tmp_path / "output" / "store")
    return runtime.parse_json(
        store.load_bytes(result.manifest.nodes[node].opaque_artifacts[name])
    )


def _context(runtime, result, tmp_path, year=2015):
    return SimpleNamespace(
        params={"year": year, "boundary_year": 2014},
        sources={},
        artifacts={
            name: SimpleNamespace(
                payload=runtime.json_bytes(
                    _artifact(runtime, result, tmp_path, node, name)
                )
            )
            for name, node in (
                ("transition", f"apply_{year}"),
                ("snapshot", f"snapshot_{year}"),
            )
        },
    )


def test_actual_graph_preserves_original_keys_populations_and_evaluations(
    runtime, inputs, tmp_path
):
    original = runtime.trajectory.run_mortality_trajectory(
        **_sources(inputs, 2017),
        end_year=2017,
        output_dir=tmp_path / "output",
    )
    result = _run(runtime, inputs, tmp_path)
    for name, node in original.manifest.nodes.items():
        actual = result.manifest.nodes[name]
        assert actual.hit, name
        assert actual.key == node.key, name
        assert actual.receipt == node.receipt, name
    assert result.report["accounting_status"] == "complete"
    for year in range(2015, 2018):
        name = f"advance_{year}"
        old = original.manifest.population(name)
        new = result.manifest.population(name)
        pd.testing.assert_frame_equal(
            old.table("person_period"), new.table("person_period")
        )
        assert not result.manifest.nodes[f"account_{year}"].hit
        period = result.report["periods"][str(year)]
        assert period["application_status"] == "complete"
        assert period["completed_year"] == year
        account = period["account"]
        assert account["status"] == runtime.accounting.ENGINEERING_STATUS
        transition = _artifact(
            runtime, result, tmp_path, f"apply_{year}", "transition"
        )
        deaths = [row for row in transition["records"] if not row["survives"]]
        assert account["counts"]["exits_total"] == len(deaths)
        assert account["counts"]["exits_by_kind"]["death"] == len(deaths)
        assert account["counts"]["additions_total"] == 0
        weights = account["weights"]
        assert weights["revaluation"]["total"] == 0
        assert weights["closing"] == math.fsum(
            (weights["opening"], -weights["exits_total"])
        )
        assert account["residuals"]["count"] == 0
        assert account["residuals"]["weight"] == 0
    assert _read(tmp_path / "output" / "accounting-report.json") == (
        result.report
    )
    assert _read(tmp_path / "output" / "manifest.json") == json.loads(
        result.manifest.to_json()
    )
    # Existing outputs from the original runner were not overwritten.
    assert _read(tmp_path / "output" / "report.json") == original.report


def test_cold_warm_and_horizon_extension(runtime, inputs, tmp_path):
    cold = _run(runtime, inputs, tmp_path, end_year=2015)
    warm = _run(runtime, inputs, tmp_path, end_year=2015)
    assert not any(node.hit for node in cold.manifest.nodes.values())
    assert all(node.hit for node in warm.manifest.nodes.values())
    assert cold.report == warm.report
    extended = _run(runtime, inputs, tmp_path, end_year=2018)
    for name, node in warm.manifest.nodes.items():
        assert extended.manifest.nodes[name].hit, name
        assert extended.manifest.nodes[name].key == node.key, name
    assert extended.report["periods"]["2015"] == cold.report["periods"]["2015"]
    assert not extended.manifest.nodes["account_2018"].hit


@pytest.mark.parametrize("malformed", [False, True])
def test_holdout_changes_only_its_evaluation(
    runtime, inputs, tmp_path, malformed
):
    original = _run(runtime, inputs, tmp_path)
    path = inputs["holdouts"][2016]
    if malformed:
        path.write_text("{invalid fixture JSON")
    else:
        holdout = _read(path)
        holdout["expected_death_rate"] = 1.0
        holdout["fixture_max_abs_death_rate_gap"] = 0.0
        _write(path, holdout)
    changed = _run(runtime, inputs, tmp_path)
    for name, node in changed.manifest.nodes.items():
        if name == "evaluate_2016":
            assert not node.hit
            assert node.receipt["outcome"] == "fail"
        else:
            assert node.hit, name
            assert node.key == original.manifest.nodes[name].key, name
    assert changed.report == original.report


@pytest.mark.parametrize("all_die", [False, True])
def test_extinction_and_zero_mortality(runtime, inputs, tmp_path, all_die):
    _regime(inputs, all_die=all_die)
    result = _run(runtime, inputs, tmp_path)
    for year in range(2015, 2018):
        period = result.report["periods"][str(year)]
        assert period["accounting_status"] == "complete"
        account = period["account"]
        counts = account["counts"]
        expected_opening = 0 if all_die and year > 2015 else 20
        assert counts["opening"] == expected_opening
        assert counts["closing"] == (0 if all_die else 20)
        assert counts["exits_total"] == (expected_opening if all_die else 0)
        assert account["opening_year"] == year - 1
        assert account["closing_year"] == year
        assert account["residuals"]["count"] == 0
    if all_die:
        population = result.manifest.population("advance_2017")
        assert population.table("period").period.tolist() == [2014]


def test_failed_and_blocked_application_never_reconciles_stale_snapshots(
    runtime, inputs, tmp_path, monkeypatch
):
    _regime(inputs, all_die=False)
    initial = _read(inputs["initial"])
    initial[0]["age"] = 120
    _write(inputs["initial"], initial)
    original = runtime.accounting.reconcile_period
    calls = []

    def tracked(*args, **kwargs):
        calls.append(kwargs["closing_year"])
        return original(*args, **kwargs)

    monkeypatch.setattr(runtime.accounting, "reconcile_period", tracked)
    cold = _run(runtime, inputs, tmp_path)
    warm = _run(runtime, inputs, tmp_path)
    assert calls == [2015]
    assert cold.report == warm.report
    assert all(node.hit for node in warm.manifest.nodes.values())
    assert cold.report["accounting_status"] == "not_evaluated"
    for year, status in ((2016, "failed"), (2017, "blocked")):
        period = cold.report["periods"][str(year)]
        assert period["application_status"] == status
        assert period["completed_year"] == 2015
        assert period["accounting_status"] == "not_evaluated"
        assert period["account"] is None
        transition = _artifact(
            runtime, cold, tmp_path, f"apply_{year}", "transition"
        )
        assert period["diagnostic"] == transition["diagnostic"]


def test_accounting_error_does_not_change_mortality_or_later_application(
    runtime, inputs, tmp_path, monkeypatch
):
    def refuse(*args, **kwargs):
        raise runtime.accounting.PopulationAccountingInputError(
            "invented accounting refusal"
        )

    monkeypatch.setattr(runtime.accounting, "reconcile_period", refuse)
    result = _run(runtime, inputs, tmp_path)
    assert result.report["accounting_status"] == "failed"
    for year in range(2015, 2018):
        period = result.report["periods"][str(year)]
        assert period["account"] is None
        assert period["application_status"] == "complete"
        assert period["completed_year"] == year
        assert period["diagnostic"]["message"] == "invented accounting refusal"
        assert (
            result.manifest.nodes[f"apply_{year}"].receipt["outcome"] == "pass"
        )
        assert (
            result.manifest.nodes[f"evaluate_{year}"].receipt["outcome"]
            == "pass"
        )


@pytest.mark.parametrize(
    "mutation",
    ["person", "observation", "boolean", "probability", "missing_record"],
)
def test_transition_records_must_bind_to_snapshot(
    runtime, inputs, tmp_path, mutation
):
    result = _run(runtime, inputs, tmp_path, end_year=2015)
    context = _context(runtime, result, tmp_path)
    value = runtime.parse_json(context.artifacts["transition"].payload)
    row = value["records"][0]
    if mutation == "person":
        row["person_id"] += 9999
    elif mutation == "observation":
        row["observation_id"] += 9999
    elif mutation == "boolean":
        row["survives"] = 1
    elif mutation == "probability":
        row["death_probability"] = 1.1
    else:
        value["records"].pop()
    context.artifacts["transition"].payload = runtime.json_bytes(value)
    report = runtime.parse_json(runtime._account(context).artifacts["account"])
    assert report["accounting_status"] == "failed"
    assert report["account"] is None
    assert report["diagnostic"]["exception_type"] == "ValueError"


@pytest.mark.parametrize("mutation", ["omit_survivor", "retain_death"])
def test_endpoint_differences_do_not_infer_deaths(
    runtime, inputs, tmp_path, mutation
):
    result = _run(runtime, inputs, tmp_path, end_year=2015)
    context = _context(runtime, result, tmp_path)
    snapshot = runtime.parse_json(context.artifacts["snapshot"].payload)
    transition = runtime.parse_json(context.artifacts["transition"].payload)
    rows = snapshot["observations"]
    if mutation == "omit_survivor":
        index = next(
            i
            for i, row in enumerate(rows)
            if row["person_period_period_id"] == 2015
        )
        rows.pop(index)
        snapshot["weights"].pop(index)
        expected = "undeclared_exit"
    else:
        dead = next(
            row for row in transition["records"] if not row["survives"]
        )
        index = next(
            i
            for i, row in enumerate(rows)
            if row["person_period_id"] == dead["observation_id"]
        )
        child = {
            **rows[index],
            "person_period_id": 9999,
            "person_period_period_id": 2015,
        }
        rows.append(child)
        snapshot["weights"].append(snapshot["weights"][index])
        expected = "exit_contradicted_by_closing"
    context.artifacts["snapshot"].payload = runtime.json_bytes(snapshot)
    report = runtime.parse_json(runtime._account(context).artifacts["account"])
    assert report["accounting_status"] == "failed"
    assert report["account"] is None
    discrepancies = report["diagnostic"]["reconciliation"]["discrepancies"]
    assert expected in {item["kind"] for item in discrepancies}


def test_accounting_copies_rows_without_mutating_snapshot_or_columns(
    runtime, inputs, tmp_path
):
    result = _run(runtime, inputs, tmp_path, end_year=2015)
    context = _context(runtime, result, tmp_path)
    before = copy.deepcopy(context)
    frozen = runtime.trajectory._evaluation_context(context)
    opening, closing = runtime._period_frames(frozen)
    for frame in (opening, closing):
        assert {"age", "sex", "person_period_id"} <= set(frame.columns)
    opening.loc[:, "age"] = -99
    assert (frozen.tables["person_period"].age >= 0).all()
    runtime._account(context)
    assert (
        context.artifacts["snapshot"].payload
        == before.artifacts["snapshot"].payload
    )
    assert (
        context.artifacts["transition"].payload
        == before.artifacts["transition"].payload
    )


@pytest.mark.parametrize("column", ["atomic_location_id", "household_id"])
def test_initial_reader_refuses_unsupported_location_and_household_columns(
    runtime, inputs, tmp_path, column
):
    initial = _read(inputs["initial"])
    for row in initial:
        row[column] = "invented-anchor"
    _write(inputs["initial"], initial)
    with pytest.raises(Exception, match="unsupported fields"):
        _run(runtime, inputs, tmp_path)
    assert _read(inputs["initial"]) == initial


def test_snapshot_refuses_unsupported_location_column(
    runtime, inputs, tmp_path
):
    result = _run(runtime, inputs, tmp_path, end_year=2015)
    context = _context(runtime, result, tmp_path)
    snapshot = runtime.parse_json(context.artifacts["snapshot"].payload)
    for row in snapshot["observations"]:
        row["atomic_location_id"] = "invented-anchor"
    context.artifacts["snapshot"].payload = runtime.json_bytes(snapshot)
    report = runtime.parse_json(runtime._account(context).artifacts["account"])
    assert report["accounting_status"] == "failed"
    assert report["account"] is None
    assert "snapshot row binding" in report["diagnostic"]["message"]


@pytest.mark.parametrize(
    "mutation",
    ["period_alias", "duplicate_history", "weight_length", "future_period"],
)
def test_snapshot_binding_and_period_history_fail_closed(
    runtime, inputs, tmp_path, mutation
):
    result = _run(runtime, inputs, tmp_path, end_year=2015)
    context = _context(runtime, result, tmp_path)
    snapshot = runtime.parse_json(context.artifacts["snapshot"].payload)
    if mutation == "period_alias":
        snapshot["periods"].append({"period_id": 9999, "period": 2015})
    elif mutation == "duplicate_history":
        snapshot["observations"].append(
            {**snapshot["observations"][0], "person_period_id": 9999}
        )
        snapshot["weights"].append(snapshot["weights"][0])
    elif mutation == "weight_length":
        snapshot["weights"].pop()
    else:
        snapshot["periods"].append({"period_id": 2016, "period": 2016})
    context.artifacts["snapshot"].payload = runtime.json_bytes(snapshot)
    report = runtime.parse_json(runtime._account(context).artifacts["account"])
    assert report["accounting_status"] == "failed"
    assert report["account"] is None
    assert report["diagnostic"]["exception_type"] == "ValueError"


def test_changed_snapshot_survivor_weight_is_reported_separately_from_evaluation(
    runtime, inputs, tmp_path, monkeypatch
):
    original = runtime.trajectory._snapshot

    def changed_weight(context):
        result = original(context)
        snapshot = runtime.parse_json(result.artifacts["snapshot"])
        if context.params["year"] == 2016:
            index = next(
                i
                for i, row in enumerate(snapshot["observations"])
                if row["person_period_period_id"] == 2016
            )
            snapshot["weights"][index] += 3.0
        return replace(
            result, artifacts={"snapshot": runtime.json_bytes(snapshot)}
        )

    monkeypatch.setattr(runtime.trajectory, "_snapshot", changed_weight)
    result = _run(runtime, inputs, tmp_path)
    account = result.report["periods"]["2016"]["account"]
    assert account["weights"]["revaluation"]["carried"] == 3.0
    assert account["residuals"]["weight"] == 0.0
    assert result.report["accounting_status"] == "complete"
    assert result.manifest.nodes["evaluate_2016"].receipt["outcome"] == "fail"
    assert result.manifest.nodes["apply_2017"].receipt["outcome"] == "pass"
    assert result.manifest.nodes["evaluate_2017"].receipt["outcome"] == "pass"


def test_incomplete_application_does_not_parse_snapshot(runtime):
    outcome = {
        "format": runtime.trajectory.TRANSITION_TYPE.name,
        "schema_version": 1,
        "from_year": 2015,
        "year": 2016,
        "status": "failed",
        "completed_year": 2015,
        "records": [],
        "diagnostic": {"message": "synthetic prior refusal"},
    }
    context = SimpleNamespace(
        params={"year": 2016, "boundary_year": 2014},
        artifacts={
            "transition": SimpleNamespace(payload=runtime.json_bytes(outcome)),
            "snapshot": SimpleNamespace(payload=b"{invalid snapshot JSON"),
        },
    )
    report = runtime.parse_json(runtime._account(context).artifacts["account"])
    assert report["accounting_status"] == "not_evaluated"
    assert report["account"] is None
    assert report["diagnostic"] == outcome["diagnostic"]


@pytest.mark.parametrize(
    "mutation", ["json", "completed_year", "unknown_status"]
)
def test_malformed_transition_does_not_invent_application_completion(
    runtime, mutation
):
    value = {
        "format": runtime.trajectory.TRANSITION_TYPE.name,
        "schema_version": 1,
        "from_year": 2015,
        "year": 2016,
        "status": "failed",
        "completed_year": 2015,
        "records": [],
        "diagnostic": {"message": "synthetic prior refusal"},
    }
    if mutation == "completed_year":
        value["completed_year"] = 2013
    elif mutation == "unknown_status":
        value["status"] = "unknown"
    context = SimpleNamespace(
        params={"year": 2016, "boundary_year": 2014},
        artifacts={
            "transition": SimpleNamespace(
                payload=(
                    b"{invalid"
                    if mutation == "json"
                    else runtime.json_bytes(value)
                )
            )
        },
    )
    report = runtime.parse_json(runtime._account(context).artifacts["account"])
    assert report["accounting_status"] == "failed"
    assert report["account"] is None
    assert report["application_status"] is None
    assert report["completed_year"] is None


def test_runner_requires_exact_annual_holdouts(runtime, inputs, tmp_path):
    inputs["holdouts"].pop(2016)
    with pytest.raises(ValueError, match="exactly one source per year"):
        _run(runtime, inputs, tmp_path)


@pytest.mark.parametrize("value", ["1.0", True])
def test_raw_snapshot_weights_are_checked_before_float_conversion(
    runtime, inputs, tmp_path, value
):
    result = _run(runtime, inputs, tmp_path, end_year=2015)
    context = _context(runtime, result, tmp_path)
    snapshot = runtime.parse_json(context.artifacts["snapshot"].payload)
    snapshot["weights"][0] = value
    context.artifacts["snapshot"].payload = runtime.json_bytes(snapshot)
    report = runtime.parse_json(runtime._account(context).artifacts["account"])
    assert report["accounting_status"] == "failed"
    assert report["account"] is None
    assert (
        report["diagnostic"]["exception_type"]
        == "PopulationAccountingInputError"
    )
    assert "real number" in report["diagnostic"]["message"]


@pytest.mark.parametrize("identifier", ["person", "observation"])
def test_oversized_raw_identifier_cannot_wrap_into_transition_binding(
    runtime, inputs, tmp_path, identifier
):
    result = _run(runtime, inputs, tmp_path, end_year=2015)
    context = _context(runtime, result, tmp_path)
    snapshot = runtime.parse_json(context.artifacts["snapshot"].payload)
    transition = runtime.parse_json(context.artifacts["transition"].payload)
    if identifier == "person":
        column, field = "person_period_person_id", "person_id"
    else:
        column, field = "person_period_id", "observation_id"
    original_id = transition["records"][0][field]
    for row in snapshot["observations"]:
        if row[column] == original_id:
            row[column] = 2**64 - 1
    transition["records"][0][field] = -1
    context.artifacts["snapshot"].payload = runtime.json_bytes(snapshot)
    context.artifacts["transition"].payload = runtime.json_bytes(transition)
    report = runtime.parse_json(runtime._account(context).artifacts["account"])
    assert report["accounting_status"] == "failed"
    assert report["account"] is None
    assert (
        report["diagnostic"]["exception_type"]
        == "PopulationAccountingInputError"
    )
    assert "signed int64" in report["diagnostic"]["message"]


@pytest.mark.parametrize("status", ["failed", "blocked"])
def test_overflowing_diagnostic_becomes_a_serializable_accounting_refusal(
    runtime, status
):
    payload = (
        '{"format":"populace-dynamics.mortality-transition",'
        '"schema_version":1,"from_year":2015,"year":2016,'
        f'"status":"{status}","completed_year":2015,"records":[], '
        '"diagnostic":{"message":"synthetic refusal","nested":[1e400]}}'
    ).encode()
    context = SimpleNamespace(
        params={"year": 2016, "boundary_year": 2014},
        artifacts={"transition": SimpleNamespace(payload=payload)},
    )
    report = runtime.parse_json(runtime._account(context).artifacts["account"])
    assert report["accounting_status"] == "failed"
    assert report["account"] is None
    assert report["application_status"] is None
    assert report["completed_year"] is None
    assert report["diagnostic"]["exception_type"] == "ValueError"
    json.dumps(report, allow_nan=False)


@pytest.mark.parametrize(
    "module", ["accounting", "trajectory", "runtime", "model"]
)
def test_accounting_hash_includes_reused_source_modules(
    runtime, monkeypatch, module
):
    _, registry = runtime.build_accounted_trajectory_graph(end_year=2015)
    kernel = registry.get(runtime.ACCOUNT_KERNEL)
    modules = {
        "accounting": runtime.accounting,
        "trajectory": runtime.trajectory,
        "runtime": runtime.trajectory.rt,
        "model": runtime.trajectory.rt.model_module,
    }
    target = Path(modules[module].__file__).resolve()
    before = kernel.implementation_hash()
    original = Path.read_bytes

    def changed(path):
        payload = original(path)
        return (
            payload + b"\n# synthetic source change\n"
            if path.resolve() == target
            else payload
        )

    monkeypatch.setattr(Path, "read_bytes", changed)
    assert kernel.implementation_hash() != before


def test_account_nodes_have_only_artifact_dependencies(runtime):
    graph, _ = runtime.build_accounted_trajectory_graph(end_year=2017)
    for node in graph.nodes:
        if not node.id.startswith("account_"):
            continue
        assert node.population == "training"
        assert node.inputs == ()
        assert node.sources == ()
        assert {item.name for item in node.artifact_inputs} == {
            "transition",
            "snapshot",
        }
