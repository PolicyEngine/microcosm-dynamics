"""Run or assemble the aggregate-only delayed-credit diagnostic.

Verification class: labelled diagnostic under ruling d1408. Admitted
scope: six retained model results, using local PSID. No registered entry
point or output is executed, replaced, or written. Published changes use
42 USC 402(w)(2)(A); unsupported pre-1917 records have no statutory amount.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

try:
    from scripts.d1408_common import HEADER, PSID_ROOT, ROOT, SCRATCH
except ModuleNotFoundError:
    from d1408_common import HEADER, PSID_ROOT, ROOT, SCRATCH

DESTINATION = (
    ROOT / "docs/errata/2026-10-11-delayed-credit-window-diagnostic.json"
)
EXPECTED_ARTIFACTS = frozenset(
    {
        "runs/first_estimates_v1.json",
        "runs/replication_urban2010_cola_v1.json",
        "runs/replication_urban2010_fra68_v1.json",
        "runs/replication_urban2006_minimum_benefit_v1.json",
        "runs/replication_r7_sharing_v1.json",
        "runs/replication_cost_ordering_v1.json",
    }
)
PROJECTION_ARTIFACTS = frozenset(
    {
        "runs/replication_urban2010_cola_v1.json",
        "runs/replication_urban2010_fra68_v1.json",
    }
)


def assemble():
    """Assemble only already-suppressed aggregates; do not read microdata."""
    results = []
    for name in ("first-estimates", "minimum", "sharing", "cola", "fra68"):
        path = SCRATCH / f"{name}-aggregate.json"
        if not path.is_file():
            raise FileNotFoundError(f"diagnostic aggregate missing: {name}")
        part = json.loads(path.read_text())
        if name == "sharing":
            results.extend(part["results"])
        else:
            results.append(part)
    validate_result_scope(results)
    validate_projection_publication(results)
    for result in results:
        if result.get("artifact") in PROJECTION_ARTIFACTS:
            result["pre1917_flagged_evaluations"] = projection_pre1917(result)
        if "real_data_files_read" in result:
            result["real_data_files_read"] = [
                psid_relative(path) for path in result["real_data_files_read"]
            ]
    document = {
        "header": HEADER,
        "schema_version": 1,
        "verification_class": "labelled diagnostic",
        "ruling": "d1408 (2026-10-12)",
        "registered_artifacts_retained": True,
        "privacy": "aggregate counts and changes only; positive cells below ten people are suppressed together with weights, shares and changes; overlapping subtotals are withheld where subtraction would reveal a small complementary group",
        "statutory_authority": [
            "42 USC 402(w)(2)(A)",
            "42 USC 402(w)(6)(A)",
            "POMS RS 00615.692D-E",
        ],
        "results": results,
    }
    validate_publication(document)
    DESTINATION.write_text(
        json.dumps(document, indent=2, allow_nan=False) + "\n"
    )
    return document


def projection_pre1917(result):
    """State the projections' pre-1917 flags; cells exist only if flagged."""
    present = any(
        key.startswith("unsupported_pre1917/")
        for wave in result.get("counts", {}).values()
        for key in wave
    )
    return "see counts" if present else 0


def psid_relative(path):
    """Publish a PSID file read relative to the PSID root, never a home."""
    resolved = Path(path)
    try:
        return str(Path("psid-data") / resolved.relative_to(PSID_ROOT))
    except ValueError:
        if resolved.is_absolute():
            raise ValueError("real-data read outside the PSID root") from None
        return str(resolved)


def validate_result_scope(results):
    """Require every authorized retained artifact exactly once."""
    identities = [result.get("artifact") for result in results]
    if len(identities) != 6 or set(identities) != EXPECTED_ARTIFACTS:
        raise ValueError(
            "the d1408 scope requires six distinct authorized artifacts"
        )


def validate_projection_publication(results):
    """Require the completed private cross-result audit before assembly."""
    projections = [
        result
        for result in results
        if result.get("artifact") in PROJECTION_ARTIFACTS
    ]
    if len(projections) != 2:
        raise ValueError("both audited projection diagnostics required")
    for result in projections:
        audit = result.get("cross_result_publication_audit")
        if (
            not isinstance(audit, dict)
            or audit.get("completed") is not True
            or audit.get("temporary_memberships_deleted") is not True
            or not isinstance(audit.get("method"), str)
            or not audit["method"].strip()
        ):
            raise ValueError("projection publication audit is incomplete")


def validate_publication(value):
    """Refuse record payloads and incomplete small-cell suppression."""
    forbidden = {
        "person_id",
        "person_ids",
        "worker_record_id",
        "record_id",
        "microdata",
        "individual_amount",
    }
    if isinstance(value, dict):
        if forbidden.intersection(value):
            raise ValueError("record-level field in diagnostic publication")
        count_fields = {
            "people",
            "worker_people",
            "worker_records",
            "affected_people",
            "affected_worker_records",
            "admitted_people",
            "changed_recipients",
            "changed_receiving_people",
            "people_upper_bound",
            "supported_flagged_worker_people",
            "unsupported_flagged_worker_people",
        }
        for key, item in value.items():
            if (
                key in count_fields
                and isinstance(item, (int, float))
                and not isinstance(item, bool)
                and 0 < item < 10
            ):
                raise ValueError("unsuppressed small count in publication")
            if key == "records" and isinstance(item, (dict, list)):
                raise ValueError(
                    "record-level field in diagnostic publication"
                )
            if any(
                word in key.lower()
                for word in ("benchmark", "dynasim", "comparator")
            ) and isinstance(item, (int, float, dict, list)):
                raise ValueError("external benchmark payload in publication")
            validate_publication(item)
        markers = {"<10", "suppressed_complementary"}
        hidden = any(
            value.get(key) in markers
            for key in count_fields
            if isinstance(value.get(key), str)
        )
        if hidden:
            for key, item in value.items():
                monetary = any(
                    word in key
                    for word in ("weight", "share", "change", "headline")
                )
                public_denominator = (
                    key == "admitted_weight"
                    and isinstance(value.get("admitted_people"), (int, float))
                    and value["admitted_people"] >= 10
                )
                description = key.endswith(
                    ("_reason", "_definition", "_denominator")
                )
                if (
                    monetary
                    and not public_denominator
                    and not description
                    and item is not None
                    and not (isinstance(item, str) and item in markers)
                ):
                    raise ValueError("incomplete small-cell suppression")
    elif isinstance(value, list):
        for item in value:
            validate_publication(item)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--assemble-only", action="store_true")
    args = parser.parse_args()
    if not args.assemble_only:
        if not PSID_ROOT.is_dir():
            raise FileNotFoundError(
                "d1408 requires the authorized local PSID root"
            )
        env = dict(os.environ, OMP_NUM_THREADS="1", POLARS_MAX_THREADS="1")
        env["PYTHONPATH"] = f"{ROOT / 'src'}:{ROOT / 'scripts'}:{ROOT}"
        commands = [
            ["d1408_first_estimates.py"],
            ["d1408_minimum.py"],
            ["d1408_sharing.py"],
            ["d1408_projection.py", "cola"],
            ["d1408_projection.py", "fra68"],
            ["d1408_projection.py", "publication"],
        ]
        for command in commands:
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / command[0]),
                    *command[1:],
                ],
                cwd=ROOT,
                env=env,
                check=True,
            )
    assemble()


if __name__ == "__main__":
    main()
