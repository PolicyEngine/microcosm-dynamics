"""Documentary checks only. No survey records or outcome calculations."""

import copy
import hashlib
import json
from pathlib import Path

import pytest

from populace_dynamics.data import u2_source_registry as registry

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("name", registry.REGISTRY_NAMES)
def test_each_registry_has_valid_cited_schema(name):
    document = registry.load_registry(name)
    assert {e["wave"] for e in document["entries"]} <= {
        None,
        *registry.U2_SOURCE_WAVES,
    }
    if name not in ("design",):
        assert set(registry.U2_SOURCE_WAVES) <= {
            e["wave"] for e in document["entries"]
        }


@pytest.mark.parametrize(
    "change, message",
    [
        (lambda d: d.update(target_id="U1"), "identity"),
        (lambda d: d.update(waves=[2005, 2007, 2009, 2011, 2013]), "waves"),
        (lambda d: d.update(entries=[]), "nonempty"),
        (
            lambda d: d["entries"].append(copy.deepcopy(d["entries"][0])),
            "duplicate",
        ),
        (lambda d: d["entries"][0].update(wave=2025), "wave"),
        (lambda d: d["entries"][0].update(status="probably"), "status"),
        (
            lambda d: d["entries"][0].update(status="TO VERIFY", question=""),
            "exact question",
        ),
        (lambda d: d["entries"][0].update(citations=[]), "citations"),
        (
            lambda d: d["entries"][0].update(citations=[{"file": "book"}]),
            "line or page",
        ),
    ],
)
def test_invalid_documentary_metadata_refuses(change, message):
    document = copy.deepcopy(registry.load_registry("individual"))
    change(document)
    with pytest.raises(registry.SourceAdjudicationError, match=message):
        registry.validate_registry(document, expected_name="individual")


@pytest.mark.parametrize("name", registry.REGISTRY_NAMES)
def test_schema_refuses_citation_only_entries_without_mapping_payload(name):
    document = registry.load_registry(name)
    document["entries"] = [
        {
            "id": "INVENTED.empty_mapping",
            "wave": 2013,
            "status": "RESOLVED",
            "citations": [{"file": "INVENTED.source", "line": 1}],
        }
    ]
    with pytest.raises(registry.SourceAdjudicationError, match="Missing"):
        registry.validate_registry(document, expected_name=name)


@pytest.mark.parametrize(
    "name,field",
    [
        ("income", "variable"),
        ("wealth", "documented_domain"),
        ("individual", "layout"),
        ("pension", "kind"),
        ("roles", "action"),
        ("support", "birth_year"),
        ("weights", "construction"),
        ("design", "valid_codes"),
    ],
)
def test_schema_requires_registry_specific_fields(name, field):
    document = registry.load_registry(name)
    del document["entries"][0][field]
    with pytest.raises(registry.SourceAdjudicationError, match=field):
        registry.validate_registry(document, expected_name=name)


@pytest.mark.parametrize(
    "name,field",
    [
        ("individual", "layout"),
        ("pension", "position"),
        ("income", None),
        ("wealth", None),
        ("weights", "layout"),
        ("design", "layout"),
    ],
)
def test_schema_requires_inclusive_layout_width(name, field):
    document = registry.load_registry(name)
    entry = document["entries"][0]
    layout = entry[field] if field else entry
    layout["width"] += 1
    with pytest.raises(registry.SourceAdjudicationError, match="layout width"):
        registry.validate_registry(document, expected_name=name)


@pytest.mark.parametrize("start", [0, -1, True, 1.5, "1"])
def test_schema_refuses_invalid_layout_start(start):
    document = registry.load_registry("individual")
    document["entries"][0]["layout"]["start"] = start
    with pytest.raises(registry.SourceAdjudicationError):
        registry.validate_registry(document, expected_name="individual")


@pytest.mark.parametrize("name", ["income", "wealth"])
def test_crosswalk_requires_variable_list_without_scalar_layout(name):
    document = registry.load_registry(name)
    entry = next(
        e
        for e in document["entries"]
        if e.get("kind") == "historical_route_crosswalk"
    )
    assert "variable" not in entry
    entry["variables"] = []
    with pytest.raises(registry.SourceAdjudicationError, match="variables"):
        registry.validate_registry(document, expected_name=name)


def test_pension_route_requires_its_own_fields_without_variable_layout():
    document = registry.load_registry("pension")
    entry = next(
        e for e in document["entries"] if e["id"] == "2013.route.current_job"
    )
    assert "variable" not in entry
    del entry["accepted_current_types"]
    with pytest.raises(
        registry.SourceAdjudicationError, match="accepted_current_types"
    ):
        registry.validate_registry(document, expected_name="pension")


def test_schema_refuses_overlapping_wealth_asset_and_debt():
    document = registry.load_registry("wealth")
    entry = next(
        e
        for e in document["entries"]
        if e.get("identity", {}).get("operation")
        == "sum_assets_minus_sum_debts"
    )
    entry["identity"]["debts"].append(entry["identity"]["assets"][0])
    with pytest.raises(registry.SourceAdjudicationError, match="Overlapping"):
        registry.validate_registry(document, expected_name="wealth")


@pytest.mark.parametrize("action", [None, False, 1, [], ""])
def test_schema_refuses_non_string_or_empty_action(action):
    document = registry.load_registry("roles")
    document["entries"][0]["action"] = action
    with pytest.raises(registry.SourceAdjudicationError, match="action"):
        registry.validate_registry(document, expected_name="roles")


@pytest.mark.parametrize(
    "dependencies",
    [
        None,
        [1],
        [""],
        ["roles"],
        ["missing:x"],
        ["roles:"],
        ["roles:x", "roles:x"],
        ["individual:2013.interview"],
    ],
)
def test_schema_refuses_malformed_dependencies(dependencies):
    document = registry.load_registry("individual")
    document["entries"][0]["blocking_dependencies"] = dependencies
    with pytest.raises(registry.SourceAdjudicationError, match="[Dd]ependenc"):
        registry.validate_registry(document, expected_name="individual")


def test_dependency_references_name_existing_entries():
    documents = {
        name: registry.load_registry(name) for name in registry.REGISTRY_NAMES
    }
    identifiers = {
        name: {entry["id"] for entry in doc["entries"]}
        for name, doc in documents.items()
    }
    for name, document in documents.items():
        for entry in document["entries"]:
            for dependency in entry.get("blocking_dependencies", []):
                target, identifier = dependency.split(":")
                assert identifier in identifiers[target]
            if "requires_resolved_route" in entry:
                assert entry["requires_resolved_route"] in identifiers[name]


@pytest.mark.parametrize("value", [None, [], "invalid"])
def test_schema_refuses_non_object_document(value):
    with pytest.raises(
        registry.SourceAdjudicationError, match="document must be an object"
    ):
        registry.validate_registry(value, expected_name="individual")


@pytest.mark.parametrize("value", [True, 0, -1, float("nan"), float("inf")])
def test_schema_refuses_invalid_support_multiplier(value):
    document = registry.load_registry("support")
    document["entries"][0]["multiplier"] = value
    with pytest.raises(registry.SourceAdjudicationError, match="multiplier"):
        registry.validate_registry(document, expected_name="support")


def test_schema_refuses_calendar_inconsistent_with_documented_birth_and_wave():
    document = registry.load_registry("support")
    document["entries"][0]["age"] += 1
    with pytest.raises(registry.SourceAdjudicationError, match="calendar"):
        registry.validate_registry(document, expected_name="support")


def test_explicit_source_refusals_cannot_be_loaded_as_resolved(monkeypatch):
    checked = 0
    for name in registry.REGISTRY_NAMES:
        document = registry.load_registry(name)
        with monkeypatch.context() as patch:
            patch.setattr(
                registry,
                "load_registry",
                lambda _name, document=document: document,
            )
            for entry in document["entries"]:
                if (
                    entry["status"] == "TO VERIFY"
                    or entry.get("blocking_dependencies")
                    or entry.get("action", "").startswith("refuse")
                ):
                    with pytest.raises(registry.SourceAdjudicationError):
                        registry.require_resolved(name, entry["id"])
                    checked += 1
    assert checked > 0
    assert (
        registry.require_resolved("roles", "2017.relationship.10")[
            "income_role"
        ]
        == "head"
    )


def test_registry_names_and_missing_entries_refuse():
    with pytest.raises(registry.SourceAdjudicationError, match="Unknown"):
        registry.load_registry("../track_u_ssi_parameters")
    with pytest.raises(registry.SourceAdjudicationError, match="Unknown"):
        registry.require_resolved("individual", "missing")


def test_relationship_labels_and_routing_blockers_are_wave_specific():
    entries = registry.load_registry("roles")["entries"]
    by_key = {(e["wave"], e["code"]): e for e in entries}
    for wave in registry.U2_SOURCE_WAVES:
        head = "Head" if wave < 2017 else "Reference Person"
        spouse = "Legal Wife" if wave == 2013 else "Legal Spouse"
        prefixes = {
            10: f"{head} in {wave}",
            20: f"{spouse} in {wave}",
            22: (
                '"Wife"--female cohabitor'
                if wave == 2013
                else (
                    "Partner--female cohabitor"
                    if wave == 2015
                    else "Partner--cohabitor"
                )
            ),
            88: f"First-year cohabitor of {head}",
            90: (
                "Legal husband of Head"
                if wave == 2013
                else f"Uncooperative legal spouse of {head}"
            ),
        }
        for code, prefix in prefixes.items():
            entry = by_key[wave, code]
            assert entry["present"]
            assert " ".join(entry["label"].lower().split()).startswith(
                " ".join(prefix.lower().split())
            )
        assert by_key[wave, 92]["present"] == (wave >= 2017)
        assert by_key[wave, 88]["administrative_birth_support"]
        assert not by_key[wave, 92]["administrative_birth_support"]
        if wave >= 2017:
            assert by_key[wave, 92]["label"].startswith(
                "Uncooperative partner of Reference Person"
            )
            assert not by_key[wave, 92]["legal_spouse_annuity"]
            assert not by_key[wave, 92]["marital_resolution"]
        if wave >= 2015:
            assert by_key[wave, 90]["status"] == "TO VERIFY"
        if wave >= 2017:
            assert by_key[wave, 92]["status"] == "TO VERIFY"
    assert by_key[2015, 20]["action"] == "refuse_male_code20"


def test_documentary_calendar_support():
    rows = [
        e
        for e in registry.load_registry("support")["entries"]
        if "birth_year" in e
    ]
    assert len(rows) == 15
    assert sum(e["primary_observation"] for e in rows) == 5
    assert {e["birth_year"] for e in rows} == set(range(1946, 1956))
    for birth in range(1946, 1956):
        assert (
            sum(e["multiplier"] for e in rows if e["birth_year"] == birth) == 1
        )
    for entry in rows:
        assert entry["wave"] == entry["income_year"] + 1
        assert entry["income_year"] == entry["birth_year"] + entry["age"]
        if entry["wave"] == 2013:
            assert (entry["birth_year"], entry["age"]) == (1946, 66)


def test_design_domains_include_refreshment_strata():
    rows = registry.load_registry("design")["entries"]
    domain = {e["variable"]: set(e["valid_codes"]) for e in rows}
    assert set(range(88, 95)) <= domain["ER31996"]
    assert domain["ER31997"] == {1, 2}
    assert 0 not in domain["ER31996"]


def test_u1_and_protected_sources_remain_byte_identical():
    pins = json.loads(
        (registry.REGISTRY_DIRECTORY / "u1_identity.json").read_text()
    )
    assert pins["base_commit"] == "d978d966270f"
    for path, expected in pins["sha256"].items():
        assert (
            hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected
        ), path


@pytest.mark.parametrize("year", [17, 23])
def test_weight_document_capture_manifests(year):
    manifest = json.loads(
        (
            ROOT
            / f"tests/data/track_u2/psid_sources/weights{year}_manifest.json"
        ).read_text()
    )
    assert len(manifest["sources"]) == 1
    for source in manifest["sources"]:
        raw = (ROOT / source["file"]).read_bytes()
        assert raw.startswith(b"%PDF")
        assert len(raw) == source["bytes"]
        assert hashlib.sha256(raw).hexdigest() == source["sha256"]
        assert source["url"].startswith("https://psidonline.isr.umich.edu/")


def test_u1_waves_and_registries_remain_pinned():
    from populace_dynamics.cohorts import age67
    from populace_dynamics.data import employer_dc, family_income

    waves = (2005, 2007, 2009, 2011, 2013)
    assert age67.WAVES == family_income.INCOME_WAVES == waves
    assert employer_dc.EMPLOYER_DC_WAVES == waves
    assert employer_dc._NEW_CODES_WAVES == frozenset({2011, 2013})
    assert tuple(family_income._INCOME_VARS) == waves
    assert tuple(age67.ANCHOR_LAYOUTS) == waves
    assert family_income.WEALTH_WAVES == (2009, 2011, 2013)
    assert family_income.WEALTH_SUPPLEMENT_WAVES == (2005, 2007)
