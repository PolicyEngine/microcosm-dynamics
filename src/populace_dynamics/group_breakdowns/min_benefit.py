"""Exercise 4 (Track M) by MINT8 characteristic subgroups (NASI G4c).

Exercise 4 of the DYNASIM3 scorecard measured, on the PSID's 2023 wave
(income year 2022), the share of OASDI beneficiaries aged 62 and older who
would receive a minimum benefit under Table 5's options 2-5, for All, Men
and Women (Registration 17, issue #42 comment 5855753783, registered
commit ``2e4e08be``; committed artifact
``runs/replication_urban2006_minimum_benefit_v1.json``).  This module
breaks that statistic down by SSA's MINT8 characteristic subgroups.  It is
post hoc: the committed run's comparator values are public, so every
output is labelled "registered, one-shot, post hoc, not blind" and
"report-only" beside Track M's own labels, and none is scored.

The order, which :func:`run_group_breakdowns` enforces
------------------------------------------------------
1. **Parameters before data.**  The parameters' provenance
   (``TrackMParameters.source()``: the oracle's policyengine-us revision,
   the quarter-of-coverage capture and the Census thresholds) must equal
   the committed artifact's ``parameters`` block.
2. **The same PSID files.**  The cohort inputs are read (Track M's
   ``cohort.load_cohort_inputs``, which records every file's SHA-256) and
   the files' SHA-256 must equal the committed ``inputs.source.
   psid_files_sha256``.
3. **Re-execution of the frozen registered computation**
   (:func:`reexecute_track_m`), composing Track M read-only exactly as
   ``scripts/run_track_m_registered.py``'s ``run_pipeline`` does: the M4
   cohort under the scored reading and under cos d430's sensitivity
   reading, the M5 careers, and ``pipeline.run_track_m`` with the
   committed run's own registration pointer, plus each cohort's
   ``cohort_structure``; and, for the person rows the groups need,
   ``evaluation.evaluate(inputs, policy_for_row(row), params)`` and the
   unchanged ``tabulation.tabulate_track_m`` for every registered row
   MS0-MS6 and for d430's sensitivity.
4. **Exact reproduction before any group work**
   (:func:`reproduction_checks`).  Every block of the re-executed pipeline
   result (every key ``run_track_m`` returns, the rows' tabulations and
   diagnostics, the sensitivity, both cohort structures, the inputs'
   provenance; not ``header`` and ``specification``, which the registered
   runner overwrote) and every per-row tabulation and diagnostics block
   must equal the committed artifact exactly
   (:data:`.common.EXACT_COMPARISON`: equal JSON leaves, floats bit for
   bit, no tolerance).  On any difference the run raises
   :class:`.common.ReproductionMismatchError` before the group-attribute
   loader is called, and nothing is written.
5. **Person attributes** (:func:`person_attributes`), joined by
   ``person_id``: sex, age, marital status and the 2022 benefit type from
   Track M's own cohort; race and ethnicity, country of birth and
   education from the cohort side frame
   (:mod:`populace_dynamics.cohorts.group_attributes`, G1, anchor wave
   2023); the initial AIME at 62 and the lifetime payroll-tax present
   values, own and shared, from
   :mod:`populace_dynamics.estimates.lifetime_measures` (G2).
6. **Cells** (:func:`tabulate_breakdowns`): G3's
   ``tabulate_share_breakdown`` for every registered row and option 2-5
   and for d430's sensitivity, with the design-based standard error and
   the five-seed half-sample floor Track M registered.
7. **Consistency with the registered cells**
   (:func:`consistency_checks`): G3's Total, Female and Male cells must
   equal ``tabulate_track_m``'s All, Women and Men cells exactly (share,
   weighted and unweighted counts, design SE, floor); otherwise refuse.

The scheme (:data:`SCHEME`)
---------------------------
G3's ``MINT8_ANNUAL_WITH_LIFETIME_SCHEME`` (MINT8's annual beneficiary
rows, with MINT8's three cohort-table quintile measures appended as the
lifetime-earnings dimension) without the two rows Track M cannot compute
(:data:`NOT_COMPUTED_DIMENSIONS`).  Its conventions here:

* **Sex**: Track M's (ER32000 through the death records); ``unknown``
  (code 9) is unclassified, as Track M counts it in All only.
* **Age**: 2022 minus the birth year Track M resolved (the first-estimates
  birth-year law).  The universe is born 1960 or earlier, so every age is
  62 or more and MINT8's "60–69" row holds ages 62-69 here; "90 or older"
  is MINT8's top row.
* **Marital status**: Track M's ``marital_status_2022`` (the marriage
  history's state at the end of 2022, separated counted as married by
  ``psid2010.marital_state_at``'s default), MINT8's four as themselves;
  ``unknown`` and ``no_marriage_history`` are unclassified.
* **Race and ethnicity, country of birth, education**: G1's MINT8 scheme
  (``data/external/group_category_schemes_v1.json``) through
  :func:`.common.side_frame_codes` and G1's years of schooling, education
  resolved as of the 2023 wave.
* **Current-law benefit type** (:func:`benefit_type_2022`,
  :data:`BENEFIT_TYPE_RULES`): Track M's own reading of the 2022 receipt
  mapped to MINT8's four rows.  A survivor or dependent mention among the
  six G33A items ER35213-ER35218 the cohort reads makes the person a
  widow(er) or a spouse (dually entitled included); otherwise the benefit
  is the own worker benefit Track M pays (its scored reading counts an
  unknown or "other" type as own receipt, cos d430), disabled or retired
  by the worker type mentioned or, when that does not settle it, by the
  basis of Track M's own worker record, and a disabled worker at or over
  the full retirement age is a retired worker (MINT8).  "Only" that
  cannot be established is unclassified, with its reason.
* **Lifetime earnings** (MINT8's cohort-table measures):

  - *initial AIME quintile*: G2's ``initial_aime_at_62`` under the
    exercise-4 convention (``AIME_CONVENTIONS["exercise_4_min_benefit"]``:
    statutory computation years, earnings through the year of attaining
    61) over the MS0 evaluation's one history of the person's own worker
    record, which re-expresses MS0's AIME (indexed to the year of
    attaining 60, computed through the year before entitlement) at age 62;
    for an old-age record entitled in the year of attaining 62 the two are
    the same number, which the run checks.  A person with no own record
    (paid only a spouse's or survivor's benefit) has no initial AIME and
    is unclassified;
  - *lifetime payroll tax quintile*, own and shared: G2's
    ``lifetime_payroll_tax_pv_at_62`` over each person's lifetime history
    through 2022 built by Track M's own rule (``careers.
    observed_histories`` of the earnings panel, ``prior_year_labor_income.
    next_wave_histories``, then ``coverage.one_history`` with MS0's
    policy), spouses included for the shared measure, G2's registered
    builder defaults (combined OASDI rate on earnings capped at the
    taxable maximum, the OASDI trust funds' effective interest rate,
    separated counted as married, a spouse with no history counted own).

  Quintiles are cut by G3's weighted-quintile rule with the 2023
  cross-section weight within each 10-year birth cohort of the universe
  (MINT8: "We calculate the AIME quintiles for each birth cohort"), so the
  "1960–1969" cohort holds only the 1960 births here.

Group attributes are person attributes: computed once (MS0's histories,
the scored reading's cohort) and used for every row and for d430's
sensitivity, whose universe and person order are the same.

What is not computed (:data:`NOT_COMPUTED_DIMENSIONS`,
:data:`NOT_COMPUTED_STATISTICS`): current-law poverty status and household
income quintile (Track M's inputs carry no 2022 family money income), and
MINT8's benefit-change statistics (``evaluate`` returns receipt flags,
not person-level benefits).  Each is recorded with its reason.

Nothing here reads a PSID file itself, and nothing here writes: the
cohort-input and group-attribute loaders are passed in (the registered
entry script passes the staged-PSID loaders, the dry run INVENTED ones),
and the caller writes the returned document.  It never reads a comparator
value.
"""

from __future__ import annotations

import copy
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from populace_dynamics.cohorts import group_attributes as g1
from populace_dynamics.cohorts import psid2010
from populace_dynamics.data import prior_year_labor_income as pyl
from populace_dynamics.data import social_security_receipt as ssr
from populace_dynamics.estimates import group_breakdown as g3
from populace_dynamics.estimates import lifetime_measures as g2
from populace_dynamics.estimates.parameters import COLA_HISTORY_PATH
from populace_dynamics.group_breakdowns import common
from populace_dynamics.min_benefit_track_m import (
    COVERED_EARNINGS_DISCLOSURE,
    OUTPUT_LABELS,
    careers,
    cohort,
    coverage,
    pipeline,
    structure,
    tabulation,
)
from populace_dynamics.min_benefit_track_m.evaluation import (
    INVENTED,
    PSID_FILES,
    Evaluation,
    TrackMInputs,
    TrackMParameters,
    evaluate,
)
from populace_dynamics.min_benefit_track_m.policy import (
    OWN_RECEIPT_PRE62_UNKNOWN_OR_OTHER_UNOBSERVED,
    OWN_RECEIPT_SENSITIVITY_ID,
    REGISTERED_ROWS,
    SENSITIVITIES,
    TABLE6_OPTIONS,
    policy_for_row,
)
from populace_dynamics.ss.params import SSAParameters

__all__ = [
    "AIME_CONVENTION",
    "ANALYSIS_YEAR",
    "COLA_HISTORY_RELATIVE_PATH",
    "ANCHOR_WAVES",
    "BENEFIT_TYPE_RULES",
    "COLUMNS_MAP",
    "GROUP_NAMED_DELTAS",
    "LABELS",
    "LOCATION_FIELDS",
    "LOCATION_RULE",
    "NOT_COMPUTED_DIMENSIONS",
    "NOT_COMPUTED_STATISTICS",
    "OUTPUT_ARTIFACT_PATH",
    "PARENT_ARTIFACT_PATH",
    "PARENT_ARTIFACT_SHA256",
    "PARENT_REGISTERED_COMMIT",
    "PARENT_REGISTRATION_POINTER",
    "PARENT_SPECIFICATION_SHA256",
    "PersonAttributes",
    "SCHEMA_VERSION",
    "SCHEME",
    "SENSITIVITY_KEY",
    "YOUNGEST_AGE",
    "STATISTIC_ID",
    "TrackMReexecution",
    "benefit_type_2022",
    "check_parent_binding",
    "located",
    "relative_location",
    "consistency_checks",
    "initial_aime_measure",
    "invented_group_attribute_loader",
    "lifetime_careers",
    "load_parent_artifact",
    "person_attributes",
    "reexecute_track_m",
    "reproduce_parent",
    "reproduction_checks",
    "run_group_breakdowns",
    "tabulate_breakdowns",
]

SCHEMA_VERSION = "populace_dynamics.group_breakdowns.min_benefit.v1"
_ROOT = Path(__file__).resolve().parents[3]
#: The committed exercise-4 artifact (Registration 17) and its pins, as
#: ``tests/test_replication_urban2006_minimum_benefit.py`` pins them.
PARENT_ARTIFACT_PATH = (
    _ROOT / "runs" / "replication_urban2006_minimum_benefit_v1.json"
)
PARENT_ARTIFACT_SHA256 = (
    "b2c2806254618bc8c4cf6c20e652ec2a06ce8a7c05de01a82c151a5d7921cafc"
)
PARENT_REGISTRATION_POINTER = (
    "https://github.com/PolicyEngine/microcosm-dynamics/issues/42"
    "#issuecomment-5855753783"
)
PARENT_REGISTERED_COMMIT = "2e4e08beaad1614da089d76b2ad639d0a4884e2e"
PARENT_SPECIFICATION_SHA256 = (
    "2e55afc109bcd65d6cf7307b5f52ba91c4c9039891e80388b26214dcce29cc57"
)
#: The new artifact; the parent is never edited.
OUTPUT_ARTIFACT_PATH = (
    _ROOT
    / "runs"
    / "replication_urban2006_minimum_benefit_groups_posthoc_v1.json"
)
#: Track M's four labels and the two post hoc labels, on every output.
LABELS: tuple[str, ...] = (*OUTPUT_LABELS, *common.POST_HOC_LABELS)
ANALYSIS_YEAR = cohort.INCOME_YEAR
#: The universe's anchor wave: G1 resolves education as of it.
ANCHOR_WAVES: tuple[int, ...] = (cohort.WAVE,)
#: The youngest age in the universe (born 1960 or earlier).
YOUNGEST_AGE = ANALYSIS_YEAR - structure.LAST_BIRTH_YEAR
#: G2's exercise-4 AIME convention (Track M's ``history_pia`` for an
#: entitlement at 62), which must equal MINT8's initial-AIME convention.
AIME_CONVENTION = g2.AIME_CONVENTIONS["exercise_4_min_benefit"]
_MINT8_AIME_CONVENTION = g2.AIME_CONVENTIONS["mint8_initial_aime"]
STATISTIC_ID = f"{tabulation.STATISTIC_ID}_by_mint8_group"
SENSITIVITY_KEY = OWN_RECEIPT_SENSITIVITY_ID
_SENSITIVITY = SENSITIVITIES[OWN_RECEIPT_SENSITIVITY_ID]
#: The sensitivity's tabulation row id, as ``pipeline`` names it.
SENSITIVITY_ROW_ID = f"{_SENSITIVITY['row']}:{OWN_RECEIPT_SENSITIVITY_ID}"
#: The pipeline result's keys the registered runner replaced, so they are
#: compared separately (the specification) or not at all (the header).
_RUNNER_REPLACED_KEYS = ("header", "specification")
#: The COLA history's repository-relative path.
COLA_HISTORY_RELATIVE_PATH = str(
    COLA_HISTORY_PATH.relative_to(COLA_HISTORY_PATH.parents[2])
)
#: The one field of the committed artifact that records where a file was
#: read rather than what was read: the registered runner recorded the COLA
#: history by the absolute path of the worktree it ran in
#: (``estimates.parameters.load_cola_history`` writes ``path.resolve()``).
#: The same record pins the file's bytes (``sha256``, ``content_sha256``),
#: which are compared exactly.
LOCATION_FIELDS: tuple[tuple[str, ...], ...] = (
    ("inputs", "source", "cola_history", "path"),
)
LOCATION_RULE = (
    "the location fields ("
    + ", ".join("$." + ".".join(keys) for keys in LOCATION_FIELDS)
    + ") are compared by their repository-relative path: an absolute "
    "path ending in /"
    + COLA_HISTORY_RELATIVE_PATH
    + " reads as "
    + COLA_HISTORY_RELATIVE_PATH
    + " on both sides, any other path is "
    "compared as written; the same record's sha256 and content_sha256 are "
    "compared exactly, and nothing else is normalized"
)

# =========================================================================
# The scheme
# =========================================================================
_POVERTY_REASON = (
    "not computed: MINT8's poverty status and household income quintile "
    "need each person's 2022 household (family) money income and, for "
    "poverty, the official threshold of the family's size and composition; "
    "Track M's inputs (min_benefit_track_m.structure.TrackMStructureInputs: "
    "the 2023 anchor, the family file's 2022 Social Security of the "
    "reference person and spouse, death records, marriage history, the "
    "labor-income panel and the design; and the receipt and next-wave "
    "labor-income frames of cohort.TrackMCohortInputs) carry neither, and "
    "this package reads no new PSID item"
)
#: MINT8 dimensions the exercise-4 breakdown does not compute, with why.
NOT_COMPUTED_DIMENSIONS: dict[str, str] = {
    "poverty_status": _POVERTY_REASON,
    "household_income_quintile": _POVERTY_REASON,
}
#: MINT8 statistics not computed, with why.
NOT_COMPUTED_STATISTICS: dict[str, dict[str, Any]] = {
    "mint8_benefit_statistics": {
        "statistics": list(g3.MINT_BENEFIT_STATISTICS),
        "reason": (
            "not computed: MINT8's benefit statistics compare each "
            "person's benefit under the option with the same person's "
            "current-law benefit.  Track M's evaluate() returns, per "
            "person, only the receipt flags receives_2..receives_5, the "
            "receipt basis and the exposure flags (min_benefit_track_m/"
            "evaluation.py evaluate); per worker record it returns the PIA "
            "under the row's PIA rule, before any option's cut or minimum "
            "(WorkerOutcome.pia), and each option's PIA "
            "(WorkerOutcome.outcomes[k].option_pia, rules.evaluate_worker), "
            "but no person-level benefit: the own benefit after the claim "
            "factor is not formed, and a spouse's or survivor's benefit is "
            "decided only as paid or not (rules.spouse_excess_paid and "
            "rules.survivor_excess_paid return booleans).  The registered "
            "options also have no current-law column: option 1 is "
            "'Reduced current law', a 12.45 percent uniform cut "
            "(policy.OPTIONS[1]).  Computing these statistics would need a "
            "person-level benefit model this breakdown does not add"
        ),
    },
    "mint8_poverty_statistics": {
        "statistics": list(g3.POVERTY_STATISTICS),
        "reason": _POVERTY_REASON,
    },
}

_AGE_NOTE = (
    "age is 2022 minus the birth year Track M resolves (the first-estimates "
    "birth-year law, cohort._universe); the universe is born 1960 or "
    "earlier (structure.LAST_BIRTH_YEAR), so every age is 62 or more and "
    "MINT8's '60–69' row holds ages 62-69 in this breakdown"
)
_QUINTILE_NOTE = (
    "the three lifetime quintiles are cut within each 10-year birth cohort "
    "of Track M's universe (lifetime_measures.ten_year_birth_cohort; "
    "MINT8: 'We calculate the AIME quintiles for each birth cohort') with "
    "the 2023 cross-section weight ER35265; the '1960–1969' cohort holds "
    "only the 1960 births here"
)
_DROPPED_NOTE = (
    "poverty status and household income quintile are dropped: Track M's "
    "inputs carry no 2022 family money income (not_computed)"
)
SCHEME = g3.derive_scheme(
    g3.MINT8_ANNUAL_WITH_LIFETIME_SCHEME,
    scheme_id="mint8_beneficiary_annual_with_lifetime__exercise4_track_m",
    title=(
        "Exercise 4 (Track M) by MINT8's annual beneficiary rows and its "
        "lifetime-earnings quintiles, without poverty and household income"
    ),
    drop=tuple(NOT_COMPUTED_DIMENSIONS),
    population=(
        "Track M's universe: persons of the PSID's 2023 wave in a "
        "responding family unit (sequence 1-20), not aged 0-5, with a "
        "positive cross-section weight ER35265, born 1960 or earlier, with "
        "a person-level 2022 Social Security amount (ER35219) above zero "
        "(M1 specification section 10)"
    ),
    notes=(_AGE_NOTE, _QUINTILE_NOTE, _DROPPED_NOTE),
)
#: The attribute column of every non-total dimension of :data:`SCHEME`.
COLUMNS_MAP: dict[str, str] = {
    "sex": "sex",
    "race_ethnicity": "race_ethnicity",
    "country_of_birth": "country_of_birth",
    "age": "age",
    "marital_status": "marital_status",
    "education": "education_years",
    "benefit_type": "benefit_type",
    "initial_aime_quintile": "initial_aime_at_62",
    "lifetime_payroll_tax_quintile": "lifetime_payroll_tax_pv_at_62",
    "lifetime_payroll_tax_quintile_shared": (
        "lifetime_payroll_tax_pv_at_62_shared"
    ),
}
_QUINTILE_PARTITION = ("birth_cohort_10y",)
_SEX_UNCLASSIFIED = ("unknown",)
_MARITAL_UNCLASSIFIED = ("no_marriage_history", "unknown")

#: Deltas this breakdown adds to Track M's named deltas.
GROUP_NAMED_DELTAS: tuple[str, ...] = (
    "a static 2022 PSID universe of beneficiaries 62 and older against "
    "MINT8's projected beneficiaries 60 and older in 2030, 2050 and 2070",
    "age 60-69 holds ages 62-69 (the universe is born 1960 or earlier)",
    "benefit type from Track M's reading of the self-reported 2022 "
    "receipt types (G33A, ER35213-ER35218) and its own worker records, not "
    "SSA's administrative beneficiary type",
    "persons without an own worker record (paid only a spouse's or "
    "survivor's benefit) have no initial AIME and are unclassified in the "
    "AIME quintile",
    "race and ethnicity and country of birth are asked of reference "
    "persons and spouses only: other family-unit members are unclassified",
    "lifetime quintiles cut within 10-year birth cohorts of this universe "
    "with the PSID cross-section weight, not over MINT8's population",
    "lifetime histories are PSID labor income of the reference person and "
    "spouse treated as covered earnings (d280), with Track M's next-wave "
    "odd years and gap rule; years as another family member are "
    "unobserved",
    "lifetime payroll taxes apply the combined OASDI rate to every dollar "
    "of labor income up to the taxable maximum; self-employment is not "
    "separated (G2's registered builder defaults)",
    "current-law poverty status and household income quintile not "
    "computed (no 2022 family money income in Track M's inputs)",
    "MINT8's benefit-change statistics not computed (no person-level "
    "benefits in Track M's evaluation)",
)


# =========================================================================
# The parent artifact
# =========================================================================
def load_parent_artifact(
    path: Path = PARENT_ARTIFACT_PATH,
    *,
    expected_sha256: str = PARENT_ARTIFACT_SHA256,
) -> common.CommittedArtifact:
    """The committed exercise-4 artifact, its bytes pinned and its sidecar
    bound (:func:`.common.load_committed_artifact`)."""

    return common.load_committed_artifact(
        path, expected_sha256=expected_sha256
    )


def check_parent_binding(
    parent: common.CommittedArtifact,
    *,
    specification_sha256: str,
) -> dict[str, Any]:
    """Refuse a parent other than Registration 17's committed run.

    Its registration pointer and registered commit must be Registration
    17's, and the M1 specification it recorded must be the file the
    re-execution's guard reads now (``specification_sha256``, the current
    file's SHA-256) and the committed one.
    """

    document = parent.document
    run = document.get("run") or {}
    recorded = document.get("specification") or {}
    if document.get("registration_pointer") != PARENT_REGISTRATION_POINTER:
        raise ValueError("the parent is not Registration 17's artifact")
    if run.get("registered_commit") != PARENT_REGISTERED_COMMIT:
        raise ValueError("the parent's registered commit is not 2e4e08be")
    if recorded.get("sha256") != PARENT_SPECIFICATION_SHA256:
        raise ValueError("the parent recorded another M1 specification")
    if specification_sha256 != PARENT_SPECIFICATION_SHA256:
        raise ValueError(
            "the M1 specification changed since Registration 17 "
            f"({specification_sha256}): the re-execution would not be the "
            "registered computation"
        )
    return {
        "registration_pointer": PARENT_REGISTRATION_POINTER,
        "registered_commit": PARENT_REGISTERED_COMMIT,
        "specification_sha256": PARENT_SPECIFICATION_SHA256,
        "specification_version": recorded.get("version"),
    }


# =========================================================================
# Re-execution
# =========================================================================
@dataclass(frozen=True, eq=False)
class TrackMReexecution:
    """The registered computation re-executed, with its person rows.

    ``result`` is what ``run_pipeline`` returns (``pipeline.run_track_m``
    plus both cohorts' ``cohort_structure``); ``evaluations`` and
    ``tabulations`` are every registered row's ``evaluate`` and
    ``tabulate_track_m``; ``sensitivity_*`` are d430's.
    """

    cohort_inputs: Any
    cohort: cohort.TrackMCohort
    cohort_sensitivity: cohort.TrackMCohort
    records: TrackMInputs
    records_sensitivity: TrackMInputs
    result: Mapping[str, Any]
    evaluations: Mapping[str, Evaluation]
    tabulations: Mapping[str, Mapping[str, Any]]
    sensitivity_evaluation: Evaluation
    sensitivity_tabulation: Mapping[str, Any]
    data_provenance: str
    registration_pointer: str | None


def reexecute_track_m(
    cohort_inputs: Any,
    parameters: TrackMParameters,
    *,
    cola_rates: Mapping[int, float],
    data_provenance: str,
    registration_pointer: str | None,
    provenance_kind: str,
    source: Mapping[str, Any],
) -> TrackMReexecution:
    """``run_pipeline``'s computation on ``cohort_inputs``, and the rows.

    Mirrors ``scripts/run_track_m_registered.py``'s ``run_pipeline`` step
    for step (both cohorts, ``careers.build_track_m_inputs`` with
    ``provenance_kind`` and ``source``, ``pipeline.run_track_m`` with the
    sensitivity, the two ``cohort_structure`` blocks) and then evaluates
    and tabulates every registered row and d430's sensitivity with the
    unchanged ``evaluate`` and ``tabulate_track_m``, as ``run_track_m``
    does inside.  The registered path passes ``registered_real``,
    Registration 17's pointer, ``psid_files`` and
    ``{"cola_history": cola.provenance}``.
    """

    built = cohort.build_cohort(cohort_inputs)
    built_sensitivity = cohort.build_cohort(
        cohort_inputs,
        own_receipt_reading=OWN_RECEIPT_PRE62_UNKNOWN_OR_OTHER_UNOBSERVED,
    )

    def records_of(built_cohort: cohort.TrackMCohort) -> TrackMInputs:
        return careers.build_track_m_inputs(
            built_cohort,
            earnings=cohort_inputs.earnings,
            prior_year=cohort_inputs.prior_year_labor,
            params=parameters.params,
            cola_rates=cola_rates,
            provenance_kind=provenance_kind,
            source=dict(source),
        )

    records = records_of(built)
    records_sensitivity = records_of(built_sensitivity)
    result = pipeline.run_track_m(
        records,
        parameters,
        data_provenance=data_provenance,
        registration_pointer=registration_pointer,
        own_receipt_sensitivity=records_sensitivity,
    )
    result["cohort_structure"] = cohort.cohort_structure(built)
    result["sensitivities"][SENSITIVITY_KEY]["cohort_structure"] = (
        cohort.cohort_structure(built_sensitivity)
    )
    evaluations: dict[str, Evaluation] = {}
    tabulations: dict[str, Mapping[str, Any]] = {}
    for row in REGISTERED_ROWS:
        evaluation = evaluate(records, policy_for_row(row), parameters)
        evaluations[row] = evaluation
        tabulations[row] = tabulation.tabulate_track_m(
            evaluation.rows,
            row_id=row,
            data_provenance=data_provenance,
            design=records.design,
            registration_pointer=registration_pointer,
            labels=OUTPUT_LABELS,
        )
    sensitivity_evaluation = evaluate(
        records_sensitivity, policy_for_row(_SENSITIVITY["row"]), parameters
    )
    sensitivity_tabulation = tabulation.tabulate_track_m(
        sensitivity_evaluation.rows,
        row_id=SENSITIVITY_ROW_ID,
        data_provenance=data_provenance,
        design=records_sensitivity.design,
        registration_pointer=registration_pointer,
        labels=OUTPUT_LABELS,
        scored=False,
    )
    return TrackMReexecution(
        cohort_inputs=cohort_inputs,
        cohort=built,
        cohort_sensitivity=built_sensitivity,
        records=records,
        records_sensitivity=records_sensitivity,
        result=result,
        evaluations=evaluations,
        tabulations=tabulations,
        sensitivity_evaluation=sensitivity_evaluation,
        sensitivity_tabulation=sensitivity_tabulation,
        data_provenance=data_provenance,
        registration_pointer=registration_pointer,
    )


_ABSENT = object()


def _check(
    name: str, committed: Any, recomputed: Any
) -> common.ReproductionCheck:
    if committed is _ABSENT:
        return common.ReproductionCheck(
            name, 0, ("$ (absent from the committed artifact)",)
        )
    return common.compare_exact(name, committed, recomputed)


def _dig(document: Mapping[str, Any], *keys: str) -> Any:
    value: Any = document
    for key in keys:
        if not isinstance(value, Mapping) or key not in value:
            return _ABSENT
        value = value[key]
    return value


def parameter_check(
    parameters: TrackMParameters, parent: Mapping[str, Any]
) -> common.ReproductionCheck:
    """The parameters' provenance against the committed ``parameters``."""

    return _check(
        "parameters", _dig(parent, "parameters"), parameters.source()
    )


def psid_files_check(
    cohort_inputs: Any, parent: Mapping[str, Any]
) -> common.ReproductionCheck:
    """The PSID files read against the committed run's SHA-256 map."""

    key = pipeline.PSID_FILES_SOURCE_KEY
    committed = _dig(parent, "inputs", "source")
    committed = _ABSENT if committed is _ABSENT else dict(committed).get(key)
    return _check(
        f"inputs.source.{key}",
        committed,
        dict(getattr(cohort_inputs, "provenance", {}) or {}).get(key),
    )


def _recorded(document: Mapping[str, Any], keys: Sequence[str]) -> Any:
    """The leaf at ``keys``, or ``None`` where the document has none."""

    value = _dig(document, *keys)
    return None if value is _ABSENT else copy.deepcopy(value)


def relative_location(path: Any) -> Any:
    """``path`` as :data:`LOCATION_RULE` compares it."""

    if isinstance(path, str) and path.startswith("/"):
        if path.endswith("/" + COLA_HISTORY_RELATIVE_PATH):
            return COLA_HISTORY_RELATIVE_PATH
    return path


def located(document: Any) -> Any:
    """``document`` (a whole artifact) with its :data:`LOCATION_FIELDS`
    read by :func:`relative_location`; every other leaf unchanged."""

    if not isinstance(document, Mapping):
        return document
    out = copy.deepcopy(dict(document))
    for keys in LOCATION_FIELDS:
        node: Any = out
        for key in keys[:-1]:
            node = node.get(key) if isinstance(node, dict) else None
        if isinstance(node, dict) and keys[-1] in node:
            node[keys[-1]] = relative_location(node[keys[-1]])
    return out


def reproduction_checks(
    reexecution: TrackMReexecution, parent: Mapping[str, Any]
) -> tuple[common.ReproductionCheck, ...]:
    """Every recomputed block against the committed artifact, exactly.

    One check per key of the re-executed pipeline result (every key but
    ``header`` and ``specification``, which the registered runner
    replaced), and one per registered row's and the sensitivity's
    tabulation and diagnostics from the rows the groups use.  Both sides
    pass through :func:`located` first (:data:`LOCATION_RULE`).
    """

    checks = []
    committed = located(parent)
    recomputed = located(dict(reexecution.result))
    for key, value in recomputed.items():
        if key in _RUNNER_REPLACED_KEYS:
            continue
        checks.append(_check(f"pipeline.{key}", _dig(committed, key), value))
    for row in REGISTERED_ROWS:
        evaluation = reexecution.evaluations[row]
        checks.append(
            _check(
                f"group_rows.{row}.tabulation",
                _dig(parent, "rows", row, "tabulation"),
                reexecution.tabulations[row],
            )
        )
        checks.append(
            _check(
                f"group_rows.{row}.diagnostics",
                _dig(parent, "rows", row, "diagnostics"),
                evaluation.diagnostics,
            )
        )
    checks.append(
        _check(
            f"group_rows.{SENSITIVITY_KEY}.tabulation",
            _dig(parent, "sensitivities", SENSITIVITY_KEY, "tabulation"),
            reexecution.sensitivity_tabulation,
        )
    )
    checks.append(
        _check(
            f"group_rows.{SENSITIVITY_KEY}.diagnostics",
            _dig(parent, "sensitivities", SENSITIVITY_KEY, "diagnostics"),
            reexecution.sensitivity_evaluation.diagnostics,
        )
    )
    return tuple(checks)


# =========================================================================
# Person attributes
# =========================================================================
#: How Track M's 2022 receipt maps to MINT8's four benefit types, in the
#: order :func:`benefit_type_2022` applies them.
BENEFIT_TYPE_RULES: tuple[str, ...] = (
    "inputs, all Track M's own: the six G33A 'whether Social Security "
    "type' items of income year 2022 (ER35213 disability, ER35214 "
    "retirement, ER35215 survivor, ER35216 dependent of disabled, ER35217 "
    "dependent of retired, ER35218 other), decoded as Track M's cohort "
    "decodes them (cohort._anchor_types: 1 mentioned, 5 not mentioned, any "
    "other code unknown); Track M's paid_own_worker_benefit (the 2022 "
    "receipt is own receipt by cohort.observation and the person has an "
    "own worker record); and the basis of that record "
    "(cohort.classify_own_record: 'disability' when the first own receipt "
    "mentions disability or precedes the year of attaining 62, otherwise "
    "'old_age')",
    "1. survivor and a dependent type both mentioned: unclassified "
    "(survivor_and_dependent_mentioned)",
    "2. survivor mentioned: 'Widow(er) (includes dually entitled)', "
    "whatever worker type is also mentioned (the item does not say whose "
    "survivor; at 62 and older it is read as a widow(er)'s benefit)",
    "3. dependent of disabled or of retired mentioned: 'Spousal (includes "
    "dually entitled)', whatever worker type is also mentioned (the item "
    "does not say whose dependent; at 62 and older it is read as a "
    "spouse's benefit)",
    "4. no auxiliary type mentioned but one of the three auxiliary items "
    "(survivor, dependent of disabled, dependent of retired) unknown: "
    "unclassified (auxiliary_item_unknown), since MINT8's 'only' cannot be "
    "established",
    "5. otherwise the benefit is read as the person's own worker benefit; "
    "a person Track M does not pay their own worker benefit is "
    "unclassified (no_own_worker_benefit)",
    "6. the worker type: disability when disability is mentioned and "
    "retirement is not; retirement when retirement is mentioned and "
    "disability is not; when both or neither are mentioned (an 'other' or "
    "unknown type, which Track M's scored reading counts as own receipt, "
    "cos d430), the basis of Track M's own worker record",
    "7. disability: 'Disabled worker only' when the person is under the "
    "full retirement age in 2022 (12 times the whole-year age 2022 minus "
    "the birth year, Track M's claim-age convention, below the oracle's "
    "params.fra_months of the birth year); at or over it 'Retired worker "
    "only' (MINT8: 'Disabled workers convert to retired workers at FRA')",
    "8. retirement: 'Retired worker only'",
)
_UNCLASSIFIED_PREFIX = "unclassified:"
_AUXILIARY_TYPES = frozenset(ssr.AUXILIARY_TYPES)
_DEPENDENT_TYPES = frozenset({"dependent_of_disabled", "dependent_of_retired"})
_OWN_RECORD_BASES = (cohort.BASIS_OLD_AGE, cohort.BASIS_DISABILITY)


def benefit_type_2022(
    types: Mapping[str, Any],
    *,
    birth_year: int,
    paid_own_worker_benefit: bool,
    own_record_basis: str | None,
    params: SSAParameters,
) -> str:
    """One person's MINT8 benefit-type code (:data:`BENEFIT_TYPE_RULES`).

    ``types`` maps each of the six SS types to True (mentioned), False
    (not mentioned) or None (unknown), as ``cohort._anchor_types`` decodes
    the 2022 items; ``paid_own_worker_benefit`` and ``own_record_basis``
    (``None`` without an own record) are Track M's.  Returns a G3
    ``benefit_type`` code or ``unclassified:<reason>``.
    """

    unknown = {name for name in ssr.SS_TYPES if types.get(name) is None}
    mentioned = {name for name in ssr.SS_TYPES if types.get(name) is True}
    if paid_own_worker_benefit and own_record_basis not in _OWN_RECORD_BASES:
        raise ValueError(
            "a person paid their own worker benefit has an old-age or "
            f"disability own record, not {own_record_basis!r}"
        )
    dependent = mentioned & _DEPENDENT_TYPES
    if "survivor" in mentioned and dependent:
        return f"{_UNCLASSIFIED_PREFIX}survivor_and_dependent_mentioned"
    if "survivor" in mentioned:
        return "widower"
    if dependent:
        return "spousal"
    if unknown & _AUXILIARY_TYPES:
        return f"{_UNCLASSIFIED_PREFIX}auxiliary_item_unknown"
    if not paid_own_worker_benefit:
        return f"{_UNCLASSIFIED_PREFIX}no_own_worker_benefit"
    worker, _ = _own_worker_type(mentioned, own_record_basis)
    if worker == cohort.BASIS_DISABILITY:
        months = 12 * (ANALYSIS_YEAR - int(birth_year))
        if months < params.fra_months(int(birth_year)):
            return "disabled_worker_only"
    return "retired_worker_only"


def _own_worker_type(
    mentioned: set[str] | frozenset[str], own_record_basis: str | None
) -> tuple[str, str]:
    """``(worker type, what decided it)`` (:data:`BENEFIT_TYPE_RULES` 6).

    The type is ``"disability"`` or ``"old_age"``; it is decided by the
    2022 mentions when exactly one worker type is mentioned, and by Track
    M's own-record basis otherwise.
    """

    retirement = "retirement" in mentioned
    disability = "disability" in mentioned
    if disability != retirement:
        return (
            cohort.BASIS_DISABILITY if disability else cohort.BASIS_OLD_AGE,
            "2022_mentions",
        )
    return (
        (
            cohort.BASIS_DISABILITY
            if own_record_basis == cohort.BASIS_DISABILITY
            else cohort.BASIS_OLD_AGE
        ),
        "own_record_basis",
    )


def _benefit_types(
    built: cohort.TrackMCohort, cohort_inputs: Any, params: SSAParameters
) -> tuple[list[str], dict[str, Any]]:
    """Every universe person's benefit type, in ``built.persons`` order.

    Each person's 2022 observation is rebuilt from the anchor exactly as
    ``cohort.build_cohort`` builds it, and must reproduce the cohort's
    ``types_2022``, ``status_2022`` and ``paid_own_worker_benefit``
    (refused otherwise).
    """

    anchor = cohort_inputs.anchor.set_index("person_id")
    bases = dict(
        zip(built.records["record_id"], built.records["basis"], strict=True)
    )
    codes = []
    by_rule: Counter[str] = Counter()
    for pid, birth, types_2022, status_2022, paid, own in zip(
        built.persons["person_id"],
        built.persons["birth_year"],
        built.persons["types_2022"],
        built.persons["status_2022"],
        built.persons["paid_own_worker_benefit"],
        built.persons["own_record_id"],
        strict=True,
    ):
        types = cohort._anchor_types(anchor.loc[int(pid)])
        observed = cohort.observation(
            ANALYSIS_YEAR, receipt=True, types=types, source="individual"
        )
        own_id = None if own is None or pd.isna(own) else str(own)
        if (
            ",".join(sorted(observed.types)) != str(types_2022)
            or observed.status != str(status_2022)
            or bool(paid) != (observed.status == cohort.OWN and bool(own_id))
        ):
            raise ValueError(
                f"person {pid}: the 2022 receipt rebuilt from the anchor is "
                "not the cohort's"
            )
        basis = None if own_id is None else str(bases[own_id])
        code = benefit_type_2022(
            types,
            birth_year=int(birth),
            paid_own_worker_benefit=bool(paid),
            own_record_basis=basis,
            params=params,
        )
        if code in ("retired_worker_only", "disabled_worker_only"):
            mentioned = {name for name, value in types.items() if value}
            worker, decided_by = _own_worker_type(mentioned, basis)
            by_rule[f"worker_type_from_{decided_by}"] += 1
            if (
                code == "retired_worker_only"
                and worker == cohort.BASIS_DISABILITY
            ):
                by_rule["disability_at_or_over_fra_read_as_retired"] += 1
        codes.append(code)
    counts = Counter(codes)
    return codes, {
        "rules": list(BENEFIT_TYPE_RULES),
        "n_by_code": dict(sorted(counts.items())),
        "n_by_rule": dict(sorted(by_rule.items())),
    }


def _careers_rows(
    pid: int, history: coverage.OneHistory
) -> list[dict[str, Any]]:
    observed = set(history.observed_years)
    next_wave = set(history.next_wave_years)
    rows = []
    for year, value in sorted(history.values.items()):
        rows.append(
            {
                "person_id": int(pid),
                "year": int(year),
                "earnings": float(value),
                "provenance": (
                    "observed"
                    if year in observed
                    else "next_wave" if year in next_wave else "imputed"
                ),
            }
        )
    return rows


_CAREER_COLUMNS = ["person_id", "year", "earnings", "provenance"]


def initial_aime_measure(
    reexecution: TrackMReexecution, params: SSAParameters
) -> tuple[g2.MeasureResult, dict[str, Any]]:
    """G2's initial AIME at 62 over the MS0 own records' one histories.

    Returns the measure and its checks: the persons without an own record,
    and the exercise-4 identity (an old-age record entitled in the year of
    attaining 62 has the same AIME at 62 as MS0's ``history_pia.aime``;
    refused otherwise).
    """

    mint8 = (
        _MINT8_AIME_CONVENTION.computation_years,
        _MINT8_AIME_CONVENTION.last_earnings_age,
    )
    if (
        AIME_CONVENTION.computation_years,
        AIME_CONVENTION.last_earnings_age,
    ) != mint8:
        raise ValueError(
            "G2's exercise-4 AIME convention is no longer MINT8's initial "
            "AIME convention (statutory computation years, earnings through "
            "the year of attaining 61)"
        )
    persons = reexecution.cohort.persons
    ms0 = reexecution.evaluations["MS0"]
    rows: list[dict[str, Any]] = []
    own_ids: dict[int, str] = {}
    for pid, own in zip(
        persons["person_id"], persons["own_record_id"], strict=True
    ):
        if own is None or pd.isna(own):
            continue
        own_ids[int(pid)] = str(own)
        rows.extend(_careers_rows(int(pid), ms0.workers[str(own)].history))
    measure = g2.initial_aime_at_62(
        pd.DataFrame(rows, columns=_CAREER_COLUMNS),
        persons[["person_id", "birth_year"]],
        params,
        analysis_year=ANALYSIS_YEAR,
        convention=AIME_CONVENTION,
    )
    by_person = measure.frame.set_index("person_id")
    compared = 0
    for pid, record_id in own_ids.items():
        outcome = ms0.workers[record_id]
        years = outcome.years
        if (
            years.basis != "old_age"
            or years.window_year != years.birth_year + 62
            or by_person.loc[pid, "status"] != g2.COMPUTED
        ):
            continue
        aime = by_person.loc[pid, "aime"]
        if outcome.history_pia.aime is None or not (
            float(aime) == float(outcome.history_pia.aime)
        ):
            raise ValueError(
                f"person {pid}: G2's AIME at 62 is not MS0's AIME for an "
                "old-age entitlement at 62"
            )
        compared += 1
    no_rows = sum(
        1
        for pid, record_id in own_ids.items()
        if by_person.loc[pid, "status"] != g2.COMPUTED
    )
    return measure, {
        "persons_without_own_record": int(len(persons) - len(own_ids)),
        "own_records_not_computed": int(no_rows),
        "own_records_not_computed_note": (
            "G2 leaves an own record whose history has no year through the "
            "year of attaining 61 not computed (earnings unobserved, not "
            "zero), where MS0's oracle reads the empty history as zeros; "
            "such persons are unclassified in the AIME quintile"
        ),
        "history": (
            "the MS0 evaluation's one history of the person's own worker "
            "record (WorkerOutcome.history: observed panel years, "
            "next-wave odd years, gap-rule years), through the record's "
            "section 4a last year"
        ),
        "convention": {
            "name": AIME_CONVENTION.name,
            "equals_mint8_initial_aime_convention": True,
            "rule": (
                "G2's exercise_4_min_benefit and mint8_initial_aime "
                "conventions both read statutory computation years and "
                "earnings through the year of attaining 61 (checked)"
            ),
        },
        "identity_with_ms0_aime": {
            "rule": (
                "an old-age own record entitled in the year of attaining 62 "
                "whose AIME G2 computes has G2's AIME at 62 equal to MS0's "
                "history_pia.aime"
            ),
            "n_compared": compared,
            "all_equal": True,
        },
        "own_records_by_basis": dict(
            sorted(
                Counter(
                    ms0.workers[record].years.basis
                    for record in own_ids.values()
                ).items()
            )
        ),
    }


def lifetime_careers(
    cohort_inputs: Any, person_ids: Sequence[int]
) -> pd.DataFrame:
    """Each person's lifetime history through 2022 by Track M's own rule.

    ``careers.observed_histories`` (the labor-income panel, years through
    2022) and ``prior_year_labor_income.next_wave_histories`` (observed
    next-wave odd years), joined by ``coverage.one_history`` with
    ``last_year=2022`` and MS0's policy (the gap rule), exactly the
    sources and rule a worker record's history reads, but not cut at the
    record's last year: G2's payroll taxes are lifetime taxes.
    """

    ids = {int(pid) for pid in person_ids}
    panel = careers.observed_histories(cohort_inputs.earnings, ids)
    prior = cohort_inputs.prior_year_labor
    next_wave = pyl.next_wave_histories(prior[prior["person_id"].isin(ids)])
    policy = policy_for_row("MS0")
    rows: list[dict[str, Any]] = []
    for pid in sorted(ids):
        history = coverage.one_history(
            panel.get(pid, {}),
            next_wave.get(pid, {}),
            last_year=ANALYSIS_YEAR,
            policy=policy,
        )
        rows.extend(_careers_rows(pid, history))
    return pd.DataFrame(rows, columns=_CAREER_COLUMNS)


def _marriage_inputs(
    cohort_inputs: Any, universe: set[int]
) -> tuple[pd.DataFrame, set[int], set[int]]:
    """Marriage episodes of the universe and of every spouse they had."""

    history = cohort_inputs.structure_inputs.marriage_history
    mine = history[history["person_id"].isin(universe)]
    # The episodes Track M's cohort reads (cohort._marital_states).
    own_episodes = psid2010._episodes_with_separation(mine)
    spouses = {
        int(spouse) for spouse in own_episodes["spouse_person_id"].dropna()
    }
    everyone = universe | spouses
    episodes = psid2010._episodes_with_separation(
        history[history["person_id"].isin(everyone)]
    )
    with_history = {int(pid) for pid in mine["person_id"]}
    return episodes, spouses, with_history


@dataclass(frozen=True, eq=False)
class PersonAttributes:
    """The group attributes of every universe person, in row order.

    ``frame`` has ``person_id`` (the evaluation rows' string id),
    ``weight``, one column per :data:`COLUMNS_MAP` value and
    ``birth_cohort_10y``; ``unclassified_codes`` the declared codes per
    categorical dimension; ``provenance`` every source and rule.
    """

    frame: pd.DataFrame
    unclassified_codes: Mapping[str, tuple[str, ...]]
    provenance: Mapping[str, Any]


def _files_agree(
    side_frame: Mapping[str, Any], cohort_inputs: Any
) -> dict[str, Any]:
    """Files both readers record must be the same bytes (refused if not)."""

    side = dict(
        (side_frame.get("inputs") or {}).get("psid_files_sha256") or {}
    )
    track_m = dict(
        (getattr(cohort_inputs, "provenance", {}) or {}).get(
            pipeline.PSID_FILES_SOURCE_KEY
        )
        or {}
    )
    shared = sorted(set(side) & set(track_m))
    differ = [name for name in shared if side[name] != track_m[name]]
    if differ:
        raise ValueError(
            f"the side frame and Track M read different bytes of {differ}"
        )
    return {"files_read_by_both": shared, "all_equal": True}


def person_attributes(
    reexecution: TrackMReexecution,
    parameters: TrackMParameters,
    side_frame: g1.GroupAttributes,
    *,
    tax_rates: Any,
    interest_rates: Any,
) -> PersonAttributes:
    """Every group attribute of every universe person (module docstring).

    ``side_frame`` is G1's frame for the universe's person ids (int).
    Refuses a side frame that does not hold exactly the universe, persons
    out of the evaluation rows' order, files the side frame and Track M
    read with different bytes, a G1/G3 education disagreement and a
    broken AIME identity.
    """

    built = reexecution.cohort
    persons = built.persons
    rows = reexecution.evaluations["MS0"].rows
    ids = [int(pid) for pid in persons["person_id"]]
    if [str(pid) for pid in ids] != rows["person_id"].tolist():
        raise ValueError("the cohort's persons are not the rows' persons")
    frame = side_frame.frame.set_index("person_id")
    if sorted(int(pid) for pid in frame.index) != sorted(ids):
        raise ValueError(
            "the side frame must hold exactly the universe's persons"
        )
    frame = frame.loc[ids].reset_index()
    files_record = _files_agree(
        side_frame.provenance, reexecution.cohort_inputs
    )
    params = parameters.params
    dimensions = {d.key: d for d in SCHEME.dimensions}
    race = common.side_frame_codes(frame, dimensions["race_ethnicity"])
    country = common.side_frame_codes(frame, dimensions["country_of_birth"])
    education_check = common.education_agreement(
        frame, dimensions["education"]
    )
    marital = common.marital_codes(
        persons["marital_status_2022"].tolist(),
        unclassified=_MARITAL_UNCLASSIFIED,
    )
    benefit, benefit_record = _benefit_types(
        built, reexecution.cohort_inputs, params
    )
    universe = set(ids)
    aime, aime_checks = initial_aime_measure(reexecution, params)
    episodes, spouses, with_history = _marriage_inputs(
        reexecution.cohort_inputs, universe
    )
    lifetime = lifetime_careers(
        reexecution.cohort_inputs, sorted(universe | spouses)
    )
    person_frame = persons[["person_id", "birth_year"]]
    own_tax = g2.lifetime_payroll_tax_pv_at_62(
        lifetime,
        person_frame,
        params,
        shared=False,
        rates=tax_rates,
        interest=interest_rates,
    )
    shared_tax = g2.lifetime_payroll_tax_pv_at_62(
        lifetime,
        person_frame,
        params,
        shared=True,
        rates=tax_rates,
        interest=interest_rates,
        marriage_episodes=episodes,
        separated_is_married=True,
        marriage_history_person_ids=with_history,
    )

    ages = common.age_in_year(persons["birth_year"], ANALYSIS_YEAR)
    if min(ages) < YOUNGEST_AGE:
        raise ValueError(
            f"an age under {YOUNGEST_AGE}: the universe is born "
            f"{structure.LAST_BIRTH_YEAR} or earlier"
        )

    def measure(result: g2.MeasureResult, column: str) -> list[float]:
        values = result.frame.set_index("person_id")[column]
        return [float(values.loc[pid]) for pid in ids]

    out = pd.DataFrame(
        {
            "person_id": rows["person_id"].to_numpy(),
            "weight": rows["weight"].to_numpy(dtype=float),
            "sex": rows["sex"].tolist(),
            "race_ethnicity": list(race.codes),
            "country_of_birth": list(country.codes),
            "age": list(ages),
            "marital_status": list(marital.codes),
            "education_years": pd.array(
                common.education_years(frame), dtype="Int64"
            ),
            "benefit_type": benefit,
            "initial_aime_at_62": measure(aime, "aime"),
            "lifetime_payroll_tax_pv_at_62": measure(own_tax, "pv_at_62"),
            "lifetime_payroll_tax_pv_at_62_shared": measure(
                shared_tax, "pv_at_62"
            ),
            "birth_cohort_10y": g2.ten_year_birth_cohort(
                persons["birth_year"].reset_index(drop=True)
            ).to_numpy(),
        }
    )
    present_sex = tuple(
        code for code in _SEX_UNCLASSIFIED if code in set(out["sex"])
    )
    unclassified = {
        "sex": present_sex,
        "race_ethnicity": race.unclassified_codes,
        "country_of_birth": country.unclassified_codes,
        "marital_status": marital.unclassified_codes,
        "benefit_type": tuple(
            sorted(
                {code for code in benefit if code.startswith("unclassified:")}
            )
        ),
    }
    provenance = {
        "person_key": (
            "person_id: Track M's evaluation rows' id (str of the cohort's "
            "integer person id); the side frame and the lifetime measures "
            "are joined on the integer id"
        ),
        "fixed_across_rows": (
            "attributes are computed once, from the scored reading's cohort "
            "and MS0's histories, and used for every registered row and for "
            "d430's sensitivity (same universe, same person order)"
        ),
        "sex": (
            "Track M's sex (ER32000 through the death records); 'unknown' "
            "(code 9) unclassified, as Track M counts it in All only"
        ),
        "age": _AGE_NOTE,
        "marital_status": {
            "rule": marital.rule,
            "source": (
                "Track M's marital_status_2022 (cohort._marital_states: "
                "psid2010.marital_state_at at the end of 2022, separated "
                "counted as married by default)"
            ),
        },
        "race_ethnicity": {"rule": race.rule},
        "country_of_birth": {"rule": country.rule},
        "education": {
            "rule": (
                "G1's education_years (the most recent reported years of "
                "schooling at or before the 2023 wave) in G3's MINT8 bands"
            ),
            "agreement_with_g1_label": education_check,
        },
        "benefit_type": benefit_record,
        "side_frame": copy.deepcopy(dict(side_frame.provenance)),
        "side_frame_files": files_record,
        "initial_aime_at_62": {
            **aime_checks,
            "measure_provenance": aime.provenance,
        },
        "lifetime_payroll_tax_pv_at_62": {
            "history": (
                "lifetime_careers: Track M's observed panel and next-wave "
                "odd years through 2022 with MS0's gap rule, for the "
                "universe and every spouse in their marriage histories"
            ),
            "n_persons_with_history": int(lifetime["person_id"].nunique()),
            "measure_provenance": own_tax.provenance,
        },
        "lifetime_payroll_tax_pv_at_62_shared": {
            "measure_provenance": shared_tax.provenance,
        },
        "quintile_partition": {
            "columns": list(_QUINTILE_PARTITION),
            "rule": _QUINTILE_NOTE,
            "persons_by_cohort": {
                str(key): int(value)
                for key, value in sorted(
                    Counter(out["birth_cohort_10y"]).items()
                )
            },
        },
    }
    return PersonAttributes(
        frame=out,
        unclassified_codes=unclassified,
        provenance=provenance,
    )


def assign(attributes: PersonAttributes) -> g3.GroupAssignment:
    """G3's assignment of every person to :data:`SCHEME`'s categories."""

    quintiles = {
        dimension.key: _QUINTILE_PARTITION
        for dimension in SCHEME.dimensions
        if dimension.kind == g3.QUINTILE
    }
    return g3.assign_groups(
        attributes.frame,
        SCHEME,
        COLUMNS_MAP,
        key_columns=("person_id",),
        weight_column="weight",
        quintile_partitions=quintiles,
        unclassified_codes={
            key: codes
            for key, codes in attributes.unclassified_codes.items()
            if codes
        },
    )


def quintile_rule_sensitivity(
    attributes: PersonAttributes, assignment: g3.GroupAssignment
) -> dict[str, Any]:
    """Persons whose quintile G2's midpoint rule would place differently.

    The cells use G3's rule (thresholds at the weighted 20/40/60/80th
    percentiles; a value equal to a threshold takes the lower quintile).
    G2's ``weighted_quintiles`` places a value by the midpoint of its
    cumulative weight span.  The two differ only for persons whose weight
    straddles a boundary; this counts them per dimension.  Diagnostic
    only: no cell uses G2's rule.
    """

    out = {}
    frame = attributes.frame
    for dimension in SCHEME.dimensions:
        if dimension.kind != g3.QUINTILE:
            continue
        values = pd.Series(
            frame[COLUMNS_MAP[dimension.key]].to_numpy(dtype=float)
        )
        g2_labels = g2.weighted_quintiles(
            values,
            pd.Series(frame["weight"].to_numpy(dtype=float)),
            by=pd.Series(frame["birth_cohort_10y"].to_numpy()),
        ).astype(str)
        long = assignment.long[assignment.long["dimension"] == dimension.key]
        g3_labels = long.sort_values("row_id")["label"].to_numpy()
        present = values.notna().to_numpy()
        differ = int(
            (g2_labels.to_numpy()[present] != g3_labels[present]).sum()
        )
        out[dimension.key] = {
            "n_with_measure": int(present.sum()),
            "n_placed_differently_by_g2_midpoint_rule": differ,
        }
    return {
        "rule": (
            "cells use G3's quintile rule; G2's midpoint rule "
            "(lifetime_measures.weighted_quintiles) is computed only to "
            "count the persons the two rules place differently"
        ),
        "by_dimension": out,
    }


# =========================================================================
# Cells
# =========================================================================
def _breakdown_keys() -> list[tuple[str, str, int]]:
    keys = [
        (row, row, number)
        for row in REGISTERED_ROWS
        for number in TABLE6_OPTIONS
    ]
    keys.extend(
        (SENSITIVITY_KEY, SENSITIVITY_ROW_ID, number)
        for number in TABLE6_OPTIONS
    )
    return keys


def tabulate_breakdowns(
    reexecution: TrackMReexecution,
    assignment: g3.GroupAssignment,
    *,
    data_provenance: str,
    registration_pointer: str | None,
    parent_sha256: str | None,
) -> dict[tuple[str, int], g3.GroupBreakdownResult]:
    """G3's share breakdown for every registered row, option and d430.

    ``tabulate_share_breakdown`` over the row's evaluation rows with
    ``receives_<k>`` as the indicator, the design frame of the records and
    G3's defaults (Track M's floor seeds 0-4, family units linked through
    persons).  A real-data breakdown carries the new registration's
    pointer, Track M's labels and the post hoc labels.
    """

    out = {}
    for key, row_id, number in _breakdown_keys():
        if key == SENSITIVITY_KEY:
            rows = reexecution.sensitivity_evaluation.rows
            design = reexecution.records_sensitivity.design
        else:
            rows = reexecution.evaluations[key].rows
            design = reexecution.records.design
        out[(key, number)] = g3.tabulate_share_breakdown(
            rows,
            assignment,
            indicator_column=f"receives_{number}",
            design=design,
            data_provenance=data_provenance,
            registration_pointer=registration_pointer,
            labels=OUTPUT_LABELS,
            post_hoc_labels=common.POST_HOC_LABELS,
            statistic_id=STATISTIC_ID,
            upstream={
                "row": row_id,
                "option": int(number),
                "scored": False,
                "parent_artifact_sha256": parent_sha256,
            },
        )
    return out


_SEX_CELLS = (
    ("total", "total", "all"),
    ("sex", "female", "women"),
    ("sex", "male", "men"),
)


def _track_m_cell(table: Mapping[str, Any], number: int, row: str) -> dict:
    for cell in table["cells"]:
        if cell["option"] == number and cell["row"] == row:
            return cell
    raise KeyError((number, row))


def _comparable_track_m(cell: Mapping[str, Any]) -> dict[str, Any]:
    out = {"defined": cell["defined"], "floor": cell["floor"]}
    if cell["defined"]:
        out.update(
            share_percent=cell["share_percent"],
            weighted_n=cell["weighted_n"],
            unweighted_n=cell["unweighted_n"],
            weighted_receiving=cell["weighted_receiving"],
            unweighted_receiving=cell["unweighted_receiving"],
            design_se=cell["design_se"],
        )
    return out


def _comparable_g3(cell: g3.GroupCell) -> dict[str, Any]:
    statistic = cell.statistic(g3.SHARE)
    out = {
        "defined": statistic.defined,
        "floor": statistic.uncertainty["floor"],
    }
    if statistic.defined:
        out.update(
            share_percent=statistic.value,
            weighted_n=statistic.weighted_n,
            unweighted_n=statistic.unweighted_n,
            weighted_receiving=cell.counts["weighted_indicator"],
            unweighted_receiving=cell.counts["numerators"]["n_indicator"],
            design_se=statistic.uncertainty["design_se"],
        )
    return out


def consistency_checks(
    reexecution: TrackMReexecution,
    breakdowns: Mapping[tuple[str, int], g3.GroupBreakdownResult],
) -> tuple[common.ReproductionCheck, ...]:
    """G3's Total/Female/Male cells against Track M's All/Women/Men.

    For every breakdown: the share, the weighted and unweighted counts of
    the cell and of those receiving, the design-based standard error and
    the floor must equal ``tabulate_track_m``'s cell exactly (which in
    turn equals the committed artifact's).
    """

    checks = []
    for (key, number), result in breakdowns.items():
        table = (
            reexecution.sensitivity_tabulation
            if key == SENSITIVITY_KEY
            else reexecution.tabulations[key]
        )
        for dimension, category, row in _SEX_CELLS:
            checks.append(
                common.compare_exact(
                    f"{key}.option_{number}.{dimension}.{category}",
                    _comparable_track_m(_track_m_cell(table, number, row)),
                    _comparable_g3(result.cell(dimension, category)),
                )
            )
    return tuple(checks)


# =========================================================================
# The run
# =========================================================================
_SHARED_RESULT_KEYS = (
    "schema_version",
    "kind",
    "statistic_id",
    "data_provenance",
    "registration_pointer",
    "labels",
    "post_hoc_labels",
    "scheme",
    "statistics",
    "statistic_definitions",
    "assignment",
)


def _factor(
    breakdowns: Mapping[tuple[str, int], g3.GroupBreakdownResult],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Blocks shared by every breakdown once, and each breakdown's cells.

    Refuses (rather than drops) a shared block that differs between
    breakdowns, so the factoring is lossless.
    """

    shared: dict[str, Any] | None = None
    conventions: dict[str, Any] | None = None
    cells: dict[str, Any] = {}
    for (key, number), result in breakdowns.items():
        document = result.as_dict()
        mine = {name: document[name] for name in _SHARED_RESULT_KEYS}
        convention = dict(document["conventions"])
        indicator = convention.pop("indicator_column")
        if shared is None:
            shared, conventions = mine, convention
        else:
            differing = [
                check.name
                for check in (
                    common.compare_exact("shared blocks", shared, mine),
                    common.compare_exact(
                        "conventions", conventions, convention
                    ),
                )
                if not check.identical
            ]
            if differing:
                raise ValueError(
                    f"breakdown {key} option {number}: {differing} differ "
                    "from the first breakdown's; they cannot be factored"
                )
        cells.setdefault(key, {})[str(number)] = {
            "option": int(number),
            "indicator_column": indicator,
            "scored": False,
            "upstream": document["upstream"],
            "input_summary": document["input_summary"],
            "dimensions": document["dimensions"],
        }
    assert shared is not None and conventions is not None
    return {**shared, "conventions": conventions}, cells


def invented_group_attribute_loader(
    cohort_inputs: Any, *, seed: int = 0
) -> Callable[[Sequence[int]], g1.GroupAttributes]:
    """A loader of INVENTED side frames for an INVENTED Track M cohort.

    Roles come from the invented 2023 anchor's relationship codes (10
    reference person: head; 20 and 22: spouse; others none); the inputs
    are :func:`.common.invented_group_attribute_inputs`, passed through
    G1's real builder.
    """

    anchor = cohort_inputs.anchor
    roles = {
        int(pid): {10: "head", 20: "spouse", 22: "spouse"}.get(int(code))
        for pid, code in zip(
            anchor["person_id"], anchor["relationship"], strict=True
        )
    }

    def load(person_ids: Sequence[int]) -> g1.GroupAttributes:
        ids = sorted(int(pid) for pid in person_ids)
        persons = pd.DataFrame(
            {
                "person_id": ids,
                "role": pd.array(
                    [roles.get(pid) for pid in ids], dtype="string"
                ),
            }
        )
        inputs = common.invented_group_attribute_inputs(
            persons, wave=ANCHOR_WAVES[0], seed=seed
        )
        return g1.build_group_attributes(
            inputs, ids, anchor_waves=ANCHOR_WAVES
        )

    return load


def _check_run_provenance(
    *,
    data_provenance: str,
    registration_pointer: str | None,
    provenance_kind: str,
    parent: common.CommittedArtifact,
) -> None:
    """Refuse a breakdown run whose provenance does not fit together.

    ``registered_real`` needs the new registration's pointer (an issue #42
    comment other than the parent run's) and ``psid_files`` records;
    ``invented`` needs INVENTED records.
    """

    if data_provenance == tabulation.REGISTERED_REAL:
        if not isinstance(
            registration_pointer, str
        ) or not common.REGISTRATION_POINTER.fullmatch(registration_pointer):
            raise ValueError(
                "a real-data breakdown needs its own issue #42 registration "
                "pointer"
            )
        if registration_pointer == parent.document.get("registration_pointer"):
            raise ValueError(
                "the breakdown's new outcomes need a new registration: the "
                "pointer must not be the parent run's"
            )
        if provenance_kind != PSID_FILES:
            raise ValueError("a real-data breakdown reads psid_files records")
    elif data_provenance == INVENTED:
        if provenance_kind != INVENTED:
            raise ValueError("an invented breakdown reads invented records")
    else:
        raise ValueError(f"unknown data_provenance {data_provenance!r}")


def reproduce_parent(
    *,
    parameters: TrackMParameters,
    parent: common.CommittedArtifact,
    data_provenance: str,
    load_cohort_inputs: Callable[[], Any],
    cola_rates: Mapping[int, float],
    provenance_kind: str,
    source: Mapping[str, Any],
) -> tuple[TrackMReexecution, tuple[common.ReproductionCheck, ...]]:
    """Steps 1-4 of the module docstring: re-execute and prove it exact.

    The parameters' provenance is compared before the cohort inputs are
    loaded, the PSID files' SHA-256 before anything is computed, and every
    re-executed block (:func:`reproduction_checks`) before the caller does
    anything else.  The re-execution runs under the parent's own
    registration pointer, so its output is comparable with the committed
    artifact byte for byte.  Raises
    :class:`.common.ReproductionMismatchError` on any difference; computes
    no group attribute and no group cell, and writes nothing.
    """

    document = parent.document
    early = [parameter_check(parameters, document)]
    common.require_identical(early, stage="parameters")
    cohort_inputs = load_cohort_inputs()
    files = psid_files_check(cohort_inputs, document)
    common.require_identical([files], stage="PSID files")
    reexecution = reexecute_track_m(
        cohort_inputs,
        parameters,
        cola_rates=cola_rates,
        data_provenance=data_provenance,
        registration_pointer=document.get("registration_pointer"),
        provenance_kind=provenance_kind,
        source=source,
    )
    checks = (*early, files, *reproduction_checks(reexecution, document))
    common.require_identical(checks, stage="reproduction")
    return reexecution, checks


def run_group_breakdowns(
    *,
    parameters: TrackMParameters,
    parent: common.CommittedArtifact,
    data_provenance: str,
    registration_pointer: str | None,
    load_cohort_inputs: Callable[[], Any],
    load_side_frame: Callable[[Sequence[int]], g1.GroupAttributes],
    cola_rates: Mapping[int, float],
    provenance_kind: str,
    source: Mapping[str, Any],
    tax_rates: Any = None,
    interest_rates: Any = None,
) -> dict[str, Any]:
    """Re-execute, prove exact reproduction, then the group cells.

    The order of the module docstring: :func:`reproduce_parent` first, and
    ``load_side_frame`` is called only after every reproduction check is
    identical.  ``registered_real`` needs the new registration's pointer
    (an issue #42 comment other than Registration 17's) and
    ``psid_files`` records; ``invented`` needs INVENTED records.  Returns
    the document; writes nothing.
    """

    _check_run_provenance(
        data_provenance=data_provenance,
        registration_pointer=registration_pointer,
        provenance_kind=provenance_kind,
        parent=parent,
    )
    document = parent.document
    reexecution, checks = reproduce_parent(
        parameters=parameters,
        parent=parent,
        data_provenance=data_provenance,
        load_cohort_inputs=load_cohort_inputs,
        cola_rates=cola_rates,
        provenance_kind=provenance_kind,
        source=source,
    )

    # -- only now: group attributes and group cells ------------------------
    universe = [int(pid) for pid in reexecution.cohort.persons["person_id"]]
    side_frame = load_side_frame(universe)
    attributes = person_attributes(
        reexecution,
        parameters,
        side_frame,
        tax_rates=(
            g2.load_oasdi_tax_rates() if tax_rates is None else tax_rates
        ),
        interest_rates=(
            g2.load_trust_fund_interest_rates()
            if interest_rates is None
            else interest_rates
        ),
    )
    assignment = assign(attributes)
    breakdowns = tabulate_breakdowns(
        reexecution,
        assignment,
        data_provenance=data_provenance,
        registration_pointer=registration_pointer,
        parent_sha256=parent.sha256,
    )
    consistency = consistency_checks(reexecution, breakdowns)
    common.require_identical(consistency, stage="consistency")
    shared, cells = _factor(breakdowns)
    labels = list(shared["labels"]) + list(common.POST_HOC_LABELS)
    return {
        "header": (
            common.INVENTED_DATA_HEADER
            if data_provenance == INVENTED
            else None
        ),
        "schema_version": SCHEMA_VERSION,
        "description": (
            "Exercise 4 (Track M: the share of OASDI beneficiaries 62 and "
            "older receiving a minimum benefit, options 2-5, PSID 2023 "
            "wave, income year 2022) broken down by MINT8's characteristic "
            "subgroups, every registered row MS0-MS6 and d430's "
            "sensitivity; post hoc, not blind, report-only, unscored"
        ),
        "publishes_regardless": True,
        "blind": False,
        "scored": False,
        "data_provenance": data_provenance,
        "registration_pointer": registration_pointer,
        "labels": labels,
        "disclosure": COVERED_EARNINGS_DISCLOSURE,
        "parent": {
            **parent.record(_ROOT),
            "specification": copy.deepcopy(document.get("specification")),
            "role": (
                "the committed run this breakdown re-executes and must "
                "reproduce exactly; never edited"
            ),
        },
        "reproduction": {
            "comparison": dict(common.EXACT_COMPARISON),
            "reexecuted_under_registration_pointer": document.get(
                "registration_pointer"
            ),
            "reexecution_note": (
                "the registered computation is re-executed under its own "
                "registration's pointer so that its output is comparable "
                "byte for byte with the committed artifact; every group "
                "cell carries this breakdown's pointer"
            ),
            "location_fields": {
                "fields": ["$." + ".".join(keys) for keys in LOCATION_FIELDS],
                "rule": LOCATION_RULE,
                "committed": [
                    _recorded(document, keys) for keys in LOCATION_FIELDS
                ],
                "this_run": [
                    _recorded(reexecution.result, keys)
                    for keys in LOCATION_FIELDS
                ],
            },
            "identical": True,
            "checks": [check.as_dict() for check in checks],
        },
        "consistency_with_registered_cells": {
            "rule": (
                "G3's Total, Female and Male cells equal tabulate_track_m's "
                "All, Women and Men cells exactly (share, weighted and "
                "unweighted counts of the cell and of those receiving, "
                "design SE, floor), for every row, option and d430"
            ),
            "identical": True,
            "n_checks": len(consistency),
            "checks": [check.as_dict(max_paths=5) for check in consistency],
        },
        "statistic": {
            **tabulation.statistic_block(),
            "id": STATISTIC_ID,
            "formula": (
                "100 * sum_i w_i A_k,i / sum_i w_i over the persons of the "
                "group (tabulation._share's formula; G3 "
                "tabulate_share_breakdown)"
            ),
            "uncertainty": tabulation.uncertainty_block(),
        },
        "group_attributes": attributes.provenance,
        "quintile_rule_sensitivity": quintile_rule_sensitivity(
            attributes, assignment
        ),
        "not_computed": {
            "dimensions": dict(NOT_COMPUTED_DIMENSIONS),
            "statistics": copy.deepcopy(NOT_COMPUTED_STATISTICS),
        },
        "named_deltas": [
            *document.get("named_deltas", pipeline.NAMED_DELTAS),
            *GROUP_NAMED_DELTAS,
        ],
        "breakdown": shared,
        "breakdowns": cells,
    }
