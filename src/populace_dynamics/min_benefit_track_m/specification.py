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
* it lists no decision awaiting Max (cos decision d219);
* it records his ruling on every d219 field under ``decisions``
  (``{field: {"ruling": value, ...}}``) and the configuration follows each
  ruling;
* it agrees with the code (options, schedules, cuts, rows, cells, labels
  and the policy).

The committed draft (``m1-draft-1``) fails the first test.
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
    OPTIONS,
    REGISTERED_ROWS,
    SPECIFICATION_ID,
    TABLE6_OPTIONS,
    TABLE6_ROWS,
    TrackMPolicy,
    pending_decisions,
)

__all__ = [
    "M1_SPECIFICATION_PATH",
    "M1_BLOCK_SECTION",
    "check_specification_for_registered_run",
    "d219_decision_fields",
    "decision_value",
    "m1_parameter_block",
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


def d219_decision_fields() -> tuple[str, ...]:
    """The fields the nine d219 items govern, in item order."""

    return tuple(
        item.field
        for item in pending_decisions()
        if item.card_item is not None
    )


def decision_value(policy: TrackMPolicy, name: str) -> Any:
    """The configuration's value of d219 field ``name``.

    A field of :class:`TrackMPolicy` reads the policy; a process item
    (target cells, claim class, acceptance rule, ratification) reads the
    code's fixed value, which only a code change can alter.
    """

    if name not in d219_decision_fields():
        raise KeyError(f"{name} is not a d219 decision field")
    if hasattr(policy, name):
        return getattr(policy, name)
    return {
        item.field: item.default
        for item in pending_decisions()
        if item.card_item is not None
    }[name]


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
    """Compare the block with the code; ``consistent`` when all agree."""

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
    }
    mismatches = [
        key for key, value in expected.items() if block.get(key) != value
    ]
    awaiting = block.get("decisions_awaiting_max") or {}
    unknown = sorted(set(awaiting) - set(d219_decision_fields()))
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
            f"({sorted(awaiting)}; decision record {DECISION_RECORD}): no "
            "real-data statistic before he rules"
        )
    rulings = block.get("decisions") or {}
    unruled = [
        name
        for name in d219_decision_fields()
        if not isinstance(rulings.get(name), Mapping)
        or "ruling" not in rulings[name]
    ]
    if unruled:
        raise ValueError(
            f"the M1 specification records no ruling by Max for {unruled} "
            f"(decision record {DECISION_RECORD}): no real-data statistic "
            "before he rules"
        )
    departures = [
        name
        for name in d219_decision_fields()
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
