"""The row-U7 employer DC rule on INVENTED pension-section records.

Every record here is INVENTED: plan-type codes, dispositions and amounts
are made up so that each expected balance can be worked by hand, or drawn
by Hypothesis from the codebooks' code domains.  None is a PSID value.

Invariants held for every input (property tests):

* the balance is the current-job part plus the previous-employer part,
  and neither is negative;
* the rule equals an independent, row-by-row reference implementation
  written here from the specification's text (a differential test);
* an account rolled over into an IRA, an amount the codebooks do not
  route to its plan's type, and a DK or refused amount never add to the
  balance;
* no previous plan contributes through both its "both" items (P48-P49)
  and its account items (P64-P65): the codebooks' two routes are
  disjoint for every plan-type code, so one account is never counted
  twice;
* ``employer_dc_unreported`` counts exactly the DK and refused amounts on
  a counted route, and ``employer_dc_ira_rollover_items`` exactly the
  rolled-over accounts on an account route;
* the head's and the wife's items are interchangeable (swapping them
  leaves every family total unchanged), and the rule is row-wise
  (permuting families permutes the result).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.data import employer_dc as ed

WAVES = ed.EMPLOYER_DC_WAVES
OLD, NEW = 2005, 2011


def _raw(wave: int, rows: list[dict[str, int]]) -> pd.DataFrame:
    """INVENTED records: every concept 0 unless a row sets it."""

    concepts = list(ed.employer_dc_variables(wave))
    frame = pd.DataFrame(
        [
            {**dict.fromkeys(concepts, 0), "interview": i + 1, **row}
            for i, row in enumerate(rows)
        ]
    )
    return frame[concepts].astype("int64")


def _one(wave: int, **items: int) -> pd.Series:
    return ed.employer_dc_balances(_raw(wave, [items]), wave).iloc[0]


# ---------------------------------------------------------------------------
# Tables and codes
# ---------------------------------------------------------------------------
def test_tables_cover_both_persons_and_both_previous_plans():
    for wave in WAVES:
        table = ed.employer_dc_variables(wave)
        assert list(table)[0] == "interview"
        concepts = [c for c in table if c != "interview"]
        assert len(concepts) == 24
        for person in ed.PERSONS:
            assert f"{person}_current_type" in concepts
            assert f"{person}_current_amount" in concepts
            for plan in ed.PREVIOUS_PLANS:
                for item in (
                    "type",
                    "combo_disposition",
                    "combo_amount",
                    "dc_disposition",
                    "dc_amount",
                ):
                    assert f"{person}_prev{plan}_{item}" in concepts
        variables = [var for var, _ in table.values()]
        labels = [" ".join(label.split()) for _, label in table.values()]
        assert len(set(variables)) == len(variables)
        assert len(set(labels)) == len(labels)
        suffix = {"head": " - HD", "wife": " - WF"}
        for concept, (_, label) in table.items():
            if concept == "interview":
                continue
            person = concept.split("_")[0]
            if wave in (2011, 2013):
                assert label.endswith(suffix[person]), label
            else:
                assert " - " not in label, label
            # the question each concept names, by its number
            number = int(label.split()[0][1:])
            base = number - (70 if person == "wife" and wave < 2011 else 0)
            kind = concept.split(f"{person}_", 1)[1]
            expected = {
                "current_type": 16,
                "current_amount": 20,
                "type": 46,
                "combo_disposition": 48,
                "combo_amount": 49,
                "dc_disposition": 64,
                "dc_amount": 65,
            }[kind.split("_", 1)[1] if kind.startswith("prev") else kind]
            assert base == expected, (wave, concept, label)


def test_amount_codes_follow_the_field_width():
    assert ed.amount_codes(9) == {
        "top": 999_999_997,
        "dk": 999_999_998,
        "na": 999_999_999,
    }
    assert ed.amount_codes(8) == {
        "top": 99_999_997,
        "dk": 99_999_998,
        "na": 99_999_999,
    }
    with pytest.raises(ValueError):
        ed.amount_codes(1)


def test_plan_type_codes_change_in_2011():
    assert ed.plan_type_codes(OLD) == {
        "current_account": 5,
        "current_both": 3,
        "previous_formula": 1,
        "previous_account": 2,
        "previous_both": 3,
        "previous_dk": 8,
    }
    for wave in (2011, 2013):
        assert ed.plan_type_codes(wave) == {
            "current_account": 5,
            "current_both": 7,
            "previous_formula": 1,
            "previous_account": 5,
            "previous_both": 7,
            "previous_dk": 8,
        }
    with pytest.raises(ValueError, match="outside the resolved"):
        ed.employer_dc_variables(2003)


def test_undocumented_codes_are_refused():
    frame = _raw(OLD, [{"head_prev1_type": 5}])
    with pytest.raises(ValueError, match="undocumented code"):
        ed._check_codes(frame, OLD, "INVENTED")
    frame = _raw(NEW, [{"head_prev1_type": 2}])
    with pytest.raises(ValueError, match="undocumented code"):
        ed._check_codes(frame, NEW, "INVENTED")
    frame = _raw(OLD, [{"wife_prev2_dc_disposition": 5}])
    with pytest.raises(ValueError, match="undocumented code"):
        ed._check_codes(frame, OLD, "INVENTED")
    frame = _raw(OLD, [{"head_prev1_dc_amount": 100_000_000}])
    with pytest.raises(ValueError, match="outside 0-99999999"):
        ed._check_codes(frame, OLD, "INVENTED")
    ed._check_codes(_raw(NEW, [{"head_current_type": 7}]), NEW, "INVENTED")
    with pytest.raises(ValueError, match="lack"):
        ed.employer_dc_balances(
            _raw(OLD, [{}]).drop(columns=["head_prev2_dc_amount"]), OLD
        )


# ---------------------------------------------------------------------------
# The worked cases of specification section 13
# ---------------------------------------------------------------------------
def test_current_job_account_counts_only_under_an_account_plan():
    counted = _one(OLD, head_current_type=5, head_current_amount=30_000)
    assert counted["employer_dc"] == 30_000
    assert counted["employer_dc_current"] == 30_000
    assert counted["employer_dc_items"] == 1
    formula = _one(OLD, head_current_type=1, head_current_amount=30_000)
    assert formula["employer_dc"] == 0
    assert formula["employer_dc_off_route_items"] == 1
    both_new = _one(NEW, wife_current_type=7, wife_current_amount=4_000)
    assert both_new["employer_dc"] == 4_000
    # before 2011 "Both" is code 3
    both_old = _one(OLD, wife_current_type=3, wife_current_amount=4_000)
    assert both_old["employer_dc"] == 4_000


def test_previous_accounts_left_to_accumulate_count_and_iras_do_not():
    row = _one(
        OLD,
        head_prev1_type=2,
        head_prev1_dc_disposition=3,
        head_prev1_dc_amount=20_000,
        head_prev2_type=2,
        head_prev2_dc_disposition=2,
        head_prev2_dc_amount=35_000,
    )
    assert row["employer_dc"] == 20_000
    assert row["employer_dc_previous"] == 20_000
    assert row["employer_dc_ira_rollover_items"] == 1


def test_both_plans_count_and_formula_plans_do_not():
    row = _one(
        NEW,
        head_prev1_type=7,
        head_prev1_combo_disposition=3,
        head_prev1_combo_amount=9_000,
        wife_prev1_type=1,
        wife_prev1_dc_disposition=3,
        wife_prev1_dc_amount=15_000,
    )
    assert row["employer_dc"] == 9_000
    assert row["employer_dc_off_route_items"] == 1


def test_a_dk_type_plan_counts_through_its_account_items_only():
    """The codebooks route a plan of DK type (8) to the account items
    P63-P65 in every wave (their ``Inap.`` names Type A, combination and
    refused types only), and not to the "both" items P47-P49."""

    for wave in (OLD, NEW):
        row = _one(
            wave,
            head_prev2_type=8,
            head_prev2_dc_disposition=3,
            head_prev2_dc_amount=12_000,
            wife_prev1_type=8,
            wife_prev1_combo_disposition=3,
            wife_prev1_combo_amount=4_000,
        )
        assert row["employer_dc"] == 12_000, wave
        assert row["employer_dc_items"] == 1
        assert row["employer_dc_off_route_items"] == 1
        rolled = _one(
            wave,
            head_prev1_type=8,
            head_prev1_dc_disposition=2,
            head_prev1_dc_amount=7_000,
        )
        assert rolled["employer_dc"] == 0
        assert rolled["employer_dc_ira_rollover_items"] == 1


def test_a_both_plans_account_is_counted_once():
    """A "both" plan's account is asked at P48-P49; an amount in the
    account items P64-P65 of the same plan is off the codebooks' route
    (the staged files carry some, often beside a P49 amount) and is not
    counted, so one account is never counted twice."""

    for wave, both in ((OLD, 3), (NEW, 7)):
        row = _one(
            wave,
            head_prev1_type=both,
            head_prev1_combo_disposition=3,
            head_prev1_combo_amount=9_000,
            head_prev1_dc_disposition=3,
            head_prev1_dc_amount=9_000,
        )
        assert row["employer_dc"] == 9_000, wave
        assert row["employer_dc_items"] == 1
        assert row["employer_dc_off_route_items"] == 1


def test_unreported_amounts_count_as_zero_and_the_top_code_as_recorded():
    dk = ed.amount_codes(9)["dk"]
    row = _one(OLD, head_current_type=5, head_current_amount=dk)
    assert row["employer_dc"] == 0
    assert row["employer_dc_unreported"] == 1
    assert row["employer_dc_items"] == 0
    top = ed.amount_codes(8)["top"]
    row = _one(
        OLD,
        wife_prev2_type=2,
        wife_prev2_dc_disposition=3,
        wife_prev2_dc_amount=top,
    )
    assert row["employer_dc"] == top
    assert row["employer_dc_top_coded"] == 1


def test_other_dispositions_count_nothing():
    for disposition in (0, 1, 4, 7, 8, 9):
        row = _one(
            OLD,
            head_prev1_type=3,
            head_prev1_combo_disposition=disposition,
            head_prev1_combo_amount=5_000,
        )
        assert row["employer_dc"] == 0, disposition
        assert row["employer_dc_ira_rollover_items"] == 0
    # a "both" plan's combination items count only for a "both" plan
    row = _one(
        OLD,
        head_prev1_type=2,
        head_prev1_combo_disposition=3,
        head_prev1_combo_amount=5_000,
    )
    assert row["employer_dc"] == 0
    assert row["employer_dc_off_route_items"] == 1


def test_reconciliation_counts_routes():
    frame = ed.employer_dc_balances(
        _raw(
            OLD,
            [
                {"head_current_type": 1, "head_current_amount": 10},
                {
                    "head_prev1_type": 1,
                    "head_prev1_dc_disposition": 3,
                    "head_prev1_dc_amount": 10,
                },
                {
                    "head_prev1_type": 2,
                    "head_prev1_dc_disposition": 1,
                    "head_prev1_dc_amount": 10,
                },
                {
                    "head_prev1_type": 2,
                    "head_prev1_dc_disposition": 2,
                    "head_prev1_dc_amount": 10,
                },
                {
                    "wife_prev2_type": 3,
                    "wife_prev2_combo_disposition": 3,
                    "wife_prev2_combo_amount": 10,
                    "wife_prev2_dc_disposition": 3,
                    "wife_prev2_dc_amount": 10,
                },
                {
                    "head_prev2_type": 8,
                    "head_prev2_dc_disposition": 3,
                    "head_prev2_dc_amount": 10,
                },
            ],
        ),
        OLD,
    )
    counts = ed.reconcile_employer_dc(frame, OLD)
    assert counts["n_families"] == 6
    assert counts["current_amount_without_account_plan"] == 1
    assert counts["dc_amount_plan_type_formula"] == 1
    assert counts["dc_amount_plan_type_account"] == 2
    assert counts["dc_amount_plan_type_both"] == 1
    assert counts["dc_amount_plan_type_dk"] == 1
    assert counts["dc_amount_plan_type_na"] == 0
    assert counts["dc_amount_plan_type_inap"] == 0
    assert counts["plans_with_combo_and_dc_amounts"] == 1
    assert counts["combo_amount_off_route"] == 0
    assert counts["dc_amount_disposition_off_route"] == 1
    assert counts["families_with_ira_rollover_excluded"] == 1
    # the "both" plan's combo amount and the DK-type account count
    assert counts["families_employer_dc_positive"] == 2
    assert counts["families_previous_positive"] == 2
    # the current-job amount under a formula plan, the previous formula
    # plan's account amount and the "both" plan's account amount
    assert counts["families_with_off_route_amount"] == 3


# ---------------------------------------------------------------------------
# Property tests (Hypothesis) and the differential reference
# ---------------------------------------------------------------------------
def _amount(width: int) -> st.SearchStrategy[int]:
    codes = ed.amount_codes(width)
    return st.one_of(
        st.just(0),
        st.integers(1, 500_000),
        st.sampled_from([codes["top"], codes["dk"], codes["na"]]),
    )


@st.composite
def _records(draw) -> tuple[int, pd.DataFrame]:
    wave = draw(st.sampled_from(WAVES))
    new = wave in (2011, 2013)
    current_types = (0, 1, 5, 7, 8, 9) if new else (0, 1, 3, 5, 8, 9)
    previous_types = (0, 1, 5, 7, 8, 9) if new else (0, 1, 2, 3, 8, 9)
    n = draw(st.integers(1, 6))
    rows = []
    for _ in range(n):
        row: dict[str, int] = {}
        for person in ed.PERSONS:
            row[f"{person}_current_type"] = draw(
                st.sampled_from(current_types)
            )
            row[f"{person}_current_amount"] = draw(_amount(9))
            for plan in ed.PREVIOUS_PLANS:
                stem = f"{person}_prev{plan}"
                row[f"{stem}_type"] = draw(st.sampled_from(previous_types))
                for part in ("combo", "dc"):
                    row[f"{stem}_{part}_disposition"] = draw(
                        st.sampled_from(ed.DISPOSITION_CODES)
                    )
                    row[f"{stem}_{part}_amount"] = draw(_amount(8))
        rows.append(row)
    return wave, _raw(wave, rows)


def _reference(row: pd.Series, wave: int) -> dict[str, int]:
    """An independent, row-by-row statement of the section 4 rule."""

    new = wave in (2011, 2013)
    current_account = {5, 7} if new else {3, 5}
    both = 7 if new else 3
    # the codebooks route the account items to an account plan and to a
    # plan of DK type, and the "both" items to a "both" plan only
    account_route = {5, 8} if new else {2, 8}

    def value(amount: int, width: int) -> tuple[int, bool, bool, bool]:
        top, dk, na = (10**width - 3, 10**width - 2, 10**width - 1)
        unreported = amount in (dk, na)
        reported = amount > 0 and not unreported
        return (amount if reported else 0, reported, unreported, amount == top)

    out = dict.fromkeys(ed.BALANCE_COLUMNS, 0)
    for person in ("head", "wife"):
        amount = int(row[f"{person}_current_amount"])
        if int(row[f"{person}_current_type"]) in current_account:
            v, reported, unreported, top = value(amount, 9)
            out["employer_dc_current"] += v
            out["employer_dc_items"] += reported
            out["employer_dc_unreported"] += unreported
            out["employer_dc_top_coded"] += top
        elif amount != 0:
            out["employer_dc_off_route_items"] += 1
        for plan in (1, 2):
            plan_type = int(row[f"{person}_prev{plan}_type"])
            for part in ("combo", "dc"):
                disposition = int(
                    row[f"{person}_prev{plan}_{part}_disposition"]
                )
                amount = int(row[f"{person}_prev{plan}_{part}_amount"])
                on_route = (
                    plan_type == both
                    if part == "combo"
                    else plan_type in account_route
                )
                if on_route and disposition == 3:
                    v, reported, unreported, top = value(amount, 8)
                    out["employer_dc_previous"] += v
                    out["employer_dc_items"] += reported
                    out["employer_dc_unreported"] += unreported
                    out["employer_dc_top_coded"] += top
                elif on_route and disposition == 2:
                    out["employer_dc_ira_rollover_items"] += 1
                elif disposition == 3 and amount != 0:
                    out["employer_dc_off_route_items"] += 1
    out["employer_dc"] = (
        out["employer_dc_current"] + out["employer_dc_previous"]
    )
    return out


@settings(max_examples=60, deadline=None)
@given(_records())
def test_the_rule_equals_the_reference_implementation(case):
    wave, raw = case
    result = ed.employer_dc_balances(raw, wave)
    for i in range(len(raw)):
        expected = _reference(raw.iloc[i], wave)
        got = {c: int(result[c].iloc[i]) for c in ed.BALANCE_COLUMNS}
        assert got == expected, (wave, i)


@settings(max_examples=60, deadline=None)
@given(_records())
def test_balance_invariants(case):
    wave, raw = case
    result = ed.employer_dc_balances(raw, wave)
    assert (result["employer_dc_current"] >= 0).all()
    assert (result["employer_dc_previous"] >= 0).all()
    assert (
        result["employer_dc"]
        == result["employer_dc_current"] + result["employer_dc_previous"]
    ).all()
    # the recorded items are returned unchanged
    pd.testing.assert_frame_equal(result[list(raw.columns)], raw)
    # at most the positive recorded amounts: nothing is invented
    amounts = [c for c in raw.columns if c.endswith("_amount")]
    ceiling = raw[amounts].where(raw[amounts] > 0, 0).sum(axis=1)
    assert (result["employer_dc"] <= ceiling).all()


@settings(max_examples=40, deadline=None)
@given(_records(), st.integers(1, 400_000))
def test_excluded_items_never_move_the_balance(case, replacement):
    """Changing a rolled-over account, an amount under a plan type with no
    account, or any amount set to DK/refused leaves the balance alone."""

    wave, raw = case
    before = ed.employer_dc_balances(raw, wave)["employer_dc"]
    new = wave in (2011, 2013)
    both, account = (7, 5) if new else (3, 2)
    changed = raw.copy()
    for person in ed.PERSONS:
        for plan in ed.PREVIOUS_PLANS:
            stem = f"{person}_prev{plan}"
            plan_type = changed[f"{stem}_type"]
            for part in ("combo", "dc"):
                route = (
                    (plan_type == both)
                    if part == "combo"
                    else plan_type.isin([account, 8])
                )
                disposition = changed[f"{stem}_{part}_disposition"]
                excluded = (disposition == 2) | ~route | (disposition != 3)
                changed.loc[excluded, f"{stem}_{part}_amount"] = replacement
    after = ed.employer_dc_balances(changed, wave)["employer_dc"]
    current = ed.employer_dc_balances(raw, wave)["employer_dc_current"]
    changed_current = ed.employer_dc_balances(changed, wave)[
        "employer_dc_current"
    ]
    assert (current == changed_current).all()
    assert (after == before).all()
    dk = ed.amount_codes(8)["dk"]
    unreported = raw.copy()
    for person in ed.PERSONS:
        for plan in ed.PREVIOUS_PLANS:
            for part in ("combo", "dc"):
                unreported[f"{person}_prev{plan}_{part}_amount"] = dk
        unreported[f"{person}_current_amount"] = ed.amount_codes(9)["na"]
    assert (
        ed.employer_dc_balances(unreported, wave)["employer_dc"] == 0
    ).all()


@settings(max_examples=40, deadline=None)
@given(_records(), st.randoms(use_true_random=False))
def test_head_and_wife_are_interchangeable_and_the_rule_is_row_wise(case, rng):
    wave, raw = case
    result = ed.employer_dc_balances(raw, wave)
    swapped = raw.rename(
        columns={
            c: ("wife" + c[4:] if c.startswith("head") else "head" + c[4:])
            for c in raw.columns
            if c.startswith(("head_", "wife_"))
        }
    )[list(raw.columns)]
    swapped_result = ed.employer_dc_balances(swapped, wave)
    for column in ed.BALANCE_COLUMNS:
        assert (result[column] == swapped_result[column]).all(), column
    order = list(range(len(raw)))
    rng.shuffle(order)
    shuffled = ed.employer_dc_balances(
        raw.iloc[order].reset_index(drop=True), wave
    )
    for column in ed.BALANCE_COLUMNS:
        np.testing.assert_array_equal(
            shuffled[column].to_numpy(), result[column].to_numpy()[order]
        )


@settings(max_examples=40, deadline=None)
@given(
    st.sampled_from(WAVES),
    st.sampled_from((0, 1, 2, 3, 5, 7, 8, 9)),
    st.integers(1, 400_000),
    st.integers(1, 400_000),
)
def test_one_plan_never_contributes_twice(wave, plan_type, combo, dc):
    """Whatever the plan-type code, at most one of a plan's two account
    routes is open, so a plan left to accumulate adds at most one of its
    two recorded amounts (the double-count guard)."""

    new = wave in (2011, 2013)
    allowed = (0, 1, 5, 7, 8, 9) if new else (0, 1, 2, 3, 8, 9)
    if plan_type not in allowed:
        return
    row = _one(
        wave,
        head_prev1_type=plan_type,
        head_prev1_combo_disposition=3,
        head_prev1_combo_amount=combo,
        head_prev1_dc_disposition=3,
        head_prev1_dc_amount=dc,
    )
    assert row["employer_dc"] in (0, combo, dc)
    assert row["employer_dc_items"] <= 1
    assert row["employer_dc_items"] + row["employer_dc_off_route_items"] == 2


@settings(max_examples=40, deadline=None)
@given(_records(), st.integers(1, 1_000))
def test_raising_a_counted_amount_raises_the_balance_by_as_much(case, step):
    """Monotone and additive: adding ``step`` dollars to one counted,
    reported amount adds exactly ``step`` to that family's balance and
    changes no other family's."""

    wave, raw = case
    before = ed.employer_dc_balances(raw, wave)
    counted = []
    for person in ed.PERSONS:
        for plan in ed.PREVIOUS_PLANS:
            for part in ("combo", "dc"):
                column = f"{person}_prev{plan}_{part}_amount"
                counted.append(column)
    for i in range(len(raw)):
        for column in counted:
            one = raw.iloc[[i]].reset_index(drop=True)
            base = ed.employer_dc_balances(one, wave)
            amount = int(one[column].iloc[0])
            if not 0 < amount < 400_000:
                continue
            bumped = one.copy()
            bumped[column] = amount + step
            after = ed.employer_dc_balances(bumped, wave)
            delta = int(after["employer_dc"].iloc[0]) - int(
                base["employer_dc"].iloc[0]
            )
            assert delta in (0, step), (column, delta)
            assert int(base["employer_dc"].iloc[0]) == int(
                before["employer_dc"].iloc[i]
            )
