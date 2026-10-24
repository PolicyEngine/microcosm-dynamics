"""Registration 18 comparison rules, using wholly invented source values."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from copy import deepcopy
from decimal import Decimal, localcontext
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "_compare_acola", ROOT / "scripts" / "compare_acola.py"
)
compare = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(compare)
D = Decimal


def invented_cell(**changes):
    cell = {
        "html_display": "-7.3",
        "html_value": "-7.3",
        "html_decimals": 1,
        "xlsx_cell": "D7",
        "xlsx_raw": "-0.073200000000000001",
        "xlsx_number_format": "0.0%",
        "xlsx_value_pct": "-7.3200000000000001",
        "xlsx_decimals_pct": 16,
        "pdf_display": "-7.3",
    }
    cell.update(changes)
    return cell


def invented_comparator():
    """Schema-only fixture; these values describe no published comparator."""
    timing = {
        "reading": "not_stated",
        "evidence_verbatim": "INVENTED timing note",
        "evidence_source": "invented.txt",
    }
    return {
        "schema_version": "acola-comparator-v1",
        "producer": "invented",
        "sources": {},
        "oact": {
            "footer_verbatim": compare.OACT_FOOTER + ".",
            "footer_matches_registration": True,
            "provision_text_matches_registration": True,
            "row_label_verbatim": "2030",
            "columns": [
                {
                    "key": key,
                    "header_verbatim": "INVENTED " + key,
                    "display": value,
                    "value": value,
                    "decimals": 2,
                }
                for key, value in (
                    ("proposal_cost_rate", "21.75"),
                    ("change_cost_rate", "-0.75"),
                    ("proposal_income_rate", "18.25"),
                    ("change_income_rate", "-0.25"),
                )
            ],
            "prints_oasi_di_split_2030": False,
            "cost_includes_admin_expenses": "yes",
            "cost_includes_railroad_interchange": "yes",
            "december_2030_timing": timing,
        },
        "pwbm": {
            "last_modified": "INVENTED",
            "last_modified_matches_registration": True,
            "row_2030": {
                "year": "2030",
                "Baseline income rate": "14.000000",
                "Baseline cost rate": "25.000000",
                "A1 income rate": "13.500000",
                "A1 cost rate": "24.000000",
            },
            "stored_decimals": {
                key: 6
                for key in (
                    "Baseline income rate",
                    "Baseline cost rate",
                    "A1 income rate",
                    "A1 cost rate",
                )
            },
            "prints_oasi_di_split_2030": False,
            "cost_includes_admin_expenses": "not_stated",
            "cost_includes_railroad_interchange": "not_stated",
            "december_2030_timing": timing,
        },
        "mint5": {
            "table1": {
                "rows": {
                    band: {
                        "median_diff_pct": invented_cell(),
                        "median_diff_dollars": None,
                        "median_monthly_scheduled": {"html_value": "1600"},
                        "median_monthly_option": {"html_value": "1500"},
                        "median_monthly_payable": None,
                        "pct_population_affected": {"html_value": "75"},
                    }
                    for band in compare.BANDS
                }
            },
            "table2": {"rows": {"Total": {"invented_memo": None}}},
            "median_type": "median_of_individual_differences",
            "start_date_reading": "unsettled",
            "december_2030_timing": timing,
            "prints_oasi_di_split": False,
        },
    }


def invented_summary(mean=-5):
    return {
        "mean": mean,
        "sample_sd": 0.125,
        "per_draw": [mean, mean],
        "floor": {
            "mean": None,
            "defined": False,
            "undefined_reason": "INVENTED empty half",
        },
        "undefined_reason": None if mean is not None else "empty band",
    }


def invented_artifact():
    summary = invented_summary()
    mint_stats = {stat: deepcopy(summary) for stat in compare.MINT_STATISTICS}
    mint_stats.update(
        {
            key: invented_summary(1000)
            for key in (
                "baseline_falling_share",
                "median_benefit_base",
                "median_benefit_reform",
            )
        }
    )
    rows = {
        row: {"statistics": {"P": deepcopy(summary)}} for row in ("C0", "C1")
    }
    rows.update(
        {
            row: {
                "bands": {
                    band: {"statistics": deepcopy(mint_stats)}
                    for band in compare.BANDS
                }
            }
            for row in ("M0", "M1", "M2", "M3", "M4")
        }
    )
    return {
        "schema_version": "acola-track-v1",
        "rows": rows,
        "nulls": {
            key: {"value": value}
            for key, value in (
                ("N", -3),
                ("N_model", -2),
                ("N_MINT", -17),
                ("N_M1", -18),
            )
        },
        "deferred_rows": {
            "C0-D": {"status": "deferred", "reason": "INVENTED"}
        },
    }


def write_inputs(tmp_path, artifact=None):
    artifact_path, record_path = (
        tmp_path / "invented.json",
        tmp_path / "reconciled.json",
    )
    artifact_path.write_text(json.dumps(artifact or invented_artifact()))
    sidecar = {
        "artifact": artifact_path.name,
        "artifact_sha256": hashlib.sha256(
            artifact_path.read_bytes()
        ).hexdigest(),
    }
    artifact_path.with_suffix(".env.json").write_text(json.dumps(sidecar))
    record_path.write_text(json.dumps(invented_comparator()))
    extra = tmp_path / "invented.txt"
    extra.write_text("INVENTED source bytes")
    files = {
        path.name: {
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "bytes": path.stat().st_size,
        }
        for path in (record_path, extra)
    }
    seal = tmp_path / "seal.json"
    seal.write_text(json.dumps({"files": files}))
    return artifact_path, record_path, seal


def test_oact_conversion_uses_proposal_minus_change_and_decimal_corners():
    result = compare.oact_comparison(invented_comparator()["oact"])
    with localcontext() as context:
        context.prec = compare.PRECISION
        assert result["value"]["point"] == D(100) * D("-0.75") / D("22.50")
    assert result["current_law_cost_rate"] == D("22.50")
    assert (
        result["value"]["lower"]
        < result["value"]["point"]
        < result["value"]["upper"]
    )
    assert result["precision_gate"] == "OACT_primary_PWBM_secondary"
    assert result["income_rate_memo"]["change_income_rate"]["value"] == "-0.25"


@given(
    p=st.integers(1, 10000), d=st.integers(-1000, 0), places=st.integers(1, 5)
)
@settings(max_examples=60, deadline=None)
def test_oact_corners_contain_point_and_monotonicity(p, d, places):
    record = invented_comparator()["oact"]
    record["columns"][0].update(value=str(p), decimals=places)
    record["columns"][1].update(value=str(d), decimals=places)
    interval = compare.oact_comparison(record)["value"]
    assert interval["lower"] <= interval["point"] <= interval["upper"]
    with localcontext() as context:
        context.prec = compare.PRECISION
        proposal, change, delta = D(p), D(d), D("0.001")
        base = compare._oact_formula(proposal, change)
        assert compare._oact_formula(proposal, change + delta) >= base
        assert compare._oact_formula(proposal + delta, change) >= base


@pytest.mark.parametrize(
    "value,expected",
    [
        ("-0.09", "PWBM_primary_OACT_report_only"),
        ("-0.10", "OACT_primary_PWBM_secondary"),
    ],
)
def test_oact_precision_gate_boundary(value, expected):
    record = invented_comparator()["oact"]
    record["columns"][1]["value"] = value
    assert compare.oact_comparison(record)["precision_gate"] == expected
    record["columns"][1]["value"] = "-0.09999999999999999999999999999999999"
    assert (
        compare.oact_comparison(record)["precision_gate"]
        == "PWBM_primary_OACT_report_only"
    )


def test_oact_decimals_are_not_hard_coded_and_every_corner_positive():
    record = invented_comparator()["oact"]
    record["columns"][0]["decimals"] = 0
    wider = compare.oact_comparison(record)["value"]
    original = compare.oact_comparison(invented_comparator()["oact"])["value"]
    assert wider["lower"] < original["lower"]
    assert wider["upper"] > original["upper"]
    record["columns"][0].update(value="0.01", decimals=2)
    record["columns"][1].update(value="0", decimals=0)
    with pytest.raises(ValueError, match="every corner"):
        compare.oact_comparison(record)


def test_oact_wrong_year_refuses():
    record = invented_comparator()["oact"]
    record["row_label_verbatim"] = "2031"
    with pytest.raises(ValueError, match="2030"):
        compare.oact_comparison(record)


@pytest.mark.parametrize(
    "bd,rd,branch",
    [
        (6, 6, "point"),
        (15, 15, "point"),
        (5, 6, "four_corners"),
        (6, 5, "four_corners"),
    ],
)
def test_pwbm_decimal_branches_and_point_containment(bd, rd, branch):
    record = invented_comparator()["pwbm"]
    record["stored_decimals"].update(
        {"Baseline cost rate": bd, "A1 cost rate": rd}
    )
    result = compare.pwbm_comparison(record)
    value = result["value"]
    assert result["branch"] == branch
    assert value["point"] == -4
    assert value["lower"] <= value["point"] <= value["upper"]
    assert (value["lower"] == value["upper"]) == (branch == "point")


@given(b=st.integers(1, 10000), r=st.integers(0, 10000))
@settings(max_examples=50, deadline=None)
def test_pwbm_corner_interval_contains_point(b, r):
    record = invented_comparator()["pwbm"]
    record["row_2030"].update(
        {"Baseline cost rate": str(b), "A1 cost rate": str(r)}
    )
    record["stored_decimals"].update(
        {"Baseline cost rate": 2, "A1 cost rate": 2}
    )
    value = compare.pwbm_comparison(record)["value"]
    assert value["lower"] <= value["point"] <= value["upper"]


def test_pwbm_refuses_nonpositive_corner_and_wrong_year():
    record = invented_comparator()["pwbm"]
    record["row_2030"]["Baseline cost rate"] = "0.001"
    record["stored_decimals"]["Baseline cost rate"] = 0
    with pytest.raises(ValueError, match="every corner"):
        compare.pwbm_comparison(record)
    record["row_2030"]["year"] = "2029"
    with pytest.raises(ValueError, match="2030"):
        compare.pwbm_comparison(record)


def test_mint_shortest_reading_S_and_literal_sensitivity_L():
    shortest = compare.mint_interval(invented_cell())
    literal = compare.mint_interval(invented_cell(), "L")
    assert shortest["branch"] == literal["branch"] == "xlsx"
    assert shortest["value"]["point"] == D("-7.32")
    assert shortest["stored_decimals_pct"] == 2
    assert literal["value"]["point"] == D("-7.3200000000000001")
    assert literal["stored_decimals_pct"] == 16
    assert shortest["matching_modes"] == ["half_up", "half_even"]
    assert shortest["value"]["lower"] == D("-7.325")
    assert shortest["value"]["upper"] == D("-7.315")


@pytest.mark.parametrize(
    "raw,html,expected_modes",
    [("-0.0725", "-7.3", ["half_up"]), ("-0.0725", "-7.2", ["half_even"])],
)
def test_negative_tie_discloses_agreeing_modes(raw, html, expected_modes):
    result = compare.mint_interval(
        invented_cell(xlsx_raw=raw, html_value=html)
    )
    assert result["branch"] == "xlsx"
    assert result["matching_modes"] == expected_modes


@pytest.mark.parametrize(
    "changes,point,branch",
    [
        ({"xlsx_raw": "-0.073"}, D("-7.3"), "html"),
        ({"xlsx_raw": "-0.0853"}, D("-7.3"), "html"),
        ({"xlsx_raw": None}, D("-7.3"), "html"),
        ({"xlsx_number_format": None}, D("-7.3"), "html"),
        (
            {"xlsx_raw": "-7.32", "xlsx_number_format": "0.00"},
            D("-7.32"),
            "xlsx",
        ),
        (
            {"xlsx_raw": "-7.32", "xlsx_number_format": '0.00"%"'},
            D("-7.32"),
            "xlsx",
        ),
        (
            {"xlsx_raw": "-7.32", "xlsx_number_format": "0.00\\%"},
            D("-7.32"),
            "xlsx",
        ),
        ({"xlsx_raw": "-7.32e-2"}, D("-7.32"), "xlsx"),
    ],
)
def test_mint_interval_branches_and_formats(changes, point, branch):
    result = compare.mint_interval(invented_cell(**changes))
    assert result["branch"] == branch
    assert result["value"]["point"] == point


def test_literal_branch_uses_recorded_count_and_fallback():
    cell = invented_cell(xlsx_value_pct="-7.35", xlsx_decimals_pct=2)
    assert compare.mint_interval(cell, "L")["branch"] == "html"
    cell["xlsx_value_pct"] = None
    assert compare.mint_interval(cell, "L")["missing_xlsx"] is True


def test_interval_subtraction_and_null_propagation():
    left = compare._interval(D(2), D(1), D(3))
    right = compare._interval(D(6), D(4), D(8))
    assert compare.subtract_interval(left, right) == compare._interval(
        D(-4), D(-7), D(-1)
    )
    assert (
        compare.subtract_interval(left, compare._undefined("missing"))[
            "undefined_reason"
        ]
        == "missing"
    )


def test_null_uses_exact_rational_then_decimal_before_float_approximation():
    record = {
        "exact": {"numerator": "-1", "denominator": "3"},
        "value_decimal": "-0.3333",
        "value": -0.33,
    }
    with localcontext() as context:
        context.prec = compare.PRECISION
        expected = -D(1) / D(3)
    assert compare._null_interval({"N": record}, "N")["point"] == expected
    record.pop("exact")
    assert compare._null_interval({"N": record}, "N")["point"] == D("-0.3333")
    record.pop("value_decimal")
    assert compare._null_interval({"N": record}, "N")["point"] == D("-0.33")


def test_real_spec_only_null_records_keep_exact_precision():
    from populace_dynamics.acola_track.nulls import build_nulls

    nulls = build_nulls()
    for key in ("N", "N_model", "N_MINT", "N_M1"):
        record = nulls[key]
        with localcontext() as context:
            context.prec = compare.PRECISION
            exact = D(record["exact"]["numerator"]) / D(
                record["exact"]["denominator"]
            )
        assert compare._null_interval(nulls, key)["point"] == exact


@pytest.mark.parametrize(
    "median_type,headline",
    [
        ("median_of_individual_differences", "median_individual_pct_change"),
        ("difference_of_medians", "difference_of_weighted_medians_pct"),
        ("unsettled", None),
        (None, None),
    ],
)
def test_headline_follows_record_and_all_rows_bands_statistics_survive(
    median_type, headline
):
    record = invented_comparator()
    record["mint5"]["median_type"] = median_type
    result = compare.build_comparison(invented_artifact(), record)
    assert result["mint5"]["headline_statistic"] == headline
    for row in ("M0", "M1", "M2", "M3", "M4"):
        bands = result["mint5"]["rows"][row]["bands"]
        assert set(bands) == set(compare.BANDS)
        for cell in bands.values():
            assert set(cell["statistics"]) == set(compare.MINT_STATISTICS)
            assert cell["headline_statistic"] == headline
            assert cell["dollar_levels_compared"] is False
            null_key = "N_M1" if row == "M1" else "N_MINT"
            value = cell["statistics"][compare.MINT_STATISTICS[0]]
            assert value["null_key"] == null_key
            assert value["model_minus_null"]["point"] == (
                13 if row == "M1" else 12
            )
    for source in result["cost"].values():
        assert set(source["rows"]) == {"C0", "C1"}
        for cell in source["rows"].values():
            assert cell["model_minus_null"]["point"] == -2
            assert cell["model_minus_model_null"]["point"] == -3


def test_null_fields_are_reported_never_guessed_and_empty_band_serializes():
    artifact, record = invented_artifact(), invented_comparator()
    artifact["rows"]["M0"]["bands"]["90+"]["statistics"][
        compare.MINT_STATISTICS[0]
    ] = invented_summary(None)
    record["oact"]["columns"][0]["value"] = None
    record["pwbm"]["stored_decimals"]["A1 cost rate"] = None
    record["mint5"]["table1"]["rows"]["90+"]["median_diff_pct"] = None
    record["mint5"]["start_date_reading"] = None
    result = compare.build_comparison(artifact, record)
    assert result["cost"]["OACT"]["conversion"]["value"]["point"] is None
    assert result["cost"]["PWBM"]["conversion"]["value"]["point"] is None
    cell = result["mint5"]["rows"]["M0"]["bands"]["90+"]
    assert cell["registered_reading_S"]["value"]["point"] is None
    assert cell["statistics"][compare.MINT_STATISTICS[0]][
        "model_minus_comparator"
    ]["undefined_reason"]
    serialized = compare.json_result(result)
    assert "empty band" in serialized
    assert "INVENTED empty half" in serialized
    assert "NaN" not in serialized


def test_flags_timing_memos_and_split_are_read_from_records():
    record = invented_comparator()
    record["mint5"]["start_date_reading"] = "M1"
    record["oact"]["december_2030_timing"][
        "reading"
    ] = "excludes_dec2030_increase"
    result = compare.build_comparison(invented_artifact(), record)
    assert result["cost"]["PWBM"]["flags"]["dilution"] == "unsigned"
    assert (
        result["cost"]["OACT"]["flags"]["december_2030_timing"]["reading"]
        == "excludes_dec2030_increase"
    )
    assert result["mint5"]["start_date_reading"] == "M1"
    assert result["mint5"]["table2_memo"] == record["mint5"]["table2"]
    assert (
        result["cost"]["OACT"]["oasi_di_split"]["note"]
        == "not printed by the comparator"
    )
    record["oact"]["prints_oasi_di_split_2030"] = True
    record["oact"]["invented_split_fields"] = {"retained": "123"}
    result = compare.build_comparison(invented_artifact(), record)
    assert (
        result["cost"]["OACT"]["oasi_di_split"]["undefined_reason"]
        == "numeric split schema unspecified"
    )
    assert result["cost"]["OACT"]["comparator_record"][
        "invented_split_fields"
    ] == {"retained": "123"}


@pytest.mark.parametrize(
    "admin,railroad,dilution",
    [
        ("no", "no", "none from these cost items"),
        ("yes", "no", "toward zero"),
        ("no", "yes", "unsigned"),
        ("yes", "not_stated", "unsigned"),
    ],
)
def test_dilution_claims_follow_each_flag(admin, railroad, dilution):
    flags = compare._flags(
        {
            "cost_includes_admin_expenses": admin,
            "cost_includes_railroad_interchange": railroad,
        }
    )
    assert flags["dilution"] == dilution
    assert (flags["administrative_expenses_effect"] == "excluded") == (
        admin == "no"
    )
    if railroad == "no":
        assert flags["railroad_interchange_effect"] == "excluded"


def test_missing_registration_flags_have_explicit_unknown_status():
    record = invented_comparator()
    record["oact"]["footer_matches_registration"] = None
    record["oact"]["provision_text_matches_registration"] = None
    result = compare.build_comparison(invented_artifact(), record)
    for check in result["cost"]["OACT"]["registration_checks"].values():
        assert check["matches"] is None
        assert check["undefined_reason"]


@pytest.mark.parametrize(
    "key",
    ["footer_matches_registration", "provision_text_matches_registration"],
)
def test_oact_registration_mismatch_refuses(key):
    record = invented_comparator()
    record["oact"][key] = False
    with pytest.raises(ValueError, match=key):
        compare.build_comparison(invented_artifact(), record)


def test_wrong_oact_footer_refuses_without_substitution():
    record = invented_comparator()
    record["oact"]["footer_verbatim"] = "INVENTED wrong vintage"
    with pytest.raises(ValueError, match="footer"):
        compare.build_comparison(invented_artifact(), record)


@pytest.mark.parametrize(
    "mutation", ["hash", "bytes", "missing", "unsealed_comparator"]
)
def test_seal_checks_every_entry_and_precedes_any_artifact_read(
    tmp_path, monkeypatch, mutation
):
    artifact, record, seal = write_inputs(tmp_path)
    inventory = json.loads(seal.read_text())
    if mutation == "hash":
        (tmp_path / "invented.txt").write_text("TAMPERED")
    elif mutation == "bytes":
        inventory["files"]["invented.txt"]["bytes"] += 1
    elif mutation == "missing":
        (tmp_path / "invented.txt").unlink()
    else:
        inventory["files"].pop("reconciled.json")
    seal.write_text(json.dumps(inventory))
    artifact.unlink()
    monkeypatch.setattr(
        compare,
        "_load",
        lambda path: pytest.fail("parsed values before seal verification"),
    )
    with pytest.raises(ValueError, match="seal|sealed"):
        compare.compare_files(artifact, record, seal)


def test_seal_reports_all_failures_and_refuses_path_escape(tmp_path):
    _, record, seal = write_inputs(tmp_path)
    inventory = json.loads(seal.read_text())
    inventory["files"].update(
        {
            "../outside": {"sha256": "x", "bytes": 0},
            "missing": {"sha256": "x", "bytes": 0},
        }
    )
    seal.write_text(json.dumps(inventory))
    with pytest.raises(ValueError) as error:
        compare.verify_seal(seal, record)
    assert "invalid seal path" in str(error.value)
    assert "missing sealed file" in str(error.value)


@pytest.mark.parametrize(
    "change", ["artifact", "sidecar_hash", "sidecar_filename"]
)
def test_artifact_sidecar_is_verified(tmp_path, change):
    artifact, record, seal = write_inputs(tmp_path)
    sidecar = artifact.with_suffix(".env.json")
    data = json.loads(sidecar.read_text())
    if change == "artifact":
        artifact.write_text("{}")
    elif change == "sidecar_hash":
        data["artifact_sha256"] = "0" * 64
    else:
        data["artifact"] = "another.json"
    sidecar.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="sidecar"):
        compare.compare_files(artifact, record, seal)


def test_cli_writes_exact_json_markdown_and_prints_seal_hash(tmp_path, capsys):
    artifact, record, seal = write_inputs(tmp_path)
    out_json, out_md = tmp_path / "result.json", tmp_path / "result.md"
    assert (
        compare.main(
            [
                "--artifact",
                str(artifact),
                "--comparator",
                str(record),
                "--seal",
                str(seal),
                "--output-json",
                str(out_json),
                "--output-markdown",
                str(out_md),
            ]
        )
        == 0
    )
    seal_hash = hashlib.sha256(seal.read_bytes()).hexdigest()
    assert seal_hash in capsys.readouterr().out
    result = json.loads(out_json.read_text())
    assert result["verification"]["seal_sha256"] == seal_hash
    assert result["verification"]["verified_files"] == 2
    markdown = out_md.read_text()
    assert "| Row | Comparator |" in markdown
    assert "MINT5 L sensitivity" in markdown
    assert '"sample_sd": "0.125"' in markdown
    assert "not printed by the comparator" in markdown
    assert '"value": "-7.3200000000000001"' not in markdown
    assert "-7.3200000000000001" in markdown
    assert "verdict" not in result and "pass_band" not in result


def test_load_keeps_decimals_bom_and_refuses_nonfinite(tmp_path):
    path = tmp_path / "number.json"
    path.write_text('\ufeff{"value": 1.2345678901234567890123456789}')
    assert compare._load(path)["value"] == D("1.2345678901234567890123456789")
    path.write_text('{"value": NaN}')
    with pytest.raises(ValueError, match="nonfinite"):
        compare._load(path)


def test_script_has_only_standard_library_dependencies():
    import sys

    tree = ast.parse((ROOT / "scripts" / "compare_acola.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(
                alias.name.split(".")[0] in sys.stdlib_module_names
                for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom):
            assert node.module.split(".")[0] in sys.stdlib_module_names


def test_consumes_actual_stage1_invented_dry_artifact_layout(tmp_path):
    from populace_dynamics.acola_track.runner import run_acola
    from tests.acola_track.test_runner import CONFIG, _inputs

    artifact = run_acola(_inputs(), config=CONFIG)
    paths = write_inputs(tmp_path, artifact)
    result = compare.compare_files(*paths)
    assert result["deferred_rows"]["C0-D"]["status"] == "deferred"
    assert set(result["mint5"]["rows"]) == {"M0", "M1", "M2", "M3", "M4"}
    source = artifact["rows"]["C0"]["statistics"]["P"]
    model = result["cost"]["OACT"]["rows"]["C0"]["model"]
    assert model["mean"] == D(str(source["mean"]))
    assert model["sample_sd"] == D(str(source["sample_sd"]))
    assert model["floor"]["defined"] == source["floor"]["defined"]
    assert (
        result["mint5"]["rows"]["M1"]["bands"]["Total"]["statistics"][
            compare.MINT_STATISTICS[0]
        ]["null_key"]
        == "N_M1"
    )
    compare.json_result(result)
