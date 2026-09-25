"""Table 2 of the Report (PDF page 29) as formula checks (ruling C5).

Ruling C5 of the cleared definitions extract clears PDF page 29 of
Favreault, Mermin and Steuerle (2006), Table 2 ("Authors' calculations"),
for formula unit tests only.  It is **never** a comparator, a target, a
calibration input or a stand-in for a Table 5 option: its NCRP-style
column is not a Table 5 schedule, and its poverty measure (the HHS
threshold for one person) is not the Census aged threshold of fn. 25.  The
page was read as text only (``pdftotext -layout -f 29 -l 29``, Poppler
26.09.0, PDF SHA-256 ``cc22db1d…``); no other page of the Report was
opened.  A cell the formulas do not reproduce is recorded here as a
finding and never tuned to.

Stylized worker (the page's notes): never married, born 1943, claims in
2005 at 62, no spouse or survivor benefit, work from age 20 without
interruption.  The oracle's parameters come from the policyengine-us
checkout (``POPULACE_DYNAMICS_PE_US_DIR`` or the default path); the test
skips when it is absent.

Findings recorded by these tests (the draft specification, section 17,
repeats them):

1. Row 1c, column 6 (NCRP-style minimum at the NRA) prints 82%.  The
   text's NCRP-style schedule gives 60% of poverty at 20 years, below
   column 2's current-law 80%, so max(current law, minimum) is "no change"
   (NC).  82% equals column 4's value for that row.
2. Columns 1 and 2 (current law, SSI-ineligible, at 62 and at the NRA) are
   not related by the 25% reduction alone for rows 1c, 1d and 2d, even
   allowing for the printed rounding.  The page does not say on which
   year's benefit and threshold the NRA columns are evaluated.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from populace_dynamics.min_benefit_track_m import coverage
from populace_dynamics.min_benefit_track_m import policy as pol
from populace_dynamics.ss import benefits
from populace_dynamics.ss.params import load_ssa_parameters

_PE_US = Path(
    os.environ.get(
        "POPULACE_DYNAMICS_PE_US_DIR", "~/PolicyEngine/policyengine-us"
    )
).expanduser()
pytestmark = pytest.mark.skipif(
    not (_PE_US / "policyengine_us").is_dir(),
    reason="needs a policyengine-us checkout (POPULACE_DYNAMICS_PE_US_DIR)",
)

NC = "NC"
BIRTH_YEAR = 1943
#: Table 2 as printed (PDF p. 29): row -> (work years, column 1, column 2,
#: column 5, column 6).  Columns 1-2: current law, SSI-ineligible, at 62
#: and at the NRA; columns 5-6: NCRP-style minimum (SSI-ineligible), at 62
#: and at the NRA.  Percent of the single-person poverty threshold.
TABLE2 = {
    "1a": (0, 0, 0, NC, NC),
    "1b": (10, 38, 50, NC, NC),
    "1c": (20, 61, 80, NC, 82),
    "1d": (40, 76, 99, NC, 100),
    "2a": (0, 0, 0, NC, NC),
    "2b": (10, 19, 25, NC, NC),
    "2c": (20, 36, 47, 45, 60),
    "2d": (40, 56, 73, 75, 100),
    "3a": (0, 0, 0, NC, NC),
    "3b": (10, 3, 3, NC, NC),
    "3c": (20, 7, 9, 45, 60),
    "3d": (40, 20, 27, 75, 100),
}
#: Columns 7-8 (current-law OASI replacement rate at 62 and the NRA), the
#: same in every row with work.
REPLACEMENT = (68, 90)
#: The NCRP-style minimum as the text describes NCRP (PDF p. 14, quoted in
#: the cleared extract): 60% of poverty at 20 work years plus 2 points a
#: year to 40.  Not a Table 5 schedule.
NCRP_STYLE = pol.Schedule("ncrp_style_text", ((20, 0.60), (40, 1.00)))
#: Recorded findings (module docstring), never tuned to.
FINDING_NCRP_CELLS = {("1c", "nra")}
FINDING_CURRENT_LAW_ROWS = {"1c", "1d", "2d"}


@pytest.fixture(scope="module")
def params():
    return load_ssa_parameters()


@pytest.fixture(scope="module")
def factor_at_62(params):
    """The oracle's worker reduction for the 1943 cohort claiming at 62."""

    months_early = params.fra_months(BIRTH_YEAR) - 62 * 12
    return 1.0 - benefits.early_reduction(months_early, params)


def test_the_1943_cohort_claims_48_months_early(params, factor_at_62):
    # The page's fn. 18 text: early eligibility 62, NRA 66 for this cohort.
    assert params.fra_months(BIRTH_YEAR) == 66 * 12
    # 36 x 5/9% + 12 x 5/12% = 20% + 5% = 25%.
    assert factor_at_62 == pytest.approx(0.75)


def _ncrp_cell(years: int, current_law: int, factor: float):
    """max(current law, minimum), printed as NC when current law wins."""

    minimum = 100.0 * NCRP_STYLE.share(years) * factor
    if minimum <= current_law:
        return NC
    return round(minimum)


def test_ncrp_style_minimum_cells(factor_at_62):
    mismatches = set()
    for row, (years, cl62, clnra, ncrp62, ncrpnra) in TABLE2.items():
        # fn. 26(1): the minimum is set at PIA calculation, so the claim-age
        # reduction applies to it: 60% -> 45% and 100% -> 75% at 62.
        if _ncrp_cell(years, cl62, factor_at_62) != ncrp62:
            mismatches.add((row, "62"))
        if _ncrp_cell(years, clnra, 1.0) != ncrpnra:
            mismatches.add((row, "nra"))
    assert mismatches == FINDING_NCRP_CELLS


def test_the_minimum_needs_its_floor_years():
    # Below NCRP's 20 years (rows a and b: 0 and 10 years) nothing changes.
    for row, (years, *_rest, ncrp62, ncrpnra) in TABLE2.items():
        if years < NCRP_STYLE.floor_years:
            assert (ncrp62, ncrpnra) == (NC, NC), row


def _consistent_ratio(at_62: int, at_nra: int, factor: float) -> bool:
    """Whether ``factor`` lies within the printed rounding of the ratio."""

    low = (at_62 - 0.5) / (at_nra + 0.5)
    high = (at_62 + 0.5) / (at_nra - 0.5)
    return low <= factor <= high


def test_current_law_columns_and_the_claim_age_factor(factor_at_62):
    inconsistent = {
        row
        for row, (_, cl62, clnra, _, _) in TABLE2.items()
        if clnra > 0 and not _consistent_ratio(cl62, clnra, factor_at_62)
    }
    assert inconsistent == FINDING_CURRENT_LAW_ROWS


def test_replacement_rate_columns_and_the_claim_age_factor(factor_at_62):
    assert _consistent_ratio(*REPLACEMENT, factor_at_62)


def test_four_quarters_of_coverage_in_2006():
    # Rows 3a-3d: "Exactly 4 CQ threshold in all years ($3,880/year in
    # 2006)": four times the 2006 quarter-of-coverage amount.
    qc = coverage.load_qc_amounts()
    assert 4 * qc.amount(2006) == 3_880.0
    assert coverage.annual_coverage_amount(2006, qc, {}) == 3_880.0
    assert qc.source["kind"] == "policyengine_us_checkout"
    assert len(qc.source["sha256"]) == 64
