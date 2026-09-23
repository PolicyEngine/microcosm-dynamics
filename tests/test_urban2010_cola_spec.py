"""Consistency checks for the exercise 1 COLA specification draft.

``docs/design/urban2010_cola_comparison.md`` is read by downstream lanes
through its machine-readable JSON block (§21).  These tests hold that
block, the invented worked cases of §19 and the TR2008 Table V.C1
transcription of §4 to one another.  They use only the document itself,
statute arithmetic on invented amounts, and constants transcribed here
from the sources the document cites (TR2008 Table V.C1, the PSID setup
labels, the ``proposed-1`` field list): no PSID value, no model output
and no comparator value.
"""

from __future__ import annotations

import json
import re
from decimal import ROUND_FLOOR, Decimal
from fractions import Fraction
from pathlib import Path

import pytest

SPEC_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "design"
    / "urban2010_cola_comparison.md"
)

# TR2008 Table V.C1, intermediate assumptions, printed p. 102: OASDI
# benefit increases (percent) by calendar year of the December increase.
TR2008_V_C1_INTERMEDIATE = {
    2008: Decimal("2.7"),
    2009: Decimal("2.5"),
    **{year: Decimal("2.8") for year in range(2010, 2018)},
}

INVENTED_PIA = Decimal("1000.00")

# PSID setup-file labels (IND2023ER.sas): the cross-section weight and the
# interview (family-unit) number of each registered opening wave.
PSID_WAVE_LABELS = {
    2009: {"weight": "ER34046", "family_unit_id": "ER34001"},
    2011: {"weight": "ER34155", "family_unit_id": "ER34101"},
}

# The ``required_unresolved`` fields of the ``proposed-1`` specification
# (EVID/parallel-oasdi-20260920/deliverables/dynasim-specification.md).
PROPOSED_1_REQUIRED_UNRESOLVED = frozenset(
    {
        "law_cutoff_and_historical_versions",
        "population_vintage_coverage_and_weights",
        "trustees_alternative_and_parameter_splice",
        "complete_dated_parameter_sequences",
        "first_effective_and_payment_months",
        "exposure_and_existing_beneficiary_rules",
        "floor_or_verified_nonbinding_condition",
        "aggregation_formula",
        "beneficiary_membership_and_zero_treatment",
        "age_reference_and_decedent_selection",
        "benefit_period_and_partial_year_rules",
        "benefit_components_offsets_and_rounding",
        "interacting_indexation",
        "behavioral_configuration",
        "comparator_series_precision_and_provenance",
    }
)

# Page 3 of the Urban text extraction (form feeds open pages 3 and 4 at
# lines 121 and 208); it carries Figure 2.
URBAN_PAGE_3_LINES = range(121, 208)


@pytest.fixture(scope="module")
def text() -> str:
    return SPEC_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def block(text: str) -> dict:
    blocks = re.findall(r"```json\n(.*?)```", text, flags=re.S)
    assert len(blocks) == 1, "the specification carries one JSON block"
    return json.loads(blocks[0])


@pytest.fixture(scope="module")
def rates(block: dict) -> dict[int, Decimal]:
    path = block["rate_path"]["baseline"]
    return {int(year): Decimal(str(value)) for year, value in path.items()}


def _row(block: dict, name: str) -> dict:
    """R0 with the named alternative row's overrides applied."""
    merged = dict(block["rows"]["R0"])
    merged.update(block["rows"][name])
    return merged


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
    return rows[1:]  # drop the header row


def _number(cell: str) -> Decimal:
    cleaned = cell.replace("\u2212", "-").replace("$", "").replace(",", "")
    return Decimal(cleaned)


def _floor_to_dime(amount: Decimal) -> Decimal:
    return (amount * 10).to_integral_value(rounding=ROUND_FLOOR) / 10


def _dime_floored_pia(
    rates: dict[int, Decimal],
    clock: int,
    first: int,
    last: int,
    *,
    reform: bool,
) -> Decimal:
    pia = INVENTED_PIA
    for year in range(clock, last + 1):
        rate = rates[year]
        if reform and year >= first:
            rate -= 1
        pia = _floor_to_dime(pia * (1 + rate / 100))
    return pia


def _unrounded_change(
    rates: dict[int, Decimal], start: int, last: int
) -> Decimal:
    ratio = Fraction(1)
    for year in range(start, last + 1):
        rate = Fraction(rates[year]) / 100
        ratio *= (1 + rate - Fraction(1, 100)) / (1 + rate)
    value = (ratio - 1) * 100
    return Decimal(value.numerator) / Decimal(value.denominator)


def test_header_version_matches_block(text: str, block: dict) -> None:
    header = re.search(r"version `([^`]+)`", text)
    assert header is not None
    assert header.group(1) == block["version"]
    assert block["version"] == "a1-ratified-1"
    # Ratified by merging #452 under Max's 2026-09-23 authorization.
    assert block["status"] == "ratified_frozen"
    assert "ratified and frozen" in " ".join(text.split("## 1.")[0].split())


def test_changelog_records_the_current_version(text: str, block: dict) -> None:
    changelog = _section(text, "## 26. Changelog")
    assert f"`{block['version']}` (2026-09-23)" in changelog
    assert "`a1-draft-2` (2026-09-22)" in changelog


def test_rate_path_matches_tr2008_transcription(
    block: dict, rates: dict[int, Decimal]
) -> None:
    path = block["rate_path"]
    assert sorted(rates) == list(range(2008, 2031))
    assert path["published_through"] == 2017
    assert path["reconstructed_from"] == 2018
    for year, value in TR2008_V_C1_INTERMEDIATE.items():
        assert rates[year] == value, year
    # §4 reconstruction: the 2.8 percent intermediate ultimate CPI rate.
    assert {rates[year] for year in range(2018, 2031)} == {Decimal("2.8")}
    assert path["reform_delta_percentage_points"] == -1.0
    assert path["realized_series_substitution"] == "forbidden"


@pytest.mark.parametrize("row_name", ["R0", "R1"])
def test_reduced_rates_stay_positive_and_match_declared_minimum(
    block: dict, rates: dict[int, Decimal], row_name: str
) -> None:
    row = _row(block, row_name)
    first = row["first_reduced_determination_year"]
    reduced = [rates[year] - 1 for year in range(first, 2031)]
    assert min(reduced) > 0
    declared = block["rate_path"]["floor"][
        f"min_reduced_rate_{row_name.lower()}"
    ]
    assert min(reduced) == Decimal(str(declared))
    assert block["rate_path"]["floor"]["binding_on_path"] is False


def test_alternative_rows_override_only_headline_fields(block: dict) -> None:
    headline = block["rows"]["R0"]
    alternatives = {k: v for k, v in block["rows"].items() if k != "R0"}
    assert sorted(alternatives) == ["R1", "R2", "R3", "R4", "R5", "R6"]
    for name, overrides in alternatives.items():
        assert set(overrides) <= set(headline), name
        for key, value in overrides.items():
            assert value != headline[key], (name, key)
    # R4 changes one field (the benefit period) and its derived horizon.
    assert set(alternatives["R4"]) == {
        "benefit_period",
        "last_determination_year",
    }
    for name in ("R1", "R2", "R3", "R5", "R6"):
        assert len(alternatives[name]) == 1, name


def test_every_row_shares_the_annual_benefit_scale(
    block: dict, text: str
) -> None:
    for name in block["rows"]:
        assert _row(block, name)["benefit_scale"] == (
            "annual_12_times_monthly"
        )
    benefit_period = _section(text, "## 10. Benefit period")
    assert "12 times the monthly benefit for December 2030" in (
        " ".join(benefit_period.split())
    )


def test_counts_follow_first_and_last_determination_years(
    block: dict,
) -> None:
    def count(name: str, clock: int) -> int:
        row = _row(block, name)
        start = max(clock, row["first_reduced_determination_year"])
        return len(range(start, row["last_determination_year"] + 1))

    assert count("R0", 2009) == 21
    assert count("R1", 2009) == 20
    assert count("R4", 2009) == 22


def test_dime_floored_worked_cases_reproduce(
    block: dict, text: str, rates: dict[int, Decimal]
) -> None:
    section = _section(text, "## 19. Invented worked cases")
    table = section.split("Invented clock cases")[0]
    rows = _table_rows(table)
    assert len(rows) == 8
    for cells in rows:
        clock = int(cells[0])
        label = cells[1]
        if label.startswith("R4"):
            names = ["R4"]
        elif label == "R0 or R1":
            names = ["R0", "R1"]
        else:
            names = [label]
        for name in names:
            row = _row(block, name)
            first = row["first_reduced_determination_year"]
            last = row["last_determination_year"]
            count = len(range(max(clock, first), last + 1))
            assert count == int(cells[2]), (clock, name)
            base = _dime_floored_pia(rates, clock, first, last, reform=False)
            reform = _dime_floored_pia(rates, clock, first, last, reform=True)
            assert base == _number(cells[3]), (clock, name)
            assert reform == _number(cells[4]), (clock, name)
            floored = ((reform / base - 1) * 100).quantize(Decimal("0.0001"))
            assert floored == _number(cells[5]), (clock, name)
            unrounded = _unrounded_change(
                rates, max(clock, first), last
            ).quantize(Decimal("0.0001"))
            assert unrounded == _number(cells[6]), (clock, name)


def test_invented_clock_cases_reproduce(
    block: dict, text: str, rates: dict[int, Decimal]
) -> None:
    section = _section(text, "## 19. Invented worked cases")
    rows = _table_rows(section.split("Invented clock cases")[1])
    assert len(rows) == 3
    headline = _row(block, "R0")
    first = headline["first_reduced_determination_year"]
    last = headline["last_determination_year"]

    def years(cell: str) -> list[int]:
        return [int(value) for value in re.findall(r"\b\d{4}\b", cell)]

    def numbers(cell: str) -> list[Decimal]:
        return [_number(part) for part in cell.split(" or ")]

    for cells in rows:
        clock = years(cells[1])[0]
        start = max(clock, first)
        assert len(range(start, last + 1)) == int(cells[2]), cells[0]
        assert _unrounded_change(rates, start, last).quantize(
            Decimal("0.0001")
        ) == _number(cells[3]), cells[0]
        entitlements = years(cells[4])
        counts = [int(value) for value in cells[5].split(" or ")]
        changes = numbers(cells[6])
        assert len(entitlements) == len(counts) == len(changes)
        for entitle, expected_count, expected_change in zip(
            entitlements, counts, changes, strict=True
        ):
            start_r2 = max(first, entitle)
            assert len(range(start_r2, last + 1)) == expected_count
            assert (
                _unrounded_change(rates, start_r2, last).quantize(
                    Decimal("0.0001")
                )
                == expected_change
            ), cells[0]


#: Max's rulings of 2026-09-23 (decision records d074 and d075): each
#: adopts the default the plan (section 6) or the referee question proposed.
MAX_RULINGS_2026_09_23 = {
    "claim_class": ("track_a_reported_not_gated_psid_oracle", "d074"),
    "oracle_cola_horizon_extension_to_2030": (True, "d074"),
    "di_benefit_level": ("disclosed_oracle_approximation", "d074"),
    "acceptance_rule": (None, "d074"),
    "page_3_run_metadata_contact": ("accepted_as_disclosed", "d075"),
    "opening_stock_basis": ("fixed_at_opening_year", "d075"),
}


def test_decisions_record_max_rulings(block: dict, text: str) -> None:
    assert "decisions_awaiting_max" not in block
    assert "awaiting_max" not in json.dumps(block)
    decisions = dict(block["decisions"])
    assert decisions.pop("ruled_by") == "Max"
    assert decisions.pop("ruled_on") == "2026-09-23"
    assert set(decisions) == set(MAX_RULINGS_2026_09_23)
    for name, (ruling, record) in MAX_RULINGS_2026_09_23.items():
        decision = decisions[name]
        assert decision["ruling"] == ruling, name
        assert decision["decision_record"] == record, name
        assert decision["ruling"] not in decision["declined"], name
    # The opening-stock ruling is the amounts rule the block applies.
    assert block["amounts"]["opening_stock_basis"] == (
        decisions["opening_stock_basis"]["ruling"]
    )
    section = _section(text, "## 22. Decisions (ruled by Max, 2026-09-23)")
    for record in ("d074", "d075"):
        assert record in section
    assert "## 22. Decisions awaiting Max" not in text


def test_uncertainty_fails_closed(block: dict) -> None:
    uncertainty = block["uncertainty"]
    assert uncertainty["draws"] == 20
    assert uncertainty["draw_seed_base"] == 5200
    assert uncertainty["draw_summary_requires_all_draws_defined"] is True
    floor = uncertainty["floor"]
    assert floor["seeds"] == [0, 1, 2, 3, 4]
    assert floor["summary"] == ["mean", "sample_sd"]
    assert floor["min_usable_seeds"] >= 2


def _year_span(cell: str) -> list[int]:
    bounds = [int(value) for value in re.findall(r"\d{4}", cell)]
    return list(range(bounds[0], bounds[-1] + 1))


def test_rate_table_matches_block(
    block: dict, text: str, rates: dict[int, Decimal]
) -> None:
    section = _section(text, "## 4. Rate path")
    rows = _table_rows(section.split("**Reconstruction for")[0])
    covered: list[int] = []
    for cells in rows:
        years = _year_span(cells[0])
        baseline = _number(cells[3])
        reforms = {
            "R0": _number(cells[5].strip("*")),
            "R1": _number(cells[6].strip("*")),
        }
        for year in years:
            covered.append(year)
            assert rates[year] == baseline, year
            for name, value in reforms.items():
                first = _row(block, name)["first_reduced_determination_year"]
                expected = baseline - 1 if year >= first else baseline
                assert value == expected, (year, name)
    assert covered == sorted(rates)


def test_population_horizons_reach_the_outcome_year(block: dict) -> None:
    outcome_year = block["target"]["outcome_year"]
    youngest = min(low for low, _ in block["target"]["age_groups"])
    for name in block["rows"]:
        population = _row(block, name)["population"]
        assert population["start_year"] == population["wave"] - 1, name
        assert (
            population["start_year"] + population["periods"] == outcome_year
        ), name
        assert population["born_max"] == outcome_year - youngest, name


def test_floor_split_unit_follows_each_rows_opening_wave(block: dict) -> None:
    """R6's 2009-wave universe includes people with no 2011 family unit.

    The floor therefore splits on each row's own opening-wave interview
    number, never on a wave fixed across rows.
    """
    floor = block["uncertainty"]["floor"]
    assert floor["split_unit"] == "population_family_unit_id_of_the_row"
    assert not re.search(r"\d{4}", floor["split_unit"])
    for name in block["rows"]:
        population = _row(block, name)["population"]
        labels = PSID_WAVE_LABELS[population["wave"]]
        assert population["weight"] == labels["weight"], name
        assert population["family_unit_id"] == labels["family_unit_id"], name


def test_opening_stock_amount_rules_are_explicit(block: dict) -> None:
    amounts = block["amounts"]
    assert amounts["opening_stock_dime_floor"] is False
    assert amounts["opening_stock_basis"] == "fixed_at_opening_year"
    assert amounts["opening_stock_under_worker_only_components"] == (
        "whole_observed_amount_kept_if_a3_classifies_a_worker_benefit"
    )
    assert amounts["gross_of_premiums_taxes_and_withholding"] is True
    assert amounts["gross_of_wep_gpo_and_disability_offset"] is True


def test_resolution_map_lists_every_proposed_1_field(text: str) -> None:
    section = _section(text, "## 20. Resolution map")
    table = section.split("**Where this draft adds")[0]
    fields = [cells[0].strip("`") for cells in _table_rows(table)]
    assert len(fields) == len(set(fields))
    assert set(fields) == PROPOSED_1_REQUIRED_UNRESOLVED


def test_page_3_contact_is_fully_disclosed(text: str) -> None:
    """Every page-3 line of the Urban extraction that §2 cites is disclosed."""
    sources = _section(text, "## 2. Sources")
    urban_row = next(
        cells
        for cells in _table_rows(sources.split("**Not opened")[0])
        if cells[0].startswith("Urban (2010)")
    )
    cited: set[int] = set()
    for low, high in re.findall(r"(\d+)(?:–(\d+))?", urban_row[3]):
        start = int(low)
        cited.update(range(start, int(high or start) + 1))
    page_3 = sorted(cited & set(URBAN_PAGE_3_LINES))
    assert page_3, "the draft cites page-3 lines; the test must see them"
    marker = "**Disclosure: page-3 text.**"
    assert marker in sources, "§2 must disclose the page-3 contact"
    disclosure = " ".join(sources.split(marker)[1].split())
    for line in page_3:
        assert re.search(
            rf"lines? (?:\d+–)?{line}\b|lines? {line}–", disclosure
        ), line
    header = " ".join(text.split("## 1. Target")[0].split())
    assert "page-3 *text*" in header
    assert "lines 125–126" in header and "line 160" in header
