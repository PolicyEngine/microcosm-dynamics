"""Opt-in, retrospective histories from unchanged assembled projections.

The observer performs no model evaluation. Fertility boundary capture is a
separately instrumented execution and never exposes private maternal draws.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass, replace

import numpy as np
import pandas as pd

from .closed_cohort_history import ClosedCohortEarningsHistory
from .engine.loop import PeriodModules, ProjectionResult
from .engine.rng import ProjectionModule
from .forward_earnings_history import ForwardEarningsHistory
from .mortality_observer import (
    MortalityModelSnapshot,
    MortalityObservation,
    MortalityStepObservation,
)
from .person_identity import PersonIdentity, PersonIdentityMap

_MODES = {"strict_full_roster", "original_2014_view"}
_SCHEMA = "assembled-history-observation/v1"
_AUDIT_KEYS = {
    "mode",
    "baseline_digest",
    "history_digest",
    "identity_bindings",
    "initial_ids",
    "scheduled",
    "periods",
    "excluded",
    "input_digests",
}


def _json(value: object) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def _load(text: str):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON field")
            result[key] = value
        return result

    def nonfinite(value):
        raise ValueError("nonfinite JSON number")

    return json.loads(text, object_pairs_hook=pairs, parse_constant=nonfinite)


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _digest(value: object) -> None:
    if (
        type(value) is not str
        or len(value) != 64
        or any(c not in "0123456789abcdef" for c in value)
    ):
        raise ValueError("canonical SHA-256 required")


def _int(value: object) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value, (int, np.integer)
    ):
        raise ValueError("exact integer required")
    return int(value)


def _ids(values) -> tuple[int, ...]:
    result = tuple(_int(x) for x in values)
    if any(x < -(2**63) or x >= 2**63 for x in result):
        raise ValueError("native identity must fit signed int64")
    if len(set(result)) != len(result):
        raise ValueError("duplicate native identity")
    return tuple(sorted(result))


def _strings(values) -> list[str]:
    return [str(x) for x in sorted(values)]


def _parse_ids(values) -> tuple[int, ...]:
    if type(values) is not list:
        raise ValueError("ID list required")
    result = []
    for value in values:
        if type(value) is not str or str(int(value)) != value:
            raise ValueError("canonical integer string required")
        result.append(int(value))
    if tuple(result) != _ids(result):
        raise ValueError("sorted unique IDs required")
    return tuple(result)


def _keys(value, expected):
    if type(value) is not dict or set(value) != set(expected):
        raise ValueError("unexpected document fields")


def _scalar(value):
    if value is None:
        return ["null", None]
    if value is pd.NA:
        return ["NA", None]
    if isinstance(value, (bool, np.bool_)):
        return ["bool", bool(value)]
    if isinstance(value, (int, np.integer)):
        return ["int", str(int(value))]
    if isinstance(value, (float, np.floating)):
        return ["float", float(value).hex()]
    if isinstance(value, str):
        return ["str", value]
    raise ValueError("unsupported frame scalar for exact input binding")


def _frame_json(frame: pd.DataFrame) -> str:
    if (
        type(frame) is not pd.DataFrame
        or not frame.columns.is_unique
        or any(type(c) is not str for c in frame)
    ):
        raise ValueError("ordinary frame with unique string columns required")
    return _json(
        {
            "columns": [[c, str(frame[c].dtype)] for c in frame],
            "rows": [
                [_scalar(x) for x in row]
                for row in frame.itertuples(index=False, name=None)
            ],
        }
    )


def _frame_from_json(text: str) -> pd.DataFrame:
    doc = _load(text)

    def decode(cell):
        kind, value = cell
        return {
            "null": lambda: None,
            "NA": lambda: pd.NA,
            "bool": lambda: value,
            "int": lambda: int(value),
            "float": lambda: float.fromhex(value),
            "str": lambda: value,
        }[kind]()

    return pd.DataFrame(
        {
            c: pd.Series([decode(row[i]) for row in doc["rows"]], dtype=dtype)
            for i, (c, dtype) in enumerate(doc["columns"])
        }
    )


def _rows(frame: pd.DataFrame, *, year: int | None = None) -> dict[int, dict]:
    required = {"person_id", "age", "sex", "weight"}
    if year is not None:
        required.add("year")
    if (
        type(frame) is not pd.DataFrame
        or not frame.columns.is_unique
        or not required.issubset(frame)
    ):
        raise ValueError("complete unique demographic frame required")
    if frame.person_id.dtype != np.dtype("int64"):
        raise ValueError("native person_id must preserve int64")
    keys = _ids(frame.person_id)
    if len(keys) != len(frame):
        raise ValueError("duplicate person rows")
    result = {}
    for row in frame.to_dict("records"):
        key = _int(row["person_id"])
        age = _int(row["age"])
        if age < 0 or row["sex"] not in ("female", "male"):
            raise ValueError("invalid mortality demographics")
        if isinstance(row["weight"], (bool, np.bool_)) or not isinstance(
            row["weight"], (float, int, np.number)
        ):
            raise ValueError("numeric weight required")
        if not math.isfinite(float(row["weight"])) or row["weight"] < 0:
            raise ValueError("invalid weight")
        if year is not None and _int(row["year"]) != year:
            raise ValueError("frame year mismatch")
        result[key] = row
    return result


def _same_demographics(left: dict, right: dict, *, aging: int = 0):
    for key in left:
        a, b = left[key], right[key]
        if (
            a["age"] + aging != b["age"]
            or a["sex"] != b["sex"]
            or _scalar(a["weight"]) != _scalar(b["weight"])
        ):
            raise ValueError("demographic continuity mismatch")


@dataclass(frozen=True)
class FertilityBoundary:
    """Exact value/dtype copies of one actual callback boundary."""

    draw_index: int
    period_index: int
    year: int
    before_json: str
    after_json: str


class FertilityCapture:
    """Single-invocation capture; failure and attempted reuse are permanent."""

    def __init__(self):
        self._records: list[FertilityBoundary] = []
        self._failed = False
        self._draw: int | None = None
        self._periods: int | None = None

    @property
    def records(self) -> tuple[FertilityBoundary, ...]:
        return tuple(self._records)

    def _call(self, original, frame, context, marital, rng):
        try:
            if self._failed or context.period_index != len(self._records) + 1:
                raise ValueError(
                    "fertility capture cannot be reused or reordered"
                )
            if context.rng_registry is None:
                raise ValueError("assembled capture requires registry")
            if self._draw is None:
                self._draw = context.draw_index
                self._periods = context.rng_registry.n_periods
            if (
                context.draw_index != self._draw
                or context.rng_registry.n_periods != self._periods
                or context.period_index > self._periods
            ):
                raise ValueError("fertility capture mixes invocations")
            if _int(context.rng_registry.draw_index) != _int(
                context.draw_index
            ) or _int(context.year) != 2014 + _int(context.period_index):
                raise ValueError(
                    "fertility capture registry/calendar mismatch"
                )
            before = _frame_json(frame)
            output = original(frame, context, marital, rng)
            self._records.append(
                FertilityBoundary(
                    context.draw_index,
                    context.period_index,
                    context.year,
                    before,
                    _frame_json(output),
                )
            )
            return output
        except BaseException:
            self._failed = True
            raise

    def to_json(self) -> str:
        """Persist complete copied boundaries for an external run receipt."""
        if self._periods is None:
            raise ValueError("no fertility invocation captured")
        self._require_complete(self._draw, self._periods)
        return _json(
            {
                "schema": "assembled-fertility-boundaries/v1",
                "draw_index": self._draw,
                "n_periods": self._periods,
                "records": [
                    [
                        x.draw_index,
                        x.period_index,
                        x.year,
                        x.before_json,
                        x.after_json,
                    ]
                    for x in self.records
                ],
            }
        )

    def _require_complete(self, draw: int, periods: int):
        if self._failed or len(self._records) != periods:
            raise ValueError("incomplete or failed fertility capture")
        if periods and (self._draw != draw or self._periods != periods):
            raise ValueError("fertility capture belongs to another invocation")


def capture_fertility(
    modules: PeriodModules,
) -> tuple[PeriodModules, FertilityCapture]:
    """Wrap only fertility, calling the original exactly once by identity."""
    if type(modules) is not PeriodModules:
        raise ValueError("existing PeriodModules required")
    capture = FertilityCapture()
    original = modules.fertility

    def fertility(frame, context, marital, rng):
        return capture._call(original, frame, context, marital, rng)

    return replace(modules, fertility=fertility), capture


def _validate_audit(history, audit):
    _keys(audit, _AUDIT_KEYS)
    if (
        audit["mode"] not in _MODES
        or audit["baseline_digest"] != history.baseline.digest
        or audit["history_digest"] != history.digest
    ):
        raise ValueError("audit/history binding mismatch")
    initial = set(_parse_ids(audit["initial_ids"]))
    bindings = audit["identity_bindings"]
    if bindings != sorted(bindings, key=lambda row: int(row[0])):
        raise ValueError("native bindings must be sorted")
    native_to_key, ordinals = {}, {}
    for native, key, ordinal in bindings:
        # Parse singly: mapping order is native-numeric, not private-key order.
        native, key, ordinal = (
            _parse_ids([x])[0] for x in (native, key, ordinal)
        )
        if native in native_to_key or ordinal < 0:
            raise ValueError("invalid identity binding")
        native_to_key[native], ordinals[native] = key, ordinal
        if history.baseline.identity_map.reverse_rows([key])[
            0
        ] != PersonIdentity("int64", native):
            raise ValueError("native identity binding mismatch")
    if (
        set(native_to_key) != initial
        or set(native_to_key.values()) != set(history.baseline.roster_keys)
        or len(set(ordinals.values())) != len(ordinals)
    ):
        raise ValueError("cohort identity coverage mismatch")
    if audit["scheduled"] != sorted(
        audit["scheduled"], key=lambda row: row[0]
    ):
        raise ValueError("scheduled years must be sorted")
    scheduled = {}
    scheduled_ids = set()
    for year, ids in audit["scheduled"]:
        if (
            type(year) is not int
            or not 2015 <= year <= history.last_year
            or year in scheduled
        ):
            raise ValueError("invalid scheduled period")
        scheduled[year] = set(_parse_ids(ids))
        if scheduled[year] & (initial | scheduled_ids):
            raise ValueError("scheduled identity collision")
        scheduled_ids.update(scheduled[year])
    native_order = {
        key: i for i, key in enumerate(sorted(initial | scheduled_ids))
    }
    if any(ordinals[x] != native_order[x] for x in initial):
        raise ValueError("native ordinal binding mismatch")
    if len(audit["periods"]) != len(history.transitions):
        raise ValueError("audit period coverage mismatch")
    active, seen, excluded = set(initial), set(initial | scheduled_ids), {}
    for transition, row in zip(
        history.transitions, audit["periods"], strict=True
    ):
        _keys(row, {"year", "pre_ids", "death_ids", "post_ids", "births"})
        year = transition.mortality.target_year
        if row["year"] != year:
            raise ValueError("audit year mismatch")
        entrants = scheduled.get(year, set())
        pre, dead, post = (
            set(_parse_ids(row[x]))
            for x in ("pre_ids", "death_ids", "post_ids")
        )
        if pre != active | entrants or not dead <= pre:
            raise ValueError("full mortality roster mismatch")
        for key in entrants:
            excluded[key] = {
                "native_id": str(key),
                "kind": "scheduled_entry",
                "entry_year": year,
                "death_year": None,
                "parent_id": None,
            }
        survivors = pre - dead
        added = set()
        for native, parent in row["births"]:
            native, parent = _parse_ids([native])[0], _parse_ids([parent])[0]
            if native in seen or native in added or parent not in survivors:
                raise ValueError("birth identity or parent mismatch")
            added.add(native)
            excluded[native] = {
                "native_id": str(native),
                "kind": "native_synthetic_birth",
                "entry_year": year,
                "death_year": None,
                "parent_id": str(parent),
            }
        if post != survivors | added:
            raise ValueError("full final roster mismatch")
        for key in dead - initial:
            excluded[key]["death_year"] = year
        if (
            tuple(sorted(native_to_key[x] for x in pre & initial))
            != transition.mortality.pre_keys
        ):
            raise ValueError("cohort pre-roster mismatch")
        if (
            tuple(sorted(native_to_key[x] for x in survivors & initial))
            != transition.mortality.post_keys
        ):
            raise ValueError("cohort survivor mismatch")
        for observed in transition.mortality.rows:
            native = history.baseline.identity_map.reverse_rows(
                [observed.dynamics_person_key]
            )[0].value
            if observed.person_ordinal != ordinals[native]:
                raise ValueError("cohort ordinal mismatch")
        if audit["mode"] == "strict_full_roster" and (entrants or added):
            raise ValueError("strict full roster prohibits additions")
        active, seen = post, seen | added
    if audit["excluded"] != [excluded[x] for x in sorted(excluded)]:
        raise ValueError("excluded-person audit mismatch")
    expected = {
        "projection",
        "mortality",
        "traces",
        "entry_metadata",
        "mortality_model",
        "fertility_capture",
    }
    _keys(audit["input_digests"], expected)
    for digest in audit["input_digests"].values():
        _digest(digest)
    if (
        history.transitions
        and audit["input_digests"]["mortality_model"]
        != history.transitions[0].mortality.model.digest
    ):
        raise ValueError("model digest mismatch")


@dataclass(frozen=True)
class AssembledHistoryObservation:
    """Canonical cohort history plus inseparable full-roster selection audit."""

    history: ClosedCohortEarningsHistory
    audit_json: str

    def __post_init__(self):
        if type(self.history) is not ClosedCohortEarningsHistory:
            raise ValueError("explicit closed-cohort history required")
        audit = _load(self.audit_json)
        if _json(audit) != self.audit_json:
            raise ValueError("canonical audit JSON required")
        _validate_audit(self.history, audit)

    def to_json(self) -> str:
        return _json(
            {
                "schema": _SCHEMA,
                "history": _load(self.history.to_json()),
                "audit": _load(self.audit_json),
            }
        )

    @property
    def digest(self) -> str:
        return _hash(self.to_json())

    @classmethod
    def from_json(
        cls,
        text: str,
        *,
        baseline: ForwardEarningsHistory,
        expected_digest: str,
    ):
        """Require trusted baseline and whole-envelope digest before loading."""
        _digest(expected_digest)
        if _hash(text) != expected_digest:
            raise ValueError("observation digest mismatch")
        doc = _load(text)
        _keys(doc, {"schema", "history", "audit"})
        if doc["schema"] != _SCHEMA:
            raise ValueError("unsupported observation schema")
        result = cls(
            ClosedCohortEarningsHistory.from_json(
                _json(doc["history"]), baseline=baseline
            ),
            _json(doc["audit"]),
        )
        if result.to_json() != text:
            raise ValueError("noncanonical observation envelope")
        return result


def _birth_year(value, year):
    # Native concatenation adds missing values for nonchildren, promoting this
    # column to float. The supported calendar is small and exact.
    if isinstance(value, (float, np.floating)):
        if (
            not math.isfinite(value)
            or not float(value).is_integer()
            or abs(value) >= 2**53
        ):
            raise ValueError("unsafe birth year")
        value = int(value)
    if _int(value) != year:
        raise ValueError("birth year mismatch")
    return value


def _parent(value, survivors):
    if isinstance(value, (int, np.integer)) and not isinstance(
        value, (bool, np.bool_)
    ):
        parent = int(value)
    elif (
        isinstance(value, (float, np.floating))
        and math.isfinite(value)
        and float(value).is_integer()
        and abs(value) < 2**53
    ):
        parent = int(value)
        if sum(float(x) == value for x in survivors) != 1:
            raise ValueError("ambiguous float parent identity")
    else:
        raise ValueError("unsafe or ambiguous parent identity")
    if parent not in survivors:
        raise ValueError("birth parent is not a survivor")
    return parent


def observe_assembled_history(
    projection: ProjectionResult,
    draw_outputs: Mapping[str, object],
    *,
    mode: str,
    identity_map: PersonIdentityMap,
    realization_id: str,
    generator_digest: str,
    earnings_source_contract_digest: str,
    mortality_snapshot: MortalityModelSnapshot,
    mortality_snapshot_after: MortalityModelSnapshot,
    mortality_source_contract_digest: str,
    unit: str,
    price_basis: str,
    lineage_by_year: Mapping[int, str],
    initial_native_ids,
    scheduled_entries_by_year: Mapping[int, pd.DataFrame],
    reserved_real_ids,
    synthetic_id_start: int,
    fertility_capture: FertilityCapture | None = None,
) -> AssembledHistoryObservation:
    """Reconcile a complete run before selecting the original 2014 cohort.

    This reads supplied evidence only. Effective parameters and execution
    provenance must independently be bound before/after the actual run.
    """
    if type(projection) is not ProjectionResult or mode not in _MODES:
        raise ValueError("explicit projection and population mode required")
    if (
        type(identity_map) is not PersonIdentityMap
        or type(mortality_snapshot) is not MortalityModelSnapshot
    ):
        raise ValueError(
            "explicit identity map and immutable mortality snapshot required"
        )
    if (
        type(mortality_snapshot_after) is not MortalityModelSnapshot
        or mortality_snapshot_after != mortality_snapshot
    ):
        raise ValueError("pre/post mortality parameter binding mismatch")
    _digest(mortality_source_contract_digest)
    if any(type(year) is not int for year in lineage_by_year):
        raise ValueError("integer lineage years required")
    for value in lineage_by_year.values():
        _digest(value)
    periods = len(projection.traces)
    if not 0 <= periods <= 8 or len(projection.slices) != periods + 1:
        raise ValueError("complete 2014-22 projection required")
    draw = _int(projection.draw_index)
    initial = set(_ids(initial_native_ids))
    if not initial:
        raise ValueError("nonempty original cohort required")
    if set(lineage_by_year) != set(range(2014, 2015 + periods)):
        raise ValueError("exact annual lineage coverage required")
    if fertility_capture is not None:
        if type(fertility_capture) is not FertilityCapture:
            raise ValueError("native fertility boundary capture required")
        fertility_capture._require_complete(draw, periods)
    scheduled, all_ids = {}, set(initial)
    for year, frame in scheduled_entries_by_year.items():
        year = _int(year)
        if not 2015 <= year <= 2014 + periods or year in scheduled:
            raise ValueError("invalid scheduled entry year")
        rows = _rows(frame, year=year - 1)
        if not rows:
            raise ValueError("registered scheduled entries cannot be empty")
        if all_ids & set(rows):
            raise ValueError("scheduled identity collision")
        scheduled[year] = rows
        all_ids.update(rows)
    if mode == "strict_full_roster" and any(scheduled.values()):
        raise ValueError("strict full roster prohibits scheduled entrants")
    reserved = set(_ids(reserved_real_ids))
    if not all_ids <= reserved:
        raise ValueError(
            "reserved real namespace must cover all supplied real IDs"
        )
    next_id = _int(synthetic_id_start)
    if next_id < 0:
        raise ValueError("invalid synthetic namespace")
    ordinals = {key: ordinal for ordinal, key in enumerate(sorted(all_ids))}
    mapped = dict(
        zip(
            sorted(initial),
            identity_map.map_rows(
                PersonIdentity("int64", x) for x in sorted(initial)
            ),
            strict=True,
        )
    )

    def copied(frame):
        subset = frame.loc[frame.person_id.isin(initial)].copy()
        subset["person_id"] = np.asarray(
            [mapped[_int(x)] for x in subset.person_id], dtype="int64"
        )
        # Registered merges may carry object columns; accept only exact integer
        # scalar ages/years, never float coercion, on these observation copies.
        for column in ("age", "year"):
            subset[column] = np.asarray(
                [_int(x) for x in subset[column]], dtype="int64"
            )
        return subset

    previous = _rows(projection.slices[0], year=2014)
    if set(previous) != initial:
        raise ValueError(
            "declared initial cohort differs from initialized slice"
        )
    baseline = ForwardEarningsHistory.start(
        identity_map,
        copied(projection.slices[0]),
        realization_id=realization_id,
        generator_digest=generator_digest,
        source_contract_digest=earnings_source_contract_digest,
        unit=unit,
        price_basis=price_basis,
        lineage_digest=lineage_by_year[2014],
    )
    history = ClosedCohortEarningsHistory.start(baseline, draw_index=draw)
    mortalities = draw_outputs.get("mortality_slices", [])
    if type(mortalities) is not list or len(mortalities) != periods:
        raise ValueError("complete mortality slices required")
    period_audits, excluded, seen = [], {}, set(all_ids)
    for offset, (trace, frame, mortality) in enumerate(
        zip(
            projection.traces, projection.slices[1:], mortalities, strict=True
        ),
        1,
    ):
        year = 2014 + offset
        if trace.year != year or trace.steps != tuple(
            x.value for x in ProjectionModule
        ):
            raise ValueError("actual ordered eight-step trace required")
        pre = _rows(mortality)
        if (
            "cal_year" not in mortality
            or "death" not in mortality
            or mortality.death.dtype != np.dtype("bool")
        ):
            raise ValueError(
                "native mortality year and boolean death flags required"
            )
        if any(_int(x) != year for x in mortality.cal_year):
            raise ValueError("mortality target year mismatch")
        expected = {**previous, **scheduled.get(year, {})}
        if set(previous) & set(scheduled.get(year, {})) or set(pre) != set(
            expected
        ):
            raise ValueError("complete mortality pre-roster mismatch")
        _same_demographics(expected, pre)
        if any(
            row["age"] > mortality_snapshot.cells[-1][1]
            for row in pre.values()
        ):
            raise ValueError("age outside mortality snapshot")
        dead = {key for key, row in pre.items() if row["death"]}
        survivors = set(pre) - dead
        final = _rows(frame, year=year)
        if not survivors <= set(final):
            raise ValueError("unexplained survivor disappearance")
        _same_demographics({x: pre[x] for x in survivors}, final, aging=1)
        additions = set(final) - survivors
        births = []
        if additions and fertility_capture is None:
            raise ValueError(
                "birth additions require actual fertility capture"
            )
        if fertility_capture is not None:
            boundary = fertility_capture.records[offset - 1]
            if (boundary.draw_index, boundary.period_index, boundary.year) != (
                draw,
                offset,
                year,
            ):
                raise ValueError("fertility capture coordinates mismatch")
            before = _rows(_frame_from_json(boundary.before_json), year=year)
            after = _rows(_frame_from_json(boundary.after_json), year=year)
            if set(before) != survivors or set(after) != set(final):
                raise ValueError("fertility boundary roster mismatch")
            _same_demographics({x: pre[x] for x in survivors}, before, aging=1)
            _same_demographics(before, after)
            _same_demographics(after, final)
            for key in additions:
                for column in (
                    "birth_year",
                    "parent_person_id",
                    "synthetic_entry",
                ):
                    if (
                        column not in after[key]
                        or column not in final[key]
                        or _scalar(after[key][column])
                        != _scalar(final[key][column])
                    ):
                        raise ValueError("birth boundary metadata mismatch")
        for key in sorted(additions):
            row = final[key]
            if (
                key != next_id
                or key in seen
                or key in reserved
                or row["age"] != 0
                or _birth_year(row["birth_year"], year) != year
                or type(row["synthetic_entry"]) is not bool
                or not row["synthetic_entry"]
            ):
                raise ValueError(
                    "birth identity, allocator or metadata mismatch"
                )
            parent = _parent(row["parent_person_id"], survivors)
            births.append([str(key), str(parent)])
            next_id += 1
        if mode == "strict_full_roster" and additions:
            raise ValueError("strict full roster prohibits births")
        for key in scheduled.get(year, {}):
            excluded[key] = {
                "native_id": str(key),
                "kind": "scheduled_entry",
                "entry_year": year,
                "death_year": None,
                "parent_id": None,
            }
        for key, parent in births:
            excluded[int(key)] = {
                "native_id": key,
                "kind": "native_synthetic_birth",
                "entry_year": year,
                "death_year": None,
                "parent_id": parent,
            }
        for key in dead - initial:
            excluded[key]["death_year"] = year
        mortality_record = MortalityStepObservation(
            identity_map,
            realization_id,
            mortality_source_contract_digest,
            mortality_snapshot,
            year,
            offset,
            draw,
            periods,
            tuple(
                sorted(
                    (
                        MortalityObservation(
                            mapped[key],
                            row["age"],
                            row["sex"],
                            key not in dead,
                            ordinals[key],
                        )
                        for key, row in pre.items()
                        if key in initial
                    ),
                    key=lambda x: x.dynamics_person_key,
                )
            ),
        )
        history = history.append(
            mortality=mortality_record,
            earnings_frame=copied(frame),
            lineage_digest=lineage_by_year[year],
        )
        period_audits.append(
            {
                "year": year,
                "pre_ids": _strings(pre),
                "death_ids": _strings(dead),
                "post_ids": _strings(final),
                "births": births,
            }
        )
        previous, seen = final, seen | additions
    audit = {
        "mode": mode,
        "baseline_digest": baseline.digest,
        "history_digest": history.digest,
        "identity_bindings": [
            [str(x), str(mapped[x]), str(ordinals[x])] for x in sorted(initial)
        ],
        "initial_ids": _strings(initial),
        "scheduled": [
            [y, _strings(rows)] for y, rows in sorted(scheduled.items())
        ],
        "periods": period_audits,
        "excluded": [excluded[x] for x in sorted(excluded)],
        "input_digests": {
            "projection": _hash(
                _json([_frame_json(x) for x in projection.slices])
            ),
            "mortality": _hash(_json([_frame_json(x) for x in mortalities])),
            "traces": _hash(
                _json(
                    [
                        [
                            x.year,
                            list(x.steps),
                            _frame_json(x.authoritative_marital_state.births),
                        ]
                        for x in projection.traces
                    ]
                )
            ),
            "entry_metadata": _hash(
                _json(
                    {
                        "initial": _strings(initial),
                        "reserved": _strings(reserved),
                        "synthetic_start": str(synthetic_id_start),
                        "scheduled": [
                            [y, _frame_json(f)]
                            for y, f in sorted(
                                scheduled_entries_by_year.items()
                            )
                        ],
                    }
                )
            ),
            "mortality_model": mortality_snapshot.digest,
            "fertility_capture": _hash(
                _json(
                    None
                    if fertility_capture is None
                    else [
                        [
                            x.draw_index,
                            x.period_index,
                            x.year,
                            x.before_json,
                            x.after_json,
                        ]
                        for x in fertility_capture.records
                    ]
                )
            ),
        },
    }
    return AssembledHistoryObservation(history, _json(audit))
