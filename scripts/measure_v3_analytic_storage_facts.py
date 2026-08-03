"""Measure the §22.4.5 storage facts from the authenticated source corpus.

The script reconstructs the complete 89,599-field relation, then accumulates
the exact population §22.4.5 pins: the per-status range-member decomposition,
the threshold partition of every named ``renderable_member_rows`` and
``unrenderable_member_rows`` relation value, and the arm-ambiguous renderable
members of the finite-domain arm-ambiguous branch.  No count is read from the
design; every one is derived and only then compared.

Usage::

    PYTHONPATH=src python scripts/measure_v3_analytic_storage_facts.py \
        --output runs/v3_analytic_storage_facts_v1.json
"""

from __future__ import annotations

import argparse
import json
import resource
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from populace_dynamics.data import (  # noqa: E402
    psid_amendment8_vectors as a8,
)
from populace_dynamics.data.psid_analytic_partition import (  # noqa: E402
    MEMBER_THRESHOLD,
)
from populace_dynamics.data.psid_source_classifier import (  # noqa: E402
    COMPILED,
    FINITE_ARM_AMBIGUOUS,
    PADDING_UNDERDETERMINED,
    PARTIAL_RANGE,
    classify_complete_corpus,
    normalize_field_entries,
    range_member_runs,
)
from populace_dynamics.data.psid_source_compiler import (  # noqa: E402
    DEFAULT_PSID_ROOT,
    canonical_sha256,
    derive_all_raw_censuses,
    load_authenticated_evidence,
)

COMPILED_STATUSES = (
    COMPILED,
    PADDING_UNDERDETERMINED,
    FINITE_ARM_AMBIGUOUS,
    PARTIAL_RANGE,
)


def measure(psid_root: Path) -> dict[str, object]:
    corpus = load_authenticated_evidence(psid_root=psid_root)
    censuses = derive_all_raw_censuses(corpus, psid_root)

    fields = Counter()
    entries = Counter()
    members = Counter()
    totals = Counter()

    def observe(field, detail) -> None:
        status = detail.derivation_status
        if status not in COMPILED_STATUSES:
            return
        fields[status] += 1
        _, ranges = normalize_field_entries(field)
        by_index = {item.index: item for item in ranges}
        for row in detail.range_renderability_counts:
            entries[status] += 1
            members[status] += row["source_member_count"]
            renderable = row["renderable_member_count"]
            unrenderable = row["unrenderable_member_count"]
            if renderable is None or unrenderable is None:
                raise ValueError(
                    "a compiled range lacks its renderability partition"
                )
            if status == FINITE_ARM_AMBIGUOUS:
                totals["arm_ambiguous_renderable_members"] += row[
                    "arm_ambiguous_renderable_member_count"
                ]
            # Rebuild the same partition as unique maximal index runs, then
            # require the run cardinalities to reproduce the counts the
            # ratified census already validated.
            runs = range_member_runs(
                by_index[row["source_entry_index"]],
                detail.selected_token_form,
                detail.selected_width,
                detail.selected_decimal_places,
            )
            if (runs.renderable_count, runs.unrenderable_count) != (
                renderable,
                unrenderable,
            ):
                raise ValueError(
                    "analytic runs disagree with the classified partition"
                )
            for count, arm_runs, arm in (
                (renderable, runs.renderable, "renderable"),
                (unrenderable, runs.unrenderable, "unrenderable"),
            ):
                if count <= MEMBER_THRESHOLD:
                    totals["explicit_members"] += count
                    totals["explicit_containers"] += 1
                    continue
                totals["analytic_members"] += count
                totals[f"analytic_{arm}_members"] += count
                totals[f"analytic_{arm}_containers"] += 1
                totals["analytic_intervals"] += len(arm_runs)
                totals[f"analytic_{arm}_intervals"] += len(arm_runs)
            totals["partition_rows"] += 1

    census = classify_complete_corpus(corpus, censuses, observer=observe)

    explicit_members = totals["explicit_members"]
    explicit_containers = totals["explicit_containers"]
    analytic_members = totals["analytic_members"]
    analytic_renderable_members = totals["analytic_renderable_members"]
    analytic_unrenderable_members = totals["analytic_unrenderable_members"]
    analytic_renderable_containers = totals["analytic_renderable_containers"]
    analytic_unrenderable_containers = totals[
        "analytic_unrenderable_containers"
    ]
    arm_ambiguous_renderable_members = totals[
        "arm_ambiguous_renderable_members"
    ]
    interval_rows = totals["partition_rows"]

    decomposition = tuple(
        (status, fields[status], entries[status], members[status])
        for status in COMPILED_STATUSES
    )
    facts = a8.StorageFacts(
        status_decomposition=decomposition,
        total_members=sum(members.values()),
        explicit_members=explicit_members,
        analytic_members=analytic_members,
        analytic_renderable_members=analytic_renderable_members,
        analytic_unrenderable_members=analytic_unrenderable_members,
        analytic_renderable_containers=analytic_renderable_containers,
        analytic_unrenderable_containers=analytic_unrenderable_containers,
        arm_ambiguous_renderable_members=arm_ambiguous_renderable_members,
    )
    r04 = a8.a8_r04(facts)
    vectors = a8.run_amendment_8_vectors(facts)

    payload = {
        "schema_version": "v3_analytic_storage_facts.v1",
        "amendment_8_vector_identity": a8.a8_vector_relation_identity(),
        "amendment_8_vector_results": list(vectors),
        "denominator_sha256": census["denominator_sha256"],
        "count_array_sha256": census["count_array_sha256"],
        "ordered_assignment_sha256": census["ordered_assignment_sha256"],
        "failure_reason_rows_sha256": census["failure_reason_rows_sha256"],
        "status_decomposition_rows": [
            {
                "derivation_status": status,
                "field_count": field_count,
                "numeric_range_entry_count": entry_count,
                "logical_source_range_member_count": member_count,
            }
            for status, field_count, entry_count, member_count in decomposition
        ],
        "complete_field_count": sum(fields.values()),
        "complete_range_entry_count": sum(entries.values()),
        "complete_member_count": facts.total_members,
        "explicit_arm_member_count": explicit_members,
        "explicit_arm_container_count": explicit_containers,
        "analytic_arm_member_count": analytic_members,
        "analytic_arm_renderable_member_count": (
            analytic_renderable_members
        ),
        "analytic_arm_unrenderable_member_count": (
            analytic_unrenderable_members
        ),
        "analytic_arm_renderable_container_count": (
            analytic_renderable_containers
        ),
        "analytic_arm_unrenderable_container_count": (
            analytic_unrenderable_containers
        ),
        "arm_ambiguous_renderable_member_count": (
            arm_ambiguous_renderable_members
        ),
        "range_partition_row_count": interval_rows,
        "analytic_arm_interval_count": totals["analytic_intervals"],
        "analytic_arm_renderable_interval_count": totals[
            "analytic_renderable_intervals"
        ],
        "analytic_arm_unrenderable_interval_count": totals[
            "analytic_unrenderable_intervals"
        ],
        "a8_r04_result": r04,
    }
    payload["facts_sha256"] = canonical_sha256(payload)
    return payload


def serialize(payload: dict[str, object]) -> bytes:
    """Return the committed byte sequence for *payload*."""

    return (
        json.dumps(payload, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--psid-root", type=Path, default=DEFAULT_PSID_ROOT)
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "reconstruct independently in this fresh process and byte-compare "
            "the committed artifact instead of writing one"
        ),
    )
    arguments = parser.parse_args()
    payload = serialize(measure(arguments.psid_root))
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if arguments.check:
        committed = arguments.output.read_bytes()
        if committed != payload:
            print(
                f"--check FAILED: {len(committed)} committed bytes differ "
                f"from {len(payload)} rebuilt bytes",
                file=sys.stderr,
            )
            return 1
        print(
            f"--check ok: {len(payload)} bytes byte-equal; "
            f"peak RSS {peak} bytes"
        )
        return 0
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_bytes(payload)
    print(payload.decode("utf-8"))
    print(f"peak RSS {peak} bytes", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
