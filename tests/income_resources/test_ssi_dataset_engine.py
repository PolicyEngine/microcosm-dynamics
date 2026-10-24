"""Public dataset-route oracle differential on invented households only.

POPULACE_DYNAMICS_PE_US_PYTHON_SSI0 selects the separate interpreter and
assigns this module to oracle_policyengine without changing tier policy.
"""

import json
import os
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from populace_dynamics.income_resources.ssi.records import (
    MaritalUnit,
    SSIResult,
)
from populace_dynamics.income_resources.ssi.runner import (
    CHILD,
    DEFAULT_PYTHON,
    PYTHON_ENV,
    SSIRunner,
    load_pin,
    prepare,
)

from .ssi_invented import invented_case


def test_two_units_match_independent_household_runs_in_person_order():
    python = Path(os.environ.get(PYTHON_ENV, str(DEFAULT_PYTHON))).expanduser()
    if not python.is_file():
        pytest.skip(f"SSI0 interpreter absent: {python}")
    first = invented_case(
        "INVENTED_FIRST_COUPLE",
        couple=True,
        social_security=3600,
        bank_account_assets=2900,
    )
    second = invented_case(
        "INVENTED_SECOND_COUPLE",
        couple=True,
        employment_income=6000,
        bank_account_assets=1000,
    )

    def renamed(case, tag):
        return tuple(
            replace(
                person,
                person_id=f"INVENTED_{tag}_{index}",
                marital_unit_id=f"INVENTED_M_{tag}",
                tax_unit_id=f"INVENTED_T_{tag}",
            )
            for index, person in enumerate(case.household.people)
        )

    first_people = renamed(first, "Z_FIRST")
    second_people = renamed(second, "A_SECOND")
    # Interleave units and reverse their declaration order. Correct results
    # require explicit membership and restoration of the caller's row order.
    people = (
        first_people[0],
        second_people[0],
        first_people[1],
        second_people[1],
    )
    combined = replace(
        first,
        case_id="INVENTED_TWO_UNIT_HOUSEHOLD",
        household=replace(
            first.household,
            household_id="INVENTED_COMBINED_HOUSEHOLD",
            people=people,
            marital_units=tuple(
                MaritalUnit(
                    pair[0].marital_unit_id,
                    tuple(person.person_id for person in pair),
                    {},
                )
                for pair in (second_people, first_people)
            ),
            tax_units={
                pair[0].tax_unit_id: tuple(person.person_id for person in pair)
                for pair in (second_people, first_people)
            },
        ),
    )
    runner = SSIRunner(python, timeout=1800)
    batch = runner.run_many([first, second, combined])
    assert all(
        isinstance(item, SSIResult) for item in batch.outcomes
    ), batch.outcomes
    one, two, together = batch.outcomes

    def interleaved(a, b):
        return (a[0], b[0], a[1], b[1])

    assert together.person_ids == tuple(person.person_id for person in people)
    assert together.federal_ssi == interleaved(
        one.federal_ssi, two.federal_ssi
    )
    for name in together.intermediate:
        assert together.intermediate[name] == interleaved(
            one.intermediate[name], two.intermediate[name]
        )
    assert one.total > 0 and two.total > 0
    assert together.total == one.total + two.total
    assert batch.denominator == runner.accounting.accepted == 3
    assert runner.accounting.refused == 0


def test_compatible_batch_matches_independent_household_runs():
    python = Path(os.environ.get(PYTHON_ENV, str(DEFAULT_PYTHON))).expanduser()
    if not python.is_file():
        pytest.skip(f"SSI0 interpreter absent: {python}")
    first = invented_case(
        "INVENTED_REFERENCE_SINGLE",
        social_security=3600,
        bank_account_assets=1900,
    )
    second = invented_case(
        "INVENTED_REFERENCE_COUPLE",
        couple=True,
        employment_income=6000,
        bank_account_assets=2900,
    )
    runner = SSIRunner(python, timeout=1800)
    references = runner.run_many([first, second])
    assert all(
        isinstance(item, SSIResult) for item in references.outcomes
    ), references.outcomes
    # All source IDs deliberately collide across cases. Pooling must create
    # fresh internal IDs and must restore each case's original person order.
    cases = [
        replace(case, case_id=f"INVENTED_BATCH_CASE_{index}")
        for index, case in enumerate((first, second, first, second))
    ]
    pooled = runner.run_many(cases)
    assert all(
        isinstance(item, SSIResult) for item in pooled.outcomes
    ), pooled.outcomes
    for index, outcome in enumerate(pooled.outcomes):
        reference = references.outcomes[index % 2]
        assert outcome.person_ids == reference.person_ids
        assert outcome.federal_ssi == reference.federal_ssi
        assert outcome.intermediate == reference.intermediate
    assert references.denominator == 2
    assert pooled.denominator == 4
    assert runner.accounting.attempted == runner.accounting.accepted == 6
    assert runner.accounting.refused == 0


def test_one_invalid_request_fails_alone_in_a_pooled_worker_batch():
    python = Path(os.environ.get(PYTHON_ENV, str(DEFAULT_PYTHON))).expanduser()
    if not python.is_file():
        pytest.skip(f"SSI0 interpreter absent: {python}")
    first = invented_case(
        "INVENTED_ISOLATION_SINGLE",
        social_security=3600,
        bank_account_assets=1900,
    )
    second = invented_case(
        "INVENTED_ISOLATION_COUPLE",
        couple=True,
        employment_income=6000,
        bank_account_assets=2900,
    )
    references = SSIRunner(python, timeout=1800).run_many([first, second])
    assert all(
        isinstance(item, SSIResult) for item in references.outcomes
    ), references.outcomes
    jobs = [
        prepare(replace(case, case_id=f"INVENTED_ISOLATION_{index}"))[0]
        for index, case in enumerate((first, second, first, second))
    ]
    # The contract refuses this name, so only a contract defect could send
    # it. The worker must still keep it from refusing its companions.
    jobs[3]["people"][0]["immigration_status"] = "INVENTED_INVALID_STATUS"
    process = subprocess.run(
        [str(python), str(CHILD)],
        input=json.dumps({"pin": load_pin(), "cases": jobs}),
        text=True,
        capture_output=True,
        timeout=3600,
        check=False,
    )
    assert process.returncode == 0, process.stderr[-2000:]
    raw = json.loads(process.stdout)["cases"]
    assert len(raw) == 4
    assert "INVENTED_INVALID_STATUS" in raw[3]["error"]
    for index in range(3):
        reference = references.outcomes[index % 2]
        assert "error" not in raw[index], raw[index]
        assert (
            tuple(float(person["ssi"]) for person in raw[index]["person"])
            == reference.federal_ssi
        )
