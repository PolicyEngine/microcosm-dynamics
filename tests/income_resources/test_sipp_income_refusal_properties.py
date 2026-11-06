"""Registry properties using INVENTED metadata and values only.

The generator must refuse uncovered or unsettled source conflicts, retain
ownership and period unchanged, and hash the exact evidence bytes. Domain
rulings must match both sources, including their API missing codes. The
committed data/external check verifies coverage, without reading any note.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from decimal import Decimal
from functools import cache
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from populace_dynamics.data import sipp_income_registry as registry

EVIDENCE = (
    Path(__file__).resolve().parents[2] / "data" / "external" / "sipp_income"
)
INVENTED_SETTINGS = settings(
    max_examples=25,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
INVENTED_OWNERSHIP = (
    "person",
    "joint_spouse_person_share",
    "joint_other_person_share",
    "household",
    "business_interest",
    "sample_unit",
)
INVENTED_PERIODS = (
    "monthly",
    "reference_period",
    "year_end",
    "interview",
    "design",
)


@cache
def _generator():
    spec = importlib.util.spec_from_file_location(
        "invented_refusal_generator", EVIDENCE / "build_registry.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json(directory, name, value):
    (directory / name).write_text(json.dumps(value))


def _invented_evidence(directory, *, lower, width, gap=0):
    """Write a complete one-release metadata set with invented domains."""
    name = "INVENTED_BALANCE"
    label = "Invented balance, never survey data."
    upper = lower + width + gap
    primary = {
        "label": label,
        "predicateType": "int",
        "values": {
            "item": {"-999": "NA-Missing"},
            "range": [{"min": str(lower), "max": str(upper)}],
        },
    }
    dictionary = {
        "dictionary_label": label,
        "predicateType": "int",
        "verified": True,
        "universe": "Invented eligible people",
        "dictionary_pdf_pages": [1],
        "values": {
            "item": {},
            "range": [{"min": str(lower + gap), "max": str(upper)}],
        },
    }
    selection = {
        "core_concepts": [],
        "concepts": {
            "invented_balance": {
                "raw_name": name,
                "ownership_level": "person",
                "period": "year_end",
            }
        },
        "release_crosswalk": {"2022": {"invented_balance": name}},
    }
    rulings = {
        "label_conflicts": {},
        "suppression_conflicts": {},
        "universe_anomalies": [],
        "release_family_conflicts": [],
        "code_conflicts": {},
        "corrected_releases": {},
        "domain_conflicts": {},
    }
    if gap:
        rulings["domain_conflicts"]["invented-intersection"] = {
            "name": "Invented conservative intersection",
            "reason": "Invented sources admit only their common interval.",
            "resolution": "intersection",
            "missing_code_policy": "preserve_api_missing_codes",
            "api": [[str(lower), str(upper)]],
            "dictionary": [[str(lower + gap), str(upper)]],
            "admitted": [[str(lower + gap), str(upper)]],
            "members": [
                {
                    "release": 2022,
                    "variable": name,
                    "api_missing_codes": ["-999"],
                    "dictionary_pdf_pages": [1],
                    "evidence": [
                        f"2022_variables.json#{name}",
                        f"2022_dictionary_variables.json#{name}",
                        "2022_dictionary.pdf#page=1",
                    ],
                }
            ],
        }
    _write_json(directory, "concept_selection.json", selection)
    _write_json(directory, "source_rulings.json", rulings)
    _write_json(directory, "user_notes_manifest.json", [])
    _write_json(
        directory, "2022_variables.json", {"variables": {name: primary}}
    )
    _write_json(
        directory,
        "2022_dictionary_variables.json",
        {"variables": {name: dictionary}},
    )
    _write_json(
        directory,
        "pu2022_schema.json",
        [{"name": name, "label": label, "dtype": "integer"}],
    )
    for filename in (
        "2022_dictionary.pdf",
        "2022_dictionary.txt",
        "2022_python_input_example.py.txt",
    ):
        (directory / filename).write_bytes(b"INVENTED METADATA ONLY")
    # The production replicate builder verifies each key and every weight.
    keys = (
        ("SSUID", "string", "00000000000000:99999999999999"),
        ("PNUM", "integer", "101:499"),
        ("MONTHCODE", "integer", "1:12"),
    )
    _write_json(
        directory,
        "rw2022_schema.json",
        [
            {"name": key, "dtype": dtype, "label": "Invented key"}
            for key, dtype, _ in keys
        ]
        + [
            {"name": f"REPWGT{n}", "dtype": "float", "label": ""}
            for n in range(241)
        ],
    )
    (directory / "rw2022_dictionary.txt").write_text(
        "INVENTED METADATA ONLY\n"
        + "\n".join(f"D {key}\n{domain}" for key, _, domain in keys)
        + "\nREPWGT1 REPWGT240 0.000000:9999999.999999\n"
    )
    return selection, rulings


def _use_invented_generator(patch, directory):
    generator = _generator()
    patch.setattr(generator, "BASE", directory)
    patch.setattr(generator, "YEARS", (2022,))
    patch.setattr(generator, "API_YEARS", (2022,))
    return generator


@INVENTED_SETTINGS
@given(
    lower=st.integers(min_value=0, max_value=10**6),
    width=st.integers(min_value=0, max_value=1000),
    gap=st.integers(min_value=1, max_value=1000),
    conflict=st.sampled_from(("label", "domain")),
    open_ruling=st.booleans(),
)
def test_invented_source_conflicts_refuse_without_settled_rulings(
    tmp_path, monkeypatch, lower, width, gap, conflict, open_ruling
):
    _, rulings = _invented_evidence(
        tmp_path,
        lower=lower,
        width=width,
        gap=gap if conflict == "domain" else 0,
    )
    if conflict == "label":
        filename = "2022_dictionary_variables.json"
        dictionary = json.loads((tmp_path / filename).read_text())
        dictionary["variables"]["INVENTED_BALANCE"][
            "dictionary_label"
        ] = "Invented conflicting definition"
        _write_json(tmp_path, filename, dictionary)
        if open_ruling:
            rulings["label_conflicts"]["2022/INVENTED_BALANCE"] = {
                "resolution": None
            }
    elif open_ruling:
        rulings["domain_conflicts"]["invented-intersection"][
            "resolution"
        ] = None
    else:
        rulings["domain_conflicts"] = {}
    _write_json(tmp_path, "source_rulings.json", rulings)
    with monkeypatch.context() as patch:
        generator = _use_invented_generator(patch, tmp_path)
        if open_ruling:
            tables = generator.build_tables()
            assert "invented_balance" not in tables["releases"][2022]
            assert tables["refused"]["2022"]["invented_balance"].startswith(
                "open conflict:"
            )
        else:
            with pytest.raises(AssertionError, match=f"unruled {conflict}"):
                generator.build_tables()


# Every damage runs, each against its own generated rulings.
@pytest.mark.parametrize(
    "damage",
    (
        "interval",
        "missing_code",
        "source",
        "location",
        "pdf_citation",
        "other_release_pdf",
        "pageless_pdf",
        "pageless_other_release_pdf",
        "release_notes_pdf",
        "coverage",
    ),
)
@INVENTED_SETTINGS
@given(
    lower=st.integers(min_value=0, max_value=10**6),
    width=st.integers(min_value=0, max_value=1000),
    gap=st.integers(min_value=1, max_value=1000),
)
def test_invented_domain_ruling_cannot_cover_changed_evidence(
    tmp_path, monkeypatch, lower, width, gap, damage
):
    _, rulings = _invented_evidence(
        tmp_path, lower=lower, width=width, gap=gap
    )
    rule = rulings["domain_conflicts"]["invented-intersection"]
    member = rule["members"][0]
    if damage == "interval":
        rule["admitted"][0][0] = str(lower + gap + 1)
    elif damage == "missing_code":
        member["api_missing_codes"] = []
    elif damage == "source":
        member["evidence"] = member["evidence"][:1]
    elif damage == "location":
        member["dictionary_pdf_pages"] = [2]
    elif damage == "pdf_citation":
        member["evidence"][2] = "2022_dictionary.pdf#page=2"
    elif damage == "other_release_pdf":
        member["evidence"][2] = "2021_dictionary.pdf#page=1"
    elif damage == "pageless_pdf":
        member["evidence"].append("2022_dictionary.pdf")
    elif damage == "pageless_other_release_pdf":
        member["evidence"].append("2021_dictionary.pdf")
    elif damage == "release_notes_pdf":
        member["evidence"].append("2022_release_notes.PDF#page=1")
    else:
        member["variable"] = "INVENTED_DIFFERENT_VARIABLE"
    _write_json(tmp_path, "source_rulings.json", rulings)
    # Each damage stops generation at its own check.
    message = {
        "interval": "stale domain ruling",
        "missing_code": "stale API missing codes",
        "source": "uncited domain ruling",
        "location": "stale dictionary location",
        "coverage": "unruled domain conflict",
    }.get(damage, "stale PDF citation")
    with monkeypatch.context() as patch:
        generator = _use_invented_generator(patch, tmp_path)
        with pytest.raises(AssertionError, match=message):
            generator.build_tables()


@INVENTED_SETTINGS
@given(
    lower=st.integers(min_value=0, max_value=10**6),
    width=st.integers(min_value=0, max_value=1000),
    gap=st.integers(min_value=1, max_value=1000),
    probe=st.integers(min_value=-2000, max_value=1002000),
)
def test_invented_ruled_domains_keep_intersection_and_api_missing_code(
    tmp_path, monkeypatch, lower, width, gap, probe
):
    _invented_evidence(tmp_path, lower=lower, width=width, gap=gap)
    with monkeypatch.context() as patch:
        tables = _use_invented_generator(patch, tmp_path).build_tables()
        patch.setattr(registry, "_CONCEPTS", tables["concepts"])
        patch.setattr(registry, "_DEFINITIONS", tables["definitions"])
        patch.setattr(registry, "_RELEASES", tables["releases"])
        spec = registry.income_variables(2022)["invented_balance"]
        for value in (probe, lower, lower + gap, lower + width + gap, -999):
            assert registry.domain_contains(spec, Decimal(value)) == (
                value == -999 or lower + gap <= value <= lower + width + gap
            )


@INVENTED_SETTINGS
@given(
    ownership=st.sampled_from(INVENTED_OWNERSHIP),
    period=st.sampled_from(INVENTED_PERIODS),
    lower=st.integers(min_value=0, max_value=10**6),
)
def test_invented_ownership_and_period_survive_generation(
    tmp_path, monkeypatch, ownership, period, lower
):
    selection, _ = _invented_evidence(tmp_path, lower=lower, width=100)
    selection["concepts"]["invented_balance"].update(
        ownership_level=ownership, period=period
    )
    _write_json(tmp_path, "concept_selection.json", selection)
    with monkeypatch.context() as patch:
        tables = _use_invented_generator(patch, tmp_path).build_tables()
        patch.setattr(registry, "_CONCEPTS", tables["concepts"])
        patch.setattr(registry, "_DEFINITIONS", tables["definitions"])
        patch.setattr(registry, "_RELEASES", tables["releases"])
        spec = registry.income_variables(2022)["invented_balance"]
        assert (spec.ownership, spec.period) == (ownership, period)


@INVENTED_SETTINGS
@given(payload=st.binary(min_size=0, max_size=300), bit=st.integers(0, 7))
def test_invented_evidence_pins_hash_exact_bytes(
    tmp_path, monkeypatch, payload, bit
):
    _invented_evidence(tmp_path, lower=0, width=100)
    filename = "2022_dictionary.pdf"
    original = b"INVENTED DOCUMENTATION ONLY\n" + payload
    changed = bytes([original[0] ^ (1 << bit)]) + original[1:]
    with monkeypatch.context() as patch:
        generator = _use_invented_generator(patch, tmp_path)
        (tmp_path / filename).write_bytes(original)
        before = generator.build_tables()["hashes"]
        (tmp_path / filename).write_bytes(changed)
        after = generator.build_tables()["hashes"]
    assert before[filename] == hashlib.sha256(original).hexdigest()
    assert after[filename] == hashlib.sha256(changed).hexdigest()
    assert before[filename] != after[filename]
    assert {
        key: value for key, value in before.items() if key != filename
    } == {key: value for key, value in after.items() if key != filename}


def test_named_domain_rulings_cover_every_recorded_difference():
    rulings = json.loads((EVIDENCE / "source_rulings.json").read_text())[
        "domain_conflicts"
    ]
    rows = json.loads((EVIDENCE / "domain_checks.json").read_text())
    covered = {}
    for identifier, rule in rulings.items():
        assert rule["name"] and rule["reason"]
        for member in rule["members"]:
            key = (member["release"], member["variable"])
            assert key not in covered
            covered[key] = identifier
    assert set(covered) == {(row["release"], row["variable"]) for row in rows}
    for row in rows:
        key = (row["release"], row["variable"])
        identifier = covered[key]
        rule = rulings[identifier]
        assert row["ruling"] == (
            "source_rulings.json#domain_conflicts/" + identifier
        )
        assert {
            field: row[field] for field in ("api", "dictionary", "admitted")
        } == {
            field: rule[field] for field in ("api", "dictionary", "admitted")
        }
