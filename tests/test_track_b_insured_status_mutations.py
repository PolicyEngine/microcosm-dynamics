"""Statutory conformance: review mutation evidence stays with design notes.

Invented and captured statutory cases only; no population or forecast claim.
"""

import json
from pathlib import Path


def test_mutation_report_is_retained_with_its_design_note():
    root = Path(__file__).resolve().parents[1]
    name = "track_b_insured_status_mutations.json"
    report = root / "docs" / "design" / name
    assert report.is_file()
    assert (
        name
        in (root / "docs" / "design" / "track_b_insured_status.md").read_text()
    )
    evidence = json.loads(report.read_text())
    assert evidence["verification_class"] == "statutory_conformance"
    assert not (
        root
        / "tests"
        / "data"
        / "track_b"
        / "insured_status_mutation_checks.json"
    ).exists()
