#!/usr/bin/env python3
"""Author the candidate-free source review for R_Q document 32.

All 64 physical pages of q83.pdf were reviewed against the authenticated
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

import build_rq_stage2_document_032_annotation as annotation

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
    9: "Head current-employment entry and assignment.",
    10: "Head current-job occupation, industry, and pay.",
    11: "Head current and immediately prior job context.",
    12: "Head annual work exposure and main-job hours.",
    13: "Head overtime and extra-job block.",
    14: "Head first and second unemployment-spell exposure.",
    15: "Head second and third unemployment-spell exposure.",
    16: "Head return-to-employer, job, and wage cross-references.",
    19: "Head looking-for-work and last-job context.",
    20: "Head last-job annual exposure.",
    21: "Head last-job extra-job block.",
    22: "Head last-job unemployment-spell exposure.",
    23: "Head last-job unemployment-spell continuation.",
    24: "Head last-job return cross-references.",
    27: "Head prior-year work while otherwise out of labor force.",
    29: "Spouse employment entry and assignment.",
    30: "Spouse current-job occupation, industry, and government level.",
    31: "Spouse current and immediately prior job pay/context.",
    32: "Spouse annual work exposure and main-job hours.",
    33: "Spouse overtime and extra-job block.",
    35: "Spouse last-job context.",
    36: "Spouse last-job annual exposure and extra jobs.",
    37: "Spouse last-job extra-job exposure.",
    39: "Spouse prior-year work while otherwise out of labor force.",
    43: "Farm and business work-income aggregates.",
    44: "Head wage, salary, and other work-income components.",
    45: "Head earned-income hours reconciliation.",
    47: "Spouse earned-income entry and total.",
    60: "New-spouse lifetime work exposure.",
    61: "New-head first regular job and occupation pattern.",
    63: "New-head lifetime work exposure.",
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

    # Head current-employment entry.  The three outer labels occur in source
    # order before the retained questions and are the only exact byte labels
    # used to route the C/D/E alternatives.
    flow("d_route", 9, block(9, "TURN TO P. 17.", "SECTIW D"))
    flow("e_route", 9, block(9, "*TURN TO", "SECTION           E"))
    flow("e_otherwise", 9, line(9, "OTHERWISE"))
    flow("c_has_job", 9, needle(9, "GO TO C2 If HEAD HAS JOB."))
    c_path = (("c_has_job",),)
    d_path = (("d_route",),)
    e_path = (("e_route",), ("e_otherwise",))
    flow(
        "c2_someone",
        9,
        needle(9, "1.    SOIIEDNE          ELSE"),
        parents=c_path,
    )
    flow(
        "c2_both",
        9,
        needle(
            9,
            "2.        BOTH       SOHEONE                  ELSE      AND SELF",
        ),
        parents=c_path,
    )
    flow(
        "c2_self",
        9,
        block(9, "3.   SELf     ONLY", "P. 8. c7"),
        parents=c_path,
    )
    c2_someone_paths = (
        ("c_has_job", "c2_someone"),
        ("c_has_job", "c2_both"),
    )

    anchor(
        "c_head_role",
        9,
        needle(9, "(HEAD)"),
        R,
    )
    anchor(
        "c_section_context",
        9,
        line(9, "SECTION                          C:"),
        C,
    )
    question(
        "c1_assignment",
        9,
        lines(9, "0 Cl.", "or   wh8t?"),
        context=True,
    )
    anchor(
        "c_current_job",
        9,
        needle(9, "current            job"),
        J,
        branches=c2_someone_paths,
    )
    question(
        "c2_employee_self",
        9,
        lines(9, "0 c2.", "yourself.                   or     what?"),
        branches=c_path,
        context=True,
        context_parents=("c_current_job",),
    )
    question(
        "c3_government",
        9,
        lines(
            9,
            "c3.",
            "a private      company,                             or        wh8t?",
        ),
        branches=c2_someone_paths,
        context=True,
        context_parents=("c_current_job",),
    )
    anchor(
        "c_present_employer",
        9,
        needle(9, "present           employer"),
        J,
        branches=c2_someone_paths,
    )
    question(
        "c6_employer_duration",
        9,
        line(9, "c6."),
        branches=c2_someone_paths,
        context=True,
        context_parents=("c_present_employer",),
    )

    # Head current-job attributes and pay.  Salary question prose is absent
    # from the authenticated extraction, so no visual-only C11 text is added.
    anchor(
        "c_main_job", 10, needle(10, "main         job"), J, branches=c_path
    )
    question(
        "c7_occupation",
        10,
        line(10, "Cl."),
        branches=c_path,
        context=True,
        context_parents=("c_main_job",),
    )
    question(
        "c8_duties",
        10,
        line(10, "C8."),
        branches=c_path,
        context=True,
        context_parents=("c_main_job",),
    )
    question(
        "c9_industry",
        10,
        line(10, "c9."),
        branches=c_path,
        context=True,
        context_parents=("c_main_job",),
    )
    question(
        "c10_pay_method",
        10,
        line(10, "ClO."),
        branches=c_path,
        context=True,
        context_parents=("c_main_job",),
    )
    flow("c_pay_salary", 10, needle(10, "salaried"), parents=c_path)
    flow(
        "c_pay_hourly",
        10,
        needle(10, "paid          by   the    hour"),
        parents=c_path,
    )
    flow("c_pay_other", 10, needle(10, "7.      OTWER"), parents=c_path)
    anchor(
        "c_salary_component",
        10,
        needle(10, "salaried"),
        M,
        branches=c_path,
        parents=("c_main_job",),
    )
    anchor(
        "c_hourly_component",
        10,
        needle(10, "paid          by   the    hour"),
        M,
        branches=c_path,
        parents=("c_main_job",),
    )
    anchor(
        "c_other_pay_component",
        10,
        needle(10, "7.      OTWER"),
        M,
        branches=c_path,
        parents=("c_main_job",),
    )
    c_salary_path = (("c_has_job", "c_pay_salary"),)
    c_hourly_path = (("c_has_job", "c_pay_hourly"),)
    c_other_path = (("c_has_job", "c_pay_other"),)
    flow("c12_yes", 10, needle(10, "1.      VES"), parents=c_salary_path)
    c12_path = (("c_has_job", "c_pay_salary", "c12_yes"),)
    question(
        "c12_extra_hours",
        10,
        lines(10, "C12.", "Of work?"),
        branches=c_salary_path,
        context=True,
        context_parents=("c_main_job",),
    )
    anchor(
        "c_extra_hours_component",
        10,
        needle(10, "those       extra      hours"),
        M,
        branches=c_salary_path,
        parents=("c_main_job",),
    )
    question(
        "c13_extra_hour_pay",
        10,
        lines(10, "C13.", "those    .xtr*        nours?"),
        branches=c12_path,
    )
    anchor(
        "c_regular_hourly_rate",
        10,
        needle(10, "nour1y       r.ga       t-ate"),
        M,
        branches=c_hourly_path,
        parents=("c_main_job",),
    )
    question(
        "c14_regular_hourly_rate",
        10,
        block(10, "nour1y       r.ga       t-ate", "work     tlw?"),
        branches=c_hourly_path,
    )
    anchor(
        "c_overtime_rate",
        10,
        needle(10, "hourly      “age         rate"),
        M,
        branches=c_hourly_path,
        parents=("c_main_job",),
    )
    question(
        "c15_overtime_rate",
        10,
        block(10, "hourly      “age         rate", "tot-   OWrtlme?"),
        branches=c_hourly_path,
    )
    question(
        "c16_other_pay_unit",
        10,
        needle(10, "C16.            How    IS     that7"),
        branches=c_other_path,
    )
    question(
        "c17_other_pay_amount",
        10,
        needle(
            10,
            "c17.            If   you    UOPkd            m-l .xtf-.      hour.",
        ),
        branches=c_other_path,
    )

    anchor(
        "c_present_position",
        11,
        needle(11, "present      position"),
        J,
        branches=c_path,
    )
    question(
        "c18_position_duration",
        11,
        line(11, "~18."),
        branches=c_path,
        context=True,
        context_parents=("c_present_position",),
    )
    flow(
        "c19_less",
        11,
        block(11, "8.       HEAD   HAS HAD PRESENT", "THAN       ONE YEAR"),
        parents=c_path,
    )
    c19_path = (("c_has_job", "c19_less"),)
    anchor(
        "c_prior_job",
        11,
        needle(11, "the job  you                  had     before"),
        J,
        branches=c19_path,
    )
    question(
        "c20_prior_job_exit",
        11,
        lines(11, "0 c20.", "or    what?"),
        branches=c19_path,
        context=True,
        context_parents=("c_prior_job",),
    )
    anchor(
        "c_present_job_reference",
        11,
        needle(11, "present        job"),
        J,
        branches=c19_path,
    )
    question(
        "c21_present_prior_assignment",
        11,
        lines(11, "0 c21.", "before?"),
        branches=c19_path,
        context=True,
        context_parents=("c_present_job_reference",),
    )

    # Head annual exposure.  Where response boxes disappeared from the
    # pinned extraction, the exact yes/no question block itself is the only
    # source-visible gate for its retained follow-up amount.
    c22_span = lines(12, "0 c22.", "in the family       was sick?")
    question(
        "c22_family_sick",
        12,
        c22_span,
        branches=c_path,
        context=True,
        context_parents=("c_main_job",),
    )
    flow("c22_yes", 12, c22_span, parents=c_path)
    c22_path = (("c_has_job", "c22_yes"),)
    question(
        "c23_family_sick_amount",
        12,
        line(12, "C23."),
        branches=c22_path,
        context=True,
        context_parents=("c_main_job",),
    )
    c24_span = line(12, "c24.")
    question(
        "c24_own_sick",
        12,
        c24_span,
        branches=c_path,
        context=True,
        context_parents=("c_main_job",),
    )
    flow("c24_yes", 12, c24_span, parents=c_path)
    c24_path = (("c_has_job", "c24_yes"),)
    question(
        "c25_own_sick_amount",
        12,
        line(12, "c25."),
        branches=c24_path,
        context=True,
        context_parents=("c_main_job",),
    )
    question(
        "c27_vacation_amount",
        12,
        line(12, "c27."),
        branches=c_path,
        context=True,
        context_parents=("c_main_job",),
        note="Exact C27 exposure row retained; C26 prompt bytes are absent.",
    )
    c28_span = line(12, "C28.")
    question(
        "c28_strike",
        12,
        c28_span,
        branches=c_path,
        context=True,
        context_parents=("c_main_job",),
    )
    flow("c28_yes", 12, c28_span, parents=c_path)
    c28_path = (("c_has_job", "c28_yes"),)
    question(
        "c29_strike_amount",
        12,
        line(12, "czg."),
        branches=c28_path,
        context=True,
        context_parents=("c_main_job",),
    )
    c30_span = lines(12, "0 c30.", "temporarily            laid   off?")
    question(
        "c30_unemployed",
        12,
        c30_span,
        branches=c_path,
        context=True,
        context_parents=("c_main_job",),
    )
    flow("c30_yes", 12, c30_span, parents=c_path)
    c30_path = (("c_has_job", "c30_yes"),)
    question(
        "c31_unemployed_amount",
        12,
        line(12, "c31."),
        branches=c30_path,
        context=True,
        context_parents=("c_main_job",),
    )
    question(
        "c32_weeks_worked",
        12,
        lines(12, "~32.", "WEEKS            IN     1982"),
        branches=c_path,
        context=True,
        context_parents=("c_main_job",),
    )
    question(
        "c33_main_job_hours",
        12,
        lines(12, "c33.", "HOURS       PER WEEK                 IN     1982"),
        branches=c_path,
        context=True,
        context_parents=("c_main_job",),
    )

    c34_span = line(13, "c34.")
    flow("c34_yes", 13, c34_span, parents=c_path)
    c34_path = (("c_has_job", "c34_yes"),)
    anchor(
        "c_overtime_component",
        13,
        needle(13, "overtime", 0),
        M,
        branches=c_path,
        parents=("c_main_job",),
    )
    question(
        "c34_overtime",
        13,
        c34_span,
        branches=c_path,
        context=True,
        context_parents=("c_main_job",),
    )
    question(
        "c35_overtime_hours",
        13,
        line(13, "c35."),
        branches=c34_path,
        context=True,
        context_parents=("c_main_job",),
    )
    c36_span = lines(13, "l c36.", "job      in ig8t?")
    flow("c36_yes", 13, c36_span, parents=c_path)
    c36_path = (("c_has_job", "c36_yes"),)
    anchor(
        "c_extra_jobs",
        13,
        needle(13, "extra          jobs"),
        J,
        branches=c_path,
    )
    question(
        "c36_extra_jobs",
        13,
        c36_span,
        branches=c_path,
        context=True,
        context_parents=("c_extra_jobs",),
    )
    question(
        "c37_extra_job_occupation",
        13,
        line(13, "c31."),
        branches=c36_path,
        context=True,
        context_parents=("c_extra_jobs",),
    )
    question(
        "c38_extra_job_count",
        13,
        line(13, "c38."),
        branches=c36_path,
        context=True,
        context_parents=("c_extra_jobs",),
    )
    anchor(
        "c_extra_job_hourly_pay",
        13,
        needle(13, "make       per        hour"),
        M,
        branches=c36_path,
        parents=("c_extra_jobs",),
    )
    question(
        "c39_extra_job_pay",
        13,
        line(13, "c39."),
        branches=c36_path,
    )
    question(
        "c40_extra_job_weeks",
        13,
        line(13, "c40."),
        branches=c36_path,
        context=True,
        context_parents=("c_extra_jobs",),
    )
    question(
        "c41_extra_job_hours",
        13,
        line(13, "c41."),
        branches=c36_path,
        context=True,
        context_parents=("c_extra_jobs",),
    )
    flow(
        "c42_unemp",
        13,
        block(
            13,
            "A.      HEAD HISSED",
            "TURN TO P. 12.                       03",
        ),
        parents=c_path,
    )
    c42_path = (("c_has_job", "c42_unemp"),)

    question(
        "c43_first_unemployment",
        14,
        block(14, "l c43.", "begin?              (IF     R"),
        branches=c42_path,
        context=True,
    )
    flow(
        "c43_january",
        14,
        block(
            14, "SAYS,     “January", "January .             -            IF"
        ),
        parents=c42_path,
    )
    question(
        "c43_january_start",
        14,
        needle(14, "“Yes, “ ASK :        When did  it first      begin?)"),
        branches=(("c_has_job", "c42_unemp", "c43_january"),),
    )
    question(
        "c44_first_unemployment_weeks",
        14,
        line(14, "c44."),
        branches=c42_path,
        context=True,
    )
    flow(
        "c49_1982",
        14,
        block(14, "A.    HEAD’S", "BEGAN      IN    1982"),
        parents=c42_path,
    )
    c49_path = (("c_has_job", "c42_unemp", "c49_1982"),)
    c50_span = lines(14, "0 (50.", "laid         off?")
    flow("c50_more", 14, c50_span, parents=c49_path)
    c50_path = (("c_has_job", "c42_unemp", "c49_1982", "c50_more"),)
    question(
        "c50_second_unemployment",
        14,
        c50_span,
        branches=c49_path,
        context=True,
    )
    question(
        "c51_second_unemployment_start",
        14,
        line(14, "C51."),
        branches=c50_path,
        context=True,
    )
    question(
        "c52_second_unemployment_weeks",
        15,
        line(15, ".   c52"),
        branches=c50_path,
        context=True,
    )
    flow(
        "c57_1982",
        15,
        block(15, "A.      HEAD’S", "BEGAN           IN          1062"),
        parents=c50_path,
    )
    c57_path = (
        ("c_has_job", "c42_unemp", "c49_1982", "c50_more", "c57_1982"),
    )
    c58_span = lines(
        15, ".C59.", "t.mporarr1y                  l.ld           Off?"
    )
    flow("c58_more", 15, c58_span, parents=c57_path)
    c58_path = (
        (
            "c_has_job",
            "c42_unemp",
            "c49_1982",
            "c50_more",
            "c57_1982",
            "c58_more",
        ),
    )
    question(
        "c58_third_unemployment",
        15,
        c58_span,
        branches=c57_path,
        context=True,
    )
    question(
        "c59_third_unemployment_start",
        15,
        line(15, "l c59."),
        branches=c58_path,
        context=True,
    )
    question(
        "c60_third_unemployment_weeks",
        15,
        line(15, "0 C60"),
        branches=c58_path,
        context=True,
    )

    # The three "same" questions are respondent-facing cross-references, not
    # automatic equivalence.  Preserve each exact relation for global review.
    anchor(
        "c72_same_employer",
        16,
        needle(16, "same        employer"),
        J,
        branches=c42_path,
    )
    c72_span = lines(16, "0     (72.", "same        employer?")
    question(
        "c72_return_employer",
        16,
        c72_span,
        branches=c42_path,
        context=True,
        context_parents=("c72_same_employer",),
    )
    repeat(
        "c72_crossref",
        16,
        c72_span,
        branches=c42_path,
        relation="explicit_cross_reference",
        alias_keys=("c72_same_employer",),
        evidence_keys=("c72_crossref", "c72_same_employer"),
    )
    c73_span = lines(16, ".c73.", "same      m       of      .j?")
    anchor(
        "c73_same_job",
        16,
        needle(16, "same      m       of      .j"),
        J,
        branches=c42_path,
    )
    question(
        "c73_return_job",
        16,
        c73_span,
        branches=c42_path,
        context=True,
        context_parents=("c73_same_job",),
    )
    repeat(
        "c73_crossref",
        16,
        c73_span,
        branches=c42_path,
        relation="explicit_cross_reference",
        alias_keys=("c73_same_job",),
        evidence_keys=("c73_crossref", "c73_same_job"),
    )
    c74_span = lines(16, "0     c74.", "off)?")
    anchor(
        "c74_wage_rate",
        16,
        needle(16, "wage    rate"),
        M,
        branches=c42_path,
        parents=("c73_same_job",),
    )
    question("c74_return_wage", 16, c74_span, branches=c42_path)
    repeat(
        "c74_crossref",
        16,
        c74_span,
        branches=c42_path,
        relation="explicit_cross_reference",
        alias_keys=("c74_wage_rate",),
        evidence_keys=("c74_crossref", "c74_wage_rate"),
    )

    # Head looking/not-currently-working: only actual prior work survives the
    # prospective search screen.  D7 is the exact source-visible gate.
    anchor("d_head_role", 19, needle(19, "HEAD"), R, branches=d_path)
    anchor(
        "d_section_context",
        19,
        line(19, "SECTION                   D:"),
        C,
        branches=d_path,
    )
    d7_span = line(19, "07.")
    flow("d7_ever_job", 19, d7_span, parents=d_path)
    d7_path = (("d_route", "d7_ever_job"),)
    question(
        "d7_ever_job",
        19,
        d7_span,
        branches=d_path,
        context=True,
    )
    anchor(
        "d_last_job",
        19,
        needle(19, "last      job"),
        J,
        branches=d7_path,
    )
    question(
        "d8_last_job_occupation",
        19,
        line(19, "08."),
        branches=d7_path,
        context=True,
        context_parents=("d_last_job",),
    )
    question(
        "d9_last_job_duties",
        19,
        line(19, "09."),
        branches=d7_path,
        context=True,
        context_parents=("d_last_job",),
    )
    question(
        "d10_last_job_industry",
        19,
        line(19, "DIO."),
        branches=d7_path,
        context=True,
        context_parents=("d_last_job",),
    )
    question(
        "d11_last_job_exit",
        19,
        lines(19, "Dll.", "laid           off,   or         what?"),
        branches=d7_path,
        context=True,
        context_parents=("d_last_job",),
    )
    question(
        "d12_last_worked",
        19,
        line(19, "D12.When"),
        branches=d7_path,
        context=True,
        context_parents=("d_last_job",),
    )

    d13_span = lines(20, "Dl3.", "Did you take         any vacation")
    flow("d13_yes", 20, d13_span, parents=d7_path)
    d13_path = (("d_route", "d7_ever_job", "d13_yes"),)
    question(
        "d13_vacation",
        20,
        d13_span,
        branches=d7_path,
        context=True,
        context_parents=("d_last_job",),
    )
    question(
        "d14_vacation_amount",
        20,
        line(20, "0’4."),
        branches=d13_path,
        context=True,
        context_parents=("d_last_job",),
    )
    question(
        "d16_family_sick_amount",
        20,
        line(20, "Dl6."),
        branches=d7_path,
        context=True,
        context_parents=("d_last_job",),
        note="Exact D16 amount row retained; D15 prompt bytes are absent.",
    )
    d17_span = line(20, "017.")
    flow("d17_yes", 20, d17_span, parents=d7_path)
    d17_path = (("d_route", "d7_ever_job", "d17_yes"),)
    question(
        "d17_own_sick",
        20,
        d17_span,
        branches=d7_path,
        context=True,
        context_parents=("d_last_job",),
    )
    question(
        "d18_own_sick_amount",
        20,
        line(20, "0~18."),
        branches=d17_path,
        context=True,
        context_parents=("d_last_job",),
    )
    d19_span = line(20, "0'9.")
    flow("d19_yes", 20, d19_span, parents=d7_path)
    d19_path = (("d_route", "d7_ever_job", "d19_yes"),)
    question(
        "d19_strike",
        20,
        d19_span,
        branches=d7_path,
        context=True,
        context_parents=("d_last_job",),
    )
    question(
        "d20_strike_amount",
        20,
        line(20, "D20."),
        branches=d19_path,
        context=True,
        context_parents=("d_last_job",),
    )
    d21_span = lines(20, "02’.", "temporarily                laid       off?")
    flow("d21_yes", 20, d21_span, parents=d7_path)
    d21_path = (("d_route", "d7_ever_job", "d21_yes"),)
    question(
        "d21_unemployed",
        20,
        d21_span,
        branches=d7_path,
        context=True,
        context_parents=("d_last_job",),
    )
    question(
        "d22_unemployed_amount",
        20,
        line(20, "D22."),
        branches=d21_path,
        context=True,
        context_parents=("d_last_job",),
    )
    anchor(
        "d_actual_jobs",
        20,
        needle(20, "job(s)"),
        J,
        branches=d7_path,
    )
    question(
        "d23_weeks_worked",
        20,
        lines(20, "023.", "WEEKS         IN     ‘982"),
        branches=d7_path,
        context=True,
        context_parents=("d_actual_jobs",),
    )
    question(
        "d24_hours_worked",
        20,
        lines(20, "D26.", "HOURS    PER WEEK                 IN      1982"),
        branches=d7_path,
        context=True,
        context_parents=("d_actual_jobs",),
    )

    d25_span = lines(21, "025.", "money  in lg82?")
    flow("d25_yes", 21, d25_span, parents=d7_path)
    d25_path = (("d_route", "d7_ever_job", "d25_yes"),)
    anchor(
        "d_extra_jobs",
        21,
        needle(21, "extra   jobs"),
        J,
        branches=d7_path,
    )
    question(
        "d25_extra_jobs",
        21,
        d25_span,
        branches=d7_path,
        context=True,
        context_parents=("d_extra_jobs",),
    )
    question(
        "d26_extra_job_occupation",
        21,
        line(21, "026."),
        branches=d25_path,
        context=True,
        context_parents=("d_extra_jobs",),
    )
    question(
        "d27_extra_job_count",
        21,
        line(21, "D27."),
        branches=d25_path,
        context=True,
        context_parents=("d_extra_jobs",),
    )
    anchor(
        "d_extra_job_hourly_pay",
        21,
        needle(21, "make       per     hour"),
        M,
        branches=d25_path,
        parents=("d_extra_jobs",),
    )
    question("d28_extra_job_pay", 21, line(21, "028."), branches=d25_path)
    question(
        "d29_extra_job_weeks",
        21,
        lines(21, "D2g.", "in     1gB2?"),
        branches=d25_path,
        context=True,
        context_parents=("d_extra_jobs",),
    )
    question(
        "d30_extra_job_hours",
        21,
        line(21, "030."),
        branches=d25_path,
        context=True,
        context_parents=("d_extra_jobs",),
    )
    flow(
        "d31_unemp",
        21,
        block(21, "A.      HEAD HISSED", "To    P. 20. r132"),
        parents=d7_path,
    )
    d31_path = (("d_route", "d7_ever_job", "d31_unemp"),)

    question(
        "d32_first_unemployment",
        22,
        block(22, "0032.", "begin?     (If              R"),
        branches=d31_path,
        context=True,
    )
    flow(
        "d32_january",
        22,
        block(
            22, "SAYS,    “J #anuary", "January    1982?                   IF"
        ),
        parents=d31_path,
    )
    question(
        "d32_january_start",
        22,
        needle(22, "“Yes, ” ASK:         When did   it first      begin?)"),
        branches=(("d_route", "d7_ever_job", "d31_unemp", "d32_january"),),
    )
    question(
        "d33_first_unemployment_weeks",
        22,
        lines(22, "D33.", "to    work?"),
        branches=d31_path,
        context=True,
    )
    flow(
        "d38_1982",
        22,
        block(22, "A.    HEAD’S", "BEGAN      IN     1982"),
        parents=d31_path,
    )
    d38_path = (("d_route", "d7_ever_job", "d31_unemp", "d38_1982"),)
    d39_span = lines(22, "039.", "temporarily           laid         off?")
    flow("d39_more", 22, d39_span, parents=d38_path)
    d39_path = (
        ("d_route", "d7_ever_job", "d31_unemp", "d38_1982", "d39_more"),
    )
    question(
        "d39_second_unemployment",
        22,
        d39_span,
        branches=d38_path,
        context=True,
    )
    question(
        "d40_second_unemployment_start",
        22,
        line(22, "040."),
        branches=d39_path,
        context=True,
    )
    question(
        "d41_second_unemployment_weeks",
        23,
        line(23, "041."),
        branches=d39_path,
        context=True,
    )
    flow(
        "d46_1982",
        23,
        block(23, "046.       IN~ERV:EYER", "(SEE          D40)"),
        parents=d39_path,
    )
    d46_path = (
        (
            "d_route",
            "d7_ever_job",
            "d31_unemp",
            "d38_1982",
            "d39_more",
            "d46_1982",
        ),
    )
    d47_span = block(
        23,
        "l    D47.",
        "15.                No    J-+TuRN                         T0        P.         22.     054",
    )
    flow("d47_more", 23, d47_span, parents=d46_path)
    d47_path = (
        (
            "d_route",
            "d7_ever_job",
            "d31_unemp",
            "d38_1982",
            "d39_more",
            "d46_1982",
            "d47_more",
        ),
    )
    question(
        "d47_third_unemployment",
        23,
        d47_span,
        branches=d46_path,
        context=True,
        note="Complete OCR-column-scrambled D47 source block retained.",
    )
    question(
        "d48_third_unemployment_start",
        23,
        line(23, "DOB."),
        branches=d47_path,
        context=True,
    )
    question(
        "d49_third_unemployment_weeks",
        23,
        line(23, "0049."),
        branches=d47_path,
        context=True,
    )

    anchor(
        "d61_same_employer",
        24,
        needle(24, "same employer"),
        J,
        branches=d31_path,
    )
    d61_span = lines(24, "061.", "same employer?")
    question(
        "d61_return_employer",
        24,
        d61_span,
        branches=d31_path,
        context=True,
        context_parents=("d61_same_employer",),
    )
    repeat(
        "d61_crossref",
        24,
        d61_span,
        branches=d31_path,
        relation="explicit_cross_reference",
        alias_keys=("d61_same_employer",),
        evidence_keys=("d61_crossref", "d61_same_employer"),
    )
    d62_span = lines(24, "~62.", "joJob?")
    anchor(
        "d62_same_job",
        24,
        block(24, "same       m", "joJob"),
        J,
        branches=d31_path,
    )
    question(
        "d62_return_job",
        24,
        d62_span,
        branches=d31_path,
        context=True,
        context_parents=("d62_same_job",),
    )
    repeat(
        "d62_crossref",
        24,
        d62_span,
        branches=d31_path,
        relation="explicit_cross_reference",
        alias_keys=("d62_same_job",),
        evidence_keys=("d62_crossref", "d62_same_job"),
    )
    d63_span = lines(24, "063.", "off)?")
    anchor(
        "d63_wage_rate",
        24,
        needle(24, "wage      rate"),
        M,
        branches=d31_path,
        parents=("d62_same_job",),
    )
    question("d63_return_wage", 24, d63_span, branches=d31_path)
    repeat(
        "d63_crossref",
        24,
        d63_span,
        branches=d31_path,
        relation="explicit_cross_reference",
        alias_keys=("d63_wage_rate",),
        evidence_keys=("d63_crossref", "d63_wage_rate"),
    )

    # Head otherwise out of the labor force: retain only actual 1982 work.
    anchor(
        "e_head_role",
        27,
        needle(27, "HEAD", 0),
        R,
        branches=e_path,
    )
    anchor(
        "e_section_context",
        27,
        line(27, "SECTION       E:"),
        C,
        branches=e_path,
    )
    e3_span = line(27, "E3.")
    flow("e3_yes", 27, e3_span, parents=e_path)
    e3_paths = (("e_route", "e3_yes"), ("e_otherwise", "e3_yes"))
    anchor(
        "e_work_for_money",
        27,
        needle(27, "work        for      money"),
        J,
        branches=e_path,
    )
    question(
        "e3_worked",
        27,
        e3_span,
        branches=e_path,
        context=True,
        context_parents=("e_work_for_money",),
    )
    question(
        "e4_occupation",
        27,
        line(27, "EA."),
        branches=e3_paths,
        context=True,
        context_parents=("e_work_for_money",),
    )
    question(
        "e5_duties",
        27,
        line(27, "E5."),
        branches=e3_paths,
        context=True,
        context_parents=("e_work_for_money",),
    )
    question(
        "e6_industry",
        27,
        line(27, "E6."),
        branches=e3_paths,
        context=True,
        context_parents=("e_work_for_money",),
    )
    question(
        "e7_weeks",
        27,
        line(27, "E7."),
        branches=e3_paths,
        context=True,
        context_parents=("e_work_for_money",),
    )
    question(
        "e8_hours",
        27,
        line(27, "E8."),
        branches=e3_paths,
        context=True,
        context_parents=("e_work_for_money",),
    )
    e9_span = line(27, "E9.")
    flow("e9_no", 27, e9_span, parents=e3_paths)
    e9_paths = (
        ("e_route", "e3_yes", "e9_no"),
        ("e_otherwise", "e3_yes", "e9_no"),
    )
    question(
        "e9_still_working",
        27,
        e9_span,
        branches=e3_paths,
        context=True,
        context_parents=("e_work_for_money",),
    )
    question(
        "e10_job_exit",
        27,
        lines(27, "EIO.", "laid        off,   or             what?"),
        branches=e9_paths,
        context=True,
        context_parents=("e_work_for_money",),
    )

    # Spouse employment entry.  All three checkpoint siblings are retained;
    # only the wife-in-FU path has employment descendants in this document.
    flow(
        "f_wife_in_fu",
        29,
        lines(29, "1.      HEAD IS MLE", "IS CONSIDERED   WIFE)"),
    )
    flow(
        "f_no_wife",
        29,
        lines(29, "2.         HEAD", "SECTION J"),
    )
    flow(
        "f_head_female",
        29,
        line(29, "3.        HEAD"),
    )
    f_entry = (("f_wife_in_fu",),)
    anchor(
        "f_section_context",
        29,
        needle(
            29,
            "SECTION             F: EMPLOYMENT                           OF WIFE/FRIEND",
        ),
        C,
        branches=f_entry,
    )
    anchor(
        "f_wife_role",
        29,
        needle(29, "WIFE", 0),
        R,
        branches=f_entry,
    )
    question(
        "f2_assignment",
        29,
        lines(29, "0 F2.", "or      what?"),
        branches=f_entry,
        context=True,
    )
    flow(
        "g_route",
        29,
        lines(29, "TURN TO P. 33.", "SECTION G"),
        parents=f_entry,
    )
    flow(
        "f_has_job",
        29,
        needle(29, "GO TO F3 IF HAS JOB."),
        parents=f_entry,
    )
    flow(
        "h_route",
        29,
        line(29, "OTHERWISE"),
        parents=f_entry,
    )
    f_job_path = (("f_wife_in_fu", "f_has_job"),)
    question(
        "f3_employee_self",
        29,
        line(29, "Does    your"),
        branches=f_job_path,
        context=True,
    )
    flow(
        "f3_someone_route",
        29,
        needle(29, "TURN       TO P.    28,     F4"),
        parents=f_job_path,
    )
    f_someone_path = (("f_wife_in_fu", "f_has_job", "f3_someone_route"),)

    anchor(
        "f_current_job",
        30,
        needle(30, "current          job"),
        J,
        branches=f_someone_path,
    )
    question(
        "f4_government",
        30,
        lines(
            30, "F4.", "a private      company,                    or what?"
        ),
        branches=f_someone_path,
        context=True,
        context_parents=("f_current_job",),
    )
    anchor(
        "f_present_employer",
        30,
        needle(30, "present       employer"),
        J,
        branches=f_someone_path,
    )
    question(
        "f7_employer_duration",
        30,
        line(30, "F7."),
        branches=f_someone_path,
        context=True,
        context_parents=("f_present_employer",),
    )
    anchor(
        "f_main_occupation",
        30,
        needle(30, "main            occupation"),
        J,
        branches=f_job_path,
    )
    question(
        "f8_occupation",
        30,
        line(30, "F8."),
        branches=f_job_path,
        context=True,
        context_parents=("f_main_occupation",),
    )
    question(
        "f9_duties",
        30,
        line(30, "F9."),
        branches=f_job_path,
        context=True,
        context_parents=("f_main_occupation",),
    )
    question(
        "f10_industry",
        30,
        line(30, "FlO."),
        branches=f_job_path,
        context=True,
        context_parents=("f_main_occupation",),
    )

    question(
        "f11_pay_method",
        31,
        line(31, "Fll."),
        branches=f_job_path,
        context=True,
        context_parents=("f_current_job",),
    )
    flow(
        "f_hourly_label",
        31,
        needle(31, "3.    PAID     BY HOUR"),
        parents=f_job_path,
    )
    f_hourly_path = (("f_wife_in_fu", "f_has_job", "f_hourly_label"),)
    anchor(
        "f_hourly_component",
        31,
        needle(31, "paid     by   the     hour"),
        M,
        branches=f_job_path,
        parents=("f_current_job",),
    )
    anchor(
        "f_salary_component",
        31,
        needle(31, "salary"),
        M,
        branches=f_job_path,
        parents=("f_current_job",),
    )
    add(
        "f12_salary_amount_purpose",
        31,
        needle(31, "salary?"),
        P,
        branches=f_job_path,
        note="Exact salary amount atom; surrounding columns are interleaved.",
    )
    for key, unit in (
        ("f12_per_week", "PER WEEK"),
        ("f12_per_month", "PER RONTH"),
        ("f12_per_year", "PER YEAR"),
    ):
        add(
            key,
            31,
            needle(31, unit),
            P,
            branches=f_job_path,
            note="Exact source reporting-unit atom retained manually.",
        )
    add(
        "f13_per_hour",
        31,
        needle(31, "PER HOUR"),
        P,
        branches=f_hourly_path,
        note="Exact source reporting-unit atom retained manually.",
    )
    add(
        "f14_other_pay_unit",
        31,
        needle(31, "F14.        How    is   that?"),
        P,
        branches=f_job_path,
        note="Exact other-pay reporting-unit prompt.",
    )
    anchor(
        "f_present_position",
        31,
        needle(31, "present         position", 0),
        J,
        branches=f_job_path,
    )
    question(
        "f15_position_duration",
        31,
        line(31, "FlS."),
        branches=f_job_path,
        context=True,
        context_parents=("f_present_position",),
    )
    flow(
        "f16_long",
        31,
        lines(31, "A.        WIFE/FRIEND", "P.    30.    F18"),
        parents=f_job_path,
    )
    flow(
        "f16_less",
        31,
        line(31, "8.        WIFE/FRIEND"),
        parents=f_job_path,
    )
    f16_less_path = (("f_wife_in_fu", "f_has_job", "f16_less"),)
    anchor(
        "f_prior_job",
        31,
        needle(31, "the job  she had                            before"),
        J,
        branches=f16_less_path,
    )
    question(
        "f17_prior_job_exit",
        31,
        lines(31, "F17.", "or what?"),
        branches=f16_less_path,
        context=True,
        context_parents=("f_prior_job",),
    )

    # Complete annual-exposure chain; edited-variable and reconciliation
    # metadata is deliberately outside the occurrence domain.
    f18_span = lines(32, "Fl8.", "family         was sick?")
    flow("f18_yes", 32, f18_span, parents=f_job_path)
    f18_path = (("f_wife_in_fu", "f_has_job", "f18_yes"),)
    question(
        "f18_family_sick",
        32,
        f18_span,
        branches=f_job_path,
        context=True,
        context_parents=("f_current_job",),
    )
    question(
        "f19_family_sick_amount",
        32,
        line(32, "Fig."),
        branches=f18_path,
        context=True,
        context_parents=("f_main_occupation",),
    )
    f20_span = line(32, "F20.")
    flow("f20_yes", 32, f20_span, parents=f_job_path)
    f20_path = (("f_wife_in_fu", "f_has_job", "f20_yes"),)
    question(
        "f20_own_sick",
        32,
        f20_span,
        branches=f_job_path,
        context=True,
        context_parents=("f_current_job",),
    )
    question(
        "f21_own_sick_amount",
        32,
        line(32, "F21."),
        branches=f20_path,
        context=True,
        context_parents=("f_main_occupation",),
    )
    f22_span = line(32, "F22.")
    flow("f22_yes", 32, f22_span, parents=f_job_path)
    f22_path = (("f_wife_in_fu", "f_has_job", "f22_yes"),)
    question(
        "f22_vacation",
        32,
        f22_span,
        branches=f_job_path,
        context=True,
        context_parents=("f_current_job",),
    )
    question(
        "f23_vacation_amount",
        32,
        line(32, "F23."),
        branches=f22_path,
        context=True,
        context_parents=("f_main_occupation",),
    )
    f24_span = lines(32, "F24.", "strike?")
    flow("f24_yes", 32, f24_span, parents=f_job_path)
    f24_path = (("f_wife_in_fu", "f_has_job", "f24_yes"),)
    question(
        "f24_strike",
        32,
        f24_span,
        branches=f_job_path,
        context=True,
        context_parents=("f_current_job",),
    )
    question(
        "f25_strike_amount",
        32,
        line(32, "F25."),
        branches=f24_path,
        context=True,
        context_parents=("f_main_occupation",),
    )
    f26_span = lines(32, "F26.", "laid   off?")
    flow("f26_yes", 32, f26_span, parents=f_job_path)
    f26_path = (("f_wife_in_fu", "f_has_job", "f26_yes"),)
    question(
        "f26_unemployed",
        32,
        f26_span,
        branches=f_job_path,
        context=True,
        context_parents=("f_current_job",),
    )
    question(
        "f27_unemployed_amount",
        32,
        line(32, "F27."),
        branches=f26_path,
        context=True,
        context_parents=("f_main_occupation",),
    )
    question(
        "f28_weeks_worked",
        32,
        lines(32, "F28.", "WEEKS             IN       1982"),
        branches=f_job_path,
        context=True,
        context_parents=("f_current_job",),
    )
    question(
        "f29_hours_worked",
        32,
        lines(32, "F29.", "HOURS         PER WEEK             IN     1982"),
        branches=f_job_path,
        context=True,
        context_parents=("f_current_job",),
    )

    f30_span = line(33, "F30.")
    flow("f30_yes", 33, f30_span, parents=f_job_path)
    f30_path = (("f_wife_in_fu", "f_has_job", "f30_yes"),)
    anchor(
        "f_overtime_component",
        33,
        needle(33, "overtime", 0),
        M,
        branches=f_job_path,
        parents=("f_current_job",),
    )
    question(
        "f30_overtime",
        33,
        f30_span,
        branches=f_job_path,
        context=True,
        context_parents=("f_current_job",),
    )
    question(
        "f31_overtime_hours",
        33,
        line(33, "F31."),
        branches=f30_path,
        context=True,
        context_parents=("f_main_occupation",),
    )
    f32_span = lines(
        33, "F32.", "to her main     job      in                    19821"
    )
    flow("f32_yes", 33, f32_span, parents=f_job_path)
    f32_path = (("f_wife_in_fu", "f_has_job", "f32_yes"),)
    anchor(
        "f_extra_jobs",
        33,
        needle(33, "extra         jobs"),
        J,
        branches=f_job_path,
    )
    question(
        "f32_extra_jobs",
        33,
        f32_span,
        branches=f_job_path,
        context=True,
        context_parents=("f_extra_jobs",),
    )
    question(
        "f33_extra_job_occupation",
        33,
        line(33, "f33."),
        branches=f32_path,
        context=True,
        context_parents=("f_extra_jobs",),
    )
    question(
        "f34_extra_job_weeks",
        33,
        lines(33, "F34.", "WEEKS         IN       1982"),
        branches=f32_path,
        context=True,
        context_parents=("f_extra_jobs",),
    )
    question(
        "f35_extra_job_hours",
        33,
        line(33, "F35."),
        branches=f32_path,
        context=True,
        context_parents=("f_extra_jobs",),
    )

    # Spouse not currently working: exclude prospective search G1-G4 and
    # retain only actual prior employment beginning at G5.
    g_path = (("f_wife_in_fu", "g_route"),)
    g5_span = line(35, "GS.")
    flow("g5_ever_job", 35, g5_span, parents=g_path)
    g5_path = (("f_wife_in_fu", "g_route", "g5_ever_job"),)
    question(
        "g5_ever_job",
        35,
        g5_span,
        branches=g_path,
        context=True,
    )
    anchor(
        "g_last_job",
        35,
        needle(35, "last        job"),
        J,
        branches=g5_path,
    )
    question(
        "g6_last_job_occupation",
        35,
        lines(35, "G6.", "her occupation?"),
        branches=g5_path,
        context=True,
        context_parents=("g_last_job",),
    )
    question(
        "g7_last_job_duties",
        35,
        line(35, "Gj."),
        branches=g5_path,
        context=True,
        context_parents=("g_last_job",),
    )
    question(
        "g8_last_job_industry",
        35,
        line(35, "G8."),
        branches=g5_path,
        context=True,
        context_parents=("g_last_job",),
    )
    question(
        "g9_last_job_exit",
        35,
        lines(35, "G9.", "laid         off,   or          what?"),
        branches=g5_path,
        context=True,
        context_parents=("g_last_job",),
    )
    question(
        "g10_last_worked",
        35,
        line(35, "GlO."),
        branches=g5_path,
        context=True,
        context_parents=("g_last_job",),
    )

    g11_span = lines(36, ".Gll.", "or time    off           during     1982’1")
    flow("g11_yes", 36, g11_span, parents=g5_path)
    g11_path = (("f_wife_in_fu", "g_route", "g5_ever_job", "g11_yes"),)
    question(
        "g11_vacation",
        36,
        g11_span,
        branches=g5_path,
        context=True,
        context_parents=("g_last_job",),
    )
    question(
        "g12_vacation_amount",
        36,
        line(36, "G12."),
        branches=g11_path,
        context=True,
        context_parents=("g_last_job",),
    )
    g13_span = lines(36, "Gl3.", "family        was                sick?")
    flow("g13_yes", 36, g13_span, parents=g5_path)
    g13_path = (("f_wife_in_fu", "g_route", "g5_ever_job", "g13_yes"),)
    question(
        "g13_family_sick",
        36,
        g13_span,
        branches=g5_path,
        context=True,
        context_parents=("g_last_job",),
    )
    question(
        "g14_family_sick_amount",
        36,
        line(36, "Cl&."),
        branches=g13_path,
        context=True,
        context_parents=("g_last_job",),
    )
    g15_span = line(36, "GlS.")
    flow("g15_yes", 36, g15_span, parents=g5_path)
    g15_path = (("f_wife_in_fu", "g_route", "g5_ever_job", "g15_yes"),)
    question(
        "g15_own_sick",
        36,
        g15_span,
        branches=g5_path,
        context=True,
        context_parents=("g_last_job",),
    )
    question(
        "g16_own_sick_amount",
        36,
        line(36, "G16."),
        branches=g15_path,
        context=True,
        context_parents=("g_last_job",),
    )
    g17_span = lines(36, "617.", "strike?")
    flow("g17_yes", 36, g17_span, parents=g5_path)
    g17_path = (("f_wife_in_fu", "g_route", "g5_ever_job", "g17_yes"),)
    question(
        "g17_strike",
        36,
        g17_span,
        branches=g5_path,
        context=True,
        context_parents=("g_last_job",),
    )
    question(
        "g18_strike_amount",
        36,
        line(36, "Gl8."),
        branches=g17_path,
        context=True,
        context_parents=("g_last_job",),
    )
    g19_span = lines(36, "Gl9.", "laid    off?")
    flow("g19_yes", 36, g19_span, parents=g5_path)
    g19_path = (("f_wife_in_fu", "g_route", "g5_ever_job", "g19_yes"),)
    question(
        "g19_unemployed",
        36,
        g19_span,
        branches=g5_path,
        context=True,
        context_parents=("g_last_job",),
    )
    question(
        "g20_unemployed_amount",
        36,
        line(36, "G20."),
        branches=g19_path,
        context=True,
        context_parents=("g_last_job",),
    )
    question(
        "g21_weeks_worked",
        36,
        lines(36, "G2l.", "WEEKS           IN    1982"),
        branches=g5_path,
        context=True,
        context_parents=("g_last_job",),
    )
    question(
        "g22_hours_worked",
        36,
        lines(36, "t22.", "HOURS         PER WEEK          IN      1982"),
        branches=g5_path,
        context=True,
        context_parents=("g_last_job",),
    )

    g23_span = lines(37, "G23.", "job        in    Ig82?")
    flow(
        "g23_yes",
        37,
        needle(37, "1.         YES"),
        parents=g5_path,
    )
    g23_path = (("f_wife_in_fu", "g_route", "g5_ever_job", "g23_yes"),)
    anchor(
        "g_extra_jobs",
        37,
        needle(37, "extra  jobs"),
        J,
        branches=g5_path,
    )
    question(
        "g23_extra_jobs",
        37,
        g23_span,
        branches=g5_path,
        context=True,
        context_parents=("g_extra_jobs",),
    )
    repeat(
        "g23_exposure_crossref",
        37,
        block(37, "(In addition", "US about.)"),
        branches=g5_path,
        relation="explicit_cross_reference",
        evidence_keys=(
            "g21_weeks_worked_context",
            "g22_hours_worked_context",
            "g23_exposure_crossref",
        ),
    )
    question(
        "g24_extra_job_occupation",
        37,
        line(37, "G24."),
        branches=g23_path,
        context=True,
        context_parents=("g_extra_jobs",),
    )
    question(
        "g25_extra_job_weeks",
        37,
        line(37, "G25."),
        branches=g23_path,
        context=True,
        context_parents=("g_extra_jobs",),
    )
    question(
        "g26_extra_job_hours",
        37,
        line(37, "G26."),
        branches=g23_path,
        context=True,
        context_parents=("g_extra_jobs",),
    )

    # Spouse otherwise out of the labor force mirrors the retained E3-E10
    # work episode.  Retirement-only H1/H2 and future-search H11-H13 are out.
    h_path = (("f_wife_in_fu", "h_route"),)
    anchor(
        "h_wife_role",
        39,
        needle(39, "WIFE/FRIEND"),
        R,
        branches=h_path,
    )
    anchor(
        "h_section_context",
        39,
        lines(39, "SECT&  H:", "DISABLED                          IN F2"),
        C,
        branches=h_path,
    )
    h3_span = block(39, "H3.", "money?")
    flow("h3_yes", 39, h3_span, parents=h_path)
    h3_path = (("f_wife_in_fu", "h_route", "h3_yes"),)
    anchor(
        "h_work_for_money",
        39,
        needle(39, "work         for        money"),
        J,
        branches=h_path,
    )
    question(
        "h3_worked",
        39,
        h3_span,
        branches=h_path,
        context=True,
        context_parents=("h_work_for_money",),
    )
    for key, marker in (
        ("h4_occupation", "H4."),
        ("h5_duties", "H5."),
        ("h6_industry", "H6."),
        ("h7_weeks", "H7."),
        ("h8_hours", "H8."),
    ):
        question(
            key,
            39,
            line(39, marker),
            branches=h3_path,
            context=True,
            context_parents=("h_work_for_money",),
        )
    h9_span = block(39, "Hg.", "working?")
    flow(
        "h9_no",
        39,
        needle(39, "5.          NO"),
        parents=h3_path,
    )
    h9_path = (("f_wife_in_fu", "h_route", "h3_yes", "h9_no"),)
    question(
        "h9_still_working",
        39,
        h9_span,
        branches=h3_path,
        context=True,
        context_parents=("h_work_for_money",),
    )
    question(
        "h10_job_exit",
        39,
        lines(39, "HIO.", "laid          off,   or           what?"),
        branches=h9_path,
        context=True,
        context_parents=("h_work_for_money",),
    )

    # Work-linked income.  Family transfers, other-FU loops, health, and
    # asset/support questions on pages 45-58 are not covered-earnings slots.
    flow(
        "k1_farmer",
        43,
        needle(43, "HEAD        IS     A FARNER               OR RANCHER"),
    )
    flow(
        "k1_nonfarmer",
        43,
        needle(
            43,
            "HEAD         IS      NOT A FARhER               OR RANCHER            -GO                   TO K5",
        ),
    )
    k_farmer_path = (("k1_farmer",),)
    k_all_paths = (("k1_farmer",), ("k1_nonfarmer",))
    k2_span = lines(43, "K2.", "commodity               credit loans?")
    anchor(
        "k2_farm",
        43,
        needle(43, "farming", 0),
        FA,
        branches=k_farmer_path,
    )
    anchor(
        "k2_receipts",
        43,
        needle(43, "receipts"),
        M,
        branches=k_farmer_path,
        parents=("k2_farm",),
    )
    question("k2_farm_receipts", 43, k2_span, branches=k_farmer_path)
    anchor(
        "k3_expenses",
        43,
        needle(43, "operating            expenses"),
        M,
        branches=k_farmer_path,
        parents=("k2_farm",),
    )
    question(
        "k3_farm_expenses",
        43,
        lines(43, "K3.", "living       expenses?"),
        branches=k_farmer_path,
    )
    anchor(
        "k4_net_income",
        43,
        needle(43, "net             income"),
        M,
        branches=k_farmer_path,
        parents=("k4_farm",),
    )
    anchor(
        "k4_farm",
        43,
        needle(43, "farming", 1),
        FA,
        branches=k_farmer_path,
    )
    question(
        "k4_farm_net",
        43,
        line(43, "K4."),
        branches=k_farmer_path,
    )
    k5_span = lines(43, "K5.", "business        enterprise?")
    anchor(
        "k5_business_owned",
        43,
        needle(43, "business", 0),
        BA,
        branches=k_all_paths,
    )
    anchor(
        "k5_business_enterprise",
        43,
        needle(43, "business", 1),
        BA,
        branches=k_all_paths,
    )
    question("k5_business_assignment", 43, k5_span, branches=k_all_paths)
    question(
        "k6_incorporation",
        43,
        lines(43, "K6.", "interest            in both               kinds?"),
        branches=k_all_paths,
        context=True,
        context_parents=("k5_business_owned",),
    )
    # Poppler omits K5's YES box and K6's CORPORATION text.  The unpaired K5
    # skip is not serialized because it would make K6 prefix-compatible with
    # the bypass.  Within K6, every locatable continuation/skip is retained.
    for key, label in (
        ("k6_unincorporated", "2.        UNINCORPORATED"),
        ("k6_both", "3.         BOTH"),
        ("k6_dont_know", "8.          DON’T           KNOW"),
    ):
        flow(key, 43, needle(43, label), parents=k_all_paths)
    flow(
        "k6_corporation_skip",
        43,
        needle(43, "TURN      TO P.       42.        K8"),
        parents=k_all_paths,
    )
    k7_paths = tuple(
        (*path, route)
        for path in k_all_paths
        for route in ("k6_unincorporated", "k6_both", "k6_dont_know")
    )
    anchor(
        "k7_business",
        43,
        needle(43, "business", 3),
        BA,
        branches=k7_paths,
    )
    anchor(
        "k7_business_income",
        43,
        needle(43, "share  of       the      total          income"),
        M,
        branches=k7_paths,
        parents=("k7_business",),
    )
    question(
        "k7_business_share",
        43,
        lines(43, "K7.", "profit      left     in?"),
        branches=k7_paths,
    )

    anchor("k8_head_role", 44, needle(44, "HEAD", 0), R)
    k8_span = lines(44, "K8.", "taxes               or other   thongs?")
    anchor("k8_head_work_total", 44, k8_span, T)
    anchor(
        "k8_wages_salaries",
        44,
        needle(44, "wages ind salaries"),
        M,
        parents=("k8_head_work_total",),
    )
    question("k8_work_total", 44, k8_span)
    k9_span = lines(44, "K9.", "commissions?")
    flow("k9_yes", 44, needle(44, "YES", 0))
    flow("k9_no_route", 44, needle(44, "GO TO Kll"))
    k9_path = (("k9_yes",),)
    anchor(
        "k9_additional_compensation",
        44,
        k9_span,
        M,
        parents=("k8_head_work_total",),
    )
    question("k9_additional_compensation", 44, k9_span)
    question("k10_additional_amount", 44, line(44, "K10."), branches=k9_path)
    anchor(
        "k11_professional_trade",
        44,
        needle(44, "professional           practice         or trade"),
        BA,
    )
    anchor(
        "k11_farming",
        44,
        needle(44, "farming        or    market"),
        FA,
    )
    anchor(
        "k11_roomers",
        44,
        needle(44, "roomers        or    boarders"),
        BA,
    )
    question(
        "k11_other_work_income",
        44,
        lines(
            44,
            "Kll.",
            "professional           practice         or trade?",
            start_ordinal=0,
        ),
    )
    add(
        "k11_farming_purpose",
        44,
        needle(44, "farming        or    market"),
        P,
        note="Exact K11 farming/market-gardening row prompt.",
    )
    add(
        "k11_farming_gardening_purpose",
        44,
        needle(44, "gardening?"),
        P,
        note=(
            "Exact tail of the K11 farming/market-gardening row; Poppler "
            "interleaves K12 value-column bytes between its two fragments."
        ),
    )
    add(
        "k11_roomers_purpose",
        44,
        needle(44, "roomers        or    boarders?"),
        P,
        note="Exact K11 roomers/boarders row prompt.",
    )
    add(
        "k12_amount_purpose",
        44,
        needle(44, "How much         was    it?"),
        P,
    )
    add(
        "k13_duration_purpose",
        44,
        needle(44, "Durina    how much            of        1982"),
        P,
    )
    add(
        "k13_duration_tail_purpose",
        44,
        needle(44, "did    you get this                income?"),
        P,
        note=(
            "Exact continuation of K13 retained separately because the "
            "K12 column is interleaved in Poppler order."
        ),
    )
    repeat(
        "k11_repeat",
        44,
        needle(
            44,
            '(FOR EACH "YES" TO Kll.                         ASK K12 AND Kl3.)',
        ),
        relation="explicit_repeat_instruction",
        evidence_keys=(
            "k11_repeat",
            "k11_professional_trade",
            "k11_farming",
            "k11_roomers",
        ),
    )

    question(
        "k14_hours_reconciliation",
        45,
        lines(
            45,
            "Kl4a.",
            "included         in    the hours           we discussed       earlier?",
        ),
        context=True,
        context_parents=("k8_head_work_total",),
    )
    repeat(
        "k14_hours_crossref",
        45,
        lines(
            45,
            "TURN           BACK TO APPROPRIATE",
            "SECTION           TO OBTAIN HISSING   HOURS",
        ),
        relation="explicit_cross_reference",
        evidence_keys=(
            "k14_hours_reconciliation_context",
            "k14_hours_crossref",
        ),
    )

    # Spouse work earnings only; transfer-source follow-ups K27-K33 are out.
    flow(
        "k23_wife_in_fu",
        47,
        lines(
            47,
            "HEAD IS NALE WHO HAS WIFE IN FU",
            "ONE YEAR OR HORE IS CONSIDERED WIFE)",
        ),
    )
    flow(
        "k23_no_wife",
        47,
        line(47, "8.      HEAD          IS    BALE."),
    )
    flow(
        "k23_head_female",
        47,
        line(47, "C.      HEAD          IS    FEHALE"),
    )
    k23_path = (("k23_wife_in_fu",),)
    anchor(
        "k23_wife_role",
        47,
        needle(47, "WIFE", 0),
        R,
        branches=k23_path,
    )
    k24_span = line(47, "K24.")
    flow("k24_yes", 47, needle(47, "YES", 0), parents=k23_path)
    flow(
        "k24_no_route",
        47,
        needle(47, "TURN     TO P.    47.     Kjltb"),
        parents=k23_path,
    )
    k24_path = (("k23_wife_in_fu", "k24_yes"),)
    question("k24_wife_income", 47, k24_span, branches=k23_path)
    k25_span = line(47, "K25.")
    flow("k25_yes", 47, needle(47, "YES", 1), parents=k24_path)
    flow(
        "k25_no_route",
        47,
        needle(47, "GO TO K27"),
        parents=k24_path,
    )
    k25_path = (("k23_wife_in_fu", "k24_yes", "k25_yes"),)
    k26_span = line(47, "~26.")
    anchor(
        "k26_wife_work_total",
        47,
        k26_span,
        T,
        branches=k25_path,
    )
    anchor(
        "k25_wife_work_earnings",
        47,
        needle(47, "earnings              from     her     work"),
        M,
        branches=k24_path,
        parents=("k26_wife_work_total",),
    )
    question("k25_wife_work_earnings", 47, k25_span, branches=k24_path)
    question("k26_wife_work_amount", 47, k26_span, branches=k25_path)
    repeat(
        "k26_work_hours_crossref",
        47,
        lines(
            47,
            "INTERVIEWER:  ANY DOLLARS  LISTED",
            "EHPLOYHENT   SECTIONS   (SECTION   F.                       G, OR HI!!",
        ),
        branches=k25_path,
        relation="explicit_cross_reference",
        evidence_keys=(
            "k25_wife_work_earnings",
            "k26_work_hours_crossref",
        ),
    )

    # Limited new-spouse/new-head work history.  Education, family
    # background, childhood farm residence, and religion remain excluded.
    flow(
        "l_new_wife",
        59,
        lines(
            59,
            "HEAD       HAS NEW WIFE THIS YEAR",
            "YEAR       OR HORE IS CONSIDERED WIFE)",
        ),
    )
    flow(
        "l_head_female",
        59,
        line(59, "HEAD         IS    FERALE"),
    )
    flow(
        "l_no_wife",
        59,
        line(59, "HEAD         IS HALE            WITH        NO WIFE"),
    )
    flow(
        "l_same_wife",
        59,
        lines(59, "HEAD         IS    MULE", "SECTION  A"),
    )
    l_path = (("l_new_wife",),)
    anchor(
        "l_wife_role",
        59,
        needle(59, "WIFE", 0),
        R,
        branches=l_path,
    )
    question(
        "l10_years_worked",
        60,
        line(60, "LlO."),
        branches=l_path,
        context=True,
    )
    question(
        "l11_full_time_years",
        60,
        line(60, "Lll."),
        branches=l_path,
        context=True,
    )
    question(
        "l12_part_time_share",
        60,
        lines(60, "L12.", "did    she work?"),
        branches=l_path,
        context=True,
    )

    flow(
        "m_new_head",
        61,
        needle(61, "HEAD IS A NEW HEAD                       THIS      YEAR"),
    )
    flow(
        "m_same_head",
        61,
        needle(
            61,
            "HEAD    IS THE            SAHE        HEAD       AS    IN      1982",
        ),
    )
    m_path = (("m_new_head",),)
    anchor(
        "m_head_role",
        61,
        needle(61, "(HEAD’S)", 1),
        R,
        branches=m_path,
    )
    anchor(
        "m4_first_job",
        61,
        needle(
            61, "first        full-time                regular         job"
        ),
        J,
        branches=m_path,
    )
    question(
        "m4_first_job",
        61,
        line(61, "A4."),
        branches=m_path,
    )
    question(
        "m5_occupation_pattern",
        61,
        lines(
            61,
            "H5.",
            "same       occupation            you started       in,                  or      what?",
        ),
        branches=m_path,
        context=True,
        context_parents=("m4_first_job",),
    )
    question(
        "m25_years_worked",
        63,
        line(63, "k25."),
        branches=m_path,
        context=True,
    )
    question(
        "m26_full_time_years",
        63,
        line(63, "n26."),
        branches=m_path,
        context=True,
    )
    question(
        "m27_part_time_share",
        63,
        lines(63, "n27.", "did    you work?"),
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
            "whole_page_review": "all_64_pages_including_empty_occurrence_pages",
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
            raise SystemExit("document 32 source review is missing")
        if annotation.REVIEW_PATH.read_bytes() != raw:
            raise SystemExit("document 32 source review is stale")
    else:
        annotation.REVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
        annotation.REVIEW_PATH.write_bytes(raw)
    print(
        f"document 32 source review: {len(value['page_review_rows'])} pages, "
        f"{len(value['occurrence_specs'])} occurrences"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
