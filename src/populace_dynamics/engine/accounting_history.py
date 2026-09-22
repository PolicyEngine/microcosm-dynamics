"""Optional accounting of supplied annual frames under an explicit ID contract.

This module adds boundary and identity-history checks to ``reconcile_period``.
It neither generates events nor establishes their truth or completeness. The
only supported identity contract allows one presence episode per person ID
within the supplied history; same-ID return requires a different contract.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType

import pandas as pd

from . import accounting

__all__ = [
    "HISTORY_INTERFACE_VERSION",
    "SINGLE_PRESENCE_EPISODE",
    "AnnualTransition",
    "HistoryAccount",
    "HistoryAccountingError",
    "HistoryErrorKind",
    "reconcile_history",
]

HISTORY_INTERFACE_VERSION = "accounting-history/0.1.0-experimental"
SINGLE_PRESENCE_EPISODE = "single_presence_episode"


class HistoryErrorKind(str, Enum):
    """The stage at which a supplied history is refused."""

    INPUT = "input"
    PERIOD = "period"
    NONCONTIGUOUS = "noncontiguous"
    BOUNDARY_PERSON_IDS = "boundary_person_ids"
    BOUNDARY_WEIGHTS = "boundary_weights"
    RETIRED_PERSON_ID = "retired_person_id"


class HistoryAccountingError(accounting.PopulationAccountingError):
    """A history refusal, with a zero-based period index when applicable.

    Annual input/reconciliation failures retain the original exception as
    ``__cause__``, including its typed discrepancies. No partial history
    account is returned on failure.
    """

    def __init__(
        self,
        message: str,
        *,
        kind: HistoryErrorKind,
        period_index: int | None = None,
        opening_year: int | None = None,
        closing_year: int | None = None,
        person_ids: tuple[int, ...] = (),
    ) -> None:
        self.kind = kind
        self.period_index = period_index
        self.opening_year = opening_year
        self.closing_year = closing_year
        self.person_ids = person_ids
        prefix = (
            "history" if period_index is None else f"period[{period_index}]"
        )
        super().__init__(f"{prefix}: {message}")

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe refusal without serializing input containers."""
        cause = self.__cause__
        return {
            "interface_version": HISTORY_INTERFACE_VERSION,
            "error": "history_accounting_error",
            "kind": self.kind.value,
            "message": str(self),
            "period_index": self.period_index,
            "opening_year": self.opening_year,
            "closing_year": self.closing_year,
            "person_ids": list(self.person_ids),
            "cause": (
                {
                    "type": type(cause).__name__,
                    "message": str(cause),
                    "details": (
                        cause.to_dict()
                        if isinstance(
                            cause, accounting.PopulationReconciliationError
                        )
                        else None
                    ),
                }
                if cause is not None
                else None
            ),
        }


@dataclass(frozen=True)
class AnnualTransition:
    """One supplied period, without ownership of the caller's containers.

    Freezing this descriptor prevents field reassignment. The DataFrames and
    any declaration lists remain caller-owned and mutable; reconciliation
    reads snapshots and never stores those containers in its result.
    """

    opening_year: int
    closing_year: int
    opening: pd.DataFrame
    closing: pd.DataFrame
    additions: Sequence[accounting.PopulationEvent] = ()
    exits: Sequence[accounting.PopulationEvent] = ()


@dataclass(frozen=True)
class HistoryAccount:
    """Immutable annual accounts and the IDs observed within this history."""

    identity_contract: str
    periods: tuple[accounting.PeriodAccount, ...]
    seen_person_ids: tuple[int, ...]
    retired_person_ids: tuple[int, ...]
    provenance: Mapping[str, object]

    def to_dict(self) -> dict[str, object]:
        """Return fresh summary containers, omitting the identifier rosters."""
        return {
            "interface_version": HISTORY_INTERFACE_VERSION,
            "status": accounting.ENGINEERING_STATUS,
            "identity_contract": self.identity_contract,
            "periods": [period.to_dict() for period in self.periods],
            "provenance": dict(self.provenance),
        }


def _snapshot_frame(
    frame: pd.DataFrame, year: int, label: str
) -> tuple[pd.DataFrame, dict[int, float]]:
    # Reuse the accountant's strict domain before conversion. These helpers
    # are internal to the same package; annual law remains reconcile_period.
    ids, weights = accounting._read_frame(frame, year, label)
    return (
        pd.DataFrame(
            {
                accounting.PERSON_ID_COLUMN: ids,
                accounting.YEAR_COLUMN: year,
                accounting.WEIGHT_COLUMN: weights,
            }
        ),
        dict(zip(ids.tolist(), weights.tolist(), strict=True)),
    )


def _snapshot_events(events: object) -> object:
    # Preserve malformed inputs for the accountant's own typed validation.
    if isinstance(events, Sequence) and not isinstance(events, (str, bytes)):
        return tuple(events)
    return events


def reconcile_history(
    transitions: Sequence[AnnualTransition], *, identity_contract: str
) -> HistoryAccount:
    """Reconcile nonempty, ordered, contiguous annual periods.

    ``identity_contract`` must explicitly be ``single_presence_episode``.
    Every declared departure retires its ID for the supplied history under
    that chosen constraint, regardless of cause. This does not assert that
    emigration or another exit is demographically permanent. A same-ID return
    is unsupported, including a return declared as a transient.

    Adjacent snapshots must agree on the person-ID set and exact binary64
    weight per ID, independent of row order. Other columns are not compared.
    The first opening roster supplies no prehistory. Callers must not mutate
    input containers concurrently while this function reads them.
    """
    if (
        not isinstance(identity_contract, str)
        or identity_contract != SINGLE_PRESENCE_EPISODE
    ):
        raise HistoryAccountingError(
            "identity_contract must explicitly be 'single_presence_episode'; "
            "general same-person re-entry requires a separate typed contract",
            kind=HistoryErrorKind.INPUT,
        )
    if (
        isinstance(transitions, (str, bytes))
        or not isinstance(transitions, Sequence)
        or not transitions
    ):
        raise HistoryAccountingError(
            "transitions must be a nonempty ordered sequence of "
            "AnnualTransition",
            kind=HistoryErrorKind.INPUT,
        )

    periods: list[accounting.PeriodAccount] = []
    seen: set[int] = set()
    retired: set[int] = set()
    previous_closing: dict[int, float] = {}
    for index, transition in enumerate(tuple(transitions)):
        opening_year = closing_year = None
        try:
            if not isinstance(transition, AnnualTransition):
                raise accounting.PopulationAccountingInputError(
                    "transition must be an AnnualTransition"
                )
            opening_year = accounting._as_year(
                transition.opening_year, "opening_year"
            )
            closing_year = accounting._as_year(
                transition.closing_year, "closing_year"
            )
            opening, opening_by_id = _snapshot_frame(
                transition.opening, opening_year, "opening frame"
            )
            closing, closing_by_id = _snapshot_frame(
                transition.closing, closing_year, "closing frame"
            )
            account = accounting.reconcile_period(
                opening,
                closing,
                opening_year=opening_year,
                closing_year=closing_year,
                additions=_snapshot_events(transition.additions),
                exits=_snapshot_events(transition.exits),
            )
        except accounting.PopulationAccountingError as error:
            raise HistoryAccountingError(
                str(error),
                kind=HistoryErrorKind.PERIOD,
                period_index=index,
                opening_year=opening_year,
                closing_year=closing_year,
            ) from error

        context = {
            "period_index": index,
            "opening_year": opening_year,
            "closing_year": closing_year,
        }
        if periods:
            if opening_year != periods[-1].closing_year:
                raise HistoryAccountingError(
                    "periods must be ordered and contiguous: "
                    f"expected opening year {periods[-1].closing_year}",
                    kind=HistoryErrorKind.NONCONTIGUOUS,
                    **context,
                )
            differing_ids = previous_closing.keys() ^ opening_by_id.keys()
            if differing_ids:
                raise HistoryAccountingError(
                    "shared boundary person-ID sets differ",
                    kind=HistoryErrorKind.BOUNDARY_PERSON_IDS,
                    person_ids=tuple(sorted(differing_ids)),
                    **context,
                )
            differing_weights = tuple(
                sorted(
                    person_id
                    for person_id, weight in opening_by_id.items()
                    if weight != previous_closing[person_id]
                )
            )
            if differing_weights:
                raise HistoryAccountingError(
                    "shared boundary weights differ in the accountant's "
                    "binary64 domain",
                    kind=HistoryErrorKind.BOUNDARY_WEIGHTS,
                    person_ids=differing_weights,
                    **context,
                )
        else:
            seen.update(opening_by_id)

        reused = tuple(sorted(retired.intersection(account.added_person_ids)))
        if reused:
            raise HistoryAccountingError(
                "a departed person ID was declared again; reuse and "
                "same-person return are unsupported under the explicitly "
                "selected single_presence_episode contract",
                kind=HistoryErrorKind.RETIRED_PERSON_ID,
                person_ids=reused,
                **context,
            )
        seen.update(account.added_person_ids)
        retired.update(account.departed_person_ids)
        periods.append(account)
        previous_closing = closing_by_id

    return HistoryAccount(
        identity_contract=SINGLE_PRESENCE_EPISODE,
        periods=tuple(periods),
        seen_person_ids=tuple(sorted(seen)),
        retired_person_ids=tuple(sorted(retired)),
        provenance=MappingProxyType(
            {
                "annual_accounting_interface": (
                    accounting.ACCOUNTING_INTERFACE_VERSION
                ),
                "scope": "supplied history only; first opening has no prehistory",
                "boundary_comparison": "person-ID set and binary64 weight per ID",
                "other_column_continuity_verified": False,
                "event_log_completeness_verified": False,
                "event_truth_verified": False,
                "retirement_policy": "all declared departures under the selected contract",
                "general_reentry_supported": False,
            }
        ),
    )
