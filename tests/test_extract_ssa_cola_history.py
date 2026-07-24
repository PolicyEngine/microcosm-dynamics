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
    "e8ffa0e51e08a7917904a959e6918f10cbdd3a554f975e3e1211f93aaa1aca29"
)
CONTENT_SHA256 = (
    "488618df8a8ea05f929d0f8ecc7eb79d240bee39adaea0572e9d73d339a54d69"
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
    (1983, 0.0),
    (1984, 3.5),
    (1985, 3.5),
    (1986, 3.1),
    (1987, 1.3),
    (1988, 4.2),
    (1989, 4.0),
    (1990, 4.7),
    (1991, 5.4),
    (1992, 3.7),
    (1993, 3.0),
    (1994, 2.6),
    (1995, 2.8),
    (1996, 2.6),
    (1997, 2.9),
    (1998, 2.1),
    (1999, 1.3),
    (2000, 2.5),
    (2001, 3.5),
    (2002, 2.6),
    (2003, 1.4),
    (2004, 2.1),
    (2005, 2.7),
    (2006, 4.1),
    (2007, 3.3),
    (2008, 2.3),
    (2009, 5.8),
    (2010, 0.0),
    (2011, 0.0),
    (2012, 3.6),
    (2013, 1.7),
    (2014, 1.5),
    (2015, 1.7),
    (2016, 0.0),
    (2017, 0.3),
    (2018, 2.0),
    (2019, 2.8),
    (2020, 1.6),
    (2021, 1.3),
    (2022, 5.9),
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
        "first_payment_year": 1975,
        "latest_payment_year": 2022,
        "n_observations": 48,
        "continuous_payment_years": True,
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


def test__cola_history__matches_mandatory_payment_year_spot_checks():
    data = _committed()["data"]
    assert {
        year: data[str(year)]
        for year in (1975, 1980, 2009, 2010, 2011, 2016, 2022)
    } == {
        1975: 8.0,
        1980: 14.3,
        2009: 5.8,
        2010: 0.0,
        2011: 0.0,
        2016: 0.0,
        2022: 5.9,
    }


def test__cola_history__records_the_1983_payment_timing_transition():
    doc = _committed()
    assert {year: doc["data"][str(year)] for year in (1982, 1983, 1984)} == {
        1982: 7.4,
        1983: 0.0,
        1984: 3.5,
    }
    assert "no COLA" in doc["historical_timing"]["1983"]


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
    assert doc["year_basis"] == "first_payment_year"
    assert "payments reflecting the COLA begin" in doc["year_semantics"]
    assert "July payments" in doc["historical_timing"]["1975-1982"]
    assert "January payments" in doc["historical_timing"]["1984-2022"]
    assert doc["vintage_year"] == 2022
    assert provenance["source_url"] == (
        "https://www.ssa.gov/oact/cola/colaseries.html"
    )
    assert provenance["retrieval_date"] == "2026-07-24"
    assert "2022" in provenance["vintage"]
    assert "requires verification at implementation review" in (
        provenance["transcription_verification"]
    )
    assert provenance["source_url"] in (
        provenance["transcription_verification"]
    )
