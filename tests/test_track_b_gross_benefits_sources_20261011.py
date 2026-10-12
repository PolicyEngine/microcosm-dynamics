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


@pytest.mark.parametrize(("source_id", "quote"), RULE_QUOTES)
def test_rule_text_is_quoted_from_the_captures(source_id, quote):
    assert quote in source_text(source_id)


def test_every_new_capture_has_a_rule_and_pinned_bytes():
    sources = {
        source["id"]: source
        for source in manifest()["sources"]
        if source["retrieved_at_utc"].startswith("2026-10-11T")
    }
    assert len(sources) == 21
    assert set(sources) == {source_id for source_id, _ in RULE_QUOTES}
    for source_id, source in sources.items():
        data = (SOURCES / source["file"]).read_bytes()
        assert len(data) == source["bytes"], source_id
        assert hashlib.sha256(data).hexdigest() == source["sha256"]
        assert source["poms_transmittal"]
        assert source["page_date"]
