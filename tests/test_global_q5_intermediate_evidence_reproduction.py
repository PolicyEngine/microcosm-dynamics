"""Capture-backed reproduction of the global Q5 intermediate evidence."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
CAPTURE_ROOT = (
    Path("~/PolicyEngine/psid-data").expanduser()
    / "documentation"
    / "capture1"
)
EVIDENCE_DIRECTORY = ROOT / "docs" / "analysis" / "global_q5_evidence"
CATALOG_PATH = (
    EVIDENCE_DIRECTORY / "global_relationship_catalog_evidence_v1.json"
)
ABSENCE_STOP_PATH = (
    EVIDENCE_DIRECTORY / "global_absence_domain_stop_evidence_v1.json"
)

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_global_q5_intermediate_evidence as builder  # noqa: E402

ERA_PATHS = tuple(
    EVIDENCE_DIRECTORY / f"{spec['era_id']}_slot_evidence_v1.json"
    for spec in builder.ERA_SPECS
)


@pytest.fixture(scope="module")
def reproduced_catalog() -> dict:
    if not (CAPTURE_ROOT / "browser_digests.txt").is_file():
        pytest.skip("PSID questionnaire capture is not staged")
    return builder.build_catalog_evidence(CAPTURE_ROOT)


def test_catalog_reproduces_from_capture(reproduced_catalog: dict):
    assert builder.canonical_json_bytes(reproduced_catalog) == (
        CATALOG_PATH.read_bytes()
    )


@pytest.mark.skipif(
    not all(path.is_file() for path in ERA_PATHS),
    reason="all six staged era artifacts have not landed yet",
)
def test_all_six_era_artifacts_reproduce_from_catalog_capture(
    reproduced_catalog: dict,
):
    for spec in builder.ERA_SPECS:
        era_id = spec["era_id"]
        era_path = EVIDENCE_DIRECTORY / f"{era_id}_slot_evidence_v1.json"
        era = builder.build_era_evidence(reproduced_catalog, era_id)
        assert builder.canonical_json_bytes(era) == era_path.read_bytes()


@pytest.mark.skipif(
    not all(path.is_file() for path in ERA_PATHS),
    reason="all six staged era artifacts have not landed yet",
)
def test_absence_stop_reproduces_from_committed_intermediates(
    reproduced_catalog: dict,
):
    eras = {
        spec["era_id"]: builder.build_era_evidence(
            reproduced_catalog, spec["era_id"]
        )
        for spec in builder.ERA_SPECS
    }
    artifact = builder.build_absence_stop_evidence(reproduced_catalog, eras)
    assert (
        builder.canonical_json_bytes(artifact)
        == ABSENCE_STOP_PATH.read_bytes()
    )
