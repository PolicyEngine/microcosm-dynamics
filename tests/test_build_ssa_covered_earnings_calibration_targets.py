"""Source reproduction and amended vintage-2 tests for entry 11."""

from __future__ import annotations

import copy
import hashlib
import shutil
import sys
from fractions import Fraction
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SNAPSHOTS = (
    ROOT / "data" / "external" / "snapshots" / "ssa_level_anchors_vintage1"
)
ARTIFACT = (
    ROOT
    / "data"
    / "external"
    / "ssa_covered_earnings_calibration_targets_vintage2.json"
)

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_ssa_covered_earnings_calibration_targets as builder  # noqa: E402


def _evidence() -> dict:
    return builder.extract_b2_b11_source_evidence()


def _partial_legacy_artifact() -> dict:
    """Construct the withdrawn round-1 shape solely for rejection attacks."""

    evidence = _evidence()
    artifact = {
        "schema_version": builder.SCHEMA_VERSION,
        "artifact_vintage_id": builder.ARTIFACT_VINTAGE_ID,
        "artifact_role": builder.ARTIFACT_ROLE,
        "year_basis": builder.YEAR_BASIS,
        "required_calendar_years": list(builder.REQUIRED_CALENDAR_YEARS),
        "required_source_cell_ids": {
            **evidence["required_source_cell_ids"],
            "ssa_covered_share": [],
        },
        "covered_share_required_years": [],
        "source_document_manifest": evidence["source_document_manifest"],
        "observations": evidence["observations"],
        "cross_table_discrepancies": evidence["cross_table_discrepancies"],
        "integrity": {
            "canonicalization": builder.CANONICALIZATION,
            "content_sha256": "0" * 64,
            "extraction_implementation_commit": (
                builder.EXTRACTION_IMPLEMENTATION_COMMIT
            ),
            "reproduced_from_source_bytes": True,
        },
    }
    artifact["integrity"]["content_sha256"] = builder._content_sha256(artifact)
    return artifact


def _observations_by_id(evidence: dict) -> dict[str, dict]:
    return {
        observation["source_cell_id"]: observation
        for observation in evidence["observations"]
    }


def _extract_after_source_mutation(old: bytes, new: bytes):
    source = SNAPSHOTS / builder.SOURCE_FILENAME
    raw = source.read_bytes()
    assert raw.count(old) == 1
    mutated = raw.replace(old, new, 1)
    return builder._extract_observations(builder._select_tables(mutated))


def test__vintage2_authority__builds_with_exact_amended_shape():
    artifact = builder.build()
    assert set(artifact) == {
        "artifact_role",
        "artifact_vintage_id",
        "cross_table_discrepancies",
        "integrity",
        "observations",
        "optional_covered_share",
        "required_calendar_years",
        "required_source_cell_ids",
        "schema_version",
        "source_document_manifest",
        "year_basis",
    }
    assert artifact["schema_version"] == (
        "ssa_covered_earnings_calibration_targets.v2"
    )
    assert set(artifact["required_source_cell_ids"]) == {
        "table4_b2",
        "table4_b11",
    }
    assert artifact["optional_covered_share"] == (
        builder.OPTIONAL_COVERED_SHARE_UNAVAILABLE
    )
    builder.validate_artifact(artifact)
    assert builder.render() == builder.entry10.canonical_json_bytes(artifact)


def test__b2_b11_evidence__is_complete_and_ordered():
    evidence = _evidence()
    assert set(evidence) == {
        "cross_table_discrepancies",
        "observations",
        "required_calendar_years",
        "required_source_cell_ids",
        "source_document_manifest",
    }
    required = evidence["required_source_cell_ids"]
    b2_components = ("c5", "c8", "c11", "c12", "c13", "c17")
    b11_components = (
        "workers_total",
        "workers_wage",
        "workers_self_employment",
        "taxable_earnings_total",
        "taxable_earnings_wage",
        "taxable_earnings_self_employment",
        "contributions_total",
        "contributions_wage",
        "contributions_self_employment",
    )
    assert required["table4_b2"] == [
        f"table4.b2/{year}/{component}"
        for year in range(1968, 2023)
        for component in b2_components
    ]
    assert required["table4_b11"] == [
        f"table4.b11/{year}/{component}"
        for year in range(1968, 2023)
        for component in b11_components
    ]
    assert [
        row["source_cell_id"] for row in evidence["observations"]
    ] == required["table4_b2"] + required["table4_b11"]
    assert len(evidence["observations"]) == 825


def test__b2_b11_evidence__pins_boundary_source_rows():
    rows = _observations_by_id(_evidence())
    expected = {
        "table4.b2/1968/c5": "413,600",
        "table4.b2/1968/c8": "46,400",
        "table4.b2/1968/c11": "84,470",
        "table4.b2/1968/c12": "6,570",
        "table4.b2/2014/c5": "6,873,446",
        "table4.b2/2014/c8": "558,400",
        "table4.b11/1968/workers_total": "89,380",
        "table4.b11/1968/taxable_earnings_total": "375,800",
        "table4.b11/1968/contributions_total": "28,069",
        "table4.b11/2014/workers_total": "165,429",
        "table4.b11/2014/taxable_earnings_total": "6,178,700",
        "table4.b11/2014/contributions_total": "766,159",
    }
    assert {
        source_cell_id: rows[source_cell_id]["as_published"]
        for source_cell_id in expected
    } == expected


def test__b2_b11_evidence__pins_units_status_manifest_and_discrepancies():
    evidence = _evidence()
    assert evidence["source_document_manifest"] == [
        {
            "source_document_id": "ssa_supplement_2025_4b",
            "publication": "Annual Statistical Supplement, 2025",
            "edition": "2025",
            "table_ids": ["table4.b2", "table4.b11"],
            "url": (
                "https://www.ssa.gov/policy/docs/statcomps/supplement/"
                "2025/4b.html"
            ),
            "retrieved_at_utc": "2026-07-27T13:02:54Z",
            "committed_path": (
                "data/external/snapshots/ssa_level_anchors_vintage1/"
                "supplement2025_4b.html"
            ),
            "sha256": builder.SOURCE_SHA256,
            "size_bytes": 488_165,
            "capture_manifest_path": (
                "data/external/snapshots/ssa_level_anchors_vintage1/"
                "capture_manifest.txt"
            ),
            "capture_manifest_entry": (
                "2026-07-27T13:02:54Z "
                f"{builder.SOURCE_SHA256} 488165 supplement2025_4b.html"
            ),
        }
    ]
    for observation in evidence["observations"]:
        year = observation["calendar_year"]
        assert observation["status"] == (
            "preliminary" if year in {2021, 2022} else "historical"
        )
        assert observation["published_rounding_interval"] == (
            builder.ROUNDING_NOT_ESTABLISHED
        )
    assert [
        (
            row["calendar_year"],
            row["concept"],
            row["table4_b2_as_published"],
            row["table4_b11_as_published"],
            row["discrepancy_class"],
        )
        for row in evidence["cross_table_discrepancies"]
    ] == list(builder.EXPECTED_CROSS_TABLE_DISCREPANCIES)


def test__vb7_adjudication__rejects_every_committed_construction():
    adjudication = builder.vb7_adjudication()
    assert adjudication["covered_share_required_years"] == []
    assert adjudication["registration_disposition"] == (
        "abort_no_authoritative_vintage2_or_calibration_target_specs"
    )
    candidates = {
        row["candidate_id"]: row
        for row in adjudication["candidate_constructions"]
    }
    assert set(candidates) == {
        "table4_b1_reported_taxable_earnings_share",
        (
            "supplement_workers_with_taxable_earnings_over_"
            "trustees_covered_workers"
        ),
        "trustees_vi_g1_taxable_payroll_to_gdp",
        "trustees_iv_b4_covered_workers_per_oasdi_beneficiary",
        ("trustees_iv_b4_oasdi_beneficiaries_per_100_" "covered_workers"),
        (
            "supplement_2023_table4_b10_oasdi_workers_over_"
            "table4_b12_hi_workers"
        ),
        "other_committed_same_universe_construction",
    }
    assert adjudication["candidate_constructions"][-1]["candidate_id"] == (
        "other_committed_same_universe_construction"
    )
    earnings = candidates["table4_b1_reported_taxable_earnings_share"]
    assert earnings["published_percentage_examples"] == {
        "1968": "81.7",
        "2014": "83.1",
    }
    assert earnings["verdict"] == "reject_earnings_share_is_not_worker_share"

    workers = candidates[
        "supplement_workers_with_taxable_earnings_over_"
        "trustees_covered_workers"
    ]
    assert workers["displayed_ratio_comparison_counts"] == {
        "above_one": 31,
        "below_one": 24,
        "equal_one": 0,
    }
    assert workers["example_1978"] == {
        "numerator_thousands": "110,600",
        "denominator_thousands": "109,432",
    }
    assert workers["verdict"].startswith("reject_not_a_source_defined")
    assert (
        "one_as_published_covered_share_observation_per_year"
        in workers["not_established"]
    )


def test__vb7_adjudication__rejects_vi_g1_payroll_to_gdp():
    candidates = {
        row["candidate_id"]: row
        for row in builder.vb7_adjudication()["candidate_constructions"]
    }
    candidate = candidates["trustees_vi_g1_taxable_payroll_to_gdp"]
    assert candidate["available_years"] == list(range(1970, 2023))
    assert candidate["source_document_sha256"] == (
        "3b9e96be991d5a102d41ede443e157d2d1a2a928174430497dc9c3a1fa532dc0"
    )
    assert candidate["published_ratio_examples"] == {
        "1970": "0.376",
        "2014": ".350",
        "2022": ".351",
    }
    assert candidate["source_definition_fragment_sha256"] == (
        "3ca4fa14471b8fe43c539f527ba11727dcc72aeac6bcd944977508309bfc9b38"
    )
    assert candidate["ratio_header_fragment_sha256"] == (
        "1ddc1e23278571f12b430c83283d32f5a78533a2568036f7ee8b9ebf1711f54f"
    )
    assert candidate["not_established"] == [
        "worker_incidence_numerator_denominator",
        "person_or_worker_denominator",
        "worker_duplicate_rule",
        "one_as_published_covered_share_observation_per_year",
        "exact_worker_universe_model_analogue",
        "1968_1969_source_cells",
    ]
    assert candidate["verdict"] == (
        "reject_payroll_to_gdp_dollar_ratio_is_not_worker_incidence_share"
    )


def test__vb7_adjudication__rejects_both_iv_b4_beneficiary_ratios():
    candidates = {
        row["candidate_id"]: row
        for row in builder.vb7_adjudication()["candidate_constructions"]
    }
    expected = {
        "trustees_iv_b4_covered_workers_per_oasdi_beneficiary": {
            "examples": {
                "1968": "3.8",
                "1978": "3.2",
                "2014": "2.8",
                "2022": "2.8",
            },
            "header_sha256": (
                "5aecf2b5d2c9a65e67e354e114d08c336c348c667f0a54d30516d2d4a6f9317c"
            ),
        },
        ("trustees_iv_b4_oasdi_beneficiaries_per_100_covered_workers"): {
            "examples": {
                "1968": "26",
                "1978": "31",
                "2014": "35",
                "2022": "36",
            },
            "header_sha256": (
                "1b33b9c5de900b8102d5026b05135260e183a1d86fc106d16c538ac4c427c84a"
            ),
        },
    }
    failures = [
        "worker_incidence_numerator_denominator",
        "population_universe_denominator",
        "common_annual_timing_numerator_denominator",
        "worker_duplicate_rule",
        "one_as_published_covered_share_observation_per_year",
        "exact_worker_universe_model_analogue",
    ]
    for candidate_id, values in expected.items():
        candidate = candidates[candidate_id]
        assert candidate["available_years"] == list(range(1968, 2023))
        assert candidate["published_ratio_examples"] == values["examples"]
        assert candidate["source_definition_fragment_sha256"] == (
            "130d02a0fb0158a972b5ead853e338a6b1e58d5bdd7d032f40b187a5deeaca49"
        )
        assert (
            candidate["ratio_header_fragment_sha256"]
            == values["header_sha256"]
        )
        assert candidate["not_established"] == failures
        assert candidate["verdict"] == (
            "reject_beneficiary_burden_ratio_is_not_worker_incidence_share"
        )


def test__vb7_adjudication__rejects_2023_b10_b12_worker_quotient():
    candidates = {
        row["candidate_id"]: row
        for row in builder.vb7_adjudication()["candidate_constructions"]
    }
    candidate = candidates[
        "supplement_2023_table4_b10_oasdi_workers_over_"
        "table4_b12_hi_workers"
    ]
    assert candidate["available_years"] == [2023]
    assert candidate["example_2023"] == {
        "numerator_thousands": "182,689",
        "denominator_thousands": "186,620",
        "exact_fraction": "182689/186620",
        "decimal_10_places": "0.9789358054",
    }
    assert candidate["numerator_fragment_sha256"] == (
        "aeb3f0f7a8cea093ea854a93499996c46a188d326f0986ca1e665644e703fff7"
    )
    assert candidate["denominator_fragment_sha256"] == (
        "5e62802d7d9345c0ec9fe3e28e25410dc1344ac3e0611f6350e6578bc22bf9bf"
    )
    assert candidate["operand_fragment_composite_sha256"] == (
        "b1802803df0069051016ecd046f8954af6325232f17e3f79fed4bfa8cb175293"
    )
    assert candidate["cwhs_source_fragment_sha256"] == (
        "a02bb45f130c696aef43924a63ac9c1ede08206d2bef7e8bc24f72d28fff0a4b"
    )
    assert candidate["unduplicated_worker_rule_fragment_sha256"] == (
        "d92c41987b78b20db440870cc57b34e474b96e7d72cd4dcc2c63db1a203a546d"
    )
    assert candidate["preliminary_status_fragment_sha256"] == (
        "f05a3933f67a7701befd7bd5e834c87db3bf8c610a554556435b3f1c23e2ed1d"
    )
    assert candidate["not_established"] == [
        "one_as_published_covered_share_observation_per_year",
        "non_preliminary_status",
        "any_1968_2022_registered_role_year",
        "hi_worker_denominator_model_analogue",
    ]
    assert candidate["verdict"] == (
        "reject_synthesized_preliminary_2023_only_quotient_"
        "without_hi_model_denominator"
    )


def test__membership_adjudication__fails_required_fitting_families():
    relationships = {
        row["family"]: row
        for row in builder.vb7_adjudication()[
            "worker_membership_relationships"
        ]
    }
    assert set(relationships) == {
        "b2_wage_total_intensity",
        "b2_se_total_intensity",
        "b11_worker_distribution",
    }
    assert {row["verdict"] for row in relationships.values()} == {
        "fail_closed"
    }
    assert (
        "zero_and_loss_only_membership"
        in relationships["b2_se_total_intensity"]["not_established"]
    )


def test__partial_round1_shape__is_never_accepted_as_vintage2():
    with pytest.raises(ValueError, match="top-level fields"):
        builder.validate_artifact(_partial_legacy_artifact())


def test__validator__reresolves_coherently_rehashed_cell_from_source_bytes():
    artifact = builder.build()
    row = next(
        row
        for row in artifact["observations"]
        if row["source_cell_id"] == "table4.b2/1973/c5"
    )
    row["as_published"] = "999"
    row["normalized_value"] = 999_000_000
    artifact["integrity"]["content_sha256"] = builder._content_sha256(artifact)
    with pytest.raises(ValueError, match="re-resolve from source bytes"):
        builder.validate_artifact(artifact)


def test__extractor__rejects_source_drift_before_parsing(
    tmp_path, monkeypatch
):
    copied = tmp_path / "ssa_level_anchors_vintage1"
    shutil.copytree(SNAPSHOTS, copied)
    source = copied / "supplement2025_4b.html"
    changed = bytearray(source.read_bytes())
    changed[-1] ^= 1
    source.write_bytes(changed)
    monkeypatch.setattr(builder.entry10, "SNAPSHOT_DIR", copied)

    def parse_must_not_run(*_args, **_kwargs):
        raise AssertionError("HTML parsing ran before source hashes passed")

    monkeypatch.setattr(builder, "_select_tables", parse_must_not_run)
    with pytest.raises(ValueError, match="source-byte drift"):
        builder.extract_b2_b11_source_evidence()


def test__vb7_fragment_hashes__come_from_verified_source_text():
    inputs = builder._verified_vb7_inputs()
    candidates = {
        row["candidate_id"]: row
        for row in builder.vb7_adjudication()["candidate_constructions"]
    }
    vi_g1 = candidates["trustees_vi_g1_taxable_payroll_to_gdp"]
    vi_definition = builder._source_fragment(
        inputs["trustees_vi_g1_tables"],
        required_text="Total earnings subject to OASDI contribution rates",
        source_document_id=builder.TRUSTEES_VI_G1_DOCUMENT_ID,
    )
    vi_header = builder._source_fragment(
        [inputs["trustees_vi_g1"]],
        required_text="Ratio of taxable payroll to GDP",
        source_document_id=builder.TRUSTEES_VI_G1_DOCUMENT_ID,
    )
    assert (
        vi_g1["source_definition_fragment_sha256"]
        == hashlib.sha256(vi_definition.encode("utf-8")).hexdigest()
    )
    assert (
        vi_g1["ratio_header_fragment_sha256"]
        == hashlib.sha256(vi_header.encode("utf-8")).hexdigest()
    )

    trustees_definition = builder._source_fragment(
        inputs["trustees_tables"],
        required_text=(
            "Workers who are paid at some time during the year for employment"
        ),
        source_document_id=builder.TRUSTEES_COVERED_WORKERS_DOCUMENT_ID,
    )
    iv_candidates = (
        (
            "trustees_iv_b4_covered_workers_per_oasdi_beneficiary",
            "Covered workers per OASDI beneficiary",
        ),
        (
            "trustees_iv_b4_oasdi_beneficiaries_per_100_covered_workers",
            "OASDI beneficiaries per 100 covered workers",
        ),
    )
    for candidate_id, header_text in iv_candidates:
        candidate = candidates[candidate_id]
        header = builder._source_fragment(
            [inputs["trustees"]],
            required_text=header_text,
            source_document_id=builder.TRUSTEES_COVERED_WORKERS_DOCUMENT_ID,
        )
        assert (
            candidate["source_definition_fragment_sha256"]
            == hashlib.sha256(trustees_definition.encode("utf-8")).hexdigest()
        )
        assert (
            candidate["ratio_header_fragment_sha256"]
            == hashlib.sha256(header.encode("utf-8")).hexdigest()
        )

    quotient = candidates[
        "supplement_2023_table4_b10_oasdi_workers_over_"
        "table4_b12_hi_workers"
    ]
    total_header = builder.TABLE4_B10_B12_TOTAL_WORKERS_HEADER
    b10_literal = builder._selected_literal(
        builder._unique_stub_row(
            inputs["table4_b10"],
            stub_text="All areas",
        ),
        builder._unique_column(inputs["table4_b10"], total_header),
        where="test/table4.b10/all_areas/total",
    )
    b12_literal = builder._selected_literal(
        builder._unique_stub_row(
            inputs["table4_b12"],
            stub_text="All areas",
        ),
        builder._unique_column(inputs["table4_b12"], total_header),
        where="test/table4.b12/all_areas/total",
    )
    b10_value = builder.entry10._parse_integer_cell(
        b10_literal,
        where="test/table4.b10/all_areas/total",
    )
    b12_value = builder.entry10._parse_integer_cell(
        b12_literal,
        where="test/table4.b12/all_areas/total",
    )
    ratio = Fraction(b10_value, b12_value)
    assert ratio == Fraction(182_689, 186_620)
    assert builder._fraction_decimal(ratio, places=10) == "0.9789358054"
    assert (
        quotient["numerator_fragment_sha256"]
        == hashlib.sha256(b10_literal.encode("utf-8")).hexdigest()
    )
    assert (
        quotient["denominator_fragment_sha256"]
        == hashlib.sha256(b12_literal.encode("utf-8")).hexdigest()
    )
    assert (
        quotient["operand_fragment_composite_sha256"]
        == hashlib.sha256(
            b10_literal.encode("utf-8") + b"\x00" + b12_literal.encode("utf-8")
        ).hexdigest()
    )

    note_fields = (
        (
            (
                "SOURCE: Social Security Administration, Continuous Work "
                "History Sample"
            ),
            "cwhs_source_fragment_sha256",
        ),
        (
            (
                "National and state totals and subtotals are unduplicated "
                "counts of workers in each type of employment."
            ),
            "unduplicated_worker_rule_fragment_sha256",
        ),
        (
            "NOTES: Data are based on preliminary estimates.",
            "preliminary_status_fragment_sha256",
        ),
    )
    for required_text, field in note_fields:
        b10_fragment = builder._source_fragment(
            [inputs["table4_b10"]],
            required_text=required_text,
            source_document_id=builder.SOURCE_DOCUMENT_ID,
        )
        b12_fragment = builder._source_fragment(
            [inputs["table4_b12"]],
            required_text=required_text,
            source_document_id=builder.SOURCE_DOCUMENT_ID,
        )
        assert b10_fragment == b12_fragment
        assert (
            quotient[field]
            == hashlib.sha256(b10_fragment.encode("utf-8")).hexdigest()
        )


def test__partial_attack_helper__has_valid_self_hash_before_mutation():
    artifact = builder.build()
    preimage = copy.deepcopy(artifact)
    preimage["integrity"]["content_sha256"] = "0" * 64
    assert (
        artifact["integrity"]["content_sha256"]
        == hashlib.sha256(
            builder.entry10.canonical_json_bytes(preimage)
        ).hexdigest()
    )


@pytest.mark.parametrize(
    ("span_attribute", "expected"),
    (
        (b'colspan="2"', r"rowspan=1, colspan=2"),
        (b'rowspan="2"', r"rowspan=2, colspan=1"),
    ),
)
def test__parser_attack__rejects_selected_cell_span_collapse(
    span_attribute: bytes,
    expected: str,
):
    original = b'<td headers="r18 c3 c5">413,600</td>'
    mutated = b"<td " + span_attribute + b' headers="r18 c3 c5">413,600</td>'
    with pytest.raises(ValueError, match=expected):
        _extract_after_source_mutation(original, mutated)


def test__parser_attack__rejects_numeric_footnote_insertion():
    original = b'<td headers="r18 c3 c5">413,600</td>'
    mutated = b'<td headers="r18 c3 c5">413,600<sup>a</sup></td>'
    with pytest.raises(ValueError, match="missing or nonnumeric"):
        _extract_after_source_mutation(original, mutated)


def test__parser_attack__rejects_malformed_thousands_grouping():
    original = b'<td headers="r18 c3 c5">413,600</td>'
    mutated = b'<td headers="r18 c3 c5">413,60</td>'
    with pytest.raises(ValueError, match="missing or nonnumeric"):
        _extract_after_source_mutation(original, mutated)


def test__parser_attack__rejects_nested_header_drift():
    original = (
        b'<th rowspan="2" id="c5" headers="c3">'
        b"Total in covered employment&nbsp;<sup>b</sup> "
        b"(millions of&nbsp;dollars)</th>"
    )
    mutated = original.replace(
        b"Total in covered employment",
        b"Total covered employment",
    )
    with pytest.raises(ValueError, match="selected 0 columns"):
        _extract_after_source_mutation(original, mutated)
