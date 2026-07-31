#!/usr/bin/env python3
"""Build the physical-only PSID modern job-context reader registry."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from populace_dynamics.data import psid_job_context_registry


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dictionary-audit",
        type=Path,
        default=Path(psid_job_context_registry.DICTIONARY_AUDIT_PATH),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "data/external/"
            "psid_modern_job_context_raw_extraction_specs_v1.json"
        ),
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    audit_bytes = args.dictionary_audit.read_bytes()
    audit = json.loads(audit_bytes)
    audit_sha256 = hashlib.sha256(audit_bytes).hexdigest()
    registry = psid_job_context_registry.build_raw_extraction_registry(
        audit,
        dictionary_audit_file_sha256=audit_sha256,
    )
    rendered = psid_job_context_registry.render_registry(
        registry,
        audit,
        dictionary_audit_file_sha256=audit_sha256,
    )
    if args.check:
        if not args.output.is_file():
            raise SystemExit(f"missing committed registry: {args.output}")
        if args.output.read_bytes() != rendered:
            raise SystemExit(
                f"committed registry differs from source audit: {args.output}"
            )
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
