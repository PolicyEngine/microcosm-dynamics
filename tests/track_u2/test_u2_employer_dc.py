"""Employer DC routes for row U7 (section 13, group "Employer DC").

All verified current/previous-plan routes, the checkpoint branches, IRA
rollovers and duplicate accounts, on INVENTED pension items; and the
registry gate's refusal of every later-wave route still marked TO VERIFY.
INVENTED DATA - NOT A COMPARISON.
"""

from __future__ import annotations

import pandas as pd
import pytest

from populace_dynamics.data import employer_dc as u1_dc
from populace_dynamics.uniform_cut_track_u2 import sources

WIDTHS = {"current": 9, "combo": 8, "dc": 8}


def _items(**values: int) -> pd.DataFrame:
    row = {"interview": 1}
    for person in ("head", "wife"):
        row[f"{person}_current_type"] = 0
        row[f"{person}_current_amount"] = 0
        for plan in (1, 2):
            for item in (
                "type",
                "combo_disposition",
                "combo_amount",
                "dc_disposition",
                "dc_amount",
            ):
                row[f"{person}_prev{plan}_{item}"] = 0
    row.update(values)
    return pd.DataFrame([row]).astype("int64")


def _widths(frame: pd.DataFrame) -> dict[str, int]:
    return {
        column: WIDTHS[
            (
                "current"
                if "current" in column
                else ("combo" if "combo" in column else "dc")
            )
        ]
        for column in frame.columns
        if column.endswith("_amount")
    }


def _declared(wave: int = 2019) -> sources.DcRoute:
    return sources.declared_dc_route(wave)


def _balance(route: sources.DcRoute | None = None, **values: int) -> dict:
    frame = _items(**values)
    out = sources.employer_dc_balances(
        frame, route or _declared(), _widths(frame)
    )
    return out.iloc[0][list(sources.DC_BALANCE_COLUMNS)].to_dict()


@pytest.mark.parametrize(
    "plan_type, counted",
    [(5, True), (7, True), (1, False), (8, False), (9, False), (0, False)],
)
def test_current_job_account_or_combined_plan(plan_type, counted):
    out = _balance(head_current_type=plan_type, head_current_amount=40_000)
    assert out["employer_dc_current"] == (40_000 if counted else 0)
    assert out["employer_dc_off_route_items"] == (0 if counted else 1)


def test_combined_previous_plan_counts_its_both_items_once():
    out = _balance(
        head_prev1_type=7,
        head_prev1_combo_disposition=3,
        head_prev1_combo_amount=9_000,
        head_prev1_dc_disposition=3,
        head_prev1_dc_amount=9_000,
    )
    assert out["employer_dc_previous"] == 9_000
    assert out["employer_dc_duplicate_items"] == 1
    assert out["employer_dc_off_route_items"] == 0


@pytest.mark.parametrize("wave", sources.SUPPORT_WAVES)
@pytest.mark.parametrize("plan_type", [5, 1, 8, 9])
def test_declared_account_items_route(wave, plan_type):
    """Amendment 5 (ratified by d637): a previous plan's account items
    count for an account plan in every wave and, in 2013 only, for a
    formula or DK plan too (U1's inherited route); otherwise they are
    off-route, counted under that disposition and never zero-filled."""
    out = _balance(
        _declared(wave),
        wife_prev2_type=plan_type,
        wife_prev2_dc_disposition=3,
        wife_prev2_dc_amount=15_000,
    )
    counted = plan_type == 5 or (wave == 2013 and plan_type in (1, 8))
    assert out["employer_dc_previous"] == (15_000 if counted else 0)
    assert out["employer_dc_items"] == int(counted)
    assert out["employer_dc_off_route_items"] == int(not counted)


def _section_16a_fragment() -> dict:
    """Amendment 5's ``previous_routes`` fragment as section 16a prints it."""
    import json
    import re

    from populace_dynamics.uniform_cut_track_u2 import identity

    text = identity.SPECIFICATION_PATH.read_text(encoding="utf-8")
    section = text[text.index("## 16a. ") : text.index("## 16b. ")]
    lead = (
        "Proposed replacement for \N{SECTION SIGN}15 "
        "`income_concept.employer_dc.previous_routes`:"
    )
    after = section[section.index(lead) :]
    (block,) = re.findall(r"```json\n(.*?)\n```", after, re.S)[:1]
    return json.loads("{" + block + "}")["previous_routes"]


def test_declared_route_follows_the_ratified_amendment_5_fragment():
    """Max's d637 ruling ratified amendment 5 as written (section 16b),
    so the declared route is section 16a's ``previous_routes`` fragment:
    the same items per wave, with 2013 equal to section 15's generic
    route.  Section 15's block keeps draft 3's generic route until section
    20 step 5 materializes the final parameter block; this test then has
    to change with it."""
    from populace_dynamics.uniform_cut_track_u2 import rows

    fragment = _section_16a_fragment()
    assert fragment["both_items"] == ["both"]
    assert {
        int(wave): tuple(items)
        for wave, items in fragment["account_items_by_wave"].items()
    } == sources.DECLARED_PREVIOUS_ACCOUNT_ITEMS
    assert set(sources.DECLARED_PREVIOUS_ACCOUNT_ITEMS) == set(
        sources.SUPPORT_WAVES
    )
    assert fragment["refused_branches"] == {
        "2015": "P62ACKPT: P46=1 AND P52=1 AND P62AMT=DK/RF"
    }
    block = rows.specification_block()["income_concept"]["employer_dc"]
    assert block["previous_routes"] == {
        "both_items": ["both"],
        "account_items": ["account", "formula", "dk"],
    }
    assert tuple(block["previous_routes"]["account_items"]) == (
        sources.DECLARED_PREVIOUS_ACCOUNT_ITEMS[2013]
    )
    for wave in sources.SUPPORT_WAVES:
        route = sources.declared_dc_route(wave)
        assert route.previous_account_items == tuple(
            sources.DC_ITEM_PLAN_TYPES[item]
            for item in sources.DECLARED_PREVIOUS_ACCOUNT_ITEMS[wave]
        )
        assert route.current_account == (5, 7)
        assert route.previous_both == (7,)
    with pytest.raises(sources.U2SourceRefusal):
        sources.declared_dc_route(2011)


def test_rollover_into_an_ira_is_excluded_and_counted():
    out = _balance(
        head_prev1_type=5,
        head_prev1_dc_disposition=2,
        head_prev1_dc_amount=35_000,
    )
    assert out["employer_dc"] == 0
    assert out["employer_dc_ira_rollover_items"] == 1


@pytest.mark.parametrize("disposition", [1, 4, 7, 8, 9])
def test_other_dispositions_count_nothing(disposition):
    out = _balance(
        head_prev1_type=5,
        head_prev1_dc_disposition=disposition,
        head_prev1_dc_amount=12_000,
    )
    assert out["employer_dc"] == 0


def test_off_route_and_unreported_and_top_codes():
    dk = 10**8 - 2
    top = 10**9 - 3
    # 2013's route, where a DK-type plan's account items are on route.
    out = _balance(
        _declared(2013),
        head_prev1_type=9,
        head_prev1_dc_disposition=3,
        head_prev1_dc_amount=4_000,
        wife_prev1_type=8,
        wife_prev1_dc_disposition=3,
        wife_prev1_dc_amount=dk,
        head_current_type=5,
        head_current_amount=top,
    )
    assert out["employer_dc_off_route_items"] == 1
    assert out["employer_dc_unreported"] == 1
    assert out["employer_dc_top_coded"] == 1
    assert out["employer_dc"] == top


def test_2013_registry_route_equals_the_declared_route_and_u1_rule(
    committed_registries,
):
    gate = sources.SourceGate(sources.REGISTRY, committed_registries)
    route = sources.dc_route(2013, gate)
    assert set(route.current_account) == set(
        sources.DECLARED_DC_ROUTE_TYPES["current_account"]
    )
    assert set(route.previous_both) == {7}
    assert set(route.previous_account_items) == {5, 1, 8}
    assert route.previous_account_items == (
        sources.declared_dc_route(2013).previous_account_items
    )
    # The same items through U1's 2013 rule give the same balance.
    frame = _items(
        head_current_type=5,
        head_current_amount=30_000,
        head_prev1_type=7,
        head_prev1_combo_disposition=3,
        head_prev1_combo_amount=9_000,
        head_prev2_type=1,
        head_prev2_dc_disposition=3,
        head_prev2_dc_amount=15_000,
        wife_prev1_type=8,
        wife_prev1_dc_disposition=3,
        wife_prev1_dc_amount=12_000,
        wife_prev2_type=5,
        wife_prev2_dc_disposition=2,
        wife_prev2_dc_amount=35_000,
    )
    mine = sources.employer_dc_balances(frame, route, _widths(frame))
    theirs = u1_dc.employer_dc_balances(frame, 2013)
    for column in u1_dc.BALANCE_COLUMNS:
        if column == "employer_dc_off_route_items":
            continue
        assert int(mine[column].iloc[0]) == int(theirs[column].iloc[0]), column


@pytest.mark.parametrize("wave", [2015, 2017, 2019, 2021, 2023])
def test_later_wave_routes_refuse_under_the_registry_gate(
    wave, committed_registries
):
    gate = sources.SourceGate(sources.REGISTRY, committed_registries)
    with pytest.raises(sources.U2SourceRefusal):
        sources.dc_route(wave, gate)
    with pytest.raises(sources.U2SourceRefusal):
        sources.pension_field_specs(wave, gate)


def test_registry_documents_dc_only_checkpoints_from_2017(
    committed_registries,
):
    # The documentary finding the pending amendment 5 would adopt: the
    # 2017-2023 checkpoint routes DC-only plans (P46 = 5).  The
    # adjudication resolved it (disposition D) but its application waits
    # on Max's ruling, so the loader refuses the amendment entry and every
    # P64/P65 record that depends on it.  U2 records the finding and
    # refuses; it does not silently narrow or widen the route.
    from populace_dynamics.data import u2_source_registry as loader_api

    for wave in (2017, 2019, 2021, 2023):
        entry = committed_registries.entry(
            "pension", f"{wave}.route.formula_unknown_checkpoint"
        )
        assert list(entry["accepted_plan_types"]) == [5]
        amendment = committed_registries.entry(
            "pension", f"{wave}.route.inherited_route_amendment"
        )
        assert amendment["status"] == "RESOLVED"
        assert amendment["action"] == "refuse_pending_amendment_5_ruling"
        with pytest.raises(
            loader_api.SourceAdjudicationError,
            match="refuse_pending_amendment_5_ruling",
        ):
            loader_api.require_resolved(
                "pension", f"{wave}.route.inherited_route_amendment"
            )
        with pytest.raises(
            loader_api.SourceAdjudicationError, match="blocked"
        ):
            loader_api.require_resolved(
                "pension", f"{wave}.route.previous_dc_only"
            )
    declared = sources.SourceGate(
        sources.INVENTED_DECLARED, committed_registries
    )
    route = sources.dc_route(2019, declared)
    assert route.source == "section_15_declared_route_invented_only"
    assert "pension:2019.route.inherited_route_amendment" in (
        declared.would_refuse
    )


def test_invented_dc_frames_exercise_every_path(u2_inputs):
    totals = {column: 0 for column in sources.DC_BALANCE_COLUMNS}
    for frame in u2_inputs.employer_dc.values():
        for column in sources.DC_BALANCE_COLUMNS:
            totals[column] += int((frame[column] > 0).sum())
    for column in sources.DC_BALANCE_COLUMNS:
        assert totals[column] > 0, column


def test_dc_code_domains_equal_the_registry_routes(committed_registries):
    for wave in sources.SUPPORT_WAVES:
        route = committed_registries.entry(
            "pension", f"{wave}.route.current_job"
        )
        assert set(route["accepted_current_types"]) | set(
            route["rejected_current_types"]
        ) == set(sources.DC_CODE_DOMAINS["current_type"])
        rollovers = committed_registries.entry(
            "pension", f"{wave}.route.ira_rollovers"
        )
        assert {
            rollovers["counted_disposition"],
            rollovers["excluded_disposition"],
        } <= sources.DC_CODE_DOMAINS["disposition"]


@pytest.mark.parametrize(
    "route, field",
    [
        ("previous_combined", "counted_disposition"),
        ("previous_dc_only", "counted_disposition"),
        ("previous_combined", "excluded_ira_disposition"),
        ("previous_dc_only", "excluded_ira_disposition"),
        ("ira_rollovers", "counted_disposition"),
        ("ira_rollovers", "excluded_disposition"),
    ],
)
def test_route_disposition_codes_must_agree(
    route, field, committed_registries, monkeypatch
):
    """Review finding 9: the counted and IRA-rollover disposition codes
    appear on three route entries; a disagreement refuses rather than
    silently applying one entry's codes.  The committed 2013 entries
    agree (3 counted, 2 rolled over); each case changes one field of one
    entry, as a later registry edit could."""

    gate = sources.SourceGate(sources.REGISTRY, committed_registries)
    agreed = sources.dc_route(2013, gate)
    assert (agreed.counted_disposition, agreed.excluded_ira_disposition) == (
        3,
        2,
    )
    for name in ("previous_combined", "previous_dc_only"):
        entry = committed_registries.entry("pension", f"2013.route.{name}")
        assert entry["counted_disposition"] == 3
        assert entry["excluded_ira_disposition"] == 2
    original = sources.SourceGate.require

    def require(self, name, entry_id):
        entry = original(self, name, entry_id)
        if entry_id == f"2013.route.{route}":
            entry = {**entry, field: 7}
        return entry

    monkeypatch.setattr(sources.SourceGate, "require", require)
    with pytest.raises(sources.U2SourceRefusal, match="disagree"):
        sources.dc_route(
            2013, sources.SourceGate(sources.REGISTRY, committed_registries)
        )
