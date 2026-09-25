"""The C0 membership guard of exercise 3, end to end, on INVENTED data.

Registration 14 (issue #42) ran the exercise-3 one-shot at ``a9b0d09f``
and the runner refused it at row F0: under fixed claim ages (C0) eight
person-draw rows were recipients in the baseline only.  A membership-only
diagnostic traced every one to one mechanism (E1 section 27): a disabled
worker born 1963 with a zero own DI level, married to a retired worker,
whom the projection converts at the baseline FRA of 67 in 2030 and whom
the reform (FRA 68, attained in 2031) leaves a disabled worker in 2030.
By Track A's convention a disabled worker still entitled to DI draws no
spouse's excess, so the reform pays nothing and the baseline pays the
excess.  ``e1-ratified-2`` names this mechanism (E1 section 12) and the
runner now refuses only differences it does not explain.

Every person, date, earnings amount and weight below is INVENTED: the
Track A invented cohort, with the 2030 state of one invented couple set by
the test.  No PSID value, no model output and no comparator value is
read.  This module imports only names that exist at ``a9b0d09f``, so
:func:`test_a_zero_level_di_spouse_is_a_named_baseline_only_recipient`
runs there too, and fails there: the guard refuses the run.
"""

from __future__ import annotations

import dataclasses

import pandas as pd
import pytest

from populace_dynamics.cola_track_a import runner as track_runner
from populace_dynamics.fra68_track import FRA68Config, run_fra68
from populace_dynamics.fra68_track import runner as fra68_runner
from tests.fra68_track.test_runner import _inputs

#: INVENTED persons of the invented cohort (both waves): the wife, born
#: 1963 and first in covered work in 1985, and her husband, born 1960.
WIFE, HUSBAND = 110902, 110901
WIFE_BIRTH, HUSBAND_BIRTH = 1963, 1960
#: INVENTED: a DI award in 1984, before the wife's first covered earnings,
#: so the disclosed approximation reads no earnings through the onset and
#: her own DI level is zero (the AIME floors to 0).
ZERO_LEVEL_AWARD_YEAR = 1984
#: INVENTED: the husband claims retirement at 67 (his FRA) in 2027.
HUSBAND_CLAIM_YEAR = 2027
#: A4's conversion year for the wife, July birth month: FRA 67 (804
#: months) is attained in 2030 under the statute, FRA 68 (816 months) in
#: 2031 under every reform schedule.
BASELINE_CONVERSION, REFORM_CONVERSION = 2030, 2031
MECHANISM = "spouse_excess_withheld_until_reform_conversion"
WITHHELD = "fra68_spouse_excess_withheld_until_reform_conversion"
C0_ALL_COMPONENT_ROWS = ("F0", "F1", "F2", "F5", "F7", "F8")
CONFIG = FRA68Config(draw_indices=(0, 1))

_COUPLE_STATE = {
    WIFE: {
        "birth_year": WIFE_BIRTH,
        "di_entitled": False,
        "di_award_year": ZERO_LEVEL_AWARD_YEAR,
        "di_conversion_year": BASELINE_CONVERSION,
        "di_recovery_year": pd.NA,
        "claimed": True,
        "claim_year": BASELINE_CONVERSION,
        "claim_age": BASELINE_CONVERSION - WIFE_BIRTH,
        "marital_status": "married",
        "spouse_person_id": HUSBAND,
        "late_spouse_person_id": pd.NA,
        "widowhood_year": pd.NA,
    },
    HUSBAND: {
        "birth_year": HUSBAND_BIRTH,
        "di_entitled": False,
        "di_award_year": pd.NA,
        "di_conversion_year": pd.NA,
        "di_recovery_year": pd.NA,
        "claimed": True,
        "claim_year": HUSBAND_CLAIM_YEAR,
        "claim_age": HUSBAND_CLAIM_YEAR - HUSBAND_BIRTH,
        "marital_status": "married",
        "spouse_person_id": WIFE,
        "late_spouse_person_id": pd.NA,
        "widowhood_year": pd.NA,
    },
}


def _with_couple(result, cohort):
    """The projected draw with the INVENTED couple's 2030 state set.

    A partner of either spouse in the projected state keeps its own state;
    the couple is alive in 2030 in every draw (a row is added from the
    opening roster if the projection had them die).
    """

    final = result.slices[-1].copy()
    year = int(final["year"].iloc[0])
    for person_id, fields in _COUPLE_STATE.items():
        if not (final["person_id"] == person_id).any():
            opening = cohort.initial_slice
            row = opening.loc[opening["person_id"] == person_id].copy()
            row["year"] = year
            row["age"] = year - fields["birth_year"]
            final = pd.concat([final, row], ignore_index=True)
        mask = final["person_id"] == person_id
        for name, value in fields.items():
            final.loc[mask, name] = value
        final.loc[mask, "age"] = year - fields["birth_year"]
    return dataclasses.replace(result, slices=(*result.slices[:-1], final))


@pytest.fixture
def couple(monkeypatch):
    """Every projected draw of both waves carries the INVENTED couple."""

    original = track_runner._project_population

    def project(cohort, inputs, track_config, **kwargs):
        results, diagnostics = original(cohort, inputs, track_config, **kwargs)
        return {
            draw: _with_couple(result, cohort)
            for draw, result in results.items()
        }, diagnostics

    monkeypatch.setattr(track_runner, "_project_population", project)
    captured: dict[tuple[str, int], list[dict]] = {}
    union = fra68_runner.union_benefit_rows

    def capture(base, reform, **kwargs):
        rows, counters = union(base, reform, **kwargs)
        key = (id(reform), int(kwargs["draw"]))
        captured[key] = [row for row in rows if row["person_id"] == WIFE]
        return rows, counters

    monkeypatch.setattr(fra68_runner, "union_benefit_rows", capture)
    return captured


def test_a_zero_level_di_spouse_is_a_named_baseline_only_recipient(couple):
    # Regression for Registration 14's refusal.  At a9b0d09f the runner
    # raised "F0: under fixed claim ages (C0) the baseline and reform
    # memberships must coincide, but 2 rows are recipients in one scenario
    # only" here; e1-ratified-2 names the mechanism, so the run completes,
    # counts the rows and records them in the artifact.
    result = run_fra68(_inputs(), config=CONFIG)
    # The wife's A7 rows: a recipient of the spouse's excess alone in the
    # baseline (converted, own level zero), a disabled worker with nothing
    # in the reform.
    wife_rows = [row for rows in couple.values() for row in rows]
    assert wife_rows
    for row in wife_rows:
        assert row["birth_year"] == WIFE_BIRTH
        assert (row["beneficiary_base"], row["beneficiary_reform"]) == (
            True,
            False,
        )
        assert (row["own_kind_base"], row["own_kind_reform"]) == (
            "converted",
            "disabled",
        )
        components = row["benefit_components"]
        assert components["spouse"]["base"] > 0
        assert components["spouse"]["reform"] == 0
        assert components["retired_worker"] == {"base": 0.0, "reform": 0.0}
        assert components["disabled_worker"] == {"base": 0.0, "reform": 0.0}
        assert row["benefit_reform"] == 0
        assert row["fra_increase_months"] == 12
    for row_id in C0_ALL_COMPONENT_ROWS:
        entry = result["rows"][row_id]
        assert entry["status"].startswith("tabulated"), (row_id, entry)
        record = entry["membership_differences"]
        assert record["classified"] is True
        assert record["claiming_response"] == "c0_fixed_claim_ages"
        assert record["not_explained_allowed"] is False
        # One row per draw: the wife, a baseline-only recipient.
        assert record["n_rows_differ"] == 2, row_id
        assert record["n_rows_baseline_only"] == 2
        assert record["n_rows_reform_only"] == 0
        assert record["n_rows_not_explained"] == 0
        named = record["named_mechanisms"][MECHANISM]
        assert named["n_rows"] == 2
        assert named["n_rows_by_draw"] == {"0": 1, "1": 1}
        assert named["n_rows_by_birth_year"] == {str(WIFE_BIRTH): 2}
        # A7's count agrees, and the statistic's sets are
        # scenario-specific: the wife is in S_base, not in S_reform.
        summary = entry["tabulation"]["input_summary"]
        assert summary["n_rows_membership_differs"] == 2
        assert summary["n_recipient_rows"]["base"] == (
            summary["n_recipient_rows"]["reform"] + 2
        )
        counters = entry["benefit_counters"]
        assert counters[WITHHELD] == 2
        assert counters[f"{WITHHELD}_no_reform_benefit"] == 2
    # Workers only (F6): the spouse's excess is not selected and the own
    # level is zero, so the wife is a recipient in neither scenario.
    f6 = result["rows"]["F6"]["membership_differences"]
    assert f6["n_rows_differ"] == 0
    assert f6["named_mechanisms"][MECHANISM]["n_rows"] == 0
    # C1 and C2 leave conversions unchanged (E1 section 13): the same
    # rows, counted; other differences are allowed there.
    for row_id in ("F3", "F4"):
        record = result["rows"][row_id]["membership_differences"]
        assert record["not_explained_allowed"] is True
        assert record["named_mechanisms"][MECHANISM]["n_rows"] == 2
    assert result["specification_check"]["consistent"]


def _zero_one_reform(rows, *, reform_only: bool):
    """INVENTED defect: one projected retired worker's row made one-sided.

    ``reform_only`` False zeroes the reform amount (a baseline-only
    recipient); True zeroes the baseline amount (a reform-only one).
    Neither is the named mechanism.
    """

    for row in rows:
        if row["basis"] != "projected" or set(row["benefit_components"]) != {
            "retired_worker"
        }:
            continue
        if row["benefit_base"] <= 0 or row["benefit_reform"] <= 0:
            continue
        side = "base" if reform_only else "reform"
        row[f"benefit_{side}"] = 0.0
        row[f"beneficiary_{side}"] = False
        row["benefit_components"]["retired_worker"][side] = 0.0
        return row["person_id"]
    raise AssertionError("no projected retired worker in the invented draw")


@pytest.mark.parametrize("reform_only", [False, True])
def test_an_unexplained_c0_difference_refuses_before_any_tabulation(
    monkeypatch, reform_only
):
    # A membership difference the named mechanism does not explain still
    # refuses, and now before A7 tabulates any row (the earlier guard ran
    # after A7 had tabulated the row).  INVENTED one-sided rows.
    union = fra68_runner.union_benefit_rows
    changed = []

    def one_sided(base, reform, **kwargs):
        rows, counters = union(base, reform, **kwargs)
        if int(kwargs["draw"]) == 0 and not changed:
            changed.append(_zero_one_reform(rows, reform_only=reform_only))
        return rows, counters

    tabulated = []

    def no_tabulation(*args, **kwargs):
        tabulated.append(kwargs.get("statistic_id"))
        raise AssertionError("a row was tabulated before the refusal")

    monkeypatch.setattr(fra68_runner, "union_benefit_rows", one_sided)
    monkeypatch.setattr(
        fra68_runner, "tabulate_cola_age_profile", no_tabulation
    )
    with pytest.raises(ValueError) as refused:
        run_fra68(_inputs(), config=FRA68Config(draw_indices=(0, 1)))
    message = str(refused.value)
    assert "may differ only through the named mechanisms" in message
    assert MECHANISM in message
    assert "no row was tabulated" in message
    assert f"person {changed[0]!r}" in message
    assert tabulated == []


def test_a_named_row_does_not_mask_an_unexplained_one(couple, monkeypatch):
    # The couple's rows are explained; one INVENTED one-sided row is not,
    # and the run is still refused.
    union = fra68_runner.union_benefit_rows
    changed = []

    def one_sided(base, reform, **kwargs):
        rows, counters = union(base, reform, **kwargs)
        if int(kwargs["draw"]) == 1 and not changed:
            changed.append(_zero_one_reform(rows, reform_only=False))
        return rows, counters

    monkeypatch.setattr(fra68_runner, "union_benefit_rows", one_sided)
    with pytest.raises(ValueError, match="for another reason") as refused:
        run_fra68(_inputs(), config=CONFIG)
    assert "1 of 3 rows" in str(refused.value)
