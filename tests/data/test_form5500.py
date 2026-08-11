"""Tests for the Form 5500 / 5500-SF sponsor microdata reader."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from populace_dynamics.data import form5500

REAL_DATA = form5500.firm_data_dir()
needs_real_5500 = pytest.mark.skipif(
    not (REAL_DATA / "f_5500_2023_latest.csv").exists(),
    reason="Form 5500 files not staged",
)


def _write_main(directory: Path, year: int, rows: list[dict]) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    defaults = {
        "SPONS_DFE_EIN": "123456789",
        "BUSINESS_CODE": "541990",
        "SPONS_DFE_LOC_US_STATE": "CA",
        "TYPE_PLAN_ENTITY_CD": 2,
        "TOT_PARTCP_BOY_CNT": 120,
        "TOT_ACTIVE_PARTCP_CNT": 100,
    }
    frame = pd.DataFrame([{**defaults, **row} for row in rows])
    path = directory / f"f_5500_{year}_latest.csv"
    frame.to_csv(path, index=False)
    return path


def _write_sf(directory: Path, year: int, rows: list[dict]) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    defaults = {
        "SF_SPONS_EIN": "987654321",
        "SF_BUSINESS_CODE": "722511",
        "SF_SPONS_US_STATE": "TX",
        "SF_TOT_ACT_PARTCP_BOY_CNT": 8,
    }
    frame = pd.DataFrame([{**defaults, **row} for row in rows])
    path = directory / f"f_5500_sf_{year}_latest.csv"
    frame.to_csv(path, index=False)
    return path


def test_missing_file_names_the_staging_hint(tmp_path):
    with pytest.raises(FileNotFoundError, match="POPULACE_DYNAMICS_FIRM_DIR"):
        form5500.read_main_filings(2023, tmp_path)


def test_missing_column_fails_loudly(tmp_path):
    frame = pd.DataFrame([{"SPONS_DFE_EIN": "1", "BUSINESS_CODE": "541990"}])
    frame.to_csv(tmp_path / "f_5500_2023_latest.csv", index=False)
    with pytest.raises(ValueError, match="missing columns"):
        form5500.read_main_filings(2023, tmp_path)


def test_ein_normalisation_survives_hyphens(tmp_path):
    """A hyphenated EIN must land on the same key as a bare one.

    DOL emits both forms across vintages; an unnormalised join drops
    the hyphenated rows silently, which reads as genuine non-overlap.
    """
    _write_main(
        tmp_path,
        2023,
        [
            {"SPONS_DFE_EIN": "12-3456789", "TOT_ACTIVE_PARTCP_CNT": 60},
            {"SPONS_DFE_EIN": "123456789", "TOT_ACTIVE_PARTCP_CNT": 40},
        ],
    )
    out = form5500.read_sponsors(2023, tmp_path, forms=("5500",))
    assert len(out) == 1
    assert out.loc[0, "sponsor_ein"] == "123456789"
    assert out.loc[0, "filings"] == 2


def test_short_ein_is_zero_padded(tmp_path):
    _write_main(tmp_path, 2023, [{"SPONS_DFE_EIN": "4567"}])
    out = form5500.read_sponsors(2023, tmp_path, forms=("5500",))
    assert out.loc[0, "sponsor_ein"] == "000004567"


def test_multiple_filings_take_max_not_sum(tmp_path):
    """The load-bearing aggregation rule.

    A sponsor with a 401(k) and a welfare plan files twice and the
    participant counts overlap. Summing would move this sponsor from
    ``50-99`` into ``100-499`` and inflate every large band.
    """
    _write_main(
        tmp_path,
        2023,
        [
            {"SPONS_DFE_EIN": "111111111", "TOT_ACTIVE_PARTCP_CNT": 90},
            {"SPONS_DFE_EIN": "111111111", "TOT_ACTIVE_PARTCP_CNT": 80},
        ],
    )
    out = form5500.read_sponsors(2023, tmp_path, forms=("5500",))
    assert len(out) == 1
    assert out.loc[0, "active_participants"] == 90
    assert out.loc[0, "canonical_band"] == "B50_99"
    assert out.loc[0, "filings"] == 2


def test_zero_active_participants_dropped_not_banded(tmp_path):
    """Canonical bands partition [1, inf); zero is not a firm of size 0."""
    _write_main(
        tmp_path,
        2023,
        [
            {"SPONS_DFE_EIN": "111111111", "TOT_ACTIVE_PARTCP_CNT": 0},
            {"SPONS_DFE_EIN": "222222222", "TOT_ACTIVE_PARTCP_CNT": 5},
        ],
    )
    out = form5500.read_sponsors(2023, tmp_path, forms=("5500",))
    assert list(out["sponsor_ein"]) == ["222222222"]
    assert out.loc[0, "canonical_band"] == "LT10"


def test_reads_both_forms_by_default(tmp_path):
    _write_main(tmp_path, 2023, [{"SPONS_DFE_EIN": "111111111"}])
    _write_sf(tmp_path, 2023, [{"SF_SPONS_EIN": "222222222"}])
    out = form5500.read_sponsors(2023, tmp_path)
    assert set(out["sponsor_ein"]) == {"111111111", "222222222"}


def test_sf_only_read_is_opt_in(tmp_path):
    """Reading one form must be a deliberate act, not a default."""
    _write_sf(tmp_path, 2023, [{"SF_SPONS_EIN": "222222222"}])
    with pytest.raises(FileNotFoundError):
        form5500.read_sponsors(2023, tmp_path)
    out = form5500.read_sponsors(2023, tmp_path, forms=("5500-SF",))
    assert list(out["sponsor_ein"]) == ["222222222"]


def test_unknown_form_rejected(tmp_path):
    _write_main(tmp_path, 2023, [{}])
    with pytest.raises(ValueError, match="Unknown Form 5500 variant"):
        form5500.read_sponsors(2023, tmp_path, forms=("5500", "5500-EZ"))


def test_empty_forms_rejected(tmp_path):
    with pytest.raises(ValueError, match="At least one"):
        form5500.read_sponsors(2023, tmp_path, forms=())


def test_business_code_yields_two_digit_sector(tmp_path):
    _write_main(
        tmp_path,
        2023,
        [{"SPONS_DFE_EIN": "111111111", "BUSINESS_CODE": "722511"}],
    )
    out = form5500.read_sponsors(2023, tmp_path, forms=("5500",))
    assert out.loc[0, "naics_sector"] == "72"


def test_bands_are_exact_for_every_canonical_edge(tmp_path):
    """Integer counts must never straddle — the point of the source.

    Intended bands are stated here independently of ``banding.py``'s
    tables, so editing one cannot silently move the other.
    """
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
        100_000: "B500_PLUS",
    }
    _write_main(
        tmp_path,
        2023,
        [
            {
                "SPONS_DFE_EIN": str(100_000_000 + i),
                "TOT_ACTIVE_PARTCP_CNT": n,
            }
            for i, n in enumerate(expected)
        ],
    )
    out = form5500.read_sponsors(2023, tmp_path, forms=("5500",))
    got = dict(
        zip(
            out["active_participants"],
            out["canonical_band"],
            strict=True,
        )
    )
    assert got == expected


@needs_real_5500
def test_real_2023_files_reproduce_pinned_counts():
    """Guards the provenance sidecar's headline numbers."""
    main = form5500.read_main_filings(2023, REAL_DATA)
    assert len(main) == 231_725
    sf = form5500.read_sf_filings(2023, REAL_DATA)
    assert len(sf) == 763_552
    sponsors = form5500.read_sponsors(2023, REAL_DATA)
    assert len(sponsors) == 790_028
    # More large sponsors than SUSB has large firms: the recorded
    # proof that the sponsor EIN is not the SUSB enterprise.
    assert int((sponsors["canonical_band"] == "B500_PLUS").sum()) == 23_813
