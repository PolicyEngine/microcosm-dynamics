"""The M1 specification's parameter block and the registered-run gate.

``docs/design/minimum_benefits_comparison.md`` (plan work item M1) carries
a machine-readable block in its section 19.  This module reads it, checks
it against the code (:mod:`.policy`), and refuses a registered real-data
run the block does not authorize.  A run is authorized only when:

* the block's ``status`` and ``version`` each name ``ratified`` as a word,
  with no negating word and no candidate, draft, not-merged, not-ratified
  or referee marker (A7's fail-closed test,
  ``estimates.cola_age_profile.specification_unratified_fields``, plus the
  ``referee`` marker exercise 3 added);
* it lists no decision awaiting Max;
* its ``blocked_by`` is empty: a block that still names a blocker (a
  missing capture, reader or registration) authorizes nothing, as Track
  U's entry point refuses one;
* it records a ruling under ``decisions`` for every field Max ruled on
  (cos d219's nine items, d279 and d280), each entry equal to the code's
  record of it (:data:`~.policy.MAX_RULINGS`), and the configuration
  follows each ruling;
* it agrees with the code (options, schedules, cuts, rows, cells, labels,
  the policy, the statistic and the uncertainty the tabulation computes).

``m1-draft-2`` records Max's rulings and fails the first test: it awaits an
independent check of the referee's changes, then ratification by merge.
Its ``blocked_by`` also still lists the unbuilt PSID readers (M3-M5).
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from populace_dynamics.min_benefit_track_m import OUTPUT_LABELS
from populace_dynamics.min_benefit_track_m.policy import (
    DECISION_RECORD,
    HEADLINE_CELL,
    MAX_RULINGS,
    OPTIONS,
    REGISTERED_ROWS,
    SPECIFICATION_ID,
    TABLE6_OPTIONS,
    TABLE6_ROWS,
    TrackMPolicy,
    fixed_decision_value,
)

__all__ = [
    "M1_SPECIFICATION_PATH",
    "M1_BLOCK_SECTION",
    "check_specification_for_registered_run",
    "d219_decision_fields",
    "decision_value",
    "expected_decisions",
    "m1_parameter_block",
    "ruled_fields",
    "specification_code_check",
    "unratified_fields",
]

_ROOT = Path(__file__).resolve().parents[3]
M1_SPECIFICATION_PATH = (
    _ROOT / "docs" / "design" / "minimum_benefits_comparison.md"
)
M1_BLOCK_SECTION = "## 19. Machine-readable parameter block"
#: Markers beyond A7's that keep a status or version from counting as
#: ratified (exercise 3 added "referee").
_EXTRA_UNRATIFIED_MARKERS = ("referee",)


def m1_parameter_block(path: Path = M1_SPECIFICATION_PATH) -> dict[str, Any]:
    """The JSON block of the M1 specification's section 19."""

    text = Path(path).read_text(encoding="utf-8")
    match = re.search(
        re.escape(M1_BLOCK_SECTION) + r".*?```json\n(.*?)\n```",
        text,
        flags=re.S,
    )
    if match is None:
        raise ValueError(f"no section 19 JSON block in {path}")
    return json.loads(match.group(1))


def unratified_fields(block: Mapping[str, Any]) -> list[str]:
    """Header fields that keep the block from counting as ratified."""

    from populace_dynamics.estimates import cola_age_profile

    fields = list(cola_age_profile.specification_unratified_fields(block))
    for name in ("status", "version"):
        value = block.get(name)
        if name in fields or not isinstance(value, str):
            continue
        normalized = "_".join(
            word for word in re.split(r"[^0-9a-z]+", value.lower()) if word
        )
        if any(mark in normalized for mark in _EXTRA_UNRATIFIED_MARKERS):
            fields.append(name)
    return fields


def ruled_fields() -> tuple[str, ...]:
    """Every field Max ruled on (d219, d279, d280), in the code's order."""

    return tuple(MAX_RULINGS)


def d219_decision_fields() -> tuple[str, ...]:
    """The fields the nine d219 items govern, in item order."""

    return tuple(
        name
        for name, entry in sorted(
            MAX_RULINGS.items(), key=lambda item: item[1]["item"] or 0
        )
        if entry["decision_record"] == DECISION_RECORD
    )


def decision_value(policy: TrackMPolicy, name: str) -> Any:
    """The configuration's value of ruled field ``name``.

    A field of :class:`TrackMPolicy` reads the policy; a process decision
    (target cells, claim class, module placement, acceptance rule,
    ratification, the threshold download) reads the code's fixed value,
    which only a code change can alter.
    """

    if name not in MAX_RULINGS:
        raise KeyError(f"{name} is not a field Max ruled on")
    if hasattr(policy, name):
        return getattr(policy, name)
    return fixed_decision_value(name)


def expected_decisions() -> dict[str, Any]:
    """The block's ``decisions`` object as the code records the rulings."""

    return {
        "ruled_by": "Max",
        **json.loads(json.dumps(MAX_RULINGS)),
    }


def _expected_options() -> dict[str, Any]:
    out = {}
    for number, option in OPTIONS.items():
        entry = option.as_dict()
        entry["schedule_points"] = (
            None
            if option.schedule is None
            else option.schedule.as_dict()["points"]
        )
        out[str(number)] = entry
    return out


def specification_code_check(
    block: Mapping[str, Any], policy: TrackMPolicy | None = None
) -> dict[str, Any]:
    """Compare the block with the code; ``consistent`` when all agree.

    ``statistic`` and ``uncertainty`` are held to the tabulation's
    :data:`~.tabulation.STATISTIC` and :data:`~.tabulation.UNCERTAINTY`
    (imported here, not at module level, so reading the block loads no
    tabulation code).
    """

    from populace_dynamics.min_benefit_track_m import tabulation

    policy = policy or TrackMPolicy()
    expected = {
        "specification": SPECIFICATION_ID,
        "options": _expected_options(),
        "cells": {
            "options": list(TABLE6_OPTIONS),
            "rows": list(TABLE6_ROWS),
            "headline": {"option": HEADLINE_CELL[0], "row": HEADLINE_CELL[1]},
        },
        "policy": policy.as_dict(),
        "rows": {
            name: dict(change) for name, change in REGISTERED_ROWS.items()
        },
        "labels": list(OUTPUT_LABELS),
        "decisions": expected_decisions(),
        "statistic": tabulation.statistic_block(),
        "uncertainty": tabulation.uncertainty_block(),
    }
    mismatches = [
        key for key, value in expected.items() if block.get(key) != value
    ]
    awaiting = block.get("decisions_awaiting_max") or {}
    unknown = sorted(set(awaiting) - set(ruled_fields()))
    if unknown:
        mismatches.append(f"decisions_awaiting_max:{unknown}")
    return {"consistent": not mismatches, "mismatches": mismatches}


def check_specification_for_registered_run(
    block: Mapping[str, Any], policy: TrackMPolicy | None = None
) -> None:
    """Refuse a real-data run the M1 block does not authorize."""

    policy = policy or TrackMPolicy()
    for name in unratified_fields(block):
        raise ValueError(
            f"the M1 specification {name} is {block.get(name)!r}: it "
            "authorizes no real-data run until Max ratifies it by merging "
            "(d219 item 9), and the ratified text must say so in its "
            "section 19 block"
        )
    awaiting = block.get("decisions_awaiting_max")
    if awaiting:
        raise ValueError(
            "the M1 specification still lists decisions awaiting Max "
            f"({sorted(awaiting)}): no real-data statistic before he rules"
        )
    if "blocked_by" not in block:
        raise ValueError(
            "the M1 specification block has no blocked_by list: a "
            "registered run needs it present and empty"
        )
    blocked = block["blocked_by"]
    if not isinstance(blocked, list) or blocked:
        raise ValueError(
            f"the M1 specification is still blocked by {blocked!r}: no "
            "real-data run while its block names a blocker"
        )
    rulings = block.get("decisions") or {}
    unruled = [
        name
        for name in ruled_fields()
        if not isinstance(rulings.get(name), Mapping)
        or "ruling" not in rulings[name]
    ]
    if unruled:
        raise ValueError(
            f"the M1 specification records no ruling by Max for {unruled} "
            f"(decision records {DECISION_RECORD}, d279, d280): no "
            "real-data statistic before he rules"
        )
    recorded = json.loads(json.dumps(dict(rulings)))
    recorded.pop("ruled_by", None)
    expected = expected_decisions()
    expected.pop("ruled_by")
    if recorded != expected:
        differing = sorted(
            name
            for name in set(recorded) | set(expected)
            if recorded.get(name) != expected.get(name)
        )
        raise ValueError(
            f"the M1 specification's rulings on {differing} differ from the "
            "code's record of Max's rulings (policy.MAX_RULINGS)"
        )
    departures = [
        name
        for name in ruled_fields()
        if decision_value(policy, name) != rulings[name]["ruling"]
    ]
    if departures:
        raise ValueError(
            f"the configuration departs from Max's rulings on {departures}; "
            "a registered run follows every ruling"
        )
    check = specification_code_check(block, policy)
    if not check["consistent"]:
        raise ValueError(
            "the M1 specification block and the code or configuration "
            f"differ: {check['mismatches']}"
        )
