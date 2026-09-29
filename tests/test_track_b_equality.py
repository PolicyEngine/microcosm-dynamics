"""Invented-data checks of B1's exact per-person reproduction contract."""

from __future__ import annotations

import copy
import json
import types

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b.equality import compare_frames, compare_replay


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "person_id": [101, 202, 303, 101, 202, 303],
            "period": [2016, 2016, 2016, 2018, 2018, 2018],
            "earnings": [0.0, 12000.0, 30000.0, 100.0, 13000.0, 31000.0],
            "weight": [0.5, 1.0, 1.5, 0.5, 1.0, 1.5],
            "age": [25, 35, 45, 27, 37, 47],
        }
    )


def _payload() -> dict:
    return {
        "scored": _frame(),
        "fit_signature": {"sha256": "invented-fit", "rho": -0.6},
        "rng_signature": {
            "n_periods": 8,
            "addresses": [[1, "earnings"], [2, "earnings"]],
        },
    }


def _runs() -> dict:
    return {(seed, draw): _payload() for seed in (0, 1) for draw in (0, 1)}


def _compare(expected: dict, actual: dict) -> dict:
    return compare_replay(
        expected, actual, registered_seeds=(0, 1), registered_draws=(0, 1)
    )


def test_exact_reproduction_and_deterministic_diagnostics():
    expected = _runs()
    actual = copy.deepcopy(expected)
    for payload in actual.values():
        payload["scored"] = payload["scored"].iloc[::-1, ::-1]
    report = _compare(expected, actual)
    assert report["status"] == "REPRODUCED"
    assert report["verification_class"] == "reproduction"
    assert report["differences"] == []
    assert len(report["comparisons"]) == 4
    assert json.dumps(report, sort_keys=True, allow_nan=False) == json.dumps(
        _compare(expected, actual), sort_keys=True, allow_nan=False
    )


@settings(deadline=None)
@given(
    row=st.integers(min_value=0, max_value=5),
    column=st.sampled_from(["earnings", "weight", "age"]),
    seed=st.integers(min_value=0, max_value=1),
    draw=st.integers(min_value=0, max_value=1),
)
def test_any_single_person_perturbation_is_reported(row, column, seed, draw):
    expected = _runs()
    actual = copy.deepcopy(expected)
    actual[seed, draw]["scored"].loc[row, column] += 1
    report = _compare(expected, actual)
    assert report["status"] == "BASELINE_REPLAY_MISMATCH"
    assert len(report["differences"]) == 1
    difference = report["differences"][0]
    assert difference["kind"] == "value"
    assert difference["column"] == column
    assert difference["seed"] == seed
    assert difference["draw"] == draw
    assert difference["key"]["person_id"]["bytes"] == (
        expected[seed, draw]["scored"]["person_id"].iloc[row].tobytes().hex()
    )


@pytest.mark.parametrize("column", ["earnings", "weight"])
def test_one_bit_float_change_including_signed_zero_fails(column):
    expected = _frame()
    actual = expected.copy()
    if column == "earnings":
        actual.loc[0, column] = -0.0
    else:
        actual.loc[0, column] = np.nextafter(actual.loc[0, column], np.inf)
    report = compare_frames(expected, actual)
    assert not report["equal"]
    assert report["differences"][0]["expected"]["bytes"] != (
        report["differences"][0]["actual"]["bytes"]
    )


def test_nan_payloads_are_compared_by_bits():
    expected = _frame()
    actual = _frame()
    expected_values = expected["earnings"].to_numpy(copy=True)
    actual_values = actual["earnings"].to_numpy(copy=True)
    expected_values.view("uint64")[0] = 0x7FF8000000000001
    actual_values.view("uint64")[0] = 0x7FF8000000000002
    expected["earnings"] = expected_values
    actual["earnings"] = actual_values
    assert not compare_frames(expected, actual)["equal"]


@pytest.mark.parametrize("column", ["earnings", "weight", "age"])
def test_dtype_is_material(column):
    expected = _frame()
    actual = expected.copy()
    actual[column] = actual[column].astype("float32")
    differences = compare_frames(expected, actual)["differences"]
    assert any(item["kind"] == "dtype" for item in differences)


def test_unordered_categorical_dtype_order_is_material():
    expected, actual = _frame(), _frame()
    values = ["a", "b", "a", "b", "a", "b"]
    expected["cohort"] = pd.Categorical(values, categories=["a", "b"])
    actual["cohort"] = pd.Categorical(values, categories=["b", "a"])
    assert expected["cohort"].dtype == actual["cohort"].dtype
    differences = compare_frames(expected, actual)["differences"]
    assert len(differences) == 1
    assert differences[0]["kind"] == "dtype"


def test_support_missing_extra_duplicate_and_null_rows_fail():
    expected = _frame()
    missing = expected.iloc[1:]
    assert compare_frames(expected, missing)["differences"][0]["kind"] == (
        "missing_row"
    )
    extra = expected.copy()
    extra.loc[0, "person_id"] = 999
    assert {
        item["kind"] for item in compare_frames(expected, extra)["differences"]
    } == {
        "missing_row",
        "extra_row",
    }
    duplicate = pd.concat([expected, expected.iloc[[0]]], ignore_index=True)
    assert any(
        item["kind"] == "duplicate_key"
        for item in compare_frames(expected, duplicate)["differences"]
    )
    null = expected.copy()
    null["person_id"] = null["person_id"].astype("Int64")
    null.loc[0, "person_id"] = pd.NA
    assert any(
        item["kind"] == "null_key"
        for item in compare_frames(expected, null)["differences"]
    )


@pytest.mark.parametrize("field", ["fit_signature", "rng_signature"])
def test_signature_changes_have_full_paths(field):
    expected = _runs()
    actual = copy.deepcopy(expected)
    if field == "fit_signature":
        actual[1, 0][field]["rho"] = np.nextafter(-0.6, 0.0).item()
        suffix = ["rho"]
    else:
        actual[1, 0][field]["addresses"][1][0] = 99
        suffix = ["addresses", 1, 0]
    report = _compare(expected, actual)
    assert report["status"] == "BASELINE_REPLAY_MISMATCH"
    assert report["differences"][0]["path"] == [field, *suffix]


def test_deep_signature_signed_zero_is_material():
    expected = _runs()
    actual = copy.deepcopy(expected)
    expected[0, 0]["fit_signature"]["rho"] = 0.0
    actual[0, 0]["fit_signature"]["rho"] = -0.0
    assert not _compare(expected, actual)["equal"]


@pytest.mark.parametrize("side", ["expected", "actual"])
def test_missing_registered_seed_draw_fails(side):
    expected, actual = _runs(), _runs()
    {"expected": expected, "actual": actual}[side].pop((1, 1))
    report = _compare(expected, actual)
    assert report["status"] == "BASELINE_REPLAY_MISMATCH"
    assert report["differences"] == [
        {"kind": "missing_seed_draw", "side": side, "seed": 1, "draw": 1}
    ]


def test_extra_draw_does_not_replace_registered_draw():
    expected, actual = _runs(), _runs()
    actual[1, 2] = actual.pop((1, 1))
    kinds = {
        item["kind"] for item in _compare(expected, actual)["differences"]
    }
    assert kinds == {"missing_seed_draw", "extra_seed_draw"}


@pytest.mark.parametrize(
    "seeds,draws", [((), (0,)), ((0,), ()), ((0, 0), (0,))]
)
def test_empty_or_duplicate_registration_never_passes(seeds, draws):
    report = compare_replay(
        {}, {}, registered_seeds=seeds, registered_draws=draws
    )
    assert report["status"] == "BASELINE_REPLAY_MISMATCH"


def test_empty_frames_never_pass():
    frame = _frame().iloc[:0]
    assert not compare_frames(frame, frame)["equal"]


@pytest.mark.parametrize(
    "field", ["earnings", "weight", "fit_signature", "rng_signature"]
)
def test_missing_required_values_on_both_sides_never_pass(field):
    expected, actual = _runs(), _runs()
    for runs in (expected, actual):
        if field in ("earnings", "weight"):
            runs[0, 0]["scored"] = runs[0, 0]["scored"].drop(columns=field)
        else:
            del runs[0, 0][field]
    assert not _compare(expected, actual)["equal"]


def test_optional_explicit_support_and_weights_are_checked():
    expected, actual = _runs(), _runs()
    expected[0, 0]["support"] = _frame()[["person_id", "period", "age"]]
    actual[0, 0]["support"] = expected[0, 0]["support"].iloc[1:]
    expected[0, 0]["weights"] = _frame()[["person_id", "period", "weight"]]
    report = _compare(expected, actual)
    assert {item["field"] for item in report["differences"]} == {
        "support",
        "weights",
    }


def test_all_person_diagnostics_retained_and_json_safe():
    expected = _frame()
    actual = expected.copy()
    actual["earnings"] += 1
    actual["weight"] += 1
    report = compare_frames(expected, actual)
    assert len(report["differences"]) == 2 * len(expected)
    json.dumps(report, allow_nan=False)


def test_balanced_earnings_changes_cannot_hide_behind_aggregate_equality():
    expected = _frame()
    actual = expected.copy()
    actual.loc[1, "earnings"] += 100
    actual.loc[2, "earnings"] -= 100
    assert expected["earnings"].sum() == actual["earnings"].sum()
    assert len(compare_frames(expected, actual)["differences"]) == 2


def _single(expected_fit, actual_fit) -> dict:
    """Compare one invented seed/draw whose payloads differ only in fit."""
    expected, actual = _payload(), _payload()
    expected["fit_signature"] = expected_fit
    actual["fit_signature"] = actual_fit
    return compare_replay(
        {(0, 0): expected},
        {(0, 0): actual},
        registered_seeds=(0,),
        registered_draws=(0,),
    )


def test_int_and_bool_signature_keys_do_not_match():
    # The pre-fix checker compared keys with ==, so this returned REPRODUCED.
    report = _single({1: "a"}, {True: "a"})
    assert report["status"] == "BASELINE_REPLAY_MISMATCH"
    assert report["equal"] is False
    assert [item["kind"] for item in report["differences"]] == [
        "signature_key_type"
    ]
    difference = report["differences"][0]
    assert difference["path"] == ["fit_signature", "1"]
    assert difference["expected_key"]["type"] == "builtins.int"
    assert difference["actual_key"]["type"] == "builtins.bool"
    json.dumps(report, allow_nan=False)
    assert _single({True: "a"}, {1: "a"})["status"] == (
        "BASELINE_REPLAY_MISMATCH"
    )


def test_retyped_key_with_changed_value_reports_both():
    report = _single({1: "a"}, {True: "b"})
    assert [
        (item["kind"], item["path"]) for item in report["differences"]
    ] == [
        ("signature_key_type", ["fit_signature", "1"]),
        ("signature_value", ["fit_signature", "1"]),
    ]


def test_unequal_keys_of_different_types_are_missing_and_extra():
    report = _single({1: "a"}, {"1": "a"})
    assert {
        (item["kind"], item["key"]["type"]) for item in report["differences"]
    } == {
        ("missing_signature_field", "builtins.int"),
        ("extra_signature_field", "builtins.str"),
    }


@pytest.mark.parametrize("field", ["fit_signature", "rng_signature"])
def test_signature_mapping_type_is_material(field):
    expected, actual = _runs(), _runs()
    actual[0, 1][field] = types.MappingProxyType(dict(actual[0, 1][field]))
    report = _compare(expected, actual)
    assert report["status"] == "BASELINE_REPLAY_MISMATCH"
    assert report["differences"] == [
        {
            "seed": 0,
            "draw": 1,
            "kind": "signature_mapping_type",
            "path": [field],
            "expected_type": "builtins.dict",
            "actual_type": "builtins.mappingproxy",
        }
    ]


def test_nested_retyped_key_has_full_path():
    expected, actual = _runs(), _runs()
    expected[1, 1]["rng_signature"]["codes"] = {0: "gate"}
    actual[1, 1]["rng_signature"]["codes"] = {False: "gate"}
    report = _compare(expected, actual)
    assert [
        (item["kind"], item["path"]) for item in report["differences"]
    ] == [("signature_key_type", ["rng_signature", "codes", "0"])]


def test_unsupported_or_colliding_signature_keys_fail_closed():
    tuple_keys = _single({(1, 2): "a"}, {(1, 2): "a"})
    assert {item["kind"] for item in tuple_keys["differences"]} == {
        "unsupported_signature_key"
    }
    first, second = float("nan"), float("nan")
    colliding = _single({first: "a", second: "b"}, {first: "a", second: "b"})
    assert colliding["status"] == "BASELINE_REPLAY_MISMATCH"
    assert {item["kind"] for item in colliding["differences"]} == {
        "duplicate_signature_key"
    }


@settings(deadline=None)
@given(
    keys=st.lists(
        st.integers(min_value=-5, max_value=5),
        min_size=1,
        max_size=6,
        unique=True,
    ),
    data=st.data(),
)
def test_any_equal_but_retyped_key_is_reported(keys, data):
    """Property: dict equality merges these keys; the checker must not."""
    values = {key: f"value-{key}" for key in keys}
    target = data.draw(st.sampled_from(keys))
    retypes = [float, np.int64] + ([bool] if target in (0, 1) else [])
    retype = data.draw(st.sampled_from(retypes))
    retyped = {
        (retype(key) if key == target else key): value
        for key, value in values.items()
    }
    assert retyped == values
    report = _single(values, retyped)
    assert [
        (item["kind"], item["path"]) for item in report["differences"]
    ] == [("signature_key_type", ["fit_signature", str(target)])]
    assert _single(values, copy.deepcopy(values))["status"] == "REPRODUCED"
