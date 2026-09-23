"""Unit tests for the label-verified Social Security income readers.

Every fixture here is INVENTED: miniature fixed-width PSID products written
into ``tmp_path`` with the same DATA LIST / VARIABLE LABELS layout and SAS
``VALUE`` blocks the staged release uses, so the tests exercise the real
label-verification, value-code verification and colspec paths without any
PSID data. No value below is a PSID observation.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from populace_dynamics.data import social_security_income as ssi
from tests.data.psid_fixtures import write_product

# --------------------------------------------------------------------------
# Invented fixture builders
# --------------------------------------------------------------------------
_FAMILY_2011 = {
    "interview": ("ER47302", "2011 FAMILY INTERVIEW (ID) NUMBER"),
    "fu_ss_prior_year": (
        "ER52088",
        "R20 WTR RECD SOC SECURITY YR BEFORE LAST",
    ),
    "head_ss": ("ER52337", "HEAD SOCIAL SECURITY INCOME-2010"),
    "head_ss_acc": ("ER52338", "ACCURACY OF HEAD SOCIAL SECURITY-2010"),
    "spouse_ss": ("ER52339", "WIFE SOCIAL SECURITY INCOME-2010"),
    "spouse_ss_acc": ("ER52340", "ACCURACY OF WIFE SOCIAL SECURITY-2010"),
    "ofum_ss": ("ER52341", "OFUM SOCIAL SECURITY INCOME-2010"),
    "ofum_ss_acc": ("ER52342", "ACCURACY OF OFUM SOCIAL SECURITY-2010"),
}

_WIDTHS = {
    "interview": 5,
    "fu_ss_prior_year": 1,
    "head_ss": 6,
    "head_ss_acc": 1,
    "spouse_ss": 6,
    "spouse_ss_acc": 1,
    "ofum_ss": 6,
    "ofum_ss_acc": 1,
}


def _write_family_2011(
    root: Path,
    values: dict[str, list[int]],
    *,
    labels: dict[str, str] | None = None,
    extra: list[tuple[str, int, str, list[int]]] = (),
) -> None:
    labels = labels or {}
    fields = [
        (
            var,
            _WIDTHS[concept],
            labels.get(concept, label),
            values[concept],
        )
        for concept, (var, label) in _FAMILY_2011.items()
    ]
    write_product(
        root / "family" / "2011",
        "FAM2011ER.sps",
        "FAM2011ER.txt",
        [*fields, *extra],
    )


def _family_values(**overrides: list[int]) -> dict[str, list[int]]:
    values = {
        "interview": [101, 102, 103],
        "fu_ss_prior_year": [1, 5, 9],
        "head_ss": [14000, 0, 9000],
        "head_ss_acc": [0, 0, 5],
        "spouse_ss": [7000, 0, 0],
        "spouse_ss_acc": [1, 0, 0],
        "ofum_ss": [0, 0, 6000],
        "ofum_ss_acc": [0, 0, 0],
    }
    values.update(overrides)
    return values


_FLAG_VARS_2011 = (
    ("ER34137", "G33A WTR SOC SEC TYPE DISABILITY 11", "disability"),
    ("ER34138", "G33A WTR SOC SEC TYPE RETIREMENT 11", "retirement"),
    ("ER34139", "G33A WTR SOC SEC TYPE SURVIVOR 11", "survivor''s benefit"),
    (
        "ER34140",
        "G33A WTR SOC SEC TYPE DEP OF DISABLED 11",
        "dependent of disabled recipient",
    ),
    (
        "ER34141",
        "G33A WTR SOC SEC TYPE DEP OF RETIRED 11",
        "dependent of retired recipient",
    ),
    ("ER34142", "G33A WTR SOC SEC TYPE OTHER 11", "other"),
)

_TYPE_CODE_2009_LABELS = {
    1: "Disability",
    2: "Retirement",
    3: "Survivor benefits; dependent of deceased recipient",
    4: "Any combination of codes 1-3 and 5-7",
    5: "Dependent of disabled recipient",
    6: "Dependent of retired recipient",
    7: "Other",
    8: "DK",
    9: "NA",
}


def _formats_text(*, relabel_2011_flag: str | None = None) -> str:
    """An invented SAS formats file in the staged release's layout."""

    lines = ["PROC FORMAT;"]
    for var, _, kind in _FLAG_VARS_2011:
        yes = f"Social security type was {kind}"
        if relabel_2011_flag == var:
            yes = "Social security type was something else"
        lines += [
            f"   VALUE {var}F",
            f"         1 = '{yes}'",
            f"         5 = 'Social security type was not {kind}'",
            "         8 = 'DK'",
            "         9 = 'NA; refused'",
            "         0 = 'Inap.:  no Social Security income; from Latino'",
            "             ' sample (ER30001=7001-9308)'",
            "   ;",
        ]
    lines.append("   VALUE ER34030F")
    for code, label in _TYPE_CODE_2009_LABELS.items():
        lines.append(f"         {code} = '{label}'")
    lines += ["         0 = 'Inap.: no Social Security income'", "   ;"]
    lines += ["RUN;", "", "FORMAT"]
    for var, _, _ in _FLAG_VARS_2011:
        lines.append(f"    {var}    {var}F.")
    lines.append("    ER34030    ER34030F.")
    return "\n".join(lines) + "\n"


def _write_individual(
    root: Path,
    *,
    relabel_2011_flag: str | None = None,
    amount_label: str = "G34 AMT SOC SEC RCD 11",
) -> None:
    """Five invented persons across 2009 and 2011 in two families each.

    2011: family 101 has head 1001 and wife 1002; family 103 has head 3001
    and an OFUM 3002; person 4001 is in an institution (sequence 51).
    2009: family 201 has head 1001 and OFUM 1002.
    """

    fields = [
        ("ER30001", 4, "1968 INTERVIEW NUMBER", [1, 1, 3, 3, 4]),
        ("ER30002", 3, "PERSON NUMBER 68", [1, 2, 1, 2, 1]),
        ("ER34001", 5, "2009 INTERVIEW NUMBER", [201, 201, 0, 0, 0]),
        ("ER34002", 2, "SEQUENCE NUMBER 09", [1, 2, 0, 0, 0]),
        ("ER34003", 2, "RELATION TO HEAD 09", [10, 30, 0, 0, 0]),
        ("ER34004", 3, "AGE OF INDIVIDUAL 09", [66, 40, 0, 0, 0]),
        (
            "ER34046",
            5,
            "CORE/IMM INDIVIDUAL CROSS-SECTION WT 09",
            [1000, 900, 0, 0, 0],
        ),
        ("ER34030", 1, "G33 TYPE SOC SEC RCD 09", [2, 3, 0, 0, 0]),
        ("ER34031", 5, "G34 AMT SOC SEC RCD 09", [12000, 3000, 0, 0, 0]),
        ("ER34032", 1, "G34 ACC SOC SEC AMT 09", [0, 5, 0, 0, 0]),
        ("ER34101", 5, "2011 INTERVIEW NUMBER", [101, 101, 103, 103, 104]),
        ("ER34102", 2, "SEQUENCE NUMBER 11", [1, 2, 1, 3, 51]),
        ("ER34103", 2, "RELATION TO HEAD 11", [10, 20, 10, 60, 10]),
        ("ER34104", 3, "AGE OF INDIVIDUAL 11", [68, 64, 70, 90, 80]),
        (
            "ER34155",
            5,
            "CORE/IMM INDIVIDUAL CROSS-SECTION WT 11",
            [1100, 1000, 800, 700, 600],
        ),
    ]
    flags = {
        "ER34137": [5, 5, 5, 5, 0],
        "ER34138": [1, 5, 1, 5, 0],
        "ER34139": [5, 1, 5, 1, 0],
        "ER34140": [5, 5, 5, 5, 0],
        "ER34141": [5, 5, 5, 5, 0],
        "ER34142": [5, 8, 5, 1, 0],
    }
    for var, label, _ in _FLAG_VARS_2011:
        fields.append((var, 1, label, flags[var]))
    fields += [
        ("ER34143", 5, amount_label, [14000, 7000, 9000, 5000, 0]),
        ("ER34144", 1, "G34 ACC SOC SEC AMT 11", [0, 1, 5, 0, 0]),
    ]
    write_product(root / "ind2023er", "IND2023ER.sps", "IND2023ER.txt", fields)
    (root / "ind2023er" / "IND2023ER_formats.sas").write_text(
        _formats_text(relabel_2011_flag=relabel_2011_flag)
    )


# --------------------------------------------------------------------------
# Family reader
# --------------------------------------------------------------------------
def test_family_reader_decodes_invented_wave(tmp_path):
    _write_family_2011(tmp_path, _family_values())
    frame = ssi.read_family_social_security(2011, data_dir=tmp_path)
    assert set(frame.columns) == set(_FAMILY_2011)
    assert frame["interview"].tolist() == [101, 102, 103]
    assert frame["head_ss"].tolist() == [14000, 0, 9000]
    assert frame["spouse_ss"].tolist() == [7000, 0, 0]
    assert frame["head_ss_acc"].tolist() == [0, 0, 5]
    assert frame["fu_ss_prior_year"].tolist() == [1, 5, 9]


def test_family_reader_rejects_a_relabelled_variable(tmp_path):
    _write_family_2011(
        tmp_path,
        _family_values(),
        labels={"head_ss": "HEAD SOCIAL SECURITY INCOME-2009"},
    )
    with pytest.raises(ValueError, match="adjudicated table"):
        ssi.read_family_social_security(2011, data_dir=tmp_path)


def test_family_reader_rejects_a_second_concept_match(tmp_path):
    _write_family_2011(
        tmp_path,
        _family_values(),
        extra=[
            (
                "ER99999",
                6,
                "HEAD SOCIAL SECURITY INCOME-2010 REVISED",
                [0, 0, 0],
            )
        ],
    )
    with pytest.raises(ValueError, match="expected only ER52337"):
        ssi.read_family_social_security(2011, data_dir=tmp_path)


def test_family_reader_rejects_undocumented_codes(tmp_path):
    _write_family_2011(tmp_path, _family_values(head_ss_acc=[0, 3, 0]))
    with pytest.raises(ValueError, match="undocumented code"):
        ssi.read_family_social_security(2011, data_dir=tmp_path)
    _write_family_2011(tmp_path, _family_values(fu_ss_prior_year=[1, 2, 5]))
    with pytest.raises(ValueError, match="undocumented code"):
        ssi.read_family_social_security(2011, data_dir=tmp_path)


def test_family_reader_rejects_negative_amounts(tmp_path):
    _write_family_2011(tmp_path, _family_values(ofum_ss=[0, -5, 0]))
    with pytest.raises(ValueError, match="negative"):
        ssi.read_family_social_security(2011, data_dir=tmp_path)


def test_family_reader_rejects_duplicate_interviews(tmp_path):
    _write_family_2011(tmp_path, _family_values(interview=[101, 101, 103]))
    with pytest.raises(ValueError, match="duplicate interview"):
        ssi.read_family_social_security(2011, data_dir=tmp_path)


@pytest.mark.parametrize("wave", [2007, 2010, 2015])
def test_readers_refuse_unresolved_waves(tmp_path, wave):
    with pytest.raises(ValueError, match="outside the resolved"):
        ssi.read_family_social_security(wave, data_dir=tmp_path)
    with pytest.raises(ValueError, match="outside the resolved"):
        ssi.head_spouse_social_security_panel(waves=(wave,), data_dir=tmp_path)


def test_income_years_follow_waves():
    assert ssi.SS_WAVES == (2009, 2011, 2013)
    assert ssi.SS_INCOME_YEARS == (2008, 2010, 2012)


def test_head_spouse_panel_attaches_roles(tmp_path):
    _write_family_2011(tmp_path, _family_values())
    _write_individual(tmp_path)
    panel = ssi.head_spouse_social_security_panel(
        waves=(2011,), data_dir=tmp_path
    )
    assert panel["person_id"].tolist() == [1001, 1002, 3001]
    assert panel["role"].tolist() == ["head", "spouse", "head"]
    assert panel["ss_amount"].tolist() == [14000, 7000, 9000]
    assert panel["ss_acc"].tolist() == [0, 1, 5]
    assert panel["income_year"].unique().tolist() == [2010]
    assert panel["fu_ss_prior_year"].tolist() == [1, 1, 9]
    # The OFUM (3002) and the institutionalized person (4001) never attach.
    assert not {3002, 4001} & set(panel["person_id"])


# --------------------------------------------------------------------------
# Value labels and the individual-file reader
# --------------------------------------------------------------------------
def test_value_block_parser_keeps_semicolons_inside_labels(tmp_path):
    path = tmp_path / "formats.sas"
    path.write_text(_formats_text())
    blocks = ssi.parse_value_label_blocks(path)
    assert blocks["ER34030F"][3] == (
        "Survivor benefits; dependent of deceased recipient"
    )
    assert blocks["ER34030F"][7] == "Other"
    assert (
        blocks["ER34139F"][1] == "Social security type was survivor's benefit"
    )
    assert blocks["ER34137F"][9] == "NA; refused"


def test_type_code_verification_passes_and_fails(tmp_path):
    _write_individual(tmp_path)
    checked = ssi.verify_social_security_type_codes(
        data_dir=tmp_path, waves=(2009, 2011)
    )
    assert checked[2009] == {"ER34030": "ER34030F"}
    assert set(checked[2011]) == {var for var, _, _ in _FLAG_VARS_2011}
    _write_individual(tmp_path, relabel_2011_flag="ER34138")
    with pytest.raises(ValueError, match="ER34138"):
        ssi.verify_social_security_type_codes(data_dir=tmp_path, waves=(2011,))


def test_individual_reader_decodes_amounts_and_types(tmp_path):
    _write_individual(tmp_path)
    frame = ssi.read_individual_social_security(
        waves=(2009, 2011), data_dir=tmp_path
    )
    rows = frame.set_index(["person_id", "wave"])
    # Only in-family persons (sequence 1-20) appear; 4001 is institutional.
    assert 4001 not in set(frame["person_id"])
    assert rows.loc[(1001, 2011), "ss_amount"] == 14000
    assert rows.loc[(1001, 2011), "income_year"] == 2010
    assert bool(rows.loc[(1001, 2011), "type_retirement"])
    assert not bool(rows.loc[(1001, 2011), "type_survivor"])
    # Code 8 (DK) carries no type information.
    assert pd.isna(rows.loc[(1002, 2011), "type_other"])
    assert bool(rows.loc[(3002, 2011), "type_survivor"])
    assert bool(rows.loc[(3002, 2011), "type_other"])
    # The 2009 single code maps onto the same flags.
    assert bool(rows.loc[(1001, 2009), "type_retirement"])
    assert not bool(rows.loc[(1001, 2009), "type_disability"])
    assert bool(rows.loc[(1002, 2009), "type_survivor"])
    assert rows.loc[(1002, 2009), "ss_acc"] == 5
    assert not rows["type_combination"].any()


def test_individual_reader_rejects_a_relabelled_amount(tmp_path):
    _write_individual(tmp_path, amount_label="G34 AMT SOC SEC RCD 13")
    with pytest.raises(ValueError, match="ER34143"):
        ssi.read_individual_social_security(waves=(2011,), data_dir=tmp_path)
