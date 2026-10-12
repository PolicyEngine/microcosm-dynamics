"""R3 statutory conformance: captured rules and invented earnings, no data.

All reference earnings are invented. POMS RS 00605.501's PIA-only examples
are reproduced at the decision boundary because SSA supplies no earnings
history. Each invented worked case spells out its intermediate figures.
Original insured status and entitlement are supplied and assumed; these
arithmetic cases do not verify quarters of coverage or insured status.
"""

import html
import json
import math
import re
from dataclasses import replace
from fractions import Fraction as F
from hashlib import sha256
from unittest.mock import patch

import pytest

from populace_dynamics.ss.statutory_aime import aime_with_computation_years
from populace_dynamics.track_b import recompute as r
from populace_dynamics.track_b.gross_benefits import (
    FamilyConfigurationUnsupported,
    FamilyTargetBlocked,
    InvalidFamilyInput,
    YearMonth,
    ceil_dime,
    count_family_outcomes,
    increase_by_colas,
    whole_dollars,
)
from tests.track_b_gross_benefit_support import TRACK_B_DATA, ssa_params

PARAMS = ssa_params(wage_base={1951: 1_000_000})


def basis(**overrides):
    values = dict(
        eligibility_year=2020,
        indexing_year=2018,
        computation_years=35,
        bend_points=r.eligibility_bend_points(2020, PARAMS),
        first_base_year=1951,
        entitlement_month=YearMonth(2020, 6),
    )
    values.update(overrides)
    return r.RecomputationBasis(**values)


def explicit_early_zeros(values):
    """Invented history explicitly sets every 1951-2017 year to zero."""
    return {year: 0 for year in range(1951, 2018)} | values


def annual(**overrides):
    values = dict(
        basis=basis(),
        history={2018: 21000, 2019: 42000, 2020: 63000},
        earnings_year=2020,
        eligibility_pia_of_record=135,
        params=PARAMS,
        december_cola_percent={2020: 0},
    )
    values.update(overrides)
    values["history"] = explicit_early_zeros(values["history"])
    return r.annual_recomputation(**values)


def death_annual(month=11, cola=0):
    """Invented DOB1958-06-02: ELY2020, FRA2025-02, death2026."""
    history = {year: 0 for year in range(1951, 2027)}
    history.update({2018: 21000, 2019: 42000, 2026: 63000})
    return annual(
        history=history,
        earnings_year=2026,
        death_month=YearMonth(2026, month),
        fra_month=YearMonth(2025, 2),
        december_cola_percent={year: 0 for year in range(2020, 2026)}
        | {2026: cola},
    )


def test_invented_ordinary_recomputation_preserves_original_basis():
    """35 years: 21000+42000 /420=150; PIA135.0; 33 explicit zeros.

    New63000 replaceszero; revised126000/420=300; original2020 bend
    points960/5785; .9*300=270.
    10% December2020 COLA: old148.5, candidate297.0, increase148.5.
    Effective January2021; whole-dollar reference PIAs148 and297.
    """
    result = annual(december_cola_percent={2020: 10})
    assert basis().bend_points == (960, 5785)
    assert result.aime == 300
    assert result.candidate_eligibility_pia == F(270)
    assert result.decision.pia_of_record == F("148.5")
    assert result.decision.candidate_pia == F(297)
    assert result.decision.increase == F("148.5")
    assert result.decision.applied
    assert result.effective_month == YearMonth(2021, 1)
    assert whole_dollars(result.decision.pia_of_record) == 148
    assert whole_dollars(result.decision.pia_in_force) == 297
    # RS00605.401's published date example: earnings1999 -> January2000.
    # Invented amount42000/420=AIME100 ->PIA90 with an explicit zeroCOLA.
    history_1999 = {year: 0 for year in range(1951, 2000)}
    history_1999[1999] = 42000
    original_1999 = basis(
        eligibility_year=1999,
        indexing_year=1997,
        bend_points=r.eligibility_bend_points(1999, PARAMS),
        entitlement_month=YearMonth(1999, 6),
    )
    published_date = r.annual_recomputation(
        original_1999, history_1999, 1999, 0, PARAMS, {1999: 0}
    )
    assert published_date.effective_month == YearMonth(2000, 1)
    assert published_date.decision.pia_in_force == 90


@pytest.mark.parametrize("increase", [F(d, 10) for d in range(1, 10)])
def test_sub_dollar_increase_is_not_effective(increase):
    decision = r.recomputation_decision(100, 100 + increase)
    assert not decision.applied
    assert decision.pia_in_force == 100


def test_poms_rs00605501_actual_pia_not_whole_dollar_threshold():
    """SSA: $849.40->$850.00 is $.60; $850.40 is the $1 boundary."""
    low = r.recomputation_decision("849.40", "850.00")
    sufficient = r.recomputation_decision("849.40", "850.40")
    assert low.increase == F("0.60") and not low.applied
    assert (
        whole_dollars(low.candidate_pia) - whole_dollars(low.pia_of_record)
        == 1
    )
    assert sufficient.increase == 1 and sufficient.applied


def test_poms_rs00605501_sub_dollar_then_later_earnings():
    """SSA PIA-only example: 445.50 +.90 refused January1998.

    December1998 old451.20; January1999 candidate452.20; $1 accepted,
    including when that year's positive earnings do not enter the top set.
    Without1998 earnings the same candidate cannot trigger recomputation.
    """
    first = r.recomputation_decision("445.50", F("445.50") + F(".90"))
    second = r.recomputation_decision("451.20", "452.20")
    no_earnings = r.recomputation_decision(
        "451.20", "452.20", has_earnings=False
    )
    assert first.candidate_pia == F("446.40")
    assert not first.applied and first.pia_in_force == F("445.50")
    historical_colas = json.loads(
        (TRACK_B_DATA / "ret_history.json").read_text()
    )
    cola_1998 = F(historical_colas["december_cola_percent"]["1998"])
    assert cola_1998 == F("1.3")
    ret_sources = TRACK_B_DATA / "ret_sources"
    ret_manifest = json.loads((ret_sources / "manifest.json").read_text())
    pin = next(
        p for p in ret_manifest["sources"] if p["id"] == "ssa_cola_history"
    )
    capture = (ret_sources / pin["file"]).read_bytes()
    assert len(capture) == pin["bytes"]
    assert sha256(capture).hexdigest() == pin["sha256"]
    captured_text = " ".join(
        html.unescape(re.sub("<[^>]*>", " ", capture.decode())).split()
    )
    assert "1998 1.3" in captured_text
    assert increase_by_colas(first.pia_in_force, [cola_1998]) == F("451.20")
    assert increase_by_colas(first.candidate_pia, [cola_1998]) == F("452.20")
    assert second.applied and second.pia_in_force == F("452.20")
    assert not no_earnings.applied and no_earnings.pia_in_force == F("451.20")


def test_invented_sub_dollar_fold_compares_against_pia_in_force():
    """35 years, original42000/420=100, PIA90.0; +420 =>101/90.9.

    The .90 increase is refused. Another420 =>102/91.8; against the
    original90.0 this raises1.8, accepted January2022. Zero COLAs.
    """
    original = basis(computation_years=35)
    history = {year: 0 for year in range(1951, 2022)}
    history.update({2019: 42000, 2020: 420, 2021: 420})
    results = r.recompute_sequence(
        original, history, [2020, 2021], 90, PARAMS, {2020: 0, 2021: 0}
    )
    assert [v.aime for v in results] == [101, 102]
    assert [v.candidate_eligibility_pia for v in results] == [
        F("90.9"),
        F("91.8"),
    ]
    assert [v.eligibility_pia_in_force for v in results] == [F(90), F("91.8")]
    assert results[1].decision.increase == F("1.8")
    assert results[1].effective_month == YearMonth(2022, 1)


def test_invented_dollar_threshold_is_compared_after_colas():
    """AIME100/PIA90.0 -> AIME101/PIA90.9; 12% COLA =>100.8/101.8.

    The eligibility-level .90 becomes an actual $1 PIA increase.
    """
    history = {year: 0 for year in range(1951, 2021)}
    history.update({2019: 42000, 2020: 420})
    result = annual(
        basis=basis(computation_years=35),
        history=history,
        eligibility_pia_of_record=90,
        december_cola_percent={2020: 12},
    )
    assert result.candidate_eligibility_pia == F("90.9")
    assert result.decision.pia_of_record == F("100.8")
    assert result.decision.candidate_pia == F("101.8")
    assert result.decision.applied


def test_invented_recomputation_uses_original_bend_points():
    """AIME1000 with 2020 bends960/5785 =>864+12.8=876.8.

    2021 bends996/6002 yield896.4+1.28=897.6, an intended $20.8 divergence.
    """
    result = annual(
        history={2018: 0, 2019: 0, 2020: 0, 2021: 420000},
        earnings_year=2021,
        eligibility_pia_of_record=0,
        december_cola_percent={2020: 0, 2021: 0},
    )
    assert result.aime == 1000
    assert result.candidate_eligibility_pia == F("876.8")
    assert r.exact_pia(1000, r.eligibility_bend_points(2021, PARAMS)) == F(
        "897.6"
    )


def test_unavailable_and_absent_base_years_never_become_zero():
    for history in (
        {2018: r.UNAVAILABLE, 2019: 42000, 2020: 63000},
        {2019: 42000, 2020: 63000},
    ):
        with pytest.raises(InvalidFamilyInput, match="2018"):
            annual(history=history)
    assert annual(history={2018: 0, 2019: 42000, 2020: 63000}).aime == 250


def test_first_statutory_base_year_cannot_be_hidden():
    history = {year: 0 for year in range(1952, 2021)}
    with pytest.raises(InvalidFamilyInput, match="1951"):
        r.annual_recomputation(basis(), history, 2020, 0, PARAMS, {2020: 0})
    with pytest.raises(InvalidFamilyInput, match="1951"):
        basis(first_base_year=2018)


def test_invented_aime_wage_caps_and_original_indexing_year():
    """1951 earnings2799.16 index to52145.80 at original2018 NAWI.

    With2019 earnings42000 and2020 earnings63000, total157145.80/420 floor374;
    original2020 bends960/5785 =>.9*374=336.6. Later NAWI is
    immaterial. Annual caps1000/2000/3000 instead give total6000/420=14.
    """
    history = {2018: 0, 2019: 42000, 2020: 63000, 1951: F("2799.16")}
    result = annual(history=history)
    assert result.aime == 374
    assert result.candidate_eligibility_pia == F("336.6")
    changed = ssa_params(
        nawi=PARAMS.nawi | {2019: 1_000_000},
        wage_base={1951: 1_000_000},
    )
    assert result == annual(history=history, params=changed)
    capped = ssa_params(wage_base={1951: 1000, 2019: 2000, 2020: 3000})
    assert annual(params=capped).aime == 14
    assert annual(params=capped).candidate_eligibility_pia == F("12.6")
    huge = {year: F(10) ** 400 for year in (2018, 2019, 2020)}
    assert annual(params=capped, history=huge).aime == 14


def test_later_earnings_never_enter_earlier_recomputation():
    base = annual()
    changed = annual(
        history={2018: 21000, 2019: 42000, 2020: 63000, 2021: 1_000_000}
    )
    assert base == changed
    unavailable_later = annual(
        history={2018: 21000, 2019: 42000, 2020: 63000, 2021: r.UNAVAILABLE}
    )
    assert base == unavailable_later


def test_death_year_after_fra_effective_death_month_and_cola_cutoff():
    """PIA135->270 effective November2026; December2026 COLA excluded.

    Invented DOB1958-06-02, RIB June2020, FRA February2025, death2026.
    Original63000/420=150/135; revised126000/420=300/270; zero priorCOLAs.
    December death includes10% December2026 COLA: candidate297.
    """
    result = death_annual(11, 99)
    assert result.effective_month == YearMonth(2026, 11)
    assert result.decision.pia_of_record == 135
    assert result.decision.candidate_pia == 270
    december = death_annual(12, 10)
    assert december.decision.candidate_pia == 297


def test_death_before_fra_is_named_refusal():
    with pytest.raises(FamilyConfigurationUnsupported) as error:
        annual(death_month=YearMonth(2020, 11), fra_month=YearMonth(2025, 2))
    assert (
        error.value.reason is r.RecomputationUnsupportedReason.DEATH_BEFORE_FRA
    )


def test_death_before_fra_not_assumed_when_fra_unavailable():
    with pytest.raises(InvalidFamilyInput, match="FRA"):
        annual(death_month=YearMonth(2020, 11))


def test_later_death_before_fra_does_not_change_earlier_recomputation():
    assert annual() == annual(
        death_month=YearMonth(2021, 11), fra_month=YearMonth(2025, 2)
    )


def test_later_death_refuses_entire_sequence_before_any_arithmetic():
    history = {year: 0 for year in range(1951, 2022)}
    with (
        patch.object(
            r, "_aime_from_prefix", wraps=r._aime_from_prefix
        ) as adapter,
        patch.object(
            r,
            "aime_with_computation_years",
            wraps=r.aime_with_computation_years,
        ) as aime,
        patch.object(r, "exact_pia", wraps=r.exact_pia) as pia,
    ):
        with pytest.raises(FamilyConfigurationUnsupported) as error:
            r.recompute_sequence(
                basis(),
                history,
                [2020, 2021],
                0,
                PARAMS,
                {2020: 0, 2021: 0},
                death_month=YearMonth(2021, 11),
                fra_month=YearMonth(2025, 2),
            )
        assert (
            error.value.reason
            is r.RecomputationUnsupportedReason.DEATH_BEFORE_FRA
        )
        assert (adapter.call_count, aime.call_count, pia.call_count) == (
            0,
            0,
            0,
        )


def test_invalid_original_count_precedes_later_death_sequence_refusal():
    history = {year: 0 for year in range(1951, 2022)}
    with pytest.raises(InvalidFamilyInput, match="computation count"):
        r.recompute_sequence(
            basis(computation_years=2),
            history,
            [2020, 2021],
            0,
            PARAMS,
            {2020: 0, 2021: 0},
            death_month=YearMonth(2021, 11),
            fra_month=YearMonth(2025, 2),
        )


def test_ordinary_rib_original_count_must_match_known_eligibility_basis():
    with pytest.raises(InvalidFamilyInput, match="computation count"):
        annual(basis=basis(computation_years=2))


@pytest.mark.parametrize("condition", list(r.RecomputationCondition))
def test_exceptional_conditions_have_named_refusals(condition):
    with pytest.raises(FamilyConfigurationUnsupported) as error:
        annual(basis=replace(basis(), conditions=frozenset({condition})))
    assert error.value.code == "FAMILY_CONFIG_UNSUPPORTED"
    assert (
        error.value.reason is r.RecomputationUnsupportedReason[condition.name]
    )


@pytest.mark.parametrize(
    "formula", [f for f in r.PIAFormula if f is not r.PIAFormula.AIME]
)
def test_non_aime_formulas_are_refused(formula):
    with pytest.raises(FamilyConfigurationUnsupported) as error:
        annual(basis=replace(basis(), formula=formula))
    assert (
        error.value.reason
        is r.RecomputationUnsupportedReason.NON_AIME_FORMULA_PIA
    )


@pytest.mark.parametrize(
    "formula", [f for f in r.PIAFormula if f is not r.PIAFormula.AIME]
)
@pytest.mark.parametrize("sequence", [False, True])
def test_refused_formula_never_calculates_ordinary_aime_or_pia(
    formula, sequence
):
    """Review's minimized AMW case: complete zero history, ELY2020."""
    original = basis(formula=formula)
    history = {year: 0 for year in range(1951, 2021)}
    with (
        patch.object(
            r, "_aime_from_prefix", wraps=r._aime_from_prefix
        ) as adapter,
        patch.object(
            r,
            "aime_with_computation_years",
            wraps=r.aime_with_computation_years,
        ) as aime,
        patch.object(r, "exact_pia", wraps=r.exact_pia) as pia,
    ):
        with pytest.raises(FamilyConfigurationUnsupported) as error:
            if sequence:
                r.recompute_sequence(
                    original, history, [2020], 0, PARAMS, {2020: 0}
                )
            else:
                r.annual_recomputation(
                    original, history, 2020, 0, PARAMS, {2020: 0}
                )
        assert (
            error.value.reason
            is r.RecomputationUnsupportedReason.NON_AIME_FORMULA_PIA
        )
        assert (adapter.call_count, aime.call_count, pia.call_count) == (
            0,
            0,
            0,
        )


@pytest.mark.parametrize("sequence", [False, True])
@pytest.mark.parametrize(
    "params",
    [
        replace(PARAMS, nawi=PARAMS.nawi | {2018: 0}),
        replace(PARAMS, nawi=PARAMS.nawi | {1951: -1}),
        replace(PARAMS, nawi=PARAMS.nawi | {2018: float("nan")}),
        replace(
            PARAMS, nawi={k: v for k, v in PARAMS.nawi.items() if k != 2018}
        ),
        replace(
            PARAMS, nawi={k: v for k, v in PARAMS.nawi.items() if k != 1951}
        ),
        replace(PARAMS, wage_base={}),
        replace(PARAMS, wage_base={1951: float("inf")}),
        replace(PARAMS, wage_base={1951: 1_000_000, 2021: 0}),
    ],
    ids=[
        "zero-original-nawi",
        "negative-early-nawi",
        "nonfinite-original-nawi",
        "missing-original-nawi",
        "missing-early-nawi",
        "missing-wage-base",
        "nonfinite-wage-base",
        "invalid-later-wage-base",
    ],
)
def test_refused_formula_validates_all_parameters_without_calculation(
    params, sequence
):
    original = basis(formula=r.PIAFormula.AMW)
    history = {year: 0 for year in range(1951, 2022)}
    with (
        patch.object(
            r, "_aime_from_prefix", wraps=r._aime_from_prefix
        ) as adapter,
        patch.object(r, "exact_pia", wraps=r.exact_pia) as pia,
    ):
        with pytest.raises(InvalidFamilyInput):
            if sequence:
                r.recompute_sequence(
                    original,
                    history,
                    [2020, 2021],
                    0,
                    params,
                    {2020: 0, 2021: 0},
                )
            else:
                r.annual_recomputation(
                    original, history, 2021, 0, params, {2020: 0, 2021: 0}
                )
        assert (adapter.call_count, pia.call_count) == (0, 0)


@pytest.mark.parametrize("sequence", [False, True])
@pytest.mark.parametrize("field", ["earnings", "cola"])
def test_refused_formula_validates_complete_histories_before_calculation(
    field, sequence
):
    original = basis(formula=r.PIAFormula.AMW)
    history = {year: 0 for year in range(1951, 2022)}
    colas = {2020: 0, 2021: 0}
    (history if field == "earnings" else colas)[2021] = r.UNAVAILABLE
    with patch.object(
        r, "_aime_from_prefix", wraps=r._aime_from_prefix
    ) as adapter:
        with pytest.raises(InvalidFamilyInput, match="2021"):
            if sequence:
                r.recompute_sequence(
                    original, history, [2020, 2021], 0, PARAMS, colas
                )
            else:
                r.annual_recomputation(
                    original, history, 2021, 0, PARAMS, colas
                )
        assert adapter.call_count == 0


@pytest.mark.parametrize(
    "conditions", [[], [r.RecomputationCondition.ADMINISTRATIVE_FINALITY]]
)
def test_iterator_conditions_are_frozen_for_repeated_evaluation(conditions):
    original = basis(conditions=iter(conditions))
    assert original.conditions == frozenset(conditions)
    assert isinstance(original.conditions, frozenset)
    first = r.evaluate_recomputation(
        "first", 1, lambda: annual(basis=original)
    )
    second = r.evaluate_recomputation(
        "second", 1, lambda: annual(basis=original)
    )
    assert first.result == second.result
    assert first.supported == second.supported == (not conditions)
    if conditions:
        assert first.unsupported.reason == second.unsupported.reason
        assert count_family_outcomes([first, second]).unsupported_rows == 2


def test_cfr1979_roundup_example_explicitly_outside_modern_scope():
    """CFR404.284 Ex1: AIME911 gives raw395.92, historical roundup396.00.

    Historical COLAs9.9/14.3/11.2 give435.30/497.60/553.40. G's modern
    floor yields395.90/435.00/497.20/552.80; historical formula refused.
    """
    old = basis(
        eligibility_year=1979,
        indexing_year=1977,
        computation_years=23,
        first_base_year=1951,
        entitlement_month=YearMonth(1979, 6),
        bend_points=(180, 1085),
    )
    assert r.exact_pia(911, old.bend_points) == F("395.9")
    with pytest.raises(FamilyConfigurationUnsupported) as error:
        annual(
            basis=old,
            history={1977: 0, 1978: 0, 1979: 11000},
            earnings_year=1979,
            eligibility_pia_of_record="432.4",
            december_cola_percent={1979: 0},
        )
    assert (
        error.value.reason
        is r.RecomputationUnsupportedReason.ELIGIBILITY_BEFORE_1983
    )


def test_cfr404284_example_one_historical_arithmetic_reproduced_separately():
    """Historical statutory demonstration; supported API refuses1979.

    Source supplies total251470.05, replaced8911.36, new11000. Derived
    oldtotal249381.41, divisor23*12=276: oldAIME903, newAIME911.
    Historical PIA ceiling393.36->393.4 and9.9% ceiling->432.4;
    revised395.92->396.0, then9.9/14.3/11.2%->435.3/497.6/553.4.
    Derived whole-dollar values are 432 and 435/497/553, respectively.
    """
    total = F("251470.05")
    old_total = total - 11000 + F("8911.36")
    assert old_total == F("249381.41")
    assert math.floor(old_total / 276) == 903
    assert math.floor(total / 276) == 911
    old_raw = F(180) * F(9, 10) + F(903 - 180) * F(8, 25)
    new_raw = F(180) * F(9, 10) + F(911 - 180) * F(8, 25)
    assert old_raw == F("393.36")
    assert new_raw == F("395.92")
    old_pia = ceil_dime(ceil_dime(old_raw) * F("1.099"))
    assert old_pia == F("432.4")
    assert whole_dollars(old_pia) == 432
    value = ceil_dime(new_raw)
    assert value == 396
    for multiplier, expected, whole in [
        (F("1.099"), F("435.3"), 435),
        (F("1.143"), F("497.6"), 497),
        (F("1.112"), F("553.4"), 553),
    ]:
        value = ceil_dime(value * multiplier)
        assert value == expected
        assert whole_dollars(value) == whole


def test_cfr404284_example_two_amw_table_and_historical_colas():
    """SourceAMW502->537, tablePIA407.7, COLAs->448.1/512.2/569.6.

    Source initialJune1978 PIA429.20 uses an unavailable benefit-table
    row; it is explicitly a source-supplied amount, not an AIME result.
    The original amount implies132700 total:142000-12000+2700.
    Derived whole-dollar values are 429 initially, 448/512/569 for the
    candidate and 471/539/599 when the initial PIA receives those COLAs.
    """
    assert math.floor((142000 - 12000 + 2700) / 264) == 502
    assert math.floor(142000 / 264) == 537
    supplied_initial_pia = F("429.20")
    assert whole_dollars(supplied_initial_pia) == 429
    value = F("407.7")
    for multiplier, expected, whole in [
        (F("1.099"), F("448.1"), 448),
        (F("1.143"), F("512.2"), 512),
        (F("1.112"), F("569.6"), 569),
    ]:
        value = ceil_dime(value * multiplier)
        assert value == expected
        assert whole_dollars(value) == whole
    with pytest.raises(FamilyConfigurationUnsupported) as error:
        annual(basis=replace(basis(), formula=r.PIAFormula.AMW))
    assert (
        error.value.reason
        is r.RecomputationUnsupportedReason.NON_AIME_FORMULA_PIA
    )
    # The capture's supplied replacement tablePIA is lower than its
    # supplied oldPIA. Applying identical historical COLAs to both cannot
    # resolve that contradiction; do not claim an effective recomputation.
    assert F("407.70") - supplied_initial_pia == F("-21.50")
    old_value = supplied_initial_pia
    for multiplier, expected, whole in [
        (F("1.099"), F("471.70"), 471),
        (F("1.143"), F("539.20"), 539),
        (F("1.112"), F("599.60"), 599),
    ]:
        old_value = ceil_dime(old_value * multiplier)
        assert old_value == expected
        assert whole_dollars(old_value) == whole
    assert value == F("569.60")
    assert value - old_value == -30
    assert not r.recomputation_decision(old_value, value).applied


def test_pre1979_amw_earnings_is_coverage_refusal_not_invalid_input():
    """CFR404.284 Ex2's 1978 earnings/January1979 date is legal legacy.

    Its AMW formula is outside the supported ordinary AIME method. A
    complete invented history demonstrates refusal rather than a date
    input error; the table arithmetic is checked separately above.
    """
    original = basis(
        eligibility_year=1978,
        indexing_year=1976,
        computation_years=22,
        entitlement_month=YearMonth(1978, 6),
        bend_points=(180, 1085),
        formula=r.PIAFormula.AMW,
    )
    history = {year: 0 for year in range(1951, 1979)}
    history[1978] = 12000
    with pytest.raises(FamilyConfigurationUnsupported) as error:
        r.annual_recomputation(
            original, history, 1978, "429.2", PARAMS, {1978: 0}
        )
    assert (
        error.value.reason
        is r.RecomputationUnsupportedReason.ELIGIBILITY_BEFORE_1983
    )
    with pytest.raises(FamilyConfigurationUnsupported):
        r.recompute_sequence(
            original, history, [1978], "429.2", PARAMS, {1978: 0}
        )


def test_minimized_cent_earnings_float_aime_boundary_is_intended_correction():
    """Lexicographic cent search: .02+2.07+33.91=$36 exact /36=1.

    Sorted binary sum is35.99999999999999: old oracle floors to0. Two
    cent-valued summands totaling24 have no such AIME1 counterexample.
    R3's exact guard returns1, explicitly preserving the statutory floor.
    """
    original = basis(computation_years=3)
    history = explicit_early_zeros(
        {2018: F(".02"), 2019: F("2.07"), 2020: F("33.91")}
    )
    assert (
        aime_with_computation_years(history, 3, PARAMS, indexing_year=2018)
        == 0
    )
    assert r.earnings_aime(history, original, 2020, PARAMS) == 1


def test_statutory_bend_half_dollar_tie_up_is_intended_oracle_divergence():
    params = ssa_params(nawi={1977: 360, 2018: 361})
    assert params.bend_points(2020)[0] == 180
    assert r.eligibility_bend_points(2020, params)[0] == 181


@pytest.mark.parametrize(
    "history",
    [{2018: -1, 2019: 0, 2020: 0}, {2018: r.UNAVAILABLE, 2019: 0, 2020: 0}],
)
def test_input_errors_precede_coverage_refusal(history):
    unsupported = replace(basis(), formula=r.PIAFormula.OLD_START)
    with pytest.raises(InvalidFamilyInput):
        annual(basis=unsupported, history=history)


def test_recomputation_refusals_stay_in_denominator_and_block_target():
    supported = r.evaluate_recomputation("yes", 2, annual)
    refused = r.evaluate_recomputation(
        "no",
        3,
        lambda: annual(basis=replace(basis(), formula=r.PIAFormula.GUARANTEE)),
    )
    counts = count_family_outcomes([supported, refused])
    assert (counts.rows, counts.weight) == (2, 5)
    assert (counts.unsupported_rows, counts.unsupported_weight) == (1, 3)
    assert counts.supported_weight_share == F(2, 5)
    with pytest.raises(FamilyTargetBlocked):
        r.weighted_recomputed_pia([supported, refused])
    assert r.weighted_recomputed_pia([supported]) == 540
    with pytest.raises(InvalidFamilyInput):
        r.evaluate_recomputation("bad", 1, lambda: annual(history={}))


@pytest.mark.parametrize("years", [[2021, 2020], [2020, 2020]])
def test_annual_fold_requires_strict_chronology(years):
    with pytest.raises(InvalidFamilyInput, match="increase strictly"):
        r.recompute_sequence(basis(), {}, years, 135, PARAMS, {})


def test_later_fold_input_error_precedes_earlier_coverage_refusal():
    unsupported = replace(basis(), formula=r.PIAFormula.GUARANTEE)
    with pytest.raises(InvalidFamilyInput, match="2021"):
        r.recompute_sequence(
            unsupported,
            explicit_early_zeros(
                {2018: 0, 2019: 0, 2020: 1, 2021: r.UNAVAILABLE}
            ),
            [2020, 2021],
            0,
            PARAMS,
            {2020: 0, 2021: 0},
        )


@pytest.mark.parametrize(
    "values",
    [
        {"computation_years": 0},
        {"indexing_year": 2019},
        {"first_base_year": 1950},
        {"bend_points": (960, 900)},
        {"entitlement_end_month": YearMonth(2019, 1)},
    ],
)
def test_invalid_original_basis_is_input_error(values):
    with pytest.raises(InvalidFamilyInput):
        basis(**values)


@pytest.mark.parametrize("value", [None, 1, False])
def test_invalid_collection_inputs_raise_input_error(value):
    with pytest.raises(InvalidFamilyInput):
        basis(conditions=value)
    with pytest.raises(InvalidFamilyInput):
        r.recompute_sequence(basis(), {}, value, 0, PARAMS, {})


@pytest.mark.parametrize(
    "values",
    [
        {"december_cola_percent": {}},
        {"december_cola_percent": {2020: -1}},
        {"eligibility_pia_of_record": F("135.01")},
        {"earnings_year": 2019},
        {"history": {2018: 1.1, 2019: 0, 2020: 0}},
    ],
)
def test_invalid_annual_input_is_input_error(values):
    with pytest.raises(InvalidFamilyInput):
        annual(**values)


def test_current_pia_never_decreases_even_if_candidate_is_lower():
    result = annual(eligibility_pia_of_record=1000)
    assert not result.decision.applied
    assert result.decision.pia_in_force == 1000
    assert result.eligibility_pia_in_force == 1000


def test_no_earnings_cannot_trigger_an_earlier_candidate():
    result = annual(
        history={2018: 21000, 2019: 63000, 2020: 0},
        eligibility_pia_of_record=0,
    )
    assert result.candidate_eligibility_pia == 180
    assert not result.decision.applied


def test_cola_rounding_occurs_after_each_increase():
    assert increase_by_colas(F("90.9"), [12, 10]) == F("111.9")
