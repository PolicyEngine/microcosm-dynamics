#!/usr/bin/env python3
"""Canonical mechanism-L benefits on seeded, entirely invented people.

Run this same script against the registered source and the build source.
Only legacy interfaces already present at the registration commit are used;
the A-COLA package is deliberately unnecessary in the historical checkout.
The fixture is a fixed projection state, not a new demographic simulation.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

SEED = 20261024
REGISTERED_COMMIT = "dd222b9af926c773a0f92732e2d08be507793378"
ROW_IDS = ("C0", "C1", "M0", "M1", "M2", "M3", "M4")


def registered_rows():
    """Spell out Registration 18 using the common legacy row interface."""
    from populace_dynamics.cola_track_a.config import RegisteredRow
    from populace_dynamics.scenario_benefits import (
        BenefitPeriod,
        ExposureClock,
    )

    components = (
        "retired_worker",
        "disabled_worker",
        "spouse",
        "aged_widow",
        "disabled_widow",
    )
    rows = []
    for row_id in ROW_IDS:
        first = 2027 if row_id.startswith("C") else 2011
        if row_id == "M1":
            first = 2010
        rows.append(
            RegisteredRow(
                row_id=row_id,
                field_changed={
                    "C1": "benefit_period",
                    "M1": "first_reduced_increase",
                    "M2": "benefit_period",
                    "M3": "exposure_clock",
                    "M4": "age_rule",
                }.get(row_id),
                first_reduced_determination_year=first,
                exposure_clock=(
                    ExposureClock.ENTITLEMENT
                    if row_id == "M3"
                    else ExposureClock.ELIGIBILITY
                ),
                benefit_period=(
                    BenefitPeriod.DECEMBER
                    if row_id in ("C1", "M2")
                    else BenefitPeriod.CALENDAR_YEAR
                ),
                components=components,
                headline_statistic=(
                    "ratio_of_all_alive_weighted_totals"
                    if row_id.startswith("C")
                    else "ratio_of_scenario_means"
                ),
            )
        )
    return tuple(rows)


def invented_parameters():
    """Invented monetary/rate inputs; the FRA shape spans the cap gap."""
    from populace_dynamics.ss.params import SSAParameters

    return SSAParameters(
        nawi={y: 2800.0 * 1.04 ** (y - 1951) for y in range(1951, 2061)},
        wage_base={1937: 3000.0, 1975: 14100.0, 1990: 51300.0},
        pia_factors=(0.9, 0.32, 0.15),
        fra_months_by_birth_year=[
            (1900, 780),
            *((y, 780 + 2 * (y - 1937)) for y in range(1938, 1943)),
            (1943, 792),
            (1955, 794),
            (1956, 796),
            (1957, 798),
            (1958, 800),
            (1959, 802),
            (1960, 804),
        ],
        early_monthly_rates=(5 / 900, 5 / 1200),
        early_first_bracket_months=36,
        delayed_credit_by_birth_year=[(1900, 0.08)],
        max_delayed_months=48,
        pe_us_revision="INVENTED mechanism-L equivalence fixture",
    )


def invented_population():
    """Fixed seeded careers and states, including all 1917–1942 cohorts."""
    import pandas as pd

    from populace_dynamics.cola_track_a.config import INVENTED_COHORT_LABEL
    from populace_dynamics.cola_track_a.opening import (
        OpeningStockRecord,
        TrackACohort,
    )
    from populace_dynamics.engine.loop import ProjectionResult

    rng = random.Random(SEED)
    persons, initial, final, departed = [], [], [], []
    careers, opening = {}, {}

    def add(birth, level, *, claim_age=70, **changes):
        pid = len(persons) + 1
        weight = float(rng.randint(100, 500))
        person = {
            "person_id": pid,
            "family_unit_id": (pid + 1) // 2,
            "weight": weight,
            "sex": "female" if pid % 2 else "male",
            "birth_year": birth,
            "age_opening": 2010 - birth,
            "opening_status": "none",
            "ss_opening": 0,
            "marital_status_opening": "married",
            "ss_receipt_opening": False,
        }
        for column in (
            "opening_claim_year",
            "opening_claim_year_upper_bound",
            "opening_claim_age",
            "spouse_person_id",
            "late_spouse_person_id",
            "late_spouse_death_year",
            "widowhood_year",
            "linked_spouse_birth_year",
        ):
            person[column] = pd.NA
        persons.append(person)
        careers[pid] = {
            y: float(level + rng.randint(0, 1000))
            for y in range(max(1951, birth + 22), 2011)
        }
        state = {
            "person_id": pid,
            "year": 2030,
            "age": 2030 - birth,
            "sex": person["sex"],
            "birth_year": birth,
            "weight": weight,
            "di_entitled": False,
            "di_award_year": pd.NA,
            "di_conversion_year": pd.NA,
            "di_recovery_year": pd.NA,
            "claimed": True,
            "claim_age": claim_age,
            "claim_year": birth + claim_age,
            "marital_status": "married",
            "spouse_person_id": pd.NA,
            "widowhood_year": pd.NA,
            "late_spouse_person_id": pd.NA,
            "widowed_in_projection": False,
        }
        state.update(changes)
        final.append(state)
        initial.append(
            {
                **state,
                "year": 2010,
                "age": 2010 - birth,
                "claimed": state["claim_year"] <= 2010,
            }
        )
        return pid

    # Low and high earners in every affected older cohort; each low
    # earner has both an own worker benefit and a positive spouse excess.
    for birth in (*range(1917, 1943), 1965, 1966, 1967, 1968):
        claim_age = 70 if birth < 1943 else 62
        low = add(birth, 2000, claim_age=claim_age)
        high = add(birth, 80000, claim_age=claim_age)
        final[low - 1]["spouse_person_id"] = high
        final[high - 1]["spouse_person_id"] = low
        initial[low - 1]["spouse_person_id"] = high
        initial[high - 1]["spouse_person_id"] = low

    # Unconverted and converted DI records, including a spouse on DI.
    disabled = add(
        1975,
        30000,
        di_entitled=True,
        di_award_year=2008,
        claimed=False,
    )
    spouse = add(1967, 2000, claim_age=62, spouse_person_id=disabled)
    final[disabled - 1]["spouse_person_id"] = spouse
    add(
        1960,
        25000,
        di_award_year=2000,
        di_conversion_year=2027,
    )

    # A projected widow rests on a deceased worker's late-claim record.
    deceased = add(1958, 70000, claim_age=68)
    departed.append({**final.pop(), "year": 2027, "age": 69})
    add(
        1960,
        2000,
        claim_age=64,
        marital_status="widowed",
        widowhood_year=2028,
        late_spouse_person_id=deceased,
        widowed_in_projection=True,
    )

    # Intact frozen opening stock covers all remaining component paths.
    for birth, component in (
        (1935, "retired_worker"),
        (1975, "disabled_worker"),
        (1940, "spouse"),
        (1942, "aged_widow"),
        (1975, "disabled_widow"),
    ):
        pid = add(birth, 10000)
        status = "survivor" if "widow" in component else component
        persons[pid - 1]["opening_status"] = status
        persons[pid - 1]["ss_receipt_opening"] = True
        opening[pid] = OpeningStockRecord(
            person_id=pid,
            status=status,
            component=component,
            observed_annual_amount=float(rng.randint(500, 2000) * 12),
            clock_year=2008,
            clock_rule="INVENTED fixed opening clock",
            entitlement_year=2009,
            entitlement_clamped=False,
        )
        if component == "disabled_worker":
            final[-1]["di_entitled"] = True
            final[-1]["di_award_year"] = 2008

    static = pd.DataFrame(persons)
    initial_frame = pd.DataFrame(initial)
    return (
        TrackACohort(
            persons=static,
            careers=careers,
            initial_slice=initial_frame,
            opening=opening,
            data_provenance="invented",
            labels=(INVENTED_COHORT_LABEL,),
            diagnostics={"seed": SEED},
        ),
        ProjectionResult(
            slices=(
                initial_frame,
                pd.DataFrame(departed),
                pd.DataFrame(final),
            ),
            traces=(),
            draw_index=0,
        ),
    )


def compute_equivalence():
    """Return per-person scenario/component amounts for every runnable row."""
    from populace_dynamics.cola_track_a.benefits import (
        BenefitContext,
        StateLookups,
        reference_benefit_rows,
    )
    from populace_dynamics.cola_track_a.config import TrackAConfig
    from populace_dynamics.estimates.parameters import COLASeries

    cohort, result = invented_population()
    context = BenefitContext(
        cohort=cohort,
        params=invented_parameters(),
        baseline=COLASeries(
            {y: 0.02 + 0.002 * (y % 5) for y in range(1979, 2031)},
            {"invented": True},
        ),
        config=TrackAConfig(rows=("R0",), draw_indices=(0,)),
    )
    lookups = StateLookups(result, 2030)
    cache, output = {}, {}
    for row in registered_rows():
        benefits, _ = reference_benefit_rows(
            result,
            draw=0,
            row=row,
            context=context,
            pia_cache=cache,
            lookups=lookups,
        )
        output[row.row_id] = {
            str(person["person_id"]): {
                "birth_year": person["birth_year"],
                "basis": person["basis"],
                "base": person["benefit_base"],
                "reform": person["benefit_reform"],
                "components": person["benefit_components"],
            }
            for person in benefits
        }
    return {
        "schema_version": "acola-mechanism-l-equivalence-v1",
        "data": "INVENTED DATA ONLY",
        "seed": SEED,
        "draw": 0,
        "reference_year": 2030,
        "rows": output,
    }


def canonical_json(value):
    return json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n"


def differing_people(expected, actual):
    """Name changed row/person pairs without hiding missing membership."""
    differences = []
    for row in sorted(set(expected["rows"]) | set(actual["rows"])):
        before = expected["rows"].get(row, {})
        after = actual["rows"].get(row, {})
        for person in sorted(set(before) | set(after), key=int):
            if before.get(person) != after.get(person):
                differences.append(f"{row}/person-{person}")
    return differences


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository_root", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    source = args.repository_root.resolve() / "src"
    if not (source / "populace_dynamics/cola_track_a/benefits.py").is_file():
        parser.error("repository root has no legacy mechanism-L source")
    sys.path.insert(0, str(source))
    args.output.write_text(canonical_json(compute_equivalence()))


if __name__ == "__main__":
    main()
