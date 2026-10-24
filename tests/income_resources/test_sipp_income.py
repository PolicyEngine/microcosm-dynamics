"""Structure and invariant tests using invented SIPP-shaped records only.

Every file created here contains invented values generated from metadata
domains, never survey records. No staging directory is inspected.
"""

from __future__ import annotations

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
    income_variables,
    replicate_variables,
)

INVENTED_SAMPLE_UNIT_ID = "000000012345"
INVENTED_PROPERTY_SETTINGS = settings(
    max_examples=35,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)


def _invented_valid_value(concept: str, spec: SippVariable):
    """Choose a domain member without borrowing an individual record."""
    if concept == "sample_unit_id":
        return INVENTED_SAMPLE_UNIT_ID
    if concept == "weight" or spec.period == "weight":
        return 1234.25
    storage = getattr(spec, "storage_type", spec.predicate_type)

    def stored(number):
        return str(number) if storage == "string" else number

    preferred = {
        "person_number": 101,
        "month": 1,
        "wave": 1,
    }.get(concept)
    if preferred is not None and _domain_contains(spec, preferred):
        return stored(preferred)
    for code, _ in spec.items:
        number = Decimal(code)
        if number >= 0:
            return stored(int(number))
    ranges = getattr(spec, "domain_ranges", ()) or spec.ranges
    for low, high, _ in ranges:
        number = max(Decimal(low), Decimal(0))
        if number <= Decimal(high):
            return stored(int(number))
    if storage == "string":
        return "12345"
    if spec.items:
        return stored(int(Decimal(spec.items[0][0])))
    raise AssertionError(f"No invented domain member for {concept}")


def _domain_contains(spec: SippVariable, value) -> bool:
    """Independent exact-decimal domain check for invented test inputs."""
    number = Decimal(str(value))
    ranges = getattr(spec, "domain_ranges", ()) or spec.ranges
    return any(number == Decimal(code) for code, _ in spec.items) or any(
        Decimal(low) <= number <= Decimal(high) for low, high, _ in ranges
    )


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


@pytest.mark.parametrize("year", SIPP_INCOME_YEARS)
def test_every_verified_release_layout_and_source_codes(tmp_path, year):
    invented = _invented_row(year)
    path = _write_invented_file(tmp_path, year, [invented])
    out = sipp_income.read_sipp_income_months(year, path=path)
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


@pytest.mark.parametrize("concept", CORE_CONCEPTS)
def test_blank_required_core_refuses(tmp_path, concept):
    year = 2022
    row = _invented_row(year, **{concept: ""})
    path = _write_invented_file(tmp_path, year, [row], concepts=CORE_CONCEPTS)
    with pytest.raises(ValueError):
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
    year = 2022
    code = -9
    concept = "ssi_received_month"
    spec = income_variables(year)[concept]
    assert str(code) in dict(spec.items)
    path = _write_invented_file(
        tmp_path,
        year,
        [_invented_row(year, **{concept: code})],
        concepts=(*CORE_CONCEPTS, concept),
    )
    out = sipp_income.read_sipp_income_months(
        year, path=path, concepts=[concept]
    )
    assert out[concept].tolist() == [code]
    assert not out[concept].isna().any()


def test_amount_uses_its_own_sentinels(tmp_path):
    year = 2022
    concept = "ssi_amount"
    spec = income_variables(year)[concept]
    assert "-999" in dict(spec.items)
    assert not _domain_contains(spec, -9)
    path = _write_invented_file(
        tmp_path,
        year,
        [_invented_row(year, ssi_amount=-9)],
        concepts=(*CORE_CONCEPTS, concept),
    )
    with pytest.raises(ValueError, match="TSSI_AMT"):
        sipp_income.read_sipp_income_months(
            year, path=path, concepts=[concept]
        )
    path = _write_invented_file(
        tmp_path,
        year,
        [_invented_row(year, ssi_amount=-999)],
        concepts=(*CORE_CONCEPTS, concept),
    )
    out = sipp_income.read_sipp_income_months(
        year, path=path, concepts=[concept]
    )
    assert out[concept].tolist() == [-999]


def test_receipt_does_not_accept_amounts_missing_sentinel(tmp_path):
    year = 2022
    concept = "ssi_received_month"
    assert "-999" not in dict(income_variables(year)[concept].items)
    path = _write_invented_file(
        tmp_path,
        year,
        [_invented_row(year, **{concept: -999})],
        concepts=(*CORE_CONCEPTS, concept),
    )
    with pytest.raises(ValueError, match="RSSI_MNYN"):
        sipp_income.read_sipp_income_months(
            year, path=path, concepts=[concept]
        )


@pytest.mark.parametrize("year,value", ((2022, ""), (2018, ".")))
def test_verified_structural_blank_stays_missing(tmp_path, year, value):
    concept = "ssi_amount"
    assert income_variables(year)[concept].allow_blank
    path = _write_invented_file(
        tmp_path,
        year,
        [_invented_row(year, ssi_amount=value)],
        concepts=(*CORE_CONCEPTS, concept),
    )
    out = sipp_income.read_sipp_income_months(
        year, path=path, concepts=[concept]
    )
    assert out[concept].isna().all()


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


def test_entry_year_crosswalk_preserves_grouped_year_semantics(tmp_path):
    concept = "entry_year_code"
    early = income_variables(2022)[concept]
    late = income_variables(2025)[concept]
    assert early.name == late.name == "TYRENTRY"
    assert dict(early.items)["2016"] == "Recode for year 2015 to 2016"
    assert dict(late.items)["2016"] == "Year"
    assert code_label(2022, concept, 2016) != code_label(2025, concept, 2016)
    for year in (2022, 2025):
        path = _write_invented_file(
            tmp_path / f"INVENTED_{year}",
            year,
            [_invented_row(year, entry_year_code=2016)],
            concepts=(*CORE_CONCEPTS, concept),
        )
        out = sipp_income.read_sipp_income_months(
            year, path=path, concepts=[concept]
        )
        assert out[concept].tolist() == [2016]
        assert (
            out.attrs["sipp_variables"][concept]
            == income_variables(year)[concept]
        )


def test_entry_year_code_valid_in_2022_refuses_in_2025(tmp_path):
    concept = "entry_year_code"
    assert _domain_contains(income_variables(2022)[concept], 2022)
    assert not _domain_contains(income_variables(2025)[concept], 2022)
    path = _write_invented_file(
        tmp_path,
        2025,
        [_invented_row(2025, entry_year_code=2022)],
        concepts=(*CORE_CONCEPTS, concept),
    )
    with pytest.raises(ValueError, match="TYRENTRY"):
        sipp_income.read_sipp_income_months(
            2025, path=path, concepts=[concept]
        )


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


def test_ssi_annual_receipt_indeterminate_code_is_release_specific(tmp_path):
    concept = "ssi_received_year"
    for year in (2018, 2019):
        path = _write_invented_file(
            tmp_path / f"INVENTED_{year}",
            year,
            [_invented_row(year, **{concept: 9})],
            concepts=(*CORE_CONCEPTS, concept),
        )
        if year == 2018:
            with pytest.raises(ValueError, match="RSSI_YRYN"):
                sipp_income.read_sipp_income_months(
                    year, path=path, concepts=[concept]
                )
        else:
            out = sipp_income.read_sipp_income_months(
                year, path=path, concepts=[concept]
            )
            assert out[concept].tolist() == [9]
            assert "determined" in code_label(year, concept, 9).lower()


def test_retirement_distribution_sources_do_not_alias():
    unreported = "retirement_unreported_distribution_amount"
    ira = "ira_keogh_withdrawal_amount"
    for year in (2019, 2020):
        assert income_variables(year)[unreported].name == "TDRAW_AMT"
        assert ira not in income_variables(year)
    for year in range(2021, 2026):
        assert unreported not in income_variables(year)
        assert income_variables(year)[ira].name == "TIRA_INC_AMT"


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
        out[key].tolist() == [1234.25, 1234.25]
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


@pytest.mark.parametrize(
    "value",
    ("1.5", "1.0000000000000000000001", "NaN", "inf", "-inf", "garbage"),
)
def test_noninteger_nonfinite_and_garbage_receipt_codes_refuse(
    tmp_path, value
):
    year = 2022
    concept = "ssi_received_month"
    path = _write_invented_file(
        tmp_path,
        year,
        [_invented_row(year, **{concept: value})],
        concepts=(*CORE_CONCEPTS, concept),
    )
    with pytest.raises(ValueError, match="RSSI_MNYN"):
        sipp_income.read_sipp_income_months(
            year, path=path, concepts=[concept]
        )


def test_decimal_weight_just_above_verified_bound_refuses(tmp_path):
    year = 2022
    spec = income_variables(year)["weight"]
    ranges = getattr(spec, "domain_ranges", ()) or spec.ranges
    maximum = max(Decimal(high) for _, high, _ in ranges)
    value = str(maximum + Decimal("0.000000000001"))
    assert Decimal(value) > maximum
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
        items=(("-999", "Invented missing sentinel"),),
        ranges=(),
        ownership="invented",
        period="annual",
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
)
def test_property_person_identity_ignores_month_and_wave(
    tmp_path, months, person
):
    year = 2022
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
@given(st.integers(101, 120), st.integers(1, 12))
def test_property_same_panel_person_links_across_releases(
    tmp_path, person, month
):
    years = (2022, 2023)
    panels = [
        panel
        for panel in range(2018, 2024)
        if all(
            _domain_contains(income_variables(year)["panel"], panel)
            for year in years
        )
    ]
    assert panels
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


def test_same_sample_person_number_in_different_panels_has_distinct_id(
    tmp_path,
):
    year = 2022
    panel_spec = income_variables(year)["panel"]
    panels = [
        panel
        for panel in range(2018, 2023)
        if _domain_contains(panel_spec, panel)
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


@INVENTED_PROPERTY_SETTINGS
@given(st.lists(st.integers(0, 100000), min_size=1, max_size=12))
def test_property_monthly_weights_are_carried_unchanged(tmp_path, quarters):
    year = 2022
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


@INVENTED_PROPERTY_SETTINGS
@given(st.integers(min_value=3, max_value=10**9))
def test_property_unverified_finite_receipt_code_always_refuses(
    tmp_path, code
):
    year = 2022
    concept = "ssi_received_month"
    spec = income_variables(year)[concept]
    assert not _domain_contains(spec, code)
    path = _write_invented_file(
        tmp_path,
        year,
        [_invented_row(year, **{concept: code})],
        concepts=(*CORE_CONCEPTS, concept),
    )
    with pytest.raises(ValueError, match="RSSI_MNYN"):
        sipp_income.read_sipp_income_months(
            year, path=path, concepts=[concept]
        )
    with pytest.raises(ValueError, match="unverified categorical code"):
        code_label(year, concept, code)
