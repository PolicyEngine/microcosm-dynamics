"""Fail-closed validators for the standing benchmark artifacts."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REGISTRY_PATH = HERE / "registry.json"
HISTORY_PATH = HERE / "history.jsonl"

TIERS = (
    "admin_truth",
    "model_triangulation",
    "statutory_parameter",
)
GAP_CLASSES = (
    "label_mismatch",
    "frame_no_alignment",
    "concept_mismatch",
    "module_missing",
    "small_cell",
    "preliminary_source",
    "unexplained",
)
COMPARISON_SCOPES = ("ratio", "share", "trajectory", "ordering")

REGISTRY_KEYS = {
    "allowed_comparison_scopes",
    "canonicalization",
    "deferred_comparisons",
    "entries",
    "external_capture_review",
    "gap_class_counts",
    "gap_classes",
    "honesty_frame",
    "inputs",
    "purpose",
    "registry_change_law",
    "row_count",
    "schema_version",
    "seed_evaluation",
    "tier_counts",
    "tiers",
    "validation_only_law",
}
ENTRY_KEYS = {
    "comparison_scope",
    "concept_mismatch",
    "evidential_status",
    "external_reference",
    "gap_class",
    "gap_closure_condition",
    "gap_note",
    "our_side_artifact",
    "published_formula",
    "published_unit",
    "quantity",
    "row_id",
    "source_pin",
    "spec_revisions",
    "tier",
    "verification_class",
}
HISTORY_KEYS = {
    "deviation",
    "evaluated_at_run",
    "gap_class",
    "gap_note",
    "label_state",
    "our",
    "published",
    "registry_sha",
    "row_id",
}
LABEL_STATE_KEYS = {
    "individual_administrative_truth_claim",
    "matrix_display",
    "population_alignment_claim",
    "ratified_array_activation_asserted_by_this_matrix",
    "ratified_array_locator",
    "ratified_fitting_free_exact_label_array",
    "source_artifact_embedded_labels",
    "source_artifact_label_note",
}
REVISION_KEYS = {"changed_fields", "note", "revision"}
IMMUTABLE_REGISTRY_KEYS = {
    "allowed_comparison_scopes",
    "canonicalization",
    "gap_classes",
    "honesty_frame",
    "purpose",
    "registry_change_law",
    "schema_version",
    "seed_evaluation",
    "tiers",
    "validation_only_law",
}


def sha256_bytes(raw: bytes) -> str:
    """Return the lowercase SHA-256 digest of bytes."""

    return hashlib.sha256(raw).hexdigest()


def is_sha256(value: Any) -> bool:
    """Return whether value is exactly one lowercase SHA-256 digest."""

    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return value == value.lower()


def require(condition: bool, message: str) -> None:
    """Raise an alarm that remains active under optimized Python."""

    if not condition:
        raise AssertionError(message)


def is_one_sentence(value: Any) -> bool:
    """Return whether value is one nonempty, terminally punctuated sentence."""

    if not isinstance(value, str):
        return False
    text = value.strip()
    if not text or not any(character.isalnum() for character in text):
        return False
    boundaries = re.findall(r"[.!?](?=\s|$)", text)
    return len(boundaries) == 1 and text[-1] in ".!?"


def is_repo_relative_json_path(value: Any) -> bool:
    """Return whether value is one normalized, repository-relative JSON path."""

    if not isinstance(value, str) or not value.endswith(".json"):
        return False
    path = PurePosixPath(value)
    return (
        not path.is_absolute()
        and value == path.as_posix()
        and ".." not in path.parts
        and "." not in path.parts
    )


def is_json_pointer(value: Any) -> bool:
    """Return whether value is the root marker or an absolute JSON pointer."""

    return isinstance(value, str) and (value == "/" or value.startswith("/"))


def is_measurement_value(value: Any) -> bool:
    """Reject empty or nonnumeric measurements while permitting orderings."""

    if isinstance(value, bool) or value is None:
        return False
    if isinstance(value, (int, float)):
        return math.isfinite(value)
    if not isinstance(value, list) or not value:
        return False
    if all(isinstance(item, str) and item.strip() for item in value):
        return len(value) == len(set(value))
    return all(
        isinstance(item, dict) and item and any_numeric_leaf(item)
        for item in value
    )


def any_numeric_leaf(value: Any) -> bool:
    """Return whether a JSON-like value contains a finite numeric leaf."""

    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return math.isfinite(value)
    if isinstance(value, dict):
        return any(any_numeric_leaf(item) for item in value.values())
    if isinstance(value, list):
        return any(any_numeric_leaf(item) for item in value)
    return False


def canonical_json_bytes(value: Any) -> bytes:
    """Render canonical pretty JSON used by registry.json."""

    return (
        json.dumps(
            value,
            sort_keys=True,
            indent=2,
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def canonical_jsonl_line(value: Any) -> bytes:
    """Render one compact, sorted, canonical JSONL object."""

    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def resolve_json_pointer(document: Any, pointer: str) -> Any:
    """Resolve the registry's slash-rooted JSON pointer convention."""

    if pointer == "/":
        return document
    current = document
    for encoded_token in pointer[1:].split("/"):
        token = encoded_token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            current = current[int(token)]
        else:
            current = current[token]
    return current


def validate_registry_artifacts(
    registry: dict[str, Any], root: Path = ROOT
) -> None:
    """Verify every committed pointer against confined repository bytes."""

    root = root.resolve()
    pointers = []
    for entry in registry["entries"]:
        pointers.append(entry["our_side_artifact"]["artifact_pointer"])
        pointers.extend(
            artifact
            for artifact in entry["source_pin"]["artifacts"]
            if artifact["pin_type"] == "committed_extraction"
        )

    parsed_documents: dict[Path, Any] = {}
    for pointer in pointers:
        relative_path = pointer["path"]
        require(
            is_repo_relative_json_path(relative_path),
            f"artifact path escapes or is not JSON: {relative_path}",
        )
        path = (root / relative_path).resolve()
        require(
            path.is_relative_to(root),
            f"artifact path escapes repository: {relative_path}",
        )
        require(path.is_file(), f"missing committed artifact: {relative_path}")
        raw = path.read_bytes()
        require(
            sha256_bytes(raw) == pointer["sha256"],
            f"committed artifact SHA drift: {relative_path}",
        )
        if path not in parsed_documents:
            parsed_documents[path] = json.loads(raw)
        try:
            resolve_json_pointer(
                parsed_documents[path], pointer["json_pointer"]
            )
        except (IndexError, KeyError, TypeError, ValueError) as error:
            raise AssertionError(
                f"unresolvable JSON pointer in {relative_path}: "
                f"{pointer['json_pointer']}"
            ) from error


def load_registry(path: Path = REGISTRY_PATH) -> tuple[dict[str, Any], bytes]:
    """Load registry bytes while retaining their hash identity."""

    raw = path.read_bytes()
    registry = json.loads(raw)
    if raw != canonical_json_bytes(registry):
        raise AssertionError("registry.json is not canonical sorted JSON")
    validate_registry(registry)
    validate_registry_artifacts(registry)
    return registry, raw


def load_history(
    path: Path = HISTORY_PATH,
) -> tuple[list[dict[str, Any]], bytes]:
    """Load and validate canonical history records in append order."""

    raw = path.read_bytes()
    if not raw or not raw.endswith(b"\n"):
        raise AssertionError(
            "history.jsonl must be nonempty and LF-terminated"
        )
    records = []
    offset = 0
    for line_number, line in enumerate(raw.splitlines(keepends=True), 1):
        if line in {b"\n", b"\r\n"}:
            raise AssertionError(f"blank history line {line_number}")
        record = json.loads(line)
        if line != canonical_jsonl_line(record):
            raise AssertionError(
                f"history line {line_number} is not canonical sorted JSON"
            )
        record["_byte_start"] = offset
        offset += len(line)
        record["_byte_end"] = offset
        records.append(record)
    validate_history(records)
    for record in records:
        del record["_byte_start"]
        del record["_byte_end"]
    return records, raw


def validate_registry(registry: dict[str, Any]) -> None:
    """Validate exact registry shape, enums, pins, and synchronized counts."""

    require(set(registry) == REGISTRY_KEYS, "registry keys have drifted")
    require(
        registry["schema_version"] == "standing_benchmark_registry.v1",
        "unsupported benchmark registry schema",
    )
    require(
        registry["allowed_comparison_scopes"] == list(COMPARISON_SCOPES),
        "comparison-scope enum has drifted",
    )
    require(set(registry["tiers"]) == set(TIERS), "tier enum has drifted")
    require(
        set(registry["gap_classes"]) == set(GAP_CLASSES),
        "gap-class enum has drifted",
    )
    require(
        all(
            isinstance(definition, dict)
            and set(definition) == {"closure_condition", "definition"}
            and isinstance(definition["closure_condition"], str)
            and definition["closure_condition"].strip()
            for definition in registry["gap_classes"].values()
        ),
        "every gap class needs a closure condition",
    )
    require(
        "never normative"
        in registry["tiers"]["model_triangulation"]["gap_law"],
        "model-triangulation gaps must remain nonnormative",
    )

    entries = registry["entries"]
    require(isinstance(entries, list) and entries, "registry needs entries")
    require(
        registry["row_count"] == len(entries),
        "registry row_count is not synchronized",
    )
    row_ids = [entry["row_id"] for entry in entries]
    require(len(row_ids) == len(set(row_ids)), "duplicate benchmark row_id")

    tier_counts = Counter()
    gap_counts = Counter()
    for entry in entries:
        validate_registry_entry(entry)
        tier_counts[entry["tier"]] += 1
        gap_counts[entry["gap_class"]] += 1

    reviewed_captures = {
        json.dumps(
            {
                "filename": capture["filename"],
                "pin_type": "sha_manifested_capture",
                "sha256": capture["sha256"],
                "size_bytes": capture["size_bytes"],
                "url": capture["url"],
            },
            sort_keys=True,
        )
        for capture in registry["external_capture_review"]["captures"].values()
    }
    registered_captures = {
        json.dumps(artifact, sort_keys=True)
        for entry in entries
        for artifact in entry["source_pin"]["artifacts"]
        if artifact["pin_type"] == "sha_manifested_capture"
    }
    require(
        registered_captures <= reviewed_captures,
        "source capture is absent from the reviewed external manifest",
    )

    require(
        registry["tier_counts"] == {tier: tier_counts[tier] for tier in TIERS},
        "registry tier_counts are not synchronized",
    )
    require(
        registry["gap_class_counts"]
        == {gap_class: gap_counts[gap_class] for gap_class in GAP_CLASSES},
        "registry gap_class_counts are not synchronized",
    )


def validate_registry_entry(entry: dict[str, Any]) -> None:
    """Validate one append-mostly benchmark specification."""

    require(set(entry) == ENTRY_KEYS, "benchmark entry keys have drifted")
    row_id = entry["row_id"]
    require(isinstance(row_id, str) and row_id.strip(), "missing row_id")
    require(
        isinstance(entry["quantity"], str) and entry["quantity"].strip(),
        f"missing quantity: {row_id}",
    )
    require(entry["tier"] in TIERS, f"invalid tier: {row_id}")
    require(
        entry["gap_class"] in GAP_CLASSES,
        f"invalid gap class: {row_id}",
    )
    require(
        entry["gap_class"] != "unexplained",
        f"unexplained benchmark gap: {row_id}",
    )
    require(
        is_one_sentence(entry["gap_note"]),
        f"gap note must be one sentence: {row_id}",
    )
    require(
        isinstance(entry["gap_closure_condition"], str)
        and entry["gap_closure_condition"].strip(),
        f"missing gap closure condition: {row_id}",
    )
    require(
        entry["verification_class"] in {"verified", "reported_not_verified"},
        f"invalid verification class: {row_id}",
    )
    require(
        isinstance(entry["comparison_scope"], list)
        and entry["comparison_scope"],
        f"missing comparison scope: {row_id}",
    )
    require(
        len(entry["comparison_scope"]) == len(set(entry["comparison_scope"])),
        f"duplicate comparison scope: {row_id}",
    )
    require(
        set(entry["comparison_scope"]) <= set(COMPARISON_SCOPES),
        f"invalid comparison scope: {row_id}",
    )

    our_side = entry["our_side_artifact"]
    require(
        isinstance(our_side, dict)
        and isinstance(our_side.get("unit"), str)
        and our_side["unit"].strip(),
        f"invalid our-side artifact spec: {row_id}",
    )
    our_pointer = our_side["artifact_pointer"]
    require(
        set(our_pointer) == {"json_pointer", "path", "sha256"},
        f"invalid our-side artifact pointer: {row_id}",
    )
    require(
        is_sha256(our_pointer["sha256"]), f"invalid artifact SHA: {row_id}"
    )
    require(
        is_repo_relative_json_path(our_pointer["path"]),
        f"our-side artifact must be JSON: {row_id}",
    )
    require(
        is_json_pointer(our_pointer["json_pointer"]),
        f"invalid our-side JSON pointer: {row_id}",
    )

    source_pin = entry["source_pin"]
    require(
        set(source_pin)
        == {"artifacts", "exact_locators", "reported_value_provenance"},
        f"invalid source pin: {row_id}",
    )
    require(source_pin["artifacts"], f"missing source artifact: {row_id}")
    require(source_pin["exact_locators"], f"missing exact locator: {row_id}")
    artifact_identities = set()
    for artifact in source_pin["artifacts"]:
        require(
            artifact["pin_type"]
            in {"committed_extraction", "sha_manifested_capture"},
            f"invalid source pin type: {row_id}",
        )
        require(is_sha256(artifact["sha256"]), f"invalid source SHA: {row_id}")
        if artifact["pin_type"] == "committed_extraction":
            require(
                set(artifact)
                == {"json_pointer", "path", "pin_type", "sha256"},
                f"invalid committed extraction shape: {row_id}",
            )
            require(
                is_repo_relative_json_path(artifact["path"]),
                f"invalid extraction path: {row_id}",
            )
            require(
                is_json_pointer(artifact["json_pointer"]),
                f"invalid extraction JSON pointer: {row_id}",
            )
        else:
            require(
                set(artifact)
                == {"filename", "pin_type", "sha256", "size_bytes", "url"},
                f"invalid external capture shape: {row_id}",
            )
            require(
                bool(artifact["filename"]), f"missing capture file: {row_id}"
            )
            require(bool(artifact["url"]), f"missing capture URL: {row_id}")
            require(
                artifact["size_bytes"] > 0, f"empty source capture: {row_id}"
            )
        artifact_identities.add(json.dumps(artifact, sort_keys=True))
    require(
        len(artifact_identities) == len(source_pin["artifacts"]),
        f"duplicate source artifact: {row_id}",
    )

    locators = source_pin["exact_locators"]
    require(
        len({json.dumps(locator, sort_keys=True) for locator in locators})
        == len(locators),
        f"duplicate exact locator: {row_id}",
    )
    coordinate_families = (
        {"column_header_path", "row_locator"},
        {"observation_range", "sheet"},
        {"column_path", "row_path"},
        {"provision", "section"},
    )
    used_artifacts = set()
    for locator in locators:
        require(
            bool(locator["document"]), f"missing source document: {row_id}"
        )
        require(bool(locator.get("page")), f"missing source page: {row_id}")
        require(bool(locator["table"]), f"missing source table: {row_id}")
        matched_families = [
            family
            for family in coordinate_families
            if family <= set(locator)
            and all(bool(locator[field]) for field in family)
        ]
        require(
            len(matched_families) == 1,
            f"locator needs one exact coordinate family: {row_id}",
        )

    if entry["verification_class"] == "verified":
        require(
            source_pin["reported_value_provenance"] is None,
            f"verified row cannot retain reported provenance: {row_id}",
        )
        for locator in locators:
            accepted = {
                "committed_extraction",
                "reviewed_external_capture",
            } & set(locator)
            require(
                len(accepted) == 1,
                f"verified locator needs one accepted source: {row_id}",
            )
            require(
                "capture_status" not in locator
                and "unmanifested_corroborating_copy" not in locator,
                f"verified locator cannot retain provisional markers: {row_id}",
            )
            if "committed_extraction" in locator:
                normalized = {
                    "pin_type": "committed_extraction",
                    **locator["committed_extraction"],
                }
            else:
                normalized = {
                    "pin_type": "sha_manifested_capture",
                    **locator["reviewed_external_capture"],
                }
            identity = json.dumps(normalized, sort_keys=True)
            require(
                identity in artifact_identities,
                f"locator source is absent from source artifacts: {row_id}",
            )
            used_artifacts.add(identity)
    else:
        require(".mermin." in row_id, f"unexpected unverified row: {row_id}")
        provenance = source_pin["reported_value_provenance"]
        require(
            isinstance(provenance, dict)
            and set(provenance)
            == {
                "classification",
                "numeric_source",
                "numeric_source_note",
                "publisher_capture_status",
            }
            and provenance["classification"] == "reported_not_verified",
            f"unverified provenance class mismatch: {row_id}",
        )
        numeric_source = provenance["numeric_source"]
        require(
            set(numeric_source) == {"json_pointer", "path", "sha256"},
            f"invalid reported numeric source: {row_id}",
        )
        normalized_numeric_source = {
            "pin_type": "committed_extraction",
            **numeric_source,
        }
        numeric_identity = json.dumps(
            normalized_numeric_source, sort_keys=True
        )
        require(
            numeric_identity in artifact_identities,
            f"reported numeric source is absent from source artifacts: {row_id}",
        )
        used_artifacts.add(numeric_identity)
        for locator in locators:
            require(
                not {
                    "committed_extraction",
                    "reviewed_external_capture",
                }
                & set(locator),
                f"unverified locator cannot name an accepted source: {row_id}",
            )
            require(
                "missing after REFRESH" in locator.get("capture_status", ""),
                f"unverified locator needs capture status: {row_id}",
            )
            corroboration = locator["unmanifested_corroborating_copy"]
            require(
                set(corroboration)
                == {
                    "accepted_as_verified_source",
                    "manifested",
                    "scope",
                    "sha256",
                }
                and is_sha256(corroboration["sha256"]),
                f"invalid unmanifested corroboration: {row_id}",
            )
            require(
                corroboration["manifested"] is False,
                f"unverified corroboration cannot be manifested: {row_id}",
            )
            require(
                corroboration["accepted_as_verified_source"] is False,
                f"corroboration cannot verify source: {row_id}",
            )

    require(
        used_artifacts == artifact_identities,
        f"source artifacts and exact locators are not one-to-one: {row_id}",
    )

    revisions = entry["spec_revisions"]
    require(isinstance(revisions, list), f"invalid spec revisions: {row_id}")
    for expected_revision, revision in enumerate(revisions, 1):
        require(
            set(revision) == REVISION_KEYS, f"invalid revision keys: {row_id}"
        )
        require(
            revision["revision"] == expected_revision,
            f"nonsequential spec revision: {row_id}",
        )
        require(
            is_one_sentence(revision["note"]),
            f"revision note must be one sentence: {row_id}",
        )
        require(
            isinstance(revision["changed_fields"], list)
            and revision["changed_fields"]
            and len(revision["changed_fields"])
            == len(set(revision["changed_fields"]))
            and all(
                isinstance(field, str)
                and field.startswith("/")
                and field not in {"/row_id", "/spec_revisions"}
                and not field.startswith("/spec_revisions/")
                for field in revision["changed_fields"]
            ),
            f"invalid changed_fields: {row_id}",
        )


def escaped_pointer_token(value: Any) -> str:
    """Encode one mapping key or list index as a JSON Pointer token."""

    return str(value).replace("~", "~0").replace("/", "~1")


def json_diff_paths(old: Any, new: Any, path: str = "") -> set[str]:
    """Return the precise JSON Pointer leaves that differ."""

    if type(old) is not type(new):
        return {path or "/"}
    if isinstance(old, dict):
        differences = set()
        for key in set(old) | set(new):
            child = f"{path}/{escaped_pointer_token(key)}"
            if key not in old or key not in new:
                differences.add(child)
            else:
                differences |= json_diff_paths(old[key], new[key], child)
        return differences
    if isinstance(old, list):
        differences = set()
        for index in range(max(len(old), len(new))):
            child = f"{path}/{index}"
            if index >= len(old) or index >= len(new):
                differences.add(child)
            else:
                differences |= json_diff_paths(old[index], new[index], child)
        return differences
    return set() if old == new else {path or "/"}


def validate_append_mostly_registry(
    previous: dict[str, Any], current: dict[str, Any]
) -> None:
    """Enforce row order and revision notes across registry generations."""

    validate_registry(previous)
    validate_registry(current)
    for key in IMMUTABLE_REGISTRY_KEYS:
        require(
            current[key] == previous[key],
            f"immutable registry law changed without a schema migration: {key}",
        )
    previous_entries = previous["entries"]
    current_entries = current["entries"]
    previous_ids = [entry["row_id"] for entry in previous_entries]
    current_ids = [entry["row_id"] for entry in current_entries]
    require(
        current_ids[: len(previous_ids)] == previous_ids,
        "existing benchmark rows cannot be removed, reordered, or renamed",
    )
    for old, new in zip(previous_entries, current_entries, strict=False):
        old_revisions = old["spec_revisions"]
        new_revisions = new["spec_revisions"]
        require(
            new_revisions[: len(old_revisions)] == old_revisions,
            f"spec revision history was rewritten: {old['row_id']}",
        )
        old_spec = {
            key: value for key, value in old.items() if key != "spec_revisions"
        }
        new_spec = {
            key: value for key, value in new.items() if key != "spec_revisions"
        }
        actual_changes = json_diff_paths(old_spec, new_spec)
        if not actual_changes:
            require(
                new_revisions == old_revisions,
                f"revision note without a spec change: {old['row_id']}",
            )
            continue
        require(
            len(new_revisions) == len(old_revisions) + 1,
            f"changed spec needs one appended revision note: {old['row_id']}",
        )
        declared_changes = new_revisions[-1]["changed_fields"]
        for actual in actual_changes:
            require(
                any(
                    actual == declared or actual.startswith(f"{declared}/")
                    for declared in declared_changes
                ),
                f"spec revision omits a changed field: {old['row_id']}",
            )
        for declared in declared_changes:
            require(
                any(
                    actual == declared or actual.startswith(f"{declared}/")
                    for actual in actual_changes
                ),
                f"spec revision names an unchanged field: {old['row_id']}",
            )
    for entry in current_entries[len(previous_entries) :]:
        require(
            entry["spec_revisions"] == [],
            f"new benchmark row must start without revisions: {entry['row_id']}",
        )


def validate_history(records: list[dict[str, Any]]) -> None:
    """Validate record sets and enforce the unexplained-gap alarm."""

    require(bool(records), "history must contain at least one record")
    sets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    run_registry_shas: dict[str, set[str]] = defaultdict(set)
    seen_row_runs = set()
    for record in records:
        public_record = {
            key: value
            for key, value in record.items()
            if not key.startswith("_")
        }
        require(
            set(public_record) == HISTORY_KEYS,
            "history record keys have drifted",
        )
        require(
            is_sha256(record["evaluated_at_run"]), "invalid evaluation run SHA"
        )
        require(
            is_sha256(record["registry_sha"]), "invalid history registry SHA"
        )
        require(
            isinstance(record["row_id"], str) and record["row_id"],
            "history record is missing row_id",
        )
        row_id = record["row_id"]
        require(
            record["gap_class"] in GAP_CLASSES, f"invalid gap class: {row_id}"
        )
        require(
            record["gap_class"] != "unexplained",
            f"unexplained benchmark gap: {row_id}",
        )
        require(
            isinstance(record["gap_note"], str) and record["gap_note"].strip(),
            f"missing gap note: {row_id}",
        )
        require(
            is_one_sentence(record["gap_note"]),
            f"gap note must be one sentence: {row_id}",
        )
        require(
            set(record["our"]) == {"unit", "value"}
            and isinstance(record["our"]["unit"], str)
            and record["our"]["unit"].strip()
            and is_measurement_value(record["our"]["value"]),
            f"invalid our value: {row_id}",
        )
        require(
            set(record["published"]) == {"unit", "value"}
            and isinstance(record["published"]["unit"], str)
            and record["published"]["unit"].strip()
            and is_measurement_value(record["published"]["value"]),
            f"invalid published value: {row_id}",
        )
        require(
            isinstance(record["deviation"], dict)
            and record["deviation"]
            and any_numeric_leaf(record["deviation"]),
            f"missing deviation: {row_id}",
        )
        require(
            isinstance(record["label_state"], dict)
            and set(record["label_state"]) == LABEL_STATE_KEYS,
            f"invalid label state: {row_id}",
        )
        label_state = record["label_state"]
        require(
            all(
                isinstance(label_state[key], bool)
                for key in (
                    "individual_administrative_truth_claim",
                    "population_alignment_claim",
                    "ratified_array_activation_asserted_by_this_matrix",
                )
            )
            and isinstance(label_state["matrix_display"], str)
            and label_state["matrix_display"].strip()
            and isinstance(label_state["ratified_array_locator"], str)
            and label_state["ratified_array_locator"].strip()
            and isinstance(
                label_state["ratified_fitting_free_exact_label_array"], list
            )
            and label_state["ratified_fitting_free_exact_label_array"]
            and (
                label_state["source_artifact_embedded_labels"] is None
                or isinstance(
                    label_state["source_artifact_embedded_labels"], list
                )
            )
            and isinstance(label_state["source_artifact_label_note"], str)
            and label_state["source_artifact_label_note"].strip(),
            f"invalid honest-label fields: {row_id}",
        )

        row_run = (record["row_id"], record["evaluated_at_run"])
        require(
            row_run not in seen_row_runs,
            "row/run SHA reused; any deviation movement without a new run SHA "
            "is a drift finding",
        )
        seen_row_runs.add(row_run)
        sets[(record["evaluated_at_run"], record["registry_sha"])].append(
            record
        )
        run_registry_shas[record["evaluated_at_run"]].add(
            record["registry_sha"]
        )

    require(
        all(len(shas) == 1 for shas in run_registry_shas.values()),
        "one run SHA cannot be reused against multiple registries",
    )

    for record_set in sets.values():
        offset_states = [
            "_byte_start" in record and "_byte_end" in record
            for record in record_set
        ]
        require(
            all(offset_states) or not any(offset_states),
            "history byte offsets must be present for every record or none",
        )
        if not any(offset_states):
            continue
        byte_starts = [record["_byte_start"] for record in record_set]
        byte_ends = [record["_byte_end"] for record in record_set]
        require(
            max(byte_ends) - min(byte_starts)
            == sum(
                end - start
                for start, end in zip(byte_starts, byte_ends, strict=True)
            ),
            "each evaluation record set must be contiguous",
        )


def validate_history_against_registry(
    records: list[dict[str, Any]],
    registry: dict[str, Any],
    registry_sha: str,
) -> None:
    """Check each historical block against the append-mostly row prefix."""

    validate_history(records)
    validate_registry(registry)
    row_order = [entry["row_id"] for entry in registry["entries"]]
    record_sets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(
        list
    )
    for record in records:
        record_sets[
            (record["evaluated_at_run"], record["registry_sha"])
        ].append(record)
    for (_, set_registry_sha), record_set in record_sets.items():
        record_ids = [record["row_id"] for record in record_set]
        require(
            record_ids == row_order[: len(record_ids)],
            "evaluation record set must follow a complete registry prefix",
        )
        if set_registry_sha == registry_sha:
            require(
                record_ids == row_order,
                "current-registry evaluation must contain every active row",
            )


def validate_append_only_history(
    previous_raw: bytes, current_raw: bytes
) -> None:
    """Reject every rewrite, reorder, or truncation of committed history."""

    require(
        current_raw.startswith(previous_raw),
        "history is append-only; prior committed bytes must remain a prefix",
    )


def latest_records(
    records: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Return the last appended record for each row."""

    latest = {}
    for record in records:
        latest[record["row_id"]] = record
    return latest
