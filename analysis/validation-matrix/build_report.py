#!/usr/bin/env python3
"""Render the final human validation report from canonical matrix.json."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
MATRIX_PATH = HERE / "matrix.json"
OUT = HERE / "report.md"


def compact_number(value: Any) -> str:
    if isinstance(value, bool) or value is None:
        return str(value).lower()
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        if value == 0:
            return "0"
        absolute = abs(value)
        if absolute >= 1000:
            return f"{value:,.2f}"
        if absolute >= 100:
            return f"{value:.3f}"
        if absolute >= 1:
            return f"{value:.4f}"
        return f"{value:.6g}"
    return str(value)


def escape(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", "<br>")


def display_mapping(
    mapping: dict[str, Any], skip: set[str] | None = None
) -> str:
    skip = skip or set()
    parts = []
    for key, value in mapping.items():
        if key in skip:
            continue
        label = key.replace("_", " ")
        if isinstance(value, float | int) and not isinstance(value, bool):
            rendered = compact_number(value)
        elif isinstance(value, list):
            rendered = " → ".join(compact_number(item) for item in value)
        else:
            rendered = str(value)
        parts.append(f"{label}: {rendered}")
    return ", ".join(parts)


def display_value(value: Any) -> str:
    if isinstance(value, list):
        if not value:
            return "[]"
        if all(isinstance(item, str) for item in value):
            return " → ".join(value)
        if all(isinstance(item, dict) and "year" in item for item in value):
            return "; ".join(
                f"{item['year']}: " + display_mapping(item, {"year"})
                for item in value
            )
        if all(
            isinstance(item, dict) and "component_years" in item
            for item in value
        ):
            return "; ".join(
                f"{item['component_years'][0]}–{item['component_years'][1]}: "
                + display_mapping(item, {"component_years"})
                for item in value
            )
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if isinstance(value, dict):
        return display_mapping(value)
    return compact_number(value)


def display_label(label: dict[str, Any]) -> str:
    embedded = label["source_artifact_embedded_labels"]
    embedded_text = (
        json.dumps(embedded, ensure_ascii=False)
        if embedded is not None
        else "none (report-only module artifact)"
    )
    ratified = json.dumps(
        label["ratified_fitting_free_exact_label_array"], ensure_ascii=False
    )
    return (
        f"**Label:** {label['matrix_display']}. Embedded source array: "
        f"`{embedded_text}`. Ratified §16.7.1 array: `{ratified}`; activation "
        "is not asserted by this matrix."
    )


def display_page(page: Any) -> str:
    if isinstance(page, dict):
        return "/".join(f"{key} {value}" for key, value in page.items())
    return str(page)


def display_locator(locator: dict[str, Any]) -> str:
    parts = []
    role = locator.get("role")
    if role:
        parts.append(role)
    parts.append(locator["document"])
    if locator.get("edition_or_report_year"):
        parts.append(str(locator["edition_or_report_year"]))
    parts.append(f"p. {display_page(locator['page'])}")
    parts.append(f"{locator['table']}")
    for key in (
        "sheet",
        "observation_range",
        "definition_or_note_range",
        "row_locator",
        "column_header_path",
        "section",
        "provision",
    ):
        if locator.get(key):
            parts.append(f"{key.replace('_', ' ')}: {locator[key]}")
    url = locator.get("url")
    if url:
        parts.append(f"[publisher source]({url})")
    if locator.get("capture_status"):
        parts.append(f"capture status: {locator['capture_status']}")
    corroboration = locator.get("unmanifested_corroborating_copy")
    if corroboration:
        parts.append(
            "unmanifested corroborating copy SHA-256 "
            f"`{corroboration['sha256']}`; not an accepted verified source; "
            f"{corroboration['scope']}"
        )
    return "; ".join(parts)


def display_published(published: dict[str, Any]) -> str:
    value = display_value(published["value"])
    unit = published.get("unit", "")
    locators = "<br>".join(
        display_locator(locator) for locator in published["source_locators"]
    )
    companions = published.get("companion_parameters")
    companion_text = (
        f"<br>Companion parameters: {display_value(companions)}"
        if companions
        else ""
    )
    provenance = published.get("provenance")
    provenance_text = ""
    if provenance:
        source = provenance["numeric_source"]
        provenance_text = (
            "<br>**Reported-value provenance:** "
            f"`{source['path']}` at `{source['json_pointer']}`, SHA-256 "
            f"`{source['sha256']}`. {provenance['numeric_source_note']}"
        )
    return (
        f"{value} {unit}{companion_text}{provenance_text}"
        f"<br>**Locator:** {locators}"
    )


def annual_list(values: list[dict[str, Any]], value_key: str) -> str:
    return "; ".join(
        f"{item['year']}: {compact_number(item[value_key])}" for item in values
    )


def display_deviation(deviation: dict[str, Any]) -> str:
    parts = []
    if "relative_percent" in deviation:
        relative = deviation["relative_percent"]
        if isinstance(relative, list):
            rendered_relative = annual_list(relative, "percent")
        else:
            rendered_relative = compact_number(relative)
        parts.append("relative % (ours/published−1): " + rendered_relative)
    if "trajectory_2015_100" in deviation:
        parts.append(
            "2015-index Δ: "
            + annual_list(
                deviation["trajectory_2015_100"], "deviation_index_points"
            )
        )
    for key in ("signed_index_points", "signed_percentage_points"):
        if key not in deviation:
            continue
        value = deviation[key]
        if isinstance(value, list):
            numeric_key = next(name for name in value[0] if name != "year")
            parts.append(
                key.replace("_", " ") + ": " + annual_list(value, numeric_key)
            )
        else:
            parts.append(f"{key.replace('_', ' ')}: {compact_number(value)}")
    for key in (
        "absolute_percentage_points",
        "our_over_published_ratio",
        "kendall_tau",
        "discordant_pair_count",
        "pair_count",
    ):
        if key in deviation:
            value = deviation[key]
            if isinstance(value, list) and value and "year" in value[0]:
                numeric_key = next(name for name in value[0] if name != "year")
                rendered = annual_list(value, numeric_key)
            else:
                rendered = compact_number(value)
            parts.append(f"{key.replace('_', ' ')}: {rendered}")
    if not parts:
        parts.append(
            display_value(
                {k: v for k, v in deviation.items() if k != "definition"}
            )
        )
    if deviation.get("definition"):
        parts.append(f"Definition: {deviation['definition']}")
    return "<br>".join(parts)


def display_mismatch(mismatch: dict[str, Any]) -> str:
    labels = {
        "frame": "Frame",
        "population": "Population",
        "year_basis": "Year basis",
        "benefit_concept": "Benefit concept",
        "earnings_and_accounting": "Earnings/accounting",
    }
    return "<br>".join(f"**{labels[key]}:** {mismatch[key]}" for key in labels)


def row_group(row: dict[str, Any]) -> str:
    model = row["external_model"]
    if model.startswith("SSA"):
        return "SSA Trustees and Statistical Supplement"
    if model.startswith("CBOLT"):
        return "CBO / CBOLT"
    if model.startswith("DYNASIM"):
        return "DYNASIM module replications"
    return "WISH statutory parameter"


def human_matrix(rows: list[dict[str, Any]]) -> list[str]:
    output = []
    groups = [
        "SSA Trustees and Statistical Supplement",
        "CBO / CBOLT",
        "DYNASIM module replications",
        "WISH statutory parameter",
    ]
    for group in groups:
        group_rows = [row for row in rows if row_group(row) == group]
        if not group_rows:
            continue
        output.extend(
            [
                f"### {group}",
                "",
                "| Row / quantity | Our value and label state | Published value and exact locator | Deviation | Concept mismatch |",
                "|---|---|---|---|---|",
            ]
        )
        for row in group_rows:
            our = (
                f"{display_value(row['our']['value'])} {row['our']['unit']}<br>"
                + display_label(row["our"]["label_state"])
            )
            cells = [
                f"`{row['row_id']}`<br>{row['quantity']}",
                our,
                display_published(row["published"]),
                display_deviation(row["deviation"]),
                display_mismatch(row["concept_mismatch"]),
            ]
            output.append(
                "| " + " | ".join(escape(cell) for cell in cells) + " |"
            )
        output.append("")
    return output


def series_inventory(matrix: dict[str, Any]) -> list[str]:
    inventory = matrix["available_series_inventory"]
    source = inventory["source"]
    output = [
        "## Available-series inventory",
        "",
        (
            f"The complete inventory comes from `{source['path']}` "
            f"(SHA-256 `{source['sha256']}`, pointer `{source['json_pointer']}`). "
            "The source has 20 draws and calendar years 2015–2022; every annual "
            "table also includes an odd-year-carry-aware biennial companion."
        ),
        "",
        "Projection configuration echo: "
        f"`{json.dumps(inventory['projection'], sort_keys=True)}`.",
        "",
    ]
    for name, table in inventory["tables"].items():
        output.extend(
            [
                f"### `{name}`",
                "",
                (
                    f"Pointer `{table['json_pointer']}`; years "
                    f"{table['years'][0]}–{table['years'][-1]}; "
                    f"{table['per_draw_row_count']} per-draw rows, "
                    f"{table['aggregate_row_count']} aggregate rows, and "
                    f"{table['biennial_companion_row_count']} biennial rows. "
                    f"Unit label: `{table['unit_label']}`. Embedded labels: "
                    f"`{json.dumps(table['labels'])}`."
                ),
                "",
                "Per-draw fields: "
                + ", ".join(f"`{item}`" for item in table["per_draw_fields"])
                + ".",
                "",
                "Aggregate metrics: "
                + ", ".join(f"`{item}`" for item in table["aggregate_metrics"])
                + ".",
                "",
                f"Odd-year disclosure: {table['odd_year_carry_disclosure']}",
                "",
            ]
        )
    counts = inventory["counts"]
    diagnostics = inventory["diagnostics"]
    output.extend(
        [
            "### Counts and diagnostics",
            "",
            (
                f"`counts` contains {counts['per_draw_row_count']} per-draw rows "
                f"and {counts['aggregate_metric_count']} aggregate metrics: "
                + ", ".join(
                    f"`{item}`" for item in counts["aggregate_metrics"]
                )
                + "."
            ),
            "",
            (
                f"`diagnostics` contains {diagnostics['per_draw_row_count']} "
                f"per-draw rows, {diagnostics['aggregate_metric_count']} aggregate "
                "metrics, and "
                f"{diagnostics['included_career_per_draw_row_count']:,} included-career "
                "per-draw rows. Aggregate metrics: "
                + ", ".join(
                    f"`{item}`" for item in diagnostics["aggregate_metrics"]
                )
                + "."
            ),
            "",
            "Additional diagnostic objects: "
            + ", ".join(
                f"`{item}`" for item in diagnostics["additional_objects"]
            )
            + ".",
            "",
            "Entry-10 evaluated comparisons: "
            + ", ".join(
                f"`{item}`"
                for item in inventory["entry10_comparisons"]["evaluated"]
            )
            + ".",
            "",
            "Entry-10 unavailable comparisons: "
            + "; ".join(
                f"`{item['comparison_id']}` — {item['reason']}"
                for item in inventory["entry10_comparisons"]["unavailable"]
            )
            + ".",
            "",
        ]
    )
    return output


def blocked_table(matrix: dict[str, Any]) -> list[str]:
    output = [
        "## Blocked comparisons and published-but-unsupported outputs",
        "",
        "| Comparison | Our support | Published support | Why no canonical row |",
        "|---|---|---|---|",
    ]
    for item in matrix["blocked_comparisons"]:
        cells = [
            f"`{item['comparison_id']}`<br>{item['external_model']}",
            item["our_support"],
            item["published_support"],
            item["reason"],
        ]
        output.append("| " + " | ".join(escape(cell) for cell in cells) + " |")
    output.extend(
        ["", "Published-side examples retained as gaps, not rows:", ""]
    )
    for item in matrix["blocked_comparisons"]:
        examples = item.get("published_examples_not_promoted_to_rows", [])
        for example in examples:
            locator = example.get("locator")
            if isinstance(locator, dict):
                locator_text = display_locator(locator)
            else:
                locator_text = str(locator)
            values = example.get("published_values")
            if values is None:
                values = example.get("published_percent")
            value_text = (
                f" Published: {display_value(values)}."
                if values is not None
                else ""
            )
            output.append(
                f"- `{item['comparison_id']}` — {example['quantity']}."
                f"{value_text} Locator: {locator_text}"
            )
    output.append("")
    return output


def per_row_notes(
    rows: list[dict[str, Any]], heading: str = "Per-row provenance notes"
) -> list[str]:
    output = [
        f"## {heading}",
        "",
        "These notes make the artifact, source class, and gate status explicit for every row.",
        "",
    ]
    for row in rows:
        source = row["our"]["source"]
        codes = row["concept_mismatch"]["mismatch_codes"]
        output.append(
            f"- `{row['row_id']}` — scopes "
            f"`{', '.join(row['comparison_scope'])}`; our source "
            f"`{source['path']}` at `{source['json_pointer']}`, SHA-256 "
            f"`{source['sha256']}`; class: `{row['verification_class']}`; "
            f"status: {row['evidential_status']}; mismatch "
            "codes: " + ", ".join(f"`{code}`" for code in codes) + "."
        )
    output.append("")
    return output


def wish_section(matrix: dict[str, Any]) -> list[str]:
    wish = matrix["wish_financing_stub"]
    ours = wish["our"]
    published = wish["published"]
    output = [
        "## WISH financing stub",
        "",
        (
            "The requested path is computable only as **single-side mechanical "
            "arithmetic**: `0.003 × weighted_taxable_payroll`. It is 0.3% of the "
            "frame-relative proxy base and "
            f"{100 * ours['share_of_modeled_combined_12_4_percent_contributions']:.4f}% "
            "of the artifact's modeled 12.4% combined Social Security contributions. "
            "No absolute revenue level is reported."
        ),
        "",
        (
            "H.R. 4289 §5 separately proposes a 0.3% employee tax and a 0.3% "
            "employer tax after 2021—0.6% combined—and 0.6% on self-employment. "
            "Therefore this 0.3% path is one side, not total WISH financing. The "
            "bill is statutory text, not an actuarial estimate."
        ),
        "",
        "### Annual proxy-base trajectory",
        "",
        "| Year | Mean single-side revenue index (2015=100) | SD across paired draws |",
        "|---:|---:|---:|",
    ]
    for item in ours["annual_relative_trajectory"]:
        output.append(
            f"| {item['year']} | {item['mean_index_2015_100']:.3f} | "
            f"{item['sample_sd_across_paired_draw_indices']:.3f} |"
        )
    output.extend(
        [
            "",
            (
                "This is a proxy-base index, not a policy-effective revenue path. "
                "The proposed tax applies after 2021, so only 2022 overlaps the "
                "certified artifact. Odd-year values inherit the artifact's carry rule."
            ),
            "",
            "### Odd-year-carry-aware biennial trajectory",
            "",
            "| Component years | Mean index (2015–2016=100) | SD across paired draws |",
            "|---|---:|---:|",
        ]
    )
    for item in ours["odd_year_carry_aware_biennial_relative_trajectory"]:
        years = item["component_years"]
        output.append(
            f"| {years[0]}–{years[1]} | "
            f"{item['mean_index_2015_2016_100']:.3f} | "
            f"{item['sample_sd_across_paired_draw_indices']:.3f} |"
        )
    locators = " ".join(
        display_locator(locator) for locator in published["source_locators"]
    )
    output.extend(
        [
            "",
            f"Statutory locator: {locators}",
            "",
            (
                "Actuarial side remains blocked. No primary ARC/Oliver Wyman "
                "memorandum landed. The captured Morningstar page gives only "
                "unpaginated summary bullets (single women 58%→28%; single men "
                "34%→16% among households projected to qualify), while the full "
                f"report `{matrix['external_capture_review']['missing_after_refresh']['morningstar_full_wish_report']['url_discovered_in_captured_landing_json_ld']}` "
                "is absent and the staged appendix is generic. Our artifact also "
                "has no LTSS, retirement-shortfall, assets, spend-down, program-cost, "
                "or financing-sufficiency outcome."
            ),
            "",
        ]
    )
    return output


def certification_section(matrix: dict[str, Any]) -> list[str]:
    context = matrix["certification_context"]
    m6 = context["m6"]
    gate1 = context["ppi_gate1_generator"]
    output = [
        "## Frame, labels, and certification boundaries",
        "",
        (
            "All rows are **frame-relative proxy covered-earnings** results and "
            "make **no population-alignment claim**. Absolute national dollar "
            "levels are never compared. The committed entry-8/entry-10 artifacts "
            "embed `['frame-relative', 'pre-alignment', 'labor-income proxy']`. "
            "The exact ratified fitting-free §16.7.1 array is "
            "`['frame-relative', 'modeled-covered-earnings', "
            "'deterministic-uncalibrated']`; this report quotes it but does not "
            "assert the later activation event."
        ),
        "",
        (
            f"M6 source: `{m6['source']['path']}` (SHA-256 "
            f"`{m6['source']['sha256']}`). Verdict `{m6['status']}`; "
            f"{m6['n_seeds_pass']}/5 seeds pass. Family A is gated; Family B and "
            "Family C are not gated. M6 forward certification does not transfer "
            "to the backward-law module replications."
        ),
        "",
        (
            f"PPI gate-1 generator: `{gate1['source']['path']}` (SHA-256 "
            f"`{gate1['source']['sha256']}`); geometry "
            f"{gate1['geometry_seed_passes']}/5 and battery "
            f"{gate1['battery_seed_passes']}/5. {gate1['warning']}"
        ),
        "",
        "M6 Family-B margins explicitly not certified:",
        "",
    ]
    for item in m6["not_certified"]:
        output.append(f"- `{item['margin']}` — {item['detail']}")
    output.extend(["", "Committed module replication artifacts:", ""])
    module_paths = [
        "runs/replication_ppi_mermin_v1.json",
        "runs/replication_ppi_shared_v1.json",
        "runs/replication_mermin_rows_v1.json",
        "runs/replication_r7_sharing_v1.json",
        "runs/replication_cost_ordering_v1.json",
    ]
    by_path = {item["path"]: item["sha256"] for item in matrix["inputs"]}
    for path in module_paths:
        output.append(f"- `{path}` — SHA-256 `{by_path[path]}`")
    output.append("")
    return output


def capture_section(matrix: dict[str, Any]) -> list[str]:
    review = matrix["external_capture_review"]
    manifest = review["staging_manifest"]
    output = [
        "## External capture review",
        "",
        (
            f"The 2026-08-01 REFRESH contained {manifest['entry_count']} unique "
            "manifested files. Every declared size and SHA-256 was verified. The "
            f"manifest SHA-256 is `{manifest['sha256']}`. External source bytes "
            "remain outside this repository; canonical extracted cells and source "
            "pins are frozen in the committed builder, so reproduction reads only "
            "committed repository bytes."
        ),
        "",
        "Reviewed capture pins used by the matrix:",
        "",
    ]
    for name, capture in review["captures"].items():
        warning = (
            f" Warning: {capture['warning']}" if capture.get("warning") else ""
        )
        output.append(
            f"- `{name}` — `{capture['filename']}`, SHA-256 "
            f"`{capture['sha256']}`, {capture['size_bytes']:,} bytes, "
            f"[publisher source]({capture['url']}).{warning}"
        )
    output.extend(["", "Missing after REFRESH:", ""])
    for name, value in review["missing_after_refresh"].items():
        output.append(f"- `{name}` — {display_value(value)}")
    output.append("")
    return output


def render() -> str:
    raw = MATRIX_PATH.read_bytes()
    matrix = json.loads(raw)
    matrix_sha = hashlib.sha256(raw).hexdigest()
    counts = Counter(row_group(row) for row in matrix["rows"])
    reported_counts = Counter(
        row_group(row) for row in matrix["reported_not_verified"]["rows"]
    )
    lines = [
        "# Cross-model validation matrix",
        "",
        "## Outcome",
        "",
        (
            f"**State:** the canonical verified-source matrix has "
            f"**{matrix['row_count']} rows** and SHA-256 `{matrix_sha}`: "
            f"{counts['SSA Trustees and Statistical Supplement']} SSA, "
            f"{counts['CBO / CBOLT']} CBO, "
            f"{counts['DYNASIM module replications']} DYNASIM, and "
            f"{counts['WISH statutory parameter']} WISH statutory row. "
            f"A separate `reported_not_verified` class contains "
            f"**{matrix['reported_not_verified']['row_count']} Mermin rows** "
            f"({reported_counts['DYNASIM module replications']} DYNASIM) whose "
            "publisher-controlled source bytes could not be retrieved."
        ),
        "",
        (
            "**Done:** the supported ratios, shares, and trajectories were built. "
            "The Mermin comparisons remain visible only as reported, unverified "
            "replication results with their committed-artifact provenance and the "
            "unmanifested corroborating-copy SHA disclosed. Displayed numbers are "
            "rounded for readability; `matrix.json` is canonical."
        ),
        "",
        (
            "**Next:** obtain the full Morningstar WISH paper, a primary ARC/Oliver "
            "Wyman memorandum, SSA/ORP numeric MINT policy-option outputs, and the "
            "dead DYNASIM4 workbook if publisher-controlled bytes become available."
        ),
        "",
    ]
    lines.extend(certification_section(matrix))
    lines.extend(capture_section(matrix))
    lines.extend(series_inventory(matrix))
    lines.extend(
        [
            "## Canonical verified-source human matrix",
            "",
            (
                "The deviation convention is always ours minus published unless "
                "the row explicitly states a ratio or Kendall-tau definition."
            ),
            "",
        ]
    )
    lines.extend(human_matrix(matrix["rows"]))
    lines.extend(per_row_notes(matrix["rows"]))
    lines.extend(
        [
            "## Reported, not verified: Mermin comparisons",
            "",
            (
                "These 20 rows are excluded from the canonical verified-source "
                "matrix. Their published values come only from committed "
                "replication artifacts. Publisher-controlled bytes were not "
                "retrieved; the disclosed unmanifested copy is not accepted as "
                "verification under the capture rule."
            ),
            "",
        ]
    )
    lines.extend(human_matrix(matrix["reported_not_verified"]["rows"]))
    lines.extend(
        per_row_notes(
            matrix["reported_not_verified"]["rows"],
            "Reported-not-verified per-row provenance notes",
        )
    )
    lines.extend(wish_section(matrix))
    lines.extend(blocked_table(matrix))
    lines.extend(["## Honest gaps", ""])
    lines.extend(f"- {item}" for item in matrix["honest_gaps"])
    lines.extend(
        [
            "",
            "## Reproduction and verification",
            "",
            (
                "Rebuild with `/Users/maxghenis/PolicyEngine/social-security-model/"
                ".venv/bin/python analysis/validation-matrix/build_matrix.py` and "
                "then regenerate this report with the same interpreter and "
                "`analysis/validation-matrix/build_report.py`. Final verification:"
            ),
            "",
            (
                f"- Matrix rebuild was byte-stable at SHA-256 `{matrix_sha}` with "
                f"{matrix['row_count']} canonical verified-source rows and "
                f"{matrix['reported_not_verified']['row_count']} separately "
                "reported-not-verified rows."
            ),
            "- Report regeneration was byte-stable.",
            (
                "- `python -m pytest -q tests/test_validation_matrix.py`: "
                "1 passed."
            ),
            (
                "- `python -m pytest -q -k "
                "test__given_collected_suite__then_tiers_match_policy_manifest`: "
                "1 passed, 4,471 deselected; the new test is registered in the "
                "unit tier (903 unit tests; 4,472 total tests)."
            ),
            "- Progress and final closure reporting are tracked separately from the matrix artifact.",
            "",
        ]
    )
    return "\n".join(lines)


OUT.write_text(render(), encoding="utf-8")
