"""Content-addressed records for a2-ratified-1 §17.6; no model execution."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import fields, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

SPECIFICATION_PATH = Path("docs/design/urban2010_track_a_v2.md")
SPECIFICATION_SHA256 = (
    "d344764c4d812333f7c48dfc85c4d97183816b2ec51ebb86fbcb6995f9a916ba"
)
SPECIFICATION_VERSION = "a2-ratified-1"
INVENTED_HEADER = "INVENTED DATA - NOT A COMPARISON"
REGISTERED_HEADER = (
    "registered, one-shot, post hoc, not blind; PSID-seeded closed cohort; "
    "Python oracle (not Axiom)"
)


def canonical_bytes(value: Any) -> bytes:
    """Canonical JSON is independent of mapping insertion order (§17.6)."""
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def object_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def normalized_parameters(value: Any) -> Any:
    """Canonicalize exact runtime fields, including tuple keys and arrays."""
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: normalized_parameters(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {
            "mapping": [
                [normalized_parameters(key), normalized_parameters(item)]
                for key, item in sorted(
                    value.items(), key=lambda pair: repr(pair[0])
                )
            ]
        }
    if isinstance(value, (tuple, list)):
        return [normalized_parameters(item) for item in value]
    if hasattr(value, "tolist"):
        return normalized_parameters(value.tolist())
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError(
        f"unsupported frozen parameter type {type(value).__name__}"
    )


def runtime_parameter_bundle(inputs) -> dict[str, Any]:
    """Bind all effective parameter bundles actually supplied to projection."""
    return {
        name: normalized_parameters(getattr(inputs, name))
        for name in (
            "params",
            "baseline",
            "di_rates",
            "population_mortality",
            "claiming_pmf",
        )
    }


def file_record(path: Path, *, root: Path) -> dict[str, str | int]:
    """Hash explicit files only; never discover or load a data population."""
    path = Path(path)
    actual = path if path.is_absolute() else root / path
    raw = actual.read_bytes()
    try:
        name = str(actual.resolve().relative_to(root.resolve()))
    except ValueError:
        name = str(actual.resolve())
    return {
        "path": name,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw),
    }


def parameter_block(path: Path) -> dict[str, Any]:
    """Extract exactly A1/E1 §21, with no outcome or artifact access."""
    match = re.search(
        r"## 21\. Machine-readable parameter block.*?```json\n(.*?)\n```",
        path.read_text(encoding="utf-8"),
        flags=re.S,
    )
    if match is None:
        raise ValueError(f"no section 21 JSON parameter block: {path}")
    result = json.loads(match.group(1))
    if not isinstance(result, dict):
        raise ValueError("parameter block must be an object")
    return result


def source_records() -> dict[str, Any]:
    """Pin the spec's source records without claiming archived bytes read.

    §17.6 is silent on a missing POMS archive. Conservatively retain the
    §4.1/Appendix B provenance verbatim as metadata; actual source files,
    when supplied, are hashed separately and must match these pins.
    """
    return {
        "statute": {
            "source": "42 USC 415(b)(2)",
            "release_point": "119-100",
            "expression_date": "2026-06-26",
            "sha256": (
                "5b41d1cdacd39f4c49da7cf41dbbf22e1ea29b125be7105ca2daa12292e06eae"
            ),
            "path_from_evidence_root": (
                "parallel-oasdi-20260920/encoder-recovery/"
                "unsigned-415-b-reviewed-runtime-r4/candidate/"
                "_eval_workspaces/codex-gpt-5.6-terra/us-statute-42-415-b/"
                "workspace/source.txt"
            ),
        },
        "poms": {
            "RS 00615.260": {
                "url": "https://secure.ssa.gov/poms.nsf/lnx/0300615260",
                "transmittal": "TN 42",
                "retrieved": "2026-09-27",
                "historical_raw_page_sha256": (
                    "d938b1f5f4a13903fd7004326a3c8cf305d9a72af958551d900e5a132951f72c"
                ),
                "archived_bytes_independently_rehashed": False,
            },
            "GN 00204.035": {
                "url": "https://secure.ssa.gov/poms.nsf/lnx/0200204035",
                "transmittal": "TN 166",
                "retrieved": "2026-09-27",
                "historical_raw_page_sha256": (
                    "a935727e4fda4b4f18906a6530aba109a5a396fff21c3d19b50d842bf7fb01da"
                ),
                "archived_bytes_independently_rehashed": False,
            },
        },
    }


def build_manifest(
    *,
    root: Path,
    implementation: Sequence[Path],
    inputs: Mapping[str, Path],
    parameter_bundles: Mapping[str, Any],
    invented: bool,
    source_files: Mapping[str, Path] | None = None,
) -> dict[str, Any]:
    """Emit every §17.6 category, binding bytes and canonical parameter data."""
    if not implementation or not inputs or not parameter_bundles:
        raise ValueError(
            "implementation, inputs and parameter bundles required"
        )
    specification = file_record(SPECIFICATION_PATH, root=root)
    if specification["sha256"] != SPECIFICATION_SHA256:
        raise ValueError("specification does not match a2-ratified-1")
    sources = source_records()
    supplied_sources = {
        name: file_record(path, root=root)
        for name, path in sorted((source_files or {}).items())
    }
    pins = {
        "statute": sources["statute"]["sha256"],
        **{
            name: record["historical_raw_page_sha256"]
            for name, record in sources["poms"].items()
        },
    }
    for name, record in supplied_sources.items():
        if name not in pins or record["sha256"] != pins[name]:
            raise ValueError(
                f"source bytes differ from registered pin: {name}"
            )
    if not invented and "statute" not in supplied_sources:
        raise ValueError("registered manifest requires statute source bytes")
    blocks = {}
    for name, path in (
        ("A1", Path("docs/design/urban2010_cola_comparison.md")),
        ("E1", Path("docs/design/urban2010_fra68_comparison.md")),
    ):
        block = parameter_block(root / path)
        blocks[name] = {
            "source": file_record(path, root=root),
            "sha256": object_sha256(block),
            "block": block,
        }
    manifest = {
        "header": INVENTED_HEADER if invented else REGISTERED_HEADER,
        "schema": "track-a-v2-hash-manifest-1",
        "specification": specification,
        "implementation": [
            file_record(path, root=root)
            for path in sorted(set(implementation), key=str)
        ],
        "inputs": {
            name: file_record(path, root=root)
            for name, path in sorted(inputs.items())
        },
        "parameter_bundles": {
            name: {"sha256": object_sha256(bundle), "bundle": bundle}
            for name, bundle in sorted(parameter_bundles.items())
        },
        "parameter_blocks": blocks,
        "source_records": sources,
        "source_records_sha256": object_sha256(sources),
        "source_files": supplied_sources,
    }
    return {**manifest, "manifest_sha256": object_sha256(manifest)}


def verify_manifest(manifest: Mapping[str, Any], *, root: Path) -> None:
    """Refuse stale content addresses before any input is loaded (§11)."""
    if manifest.get("schema") != "track-a-v2-hash-manifest-1":
        raise ValueError("unrecognized hash manifest schema")
    content = {k: v for k, v in manifest.items() if k != "manifest_sha256"}
    if manifest.get("manifest_sha256") != object_sha256(content):
        raise ValueError("hash manifest content differs from its digest")
    if manifest.get("specification", {}).get("sha256") != SPECIFICATION_SHA256:
        raise ValueError("hash manifest specification differs")
    for category in ("implementation", "inputs", "parameter_bundles"):
        if not manifest.get(category):
            raise ValueError(f"empty hash manifest category: {category}")
    records = [
        manifest["specification"],
        *manifest["implementation"],
        *manifest["inputs"].values(),
        *manifest.get("source_files", {}).values(),
    ]
    if set(manifest.get("parameter_blocks", {})) != {"A1", "E1"}:
        raise ValueError("manifest requires both A1 and E1 parameter blocks")
    for block in manifest["parameter_blocks"].values():
        records.append(block["source"])
        if object_sha256(block["block"]) != block["sha256"]:
            raise ValueError("parameter block digest differs")
        if parameter_block(root / block["source"]["path"]) != block["block"]:
            raise ValueError(
                "parameter block differs from specification source"
            )
    for bundle in manifest["parameter_bundles"].values():
        if object_sha256(bundle["bundle"]) != bundle["sha256"]:
            raise ValueError("parameter bundle digest differs")
    if manifest.get("source_records") != source_records():
        raise ValueError(
            "source records differ from the ratified specification"
        )
    if manifest.get("source_records_sha256") != object_sha256(
        source_records()
    ):
        raise ValueError("source records digest differs")
    source_pins = {
        "statute": source_records()["statute"]["sha256"],
        **{
            name: record["historical_raw_page_sha256"]
            for name, record in source_records()["poms"].items()
        },
    }
    for name, record in manifest.get("source_files", {}).items():
        if name not in source_pins or record["sha256"] != source_pins[name]:
            raise ValueError(
                f"source bytes differ from registered pin: {name}"
            )
    for record in records:
        if file_record(Path(record["path"]), root=root) != record:
            raise ValueError(
                f"file differs from hash manifest: {record['path']}"
            )
