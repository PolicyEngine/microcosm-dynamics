"""Capture-backed reproduction for the R_Q stage-1 replay parent."""

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
ARTIFACT_PATH = (
    ROOT / "docs" / "analysis" / "rq_stage1_evidence" / "source_replay_v1.json"
)

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_rq_stage1_source_replay as builder  # noqa: E402


@pytest.fixture(scope="module")
def reproduced_source_replay() -> bytes:
    if not (CAPTURE_ROOT / "browser_digests.txt").is_file():
        pytest.skip("PSID questionnaire capture is not staged")
    return builder.render_source_replay(CAPTURE_ROOT)


def test_source_replay_reproduces_from_pinned_roots_and_bytes(
    reproduced_source_replay: bytes,
):
    assert reproduced_source_replay == ARTIFACT_PATH.read_bytes()


def test_reproduced_source_replay_passes_mirrored_validator(
    reproduced_source_replay: bytes,
):
    value = builder.replay.strict_parse_document(
        reproduced_source_replay, "reproduced R_Q source replay"
    )
    assert isinstance(value, dict)
    builder.validate_source_replay(value)
