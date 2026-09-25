"""M3's year-before-last labor income reader on INVENTED fixtures.

No PSID file is read: the fixtures are invented setup and data files in
the family files' shapes.  The staged files' labels are checked by
``test_track_m_psid_labels.py``.

Invariants (property tests below):

* every item gets exactly one status of :data:`STATUSES`;
* an observed status gives a finite, nonnegative annual amount and an
  unobserved one NaN;
* not employed is zero whatever the amount; a loss is zero; DK or NA is
  unobserved; a positive amount is the amount times its time unit's
  periods per year, so annualizing is linear in the amount and never
  lowers it;
* :func:`next_wave_histories` keeps exactly the observed items.
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.data import prior_year_labor_income as pyl

_WAVES = tuple(pyl._VARS)


def test_the_tables_cover_every_odd_year_2001_2021():
    assert pyl.ODD_INCOME_YEARS == tuple(range(2001, 2022, 2))
    assert _WAVES == tuple(year + 2 for year in pyl.ODD_INCOME_YEARS)
    for wave in _WAVES:
        table = pyl.prior_year_variables(wave)
        year = wave - 2
        assert table["interview"][1] == f"{wave} FAMILY INTERVIEW (ID) NUMBER"
        for role in pyl.ROLES:
            labels = {key: label for key, (_, label) in table[role].items()}
            assert labels["employed"].startswith(f"WTR EMPLOYED IN {year}")
            assert f"LABOR INCOME {year}" in labels["amount"]
            assert f"PER FOR LABOR INCOME {year}" in labels["per"]
            assert labels["acc"].startswith(f"ACCURACY OF LABOR INCOME {year}")
    with pytest.raises(ValueError, match="no year-before-last"):
        pyl.prior_year_variables(2001)


def test_the_conventions_worked_by_hand():
    assert pyl.annualize(5, 40_000, 6, wave=2023) == ("not_employed", 0.0)
    status, value = pyl.annualize(9, 0, 0, wave=2023)
    assert status == "employed_unknown" and math.isnan(value)
    status, value = pyl.annualize(1, 9_999_999.0, 9, wave=2023)
    assert status == "amount_unknown" and math.isnan(value)
    status, value = pyl.annualize(1, 99_999_999, 9, wave=2003)
    assert status == "amount_unknown" and math.isnan(value)
    status, value = pyl.annualize(1, 99_999_998, 8, wave=2003)
    assert status == "amount_unknown" and math.isnan(value)
    assert pyl.annualize(1, -999_999.0, 0, wave=2023) == ("loss", 0.0)
    assert pyl.annualize(1, -9_999_999, 0, wave=2005) == ("loss", 0.0)
    assert pyl.annualize(1, -350.0, 6, wave=2023) == ("loss", 0.0)
    assert pyl.annualize(1, 0, 0, wave=2023) == ("zero_broke_even", 0.0)
    assert pyl.annualize(1, 30_000, 6, wave=2023) == (
        "annual_amount",
        30_000.0,
    )
    assert pyl.annualize(1, 2_500, 5, wave=2023) == (
        "annual_amount",
        30_000.0,
    )
    assert pyl.annualize(1, 15, 1, wave=2023) == ("annual_amount", 31_200.0)
    status, value = pyl.annualize(1, 500, 7, wave=2023)
    assert status == "time_unit_unknown" and math.isnan(value)
    status, value = pyl.annualize(1, 500, 0, wave=2023)
    assert status == "time_unit_unknown" and math.isnan(value)


def test_undocumented_codes_are_refused():
    with pytest.raises(ValueError, match="whether employed"):
        pyl.annualize(0, 100, 6, wave=2023)
    with pytest.raises(ValueError, match="time unit"):
        pyl.annualize(1, 100, 10, wave=2023)


_codes = st.tuples(
    st.sampled_from([1, 5, 9]),
    st.one_of(
        st.floats(min_value=-1e6, max_value=1e7, allow_nan=False),
        st.sampled_from(
            [9_999_999.0, -999_999.0, 99_999_999, 99_999_998, -9_999_999, 0]
        ),
    ),
    st.sampled_from([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]),
    st.sampled_from(_WAVES),
)


@settings(max_examples=400, deadline=None)
@given(_codes)
def test_every_item_gets_one_status_and_a_consistent_amount(item):
    employed, amount, per, wave = item
    status, value = pyl.annualize(employed, amount, per, wave=wave)
    assert status in pyl.STATUSES
    if status in pyl.observed_statuses():
        assert math.isfinite(value) and value >= 0
    else:
        assert math.isnan(value)
    if employed == 5:
        assert (status, value) == ("not_employed", 0.0)
    if employed == 9:
        assert status == "employed_unknown"
    if status == "annual_amount":
        factor = pyl.TIME_UNIT_FACTORS[per]
        assert value == pytest.approx(float(amount) * factor)
        assert value >= float(amount)


@settings(max_examples=200, deadline=None)
@given(
    st.floats(min_value=1, max_value=1e6),
    st.floats(min_value=1.01, max_value=5),
    st.sampled_from(sorted(pyl.TIME_UNIT_FACTORS)),
)
def test_annualizing_is_linear_in_the_amount(amount, scale, per):
    _, low = pyl.annualize(1, amount, per, wave=2023)
    _, high = pyl.annualize(1, amount * scale, per, wave=2023)
    assert high == pytest.approx(low * scale)
    assert high > low


def _frame(rows):
    return pd.DataFrame(
        rows,
        columns=["person_id", "income_year", "status", "annual"],
    )


def test_next_wave_histories_keep_the_observed_items_only():
    frame = _frame(
        [
            (1, 2001, "annual_amount", 20_000.0),
            (1, 2003, "amount_unknown", float("nan")),
            (1, 2005, "not_employed", 0.0),
            (2, 2001, "employed_unknown", float("nan")),
            (2, 2003, "loss", 0.0),
            (3, 2021, "time_unit_unknown", float("nan")),
        ]
    )
    assert pyl.next_wave_histories(frame) == {
        1: {2001: 20_000.0, 2005: 0.0},
        2: {2003: 0.0},
    }


@settings(max_examples=150, deadline=None)
@given(
    st.lists(
        st.tuples(
            st.integers(min_value=1, max_value=20),
            st.sampled_from(pyl.ODD_INCOME_YEARS),
            st.sampled_from(pyl.STATUSES),
        ),
        max_size=40,
        unique_by=lambda row: (row[0], row[1]),
    )
)
def test_next_wave_histories_are_exactly_the_observed_items(rows):
    observed = set(pyl.observed_statuses())
    frame = _frame(
        [
            (pid, year, status, 1.0 if status in observed else float("nan"))
            for pid, year, status in rows
        ]
    )
    histories = pyl.next_wave_histories(frame)
    kept = {(pid, year) for pid, years in histories.items() for year in years}
    assert kept == {
        (pid, year) for pid, year, status in rows if status in observed
    }


# ---------------------------------------------------------------------------
# The reader on INVENTED family files
# ---------------------------------------------------------------------------
def _write(root: Path, wave: int, rows: list[dict]) -> None:
    table = pyl.prior_year_variables(wave)
    columns = [("interview", table["interview"])]
    for role in pyl.ROLES:
        for concept, entry in table[role].items():
            columns.append((f"{role}_{concept}", entry))
    base = root / "family" / str(wave)
    base.mkdir(parents=True, exist_ok=True)
    width = 12
    layout = "\n".join(
        f"      {var}  {1 + i * width} - {(i + 1) * width}"
        for i, (_, (var, _)) in enumerate(columns)
    )
    labels = "\n".join(
        f'      {var}    "{label}"' for _, (var, label) in columns
    )
    (base / f"FAM{wave}ER.sps").write_text(
        "DATA LIST FILE = PSID FIXED /\n"
        + layout
        + "\n.\n\nVARIABLE LABELS\n"
        + labels
        + "\n.\n",
        encoding="utf-8",
    )
    lines = [
        "".join(str(row[key]).rjust(width) for key, _ in columns)
        for row in rows
    ]
    (base / f"FAM{wave}ER.txt").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def _row(interview, rp, sp):
    out = {"interview": interview}
    for role, values in (("reference_person", rp), ("spouse", sp)):
        for key, value in zip(
            ("employed", "amount", "per", "acc"), values, strict=True
        ):
            out[f"{role}_{key}"] = value
    return out


def test_the_reader_attaches_each_role_by_interview(tmp_path):
    _write(
        tmp_path,
        2023,
        [
            _row(1, (1, "52000.00", 6, 0), (1, "1500.00", 5, 1)),
            _row(2, (5, ".00", 0, 0), (9, ".00", 0, 0)),
            _row(3, (1, "9999999.00", 9, 0), (1, "-999999.00", 0, 0)),
        ],
    )
    members = pd.DataFrame(
        [
            (11, 2023, 1, 10, 1),
            (12, 2023, 2, 20, 1),
            (21, 2023, 1, 10, 2),
            (22, 2023, 2, 22, 2),
            (23, 2023, 3, 30, 2),
            (31, 2023, 1, 10, 3),
            (32, 2023, 2, 20, 3),
        ],
        columns=["person_id", "wave", "sequence", "relationship", "interview"],
    )
    out = pyl.read_prior_year_labor_income(
        waves=(2023,), data_dir=tmp_path, members=members
    ).set_index("person_id")
    assert sorted(out.index) == [11, 12, 21, 22, 31, 32]
    assert set(out["income_year"]) == {2021}
    assert out.loc[11, "status"] == "annual_amount"
    assert out.loc[11, "annual"] == 52_000.0
    assert out.loc[12, "annual"] == 18_000.0
    assert out.loc[12, "role"] == "spouse"
    assert out.loc[21, "status"] == "not_employed"
    assert out.loc[22, "status"] == "employed_unknown"
    assert out.loc[31, "status"] == "amount_unknown"
    assert out.loc[32, "status"] == "loss"
    assert pyl.next_wave_histories(out.reset_index()) == {
        11: {2021: 52_000.0},
        12: {2021: 18_000.0},
        21: {2021: 0.0},
        32: {2021: 0.0},
    }


def test_a_label_the_table_does_not_name_is_refused(tmp_path):
    _write(tmp_path, 2021, [_row(1, (5, ".00", 0, 0), (5, ".00", 0, 0))])
    sps = tmp_path / "family" / "2021" / "FAM2021ER.sps"
    sps.write_text(
        sps.read_text(encoding="utf-8").replace(
            "R2 LABOR INCOME 2019 (RP)", "R2 LABOR INCOME 2018 (RP)"
        ),
        encoding="utf-8",
    )
    members = pd.DataFrame(
        [(1, 2021, 1, 10, 1)],
        columns=["person_id", "wave", "sequence", "relationship", "interview"],
    )
    with pytest.raises(ValueError, match="does not match"):
        pyl.read_prior_year_labor_income(
            waves=(2021,), data_dir=tmp_path, members=members
        )


def test_the_concept_delta_names_what_differs():
    delta = pyl.CONCEPT_DELTA
    for word in ("farm", "self-employment", "unassigned", "time unit"):
        assert word in delta
