"""Native-entity bridge protocol checks using invented, mocked results."""

from __future__ import annotations

import copy
import json
from dataclasses import asdict
from pathlib import Path

import pytest

from populace_dynamics.bridge import policyengine_us as bridge


@pytest.fixture
def named_protocol(monkeypatch):
    interpreter = Path("/invented/python")
    installation = bridge.PolicyEngineUSInstallation(
        python=str(interpreter),
        python_version="3.13.9",
        package_dir="/invented/site/policyengine_us",
        version="2.61.0",
        core_version="3.22.0",
        location="/invented/site",
        record_path="/invented/site/policyengine_us-2.61.0.dist-info/RECORD",
        record_sha256="a" * 64,
        direct_url=None,
        installer="pip",
    )
    household = bridge.BridgeHousehold(
        "invented",
        "TX",
        (bridge.BridgePerson("older", 70), bridge.BridgePerson("younger", 40)),
        (("older",), ("younger",)),
        (("older", "younger"),),
        (("older",), ("younger",)),
    )
    situation = bridge.to_situation(household, 2026)
    case = bridge.RunCase("invented", situation, expected_state="TX")
    entity_ids = {key: list(value) for key, value in situation.items()}
    payload = {
        "policyengine_us_version": installation.version,
        "policyengine_core_version": installation.core_version,
        "policyengine_us_package": installation.package_dir + "/__init__.py",
        "installation": asdict(installation),
        "cases": [
            {
                "case_id": "invented",
                "state_code": ["TX"],
                "values": {
                    "income_tax": [120.25, -30.5],
                    "filing_status": ["SINGLE", "SINGLE"],
                },
                "entity_ids": entity_ids,
                "variable_entities": {
                    "income_tax": "tax_units",
                    "filing_status": "tax_units",
                },
            }
        ],
    }
    calls = {}

    def checked(python, **kwargs):
        calls["checked"] = (python, kwargs)
        return installation, {"kind": "index"}

    def run(python, source, stdin, timeout):
        calls["run"] = (python, source, json.loads(stdin), timeout)
        return copy.deepcopy(payload)

    monkeypatch.setattr(bridge, "_interpreter", lambda python: interpreter)
    monkeypatch.setattr(bridge, "_checked_installation", checked)
    monkeypatch.setattr(bridge, "_run_child", run)
    return case, payload, calls, installation


def _run(case, **kwargs):
    return bridge.run_policyengine_us_variables(
        [case],
        year=2026,
        variables=("income_tax", "filing_status"),
        **kwargs,
    )


def test_native_arrays_preserve_order_enum_names_and_source_checks(
    named_protocol,
):
    case, _, calls, installation = named_protocol
    result = _run(
        case,
        required_version="2.61.0",
        expected_package_record_digest="b" * 64,
    )
    run = result.runs["invented"]
    assert run.values["income_tax"] == (120.25, -30.5)
    assert run.values["filing_status"] == ("SINGLE", "SINGLE")
    assert run.entity_ids["tax_units"] == tuple(case.situation["tax_units"])
    assert run.variable_entities["income_tax"] == "tax_units"
    assert result.installation == installation
    assert result.source == {"kind": "index"}
    assert calls["checked"][1] == {
        "require_published": True,
        "verify_files": True,
        "expected_package_record_digest": "b" * 64,
    }
    assert calls["run"][2]["variables"] == ["income_tax", "filing_status"]
    assert calls["run"][2]["cases"][0]["situation"] == case.situation


@pytest.mark.parametrize(
    "variables",
    [
        (),
        "income_tax",
        ("",),
        (" ",),
        ("income_tax@2026",),
        (None,),
        ("income_tax", "income_tax"),
    ],
)
def test_invalid_variable_names_are_refused_before_interpreter(variables):
    with pytest.raises(ValueError, match="variable"):
        bridge.run_policyengine_us_variables(
            [bridge.RunCase("a", {})], year=2026, variables=variables
        )


@pytest.mark.parametrize("ids", [(), ("",), (" ",), ("a", "a")])
def test_invalid_case_ids_are_refused_before_interpreter(ids):
    with pytest.raises(ValueError, match="case|IDs"):
        bridge.run_policyengine_us_variables(
            [bridge.RunCase(case_id, {}) for case_id in ids],
            year=2026,
            variables=("income_tax",),
        )


def test_wrong_required_release_is_refused_before_calculation(named_protocol):
    case, _, calls, _ = named_protocol
    with pytest.raises(
        bridge.UnpublishedSourceError, match="required version"
    ):
        _run(case, required_version="2.60.0")
    assert "run" not in calls


@pytest.mark.parametrize("value", [float("nan"), float("inf"), None, [1]])
def test_nonfinite_and_nonscalar_output_is_refused(named_protocol, value):
    case, payload, _, _ = named_protocol
    payload["cases"][0]["values"]["income_tax"][0] = value
    with pytest.raises(
        bridge.PolicyEngineUSUnavailable, match="finite scalar"
    ):
        _run(case)


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate_case",
        "missing_case",
        "unknown_case",
        "missing_variable",
        "shape",
        "entity_ids",
        "installation",
        "version",
        "state",
    ],
)
def test_malformed_protocol_is_refused(named_protocol, mutation):
    case, payload, _, _ = named_protocol
    raw = payload["cases"][0]
    if mutation == "duplicate_case":
        payload["cases"].append(copy.deepcopy(raw))
    elif mutation == "missing_case":
        payload["cases"].clear()
    elif mutation == "unknown_case":
        raw["case_id"] = "unknown"
    elif mutation == "missing_variable":
        del raw["values"]["income_tax"]
    elif mutation == "shape":
        raw["values"]["income_tax"].append(0)
    elif mutation == "entity_ids":
        raw["entity_ids"]["tax_units"][0] = "other"
    elif mutation == "installation":
        payload["installation"]["record_sha256"] = "changed"
    elif mutation == "version":
        payload["policyengine_us_version"] = "other"
    elif mutation == "state":
        raw["state_code"] = ["CA"]
    with pytest.raises(bridge.PolicyEngineUSUnavailable, match="malformed"):
        _run(case)


def test_boolean_results_remain_boolean(named_protocol):
    case, payload, _, _ = named_protocol
    payload["cases"][0]["values"]["income_tax"] = [True, False]
    assert _run(case).runs["invented"].values["income_tax"] == (True, False)


def test_empty_entity_identifier_is_refused(named_protocol):
    case, _, _, _ = named_protocol
    situation = copy.deepcopy(case.situation)
    situation["people"][""] = situation["people"].pop("older")
    with pytest.raises(ValueError, match="nonempty string IDs"):
        _run(bridge.RunCase("bad", situation))
