"""Track B milestone G against the repository's live parameter source.

Production callers pass the policyengine-us bundle
(``ss.params.load_ssa_parameters``). These checks confirm that bundle
reproduces SSA's published family-maximum bend points for every year
1979-2026, passes the statutory-rate cross-check, and carries the 402(w)
schedule the unit tier assumes. Skipped without a policyengine-us checkout.
"""

from __future__ import annotations

import os
from fractions import Fraction as F
from pathlib import Path

import pytest

from populace_dynamics.ss.params import load_ssa_parameters
from populace_dynamics.track_b import gross_benefits as g
from tests.track_b_gross_benefit_support import (
    DELAYED_CREDIT_SCHEDULE,
    poms_bend_point_table,
    published_nawi,
)

PE_US = Path("~/PolicyEngine/policyengine-us").expanduser()
pytestmark = pytest.mark.skipif(
    not PE_US.is_dir() and "POPULACE_DYNAMICS_PE_US_DIR" not in os.environ,
    reason="policyengine-us not checked out and "
    "POPULACE_DYNAMICS_PE_US_DIR unset",
)


@pytest.fixture(scope="module")
def params():
    return load_ssa_parameters()


def test_policyengine_us_bundle_passes_the_statutory_rate_check(params):
    rates = g.statutory_rates(params)
    assert rates.worker_first == F(1, 180)
    assert rates.spouse_first == F(1, 144)
    assert rates.pe_us_revision == params.pe_us_revision != "unknown"


def test_policyengine_us_nawi_reproduces_published_bend_points(params):
    for year, (_, _, *family) in poms_bend_point_table().items():
        assert g.family_maximum_bend_points(year, params) == tuple(family)


def test_policyengine_us_nawi_matches_ssa_through_2024(params):
    for year, value in published_nawi().items():
        if 1977 <= year <= 2024:
            assert params.nawi[year] == pytest.approx(value, abs=0.005)


def test_policyengine_us_delayed_credit_schedule_is_the_statutes(params):
    assert params.delayed_credit_by_birth_year == DELAYED_CREDIT_SCHEDULE


def test_worked_examples_hold_on_the_live_bundle(params):
    record = g.WorkerRecord(g.FamilyKind.SURVIVOR, 2015, F(1200))
    assert g.record_state(record, params).family_maximum == F("1975.60")
    assert g.retirement_survivor_family_maximum(
        F("2371.00"), 2026, params
    ) == F("4444.60")
    base, credited = g.worker_age_adjusted(F(1000), 0, 30, 1940, params)
    assert credited == F(1175)
    assert g.worker_age_adjusted(F("802.80"), 5, 0, None, params)[0] == F(
        "780.50"
    )
