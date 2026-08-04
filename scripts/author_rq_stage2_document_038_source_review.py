#!/usr/bin/env python3
"""Author the candidate-free source review for R_Q document 38.

All 59 Poppler pages of q86.pdf were reviewed from the authenticated page
bytes.  The retained spans below cover the source-visible Head and Wife work
sections, work-income prompts, and the narrow New-Head first-job history.
Health, housework, other-family-member, marriage, and education prose that
merely contains words such as ``work`` or ``job`` is deliberately excluded.

This helper never opens the stage-1 candidate shard.  Candidate adjudication
is performed later, after this page-complete source ledger validates.
"""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import build_rq_stage2_document_038_annotation as annotation

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


def _review_id(
    source_document_id: str,
    page_texts: Sequence[str],
    spec: dict[str, Any],
) -> str:
    raw = page_texts[spec["page"] - 1].encode("utf-8")
    matched = raw[spec["start"] : spec["end"]]
    matched.decode("utf-8", errors="strict")
    return "rq-review-occurrence:" + annotation._canonical_digest(
        [
            source_document_id,
            spec["page"],
            spec["start"],
            spec["end"],
            spec["kind"],
            annotation._sha256(matched),
        ]
    )


def author_review() -> dict[str, Any]:
    replay, index = annotation._source_replay_and_index()
    document, _identity = annotation._document_identity(replay, index)
    page_texts = annotation._extract_page_texts(document, replay)
    source_document_id = document["source_document_id"]

    specs: dict[str, dict[str, Any]] = {}

    def locate(page: int, text: str, ordinal: int) -> tuple[int, int]:
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
            raise ValueError(f"review needle absent on page {page}: {text!r}")
        if not 0 <= ordinal < len(positions):
            raise ValueError(
                f"review needle ordinal drift on page {page}: {text!r}"
            )
        start = positions[ordinal]
        return start, start + len(target)

    def span_text(
        page: int,
        start_text: str,
        end_text: str,
        *,
        start_ordinal: int = 0,
    ) -> str:
        start, _ = locate(page, start_text, start_ordinal)
        raw = page_texts[page - 1].encode("utf-8")
        end_target = end_text.encode("utf-8")
        end_start = raw.find(end_target, start)
        if end_start < 0:
            raise ValueError(
                f"review block end absent on page {page}: {end_text!r}"
            )
        return raw[start : end_start + len(end_target)].decode(
            "utf-8", errors="strict"
        )

    def add(
        key: str,
        page: int,
        text: str,
        kind: str,
        *,
        ordinal: int = 0,
        branches: Sequence[str] = (),
        branch_paths: Sequence[Sequence[str]] | None = None,
        parents: Sequence[str] = (),
        note: str = "Exact source atom retained after whole-page review.",
    ) -> None:
        if key in specs:
            raise ValueError(f"duplicate review key: {key}")
        if branch_paths is not None and branches:
            raise ValueError(
                f"review spec cannot mix branches and branch_paths: {key}"
            )
        start, end = locate(page, text, ordinal)
        resolved_branch_paths = (
            tuple(tuple(path) for path in branch_paths)
            if branch_paths is not None
            else (tuple(branches),)
        )
        if not resolved_branch_paths or any(
            not isinstance(path, tuple) for path in resolved_branch_paths
        ):
            raise ValueError(f"invalid review branch paths: {key}")
        specs[key] = {
            "key": key,
            "page": page,
            "start": start,
            "end": end,
            "kind": kind,
            "branch_paths": resolved_branch_paths,
            "parents": tuple(parents),
            "note": note,
        }

    def pair(
        key: str,
        page: int,
        text: str,
        kind: str,
        *,
        ordinal: int = 0,
        branches: Sequence[str] = (),
        branch_paths: Sequence[Sequence[str]] | None = None,
        parents: Sequence[str] = (),
    ) -> None:
        add(
            key + "_anchor",
            page,
            text,
            kind,
            ordinal=ordinal,
            branches=branches,
            branch_paths=branch_paths,
            parents=parents,
        )
        add(
            key + "_purpose",
            page,
            text,
            P,
            ordinal=ordinal,
            branches=branches,
            branch_paths=branch_paths,
            note="Exact source prompt retained for a covered R_Q purpose.",
        )

    def flow(
        key: str,
        page: int,
        text: str,
        *,
        ordinal: int = 0,
        branches: Sequence[str] = (),
    ) -> None:
        add(
            key,
            page,
            text,
            F,
            ordinal=ordinal,
            branches=branches,
            note="Exact source-visible routing label with reviewed ancestry.",
        )

    # Section B: Head currently working.  Response boxes missing from the
    # canonical Poppler bytes are not reconstructed from the image or from
    # neighboring waves.  Exact printed assignment/pay alternatives and
    # question-as-gate follow-ups are retained where the bytes resolve them.
    flow("b_section", 5, "SECTION B: EMPLOYMENT OF HEAD")
    b = ("b_section",)
    add("b_main_job_anchor", 5, "main job", J, branches=b)
    pair(
        "b_assignment",
        5,
        "On your main job, are you (HEAD) self-employed,",
        C,
        branches=b,
        parents=("b_main_job_anchor",),
    )
    flow("b_assignment_self", 5, "self-employed", branches=b)
    flow(
        "b_assignment_employee",
        5,
        "employed by someone else",
        branches=b,
    )
    flow("b_assignment_other", 5, "what?", ordinal=0, branches=b)
    b_self_employed = (*b, "b_assignment_self")
    b_employee = (*b, "b_assignment_employee")
    add(
        "b_assignment_employee_purpose",
        5,
        "are you employed by someone else, or",
        P,
        branches=b,
    )
    add(
        "b_assignment_other_purpose",
        5,
        "what?",
        P,
        ordinal=0,
        branches=b,
    )
    pair(
        "b_status",
        5,
        "We would like to know about what you do -- are you (HEAD) working now, looking for\nwork, retired, keeping house, student, or what?",
        C,
        branches=b,
    )
    add("b_head_role", 5, "HEAD", R, ordinal=2, branches=b)
    pair(
        "b_government_level",
        5,
        "local government, a private company, or what?",
        C,
        branches=b_employee,
        parents=("b_main_job_anchor",),
    )
    add(
        "b_government_lead_purpose",
        5,
        "Do you (HEAD) work for the federal, state, or",
        P,
        branches=b_employee,
    )
    pair(
        "b_incorporation",
        5,
        "a corporation?",
        C,
        branches=b_self_employed,
        parents=("b_main_job_anchor",),
    )
    add(
        "b_incorporation_lead_purpose",
        5,
        "Is that an unincor-",
        P,
        branches=b_self_employed,
    )
    add(
        "b_incorporation_middle_purpose",
        5,
        "porated business or",
        P,
        branches=b_self_employed,
    )
    pair(
        "b_occupation",
        5,
        "What isyour (HEAD'S) main occupation? What sort of work do you do?",
        C,
        branches=b,
        parents=("b_main_job_anchor",),
    )
    pair(
        "b_duties",
        5,
        "What are your most important activities or duties?",
        C,
        branches=b,
        parents=("b_main_job_anchor",),
    )
    pair(
        "b_industry",
        5,
        "What kind of business or industry is that in?",
        C,
        branches=b,
        parents=("b_main_job_anchor",),
    )

    pair(
        "b_pay_type",
        6,
        "(On your main job,) are you (HEAD) salaried, paid by the hour, or what?",
        C,
        branches=b,
        parents=("b_main_job_anchor",),
    )
    flow("b_pay_salary", 6, "salaried", branches=b)
    flow("b_pay_hourly", 6, "paid by the hour", branches=b)
    flow("b_pay_other", 6, "or what?", branches=b)
    b_salary_path = (*b, "b_pay_salary")
    b_hourly_path = (*b, "b_pay_hourly")
    b_other_pay_path = (*b, "b_pay_other")
    add(
        "b_salary_method_component",
        6,
        "salaried",
        M,
        branches=b,
        parents=("b_main_job_anchor",),
    )
    add(
        "b_hourly_method_component",
        6,
        "paid by the hour",
        M,
        branches=b,
        parents=("b_main_job_anchor",),
    )
    add(
        "b_other_pay_method_component",
        6,
        "or what?",
        M,
        branches=b,
        parents=("b_main_job_anchor",),
    )
    add(
        "b_salary_amount_lead_purpose",
        6,
        "How much is you",
        P,
        branches=b_salary_path,
    )
    pair(
        "b_salary",
        6,
        "salary?",
        M,
        branches=b_salary_path,
        parents=("b_main_job_anchor",),
    )
    pair(
        "b_hourly_regular",
        6,
        "hourly wage rate",
        M,
        ordinal=0,
        branches=b_hourly_path,
        parents=("b_main_job_anchor",),
    )
    pair(
        "b_hourly_overtime",
        6,
        "hourly wage rate",
        M,
        ordinal=1,
        branches=b_hourly_path,
        parents=("b_main_job_anchor",),
    )
    pair(
        "b_other_pay_unit",
        6,
        "How is that?",
        C,
        branches=b_other_pay_path,
        parents=("b_main_job_anchor",),
    )
    pair(
        "b_extra_hour_rate",
        6,
        "earn for that hour?",
        M,
        branches=b_other_pay_path,
        parents=("b_main_job_anchor",),
    )
    b_extra_hours_gate_text = span_text(
        6,
        "If you were tot",
        "some week, would",
    )
    pair(
        "b_extra_hours_gate_prompt",
        6,
        b_extra_hours_gate_text,
        C,
        branches=b_salary_path,
        parents=("b_main_job_anchor",),
    )
    pair(
        "b_extra_hours_gate_middle",
        6,
        "you get paid fort",
        C,
        branches=b_salary_path,
        parents=("b_main_job_anchor",),
    )
    b_extra_hours_gate_tail = span_text(
        6,
        "those extra hours",
        "work?",
    )
    pair(
        "b_extra_hours_gate_tail",
        6,
        b_extra_hours_gate_tail,
        C,
        branches=b_salary_path,
        parents=("b_main_job_anchor",),
    )
    flow(
        "b_extra_hours_gate",
        6,
        b_extra_hours_gate_text,
        branches=b_salary_path,
    )
    b_extra_hours_path = (*b_salary_path, "b_extra_hours_gate")
    pair(
        "b_extra_hours_amount",
        6,
        "would you make",
        M,
        branches=b_extra_hours_path,
        parents=("b_main_job_anchor",),
    )

    pair(
        "b_start_date",
        8,
        "Inwhat month and year did you (HEAD) start working inthat (position/work",
        C,
        branches=b,
    )
    pair(
        "b_prior_government",
        8,
        "government, a private company, or what?",
        C,
        branches=b,
    )
    pair(
        "b_prior_hours_1",
        8,
        "And how many hours a week did you work?",
        C,
        ordinal=0,
        branches=b,
    )
    pair(
        "b_prior_industry",
        8,
        "What kind of business or industry was that in?",
        C,
        branches=b,
    )
    pair(
        "b_prior_occupation",
        8,
        "What was your (HEAD'S) occupation? What sort of work did you do?",
        C,
        branches=b,
    )
    pair(
        "b_prior_duties",
        8,
        "What were your most important activities or duties?",
        C,
        branches=b,
    )
    pair(
        "b_prior_final_pay",
        8,
        "final wage or salary",
        M,
        branches=b,
    )
    pair(
        "b_prior_hours_2",
        8,
        "And how many hours a week did you work?",
        C,
        ordinal=1,
        branches=b,
    )

    # Annual exposure gates.  The answer boxes are absent from the canonical
    # extraction, so each exact yes/no question is the source-visible parent
    # of its amount/timing follow-ups.
    pair(
        "b_strike",
        9,
        "Did you miss any work in 1985 because you were on strike?",
        C,
        branches=b,
        parents=("b_main_job_anchor",),
    )
    flow(
        "b_strike_gate",
        9,
        "Did you miss any work in 1985 because you were on strike?",
        branches=b,
    )
    b_strike = (*b, "b_strike_gate")
    pair(
        "b_strike_amount",
        9,
        "How much work did you miss?",
        C,
        ordinal=0,
        branches=b_strike,
        parents=("b_main_job_anchor",),
    )
    pair(
        "b_strike_when",
        9,
        "When was that? [GET DAY IF VOLUNTEERED]",
        C,
        ordinal=0,
        branches=b_strike,
        parents=("b_main_job_anchor",),
    )

    add(
        "b_unemployed_lead",
        9,
        "Did you miss any work in 1985 because you were unemployed and",
        P,
        branches=b,
    )
    pair(
        "b_unemployed",
        9,
        "looking for work or temporarily laid off?",
        C,
        branches=b,
        parents=("b_main_job_anchor",),
    )
    flow(
        "b_unemployed_gate",
        9,
        "Did you miss any work in 1985 because you were unemployed and",
        branches=b,
    )
    b_unemployed = (*b, "b_unemployed_gate")
    pair(
        "b_unemployed_amount",
        9,
        "How much work did you miss?",
        C,
        ordinal=1,
        branches=b_unemployed,
        parents=("b_main_job_anchor",),
    )
    pair(
        "b_unemployed_when",
        9,
        "When was that? [GET DAY IF VOLUNTEERED]",
        C,
        ordinal=1,
        branches=b_unemployed,
        parents=("b_main_job_anchor",),
    )

    add(
        "b_family_sick_lead",
        9,
        "Did you miss any work in 1985 because",
        P,
        ordinal=2,
        branches=b,
    )
    pair(
        "b_family_sick",
        9,
        "someone else in the family was sick?",
        C,
        branches=b,
        parents=("b_main_job_anchor",),
    )
    flow(
        "b_family_sick_gate",
        9,
        "someone else in the family was sick?",
        branches=b,
    )
    b_family_sick = (*b, "b_family_sick_gate")
    pair(
        "b_family_sick_amount",
        9,
        "How much did you miss?",
        C,
        ordinal=0,
        branches=b_family_sick,
        parents=("b_main_job_anchor",),
    )
    pair(
        "b_family_sick_when",
        9,
        "When was that?",
        C,
        ordinal=2,
        branches=b_family_sick,
        parents=("b_main_job_anchor",),
    )

    no_job_text = span_text(
        9,
        "Were there any weeks in 1985 when you didn't have a job and",
        "were not looking for one?",
    )
    pair("b_no_job", 9, no_job_text, C, branches=b)
    flow("b_no_job_gate", 9, no_job_text, branches=b)
    b_no_job = (*b, "b_no_job_gate")
    pair(
        "b_no_job_amount",
        9,
        "How much time was that?",
        C,
        branches=b_no_job,
    )
    pair(
        "b_no_job_when",
        9,
        "When was that [GET DAY IFVOLUNTEERED]",
        C,
        branches=b_no_job,
    )

    pair(
        "b_own_sick",
        9,
        "Did you miss any work in 1985 because you were sick?",
        C,
        branches=b,
        parents=("b_main_job_anchor",),
    )
    flow(
        "b_own_sick_gate",
        9,
        "Did you miss any work in 1985 because you were sick?",
        branches=b,
    )
    b_own_sick = (*b, "b_own_sick_gate")
    pair(
        "b_own_sick_amount",
        9,
        "How much did you miss?",
        C,
        ordinal=1,
        branches=b_own_sick,
        parents=("b_main_job_anchor",),
    )
    pair(
        "b_own_sick_when",
        9,
        "When was that?",
        C,
        ordinal=3,
        branches=b_own_sick,
        parents=("b_main_job_anchor",),
    )

    pair(
        "b_vacation",
        9,
        "Did you take any vacation or time off during 1985?",
        C,
        branches=b,
        parents=("b_main_job_anchor",),
    )
    flow(
        "b_vacation_gate",
        9,
        "Did you take any vacation or time off during 1985?",
        branches=b,
    )
    b_vacation = (*b, "b_vacation_gate")
    pair(
        "b_vacation_amount",
        9,
        "How much vacation or time off did you take?",
        C,
        branches=b_vacation,
        parents=("b_main_job_anchor",),
    )
    pair(
        "b_vacation_when",
        9,
        "When was that?",
        C,
        ordinal=4,
        branches=b_vacation,
        parents=("b_main_job_anchor",),
    )

    b_weeks_text = span_text(
        9,
        "Then, how many weeks did you actually work on you main job(s) in",
        "1985?",
    )
    add("b_annual_weeks_job", 9, "main job(s)", J, branches=b)
    pair(
        "b_annual_weeks",
        9,
        b_weeks_text,
        C,
        branches=b,
        parents=("b_annual_weeks_job",),
    )
    add("b_annual_hours_job", 9, "main j", J, ordinal=1, branches=b)
    pair(
        "b_annual_hours",
        9,
        "And, on the average, how many hours a week did you work on your main j",
        C,
        branches=b,
        parents=("b_annual_hours_job",),
    )

    overtime_text = "Did you work any overtime which isn't included in that?"
    add(
        "b_overtime_component",
        9,
        "overtime",
        M,
        ordinal=0,
        branches=b,
        parents=("b_annual_hours_job",),
    )
    pair(
        "b_overtime",
        9,
        overtime_text,
        C,
        branches=b,
        parents=("b_annual_hours_job",),
    )
    flow("b_overtime_gate", 9, overtime_text, branches=b)
    b_overtime = (*b, "b_overtime_gate")
    pair(
        "b_overtime_hours",
        9,
        "How many hours did that overtime amount to in 1985?",
        C,
        branches=b_overtime,
        parents=("b_annual_hours_job",),
    )

    # Section C: Head not currently working.  The left-column more-work gate
    # and pay follow-up remain on B.  Poppler places the Section-C heading
    # between the gate's two physical lines, so the exact source fragments are
    # retained separately instead of spanning unrelated right-column prose.
    b_more_work_gate_lead = "Now thinking about your job(s) over the past year, was there more work available on"
    pair(
        "b_more_work_gate_lead",
        11,
        b_more_work_gate_lead,
        C,
        branches=b,
        parents=("b_main_job_anchor",),
    )
    pair(
        "b_more_work_gate_continuation",
        11,
        "(any of) your job(s) so that you could have worked more ifyou had wanted to",
        C,
        branches=b,
        parents=("b_main_job_anchor",),
    )
    flow(
        "b_more_work_gate",
        11,
        b_more_work_gate_lead,
        branches=b,
    )
    b_more_work_path = (*b, "b_more_work_gate")

    # Prospective right-column job-search intentions are not source jobs,
    # while actual last-work facts follow C's ever-work gate.
    flow("c_section", 11, 'SECTION C: HEAD IS NOT WORKING NOW ["NO" TO')
    c = ("c_section",)
    add("c_head_role", 11, "HEAD", R, ordinal=0, branches=c)
    pair(
        "b_more_work_pay",
        11,
        "How much would you have earned",
        M,
        branches=b_more_work_path,
        parents=("b_main_job_anchor",),
    )
    pair(
        "c_ever_work",
        12,
        "Have you ever done any work for money?",
        C,
        branches=c,
    )
    flow(
        "c_ever_work_gate",
        12,
        "Have you ever done any work for money?",
        branches=c,
    )
    c_worked = (*c, "c_ever_work_gate")
    pair(
        "c_last_work_date",
        12,
        "C10. When did you last work? [IF NECESSARY:   What would",
        C,
        branches=c_worked,
        parents=("c_last_job_anchor",),
    )
    add(
        "c_last_work_date_continuation",
        12,
        "be your best guess? Did you last work before 1985?]",
        P,
        branches=c_worked,
    )
    pair(
        "c_assignment",
        12,
        "C20. Were you self-employed, were you employed by someone else",
        C,
        branches=c_worked,
        parents=("c_last_job_anchor",),
    )
    flow("c_assignment_self", 12, "self-employed", branches=c_worked)
    flow(
        "c_assignment_employee",
        12,
        "employed by someone else",
        branches=c_worked,
    )
    c_last_job_employee = (*c_worked, "c_assignment_employee")
    c21_text = span_text(
        12,
        "C21. Did you work for the federal, state, or local government, a private",
        "or what?",
    )
    pair(
        "c_government",
        12,
        c21_text,
        C,
        branches=c_last_job_employee,
        parents=("c_last_job_anchor",),
    )
    pair(
        "c_exit_reason",
        12,
        "What happened to that job -- did the company go out of business, were you laid off,",
        C,
        branches=c_worked,
        parents=("c_last_job_anchor",),
    )
    pair(
        "c_end_date",
        12,
        "In what month and year did that (position/work situation) end?",
        C,
        branches=c_worked,
        parents=("c_last_job_anchor",),
    )
    pair(
        "c_last_job",
        12,
        "your occupation on your last job",
        J,
        branches=c_worked,
    )
    pair(
        "c_duties",
        12,
        "C18. What were your most important activities or duties.",
        C,
        branches=c_worked,
        parents=("c_last_job_anchor",),
    )
    pair(
        "c_industry",
        12,
        "C19. What kind of business or industry was that in?",
        C,
        branches=c_worked,
        parents=("c_last_job_anchor",),
    )

    pair(
        "c_prior_start",
        14,
        "C44. In what month and year did you (HEAD) start working in that (position/work",
        C,
        branches=c_worked,
    )
    pair(
        "c_prior_government",
        14,
        "government, a private company, or what?",
        C,
        branches=c_worked,
    )
    pair(
        "c_prior_start_pay",
        14,
        "What was your starting salary or wage at that time?",
        M,
        branches=c_worked,
    )
    pair(
        "c_prior_hours_1",
        14,
        "And how many hours a week did you work?",
        C,
        ordinal=0,
        branches=c_worked,
    )
    pair(
        "c_prior_industry",
        14,
        "What kind of business or industry was that in?",
        C,
        branches=c_worked,
    )
    pair(
        "c_prior_occupation",
        14,
        "What was your (HEAD'S) occupation? What sort of work did you do?",
        C,
        branches=c_worked,
    )
    pair(
        "c_prior_duties",
        14,
        "What were your most important activities or duties?",
        C,
        branches=c_worked,
    )
    pair(
        "c_prior_final_pay",
        14,
        "final wage or salary",
        M,
        branches=c_worked,
    )
    pair(
        "c_prior_hours_2",
        14,
        "And how many hours a week did you work?",
        C,
        ordinal=1,
        branches=c_worked,
    )

    # Wife currently working.  The section-D heading is absent from the exact
    # page text, so source-visible D atoms remain on the root path.
    add("d_spouse_role", 18, 'wife/"WIFE"', R, ordinal=0)
    add("d_main_job_anchor", 18, "her main job", J)
    # Stop before the following D20 column collision (", or job)"), which is
    # not the continuation of D12's pay-type question.
    pair(
        "d_pay_type",
        18,
        'D12. (On her main job,) is your (wife/"WIFE") salaried, paid by the hour',
        C,
        parents=("d_main_job_anchor",),
    )
    add("d_pay_type_continuation", 18, "what?", P)
    flow("d_pay_salary", 18, "salaried")
    flow("d_pay_hourly", 18, "paid by the hour")
    flow("d_pay_other", 18, "what?")
    d_salary_path = ("d_pay_salary",)
    d_hourly_path = ("d_pay_hourly",)
    d_other_pay_path = ("d_pay_other",)
    add(
        "d_salary_method_component",
        18,
        "salaried",
        M,
        parents=("d_main_job_anchor",),
    )
    add(
        "d_hourly_method_component",
        18,
        "paid by the hour",
        M,
        parents=("d_main_job_anchor",),
    )
    add(
        "d_other_pay_method_component",
        18,
        "what?",
        M,
        parents=("d_main_job_anchor",),
    )
    add(
        "d_salary_amount_purpose",
        18,
        "D13. How much is her",
        P,
        branches=d_salary_path,
    )
    add(
        "d_salary_component",
        18,
        "salary?",
        M,
        branches=d_salary_path,
        parents=("d_main_job_anchor",),
    )
    add(
        "d_salary_component_purpose",
        18,
        "salary?",
        P,
        branches=d_salary_path,
    )
    pair(
        "d_hourly_regular",
        18,
        "hourly wage rate",
        M,
        ordinal=0,
        branches=d_hourly_path,
        parents=("d_main_job_anchor",),
    )
    pair(
        "d_hourly_overtime",
        18,
        "hourly wage rate",
        M,
        ordinal=1,
        branches=d_hourly_path,
        parents=("d_main_job_anchor",),
    )
    pair(
        "d_other_pay_unit",
        18,
        "D18. How is that?",
        C,
        branches=d_other_pay_path,
        parents=("d_main_job_anchor",),
    )
    pair(
        "d_extra_hour_rate",
        18,
        "earn for that hour?",
        M,
        branches=d_other_pay_path,
        parents=("d_main_job_anchor",),
    )
    d_extra_hours_gate_text = span_text(
        18,
        "D14. Ifshe were to",
        "of work?",
    )
    pair(
        "d_extra_hours_gate_prompt",
        18,
        d_extra_hours_gate_text,
        C,
        branches=d_salary_path,
        parents=("d_main_job_anchor",),
    )
    flow(
        "d_extra_hours_gate",
        18,
        d_extra_hours_gate_text,
        branches=d_salary_path,
    )
    d_extra_hours_path = (*d_salary_path, "d_extra_hours_gate")
    pair(
        "d_extra_hours_amount",
        18,
        "would she make",
        M,
        branches=d_extra_hours_path,
        parents=("d_main_job_anchor",),
    )

    add("d_previous_job_anchor", 19, "another position with the same", J)
    d_prior_work_path = ("d_ever_prior_work_gate",)
    d_prior_job_paths = ((), d_prior_work_path)
    d_previous_assignment = span_text(
        19,
        'D30. We want to know what your (wife/"WIFE") was doing just before she started her',
        "another position with the same",
    )
    pair(
        "d_previous_assignment",
        19,
        d_previous_assignment,
        C,
        parents=("d_previous_job_anchor",),
    )
    add(
        "d_previous_assignment_continuation",
        19,
        span_text(
            19,
            "employer, was she unemployed and looking for work, temporarily laid off, working",
            "for a different employer, self employed, or what?",
        ),
        P,
    )
    pair(
        "d_employer_tenure",
        19,
        'How many years altogether has your (wife/"WIFE") worked for her present',
        C,
        parents=("d_main_job_anchor",),
    )
    pair(
        "d_current_start",
        19,
        "In what month and year did she start working in her present (position/",
        C,
        parents=("d_main_job_anchor",),
    )
    pair(
        "d_previous_end",
        19,
        "In what month and year did that (position/work         situation) end?",
        C,
        branch_paths=d_prior_job_paths,
        parents=("d_previous_job_anchor",),
    )
    pair(
        "d_current_start_pay",
        19,
        "What was her starting salary or wage at that time?",
        M,
        parents=("d_main_job_anchor",),
    )
    pair(
        "d_current_hours",
        19,
        "And how many hours a week did she work?",
        C,
        parents=("d_main_job_anchor",),
    )
    d_ever_prior_work_text = "D31. Did she ever work before that?"
    pair(
        "d_ever_prior_work",
        19,
        d_ever_prior_work_text,
        C,
        parents=("d_previous_job_anchor",),
    )
    flow("d_ever_prior_work_gate", 19, d_ever_prior_work_text)
    d_same_employer = "D32. Was she working for the same employer as"
    pair(
        "d_same_employer",
        19,
        d_same_employer,
        C,
        branches=d_prior_work_path,
        parents=("d_previous_job_anchor",),
    )
    pair(
        "d_same_employer_continuation",
        19,
        span_text(
            19,
            "she has now, a different one, or was",
            "she self-employed?",
        ),
        C,
        branches=d_prior_work_path,
        parents=("d_previous_job_anchor",),
    )
    add(
        "d_same_employer_reference",
        19,
        d_same_employer,
        A,
        branches=d_prior_work_path,
        note="Explicit source cross-reference retained for global resolution.",
    )
    specs["d_same_employer_reference"][
        "repeat_relation"
    ] = "explicit_cross_reference"
    specs["d_same_employer_reference"]["repeat_alias_keys"] = (
        "d_same_employer_anchor",
    )
    specs["d_same_employer_reference"]["repeat_evidence_keys"] = (
        "d_same_employer_anchor",
        "d_same_employer_continuation_anchor",
        "d_same_employer_reference",
    )
    pair(
        "d_previous_exit_reason",
        19,
        span_text(
            19,
            "D33. What happened to that job -- did the company go out of business, was she laid off,",
            "promoted, or what?",
        ),
        C,
        branch_paths=d_prior_job_paths,
        parents=("d_previous_job_anchor",),
    )

    pair(
        "d_earlier_start",
        20,
        'In what month and year did you (wife/"WIFE) start working in that (position/work',
        C,
        branch_paths=d_prior_job_paths,
        parents=("d_previous_job_anchor",),
    )
    pair(
        "d_earlier_government",
        20,
        "local government, a private company, or what?",
        C,
        branch_paths=d_prior_job_paths,
        parents=("d_previous_job_anchor",),
    )
    pair(
        "d_earlier_start_pay",
        20,
        "What was her starting salary or wage at that time?",
        M,
        branch_paths=d_prior_job_paths,
        parents=("d_previous_job_anchor",),
    )
    pair(
        "d_earlier_hours_1",
        20,
        "And how many hours a week did she work?",
        C,
        ordinal=0,
        branch_paths=d_prior_job_paths,
        parents=("d_previous_job_anchor",),
    )
    pair(
        "d_earlier_industry",
        20,
        "What kind of business or industry was that in?",
        C,
        branch_paths=d_prior_job_paths,
        parents=("d_previous_job_anchor",),
    )
    pair(
        "d_earlier_occupation",
        20,
        "What was your (wife's/\"WIFE'S\")                    occupation? What sort of work did she do?",
        C,
        branch_paths=d_prior_job_paths,
        parents=("d_previous_job_anchor",),
    )
    pair(
        "d_earlier_duties",
        20,
        "What were her most important activities or duties?",
        C,
        branch_paths=d_prior_job_paths,
        parents=("d_previous_job_anchor",),
    )
    pair(
        "d_earlier_final_pay",
        20,
        "final wage or salary",
        M,
        branch_paths=d_prior_job_paths,
        parents=("d_previous_job_anchor",),
    )
    pair(
        "d_earlier_hours_2",
        20,
        "And how many hours a week did she work?",
        C,
        ordinal=1,
        branch_paths=d_prior_job_paths,
        parents=("d_previous_job_anchor",),
    )

    # Section E: Wife not currently working.  Prospective job-search wording
    # on page 23 is not treated as a source job.
    flow("e_section", 23, 'SECTION E: WIFE/"WIFE" IS NOT WORKING NOW ["NO"')
    e = ("e_section",)
    add("e_spouse_role", 23, 'WIFE/"WIFE"', R, branches=e)
    pair(
        "e_ever_work",
        24,
        'E7. Has your (wife/"WIFE") ever done any work for money?',
        C,
        branches=e,
    )
    flow(
        "e_ever_work_gate",
        24,
        'E7. Has your (wife/"WIFE") ever done any work for money?',
        branches=e,
    )
    e_worked = (*e, "e_ever_work_gate")
    pair(
        "e_last_work_date",
        24,
        "E8. When did she last work? [IF NECESSARY: What would",
        C,
        branches=e_worked,
        parents=("e_last_job_anchor",),
    )
    add(
        "e_last_work_date_continuation",
        24,
        "be your best guess? Did she last work before 1985?]",
        P,
        branches=e_worked,
    )
    pair(
        "e_assignment",
        24,
        "E18. Was she self-employed, was she employed by someone else, or what?",
        C,
        branches=e_worked,
        parents=("e_last_job_anchor",),
    )
    flow("e_assignment_self", 24, "self-employed", branches=e_worked)
    flow(
        "e_assignment_employee",
        24,
        "employed by someone else",
        branches=e_worked,
    )
    flow(
        "e_assignment_other",
        24,
        "or what?",
        ordinal=0,
        branches=e_worked,
    )
    e_last_job_employee = (*e_worked, "e_assignment_employee")
    e19_text = span_text(
        24,
        "E19. Did she work for the federal, state, or local government, a priv",
        "or what?",
    )
    pair(
        "e_government",
        24,
        e19_text,
        C,
        branches=e_last_job_employee,
        parents=("e_last_job_anchor",),
    )
    pair(
        "e_exit_reason",
        24,
        span_text(
            24,
            "E23. What happened to that job--did the company go out of business, was she laid off, or",
            "what?",
        ),
        C,
        branches=e_worked,
        parents=("e_last_job_anchor",),
    )
    pair(
        "e_end_date",
        24,
        "E24. In what month and year did that (position/work situation) end?",
        C,
        branches=e_worked,
        parents=("e_last_job_anchor",),
    )
    pair(
        "e_last_job",
        24,
        "her occupation on her last job",
        J,
        branches=e_worked,
    )
    pair(
        "e_duties",
        24,
        "E16. What were her most important activities or duties?",
        C,
        branches=e_worked,
        parents=("e_last_job_anchor",),
    )
    pair(
        "e_industry",
        24,
        "E17. What kind of business or industry was that in?",
        C,
        branches=e_worked,
        parents=("e_last_job_anchor",),
    )

    pair(
        "e_final_pay",
        25,
        "final wage or salary",
        M,
        branches=e_worked,
        parents=("e_last_job_anchor",),
    )
    add(
        "e_previous_job_anchor",
        25,
        "another position with the same employer",
        J,
        branches=e_worked,
    )
    e_previous_assignment = span_text(
        25,
        'E31. We want to know what your (wife/"WIFE")                       was doing just before she started that',
        "another position with the same employer,",
    )
    pair(
        "e_previous_assignment",
        25,
        e_previous_assignment,
        C,
        branches=e_worked,
        parents=("e_previous_job_anchor",),
    )
    add(
        "e_previous_assignment_continuation",
        25,
        span_text(
            25,
            "was she unemployed and looking for work, temporarily laid off, working for a",
            "different employer, self-employed,                   or what?",
        ),
        P,
        branches=e_worked,
    )
    e_ever_prior_work_text = "E32. Did she ever work before that?"
    pair(
        "e_ever_prior_work",
        25,
        e_ever_prior_work_text,
        C,
        branches=e_worked,
        parents=("e_previous_job_anchor",),
    )
    flow(
        "e_ever_prior_work_gate",
        25,
        e_ever_prior_work_text,
        branches=e_worked,
    )
    e_prior_work_path = (*e_worked, "e_ever_prior_work_gate")
    e_prior_job_paths = (e_worked, e_prior_work_path)
    e_same_employer = span_text(
        25,
        "E33. Was she working for the same employer that",
        "we just talked about, a different one, or",
    )
    pair(
        "e_same_employer",
        25,
        e_same_employer,
        C,
        branches=e_prior_work_path,
        parents=("e_previous_job_anchor",),
    )
    add(
        "e_same_employer_continuation",
        25,
        "was she self-employed?",
        P,
        branches=e_prior_work_path,
    )
    add(
        "e_same_employer_reference",
        25,
        e_same_employer,
        A,
        branches=e_prior_work_path,
        note="Explicit source cross-reference retained for global resolution.",
    )
    specs["e_same_employer_reference"][
        "repeat_relation"
    ] = "explicit_cross_reference"
    specs["e_same_employer_reference"]["repeat_alias_keys"] = (
        "e_same_employer_anchor",
    )
    specs["e_same_employer_reference"]["repeat_evidence_keys"] = (
        "e_same_employer_anchor",
        "e_same_employer_reference",
    )
    pair(
        "e_last_hours",
        25,
        "And how many hours did a week did she work?",
        C,
        branches=e_worked,
        parents=("e_last_job_anchor",),
    )
    pair(
        "e_last_start",
        25,
        "In what month and year did she start working in that (position/work situation)?",
        C,
        branches=e_worked,
        parents=("e_last_job_anchor",),
    )
    pair(
        "e_last_start_pay",
        25,
        "What was her starting salary or wage at that time?",
        M,
        branches=e_worked,
        parents=("e_last_job_anchor",),
    )
    pair(
        "e_previous_end",
        25,
        "In what month and year that (position.work         situation) end?",
        C,
        branch_paths=e_prior_job_paths,
        parents=("e_previous_job_anchor",),
    )
    pair(
        "e_last_start_hours",
        25,
        "And how many hours a week did she work?",
        C,
        branches=e_worked,
        parents=("e_last_job_anchor",),
    )

    add(
        "e_annual_weeks_job",
        27,
        "main job(s)",
        J,
        branches=e_worked,
    )
    add(
        "e_annual_hours_job",
        27,
        "main job(S)",
        J,
        branches=e_worked,
    )

    pair(
        "e_strike",
        27,
        "E55. Did she miss any work in1985 because she was on strike?",
        C,
        branches=e_worked,
        parents=("e_annual_weeks_job",),
    )
    flow(
        "e_strike_gate",
        27,
        "E55. Did she miss any work in1985 because she was on strike?",
        branches=e_worked,
    )
    e_strike = (*e_worked, "e_strike_gate")
    pair(
        "e_strike_amount",
        27,
        "E56. How much work did she miss?",
        C,
        branches=e_strike,
        parents=("e_annual_weeks_job",),
    )
    pair(
        "e_strike_when",
        27,
        "E57. When was that?",
        C,
        branches=e_strike,
        parents=("e_annual_weeks_job",),
    )

    add(
        "e_unemployed_lead",
        27,
        "E58. Did she miss any work in1985 because she was unemployed and",
        P,
        branches=e_worked,
    )
    pair(
        "e_unemployed",
        27,
        "looking for work or temporarily laid off?",
        C,
        branches=e_worked,
        parents=("e_annual_weeks_job",),
    )
    flow(
        "e_unemployed_gate",
        27,
        "E58. Did she miss any work in1985 because she was unemployed and",
        branches=e_worked,
    )
    e_unemployed = (*e_worked, "e_unemployed_gate")
    pair(
        "e_unemployed_amount",
        27,
        "E59. How much work did she miss?",
        C,
        branches=e_unemployed,
        parents=("e_annual_weeks_job",),
    )
    pair(
        "e_unemployed_when",
        27,
        "E60. What was that?",
        C,
        branches=e_unemployed,
        parents=("e_annual_weeks_job",),
    )

    add(
        "e_vacation_lead",
        27,
        "Did she take any vacation or time off",
        P,
        branches=e_worked,
    )
    pair(
        "e_vacation",
        27,
        "during 1985?",
        C,
        branches=e_worked,
        parents=("e_annual_weeks_job",),
    )
    flow(
        "e_vacation_gate",
        27,
        "Did she take any vacation or time off",
        branches=e_worked,
    )
    e_vacation = (*e_worked, "e_vacation_gate")
    pair(
        "e_vacation_amount",
        27,
        "E47. How much vacation or time off did she take?",
        C,
        branches=e_vacation,
        parents=("e_annual_weeks_job",),
    )
    pair(
        "e_vacation_when",
        27,
        "E48. When was that?",
        C,
        branches=e_vacation,
        parents=("e_annual_weeks_job",),
    )

    e_no_job_text = span_text(
        27,
        "E61. Were there any weeks in1985 when she didn't have a job and",
        "was not looking for one?",
    )
    pair("e_no_job", 27, e_no_job_text, C, branches=e_worked)
    flow("e_no_job_gate", 27, e_no_job_text, branches=e_worked)
    e_no_job = (*e_worked, "e_no_job_gate")
    pair(
        "e_no_job_amount",
        27,
        "E62. How much time was that?",
        C,
        branches=e_no_job,
    )
    pair(
        "e_no_job_when",
        27,
        "E63. When was that? [GET DAY IFVOLUNTEERED]",
        C,
        branches=e_no_job,
    )

    e_family_sick_text = span_text(
        27,
        "E49. Did she miss any work in 1985 because you or someone else in the",
        "family was sick?",
    )
    pair(
        "e_family_sick",
        27,
        e_family_sick_text,
        C,
        branches=e_worked,
        parents=("e_annual_weeks_job",),
    )
    flow(
        "e_family_sick_gate",
        27,
        e_family_sick_text,
        branches=e_worked,
    )
    e_family_sick = (*e_worked, "e_family_sick_gate")
    pair(
        "e_family_sick_amount",
        27,
        "E50. How much work did she miss?",
        C,
        branches=e_family_sick,
        parents=("e_annual_weeks_job",),
    )

    e_own_sick_text = (
        "E52. Did she miss any work in 1985 because she was sick?"
    )
    pair(
        "e_own_sick",
        27,
        e_own_sick_text,
        C,
        ordinal=0,
        branches=e_worked,
        parents=("e_annual_weeks_job",),
    )
    flow(
        "e_own_sick_gate",
        27,
        e_own_sick_text,
        branches=e_worked,
    )
    e_own_sick = (*e_worked, "e_own_sick_gate")
    pair(
        "e_own_sick_duplicate",
        27,
        e_own_sick_text,
        C,
        ordinal=1,
        branches=e_worked,
        parents=("e_annual_weeks_job",),
    )
    pair(
        "e_own_sick_when",
        27,
        "E54. When was that?",
        C,
        branches=e_own_sick,
        parents=("e_annual_weeks_job",),
    )

    e_annual_weeks_text = span_text(
        27,
        "E64. Then, how many weeks did she actually work on her main job(s) in",
        "1985?",
    )
    pair(
        "e_annual_weeks",
        27,
        e_annual_weeks_text,
        C,
        branches=e_worked,
        parents=("e_annual_weeks_job",),
    )
    pair(
        "e_annual_hours",
        27,
        "E65. And, on the average, how many hours a week did she work on her main job(S) in 1985?",
        C,
        branches=e_worked,
        parents=("e_annual_hours_job",),
    )

    # Section G: only earned/work income and its farm/business aggregates.
    # Transfer-income and other-family-member grids are outside the two-role
    # R_Q domain.
    g: tuple[str, ...] = ()
    g12_text = span_text(
        31,
        "G12. Did you (HEAD) earn wages and salaries in 1985 from any jobs",
        "about?)",
    )
    flow("g_wage_gate", 31, g12_text, branches=g)
    g_wages_path = (*g, "g_wage_gate")
    add(
        "g_role_total_anchor",
        31,
        "altogether from wages and",
        T,
        branches=g_wages_path,
    )
    add("g_role_total_purpose", 31, g12_text, P, branches=g)
    add("g_head_role", 31, "HEAD", R, ordinal=0, branches=g)
    add(
        "g_prior_business_context",
        31,
        "unincorporated business we have just talked about",
        C,
        branches=g,
        parents=("g_business_owner",),
    )
    add(
        "g_prior_business_reference",
        31,
        "unincorporated business we have just talked about",
        A,
        branches=g,
        note="Explicit source cross-reference retained for global resolution.",
    )
    specs["g_prior_business_reference"][
        "repeat_relation"
    ] = "explicit_cross_reference"
    specs["g_prior_business_reference"]["repeat_alias_keys"] = (
        "g_prior_business_context",
    )
    specs["g_prior_business_reference"]["repeat_evidence_keys"] = (
        "g_prior_business_context",
        "g_prior_business_reference",
    )
    add(
        "g_wages",
        31,
        "wages and salaries",
        M,
        branches=g,
        parents=("g_role_total_anchor",),
    )
    g13_text = span_text(
        31,
        "G13. How much did you (HEAD) earn",
        "fir taxes or other things?",
    )
    add(
        "g_wage_amount",
        31,
        "G13. How much did you (HEAD) earn",
        M,
        branches=g_wages_path,
        parents=("g_role_total_anchor",),
    )
    add(
        "g_wage_amount_purpose",
        31,
        g13_text,
        P,
        branches=g_wages_path,
    )

    g14_text = span_text(
        31,
        "G14. In addition to this, did you",
        "overtime, tips, or commissions?",
    )
    flow("g_bonus_gate", 31, g14_text, branches=g)
    g_bonus_path = (*g, "g_bonus_gate")
    add(
        "g_bonus_income",
        31,
        span_text(
            31,
            "income from bonuses,",
            "overtime, tips, or commissions?",
        ),
        M,
        branches=g,
        parents=("g_role_total_anchor",),
    )
    add(
        "g_bonus_income_purpose",
        31,
        g14_text,
        P,
        branches=g,
    )
    add(
        "g_bonus_amount_purpose",
        31,
        "G15. How much was that?",
        P,
        branches=g_bonus_path,
    )

    add("g_farm_anchor", 31, "farming", FA, ordinal=0, branches=g)
    add(
        "g_farm_receipts",
        31,
        "total receipts from farming in 1985",
        M,
        branches=g,
        parents=("g_farm_anchor",),
    )
    add(
        "g_farm_receipts_purpose",
        31,
        span_text(
            31,
            "G3. What were your total receipts from farming in 1985,",
            "including soil bank payments and commodity credit loans?",
        ),
        P,
        branches=g,
    )
    add(
        "g_farm_expenses",
        31,
        "total operating expenses",
        M,
        branches=g,
        parents=("g_farm_anchor",),
    )
    add(
        "g_farm_expenses_purpose",
        31,
        span_text(
            31,
            "G4. What were your total operating expenses, not counting",
            "living expenses?",
        ),
        P,
        branches=g,
    )
    add(
        "g_farm_net",
        31,
        "net income from farming",
        M,
        branches=g,
        parents=("g_farm_anchor",),
    )
    add(
        "g_farm_net_purpose",
        31,
        "G5. That left you a net income from farming of?",
        P,
        branches=g,
    )

    g6_text = span_text(
        31,
        "G6. Did you (or anyone else in the family there ) own a business at any time in 1985 or",
        "have a financial interest in any business enterprise?",
    )
    add("g_business_owner", 31, "own a business", BA, branches=g)
    add(
        "g_business_owner_purpose",
        31,
        g6_text,
        P,
        branches=g,
    )
    flow("g_business_gate", 31, g6_text, branches=g)
    g_business_path = (*g, "g_business_gate")
    add(
        "g_business_practice",
        31,
        "professional practice of trade",
        BA,
        branches=g,
    )
    add(
        "g_business_practice_purpose",
        31,
        span_text(
            31,
            "G18. I'm going to read you a list of other sources of income you might have. Did you",
            "(HEAD) receive any other income in 1985 from professional practice of trade?",
        ),
        P,
        branches=g,
    )
    pair(
        "g_business_kind",
        31,
        "G7. What kind of business was that?",
        C,
        branches=g_business_path,
        parents=("g_business_owner",),
    )
    pair(
        "g_business_owner_assignment",
        31,
        "G8. Who inthe family owned that?",
        C,
        branches=g_business_path,
        parents=("g_business_owner",),
    )
    pair(
        "g_business_work",
        31,
        "G9. Did (you/he/she/they)        put in any work time for this business in 1985?",
        C,
        branches=g_business_path,
        parents=("g_business_owner",),
    )
    pair(
        "g_incorporation",
        31,
        span_text(
            31,
            "G10. Was it a corporation or an unincorporated business, or did (you/he/she/they)",
            "have an interest in both kinds?",
        ),
        C,
        branches=g_business_path,
        parents=("g_business_owner",),
    )
    add("g_farm_market", 31, "farming or", FA, ordinal=0, branches=g)
    add(
        "g_farm_market_purpose",
        31,
        span_text(31, "b.    farming or", "sardenins?"),
        P,
        branches=g,
    )
    add(
        "g_business_income",
        31,
        "share of the total income from the business",
        M,
        branches=g_business_path,
        parents=("g_business_owner",),
    )
    add(
        "g_business_income_purpose",
        31,
        span_text(31, "G11. How much was", "in?"),
        P,
        branches=g_business_path,
    )
    loss_gate_text = "[IF ZERO: Did you have a loss? How much was it?]"
    flow("g_loss_gate", 31, loss_gate_text, branches=g_business_path)
    g_loss = (*g_business_path, "g_loss_gate")
    add(
        "g_business_loss",
        31,
        "loss",
        M,
        branches=g_loss,
        parents=("g_business_owner",),
    )
    add(
        "g_business_loss_purpose",
        31,
        "Did you have a loss? How much was it?",
        P,
        branches=g_loss,
    )

    g23_text = span_text(
        32,
        "G23.talked",
        "about?",
    )
    add("g_extra_job_anchor", 32, "extra job(s)", J, branches=g)
    pair(
        "g_extra_job_crosscheck",
        32,
        g23_text,
        C,
        branches=g,
        parents=("g_extra_job_anchor",),
    )
    add(
        "g_prior_amount_reference",
        32,
        g23_text,
        A,
        branches=g,
        note="Explicit source cross-reference retained for global resolution.",
    )
    specs["g_prior_amount_reference"][
        "repeat_relation"
    ] = "explicit_cross_reference"
    specs["g_prior_amount_reference"]["repeat_alias_keys"] = (
        "g_extra_job_crosscheck_anchor",
    )
    specs["g_prior_amount_reference"]["repeat_evidence_keys"] = (
        "g_extra_job_crosscheck_anchor",
        "g_prior_amount_reference",
    )
    pair(
        "g_extra_job_amount",
        32,
        "How much did you earn from your extra jobs in 1985?",
        M,
        branches=g,
        parents=("g_extra_job_anchor",),
    )

    # The one source-visible New-Head work-history block.  Relocation prose,
    # parents' occupations, and education conditionals on the same page do not
    # create role/job/component nodes.
    section_l: tuple[str, ...] = ()
    add("l_head_role", 57, "HEAD'S", R, ordinal=2, branches=section_l)
    add(
        "l_first_job_anchor",
        57,
        "first full-time regular job",
        J,
        branches=section_l,
    )
    add(
        "l_first_job_purpose",
        57,
        "Thinking or your (HEAD'S) first full-time regular job, what did you do?",
        P,
        branches=section_l,
    )
    pair(
        "l_occupation_pattern",
        57,
        span_text(
            57,
            "have you had a number of jobs or have you mostly worked in the",
            "same occupation you started in, or what?",
        ),
        C,
        branches=section_l,
        parents=("l_first_job_anchor",),
    )

    ordered = sorted(
        specs.values(),
        key=lambda row: (
            row["page"],
            row["start"],
            row["end"],
            annotation.KIND_ORDER[row["kind"]],
            row["key"],
        ),
    )
    review_id_by_key = {
        spec["key"]: _review_id(source_document_id, page_texts, spec)
        for spec in ordered
    }
    occurrence_specs: list[dict[str, Any]] = []
    for spec in ordered:
        occurrence_specs.append(
            {
                "review_occurrence_id": review_id_by_key[spec["key"]],
                "page_number": spec["page"],
                "utf8_byte_start": spec["start"],
                "utf8_byte_end": spec["end"],
                "occurrence_kind": spec["kind"],
                "parent_review_branch_paths": [
                    [review_id_by_key[key] for key in path]
                    for path in spec["branch_paths"]
                ],
                "review_note": spec["note"],
            }
        )

    anchor_classification = annotation.ANCHOR_CLASSIFICATION
    local_anchor_specs: list[dict[str, Any]] = []
    for spec in ordered:
        if spec["kind"] not in annotation.ANCHOR_KINDS:
            continue
        raw = page_texts[spec["page"] - 1].encode("utf-8")
        matched = raw[spec["start"] : spec["end"]].decode("utf-8")
        if spec["kind"] == R:
            node_domain = "role"
            classification = annotation.stage1_candidates._role_classification(
                matched
            )
        else:
            node_domain, classification = anchor_classification[spec["kind"]]
        parents = [review_id_by_key[key] for key in spec["parents"]]
        local_anchor_specs.append(
            {
                "review_occurrence_id": review_id_by_key[spec["key"]],
                "node_domain": node_domain,
                "classification": classification,
                "printed_identifier": annotation._source_printed_identifier(
                    page_texts[spec["page"] - 1], spec["start"]
                ),
                "parent_review_occurrence_ids": parents,
                "parent_resolution_note": (
                    "Exact document-local source parent(s) retained."
                    if parents
                    else "No source-visible document-local parent is asserted."
                ),
                "classification_status": "provisional_document_local",
            }
        )

    counts = Counter(spec["page"] for spec in ordered)
    page_review_rows = []
    for page_number, page_text in enumerate(page_texts, start=1):
        count = counts[page_number]
        page_review_rows.append(
            {
                "page_number": page_number,
                "page_text_utf8_sha256": annotation._sha256(
                    page_text.encode("utf-8")
                ),
                "whole_page_review_complete": True,
                "review_status": "complete",
                "review_note": (
                    f"Whole page reviewed; retained {count} exact R_Q source atom(s)."
                    if count
                    else "Whole page reviewed; no covered R_Q source atoms retained."
                ),
            }
        )

    repeat_alias_specs = []
    source_order_by_key = {
        spec["key"]: position for position, spec in enumerate(ordered)
    }
    for spec in ordered:
        relation = spec.get("repeat_relation")
        if relation is None:
            continue
        occurrence_id = review_id_by_key[spec["key"]]
        alias_keys = sorted(
            spec.get("repeat_alias_keys", ()),
            key=source_order_by_key.__getitem__,
        )
        canonical_keys = sorted(
            spec.get("repeat_canonical_keys", ()),
            key=source_order_by_key.__getitem__,
        )
        evidence_keys = sorted(
            spec.get("repeat_evidence_keys", (spec["key"],)),
            key=source_order_by_key.__getitem__,
        )
        repeat_alias_specs.append(
            {
                "review_occurrence_id": occurrence_id,
                "relation": relation,
                "alias_anchor_review_occurrence_ids": [
                    review_id_by_key[key] for key in alias_keys
                ],
                "canonical_anchor_review_occurrence_ids": [
                    review_id_by_key[key] for key in canonical_keys
                ],
                "evidence_review_occurrence_ids": [
                    review_id_by_key[key] for key in evidence_keys
                ],
                "target_scope": "unresolved",
                "resolution_status": "preserved_for_global_resolution",
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
            "whole_page_review": "all_59_pages_including_empty_occurrence_pages",
            "span_granularity": "exact_utf8_lexeme_physical_line_or_source_block",
            "candidate_nonselection": "candidates_joined_only_after_source_rows_complete",
            "global_ids_assigned": False,
        },
        "page_review_rows": page_review_rows,
        "occurrence_specs": occurrence_specs,
        "local_anchor_specs": local_anchor_specs,
        "repeat_alias_specs": repeat_alias_specs,
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
        if (
            not annotation.REVIEW_PATH.is_file()
            or annotation.REVIEW_PATH.read_bytes() != raw
        ):
            raise ValueError("document 38 source review is missing or stale")
    else:
        annotation.REVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
        annotation.REVIEW_PATH.write_bytes(raw)
    counts = Counter(
        row["occurrence_kind"] for row in value["occurrence_specs"]
    )
    print(
        f"document 38 source review: {len(value['page_review_rows'])} pages, "
        f"{len(value['occurrence_specs'])} occurrences, {dict(sorted(counts.items()))}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
