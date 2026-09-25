"""Consistency checks for the exercise 3 (FRA to 68) specification, E1.

``docs/design/urban2010_fra68_comparison.md`` (E1) is read by the
exercise-3 runner through its machine-readable JSON block (section 21).
These tests hold that block (ratified, ``e1-ratified-1``, with Max's
rulings of 2026-09-24), the section 3 schedule table and the section 19
invented worked cases to the code (``populace_dynamics.fra68_track``) and
to the A1 template.  They use the document, statute arithmetic on
INVENTED amounts and the committed statutory capture's rates: no PSID
value, no model output and no comparator value.
"""

from __future__ import annotations

import copy
import json
import re
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from populace_dynamics import claiming
from populace_dynamics import scenario_benefits as sb
from populace_dynamics.cola_track_a import benefits as track_benefits
from populace_dynamics.cola_track_a.benefits import PiaRecord
from populace_dynamics.cola_track_a.runner import a1_parameter_block
from populace_dynamics.cola_track_a.statutory import captured_ssa_parameters
from populace_dynamics.engine.di_entitlement import fra_attainment_year
from populace_dynamics.estimates.cola_age_profile import (
    UNRATIFIED_MARKERS,
)
from populace_dynamics.fra68_track.benefits import ScenarioCalculator
from populace_dynamics.fra68_track.config import (
    E1_RULINGS,
    FRA68_LABELS,
    MAX_RULINGS,
    STATISTIC_ID,
    STYLIZED_RESPONSE_LABEL,
    FRA68Config,
)
from populace_dynamics.fra68_track.reform import (
    CONVERSION_CLAIM_EXCESS_MONTHS_EARLY_RULE,
    SCHEDULES,
    SPOUSE_EXCESS_MONTHS_EARLY_RULE,
    conversion_claim_excess_months_early,
    reform_parameters,
    spouse_excess_months_early,
    survivor_parameters,
)
from populace_dynamics.fra68_track.runner import (
    check_specification_for_registered_run,
    e1_parameter_block,
    specification_code_check,
)
from populace_dynamics.ss import benefits

SPEC_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "design"
    / "urban2010_fra68_comparison.md"
)
#: Pages 3-5 of the Urban text extraction (page 3 carries Figure 2; pages
#: 4-5 may summarize results): the draft may cite none of these lines.
URBAN_UNREAD_LINES = range(121, 359)


@pytest.fixture(scope="module")
def text() -> str:
    return SPEC_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def block(text: str) -> dict:
    blocks = re.findall(r"```json\n(.*?)```", text, flags=re.S)
    assert len(blocks) == 1, "the specification carries one JSON block"
    return json.loads(blocks[0])


def _section(text: str, heading: str) -> str:
    start = text.index(heading)
    end = text.find("\n## ", start + len(heading))
    return text[start:] if end == -1 else text[start:end]


def _table_rows(section: str) -> list[list[str]]:
    rows = []
    for line in section.splitlines():
        if not line.startswith("|") or set(line) <= set("|- "):
            continue
        rows.append([cell.strip() for cell in line.strip("|").split("|")])
    return rows


def _number(cell: str) -> Decimal:
    cleaned = cell.replace("−", "-").replace("$", "").replace(",", "")
    return Decimal(cleaned)


# --------------------------------------------------------------------------
# Status and governance
# --------------------------------------------------------------------------
def test_the_committed_e1_is_ratified_and_says_so(block, text):
    assert block["specification"] == "urban2010_fra68_exercise3"
    assert block["version"] == "e1-ratified-1"
    assert block["status"] == "ratified_frozen"
    # A7's fail-closed ratification test (with E1's extra marker) accepts
    # both header fields, and neither carries an A7 unratified marker.
    assert E1_RULINGS.unratified_fields(block) == []
    for name in ("status", "version"):
        assert not any(mark in block[name] for mark in UNRATIFIED_MARKERS)
    header = text.split("\n## 1.")[0]
    assert "ratified and frozen" in header
    assert "not ratified" not in header
    assert e1_parameter_block(SPEC_PATH) == block
    # The committed block is the one the one-shot entry point accepts.
    check_specification_for_registered_run(block, FRA68Config())
    # The builder boundary points to the builder-side restriction list,
    # which restricts Urban pages 3-4 (E1 referee required change 8).
    assert "RESTRICTED-FILES.md" in header
    assert "pages 3-4" in header


#: Section 21 ``decisions`` entries that are process rulings, not
#: configuration fields (d188 item (c); d196 item (5)).
_PROCESS_RULINGS = {
    "ratification_and_registration": (
        "ratify_by_merge_post_42_registration_run_one_shot",
        "d188",
        "(c)",
    ),
    "screening_lane_or_clarification_request": (
        "neither_before_the_one_shot_gaps_reported_as_results",
        "d196",
        "(5)",
    ),
}


def test_every_decision_field_records_maxs_ruling(block, text):
    assert "decisions_awaiting_max" not in block
    decisions = block["decisions"]
    assert decisions["ruled_by"] == "Max"
    assert decisions["ruled_on"] == "2026-09-24"
    assert set(decisions) == {
        "ruled_by",
        "ruled_on",
        *MAX_RULINGS,
        *_PROCESS_RULINGS,
    }
    # The block and the code record the same ruling, from the same record
    # and item, with the same declined alternatives and flags.
    for name, ruling in MAX_RULINGS.items():
        entry = decisions[name]
        assert entry["ruling"] == ruling["ruling"], name
        assert entry["decision_record"] == ruling["decision_record"], name
        assert entry["item"] == ruling["item"], name
        assert entry["declined"] == ruling["declined"], name
        assert entry.get("named_in_d188_as_filed", True) == ruling.get(
            "named_in_d188_as_filed", True
        ), name
        assert entry.get("carries_over") == ruling.get("carries_over"), name
        assert entry["decision_record"] in {"d188", "d196"}
    for name, (value, record, item) in _PROCESS_RULINGS.items():
        assert decisions[name]["ruling"] == value
        assert decisions[name]["decision_record"] == record
        assert decisions[name]["item"] == item
    # Every ruling adopts the default the configuration already uses.
    config = FRA68Config()
    for name, ruling in MAX_RULINGS.items():
        value = getattr(config, name)
        value = getattr(value, "value", value)
        value = list(value) if isinstance(value, tuple) else value
        assert value == ruling["ruling"], name
    # d196 rules by name on the fields d188 as filed does not name (E1
    # referee required change 7); the benefit computation years are
    # covered by d188 item (a), which does not name them either.
    assert {
        name
        for name, entry in decisions.items()
        if isinstance(entry, dict)
        and entry.get("named_in_d188_as_filed") is False
    } == {
        "survivor_reduction_span",
        "oracle_cola_horizon_extension_to_2030",
        "opening_stock_basis",
        "benefit_computation_years",
    }
    assert {
        name
        for name, entry in decisions.items()
        if isinstance(entry, dict) and entry.get("decision_record") == "d196"
    } == {
        "survivor_reduction_span",
        "oracle_cola_horizon_extension_to_2030",
        "opening_stock_basis",
        "rows",
        "screening_lane_or_clarification_request",
    }
    assert decisions["benefit_computation_years"]["covered_by"] == (
        "d188_run_exercise_3_exactly_like_track_a"
    )
    # Regression: the block recorded the statutory 415(b)(2) count as an
    # alternative Max declined, but no decision record put it to him.
    assert decisions["benefit_computation_years"]["declined"] == []
    section22 = _section(text, "## 22. Decisions (ruled by Max, 2026-09-24)")
    assert "records no declined alternative" in " ".join(section22.split())
    # Each ruled value is the one the block itself uses.
    assert decisions["survivor_reduction_span"]["ruling"] == (
        block["policy"]["survivor_reduction_span"]
    )
    assert decisions["opening_stock_basis"]["ruling"] == (
        block["amounts"]["opening_stock_basis"]
    )
    assert decisions["benefit_computation_years"]["ruling"] == (
        block["amounts"]["benefit_computation_years"]
    )
    assert decisions["primary_schedule_id"]["ruling"] == (
        block["primary_schedule"]
    )
    assert decisions["rows"]["ruling"] == list(block["rows"])
    # Section 22 names every ruled field with its record.
    section = _section(text, "## 22. Decisions (ruled by Max, 2026-09-24)")
    assert "d188" in section and "d196" in section
    assert "2026-09-24T21:44" in section
    for name in (*MAX_RULINGS, *_PROCESS_RULINGS):
        assert f"`{name}`" in section, name


def test_no_section_before_the_review_record_says_pending_or_awaiting(text):
    # Every decision field is ruled: sections 1-24 and the changelog carry
    # no "pending", "awaiting" or "awaits".  Section 25 records the reviews
    # as they happened, before the rulings.  The one exception names a
    # restricted file ("pending validation checks", the builder boundary's
    # summary of the restriction list).
    before, rest = text.split("\n## 25. Referee pass")
    changelog = rest[rest.index("\n## 26. Changelog") :]
    for part in (before, changelog):
        flat = " ".join(part.split())
        flat = flat.replace("pending validation checks", "")
        found = re.findall(r"\b(pending|awaiting|awaits)\b", flat, re.I)
        assert found == [], found


def _unratified(block: dict) -> dict:
    """The committed block under the last draft's header (INVENTED)."""
    edited = copy.deepcopy(block)
    edited["version"] = "e1-draft-7"
    edited["status"] = "draft_refereed_not_ratified"
    return edited


def test_an_unratified_or_partly_ruled_copy_is_still_refused(block):
    config = FRA68Config()
    with pytest.raises(ValueError, match="authorizes no real-data run"):
        check_specification_for_registered_run(_unratified(block), config)
    awaiting = copy.deepcopy(block)
    awaiting["decisions_awaiting_max"] = {"primary_schedule_id": {}}
    with pytest.raises(ValueError, match="awaiting Max"):
        check_specification_for_registered_run(awaiting, config)
    # A ruling on what d188 as filed names alone leaves d196's fields and
    # the covered computation years unruled.
    as_filed = copy.deepcopy(block)
    unnamed = [
        name
        for name, ruling in MAX_RULINGS.items()
        if ruling.get("named_in_d188_as_filed") is False
    ]
    for name in unnamed:
        del as_filed["decisions"][name]
    with pytest.raises(ValueError, match="records no ruling") as refused:
        check_specification_for_registered_run(as_filed, config)
    for name in unnamed:
        assert name in str(refused.value)
    for name in MAX_RULINGS:
        partial = copy.deepcopy(block)
        del partial["decisions"][name]
        with pytest.raises(ValueError, match="records no ruling"):
            check_specification_for_registered_run(partial, config)


def test_no_unread_urban_line_is_cited(text):
    cited = [
        (int(a), int(b or a))
        for a, b in re.findall(
            r"(?:urban-2010-reform-details\.txt|`):(\d+)(?:-(\d+))?", text
        )
    ]
    assert cited
    for first, last in cited:
        assert not set(range(first, last + 1)) & set(URBAN_UNREAD_LINES), (
            first,
            last,
        )


# --------------------------------------------------------------------------
# The block and the code
# --------------------------------------------------------------------------
def test_the_block_equals_the_code(block):
    check = specification_code_check(block, FRA68Config())
    assert check["consistent"], check["mismatches"]
    assert block["statistic_id"] == STATISTIC_ID
    assert block["labels"] == list(FRA68_LABELS)
    assert block["stylized_response_label"] == STYLIZED_RESPONSE_LABEL
    assert block["stylized_response_rows"] == ["F3", "F4"]
    for sid, schedule in SCHEDULES.items():
        record = schedule.as_dict()
        assert block["schedules"][sid]["rule"] == record["rule"]
        assert block["schedules"][sid]["months_from_year_turning_62"] == (
            record["months_from_year_turning_62"]
        )
    assert block["primary_schedule"] == "P3"
    assert block["claiming"]["C1"]["anchor_age"] == FRA68Config().c1_anchor_age
    # Not read by the specification check: held to the code's statements.
    assert block["claiming"]["spouse_excess_months_early"] == (
        SPOUSE_EXCESS_MONTHS_EARLY_RULE
    )
    assert block["amounts"]["conversion_claim_spouse_excess_months_early"] == (
        CONVERSION_CLAIM_EXCESS_MONTHS_EARLY_RULE
    )


#: The E1 section each tabulation convention cites, by its heading.
_E1_HEADINGS = {
    "7": "Statistic",
    "8": "Membership",
    "9": "Age",
    "10": "Benefit period",
    "11": "Benefit components, amount rules and rounding",
    "16": "Uncertainty",
    "18": "Registered rows",
}


def test_the_e1_tabulation_rulings_follow_the_block_and_cite_e1(block, text):
    # Regression: exercise-3 tabulations recorded A1's conventions, A1's
    # sections and A1's ratification.  E1's own table must name E1's
    # identifier, cite sections of E1 (whose headings are checked here)
    # and carry E1's proposed primaries and registered rows.
    assert E1_RULINGS.specification == block["specification"]
    assert E1_RULINGS.statistic_id == block["statistic_id"] == STATISTIC_ID
    assert E1_RULINGS.name == "E1"
    assert E1_RULINGS.section_field == "e1_section"
    assert "d188 item (c)" in E1_RULINGS.ratification
    assert "A1" not in E1_RULINGS.ratification
    headings = dict(re.findall(r"^## (\d+)\. (.+)$", text, flags=re.M))
    by_name = {}
    for ruling in E1_RULINGS.rulings:
        assert "a1_section" not in ruling
        cited = re.findall(r"section (\d+)", ruling["e1_section"])
        assert cited, ruling["parameter"]
        for number in cited:
            assert headings[number] == _E1_HEADINGS[number], number
        by_name[ruling["parameter"]] = ruling
    f0, rows = block["rows"]["F0"], block["rows"]
    assert by_name["headline_statistic"]["proposed_primary"] == f0["statistic"]
    assert by_name["headline_statistic"]["registered_alternatives"] == [
        rows["F5"]["statistic"]
    ]
    assert by_name["membership_basis"]["proposed_primary"] == (
        f0["membership_basis"]
    )
    # Section 7: scenario-specific membership, allowed to differ (C1, C2).
    assert by_name["allow_membership_difference"]["proposed_primary"] is True
    assert by_name["components"]["proposed_primary"] == f0["components"]
    assert by_name["components"]["registered_alternatives"] == [
        rows["F6"]["components"]
    ]
    # Section 10: no December-amount row (A1's R4) is registered.
    assert by_name["benefit_period"]["registered_alternatives"] == []
    assert not any("benefit_period" in row for row in list(rows.values())[1:])
    uncertainty = block["uncertainty"]
    assert by_name["draw_indices"]["proposed_primary"] == list(
        range(uncertainty["draws"])
    )
    assert by_name["draw_indices"]["proposed_primary"] == list(
        FRA68Config().draw_indices
    )
    assert by_name["floor_seeds"]["proposed_primary"] == (
        uncertainty["floor"]["seeds"]
    )
    assert "referee" in E1_RULINGS.extra_unratified_markers


def test_each_alternative_row_changes_one_field(block):
    rows = block["rows"]
    assert list(rows) == [f"F{k}" for k in range(9)]
    for row_id, row in rows.items():
        if row_id == "F0":
            continue
        changed = {key for key in row if key != "behavior"}
        assert len(changed) == 1, row_id
        assert row[next(iter(changed))] != rows["F0"][next(iter(changed))]


def test_carried_over_blocks_equal_a1(block):
    a1 = a1_parameter_block()
    assert block["template"]["version"] == a1["version"]
    for key in (
        "model",
        "run",
        "run_date",
        "trustees_vintage",
        "baseline",
        "outcome_year",
        "age_groups",
        "disability_included",
    ):
        assert block["target"][key] == a1["target"][key], key
    assert block["uncertainty"] == a1["uncertainty"]
    # A1's amount rules that E1 carries over (section 11), including the
    # two E1 referee required change 6 added.
    for key in (
        "pia_dime_floor_after_each_increase",
        "claim_age_factor_dime_floor_each_payment_year",
        "opening_stock_dime_floor",
        "opening_stock_basis",
        "opening_stock_under_worker_only_components",
        "gross_of_premiums_taxes_and_withholding",
        "gross_of_wep_gpo_and_disability_offset",
    ):
        assert block["amounts"][key] == a1["amounts"][key], key
    assert block["rows"]["F0"]["population"] == a1["rows"]["R0"]["population"]
    assert block["rows"]["F8"]["population"] == a1["rows"]["R6"]["population"]


# --------------------------------------------------------------------------
# Section 3: the schedule table
# --------------------------------------------------------------------------
def _statute_months(year_turning_62: int) -> int:
    """42 USC 416(l)(1)(C)-(E) and (l)(3)(B) for workers, by year of 62."""
    if year_turning_62 <= 2016:
        return 792
    if year_turning_62 <= 2021:
        return 792 + 2 * (year_turning_62 - 2016)
    return 804


def test_section_3_table_equals_the_statute_and_the_schedules(text):
    table = _table_rows(_section(text, "## 3. Policy"))
    rows = [row for row in table if row and row[0][:4].isdigit()]
    assert len(rows) == 14
    for row in rows:
        year = int(row[0][:4])
        baseline, p1, p2, p3 = (int(cell) for cell in row[2:6])
        assert baseline == _statute_months(year)
        for sid, value in zip(("P1", "P2", "P3"), (p1, p2, p3), strict=True):
            expected = SCHEDULES[sid].months_for_year_turning_62(year)
            assert value == (baseline if expected is None else expected)
        increases = [int(part) for part in row[6].split("/")]
        assert increases == [p1 - baseline, p2 - baseline, p3 - baseline]


# --------------------------------------------------------------------------
# Section 19: the invented worked cases, through the code
# --------------------------------------------------------------------------
class _A1Path:
    def __init__(self) -> None:
        self.rates = {
            int(year): float(value) / 100.0
            for year, value in a1_parameter_block()["rate_path"][
                "baseline"
            ].items()
        }

    def rate_for_determination_year(self, year: int) -> float:
        return self.rates[year]


def _computed_cases() -> list[tuple[Decimal, ...]]:
    cola = _A1Path()
    base = captured_ssa_parameters()
    reforms = {sid: reform_parameters(base, s) for sid, s in SCHEDULES.items()}
    out = []

    def worker(birth, age, sid):
        amounts, factors = [], []
        for params in (base, reforms[sid]):
            factor = claiming.benefit_factor(12 * age, birth, params)
            factors.append(factor)
            amounts.append(
                sb.monthly_benefit_path(
                    eligibility_pia=1000.0,
                    claim_age_factor=factor,
                    eligibility_year=birth + 62,
                    cola=cola,
                    horizon_year=2030,
                )[2030]
            )
        return amounts, factors

    for birth, age, sid in [
        (1966, 62, "P3"),
        (1963, 67, "P3"),
        (1954, 66, "P1"),
        (1954, 66, "P2"),
        (1954, 66, "P3"),
        (1950, 62, "P1"),
        (1950, 62, "P2"),
        (1950, 62, "P3"),
    ]:
        out.append(worker(birth, age, sid))
    worker_pia = sb.increased_pia_path(
        eligibility_pia=2000.0,
        eligibility_year=2026,
        cola=cola,
        horizon_year=2030,
    )
    spouse = [
        sb.spouse_excess_path(
            worker_pia_by_year=worker_pia,
            own_pia_by_year=None,
            months_early=max(0, params.fra_months(1966) - 744),
            entitlement_year=2028,
            params=params,
            horizon_year=2030,
        )[2030]
        for params in (base, reforms["P3"])
    ]
    out.append((spouse, [0.65, 0.60]))
    deceased = sb.increased_pia_path(
        eligibility_pia=1500.0,
        eligibility_year=2025,
        cola=cola,
        horizon_year=2030,
    )
    for entitled_at in (63, 60):
        amounts, factors = [], []
        for params in (base, reforms["P3"]):
            bundle = survivor_parameters(params, 1965)
            early = max(
                0,
                bundle.survivor_reduction_period_months
                - 12 * (entitled_at - 60),
            )
            factors.append(
                1 - 0.285 * early / bundle.survivor_reduction_period_months
            )
            amounts.append(
                sb.widow_benefit_path(
                    deceased_pia_by_year=deceased,
                    own_amount_by_year=None,
                    survivor_months_early=early,
                    deceased_claim_age_factor=1.0,
                    entitlement_year=1965 + entitled_at,
                    params=bundle,
                    horizon_year=2030,
                )[2030]
            )
        out.append((amounts, factors))
    return out


def test_section_19_worked_cases_equal_the_code(text):
    table = _table_rows(_section(text, "## 19. Invented worked cases"))
    rows = [row for row in table if row[0] != "Invented case"]
    computed = _computed_cases()
    assert len(rows) == len(computed) == 11
    for row, (amounts, factors) in zip(rows, computed, strict=True):
        baseline, reformed = _number(row[1]), _number(row[2])
        assert baseline == Decimal(f"{amounts[0]:.2f}"), row[0]
        assert reformed == Decimal(f"{amounts[1]:.2f}"), row[0]
        change = Decimal(str(round(100 * (amounts[1] / amounts[0] - 1), 4)))
        assert _number(row[3]) == change, row[0]
        unrounded = Decimal(str(round(100 * (factors[1] / factors[0] - 1), 4)))
        assert _number(row[4]) == unrounded, row[0]


_SPOUSE_CASE = re.compile(
    r"\*\*Spouse's excess under C2\*\*, spouse born (\d{4}) \(P3, D = "
    r"(\d+)\), whose own\s+claim at 62 in (\d{4}) starts the excess: "
    r"reform claim month (\d+)\s+\(entitled (\d{4})\), (\d+) - (\d+) = "
    r"(\d+) months early, as in the baseline\s+\((\d+) - (\d+) = (\d+)\): "
    r"factor ([0-9.]+) in both, ratio 1\."
)


def test_section_19_spouse_cases_under_c2_equal_the_code(text):
    # E1 referee required change 1: under C2 a moved spouse's excess keeps
    # its months early (the exact moved claim month, not its whole year).
    section = _section(text, "## 19. Invented worked cases")
    assert "Six further invented cases have no dollar amount" in section
    cases = _SPOUSE_CASE.findall(section)
    assert len(cases) == 2
    base = captured_ssa_parameters()
    p3 = reform_parameters(base, SCHEDULES["P3"])
    for case in cases:
        birth, increase, claim_year, month, entitled, fra, month_again = (
            int(value) for value in case[:7]
        )
        early, base_fra, base_month, base_early = (
            int(value) for value in case[7:11]
        )
        factor = Decimal(case[11])
        assert claim_year == birth + 62
        assert increase == p3.fra_months(birth) - base.fra_months(birth)
        assert month == month_again == 12 * 62 + increase
        assert entitled == birth + (6 + month) // 12
        assert fra == p3.fra_months(birth)
        assert base_fra == base.fra_months(birth) and base_month == 744
        worker_year = birth + 60
        assert (
            early
            == fra - month
            == spouse_excess_months_early(
                own_claim_month=month,
                worker_entitlement_year=worker_year,
                birth_year=birth,
                params=p3,
            )
        )
        assert (
            base_early
            == base_fra - base_month
            == (
                spouse_excess_months_early(
                    own_claim_month=base_month,
                    worker_entitlement_year=worker_year,
                    birth_year=birth,
                    params=base,
                )
            )
        )
        for months, params in ((early, p3), (base_early, base)):
            computed = 1 - benefits.spousal_early_reduction(months, params)
            assert Decimal(f"{computed:.2f}") == factor


_CONVERSION_CASE = re.compile(
    r"\*\*Converted spouse's excess\*\*, spouse born (\d{4}) \((P\d), D = "
    r"(\d+)\), converted\s+at FRA in (\d{4}) with the worker entitled "
    r"earlier, so the conversion\s+starts the excess: baseline (\d+) - "
    r"(\d+) = (\d+) months early \(Track A's\s+whole-year count\), reform "
    r"(\d+) - \((\d+) \+ (\d+)\) = (\d+) months early: factor\s+"
    r"([0-9.]+) in both, ratio 1\. `e1-draft-4` counted from the reform's "
    r"whole\s+conversion year, (\d{4}) \(month (\d+)\): (\d+) months "
    r"early, factor (\d+), \+([0-9.]+)\s+percent"
)


def test_section_19_converted_spouse_case_equals_the_code(text):
    # The review of e1-draft-4: a converted spouse's excess on its
    # conversion claim keeps Track A's baseline count in every scenario.
    section = _section(text, "## 19. Invented worked cases")
    (case,) = _CONVERSION_CASE.findall(section)
    birth, sid = int(case[0]), case[1]
    (
        increase,
        conversion,
        base_fra,
        base_month,
        base_early,
        fra,
        month,
        increase_again,
        early,
    ) = (int(value) for value in case[2:11])
    factor = Decimal(case[11])
    old_year, old_month, old_early, old_factor = (
        int(value) for value in case[12:16]
    )
    change = Decimal(case[16])
    base = captured_ssa_parameters()
    reform = reform_parameters(base, SCHEDULES[sid])
    assert (
        increase
        == increase_again
        == (reform.fra_months(birth) - base.fra_months(birth))
    )
    assert conversion == int(fra_attainment_year([birth], base)[0])
    assert base_fra == base.fra_months(birth) and fra == reform.fra_months(
        birth
    )
    assert base_month == month == 12 * (conversion - birth)
    for params, months in ((base, base_early), (reform, early)):
        assert months == conversion_claim_excess_months_early(
            conversion_claim_year=conversion,
            worker_entitlement_year=conversion - 5,
            birth_year=birth,
            baseline=base,
            params=params,
        )
    assert base_early == base_fra - base_month
    assert early == fra - (month + increase)
    computed = [
        1 - benefits.spousal_early_reduction(months, params)
        for months, params in ((base_early, base), (early, reform))
    ]
    assert computed[0] == computed[1]
    assert Decimal(f"{computed[0]:.6f}") == factor
    # e1-draft-4's rule: the reform's own whole conversion year.
    assert old_year == int(fra_attainment_year([birth], reform)[0])
    assert old_month == 12 * (old_year - birth)
    assert old_early == max(0, fra - old_month)
    old = 1 - benefits.spousal_early_reduction(old_early, reform)
    assert Decimal(str(old)) == old_factor
    assert Decimal(str(round(100 * (old / computed[0] - 1), 4))) == change


_MOVED_WORKER_CASE = re.compile(
    r"\*\*Spouse's excess under C1, started by the worker's moved "
    r"claim\*\*,\s+spouse born (\d{4}) \((P\d), D = (\d+)\) who claimed "
    r"at 62 in (\d{4}), worker born\s+(\d{4}) \(D = (\d+)\) who claimed "
    r"at (\d+) in (\d{4}), a claim C1 moves to month (\d+)\s+\(entitled "
    r"(\d{4})\): the spouse is (\d+) \+ (\d+) = (\d+) months old when "
    r"the\s+worker's moved entitlement starts, so (\d+) - (\d+) = (\d+) "
    r"months early,\s+against the baseline's (\d+) - (\d+) = (\d+): "
    r"factor ([0-9.]+) against ([0-9.]+),\s+-([0-9.]+) percent\. "
    r"`e1-draft-5` counted from the whole year (\d{4})\s+\(month (\d+)\): "
    r"(\d+) months early, factor ([0-9.]+), \+([0-9.]+) percent, above\s+"
    r"the baseline\."
)


def test_section_19_moved_worker_case_equals_the_code(text):
    # The review of e1-draft-5: a worker's claim C1 moved enters the
    # spouse's count at its exact month (baseline year plus the months
    # moved), not the whole reform year it falls in.
    section = _section(text, "## 19. Invented worked cases")
    (case,) = _MOVED_WORKER_CASE.findall(section)
    spouse_birth, sid = int(case[0]), case[1]
    (
        spouse_increase,
        spouse_claim,
        worker_birth,
        worker_increase,
        worker_age,
        worker_claim,
        month,
        entitled,
        spouse_age,
        moved,
        spouse_age_at_start,
        fra,
        start,
        early,
        base_fra,
        base_start,
        base_early,
    ) = (int(value) for value in case[2:19])
    factor, base_factor, cut = (Decimal(value) for value in case[19:22])
    old_year, old_month, old_early = (int(value) for value in case[22:25])
    old_factor, rise = Decimal(case[25]), Decimal(case[26])
    base = captured_ssa_parameters()
    reform = reform_parameters(base, SCHEDULES[sid])
    assert spouse_increase == reform.fra_months(
        spouse_birth
    ) - base.fra_months(spouse_birth)
    assert (
        worker_increase
        == moved
        == reform.fra_months(worker_birth) - base.fra_months(worker_birth)
    )
    assert spouse_claim == spouse_birth + 62
    assert worker_claim == worker_birth + worker_age > spouse_claim
    # C1 moves the worker's claim (age at least the anchor, 65).
    assert worker_age >= 65
    assert month == 12 * worker_age + worker_increase
    assert entitled == worker_birth + (6 + month) // 12
    assert spouse_age == 12 * (worker_claim - spouse_birth)
    assert start == spouse_age_at_start == spouse_age + moved
    assert fra == reform.fra_months(spouse_birth)
    assert base_fra == base.fra_months(spouse_birth)
    assert base_start == spouse_age
    assert (
        early
        == fra - start
        == spouse_excess_months_early(
            own_claim_month=12 * 62,
            worker_entitlement_year=worker_claim,
            birth_year=spouse_birth,
            params=reform,
            worker_claim_move_months=moved,
        )
    )
    assert (
        base_early
        == base_fra - base_start
        == spouse_excess_months_early(
            own_claim_month=12 * 62,
            worker_entitlement_year=worker_claim,
            birth_year=spouse_birth,
            params=base,
        )
    )
    computed = 1 - benefits.spousal_early_reduction(early, reform)
    base_computed = 1 - benefits.spousal_early_reduction(base_early, base)
    assert Decimal(f"{computed:.6f}") == factor
    assert Decimal(str(base_computed)) == base_factor
    assert Decimal(str(round(100 * (1 - computed / base_computed), 4))) == cut
    # e1-draft-5's rule: the whole reform year the moved claim falls in.
    assert old_year == entitled and old_month == 12 * (old_year - spouse_birth)
    assert (
        old_early
        == fra - old_month
        == spouse_excess_months_early(
            own_claim_month=12 * 62,
            worker_entitlement_year=entitled,
            birth_year=spouse_birth,
            params=reform,
        )
    )
    old = 1 - benefits.spousal_early_reduction(old_early, reform)
    assert Decimal(f"{old:.6f}") == old_factor
    assert Decimal(str(round(100 * (old / base_computed - 1), 4))) == rise
    assert old_early < base_early < early


# --------------------------------------------------------------------------
# Sections 12 and 13: the review of e1-draft-6
# --------------------------------------------------------------------------
def test_section_12_credit_window_row_equals_the_oracle(text):
    # The oracle accrues credits for at most max_delayed_months (48);
    # 402(w)(2)(A) counts every month from the retirement age to the month
    # before 70, which is longer only for workers born 1938-1942.
    section = _section(text, "## 12. Named omitted deltas")
    assert "Credit window of cohorts born 1938-1942 (oracle)" in section
    assert "58, 56, 54, 52 and 50 months for workers born 1938-1942" in (
        section
    )
    base = captured_ssa_parameters()
    assert base.max_delayed_months == 48
    windows = []
    for birth in range(1938, 1972):
        window = 12 * 70 - base.fra_months(birth)
        rate = base.delayed_credit_annual_rate(birth)
        credit = benefits.delayed_credit(window, birth, base)
        if window > 48:
            windows.append(window)
            assert credit == pytest.approx(48 / 12 * rate), birth
            assert birth <= 1942
        else:
            assert credit == pytest.approx(window / 12 * rate), birth
    assert windows == [58, 56, 54, 52, 50]
    # The reform does not reach these cohorts (they turned 62 before 2010).
    for schedule in SCHEDULES.values():
        reform = reform_parameters(base, schedule)
        for birth in range(1938, 1943):
            assert reform.fra_months(birth) == base.fra_months(birth)


def test_section_13_death_boundary_equals_the_code(text, monkeypatch):
    # E1 section 13: a worker who dies in or before the reform claim year
    # is a never-entitled decedent in the reform scenario, as
    # ScenarioCalculator._decedent does (the moved entitlement year at or
    # after the death year).  e1-draft-6 said "before" only.  INVENTED.
    section = _section(text, "## 13. Behavior (claiming)")
    flat = " ".join(section.split())
    assert "A worker who dies in or before the reform claim year" in flat
    assert "dies before the reform claim year" not in flat
    record = PiaRecord(
        person_id=1,
        kind="retired",
        component="retired_worker",
        basis=sb.EligibilityBasis.AGE_62,
        eligibility_year=2022,
        entitlement_year=2027,
        eligibility_pia=1000.0,
        claim_age_factor=0.8,
        level_basis="invented",
    )
    monkeypatch.setattr(
        track_benefits._Calculator,
        "deceased_record",
        lambda self, person_id: record,
    )
    calculator = object.__new__(ScenarioCalculator)
    calculator.statics = pd.DataFrame({"birth_year": [1960]}, index=[1])
    outcomes = {}
    for death in (2026, 2027, 2028):
        calculator.lookups = SimpleNamespace(
            death_year=lambda person_id, _d=death: _d
        )
        decedent, undone = calculator._decedent(1)
        outcomes[death] = (decedent.kind, undone)
    assert outcomes == {
        2026: ("deceased_unentitled", True),
        2027: ("deceased_unentitled", True),
        2028: ("retired", False),
    }
