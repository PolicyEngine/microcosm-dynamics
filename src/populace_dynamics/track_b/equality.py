"""Exact, fail-closed comparisons for the Track B B1 reproduction.

No tolerances or aggregate substitutes are used. Frame row and column order
are immaterial, but each keyed value, its dtype, and its floating-point bits
are material. Signature mapping keys match by typed token, so ``1`` and
``True`` are different keys, and mapping types must agree. Diagnostics
retain every discrepancy and are JSON serializable.
"""

from __future__ import annotations

import json
import struct
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import pandas as pd

MISMATCH = "BASELINE_REPLAY_MISMATCH"
REPRODUCED = "REPRODUCED"


def _scalar(value: Any) -> dict[str, Any]:
    """Describe a scalar without losing signed zeros or NaN payloads."""
    kind = f"{type(value).__module__}.{type(value).__qualname__}"
    result: dict[str, Any] = {"type": kind, "repr": repr(value)}
    if isinstance(value, np.generic):
        result.update(dtype=value.dtype.str, bytes=value.tobytes().hex())
    elif isinstance(value, float):
        result["bytes"] = struct.pack(">d", value).hex()
    elif isinstance(value, (pd.Timestamp, pd.Timedelta)):
        result["bytes"] = value.asm8.tobytes().hex()
    elif value is pd.NA or value is pd.NaT or value is None:
        pass
    elif isinstance(value, (str, int, bool, bytes)):
        pass
    else:
        raise TypeError(f"unsupported exact-comparison scalar: {kind}")
    return result


def _token(value: Any) -> str:
    return json.dumps(_scalar(value), sort_keys=True)


def _dtype_description(dtype: Any) -> dict[str, Any]:
    description = {
        "type": f"{type(dtype).__module__}.{type(dtype).__qualname__}",
        "repr": repr(dtype),
    }
    if isinstance(dtype, pd.CategoricalDtype):
        # Pandas considers unordered categories equal after permutation;
        # dtype identity for a byte-exact replay is stricter than that.
        description["categories"] = [
            _scalar(value) for value in dtype.categories
        ]
        description["ordered"] = dtype.ordered
        description["categories_dtype"] = _dtype_description(
            dtype.categories.dtype
        )
    return description


def _difference(
    differences: list[dict[str, Any]], kind: str, **details: Any
) -> None:
    differences.append({"kind": kind, **details})


def compare_frames(
    expected: pd.DataFrame,
    actual: pd.DataFrame,
    *,
    keys: Sequence[str] = ("person_id", "period"),
) -> dict[str, Any]:
    """Compare all nonempty keyed rows and columns, retaining all failures.

    Duplicate or missing keys, null key values and unsupported scalar types
    fail closed. Index labels are not part of the person-period identity.
    """
    differences: list[dict[str, Any]] = []
    result = {
        "equal": False,
        "expected_rows": len(expected),
        "actual_rows": len(actual),
        "differences": differences,
    }
    if not keys or len(set(keys)) != len(keys):
        _difference(differences, "invalid_keys", keys=list(keys))
        return result
    columns: dict[str, set[str]] = {}
    for side, frame in (("expected", expected), ("actual", actual)):
        if frame.empty:
            _difference(differences, "empty_frame", side=side)
        if frame.columns.has_duplicates:
            _difference(differences, "duplicate_columns", side=side)
            return result
        if not all(isinstance(column, str) for column in frame.columns):
            _difference(differences, "nonstring_columns", side=side)
            return result
        columns[side] = set(frame.columns)
        missing_keys = sorted(set(keys) - columns[side])
        if missing_keys:
            _difference(
                differences, "missing_keys", side=side, columns=missing_keys
            )
    if any(item["kind"] == "missing_keys" for item in differences):
        return result
    for column in sorted(columns["expected"] - columns["actual"]):
        _difference(differences, "missing_column", column=column)
    for column in sorted(columns["actual"] - columns["expected"]):
        _difference(differences, "extra_column", column=column)
    shared = sorted(columns["actual"] & columns["expected"])
    for column in shared:
        left, right = expected[column].dtype, actual[column].dtype
        left_description, right_description = (
            _dtype_description(left),
            _dtype_description(right),
        )
        if left != right or left_description != right_description:
            _difference(
                differences,
                "dtype",
                column=column,
                expected=left_description,
                actual=right_description,
            )
    rows: dict[str, dict[tuple[str, ...], int]] = {}
    for side, frame in (("expected", expected), ("actual", actual)):
        lookup: dict[tuple[str, ...], int] = {}
        rows[side] = lookup
        for index in range(len(frame)):
            values = [frame[key].iloc[index] for key in keys]
            if any(pd.isna(value) for value in values):
                _difference(
                    differences, "null_key", side=side, row_position=index
                )
                continue
            try:
                key = tuple(_token(value) for value in values)
            except TypeError as error:
                _difference(
                    differences,
                    "unsupported_key",
                    side=side,
                    row_position=index,
                    detail=str(error),
                )
                continue
            if key in lookup:
                _difference(
                    differences,
                    "duplicate_key",
                    side=side,
                    key=dict(zip(keys, map(json.loads, key), strict=True)),
                    row_positions=[lookup[key], index],
                )
            else:
                lookup[key] = index
    for key in sorted(set(rows["expected"]) | set(rows["actual"])):
        identity = dict(zip(keys, map(json.loads, key), strict=True))
        if key not in rows["actual"]:
            _difference(differences, "missing_row", key=identity)
            continue
        if key not in rows["expected"]:
            _difference(differences, "extra_row", key=identity)
            continue
        for column in shared:
            try:
                left = _scalar(expected[column].iloc[rows["expected"][key]])
                right = _scalar(actual[column].iloc[rows["actual"][key]])
            except TypeError as error:
                _difference(
                    differences,
                    "unsupported_value",
                    key=identity,
                    column=column,
                    detail=str(error),
                )
                continue
            if left != right:
                _difference(
                    differences,
                    "value",
                    key=identity,
                    column=column,
                    expected=left,
                    actual=right,
                )
    result["equal"] = not differences
    return result


def _type_name(value: Any) -> str:
    return f"{type(value).__module__}.{type(value).__qualname__}"


def _key_tokens(
    mapping: Mapping[Any, Any],
    side: str,
    path: list[Any],
    differences: list[dict[str, Any]],
) -> dict[str, Any]:
    """Index keys by exact typed token; ``==`` would merge 1 and True.

    Keys match by type and bits, so NaN keys with identical payloads match.
    Intended fail-closed cases, even when comparing a mapping with itself:
    unsupported key types (e.g. tuples) and distinct keys sharing a token
    (e.g. two NaN objects). JSON-derived signatures contain neither.
    """
    tokens: dict[str, Any] = {}
    for key in mapping:
        try:
            token = _token(key)
        except TypeError as error:
            _difference(
                differences,
                "unsupported_signature_key",
                path=path,
                side=side,
                key_repr=repr(key),
                detail=str(error),
            )
            continue
        if token in tokens:
            # Distinct keys sharing a token (e.g. two NaN objects) would
            # otherwise shadow one another, so they fail closed.
            _difference(
                differences,
                "duplicate_signature_key",
                path=path,
                side=side,
                key=json.loads(token),
            )
            continue
        tokens[token] = key
    return tokens


def _same_dict_key(left: Any, right: Any) -> bool:
    """Whether a dict would treat two keys as one (hash and ``==``)."""
    try:
        return hash(left) == hash(right) and bool(left == right)
    except Exception:
        return False


def _compare_signature(
    expected: Any,
    actual: Any,
    path: list[Any],
    differences: list[dict[str, Any]],
) -> None:
    if isinstance(expected, Mapping) and isinstance(actual, Mapping):
        if type(expected) is not type(actual):
            _difference(
                differences,
                "signature_mapping_type",
                path=path,
                expected_type=_type_name(expected),
                actual_type=_type_name(actual),
            )
        left = _key_tokens(expected, "expected", path, differences)
        right = _key_tokens(actual, "actual", path, differences)
        # Pair keys that differ only in type, such as 1 and True, so the
        # diagnostic names the type change rather than a missing field.
        retyped: dict[str, str] = {}
        extra = [token for token in sorted(right) if token not in left]
        for token in sorted(set(left) - set(right)):
            for candidate in extra:
                if _same_dict_key(left[token], right[candidate]):
                    retyped[token] = candidate
                    extra.remove(candidate)
                    break
        for token in sorted(set(left) | set(right)):
            if token in left and token in right:
                location = [*path, str(left[token])]
                _compare_signature(
                    expected[left[token]],
                    actual[right[token]],
                    location,
                    differences,
                )
            elif token in retyped:
                key, other = left[token], right[retyped[token]]
                location = [*path, str(key)]
                _difference(
                    differences,
                    "signature_key_type",
                    path=location,
                    expected_key=_scalar(key),
                    actual_key=_scalar(other),
                )
                _compare_signature(
                    expected[key], actual[other], location, differences
                )
            elif token in left:
                _difference(
                    differences,
                    "missing_signature_field",
                    path=[*path, str(left[token])],
                    key=_scalar(left[token]),
                )
            elif token in extra:
                _difference(
                    differences,
                    "extra_signature_field",
                    path=[*path, str(right[token])],
                    key=_scalar(right[token]),
                )
        return
    if isinstance(expected, (list, tuple)) and isinstance(
        actual, (list, tuple)
    ):
        if type(expected) is not type(actual) or len(expected) != len(actual):
            _difference(
                differences,
                "signature_sequence",
                path=path,
                expected_type=type(expected).__name__,
                actual_type=type(actual).__name__,
                expected_length=len(expected),
                actual_length=len(actual),
            )
        for index in range(max(len(expected), len(actual))):
            location = [*path, index]
            if index >= len(actual):
                _difference(
                    differences, "missing_signature_field", path=location
                )
            elif index >= len(expected):
                _difference(
                    differences, "extra_signature_field", path=location
                )
            else:
                _compare_signature(
                    expected[index], actual[index], location, differences
                )
        return
    try:
        left, right = _scalar(expected), _scalar(actual)
    except TypeError as error:
        _difference(
            differences,
            "unsupported_signature_value",
            path=path,
            detail=str(error),
        )
        return
    if left != right:
        _difference(
            differences,
            "signature_value",
            path=path,
            expected=left,
            actual=right,
        )


def compare_replay(
    expected: Mapping[tuple[int, int], Mapping[str, Any]],
    actual: Mapping[tuple[int, int], Mapping[str, Any]],
    *,
    registered_seeds: Sequence[int],
    registered_draws: Sequence[int],
) -> dict[str, Any]:
    """Check the complete registered Cartesian product of seeds and draws.

    Each payload requires a nonempty ``scored`` frame with earnings and
    weight columns plus nonempty ``fit_signature`` and ``rng_signature``
    values. Every scored column is checked, including support covariates.
    Optional separate ``support`` and ``weights`` frames are also checked
    whenever either payload provides them. A missing baseline never passes.
    """
    differences: list[dict[str, Any]] = []
    comparisons: list[dict[str, Any]] = []
    seeds, draws = list(registered_seeds), list(registered_draws)
    if (
        not seeds
        or not draws
        or len(set(seeds)) != len(seeds)
        or len(set(draws)) != len(draws)
    ):
        _difference(differences, "invalid_registration_coverage")
    coverage = {(seed, draw) for seed in seeds for draw in draws}
    for side, payloads in (("expected", expected), ("actual", actual)):
        for seed, draw in sorted(coverage - set(payloads)):
            _difference(
                differences,
                "missing_seed_draw",
                side=side,
                seed=seed,
                draw=draw,
            )
        for seed, draw in sorted(set(payloads) - coverage):
            _difference(
                differences,
                "extra_seed_draw",
                side=side,
                seed=seed,
                draw=draw,
            )
    for seed, draw in sorted(coverage & set(expected) & set(actual)):
        left, right = expected[seed, draw], actual[seed, draw]
        current: list[dict[str, Any]] = []
        for field in ("scored", "support", "weights"):
            if field != "scored" and field not in left and field not in right:
                continue
            values = (left.get(field), right.get(field))
            for side, frame in zip(
                ("expected", "actual"), values, strict=True
            ):
                if not isinstance(frame, pd.DataFrame):
                    _difference(
                        current, "missing_frame", side=side, field=field
                    )
                elif field == "scored":
                    for column in ("earnings", "weight"):
                        if column not in frame:
                            _difference(
                                current,
                                "missing_required_column",
                                side=side,
                                field=field,
                                column=column,
                            )
            if all(isinstance(frame, pd.DataFrame) for frame in values):
                comparison = compare_frames(*values)
                current.extend(
                    {"field": field, **item}
                    for item in comparison["differences"]
                )
        for field in ("fit_signature", "rng_signature"):
            values = (left.get(field), right.get(field))
            valid = True
            for side, signature in zip(
                ("expected", "actual"), values, strict=True
            ):
                missing = signature is None or (
                    isinstance(signature, (Mapping, list, tuple, str))
                    and len(signature) == 0
                )
                if missing:
                    _difference(
                        current, "missing_signature", side=side, field=field
                    )
                    valid = False
            if valid:
                _compare_signature(*values, [field], current)
        comparisons.append(
            {
                "seed": seed,
                "draw": draw,
                "equal": not current,
                "differences": current,
            }
        )
        differences.extend(
            {"seed": seed, "draw": draw, **item} for item in current
        )
    return {
        "status": MISMATCH if differences else REPRODUCED,
        "verification_class": "reproduction",
        "equal": not differences,
        "registered_seeds": seeds,
        "registered_draws": draws,
        "differences": differences,
        "comparisons": comparisons,
    }
