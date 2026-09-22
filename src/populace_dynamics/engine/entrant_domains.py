"""Experimental support restrictions for explicitly scheduled entrants.

Recovered from local entrant work at 61bbf1c7e25a7e55033c134bbc2e846022b8850b.
The existing fitted 2014 earnings state and observed disability panel do not
supply histories for newly allocated IDs. The historical claiming adapter also
has no insured-status gate. This module therefore identifies unsupported rows
and offers an explicit claiming wrapper; it does not supply entrant behavior,
entitlement, or an admitted population. Fertility/disability ID inventories
and demographic scope declarations do not demonstrate step execution.

A source-only recovery accepts caller-supplied synthetic frames. No native
donor, control release, fitted model, or scientific gate is invoked here.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from populace_dynamics.engine.earnings_domain import EARNINGS_DOMAIN_COLUMN
from populace_dynamics.engine.entrant_schedule import (
    ENTRY_KIND_BIRTH,
    ENTRY_KIND_COLUMN,
    ENTRY_KIND_IMMIGRANT,
    ENTRY_KIND_INCUMBENT,
    ENTRY_KIND_REALIZED_OPENER,
)
from populace_dynamics.engine.steps import materialize_maternal_births

__all__ = [
    "EXCLUDED_DOMAINS",
    "EntrantClaimingAdapter",
    "EntrantExclusionReport",
    "entrant_mask",
    "materialize_births_with_provenance",
    "assert_entrants_out_of_earnings_domain",
    "excluded_claiming_ids",
    "excluded_disability_ids",
    "excluded_fertility_ids",
    "exclusion_report",
    "suppress_entrant_benefit_outputs",
]

#: The four domains an entrant is excluded from, and why each one is unfitted.
EXCLUDED_DOMAINS: Mapping[str, str] = {
    "fertility_risk": (
        "steps.py:451-506 materializes births only for on-roster mothers and "
        "initializes parity at zero; no entrant parity or birth-history seed "
        "exists, so leaving entrants at risk would assert every entrant "
        "arrived childless"
    ),
    "claiming_eligibility": (
        "steps.py:390-450 draws a claim age for everyone aged 50+ with no "
        "insured-status, quarters-of-coverage, AIME or PIA test; reported "
        "year of entry does not identify FIRST entry, so prior US covered "
        "earnings are unknown/censored rather than zero and insured status "
        "cannot be established from either survey"
    ),
    "disability_panel": (
        "disability.py:56-60 filters a PSID-built DisabilityPanel to "
        "holdout_ids; entrants are not in the panel, and ASEC/CPS disability "
        "items are not realized PSID M4 status"
    ),
    "earnings_domain": (
        "earnings_domain.py:150-208 keys membership on the generator's fitted "
        "2014 state and forward_earnings.py:1421-1436 raises without it; the "
        "section 2.8.3a certificate was never fitted on entrants and does not "
        "transfer to them"
    ),
}


def entrant_mask(
    frame: pd.DataFrame,
    *,
    entry_kinds: Iterable[str] = (ENTRY_KIND_IMMIGRANT,),
) -> np.ndarray:
    """Boolean membership: is each row a scheduled entrant?

    Reads the explicit :data:`~populace_dynamics.engine.entrant_schedule.ENTRY_KIND_COLUMN`
    provenance column.  A frame without that column is a closed-panel frame
    and every row is an incumbent -- that is the honest reading, and it keeps
    this predicate safe to call on a roster that has never seen a schedule.
    A missing value is also treated as incumbent unless the row is explicitly
    synthetic. Synthetic rows require a known entry kind, so losing that
    provenance cannot silently remove their exclusion.
    """
    known = {
        ENTRY_KIND_BIRTH,
        ENTRY_KIND_INCUMBENT,
        ENTRY_KIND_IMMIGRANT,
        ENTRY_KIND_REALIZED_OPENER,
    }
    if isinstance(entry_kinds, (str, bytes)):
        raise ValueError(
            "entry_kinds must be a collection, not a scalar string"
        )
    kinds = set(entry_kinds)
    if not kinds:
        raise ValueError("entrant_mask needs at least one entry kind")
    if not kinds.issubset(known):
        raise ValueError("entry_kinds contains unknown selectors")
    values = frame.get(
        ENTRY_KIND_COLUMN, pd.Series(pd.NA, index=frame.index)
    ).to_numpy()
    synthetic = frame.get(
        "synthetic_entry", pd.Series(False, index=frame.index)
    ).to_numpy()
    for value, synthetic_value in zip(values, synthetic, strict=True):
        if not pd.isna(synthetic_value) and not isinstance(
            synthetic_value, (bool, np.bool_)
        ):
            raise ValueError(
                "synthetic_entry must contain booleans or missing"
            )
        is_synthetic = not pd.isna(synthetic_value) and synthetic_value
        if pd.isna(value):
            if is_synthetic:
                raise ValueError(
                    "synthetic entrants require explicit entry_kind"
                )
        elif not isinstance(value, str) or value not in known:
            raise ValueError(f"unknown entry_kind {value!r}")
    return np.asarray(
        [(not pd.isna(value)) and str(value) in kinds for value in values],
        dtype=bool,
    )


def materialize_births_with_provenance(
    frame: pd.DataFrame,
    births: pd.DataFrame,
    context: Any,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Label children at the actual historical birth-materialization boundary.

    Existing synthetic rows must already have valid provenance. Only rows
    allocated by this call receive the maternal-birth marker. This helper
    handles supplied birth records; it does not fit/simulate fertility or
    enforce the entrant fertility risk restriction.
    """
    entrant_mask(frame)
    out = materialize_maternal_births(frame, births, context, rng)
    added = ~out["person_id"].isin(frame["person_id"])
    if ENTRY_KIND_COLUMN not in out:
        out[ENTRY_KIND_COLUMN] = pd.Series(
            pd.NA, index=out.index, dtype="object"
        )
    out.loc[added, ENTRY_KIND_COLUMN] = ENTRY_KIND_BIRTH
    return out


def _entrant_ids(frame: pd.DataFrame, **kwargs: Any) -> set[int]:
    mask = entrant_mask(frame, **kwargs)
    return {int(value) for value in frame.loc[mask, "person_id"]}


def excluded_fertility_ids(frame: pd.DataFrame, **kwargs: Any) -> set[int]:
    """Person IDs to remove from the fertility risk set.

    This is an inventory, not a fertility adapter. Historical
    ``apply_fertility`` treats an empty ``holdout_ids`` as all roster IDs and
    its precomputed-birth path does not apply that argument. Passing this
    set's complement therefore does not establish entrant exclusion.
    """
    return _entrant_ids(frame, **kwargs)


def excluded_claiming_ids(frame: pd.DataFrame, **kwargs: Any) -> set[int]:
    """Person IDs whose claiming draw must be suppressed."""
    return _entrant_ids(frame, **kwargs)


def excluded_disability_ids(frame: pd.DataFrame, **kwargs: Any) -> set[int]:
    """Person IDs to keep out of the M4 disability panel's holdout set."""
    return _entrant_ids(frame, **kwargs)


def assert_entrants_out_of_earnings_domain(frame: pd.DataFrame) -> int:
    """Fail loudly if any entrant is marked inside the fitted earnings domain.

    Returns the number of entrants checked.  There is no "exclude" step to
    perform here -- ``earnings_domain.membership`` already excludes them by
    construction, because a synthetic ID cannot be in the fitted 2014 state
    maps.  This is the assertion that the construction was not circumvented,
    which is the failure mode ``validate_domain`` exists to catch.
    """
    mask = entrant_mask(frame)
    if not mask.any():
        return 0
    if EARNINGS_DOMAIN_COLUMN not in frame.columns:
        return int(mask.sum())
    marked = frame.loc[mask, EARNINGS_DOMAIN_COLUMN]
    offending = marked.fillna(False).astype(bool).to_numpy()
    if offending.any():
        bad = frame.loc[mask].loc[offending, "person_id"].tolist()[:10]
        raise ValueError(
            "scheduled entrants are marked inside the fitted earnings "
            f"domain: {bad}; the section 2.8.3a certificate does not transfer "
            "to a population it was never fitted on"
        )
    return int(mask.sum())


def suppress_entrant_benefit_outputs(
    frame: pd.DataFrame, *, columns: Iterable[str] = ("aime", "pia", "benefit")
) -> pd.DataFrame:
    """Blank entrant benefit outputs to missing, never to zero.

    A zero AIME is a *measurement*: it says this person had no covered
    earnings.  For an entrant it would be a fabrication, because reported year
    of entry does not identify first entry, so prior US covered earnings are
    censored rather than absent.  Missing is the only honest value until a
    stock-to-arrival and insured-status bridge exists.
    """
    out = frame.copy()
    mask = entrant_mask(out)
    if not mask.any():
        return out
    for column in columns:
        if column in out.columns:
            out.loc[mask, column] = pd.NA
    return out


@dataclass(frozen=True)
class EntrantExclusionReport:
    """What was excluded, from where, and how many -- for the run artifact."""

    n_rows: int
    n_entrants: int
    excluded: dict[str, dict[str, Any]]

    def as_dict(self) -> dict[str, Any]:
        return {
            "n_rows": self.n_rows,
            "n_entrants": self.n_entrants,
            "excluded_domains": self.excluded,
            "gated": False,
            "status": "inventory_only",
            "interpretation": (
                "an excluded entrant is OUTSIDE the estimand for that domain, "
                "not a person modelled as having no children, no disability "
                "and no claim; suppressed counts are reported instead of "
                "zeros for exactly that reason"
            ),
            "execution_verified": False,
            "intended_demographic_domains": [
                "mortality (age/sex draw at the entry age)",
                "aging (deterministic advance)",
            ],
            "not_certified": (
                "entrant benefit levels, insured status, prior US covered "
                "earnings, legal status, population stocks and every "
                "post-entry transition remain out of scope"
            ),
        }


def exclusion_report(frame: pd.DataFrame) -> EntrantExclusionReport:
    """Measure the exclusions on one roster frame."""
    mask = entrant_mask(frame)
    n_entrants = int(mask.sum())
    age = (
        frame["age"].to_numpy(dtype=np.float64)
        if "age" in frame.columns
        else np.full(len(frame), np.nan)
    )
    missing_plan = (
        frame.get("claim_age", pd.Series(pd.NA, index=frame.index))
        .isna()
        .to_numpy()
    )
    claim_exposed = int((mask & (age >= 50) & missing_plan).sum())
    female = (
        frame["sex"].astype(str).to_numpy() == "female"
        if "sex" in frame.columns
        else np.zeros(len(frame), dtype=bool)
    )
    fertile_exposed = int((mask & female & (age >= 15) & (age <= 49)).sum())

    excluded: dict[str, dict[str, Any]] = {}
    for domain, reason in EXCLUDED_DOMAINS.items():
        record: dict[str, Any] = {
            "n_excluded": n_entrants,
            "reason": reason,
        }
        if domain == "claiming_eligibility":
            record["n_would_have_drawn_a_claim_age"] = claim_exposed
            record["counterfactual"] = (
                "without this exclusion apply_claiming would draw a claim age "
                f"for {claim_exposed} entrant rows aged 50+ without a plan; "
                "this inventory does not verify execution or entitlement"
            )
        if domain == "fertility_risk":
            record["n_would_have_been_at_risk"] = fertile_exposed
        if domain == "earnings_domain":
            record["n_checked_out_of_domain"] = (
                assert_entrants_out_of_earnings_domain(frame)
            )
        excluded[domain] = record
    return EntrantExclusionReport(
        n_rows=int(len(frame)), n_entrants=n_entrants, excluded=excluded
    )


@dataclass(frozen=True)
class EntrantClaimingAdapter:
    """Run a claiming step on incumbents only, leaving entrants unclaimed.

    The direct analogue of :class:`~populace_dynamics.engine.earnings_domain.EarningsDomainAdapter`:
    it keeps a support restriction outside the historical step rather than
    editing the historical step; entrant rows never reach that step.

    Existing entrant plans, claim years, claimed state, or conversion events
    are rejected before the incumbent step runs. They require a separately
    admitted claim-history path; this wrapper does not erase them or rule on
    observed entitlement. For admitted inputs, those three fields come back as
    missing / ``False`` / missing.  ``claimed = False`` is not a behavioural
    claim that entrants never retire -- it is the roster's structural default
    for a person outside the claiming estimand, and
    :func:`exclusion_report` publishes how many rows it applied to so the
    suppression is never mistaken for a measured zero.
    """

    step: Any
    entry_kinds: tuple[str, ...] = (ENTRY_KIND_IMMIGRANT,)

    def __call__(
        self,
        frame: pd.DataFrame,
        context: Any,
        rng: np.random.Generator,
    ) -> pd.DataFrame:
        mask = entrant_mask(frame, entry_kinds=self.entry_kinds)
        if not mask.any():
            return self.step(frame, context, rng)
        incumbents = frame.loc[~mask].copy()
        entrants = frame.loc[mask].copy()
        # Preserve possible observed entitlement by rejecting unsupported
        # state, rather than overwriting it with an exclusion default.
        for column in ("claim_age", "claim_year"):
            if column in entrants and entrants[column].notna().any():
                raise ValueError(
                    f"excluded entrants have existing {column}; an admitted "
                    "claim-history path is required"
                )
        for column in ("claimed", "di_converted"):
            if column in entrants:
                observed = entrants[column].dropna()
                if any(
                    not isinstance(value, (bool, np.bool_)) or value
                    for value in observed
                ):
                    raise ValueError(
                        f"excluded entrants have unsupported {column} state"
                    )
        advanced = (
            self.step(incumbents, context, rng)
            if not incumbents.empty
            else incumbents
        )
        for column, default in (
            ("claim_age", pd.NA),
            ("claimed", False),
            ("claim_year", pd.NA),
        ):
            entrants[column] = pd.array(
                [default] * len(entrants),
                dtype="bool" if column == "claimed" else "Int64",
            )
        out = pd.concat([advanced, entrants], ignore_index=True, sort=False)
        return out.sort_values("person_id", kind="stable").reset_index(
            drop=True
        )
