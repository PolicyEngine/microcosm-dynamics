"""Scenario paths against the committed realized COLA extraction.

Reads only ``data/external/ssa_cola_history.json`` (realized SSA
determination-year COLAs, 1979-2022).  The projected rates below are
INVENTED.  No test computes the exercise-1 age-group statistic.
"""

from __future__ import annotations

import struct
from pathlib import Path

from populace_dynamics import scenario_benefits as sb
from populace_dynamics.estimates import ledgers
from populace_dynamics.estimates.parameters import load_cola_history

COLA_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "external"
    / "ssa_cola_history.json"
)
_INVENTED_PROJECTION = {year: 0.02 for year in range(2023, 2031)}


def _bits(values: dict[int, float]) -> list[tuple[int, bytes]]:
    return [(year, struct.pack("<d", value)) for year, value in values.items()]


def test_default_path_is_the_sealed_path_on_the_committed_history():
    cola = load_cola_history(COLA_PATH)
    for eligibility_year in range(1979, 2024):
        for pia in (0.0, 1.05, 437.3, 1_234.56, 2_609.87, 4_018.99):
            for factor in (0.7, 0.75, 0.8, 14 / 15, 1.0, 1.08, 1.32):
                sealed = ledgers._monthly_benefit_path(
                    eligibility_pia=pia,
                    claim_age_factor=factor,
                    eligibility_year=eligibility_year,
                    cola=cola,
                )
                general = sb.monthly_benefit_path(
                    eligibility_pia=pia,
                    claim_age_factor=factor,
                    eligibility_year=eligibility_year,
                    cola=cola,
                )
                assert _bits(general) == _bits(sealed)


def test_invented_extension_leaves_the_realized_years_unchanged():
    realized = load_cola_history(COLA_PATH)
    extended = sb.extend_cola_series(
        realized,
        _INVENTED_PROJECTION,
        projection_label="INVENTED flat 2 percent",
    )
    assert extended.provenance["realized_through_determination_year"] == 2022
    assert extended.provenance["superseded_realized_determination_years"] == []
    assert (
        extended.provenance["realized"]["content_sha256"]
        == realized.provenance["content_sha256"]
    )
    for eligibility_year in (1985, 2000, 2012, 2020):
        clock = sb.WorkerClock.at_age_62(
            eligibility_year - 62, entitlement_year=eligibility_year
        )
        baseline = sb.worker_benefit_path(
            eligibility_pia=1_500.0,
            claim_age_factor=0.8,
            clock=clock,
            rates=sb.scenario_rates(extended, None, clock=clock),
        )
        sealed = ledgers._monthly_benefit_path(
            eligibility_pia=1_500.0,
            claim_age_factor=0.8,
            eligibility_year=eligibility_year,
            cola=realized,
        )
        assert list(baseline)[-1] == 2030
        assert _bits({year: baseline[year] for year in sealed}) == _bits(
            sealed
        )
