"""Guard that d1408 test fixtures never carry the diagnostic's own numbers.

Verification class: labelled diagnostic publication guard. An earlier
draft of these tests copied real counts into fixtures (review round 4).
Two checks stop that recurring:

* Structural (always runs): in every ``tests/test_d1408_*.py`` file, no
  numeric literal other than 0 or 1 sits in a count or weight position (a
  dict value or keyword under a count/weight key, or an argument of the
  ``_cell``/``_rows`` fixture helpers). Those values must come from the
  seeded generator ``tests/d1408_synthetic.py`` (or from Hypothesis), and
  each generator call must use literal arguments so it can be recomputed.
* Private-value (local only): every value the generator produces for these
  tests is recomputed and compared with every number in the diagnostic's
  private aggregates (``scratch/d1408/*-aggregate.json``, git-ignored and
  absent in CI) and in the published JSON. No generated count may lie
  within ten of a real count, which also covers fixtures derived from a
  generated base by a small mechanism difference, and no generated weight
  may equal a real one.
"""

import ast
import json
from pathlib import Path

import pytest

from tests import d1408_synthetic as synthetic

ROOT = Path(__file__).resolve().parents[1]
TEST_FILES = sorted((ROOT / "tests").glob("test_d1408_*.py"))
PRIVATE = sorted((ROOT / "scratch" / "d1408").glob("*-aggregate.json"))
PUBLISHED = (
    ROOT / "docs/errata/2026-10-11-delayed-credit-window-diagnostic.json"
)
COUNT_KEYS = frozenset(
    {
        "people",
        "worker_records",
        "weight",
        "admitted_people",
        "admitted_weight",
        "admitted_worker_records",
        "changed_recipients",
        "changed_receiving_people",
        "seed_cohort_weight",
        "people_upper_bound",
        "weight_upper_bound",
        "real_roster_people",
        "real_roster_weight",
        "mean_draw_admitted_weight",
    }
)
FIXTURE_HELPERS = frozenset({"_cell", "_rows"})
IDENTITY = frozenset({0, 1})


def _literal_numbers(node):
    """Numeric constants in an expression, through tuples and lists only."""
    if isinstance(node, ast.Constant):
        value = node.value
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            yield node
    elif isinstance(node, (ast.Tuple, ast.List)):
        for item in node.elts:
            yield from _literal_numbers(item)


def literal_fixture_numbers(source: str):
    """(line, value) for every non-identity literal in a count position."""
    found = []
    for node in ast.walk(ast.parse(source)):
        candidates = []
        if isinstance(node, ast.Dict):
            candidates = [
                value
                for key, value in zip(node.keys, node.values, strict=True)
                if isinstance(key, ast.Constant) and key.value in COUNT_KEYS
            ]
        elif isinstance(node, ast.keyword) and node.arg in COUNT_KEYS:
            candidates = [node.value]
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in FIXTURE_HELPERS
        ):
            candidates = list(node.args)
        for candidate in candidates:
            for constant in _literal_numbers(candidate):
                if constant.value not in IDENTITY:
                    found.append((constant.lineno, constant.value))
    return found


def generator_calls(source: str):
    """(kind, salt, n) for every synthetic.counts/weights call."""
    calls = []
    for node in ast.walk(ast.parse(source)):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "synthetic"
            and node.func.attr in {"counts", "weights"}
        ):
            salt, n = node.args
            if not (
                isinstance(salt, ast.Constant)
                and isinstance(salt.value, str)
                and isinstance(n, ast.Constant)
                and isinstance(n.value, int)
            ):
                raise AssertionError(
                    f"line {node.lineno}: generator arguments must be literal"
                )
            calls.append((node.func.attr, salt.value, n.value))
    return calls


def test_no_literal_count_or_weight_in_any_d1408_fixture():
    assert TEST_FILES
    offending = {
        path.name: literal_fixture_numbers(path.read_text())
        for path in TEST_FILES
    }
    assert {name: hits for name, hits in offending.items() if hits} == {}


def test_structural_guard_catches_a_copied_count():
    # Placeholder literals standing in for a copied value (not real counts).
    copied = 'cell = {"people": 12345, "weight": 1.0}\n_cell(67890, 0, 2.5)\n'
    assert sorted(v for _, v in literal_fixture_numbers(copied)) == [
        2.5,
        12345,
        67890,
    ]
    clean = 'cell = {"people": base - 4, "weight": 1.0}\n_cell(0, 1, w)\n'
    assert literal_fixture_numbers(clean) == []


def test_generator_calls_are_recomputable_and_deterministic():
    calls = [
        call
        for path in TEST_FILES
        for call in generator_calls(path.read_text())
    ]
    assert calls
    for kind, salt, n in calls:
        produce = getattr(synthetic, kind)
        assert produce(salt, n) == produce(salt, n)
        assert len(produce(salt, n)) == n
    with pytest.raises(AssertionError, match="must be literal"):
        generator_calls("synthetic.counts(name, 2)\n")


def _numbers(value, out):
    if isinstance(value, dict):
        for item in value.values():
            _numbers(item, out)
    elif isinstance(value, list):
        for item in value:
            _numbers(item, out)
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        out.add(float(value))


def collisions(calls, real):
    """Generated values within ten of a real count, or equal to a weight."""
    real_counts = sorted(v for v in real if v.is_integer() and v >= 10)
    hits = []
    for kind, salt, n in calls:
        for value in getattr(synthetic, kind)(salt, n):
            if kind == "counts":
                if any(abs(c - value) <= 10 for c in real_counts):
                    hits.append((salt, value))
            elif float(value) in real:
                hits.append((salt, value))
    return hits


def test_private_value_check_catches_a_near_collision():
    (base,) = synthetic.counts("self-test", 1)
    (weight,) = synthetic.weights("self-test", 1)
    calls = [("counts", "self-test", 1), ("weights", "self-test", 1)]
    assert collisions(calls, {float(base + 7)}) == [("self-test", base)]
    assert collisions(calls, {weight}) == [("self-test", weight)]
    assert collisions(calls, {float(base + 11)}) == []


@pytest.mark.skipif(
    not PRIVATE, reason="private d1408 aggregates exist only on the run host"
)
def test_generated_fixtures_avoid_every_real_count_and_weight():
    real = set()
    for path in [*PRIVATE, PUBLISHED]:
        _numbers(json.loads(path.read_text()), real)
    calls = [
        call
        for path in TEST_FILES
        for call in generator_calls(path.read_text())
    ]
    assert calls
    assert collisions(calls, real) == []
