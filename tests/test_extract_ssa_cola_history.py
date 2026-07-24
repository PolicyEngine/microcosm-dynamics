"""Reader-free tests for the committed SSA COLA-history transcription."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
OUTPUT = ROOT / "data" / "external" / "ssa_cola_history.json"

OUTPUT_SHA256 = (
    "12da7f0e0d33fc53eaa31567d86c3cc035a49feefc2e4695bceea3379c2a38db"
)
CONTENT_SHA256 = (
    "8f1d75cab8bd1dba226c83bdff28a0ca1b21167e803eb65ff1d13d5cbe2255e0"
)

EXPECTED_COLA_PERCENT = (
    (1975, 8.0),
    (1976, 6.4),
    (1977, 5.9),
    (1978, 6.5),
    (1979, 9.9),
    (1980, 14.3),
    (1981, 11.2),
    (1982, 7.4),
    (1983, 3.5),
    (1984, 3.5),
    (1985, 3.1),
    (1986, 1.3),
    (1987, 4.2),
    (1988, 4.0),
    (1989, 4.7),
    (1990, 5.4),
    (1991, 3.7),
    (1992, 3.0),
    (1993, 2.6),
    (1994, 2.8),
    (1995, 2.6),
    (1996, 2.9),
    (1997, 2.1),
    (1998, 1.3),
    (1999, 2.5),
    (2000, 3.5),
    (2001, 2.6),
    (2002, 1.4),
    (2003, 2.1),
    (2004, 2.7),
    (2005, 4.1),
    (2006, 3.3),
    (2007, 2.3),
    (2008, 5.8),
    (2009, 0.0),
    (2010, 0.0),
    (2011, 3.6),
    (2012, 1.7),
    (2013, 1.5),
    (2014, 1.7),
    (2015, 0.0),
    (2016, 0.3),
    (2017, 2.0),
    (2018, 2.8),
    (2019, 1.6),
    (2020, 1.3),
    (2021, 5.9),
    (2022, 8.7),
)

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import extract_ssa_cola_history as extractor  # noqa: E402


def _committed() -> dict:
    return json.loads(OUTPUT.read_text())


def test__cola_history_json__has_the_review_pin_sha256():
    assert hashlib.sha256(OUTPUT.read_bytes()).hexdigest() == OUTPUT_SHA256


def test__cola_history_build__reproduces_json_byte_for_byte():
    rendered = json.dumps(extractor.build(), indent=2) + "\n"
    assert rendered == OUTPUT.read_text()


def test__cola_history_build__is_deterministic_across_runs():
    first = json.dumps(extractor.build(), indent=2)
    second = json.dumps(extractor.build(), indent=2)
    assert first == second


def test__cola_history__matches_every_transcribed_ssa_row():
    rows = tuple(
        (int(year), percentage)
        for year, percentage in _committed()["data"].items()
    )
    assert rows == EXPECTED_COLA_PERCENT


def test__cola_history__covers_1975_through_2022_continuously():
    doc = _committed()
    years = [int(year) for year in doc["data"]]
    assert years == list(range(1975, 2023))
    assert doc["validation"] == {
        "first_determination_year": 1975,
        "latest_determination_year": 2022,
        "n_observations": 48,
        "continuous_determination_years": True,
        "required_coverage": {
            "first_year": 1979,
            "last_year": 2022,
            "n_years": 44,
            "complete": True,
        },
    }


def test__cola_history__has_exact_required_1979_2022_span():
    required_years = [
        int(year) for year in _committed()["data"] if 1979 <= int(year) <= 2022
    ]
    assert required_years == list(range(1979, 2023))


def test__cola_history__matches_independent_official_literal_vector():
    # This literal vector is deliberately independent of the extractor's
    # TRANSCRIBED_COLA_PERCENT and pins scattered official SSA rows directly.
    data = _committed()["data"]
    assert {
        year: data[str(year)]
        for year in (
            1975,
            1979,
            1983,
            1987,
            1996,
            2000,
            2008,
            2009,
            2010,
            2015,
            2020,
            2022,
        )
    } == {
        1975: 8.0,
        1979: 9.9,
        1983: 3.5,
        1987: 4.2,
        1996: 2.9,
        2000: 3.5,
        2008: 5.8,
        2009: 0.0,
        2010: 0.0,
        2015: 0.0,
        2020: 1.3,
        2022: 8.7,
    }


def test__cola_history__records_the_1983_determination_timing_transition():
    doc = _committed()
    assert {year: doc["data"][str(year)] for year in (1982, 1983, 1984)} == {
        1982: 7.4,
        1983: 3.5,
        1984: 3.5,
    }
    assert "following year" in doc["historical_timing"]["1983-2022"]


def test__cola_history__pins_the_canonical_content_hash():
    doc = _committed()
    digest = extractor.content_sha256(doc["data"])
    assert digest == CONTENT_SHA256
    assert extractor.CONTENT_SHA256 == CONTENT_SHA256
    assert doc["provenance"]["content_sha256"] == CONTENT_SHA256
    assert doc["build"]["content_sha256"] == CONTENT_SHA256


def test__cola_history__rejects_transcription_drift(monkeypatch):
    rows = list(extractor.TRANSCRIBED_COLA_PERCENT)
    rows[-1] = (2022, 8.6)
    monkeypatch.setattr(extractor, "TRANSCRIBED_COLA_PERCENT", tuple(rows))
    with pytest.raises(ValueError, match="content sha256"):
        extractor.transcribed_data()


def test__cola_history__binds_semantics_vintage_and_provenance():
    doc = _committed()
    provenance = doc["provenance"]
    assert doc["schema_version"] == "ssa_cola_history.v1"
    assert doc["unit"] == "percent"
    assert doc["year_basis"] == "determination_year"
    assert "automatic COLA determination" in doc["year_semantics"]
    assert "July payments" in doc["historical_timing"]["1975-1982"]
    assert "January payments" in doc["historical_timing"]["1983-2022"]
    assert doc["vintage_year"] == 2022
    assert provenance["source_url"] == (
        "https://www.ssa.gov/oact/cola/colaseries.html"
    )
    assert provenance["retrieval_date"] == "2026-07-24"
    assert "2022" in provenance["vintage"]
    assert "checked row by row" in provenance["transcription_verification"]
    assert "PR #286" in provenance["transcription_verification"]
