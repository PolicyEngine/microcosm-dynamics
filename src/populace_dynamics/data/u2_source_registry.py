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
        if entry["present"]:
            _fields(entry, {"label": str, "spouse_slot": bool})
        elif "label" not in entry or entry["label"] is not None:
            raise SourceAdjudicationError(
                f"Absent role needs null label for {entry['id']}"
            )
        if entry["status"] == "RESOLVED" and entry["present"]:
            _fields(entry, {"income_role": str})
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
        _entry_payload(entry, expected_name)


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
