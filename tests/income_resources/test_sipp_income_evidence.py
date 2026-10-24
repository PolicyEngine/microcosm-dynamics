"""Check committed data/external SIPP metadata, never survey records.

The INVENTED_* pages below are made-up dictionary fragments. The evidence
checks read only captured APIs, dictionaries and Census input-example code.
Registry definitions must match their own release, and a missing or
incompletely parsed domain must refuse admission rather than borrow codes.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from datetime import datetime, timedelta
from functools import cache
from pathlib import Path
from urllib.parse import urlparse

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.data import sipp_income_registry as registry

EVIDENCE = (
    Path(__file__).resolve().parents[2] / "data" / "external" / "sipp_income"
)
YEARS = tuple(range(2018, 2026))
RAW_RANGE = re.compile(
    r"^\s*(-?\$?[\d,]+(?:\.\d+)?%?)\s*:\s*"
    r"(-?\$?[\d,]+(?:\.\d+)?%?)(?:\.\s+|\s+|$)",
    re.M,
)
INVENTED_RANGE_PAGE = """Name: INVENTED_BALANCE
Description: Invented account balance, not survey data.
Possible Values
0. No value
{lower} {before}:{after} {upper}. Invented dollars
1
"""
INVENTED_CONTINUATION = """Name: INVENTED_ENTRY
Description: Invented entry-year intervals, not survey data.
Possible Values
2010. Invented interval through 2010
1
\f
2015. Invented interval through 2015
2021. Invented interval through 2021
2
"""


@cache
def _json(filename):
    return json.loads((EVIDENCE / filename).read_text())


@cache
def _module(filename):
    name = "invented_test_" + Path(filename).stem
    spec = importlib.util.spec_from_file_location(name, EVIDENCE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@cache
def _pages(year):
    return (EVIDENCE / f"{year}_dictionary.txt").read_text().split("\f")


def _metadata(year):
    filename = (
        f"{year}_dictionary_variables.json"
        if year < 2022
        else f"{year}_variables.json"
    )
    return filename, _json(filename)["variables"]


def _ranges(metadata):
    return tuple(
        (item["min"], item["max"], item.get("description", ""))
        for item in metadata.get("values", {}).get("range", [])
    )


def _replay_page(year, metadata):
    """Replay declared PDF pages without trusting derived value domains."""
    pages = _pages(year)
    indices = metadata["dictionary_pdf_pages"]
    first = pages[indices[0] - 1]
    if len(indices) == 1:
        return first
    assert indices == list(range(indices[0], indices[-1] + 1))
    joined = re.sub(r"\n\s*\d+\s*$", "", first)
    for number in indices[1:]:
        joined += "\n" + re.sub(r"\n\s*\d+\s*$", "", pages[number - 1])
    return joined + "\n" + str(metadata["dictionary_printed_page"])


@pytest.mark.parametrize("year", YEARS)
def test_registry_matches_own_release_metadata(year):
    filename, metadata = _metadata(year)
    selected = _json("concept_selection.json")["concepts"]
    for concept, spec in registry.income_variables(year).items():
        raw = metadata[spec.name]
        assert spec.source == f"{filename}#{spec.name}"
        assert raw["label"] != "Suppressed"
        assert spec.label == raw["label"]
        assert spec.predicate_type == raw["predicateType"]
        assert spec.items == tuple(
            sorted(raw.get("values", {}).get("item", {}).items())
        )
        assert spec.ranges == _ranges(raw)
        assert spec.ownership == selected[concept]["ownership_level"]
        assert spec.period == selected[concept]["period"]
        assert spec.allow_blank == (concept not in registry.CORE_CONCEPTS)
        expected_missing = (
            ("", ".")
            if year <= 2021 and spec.storage_type != "string"
            else ("",)
        )
        assert spec.structural_missing == expected_missing


@pytest.mark.parametrize("year", range(2018, 2022))
def test_admitted_dictionary_domains_replay_from_raw_pages(year):
    parser = _module("parse_dictionary_metadata.py")
    document = _json(f"{year}_dictionary_variables.json")
    for spec in registry.income_variables(year).values():
        raw = document["variables"][spec.name]
        page = _replay_page(year, raw)
        name, fields, values, printed = parser.parse_page(page, year)
        assert name == spec.name
        assert fields.get("Description", "") == raw["dictionary_label"]
        assert fields.get("Universe", "") == raw["universe"]
        assert printed == raw["dictionary_printed_page"]
        assert values == raw["values"]
        assert not fields["Unparsed values"]
        assert raw["verified"]
        # Independently check that a source range was not swallowed into
        # the preceding categorical label by the metadata parser.
        parsed_ranges = {(lo, hi) for lo, hi, _ in spec.ranges}
        for match in RAW_RANGE.finditer(page):
            endpoints = tuple(
                token.replace("$", "").replace("%", "").replace(",", "")
                for token in match.groups()
            )
            assert endpoints in parsed_ranges


@pytest.mark.parametrize("year", YEARS)
def test_storage_types_match_census_input_schema(year):
    schema = {row["name"]: row for row in _json(f"pu{year}_schema.json")}
    for spec in registry.income_variables(year).values():
        assert spec.storage_type == schema[spec.name]["dtype"]
    assert registry.income_variables(year)["sample_unit_id"].storage_type == (
        "string"
    )
    assert registry.income_variables(year)["weight"].storage_type == "float"


@pytest.mark.parametrize("year", YEARS)
def test_explicit_crosswalk_admits_only_verified_domains(year):
    selected = _json("concept_selection.json")
    crosswalk = selected["release_crosswalk"][str(year)]
    assert set(crosswalk) == set(selected["concepts"])
    _, metadata = _metadata(year)
    admitted, refused = {}, {}
    for concept, raw_name in crosswalk.items():
        if raw_name is None:
            refused[concept] = "absent or suppressed in release"
            continue
        raw = metadata.get(raw_name)
        if raw is None or raw.get("verified") is False:
            refused[concept] = "dictionary domain unverified"
        elif not raw.get("values"):
            refused[concept] = "no verified value domain"
        else:
            assert raw["label"] != "Suppressed"
            admitted[concept] = raw_name
    actual = registry.income_variables(year)
    assert {name: spec.name for name, spec in actual.items()} == admitted
    assert set(registry.CORE_CONCEPTS) <= actual.keys()
    assert _json("refused_concepts.json")[str(year)] == refused


def test_changed_entry_intervals_and_suppression_remain_explicit():
    assert registry.code_label(2022, "entry_year_code", 2016) == (
        "Recode for year 2015 to 2016"
    )
    assert registry.code_label(2025, "entry_year_code", 2016) == "Year"
    assert "roster_relationship_15" in registry.income_variables(2024)
    assert "roster_relationship_15" not in registry.income_variables(2025)
    assert "9" not in dict(
        registry.income_variables(2018)["ssi_received_year"].items
    )
    assert registry.code_label(2019, "ssi_received_year", 9) == (
        "Cannot be determined"
    )
    for year in range(2018, 2021):
        assert "employer_retirement_plan_offered" not in (
            registry.income_variables(year)
        )
    assert "employer_retirement_plan_offered" in registry.income_variables(
        2021
    )


def test_2022_person_number_uses_its_own_dictionary_supplement():
    spec = registry.income_variables(2022)["person_number"]
    raw = _json("2022_dictionary_variables.json")["variables"]["PNUM"]
    parser = _module("parse_dictionary_metadata.py")
    name, _, values, _ = parser.parse_page(_replay_page(2022, raw), 2022)
    assert name == "PNUM"
    assert raw["verified"]
    assert values == raw["values"]
    assert spec.domain_source == "2022_dictionary_variables.json#PNUM"
    assert spec.domain_ranges == _ranges(raw)
    assert [(lo, hi) for lo, hi, _ in spec.domain_ranges] == [("101", "499")]
    for year in YEARS:
        for concept, item in registry.income_variables(year).items():
            if (year, concept) != (2022, "person_number"):
                assert item.domain_ranges == ()
                assert item.domain_source == ""


@pytest.mark.parametrize("year", YEARS)
def test_replicate_family_matches_census_dictionary_and_schema(year):
    schema = {row["name"]: row for row in _json(f"rw{year}_schema.json")}
    dictionary = (EVIDENCE / f"rw{year}_dictionary.txt").read_text()
    table = registry.replicate_variables(year)
    linkage = {"sample_unit_id", "person_number", "month"}
    assert set(table) == linkage | {
        f"replicate_weight_{number}" for number in range(241)
    }
    for concept, raw_name, low, high in [
        ("sample_unit_id", "SSUID", "00000000000000", "99999999999999"),
        ("person_number", "PNUM", "101", "499"),
        ("month", "MONTHCODE", "1", "12"),
    ]:
        spec = table[concept]
        assert spec.name == raw_name
        assert f"D {raw_name}" in dictionary
        assert f"{low}:{high}" in dictionary
        assert [(a, b) for a, b, _ in spec.ranges] == [(low, high)]
    assert "D REPWGT1" in dictionary
    assert "REPWGT240" in dictionary
    assert "0.000000:9999999.999999" in dictionary
    for number in range(241):
        spec = table[f"replicate_weight_{number}"]
        assert spec.name == f"REPWGT{number}"
        assert schema[spec.name]["dtype"] == spec.storage_type == "float"
        assert spec.label == schema[spec.name]["label"] == ""
        assert spec.predicate_type == "float"
        assert spec.items == ()
        assert spec.ranges == (
            ("0.000000", "9999999.999999", "Final person replicate weight"),
        )
        assert spec.period == "weight"
        assert spec.source == (
            f"rw{year}_dictionary.txt+rw{year}_schema.json#{spec.name}"
        )


def test_embedded_evidence_hashes_and_derived_provenance():
    assert registry.EVIDENCE_SHA256
    for filename, digest in registry.EVIDENCE_SHA256.items():
        assert hashlib.sha256(
            (EVIDENCE / filename).read_bytes()
        ).hexdigest() == (digest)
    for derived in _json("derived_manifest.json"):
        payload = (EVIDENCE / derived["path"]).read_bytes()
        assert len(payload) == derived["bytes"]
        assert hashlib.sha256(payload).hexdigest() == derived["sha256"]
    for year in range(2018, 2023):
        source = _json(f"{year}_dictionary_variables.json")["derived_from"]
        for key in ["dictionary", "text", "schema"]:
            assert (
                hashlib.sha256(
                    (EVIDENCE / source[key]).read_bytes()
                ).hexdigest()
                == source[f"{key}_sha256"]
            )


def test_capture_manifest_pins_only_public_census_metadata():
    manifest = _json("capture_manifest.json")
    assert manifest
    for capture in manifest:
        assert urlparse(capture["url"]).hostname in {
            "api.census.gov",
            "www.census.gov",
            "www2.census.gov",
        }
        retrieved = datetime.fromisoformat(capture["retrieved_utc"])
        assert retrieved.utcoffset() == timedelta(0)
        filename = Path(capture["path"])
        assert filename.parent == Path(".")
        assert filename.suffix in {".json", ".txt", ".html", ".pdf", ".py"}
        payload = (EVIDENCE / filename).read_bytes()
        assert len(payload) == capture["bytes"]
        assert hashlib.sha256(payload).hexdigest() == capture["sha256"]
        # Input examples are executable metadata, never staged pu/rw records.
        if filename.suffix == ".py":
            assert "input_example" in filename.name
        if filename.suffix == ".pdf":
            assert "dictionary" in filename.name


def test_regeneration_matches_embedded_tables_without_writing():
    builder = _module("build_registry.py")
    concepts, definitions, releases, replicates, refused, hashes = (
        builder.build_tables()
    )
    assert concepts == registry._CONCEPTS
    assert definitions == registry._DEFINITIONS
    assert releases == registry._RELEASES
    assert replicates == registry._REPLICATES
    assert refused == _json("refused_concepts.json")
    assert hashes == registry.EVIDENCE_SHA256


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("499. Person Number", "499"),
        ("$9,999,999", "9999999"),
        ("-999.00000000", "-999.00000000"),
        ("100%", "100"),
        ("9,99", None),
        ("1e4", None),
        ("not an invented number", None),
    ],
)
def test_metadata_numeric_parser_keeps_verified_precision(source, expected):
    assert _module("parse_dictionary_metadata.py").numeric(source) == expected


@given(
    lower=st.integers(min_value=0, max_value=10**9),
    width=st.integers(min_value=0, max_value=10**9),
    before=st.integers(min_value=0, max_value=3),
    after=st.integers(min_value=0, max_value=3),
    currency=st.booleans(),
)
@settings(max_examples=50, deadline=None)
def test_invented_currency_ranges_do_not_become_categorical_labels(
    lower, width, before, after, currency
):
    upper = lower + width
    prefix = "$" if currency else ""
    page = INVENTED_RANGE_PAGE.format(
        lower=f"{prefix}{lower:,}",
        upper=f"{prefix}{upper:,}",
        before=" " * before,
        after=" " * after,
    )
    parser = _module("parse_dictionary_metadata.py")
    _, fields, values, _ = parser.parse_page(page, 2021)
    assert values["item"] == {"0": "No value"}
    assert not fields["Unparsed values"]
    assert values["range"] == [
        {
            "min": str(lower),
            "max": str(upper),
            "description": "Invented dollars",
        }
    ]


def test_invented_dictionary_continuation_retains_last_code(
    tmp_path, monkeypatch
):
    parser = _module("parse_dictionary_metadata.py")
    monkeypatch.setattr(parser, "BASE", tmp_path)
    (tmp_path / "2021_dictionary.txt").write_text(INVENTED_CONTINUATION)
    (tmp_path / "2021_dictionary.pdf").write_bytes(b"INVENTED METADATA ONLY")
    (tmp_path / "pu2021_schema.json").write_text(
        json.dumps(
            [
                {
                    "name": "INVENTED_ENTRY",
                    "label": "Invented",
                    "dtype": "integer",
                }
            ]
        )
    )
    parser.derive(2021)
    derived = json.loads(
        (tmp_path / "2021_dictionary_variables.json").read_text()
    )["variables"]["INVENTED_ENTRY"]
    assert derived["dictionary_pdf_pages"] == [1, 2]
    assert derived["verified"]
    assert set(derived["values"]["item"]) == {"2010", "2015", "2021"}


def test_unparsed_invented_numeric_line_is_never_verified(
    tmp_path, monkeypatch
):
    parser = _module("parse_dictionary_metadata.py")
    monkeypatch.setattr(parser, "BASE", tmp_path)
    (tmp_path / "2021_dictionary.txt").write_text(
        "Name: INVENTED_BAD_DOMAIN\nDescription: Invented, not survey data.\n"
        "Possible Values\n1. Yes\n$1 to $999 malformed range\n1\n"
    )
    (tmp_path / "2021_dictionary.pdf").write_bytes(b"INVENTED METADATA ONLY")
    (tmp_path / "pu2021_schema.json").write_text(
        json.dumps(
            [
                {
                    "name": "INVENTED_BAD_DOMAIN",
                    "label": "Invented",
                    "dtype": "integer",
                }
            ]
        )
    )
    parser.derive(2021)
    derived = json.loads(
        (tmp_path / "2021_dictionary_variables.json").read_text()
    )["variables"]["INVENTED_BAD_DOMAIN"]
    assert not derived["verified"]
    assert derived["unparsed_value_lines"] == ["$1 to $999 malformed range"]
