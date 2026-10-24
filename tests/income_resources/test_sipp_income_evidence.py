"""Check the registry against committed data/external SIPP metadata.

These tests read only captured Census documentation: the variable API,
dictionaries, storage schemas, replicate dictionaries, release notes,
crosswalks and user notes. No survey record exists in the repository.
The INVENTED_* pages are made-up dictionary fragments. Each check derives
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
import unicodedata
from datetime import datetime, timedelta
from decimal import Decimal
from functools import cache
from pathlib import Path
from urllib.parse import urlparse

import openpyxl
import pytest
from hypothesis import given, settings
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
    assert {row["http_status"] for row in manifest} == {200}
    for row in manifest:
        assert urlparse(row["url"]).hostname == "www.census.gov"
        assert "/sipp/tech-documentation/user-notes" in row["url"]
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


def test_user_notes_attach_by_release_and_variable():
    manifest = _json("user_notes_manifest.json")
    for year in YEARS:
        for concept, spec in registry.income_variables(year).items():
            expected = {
                (row["title"], row["url"])
                for row in manifest
                if row["kind"] == "note"
                and row["stored_as"]
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
