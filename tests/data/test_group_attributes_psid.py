"""INVENTED fixed-width fixtures and pinned documentation checks.

The committed ``data/external`` table supplies code domains, never
microdata. Fixture persons and all their answers are INVENTED. Invariants:
labels and domains are checked before interpretation; role joins preserve
OFUMs in the individual roster but attach family answers only to present
heads/spouses; ambiguous or absent answers never become negative answers.
"""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.data import group_attributes_psid as gap
from tests.data.psid_fixtures import write_product


def _write_individual(root: Path, wave: int = 2023) -> Path:
    items = gap.INDIVIDUAL_ITEMS[wave]
    fields = [
        ("ER30001", 5, "1968 INTERVIEW NUMBER", [1] * 5),
        ("ER30002", 3, "PERSON NUMBER 68", [1, 2, 3, 4, 5]),
        (*items.interview, [101, 101, 101, 202, 303]),
        (*items.sequence, [1, 2, 3, 2, 81]),
        (*items.relationship, [10, 20, 30, 22, 10]),
        (*items.education, [17, 0, 99, 12, 0]),
    ]
    # The first two tuples already contain width; remaining tuples do not.
    fields = [
        field if len(field) == 4 else (field[0], 4, field[1], field[2])
        for field in fields
    ]
    directory = root / "ind2023er"
    write_product(directory, "IND2023ER.sps", "IND2023ER.txt", fields)
    edu, rel, seq = (
        items.education[0],
        items.relationship[0],
        items.sequence[0],
    )
    # Domains and role descriptions of this synthetic product are INVENTED
    # documentation matching the reader's adjudicated frame.
    dk = "98 = 'DK'\n" if 1994 <= wave <= 2011 else ""
    formats = (
        f"VALUE {edu}F\n1 - 17 = 'Grades'\n{dk}"
        "99 = 'NA'\n0 = 'Inap.'\n;\n"
        f"VALUE {rel}F\n10 = 'Head in {wave}'\n"
        f"20 = 'Legal wife in {wave}'\n"
        "22 = '\"Wife\"--cohabitor'\n30 = 'Child'\n0 = 'Inap.'\n;\n"
        f"VALUE {seq}F\n1 - 20 = 'Present'\n"
        "51 - 59 = 'Institution'\n71 - 89 = 'Absent'\n0 = 'Inap.'\n;\n"
    )
    target = directory / "IND2023ER_formats.sas"
    target.write_text(formats)
    return target


def _write_family(root: Path, wave: int = 2023) -> Path:
    items = gap.FAMILY_ITEMS[wave]
    values = {variable: [0, 0] for variable in items.labels()}
    values[items.interview[0]] = [101, 202]
    for role in gap.ROLES:
        values[items.race[role][0][0]] = [1, 2]
        if items.completed_education:
            values[items.completed_education[role][0]] = [0, 12]
        if items.birth_state:
            values[items.birth_state[role][0]] = [1, 0]
            values[items.year_came[role][0]] = [0, 1999]
    fields = [
        (variable, 5, label, values[variable])
        for variable, label in items.labels().items()
    ]
    directory = root / "family" / str(wave)
    write_product(directory, "FAM.sps", "FAM.txt", fields)
    return directory / "FAM.sps"


def test_fixed_width_reader_and_role_join(tmp_path):
    _write_individual(tmp_path)
    _write_family(tmp_path)
    individual = gap.read_individual_items(data_dir=tmp_path, waves=(2023,))
    family = gap.read_family_items(2023, data_dir=tmp_path)
    reports = gap.head_spouse_reports(individual, {2023: family})
    assert len(individual) == 5
    assert reports["person_id"].tolist() == [1001, 1002, 1004]
    assert reports["role"].tolist() == ["head", "spouse", "spouse"]
    assert reports["race_code_1"].tolist() == [1, 1, 2]
    assert all(
        reports[column].dtype == "Int64" for column in gap.REPORT_CODE_COLUMNS
    )
    # OFUM education remains available without a fabricated family role.
    assert (
        individual.loc[individual.person_id == 1003, "education_code"].item()
        == 99
    )
    assert gap.education_report(
        0, reports.loc[1, "family_education_code"]
    ) == (
        0,
        "no_grades",
    )


@pytest.mark.parametrize("kind", ["individual", "family"])
def test_label_mismatch_refused_before_data_read(tmp_path, monkeypatch, kind):
    _write_individual(tmp_path)
    family_sps = _write_family(tmp_path)
    if kind == "individual":
        target = tmp_path / "ind2023er" / "IND2023ER.sps"
        target.write_text(
            target.read_text().replace(
                "YEARS COMPLETED EDUCATION 23", "WRONG LABEL"
            )
        )

        def call():
            return gap.read_individual_items(data_dir=tmp_path, waves=(2023,))

    else:
        family_sps.write_text(
            family_sps.read_text().replace(
                "L39 SPANISH DESCENT-RP", "WRONG LABEL"
            )
        )

        def call():
            return gap.read_family_items(2023, data_dir=tmp_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("fixed-width data opened before label check")

    monkeypatch.setattr(pd, "read_fwf", forbidden)
    with pytest.raises(ValueError, match="label"):
        call()


@pytest.mark.parametrize(
    "concept,code", [("education", 18), ("relationship", 11), ("sequence", 21)]
)
def test_individual_undocumented_codes_refused(tmp_path, concept, code):
    _write_individual(tmp_path)
    variable = getattr(gap.INDIVIDUAL_ITEMS[2023], concept)[0]
    # Rewrite the INVENTED fixture through its explicit SPSS colspecs.
    sps = tmp_path / "ind2023er" / "IND2023ER.sps"
    from populace_dynamics.data import psid

    spec = psid.parse_sps_layout(sps).set_index("name").loc[variable]
    txt = sps.with_suffix(".txt")
    lines = txt.read_text().splitlines()
    start, end = int(spec.start) - 1, int(spec.end)
    lines[0] = lines[0][:start] + f"{code:>{end - start}}" + lines[0][end:]
    txt.write_text("\n".join(lines) + "\n")
    with pytest.raises(ValueError, match="not documented"):
        gap.read_individual_items(data_dir=tmp_path, waves=(2023,))


def test_family_undocumented_code_and_duplicate_interview_refused(tmp_path):
    sps = _write_family(tmp_path)
    txt = sps.with_suffix(".txt")
    rows = txt.read_text().splitlines()
    rows[0] = rows[0][:5] + "    6" + rows[0][10:]
    txt.write_text("\n".join(rows) + "\n")
    with pytest.raises(ValueError, match="not documented"):
        gap.read_family_items(2023, data_dir=tmp_path)
    _write_family(tmp_path)
    rows = txt.read_text().splitlines()
    rows[1] = rows[0][:5] + rows[1][5:]
    txt.write_text("\n".join(rows) + "\n")
    with pytest.raises(ValueError, match="duplicate interview"):
        gap.read_family_items(2023, data_dir=tmp_path)


def test_family_formats_disagreement_refused(tmp_path):
    _write_family(tmp_path)
    variable = gap.FAMILY_ITEMS[2023].hispanic["head"][0]
    (tmp_path / "family" / "2023" / "FAM_formats.sas").write_text(
        f"VALUE {variable}F\n0 = 'Negative'\n1 = 'Positive'\n;\n"
    )
    with pytest.raises(ValueError, match="formats file documents"):
        gap.read_family_items(2023, data_dir=tmp_path)


def test_missing_family_and_duplicate_role_refused(tmp_path):
    _write_individual(tmp_path)
    _write_family(tmp_path)
    individual = gap.read_individual_items(data_dir=tmp_path, waves=(2023,))
    family = gap.read_family_items(2023, data_dir=tmp_path)
    with pytest.raises(ValueError, match="no family-file row"):
        gap.head_spouse_reports(individual, {2023: family.iloc[:1]})
    individual.loc[individual.person_id == 1003, "relationship"] = 10
    with pytest.raises(ValueError, match="share a family's head"):
        gap.head_spouse_reports(individual, {2023: family})


def _invented_multiwave_join_inputs(rows):
    """An INVENTED interleaved roster and family answers for join tests."""

    waves = (1985, 1993, 2005, 2023)
    individual = pd.DataFrame(
        [
            {
                "person_id": position + 1001,
                "wave": wave,
                "interview": position + 101,
                "sequence": sequence,
                "relationship": relationship,
                "education_code": 12,
            }
            for position, (wave, relationship, sequence) in enumerate(rows)
        ],
        columns=[
            "person_id",
            "wave",
            "interview",
            "sequence",
            "relationship",
            "education_code",
        ],
        dtype="int64",
    )
    # The partition must preserve selection and alignment with these
    # nonconsecutive, decreasing input labels.
    individual.index = range(7 * len(individual), 0, -7)
    families = {}
    for wave in waves:
        items = gap.FAMILY_ITEMS[wave]
        interviews = individual.loc[
            individual["wave"] == wave, "interview"
        ].tolist()
        values = {
            variable: [0] * len(interviews) for variable in items.labels()
        }
        values[items.interview[0]] = interviews
        for role in gap.ROLES:
            values[items.race[role][0][0]] = [1] * len(interviews)
            if items.completed_education:
                values[items.completed_education[role][0]] = [12] * len(
                    interviews
                )
            if items.birth_state:
                values[items.birth_state[role][0]] = [1] * len(interviews)
        families[wave] = pd.DataFrame(values, dtype="int64").rename(
            columns={items.interview[0]: "interview"}
        )
    return individual, families


def _whole_frame_mask_reference(individual, families):
    """The original whole-roster masks with independent row-based joins."""

    result = []
    for wave, family in sorted(families.items()):
        selected = individual[
            (individual["wave"] == wave)
            & individual["sequence"].between(*gap.IN_FAMILY_SEQUENCE)
        ]
        family_by_interview = family.set_index("interview")
        for person in selected.itertuples(index=False):
            if person.relationship == gap.HEAD_RELATIONSHIP:
                role = "head"
            elif person.relationship in gap.SPOUSE_RELATIONSHIPS:
                role = "spouse"
            else:
                continue
            row = dict.fromkeys(gap.REPORT_CODE_COLUMNS, pd.NA)
            row.update(person_id=person.person_id, wave=wave, role=role)
            family_row = family_by_interview.loc[person.interview]
            for variable, column in (
                gap.FAMILY_ITEMS[wave].role_columns(role).items()
            ):
                row[column] = int(family_row[variable])
            result.append(row)
    frame = pd.DataFrame(
        result,
        columns=["person_id", "wave", "role", *gap.REPORT_CODE_COLUMNS],
    )
    frame = frame.astype(
        {
            "person_id": "int64",
            "wave": "int64",
            "role": "string",
            **dict.fromkeys(gap.REPORT_CODE_COLUMNS, "Int64"),
        }
    )
    return frame.sort_values(["person_id", "wave"]).reset_index(drop=True)


@settings(max_examples=40, deadline=None)
@given(
    st.lists(
        st.tuples(
            st.sampled_from((1985, 1993, 2005, 2023)),
            st.sampled_from((10, 20, 22, 30)),
            st.sampled_from((1, 20, 51, 81)),
        ),
        max_size=24,
    )
)
def test_wave_partition_differential_preserves_whole_frame_masks(rows):
    individual, families = _invented_multiwave_join_inputs(rows)
    expected = _whole_frame_mask_reference(individual, families)
    actual = gap.head_spouse_reports(individual, families)
    pd.testing.assert_frame_equal(actual, expected)


def test_wave_partition_preserves_missing_wave_and_empty_role_outputs():
    individual, families = _invented_multiwave_join_inputs(
        [(2023, 10, 1), (2005, 30, 1), (1993, 20, 81)]
    )
    expected = _whole_frame_mask_reference(individual, families)
    actual = gap.head_spouse_reports(individual, families)
    pd.testing.assert_frame_equal(actual, expected)
    assert actual["person_id"].tolist() == [1001]


def test_domains_pinned_and_all_documented_race_codes_mean_something():
    expected_path = (
        Path(__file__).resolve().parents[2]
        / "data"
        / "external"
        / "psid_group_attribute_codebook_values_v1.json"
    )
    assert gap.CODEBOOK_VALUES_PATH == expected_path
    table = gap.load_codebook_values()
    assert (
        hashlib.sha256(gap.CODEBOOK_VALUES_PATH.read_bytes()).hexdigest()
        == gap.CODEBOOK_VALUES_SHA256
    )
    for wave, items in gap.FAMILY_ITEMS.items():
        for role in gap.ROLES:
            for mention, (variable, label) in enumerate(items.race[role], 1):
                entry = table["family"][str(wave)]["variables"][variable]
                assert entry["label"] == " ".join(label.split())
                domain = gap.documented_domain(table, wave, variable)
                for code in domain.normalized()[0]:
                    assert gap.race_mention_meaning(wave, mention, code) in (
                        *gap.RACE_CATEGORIES,
                        gap.MISSING,
                        gap.LATINO_ORIGIN,
                        gap.NO_FURTHER_MENTION,
                    )


@pytest.mark.parametrize("wave", [1994, 1995, 1996])
def test_ambiguous_spouse_zero_remains_unknown(wave):
    head = gap.race_ethnicity_report(wave, 0, (1, 0, 0), role="head")
    spouse = gap.race_ethnicity_report(wave, 0, (1, 0, 0), role="spouse")
    assert head.hispanic is False
    assert spouse.hispanic is None
    assert not spouse.complete
    assert spouse.hispanic_basis == "undocumented_zero_meaning"


def test_wave_specific_race_and_missing_origin():
    assert gap.race_mention_meaning(1993, 1, 5) == gap.LATINO_ORIGIN
    assert gap.race_mention_meaning(2005, 1, 5) == gap.PACIFIC_ISLANDER
    assert gap.race_mention_meaning(1993, 2, 8) == gap.MORE_THAN_TWO
    assert gap.race_mention_meaning(1994, 2, 8) == gap.MISSING
    assert gap.race_ethnicity_report(1997, None, (1, 0, 0, 0)).hispanic is None
    assert gap.race_ethnicity_report(1997, None, (5, 0, 0, 0)).hispanic is True
    assert gap.race_ethnicity_report(2023, 1, (9, 0, 0, 0)).complete
    assert gap.race_ethnicity_report(2023, 0, (9, 0, 0, 0)).races is None


@pytest.mark.parametrize(
    "codes",
    [(1,), (1, None, 0, 0), (1, 6, 0, 0), (1, 9, 0, 0), (1, 0, 0, 0, 0)],
)
def test_incomplete_or_undocumented_mentions_refused(codes):
    with pytest.raises(ValueError):
        gap.race_ethnicity_report(2023, 0, codes)


def test_unasked_origin_and_modern_undocumented_origin_refused():
    with pytest.raises(ValueError, match="asks_hispanic_origin"):
        gap.race_ethnicity_report(1997, 0, (1, 0, 0, 0))
    with pytest.raises(ValueError, match="undocumented code"):
        gap.race_ethnicity_report(2023, 6, (1, 0, 0, 0))


@given(st.integers(1, 17))
def test_education_codes_preserve_years_and_never_impute(code):
    assert gap.education_report(code) == (code, "reported")
    assert gap.education_report(code, 99) == (code, "reported")
    assert gap.education_report(0) == (None, "inapplicable")
    assert gap.education_report(0, 99) == (None, "inapplicable")
    assert gap.education_report(0, 0) == (0, "no_grades")


@pytest.mark.parametrize(
    "value", [True, 1.0, 1.5, "1", float("nan"), float("inf")]
)
def test_numeric_codes_must_be_integers(value):
    for call in (
        lambda: gap.education_report(value),
        lambda: gap.hispanic_meaning(value),
        lambda: gap.race_mention_meaning(2023, 1, value),
        lambda: gap.birthplace_class(value, 0),
    ):
        with pytest.raises(ValueError):
            call()


@pytest.mark.parametrize("code", [-1, 18, 98, 100])
def test_undocumented_family_education_refused(code):
    with pytest.raises(ValueError, match="family education"):
        gap.education_report(12, code)


@given(st.integers(1, 56), st.integers(1901, 2023))
def test_birthplace_pair_respects_skip_pattern(state, came):
    assert gap.birthplace_class(state, 0) == gap.UNITED_STATES
    assert gap.birthplace_class(state, came) == gap.INCONSISTENT
    assert gap.birthplace_class(0, 0) == gap.US_TERRITORY
    assert gap.birthplace_class(0, came) == gap.FOREIGN_COUNTRY


def test_birthplace_missing_and_invalid_year():
    assert gap.birthplace_class(99, 0) == gap.MISSING
    assert gap.birthplace_class(99, 1999) == gap.INCONSISTENT
    assert gap.birthplace_class(0, 9999) == gap.FOREIGN_COUNTRY
    with pytest.raises(ValueError, match="year-came"):
        gap.birthplace_class(0, -1)


@given(
    st.sets(st.integers(-10, 10)),
    st.lists(
        st.tuples(st.integers(-10, 10), st.integers(-10, 10)), max_size=5
    ),
    st.integers(-15, 15),
)
def test_domain_representations_differential(singles, ranges, value):
    intervals = tuple((min(lo, hi), max(lo, hi)) for lo, hi in ranges)
    domain = gap.CodeDomain(frozenset(singles), intervals)
    expected = value in singles or any(
        lo <= value <= hi for lo, hi in intervals
    )
    assert domain.contains(value) is expected
    expanded = gap.CodeDomain(domain.normalized()[0])
    assert domain.same_as(expanded)
    assert expanded.contains(value) is expected


def test_sas_domains_preserve_ranges_and_reject_truncation(tmp_path):
    path = tmp_path / "formats.sas"
    path.write_text(
        "VALUE EXAMPLE\n1 - 17 = 'Grades'\n99 = 'NA'\n0 = 'Inap.'\n;\n"
    )
    parsed = gap.parse_sas_value_domains(path)["EXAMPLE"]
    assert parsed.same_as(gap.CodeDomain(frozenset({0, 99}), ((1, 17),)))
    path.write_text(path.read_text().removesuffix(";\n"))
    with pytest.raises(ValueError, match="Unterminated"):
        gap.parse_sas_value_domains(path)


def test_codebook_extraction_continuations_and_page_locator():
    script = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "build_group_attribute_codebook_values.py"
    )
    spec = importlib.util.spec_from_file_location(
        "group_codebook_builder", script
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    text = (
        'ER00001 "INVENTED LABEL"\nQuestion?\n'
        " Count % Value/Range Code Value/Range Text\n"
        " 1 10.0 1 - 17 Grades\n"
        " continuation\nPage 1 of 2\n\f"
        "PANEL STUDY OF INCOME DYNAMICS\n"
        " 1 10.0 99 NA\n 1 10.0 0 Inap.\n"
        'ER00002 "NEXT INVENTED LABEL"\n'
    )
    entry = module.extract_entry(text, "ER00001")
    assert entry == {
        "label": "INVENTED LABEL",
        "page": 1,
        "values": [
            {"range": [1, 17], "text": "Grades continuation"},
            {"code": 99, "text": "NA"},
            {"code": 0, "text": "Inap."},
        ],
    }


def test_source_pins_refuse_changed_documentation(tmp_path):
    pdf = tmp_path / "INVENTED.pdf"
    pdf.write_bytes(b"INVENTED source documentation")
    sha = hashlib.sha256(pdf.read_bytes()).hexdigest()
    table = {
        "family": {"2023": {"codebook": {"path": pdf.name, "sha256": sha}}}
    }
    assert gap.verify_codebook_pins(
        (2023,), data_dir=tmp_path, codebook=table
    ) == {2023: sha}
    pdf.write_bytes(b"changed INVENTED source documentation")
    with pytest.raises(ValueError, match="pins"):
        gap.verify_codebook_pins((2023,), data_dir=tmp_path, codebook=table)
