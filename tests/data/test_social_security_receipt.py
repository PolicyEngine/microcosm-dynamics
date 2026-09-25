"""M3's Social Security receipt readers on INVENTED fixtures (no PSID).

The adjudicated tables, the strict code decoding, and the family-level
readings (a family reporting none identifies every member's non-receipt;
a year-before-last "yes" identifies a one-member family's receipt;
nothing else identifies a person).  The labels of the staged files are
checked by ``test_track_m_psid_labels.py``; these fixtures are invented
setup and data files in the PSID's shapes.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.data import social_security_receipt as ssr


# ---------------------------------------------------------------------------
# The adjudicated tables
# ---------------------------------------------------------------------------
def test_every_individual_wave_has_an_amount_accuracy_and_types():
    assert ssr.INDIVIDUAL_WAVES == (
        *range(1984, 1993),
        *range(2005, 2024, 2),
    )
    for wave in ssr.INDIVIDUAL_WAVES:
        table = ssr.individual_variables(wave)
        yy = f"{wave % 100:02d}"
        assert table["amount"][1].endswith(f"AMT SOC SEC RCD {yy}")
        assert table["acc"][1].endswith(f"ACC SOC SEC AMT {yy}")
        if wave <= 2009:
            assert set(table) == {"type_code", "amount", "acc"}
        else:
            assert set(table) == {
                "amount",
                "acc",
                *(f"flag_{name}" for name in ssr.SS_TYPES),
            }
    with pytest.raises(ValueError, match="no person-level"):
        ssr.individual_variables(1995)


def test_the_family_tables_cover_the_waves_without_person_items():
    assert ssr.YEAR_BEFORE_LAST_WAVES == (2005, 2007, 2009, 2011, 2013, 2015)
    assert ssr.YEAR_BEFORE_LAST_TYPED_WAVES == (2005, 2007)
    assert ssr.FAMILY_TOTAL_WAVES == (1994, 1995, 1996, 1997, 1999, 2001, 2003)
    for wave in ssr.YEAR_BEFORE_LAST_WAVES:
        table = ssr.year_before_last_variables(wave)
        assert table["received"][1] == (
            "R20 WTR RECD SOC SECURITY YR BEFORE LAST"
        )
        assert table["interview"][1].startswith(f"{wave} FAMILY INTERVIEW")
        typed = wave in ssr.YEAR_BEFORE_LAST_TYPED_WAVES
        assert ("mention_1" in table) is typed, wave
        assert ("amount" in table) is typed, wave
    for wave in ssr.FAMILY_TOTAL_WAVES:
        assert set(ssr.family_total_variables(wave)) == {"interview", "total"}
    # The 2017-2023 files carry no year-before-last Social Security item.
    for wave in (2017, 2019, 2021, 2023):
        with pytest.raises(ValueError):
            ssr.year_before_last_variables(wave)
    with pytest.raises(ValueError):
        ssr.family_total_variables(2005)


def test_a_whether_only_wave_identifies_receipt_of_an_unknown_type(
    tmp_path,
):
    """2009-2015 keep R20 alone: a one-member "yes" is receipt of an
    unknown type; a family "no" is every member's non-receipt; DK and NA
    identify nobody."""

    table = ssr.year_before_last_variables(2011)
    _write_family(
        tmp_path,
        2011,
        table,
        {"received": 1},
        [
            {"interview": 1, "received": 1},
            {"interview": 2, "received": 5},
            {"interview": 3, "received": 1},
            {"interview": 4, "received": 9},
        ],
    )
    families = ssr.read_year_before_last(2011, data_dir=tmp_path)
    assert list(families["income_year"].unique()) == [2009]
    for name in ssr.SS_TYPES:
        assert families[f"type_{name}"].isna().all(), name
    assert families["amount"].isna().all()
    assert families["per"].isna().all()
    members = _members(
        2011, [(1, 1, 10), (2, 2, 10), (3, 2, 20), (4, 3, 10), (5, 3, 20)]
    )
    members = pd.concat([members, _members(2011, [(6, 4, 10)])])
    rows = ssr.family_level_person_rows(
        families, members, kind="year_before_last"
    ).set_index("person_id")
    assert sorted(rows.index) == [1, 2, 3]
    assert bool(rows.loc[1, "receipt"])
    assert not rows.loc[[2, 3], "receipt"].any()
    for name in ssr.SS_TYPES:
        assert rows[f"type_{name}"].isna().all(), name
    with pytest.raises(ValueError, match="undocumented"):
        _write_family(
            tmp_path,
            2013,
            ssr.year_before_last_variables(2013),
            {"received": 1},
            [{"interview": 1, "received": 0}],
        )
        ssr.read_year_before_last(2013, data_dir=tmp_path)


def test_the_2023_amount_reading_is_recorded():
    reading = ssr.AMOUNT_2023_READING
    assert reading["variable"] == ssr.AMOUNT_2023[0] == "ER35219"
    assert reading["top_code"] == ssr.AMOUNT_TOP_CODE == 99_999
    assert reading["monthly_conversion"] == "annual_total_divided_by_12"
    assert reading["months_of_receipt_released"] is False
    assert reading["medicare_premium"] == "gross"


# ---------------------------------------------------------------------------
# Strict decoding
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("code", "expected", "combination"),
    [
        (1, "disability", False),
        (2, "retirement", False),
        (3, "survivor", False),
        (5, "dependent_of_disabled", False),
        (6, "dependent_of_retired", False),
        (7, "other", False),
        (4, None, True),
        (9, None, False),
        (0, None, False),
    ],
)
def test_a_single_type_code_sets_one_type(code, expected, combination):
    columns = ssr._types_from_code(pd.Series([code]), ssr.TYPE_CODES_1988)
    assert bool(columns["type_combination"].iloc[0]) is combination
    for name in ssr.SS_TYPES:
        value = columns[f"type_{name}"].iloc[0]
        if expected is None:
            assert value is pd.NA, name
        else:
            assert bool(value) is (name == expected), name


def test_the_1984_scheme_has_no_dependent_codes():
    assert set(ssr.TYPE_CODES_1984) == {1, 2, 3, 4, 7}
    columns = ssr._types_from_code(pd.Series([3]), ssr.TYPE_CODES_1984)
    assert bool(columns["type_survivor"].iloc[0])
    assert not bool(columns["type_dependent_of_retired"].iloc[0])


def test_flags_and_codes_decode_strictly():
    flags = ssr._flag(pd.Series([1, 5, 0, 8, 9]), "invented")
    assert list(flags.astype(object)) == [True, False, pd.NA, pd.NA, pd.NA]
    with pytest.raises(ValueError, match="undocumented"):
        ssr._flag(pd.Series([1, 3]), "invented")
    with pytest.raises(ValueError, match="undocumented"):
        ssr._decode(pd.Series([0, 2]), ssr.ACCURACY_CODES_2005, "acc")
    with pytest.raises(ValueError, match="negative"):
        ssr._amount(pd.Series([10, -1]), "amount")


# ---------------------------------------------------------------------------
# INVENTED family-file fixtures in the PSID's setup and data shapes
# ---------------------------------------------------------------------------
def _write_family(
    root: Path,
    wave: int,
    table: dict[str, tuple[str, str]],
    widths: dict[str, int],
    rows: list[dict[str, int]],
) -> None:
    base = root / "family" / str(wave)
    base.mkdir(parents=True, exist_ok=True)
    layout, start = [], 1
    for concept, (var, _) in table.items():
        width = widths.get(concept, 7)
        layout.append(f"      {var}  {start} - {start + width - 1}")
        start += width
    labels = "\n".join(
        f'      {var}    "{label}"' for var, label in table.values()
    )
    (base / f"FAM{wave}ER.sps").write_text(
        "DATA LIST FILE = PSID FIXED /\n"
        + "\n".join(layout)
        + "\n.\n\nVARIABLE LABELS\n"
        + labels
        + "\n.\n",
        encoding="utf-8",
    )
    lines = []
    for row in rows:
        line = ""
        for concept in table:
            width = widths.get(concept, 7)
            line += str(row[concept]).rjust(width)
        lines.append(line)
    (base / f"FAM{wave}ER.txt").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def _members(wave: int, rows: list[tuple[int, int, int]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "person_id": pid,
                "wave": wave,
                "sequence": 1,
                "relationship": rel,
                "interview": interview,
            }
            for pid, interview, rel in rows
        ]
    )


def test_year_before_last_items_are_family_level(tmp_path):
    table = ssr.year_before_last_variables(2005)
    _write_family(
        tmp_path,
        2005,
        table,
        {"received": 1, "mention_1": 1, "mention_2": 1, "per": 1},
        [
            # family 1: one member, received, retirement then survivor
            {
                "interview": 1,
                "received": 1,
                "mention_1": 2,
                "mention_2": 3,
                "amount": 900,
                "per": 5,
            },
            # family 2: two members, received (identifies nobody)
            {
                "interview": 2,
                "received": 1,
                "mention_1": 1,
                "mention_2": 0,
                "amount": 800,
                "per": 5,
            },
            # family 3: three members, none received
            {
                "interview": 3,
                "received": 5,
                "mention_1": 0,
                "mention_2": 0,
                "amount": 0,
                "per": 0,
            },
            # family 4: one member, DK
            {
                "interview": 4,
                "received": 8,
                "mention_1": 0,
                "mention_2": 0,
                "amount": 0,
                "per": 0,
            },
        ],
    )
    families = ssr.read_year_before_last(2005, data_dir=tmp_path)
    assert list(families["income_year"].unique()) == [2003]
    first = families.iloc[0]
    assert bool(first["type_retirement"]) and bool(first["type_survivor"])
    assert not bool(first["type_disability"])
    assert families.iloc[2]["type_retirement"] is pd.NA
    members = _members(
        2005,
        [
            (101, 1, 10),
            (201, 2, 10),
            (202, 2, 20),
            (301, 3, 10),
            (302, 3, 20),
            (303, 3, 30),
            (401, 4, 10),
        ],
    )
    rows = ssr.family_level_person_rows(
        families, members, kind="year_before_last"
    ).set_index("person_id")
    assert sorted(rows.index) == [101, 301, 302, 303]
    assert bool(rows.loc[101, "receipt"])
    assert bool(rows.loc[101, "type_retirement"])
    for pid in (301, 302, 303):
        assert not bool(rows.loc[pid, "receipt"])
        assert rows.loc[pid, "type_retirement"] is pd.NA
    assert set(rows["source"]) == {"year_before_last"}


def test_undocumented_family_codes_are_refused(tmp_path):
    table = ssr.year_before_last_variables(2007)
    _write_family(
        tmp_path,
        2007,
        table,
        {"received": 1, "mention_1": 1, "mention_2": 1, "per": 1},
        [
            {
                "interview": 1,
                "received": 3,
                "mention_1": 0,
                "mention_2": 0,
                "amount": 0,
                "per": 0,
            }
        ],
    )
    with pytest.raises(ValueError, match="undocumented"):
        ssr.read_year_before_last(2007, data_dir=tmp_path)


def test_family_totals_mark_non_amounts_and_the_head_only_1996(tmp_path):
    for wave, not_amount in ((1994, 999_999), (1996, 0)):
        table = ssr.family_total_variables(wave)
        _write_family(
            tmp_path,
            wave,
            table,
            {},
            [
                {"interview": 1, "total": 0},
                {"interview": 2, "total": 5_000},
                {"interview": 3, "total": not_amount},
            ],
        )
    totals_1994 = ssr.read_family_totals(1994, data_dir=tmp_path)
    assert totals_1994["total"].isna().tolist() == [False, False, True]
    assert not totals_1994["head_only"].any()
    members = _members(1994, [(1, 1, 10), (2, 1, 20), (3, 2, 10), (4, 3, 10)])
    rows = ssr.family_level_person_rows(totals_1994, members, kind="total")
    # the zero-total family identifies both members; the Latino-sample
    # code and a positive total identify nobody
    assert sorted(rows["person_id"]) == [1, 2]
    assert not rows["receipt"].any()
    assert set(rows["income_year"]) == {1993}
    totals_1996 = ssr.read_family_totals(1996, data_dir=tmp_path)
    assert totals_1996["head_only"].all()
    members = _members(1996, [(1, 1, 10), (2, 1, 20), (3, 3, 10)])
    rows = ssr.family_level_person_rows(totals_1996, members, kind="total")
    # 1996's total is the head's (codebook text): the head only
    assert sorted(rows["person_id"]) == [1, 3]


_family = st.fixed_dictionaries(
    {
        "size": st.integers(min_value=1, max_value=4),
        "received": st.sampled_from([1, 5, 8, 9]),
        "mention": st.sampled_from([0, 1, 2, 3, 5, 6, 7, 8]),
    }
)


@settings(max_examples=150, deadline=None)
@given(st.lists(_family, min_size=1, max_size=12))
def test_family_level_rows_identify_only_what_the_family_reports(families):
    """For any set of families: a receipt row comes only from a one-member
    family reporting yes; every member of a family reporting no appears
    once, without receipt; DK and NA identify nobody."""

    family_rows, member_rows = [], []
    pid = 0
    for interview, family in enumerate(families, start=1):
        mention = family["mention"] if family["received"] == 1 else 0
        row = {
            "interview": interview,
            "wave": 2005,
            "income_year": 2003,
            "received": family["received"],
        }
        for code, name in ssr._MENTION_TYPES.items():
            value = pd.NA
            if family["received"] == 1 and mention in ssr._MENTION_TYPES:
                value = mention == code
            row[f"type_{name}"] = value
        family_rows.append(row)
        for position in range(family["size"]):
            pid += 1
            member_rows.append((pid, interview, 10 if position == 0 else 30))
    frame = pd.DataFrame(family_rows)
    for name in ssr.SS_TYPES:
        frame[f"type_{name}"] = frame[f"type_{name}"].astype("boolean")
    out = ssr.family_level_person_rows(
        frame, _members(2005, member_rows), kind="year_before_last"
    )
    assert not out["person_id"].duplicated().any()
    members = pd.DataFrame(
        member_rows, columns=["person_id", "interview", "relationship"]
    )
    merged = out.merge(members, on="person_id")
    by_family = {row["interview"]: row for row in family_rows}
    for row in merged.itertuples(index=False):
        family = families[row.interview - 1]
        if row.receipt:
            assert family["size"] == 1 and family["received"] == 1
        else:
            assert family["received"] == 5
        assert by_family[row.interview]["received"] in (1, 5)
    expected = sum(
        family["size"] for family in families if family["received"] == 5
    ) + sum(
        1
        for family in families
        if family["size"] == 1 and family["received"] == 1
    )
    assert len(out) == expected
