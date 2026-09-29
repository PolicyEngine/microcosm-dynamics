"""INVENTED DATA - NOT A COMPARISON: joint ordering and conservation."""

from collections import Counter
from dataclasses import fields, replace
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.cola_track_a import benefits as legacy_benefits
from populace_dynamics.cola_track_a.config import REGISTERED_ROWS
from populace_dynamics.engine.loop import ProjectionResult
from populace_dynamics.estimates.parameters import COLASeries
from populace_dynamics.fra68_track.benefits import (
    PersonScenario,
    union_benefit_rows,
)
from populace_dynamics.track_a_v2 import benefits, estimands, histories, runner
from populace_dynamics.track_a_v2.invented import invented_parameters
from populace_dynamics.track_a_v2.matrix import MATRIX
from tests.track_a_v2._invented import build, calculator


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


def _retirees(size=2, *, married=False):
    """Review P2's invented retirees: born 1960, claim 2027, equal careers."""
    return build(
        [
            dict(
                id=pid,
                claim=2027,
                marital="married" if married else "single",
            )
            for pid in range(1, size + 1)
        ],
        careers={pid: {1987: 840000} for pid in range(1, size + 1)},
    )


def _joint_inputs(monkeypatch, *, married=False, population=None):
    """Run the real collectors over an invented one-draw projection."""
    cohort, projection = population or _retirees(married=married)
    draws = projection if isinstance(projection, dict) else {0: projection}
    monkeypatch.setattr(runner, "_before_projection", lambda *args: None)
    monkeypatch.setattr(
        runner, "claiming_schedule", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        runner.legacy,
        "_project_population",
        lambda *args, **kwargs: (draws, {}),
    )
    return SimpleNamespace(
        cohort=cohort,
        params=invented_parameters(),
        baseline=COLASeries(
            {year: 0.025 for year in range(1979, 2032)}, {"invented": True}
        ),
        claiming_pmf={},
    )


def _interrupt_first_level(failure, person_id, calculator_type):
    """Patch the inherited level so person_id's first calculation fails."""
    level = legacy_benefits._Calculator._level
    injected = []

    def interrupt(self, pid, *args):
        if pid == person_id and isinstance(self, calculator_type):
            if not injected:
                injected.append(pid)
                raise failure("intended interruption inside a person")
        return level(self, pid, *args)

    return patch.object(legacy_benefits._Calculator, "_level", interrupt), (
        injected
    )


@pytest.mark.parametrize(
    "failure", (ValueError, RuntimeError, KeyboardInterrupt)
)
def test_interruption_inside_reference_person_keeps_counts_and_identity(
    monkeypatch, failure
):
    """Person 2's interrupted L×R0 level keeps person 1's count and person 2."""
    inputs = _joint_inputs(monkeypatch)
    injection, injected = _interrupt_first_level(
        failure, 2, benefits.TrackACalculator
    )
    with injection:
        result = runner.run_joint(inputs, draw_indices=(0,))
    attempt = result["attempt"]
    assert injected == [2]
    assert attempt["status"] == "refused"
    assert attempt["step"] == 3
    assert attempt["refusal"]["type"] == failure.__name__
    assert attempt["first_failing_person_draw"] == {
        "person_id": 2,
        "draw": 0,
    }
    assert result["failure_counters"] == {"beneficiaries_projected": 1}
    assert attempt["counters"]["beneficiaries_projected"] == 1
    assert attempt["uncomputed_rows"] == [row.key for row in MATRIX]
    assert not result["rows"]


@pytest.mark.parametrize(
    "failure", (ValueError, RuntimeError, KeyboardInterrupt)
)
def test_interruption_inside_scenario_person_keeps_counts_and_identity(
    monkeypatch, failure
):
    """Exercise 3's collector also keeps its partial counts and person 2."""
    inputs = _joint_inputs(monkeypatch, married=True)
    injection, injected = _interrupt_first_level(
        failure, 2, benefits.ScenarioCalculator
    )
    with injection:
        result = runner.run_joint(inputs, draw_indices=(0,))
    attempt = result["attempt"]
    assert injected == [2]
    assert attempt["step"] == 3
    assert attempt["refusal"]["type"] == failure.__name__
    assert attempt["first_failing_person_draw"] == {
        "person_id": 2,
        "draw": 0,
    }
    # Person 1's unlinked-spouse count in the L C0 baseline scenario,
    # after both people completed all six L×R collectors.
    assert result["failure_counters"] == {"spouse_unlinked": 1}
    assert attempt["counters"]["spouse_unlinked"] == 6 * 2 + 1
    assert attempt["counters"]["beneficiaries_projected"] == 6 * 2
    assert attempt["uncomputed_rows"] == [row.key for row in MATRIX]
    assert not result["rows"]


def _collect(exercise, cohort, result):
    calc = calculator(cohort, result, exercise=exercise)
    if exercise == 1:
        return benefits.collect_reference_benefit_rows(
            result, draw=0, row=REGISTERED_ROWS["R0"], context=calc.ctx
        )[1]
    return benefits.scenario_benefits(
        result,
        context=calc.ctx,
        track_row=calc.row,
        scenario=calc.scenario,
        lookups=calc.lookups,
        pia_cache={},
        assumed_birth_month=7,
    )[1]


@settings(max_examples=16, deadline=None)
@given(
    size=st.integers(2, 4),
    data=st.data(),
    failure=st.sampled_from((ValueError, RuntimeError, KeyboardInterrupt)),
    exercise=st.sampled_from((1, 3)),
)
def test_interrupted_collectors_attach_completed_prefix_counts(
    size, data, failure, exercise
):
    """Any interrupted person carries its identity and every prior count."""
    failing = data.draw(st.integers(1, size))
    cohort, result = _retirees(size, married=True)
    kind = (
        benefits.TrackACalculator
        if exercise == 1
        else benefits.ScenarioCalculator
    )
    injection, injected = _interrupt_first_level(failure, failing, kind)
    with injection, pytest.raises(failure) as caught:
        _collect(exercise, cohort, result)
    assert injected == [failing]
    assert caught.value.person_id == failing
    # Differential: a clean run over only the completed prefix.
    prefix = (
        dict(_collect(exercise, *_retirees(failing - 1, married=True)))
        if failing > 1
        else {}
    )
    assert caught.value.counters == prefix
    assert all(type(value) is int for value in caught.value.counters.values())


@pytest.mark.parametrize("failure", (RuntimeError, KeyboardInterrupt))
def test_interrupted_collector_keeps_existing_person_attribution(failure):
    """An inner failure already attributed to another person keeps it."""
    cohort, result = _retirees(married=True)
    level = legacy_benefits._Calculator._level

    def attributed(self, pid, *args):
        if pid == 2:
            error = failure("intended failure attributed to person 1")
            error.person_id = 1
            raise error
        return level(self, pid, *args)

    for exercise in (1, 3):
        with (
            patch.object(legacy_benefits._Calculator, "_level", attributed),
            pytest.raises(failure) as caught,
        ):
            _collect(exercise, cohort, result)
        assert caught.value.person_id == 1
        assert caught.value.counters == dict(
            _collect(exercise, *_retirees(1, married=True))
        )


def _awardees():
    """Two invented single-spell DI awardees, requested at their award."""
    return build([dict(id=1, awards=(2015,)), dict(id=2, awards=(2016,))])


@pytest.mark.parametrize("phase", ("discovery", "validation"))
@pytest.mark.parametrize(
    "failure", (ValueError, RuntimeError, KeyboardInterrupt)
)
def test_interruption_inside_history_person_keeps_counts_and_identity(
    monkeypatch, failure, phase
):
    """Person 2's interrupted draw-1 step 2 keeps draw 0, person 1 and 2."""
    cohort, first = _awardees()
    _, second = _awardees()
    inputs = _joint_inputs(
        monkeypatch, population=(cohort, {0: first, 1: second})
    )
    name = "baseline_di_record" if phase == "discovery" else "validate"
    original = getattr(histories.HistoryValidator, name)
    injected = []

    def interrupt(self, pid, *args):
        if self.result is second and pid == 2 and not injected:
            injected.append(pid)
            raise failure("intended interruption inside a history person")
        return original(self, pid, *args)

    with patch.object(histories.HistoryValidator, name, interrupt):
        result = runner.run_joint(inputs, draw_indices=(0, 1))
    attempt = result["attempt"]
    assert injected == [2]
    assert attempt["status"] == "refused"
    assert attempt["step"] == 2
    assert attempt["refusal"]["type"] == failure.__name__
    assert attempt["first_failing_person_draw"] == {
        "person_id": 2,
        "draw": 1,
    }
    # Discovery precedes every validation; validation keeps person 1's proxy.
    prefix = {} if phase == "discovery" else {"d_proxy_award_year": 1}
    assert result["failure_counters"] == prefix
    assert attempt["counters"] == dict(
        Counter({"d_proxy_award_year": 2}) + Counter(prefix)
    )
    assert attempt["uncomputed_rows"] == [row.key for row in MATRIX]
    assert not result["rows"]


_SCENARIO_READS = frozenset(
    [field.name for field in fields(PersonScenario)] + ["total"]
)


def _tripwire(scenario, failure=None, reads=None):
    """An invented scenario copy whose `reads`-th field read fails.

    Returns the copy and its read log; with no `reads` it only logs.
    """
    seen = []

    class Tripwire(PersonScenario):
        def __getattribute__(self, name):
            if name in _SCENARIO_READS:
                seen.append(name)
                if len(seen) == reads:
                    raise failure("intended interruption in a paired person")
            return super().__getattribute__(name)

    values = {
        field.name: getattr(scenario, field.name) for field in fields(scenario)
    }
    return Tripwire(**values), seen


@pytest.mark.parametrize(
    "failure", (ValueError, RuntimeError, KeyboardInterrupt)
)
def test_interruption_inside_paired_person_keeps_counts_and_identity(
    monkeypatch, failure
):
    """Person 2's interrupted L×F0 pairing keeps person 1's pair count and 2."""
    inputs = _joint_inputs(monkeypatch, married=True)
    original = benefits.scenario_benefits
    logs = []

    def scenario(*args, **kwargs):
        people, counts = original(*args, **kwargs)
        if kwargs["scenario"].name == "baseline" and not logs:
            people[2], seen = _tripwire(people[2], failure, reads=1)
            logs.append(seen)
        return people, counts

    monkeypatch.setattr(benefits, "scenario_benefits", scenario)
    result = runner.run_joint(inputs, draw_indices=(0,))
    attempt = result["attempt"]
    # The first read of person 2's baseline is inside v1's union loop.
    assert logs == [["total"]]
    assert attempt["status"] == "refused"
    assert attempt["step"] == 3
    assert attempt["refusal"]["type"] == failure.__name__
    assert attempt["first_failing_person_draw"] == {
        "person_id": 2,
        "draw": 0,
    }
    assert result["failure_counters"] == {"beneficiaries_projected": 1}
    # Six L×R collectors for both people, then person 1's pair count.
    assert attempt["counters"]["beneficiaries_projected"] == 6 * 2 + 1
    # Six L×R collectors, then the L C0 baseline and the L×F0 reform
    # scenario, each computed for both people before the stop.
    assert attempt["counters"]["spouse_unlinked"] == 6 * 2 + 2 + 2
    assert attempt["uncomputed_rows"] == [row.key for row in MATRIX]
    assert not result["rows"]


def _stopped_counters(monkeypatch, failure, stop):
    """Attempt counters when the first L×F0 reform or its pairing stops."""
    inputs = _joint_inputs(monkeypatch, married=True)
    original = benefits.scenario_benefits
    injection, injected = _interrupt_first_level(
        failure, 2, benefits.ScenarioCalculator
    )
    calls = []

    def scenario(*args, **kwargs):
        calls.append(kwargs["scenario"].name)
        if stop == "reform" and len(calls) == 2:
            with injection:
                return original(*args, **kwargs)
        people, counts = original(*args, **kwargs)
        if stop == "pairing" and len(calls) == 1:
            people[1], _ = _tripwire(people[1], failure, reads=1)
        return people, counts

    monkeypatch.setattr(benefits, "scenario_benefits", scenario)
    result = runner.run_joint(inputs, draw_indices=(0,))
    assert calls[0] == "baseline" and calls[1] != "baseline"
    assert injected == ([2] if stop == "reform" else [])
    assert result["attempt"]["step"] == 3
    return Counter(result["attempt"]["counters"])


@pytest.mark.parametrize("failure", (RuntimeError, KeyboardInterrupt))
def test_later_pairing_stop_keeps_every_earlier_scenario_count(
    monkeypatch, failure
):
    """A later stop never retains fewer counts: reform, then its pairing."""
    earlier = _stopped_counters(monkeypatch, failure, "reform")
    later = _stopped_counters(monkeypatch, failure, "pairing")
    # Person 1 finished the reform scenario before person 2 stopped it.
    assert earlier["spouse_unlinked"] == 6 * 2 + 2 + 1
    # The pairing stop keeps both completed scenarios' counts (§10).
    assert later["spouse_unlinked"] == 6 * 2 + 2 + 2
    assert all(later[key] >= value for key, value in earlier.items())


_KINDS = (None, "retired", "converted", "disabled")


def _paired_inputs(people):
    """Invented base/reform scenario pairs over invented alive retirees."""
    cohort, result = _retirees(len(people))
    calc = calculator(cohort, result, exercise=3)
    base, reform = {}, {}
    for pid, (amounts, kinds) in enumerate(people, 1):
        for side, amount, kind in zip(
            (base, reform), amounts, kinds, strict=True
        ):
            side[pid] = PersonScenario(
                {"retired_worker": amount}, "projected", kind, 2027, 67
            )
    return base, reform, calc


def _pair(base, reform, calc):
    return runner._paired_scenarios(
        base,
        reform,
        draw=0,
        context=calc.ctx,
        lookups=calc.lookups,
        params=calc.ctx.params,
    )


_PEOPLE = st.lists(
    st.tuples(
        st.tuples(*[st.sampled_from((0.0, 40.0, 120.0))] * 2),
        st.tuples(*[st.sampled_from(_KINDS)] * 2),
    ),
    min_size=2,
    max_size=4,
)


@settings(max_examples=60, deadline=None)
@given(
    people=_PEOPLE,
    data=st.data(),
    failure=st.sampled_from((ValueError, RuntimeError, KeyboardInterrupt)),
)
def test_interrupted_pairing_names_the_processed_person(people, data, failure):
    """Any failed read of a person's paired scenarios names that person."""
    base, reform, calc = _paired_inputs(people)
    person = data.draw(st.integers(1, len(people)))
    side = data.draw(st.sampled_from((base, reform)))
    probe, reads = _tripwire(side[person])
    _pair(
        *(({**s, person: probe} if s is side else s) for s in (base, reform)),
        calc,
    )
    # Every read of the person's own scenario, in the union or double-zero branch.
    at = data.draw(st.integers(1, len(reads)))
    wired, _ = _tripwire(side[person], failure, reads=at)
    scenarios = [
        {**s, person: wired} if s is side else s for s in (base, reform)
    ]
    with pytest.raises(failure) as caught:
        _pair(*scenarios, calc)
    assert caught.value.person_id == person
    # Differential: one inherited union call over only the completed prefix.
    prefix = [pid for pid in base if pid < person]
    assert caught.value.counters == dict(
        union_benefit_rows(
            {pid: base[pid] for pid in prefix},
            {pid: reform[pid] for pid in prefix},
            draw=0,
            context=calc.ctx,
            lookups=calc.lookups,
            baseline_params=calc.ctx.params,
            reform_params=calc.ctx.params,
        )[1]
    )
    assert all(type(value) is int for value in caught.value.counters.values())


def _single_union_pairing(base, reform, calc):
    """Pre-attribution reference: one v1 union call, then double zeros."""
    lookups, context = calc.lookups, calc.ctx
    rows, counters = union_benefit_rows(
        base,
        reform,
        draw=0,
        context=context,
        lookups=lookups,
        baseline_params=context.params,
        reform_params=context.params,
    )
    present = {item["person_id"] for item in rows}
    for pid in sorted(set(base) - present):
        state = lookups.final.loc[pid]
        names = sorted(set(base[pid].components) | set(reform[pid].components))
        rows.append(
            {
                "draw": 0,
                "person_id": pid,
                "family_unit_id": int(
                    context.cohort.persons_by_id.loc[pid, "family_unit_id"]
                ),
                "weight": float(state["weight"]),
                "birth_year": int(state["birth_year"]),
                "beneficiary_base": False,
                "beneficiary_reform": False,
                "benefit_base": 0.0,
                "benefit_reform": 0.0,
                "benefit_components": {
                    name: {"base": 0.0, "reform": 0.0} for name in names
                },
                "basis": base[pid].basis,
                "own_kind_base": base[pid].own_kind,
                "own_kind_reform": reform[pid].own_kind,
            }
        )
    for item in rows:
        item["age_reference"] = 2030 - item["birth_year"]
    return sorted(rows, key=lambda item: item["person_id"]), counters


@settings(max_examples=100, deadline=None)
@given(people=_PEOPLE)
def test_per_person_pairing_replays_one_inherited_union_call(people):
    """Rows, row and key order, and counter order equal one v1 union call."""
    base, reform, calc = _paired_inputs(people)
    rows, counters = _pair(base, reform, calc)
    expected_rows, expected_counters = _single_union_pairing(
        base, reform, calc
    )
    assert rows == expected_rows
    assert [list(item) for item in rows] == [
        list(item) for item in expected_rows
    ]
    assert list(counters.items()) == list(expected_counters.items())
    assert type(counters) is Counter
