"""SSI0 structural and pin tests; every record below is invented."""

import io
import json
import sys
from dataclasses import replace
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.income_resources.ssi.contract import ResolvedInputs
from populace_dynamics.income_resources.ssi.pinning import check_versions
from populace_dynamics.income_resources.ssi.records import (
    Case,
    CountedRefusal,
    Household,
    MaritalUnit,
    Person,
    RetirementAccount,
    SSIResult,
)
from populace_dynamics.income_resources.ssi.runner import (
    OUTPUTS,
    SSIRunner,
    prepare,
)


@pytest.fixture
def invented_case(monkeypatch):
    # Contract completeness and assumptions have their own independent tests.
    # Here isolate structural guards from any installed policy package.
    monkeypatch.setattr(
        "populace_dynamics.income_resources.ssi.runner.resolve_inputs",
        lambda population, values, **kwargs: ResolvedInputs(
            (
                {"interface_geography": "national"}
                if kwargs.get("entity") == "Context"
                else dict(values)
            ),
            (),
        ),
    )
    person = Person(
        "INVENTED_P",
        "INVENTED_M",
        "INVENTED_T",
        {"age": 70, "is_tax_unit_head": True, "is_tax_unit_spouse": False},
        (),
    )
    household = Household(
        "INVENTED_H",
        (person,),
        (MaritalUnit("INVENTED_M", ("INVENTED_P",), {}),),
        {"INVENTED_T": ("INVENTED_P",)},
        {},
        {},
        {},
        {},
        True,
    )
    return Case(
        "INVENTED_CASE",
        "PSID",
        2026,
        household,
        "frozen_annual_state_equal_twelfths",
    )


@given(st.text().filter(lambda value: value != "6.10.2"))
@settings(deadline=None)
def test_version_mismatch_refuses(actual):
    with pytest.raises(ValueError, match="pinned"):
        check_versions(
            {"policyengine": actual}, {"versions": {"policyengine": "6.10.2"}}
        )


def test_identical_pin_accepts():
    check_versions(
        {"policyengine": "6.10.2"}, {"versions": {"policyengine": "6.10.2"}}
    )


def test_dependency_version_is_part_of_pin():
    with pytest.raises(ValueError, match="numpy"):
        check_versions(
            {"policyengine": "6.10.2", "numpy": "INVENTED_OTHER"},
            {
                "versions": {"policyengine": "6.10.2"},
                "environment_versions": {"numpy": "2.5.4"},
            },
        )


_RECORD_PATH = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz_/.", min_size=1, max_size=30
).filter(lambda path: not path.startswith("../"))
_RECORD_LINE = st.builds(
    lambda path, digest: f"{path},sha256={digest},{len(digest)}",
    _RECORD_PATH,
    st.text(alphabet="ABCDEFabcdef0123456789", min_size=4, max_size=12),
)
_OUTSIDE_LINE = st.builds(
    lambda name, shebang: f"../../../bin/{name},sha256={shebang},1",
    st.text(alphabet="abcdefghijklmnopqrstuvwxyz-", min_size=1, max_size=12),
    st.text(alphabet="ABCDEFabcdef0123456789", min_size=4, max_size=12),
)


@given(
    st.lists(_RECORD_LINE, min_size=1, max_size=6),
    st.lists(_OUTSIDE_LINE, max_size=3),
    st.lists(_OUTSIDE_LINE, max_size=3),
)
@settings(deadline=None)
def test_record_digest_ignores_install_location(inside, here, there):
    # Console scripts outside site-packages carry the interpreter's path.
    from populace_dynamics.income_resources.ssi import _child

    assert _child.record_digest("\n".join([*here, *inside])) == (
        _child.record_digest("\n".join([*inside, *there]))
    )


@given(st.lists(_RECORD_LINE, min_size=1, max_size=6), st.data())
@settings(deadline=None)
def test_record_digest_binds_package_files(inside, data):
    from populace_dynamics.income_resources.ssi import _child

    index = data.draw(st.integers(0, len(inside) - 1))
    changed = [*inside]
    changed[index] = changed[index] + "0"
    assert _child.record_digest("\n".join(inside)) != (
        _child.record_digest("\n".join(changed))
    )


@pytest.mark.parametrize("period", ["2026-01", True, "today"])
def test_unsupported_period_is_counted(invented_case, period):
    runner = SSIRunner("/INVENTED_ABSENT_INTERPRETER")
    with pytest.raises(CountedRefusal) as error:
        runner.run(replace(invented_case, period=period))
    assert error.value.condition == "RULES_ENGINE_GAP"
    assert runner.accounting.attempted == runner.accounting.refused == 1


def test_resource_deeming_is_counted(invented_case):
    household = invented_case.household
    spouse = Person("INVENTED_S", "INVENTED_M", "INVENTED_T", {"age": 50}, ())
    members = ("INVENTED_P", "INVENTED_S")
    household = replace(
        household,
        people=(*household.people, spouse),
        marital_units=(MaritalUnit("INVENTED_M", members, {}),),
        tax_units={"INVENTED_T": members},
    )
    runner = SSIRunner()
    result = runner.run_many([replace(invented_case, household=household)])
    assert result.denominator == 1
    assert result.refusal_counts == {"RULES_ENGINE_GAP": 1}
    assert "deeming" in result.outcomes[0].detail


@given(st.floats(min_value=0.01, max_value=1e9, allow_nan=False))
@settings(deadline=None)
def test_retirement_accounts_refuse_without_losing_owner(balance):
    from .ssi_invented import invented_case

    case = invented_case()
    person = replace(
        case.household.people[0],
        retirement_accounts=(
            RetirementAccount(balance, True, False, False, 0, 0),
        ),
    )
    case = replace(case, household=replace(case.household, people=(person,)))
    result = SSIRunner().run_many([case])
    assert result.denominator == 1
    assert result.refusal_counts == {"RULES_ENGINE_GAP": 1}
    assert person.retirement_accounts[0].balance == balance


def test_retirement_gap_is_counted(invented_case):
    person = replace(
        invented_case.household.people[0],
        retirement_accounts=(
            RetirementAccount(1000, True, False, False, 100, 0),
        ),
    )
    case = replace(
        invented_case,
        household=replace(invented_case.household, people=(person,)),
    )
    result = SSIRunner().run_many([case])
    assert result.refusal_counts == {"RULES_ENGINE_GAP": 1}
    assert "retirement_accounts" in result.outcomes[0].inputs


def test_periodic_payment_branch_refuses_even_with_zero_balance(invented_case):
    person = replace(
        invented_case.household.people[0],
        retirement_accounts=(RetirementAccount(0, False, True, False, 0, 0),),
    )
    case = replace(
        invented_case,
        household=replace(invented_case.household, people=(person,)),
    )
    result = SSIRunner().run_many([case])
    assert result.refusal_counts == {"RULES_ENGINE_GAP": 1}
    assert "retirement_accounts" in result.outcomes[0].inputs


@given(st.integers(min_value=1, max_value=20))
@settings(deadline=None)
def test_batch_accounting_retains_all_refusals(count):
    # Invalid annual period refuses before touching a contract or interpreter.
    cases = [
        Case(f"INVENTED_{i}", "PSID", "2026-01", None, "")
        for i in range(count)
    ]
    runner = SSIRunner()
    batch = runner.run_many(cases)
    assert batch.denominator == count
    assert batch.refusal_counts == {"RULES_ENGINE_GAP": count}
    assert runner.accounting.attempted == runner.accounting.refused == count


@given(st.one_of(st.none(), st.integers(), st.lists(st.integers())))
@settings(deadline=None)
def test_malformed_population_is_counted(population):
    from .ssi_invented import invented_case

    runner = SSIRunner("/INVENTED_ABSENT_INTERPRETER")
    with pytest.raises(CountedRefusal) as error:
        runner.run(replace(invented_case(), population=population))
    assert error.value.condition == "INPUT_CONTRACT_GAP"
    assert runner.accounting.attempted == runner.accounting.refused == 1


@pytest.mark.parametrize(
    "field",
    ["people", "marital_units", "retirement_accounts", "inputs", "overrides"],
)
def test_malformed_record_field_is_counted(invented_case, field):
    household = invented_case.household
    if field in ("people", "marital_units"):
        case = replace(
            invented_case, household=replace(household, **{field: (None,)})
        )
    elif field == "retirement_accounts":
        person = replace(household.people[0], retirement_accounts=(None,))
        case = replace(
            invented_case, household=replace(household, people=(person,))
        )
    elif field == "inputs":
        case = replace(
            invented_case, household=replace(household, inputs=None)
        )
    else:
        case = replace(invented_case, parameter_overrides=None)
    runner = SSIRunner("/INVENTED_ABSENT_INTERPRETER")
    result = runner.run_many([case])
    assert result.denominator == 1
    assert result.refusal_counts == {"INPUT_CONTRACT_GAP": 1}
    assert runner.accounting.attempted == runner.accounting.refused == 1


def test_duplicate_case_ids_are_counted(invented_case):
    runner = SSIRunner("/INVENTED_ABSENT_INTERPRETER")
    result = runner.run_many([invented_case, invented_case])
    assert result.denominator == 2
    assert result.refusal_counts == {"INPUT_CONTRACT_GAP": 2}
    assert runner.accounting.attempted == runner.accounting.refused == 2


def test_missing_interpreter_is_counted(invented_case):
    # Missing interpreter is operationally unsupported and retains the case.
    result = SSIRunner("/INVENTED_ABSENT_INTERPRETER").run_many(
        [invented_case]
    )
    assert result.refusal_counts == {"RULES_ENGINE_GAP": 1}


def test_ownership_gap_is_population_specific(invented_case):
    case = replace(
        invented_case,
        population="Microcosm",
        household=replace(
            invented_case.household,
            resource_ownership_validated=False,
        ),
    )
    result = SSIRunner().run_many([case])
    assert result.refusal_counts == {"FRAME_LACKS_RESOURCES": 1}


def test_links_are_checked(invented_case):
    person = replace(
        invented_case.household.people[0], tax_unit_id="INVENTED_WRONG"
    )
    case = replace(
        invented_case,
        household=replace(invented_case.household, people=(person,)),
    )
    result = SSIRunner().run_many([case])
    assert result.refusal_counts == {"INPUT_CONTRACT_GAP": 1}


def test_preparation_preserves_explicit_values(invented_case):
    job, assumptions = prepare(invented_case)
    assert job["people"] == [
        {"age": 70, "is_tax_unit_head": True, "is_tax_unit_spouse": False}
    ]
    assert assumptions == ()


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {},
        {"cases": []},
        {"cases": [None]},
        {"cases": [{"person": []}]},
        {"cases": [{"person": [{"ssi": float("nan")}]}]},
    ],
)
def test_malformed_response_is_counted(invented_case, payload):
    with patch(
        "populace_dynamics.income_resources.ssi.runner.subprocess.run",
        return_value=SimpleNamespace(returncode=0, stdout=json.dumps(payload)),
    ):
        runner = SSIRunner(sys.executable)
        batch = runner.run_many([invented_case])
    assert batch.refusal_counts == {"RULES_ENGINE_GAP": 1}
    assert runner.accounting.attempted == runner.accounting.refused == 1


def test_invented_fixture_has_every_input():
    from populace_dynamics.income_resources.ssi.contract import load_contract

    from .ssi_invented import INVENTED_INPUTS

    names = {
        row["name"]
        for row in load_contract()["rows"]
        if row["kind"] == "engine"
    }
    assert set(INVENTED_INPUTS) == names


@given(st.lists(st.text(min_size=1), max_size=5))
@settings(deadline=None)
def test_dependency_changing_overrides_refuse(sources):
    from .ssi_invented import invented_case

    case = replace(
        invented_case(),
        parameter_overrides={
            "gov.ssa.ssi.income.sources.earned": sources,
        },
    )
    result = SSIRunner().run_many([case])
    assert result.refusal_counts == {"RULES_ENGINE_GAP": 1}


def test_singleton_roles_must_match_links(invented_case):
    person = replace(
        invented_case.household.people[0],
        inputs={
            "age": 70,
            "is_tax_unit_head": False,
            "is_tax_unit_spouse": True,
        },
    )
    case = replace(
        invented_case,
        household=replace(invented_case.household, people=(person,)),
    )
    result = SSIRunner().run_many([case])
    assert result.refusal_counts == {"INPUT_CONTRACT_GAP": 1}


@given(st.floats(min_value=1, max_value=1e8, allow_nan=False))
@settings(deadline=None)
def test_engine_output_above_its_fbr_is_counted(excess):
    from .ssi_invented import invented_case

    person = dict.fromkeys(OUTPUTS, 0)
    person.update(
        ssi=1000 + excess,
        ssi_if_takes_up=1000 + excess,
        ssi_amount_if_eligible=1000,
    )
    payload = {"versions": {}, "cases": [{"person": [person]}]}
    with patch(
        "populace_dynamics.income_resources.ssi.runner.subprocess.run",
        return_value=SimpleNamespace(returncode=0, stdout=json.dumps(payload)),
    ):
        result = SSIRunner(sys.executable).run_many([invented_case()])
    assert result.refusal_counts == {"RULES_ENGINE_GAP": 1}


@pytest.mark.parametrize("different_policy", [False, True])
def test_worker_keeps_policy_changes_out_of_combined_batches(
    monkeypatch, different_policy
):
    from populace_dynamics.income_resources.ssi import _child

    calls = []

    def household(**kwargs):
        amount = kwargs["reform"]["INVENTED_PARAMETER"]
        calls.append(("household", amount))
        return {"person": [{"ssi": amount}]}

    def batch(cases, pe):
        calls.append(("batch", len(cases)))
        return [
            {"person": [{"ssi": case["reform"]["INVENTED_PARAMETER"]}]}
            for case in cases
        ]

    pe = ModuleType("policyengine")
    pe.us = SimpleNamespace(calculate_household=household)
    dataset = ModuleType("dataset_worker")
    dataset.calculate_dataset_batch = batch
    monkeypatch.setitem(sys.modules, "policyengine", pe)
    monkeypatch.setitem(sys.modules, "dataset_worker", dataset)
    cases = []
    for index in range(4):
        case = dict.fromkeys(_child.HOUSEHOLD_ARGUMENTS, {})
        case.update(
            year=2026,
            reform={
                "INVENTED_PARAMETER": (
                    2 if different_policy and index == 3 else 1
                )
            },
            extra_variables=["ssi"],
            person_links=[{"person_id": f"INVENTED_{index}"}],
        )
        cases.append(case)
    pin = {"versions": {}, "record_sha256": {}}
    monkeypatch.setattr(
        sys, "stdin", io.StringIO(json.dumps({"pin": pin, "cases": cases}))
    )
    stdout = io.StringIO()
    monkeypatch.setattr(sys, "stdout", stdout)
    _child.main()
    payload = json.loads(stdout.getvalue())
    assert [row["person"][0]["ssi"] for row in payload["cases"]] == [
        1,
        1,
        1,
        2 if different_policy else 1,
    ]
    assert calls == (
        [
            ("household", 1),
            ("household", 1),
            ("household", 1),
            ("household", 2),
        ]
        if different_policy
        else [("batch", 4)]
    )


def invented_worker_case(index, *, valid=True, policy=1, pooled=True):
    """An invented worker request; ``valid`` stands in for an engine check."""
    from populace_dynamics.income_resources.ssi import _child

    case = dict.fromkeys(_child.HOUSEHOLD_ARGUMENTS, {})
    case.update(
        year=2026,
        reform={"INVENTED_PARAMETER": policy},
        extra_variables=["ssi"],
        people={"INVENTED_ID": index, "INVENTED_VALID": valid},
    )
    if pooled:
        case["person_links"] = [{"person_id": f"INVENTED_{index}"}]
    return case


def run_invented_worker(cases, calls=None):
    """Run the worker on invented requests with stubbed public interfaces.

    The stub engine raises for an invalid request whether it runs alone or
    pooled, as the pinned enum validator does, and a pool's results agree
    with single runs. So any dependence on companions is the worker's.
    """
    from populace_dynamics.income_resources.ssi import _child

    calls = [] if calls is None else calls

    def value(arguments):
        people = arguments["people"]
        if not people["INVENTED_VALID"]:
            raise ValueError("Invalid value(s) ['INVENTED_INVALID_STATUS']")
        amount = arguments["reform"]["INVENTED_PARAMETER"]
        return {"person": [{"ssi": 1000 * amount + people["INVENTED_ID"]}]}

    def household(**arguments):
        calls.append("household")
        return value(arguments)

    def batch(requests, pe):
        calls.append(("batch", len(requests)))
        return [value(request) for request in requests]

    pe = ModuleType("policyengine")
    pe.us = SimpleNamespace(calculate_household=household)
    dataset = ModuleType("dataset_worker")
    dataset.calculate_dataset_batch = batch
    job = {"pin": {"versions": {}, "record_sha256": {}}, "cases": cases}
    stdout = io.StringIO()
    with (
        patch.dict(
            sys.modules, {"policyengine": pe, "dataset_worker": dataset}
        ),
        patch.object(sys, "stdin", io.StringIO(json.dumps(job))),
        patch.object(sys, "stdout", stdout),
    ):
        _child.main()
    return json.loads(stdout.getvalue())["cases"]


@pytest.mark.parametrize("size", [3, 4, 5])
def test_one_failing_request_fails_alone_in_a_pooled_batch(size):
    cases = [
        invented_worker_case(index, valid=index != 1) for index in range(size)
    ]
    calls = []
    outcomes = run_invented_worker(cases, calls)
    assert outcomes[1] == {
        "error": "ValueError: Invalid value(s) ['INVENTED_INVALID_STATUS']"
    }
    assert [
        outcome for index, outcome in enumerate(outcomes) if index != 1
    ] == [
        {"person": [{"ssi": 1000 + index}]}
        for index in range(size)
        if index != 1
    ]
    # Four or more compatible requests pool; a failed pool reruns each alone.
    assert (
        calls == ([("batch", size)] if size > 3 else []) + ["household"] * size
    )


@settings(deadline=None, max_examples=200)
@given(
    valid=st.lists(st.booleans(), max_size=8),
    pooled=st.booleans(),
    deviant=st.none() | st.integers(min_value=0, max_value=7),
    unlinked=st.none() | st.integers(min_value=0, max_value=7),
)
def test_worker_outcomes_do_not_depend_on_companions(
    valid, pooled, deviant, unlinked
):
    # Batches are compatible unless one request's policy differs or one
    # request lacks links, so pools of four or more are drawn often.
    cases = [
        invented_worker_case(
            index,
            valid=is_valid,
            policy=2 if index == deviant else 1,
            pooled=pooled and index != unlinked,
        )
        for index, is_valid in enumerate(valid)
    ]
    together = run_invented_worker(cases)
    assert len(together) == len(cases)
    for case, outcome in zip(cases, together, strict=True):
        assert outcome == run_invented_worker([case])[0]
        assert ("error" in outcome) == (not case["people"]["INVENTED_VALID"])


def test_invalid_enum_name_refuses_only_its_own_case_before_dispatch():
    from .ssi_invented import invented_case

    cases = [invented_case(f"INVENTED_CASE_{index}") for index in range(3)]
    cases.append(
        invented_case(
            "INVENTED_CASE_INVALID",
            immigration_status="INVENTED_INVALID_STATUS",
        )
    )
    sent = []

    def worker(command, *, input, **kwargs):
        job = json.loads(input)
        sent.append(job["cases"])
        person = dict.fromkeys(OUTPUTS, 0)
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "versions": {},
                    "cases": [{"person": [person]} for _ in job["cases"]],
                }
            ),
        )

    with patch(
        "populace_dynamics.income_resources.ssi.runner.subprocess.run",
        side_effect=worker,
    ):
        result = SSIRunner(sys.executable).run_many(cases)
    assert [len(batch) for batch in sent] == [3]
    assert [case["case_id"] for case in sent[0]] == [
        f"INVENTED_CASE_{index}" for index in range(3)
    ]
    assert result.refusal_counts == {"INPUT_CONTRACT_GAP": 1}
    assert result.outcomes[3].inputs == ("immigration_status",)
    assert [outcome.case_id for outcome in result.outcomes[:3]] == [
        f"INVENTED_CASE_{index}" for index in range(3)
    ]
    assert all(
        isinstance(outcome, SSIResult) for outcome in result.outcomes[:3]
    )
