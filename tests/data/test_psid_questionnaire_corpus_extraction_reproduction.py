"""On-machine reproduction of the source-bound questionnaire extraction."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
CAPTURE_ROOT = (
    Path("~/PolicyEngine/psid-data").expanduser()
    / "documentation"
    / "capture1"
)
ARTIFACT_PATH = (
    ROOT / "data" / "external" / "psid_questionnaire_corpus_extraction_v1.json"
)

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_psid_questionnaire_corpus_extraction as builder  # noqa: E402


@pytest.mark.skipif(
    not (CAPTURE_ROOT / "browser_digests.txt").is_file(),
    reason="PSID questionnaire capture is not staged",
)
def test_committed_extraction_reproduces_byte_for_byte_from_capture():
    assert builder.render(CAPTURE_ROOT) == ARTIFACT_PATH.read_bytes()
