"""Pinned, full-actual parameter bundle for the first-estimates report.

The projection input factory deliberately replaces post-boundary SSA
parameters.  The report must not use that bundle.  This module independently
loads the full policyengine-us 1.752.2 SSA bundle, both OASDI payroll-rate
legs, and the committed SSA COLA extraction.  Every consumed file is guarded
by a raw sha256 and represented in JSON-ready configuration provenance.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from populace_dynamics.ss import params as ss_params
from populace_dynamics.ss.params import SSAParameters

__all__ = [
    "COLA_CONTENT_SHA256",
    "COLA_FILE_SHA256",
    "COLA_HISTORY_PATH",
    "COLASeries",
    "PINNED_PE_US_VERSION",
    "PayrollRateLegs",
    "ReportParameters",
    "load_cola_history",
    "load_payroll_rate_legs",
    "load_report_parameters",
]

PINNED_PE_US_VERSION = "1.752.2"
REPORT_YEARS = tuple(range(2015, 2023))
REQUIRED_COLA_PAYMENT_YEARS = tuple(range(1979, 2023))

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
COLA_HISTORY_PATH = (
    _PROJECT_ROOT / "data" / "external" / "ssa_cola_history.json"
)
COLA_FILE_SHA256 = (
    "e8ffa0e51e08a7917904a959e6918f10cbdd3a554f975e3e1211f93aaa1aca29"
)
COLA_CONTENT_SHA256 = (
    "488618df8a8ea05f929d0f8ecc7eb79d240bee39adaea0572e9d73d339a54d69"
)

SSA_PARAMETER_SHA256 = {
    "policyengine_us/parameters/gov/ssa/nawi.yaml": (
        "9db55fe9ea25447a139767c7719b32920982dd2a65887c8fc0ddb12a2dcf7c53"
    ),
    "policyengine_us/parameters/gov/ssa/social_security/wage_base.yaml": (
        "c0d8b9b3cf76ece610f27aede27224f32c668bcde0da7e424c5cd3ea8c83e610"
    ),
    (
        "policyengine_us/parameters/gov/ssa/social_security/pia/"
        "formula_factors.yaml"
    ): "0df7562dfeace3f662b2c3867a5ac506b57868f8fe41db48f20027ad6e9b6b7e",
    (
        "policyengine_us/parameters/gov/ssa/social_security/"
        "full_retirement_age_by_birth_year.yaml"
    ): "9974a3e24766c37b3bda0beb6507843bf170479c1422d391452b10cc52b16dcb",
    (
        "policyengine_us/parameters/gov/ssa/social_security/"
        "retirement_age_adjustment/early_retirement/reduction_rates.yaml"
    ): "ddcdfcfc0ebcf558b9c8f9bd4dc6ac09cb25f77c299e9c9895011b50d14f2147",
    (
        "policyengine_us/parameters/gov/ssa/social_security/"
        "retirement_age_adjustment/delayed_retirement/credit_rates.yaml"
    ): "317da013a15716c377850759f9748b4903b5e24f72e85a62e4b4fdbf2bb2dfa4",
    (
        "policyengine_us/parameters/gov/ssa/social_security/"
        "retirement_age_adjustment/max_delayed_years.yaml"
    ): "8b181708b5f0a993e5a0fd0705ed8cf916fddbc616b476c25d1f95be78cc93a4",
}
RATE_LEG_SHA256 = {
    (
        "policyengine_us/parameters/gov/irs/payroll/social_security/"
        "rate/employee.yaml"
    ): "a9ba2b1f3cd50c0febfc01b94121c97094925d80716fe7b4c366c2fb8a1085ff",
    (
        "policyengine_us/parameters/gov/irs/payroll/social_security/"
        "rate/employer.yaml"
    ): "19591c5dada437d46ff95279b549f77a950c192927b8146ef7e0a7159f7aa9c6",
}
SSA_PARAMETER_BUNDLE_SHA256 = (
    "f2c4069caf30807f99183e2a4f852ad54930fdb7058d2ea303f295eeeda49387"
)
RATE_LEG_BUNDLE_SHA256 = (
    "76dd1ba4f67df1d87eaa26882a51315d76757cf249bd55f89529a3ef4410b3d8"
)
PE_US_CONSUMED_BUNDLE_SHA256 = (
    "e89a1fa01c3348d68f2c10eee0d572a62495b3e524dc1d39b30bc4f0d6ecec9d"
)

_EMPLOYEE_RATE_PATH = next(
    path for path in RATE_LEG_SHA256 if path.endswith("employee.yaml")
)
_EMPLOYER_RATE_PATH = next(
    path for path in RATE_LEG_SHA256 if path.endswith("employer.yaml")
)


@dataclass(frozen=True)
class PayrollRateLegs:
    """Employee and employer OASDI rate step functions."""

    employee_by_effective_year: dict[int, float]
    employer_by_effective_year: dict[int, float]
    provenance: dict[str, Any]

    @staticmethod
    def _value_for(values: Mapping[int, float], year: int) -> float:
        applicable = [effective for effective in values if effective <= year]
        if not applicable:
            raise KeyError(f"No OASDI payroll rate on or before {year}.")
        return float(values[max(applicable)])

    def employee_for(self, year: int) -> float:
        """Return the employee OASDI rate in effect in ``year``."""

        return self._value_for(self.employee_by_effective_year, year)

    def employer_for(self, year: int) -> float:
        """Return the employer OASDI rate in effect in ``year``."""

        return self._value_for(self.employer_by_effective_year, year)

    def combined_for(self, year: int) -> float:
        """Return the combined employee-plus-employer OASDI rate."""

        return self.employee_for(year) + self.employer_for(year)


@dataclass(frozen=True)
class COLASeries(Mapping[int, float]):
    """COLA fractions keyed honestly by first payment year.

    The committed artifact is payment-year keyed.  Mapping access preserves
    that basis.  ``rate_for_determination_year`` performs the explicit
    historical timing conversion required by the design's determination-year
    compounding loop.
    """

    by_payment_year: dict[int, float]
    provenance: dict[str, Any]

    def __getitem__(self, payment_year: int) -> float:
        return self.by_payment_year[payment_year]

    def __iter__(self) -> Iterator[int]:
        return iter(self.by_payment_year)

    def __len__(self) -> int:
        return len(self.by_payment_year)

    @staticmethod
    def payment_year_for_determination_year(
        determination_year: int,
    ) -> int:
        """Translate an SSA determination year to its first payment year.

        The 1975-1982 adjustments first appeared in July payments of the
        named year.  From the December 1983 determination onward, an
        adjustment first appears in January payments of the next year.
        """

        if determination_year <= 1982:
            return determination_year
        return determination_year + 1

    def rate_for_determination_year(self, determination_year: int) -> float:
        """Return the fraction for an adjustment's determination year."""

        payment_year = self.payment_year_for_determination_year(
            determination_year
        )
        try:
            return self[payment_year]
        except KeyError as error:
            raise KeyError(
                f"COLA determination year {determination_year} maps to "
                f"first payment year {payment_year}, which is outside the "
                "committed 1979-2022 payment-year runtime span."
            ) from error


@dataclass(frozen=True)
class ReportParameters:
    """Independent statutory parameters consumed by the report."""

    ssa: SSAParameters
    rates: PayrollRateLegs
    cola: COLASeries
    provenance: dict[str, Any]


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical_mapping_sha256(values: Mapping[str, str]) -> str:
    encoded = (
        json.dumps(dict(values), sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()
    return _sha256(encoded)


def _verify_files(
    root: Path,
    expected_by_relative_path: Mapping[str, str],
    *,
    expected_bundle_sha256: str,
) -> tuple[dict[str, dict[str, str]], dict[str, str]]:
    records: dict[str, dict[str, str]] = {}
    actual_by_relative_path: dict[str, str] = {}
    for relative_path, expected in expected_by_relative_path.items():
        path = root / relative_path
        try:
            actual = _sha256(path.read_bytes())
        except FileNotFoundError as error:
            raise FileNotFoundError(
                f"Pinned policyengine-us parameter file is absent: {path}"
            ) from error
        if actual != expected:
            raise ValueError(
                f"policyengine-us parameter {path} sha256 {actual} != "
                f"pinned {expected}; refusing a non-1.752.2 parameter tree."
            )
        actual_by_relative_path[relative_path] = actual
        records[relative_path] = {
            "path": str(path.resolve()),
            "sha256": actual,
        }

    bundle_sha256 = _canonical_mapping_sha256(actual_by_relative_path)
    if bundle_sha256 != expected_bundle_sha256:
        raise ValueError(
            f"parameter-file bundle sha256 {bundle_sha256} != pinned "
            f"{expected_bundle_sha256}."
        )
    return records, actual_by_relative_path


def _installed_distribution() -> importlib.metadata.Distribution:
    try:
        return importlib.metadata.distribution("policyengine-us")
    except importlib.metadata.PackageNotFoundError as error:
        raise RuntimeError(
            "policyengine-us is not installed; the first-estimates report "
            "requires policyengine-us==1.752.2."
        ) from error


def _assert_parameter_dir_binding(
    root: Path,
    distribution: importlib.metadata.Distribution,
) -> None:
    resolved = (root / ss_params._SSA).resolve()
    versioned = (
        Path(distribution.locate_file("policyengine_us")).resolve()
        / "parameters"
        / "gov"
        / "ssa"
    )
    if resolved != versioned:
        raise RuntimeError(
            "The checkout resolved by ss.params is not the "
            "metadata-versioned policyengine-us install. Point "
            "POPULACE_DYNAMICS_PE_US_DIR at the 1.752.2 install."
        )


def _effective_year_values(path: Path) -> dict[int, float]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or not isinstance(
        document.get("values"), dict
    ):
        raise ValueError(f"Rate parameter {path} has no values mapping.")
    result: dict[int, float] = {}
    for raw_effective_date, raw_value in document["values"].items():
        try:
            year = int(str(raw_effective_date)[:4])
            value = float(raw_value)
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"Rate parameter {path} has an invalid value row "
                f"{raw_effective_date!r}: {raw_value!r}."
            ) from error
        if year in result:
            raise ValueError(
                f"Rate parameter {path} has multiple changes in {year}; "
                "the report's annual step loader cannot collapse them."
            )
        result[year] = value
    if not result:
        raise ValueError(f"Rate parameter {path} has an empty values mapping.")
    return dict(sorted(result.items()))


def _load_rate_legs(
    root: Path,
    file_records: Mapping[str, dict[str, str]],
    *,
    bundle_sha256: str,
) -> PayrollRateLegs:
    employee = _effective_year_values(root / _EMPLOYEE_RATE_PATH)
    employer = _effective_year_values(root / _EMPLOYER_RATE_PATH)

    rates = PayrollRateLegs(
        employee_by_effective_year=employee,
        employer_by_effective_year=employer,
        provenance={},
    )
    for year in REPORT_YEARS:
        if rates.employee_for(year) != 0.062:
            raise ValueError(
                f"Employee OASDI rate for {year} is "
                f"{rates.employee_for(year)!r}, expected 0.062."
            )
        if rates.employer_for(year) != 0.062:
            raise ValueError(
                f"Employer OASDI rate for {year} is "
                f"{rates.employer_for(year)!r}, expected 0.062."
            )
        if rates.combined_for(year) != 0.124:
            raise ValueError(
                f"Combined OASDI rate for {year} is "
                f"{rates.combined_for(year)!r}, expected 0.124."
            )

    provenance: dict[str, Any] = {
        "employee": {
            **file_records[_EMPLOYEE_RATE_PATH],
            "effective_values": {
                str(year): value for year, value in employee.items()
            },
        },
        "employer": {
            **file_records[_EMPLOYER_RATE_PATH],
            "effective_values": {
                str(year): value for year, value in employer.items()
            },
        },
        "bundle_sha256": bundle_sha256,
        "bundle_hash_basis": (
            "sha256 of canonical JSON {relative_path: raw_sha256} "
            "(sorted keys, compact separators, trailing newline)"
        ),
        "asserted_report_years": list(REPORT_YEARS),
        "asserted_employee_rate": 0.062,
        "asserted_employer_rate": 0.062,
        "asserted_combined_rate": 0.124,
    }
    return PayrollRateLegs(
        employee_by_effective_year=employee,
        employer_by_effective_year=employer,
        provenance=provenance,
    )


def _resolve_pinned_root(
    pe_us_dir: Path | None,
    pe_us_version: str | None,
) -> tuple[Path, str, str]:
    distribution = None
    if pe_us_version is None:
        distribution = _installed_distribution()
        resolved_version = distribution.version
        version_source = "importlib.metadata"
    else:
        resolved_version = str(pe_us_version)
        version_source = "explicit_test_seam"
    if resolved_version != PINNED_PE_US_VERSION:
        raise RuntimeError(
            f"policyengine-us {resolved_version!r} != pinned "
            f"{PINNED_PE_US_VERSION!r}; the first-estimates report requires "
            "the registered full-actual parameter vintage."
        )
    root = ss_params._resolve_pe_us(pe_us_dir).resolve()
    if distribution is not None:
        _assert_parameter_dir_binding(root, distribution)
    return root, resolved_version, version_source


def load_payroll_rate_legs(
    pe_us_dir: Path | None = None,
    *,
    pe_us_version: str | None = None,
) -> PayrollRateLegs:
    """Load both pinned OASDI rate legs with no constant fallback."""

    root, _resolved_version, _version_source = _resolve_pinned_root(
        pe_us_dir,
        pe_us_version,
    )
    records, _actual = _verify_files(
        root,
        RATE_LEG_SHA256,
        expected_bundle_sha256=RATE_LEG_BUNDLE_SHA256,
    )
    return _load_rate_legs(
        root,
        records,
        bundle_sha256=RATE_LEG_BUNDLE_SHA256,
    )


def _require_mapping(document: Mapping[str, Any], key: str) -> Mapping:
    value = document.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"COLA history field {key!r} must be an object.")
    return value


def load_cola_history(
    path: Path = COLA_HISTORY_PATH,
    *,
    expected_sha256: str = COLA_FILE_SHA256,
    expected_content_sha256: str = COLA_CONTENT_SHA256,
) -> COLASeries:
    """Load and integrity-check the committed payment-year COLA history."""

    path = Path(path)
    raw = path.read_bytes()
    raw_sha256 = _sha256(raw)
    if raw_sha256 != expected_sha256:
        raise ValueError(
            f"COLA history {path} sha256 {raw_sha256} != pinned "
            f"{expected_sha256}; refusing a changed committed extraction."
        )

    try:
        document = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError(f"COLA history {path} is not valid JSON.") from error
    if not isinstance(document, dict):
        raise ValueError("COLA history root must be a JSON object.")
    if document.get("schema_version") != "ssa_cola_history.v1":
        raise ValueError(
            "COLA history schema_version must be 'ssa_cola_history.v1'."
        )
    if document.get("unit") != "percent":
        raise ValueError("COLA history unit must be 'percent'.")
    if document.get("year_basis") != "first_payment_year":
        raise ValueError(
            "COLA history must be explicitly keyed by first payment year."
        )

    data = _require_mapping(document, "data")
    provenance = _require_mapping(document, "provenance")
    build = _require_mapping(document, "build")
    validation = _require_mapping(document, "validation")
    canonical_content = (
        json.dumps(dict(data), sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()
    content_sha256 = _sha256(canonical_content)
    internal_hashes = (
        provenance.get("content_sha256"),
        build.get("content_sha256"),
    )
    if content_sha256 != expected_content_sha256 or internal_hashes != (
        expected_content_sha256,
        expected_content_sha256,
    ):
        raise ValueError(
            "COLA history content hash does not match its pinned and "
            "internally recorded sha256 values."
        )

    required_coverage = validation.get("required_coverage")
    if required_coverage != {
        "first_year": 1979,
        "last_year": 2022,
        "n_years": 44,
        "complete": True,
    }:
        raise ValueError(
            "COLA history required_coverage is not the frozen 1979-2022 "
            "payment-year span."
        )

    rates: dict[int, float] = {}
    for payment_year in REQUIRED_COLA_PAYMENT_YEARS:
        raw_percent = data.get(str(payment_year))
        if isinstance(raw_percent, bool) or not isinstance(
            raw_percent, (int, float)
        ):
            raise ValueError(
                f"COLA history lacks numeric payment year {payment_year}."
            )
        rate = float(raw_percent) / 100.0
        if not 0.0 <= rate < 1.0:
            raise ValueError(
                f"COLA payment-year rate for {payment_year} is invalid: "
                f"{rate!r}."
            )
        rates[payment_year] = rate
    if tuple(rates) != REQUIRED_COLA_PAYMENT_YEARS:
        raise ValueError(
            "Runtime COLA keys are not exactly payment years 1979-2022."
        )

    source_provenance: dict[str, Any] = {
        "path": str(path.resolve()),
        "sha256": raw_sha256,
        "content_sha256": content_sha256,
        "schema_version": "ssa_cola_history.v1",
        "source_unit": "percent",
        "runtime_unit": "fraction",
        "year_basis": "first_payment_year",
        "runtime_first_payment_year": 1979,
        "runtime_last_payment_year": 2022,
        "runtime_n_years": len(rates),
        "determination_year_conversion": (
            "payment year equals determination year through 1982; "
            "payment year equals determination year plus one from 1983"
        ),
    }
    return COLASeries(
        by_payment_year=rates,
        provenance=source_provenance,
    )


def load_report_parameters(
    pe_us_dir: Path | None = None,
    *,
    pe_us_version: str | None = None,
    cola_path: Path = COLA_HISTORY_PATH,
) -> ReportParameters:
    """Load the report's independent, full-actual statutory parameters.

    ``pe_us_version`` is an explicit injection seam for synthetic tests.
    Production calls leave it unset, so version and parameter-directory
    identity are both bound to the installed policyengine-us distribution.
    Raw file hashes remain mandatory in either mode.
    """

    root, resolved_version, version_source = _resolve_pinned_root(
        pe_us_dir,
        pe_us_version,
    )

    ssa_records, ssa_actual = _verify_files(
        root,
        SSA_PARAMETER_SHA256,
        expected_bundle_sha256=SSA_PARAMETER_BUNDLE_SHA256,
    )
    rate_records, rate_actual = _verify_files(
        root,
        RATE_LEG_SHA256,
        expected_bundle_sha256=RATE_LEG_BUNDLE_SHA256,
    )
    all_actual = {**ssa_actual, **rate_actual}
    all_bundle_sha256 = _canonical_mapping_sha256(all_actual)
    if all_bundle_sha256 != PE_US_CONSUMED_BUNDLE_SHA256:
        raise ValueError(
            f"All consumed policyengine-us files hash to "
            f"{all_bundle_sha256}, expected "
            f"{PE_US_CONSUMED_BUNDLE_SHA256}."
        )

    ssa = ss_params.load_ssa_parameters(root)
    if ssa.nawi.get(2020) != 55_628.60:
        raise ValueError(
            f"Full-actual NAWI(2020) is {ssa.nawi.get(2020)!r}, "
            "expected 55628.60."
        )
    if ssa.wage_base.get(2022) != 147_000.0:
        raise ValueError(
            f"Full-actual wage base entry for 2022 is "
            f"{ssa.wage_base.get(2022)!r}, expected 147000."
        )
    if ssa.wage_base_for(2022) != 147_000.0:
        raise ValueError(
            "Full-actual wage-base step function does not resolve 2022 "
            "to 147000."
        )

    rates = _load_rate_legs(
        root,
        rate_records,
        bundle_sha256=RATE_LEG_BUNDLE_SHA256,
    )
    cola = load_cola_history(cola_path)
    bundle_components = {
        "policyengine_us_consumed_files": all_bundle_sha256,
        "cola_file": cola.provenance["sha256"],
        "cola_content": cola.provenance["content_sha256"],
    }
    parameter_bundle_sha256 = _canonical_mapping_sha256(bundle_components)
    provenance: dict[str, Any] = {
        "schema_version": "first_estimates.parameters.v1",
        "bundle_sha256": parameter_bundle_sha256,
        "bundle_components": bundle_components,
        "bundle_hash_basis": (
            "sha256 of canonical JSON {component: sha256} "
            "(sorted keys, compact separators, trailing newline)"
        ),
        "policyengine_us": {
            "version": resolved_version,
            "version_source": version_source,
            "root": str(root),
            "ssa_parameter_directory": str((root / ss_params._SSA).resolve()),
            "git_revision": ssa.pe_us_revision,
            "ssa_parameter_files": ssa_records,
            "ssa_parameter_bundle_sha256": SSA_PARAMETER_BUNDLE_SHA256,
            "all_consumed_files_sha256": all_bundle_sha256,
            "bundle_hash_basis": (
                "sha256 of canonical JSON {relative_path: raw_sha256} "
                "(sorted keys, compact separators, trailing newline)"
            ),
            "actuals_asserted": {
                "nawi_2020": 55_628.60,
                "wage_base_2022": 147_000.0,
            },
        },
        "oasdi_rate_legs": rates.provenance,
        "cola": cola.provenance,
    }
    # Fail here, before compute, if a future edit introduces a Path, int-keyed
    # mapping, or another value the artifact writer cannot serialize.
    json.dumps(provenance, sort_keys=True, separators=(",", ":"))
    return ReportParameters(
        ssa=ssa,
        rates=rates,
        cola=cola,
        provenance=provenance,
    )
