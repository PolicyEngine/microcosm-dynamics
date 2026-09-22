"""The PSID 2010 starting cohort (Track A, work item A3).

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

import hashlib
import re
from collections.abc import Mapping
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
    "ANCHOR_WAVE",
    "START_YEAR",
    "DEFAULT_MAX_BIRTH_YEAR",
    "SS_YEARS",
    "COHORT_LABELS",
    "CLAIMING_REFERENCE_SHA256",
    "Presence",
    "OpeningStatus",
    "StatusRule",
    "Under62Precedence",
    "Under62Residual",
    "OfumSsSource",
    "BracketResolution",
    "Psid2010CohortSpec",
    "PendingDecision",
    "pending_decisions",
    "Psid2010Inputs",
    "Psid2010Cohort",
    "read_anchor_wave",
    "load_psid2010_inputs",
    "marital_state_at",
    "build_psid2010_cohort",
    "structural_summary",
]

#: The collection wave that defines presence, and its income year.
ANCHOR_WAVE = 2011
START_YEAR = ANCHOR_WAVE - 1
#: Plan section 3: persons aged 50+ in 2030 were born 1980 or earlier.
DEFAULT_MAX_BIRTH_YEAR = 1980
#: Social Security income years observed around the start (biennial).
SS_YEARS: tuple[int, ...] = ssi.SS_INCOME_YEARS

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

#: The 2011-wave anchor variables, each with its exact label, verified
#: against IND2023ER.sps before the read (2026-09-22: ER34155 is
#: "CORE/IMM INDIVIDUAL CROSS-SECTION WT 11" in both IND2023ER.sas and
#: IND2023ER.sps; codebook range 55-88,308, 0 = "not response in 2011").
_ANCHOR_VARS: dict[str, str] = {
    "ER30001": "1968 INTERVIEW NUMBER",
    "ER30002": "PERSON NUMBER 68",
    "ER34101": "2011 INTERVIEW NUMBER",
    "ER34102": "SEQUENCE NUMBER 11",
    "ER34103": "RELATION TO HEAD 11",
    "ER34104": "AGE OF INDIVIDUAL 11",
    "ER34106": "YEAR INDIVIDUAL BORN 11",
    "ER34155": "CORE/IMM INDIVIDUAL CROSS-SECTION WT 11",
}
_ANCHOR_COLUMNS: dict[str, str] = {
    "ER34101": "interview",
    "ER34102": "sequence",
    "ER34103": "relationship",
    "ER34104": "age",
    "ER34106": "reported_birth_year",
    "ER34155": "weight",
}
_WEIGHT_CONCEPT = r"CROSS-SECTION WT\s+11$"
_REPORTED_BIRTH_YEAR_NA = 9999

#: 2011 relationship codes (two-digit era): 10 head, 20 legal wife,
#: 22 cohabiting partner ("wife").
_HEAD = 10
_LEGAL_SPOUSE = 20
_PARTNER = 22

_SEQUENCE_IN_FAMILY = (1, 20)
_SEQUENCE_INSTITUTION = (51, 59)

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
    its default is the plan's proposal or a builder choice.
    """

    presence: Presence = Presence.IN_FAMILY
    max_birth_year: int = DEFAULT_MAX_BIRTH_YEAR
    retirement_age: int = 62
    status_rule: StatusRule = StatusRule.PLAN_AGE_M4_WIDOWHOOD
    under_62_precedence: Under62Precedence = (
        Under62Precedence.M4_THEN_WIDOWHOOD
    )
    under_62_residual: Under62Residual = Under62Residual.DISABLED_WORKER
    aged_m4_disabled_di_below_age: int | None = None
    m4_waves: tuple[int, ...] = (ANCHOR_WAVE,)
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
        if any(wave > ANCHOR_WAVE for wave in self.m4_waves):
            raise ValueError("m4_waves may not follow the 2011 anchor wave")
        if self.max_birth_year > START_YEAR:
            raise ValueError("max_birth_year may not follow the start year")
        if self.claim_table_max_year > START_YEAR:
            raise ValueError("claim_table_max_year may not follow 2010")
        if self.stock_imputation_root_seed < 0:
            raise ValueError("stock_imputation_root_seed must be >= 0")
        if (
            self.aged_m4_disabled_di_below_age is not None
            and self.aged_m4_disabled_di_below_age <= self.retirement_age
        ):
            raise ValueError(
                "aged_m4_disabled_di_below_age must exceed retirement_age"
            )

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
_MAX = "Max ruling / A1 specification freeze"


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
            "presence",
            spec.presence.value,
            (Presence.IN_FAMILY_OR_INSTITUTION.value,),
            f"{_BUILDER}: the plan says 'observed in the 2011 wave'; the "
            "default is the repository's presence notion (sequence 1-20), "
            "the only persons whose 2010 Social Security is asked",
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
            f"{_BUILDER}: the M4 self-report nearest the start",
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
    """

    persons: pd.DataFrame
    careers: pd.DataFrame
    social_security: pd.DataFrame
    dispositions: pd.DataFrame
    spec: Psid2010CohortSpec
    diagnostics: Mapping[str, Any]
    labels: tuple[str, ...] = COHORT_LABELS


# --------------------------------------------------------------------------
# Readers
# --------------------------------------------------------------------------
def read_anchor_wave(
    *, data_dir: Path | None = None, nrows: int | None = None
) -> pd.DataFrame:
    """Read the label-verified 2011-wave anchor row for every person.

    Columns: ``person_id`` (``ER30001 * 1000 + ER30002``), ``interview``,
    ``sequence``, ``relationship``, ``age`` (raw PSID code), and
    ``reported_birth_year`` (``ER34106``; a diagnostic only, never used by
    the birth-year law; ``<NA>`` for code 9999 or 0) and ``weight``
    (``ER34155``). ER34155 must be the only "CROSS-SECTION WT 11" label.
    """

    labels = psid.parse_sps_labels(
        psid.product_sps_path("ind2023er", data_dir)
    )
    psid.verify_labels(labels, _ANCHOR_VARS, context="ind2023er 2011 anchor")
    weight_hits = sorted(
        name
        for name, label in labels.items()
        if re.search(_WEIGHT_CONCEPT, " ".join(label.split()))
    )
    if weight_hits != ["ER34155"]:
        raise ValueError(
            f"2011 cross-section weight concept matched {weight_hits}; "
            "expected only ER34155"
        )
    raw = psid.read_psid(
        "ind2023er",
        columns=list(_ANCHOR_VARS),
        data_dir=data_dir,
        nrows=nrows,
    )
    frame = pd.DataFrame(
        {
            "person_id": raw["ER30001"].astype("int64") * 1000
            + raw["ER30002"].astype("int64")
        }
    )
    for var, column in _ANCHOR_COLUMNS.items():
        frame[column] = raw[var]
    for column in ("interview", "sequence", "relationship", "age"):
        frame[column] = frame[column].astype("int64")
    frame["weight"] = frame["weight"].astype("float64")
    if (frame["weight"] < 0).any():
        raise ValueError("negative 2011 cross-sectional weight")
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


def load_psid2010_inputs(
    *,
    data_dir: Path | None = None,
    birth_inference_max_wave: int | None = None,
    claiming_reference_path: Path | None = None,
) -> Psid2010Inputs:
    """Read every input from the staged PSID and the committed claim table.

    ``birth_inference_max_wave`` caps the family earnings waves read (and so
    the waves birth-year clause 2 may use); ``None`` reads every staged
    wave. Careers use income years through 2010 whatever the cap, so the
    cap may not precede the 2011 wave.
    """

    waves = family.FAMILY_WAVES
    if birth_inference_max_wave is not None:
        if int(birth_inference_max_wave) < ANCHOR_WAVE:
            raise ValueError(
                "birth_inference_max_wave may not precede the 2011 wave"
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
    status_codes = disability.verify_employment_status_codes(
        data_dir=data_dir, waves=[2009, ANCHOR_WAVE]
    )
    return Psid2010Inputs(
        anchor=read_anchor_wave(data_dir=data_dir),
        death_records=deaths.read_death_records(data_dir=data_dir),
        marriage_history=marriage.marriage_history(data_dir=data_dir),
        observed_earnings=family.family_earnings_panel(
            waves=waves, data_dir=data_dir
        ),
        head_spouse_ss=ssi.head_spouse_social_security_panel(
            data_dir=data_dir
        ),
        individual_ss=ssi.read_individual_social_security(data_dir=data_dir),
        disability_status=disability.read_disability_status(
            data_dir=data_dir, max_period=ANCHOR_WAVE
        ),
        claiming_pmf=claiming_pmf,
        provenance={
            "psid_data_dir": str(psid._resolve_data_dir(data_dir)),
            "earnings_waves": [int(waves[0]), int(waves[-1])],
            "claiming_reference": str(reference_path),
            "claiming_reference_sha256": digest,
            "employment_status_formats": {
                str(wave): value["format"]
                for wave, value in status_codes.items()
            },
        },
    )


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
    :func:`populace_dynamics.data.marriage.marriage_episodes` rows. A
    marriage is dated when its start year is known and, if it has ended,
    its end (or separation) year is known. The precedence is:

    1. any dated marriage in force at the end of ``year`` -> ``married``
       (the latest start wins; ``multiple_in_force`` flags more than one
       marriage in force); a
       marriage separated by ``year`` counts as in force (flagged
       ``separated``) when ``separated_is_married``, else it is a
       ``separated`` dissolution;
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
        if how == "intact":
            in_force.append((start, order, spouse, False))
        elif how in ("widowhood", "divorce", "separated"):
            if pd.isna(end):
                undated = True
            elif int(end) > year:
                in_force.append((start, order, spouse, False))
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


def _base_persons(members: pd.DataFrame) -> pd.DataFrame:
    persons = pd.DataFrame(
        {
            "person_id": members["person_id"].astype("int64"),
            "interview_2011": members["interview"].astype("int64"),
            "sequence_2011": members["sequence"].astype("int64"),
            "relationship_2011": members["relationship"].astype("int64"),
            "age_2011_reported": members["age"].astype("int64"),
            "weight": members["weight"].astype("float64"),
            "sex": members["sex"].astype("string"),
            "birth_year": members["birth_year"].astype("int64"),
            "birth_source": members["birth_source"].astype("string"),
            "reported_birth_year_2011": members["reported_birth_year"].astype(
                "Int64"
            ),
        }
    ).reset_index(drop=True)
    persons["birth_year_age_derived"] = persons["birth_source"].isin(
        [
            career.BirthSource.INFERRED_PERIOD_AGE.value,
            career.BirthSource.DERIVED_PROJECTION_AGE.value,
        ]
    )
    persons["age_2010"] = START_YEAR - persons["birth_year"]
    return persons


def _attach_death(persons: pd.DataFrame, death_records: pd.DataFrame) -> None:
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
    persons["death_before_2011_presence"] = (
        persons["death_year_hi"].fillna(ANCHOR_WAVE) < ANCHOR_WAVE
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
    episodes = marriage.marriage_episodes(history)
    by_person = {
        int(pid): rows
        for pid, rows in episodes.groupby("person_id", sort=False)
    }
    with_history = set(int(pid) for pid in history["person_id"])
    no_episodes = episodes.iloc[0:0]
    states = []
    for pid in persons["person_id"]:
        pid = int(pid)
        if pid in with_history:
            state = marital_state_at(
                by_person.get(pid, no_episodes),
                START_YEAR,
                separated_is_married=spec.separated_is_married,
            )
        else:
            state = marital_state_at(no_episodes, START_YEAR)
            state["status"] = "no_marriage_history"
        states.append(state)
    state = pd.DataFrame(states, index=persons.index)
    persons["marital_status_2010"] = state["status"].astype("string")
    persons["spouse_person_id"] = state["spouse_person_id"].astype("Int64")
    persons["spouse_in_cohort"] = (
        persons["spouse_person_id"].isin(member_ids).fillna(False).astype(bool)
    )
    persons["separated_2010"] = state["separated"].astype(bool)
    persons["multiple_marriages_in_force"] = state["multiple_in_force"].astype(
        bool
    )
    widowed = persons["marital_status_2010"] == "widowed"
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
    persons: pd.DataFrame, anchor: pd.DataFrame
) -> None:
    present = anchor[_presence_mask(anchor, Presence.IN_FAMILY)]
    heads = present[present["relationship"] == _HEAD].set_index("interview")
    partners = present[
        present["relationship"].isin([_LEGAL_SPOUSE, _PARTNER])
    ].set_index("interview")
    if heads.index.duplicated().any() or partners.index.duplicated().any():
        raise ValueError("a 2011 family has two heads or two wives/partners")
    is_head = persons["relationship_2011"] == _HEAD
    is_partner = persons["relationship_2011"].isin([_LEGAL_SPOUSE, _PARTNER])
    interview = persons["interview_2011"]
    partner_id = pd.Series(pd.NA, index=persons.index, dtype="Int64")
    relationship = pd.Series(pd.NA, index=persons.index, dtype="Int64")
    partner_id[is_head] = interview[is_head].map(partners["person_id"])
    relationship[is_head] = interview[is_head].map(partners["relationship"])
    partner_id[is_partner] = interview[is_partner].map(heads["person_id"])
    relationship[is_partner] = persons.loc[is_partner, "relationship_2011"]
    relationship[partner_id.isna()] = pd.NA
    persons["coresident_partner_person_id_2011"] = partner_id
    persons["coresident_partner_relationship_2011"] = relationship


def _attach_m4(
    persons: pd.DataFrame,
    disability_status: pd.DataFrame,
    spec: Psid2010CohortSpec,
) -> None:
    columns = []
    for wave in spec.m4_waves:
        column = f"m4_disabled_{wave}"
        rows = disability_status[disability_status["period"] == wave]
        disabled = rows.set_index("person_id")["disabled"]
        persons[column] = persons["person_id"].map(disabled).astype("boolean")
        columns.append(column)
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
    persons: pd.DataFrame, social_security: pd.DataFrame
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
    start = indexed.xs(START_YEAR, level="income_year")
    for column in [*_TYPE_COLUMNS, "type_combination"]:
        persons[column] = (
            persons["person_id"].map(start[column]).astype("boolean")
        )
    persons["ss_receipt_2010"] = (persons["ss_2010"] > 0).astype("boolean")


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
    for row in persons.itertuples(index=False):
        receipt = row.ss_receipt_2010
        if pd.isna(receipt):
            statuses.append(OpeningStatus.UNOBSERVED.value)
            bases.append("ss_2010_unobserved")
            multiple.append(False)
            continue
        if not receipt:
            statuses.append(OpeningStatus.NONE.value)
            bases.append("no_receipt_2010")
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
                age=int(row.age_2010),
                widowed=row.marital_status_2010 == "widowed",
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

    Receipt is *bracketed* when 2008 is observed as zero and 2010 positive;
    the claim year then follows ``spec.bracket_resolution``. Otherwise the
    first receipt is censored at the latest year it is known to precede
    (2008 when 2008 is positive, 2010 when 2008 is unobserved): a retired
    worker's claim age is imputed under the section 6 law restricted to
    table rows at or before ``spec.claim_table_max_year``; other statuses
    have no table law and keep only the upper bound.
    """

    table = {
        key: value
        for key, value in inputs.claiming_pmf.items()
        if int(key[1]) <= spec.claim_table_max_year
    }
    if not table:
        raise ValueError("no claiming table rows at or before the table cap")
    schedule = ClaimingSchedule(table)
    anchor_families = inputs.head_spouse_ss[
        inputs.head_spouse_ss["wave"] == ANCHOR_WAVE
    ].drop_duplicates("interview")
    prior_year = anchor_families.set_index("interview")["fu_ss_prior_year"]
    no_claim = (OpeningStatus.NONE.value, OpeningStatus.UNOBSERVED.value)
    rows = []
    for row in persons.itertuples(index=False):
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
        ss_2008 = row.ss_2008
        if not pd.isna(ss_2008) and int(ss_2008) == 0:
            year, basis = START_YEAR, "bracketed_first_observed"
            if (
                spec.bracket_resolution
                is BracketResolution.FU_PRIOR_YEAR_INDICATOR
            ):
                code = prior_year.get(row.interview_2011, pd.NA)
                if not pd.isna(code) and int(code) == 1:
                    year, basis = 2009, "bracketed_fu_yes_2009"
                elif not pd.isna(code) and int(code) == 5:
                    basis = "bracketed_fu_no_2009"
                else:
                    basis = "bracketed_fu_2009_unknown"
            entry.update(
                opening_claim_year=year,
                opening_claim_year_basis=basis,
                opening_claim_year_upper_bound=START_YEAR,
                opening_claim_age=year - int(row.birth_year),
            )
            continue
        latest = 2008 if not pd.isna(ss_2008) else START_YEAR
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
    persons: pd.DataFrame, observed_earnings: pd.DataFrame
) -> pd.DataFrame:
    """1968-2010 careers under ``career.build_career`` (as-of 2010)."""

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
            claim_year=START_YEAR,
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
    """Build the PSID 2010 starting cohort from materialized inputs.

    Membership: a person in the 2011 presence universe (``spec.presence``,
    positive ER34155 weight) whose section 3.1 birth year is at most
    ``spec.max_birth_year`` and whose sex is coded. Every universe person
    receives exactly one disposition: ``member``,
    ``excluded_birth_year_unresolved``, ``outside_birth_cohort`` or
    ``excluded_sex_unknown`` (in that precedence).

    ``persons`` columns: identity and anchor (``person_id``,
    ``interview_2011``, ``sequence_2011``, ``relationship_2011``,
    ``age_2011_reported``, ``weight``), ``sex``, birth (``birth_year``,
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
    (``m4_disabled_<wave>`` for each consulted wave and ``m4_disabled``),
    Social Security (``ss_<year>``, ``ss_<year>_source`` for 2008, 2010,
    2012; ``ss_receipt_2010``; the 2010 reported ``type_*`` flags), the
    opening stock (``opening_status``, ``opening_status_basis``,
    ``reported_type_multiple``, ``opening_claim_year``,
    ``opening_claim_year_basis``, ``opening_claim_year_upper_bound``,
    ``opening_claim_age``, ``claim_schedule_year``, ``claim_schedule_snap``)
    and the career summary (``career_coverage_start``,
    ``career_coverage_ratio``, ``career_imputed_share``).
    """

    spec = spec or Psid2010CohortSpec()
    _validate_inputs(inputs)
    anchor = inputs.anchor
    universe = anchor[_presence_mask(anchor, spec.presence)].copy()
    universe_ids = set(int(pid) for pid in universe["person_id"])

    # The section 3.1 birth-year law, total over the presence universe.
    seed = pd.DataFrame(
        {
            "person_id": universe["person_id"].astype("int64"),
            "year": START_YEAR,
            "anchor_wave": ANCHOR_WAVE,
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
    persons = _base_persons(members)
    _attach_death(persons, inputs.death_records)
    _attach_marital(persons, inputs, births, universe_ids, spec)
    _attach_coresident_partner(persons, anchor)
    _attach_m4(persons, inputs.disability_status, spec)
    social_security = _social_security_rows(
        persons, inputs.head_spouse_ss, inputs.individual_ss, spec
    )
    _attach_social_security(persons, social_security)
    _attach_opening_status(persons, spec)
    _attach_opening_claim(persons, inputs, spec)
    careers = _careers(persons, earnings)
    return Psid2010Cohort(
        persons=persons,
        careers=careers,
        social_security=social_security,
        dispositions=dispositions,
        spec=spec,
        diagnostics=_diagnostics(persons, social_security, dispositions),
    )


def _reported_primary_type(persons: pd.DataFrame) -> pd.Series:
    """First mentioned 2010 type under the default precedence, per person."""

    precedence = Psid2010CohortSpec().reported_type_precedence
    primary = pd.Series("none_reported", index=persons.index, dtype=object)
    for name in reversed(precedence):
        mentioned = persons[f"type_{name}"].fillna(False).astype(bool)
        primary[mentioned] = name
    return primary.astype("string")


def _diagnostics(
    persons: pd.DataFrame,
    social_security: pd.DataFrame,
    dispositions: pd.DataFrame,
) -> dict[str, Any]:
    """Structural cross-checks of the build (counts only)."""

    family_rows = social_security[
        social_security["source"] == "family_head_spouse"
    ]
    both = family_rows.dropna(subset=["ss_amount", "individual_amount"])
    difference = (both["ss_amount"] - both["individual_amount"]).abs()
    receipt_disagreements = (both["ss_amount"] > 0) != (
        both["individual_amount"] > 0
    )
    linked = (persons["marital_status_2010"] == "married") & persons[
        "spouse_person_id"
    ].notna()
    legal = persons["coresident_partner_relationship_2011"] == _LEGAL_SPOUSE
    same = linked & (
        persons["spouse_person_id"]
        == persons["coresident_partner_person_id_2011"]
    )
    reported = persons["reported_birth_year_2011"]
    comparable = reported.notna()
    gap = (persons["birth_year"][comparable] - reported[comparable]).abs()
    recipients = persons[persons["ss_receipt_2010"].fillna(False).astype(bool)]
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
        "mh_spouse_vs_2011_coresident_legal_spouse": {
            "married_with_joinable_mh_spouse": int(linked.sum()),
            "coresident_legal_spouse_rows": int(legal.fillna(False).sum()),
            "mh_spouse_equals_coresident_partner": int(
                same.fillna(False).sum()
            ),
        },
        "birth_year_vs_reported_2011": {
            "comparable": int(comparable.sum()),
            "exact": int((gap == 0).sum()),
            "within_one": int((gap <= 1).sum()),
        },
        "opening_status_by_reported_primary_type_2010": {
            str(status): {
                str(kind): int(count)
                for kind, count in row.items()
                if int(count)
            }
            for status, row in crosstab.iterrows()
        },
        "death_before_2011_presence": int(
            persons["death_before_2011_presence"].sum()
        ),
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

    def counts(column: str) -> dict[str, dict]:
        values = persons[column].astype("string").fillna("<NA>")
        return {
            str(key): _weighted(persons, values == key)
            for key in sorted(values.unique())
        }

    receipt = persons["ss_receipt_2010"].fillna(False).astype(bool)
    bands = {}
    for low, high in _SUMMARY_AGE_BANDS:
        in_band = persons["age_2010"] >= low
        if high is not None:
            in_band &= persons["age_2010"] <= high
        bands[_band_label(low, high)] = {
            "persons": _weighted(persons, in_band),
            "ss_receipt_2010": _weighted(persons, in_band & receipt),
        }
    return {
        "labels": list(cohort.labels),
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
        "marital_status_2010": counts("marital_status_2010"),
        "spouse_in_cohort": _weighted(persons, persons["spouse_in_cohort"]),
        "ss_2010_source": counts("ss_2010_source"),
        "ss_receipt_2010": _weighted(persons, receipt),
        "ss_receipt_2010_by_age_2010": bands,
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
