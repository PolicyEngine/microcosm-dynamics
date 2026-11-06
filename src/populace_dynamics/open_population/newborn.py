"""Append the newborn entry packet from design §§2.2, 3.1 (OP2) and 7.

Implement ``docs/design/open_population.md`` §§5.4 and 6.1, approved in
ruling d1925. Keep the allocation and maternal carries of
``engine/steps.py:485–507``. A newborn receives its ordinal only at year end
(``engine/loop.py:358–360``), so its sex stream uses its mother's ordinal.
The surrounding ``BirthEntryAdapter`` owns entry provenance and accounting.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from numbers import Integral, Real
from types import MappingProxyType

import numpy as np
import pandas as pd

from populace_dynamics.engine.loop import MaritalStepResult, PeriodContext
from populace_dynamics.engine.rng import ProjectionModule
from populace_dynamics.open_population.conventions import (
    BIRTH_ORDER_COLUMN,
    FOREIGN_BORN_COLUMN,
    NEWBORN_SEX_STREAM_TAG,
    OUT_OF_DOMAIN_COLUMNS,
    PARITY_COLUMN,
    SECOND_PARENT_COLUMN,
    SECOND_PARENT_UNLINKED_COLUMN,
    SPOUSE_ABROAD_COLUMN,
    ConventionSource,
)
from populace_dynamics.open_population.errors import (
    ControlSourceUnavailable,
    IdOrStreamCollision,
    OpenPopulationError,
)

UNLINKED_UNPARTNERED = "unpartnered_mother"
UNLINKED_PARTNER_OUTSIDE_ROSTER = "partner_outside_roster"
UNLINKED_PARTNER_UNKNOWN = "partner_unknown"
UNLINKED_REASONS = frozenset(
    {
        UNLINKED_UNPARTNERED,
        UNLINKED_PARTNER_OUTSIDE_ROSTER,
        UNLINKED_PARTNER_UNKNOWN,
    }
)

#: An assembly adapter supplies the remaining G inputs (design §6.1).
NEWBORN_G_FIELDS: Mapping[str, str] = MappingProxyType(
    {"person_id": "beneficiary_id", "birth_year": "birth_year"}
)
NEWBORN_G_WORKER_LINKS = ("parent_person_id", SECOND_PARENT_COLUMN)


class NewbornPacketRefused(OpenPopulationError):
    """Refuse an incoherent maternal birth or second-parent packet (§7)."""

    code = "NEWBORN_PACKET_REFUSED"


@dataclass(frozen=True, slots=True)
class SexRatioPin:
    """Hold a required sex share and its explicit source (design §5.4)."""

    share_male: float
    source: ConventionSource

    def __post_init__(self) -> None:
        if isinstance(self.share_male, (bool, np.bool_)) or not isinstance(
            self.share_male, Real
        ):
            raise ValueError("the male share must be a real number")
        share = float(self.share_male)
        if not math.isfinite(share) or not 0 < share < 1:
            raise ValueError("the male share must lie strictly inside (0, 1)")
        if type(self.source) is not ConventionSource:
            raise TypeError("a sex ratio needs a ConventionSource")
        object.__setattr__(self, "share_male", share)


def read_second_parents(
    frame: pd.DataFrame,
    mothers: Iterable[int],
    marital: MaritalStepResult,
) -> dict[int, tuple[object, object]]:
    """Read links or registered reasons from authoritative state (§5.4).

    Return ``mother_id: (link, reason)``, with exactly one nonmissing value.
    The supplied state is the year's snapshot; duplicate mother rows refuse
    rather than selecting a state or reconstructing a link from the roster.
    """
    if "person_id" not in frame or frame["person_id"].duplicated().any():
        raise NewbornPacketRefused("the roster needs unique person IDs")
    roster = frame.set_index("person_id", drop=False)
    state = marital.sim_years
    if not state.empty and "person_id" not in state:
        raise NewbornPacketRefused("marital state needs person_id")
    result = {}
    for mother in mothers:
        if mother not in roster.index:
            raise NewbornPacketRefused("a mother is absent from the roster")
        rows = (
            state.loc[state["person_id"].eq(mother)]
            if not state.empty
            else state
        )
        if len(rows) > 1:
            raise NewbornPacketRefused("a mother has duplicate marital rows")
        if rows.empty:
            result[mother] = (pd.NA, UNLINKED_PARTNER_UNKNOWN)
            continue
        row = rows.iloc[0]
        spouse = row.get("spouse_person_id", pd.NA)
        partner = row.get("partner_person_id", pd.NA)
        if pd.notna(spouse) and pd.notna(partner) and spouse != partner:
            raise NewbornPacketRefused("spouse and partner links conflict")
        link = spouse if pd.notna(spouse) else partner
        if pd.notna(link):
            if link == mother:
                raise NewbornPacketRefused("a mother cannot be her own parent")
            result[mother] = (
                (link, pd.NA)
                if link in roster.index
                else (pd.NA, UNLINKED_PARTNER_OUTSIDE_ROSTER)
            )
            continue
        abroad = (
            row[SPOUSE_ABROAD_COLUMN]
            if SPOUSE_ABROAD_COLUMN in state
            else roster.loc[mother].get(SPOUSE_ABROAD_COLUMN, pd.NA)
        )
        status = row.get("marital_status", pd.NA)
        if pd.notna(abroad):
            reason = UNLINKED_PARTNER_OUTSIDE_ROSTER
        elif pd.isna(status) or status == "married":
            reason = UNLINKED_PARTNER_UNKNOWN
        else:
            reason = UNLINKED_UNPARTNERED
        result[mother] = (pd.NA, reason)
    return result


def _integers(values: object, what: str) -> pd.arrays.IntegerArray:
    """Keep packet IDs and counts exact, or refuse an invalid integer."""
    try:
        return pd.array(values, dtype="Int64")
    except (TypeError, ValueError, OverflowError) as error:
        raise NewbornPacketRefused(
            f"{what} must hold nullable integers"
        ) from error


def append_newborn_packet(
    frame: pd.DataFrame,
    births: pd.DataFrame,
    context: PeriodContext,
    marital: MaritalStepResult,
    rng: np.random.Generator,
    *,
    sex_ratio: SexRatioPin,
    second_parents: Callable = read_second_parents,
) -> pd.DataFrame:
    """Materialize this year's maternal births without consuming ``rng``.

    Sort mothers before allocation, as required by design §7's order
    invariance. Only packet fields have values on child rows; other roster
    fields stay missing, as in ``engine/steps.py:485–487`` (design §2.2).
    """
    if type(sex_ratio) is not SexRatioPin:
        raise TypeError("the newborn packet needs a SexRatioPin")
    if births.empty:
        return frame.copy()
    required = {"parent_person_id", "birth_year", BIRTH_ORDER_COLUMN}
    if required - set(births.columns):
        raise NewbornPacketRefused("births need mother, year and birth_order")
    years = _integers(births["birth_year"], "birth years")
    current = births.loc[years == context.year].copy()
    if current.empty:
        return frame.copy()
    if {"person_id", "year", "age", "sex"} - set(frame.columns):
        raise NewbornPacketRefused(
            "the roster needs person_id, year, age and sex"
        )
    if (
        frame["person_id"].isna().any()
        or frame["person_id"].duplicated().any()
    ):
        raise NewbornPacketRefused("the roster needs unique nonmissing IDs")
    current["parent_person_id"] = _integers(
        current["parent_person_id"], "mother IDs"
    )
    current[BIRTH_ORDER_COLUMN] = _integers(
        current[BIRTH_ORDER_COLUMN], "birth orders"
    )
    if current["parent_person_id"].isna().any():
        raise NewbornPacketRefused("a birth needs a mother")
    if (
        current[BIRTH_ORDER_COLUMN].isna().any()
        or (current[BIRTH_ORDER_COLUMN] < 1).any()
    ):
        raise NewbornPacketRefused("birth_order must be a positive count")
    if current["parent_person_id"].duplicated().any():
        raise NewbornPacketRefused("a mother has two births in one year")
    current = current.sort_values("parent_person_id").reset_index(drop=True)
    mothers = current["parent_person_id"].tolist()
    roster = frame.set_index("person_id", drop=False)
    if set(mothers) - set(roster.index):
        raise NewbornPacketRefused("a mother is absent from the roster")
    maternal = roster.loc[mothers]
    if not maternal["sex"].eq("female").fillna(False).all():
        raise NewbornPacketRefused("a mother must have sex female")
    if not maternal["year"].eq(context.year).fillna(False).all():
        raise NewbornPacketRefused("a mother must be on the birth-year roster")

    parent_rows = second_parents(frame, mothers, marital)
    links, reasons = [], []
    for mother in mothers:
        try:
            link, reason = parent_rows[mother]
        except (KeyError, TypeError, ValueError) as error:
            raise NewbornPacketRefused(
                "the second-parent reader lost a mother"
            ) from error
        linked, explained = pd.notna(link), pd.notna(reason)
        if linked == explained:
            raise NewbornPacketRefused(
                "a child needs exactly one link or reason"
            )
        if linked:
            if link == mother:
                raise NewbornPacketRefused("a mother cannot be her own parent")
            if link not in roster.index:
                raise NewbornPacketRefused(
                    "a linked second parent is off roster"
                )
        elif reason not in UNLINKED_REASONS:
            raise NewbornPacketRefused("the unlinked reason is not registered")
        links.append(link)
        reasons.append(reason)

    registry = context.rng_registry
    if registry is None:
        raise IdOrStreamCollision(
            "newborn sex needs the projection RNG registry"
        )
    try:
        uniforms = [
            registry.tagged_child_generator(
                context.period_index,
                ProjectionModule.FERTILITY,
                NEWBORN_SEX_STREAM_TAG,
                context.person_ordinals[mother],
            ).random()
            for mother in mothers
        ]
    except KeyError as error:
        raise IdOrStreamCollision(
            "a mother has no projection RNG ordinal"
        ) from error
    male = np.asarray(uniforms) < sex_ratio.share_male
    count = len(current)
    packet = pd.DataFrame(
        {
            "year": _integers([context.year] * count, "years"),
            "birth_year": _integers([context.year] * count, "birth years"),
            "age": _integers([0] * count, "ages"),
            "sex": np.where(male, "male", "female"),
            "parent_person_id": _integers(mothers, "mother IDs"),
            SECOND_PARENT_COLUMN: _integers(links, "second-parent IDs"),
            SECOND_PARENT_UNLINKED_COLUMN: pd.Series(reasons, dtype=object),
            BIRTH_ORDER_COLUMN: current[BIRTH_ORDER_COLUMN].array,
            "synthetic_entry": pd.array([True] * count, dtype="boolean"),
            **{
                column: pd.array([True] * count, dtype="boolean")
                for column in OUT_OF_DOMAIN_COLUMNS.values()
            },
            PARITY_COLUMN: _integers(
                [pd.NA if is_male else 0 for is_male in male], "parities"
            ),
            FOREIGN_BORN_COLUMN: pd.array([False] * count, dtype="boolean"),
        }
    )
    for carried in ("household_id", "weight", "start_weight"):
        if carried in frame:
            values = maternal[carried].reset_index(drop=True)
            packet[carried] = (
                _integers(values, "household IDs")
                if carried == "household_id"
                else values
            )
    existing = frame.copy()
    integer_columns = {
        "person_id",
        "year",
        "age",
        "birth_year",
        "parent_person_id",
        SECOND_PARENT_COLUMN,
        BIRTH_ORDER_COLUMN,
        PARITY_COLUMN,
        "household_id",
    }
    flags = {"synthetic_entry", *OUT_OF_DOMAIN_COLUMNS.values()}
    for column in existing:
        if column in integer_columns or pd.api.types.is_integer_dtype(
            existing[column]
        ):
            existing[column] = _integers(existing[column], column)
        elif column in flags | {
            FOREIGN_BORN_COLUMN
        } or pd.api.types.is_bool_dtype(existing[column]):
            existing[column] = existing[column].astype("boolean")
    for column in packet:
        if column not in existing:
            existing[column] = pd.Series(
                False if column in flags else pd.NA,
                index=existing.index,
                dtype=packet[column].dtype,
            )
    try:
        allocator = context.synthetic_id_allocator
        start = allocator.next_id
        if isinstance(start, (bool, np.bool_)) or not isinstance(
            start, Integral
        ):
            raise IdOrStreamCollision(
                "the allocator cursor must be an integer"
            )
        start = int(start)
        if (
            start < np.iinfo(np.int64).min
            or start + count - 1 > np.iinfo(np.int64).max
            or any(start <= person < start + count for person in roster.index)
        ):
            raise IdOrStreamCollision(
                "newborn IDs overlap or exceed the namespace"
            )
        packet["person_id"] = _integers(allocator.allocate(count), "child IDs")
    except RuntimeError as error:
        raise IdOrStreamCollision(
            "newborn IDs need a safe projection allocator"
        ) from error
    return pd.concat([existing, packet], ignore_index=True)


@dataclass(frozen=True)
class NewbornPacketStep:
    """Fill the fertility slot with the required packet convention (§3.1)."""

    sex_ratio: SexRatioPin
    second_parents: Callable = read_second_parents

    def __post_init__(self) -> None:
        if type(self.sex_ratio) is not SexRatioPin:
            raise TypeError("the newborn step needs a SexRatioPin")
        if not callable(self.second_parents):
            raise TypeError("the second-parent reader must be callable")

    def __call__(self, frame, context, marital, rng) -> pd.DataFrame:
        """Read births from the one authoritative marital result (§2.1)."""
        return append_newborn_packet(
            frame,
            marital.births,
            context,
            marital,
            rng,
            sex_ratio=self.sex_ratio,
            second_parents=self.second_parents,
        )

    def require_frozen(self) -> None:
        """Refuse an unfrozen sex share under design §8's source condition."""
        self.sex_ratio.source.require_frozen(
            ControlSourceUnavailable, "sex ratio"
        )
