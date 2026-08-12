"""Pure unit checks for the PSID corpus-registration builder."""

from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_psid_questionnaire_corpus_authority_registration as builder  # noqa: E402


def test_builder_import_is_source_only_in_a_fresh_interpreter():
    source = f"""
import sys
sys.path.insert(0, {str(SCRIPTS)!r})
import build_psid_questionnaire_corpus_authority_registration as builder
assert str(builder.ROOT) == {str(ROOT)!r}
assert not any(
    name == 'populace_dynamics' or name.startswith('populace_dynamics.')
    for name in sys.modules
)
"""
    completed = subprocess.run(
        [sys.executable, "-I", "-c", source],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def test_canonical_json_bytes_freezes_sorting_ascii_compaction_and_lf():
    value = {
        "z": "caf\N{LATIN SMALL LETTER E WITH ACUTE}",
        "a": [1, True, None, 1.25],
    }
    assert builder.canonical_json_bytes(value) == (
        b'{"a":[1,true,null,1.25],"z":"caf\\u00e9"}\n'
    )


def test_canonical_json_bytes_rejects_non_finite_values():
    with pytest.raises(ValueError, match="Out of range float values"):
        builder.canonical_json_bytes({"value": math.nan})


def test_strict_parser_accepts_unique_exact_json_numbers():
    raw = b'{"integer":7,"quarter":0.25,"small":1e-3,"text":"ok"}'
    assert builder._strictly_parsed_document(raw, "fixture") == {
        "integer": 7,
        "quarter": 0.25,
        "small": 0.001,
        "text": "ok",
    }


@pytest.mark.parametrize(
    ("raw", "cause_fragment"),
    [
        (b'{"field":1,"field":2}', "duplicate object key"),
        (b'{"field":NaN}', "non-finite constant NaN"),
        (b'{"field":Infinity}', "non-finite constant Infinity"),
        (b'{"field":-Infinity}', "non-finite constant -Infinity"),
        (b'{"field":1e999}', "non-finite number 1e999"),
        (b'{"field":0.10000000000000001}', "inexact number"),
        (b'\xef\xbb\xbf{"field":1}', "leading U+FEFF BOM"),
        (b'{"field":"\xff"}', "invalid start byte"),
    ],
    ids=[
        "duplicate-key",
        "nan",
        "positive-infinity",
        "negative-infinity",
        "overflowing-exponent",
        "decimal-fidelity",
        "utf8-bom",
        "invalid-utf8",
    ],
)
def test_strict_parser_rejects_ambiguous_or_lossy_documents(
    raw: bytes,
    cause_fragment: str,
):
    with pytest.raises(ValueError, match="uniquely parseable") as error:
        builder._strictly_parsed_document(raw, "fixture")
    assert error.value.__cause__ is not None
    assert cause_fragment in str(error.value.__cause__)
