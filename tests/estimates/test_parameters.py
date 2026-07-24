"""Fast tests for the first-estimates full-actual parameter loaders."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from populace_dynamics.estimates import parameters


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_synthetic_pe_us(root: Path) -> dict[str, str]:
    documents = {
        "policyengine_us/parameters/gov/ssa/nawi.yaml": """
values:
  1977-01-01: 9779.44
  2020-01-01: 55628.60
""",
        (
            "policyengine_us/parameters/gov/ssa/social_security/"
            "wage_base.yaml"
        ): """
values:
  1979-01-01: 22900
  2022-01-01: 147000
""",
        (
            "policyengine_us/parameters/gov/ssa/social_security/pia/"
            "formula_factors.yaml"
        ): """
brackets:
  - rate: {1979-01-01: 0.9}
    threshold: {}
  - rate: {1979-01-01: 0.32}
    threshold: {}
  - rate: {1979-01-01: 0.15}
    threshold: {}
""",
        (
            "policyengine_us/parameters/gov/ssa/social_security/"
            "full_retirement_age_by_birth_year.yaml"
        ): """
brackets:
  - threshold: {1900-01-01: 1900}
    amount: {1900-01-01: 780}
""",
        (
            "policyengine_us/parameters/gov/ssa/social_security/"
            "retirement_age_adjustment/early_retirement/"
            "reduction_rates.yaml"
        ): """
brackets:
  - rate: {1900-01-01: 0.005555555555555556}
    threshold: {1900-01-01: 0}
  - rate: {1900-01-01: 0.004166666666666667}
    threshold: {1900-01-01: 36}
""",
        (
            "policyengine_us/parameters/gov/ssa/social_security/"
            "retirement_age_adjustment/delayed_retirement/"
            "credit_rates.yaml"
        ): """
brackets:
  - threshold: {1900-01-01: 1900}
    amount: {1900-01-01: 0.08}
""",
        (
            "policyengine_us/parameters/gov/ssa/social_security/"
            "retirement_age_adjustment/max_delayed_years.yaml"
        ): """
values:
  1900-01-01: 4
""",
        (
            "policyengine_us/parameters/gov/irs/payroll/social_security/"
            "rate/employee.yaml"
        ): """
values:
  2013-01-01: 0.062
""",
        (
            "policyengine_us/parameters/gov/irs/payroll/social_security/"
            "rate/employer.yaml"
        ): """
values:
  2013-01-01: 0.062
""",
    }
    hashes = {}
    for relative_path, text in documents.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text.lstrip())
        hashes[relative_path] = _sha256(path)
    return hashes


def _bundle_sha256(hashes: dict[str, str]) -> str:
    payload = json.dumps(hashes, sort_keys=True, separators=(",", ":")) + "\n"
    return hashlib.sha256(payload.encode()).hexdigest()


def _install_synthetic_hash_pins(
    monkeypatch: pytest.MonkeyPatch,
    hashes: dict[str, str],
) -> None:
    ssa = {
        path: digest
        for path, digest in hashes.items()
        if "/parameters/gov/ssa/" in path
    }
    rates = {
        path: digest
        for path, digest in hashes.items()
        if "/parameters/gov/irs/" in path
    }
    monkeypatch.setattr(parameters, "SSA_PARAMETER_SHA256", ssa)
    monkeypatch.setattr(parameters, "RATE_LEG_SHA256", rates)
    monkeypatch.setattr(
        parameters,
        "SSA_PARAMETER_BUNDLE_SHA256",
        _bundle_sha256(ssa),
    )
    monkeypatch.setattr(
        parameters,
        "RATE_LEG_BUNDLE_SHA256",
        _bundle_sha256(rates),
    )
    monkeypatch.setattr(
        parameters,
        "PE_US_CONSUMED_BUNDLE_SHA256",
        _bundle_sha256(hashes),
    )


def test__cola_loader__verifies_committed_anchor_and_converts_to_fraction():
    cola = parameters.load_cola_history()

    assert tuple(cola) == tuple(range(1979, 2023))
    assert cola[1979] == pytest.approx(0.099)
    assert cola[1980] == pytest.approx(0.143)
    assert cola[1983] == pytest.approx(0.035)
    assert cola[2008] == pytest.approx(0.058)
    assert cola[2009] == 0.0
    assert cola[2010] == 0.0
    assert cola[2015] == 0.0
    assert cola[2022] == pytest.approx(0.087)
    assert cola.provenance == {
        "path": str(parameters.COLA_HISTORY_PATH.resolve()),
        "sha256": parameters.COLA_FILE_SHA256,
        "content_sha256": parameters.COLA_CONTENT_SHA256,
        "schema_version": "ssa_cola_history.v1",
        "source_unit": "percent",
        "runtime_unit": "fraction",
        "year_basis": "determination_year",
        "runtime_first_determination_year": 1979,
        "runtime_last_determination_year": 2022,
        "runtime_n_years": 44,
    }


def test__cola_loader__uses_direct_determination_year_lookup():
    cola = parameters.load_cola_history()

    assert cola.rate_for_determination_year(1982) == pytest.approx(0.074)
    assert cola.rate_for_determination_year(1983) == pytest.approx(0.035)
    assert cola.rate_for_determination_year(2021) == pytest.approx(0.059)
    assert cola.rate_for_determination_year(2022) == pytest.approx(0.087)


def test__cola_loader__rejects_rehashed_schema_drift(tmp_path: Path):
    document = json.loads(parameters.COLA_HISTORY_PATH.read_text())
    document["year_basis"] = "first_payment_year"
    drifted = tmp_path / "cola.json"
    drifted.write_text(json.dumps(document))

    with pytest.raises(ValueError, match="determination year"):
        parameters.load_cola_history(
            drifted,
            expected_sha256=_sha256(drifted),
        )


def test__report_loader__loads_full_actuals_rates_and_json_provenance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    hashes = _write_synthetic_pe_us(tmp_path)
    _install_synthetic_hash_pins(monkeypatch, hashes)

    bundle = parameters.load_report_parameters(
        tmp_path,
        pe_us_version="1.752.2",
    )

    assert bundle.ssa.nawi[2020] == 55_628.60
    assert bundle.ssa.wage_base_for(2022) == 147_000.0
    for year in range(2015, 2023):
        assert bundle.rates.employee_for(year) == 0.062
        assert bundle.rates.employer_for(year) == 0.062
        assert bundle.rates.combined_for(year) == 0.124
    assert bundle.cola[2022] == pytest.approx(0.087)
    assert bundle.provenance["schema_version"] == (
        "first_estimates.parameters.v1"
    )
    assert bundle.provenance["policyengine_us"]["version_source"] == (
        "explicit_test_seam"
    )
    assert set(bundle.provenance["bundle_components"]) == {
        "policyengine_us_consumed_files",
        "cola_file",
        "cola_content",
    }
    assert bundle.provenance["bundle_sha256"] == _bundle_sha256(
        bundle.provenance["bundle_components"]
    )
    file_records = bundle.provenance["policyengine_us"]["ssa_parameter_files"]
    assert len(file_records) == 7
    assert all(
        set(record) == {"path", "sha256"} for record in file_records.values()
    )
    assert json.loads(json.dumps(bundle.provenance)) == bundle.provenance


def test__rate_leg_loader__works_independently_without_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    hashes = _write_synthetic_pe_us(tmp_path)
    _install_synthetic_hash_pins(monkeypatch, hashes)

    rates = parameters.load_payroll_rate_legs(
        tmp_path,
        pe_us_version="1.752.2",
    )

    assert rates.employee_for(2015) == 0.062
    assert rates.employer_for(2022) == 0.062
    assert rates.combined_for(2022) == 0.124
    assert rates.provenance["bundle_sha256"] == _bundle_sha256(
        {
            path: digest
            for path, digest in hashes.items()
            if "/parameters/gov/irs/" in path
        }
    )


def test__report_loader__has_no_rate_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    hashes = _write_synthetic_pe_us(tmp_path)
    employee_path = tmp_path / parameters._EMPLOYEE_RATE_PATH
    employee_path.write_text("values:\n  2023-01-01: 0.062\n")
    hashes[parameters._EMPLOYEE_RATE_PATH] = _sha256(employee_path)
    _install_synthetic_hash_pins(monkeypatch, hashes)

    with pytest.raises(KeyError, match="No OASDI payroll rate"):
        parameters.load_report_parameters(
            tmp_path,
            pe_us_version="1.752.2",
        )


def test__report_loader__rejects_hash_drift_before_loading(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    hashes = _write_synthetic_pe_us(tmp_path)
    _install_synthetic_hash_pins(monkeypatch, hashes)
    wage_base = (
        tmp_path
        / "policyengine_us/parameters/gov/ssa/social_security/wage_base.yaml"
    )
    wage_base.write_text(wage_base.read_text() + "# drift\n")

    with pytest.raises(ValueError, match="sha256"):
        parameters.load_report_parameters(
            tmp_path,
            pe_us_version="1.752.2",
        )


def test__report_loader__rejects_wrong_policyengine_version(tmp_path: Path):
    with pytest.raises(RuntimeError, match="1.752.2"):
        parameters.load_report_parameters(
            tmp_path,
            pe_us_version="1.752.1",
        )
