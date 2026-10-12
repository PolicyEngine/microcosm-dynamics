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
        for code in (90, 92):
            if wave < 2015 or (code == 92 and wave < 2017):
                continue
            entry = by_key[wave, code]
            assert entry["status"] == "RESOLVED"
            if wave <= 2017:
                # Independent adjudication D: OFUM collection documented.
                assert entry["adjudication"]["disposition"] == "D"
                assert entry["action"] == "documented_rule"
                assert entry["income_role"] == "ofum"
                assert not entry["spouse_slot"]
            else:
                # Independent adjudication F (OFUM assignment refused),
                # replaced by Max's d1090 ruling (section 16c): the family
                # unit is excluded and no income role is assigned.
                assert entry["adjudication"]["disposition"] == "F"
                assert entry["action"] == "exclude_family_unit_per_d1090"
                assert entry["income_role"] == "excluded"
                assert entry["family_unit_exclusion"] == {
                    "disposition": (
                        "uncooperative spouse or partner in family unit"
                    )
                }
                assert entry["ruling"]["decision"] == "d1090"
    code20 = by_key[2015, 20]
    assert code20["action"] == "documented_rule_with_family_unit_exclusion"
    assert code20["family_unit_exclusion"] == {
        "disposition": "male code 20 in 2015 family unit",
        "condition": {"sex": 1},
    }
    assert code20["adjudication"]["disposition"] == "F"
    assert code20["ruling"]["decision"] == "d1090"


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
    # Milestone 1b moved the U2 specification, which Part C revises, to its
    # own revision pin (see test_adjudication_applied.py); the U1 files stay.
    assert len(pins["sha256"]) == 50
    assert (
        "docs/design/boomers2004_uniform_cut_comparison.md" in pins["sha256"]
    )
    for path, expected in pins["sha256"].items():
        observed = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        if path == "gates.yaml" and observed != expected:
            # A ratified flip outside U2 (first: the gate_epuf_fill lock,
            # decision d927) may move the contract; it must then be the
            # ratified one, recorded in runs/legacy_manifest_v1.json by
            # scripts/build_legacy_manifest.py --transition.
            entries = json.loads(
                (ROOT / "runs" / "legacy_manifest_v1.json").read_text()
            )["entries"]
            (entry,) = [e for e in entries if e["path"] == "gates.yaml"]
            assert observed == entry["sha256"], path
            continue
        assert observed == expected, path


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


# ---------------------------------------------------------------------------
# Max's d1090 ruling (section 16c): each ratified exclusion, held to its
# exact scope (review of 07916bb, finding 1)
# ---------------------------------------------------------------------------
def _entry(document, key):
    return next(e for e in document["entries"] if e["id"] == key)


def _move(document, source, target):
    """Move the exclusion fields of ``source`` onto ``target``."""
    moved = _entry(document, source)
    entry = _entry(document, target)
    for field in ("family_unit_exclusion", "income_role", "action", "ruling"):
        entry[field] = copy.deepcopy(moved[field])
    entry.pop("adjudication", None)


def _swap(document, field, first, second):
    """Swap one numeric field of two entries, leaving their ids alone."""
    a, b = _entry(document, first), _entry(document, second)
    a[field], b[field] = b[field], a[field]


def _absent(document, key):
    _entry(document, key).update(present=False, label=None)


D1090_SCOPE_MUTATIONS = {
    # Review of db735e5, finding 2: the rules are keyed on an entry's wave
    # and code, so swapping those under unchanged ids, or marking the code
    # absent, must not move or remove an exclusion.
    "b1_code_swapped_with_22": lambda d: _swap(
        d, "code", "2015.relationship.20", "2015.relationship.22"
    ),
    "b1_wave_swapped_with_2017": lambda d: _swap(
        d, "wave", "2015.relationship.20", "2017.relationship.20"
    ),
    "b2_code_swapped_with_10": lambda d: _swap(
        d, "code", "2019.relationship.90", "2019.relationship.10"
    ),
    "b2_wave_swapped_with_2017": lambda d: _swap(
        d, "wave", "2019.relationship.92", "2017.relationship.92"
    ),
    "b1_marked_absent": lambda d: _absent(d, "2015.relationship.20"),
    "b2_marked_absent": lambda d: _absent(d, "2021.relationship.90"),
    "unruled_codes_swapped": lambda d: _swap(
        d, "code", "2013.relationship.10", "2013.relationship.22"
    ),
    "b1_on_female_spouses": lambda d: _entry(d, "2015.relationship.20")[
        "family_unit_exclusion"
    ].update(condition={"sex": 2}),
    "b1_unconditional": lambda d: _entry(d, "2015.relationship.20")[
        "family_unit_exclusion"
    ].pop("condition"),
    "b1_condition_as_bool": lambda d: _entry(d, "2015.relationship.20")[
        "family_unit_exclusion"
    ].update(condition={"sex": True}),
    "b1_on_code_22": lambda d: _move(
        d, "2015.relationship.20", "2015.relationship.22"
    ),
    "b1_on_2017_code_20": lambda d: _move(
        d, "2015.relationship.20", "2017.relationship.20"
    ),
    "b2_on_2017_code_92": lambda d: _move(
        d, "2019.relationship.92", "2017.relationship.92"
    ),
    "b2_on_2019_code_10": lambda d: _move(
        d, "2019.relationship.90", "2019.relationship.10"
    ),
    "b2_conditional_with_ofum_income": lambda d: (
        _entry(d, "2019.relationship.90")["family_unit_exclusion"].update(
            condition={"sex": 1}
        ),
        _entry(d, "2019.relationship.90").update(income_role="ofum"),
    ),
    "b2_assigns_ofum_income": lambda d: _entry(
        d, "2021.relationship.92"
    ).update(income_role="ofum"),
    "b1_option_changed": lambda d: _entry(d, "2015.relationship.20")[
        "ruling"
    ].update(option="1d-1"),
    "b1_decision_fabricated": lambda d: _entry(d, "2015.relationship.20")[
        "ruling"
    ].update(decision="d999"),
    "b2_amended_lines_changed": lambda d: _entry(d, "2023.relationship.90")[
        "ruling"
    ].update(amends_draft_3_lines=[152]),
    "b2_waves_narrowed": lambda d: _entry(d, "2023.relationship.92")[
        "ruling"
    ].update(amended_waves=[2023]),
    "disposition_renamed": lambda d: _entry(d, "2019.relationship.92")[
        "family_unit_exclusion"
    ].update(disposition="uncooperative member in family unit"),
    "b1_exclusion_dropped": lambda d: _entry(d, "2015.relationship.20").pop(
        "family_unit_exclusion"
    ),
    "b2_exclusion_dropped": lambda d: (
        _entry(d, "2021.relationship.90").pop("family_unit_exclusion"),
        _entry(d, "2021.relationship.90").update(income_role="ofum"),
    ),
    "b2_action_documented_rule": lambda d: _entry(
        d, "2019.relationship.92"
    ).update(action="documented_rule"),
}


@pytest.mark.parametrize("mutation", sorted(D1090_SCOPE_MUTATIONS))
def test_d1090_exclusions_are_held_to_their_ratified_scope(mutation):
    document = registry.load_registry("roles")
    registry.validate_registry(document, expected_name="roles")
    changed = copy.deepcopy(document)
    D1090_SCOPE_MUTATIONS[mutation](changed)
    # Serialized, so a bool standing in for 1 still counts as a change.
    assert json.dumps(changed) != json.dumps(document)
    with pytest.raises(registry.SourceAdjudicationError):
        registry.validate_registry(changed, expected_name="roles")


def test_d1090_scope_matches_the_committed_entries():
    """Every ratified exclusion sits on exactly its scope's entries, each
    present and named by its own wave and code."""
    entries = registry.load_registry("roles")["entries"]
    for entry in entries:
        assert entry["id"] == (
            f"{entry['wave']}.relationship.{entry['code']}"
        ), entry["id"]
    for name, scope in registry.RATIFIED_EXCLUSIONS.items():
        carrying = {
            e["id"]: e
            for e in entries
            if e.get("family_unit_exclusion", {}).get("disposition") == name
        }
        assert set(carrying) == set(scope["entries"]), name
        assert all(e["present"] is True for e in carrying.values()), name


def test_d1090_scope_mutations_would_move_the_operative_rule():
    """Why the numeric fields matter: the builder's rules follow an
    entry's wave and code, so each swap above, if the validator let it
    through, would move or drop an exclusion in the role rules."""
    from populace_dynamics.uniform_cut_track_u2 import sources

    document = registry.load_registry("roles")
    expected = {
        key
        for key, rule in sources.RoleContext.from_registry().rules.items()
        if rule.family_unit_exclusion
    }
    for name in (
        "b1_code_swapped_with_22",
        "b1_wave_swapped_with_2017",
        "b2_code_swapped_with_10",
        "b2_wave_swapped_with_2017",
        "b1_marked_absent",
        "b2_marked_absent",
    ):
        changed = copy.deepcopy(document)
        D1090_SCOPE_MUTATIONS[name](changed)
        moved = {
            (int(e["wave"]), int(e["code"]))
            for e in changed["entries"]
            if e["present"] and "family_unit_exclusion" in e
        }
        assert moved != expected, name


# ---------------------------------------------------------------------------
# Max's d637 ruling (section 16b): each applied amendment, held to its exact
# scope (``u2_source_registry.RATIFIED_AMENDMENTS``)
# ---------------------------------------------------------------------------
def _copy_ruling(document, source, target):
    """Put ``source``'s d637 ruling on ``target`` as well."""
    _entry(document, target)["ruling"] = copy.deepcopy(
        _entry(document, source)["ruling"]
    )


#: (registry, mutation): each moves, drops, widens or rewrites an applied
#: d637 amendment, and each must fail validation.
D637_SCOPE_MUTATIONS = {
    "a2_ruling_on_2013_spouse_age": (
        "income",
        lambda d: _copy_ruling(
            d, "income.2015.wife_age", "income.2013.wife_age"
        ),
    ),
    "a2_ruling_on_a_slot_income_item": (
        "income",
        lambda d: _copy_ruling(
            d, "income.2019.wife_sex", "income.2019.wife_labor"
        ),
    ),
    "a2_ruling_dropped": (
        "income",
        lambda d: _entry(d, "income.2021.wife_age").pop("ruling"),
    ),
    "a2_decision_fabricated": (
        "income",
        lambda d: _entry(d, "income.2023.wife_sex")["ruling"].update(
            decision="d999"
        ),
    ),
    "a2_amendment_renumbered": (
        "income",
        lambda d: _entry(d, "income.2017.wife_age")["ruling"].update(
            amendment="3"
        ),
    ),
    "a2_ruling_dated_otherwise": (
        "income",
        lambda d: _entry(d, "income.2017.wife_sex")["ruling"].update(
            date="2026-10-10"
        ),
    ),
    "a2_usage_widened": (
        "income",
        lambda d: _entry(d, "income.2019.wife_age").update(
            usage="slot_occupancy"
        ),
    ),
    "a2_usage_dropped": (
        "income",
        lambda d: _entry(d, "income.2015.wife_sex").pop("usage"),
    ),
    "a2_reopened": (
        "income",
        lambda d: _entry(d, "income.2023.wife_age").update(
            status="TO VERIFY", question="reopened"
        ),
    ),
    "a2_question_kept": (
        "income",
        lambda d: _entry(d, "income.2021.wife_sex").update(question="kept"),
    ),
    "a2_refusing_action": (
        "income",
        lambda d: _entry(d, "income.2015.wife_age").update(
            action="refuse_slot_inference"
        ),
    ),
    "a3_ruling_on_a_component": (
        "income",
        lambda d: _copy_ruling(
            d,
            "income.2017.wife_retirement_annuities",
            "income.2017.wife_annuities",
        ),
    ),
    "a3_made_executable": (
        "income",
        lambda d: _entry(d, "income.2019.wife_retirement_annuities").update(
            kind="variable"
        ),
    ),
    "a3_usage_rewritten": (
        "income",
        lambda d: _entry(d, "income.2013.wife_retirement_annuities").update(
            usage="Executable scalar crosswalk"
        ),
    ),
    "a3_ruling_dropped": (
        "income",
        lambda d: _entry(d, "income.2023.wife_retirement_annuities").pop(
            "ruling"
        ),
    ),
    "a3_ruling_as_amendment_2": (
        "income",
        lambda d: _entry(d, "income.2015.wife_retirement_annuities")[
            "ruling"
        ].update(amendment="2"),
    ),
    "a4_ruling_on_wealth1_acc": (
        "wealth",
        lambda d: _copy_ruling(
            d, "wealth.2013.wealth2_acc", "wealth.2013.wealth1_acc"
        ),
    ),
    "a4_restriction_reverted": (
        "wealth",
        lambda d: _entry(d, "wealth.2015.checking_saving_acc").update(
            use_restriction=_entry(d, "wealth.2015.checking_saving_acc")[
                "use_restriction"
            ].replace(
                "ratified by Max on 2026-09-30: d637, specification section "
                "16b",
                "pending Max's ruling",
            )
        ),
    ),
    "a4_restriction_widened": (
        "wealth",
        lambda d: _entry(d, "wealth.2023.wealth2_acc").update(
            use_restriction="Imputation and sample selection"
        ),
    ),
    "a4_ruling_dropped": (
        "wealth",
        lambda d: _entry(d, "wealth.2019.wealth2_acc").pop("ruling"),
    ),
    "a5b_conditional_types_readded": (
        "pension",
        lambda d: _entry(d, "2015.route.formula_unknown_checkpoint").update(
            accepted_conditional_types=[1, 8]
        ),
    ),
    "a5b_formula_admitted": (
        "pension",
        lambda d: _entry(d, "2015.route.formula_unknown_checkpoint").update(
            accepted_plan_types=[5, 1]
        ),
    ),
    "a5b_branch_rewritten": (
        "pension",
        lambda d: _entry(d, "2015.route.formula_unknown_checkpoint").update(
            refused_branch="P62ACKPT: P62AMT=DK/RF"
        ),
    ),
    "a5b_disposition_renamed": (
        "pension",
        lambda d: _entry(d, "2015.route.formula_unknown_checkpoint").update(
            off_route_disposition="zero_filled"
        ),
    ),
    "a5b_refusal_kept": (
        "pension",
        lambda d: _entry(d, "2015.route.formula_unknown_checkpoint").update(
            refusal="kept"
        ),
    ),
    "a5b_on_2017_checkpoint": (
        "pension",
        lambda d: _copy_ruling(
            d,
            "2015.route.formula_unknown_checkpoint",
            "2017.route.formula_unknown_checkpoint",
        ),
    ),
    "a5b_lines_narrowed": (
        "pension",
        lambda d: _entry(d, "2015.route.formula_unknown_checkpoint")[
            "ruling"
        ].update(replaces_draft_3_lines=[1175]),
    ),
    "a2_blocked_again": (
        "income",
        lambda d: _entry(d, "income.2019.wife_sex").update(
            blocking_dependencies=["roles:2019.relationship.20"]
        ),
    ),
}


@pytest.mark.parametrize("mutation", sorted(D637_SCOPE_MUTATIONS))
def test_d637_amendments_are_held_to_their_ratified_scope(mutation):
    name, change = D637_SCOPE_MUTATIONS[mutation]
    document = registry.load_registry(name)
    registry.validate_registry(document, expected_name=name)
    changed = copy.deepcopy(document)
    change(changed)
    assert json.dumps(changed) != json.dumps(document)
    with pytest.raises(registry.SourceAdjudicationError):
        registry.validate_registry(changed, expected_name=name)


def test_d637_scope_matches_the_committed_entries():
    """Every applied d637 amendment sits on exactly its scope's entries, in
    its own registry, and no other entry records a d637 ruling."""
    scoped = {
        (scope["registry"], key): amendment
        for amendment, scope in registry.RATIFIED_AMENDMENTS.items()
        for key in scope["entries"]
    }
    found = {}
    for name in registry.REGISTRY_NAMES:
        for entry in registry.load_registry(name)["entries"]:
            ruling = entry.get("ruling", {})
            if ruling.get("decision") == "d637":
                found[(name, entry["id"])] = ruling["amendment"]
    assert found == scoped
    for scope in registry.RATIFIED_AMENDMENTS.values():
        assert scope["ruling"]["decision"] == "d637"
        assert len(scope["entries"]) == len(set(scope["entries"]))
