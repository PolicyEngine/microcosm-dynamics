"""Tests for the OSHA ITA establishment microdata reader."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from populace_dynamics.data import osha_ita

REAL_DATA = osha_ita.firm_data_dir()
needs_real_ita = pytest.mark.skipif(
    not (REAL_DATA / "ITA_300A_Summary_Data_2025.csv").exists(),
    reason="OSHA ITA file not staged",
)


def _write_ita(directory: Path, year: int, rows: list[dict]) -> Path:
    """Write a fixture OSHA ITA summary CSV.

    ``total_hours_worked`` defaults to 2,000 h per employee — a plausible
    full-year figure — so a row is never *accidentally* flagged
    hours-implausible. Tests that want that flag set the hours
    explicitly.
    """
    directory.mkdir(parents=True, exist_ok=True)
    defaults = {
        "ein": "123456789",
        "company_name": "ACME CORP",
        "establishment_name": "ACME PLANT 1",
        "state": "OH",
        "naics_code": "332999",
        "annual_average_employees": 120,
        "establishment_type": 1,
        "year_filing_for": year,
    }
    records = []
    for row in rows:
        record = {**defaults, **row}
        record.setdefault(
            "total_hours_worked", record["annual_average_employees"] * 2_000
        )
        records.append(record)
    frame = pd.DataFrame(records)
    path = directory / f"ITA_300A_Summary_Data_{year}.csv"
    frame.to_csv(path, index=False)
    return path


def test_missing_file_names_the_staging_hint(tmp_path):
    with pytest.raises(FileNotFoundError, match="POPULACE_DYNAMICS_FIRM_DIR"):
        osha_ita.read_ita(2025, tmp_path)


def test_missing_column_fails_loudly(tmp_path):
    pd.DataFrame([{"ein": "1", "state": "OH"}]).to_csv(
        tmp_path / "ITA_300A_Summary_Data_2025.csv", index=False
    )
    with pytest.raises(ValueError, match="missing columns"):
        osha_ita.read_ita(2025, tmp_path)


def test_read_applies_no_cleaning(tmp_path):
    """The raw counts must survive read_ita untouched.

    Cleaning inside the loader would bury a choice that moves the
    national total by 32%.
    """
    _write_ita(
        tmp_path,
        2025,
        [{"annual_average_employees": 120_000_000, "total_hours_worked": 10}],
    )
    out = osha_ita.read_ita(2025, tmp_path)
    assert out.loc[0, "annual_average_employees"] == 120_000_000
    assert "canonical_band" not in out.columns


def test_hours_flag_marks_physically_impossible_rows(tmp_path):
    _write_ita(
        tmp_path,
        2025,
        [
            # 8,760 h/employee is the 24x365 boundary: allowed.
            {"annual_average_employees": 10, "total_hours_worked": 87_600},
            # 8,761 h/employee: impossible.
            {"annual_average_employees": 10, "total_hours_worked": 87_610},
        ],
    )
    out = osha_ita.read_ita(2025, tmp_path)
    assert list(out["hours_implausible"]) == [False, True]


def test_zero_employment_is_unbandable(tmp_path):
    """A zero-employee summary must not be coerced into ``1-9``."""
    _write_ita(
        tmp_path,
        2025,
        [
            {"annual_average_employees": 0},
            {"annual_average_employees": 3},
        ],
    )
    out = osha_ita.read_ita(2025, tmp_path)
    assert list(out["bandable"]) == [False, True]
    cleaned = osha_ita.apply_quality_rule(out, max_employees=1_000_000)
    assert list(cleaned["annual_average_employees"]) == [3]
    assert cleaned.attrs["quality_rule"]["dropped_unbandable"] == 1


def test_quality_rule_requires_an_explicit_cap(tmp_path):
    """No default: the cap is a referee choice, not a loader detail."""
    _write_ita(tmp_path, 2025, [{}])
    out = osha_ita.read_ita(2025, tmp_path)
    with pytest.raises(TypeError):
        osha_ita.apply_quality_rule(out)


def test_quality_rule_rejects_nonsense_cap(tmp_path):
    _write_ita(tmp_path, 2025, [{}])
    out = osha_ita.read_ita(2025, tmp_path)
    with pytest.raises(ValueError, match="max_employees must be >= 1"):
        osha_ita.apply_quality_rule(out, max_employees=0)


def test_quality_rule_records_what_it_dropped(tmp_path):
    _write_ita(
        tmp_path,
        2025,
        [
            {"annual_average_employees": 50},
            {"annual_average_employees": 0},
            {"annual_average_employees": 10, "total_hours_worked": 900_000},
            {"annual_average_employees": 5_000_000},
        ],
    )
    out = osha_ita.read_ita(2025, tmp_path)
    cleaned = osha_ita.apply_quality_rule(out, max_employees=100_000)
    rule = cleaned.attrs["quality_rule"]
    assert rule["rows_in"] == 4
    assert rule["rows_out"] == 1
    assert rule["dropped_unbandable"] == 1
    assert rule["dropped_hours_implausible"] == 1
    assert rule["dropped_above_max_employees"] == 1
    assert rule["max_employees"] == 100_000
    assert rule["employment_out"] == 50
    assert list(cleaned["canonical_band"]) == ["B50_99"]


def test_quality_rule_can_keep_hours_implausible_rows(tmp_path):
    _write_ita(
        tmp_path,
        2025,
        [{"annual_average_employees": 10, "total_hours_worked": 900_000}],
    )
    out = osha_ita.read_ita(2025, tmp_path)
    kept = osha_ita.apply_quality_rule(
        out, max_employees=100_000, drop_hours_implausible=False
    )
    assert len(kept) == 1
    assert kept.attrs["quality_rule"]["dropped_hours_implausible"] == 0


def test_quality_rule_rejects_a_frame_it_did_not_produce():
    frame = pd.DataFrame({"annual_average_employees": [10]})
    with pytest.raises(ValueError, match="pass the output of read_ita"):
        osha_ita.apply_quality_rule(frame, max_employees=1000)


def test_bands_are_exact_for_every_canonical_edge(tmp_path):
    """Administrative headcounts never straddle a canonical edge."""
    expected = {
        1: "LT10",
        9: "LT10",
        10: "B10_49",
        49: "B10_49",
        50: "B50_99",
        99: "B50_99",
        100: "B100_499",
        499: "B100_499",
        500: "B500_PLUS",
    }
    _write_ita(
        tmp_path,
        2025,
        [
            {"annual_average_employees": n, "total_hours_worked": n * 2000}
            for n in expected
        ],
    )
    out = osha_ita.read_ita(2025, tmp_path)
    cleaned = osha_ita.apply_quality_rule(out, max_employees=1_000_000)
    got = dict(
        zip(
            cleaned["annual_average_employees"],
            cleaned["canonical_band"],
            strict=True,
        )
    )
    assert got == expected


def test_naics_sector_is_the_first_two_digits(tmp_path):
    _write_ita(tmp_path, 2025, [{"naics_code": "622110"}])
    out = osha_ita.read_ita(2025, tmp_path)
    assert out.loc[0, "naics_sector"] == "62"


@needs_real_ita
def test_real_2025_file_reproduces_pinned_quality_facts():
    """Guards the provenance sidecar's cleaning-sensitivity table."""
    out = osha_ita.read_ita(2025, REAL_DATA)
    assert len(out) == 383_283
    raw_sum = out["annual_average_employees"].sum()
    assert int(raw_sum) == 321_889_014
    assert int(out["hours_implausible"].sum()) == 1_996
    assert int((~out["bandable"]).sum()) >= 4_468
    # The cap, not the physical test, does essentially all the work.
    hours_only = osha_ita.apply_quality_rule(out, max_employees=10**12)
    assert hours_only.attrs["quality_rule"]["employment_out"] > 300_000_000
    capped = osha_ita.apply_quality_rule(out, max_employees=613_000)
    assert capped.attrs["quality_rule"]["employment_out"] == 61_188_048
