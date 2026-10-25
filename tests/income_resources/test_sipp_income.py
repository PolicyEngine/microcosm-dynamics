"""Structure and invariant tests using invented SIPP-shaped records only.

Every file written here holds INVENTED values chosen from registry
domains, never survey records, and no staging directory is read. The
helper ``_admits`` re-implements the registry's domain rule independently
so the reader can be checked against it (a differential test).
"""

from __future__ import annotations

import csv
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from populace_dynamics.data import sipp_income
from populace_dynamics.data.sipp_income_registry import (
    CORE_CONCEPTS,
    SIPP_INCOME_YEARS,
    SippVariable,
    code_label,
    corrected_on,
    income_variables,
    replicate_variables,
    user_notes,
)

#: Fourteen digits, the dictionaries' fixed width for SSUID.
INVENTED_SAMPLE_UNIT_ID = "00000000012345"
INVENTED_WEIGHT = 1234.25
#: A download date after Census's 2025-07-24 re-release of 2018-2021.
INVENTED_DOWNLOAD = "2026-10-24"
INVENTED_PROPERTY_SETTINGS = settings(
    max_examples=35,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
INVENTED_MISSING_LABELS = ("NA-Missing", "NA or Missing")


def _admits(spec: SippVariable, value) -> bool:
    """Independent statement of the domain rule, for differential tests.

    The primary source's missing codes stand for themselves; any other
    value must lie in every non-empty domain (primary and dictionary).
    """
    number = Decimal(str(value))
    missing = [
        Decimal(code)
        for code, label in spec.items
        if label in INVENTED_MISSING_LABELS
    ]
    if number in missing:
        return True
    primary = (
        [
            Decimal(code)
            for code, label in spec.items
            if label not in INVENTED_MISSING_LABELS
        ],
        [(Decimal(lo), Decimal(hi)) for lo, hi, _ in spec.ranges],
    )
    check = (
        [Decimal(code) for code, _ in spec.check_items],
        [(Decimal(lo), Decimal(hi)) for lo, hi, _ in spec.check_ranges],
    )
    domains = [domain for domain in (primary, check) if any(domain)]
    return bool(domains) and all(
        number in codes or any(lo <= number <= hi for lo, hi in spans)
        for codes, spans in domains
    )


def _integral(spec: SippVariable) -> bool:
    return spec.storage_type != "float" and spec.period != "weight"


def _well_formed(spec: SippVariable, token: str) -> bool:
    """Independent statement of the reader's token syntax."""
    if not token or not token.isascii():
        return False
    body = token[1:] if token.startswith("-") else token
    whole, _, fraction = body.partition(".")
    if not (whole + fraction).isdigit() or body.count(".") > 1:
        return False
    if not whole and not fraction:
        return False
    missing = [
        Decimal(code)
        for code, label in spec.items
        if label in INVENTED_MISSING_LABELS
    ]
    if spec.storage_type == "string" and Decimal(token) not in missing:
        return token.isdigit() and (
            not spec.length or len(token) == spec.length
        )
    return True


def _accepted_by_reader(spec: SippVariable, token: str) -> bool:
    """The reader's verdict on one invented token."""
    try:
        sipp_income.validate_sipp_values(
            pd.Series([token], dtype="string"), spec, year=2099
        )
    except ValueError:
        return False
    return True


def _candidates(concept: str, spec: SippVariable):
    preferred = {"person_number": 101, "month": 1, "wave": 1}.get(concept)
    if preferred is not None:
        yield preferred
    for code, label in (*spec.items, *spec.check_items):
        if label not in INVENTED_MISSING_LABELS and not code.startswith("-"):
            yield Decimal(code)
    for low, high, _ in (*spec.ranges, *spec.check_ranges):
        yield max(Decimal(low), Decimal(0))
        yield Decimal(high)


def _invented_valid_value(concept: str, spec: SippVariable):
    """Choose a value every verified source admits, not a survey record."""
    if concept == "sample_unit_id":
        return INVENTED_SAMPLE_UNIT_ID
    if spec.period == "weight":
        return INVENTED_WEIGHT
    for candidate in _candidates(concept, spec):
        number = Decimal(candidate)
        if _integral(spec) and number != number.to_integral_value():
            continue
        if _admits(spec, number):
            value = int(number) if _integral(spec) else float(number)
            if spec.storage_type == "string":
                return str(value).zfill(spec.length)
            return value
    raise AssertionError(f"No invented domain member for {concept}")


def _invented_row(year: int, **overrides) -> dict:
    table = income_variables(year)
    return {
        concept: overrides.get(concept, _invented_valid_value(concept, spec))
        for concept, spec in table.items()
    }


def _write_invented_file(
    directory: Path,
    year: int,
    rows: list[dict],
    *,
    concepts=None,
    filename=None,
    extra_columns=None,
) -> Path:
    """Write only the requested metadata layout, with invented values."""
    directory.mkdir(parents=True, exist_ok=True)
    table = income_variables(year)
    selected = list(table) if concepts is None else list(concepts)
    columns = [table[concept].name for concept in selected]
    records = [
        {table[concept].name: row[concept] for concept in selected}
        for row in rows
    ]
    frame = pd.DataFrame(records, columns=columns)
    for column, value in (extra_columns or {}).items():
        frame[column] = value
    path = directory / (filename or f"INVENTED_pu{year}.csv")
    frame.to_csv(path, index=False, sep="|")
    return path


def _write_invented_replicates(
    directory: Path,
    year: int,
    rows: list[dict],
    *,
    overrides=None,
) -> Path:
    """Write an invented replicate sidecar with the verified column names."""
    table = replicate_variables(year)
    records = []
    for row in rows:
        record = {}
        for concept, spec in table.items():
            value = (
                row[concept]
                if concept in row
                else (
                    row["weight"]
                    if concept == "replicate_weight_0"
                    else _invented_valid_value(concept, spec)
                )
            )
            record[spec.name] = (overrides or {}).get(concept, value)
        records.append(record)
    path = directory / f"INVENTED_replicate{year}.csv"
    pd.DataFrame(
        records, columns=[spec.name for spec in table.values()]
    ).to_csv(path, index=False, sep="|")
    return path


def _read_one(tmp_path, year, concept, value, **kwargs):
    """Read a one-row invented file holding ``value`` for ``concept``."""
    path = _write_invented_file(
        tmp_path / f"INVENTED_{year}_{concept}",
        year,
        [_invented_row(year, **{concept: value})],
        concepts=(*CORE_CONCEPTS, concept),
    )
    return sipp_income.read_sipp_income_months(
        year, path=path, concepts=[concept], **kwargs
    )


# Layout, selection and staging.


@pytest.mark.parametrize("year", SIPP_INCOME_YEARS)
def test_every_verified_release_layout_and_source_codes(tmp_path, year):
    invented = _invented_row(year)
    path = _write_invented_file(tmp_path, year, [invented])
    out = sipp_income.read_sipp_income_months(
        year, path=path, downloaded_on=INVENTED_DOWNLOAD
    )
    table = income_variables(year)
    assert len(out) == 1
    assert set(table) <= set(out.columns)
    assert out["release_year"].tolist() == [year]
    assert out["reference_year"].tolist() == [year - 1]
    assert out["sample_unit_id"].tolist() == [INVENTED_SAMPLE_UNIT_ID]
    assert pd.api.types.is_string_dtype(out["sample_unit_id"])
    assert pd.api.types.is_float_dtype(out["weight"])
    for concept in table:
        assert out.at[0, concept] == invented[concept], concept
    assert out.attrs["sipp_variables"] == table
    assert out.attrs["sipp_user_notes"] == {
        concept: user_notes(year, concept)
        for concept in table
        if user_notes(year, concept)
    }


def test_column_selection_uses_pipe_usecols_and_string_dtype(
    tmp_path, monkeypatch
):
    year = 2022
    selected = (*CORE_CONCEPTS, "ssi_received_month")
    path = _write_invented_file(
        tmp_path,
        year,
        [_invented_row(year)],
        concepts=selected,
        extra_columns={"INVENTED_UNUSED_COLUMN": "not numeric"},
    )
    original_read_csv = pd.read_csv
    calls = []

    def capture_read_csv(*args, **kwargs):
        calls.append(kwargs)
        return original_read_csv(*args, **kwargs)

    monkeypatch.setattr(sipp_income.pd, "read_csv", capture_read_csv)
    out = sipp_income.read_sipp_income_months(
        year, path=path, concepts=["ssi_received_month"]
    )
    assert len(out) == 1
    assert set(selected) <= set(out.columns)
    assert "ssi_amount" not in out
    assert "INVENTED_UNUSED_COLUMN" not in out
    body_calls = [call for call in calls if call.get("nrows") != 0]
    assert len(body_calls) == 1
    call = body_calls[0]
    assert call["sep"] == "|"
    assert call["quoting"] == csv.QUOTE_NONE
    wanted = {income_variables(year)[key].name for key in selected}
    usecols = call["usecols"]
    if callable(usecols):
        assert all(usecols(column) for column in wanted)
        assert not usecols("INVENTED_UNUSED_COLUMN")
    else:
        assert set(usecols) == wanted
    dtype = call["dtype"]
    assert dtype == "string" or dtype["SSUID"] in (str, "string")


@pytest.mark.parametrize("year", SIPP_INCOME_YEARS)
def test_core_only_selection_needs_no_optional_columns(tmp_path, year):
    path = _write_invented_file(
        tmp_path, year, [_invented_row(year)], concepts=CORE_CONCEPTS
    )
    out = sipp_income.read_sipp_income_months(year, path=path, concepts=[])
    assert set(out.columns) == {
        *CORE_CONCEPTS,
        "person_id",
        "household_id",
        "release_year",
        "reference_year",
    }


@pytest.mark.parametrize("year", (2017, 2026, "2022", 2022.5))
def test_unverified_release_refuses_before_file_access(monkeypatch, year):
    def unexpected_read(*args, **kwargs):
        pytest.fail("An unverified release must not open a data file")

    monkeypatch.setattr(sipp_income.pd, "read_csv", unexpected_read)
    with pytest.raises(ValueError, match="verified"):
        sipp_income.read_sipp_income_months(
            year, path="INVENTED_nonexistent.csv"
        )


@pytest.mark.parametrize("concepts", (["unverified_income"], ["TSSI_AMT"]))
def test_unverified_concept_refuses_before_file_access(monkeypatch, concepts):
    def unexpected_read(*args, **kwargs):
        pytest.fail("An unverified concept must not open a data file")

    monkeypatch.setattr(sipp_income.pd, "read_csv", unexpected_read)
    with pytest.raises(ValueError, match="unverified concept"):
        sipp_income.read_sipp_income_months(
            2022, path="INVENTED_nonexistent.csv", concepts=concepts
        )


def test_string_is_not_a_concept_list(tmp_path):
    with pytest.raises(ValueError, match="iterable"):
        sipp_income.read_sipp_income_months(
            2022, path=tmp_path / "INVENTED_missing.csv", concepts="weight"
        )


def test_missing_selected_column_refuses(tmp_path):
    year = 2022
    path = _write_invented_file(
        tmp_path, year, [_invented_row(year)], concepts=CORE_CONCEPTS
    )
    with pytest.raises(ValueError, match="missing required column"):
        sipp_income.read_sipp_income_months(
            year, path=path, concepts=["ssi_amount"]
        )


def test_default_requires_all_release_verified_columns(tmp_path):
    year = 2022
    path = _write_invented_file(
        tmp_path, year, [_invented_row(year)], concepts=CORE_CONCEPTS
    )
    with pytest.raises(ValueError, match="missing required column"):
        sipp_income.read_sipp_income_months(year, path=path)


@pytest.mark.parametrize("suffix", (".csv", ".csv.gz"))
def test_explicit_directory_overrides_environment(
    tmp_path, monkeypatch, suffix
):
    year = 2022
    staged = tmp_path / "INVENTED_EXPLICIT_STAGE"
    path = _write_invented_file(
        staged,
        year,
        [_invented_row(year)],
        concepts=CORE_CONCEPTS,
        filename=f"pu{year}{suffix}",
    )
    monkeypatch.setenv(
        "POPULACE_DYNAMICS_SIPP_DIR", str(tmp_path / "INVENTED_MISSING")
    )
    assert path.is_file()
    out = sipp_income.read_sipp_income_months(
        year, data_dir=staged, concepts=[]
    )
    assert out["sample_unit_id"].tolist() == [INVENTED_SAMPLE_UNIT_ID]


def test_gzip_environment_staging(tmp_path, monkeypatch):
    year = 2022
    staged = tmp_path / "INVENTED_ENVIRONMENT_STAGE"
    _write_invented_file(
        staged,
        year,
        [_invented_row(year)],
        concepts=CORE_CONCEPTS,
        filename=f"pu{year}.csv.gz",
    )
    monkeypatch.setenv("POPULACE_DYNAMICS_SIPP_DIR", str(staged))
    out = sipp_income.read_sipp_income_months(year, concepts=[])
    assert len(out) == 1


def test_filename_year_must_agree(tmp_path):
    path = _write_invented_file(
        tmp_path / "INVENTED_STAGE",
        2022,
        [_invented_row(2022)],
        concepts=CORE_CONCEPTS,
        filename="pu2023.csv",
    )
    with pytest.raises(ValueError, match="year"):
        sipp_income.read_sipp_income_months(2022, path=path, concepts=[])


# Codes, sentinels and blanks.


@pytest.mark.parametrize("concept", CORE_CONCEPTS)
def test_blank_required_core_refuses(tmp_path, concept):
    year = 2022
    row = _invented_row(year, **{concept: ""})
    path = _write_invented_file(tmp_path, year, [row], concepts=CORE_CONCEPTS)
    with pytest.raises(ValueError):
        sipp_income.read_sipp_income_months(year, path=path, concepts=[])


#: Every documented missing code of a structural key or the weight.
INVENTED_KEY_MISSING_CODES = [
    (year, concept, code)
    for year in SIPP_INCOME_YEARS
    for concept, spec in income_variables(year).items()
    if concept in CORE_CONCEPTS
    for code, label in spec.items
    if label in INVENTED_MISSING_LABELS
]


def test_every_api_release_documents_a_weight_missing_code():
    assert {
        year
        for year, concept, _ in INVENTED_KEY_MISSING_CODES
        if concept == "weight"
    } == {2022, 2023, 2024, 2025}


@pytest.mark.parametrize("year,concept,code", INVENTED_KEY_MISSING_CODES)
def test_documented_missing_code_in_a_key_or_weight_refuses(
    tmp_path, year, concept, code
):
    """A missing code never enters as an identifier or a weight."""
    path = _write_invented_file(
        tmp_path,
        year,
        [_invented_row(year, **{concept: code})],
        concepts=CORE_CONCEPTS,
    )
    with pytest.raises(ValueError, match="missing structural key or weight"):
        sipp_income.read_sipp_income_months(year, path=path, concepts=[])


@pytest.mark.parametrize("value", (-9, -999, ".", "not_an_id"))
def test_invalid_month_cannot_become_a_missing_or_default(tmp_path, value):
    year = 2022
    path = _write_invented_file(
        tmp_path,
        year,
        [_invented_row(year, month=value)],
        concepts=CORE_CONCEPTS,
    )
    with pytest.raises(ValueError):
        sipp_income.read_sipp_income_months(year, path=path, concepts=[])


def test_documented_receipt_missing_code_remains_raw(tmp_path):
    year, concept = 2022, "ssi_received_month"
    assert "-9" in dict(income_variables(year)[concept].items)
    out = _read_one(tmp_path, year, concept, -9)
    assert out[concept].tolist() == [-9]
    assert not out[concept].isna().any()


def test_amount_uses_its_own_sentinels(tmp_path):
    year, concept = 2022, "ssi_amount"
    spec = income_variables(year)[concept]
    assert "-999" in dict(spec.items)
    assert not _admits(spec, -9)
    with pytest.raises(ValueError, match="TSSI_AMT"):
        _read_one(tmp_path, year, concept, -9)
    assert _read_one(tmp_path, year, concept, -999)[concept].tolist() == [-999]


def test_receipt_does_not_accept_amounts_missing_sentinel(tmp_path):
    year, concept = 2022, "ssi_received_month"
    assert "-999" not in dict(income_variables(year)[concept].items)
    with pytest.raises(ValueError, match="RSSI_MNYN"):
        _read_one(tmp_path, year, concept, -999)


@pytest.mark.parametrize("year,value", ((2022, ""), (2018, ".")))
def test_verified_structural_blank_stays_missing(tmp_path, year, value):
    concept = "ssi_amount"
    assert income_variables(year)[concept].allow_blank
    assert _read_one(tmp_path, year, concept, value)[concept].isna().all()


def test_numeric_dot_blank_is_only_for_releases_that_document_it(tmp_path):
    concept = "ssi_amount"
    assert "." not in income_variables(2022)[concept].structural_missing
    with pytest.raises(ValueError, match="TSSI_AMT"):
        _read_one(tmp_path, 2022, concept, ".")


@pytest.mark.parametrize(
    "value",
    ("1.5", "1.0000000000000000000001", "NaN", "inf", "-inf", "garbage"),
)
def test_noninteger_nonfinite_and_garbage_receipt_codes_refuse(
    tmp_path, value
):
    with pytest.raises(ValueError, match="RSSI_MNYN"):
        _read_one(tmp_path, 2022, "ssi_received_month", value)


def test_decimal_weight_just_above_verified_bound_refuses(tmp_path):
    year = 2022
    spec = income_variables(year)["weight"]
    maximum = min(
        max(Decimal(high) for _, high, _ in ranges)
        for ranges in (spec.ranges, spec.check_ranges)
        if ranges
    )
    value = str(maximum + Decimal("0.000000000001"))
    assert not _admits(spec, value)
    path = _write_invented_file(
        tmp_path,
        year,
        [_invented_row(year, weight=value)],
        concepts=CORE_CONCEPTS,
    )
    with pytest.raises(ValueError, match="WPFINWGT"):
        sipp_income.read_sipp_income_months(year, path=path, concepts=[])


@pytest.mark.parametrize("allow_blank", (True, False))
def test_opaque_string_structural_blank_follows_explicit_contract(allow_blank):
    invented_spec = SippVariable(
        name="INVENTED_OPAQUE_ID",
        label="Invented optional identifier",
        predicate_type="string",
        items=(("-999", "NA-Missing"),),
        ranges=(),
        ownership="invented",
        period="interview",
        source="INVENTED_METADATA",
        allow_blank=allow_blank,
        storage_type="string",
    )
    values = pd.Series(["0001", "", "-999"], dtype="string")
    if allow_blank:
        out = sipp_income.validate_sipp_values(
            values, invented_spec, year=2022
        )
        assert out.iloc[0] == "0001"
        assert pd.isna(out.iloc[1])
        assert out.iloc[2] == "-999"
    else:
        with pytest.raises(ValueError, match="INVENTED_OPAQUE_ID"):
            sipp_income.validate_sipp_values(values, invented_spec, year=2022)


# Both Census sources for a release must admit a value.


@pytest.mark.parametrize("year", (2022, 2023, 2024, 2025))
@pytest.mark.parametrize(
    "concept,inside,outside",
    (
        ("half_sample", (1, 2), (0, 3)),
        ("variance_stratum", (1, 240), (0, 241)),
    ),
)
def test_design_codes_come_from_the_dictionary_when_the_api_has_none(
    tmp_path, year, concept, inside, outside
):
    spec = income_variables(year)[concept]
    assert all(label == "NA-Missing" for _, label in spec.items)
    assert spec.check_source == (
        f"{year}_dictionary_variables.json#{spec.name}"
    )
    # Census stores both as strings; the reader keeps the token verbatim.
    assert spec.storage_type == "string"
    for value in inside:
        token = str(value).zfill(spec.length)
        out = _read_one(tmp_path, year, concept, token)
        assert out[concept].tolist() == [token]
        if token != str(value):
            with pytest.raises(ValueError, match=spec.name):
                _read_one(tmp_path, year, concept, str(value))
    for value in outside:
        with pytest.raises(ValueError, match=spec.name):
            _read_one(tmp_path, year, concept, str(value).zfill(spec.length))


def test_value_one_source_admits_but_the_other_does_not_refuses(tmp_path):
    year, concept = 2023, "education_savings_1_owner"
    spec = income_variables(year)[concept]
    # The API documents 70-499; the dictionary only 70 and 101-499.
    assert [(lo, hi) for lo, hi, _ in spec.ranges] == [("70", "499")]
    assert dict(spec.check_items) == {"70": "Someone outside the household"}
    assert code_label(year, concept, 70) == "Someone outside the household"
    for value in (70, 101, 499):
        assert _read_one(tmp_path, year, concept, value)[concept].tolist() == [
            value
        ]
    for value in (80, 100, 500):
        with pytest.raises(ValueError, match="EESAV1OWNER"):
            _read_one(tmp_path, year, concept, value)


# Release-specific meanings and refusals (the crosswalk).


def test_entry_year_crosswalk_preserves_grouped_year_semantics(tmp_path):
    concept = "entry_year_code"
    early = income_variables(2022)[concept]
    late = income_variables(2025)[concept]
    assert early.name == late.name == "TYRENTRY"
    assert code_label(2022, concept, 2016) == "Recode for year 2015 to 2016"
    assert code_label(2025, concept, 2016) == "Year"
    for year in (2022, 2025):
        out = _read_one(tmp_path, year, concept, 2016)
        assert out[concept].tolist() == [2016]
        assert out.attrs["sipp_variables"][concept] == (
            income_variables(year)[concept]
        )


def test_entry_year_code_valid_in_2022_refuses_in_2025(tmp_path):
    concept = "entry_year_code"
    assert _admits(income_variables(2022)[concept], 2022)
    assert not _admits(income_variables(2025)[concept], 2022)
    with pytest.raises(ValueError, match="TYRENTRY"):
        _read_one(tmp_path, 2025, concept, 2022)


def test_suppressed_roster_variable_refuses_instead_of_using_previous_year():
    concept = "roster_relationship_15"
    assert income_variables(2024)[concept].name == "RREL15"
    assert concept not in income_variables(2025)
    with pytest.raises(ValueError, match="unverified concept"):
        sipp_income.read_sipp_income_months(
            2025, path="INVENTED_nonexistent.csv", concepts=[concept]
        )


def test_employer_offer_question_starts_in_2021():
    concept = "employer_retirement_plan_offered"
    for year in (2018, 2019, 2020):
        assert concept not in income_variables(year)
        with pytest.raises(ValueError, match="unverified concept"):
            sipp_income.read_sipp_income_months(
                year, path="INVENTED_nonexistent.csv", concepts=[concept]
            )
    for year in range(2021, 2026):
        assert income_variables(year)[concept].name == "EPENSNYN"
        assert (
            income_variables(year)["employer_retirement_plan_participation"]
        ).name == "EINCPENS"


def test_ssi_annual_receipt_indeterminate_code_is_release_specific(tmp_path):
    concept = "ssi_received_year"
    with pytest.raises(ValueError, match="RSSI_YRYN"):
        _read_one(tmp_path, 2018, concept, 9)
    out = _read_one(tmp_path, 2019, concept, 9)
    assert out[concept].tolist() == [9]
    assert "determined" in code_label(2019, concept, 9).lower()
    titles = [title for title, _ in user_notes(2019, concept)]
    assert any("Inconsistent SSI Receipt" in title for title in titles)


def test_ssi_begin_reason_is_refused_where_code_meanings_conflict():
    concept = "ssi_begin_reason"
    for year in (2018, 2019, 2020, 2023, 2024, 2025):
        assert code_label(year, concept, 1) == "Blind or disabled"
        assert code_label(year, concept, 2) == "Aged (65 or over)"
    for year in (2021, 2022):
        assert concept not in income_variables(year)
        with pytest.raises(ValueError, match="unverified concept"):
            code_label(year, concept, 1)


def test_label_conflicts_follow_their_rulings():
    spouse = income_variables(2018)["other_real_estate_joint_spouse_owned"]
    assert spouse.label_source == "user_note"
    assert spouse.universe_source == (
        "source_rulings.json#label_conflicts/2018/EJSOWNRE"
    )
    assert "with a spouse or civil union partner" in spouse.label
    assert "without a spouse" in spouse.schema_label
    for concept in (
        "disability_source_6_amount",
        "disability_source_8_received_month",
    ):
        assert concept not in income_variables(2020)


def test_2020_joint_holdings_are_refused_but_recodes_stay():
    joint = (
        "checking_joint_spouse_owned",
        "checking_joint_other_value",
        "credit_card_joint_spouse_debt",
    )
    for concept in joint:
        assert concept not in income_variables(2020)
        assert concept in income_variables(2019)
        assert concept in income_variables(2021)
    for concept in ("bank_assets_value", "net_worth", "household_net_worth"):
        assert concept in income_variables(2020)


def test_retirement_distribution_sources_do_not_alias():
    unreported = "retirement_unreported_distribution_amount"
    ira = "ira_keogh_withdrawal_amount"
    for year in (2019, 2020):
        assert income_variables(year)[unreported].name == "TDRAW_AMT"
        assert ira not in income_variables(year)
    for year in range(2021, 2026):
        assert unreported not in income_variables(year)
        assert income_variables(year)[ira].name == "TIRA_INC_AMT"


def test_universe_travels_with_each_release():
    concept = "retirement_received_year"
    assert income_variables(2020)[concept].universe == "EEVERET = 1"
    assert "EPENANY=2" in income_variables(2021)[concept].universe
    assert "EPENANY ne 1" in income_variables(2022)[concept].universe
    assert "other retirement income" in income_variables(2023)[concept].label


# The correction re-release of 2018-2021.


@pytest.mark.parametrize("year", (2018, 2019, 2020, 2021))
def test_corrected_social_security_needs_a_post_correction_download(
    tmp_path, monkeypatch, year
):
    concept = "social_security_amount"
    assert corrected_on(year, concept) == "2025-07-24"

    def unexpected_read(*args, **kwargs):
        pytest.fail("A vintage refusal must not open a data file")

    monkeypatch.setattr(sipp_income.pd, "read_csv", unexpected_read)
    for downloaded_on in (None, "2025-07-23", date(2024, 1, 1)):
        with pytest.raises(ValueError, match="TSSSAMT|corrected|predate"):
            sipp_income.read_sipp_income_months(
                year,
                path="INVENTED_nonexistent.csv",
                concepts=[concept],
                downloaded_on=downloaded_on,
            )


@pytest.mark.parametrize("downloaded_on", ("2025-07-24", date(2026, 10, 24)))
def test_corrected_social_security_reads_after_the_correction(
    tmp_path, downloaded_on
):
    out = _read_one(
        tmp_path,
        2019,
        "social_security_amount",
        100,
        downloaded_on=downloaded_on,
    )
    assert out["social_security_amount"].tolist() == [100]
    assert out.attrs["sipp_corrected_on"] == {
        "social_security_amount": "2025-07-24"
    }


def test_uncorrected_concepts_and_releases_need_no_download_date(tmp_path):
    assert corrected_on(2022, "social_security_amount") is None
    assert _read_one(tmp_path, 2022, "social_security_amount", 100)[
        "social_security_amount"
    ].tolist() == [100]
    out = _read_one(tmp_path, 2019, "ssi_amount", 100)
    assert out.attrs["sipp_corrected_on"] == {}


def test_download_date_must_be_a_date():
    with pytest.raises(ValueError, match="date"):
        sipp_income.read_sipp_income_months(
            2019,
            path="INVENTED_nonexistent.csv",
            concepts=["social_security_amount"],
            downloaded_on=20250724,
        )


# Keys, linkage and replicate weights.


def test_duplicate_person_month_refuses_even_if_wave_changes(tmp_path):
    year = 2022
    path = _write_invented_file(
        tmp_path,
        year,
        [_invented_row(year, wave=1), _invented_row(year, wave=2)],
        concepts=CORE_CONCEPTS,
    )
    with pytest.raises(ValueError, match="duplicate person-month"):
        sipp_income.read_sipp_income_months(year, path=path, concepts=[])


def test_person_key_is_stable_when_monthly_household_changes(tmp_path):
    year = 2022
    address = _invented_row(year)["monthly_address_id"]
    next_address = str(int(address) + 1)
    path = _write_invented_file(
        tmp_path,
        year,
        [
            _invented_row(year, month=1, monthly_address_id=address),
            _invented_row(year, month=2, monthly_address_id=next_address),
        ],
        concepts=CORE_CONCEPTS,
    )
    out = sipp_income.read_sipp_income_months(year, path=path, concepts=[])
    assert out["person_id"].nunique() == 1
    assert out["household_id"].nunique() == 2


@pytest.mark.parametrize("year", SIPP_INCOME_YEARS)
def test_all_replicate_weights_attach_without_changing_roster(tmp_path, year):
    rows = [_invented_row(year, month=2), _invented_row(year, month=1)]
    path = _write_invented_file(tmp_path, year, rows, concepts=CORE_CONCEPTS)
    replicate_path = _write_invented_replicates(
        tmp_path, year, rows[::-1], overrides={"replicate_weight_1": 4321.5}
    )
    out = sipp_income.read_sipp_income_months(
        year, path=path, concepts=[], replicate_path=replicate_path
    )
    assert len(out) == 2
    assert out["month"].tolist() == [2, 1]
    assert out["replicate_weight_0"].tolist() == out["weight"].tolist()
    assert out["replicate_weight_1"].tolist() == [4321.5, 4321.5]
    weights = [key for key in out if key.startswith("replicate_weight_")]
    assert set(weights) == {f"replicate_weight_{i}" for i in range(241)}
    assert all(pd.api.types.is_float_dtype(out[key]) for key in weights)
    assert all(
        out[key].tolist() == [INVENTED_WEIGHT, INVENTED_WEIGHT]
        for key in weights
        if key not in ("replicate_weight_0", "replicate_weight_1")
    )


@pytest.mark.parametrize("problem", ("duplicate", "incomplete", "base"))
def test_invalid_replicate_linkage_or_base_weight_refuses(tmp_path, problem):
    year = 2022
    rows = [_invented_row(year, month=1), _invented_row(year, month=2)]
    path = _write_invented_file(tmp_path, year, rows, concepts=CORE_CONCEPTS)
    replica_rows = rows + [rows[0]] if problem == "duplicate" else rows
    if problem == "incomplete":
        replica_rows = rows[:1]
    overrides = {"replicate_weight_0": 123.5} if problem == "base" else {}
    replicate_path = _write_invented_replicates(
        tmp_path, year, replica_rows, overrides=overrides
    )
    with pytest.raises(ValueError, match="replicate"):
        sipp_income.read_sipp_income_months(
            year, path=path, concepts=[], replicate_path=replicate_path
        )


def test_unused_replicate_rows_never_expand_roster(tmp_path):
    year = 2022
    row = _invented_row(year, month=1)
    path = _write_invented_file(tmp_path, year, [row], concepts=CORE_CONCEPTS)
    replicate_path = _write_invented_replicates(
        tmp_path, year, [row, _invented_row(year, month=2)]
    )
    out = sipp_income.read_sipp_income_months(
        year, path=path, concepts=[], replicate_path=replicate_path
    )
    assert out["month"].tolist() == [1]


def test_blank_replicate_weight_refuses(tmp_path):
    year = 2022
    rows = [_invented_row(year)]
    path = _write_invented_file(tmp_path, year, rows, concepts=CORE_CONCEPTS)
    replicate_path = _write_invented_replicates(
        tmp_path, year, rows, overrides={"replicate_weight_3": ""}
    )
    with pytest.raises(ValueError, match="REPWGT3"):
        sipp_income.read_sipp_income_months(
            year, path=path, concepts=[], replicate_path=replicate_path
        )


def test_replicate_filename_year_refuses_before_opening_data(
    tmp_path, monkeypatch
):
    def unexpected_read(*args, **kwargs):
        pytest.fail("A mismatched replicate year must not open data")

    monkeypatch.setattr(sipp_income.pd, "read_csv", unexpected_read)
    with pytest.raises(ValueError, match="replicate filename"):
        sipp_income.read_sipp_income_months(
            2022,
            path=tmp_path / "INVENTED_nonexistent.csv",
            concepts=[],
            replicate_path=tmp_path / "INVENTED_STAGE" / "rw2023.csv",
        )


def test_same_sample_person_number_in_different_panels_has_distinct_id(
    tmp_path,
):
    year = 2022
    panel_spec = income_variables(year)["panel"]
    panels = [
        panel for panel in range(2018, 2023) if _admits(panel_spec, panel)
    ]
    assert len(panels) >= 2
    rows = [_invented_row(year, panel=panel) for panel in panels[:2]]
    path = _write_invented_file(tmp_path, year, rows, concepts=CORE_CONCEPTS)
    out = sipp_income.read_sipp_income_months(year, path=path, concepts=[])
    assert out["person_id"].nunique() == 2
    assert out["household_id"].nunique() == 2
    replicate_path = _write_invented_replicates(tmp_path, year, rows[:1])
    with pytest.raises(ValueError, match="replicate"):
        sipp_income.read_sipp_income_months(
            year, path=path, concepts=[], replicate_path=replicate_path
        )


# File layout and token spelling.


def _invented_lines(year, rows=2):
    """A valid invented header and rows for the core layout."""
    table = income_variables(year)
    header = "|".join(table[concept].name for concept in CORE_CONCEPTS)
    lines = [
        "|".join(
            str(_invented_row(year, month=month)[concept])
            for concept in CORE_CONCEPTS
        )
        for month in range(1, rows + 1)
    ]
    return header, lines


@pytest.mark.parametrize("problem", ("short", "long", "blank"))
def test_rows_whose_field_count_differs_refuse(tmp_path, problem):
    year = 2022
    header, lines = _invented_lines(year)
    if problem == "short":
        lines[1] = lines[1].rsplit("|", 1)[0]
    elif problem == "long":
        lines[1] = lines[1] + "|INVENTED_EXTRA"
    else:
        lines.append("")
    path = tmp_path / "INVENTED_layout.csv"
    path.write_text("\n".join([header, *lines]) + "\n")
    with pytest.raises(ValueError, match="line 3 has .* fields|line 4 has"):
        sipp_income.read_sipp_income_months(year, path=path, concepts=[])


def test_short_trailing_fields_never_become_structural_blanks(tmp_path):
    """The reviewer's case: optional columns after the last core key."""
    year = 2022
    concept = "ssi_amount"
    path = _write_invented_file(
        tmp_path,
        year,
        [_invented_row(year, month=1), _invented_row(year, month=2)],
        concepts=(*CORE_CONCEPTS, concept),
    )
    lines = path.read_text().splitlines()
    lines[2] = lines[2].rsplit("|", 1)[0]
    path.write_text("\n".join(lines) + "\n")
    with pytest.raises(ValueError, match="fields"):
        sipp_income.read_sipp_income_months(
            year, path=path, concepts=[concept]
        )


def test_quotes_in_an_unselected_field_never_join_physical_records(tmp_path):
    """The minimized review regression, using two invented monthly rows."""
    year = 2022
    header, lines = _invented_lines(year)
    path = tmp_path / "INVENTED_multiline_quote.csv"
    path.write_text(
        "\n".join(
            [header + "|INVENTED_UNUSED", *(line + '|"' for line in lines)]
        )
        + "\n"
    )
    out = sipp_income.read_sipp_income_months(year, path=path, concepts=[])
    assert len(out) == len(lines)
    assert out["month"].tolist() == [1, 2]


def test_repeated_header_name_refuses(tmp_path):
    year = 2022
    header, lines = _invented_lines(year, rows=1)
    path = tmp_path / "INVENTED_repeat.csv"
    path.write_text(
        "\n".join([header + "|TSSI_AMT|TSSI_AMT", lines[0] + "|1|2"]) + "\n"
    )
    with pytest.raises(ValueError, match="repeats a column name"):
        sipp_income.read_sipp_income_months(
            year, path=path, concepts=["ssi_amount"]
        )


def test_layout_check_reads_gzip(tmp_path):
    year = 2022
    path = _write_invented_file(
        tmp_path,
        year,
        [_invented_row(year)],
        concepts=CORE_CONCEPTS,
        filename=f"pu{year}.csv.gz",
    )
    assert (
        len(sipp_income.read_sipp_income_months(year, path=path, concepts=[]))
        == 1
    )
    path.write_bytes(path.read_bytes()[:20])
    with pytest.raises(ValueError, match="unreadable or truncated"):
        sipp_income.read_sipp_income_months(year, path=path, concepts=[])


@pytest.mark.parametrize(
    "concept,value",
    (
        ("sample_unit_id", "12345"),
        ("sample_unit_id", "000000012345"),
        ("sample_unit_id", " 00000000012345"),
        ("sample_unit_id", "+0000000012345"),
        ("sample_unit_id", "1.2345E4"),
        ("household_id_at_interview", "11"),
        ("household_id_at_interview", "+11"),
        ("monthly_address_id", "100001.0"),
        ("month", "+1"),
        ("month", "1E0"),
        ("month", "0_1"),
        ("weight", "1_234.25"),
    ),
)
def test_odd_spellings_of_keys_refuse(tmp_path, concept, value):
    year = 2022
    path = _write_invented_file(
        tmp_path,
        year,
        [_invented_row(year, **{concept: value})],
        concepts=CORE_CONCEPTS,
    )
    with pytest.raises(ValueError) as caught:
        sipp_income.read_sipp_income_months(year, path=path, concepts=[])
    # Refusals name the variable, never the record value.
    assert value.strip() not in str(caught.value)


@pytest.mark.parametrize("year", (2022, 2025))
@pytest.mark.parametrize(
    "concept", ("citizen", "born_us", "half_sample", "variance_stratum")
)
def test_blank_refuses_where_the_universe_is_everyone(tmp_path, year, concept):
    spec = income_variables(year)[concept]
    assert spec.universe in ("All persons", "All households")
    assert not spec.allow_blank
    with pytest.raises(ValueError, match=spec.name):
        _read_one(tmp_path, year, concept, "")


def test_blank_stays_missing_where_the_universe_is_a_subset(tmp_path):
    spec = income_variables(2022)["ssi_amount"]
    assert spec.universe not in ("All persons", "All households")
    assert (
        _read_one(tmp_path, 2022, "ssi_amount", "")["ssi_amount"].isna().all()
    )


def test_download_date_accepts_a_datetime(tmp_path):
    out = _read_one(
        tmp_path,
        2019,
        "social_security_amount",
        100,
        downloaded_on=datetime(2026, 1, 1, 12, 0),
    )
    assert out["social_security_amount"].tolist() == [100]


# Property tests (Hypothesis) on invented data.


@INVENTED_PROPERTY_SETTINGS
@given(
    st.sampled_from((2018, 2019, 2020, 2021)),
    st.one_of(st.integers(-3000, 3000), st.sampled_from((-1, 0, 1))),
    st.sampled_from(("date", "datetime", "string", "absent")),
)
def test_property_corrected_vintage_gate_matches_download_date(
    tmp_path, year, offset, representation
):
    """The correction date is inclusive; stale or absent vintages refuse."""
    fixed = date(2025, 7, 24)
    when = fixed + timedelta(days=offset)
    downloaded_on = {
        "date": when,
        "datetime": datetime.combine(when, datetime.min.time()),
        "string": when.isoformat(),
        "absent": None,
    }[representation]
    if downloaded_on is None or when < fixed:
        # An unopened path also proves that the vintage gate runs first.
        with pytest.raises(ValueError, match="corrected|predate"):
            sipp_income.read_sipp_income_months(
                year,
                path=tmp_path / "INVENTED_absent_vintage.csv",
                concepts=["social_security_amount"],
                downloaded_on=downloaded_on,
            )
    else:
        out = _read_one(
            tmp_path,
            year,
            "social_security_amount",
            100,
            downloaded_on=downloaded_on,
        )
        assert out["social_security_amount"].tolist() == [100]


@pytest.mark.parametrize("placement", ("selected", "unselected", "both"))
@INVENTED_PROPERTY_SETTINGS
@given(
    st.sampled_from(SIPP_INCOME_YEARS),
    st.lists(
        st.text(alphabet='"abc012 ', max_size=8).map(lambda text: '"' + text),
        min_size=2,
        max_size=12,
    ),
    st.sampled_from(CORE_CONCEPTS),
)
def test_property_quotes_preserve_physical_records_or_refuse(
    tmp_path, placement, year, tokens, selected_concept
):
    """Quotes in selected and unselected fields never swallow a row."""
    table = income_variables(year)
    header, lines = _invented_lines(year, rows=len(tokens))
    records = [line.split("|") for line in lines]
    if placement in ("selected", "both"):
        position = CORE_CONCEPTS.index(selected_concept)
        for fields, token in zip(records, tokens, strict=True):
            fields[position] = token
    for fields, token in zip(records, tokens, strict=True):
        fields.append(token if placement in ("unselected", "both") else "0")
    path = tmp_path / "INVENTED_generated_quotes.csv"
    path.write_text(
        "\n".join(
            [header + "|INVENTED_UNUSED", *("|".join(row) for row in records)]
        )
        + "\n"
    )
    if placement in ("selected", "both"):
        # Every core field has a numeric or fixed-width digit domain.
        with pytest.raises(ValueError, match=table[selected_concept].name):
            sipp_income.read_sipp_income_months(year, path=path, concepts=[])
    else:
        out = sipp_income.read_sipp_income_months(year, path=path, concepts=[])
        assert len(out) == len(records)
        assert out["month"].tolist() == list(range(1, len(records) + 1))


@pytest.mark.parametrize("problem", ("short", "long", "blank", "header"))
@INVENTED_PROPERTY_SETTINGS
@given(
    st.sampled_from(SIPP_INCOME_YEARS),
    st.integers(1, 12),
    st.data(),
)
def test_property_malformed_physical_layout_refuses(
    tmp_path, problem, year, count, data
):
    """Any altered field count or repeated header refuses before parsing."""
    header, lines = _invented_lines(year, rows=count)
    row_index = data.draw(st.integers(0, count - 1))
    fields = lines[row_index].split("|")
    if problem == "header":
        header += "|" + data.draw(st.sampled_from(header.split("|")))
        lines = [line + "|INVENTED_EXTRA" for line in lines]
        message = "repeats a column name"
    else:
        if problem == "short":
            del fields[data.draw(st.integers(0, len(fields) - 1))]
        elif problem == "long":
            fields.insert(
                data.draw(st.integers(0, len(fields))), "INVENTED_EXTRA"
            )
        else:
            fields = [""]
        lines[row_index] = "|".join(fields)
        message = "fields"
    path = tmp_path / "INVENTED_generated_bad_layout.csv"
    path.write_text("\n".join([header, *lines]) + "\n")
    with pytest.raises(ValueError, match=message):
        sipp_income.read_sipp_income_months(year, path=path, concepts=[])


@pytest.mark.parametrize(
    "problem", ("duplicate", "incomplete", "missing", "ambiguous", "base")
)
@INVENTED_PROPERTY_SETTINGS
@given(
    st.lists(
        st.tuples(st.integers(101, 120), st.integers(1, 12)),
        unique=True,
        min_size=2,
        max_size=8,
    ),
    st.integers(1, 100000),
    st.data(),
)
def test_property_invalid_replicate_keys_or_base_weight_refuse(
    tmp_path, problem, keys, quarters, data
):
    """Sidecars must link completely, uniquely and with the same weight."""
    year = 2022
    rows = [
        _invented_row(
            year, person_number=person, month=month, weight=quarters / 4
        )
        for person, month in keys
    ]
    chosen = data.draw(st.integers(0, len(rows) - 1))
    replica_rows = list(rows)
    overrides = {}
    message = "replicate"
    if problem == "duplicate":
        replica_rows.append(rows[chosen])
    elif problem == "incomplete":
        del replica_rows[chosen]
    elif problem == "missing":
        concept = data.draw(
            st.sampled_from(("sample_unit_id", "person_number", "month"))
        )
        replica_rows[chosen] = rows[chosen] | {concept: ""}
        message = ".*"
    elif problem == "ambiguous":
        panel = next(
            panel
            for panel in range(2018, year + 1)
            if panel != rows[chosen]["panel"]
            and _admits(income_variables(year)["panel"], panel)
        )
        rows.append(rows[chosen] | {"panel": panel})
        message = "ambiguous replicate linkage keys"
    else:
        overrides["replicate_weight_0"] = quarters / 4 + 0.25
    path = _write_invented_file(tmp_path, year, rows, concepts=CORE_CONCEPTS)
    replicate_path = _write_invented_replicates(
        tmp_path, year, replica_rows, overrides=overrides
    )
    with pytest.raises(ValueError, match=message):
        sipp_income.read_sipp_income_months(
            year, path=path, concepts=[], replicate_path=replicate_path
        )


@INVENTED_PROPERTY_SETTINGS
@given(
    st.lists(
        st.tuples(st.integers(101, 120), st.integers(1, 12)),
        unique=True,
        max_size=24,
    )
)
def test_property_roster_count_and_input_order_are_preserved(tmp_path, keys):
    year = 2022
    rows = [
        _invented_row(year, person_number=person, month=month)
        for person, month in keys
    ]
    path = _write_invented_file(tmp_path, year, rows, concepts=CORE_CONCEPTS)
    out = sipp_income.read_sipp_income_months(year, path=path, concepts=[])
    assert len(out) == len(keys)
    assert list(zip(out["person_number"], out["month"], strict=True)) == keys


@INVENTED_PROPERTY_SETTINGS
@given(
    st.lists(st.integers(1, 12), unique=True, min_size=1, max_size=12),
    st.integers(101, 120),
    st.sampled_from(SIPP_INCOME_YEARS),
)
def test_property_person_identity_ignores_month_and_wave(
    tmp_path, months, person, year
):
    rows = [
        _invented_row(year, person_number=person, month=month, wave=1 + i % 2)
        for i, month in enumerate(months)
    ]
    path = _write_invented_file(tmp_path, year, rows, concepts=CORE_CONCEPTS)
    out = sipp_income.read_sipp_income_months(year, path=path, concepts=[])
    panel = rows[0]["panel"]
    assert out["person_id"].tolist() == [
        f"{panel}:{INVENTED_SAMPLE_UNIT_ID}:{person}"
    ] * len(rows)


@INVENTED_PROPERTY_SETTINGS
@given(
    st.integers(101, 120),
    st.integers(1, 12),
    st.sampled_from(
        [
            (year, year + 1)
            for year in SIPP_INCOME_YEARS[:-1]
            if any(
                _admits(income_variables(year)["panel"], panel)
                and _admits(income_variables(year + 1)["panel"], panel)
                for panel in range(2018, 2026)
            )
        ]
    ),
)
def test_property_same_panel_person_links_across_releases(
    tmp_path, person, month, years
):
    panels = [
        panel
        for panel in range(2018, 2026)
        if all(
            _admits(income_variables(year)["panel"], panel) for year in years
        )
    ]
    identifiers = []
    for year in years:
        row = _invented_row(
            year, panel=panels[0], person_number=person, month=month
        )
        path = _write_invented_file(
            tmp_path / f"INVENTED_{year}",
            year,
            [row],
            concepts=CORE_CONCEPTS,
        )
        out = sipp_income.read_sipp_income_months(year, path=path, concepts=[])
        identifiers.append(out.at[0, "person_id"])
    assert identifiers[0] == identifiers[1]


@INVENTED_PROPERTY_SETTINGS
@given(
    st.lists(st.integers(0, 4 * 10**6), min_size=1, max_size=12),
    st.sampled_from(SIPP_INCOME_YEARS),
)
def test_property_monthly_weights_are_carried_unchanged(
    tmp_path, quarters, year
):
    weights = [quarter / 4 for quarter in quarters]
    rows = [
        _invented_row(year, month=i + 1, weight=weight)
        | {
            "replicate_weight_1": weight + 0.25,
            "replicate_weight_240": weight + 0.5,
        }
        for i, weight in enumerate(weights)
    ]
    path = _write_invented_file(tmp_path, year, rows, concepts=CORE_CONCEPTS)
    replicate_path = _write_invented_replicates(tmp_path, year, rows)
    out = sipp_income.read_sipp_income_months(
        year, path=path, concepts=[], replicate_path=replicate_path
    )
    assert out["weight"].tolist() == weights
    assert out["replicate_weight_0"].tolist() == weights
    assert out["replicate_weight_1"].tolist() == [w + 0.25 for w in weights]
    assert out["replicate_weight_240"].tolist() == [w + 0.5 for w in weights]


#: Every admitted (release, concept) whose values are numeric codes only.
INVENTED_CATEGORICAL = [
    (year, concept)
    for year in SIPP_INCOME_YEARS
    for concept, spec in income_variables(year).items()
    if spec.storage_type != "string"
    and not spec.ranges
    and not spec.check_ranges
    and spec.items
]
#: Every admitted (release, concept) with a documented domain.
INVENTED_NUMERIC = [
    (year, concept)
    for year in SIPP_INCOME_YEARS
    for concept, spec in income_variables(year).items()
    if spec.ranges or spec.check_ranges or spec.items or spec.check_items
]
#: Spellings Decimal() accepts but the reader must refuse.
INVENTED_ODD_SPELLINGS = (
    "+1",
    "1E0",
    "1e2",
    "1_0",
    " 1",
    "1 ",
    "\uff11",
    "0x1",
    "1.2.3",
    "--1",
    ".",
    "-",
)


def _edge_tokens(spec: SippVariable):
    """Domain edges and their neighbours, as strings."""
    points = set()
    for code, _ in (*spec.items, *spec.check_items):
        points.add(Decimal(code))
    for low, high, _ in (*spec.ranges, *spec.check_ranges):
        points.update({Decimal(low), Decimal(high)})
    return sorted(
        {
            str(point + delta)
            for point in points
            for delta in (Decimal(-1), Decimal(0), Decimal(1))
        }
    )


@settings(max_examples=400, deadline=None)
@given(st.sampled_from(INVENTED_NUMERIC), st.data())
def test_property_reader_domain_matches_independent_rule(case, data):
    """Differential: the reader admits exactly what ``_admits`` admits."""
    year, concept = case
    spec = income_variables(year)[concept]
    width = spec.length or 1
    token = data.draw(
        st.one_of(
            st.sampled_from(_edge_tokens(spec)),
            st.integers(-(10**12), 10**12).map(str),
            st.integers(0, 10**width - 1).map(lambda n: str(n).zfill(width)),
            st.sampled_from(INVENTED_ODD_SPELLINGS),
        )
    )
    if token in spec.structural_missing:
        # A documented blank ("." before 2022) is a not-in-universe value.
        assert _accepted_by_reader(spec, token) == spec.allow_blank
        return
    expected = _well_formed(spec, token)
    if expected:
        number = Decimal(token)
        expected = _admits(spec, number) and (
            not _integral(spec) or number == number.to_integral_value()
        )
    assert _accepted_by_reader(spec, token) == expected, token
