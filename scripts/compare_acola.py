#!/usr/bin/env python3
"""Registration 18 comparison, for the validation lane after seal opening.

This standard-library program fetches nothing. Decimal values in its JSON
output are strings, preserving the computed digits without a float conversion.
The only float conversion implements the explicitly registered MINT reading S.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import re
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal, localcontext
from pathlib import Path

PRECISION = 50
BANDS = ("Total", "62-69", "70-79", "80-89", "90+")
MINT_STATISTICS = (
    "median_individual_pct_change",
    "difference_of_weighted_medians_pct",
    "ratio_of_scenario_means",
)
OACT_FOOTER = "Based on Intermediate Assumptions of the 2026 Trustees Report"


def _decimal(value):
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("a boolean is not a decimal")
    parsed = Decimal(str(value))
    if not parsed.is_finite():
        raise ValueError("nonfinite decimal")
    return parsed


def _decimals(value):
    if value is None:
        return None
    parsed = int(value)
    if parsed < 0 or Decimal(str(value)) != parsed:
        raise ValueError("decimal count must be a nonnegative integer")
    return parsed


def _half_unit(decimals):
    return Decimal(5).scaleb(-decimals - 1)


def _undefined(reason):
    return {
        "point": None,
        "lower": None,
        "upper": None,
        "undefined_reason": reason,
    }


def _interval(point, lower=None, upper=None):
    return {
        "point": point,
        "lower": point if lower is None else lower,
        "upper": point if upper is None else upper,
        "undefined_reason": None,
    }


def subtract_interval(left, right):
    """Return [a,b] - [c,d] = [a-d,b-c], retaining undefined reasons."""
    if left["lower"] is None or right["lower"] is None:
        reasons = [
            item["undefined_reason"]
            for item in (left, right)
            if item["lower"] is None
        ]
        return _undefined("; ".join(reasons))
    with localcontext() as context:
        context.prec = PRECISION
        return _interval(
            left["point"] - right["point"],
            left["lower"] - right["upper"],
            left["upper"] - right["lower"],
        )


def _corners(first, second, first_decimals, second_decimals, function):
    with localcontext() as context:
        context.prec = PRECISION
        corners = [
            function(a, b)
            for a, b in itertools.product(
                (
                    first - _half_unit(first_decimals),
                    first + _half_unit(first_decimals),
                ),
                (
                    second - _half_unit(second_decimals),
                    second + _half_unit(second_decimals),
                ),
            )
        ]
        return _interval(function(first, second), min(corners), max(corners))


def _oact_formula(proposal, change):
    if proposal - change <= 0:
        raise ValueError("OACT p - d must be positive at every corner")
    return Decimal(100) * change / (proposal - change)


def oact_comparison(record):
    """Compute C_OACT and its registered printed-precision interval."""
    record = record or {}
    year = record.get("row_label_verbatim")
    if year is not None and str(year).strip() != "2030":
        raise ValueError("OACT row must be 2030")
    columns = {
        column["key"]: column
        for column in (record.get("columns") or [])
        if column is not None
    }
    proposal = columns.get("proposal_cost_rate") or {}
    change = columns.get("change_cost_rate") or {}
    p, d = (_decimal(item.get("value")) for item in (proposal, change))
    pd, dd = (_decimals(item.get("decimals")) for item in (proposal, change))
    gate = (
        None
        if p is None or d is None
        else (
            "PWBM_primary_OACT_report_only"
            if min(p.copy_abs(), d.copy_abs()) < Decimal("0.10")
            else "OACT_primary_PWBM_secondary"
        )
    )
    value = (
        _undefined("missing OACT cost value or printed decimals")
        if None in (p, d, pd, dd)
        else _corners(p, d, pd, dd, _oact_formula)
    )
    with localcontext() as context:
        context.prec = PRECISION
        current_law = None if p is None or d is None else p - d
    return {
        "value": value,
        "branch": "four_corners",
        "current_law_cost_rate": current_law,
        "precision_gate": gate,
        "report_only": True,
        "income_rate_memo": {
            key: columns.get(key)
            for key in ("proposal_income_rate", "change_income_rate")
        },
    }


def _pwbm_formula(baseline, reform):
    if baseline <= 0:
        raise ValueError("PWBM B must be positive at every corner")
    return Decimal(100) * (reform - baseline) / baseline


def pwbm_comparison(record):
    """Use the six-decimal point rule, otherwise all four corners."""
    record = record or {}
    row = record.get("row_2030") or {}
    if row.get("year") is not None and str(row["year"]) != "2030":
        raise ValueError("PWBM row must be 2030")
    decimals = record.get("stored_decimals") or {}
    keys = ("Baseline cost rate", "A1 cost rate")
    b, r = (_decimal(row.get(key)) for key in keys)
    bd, rd = (_decimals(decimals.get(key)) for key in keys)
    if None in (b, r, bd, rd):
        value, branch = (
            _undefined("missing PWBM cost value or stored decimals"),
            None,
        )
    elif min(bd, rd) >= 6:
        with localcontext() as context:
            context.prec = PRECISION
            value, branch = _interval(_pwbm_formula(b, r)), "point"
    else:
        value = _corners(b, r, bd, rd, _pwbm_formula)
        branch = "four_corners"
    return {
        "value": value,
        "branch": branch,
        "report_only": True,
        "income_rate_memo": {
            key: row.get(key)
            for key in ("Baseline income rate", "A1 income rate")
        },
    }


def _percent_format(number_format):
    """Excel's quoted and escaped percent signs are literals."""
    unquoted = re.sub(r'"[^\"]*"', "", number_format)
    return "%" in re.sub(r"\\.", "", unquoted)


def mint_interval(cell, reading="S"):
    """Apply reading S or sensitivity L and identify both rounding modes."""
    cell = cell or {}
    html = _decimal(cell.get("html_value"))
    html_decimals = _decimals(cell.get("html_decimals"))
    if html is None or html_decimals is None:
        return {
            "value": _undefined("missing MINT HTML value or decimals"),
            "reading": reading,
            "branch": None,
            "rounding_modes_agree": [],
            "matching_modes": [],
        }
    if reading == "S":
        raw, number_format = cell.get("xlsx_raw"), cell.get(
            "xlsx_number_format"
        )
        if raw is None or number_format is None:
            stored, stored_decimals = None, None
        else:
            double = float(raw)
            if not math.isfinite(double):
                raise ValueError("nonfinite stored MINT double")
            # repr gives the shortest round-trip digits but writes an
            # integral double with a non-significant ".0". normalize()
            # drops it, so the count is that of the shortest decimal
            # string that denotes the double (review r1b, finding 1).
            # normalize() and scaleb() round to the context's precision,
            # so both run at PRECISION, not the caller's (review r2, 3).
            with localcontext() as context:
                context.prec = PRECISION
                stored = Decimal(repr(double)).normalize()
                if _percent_format(number_format):
                    stored = stored.scaleb(2)
                stored_decimals = max(0, -stored.as_tuple().exponent)
    elif reading == "L":
        stored = _decimal(cell.get("xlsx_value_pct"))
        stored_decimals = _decimals(cell.get("xlsx_decimals_pct"))
    else:
        raise ValueError("MINT reading must be S or L")
    with localcontext() as context:
        context.prec = PRECISION
        quantum = Decimal(1).scaleb(-html_decimals)
        modes = (
            []
            if stored is None
            else [
                name
                for name, mode in (
                    ("half_up", ROUND_HALF_UP),
                    ("half_even", ROUND_HALF_EVEN),
                )
                if stored.quantize(quantum, rounding=mode) == html
            ]
        )
        use_stored = (
            stored is not None
            and stored_decimals is not None
            and stored_decimals > html_decimals
            and bool(modes)
        )
        point, decimals = (
            (stored, stored_decimals) if use_stored else (html, html_decimals)
        )
        half = _half_unit(decimals)
        return {
            "value": _interval(point, point - half, point + half),
            "reading": reading,
            "branch": "xlsx" if use_stored else "html",
            "rounding_modes_agree": modes,
            "matching_modes": modes,
            "stored_value_pct": stored,
            "stored_decimals_pct": stored_decimals,
            "missing_xlsx": stored is None or stored_decimals is None,
        }


def _summary_interval(summary, missing_reason):
    mean = _decimal(summary.get("mean"))
    if mean is None:
        return _undefined(summary.get("undefined_reason") or missing_reason)
    return _interval(mean)


def _null_interval(nulls, key):
    record = nulls.get(key) or {}
    exact = record.get("exact") or {}
    numerator = _decimal(exact.get("numerator"))
    denominator = _decimal(exact.get("denominator"))
    if numerator is not None and denominator is not None:
        if denominator == 0:
            raise ValueError(f"zero denominator for exact null {key}")
        with localcontext() as context:
            context.prec = PRECISION
            value = numerator / denominator
    elif record.get("value_decimal") is not None:
        value = _decimal(record["value_decimal"])
    else:
        value = _decimal(record.get("value"))
    return (
        _undefined(record.get("undefined_reason") or f"missing null {key}")
        if value is None
        else _interval(value)
    )


def _comparison(summary, comparator, nulls, null_key, model_null_key):
    summary = summary or {
        "mean": None,
        "sample_sd": None,
        "floor": None,
        "undefined_reason": "missing model statistic",
    }
    model = _summary_interval(summary, "undefined model statistic")
    null = _null_interval(nulls, null_key)
    model_null = _null_interval(nulls, model_null_key)
    return {
        "model": summary,
        "comparator": comparator,
        "null_key": null_key,
        "model_null_key": model_null_key,
        "model_minus_comparator": subtract_interval(model, comparator),
        "null_minus_comparator": subtract_interval(null, comparator),
        "model_minus_null": subtract_interval(model, null),
        "model_minus_model_null": subtract_interval(model, model_null),
    }


def _split(record, flag):
    printed = record.get(flag)
    if printed is False:
        return {
            "printed": False,
            "comparison": None,
            "note": "not printed by the comparator",
        }
    return {
        "printed": printed,
        "comparison": None,
        "undefined_reason": (
            "numeric split schema unspecified"
            if printed
            else "split availability not stated"
        ),
        "note": "carried fields are retained in comparator_record",
    }


def _flags(record):
    flags = {
        key: record.get(key)
        for key in (
            "cost_includes_admin_expenses",
            "cost_includes_railroad_interchange",
        )
    }
    admin, railroad = flags.values()
    return {
        **flags,
        "dilution": (
            "unsigned"
            if railroad != "no" or admin in (None, "not_stated")
            else (
                "toward zero"
                if admin == "yes"
                else "none from these cost items"
            )
        ),
        "administrative_expenses_effect": {
            "yes": "dilutes toward zero",
            "no": "excluded",
        }.get(admin, "not stated"),
        "railroad_interchange_effect": {
            "yes": "direction unknown",
            "no": "excluded",
        }.get(railroad, "not stated"),
        "december_2030_timing": record.get("december_2030_timing"),
    }


def _registration_checks(record, keys):
    return {
        key: {
            "matches": record.get(key),
            "undefined_reason": (
                "source lacks registration-match flag"
                if record.get(key) is None
                else None
            ),
        }
        for key in keys
    }


def oact_footer_matches(footer):
    """Whether a transcribed OACT footer has the registered words.

    Whitespace runs of any kind (``str.split`` also splits on no-break
    and thin spaces) and any run of periods and whitespace after the last
    word are transcription details, not words of the footer (reviews
    r1b, finding 2, and r2, finding 1). Every word must match.
    """
    return " ".join(footer.split()).rstrip(". ") == OACT_FOOTER


def _written_decimals(value):
    """The decimals in a value as the record writes it, else None.

    ``_load`` keeps each JSON number as an int or as a Decimal built from
    its literal, and the Decimal constructor keeps the literal's exponent
    without normalizing it, so a trailing zero counts as written:
    "12.30" has two decimals and "12.300" three. A string is read the
    same way. A float has lost its written digits, and a value that
    writes no finite number has none to count.
    """
    if isinstance(value, (bool, float)):
        return None
    if isinstance(value, int):
        return 0
    if isinstance(value, str):
        try:
            value = Decimal(value)
        except ArithmeticError:
            return None
    if not isinstance(value, Decimal) or not value.is_finite():
        return None
    return max(0, -value.as_tuple().exponent)


def decimal_count_mismatches(comparator):
    """Locate each decimal count that differs from its value as written.

    It checks every count the comparison computes with: ``decimals`` of
    OACT's two cost-rate columns, PWBM's ``stored_decimals`` of its two
    2030 cost rates, and ``html_decimals`` of each MINT band's
    ``median_diff_pct`` cell. A count matches when it equals the decimals
    its value writes, trailing zeros included (:func:`_written_decimals`).
    A count that is not a nonnegative integer, or a value that writes no
    finite number, never matches. A float value never matches either:
    load records with :func:`_load`, which yields none. A missing value
    or count is not checked; the conversion reports it as undefined.
    Returns ``(cell, field)`` locators, never a value, and needs nothing
    but the comparator record (review r2, finding 4).
    """
    mismatches = []

    def check(cell, field, value, count):
        if value is None or count is None:
            return
        try:
            parsed = _decimals(count)
        except (ArithmeticError, TypeError, ValueError):
            parsed = None
        written = _written_decimals(value)
        if parsed is None or written is None or parsed != written:
            mismatches.append((cell, field))

    oact = comparator.get("oact") or {}
    columns = {
        column["key"]: column
        for column in (oact.get("columns") or [])
        if column is not None
    }
    for key in ("proposal_cost_rate", "change_cost_rate"):
        column = columns.get(key) or {}
        check(
            f"oact.columns.{key}",
            "decimals",
            column.get("value"),
            column.get("decimals"),
        )
    pwbm = comparator.get("pwbm") or {}
    row = pwbm.get("row_2030") or {}
    counts = pwbm.get("stored_decimals") or {}
    for key in ("Baseline cost rate", "A1 cost rate"):
        check(
            f"pwbm.row_2030.{key}",
            "stored_decimals",
            row.get(key),
            counts.get(key),
        )
    mint = comparator.get("mint5") or {}
    bands = (mint.get("table1") or {}).get("rows") or {}
    for band in BANDS:
        cell = (bands.get(band) or {}).get("median_diff_pct") or {}
        check(
            f"mint5.table1.rows.{band}.median_diff_pct",
            "html_decimals",
            cell.get("html_value"),
            cell.get("html_decimals"),
        )
    return mismatches


def build_comparison(artifact, comparator):
    """Consume the stage-1 artifact shape without dropping undefined rows."""
    if comparator.get("schema_version") != "acola-comparator-v1":
        raise ValueError("expected acola-comparator-v1")
    oact, pwbm, mint = (
        comparator.get(key) or {} for key in ("oact", "pwbm", "mint5")
    )
    footer = oact.get("footer_verbatim")
    if footer is not None and not oact_footer_matches(footer):
        raise ValueError("OACT footer does not match registration")
    for key in (
        "footer_matches_registration",
        "provision_text_matches_registration",
    ):
        if oact.get(key) is False:
            raise ValueError(f"OACT {key} is false")
    mismatches = decimal_count_mismatches(comparator)
    if mismatches:
        raise ValueError(
            "decimal counts differ from the values as written at: "
            + "; ".join(f"{cell} ({field})" for cell, field in mismatches)
        )
    nulls, rows = artifact.get("nulls") or {}, artifact.get("rows") or {}
    cost = {}
    for name, record, conversion in (
        ("OACT", oact, oact_comparison(oact)),
        ("PWBM", pwbm, pwbm_comparison(pwbm)),
    ):
        cost[name] = {
            "conversion": conversion,
            "comparator_record": record,
            "registration_checks": _registration_checks(
                record,
                (
                    (
                        "footer_matches_registration",
                        "provision_text_matches_registration",
                    )
                    if name == "OACT"
                    else ("last_modified_matches_registration",)
                ),
            ),
            "flags": _flags(record),
            "oasi_di_split": _split(record, "prints_oasi_di_split_2030"),
            "rows": {
                row: {
                    **_comparison(
                        (rows.get(row) or {}).get("statistics", {}).get("P"),
                        conversion["value"],
                        nulls,
                        "N",
                        "N_model",
                    ),
                    "all_model_statistics": (rows.get(row) or {}).get(
                        "statistics"
                    ),
                    "model_row_record": rows.get(row),
                }
                for row in ("C0", "C1")
            },
        }
    median_type = mint.get("median_type")
    headline = {
        "median_of_individual_differences": MINT_STATISTICS[0],
        "difference_of_medians": MINT_STATISTICS[1],
    }.get(median_type)
    mint_rows = {}
    source_bands = (mint.get("table1") or {}).get("rows") or {}
    for row_id in ("M0", "M1", "M2", "M3", "M4"):
        null_key = "N_M1" if row_id == "M1" else "N_MINT"
        model_row = rows.get(row_id) or {}
        band_results = {}
        for band in BANDS:
            source_band = source_bands.get(band) or {}
            cell = source_band.get("median_diff_pct")
            registered, literal = mint_interval(cell), mint_interval(cell, "L")
            model_band = (model_row.get("bands") or {}).get(band) or {}
            statistics = model_band.get("statistics") or {}
            band_results[band] = {
                "registered_reading_S": registered,
                "sensitivity_reading_L": literal,
                "headline_statistic": headline,
                "statistics": {
                    statistic: {
                        **_comparison(
                            statistics.get(statistic),
                            registered["value"],
                            nulls,
                            null_key,
                            null_key,
                        ),
                        "role": (
                            "headline" if statistic == headline else "beside"
                        ),
                        "compared_as_median": statistic == headline
                        or (
                            headline is None
                            and statistic in MINT_STATISTICS[:2]
                        ),
                        "sensitivity_reading_L": _comparison(
                            statistics.get(statistic),
                            literal["value"],
                            nulls,
                            null_key,
                            null_key,
                        ),
                    }
                    for statistic in MINT_STATISTICS
                },
                "model_memo_items": {
                    key: statistics.get(key)
                    for key in (
                        "baseline_falling_share",
                        "median_benefit_base",
                        "median_benefit_reform",
                    )
                },
                "comparator_memo_items": {
                    key: value
                    for key, value in source_band.items()
                    if key != "median_diff_pct"
                },
                "dollar_levels_compared": False,
                "model_band_record": model_band,
            }
        mint_rows[row_id] = {
            "bands": band_results,
            "model_row_record": model_row,
        }
    return {
        "schema_version": "acola-comparison-v1",
        "report_only": True,
        "decimal_precision": PRECISION,
        "decimal_encoding": "JSON strings",
        "rounding_interpretation": "XLSX branch if either named mode agrees",
        "cost": cost,
        "mint5": {
            "comparator_record": mint,
            "headline_statistic": headline,
            "median_type": median_type,
            "start_date_reading": mint.get("start_date_reading"),
            "december_2030_timing": mint.get("december_2030_timing"),
            "oasi_di_split": _split(mint, "prints_oasi_di_split"),
            "table2_memo": mint.get("table2"),
            "rows": mint_rows,
        },
        "nulls": nulls,
        "N_minus_N_model": subtract_interval(
            _null_interval(nulls, "N"), _null_interval(nulls, "N_model")
        ),
        "deferred_rows": artifact.get("deferred_rows"),
        "model_artifact": artifact,
        "comparator_record": comparator,
    }


def _load(path):
    return json.loads(
        Path(path).read_text(encoding="utf-8-sig"),
        parse_float=Decimal,
        parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError(f"nonfinite JSON number: {value}")
        ),
    )


def _sha256(content):
    return hashlib.sha256(content).hexdigest()


def verify_seal(seal_path, comparator_path, evidence_root=None):
    """Hash every listed file before parsing any comparator or artifact."""
    seal_path, comparator_path = (
        Path(seal_path),
        Path(comparator_path).resolve(),
    )
    root = Path(evidence_root or seal_path.parent).resolve()
    seal_bytes = seal_path.read_bytes()
    seal = json.loads(seal_bytes)
    files = seal.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("seal has no file inventory")
    failures, verified = [], set()
    for relative, expected in files.items():
        path = (root / relative).resolve()
        if Path(relative).is_absolute() or not path.is_relative_to(root):
            failures.append(f"invalid seal path: {relative}")
            continue
        try:
            content = path.read_bytes()
        except OSError:
            failures.append(f"missing sealed file: {relative}")
            continue
        if _sha256(content) != expected.get("sha256") or len(
            content
        ) != expected.get("bytes"):
            failures.append(f"seal mismatch: {relative}")
        verified.add(path)
    if comparator_path not in verified:
        failures.append("comparator record is not listed in seal")
    if failures:
        raise ValueError("; ".join(failures))
    return {
        "seal_sha256": _sha256(seal_bytes),
        "verified_files": len(verified),
    }


def compare_files(
    artifact_path, comparator_path, seal_path, evidence_root=None
):
    verification = verify_seal(seal_path, comparator_path, evidence_root)
    artifact_path = Path(artifact_path)
    sidecar_path = artifact_path.with_suffix(".env.json")
    sidecar = _load(sidecar_path)
    content = artifact_path.read_bytes()
    if sidecar.get("artifact_sha256") != _sha256(content):
        raise ValueError("artifact SHA-256 differs from .env.json sidecar")
    if sidecar.get("artifact") != artifact_path.name:
        raise ValueError("sidecar names another artifact")
    result = build_comparison(_load(artifact_path), _load(comparator_path))
    result["verification"] = {
        **verification,
        "artifact_sha256": _sha256(content),
        "sidecar_sha256": _sha256(sidecar_path.read_bytes()),
    }
    return result


def _json_default(value):
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"cannot serialize {type(value).__name__}")


def json_result(result):
    return (
        json.dumps(result, indent=2, default=_json_default, allow_nan=False)
        + "\n"
    )


def _display(value):
    if isinstance(value, dict) and "lower" in value:
        if value["lower"] is None:
            return "undefined: " + value["undefined_reason"]
        return f'[{value["lower"]}, {value["upper"]}]'
    return json.dumps(
        value, default=_json_default, ensure_ascii=False
    ).replace("|", "\\|")


def markdown_result(result):
    """Include all digits, uncertainty, null reasons, flags and source memos."""
    verification = result.get("verification") or {}
    lines = [
        "# Registration 18 comparison (report-only)",
        "",
        f'Seal SHA-256: `{verification.get("seal_sha256")}`',
        "",
        "Decimal arithmetic uses 50 significant digits; decimal JSON values are strings.",
        "",
        "| Row | Comparator | Band/statistic | Mean | Draw SD | Floor | Comparator interval | Model − comparator | Null − comparator | Model − null | Model − model null |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]

    def append(row, source, label, comparison):
        model = comparison["model"]
        values = [
            row,
            source,
            label,
            model.get("mean"),
            model.get("sample_sd"),
            model.get("floor"),
            comparison["comparator"],
            comparison["model_minus_comparator"],
            comparison["null_minus_comparator"],
            comparison["model_minus_null"],
            comparison["model_minus_model_null"],
        ]
        lines.append(
            "| " + " | ".join(_display(item) for item in values) + " |"
        )

    for name, source in result["cost"].items():
        for row, comparison in source["rows"].items():
            append(row, name, "P", comparison)
    for row, record in result["mint5"]["rows"].items():
        for band, cell in record["bands"].items():
            for statistic, comparison in cell["statistics"].items():
                append(
                    row,
                    "MINT5 S",
                    f"{band}: {statistic} ({comparison['role']})",
                    comparison,
                )
                append(
                    row,
                    "MINT5 L sensitivity",
                    f"{band}: {statistic}",
                    comparison["sensitivity_reading_L"],
                )
    lines += [
        "",
        "All carried records, memo items, timing and cost-definition flags,",
        "rounding branches, deferred rows and undefined reasons follow.",
        "Dollar levels are memo items; no dollar-level comparison is made.",
        "",
        "```json",
        json_result(result).rstrip(),
        "```",
        "",
    ]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", required=True, type=Path)
    parser.add_argument("--comparator", required=True, type=Path)
    parser.add_argument("--seal", required=True, type=Path)
    parser.add_argument("--evidence-root", type=Path)
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--output-markdown", required=True, type=Path)
    args = parser.parse_args(argv)
    result = compare_files(
        args.artifact, args.comparator, args.seal, args.evidence_root
    )
    inputs = {
        args.artifact.resolve(),
        args.artifact.with_suffix(".env.json").resolve(),
        args.comparator.resolve(),
        args.seal.resolve(),
    }
    outputs = {args.output_json.resolve(), args.output_markdown.resolve()}
    if inputs & outputs or len(outputs) != 2:
        raise ValueError("comparison outputs must be distinct from inputs")
    args.output_json.write_text(json_result(result), encoding="utf-8")
    args.output_markdown.write_text(markdown_result(result), encoding="utf-8")
    print(f'Seal SHA-256: {result["verification"]["seal_sha256"]}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
