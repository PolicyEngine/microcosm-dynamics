"""Cohort-side group attributes on INVENTED persons and fixed-width files.

No observation in this module comes from the PSID. The differential
oracle implements latest-complete report selection with ordinary Python
records, independently of the pandas builder. The invariants are exact
requested-person coverage, order-independent resolution, education at the
anchor cutoff, explicit unknowns, and independently reproducible seals.
The committed category schemes under ``"data" / "external"`` are read,
so the module belongs to the artifact tier.
"""

from __future__ import annotations

import copy
import dataclasses
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pandas.testing import assert_frame_equal

from populace_dynamics.cohorts import group_attributes as cohort
from populace_dynamics.data import group_attributes_psid as gap
from tests.data.psid_fixtures import write_product

_REPORT_COLUMNS = ["person_id", "wave", "role", *gap.REPORT_CODE_COLUMNS]
_EDUCATION_COLUMNS = [
    "person_id",
    "wave",
    "education_code",
    "role",
    "family_education_code",
]


def _report(
    person_id: int,
    wave: int,
    *,
    hispanic: int | None = 0,
    race: tuple[int, ...] = (1,),
    role: str = "head",
    birth_state: int = 1,
    year_came: int = 0,
) -> dict:
    """One INVENTED report, with every actual mention explicitly coded."""

    items = gap.FAMILY_ITEMS[wave]
    row = dict.fromkeys(_REPORT_COLUMNS, pd.NA)
    row.update(person_id=person_id, wave=wave, role=role)
    row["hispanic_code"] = hispanic if items.asks_hispanic_origin else pd.NA
    for mention in range(1, len(items.race[role]) + 1):
        row[f"race_code_{mention}"] = (
            race[mention - 1] if mention <= len(race) else 0
        )
    if wave in gap.FAMILY_EDUCATION_WAVES:
        row["family_education_code"] = 12
    if wave in gap.BIRTHPLACE_WAVES:
        row["birth_state_code"] = birth_state
        row["year_came_code"] = year_came
    return row


def _education(
    person_id: int,
    wave: int,
    years: int,
    *,
    role: str | None = None,
    family_code: int | None = None,
) -> dict:
    return {
        "person_id": person_id,
        "wave": wave,
        "education_code": years,
        "role": pd.NA if role is None else role,
        "family_education_code": (
            pd.NA if family_code is None else family_code
        ),
    }


def _inputs(
    reports: list[dict] | None = None,
    education: list[dict] | None = None,
    *,
    universe: tuple[int, ...] = (1001, 1002, 1003),
) -> cohort.GroupAttributeInputs:
    race = pd.DataFrame(reports or [], columns=_REPORT_COLUMNS)
    edu = pd.DataFrame(education or [], columns=_EDUCATION_COLUMNS)
    for frame in (race, edu):
        for column in frame:
            frame[column] = frame[column].astype(
                "string" if column == "role" else "Int64"
            )
    return cohort.GroupAttributeInputs(
        reports=race,
        education=edu,
        universe=pd.Series(universe, name="person_id", dtype="int64"),
        provenance={"kind": "INVENTED", "fixture": "group attributes"},
    )


def _build(inputs, person_ids=(1001, 1002, 1003), waves=(2011,)):
    return cohort.build_group_attributes(
        inputs, person_ids, anchor_waves=waves
    )


def test_latest_complete_report_wins_and_unknown_person_is_retained():
    inputs = _inputs(
        [
            _report(1001, 2005, race=(1,)),
            _report(1001, 2011, race=(2,)),
            _report(1001, 2023, hispanic=9, race=(1,)),
            _report(1002, 2023, hispanic=1, race=(9,)),
        ],
        [_education(1001, 2011, 12), _education(1003, 2011, 14)],
    )
    result = _build(inputs, [1003, 1002, 1001])
    frame = result.frame.set_index("person_id")
    assert result.frame.person_id.tolist() == [1001, 1002, 1003]
    assert tuple(result.frame.columns) == cohort.FRAME_COLUMNS
    assert frame.loc[1001, "race_ethnicity_mint8"] == (
        "Black or African American, non-Hispanic"
    )
    assert frame.loc[1001, "race_ethnicity_source_wave"] == 2011
    assert frame.loc[1001, "race_ethnicity_n_reports"] == 2
    assert frame.loc[1001, "race_ethnicity_n_distinct"] == 2
    assert frame.loc[1002, "race_ethnicity_mint8"] == (
        "Hispanic or Latino, any race"
    )
    assert frame.loc[1002, "race_ethnicity_source_wave"] == 2023
    assert frame.loc[1003, "race_ethnicity_status"] == ("never_head_or_spouse")
    assert pd.isna(frame.loc[1003, "race_ethnicity_mint8"])
    assert frame.loc[1003, "education_mint8"] == "Associate"
    assert result.provenance["n_persons"] == 3
    assert result.provenance["sourced_after_cutoff"]["race_ethnicity"] == 1
    assert result.provenance["status_counts"]["race_ethnicity_status"] == {
        "known": 2,
        "never_head_or_spouse": 1,
    }


def test_all_never_head_spouse_still_get_rows_and_status_counts():
    result = _build(_inputs())
    assert result.frame.person_id.tolist() == [1001, 1002, 1003]
    for column in ("race_ethnicity_status", "country_of_birth_status"):
        assert result.frame[column].tolist() == ["never_head_or_spouse"] * 3
        assert result.provenance["status_counts"][column] == {
            "never_head_or_spouse": 3
        }
    assert (
        result.frame.education_status.tolist() == ["no_report_by_cutoff"] * 3
    )
    for column in (
        "race_ethnicity_mint8",
        "education_mint8",
        "education_report3",
        "country_of_birth_mint8",
    ):
        assert result.frame[column].isna().all()
        assert (
            result.frame[f"{column}_status"].tolist()
            == ["attribute_unknown"] * 3
        )


def test_hispanic_fallback_does_not_invent_race_or_non_hispanic_origin():
    frame = _build(
        _inputs(
            [
                _report(1001, 2011, hispanic=0, race=(9,)),
                _report(1001, 2023, hispanic=9, race=(1,)),
                _report(1002, 1999, hispanic=None, race=(1,)),
                _report(1003, 1999, hispanic=None, race=(5,)),
            ]
        )
    ).frame.set_index("person_id")
    assert not frame.loc[1001, "hispanic"]
    assert frame.loc[1001, "hispanic_source_wave"] == 2011
    assert frame.loc[1001, "race_ethnicity_status"] == "dk_na_refused"
    assert pd.isna(frame.loc[1001, "race_ethnicity_mint8"])
    assert pd.isna(frame.loc[1002, "hispanic"])
    assert frame.loc[1002, "race_ethnicity_status"] == (
        "hispanic_origin_not_asked"
    )
    assert frame.loc[1003, "hispanic"]
    assert frame.loc[1003, "race_ethnicity_hispanic_basis"] == (
        "latino_race_mention"
    )
    assert frame.loc[1003, "race_ethnicity_report4"] == "Hispanic"


def test_distinct_race_count_uses_four_way_semantics_and_not_mention_order():
    frame = _build(
        _inputs(
            [
                _report(1001, 2005, race=(1, 2)),
                _report(1001, 2011, race=(2, 1)),
                _report(1001, 2023, race=(4,)),
            ]
        )
    ).frame.set_index("person_id")
    assert frame.loc[1001, "race_ethnicity_n_reports"] == 3
    assert frame.loc[1001, "race_ethnicity_n_distinct"] == 1
    assert frame.loc[1001, "race_ethnicity_mint8"] == (
        "All other races, non-Hispanic"
    )


def test_undocumented_spouse_zero_does_not_override_known_ethnicity():
    frame = _build(
        _inputs(
            [
                _report(1001, 1993, hispanic=1, role="spouse"),
                _report(1001, 1994, hispanic=0, role="spouse"),
                _report(1002, 1996, hispanic=0, role="spouse"),
            ]
        )
    ).frame.set_index("person_id")
    assert frame.loc[1001, "race_ethnicity_source_wave"] == 1993
    assert frame.loc[1001, "race_ethnicity_report4"] == "Hispanic"
    assert pd.isna(frame.loc[1002, "race_ethnicity_report4"])
    assert pd.isna(frame.loc[1002, "hispanic"])
    assert frame.loc[1002, "race_ethnicity_n_reports"] == 0


def test_education_uses_latest_known_by_cutoff_and_family_zero_adjudication():
    inputs = _inputs(
        education=[
            _education(1001, 2009, 12),
            _education(1001, 2011, 99),
            _education(1001, 2023, 17),
            _education(1002, 2011, 0, role="head", family_code=0),
            _education(1003, 2011, 0),
        ]
    )
    frame = _build(inputs, waves=(2011, 2009, 2011)).frame.set_index(
        "person_id"
    )
    assert frame.loc[1001, "education_years"] == 12
    assert frame.loc[1001, "education_source_wave"] == 2009
    assert frame.loc[1001, "education_n_reports"] == 1
    assert frame.loc[1002, "education_years"] == 0
    assert frame.loc[1002, "education_source_variables"] == (
        gap.INDIVIDUAL_ITEMS[2011].education[0]
        + "|"
        + gap.FAMILY_ITEMS[2011].completed_education["head"][0]
    )
    assert pd.isna(frame.loc[1003, "education_years"])
    assert frame.loc[1003, "education_status"] == "no_report_by_cutoff"
    later = _build(inputs, waves=(2023,)).frame.set_index("person_id")
    assert later.loc[1001, "education_years"] == 17
    assert later.loc[1001, "education_n_distinct"] == 2


def test_country_latest_valid_pair_wins_and_territory_stays_unresolved():
    frame = _build(
        _inputs(
            [
                _report(1001, 2013, birth_state=1),
                _report(1001, 2015, birth_state=0, year_came=1980),
                _report(1001, 2023, birth_state=1, year_came=1980),
                _report(1002, 2023, birth_state=0),
                _report(1003, 2023, birth_state=99),
            ]
        )
    ).frame.set_index("person_id")
    assert frame.loc[1001, "country_of_birth"] == "foreign_country"
    assert frame.loc[1001, "country_of_birth_source_wave"] == 2015
    assert frame.loc[1001, "country_of_birth_n_reports"] == 2
    assert frame.loc[1001, "country_of_birth_n_distinct"] == 2
    assert frame.loc[1001, "country_of_birth_mint8"] == "Other countries"
    assert frame.loc[1002, "country_of_birth_status"] == "known"
    assert pd.isna(frame.loc[1002, "country_of_birth_mint8"])
    assert frame.loc[1002, "country_of_birth_mint8_status"] == (
        "unresolved:us_territory"
    )
    assert frame.loc[1003, "country_of_birth_status"] == "dk_na_refused"


@pytest.mark.parametrize(
    ("years", "mint_label"),
    [
        (0, "Less than high school"),
        (11, "Less than high school"),
        (12, "High school"),
        (13, "High school"),
        (14, "Associate"),
        (15, "Associate"),
        (16, "Bachelor"),
        (17, "Graduate"),
    ],
)
def test_mint_boundaries_and_unrecorded_report_definitions(years, mint_label):
    inputs = _inputs(
        education=[
            _education(1001, 2011, years, role="head", family_code=years)
        ]
    )
    row = _build(inputs, (1001,)).frame.iloc[0]
    assert row.education_mint8 == mint_label
    assert row.education_mint8_status == "assigned"
    assert pd.isna(row.education_report3)
    assert row.education_report3_status == (
        "unresolved:definition_not_recorded"
    )


@given(
    st.dictionaries(
        st.sampled_from((2005, 2007, 2009, 2011, 2013, 2023)),
        st.tuples(st.sampled_from((0, 1, 9)), st.sampled_from((1, 2, 4, 9))),
        min_size=1,
    )
)
@settings(max_examples=40, deadline=None)
def test_latest_complete_selection_matches_independent_record_oracle(codes):
    reports = [
        _report(1001, wave, hispanic=hispanic, race=(race,))
        for wave, (hispanic, race) in codes.items()
    ]
    row = _build(_inputs(reports), (1001,)).frame.iloc[0]
    # This oracle deliberately does not call the reader's harmonization,
    # cohort helper, pandas grouping, or data-driven category mapper.
    complete = []
    for wave, (hispanic, race) in sorted(codes.items()):
        if hispanic == 1:
            complete.append((wave, "Hispanic or Latino, any race"))
        elif hispanic == 0 and race != 9:
            label = {
                1: "White, non-Hispanic",
                2: "Black or African American, non-Hispanic",
                4: "All other races, non-Hispanic",
            }[race]
            complete.append((wave, label))
    assert row.race_ethnicity_n_reports == len(complete)
    assert row.race_ethnicity_n_distinct == len({r[1] for r in complete})
    if complete:
        assert row.race_ethnicity_source_wave == complete[-1][0]
        assert row.race_ethnicity_mint8 == complete[-1][1]
    else:
        assert pd.isna(row.race_ethnicity_source_wave)
        assert pd.isna(row.race_ethnicity_mint8)


@given(
    st.dictionaries(
        st.sampled_from((2005, 2007, 2009, 2011, 2013, 2023)),
        st.sampled_from((0, 1, 11, 12, 14, 16, 17, 99)),
        min_size=1,
    ),
    st.sampled_from((2005, 2009, 2011, 2023)),
)
@settings(max_examples=40, deadline=None)
def test_education_latest_known_matches_independent_cutoff_oracle(
    codes, cutoff
):
    education = [_education(1001, wave, code) for wave, code in codes.items()]
    row = _build(_inputs(education=education), (1001,), (cutoff,)).frame.iloc[
        0
    ]
    known = sorted(
        (wave, code)
        for wave, code in codes.items()
        if wave <= cutoff and 1 <= code <= 17
    )
    assert row.education_n_reports == len(known)
    assert row.education_n_distinct == len({r[1] for r in known})
    if known:
        assert row.education_source_wave == known[-1][0]
        assert row.education_years == known[-1][1]
        assert row.education_source_wave <= cutoff
    else:
        assert pd.isna(row.education_source_wave)
        assert pd.isna(row.education_years)


@given(st.permutations((1001, 1002, 1003)))
@settings(deadline=None)
def test_requested_person_order_does_not_change_frame_or_provenance(order):
    inputs = _inputs(
        [_report(1001, 2011), _report(1002, 2023, hispanic=1)],
        [_education(1003, 2011, 13)],
    )
    expected = _build(inputs)
    reordered = dataclasses.replace(
        inputs,
        reports=inputs.reports.iloc[::-1].reset_index(drop=True),
        education=inputs.education.iloc[::-1].reset_index(drop=True),
    )
    actual = _build(reordered, order)
    assert_frame_equal(actual.frame, expected.frame)
    assert {
        k: v
        for k, v in actual.provenance.items()
        if k != "input_frames_sha256"
    } == {
        k: v
        for k, v in expected.provenance.items()
        if k != "input_frames_sha256"
    }


@pytest.mark.parametrize("ids", [(), (1001, 1001), (9999,)])
def test_empty_duplicate_and_absent_requested_ids_are_refused(ids):
    with pytest.raises(ValueError):
        _build(_inputs(), ids)


@pytest.mark.parametrize("bad", [1001.5, 1001.0, "1001", True, None])
def test_requested_ids_require_exact_integer_type(bad):
    with pytest.raises(ValueError, match="integer"):
        _build(_inputs(universe=(1, 1001)), (bad,))


def test_numpy_integer_identifiers_are_accepted():
    result = _build(_inputs(), (np.int64(1001),), (np.int64(2011),))
    assert result.frame.person_id.tolist() == [1001]
    assert json.loads(json.dumps(result.provenance))["anchor_waves"] == [2011]


@pytest.mark.parametrize("waves", [(), (2010,), (2011.5,), ("2011",), (True,)])
def test_missing_unsupported_or_coerced_anchor_waves_are_refused(waves):
    with pytest.raises(ValueError):
        _build(_inputs(), waves=waves)


@pytest.mark.parametrize("name", ["reports", "education"])
def test_duplicate_person_wave_input_is_refused(name):
    inputs = _inputs([_report(1001, 2011)], [_education(1001, 2011, 12)])
    duplicated = pd.concat([getattr(inputs, name)] * 2, ignore_index=True)
    with pytest.raises(ValueError, match="more than one row"):
        _build(dataclasses.replace(inputs, **{name: duplicated}))


def test_builder_is_pure_and_independent_seals_bind_values_types_and_columns():
    inputs = _inputs([_report(1001, 2011)], [_education(1001, 2011, 12)])
    before = copy.deepcopy(inputs)
    digest = cohort.input_frames_sha256(inputs)
    result = _build(inputs)
    assert_frame_equal(inputs.reports, before.reports)
    assert_frame_equal(inputs.education, before.education)
    assert inputs.universe.equals(before.universe)
    assert inputs.provenance == before.provenance
    assert cohort.input_frames_sha256(inputs) == digest
    assert result.provenance["inputs"] == inputs.provenance
    assert (
        result.provenance["person_ids_sha256"]
        == hashlib.sha256(b"1001,1002,1003").hexdigest()
    )
    assert result.provenance["content_sha256"] == cohort.content_sha256(
        result.frame
    )
    assert result.provenance["content_sha256"] == _independent_frame_digest(
        "group_attributes", result.frame
    )
    changed = result.frame.copy()
    changed.loc[0, "education_years"] = 16
    assert (
        cohort.content_sha256(changed) != result.provenance["content_sha256"]
    )
    assert cohort.content_sha256(result.frame.iloc[:, ::-1]) != (
        result.provenance["content_sha256"]
    )
    changed = result.frame.astype({"education_years": "object"})
    assert (
        cohort.content_sha256(changed) != result.provenance["content_sha256"]
    )
    changed_inputs = dataclasses.replace(
        inputs, education=inputs.education.assign(education_code=16)
    )
    assert cohort.input_frames_sha256(changed_inputs) != digest


def _independent_frame_digest(name: str, frame: pd.DataFrame) -> str:
    digest = hashlib.sha256()
    digest.update(f"{name}\n".encode())
    digest.update(json.dumps([str(c) for c in frame.columns]).encode())
    digest.update(json.dumps([str(d) for d in frame.dtypes]).encode())
    digest.update(frame.to_csv(index=False, lineterminator="\n").encode())
    return digest.hexdigest()


def _write_loader_fixture(root: Path) -> dict:
    """INVENTED one-wave source, including a pinned fake source document."""

    wave = 2011
    individual = gap.INDIVIDUAL_ITEMS[wave]
    fields = [
        ("ER30001", 4, "1968 INTERVIEW NUMBER", [1, 1, 1]),
        ("ER30002", 3, "PERSON NUMBER 68", [1, 2, 3]),
    ]
    for item, values in (
        (individual.interview, [11, 11, 11]),
        (individual.sequence, [1, 2, 3]),
        (individual.relationship, [10, 20, 30]),
        (individual.education, [0, 16, 13]),
    ):
        fields.append((*item[:1], 4, item[1], values))
    write_product(root / "ind2023er", "IND2023ER.sps", "IND2023ER.txt", fields)
    formats = root / "ind2023er" / "IND2023ER_formats.sas"
    formats.write_text(
        f"VALUE {individual.education[0]}F\n"
        "0 = 'Inap.'\n1 - 17 = 'INVENTED grades'\n"
        "98 = 'DK'\n99 = 'NA'\n;\n"
        f"VALUE {individual.relationship[0]}F\n"
        "10 = 'Head in 2011'\n20 = 'Legal wife in 2011'\n"
        "22 = '\"Wife\"--partner'\n30 = 'Child'\n;\n"
        f"VALUE {individual.sequence[0]}F\n"
        "1 - 20 = 'INVENTED present family sequence'\n;\n"
    )
    family = gap.FAMILY_ITEMS[wave]
    family_values = {family.interview[0]: 11}
    for role, first_race in (("head", 1), ("spouse", 2)):
        family_values[family.hispanic[role][0]] = 0
        for mention, (variable, _) in enumerate(family.race[role], start=1):
            family_values[variable] = first_race if mention == 1 else 0
        family_values[family.completed_education[role][0]] = (
            0 if role == "head" else 16
        )
    fields = [
        (var, 4, label, [family_values[var]])
        for var, label in family.labels().items()
    ]
    write_product(
        root / "family" / "2011", "FAM2011ER.sps", "FAM2011ER.txt", fields
    )
    documentation = root / "documentation"
    documentation.mkdir()
    fake_document = documentation / "INVENTED-codebook.txt"
    fake_document.write_text("INVENTED source document for audit tests.\n")
    return {
        "schema_version": "psid_group_attribute_codebook.v1",
        "family": {
            "2011": {
                "codebook": {
                    "path": str(fake_document.relative_to(root)),
                    "sha256": hashlib.sha256(
                        fake_document.read_bytes()
                    ).hexdigest(),
                },
                "variables": {
                    var: {"values": [{"code": value, "label": "INVENTED"}]}
                    for var, value in family_values.items()
                    if var != family.interview[0]
                },
            }
        },
    }


def test_fixed_width_cohort_loader_audits_sources_and_retains_ofum(
    tmp_path, monkeypatch
):
    codebook = _write_loader_fixture(tmp_path)
    original_reader = gap.read_individual_items
    monkeypatch.setattr(gap, "load_codebook_values", lambda: codebook)
    monkeypatch.setattr(gap, "RACE_WAVES", (2011,))
    monkeypatch.setattr(
        gap,
        "read_individual_items",
        lambda *, data_dir: original_reader(data_dir=data_dir, waves=(2011,)),
    )
    inputs = cohort.load_group_attribute_inputs(psid_dir=tmp_path)
    result = _build(inputs)
    frame = result.frame.set_index("person_id")
    assert frame.loc[1001, "education_years"] == 0
    assert frame.loc[1002, "race_ethnicity_report4"] == "Black, non-hispanic"
    assert frame.loc[1003, "race_ethnicity_status"] == "never_head_or_spouse"
    assert frame.loc[1003, "education_years"] == 13
    assert inputs.provenance["input_frames_sha256"] == (
        cohort.input_frames_sha256(inputs)
    )
    expected_files = {
        "documentation/INVENTED-codebook.txt",
        "family/2011/FAM2011ER.sps",
        "family/2011/FAM2011ER.txt",
        "ind2023er/IND2023ER.sps",
        "ind2023er/IND2023ER.txt",
        "ind2023er/IND2023ER_formats.sas",
    }
    files = inputs.provenance["psid_files_sha256"]
    assert set(files) == expected_files
    for path, digest in files.items():
        assert (
            digest
            == hashlib.sha256((tmp_path / path).read_bytes()).hexdigest()
        )
    bundle = (
        json.dumps(files, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()
    assert (
        inputs.provenance["psid_files_bundle_sha256"]
        == hashlib.sha256(bundle).hexdigest()
    )


def test_custom_education_scheme_and_unresolved_bands_are_data_driven():
    spec = {
        "bands": [{"min": 0, "max": 11, "label": "INVENTED lower"}],
        "unresolved_bands": [
            {"min": 12, "max": None, "status": "INVENTED unsupported"}
        ],
    }
    frame = pd.DataFrame(
        {"education_years": pd.array([11, 12, pd.NA], dtype="Int64")},
        index=[9, 4, 7],
    )
    labels, statuses = cohort.apply_category_scheme(frame, "education", spec)
    assert labels.index.tolist() == [9, 4, 7]
    assert labels.iloc[0] == "INVENTED lower"
    assert labels.iloc[1:].isna().all()
    assert statuses.tolist() == [
        "assigned",
        "unresolved:INVENTED unsupported",
        "attribute_unknown",
    ]


@pytest.mark.parametrize("years", [12.5, 12.0, "12", True, -1, 18])
def test_category_mapping_refuses_nonintegral_or_unsupported_schooling(years):
    spec = {
        "bands": [{"min": 0, "max": 17, "label": "INVENTED supported"}],
        "unresolved_bands": [],
    }
    with pytest.raises(ValueError):
        cohort.apply_category_scheme(
            pd.DataFrame({"education_years": [years]}), "education", spec
        )


def test_every_attribute_traces_the_selected_source_and_mention():
    row = _build(
        _inputs(
            [
                _report(
                    1001, 2023, role="spouse", birth_state=0, year_came=1999
                )
            ],
            [_education(1001, 2011, 0, role="head", family_code=0)],
        ),
        (1001,),
    ).frame.iloc[0]
    items = gap.FAMILY_ITEMS[2023]
    assert row.race_ethnicity_source_role == "spouse"
    assert row.race_ethnicity_source_mentions == "1"
    assert row.hispanic_source_variables == items.hispanic["spouse"][0]
    assert row.hispanic_source_mentions == "direct_question"
    assert row.hispanic_source_wave == 2023
    assert row.education_source_role == "head"
    assert row.education_source_mentions == "individual|family_recode"
    assert row.country_of_birth_source_role == "spouse"
    assert row.country_of_birth_source_mentions == "birth_state|year_came"
    assert row.country_of_birth_source_variables == (
        items.birth_state["spouse"][0] + "|" + items.year_came["spouse"][0]
    )


def test_mutated_audited_inputs_are_refused():
    inputs = _inputs(education=[_education(1001, 2011, 12)])
    sealed = dataclasses.replace(
        inputs,
        provenance={"input_frames_sha256": cohort.input_frames_sha256(inputs)},
    )
    sealed.education.loc[0, "education_code"] = 16
    with pytest.raises(
        ValueError, match="changed after their provenance seal"
    ):
        _build(sealed)


@pytest.mark.parametrize(
    "ids,waves", [([1001.5], [2011]), ([1001], [2010]), ([], [2011])]
)
def test_loader_refuses_malformed_request_before_opening_psid(
    monkeypatch, ids, waves
):
    def forbidden(**kwargs):
        raise AssertionError("PSID opened for a malformed request")

    monkeypatch.setattr(cohort, "load_group_attribute_inputs", forbidden)
    with pytest.raises(ValueError):
        cohort.load_group_attributes(ids, anchor_waves=waves)


@pytest.mark.parametrize(
    "wave,admitted",
    [(1993, False), (1994, True), (2011, True), (2013, False), (2023, False)],
)
def test_supplied_education_codes_follow_reader_wave_domain(wave, admitted):
    inputs = _inputs(education=[_education(1001, wave, 98)])
    if admitted:
        row = _build(inputs, (1001,), (wave,)).frame.iloc[0]
        assert pd.isna(row.education_years)
        assert row.education_status == "dk_na_refused"
    else:
        with pytest.raises(ValueError, match="not documented"):
            _build(inputs, (1001,), (wave,))


@pytest.mark.parametrize(
    "wave,role,code,reason",
    [
        (2023, None, 0, "requires a head or spouse role"),
        (1992, "head", 0, "not asked"),
        (2023, "head", 18, "not documented"),
        (2023, "spouse", 98, "not documented"),
    ],
)
def test_supplied_family_education_requires_role_wave_and_domain(
    wave, role, code, reason
):
    inputs = _inputs(
        education=[_education(1001, wave, 0, role=role, family_code=code)]
    )
    with pytest.raises(ValueError, match=reason):
        _build(inputs, (1001,), (wave,))


@pytest.mark.parametrize("wave,code", [(1992, 0), (2023, 98)])
def test_supplied_report_family_education_requires_asked_documented_code(
    wave, code
):
    report = _report(1001, wave)
    report["family_education_code"] = code
    with pytest.raises(ValueError, match="not asked|not documented"):
        _build(_inputs([report]), (1001,), (wave,))


@pytest.mark.parametrize(
    "wave,role,year,admitted",
    [
        (2013, "head", 1900, False),
        (2013, "head", 2014, False),
        (2013, "head", 9998, True),
        (2023, "head", 1901, True),
        (2023, "spouse", 1901, False),
        (2023, "spouse", 1920, True),
        (2023, "head", 9998, False),
    ],
)
def test_supplied_birthplace_codes_follow_wave_and_role_domain(
    wave, role, year, admitted
):
    inputs = _inputs(
        [_report(1001, wave, role=role, birth_state=0, year_came=year)]
    )
    if admitted:
        row = _build(inputs, (1001,), (wave,)).frame.iloc[0]
        assert row.country_of_birth == "foreign_country"
    else:
        with pytest.raises(ValueError, match="not documented"):
            _build(inputs, (1001,), (wave,))


@pytest.mark.parametrize(
    "column,code",
    [
        ("birth_state_code", 57),
        ("year_came_code", -1),
        ("birth_state_code", pd.NA),
        ("year_came_code", pd.NA),
    ],
)
def test_supplied_birthplace_pairs_refuse_undocumented_or_blank_codes(
    column, code
):
    report = _report(1001, 2023)
    report[column] = code
    with pytest.raises(ValueError, match="not documented"):
        _build(_inputs([report]), (1001,), (2023,))


@pytest.mark.parametrize("column", ["birth_state_code", "year_came_code"])
def test_supplied_birthplace_codes_are_refused_before_question_exists(column):
    report = _report(1001, 2011)
    report[column] = 0
    with pytest.raises(ValueError, match="not asked"):
        _build(_inputs([report]), (1001,))


def test_supplied_domains_are_checked_even_after_education_cutoff():
    inputs = _inputs(education=[_education(1001, 2023, 98)])
    with pytest.raises(ValueError, match="not documented"):
        _build(inputs, (1001,), (2011,))
