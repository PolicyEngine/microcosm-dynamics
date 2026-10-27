"""Check the registry against committed data/external SIPP metadata.

These tests read only captured Census documentation: the variable API,
dictionaries, storage schemas, replicate dictionaries, release notes,
crosswalks and user notes. A guard refuses stored notes with case records;
known excluded notes retain inventory metadata only. The INVENTED_* pages
and generated note snippets are made up. Each check derives
its expectation from the evidence independently of the generator, except
the regeneration test, which runs the generator without writing.
"""

from __future__ import annotations

import gzip
import hashlib
import html
import importlib.util
import json
import re
import signal
import subprocess
import sys
import unicodedata
from datetime import datetime, timedelta
from decimal import Decimal
from functools import cache
from pathlib import Path
from urllib.parse import urlparse

import openpyxl
import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.data import sipp_income_registry as registry

EVIDENCE = (
    Path(__file__).resolve().parents[2] / "data" / "external" / "sipp_income"
)
YEARS = tuple(range(2018, 2026))
API_YEARS = tuple(range(2022, 2026))
MISSING_LABELS = ("NA-Missing", "NA or Missing")
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


@cache
def _dictionary(year):
    return _json(f"{year}_dictionary_variables.json")["variables"]


@cache
def _api(year):
    return _json(f"{year}_variables.json")["variables"]


@cache
def _schema(year):
    return {row["name"]: row for row in _json(f"pu{year}_schema.json")}


@cache
def _note_text(stored_as):
    body = gzip.decompress((EVIDENCE / stored_as).read_bytes()).decode()
    body = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", body)
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", body)).split())


def _key(text):
    """Independent label key: NFKC, casefold, letters and digits only."""
    folded = unicodedata.normalize("NFKC", text).casefold()
    return re.sub(r"[^a-z0-9]", "", folded)


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


# The registry against each release's own metadata.


@pytest.mark.parametrize("year", YEARS)
def test_registry_matches_own_release_metadata(year):
    selected = _json("concept_selection.json")["concepts"]
    for concept, spec in registry.income_variables(year).items():
        entry = _dictionary(year).get(spec.name)
        stored = _schema(year)[spec.name]
        if year in API_YEARS:
            raw = _api(year)[spec.name]
            assert spec.source == f"{year}_variables.json#{spec.name}"
            assert spec.label == raw["label"]
            assert spec.label_source == "api"
        else:
            raw = entry
            assert spec.source == (
                f"{year}_dictionary_variables.json#{spec.name}"
            )
            assert raw["verified"]
            ruling = _json("source_rulings.json")["label_conflicts"].get(
                f"{year}/{spec.name}", {}
            )
            assert spec.label == (
                ruling["label"]
                if ruling.get("resolution") == "user_note"
                else raw["dictionary_label"]
            )
        assert "Suppressed" not in (spec.label, stored["label"])
        assert spec.predicate_type == raw["predicateType"]
        assert spec.items == tuple(
            sorted(raw.get("values", {}).get("item", {}).items())
        )
        assert spec.ranges == _ranges(raw)
        assert spec.storage_type == stored["dtype"]
        assert spec.schema_label == stored["label"]
        assert spec.ownership == selected[concept]["ownership_level"]
        assert spec.period == selected[concept]["period"]
        printed = (entry or {}).get("universe", "")
        assert spec.allow_blank == (
            concept not in registry.CORE_CONCEPTS
            and spec.period != "weight"
            and " ".join(printed.split()).casefold()
            not in ("all persons", "all households")
        )
        if spec.storage_type == "string":
            assert spec.length == int(entry["length"])
            assert all(
                len(low) == len(high) == spec.length
                for low, high, _ in (*spec.ranges, *spec.check_ranges)
            )
        assert spec.structural_missing == (
            ("", ".")
            if year <= 2021 and spec.storage_type != "string"
            else ("",)
        )
        # Universes and second domains come from the same release only,
        # unless a cited ruling replaces or clears a misprinted universe.
        if spec.universe_source.startswith("source_rulings.json#"):
            assert spec.universe != printed
        else:
            assert spec.universe == printed
            if spec.universe:
                assert spec.universe_source == (
                    f"{year}_dictionary_variables.json#{spec.name}"
                )
        if year in API_YEARS and entry and entry["verified"]:
            assert spec.check_source == (
                f"{year}_dictionary_variables.json#{spec.name}"
            )
            assert spec.check_items == tuple(
                (code, label)
                for code, label in sorted(entry["values"]["item"].items())
                if label not in MISSING_LABELS
            )
            assert spec.check_ranges == _ranges(entry)
        else:
            assert spec.check_source == ""
            assert spec.check_items == spec.check_ranges == ()


@pytest.mark.parametrize("year", range(2018, 2022))
def test_admitted_dictionary_domains_replay_from_raw_pages(year):
    parser = _module("parse_dictionary_metadata.py")
    for spec in registry.income_variables(year).values():
        raw = _dictionary(year)[spec.name]
        page = _replay_page(year, raw)
        name, fields, values, printed = parser.parse_page(page, year)
        assert name == spec.name
        assert fields.get("Description", "") == raw["dictionary_label"]
        assert fields.get("Universe", "") == raw["universe"]
        assert printed == raw["dictionary_printed_page"]
        assert values == raw["values"]
        assert not fields["Unparsed values"]
        # Independently check that a source range was not swallowed into
        # the preceding categorical label by the metadata parser.
        parsed_ranges = {(lo, hi) for lo, hi, _ in spec.ranges}
        for match in RAW_RANGE.finditer(page):
            endpoints = tuple(
                token.replace("$", "").replace("%", "").replace(",", "")
                for token in match.groups()
            )
            assert endpoints in parsed_ranges


@pytest.mark.parametrize("year", range(2018, 2022))
def test_schema_labels_agree_with_dictionary_or_are_ruled(year):
    """2018-2021 labels: the schema must agree with the dictionary."""
    rulings = _json("source_rulings.json")["label_conflicts"]
    checks = {
        (row["release"], row["variable"]) for row in _json("label_checks.json")
    }
    for spec in registry.income_variables(year).values():
        schema, dictionary = (
            spec.schema_label,
            _dictionary(year)[spec.name]["dictionary_label"],
        )
        if _key(schema) == _key(dictionary):
            continue
        if len(schema) >= 255 and _key(dictionary).startswith(_key(schema)):
            continue
        ruling = rulings[f"{year}/{spec.name}"]
        assert (year, spec.name) in checks
        assert (
            spec.label
            == {
                "dictionary": dictionary,
                "schema": schema,
                "user_note": ruling.get("label"),
            }[ruling["resolution"]]
        )


def _api_key(text):
    """Label key that reads the API's "equals" and "or" as "=" and "/"."""
    return _key(
        unicodedata.normalize("NFKC", text)
        .replace("=", " equals ")
        .replace("/", " or ")
    )


@pytest.mark.parametrize("year", API_YEARS)
def test_api_labels_agree_with_the_release_dictionary(year):
    for spec in registry.income_variables(year).values():
        entry = _dictionary(year).get(spec.name)
        if not entry:
            continue
        api, printed = _api_key(spec.label), _api_key(
            entry["dictionary_label"]
        )
        short, full = sorted((api, printed), key=len)
        assert api == printed or (
            min(len(spec.label), len(entry["dictionary_label"])) >= 255
            and full.startswith(short)
        ), (year, spec.name)


@pytest.mark.parametrize("year", YEARS)
def test_admission_and_refusal_follow_the_evidence(year):
    """Every refusal has a cause in this release's own evidence."""
    selection = _json("concept_selection.json")
    rulings = _json("source_rulings.json")
    crosswalk = selection["release_crosswalk"][str(year)]
    refused = _json("refused_concepts.json")[str(year)]
    admitted = registry.income_variables(year)
    assert set(crosswalk) == set(selection["concepts"])
    assert admitted.keys() | refused.keys() == set(crosswalk)
    assert not admitted.keys() & refused.keys()
    assert set(registry.CORE_CONCEPTS) <= admitted.keys()
    api = _api(year) if year in API_YEARS else {}
    for concept, reason in refused.items():
        name = crosswalk[concept] or selection["concepts"][concept]["raw_name"]
        labels = (
            _schema(year).get(name, {}).get("label", ""),
            _dictionary(year).get(name, {}).get("dictionary_label", ""),
            api.get(name, {}).get("label", ""),
        )
        if reason == "absent or suppressed in release":
            assert crosswalk[concept] is None
            assert name not in _schema(year) or "Suppressed" in labels
        elif reason == "dictionary domain unverified":
            assert year < 2022
            assert not _dictionary(year).get(name, {}).get("verified")
        elif reason in (
            "open conflict: schema label",
            "open conflict: dictionary label",
        ):
            assert rulings["label_conflicts"][f"{year}/{name}"][
                "resolution"
            ] is (None)
        elif reason == "open conflict: suppressed in one source":
            assert crosswalk[concept] is None
            stated = [label for label in labels if label]
            assert "Suppressed" in stated
            assert any(label != "Suppressed" for label in stated)
            assert rulings["suppression_conflicts"][f"{year}/{name}"][
                "resolution"
            ] is (None)
        elif reason == "open conflict: code meanings":
            assert rulings["code_conflicts"][f"{year}/{name}"][
                "resolution"
            ] is (None)
        elif reason == "open conflict: release metadata and user note":
            (family,) = [
                rule
                for rule in rulings["release_family_conflicts"]
                if rule["release"] == year
            ]
            entry = _dictionary(year)[name]
            text = " ".join(entry[field] for field in family["fields"])
            assert re.search(family["pattern"], text, re.I)
        else:
            pytest.fail(f"unexpected refusal reason {reason!r}")
    for concept, spec in admitted.items():
        assert crosswalk[concept] == spec.name
        assert spec.name in _schema(year)


def test_rulings_cite_committed_evidence_that_says_so():
    """Each ruling's claim appears in the evidence it cites."""
    rulings = _json("source_rulings.json")
    evidence = {
        path
        for section in ("label_conflicts", "code_conflicts")
        for ruling in rulings[section].values()
        for path in ruling.get("evidence", [])
    } | {
        path
        for rule in rulings["release_family_conflicts"]
        for path in rule["evidence"]
    }
    for rule in rulings["corrected_releases"].values():
        evidence.update(rule["evidence"])
    for path in evidence:
        assert path in registry.EVIDENCE_SHA256
        assert (
            hashlib.sha256((EVIDENCE / path).read_bytes()).hexdigest()
            == registry.EVIDENCE_SHA256[path]
        )
    real_estate = _note_text(
        "user_notes/2018/2018sipp-metadata-for-rental-properties-"
        "other-real-estate.html.gz"
    )
    assert "were incorrect in the data dictionary files" in real_estate
    assert (
        "for respondents with a spouse or civil union partner in the "
        "household" in real_estate
    )
    for key in ("2018/EJSOWNRE", "2018/EJSOWNRP"):
        ruling = rulings["label_conflicts"][key]
        assert ruling["resolution"] == "user_note"
        assert ruling["label"] in real_estate
        assert ruling["universe"] in real_estate
    for anomaly in rulings["universe_anomalies"]:
        for year in anomaly["releases"]:
            for name in anomaly["variables"]:
                assert _dictionary(year)[name]["universe"] == (
                    anomaly["printed"]
                )
    assert _dictionary(2021)["ERETANY"]["universe"].endswith("EPENANY=2)")
    assert _dictionary(2023)["TRET3AMT"]["universe"] == "ERETTYP3YN = 1"
    ssi = _note_text("user_notes/2018/2018-reason-ssi-recpt-answ-catg.html.gz")
    assert "1. Blind or disabled 2. Aged (65 and over) 3. Other" in ssi
    assert "1. Aged (65 and over) 2. Blind or disabled 3. Other" in ssi
    social_security = _note_text(
        "user_notes/2022/2022-prior-process-err-affct-soc-sec-self-amts"
        ".html.gz"
    )
    assert "only applicable to SIPP data downloaded prior to 7/24/2025" in (
        social_security
    )
    joint = _note_text(
        "user_notes/2020/2020-univ-joint-held-assets-debts.html.gz"
    )
    assert "EREGDOMPART, was removed in the 2020 SIPP" in joint


@pytest.mark.parametrize("year", (2021, 2022))
def test_ssi_begin_reason_code_conflict_matches_publication(year):
    ruling = _json("source_rulings.json")["code_conflicts"][
        f"{year}/ESSI_BRSN"
    ]
    published = (
        _api(year)["ESSI_BRSN"] if year in API_YEARS else _dictionary(year)
    )
    if year in API_YEARS:
        items = published["values"]["item"]
    else:
        items = published["ESSI_BRSN"]["values"]["item"]
    assert {
        code: label for code, label in items.items() if code != "-9"
    } == ruling["as_published"]
    for other in (2018, 2023):
        assert (
            _dictionary(other)["ESSI_BRSN"]["values"]["item"]["1"]
            == "Blind or disabled"
        )


def test_2020_joint_family_matches_the_note_and_spares_other_years():
    refused = _json("refused_concepts.json")
    reason = "open conflict: release metadata and user note"
    family = sorted(c for c, r in refused["2020"].items() if r == reason)
    assert len(family) == 70
    names = {
        _json("concept_selection.json")["release_crosswalk"]["2020"][c]
        for c in family
    }
    assert all(re.match(r"[ET]J[SO]", name) for name in names)
    for year in (2018, 2019, 2021, 2022, 2023, 2024, 2025):
        assert reason not in refused[str(year)].values()


def _inside(value, items, ranges):
    return value in {Decimal(code) for code in items} or any(
        Decimal(low) <= value <= Decimal(high) for low, high in ranges
    )


@pytest.mark.parametrize("year", API_YEARS)
def test_domain_checks_record_every_api_dictionary_difference(year):
    """Probe every boundary of both sources independently of the generator."""
    recorded = {
        row["concept"]: row
        for row in _json("domain_checks.json")
        if row["release"] == year
    }
    for concept, spec in registry.income_variables(year).items():
        entry = _dictionary(year).get(spec.name)
        if not entry or not entry["verified"]:
            assert recorded[concept]["dictionary"] is None
            continue
        api = _api(year)[spec.name].get("values", {})
        api_items = [
            code
            for code, label in api.get("item", {}).items()
            if label not in MISSING_LABELS
        ]
        api_ranges = [(r["min"], r["max"]) for r in api.get("range", [])]
        printed = entry["values"]
        dict_items = list(printed["item"])
        dict_ranges = [(r["min"], r["max"]) for r in printed.get("range", [])]
        # Integer variables admit only integers, so half steps would report
        # differences no value can exhibit.
        integral = spec.storage_type != "float" and spec.period != "weight"
        deltas = (Decimal(-1), Decimal(0), Decimal(1)) + (
            () if integral else (Decimal("-0.5"), Decimal("0.5"))
        )
        probes = {
            Decimal(point) + delta
            for point in (
                *api_items,
                *dict_items,
                *(end for pair in (*api_ranges, *dict_ranges) for end in pair),
            )
            for delta in deltas
        }
        differs = any(
            _inside(value, api_items, api_ranges)
            != _inside(value, dict_items, dict_ranges)
            for value in probes
        )
        assert (concept in recorded) == differs, (year, concept)
    for name in ("GHLFSAM", "GVARSTR", "SHHADID", "SSUID"):
        (row,) = [r for r in recorded.values() if r["variable"] == name]
        assert row["api"] == []
        assert row["admitted"] == row["dictionary"]


def test_record_levels_match_period_and_ownership():
    """Census's 2022 record levels against each concept's tags."""
    for concept, spec in registry.income_variables(2022).items():
        level = _dictionary(2022)[spec.name]["record_level"]
        if level == "Person-month":
            assert spec.period in ("monthly", "weight", "interview"), concept
            if spec.period == "interview":
                assert spec.name == "EHRESIDENCID"
        elif level == "Household":
            assert spec.ownership in ("household", "sample_unit"), concept
        else:
            assert level == "Person"
            assert spec.ownership not in ("household",), concept
            assert spec.period != "monthly", concept


@pytest.mark.parametrize("year", YEARS)
def test_storage_types_match_census_input_schema(year):
    for spec in registry.income_variables(year).values():
        assert spec.storage_type == _schema(year)[spec.name]["dtype"]
    table = registry.income_variables(year)
    assert table["sample_unit_id"].storage_type == "string"
    assert table["weight"].storage_type == "float"


# Census's own release-to-release crosswalks (a differential check).


def _census_crosswalk(year):
    book = openpyxl.load_workbook(
        EVIDENCE / f"crosswalk_{year}_to_{year + 1}.xlsx", read_only=True
    )
    rows = list(book.worksheets[0].iter_rows(values_only=True))
    assert rows[0][0] == year and rows[0][3] == year + 1
    assert rows[1][0].strip() == rows[1][3].strip() == "Variable Name"
    pairs = [(row[0], row[3]) for row in rows[2:] if row[0] or row[3]]
    forward, backward = {}, {}
    for old, new in pairs:
        forward.setdefault(old, set()).add(new)
        backward.setdefault(new, set()).add(old)
    return forward, backward


#: Census's crosswalk maps 2018's top-code standard deviation TMHLOAN_STD
#: to 2019's loan count TMHLOAN_NUM, though both releases carry
#: TMHLOAN_NUM with the same label and codes; the registry follows the
#: dictionaries.
CENSUS_CROSSWALK_EXCEPTIONS = {(2018, "TMHLOAN_STD", "TMHLOAN_NUM")}


@pytest.mark.parametrize("year", (2018, 2019, 2020, 2021))
def test_crosswalk_agrees_with_census_crosswalk(year):
    selection = _json("concept_selection.json")
    ours, theirs = (
        selection["release_crosswalk"][str(year)],
        selection["release_crosswalk"][str(year + 1)],
    )
    forward, backward = _census_crosswalk(year)
    no_match = "*** NO MATCH AVAILABLE ***"
    for concept in ours:
        old, new = ours[concept], theirs[concept]
        if old and new:
            assert old == new
            assert new in forward[old]
        elif old and not new:
            raw = _schema(year + 1).get(old, {}).get("label", "")
            mapped = forward.get(old, {None})
            assert (
                mapped <= {None, no_match}
                or raw == "Suppressed"
                or old not in _schema(year + 1)
            ), (concept, old, mapped)
        elif new and not old:
            raw = _schema(year).get(new, {}).get("label", "")
            mapped = backward.get(new, {None})
            assert (
                mapped <= {None, no_match}
                or raw == "Suppressed"
                or new not in _schema(year)
            ), (concept, new, mapped)
    names = {name for name in [*ours.values(), *theirs.values()] if name}
    renames = {
        (year, old, new)
        for old, targets in forward.items()
        for new in targets
        if old
        and new
        and new != no_match
        and old != new
        and (old in names or new in names)
    }
    assert renames <= CENSUS_CROSSWALK_EXCEPTIONS


# The explicit release-change ledger.


def _changes(concept, field):
    return [
        row
        for row in _json("release_changes.json")
        if row["concept"] == concept and row["field"] == field
    ]


def test_release_changes_record_the_known_semantic_changes():
    universe = {
        (row["from"], row["to"])
        for row in _changes("retirement_received_year", "universe")
    }
    assert {(2020, 2021), (2021, 2022)} <= universe
    label = _changes("retirement_received_year", "dictionary_label")
    assert [(row["from"], row["to"]) for row in label] == [(2022, 2023)]
    assert "other retirement income" in label[0]["after"]
    withdrawals = _changes("thrift_401k_403b_withdrawal_received", "universe")
    assert [(row["from"], row["to"]) for row in withdrawals] == [(2021, 2022)]
    assert "eeveret" in withdrawals[0]["before"]
    assert "eeveret" not in withdrawals[0]["after"]
    spouse = _changes("checking_joint_spouse_owned", "universe")
    assert [(row["from"], row["to"]) for row in spouse] == [(2019, 2021)]
    assert "eregdompart" in spouse[0]["before"]
    assert "eregdompart" not in spouse[0]["after"]
    offer = _changes("employer_retirement_plan_offered", "admission")
    assert [(row["from"], row["to"], row["after"]) for row in offer] == [
        (2020, 2021, "admitted")
    ]
    reason = _changes("ssi_begin_reason", "admission")
    assert [(row["from"], row["to"]) for row in reason] == [
        (2020, 2021),
        (2022, 2023),
    ]
    entry = _changes("entry_year_code", "codes")
    assert entry and all(
        any(row["before"][kind] for kind in ("changed", "added", "removed"))
        for row in entry
    )


def test_release_changes_cover_every_admitted_pair():
    """Recompute names and admission transitions independently."""
    selection = _json("concept_selection.json")
    rows = _json("release_changes.json")
    for concept in selection["concepts"]:
        admitted = [
            year
            for year in YEARS
            if concept in registry.income_variables(year)
        ]
        transitions = {
            (year, year + 1)
            for year in YEARS[:-1]
            if (year in admitted) != (year + 1 in admitted)
        }
        recorded = {
            (row["from"], row["to"])
            for row in rows
            if row["concept"] == concept and row["field"] == "admission"
        }
        assert recorded == transitions
        for before, after in zip(admitted[:-1], admitted[1:], strict=True):
            old = registry.income_variables(before)[concept]
            new = registry.income_variables(after)[concept]
            if old.name != new.name:
                assert any(
                    row["concept"] == concept
                    and row["field"] == "name"
                    and (row["from"], row["to"]) == (before, after)
                    for row in rows
                )


# User notes, release notes and corrections.


def test_user_notes_manifest_pins_every_stored_note():
    manifest = _json("user_notes_manifest.json")
    stored = [row for row in manifest if row["stored_as"]]
    assert len(manifest) == 355
    assert len(stored) == 101
    for row in manifest:
        assert urlparse(row["url"]).hostname == "www.census.gov"
        assert "/sipp/tech-documentation/user-notes" in row["url"]
        if row.get("status") == "excluded_record_bearing":
            continue
        assert row["http_status"] == 200
        assert datetime.fromisoformat(row["retrieved_utc"]).utcoffset() == (
            timedelta(0)
        )
    for row in stored:
        payload = gzip.decompress((EVIDENCE / row["stored_as"]).read_bytes())
        assert len(payload) == row["bytes"]
        assert hashlib.sha256(payload).hexdigest() == row["sha256"]
        if row["kind"] == "note":
            text = _note_text(row["stored_as"])
            for variable in row["variables"]:
                assert re.search(rf"\b{variable}\b", text)
    on_disk = {
        str(path.relative_to(EVIDENCE))
        for path in (EVIDENCE / "user_notes").rglob("*.gz")
    }
    assert on_disk == {row["stored_as"] for row in stored}


def test_every_stored_user_note_passes_record_bearing_guard():
    checker = _module("capture_user_notes.py").record_bearing_note
    for path in sorted((EVIDENCE / "user_notes").rglob("*.gz")):
        body = gzip.decompress(path.read_bytes()).decode("utf-8", "replace")
        if checker(body):
            # Never return a matched identifier, value or captured text.
            pytest.fail(str(path.relative_to(EVIDENCE)))


def test_excluded_notes_retain_only_cited_inventory_metadata():
    capture = _module("capture_user_notes.py")
    excluded = [
        row
        for row in _json("user_notes_manifest.json")
        if row.get("status") == "excluded_record_bearing"
    ]
    assert {row["url"] for row in excluded} == capture.EXCLUDED_NOTE_URLS
    assert len(excluded) == 8
    for row in excluded:
        assert set(row) == {
            "url",
            "title",
            "release",
            "variables",
            "kind",
            "stored_as",
            "status",
            "exclusion_reason",
        }
        assert row["stored_as"] is None
        assert row["title"] and row["variables"]
        assert row["release"] in YEARS
        assert row["kind"] == "note"
        assert "URL and title only" in row["exclusion_reason"]
        removed_path = (
            f"user_notes/{row['release']}/{Path(row['url']).stem}.html.gz"
        )
        assert removed_path not in registry.EVIDENCE_SHA256
    for _, url, body_path, status in registry._NOTE_TABLE:
        if url in capture.EXCLUDED_NOTE_URLS:
            assert body_path == ""
            assert status == "excluded_record_bearing"


@given(
    st.sampled_from(
        sorted(_module("capture_user_notes.py").EXCLUDED_NOTE_URLS)
    )
)
@settings(deadline=None)
def test_known_record_bearing_urls_refuse_before_request(url):
    capture = _module("capture_user_notes.py")

    def invented_request(*args, **kwargs):
        pytest.fail("Capture exclusion attempted a request")

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(capture.requests, "get", invented_request)
        with pytest.raises(
            ValueError, match="Excluded record-bearing note URL"
        ):
            capture.fetch(url)


@given(
    identifier=st.sampled_from(("SSUID", "PNUM", "ssuid", "pnum")),
    invented_digits=st.text(alphabet="0123456789", min_size=1, max_size=20),
    separator=st.sampled_from(("", " ", ": ", "=", "&#58;&nbsp;", " ('")),
    table=st.booleans(),
    closed=st.booleans(),
    heading_tag=st.sampled_from(("th", "td")),
    preceding_row=st.booleans(),
)
@settings(deadline=None)
def test_invented_identifier_records_always_trigger_capture_guard(
    identifier,
    invented_digits,
    separator,
    table,
    closed,
    heading_tag,
    preceding_row,
):
    if table:
        prefix = (
            "<tr><td>Invented heading</td><td>Invented annotation</td></tr>"
            if preceding_row
            else ""
        )
        body = (
            f"<table>{prefix}<tr><{heading_tag}>{identifier}</{heading_tag}>"
            "<td>Invented annotation</td></tr>"
            f"<tr><td>{invented_digits}</td><td>Invented annotation</td></tr>"
        )
        if closed:
            body += "</table>"
    else:
        body = f"<p>{identifier}{separator}{invented_digits}</p>"
    assert _module("capture_user_notes.py").record_bearing_note(body)


@given(
    identifier=st.sampled_from(("SSUID", "PNUM")),
    table=st.booleans(),
    row_tag=st.sampled_from(("th", "td")),
    row_scope=st.sampled_from(("", ' scope="row"')),
)
@settings(deadline=None)
def test_invented_identifier_definitions_are_metadata(
    identifier, table, row_tag, row_scope
):
    if table:
        body = (
            "<table><tr><th>Variable</th><th>Description</th>"
            "<th>Universe</th></tr>"
            f"<tr><{row_tag}{row_scope}>{identifier}</{row_tag}>"
            "<td>Invented person linkage variable</td>"
            "<td>All invented persons</td></tr>"
            "<tr><td>INVENTED_AMOUNT</td><td>Invented amount</td>"
            f"<td>{identifier} identifies invented persons</td></tr></table>"
        )
    else:
        body = f"<p>{identifier} is an invented survey linkage variable.</p>"
    assert not _module("capture_user_notes.py").record_bearing_note(body)


INVENTED_ID = "000011112222333"
# Invented pages, from the round-3 review's probe, in each form a case record
# can take on a page. None is Census text.
INVENTED_RECORD_PAGES = {
    "wide_header_row": (
        "<table><tr><th>SSUID</th><th>PNUM</th><th>MONTHCODE</th></tr>"
        f"<tr><td>{INVENTED_ID}</td><td>101</td><td>1</td></tr></table>"
    ),
    "prose_adjacent": f"<p>SSUID: {INVENTED_ID}</p>",
    "long_td_definition_style": (
        "<table><tr><th>Variable</th><th>Description</th><th>Value</th></tr>"
        "<tr><td>SSUID</td><td>Invented sample unit</td>"
        f"<td>{INVENTED_ID}</td></tr>"
        "<tr><td>PNUM</td><td>Invented person</td><td>101</td></tr>"
        "<tr><td>INVENTED_EARN</td><td>Invented earnings</td>"
        "<td>-4321</td></tr></table>"
    ),
    "long_th_row_header_definition_style": (
        "<table><tr><th>Variable</th><th>Description</th>"
        "<th>Value for this case</th></tr>"
        "<tr><th>SSUID</th><td>Invented sample unit</td>"
        f"<td>{INVENTED_ID}</td></tr>"
        "<tr><th>PNUM</th><td>Invented person</td><td>101</td></tr></table>"
    ),
    "long_name_label_value": (
        "<table><tr><th>Name</th><th>Label</th><th>Original</th>"
        "<th>Corrected</th></tr><tr><th>SSUID</th><td>Invented unit</td>"
        f"<td>{INVENTED_ID}</td><td>{INVENTED_ID}</td></tr></table>"
    ),
    "scope_row_with_description": (
        "<table><tr><td>Item</td><td>Invented</td></tr>"
        '<tr><th scope="row">SSUID</th><td>(invented unit)</td>'
        f"<td>{INVENTED_ID}</td></tr></table>"
    ),
    "header_with_parenthetical": (
        "<table><tr><th>SSUID (invented unit)</th><th>PNUM (person)</th>"
        f"<th>Month</th></tr><tr><td>{INVENTED_ID}</td><td>101</td>"
        "<td>1</td></tr></table>"
    ),
    "header_after_title_row_with_dashed_values": (
        "<table><tr><td colspan=3>Invented table</td></tr>"
        "<tr><td>SSUID</td><td>PNUM</td><td>MONTHCODE</td></tr>"
        "<tr><td>0000-1111-2222</td><td>101</td><td>1</td></tr></table>"
    ),
    "pre_block": f"<pre>SSUID           PNUM MONTHCODE\n{INVENTED_ID} 101  1\n</pre>",
    "csv_text": f"<p>SSUID,PNUM,MONTHCODE<br>{INVENTED_ID},101,1</p>",
    "prose_words_between": (
        f"<p>The SSUID for this case is {INVENTED_ID} and its PNUM is 101.</p>"
    ),
    "prose_of": f"<p>The case with SSUID of {INVENTED_ID} is invented.</p>",
    "prose_em_dash": f"<p>SSUID &mdash; {INVENTED_ID}</p>",
    "prose_plural": f"<p>SSUIDs {INVENTED_ID} and {INVENTED_ID[::-1]}</p>",
    "person_months_without_identifier": (
        "<table><tr><th>Month</th><th>Earnings</th><th>Hours</th></tr>"
        "<tr><td>1</td><td>-250</td><td>40</td></tr></table>"
    ),
    "comment": f"<p>Invented note.</p><!-- SSUID {INVENTED_ID} -->",
    # Round 4: the page source, signed and bracketed amounts, and numbers in
    # a preformatted block.
    "attribute_identifier": f'<p title="SSUID {INVENTED_ID}">Invented.</p>',
    "script_identifier": (
        f'<script>var invented = "SSUID={INVENTED_ID}";</script>'
    ),
    "bare_identifier_value_in_attribute": f'<img alt="{INVENTED_ID}">',
    "bare_identifier_value_in_comment": f"<!-- {INVENTED_ID} -->",
    "signed_and_bracketed_amounts": (
        "<table><tr><td>-$250</td><td>($40)</td><td>\u2212$12</td></tr>"
        "</table>"
    ),
    "pre_numbers": "<pre>101 -250 40\n</pre>",
    # Round 5: an identifier inside a heading, a five-digit value and a year
    # run straight after an identifier.
    "identifier_inside_heading": (
        "<table><tr><th>Person number (PNUM)</th>"
        "<th>Invented monthly earnings amount in dollars</th></tr>"
        "<tr><td>101</td><td>-25</td></tr></table>"
    ),
    "five_digits_after_identifier": "<p>SSUID invented 20221</p>",
    "year_straight_after_identifier": "<p>SSUID 2022</p>",
    # Only href and src values are removed from the source, and only inside
    # tags, which open with a letter, "!" or "/".
    "identifier_in_data_src": '<p data-src="ssuid-7">Invented</p>',
    "script_assigning_src": '<script>var src = "PNUM=101";</script>',
    "script_comparison_around_src": (
        '<script>var a = 1 < 2; img.src = "PNUM=101"; var b = 3 > 2;'
        "</script>"
    ),
    # Round 6: a header cell after the first row, and a first-row cell that
    # is not a header cell, each naming an identifier after other words.
    "identifier_inside_later_header_cell": (
        "<table><tr><td>Invented</td></tr>"
        "<tr><th>Invented person number (PNUM).</th></tr>"
        "<tr><td>101</td></tr></table>"
    ),
    "identifier_inside_first_row_cell": (
        "<table><tr><td>Person number (PNUM)</td>"
        "<td>Invented monthly earnings amount in dollars</td></tr>"
        "<tr><td>101</td><td>-25</td></tr></table>"
    ),
    # Round 7: script and style contents are read as they stand, so no "<"
    # in code hides a src assignment, with or without an end tag.
    "script_minified_comparison": (
        '<script>for(i=0;i<n;i++){img.src="PNUM=101"}</script>'
    ),
    "script_cdata": (
        '<script>//<![CDATA[\nimg.src = "PNUM=101";\n//]]></script>'
    ),
    "script_end_tag_like": (
        '<script>var t = a</b; img.src = "PNUM=101"; c > d;</script>'
    ),
    "script_unquoted_src": (
        "<script>for(i=0;i<n;i++){img.src=PNUM+101}</script>"
    ),
    "unclosed_script": "<script>for(i=0;i<n;i++){img.src=PNUM+101} c > d",
    "style_contents": "<style>a<b{} x{src=PNUM+101}</style>",
    # Round 7: each quoted attribute value and script string is also read
    # alone, so a quote, equals sign or angle bracket inside one stops no
    # window.
    "attribute_value_with_apostrophe": (
        '<img alt="PNUM (person\'s number) 101">'
    ),
    "single_quoted_attribute_value": "<img alt='PNUM (the \"person\") 101'>",
    "attribute_value_with_equals": '<img alt="PNUM value=105">',
    "attribute_value_with_quote_entity": '<img alt="PNUM &quot;x&quot; 105">',
    "attribute_value_with_bracket_entities": (
        '<img alt="PNUM &lt;x&gt; 101">'
    ),
    "attribute_value_with_markup_entities": (
        '<img alt="&lt;b&gt;PNUM&lt;/b&gt; 101">'
    ),
    "script_string_with_markup": (
        '<script>el.innerHTML = "<b>PNUM</b> 101";</script>'
    ),
    "script_string_with_cells": (
        '<script>row.innerHTML = "<td>PNUM</td><td>101</td>";</script>'
    ),
    # Round 7: an unquoted data-src value is kept, quoted values are read
    # with entities decoded and from tags in either case, and the strings
    # of a script without an end tag are read too, past their backslash
    # escapes.
    "unquoted_data_src": "<p data-src=ssuid-7>Invented</p>",
    "attribute_value_with_encoded_digits": (
        '<img alt="PNUM value&#61;&#49;05">'
    ),
    "upper_case_tag_attribute_value": (
        '<IMG ALT="PNUM (person\'s number) 101">'
    ),
    "unclosed_script_string": '<script>s = "PNUM <i 101"; t = x > y;',
    "script_string_with_escaped_quotes": (
        '<script>s = "PNUM \\"x\\" 101";</script>'
    ),
    # Round 7: outside scripts, "<" before a sign opens no tag either.
    "text_comparison_before_src": (
        '<p>Invented: if a <= 2 then src="PNUM=101"</p>'
    ),
    # Round 7: the same-row rule reads every other cell, even one that names
    # an identifier too, and both cell conditions of the heading-names rule.
    "heading_names_identifier_beside_identifier_cell": (
        "<table><tr><th>Person number (PNUM)</th><td>SSUID of the invented "
        "case, described here at some length 101</td></tr></table>"
    ),
    "identifier_cell_beside_identifier_cell": (
        "<table><tr><th>Item</th><th>Note</th></tr><tr><td>PNUM</td>"
        "<td>SSUID of the invented case, described here at some length 101"
        "</td></tr></table>"
    ),
    "first_row_cell_names_identifier_beside_value": (
        "<table><tr><td>Invented note on the PNUM.</td><td>101</td></tr>"
        "</table>"
    ),
    "later_header_cell_names_identifier_beside_value": (
        "<table><tr><td>Invented</td></tr>"
        "<tr><th>Invented person number (PNUM).</th><td>101</td></tr>"
        "</table>"
    ),
    # Round 8: a "<script" inside a quoted value opens no element, as a
    # "<b" there opens no tag, so its src is no link target.
    "script_tag_inside_quoted_value": '<a href="<script src="PNUM=101">',
    "tag_inside_quoted_value": '<a href="<b src="PNUM=101">',
    # Round 8: template literals are read as script strings.
    "template_literal_with_markup": (
        "<script>el.innerHTML = `<b>PNUM</b> 101`;</script>"
    ),
    "template_literal_with_apostrophe": (
        "<script>s = `PNUM (person's number) 101`;</script>"
    ),
    "template_literal_with_equals": "<script>s = `PNUM value=105`;</script>",
    "template_literal_with_quotes": '<script>s = `PNUM "x" 105`;</script>',
    # Round 8: in the text as a browser reads it, a "<" opens a tag only
    # before a letter, "!" or "/", and title, textarea and xmp contents are
    # text; quoted strings in a style are read alone.
    "text_comparison": "<p>PNUM < 101</p>",
    "text_assignment_arrow": "<p><code>PNUM <- 101</code></p>",
    "text_value_in_angle_brackets": "<p>PNUM: <101></p>",
    "textarea_contents": '<textarea>a<b src="PNUM=101"</textarea>',
    "title_contents": "<title>PNUM <i 101</title>",
    "xmp_contents": "<xmp>PNUM <i 101</xmp>",
    "style_string": (
        '<style>a::after{content:"PNUM (person\'s number) 101"}</style>'
    ),
    # Round 8: the review's mutants O1-O10 of the script and style split,
    # the script strings, the attribute names and the same-row rule.
    "multi_line_script_code": (
        "<script>\nfor(i=0;i<n;i++){img.src=PNUM+101}\n</script>"
    ),
    "multi_line_script_string": (
        '<script>\nel.innerHTML = "<b>PNUM</b> 101";\n</script>'
    ),
    "upper_case_script_code": (
        "<SCRIPT>for(i=0;i<n;i++){img.src=PNUM+101}</SCRIPT>"
    ),
    "single_quoted_script_string": (
        "<script>el.innerHTML = '<b>PNUM</b> 101';</script>"
    ),
    "script_code_after_end_tag_in_string": (
        '<script>x = "</b>"; if(a<b) src=PNUM+101;</script>'
    ),
    "upper_case_script_string": (
        '<SCRIPT>el.innerHTML = "<b>PNUM</b> 101";</SCRIPT>'
    ),
    "hyphenated_attribute_name": (
        '<img data-src="PNUM (person\'s number) 101">'
    ),
    "value_cell_before_later_identifier_cell": (
        "<table><tr><td>a</td><td>b</td></tr>"
        "<tr><td>101</td><td>PNUM of the case</td></tr></table>"
    ),
    "spaces_around_equals": '<img alt = "PNUM (person\'s number) 101">',
    "attribute_value_in_script": (
        '<script type="text/template">it\'s '
        '<img alt="PNUM (person\'s number) 101"></script>'
    ),
    # Round 8: the source is read both with script and style elements found
    # where a browser starts them and with one at every "<script" or
    # "<style". Each of these pages is refused by one reading alone: a
    # "<script" right after an unclosed tag, and a script that the other
    # reading's style element, started inside a quoted value, ends within.
    "script_inside_unclosed_tag": "<a<script>if(i<n) src=PNUM+101;</script>",
    "script_after_style_tag_in_quoted_value": (
        '<a title="<style>"><script>x="</style>"; if(i<n) src=PNUM+101;'
        "</script>"
    ),
    # Round 8: an unclosed element read past the page's last ">", a string
    # closed by the last unescaped quote mark before an escaped one, and a
    # cell of digits below an identifier cell that has one above it too.
    "unclosed_pre_after_last_bracket": "<pre>SSUID. x\n7",
    "script_string_before_escaped_quote_mark": (
        '<script>s = "PNUM (person\'s number) 101"; // \\"</script>'
    ),
    "digits_above_and_below_identifier_cell": (
        "<table><tr><td>Invented</td><td>Table</td></tr>"
        "<tr><td>7</td><td>x</td></tr><tr><td>PNUM</td><td>Invented</td>"
        "</tr><tr><td>7</td><td>x</td></tr></table>"
    ),
    # Round 9: a script name with a long s, which "(?i)script" reads. Its
    # end tag "</script>" spells the name another way, so the text keeps
    # the script, and the script's strings end there, as in round 8.
    "script_name_with_long_s": "<\u017fcript>Invented</script> PNUM 101",
    "string_after_script_name_with_long_s": (
        '<\u017fcript>a = "x</script><script>s = "<b>PNUM</b> 101";</script>'
    ),
}
# Invented definition-only pages, which name an identifier with no value.
INVENTED_DEFINITION_PAGES = {
    "definition_table_heading_cell": (
        "<table><tr><th>Variable</th><th>Description</th>"
        "<th>Universe</th></tr><tr><th>SSUID</th>"
        "<td>Invented linkage variable</td><td>All invented persons</td>"
        "</tr></table>"
    ),
    "definition_prose": (
        "<p>SSUID is an invented survey linkage variable.</p>"
    ),
    "universe_footer": (
        "<p>Universe: INVENTED_VAR = PNUM. "
        "Page Last Revised - July 1, 2025</p>"
    ),
    # Tracking numbers shorter than SSUID: as text in a comment (after a
    # ">", so only the comment rule removes it), in a noscript block, and in
    # an attribute.
    "tracking_number_in_comment": (
        "<p>Invented note.</p><!-- invented > 123456789012 -->"
    ),
    "tracking_number_in_noscript": (
        "<p>Invented note.</p><noscript>123456789012</noscript>"
    ),
    "tracking_number_in_attribute": (
        "<p>Invented note.</p><noscript><img src=x?id=123456789012>"
        "</noscript>"
    ),
    # Years beside identifier names are panel and release years.
    "universe_footer_without_period": (
        "<p>Universe: INVENTED_VAR = PNUM "
        "Page Last Revised - July 1, 2025</p>"
    ),
    "panel_year": "<p>PNUM in the 2022 panel is invented.</p>",
    "index_link_with_year": (
        '<li><a href="/invented/2022-usernotes/invented.html" '
        'title="Invented PNUM note, 2022">Invented PNUM note (2022)</a></li>'
    ),
    "definition_row_with_year": (
        "<table><tr><th>Variable</th><th>Description</th></tr>"
        "<tr><td>SSUID</td><td>Invented since 2018</td></tr></table>"
    ),
    # Round 5: identifier names in attributes, scripts and link targets,
    # beside numbers that sit in other attribute values or strings.
    "image_alt_beside_dimensions": (
        '<img src="/invented/diagram.png" alt="SSUID structure" '
        'width="640" height="360">'
    ),
    "index_link_slug": (
        '<li><a href="/invented/2024-usernotes/ssuid-2024-invented.html">'
        "Invented SSUID note</a></li>"
    ),
    "attribute_beside_position": (
        '<a href="/invented/note.html" title="Invented PNUM note" '
        'data-position="105">Invented</a>'
    ),
    "script_strings": (
        '<script>var invented = {"title": "Invented PNUM note", '
        '"id": "4567"};</script>'
    ),
    "anchor_title_and_href": '<a title="PNUM" href="/invented/101">x</a>',
    "tracking_number_in_link_target": (
        '<p>Invented note.</p><img src="/invented.png?id=123456789012">'
    ),
    "row_header_outside_definition_table": (
        "<table><tr><th>Item</th><th>Note</th></tr>"
        '<tr><th scope="row">SSUID</th><td>Invented unit identifier</td>'
        "</tr></table>"
    ),
    "pre_two_numbers_per_line": "<pre>101 -250\n40</pre>",
    # Round 6: a body cell names an identifier after other words, which only
    # first-row and header cells may do.
    "identifier_named_in_body_cell": (
        "<table><tr><th>Item</th><th>Note</th></tr>"
        "<tr><td>Invented PNUM note</td><td>x</td></tr>"
        "<tr><td>7</td><td>x</td></tr></table>"
    ),
    # Round 7: link targets are removed from tags in either case, from
    # tags that open with "!" or "/", and from script opening tags.
    "upper_case_link_target": '<A HREF="/ssuid-2024-x.html">Invented</A>',
    "cdata_link_target": '<![CDATA[ href="/ssuid-2024-x.html" ]]>',
    "doctype_link_target": '<!DOCTYPE x href="/ssuid-2024-x.html">',
    "end_tag_link_target": '</a href="/ssuid-2024-x.html">',
    "script_opening_tag_link_target": (
        '<script src="/invented/ssuid-2024-x.js"></script>'
    ),
    # Round 8: noscript and iframe contents are markup in the text as a
    # browser reads it, so the link targets of their tags are not text.
    "noscript_link_target": (
        '<noscript><img src="/invented/ssuid-2024-x.gif"></noscript>'
    ),
    "iframe_link_target": (
        '<iframe><a href="/invented/ssuid-2024-x.html">x</a></iframe>'
    ),
    # Round 8: a style with no end tag leaves the script after it out of
    # the text all the same.
    "script_after_unclosed_style": (
        "<style>a{}</p><script>var invented = "
        '{"title": "Invented PNUM note", "id": "4567"};</script>'
    ),
    # Round 9: a script name with a dotted capital I, which "(?i)script"
    # matches and "</script>" closes, read without error.
    "script_name_with_dotted_capital_i": (
        '<SCR\u0130PT>var invented = {"id": "4567"};</script>'
        "<p>SSUID names the invented household.</p>"
    ),
}

# Each refused page and a twin that differs only in the structure one rule
# reads, so the rule alone refuses it (round 4's minimal pages).
INVENTED_RULE_TWINS = {
    "same_row_value": (
        "<table><tr><th>Variable</th><th>Description</th></tr>"
        "<tr><td>SSUID</td><td>Invented. 123</td></tr></table>",
        "<table><tr><th>Variable</th><th>Description</th></tr>"
        "<tr><td>SSUID</td><td>Invented.</td></tr>"
        "<tr><td>INVENTED</td><td>Invented. 123</td></tr></table>",
    ),
    "identifier_heading": (
        "<table><tr><th>SSUID</th></tr></table>",
        "<table><tr><th>Variable</th></tr><tr><td>SSUID</td></tr></table>",
    ),
    "pre_identifier": ("<pre>SSUID. x\n7</pre>", "<p>SSUID. x\n7</p>"),
    "pre_numbers": ("<pre>101 -250 40</pre>", "<p>101 -250 40</p>"),
    "row_of_numbers": (
        "<table><tr><td>-$250</td><td>($40)</td><td>40%</td></tr></table>",
        "<table><tr><td>-$250</td><td>($40)</td></tr></table>",
    ),
    # Values too short for the digit-run rules, so only the identifier
    # rules' reading of the source or of comment text can refuse them. The
    # attribute value is unquoted and the script holds no string, so the
    # reading of quoted values cannot refuse the first two either.
    "attribute_source": (
        "<p title=SSUID-123>Invented.</p>",
        "<p title=SSUID>Invented.</p>",
    ),
    "script_source": (
        "<script>var invented = PNUM + 101;</script>",
        "<script>var invented = PNUM;</script>",
    ),
    "comment_text": (
        "<!-- SSUID <b>invented</b> 123 -->",
        "<!-- SSUID <b>invented</b> -->",
    ),
    # Round 5: a twin for every other rule, and for each limit on what the
    # identifier rules read in the source.
    "digit_below": (
        "<table><tr><td>Invented</td><td>Table</td></tr>"
        "<tr><td>PNUM</td><td>Invented</td></tr>"
        "<tr><td>7</td><td>x</td></tr></table>",
        "<table><tr><td>Invented</td><td>Table</td></tr>"
        "<tr><td>PNUM</td><td>Invented</td></tr>"
        "<tr><td>x</td><td>7</td></tr></table>",
    ),
    "adjacent_digit": ("<p>PNUM: 7</p>", "<p>PNUM: x 7</p>"),
    "nine_digits_rendered": (
        "<p>Invented 123456789</p>",
        "<p>Invented 12345678</p>",
    ),
    "ssuid_length_run": (
        '<link rel="stylesheet" href="/invented.css?v=20241015123456">',
        '<link rel="stylesheet" href="/invented.css?v=2024101512345">',
    ),
    "source_window": (
        '<img alt="Invented case PNUM is 101">',
        '<img alt="Invented case PNUM is">',
    ),
    "source_adjacency": (
        '<p data-pnum="7">Invented</p>',
        '<p data-pnum="x">Invented</p>',
    ),
    "source_window_stops_at_tags": (
        "<script>SSUID x 101</script>",
        "<script>SSUID x</script><b>101</b>",
    ),
    "source_window_stays_in_one_value": (
        '<img alt="PNUM x 105">',
        '<img alt="PNUM x" data-position="105">',
    ),
    "link_targets_removed": (
        '<a title="ssuid-2024-x">Invented</a>',
        '<a href="/ssuid-2024-x.html">Invented</a>',
    ),
    # Round 6: in the text an angle bracket is a decoded entity, not a tag,
    # so the window crosses it; the source reading stops there.
    "text_window_crosses_decoded_brackets": (
        "<p>SSUID &lt;x&gt; 101</p>",
        "<p>SSUID &lt;x&gt; 10</p>",
    ),
    # Round 6: each mark that stops the source window, alone; each form of
    # link target the source reading removes; adjacency read in the text
    # alone; and both heading-cell rules.
    "source_window_stops_at_equals": (
        "<img alt=SSUID width 640>",
        "<img alt=SSUID width=640>",
    ),
    "source_window_stops_at_single_quote": (
        "<script>f('SSUID x 640')</script>",
        "<script>f('SSUID', '640')</script>",
    ),
    "source_window_stops_at_double_quote": (
        '<script>f("SSUID x 640")</script>',
        '<script>f("SSUID", "640")</script>',
    ),
    "unquoted_link_targets_removed": (
        "<a title=ssuid-2024-x>Invented</a>",
        "<a href=/ssuid-2024-x.html>Invented</a>",
    ),
    "src_values_removed": (
        '<img title="ssuid-2024-x">',
        '<img src="/ssuid-2024-x.png">',
    ),
    "text_adjacency": ("<p>PNUM<b>:</b> 7</p>", "<p>PNUM<b>:</b> x 7</p>"),
    "heading_names_identifier_above_digits": (
        "<table><tr><th>Person number (PNUM)</th>"
        "<th>Invented monthly earnings amount in dollars</th></tr>"
        "<tr><td>101</td><td>-25</td></tr></table>",
        "<table><tr><th>Person number (PNUM)</th>"
        "<th>Invented monthly earnings amount in dollars</th></tr>"
        "<tr><td>x</td><td>-25</td></tr></table>",
    ),
    "heading_names_identifier_beside_value": (
        "<table><tr><th>Person number (PNUM)</th>"
        "<td>Invented note about the invented value for this case</td>"
        "<td>101</td></tr></table>",
        "<table><tr><th>Person number (PNUM)</th>"
        "<td>Invented note about the invented value for this case</td>"
        "<td>2022</td></tr></table>",
    ),
    # Round 7: script contents read as they stand, with no quoted string to
    # read alone; link targets removed from a script's opening tag; each
    # quoted value and script string read alone, joined by periods and
    # without href and src values; and the same-row rule beside a cell that
    # names an identifier too.
    "script_contents_read_as_they_stand": (
        "<script>for(i=0;i<n;i++){img.src=PNUM+101}</script>",
        "<script>for(i=0;i<n;i++){img.src=PNUM+x}</script>",
    ),
    "script_opening_tag_link_target_removed": (
        '<script title="ssuid-2024-x"></script>',
        '<script src="/ssuid-2024-x.js"></script>',
    ),
    "quoted_value_read_alone": (
        '<img alt="PNUM (person\'s number) 101">',
        '<img alt="PNUM (person\'s number)">',
    ),
    "quoted_values_joined_by_periods": (
        '<img alt="PNUM (person\'s number) 101">',
        '<img alt="PNUM (person\'s number)" title="101">',
    ),
    "link_target_values_not_read_alone": (
        '<img alt="PNUM (person\'s number) 101">',
        '<img src="PNUM (person\'s number) 101">',
    ),
    "script_string_read_alone": (
        '<script>s = "<b>PNUM</b> 101";</script>',
        '<script>s = "<b>PNUM</b>" + 101;</script>',
    ),
    "same_row_value_beside_identifier_cell": (
        "<table><tr><th>Person number (PNUM)</th><td>SSUID of the invented "
        "case, described here at some length 101</td></tr></table>",
        "<table><tr><th>Person number (PNUM)</th><td>SSUID of the invented "
        "case, described here at some length 10</td></tr></table>",
    ),
    # Round 8: the browser scan of the source, which reads a "<script"
    # inside a quoted value as text; the text as a browser reads it, where
    # a "<" before a space opens no tag and title contents are text; and
    # template literals and style strings, each read alone.
    "browser_scan_of_the_source": (
        '<a href="<script src="PNUM=101">',
        '<a href="<script" src="PNUM=101">',
    ),
    "browser_text_lt_opens_no_tag": (
        "<p>PNUM < 101</p>",
        "<p>PNUM <b 101</p>",
    ),
    "browser_text_title_contents": (
        "<title>PNUM <i 101</title>",
        "<p>PNUM <i 101</p>",
    ),
    "template_literal_read_alone": (
        "<script>s = `<b>PNUM</b> 101`;</script>",
        "<script>s = `<b>PNUM</b>` + 101;</script>",
    ),
    "style_string_read_alone": (
        '<style>a::after{content:"PNUM (person\'s number) 101"}</style>',
        '<style>a::after{content:"PNUM (person\'s number)" 101}</style>',
    ),
}


@pytest.mark.parametrize("kind", sorted(INVENTED_RECORD_PAGES))
def test_invented_record_pages_trigger_capture_guard(kind):
    record_bearing_note = _module("capture_user_notes.py").record_bearing_note
    assert record_bearing_note(INVENTED_RECORD_PAGES[kind])


@pytest.mark.parametrize("kind", sorted(INVENTED_DEFINITION_PAGES))
def test_invented_definition_pages_are_metadata(kind):
    record_bearing_note = _module("capture_user_notes.py").record_bearing_note
    assert not record_bearing_note(INVENTED_DEFINITION_PAGES[kind])


@pytest.mark.parametrize("rule", sorted(INVENTED_RULE_TWINS))
def test_each_guard_rule_alone_refuses_its_page(rule):
    record_bearing_note = _module("capture_user_notes.py").record_bearing_note
    refused, twin = INVENTED_RULE_TWINS[rule]
    assert record_bearing_note(refused)
    assert not record_bearing_note(twin)


@pytest.mark.parametrize(("width", "refused"), [(40, True), (41, False)])
def test_identifier_value_window_is_forty_characters(width, refused):
    # Letters between, so only the 40-character rule can apply.
    between = " " + "a" * (width - 2) + " "
    body = f"<p>SSUID{between}123</p>"
    record_bearing_note = _module("capture_user_notes.py").record_bearing_note
    assert record_bearing_note(body) == refused


# Invented pages of 200 to 600 kB in forms that a quadratic pattern reads
# for minutes: a long word in a tag, escaped quotes after an unpaired quote
# in a script, tags and comments that never close, script start tags with
# no end tag, and table rows and cells that name an identifier.
INVENTED_LONG_PAGES = {
    "long_word_in_tag": "<p " + "a" * 200_000 + ">x</p>",
    "escaped_quotes_in_script": (
        '<script>s = "' + '\\"' * 100_000 + "</script>"
    ),
    "unclosed_tags": "<a" * 200_000,
    "script_start_tags": "<script>" * 50_000,
    "unclosed_comments": "<!--" * 100_000,
    "identifier_rows": (
        "<table><tr><td>x</td></tr>" + "<tr><td>PNUM</td></tr>" * 27_000
    ),
    "identifier_cells_in_row": (
        "<table><tr><td>x</td></tr><tr>" + "<td>PNUM</td>" * 30_000
    ),
}
LINEAR_TIME_CHILD = """
import importlib.util, resource, sys, time
resource.setrlimit(resource.RLIMIT_CPU, (6, 7))
spec = importlib.util.spec_from_file_location("invented_guard", sys.argv[1])
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
page = sys.stdin.read()
start = time.process_time()
guard.record_bearing_note(page)
print(time.process_time() - start)
"""


@pytest.mark.parametrize("kind", sorted(INVENTED_LONG_PAGES))
def test_guard_reads_long_pages_in_linear_time(kind):
    # The guard read each page in under a second of CPU time, and the
    # quadratic patterns it replaced, by their growth over a tenth of each
    # page, would take two to five minutes on the same host. The guard runs
    # in a child process that the operating system stops after 6 s of CPU
    # time, so a slow pattern fails here instead of stalling the run; CPU
    # time, unlike wall time, grows little with host load.
    child = subprocess.run(
        [
            sys.executable,
            "-c",
            LINEAR_TIME_CHILD,
            str(EVIDENCE / "capture_user_notes.py"),
        ],
        input=INVENTED_LONG_PAGES[kind],
        capture_output=True,
        text=True,
        timeout=900,
    )
    if child.returncode == -signal.SIGXCPU:
        pytest.fail(f"The guard read the invented {kind} page for 6 s")
    assert child.returncode == 0, child.stderr
    assert float(child.stdout) < 5


LINEAR_TOKENS = (
    "<",
    ">",
    "<a ",
    "</",
    "<!",
    "<!--",
    "-->",
    "<script>",
    "<SCRIPT ",
    "<\u017fcript>",
    "<SCR\u0130PT>",
    "</script>",
    "</script >",
    "</scr\u0131pt>",
    "<style>",
    "</style>",
    "<title>",
    "</title>",
    "<noscript>",
    "</noscript>",
    "<table>",
    "<tr>",
    "<td>",
    "</td>",
    "<pre>",
    '"',
    "'",
    "`",
    "\\",
    "\\\\",
    "=",
    " ",
    "\n",
    "x",
)


@given(tokens=st.lists(st.sampled_from(LINEAR_TOKENS), max_size=30))
@example(tokens=["<\u017fcript>", "x", "</script>"])
@example(tokens=["<SCR\u0130PT>", "x", "</script>"])
@settings(max_examples=300, deadline=None)
def test_linear_readings_match_their_patterns(tokens):
    # Each helper that keeps a reading linear gives what the plain pattern
    # gives, on invented text. The examples spell "script" with a long s
    # and with a dotted capital I, which "(?i)" reads as an s and an i.
    text = "".join(tokens)
    capture = _module("capture_user_notes.py")
    for pattern in (
        capture.ELEMENT,
        capture.BROWSER_SOURCE,
        capture.BROWSER_TEXT,
        capture.SCRIPT,
        capture.STYLE,
        capture.TABLE,
        capture.PRE,
        capture.ROW,
        capture.CELL,
        capture.TAGS,
    ):
        assert [
            match.span() for match in capture._finditer(pattern, text)
        ] == [match.span() for match in pattern.finditer(text)]
    assert capture._without_closed_scripts(text) == (
        capture.CLOSED_SCRIPT.sub(" ", text)
    )
    assert capture._without_tags(text) == re.sub(r"<[^>]+>", " ", text)
    for pattern, end_tag in (
        (r"(?is)<noscript\b.*?</noscript\s*>", r"(?i)</noscript\s*>"),
        (r"(?s)<!--.*?-->", "-->"),
    ):
        assert capture._sub_to_last(pattern, end_tag, text) == re.sub(
            pattern, " ", text
        )
    for quotes in ("\"'", "`"):
        found = re.findall(
            "(?s)" + "|".join(capture.STRING[quote] for quote in quotes), text
        )
        assert capture._strings(text, quotes) == [
            "".join(strings) if isinstance(strings, tuple) else strings
            for strings in found
        ]


@given(
    identifier=st.sampled_from(("SSUID", "PNUM", "SSUIDs", "pnum")),
    invented_words=st.text(alphabet="abcdefgh ,;:'-", max_size=38),
    invented_digits=st.text(
        alphabet="0123456789", min_size=3, max_size=20
    ).filter(lambda digits: not re.fullmatch(r"(?:19|20)\d\d", digits)),
    comment=st.booleans(),
)
@settings(deadline=None)
def test_identifier_and_value_within_a_sentence_trigger_capture_guard(
    identifier, invented_words, invented_digits, comment
):
    sentence = f"{identifier} {invented_words} {invented_digits}"
    body = f"<!-- {sentence} -->" if comment else f"<p>{sentence}</p>"
    assert _module("capture_user_notes.py").record_bearing_note(body)


@given(
    invented_words=st.text(alphabet="abcdefgh .,", max_size=40),
    invented_digits=st.text(alphabet="0123456789", min_size=9, max_size=20),
    hidden=st.sampled_from(("", "comment", "noscript")),
)
@settings(deadline=None)
def test_long_digit_runs_trigger_capture_guard_where_rendered(
    invented_words, invented_digits, hidden
):
    # A run of nine or more digits refuses the page where a reader sees it;
    # in a comment or noscript block, with no identifier, it is tracking,
    # unless it is as long as an SSUID.
    body = {
        "": f"<p>{invented_words} {invented_digits}</p>",
        "comment": f"<p>{invented_words}</p><!-- {invented_digits} -->",
        "noscript": (
            f"<p>{invented_words}</p><noscript>{invented_digits}</noscript>"
        ),
    }[hidden]
    record_bearing_note = _module("capture_user_notes.py").record_bearing_note
    assert record_bearing_note(body) == (
        hidden == "" or len(invented_digits) >= 14
    )


@given(
    identifier=st.sampled_from(("SSUID", "PNUM", "SSUIDs", "pnum")),
    invented_words=st.text(alphabet="abcdefgh", min_size=1, max_size=30),
    year=st.integers(1900, 2099),
    place=st.sampled_from(("text", "comment", "attribute")),
)
@settings(deadline=None)
def test_years_beside_identifier_names_are_metadata(
    identifier, invented_words, year, place
):
    sentence = f"{identifier} {invented_words} {year}"
    body = {
        "text": f"<p>{sentence}</p>",
        "comment": f"<!-- {sentence} -->",
        "attribute": f'<a title="{sentence}">Invented</a>',
    }[place]
    assert not _module("capture_user_notes.py").record_bearing_note(body)


NUMERIC_TEXT = st.one_of(
    st.builds(
        "{}{}{}".format,
        st.sampled_from(("", "-", "+", "$", "-$", "$-", "\u2212", "\u2212$")),
        st.integers(0, 99_999_999).map("{:,}".format),
        st.sampled_from(("", ".5", "%")),
    ),
    st.builds(
        "({}{})".format,
        st.sampled_from(("", "$")),
        st.integers(0, 99_999_999).map("{:,}".format),
    ),
)


@given(
    numbers=st.lists(NUMERIC_TEXT, min_size=1, max_size=6),
    invented_words=st.lists(
        st.text(alphabet="abcdefgh", min_size=1, max_size=8), max_size=3
    ),
)
@settings(deadline=None)
def test_rows_of_three_numbers_trigger_capture_guard(numbers, invented_words):
    cells = "".join(f"<td>{text}</td>" for text in [*invented_words, *numbers])
    body = (
        "<table><tr><th>Invented</th><th>Heading</th></tr>"
        f"<tr>{cells}</tr></table>"
    )
    record_bearing_note = _module("capture_user_notes.py").record_bearing_note
    assert record_bearing_note(body) == (len(numbers) >= 3)


@given(
    numbers=st.lists(NUMERIC_TEXT, min_size=1, max_size=6),
    invented_words=st.lists(
        st.text(alphabet="abcdefgh", min_size=1, max_size=8), max_size=3
    ),
)
@settings(deadline=None)
def test_preformatted_lines_of_three_numbers_trigger_capture_guard(
    numbers, invented_words
):
    line = " ".join([*invented_words, *numbers])
    body = f"<pre>Invented heading\n{line}\n</pre>"
    record_bearing_note = _module("capture_user_notes.py").record_bearing_note
    assert record_bearing_note(body) == (len(numbers) >= 3)


@given(invented_text=st.text(alphabet="abcdefgh", max_size=30))
@settings(deadline=None)
def test_invented_exclusion_inventory_never_retains_body_or_pin(
    invented_text,
):
    entry = {
        "url": "https://example.invalid/INVENTED_NOTE",
        "title": "Invented note",
        "release": 2025,
        "variables": ["INVENTED_VARIABLE"],
        "kind": "note",
        "body": invented_text,
        "extract": invented_text,
        "sha256": invented_text,
        "bytes": len(invented_text),
        "retrieved_utc": invented_text,
    }
    excluded = _module("capture_user_notes.py").excluded_note_metadata(entry)
    assert set(excluded) == {
        "url",
        "title",
        "release",
        "variables",
        "kind",
        "stored_as",
        "status",
        "exclusion_reason",
    }
    assert excluded["stored_as"] is None
    assert excluded["status"] == "excluded_record_bearing"


def test_user_notes_attach_by_release_and_variable():
    manifest = _json("user_notes_manifest.json")
    for year in YEARS:
        for concept, spec in registry.income_variables(year).items():
            expected = {
                (row["title"], row["url"])
                for row in manifest
                if row["kind"] == "note"
                and (
                    row["stored_as"]
                    or row.get("status") == "excluded_record_bearing"
                )
                and row["release"] == year
                and spec.name in row["variables"]
                and spec.name
                not in ("SSUID", "PNUM", "MONTHCODE", "SPANEL", "SWAVE")
            }
            assert set(registry.user_notes(year, concept)) == expected


def test_corrections_match_rulings():
    rule = _json("source_rulings.json")["corrected_releases"][
        "social_security_amount"
    ]
    for year in YEARS:
        expected = rule["corrected_on"] if year in rule["releases"] else None
        assert registry.corrected_on(year, "social_security_amount") == (
            expected
        )
        assert (
            registry.income_variables(year)["social_security_amount"].name
            == rule["variable"]
        )


# Replicate weights.


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
        assert spec.storage_type == schema[raw_name]["dtype"]
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


# Hashes, manifests and regeneration.


def test_embedded_evidence_hashes_and_derived_provenance():
    assert registry.EVIDENCE_SHA256
    for filename, digest in registry.EVIDENCE_SHA256.items():
        assert (
            hashlib.sha256((EVIDENCE / filename).read_bytes()).hexdigest()
            == digest
        )
    for derived in _json("derived_manifest.json"):
        payload = (EVIDENCE / derived["path"]).read_bytes()
        assert len(payload) == derived["bytes"]
        assert hashlib.sha256(payload).hexdigest() == derived["sha256"]
    for year in YEARS:
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
        assert "validate" not in capture["url"]
        assert not re.search(r"/(pu|rw)\d{4}_(csv|dta|sas)", capture["url"])
        retrieved = datetime.fromisoformat(capture["retrieved_utc"])
        assert retrieved.utcoffset() == timedelta(0)
        filename = Path(capture["path"])
        assert filename.parent == Path(".")
        assert filename.suffix in {".json", ".txt", ".html", ".pdf", ".xlsx"}
        payload = (EVIDENCE / filename).read_bytes()
        assert len(payload) == capture["bytes"]
        assert hashlib.sha256(payload).hexdigest() == capture["sha256"]
        if capture["url"].endswith(".py"):
            # Census's input examples, stored byte for byte as .py.txt so
            # repository linters never rewrite them.
            assert filename.name.endswith("_python_input_example.py.txt")
        if filename.suffix == ".pdf":
            assert re.search(
                r"dictionary|release_notes|metadata", filename.name
            )


def test_regeneration_matches_embedded_tables_without_writing():
    tables = _module("build_registry.py").build_tables()
    assert tables["concepts"] == registry._CONCEPTS
    assert tables["definitions"] == registry._DEFINITIONS
    assert tables["releases"] == registry._RELEASES
    assert tables["replicates"] == registry._REPLICATES
    assert tables["notes"] == registry._USER_NOTES
    assert tables["note_table"] == registry._NOTE_TABLE
    assert tables["corrections"] == registry._CORRECTED_ON
    assert tables["hashes"] == registry.EVIDENCE_SHA256
    assert tables["refused"] == _json("refused_concepts.json")
    assert tables["label_checks"] == _json("label_checks.json")
    assert tables["domain_checks"] == _json("domain_checks.json")
    assert tables["changes"] == _json("release_changes.json")


# The dictionary parser, on invented pages.


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


@given(
    lower=st.integers(min_value=1, max_value=10**9),
    gap=st.integers(min_value=1, max_value=10**9),
    inline=st.booleans(),
)
@settings(max_examples=50, deadline=None)
def test_invented_inverted_range_never_verifies(lower, gap, inline):
    """A misprinted range (minimum above maximum) is never admitted."""
    upper = lower + gap
    body = (
        f"{upper}:{lower}. Invented misprint"
        if inline
        else f" Minimum:     {upper}\n Maximum:     {lower}"
    )
    page = (
        "Name: INVENTED_ID\nDescription: Invented identifier, not survey "
        f"data.\nPossible Values\n{body}\n1\n"
    )
    _, fields, values, _ = _module("parse_dictionary_metadata.py").parse_page(
        page, 2021
    )
    assert fields["Unparsed values"]
    assert not values.get("range")


def test_inverted_2021_interview_address_range_is_refused():
    entry = _dictionary(2021)["EHRESIDENCID"]
    assert not entry["verified"]
    assert entry["unparsed_value_lines"] == [
        "Minimum 100001 exceeds Maximum 40999"
    ]
    assert "interview_address_id" not in registry.income_variables(2021)
    assert "interview_address_id" in registry.income_variables(2022)


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
