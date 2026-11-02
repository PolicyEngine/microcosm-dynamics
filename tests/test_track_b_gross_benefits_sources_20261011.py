"""Track B G source conformance for the October 2026 review captures.

Verification class: statutory conformance. These verbatim instructions
establish the cited rules and continuing refusal boundaries; they contain
no population data and admit no behavioral or forecast claim. The combined
maximum instructions are retained to specify the refused future surface.
"""

from __future__ import annotations

import hashlib

import pytest

from tests.track_b_gross_benefit_support import (
    SOURCES,
    manifest,
    source_text,
)

RULE_QUOTES = (
    (
        "poms_gn_02603_020",
        "Take the reduction for the family maximum after making the "
        "deductions listed on GN 02603.040 .",
    ),
    (
        "poms_gn_02603_040",
        "Work deductions for the number holder that apply to the auxiliaries",
    ),
    (
        "poms_gn_02603_090",
        "Determine household status using the configuration that exists "
        "when the beneficiary files the annual report.",
    ),
    (
        "poms_rs_02501_130",
        "Readjust auxiliary benefit rates up to the family maximum when "
        "an individual is deemed not entitled to benefits for a month",
    ),
    (
        "poms_rs_02501_155",
        "Reduce the maximum applicable to the other beneficiaries by "
        "the amount of the partial benefit due the beneficiary.",
    ),
    (
        "poms_rs_02501_160",
        "E and C1 will receive the extra $33 per month only when the "
        "deductions become permanent.",
    ),
    (
        "poms_gn_02603_045",
        "Only pay this increase to others who are not dually entitled. "
        "If there are no other beneficiaries who are not dually entitled, "
        "this change does not apply.",
    ),
    (
        "poms_gn_02603_045",
        "Always consider the possibility of a Combined Family Maximum "
        "based on children who are simultaneously entitled on more than "
        "one record before applying deduction before reduction based on "
        "dual entitlement.",
    ),
    (
        "poms_gn_02603_050",
        "If dual entitlement reduces a beneficiary's rate to $0.00 "
        "(technically entitled) regardless of other deductions that may "
        "apply for any other beneficiary on record disregard the dually "
        "entitled beneficiary when distributing the family maximum.",
    ),
    (
        "poms_gn_02603_050",
        "Age reduction amount for all workers or deductees",
    ),
    (
        "poms_gn_02603_050",
        "Partial benefit payable to any worker or deductee",
    ),
    (
        "poms_gn_02603_050",
        "Use the OB if the result of this calculation is greater than "
        "the OB.",
    ),
    (
        "poms_gn_02603_060",
        "In order to redistribute only the amount being withheld because "
        "of dual entitlement we must account for the entire $83.30 due B. "
        "Of that amount $80.00 is withheld for dual entitlement, $2.40 is "
        "payable and $0.90 is withheld for age reduction.",
    ),
    (
        "poms_rs_00615_003",
        "FRA for retirement or spouse's benefits is age 65.",
    ),
    (
        "poms_rs_00615_010",
        "For benefits payable after 12/83, there is no additional "
        "reduction for months prior to age 60.",
    ),
    (
        "poms_rs_00615_010",
        "Reduce the spouse's benefit (adjusted for the maximum if "
        "necessary) by the number of months of entitlement before FRA.",
    ),
    (
        "poms_rs_00615_010",
        "Determine the WIB under the appropriate rules summarized above "
        "subject to the condition that it shall not be less than the "
        "mother's or father's benefit would be for any month the "
        "widow(er) has an entitled child in care (see RS 00615.340 ).",
    ),
    (
        "poms_rs_00615_310",
        "DWB are reduced by 28.5 percent. No additional reduction "
        "applies for the period before age 60.",
    ),
    (
        "poms_rs_00615_310",
        "Beneficiaries who were entitled to DWB prior to 1/84 had their "
        "benefits recalculated effective 1/84 as if the reduction for "
        "the period prior to age 60 did not exist.",
    ),
    (
        "poms_rs_00615_340",
        "Any month a person receiving a reduced widow(er) benefit has an "
        "entitled child-in-care they cannot receive less than the amount "
        "a mother and father would receive. The benefit amount is raised "
        "for all months the child is in care.",
    ),
    (
        "poms_rs_00615_340",
        "At FRA attainment the widow(er) is granted an ARF to remove all "
        "months the increase was applied.",
    ),
    (
        "poms_rs_00615_340",
        "If the widow(er) receives a higher benefit as a widow(er) do not "
        "change the benefit to the mother and father amount and an ARF "
        "will not apply.",
    ),
    (
        "poms_rs_00615_340",
        "A surviving divorced spouse who is eligible for and has elected "
        "reduced benefits can receive the mother's/father's benefit "
        "amount if larger than the reduced WIB without meeting the "
        "additional requirements in RS 00208.001",
    ),
    (
        "poms_rs_00615_340",
        "This policy applies to benefits payable 1/73 and later.",
    ),
    (
        "poms_rs_00615_315",
        "When an eligible person elects to switch from WIB to DWB or "
        "DWB to WIB the PIA and the reduction factors remain the same.",
    ),
    (
        "poms_rs_00615_590",
        "The 1983 amendments repealed the additional reduction percentage "
        "for disabled widow(er)'s benefits. Determine the reduction "
        "factor as if the widow(er) attains age 60 in the MOET.",
    ),
    (
        "poms_rs_00615_712",
        "The only criterion for this to apply is entitlement for the "
        "specific month of 5/78. Entitlement before or after 5/78 "
        "is immaterial.",
    ),
    (
        "poms_rs_00615_758",
        "The family maximum must be reapportioned among those who "
        "remain entitled to benefits after the family composition changes.",
    ),
    (
        "poms_rs_00615_770",
        "A combined family maximum equals the sum of the table or formula "
        "maximums on the records on which the child is simultaneously "
        "entitled, but not more than the maximum allowable limits "
        "established in the chart in the following section.",
    ),
    (
        "poms_rs_00615_770",
        "Splitting of entitlement is not permitted because all eligible "
        "children on the same SSNs are handled as an indivisible group.",
    ),
    (
        "poms_rs_00615_772",
        "A simultaneously entitled child will be paid on the SSN with "
        "the higher PIA, unless one of the exceptions in "
        "RS 00615.772A.2. applies.",
    ),
    (
        "poms_rs_00615_774",
        "A suspension, deduction, or offset event is not cause for "
        "re-determining the SSN on which to pay benefits and is not "
        "a factor in the initial determination of which SSN will be "
        "used for payment except for suspension due to EPE and EXR/IRP",
    ),
    (
        "poms_rs_00615_776",
        "When one of the children who are currently entitled to child's "
        "benefits on a particular SSN files an application for child's "
        "benefits on another SSN, all such children who could also be "
        "entitled on the second SSN are automatically entitled on that SSN.",
    ),
    (
        "poms_rs_00615_778",
        "If entitlement on the other SSN terminates the maximums can "
        "no longer be combined.",
    ),
    (
        "poms_rs_00202_005",
        "No benefits are payable under this provision prior to "
        "January 1985.",
    ),
    (
        "poms_rs_00202_005",
        "be finally divorced from the NH for at least 2 continuous years.",
    ),
    (
        "poms_rs_00202_100",
        "For months of entitlement prior to January 2024, review the "
        "NH's record to determine if evidence of a non-covered pension "
        "exists.",
    ),
    (
        "poms_rs_00202_100",
        "entitlement of the divorced spouse will not adversely affect "
        "their benefit amount or the benefits of any future auxiliaries",
    ),
    (
        "poms_rs_00209_001",
        "not be entitled to retirement insurance benefit (RIB) equal "
        "to or exceeding the amount of the parent's original benefit "
        "(One parent = 82 1/2%; Two parents = 75%);",
    ),
    (
        "poms_rs_00209_015",
        "There is no actuarial reduction of benefits for months before "
        "attainment of full retirement age. The parent's benefit is "
        "subject to reduction for the family maximum.",
    ),
    (
        "poms_rs_00209_015",
        "Benefit rate equals 75% of the worker's PIA for each month "
        "both are entitled.",
    ),
    (
        "poms_rs_00209_015",
        "DIB larger than parent's benefit - DIB is only benefit payable "
        "but technical entitlement to parent's benefit continues.",
    ),
    (
        "poms_gn_02608_100",
        "On January 5, 2025, the President signed the Social Security "
        "Fairness Act of 2023 (SSFA), which eliminates the offset of "
        "Social Security benefits under GPO for benefits payable for "
        "months after December 2023.",
    ),
    (
        "poms_rs_00605_360",
        "On January 5, 2025, the President signed the Social Security "
        "Fairness Act of 2023 (SSFA), which eliminates the WEP reduction "
        "for benefits payable for months after December 2023.",
    ),
)


# Some older manifest entries had integrity checks alone; others had table
# checks without a quoted rule. These instructions substantively pin the
# arithmetic and refusal boundaries cited by G, so every retained capture
# has a quoted rule or a registered example.
REFERENCE_RULE_QUOTES = (
    (
        "poms_rs_00605_900",
        "Bend points are used to derive the PIA from the AIME and the "
        "family maximum from the PIA. A different set of bend points "
        "is established each year.",
    ),
    (
        "poms_rs_00615_020",
        "Method B - Both benefits calculated and reduced independently; "
        "small MBA paid plus excess of larger MBA.",
    ),
    (
        "poms_rs_00615_101",
        "Round the result down to the next dime for benefits after 5/82 "
        "and up to the next dime for benefits prior to 6/82.",
    ),
    (
        "poms_rs_00615_201",
        "When RIB entitlement is involved, for months with a child-in-care, "
        "the amount payable as a spouse will always be the difference "
        "between the unreduced spouse benefit and the reduced RIB rate.",
    ),
    (
        "poms_rs_00615_210",
        "Reduce the OB for the maximum, then",
    ),
    (
        "poms_rs_00615_250",
        "Then subtract the RIB PIA from the unreduced spouse's benefit, "
        "and reduce the excess by the spouse's reduction factor.",
    ),
    (
        "poms_rs_00615_260",
        "Reduce the DIB PIA by the number of months of reduced RIB "
        "prior to the DIB MOE.",
    ),
    (
        "poms_rs_00615_680",
        "The benefit of a divorced spouse or surviving divorced spouse "
        "(B6/BR, D6/DC or W6/WR) is not subject to reduction for the maximum.",
    ),
    (
        "poms_rs_00615_684",
        "When there are both a deemed or putative spouse and a legal spouse "
        "on a record, the legal spouse is paid outside the family maximum",
    ),
    (
        "poms_rs_00615_695",
        "Do not subtract the amount after the DRC increase.",
    ),
    (
        "poms_rs_00615_730",
        "If the total of all original rates exceeds the maximum, "
        "the rates must be adjusted.",
    ),
    (
        "poms_rs_00615_740",
        "The NH was ever entitled to DIB before July 1980",
    ),
    (
        "poms_rs_00615_742",
        "The DMAX will be converted to an AIME maximum when "
        "the DIB is changed to RIB or the NH dies.",
    ),
    (
        "poms_rs_00615_752",
        "If an auxiliary or survivor is entitled to reduced benefits "
        "or is subject to offset, use the unreduced amount.",
    ),
    (
        "poms_rs_00615_754",
        "Benefits are first adjusted for the maximum and then reduced "
        "for age.",
    ),
    (
        "poms_rs_00615_766",
        "If a deduction is made before reduction for the maximum, "
        "other beneficiaries on the record may receive an increase.",
    ),
    (
        "ssa_act_202_215",
        "Such mother's or father's insurance benefit for each month "
        "shall be equal to three-fourths of the primary insurance amount "
        "of such deceased individual.",
    ),
    (
        "ssa_oact_dibfamilymax",
        "The family maximum for a family of a disabled worker is "
        "85 percent of the worker's Average Indexed Monthly Earnings "
        "(AIME). However, it cannot be less than the worker's PIA "
        "nor more than 150 percent of the PIA.",
    ),
)


@pytest.mark.parametrize(("source_id", "quote"), RULE_QUOTES)
def test_rule_text_is_quoted_from_the_captures(source_id, quote):
    assert quote in source_text(source_id)


@pytest.mark.parametrize(("source_id", "quote"), REFERENCE_RULE_QUOTES)
def test_reference_rule_text_is_quoted_from_the_captures(source_id, quote):
    assert quote in source_text(source_id)


def test_every_manifest_capture_has_a_quoted_rule_or_registered_figure():
    from tests.test_track_b_gross_benefits import (
        RULE_QUOTES as original_rules,
    )
    from tests.test_track_b_gross_benefits import (
        WORKED_EXAMPLE_QUOTES as original_figures,
    )
    from tests.test_track_b_gross_benefits_registry import REGISTRY

    quoted = (
        set(original_rules)
        | set(original_figures)
        | {source_id for source_id, _ in RULE_QUOTES}
        | {source_id for source_id, _ in REFERENCE_RULE_QUOTES}
        | {example["capture_id"] for example in REGISTRY["examples"]}
    )
    assert quoted == {source["id"] for source in manifest()["sources"]}


def test_every_new_capture_has_a_rule_and_pinned_bytes():
    sources = {
        source["id"]: source
        for source in manifest()["sources"]
        if source["retrieved_at_utc"].startswith(
            ("2026-10-11T", "2026-10-12T")
        )
    }
    assert len(sources) == 28
    assert set(sources) == {source_id for source_id, _ in RULE_QUOTES}
    for source_id, source in sources.items():
        data = (SOURCES / source["file"]).read_bytes()
        assert len(data) == source["bytes"], source_id
        assert hashlib.sha256(data).hexdigest() == source["sha256"]
        assert source["poms_transmittal"]
        assert source["page_date"]
