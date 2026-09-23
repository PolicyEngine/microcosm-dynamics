"""Registered-run value checks of the Track A oracle's statutory inputs.

These tests read committed evidence under "data/external": the statutory
capture (data/external/track_a_statutory_parameters.json), the TR2008
capture and the realized COLA history.  The oracle parameters are built
from the committed capture (no policyengine-us checkout is read), and each
perturbation below is INVENTED to show that the check bound to that value
names it.  Nothing here reads PSID or a comparator value.
"""

from __future__ import annotations

import dataclasses
import hashlib
from pathlib import Path

import pytest

from populace_dynamics.cola_track_a import statutory
from populace_dynamics.cola_track_a.runner import tr2008_baseline_cola
from populace_dynamics.data import tr2008
from populace_dynamics.estimates.parameters import load_cola_history

ROOT = Path(__file__).resolve().parents[2]
CAPTURE = ROOT / "data" / "external" / "track_a_statutory_parameters.json"

CHECKS = {
    "realized_cola_history",
    "contribution_and_benefit_base",
    "contribution_and_benefit_base_tr2008",
    "awi_before_1975",
    "bend_points",
    "pia_factors",
    "full_retirement_age",
    "early_reduction",
    "delayed_retirement_credit",
    "auxiliary_constants",
}


@pytest.fixture(scope="module")
def params():
    return statutory.captured_ssa_parameters()


@pytest.fixture(scope="module")
def baseline():
    return tr2008_baseline_cola(load_cola_history())


def _checks(params, baseline, **kwargs):
    values = {
        "first_tr2008_rate_year": 2008,
        "reference_year": 2030,
        "last_earnings_year": 2010,
    }
    values.update(kwargs)
    return statutory.statutory_value_checks(params, baseline, **values)


def _inconsistent(checks) -> set[str]:
    return {name for name, check in checks.items() if not check["consistent"]}


def test_capture_is_the_committed_file_and_its_pin():
    assert statutory.CAPTURE_PATH == CAPTURE
    digest = hashlib.sha256(CAPTURE.read_bytes()).hexdigest()
    assert digest == statutory.CAPTURE_SHA256
    capture = statutory.load_statutory_capture()
    assert capture["schema_version"] == statutory.CAPTURE_SCHEMA_VERSION
    # The capture names the policyengine-us files it came from, by hash.
    assert capture["source"]["policyengine_us_files_sha256"]
    with pytest.raises(ValueError, match="re-pin"):
        statutory.load_statutory_capture(expected_sha256="0" * 64)


def test_a_changed_capture_file_is_refused(tmp_path):
    changed = tmp_path / "capture.json"
    changed.write_bytes(CAPTURE.read_bytes().replace(b"0.9", b"0.8", 1))
    with pytest.raises(ValueError, match="sha256"):
        statutory.load_statutory_capture(changed)


def test_captured_parameters_pass_every_check(params, baseline):
    checks = _checks(params, baseline)
    assert set(checks) == CHECKS
    assert _inconsistent(checks) == set()
    realized = checks["realized_cola_history"]
    # load_cola_history's runtime span is 1979-2022 (the oracle's first
    # eligibility year); every year of it before 2008 is compared.
    assert "1979-2007" in realized["expected"]
    assert realized["source"]["sha256"] == (
        load_cola_history().provenance["sha256"]
    )
    for name in CHECKS - {
        "realized_cola_history",
        "contribution_and_benefit_base_tr2008",
    }:
        assert checks[name]["source"]["sha256"] == statutory.CAPTURE_SHA256


def test_tr2008_wage_base_projections_are_documented_not_mismatched(
    params, baseline
):
    # V.C1 prints projected bases from 2009; the oracle reads the realized
    # ones.  Both 2009 and 2010 (the last career year) are listed as
    # documented differences, and the check stays consistent.
    check = _checks(params, baseline)["contribution_and_benefit_base_tr2008"]
    assert check["consistent"] is True
    assert set(check["documented_differences"]) == {"2009", "2010"}
    printed = {
        entry.year: entry
        for entry in tr2008.contribution_benefit_base_path(2009, 2010)
    }
    for year, record in check["documented_differences"].items():
        entry = printed[int(year)]
        assert record["tr2008"] == entry.amount
        assert record["tr2008_source"] == "tr2008_v_c1_projected"
        assert record["runtime"] == params.wage_base_for(int(year))
    # Through 2008 only historical and actual rows enter, so nothing is
    # documented.
    earlier = _checks(params, baseline, last_earnings_year=2008)
    assert (
        earlier["contribution_and_benefit_base_tr2008"][
            "documented_differences"
        ]
        == {}
    )


def _replace(params, **changes):
    return dataclasses.replace(params, **changes)


def _nawi(params, year, factor):
    nawi = dict(params.nawi)
    nawi[year] = nawi[year] * factor
    return nawi


def _wage_base(params, year, amount):
    base = dict(params.wage_base)
    base[year] = amount
    return base


# Each case is an INVENTED perturbation of one statutory value and the
# check(s) that must name it.
PERTURBATIONS = [
    (
        "wage base 1990",
        lambda p: _replace(p, wage_base=_wage_base(p, 1990, 51_000.0)),
        {
            "contribution_and_benefit_base",
            "contribution_and_benefit_base_tr2008",
        },
        "1990",
    ),
    (
        "AWI 1960",
        lambda p: _replace(p, nawi=_nawi(p, 1960, 1.01)),
        {"awi_before_1975"},
        "1960",
    ),
    (
        "AWI 2000 (the 2002 bend points)",
        lambda p: _replace(p, nawi=_nawi(p, 2000, 1.01)),
        {"bend_points"},
        "2002",
    ),
    (
        "PIA factors",
        lambda p: _replace(p, pia_factors=(0.9, 0.32, 0.16)),
        {"pia_factors"},
        None,
    ),
    (
        "FRA schedule",
        lambda p: _replace(
            p,
            fra_months_by_birth_year=[
                *p.fra_months_by_birth_year[:-1],
                (p.fra_months_by_birth_year[-1][0], 816),
            ],
        ),
        {"full_retirement_age"},
        None,
    ),
    (
        "early reduction rate",
        lambda p: _replace(p, early_monthly_rates=(5 / 900, 5 / 1000)),
        {"early_reduction"},
        None,
    ),
    (
        "early first bracket",
        lambda p: _replace(p, early_first_bracket_months=24),
        {"early_reduction"},
        None,
    ),
    (
        "delayed credit rate",
        lambda p: _replace(
            p,
            delayed_credit_by_birth_year=[
                *p.delayed_credit_by_birth_year[:-1],
                (p.delayed_credit_by_birth_year[-1][0], 0.07),
            ],
        ),
        {"delayed_retirement_credit"},
        None,
    ),
    (
        "delayed credit cap",
        lambda p: _replace(p, max_delayed_months=36),
        {"delayed_retirement_credit"},
        None,
    ),
    (
        "survivor reduction floor",
        lambda p: _replace(p, survivor_reduction_floor=0.7),
        {"auxiliary_constants"},
        "survivor_reduction_floor",
    ),
    (
        "spousal reduction rates",
        lambda p: _replace(p, spousal_early_monthly_rates=(0.007, 5 / 1200)),
        {"auxiliary_constants"},
        "spousal_early_monthly_rates",
    ),
]


@pytest.mark.parametrize(
    ("label", "perturb", "failing", "key"),
    PERTURBATIONS,
    ids=[case[0] for case in PERTURBATIONS],
)
def test_each_statutory_value_is_bound_to_its_source(
    params, baseline, label, perturb, failing, key
):
    checks = _checks(perturb(params), baseline)
    assert _inconsistent(checks) == failing, label
    if key is not None:
        for name in failing:
            assert key in checks[name]["mismatched"], (label, name)


class _ReplacedRates:
    """INVENTED rate source: the baseline with some years replaced."""

    def __init__(self, baseline, replaced):
        self._baseline = baseline
        self._replaced = dict(replaced)

    def rate_for_determination_year(self, year):
        if year in self._replaced:
            value = self._replaced[year]
            if value is None:
                raise KeyError(year)
            return value
        return self._baseline.rate_for_determination_year(year)


def test_realized_cola_history_before_2008_is_bound(params, baseline):
    realized = load_cola_history()
    # INVENTED: 1990's 5.4 percent read as 5.0, and 1985 missing.
    rates = _ReplacedRates(baseline, {1990: 0.05, 1985: None})
    checks = _checks(params, rates)
    assert _inconsistent(checks) == {"realized_cola_history"}
    mismatched = checks["realized_cola_history"]["mismatched"]
    assert mismatched == {
        "1985": {"committed": realized[1985], "runtime": None},
        "1990": {"committed": realized[1990], "runtime": 0.05},
    }


def test_realized_history_check_stops_at_the_first_tr2008_year(
    params, baseline
):
    # The TR2008 2.7 percent for 2008 is not the realized 5.8 percent, and
    # 2008 is not compared: it enters ratios and belongs to the COLA-path
    # check.  With a first TR2008 year of 2009 it would be compared.
    assert baseline.rate_for_determination_year(2008) != (
        load_cola_history()[2008]
    )
    assert _checks(params, baseline)["realized_cola_history"]["consistent"]
    later = _checks(params, baseline, first_tr2008_rate_year=2009)
    assert set(later["realized_cola_history"]["mismatched"]) == {"2008"}


def test_captured_parameters_carry_tr2008_awi_from_1975(params):
    capture = statutory.load_statutory_capture()
    assert params.nawi[1974] == capture["nawi_before_1975"]["1974"]
    for year in (1975, 2008, 2030):
        assert params.nawi[year] == tr2008.awi(year)
    assert params.pe_us_revision.startswith("committed_capture:")
