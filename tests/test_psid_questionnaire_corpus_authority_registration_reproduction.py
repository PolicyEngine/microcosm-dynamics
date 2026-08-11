"""Source-backed reproduction of the PSID corpus-registration attempt."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PSID_CAPTURE_ROOT = (
    Path("~/PolicyEngine/psid-data").expanduser()
    / "documentation"
    / "capture1"
)
ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
ARTIFACT = (
    ROOT
    / "data"
    / "external"
    / "psid_questionnaire_corpus_authority_registration_attempt_v1.json"
)

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_psid_questionnaire_corpus_authority_registration as builder  # noqa: E402


@pytest.mark.skipif(
    not PSID_CAPTURE_ROOT.is_dir(),
    reason="PSID questionnaire corpus capture is not staged",
)
def test_committed_registration_attempt_reproduces_byte_for_byte():
    assert builder.render(PSID_CAPTURE_ROOT) == ARTIFACT.read_bytes()
