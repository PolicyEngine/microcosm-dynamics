"""Statutory conformance: captured insured-status rules and source tables.

Published examples and invented cases only; no population, behavioral or
forecast claim. Missing linked POMS exhibits are recorded explicitly and
are not represented as captured charts.
"""

from __future__ import annotations

import ast
import hashlib
import html
import json
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime
from decimal import Decimal
from fractions import Fraction
from functools import cache
from pathlib import Path

import pytest
import yaml

DATA = Path(__file__).with_name("data") / "track_b"
SOURCES = DATA / "insured_status_sources"


@cache
def manifest():
    return json.loads((SOURCES / "manifest.json").read_text())


@cache
def registry():
    return yaml.safe_load((DATA / "insured_status_examples.yaml").read_text())


@cache
def source_text(source_id):
    source = next(s for s in manifest()["sources"] if s["id"] == source_id)
    text = (SOURCES / source["file"]).read_text()
    if source["file"].endswith((".html", ".xml")):
        text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", text)
        text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    text = text.replace("\u200b", " ").replace("’", "'")
    return " ".join(text.split())


# Each retained capture has a specific rule or documentary-purpose quote.
# The two exhibit shells are retained to pin exactly what is unavailable.
RULE_QUOTES = {
    "poms_rs_00301_000_toc": [
        "Retirement, Survivors and Disability Requirements",
        "RS 00301.800 Quarters of Coverage Requirements - Exhibit",
    ],
    "poms_rs_00301_101": [
        "For certain benefits, the QCs must be earned within a specific "
        "time frame.",
    ],
    "poms_rs_00301_102": [
        "Section 211 of the SSPA applies to an alien worker whose Social "
        "Security Number (SSN) was first assigned on or after January 1, "
        "2004.",
    ],
    "poms_rs_00301_105": [
        "A NH needs at least 6 QCs and no more than 40 QCs to meet fully "
        "insured status.",
        "In determining the number of years, do not count any year if "
        "part or all of that year is included in a period of disability "
        "if entitlement or a higher benefit would result.",
    ],
    "poms_rs_00301_106": [
        "Do not use QCs earned before 01/01/84 for deemed fully insured "
        "status.",
    ],
    "poms_rs_00301_107": [
        "Contact the employer to establish that deemed fully insured "
        "status does exist.",
    ],
    "poms_rs_00301_110": [
        "The 13-quarter period ending with the quarter of death;",
        "An intervening period of disability may extend the 13-quarter "
        "period during which the six QC's necessary for a currently "
        "insured status must be acquired.",
    ],
    "poms_rs_00301_120": [
        "Have at least 20 QC's during a 40 quarter period ending with "
        "the quarter the waiting period begins;",
        "When there are two or more prior periods of disability, either "
        "all must be disregarded or all must be used when determining "
        "insured status and benefit amount.",
    ],
    "poms_rs_00301_122": [
        "Cash benefits are not payable.",
    ],
    "poms_rs_00301_130": [
        "Have at least 20 QC's in a period of 40 consecutive calendar "
        "quarters ending with that quarter;",
    ],
    "poms_rs_00301_131": [
        "For freeze-insured status, include quarters of coverage based "
        "on certain RR compensation or MS credits that are not "
        "creditable for other Retirement, Survivors, and Disability "
        "Insurance purposes.",
    ],
    "poms_rs_00301_132": [
        "Do not use a freeze period if it would cause a denial of or "
        "reduced benefits.",
    ],
    "poms_rs_00301_140": [
        "Are under a disability which began before the quarter in which "
        "they attained or would attain age 31;",
        "If the number of elapsed quarters after age 21 is an odd "
        "number, subtract one elapsed quarter from the total elapsed "
        "quarters.",
    ],
    "poms_rs_00301_147": [
        "Had a prior period of disability (PPD) established before age "
        "31 and met only the special insured status requirements;",
    ],
    "poms_rs_00301_148": [
        "DLI is the last day in the last quarter when disability "
        "insured status is met.",
        "If full retirement age (FRA) attainment is involved, the DLI "
        "is the last day of the quarter before the quarter of FRA "
        "attainment.",
    ],
    "poms_rs_00301_149": [
        "See OS 15020.220 for SSA-1164, Worksheet – Special Insured Status",
    ],
    "poms_rs_00301_150": [
        "For benefits payable January 1973 or later, a statutorily "
        "blind worker no longer needs to meet a 20/40 or special insured "
        "status test.",
    ],
    "poms_rs_00301_160": [
        "Meeting the requirements for a freeze only is not sufficient "
        "to qualify for Medicare.",
    ],
    "poms_rs_00301_161": [
        "The reduction is effective 01/94 or, if later, the month after "
        "the month an individual receives the 30th QC.",
    ],
    "poms_rs_00301_200": [
        "For 1978, the law specifically set the increment amount at $250.",
    ],
    "poms_rs_00301_210": [
        "Credit a QC (maximum of 4) for each increment of total earnings "
        "credited to the year.",
    ],
    "poms_rs_00301_220": [
        "the number of months in each calendar year that are completely "
        "included within the taxable year.",
    ],
    "poms_rs_00301_230": [
        "Assignment of QCs is flexible.",
        "We determine QCs by the amount of earnings credited to a "
        "calendar year and assign them to the quarters most "
        "advantageous to the NH.",
    ],
    "poms_rs_00301_240": [
        "Do not count a quarter as more than one QC.",
        "Except for the first and last such quarters, any quarter of "
        "which any portion is included in a period of disability "
        "cannot be a QC.",
        "A future quarter is a quarter that has not yet commenced "
        "and; therefore, cannot be a QC.",
    ],
    "poms_rs_00301_250": [
        "The following chart contains increment amounts for the years "
        "shown.",
    ],
    "poms_rs_00301_301": [
        "SSA credits QCs on wages paid to an individual after 1936, "
        "or on SEI for taxable years beginning after 1950.",
    ],
    "poms_rs_00301_310": [
        "If the NH had more than one employer, it is only necessary "
        "that the total wages from all employers is $50 or more.",
    ],
    "poms_rs_00301_315": [
        "The simplified method does not apply to disability claims.",
    ],
    "poms_rs_00301_320": [
        "$400 or more paid in a calendar year-all four quarters are QCs;",
    ],
    "poms_rs_00301_325": [
        "We credit agricultural labor QCs in 1951 through 1954 as "
        "regular wage QCs.",
    ],
    "poms_rs_00301_340": [
        "We credit SEI equally to each quarter of the calendar year.",
    ],
    "poms_rs_00301_345": [
        "If a number holder (NH) has maximum creditable earnings in a "
        "year, all quarters in that year are QCs.",
        "$10,800 in a TY beginning after 1972 and before 1974;",
    ],
    "poms_rs_00301_350": [
        "The Railroad Retirement Act contains a table for computing "
        "compensation for QCs before 1978.",
    ],
    "poms_rs_00301_470": [
        "a WWII veteran who separated from active military service "
        "before July 27, 1951, and died within three years after such "
        "separation to have died fully insured.",
    ],
    "poms_rs_00301_475": [
        "Any wages reallocated based on wages earned cannot then be "
        "used to establish a QC based on wages paid for the same year "
        "or any subsequent year.",
    ],
    "poms_rs_00301_480": [
        "It is also not effective for disabilities beginning after "
        "1955, as any NH disabled after 1955 and meeting the "
        "alternative test would be insured under the 20/40 rule.",
    ],
    "poms_rs_00301_600": [
        "The election of coverage by a religious order under the "
        "“vow-of-poverty provision” may give a member of the order "
        "insured status.",
    ],
    "poms_rs_00301_800": [
        "Quarters of Coverage Requirements (Back) - Exhibit",
    ],
    "ecfr_20cfr404_subpart_b": [
        "You reach a particular age on the day before your birthday.",
        "You are fully insured as of the first day of the calendar "
        "quarter in which you acquire the last needed QC",
    ],
    "lii_usc_42_413": [
        "with such product, if not a multiple of $10, being rounded "
        "to the next higher multiple of $10 where such amount is a "
        "multiple of $5 but not of $10 and to the nearest multiple "
        "of $10 in any other case.",
        "$10,800 in the case of a taxable year beginning after 1972 "
        "and before 1974",
    ],
    "lii_usc_42_414": [
        "one quarter of coverage (whenever acquired) for each calendar "
        "year elapsing after 1950 (or, if later, the year in which he "
        "attained age 21)",
    ],
    "lii_usc_42_416": [
        "on the first day of the first quarter thereafter in which he "
        "satisfies such requirements.",
    ],
    "lii_usc_42_423": [
        "not less than 20 quarters of coverage during the 40-quarter "
        "period which ends with the quarter in which such month occurred",
        "when the number of quarters in any period is an odd number, "
        "such number shall be reduced by one",
    ],
    "ssa_oact_qc": [
        "No matter how high your earnings may be, you can not earn "
        "more than 4 QC's in one year.",
    ],
}


def test_manifest_pins_every_capture():
    document = manifest()
    assert document["schema_version"] == 1
    sources = document["sources"]
    assert len(sources) == 44
    assert len({source["id"] for source in sources}) == len(sources)
    for source in sources:
        data = (SOURCES / source["file"]).read_bytes()
        assert len(data) == source["bytes"], source["id"]
        assert hashlib.sha256(data).hexdigest() == source["sha256"]
        assert source["url"].startswith("https://")
        when = datetime.fromisoformat(source["retrieved_at_utc"])
        assert when.utcoffset().total_seconds() == 0
        assert source["capture"] in document["capture_formats"]
        if source["id"].startswith("poms"):
            assert re.fullmatch(r"\d{2}/\d{2}/\d{4}", source["page_date"])
            if source["id"] != "poms_rs_00301_000_toc":
                assert source["poms_transmittal"].startswith("TN ")
        if source["capture"] != "http_body":
            assert source["served_bodies"]
            for body in source["served_bodies"]:
                assert body["url"].startswith("https://")
                assert re.fullmatch(r"[0-9a-f]{64}", body["sha256"])
                assert body["bytes"] > len(data)
    assert {path.name for path in SOURCES.iterdir()} == {
        "manifest.json",
        "README.md",
        *(source["file"] for source in sources),
    }


@pytest.mark.parametrize("source_id,quotes", RULE_QUOTES.items())
def test_rule_text_is_quoted_from_the_captures(source_id, quotes):
    text = source_text(source_id)
    for quote in quotes:
        assert quote in text, (source_id, quote)


@pytest.mark.parametrize(
    "example", registry()["examples"], ids=lambda e: e["id"]
)
def test_worked_example_figures_are_quoted_from_the_captures(example):
    for quote in example["quotes"]:
        assert quote in source_text(example["source"]), (example["id"], quote)


def test_every_retained_source_has_a_specific_use():
    assert {source["id"] for source in manifest()["sources"]} == set(
        RULE_QUOTES
    )
    ids = [case["id"] for case in registry()["examples"]]
    assert len(ids) == len(set(ids))
    for finding in registry()["source_findings"].values():
        for quote in finding.get("quotes", [finding.get("quote")]):
            assert quote in source_text(finding["source"])


def test_registry_computations_name_existing_execution_tests():
    root = DATA.parents[2]
    functions_by_path = {}
    for example in registry()["examples"]:
        if example["coverage"] in {
            "computed",
            "source_erratum",
            "source_ambiguity",
            "source_rule_divergence",
            "table_differential",
        }:
            path, name = example["test_node"].split("::")
            if path not in functions_by_path:
                functions_by_path[path] = {
                    node.name
                    for node in ast.walk(ast.parse((root / path).read_text()))
                    if isinstance(node, ast.FunctionDef)
                }
            assert name in functions_by_path[path], example["id"]


def test_rulespec_dispatch_law_is_copied_from_captures():
    root = DATA.parents[2]
    dispatch = (
        root / "docs/design/track_b_insured_status_rulespec_issue.md"
    ).read_text()
    for number in (413, 414, 423):
        source = next(
            entry
            for entry in manifest()["sources"]
            if entry["id"] == f"lii_usc_42_{number}"
        )
        for paragraph in (
            (SOURCES / source["file"]).read_text().strip().split("\n\n")
        ):
            assert "> " + paragraph in dispatch


@pytest.mark.parametrize(
    "example_id,quote",
    [
        (
            "poms_102_2_john",
            "The deceased worker was never assigned an SSN.",
        ),
        (
            "poms_102_5_kismet",
            "They have never been assigned an SSN, nor were they ever "
            "issued an SSN card for work purposes.",
        ),
        (
            "poms_102_6_rocky",
            "Rocky and Oksana were never assigned SSNs.",
        ),
        (
            "poms_102_7_cyril",
            "nor were they ever assigned an SSN.",
        ),
    ],
)
def test_poms_102_never_assigned_ssn_is_a_named_refusal(example_id, quote):
    from populace_dynamics.track_b import insured_status as i
    from populace_dynamics.track_b.gross_benefits import count_family_outcomes

    assert quote in source_text("poms_rs_00301_102")
    # Published cases do not give complete year-level records. The invented
    # zero history only supplies structurally valid input to the explicitly
    # unsupported SSPA adjudication; it is not a claim about their earnings.
    person = i.Person(
        date(1960, 1, 2), alien_worker=True, ssn_never_assigned=True
    )
    month = date(2026, 1, 1)
    years = {
        year: i.CoverageYear(
            i.EarningsProvenance.OBSERVED,
            **(
                {"qc_count": 0}
                if year >= 1978
                else {"qc_quarters": (False,) * 4}
            ),
        )
        for year in range(1960, 2027)
    }
    outcome = i.evaluate_insured_status(
        example_id,
        Fraction(1),
        lambda: i.insured_status(person, years, month),
    )
    assert (
        outcome.unsupported.reason is i.InsuredUnsupportedReason.ALIEN_WORKER
    )
    denominator = count_family_outcomes((outcome,))
    assert denominator.rows == denominator.unsupported_rows == 1


def test_never_assigned_ssn_cannot_also_have_an_assignment_date():
    from populace_dynamics.track_b import insured_status as i
    from populace_dynamics.track_b.gross_benefits import InvalidFamilyInput

    with pytest.raises(InvalidFamilyInput):
        i.Person(
            date(1960, 1, 2),
            alien_worker=True,
            ssn_never_assigned=True,
            ssn_assignment_date=date(2004, 1, 2),
        )


def poms_qc_chart():
    text = source_text("poms_rs_00301_250")
    result = {}
    pattern = r"(\d{4})(?: – (\d{4}))? \$([\d,]+) \$([\d,]+)"
    for start, end, amount, maximum in re.findall(pattern, text):
        amount, maximum = int(amount.replace(",", "")), int(
            maximum.replace(",", "")
        )
        assert maximum == amount * 4
        for year in range(int(start), int(end or start) + 1):
            result[year] = amount
    assert set(result) == set(range(1978, 2027))
    return result


def oact_qc_chart():
    text = source_text("ssa_oact_qc").split(
        "Amount of earnings needed to earn one quarter of coverage"
    )[-1]
    result = {
        int(year): int(amount.replace(",", ""))
        for year, amount in re.findall(r"\b(\d{4}) \$?([\d,]+)", text)
    }
    assert set(result) == set(range(1978, 2028))
    return result


def test_poms_and_oact_qc_charts_agree_every_shared_year():
    poms, oact = poms_qc_chart(), oact_qc_chart()
    assert poms == {year: oact[year] for year in poms}
    assert poms[2010] == poms[2011] == 1120


def test_module_qc_amounts_match_both_published_charts():
    from populace_dynamics.track_b._insured_status_qc import QC_AMOUNTS

    assert dict(QC_AMOUNTS) == oact_qc_chart()


@pytest.mark.parametrize("year", range(1979, 2027))
def test_213d_formula_against_published_chart_and_nawi_bundle(year):
    from populace_dynamics.track_b._insured_status_qc import (
        _qc_amount_from_nawi,
    )

    nawi = json.loads((DATA / "ret_history.json").read_text())["nawi"]
    # Exact decimal strings, with no float conversion or tolerance.
    chart = poms_qc_chart()
    actual = _qc_amount_from_nawi(
        Fraction(nawi[str(year - 2)]), chart[year - 1]
    )
    assert actual == chart[year]


def test_nawi_bundle_is_verified_against_its_original_capture():
    source_dir = DATA / "ret_sources"
    manifest = json.loads((source_dir / "manifest.json").read_text())
    entry = next(
        s for s in manifest["sources"] if s["id"] == "ssa_nawi_history"
    )
    data = (source_dir / entry["file"]).read_bytes()
    assert hashlib.sha256(data).hexdigest() == entry["sha256"]
    text = html.unescape(re.sub(r"<[^>]+>", " ", data.decode()))
    text = " ".join(text.split())
    for year, value in json.loads((DATA / "ret_history.json").read_text())[
        "nawi"
    ].items():
        assert f"{year} {Decimal(value):,.2f}" in text


def cfr_cohort_chart():
    """Return (birth-band text, male requirement, female requirement)."""
    root = ET.parse(SOURCES / "ecfr_20cfr404_subpart_b.xml").getroot()
    section = next(
        node for node in root.iter("DIV8") if node.get("N") == "404.115"
    )
    result = []
    for row in section.findall(".//TBODY/TR"):
        cells = [
            " ".join("".join(cell.itertext()).split())
            for cell in row.findall("TD")
        ]
        # The open-ended final row prints 40 once for both sex columns.
        result.append((cells[0], int(cells[1]), int(cells[2] or cells[1])))
    assert len(result) == 38
    return tuple(result)


def test_cfr_cohort_chart_is_complete_and_has_male_transition_rows():
    chart = cfr_cohort_chart()
    assert chart[0] == ("Jan. 1, 1893 or earlier", 6, 6)
    assert chart[-1] == ("Jan. 2, 1929 or later", 40, 40)
    assert [row[1] for row in chart if "Jan. 2, 191" in row[0]][:4] == [24] * 4


def test_rs00301_800_chart_attachment_is_explicitly_unavailable():
    raw = (SOURCES / "poms_rs_00301_800.html").read_text()
    assert "G-RS_00301.800-1.gif" in raw
    assert "G-RS_00301.800-2.gif" in raw
    assert "G-RS_00301.800-1.pdf" in raw
    assert not tuple(SOURCES.glob("*.gif"))
    case = next(
        e for e in registry()["examples"] if e["id"] == "poms_800_exhibit"
    )
    assert case["coverage"] == "missing_attachment"
