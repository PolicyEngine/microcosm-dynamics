"""Track M structural counts on INVENTED frames (no PSID file is read).

Ten INVENTED persons exercise every step of the universe funnel and the
availability counts; each expected count is worked by hand below.  The
real counts are written by ``scripts/track_m_structure.py`` to the
evidence directory, never by a test.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from populace_dynamics.min_benefit_track_m import structure


def _anchor() -> pd.DataFrame:
    # person, sequence, relationship, age, weight, interview, amount, acc,
    # retirement, disability, other
    rows = [
        (1, 1, 10, 70, 1.0, 100, 15_000, 0, 1, 5, 5),  # RP, born 1952
        (2, 1, 20, 68, 1.0, 100, 8_000, 5, 1, 5, 5),  # spouse, 1954
        (3, 2, 30, 3, 1.0, 100, 0, 0, 0, 0, 0),  # child aged 3
        (4, 55, 10, 80, 1.0, 400, 0, 0, 0, 0, 0),  # institution
        (5, 75, 10, 66, 1.0, 500, 0, 0, 0, 0, 0),  # moved out
        (6, 1, 10, 50, 1.0, 200, 0, 0, 0, 0, 0),  # RP born 1972
        (7, 1, 22, 64, 1.0, 200, 5_000, 1, 5, 1, 8),  # partner, 1958
        (8, 1, 30, 90, 0.0, 200, 0, 0, 0, 0, 0),  # zero weight
        (9, 1, 40, 75, 1.0, 100, 0, 0, 0, 0, 0),  # other member, no SS
        (10, 1, 10, 80, 1.0, 300, 0, 0, 0, 0, 0),  # RP, family-only SS
    ]
    frame = pd.DataFrame(
        rows,
        columns=[
            "person_id",
            "sequence",
            "relationship",
            "age",
            "weight",
            "interview",
            "ss_amount",
            "ss_acc",
            "type_retirement",
            "type_disability",
            "type_other",
        ],
    )
    for column in (
        "type_survivor",
        "type_dependent_of_disabled",
        "type_dependent_of_retired",
    ):
        frame[column] = frame["ss_amount"].gt(0).map({True: 5, False: 0})
    frame["reported_birth_year"] = pd.array([pd.NA] * len(frame), "Int64")
    return frame


def _inputs() -> structure.TrackMStructureInputs:
    earnings = pd.DataFrame(
        [
            {"person_id": 1, "period": year, "age": year - 1952}
            for year in [*range(1974, 1997), *range(1998, 2013, 2)]
        ]
    )
    earnings["earnings"] = 30_000.0
    return structure.TrackMStructureInputs(
        anchor=_anchor(),
        family_social_security=pd.DataFrame(
            {
                "interview": [100, 200, 300],
                "rp_amount": [15_000, 0, 700],
                "spouse_amount": [8_000, 5_000, 0],
            }
        ),
        death_records=pd.DataFrame(
            {
                "person_id": [1, 2, 7, 10],
                "sex": ["male", "female", "male", "female"],
            }
        ),
        marriage_history=pd.DataFrame(
            {"person_id": [1, 2], "birth_year": [1952, 1954]}
        ),
        observed_earnings=earnings,
        design=pd.DataFrame(
            {
                "person_id": [1, 2, 7],
                "stratum": [1, 1, 2],
                "cluster": [1, 1, 1],
            }
        ),
        codes={"INVENTED": "INVENTED"},
    )


@pytest.fixture(scope="module")
def counts() -> dict:
    return structure.structural_counts(_inputs())


def test_the_universe_funnel(counts):
    funnel = counts["funnel"]
    assert funnel["ind2023er_records"] == 10
    assert funnel["sequence_groups_2023"] == {
        "in_family": 8,
        "institution": 1,
        "moved_out": 1,
    }
    assert funnel["in_family"] == 8
    assert funnel["in_family_zero_weight"] == 1  # person 8
    assert funnel["in_family_positive_weight"] == 7
    assert funnel["age_0_5_counted_out_before_birth_law"] == 1  # person 3
    # Persons 1 and 2 from the marriage history; 6, 7, 9 and 10 from the
    # 2023 age (2022 - age).
    assert funnel["birth_source"] == {
        "derived_projection_age": 4,
        "exact_marriage": 2,
    }
    assert funnel["born_1960_or_earlier"] == 5  # 1, 2, 7, 9, 10
    assert funnel["born_1961_or_later"] == 1  # 6
    assert funnel["receives_oasdi_person_level"] == 3  # 1, 2, 7
    assert funnel["no_person_level_receipt"] == 2  # 9, 10


def test_the_family_file_reconciliation_counts(counts):
    reconciliation = counts["funnel"]["reconciliation_with_family_file"]
    assert reconciliation["reference_person"] == {
        "persons": 2,
        "family_record_missing": 0,
        "both_positive": 1,  # person 1
        "person_only": 0,
        "family_only": 1,  # person 10: family file 700, person-level 0
        "neither": 0,
    }
    assert reconciliation["spouse"]["both_positive"] == 1
    assert reconciliation["partner"]["both_positive"] == 1


def test_the_beneficiary_counts(counts):
    summary = counts["beneficiaries_62_plus"]
    assert summary["persons"] == 3
    assert summary["sex"] == {"female": 1, "male": 2}
    assert summary["role"] == {
        "partner": 1,
        "reference_person": 1,
        "spouse": 1,
    }
    assert summary["birth_band"] == {"born_1945_1960": 3}
    assert summary["amount_accuracy_code"] == {"0": 1, "1": 1, "5": 1}
    assert summary["type_mentions"]["type_retirement"] == {
        "mentioned": 2,
        "not_mentioned": 1,
    }
    assert summary["type_mentions"]["type_other"] == {
        "not_mentioned": 2,
        "unknown": 1,
    }
    assert summary["design"] == {
        "strata": 2,
        "stratum_cluster_pairs": 2,
        "family_units": 2,
    }


def test_the_availability_counts(counts):
    availability = counts["years_of_coverage_availability"]
    # Each window is 40 years (ages 22-61).  Person 1 (1952): 1974-2013,
    # gap years 1997-2013 odd = 9, collected 31, all observed.  Person 2
    # (1954): 1976-2015, 10 gap years, 30 collected, none observed.
    # Person 7 (1958): 1980-2019, 12 gap years, 28 collected, none.
    # Each window holds 1997 and 1999 (never asked: 3 x 2 = 6); the other
    # gap years (2001 on: 7 + 8 + 10 = 25) were asked one wave later.
    assert availability["person_years"] == {
        "window_years": 120,
        "pre_panel": 0,
        "gap": 31,
        "gap_never_asked": 6,
        "gap_asked_next_wave": 25,
        "collected_observed": 31,
        "collected_not_observed": 58,
    }
    assert availability["prior_year_labor_income_labels"] == {}
    assert availability["persons_by_observed_window_years"] == {
        "0": 2,
        "30_39": 1,
    }
    assert availability["persons_with_no_observed_year"] == 2


def test_availability_window():
    window = structure.availability_window(1940)
    # 1962-2001: 1962-1967 before the panel, 1997, 1999, 2001 gap years.
    assert (window["start"], window["end"]) == (1962, 2001)
    assert window["pre_panel"] == list(range(1962, 1968))
    assert window["gap"] == [1997, 1999, 2001]
    assert window["gap_never_asked"] == [1997, 1999]
    assert window["gap_asked_next_wave"] == [2001]
    assert len(window["collected"]) == 40 - 6 - 3
    # A window past 2022 is cut there.
    assert structure.availability_window(1965)["end"] == 2022


def test_the_structure_module_imports_no_rules():
    # The counts must never reach the years-of-coverage or minimum rules;
    # the script also refuses at run time if either was imported.
    source = Path(structure.__file__).read_text(encoding="utf-8")
    for name in (
        "rules",
        "coverage",
        "specification",
        "thresholds",
        "evaluation",
        "tabulation",
        "pipeline",
        "invented",
    ):
        assert f"min_benefit_track_m.{name}" not in source
        assert f"min_benefit_track_m import {name}" not in source


def test_prior_year_labor_income_labels_are_matched_by_role():
    # INVENTED labels in the PSID's forms: the amount is matched, its
    # "PER FOR" time unit and "ACCURACY OF" code are not.
    labels = {
        "V1": "R2 LABOR INCOME 2021 (RP)",
        "V2": "R2 PER FOR LABOR INCOME 2021 (RP)",
        "V3": "ACCURACY OF LABOR INCOME 2021 (RP)",
        "V4": "R2  LABOR INCOME 2021 (SP)",
        "V5": "R26 LABOR INCOME 2019 (HD)",
        "V6": "LABOR INCOME OF REF PERSON-2022",
    }
    assert structure.prior_year_labor_income_variables(labels, 2021) == {
        "reference_person": "V1",
        "spouse": "V4",
    }
    assert structure.prior_year_labor_income_variables(labels, 2019) == {
        "reference_person": "V5"
    }
    assert structure.prior_year_labor_income_variables(labels, 1997) == {}
    with pytest.raises(ValueError, match="two reference_person"):
        structure.prior_year_labor_income_variables(
            {**labels, "V7": "R11 LABOR INCOME 2021 (HD)"}, 2021
        )


def _write_family_sps(root: Path, wave: int, labels: dict) -> None:
    base = root / "family" / str(wave)
    base.mkdir(parents=True)
    body = "\n".join(
        f'      {var}    "{label}"' for var, label in labels.items()
    )
    (base / f"FAM{wave}ER.sps").write_text(
        f"VARIABLE LABELS\n{body}\n.\n", encoding="utf-8"
    )
    (base / f"FAM{wave}ER.txt").write_text("", encoding="utf-8")


def test_prior_year_labels_are_verified_wave_by_wave(tmp_path):
    # INVENTED setup files: none for 1997 or 1999, both roles 2001-2021.
    for year in structure.NEVER_ASKED_LABOR_INCOME_YEARS:
        _write_family_sps(tmp_path, year + 2, {"X1": f"TOTAL INCOME {year}"})
    for year in structure.NEXT_WAVE_LABOR_INCOME_YEARS:
        _write_family_sps(
            tmp_path,
            year + 2,
            {
                f"H{year}": f"R2 LABOR INCOME {year} (RP)",
                f"S{year}": f"R11 LABOR INCOME {year} (SP)",
            },
        )
    found = structure.verify_prior_year_labor_income_labels(data_dir=tmp_path)
    assert found["1997"] == {
        "wave": 1999,
        "reference_person": None,
        "spouse": None,
    }
    assert found["2021"] == {
        "wave": 2023,
        "reference_person": "H2021",
        "spouse": "S2021",
    }
    assert len(found) == 2 + 11
    # A wave that drops the spouse item is refused.
    sps = tmp_path / "family" / "2013" / "FAM2013ER.sps"
    sps.write_text(
        'VARIABLE LABELS\n      H2011    "R2 LABOR INCOME 2011 (RP)"\n.\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="2013 family file"):
        structure.verify_prior_year_labor_income_labels(data_dir=tmp_path)
