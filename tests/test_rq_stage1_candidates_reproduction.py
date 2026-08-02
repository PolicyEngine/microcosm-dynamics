"""Capture-backed reproduction for all 81 R_Q candidate documents."""

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

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_rq_stage1_candidates as builder  # noqa: E402


def test_all_candidate_documents_batches_and_index_reproduce_byte_for_byte():
    if not (CAPTURE_ROOT / "browser_digests.txt").is_file():
        pytest.skip("PSID questionnaire capture is not staged")
    replay_artifact = builder.load_source_replay()
    for batch_index in range(1, 10):
        outputs, manifest = builder.build_batch(
            replay_artifact, batch_index, CAPTURE_ROOT
        )
        for path, raw in outputs:
            assert raw == path.read_bytes()
        assert builder.source_tools.canonical_json_bytes(manifest) == (
            builder.batch_manifest_path(batch_index).read_bytes()
        )

    rebuilt_index = builder.build_candidate_index(replay_artifact)
    assert builder.source_tools.canonical_json_bytes(rebuilt_index) == (
        builder.INDEX_PATH.read_bytes()
    )
