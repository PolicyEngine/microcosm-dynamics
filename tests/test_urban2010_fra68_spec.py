"""Consistency checks for the exercise 3 (FRA to 68) specification draft.

``docs/design/urban2010_fra68_comparison.md`` (E1) is read by the
exercise-3 runner through its machine-readable JSON block (section 21).
These tests hold that block, the section 3 schedule table and the section
19 invented worked cases to the code (``populace_dynamics.fra68_track``)
and to the A1 template.  They use the document, statute arithmetic on
INVENTED amounts and the committed statutory capture's rates: no PSID
value, no model output and no comparator value.
"""

from __future__ import annotations

import json
import re
from decimal import Decimal
from pathlib import Path

import pytest

from populace_dynamics import claiming
from populace_dynamics import scenario_benefits as sb
from populace_dynamics.cola_track_a.runner import a1_parameter_block
from populace_dynamics.cola_track_a.statutory import captured_ssa_parameters
from populace_dynamics.estimates.cola_age_profile import (
    UNRATIFIED_MARKERS,
)
from populace_dynamics.fra68_track.config import (
    E1_RULINGS,
    FRA68_LABELS,
    PENDING_DECISIONS,
    STATISTIC_ID,
    STYLIZED_RESPONSE_LABEL,
    FRA68Config,
)
from populace_dynamics.fra68_track.reform import (
    SCHEDULES,
    SPOUSE_EXCESS_MONTHS_EARLY_RULE,
    reform_parameters,
    spouse_excess_months_early,
    survivor_parameters,
)
from populace_dynamics.fra68_track.runner import (
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
def test_the_draft_is_not_ratified_and_says_so(block, text):
    assert block["specification"] == "urban2010_fra68_exercise3"
    # A7's fail-closed ratification test (with E1's extra marker) refuses
    # both header fields, and each also carries an A7 unratified marker.
    assert E1_RULINGS.unratified_fields(block) == ["status", "version"]
    for name in ("status", "version"):
        assert any(mark in block[name] for mark in UNRATIFIED_MARKERS)
    assert "not ratified" in text.split("\n## 1.")[0]
    assert e1_parameter_block(SPEC_PATH) == block
    # The builder boundary points to the builder-side restriction list,
    # which restricts Urban pages 3-4 (E1 referee required change 8).
    header = text.split("\n## 1.")[0]
    assert "RESTRICTED-FILES.md" in header
    assert "pages 3-4" in header


def test_every_pending_decision_is_listed_with_the_code_default(block, text):
    awaiting = block["decisions_awaiting_max"]
    for name, decision in PENDING_DECISIONS.items():
        assert awaiting[name]["proposed_default"] == (
            decision["proposed_default"]
        ), name
        assert awaiting[name]["decision_record"] == "d188"
    assert set(awaiting) == {
        *PENDING_DECISIONS,
        "ratification_and_registration",
    }
    # E1 referee required change 7: the choices d188 as filed does not
    # name are fields of their own, flagged in the block and the code.
    for name, decision in PENDING_DECISIONS.items():
        assert awaiting[name].get("named_in_d188_as_filed", True) == (
            decision.get("named_in_d188_as_filed", True)
        ), name
        assert awaiting[name].get("carries_over") == decision.get(
            "carries_over"
        ), name
    assert {
        name
        for name, entry in awaiting.items()
        if entry.get("named_in_d188_as_filed") is False
    } == {
        "survivor_reduction_span",
        "oracle_cola_horizon_extension_to_2030",
        "opening_stock_basis",
    }
    assert awaiting["survivor_reduction_span"]["proposed_default"] == (
        block["policy"]["survivor_reduction_span"]
    )
    assert awaiting["opening_stock_basis"]["proposed_default"] == (
        block["amounts"]["opening_stock_basis"]
    )
    decisions = _section(text, "## 22. Decisions awaiting Max")
    assert "d188" in decisions and "open" in decisions


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
    # Not read by the specification check: held to the code's statement.
    assert block["claiming"]["spouse_excess_months_early"] == (
        SPOUSE_EXCESS_MONTHS_EARLY_RULE
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
    assert "Four further invented cases have no dollar amount" in section
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
