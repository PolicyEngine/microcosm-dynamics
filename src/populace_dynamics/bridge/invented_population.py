"""INVENTED populations for the PolicyEngine-US population path.

INVENTED DATA - NOT A COMPARISON, NOT THE US.  Nothing here reads a PSID
file, a projection or a comparator value.  The population runs on invented
data by design until a registered real-data analysis exists (cos decision
d727, under Max's d479: "Development checks use invented cases").

1. **The cohort.**  :func:`build_invented_cohort` draws the PSID-shaped frames
   of :mod:`populace_dynamics.min_benefit_track_m.invented_psid` (seeded,
   ``n_family_units`` family units) and runs them through Track M's M4
   cohort (:func:`~populace_dynamics.min_benefit_track_m.cohort.
   build_cohort`) and M5 careers (:func:`~populace_dynamics.
   min_benefit_track_m.careers.build_track_m_inputs`) with provenance
   ``invented``.  ``careers`` itself refuses to mark a cohort read from
   PSID files as invented, and requires the invented generator's label
   (``careers.py:244-260``).
2. **The benefits.**  :func:`evaluate_headline` applies the Track M rules
   (:func:`~populace_dynamics.min_benefit_track_m.evaluation.evaluate`)
   under the headline row MS0.  ``evaluate`` has no provenance guard of
   its own; the tabulation and the pipeline hold them
   (``evaluation.py:27-29``; ``pipeline.py:205-224``).  So
   :func:`require_invented` refuses, before ``evaluate`` runs, any records
   not marked ``invented``, any carrying the PSID file-provenance key
   (``pipeline.PSID_FILES_SOURCE_KEY``) and any whose source lacks the
   invented label.  The people, family units, weights, birth years and
   2022 amounts come from the cohort and the frames, not the records, so
   :func:`require_invented_cohort` refuses, before evaluation or mapping,
   frames or a cohort without the invented label or with PSID
   file-provenance keys, and a cohort or records with different source
   provenance from those frames.
   :func:`person_benefits` turns each worker record's PIA
   at first calculation into each person's 2026 benefit, three ways:
   current law (the history PIA, *P*), option 1 (a memo) and option 2
   (``max((1 - c) P, M)``, ``rules.py:317-401``).  Both PIAs are carried to
   2026 with statutory COLAs as the bridge carries them
   (:func:`~.policyengine_us.carry_pia_forward`, from the record's
   threshold year, the section 4a year of eligibility, onset or death,
   ``rules.py:464-533``), times the own claim factor and rounded down to
   the dollar (``scripts/pe_us_minimum_benefit_sample_households.py:789``).
   Spouse's and widow(er)'s excesses come from the oracle's
   ``spousal_benefit`` and ``widow_benefit`` (``ss/benefits.py:205-236,
   266-329``) on the carried PIAs, with the months early and claim factors
   the M5 careers recorded (``evaluation._receipts`` applies the same
   functions to decide receipt, ``evaluation.py:491-536``).  Two groups
   keep their 2022 amount, carried by the COLAs, in every scenario:
   unlinked auxiliaries, and people paid an own benefit whose current-law
   PIA is zero because no covered earnings are observed
   (:func:`person_benefits`).
3. **Everything else, invented.**  The generator draws no state, income
   other than Social Security, assets or rent.
   :func:`invented_other_inputs` draws them from
   :data:`INVENTED_DISTRIBUTIONS` (seeded, on a stream apart from the
   cohort's), named for the PSID concepts ``estimates.adjusted_poverty``
   reads, and :data:`INPUT_CONCEPTS` maps each to a PolicyEngine-US input
   by that module's conventions.
4. **The households.**  :func:`build_population` places each family unit in
   one household, SPM unit and family; the reference person and spouse
   in one marital unit and one joint tax unit; every other member in a
   marital unit and a tax unit of their own.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from populace_dynamics.bridge import policyengine_us as bridge
from populace_dynamics.bridge.population import (
    GROUP_ENTITIES,
    PopulationFrame,
)
from populace_dynamics.min_benefit_track_m import (
    DRY_RUN_HEADER,
    careers,
    cohort,
    invented_psid,
)
from populace_dynamics.min_benefit_track_m.evaluation import (
    INVENTED,
    Evaluation,
    TrackMInputs,
    TrackMParameters,
    evaluate,
)
from populace_dynamics.min_benefit_track_m.pipeline import (
    PSID_FILES_SOURCE_KEY,
)
from populace_dynamics.min_benefit_track_m.policy import (
    HEADLINE_CELL,
    policy_for_row,
)
from populace_dynamics.min_benefit_track_m.rules import survivor_own_amount
from populace_dynamics.ss import benefits

__all__ = [
    "BENEFIT_SCENARIOS",
    "HEADLINE_ROW",
    "INPUT_CONCEPTS",
    "INVENTED_DISTRIBUTIONS",
    "INVENTED_INPUT_LABEL",
    "INVENTED_POPULATION_LABEL",
    "InventedCohort",
    "InventedPopulation",
    "OTHER_INPUTS_STREAM",
    "PAYMENT_YEAR",
    "SIMULATED_SCENARIOS",
    "build_invented_cohort",
    "build_population",
    "evaluate_headline",
    "invented_other_inputs",
    "person_benefits",
    "require_invented",
    "require_invented_cohort",
]

#: Every output of the population path carries this label.
INVENTED_POPULATION_LABEL = f"{DRY_RUN_HEADER}, NOT THE US"
#: The payment year, as the bridge's (``pe_us_bridge.md``, Payment year).
PAYMENT_YEAR = 2026
#: Exercise 4's headline row and option (``policy.HEADLINE_CELL``).
HEADLINE_ROW = "MS0"
HEADLINE_OPTION = HEADLINE_CELL[0]
#: The benefit scenarios: current law (the PIA with no cut), option 1
#: (reduced current law; a memo, not simulated) and the headline option.
BENEFIT_SCENARIOS: tuple[str, ...] = ("current_law", "option_1", "option_2")
#: The scenarios run through PolicyEngine-US: baseline, then reform.
SIMULATED_SCENARIOS: tuple[str, ...] = ("current_law", "option_2")
#: The seed stream of :func:`invented_other_inputs`, apart from the
#: cohort's (``invented_psid`` seeds ``np.random.default_rng(seed)``).
OTHER_INPUTS_STREAM = 20260930
_ROLES = ("reference_person", "spouse", "other_member")
_MONTHS = 12

#: The label every invented input carries, here and in the outputs.
INVENTED_INPUT_LABEL = "INVENTED"
#: The INVENTED distributions of the inputs the cohort lacks.  Each amount
#: is lognormal with the given median and log-scale sigma, drawn with the
#: given probability (zero otherwise), and rounded to the dollar.  Every
#: variate is drawn whether or not it is used, so one input's probability
#: never shifts another's draws.  None is a survey, Census or program
#: value.
INVENTED_DISTRIBUTIONS: dict[str, dict[str, Any]] = {
    "state": {
        "label": INVENTED_INPUT_LABEL,
        "unit": "family unit",
        "rule": "uniform over the 50 states and DC (bridge.STATE_FIPS)",
    },
    "renter": {
        "label": INVENTED_INPUT_LABEL,
        "unit": "family unit",
        "probability": 0.4,
    },
    "monthly_rent": {
        "label": INVENTED_INPUT_LABEL,
        "unit": "family unit (renters)",
        "median": 900.0,
        "sigma": 0.35,
    },
    "wealth1": {
        "label": INVENTED_INPUT_LABEL,
        "unit": "family unit",
        "low_probability": 0.3,
        "low_uniform_max": 3_000.0,
        "median": 60_000.0,
        "sigma": 1.4,
    },
    "vehicles": {
        "label": INVENTED_INPUT_LABEL,
        "unit": "family unit",
        "probability": 0.75,
        "median": 9_000.0,
        "sigma": 0.7,
    },
    "labor": {
        "label": INVENTED_INPUT_LABEL,
        "unit": "person",
        "probability": {
            "reference_person": 0.10,
            "spouse": 0.10,
            "other_member": 0.05,
        },
        "median": 12_000.0,
        "sigma": 0.9,
    },
    "annuities": {
        "label": INVENTED_INPUT_LABEL,
        "unit": "person",
        "probability": 0.35,
        "median": 9_000.0,
        "sigma": 0.9,
    },
    "interest": {
        "label": INVENTED_INPUT_LABEL,
        "unit": "person",
        "probability": 0.45,
        "median": 300.0,
        "sigma": 1.3,
    },
}

#: Each invented item, the PolicyEngine-US input it becomes, and the
#: convention it follows.  Named for the PSID concepts
#: ``estimates.adjusted_poverty`` reads where the invented data has one.
INPUT_CONCEPTS: tuple[dict[str, str], ...] = (
    {
        "label": INVENTED_INPUT_LABEL,
        "item": "labor",
        "input": "employment_income",
        "convention": (
            "earned income: the PSID labor items of "
            "family_income.HW_EARNED_CONCEPTS (data/family_income.py:"
            "1148-1154), which estimates.adjusted_poverty treats as earned "
            "income (adjusted_poverty.py:118, 1463-1466)"
        ),
    },
    {
        "label": INVENTED_INPUT_LABEL,
        "item": "interest",
        "input": "interest_income",
        "convention": (
            "asset income: an item of family_income.ASSET_INCOME_CONCEPTS "
            "(data/family_income.py:1131-1143)"
        ),
    },
    {
        "label": INVENTED_INPUT_LABEL,
        "item": "annuities",
        "input": "taxable_private_pension_income",
        "convention": (
            "income from annuities and IRAs (HEAD ANNUITIES; "
            "adjusted_poverty.py:28-33), drawn for every person here, "
            "entered as a taxable private pension as the bridge enters "
            "its households' pensions"
        ),
    },
    {
        "label": INVENTED_INPUT_LABEL,
        "item": "max(0, wealth1 - vehicles)",
        "input": "bank_account_assets",
        "convention": (
            "adjusted_poverty's resource proxy (adjusted_poverty.py:118-119,"
            " 1469), on the reference person; policyengine-us 2.18.0 counts "
            "bank_account_assets as an SSI resource "
            "(parameters/gov/ssa/ssi/eligibility/resources/countable.yaml:7)"
        ),
    },
    {
        "label": INVENTED_INPUT_LABEL,
        "item": "12 x monthly_rent",
        "input": "pre_subsidy_rent",
        "convention": (
            "no adjusted_poverty analog; renters only, on the reference "
            "person, as the bridge enters its households' rent"
        ),
    },
)


# ---------------------------------------------------------------------------
# The cohort and the guard
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class InventedCohort:
    """The invented frames, the M4 cohort and the M5 records."""

    frames: Any
    cohort: Any
    inputs: TrackMInputs
    seed: int
    n_family_units: int


def build_invented_cohort(
    *,
    seed: int,
    n_family_units: int,
    params: Any,
    cola_rates: Mapping[int, float],
) -> InventedCohort:
    """``invented_psid`` through M4 and M5, marked ``invented``."""

    frames = invented_psid.invented_cohort_inputs(
        seed=seed, n_family_units=n_family_units
    )
    built = cohort.build_cohort(frames)
    inputs = careers.build_track_m_inputs(
        built,
        earnings=frames.earnings,
        prior_year=frames.prior_year_labor,
        params=params,
        cola_rates=cola_rates,
        provenance_kind=INVENTED,
        source=dict(frames.provenance),
    )
    return InventedCohort(frames, built, inputs, seed, n_family_units)


def require_invented(inputs: TrackMInputs) -> None:
    """Refuse records the population path may not evaluate.

    Only records marked ``invented``, carrying no PSID file-provenance key
    (even an empty one) and the invented generator's label
    (:data:`DRY_RUN_HEADER`) pass.  Real-data
    records belong to the registered post hoc analysis (d727).
    """

    if inputs.provenance_kind != INVENTED:
        raise ValueError(
            "the population path evaluates invented records only, not "
            f"{inputs.provenance_kind!r}"
        )
    if PSID_FILES_SOURCE_KEY in inputs.source:
        raise ValueError(
            "records carrying a PSID file hashes key are never evaluated here"
        )
    if inputs.source.get("label") != DRY_RUN_HEADER:
        raise ValueError(
            "records need the invented generator's label "
            f"{DRY_RUN_HEADER!r}"
        )


def _require_same_persons(inputs: TrackMInputs, persons: pd.DataFrame) -> None:
    # The person frame is the records' persons: the same ids, each once,
    # each in the same family unit with the same weight (careers copies
    # both from the cohort's person frame).
    ids = persons["person_id"].astype(int).astype(str)
    if ids.duplicated().any():
        raise ValueError("the cohort's person ids must be unique")
    cohort_rows = dict(
        zip(
            ids,
            zip(
                persons["family_unit_id"].astype(int),
                persons["weight"].astype(float),
                strict=True,
            ),
            strict=True,
        )
    )
    records = {
        person.person_id: (int(person.family_unit_id), float(person.weight))
        for person in inputs.persons
    }
    if set(records) != set(cohort_rows):
        raise ValueError("the records' persons are not the cohort's persons")
    differ = sorted(pid for pid in records if records[pid] != cohort_rows[pid])
    if differ:
        raise ValueError(
            f"persons {differ[:10]}: the records and the cohort give "
            "different family units or weights"
        )


def require_invented_cohort(invented: InventedCohort) -> None:
    """Refuse a cohort the population path may not evaluate or map.

    :func:`require_invented` checks the records alone, but the people,
    family units, weights, birth years and 2022 amounts come from the M4
    cohort (``cohort.persons``) and the invented frames (``frames.anchor``).
    So, besides the records' own guard:

    * the frames, their structural inputs (which hold the anchor), and
      the cohort must each carry the invented generator's label
      (:data:`DRY_RUN_HEADER`) and no PSID file-provenance key
      (``pipeline.PSID_FILES_SOURCE_KEY``), even an empty one;
    * the cohort must carry those frames' provenance (``build_cohort``
      copies it, ``cohort.py:1308``), and the records' source must include
      that same provenance (:func:`build_invented_cohort` passes it to
      ``careers``), for this seed and size;
    * the records' persons must be the cohort's, each in the same family
      unit with the same weight.
    """

    require_invented(invented.inputs)
    frames = dict(invented.frames.provenance)
    for name, provenance in (
        ("frames", frames),
        ("structural inputs", invented.frames.structure_inputs.provenance),
        ("cohort", invented.cohort.provenance),
    ):
        if PSID_FILES_SOURCE_KEY in provenance:
            raise ValueError(
                f"the {name} carry a PSID file hashes key and are never "
                "mapped here"
            )
        if provenance.get("label") != DRY_RUN_HEADER:
            raise ValueError(
                f"the {name} need the invented generator's label "
                f"{DRY_RUN_HEADER!r}"
            )
    if dict(invented.cohort.provenance) != frames:
        raise ValueError("the cohort was not built from these frames")
    source = invented.inputs.source
    if any(source.get(key) != value for key, value in frames.items()):
        raise ValueError("the records were not built from these frames")
    if (frames.get("seed"), frames.get("n_family_units")) != (
        invented.seed,
        invented.n_family_units,
    ):
        raise ValueError(
            "the frames are not of this cohort's seed and number of family "
            "units"
        )
    _require_same_persons(invented.inputs, invented.cohort.persons)


def evaluate_headline(
    invented: InventedCohort, parameters: TrackMParameters
) -> Evaluation:
    """Track M's rules under row MS0, on a checked invented cohort only."""

    require_invented_cohort(invented)
    return evaluate(invented.inputs, policy_for_row(HEADLINE_ROW), parameters)


# ---------------------------------------------------------------------------
# Benefits
# ---------------------------------------------------------------------------
def _scenario_pia(outcome: Any, scenario: str) -> float:
    if scenario == "current_law":
        return float(outcome.pia)
    number = {"option_1": 1, "option_2": HEADLINE_OPTION}[scenario]
    return float(outcome.outcomes[number].option_pia)


def _floor_dollar(amount: float) -> int:
    # As the bridge's worker: "rounded down to the dollar" with a guard
    # against float noise below a whole dollar
    # (scripts/pe_us_minimum_benefit_sample_households.py:789).
    return int(math.floor(amount + 1e-9))


def person_benefits(
    invented: InventedCohort,
    result: Evaluation,
    parameters: TrackMParameters,
    cola_rates: Mapping[int, float],
    *,
    payment_year: int = PAYMENT_YEAR,
) -> pd.DataFrame:
    """Each person's monthly and annual benefits in ``payment_year``.

    One row per person of the cohort's records (``invented.inputs``), with,
    for each of :data:`BENEFIT_SCENARIOS`: ``own_<s>`` (the own worker
    benefit), ``auxiliary_<s>`` (the largest spouse's or widow(er)'s excess,
    or an unlinked auxiliary's invented amount) and the annual
    ``<s>__social_security_retirement`` (own), ``__dependents`` (spouse's
    excess or unlinked dependent's) and ``__survivors``.  ``result`` is
    :func:`evaluate_headline` of those records.  The M4 cohort's person
    frame (``invented.cohort.persons``) gives two amounts carried from the
    2022 amount (``amount_2022``) by the COLAs determined 2022 through
    ``payment_year - 1``, the same in every scenario:

    * an unlinked auxiliary's benefit (no linked worker record to compute
      it from);
    * the whole benefit of a person paid an own worker benefit whose own
      record's current-law PIA is zero because no covered earnings are
      observed (``own_benefit_source`` ``"observed_2022_amount"``).  The
      invented generator, like the PSID panel it mimics, has labor income
      for reference persons and spouses only, so every other family-unit
      member's history is empty (``invented_psid.py:599-617`` draws their
      receipt but no earnings).  Track M's rules then give them no
      benefit, and PolicyEngine-US would pay them SSI as if they had no
      Social Security.  Their benefit does not change under the reform:
      Track M cannot compute their PIA, so it cannot apply the option.

    Refuses, before computing anything, a cohort
    :func:`require_invented_cohort` refuses, an evaluation with different
    worker or person ids,
    and a person paid an own worker benefit without an evaluated own record
    (``PersonRecord`` refuses one with no own record when it is built,
    ``evaluation.py:208-211``; this holds for records altered after).
    Raises if a person with no record in the window gets different
    benefits in two scenarios.
    """

    require_invented_cohort(invented)
    inputs = invented.inputs
    persons = invented.cohort.persons
    if set(result.workers) != set(inputs.workers) or set(
        result.rows["person_id"].astype(str)
    ) != {person.person_id for person in inputs.persons}:
        raise ValueError("the evaluation is not of the cohort's records")
    unpaid = sorted(
        person.person_id
        for person in inputs.persons
        if person.paid_own_worker_benefit
        and (
            person.own_record_id is None
            or person.own_record_id not in result.workers
        )
    )
    if unpaid:
        raise ValueError(
            f"persons {unpaid[:10]} are paid an own worker benefit but have "
            "no evaluated own record"
        )
    params = parameters.params
    last = payment_year - 1
    carried: dict[str, dict[str, float]] = {s: {} for s in BENEFIT_SCENARIOS}
    for key, outcome in result.workers.items():
        first = outcome.years.threshold_year
        for scenario in BENEFIT_SCENARIOS:
            amount, _ = bridge.carry_pia_forward(
                _scenario_pia(outcome, scenario),
                cola_rates,
                first_determination_year=first,
                last_determination_year=last,
            )
            carried[scenario][key] = amount
    unlinked_factor = 1.0
    for year in range(2022, payment_year):
        unlinked_factor *= 1.0 + float(cola_rates[year])
    rows_by_person = result.rows.set_index("person_id")
    cohort_persons = persons.set_index(persons["person_id"].astype(str))
    table = []
    for person in inputs.persons:
        own = person.own_record_id
        outcome = result.workers[own] if own is not None else None
        row: dict[str, Any] = {
            "person_id": person.person_id,
            "family_unit_id": person.family_unit_id,
            "exposed": bool(rows_by_person.loc[person.person_id, "exposed"]),
            "receives_2": bool(
                rows_by_person.loc[person.person_id, "receives_2"]
            ),
            "receipt_basis_2": str(
                rows_by_person.loc[person.person_id, "basis"]
            ),
            "own_record_id": own,
            "paid_own_worker_benefit": person.paid_own_worker_benefit,
            "own_claim_factor": person.own_claim_factor,
            "own_years_of_coverage": (
                int(outcome.count.years) if outcome is not None else None
            ),
            "own_threshold_year": (
                int(outcome.years.threshold_year)
                if outcome is not None
                else None
            ),
            "own_in_window": (
                bool(outcome.outcomes[HEADLINE_OPTION].in_window)
                if outcome is not None
                else False
            ),
            "own_on_minimum": (
                bool(outcome.outcomes[HEADLINE_OPTION].on_minimum)
                if outcome is not None
                else False
            ),
            "unlinked_auxiliary": person.unlinked_auxiliary,
        }
        observed_only = bool(
            person.paid_own_worker_benefit and carried["current_law"][own] == 0
        )
        row["own_benefit_source"] = (
            "observed_2022_amount"
            if observed_only
            else "track_m_pia" if person.paid_own_worker_benefit else None
        )
        for scenario in BENEFIT_SCENARIOS:
            pias = carried[scenario]
            own_monthly = 0
            if observed_only:
                amount_2022 = float(
                    cohort_persons.loc[person.person_id, "amount_2022"]
                )
                own_monthly = _floor_dollar(
                    amount_2022 / _MONTHS * unlinked_factor
                )
            elif person.paid_own_worker_benefit:
                own_monthly = _floor_dollar(
                    pias[own] * float(person.own_claim_factor)
                )
            best, kind = 0, None
            for link in () if observed_only else person.links:
                worker = pias[link.worker_record_id]
                if link.kind == "spouse":
                    excess = benefits.spousal_benefit(
                        pias[own] if own is not None else 0.0,
                        worker,
                        link.months_early,
                        params,
                    )
                else:
                    own_amount = survivor_own_amount(
                        pias[own] if own is not None else None,
                        person.own_claim_factor,
                        receives_own_benefit=person.paid_own_worker_benefit,
                    )
                    paid = benefits.widow_benefit(
                        own_amount,
                        worker,
                        link.months_early,
                        link.worker_claim_factor,
                        params,
                    )
                    excess = max(paid - own_amount, 0.0)
                amount = _floor_dollar(excess)
                if amount > best:
                    best, kind = amount, link.kind
            if person.unlinked_auxiliary:
                amount_2022 = float(
                    cohort_persons.loc[person.person_id, "amount_2022"]
                )
                best = _floor_dollar(amount_2022 / _MONTHS * unlinked_factor)
                unlinked = str(
                    cohort_persons.loc[person.person_id, "unlinked_kind"]
                )
                kind = "survivor" if unlinked == "survivor" else "spouse"
            row[f"pia_{scenario}"] = pias[own] if own is not None else None
            row[f"own_{scenario}"] = own_monthly
            row[f"auxiliary_{scenario}"] = best
            row[f"auxiliary_kind_{scenario}"] = kind
            row[f"{scenario}__social_security_retirement"] = (
                _MONTHS * own_monthly
            )
            row[f"{scenario}__social_security_dependents"] = (
                _MONTHS * best if kind == "spouse" else 0
            )
            row[f"{scenario}__social_security_survivors"] = (
                _MONTHS * best if kind == "survivor" else 0
            )
        table.append(row)
    frame = pd.DataFrame(table)
    for scenario in BENEFIT_SCENARIOS:
        frame[f"{scenario}__social_security"] = sum(
            frame[f"{scenario}__social_security_{kind}"]
            for kind in ("retirement", "dependents", "survivors")
        )
    unexposed = ~frame["exposed"]
    for scenario in BENEFIT_SCENARIOS[1:]:
        differs = frame.loc[unexposed, f"{scenario}__social_security"] != (
            frame.loc[unexposed, "current_law__social_security"]
        )
        if differs.any():
            raise AssertionError(
                f"{int(differs.sum())} persons with no record in the window "
                f"have different benefits under {scenario}"
            )
    return frame


# ---------------------------------------------------------------------------
# The invented inputs the cohort lacks
# ---------------------------------------------------------------------------
def _lognormal(rng: np.random.Generator, spec: Mapping[str, Any]) -> float:
    return float(np.exp(np.log(spec["median"]) + spec["sigma"] * rng.normal()))


def invented_other_inputs(
    members: pd.DataFrame, *, seed: int
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """INVENTED state, rent, assets and non-Social Security income.

    ``members`` has ``person_id``, ``family_unit_id`` and ``role`` (one of
    reference_person, spouse, other_member).  Returns a family frame
    (``family_unit_id``, ``state``, ``renter``, ``monthly_rent``,
    ``wealth1``, ``vehicles``) and a person frame (``person_id``,
    ``labor``, ``annuities``, ``interest``), drawn from
    :data:`INVENTED_DISTRIBUTIONS` with ``np.random.default_rng([seed,
    OTHER_INPUTS_STREAM])``, families in id order and then persons in id
    order.  Deterministic for a given seed and membership.
    """

    rng = np.random.default_rng([int(seed), OTHER_INPUTS_STREAM])
    spec = INVENTED_DISTRIBUTIONS
    states = sorted(bridge.STATE_FIPS)
    families = []
    for family in sorted(set(members["family_unit_id"].astype(int))):
        state = states[int(rng.integers(len(states)))]
        renter = bool(rng.random() < spec["renter"]["probability"])
        rent = _lognormal(rng, spec["monthly_rent"])
        low = bool(rng.random() < spec["wealth1"]["low_probability"])
        low_amount = float(
            rng.uniform(0.0, spec["wealth1"]["low_uniform_max"])
        )
        high_amount = _lognormal(rng, spec["wealth1"])
        has_vehicle = bool(rng.random() < spec["vehicles"]["probability"])
        vehicle = _lognormal(rng, spec["vehicles"])
        families.append(
            {
                "family_unit_id": family,
                "state": state,
                "renter": renter,
                "monthly_rent": float(round(rent)) if renter else 0.0,
                "wealth1": float(round(low_amount if low else high_amount)),
                "vehicles": float(round(vehicle)) if has_vehicle else 0.0,
            }
        )
    people = []
    ordered = members.assign(_id=members["person_id"].astype(int)).sort_values(
        "_id"
    )
    for row in ordered.itertuples(index=False):
        if row.role not in _ROLES:
            raise ValueError(f"unknown role {row.role!r}")
        amounts = {}
        for item in ("labor", "annuities", "interest"):
            probability = spec[item]["probability"]
            if isinstance(probability, Mapping):
                probability = probability[row.role]
            present = bool(rng.random() < probability)
            amount = _lognormal(rng, spec[item])
            amounts[item] = float(round(amount)) if present else 0.0
        people.append({"person_id": str(row.person_id), **amounts})
    return pd.DataFrame(families), pd.DataFrame(people)


# ---------------------------------------------------------------------------
# Households
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class InventedPopulation:
    """The simulated scenarios' frames and the tables behind them."""

    frames: Mapping[str, PopulationFrame]
    people: pd.DataFrame
    households: pd.DataFrame


def build_population(
    invented: InventedCohort,
    benefit_table: pd.DataFrame,
    *,
    seed: int,
    payment_year: int = PAYMENT_YEAR,
) -> InventedPopulation:
    """The PolicyEngine-US population of an invented cohort (docstring 4).

    Refuses, before anything is mapped, a cohort
    :func:`require_invented_cohort` refuses.  The people are the M4
    cohort's universe (``cohort.persons``: their role, birth year, weight
    and family unit).  The invented frames' anchor must hold exactly those
    persons, each in the family unit (the anchor's ``interview``) the
    cohort gives them.  The anchor defines current family membership;
    every current member must belong to the universe.  Historical receipt,
    marriage and earnings rows can include deceased linked workers and do
    not define current household membership.  The invented generator gives
    every anchor person a 2022 benefit and a birth year of 1960 or earlier
    (``invented_psid.py:481,493,518,551,569,601,614``), and a family with a
    current member outside the universe is refused, since this path has
    no inputs for such a member.  Ages are
    ``payment_year`` less the birth year.  Medicare quarters of coverage
    are left to policyengine-us's default of 40
    (``medicare_quarters_of_coverage.py:16``), the premium-free Part A
    threshold (``is_premium_free_part_a.py:17-20``): every universe member
    receives OASDI, own or auxiliary.  Heating or cooling costs, no housing
    voucher and food preparation at home are set for every household, as
    the bridge sets them.
    """

    require_invented_cohort(invented)
    persons = invented.cohort.persons.copy()
    persons["person_id"] = persons["person_id"].astype(int)
    anchor = invented.frames.anchor
    anchor_ids = anchor["person_id"].astype(int)
    if anchor_ids.duplicated().any():
        raise ValueError("the anchor's person ids must be unique")
    anchor_family = dict(
        zip(anchor_ids, anchor["interview"].astype(int), strict=True)
    )
    outside = sorted(set(anchor_family) - set(persons["person_id"]))
    if outside:
        raise ValueError(
            f"persons {outside[:10]} are outside the Track M universe; the "
            "population path places only universe members in households"
        )
    moved = sorted(
        pid
        for pid, fid in zip(
            persons["person_id"],
            persons["family_unit_id"].astype(int),
            strict=True,
        )
        if anchor_family.get(pid) != fid
    )
    if moved:
        raise ValueError(
            f"persons {moved[:10]} are not in the anchor's family unit the "
            "cohort gives them"
        )
    unknown = set(persons["role"]) - set(_ROLES)
    if unknown:
        raise ValueError(f"unknown roles {sorted(unknown)}")
    members = pd.DataFrame(
        {
            "person_id": persons["person_id"],
            "family_unit_id": persons["family_unit_id"].astype(int),
            "role": persons["role"].astype(str),
            "birth_year": persons["birth_year"].astype(int),
            "weight": persons["weight"].astype(float),
            "amount_2022": persons["amount_2022"].astype(float),
        }
    )
    by_person = benefit_table.set_index(benefit_table["person_id"].astype(int))
    if by_person.index.has_duplicates:
        raise ValueError("the benefit table person ids must be unique")
    if set(by_person.index) != set(members["person_id"]):
        raise ValueError("the benefit table is not the cohort's persons")
    families, incomes = invented_other_inputs(members, seed=seed)
    members = members.merge(
        incomes.assign(person_id=incomes["person_id"].astype(int)),
        on="person_id",
        how="left",
        validate="one_to_one",
    )
    members["role_order"] = members["role"].map(
        {role: i for i, role in enumerate(_ROLES)}
    )
    members = members.sort_values(
        ["family_unit_id", "role_order", "person_id"]
    ).reset_index(drop=True)
    families = families.set_index("family_unit_id")
    household_ids = sorted(members["family_unit_id"].unique().tolist())
    household_index = {fid: h for h, fid in enumerate(household_ids)}
    weights = members.groupby("family_unit_id")["weight"].agg(["min", "max"])
    if (weights["min"] != weights["max"]).any():
        raise ValueError("members of a family unit carry different weights")
    if (weights["min"] <= 0).any():
        raise ValueError("every family unit needs a positive weight")
    n = len(members)
    units = {kind: np.zeros(n, dtype=np.int64) for kind in GROUP_ENTITIES}
    next_unit = 0
    for fid in household_ids:
        index = np.flatnonzero(members["family_unit_id"].to_numpy() == fid)
        roles = members["role"].to_numpy()[index]
        if (roles == "reference_person").sum() != 1 or (
            roles == "spouse"
        ).sum() > 1:
            raise ValueError(
                f"family unit {fid}: needs one reference person and at "
                "most one spouse"
            )
        couple = [
            i for i, r in zip(index, roles, strict=True) if r != "other_member"
        ]
        for i in index:
            units["household"][i] = household_index[fid]
            units["spm_unit"][i] = household_index[fid]
            units["family"][i] = household_index[fid]
        assigned: dict[int, int] = {}
        if len(couple) == 2:
            for i in couple:
                assigned[int(i)] = next_unit
            next_unit += 1
        for i in index:
            if int(i) not in assigned:
                assigned[int(i)] = next_unit
                next_unit += 1
        for i in index:
            units["marital_unit"][i] = assigned[int(i)]
            units["tax_unit"][i] = assigned[int(i)]

    amounts: dict[str, np.ndarray] = {
        name: np.zeros(n) for name in bridge.AMOUNT_FIELDS
    }
    amounts["employment_income"] = members["labor"].to_numpy(dtype=float)
    amounts["taxable_private_pension_income"] = members["annuities"].to_numpy(
        dtype=float
    )
    amounts["interest_income"] = members["interest"].to_numpy(dtype=float)
    first_member = ~members["family_unit_id"].duplicated().to_numpy()
    family_of = members["family_unit_id"].to_numpy()
    resources = np.asarray(
        [
            max(
                0.0,
                families.loc[f, "wealth1"] - families.loc[f, "vehicles"],
            )
            for f in family_of
        ]
    )
    rent = np.asarray(
        [12.0 * families.loc[f, "monthly_rent"] for f in family_of]
    )
    amounts["bank_account_assets"] = np.where(first_member, resources, 0.0)
    amounts["pre_subsidy_rent"] = np.where(first_member, rent, 0.0)

    quarters = np.full(n, -1, dtype=np.int64)  # the model's default, 40
    social_security: dict[str, dict[str, np.ndarray]] = {}
    for scenario in BENEFIT_SCENARIOS:
        social_security[scenario] = {
            kind: np.zeros(n)
            for kind in ("retirement", "dependents", "survivors")
        }
    for i, row in enumerate(members.itertuples(index=False)):
        benefit = by_person.loc[int(row.person_id)]
        for scenario in BENEFIT_SCENARIOS:
            for kind in ("retirement", "dependents", "survivors"):
                social_security[scenario][kind][i] = float(
                    benefit[f"{scenario}__social_security_{kind}"]
                )
    frames = {}
    base = dict(
        person_ids=tuple(str(p) for p in members["person_id"]),
        age=(payment_year - members["birth_year"]).to_numpy(dtype=np.int64),
        medicare_quarters_of_coverage=quarters,
        units=units,
        household_ids=tuple(str(f) for f in household_ids),
        state=tuple(families.loc[f, "state"] for f in household_ids),
        weight=np.asarray(
            [float(weights.loc[f, "min"]) for f in household_ids]
        ),
        has_heating_cooling_expense=np.ones(len(household_ids), dtype=bool),
        takes_up_housing_assistance=np.zeros(len(household_ids), dtype=bool),
        food_preparation_allowed=np.ones(len(household_ids), dtype=bool),
    )
    for scenario in SIMULATED_SCENARIOS:
        scenario_amounts = dict(amounts)
        for kind in ("retirement", "dependents", "survivors"):
            scenario_amounts[f"social_security_{kind}"] = social_security[
                scenario
            ][kind]
        frames[scenario] = PopulationFrame(amounts=scenario_amounts, **base)
    people = members.drop(columns=["role_order"]).copy()
    for scenario in BENEFIT_SCENARIOS:
        people[f"{scenario}__social_security"] = sum(
            social_security[scenario][kind]
            for kind in ("retirement", "dependents", "survivors")
        )
    people["household"] = units["household"]
    households = families.loc[household_ids].reset_index()
    households["weight"] = base["weight"]
    households["household"] = np.arange(len(household_ids))
    return InventedPopulation(frames, people, households)
