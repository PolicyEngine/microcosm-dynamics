"""Invented structural histories prove that count collection has no amounts."""

from __future__ import annotations

import copy
from types import SimpleNamespace

import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.engine.loop import ProjectionResult
from populace_dynamics.ss.params import SSAParameters
from populace_dynamics.track_a_v2.structural import (
    StructuralRefusal,
    count_projection,
    validate_count_outputs,
)


def fixture(*, recovery=False, weight=1):
    """Two invented linked people, no indexing/benefit parameter coverage."""
    slices = []
    for year in range(2010, 2031):
        award = 2023 if recovery and year >= 2023 else 2015
        entitled = 2015 <= year < 2027
        if recovery and 2018 <= year < 2023:
            entitled = False
        event = "opening" if year == 2010 else "none"
        if year == 2015 or recovery and year == 2023:
            event = "award"
        elif recovery and year == 2018:
            event = "recovery"
        elif year == 2027:
            event = "conversion"
        elif entitled:
            event = "continuing"
        common = {
            "year": year,
            "weight": weight,
            "marital_status": "married",
            "claimed": True,
            "late_spouse_person_id": None,
            "widowhood_year": None,
        }
        slices.append(
            pd.DataFrame(
                [
                    {
                        **common,
                        "person_id": 1,
                        "birth_year": 1960,
                        "spouse_person_id": 2,
                        "claim_year": 2010,
                        "di_entitled": entitled,
                        "di_award_year": award if year >= 2015 else None,
                        "di_recovery_year": (
                            2018 if recovery and year >= 2018 else None
                        ),
                        "di_conversion_year": 2027 if year >= 2027 else None,
                        "di_event": event,
                    },
                    {
                        **common,
                        "person_id": 2,
                        "birth_year": 1950,
                        "spouse_person_id": 1,
                        "claim_year": 2015,
                        "di_entitled": False,
                        "di_award_year": None,
                        "di_recovery_year": None,
                        "di_conversion_year": None,
                        "di_event": "opening" if year == 2010 else "none",
                    },
                ]
            )
        )
    persons = pd.DataFrame(
        [
            {
                "person_id": 1,
                "birth_year": 1960,
                "opening_status": "none",
                "ss_receipt_opening": True,
            },
            {
                "person_id": 2,
                "birth_year": 1950,
                "opening_status": "none",
                "ss_receipt_opening": False,
            },
        ]
    ).set_index("person_id", drop=False)
    cohort = SimpleNamespace(
        persons_by_id=persons,
        opening={},
        start_year=2010,
        roster_ids=frozenset({1, 2}),
        careers={1: {1987: object()}, 2: {1987: object()}},
    )
    params = SSAParameters(
        nawi={},
        wage_base={},
        pia_factors=(1, 1, 1),
        fra_months_by_birth_year=[(1900, 792), (1960, 804)],
        early_monthly_rates=(0, 0),
        early_first_bracket_months=36,
        pe_us_revision="INVENTED DATA - NOT A COMPARISON",
    )
    return ProjectionResult(tuple(slices), (), 0), cohort, params


def test_structural_counts_use_histories_and_dates_without_levels():
    """No earnings amount, index, PIA or weight arithmetic is needed."""
    result, cohort, params = fixture(weight=object())
    counts = count_projection(result, cohort, params)
    validate_count_outputs(counts)
    assert counts["d_unsupported_histories"] == 0
    assert counts["s_refused_earlier_spells"] == 0
    assert counts["opening_proxy_applications"] == 1
    assert (
        counts["s_ordering_classes"]["R0/baseline"]["prior_rib_di_spouse"] == 1
    )


def test_structural_counts_detect_overwritten_awards_and_earlier_spells():
    """A re-award cannot erase the unsupported earlier spell in event counts."""
    counts = count_projection(*fixture(recovery=True))
    assert counts["d_unsupported_histories"] == 1
    assert counts["s_refused_earlier_spells"] == 1
    assert all(
        sum(row.values()) == 0 for row in counts["s_ordering_classes"].values()
    )


def test_opening_applications_and_earlier_spells_count_before_link_gate():
    """S reaches H/earlier-spell checks even when no linked amount is payable."""
    result, cohort, params = fixture()
    for frame in result.slices:
        frame.loc[frame.person_id == 1, "spouse_person_id"] = None
    counts = count_projection(result, cohort, params)
    assert counts["opening_proxy_applications"] == 1
    assert sum(counts["s_ordering_classes"]["R0/baseline"].values()) == 0
    result, cohort, params = fixture(recovery=True)
    for frame in result.slices:
        frame.loc[frame.person_id == 1, "spouse_person_id"] = None
    assert (
        count_projection(result, cohort, params)["s_refused_earlier_spells"]
        == 1
    )


def test_structural_refusal_preserves_prior_counts():
    """A filing-integrity refusal carries already computed permitted counts."""
    result, cohort, params = fixture()
    cohort.careers[1][1950] = object()  # Intended D-unsupported history.
    result.slices[-1].loc[
        result.slices[-1].person_id == 1, "claim_year"
    ] = 2028
    with pytest.raises(StructuralRefusal) as caught:
        count_projection(result, cohort, params)
    assert caught.value.counts["d_unsupported_histories"] == 1
    assert caught.value.person_id == 1
    validate_count_outputs(caught.value.counts)


@given(st.integers(min_value=-(10**9), max_value=10**9))
@settings(deadline=None, max_examples=30)
def test_structural_counts_are_independent_of_weights(weight):
    """Permitted structural counts are unweighted, deterministic integers."""
    assert count_projection(*fixture(weight=weight)) == count_projection(
        *fixture()
    )


@pytest.mark.parametrize(
    "extra", ["benefits", "weight_sum", "tabulations", "mean", "anything_else"]
)
def test_structural_outputs_refuse_every_extra_category(extra):
    """Intended violation: no amount, weight sum or extra output can escape."""
    counts = count_projection(*fixture())
    counts[extra] = 0
    with pytest.raises(ValueError, match="only the four frozen"):
        validate_count_outputs(counts)


@pytest.mark.parametrize("mutation", ["amount", "row", "float", "negative"])
def test_structural_outputs_refuse_hidden_outcome_fields(mutation):
    """Even allowed containers accept only fixed nonnegative integer bins."""
    counts = copy.deepcopy(count_projection(*fixture()))
    if mutation == "amount":
        counts["s_ordering_classes"]["R0/baseline"]["benefit"] = 100
    elif mutation == "row":
        counts["s_ordering_classes"]["unregistered/baseline"] = {}
    elif mutation == "float":
        counts["opening_proxy_applications"] = 1.0
    else:
        counts["d_unsupported_histories"] = -1
    with pytest.raises(ValueError):
        validate_count_outputs(counts)


def test_no_level_or_weight_aggregate_is_invoked(monkeypatch):
    """Poisoning all legacy amount and summary calls leaves counts usable."""
    from populace_dynamics.cola_track_a import benefits, runner
    from populace_dynamics.ss import statutory_aime

    def forbidden(*args, **kwargs):
        raise AssertionError("forbidden computation in structural protocol")

    monkeypatch.setattr(benefits, "approximate_pia", forbidden)
    monkeypatch.setattr(benefits._Calculator, "_level", forbidden)
    monkeypatch.setattr(statutory_aime, "aime", forbidden)
    monkeypatch.setattr(runner, "_draw_diagnostics", forbidden)
    assert count_projection(*fixture())["opening_proxy_applications"] == 1


def test_structural_entry_preserves_partial_attempt_and_avoids_diagnostics(
    monkeypatch,
):
    """A failed draw preserves prior counters without any weighted diagnostic."""
    from populace_dynamics.cola_track_a import runner
    from populace_dynamics.track_a_v2 import structural
    from populace_dynamics.track_a_v2.manifest import SPECIFICATION_SHA256
    from populace_dynamics.track_a_v2.protocol import PreflightRecord

    result, cohort, params = fixture()
    cohort.data_provenance = "invented"
    cohort.initial_slice = result.slices[0]
    cohort.careers[1][1950] = object()
    result.slices[-1].loc[
        result.slices[-1].person_id == 1, "claim_year"
    ] = 2028
    inputs = SimpleNamespace(
        cohort=cohort,
        params=params,
        claiming_pmf={},
        population_mortality=None,
        di_rates=None,
    )
    monkeypatch.setattr(structural, "claiming_schedule", lambda *a, **kw: None)
    monkeypatch.setattr(structural, "build_period_modules", lambda **kw: None)
    monkeypatch.setattr(
        structural.ProjectionEngine, "project", lambda *a, **kw: result
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("weighted diagnostics forbidden")

    monkeypatch.setattr(runner, "_project_population", forbidden)
    monkeypatch.setattr(runner, "_draw_diagnostics", forbidden)
    registration = PreflightRecord(
        "1" * 40, SPECIFICATION_SHA256, "invented", "0" * 64, "structural"
    )
    artifact = structural.run_structural(
        inputs, registration=registration, draw_indices=(0,)
    )
    assert artifact["header"] == "INVENTED DATA - NOT A COMPARISON"
    assert artifact["attempt"]["status"] == "refused"
    assert artifact["attempt"]["uncomputed_draws"] == [0]
    assert artifact["counts"]["d_unsupported_histories"] == 1
