"""Experimental accounting for one annual population transition.

``reconcile_period`` checks opening and closing person sets against the
caller's declared arrivals and departures. It does not generate transitions,
infer their causes, fit a model, or read data. Count conservation is exact;
weight stocks, flows, and separate revaluations use binary64 arithmetic with
``math.fsum`` and a reported residual. An unrepresentable summary is refused.
No scientific tolerance or acceptance gate is introduced.

Frames require unique signed-int64 person IDs, matching integer years, and
finite nonnegative real weights. These are this interface's validation rules;
the historical projection loop has a less restrictive input check. Zero-weight
rows remain people. Every declaration uses the closing year, even when a
scheduled-entry frame carries the loop's required previous-year stamp.

The supported lifecycle is at most one arrival followed by at most one
departure in the period. Event ordering within the year is not observed.
Declared transients appear in neither endpoint frame and need explicit
weights for both events. Omitting BOTH events is unobservable from endpoints:
accounting coherence does not establish event-log completeness or true causes.
There is no cross-period history, so declared reuse of a past ID is not caught.

The module has only stdlib, NumPy, and pandas direct imports. A normal package
import also executes the existing engine package initializer and its broader
source dependencies. This optional module is not called by the historical
engine. See ``docs/stock-flow-accounting.md`` for the interface and limits.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType

import numpy as np
import pandas as pd

__all__ = [
    "ACCOUNTING_INTERFACE_VERSION",
    "ADDITION_KINDS",
    "ENGINEERING_STATUS",
    "ENGINEERING_STATUS_NOTE",
    "EXIT_KINDS",
    "PERSON_ID_COLUMN",
    "REQUIRED_COLUMNS",
    "WEIGHT_COLUMN",
    "YEAR_COLUMN",
    "AccountingDiscrepancy",
    "DiscrepancyKind",
    "PeriodAccount",
    "PersonCounts",
    "PopulationAccountingError",
    "PopulationAccountingInputError",
    "PopulationEvent",
    "PopulationEventKind",
    "PopulationReconciliationError",
    "WeightRevaluation",
    "WeightTotals",
    "reconcile_period",
]

ACCOUNTING_INTERFACE_VERSION = "stock-flow-accounting/0.1.0-experimental"
ENGINEERING_STATUS = "engineering-accounting-coherence-only"
ENGINEERING_STATUS_NOTE = (
    "Person sets reconcile exactly and the weight identity closes to the "
    "reported arithmetic residual. This is engineering coherence only: it "
    "is not scientific acceptance, not a benchmark comparison, not a gate "
    "outcome, and not evidence that the population is admitted."
)
SUMMATION_METHOD = "math.fsum over binary64 components; residual reported"
INFERENCE_POLICY = (
    "none: every addition and every exit must be declared by the caller"
)

PERSON_ID_COLUMN = "person_id"
YEAR_COLUMN = "year"
WEIGHT_COLUMN = "weight"
REQUIRED_COLUMNS = (PERSON_ID_COLUMN, YEAR_COLUMN, WEIGHT_COLUMN)
_INT64_MIN = -(2**63)
_INT64_MAX = 2**63 - 1


class PopulationEventKind(str, Enum):
    """The declared reason a person joins or leaves within one period."""

    BIRTH = "birth"
    SCHEDULED_ENTRY = "scheduled_entry"
    OTHER_ENTRY = "other_entry"
    DEATH = "death"
    EMIGRATION = "emigration"
    OTHER_EXIT = "other_exit"


ADDITION_KINDS = frozenset(
    {
        PopulationEventKind.BIRTH,
        PopulationEventKind.SCHEDULED_ENTRY,
        PopulationEventKind.OTHER_ENTRY,
    }
)
EXIT_KINDS = frozenset(
    {
        PopulationEventKind.DEATH,
        PopulationEventKind.EMIGRATION,
        PopulationEventKind.OTHER_EXIT,
    }
)
#: Kinds whose whole purpose is "something else happened", and which are
#: therefore only meaningful if the caller says what.
REASON_REQUIRED_KINDS = frozenset(
    {PopulationEventKind.OTHER_ENTRY, PopulationEventKind.OTHER_EXIT}
)


class DiscrepancyKind(str, Enum):
    """Ways a declared story can fail to match the two frames."""

    UNDECLARED_ADDITION = "undeclared_addition"
    UNDECLARED_EXIT = "undeclared_exit"
    ADDITION_COLLIDES_WITH_OPENING = "addition_collides_with_opening"
    DUPLICATE_ADDITION = "duplicate_addition"
    DUPLICATE_EXIT = "duplicate_exit"
    EXIT_WITHOUT_PRESENCE = "exit_without_presence"
    EXIT_CONTRADICTED_BY_CLOSING = "exit_contradicted_by_closing"
    ADDITION_ABSENT_AT_CLOSE = "addition_absent_at_close"
    COUNT_IDENTITY_VIOLATION = "count_identity_violation"


_DISCREPANCY_ORDER = {
    kind: index for index, kind in enumerate(DiscrepancyKind)
}


class PopulationAccountingError(ValueError):
    """Base class for every refusal raised by this module."""


class PopulationAccountingInputError(PopulationAccountingError):
    """A frame or a declaration is malformed on its own terms."""


class PopulationReconciliationError(PopulationAccountingError):
    """Well-formed inputs whose declared story does not reconcile.

    The typed findings stay on the exception so that a caller can
    distinguish an unexplained arrival from an omitted exit without
    parsing a message.
    """

    def __init__(
        self,
        message: str,
        discrepancies: Sequence[AccountingDiscrepancy],
    ) -> None:
        self.discrepancies: tuple[AccountingDiscrepancy, ...] = tuple(
            discrepancies
        )
        super().__init__(message)

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe view of the refusal."""
        return {
            "interface_version": ACCOUNTING_INTERFACE_VERSION,
            "error": "population_reconciliation_error",
            "message": str(self),
            "discrepancies": [item.to_dict() for item in self.discrepancies],
        }


def _as_person_id(value: object, label: str) -> int:
    """Coerce one identifier to ``int``, rejecting bools and floats."""
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise PopulationAccountingInputError(
            f"{label} must be an integer person identifier, "
            f"got {value!r} of type {type(value).__name__}"
        )
    return _in_integer_domain(int(value), label)


def _as_year(value: object, label: str) -> int:
    """Coerce one calendar year to ``int``, rejecting bools and floats."""
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise PopulationAccountingInputError(
            f"{label} must be an integer year, got {value!r} of type "
            f"{type(value).__name__}"
        )
    return _in_integer_domain(int(value), label)


def _in_integer_domain(value: int, label: str) -> int:
    """Enforce the same signed int64 domain before any array cast."""
    if not _INT64_MIN <= value <= _INT64_MAX:
        raise PopulationAccountingInputError(
            f"{label} must fit in signed int64, got {value!r}"
        )
    return value


def _stable_sum(values: Iterable[float]) -> float:
    """Sum binary64 components and refuse an unrepresentable summary."""
    try:
        result = math.fsum(float(value) for value in values)
    except (OverflowError, ValueError) as error:
        raise PopulationAccountingInputError(
            "weight summary is not representable with finite binary64 "
            "arithmetic"
        ) from error
    if not math.isfinite(result):
        raise PopulationAccountingInputError("weight summary is not finite")
    return result


def _as_weight(value: object, label: str) -> float:
    """Validate a real numeric weight before converting it to binary64."""
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value, (int, float, np.integer, np.floating)
    ):
        raise PopulationAccountingInputError(
            f"{label} must be a real number, got {value!r}"
        )
    if value < 0:
        raise PopulationAccountingInputError(
            f"{label} must be finite and non-negative, got {value!r}"
        )
    try:
        weight = float(value)
    except (OverflowError, ValueError) as error:
        raise PopulationAccountingInputError(
            f"{label} is not representable as a finite binary64 weight"
        ) from error
    if not math.isfinite(weight) or weight < 0.0:
        raise PopulationAccountingInputError(
            f"{label} must be finite and non-negative, got {value!r}"
        )
    if weight == 0.0 and value != 0:
        raise PopulationAccountingInputError(
            f"{label} underflows to zero in binary64 arithmetic"
        )
    return weight


@dataclass(frozen=True)
class PopulationEvent:
    """One declared arrival or departure inside one annual period.

    Parameters
    ----------
    person_id:
        The identifier that joins or leaves.  Must match the identifier
        used in the frames.
    kind:
        A member of :class:`PopulationEventKind`.  Plain strings are
        accepted and coerced.
    year:
        The period's *closing* year, which labels the period.
    weight:
        Optional explicit weight at the moment of the event.  When
        omitted, an addition inherits the weight of its closing-frame
        row and an exit inherits the weight of its opening-frame row.
        A person who both arrives and departs within the period appears
        in neither frame and must therefore declare both weights.
    reason:
        Free text.  Required, and required to be non-empty, for
        ``other_entry`` and ``other_exit`` so that "something else"
        is never silent.
    source:
        Free-text provenance, e.g. the adapter that emitted the record.
        Collected into the account's provenance block.
    """

    person_id: int
    kind: PopulationEventKind
    year: int
    weight: float | None = None
    reason: str = ""
    source: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "person_id",
            _as_person_id(self.person_id, "PopulationEvent.person_id"),
        )
        try:
            kind = PopulationEventKind(self.kind)
        except ValueError as error:
            raise PopulationAccountingInputError(
                f"unknown population event kind {self.kind!r}; expected one "
                f"of {sorted(item.value for item in PopulationEventKind)}"
            ) from error
        object.__setattr__(self, "kind", kind)
        object.__setattr__(
            self, "year", _as_year(self.year, "PopulationEvent.year")
        )
        if self.weight is not None:
            object.__setattr__(
                self,
                "weight",
                _as_weight(self.weight, "PopulationEvent.weight"),
            )
        for field_name in ("reason", "source"):
            value = getattr(self, field_name)
            if not isinstance(value, str):
                raise PopulationAccountingInputError(
                    f"PopulationEvent.{field_name} must be a string, "
                    f"got {value!r}"
                )
        if kind in REASON_REQUIRED_KINDS and not self.reason.strip():
            raise PopulationAccountingInputError(
                f"a {kind.value!r} event must state a non-empty reason; "
                "this module never books an unexplained change"
            )

    @property
    def is_addition(self) -> bool:
        """Whether this kind adds a person to the roster."""
        return self.kind in ADDITION_KINDS

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe view of the declaration."""
        return {
            "person_id": self.person_id,
            "kind": self.kind.value,
            "year": self.year,
            "weight": self.weight,
            "reason": self.reason,
            "source": self.source,
        }


@dataclass(frozen=True)
class AccountingDiscrepancy:
    """One typed reason the declared story does not reconcile."""

    kind: DiscrepancyKind
    person_id: int | None
    detail: str

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe view of the finding."""
        return {
            "kind": self.kind.value,
            "person_id": self.person_id,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class PersonCounts:
    """Exact integer person counts for one period.

    ``closing == opening + additions_total - exits_total`` holds
    exactly, including transients, which are counted in both
    ``additions_total`` and ``exits_total`` and cancel.
    """

    opening: int
    closing: int
    carried: int
    entered: int
    exited: int
    transient: int
    additions_total: int
    exits_total: int
    additions_by_kind: Mapping[str, int]
    exits_by_kind: Mapping[str, int]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe view of the counts."""
        return {
            "opening": self.opening,
            "closing": self.closing,
            "carried": self.carried,
            "entered": self.entered,
            "exited": self.exited,
            "transient": self.transient,
            "additions_total": self.additions_total,
            "exits_total": self.exits_total,
            "additions_by_kind": dict(self.additions_by_kind),
            "exits_by_kind": dict(self.exits_by_kind),
        }


@dataclass(frozen=True)
class WeightRevaluation:
    """Weight movement that is *not* an arrival or a departure.

    Each component is the sum of ``weight at the end of the person's
    presence minus weight at the start of it`` over one presence class.
    ``carried`` is the component the caller usually wants: it is the
    entire change in the weight of people who were present at both ends
    of the period.  The other three are zero unless the caller declared
    an explicit event weight that differs from the frame weight.
    """

    carried: float
    entrant: float
    exiting: float
    transient: float

    @property
    def total(self) -> float:
        """Stable sum of the four binary64 components."""
        return _stable_sum(
            (self.carried, self.entrant, self.exiting, self.transient)
        )

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe view of the revaluation."""
        return {
            "carried": self.carried,
            "entrant": self.entrant,
            "exiting": self.exiting,
            "transient": self.transient,
            "total": self.total,
        }


@dataclass(frozen=True)
class WeightTotals:
    """Weight stocks and flows for one period.

    The identity is::

        closing == opening
                 + additions_total
                 - exits_total
                 + revaluation.total

    reported against an arithmetic residual rather than a tolerance.
    """

    opening: float
    closing: float
    additions_total: float
    exits_total: float
    additions_by_kind: Mapping[str, float]
    exits_by_kind: Mapping[str, float]
    revaluation: WeightRevaluation

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe view of the weight totals."""
        return {
            "opening": self.opening,
            "closing": self.closing,
            "additions_total": self.additions_total,
            "exits_total": self.exits_total,
            "additions_by_kind": dict(self.additions_by_kind),
            "exits_by_kind": dict(self.exits_by_kind),
            "revaluation": self.revaluation.to_dict(),
        }


@dataclass(frozen=True)
class PeriodAccount:
    """The reconciled stock-flow account for one annual period."""

    opening_year: int
    closing_year: int
    status: str
    status_note: str
    counts: PersonCounts
    weights: WeightTotals
    count_residual: int
    weight_residual: float
    reconstructed_closing_weight: float
    carried_person_ids: tuple[int, ...]
    entered_person_ids: tuple[int, ...]
    exited_person_ids: tuple[int, ...]
    transient_person_ids: tuple[int, ...]
    provenance: Mapping[str, object]

    @property
    def added_person_ids(self) -> tuple[int, ...]:
        """Every declared addition: entrants plus transients, sorted."""
        return tuple(
            sorted(self.entered_person_ids + self.transient_person_ids)
        )

    @property
    def departed_person_ids(self) -> tuple[int, ...]:
        """Every declared exit: exiters plus transients, sorted."""
        return tuple(
            sorted(self.exited_person_ids + self.transient_person_ids)
        )

    def to_dict(self) -> dict[str, object]:
        """Return the serializable counts, weights and provenance.

        Person identifier tuples stay off this payload on purpose: they
        are available as attributes for programmatic use, but a
        serialized account is a summary, not a roster.
        """
        return {
            "interface_version": ACCOUNTING_INTERFACE_VERSION,
            "status": self.status,
            "status_note": self.status_note,
            "opening_year": self.opening_year,
            "closing_year": self.closing_year,
            "counts": self.counts.to_dict(),
            "weights": self.weights.to_dict(),
            "residuals": {
                "count": self.count_residual,
                "weight": self.weight_residual,
                "reconstructed_closing_weight": (
                    self.reconstructed_closing_weight
                ),
            },
            "provenance": {
                **self.provenance,
                "declaration_sources": list(
                    self.provenance["declaration_sources"]
                ),
            },
        }


def _integer_column(
    frame: pd.DataFrame, column: str, label: str
) -> np.ndarray:
    """Return one non-null integral column as ``int64``.

    An empty column is accepted whatever its dtype: it holds no value
    that could be non-integral, and the naive way to spell an empty
    population, ``pd.DataFrame({"person_id": [], ...})``, yields float
    columns that carry no information about the caller's intent.
    """
    series = frame[column]
    if len(series) == 0:
        return np.empty(0, dtype=np.int64)
    if series.isna().any():
        raise PopulationAccountingInputError(
            f"{label} column {column!r} contains null values"
        )
    if pd.api.types.is_bool_dtype(series.dtype):
        raise PopulationAccountingInputError(
            f"{label} column {column!r} is boolean, not integral"
        )
    if pd.api.types.is_integer_dtype(series.dtype):
        _in_integer_domain(int(series.min()), f"{label}.{column}")
        _in_integer_domain(int(series.max()), f"{label}.{column}")
        return series.to_numpy(dtype=np.int64, copy=True)
    if series.dtype == object:
        values = series.tolist()
        for value in values:
            if isinstance(value, bool) or not isinstance(
                value, (int, np.integer)
            ):
                raise PopulationAccountingInputError(
                    f"{label} column {column!r} holds a non-integral value "
                    f"{value!r} of type {type(value).__name__}"
                )
        return np.asarray(
            [
                _in_integer_domain(int(value), f"{label}.{column}")
                for value in values
            ],
            dtype=np.int64,
        )
    raise PopulationAccountingInputError(
        f"{label} column {column!r} must be an integer dtype, got "
        f"{series.dtype!r}; float identifiers and years are rejected "
        "because they cannot be compared exactly"
    )


def _weight_column(frame: pd.DataFrame, label: str) -> np.ndarray:
    """Return the weight column as finite, non-negative ``float64``.

    As with identifiers, an empty column is accepted whatever its
    dtype.
    """
    series = frame[WEIGHT_COLUMN]
    if len(series) == 0:
        return np.empty(0, dtype=np.float64)
    if series.isna().any():
        raise PopulationAccountingInputError(
            f"{label} column {WEIGHT_COLUMN!r} contains null values"
        )
    if pd.api.types.is_bool_dtype(series.dtype):
        raise PopulationAccountingInputError(
            f"{label} column {WEIGHT_COLUMN!r} is boolean, not numeric"
        )
    if series.dtype == object:
        return np.asarray(
            [
                _as_weight(value, f"{label}.{WEIGHT_COLUMN}")
                for value in series.tolist()
            ],
            dtype=np.float64,
        )
    if not pd.api.types.is_numeric_dtype(
        series.dtype
    ) or pd.api.types.is_complex_dtype(series.dtype):
        raise PopulationAccountingInputError(
            f"{label} column {WEIGHT_COLUMN!r} must contain real numbers"
        )
    if (series < 0).any():
        raise PopulationAccountingInputError(
            f"{label} column {WEIGHT_COLUMN!r} contains negative weights"
        )
    try:
        values = series.to_numpy(dtype=np.float64, copy=True)
    except (TypeError, ValueError, OverflowError) as error:
        raise PopulationAccountingInputError(
            f"{label} column {WEIGHT_COLUMN!r} is not numeric "
            f"({series.dtype!r})"
        ) from error
    if not np.isfinite(values).all():
        raise PopulationAccountingInputError(
            f"{label} column {WEIGHT_COLUMN!r} contains non-finite weights"
        )
    if (values < 0.0).any():
        raise PopulationAccountingInputError(
            f"{label} column {WEIGHT_COLUMN!r} contains negative weights"
        )
    if ((values == 0.0) & series.ne(0).to_numpy(dtype=bool)).any():
        raise PopulationAccountingInputError(
            f"{label} column {WEIGHT_COLUMN!r} underflows to zero in binary64"
        )
    return values


def _read_frame(
    frame: pd.DataFrame, year: int, label: str
) -> tuple[np.ndarray, np.ndarray]:
    """Validate one population frame and snapshot its two columns.

    The frame is only read.  Nothing is assigned, sorted in place, or
    otherwise mutated, and the returned arrays are fresh.
    """
    if not isinstance(frame, pd.DataFrame):
        raise PopulationAccountingInputError(
            f"{label} must be a pandas DataFrame, got "
            f"{type(frame).__name__}"
        )
    missing = [
        column for column in REQUIRED_COLUMNS if column not in frame.columns
    ]
    if missing:
        raise PopulationAccountingInputError(
            f"{label} is missing columns {missing}"
        )
    if frame.columns.duplicated().any():
        raise PopulationAccountingInputError(
            f"{label} has duplicate column labels"
        )
    person_ids = _integer_column(frame, PERSON_ID_COLUMN, label)
    unique_ids, counts = np.unique(person_ids, return_counts=True)
    if unique_ids.size != person_ids.size:
        repeated = unique_ids[counts > 1][:10].tolist()
        raise PopulationAccountingInputError(
            f"{label} contains duplicate {PERSON_ID_COLUMN} rows: {repeated}"
        )
    years = _integer_column(frame, YEAR_COLUMN, label)
    off_year = np.unique(years[years != year])[:10].tolist()
    if off_year:
        raise PopulationAccountingInputError(
            f"{label} must carry year {year}; found {off_year}"
        )
    weights = _weight_column(frame, label)
    return person_ids, weights


def _index_events(
    events: Sequence[PopulationEvent],
    *,
    expected_kinds: frozenset[PopulationEventKind],
    closing_year: int,
    label: str,
    duplicate_kind: DiscrepancyKind,
    discrepancies: list[AccountingDiscrepancy],
) -> dict[int, PopulationEvent]:
    """Validate one declaration sequence and index it by person."""
    if isinstance(events, (str, bytes)) or not isinstance(events, Sequence):
        raise PopulationAccountingInputError(
            f"{label} must be a sequence of PopulationEvent, got "
            f"{type(events).__name__}"
        )
    indexed: dict[int, PopulationEvent] = {}
    for position, event in enumerate(events):
        if not isinstance(event, PopulationEvent):
            raise PopulationAccountingInputError(
                f"{label}[{position}] must be a PopulationEvent, got "
                f"{type(event).__name__}"
            )
        if event.kind not in expected_kinds:
            raise PopulationAccountingInputError(
                f"{label}[{position}] declares kind {event.kind.value!r}, "
                f"which is not one of "
                f"{sorted(item.value for item in expected_kinds)}; "
                "arrivals and departures are declared separately"
            )
        if event.year != closing_year:
            raise PopulationAccountingInputError(
                f"{label}[{position}] is booked to year {event.year}, but "
                f"this period closes in {closing_year}; events are booked "
                "to the period's closing year"
            )
        if event.person_id in indexed:
            discrepancies.append(
                AccountingDiscrepancy(
                    kind=duplicate_kind,
                    person_id=event.person_id,
                    detail=(
                        f"person {event.person_id} is declared more than "
                        f"once in {label} "
                        f"({indexed[event.person_id].kind.value!r} then "
                        f"{event.kind.value!r})"
                    ),
                )
            )
            continue
        indexed[event.person_id] = event
    return indexed


def _resolve_weight(
    person_id: int,
    event: PopulationEvent,
    fallback: Mapping[int, float],
    *,
    fallback_label: str,
) -> float:
    """Return the declared event weight, or its frame stand-in."""
    if event.weight is not None:
        return event.weight
    try:
        return fallback[person_id]
    except KeyError:
        raise PopulationAccountingInputError(
            f"person {person_id} is declared as a "
            f"{event.kind.value!r} but appears in neither the opening nor "
            "the closing frame, so this module cannot recover a weight for "
            f"the event from the {fallback_label} frame; a person who both "
            "arrives and departs within the period must declare an "
            "explicit weight on both declarations"
        ) from None


def reconcile_period(
    opening: pd.DataFrame,
    closing: pd.DataFrame,
    *,
    opening_year: int,
    closing_year: int,
    additions: Sequence[PopulationEvent] = (),
    exits: Sequence[PopulationEvent] = (),
) -> PeriodAccount:
    """Reconcile one annual period against its declared transitions.

    This is the module's only entry point.  It is a pure function: it
    reads the two frames and the two declaration sequences, mutates
    nothing, touches no filesystem, and returns a
    :class:`PeriodAccount` or raises.

    Parameters
    ----------
    opening, closing:
        Person-level frames carrying ``person_id``, ``year`` and
        ``weight``.  Identifiers must be integral and unique within
        each frame; weights must be finite and non-negative.  Rows with
        zero weight are ordinary persons and are never dropped.
    opening_year, closing_year:
        The period's endpoints, stated explicitly rather than inferred,
        so an empty frame is unambiguous.  ``closing_year`` must be
        ``opening_year + 1``.
    additions, exits:
        The declared arrivals and departures, each a sequence of
        :class:`PopulationEvent`.  Passing a departure kind in
        ``additions`` (or the reverse) is an input error.

    Returns
    -------
    PeriodAccount
        Counts, weight stocks and flows, arithmetic residuals and
        provenance.  Its ``status`` is always
        :data:`ENGINEERING_STATUS`: a returned account is an
        engineering statement about arithmetic and identity, never a
        scientific verdict.

    Raises
    ------
    PopulationAccountingInputError
        A frame or a declaration is malformed: a missing column, a null
        or non-integral identifier, a duplicate identifier within one
        frame, a non-finite or negative weight, a row carrying the
        wrong year, a declaration booked to the wrong year, a
        declaration of the wrong direction, or a transient whose weight
        cannot be recovered.
    PopulationReconciliationError
        The inputs are well formed but the declared story does not
        match the frames: an unexplained arrival, an omitted exit, a
        duplicate or colliding declaration, or an impossible sequence.
        The typed findings are on the exception's ``discrepancies``.

    Notes
    -----
    Validation is staged, and the first stage to find a problem raises:
    frames, then declarations, then reconciliation, then weights.  A
    caller with several problems at once therefore sees the earliest,
    not all of them.

    The accountant sees exactly one period.  It has no memory of
    earlier ones and no view of what the loop *should* have scheduled;
    it is not a schedule builder.  A person who exits in one period and
    reappears later is an unexplained arrival only if no addition is
    declared. The accountant cannot detect declared reuse of a past ID,
    or a transient omitted from both event sequences.
    """
    opening_year = _as_year(opening_year, "opening_year")
    closing_year = _as_year(closing_year, "closing_year")
    if closing_year != opening_year + 1:
        raise PopulationAccountingInputError(
            f"closing_year must be opening_year + 1 (this is an annual "
            f"accountant); got opening_year={opening_year} and "
            f"closing_year={closing_year}"
        )

    opening_ids, opening_weights = _read_frame(
        opening, opening_year, "opening frame"
    )
    closing_ids, closing_weights = _read_frame(
        closing, closing_year, "closing frame"
    )
    opening_weight_by_person = dict(
        zip(opening_ids.tolist(), opening_weights.tolist(), strict=True)
    )
    closing_weight_by_person = dict(
        zip(closing_ids.tolist(), closing_weights.tolist(), strict=True)
    )
    opening_set = set(opening_weight_by_person)
    closing_set = set(closing_weight_by_person)

    discrepancies: list[AccountingDiscrepancy] = []
    additions_by_person = _index_events(
        additions,
        expected_kinds=ADDITION_KINDS,
        closing_year=closing_year,
        label="additions",
        duplicate_kind=DiscrepancyKind.DUPLICATE_ADDITION,
        discrepancies=discrepancies,
    )
    exits_by_person = _index_events(
        exits,
        expected_kinds=EXIT_KINDS,
        closing_year=closing_year,
        label="exits",
        duplicate_kind=DiscrepancyKind.DUPLICATE_EXIT,
        discrepancies=discrepancies,
    )

    for person_id in sorted(additions_by_person):
        if person_id in opening_set:
            discrepancies.append(
                AccountingDiscrepancy(
                    kind=DiscrepancyKind.ADDITION_COLLIDES_WITH_OPENING,
                    person_id=person_id,
                    detail=(
                        f"person {person_id} is declared as a "
                        f"{additions_by_person[person_id].kind.value!r} but "
                        "was already present in the opening frame"
                    ),
                )
            )
    for person_id in sorted(exits_by_person):
        if person_id not in opening_set and person_id not in (
            additions_by_person
        ):
            discrepancies.append(
                AccountingDiscrepancy(
                    kind=DiscrepancyKind.EXIT_WITHOUT_PRESENCE,
                    person_id=person_id,
                    detail=(
                        f"person {person_id} is declared as a "
                        f"{exits_by_person[person_id].kind.value!r} but was "
                        "never present: absent from the opening frame and "
                        "never declared as an addition"
                    ),
                )
            )
        if person_id in closing_set:
            discrepancies.append(
                AccountingDiscrepancy(
                    kind=DiscrepancyKind.EXIT_CONTRADICTED_BY_CLOSING,
                    person_id=person_id,
                    detail=(
                        f"person {person_id} is declared as a "
                        f"{exits_by_person[person_id].kind.value!r} but is "
                        "still present in the closing frame"
                    ),
                )
            )
    for person_id in sorted(closing_set - opening_set):
        if person_id not in additions_by_person:
            discrepancies.append(
                AccountingDiscrepancy(
                    kind=DiscrepancyKind.UNDECLARED_ADDITION,
                    person_id=person_id,
                    detail=(
                        f"person {person_id} appears in the closing frame "
                        "with no declared addition; this module will not "
                        "guess whether the identifier is a birth, a "
                        "scheduled entry, or a defect"
                    ),
                )
            )
    for person_id in sorted(opening_set - closing_set):
        if person_id not in exits_by_person:
            discrepancies.append(
                AccountingDiscrepancy(
                    kind=DiscrepancyKind.UNDECLARED_EXIT,
                    person_id=person_id,
                    detail=(
                        f"person {person_id} disappears between the frames "
                        "with no declared exit; this module will not assume "
                        "the person died"
                    ),
                )
            )
    for person_id in sorted(additions_by_person):
        if (
            person_id not in closing_set
            and person_id not in exits_by_person
            and person_id not in opening_set
        ):
            discrepancies.append(
                AccountingDiscrepancy(
                    kind=DiscrepancyKind.ADDITION_ABSENT_AT_CLOSE,
                    person_id=person_id,
                    detail=(
                        f"person {person_id} is declared as a "
                        f"{additions_by_person[person_id].kind.value!r} but "
                        "is absent from the closing frame and has no "
                        "declared exit"
                    ),
                )
            )

    if discrepancies:
        raise PopulationReconciliationError(
            _summarize(discrepancies, opening_year, closing_year),
            _sorted_discrepancies(discrepancies),
        )

    carried = tuple(sorted(opening_set & closing_set))
    entered = tuple(sorted(closing_set - opening_set))
    exited = tuple(sorted(opening_set - closing_set))
    transient = tuple(
        sorted(set(additions_by_person) - opening_set - closing_set)
    )

    counts = PersonCounts(
        opening=len(opening_set),
        closing=len(closing_set),
        carried=len(carried),
        entered=len(entered),
        exited=len(exited),
        transient=len(transient),
        additions_total=len(additions_by_person),
        exits_total=len(exits_by_person),
        additions_by_kind=_count_by_kind(additions_by_person, ADDITION_KINDS),
        exits_by_kind=_count_by_kind(exits_by_person, EXIT_KINDS),
    )
    count_residual = counts.closing - (
        counts.opening + counts.additions_total - counts.exits_total
    )
    if count_residual != 0:
        raise PopulationReconciliationError(
            "the exact person-count identity does not hold: "
            f"closing {counts.closing} != opening {counts.opening} + "
            f"additions {counts.additions_total} - exits "
            f"{counts.exits_total}",
            (
                AccountingDiscrepancy(
                    kind=DiscrepancyKind.COUNT_IDENTITY_VIOLATION,
                    person_id=None,
                    detail=f"count residual {count_residual}",
                ),
            ),
        )

    entry_weight = {
        person_id: _resolve_weight(
            person_id,
            event,
            closing_weight_by_person,
            fallback_label="closing",
        )
        for person_id, event in additions_by_person.items()
    }
    exit_weight = {
        person_id: _resolve_weight(
            person_id,
            event,
            opening_weight_by_person,
            fallback_label="opening",
        )
        for person_id, event in exits_by_person.items()
    }

    revaluation = WeightRevaluation(
        carried=_stable_sum(
            closing_weight_by_person[person_id]
            - opening_weight_by_person[person_id]
            for person_id in carried
        ),
        entrant=_stable_sum(
            closing_weight_by_person[person_id] - entry_weight[person_id]
            for person_id in entered
        ),
        exiting=_stable_sum(
            exit_weight[person_id] - opening_weight_by_person[person_id]
            for person_id in exited
        ),
        transient=_stable_sum(
            exit_weight[person_id] - entry_weight[person_id]
            for person_id in transient
        ),
    )
    additions_by_kind_weight = _weight_by_kind(
        additions_by_person, entry_weight, ADDITION_KINDS
    )
    exits_by_kind_weight = _weight_by_kind(
        exits_by_person, exit_weight, EXIT_KINDS
    )
    weights = WeightTotals(
        opening=_stable_sum(opening_weights.tolist()),
        closing=_stable_sum(closing_weights.tolist()),
        additions_total=_stable_sum(entry_weight.values()),
        exits_total=_stable_sum(exit_weight.values()),
        additions_by_kind=additions_by_kind_weight,
        exits_by_kind=exits_by_kind_weight,
        revaluation=revaluation,
    )
    reconstructed = _stable_sum(
        (
            weights.opening,
            weights.additions_total,
            -weights.exits_total,
            revaluation.total,
        )
    )
    weight_residual = _stable_sum((weights.closing, -reconstructed))

    provenance = MappingProxyType(
        {
            "interface_version": ACCOUNTING_INTERFACE_VERSION,
            "person_id_column": PERSON_ID_COLUMN,
            "year_column": YEAR_COLUMN,
            "weight_column": WEIGHT_COLUMN,
            "summation": SUMMATION_METHOD,
            "inference": INFERENCE_POLICY,
            "opening_rows": int(opening_ids.size),
            "closing_rows": int(closing_ids.size),
            "opening_zero_weight_rows": int(
                np.count_nonzero(opening_weights == 0.0)
            ),
            "closing_zero_weight_rows": int(
                np.count_nonzero(closing_weights == 0.0)
            ),
            "declared_additions": len(additions_by_person),
            "declared_exits": len(exits_by_person),
            "declared_addition_weights": sum(
                1
                for event in additions_by_person.values()
                if event.weight is not None
            ),
            "declared_exit_weights": sum(
                1
                for event in exits_by_person.values()
                if event.weight is not None
            ),
            "event_log_completeness_verified": False,
            "declaration_sources": tuple(
                sorted(
                    {
                        event.source
                        for event in (
                            *additions_by_person.values(),
                            *exits_by_person.values(),
                        )
                        if event.source
                    }
                )
            ),
        }
    )

    return PeriodAccount(
        opening_year=opening_year,
        closing_year=closing_year,
        status=ENGINEERING_STATUS,
        status_note=ENGINEERING_STATUS_NOTE,
        counts=counts,
        weights=weights,
        count_residual=count_residual,
        weight_residual=weight_residual,
        reconstructed_closing_weight=reconstructed,
        carried_person_ids=carried,
        entered_person_ids=entered,
        exited_person_ids=exited,
        transient_person_ids=transient,
        provenance=provenance,
    )


def _count_by_kind(
    indexed: Mapping[int, PopulationEvent],
    kinds: frozenset[PopulationEventKind],
) -> Mapping[str, int]:
    """Count declarations by kind, with every kind present as a key."""
    tally = {kind.value: 0 for kind in sorted(kinds, key=lambda k: k.value)}
    for event in indexed.values():
        tally[event.kind.value] += 1
    return MappingProxyType(tally)


def _weight_by_kind(
    indexed: Mapping[int, PopulationEvent],
    resolved: Mapping[int, float],
    kinds: frozenset[PopulationEventKind],
) -> Mapping[str, float]:
    """Sum resolved event weights by kind, stably, with all keys present."""
    grouped: dict[str, list[float]] = {
        kind.value: [] for kind in sorted(kinds, key=lambda k: k.value)
    }
    for person_id, event in indexed.items():
        grouped[event.kind.value].append(resolved[person_id])
    return MappingProxyType(
        {kind: _stable_sum(values) for kind, values in grouped.items()}
    )


def _sorted_discrepancies(
    discrepancies: Iterable[AccountingDiscrepancy],
) -> tuple[AccountingDiscrepancy, ...]:
    """Order findings deterministically by kind then person."""
    return tuple(
        sorted(
            discrepancies,
            key=lambda item: (
                _DISCREPANCY_ORDER[item.kind],
                -1 if item.person_id is None else item.person_id,
            ),
        )
    )


def _summarize(
    discrepancies: Sequence[AccountingDiscrepancy],
    opening_year: int,
    closing_year: int,
) -> str:
    """Build a stable one-line summary of a refusal."""
    tally: dict[str, int] = {}
    for item in discrepancies:
        tally[item.kind.value] = tally.get(item.kind.value, 0) + 1
    rendered = ", ".join(
        f"{kind}={count}" for kind, count in sorted(tally.items())
    )
    return (
        f"population accounting for {opening_year}->{closing_year} does not "
        f"reconcile: {rendered}"
    )
