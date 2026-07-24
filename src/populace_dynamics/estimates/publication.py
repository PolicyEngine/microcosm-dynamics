"""Publication contracts for the registered first-estimates report.

This module only builds, validates, and exclusively writes records.  It never
starts a projection.  The primary report is integrity-bound to the exact
``.env.json`` bytes supplied to :func:`populace_dynamics.artifacts.write_new`;
incident records use the frozen nine-key ``first_estimates_incident.v1``
schema from design revision 9.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from populace_dynamics import artifacts
from populace_dynamics.contract import ContractRef, environment_block

ARTIFACT_SCHEMA_VERSION = "first_estimates.v1"
INCIDENT_SCHEMA_VERSION = "first_estimates_incident.v1"
DEFAULT_ARTIFACT_PATH = Path("runs/first_estimates_v1.json")
INCIDENT_PHASES = frozenset(
    {"preparation", "invariant", "compute", "publication"}
)
EVIDENCE_LABELS = (
    "frame-relative",
    "pre-alignment",
    "labor-income proxy",
)
ODD_YEAR_CARRY_DISCLOSURE = (
    "The engine draws even-year earnings and carries the prior even-year "
    "value into odd years (2015 repeats 2014, 2017 repeats 2016, and so on)."
)
CANONICAL_EXECUTION_RULE = {
    "registered_runs": 1,
    "publishes_regardless": True,
    "no_self_rescue": True,
    "retry": (
        "At most one coordinator-adjudicated, report-first retry solely for "
        "an external pre-output failure yielding no estimate-bearing "
        "information."
    ),
    "fresh_registration_required_if": (
        "A published v1, any changed configuration byte, or a second failure "
        "of any kind."
    ),
}
CERTIFIES_NOTHING = (
    "This report does not certify forward production.",
    "This report does not estimate national dollars.",
    "This report does not claim that PSID labor income is OASDI-covered "
    "earnings.",
    "This report does not claim administrative benefit-payment dollars.",
    "This report creates no gate, floor, threshold, or verdict.",
)

# The design freezes the gap block.  Keep it data, rather than prose assembled
# by a runner, so the artifact validator can reject omissions or paraphrase
# drift before publication.
GAP_BLOCK: tuple[dict[str, str], ...] = (
    {
        "disclosure": "Scheduled realized 2017/2019 openers condition the object",
        "classification": (
            "material — the reproduction panel is anchored, not forward"
        ),
    },
    {
        "disclosure": "Widowhood limitations",
        "classification": ("material — survivor composition affects presence"),
    },
    {
        "disclosure": (
            'Open additions — certified sentence quoted exactly: "The gate '
            "covers the closed panel only; "
            "synthetic births, immigrant cohorts, and other open additions "
            'remain report-only."'
        ),
        "classification": "material",
    },
    {
        "disclosure": "Lag-5 persistence unscored",
        "classification": "material context for earnings paths",
    },
    {
        "disclosure": "Stock margins unscored",
        "classification": "material context",
    },
    {
        "disclosure": "65+ remarriage tail limitation",
        "classification": (
            "material context — presence of older married persons"
        ),
    },
    {
        "disclosure": (
            "Earnings survivorship — certified sentence quoted exactly: "
            '"Gated earnings use realized support and do not certify '
            "mortality's effect on the earnings composition through "
            'survivorship."'
        ),
        "classification": "material",
    },
    {
        "disclosure": "Full-window model selection",
        "classification": "material context",
    },
    {
        "disclosure": "Redrawn-seed comparison unavailable",
        "classification": "material context",
    },
    {
        "disclosure": (
            "The artifact's earnings-certification string quoted exactly: "
            '"M6-first-certified forward earnings law; no gate_1 backward-law '
            'certificate transfers"'
        ),
        "classification": "restated verbatim",
    },
    {
        "disclosure": (
            "F4 — partial overlay: _merge_period_columns drops named columns "
            "before left-merging, so unmatched live state becomes NaN "
            "(pinned: carried di_converted=True read as no-conversion)"
        ),
        "classification": (
            "material — directly motivates the DI precedence law and the "
            "di_unknown class"
        ),
    },
    {
        "disclosure": (
            "F5 — exact-anchor household seed gap (minors reaching 15 later "
            "and source-gap adults never enter the household domain)"
        ),
        "classification": (
            "inapplicable to presence (certified: household fields feed no "
            "locked cell and are not serialized; roster presence is "
            "unaffected) — material only if household-domain counts are "
            "quoted, and then the certified excluded/domain counts publish "
            "first"
        ),
    },
    {
        "disclosure": (
            'F6 — closed "85+" band (nominal 85+ ends at 120; uncovered ages '
            "get p=0)"
        ),
        "classification": (
            "material context — oldest-old presence in benefit-years"
        ),
    },
    {
        "disclosure": (
            "F8 — entrant classification (anchor_wave > 2015 & ~domain "
            "treated as row existence)"
        ),
        "classification": (
            "material — the reason §3.3/§10 re-derive the entrant count from "
            "explicit earnings rows"
        ),
    },
    {
        "disclosure": (
            "F9 — candidate-9/live-roster reconciliation (household fields do "
            "not reconcile mortality-thinned members or newborns)"
        ),
        "classification": (
            "inapplicable — household composition fields are not consumed"
        ),
    },
    {
        "disclosure": (
            "F9 sub-item — coresident_spouse carried for a person whose "
            "spouse was removed by simulated mortality"
        ),
        "classification": (
            "inapplicable here (household column unconsumed), listed by name "
            "as the certified record requires"
        ),
    },
    {
        "disclosure": (
            "F10 — entrant schema NAs (synthetic_entry=NA inheritance; "
            "certified surface: future panel/schema consumers)"
        ),
        "classification": (
            "this report is such a consumer — it identifies synthetic persons "
            "by ID-set difference per the certified mechanism and never reads "
            "this field; classified handled-by-construction, listed"
        ),
    },
    {
        "disclosure": (
            "F11 — fertility-domain coverage (births draw over "
            "state.marital_ids only; certified surface: family-B birth "
            "counts, no gated cell)"
        ),
        "classification": (
            "inapplicable to benefit tables (no in-window newborn claims); "
            "for revenue person-years the certified fertility-domain "
            "denominator disclosure is restated, not extended"
        ),
    },
    {
        "disclosure": (
            "Certified `forward_projection_2100_extrapolation` limitation"
        ),
        "classification": (
            "material — restated: nothing here extends past 2022, and nothing "
            "certifies any longer horizon"
        ),
    },
    {
        "disclosure": "Mortality drift uncertified",
        "classification": "material",
    },
    {
        "disclosure": "Families B/C ungated",
        "classification": "material",
    },
    {
        "disclosure": "2020-2022 shock window report-only",
        "classification": "material — in-window years",
    },
    {
        "disclosure": "Mechanical claiming, 1998-2013 table",
        "classification": "material",
    },
    {
        "disclosure": "M4 is not DI adjudication",
        "classification": "material — DI is out of scope",
    },
    {
        "disclosure": "Alignment `not_computed`; scored path unaligned",
        "classification": "material",
    },
    {
        "disclosure": "Domain and coverage exclusions (§3.3)",
        "classification": "material; counts published",
    },
    {
        "disclosure": "Odd-year earnings carry law (§3.2)",
        "classification": "material — annual tables",
    },
    {
        "disclosure": "Spouse/survivor benefits out of scope",
        "classification": "material",
    },
    {
        "disclosure": (
            "Levels unanchored — no committed annual SSA level series"
        ),
        "classification": (
            "material; the registered anchor extraction is the successor step"
        ),
    },
)

_ARTIFACT_KEYS = frozenset(
    {
        "schema_version",
        "identity",
        "configuration_echo",
        "integrity",
        "parameters",
        "execution",
        "tables",
        "counts",
        "diagnostics",
        "gap_block",
        "certifies_nothing",
    }
)
_INCIDENT_KEYS = frozenset(
    {
        "schema_version",
        "incident_index",
        "timestamp_utc",
        "phase",
        "reason",
        "reason_detail",
        "registration_reference",
        "configuration_echo",
        "artifact_path",
    }
)
_INCIDENT_FILENAME = re.compile(r"first_estimates_incident_(\d+)\.json")
_UTC_TIMESTAMP = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}" r"(?:\.\d{1,6})?Z"
)


def canonical_json_bytes(value: Any) -> bytes:
    """Return the report's canonical hash representation."""
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def prepare_environment_sidecar(
    root: str | Path | None = None,
) -> tuple[bytes, str]:
    """Freeze exact sidecar bytes before any projection compute begins."""
    record = {
        "environment": environment_block(),
        "contract": asdict(ContractRef.current(root)),
    }
    payload = canonical_json_bytes(record)
    return payload, hashlib.sha256(payload).hexdigest()


def _require_exact_keys(
    value: Mapping[str, Any], expected: frozenset[str], label: str
) -> None:
    observed = frozenset(value)
    if observed != expected:
        raise ValueError(
            f"{label} keys {sorted(observed)} != expected {sorted(expected)}"
        )


def _require_json_finite(value: Any, path: str = "$") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{path} contains a non-finite number")
    if isinstance(value, Mapping):
        for key, child in value.items():
            _require_json_finite(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _require_json_finite(child, f"{path}[{index}]")


def _validate_table(
    name: str,
    table: Any,
    *,
    expected_draw_indices: Sequence[int],
) -> None:
    if not isinstance(table, Mapping):
        raise TypeError(f"table {name!r} must be a mapping")
    if tuple(table.get("labels", ())) != EVIDENCE_LABELS:
        raise ValueError(f"table {name!r} does not carry all evidence labels")
    per_draw = table.get("per_draw")
    if not isinstance(per_draw, list):
        raise TypeError(f"table {name!r} per_draw must be a list")
    if not per_draw or not all(isinstance(row, Mapping) for row in per_draw):
        raise ValueError(f"table {name!r} per_draw rows must be nonempty")
    observed_draws = {
        row.get("draw_index")
        for row in per_draw
        if isinstance(row.get("draw_index"), int)
        and not isinstance(row.get("draw_index"), bool)
    }
    if observed_draws != set(expected_draw_indices):
        raise ValueError(
            f"table {name!r} does not publish every registered draw"
        )
    aggregate = table.get("aggregate")
    if not isinstance(aggregate, list):
        raise TypeError(f"table {name!r} aggregate must be a list")
    if not aggregate or not all(isinstance(row, Mapping) for row in aggregate):
        raise ValueError(f"table {name!r} aggregate rows must be nonempty")
    for row in aggregate:
        if "mean" not in row or "sample_sd" not in row:
            raise ValueError(
                f"table {name!r} aggregate row omits mean/sample_sd"
            )
    if table.get("annual") is True:
        if table.get("odd_year_carry_disclosure") != (
            ODD_YEAR_CARRY_DISCLOSURE
        ):
            raise ValueError(
                f"annual table {name!r} omits the odd-year carry disclosure"
            )
        companion = table.get("biennial_companion")
        if (
            not isinstance(companion, list)
            or not companion
            or not all(isinstance(row, Mapping) for row in companion)
        ):
            raise ValueError(
                f"annual table {name!r} omits its biennial companion"
            )


def validate_first_estimates_artifact(
    artifact: Mapping[str, Any],
    *,
    expected_configuration_echo: Mapping[str, Any],
) -> None:
    """Validate the complete publication object before its one-shot write."""
    _require_exact_keys(artifact, _ARTIFACT_KEYS, "artifact")
    if artifact["schema_version"] != ARTIFACT_SCHEMA_VERSION:
        raise ValueError("first-estimates artifact schema version changed")
    if artifact["configuration_echo"] != expected_configuration_echo:
        raise ValueError(
            "configuration_echo differs from the pre-compute configuration"
        )
    identity = artifact["identity"]
    if not isinstance(identity, Mapping):
        raise TypeError("artifact identity must be a mapping")
    if not isinstance(identity.get("registration_reference"), str):
        raise TypeError("registration_reference must be a JSON string")
    if identity["registration_reference"] != expected_configuration_echo.get(
        "registration_reference"
    ):
        raise ValueError(
            "identity registration reference differs from configuration"
        )
    integrity = artifact["integrity"]
    sidecar = (
        integrity.get("environment_sidecar")
        if isinstance(integrity, Mapping)
        else None
    )
    if not isinstance(sidecar, Mapping):
        raise ValueError("artifact has no environment-sidecar binding")
    digest = sidecar.get("sha256")
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        raise ValueError("environment-sidecar sha256 is invalid")
    execution = artifact["execution"]
    if not isinstance(execution, Mapping):
        raise TypeError("artifact execution must be a mapping")
    if execution.get("canonical_rule") != (CANONICAL_EXECUTION_RULE):
        raise ValueError("artifact changed the canonical execution rule")
    if artifact["parameters"] != expected_configuration_echo.get("parameters"):
        raise ValueError(
            "artifact parameters differ from the registered configuration"
        )
    for name in ("counts", "diagnostics"):
        if not isinstance(artifact[name], Mapping):
            raise TypeError(f"artifact {name} must be a mapping")
    tables = artifact["tables"]
    if not isinstance(tables, Mapping) or not tables:
        raise ValueError("artifact tables must be a nonempty mapping")
    projection = expected_configuration_echo.get("projection")
    expected_draw_indices = (
        projection.get("draw_indices")
        if isinstance(projection, Mapping)
        else None
    )
    if not isinstance(expected_draw_indices, list) or not all(
        isinstance(index, int) and not isinstance(index, bool)
        for index in expected_draw_indices
    ):
        raise ValueError("configuration has no integer draw-index list")
    for name, table in tables.items():
        _validate_table(
            str(name),
            table,
            expected_draw_indices=expected_draw_indices,
        )
    if artifact["gap_block"] != list(GAP_BLOCK):
        raise ValueError("artifact gap block differs from the frozen design")
    if artifact["certifies_nothing"] != list(CERTIFIES_NOTHING):
        raise ValueError("artifact certifies_nothing statements changed")
    _require_json_finite(artifact)
    canonical_json_bytes(artifact)


def write_first_estimates_artifact(
    path: str | Path,
    artifact: Mapping[str, Any],
    *,
    expected_configuration_echo: Mapping[str, Any],
    sidecar_payload: bytes,
) -> None:
    """Validate and exclusively write the integrity-bound report pair."""
    destination = Path(path)
    if destination.name != DEFAULT_ARTIFACT_PATH.name:
        raise ValueError(
            "the first-estimates writer requires first_estimates_v1.json"
        )
    expected_hash = hashlib.sha256(sidecar_payload).hexdigest()
    integrity = artifact.get("integrity")
    sidecar = (
        integrity.get("environment_sidecar")
        if isinstance(integrity, Mapping)
        else None
    )
    if not isinstance(sidecar, Mapping) or sidecar.get("sha256") != (
        expected_hash
    ):
        raise ValueError(
            "primary artifact does not bind the supplied sidecar bytes"
        )
    if sidecar.get("path") != f"{destination.name}.env.json":
        raise ValueError("primary artifact records the wrong sidecar path")
    try:
        parsed_sidecar = json.loads(sidecar_payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("environment sidecar is not valid JSON") from error
    if canonical_json_bytes(parsed_sidecar) != sidecar_payload:
        raise ValueError("environment sidecar bytes are not canonical JSON")
    validate_first_estimates_artifact(
        artifact,
        expected_configuration_echo=expected_configuration_echo,
    )
    artifacts.write_new(
        destination,
        artifact,
        sidecar=True,
        sidecar_payload=sidecar_payload,
    )


def _parse_utc_timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or _UTC_TIMESTAMP.fullmatch(value) is None:
        raise ValueError("timestamp_utc must be ISO-8601 with Z")
    try:
        parsed = datetime.fromisoformat(f"{value[:-1]}+00:00")
    except ValueError as error:
        raise ValueError("timestamp_utc must be ISO-8601 with Z") from error
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(
        parsed
    ):
        raise ValueError("timestamp_utc must be UTC")
    return parsed


def _contains_numeric_array(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_contains_numeric_array(child) for child in value.values())
    if isinstance(value, (list, tuple)):
        if any(
            isinstance(child, (int, float)) and not isinstance(child, bool)
            for child in value
        ):
            return True
        return any(_contains_numeric_array(child) for child in value)
    return False


def validate_first_estimates_incident(
    record: Mapping[str, Any],
    *,
    path: str | Path,
    expected_configuration_echo: Mapping[str, Any],
    repository_root: str | Path,
) -> None:
    """Enforce the exact frozen incident schema and no-output-value rule."""
    _require_exact_keys(record, _INCIDENT_KEYS, "incident")
    if record["schema_version"] != INCIDENT_SCHEMA_VERSION:
        raise ValueError("incident schema version changed")
    index = record["incident_index"]
    if isinstance(index, bool) or not isinstance(index, int) or index < 1:
        raise TypeError("incident_index must be a positive integer")
    match = _INCIDENT_FILENAME.fullmatch(Path(path).name)
    if match is None or int(match.group(1)) != index:
        raise ValueError("incident index does not match its filename")
    _parse_utc_timestamp(record["timestamp_utc"])
    phase = record["phase"]
    if phase not in INCIDENT_PHASES:
        raise ValueError("incident phase is outside the frozen enum")
    for key in ("reason", "reason_detail", "registration_reference"):
        if not isinstance(record[key], str):
            raise TypeError(f"{key} must be a JSON string")
    if not record["reason"]:
        raise ValueError("incident reason must not be empty")
    if record["configuration_echo"] != expected_configuration_echo:
        raise ValueError(
            "incident configuration_echo is not the pre-compute object"
        )
    if not isinstance(record["configuration_echo"], Mapping):
        raise TypeError("incident configuration_echo must be a mapping")
    if record["registration_reference"] != expected_configuration_echo.get(
        "registration_reference"
    ):
        raise ValueError(
            "incident registration reference differs from configuration"
        )
    artifact_path = record["artifact_path"]
    if artifact_path is not None and not isinstance(artifact_path, str):
        raise TypeError("artifact_path must be a JSON string or null")
    root = Path(repository_root).resolve()
    default_partial = root / DEFAULT_ARTIFACT_PATH
    partial_exists = default_partial.is_file()
    if artifact_path is not None:
        candidate = root / artifact_path
        try:
            candidate.resolve().relative_to(root)
        except ValueError as error:
            raise ValueError("artifact_path escapes the repository") from error
        if candidate.resolve() != default_partial.resolve():
            raise ValueError(
                "artifact_path must identify runs/first_estimates_v1.json"
            )
    expected_artifact_path = (
        DEFAULT_ARTIFACT_PATH.as_posix()
        if phase == "publication" and partial_exists
        else None
    )
    if artifact_path != expected_artifact_path:
        raise ValueError(
            "artifact_path must be non-null iff a publication partial exists"
        )
    outside_echo = {
        key: value
        for key, value in record.items()
        if key != "configuration_echo"
    }
    if _contains_numeric_array(outside_echo):
        raise ValueError(
            "incident contains a numeric array outside configuration_echo"
        )
    _require_json_finite(record)
    canonical_json_bytes(record)


def incident_is_retry_eligible(record: Mapping[str, Any]) -> bool:
    """Return the canonical external-pre-output retry classification."""
    return (
        record.get("phase") in {"preparation", "compute"}
        and isinstance(record.get("reason"), str)
        and record["reason"].startswith("external_")
    )


def _next_incident_path(repository_root: Path) -> tuple[Path, int]:
    runs = repository_root / "runs"
    existing: list[int] = []
    for path in runs.glob("first_estimates_incident_*.json"):
        match = _INCIDENT_FILENAME.fullmatch(path.name)
        if match is not None:
            existing.append(int(match.group(1)))
    ordered = sorted(existing)
    if ordered != list(range(1, len(ordered) + 1)):
        raise RuntimeError(
            "existing first-estimates incidents are not contiguous"
        )
    index = len(ordered) + 1
    return runs / f"first_estimates_incident_{index}.json", index


def write_first_estimates_incident(
    *,
    repository_root: str | Path,
    phase: str,
    reason: str,
    reason_detail: str,
    registration_reference: str,
    configuration_echo: Mapping[str, Any],
    partial_artifact_path: str | Path | None = None,
    timestamp_utc: str | None = None,
) -> Path:
    """Append the next validated incident record without a sidecar."""
    root = Path(repository_root).resolve()
    path, index = _next_incident_path(root)
    relative_artifact: str | None = None
    if partial_artifact_path is not None:
        partial = Path(partial_artifact_path)
        if not partial.is_absolute():
            partial = root / partial
        try:
            relative_artifact = partial.resolve().relative_to(root).as_posix()
        except ValueError as error:
            raise ValueError(
                "partial artifact path is outside the repository"
            ) from error
        if not partial.is_file():
            raise FileNotFoundError(
                "partial artifact path does not identify an existing file"
            )
    timestamp = timestamp_utc or (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )
    record = {
        "schema_version": INCIDENT_SCHEMA_VERSION,
        "incident_index": index,
        "timestamp_utc": timestamp,
        "phase": phase,
        "reason": reason,
        "reason_detail": reason_detail,
        "registration_reference": registration_reference,
        "configuration_echo": dict(configuration_echo),
        "artifact_path": relative_artifact,
    }
    validate_first_estimates_incident(
        record,
        path=path,
        expected_configuration_echo=configuration_echo,
        repository_root=root,
    )
    artifacts.write_new(path, record)
    return path


def table_record(
    *,
    per_draw: Sequence[Mapping[str, Any]],
    aggregate: Sequence[Mapping[str, Any]],
    unit_label: str,
    annual: bool,
    biennial_companion: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Wrap report rows with the repeated evidential labels and disclosures."""
    record: dict[str, Any] = {
        "labels": list(EVIDENCE_LABELS),
        "unit_label": unit_label,
        "annual": bool(annual),
        "per_draw": [dict(row) for row in per_draw],
        "aggregate": [dict(row) for row in aggregate],
    }
    if annual:
        record["odd_year_carry_disclosure"] = ODD_YEAR_CARRY_DISCLOSURE
        record["biennial_companion"] = [
            dict(row) for row in (biennial_companion or ())
        ]
    return record
