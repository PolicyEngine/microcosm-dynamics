"""Pure unit tests for the questionnaire extraction and closure builders."""

from __future__ import annotations

import ast
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_covered_earnings_questionnaire_closure_attempt as closure  # noqa: E402
import build_psid_questionnaire_corpus_extraction as extraction  # noqa: E402

BUILDERS = (
    pytest.param(extraction, id="extraction"),
    pytest.param(closure, id="closure"),
)


@pytest.mark.parametrize("builder", BUILDERS)
def test_canonical_json_is_compact_sorted_ascii_and_lf_terminated(builder):
    assert builder.canonical_json_bytes({"\N{SNOWMAN}": 2, "a": 1}) == (
        b'{"a":1,"\\u2603":2}\n'
    )


@pytest.mark.parametrize("builder", BUILDERS)
@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_canonical_json_rejects_nonfinite_python_numbers(builder, value):
    with pytest.raises(ValueError, match="Out of range float values"):
        builder.canonical_json_bytes({"value": value})


@pytest.mark.parametrize("builder", BUILDERS)
def test_strict_parser_accepts_exactly_representable_json(builder):
    assert builder._strictly_parsed_document(
        b'{"integer":9007199254740993,"decimal":0.5,"text":"ok"}\n',
        "fixture",
    ) == {
        "integer": 9_007_199_254_740_993,
        "decimal": 0.5,
        "text": "ok",
    }


@pytest.mark.parametrize("builder", BUILDERS)
@pytest.mark.parametrize(
    ("raw", "case_id"),
    (
        pytest.param(
            b'{"value":1,"value":2}\n',
            "duplicate-key",
            id="duplicate-key",
        ),
        pytest.param(b'{"value":NaN}\n', "nan", id="nan"),
        pytest.param(
            b'{"value":Infinity}\n',
            "positive-infinity",
            id="positive-infinity",
        ),
        pytest.param(
            b'{"value":-Infinity}\n',
            "negative-infinity",
            id="negative-infinity",
        ),
        pytest.param(b'{"value":1e999}\n', "overflow", id="overflow"),
        pytest.param(
            b'{"value":0.10000000000000001}\n',
            "decimal-fidelity",
            id="decimal-fidelity",
        ),
        pytest.param(
            b'\xef\xbb\xbf{"value":1}\n',
            "utf8-bom",
            id="utf8-bom",
        ),
        pytest.param(
            b'{"value":"\xff"}\n',
            "invalid-utf8",
            id="invalid-utf8",
        ),
    ),
)
def test_strict_parser_rejects_ambiguous_or_noncanonical_inputs(
    builder,
    raw,
    case_id,
):
    del case_id
    with pytest.raises(
        ValueError,
        match=r"^fixture is not a uniquely parseable JSON document$",
    ):
        builder._strictly_parsed_document(raw, "fixture")


@pytest.mark.parametrize("builder", BUILDERS)
def test_builders_import_only_the_standard_library(builder):
    source = Path(builder.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(
                alias.name.split(".", 1)[0] for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".", 1)[0])
    assert imported_roots <= sys.stdlib_module_names
    assert imported_roots.isdisjoint(
        {"numpy", "pandas", "pypdf", "PyPDF2", "populace_dynamics"}
    )


@pytest.mark.parametrize("builder", BUILDERS)
def test_builders_declare_source_only_nonfitting_scope(builder):
    if builder is extraction:
        assert builder.EXTRACTION_METHOD["source_only"] is True
        assert builder.EXTRACTION_METHOD["derived_text_retained"] is False
        assert (
            builder.AUTHORITY_DISPOSITION[
                "membership_v3_or_supersession_effect"
            ]
            == "none"
        )
    else:
        source = Path(builder.__file__).read_text(encoding="utf-8")
        assert '"fitting_or_numeric_targets": False' in source
        assert '"membership_v3_permitted": False' in source
        assert '"operative_effect": "none"' in source
