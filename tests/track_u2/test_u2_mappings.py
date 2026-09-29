"""Income and wealth maps through the registry adapters (section 13).

Group "Income/wealth maps": exact labels and widths, losses, sentinels,
seven/eight-asset identities, debt once, home equity excluded -- on
INVENTED fixed-width records written in each wave's registry layout
(section 4 pre-registration step 5).  Also: every route marked TO VERIFY
or unresolved refuses under the registry gate, never falls back.
INVENTED DATA - NOT A COMPARISON.
"""

from __future__ import annotations

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
def test_invented_records_round_trip_every_field(wave, u2_inputs, declared_gate):
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


def _one_record(u2_inputs, declared_gate, wave=2019, **changes):
    records = invented.invented_fixed_width_records(
        u2_inputs, wave, declared_gate
    )
    raw = records["raw"].copy()
    for column, value in changes.items():
        raw.loc[raw.index[0], column] = value
    return (
        sources.encode_fixed_width(
            raw[[spec.concept for spec in records["specs"]]], records["specs"]
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
    u2_inputs, declared_gate, changes, message
):
    lines, specs = _one_record(u2_inputs, declared_gate, **changes)
    if message is None:
        # Vehicles and WEALTH1 document negative balances: accepted.
        parsed = sources.parse_fixed_width(lines, specs)
        assert int(parsed["vehicles"].iloc[0]) == -5
        return
    with pytest.raises(sources.U2SourceRefusal, match=message):
        sources.parse_fixed_width(lines, specs)


def test_parse_refuses_blank_truncated_and_duplicate_records(
    u2_inputs, declared_gate
):
    lines, specs = _one_record(u2_inputs, declared_gate)
    interview = next(spec for spec in specs if spec.concept == "interview")
    blank = lines[0][: interview.start - 1] + " " * interview.width + lines[0][
        interview.end :
    ]
    with pytest.raises(sources.U2SourceRefusal, match="blank"):
        sources.parse_fixed_width([blank], specs)
    with pytest.raises(sources.U2SourceRefusal, match="truncated"):
        sources.parse_fixed_width([lines[0][: max(s.end for s in specs) - 1]], specs)
    with pytest.raises(sources.U2SourceRefusal, match="duplicate"):
        sources.parse_fixed_width([lines[0], lines[0]], specs)


@pytest.mark.parametrize("wave", sources.SUPPORT_WAVES)
def test_wealth1_identity_seven_or_eight_assets_debt_once(
    wave, declared_gate
):
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


def test_registry_gate_refuses_every_open_wave(registry_gate):
    # 2013: every mapping U2 reads is resolved (the 2013 meanings are
    # U1's); 2015-2023: every income entry waits on the open role routing.
    specs = loader.family_record_specs(2013, registry_gate)
    concepts = {spec.concept for spec in specs}
    assert set(sources.INCOME_CONCEPTS) <= concepts
    assert {"wealth1", "vehicles", "head_current_amount"} <= concepts
    for wave in (2015, 2017, 2019, 2021, 2023):
        with pytest.raises(sources.U2SourceRefusal, match="roles:"):
            loader.family_record_specs(wave, registry_gate)


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
    assert any("roles:2019.relationship.92" in reason for reasons in refused.values() for reason in reasons)


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
    registries = sources.RegistrySet(documents, {}, "committed")
    assert loader.check_source_hashes(registries, tmp_path) == {
        "PSID/family/2019/x.sps": digest
    }
    (staged / "x.sps").write_text("CHANGED")
    with pytest.raises(loader.U2LoaderRefusal, match="changed"):
        loader.check_source_hashes(registries, tmp_path)
