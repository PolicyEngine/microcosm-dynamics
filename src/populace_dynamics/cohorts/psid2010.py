"""The PSID starting cohorts of Track A (work item A3).

This module builds the closed starting population proposed for DynaSim
scorecard exercise 1 in the critical-path plan
(``critical-path-cola-20260922.md``, section 3 and work item A3): persons
observed in the 2011 PSID wave (income year 2010), born 1980 or earlier,
weighted with the 2011 core/immigrant individual cross-sectional weight.
For each member it assembles sex, birth year, death year where known,
marital state and spouse links at the end of 2010, self-reported
work-limitation (M4) status, observed Social Security receipt for income
years 2008, 2010 and 2012, an opening-stock status with an opening claim
year, and the 1968-2010 annual earnings career.

The same builder materializes the registered alternative population of
the A1 specification (section 14, row R6): the 2009 wave (income year
2008), weighted with the 2009 cross-sectional weight ER34046, opening at
the end of 2008 with the 1968-2008 career
(``Psid2010CohortSpec(anchor_wave=2009)``).  :data:`ANCHOR_LAYOUTS` holds
each wave's label-verified anchor variables; every wave-specific column
name carries its own year (``interview_2009``, ``age_2008``,
``ss_receipt_2008``, ...), and ``family_unit_id`` is the anchor wave's
interview number under either wave (the A1 section 16 half-split unit).
The Social Security reader resolves income years 2008, 2010 and 2012
only, so no 2009-wave recipient's first receipt can be bracketed: every
2008 recipient's receipt start is censored at 2008 (no earlier
observation), which A1 section 6 allows because the start is never
earlier than the observations allow.

Provenance: :func:`build_psid2010_cohort` records on the cohort where its
inputs came from (``Psid2010Cohort.provenance``, a read-only mapping), set
by the builder and not by the caller: ``psid_files`` only for inputs that
:func:`load_psid2010_inputs` returned and sealed (the SHA-256 of every
staged PSID file it read, and of its frames; a replaced or edited
``Psid2010Inputs`` loses the seal), ``invented`` for inputs whose frames
hash to the digest their provenance records (the A5 opening step then
re-generates the cohort from the invented generator's seed, which this
module cannot import), and ``caller_frames`` otherwise.  The provenance
also seals the built persons and careers (``content_sha256``), so a later
edit is detectable.

Every output of this module is a *PSID-seeded closed cohort*. It computes
no benefit, no reform and no comparison statistic.

Laws reused verbatim (not re-implemented):

* **Birth year** -- :func:`populace_dynamics.estimates.career.derive_birth_years`,
  the first-estimates section 3.1 precedence: marriage-history year, then
  ``median(period - age)`` over the earnings panel, then the seed
  coordinate ``(anchor_wave - 1) - age`` with the 2011 wave as anchor
  (``birth_year = 2010 - age``), else ``unresolved``.
* **Earnings career** -- :func:`populace_dynamics.estimates.career.build_career`
  with ``claim_year = 2010`` as the information-as-of cutoff: observed
  head/spouse labor income 1968-2010 from
  :func:`populace_dynamics.data.family.family_earnings_panel`, the biennial
  gap law (odd years 1997-2009 imputed from their neighbors), a career
  span from ``max(1968, birth_year + 22)`` through 2010 (earlier years are
  outside the career), and the per-year provenance enum.

One finding changes an input the plan assumed missing: the 2011 individual
file carries a person-level Social Security amount and self-reported
benefit type (G33A mention flags) for every member of a responding family,
heads and wives included (see
:mod:`populace_dynamics.data.social_security_income`). The plan's
age/M4/widowhood status rule stays the default; the reported type is the
registered alternative ``status_rule=reported_type``.

Rules whose choice is still open are explicit fields of
:class:`Psid2010CohortSpec`. The plan's proposal is each field's default;
where the plan is silent the default is a builder choice.
:func:`pending_decisions` lists every one of them with its alternatives.
"""

from __future__ import annotations

import contextlib
import contextvars
import copy
import hashlib
import json
import os
import re
import sys
from collections.abc import Iterator, Mapping
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from populace_dynamics import claiming
from populace_dynamics.data import (
    deaths,
    disability,
    family,
    marriage,
    psid,
)
from populace_dynamics.data import social_security_income as ssi
from populace_dynamics.engine.steps import ClaimingSchedule
from populace_dynamics.estimates import career

__all__ = [
    "ANCHOR_LAYOUTS",
    "ANCHOR_WAVE",
    "ANCHOR_WAVES",
    "CALLER_FRAMES",
    "INVENTED",
    "PSID_FILES",
    "START_YEAR",
    "DEFAULT_MAX_BIRTH_YEAR",
    "SS_YEARS",
    "M4_VERIFIED_WAVES",
    "COHORT_LABELS",
    "CLAIMING_REFERENCE_SHA256",
    "Presence",
    "OpeningStatus",
    "StatusRule",
    "Under62Precedence",
    "Under62Residual",
    "OfumSsSource",
    "BracketResolution",
    "AnchorWaveLayout",
    "Psid2010CohortSpec",
    "PendingDecision",
    "pending_decisions",
    "Psid2010Inputs",
    "Psid2010Cohort",
    "read_anchor_wave",
    "load_psid2010_inputs",
    "marital_state_at",
    "build_psid2010_cohort",
    "CLAIM_IMPUTATION_COLUMNS",
    "ReadOnlyProvenance",
    "cohort_content_sha256",
    "cohort_data_sha256",
    "input_frames_sha256",
    "record_files_read",
    "structural_summary",
]

#: The collection wave that defines presence by default (A1 section 14,
#: R0), and its income year.
ANCHOR_WAVE = 2011
START_YEAR = ANCHOR_WAVE - 1
#: Plan section 3: persons aged 50+ in 2030 were born 1980 or earlier.
DEFAULT_MAX_BIRTH_YEAR = 1980
#: Social Security income years observed around the start (biennial).
SS_YEARS: tuple[int, ...] = ssi.SS_INCOME_YEARS
#: Waves whose M4 employment-status value codes the loader verifies
#: (code 5 = disabled); ``Psid2010CohortSpec.m4_waves`` must lie in them.
M4_VERIFIED_WAVES: tuple[int, ...] = (2009, ANCHOR_WAVE)

#: The claim label every output of this module carries (plan section 4).
COHORT_LABELS: tuple[str, ...] = ("PSID-seeded closed cohort",)

#: The first-estimates section 6 claiming reference and its pinned sha256
#: (the same pin as ``scripts/registered_m6_inputs.py``).
_REPO_ROOT = Path(__file__).resolve().parents[3]
CLAIMING_REFERENCE_PATH = (
    _REPO_ROOT / "data" / "external" / "ssa_claim_ages_2014supplement.json"
)
CLAIMING_REFERENCE_SHA256 = (
    "b88e45a08909f0f88a0ff37074c757891759ec988fd7e9fe14362eebd0abe462"
)

_PERSON_VARS: dict[str, str] = {
    "ER30001": "1968 INTERVIEW NUMBER",
    "ER30002": "PERSON NUMBER 68",
}
_ANCHOR_ROLES = (
    "interview",
    "sequence",
    "relationship",
    "age",
    "reported_birth_year",
    "weight",
)


@dataclass(frozen=True)
class AnchorWaveLayout:
    """One anchor wave's label-verified individual-file variables.

    ``variables`` maps each role in ``("interview", "sequence",
    "relationship", "age", "reported_birth_year", "weight")`` to
    ``(variable, exact label)``.  The read verifies every label under
    whitespace normalization and requires the weight to be the only
    "CROSS-SECTION WT <yy>" label of the wave.
    """

    wave: int
    variables: Mapping[str, tuple[str, str]]

    @property
    def start_year(self) -> int:
        """The income year the wave observes (the opening year)."""
        return self.wave - 1

    @property
    def weight_variable(self) -> str:
        return self.variables["weight"][0]

    @property
    def family_unit_variable(self) -> str:
        return self.variables["interview"][0]

    @property
    def weight_concept(self) -> str:
        return rf"CROSS-SECTION WT\s+{self.wave % 100:02d}$"

    def labels(self) -> dict[str, str]:
        return {
            **_PERSON_VARS,
            **{var: label for var, label in self.variables.values()},
        }

    def columns(self) -> dict[str, str]:
        return {var: role for role, (var, _) in self.variables.items()}

    def as_dict(self) -> dict[str, Any]:
        return {
            "wave": self.wave,
            "start_year": self.start_year,
            "variables": {
                role: {"variable": var, "label": label}
                for role, (var, label) in self.variables.items()
            },
        }


#: The anchor waves the builder materializes, each with its exact labels,
#: verified against IND2023ER.sps before the read.  2011 (A1 R0): verified
#: 2026-09-22; ER34155 is "CORE/IMM INDIVIDUAL CROSS-SECTION WT 11" in both
#: IND2023ER.sas and IND2023ER.sps (codebook range 55-88,308, 0 = "not
#: response in 2011").  2009 (A1 R6): verified 2026-09-23 against
#: IND2023ER.sps and the IND2023ER codebook; ER34046 is "CORE/IMM
#: INDIVIDUAL CROSS-SECTION WT 09" (codebook range 55-68,935, 0 = "not
#: response in 2009"), ER34001 "2009 INTERVIEW NUMBER" (0 = main family
#: nonresponse), ER34006 codes 9,999 as NA and 0 as Inap., as ER34106 does.
ANCHOR_LAYOUTS: dict[int, AnchorWaveLayout] = {
    2011: AnchorWaveLayout(
        wave=2011,
        variables={
            "interview": ("ER34101", "2011 INTERVIEW NUMBER"),
            "sequence": ("ER34102", "SEQUENCE NUMBER 11"),
            "relationship": ("ER34103", "RELATION TO HEAD 11"),
            "age": ("ER34104", "AGE OF INDIVIDUAL 11"),
            "reported_birth_year": ("ER34106", "YEAR INDIVIDUAL BORN 11"),
            "weight": ("ER34155", "CORE/IMM INDIVIDUAL CROSS-SECTION WT 11"),
        },
    ),
    2009: AnchorWaveLayout(
        wave=2009,
        variables={
            "interview": ("ER34001", "2009 INTERVIEW NUMBER"),
            "sequence": ("ER34002", "SEQUENCE NUMBER 09"),
            "relationship": ("ER34003", "RELATION TO HEAD 09"),
            "age": ("ER34004", "AGE OF INDIVIDUAL 09"),
            "reported_birth_year": ("ER34006", "YEAR INDIVIDUAL BORN 09"),
            "weight": ("ER34046", "CORE/IMM INDIVIDUAL CROSS-SECTION WT 09"),
        },
    ),
}
#: The waves above, default first.
ANCHOR_WAVES: tuple[int, ...] = tuple(ANCHOR_LAYOUTS)
_REPORTED_BIRTH_YEAR_NA = 9999

#: Relationship codes (two-digit era; the 2009 and 2011 formats of
#: ER34003/ER34103 agree): 10 head, 20 legal wife, 22 cohabiting partner
#: ("wife").
_HEAD = 10
_LEGAL_SPOUSE = 20
_PARTNER = 22

_SEQUENCE_IN_FAMILY = (1, 20)
_SEQUENCE_INSTITUTION = (51, 59)
#: Sequence groups (IND2023ER formats ER34002F and ER34102F: 71-80 moved
#: out, 81-89 died, since the previous wave's interview, named by that
#: wave) for the accounting of positive-weight persons outside the
#: presence universe.
_SEQUENCE_GROUPS: tuple[tuple[str, int, int], ...] = (
    ("in_family", 1, 20),
    ("institution", 51, 59),
    ("moved_out_since_{previous}", 71, 80),
    ("died_since_{previous}", 81, 89),
)

#: ``Psid2010Cohort.provenance`` kinds, set by the builder.
PSID_FILES = "psid_files"
INVENTED = "invented"
CALLER_FRAMES = "caller_frames"

_RNG_NAMESPACE = "psid2010_cohort.opening_stock.person.v1"

#: 2010-age bands for the structural SS-receipt counts.
_SUMMARY_AGE_BANDS: tuple[tuple[int, int | None], ...] = (
    (30, 49),
    (50, 61),
    (62, 64),
    (65, 69),
    (70, 79),
    (80, None),
)


class Presence(str, Enum):
    """Which 2011 sequence numbers count as "observed in the 2011 wave"."""

    IN_FAMILY = "in_family"
    IN_FAMILY_OR_INSTITUTION = "in_family_or_institution"


class OpeningStatus(str, Enum):
    """Opening-stock Social Security status at the end of 2010."""

    NONE = "none"
    RETIRED_WORKER = "retired_worker"
    DISABLED_WORKER = "disabled_worker"
    SURVIVOR = "survivor"
    SPOUSE = "spouse"
    OTHER = "other"
    UNCLASSIFIED = "unclassified"
    UNOBSERVED = "unobserved"


class StatusRule(str, Enum):
    """How a 2010 Social Security recipient's status is assigned."""

    #: Plan A3: 62+ -> retired or survivor; under 62 -> DI or survivor,
    #: by a frozen rule using M4 status and widowhood.
    PLAN_AGE_M4_WIDOWHOOD = "plan_age_m4_widowhood"
    #: The PSID 2011 self-reported type (G33A mention flags), falling back
    #: to the plan rule when the person reported no type.
    REPORTED_TYPE = "reported_type"


class Under62Precedence(str, Enum):
    """Order of the two under-62 clauses of the plan rule."""

    M4_THEN_WIDOWHOOD = "m4_then_widowhood"
    WIDOWHOOD_THEN_M4 = "widowhood_then_m4"


class Under62Residual(str, Enum):
    """Status of an under-62 recipient neither M4-disabled nor widowed."""

    DISABLED_WORKER = "disabled_worker"
    UNCLASSIFIED = "unclassified"


class OfumSsSource(str, Enum):
    """Person-level amount for recipients who are not head or wife.

    The family files carry only a family-unit total for other family-unit
    members (OFUMs), so a person-level OFUM amount comes from the
    individual file or is unobserved.
    """

    INDIVIDUAL_FILE = "individual_file"
    UNOBSERVED = "unobserved"


class BracketResolution(str, Enum):
    """Claim year when receipt is bracketed (none in 2008, some in 2010)."""

    #: Plan A3 "opening claim year from observed first SS receipt": the
    #: first income year in which receipt is observed.
    FIRST_OBSERVED = "first_observed"
    #: Use the family's R20 item about 2009 (asked in 2011): "no" -> 2010,
    #: "yes" -> 2009 (the R20 item is family-level, so a "yes" may be
    #: another member's receipt), DK/NA -> 2010.
    FU_PRIOR_YEAR_INDICATOR = "fu_prior_year_indicator"


_REPORTED_TYPE_STATUS: dict[str, OpeningStatus] = {
    "disability": OpeningStatus.DISABLED_WORKER,
    "survivor": OpeningStatus.SURVIVOR,
    "retirement": OpeningStatus.RETIRED_WORKER,
    "dependent_of_disabled": OpeningStatus.SPOUSE,
    "dependent_of_retired": OpeningStatus.SPOUSE,
    "other": OpeningStatus.OTHER,
}


@dataclass(frozen=True)
class Psid2010CohortSpec:
    """Every open choice of the builder, defaulting to the plan's proposal.

    See :func:`pending_decisions` for each field's alternatives and whether
    its default is the plan's proposal or a builder choice.  ``m4_waves``
    defaults to the anchor wave alone.
    """

    anchor_wave: int = ANCHOR_WAVE
    presence: Presence = Presence.IN_FAMILY
    max_birth_year: int = DEFAULT_MAX_BIRTH_YEAR
    retirement_age: int = 62
    status_rule: StatusRule = StatusRule.PLAN_AGE_M4_WIDOWHOOD
    under_62_precedence: Under62Precedence = (
        Under62Precedence.M4_THEN_WIDOWHOOD
    )
    under_62_residual: Under62Residual = Under62Residual.DISABLED_WORKER
    aged_m4_disabled_di_below_age: int | None = None
    m4_waves: tuple[int, ...] | None = None
    reported_type_precedence: tuple[str, ...] = (
        "disability",
        "survivor",
        "retirement",
        "dependent_of_disabled",
        "dependent_of_retired",
        "other",
    )
    ofum_ss_source: OfumSsSource = OfumSsSource.INDIVIDUAL_FILE
    bracket_resolution: BracketResolution = BracketResolution.FIRST_OBSERVED
    claim_table_max_year: int = 2008
    stock_imputation_root_seed: int = 2010
    separated_is_married: bool = True

    def __post_init__(self) -> None:
        if self.anchor_wave not in ANCHOR_LAYOUTS:
            raise ValueError(
                f"anchor_wave must be one of {sorted(ANCHOR_LAYOUTS)}"
            )
        if self.m4_waves is None:
            object.__setattr__(self, "m4_waves", (int(self.anchor_wave),))
        object.__setattr__(self, "presence", Presence(self.presence))
        object.__setattr__(self, "status_rule", StatusRule(self.status_rule))
        object.__setattr__(
            self,
            "under_62_precedence",
            Under62Precedence(self.under_62_precedence),
        )
        object.__setattr__(
            self, "under_62_residual", Under62Residual(self.under_62_residual)
        )
        object.__setattr__(
            self, "ofum_ss_source", OfumSsSource(self.ofum_ss_source)
        )
        object.__setattr__(
            self,
            "bracket_resolution",
            BracketResolution(self.bracket_resolution),
        )
        object.__setattr__(
            self, "m4_waves", tuple(int(w) for w in self.m4_waves)
        )
        object.__setattr__(
            self,
            "reported_type_precedence",
            tuple(self.reported_type_precedence),
        )
        if sorted(self.reported_type_precedence) != sorted(ssi.SS_TYPES):
            raise ValueError(
                "reported_type_precedence must order exactly "
                f"{sorted(ssi.SS_TYPES)}"
            )
        if not self.m4_waves:
            raise ValueError("m4_waves must name at least one wave")
        if not set(self.m4_waves) <= set(M4_VERIFIED_WAVES):
            raise ValueError(
                f"m4_waves must lie in the code-verified waves "
                f"{M4_VERIFIED_WAVES}"
            )
        if max(self.m4_waves) > self.anchor_wave:
            raise ValueError(
                "m4_waves may not follow the anchor wave (the opening "
                "state's information date)"
            )
        if self.max_birth_year > self.start_year:
            raise ValueError("max_birth_year may not follow the start year")
        if self.claim_table_max_year > self.start_year:
            raise ValueError(
                f"claim_table_max_year may not follow {self.start_year}"
            )
        if self.stock_imputation_root_seed < 0:
            raise ValueError("stock_imputation_root_seed must be >= 0")
        if (
            self.aged_m4_disabled_di_below_age is not None
            and self.aged_m4_disabled_di_below_age <= self.retirement_age
        ):
            raise ValueError(
                "aged_m4_disabled_di_below_age must exceed retirement_age"
            )

    @property
    def start_year(self) -> int:
        """The opening year: the anchor wave's income year."""
        return int(self.anchor_wave) - 1

    @property
    def layout(self) -> AnchorWaveLayout:
        return ANCHOR_LAYOUTS[self.anchor_wave]

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        for key, value in out.items():
            if isinstance(value, Enum):
                out[key] = value.value
            elif isinstance(value, tuple):
                out[key] = list(value)
        return out


@dataclass(frozen=True)
class PendingDecision:
    """One open choice: its default, alternatives, basis and owner."""

    field: str
    default: Any
    alternatives: tuple[Any, ...]
    default_basis: str
    awaiting: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "default": self.default,
            "alternatives": list(self.alternatives),
            "default_basis": self.default_basis,
            "awaiting": self.awaiting,
        }


_PLAN = "plan proposal (critical-path-cola-20260922.md)"
_BUILDER = "builder choice; the plan is silent"
_MAX = (
    "A1 specification freeze (Max's ratification; his 2026-09-23 rulings "
    "did not cover this choice)"
)


def pending_decisions() -> tuple[PendingDecision, ...]:
    """Every open choice of :class:`Psid2010CohortSpec`, with its default.

    One entry per spec field, plus the loader's ``birth_inference_max_wave``
    argument. ``default_basis`` says whether the default is the plan's
    proposal or a builder choice where the plan says nothing. None of these
    is ratified.
    """

    spec = Psid2010CohortSpec()
    return (
        PendingDecision(
            "anchor_wave",
            spec.anchor_wave,
            (2009,),
            "A1 specification section 14: the 2011 wave (ER34155, ER34101) "
            "is the primary population R0; the 2009 wave (ER34046, "
            "ER34001; opening year 2008) is the registered alternative R6. "
            "Every spec field below keeps its meaning under either wave",
            _MAX,
        ),
        PendingDecision(
            "presence",
            spec.presence.value,
            (Presence.IN_FAMILY_OR_INSTITUTION.value,),
            f"{_BUILDER}: the plan says 'observed in the 2011 wave'; the "
            "default is the repository's presence notion (sequence 1-20), "
            "the only persons whose 2010 Social Security is asked. ER34155 "
            "is also positive for 2011 movers-out (sequence 71-80) and for "
            "persons who died before the 2011 interview (81-89); neither "
            "option admits them, and the diagnostic "
            "positive_weight_outside_presence counts their weight",
            _MAX,
        ),
        PendingDecision(
            "max_birth_year",
            spec.max_birth_year,
            (),
            f"{_PLAN} section 3",
            _MAX,
        ),
        PendingDecision(
            "retirement_age",
            spec.retirement_age,
            (),
            f"{_PLAN} A3 ('62+ with SS'), the early-eligibility age",
            _MAX,
        ),
        PendingDecision(
            "status_rule",
            spec.status_rule.value,
            (StatusRule.REPORTED_TYPE.value,),
            f"{_PLAN} A3 (62+ -> retired or survivor; under 62 -> DI or "
            "survivor using M4 status and widowhood); the plan lists the "
            "type as unobserved after searching the family file, but the "
            "2011 individual file carries self-reported type flags "
            "(ER34137-ER34142), offered as the alternative",
            _MAX,
        ),
        PendingDecision(
            "under_62_precedence",
            spec.under_62_precedence.value,
            (Under62Precedence.WIDOWHOOD_THEN_M4.value,),
            f"{_BUILDER}: the plan names both inputs but no order",
            _MAX,
        ),
        PendingDecision(
            "under_62_residual",
            spec.under_62_residual.value,
            (Under62Residual.UNCLASSIFIED.value,),
            f"{_PLAN} A3 allows only DI or survivor under 62, so a "
            "recipient neither M4-disabled nor widowed defaults to DI",
            _MAX,
        ),
        PendingDecision(
            "aged_m4_disabled_di_below_age",
            spec.aged_m4_disabled_di_below_age,
            (66,),
            f"{_PLAN} A3: every 62+ recipient is retired or survivor "
            "(DI beneficiaries aged 62 to FRA are therefore classed retired)",
            _MAX,
        ),
        PendingDecision(
            "m4_waves",
            list(spec.m4_waves),
            ([2009, 2011], [2009]),
            f"{_BUILDER}: the M4 self-report nearest the start (the anchor "
            "wave, so [2009] under anchor_wave 2009); a member with no "
            "ascertained status in any consulted wave counts as not "
            "M4-disabled (flagged m4_status_unknown); no wave after the "
            "anchor wave",
            _MAX,
        ),
        PendingDecision(
            "reported_type_precedence",
            list(spec.reported_type_precedence),
            (),
            f"{_BUILDER}: used only under status_rule=reported_type, for "
            "multiple mentions",
            _MAX,
        ),
        PendingDecision(
            "ofum_ss_source",
            spec.ofum_ss_source.value,
            (OfumSsSource.UNOBSERVED.value,),
            f"{_BUILDER}: the plan's reader covers head and wife; for other "
            "members the individual-file amount is used (it matches the "
            "family head/wife amounts to within $12 on the staged data)",
            _MAX,
        ),
        PendingDecision(
            "bracket_resolution",
            spec.bracket_resolution.value,
            (BracketResolution.FU_PRIOR_YEAR_INDICATOR.value,),
            f"{_PLAN} A3 'opening claim year from observed first SS "
            "receipt'",
            _MAX,
        ),
        PendingDecision(
            "claim_table_max_year",
            spec.claim_table_max_year,
            (),
            f"{_PLAN} A3 (section 6 law restricted to table rows <=2008); "
            "the rows come from the 2014 Supplement, a later publication",
            _MAX,
        ),
        PendingDecision(
            "stock_imputation_root_seed",
            spec.stock_imputation_root_seed,
            (),
            f"{_BUILDER}: unregistered; must be fixed at registration",
            "registration (A9)",
        ),
        PendingDecision(
            "separated_is_married",
            spec.separated_is_married,
            (False,),
            f"{_BUILDER}: a separated person is still legally married",
            _MAX,
        ),
        PendingDecision(
            "birth_inference_max_wave",
            None,
            (ANCHOR_WAVE,),
            f"{_BUILDER}: loader argument; None uses every staged earnings "
            "wave for birth-year clause 2, as the first-estimates run did",
            _MAX,
        ),
    )


@dataclass(frozen=True)
class Psid2010Inputs:
    """Materialized reader outputs the pure builder consumes.

    Shapes: ``anchor`` is :func:`read_anchor_wave`; ``death_records`` is
    :func:`populace_dynamics.data.deaths.read_death_records`;
    ``marriage_history`` is
    :func:`populace_dynamics.data.marriage.marriage_history`;
    ``observed_earnings`` is
    :func:`populace_dynamics.data.family.family_earnings_panel`;
    ``head_spouse_ss`` is
    :func:`populace_dynamics.data.social_security_income.head_spouse_social_security_panel`;
    ``individual_ss`` is
    :func:`populace_dynamics.data.social_security_income.read_individual_social_security`;
    ``disability_status`` is
    :func:`populace_dynamics.data.disability.read_disability_status`;
    ``claiming_pmf`` maps ``(sex, entitlement_year)`` to a claim-age PMF.
    """

    anchor: pd.DataFrame
    death_records: pd.DataFrame
    marriage_history: pd.DataFrame
    observed_earnings: pd.DataFrame
    head_spouse_ss: pd.DataFrame
    individual_ss: pd.DataFrame
    disability_status: pd.DataFrame
    claiming_pmf: Mapping[tuple[str, int], Mapping[int, float]]
    provenance: Mapping[str, Any] = field(default_factory=dict)
    #: The wave ``anchor`` was read from; must equal the spec's.
    anchor_wave: int = ANCHOR_WAVE
    #: Set by :func:`load_psid2010_inputs` only (not a constructor
    #: argument; ``dataclasses.replace`` clears it): the digest of the
    #: frames and of the PSID file hashes it read.  The builder records a
    #: ``psid_files`` provenance only for inputs that still match it.
    loader_seal: Mapping[str, str] | None = field(
        default=None, init=False, repr=False, compare=False
    )


class ReadOnlyProvenance(Mapping[str, Any]):
    """A read-only provenance record.

    It has no mutating methods, and every value is returned as a deep
    copy, so neither the record nor a nested mapping can be edited in
    place; ``dict(record)`` is a plain, JSON-serializable copy.
    """

    def __init__(self, values: Mapping[str, Any]) -> None:
        self._values = copy.deepcopy(
            {str(key): value for key, value in dict(values).items()}
        )

    def __getitem__(self, key: str) -> Any:
        return copy.deepcopy(self._values[key])

    def __iter__(self) -> Iterator[str]:
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)

    def __repr__(self) -> str:
        return f"ReadOnlyProvenance({self._values!r})"


def _unsealed_provenance() -> ReadOnlyProvenance:
    return ReadOnlyProvenance(
        {
            "kind": "unsealed",
            "note": (
                "not set by build_psid2010_cohort (a directly constructed "
                "or replaced cohort)"
            ),
        }
    )


@dataclass(frozen=True)
class Psid2010Cohort:
    """The built cohort.

    Attributes:
        persons: One row per member (see :func:`build_psid2010_cohort`).
        careers: Long 1968-2010 career rows (``person_id``, ``year``,
            ``earnings``, ``provenance``) under the first-estimates laws.
        social_security: Long person x income-year rows for 2008, 2010 and
            2012 with the amount, its source and the reported type.
        dispositions: One row per person in the 2011 presence universe with
            ``weight`` and ``disposition`` (``member`` or the single reason).
        spec: The :class:`Psid2010CohortSpec` used.
        diagnostics: Structural cross-checks computed during the build.
        provenance: Where the inputs came from, set by
            :func:`build_psid2010_cohort` only (it is not a constructor
            argument, and ``dataclasses.replace`` resets it to
            ``unsealed``): ``kind`` is :data:`PSID_FILES`,
            :data:`INVENTED` or :data:`CALLER_FRAMES`, and
            ``content_sha256`` seals the built persons and careers.  A
            :class:`ReadOnlyProvenance`: it cannot be edited in place.
    """

    persons: pd.DataFrame
    careers: pd.DataFrame
    social_security: pd.DataFrame
    dispositions: pd.DataFrame
    spec: Psid2010CohortSpec
    diagnostics: Mapping[str, Any]
    labels: tuple[str, ...] = COHORT_LABELS
    provenance: Mapping[str, Any] = field(
        default_factory=_unsealed_provenance, init=False
    )

    @property
    def anchor_wave(self) -> int:
        return int(self.spec.anchor_wave)

    @property
    def start_year(self) -> int:
        return self.spec.start_year


# --------------------------------------------------------------------------
# Readers
# --------------------------------------------------------------------------
def read_anchor_wave(
    *,
    data_dir: Path | None = None,
    nrows: int | None = None,
    anchor_wave: int = ANCHOR_WAVE,
) -> pd.DataFrame:
    """Read the label-verified anchor-wave row for every person.

    Columns: ``person_id`` (``ER30001 * 1000 + ER30002``), ``interview``,
    ``sequence``, ``relationship``, ``age`` (raw PSID code), and
    ``reported_birth_year`` (a diagnostic only, never used by the
    birth-year law; ``<NA>`` for code 9999 or 0) and ``weight``, from the
    wave's :data:`ANCHOR_LAYOUTS` variables (2011: ER34101-ER34106 and
    ER34155; 2009: ER34001-ER34006 and ER34046).  The weight must be the
    only "CROSS-SECTION WT <yy>" label of the wave.
    """

    if anchor_wave not in ANCHOR_LAYOUTS:
        raise ValueError(
            f"anchor_wave must be one of {sorted(ANCHOR_LAYOUTS)}"
        )
    layout = ANCHOR_LAYOUTS[anchor_wave]
    labels = psid.parse_sps_labels(
        psid.product_sps_path("ind2023er", data_dir)
    )
    expected = layout.labels()
    psid.verify_labels(
        labels, expected, context=f"ind2023er {anchor_wave} anchor"
    )
    weight_hits = sorted(
        name
        for name, label in labels.items()
        if re.search(layout.weight_concept, " ".join(label.split()))
    )
    if weight_hits != [layout.weight_variable]:
        raise ValueError(
            f"{anchor_wave} cross-section weight concept matched "
            f"{weight_hits}; expected only {layout.weight_variable}"
        )
    raw = psid.read_psid(
        "ind2023er",
        columns=list(expected),
        data_dir=data_dir,
        nrows=nrows,
    )
    frame = pd.DataFrame(
        {
            "person_id": raw["ER30001"].astype("int64") * 1000
            + raw["ER30002"].astype("int64")
        }
    )
    for var, column in layout.columns().items():
        frame[column] = raw[var]
    frame = frame[["person_id", *_ANCHOR_ROLES]]
    for column in ("interview", "sequence", "relationship", "age"):
        frame[column] = frame[column].astype("int64")
    frame["weight"] = frame["weight"].astype("float64")
    if (frame["weight"] < 0).any():
        raise ValueError(f"negative {anchor_wave} cross-sectional weight")
    reported = frame["reported_birth_year"].astype("Int64")
    frame["reported_birth_year"] = reported.mask(
        reported.isin([_REPORTED_BIRTH_YEAR_NA, 0])
    )
    if frame["person_id"].duplicated().any():
        raise ValueError("duplicate person_id in the individual file")
    return frame


def _load_claiming_pmf(
    path: Path,
) -> tuple[dict[tuple[str, int], dict[int, float]], str]:
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    if digest != CLAIMING_REFERENCE_SHA256:
        raise ValueError(
            f"claiming reference {path} sha256 {digest} != pinned "
            f"{CLAIMING_REFERENCE_SHA256}"
        )
    reference = claiming.load_claim_age_reference(path)
    pmf = {
        (sex, year): claiming.claim_age_pmf(
            sex, year, exclude_conversions=True, reference=reference
        )
        for sex in ("female", "male")
        for year in reference.years()
    }
    return pmf, digest


_FILES_READ: contextvars.ContextVar[set[str] | None] = contextvars.ContextVar(
    "psid2010_files_read", default=None
)
_AUDIT_HOOK_INSTALLED = False
_HASH_CHUNK = 1 << 20


def _audit_open(event: str, args: tuple) -> None:
    """Record the paths opened while :func:`record_files_read` is active.

    An audit hook must never raise (it would break the ``open`` it
    observes), so every failure is ignored.
    """

    if event != "open":
        return
    try:
        sink = _FILES_READ.get()
        if sink is None or not args or isinstance(args[0], int):
            return
        sink.add(os.fsdecode(os.fspath(args[0])))
    except Exception:  # noqa: BLE001 - see the docstring
        return


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(_HASH_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


@contextlib.contextmanager
def record_files_read(root: Path) -> Iterator[dict[str, str]]:
    """Record the SHA-256 of every file under ``root`` opened in the block.

    Uses a Python audit hook (``sys.addaudithook``, installed once per
    process) on the ``open`` event, which ``open``, ``Path.read_text`` and
    pandas' readers raise.  On a normal exit the yielded mapping is filled
    with ``{path relative to root: sha256}`` for each regular file under
    ``root`` that was opened; files outside ``root`` are ignored.
    """

    global _AUDIT_HOOK_INSTALLED
    if not _AUDIT_HOOK_INSTALLED:
        sys.addaudithook(_audit_open)
        _AUDIT_HOOK_INSTALLED = True
    literal_root = Path(os.path.abspath(Path(root).expanduser()))
    resolved_root = literal_root.resolve()
    sink: set[str] = set()
    token = _FILES_READ.set(sink)
    record: dict[str, str] = {}
    try:
        yield record
    finally:
        _FILES_READ.reset(token)
    for name in sorted(sink):
        literal = Path(os.path.abspath(Path(name).expanduser()))
        if not literal.is_file():
            continue
        # A file is under the root by its path as opened or, when the root
        # or the file sits behind a symbolic link, by its resolved path.
        if literal.is_relative_to(literal_root):
            relative = literal.relative_to(literal_root)
        elif literal.resolve().is_relative_to(resolved_root):
            relative = literal.resolve().relative_to(resolved_root)
        else:
            continue
        record[str(relative)] = _sha256_file(literal)


def _mapping_sha256(values: Mapping[str, str]) -> str:
    encoded = (
        json.dumps(dict(values), sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def load_psid2010_inputs(
    *,
    data_dir: Path | None = None,
    birth_inference_max_wave: int | None = None,
    claiming_reference_path: Path | None = None,
    anchor_wave: int = ANCHOR_WAVE,
) -> Psid2010Inputs:
    """Read every input from the staged PSID and the committed claim table.

    ``anchor_wave`` is the wave that defines presence (2011, or 2009 for
    the A1 R6 population).  ``birth_inference_max_wave`` caps the family
    earnings waves read (and so the waves birth-year clause 2 may use);
    ``None`` reads every staged wave. Careers use income years through the
    opening year whatever the cap, so the cap may not precede the anchor
    wave.  M4 status is read through the anchor wave only.

    The provenance is ``kind="psid_files"`` with the SHA-256 of every file
    under the PSID data directory that the readers opened
    (:func:`record_files_read`) and the bundle hash of that mapping.  The
    returned inputs carry the loader's seal (``loader_seal``: the digest of
    the frames and of those file hashes), without which the builder
    refuses a ``psid_files`` claim.
    """

    if anchor_wave not in ANCHOR_LAYOUTS:
        raise ValueError(
            f"anchor_wave must be one of {sorted(ANCHOR_LAYOUTS)}"
        )
    waves = family.FAMILY_WAVES
    if birth_inference_max_wave is not None:
        if int(birth_inference_max_wave) < anchor_wave:
            raise ValueError(
                f"birth_inference_max_wave may not precede the "
                f"{anchor_wave} wave"
            )
        waves = tuple(
            wave for wave in waves if wave <= int(birth_inference_max_wave)
        )
    reference_path = (
        CLAIMING_REFERENCE_PATH
        if claiming_reference_path is None
        else Path(claiming_reference_path)
    )
    claiming_pmf, digest = _load_claiming_pmf(reference_path)
    data_root = psid._resolve_data_dir(data_dir)
    with record_files_read(data_root) as files:
        status_codes = disability.verify_employment_status_codes(
            data_dir=data_dir, waves=list(M4_VERIFIED_WAVES)
        )
        frames = {
            "anchor": read_anchor_wave(
                data_dir=data_dir, anchor_wave=anchor_wave
            ),
            "death_records": deaths.read_death_records(data_dir=data_dir),
            "marriage_history": marriage.marriage_history(data_dir=data_dir),
            "observed_earnings": family.family_earnings_panel(
                waves=waves, data_dir=data_dir
            ),
            "head_spouse_ss": ssi.head_spouse_social_security_panel(
                data_dir=data_dir
            ),
            "individual_ss": ssi.read_individual_social_security(
                data_dir=data_dir
            ),
            "disability_status": disability.read_disability_status(
                data_dir=data_dir, max_period=anchor_wave
            ),
        }
    if not files:
        raise RuntimeError(
            f"no PSID file under {data_root} was recorded as read; the "
            "provenance of these inputs cannot be established"
        )
    inputs = Psid2010Inputs(
        **frames,
        claiming_pmf=claiming_pmf,
        anchor_wave=anchor_wave,
        provenance={
            "kind": PSID_FILES,
            "anchor_wave": anchor_wave,
            "psid_data_dir": str(data_root),
            "psid_files_sha256": dict(files),
            "psid_files_bundle_sha256": _mapping_sha256(files),
            "psid_files_bundle_basis": (
                "sha256 of canonical JSON {path relative to the PSID data "
                "directory: raw sha256} (sorted keys, compact separators, "
                "trailing newline)"
            ),
            "earnings_waves": [int(waves[0]), int(waves[-1])],
            "claiming_reference": str(reference_path),
            "claiming_reference_sha256": digest,
            "employment_status_formats": {
                str(wave): value["format"]
                for wave, value in status_codes.items()
            },
        },
    )
    return _seal_loaded_inputs(inputs)


def _loader_seal(inputs: Psid2010Inputs) -> dict[str, str]:
    files = dict(inputs.provenance or {}).get("psid_files_sha256")
    if not isinstance(files, Mapping) or not files:
        raise ValueError("inputs record no PSID file")
    return {
        "input_frames_sha256": input_frames_sha256(inputs),
        "psid_files_bundle_sha256": _mapping_sha256(dict(files)),
    }


def _seal_loaded_inputs(inputs: Psid2010Inputs) -> Psid2010Inputs:
    """Mark ``inputs`` as returned by :func:`load_psid2010_inputs`.

    Only the loader calls this (tests call it to stand in for the loader
    on invented frames).  The seal is the digest of the frames and of the
    recorded PSID file hashes at load time.
    """

    object.__setattr__(inputs, "loader_seal", _loader_seal(inputs))
    return inputs


# --------------------------------------------------------------------------
# Marital state at a year
# --------------------------------------------------------------------------
def marital_state_at(
    episodes: pd.DataFrame,
    year: int,
    *,
    separated_is_married: bool = True,
) -> dict[str, Any]:
    """Marital state at the end of ``year`` from one person's episodes.

    ``episodes`` is one person's
    :func:`populace_dynamics.data.marriage.marriage_episodes` rows,
    optionally with the marriage-history ``separation_year`` (MH16, the
    year the spouses stopped living together) alongside. A marriage is
    dated when its start year is known and, if it has ended, its end (or
    separation) year is known. The precedence is:

    1. any dated marriage in force at the end of ``year`` -> ``married``
       (the latest start wins; ``multiple_in_force`` flags more than one
       marriage in force); a marriage whose spouses had separated by
       ``year`` -- one still recorded as separated, or one that ended in
       divorce or widowhood only after ``year`` but whose
       ``separation_year`` is at or before it -- counts as in force
       (flagged ``separated``) when ``separated_is_married``, else it is
       a ``separated`` dissolution dated at the separation year;
    2. otherwise any undated episode (unknown start, unknown end, or the
       file's ``other``/``unknown`` statuses) -> ``unknown``;
    3. otherwise the latest dated dissolution -> ``widowed``,
       ``divorced`` or ``separated``;
    4. otherwise ``never_married``.

    Returns ``status``, ``spouse_person_id`` (current spouse, NA unless a
    joinable PSID person), ``separated``, ``multiple_in_force``,
    ``dissolution_year`` and ``former_spouse_person_id`` (for widowed,
    divorced or separated states).
    """

    year = int(year)
    has_separation = "separation_year" in episodes.columns
    in_force: list[tuple[int, int, Any, bool]] = []
    dissolved: list[tuple[int, int, str, Any]] = []
    undated = False
    for row in episodes.itertuples(index=False):
        order = -1 if pd.isna(row.marriage_order) else int(row.marriage_order)
        if pd.isna(row.start_year):
            undated = True
            continue
        start = int(row.start_year)
        if start > year:
            continue
        how = str(row.how_ended)
        end = row.episode_end_year
        spouse = row.spouse_person_id
        separation = row.separation_year if has_separation else pd.NA
        separated_by_year = not pd.isna(separation) and int(separation) <= year
        if how == "intact":
            in_force.append((start, order, spouse, False))
        elif how in ("widowhood", "divorce", "separated"):
            if pd.isna(end):
                undated = True
            elif int(end) > year:
                # Legally in force at the end of ``year``; the spouses may
                # already have separated (MH16) before a later divorce.
                if not separated_by_year:
                    in_force.append((start, order, spouse, False))
                elif separated_is_married:
                    in_force.append((start, order, spouse, True))
                else:
                    dissolved.append(
                        (int(separation), order, "separated", spouse)
                    )
            elif how == "separated" and separated_is_married:
                in_force.append((start, order, spouse, True))
            else:
                dissolved.append((int(end), order, how, spouse))
        else:
            undated = True
    out: dict[str, Any] = {
        "status": "never_married",
        "spouse_person_id": pd.NA,
        "separated": False,
        "multiple_in_force": False,
        "dissolution_year": pd.NA,
        "former_spouse_person_id": pd.NA,
    }
    if in_force:
        in_force.sort(key=lambda item: (item[0], item[1]))
        start, _, spouse, separated = in_force[-1]
        out.update(
            status="married",
            spouse_person_id=spouse,
            separated=separated,
            multiple_in_force=len(in_force) > 1,
        )
        return out
    if undated:
        out["status"] = "unknown"
        return out
    if dissolved:
        dissolved.sort(key=lambda item: (item[0], item[1]))
        end, _, how, spouse = dissolved[-1]
        status = {
            "widowhood": "widowed",
            "divorce": "divorced",
            "separated": "separated",
        }[how]
        out.update(
            status=status,
            dissolution_year=end,
            former_spouse_person_id=spouse,
        )
    return out


# --------------------------------------------------------------------------
# Builder helpers
# --------------------------------------------------------------------------
_REQUIRED_COLUMNS: dict[str, frozenset[str]] = {
    "anchor": frozenset(
        {
            "person_id",
            "interview",
            "sequence",
            "relationship",
            "age",
            "reported_birth_year",
            "weight",
        }
    ),
    "death_records": frozenset({"person_id", "sex"}),
    "marriage_history": frozenset(
        {
            "person_id",
            "birth_year",
            "is_marriage",
            "marriage_order",
            "spouse_person_id",
            "start_year",
            "start_month",
            "end_year",
            "separation_year",
            "how_ended",
            "last_known_status",
        }
    ),
    "observed_earnings": frozenset({"person_id", "period", "earnings", "age"}),
    "head_spouse_ss": frozenset(
        {
            "person_id",
            "wave",
            "role",
            "ss_amount",
            "ss_acc",
            "fu_ss_prior_year",
            "interview",
        }
    ),
    "individual_ss": frozenset(
        {"person_id", "wave", "ss_amount", "ss_acc", "type_combination"}
        | {f"type_{name}" for name in ssi.SS_TYPES}
    ),
    "disability_status": frozenset({"person_id", "period", "disabled"}),
}

_TYPE_COLUMNS: tuple[str, ...] = tuple(f"type_{name}" for name in ssi.SS_TYPES)


def _validate_inputs(inputs: Psid2010Inputs) -> None:
    for name, columns in _REQUIRED_COLUMNS.items():
        frame = getattr(inputs, name)
        missing = set(columns) - set(frame.columns)
        if missing:
            raise ValueError(f"{name} is missing columns {sorted(missing)}")
    for name in ("anchor", "death_records"):
        if getattr(inputs, name)["person_id"].duplicated().any():
            raise ValueError(f"{name} contains duplicate person_id")
    for name, key in (
        ("head_spouse_ss", ["person_id", "wave"]),
        ("individual_ss", ["person_id", "wave"]),
        ("disability_status", ["person_id", "period"]),
    ):
        if getattr(inputs, name).duplicated(key).any():
            raise ValueError(f"{name} contains duplicate {key} rows")


def _presence_mask(anchor: pd.DataFrame, presence: Presence) -> pd.Series:
    low, high = _SEQUENCE_IN_FAMILY
    mask = anchor["sequence"].between(low, high)
    if presence is Presence.IN_FAMILY_OR_INSTITUTION:
        low, high = _SEQUENCE_INSTITUTION
        mask |= anchor["sequence"].between(low, high)
    return mask & (anchor["weight"] > 0)


def _person_rng(root_seed: int, person_id: int) -> np.random.Generator:
    identity = f"{_RNG_NAMESPACE}|{int(person_id)}".encode()
    words = np.frombuffer(hashlib.sha256(identity).digest(), dtype="<u4")
    sequence = np.random.SeedSequence([int(root_seed), *map(int, words)])
    return np.random.default_rng(sequence)


def _impute_claim_age(
    *,
    person_id: int,
    birth_year: int,
    sex: str,
    latest_claim_year: int,
    schedule: ClaimingSchedule,
    root_seed: int,
) -> tuple[int | None, int, str | None]:
    """The section 6 opening-stock draw, bounded by the latest claim year.

    Draws from the engine's nearest-year snapped PMF keyed by ``birth + 62``
    (:meth:`populace_dynamics.engine.steps.ClaimingSchedule.distribution`),
    truncated to claim ages whose claim year is at or before
    ``latest_claim_year`` and renormalized, with a person-keyed RNG in this
    module's own namespace. Returns ``(age, schedule_year, snap)``; ``age``
    is None when the truncated mass is empty (the section 6 law fails
    closed there; this builder records the disposition instead, because a
    misclassified status can make the mass legitimately empty).
    """

    requested = birth_year + 62
    available = sorted(year for s, year in schedule.pmf if s == sex)
    if not available:
        raise KeyError(f"no claiming distribution for sex {sex!r}")
    schedule_year = min(available, key=lambda year: abs(year - requested))
    if requested < available[0]:
        snap = "lower"
    elif requested > available[-1]:
        snap = "upper"
    else:
        snap = None
    ages, probability = schedule.distribution(sex, requested)
    keep = ages <= latest_claim_year - birth_year
    mass = float(probability[keep].sum())
    if not keep.any() or not np.isfinite(mass) or mass <= 0.0:
        return None, schedule_year, snap
    chosen = _person_rng(root_seed, person_id).choice(
        ages[keep], p=probability[keep] / mass
    )
    return int(chosen), schedule_year, snap


def _weighted(frame: pd.DataFrame, mask: pd.Series | None = None) -> dict:
    rows = frame if mask is None else frame[mask]
    return {
        "unweighted": int(len(rows)),
        "weighted": float(rows["weight"].sum()),
    }


def _band_label(low: int, high: int | None) -> str:
    return f"{low}+" if high is None else f"{low}-{high}"


def _dispositions(
    universe: pd.DataFrame,
    births: Mapping[int, career.BirthYearRecord],
    sex_by_person: pd.Series,
    spec: Psid2010CohortSpec,
) -> pd.DataFrame:
    """Attach sex and the section 3.1 birth year, then one disposition each."""

    out = universe.copy()
    ids = [int(pid) for pid in out["person_id"]]
    out["sex"] = out["person_id"].map(sex_by_person).astype("string")
    out["birth_year"] = pd.array(
        [births[pid].birth_year for pid in ids], dtype="Int64"
    )
    out["birth_source"] = pd.array(
        [births[pid].source.value for pid in ids], dtype="string"
    )
    unresolved = out["birth_year"].isna().to_numpy()
    outside = ~unresolved & (
        out["birth_year"].fillna(0).to_numpy() > spec.max_birth_year
    )
    coded_sex = out["sex"].isin(["male", "female"]).fillna(False).to_numpy()
    disposition = np.full(len(out), "member", dtype=object)
    disposition[unresolved] = "excluded_birth_year_unresolved"
    disposition[outside] = "outside_birth_cohort"
    disposition[~unresolved & ~outside & ~coded_sex] = "excluded_sex_unknown"
    out["disposition"] = pd.array(disposition, dtype="string")
    return out


def _base_persons(
    members: pd.DataFrame, spec: Psid2010CohortSpec
) -> pd.DataFrame:
    wave, start = spec.anchor_wave, spec.start_year
    persons = pd.DataFrame(
        {
            "person_id": members["person_id"].astype("int64"),
            f"interview_{wave}": members["interview"].astype("int64"),
            f"sequence_{wave}": members["sequence"].astype("int64"),
            f"relationship_{wave}": members["relationship"].astype("int64"),
            f"age_{wave}_reported": members["age"].astype("int64"),
            "weight": members["weight"].astype("float64"),
            "sex": members["sex"].astype("string"),
            "birth_year": members["birth_year"].astype("int64"),
            "birth_source": members["birth_source"].astype("string"),
            f"reported_birth_year_{wave}": members[
                "reported_birth_year"
            ].astype("Int64"),
        }
    ).reset_index(drop=True)
    # A1 section 16: the half-split floor's unit is the anchor wave's
    # family unit (ER34101 for 2011, ER34001 for 2009).
    persons.insert(1, "family_unit_id", persons[f"interview_{wave}"])
    persons["birth_year_age_derived"] = persons["birth_source"].isin(
        [
            career.BirthSource.INFERRED_PERIOD_AGE.value,
            career.BirthSource.DERIVED_PROJECTION_AGE.value,
        ]
    )
    persons[f"age_{start}"] = start - persons["birth_year"]
    return persons


def _attach_death(
    persons: pd.DataFrame, death_records: pd.DataFrame, anchor_wave: int
) -> None:
    death = death_records.set_index("person_id")
    for column in (
        "death_status",
        "death_year",
        "death_year_lo",
        "death_year_hi",
    ):
        values = (
            persons["person_id"].map(death[column])
            if column in death
            else pd.Series(pd.NA, index=persons.index)
        )
        persons[column] = values.astype(
            "string" if column == "death_status" else "Int64"
        )
    persons[f"death_before_{anchor_wave}_presence"] = (
        persons["death_year_hi"].fillna(anchor_wave) < anchor_wave
    ).astype(bool)


def _linked_birth_records(
    marriage_history: pd.DataFrame,
    observed_earnings: pd.DataFrame,
    person_ids: set[int],
) -> tuple[dict[int, career.BirthYearRecord], set[int]]:
    """Section 3.1 clauses 1-2 for linked spouses outside the universe.

    They have no 2011 seed row, so clause 3 cannot apply. Passing an empty
    ``required_person_ids`` makes the law drop (rather than raise on) a
    person with conflicting marriage-history birth years; those persons are
    returned separately so the column can name them.
    """

    history = marriage_history[marriage_history["person_id"].isin(person_ids)]
    years = history.dropna(subset=["birth_year"]).groupby("person_id")[
        "birth_year"
    ]
    conflicted = {
        int(pid) for pid, count in years.nunique().items() if count > 1
    }
    records = career.derive_birth_years(
        history,
        observed_earnings[observed_earnings["person_id"].isin(person_ids)],
        required_person_ids=(),
    )
    return {record.person_id: record for record in records}, conflicted


def _episodes_with_separation(history: pd.DataFrame) -> pd.DataFrame:
    """``marriage_episodes`` rows plus each marriage's MH16 separation year.

    :func:`populace_dynamics.data.marriage.marriage_episodes` keeps the
    separation year only as the end of a marriage still recorded as
    separated. A marriage that later ended in divorce also carries the
    year the spouses stopped living together, which decides whether the
    spouses were separated at the end of 2010. The episode rows are the
    marriage rows in the same (person, marriage order) sort; the
    alignment is checked, not assumed.
    """

    episodes = marriage.marriage_episodes(history)
    marriages = (
        history[history["is_marriage"]]
        .sort_values(["person_id", "marriage_order"])
        .reset_index(drop=True)
    )
    aligned = len(marriages) == len(episodes)
    if aligned:
        for column in ("person_id", "marriage_order", "start_year"):
            left = pd.Series(marriages[column]).astype("Int64")
            right = pd.Series(episodes[column]).astype("Int64")
            same = (left == right).fillna(left.isna() & right.isna())
            aligned = aligned and bool(same.all())
    if not aligned:
        raise AssertionError(
            "marriage episodes do not align with the marriage-history rows"
        )
    episodes["separation_year"] = marriages["separation_year"].astype("Int64")
    return episodes


def _attach_marital(
    persons: pd.DataFrame,
    inputs: Psid2010Inputs,
    births: Mapping[int, career.BirthYearRecord],
    universe_ids: set[int],
    spec: Psid2010CohortSpec,
) -> None:
    member_ids = set(int(pid) for pid in persons["person_id"])
    history = inputs.marriage_history[
        inputs.marriage_history["person_id"].isin(member_ids)
    ]
    episodes = _episodes_with_separation(history)
    by_person = {
        int(pid): rows
        for pid, rows in episodes.groupby("person_id", sort=False)
    }
    with_history = set(int(pid) for pid in history["person_id"])
    no_episodes = episodes.iloc[0:0]
    start = spec.start_year
    states = []
    for pid in persons["person_id"]:
        pid = int(pid)
        if pid in with_history:
            state = marital_state_at(
                by_person.get(pid, no_episodes),
                start,
                separated_is_married=spec.separated_is_married,
            )
        else:
            state = marital_state_at(no_episodes, start)
            state["status"] = "no_marriage_history"
        states.append(state)
    state = pd.DataFrame(states, index=persons.index)
    persons[f"marital_status_{start}"] = state["status"].astype("string")
    persons["spouse_person_id"] = state["spouse_person_id"].astype("Int64")
    persons["spouse_in_cohort"] = (
        persons["spouse_person_id"].isin(member_ids).fillna(False).astype(bool)
    )
    persons[f"separated_{start}"] = state["separated"].astype(bool)
    persons["multiple_marriages_in_force"] = state["multiple_in_force"].astype(
        bool
    )
    widowed = persons[f"marital_status_{start}"] == "widowed"
    persons["widowhood_year"] = (
        state["dissolution_year"].astype("Int64").where(widowed)
    )
    persons["late_spouse_person_id"] = (
        state["former_spouse_person_id"].astype("Int64").where(widowed)
    )
    death = inputs.death_records.set_index("person_id")
    persons["late_spouse_death_year"] = (
        persons["late_spouse_person_id"]
        .map(death["death_year"] if "death_year" in death else {})
        .astype("Int64")
    )

    linked = persons["spouse_person_id"].fillna(
        persons["late_spouse_person_id"]
    )
    linked_ids = {int(pid) for pid in linked.dropna()}
    outside, conflicted = _linked_birth_records(
        inputs.marriage_history,
        inputs.observed_earnings,
        linked_ids - universe_ids,
    )
    lookup = {**outside, **births}
    years = []
    sources = []
    for pid in linked:
        if pd.isna(pid):
            years.append(pd.NA)
            sources.append(pd.NA)
        elif int(pid) in lookup:
            years.append(lookup[int(pid)].birth_year)
            sources.append(lookup[int(pid)].source.value)
        elif int(pid) in conflicted:
            years.append(pd.NA)
            sources.append("conflicting_exact_marriage")
        else:
            years.append(pd.NA)
            sources.append(career.BirthSource.UNRESOLVED.value)
    persons["linked_spouse_birth_year"] = pd.array(years, dtype="Int64")
    persons["linked_spouse_birth_source"] = pd.array(sources, dtype="string")


def _attach_coresident_partner(
    persons: pd.DataFrame, anchor: pd.DataFrame, anchor_wave: int
) -> None:
    present = anchor[_presence_mask(anchor, Presence.IN_FAMILY)]
    heads = present[present["relationship"] == _HEAD].set_index("interview")
    partners = present[
        present["relationship"].isin([_LEGAL_SPOUSE, _PARTNER])
    ].set_index("interview")
    if heads.index.duplicated().any() or partners.index.duplicated().any():
        raise ValueError(
            f"a {anchor_wave} family has two heads or two wives/partners"
        )
    relationship_column = f"relationship_{anchor_wave}"
    is_head = persons[relationship_column] == _HEAD
    is_partner = persons[relationship_column].isin([_LEGAL_SPOUSE, _PARTNER])
    interview = persons[f"interview_{anchor_wave}"]
    partner_id = pd.Series(pd.NA, index=persons.index, dtype="Int64")
    relationship = pd.Series(pd.NA, index=persons.index, dtype="Int64")
    partner_id[is_head] = interview[is_head].map(partners["person_id"])
    relationship[is_head] = interview[is_head].map(partners["relationship"])
    partner_id[is_partner] = interview[is_partner].map(heads["person_id"])
    relationship[is_partner] = persons.loc[is_partner, relationship_column]
    relationship[partner_id.isna()] = pd.NA
    persons[f"coresident_partner_person_id_{anchor_wave}"] = partner_id
    persons[f"coresident_partner_relationship_{anchor_wave}"] = relationship


def _attach_m4(
    persons: pd.DataFrame,
    disability_status: pd.DataFrame,
    spec: Psid2010CohortSpec,
) -> None:
    columns = []
    for wave in spec.m4_waves:
        column = f"m4_disabled_{wave}"
        rows = disability_status[disability_status["period"] == wave]
        if rows.empty:
            # An absent wave would otherwise read as "nobody disabled".
            raise ValueError(
                f"disability_status has no rows for M4 wave {wave}"
            )
        disabled = rows.set_index("person_id")["disabled"]
        persons[column] = persons["person_id"].map(disabled).astype("boolean")
        columns.append(column)
    # A member with no ascertained status in any consulted wave is not
    # M4-disabled under the rule; the flag keeps that default visible.
    persons["m4_status_unknown"] = persons[columns].isna().all(axis=1)
    persons["m4_disabled"] = (
        persons[columns].fillna(False).any(axis=1).astype(bool)
    )


def _social_security_rows(
    persons: pd.DataFrame,
    head_spouse_ss: pd.DataFrame,
    individual_ss: pd.DataFrame,
    spec: Psid2010CohortSpec,
) -> pd.DataFrame:
    """Person x income-year Social Security under the source policy.

    A head or wife takes the family-file amount; another in-family member
    takes the individual-file amount under ``ofum_ss_source=individual_file``
    and is unobserved otherwise; a person absent from that wave's families
    is unobserved. ``individual_amount`` and the ``type_*`` flags come from
    the individual file whatever the role.
    """

    ids = sorted(int(pid) for pid in persons["person_id"])
    base = pd.DataFrame(
        [(pid, year) for pid in ids for year in SS_YEARS],
        columns=["person_id", "income_year"],
    )
    ind = individual_ss[individual_ss["person_id"].isin(ids)]
    ind = ind.assign(income_year=ind["wave"] - 1)[
        [
            "person_id",
            "income_year",
            "ss_amount",
            "ss_acc",
            *_TYPE_COLUMNS,
            "type_combination",
        ]
    ].rename(
        columns={
            "ss_amount": "individual_amount",
            "ss_acc": "individual_acc",
        }
    )
    hs = head_spouse_ss[head_spouse_ss["person_id"].isin(ids)]
    hs = hs.assign(income_year=hs["wave"] - 1)[
        ["person_id", "income_year", "role", "ss_amount", "ss_acc"]
    ].rename(
        columns={
            "role": "family_role",
            "ss_amount": "family_amount",
            "ss_acc": "family_acc",
        }
    )
    merged = base.merge(
        ind, on=["person_id", "income_year"], how="left", validate="1:1"
    ).merge(hs, on=["person_id", "income_year"], how="left", validate="1:1")
    in_family = merged["family_role"].notna()
    in_individual = merged["individual_amount"].notna()
    use_individual = (
        ~in_family
        & in_individual
        & (spec.ofum_ss_source is OfumSsSource.INDIVIDUAL_FILE)
    )
    role = np.where(
        in_family,
        merged["family_role"].astype(object),
        np.where(in_individual, "ofum", "absent"),
    )
    source = np.where(
        in_family,
        "family_head_spouse",
        np.where(use_individual, "individual_file", "unobserved"),
    )
    out = pd.DataFrame(
        {
            "person_id": merged["person_id"].astype("int64"),
            "income_year": merged["income_year"].astype("int64"),
            "role": pd.array(role, dtype="string"),
            "source": pd.array(source, dtype="string"),
        }
    )
    amount = pd.Series(pd.NA, index=merged.index, dtype="Int64")
    acc = pd.Series(pd.NA, index=merged.index, dtype="Int64")
    amount[in_family] = merged.loc[in_family, "family_amount"]
    acc[in_family] = merged.loc[in_family, "family_acc"]
    amount[use_individual] = merged.loc[use_individual, "individual_amount"]
    acc[use_individual] = merged.loc[use_individual, "individual_acc"]
    out["ss_amount"] = amount
    out["ss_acc"] = acc
    out["individual_amount"] = merged["individual_amount"].astype("Int64")
    for column in [*_TYPE_COLUMNS, "type_combination"]:
        out[column] = merged[column].astype("boolean")
    return out


def _attach_social_security(
    persons: pd.DataFrame, social_security: pd.DataFrame, start_year: int
) -> None:
    indexed = social_security.set_index(["person_id", "income_year"])
    for year in SS_YEARS:
        rows = indexed.xs(year, level="income_year")
        persons[f"ss_{year}"] = (
            persons["person_id"].map(rows["ss_amount"]).astype("Int64")
        )
        persons[f"ss_{year}_source"] = (
            persons["person_id"].map(rows["source"]).astype("string")
        )
    start = indexed.xs(start_year, level="income_year")
    for column in [*_TYPE_COLUMNS, "type_combination"]:
        persons[column] = (
            persons["person_id"].map(start[column]).astype("boolean")
        )
    persons[f"ss_receipt_{start_year}"] = (
        persons[f"ss_{start_year}"] > 0
    ).astype("boolean")


def _plan_status(
    *,
    age: int,
    widowed: bool,
    m4_disabled: bool,
    spec: Psid2010CohortSpec,
) -> tuple[OpeningStatus, str]:
    """The plan's A3 rule for a 2010 recipient (see the spec fields)."""

    if age >= spec.retirement_age:
        if (
            spec.aged_m4_disabled_di_below_age is not None
            and age < spec.aged_m4_disabled_di_below_age
            and m4_disabled
        ):
            return OpeningStatus.DISABLED_WORKER, "aged_m4_disabled_below_age"
        if widowed:
            return OpeningStatus.SURVIVOR, "aged_widowed"
        return OpeningStatus.RETIRED_WORKER, "aged_not_widowed"
    clauses = (
        (m4_disabled, OpeningStatus.DISABLED_WORKER, "under62_m4_disabled"),
        (widowed, OpeningStatus.SURVIVOR, "under62_widowed"),
    )
    if spec.under_62_precedence is Under62Precedence.WIDOWHOOD_THEN_M4:
        clauses = clauses[::-1]
    for condition, status, basis in clauses:
        if condition:
            return status, basis
    return OpeningStatus(spec.under_62_residual.value), "under62_residual"


def _reported_status(
    types: Mapping[str, Any], spec: Psid2010CohortSpec
) -> tuple[OpeningStatus, str, bool] | None:
    mentioned = [
        name for name in spec.reported_type_precedence if types[name] is True
    ]
    if not mentioned:
        return None
    return (
        _REPORTED_TYPE_STATUS[mentioned[0]],
        f"reported_{mentioned[0]}",
        len(mentioned) > 1,
    )


def _attach_opening_status(
    persons: pd.DataFrame, spec: Psid2010CohortSpec
) -> None:
    statuses = []
    bases = []
    multiple = []
    start = spec.start_year
    frame = persons.rename(
        columns={
            f"ss_receipt_{start}": "opening_receipt_flag",
            f"age_{start}": "opening_age_value",
            f"marital_status_{start}": "opening_marital_value",
        }
    )
    for row in frame.itertuples(index=False):
        receipt = row.opening_receipt_flag
        if pd.isna(receipt):
            statuses.append(OpeningStatus.UNOBSERVED.value)
            bases.append(f"ss_{start}_unobserved")
            multiple.append(False)
            continue
        if not receipt:
            statuses.append(OpeningStatus.NONE.value)
            bases.append(f"no_receipt_{start}")
            multiple.append(False)
            continue
        chosen = None
        if spec.status_rule is StatusRule.REPORTED_TYPE:
            types = {
                name: (
                    None
                    if pd.isna(getattr(row, f"type_{name}"))
                    else bool(getattr(row, f"type_{name}"))
                )
                for name in ssi.SS_TYPES
            }
            chosen = _reported_status(types, spec)
        if chosen is None:
            status, basis = _plan_status(
                age=int(row.opening_age_value),
                widowed=row.opening_marital_value == "widowed",
                m4_disabled=bool(row.m4_disabled),
                spec=spec,
            )
            if spec.status_rule is StatusRule.REPORTED_TYPE:
                basis = f"no_reported_type_fallback:{basis}"
            chosen = (status, basis, False)
        statuses.append(chosen[0].value)
        bases.append(chosen[1])
        multiple.append(chosen[2])
    persons["opening_status"] = pd.array(statuses, dtype="string")
    persons["opening_status_basis"] = pd.array(bases, dtype="string")
    persons["reported_type_multiple"] = np.asarray(multiple, dtype=bool)


def _attach_opening_claim(
    persons: pd.DataFrame,
    inputs: Psid2010Inputs,
    spec: Psid2010CohortSpec,
) -> None:
    """Opening claim year from observed first receipt, else section 6.

    With opening year ``s`` and the previous observed income year ``s - 2``
    (biennial PSID), receipt is *bracketed* when ``s - 2`` is observed as
    zero and ``s`` positive; the claim year then follows
    ``spec.bracket_resolution``. Otherwise the first receipt is censored at
    the latest year it is known to precede (``s - 2`` when that year is
    positive, ``s`` when it is unobserved): a retired worker's claim age is
    imputed under the section 6 law restricted to table rows at or before
    ``spec.claim_table_max_year``; other statuses have no table law and
    keep only the upper bound.  Under the 2011 wave ``s - 2`` is 2008;
    under the 2009 wave it is 2006, which the Social Security reader does
    not resolve, so every 2008 recipient is censored at 2008.
    """

    table = {
        key: value
        for key, value in inputs.claiming_pmf.items()
        if int(key[1]) <= spec.claim_table_max_year
    }
    if not table:
        raise ValueError("no claiming table rows at or before the table cap")
    schedule = ClaimingSchedule(table)
    wave, start = spec.anchor_wave, spec.start_year
    previous = start - 2
    anchor_families = inputs.head_spouse_ss[
        inputs.head_spouse_ss["wave"] == wave
    ].drop_duplicates("interview")
    prior_year = anchor_families.set_index("interview")["fu_ss_prior_year"]
    no_claim = (OpeningStatus.NONE.value, OpeningStatus.UNOBSERVED.value)
    frame = persons.assign(
        opening_previous_ss=(
            persons[f"ss_{previous}"]
            if f"ss_{previous}" in persons
            else pd.Series(pd.NA, index=persons.index, dtype="Int64")
        ),
        opening_interview=persons[f"interview_{wave}"],
    )
    rows = []
    for row in frame.itertuples(index=False):
        entry: dict[str, Any] = {
            "opening_claim_year": pd.NA,
            "opening_claim_year_basis": "not_applicable",
            "opening_claim_year_upper_bound": pd.NA,
            "opening_claim_age": pd.NA,
            "claim_schedule_year": pd.NA,
            "claim_schedule_snap": pd.NA,
        }
        rows.append(entry)
        if row.opening_status in no_claim:
            continue
        previous_ss = row.opening_previous_ss
        if not pd.isna(previous_ss) and int(previous_ss) == 0:
            year, basis = start, "bracketed_first_observed"
            if (
                spec.bracket_resolution
                is BracketResolution.FU_PRIOR_YEAR_INDICATOR
            ):
                # R20 asks about the year before last (start - 1).
                middle = start - 1
                code = prior_year.get(row.opening_interview, pd.NA)
                if not pd.isna(code) and int(code) == 1:
                    year, basis = middle, f"bracketed_fu_yes_{middle}"
                elif not pd.isna(code) and int(code) == 5:
                    basis = f"bracketed_fu_no_{middle}"
                else:
                    basis = f"bracketed_fu_{middle}_unknown"
            entry.update(
                opening_claim_year=year,
                opening_claim_year_basis=basis,
                opening_claim_year_upper_bound=start,
                opening_claim_age=year - int(row.birth_year),
            )
            continue
        latest = previous if not pd.isna(previous_ss) else start
        entry["opening_claim_year_upper_bound"] = latest
        if row.opening_status != OpeningStatus.RETIRED_WORKER.value:
            entry["opening_claim_year_basis"] = (
                f"censored_at_{latest}_no_table_law"
            )
            continue
        age, used_year, snap = _impute_claim_age(
            person_id=int(row.person_id),
            birth_year=int(row.birth_year),
            sex=str(row.sex),
            latest_claim_year=latest,
            schedule=schedule,
            root_seed=spec.stock_imputation_root_seed,
        )
        entry.update(claim_schedule_year=used_year, claim_schedule_snap=snap)
        if age is None:
            entry["opening_claim_year_basis"] = "imputation_empty_mass"
            continue
        entry.update(
            opening_claim_year=int(row.birth_year) + age,
            opening_claim_year_basis=f"imputed_censored_at_{latest}",
            opening_claim_age=age,
        )
    frame = pd.DataFrame(rows, index=persons.index)
    for column in (
        "opening_claim_year",
        "opening_claim_year_upper_bound",
        "opening_claim_age",
        "claim_schedule_year",
    ):
        persons[column] = frame[column].astype("Int64")
    persons["opening_claim_year_basis"] = frame[
        "opening_claim_year_basis"
    ].astype("string")
    persons["claim_schedule_snap"] = (
        frame["claim_schedule_snap"]
        .map(lambda value: pd.NA if value is None else value)
        .astype("string")
    )


def _careers(
    persons: pd.DataFrame, observed_earnings: pd.DataFrame, start_year: int
) -> pd.DataFrame:
    """1968-``start_year`` careers under ``career.build_career``.

    The information-as-of cutoff is the opening year (2010, or 2008 for
    the 2009 wave).
    """

    ids = set(int(pid) for pid in persons["person_id"])
    earnings = observed_earnings[observed_earnings["person_id"].isin(ids)]
    grouped = {
        int(pid): rows
        for pid, rows in earnings.groupby("person_id", sort=False)
    }
    no_earnings = earnings.iloc[0:0]
    no_trajectory = pd.DataFrame(
        {
            "person_id": pd.Series(dtype="int64"),
            "year": pd.Series(dtype="int64"),
            "earnings": pd.Series(dtype="float64"),
        }
    )
    rows = []
    summary = []
    for row in persons.itertuples(index=False):
        record = career.build_career(
            person_id=int(row.person_id),
            birth_year=int(row.birth_year),
            claim_year=start_year,
            observed_earnings=grouped.get(int(row.person_id), no_earnings),
            trajectory=no_trajectory,
        )
        summary.append(
            (
                record.coverage_start_year,
                record.coverage_ratio,
                record.imputed_year_share,
            )
        )
        rows.extend(
            (record.person_id, year.year, year.earnings, year.provenance.value)
            for year in record.years
        )
    summary_frame = pd.DataFrame(
        summary,
        columns=[
            "career_coverage_start",
            "career_coverage_ratio",
            "career_imputed_share",
        ],
        index=persons.index,
    )
    for column in summary_frame:
        persons[column] = summary_frame[column]
    careers = pd.DataFrame(
        rows, columns=["person_id", "year", "earnings", "provenance"]
    )
    return careers.astype(
        {
            "person_id": "int64",
            "year": "int64",
            "earnings": "float64",
            "provenance": "string",
        }
    )


# --------------------------------------------------------------------------
# The builder
# --------------------------------------------------------------------------
def build_psid2010_cohort(
    inputs: Psid2010Inputs,
    spec: Psid2010CohortSpec | None = None,
) -> Psid2010Cohort:
    """Build the PSID starting cohort from materialized inputs.

    The anchor wave is ``spec.anchor_wave`` (2011 by default; 2009 for
    the A1 R6 population), and ``inputs.anchor_wave`` must equal it.  The
    column names below are those of the 2011 wave; under another wave each
    ``_2011`` suffix is that wave and each ``_2010`` suffix its opening
    year (``interview_2009``, ``age_2008``, ``ss_receipt_2008``, ...), and
    the career runs through the opening year.

    Membership: a person in the anchor-wave presence universe
    (``spec.presence``, positive cross-sectional weight: ER34155 for 2011,
    ER34046 for 2009) whose section 3.1 birth year is at most
    ``spec.max_birth_year`` and whose sex is coded. Every universe person
    receives exactly one disposition: ``member``,
    ``excluded_birth_year_unresolved``, ``outside_birth_cohort`` or
    ``excluded_sex_unknown`` (in that precedence).

    ``persons`` columns: identity and anchor (``person_id``,
    ``family_unit_id`` (the anchor wave's interview number, the A1 section
    16 split unit), ``interview_2011``, ``sequence_2011``,
    ``relationship_2011``, ``age_2011_reported``, ``weight``), ``sex``,
    birth (``birth_year``,
    ``birth_source``, ``birth_year_age_derived``,
    ``reported_birth_year_2011``, ``age_2010``), death
    (``death_status``, ``death_year``, ``death_year_lo``,
    ``death_year_hi``, ``death_before_2011_presence``), marital state at the
    end of 2010 (``marital_status_2010``, ``spouse_person_id``,
    ``spouse_in_cohort``, ``separated_2010``,
    ``multiple_marriages_in_force``, ``widowhood_year``,
    ``late_spouse_person_id``, ``late_spouse_death_year``,
    ``linked_spouse_birth_year``, ``linked_spouse_birth_source``,
    ``coresident_partner_person_id_2011``,
    ``coresident_partner_relationship_2011``), M4 status
    (``m4_disabled_<wave>`` for each consulted wave, ``m4_status_unknown``
    and ``m4_disabled``),
    Social Security (``ss_<year>``, ``ss_<year>_source`` for 2008, 2010,
    2012; ``ss_receipt_2010``; the 2010 reported ``type_*`` flags), the
    opening stock (``opening_status``, ``opening_status_basis``,
    ``reported_type_multiple``, ``opening_claim_year``,
    ``opening_claim_year_basis``, ``opening_claim_year_upper_bound``,
    ``opening_claim_age``, ``claim_schedule_year``, ``claim_schedule_snap``)
    and the career summary (``career_coverage_start``,
    ``career_coverage_ratio``, ``career_imputed_share``).

    The builder sets ``provenance`` (see :class:`Psid2010Cohort`) from the
    inputs: ``psid_files`` when the inputs are the ones
    :func:`load_psid2010_inputs` returned and sealed (a ``psid_files``
    claim without that seal, or with frames or file hashes changed since,
    is refused), ``invented`` when the inputs carry a frame digest that
    their frames still match (refused if they do not; the A5 opening step
    re-generates it from the invented generator), and ``caller_frames``
    otherwise.
    """

    spec = spec or Psid2010CohortSpec()
    _validate_inputs(inputs)
    if int(inputs.anchor_wave) != spec.anchor_wave:
        raise ValueError(
            f"inputs hold the {inputs.anchor_wave} anchor wave but the "
            f"spec asks for {spec.anchor_wave}"
        )
    input_provenance = _input_provenance(inputs)
    wave, start = spec.anchor_wave, spec.start_year
    anchor = inputs.anchor
    universe = anchor[_presence_mask(anchor, spec.presence)].copy()
    universe_ids = set(int(pid) for pid in universe["person_id"])

    # The section 3.1 birth-year law, total over the presence universe.
    seed = pd.DataFrame(
        {
            "person_id": universe["person_id"].astype("int64"),
            "year": start,
            "anchor_wave": wave,
            "age": universe["age"].astype("int64"),
        }
    )
    history = inputs.marriage_history
    earnings = inputs.observed_earnings
    records = career.derive_birth_years(
        history[history["person_id"].isin(universe_ids)],
        earnings[earnings["person_id"].isin(universe_ids)],
        seed_coordinates=seed,
        required_person_ids=universe_ids,
    )
    births = {record.person_id: record for record in records}
    if set(births) != universe_ids:
        raise AssertionError("birth dispositions are not universe-total")

    classified = _dispositions(
        universe,
        births,
        inputs.death_records.set_index("person_id")["sex"],
        spec,
    )
    dispositions = classified[
        ["person_id", "weight", "disposition"]
    ].reset_index(drop=True)
    members = classified[classified["disposition"] == "member"].sort_values(
        "person_id"
    )
    persons = _base_persons(members, spec)
    _attach_death(persons, inputs.death_records, wave)
    _attach_marital(persons, inputs, births, universe_ids, spec)
    _attach_coresident_partner(persons, anchor, wave)
    _attach_m4(persons, inputs.disability_status, spec)
    social_security = _social_security_rows(
        persons, inputs.head_spouse_ss, inputs.individual_ss, spec
    )
    _attach_social_security(persons, social_security, start)
    _attach_opening_status(persons, spec)
    _attach_opening_claim(persons, inputs, spec)
    careers = _careers(persons, earnings, start)
    outside_presence = anchor[
        (anchor["weight"] > 0) & ~anchor["person_id"].isin(universe_ids)
    ]
    built = Psid2010Cohort(
        persons=persons,
        careers=careers,
        social_security=social_security,
        dispositions=dispositions,
        spec=spec,
        diagnostics=_diagnostics(
            persons,
            social_security,
            dispositions,
            outside_presence,
            inputs.death_records,
            spec,
        ),
    )
    object.__setattr__(
        built,
        "provenance",
        ReadOnlyProvenance(
            {
                **input_provenance,
                "anchor_wave": wave,
                "start_year": start,
                "set_by": "populace_dynamics.cohorts.psid2010."
                "build_psid2010_cohort",
                "content_sha256": cohort_content_sha256(built),
                "content_basis": _CONTENT_BASIS,
            }
        ),
    )
    return built


# --------------------------------------------------------------------------
# Provenance
# --------------------------------------------------------------------------
_INPUT_FRAMES = (
    "anchor",
    "death_records",
    "marriage_history",
    "observed_earnings",
    "head_spouse_ss",
    "individual_ss",
    "disability_status",
)
_CONTENT_BASIS = (
    "sha256 over the persons and careers frames, each as its column names, "
    "dtypes and CSV text (pandas to_csv, no index, '\\n' line ends)"
)
#: The persons columns that depend on the claim-age table
#: (``Psid2010Inputs.claiming_pmf``, a parameter rather than data): the
#: opening claim-year imputation of :func:`_attach_opening_claim`.
CLAIM_IMPUTATION_COLUMNS: tuple[str, ...] = (
    "opening_claim_year",
    "opening_claim_year_basis",
    "opening_claim_age",
    "claim_schedule_year",
    "claim_schedule_snap",
)


def _frame_digest(digest: Any, name: str, frame: pd.DataFrame) -> None:
    digest.update(f"{name}\n".encode())
    digest.update(json.dumps([str(c) for c in frame.columns]).encode())
    digest.update(json.dumps([str(t) for t in frame.dtypes]).encode())
    digest.update(
        frame.to_csv(index=False, lineterminator="\n").encode("utf-8")
    )


def input_frames_sha256(inputs: Psid2010Inputs) -> str:
    """SHA-256 of the seven reader frames and the anchor wave.

    The claim-age PMF, a parameter rather than data, is not included.
    """

    digest = hashlib.sha256(f"anchor_wave={inputs.anchor_wave}\n".encode())
    for name in _INPUT_FRAMES:
        _frame_digest(digest, name, getattr(inputs, name))
    return digest.hexdigest()


def cohort_content_sha256(cohort: Psid2010Cohort) -> str:
    """SHA-256 of a built cohort's persons and careers (the A5 inputs)."""

    digest = hashlib.sha256()
    _frame_digest(digest, "persons", cohort.persons)
    _frame_digest(digest, "careers", cohort.careers)
    return digest.hexdigest()


def cohort_data_sha256(cohort: Psid2010Cohort) -> str:
    """SHA-256 of what a cohort's data determine, without the claim table.

    The persons (less :data:`CLAIM_IMPUTATION_COLUMNS`, which depend on
    the claim-age table) and the careers, so two builds from the same
    frames and spec agree whatever claim-age table each used.  The A5
    opening step compares a cohort labelled invented with a re-generated
    invented build on this digest.
    """

    digest = hashlib.sha256()
    _frame_digest(
        digest,
        "persons",
        cohort.persons.drop(
            columns=[
                c for c in CLAIM_IMPUTATION_COLUMNS if c in cohort.persons
            ]
        ),
    )
    _frame_digest(digest, "careers", cohort.careers)
    return digest.hexdigest()


def _input_provenance(inputs: Psid2010Inputs) -> dict[str, Any]:
    """The cohort provenance the inputs establish (see the builder)."""

    recorded = dict(inputs.provenance or {})
    kind = recorded.get("kind")
    frames_sha256 = input_frames_sha256(inputs)
    if kind == PSID_FILES:
        files = recorded.get("psid_files_sha256")
        if not isinstance(files, Mapping) or not files:
            raise ValueError(
                "inputs claim psid_files provenance but record no PSID file"
            )
        seal = inputs.loader_seal
        if seal is None:
            raise ValueError(
                "inputs claim psid_files provenance but were not returned "
                "by load_psid2010_inputs (a hand-built or replaced "
                "Psid2010Inputs); only the loader establishes that frames "
                "came from PSID files"
            )
        if seal != {
            "input_frames_sha256": frames_sha256,
            "psid_files_bundle_sha256": _mapping_sha256(dict(files)),
        }:
            raise ValueError(
                "the frames or the recorded PSID file hashes changed after "
                "load_psid2010_inputs sealed them"
            )
        return {
            "kind": PSID_FILES,
            "psid_data_dir": recorded.get("psid_data_dir"),
            "psid_files_sha256": dict(files),
            "psid_files_bundle_sha256": recorded.get(
                "psid_files_bundle_sha256"
            ),
            "input_frames_sha256": frames_sha256,
        }
    if kind == INVENTED:
        if recorded.get("input_frames_sha256") != frames_sha256:
            raise ValueError(
                "inputs claim invented provenance but their frames differ "
                "from the digest the invented generator recorded "
                f"({recorded.get('input_frames_sha256')!r} != "
                f"{frames_sha256!r}); invented data cannot be mixed with "
                "other frames"
            )
        return {
            "kind": INVENTED,
            "generator": recorded.get("generator"),
            "seed": recorded.get("seed"),
            "label": recorded.get("data"),
            "input_frames_sha256": frames_sha256,
        }
    return {
        "kind": CALLER_FRAMES,
        "note": (
            "the inputs record neither the PSID files read nor the invented "
            "generator's digest"
        ),
        "input_frames_sha256": frames_sha256,
    }


def _reported_primary_type(persons: pd.DataFrame) -> pd.Series:
    """First mentioned 2010 type under the default precedence, per person."""

    precedence = Psid2010CohortSpec().reported_type_precedence
    primary = pd.Series("none_reported", index=persons.index, dtype=object)
    for name in reversed(precedence):
        mentioned = persons[f"type_{name}"].fillna(False).astype(bool)
        primary[mentioned] = name
    return primary.astype("string")


def _sequence_group(sequence: pd.Series, wave: int) -> pd.Series:
    group = pd.Series("other", index=sequence.index, dtype=object)
    for name, low, high in _SEQUENCE_GROUPS:
        group[sequence.between(low, high)] = name.format(previous=wave - 2)
    return group


def _diagnostics(
    persons: pd.DataFrame,
    social_security: pd.DataFrame,
    dispositions: pd.DataFrame,
    outside_presence: pd.DataFrame,
    death_records: pd.DataFrame,
    spec: Psid2010CohortSpec,
) -> dict[str, Any]:
    """Structural cross-checks of the build (counts only).

    ``outside_presence`` holds the anchor rows with a positive
    cross-sectional weight that the presence universe leaves out; they
    carry no disposition, so their count and weight are reported here by
    anchor-wave sequence group.
    """

    wave, start = spec.anchor_wave, spec.start_year

    family_rows = social_security[
        social_security["source"] == "family_head_spouse"
    ]
    both = family_rows.dropna(subset=["ss_amount", "individual_amount"])
    difference = (both["ss_amount"] - both["individual_amount"]).abs()
    receipt_disagreements = (both["ss_amount"] > 0) != (
        both["individual_amount"] > 0
    )
    married = persons[f"marital_status_{start}"] == "married"
    linked = married & persons["spouse_person_id"].notna()
    legal = persons[f"coresident_partner_relationship_{wave}"] == _LEGAL_SPOUSE
    same = linked & (
        persons["spouse_person_id"]
        == persons[f"coresident_partner_person_id_{wave}"]
    )
    reported = persons[f"reported_birth_year_{wave}"]
    comparable = reported.notna()
    gap = (persons["birth_year"][comparable] - reported[comparable]).abs()
    recipients = persons[
        persons[f"ss_receipt_{start}"].fillna(False).astype(bool)
    ]
    groups = _sequence_group(outside_presence["sequence"], wave)
    death_year = (
        death_records.set_index("person_id")["death_year"]
        if "death_year" in death_records
        else pd.Series(dtype="Int64")
    )
    spouse_death = persons["spouse_person_id"].map(death_year).astype("Int64")
    crosstab = pd.crosstab(
        recipients["opening_status"].astype(str),
        _reported_primary_type(recipients).astype(str),
    )
    return {
        "head_spouse_family_vs_individual_amount": {
            "rows_with_both": int(len(both)),
            "receipt_disagreements": int(receipt_disagreements.sum()),
            "exact_amount_matches": int((difference == 0).sum()),
            "max_abs_difference": (
                int(difference.max()) if len(difference) else 0
            ),
        },
        f"mh_spouse_vs_{wave}_coresident_legal_spouse": {
            "married_with_joinable_mh_spouse": int(linked.sum()),
            "coresident_legal_spouse_rows": int(legal.fillna(False).sum()),
            "mh_spouse_equals_coresident_partner": int(
                same.fillna(False).sum()
            ),
        },
        f"birth_year_vs_reported_{wave}": {
            "comparable": int(comparable.sum()),
            "exact": int((gap == 0).sum()),
            "within_one": int((gap <= 1).sum()),
        },
        f"opening_status_by_reported_primary_type_{start}": {
            str(status): {
                str(kind): int(count)
                for kind, count in row.items()
                if int(count)
            }
            for status, row in crosstab.iterrows()
        },
        f"death_before_{wave}_presence": int(
            persons[f"death_before_{wave}_presence"].sum()
        ),
        "positive_weight_outside_presence": {
            str(group): _weighted(outside_presence, groups == group)
            for group in sorted(groups.unique())
        },
        f"married_with_linked_spouse_dead_by_{start}": int(
            (married & (spouse_death <= start).fillna(False)).sum()
        ),
        f"separated_{start}": int(persons[f"separated_{start}"].sum()),
        "disposition_person_ids_unique": bool(
            dispositions["person_id"].is_unique
        ),
    }


# --------------------------------------------------------------------------
# Structural summary (no benefit, no reform, no comparison statistic)
# --------------------------------------------------------------------------
def structural_summary(cohort: Psid2010Cohort) -> dict[str, Any]:
    """Structural counts of a built cohort.

    Counts only: persons, weights, birth years, dispositions, sources,
    statuses, marital states and Social Security receipt by 2010 age band.
    It computes no benefit level, no reform and no comparison statistic.
    """

    persons = cohort.persons
    dispositions = cohort.dispositions
    start = cohort.start_year

    def counts(column: str) -> dict[str, dict]:
        values = persons[column].astype("string").fillna("<NA>")
        return {
            str(key): _weighted(persons, values == key)
            for key in sorted(values.unique())
        }

    receipt = persons[f"ss_receipt_{start}"].fillna(False).astype(bool)
    age = persons[f"age_{start}"]
    bands = {}
    for low, high in _SUMMARY_AGE_BANDS:
        in_band = age >= low
        if high is not None:
            in_band &= age <= high
        bands[_band_label(low, high)] = {
            "persons": _weighted(persons, in_band),
            f"ss_receipt_{start}": _weighted(persons, in_band & receipt),
        }
    return {
        "labels": list(cohort.labels),
        "anchor_wave": cohort.anchor_wave,
        "start_year": start,
        "provenance_kind": cohort.provenance.get("kind"),
        "not_computed": [
            "benefit levels",
            "any COLA scenario",
            "the five-group comparison statistic",
        ],
        "spec": cohort.spec.as_dict(),
        "persons": _weighted(persons),
        "person_id_unique": bool(persons["person_id"].is_unique),
        "weight_min": float(persons["weight"].min()) if len(persons) else None,
        "birth_year_range": (
            [
                int(persons["birth_year"].min()),
                int(persons["birth_year"].max()),
            ]
            if len(persons)
            else None
        ),
        "dispositions": {
            str(key): {
                "unweighted": int((dispositions["disposition"] == key).sum()),
                "weighted": float(
                    dispositions.loc[
                        dispositions["disposition"] == key, "weight"
                    ].sum()
                ),
            }
            for key in sorted(dispositions["disposition"].unique())
        },
        "sex": counts("sex"),
        "birth_source": counts("birth_source"),
        "death_status": counts("death_status"),
        f"marital_status_{start}": counts(f"marital_status_{start}"),
        "spouse_in_cohort": _weighted(persons, persons["spouse_in_cohort"]),
        f"ss_{start}_source": counts(f"ss_{start}_source"),
        f"ss_receipt_{start}": _weighted(persons, receipt),
        f"ss_receipt_{start}_by_age_{start}": bands,
        "opening_status": counts("opening_status"),
        "opening_status_basis": counts("opening_status_basis"),
        "opening_claim_year_basis": counts("opening_claim_year_basis"),
        "m4_disabled": _weighted(persons, persons["m4_disabled"]),
        "career_rows": int(len(cohort.careers)),
        "career_provenance": {
            str(key): int(value)
            for key, value in cohort.careers["provenance"]
            .value_counts()
            .sort_index()
            .items()
        },
        "career_coverage_ratio_mean": (
            float(persons["career_coverage_ratio"].mean())
            if len(persons)
            else None
        ),
        "diagnostics": dict(cohort.diagnostics),
    }
