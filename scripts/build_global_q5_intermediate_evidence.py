#!/usr/bin/env python3
"""Build non-authority source evidence for the blocked global Q5 closure.

Section 19.3.3 permits only one canonical Q5 artifact.  That artifact embeds
the complete Class-B field-source derivation, which this Class-A-only lane is
forbidden to emit.  This builder therefore stops at independently
reproducible prerequisites: the 257-document source denominator, all 10,190
questionnaire page digests, the three design-fixed relationship sentinels,
and era-sliced lower-bound evidence.  It never writes the canonical Q5 path
and never represents the fixed three-row subset as the complete ``R_Q``.
"""

from __future__ import annotations

import argparse
import copy
import decimal
import hashlib
import json
import math
import subprocess
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from populace_dynamics.data import (  # noqa: E402
    psid_questionnaire_inventory as questionnaire_inventory,
)

CATALOG_PATH = (
    ROOT
    / "docs"
    / "analysis"
    / "global_q5_evidence"
    / "global_relationship_catalog_evidence_v1.json"
)
ERA_OUTPUT_DIRECTORY = CATALOG_PATH.parent
ABSENCE_STOP_PATH = (
    ERA_OUTPUT_DIRECTORY / "global_absence_domain_stop_evidence_v1.json"
)
CANONICAL_Q5_PATH = (
    ROOT
    / "data"
    / "external"
    / "psid_questionnaire_slot_closure_evidence_v1.json"
)
DEFAULT_CAPTURE_ROOT = (
    Path("~/PolicyEngine/psid-data").expanduser()
    / "documentation"
    / "capture1"
)

EVIDENCE_FORMAT = "global_q5_non_authority_intermediate_evidence.v1"
CANONICALIZATION = "python-json-sort-keys-compact-ascii-no-nan-lf-v1"
BLOCKED_STATUS = "blocked_non_authority_intermediate"
DESIGN_BINDING = {
    "path": "docs/design/covered_earnings_correction.md",
    "ratification_commit": "985be84fdeec70ffd20aa1e60dec7d300b7a555b",
    "revision": 7,
    "blob_sha256": (
        "8f90dd1aee59e6857418d2a73b617e5cb3991eba3a237a78303586a8c2a9debc"
    ),
}

FROZEN_INPUTS = {
    "questionnaire_corpus_root": {
        "path": (
            "data/external/"
            "psid_questionnaire_corpus_authority_registration_attempt_v1.json"
        ),
        "byte_size": 520_656,
        "raw_sha256": (
            "07c5bad57d702416da7ee668f504646ba85b9868a7f38819cdec85638c97558c"
        ),
        "schema_version": (
            "psid_questionnaire_corpus_authority_registration_attempt.v1"
        ),
    },
    "field_corpus_root": {
        "path": (
            "data/external/"
            "psid_questionnaire_dictionary_inventory_registration_required_v1.json"
        ),
        "byte_size": 25_474_435,
        "raw_sha256": (
            "a974c6fb65a9f3d52387163f2e98b7cd8cfdbd57f5e95d1f766b3aa25d167ac0"
        ),
        "schema_version": (
            "psid_questionnaire_dictionary_inventory.registration_required.v1"
        ),
    },
    "residual_evidence": {
        "path": "data/external/psid_codebook_inventory_adjudication_v1.json",
        "byte_size": 1_415_319,
        "raw_sha256": (
            "df73026bcf649d12ecb606501d64780f41567b6dc09d7029f9191111cab09c62"
        ),
        "schema_version": "psid_codebook_inventory_adjudication.v1",
    },
}

INTERVIEW_WAVES = tuple(range(1968, 1998)) + (
    1999,
    2001,
    2003,
    2005,
    2007,
    2009,
    2011,
    2013,
    2015,
    2017,
    2019,
    2021,
    2023,
)
ROLES = ("head_or_reference_person", "spouse_or_partner")
ROLE_ORDER = {
    "questionnaire_flow": 0,
    "dictionary_layout": 1,
    "codebook": 2,
    "raw_fixed_width_data": 3,
}
FIELD_ROLE_MAP = {
    "stata_setup": "dictionary_layout",
    "spss_setup": "dictionary_layout",
    "family_codebook": "codebook",
    "stata_value_labels": "codebook",
    "spss_value_labels": "codebook",
    "raw_fixed_width": "raw_fixed_width_data",
}

ERA_SPECS = (
    {
        "era_id": "wave1968_ry1968_1974_early_totals",
        "interview_waves": tuple(range(1968, 1976)),
        "residual_ids": (
            "wave1968_ry1968_1974_early_totals:questionnaire_slot_closure",
            "wave1968_ry1968_1974_early_totals:unsupported_job_context_absence_proofs",
        ),
        "residual_source_indices": (1, 2),
        "questionnaire_document_count": 16,
        "questionnaire_page_count": 842,
    },
    {
        "era_id": "ry1975_1977_spouse_concept_seam",
        "interview_waves": (1976, 1977, 1978),
        "residual_ids": (
            "ry1975_1977_spouse_concept_seam:questionnaire_slot_closure",
        ),
        "residual_source_indices": (5,),
        "questionnaire_document_count": 6,
        "questionnaire_page_count": 408,
    },
    {
        "era_id": "ry1978_1992_pre_er_totals",
        "interview_waves": tuple(range(1979, 1994)),
        "residual_ids": (
            "ry1978_1992_pre_er_totals:questionnaire_slot_closure",
        ),
        "residual_source_indices": (11,),
        "questionnaire_document_count": 29,
        "questionnaire_page_count": 3_349,
    },
    {
        "era_id": "ry1993_2001_er_transition",
        "interview_waves": (1994, 1995, 1996, 1997, 1999, 2001),
        "residual_ids": (
            "ry1993_2001_er_transition:questionnaire_slot_closure",
        ),
        "residual_source_indices": (14,),
        "questionnaire_document_count": 12,
        "questionnaire_page_count": 1_622,
    },
    {
        "era_id": "ry2002_2014_modern_bc_de",
        "interview_waves": (2003, 2005, 2007, 2009, 2011, 2013, 2015),
        "residual_ids": (
            "ry2002_2014_modern_bc_de:questionnaire_slot_closure",
        ),
        "residual_source_indices": (18,),
        "questionnaire_document_count": 14,
        "questionnaire_page_count": 2_337,
    },
    {
        "era_id": "ry2015_2022_exclusion_lineage",
        "interview_waves": (2017, 2019, 2021, 2023),
        "residual_ids": (
            "ry2015_2022_exclusion_lineage:questionnaire_slot_closure",
        ),
        "residual_source_indices": (26,),
        "questionnaire_document_count": 4,
        "questionnaire_page_count": 1_632,
    },
)
ERA_BY_ID = {row["era_id"]: row for row in ERA_SPECS}

EXPECTED_WAVE_DOMAIN_SHA256 = (
    "b681b78ebc82110e24fb73878b1a2b72b6bee7924ea3db1413f7acd68e163fda"
)
EXPECTED_U_KEYSET_SHA256 = (
    "8b7cad855b791c5cd7d235a74d4a0f1ecc7511dc0458db11d6b04c1b6af2c36a"
)
EXPECTED_U_DOMAIN_SHA256 = (
    "9d7a98db7c2889eba150f70935f492aebbc41cd521e4139dc1ec886ecd9945ce"
)
EXPECTED_QUESTIONNAIRE_KEYSET_SHA256 = (
    "3326c9ba70b7f83f19b0ea934630d26ced73f230be1628cb74031d17160cb1a5"
)
EXPECTED_QUESTIONNAIRE_DOMAIN_SHA256 = (
    "b06139b147391d06b4f90a8f28de472a936ec08b3e9eb37001a5a70e2b3c3543"
)
EXPECTED_UPSTREAM_QUESTIONNAIRE_ID_SHA256 = (
    "b4bde71544911441e1c1d05e5ad00d282384a98747627ee19d056dd3ce174293"
)
EXPECTED_CLASS_A_DIGEST = (
    "458c3e184e247b35d524b6800a6333eb1821b905f95322cb09aa5b90c9640b5b"
)
CLASS_A_RESIDUAL_ROWS = (
    (
        1,
        "wave1968_ry1968_1974_early_totals:questionnaire_slot_closure",
        "8b133338fda147b9b48bbc4e48b4cacc7c71eab4879b0adcb2b3adef6cb3835e",
    ),
    (
        2,
        "wave1968_ry1968_1974_early_totals:unsupported_job_context_absence_proofs",
        "3a2901825d71ece3e09df3bb80ddc627f30b7fce06e5415b780e14a5abfae8bb",
    ),
    (
        5,
        "ry1975_1977_spouse_concept_seam:questionnaire_slot_closure",
        "a8d3111af3a84318ce4b0292c9521e4a32c62fb9463cc4e67aa0ed1bcc8339b3",
    ),
    (
        11,
        "ry1978_1992_pre_er_totals:questionnaire_slot_closure",
        "fd3bc863c0775cf05bfe96e0690cf8623e11337207f68f6b8ab826642278a038",
    ),
    (
        14,
        "ry1993_2001_er_transition:questionnaire_slot_closure",
        "c3c6e342db0c7c179ae53e3aa5f1e3b38fcda0a8bd3dab6839d4d3cf7323eb98",
    ),
    (
        18,
        "ry2002_2014_modern_bc_de:questionnaire_slot_closure",
        "5a779f1d6f1e67bfa3d470d3884f2acba15aa98c5fb6397107a19c370f444325",
    ),
    (
        26,
        "ry2015_2022_exclusion_lineage:questionnaire_slot_closure",
        "dbb2de2ee9f4b82db6ce26e35a26e5489f9efab8e5661b038af2217e457349d2",
    ),
)

PAGE_IMPLEMENTATION = {
    "path": "src/populace_dynamics/data/psid_questionnaire_inventory.py",
    "source_commit": "c1899c9e3f156c411a6e62d2d9b57514c0d6bb2e",
    "tree_mode": "100644",
    "blob_oid": "e461d69cdec35f0ef795a097ac0b9ab9a8f9eaf0",
    "byte_size": 205_550,
    "raw_sha256": (
        "b742fb14d62411ed1072cf320ad7cff0b3397a5a7255584964bac4995b6acbee"
    ),
    "function_name": "_pdftotext_pages",
    "tool": "Poppler pdftotext",
    "version": "26.04.0",
    "arguments": ["-layout", "-enc", "UTF-8"],
    "encoding": "UTF-8",
    "page_split": "form_feed",
    "terminal_page_rule": (
        "remove_exactly_one_terminal_whitespace_only_page_if_present"
    ),
}


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize under the section 10.1 canonical JSON law."""

    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )


def strict_parse_document(raw: bytes, label: str) -> Any:
    """Parse uniquely encoded finite JSON and reject duplicate keys."""

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"{label} contains duplicate key {key!r}")
            result[key] = value
        return result

    def reject_constant(token: str) -> Any:
        raise ValueError(f"{label} contains non-finite constant {token}")

    def finite_float(token: str) -> float:
        value = float(token)
        if not math.isfinite(value):
            raise ValueError(f"{label} contains non-finite number {token}")
        if decimal.Decimal(token) != decimal.Decimal(str(value)):
            raise ValueError(f"{label} contains inexact number {token}")
        return value

    try:
        text = raw.decode("utf-8")
        if text.startswith("\ufeff"):
            raise ValueError(f"{label} contains a leading BOM")
        return json.loads(
            text,
            object_pairs_hook=unique_object,
            parse_constant=reject_constant,
            parse_float=finite_float,
        )
    except (
        UnicodeError,
        ValueError,
        OverflowError,
        RecursionError,
        decimal.DecimalException,
    ) as error:
        raise ValueError(
            f"{label} is not a uniquely parseable JSON document"
        ) from error


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical_digest(value: Any) -> str:
    return _sha256(canonical_json_bytes(value))


def _content_sha256(value: Mapping[str, Any]) -> str:
    preimage = copy.deepcopy(value)
    preimage["integrity"]["content_sha256"] = "0" * 64
    return _canonical_digest(preimage)


def _native_field_root_bytes(value: Mapping[str, Any]) -> bytes:
    preimage = copy.deepcopy(value)
    preimage["integrity"]["content_sha256"] = "0" * 64
    return json.dumps(
        preimage,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _load_frozen_inputs() -> dict[str, Mapping[str, Any]]:
    values: dict[str, Mapping[str, Any]] = {}
    for input_id, identity in FROZEN_INPUTS.items():
        raw = (ROOT / identity["path"]).read_bytes()
        if (
            len(raw) != identity["byte_size"]
            or _sha256(raw) != identity["raw_sha256"]
        ):
            raise ValueError(f"{input_id} frozen identity drift")
        value = strict_parse_document(raw, input_id)
        if not isinstance(value, Mapping):
            raise ValueError(f"{input_id} is not an object")
        if value.get("schema_version") != identity["schema_version"]:
            raise ValueError(f"{input_id} schema identity drift")
        values[input_id] = value

    field_root = values["field_corpus_root"]
    if (
        _sha256(_native_field_root_bytes(field_root))
        != field_root["integrity"]["content_sha256"]
        or field_root["integrity"]["content_sha256"]
        != "f1f13d9de7dcb2c8a26beafbc60a32390b5a5fb644abb68aeee8df3a5cd1b557"
        or field_root["integrity"]["reproduced_from_source_bytes"] is not False
        or field_root["inventory_ratification_abort"]["status"]
        != "registration_required"
    ):
        raise ValueError("historical field-root identity drift")
    residual_rows = values["residual_evidence"].get(
        "registration_required_residuals"
    )
    if not isinstance(residual_rows, list) or len(residual_rows) != 32:
        raise ValueError("residual-evidence denominator drift")
    residual_ids: list[str] = []
    for index, residual_id, row_sha256 in CLASS_A_RESIDUAL_ROWS:
        row = residual_rows[index]
        if (
            row.get("residual_id") != residual_id
            or _canonical_digest(row) != row_sha256
        ):
            raise ValueError(f"Class-A residual row {index} drift")
        residual_ids.append(residual_id)
    if _canonical_digest(residual_ids) != EXPECTED_CLASS_A_DIGEST:
        raise ValueError("Class-A residual domain digest drift")
    return values


def _verify_design_binding() -> None:
    worktree = (ROOT / DESIGN_BINDING["path"]).read_bytes()
    ratified = subprocess.run(
        [
            "git",
            "show",
            (
                f"{DESIGN_BINDING['ratification_commit']}:"
                f"{DESIGN_BINDING['path']}"
            ),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout
    if (
        worktree != ratified
        or _sha256(worktree) != DESIGN_BINDING["blob_sha256"]
    ):
        raise ValueError("revision-7 design binding drift")


def _source_artifact_identities() -> list[dict[str, Any]]:
    return [
        {"source_artifact_id": input_id, **identity}
        for input_id, identity in FROZEN_INPUTS.items()
    ]


def _safe_relative_path(value: str) -> Path:
    path = Path(value)
    if (
        not value
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ValueError(f"unsafe source path {value!r}")
    return path


def _verified_file(path: Path, size: int, sha256: str, label: str) -> bytes:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"{label} is unavailable or symlinked")
    raw = path.read_bytes()
    if len(raw) != size or _sha256(raw) != sha256:
        raise ValueError(f"{label} staged identity drift")
    return raw


def _verify_capture_inputs(
    registration: Mapping[str, Any], capture_root: Path
) -> dict[str, Any]:
    identities = registration.get("capture_input_identities")
    if not isinstance(identities, list) or len(identities) != 4:
        raise ValueError("questionnaire capture-input domain drift")
    values: dict[str, Any] = {}
    for row in identities:
        if set(row) != {"capture_input_id", "locator"}:
            raise ValueError("capture-input row schema drift")
        locator = row["locator"]
        filename = locator["filename"]
        if Path(filename).name != filename:
            raise ValueError("unsafe capture-input filename")
        raw = _verified_file(
            capture_root / filename,
            locator["size_bytes"],
            locator["full_file_sha256"],
            row["capture_input_id"],
        )
        if (
            locator["byte_start"] != 0
            or locator["byte_end"] != len(raw)
            or locator["range_sha256"] != _sha256(raw)
        ):
            raise ValueError("capture-input locator drift")
        values[row["capture_input_id"]] = (
            strict_parse_document(raw, row["capture_input_id"])
            if filename.endswith(".json")
            else raw
        )
    return values


def _core_basename(wave: int) -> str:
    return f"q{wave % 100:02d}.pdf" if wave <= 1997 else f"q{wave}.pdf"


def _project_questionnaire_sources(
    registration: Mapping[str, Any], capture_root: Path
) -> tuple[
    list[dict[str, Any]],
    dict[str, Mapping[str, Any]],
    dict[str, Any],
]:
    accepted = registration.get("accepted_authority_registry")
    candidates = registration.get("document_candidates")
    if (
        registration.get("registration_status") != "pass"
        or registration.get("document_candidate_count") != 456
        or registration.get("verified_document_count") != 456
        or registration.get("failed_document_count") != 0
        or registration.get("failed_document_ids") != []
        or not isinstance(accepted, Mapping)
        or accepted.get("status") != "pass"
        or accepted.get("document_count") != 456
        or not isinstance(candidates, list)
        or len(candidates) != 456
    ):
        raise ValueError("accepted questionnaire registry drift")

    capture_inputs = _verify_capture_inputs(registration, capture_root)
    links = capture_inputs.get("source_link_inventory")
    if not isinstance(links, list) or len(links) != 465:
        raise ValueError("source-link inventory domain drift")
    if any(set(row) != {"href", "text", "row"} for row in links):
        raise ValueError("source-link inventory row schema drift")

    documents_by_id = {row["source_document_id"]: row for row in candidates}
    if len(documents_by_id) != 456:
        raise ValueError("accepted document IDs are not unique")
    documents_by_url: dict[str, list[Mapping[str, Any]]] = {}
    for row in candidates:
        documents_by_url.setdefault(row["source_url"], []).append(row)

    first_by_href: dict[str, tuple[int, Mapping[str, Any]]] = {}
    for position, row in enumerate(links, start=1):
        first_by_href.setdefault(row["href"], (position, row))
        joined = documents_by_url.get(row["href"], [])
        if len(joined) != 1:
            raise ValueError("source-link occurrence does not join uniquely")
    for href, (position, link) in first_by_href.items():
        document = documents_by_url[href][0]
        if (
            document["first_link_position"] != position
            or document["source_link_text"] != link["text"]
        ):
            raise ValueError("stable-first accepted-document join drift")

    selected_by_url: dict[str, int] = {}
    for wave in INTERVIEW_WAVES:
        core = (
            "https://psidonline.isr.umich.edu/documents/psid/questionnaires/"
            + _core_basename(wave)
        )
        core_rows = [
            (index, row)
            for index, row in enumerate(links, start=1)
            if row == {"href": core, "text": "Questionnaire", "row": ""}
        ]
        if len(core_rows) != 1:
            raise ValueError(f"wave {wave} core questionnaire drift")
        selected_by_url[core] = wave

        qxq = (
            "https://psidonline.isr.umich.edu/data/Documentation/Fam/"
            f"{wave}/QxQs.pdf"
        )
        qxq_rows = [
            row
            for row in links
            if row == {"href": qxq, "text": "QxQ", "row": ""}
        ]
        if len(qxq_rows) > 1:
            raise ValueError(f"wave {wave} QxQ duplicate")
        if qxq_rows:
            selected_by_url[qxq] = wave
    if len(selected_by_url) != 81:
        raise ValueError("global questionnaire projection is not 81 rows")

    out_url = (
        "https://psidonline.isr.umich.edu/documents/psid/questionnaires/"
        "q2025.pdf"
    )
    out_links = [
        row
        for row in links
        if row == {"href": out_url, "text": "Questionnaire", "row": ""}
    ]
    if len(out_links) != 1:
        raise ValueError("2025 out-of-domain row drift")

    link_dispositions: list[dict[str, Any]] = []
    for position, row in enumerate(links, start=1):
        if row["href"] in selected_by_url and row["row"] == "":
            disposition = "included_family_questionnaire_flow"
        elif row == out_links[0]:
            disposition = "excluded_out_of_wave_2025_family_questionnaire"
        else:
            disposition = "excluded_not_family_questionnaire_flow"
        link_dispositions.append(
            {"link_position": position, "disposition": disposition}
        )
    if Counter(row["disposition"] for row in link_dispositions) != {
        "included_family_questionnaire_flow": 81,
        "excluded_out_of_wave_2025_family_questionnaire": 1,
        "excluded_not_family_questionnaire_flow": 383,
    }:
        raise ValueError("link-side disposition counts drift")

    document_dispositions: list[dict[str, Any]] = []
    for document in candidates:
        url = document["source_url"]
        if url in selected_by_url:
            disposition = "included_family_questionnaire_flow"
        elif url == out_url:
            disposition = "excluded_out_of_wave_2025_family_questionnaire"
        else:
            disposition = "excluded_not_family_questionnaire_flow"
        document_dispositions.append(
            {
                "source_document_id": document["source_document_id"],
                "disposition": disposition,
            }
        )
    if Counter(row["disposition"] for row in document_dispositions) != {
        "included_family_questionnaire_flow": 81,
        "excluded_out_of_wave_2025_family_questionnaire": 1,
        "excluded_not_family_questionnaire_flow": 374,
    }:
        raise ValueError("accepted-document disposition counts drift")

    projected: list[dict[str, Any]] = []
    upstream_ids: list[str] = []
    for position, link in enumerate(links, start=1):
        if link["href"] not in selected_by_url:
            continue
        document = documents_by_url[link["href"]][0]
        if (
            position != document["first_link_position"]
            or document["availability"] != "verified"
            or document["source_link_text"] != link["text"]
            or document["source_page_row"] != ""
        ):
            raise ValueError("included questionnaire registry join drift")
        filename = document["on_disk_filename"]
        if (
            document["digest_row_filename"] != filename
            or document["locator"]["filename"] != filename
            or Path(filename).name != filename
        ):
            raise ValueError("included questionnaire filename drift")
        raw = _verified_file(
            capture_root / filename,
            document["expected_size_bytes"],
            document["expected_sha256"],
            document["source_document_id"],
        )
        wave = selected_by_url[link["href"]]
        canonical_path = f"documentation/capture1/{filename}"
        row = {
            "source_document_id": "",
            "document_role": "questionnaire_flow",
            "interview_waves": [wave],
            "canonical_source_path": canonical_path,
            "storage_disposition": "external_registered_file",
            "storage_identity": {
                "authority_registry_id": (
                    "psid_questionnaire_corpus_authority_registry.v1"
                ),
                "document_id": document["source_document_id"],
                "registered_path": canonical_path,
            },
            "byte_size": len(raw),
            "sha256": _sha256(raw),
        }
        row["source_document_id"] = (
            "psid-source-document:"
            + _canonical_digest(
                [
                    row["document_role"],
                    row["interview_waves"],
                    canonical_path,
                    row["byte_size"],
                    row["sha256"],
                ]
            )
        )
        projected.append(row)
        upstream_ids.append(document["source_document_id"])

    if (
        _canonical_digest(upstream_ids)
        != EXPECTED_UPSTREAM_QUESTIONNAIRE_ID_SHA256
    ):
        raise ValueError("upstream questionnaire ID projection drift")
    disposition_evidence = {
        "source_link_disposition_rows": link_dispositions,
        "source_link_disposition_domain_sha256": _canonical_digest(
            link_dispositions
        ),
        "accepted_document_disposition_rows": document_dispositions,
        "accepted_document_disposition_domain_sha256": _canonical_digest(
            document_dispositions
        ),
        "included_upstream_document_ids_source_order_sha256": (
            _canonical_digest(upstream_ids)
        ),
    }
    return projected, documents_by_id, disposition_evidence


def _project_field_sources(
    field_root: Mapping[str, Any], psid_root: Path
) -> list[dict[str, Any]]:
    manifest = field_root.get("source_authority_manifest")
    if (
        field_root.get("interview_waves") != list(INTERVIEW_WAVES)
        or not isinstance(manifest, list)
        or len(manifest) != 176
        or field_root["evidence_summary"]["source_authority_manifest_sha256"]
        != "52906f7a36955d20282dbce2dd4bac260395d3ce3961bd0baf763290c3152116"
    ):
        raise ValueError("field manifest denominator drift")
    native_manifest = json.dumps(
        manifest,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    if (
        _sha256(native_manifest)
        != field_root["evidence_summary"]["source_authority_manifest_sha256"]
    ):
        raise ValueError("field manifest native digest drift")

    rows: list[dict[str, Any]] = []
    for source in manifest:
        role = FIELD_ROLE_MAP.get(source["dictionary_role"])
        if role is None or source["interview_wave"] not in INTERVIEW_WAVES:
            raise ValueError("field manifest role/wave drift")
        relative = _safe_relative_path(source["path"])
        raw = _verified_file(
            psid_root / relative,
            source["size_bytes"],
            source["sha256"],
            source["document_id"],
        )
        row = {
            "source_document_id": "",
            "document_role": role,
            "interview_waves": [source["interview_wave"]],
            "canonical_source_path": source["path"],
            "storage_disposition": "external_registered_file",
            "storage_identity": {
                "authority_registry_id": (
                    "psid_questionnaire_dictionary_inventory."
                    "registration_required.v1"
                ),
                "document_id": source["document_id"],
                "registered_path": source["path"],
            },
            "byte_size": len(raw),
            "sha256": _sha256(raw),
        }
        row["source_document_id"] = (
            "psid-source-document:"
            + _canonical_digest(
                [
                    role,
                    row["interview_waves"],
                    source["path"],
                    len(raw),
                    row["sha256"],
                ]
            )
        )
        rows.append(row)
    return rows


def _source_order(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        ROLE_ORDER[row["document_role"]],
        row["interview_waves"][0],
        row["canonical_source_path"].encode("utf-8"),
        row["source_document_id"],
    )


def _source_denominator(
    inputs: Mapping[str, Mapping[str, Any]], capture_root: Path
) -> tuple[dict[str, Any], dict[str, Mapping[str, Any]]]:
    questionnaire_rows, documents_by_id, dispositions = (
        _project_questionnaire_sources(
            inputs["questionnaire_corpus_root"], capture_root
        )
    )
    psid_root = capture_root.parents[1]
    field_rows = _project_field_sources(inputs["field_corpus_root"], psid_root)
    rows = sorted(questionnaire_rows + field_rows, key=_source_order)
    questionnaire_rows = [
        row for row in rows if row["document_role"] == "questionnaire_flow"
    ]
    role_counts = Counter(row["document_role"] for row in rows)
    if (
        len(rows) != 257
        or role_counts
        != {
            "questionnaire_flow": 81,
            "dictionary_layout": 86,
            "codebook": 47,
            "raw_fixed_width_data": 43,
        }
        or _canonical_digest([row["source_document_id"] for row in rows])
        != EXPECTED_U_KEYSET_SHA256
        or _canonical_digest(rows) != EXPECTED_U_DOMAIN_SHA256
        or _canonical_digest(
            [row["source_document_id"] for row in questionnaire_rows]
        )
        != EXPECTED_QUESTIONNAIRE_KEYSET_SHA256
        or _canonical_digest(questionnaire_rows)
        != EXPECTED_QUESTIONNAIRE_DOMAIN_SHA256
    ):
        raise ValueError("257-document source denominator drift")
    value = {
        "source_documents": rows,
        "source_document_count": len(rows),
        "source_document_role_counts": dict(role_counts),
        "source_document_keyset_sha256": _canonical_digest(
            [row["source_document_id"] for row in rows]
        ),
        "source_document_domain_sha256": _canonical_digest(rows),
        "questionnaire_documents": questionnaire_rows,
        "questionnaire_document_count": len(questionnaire_rows),
        "questionnaire_document_keyset_sha256": _canonical_digest(
            [row["source_document_id"] for row in questionnaire_rows]
        ),
        "questionnaire_document_domain_sha256": _canonical_digest(
            questionnaire_rows
        ),
        "upstream_disposition_evidence": dispositions,
        "canonical_order": "document_role_wave_canonical_source_path_v1",
        "source_bytes_reproduced": True,
        "status": "pass",
    }
    return value, documents_by_id


def _page_implementation_identity() -> dict[str, Any]:
    path = ROOT / PAGE_IMPLEMENTATION["path"]
    raw = path.read_bytes()
    if (
        len(raw) != PAGE_IMPLEMENTATION["byte_size"]
        or _sha256(raw) != PAGE_IMPLEMENTATION["raw_sha256"]
    ):
        raise ValueError("questionnaire page implementation drift")
    blob = subprocess.run(
        ["git", "hash-object", PAGE_IMPLEMENTATION["path"]],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if blob != PAGE_IMPLEMENTATION["blob_oid"]:
        raise ValueError("questionnaire page implementation blob drift")
    version = questionnaire_inventory._pdftotext_version()
    if version != PAGE_IMPLEMENTATION["version"]:
        raise ValueError("questionnaire page tool version drift")
    return copy.deepcopy(PAGE_IMPLEMENTATION)


def _questionnaire_page_evidence(
    denominator: Mapping[str, Any],
    documents_by_id: Mapping[str, Mapping[str, Any]],
    capture_root: Path,
) -> dict[str, Any]:
    implementation = _page_implementation_identity()
    rows: list[dict[str, Any]] = []
    for source in denominator["questionnaire_documents"]:
        upstream_id = source["storage_identity"]["document_id"]
        document = documents_by_id[upstream_id]
        filename = document["on_disk_filename"]
        pages = questionnaire_inventory._pdftotext_pages(
            capture_root / filename
        )
        wave = source["interview_waves"][0]
        digest_locator = {
            "source_document_id": upstream_id,
            "digest_row_filename": document["digest_row_filename"],
            "digest_row_number": document["digest_row_number"],
            "expected_size_bytes": document["expected_size_bytes"],
            "expected_sha256": document["expected_sha256"],
        }
        for page_number, page_text in enumerate(pages, start=1):
            page_bytes = page_text.encode("utf-8")
            page_sha256 = _sha256(page_bytes)
            page_id = "psid-questionnaire-page:" + _canonical_digest(
                [
                    source["source_document_id"],
                    wave,
                    page_number,
                    page_sha256,
                ]
            )
            rows.append(
                {
                    "questionnaire_page_id": page_id,
                    "source_document_id": source["source_document_id"],
                    "canonical_source_path": source["canonical_source_path"],
                    "corpus_digest_row_locator": digest_locator,
                    "interview_wave": wave,
                    "page_number": page_number,
                    "page_text_utf8_size_bytes": len(page_bytes),
                    "page_text_utf8_sha256": page_sha256,
                }
            )
    wave_counts = Counter(row["interview_wave"] for row in rows)
    for spec in ERA_SPECS:
        if (
            sum(wave_counts[wave] for wave in spec["interview_waves"])
            != spec["questionnaire_page_count"]
        ):
            raise ValueError(f"{spec['era_id']} page-domain drift")
    if len(rows) != 10_190:
        raise ValueError("global questionnaire page count drift")
    return {
        "questionnaire_page_text_derivation": implementation,
        "questionnaire_page_rows": rows,
        "questionnaire_page_count": len(rows),
        "questionnaire_page_keyset_sha256": _canonical_digest(
            [row["questionnaire_page_id"] for row in rows]
        ),
        "questionnaire_page_domain_sha256": _canonical_digest(rows),
        "page_annotation_scope": (
            "complete_page_text_digests_only_occurrence_annotation_not_emitted"
        ),
        "status": "pass_page_denominator_only",
    }


def _relationship_row(
    job_slot_id: str, component_slot_id: str, slot_kind: str
) -> dict[str, str]:
    relationship_id = "psid-questionnaire-relationship:" + _canonical_digest(
        [job_slot_id, component_slot_id, slot_kind]
    )
    return {
        "relationship_id": relationship_id,
        "job_slot_id": job_slot_id,
        "questionnaire_component_slot_id": component_slot_id,
        "slot_kind": slot_kind,
    }


def baseline_relationship_rows() -> list[dict[str, str]]:
    """Return the three design-fixed rows that precede source components."""

    return [
        _relationship_row(
            "psid-job-slot:role-total",
            "psid-component-slot:role-total",
            "role_total",
        ),
        _relationship_row(
            "psid-job-slot:farm-aggregate",
            "psid-component-slot:farm-aggregate",
            "farm_aggregate",
        ),
        _relationship_row(
            "psid-job-slot:business-aggregate",
            "psid-component-slot:business-aggregate",
            "business_aggregate",
        ),
    ]


def _catalog_relationship_evidence() -> dict[str, Any]:
    baselines = baseline_relationship_rows()
    return {
        "mandatory_baseline_relationship_rows": baselines,
        "mandatory_baseline_relationship_count": len(baselines),
        "mandatory_baseline_relationship_keyset_sha256": _canonical_digest(
            [row["relationship_id"] for row in baselines]
        ),
        "mandatory_baseline_relationship_domain_sha256": _canonical_digest(
            baselines
        ),
        "source_component_relationship_rows": None,
        "source_component_relationship_count": None,
        "global_relationship_rows": None,
        "global_relationship_count": None,
        "global_relationship_keyset_sha256": None,
        "global_relationship_domain_sha256": None,
        "r_q_count_equation": (
            "3_plus_complete_source_questionnaire_component_context_row_count"
        ),
        "r_q_status": "blocked_incomplete_source_occurrence_annotation",
        "blocking_annotation_members": [
            "questionnaire_occurrence_rows",
            "flow_branch_rows",
            "role_node_rows",
            "job_slot_rows",
            "questionnaire_component_slot_rows",
            "node_alias_rows",
            "complete_anchor_partitions_and_reverse_covers",
        ],
        "status": BLOCKED_STATUS,
    }


def build_catalog_evidence(
    capture_root: Path = DEFAULT_CAPTURE_ROOT,
) -> dict[str, Any]:
    """Reproduce the global source denominator and blocked R_Q evidence."""

    if CANONICAL_Q5_PATH.exists():
        raise ValueError("canonical Q5 path already exists")
    _verify_design_binding()
    inputs = _load_frozen_inputs()
    if _canonical_digest(list(INTERVIEW_WAVES)) != EXPECTED_WAVE_DOMAIN_SHA256:
        raise ValueError("43-wave domain drift")
    denominator, documents_by_id = _source_denominator(inputs, capture_root)
    page_evidence = _questionnaire_page_evidence(
        denominator, documents_by_id, capture_root
    )
    value: dict[str, Any] = {
        "evidence_format": EVIDENCE_FORMAT,
        "evidence_kind": "global_relationship_catalog_prerequisite_evidence",
        "design_binding": copy.deepcopy(DESIGN_BINDING),
        "source_artifact_identities": _source_artifact_identities(),
        "wave_domain": {
            "interview_waves": list(INTERVIEW_WAVES),
            "interview_wave_count": len(INTERVIEW_WAVES),
            "interview_wave_domain_sha256": _canonical_digest(
                list(INTERVIEW_WAVES)
            ),
        },
        "source_denominator": denominator,
        "questionnaire_page_evidence": page_evidence,
        "relationship_catalog_evidence": _catalog_relationship_evidence(),
        "authority_disposition": {
            "canonical_q5_path": str(CANONICAL_Q5_PATH.relative_to(ROOT)),
            "canonical_q5_emitted": False,
            "class_b_grammar_rows_emitted": False,
            "class_a_residual_ids_closed": [],
            "class_a_residual_source_indices_surviving": [
                1,
                2,
                5,
                11,
                14,
                18,
                26,
            ],
            "class_a_residual_domain_sha256": EXPECTED_CLASS_A_DIGEST,
            "disposition": BLOCKED_STATUS,
        },
        "stop_conditions": [
            {
                "section_19_anchor": "19.3.2_and_19.3.3_field_source_derivation",
                "blocking_members": [
                    "source_document_manifest.field_source_derivation",
                    "field_source_derivation.numeric_grammar_derivation_rows",
                    "positive_field_join_rows.raw_field_projections.numeric_grammar_derivation_id",
                    "positive_field_join_rows.raw_field_projections.numeric_grammar_derivation_sha256",
                ],
                "reason": "class_b_members_are_mandatory_inside_q5_but_forbidden_in_this_lane",
            },
            {
                "section_19_anchor": "19.8.1_walk_a_and_19.8.2_tension_9",
                "blocking_members": [
                    "2023:G13.:ER83121",
                    "2023:G13.:ER83495",
                ],
                "reason": "one_leading_question_identifier_resolves_two_raw_fields",
            },
        ],
        "integrity": {
            "canonicalization": CANONICALIZATION,
            "content_sha256": "0" * 64,
        },
        "status": BLOCKED_STATUS,
    }
    value["integrity"]["content_sha256"] = _content_sha256(value)
    validate_catalog_evidence(value)
    return value


def _validate_digest_relation(
    value: Mapping[str, Any],
    rows_key: str,
    count_key: str,
    domain_key: str,
    keyset_key: str | None = None,
    id_key: str | None = None,
) -> None:
    rows = value[rows_key]
    if not isinstance(rows, list) or value[count_key] != len(rows):
        raise ValueError(f"{rows_key} count drift")
    if value[domain_key] != _canonical_digest(rows):
        raise ValueError(f"{rows_key} domain digest drift")
    if keyset_key is not None and id_key is not None:
        ids = [row[id_key] for row in rows]
        if len(ids) != len(set(ids)) or value[keyset_key] != _canonical_digest(
            ids
        ):
            raise ValueError(f"{rows_key} keyset drift")


def validate_catalog_evidence(value: Mapping[str, Any]) -> None:
    """Mirror the non-authority catalog schema and all fixed equations."""

    if set(value) != {
        "evidence_format",
        "evidence_kind",
        "design_binding",
        "source_artifact_identities",
        "wave_domain",
        "source_denominator",
        "questionnaire_page_evidence",
        "relationship_catalog_evidence",
        "authority_disposition",
        "stop_conditions",
        "integrity",
        "status",
    }:
        raise ValueError("catalog evidence top-level schema drift")
    if (
        value["evidence_format"] != EVIDENCE_FORMAT
        or value["evidence_kind"]
        != "global_relationship_catalog_prerequisite_evidence"
        or value["design_binding"] != DESIGN_BINDING
        or value["source_artifact_identities"] != _source_artifact_identities()
        or value["status"] != BLOCKED_STATUS
    ):
        raise ValueError("catalog evidence identity drift")
    wave_domain = value["wave_domain"]
    if wave_domain != {
        "interview_waves": list(INTERVIEW_WAVES),
        "interview_wave_count": 43,
        "interview_wave_domain_sha256": EXPECTED_WAVE_DOMAIN_SHA256,
    }:
        raise ValueError("catalog wave domain drift")

    denominator = value["source_denominator"]
    _validate_digest_relation(
        denominator,
        "source_documents",
        "source_document_count",
        "source_document_domain_sha256",
        "source_document_keyset_sha256",
        "source_document_id",
    )
    _validate_digest_relation(
        denominator,
        "questionnaire_documents",
        "questionnaire_document_count",
        "questionnaire_document_domain_sha256",
        "questionnaire_document_keyset_sha256",
        "source_document_id",
    )
    if (
        denominator["source_document_count"] != 257
        or denominator["source_document_role_counts"]
        != {
            "questionnaire_flow": 81,
            "dictionary_layout": 86,
            "codebook": 47,
            "raw_fixed_width_data": 43,
        }
        or denominator["source_document_keyset_sha256"]
        != EXPECTED_U_KEYSET_SHA256
        or denominator["source_document_domain_sha256"]
        != EXPECTED_U_DOMAIN_SHA256
        or denominator["questionnaire_document_count"] != 81
        or denominator["questionnaire_document_keyset_sha256"]
        != EXPECTED_QUESTIONNAIRE_KEYSET_SHA256
        or denominator["questionnaire_document_domain_sha256"]
        != EXPECTED_QUESTIONNAIRE_DOMAIN_SHA256
        or denominator["source_bytes_reproduced"] is not True
        or denominator["status"] != "pass"
    ):
        raise ValueError("catalog source denominator fixed-law drift")
    if denominator["questionnaire_documents"] != [
        row
        for row in denominator["source_documents"]
        if row["document_role"] == "questionnaire_flow"
    ]:
        raise ValueError("questionnaire denominator is not the U slice")
    dispositions = denominator["upstream_disposition_evidence"]
    link_rows = dispositions["source_link_disposition_rows"]
    document_rows = dispositions["accepted_document_disposition_rows"]
    if (
        len(link_rows) != 465
        or Counter(row["disposition"] for row in link_rows)
        != {
            "included_family_questionnaire_flow": 81,
            "excluded_out_of_wave_2025_family_questionnaire": 1,
            "excluded_not_family_questionnaire_flow": 383,
        }
        or dispositions["source_link_disposition_domain_sha256"]
        != _canonical_digest(link_rows)
        or len(document_rows) != 456
        or Counter(row["disposition"] for row in document_rows)
        != {
            "included_family_questionnaire_flow": 81,
            "excluded_out_of_wave_2025_family_questionnaire": 1,
            "excluded_not_family_questionnaire_flow": 374,
        }
        or dispositions["accepted_document_disposition_domain_sha256"]
        != _canonical_digest(document_rows)
        or dispositions["included_upstream_document_ids_source_order_sha256"]
        != EXPECTED_UPSTREAM_QUESTIONNAIRE_ID_SHA256
    ):
        raise ValueError("upstream disposition evidence drift")

    pages = value["questionnaire_page_evidence"]
    _validate_digest_relation(
        pages,
        "questionnaire_page_rows",
        "questionnaire_page_count",
        "questionnaire_page_domain_sha256",
        "questionnaire_page_keyset_sha256",
        "questionnaire_page_id",
    )
    if (
        pages["questionnaire_page_count"] != 10_190
        or pages["questionnaire_page_text_derivation"] != PAGE_IMPLEMENTATION
        or pages["status"] != "pass_page_denominator_only"
    ):
        raise ValueError("questionnaire page denominator drift")
    for spec in ERA_SPECS:
        era_pages = [
            row
            for row in pages["questionnaire_page_rows"]
            if row["interview_wave"] in spec["interview_waves"]
        ]
        era_documents = [
            row
            for row in denominator["questionnaire_documents"]
            if row["interview_waves"][0] in spec["interview_waves"]
        ]
        if (
            len(era_pages) != spec["questionnaire_page_count"]
            or len(era_documents) != spec["questionnaire_document_count"]
        ):
            raise ValueError(f"{spec['era_id']} source slice drift")

    relationships = value["relationship_catalog_evidence"]
    baselines = baseline_relationship_rows()
    if (
        relationships["mandatory_baseline_relationship_rows"] != baselines
        or relationships["mandatory_baseline_relationship_count"] != 3
        or relationships["mandatory_baseline_relationship_keyset_sha256"]
        != _canonical_digest([row["relationship_id"] for row in baselines])
        or relationships["mandatory_baseline_relationship_domain_sha256"]
        != _canonical_digest(baselines)
        or any(
            relationships[key] is not None
            for key in (
                "source_component_relationship_rows",
                "source_component_relationship_count",
                "global_relationship_rows",
                "global_relationship_count",
                "global_relationship_keyset_sha256",
                "global_relationship_domain_sha256",
            )
        )
        or relationships["r_q_status"]
        != "blocked_incomplete_source_occurrence_annotation"
        or relationships["status"] != BLOCKED_STATUS
    ):
        raise ValueError("relationship lower-bound evidence drift")
    disposition = value["authority_disposition"]
    if (
        disposition["canonical_q5_emitted"] is not False
        or disposition["class_b_grammar_rows_emitted"] is not False
        or disposition["class_a_residual_ids_closed"] != []
        or disposition["class_a_residual_source_indices_surviving"]
        != [1, 2, 5, 11, 14, 18, 26]
        or disposition["class_a_residual_domain_sha256"]
        != EXPECTED_CLASS_A_DIGEST
        or disposition["disposition"] != BLOCKED_STATUS
    ):
        raise ValueError("catalog authority disposition drift")
    integrity = value["integrity"]
    if (
        set(integrity) != {"canonicalization", "content_sha256"}
        or integrity["canonicalization"] != CANONICALIZATION
        or integrity["content_sha256"] != _content_sha256(value)
    ):
        raise ValueError("catalog integrity drift")


def _baseline_hierarchy_rows(
    spec: Mapping[str, Any],
    questionnaire_pages: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    locators_by_wave: dict[int, list[Mapping[str, Any]]] = {}
    seen_documents: set[str] = set()
    for page in questionnaire_pages:
        source_document_id = page["source_document_id"]
        if source_document_id in seen_documents:
            continue
        seen_documents.add(source_document_id)
        locators_by_wave.setdefault(page["interview_wave"], []).append(
            page["corpus_digest_row_locator"]
        )
    rows: list[dict[str, Any]] = []
    for wave in spec["interview_waves"]:
        locator_rows = locators_by_wave[wave]
        if not locator_rows:
            raise ValueError(f"wave {wave} has no corpus digest-row locator")
        for role in ROLES:
            for relationship in baseline_relationship_rows():
                slot_values = [
                    wave,
                    wave - 1,
                    role,
                    relationship["job_slot_id"],
                    relationship["questionnaire_component_slot_id"],
                    relationship["slot_kind"],
                ]
                rows.append(
                    {
                        "questionnaire_slot_id": (
                            "psid-questionnaire-slot:"
                            + _canonical_digest(slot_values)
                        ),
                        "interview_wave": wave,
                        "earnings_reference_year": wave - 1,
                        "role": role,
                        "relationship_id": relationship["relationship_id"],
                        "job_slot": relationship["job_slot_id"],
                        "questionnaire_component_slot": relationship[
                            "questionnaire_component_slot_id"
                        ],
                        "slot_kind": relationship["slot_kind"],
                        "corpus_digest_row_scope": locator_rows,
                        "evidence_disposition": (
                            "design_fixed_baseline_coordinate_only_"
                            "presence_not_adjudicated"
                        ),
                    }
                )
    return rows


def era_output_path(era_id: str) -> Path:
    if era_id not in ERA_BY_ID:
        raise ValueError(f"unknown era {era_id!r}")
    return ERA_OUTPUT_DIRECTORY / f"{era_id}_slot_evidence_v1.json"


def _constructed_era_evidence(
    catalog: Mapping[str, Any], era_id: str
) -> dict[str, Any]:
    validate_catalog_evidence(catalog)
    spec = ERA_BY_ID.get(era_id)
    if spec is None:
        raise ValueError(f"unknown era {era_id!r}")
    waves = spec["interview_waves"]
    documents = [
        row
        for row in catalog["source_denominator"]["questionnaire_documents"]
        if row["interview_waves"][0] in waves
    ]
    pages = [
        row
        for row in catalog["questionnaire_page_evidence"][
            "questionnaire_page_rows"
        ]
        if row["interview_wave"] in waves
    ]
    baselines = baseline_relationship_rows()
    hierarchy_rows = _baseline_hierarchy_rows(spec, pages)
    hierarchy_multiplier = len(waves) * len(ROLES)
    expanded_multiplier = hierarchy_multiplier * 35
    value: dict[str, Any] = {
        "evidence_format": EVIDENCE_FORMAT,
        "evidence_kind": "era_questionnaire_slot_prerequisite_evidence",
        "design_binding": copy.deepcopy(DESIGN_BINDING),
        "global_catalog_identity": {
            "path": str(CATALOG_PATH.relative_to(ROOT)),
            "raw_sha256": _sha256(canonical_json_bytes(catalog)),
            "content_sha256": catalog["integrity"]["content_sha256"],
        },
        "era_id": era_id,
        "interview_waves": list(waves),
        "residual_ids": list(spec["residual_ids"]),
        "residual_source_indices": list(spec["residual_source_indices"]),
        "questionnaire_documents": documents,
        "questionnaire_document_count": len(documents),
        "questionnaire_document_keyset_sha256": _canonical_digest(
            [row["source_document_id"] for row in documents]
        ),
        "questionnaire_document_domain_sha256": _canonical_digest(documents),
        "questionnaire_page_rows": pages,
        "questionnaire_page_count": len(pages),
        "questionnaire_page_keyset_sha256": _canonical_digest(
            [row["questionnaire_page_id"] for row in pages]
        ),
        "questionnaire_page_domain_sha256": _canonical_digest(pages),
        "mandatory_baseline_relationship_rows": baselines,
        "mandatory_baseline_relationship_count": len(baselines),
        "baseline_hierarchy_rows": hierarchy_rows,
        "baseline_hierarchy_row_count": len(hierarchy_rows),
        "baseline_hierarchy_keyset_sha256": _canonical_digest(
            [row["questionnaire_slot_id"] for row in hierarchy_rows]
        ),
        "baseline_hierarchy_domain_sha256": _canonical_digest(hierarchy_rows),
        "complete_hierarchy_cardinality": {
            "r_q_count": None,
            "hierarchy_multiplier_times_r_q": hierarchy_multiplier,
            "hierarchy_row_count": None,
            "expanded_multiplier_times_r_q": expanded_multiplier,
            "expanded_row_count": None,
            "design_fixed_baseline_hierarchy_lower_bound": len(hierarchy_rows),
            "design_fixed_baseline_expanded_lower_bound": (
                len(hierarchy_rows) * 35
            ),
            "status": BLOCKED_STATUS,
        },
        "absence_domain_evidence": {
            "o_h_status": "not_constructed",
            "o_p_status": "not_constructed",
            "m_h_status": "not_constructed",
            "absence_proof_count": None,
            "absence_proof_domain_sha256": None,
            "blocking_prerequisites": [
                "complete_global_r_q",
                "complete_questionnaire_occurrence_and_flow_annotation",
                "complete_positive_occurrence_relation_o_p",
                "complete_field_source_derivation_including_class_b_grammar",
                "complete_near_match_source_annotation_domain",
            ],
            "status": BLOCKED_STATUS,
        },
        "authority_disposition": {
            "canonical_era_row_emitted": False,
            "class_a_residual_ids_closed": [],
            "surviving_residual_source_indices": list(
                spec["residual_source_indices"]
            ),
            "disposition": BLOCKED_STATUS,
        },
        "integrity": {
            "canonicalization": CANONICALIZATION,
            "content_sha256": "0" * 64,
        },
        "status": BLOCKED_STATUS,
    }
    value["integrity"]["content_sha256"] = _content_sha256(value)
    return value


def build_era_evidence(
    catalog: Mapping[str, Any], era_id: str
) -> dict[str, Any]:
    """Build one era slice from the independently validated global catalog."""

    value = _constructed_era_evidence(catalog, era_id)
    validate_era_evidence(value, catalog)
    return value


def validate_era_evidence(
    value: Mapping[str, Any], catalog: Mapping[str, Any]
) -> None:
    """Mirror one era value from the global source evidence."""

    era_id = value.get("era_id")
    if era_id not in ERA_BY_ID:
        raise ValueError("era evidence ID drift")
    expected = _constructed_era_evidence(catalog, era_id)
    if set(value) != set(expected):
        raise ValueError("era evidence top-level schema drift")
    for key, expected_value in expected.items():
        if key == "integrity":
            continue
        if value[key] != expected_value:
            raise ValueError(f"era evidence {key} drift")
    if (
        set(value["integrity"]) != {"canonicalization", "content_sha256"}
        or value["integrity"]["canonicalization"] != CANONICALIZATION
        or value["integrity"]["content_sha256"] != _content_sha256(value)
    ):
        raise ValueError("era evidence integrity drift")


def _committed_input_identity(
    path: Path, value: Mapping[str, Any]
) -> dict[str, Any]:
    raw = path.read_bytes()
    if raw != canonical_json_bytes(value):
        raise ValueError(f"noncanonical committed input: {path}")
    return {
        "path": str(path.relative_to(ROOT)),
        "raw_sha256": _sha256(raw),
        "content_sha256": value["integrity"]["content_sha256"],
    }


def _constructed_absence_stop_evidence(
    catalog: Mapping[str, Any],
    era_evidence_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Construct the complete dependency stop without asserting an absence."""

    if CANONICAL_Q5_PATH.exists():
        raise ValueError("canonical Q5 path already exists")
    validate_catalog_evidence(catalog)
    if set(era_evidence_by_id) != set(ERA_BY_ID):
        raise ValueError("absence-stop era input domain drift")

    era_inputs: list[dict[str, Any]] = []
    era_cardinalities: list[dict[str, Any]] = []
    wave_projection: list[int] = []
    document_count = 0
    page_count = 0
    baseline_hierarchy_count = 0
    baseline_expanded_count = 0
    for spec in ERA_SPECS:
        era_id = spec["era_id"]
        era = era_evidence_by_id[era_id]
        validate_era_evidence(era, catalog)
        wave_projection.extend(era["interview_waves"])
        document_count += era["questionnaire_document_count"]
        page_count += era["questionnaire_page_count"]
        baseline_hierarchy_count += era["baseline_hierarchy_row_count"]
        baseline_expanded_count += era["complete_hierarchy_cardinality"][
            "design_fixed_baseline_expanded_lower_bound"
        ]
        identity = _committed_input_identity(era_output_path(era_id), era)
        era_inputs.append({"era_id": era_id, **identity})
        cardinality = era["complete_hierarchy_cardinality"]
        era_cardinalities.append(
            {
                "era_id": era_id,
                "interview_wave_count": len(era["interview_waves"]),
                "hierarchy_multiplier_times_r_q": cardinality[
                    "hierarchy_multiplier_times_r_q"
                ],
                "expanded_multiplier_times_r_q": cardinality[
                    "expanded_multiplier_times_r_q"
                ],
                "design_fixed_baseline_hierarchy_lower_bound": cardinality[
                    "design_fixed_baseline_hierarchy_lower_bound"
                ],
                "design_fixed_baseline_expanded_lower_bound": cardinality[
                    "design_fixed_baseline_expanded_lower_bound"
                ],
                "complete_hierarchy_row_count": None,
                "absence_proof_count": None,
                "status": BLOCKED_STATUS,
            }
        )
    if (
        wave_projection != list(INTERVIEW_WAVES)
        or document_count != 81
        or page_count != 10_190
        or baseline_hierarchy_count != 258
        or baseline_expanded_count != 9_030
    ):
        raise ValueError("absence-stop global era projection drift")

    class_a_rows = [
        {
            "residual_source_index": index,
            "residual_id": residual_id,
            "residual_row_sha256": row_sha256,
            "closed_by_intermediate_evidence": False,
        }
        for index, residual_id, row_sha256 in CLASS_A_RESIDUAL_ROWS
    ]
    value: dict[str, Any] = {
        "evidence_format": EVIDENCE_FORMAT,
        "evidence_kind": "global_absence_domain_dependency_stop_evidence",
        "design_binding": copy.deepcopy(DESIGN_BINDING),
        "input_artifact_identities": {
            "global_relationship_catalog": _committed_input_identity(
                CATALOG_PATH, catalog
            ),
            "era_evidence": era_inputs,
        },
        "authenticated_scope": {
            "interview_wave_count": 43,
            "role_count": 2,
            "purpose_count": 35,
            "questionnaire_document_count": document_count,
            "questionnaire_page_count": page_count,
            "source_document_count": catalog["source_denominator"][
                "source_document_count"
            ],
            "source_document_keyset_sha256": catalog["source_denominator"][
                "source_document_keyset_sha256"
            ],
            "source_document_domain_sha256": catalog["source_denominator"][
                "source_document_domain_sha256"
            ],
            "questionnaire_page_keyset_sha256": catalog[
                "questionnaire_page_evidence"
            ]["questionnaire_page_keyset_sha256"],
            "questionnaire_page_domain_sha256": catalog[
                "questionnaire_page_evidence"
            ]["questionnaire_page_domain_sha256"],
            "status": "pass_source_denominator_only",
        },
        "relationship_catalog_stop": {
            "mandatory_baseline_relationship_count": 3,
            "mandatory_baseline_relationship_keyset_sha256": catalog[
                "relationship_catalog_evidence"
            ]["mandatory_baseline_relationship_keyset_sha256"],
            "mandatory_baseline_relationship_domain_sha256": catalog[
                "relationship_catalog_evidence"
            ]["mandatory_baseline_relationship_domain_sha256"],
            "source_component_relationship_count": None,
            "global_r_q_count": None,
            "global_r_q_keyset_sha256": None,
            "global_r_q_domain_sha256": None,
            "source_component_relation_definition": (
                "C_source=hierarchy_annotation_authority."
                "questionnaire_component_slot_rows_filtered_to_"
                "component_slot_type_in_{source_remuneration_component,"
                "source_context}"
            ),
            "cardinality_equation": "|R_Q|=3+|C_source|",
            "status": BLOCKED_STATUS,
        },
        "hierarchy_domain_stop": {
            "global_hierarchy_count": None,
            "global_hierarchy_keyset_sha256": None,
            "global_hierarchy_domain_sha256": None,
            "global_expanded_row_count": None,
            "global_expanded_keyset_sha256": None,
            "global_expanded_domain_sha256": None,
            "global_hierarchy_cardinality_equation": "|H|=86*|R_Q|",
            "global_expanded_cardinality_equation": ("|expanded|=3010*|R_Q|"),
            "design_fixed_baseline_hierarchy_lower_bound": (
                baseline_hierarchy_count
            ),
            "design_fixed_baseline_expanded_lower_bound": (
                baseline_expanded_count
            ),
            "era_cardinalities": era_cardinalities,
            "status": BLOCKED_STATUS,
        },
        "absence_domain_stop": {
            "symbolic_relation_statuses": {
                "O_H": "not_constructed",
                "O_P": "not_constructed",
                "M_h": "not_constructed",
                "P_h": "not_constructed",
            },
            "observed_hierarchy_row_count": None,
            "positive_occurrence_row_count": None,
            "structural_expanded_key_count": None,
            "near_match_source_annotation_count": None,
            "absence_proofs": None,
            "absence_proof_count": None,
            "absence_proof_domain_sha256": None,
            "relation_equations": {
                "observed_hierarchy_count": "|observed_H|=|O_H|",
                "positive_occurrence_count": "|positive|=|O_P|",
                "structural_expanded_key_count": "|structural|=sum_h|M_h|",
                "expanded_partition": "|O_P|+sum_h|M_h|=35*|H|",
                "absence_proof_count": "|P|=|{h_in_H:M_h_is_nonempty}|",
                "near_match_annotation_count": (
                    "|near_match_source_annotation|="
                    "|questionnaire_occurrence|+|field_stream_locator|"
                ),
            },
            "proof_scope_law": {
                "proof_partition": "exactly_one_P_h_per_nonempty_M_h",
                "proof_order": "nonempty_M_h_filtered_H_order",
                "searched_interview_waves": (
                    "exact_singleton_matching_h_interview_wave"
                ),
                "target_h_coordinate_count": 1,
                "target_field_purposes": "complete_M_h_in_ratified_order",
                "searched_questionnaire_domain": (
                    "all_questionnaire_documents_and_pages_in_target_wave"
                ),
                "searched_field_domain": (
                    "complete_target_wave_layout_and_codebook_keysets"
                ),
                "near_match_domain": (
                    "complete_target_wave_source_annotation_bindings"
                ),
                "era_wide_proof_allowed": False,
                "cross_wave_proof_allowed": False,
                "per_inventory_key_proof_allowed": False,
                "proof_selected_source_subset_allowed": False,
            },
            "absence_proof_member_order": [
                "absence_proof_id",
                "era_id",
                "target_inventory_keys",
                "target_predicate",
                "searched_interview_waves",
                "searched_locator_ids",
                "searched_layout_keyset_sha256",
                "searched_codebook_keyset_sha256",
                "excluded_near_matches",
                "search_implementation",
                "conclusion",
            ],
            "target_predicate_member_order": [
                "roles",
                "job_slot_ids",
                "questionnaire_component_slot_ids",
                "slot_kinds",
                "field_purposes",
                "quantifier",
            ],
            "search_implementation_member_order": [
                "authority_kind",
                "questionnaire_page_text_derivation_sha256",
                "questionnaire_page_domain_sha256",
                "questionnaire_occurrence_domain_sha256",
                "flow_branch_domain_sha256",
                "role_node_domain_sha256",
                "job_slot_domain_sha256",
                "questionnaire_component_slot_domain_sha256",
                "node_alias_domain_sha256",
                "global_relationship_domain_sha256",
                "hierarchy_domain_sha256",
                "positive_occurrence_domain_sha256",
                "near_match_source_annotation_count",
                "near_match_source_annotation_keyset_sha256",
                "near_match_source_annotation_domain_sha256",
            ],
            "conclusion_member_order": [
                "disposition",
                "proved_target_inventory_keys",
                "reason_code",
            ],
            "unsupported_zero_or_empty_claim_emitted": False,
            "status": BLOCKED_STATUS,
        },
        "blocking_members": [
            {
                "section_19_anchor": "19.3.3_complete_R_Q_and_H",
                "members": [
                    "era_rows[].questionnaire_occurrence_rows",
                    "era_rows[].flow_branch_rows",
                    "hierarchy_annotation_authority.role_node_rows",
                    "hierarchy_annotation_authority.job_slot_rows",
                    "hierarchy_annotation_authority.questionnaire_component_slot_rows",
                    "hierarchy_annotation_authority.node_alias_rows",
                    "hierarchy_annotation_authority.global_relationship_rows",
                    "era_rows[].hierarchy_rows",
                ],
            },
            {
                "section_19_anchor": "19.3.2_and_19.3.3_field_source_derivation",
                "members": [
                    "source_document_manifest.field_source_derivation",
                    "source_document_manifest.field_source_derivation.numeric_grammar_derivation_rows",
                    "source_document_manifest.field_source_derivation.numeric_grammar_derivation_row_count",
                    "source_document_manifest.field_source_derivation.numeric_grammar_derivation_keyset_sha256",
                    "source_document_manifest.field_source_derivation.numeric_grammar_derivation_domain_sha256",
                    "era_rows[].positive_field_join_rows[].raw_field_projections[].numeric_grammar_derivation_id",
                    "era_rows[].positive_field_join_rows[].raw_field_projections[].numeric_grammar_derivation_sha256",
                ],
            },
            {
                "section_19_anchor": "19.3.3_complete_O_H_O_P_M_h_and_P_h",
                "members": [
                    "era_rows[].positive_occurrence_rows",
                    "era_rows[].occurrence_raw_field_reference_rows",
                    "era_rows[].positive_field_join_rows",
                    "era_rows[].expanded_disposition_rows",
                    "era_rows[].near_match_source_annotation_rows",
                    "era_rows[].absence_proofs",
                ],
            },
            {
                "section_19_anchor": "19.4.2_G17-C01_and_19.5_DC-30",
                "members": [
                    "G17-C01.slot_source_authority_manifest",
                    "G17-C01.hierarchy_annotation_authority",
                    "source_authority_manifest.slot_closure_evidence_identity",
                ],
            },
        ],
        "blocking_predicates": [
            {
                "section_19_anchor": "19.8.1_walk_A_and_19.8.2_tension_9",
                "predicate": (
                    "unique_same_wave_leading_question_identifier_resolution"
                ),
                "status": "failed_ambiguous",
                "ambiguity_evidence": [
                    "2023:G13.:ER83121",
                    "2023:G13.:ER83495",
                ],
            },
            {
                "section_19_anchor": "19.4.2_G17-C01",
                "predicate": "complete_successor_comparand_pass",
                "status": "not_constructed",
                "ambiguity_evidence": [],
            },
            {
                "section_19_anchor": "19.5_DC-30",
                "predicate": "D5_to_Q5_and_Q5_to_consumer_ancestry",
                "status": "not_constructed_no_Q5",
                "ambiguity_evidence": [],
            },
        ],
        "class_a_inventory_blocker_disposition": {
            "residual_rows": class_a_rows,
            "residual_domain_sha256": EXPECTED_CLASS_A_DIGEST,
            "source_indices_closed": [],
            "source_indices_surviving": [1, 2, 5, 11, 14, 18, 26],
            "intermediate_artifacts_close_authority_blockers": False,
            "status": "registration_required",
        },
        "authority_disposition": {
            "canonical_q5_path": str(CANONICAL_Q5_PATH.relative_to(ROOT)),
            "canonical_q5_emitted": False,
            "class_b_grammar_rows_emitted": False,
            "q5_status": "not_emitted_blocked",
            "section_19_stop_anchors": [
                "19.3.2_complete_field_source_derivation",
                "19.3.3_R_Q_H_O_H_O_P_M_h_P_h",
                "19.4.2_G17-C01",
                "19.5_DC-30",
                "19.8.1_steps_1_and_2_including_walk_A",
                "19.8.2_tensions_8_and_9",
            ],
            "status": BLOCKED_STATUS,
        },
        "integrity": {
            "canonicalization": CANONICALIZATION,
            "content_sha256": "0" * 64,
        },
        "status": BLOCKED_STATUS,
    }
    value["integrity"]["content_sha256"] = _content_sha256(value)
    return value


def build_absence_stop_evidence(
    catalog: Mapping[str, Any],
    era_evidence_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Build the section-19 absence-domain dependency stop."""

    value = _constructed_absence_stop_evidence(catalog, era_evidence_by_id)
    validate_absence_stop_evidence(value, catalog, era_evidence_by_id)
    return value


def validate_absence_stop_evidence(
    value: Mapping[str, Any],
    catalog: Mapping[str, Any],
    era_evidence_by_id: Mapping[str, Mapping[str, Any]],
) -> None:
    """Mirror every fixed absence-stop member and dependency equation."""

    expected = _constructed_absence_stop_evidence(catalog, era_evidence_by_id)
    if set(value) != set(expected):
        raise ValueError("absence-stop top-level schema drift")
    for key, expected_value in expected.items():
        if key == "integrity":
            continue
        if value[key] != expected_value:
            raise ValueError(f"absence-stop {key} drift")
    if (
        set(value["integrity"]) != {"canonicalization", "content_sha256"}
        or value["integrity"]["canonicalization"] != CANONICALIZATION
        or value["integrity"]["content_sha256"] != _content_sha256(value)
    ):
        raise ValueError("absence-stop integrity drift")


def _read_committed_catalog() -> Mapping[str, Any]:
    if not CATALOG_PATH.is_file():
        raise SystemExit(f"catalog evidence unavailable: {CATALOG_PATH}")
    catalog = strict_parse_document(
        CATALOG_PATH.read_bytes(), "committed global catalog evidence"
    )
    if not isinstance(catalog, Mapping):
        raise SystemExit("catalog evidence is not an object")
    return catalog


def _read_committed_eras() -> dict[str, Mapping[str, Any]]:
    values: dict[str, Mapping[str, Any]] = {}
    for spec in ERA_SPECS:
        era_id = spec["era_id"]
        path = era_output_path(era_id)
        if not path.is_file():
            raise SystemExit(f"era evidence unavailable: {path}")
        value = strict_parse_document(path.read_bytes(), f"committed {era_id}")
        if not isinstance(value, Mapping):
            raise SystemExit(f"era evidence is not an object: {path}")
        values[era_id] = value
    return values


def render_catalog(capture_root: Path = DEFAULT_CAPTURE_ROOT) -> bytes:
    return canonical_json_bytes(build_catalog_evidence(capture_root))


def render_era(catalog: Mapping[str, Any], era_id: str) -> bytes:
    return canonical_json_bytes(build_era_evidence(catalog, era_id))


def render_absence_stop(
    catalog: Mapping[str, Any],
    era_evidence_by_id: Mapping[str, Mapping[str, Any]],
) -> bytes:
    return canonical_json_bytes(
        build_absence_stop_evidence(catalog, era_evidence_by_id)
    )


def _write_or_check(path: Path, raw: bytes, check: bool) -> None:
    if check:
        if not path.is_file() or path.read_bytes() != raw:
            raise SystemExit(f"artifact drift: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--capture-root", type=Path, default=DEFAULT_CAPTURE_ROOT
    )
    parser.add_argument("--catalog-output", type=Path, default=CATALOG_PATH)
    parser.add_argument("--era", choices=tuple(ERA_BY_ID))
    parser.add_argument("--era-output", type=Path)
    parser.add_argument("--absence-stop", action="store_true")
    parser.add_argument(
        "--absence-output", type=Path, default=ABSENCE_STOP_PATH
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    if args.era is not None and args.absence_stop:
        parser.error("--era and --absence-stop are mutually exclusive")
    if args.absence_stop:
        catalog = _read_committed_catalog()
        eras = _read_committed_eras()
        _write_or_check(
            args.absence_output,
            render_absence_stop(catalog, eras),
            args.check,
        )
        return 0

    if args.era is None:
        _write_or_check(
            args.catalog_output,
            render_catalog(args.capture_root),
            args.check,
        )
        return 0

    if not args.catalog_output.is_file():
        raise SystemExit(
            f"catalog evidence unavailable: {args.catalog_output}"
        )
    catalog = strict_parse_document(
        args.catalog_output.read_bytes(), "committed global catalog evidence"
    )
    if not isinstance(catalog, Mapping):
        raise SystemExit("catalog evidence is not an object")
    output = args.era_output or era_output_path(args.era)
    _write_or_check(output, render_era(catalog, args.era), args.check)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
