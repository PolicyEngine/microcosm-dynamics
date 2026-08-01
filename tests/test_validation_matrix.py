"""Reproduction pin for the reviewed cross-model validation matrix."""

import hashlib
import json
from pathlib import Path

MATRIX_PATH = (
    Path(__file__).resolve().parents[1]
    / "analysis"
    / "validation-matrix"
    / "matrix.json"
)
MATRIX_SHA256 = (
    "be74b69a2c337eade36822124a5bc67a8bbdf0364167db16b2a65782f834599e"
)
MATRIX_ROW_COUNT = 42


def test__validation_matrix__matches_reviewed_sha_and_row_count():
    raw = MATRIX_PATH.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == MATRIX_SHA256

    matrix = json.loads(raw)
    assert matrix["row_count"] == MATRIX_ROW_COUNT
    assert len(matrix["rows"]) == MATRIX_ROW_COUNT
