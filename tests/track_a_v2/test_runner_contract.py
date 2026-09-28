"""INVENTED DATA - NOT A COMPARISON: independent §§7, 10 runner audit."""

from collections import Counter
from dataclasses import replace

from populace_dynamics.track_a_v2 import benefits, estimands, runner
from tests.track_a_v2.test_runner import _row
from tests.track_a_v2.test_runner import staged as staged


def test_f_legacy_input_boundary_and_u_all_alive_denominator(
    staged, monkeypatch
):
    """F keeps v1's union input for floors; U preserves all-alive double zeros."""
    inputs, _, _ = staged
    paired = runner._paired_scenarios
    tabulate = estimands.tabulate_rows
    seen = {}

    def with_double_zero(*args, **kwargs):
        rows, counters = paired(*args, **kwargs)
        zero = _row(0, 0)
        zero.update(person_id=2, family_unit_id=2)
        rows.append(zero)
        return rows, counters

    def capture(rows, row, **kwargs):
        seen[row.key] = [person["person_id"] for person in rows]
        return tabulate(rows, row, **kwargs)

    monkeypatch.setattr(runner, "_paired_scenarios", with_double_zero)
    monkeypatch.setattr(estimands, "tabulate_rows", capture)
    result = runner.run_joint(inputs, draw_indices=(0,))
    assert result["attempt"]["status"] == "completed", result["attempt"]
    for mechanism in ("L", "D", "S", "DS"):
        assert seen[f"{mechanism}×F0"] == [1]
        assert seen[f"{mechanism}×U0"] == [1, 2]


def test_stage3_refusal_keeps_all_completed_row_counters(staged, monkeypatch):
    """A step-3 refusal retains preceding and failing-row counters, no rows."""
    inputs, _, _ = staged
    original = benefits.collect_reference_benefit_rows

    def collect(*args, **kwargs):
        if kwargs["row"].row_id == "R1":
            return [_row(0, 120)], Counter(failing_row_marker=2)
        rows, counts = original(*args, **kwargs)
        counts["completed_row_marker"] = 1
        return rows, counts

    monkeypatch.setattr(benefits, "collect_reference_benefit_rows", collect)
    result = runner.run_joint(inputs, draw_indices=(0,))
    assert result["attempt"]["status"] == "refused"
    assert result["attempt"]["step"] == 3
    assert result["benefit_counters"]["L×R0"]["completed_row_marker"] == 1
    assert result["benefit_counters"]["L×R1"]["failing_row_marker"] == 2
    assert not result["rows"]
    assert len(result["attempt"]["uncomputed_rows"]) == 68


def test_stage5_refusal_keeps_prior_membership_and_pair_counters(
    staged, monkeypatch
):
    """A step-5 refusal retains earlier classifications and all pair counters."""
    inputs, _, _ = staged
    original = benefits.scenario_benefits
    paired = runner._paired_scenarios

    def scenario(*args, **kwargs):
        people, counts = original(*args, **kwargs)
        if (
            kwargs["mechanism"] == "DS"
            and kwargs["scenario"].name == "baseline"
        ):
            people[1] = replace(people[1], components={"retired_worker": 0})
        return people, counts

    def count_pair(*args, **kwargs):
        rows, counts = paired(*args, **kwargs)
        counts["pair_marker"] += 1
        return rows, counts

    monkeypatch.setattr(benefits, "scenario_benefits", scenario)
    monkeypatch.setattr(runner, "_paired_scenarios", count_pair)
    result = runner.run_joint(inputs, draw_indices=(0,))
    assert result["attempt"]["status"] == "refused"
    assert result["attempt"]["step"] == 5
    assert result["membership"]["L×F0"]["n_rows_differ"] == 0
    assert result["benefit_counters"]["L×F0"]["pair_marker"] == 1
    assert not result["rows"]
    assert len(result["attempt"]["uncomputed_rows"]) == 68
