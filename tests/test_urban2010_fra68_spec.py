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
from populace_dynamics.fra68_track.config import (
    FRA68_LABELS,
    PENDING_DECISIONS,
    STATISTIC_ID,
    STYLIZED_RESPONSE_LABEL,
    FRA68Config,
)
from populace_dynamics.fra68_track.reform import (
    SCHEDULES,
    reform_parameters,
    survivor_parameters,
)
from populace_dynamics.fra68_track.runner import (
    UNRATIFIED_MARKERS,
    e1_parameter_block,
    specification_code_check,
)

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
    for name in ("status", "version"):
        assert any(mark in block[name] for mark in UNRATIFIED_MARKERS)
    assert "not ratified" in text.split("\n## 1.")[0]
    assert e1_parameter_block(SPEC_PATH) == block


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
        "trustees_vintage",
        "baseline",
        "outcome_year",
        "age_groups",
        "disability_included",
    ):
        assert block["target"][key] == a1["target"][key], key
    assert block["uncertainty"] == a1["uncertainty"]
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
