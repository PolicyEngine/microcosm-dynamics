"""Linear-size persistence for validated closed-cohort earnings histories.

This optional envelope leaves the legacy serializers and their digests intact.
Loading requires the trusted legacy baseline that owns the identity map.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping

from .closed_cohort_history import (
    ClosedCohortEarningsHistory,
    CohortTransition,
)
from .forward_earnings_history import (
    ForwardEarningsHistory,
    ForwardEarningsObservation,
)
from .mortality_observer import MortalityStepObservation

_SCHEMA = "populace_dynamics.compact_closed_cohort_history.v1"
_HISTORY_FIELDS = {
    "identity_map_digest",
    "realization_id",
    "generator_digest",
    "source_contract_digest",
    "unit",
    "price_basis",
    "calendar",
    "source_registry_status",
    "coverage_status",
    "roster_keys",
    "last_year",
    "observations",
}
_OBSERVATION_FIELDS = {
    "dynamics_person_key",
    "year",
    "amount_hex",
    "earnings_domain",
    "lineage_digest",
}


def _json(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )


def _load(text: str) -> object:
    if type(text) is not str:
        raise ValueError("compact history must be JSON text")

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON field")
            result[key] = value
        return result

    def reject(value):
        raise ValueError(f"invalid JSON constant: {value}")

    return json.loads(text, object_pairs_hook=unique, parse_constant=reject)


def _digest(value: object, label: str) -> str:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _integer(value: object, label: str) -> int:
    if type(value) is not str:
        raise ValueError(f"{label} must be a canonical integer string")
    try:
        result = int(value)
    except ValueError as exc:
        raise ValueError(
            f"{label} must be a canonical integer string"
        ) from exc
    if str(result) != value:
        raise ValueError(f"{label} must be a canonical integer string")
    return result


def _keys(value: object, fields: set[str], label: str) -> Mapping:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValueError(f"invalid {label} fields")
    return value


def _history_document(
    history: ForwardEarningsHistory, identity_map_digest: str
) -> dict:
    return {
        "identity_map_digest": identity_map_digest,
        "realization_id": history.realization_id,
        "generator_digest": history.generator_digest,
        "source_contract_digest": history.source_contract_digest,
        "unit": history.unit,
        "price_basis": history.price_basis,
        "calendar": "calendar_year",
        "source_registry_status": history.source_registry_status,
        "coverage_status": history.coverage_status,
        "roster_keys": [str(key) for key in history.roster_keys],
        "last_year": str(history.last_year),
        "observations": [
            {
                "dynamics_person_key": str(row.dynamics_person_key),
                "year": str(row.year),
                "amount_hex": row.amount_hex,
                "earnings_domain": row.earnings_domain,
                "lineage_digest": row.lineage_digest,
            }
            for row in history.observations
        ],
    }


def compact_history_to_json(history: ClosedCohortEarningsHistory) -> str:
    """Serialize a validated history without repeated identity-map documents."""
    if type(history) is not ClosedCohortEarningsHistory:
        raise ValueError("explicit closed-cohort history required")
    identity_map_digest = history.baseline.identity_map.digest
    return _json(
        {
            "schema": _SCHEMA,
            "baseline_digest": history.baseline.digest,
            "identity_map_digest": identity_map_digest,
            "draw_index": str(history.draw_index),
            "last_year": str(history.last_year),
            "histories": [
                _history_document(item, identity_map_digest)
                for item in history.histories
            ],
            "transitions": [
                {
                    "mortality": json.loads(item.mortality.to_json()),
                    "lineage_digest": item.lineage_digest,
                    "survivor_demographics": [
                        [str(key), str(age), sex]
                        for key, age, sex in item.survivor_demographics
                    ],
                }
                for item in history.transitions
            ],
        }
    )


def compact_history_digest(history: ClosedCohortEarningsHistory) -> str:
    """Return the distinct SHA-256 digest of the compact envelope."""
    return hashlib.sha256(
        compact_history_to_json(history).encode()
    ).hexdigest()


def _history_from_document(
    document: object,
    baseline: ForwardEarningsHistory,
    identity_map_digest: str,
):
    item = _keys(document, _HISTORY_FIELDS, "compact child history")
    if (
        item["identity_map_digest"] != identity_map_digest
        or item["calendar"] != "calendar_year"
        or item["source_registry_status"] != "registration_required"
        or item["coverage_status"] != "not_materialized"
    ):
        raise ValueError("compact child scope or identity mismatch")
    if (
        type(item["roster_keys"]) is not list
        or type(item["observations"]) is not list
    ):
        raise ValueError("compact child arrays required")
    observations = []
    for value in item["observations"]:
        row = _keys(value, _OBSERVATION_FIELDS, "compact observation")
        observations.append(
            ForwardEarningsObservation(
                _integer(row["dynamics_person_key"], "person key"),
                _integer(row["year"], "year"),
                row["amount_hex"],
                row["earnings_domain"],
                row["lineage_digest"],
            )
        )
    return ForwardEarningsHistory(
        baseline.identity_map,
        item["realization_id"],
        item["generator_digest"],
        item["source_contract_digest"],
        item["unit"],
        item["price_basis"],
        tuple(_integer(value, "roster key") for value in item["roster_keys"]),
        _integer(item["last_year"], "last year"),
        tuple(observations),
    )


def compact_history_from_json(
    text: str,
    *,
    baseline: ForwardEarningsHistory,
    expected_digest: str,
    previous: ClosedCohortEarningsHistory | None = None,
) -> ClosedCohortEarningsHistory:
    """Load a compact envelope against a trusted baseline and exact digest."""
    if type(baseline) is not ForwardEarningsHistory:
        raise ValueError("trusted ForwardEarningsHistory baseline required")
    if type(text) is not str:
        raise ValueError("compact history must be JSON text")
    expected_digest = _digest(expected_digest, "compact envelope digest")
    if hashlib.sha256(text.encode()).hexdigest() != expected_digest:
        raise ValueError("compact envelope digest mismatch")
    document = _keys(
        _load(text),
        {
            "schema",
            "baseline_digest",
            "identity_map_digest",
            "draw_index",
            "last_year",
            "histories",
            "transitions",
        },
        "compact envelope",
    )
    identity_map_digest = baseline.identity_map.digest
    if (
        document["schema"] != _SCHEMA
        or document["baseline_digest"] != baseline.digest
        or document["identity_map_digest"] != identity_map_digest
    ):
        raise ValueError("compact envelope baseline binding mismatch")
    if (
        type(document["histories"]) is not list
        or type(document["transitions"]) is not list
    ):
        raise ValueError("compact envelope arrays required")
    histories = tuple(
        _history_from_document(item, baseline, identity_map_digest)
        for item in document["histories"]
    )
    transitions = []
    for value in document["transitions"]:
        item = _keys(
            value,
            {"mortality", "lineage_digest", "survivor_demographics"},
            "compact transition",
        )
        if type(item["survivor_demographics"]) is not list:
            raise ValueError("survivor demographics array required")
        demographics = []
        for row in item["survivor_demographics"]:
            if type(row) is not list or len(row) != 3:
                raise ValueError("invalid survivor demographic row")
            demographics.append(
                (
                    _integer(row[0], "survivor key"),
                    _integer(row[1], "survivor age"),
                    row[2],
                )
            )
        transitions.append(
            CohortTransition(
                MortalityStepObservation.from_json(
                    _json(item["mortality"]),
                    identity_map=baseline.identity_map,
                ),
                item["lineage_digest"],
                tuple(demographics),
            )
        )
    result = ClosedCohortEarningsHistory(
        baseline,
        _integer(document["draw_index"], "draw index"),
        histories,
        tuple(transitions),
    )
    if result.last_year != _integer(document["last_year"], "last year"):
        raise ValueError("compact envelope last year mismatch")
    if compact_history_to_json(result) != text:
        raise ValueError("noncanonical or inconsistent compact envelope")
    if previous is not None:
        result.require_extension_of(previous)
    return result
