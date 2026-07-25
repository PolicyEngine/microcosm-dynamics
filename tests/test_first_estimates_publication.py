"""Schema and one-shot tests for first-estimates publication records."""

from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path

import pytest

from populace_dynamics.estimates import publication, runner


def _configuration() -> dict:
    return runner.registered_configuration_echo(
        registration_reference="issue-42-comment-1234567",
        parameter_bundle={"bundle_sha256": "c" * 64},
    )


def _runtime_provenance() -> dict:
    return {
        "schema_version": "first_estimates.runtime_provenance.v1",
        "parameters": {},
    }


def _sidecar() -> bytes:
    return publication.canonical_json_bytes(
        {
            "contract": {
                "blob_sha": "a" * 40,
                "head_sha": "b" * 40,
                "path": "gates.yaml",
            },
            "environment": {
                "python": "3.14.0",
                "numpy": "2.0.0",
                "pandas": "3.0.0",
                "sklearn": "1.9.0",
                "scipy": "1.18.0",
                "platform": "fixture-platform",
                "fitting_stack": {
                    "populace_fit": "absent",
                    "populace_frame": "absent",
                },
            },
        }
    )


def _summary(values: list[float | int | None]) -> dict:
    observed = [float(value) for value in values if value is not None]
    if not observed:
        return {
            "n_draws": len(values),
            "n_observations": 0,
            "mean": None,
            "sample_sd": None,
        }
    mean = math.fsum(observed) / len(observed)
    sample_sd = None
    if len(observed) >= 2:
        sample_sd = math.sqrt(
            math.fsum((value - mean) ** 2 for value in observed)
            / (len(observed) - 1)
        )
    return {
        "n_draws": len(values),
        "n_observations": len(observed),
        "mean": mean,
        "sample_sd": sample_sd,
    }


def _aggregate(
    rows: list[dict],
    *,
    dimensions: tuple[str, ...],
    metrics: tuple[str, ...],
    row_basis: bool = False,
) -> list[dict]:
    grouped: dict[tuple, list[dict]] = {}
    displayed_dimensions: dict[tuple, dict] = {}
    for row in rows:
        key = tuple(
            tuple(row[name]) if isinstance(row[name], list) else row[name]
            for name in dimensions
        )
        grouped.setdefault(key, []).append(row)
        displayed_dimensions.setdefault(
            key,
            {name: copy.deepcopy(row[name]) for name in dimensions},
        )
    result = []
    for key in sorted(grouped):
        draw_rows = sorted(grouped[key], key=lambda row: row["draw_index"])
        for metric in metrics:
            result.append(
                {
                    **({"row_basis": "across_draw"} if row_basis else {}),
                    **displayed_dimensions[key],
                    "metric": metric,
                    **_summary([row[metric] for row in draw_rows]),
                }
            )
    return result


def _benefit_table(origin: str) -> dict:
    metrics = (
        "unweighted_award_count",
        "weighted_award_count",
        "average_monthly_benefit_at_award",
        "unweighted_beneficiary_count",
        "weighted_beneficiary_count",
        "frame_annualized_benefit",
    )
    per_draw = []
    for draw_index in range(20):
        for year in range(2015, 2023):
            awarded = origin == "modeled_award" and year == 2015
            beneficiary = year <= 2016
            per_draw.append(
                {
                    "draw_index": draw_index,
                    "claim_origin": origin,
                    "year": year,
                    "unweighted_award_count": int(awarded),
                    "weighted_award_count": float(awarded),
                    "average_monthly_benefit_at_award": (
                        100.0 + draw_index if awarded else None
                    ),
                    "unweighted_beneficiary_count": int(beneficiary),
                    "weighted_beneficiary_count": float(beneficiary),
                    "frame_annualized_benefit": (
                        1_200.0 + draw_index if beneficiary else 0.0
                    ),
                }
            )
    per_draw_biennial = []
    for draw_index in range(20):
        for end_year in (2016, 2018, 2020, 2022):
            awarded = origin == "modeled_award" and end_year == 2016
            beneficiary = end_year == 2016
            per_draw_biennial.append(
                {
                    "row_basis": "per_draw",
                    "draw_index": draw_index,
                    "claim_origin": origin,
                    "end_year": end_year,
                    "component_years": [end_year - 1, end_year],
                    "unweighted_award_count": int(awarded),
                    "weighted_award_count": float(awarded),
                    "average_monthly_benefit_at_award": (
                        100.0 + draw_index if awarded else None
                    ),
                    "unweighted_beneficiary_count": 2 * int(beneficiary),
                    "weighted_beneficiary_count": 2.0 * beneficiary,
                    "frame_annualized_benefit": (
                        2_400.0 + draw_index if beneficiary else 0.0
                    ),
                    "odd_year_carry_disclosure": (
                        publication.ODD_YEAR_CARRY_DISCLOSURE
                    ),
                }
            )
    unit_label = (
        "annualized statutory benefit, eligibility-PIA with COLA, "
        "no recomputation"
    )
    if origin == "opening_backfill":
        unit_label = f"report-only imputed opening stock; {unit_label}"
    return publication.table_record(
        per_draw=per_draw,
        aggregate=_aggregate(
            per_draw,
            dimensions=("claim_origin", "year"),
            metrics=metrics,
        ),
        unit_label=unit_label,
        annual=True,
        biennial_companion=[
            *per_draw_biennial,
            *_aggregate(
                per_draw_biennial,
                dimensions=("claim_origin", "end_year", "component_years"),
                metrics=metrics,
                row_basis=True,
            ),
        ],
    )


def _revenue_table() -> dict:
    metrics = (
        "unweighted_person_year_count",
        "weighted_person_year_count",
        "unweighted_covered_earner_count",
        "weighted_covered_earner_count",
        "weighted_taxable_payroll",
        "employee_contributions",
        "employer_contributions",
        "combined_contributions",
    )
    per_draw = []
    for draw_index in range(20):
        for year in range(2015, 2023):
            per_draw.append(
                {
                    "draw_index": draw_index,
                    "year": year,
                    "unweighted_person_year_count": 1,
                    "weighted_person_year_count": 1.0,
                    "unweighted_covered_earner_count": 1,
                    "weighted_covered_earner_count": 1.0,
                    "weighted_taxable_payroll": 10_000.0 + draw_index,
                    "employee_contributions": 620.0 + draw_index,
                    "employer_contributions": 620.0 + draw_index,
                    "combined_contributions": 1_240.0 + draw_index,
                    "odd_year_carry_affected": year % 2 == 1,
                }
            )
    per_draw_biennial = []
    for draw_index in range(20):
        for end_year in (2016, 2018, 2020, 2022):
            odd_year = end_year - 1
            per_draw_biennial.append(
                {
                    "row_basis": "per_draw",
                    "draw_index": draw_index,
                    "end_year": end_year,
                    "component_years": [odd_year, end_year],
                    "unweighted_person_year_count": 2,
                    "weighted_person_year_count": 2.0,
                    "unweighted_covered_earner_count": 2,
                    "weighted_covered_earner_count": 2.0,
                    "weighted_taxable_payroll": 20_000.0 + draw_index,
                    "employee_contributions": 1_240.0 + draw_index,
                    "employer_contributions": 1_240.0 + draw_index,
                    "combined_contributions": 2_480.0 + draw_index,
                    "odd_year_carry_pair_interpretation": (
                        f"{odd_year} carries {odd_year - 1} earnings; "
                        f"{end_year} is the newly drawn even year."
                    ),
                    "odd_year_carry_disclosure": (
                        publication.ODD_YEAR_CARRY_DISCLOSURE
                    ),
                }
            )
    return publication.table_record(
        per_draw=per_draw,
        aggregate=_aggregate(
            per_draw,
            dimensions=("year",),
            metrics=metrics,
        ),
        unit_label=(
            "nominal frame-relative OASDI payroll contributions on "
            "the labor-income proxy"
        ),
        annual=True,
        biennial_companion=[
            *per_draw_biennial,
            *_aggregate(
                per_draw_biennial,
                dimensions=("end_year", "component_years"),
                metrics=metrics,
                row_basis=True,
            ),
        ],
    )


def _wide_aggregate(rows: list[dict]) -> list[dict]:
    return [
        {
            "metric": metric,
            **_summary([row[metric] for row in rows]),
        }
        for metric in sorted(set(rows[0]) - {"draw_index"})
    ]


def _artifact(sidecar: bytes | None = None) -> dict:
    payload = sidecar if sidecar is not None else _sidecar()
    count_rows = []
    one_count_metrics = {
        "inclusion__included__unweighted",
        "inclusion__included__weighted",
        "inclusion__origin_modeled_award__unweighted",
        "inclusion__origin_modeled_award__weighted",
        "birth_source__exact_marriage__unweighted",
        "birth_source__exact_marriage__weighted",
        "included_origin__modeled_award__unweighted",
        "included_origin__modeled_award__weighted",
    }
    for draw_index in range(20):
        count_rows.append(
            {
                "draw_index": draw_index,
                **{
                    metric: (
                        (1 if metric.endswith("__unweighted") else 1.0)
                        if metric in one_count_metrics
                        else (0 if metric.endswith("__unweighted") else 0.0)
                    )
                    for metric in publication._COUNT_METRICS
                },
            }
        )
    diagnostic_rows = [
        {"draw_index": draw_index, "fixture_metric": float(draw_index)}
        for draw_index in range(20)
    ]
    zero_provenance = {
        "observed": 0,
        "gap_imputed": 0,
        "boundary_2014": 0,
        "projected": 0,
        "unknown": 0,
    }
    return {
        "schema_version": publication.ARTIFACT_SCHEMA_VERSION,
        "identity": {
            "report_id": "first_estimates",
            "report_class": "registered estimates report",
            "registration_reference": "issue-42-comment-1234567",
        },
        "configuration_echo": _configuration(),
        "integrity": {
            "environment_sidecar": {
                "path": "first_estimates_v1.json.env.json",
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        },
        "parameters": {"bundle_sha256": "c" * 64},
        "runtime_provenance": _runtime_provenance(),
        "execution": {
            "canonical_rule": publication.CANONICAL_EXECUTION_RULE,
            "completed_draw_indices": list(range(20)),
            "assembly": "pure_post_compute",
        },
        "tables": {
            "modeled_award_flow": _benefit_table("modeled_award"),
            "opening_stock": _benefit_table("opening_backfill"),
            "revenue": _revenue_table(),
        },
        "counts": {
            "per_draw": count_rows,
            "aggregate": _wide_aggregate(count_rows),
            "entrant_diagnostic": {
                "source_income_years": [2016, 2018],
                "may_overlap_inclusion_classes": True,
                "operative_exclusion_rule": False,
            },
        },
        "diagnostics": {
            "per_draw": diagnostic_rows,
            "aggregate": _wide_aggregate(diagnostic_rows),
            "included_career_per_draw": [
                {
                    "draw_index": draw_index,
                    "person_id": f"person-{draw_index}",
                    "claim_origin": "modeled_award",
                    "birth_source": "exact_marriage",
                    "birth_year_inferred": False,
                    "coverage_ratio": 1.0,
                    "imputed_year_share": 0.0,
                    "affected_odd_year_share": 0.0,
                    "provenance_counts": zero_provenance,
                    "coverage_provenance_counts": zero_provenance,
                    "top35_reaches_pre_1968": False,
                    "pre_1968_top35_zero_year_count": 0,
                    "positive_post_claim_earnings": False,
                    "award_formula_computation_count": 1,
                    "post_claim_recomputation_count": 0,
                }
                for draw_index in range(20)
            ],
            "context_ratio": {
                "status": "deferred_to_anchor_extraction",
            },
            "payment_year_convention": (
                "Twelve annualized monthly payments only in realized "
                "presence years; partial first and last years are not "
                "modeled."
            ),
            "benefit_measure": (
                "annualized statutory benefit, eligibility-PIA with COLA, "
                "no recomputation"
            ),
            "revenue_population_basis": "unsplit projection.slices",
        },
        "prior_incidents": [],
        "gap_block": list(publication.GAP_BLOCK),
        "certifies_nothing": list(publication.CERTIFIES_NOTHING),
    }


def test__artifact_writer__binds_and_writes_exact_sidecar_once(tmp_path):
    sidecar = _sidecar()
    artifact = _artifact(sidecar)
    root = tmp_path / "repo"
    (root / "runs").mkdir(parents=True)
    destination = root / publication.DEFAULT_ARTIFACT_PATH
    registration = publication._RegisteredConfigurationToken(
        _repository_root=root.resolve(),
        _registration_reference="issue-42-comment-1234567",
        _configuration_bytes=publication.canonical_json_bytes(
            _configuration()
        ),
    )
    token = publication._PrecomputeToken(
        _registration=registration,
        _runtime_provenance_bytes=publication.canonical_json_bytes(
            _runtime_provenance()
        ),
        _sidecar_payload=sidecar,
        _sidecar_sha256=hashlib.sha256(sidecar).hexdigest(),
        _prior_incidents=(),
    )
    assert publication.write_first_estimates_artifact(token, artifact) == (
        destination
    )

    loaded = json.loads(destination.read_text())
    assert loaded == artifact
    publication.validate_first_estimates_artifact(
        loaded,
        expected_configuration_echo=_configuration(),
        expected_runtime_provenance=_runtime_provenance(),
    )
    assert Path(f"{destination}.env.json").read_bytes() == sidecar
    assert not (root / "first_estimates_v1.json").exists()
    with pytest.raises(FileExistsError, match="one-shot rule"):
        publication._write_first_estimates_artifact_for_test(
            repository_root=root,
            artifact=artifact,
            expected_configuration_echo=_configuration(),
            expected_runtime_provenance=_runtime_provenance(),
            sidecar_payload=sidecar,
        )


def test__artifact_writer__rejects_empty_sidecar_schema(tmp_path):
    root = tmp_path / "repo"
    (root / "runs").mkdir(parents=True)
    sidecar = publication.canonical_json_bytes({})
    with pytest.raises(ValueError, match="environment sidecar keys"):
        publication._write_first_estimates_artifact_for_test(
            repository_root=root,
            artifact=_artifact(sidecar),
            expected_configuration_echo=_configuration(),
            sidecar_payload=sidecar,
        )


def test__artifact_validator__pins_complete_prior_incident_history():
    artifact = _artifact()
    artifact["prior_incidents"] = [
        "runs/first_estimates_incident_1.json",
    ]
    publication.validate_first_estimates_artifact(
        artifact,
        expected_configuration_echo=_configuration(),
        expected_prior_incidents=artifact["prior_incidents"],
    )

    artifact["prior_incidents"] = [
        "runs/first_estimates_incident_2.json",
    ]
    with pytest.raises(ValueError, match="complete ordered history"):
        publication.validate_first_estimates_artifact(
            artifact,
            expected_configuration_echo=_configuration(),
            expected_prior_incidents=artifact["prior_incidents"],
        )


def test__artifact_validator__rejects_gap_or_label_drift():
    artifact = _artifact()
    artifact["gap_block"] = artifact["gap_block"][:-1]
    with pytest.raises(ValueError, match="gap block"):
        publication.validate_first_estimates_artifact(
            artifact,
            expected_configuration_echo=_configuration(),
        )

    artifact = _artifact()
    artifact["tables"]["modeled_award_flow"]["labels"] = ["frame-relative"]
    with pytest.raises(ValueError, match="evidence labels"):
        publication.validate_first_estimates_artifact(
            artifact,
            expected_configuration_echo=_configuration(),
        )


def test__artifact_validator__requires_exact_publication_shapes():
    artifact = _artifact()
    artifact["tables"].pop("revenue")
    with pytest.raises(ValueError, match="artifact tables keys"):
        publication.validate_first_estimates_artifact(
            artifact,
            expected_configuration_echo=_configuration(),
        )

    artifact = _artifact()
    artifact["counts"]["unexpected"] = {}
    with pytest.raises(ValueError, match="artifact counts keys"):
        publication.validate_first_estimates_artifact(
            artifact,
            expected_configuration_echo=_configuration(),
        )

    artifact = _artifact()
    artifact["diagnostics"].pop("context_ratio")
    with pytest.raises(ValueError, match="artifact diagnostics keys"):
        publication.validate_first_estimates_artifact(
            artifact,
            expected_configuration_echo=_configuration(),
        )


def test__artifact_validator__requires_exact_draw_grids():
    artifact = _artifact()
    artifact["tables"]["modeled_award_flow"]["per_draw"].pop()
    with pytest.raises(ValueError, match="exact annual draw grid"):
        publication.validate_first_estimates_artifact(
            artifact,
            expected_configuration_echo=_configuration(),
        )

    artifact = _artifact()
    artifact["counts"]["per_draw"][-1]["draw_index"] = 18
    with pytest.raises(ValueError, match="duplicate draw rows"):
        publication.validate_first_estimates_artifact(
            artifact,
            expected_configuration_echo=_configuration(),
        )

    artifact = _artifact()
    artifact["diagnostics"]["per_draw"][-1]["draw_index"] = 18
    with pytest.raises(ValueError, match="duplicate draw rows"):
        publication.validate_first_estimates_artifact(
            artifact,
            expected_configuration_echo=_configuration(),
        )

    artifact = _artifact()
    companion = artifact["tables"]["opening_stock"]["biennial_companion"]
    companion.pop(0)
    with pytest.raises(ValueError, match="exact biennial draw grid"):
        publication.validate_first_estimates_artifact(
            artifact,
            expected_configuration_echo=_configuration(),
        )


def test__artifact_validator__rejects_duplicate_table_grids():
    artifact = _artifact()
    per_draw = artifact["tables"]["revenue"]["per_draw"]
    per_draw.append(copy.deepcopy(per_draw[0]))
    with pytest.raises(ValueError, match="duplicate annual grids"):
        publication.validate_first_estimates_artifact(
            artifact,
            expected_configuration_echo=_configuration(),
        )

    artifact = _artifact()
    aggregate = artifact["tables"]["modeled_award_flow"]["aggregate"]
    aggregate.append(copy.deepcopy(aggregate[0]))
    with pytest.raises(ValueError, match="duplicate aggregate grids"):
        publication.validate_first_estimates_artifact(
            artifact,
            expected_configuration_echo=_configuration(),
        )

    artifact = _artifact()
    companion = artifact["tables"]["opening_stock"]["biennial_companion"]
    companion.insert(0, copy.deepcopy(companion[0]))
    with pytest.raises(ValueError, match="duplicate biennial grids"):
        publication.validate_first_estimates_artifact(
            artifact,
            expected_configuration_echo=_configuration(),
        )


def test__artifact_validator__recomputes_every_across_draw_summary():
    artifact = _artifact()
    aggregate = artifact["tables"]["modeled_award_flow"]["aggregate"][0]
    aggregate["n_draws"] = 19
    with pytest.raises(ValueError, match="n_draws"):
        publication.validate_first_estimates_artifact(
            artifact,
            expected_configuration_echo=_configuration(),
        )

    artifact = _artifact()
    null_mean = next(
        row
        for row in artifact["tables"]["opening_stock"]["aggregate"]
        if row["metric"] == "average_monthly_benefit_at_award"
    )
    assert null_mean["n_observations"] == 0
    assert null_mean["mean"] is None
    assert null_mean["sample_sd"] is None
    null_mean["mean"] = 0.0
    with pytest.raises(ValueError, match="mean does not match"):
        publication.validate_first_estimates_artifact(
            artifact,
            expected_configuration_echo=_configuration(),
        )

    artifact = _artifact()
    count_summary = artifact["counts"]["aggregate"][0]
    count_summary["n_observations"] = 19
    with pytest.raises(ValueError, match="n_observations"):
        publication.validate_first_estimates_artifact(
            artifact,
            expected_configuration_echo=_configuration(),
        )

    artifact = _artifact()
    diagnostic_summary = artifact["diagnostics"]["aggregate"][0]
    diagnostic_summary["sample_sd"] += 1.0
    with pytest.raises(ValueError, match="sample_sd"):
        publication.validate_first_estimates_artifact(
            artifact,
            expected_configuration_echo=_configuration(),
        )

    artifact = _artifact()
    biennial_summary = next(
        row
        for row in artifact["tables"]["revenue"]["biennial_companion"]
        if row["row_basis"] == "across_draw"
    )
    biennial_summary["mean"] += 1.0
    with pytest.raises(ValueError, match="mean does not match"):
        publication.validate_first_estimates_artifact(
            artifact,
            expected_configuration_echo=_configuration(),
        )


def test__artifact_validator__freezes_year_origin_and_disclosures():
    artifact = _artifact()
    artifact["tables"]["modeled_award_flow"]["per_draw"][0][
        "claim_origin"
    ] = "opening_backfill"
    with pytest.raises(ValueError, match="wrong claim origin"):
        publication.validate_first_estimates_artifact(
            artifact,
            expected_configuration_echo=_configuration(),
        )

    artifact = _artifact()
    artifact["tables"]["revenue"]["per_draw"][0]["year"] = 2014
    with pytest.raises(ValueError, match="out-of-window year"):
        publication.validate_first_estimates_artifact(
            artifact,
            expected_configuration_echo=_configuration(),
        )

    artifact = _artifact()
    artifact["counts"]["entrant_diagnostic"]["operative_exclusion_rule"] = True
    with pytest.raises(ValueError, match="entrant diagnostic"):
        publication.validate_first_estimates_artifact(
            artifact,
            expected_configuration_echo=_configuration(),
        )

    artifact = _artifact()
    artifact["diagnostics"]["context_ratio"]["status"] = "computed"
    with pytest.raises(ValueError, match="deferred_to_anchor_extraction"):
        publication.validate_first_estimates_artifact(
            artifact,
            expected_configuration_echo=_configuration(),
        )

    artifact = _artifact()
    artifact["counts"]["per_draw"][0][
        "opening_stock_snap__lower_endpoint__weighted_share"
    ] = 0.5
    artifact["counts"]["aggregate"] = _wide_aggregate(
        artifact["counts"]["per_draw"]
    )
    with pytest.raises(ValueError, match="lower_endpoint weighted share"):
        publication.validate_first_estimates_artifact(
            artifact,
            expected_configuration_echo=_configuration(),
        )


def test__artifact_validator__binds_career_rows_to_included_counts():
    artifact = _artifact()
    artifact["diagnostics"]["included_career_per_draw"].pop()
    with pytest.raises(ValueError, match="included claimant counts"):
        publication.validate_first_estimates_artifact(
            artifact,
            expected_configuration_echo=_configuration(),
        )

    artifact = _artifact()
    for row in artifact["counts"]["per_draw"]:
        for metric in set(row) - {"draw_index"}:
            row[metric] = 0
    for row in artifact["counts"]["aggregate"]:
        row.update(
            n_draws=20,
            n_observations=20,
            mean=0.0,
            sample_sd=0.0,
        )
    artifact["diagnostics"]["included_career_per_draw"] = []
    publication.validate_first_estimates_artifact(
        artifact,
        expected_configuration_echo=_configuration(),
    )


def test__artifact_validator__freezes_identity_and_sidecar_path():
    artifact = _artifact()
    artifact["identity"]["report_id"] = "other"
    with pytest.raises(ValueError, match="report_id"):
        publication.validate_first_estimates_artifact(
            artifact,
            expected_configuration_echo=_configuration(),
        )

    artifact = _artifact()
    artifact["integrity"]["environment_sidecar"]["path"] = "other.env.json"
    with pytest.raises(ValueError, match="sidecar path"):
        publication.validate_first_estimates_artifact(
            artifact,
            expected_configuration_echo=_configuration(),
        )

    artifact = _artifact()
    artifact["runtime_provenance"]["parameters"] = {
        "policyengine_us": {"root": "/later/site-packages"}
    }
    with pytest.raises(ValueError, match="pre-compute run-time identity"):
        publication.validate_first_estimates_artifact(
            artifact,
            expected_configuration_echo=_configuration(),
            expected_runtime_provenance=_runtime_provenance(),
        )


def test__incident_writer__uses_exact_schema_and_retry_class(tmp_path):
    root = tmp_path / "repo"
    (root / "runs").mkdir(parents=True)
    configuration = _configuration()

    path = publication._write_first_estimates_incident_for_test(
        repository_root=root,
        phase="preparation",
        reason="external_parameter_checkout_unavailable",
        reason_detail="pinned checkout was not mounted",
        registration_reference="issue-42-comment-1234567",
        configuration_echo=configuration,
        timestamp_utc="2026-07-24T12:34:56Z",
    )
    record = json.loads(path.read_text())

    assert set(record) == {
        "schema_version",
        "incident_index",
        "timestamp_utc",
        "phase",
        "reason",
        "reason_detail",
        "registration_reference",
        "configuration_echo",
        "artifact_path",
    }
    assert record["incident_index"] == 1
    assert record["artifact_path"] is None
    assert publication.incident_is_retry_eligible(record)
    publication.validate_first_estimates_incident(
        record,
        path=path,
        expected_configuration_echo=configuration,
        repository_root=root,
    )


def test__incident_validator__enforces_publication_partial_iff_rule(tmp_path):
    root = tmp_path / "repo"
    runs = root / "runs"
    runs.mkdir(parents=True)
    partial = runs / "first_estimates_v1.json"
    partial.write_text('{"partial": true}\n')
    configuration = _configuration()

    path = publication._write_first_estimates_incident_for_test(
        repository_root=root,
        phase="publication",
        reason="sidecar_hash_mismatch",
        reason_detail="the exact sidecar did not match its primary binding",
        registration_reference="issue-42-comment-1234567",
        configuration_echo=configuration,
        partial_artifact_path=partial,
        timestamp_utc="2026-07-24T12:34:56.123456Z",
    )
    record = json.loads(path.read_text())
    assert record["artifact_path"] == "runs/first_estimates_v1.json"
    assert not publication.incident_is_retry_eligible(record)

    record["phase"] = "compute"
    with pytest.raises(ValueError, match="artifact_path"):
        publication.validate_first_estimates_incident(
            record,
            path=path,
            expected_configuration_echo=configuration,
            repository_root=root,
        )


def test__incident_validator__requires_timestamp_and_registration_identity(
    tmp_path,
):
    root = tmp_path / "repo"
    (root / "runs").mkdir(parents=True)
    configuration = _configuration()
    path = root / "runs" / "first_estimates_incident_1.json"
    record = {
        "schema_version": publication.INCIDENT_SCHEMA_VERSION,
        "incident_index": 1,
        "timestamp_utc": "2026-07-24Z",
        "phase": "invariant",
        "reason": "schema_drift",
        "reason_detail": "fixture",
        "registration_reference": configuration["registration_reference"],
        "configuration_echo": configuration,
        "artifact_path": None,
    }

    with pytest.raises(ValueError, match="ISO-8601"):
        publication.validate_first_estimates_incident(
            record,
            path=path,
            expected_configuration_echo=configuration,
            repository_root=root,
        )

    record["timestamp_utc"] = "2026-07-24T12:34:56Z"
    record["registration_reference"] = "different-registration"
    with pytest.raises(ValueError, match="registration reference"):
        publication.validate_first_estimates_incident(
            record,
            path=path,
            expected_configuration_echo=configuration,
            repository_root=root,
        )


def test__incident_validator__requires_partial_path_when_v1_exists(tmp_path):
    root = tmp_path / "repo"
    runs = root / "runs"
    runs.mkdir(parents=True)
    (runs / "first_estimates_v1.json").write_text('{"partial": true}\n')
    configuration = _configuration()
    record = {
        "schema_version": publication.INCIDENT_SCHEMA_VERSION,
        "incident_index": 1,
        "timestamp_utc": "2026-07-24T12:34:56Z",
        "phase": "publication",
        "reason": "write_interrupted",
        "reason_detail": "fixture",
        "registration_reference": configuration["registration_reference"],
        "configuration_echo": configuration,
        "artifact_path": None,
    }

    with pytest.raises(ValueError, match="artifact_path"):
        publication.validate_first_estimates_incident(
            record,
            path=runs / "first_estimates_incident_1.json",
            expected_configuration_echo=configuration,
            repository_root=root,
        )
