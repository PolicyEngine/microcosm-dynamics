"""INVENTED DATA - NOT A COMPARISON: joint ordering and conservation."""

from collections import Counter
from dataclasses import replace
from types import SimpleNamespace

import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.engine.loop import ProjectionResult
from populace_dynamics.fra68_track.benefits import PersonScenario
from populace_dynamics.track_a_v2 import benefits, estimands, histories, runner
from populace_dynamics.track_a_v2.invented import invented_parameters
from populace_dynamics.track_a_v2.matrix import MATRIX


def _row(base=120.0, reform=100.0):
    return {
        "draw": 0,
        "person_id": 1,
        "family_unit_id": 1,
        "birth_year": 1960,
        "weight": 2.0,
        "beneficiary_base": base > 0,
        "beneficiary_reform": reform > 0,
        "benefit_base": base,
        "benefit_reform": reform,
        "benefit_components": {
            "retired_worker": {"base": base, "reform": reform}
        },
    }


@pytest.fixture
def staged(monkeypatch):
    """An invented seam tests scheduling separately from calculator amounts."""
    state = pd.DataFrame(
        [{"person_id": 1, "birth_year": 1960, "year": 2030, "weight": 2.0}]
    )
    projection = ProjectionResult((state,), (), 0)
    static = pd.DataFrame(
        [{"person_id": 1, "family_unit_id": 1, "ss_receipt_opening": False}]
    ).set_index("person_id")
    cohort = SimpleNamespace(
        data_provenance="invented", persons_by_id=static, opening={}
    )
    inputs = SimpleNamespace(
        cohort=cohort,
        params=invented_parameters(),
        baseline=None,
        claiming_pmf={},
    )
    calls = Counter()

    def project(*args, **kwargs):
        calls["projection"] += 1
        return {0: projection}, {}

    def validate():
        calls["validation"] += 1
        return Counter()

    def collect(*args, **kwargs):
        calls["benefits"] += 1
        return [_row()], Counter()

    def scenario(*args, **kwargs):
        calls["benefits"] += 1
        amount = 10.0 if kwargs["scenario"].name == "baseline" else 9.0
        return {
            1: PersonScenario(
                {"retired_worker": amount}, "projected", "retired", 2027, 67
            )
        }, Counter()

    monkeypatch.setattr(runner, "_before_projection", lambda *args: None)
    monkeypatch.setattr(
        runner, "claiming_schedule", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(runner.legacy, "_project_population", project)
    monkeypatch.setattr(
        histories,
        "HistoryValidator",
        lambda *args: SimpleNamespace(validate_requested=validate),
    )
    monkeypatch.setattr(benefits, "collect_reference_benefit_rows", collect)
    monkeypatch.setattr(benefits, "scenario_benefits", scenario)
    return inputs, projection, calls


def test_complete_matrix_uses_one_ensemble_and_conserves_state(staged):
    """All 68 rows share one ensemble; every original slice stays identical."""
    inputs, projection, calls = staged
    before = runner.projection_hash(projection)
    result = runner.run_joint(inputs, draw_indices=(0,))
    assert result["attempt"]["status"] == "completed", result["attempt"]
    assert calls["projection"] == calls["validation"] == 1
    assert list(result["rows"]) == [row.key for row in MATRIX]
    assert all(len(row["groups"]) == 5 for row in result["rows"].values())
    assert runner.projection_hash(projection) == before
    assert (
        result["projection_hashes_before"] == result["projection_hashes_after"]
    )
    assert result["headlines"] == ["D×R0", "D×F0"]
    assert not result["attempt"]["uncomputed_rows"]


def test_history_refusal_precedes_every_benefit_and_tabulation(
    staged, monkeypatch
):
    """An intended unsupported history stops step 2 before any amount or row."""
    inputs, _, calls = staged

    def refuse():
        raise histories.HistoryRefusal(1, "intended two-award history")

    monkeypatch.setattr(
        histories,
        "HistoryValidator",
        lambda *args: SimpleNamespace(validate_requested=refuse),
    )
    result = runner.run_joint(inputs, draw_indices=(0,))
    assert result["attempt"]["step"] == 2
    assert result["attempt"]["first_failing_person_draw"] == {
        "person_id": 1,
        "draw": 0,
    }
    assert calls["benefits"] == 0
    assert len(result["attempt"]["uncomputed_rows"]) == 68
    assert result["rows"] == {}


@pytest.mark.parametrize("mechanism", ("L", "D", "S", "DS"))
@pytest.mark.parametrize("direction", ("baseline_only", "reform_only"))
def test_unfiltered_r_refuses_before_any_tabulation(
    staged, monkeypatch, mechanism, direction
):
    """Intended unequal R membership in either direction blocks all 68 rows."""
    inputs, _, _ = staged
    original = benefits.collect_reference_benefit_rows
    tabs = []

    def collect(*args, **kwargs):
        if kwargs["mechanism"] == mechanism:
            return [
                _row(120, 0) if direction == "baseline_only" else _row(0, 120)
            ], Counter()
        return original(*args, **kwargs)

    monkeypatch.setattr(benefits, "collect_reference_benefit_rows", collect)
    monkeypatch.setattr(
        estimands, "tabulate_rows", lambda *args, **kwargs: tabs.append(args)
    )
    result = runner.run_joint(inputs, draw_indices=(0,))
    assert result["attempt"]["status"] == "refused"
    assert result["attempt"]["step"] == 3
    assert result["attempt"]["first_failing_person_draw"] == {
        "person_id": 1,
        "draw": 0,
    }
    assert not tabs
    assert len(result["attempt"]["uncomputed_rows"]) == 68


@pytest.mark.parametrize("mechanism", ("L", "D", "S", "DS"))
@pytest.mark.parametrize("direction", ("baseline_only", "reform_only"))
def test_unexplained_f_c0_refuses_whole_attempt(
    staged, monkeypatch, mechanism, direction
):
    """An intended unexplained F C0 difference stops every tabulation at 5."""
    inputs, _, _ = staged
    original = benefits.scenario_benefits
    tabs = []

    def scenario(*args, **kwargs):
        people, counters = original(*args, **kwargs)
        baseline = kwargs["scenario"].name == "baseline"
        if kwargs["mechanism"] == mechanism and baseline == (
            direction == "reform_only"
        ):
            people[1] = replace(people[1], components={"retired_worker": 0.0})
        return people, counters

    monkeypatch.setattr(benefits, "scenario_benefits", scenario)
    monkeypatch.setattr(
        estimands, "tabulate_rows", lambda *args, **kwargs: tabs.append(args)
    )
    result = runner.run_joint(inputs, draw_indices=(0,))
    assert result["attempt"]["status"] == "refused"
    assert result["attempt"]["step"] == 5
    assert not tabs
    assert len(result["attempt"]["uncomputed_rows"]) == 68


def test_projection_mutation_precedes_membership_and_tabulation(
    staged, monkeypatch
):
    """An intended mutation of a shared slice refuses at step 4, with no rows."""
    inputs, projection, _ = staged
    original = benefits.collect_reference_benefit_rows

    def mutate(*args, **kwargs):
        projection.slices[0].loc[0, "weight"] += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(benefits, "collect_reference_benefit_rows", mutate)
    result = runner.run_joint(inputs, draw_indices=(0,))
    assert result["attempt"]["step"] == 4
    assert result["rows"] == {}


@settings(deadline=None)
@given(
    st.floats(
        min_value=1, max_value=1e10, allow_nan=False, allow_infinity=False
    )
)
def test_hash_detects_scalar_changes_and_is_deterministic(value):
    """Identity hashing is deterministic and detects even adjacent floats."""
    import math

    state = pd.DataFrame({"person_id": [1], "weight": [value]})
    result = ProjectionResult((state,), (), 0)
    before = runner.projection_hash(result)
    assert before == runner.projection_hash(result)
    state.loc[0, "weight"] = math.nextafter(value, math.inf)
    assert before != runner.projection_hash(result)


def test_real_label_requires_preflight_before_projecting():
    """No registered population can enter projection without frozen preflight."""
    inputs = SimpleNamespace(
        cohort=SimpleNamespace(
            anchor_wave=2011, data_provenance="registered_real"
        ),
        additional_cohorts=(),
    )
    with pytest.raises(ValueError, match="validated preflight"):
        runner._before_projection(inputs, runner.JointConfig(), None, None)


@pytest.mark.parametrize("failure", (RuntimeError, KeyboardInterrupt))
def test_infrastructure_interrupt_retains_partial_attempt(
    staged, monkeypatch, failure
):
    """Intended infrastructure interruption preserves counts and all remaining rows."""
    inputs, _, _ = staged
    seen = 0

    def interrupt(*args, **kwargs):
        nonlocal seen
        seen += 1
        if seen == 2:
            raise failure("intended infrastructure interruption")
        return [_row()], Counter({"computed_before_interrupt": 7})

    monkeypatch.setattr(benefits, "collect_reference_benefit_rows", interrupt)
    result = runner.run_joint(inputs, draw_indices=(0,))
    assert result["attempt"]["status"] == "refused"
    assert result["attempt"]["step"] == 3
    assert result["attempt"]["refusal"]["type"] == failure.__name__
    assert result["attempt"]["counters"]["computed_before_interrupt"] == 7
    assert result["benefit_counters"]["L×R0"]["computed_before_interrupt"] == 7
    assert len(result["attempt"]["uncomputed_rows"]) == 68
    assert not result["rows"]
