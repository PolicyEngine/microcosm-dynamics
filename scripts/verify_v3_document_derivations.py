"""Reproduce and attest all 176 §19.3.2 nonquestionnaire derivations.

§21.3.2 requirement 8 admits ``pass_with_closed_failures`` only when
``document_derivations`` and every enclosing source-manifest identity pass.
This script derives the complete relation from the registered documents —
86 ``dictionary_layout``, 47 ``codebook``, and 43 ``raw_fixed_width_data`` —
and prints the attestation.  It emits no artifact and makes no §21 claim:
two normalized-entry members have no source-determined value, so the
codebook derivations are complete only up to
``psid_codebook_extraction.undetermined_entry_members()``.

Usage::

    python scripts/verify_v3_document_derivations.py [--census]

``--census`` additionally reclassifies the complete 89,599-field
denominator from the source-derived codebook relation and asserts the
ratified §20.3.7 terminal counts and digests are unchanged.  That run frames
every raw record and takes several minutes.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import resource
import sys
import time
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from populace_dynamics.data import (  # noqa: E402
    psid_codebook_extraction as codebook,
)
from populace_dynamics.data.psid_dictionary_extraction import (  # noqa: E402
    extract_dictionary_layout_rows,
)
from populace_dynamics.data.psid_source_compiler import (  # noqa: E402
    EvidenceCorpus,
    canonical_sha256,
    derive_all_raw_censuses,
    load_authenticated_evidence,
)

DOCUMENT_ROLE_ORDER = (
    "dictionary_layout",
    "codebook",
    "raw_fixed_width_data",
)
EXPECTED_ROLE_COUNTS = {
    "dictionary_layout": 86,
    "codebook": 47,
    "raw_fixed_width_data": 43,
}


def _raw_derivation_row(document: dict[str, Any], row: dict[str, Any]) -> dict:
    return {
        "source_document_id": document["source_document_id"],
        "derivation_kind": row["derivation_kind"],
        "record_framing": row["record_framing"],
        "record_count": row["record_count"],
        "record_keyset_sha256": row["record_keyset_sha256"],
        "record_domain_sha256": row["record_domain_sha256"],
        "field_census_row_count": row["field_census_row_count"],
        "field_census_keyset_sha256": row["field_census_keyset_sha256"],
        "field_census_domain_sha256": row["field_census_domain_sha256"],
    }


def build_document_derivations(
    corpus: EvidenceCorpus,
) -> tuple[list[dict[str, Any]], dict[tuple[int, str], list[dict[str, Any]]]]:
    """Return the 176 derivation summaries in manifest order."""

    summaries: list[dict[str, Any]] = []
    entries_by_key: dict[tuple[int, str], list[dict[str, Any]]] = {}
    raw_rows = {
        row["source_document_id"]: row
        for row in derive_all_raw_censuses(corpus)
    }
    for document in corpus.source_manifest:
        role = document["document_role"]
        path = document["canonical_source_path"]
        if role == "dictionary_layout":
            derivation = extract_dictionary_layout_rows(document)
        elif role == "codebook":
            derivation = codebook.extract_codebook_rows(document)
            codebook.validate_document_derivation(derivation)
            wave = document["interview_waves"][0]
            for row in derivation["canonical_rows"]:
                entries_by_key.setdefault(
                    (wave, row["raw_field_id"]), row["normalized_entries"]
                )
        elif role == "raw_fixed_width_data":
            derivation = _raw_derivation_row(
                document, raw_rows[document["source_document_id"]]
            )
        else:
            continue
        summary = {
            "source_document_id": document["source_document_id"],
            "canonical_source_path": path,
            "derivation_kind": derivation["derivation_kind"],
            "document_role": role,
        }
        if role == "raw_fixed_width_data":
            summary["row_count"] = derivation["field_census_row_count"]
            summary["domain_sha256"] = derivation["field_census_domain_sha256"]
        else:
            summary["row_count"] = derivation["canonical_row_count"]
            summary["domain_sha256"] = derivation[
                "canonical_row_domain_sha256"
            ]
            summary["parser_family"] = derivation["row_segmentation"][
                "parser_family"
            ]
            summary["decoder_kind"] = derivation["decoder"]["decoder_kind"]
            summary["region_locator_count"] = len(
                derivation["row_segmentation"]["source_region_locators"]
            )
        summaries.append(summary)
    return summaries, entries_by_key


def rebuild_corpus(
    corpus: EvidenceCorpus,
    entries_by_key: dict[tuple[int, str], list[dict[str, Any]]],
) -> EvidenceCorpus:
    """Return the corpus with every codebook relation replaced by source."""

    fields = tuple(
        dataclasses.replace(
            field,
            code_map=tuple(
                (
                    row[0],
                    row[1],
                    entry["source_value_lexeme"],
                    entry["source_meaning"],
                )
                for row, entry in zip(
                    field.code_map, entries_by_key[field.key], strict=True
                )
            ),
            missing_code_map_indices=tuple(
                index
                for index, entry in enumerate(entries_by_key[field.key])
                if entry["typed_disposition"] == "missing"
            ),
        )
        for field in corpus.fields
    )
    return EvidenceCorpus(
        fields=fields,
        source_manifest=corpus.source_manifest,
        artifact_identity_rows=corpus.artifact_identity_rows,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--census", action="store_true")
    arguments = parser.parse_args()

    started = time.time()
    corpus = load_authenticated_evidence()
    print(f"pdftotext {codebook.pdftotext_version()}")
    summaries, entries_by_key = build_document_derivations(corpus)

    counts: dict[str, int] = {}
    rows: dict[str, int] = {}
    for summary in summaries:
        role = summary["document_role"]
        counts[role] = counts.get(role, 0) + 1
        rows[role] = rows.get(role, 0) + summary["row_count"]
    if counts != EXPECTED_ROLE_COUNTS:
        raise SystemExit(f"document role counts: {counts!r}")
    if len(summaries) != 176:
        raise SystemExit(f"document derivation count: {len(summaries)}")

    print(f"document_derivation_count {len(summaries)}")
    for role in DOCUMENT_ROLE_ORDER:
        print(f"  {role}: {counts[role]} documents, {rows[role]} rows")
    print(
        "document_derivation_domain_sha256 " f"{canonical_sha256(summaries)}"
    )
    identifiers = [row["source_document_id"] for row in summaries]
    print(f"document_derivation_keyset_sha256 {canonical_sha256(identifiers)}")

    entries = sum(len(value) for value in entries_by_key.values())
    print(f"codebook_fields {len(entries_by_key)} entries {entries}")
    print(
        "undetermined_entry_members "
        + json.dumps(list(codebook.undetermined_entry_members()))
    )

    if arguments.census:
        from populace_dynamics.data import psid_source_classifier

        censuses = derive_all_raw_censuses(corpus)
        result = psid_source_classifier.classify_complete_corpus(
            rebuild_corpus(corpus, entries_by_key), censuses
        )
        print("census reproduced from the source-derived codebook relation")
        for member in (
            "denominator_sha256",
            "count_array_sha256",
            "ordered_assignment_sha256",
            "failure_reason_rows_sha256",
        ):
            print(f"  {member} {result[member]}")
        print(
            "  counts "
            + json.dumps([row["field_count"] for row in result["count_rows"]])
        )

    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(f"elapsed {time.time() - started:.1f}s peak_rss {peak}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
