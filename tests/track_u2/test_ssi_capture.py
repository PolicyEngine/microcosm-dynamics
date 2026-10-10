"""Documentary parameter checks only: no PSID input or estimator import."""

from __future__ import annotations

import copy
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/capture_track_u2_ssi_parameters.py"
SPEC = importlib.util.spec_from_file_location("u2_ssi_capture", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
capture = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(capture)
SOURCE_MANIFEST = ROOT / "tests/data/track_u2/ssi_sources/manifest.json"
CAPTURE_MANIFEST = ROOT / "tests/data/track_u2/ssi_capture_manifest.json"
SSI_CAPTURE_SHA256 = (
    "a58d55c160b48cd3e21f730d45265374bd3c8a9eb7eae947469a5a5dc0b23762"
)
EXPECTED_FBR = {
    2012: (698, 1048),
    2013: (710, 1066),
    2014: (721, 1082),
    2015: (733, 1100),
    2016: (733, 1100),
    2017: (735, 1103),
    2018: (750, 1125),
    2019: (771, 1157),
    2020: (783, 1175),
    2021: (794, 1191),
    2022: (841, 1261),
}


@pytest.fixture(scope="module")
def document():
    return json.loads(capture.OUTPUT.read_text())


def test_capture_manifest_hashes_and_bytes():
    manifest = json.loads(CAPTURE_MANIFEST.read_text())
    assert (
        manifest["schema_version"]
        == "populace_dynamics.track_u2_ssi_capture_manifest.v1"
    )
    for record in manifest["files"]:
        raw = (ROOT / record["path"]).read_bytes()
        assert len(raw) == record["bytes"]
        assert hashlib.sha256(raw).hexdigest() == record["sha256"]
    assert capture.sha256(capture.OUTPUT) == SSI_CAPTURE_SHA256


def test_source_manifest_schema_and_hashes():
    manifest = json.loads(SOURCE_MANIFEST.read_text())
    assert (
        manifest["schema_version"]
        == "populace_dynamics.track_u2_ssi_sources.v1"
    )
    assert manifest["errors"] == []
    assert len(manifest["sources"]) == 106
    capture.verify_manifest(manifest)
    notices, regulations, parameters = [], [], []
    for source in manifest["sources"]:
        assert source["url"].startswith("https://")
        assert len(source["sha256"]) == 64
        assert source["bytes"] > 0
        assert dt.datetime.fromisoformat(source["retrieved_at_utc"]).tzinfo
        if source["kind"] == "federal_register_notice":
            assert source["url"].startswith("https://www.govinfo.gov/")
            notices.append(source["income_year"])
        elif source["kind"] == "historical_cfr":
            regulations.append((source["edition_year"], source["section"]))
        else:
            assert source["kind"] == "policyengine_parameter"
            assert source["revision"] == manifest["policyengine_us_revision"]
            parameters.append(source["parameter"])
    assert sorted(notices) == list(range(2012, 2023))
    assert set(regulations) == {
        (year, f"416.{section}")
        for year in range(2012, 2023)
        for section in capture.SECTIONS
    }
    assert set(parameters) == set(capture.SSI_FILES)


def test_capture_schema_and_complete_coverage(document):
    assert (
        document["schema_version"]
        == "populace_dynamics.track_u2_ssi_parameters.v1"
    )
    assert document["target_id"] == "U2"
    assert document["years"] == list(range(2012, 2023))
    assert set(document["federal_benefit_rate_monthly"]) == {
        "individual",
        "couple",
    }
    for values in document["federal_benefit_rate_monthly"].values():
        assert set(values) == set(map(str, range(2012, 2023)))
    assert len(document["source"]["policyengine_us_files_sha256"]) == 7
    assert set(document["source"]["effective_dates"]) == set(capture.SSI_FILES)
    for dates in document["source"]["effective_dates"].values():
        assert set(dates) == set(map(str, range(2012, 2023)))
        for year, date in dates.items():
            assert dt.date.fromisoformat(date) <= dt.date(int(year), 1, 1)


def test_capture_reproduces_exactly_offline():
    assert (
        capture.serialized(capture.build_capture())
        == capture.OUTPUT.read_bytes()
    )


@pytest.mark.parametrize("year", range(2012, 2023))
def test_fbr_independently_matches_official_notice(document, year):
    rates = document["federal_benefit_rate_monthly"]
    expected = EXPECTED_FBR[year]
    source = next(
        item
        for item in json.loads(SOURCE_MANIFEST.read_text())["sources"]
        if item.get("income_year") == year
    )
    notice = capture.notice_rates(source)
    assert (notice["individual"], notice["couple"]) == expected
    assert (
        rates["individual"][str(year)],
        rates["couple"][str(year)],
    ) == expected
    assert notice["printed_page"] > 0
    assert document["verification"]["annual_notices"][str(year)] == notice


def test_2017_actual_notice_and_2018_corrected_republication():
    notices = {
        item["income_year"]: item
        for item in json.loads(SOURCE_MANIFEST.read_text())["sources"]
        if item["kind"] == "federal_register_notice"
    }
    assert notices[2017]["url"].endswith("/2016-26026.htm")
    assert notices[2018]["url"].endswith("/2017-27105.htm")
    assert notices[2018]["corrected_republication"] is True


@pytest.mark.parametrize("revision", [None, "", "unknown", " ", "abcdef"])
def test_missing_empty_unknown_and_abbreviated_revision_refuse(revision):
    manifest = json.loads(SOURCE_MANIFEST.read_text())
    manifest["policyengine_us_revision"] = revision
    with pytest.raises(ValueError, match="exact git SHA"):
        capture.build_capture(manifest)


@pytest.mark.parametrize("name", capture.CONSTANT_NAMES)
def test_constant_checks_each_of_eleven_years_and_refuses_variation(name):
    path = capture.SOURCE_DIR / "policyengine_us" / capture.SSI_FILES[name]
    values = yaml.safe_load(path.read_text())["values"]
    expected = capture.constant(name, values)
    assert all(
        capture.selected(values, year)[1] == expected for year in capture.YEARS
    )
    changed = copy.deepcopy(values)
    changed[dt.date(2018, 1, 1)] = expected + 1
    with pytest.raises(ValueError, match="amendment required"):
        capture.constant(name, changed)


def test_january_selection_including_missing_coverage():
    values = {dt.date(2011, 7, 1): 10, dt.date(2012, 2, 1): 20}
    assert capture.selected(values, 2012) == ("2011-07-01", 10)
    with pytest.raises(ValueError, match="no parameter value"):
        capture.selected(values, 2011)


def test_historical_cfr_verification_and_parameter_crosscheck(document):
    observed = capture.verify_historical_cfr()
    assert observed == document["verification"]["historical_cfr"]
    assert set(observed) == {f"416.{section}" for section in capture.SECTIONS}
    for record in observed.values():
        assert set(record["annual_editions"]) == set(
            map(str, range(2012, 2023))
        )
        assert record["status"] == "RESOLVED"
    projection = capture.parameter_projection(document, 2012)
    constants = {name: projection[name] for name in capture.CONSTANT_NAMES}
    check = capture.verify_cfr_parameter_values(constants)
    assert check == document["verification"]["historical_parameter_values"]
    constants["general_income_exclusion"] += 1
    with pytest.raises(ValueError, match="CFR parameters differ"):
        capture.verify_cfr_parameter_values(constants)


def test_complete_2012_ssi_overlap_and_u1_immutable(document):
    old = capture.checked_json(
        ROOT / "data/external/track_u_ssi_parameters.json",
        capture.U1_SSI_SHA256,
    )
    assert capture.parameter_projection(
        document, 2012
    ) == capture.parameter_projection(old, 2012)


def test_census_pin_full_coverage_full_overlap_and_2022_precision():
    check = capture.verify_census_reuse()
    assert check["complete_2003_2022"] is True
    later = capture.checked_json(ROOT / check["path"], capture.CENSUS_SHA256)
    sizes = {
        "one_under_65": 1,
        "one_65_plus": 1,
        "two_under_65": 2,
        "two_65_plus": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine_plus": 9,
    }
    for year in map(str, range(2003, 2023)):
        assert set(later["weighted_average"][year]) == set(sizes)
        assert set(later["weighted_average_all_ages"][year]) == {"one", "two"}
        assert set(later["matrix"][year]) == set(sizes)
        for size, columns in sizes.items():
            assert len(later["matrix"][year][size]) == columns
    assert check["weighted_average_unit_dollars_2022"] == 10
    assert all(
        value % 10 == 0 for value in later["weighted_average"]["2022"].values()
    )


def test_wrong_capture_hash_refused():
    with pytest.raises(ValueError, match="capture hash mismatch"):
        capture.checked_json(capture.OUTPUT, "0" * 64)
