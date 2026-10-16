"""Invented-input invariants for the two projection diagnostics."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import pandas as pd
import pytest
from hypothesis import HealthCheck, example, given, settings
from hypothesis import strategies as st

from scripts import d1408_projection as diagnostic
from scripts.d1408_projection import headline_changes, model_headlines


@settings(deadline=None)
@given(
    st.one_of(
        st.floats(min_value=-100, max_value=100, allow_nan=False),
        st.sampled_from((None, float("nan"), float("inf"), float("-inf"))),
    )
)
def test_identical_headlines_have_zero_change(value):
    import math

    if value is None or not math.isfinite(value):
        assert headline_changes({"mean": value}, {"mean": value}) == {
            "mean": {
                "change": None,
                "defined_under_legacy": False,
                "defined_under_statutory": False,
            }
        }
    else:
        assert headline_changes({"mean": value}, {"mean": value}) == {
            "all_model_headline_changes": 0.0
        }


@settings(deadline=None)
@given(st.integers(-1000, 1000), st.integers(-1000, 1000))
def test_numeric_headline_change_is_right_minus_left(left, right):
    if left != right:
        assert headline_changes(left, right) == right - left


@settings(deadline=None)
@given(st.integers(-1000, 1000), st.integers(1, 100))
def test_nested_headlines_preserve_labels_and_omit_unchanged(left, delta):
    first = {"old": {"mean": left}, "unchanged": 1}
    second = {"old": {"mean": left + delta}, "unchanged": 1}
    assert headline_changes(first, second) == {"old": {"mean": delta}}


@given(st.floats(min_value=-100, max_value=100, allow_nan=False))
@settings(deadline=None)
def test_headline_selector_excludes_record_and_benchmark_fields(value):
    group = {
        "label": "all",
        "cells": [{"person_id": "invented"}],
        "external_anchor": "must not publish",
        "ratio_of_scenario_means": {"mean": value, "sample_sd": 2},
        "mean_of_individual_ratios": {"mean": value, "sample_sd": 4},
    }
    selected = model_headlines({"groups": [group]})
    assert selected == {
        "all": {
            "ratio_of_scenario_means": {"mean": value, "sample_sd": 2},
            "mean_of_individual_ratios": {"mean": value, "sample_sd": 4},
        }
    }


@given(st.dictionaries(st.text(min_size=1, max_size=8), st.integers()))
@settings(
    deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
def test_checkpoint_round_trip_and_read_audit(monkeypatch, values):
    scratch = diagnostic.ROOT / "scratch" / "d1408"
    scratch.mkdir(parents=True, exist_ok=True)
    with (
        TemporaryDirectory(
            prefix="projection-method-test-", dir=scratch
        ) as temporary,
        monkeypatch.context() as context,
    ):
        _checkpoint_round_trip_and_read_audit(context, Path(temporary), values)


def _checkpoint_round_trip_and_read_audit(monkeypatch, tmp_path, values):
    monkeypatch.setattr(diagnostic, "SCRATCH", tmp_path)
    path = diagnostic.checkpoint_path("invented", "commit", "cohort", 2011)
    before = {"invented-read-one", "invented-read-two"}
    diagnostic.checkpoint_write(
        path, values, commit="commit", kind="invented", reads=before
    )
    after = set()
    assert (
        diagnostic.checkpoint_load(
            path, commit="commit", kind="invented", reads=after
        )
        == values
    )
    assert after == before
    with pytest.raises(ValueError, match="code identity"):
        diagnostic.checkpoint_load(
            path, commit="different", kind="invented", reads=set()
        )
    with pytest.raises(ValueError, match="code identity"):
        diagnostic.checkpoint_load(
            path, commit="commit", kind="different", reads=set()
        )
    assert (
        diagnostic.artifact_commit(
            {"run": {"registered_commit": "commit", "git_head": "commit"}}
        )
        == "commit"
    )
    with pytest.raises(ValueError, match="registered_commit"):
        diagnostic.artifact_commit(
            {"run": {"registered_commit": "commit", "git_head": "different"}}
        )
    path.unlink()
    monkeypatch.setattr(diagnostic, "install_read_guard", lambda: set())
    membership_paths = []
    ledger = {
        "events": {},
        "row_events": {},
        "changed_people_by_row": {},
        "row_waves": {},
        "admitted_people_by_row": {},
    }
    for kind in diagnostic.ARTIFACTS:
        aggregate = {"code_commit": "commit", "invented_values": values}
        (tmp_path / f"{kind}-aggregate.json").write_text(json.dumps(aggregate))
        membership = tmp_path / f"{kind}-publication-memberships.pickle"
        diagnostic.checkpoint_write(
            membership, ledger, commit="commit", kind=kind, reads=before
        )
        for suffix in (".retain", ".replay"):
            membership.with_suffix(suffix).write_bytes(b"invented backup")
        membership_paths.append(membership)
    published = {}

    def capture_publication(output, aggregate):
        for membership in membership_paths:
            assert not membership.exists()
            assert not membership.with_suffix(".retain").exists()
            assert not membership.with_suffix(".replay").exists()
        audit = aggregate["cross_result_publication_audit"]
        assert audit["completed"] is True
        assert audit["temporary_memberships_deleted"] is True
        assert isinstance(audit["method"], str)
        assert aggregate["invented_values"] == values
        published[output.name] = aggregate

    monkeypatch.setattr(diagnostic, "write_aggregate", capture_publication)
    diagnostic.finalize_publication()
    assert set(published) == {
        f"{kind}-aggregate.json" for kind in diagnostic.ARTIFACTS
    }
    with pytest.raises(ValueError, match="membership ledgers required"):
        diagnostic.finalize_publication()


@given(
    value=st.floats(min_value=-100, max_value=100, allow_nan=False),
    large=st.integers(10, 100),
    small=st.integers(1, 9),
    other_wave=st.sampled_from((2009, 2011)),
)
@settings(deadline=None)
def test_model_selector_includes_committed_floor_summary(
    value, large, small, other_wave
):
    floor = {
        "mean": value,
        "sd": 0.0,
        "min": value,
        "max": value,
        "n_seeds": 5,
        "values": [value] * 5,
    }
    stats = {"mean": 1.0, "sample_sd": 0.1, "floor": floor}
    selected = model_headlines(
        {
            "groups": [
                {
                    "label": "all",
                    "ratio_of_scenario_means": stats,
                    "mean_of_individual_ratios": stats,
                }
            ]
        }
    )
    assert selected["all"]["ratio_of_scenario_means"]["floor"] == {
        key: floor[key] for key in ("mean", "sd", "min", "max", "n_seeds")
    }
    groups = {
        "small": {"changed_recipients": "<10", "model_headlines": "<10"},
        "large": {"changed_recipients": large, "model_headlines": value},
        "second_large": {
            "changed_recipients": large,
            "model_headlines": value,
        },
        "empty": {"changed_recipients": 0, "model_headlines": 0.0},
    }
    # The admitted total 2 * large + small can stay public, while its age
    # partition cannot reveal the positive cell below ten by subtraction.
    total = 2 * large + small
    diagnostic.protect_age_partition(groups)
    assert total >= 21
    assert set(groups["large"].values()) == {"suppressed_complementary"}
    assert set(groups["second_large"].values()) == {"suppressed_complementary"}
    assert set(groups["small"].values()) == {"<10"}
    assert groups["empty"] == {"changed_recipients": 0, "model_headlines": 0.0}
    changes = {
        name: {"changed_recipients": count, "groups": {}}
        for name, count in (("first", large), ("second", large + small))
    }
    diagnostic.protect_row_overlaps(
        changes,
        {"first": set(range(large)), "second": set(range(large + small))},
        {"first": 2011, "second": other_wave},
    )
    assert all(
        cell["changed_recipients"] == "suppressed_complementary"
        for cell in changes.values()
    )


@given(birth=st.integers(1917, 1942), late=st.integers(49, 72))
@settings(deadline=None)
def test_opening_stock_factor_keeps_original_worker_and_role(birth, late):
    trace = diagnostic.Trace()
    trace.wave = 2011
    trace.cohort = SimpleNamespace(
        persons_by_id=pd.DataFrame({"weight": [1.0]}, index=[1])
    )

    def opening_stock_factor_ratio():
        trace.callback(late, birth, None)

    def opening_scenario(record):
        opening_stock_factor_ratio()

    opening_scenario(SimpleNamespace(person_id=1))
    assert trace.events[("supported", "factor_evaluation")] == {
        (2011, 1, "old_age")
    }
    assert trace.events[("supported", "opening_stock_adjustment")] == {
        (2011, 1, "old_age")
    }
    assert not trace.events[("supported", "available_pia")]


@given(
    amount=st.integers(0, 1000),
    undone=st.booleans(),
    workers=st.integers(10, 20),
    linked=st.integers(1, 9),
)
@example(amount=0, undone=False, workers=10, linked=1)
@settings(
    deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
def test_payment_observer_preserves_returns_and_tracks_positive_used_credit(
    monkeypatch, amount, undone, workers, linked
):
    from populace_dynamics.cola_track_a.benefits import _Calculator
    from tests.track_b_gross_benefit_support import ssa_params

    trace = diagnostic.Trace()
    trace.wave = 2011
    calculator = SimpleNamespace(
        payment_year=2030,
        statics=pd.DataFrame({"birth_year": [1937]}, index=[2]),
        ctx=SimpleNamespace(params=ssa_params()),
    )
    record = SimpleNamespace(
        person_id=2,
        kind="retired",
        entitlement_year=2007,
        claim_age_factor=1.0 if undone else 1.26,
    )
    trace.latest_records[(id(calculator), 2)] = record
    paths = ({2030: amount}, {2030: amount})
    widow = None if amount == 0 else ((amount, amount), 0)
    spouse = None if amount == 0 else (amount, amount)

    def original_paths(*args, **kwargs):
        return paths

    def original_widow(*args, **kwargs):
        return widow

    def original_spouse(*args, **kwargs):
        return spouse

    monkeypatch.setattr(_Calculator, "_worker_paths", original_paths)
    monkeypatch.setattr(_Calculator, "_widow_excess", original_widow)
    monkeypatch.setattr(_Calculator, "_spouse_excess", original_spouse)
    state = {"late_spouse_person_id": 2, "spouse_person_id": 2}
    with trace.payment_flows("cola"):
        assert _Calculator._worker_paths(calculator, record, None) is paths
        assert _Calculator._widow_excess(calculator, 1, state) is widow
        assert _Calculator._spouse_excess(calculator, 1, state) is spouse
    assert _Calculator._worker_paths is original_paths
    assert _Calculator._widow_excess is original_widow
    assert _Calculator._spouse_excess is original_spouse
    expected = {(2011, 2, "old_age")} if amount > 0 and not undone else set()
    for role in (
        "positive_worker_payment",
        "positive_survivor_payment",
        "positive_spouse_basis_factor_unused",
    ):
        assert trace.events[("supported", role)] == expected
    data = [
        {
            "draw": draw,
            "person_id": person,
            "weight": 1.0,
            "beneficiary_base": person < 10,
            "benefit_base": amount if person < 10 else 1000.0,
        }
        for draw in (0, 1)
        for person in range(20)
    ]
    counted = diagnostic.row_admitted_counts("invented", data, trace, (0, 1))
    assert counted["admitted_people"] == (10 if amount > 0 else 0)
    assert counted["admitted_weight"] == (10.0 if amount > 0 else 0.0)
    assert counted["mean_draw_admitted_weight"] == (
        10.0 if amount > 0 else 0.0
    )
    with trace.row("base"):
        trace.emit("supported", "factor_evaluation", (2011, 2, "old_age"))
    trace.wave = 2009
    trace.copy_row("base", "F8")
    assert not trace.row_events[("F8", "supported", "factor_evaluation")]
    assert trace.row_id is None
    privacy = diagnostic.Trace()
    privacy.wave = 2011
    privacy.cohort = SimpleNamespace(
        persons_by_id=pd.DataFrame({"weight": [1.0] * 50}, index=range(50))
    )
    with privacy.row("invented"):
        for person in range(workers):
            record = (2011, person, "old_age")
            privacy.emit("supported", "factor_evaluation", record)
            privacy.emit("supported", "positive_worker_payment", record)
            privacy.emit(
                "supported",
                "positive_worker_payment_recipient",
                (2011, person, person),
            )
        for person in range(workers + linked):
            privacy.emit(
                "supported",
                "recipient",
                (2011, person, min(person, workers - 1)),
            )
    data = [
        {
            "draw": 0,
            "person_id": person,
            "weight": 1.0,
            "beneficiary_base": True,
            "benefit_base": 1.0,
        }
        for person in range(50)
    ]
    row_count = diagnostic.row_admitted_counts("invented", data, privacy, (0,))
    assert (
        row_count["supported/factor_evaluation"]["people"] == workers + linked
    )
    assert set(row_count["supported/positive_worker_payment"].values()) == {
        "suppressed_complementary"
    }
    summary = privacy.summary({2011: privacy.cohort})["2011"]
    assert summary["supported/recipient"]["people"] == workers + linked
    for role in (
        "positive_worker_payment",
        "positive_worker_payment_recipient",
    ):
        assert set(summary[f"supported/{role}"].values()) == {
            "suppressed_complementary"
        }
    from populace_dynamics.estimates.cola_age_profile import (
        WORKERS_ONLY_COMPONENTS,
        ColaAgeProfileConfig,
        _normalize,
    )

    # R5/F6 retain full returned payments but admit only selected workers.
    # An auxiliary-only payment is outside their original baseline frame.
    selected_rows = [
        {
            "draw": 0,
            "person_id": 1,
            "family_unit_id": 1,
            "weight": 1.0,
            "birth_year": 1937,
            "beneficiary_base": True,
            "beneficiary_reform": True,
            "benefit_base": float(amount + 1),
            "benefit_reform": float(amount + 1),
            "benefit_components": {
                "retired_worker": {"base": amount, "reform": amount},
                "aged_widow": {"base": 1.0, "reform": 1.0},
            },
        }
    ]
    alternative_rows = [
        {
            **selected_rows[0],
            "benefit_base": float(amount + 2),
            "benefit_reform": float(amount + 2),
            "benefit_components": {
                "retired_worker": {"base": amount, "reform": amount},
                "aged_widow": {"base": 2.0, "reform": 2.0},
            },
        }
    ]
    selected_config = ColaAgeProfileConfig(
        draw_indices=(0,),
        floor_seeds=(0,),
        components=WORKERS_ONLY_COMPONENTS,
    )
    selected = _normalize(selected_rows, selected_config)
    selected_alternative = _normalize(alternative_rows, selected_config)
    selected_count = diagnostic.row_admitted_counts(
        "invented",
        selected_rows,
        diagnostic.Trace(),
        (0,),
        baseline_mask=selected.recipient_base,
    )
    assert selected_count["admitted_people"] == ("<10" if amount else 0)
    assert (
        diagnostic.selected_changed_people(selected, selected_alternative)
        == set()
    )
    all_config = ColaAgeProfileConfig(draw_indices=(0,), floor_seeds=(0,))
    assert diagnostic.selected_changed_people(
        _normalize(selected_rows, all_config),
        _normalize(alternative_rows, all_config),
    ) == {1}
    assert diagnostic.selected_changed_people(selected, selected) == set()
    # Attribution ignores input row ordering and keeps original masks.
    extra = {**selected_rows[0], "person_id": 2, "family_unit_id": 2}
    assert diagnostic.selected_changed_people(
        _normalize([selected_rows[0], extra], all_config),
        _normalize([extra, alternative_rows[0]], all_config),
    ) == {1}
