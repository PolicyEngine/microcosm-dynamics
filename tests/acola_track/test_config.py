"""Registration 18 row definitions, composition and specification binding."""

from dataclasses import fields, replace
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.acola_track.config import (
    DEFERRED_ROWS,
    LABELS,
    REGISTERED_ROWS,
    ROOT,
    RUNNABLE_ROWS,
    SPECIFICATION_PATH,
    SPECIFICATION_SHA256,
    ACOLAConfig,
    check_specification,
)
from populace_dynamics.cola_track_a.config import (
    REGISTERED_ROWS as LEGACY_ROWS,
)
from populace_dynamics.cola_track_a.config import (
    TrackAConfig,
    rulings_departures,
)
from populace_dynamics.scenario_benefits import BenefitPeriod, ExposureClock
from populace_dynamics.ss.statutory_aime import ComputationYears


def test_all_registered_rows_have_the_registered_fields():
    assert list(REGISTERED_ROWS) == [
        "C0",
        "C1",
        "C0-D",
        "M0",
        "M1",
        "M2",
        "M3",
        "M4",
    ]
    assert ACOLAConfig().rows == RUNNABLE_ROWS
    assert len(RUNNABLE_ROWS) == 7
    for row in REGISTERED_ROWS.values():
        assert row.anchor_wave == 2011
        assert row.track_row().first_reduced_determination_year == (
            row.first_reduced_determination_year
        )
        assert row.track_row().exposure_clock is row.exposure_clock
        assert row.track_row().benefit_period is row.benefit_period
        assert row.as_dict()["benefit_scale"] == "annual_12_times_monthly"
    assert REGISTERED_ROWS["C0"].first_reduced_determination_year == 2027
    assert REGISTERED_ROWS["M0"].first_reduced_determination_year == 2011
    assert REGISTERED_ROWS["M1"].first_reduced_determination_year == 2010
    assert REGISTERED_ROWS["M3"].exposure_clock is ExposureClock.ENTITLEMENT
    assert REGISTERED_ROWS["M4"].age_rule.endswith("_minus_one")


@pytest.mark.parametrize(
    "alternative,primary,changed",
    [
        ("C1", "C0", "benefit_period"),
        ("C0-D", "C0", "mechanism"),
        ("M1", "M0", "first_reduced_determination_year"),
        ("M2", "M0", "benefit_period"),
        ("M3", "M0", "exposure_clock"),
        ("M4", "M0", "age_rule"),
    ],
)
def test_each_alternative_changes_exactly_one_registered_field(
    alternative, primary, changed
):
    a, p = REGISTERED_ROWS[alternative], REGISTERED_ROWS[primary]
    differences = [
        f.name
        for f in fields(a)
        if f.name not in {"row_id", "field_changed"}
        and getattr(a, f.name) != getattr(p, f.name)
    ]
    assert differences == [changed]


def test_deferred_D_has_a_full_spec_and_cannot_run():
    assert DEFERRED_ROWS["C0-D"]["status"] == "deferred"
    assert "further issue #42 comment" in DEFERRED_ROWS["C0-D"]["reason"]
    assert REGISTERED_ROWS["C0-D"].di_computation == (
        ComputationYears.STATUTORY.value
    )
    assert REGISTERED_ROWS["C0"].di_computation == (
        ComputationYears.LEGACY_FIXED_35.value
    )
    with pytest.raises(ValueError, match="deferred"):
        ACOLAConfig(rows=("C0-D",))


def test_projection_composes_R0_without_extending_its_registry():
    config = ACOLAConfig()
    track = config.track_a_config()
    assert track == TrackAConfig(rows=("R0",))
    assert track.anchor_waves == (2011,)
    assert config.start_years == {2011: 2010}
    assert config.rows_for_wave(2009) == ()
    assert list(LEGACY_ROWS) == ["R0", "R1", "R2", "R3", "R4", "R5", "R6"]
    assert rulings_departures(track) == []
    config.check_runnable()
    config.check_registered()
    assert LABELS[-1] == "report-only"


@given(st.lists(st.integers(0, 100), min_size=1, max_size=20, unique=True))
@settings(deadline=None)
def test_unique_draws_sort_without_changing_the_seed_indices(draws):
    config = ACOLAConfig(draw_indices=tuple(draws))
    assert config.draw_indices == tuple(sorted(draws))
    assert config.track_a_config().draw_indices == config.draw_indices


@pytest.mark.parametrize(
    "kwargs,message",
    [
        ({"rows": ()}, "non-empty"),
        ({"rows": ("C0", "C0")}, "unique"),
        ({"rows": ("unknown",)}, "unknown"),
        ({"draw_indices": ()}, "draw_indices"),
        ({"draw_indices": (0, 0)}, "draw_indices"),
        ({"draw_indices": (-1,)}, "draw_indices"),
        ({"draw_indices": (0.5,)}, "draw_indices"),
        ({"floor_seeds": (1, 1)}, "floor_seeds"),
        ({"reference_year": 2031}, "2030 only"),
        ({"annual_reduction": -0.01}, "non-negative"),
        ({"annual_reduction": float("nan")}, "finite"),
        ({"opening_stock_basis": "rolling"}, "not implemented"),
    ],
)
def test_invalid_config_refuses(kwargs, message):
    with pytest.raises(ValueError, match=message):
        ACOLAConfig(**kwargs)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"rows": ("C0",)},
        {"draw_indices": (0, 1)},
        {"floor_seeds": (0, 1)},
        {"annual_reduction": 0},
        {"claim_table_max_year": 2007},
        {"opening_stock_dime_floor": True},
        {"auxiliary_entitlement_clock": "worker"},
        {"di_benefit_level": "exclude"},
    ],
)
def test_invented_sensitivities_cannot_change_the_registered_run(kwargs):
    config = ACOLAConfig(**kwargs)
    config.check_runnable()
    with pytest.raises(ValueError, match="settings differ"):
        config.check_registered()


def test_an_acceptance_rule_is_refused():
    config = ACOLAConfig(acceptance_rule="any band")
    with pytest.raises(ValueError, match="no acceptance rule"):
        config.check_runnable()


def test_specification_hash_is_the_verbatim_posted_body_pin():
    assert check_specification()["sha256"] == SPECIFICATION_SHA256
    with TemporaryDirectory(dir=ROOT, prefix=".acola-spec-test-") as directory:
        changed = Path(directory) / "registration.md"
        changed.write_bytes(SPECIFICATION_PATH.read_bytes() + b"changed\n")
        with pytest.raises(ValueError, match="SHA-256"):
            check_specification(changed)


def test_december_rows_do_not_change_the_registration_reference_year():
    assert REGISTERED_ROWS["C1"].benefit_period is BenefitPeriod.DECEMBER
    assert REGISTERED_ROWS["M2"].benefit_period is BenefitPeriod.DECEMBER
    config = replace(ACOLAConfig(), annual_reduction=0)
    assert config.track_a_config().annual_reduction == 0
    assert config.reference_year == 2030
