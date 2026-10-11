"""The byte-pinned EPUF reader and its reproduction of SSA's tables.

The refusal tests run anywhere. The reproduction tests need the staged
EPUF members (``~/PolicyEngine/epuf-data/csv`` or
``POPULACE_DYNAMICS_EPUF_DIR``) and skip unless the staged bytes are the
pinned ones. Their targets are SSA's own published numbers, extracted
by ``scripts/extract_epuf_published_tables.py`` into
``data/external/epuf_2006/published_tables.json``.
"""

from __future__ import annotations

import hashlib
import json
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pandas as pd
import pytest

from populace_dynamics.cola_track_a.statutory import load_statutory_capture
from populace_dynamics.data import epuf

ROOT = Path(__file__).resolve().parents[2]
PUBLISHED = ROOT / "data" / "external" / "epuf_2006" / "published_tables.json"

_STATUS = epuf.epuf_status()
needs_pinned_epuf = pytest.mark.skipif(
    not _STATUS["pinned"],
    reason="EPUF members not staged, or not the pinned bytes",
)


def _round_half_up(value: float, places: str) -> float:
    return float(
        Decimal(repr(float(value))).quantize(
            Decimal(places), rounding=ROUND_HALF_UP
        )
    )


def _published() -> dict:
    return json.loads(PUBLISHED.read_text(encoding="utf-8"))["tables"]


def _wage_base() -> dict[int, float]:
    points = {
        int(year): float(value)
        for year, value in load_statutory_capture()[
            "wage_base_change_points"
        ].items()
    }
    out = {}
    for year in range(epuf.EPUF_FIRST_YEAR, epuf.EPUF_LAST_YEAR + 1):
        out[year] = points[max(y for y in points if y <= year)]
    return out


# --- refusals (no data needed) -------------------------------------------


def test_missing_folder_is_refused(tmp_path):
    with pytest.raises(epuf.EPUFNotStagedError, match="No EPUF2006"):
        epuf.read_demographic(data_dir=tmp_path)
    status = epuf.epuf_status(data_dir=tmp_path)
    assert status["staged"] is False
    assert status["pinned"] is False


def test_unpinned_bytes_are_refused_before_reading(tmp_path):
    (tmp_path / epuf.DEMOGRAPHIC_FILE).write_text(
        '"ID","YOB","SEX","TOT_COV_EARN3750","QC3750","QC5152"\n'
        '"1","1973","1","0","0","0"\n'
    )
    (tmp_path / epuf.ANNUAL_FILE).write_text(
        '"ID","YEAR_EARN","ANNUAL_EARNINGS","ANNUAL_QTRS"\n'
        '"1","1998","7500","4"\n'
    )
    with pytest.raises(epuf.EPUFNotStagedError, match="not the pinned"):
        epuf.read_annual(data_dir=tmp_path)
    status = epuf.epuf_status(data_dir=tmp_path)
    assert status["staged"] is True
    assert status["pinned"] is False


def test_unverified_read_of_other_bytes_checks_row_counts(tmp_path):
    (tmp_path / epuf.DEMOGRAPHIC_FILE).write_text(
        '"ID","YOB","SEX","TOT_COV_EARN3750","QC3750","QC5152"\n'
        '"1","1973","1","0","0","0"\n'
    )
    with pytest.raises(ValueError, match="persons; the pinned file has"):
        epuf.read_demographic(data_dir=tmp_path, verify=False)


def test_env_var_names_the_folder(tmp_path, monkeypatch):
    monkeypatch.setenv("POPULACE_DYNAMICS_EPUF_DIR", str(tmp_path))
    assert epuf.epuf_status()["directory"] == str(tmp_path)


def test_published_tables_record_their_sources():
    payload = json.loads(PUBLISHED.read_text(encoding="utf-8"))
    for source in payload["sources"].values():
        text = ROOT / source["text"]
        assert hashlib.sha256(text.read_bytes()).hexdigest() == (
            source["text_sha256"]
        )
    tables = payload["tables"]
    assert set(tables) == {
        "ssb_table_a1_records",
        "ssb_table_4_mean_median",
        "ssb_chart_3_birth_year",
        "ssb_chart_4_birth_year_sex",
        "rsn_table_8_pct_below_max",
    }
    assert len(tables["ssb_table_a1_records"]["rows"]) == 56
    assert len(tables["rsn_table_8_pct_below_max"]["rows"]) == 56
    assert len(tables["ssb_chart_3_birth_year"]["rows"]) == 137


# --- reproduction against SSA's published tables -------------------------


@pytest.fixture(scope="module")
def frames():
    demographic = epuf.read_demographic()
    annual = epuf.read_annual().merge(
        demographic[["person_id", "birth_year", "sex"]],
        on="person_id",
        how="left",
        validate="many_to_one",
    )
    return demographic, annual


@needs_pinned_epuf
def test_counts_match_the_pinned_file(frames):
    demographic, annual = frames
    assert len(demographic) == epuf.EPUF_PERSONS == 4_384_254
    assert annual["person_id"].nunique() == epuf.EPUF_EARNER_PERSONS
    assert len(annual) == epuf.EPUF_ANNUAL_ROWS
    assert annual["birth_year"].notna().all()
    assert not annual.duplicated(["person_id", "year"]).any()
    assert (annual["earnings"] > 0).all()
    assert annual.loc[annual["year"] <= 1952, "quarters"].isna().all()
    assert annual.loc[annual["year"] > 1952, "quarters"].notna().all()


@needs_pinned_epuf
def test_rows_exist_only_at_ages_15_to_85(frames):
    _, annual = frames
    age = annual["year"] - annual["birth_year"]
    assert int(age.min()) == 15
    assert int(age.max()) == 85


@needs_pinned_epuf
def test_every_year_tops_out_exactly_at_the_wage_base(frames):
    _, annual = frames
    cap = annual["year"].map(_wage_base())
    assert (annual["earnings"] <= cap).all()
    top = annual.groupby("year")["earnings"].max()
    assert top.to_dict() == {
        year: int(value) for year, value in _wage_base().items()
    }


@needs_pinned_epuf
def test_ssb_table_a1_records_by_sex(frames):
    _, annual = frames
    counts = annual.groupby(["year", "sex"]).size().unstack(fill_value=0)
    rows = _published()["ssb_table_a1_records"]["rows"]
    for year, row in rows.items():
        got = counts.loc[int(year)]
        assert {
            "all": int(got.sum()),
            "men": int(got[1]),
            "women": int(got[2]),
            "unknown": int(got[3]),
        } == row, year


@needs_pinned_epuf
def test_ssb_table_4_means_and_medians(frames):
    _, annual = frames
    rows = _published()["ssb_table_4_mean_median"]["rows"]
    groups = {"all": None, "men": 1, "women": 2, "unknown": 3}
    for year, row in rows.items():
        in_year = annual[annual["year"] == int(year)]
        for label, sex in groups.items():
            values = (
                in_year["earnings"]
                if sex is None
                else in_year.loc[in_year["sex"] == sex, "earnings"]
            )
            mean = _round_half_up(values.mean(), "1")
            median = float(values.median())
            assert median == row[f"median_{label}"], (year, label)
            # The sex-unknown group (300-500 records a year) misses SSA's
            # rounded mean by one dollar in 1963 and 1992.
            slack = 1 if label == "unknown" else 0
            assert abs(mean - row[f"mean_{label}"]) <= slack, (year, label)


@needs_pinned_epuf
def test_ssb_charts_3_and_4_birth_year_counts(frames):
    demographic, _ = frames
    tables = _published()
    by_year = demographic.groupby("birth_year").size()
    by_sex = (
        demographic.groupby(["birth_year", "sex"]).size().unstack(fill_value=0)
    )
    for year, row in tables["ssb_chart_3_birth_year"]["rows"].items():
        got = _round_half_up(by_year.get(int(year), 0) / 1000, "0.01")
        assert got == row["thousands"], year
    for year, row in tables["ssb_chart_4_birth_year_sex"]["rows"].items():
        got = (
            _round_half_up(by_sex.loc[int(year), 1] / 1000, "0.01"),
            _round_half_up(by_sex.loc[int(year), 2] / 1000, "0.01"),
        )
        assert got == (row["men_thousands"], row["women_thousands"]), year


@needs_pinned_epuf
def test_rsn_table_8_share_below_the_maximum(frames):
    _, annual = frames
    below = annual["earnings"] < annual["year"].map(_wage_base())
    frame = pd.DataFrame(
        {"year": annual["year"], "sex": annual["sex"], "below": below}
    )
    rows = _published()["rsn_table_8_pct_below_max"]["rows"]
    for year, row in rows.items():
        in_year = frame[frame["year"] == int(year)]
        got = {
            "epuf_all": _round_half_up(100 * in_year["below"].mean(), "0.1"),
            "epuf_men": _round_half_up(
                100 * in_year.loc[in_year["sex"] == 1, "below"].mean(), "0.1"
            ),
            "epuf_women": _round_half_up(
                100 * in_year.loc[in_year["sex"] == 2, "below"].mean(), "0.1"
            ),
        }
        assert got == {key: row[key] for key in got}, year


@needs_pinned_epuf
def test_year_filter_keeps_only_those_years():
    annual = epuf.read_annual(years=[2004])
    assert set(annual["year"].unique()) == {2004}
    assert len(annual) == int(
        _published()["ssb_table_a1_records"]["rows"]["2004"]["all"]
    )
    with pytest.raises(ValueError, match="cover 1951-2006"):
        epuf.read_annual(years=[2007])
