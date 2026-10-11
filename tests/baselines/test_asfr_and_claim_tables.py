"""The derived TR2026 fertility shape and the 2026 claim-age PMFs.

Artifact tier: reads committed inputs under ``data/external`` only
through their pinned accessors (``nchs_asfr_2024.json``,
``ssa_claim_ages_2026supplement.json``, the TR2026 and CBO2026 JSON).
No projection runs and no outcome is computed.

Invariants:

* the NCHS single-age shape is non-negative, keeps every NCHS band's
  total (ages 10-13 folded into 14) and sums to the NCHS TFR;
* a derived TR2026 ASFR sums to the V.A1 TFR and is proportional to the
  shape in every year;
* the 2026 claim-age PMFs equal ``claiming.claim_age_pmf`` exactly in
  every row both can read (1998-2022, a differential test), sum to one
  and cover 1998-2025.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics import claiming
from populace_dynamics.baselines import TR2026Intermediate, asfr
from populace_dynamics.baselines import claim_tables as tables
from populace_dynamics.data import cbo2026, tr2026

ROOT = Path(__file__).resolve().parents[2]
DATA_EXTERNAL = ROOT / "data" / "external"


def test_the_pinned_files_are_the_committed_ones():
    for path, pinned in (
        (asfr.NCHS_ASFR_PATH, asfr.NCHS_ASFR_SHA256),
        (tables.CLAIM_AGES_2026_PATH, tables.CLAIM_AGES_2026_SHA256),
    ):
        assert path.parent == DATA_EXTERNAL
        assert hashlib.sha256(path.read_bytes()).hexdigest() == pinned


def test_nchs_shape_keeps_every_band_total_and_the_tfr():
    shape = asfr.nchs_single_age_shape()
    assert tuple(shape) == asfr.FERTILE_AGES
    values = np.array(list(shape.values()))
    assert np.all(values >= 0.0)
    table = json.loads(asfr.NCHS_ASFR_PATH.read_text())["tables"]["2024"]
    for label, lower, upper in asfr.NCHS_BANDS:
        expected = (upper - lower) * table[label] / 1000.0
        ages = range(max(lower, 14), upper)
        observed = sum(shape[age] for age in ages)
        assert observed == pytest.approx(expected, rel=1e-12, abs=1e-15)
    assert values.sum() == pytest.approx(asfr.nchs_published_tfr(), 1e-12)
    # The NCHS 2024 schedule peaks in the 30-34 band (file validation).
    assert max(shape, key=shape.get) in range(28, 35)


def test_nchs_shape_is_read_only():
    with pytest.raises(TypeError):
        asfr.nchs_single_age_shape()[30] = 1.0


@settings(max_examples=40, deadline=None)
@given(year=st.integers(1940, 2100))
def test_tr2026_asfr_is_the_shape_scaled_to_the_v_a1_tfr(year):
    rates = TR2026Intermediate().asfr(year)
    shape = asfr.nchs_single_age_shape()
    assert tuple(rates) == asfr.FERTILE_AGES
    assert sum(rates.values()) == pytest.approx(tr2026.tfr(year), 1e-12)
    ratio = {age: rates[age] / shape[age] for age in shape if shape[age]}
    assert max(ratio.values()) == pytest.approx(min(ratio.values()), 1e-12)


@settings(max_examples=30, deadline=None)
@given(year=st.integers(2021, 2099))
def test_cbo_shape_alternative_scales_cbo_ages_to_the_tr2026_tfr(year):
    rates = TR2026Intermediate(asfr_shape="cbo2026").asfr(year)
    published = cbo2026.asfr(year)
    assert sum(rates.values()) == pytest.approx(tr2026.tfr(year), 1e-12)
    factor = tr2026.tfr(year) / sum(published.values())
    for age, value in published.items():
        assert rates[age] == pytest.approx(value * factor, rel=1e-12)


def test_cbo_shape_alternative_refuses_years_cbo_does_not_cover():
    baseline = TR2026Intermediate(asfr_shape="cbo2026")
    with pytest.raises(ValueError, match="outside coverage"):
        baseline.asfr(2100)
    with pytest.raises(ValueError, match="asfr_shape"):
        TR2026Intermediate(asfr_shape="flat")


def test_scale_shape_refuses_degenerate_inputs():
    with pytest.raises(ValueError, match="all-zero"):
        asfr.scale_shape_to_tfr({20: 0.0}, 1.5)
    with pytest.raises(ValueError, match="TFR"):
        asfr.scale_shape_to_tfr({20: 0.1}, float("nan"))
    with pytest.raises(ValueError, match="non-negative"):
        asfr.scale_shape_to_tfr({20: -0.1, 21: 0.2}, 1.5)


# ---------------------------------------------------------------------------
# Claim-age PMFs from the 2026 Supplement
# ---------------------------------------------------------------------------
def test_2026_claim_pmf_equals_the_claiming_module_where_both_read():
    reference = claiming.load_claim_age_reference(tables.CLAIM_AGES_2026_PATH)
    ours = tables.claim_pmf_2026_supplement()
    compared = 0
    for (sex, year), pmf in ours.items():
        if claiming.MIN_YEAR <= year <= claiming.MAX_YEAR:
            theirs = claiming.claim_age_pmf(
                sex, year, exclude_conversions=True, reference=reference
            )
            assert pmf == theirs, (sex, year)
            compared += 1
    assert compared == 2 * (claiming.MAX_YEAR - claiming.MIN_YEAR + 1)


def test_the_claiming_module_snaps_rows_after_2022_which_ours_reads():
    reference = claiming.load_claim_age_reference(tables.CLAIM_AGES_2026_PATH)
    snapped = claiming.claim_age_distribution(
        "male", 2025, reference=reference
    )
    assert snapped.nearest_year_used and snapped.entitlement_year == 2022
    ours = tables.claim_pmf_2026_supplement()[("male", 2025)]
    direct = tables.claim_row_pmf(reference.row("male", 2025)["categories"])
    assert ours == direct


def test_2026_claim_pmfs_cover_1998_2025_and_sum_to_one():
    pmfs = tables.claim_pmf_2026_supplement()
    assert {year for _, year in pmfs} == set(range(1998, 2026))
    assert {sex for sex, _ in pmfs} == {"female", "male"}
    assert tables.last_year_2026_supplement() == 2025
    for pmf in pmfs.values():
        assert set(pmf) == set(range(62, 71))
        assert all(value >= 0.0 for value in pmf.values())
        assert sum(pmf.values()) == pytest.approx(1.0, abs=1e-12)


def test_claim_row_pmf_refuses_degenerate_rows():
    zero = dict.fromkeys(
        ("age62", "age63", "age64", "age65", "age66", "age67_69"), 0.0
    )
    with pytest.raises(ValueError, match="degenerate"):
        tables.claim_row_pmf({**zero, "age70plus": 0.0})
    with pytest.raises(ValueError, match="non-negative"):
        tables.claim_row_pmf({**zero, "age62": -1.0, "age70plus": 2.0})
