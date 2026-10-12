"""R3 statutory captures: byte integrity and verbatim rule/example text.

Verification class: statutory conformance, for supported ARF and
recomputation mechanics only. No population or forecast evidence.
"""

import hashlib
import re
from datetime import date
from fractions import Fraction
from pathlib import Path

import pytest

from populace_dynamics.track_b import arf, gross_benefits
from tests.track_b_arf_recompute_support import SOURCES, manifest, source_text
from tests.track_b_gross_benefit_support import (
    SOURCES as GROSS_SOURCES,
)
from tests.track_b_gross_benefit_support import (
    manifest as gross_manifest,
)
from tests.track_b_gross_benefit_support import (
    source_text as gross_source_text,
)
from tests.track_b_gross_benefit_support import (
    ssa_params,
)


def test_manifest_pins_every_capture():
    document = manifest()
    assert document["schema_version"] == 1
    assert set(document["capture_formats"]) == {
        "http_body",
        "http_text_excerpt",
        "browser_text",
    }
    entries = document["sources"]
    assert len({entry["id"] for entry in entries}) == len(entries)
    for entry in entries:
        data = (SOURCES / entry["file"]).read_bytes()
        assert len(data) == entry["bytes"], entry["id"]
        assert hashlib.sha256(data).hexdigest() == entry["sha256"]
        assert entry["url"].startswith("https://")
        assert re.fullmatch(
            r"2026-10-11T\d\d:\d\d:\d\dZ", entry["retrieved_at_utc"]
        )
        assert entry["capture"] in document["capture_formats"]
        if entry["id"].startswith("poms_"):
            assert re.fullmatch(
                r"TN \d+ \(\d\d-\d\d\)", entry["poms_transmittal"]
            )
            assert re.fullmatch(r"\d\d/\d\d/\d{4}", entry["page_date"])
        if entry["id"].startswith("ecfr_"):
            assert "2026-10-07" in entry["url"]
        if entry["capture"] == "http_body":
            assert "served_bodies" not in entry
        else:
            urls = [entry["url"], *entry.get("additional_urls", [])]
            assert [b["url"] for b in entry["served_bodies"]] == urls
            for body in entry["served_bodies"]:
                assert re.fullmatch(r"[0-9a-f]{64}", body["sha256"])
                assert body["bytes"] > len(data)
                assert body["retrieved_at_utc"] == entry["retrieved_at_utc"]
    listed = {entry["file"] for entry in entries}
    assert {p.name for p in SOURCES.iterdir()} - listed == {
        "README.md",
        "manifest.json",
    }


def test_ssa_full_pdf_capture_provenance_names_separate_r2_pr():
    entry = next(
        source
        for source in manifest()["sources"]
        if source["id"] == "ssa_pub_05_10069_arf_recompute_excerpts"
    )
    assert "R2 PR #528" in entry["note"]
    assert "../ret_ledger_sources/" not in entry["note"]


RULE_QUOTES = {
    "poms_rs_00615_003": [
        "FRA for retirement or spouse's benefits is age 65."
    ],
    "poms_rs_00615_004": [
        "Attainment of FRA will always occur in the same month for all possible types of benefits."
    ],
    "poms_rs_00615_010": [
        "DIB is not reduced unless there was prior entitlement to reduced RIB (or WIB prior to 1/90)."
    ],
    "poms_rs_00615_015": [
        "Social Security follows English common law that finds that a person attains an age on the day before the birthday."
    ],
    "poms_rs_00615_480": [
        "This adjustment is automatic; i.e., no application or request is needed."
    ],
    "poms_rs_00615_482": [
        "full or partial work deduction; or",
        "grant ARFs separately on each record.",
    ],
    "poms_rs_00615_490": ["These adjustments are effective at FRA."],
    "poms_rs_00615_491": [
        "all months of termination will be eliminated from the reduction months:"
    ],
    "poms_rs_00615_500": [
        "Entitlement to RIB or DIB does not affect the ARF for the spouse benefit.",
        "The adjusted spouse reduction factor is applied to the excess spouse's benefit.",
    ],
    "poms_rs_00615_580": ["Different methods are used for these adjustments."],
    "poms_rs_00615_582": [
        "Compute the rates at 62 and FRA by removing crediting months."
    ],
    "poms_rs_00615_585": ["Pay no more than RIB limitation."],
    "poms_rs_00615_590": [
        "Determine the reduction factor as if the widow(er) attains age 60 in the MOET."
    ],
    "poms_rs_00615_595": [
        "The adjusted reduction factor is applied to the excess of the WIB PIA over the DIB PIA."
    ],
    "poms_rs_00615_598": [
        "Consider as crediting months only months NH was alive."
    ],
    "poms_rs_00605_005": [
        "The benchmark year for RIB is the year of age 62 attainment"
    ],
    "poms_rs_00605_401": [
        "A recomputation to allow credit for earnings in the year of death is effective the month of death."
    ],
    "poms_rs_00605_405": [
        "A recomputation is a new initial determination.",
        "If the resulting PIA is lower than the PIA of record, the recomputation will not be processed.",
    ],
    "poms_rs_00605_407": [
        "A recomputation of the PIA can result in a decrease in total family benefits."
    ],
    "poms_rs_00605_501": [
        "If the increase over the PIA of record after considering all applicable COLAs up to the effective date of the recomputation is less than $1.00, a recomputation is not due.",
        "If the NH had no earnings for 1998 we could not consider the recomputation for 1/ 1999.",
    ],
    "poms_rs_00605_560": [
        "AERO is the process that automatically screens ERs that have changes in earnings information and computes the necessary changes."
    ],
    "poms_rs_00605_570": [
        "When an increase is not due, a notice is required."
    ],
    "poms_rs_00605_580": [
        "When a prior computation is incorrect, any necessary recalculation is made under the rules applicable to the computation being corrected."
    ],
    "ecfr_20cfr_404_280": [
        "There is no limit on the number of times your primary insurance amount may be recomputed, and we do most recomputations automatically."
    ],
    "ecfr_20cfr_404_281": [
        "Earnings that you have after you become entitled to benefits will be used in a recomputation of your primary insurance amount."
    ],
    "ecfr_20cfr_404_282": [
        "However, a recomputation to include earnings in the year of death (whether or not paid before death) is effective for the month of death."
    ],
    "ecfr_20cfr_404_283": [
        "In some cases, we may recompute your primary insurance amount under a computation method different from the method used in the computation (or earlier recomputation) of your primary insurance amount"
    ],
    "ecfr_20cfr_404_284": [
        "The formula that was used in the first computation of your primary insurance amount is also used in recomputations of your primary insurance amount."
    ],
    "ecfr_20cfr_404_285": ["You do not have to request this service"],
    "ecfr_20cfr_404_286": [
        "we cannot begin paying higher benefits on the recomputed primary insurance amount any sooner than we could under an automatic recomputation"
    ],
    "ecfr_20cfr_404_287": [
        "That you waive one recomputation, however, does not mean that you also waive future recomputations for which you might be eligible."
    ],
    "ecfr_20cfr_404_288": [
        "We will disregard the rule in § 404.284(e) that the recomputation must increase your primary insurance amount by at least $1."
    ],
    "ecfr_20cfr_404_409": [
        "You may receive unreduced old-age, wife's, or husband's benefits beginning with the month you attain the age shown."
    ],
    "ecfr_20cfr_404_410": [
        "The reduction is 5/9 of 1 percent for each of the first 36 months and 5/12 of 1 percent for each month in excess of 36."
    ],
    "ecfr_20cfr_404_411": [
        "Such age reductions are made before any reduction under the provisions of § 404.407."
    ],
    "ecfr_20cfr_404_412": [
        "Increases in benefit amounts based upon this adjustment are effective with the month of attainment of full retirement age."
    ],
}

RULE_QUOTES.update(
    {
        "lii_usc_402q_415f_excerpts": [
            "If the amount of any reduction computed under paragraph (1), (2), or (3) is not a multiple of $0.10, it shall be increased to the next higher multiple of $0.10.",
            "A recomputation shall be effective under this subsection only if it increases the primary insurance amount by at least $1.",
        ],
        "ssa_pub_05_10069_arf_recompute_excerpts": [
            "your monthly benefit will increase starting at your full retirement age.",
            "This is an automatic process, and benefits are paid in December of the following year.",
        ],
    }
)


@pytest.mark.parametrize(
    ("source_id", "quote"),
    [
        (source, quote)
        for source, quotes in RULE_QUOTES.items()
        for quote in quotes
    ],
)
def test_rule_text_is_quoted_from_the_captures(source_id, quote):
    assert quote in source_text(source_id)


def test_every_capture_is_used_by_a_substantive_rule_test():
    assert set(RULE_QUOTES) == {
        source["id"] for source in manifest()["sources"]
    }


WORKED_EXAMPLE_QUOTES = {
    "ssa_pub_05_10069_arf_recompute_excerpts": [
        "$910",
        "$975",
        "$1,300",
        "12 months",
        "62",
        "67",
        "2026",
    ],
    "poms_rs_00615_015": [
        "5/31/1935",
        "6/1/1935",
        "6/2/1935",
        "6/3/1935",
        "12/31/1935",
        "1/1/1936",
        "1/2/1936",
        "1/3/1936",
        "12/31/1937",
        "1/1/1938",
        "1/2/1938",
        "1/3/1938",
        "$1207",
        "$972",
        "$965",
        "$1232",
        "$1266",
        "$992",
        "$1012",
        "$1019",
        "$1372",
        "$1410",
        "$1105",
        "$1116",
        "$1122",
        "35 RF",
        "36 RF",
        "37 RF",
        "38 RF",
        "age 65 and 2 months",
        "In 2/1998 Demi has 37 RF.",
        "Demi - $1122 starting 2/2000",
        "6/1997",
        "7/1997",
        "1/1998",
        "2/1998",
        "1/2000",
        "2/2000",
    ],
    "poms_rs_00605_501": [
        "$849.40",
        "$850.00",
        "$850.40",
        "$1.00",
        "$445.50",
        "$.90",
        "$451.20",
        "$452.20",
        "12/1997",
        "1 /1998",
        "12/ 1998",
        "1/1999",
    ],
    # Example 1 is deliberately refused by modern eligibility scope, not
    # reproduced using modern floor rounding. Keep all historical figures
    # beside that refusal and the historical arithmetic demonstration.
    "ecfr_20cfr_404_284": [
        "$432.40",
        "$903",
        "$11,000",
        "$8,911.36",
        "$251,470.05",
        "$911",
        "$396.00",
        "9.9 percent",
        "$435.30",
        "14.3 percent",
        "$497.60",
        "11.2 percent",
        "$553.40",
        "$12,000",
        "$2,700",
        "$537",
        "$407.70",
        "$569.60",
        "$429.20",
        "$502",
        "$142,000",
    ],
}


@pytest.mark.parametrize(
    ("source_id", "quote"),
    [
        (source, quote)
        for source, quotes in WORKED_EXAMPLE_QUOTES.items()
        for quote in quotes
    ],
)
def test_worked_example_figures_are_quoted_from_the_captures(source_id, quote):
    assert quote in source_text(source_id)


READING_QUOTES = {
    "poms_rs_00615_003": [
        "People Born Before 1/2/1911",
        "FRA for widow(er)'s benefits was age 62",
        "People Born from 1/2/1911 Through 1/1/40",
    ],
    "ecfr_20cfr_404_409": [
        "Before 1/2/1912 62 years.",
        "1/2/1912—1/1/1940 65 years.",
    ],
    "ecfr_20cfr_404_412": [
        "any month in which she or he had in her or his care a child of the deceased insured individual and for which the child was entitled to child's benefits;"
    ],
    "poms_rs_00615_482": [
        "widow(er)'s benefits were increased to the mother or father's rate."
    ],
    "lii_usc_402q_415f_excerpts": [
        "any month in which the reduction in the amount of such benefit was determined under paragraph (5)(D)"
    ],
}


@pytest.mark.parametrize(
    ("source_id", "quote"),
    [
        (source, quote)
        for source, quotes in READING_QUOTES.items()
        for quote in quotes
    ],
)
def test_alternative_readings_are_quoted_from_captures(source_id, quote):
    assert quote in source_text(source_id)


SPOUSE_REENTITLEMENT_QUOTES = {
    "RS 00615.201A.1": (
        "After 12/72 a spouse reentitled prior to FRA as a spouse on the "
        "same earnings is reduced the same number of months as the "
        "earlier entitlement. An ARF at FRA will remove all months of "
        "nonentitlement."
    ),
    "RS 00615.491A": (
        "Beginning in 1/78, if a reduced spouse is terminated and then "
        "reentitled, (months in which the spouse's benefits were "
        "terminated will be eliminated from the reduction factor when "
        "the spouse is reentitled."
    ),
}


def test_spouse_reentitlement_conflict_quotes_and_refusal_are_documented():
    """Both already captured POMS readings must remain visible to review."""
    # The .201 source is listed in G's manifest rather than R3's. Check
    # those referenced bytes here as well as the verbatim quoted text.
    entry = next(
        s
        for s in gross_manifest()["sources"]
        if s["id"] == "poms_rs_00615_201"
    )
    data = (GROSS_SOURCES / entry["file"]).read_bytes()
    assert len(data) == entry["bytes"]
    assert hashlib.sha256(data).hexdigest() == entry["sha256"]
    texts = {
        "RS 00615.201A.1": gross_source_text("poms_rs_00615_201"),
        "RS 00615.491A": source_text("poms_rs_00615_491"),
    }
    note = (
        Path(__file__).parents[1] / "docs/design/track_b_r3_arf_recompute.md"
    ).read_text()
    judgment = " ".join(
        note.split("## Findings and readings requiring judgment", 1)[1]
        .split("## Monthly assembly inputs", 1)[0]
        .split()
    )
    refusal_row = next(
        line
        for line in note.splitlines()
        if line.startswith("| Earlier reentitled spouse adjustment |")
    )
    for authority, quote in SPOUSE_REENTITLEMENT_QUOTES.items():
        assert quote in texts[authority]
        assert quote in judgment
        assert authority in refusal_row
    assert "conflict" in refusal_row
    assert "arf_spouse_reentitlement_before_fra" in refusal_row
    for amount in ("$422.50", "$425.20", "$2.70"):
        assert amount in judgment


def test_spouse_reentitlement_counterfactual_readings_keep_named_refusal():
    """Invented 1960-01-02 spouse: $650, 60 RF versus 59 RF.

    First entitlement 2022-01, termination 2022-02, reentitlement
    2022-03. The .201 reading preserves 60 RF: 35% reduction gives
    $422.50/$422. The .491 reading removes the terminated month: 59 RF
    has reduction 83/240, rounded upward from $224.7916... to $224.80,
    giving $425.20/$425. These are counterfactual arithmetic diagnostics;
    neither reading is admitted by the refused pre-FRA claim.
    """
    params = ssa_params()
    unreduced = Fraction(650)
    amounts = tuple(
        gross_benefits.floor_dime(
            unreduced
            - gross_benefits.ceil_dime(
                unreduced
                * gross_benefits.spouse_reduction_fraction(months, params)
            )
        )
        for months in (60, 59)
    )
    assert amounts == (Fraction("422.50"), Fraction("425.20"))
    assert tuple(map(gross_benefits.whole_dollars, amounts)) == (422, 425)
    assert amounts[1] - amounts[0] == Fraction("2.70")
    claim = arf.ARFClaim(
        kind=arf.ARFBenefitKind.SPOUSE,
        birth_date=date(1960, 1, 2),
        first_reduction_month=(2022, 1),
        unreduced_benefit=unreduced,
        nonentitlement_months=frozenset({(2022, 2)}),
    )
    with pytest.raises(
        gross_benefits.FamilyConfigurationUnsupported
    ) as caught:
        arf.apply_arf(claim, payment_month=(2022, 3), params=params)
    assert (
        caught.value.reason
        is arf.ARFUnsupportedReason.SPOUSE_REENTITLEMENT_BEFORE_FRA
    )
