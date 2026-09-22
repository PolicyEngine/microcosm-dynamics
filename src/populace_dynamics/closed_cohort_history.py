"""Compose existing earnings histories with closed-cohort mortality records.

This observer makes no generator calls and supplies no post-death amounts.
It does not integrate the registered assembly or admit a model or source.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from hashlib import sha256
from numbers import Integral

import numpy as np
import pandas as pd

from .forward_earnings_history import ForwardEarningsHistory
from .mortality_observer import MortalityStepObservation
from .person_identity import PersonIdentity

_SCHEMA = "populace_dynamics.closed_cohort_history.v1"


def _integer(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise ValueError("integer required without coercion")
    if not 0 <= value < 2**63:
        raise ValueError("integer outside nonnegative int64")
    return int(value)


def _parse_integer(value: object) -> int:
    if type(value) is not str:
        raise ValueError("canonical integer string required")
    result = _integer(int(value))
    if str(result) != value:
        raise ValueError("noncanonical integer")
    return result


def _digest(value: object) -> None:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError("lowercase SHA-256 digest required")


def _json(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )


def _person_baselines(
    baseline: ForwardEarningsHistory,
) -> dict[int, ForwardEarningsHistory]:
    # A validated 2014 baseline contains exactly one observation per person.
    return {
        row.dynamics_person_key: replace(
            baseline,
            roster_keys=(row.dynamics_person_key,),
            observations=(row,),
        )
        for row in baseline.observations
    }


@dataclass(frozen=True)
class CohortTransition:
    """Actual mortality plus post-aging demographics and frame lineage."""

    mortality: MortalityStepObservation
    lineage_digest: str
    survivor_demographics: tuple[tuple[int, int, str], ...]

    def __post_init__(self) -> None:
        if type(self.mortality) is not MortalityStepObservation:
            raise ValueError("explicit mortality step required")
        _digest(self.lineage_digest)
        demographics = []
        for key, age, sex in self.survivor_demographics:
            if type(sex) is not str:
                raise ValueError("explicit mortality sex label required")
            demographics.append((_integer(key), _integer(age), sex))
        expected = tuple(
            (row.dynamics_person_key, row.age + 1, row.sex)
            for row in self.mortality.rows
            if row.survived
        )
        if tuple(demographics) != expected:
            raise ValueError("survivor demographics must match actual aging")
        object.__setattr__(self, "survivor_demographics", tuple(demographics))


@dataclass(frozen=True)
class ClosedCohortEarningsHistory:
    """Original persons remain recorded while only mortality survivors append."""

    baseline: ForwardEarningsHistory
    draw_index: int
    histories: tuple[ForwardEarningsHistory, ...]
    transitions: tuple[CohortTransition, ...] = ()

    def __init_subclass__(cls, **kwargs) -> None:
        raise TypeError("ClosedCohortEarningsHistory cannot be subclassed")

    def __post_init__(self) -> None:
        if (
            type(self.baseline) is not ForwardEarningsHistory
            or self.baseline.last_year != 2014
        ):
            raise ValueError("baseline must be an explicit 2014 history")
        object.__setattr__(self, "draw_index", _integer(self.draw_index))
        histories, transitions = tuple(self.histories), tuple(self.transitions)
        if len(transitions) > 8:
            raise ValueError("closed-cohort history cannot extend past 2022")
        if any(
            type(h) is not ForwardEarningsHistory or len(h.roster_keys) != 1
            for h in histories
        ):
            raise ValueError(
                "one existing history per original person required"
            )
        keys = [h.roster_keys[0] for h in histories]
        if tuple(sorted(keys)) != self.baseline.roster_keys:
            raise ValueError(
                "person histories must cover the original roster once"
            )
        if any(type(t) is not CohortTransition for t in transitions):
            raise ValueError("typed annual transitions required")
        active, previous, deaths = self.baseline.roster_keys, {}, {}
        signature = None
        for offset, transition in enumerate(transitions, 1):
            mortality = transition.mortality
            if (
                mortality.target_year != 2014 + offset
                or mortality.period_index != offset
                or mortality.draw_index != self.draw_index
                or mortality.identity_map != self.baseline.identity_map
                or mortality.realization_id != self.baseline.realization_id
            ):
                raise ValueError(
                    "mortality calendar, identity or realization mismatch"
                )
            current_signature = (
                mortality.model,
                mortality.source_contract_digest,
                mortality.registry_n_periods,
            )
            if signature is not None and current_signature != signature:
                raise ValueError("mortality model, source or RNG mode changed")
            signature = current_signature
            if mortality.pre_keys != active:
                raise ValueError(
                    "mortality input roster must equal prior survivors"
                )
            for row in mortality.rows:
                key = row.dynamics_person_key
                if previous:
                    prior = previous[key]
                    if (
                        row.age != prior.age + 1
                        or row.sex != prior.sex
                        or row.person_ordinal != prior.person_ordinal
                    ):
                        raise ValueError(
                            "mortality demographic or ordinal continuity changed"
                        )
                if not row.survived:
                    deaths[key] = mortality.target_year
            previous = {
                r.dynamics_person_key: r for r in mortality.rows if r.survived
            }
            active = mortality.post_keys
        person_baselines = _person_baselines(self.baseline)
        for history in histories:
            key = history.roster_keys[0]
            history.require_extension_of(person_baselines[key])
            end = deaths[key] - 1 if key in deaths else 2014 + len(transitions)
            if history.last_year != end:
                raise ValueError(
                    "person history extent disagrees with mortality"
                )
            for row in history.observations[1:]:
                if (
                    row.lineage_digest
                    != transitions[row.year - 2015].lineage_digest
                ):
                    raise ValueError(
                        "annual earnings lineage disagrees with transition"
                    )
        object.__setattr__(
            self,
            "histories",
            tuple(sorted(histories, key=lambda h: h.roster_keys[0])),
        )
        object.__setattr__(self, "transitions", transitions)

    @classmethod
    def start(
        cls, initial_history: ForwardEarningsHistory, *, draw_index: int
    ) -> ClosedCohortEarningsHistory:
        """Bind an already materialized 2014 history without changing it."""
        if (
            type(initial_history) is not ForwardEarningsHistory
            or initial_history.last_year != 2014
        ):
            raise ValueError("baseline must be an explicit 2014 history")
        return cls(
            initial_history,
            draw_index,
            tuple(_person_baselines(initial_history).values()),
        )

    @property
    def last_year(self) -> int:
        return 2014 + len(self.transitions)

    @property
    def active_keys(self) -> tuple[int, ...]:
        return (
            self.transitions[-1].mortality.post_keys
            if self.transitions
            else self.baseline.roster_keys
        )

    def append(
        self,
        *,
        mortality: MortalityStepObservation,
        earnings_frame: pd.DataFrame,
        lineage_digest: str,
    ) -> ClosedCohortEarningsHistory:
        """Observe one actual survivor frame; never generate or fill earnings."""
        if self.last_year == 2022:
            raise ValueError("closed-cohort history cannot extend past 2022")
        if type(mortality) is not MortalityStepObservation:
            raise ValueError("explicit mortality step required")
        if mortality.pre_keys != self.active_keys:
            raise ValueError(
                "mortality input roster must equal prior survivors"
            )
        frame = earnings_frame
        required = {
            "person_id",
            "year",
            "age",
            "sex",
            "earnings",
            "earnings_domain",
        }
        if (
            not isinstance(frame, pd.DataFrame)
            or not frame.columns.is_unique
            or not required.issubset(frame.columns)
        ):
            raise ValueError(
                "earnings frame requires unique observation columns"
            )
        for column, dtype in (
            ("person_id", "int64"),
            ("year", "int64"),
            ("age", "int64"),
            ("earnings", "float64"),
            ("earnings_domain", "bool"),
        ):
            if frame[column].dtype != np.dtype(dtype):
                raise ValueError(f"{column} must preserve {dtype} dtype")
        if not pd.api.types.is_string_dtype(frame["sex"].dtype):
            raise ValueError("sex must preserve a string-compatible dtype")
        if tuple(sorted(frame["person_id"])) != mortality.post_keys:
            raise ValueError(
                "earnings frame must contain exactly the survivors"
            )
        if not (frame["year"] == self.last_year + 1).all():
            raise ValueError("earnings frame must contain the next year")
        ordered = frame.sort_values("person_id", kind="stable")
        transition = CohortTransition(
            mortality,
            lineage_digest,
            tuple(
                zip(
                    ordered["person_id"],
                    ordered["age"],
                    ordered["sex"],
                    strict=True,
                )
            ),
        )
        survivors = set(mortality.post_keys)
        by_person = frame.set_index("person_id", drop=False)
        histories = tuple(
            (
                history.append(
                    by_person.loc[[history.roster_keys[0]]],
                    lineage_digest=lineage_digest,
                )
                if history.roster_keys[0] in survivors
                else history
            )
            for history in self.histories
        )
        return type(self)(
            self.baseline,
            self.draw_index,
            histories,
            self.transitions + (transition,),
        )

    def for_person(self, identity: PersonIdentity) -> ForwardEarningsHistory:
        """Return the retained existing history using exact source identity."""
        key = self.baseline.identity_map.map_rows([identity])[0]
        for history in self.histories:
            if history.roster_keys == (key,):
                return history
        raise ValueError("person is outside the original cohort")

    def death_step(
        self, identity: PersonIdentity
    ) -> MortalityStepObservation | None:
        """Return the recorded removal step, without inferring a death date."""
        key = self.for_person(identity).roster_keys[0]
        for transition in self.transitions:
            if (
                key in transition.mortality.pre_keys
                and key not in transition.mortality.post_keys
            ):
                return transition.mortality
        return None

    def amount_state(self, identity: PersonIdentity, *, year: int) -> str:
        """Distinguish generated amounts, unsupported inputs and mortality."""
        year = _integer(year)
        if not 2014 <= year <= self.last_year:
            raise ValueError("year is outside the observed cohort envelope")
        history = self.for_person(identity)
        if year <= history.last_year:
            return history.observations[year - 2014].amount_state
        return "not_generated_after_mortality_step"

    def require_extension_of(
        self, previous: ClosedCohortEarningsHistory
    ) -> None:
        """Reject changes to the baseline, draw or any prior observation."""
        if (
            type(previous) is not ClosedCohortEarningsHistory
            or self.baseline != previous.baseline
            or self.draw_index != previous.draw_index
        ):
            raise ValueError("cohort extension changed baseline or draw")
        if (
            self.transitions[: len(previous.transitions)]
            != previous.transitions
        ):
            raise ValueError(
                "cohort extension removed or changed prior transitions"
            )
        for current, prior in zip(
            self.histories, previous.histories, strict=True
        ):
            current.require_extension_of(prior)

    def to_json(self) -> str:
        """Compose existing canonical records with an external baseline bind."""
        return _json(
            {
                "schema": _SCHEMA,
                "baseline_digest": self.baseline.digest,
                "draw_index": str(self.draw_index),
                "last_year": str(self.last_year),
                "histories": [json.loads(h.to_json()) for h in self.histories],
                "transitions": [
                    {
                        "mortality": json.loads(t.mortality.to_json()),
                        "lineage_digest": t.lineage_digest,
                        "survivor_demographics": [
                            [str(key), str(age), sex]
                            for key, age, sex in t.survivor_demographics
                        ],
                    }
                    for t in self.transitions
                ],
            }
        )

    @property
    def digest(self) -> str:
        return sha256(self.to_json().encode("utf-8")).hexdigest()

    @classmethod
    def from_json(
        cls,
        text: str,
        *,
        baseline: ForwardEarningsHistory,
        expected_digest: str | None = None,
        previous: ClosedCohortEarningsHistory | None = None,
    ) -> ClosedCohortEarningsHistory:
        """Load through existing validators, then check cross-step continuity."""

        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("duplicate JSON field")
                result[key] = value
            return result

        def reject(value):
            raise ValueError(f"invalid JSON constant: {value}")

        document = json.loads(
            text, object_pairs_hook=unique, parse_constant=reject
        )
        if (
            type(baseline) is not ForwardEarningsHistory
            or not isinstance(document, dict)
            or document.get("baseline_digest") != baseline.digest
        ):
            raise ValueError("trusted baseline digest mismatch")
        try:
            result = cls(
                baseline,
                _parse_integer(document["draw_index"]),
                tuple(
                    ForwardEarningsHistory.from_json(_json(h))
                    for h in document["histories"]
                ),
                tuple(
                    CohortTransition(
                        MortalityStepObservation.from_json(
                            _json(t["mortality"]),
                            identity_map=baseline.identity_map,
                        ),
                        t["lineage_digest"],
                        tuple(
                            (_parse_integer(key), _parse_integer(age), sex)
                            for key, age, sex in t["survivor_demographics"]
                        ),
                    )
                    for t in document["transitions"]
                ),
            )
        except (KeyError, TypeError) as exc:
            raise ValueError("invalid closed-cohort record structure") from exc
        if result.to_json() != _json(document):
            raise ValueError(
                "noncanonical or inconsistent closed-cohort record"
            )
        if expected_digest is not None:
            _digest(expected_digest)
            if result.digest != expected_digest:
                raise ValueError("closed-cohort digest mismatch")
        if previous is not None:
            result.require_extension_of(previous)
        return result
