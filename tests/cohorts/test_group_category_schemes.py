"""Pins and definitions of the committed group-category scheme artifact.

Only the cleared guide and its labels-only capture under ``data/external``
are read. No policy-option page or comparator is opened. Altered captures,
malformed schemes and person attributes are explicitly INVENTED fixtures.
Invariants: committed sources match their seals, row labels and order
match the capture, education bands partition their documented support,
output/status column names do not collide, and an unresolved definition
produces an explicit status rather than an inferred category.
"""

from __future__ import annotations

import copy
import hashlib
import html
import json
import re
from pathlib import Path

import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.cohorts import group_attributes as cohort
from populace_dynamics.data import group_attributes_psid as gap

_ROOT = Path(__file__).resolve().parents[2]
_EXTERNAL = _ROOT / "data" / "external"
_PROFILE_TABLES = {
    "annual_benefits": (1, 2, 3),
    "annual_household_income": (7, 8, 9),
    "annual_official_poverty": (10, 11, 12),
    "cohort_benefit_tax_ratio": (13, 14, 15, 16),
    "cohort_initial_replacement_rate": (17, 18, 19, 20),
}
_SOURCE_PROVENANCE = {
    "mint8_user_guide": "ssa_mint8_table_user_guide.source.provenance.json",
    "mint8_row_labels": (
        "ssa_mint8_payroll_option_row_labels.source.provenance.json"
    ),
}


@pytest.fixture(scope="module")
def schemes():
    return cohort.load_schemes()


@pytest.fixture(scope="module")
def captured_rows(schemes):
    source = schemes["sources"]["mint8_row_labels"]["committed_file"]
    return json.loads((_ROOT / source).read_text())


def _plain_text(value: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", value)).split())


def _paragraph(guide: str, identifier: str) -> str:
    match = re.search(
        rf'<p\b[^>]*\bid="{re.escape(identifier)}"[^>]*>(.*?)</p>',
        guide,
        flags=re.DOTALL,
    )
    assert match is not None
    return _plain_text(match.group(1))


def _invented_scheme(schemes: dict) -> dict:
    altered = copy.deepcopy(schemes)
    altered["note"] = "INVENTED altered scheme for validation tests"
    return altered


def test_scheme_and_source_seals(schemes):
    assert hashlib.sha256(cohort.SCHEMES_PATH.read_bytes()).hexdigest() == (
        cohort.SCHEMES_SHA256
    )
    for source_id, provenance_file in _SOURCE_PROVENANCE.items():
        source = schemes["sources"][source_id]
        provenance = json.loads((_EXTERNAL / provenance_file).read_text())
        raw = (_ROOT / source["committed_file"]).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        assert digest == source["sha256"] == provenance["source_sha256"]
        assert provenance["committed_source_file"] == source["committed_file"]
        assert provenance["source_url"] == source["url"]
        assert source["locator"]
    guide = _ROOT / schemes["sources"]["mint8_user_guide"]["committed_file"]
    assert (
        'name="DCTERMS:dateCertified" content="2025-10-01"'
        in guide.read_text()
    )


@pytest.mark.parametrize("profile_id", tuple(_PROFILE_TABLES))
def test_profile_row_groups_match_every_captured_table(
    schemes, captured_rows, profile_id
):
    profiles = schemes["schemes"]["mint8"]["table_profiles"]
    assert set(profiles) == set(_PROFILE_TABLES)
    profile = profiles[profile_id]
    assert profile["source"] == "mint8_row_labels"
    table_ids = _PROFILE_TABLES[profile_id]
    assert profile["locator"] == "tables " + ", ".join(map(str, table_ids))
    for table_id in table_ids:
        table = captured_rows["tables"][str(table_id)]
        assert profile["row_groups"] == table["groups"]
    if profile_id.startswith("annual_"):
        assert profile["analysis_years"] == [2030, 2050, 2070]
        for year, table_id in zip(
            profile["analysis_years"], table_ids, strict=True
        ):
            caption = captured_rows["tables"][str(table_id)]["caption"]
            assert str(year) in caption
            assert profile["population"] in caption
    else:
        for (lower, upper), table_id in zip(
            profile["birth_cohorts"], table_ids, strict=True
        ):
            caption = captured_rows["tables"][str(table_id)]["caption"]
            assert f"{lower}–{upper}" in caption


def test_lifetime_descriptors_match_captured_definitions_and_labels(
    schemes, captured_rows
):
    mint = schemes["schemes"]["mint8"]
    descriptors = mint["lifetime_earnings_dimensions"]
    assert set(descriptors) == {
        "initial_aime",
        "payroll_tax_own",
        "payroll_tax_shared",
    }
    guide_file = schemes["sources"]["mint8_user_guide"]["committed_file"]
    guide = (_ROOT / guide_file).read_text()
    paragraphs = {
        "initial_aime": _paragraph(guide, "AIME"),
        "payroll_tax_own": _paragraph(guide, "lifetime-tax"),
        "payroll_tax_shared": _paragraph(guide, "lifetime-tax-shared"),
    }
    for dimension_id, descriptor in descriptors.items():
        assert descriptor["source"] == "mint8_user_guide"
        assert descriptor["labels_source"] == "mint8_row_labels"
        assert descriptor["reference_age"] == 62
        assert "at age 62" in paragraphs[dimension_id]
        assert descriptor["quintile_population"] == "each birth cohort"
        assert "for each birth cohort" in paragraphs[dimension_id]
        for table_id in range(13, 21):
            groups = captured_rows["tables"][str(table_id)]["groups"]
            group = next(
                row
                for row in groups
                if row["group"] == descriptor["group_label"]
            )
            assert descriptor["labels"] == group["labels"]

    assert "under current law at age 62" in paragraphs["initial_aime"]
    assert "present value" in paragraphs["payroll_tax_own"]
    plain_guide = _plain_text(guide)
    assert (
        "We use the Social Security Trust Fund interest rate to adjust "
        "benefits and taxes to their present values at age 62."
    ) in plain_guide
    for dimension in ("payroll_tax_own", "payroll_tax_shared"):
        assert descriptors[dimension]["discount_rate"] == (
            "Social Security Trust Fund interest rate"
        )
    shared = descriptors["payroll_tax_shared"]
    assert shared["married_year_rule"] == (
        "(own payroll taxes + spouse payroll taxes) / 2"
    )
    assert shared["unmarried_year_rule"] == "own payroll taxes"
    assert (
        "paid while married are shared equally"
        in paragraphs["payroll_tax_shared"]
    )
    assert (
        "For never-married individuals, this is the same"
        in paragraphs["payroll_tax_shared"]
    )
    assert "not married, we count only their individual payroll taxes" in (
        paragraphs["payroll_tax_shared"]
    )


def test_report_education_definitions_remain_unresolved(schemes):
    spec = schemes["schemes"]["boomers2004"]["dimensions"]["education"]
    assert not spec["bands"]
    assert not spec["assumptions"]
    assert spec["row_labels"] == [
        "High school dropout",
        "High school graduate",
        "College graduate",
    ]
    # INVENTED persons span the documented years-of-education support.
    frame = pd.DataFrame(
        {"education_years": pd.array([*range(18), pd.NA], dtype="Int64")}
    )
    labels, statuses = cohort.apply_category_scheme(frame, "education", spec)
    assert labels.isna().all()
    assert statuses.iloc[:-1].eq("unresolved:definition_not_recorded").all()
    assert statuses.iloc[-1] == cohort.ATTRIBUTE_UNKNOWN


@pytest.mark.parametrize("source_id", tuple(_SOURCE_PROVENANCE))
def test_changed_capture_is_refused(schemes, monkeypatch, tmp_path, source_id):
    for source in schemes["sources"].values():
        if "committed_file" not in source:
            continue
        path = tmp_path / source["committed_file"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((_ROOT / source["committed_file"]).read_bytes())
    altered = tmp_path / schemes["sources"][source_id]["committed_file"]
    altered.write_bytes(altered.read_bytes() + b"\nINVENTED altered bytes\n")
    monkeypatch.setattr(cohort, "_REPO_ROOT", tmp_path)
    with pytest.raises(ValueError, match="scheme source .* changed"):
        cohort.load_schemes()


def test_changed_scheme_is_refused(schemes, monkeypatch, tmp_path):
    path = tmp_path / "INVENTED_altered_scheme.json"
    path.write_text(json.dumps(_invented_scheme(schemes)))
    monkeypatch.setattr(cohort, "SCHEMES_PATH", path)
    with pytest.raises(ValueError, match="expected the pinned"):
        cohort.load_schemes()


@pytest.mark.parametrize("defect", ("gap", "overlap"))
@settings(max_examples=18, deadline=None)
@given(year=st.integers(min_value=0, max_value=17))
def test_education_support_must_be_partitioned(defect, year):
    invented = _invented_scheme(cohort.load_schemes())
    spec = invented["schemes"]["boomers2004"]["dimensions"]["education"]
    spec["unresolved_bands"] = []
    intervals = (
        [(0, year - 1), (year + 1, 17)]
        if defect == "gap"
        else [(0, 17), (year, year)]
    )
    for lower, upper in intervals:
        if lower <= upper:
            spec["unresolved_bands"].append(
                {
                    "min": lower,
                    "max": upper,
                    "status": "INVENTED_missing_definition",
                    "reason": "INVENTED malformed partition",
                }
            )
    with pytest.raises(ValueError, match="bands must cover each"):
        cohort._validate_schemes(invented)


@pytest.mark.parametrize(
    "column",
    (
        "race_ethnicity_mint8_status",
        "education_years",
        "education_source_wave",
    ),
)
def test_output_and_status_columns_cannot_collide(schemes, column):
    invented = _invented_scheme(schemes)
    invented["schemes"]["mint8"]["dimensions"]["education"]["column"] = column
    with pytest.raises(ValueError, match="column .* is taken"):
        cohort._validate_schemes(invented)


def test_race_dimension_can_explicitly_leave_a_known_code_unresolved(schemes):
    invented = _invented_scheme(schemes)
    spec = invented["schemes"]["mint8"]["dimensions"]["race_ethnicity"]
    del spec["categories"]["white_non_hispanic"]
    spec["unresolved"] = {
        "white_non_hispanic": "INVENTED definition withheld in a test scheme"
    }
    cohort._validate_schemes(invented)
    # INVENTED attribute rows exercise unresolved, assigned and unknown.
    frame = pd.DataFrame(
        {
            "hispanic": pd.array([False, True, pd.NA], dtype="boolean"),
            "race_mentions": pd.array(
                [gap.WHITE, pd.NA, pd.NA], dtype="string"
            ),
        }
    )
    labels, statuses = cohort.apply_category_scheme(
        frame, "race_ethnicity", spec
    )
    assert pd.isna(labels.iloc[0])
    assert statuses.iloc[0] == "unresolved:white_non_hispanic"
    assert labels.iloc[1] == spec["categories"]["hispanic"]
    assert statuses.iloc[1] == cohort.ASSIGNED
    assert pd.isna(labels.iloc[2])
    assert statuses.iloc[2] == cohort.ATTRIBUTE_UNKNOWN
