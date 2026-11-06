"""Verification class: statutory conformance; R2 sources and worked examples.

Every rule and figure below is read from pinned source bytes. Published
pre-2000 examples exercise pure rule helpers; the ledger still refuses
pre-2000 payment years. Admitted scope: RET rule mechanics on invented
cases and published examples; no population, behavioral or forecast claim.
"""

from __future__ import annotations

import hashlib
import inspect
import re
from datetime import datetime
from fractions import Fraction as F

import pytest

from populace_dynamics.track_b import ret_ledger as r
from populace_dynamics.track_b.ret_grace import (
    BenefitType as T,
)
from populace_dynamics.track_b.ret_grace import (
    GraceMonth,
    GraceYearState,
    grace_year,
)
from populace_dynamics.track_b.ret_params import load_ret_parameters
from tests.track_b_ret_ledger_support import SOURCES, manifest, source_text


def test_source_conflict_ids_are_linked_at_the_decision_lines():
    decisions = (
        (
            r.countable_earnings,
            "us:oasdi-ret-negative-nese-proration",
            "if nese_proration_policy is NESEProrationPolicy.FLOOR",
        ),
        (
            grace_year,
            "us:oasdi-ret-grace-simultaneous-rib-dib",
            "not month.entitled_types & DISABILITY_TYPES",
        ),
        (
            r._protected,
            "us:oasdi-ret-own-work-age-exemptions",
            "or b.benefit_types[month - 1] in DISABILITY_TYPES",
        ),
        (
            r.RETBeneficiary.__post_init__,
            "us:oasdi-ret-deemed-entitlement-basis",
            "if not self.deemed_married_to_nh:",
        ),
        (
            r.apply_ret_year,
            "us:oasdi-ret-deemed-entitlement-basis",
            "if b.deemed_entitled and any(",
        ),
    )
    for function, conflict_id, decision in decisions:
        source = inspect.getsource(function)
        expected = (
            re.escape(f"# Source conflict {conflict_id}")
            + r"\n\s*"
            + re.escape(decision)
        )
        assert re.search(expected, source), (conflict_id, decision)


def test_manifest_pins_every_capture():
    document = manifest()
    assert document["schema_version"] == 1
    ids = [s["id"] for s in document["sources"]]
    assert len(ids) == len(set(ids))
    for entry in document["sources"]:
        data = (SOURCES / entry["file"]).read_bytes()
        assert len(data) == entry["bytes"], entry["id"]
        assert hashlib.sha256(data).hexdigest() == entry["sha256"]
        assert entry["url"].startswith("https://")
        when = datetime.fromisoformat(
            entry["retrieved_at_utc"].replace("Z", "+00:00")
        )
        assert when.utcoffset().total_seconds() == 0
        assert entry["capture"] in document["capture_formats"]
        if entry["id"].startswith("poms_"):
            assert entry["poms_transmittal"] in source_text(entry["id"])
            assert entry["page_date"] in source_text(entry["id"])
        if entry["capture"] == "pdf_text":
            body = next(
                s for s in document["sources"] if s["id"] == "ssa_pub_05_10069"
            )
            assert entry["served_bodies"] == [
                {name: body[name] for name in ("url", "bytes", "sha256")}
            ]
    captured = {path.name for path in SOURCES.iterdir()}
    listed = {s["file"] for s in document["sources"]}
    assert captured - listed == {"manifest.json", "README.md"}


# A quote for every capture: part-b sources pin the explicit refusal boundary.
RULE_QUOTES = {
    "poms_rs_02501_001": [
        "Charging begins the first MOE in rule 8(c) and continues to last MOE in TY"
    ],
    "poms_rs_02501_021": [
        "Always use the FRA for retirement insurance benefits (RIB)",
        "wage earner is entitled to benefits prior to the month of divorce",
        "A beneficiary will receive crediting months for any month they were in full or partial work deduction",
    ],
    "poms_rs_02501_025": [
        "The monthly exempt amount is equal to 1/12 of the applicable annual exempt amount.",
        "use the full annual exempt amount for a beneficiary who dies in the year of attainment of FRA even if they died before attaining FRA",
        "2000 $10,080 $840 $2 over $10,080 $17,000 $1,417",
        "2001 $10,680 $890 $2 over $10,680 $25,000 $2,084",
    ],
    "poms_rs_02501_030": [
        "becomes entitled to a different type of benefit (i.e., retirement, wife's, husband's, child's, widow's, widower's, mother's, father's, or parent's);",
        "Child's benefits as defined in section 202(d) of the Social Security Act (the Act),",
        "A grace year does not apply to a disabled beneficiary in any year if entitled solely to DIB, disabled widow(er)'s (DWB), or childhood disability benefits (CDB).",
        "Do not annotate the LMETY field if the only reason to apply the MET is the termination grace year or all months of entitlement are in the month of FRA or later.",
        "there is a break in entitlement of at least 1 month",
        "A grace year does not apply to a disabled beneficiary in any year if entitled solely to DIB",
        "Do not annotate the LMETY field if the only reason to apply the MET is the termination grace year",
        "A NSM is any month of entitlement, before FRA",
    ],
    "poms_rs_02501_070": [
        "If the beneficiary withdraws an application, eliminate NSM because entitlement does not exist."
    ],
    "poms_rs_02501_075": [
        "A FY is an accounting period of 12 months that is other than January 1 through December 31."
    ],
    "poms_rs_02501_080": [
        "prorate the net earnings (or loss) equally over all months the beneficiary was engaged in self-employment",
        "Divide the remainder by 2, then round down to the next lower dollar",
        "exclude wages earned in or after the month of attainment of FRA",
        "then drop the cents, then round down before multiplying by the months before the beneficiary attains FRA",
        "If the answer is not in whole dollars, round down to the next lower dollar.",
    ],
    "poms_rs_02501_095": [
        "do not count the divorced spouse's benefit amount when determining the total family benefit",
        "Withhold the working auxiliary's excess earnings from any remaining benefits",
        "reductions above and after the benefit amount is rounded to a multiple of $.10",
    ],
    "poms_rs_02501_100": [
        "When the excess earnings charged to a month are less than a full monthly benefit, impose a work suspension for the entire month.",
        "continuing until the excess is recovered or until all the benefits have been withheld for the year",
        "If a beneficiary protests the withholding of a full month's benefit",
    ],
    "poms_rs_02501_105": [
        "Base the amount of Social Security benefits paid to an individual during the year on that individual's estimate of earnings for the year."
    ],
    "poms_rs_02501_110": [
        "Reapportion the excess to all other beneficiaries in proportion to their original entitlement rates.",
        "Do not reapportion the excess amount if at any point it totals less than $1; the monthly benefit amount includes this last calculation.",
        "Once we receive the closed-year earnings, pay a partial monthly benefit, if due.",
        "allocate partial benefit to each beneficiary in proportion to each original monthly benefit amount",
        "Do not reapportion the excess amount if at any point it totals less than $1",
        "Do not round any share until the final apportionment or reapportionment is completed.",
    ],
    "poms_rs_02501_120": ["Cannot extend beyond June of the following year"],
    "poms_rs_02501_125": [
        "Divide remaining excess withholding by the number of months in the prorating period"
    ],
    "poms_rs_02501_130": [
        "Readjust auxiliary benefit rates up to the family maximum when an individual is deemed not entitled to benefits for a month"
    ],
    "poms_rs_02501_140": [
        "deem a retirement beneficiary's spouse or child entitled on their record if they are receiving CDB, mother's or father's benefits, or child's benefits based on another person's ER.",
        "Charge the excess earnings of the retirement beneficiary not only to the benefits of the retirement beneficiary",
    ],
    "poms_rs_02501_145": [
        "If a beneficiary with excess earnings has entitlement to both retirement insurance benefits (RIB) and auxiliary/survivor benefits, charge the excess to the total of all benefits."
    ],
    "poms_rs_02501_150": [
        "charge their excess for the month to the combined amount of their RIB and their share of the partial benefit"
    ],
    "poms_rs_02501_155": [
        "treat the beneficiary as not being on the benefit rolls in applying the maximum provisions",
        "Reduce the maximum applicable to the other beneficiaries by the amount of the partial benefit due the beneficiary.",
        "charge each auxiliary's or survivor's excess earnings against their own benefit.",
        "The partial benefits of other auxiliaries cannot be readjusted except to the extent to which we charge the auxiliary's excess earnings against the benefits to which the auxiliary otherwise was eligible.",
    ],
    "poms_rs_02501_160": [
        "Withhold any increased amounts due beneficiaries outside the household of the working beneficiary until after the close of the year"
    ],
    "poms_gn_02603_010": [
        "The statute requires the imposition of certain deductions before reducing benefits to achieve the maximum family benefit."
    ],
    "poms_gn_02603_020": [
        "Take the reduction for the family maximum after making the deductions listed on GN 02603.040"
    ],
    "poms_gn_02603_040": [
        "Annual earnings test deduction for an auxiliary or survivor"
    ],
    "poms_gn_02603_045": [
        "we will consider only the benefit actually payable when reducing the benefits of dually entitled auxiliaries or survivors"
    ],
    "poms_gn_02603_050": [
        "Deductions based on the annual earnings test become permanent deductions based on a closed year work report",
        "regardless of other deductions that may apply for any other beneficiary on record disregard the dually entitled beneficiary",
        "The worker's rate will always be $0.00 because there are no partial deductions for temporary work deductions.",
    ],
    "poms_gn_02603_055": [
        "Apply WC or PDB offset to determine the amount of offset that applies to each beneficiary."
    ],
    "poms_gn_02603_060": [
        "References to old rule and new rule in these examples refer to the treatment of dual entitlement situations"
    ],
    "poms_gn_02603_075": [
        "After 12/1995, the facility of payment provision no longer applies."
    ],
    "poms_gn_02603_090": [
        "Determine household status using the configuration that exists when the beneficiary files the annual report."
    ],
    "poms_gn_02603_100": [
        "Under the facility-of-payment provision, E continues to receive a readjusted benefit"
    ],
    "poms_rs_02510_001": [
        "Section 203(b) of the Act provides for deductions on the basis of excess earnings."
    ],
    "poms_rs_02510_005": [
        "Current year work reports refer to the estimates of earnings that are used to pay current year benefits."
    ],
    "poms_rs_02510_015": [
        "Was under FRA (Full Retirement Age) for at least 1 month of the year"
    ],
    "poms_rs_02510_026": [
        "In 1997, we changed our regulations to use earnings posted to the MEF as the annual report required by law."
    ],
    "poms_rs_02505_005": [
        "Wages above the yearly maximum limitations for coverage purposes"
    ],
    "poms_rs_02505_065": [
        "Where the time devoted to the business is less than 15 hours a month, the services are not substantial."
    ],
    "ecfr_20cfr404_subpart_e": [
        "A beneficiary may have another grace year each time his or her entitlement to one type of benefit ends and, after a break in entitlement of at least one month, the beneficiary becomes entitled to a different type of retirement or survivors benefit.",
        "The new grace year would then be the taxable year in which the first non-service month occurs after the break in entitlement.",
        "we will not count as a non-service month, a month that occurred while the beneficiary was entitled to disability benefits under section 223 of the Social Security Act or as a disabled widow, widower, or child under section 202.",
        "A beneficiary entitled to child's benefits",
        "is entitled to a termination grace year in any year the beneficiary's entitlement to these types of benefits terminates.",
        "a month that occurred while the beneficiary was entitled to disability benefits under section 223 of the Social Security Act or as a disabled widow, widower, or child under section 202.",
        "a child's insurance benefit based on the child's disability",
        "Are age 18 or over and entitled to a child's insurance benefit based on disability",
        "Are entitled to a widow's or widower's insurance benefit based on disability",
        "The monthly exempt amount, (which is 1/12 of the annual exempt amount), applies only in a beneficiary's grace year or years.",
        "If the excess amount involved at any point totals less than $1, it is not reapportioned; instead, each beneficiary is paid on the basis of the last calculation.",
        "a person who is married to an old-age insurance beneficiary",
        "Where both the insured individual and another person entitled (or deemed entitled) on the same earnings record have excess earnings",
        "Excess earnings are 33 1/3 percent of the earnings above the annual exempt amount.",
        "your excess earnings are charged first against the total family benefits payable",
        "If the excess amount involved at any point totals less than $1, it is not reapportioned",
        "$17,000 $1,417",
        "25,000 2,084",
    ],
    "ssa_while_working": [
        "We only count your earnings up to the month before you reach your full retirement age"
    ],
    "ssa_special_rule": [
        "you are considered retired in any month that your earnings are $2,040 or less and you did not perform substantial services"
    ],
    "ssa_pub_05_10069": [
        "we must deduct $1 from your benefits for each $2 you earn above $24,480"
    ],
    "ssa_pub_05_10069_text": [
        "we must deduct $1 from your benefits for each $2 you earn above $24,480"
    ],
    "ssa_act_203": [
        "the taxable year in which occurs the first month after December 1977",
        "subsection (a), (b), (c), (d), (e), (f), (g), or (h) of section 202",
        "without having been entitled for the preceding month to a benefit under any other of such subsections",
        "benefits payable under section 202(d) by reason of being under a disability",
        "or under section 202(d) or (g), if such month is in a year in which such entitlement ends for a reason other than the death of such individual",
        "is not entitled to any benefits under this title for the month following",
        "Notwithstanding any other provision of this subsection",
        "for each month of any taxable year ending after 1999 and before 2001, $1,416.66 2/3",
        "for each month of any taxable year ending after 2000 and before 2002, $2,083.33 1/3",
        "If a child who has attained the age of 18 and is entitled to child's insurance benefits",
        "in which such individual, if a child entitled to child's insurance benefits, has attained the age of 18",
        "for which such individual is entitled to widow's or widower's insurance benefits if such individual became so entitled prior to attaining age 60",
        "Notwithstanding the preceding provisions of this paragraph but subject to section 202(s)",
        "is married to an individual entitled to old-age insurance benefits under section 202(a)",
        "excess earnings, under the provisions of subsection (f) of this section",
    ],
}


WORKED_EXAMPLE_QUOTES = {
    "poms_rs_02501_160": [
        "$159.90",
        "$213.10",
        "$396",
        "$99",
        "$555",
        "$60",
        "$132",
        "$119",
        "$33",
        "$20",
        "$ 39",
    ],
    "poms_rs_02501_080": [
        "Beneficiary is age 64 in TY 1999",
        "$12,121",
        "$9,600",
        "$1,260",
        "FRA in 6/00",
        "$30,000",
        "$10,000",
        "$17,000",
        "$4,333",
        "$24,000",
        "$2,000 x 5",
        "$44,000",
        "$9,776",
        "$4,888",
        "4/99 and 5/99",
        "$15,500",
        "FRA in 7/00",
        "$7,000",
        "$25,000",
        "$2,666",
    ],
    "poms_rs_02501_095": [
        "$378",
        "$160",
        "$2,094",
        "$698",
        "January through March",
        "$346",
        "$173",
        "$2,076",
        "$865",
        "January through April",
        "May through September",
    ],
    "poms_rs_02501_100": [
        "$562.00",
        "$2,880",
        "full-month suspensions through June",
    ],
    "poms_rs_02501_110": [
        "$562",
        "$2,881",
        "$71",
        "$491 for June",
        "$800",
        "$101 each",
        "$6,624",
        "$1,204",
        "$600",
        "$200",
        "$100",
        "$93",
        "$117",
        "$19.90",
        "$16",
        "$172.80",
        "$37.20",
        "$18.60",
        "$2.60",
        "$1.30",
        "$.65",
        "$38.50",
        "$19.25",
        "A - $38",
        "B - $16",
        "C2 - $19",
        "C1 - $19",
        "2/6 (NH) plus 1/6 x 4 (aux)",
        "two shares (2/5)",
        "one share (1/5)",
        "two to NH (2/4) and 1/4 to each child",
    ],
    "poms_rs_02501_030": [
        "entitled to benefits 01/11",
        "FRA in 08/11",
        "06/11 and 07/11",
        "initial grace year is 2011",
        "mother's benefits in 2010",
        "terminate in 06/10",
        "In 2011",
        "date of birth is 01/20/92",
        "entitlement ends in 12/09",
        "termination grace year is 2009",
        "child's benefits in 2008",
        "terminate in 03/10",
        "beginning 09/10",
        "terminate again 04/11",
        "2011 is another termination grace year",
        "RIB and DIB simultaneously in 06/10",
        "NSMs of 06/10 through 12/10",
        "DIB instead of RIB in 01/11",
        "Effective 01/12",
        "initial grace year was in 2010",
    ],
    "ssa_pub_05_10069": [
        "$600 per month",
        "$7,200",
        "$26,080",
        "$1,600",
        "$24,480",
        "$800",
        "January 2026 through February 2026",
        "In 2027, we would pay you the additional $400",
        "November 2026",
        "$68,520",
        "$1,120",
        "$65,160",
        "remaining $80",
        "$700",
        "$900",
        "$1,100",
        "$8,400",
        "$8,140",
        "$7,140",
        "$10,800",
        "$10,540",
        "$9,540",
        "$13,200",
        "$12,940",
        "$11,940",
        "$25,000",
        "$27,000",
        "October 30, 2026",
        "$45,000",
        "$500 per month",
        "November and December",
        "$2,040",
    ],
    "ssa_while_working": [
        "$800",
        "$9,600",
        "$33,400",
        "$8,920",
        "$4,460",
        "$5,140",
        "August 2026",
        "$72,000",
        "$66,000",
        "$840",
        "$280",
        "$5,320",
        "$5,600",
    ],
    "ssa_special_rule": [
        "John Smith",
        "June 30, 2026",
        "$37,000",
        "October 5",
        "$3,000",
        "$40,000",
        "July, August, and September",
        "October, November, or December",
    ],
    "ecfr_20cfr404_subpart_e": [
        "Don, age 62",
        "$15,000 for January-April",
        "May-December",
        "Marion",
        "1998 was her initial grace year",
        "termination grace year for 2000",
        "effective February 2001",
        "$165",
        "$82.50",
        "$247.50",
        "$200 payable for October",
        "$133",
        "66",
        "199",
        "Family maximum is $150",
        "$25",
        "$125",
        "16.60",
        "75",
        "16",
        "$264",
        "$176",
        "$1,599",
        "$265",
        "$340",
        "except February",
        "$249",
        "$166 and $83",
        "February ($88)",
        "September",
        "$6",
        "$82",
    ],
}


def test_every_capture_is_used_by_a_conformance_quote():
    assert {s["id"] for s in manifest()["sources"]} == set(RULE_QUOTES) | set(
        WORKED_EXAMPLE_QUOTES
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


def test_act_203_f_8_d_v_vi_monthly_amounts_are_quoted_and_equal_annual_twelfths():
    text = source_text("ssa_act_203")
    assert "Notwithstanding any other provision of this subsection" in text
    statutory = {
        2000: ("$1,416.66 2/3", F(1416) + F(66, 100) + F(2, 300)),
        2001: ("$2,083.33 1/3", F(2083) + F(33, 100) + F(1, 300)),
    }
    for year, (quoted_amount, exact_amount) in statutory.items():
        assert quoted_amount in text
        assert (
            load_ret_parameters().for_year(year).higher_exempt_amount.value
            / 12
            == exact_amount
        )


def test_pdf_excerpt_matches_the_captured_pdf_text():
    full = source_text("ssa_pub_05_10069")
    for passage in (
        (SOURCES / "ssa_pub_05_10069_excerpt.txt").read_text().split("\f")
    ):
        normalized = re.sub(r"\s+", " ", passage.replace("’", "'")).strip()
        # A passage is a source slice, not a paraphrase or edited figure.
        assert normalized in full


def _wages(total, *, after_fra=0):
    return r.WorkEarnings(wages=(F(total),) + (F(0),) * 10 + (F(after_fra),))


_ALL_MONTHS = frozenset(range(1, 13))


def _beneficiary(
    identity,
    rate,
    *,
    benefit_type=T.RIB,
    original=None,
    earnings=None,
    fra=None,
    entitled=_ALL_MONTHS,
    grace=None,
):
    """Invented input fixtures with the cited example's rates and excess."""
    entitled = frozenset(entitled)
    return r.RETBeneficiary(
        identity,
        (benefit_type,) * 12,
        entitled,
        tuple(
            F(rate) if month in entitled else F(0) for month in range(1, 13)
        ),
        (F(original if original is not None else rate),) * 12,
        earnings=earnings or r.WorkEarnings(),
        fra_month=fra,
        grace=grace,
    )


def _excess_earnings(excess, *, year=2026, fra=None):
    """Invent wages that yield a source's expressly supplied excess amount."""
    year_params = load_ret_parameters().for_year(year)
    exempt = (
        year_params.lower_exempt_amount
        if fra is None
        else year_params.higher_exempt_amount
    )
    rate = (
        year_params.lower_withholding_rate
        if fra is None
        else year_params.higher_withholding_rate
    )
    return _wages(exempt.value + F(excess) / rate.value)


def _record(*beneficiaries, year=2026, binding=()):
    return r.RecordYear(
        year,
        "nh",
        beneficiaries=beneficiaries,
        family_maximum_binding_months=frozenset(binding),
    )


def _monthly(ledger, identity="nh"):
    return {row.month: row for row in ledger.for_beneficiary(identity)}


def _worker(ledger, identity="nh"):
    return next(w for w in ledger.workers if w.beneficiary_id == identity)


def test_poms_02501_080_1999_formula_example_outside_ledger_scope():
    assert r.calculated_excess(F(12121), F(9600), F(1, 2)) == 1260
    with pytest.raises(r.RETConfigurationUnsupported) as caught:
        r.apply_ret_year(_record(_beneficiary("nh", 562), year=1999))
    assert caught.value.reason is r.UnsupportedReason.YEAR_BEFORE_2000


@pytest.mark.parametrize(
    ("earnings", "fra", "expected_countable", "expected_excess"),
    [
        (_wages(30000, after_fra=10000), 6, 30000, 4333),
        (
            r.WorkEarnings(
                nese=24000, self_employment_months=frozenset(range(1, 13))
            ),
            6,
            10000,
            0,
        ),
        (
            r.WorkEarnings(
                nese=44000, self_employment_months=frozenset(range(4, 13))
            ),
            6,
            9776,
            0,
        ),
        (
            r.WorkEarnings(
                wages=(24000,) + (0,) * 11,
                nese=7000,
                self_employment_months=frozenset(range(6, 13)),
            ),
            7,
            25000,
            2666,
        ),
    ],
)
def test_poms_02501_080_fra_wage_and_nese_examples(
    earnings, fra, expected_countable, expected_excess
):
    # The rate is invented: this example establishes earnings, not a benefit.
    ledger = r.apply_ret_year(
        _record(_beneficiary("nh", 100, earnings=earnings, fra=fra), year=2000)
    )
    worker = _worker(ledger)
    assert worker.countable_earnings == expected_countable
    assert worker.excess == expected_excess
    assert worker.annual_exempt == 17000


def test_poms_02501_080_nese_source_errata_are_pinned_side_by_side():
    text = source_text("poms_rs_02501_080")
    assert "NESE for 2000 is $44,000" in text
    assert "4/99 and 5/99" in text
    assert "Since the exempt amount is $15,500" in text
    current_limit = (
        load_ret_parameters().for_year(2000).higher_exempt_amount.value
    )
    assert current_limit == 17000
    assert r.calculated_excess(F(9776), F(15500), F(1, 3)) == 0
    assert r.calculated_excess(F(9776), current_limit, F(1, 3)) == 0


def test_poms_02501_095_number_holder_family_example():
    ledger = r.apply_ret_year(
        _record(
            _beneficiary("nh", 378, earnings=_excess_earnings(2094)),
            _beneficiary("spouse", 160, benefit_type=T.SPOUSE, original=189),
            _beneficiary("child", 160, benefit_type=T.CHILD, original=189),
        )
    )
    assert _worker(ledger).charged == 2094
    for identity in ("nh", "spouse", "child"):
        rows = _monthly(ledger, identity)
        assert [m for m, row in rows.items() if row.deduction] == [1, 2, 3]
        assert all(row.net_due == 0 for m, row in rows.items() if m <= 3)


def test_poms_02501_095_number_holder_then_auxiliary_example():
    ledger = r.apply_ret_year(
        _record(
            _beneficiary("nh", 346, earnings=_excess_earnings(2076)),
            _beneficiary(
                "spouse",
                173,
                benefit_type=T.SPOUSE,
                earnings=_excess_earnings(865),
            ),
        )
    )
    nh = _monthly(ledger)
    spouse = _monthly(ledger, "spouse")
    assert [m for m, row in nh.items() if row.deduction] == [1, 2, 3, 4]
    assert [m for m, row in spouse.items() if row.own_deduction] == [
        5,
        6,
        7,
        8,
        9,
    ]
    assert _worker(ledger).charged == 2076
    assert _worker(ledger, "spouse").charged == 865


def test_poms_02501_100_full_month_suspension_example():
    ledger = r.apply_ret_year(
        _record(_beneficiary("nh", 562, earnings=_excess_earnings(2880)))
    )
    rows = _monthly(ledger)
    assert [m for m, row in rows.items() if row.provisional_deduction] == [
        1,
        2,
        3,
        4,
        5,
        6,
    ]
    assert all(rows[m].provisional_payment == 0 for m in range(1, 7))
    assert _worker(ledger).charged == 2880


def test_poms_02501_110_partial_benefit_example_1():
    ledger = r.apply_ret_year(
        _record(_beneficiary("nh", 562, earnings=_excess_earnings(2881)))
    )
    rows = _monthly(ledger)
    assert all(rows[m].net_due == 0 for m in range(1, 6))
    assert rows[6].deduction == 71
    assert rows[6].net_due == rows[6].payment == 491
    assert rows[6].provisional_payment == 0
    assert ledger.reconciliation["nh"] == 491


def test_poms_02501_110_partial_benefit_example_2_original_shares():
    ledger = r.apply_ret_year(
        _record(
            _beneficiary("nh", 800, earnings=_excess_earnings(6624)),
            *(
                _beneficiary(
                    f"aux{i}", 101, benefit_type=T.CHILD, original=400
                )
                for i in range(4)
            ),
            binding=range(1, 13),
        )
    )
    assert sum(row.gross for row in ledger.months if row.month == 6) == 1204
    assert _monthly(ledger)[6].net_due == 200
    for i in range(4):
        assert _monthly(ledger, f"aux{i}")[6].net_due == 100
    assert sum(row.payment for row in ledger.months if row.month == 6) == 600
    assert all(row.payment == 0 for row in ledger.months if row.month <= 5)
    assert _worker(ledger).charged == 6624


def test_poms_02501_110_partial_benefit_example_3_capped_reapportionment():
    # This source supplies the partial pool, not an annual excess amount.
    exact = r.partial_payments(
        F(93),
        {"nh": F(117), "spouse": F(16), "c1": F("19.90"), "c2": F("19.90")},
        {
            "nh": F(117),
            "spouse": F("58.50"),
            "c1": F("58.50"),
            "c2": F("58.50"),
        },
    )
    assert dict(exact) == {
        "nh": F("38.50"),
        "spouse": F(16),
        "c1": F("19.25"),
        "c2": F("19.25"),
    }
    assert {
        key: value.numerator // value.denominator
        for key, value in exact.items()
    } == {"nh": 38, "spouse": 16, "c1": 19, "c2": 19}
    assert exact.undistributed_subdollar_residual == 0


@pytest.mark.parametrize(
    ("pool", "shares", "residual"),
    [
        (F(8), (F(4), F("1.90"), F(2)), F("0.10")),
        (F("9.90"), (F("4.95"), F("1.90"), F("2.475")), F("0.575")),
    ],
)
def test_cfr_404_440_and_poms_02501_110_stop_at_subdollar_last_calculation(
    pool, shares, residual
):
    # These pools are invented executions of the verbatim stopping rule,
    # rather than additional monetary figures attributed to the sources.
    assert (
        "If the excess amount involved at any point totals less than $1, "
        "it is not reapportioned; instead, each beneficiary is paid on the "
        "basis of the last calculation."
        in source_text("ecfr_20cfr404_subpart_e")
    )
    assert (
        "Do not reapportion the excess amount if at any point it totals "
        "less than $1; the monthly benefit amount includes this last "
        "calculation." in source_text("poms_rs_02501_110")
    )
    exact = r.partial_payments(
        pool,
        {"nh": F(10), "spouse": F("1.90"), "child": F(10)},
        {"nh": F(2), "spouse": F(1), "child": F(1)},
    )
    assert tuple(exact[key] for key in ("nh", "spouse", "child")) == shares
    assert exact.undistributed_subdollar_residual == residual
    assert sum(exact.values()) + residual == pool
    assert tuple(int(exact[key]) for key in ("nh", "spouse", "child")) == (
        4,
        1,
        2,
    )


@pytest.mark.parametrize(
    ("fra", "earnings", "excess", "repayment"),
    [(None, 26080, 800, 400), (11, 68520, 1120, 80)],
)
def test_publication_05_10069_current_year_suspension_and_next_year_repayment(
    fra, earnings, excess, repayment
):
    ledger = r.apply_ret_year(
        _record(_beneficiary("nh", 600, earnings=_wages(earnings), fra=fra))
    )
    rows = _monthly(ledger)
    assert _worker(ledger).excess == _worker(ledger).charged == excess
    assert rows[1].provisional_payment == rows[2].provisional_payment == 0
    assert all(rows[m].provisional_payment == 600 for m in range(3, 13))
    assert rows[2].payment == repayment
    assert ledger.reconciliation["nh"] == repayment


@pytest.mark.parametrize(
    ("rate", "earnings", "annual"),
    [
        (700, 24480, 8400),
        (700, 25000, 8140),
        (700, 27000, 7140),
        (900, 24480, 10800),
        (900, 25000, 10540),
        (900, 27000, 9540),
        (1100, 24480, 13200),
        (1100, 25000, 12940),
        (1100, 27000, 11940),
    ],
)
def test_publication_05_10069_annual_benefit_table(rate, earnings, annual):
    ledger = r.apply_ret_year(
        _record(_beneficiary("nh", rate, earnings=_wages(earnings)))
    )
    assert sum(row.payment for row in ledger.months) == annual


@pytest.mark.parametrize(
    ("fra", "wages", "deduction", "through", "received"),
    [
        (None, _wages(33400), 4460, 12, 5140),
        (8, _wages(66000, after_fra=6000), 280, 7, 5320),
    ],
)
def test_receiving_benefits_while_working_examples(
    fra, wages, deduction, through, received
):
    ledger = r.apply_ret_year(
        _record(_beneficiary("nh", 800, earnings=wages, fra=fra))
    )
    assert _worker(ledger).charged == deduction
    assert (
        sum(row.payment for row in ledger.months if row.month <= through)
        == received
    )


def _initial_grace(year, benefit_type, entitled, nonservice, fra=None):
    entitled = frozenset(entitled)
    months = tuple(
        (
            GraceMonth(
                frozenset({benefit_type}),
                frozenset({benefit_type}),
                month in nonservice,
            )
            if month in entitled
            else GraceMonth()
        )
        for month in range(1, 13)
    )
    return grace_year(year, GraceYearState(), months, fra_month=fra)


def test_publication_05_10069_october_retirement_special_rule():
    earnings = r.WorkEarnings(wages=(45000,) + (0,) * 9 + (500, 500))
    grace = _initial_grace(2026, T.RIB, (11, 12), (11, 12))
    # The publication supplies no benefit rate: 600 is an invented fixture.
    ledger = r.apply_ret_year(
        _record(
            _beneficiary(
                "nh", 600, earnings=earnings, entitled=(11, 12), grace=grace
            )
        )
    )
    assert sum(row.payment for row in ledger.months) == 1200
    assert all(row.deduction == 0 for row in ledger.months)
    assert grace.protected_months == frozenset({11, 12})


def test_special_earnings_limit_john_smith_example():
    earnings = r.WorkEarnings(
        wages=(37000,) + (0,) * 11,
        nese=3000,
        self_employment_months=frozenset({10, 11, 12}),
        substantial_service_months=frozenset({10, 11, 12}),
    )
    grace = _initial_grace(2026, T.RIB, range(7, 13), (7, 8, 9))
    # The webpage supplies no benefit rate: 600 is an invented fixture.
    ledger = r.apply_ret_year(
        _record(
            _beneficiary(
                "nh",
                600,
                earnings=earnings,
                entitled=range(7, 13),
                grace=grace,
            )
        )
    )
    rows = _monthly(ledger)
    assert all(rows[m].payment == 600 for m in (7, 8, 9))
    assert all(rows[m].payment == 0 for m in (10, 11, 12))
    assert _worker(ledger).countable_earnings == 40000


def test_cfr_404_439_original_benefit_partial_payment_example():
    exact = r.partial_payments(
        F(200),
        {"nh": F(165), "spouse": F("82.50")},
        {"nh": F(165), "spouse": F("82.50")},
    )
    assert exact["nh"] == F(400, 3)
    assert exact["spouse"] == F(200, 3)
    assert [int(exact[key]) for key in ("nh", "spouse")] == [133, 66]
    assert sum(int(value) for value in exact.values()) == 199


def test_cfr_404_440_dime_sum_and_printed_pool_are_pinned_side_by_side():
    rates = {
        "nh": F(100),
        "spouse": F("16.60"),
        "c1": F("16.60"),
        "c2": F("16.60"),
    }
    originals = {"nh": F(100), "spouse": F(50), "c1": F(50), "c2": F(50)}
    gross = sum(rates.values())
    assert gross == F("149.80")
    source_pool = F(150) - 25
    ledger_pool = gross - 25
    assert source_pool == 125 and ledger_pool == F("124.80")
    source_result = r.partial_payments(source_pool, rates, originals)
    ledger_result = r.partial_payments(ledger_pool, rates, originals)
    assert source_result["nh"] == F("75.20")
    assert ledger_result["nh"] == F(75)
    for result in (source_result, ledger_result):
        assert result.undistributed_subdollar_residual == 0
        assert [int(result[key]) for key in ("nh", "spouse", "c1", "c2")] == [
            75,
            16,
            16,
            16,
        ]


def test_cfr_404_441_number_holder_then_spouse_with_grace_month():
    grace = _initial_grace(2026, T.RIB, range(1, 13), (2,))
    # Invent wages with the cited excess and February as the only NSM.
    # The CFR's historical $340 monthly limit is outside ledger scope;
    # the 2026 fixture uses R1's actual exempt amount for that year.
    nh_earnings = r.WorkEarnings(wages=(6678, 0) + (2100,) * 10)
    ledger = r.apply_ret_year(
        _record(
            _beneficiary("nh", 176, earnings=nh_earnings, grace=grace),
            _beneficiary(
                "spouse",
                88,
                benefit_type=T.SPOUSE,
                earnings=_excess_earnings(265),
            ),
        )
    )
    nh = _monthly(ledger)
    spouse = _monthly(ledger, "spouse")
    assert nh[2].payment == 176
    assert all(nh[m].payment == 0 for m in (1, 3, 4, 5, 6, 7))
    assert nh[8].net_due == 166
    assert spouse[8].nh_deduction == 5 and spouse[8].own_deduction == 83
    assert spouse[2].own_deduction == spouse[9].own_deduction == 88
    assert spouse[10].own_deduction == 6 and spouse[10].payment == 82
    assert _worker(ledger).charged == 1599
    assert _worker(ledger, "spouse").charged == 265


def test_cfr_404_435_don_initial_grace_example():
    decision = _initial_grace(2000, T.RIB, range(5, 13), range(5, 13))
    # Don's age62, 15000 Jan-April and protected May-Dec are source facts;
    # the calendar year and 600-dollar benefit are invented fixture choices.
    ledger = r.apply_ret_year(
        _record(
            _beneficiary(
                "nh",
                600,
                earnings=_wages(15000),
                entitled=range(5, 13),
                grace=decision,
            ),
            year=2000,
        )
    )
    assert decision.protected_months == frozenset(range(5, 13))
    assert all(_monthly(ledger)[m].payment == 600 for m in range(5, 13))
