#!/usr/bin/env python3
"""Build the nonoperative Entry-11 questionnaire closure attempt.

The ratified design has no successor methodology or PSID authority registry
that can admit a membership v3.  This artifact therefore preserves every v2
membership fact and family disposition, records the independently extracted
PSID evidence, and makes both blocking conditions explicit.
"""

from __future__ import annotations

import argparse
import copy
import decimal
import hashlib
import json
import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = (
    ROOT
    / "data"
    / "external"
    / "covered_earnings_questionnaire_closure_attempt_v1.json"
)

SCHEMA_VERSION = "covered_earnings_questionnaire_closure_attempt.v1"
ARTIFACT_ID = "entry11_unit1b_questionnaire_closure_attempt_v1"
CANONICALIZATION = "python-json-sort-keys-compact-ascii-no-nan-lf-v1"

FROZEN_INPUTS = {
    "membership_adjudication_v2": {
        "committed_path": "data/external/covered_earnings_membership_adjudication_v2.json",
        "size_bytes": 57_125,
        "sha256": "7306c898d044df0ce86754b8468b26e32d8696027e8dde2f7d5935d79f1abb14",
        "schema_version": "covered_earnings_membership_adjudication.v2",
    },
    "psid_codebook_inventory_adjudication": {
        "committed_path": "data/external/psid_codebook_inventory_adjudication_v1.json",
        "size_bytes": 1_415_319,
        "sha256": "df73026bcf649d12ecb606501d64780f41567b6dc09d7029f9191111cab09c62",
        "schema_version": "psid_codebook_inventory_adjudication.v1",
    },
    "corpus_registration_attempt": {
        "committed_path": "data/external/psid_questionnaire_corpus_authority_registration_attempt_v1.json",
        "size_bytes": 499_221,
        "sha256": "a1216521410d5a73e0dfde4d094d703843016cf6e67c8ee11ac3c4be70baceb0",
        "schema_version": "psid_questionnaire_corpus_authority_registration_attempt.v1",
    },
    "questionnaire_extraction": {
        "committed_path": "data/external/psid_questionnaire_corpus_extraction_v1.json",
        "size_bytes": 81_210,
        "sha256": "4a6bfd761b05b40115c7a416ceb0836f73989d1492b58cb2729e78a288e5a29b",
        "schema_version": "psid_questionnaire_corpus_extraction.v1",
    },
}

FROZEN_DESIGN_PREFIX = {
    "committed_path": "docs/design/covered_earnings_correction.md",
    "identity_scope": "append_only_prefix",
    "size_bytes": 1_252_209,
    "sha256": "29f0cb134e95b6215dc502d0e25392b5c971fdb93dfad40fd5d221e8a482a1b7",
    "revision": 4,
}

DESIGN_LOCATOR_SPECS = (
    (
        "closed_methodology_registry_requires_successor",
        9433,
        9441,
        "Section 16.2 closes the current authority registry and requires a later ratified append-only version plus fresh adjudication.",
    ),
    (
        "membership_v2_legacy_envelope_law",
        9471,
        9565,
        "Section 16.2 fixes membership v2 path, schema, identifier, size, SHA-256, projections, and semantic result.",
    ),
    (
        "membership_methodology_successor_law",
        14541,
        14563,
        "Section 16.9 permits new B2/B11 methodology only through a later ratified append-only successor and fresh adjudication.",
    ),
    (
        "frozen_membership_methodology_identity_law",
        17453,
        17463,
        "Section 16.11.3 declares the v2 methodology identifiers frozen methodology bytes rather than a live row.",
    ),
    (
        "closed_psid_source_disposition_law",
        19719,
        19799,
        "Section 16.13.2 fixes the PSID source singleton and makes registration_required the only representable disposition for V-B5/V-B6/V-B8.",
    ),
    (
        "frozen_vb_source_rows_and_residuals_law",
        21542,
        21610,
        "Section 16.14.6 fixes the operative PSID source identity, V-B row digests, and residual cardinalities.",
    ),
)

OPERATIVE_VB_ROWS = (
    (
        "V-B5",
        0,
        "8c2d6b0580f3d9d9d5c042c2a8b5822f1ab656089e0f82561d057c8624ff6622",
        1,
    ),
    (
        "V-B6",
        1,
        "25fb91f2b80bd8d5ca80ec942c00f96f95a49b37bf7c6dd3a067c6c74ef2b05e",
        4,
    ),
    (
        "V-B8",
        2,
        "25fa8ecf8de54c672724c29deb0f994090c243c793b8b5fbe9238248d35faa8e",
        3,
    ),
)


def canonical_json_bytes(value: Any) -> bytes:
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


def _strictly_parsed_document(raw: bytes, label: str) -> Any:
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"{label} contains duplicate object key {key!r}")
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
            raise ValueError(f"{label} contains a leading U+FEFF BOM")
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
        raise ValueError(f"{label} is not a uniquely parseable JSON document") from error


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _frozen_inputs() -> dict[str, Any]:
    values: dict[str, Any] = {}
    for input_id, spec in FROZEN_INPUTS.items():
        raw = (ROOT / spec["committed_path"]).read_bytes()
        if len(raw) != spec["size_bytes"] or _sha256(raw) != spec["sha256"]:
            raise ValueError(f"{input_id} frozen identity drift")
        value = _strictly_parsed_document(raw, input_id)
        if value.get("schema_version") != spec["schema_version"]:
            raise ValueError(f"{input_id} schema identity drift")
        values[input_id] = value
    return values


def _source_artifact_identities() -> list[dict[str, Any]]:
    return [
        {"source_artifact_id": input_id, **spec}
        for input_id, spec in FROZEN_INPUTS.items()
    ]


def _frozen_design_bytes() -> bytes:
    live = (ROOT / FROZEN_DESIGN_PREFIX["committed_path"]).read_bytes()
    size_bytes = FROZEN_DESIGN_PREFIX["size_bytes"]
    if len(live) < size_bytes:
        raise ValueError("ratified design frozen prefix truncated")
    prefix = live[:size_bytes]
    if _sha256(prefix) != FROZEN_DESIGN_PREFIX["sha256"]:
        raise ValueError("ratified design frozen prefix identity drift")
    return prefix


def _design_authority_locators() -> list[dict[str, Any]]:
    raw = _frozen_design_bytes()
    lines = raw.splitlines(keepends=True)
    rows: list[dict[str, Any]] = []
    for locator_id, line_start, line_end, description in DESIGN_LOCATOR_SPECS:
        if not 1 <= line_start <= line_end <= len(lines):
            raise ValueError(f"{locator_id} line range outside frozen design")
        byte_start = sum(len(line) for line in lines[: line_start - 1])
        byte_end = sum(len(line) for line in lines[:line_end])
        rows.append(
            {
                "locator_id": locator_id,
                "committed_path": FROZEN_DESIGN_PREFIX["committed_path"],
                "identity_scope": FROZEN_DESIGN_PREFIX["identity_scope"],
                "full_source_sha256": FROZEN_DESIGN_PREFIX["sha256"],
                "size_bytes": FROZEN_DESIGN_PREFIX["size_bytes"],
                "design_revision": FROZEN_DESIGN_PREFIX["revision"],
                "line_start": line_start,
                "line_end": line_end,
                "byte_start": byte_start,
                "byte_end": byte_end,
                "range_sha256": _sha256(raw[byte_start:byte_end]),
                "description": description,
            }
        )
    return rows


def _membership_fact_readjudications(membership: Mapping[str, Any]) -> list[dict[str, Any]]:
    facts = membership.get("facts")
    if not isinstance(facts, list) or len(facts) != 30:
        raise ValueError("membership v2 fact domain drift")
    rows: list[dict[str, Any]] = []
    for index, fact in enumerate(facts):
        rows.append(
            {
                "source_pointer": f"/facts/{index}",
                "v2_fact_row_sha256": _sha256(canonical_json_bytes(fact)),
                "fact_id": fact["fact_id"],
                "group": fact["group"],
                "requirement": fact["requirement"],
                "prior_v2_verdict": fact["verdict"],
                "closure_attempt_verdict": fact["verdict"],
                "psid_corpus_source_disposition": "does_not_establish_membership_facts",
                "evidence_locator_ids": [],
                "supersession_effect": "none",
            }
        )
    return rows


def _membership_verdict_summary(rows: list[Mapping[str, Any]]) -> dict[str, int]:
    verdicts = [row["closure_attempt_verdict"] for row in rows]
    summary = {
        "fact_count": len(rows),
        "established_count": verdicts.count("established"),
        "partially_established_count": verdicts.count(
            "partially_established_required_fact_unestablished"
        ),
        "unestablished_count": verdicts.count("unestablished"),
    }
    if summary != {
        "fact_count": 30,
        "established_count": 2,
        "partially_established_count": 17,
        "unestablished_count": 11,
    }:
        raise ValueError("membership v2 verdict counts drift")
    return summary


def _membership_family_dispositions(membership: Mapping[str, Any]) -> list[dict[str, Any]]:
    families = membership.get("family_dispositions")
    if not isinstance(families, list) or len(families) != 14:
        raise ValueError("membership v2 family domain drift")
    rows: list[dict[str, Any]] = []
    for index, family in enumerate(families):
        if family.get("verdict") != "fail_closed":
            raise ValueError("membership v2 family verdict drift")
        rows.append(
            {
                "source_pointer": f"/family_dispositions/{index}",
                "v2_family_row_sha256": _sha256(canonical_json_bytes(family)),
                "target_family": family["target_family"],
                "prior_v2_verdict": family["verdict"],
                "closure_attempt_verdict": family["verdict"],
                "missing_source_fact_ids": family["missing_source_fact_ids"],
                "missing_registration_authority_ids": family[
                    "missing_registration_authority_ids"
                ],
                "missing_fact_list": family["missing_fact_list"],
                "supersession_effect": "none",
            }
        )
    return rows


def _operative_psid_rows(psid: Mapping[str, Any]) -> list[dict[str, Any]]:
    verdicts = psid.get("verdicts")
    if not isinstance(verdicts, list):
        raise ValueError("PSID verdict domain missing")
    rows: list[dict[str, Any]] = []
    for claim_id, index, row_sha256, residual_count in OPERATIVE_VB_ROWS:
        verdict = verdicts[index]
        if (
            verdict.get("registration_item_id") != claim_id
            or verdict.get("verdict") != "registration_required"
            or len(verdict.get("residual_ids", [])) != residual_count
            or _sha256(canonical_json_bytes(verdict)) != row_sha256
        ):
            raise ValueError(f"operative {claim_id} source row drift")
        rows.append(
            {
                "claim_id": claim_id,
                "source_pointer": f"/verdicts/{index}",
                "source_row_sha256": row_sha256,
                "operative_residual_ids": verdict["residual_ids"],
                "operative_residual_count": residual_count,
                "operative_source_disposition": "registration_required",
            }
        )
    return rows


def _psid_evidence_rows(extraction: Mapping[str, Any]) -> list[dict[str, Any]]:
    source_rows = extraction.get("psid_vb_residual_extractions")
    if not isinstance(source_rows, list) or len(source_rows) != 8:
        raise ValueError("questionnaire extraction residual domain drift")
    rows: list[dict[str, Any]] = []
    for index, source in enumerate(source_rows):
        rows.append(
            {
                "source_pointer": f"/psid_vb_residual_extractions/{index}",
                "source_extraction_row_sha256": _sha256(
                    canonical_json_bytes(source)
                ),
                "family_id": source["family_id"],
                "residual_id": source["residual_id"],
                "evidentiary_verdict": source["evidentiary_verdict"],
                "evidence_locator_ids": source["evidence_locator_ids"],
                "absence_proof_ids": source["absence_proof_ids"],
                "established_findings": source["established_findings"],
                "remaining_unestablished_facts": source[
                    "remaining_unestablished_facts"
                ],
                "operative_effect": "none",
            }
        )
    if sum(row["evidentiary_verdict"] == "established_by_questionnaire_corpus" for row in rows) != 7:
        raise ValueError("questionnaire established-count drift")
    if sum(bool(row["remaining_unestablished_facts"]) for row in rows) != 1:
        raise ValueError("questionnaire residual-count drift")
    return rows


def _vb_family_summary(
    evidence_rows: list[Mapping[str, Any]],
    operative_rows: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    operative_by_id = {row["claim_id"]: row for row in operative_rows}
    rows: list[dict[str, Any]] = []
    for family_id in ("V-B5", "V-B6", "V-B8"):
        selected = [row for row in evidence_rows if row["family_id"] == family_id]
        closed = sum(
            row["evidentiary_verdict"] == "established_by_questionnaire_corpus"
            for row in selected
        )
        remaining = sum(bool(row["remaining_unestablished_facts"]) for row in selected)
        operative = operative_by_id[family_id]
        rows.append(
            {
                "family_id": family_id,
                "targeted_residual_count": len(selected),
                "evidentially_closed_count": closed,
                "evidentiary_remaining_residual_count": remaining,
                "operative_residual_count": operative["operative_residual_count"],
                "operative_source_disposition": "registration_required",
                "operative_change": "none",
            }
        )
    return rows


def _content_sha256(value: Mapping[str, Any]) -> str:
    preimage = copy.deepcopy(value)
    preimage["integrity"]["content_sha256"] = "0" * 64
    return _sha256(canonical_json_bytes(preimage))


def _constructed_value() -> dict[str, Any]:
    inputs = _frozen_inputs()
    registration = inputs["corpus_registration_attempt"]
    extraction = inputs["questionnaire_extraction"]
    if (
        registration.get("registration_status") != "fail"
        or registration.get("accepted_authority_registry") is not None
        or registration.get("verified_document_count") != 440
        or registration.get("failed_document_count") != 16
    ):
        raise ValueError("corpus registration blocker drift")
    if extraction.get("authority_disposition") != {
        "corpus_registration_status": "fail",
        "accepted_corpus_authority": False,
        "verified_candidate_documents_may_support_nonoperative_audit": True,
        "membership_v3_or_supersession_effect": "none",
    }:
        raise ValueError("questionnaire extraction authority disposition drift")
    membership_rows = _membership_fact_readjudications(
        inputs["membership_adjudication_v2"]
    )
    evidence_rows = _psid_evidence_rows(extraction)
    operative_rows = _operative_psid_rows(
        inputs["psid_codebook_inventory_adjudication"]
    )
    value: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_id": ARTIFACT_ID,
        "source_artifact_identities": _source_artifact_identities(),
        "design_authority_locators": _design_authority_locators(),
        "attempt_scope": {
            "membership_domain": "SSA_Tables_B2_B11_membership_predicates",
            "questionnaire_domain": "PSID_variable_semantics_for_V-B5_V-B6_V-B8",
            "fitting_or_numeric_targets": False,
            "accepted_authority_registration": False,
        },
        "supersession_adjudication": {
            "membership_v3_permitted": False,
            "disposition": "blocked_missing_ratified_append_only_successor_registry",
            "legacy_membership_v2_disposition": "byte_frozen_preserved",
            "operative_effect": "none",
            "design_blocking_locator_ids": [
                "closed_methodology_registry_requires_successor",
                "membership_v2_legacy_envelope_law",
                "membership_methodology_successor_law",
                "frozen_membership_methodology_identity_law",
                "closed_psid_source_disposition_law",
                "frozen_vb_source_rows_and_residuals_law",
            ],
            "independent_capture_blocker": {
                "disposition": "corpus_registration_failed",
                "document_candidate_count": 456,
                "verified_document_count": 440,
                "failed_document_count": 16,
                "accepted_authority_registry": None,
            },
        },
        "membership_verdict_summary": _membership_verdict_summary(membership_rows),
        "membership_fact_readjudications": membership_rows,
        "membership_family_dispositions": _membership_family_dispositions(
            inputs["membership_adjudication_v2"]
        ),
        "operative_psid_vb_rows": operative_rows,
        "psid_questionnaire_evidence_results": evidence_rows,
        "psid_vb_family_summary": _vb_family_summary(evidence_rows, operative_rows),
        "closure_disposition": {
            "evidentiary_residuals_by_family": {"V-B5": 0, "V-B6": 1, "V-B8": 0},
            "operative_residuals_by_family": {"V-B5": 1, "V-B6": 4, "V-B8": 3},
            "membership_facts_changed": 0,
            "membership_families_changed": 0,
            "membership_v3_emitted": False,
            "closure_attempt_status": "nonoperative_partial_evidentiary_closure",
            "required_next_authority_action": "restore_all_456_capture_identities_then_ratify_append_only_successor_registry_and_fresh_adjudication",
        },
        "integrity": {
            "canonicalization": CANONICALIZATION,
            "content_sha256": "0" * 64,
            "structural_status": "pass",
            "membership_v2_raw_sha256_preserved": FROZEN_INPUTS[
                "membership_adjudication_v2"
            ]["sha256"],
        },
    }
    value["integrity"]["content_sha256"] = _content_sha256(value)
    return value


def validate_structure(value: Mapping[str, Any]) -> None:
    expected = _constructed_value()
    if set(value) != set(expected):
        raise ValueError("closure-attempt top-level schema drift")
    for key, expected_value in expected.items():
        if key == "integrity":
            continue
        if value[key] != expected_value:
            raise ValueError(f"closure-attempt {key} drift")
    integrity = value["integrity"]
    if set(integrity) != {
        "canonicalization",
        "content_sha256",
        "structural_status",
        "membership_v2_raw_sha256_preserved",
    }:
        raise ValueError("closure-attempt integrity schema drift")
    if (
        integrity["canonicalization"] != CANONICALIZATION
        or integrity["structural_status"] != "pass"
        or integrity["membership_v2_raw_sha256_preserved"]
        != FROZEN_INPUTS["membership_adjudication_v2"]["sha256"]
        or integrity["content_sha256"] != _content_sha256(value)
    ):
        raise ValueError("closure-attempt integrity failure")


def build_closure_attempt() -> dict[str, Any]:
    value = _constructed_value()
    validate_structure(value)
    return value


def validate_closure_attempt(value: Mapping[str, Any]) -> None:
    validate_structure(value)
    if value != _constructed_value():
        raise ValueError("closure attempt does not reproduce from frozen inputs")


def render() -> bytes:
    return canonical_json_bytes(build_closure_attempt())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUT_PATH)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = render()
    if args.check:
        if not args.output.is_file() or args.output.read_bytes() != rendered:
            raise SystemExit(f"artifact drift: {args.output}")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
