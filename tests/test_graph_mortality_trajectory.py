"""Independent synthetic engineering checks for the annual mortality DAG.

All sources are generated in the test directory. Aggregate fixtures below
are deliberately hand specified and are neither native population evidence
nor scientific acceptance thresholds.
"""

import json
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from populace_dynamics.graph.model import fit_mortality
from populace_dynamics.graph.synthetic import write_synthetic_inputs

TRAJECTORY_COLUMNS = ["person_id", "age", "year", "weight"]


@pytest.fixture
def runtime():
    from populace_dynamics.graph._compat import require_graph

    try:
        require_graph()
    except ImportError as error:
        pytest.skip(str(error))
    from populace_dynamics.graph import run_mortality_trajectory

    return run_mortality_trajectory


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
        path = tmp_path / "inputs" / f"aggregate-{year}.json"
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


def _run(runtime, inputs, tmp_path, *, end_year=2017, **kwargs):
    sources = {
        **inputs,
        "holdouts": {
            year: path
            for year, path in inputs["holdouts"].items()
            if year <= end_year
        },
    }
    return runtime(
        **sources,
        end_year=end_year,
        output_dir=tmp_path / "output",
        **kwargs,
    )


def _ordered(frame):
    return (
        frame[TRAJECTORY_COLUMNS]
        .sort_values(["year", "person_id"])
        .reset_index(drop=True)
    )


def _direct_projection(inputs, *, end_year=2017, **coordinates):
    """Use the original fit/steps and an independently assembled RNG key."""
    from microcosm.graph.randomness import keyed_uniform

    from populace_dynamics.engine.steps import advance_age, apply_mortality

    artifact = fit_mortality(
        pd.DataFrame(_read(inputs["training"])),
        pd.DataFrame(_read(inputs["rates"])),
        boundary_year=2014,
        external_vintage_year=2014,
    )
    stream = (
        "sha256-u53-v1",
        coordinates.get("experiment_id", "mortality"),
        coordinates.get("replicate", 0),
        coordinates.get("base_seed", 0),
    )
    current = pd.DataFrame(_read(inputs["initial"])).sort_values("person_id")
    current["year"] = 2014
    history = [current[TRAJECTORY_COLUMNS].copy()]
    diagnostics = {}
    for year in range(2015, end_year + 1):
        current = current.sort_values("person_id").reset_index(drop=True)
        uniforms = keyed_uniform(
            stream=stream,
            keys=[
                (int(pid), "mortality", year, 0) for pid in current.person_id
            ],
        )

        class FixedUniforms:
            def __init__(self, values):
                self.values = values

            def random(self, n):
                assert n == len(self.values)
                return self.values.copy()

        context = SimpleNamespace(rng_registry=None, year=year, metadata={})
        survived = apply_mortality(
            current, context, FixedUniforms(uniforms), model=artifact.model
        )
        future = advance_age(survived, context, np.random.default_rng(0))
        probability = artifact.model.probabilities(current)
        diagnostics[str(year)] = {
            "from_year": year - 1,
            "year": year,
            "initial_records": len(current),
            "survivor_records": len(future),
            "expected_deaths": float(np.dot(current.weight, probability)),
            "generated_deaths": float(
                current.loc[
                    ~current.person_id.isin(future.person_id), "weight"
                ].sum()
            ),
            "start_mass": float(current.weight.sum()),
            "next_period_mass": float(future.weight.sum()),
        }
        history.append(future[TRAJECTORY_COLUMNS].copy())
        current = future
    return artifact.to_bytes(), _ordered(pd.concat(history)), diagnostics


def _set_death_regime(inputs, *, all_die):
    training = _read(inputs["training"])
    for row in training:
        row["death"] = 1.0 if all_die else 0.0
        row["exposure"] = 1e-9 if all_die else 1.0
    _write(inputs["training"], training)
    for path in inputs["holdouts"].values():
        holdout = _read(path)
        holdout["expected_death_rate"] = 1.0 if all_die else 0.0
        _write(path, holdout)


@pytest.mark.parametrize(
    "coordinates",
    [
        {},
        {"experiment_id": "trajectory-alternative"},
        {"replicate": 7},
        {"base_seed": 831},
    ],
)
def test_annual_projection_matches_independent_steps_and_weighted_diagnostics(
    runtime, inputs, tmp_path, coordinates
):
    result = _run(runtime, inputs, tmp_path, **coordinates)
    payload, expected, diagnostics = _direct_projection(inputs, **coordinates)
    assert result.model_payload == payload
    pd.testing.assert_frame_equal(_ordered(result.trajectory), expected)
    assert result.report["scope"] == "synthetic_engineering"
    assert result.report["engineering_verdict"] == "pass"
    assert result.report["fixture_verdict"] == "pass"
    assert set(result.report["periods"]) == {"2015", "2016", "2017"}
    for year, expected_period in diagnostics.items():
        actual = result.report["periods"][year]
        for field, value in expected_period.items():
            assert actual[field] == pytest.approx(value), (year, field)
        assert actual["engineering_verdict"] == "pass"
        assert actual["fixture_verdict"] == "pass"
        assert actual["start_mass"] == pytest.approx(
            actual["generated_deaths"] + actual["next_period_mass"]
        )


def test_expansion_preserves_every_historical_row_and_person_link(
    runtime, inputs, tmp_path
):
    result = _run(runtime, inputs, tmp_path)
    previous = result.manifest.population("initial").table("person_period")
    for year in range(2015, 2018):
        population = result.manifest.population(f"advance_{year}")
        observations = population.table("person_period")
        assert observations.person_period_id.is_unique
        assert not observations.duplicated(
            ["person_period_person_id", "person_period_period_id"]
        ).any()
        retained = observations.loc[
            observations.person_period_id.isin(previous.person_period_id),
            previous.columns,
        ]
        pd.testing.assert_frame_equal(
            retained.sort_values("person_period_id").reset_index(drop=True),
            previous.sort_values("person_period_id").reset_index(drop=True),
        )
        entrants = observations.loc[
            observations.person_period_period_id == year
        ]
        at_risk = previous.loc[
            previous.person_period_period_id == year - 1
        ].set_index("person_period_person_id")
        assert set(entrants.person_period_person_id) <= set(at_risk.index)
        for row in entrants.itertuples(index=False):
            parent = at_risk.loc[row.person_period_person_id]
            assert row.age == parent.age + 1
            assert row.sex == parent.sex
        previous = observations
    assert set(previous.person_period_period_id) == {2014, 2015, 2016, 2017}


def test_cold_warm_cache_and_exported_artifacts(runtime, inputs, tmp_path):
    cold = _run(runtime, inputs, tmp_path)
    warm = _run(runtime, inputs, tmp_path)
    assert not any(node.hit for node in cold.manifest.nodes.values())
    assert all(node.hit for node in warm.manifest.nodes.values())
    assert type(warm.manifest).__module__.startswith("microcosm.graph")
    assert cold.model_payload == warm.model_payload
    assert cold.report["periods"] == warm.report["periods"]
    pd.testing.assert_frame_equal(cold.trajectory, warm.trajectory)
    output = tmp_path / "output"
    assert _read(output / "report.json") == warm.report
    assert _read(output / "manifest.json") == json.loads(
        warm.manifest.to_json()
    )
    assert (output / "model.json").read_bytes() == warm.model_payload
    pd.testing.assert_frame_equal(
        _ordered(pd.read_csv(output / "trajectory.csv")),
        _ordered(warm.trajectory),
    )


def test_horizon_extension_reuses_fit_and_existing_annual_nodes(
    runtime, inputs, tmp_path
):
    short = _run(runtime, inputs, tmp_path, end_year=2015)
    extended = _run(runtime, inputs, tmp_path, end_year=2018)
    for name, node in short.manifest.nodes.items():
        assert extended.manifest.nodes[name].hit, name
        assert extended.manifest.nodes[name].key == node.key, name
    for year in range(2016, 2019):
        for prefix in ("apply", "advance", "age", "evaluate"):
            assert not extended.manifest.nodes[f"{prefix}_{year}"].hit
    assert short.model_payload == extended.model_payload
    pd.testing.assert_frame_equal(
        _ordered(short.trajectory),
        _ordered(extended.trajectory.query("year <= 2015")),
    )


@pytest.mark.parametrize(
    "coordinates",
    [
        {"experiment_id": "trajectory-alternative"},
        {"replicate": 7},
        {"base_seed": 831},
    ],
)
def test_stream_change_reuses_fit_but_invalidates_each_application(
    runtime, inputs, tmp_path, coordinates
):
    original = _run(runtime, inputs, tmp_path)
    changed = _run(runtime, inputs, tmp_path, **coordinates)
    for name in ("training", "fit", "initial"):
        assert changed.manifest.nodes[name].hit
        assert (
            changed.manifest.nodes[name].key
            == original.manifest.nodes[name].key
        )
    for year in range(2015, 2018):
        name = f"apply_{year}"
        assert not changed.manifest.nodes[name].hit
        assert (
            changed.manifest.nodes[name].key
            != original.manifest.nodes[name].key
        )
    assert changed.model_payload == original.model_payload
    _, expected, _ = _direct_projection(inputs, **coordinates)
    pd.testing.assert_frame_equal(_ordered(changed.trajectory), expected)


def test_holdout_change_invalidates_only_its_own_evaluation(
    runtime, inputs, tmp_path
):
    original = _run(runtime, inputs, tmp_path)
    holdout = _read(inputs["holdouts"][2016])
    holdout["expected_death_rate"] = 1.0
    holdout["fixture_max_abs_death_rate_gap"] = 0.0
    _write(inputs["holdouts"][2016], holdout)
    changed = _run(runtime, inputs, tmp_path)
    for name, node in changed.manifest.nodes.items():
        if name == "evaluate_2016":
            assert not node.hit
            assert node.key != original.manifest.nodes[name].key
        else:
            assert node.hit, name
            assert node.key == original.manifest.nodes[name].key, name
    assert changed.report["engineering_verdict"] == "pass"
    assert changed.report["fixture_verdict"] == "fail"
    assert changed.report["periods"]["2016"]["fixture_verdict"] == "fail"
    for year in ("2015", "2017"):
        assert (
            changed.report["periods"][year] == original.report["periods"][year]
        )
    assert changed.model_payload == original.model_payload
    pd.testing.assert_frame_equal(changed.trajectory, original.trajectory)


def test_recipient_change_reuses_the_fitted_model(runtime, inputs, tmp_path):
    original = _run(runtime, inputs, tmp_path)
    initial = _read(inputs["initial"])
    initial[0]["age"] += 1
    initial[0]["weight"] *= 2
    _write(inputs["initial"], initial)
    changed = _run(runtime, inputs, tmp_path)
    assert changed.manifest.nodes["fit"].hit
    assert changed.model_payload == original.model_payload
    assert not changed.manifest.nodes["initial"].hit
    assert not changed.manifest.nodes["apply_2015"].hit
    _, expected, _ = _direct_projection(inputs)
    pd.testing.assert_frame_equal(_ordered(changed.trajectory), expected)


def test_training_change_refits_and_reapplies(runtime, inputs, tmp_path):
    original = _run(runtime, inputs, tmp_path)
    training = _read(inputs["training"])
    training[0]["start_weight"] = 8.0
    _write(inputs["training"], training)
    changed = _run(runtime, inputs, tmp_path)
    assert not changed.manifest.nodes["fit"].hit
    assert not changed.manifest.nodes["apply_2015"].hit
    assert changed.model_payload != original.model_payload
    payload, expected, _ = _direct_projection(inputs)
    assert changed.model_payload == payload
    pd.testing.assert_frame_equal(_ordered(changed.trajectory), expected)


def test_complete_extinction_leaves_no_future_period_groups(
    runtime, inputs, tmp_path
):
    _set_death_regime(inputs, all_die=True)
    result = _run(runtime, inputs, tmp_path)
    warm = _run(runtime, inputs, tmp_path)
    assert all(node.hit for node in warm.manifest.nodes.values())
    assert set(result.trajectory.year) == {2014}
    first = result.report["periods"]["2015"]
    assert first["generated_deaths"] == first["start_mass"]
    assert first["survivor_records"] == 0
    assert first["next_period_mass"] == 0
    for year in (2016, 2017):
        period = result.report["periods"][str(year)]
        for field in (
            "initial_records",
            "survivor_records",
            "expected_deaths",
            "generated_deaths",
            "start_mass",
            "next_period_mass",
        ):
            assert period[field] == 0, (year, field)
        assert period["engineering_verdict"] == "not_applicable"
        assert period["fixture_verdict"] == "not_applicable"
    for year in range(2015, 2018):
        population = result.manifest.population(f"advance_{year}")
        assert population.table("period").period.tolist() == [2014]
        assert set(
            population.table("person_period").person_period_period_id
        ) == {2014}


def test_zero_mortality_keeps_all_people_and_each_periods_mass(
    runtime, inputs, tmp_path
):
    _set_death_regime(inputs, all_die=False)
    result = _run(runtime, inputs, tmp_path)
    initial = pd.DataFrame(_read(inputs["initial"]))
    for year in range(2014, 2018):
        period = result.trajectory.loc[result.trajectory.year == year]
        assert set(period.person_id) == set(initial.person_id)
        assert period.weight.sum() == initial.weight.sum()
    _, expected, _ = _direct_projection(inputs)
    pd.testing.assert_frame_equal(_ordered(result.trajectory), expected)
    for period in result.report["periods"].values():
        assert period["expected_deaths"] == 0
        assert period["generated_deaths"] == 0
        assert period["fixture_verdict"] == "pass"


def test_missing_annual_holdout_fails_closed(runtime, inputs, tmp_path):
    inputs["holdouts"].pop(2016)
    with pytest.raises(ValueError, match="holdout"):
        _run(runtime, inputs, tmp_path)


@pytest.mark.parametrize("mutation", ["year", "scope", "rate", "json"])
def test_bad_holdout_retains_gate_diagnostics_without_changing_simulation(
    runtime, inputs, tmp_path, mutation
):
    original = _run(runtime, inputs, tmp_path)
    path = inputs["holdouts"][2016]
    holdout = _read(path)
    if mutation == "year":
        holdout["year"] = 2015
    elif mutation == "scope":
        holdout["scope"] = "scientific_acceptance"
    elif mutation == "rate":
        holdout["expected_death_rate"] = float("nan")
    _write(path, holdout)
    if mutation == "json":
        path.write_text("{broken JSON")
    for cached_failure in (False, True):
        result = _run(runtime, inputs, tmp_path)
        gate = result.manifest.nodes["evaluate_2016"]
        assert gate.hit is cached_failure
        assert gate.receipt["outcome"] == "fail"
        diagnostic = result.report["periods"]["2016"]["evaluation_gate"]
        assert diagnostic["node_id"] == "evaluate_2016"
        assert diagnostic["outcome"] == "fail"
        assert diagnostic["evidence"]["exception_type"] == "ValueError"
        assert diagnostic["evidence"]["message"]
        assert result.report["fixture_verdict"] == "not_evaluated"
        for name, node in result.manifest.nodes.items():
            if name != "evaluate_2016":
                assert node.hit, name
                assert node.key == original.manifest.nodes[name].key
        pd.testing.assert_frame_equal(result.trajectory, original.trajectory)
        assert _read(tmp_path / "output" / "report.json") == result.report
        assert _read(tmp_path / "output" / "manifest.json") == json.loads(
            result.manifest.to_json()
        )


def test_unsupported_age_stops_future_application_and_preserves_evidence(
    runtime, inputs, tmp_path
):
    _set_death_regime(inputs, all_die=False)
    initial = _read(inputs["initial"])
    initial[0]["age"] = 120
    _write(inputs["initial"], initial)
    short = _run(runtime, inputs, tmp_path, end_year=2015)
    assert short.trajectory.query("year == 2015").age.max() == 121
    for cached_failure in (False, True):
        result = _run(runtime, inputs, tmp_path)
        gate = result.manifest.nodes["apply_2016"]
        assert gate.hit is cached_failure
        assert gate.receipt["outcome"] == "fail"
        assert set(gate.opaque_artifacts) == {"transition"}
        assert gate.receipt["application_status"] == "failed"
        diagnostic = result.report["periods"]["2016"]["application_gate"]
        assert diagnostic["node_id"] == "apply_2016"
        assert diagnostic["outcome"] == "fail"
        assert diagnostic["evidence"]["exception_type"] == "ValueError"
        assert "age" in diagnostic["evidence"]["message"].lower()
        # The exact pinned core executes guarded descendants. Their native
        # receipts stay honest; application-level blocked is not unreached.
        for name in ("advance_2016", "apply_2017", "advance_2017"):
            assert (
                result.manifest.nodes[name].receipt["application_status"]
                == "blocked"
            )
        for year in (2016, 2017):
            assert (
                result.manifest.nodes[f"evaluate_{year}"].receipt["outcome"]
                == "evidence_absent"
            )
            period = result.report["periods"][str(year)]
            assert period["completed_year"] == 2015
            assert period["engineering_verdict"] == "not_evaluated"
            population = result.manifest.population(f"advance_{year}")
            pd.testing.assert_frame_equal(
                population.table("person_period"),
                short.manifest.population("advance_2015").table(
                    "person_period"
                ),
            )
        assert result.report["periods"]["2017"]["application_status"] == (
            "blocked"
        )
        assert result.report["completed_year"] == 2015
        assert result.report["engineering_verdict"] == "not_evaluated"
        assert result.model_payload == short.model_payload
        pd.testing.assert_frame_equal(result.trajectory, short.trajectory)
        assert _read(tmp_path / "output" / "report.json") == result.report
        assert _read(tmp_path / "output" / "manifest.json") == json.loads(
            result.manifest.to_json()
        )


def test_household_accounting_remains_explicitly_unsupported(
    runtime, inputs, tmp_path
):
    with pytest.raises(ValueError, match="household"):
        _run(runtime, inputs, tmp_path, household_accounting=True)


def test_known_fixture_failure_survives_later_missing_evaluation(
    runtime, inputs, tmp_path
):
    failed_fixture = _read(inputs["holdouts"][2015])
    failed_fixture["expected_death_rate"] = 1.0
    failed_fixture["fixture_max_abs_death_rate_gap"] = 0.0
    _write(inputs["holdouts"][2015], failed_fixture)
    inputs["holdouts"][2016].write_text("{broken JSON")
    result = _run(runtime, inputs, tmp_path)
    assert result.report["periods"]["2015"]["fixture_verdict"] == "fail"
    assert result.report["periods"]["2016"]["fixture_verdict"] == (
        "not_evaluated"
    )
    assert result.report["periods"]["2017"]["engineering_verdict"] == "pass"
    assert result.report["fixture_verdict"] == "fail"
    assert result.report["execution_status"] == "failed"
    assert result.report["completed_year"] == 2017


def test_zero_risk_set_cannot_certify_an_unexpected_future_observation(
    runtime, inputs, tmp_path, monkeypatch
):
    from dataclasses import replace

    from populace_dynamics.graph import trajectory

    _set_death_regime(inputs, all_die=True)
    original_snapshot = trajectory._snapshot

    def snapshot_with_unexpected_future_row(context):
        result = original_snapshot(context)
        if context.params["year"] != 2016:
            return result
        payload = json.loads(result.artifacts["snapshot"])
        record = dict(payload["observations"][0])
        record["person_period_id"] = 999
        record["person_period_period_id"] = 2016
        record["age"] += 2
        payload["observations"].append(record)
        payload["periods"].append({"period_id": 2016, "period": 2016})
        payload["weights"].append(1.0)
        return replace(
            result, artifacts={"snapshot": json.dumps(payload).encode()}
        )

    monkeypatch.setattr(
        trajectory, "_snapshot", snapshot_with_unexpected_future_row
    )
    result = _run(runtime, inputs, tmp_path)
    period = result.report["periods"]["2016"]
    assert period["initial_records"] == 0
    assert period["survivor_records"] == 1
    assert period["engineering_verdict"] == "fail"
    assert period["fixture_verdict"] == "not_applicable"
    assert result.manifest.nodes["evaluate_2016"].receipt["outcome"] == "fail"
    assert result.report["engineering_verdict"] == "fail"


@pytest.mark.parametrize(
    "payload_kind", ["malformed_json", "unknown_status", "before_boundary"]
)
def test_malformed_prerequisite_does_not_invent_completed_year(
    runtime, monkeypatch, payload_kind
):
    from populace_dynamics.graph import trajectory

    def unexpected_application(context):
        raise AssertionError("invalid prerequisite reached model application")

    monkeypatch.setattr(trajectory, "_apply_complete", unexpected_application)
    payload = b"{broken JSON"
    if payload_kind != "malformed_json":
        payload = json.dumps(
            {
                "format": "populace-dynamics.mortality-transition",
                "schema_version": 1,
                "from_year": 2015,
                "year": 2016,
                "status": (
                    "unknown" if payload_kind == "unknown_status" else "failed"
                ),
                "completed_year": (
                    2013 if payload_kind == "before_boundary" else 2015
                ),
                "records": [],
                "diagnostic": {"message": "prior failure"},
            }
        ).encode()
    context = SimpleNamespace(
        params={"year": 2017, "boundary_year": 2014},
        artifacts={"previous_transition": SimpleNamespace(payload=payload)},
    )
    result = trajectory._apply(context)
    outcome = json.loads(result.artifacts["transition"])
    assert outcome["status"] == "failed"
    assert outcome["completed_year"] == 2014
    assert outcome["records"] == []
    assert outcome["diagnostic"]["exception_type"] == "ValueError"
    assert result.receipt["outcome"] == "fail"


def test_blocked_years_do_not_apply_laws_or_parse_holdouts(
    runtime, inputs, tmp_path, monkeypatch
):
    from populace_dynamics.graph import trajectory

    _set_death_regime(inputs, all_die=False)
    initial = _read(inputs["initial"])
    initial[0]["age"] = 120
    _write(inputs["initial"], initial)
    for year in (2016, 2017):
        # The executor still hashes these bytes, but guarded evaluations
        # must not parse them after application fails in 2016.
        inputs["holdouts"][year].write_text("{unparseable held-out fixture")

    application_years, ageing_years, holdout_years = [], [], []
    apply_complete = trajectory._apply_complete
    advance_age = trajectory.rt.advance_age
    holdout = trajectory._holdout

    def tracked_application(context):
        application_years.append(context.params["year"])
        assert context.params["year"] <= 2016
        return apply_complete(context)

    def tracked_ageing(frame, context, rng):
        ageing_years.append(context.year)
        assert context.year == 2015
        return advance_age(frame, context, rng)

    def tracked_holdout(context):
        holdout_years.append(context.params["year"])
        assert context.params["year"] == 2015
        return holdout(context)

    monkeypatch.setattr(trajectory, "_apply_complete", tracked_application)
    monkeypatch.setattr(trajectory.rt, "advance_age", tracked_ageing)
    monkeypatch.setattr(trajectory, "_holdout", tracked_holdout)
    result = _run(runtime, inputs, tmp_path)
    assert application_years == [2015, 2016]
    assert ageing_years == [2015]
    assert holdout_years == [2015]
    assert result.report["completed_year"] == 2015
    assert (
        result.report["periods"]["2016"]["application_gate"]["evidence"][
            "exception_type"
        ]
        == "ValueError"
    )
    assert result.report["periods"]["2017"]["application_status"] == (
        "blocked"
    )
