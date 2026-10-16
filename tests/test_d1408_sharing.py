"""Invented-case checks of d1408's R7 aggregation and trace safeguards.

These unit tests open no PSID, registered result, or external benchmark.
Actual local-PSID reconstruction is a labelled diagnostic, separately run.
"""

import ast
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from d1408_sharing import (  # noqa: E402
    CreditTrace,
    headline_changes,
    imported_source_identity,
    reproduction_check,
    retain_unsupported_rows,
    selected_nodes,
    suppress_complementary_cells,
    trace_group,
)


def test_selected_nodes_exclude_nonmodel_execution():
    source = '''
"""Unselected module prose."""
ANCHOR = explode()
MODEL_CONSTANT = 42
def model():
    return MODEL_CONSTANT
def run():
    explode()
'''
    namespace = {}
    tree = selected_nodes(source, {"model"}, {"MODEL_CONSTANT"})
    exec(compile(tree, "invented", "exec"), namespace)
    assert namespace["model"]() == 42
    assert "ANCHOR" not in namespace
    assert "run" not in namespace
    assert "__doc__" not in namespace


@settings(deadline=None)
@given(st.integers(min_value=-100000, max_value=100000))
def test_selected_model_node_preserves_computation(value):
    source = f"def model():\n    return {value} * 7 + 3\n"
    namespace = {}
    tree = selected_nodes(source, {"model"})
    actual = next(n for n in tree.body if isinstance(n, ast.FunctionDef))
    expected = ast.parse(source).body[0]
    assert ast.dump(actual) == ast.dump(expected)
    exec(compile(tree, "invented", "exec"), namespace)
    assert namespace["model"]() == value * 7 + 3


@settings(deadline=None, max_examples=20)
@given(st.binary(min_size=1, max_size=64))
def test_imported_source_identity_requires_identical_bytes(content):
    from d1408_sharing import EXTRA_PATHS

    left = Path("/invented-d1408-left")
    right = Path("/invented-d1408-right")
    contents = {
        str(root / relative): content
        for root in (left, right)
        for relative in EXTRA_PATHS
    }
    with patch.object(Path, "read_bytes", lambda path: contents[str(path)]):
        proof = imported_source_identity(left, right)
        assert {item["path"] for item in proof} == set(EXTRA_PATHS)
        assert len({item["sha256"] for item in proof}) == 1
        contents[str(right / EXTRA_PATHS[0])] = content + b"different"
        with pytest.raises(RuntimeError, match="closure differs"):
            imported_source_identity(left, right)


@settings(deadline=None)
@given(st.integers(min_value=1, max_value=30))
def test_trace_repeated_calls_are_order_independent_and_deduplicated(n):
    trace = CreditTrace(None, SimpleNamespace(weight={0: 2.0, 1: 3.0}))
    with trace.context(
        recipient=0,
        worker=1,
        stage="baseline",
        basis="original",
        role="linked_survivor_basis",
    ):
        for _ in range(n):
            trace.callback(60, 1930, None)
        trace.callback(48, 1930, None)
        trace.callback(60, 1943, None)
    assert trace.events == {
        (0, 1, "original", "baseline", "linked_survivor_basis", 1930, 60)
    }
    assert trace.recipient is None
    assert trace.worker is None


@settings(deadline=None)
@given(st.integers(min_value=10, max_value=50))
def test_trace_group_counts_unique_recipients_and_worker_bases(n):
    weights = {pid: 2.0 for pid in range(n)}
    trace = CreditTrace(None, SimpleNamespace(weight=weights))
    events = {
        (pid, pid, "original", "baseline", "computed_own_payment", 1930, 60)
        for pid in range(n)
    }
    events |= {
        (pid, pid, "shared", "1a", "linked_survivor_basis", 1930, 60)
        for pid in range(n)
    }
    result = trace_group(trace, events, n * 2.0)
    assert result["admitted_recipients"] == {
        "people": n,
        "worker_records": 2 * n,
        "weight": n * 2.0,
        "admitted_weight_share": 1.0,
    }
    assert result["workers"] == {
        "people": n,
        "worker_records": 2 * n,
        "weight": n * 2.0,
    }


@settings(deadline=None)
@given(st.integers(min_value=1, max_value=9))
def test_trace_group_suppresses_entire_small_cell(n):
    trace = CreditTrace(
        None, SimpleNamespace(weight={pid: 17.0 for pid in range(n)})
    )
    events = {
        (pid, pid, "original", "baseline", "computed_own_payment", 1930, 60)
        for pid in range(n)
    }
    result = trace_group(trace, events, n * 17.0)
    assert set(result["admitted_recipients"].values()) == {"<10"}
    assert set(result["workers"].values()) == {"<10"}


@settings(deadline=None)
@given(st.integers(min_value=1, max_value=9))
def test_headline_changes_suppress_all_small_affected_groups(n):
    result = headline_changes(None, None, None, set(range(n)), set())
    assert result["all_committed_model_headline_changes"] == "<10"
    assert result["status"] == "suppressed"


def test_headline_changes_admit_ten_affected_people(monkeypatch):
    import d1408_sharing

    def reached_computation(*_args):
        raise LookupError("ten-person aggregate is admitted")

    monkeypatch.setattr(d1408_sharing, "model_headlines", reached_computation)
    with pytest.raises(LookupError, match="ten-person aggregate"):
        headline_changes(None, None, None, set(range(10)), set())


def test_trace_context_restores_after_exception():
    trace = CreditTrace(None, None)
    with pytest.raises(RuntimeError):
        with trace.context(recipient=17, worker=42):
            assert trace.recipient == 17
            raise RuntimeError("invented exception")
    assert trace.recipient is None
    assert trace.worker is None


def test_trace_refuses_unattributed_flagged_credit():
    trace = CreditTrace(None, None)
    with pytest.raises(RuntimeError, match="no worker attribution"):
        trace.callback(60, 1930, None)


def test_exact_cost_cross_check_detects_changed_headline(monkeypatch):
    import d1408_sharing

    actual = {
        "n_scored": 10,
        "aggregate": {
            "weighted_aggregate_pct_change_1b": -4.23,
            "weighted_aggregate_pct_change_1b_noscalar": -8.35,
        },
    }
    expected = {
        "earnings_sharing": {
            "n_scored_couples_frame": 10,
            "our_delta_1b": -4.23 / 100,
            "our_delta_1b_pct": -4.23,
            "our_delta_1b_noscalar": -8.35 / 100,
            "our_delta_1b_noscalar_pct": -8.35,
        }
    }
    monkeypatch.setattr(d1408_sharing, "model_headlines", lambda *_: actual)
    result = reproduction_check(None, None, expected, "cost_ordering_r7")
    assert result["exact"] is True
    assert result["quantities_checked"] == 5
    expected["earnings_sharing"]["our_delta_1b_pct"] += 0.01
    result = reproduction_check(None, None, expected, "cost_ordering_r7")
    assert result["exact"] is False
    assert result["counts_verified"] is False
    assert result["mismatch_names"] == ["our_delta_1b_pct"]


@settings(deadline=None)
@given(st.integers(min_value=0, max_value=20))
def test_unsupported_placeholders_preserve_dtypes_and_denominator(n):
    import pandas as pd

    legacy = pd.DataFrame({"person_id": range(n), "baseline": [100.0] * n})
    statutory = legacy.copy()
    statutory["baseline"] += 1.0
    unchanged = statutory.copy()
    result = retain_unsupported_rows(legacy, statutory, set())
    pd.testing.assert_frame_equal(result, unchanged)
    if n:
        result = retain_unsupported_rows(legacy, statutory, {0})
        assert result.loc[0, "baseline"] == 100.0
        pd.testing.assert_series_equal(result.dtypes, legacy.dtypes)
        assert list(result.person_id) == list(legacy.person_id)
        assert list(result.loc[result.person_id != 0, "baseline"]) == [
            101.0
        ] * (n - 1)


@settings(deadline=None)
@given(st.integers(min_value=10, max_value=50))
def test_complementary_sex_suppression_withholds_count_and_changes(n):
    cells = {
        "1b": {
            "widowed:male": {"affected_people": "<10", "changes": "<10"},
            "widowed:female": {"affected_people": n, "changes": 0.0},
            "married:male": {"affected_people": 0, "changes": 0.0},
            "married:female": {"affected_people": 0, "changes": 0.0},
        }
    }
    result = suppress_complementary_cells(cells)
    assert set(result["1b"]["widowed:female"].values()) == {
        "suppressed_complementary"
    }
    assert result["1b"]["widowed:male"]["affected_people"] == "<10"
    assert result["1b"]["married:male"] == {
        "affected_people": 0,
        "changes": 0.0,
    }
    assert suppress_complementary_cells(result) == result
