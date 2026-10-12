"""Documentary U2 mappings; this module never reads survey records.

Source status describes documentary adjudication, not independent approval.
The resolver refuses open questions and explicit application dependencies.
Nothing here builds a cohort, evaluates income, or extends a U1 registry.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

U2_SOURCE_WAVES = (2013, 2015, 2017, 2019, 2021, 2023)
REGISTRY_NAMES = (
    "income",
    "wealth",
    "individual",
    "pension",
    "roles",
    "support",
    "weights",
    "design",
)
REGISTRY_DIRECTORY = (
    Path(__file__).resolve().parents[3] / "data" / "external" / "track_u2"
)
_D1090 = {
    "decision": "d1090",
    "date": "2026-10-10",
    "specification_section": "16c",
}
#: The two family-unit exclusions Max ratified on 2026-10-10 (d1090;
#: specification section 16c), by named disposition, each with its exact
#: scope: the role entries that carry it, its recorded-sex condition, the
#: income role and action it leaves and the ruling it records.  Blocker
#: B1 (section 16a option 1d-2) is a 2015 code-20 person recorded male;
#: blocker B2 (option 1e-1) is codes 90 and 92 in 2019-2023.
RATIFIED_EXCLUSIONS: dict[str, dict[str, Any]] = {
    "male code 20 in 2015 family unit": {
        "entries": ("2015.relationship.20",),
        "condition": {"sex": 1},
        "income_role": "spouse",
        "action": "documented_rule_with_family_unit_exclusion",
        "ruling": {
            **_D1090,
            "option": "1d-2",
            "amends_draft_3_lines": [160],
        },
    },
    "uncooperative spouse or partner in family unit": {
        "entries": tuple(
            f"{wave}.relationship.{code}"
            for wave in (2019, 2021, 2023)
            for code in (90, 92)
        ),
        "condition": None,
        "income_role": "excluded",
        "action": "exclude_family_unit_per_d1090",
        "ruling": {
            **_D1090,
            "option": "1e-1",
            "amends_draft_3_lines": [152, 154, 158],
            "amended_waves": [2019, 2021, 2023],
        },
    },
}
#: The named dispositions; a role entry carries one as
#: ``family_unit_exclusion``.
FAMILY_UNIT_DISPOSITIONS = tuple(RATIFIED_EXCLUSIONS)
#: The role entry each ratified exclusion belongs to.
_EXCLUSION_OF_ENTRY = {
    entry: name
    for name, scope in RATIFIED_EXCLUSIONS.items()
    for entry in scope["entries"]
}
_D637 = {
    "decision": "d637",
    "date": "2026-09-30",
    "specification_section": "16b",
}
_LATER_WAVES = (2015, 2017, 2019, 2021, 2023)
#: Max confirmed on 2026-10-12 that d637 ratified amendment 1's parts
#: 1a-1c as written (d745; specification section 16b).
_D745 = {"confirmed_by": "d745", "confirmed_on": "2026-10-12"}
#: The u2-draft-4 amendments Max ratified on 2026-09-30 (d637;
#: specification section 16b) that a registry commit has applied, each
#: with its exact scope: the registry and entries it rules, the ruling
#: they record, the adjudication disposition they keep, the gate fields
#: it fixes (``fields``, exact values), the fields it removes
#: (``absent``), the fields that must hold its text (``required``,
#: nonempty), the fixed values that only its entries may carry
#: (``markers``) and, for amendment 5, the route entries the builder
#: reads that it governs (``governs``: exact fields, and fields that must
#: be absent).  An entry that records a d637 ruling must be in its
#: amendment's scope and hold those values, and every entry in a scope
#: must record the ruling.  Each registry commit adds its amendment here
#: (section 16a, "Registry effect of the rulings").
RATIFIED_AMENDMENTS: dict[str, dict[str, Any]] = {
    "1a": {
        "registry": "roles",
        "entries": (
            "2015.relationship.90",
            "2017.relationship.90",
            "2017.relationship.92",
        ),
        "ruling": {**_D637, "amendment": "1a", **_D745},
        "disposition": "D",
        "fields": {
            "status": "RESOLVED",
            "action": "documented_rule",
            "income_role": "ofum",
            "spouse_slot": False,
        },
        "absent": (
            "refusal",
            "question",
            "blocking_dependencies",
            "family_unit_exclusion",
        ),
        "required": ("resolution", "ruling_effect", "completeness_disclosure"),
        "markers": ("completeness_disclosure",),
    },
    "2": {
        "registry": "income",
        "entries": tuple(
            f"income.{wave}.{route}"
            for wave in _LATER_WAVES
            for route in ("wife_age", "wife_sex")
        ),
        "ruling": {**_D637, "amendment": "2"},
        "disposition": "A",
        "fields": {"status": "RESOLVED", "usage": "slot_metadata_only"},
        "absent": ("action", "blocking_dependencies", "question"),
        "required": ("use_restriction", "resolution", "superseded_question"),
        "markers": ("usage",),
    },
    "3": {
        "registry": "income",
        "entries": tuple(
            f"income.{wave}.wife_retirement_annuities"
            for wave in (2013, *_LATER_WAVES)
        ),
        "ruling": {**_D637, "amendment": "3"},
        "disposition": "A",
        "fields": {
            "status": "RESOLVED",
            "kind": "historical_route_crosswalk",
            "usage": (
                "Documentary crosswalk only; not an executable derived input"
            ),
            "use_restriction": (
                "Non-executable metadata (u2-draft-4 amendment 3): no U2 "
                "input or row reads this crosswalk, and no scalar historical "
                "equivalence is inferred from it."
            ),
        },
        "absent": ("action", "question", "variable"),
        "required": ("resolution", "superseded_question", "variables"),
        "markers": ("use_restriction",),
    },
    "4": {
        "registry": "wealth",
        "entries": tuple(
            f"wealth.{wave}.{route}"
            for wave in (2013, *_LATER_WAVES)
            for route in ("wealth2_acc", "checking_saving_acc")
            if route == "wealth2_acc" or wave < 2019
        ),
        "ruling": {**_D637, "amendment": "4"},
        "disposition": "D",
        "fields": {
            "status": "RESOLVED",
            "use_restriction": (
                "Imputation diagnostics only; the correction never changes "
                "amounts or sample inclusion (u2-draft-4 amendment 4, "
                "ratified by Max on 2026-09-30: d637, specification section "
                "16b)."
            ),
        },
        "absent": ("action", "blocking_dependencies", "question"),
        "required": ("resolution", "source_wording_conflict"),
        "markers": ("use_restriction",),
        # The corrected targets of section 16a's table (amendment 4).
        "targets": {
            "wealth.2013.wealth2_acc": "ER58211",
            "wealth.2013.checking_saving_acc": "ER58161",
            "wealth.2015.wealth2_acc": "ER65408",
            "wealth.2015.checking_saving_acc": "ER65358",
            "wealth.2017.wealth2_acc": "ER71485",
            "wealth.2017.checking_saving_acc": "ER71435",
            "wealth.2019.wealth2_acc": "ER77511",
            "wealth.2021.wealth2_acc": "ER81838",
            "wealth.2023.wealth2_acc": "ER85692",
        },
    },
    "5b": {
        "registry": "pension",
        "entries": ("2015.route.formula_unknown_checkpoint",),
        "ruling": {
            **_D637,
            "amendment": "5b",
            "replaces_draft_3_lines": [1173, 1174, 1175, 1176],
        },
        "disposition": "A",
        "fields": {
            "status": "RESOLVED",
            "accepted_plan_types": [5],
            "rejected_plan_types": [1, 7, 8, 9],
            "refused_branch": "P62ACKPT: P46=1 AND P52=1 AND P62AMT=DK/RF",
            "off_route_disposition": "off_route",
        },
        "absent": (
            "action",
            "refusal",
            "question",
            "blocking_dependencies",
            "accepted_conditional_types",
        ),
        "required": (
            "condition",
            "resolution",
            "superseded_question",
            "superseded_refusal",
        ),
        "markers": ("refused_branch", "off_route_disposition"),
        "governs": {
            "2015.route.previous_combined": ({"accepted_plan_types": [7]}, ()),
            "2015.route.previous_dc_only": ({"accepted_plan_types": [5]}, ()),
        },
    },
    "5a": {
        "registry": "pension",
        "entries": tuple(
            f"{wave}.route.inherited_route_amendment"
            for wave in _LATER_WAVES[1:]
        ),
        "ruling": {
            **_D637,
            "amendment": "5a",
            "replaces_draft_3_lines": [1173, 1174, 1175, 1176],
        },
        "disposition": "D",
        "fields": {"status": "RESOLVED"},
        "absent": ("action", "refusal", "question", "blocking_dependencies"),
        "required": (
            "required_amendment",
            "resolution",
            "ruling_effect",
            "superseded_refusal",
        ),
        "markers": (),
        # The route dc_route reads for each wave: the DC-only checkpoint,
        # the combined plan's items and the DC-only plan's (5a).
        "governs": {
            **{
                f"{wave}.route.formula_unknown_checkpoint": (
                    {
                        "status": "RESOLVED",
                        "accepted_plan_types": [5],
                        "rejected_plan_types": [1, 7, 8, 9],
                    },
                    ("accepted_conditional_types",),
                )
                for wave in _LATER_WAVES[1:]
            },
            **{
                f"{wave}.route.{route}": ({"accepted_plan_types": types}, ())
                for wave in _LATER_WAVES[1:]
                for route, types in (
                    ("previous_combined", [7]),
                    ("previous_dc_only", [5]),
                )
            },
        },
    },
    "6": {
        "registry": "weights",
        "entries": ("2017.cross_section_weight",),
        "ruling": {
            **_D637,
            "amendment": "6",
            "option": "1",
            "amends_draft_3_lines": [134],
        },
        "disposition": "A",
        "fields": {
            "status": "RESOLVED",
            "variable": "ER34651",
            "selection": (
                "positive recorded cross-sectional weight; do not infer a "
                "domain from empirical ranges printed in codebook"
            ),
            "purpose": (
                "Use reporting-wave individual cross-sectional weight times "
                "documentary plan multiplier. No cohort reweighting or "
                "immigrant exclusion."
            ),
            # Option 1's disclosure, exactly (section 16a amendment 6).
            "registration_disclosure": {
                "documented": [
                    (
                        "the weight's identity: ER34651, CORE/IMM INDIVIDUAL "
                        "CROSS-SECTION WT 17, the 2017 individual weight in "
                        "Table A3 of PSID's April 2021 and June 2026 "
                        "cross-sectional weight reports"
                    ),
                    (
                        "the 2017 population control: the ACS one-year PUMS "
                        "population total, with the CPS not used, and its two "
                        "named exclusions, individuals in donut-hole families "
                        "and post-1997 immigrants living in group quarters"
                    ),
                    (
                        "the calibration-variable selection approach PSID has "
                        "used since 2017"
                    ),
                    (
                        "some calibration controls: gender, race, region and "
                        "age in 10-year groups, in comparisons that include "
                        "2017 (April 2021 report)"
                    ),
                    (
                        "how the 2017 Immigrant sample's base weights were "
                        "formed and integrated with the core sample, for the "
                        "2019 weights (the 2019 longitudinal-weights report)"
                    ),
                ],
                "not_published": [
                    (
                        "which starting weights the revised 2017 weight used "
                        "for the 2017 Immigrant sample, whose 2017 "
                        "longitudinal family weight is zero"
                    ),
                    (
                        "how that sample's joint families were integrated "
                        "with the core sample in the revised 2017 weight"
                    ),
                    (
                        "the complete 2017 raking specification: every "
                        "calibration variable and interaction, the collapsed "
                        "categories and the trimming"
                    ),
                ],
                "coverage_bound": (
                    "The control's documented exclusions bound coverage: the "
                    "donut-hole group includes post-1997 immigrants who "
                    "co-reside with individuals born in 1960-1971, with no "
                    "limit on their own birth year, and post-1997 immigrants "
                    "in group quarters are excluded too (June 2026 report, "
                    "Table A2 note)."
                ),
            },
        },
        "absent": ("action", "refusal", "question", "blocking_dependencies"),
        "required": (
            "resolution",
            "registration_disclosure",
            "superseded_question",
        ),
        "markers": ("registration_disclosure",),
    },
}
#: The rulings a registry entry may record.
_RULED_DECISIONS = ("d637", "d1090")
#: The d637 amendment each ruled entry belongs to, by (registry, id).
_AMENDMENT_OF_ENTRY = {
    (scope["registry"], entry): name
    for name, scope in RATIFIED_AMENDMENTS.items()
    for entry in scope["entries"]
}


class SourceAdjudicationError(ValueError):
    """A documentary mapping is malformed or still requires adjudication."""


def _fields(entry: dict[str, Any], fields: dict[str, type]) -> None:
    for field, expected in fields.items():
        value = entry.get(field)
        if type(value) is not expected or (
            expected is str and not value.strip()
        ):
            raise SourceAdjudicationError(
                f"Missing or invalid {field} for {entry.get('id', 'entry')}"
            )


def _list(entry: dict[str, Any], field: str, item_type: type) -> None:
    _fields(entry, {field: list})
    values = entry[field]
    if not values or any(
        type(value) is not item_type
        or (item_type is str and not value.strip())
        for value in values
    ):
        raise SourceAdjudicationError(f"Invalid {field} for {entry['id']}")
    if len(values) != len(set(values)):
        raise SourceAdjudicationError(f"Duplicate {field} for {entry['id']}")


def _layout(entry: dict[str, Any], field: str | None = None) -> None:
    if field is None:
        layout = entry
        start, end = "position_start", "position_end"
    else:
        _fields(entry, {field: dict})
        layout = entry[field]
        start, end = "start", "end"
    _fields(layout, {start: int, end: int, "width": int})
    if layout[start] < 1 or layout[end] < layout[start]:
        raise SourceAdjudicationError(
            f"Invalid layout coordinates for {entry['id']}"
        )
    if layout["width"] != layout[end] - layout[start] + 1:
        raise SourceAdjudicationError(
            f"Inconsistent layout width for {entry['id']}"
        )


def _ruling(entry: dict[str, Any]) -> None:
    """A recorded ruling names its decision, date and specification part."""
    _fields(entry, {"ruling": dict})
    ruling = {**entry["ruling"], "id": entry["id"]}
    _fields(
        ruling, {"decision": str, "date": str, "specification_section": str}
    )
    if ruling["decision"] not in _RULED_DECISIONS:
        raise SourceAdjudicationError(
            f"Unknown ruling {ruling['decision']!r} for {entry['id']}"
        )


def _same(first: Any, second: Any) -> bool:
    """Equal as JSON, so ``True`` never stands in for ``1``."""
    return json.dumps(first, sort_keys=True) == json.dumps(
        second, sort_keys=True
    )


def _ratified_amendment(entry: dict[str, Any], name: str) -> None:
    """A d637 ruling, held to its amendment's exact scope
    (:data:`RATIFIED_AMENDMENTS`)."""
    ruling = entry["ruling"]
    amendment = ruling.get("amendment")
    scope = RATIFIED_AMENDMENTS.get(amendment)
    if scope is None:
        raise SourceAdjudicationError(
            f"Unratified d637 amendment for {entry['id']}"
        )
    if _AMENDMENT_OF_ENTRY.get((name, entry["id"])) != amendment:
        raise SourceAdjudicationError(
            f"d637 amendment {amendment} is not ratified for "
            f"{name}:{entry['id']}"
        )
    if not _same(ruling, scope["ruling"]):
        raise SourceAdjudicationError(
            f"ruling is not the ratified one for {entry['id']}"
        )
    for field, value in scope["fields"].items():
        if field not in entry or not _same(entry[field], value):
            raise SourceAdjudicationError(
                f"{field} is not the ratified one for {entry['id']}"
            )
    for field in scope["absent"]:
        if field in entry:
            raise SourceAdjudicationError(
                f"{field} remains after the d637 ruling for {entry['id']}"
            )
    for field in scope["required"]:
        if not entry.get(field):
            raise SourceAdjudicationError(
                f"d637 amendment {amendment} needs {field} for {entry['id']}"
            )
    if entry.get("blocking_dependencies"):
        raise SourceAdjudicationError(
            f"A d637 ruling applies only unblocked, for {entry['id']}"
        )
    record = entry.get("adjudication")
    if (
        not isinstance(record, dict)
        or record.get("disposition") != scope["disposition"]
        or not _same(record.get("amendment"), int(amendment[0]))
    ):
        raise SourceAdjudicationError(
            f"Adjudication record is not amendment {amendment}'s "
            f"{scope['disposition']} for {entry['id']}"
        )
    target = scope.get("targets", {}).get(entry["id"])
    if "targets" in scope:
        _fields(entry, {"source_wording_conflict": dict})
    if "targets" in scope and not (
        entry.get("accuracy_for_variable") == target
        and entry["source_wording_conflict"].get(
            "resolved_accuracy_for_variable"
        )
        == target
    ):
        raise SourceAdjudicationError(
            f"Corrected target is not the ratified one for {entry['id']}"
        )


def _family_unit_exclusion(entry: dict[str, Any]) -> None:
    """A ratified exclusion, held to its exact scope: the entry it may
    attach to, its condition, the income role and action it leaves and
    the ruling that made it (:data:`RATIFIED_EXCLUSIONS`)."""
    _fields(entry, {"family_unit_exclusion": dict})
    exclusion = {**entry["family_unit_exclusion"], "id": entry["id"]}
    _fields(exclusion, {"disposition": str})
    scope = RATIFIED_EXCLUSIONS.get(exclusion["disposition"])
    if scope is None:
        raise SourceAdjudicationError(
            f"Unratified family-unit exclusion for {entry['id']}"
        )
    if set(exclusion) - {"disposition", "condition", "id"}:
        raise SourceAdjudicationError(
            f"Unknown exclusion field for {entry['id']}"
        )
    if entry["id"] not in scope["entries"]:
        raise SourceAdjudicationError(
            f"{exclusion['disposition']!r} is not ratified for {entry['id']}"
        )
    # The builder keys a rule on the entry's wave and code and drops an
    # absent code's rule, so the exclusion must sit on a present entry
    # whose own wave and code are its id's (checked for every role entry
    # in ``_entry_payload``).
    if entry["present"] is not True:
        raise SourceAdjudicationError(
            f"A family-unit exclusion needs a present code for {entry['id']}"
        )
    condition = exclusion.get("condition")
    if condition != scope["condition"] or (
        condition is not None and type(condition["sex"]) is not int
    ):
        raise SourceAdjudicationError(
            f"Exclusion condition is not the ratified one for {entry['id']}"
        )
    for field in ("income_role", "action", "ruling"):
        if entry.get(field) != scope[field]:
            raise SourceAdjudicationError(
                f"{field} is not the ratified one for {entry['id']}"
            )


def _variable(entry: dict[str, Any], layout: str) -> None:
    _fields(entry, {"variable": str, "label": str, "concept": str})
    _layout(entry, layout)


def _identity(entry: dict[str, Any]) -> None:
    if "identity" not in entry:
        return
    _fields(entry, {"identity": dict})
    identity = {**entry["identity"], "id": entry["id"]}
    _fields(identity, {"operation": str})
    operation = identity["operation"]
    if operation == "sum":
        _list(identity, "terms", str)
    elif operation == "asset_minus_separately_documented_debt":
        _fields(identity, {"asset": str, "debt": str})
        if identity["asset"] == identity["debt"]:
            raise SourceAdjudicationError(
                f"Asset equals debt for {entry['id']}"
            )
    elif operation == "sum_assets_minus_sum_debts":
        for field in ("assets", "debts"):
            _list(identity, field, str)
        _fields(identity, {"excluded_home_equity": str})
        if set(identity["assets"]) & set(identity["debts"]):
            raise SourceAdjudicationError(
                f"Overlapping asset/debt for {entry['id']}"
            )
        if (
            identity["excluded_home_equity"]
            in identity["assets"] + identity["debts"]
        ):
            raise SourceAdjudicationError(
                f"Home equity included for {entry['id']}"
            )
    else:
        raise SourceAdjudicationError(
            f"Unknown identity operation for {entry['id']}"
        )


def _pension_route(entry: dict[str, Any]) -> None:
    _fields(entry, {"finding": str})
    suffix = entry["id"].split(".route.")[-1]
    fields = {
        "current_job": {
            "accepted_current_types": list,
            "rejected_current_types": list,
            "slots": list,
        },
        "previous_combined": {
            "accepted_plan_types": list,
            "counted_disposition": int,
            "excluded_ira_disposition": int,
            "previous_plans": list,
        },
        "previous_dc_only": {
            "accepted_plan_types": list,
            "counted_disposition": int,
            "excluded_ira_disposition": int,
            "previous_plans": list,
        },
        "checkpoint_documentation": {},
        "formula_unknown_checkpoint": {},
        "inherited_route_amendment": {"required_amendment": str},
        "ira_rollovers": {
            "counted_disposition": int,
            "excluded_disposition": int,
        },
        "duplicate_and_off_route": {
            "duplicate_exclusion": str,
            "requires_resolved_route": str,
        },
        "amounts_brackets_top_codes": {
            "brackets_used": bool,
            "codebook_variable_ids": list,
            "top_code": str,
            "unreported_amount": str,
        },
        "previous_plan_universe": {
            "maximum_previous_plans": int,
            "slots": list,
        },
        "respondent_slots": {
            "family_list_gate": dict,
            "requires_role_registry": bool,
        },
        "other_current_plan": {"included": bool},
        "plan_type_nonresponse_release_note": {},
    }
    if suffix not in fields:
        raise SourceAdjudicationError(
            f"Unknown pension route for {entry['id']}"
        )
    _fields(entry, fields[suffix])
    for field in (
        "accepted_current_types",
        "rejected_current_types",
        "accepted_plan_types",
        "rejected_plan_types",
        "accepted_conditional_types",
        "previous_plans",
    ):
        if field in entry:
            _list(entry, field, int)
    for field in ("slots", "codebook_variable_ids"):
        if field in entry:
            _list(entry, field, str)
    if (
        suffix == "formula_unknown_checkpoint"
        and entry["status"] == "RESOLVED"
    ):
        _fields(entry, {"condition": str})
        if not any(
            field in entry
            for field in ("accepted_plan_types", "accepted_conditional_types")
        ):
            raise SourceAdjudicationError(
                f"Missing accepted plan types for {entry['id']}"
            )


def _entry_payload(entry: dict[str, Any], name: str) -> None:
    """Validate documentary shapes, never empirical amounts or frequencies."""
    if name in ("income", "wealth"):
        _fields(
            entry,
            {
                "route": str,
                "label": str,
                "codebook_text": str,
                "documented_domain": str,
            },
        )
        if entry.get("kind") == "historical_route_crosswalk":
            _list(entry, "variables", str)
            _fields(entry, {"usage": str})
            if "variable" in entry:
                raise SourceAdjudicationError(
                    f"A crosswalk declares no scalar variable: {entry['id']}"
                )
        elif "kind" not in entry or entry["kind"] == "variable":
            _fields(
                entry,
                {
                    "variable": str,
                    "decimals": int,
                    "reference_year": int,
                    "negative_domain_documented": bool,
                    "all_missing_assigned_statement_present": bool,
                },
            )
            _layout(entry)
            if not 0 <= entry["decimals"] < entry["width"]:
                raise SourceAdjudicationError(
                    f"Invalid decimals for {entry['id']}"
                )
        else:
            raise SourceAdjudicationError(
                f"Unknown mapping kind for {entry['id']}"
            )
        _identity(entry)
    elif name == "pension":
        _fields(entry, {"kind": str})
        if entry["kind"] == "variable":
            _variable(entry, "position")
            _fields(
                entry,
                {
                    "person_slot": str,
                    "numeric_format": str,
                    "codebook_documentation": str,
                },
            )
        elif entry["kind"] == "route":
            _pension_route(entry)
        else:
            raise SourceAdjudicationError(
                f"Unknown pension kind for {entry['id']}"
            )
    elif name in ("individual", "weights", "design"):
        if name == "weights" and entry["id"] == "2023.weight_document_staging":
            _fields(entry, {"finding": str})
            return
        _variable(entry, "layout")
        _fields(entry, {"codes": dict, "codebook_text": str})
        if name == "weights":
            _fields(
                entry, {"construction": str, "selection": str, "purpose": str}
            )
        if name == "design":
            _fields(entry, {"rule": str})
            _list(entry, "valid_codes", int)
    elif name == "roles":
        _fields(
            entry,
            {
                "variable": str,
                "code": int,
                "action": str,
                "present": bool,
                "administrative_birth_support": bool,
                "legal_spouse_annuity": bool,
                "marital_resolution": bool,
            },
        )
        # The role rules are keyed on (wave, code); the id must name the
        # same pair, or a rule could be moved under an unchanged id.
        if entry["id"] != f"{entry['wave']}.relationship.{entry['code']}":
            raise SourceAdjudicationError(
                f"Role id does not name its wave and code: {entry['id']}"
            )
        if entry["present"]:
            _fields(entry, {"label": str, "spouse_slot": bool})
        elif "label" not in entry or entry["label"] is not None:
            raise SourceAdjudicationError(
                f"Absent role needs null label for {entry['id']}"
            )
        if entry["status"] == "RESOLVED" and entry["present"]:
            _fields(entry, {"income_role": str})
        if "family_unit_exclusion" in entry:
            _family_unit_exclusion(entry)
        elif entry.get("income_role") == "excluded":
            raise SourceAdjudicationError(
                f"Excluded income role without an exclusion for {entry['id']}"
            )
        elif entry["id"] in _EXCLUSION_OF_ENTRY and not entry.get(
            "action", ""
        ).startswith("refuse"):
            # A ruled entry that applies must carry its exclusion; only a
            # refusal (the pre-ruling state) may go without it.
            raise SourceAdjudicationError(
                f"{entry['id']} applies without its ratified exclusion "
                f"{_EXCLUSION_OF_ENTRY[entry['id']]!r}"
            )
    elif name == "support":
        if entry["id"] == "common.birth_derivation":
            _fields(entry, {"rule": str})
        else:
            _fields(
                entry,
                {
                    "birth_year": int,
                    "income_year": int,
                    "age": int,
                    "primary_observation": bool,
                    "support": str,
                },
            )
            multiplier = entry.get("multiplier")
            if (
                type(multiplier) not in (int, float)
                or not math.isfinite(multiplier)
                or multiplier <= 0
            ):
                raise SourceAdjudicationError(
                    f"Invalid multiplier for {entry['id']}"
                )
            if (
                entry["wave"] != entry["income_year"] + 1
                or entry["income_year"] != entry["birth_year"] + entry["age"]
            ):
                raise SourceAdjudicationError(
                    f"Inconsistent calendar for {entry['id']}"
                )


def validate_registry(document: dict[str, Any], *, expected_name: str) -> None:
    """Check the common citation/status schema without external file access."""
    if expected_name not in REGISTRY_NAMES:
        raise SourceAdjudicationError(f"Unknown U2 registry: {expected_name}")
    if not isinstance(document, dict):
        raise SourceAdjudicationError("Registry document must be an object")
    if (
        type(document.get("schema_version")) is not int
        or document.get("schema_version") != 1
        or document.get("target_id") != "U2"
        or document.get("registry") != expected_name
        or document.get("waves") != list(U2_SOURCE_WAVES)
    ):
        raise SourceAdjudicationError("Wrong U2 registry identity or waves")
    entries = document.get("entries")
    if not isinstance(entries, list) or not entries:
        raise SourceAdjudicationError(
            "Registry entries must be a nonempty list"
        )
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise SourceAdjudicationError("Each entry must be an object")
        key = entry.get("id")
        if not isinstance(key, str) or not key.strip() or key in seen:
            raise SourceAdjudicationError(f"Invalid or duplicate entry: {key}")
        seen.add(key)
        if "wave" not in entry or not (
            entry["wave"] is None
            or (
                type(entry["wave"]) is int and entry["wave"] in U2_SOURCE_WAVES
            )
        ):
            raise SourceAdjudicationError(f"Invalid wave for {key}")
        status = entry.get("status")
        if status not in ("RESOLVED", "TO VERIFY"):
            raise SourceAdjudicationError(f"Invalid source status for {key}")
        if status == "TO VERIFY" and not (
            isinstance(entry.get("question"), str)
            and entry["question"].strip()
        ):
            raise SourceAdjudicationError(f"Missing exact question for {key}")
        citations = entry.get("citations")
        if not isinstance(citations, list) or not citations:
            raise SourceAdjudicationError(f"Missing citations for {key}")
        for citation in citations:
            if not isinstance(citation, dict) or not isinstance(
                citation.get("file"), str
            ):
                raise SourceAdjudicationError(f"Invalid citation for {key}")
            if not citation["file"].strip() or not any(
                type(citation.get(location)) is int and citation[location] > 0
                for location in ("line", "page")
            ):
                raise SourceAdjudicationError(
                    f"Citation needs a file and line or page for {key}"
                )
        dependencies = entry.get("blocking_dependencies", [])
        if not isinstance(dependencies, list) or any(
            not isinstance(value, str) or not value.strip()
            for value in dependencies
        ):
            raise SourceAdjudicationError(f"Invalid dependencies for {key}")
        if len(dependencies) != len(set(dependencies)):
            raise SourceAdjudicationError(f"Duplicate dependencies for {key}")
        for dependency in dependencies:
            parts = dependency.split(":")
            if (
                len(parts) != 2
                or parts[0] not in REGISTRY_NAMES
                or not parts[1].strip()
            ):
                raise SourceAdjudicationError(
                    f"Invalid dependency reference for {key}"
                )
            if dependency == f"{expected_name}:{key}":
                raise SourceAdjudicationError(f"Self dependency for {key}")
        for field in ("action", "refusal", "requires_resolved_route"):
            if field in entry:
                _fields(entry, {field: str})
        if "requires_role_registry" in entry:
            _fields(entry, {"requires_role_registry": bool})
        if "ruling" in entry:
            _ruling(entry)
            if entry["ruling"]["decision"] == "d637":
                _ratified_amendment(entry, expected_name)
        _entry_payload(entry, expected_name)
    # Every entry an applied d637 amendment rules records that ruling, so
    # no ruled entry can drop its record and still pass.
    for (name, key), amendment in _AMENDMENT_OF_ENTRY.items():
        if name != expected_name:
            continue
        entry = next((e for e in entries if e["id"] == key), None)
        if entry is None:
            raise SourceAdjudicationError(
                f"Missing d637 amendment {amendment} entry {name}:{key}"
            )
        if entry.get("ruling", {}).get("decision") != "d637":
            raise SourceAdjudicationError(
                f"{name}:{key} lacks its d637 amendment {amendment} ruling"
            )
    # The route entries an amendment governs hold its ruled values.
    for amendment, scope in RATIFIED_AMENDMENTS.items():
        if scope["registry"] != expected_name:
            continue
        by_id = {entry["id"]: entry for entry in entries}
        for key, (fixed, absent) in scope.get("governs", {}).items():
            entry = by_id.get(key)
            if entry is None:
                raise SourceAdjudicationError(
                    f"Missing entry {key} that d637 amendment {amendment} "
                    "governs"
                )
            if any(
                field not in entry or not _same(entry[field], value)
                for field, value in fixed.items()
            ) or any(field in entry for field in absent):
                raise SourceAdjudicationError(
                    f"{expected_name}:{key} is not the route d637 amendment "
                    f"{amendment} ratified"
                )
    # A value only an amendment's entries may carry stays inside its scope.
    for amendment, scope in RATIFIED_AMENDMENTS.items():
        if scope["registry"] != expected_name:
            continue
        for entry in entries:
            if entry["id"] in scope["entries"]:
                continue
            for field in scope["markers"]:
                if field in entry and (
                    field not in scope["fields"]
                    or _same(entry[field], scope["fields"][field])
                ):
                    raise SourceAdjudicationError(
                        f"{field} of d637 amendment {amendment} outside its "
                        f"scope: {expected_name}:{entry['id']}"
                    )


def load_registry(name: str) -> dict[str, Any]:
    """Load one U2 document from its own directory and validate its schema."""
    if name not in REGISTRY_NAMES:
        raise SourceAdjudicationError(f"Unknown U2 registry: {name}")
    document = json.loads(
        (REGISTRY_DIRECTORY / f"{name}.json").read_text(encoding="utf-8")
    )
    validate_registry(document, expected_name=name)
    return document


def require_resolved(name: str, entry_id: str) -> dict[str, Any]:
    """Return documentary metadata only when it has no recorded blockers.

    This is not authorization to run U2. Independent review, registration,
    and the separate milestone-2 execution guards remain prerequisites.
    """
    for entry in load_registry(name)["entries"]:
        if entry["id"] != entry_id:
            continue
        if entry["status"] != "RESOLVED":
            raise SourceAdjudicationError(
                f"{name}:{entry_id}: TO VERIFY: {entry['question']}"
            )
        if entry.get("blocking_dependencies"):
            raise SourceAdjudicationError(
                f"{name}:{entry_id}: blocked by "
                + ", ".join(entry["blocking_dependencies"])
            )
        if entry.get("action", "").startswith("refuse"):
            raise SourceAdjudicationError(
                f"{name}:{entry_id}: {entry['action']}"
            )
        return entry
    raise SourceAdjudicationError(f"Unknown U2 entry: {name}:{entry_id}")
