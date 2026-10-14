"""Income and wealth maps through the registry adapters (section 13).

Group "Income/wealth maps": exact labels and widths, losses, sentinels,
seven/eight-asset identities, debt once, home equity excluded -- on
INVENTED fixed-width records written in each wave's registry layout
(section 4 pre-registration step 5).  Also: every route marked TO VERIFY
or unresolved refuses under the registry gate, never falls back.
INVENTED DATA - NOT A COMPARISON.
"""

from __future__ import annotations

import functools
import hashlib
import json

import pandas as pd
import pytest

from populace_dynamics.data import u2_source_registry as registry
from populace_dynamics.uniform_cut_track_u2 import invented, loader, sources


@pytest.fixture(scope="module")
def declared_gate(committed_registries):
    return sources.SourceGate(sources.INVENTED_DECLARED, committed_registries)


@pytest.fixture(scope="module")
def registry_gate(committed_registries):
    return sources.SourceGate(sources.REGISTRY, committed_registries)


def test_registries_are_the_pinned_milestone_1_bytes(committed_registries):
    assert committed_registries.kind == "committed"
    assert dict(committed_registries.sha256) == sources.REGISTRY_SHA256
    assert tuple(sorted(committed_registries.documents)) == tuple(
        sorted(registry.REGISTRY_NAMES)
    )


#: Keys that hold citations or prose only.  The loader type-checks them
#: (``u2_source_registry.py:262`` and ``:357-360``) and quotes ``question``
#: in a TO VERIFY refusal message (``:427``), but no gate decision reads
#: them: ``require_resolved`` refuses on status, blocking dependencies and
#: a refusal action (``:425-436``).
_PROSE_KEYS = frozenset(
    {
        "citations",
        "construction",
        "corroboration",
        "open_question",
        "part_b_finding",
        "question",
    }
)

#: SHA-256 of each registry's gate projection (every field except
#: :data:`_PROSE_KEYS`, at any depth, as canonical JSON) at the
#: adjudicated registries of commit 883ea48.  Milestone 1b (b948d6b)
#: moved the roles and weights bytes, so :data:`sources.REGISTRY_SHA256`
#: moved with them; these projection pins did not move, which is the
#: evidence that milestone 1b changed citations and prose only.
_ADJUDICATED_GATE_PROJECTION_SHA256 = {
    "income": (
        "51a568d57911e2beabc1ae39af2f9ac34c3f9005a97ab3325f1dc4a647d79555"
    ),
    "wealth": (
        "6e325c1aca974e24cc85e9c6ed0443a5f330d4d971e2a1f3a6e3883c8e89cf9d"
    ),
    "individual": (
        "4f53d5d2c3157e55c7ca62fb82cf82895ac37616838c3a48fe9769c0f2ea0b74"
    ),
    "pension": (
        "66f51b857304b7718d7ec2a6fe07c924c80586f222a13c002f14108dca6022cf"
    ),
    "roles": (
        "0fd3b8374e40430456aa06a788d13617bc766dee115bf262b6c3fd234887d285"
    ),
    "support": (
        "0cddbbc5a6997850ea2bce0b90c1762da193f6eb251f3d00f0120d2c63f96bc6"
    ),
    "weights": (
        "dd943cbe9cee30a1bd87724449a642999c7770e22c1134e79685078e73439969"
    ),
    "design": (
        "16d455a184005365bb540ce660834c1250093f42e4d5a30cd2a1946cf9948e35"
    ),
}


#: Max's d1090 ruling (2026-10-10, section 16c) moved the gate fields of
#: three registries in its own reviewed commit; the other five keep the
#: adjudicated projection.  The registries before that commit are read
#: from Git (CI fetches full history) at master's last pre-d1090 commit.
D1090_MOVED = ("income", "pension", "roles")
PRE_D1090_COMMIT = "1fadf50a70d1f66151597e27a81daa191ee37e4a"
_D1090_GATE_PROJECTION_SHA256 = {
    "income": (
        "15c439a3282857caddbc911f8e1a133f1cb09ac00a90142699bf67e87d8a865e"
    ),
    "pension": (
        "8fd81ec9fb5b36dbfa6af3cba224d378727cf4fccdb4dd4f7d731fa1847c9923"
    ),
    "roles": (
        "7d15c273b95396e7684ab38106c2c19f0f476b6f839812644aed03f3ceff66d3"
    ),
}
#: The d1090 registry commit's ruled entries and the role dependencies it
#: released (section 16c).
D1090_ROLES = frozenset(
    {"2015.relationship.20"}
    | {
        f"{wave}.relationship.{code}"
        for wave in (2019, 2021, 2023)
        for code in (90, 92)
    }
)
D1090_DEPENDENCIES = frozenset(f"roles:{key}" for key in D1090_ROLES)


def _pre_d1090(name):
    import subprocess

    blob = f"{PRE_D1090_COMMIT}:data/external/track_u2/{name}.json"
    found = subprocess.run(
        ["git", "-C", str(registry.REGISTRY_DIRECTORY), "show", blob],
        capture_output=True,
    )
    assert found.returncode == 0, found.stderr.decode()
    return found.stdout


def _projection_sha256(raw):
    projection = json.dumps(
        _gate_projection(json.loads(raw)),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(projection).hexdigest()


def _gate_projection(value):
    if isinstance(value, dict):
        return {
            key: _gate_projection(item)
            for key, item in value.items()
            if key not in _PROSE_KEYS
        }
    if isinstance(value, list):
        return [_gate_projection(item) for item in value]
    return value


def test_milestone_1b_moved_only_citations_and_prose():
    """The milestone-1b pin test ``sources.REGISTRY_SHA256`` cites.

    Every status, disposition, dependency, action, role and layout field
    is where the adjudicated registries put it: in the five registries
    d1090 left alone today, and in the three it moved as they stood before
    its commit.  So every route that refused at 883ea48 refused until
    d1090, and its moves are exactly those the next test pins.
    """
    assert set(_ADJUDICATED_GATE_PROJECTION_SHA256) == set(
        sources.REGISTRY_SHA256
    )
    for name, expected in _ADJUDICATED_GATE_PROJECTION_SHA256.items():
        raw = (registry.REGISTRY_DIRECTORY / f"{name}.json").read_bytes()
        assert hashlib.sha256(raw).hexdigest() == sources.REGISTRY_SHA256[name]
        if name in D1090_MOVED:
            assert _projection_sha256(_pre_d1090(name)) == expected, name
            current = _D1090_GATE_PROJECTION_SHA256[name]
            assert _projection_sha256(raw) == current, name
        else:
            assert _projection_sha256(raw) == expected, name


def _changed_keys(before, after):
    keys = set(before) | set(after)
    return {k for k in keys if before.get(k, None) != after.get(k, None)}


def test_d1090_moved_only_the_ruled_gate_fields():
    """The d1090 registry commit (section 16c), field by field: the eight
    ruled entries change only their action, refusal, role, exclusion,
    resolution and ruling fields; every other entry changes only by losing
    a dependency on a ruled role entry; no entry is added, dropped or
    reordered, and nothing else moves."""
    ruled = {
        ("roles", "2015.relationship.20"): {
            "action",
            "refusal",
            "refusal_condition",
            "family_unit_exclusion",
            "resolution",
            "ruling",
            "superseded_refusal",
        },
        ("pension", "2015.route.respondent_slots"): {
            "action",
            "refusal",
            "blocking_dependencies",
            "resolution",
            "ruling",
            "superseded_refusal",
        },
    } | {
        ("roles", key): {
            "action",
            "refusal",
            "refused_income_role",
            "income_role",
            "family_unit_exclusion",
            "resolution",
            "ruling",
            "superseded_refusal",
        }
        for key in D1090_ROLES - {"2015.relationship.20"}
    }
    released = {}
    for name in D1090_MOVED:
        before = _gate_projection(json.loads(_pre_d1090(name)))
        after = _gate_projection(
            json.loads(
                (registry.REGISTRY_DIRECTORY / f"{name}.json").read_bytes()
            )
        )
        top = _changed_keys(before, after) - {"entries"}
        assert top == (
            {"rulings_applied", "status_scope"}
            if name == "income"
            else {"rulings_applied"}
        ), name
        assert after["rulings_applied"][0]["decision"] == "d1090"
        assert [e["id"] for e in before["entries"]] == [
            e["id"] for e in after["entries"]
        ], name
        for old, new in zip(before["entries"], after["entries"], strict=True):
            changed = _changed_keys(old, new)
            if not changed:
                continue
            key = (name, old["id"])
            if key in ruled:
                assert changed == ruled[key], key
                continue
            assert changed == {"blocking_dependencies"}, key
            dropped = set(old["blocking_dependencies"]) - set(
                new.get("blocking_dependencies", [])
            )
            assert dropped and dropped <= D1090_DEPENDENCIES, key
            assert set(new.get("blocking_dependencies", [])) <= set(
                old["blocking_dependencies"]
            ), key
            released[key] = not new.get("blocking_dependencies")
        for entry in after["entries"]:
            assert not set(entry.get("blocking_dependencies", [])) & (
                D1090_DEPENDENCIES
            ), (name, entry["id"])
    # The master record's counts: 492 income and 61 more pension entries
    # (with the ruled 2015 spouse slot, 62); 537 more released in full.
    assert sum(1 for key in released if key[0] == "income") == 492
    assert sum(1 for key in released if key[0] == "pension") == 61
    assert sum(released.values()) == 492 + 45


def test_the_gate_projection_sees_a_moved_gate_field():
    """A changed status is not prose: the projection hash moves."""
    raw = (registry.REGISTRY_DIRECTORY / "weights.json").read_bytes()
    document = json.loads(raw)
    target = next(
        entry
        for entry in document["entries"]
        if entry.get("status") == "TO VERIFY"
    )
    target["status"] = "RESOLVED"
    target["question"] = "prose moves are ignored"
    projection = json.dumps(
        _gate_projection(document),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    assert (
        hashlib.sha256(projection).hexdigest()
        != _ADJUDICATED_GATE_PROJECTION_SHA256["weights"]
    )


@pytest.mark.parametrize("wave", sources.SUPPORT_WAVES)
def test_specs_carry_exact_registry_labels_positions_and_widths(
    wave, declared_gate, committed_registries
):
    specs = loader.family_record_specs(wave, declared_gate)
    assert len({spec.concept for spec in specs}) == len(specs)
    for spec in specs:
        name, entry_id = spec.registry_id.split(":", 1)
        entry = committed_registries.entry(name, entry_id)
        assert entry["variable"] == spec.variable
        if name == "pension":
            layout = entry["position"]
            assert (layout["start"], layout["end"], layout["width"]) == (
                spec.start,
                spec.end,
                spec.width,
            )
        else:
            assert (
                entry["position_start"],
                entry["position_end"],
                entry["width"],
            ) == (spec.start, spec.end, spec.width)
            assert spec.negative_allowed == entry["negative_domain_documented"]
        assert spec.width == spec.end - spec.start + 1
    labels = {
        spec.concept: committed_registries.entry(
            *spec.registry_id.split(":", 1)
        )["label"]
        for spec in specs
        if spec.registry_id.startswith("income")
    }
    assert "TOTAL FAMILY INCOME" in labels["total_family_income"]
    assert "IRA" in labels["head_iras"]


@pytest.mark.parametrize("wave", sources.SUPPORT_WAVES)
def test_invented_records_round_trip_every_field(
    wave, u2_inputs, declared_gate
):
    records = invented.invented_fixed_width_records(
        u2_inputs, wave, declared_gate
    )
    parsed = sources.parse_fixed_width(records["lines"], records["specs"])
    raw = records["raw"][[spec.concept for spec in records["specs"]]]
    pd.testing.assert_frame_equal(
        parsed.reset_index(drop=True), raw.reset_index(drop=True)
    )
    frames = loader.read_family_records(records["lines"], wave, declared_gate)
    pd.testing.assert_frame_equal(
        frames["income"].reset_index(drop=True),
        u2_inputs.family_income[wave].reset_index(drop=True),
    )
    assert frames["income_identity"]["n_exact"] == len(records["lines"])
    assert frames["wealth1_identity"]["n_exact"] == len(records["lines"])


def test_losses_top_codes_and_sentinels_are_carried(u2_inputs, declared_gate):
    seen = {"loss": 0, "negative_wealth": 0, "top": 0, "dk_age": 0}
    for wave in sources.SUPPORT_WAVES:
        raw = invented.invented_fixed_width_records(
            u2_inputs, wave, declared_gate
        )["raw"]
        seen["loss"] += int((raw["head_farm"] < 0).sum())
        seen["negative_wealth"] += int((raw["wealth1"] < 0).sum())
        seen["top"] += int((raw["head_dividends"] == 999_997).sum())
        seen["dk_age"] += int((raw["wife_age"] == 999).sum())
        decoded = u2_inputs.family_income[wave]
        dk = raw["wife_age"].to_numpy() == 999
        assert decoded["wife_present"].to_numpy()[dk].all()
        assert decoded["wife_age"].isna().to_numpy()[dk].all()
    assert all(value > 0 for value in seen.values()), seen


def _one_record(u2_inputs, registry_gate, wave=2013, **changes):
    """One invented record in 2013's layout under the registry gate (the
    path a real run parses: 2013's routes are resolved), with
    ``changes``; the parse refusals are the registry path's."""

    records = invented.invented_fixed_width_records(
        u2_inputs, wave, registry_gate
    )
    raw = records["raw"].copy()
    for column, value in changes.items():
        raw.loc[raw.index[0], column] = value
    return (
        sources.encode_fixed_width(
            raw[[spec.concept for spec in records["specs"]]],
            records["specs"],
            filler=sources.INVENTED_RECORD_FILLER,
        ),
        records["specs"],
    )


@pytest.mark.parametrize(
    "changes, message",
    [
        ({"head_ss": -1}, "documented domain"),
        ({"vehicles": -5, "wealth1": -5}, None),
        ({"wife_age": 7}, "documented domain"),
        ({"fu_size": 0}, "documented domain"),
        ({"wealth1_acc": 2}, "documented domain"),
        ({"head_current_type": 6}, "documented domain"),
        ({"head_prev1_type": 3}, "documented domain"),
        ({"wife_prev2_dc_disposition": 5}, "documented domain"),
        ({"census_needs_standard": 0}, "documented domain"),
    ],
)
def test_parse_refuses_undocumented_values(
    u2_inputs, registry_gate, changes, message
):
    lines, specs = _one_record(u2_inputs, registry_gate, **changes)
    if message is None:
        # Vehicles and WEALTH1 document negative balances: accepted.
        parsed = sources.parse_fixed_width(lines, specs)
        assert int(parsed["vehicles"].iloc[0]) == -5
        return
    with pytest.raises(sources.U2SourceRefusal, match=message):
        sources.parse_fixed_width(lines, specs)


def test_parse_refuses_blank_truncated_and_duplicate_records(
    u2_inputs, registry_gate
):
    lines, specs = _one_record(u2_inputs, registry_gate)
    assert {spec.gate for spec in specs} == {sources.REGISTRY}
    interview = next(spec for spec in specs if spec.concept == "interview")
    blank = (
        lines[0][: interview.start - 1]
        + " " * interview.width
        + lines[0][interview.end :]
    )
    with pytest.raises(sources.U2SourceRefusal, match="blank"):
        sources.parse_fixed_width([blank], specs)
    with pytest.raises(sources.U2SourceRefusal, match="truncated"):
        sources.parse_fixed_width(
            [lines[0][: max(s.end for s in specs) - 1]], specs
        )
    with pytest.raises(sources.U2SourceRefusal, match="duplicate"):
        sources.parse_fixed_width([lines[0], lines[0]], specs)


@pytest.mark.parametrize("wave", sources.SUPPORT_WAVES)
def test_wealth1_identity_seven_or_eight_assets_debt_once(wave, declared_gate):
    identity = sources.wealth1_identity(wave, declared_gate)
    assert len(identity["assets"]) == (7 if wave <= 2017 else 8)
    assert tuple(identity["assets"]) == invented.WEALTH_ASSETS[wave]
    assert tuple(identity["debts"]) == invented.WEALTH_DEBTS
    assert identity["excluded"] == "home_equity"
    assert "home_equity" not in identity["assets"] + identity["debts"]
    assert not set(identity["assets"]) & set(identity["debts"])
    assert "farm_business" not in identity["assets"]
    assert ("cd_bonds_treasury" in identity["assets"]) == (wave >= 2019)


def test_wealth1_identity_counts_a_broken_identity(u2_inputs, declared_gate):
    wave = 2021
    identity = sources.wealth1_identity(wave, declared_gate)
    frame = u2_inputs.family_wealth[wave].copy()
    frame.loc[frame.index[0], "home_equity"] += 1_000_000
    assert sources.wealth1_identity_counts(frame, identity)["n_exact"] == len(
        frame
    )
    frame.loc[frame.index[0], "other_debt"] += 7
    assert (
        sources.wealth1_identity_counts(frame, identity)["n_exact"]
        == len(frame) - 1
    )


def test_crosswalks_are_never_executable_inputs(declared_gate):
    with pytest.raises(sources.U2SourceRefusal, match="documentary"):
        sources.field_specs(
            "income", 2019, ["wife_retirement_annuities"], declared_gate
        )
    with pytest.raises(sources.U2SourceRefusal, match="documentary"):
        sources.field_specs(
            "wealth",
            2013,
            ["farm_business"],
            sources.SourceGate(
                sources.INVENTED_DECLARED, declared_gate.registries
            ),
        )


#: The first registry blocker each later wave's family-record specs meet
#: (income concepts are read first, in :data:`sources.INCOME_CONCEPTS`
#: order): every later wave's spouse age slot metadata, still TO VERIFY
#: (amendment 2).  Until the d1090 registry commit (section 16c), 2015's
#: income entries depended on the refused 2015 code-20 route and
#: 2019-2023's on the refused code-90/92 routes; those dependencies are
#: released.
FIRST_BLOCKER = {
    wave: f"income:income.{wave}.wife_age: TO VERIFY"
    for wave in (2015, 2017, 2019, 2021, 2023)
}


def test_registry_gate_refuses_every_open_wave(registry_gate):
    # 2013: every mapping U2 reads is resolved (the 2013 meanings are
    # U1's); 2015-2023: each wave meets a TO VERIFY or refused entry.
    specs = loader.family_record_specs(2013, registry_gate)
    concepts = {spec.concept for spec in specs}
    assert set(sources.INCOME_CONCEPTS) <= concepts
    assert {"wealth1", "vehicles", "head_current_amount"} <= concepts
    for wave, blocker in FIRST_BLOCKER.items():
        with pytest.raises(sources.U2SourceRefusal) as error:
            loader.family_record_specs(wave, registry_gate)
        assert blocker in str(error.value), (wave, str(error.value)[:200])


@pytest.mark.parametrize("wave", sources.SUPPORT_WAVES)
def test_registry_gate_agrees_with_the_loader_api(wave, monkeypatch):
    """Differential: every entry a U2 run applies passes the registry
    gate exactly when the milestone-1 loader's ``require_resolved``
    returns it.  ``load_registry`` is memoized for the test only (the
    loader rereads and revalidates a whole registry per call); the rule
    under test is ``require_resolved``'s own."""

    cached = functools.lru_cache(maxsize=None)(registry.load_registry)
    monkeypatch.setattr(registry, "load_registry", cached)
    registries = sources.RegistrySet.committed()
    for name, entry_id in loader.required_entries(registries):
        if registries.entry(name, entry_id).get("wave") != wave:
            continue
        gate = sources.SourceGate(sources.REGISTRY, registries)
        try:
            registry.require_resolved(name, entry_id)
        except registry.SourceAdjudicationError:
            with pytest.raises(sources.U2SourceRefusal):
                gate.require(name, entry_id)
        else:
            assert gate.require(name, entry_id) is registries.entry(
                name, entry_id
            )


def test_registry_gate_only_accepts_committed_registries(committed_registries):
    invented_set = sources.RegistrySet(
        committed_registries.documents,
        committed_registries.sha256,
        "invented",
    )
    with pytest.raises(sources.U2SourceRefusal, match="committed"):
        sources.SourceGate(sources.REGISTRY, invented_set)


def test_declared_gate_records_what_the_registry_gate_refuses(
    committed_registries,
):
    gate = sources.SourceGate(sources.INVENTED_DECLARED, committed_registries)
    loader.family_record_specs(2019, gate)
    audit = gate.audit()
    assert audit["gate"] == sources.INVENTED_DECLARED
    refused = audit["would_refuse_under_registry_gate"]
    assert "income:income.2019.wife_age" in refused
    # Since d1090 no reason is a ruled role entry (section 16c).
    assert not any(
        dependency in reason
        for reasons in refused.values()
        for reason in reasons
        for dependency in D1090_DEPENDENCIES
    )
    assert any(
        "pension:2019.route.inherited_route_amendment" in reason
        for reasons in refused.values()
        for reason in reasons
    )


def test_source_preflight_refuses_before_opening_any_psid_file(
    tmp_path, monkeypatch
):
    opened = []

    def spy(event, args):
        if event == "open" and args and str(args[0]).startswith(str(tmp_path)):
            opened.append(args[0])

    import sys

    sys.addaudithook(spy)
    with pytest.raises(loader.U2LoaderRefusal, match="registry blockers"):
        loader.load_u2_inputs(data_dir=tmp_path)
    assert opened == []


def test_source_preflight_lists_the_open_entries(committed_registries):
    with pytest.raises(loader.U2LoaderRefusal) as error:
        loader.source_preflight(committed_registries)
    assert "weights:2017.cross_section_weight" in str(error.value) or (
        "registry blockers" in str(error.value)
    )
    entries = loader.required_entries(committed_registries)
    assert ("weights", "2017.cross_section_weight") in entries
    assert ("roles", "2019.relationship.92") in entries
    assert len(entries) == len(set(entries))


def test_layouts_are_cross_checked_against_a_setup_file(
    tmp_path, declared_gate
):
    specs = loader.family_record_specs(2019, declared_gate)[:3]
    good = tmp_path / "good.sps"
    good.write_text(
        "DATA LIST FILE = x /\n"
        + "\n".join(
            f"   {spec.variable} {spec.start} - {spec.end}" for spec in specs
        )
        + "\n.\n"
    )
    assert loader.check_layouts_against_setup(specs, good) == 3
    bad = tmp_path / "bad.sps"
    bad.write_text(
        "DATA LIST FILE = x /\n"
        + "\n".join(
            f"   {spec.variable} {spec.start + 1} - {spec.end + 1}"
            for spec in specs
        )
        + "\n.\n"
    )
    with pytest.raises(loader.U2LoaderRefusal, match="differ"):
        loader.check_layouts_against_setup(specs, bad)


def test_cited_source_hashes_refuse_changed_bytes(
    tmp_path, committed_registries
):
    documents = {
        name: dict(document)
        for name, document in committed_registries.documents.items()
    }
    staged = tmp_path / "family" / "2019"
    staged.mkdir(parents=True)
    (staged / "x.sps").write_text("INVENTED")
    import hashlib

    digest = hashlib.sha256(b"INVENTED").hexdigest()
    for document in documents.values():
        document["sources"] = []
    documents["income"]["sources"] = [
        {"file": "PSID/family/2019/x.sps", "sha256": digest}
    ]
    # Changed documents cannot be labelled committed (the label is bound
    # to the pinned bytes); the rehash itself reads any registry set.
    with pytest.raises(sources.U2SourceRefusal, match="labelled committed"):
        sources.RegistrySet(documents, {}, "committed")
    registries = sources.RegistrySet(documents, {}, "invented")
    assert loader.check_source_hashes(registries, tmp_path) == {
        "PSID/family/2019/x.sps": digest
    }
    (staged / "x.sps").write_text("CHANGED")
    with pytest.raises(loader.U2LoaderRefusal, match="changed"):
        loader.check_source_hashes(registries, tmp_path)


def test_the_declared_gate_reads_only_invented_records(
    u2_inputs, declared_gate, registry_gate
):
    """Review finding 1: records not written by the invented writer (here
    the same values with blank unmapped columns, as a survey file has)
    are refused under the declared gate; the registry gate is not
    affected by the filler."""

    records = invented.invented_fixed_width_records(
        u2_inputs, 2019, declared_gate
    )
    assert all(
        sources.INVENTED_RECORD_FILLER in line for line in records["lines"]
    )
    blank = [
        line.replace(sources.INVENTED_RECORD_FILLER, " ")
        for line in records["lines"]
    ]
    with pytest.raises(sources.U2SourceRefusal, match="invented writer"):
        loader.read_family_records(blank, 2019, declared_gate)
    digits = [
        line.replace(sources.INVENTED_RECORD_FILLER, "0")
        for line in records["lines"]
    ]
    with pytest.raises(sources.U2SourceRefusal, match="invented writer"):
        loader.read_family_records(digits, 2019, declared_gate)
    truncated = [line[:-1] for line in records["lines"]]
    with pytest.raises(sources.U2SourceRefusal, match="invented writer"):
        loader.read_family_records(truncated, 2019, declared_gate)
    frames = loader.read_family_records(records["lines"], 2019, declared_gate)
    assert len(frames["income"]) == len(records["lines"])
    with pytest.raises(loader.U2LoaderRefusal, match="SourceGate"):
        loader.read_family_records(records["lines"], 2019, "registry")


def test_a_registry_gate_is_bound_at_construction(committed_registries):
    gate = sources.SourceGate(sources.REGISTRY, committed_registries)
    import dataclasses

    with pytest.raises(dataclasses.FrozenInstanceError):
        gate.kind = sources.INVENTED_DECLARED  # type: ignore[misc]


def test_declared_specs_parse_only_invented_records(u2_inputs, declared_gate):
    """Review 2, finding 4: the invented-records check sits in the parser,
    so composing the public pieces (declared specs, parse, declared DC
    route) cannot read survey-shaped records either."""

    records = invented.invented_fixed_width_records(
        u2_inputs, 2021, declared_gate
    )
    specs = loader.family_record_specs(2021, declared_gate)
    assert {spec.gate for spec in specs} == {sources.INVENTED_DECLARED}
    survey_shaped = [
        line.replace(sources.INVENTED_RECORD_FILLER, " ")
        for line in records["lines"]
    ]
    with pytest.raises(sources.U2SourceRefusal, match="invented writer"):
        sources.parse_fixed_width(survey_shaped, specs)
    parsed = sources.parse_fixed_width(records["lines"], specs)
    assert len(parsed) == len(records["lines"])


def test_registry_documents_are_read_only(committed_registries):
    """Review 2, finding 3: a checked entry cannot be edited in place; a
    deep copy is an ordinary dict, and a changed copy cannot be labelled
    committed."""

    import copy
    import json

    entry = committed_registries.entry(
        "pension", "2021.route.inherited_route_amendment"
    )
    with pytest.raises(TypeError, match="read-only"):
        entry["action"] = "apply"
    with pytest.raises(TypeError, match="read-only"):
        entry.pop("action")
    with pytest.raises(TypeError, match="read-only"):
        entry.update(status="RESOLVED")
    with pytest.raises(TypeError, match="read-only"):
        committed_registries.documents["pension"]["entries"] = ()
    with pytest.raises(AttributeError):
        committed_registries.documents["roles"]["entries"].append({})
    edited = copy.deepcopy(dict(committed_registries.documents))
    assert type(edited["pension"]) is dict
    for item in edited["pension"]["entries"]:
        if item["id"] == "2021.route.inherited_route_amendment":
            item["action"] = "apply"
    with pytest.raises(sources.U2SourceRefusal, match="labelled committed"):
        sources.RegistrySet(
            edited, dict(committed_registries.sha256), "committed"
        )
    # The frozen documents still serialize to the pinned canonical form.
    assert json.loads(json.dumps(committed_registries.documents["design"]))
    with pytest.raises(loader.U2LoaderRefusal, match="registry blockers"):
        loader.source_preflight(committed_registries)


# ---------------------------------------------------------------------------
# The third review: final classes, copies, pickles and the shared cache
# ---------------------------------------------------------------------------
def test_gates_and_registry_sets_are_final():
    with pytest.raises(TypeError, match="final"):

        class _Gate(sources.SourceGate):  # noqa: F841
            pass

    with pytest.raises(TypeError, match="final"):

        class _Registries(sources.RegistrySet):  # noqa: F841
            pass


def test_registry_set_copies_and_pickles_keep_their_binding(
    committed_registries,
):
    import copy
    import pickle

    assert copy.copy(committed_registries) is committed_registries
    assert copy.deepcopy(committed_registries) is committed_registries
    restored = pickle.loads(pickle.dumps(committed_registries))
    assert restored.kind == "committed"
    assert type(restored.documents["pension"]) is sources.FrozenDocument
    with pytest.raises(TypeError, match="read-only"):
        restored.entry("pension", "2021.route.previous_dc_only")[
            "status"
        ] = "RESOLVED"
    with pytest.raises(loader.U2LoaderRefusal, match="registry blockers"):
        loader.source_preflight(restored)


def test_a_committed_set_built_from_plain_documents_is_frozen():
    import json

    documents = {
        name: json.loads(sources.registry_path(name).read_text())
        for name in sources.REGISTRY_SHA256
    }
    built = sources.RegistrySet(
        documents, dict(sources.REGISTRY_SHA256), "committed"
    )
    entry = built.entry("roles", "2015.relationship.20")
    assert type(entry) is sources.FrozenDocument
    with pytest.raises(TypeError, match="read-only"):
        entry["action"] = "apply"
    with pytest.raises(TypeError, match="read-only"):
        entry.__init__({"status": "RESOLVED"})
    # The caller's own documents are untouched and still editable.
    documents["roles"]["entries"][0]["x"] = 1
    invented_set = sources.RegistrySet.from_documents(built.documents)
    assert invented_set.kind == "invented"


def test_a_tampered_shared_document_is_caught_by_the_next_check(tmp_path):
    """Even a C-level edit of the shared, cached committed document (which
    ``FrozenDocument`` cannot block) is caught: every committed set, the
    registry gate and the loader's source preflight recheck the pinned
    bytes.  Run in a fresh interpreter so this process's cache is not
    touched."""

    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    script = tmp_path / "tamper.py"
    script.write_text(
        "import sys\n"
        f"sys.path.insert(0, {str(root / 'src')!r})\n"
        "from populace_dynamics.uniform_cut_track_u2 import loader, sources\n"
        "committed = sources.RegistrySet.committed()\n"
        "entry = committed.entry('pension',\n"
        "    '2021.route.inherited_route_amendment')\n"
        "dict.__setitem__(entry, 'action', 'apply')\n"
        "for call in (sources.RegistrySet.committed,\n"
        "             lambda: loader.source_preflight(committed),\n"
        "             lambda: sources.SourceGate(sources.REGISTRY,\n"
        "                                        committed)):\n"
        "    try:\n"
        "        call()\n"
        "        print('ACCEPTED')\n"
        "    except sources.U2SourceRefusal as error:\n"
        "        print('REFUSED', 'labelled committed' in str(error))\n"
    )
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        check=True,
        cwd=root,
    )
    assert result.stdout.split("\n")[:3] == ["REFUSED True"] * 3, result.stdout
