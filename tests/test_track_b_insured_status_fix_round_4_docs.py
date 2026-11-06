"""Statutory conformance: retained insured-status dispatch evidence.

Invented/captured source declarations only; no population or forecast claim.
"""

import json
from pathlib import Path


def test_rulespec_dispatch_names_retained_exhibit_and_original_body_hashes():
    root = Path(__file__).resolve().parents[1]
    dispatch = (
        root / "docs/design/track_b_insured_status_rulespec_issue.md"
    ).read_text()
    sources = json.loads(
        (
            root / "tests/data/track_b/insured_status_sources/manifest.json"
        ).read_text()
    )["sources"]
    exhibit = next(
        source
        for source in sources
        if source["id"] == "poms_rs_00301_800_exhibit"
    )
    assert exhibit["file"] in dispatch
    assert exhibit["sha256"] in dispatch
    for body in exhibit["served_bodies"]:
        assert body["sha256"] in dispatch
    assert "request the exhibit capture" not in dispatch
