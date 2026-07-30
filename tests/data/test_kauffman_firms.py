"""Tests for the observed-firm Kauffman Firm Survey reader."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from populace_dynamics.data import kauffman_firms

REAL_KFS = Path(
    "~/PolicyEngine/kfs-data/logically-imputed/Public_Use_LI_Long.dta"
).expanduser()
needs_real_kfs = pytest.mark.skipif(
    not REAL_KFS.exists(),
    reason="KFS public-use long file is not staged",
)


def _write_kfs(directory: Path, rows: list[dict]) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    defaults = {
        "mprid": 10_000_016,
        "year": 2004,
        "status": "Complete",
        "c5_num_employees": "04",
        "c6_num_ft_employees": "03",
        "c7_num_pt_employees": "01",
        "naics_code": 54,
        "cswgt_final": 2.5,
    }
    frame = pd.DataFrame([{**defaults, **row} for row in rows])
    path = directory / "Public_Use_LI_Long.dta"
    frame.to_stata(path, write_index=False, version=118)
    return path


def test_reads_firm_year_rows_and_count_intervals(tmp_path):
    path = _write_kfs(
        tmp_path,
        [
            {},
            {
                "mprid": 10_000_090,
                "year": 2005,
                "c5_num_employees": "26-60",
                "c6_num_ft_employees": "25+",
                "c7_num_pt_employees": ".a",
            },
        ],
    )
    firms = kauffman_firms.read_kauffman_firms(path=path)

    assert list(firms["firm_id"]) == ["10000016", "10000090"]
    assert list(firms["year"]) == [2004, 2005]
    assert firms.loc[0, "employees_exact"] == 4
    assert firms.loc[1, "employees_lower"] == 26
    assert firms.loc[1, "employees_upper"] == 60
    assert pd.isna(firms.loc[1, "full_time_employees_upper"])
    assert pd.isna(firms.loc[1, "part_time_employees_lower"])


def test_resolves_staged_directory(tmp_path):
    _write_kfs(tmp_path, [{}])
    firms = kauffman_firms.read_kauffman_firms(data_dir=tmp_path)
    assert len(firms) == 1


def test_resolves_environment_directory(tmp_path, monkeypatch):
    _write_kfs(tmp_path, [{}])
    monkeypatch.setenv("POPULACE_DYNAMICS_KFS_DIR", str(tmp_path))
    firms = kauffman_firms.read_kauffman_firms()
    assert len(firms) == 1


def test_missing_staged_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="outside git"):
        kauffman_firms.read_kauffman_firms(data_dir=tmp_path)


def test_missing_required_column_raises(tmp_path):
    path = _write_kfs(tmp_path, [{}])
    frame = pd.read_stata(path).drop(columns="status")
    frame.to_stata(path, write_index=False, version=118)
    with pytest.raises(ValueError, match="status"):
        kauffman_firms.read_kauffman_firms(path=path)


@pytest.mark.parametrize("year", [2003, 2012, 2004.5])
def test_unsupported_year_raises(tmp_path, year):
    path = _write_kfs(tmp_path, [{"year": year}])
    with pytest.raises(ValueError, match="unsupported"):
        kauffman_firms.read_kauffman_firms(path=path)


def test_duplicate_firm_year_raises(tmp_path):
    path = _write_kfs(tmp_path, [{}, {}])
    with pytest.raises(ValueError, match="not unique"):
        kauffman_firms.read_kauffman_firms(path=path)


@pytest.mark.parametrize("firm_id", ["", -1, 10.5])
def test_invalid_firm_identifier_raises(tmp_path, firm_id):
    path = _write_kfs(tmp_path, [{"mprid": firm_id}])
    with pytest.raises(ValueError, match="identifiers"):
        kauffman_firms.read_kauffman_firms(path=path)


@pytest.mark.parametrize("weight", [-1, np.nan])
def test_invalid_weight_raises(tmp_path, weight):
    path = _write_kfs(tmp_path, [{"cswgt_final": weight}])
    with pytest.raises(ValueError, match="weights"):
        kauffman_firms.read_kauffman_firms(path=path)


def test_unknown_employee_count_code_fails_closed(tmp_path):
    path = _write_kfs(tmp_path, [{"c5_num_employees": "about five"}])
    with pytest.raises(ValueError, match="unsupported count"):
        kauffman_firms.read_kauffman_firms(path=path)


def test_profile_reports_coverage_without_mutating_input(tmp_path):
    path = _write_kfs(
        tmp_path,
        [
            {},
            {
                "mprid": 10_000_090,
                "c5_num_employees": "00",
                "cswgt_final": 3.5,
            },
            {
                "mprid": 10_000_320,
                "year": 2005,
                "status": "Out of Business",
                "c5_num_employees": ".a",
                "cswgt_final": 1.0,
            },
        ],
    )
    firms = kauffman_firms.read_kauffman_firms(path=path)
    before = firms.copy(deep=True)
    profile = kauffman_firms.kfs_profile(firms)

    row_2004 = profile.loc[profile["year"] == 2004].iloc[0]
    assert row_2004["firm_records"] == 2
    assert row_2004["complete_records"] == 2
    assert row_2004["employee_count_available"] == 2
    assert row_2004["zero_employee_records"] == 1
    assert row_2004["weighted_cohort_firms"] == 6.0
    pd.testing.assert_frame_equal(firms, before)


def test_profile_rejects_duplicate_keys(tmp_path):
    firms = kauffman_firms.read_kauffman_firms(path=_write_kfs(tmp_path, [{}]))
    duplicated = pd.concat([firms, firms], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate"):
        kauffman_firms.kfs_profile(duplicated)


@needs_real_kfs
def test_staged_public_use_file_has_documented_panel_shape():
    firms = kauffman_firms.read_kauffman_firms(path=REAL_KFS)
    assert len(firms) == 39_424
    assert firms["firm_id"].nunique() == 4_928
    assert set(firms["year"]) == set(kauffman_firms.KFS_YEARS)
    assert not firms.duplicated(["firm_id", "year"]).any()
    profile = kauffman_firms.kfs_profile(firms)
    assert list(profile["complete_records"]) == [
        4_928,
        3_998,
        3_390,
        2_915,
        2_606,
        2_408,
        2_126,
        2_007,
    ]
    assert int(firms["employees_lower"].notna().sum()) == 24_139
    assert int(firms["employees_exact"].notna().sum()) == 23_569
