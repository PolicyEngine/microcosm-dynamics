#!/usr/bin/env python3
"""Author the candidate-free source review for R_Q document 30.

All 56 physical pages of q82.pdf were reviewed against the authenticated
Poppler page bytes.  This helper records only source-visible employment,
work-income, and limited work-history atoms.  It never opens the stage-1
candidate artifact; the sealed annotation builder performs that provenance
join only after this source ledger has been built and validated.
"""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import build_rq_stage2_document_030_annotation as annotation

ROOT = Path(__file__).resolve().parents[1]

F = "flow_branch_label"
R = "role_anchor"
J = "job_anchor"
M = "remuneration_component_anchor"
T = "role_total_anchor"
FA = "farm_aggregate_anchor"
BA = "business_aggregate_anchor"
C = "context_anchor"
P = "field_purpose_prompt"
A = "repeat_or_alias_instruction"

SEMANTIC_PAGE_NOTES = {
    7: "Head current-employment entry and assignment.",
    8: "Head current-job occupation, industry, and pay.",
    9: "Head current and immediately prior job context.",
    10: "Head annual work exposure and main-job hours.",
    11: "Head overtime and extra-job block.",
    12: "Head first and second unemployment-spell exposure.",
    13: "Head second and third unemployment-spell exposure.",
    14: "Head return-to-employer, job, and wage cross-references.",
    17: "Head looking-for-work and last-job context.",
    18: "Head last-job annual exposure.",
    19: "Head last-job unemployment-spell exposure.",
    20: "Head last-job unemployment-spell continuation.",
    21: "Head last-job return cross-references.",
    23: "Head prior-year work while otherwise out of labor force.",
    24: "Spouse employment entry and assignment.",
    25: "Spouse current-job occupation, pay, and prior-job context.",
    26: "Spouse annual work exposure and main-job hours.",
    27: "Spouse overtime and extra-job block.",
    28: "Spouse last-job context.",
    29: "Spouse last-job annual exposure.",
    30: "Spouse prior-year work while otherwise out of labor force.",
    33: "Farm and business work-income aggregates.",
    34: "Head wage, salary, other work-income, and hours reconciliation.",
    37: "Spouse earned-income entry and total.",
    48: "Wife/friend role-equivalence checkpoint instruction.",
    49: "New-spouse entry routing.",
    50: "New-spouse lifetime work exposure.",
    51: "New-head first regular job.",
    52: "New-head occupation pattern.",
    54: "New-head lifetime work exposure.",
}


def _review_id(
    source_document_id: str,
    page_texts: Sequence[str],
    page_number: int,
    start: int,
    end: int,
    kind: str,
) -> str:
    matched = page_texts[page_number - 1].encode("utf-8")[start:end]
    if not matched:
        raise ValueError("empty reviewer span")
    matched.decode("utf-8", errors="strict")
    return "rq-review-occurrence:" + annotation._canonical_digest(
        [
            source_document_id,
            page_number,
            start,
            end,
            kind,
            annotation._sha256(matched),
        ]
    )


def author_review() -> dict[str, Any]:
    replay, index = annotation._source_replay_and_index()
    document, _identity = annotation._document_identity(replay, index)
    page_texts = annotation._extract_page_texts(document, replay)
    source_document_id = document["source_document_id"]

    def trim(page: int, start: int, end: int) -> tuple[int, int]:
        raw = page_texts[page - 1].encode("utf-8")
        while start < end and raw[start : start + 1] in b" \t\r\n":
            start += 1
        while start < end and raw[end - 1 : end] in b" \t\r\n":
            end -= 1
        if not 0 <= start < end <= len(raw):
            raise ValueError(f"invalid reviewed span on page {page}")
        raw[start:end].decode("utf-8", errors="strict")
        return start, end

    def needle(
        page: int, text: str, ordinal: int | None = None
    ) -> tuple[int, int]:
        raw = page_texts[page - 1].encode("utf-8")
        target = text.encode("utf-8")
        positions: list[int] = []
        cursor = 0
        while True:
            found = raw.find(target, cursor)
            if found < 0:
                break
            positions.append(found)
            cursor = found + 1
        if not positions:
            raise ValueError(f"needle absent on page {page}: {text!r}")
        if ordinal is None:
            if len(positions) != 1:
                raise ValueError(
                    f"needle is not unique on page {page}: {text!r}"
                )
            ordinal = 0
        if not 0 <= ordinal < len(positions):
            raise ValueError(f"needle ordinal drift on page {page}: {text!r}")
        start = positions[ordinal]
        return start, start + len(target)

    def block(
        page: int,
        start_text: str,
        end_text: str,
        start_ordinal: int | None = None,
    ) -> tuple[int, int]:
        start, _ = needle(page, start_text, start_ordinal)
        raw = page_texts[page - 1].encode("utf-8")
        end_target = end_text.encode("utf-8")
        end_start = raw.find(end_target, start)
        if end_start < 0:
            raise ValueError(
                f"block end absent after start on page {page}: {end_text!r}"
            )
        return trim(page, start, end_start + len(end_target))

    def line(
        page: int, marker: str, ordinal: int | None = None
    ) -> tuple[int, int]:
        marker_start, _ = needle(page, marker, ordinal)
        raw = page_texts[page - 1].encode("utf-8")
        start = raw.rfind(b"\n", 0, marker_start) + 1
        end = raw.find(b"\n", marker_start)
        if end < 0:
            end = len(raw)
        return trim(page, start, end)

    def lines(
        page: int,
        start_marker: str,
        end_marker: str,
        start_ordinal: int | None = None,
        end_ordinal: int | None = None,
    ) -> tuple[int, int]:
        start_marker_byte, _ = needle(page, start_marker, start_ordinal)
        end_marker_byte, _ = needle(page, end_marker, end_ordinal)
        if end_marker_byte < start_marker_byte:
            raise ValueError(
                f"line block reverses source order on page {page}"
            )
        raw = page_texts[page - 1].encode("utf-8")
        start = raw.rfind(b"\n", 0, start_marker_byte) + 1
        end = raw.find(b"\n", end_marker_byte)
        if end < 0:
            end = len(raw)
        return trim(page, start, end)

    def physical(
        page: int, first_line: int, last_line: int | None = None
    ) -> tuple[int, int]:
        """Return an exact trimmed span by one-based Poppler physical lines."""

        if last_line is None:
            last_line = first_line
        raw = page_texts[page - 1].encode("utf-8")
        rows = raw.splitlines(keepends=True)
        if not 1 <= first_line <= last_line <= len(rows):
            raise ValueError(f"physical line range drift on page {page}")
        start = sum(len(row) for row in rows[: first_line - 1])
        end = sum(len(row) for row in rows[:last_line])
        while end > start and raw[end - 1 : end] in b"\r\n":
            end -= 1
        return trim(page, start, end)

    specs: dict[str, dict[str, Any]] = {}

    def add(
        key: str,
        page: int,
        span: tuple[int, int],
        kind: str,
        *,
        branches: Sequence[Sequence[str]] = ((),),
        parents: Sequence[str] = (),
        note: str = "Exact source atom retained after whole-page review.",
    ) -> None:
        if key in specs:
            raise ValueError(f"duplicate review key: {key}")
        start, end = trim(page, *span)
        specs[key] = {
            "key": key,
            "page": page,
            "start": start,
            "end": end,
            "kind": kind,
            "branches": tuple(tuple(path) for path in branches),
            "parents": tuple(parents),
            "note": note,
        }

    def question(
        key: str,
        page: int,
        span: tuple[int, int],
        *,
        branches: Sequence[Sequence[str]] = ((),),
        context: bool = False,
        context_parents: Sequence[str] = (),
        note: str = "Complete printed prompt retained for a covered purpose.",
    ) -> None:
        add(key + "_purpose", page, span, P, branches=branches, note=note)
        if context:
            add(
                key + "_context",
                page,
                span,
                C,
                branches=branches,
                parents=context_parents,
                note="Prompt also establishes a document-local work context.",
            )

    def flow(
        key: str,
        page: int,
        span: tuple[int, int],
        *,
        parents: Sequence[Sequence[str]] = ((),),
    ) -> None:
        add(
            key,
            page,
            span,
            F,
            branches=parents,
            note="Exact source-visible routing label with reviewed ancestry.",
        )

    def anchor(
        key: str,
        page: int,
        span: tuple[int, int],
        kind: str,
        *,
        branches: Sequence[Sequence[str]] = ((),),
        parents: Sequence[str] = (),
    ) -> None:
        add(
            key,
            page,
            span,
            kind,
            branches=branches,
            parents=parents,
            note="Exact source anchor classified only within this document.",
        )

    def repeat(
        key: str,
        page: int,
        span: tuple[int, int],
        *,
        branches: Sequence[Sequence[str]] = ((),),
        relation: str,
        alias_keys: Sequence[str] = (),
        canonical_keys: Sequence[str] = (),
        evidence_keys: Sequence[str],
        target_scope: str = "unresolved",
        resolution_status: str = "preserved_for_global_resolution",
    ) -> None:
        add(
            key,
            page,
            span,
            A,
            branches=branches,
            note="Exact printed repeat or cross-reference retained.",
        )
        specs[key]["relation"] = relation
        specs[key]["repeat"] = (
            tuple(alias_keys),
            tuple(canonical_keys),
            tuple(evidence_keys),
            target_scope,
            resolution_status,
        )

    # Section C: head currently working.  Routes are retained only when they
    # govern a covered employment atom; response values that merely skip
    # nonemployment material are outside this document-local hierarchy.
    flow("d_route", 7, physical(7, 16, 17))
    flow("e_route", 7, physical(7, 19, 20))
    flow("c_has_job", 7, needle(7, "GO TO C2 IF HEAD HAS JOB"))
    flow("e_otherwise", 7, needle(7, "OTHERWISE TURN TO P. 21, SECTION E"))
    c_path = (("c_has_job",),)
    d_path = (("d_route",),)
    e_path = (("e_route",), ("e_otherwise",))
    flow(
        "c2_someone",
        7,
        needle(7, "11.     SOMEONE ELSE"),
        parents=c_path,
    )
    flow(
        "c2_both",
        7,
        needle(7, "2.    BOTH SOMEONE ELSE AND SELF"),
        parents=c_path,
    )
    flow(
        "c2_self",
        7,
        needle(7, "3. SELF ONLY"),
        parents=c_path,
    )
    c_someone_paths = (
        ("c_has_job", "c2_someone"),
        ("c_has_job", "c2_both"),
    )
    anchor("c_head_role", 7, needle(7, "(HEAD)"), R)
    anchor(
        "c_section_context",
        7,
        needle(7, "SECTION C:           EMPLOYMENT OF HEAD"),
        C,
    )
    question("c1_assignment", 7, physical(7, 6, 7), context=True)
    question(
        "c2_employee_self",
        7,
        physical(7, 31, 33),
        branches=c_path,
        context=True,
    )
    anchor(
        "c_current_job",
        7,
        needle(7, "current             job"),
        J,
        branches=c_someone_paths,
    )
    question(
        "c3_government",
        7,
        physical(7, 43, 44),
        branches=c_someone_paths,
        context=True,
        context_parents=("c_current_job",),
    )
    anchor(
        "c_present_employer",
        7,
        needle(7, "present       employer"),
        J,
        branches=c_someone_paths,
    )
    question(
        "c6_employer_duration",
        7,
        physical(7, 60, 62),
        branches=c_someone_paths,
        context=True,
        context_parents=("c_present_employer",),
    )

    # Current-job occupation and pay.  The three-column pay grid is sliced
    # into its independent source-visible prompts rather than treated as one
    # normalized sentence.
    anchor("c_main_job", 8, needle(8, "main     job"), J, branches=c_path)
    question(
        "c7_occupation",
        8,
        physical(8, 3),
        branches=c_path,
        context=True,
        context_parents=("c_main_job",),
    )
    question(
        "c8_duties",
        8,
        physical(8, 9),
        branches=c_path,
        context=True,
        context_parents=("c_main_job",),
    )
    question(
        "c9_industry",
        8,
        physical(8, 14),
        branches=c_path,
        context=True,
        context_parents=("c_main_job",),
    )
    question(
        "c10_pay_method",
        8,
        physical(8, 19),
        branches=c_path,
        context=True,
        context_parents=("c_main_job",),
    )
    flow("c_pay_salary", 8, needle(8, "1. SALARIED"), parents=c_path)
    flow("c_pay_hourly", 8, needle(8, "3. PAID BY HOUR"), parents=c_path)
    flow("c_pay_other", 8, needle(8, "7. OTHER"), parents=c_path)
    salary_path = (("c_has_job", "c_pay_salary"),)
    hourly_path = (("c_has_job", "c_pay_hourly"),)
    other_pay_path = (("c_has_job", "c_pay_other"),)
    anchor(
        "c_salary_component",
        8,
        needle(8, "SALARIED"),
        M,
        branches=salary_path,
        parents=("c_main_job",),
    )
    anchor(
        "c_hourly_component",
        8,
        needle(8, "PAID BY HOUR"),
        M,
        branches=hourly_path,
        parents=("c_main_job",),
    )
    anchor(
        "c_other_pay_component",
        8,
        needle(8, "OTHER"),
        M,
        branches=other_pay_path,
        parents=("c_main_job",),
    )
    question(
        "c11_salary_amount",
        8,
        needle(8, "C11. How much is your salary?"),
        branches=salary_path,
    )
    question(
        "c12_extra_hours",
        8,
        lines(8, "If you were to work more", "hours of work?"),
        branches=salary_path,
        context=True,
        context_parents=("c_main_job",),
    )
    anchor(
        "c_extra_hours_component",
        8,
        needle(8, "those extra"),
        M,
        branches=salary_path,
        parents=("c_main_job",),
    )
    question(
        "c13_extra_hour_pay",
        8,
        lines(8, "About how much would you", "extra hours?"),
        branches=salary_path,
    )
    anchor(
        "c_regular_hourly_rate",
        8,
        needle(8, "hourly wage", 0),
        M,
        branches=hourly_path,
        parents=("c_main_job",),
    )
    question(
        "c14_regular_hourly_rate",
        8,
        needle(8, "What isyour hourly wage"),
        branches=hourly_path,
    )
    anchor(
        "c_overtime_rate",
        8,
        needle(8, "hourly wage", 1),
        M,
        branches=hourly_path,
        parents=("c_main_job",),
    )
    question(
        "c15_overtime_rate",
        8,
        lines(8, "What is your hourly wage", "rate for overtime?"),
        branches=hourly_path,
    )
    question(
        "c16_other_pay_unit",
        8,
        needle(8, "How isisthat?"),
        branches=other_pay_path,
    )
    question(
        "c17_other_pay_amount",
        8,
        block(8, "C17. If you worked an extra", "urn   for that hour’"),
        branches=other_pay_path,
    )

    anchor(
        "c_present_position",
        9,
        needle(9, "present       position"),
        J,
        branches=c_path,
    )
    question(
        "c18_position_duration",
        9,
        physical(9, 6),
        branches=c_path,
        context=True,
        context_parents=("c_present_position",),
    )
    flow("c19_less", 9, physical(9, 17), parents=c_path)
    prior_path = (("c_has_job", "c19_less"),)
    anchor(
        "c_prior_job",
        9,
        needle(9, "the job you had before"),
        J,
        branches=prior_path,
    )
    question(
        "c20_prior_job_exit",
        9,
        physical(9, 20, 21),
        branches=prior_path,
        context=True,
        context_parents=("c_prior_job",),
    )
    anchor(
        "c_present_job_reference",
        9,
        needle(9, "present     job"),
        J,
        branches=prior_path,
    )
    question(
        "c21_present_prior_assignment",
        9,
        physical(9, 32, 35),
        branches=prior_path,
        context=True,
        context_parents=("c_present_job_reference",),
    )

    # Annual work exposure.  C22 and the C28/C29 printed prose are absent
    # from the authenticated text extraction, so no visual-only atoms are
    # invented for them.
    question(
        "c23_family_sick_amount",
        10,
        physical(10, 6),
        branches=c_path,
        context=True,
        context_parents=("c_main_job",),
    )
    flow("c24_yes", 10, physical(10, 10), parents=c_path)
    c24_path = (("c_has_job", "c24_yes"),)
    question(
        "c24_own_sick",
        10,
        physical(10, 10),
        branches=c_path,
        context=True,
        context_parents=("c_main_job",),
    )
    question(
        "c25_own_sick_amount",
        10,
        physical(10, 15),
        branches=c24_path,
        context=True,
        context_parents=("c_main_job",),
    )
    question(
        "c26_vacation",
        10,
        physical(10, 19),
        branches=c_path,
        context=True,
        context_parents=("c_main_job",),
    )
    flow("c30_yes", 10, physical(10, 33, 34), parents=c_path)
    c30_path = (("c_has_job", "c30_yes"),)
    question(
        "c30_unemployed",
        10,
        physical(10, 33, 34),
        branches=c_path,
        context=True,
        context_parents=("c_main_job",),
    )
    question(
        "c31_unemployed_amount",
        10,
        physical(10, 40),
        branches=c30_path,
        context=True,
        context_parents=("c_main_job",),
    )
    question(
        "c32_weeks_worked",
        10,
        physical(10, 44),
        branches=c_path,
        context=True,
        context_parents=("c_main_job",),
    )
    question(
        "c33_main_job_hours",
        10,
        physical(10, 49, 50),
        branches=c_path,
        context=True,
        context_parents=("c_main_job",),
    )

    flow("c34_yes", 11, physical(11, 3), parents=c_path)
    c34_path = (("c_has_job", "c34_yes"),)
    anchor(
        "c_overtime_component",
        11,
        needle(11, "overtime", 0),
        M,
        branches=c_path,
        parents=("c_main_job",),
    )
    question(
        "c34_overtime",
        11,
        physical(11, 3),
        branches=c_path,
        context=True,
        context_parents=("c_main_job",),
    )
    question(
        "c35_overtime_hours",
        11,
        physical(11, 9),
        branches=c34_path,
        context=True,
        context_parents=("c_main_job",),
    )
    flow("c36_yes", 11, physical(11, 14, 15), parents=c_path)
    c36_path = (("c_has_job", "c36_yes"),)
    anchor(
        "c_extra_jobs",
        11,
        needle(11, "extra jobs"),
        J,
        branches=c_path,
    )
    question(
        "c36_extra_jobs",
        11,
        physical(11, 14, 15),
        branches=c_path,
        context=True,
        context_parents=("c_extra_jobs",),
    )
    question(
        "c37_extra_job_occupation",
        11,
        physical(11, 21),
        branches=c36_path,
        context=True,
        context_parents=("c_extra_jobs",),
    )
    question(
        "c38_extra_job_count",
        11,
        physical(11, 26),
        branches=c36_path,
        context=True,
        context_parents=("c_extra_jobs",),
    )
    anchor(
        "c_extra_job_hourly_pay",
        11,
        needle(11, "much did            you make per         hour"),
        M,
        branches=c36_path,
        parents=("c_extra_jobs",),
    )
    question(
        "c39_extra_job_pay",
        11,
        physical(11, 30),
        branches=c36_path,
    )
    question(
        "c40_extra_job_weeks",
        11,
        physical(11, 34),
        branches=c36_path,
        context=True,
        context_parents=("c_extra_jobs",),
    )
    question(
        "c41_extra_job_hours",
        11,
        physical(11, 38),
        branches=c36_path,
        context=True,
        context_parents=("c_extra_jobs",),
    )
    repeat(
        "c42_see_c31",
        11,
        physical(11, 43),
        branches=c_path,
        relation="explicit_cross_reference",
        evidence_keys=(
            "c31_unemployed_amount_context",
            "c42_see_c31",
        ),
        target_scope="document_local",
    )
    flow("c42_unemp", 11, physical(11, 45, 46), parents=c_path)
    c_unemp_path = (("c_has_job", "c42_unemp"),)

    question(
        "c43_first_unemployment",
        12,
        physical(12, 4, 7),
        branches=c_unemp_path,
        context=True,
    )
    question(
        "c44_first_unemployment_weeks",
        12,
        physical(12, 12),
        branches=c_unemp_path,
        context=True,
    )
    repeat(
        "c49_see_c43",
        12,
        physical(12, 38),
        branches=c_unemp_path,
        relation="explicit_cross_reference",
        evidence_keys=(
            "c43_first_unemployment_context",
            "c49_see_c43",
        ),
        target_scope="document_local",
    )
    flow("c49_1981", 12, physical(12, 40), parents=c_unemp_path)
    c49_path = (("c_has_job", "c42_unemp", "c49_1981"),)
    flow("c50_more", 12, physical(12, 45, 46), parents=c49_path)
    c50_path = (("c_has_job", "c42_unemp", "c49_1981", "c50_more"),)
    question(
        "c50_second_unemployment",
        12,
        physical(12, 45, 46),
        branches=c49_path,
        context=True,
    )
    question(
        "c51_second_unemployment_start",
        12,
        physical(12, 51),
        branches=c50_path,
        context=True,
    )
    question(
        "c52_second_unemployment_weeks",
        13,
        physical(13, 3),
        branches=c50_path,
        context=True,
    )
    flow("c57_more", 13, physical(13, 37, 47), parents=c50_path)
    c57_path = (
        ("c_has_job", "c42_unemp", "c49_1981", "c50_more", "c57_more"),
    )
    question(
        "c57_third_unemployment",
        13,
        physical(13, 37, 47),
        branches=c50_path,
        context=True,
    )
    question(
        "c58_third_unemployment_start",
        13,
        physical(13, 51, 54),
        branches=c57_path,
        context=True,
    )

    anchor(
        "c71_same_employer",
        14,
        needle(14, "same employer"),
        J,
        branches=c_unemp_path,
    )
    question(
        "c71_return_employer",
        14,
        physical(14, 45, 46),
        branches=c_unemp_path,
        context=True,
        context_parents=("c71_same_employer",),
    )
    repeat(
        "c71_crossref",
        14,
        physical(14, 45, 46),
        branches=c_unemp_path,
        relation="explicit_cross_reference",
        alias_keys=("c71_same_employer",),
        evidence_keys=("c71_crossref", "c71_same_employer"),
    )
    anchor(
        "c72_same_job",
        14,
        needle(14, "same type        of     job"),
        J,
        branches=c_unemp_path,
    )
    question(
        "c72_return_job",
        14,
        physical(14, 52),
        branches=c_unemp_path,
        context=True,
        context_parents=("c72_same_job",),
    )
    repeat(
        "c72_crossref",
        14,
        physical(14, 52),
        branches=c_unemp_path,
        relation="explicit_cross_reference",
        alias_keys=("c72_same_job",),
        evidence_keys=("c72_crossref", "c72_same_job"),
    )
    anchor(
        "c73_wage_rate",
        14,
        needle(14, "Wage rate"),
        M,
        branches=c_unemp_path,
        parents=("c72_same_job",),
    )
    question(
        "c73_return_wage",
        14,
        physical(14, 58, 59),
        branches=c_unemp_path,
    )
    repeat(
        "c73_crossref",
        14,
        physical(14, 58, 59),
        branches=c_unemp_path,
        relation="explicit_cross_reference",
        alias_keys=("c73_wage_rate",),
        evidence_keys=("c73_crossref", "c73_wage_rate"),
    )

    # Section D: head looking for work.  D1-D6 are prospective search prose;
    # the retained hierarchy begins only when the source establishes a prior
    # job and its actual 1981 work exposure.
    anchor(
        "d_head_role",
        17,
        needle(17, "HEAD LOOKING FOR WORK"),
        R,
        branches=d_path,
    )
    anchor(
        "d_section_context",
        17,
        physical(17, 3),
        C,
        branches=d_path,
    )
    flow("d7_ever_job", 17, physical(17, 32), parents=d_path)
    d_job_path = (("d_route", "d7_ever_job"),)
    question(
        "d7_ever_job",
        17,
        physical(17, 32),
        branches=d_path,
        context=True,
    )
    anchor(
        "d_last_job",
        17,
        needle(17, "last      job"),
        J,
        branches=d_job_path,
    )
    question(
        "d8_last_job_occupation",
        17,
        physical(17, 44),
        branches=d_job_path,
        context=True,
        context_parents=("d_last_job",),
    )
    question(
        "d9_last_job_industry",
        17,
        physical(17, 51),
        branches=d_job_path,
        context=True,
        context_parents=("d_last_job",),
    )
    question(
        "d10_last_job_exit",
        17,
        physical(17, 54, 55),
        branches=d_job_path,
        context=True,
        context_parents=("d_last_job",),
    )
    question(
        "d11_last_worked",
        17,
        physical(17, 59),
        branches=d_job_path,
        context=True,
        context_parents=("d_last_job",),
    )

    flow("d12_yes", 18, physical(18, 3, 5), parents=d_job_path)
    d12_path = (("d_route", "d7_ever_job", "d12_yes"),)
    question(
        "d12_vacation",
        18,
        physical(18, 3, 5),
        branches=d_job_path,
        context=True,
        context_parents=("d_last_job",),
    )
    question(
        "d13_vacation_amount",
        18,
        physical(18, 10),
        branches=d12_path,
        context=True,
        context_parents=("d_last_job",),
    )
    flow("d14_yes", 18, physical(18, 14), parents=d_job_path)
    d14_path = (("d_route", "d7_ever_job", "d14_yes"),)
    question(
        "d14_family_sick",
        18,
        physical(18, 14),
        branches=d_job_path,
        context=True,
        context_parents=("d_last_job",),
    )
    question(
        "d15_family_sick_amount",
        18,
        physical(18, 21),
        branches=d14_path,
        context=True,
        context_parents=("d_last_job",),
    )
    flow("d16_yes", 18, physical(18, 24), parents=d_job_path)
    d16_path = (("d_route", "d7_ever_job", "d16_yes"),)
    question(
        "d16_own_sick",
        18,
        physical(18, 24),
        branches=d_job_path,
        context=True,
        context_parents=("d_last_job",),
    )
    question(
        "d17_own_sick_amount",
        18,
        physical(18, 28),
        branches=d16_path,
        context=True,
        context_parents=("d_last_job",),
    )
    question(
        "d18_strike",
        18,
        physical(18, 32),
        branches=d_job_path,
        context=True,
        context_parents=("d_last_job",),
    )
    flow("d20_yes", 18, physical(18, 41, 42), parents=d_job_path)
    d20_path = (("d_route", "d7_ever_job", "d20_yes"),)
    question(
        "d20_unemployed",
        18,
        physical(18, 41, 42),
        branches=d_job_path,
        context=True,
        context_parents=("d_last_job",),
    )
    question(
        "d21_unemployed_amount",
        18,
        physical(18, 48),
        branches=d20_path,
        context=True,
        context_parents=("d_last_job",),
    )
    anchor(
        "d_actual_job",
        18,
        needle(18, "your job"),
        J,
        branches=d_job_path,
    )
    question(
        "d22_weeks_worked",
        18,
        physical(18, 52),
        branches=d_job_path,
        context=True,
        context_parents=("d_actual_job",),
    )
    question(
        "d23_hours_worked",
        18,
        physical(18, 57, 58),
        branches=d_job_path,
        context=True,
        context_parents=("d_actual_job",),
    )

    repeat(
        "d24_see_d21",
        19,
        physical(19, 3),
        branches=d_job_path,
        relation="explicit_cross_reference",
        evidence_keys=(
            "d21_unemployed_amount_context",
            "d24_see_d21",
        ),
        target_scope="document_local",
    )
    flow("d24_unemp", 19, physical(19, 4, 6), parents=d_job_path)
    d_unemp_path = (("d_route", "d7_ever_job", "d24_unemp"),)
    question(
        "d25_first_unemployment",
        19,
        physical(19, 10, 12),
        branches=d_unemp_path,
        context=True,
    )
    question(
        "d26_first_unemployment_weeks",
        19,
        physical(19, 18),
        branches=d_unemp_path,
        context=True,
    )
    repeat(
        "d31_see_d25",
        19,
        physical(19, 52),
        branches=d_unemp_path,
        relation="explicit_cross_reference",
        evidence_keys=(
            "d25_first_unemployment_context",
            "d31_see_d25",
        ),
        target_scope="document_local",
    )
    flow("d31_1981", 19, physical(19, 54), parents=d_unemp_path)
    d31_path = (("d_route", "d7_ever_job", "d24_unemp", "d31_1981"),)
    flow("d32_more", 19, physical(19, 57), parents=d31_path)
    d32_path = (
        ("d_route", "d7_ever_job", "d24_unemp", "d31_1981", "d32_more"),
    )
    question(
        "d32_second_unemployment",
        19,
        physical(19, 57),
        branches=d31_path,
        context=True,
    )
    question(
        "d33_second_unemployment_start",
        19,
        physical(19, 62),
        branches=d32_path,
        context=True,
    )
    question(
        "d34_second_unemployment_weeks",
        20,
        physical(20, 5),
        branches=d32_path,
        context=True,
    )
    flow("d39_more", 20, physical(20, 37), parents=d32_path)
    d39_path = (
        (
            "d_route",
            "d7_ever_job",
            "d24_unemp",
            "d31_1981",
            "d32_more",
            "d39_more",
        ),
    )
    question(
        "d39_third_unemployment",
        20,
        physical(20, 37),
        branches=d32_path,
        context=True,
    )
    question(
        "d40_third_unemployment_start",
        20,
        physical(20, 43),
        branches=d39_path,
        context=True,
    )
    question(
        "d41_third_unemployment_weeks",
        20,
        physical(20, 49),
        branches=d39_path,
        context=True,
    )

    anchor(
        "d53_same_employer",
        21,
        needle(21, "same employer"),
        J,
        branches=d_unemp_path,
    )
    question(
        "d53_return_employer",
        21,
        physical(21, 36, 37),
        branches=d_unemp_path,
        context=True,
        context_parents=("d53_same_employer",),
    )
    repeat(
        "d53_crossref",
        21,
        physical(21, 36, 37),
        branches=d_unemp_path,
        relation="explicit_cross_reference",
        alias_keys=("d53_same_employer",),
        evidence_keys=("d53_crossref", "d53_same_employer"),
    )
    anchor(
        "d54_same_job",
        21,
        needle(21, "same type        of job"),
        J,
        branches=d_unemp_path,
    )
    question(
        "d54_return_job",
        21,
        physical(21, 42),
        branches=d_unemp_path,
        context=True,
        context_parents=("d54_same_job",),
    )
    repeat(
        "d54_crossref",
        21,
        physical(21, 42),
        branches=d_unemp_path,
        relation="explicit_cross_reference",
        alias_keys=("d54_same_job",),
        evidence_keys=("d54_crossref", "d54_same_job"),
    )
    anchor(
        "d55_wage_rate",
        21,
        needle(21, "wage rate"),
        M,
        branches=d_unemp_path,
        parents=("d54_same_job",),
    )
    question(
        "d55_return_wage",
        21,
        physical(21, 48, 49),
        branches=d_unemp_path,
    )
    repeat(
        "d55_crossref",
        21,
        physical(21, 48, 49),
        branches=d_unemp_path,
        relation="explicit_cross_reference",
        alias_keys=("d55_wage_rate",),
        evidence_keys=("d55_crossref", "d55_wage_rate"),
    )

    # Section E: actual work while otherwise retired/out of the labor force.
    anchor(
        "e_head_role",
        23,
        needle(23, "HEAD IS RETIRED", 0),
        R,
        branches=e_path,
    )
    anchor("e_section_context", 23, physical(23, 1), C, branches=e_path)
    flow("e3_yes", 23, physical(23, 8), parents=e_path)
    e_work_paths = (
        ("e_route", "e3_yes"),
        ("e_otherwise", "e3_yes"),
    )
    anchor(
        "e_work_for_money",
        23,
        needle(23, "work for money"),
        J,
        branches=e_path,
    )
    question(
        "e3_worked",
        23,
        physical(23, 8),
        branches=e_path,
        context=True,
        context_parents=("e_work_for_money",),
    )
    question(
        "e4_occupation",
        23,
        physical(23, 12),
        branches=e_work_paths,
        context=True,
        context_parents=("e_work_for_money",),
    )
    question(
        "e5_industry",
        23,
        physical(23, 15),
        branches=e_work_paths,
        context=True,
        context_parents=("e_work_for_money",),
    )
    question(
        "e6_weeks",
        23,
        physical(23, 20),
        branches=e_work_paths,
        context=True,
        context_parents=("e_work_for_money",),
    )
    question(
        "e7_hours",
        23,
        physical(23, 22),
        branches=e_work_paths,
        context=True,
        context_parents=("e_work_for_money",),
    )
    flow("e8_no", 23, physical(23, 24), parents=e_work_paths)
    e_exit_paths = (
        ("e_route", "e3_yes", "e8_no"),
        ("e_otherwise", "e3_yes", "e8_no"),
    )
    question(
        "e8_still_working",
        23,
        physical(23, 24),
        branches=e_work_paths,
        context=True,
        context_parents=("e_work_for_money",),
    )
    question(
        "e9_job_exit",
        23,
        physical(23, 26),
        branches=e_exit_paths,
        context=True,
        context_parents=("e_work_for_money",),
    )

    # Sections F-H: spouse/friend employment.  Q82 has no extracted Section-G
    # route label, so G descendants use only the source-visible wife-in-FU
    # ancestry plus their own G5 gate.
    flow("f_wife_in_fu", 24, physical(24, 5, 6))
    flow("f_no_wife", 24, physical(24, 8, 10))
    flow("f_head_female", 24, physical(24, 12))
    f_wife_path = (("f_wife_in_fu",),)
    repeat(
        "f1_wife_definition",
        24,
        block(24, "(REMEMBER:", "CONSIDERED WIFE)"),
        branches=f_wife_path,
        relation="explicit_repeat_instruction",
        evidence_keys=("f1_wife_definition",),
        target_scope="document_local",
    )
    anchor(
        "f_section_context",
        24,
        physical(24, 2),
        C,
        branches=f_wife_path,
    )
    anchor(
        "f_wife_role",
        24,
        needle(24, "(wife/friend)", 0),
        R,
        branches=f_wife_path,
    )
    question(
        "f2_assignment",
        24,
        physical(24, 14, 15),
        branches=f_wife_path,
        context=True,
    )
    flow(
        "f_has_job", 24, needle(24, "GO TO F3 IF HAS JOB"), parents=f_wife_path
    )
    flow("h_route", 24, physical(24, 25), parents=f_wife_path)
    flow(
        "h_otherwise",
        24,
        needle(24, "OTHERWISE TURN TO P. 28, SECTION H"),
        parents=f_wife_path,
    )
    f_job_path = (("f_wife_in_fu", "f_has_job"),)
    h_path = (
        ("f_wife_in_fu", "h_route"),
        ("f_wife_in_fu", "h_otherwise"),
    )
    question(
        "f3_employee_self",
        24,
        physical(24, 38),
        branches=f_job_path,
        context=True,
    )
    flow(
        "f3_someone",
        24,
        needle(24, "1.         SOMEONE ELSE"),
        parents=f_job_path,
    )
    flow(
        "f3_both",
        24,
        needle(24, "2. BOTH SOMEONE ELSE AND          SELF"),
        parents=f_job_path,
    )
    flow(
        "f3_self_route",
        24,
        needle(24, "TURN TO P. 23, F8"),
        parents=f_job_path,
    )
    f_someone_paths = (
        ("f_wife_in_fu", "f_has_job", "f3_someone"),
        ("f_wife_in_fu", "f_has_job", "f3_both"),
    )
    anchor(
        "f_current_job",
        24,
        needle(24, "current job"),
        J,
        branches=f_someone_paths,
    )
    question(
        "f4_government",
        24,
        physical(24, 44),
        branches=f_someone_paths,
        context=True,
        context_parents=("f_current_job",),
    )
    anchor(
        "f_present_employer",
        24,
        needle(24, "present    employer"),
        J,
        branches=f_someone_paths,
    )
    question(
        "f7_employer_duration",
        24,
        physical(24, 66, 68),
        branches=f_someone_paths,
        context=True,
        context_parents=("f_present_employer",),
    )

    anchor(
        "f_main_occupation",
        25,
        needle(25, "main         occupation"),
        J,
        branches=f_job_path,
    )
    question(
        "f8_occupation",
        25,
        physical(25, 4),
        branches=f_job_path,
        context=True,
        context_parents=("f_main_occupation",),
    )
    question(
        "f9_duties",
        25,
        physical(25, 15),
        branches=f_job_path,
        context=True,
        context_parents=("f_main_occupation",),
    )
    question(
        "f10_industry",
        25,
        physical(25, 20),
        branches=f_job_path,
        context=True,
        context_parents=("f_main_occupation",),
    )
    question(
        "f11_pay_method",
        25,
        physical(25, 24),
        branches=f_job_path,
        context=True,
        context_parents=("f_current_job",),
    )
    anchor(
        "f_salary_component",
        25,
        needle(25, "salary?"),
        M,
        branches=f_job_path,
        parents=("f_current_job",),
    )
    anchor(
        "f_hourly_component",
        25,
        needle(25, "hourly wage"),
        M,
        branches=f_job_path,
        parents=("f_current_job",),
    )
    question(
        "f12_salary_amount",
        25,
        needle(25, "How much is her salary?"),
        branches=f_job_path,
    )
    question(
        "f12_per_month",
        25,
        needle(25, "PER MONTH"),
        branches=f_job_path,
    )
    question(
        "f12_per_year",
        25,
        needle(25, "PER YEAR"),
        branches=f_job_path,
    )
    question(
        "f13_hourly_amount",
        25,
        needle(25, "What is her hourly wage"),
        branches=f_job_path,
    )
    question(
        "f14_other_pay_unit",
        25,
        needle(25, "F14. How      that?chat?"),
        branches=f_job_path,
    )
    anchor(
        "f_present_position",
        25,
        needle(25, "present    position"),
        J,
        branches=f_job_path,
    )
    question(
        "f15_position_duration",
        25,
        physical(25, 46, 47),
        branches=f_job_path,
        context=True,
        context_parents=("f_present_position",),
    )
    flow("f16_less", 25, physical(25, 51), parents=f_job_path)
    flow("f16_long", 25, physical(25, 54), parents=f_job_path)
    f_prior_path = (("f_wife_in_fu", "f_has_job", "f16_less"),)
    anchor(
        "f_prior_job",
        25,
        needle(25, "job               she had before"),
        J,
        branches=f_prior_path,
    )
    question(
        "f17_prior_job_exit",
        25,
        physical(25, 56, 57),
        branches=f_prior_path,
        context=True,
        context_parents=("f_prior_job",),
    )

    flow("f18_yes", 26, physical(26, 3, 6), parents=f_job_path)
    f18_path = (("f_wife_in_fu", "f_has_job", "f18_yes"),)
    question(
        "f18_family_sick",
        26,
        physical(26, 3, 6),
        branches=f_job_path,
        context=True,
        context_parents=("f_current_job",),
    )
    question(
        "f19_family_sick_amount",
        26,
        physical(26, 14),
        branches=f18_path,
        context=True,
        context_parents=("f_main_occupation",),
    )
    flow("f20_yes", 26, physical(26, 19), parents=f_job_path)
    f20_path = (("f_wife_in_fu", "f_has_job", "f20_yes"),)
    question(
        "f20_own_sick",
        26,
        physical(26, 19),
        branches=f_job_path,
        context=True,
        context_parents=("f_current_job",),
    )
    question(
        "f21_own_sick_amount",
        26,
        physical(26, 24),
        branches=f20_path,
        context=True,
        context_parents=("f_main_occupation",),
    )
    flow("f22_yes", 26, physical(26, 28), parents=f_job_path)
    f22_path = (("f_wife_in_fu", "f_has_job", "f22_yes"),)
    question(
        "f22_vacation",
        26,
        physical(26, 28),
        branches=f_job_path,
        context=True,
        context_parents=("f_current_job",),
    )
    question(
        "f23_vacation_amount",
        26,
        physical(26, 33),
        branches=f22_path,
        context=True,
        context_parents=("f_main_occupation",),
    )
    flow("f24_yes", 26, physical(26, 37), parents=f_job_path)
    f24_path = (("f_wife_in_fu", "f_has_job", "f24_yes"),)
    question(
        "f24_strike",
        26,
        physical(26, 37),
        branches=f_job_path,
        context=True,
        context_parents=("f_current_job",),
    )
    question(
        "f25_strike_amount",
        26,
        physical(26, 42),
        branches=f24_path,
        context=True,
        context_parents=("f_main_occupation",),
    )
    flow("f26_yes", 26, physical(26, 46, 47), parents=f_job_path)
    f26_path = (("f_wife_in_fu", "f_has_job", "f26_yes"),)
    question(
        "f26_unemployed",
        26,
        physical(26, 46, 47),
        branches=f_job_path,
        context=True,
        context_parents=("f_current_job",),
    )
    question(
        "f27_unemployed_amount",
        26,
        physical(26, 53),
        branches=f26_path,
        context=True,
        context_parents=("f_main_occupation",),
    )
    question(
        "f28_weeks_worked",
        26,
        physical(26, 57, 58),
        branches=f_job_path,
        context=True,
        context_parents=("f_current_job",),
    )
    question(
        "f29_hours_worked",
        26,
        physical(26, 62, 63),
        branches=f_job_path,
        context=True,
        context_parents=("f_current_job",),
    )

    flow("f30_yes", 27, physical(27, 4), parents=f_job_path)
    f30_path = (("f_wife_in_fu", "f_has_job", "f30_yes"),)
    anchor(
        "f_overtime_component",
        27,
        needle(27, "overtime", 0),
        M,
        branches=f_job_path,
        parents=("f_current_job",),
    )
    question(
        "f30_overtime",
        27,
        physical(27, 4),
        branches=f_job_path,
        context=True,
        context_parents=("f_current_job",),
    )
    question(
        "f31_overtime_hours",
        27,
        physical(27, 10),
        branches=f30_path,
        context=True,
        context_parents=("f_main_occupation",),
    )
    flow("f32_yes", 27, physical(27, 15, 16), parents=f_job_path)
    f32_path = (("f_wife_in_fu", "f_has_job", "f32_yes"),)
    anchor(
        "f_extra_jobs",
        27,
        needle(27, "extra                       jobs"),
        J,
        branches=f_job_path,
    )
    question(
        "f32_extra_jobs",
        27,
        physical(27, 15, 16),
        branches=f_job_path,
        context=True,
        context_parents=("f_extra_jobs",),
    )
    question(
        "f33_extra_job_occupation",
        27,
        physical(27, 22),
        branches=f32_path,
        context=True,
        context_parents=("f_extra_jobs",),
    )
    question(
        "f34_extra_job_weeks",
        27,
        physical(27, 27, 28),
        branches=f32_path,
        context=True,
        context_parents=("f_extra_jobs",),
    )
    question(
        "f35_extra_job_hours",
        27,
        physical(27, 33, 34),
        branches=f32_path,
        context=True,
        context_parents=("f_extra_jobs",),
    )

    flow("g5_ever_job", 28, physical(28, 26), parents=f_wife_path)
    g_job_path = (("f_wife_in_fu", "g5_ever_job"),)
    question(
        "g5_ever_job",
        28,
        physical(28, 26),
        branches=f_wife_path,
        context=True,
    )
    anchor(
        "g_last_job",
        28,
        needle(28, "last               job"),
        J,
        branches=g_job_path,
    )
    question(
        "g6_last_job_occupation",
        28,
        physical(28, 33, 34),
        branches=g_job_path,
        context=True,
        context_parents=("g_last_job",),
    )
    question(
        "g7_last_job_industry",
        28,
        physical(28, 40),
        branches=g_job_path,
        context=True,
        context_parents=("g_last_job",),
    )
    question(
        "g8_last_job_exit",
        28,
        physical(28, 45, 46),
        branches=g_job_path,
        context=True,
        context_parents=("g_last_job",),
    )
    question(
        "g9_last_worked",
        28,
        physical(28, 50),
        branches=g_job_path,
        context=True,
        context_parents=("g_last_job",),
    )

    flow("g10_yes", 29, physical(29, 3, 5), parents=g_job_path)
    g10_path = (("f_wife_in_fu", "g5_ever_job", "g10_yes"),)
    question(
        "g10_vacation",
        29,
        physical(29, 3, 5),
        branches=g_job_path,
        context=True,
        context_parents=("g_last_job",),
    )
    question(
        "g11_vacation_amount",
        29,
        physical(29, 11),
        branches=g10_path,
        context=True,
        context_parents=("g_last_job",),
    )
    flow("g12_yes", 29, physical(29, 17, 18), parents=g_job_path)
    g12_path = (("f_wife_in_fu", "g5_ever_job", "g12_yes"),)
    question(
        "g12_family_sick",
        29,
        physical(29, 17, 18),
        branches=g_job_path,
        context=True,
        context_parents=("g_last_job",),
    )
    question(
        "g13_family_sick_amount",
        29,
        physical(29, 24),
        branches=g12_path,
        context=True,
        context_parents=("g_last_job",),
    )
    flow("g14_yes", 29, physical(29, 28), parents=g_job_path)
    g14_path = (("f_wife_in_fu", "g5_ever_job", "g14_yes"),)
    question(
        "g14_own_sick",
        29,
        physical(29, 28),
        branches=g_job_path,
        context=True,
        context_parents=("g_last_job",),
    )
    question(
        "g15_own_sick_amount",
        29,
        physical(29, 34),
        branches=g14_path,
        context=True,
        context_parents=("g_last_job",),
    )
    flow("g16_yes", 29, physical(29, 38), parents=g_job_path)
    g16_path = (("f_wife_in_fu", "g5_ever_job", "g16_yes"),)
    question(
        "g16_strike",
        29,
        physical(29, 38),
        branches=g_job_path,
        context=True,
        context_parents=("g_last_job",),
    )
    question(
        "g17_strike_amount",
        29,
        physical(29, 43),
        branches=g16_path,
        context=True,
        context_parents=("g_last_job",),
    )
    flow("g18_yes", 29, physical(29, 47, 48), parents=g_job_path)
    g18_path = (("f_wife_in_fu", "g5_ever_job", "g18_yes"),)
    question(
        "g18_unemployed",
        29,
        physical(29, 47, 48),
        branches=g_job_path,
        context=True,
        context_parents=("g_last_job",),
    )
    question(
        "g19_unemployed_amount",
        29,
        physical(29, 53),
        branches=g18_path,
        context=True,
        context_parents=("g_last_job",),
    )
    question(
        "g20_weeks_worked",
        29,
        physical(29, 56, 57),
        branches=g_job_path,
        context=True,
        context_parents=("g_last_job",),
    )
    question(
        "g21_hours_worked",
        29,
        physical(29, 61),
        branches=g_job_path,
        context=True,
        context_parents=("g_last_job",),
    )

    anchor(
        "h_wife_role",
        30,
        needle(30, "(wife/friend)", 1),
        R,
        branches=h_path,
    )
    repeat(
        "h1_wife_definition",
        30,
        block(30, "(REMEMBER:", "CONSIDERED       WIFE)"),
        branches=h_path,
        relation="explicit_repeat_instruction",
        evidence_keys=("h1_wife_definition",),
        target_scope="document_local",
    )
    anchor("h_section_context", 30, physical(30, 2), C, branches=h_path)
    flow("h3_yes", 30, physical(30, 16), parents=h_path)
    h_work_paths = tuple((*path, "h3_yes") for path in h_path)
    anchor(
        "h_work_for_money",
        30,
        needle(30, "work       for     money"),
        J,
        branches=h_path,
    )
    question(
        "h3_worked",
        30,
        physical(30, 16),
        branches=h_path,
        context=True,
        context_parents=("h_work_for_money",),
    )
    question(
        "h4_occupation",
        30,
        physical(30, 22),
        branches=h_work_paths,
        context=True,
        context_parents=("h_work_for_money",),
    )
    question(
        "h5_industry",
        30,
        physical(30, 27),
        branches=h_work_paths,
        context=True,
        context_parents=("h_work_for_money",),
    )
    question(
        "h6_weeks",
        30,
        physical(30, 32),
        branches=h_work_paths,
        context=True,
        context_parents=("h_work_for_money",),
    )
    question(
        "h7_hours",
        30,
        physical(30, 34),
        branches=h_work_paths,
        context=True,
        context_parents=("h_work_for_money",),
    )
    flow("h8_no", 30, physical(30, 36), parents=h_work_paths)
    h_exit_paths = tuple((*path, "h8_no") for path in h_work_paths)
    question(
        "h8_still_working",
        30,
        physical(30, 36),
        branches=h_work_paths,
        context=True,
        context_parents=("h_work_for_money",),
    )
    question(
        "h9_job_exit",
        30,
        physical(30, 39),
        branches=h_exit_paths,
        context=True,
        context_parents=("h_work_for_money",),
    )

    # Section K: source remuneration totals and farm/business aggregates.
    flow("k1_farmer", 33, physical(33, 13))
    flow("k1_nonfarmer", 33, physical(33, 15))
    k_income_paths = (("k1_farmer",), ("k1_nonfarmer",))
    farmer_path = (("k1_farmer",),)
    anchor(
        "k2_farm",
        33,
        needle(33, "receipts from farming"),
        FA,
        branches=farmer_path,
    )
    anchor(
        "k2_receipts",
        33,
        needle(33, "total       receipts"),
        M,
        branches=farmer_path,
        parents=("k2_farm",),
    )
    question(
        "k2_farm_receipts",
        33,
        physical(33, 20, 22),
        branches=farmer_path,
    )
    anchor(
        "k3_expenses",
        33,
        needle(33, "total      operating           expenses"),
        M,
        branches=farmer_path,
        parents=("k2_farm",),
    )
    question(
        "k3_farm_expenses",
        33,
        physical(33, 25, 26),
        branches=farmer_path,
    )
    anchor(
        "k4_farm",
        33,
        needle(33, "income   from farming"),
        FA,
        branches=farmer_path,
    )
    anchor(
        "k4_net_income",
        33,
        needle(33, "net        income"),
        M,
        branches=farmer_path,
        parents=("k4_farm",),
    )
    question(
        "k4_farm_net",
        33,
        physical(33, 28),
        branches=farmer_path,
    )
    anchor(
        "k5_business_owned",
        33,
        needle(33, "own a business"),
        BA,
        branches=k_income_paths,
    )
    anchor(
        "k5_business_enterprise",
        33,
        needle(33, "business               enterprise"),
        BA,
        branches=k_income_paths,
    )
    question(
        "k5_business_assignment",
        33,
        physical(33, 32, 33),
        branches=k_income_paths,
    )
    question(
        "k6_incorporation",
        33,
        physical(33, 40, 41),
        branches=k_income_paths,
        context=True,
        context_parents=("k5_business_owned",),
    )
    flow(
        "k6_corporation",
        33,
        needle(33, "1. CORPORATION"),
        parents=k_income_paths,
    )
    flow(
        "k6_unincorporated",
        33,
        needle(33, "2.        UNINCORPORATED"),
        parents=k_income_paths,
    )
    flow("k6_both", 33, needle(33, "3.         BOTH"), parents=k_income_paths)
    flow(
        "k6_dont_know",
        33,
        needle(33, "8.     DON'T KNOW"),
        parents=k_income_paths,
    )
    flow(
        "k6_corporation_skip",
        33,
        needle(33, "TURN TO P. 32, K8", 1),
        parents=(
            ("k1_farmer", "k6_corporation"),
            ("k1_nonfarmer", "k6_corporation"),
        ),
    )
    k7_paths = (
        ("k1_farmer", "k6_unincorporated"),
        ("k1_farmer", "k6_both"),
        ("k1_farmer", "k6_dont_know"),
        ("k1_nonfarmer", "k6_unincorporated"),
        ("k1_nonfarmer", "k6_both"),
        ("k1_nonfarmer", "k6_dont_know"),
    )
    anchor(
        "k7_business",
        33,
        needle(33, "income from the business"),
        BA,
        branches=k7_paths,
    )
    anchor(
        "k7_business_income",
        33,
        needle(33, "total         income"),
        M,
        branches=k7_paths,
        parents=("k7_business",),
    )
    question(
        "k7_business_share",
        33,
        physical(33, 47, 48),
        branches=k7_paths,
    )

    anchor("k8_head_role", 34, needle(34, "(HEAD)", 0), R)
    anchor("k8_head_work_total", 34, physical(34, 4, 5), T)
    anchor(
        "k8_wages_salaries",
        34,
        needle(34, "wages and salaries"),
        M,
        parents=("k8_head_work_total",),
    )
    question("k8_work_total", 34, physical(34, 4, 5))
    flow("k9_yes", 34, physical(34, 9, 10))
    flow("k9_no_route", 34, needle(34, "NO -r-         GO TO KU"))
    k9_path = (("k9_yes",),)
    anchor(
        "k9_additional_compensation",
        34,
        lines(34, "bonuses.", "or commissions?"),
        M,
        parents=("k8_head_work_total",),
    )
    question("k9_additional_compensation", 34, physical(34, 9, 10))
    question(
        "k10_additional_amount", 34, physical(34, 19, 21), branches=k9_path
    )
    anchor(
        "k11_professional_trade",
        34,
        needle(34, "PROFESSIONAL"),
        BA,
    )
    anchor(
        "k11_farming",
        34,
        needle(34, "farming    or market"),
        FA,
    )
    anchor(
        "k11_roomers",
        34,
        needle(34, "roomers   or boarders"),
        BA,
    )
    question("k11_other_work_income", 34, physical(34, 24, 26))
    question("k11_professional_trade", 34, physical(34, 32, 33))
    question("k11_farming_gardening", 34, physical(34, 36, 37))
    question("k11_roomers", 34, physical(34, 41))
    question("k12_amount", 34, needle(34, "How much was           it?"))
    question(
        "k13_duration", 34, needle(34, "During how much           of 1981")
    )
    repeat(
        "k11_repeat",
        34,
        needle(34, "(FOR EACH 'YES\" TO K11, ASK K12 AND K13.)"),
        relation="explicit_repeat_instruction",
        evidence_keys=(
            "k11_professional_trade",
            "k11_farming",
            "k11_roomers",
            "k11_repeat",
        ),
    )
    repeat(
        "k14_any_dollars_crossref",
        34,
        physical(34, 47, 49),
        relation="explicit_cross_reference",
        evidence_keys=("k14_any_dollars_crossref",),
        target_scope="document_local",
    )
    question(
        "k14_hours_reconciliation",
        34,
        physical(34, 52, 58),
        context=True,
        context_parents=("k8_head_work_total",),
    )
    repeat(
        "k14_hours_crossref",
        34,
        physical(34, 55, 63),
        relation="explicit_cross_reference",
        evidence_keys=(
            "k14_hours_reconciliation_context",
            "k14_hours_crossref",
        ),
    )

    flow("k23_wife_in_fu", 37, physical(37, 5, 6))
    flow("k23_no_wife", 37, physical(37, 8))
    flow("k23_head_female", 37, physical(37, 10))
    k23_path = (("k23_wife_in_fu",),)
    anchor(
        "k23_wife_role",
        37,
        needle(37, "(wife/friend)"),
        R,
        branches=k23_path,
    )
    repeat(
        "k23_wife_definition",
        37,
        block(37, "(REMEMBER:", "CONSIDERED WIFE.)"),
        branches=k23_path,
        relation="explicit_repeat_instruction",
        evidence_keys=("k23_wife_definition",),
        target_scope="document_local",
    )
    flow("k24_yes", 37, physical(37, 14), parents=k23_path)
    k24_path = (("k23_wife_in_fu", "k24_yes"),)
    question("k24_wife_income", 37, physical(37, 14), branches=k23_path)
    flow("k25_yes", 37, physical(37, 25), parents=k24_path)
    k25_path = (("k23_wife_in_fu", "k24_yes", "k25_yes"),)
    anchor(
        "k25_wife_work_earnings",
        37,
        needle(37, "earnings   from her work"),
        M,
        branches=k24_path,
        parents=("k26_wife_work_total",),
    )
    question(
        "k25_wife_work_earnings",
        37,
        physical(37, 25),
        branches=k24_path,
    )
    anchor(
        "k26_wife_work_total",
        37,
        physical(37, 31, 33),
        T,
        branches=k25_path,
    )
    question(
        "k26_wife_work_amount",
        37,
        physical(37, 31, 33),
        branches=k25_path,
    )
    repeat(
        "k26_work_hours_crossref",
        37,
        physical(37, 39, 40),
        branches=k25_path,
        relation="explicit_cross_reference",
        evidence_keys=(
            "k25_wife_work_earnings",
            "k26_wife_work_total",
            "k26_work_hours_crossref",
        ),
    )

    repeat(
        "k65_wife_definition",
        48,
        block(48, "(REMEMBER:", "CONSIDERED WIFE)"),
        relation="explicit_repeat_instruction",
        evidence_keys=("k65_wife_definition",),
        target_scope="document_local",
    )

    # Sections L-M: limited lifetime work history for newly entering roles.
    flow("l_new_wife", 49, physical(49, 8, 9))
    flow("l_head_female", 49, physical(49, 11))
    flow("l_no_wife", 49, physical(49, 13))
    flow("l_same_wife", 49, physical(49, 14, 15))
    l_path = (("l_new_wife",),)
    anchor(
        "l_wife_role",
        49,
        needle(49, "WIFE", 0),
        R,
        branches=l_path,
    )
    repeat(
        "l1_wife_definition",
        49,
        block(49, "(REMEMBER:", "CONSIDERED WIFE.)"),
        branches=l_path,
        relation="explicit_repeat_instruction",
        evidence_keys=("l1_wife_definition",),
        target_scope="document_local",
    )
    repeat(
        "l1_same_wife_crossref",
        49,
        needle(49, "SAME WIFE AS IN 1981"),
        branches=(("l_same_wife",),),
        relation="explicit_cross_reference",
        evidence_keys=("l1_same_wife_crossref",),
        target_scope="cross_document",
    )
    question(
        "l10_years_worked",
        50,
        physical(50, 4, 5),
        branches=l_path,
        context=True,
    )
    question(
        "l11_full_time_years",
        50,
        physical(50, 12, 13),
        branches=l_path,
        context=True,
    )
    question(
        "l12_part_time_share",
        50,
        physical(50, 19, 24),
        branches=l_path,
        context=True,
    )

    flow("m_new_head", 51, physical(51, 8, 9))
    flow("m_same_head", 51, physical(51, 10, 12))
    m_path = (("m_new_head",),)
    anchor(
        "m_head_role",
        51,
        needle(51, "HEAD IS A NEW HEAD THIS YEAR"),
        R,
        branches=m_path,
    )
    repeat(
        "m1_new_head_definition",
        51,
        block(51, "(REMEMBER:", "NEW HEADS)."),
        branches=m_path,
        relation="explicit_repeat_instruction",
        evidence_keys=("m1_new_head_definition",),
        target_scope="document_local",
    )
    repeat(
        "m1_same_head_crossref",
        51,
        needle(51, "HEAD IS THE SAME HEAD AS IN 1981 ITEM 15"),
        branches=(("m_same_head",),),
        relation="explicit_cross_reference",
        evidence_keys=("m1_same_head_crossref",),
        target_scope="cross_document",
    )
    anchor(
        "m4_first_job",
        51,
        needle(51, "first       full-time      regular   job"),
        J,
        branches=m_path,
    )
    question("m4_first_job", 51, physical(51, 51), branches=m_path)
    question(
        "m5_occupation_pattern",
        52,
        physical(52, 3, 4),
        branches=m_path,
        context=True,
        context_parents=("m4_first_job",),
    )
    question(
        "m25_years_worked",
        54,
        physical(54, 32),
        branches=m_path,
        context=True,
    )
    question(
        "m26_full_time_years",
        54,
        physical(54, 39),
        branches=m_path,
        context=True,
    )
    question(
        "m27_part_time_share",
        54,
        physical(54, 46, 47),
        branches=m_path,
        context=True,
    )

    ordered_specs = sorted(
        specs.values(),
        key=lambda row: (
            row["page"],
            row["start"],
            row["end"],
            annotation.KIND_ORDER[row["kind"]],
            row["key"],
        ),
    )
    for left, right in zip(ordered_specs, ordered_specs[1:], strict=False):
        if (
            left["page"] == right["page"]
            and left["kind"] == right["kind"]
            and right["start"] < left["end"]
        ):
            raise ValueError(
                "partially overlapping same-kind authored atoms: "
                f"{left['key']} / {right['key']}"
            )

    review_id_by_key = {
        row["key"]: _review_id(
            source_document_id,
            page_texts,
            row["page"],
            row["start"],
            row["end"],
            row["kind"],
        )
        for row in ordered_specs
    }
    flow_path_count = {
        row["key"]: len(row["branches"])
        for row in ordered_specs
        if row["kind"] == F
    }

    def translate_path(path: Sequence[str]) -> list[str]:
        translated: list[str] = []
        for key in path:
            review_id = review_id_by_key[key]
            translated.append(
                annotation._review_branch_ref(
                    review_id,
                    translated,
                    flow_path_count[key],
                )
            )
        return translated

    occurrence_specs = [
        {
            "review_occurrence_id": review_id_by_key[row["key"]],
            "page_number": row["page"],
            "utf8_byte_start": row["start"],
            "utf8_byte_end": row["end"],
            "occurrence_kind": row["kind"],
            "parent_review_branch_paths": [
                translate_path(path) for path in row["branches"]
            ],
            "review_note": row["note"],
        }
        for row in ordered_specs
    ]

    anchor_specs = []
    for row in ordered_specs:
        if row["kind"] not in annotation.ANCHOR_KINDS:
            continue
        matched = (
            page_texts[row["page"] - 1]
            .encode("utf-8")[row["start"] : row["end"]]
            .decode("utf-8")
        )
        if row["kind"] == R:
            node_domain = "role"
            classification = annotation.stage1_candidates._role_classification(
                matched
            )
        else:
            node_domain, classification = annotation.ANCHOR_CLASSIFICATION[
                row["kind"]
            ]
        anchor_specs.append(
            {
                "review_occurrence_id": review_id_by_key[row["key"]],
                "node_domain": node_domain,
                "classification": classification,
                "printed_identifier": annotation._source_printed_identifier(
                    page_texts[row["page"] - 1], row["start"]
                ),
                "parent_review_occurrence_ids": [
                    review_id_by_key[parent] for parent in row["parents"]
                ],
                "parent_resolution_note": (
                    "Exact document-local source parent(s) retained."
                    if row["parents"]
                    else "No document-local component parent applies."
                ),
                "classification_status": "provisional_document_local",
            }
        )

    repeat_specs = []
    source_order_by_key = {
        row["key"]: position for position, row in enumerate(ordered_specs)
    }
    for row in ordered_specs:
        repeat = row.get("repeat")
        if repeat is None:
            continue
        alias_keys, canonical_keys, evidence_keys, target, status = repeat
        alias_keys = tuple(
            sorted(alias_keys, key=source_order_by_key.__getitem__)
        )
        canonical_keys = tuple(
            sorted(canonical_keys, key=source_order_by_key.__getitem__)
        )
        evidence_keys = tuple(
            sorted(evidence_keys, key=source_order_by_key.__getitem__)
        )
        repeat_specs.append(
            {
                "review_occurrence_id": review_id_by_key[row["key"]],
                "relation": row.get("relation", "explicit_cross_reference"),
                "alias_anchor_review_occurrence_ids": [
                    review_id_by_key[key] for key in alias_keys
                ],
                "canonical_anchor_review_occurrence_ids": [
                    review_id_by_key[key] for key in canonical_keys
                ],
                "evidence_review_occurrence_ids": [
                    review_id_by_key[key] for key in evidence_keys
                ],
                "target_scope": target,
                "resolution_status": status,
            }
        )

    page_counts = Counter(row["page"] for row in ordered_specs)
    page_review_rows = []
    for page_number, page_text in enumerate(page_texts, start=1):
        count = page_counts[page_number]
        semantic_note = SEMANTIC_PAGE_NOTES.get(page_number)
        if semantic_note is None:
            note = (
                "Whole page reviewed; no covered R_Q source atoms retained "
                "after nonemployment and third-party exclusions."
            )
        else:
            note = f"{semantic_note} Retained {count} exact source atom(s)."
        page_review_rows.append(
            {
                "page_number": page_number,
                "page_text_utf8_sha256": annotation._sha256(
                    page_text.encode("utf-8")
                ),
                "whole_page_review_complete": True,
                "review_status": "complete",
                "review_note": note,
            }
        )

    review: dict[str, Any] = {
        "schema_version": annotation.REVIEW_SCHEMA_VERSION,
        "review_id": "rq-stage2-source-review:"
        + annotation._canonical_digest(
            [source_document_id, annotation.DOCUMENT_SOURCE_POSITION]
        ),
        "authority_kind": "reviewer_authored_source_bytes_only_nonauthority",
        "document_source_position": annotation.DOCUMENT_SOURCE_POSITION,
        "source_document_id": source_document_id,
        "review_method": {
            "source_rows_derived_from_page_bytes": True,
            "whole_page_review": "all_56_pages_including_empty_occurrence_pages",
            "span_granularity": "exact_utf8_lexeme_physical_line_or_source_block",
            "candidate_nonselection": "candidates_joined_only_after_source_rows_complete",
            "global_ids_assigned": False,
        },
        "page_review_rows": page_review_rows,
        "occurrence_specs": occurrence_specs,
        "local_anchor_specs": anchor_specs,
        "repeat_alias_specs": repeat_specs,
        "integrity": {
            "canonicalization": annotation.CANONICALIZATION,
            "content_sha256": "0" * 64,
        },
        "status": "complete",
    }
    review["integrity"]["content_sha256"] = annotation._content_sha256(review)
    annotation.validate_review(review, document, page_texts)
    return review


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    value = author_review()
    raw = annotation._canonical_bytes(value)
    if args.check:
        if not annotation.REVIEW_PATH.exists():
            raise SystemExit("document 30 source review is missing")
        if annotation.REVIEW_PATH.read_bytes() != raw:
            raise SystemExit("document 30 source review is stale")
    else:
        annotation.REVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
        annotation.REVIEW_PATH.write_bytes(raw)
    print(
        f"document 30 source review: {len(value['page_review_rows'])} pages, "
        f"{len(value['occurrence_specs'])} occurrences"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
