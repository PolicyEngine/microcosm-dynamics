"""Tests for the entrant schedule builder and its seam contract.

The final test runs a real :class:`ProjectionEngine` over a built schedule.
That is the point of the piece: the seam already exists and is tested, so a
schedule builder is only correct if the loop accepts what it produces.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from populace_dynamics.engine import entrant_schedule as esm
from populace_dynamics.engine.entrant_domains import (
    EntrantClaimingAdapter,
    suppress_entrant_benefit_outputs,
)
from populace_dynamics.engine.loop import (
    SCHEDULED_ENTRIES_KEY,
    MaritalStepResult,
    PeriodModules,
    ProjectionEngine,
    SyntheticPersonIdAllocator,
)
from populace_dynamics.engine.steps import advance_age


def _donor(n: int = 40, seed: int = 2) -> pd.DataFrame:
    """An explicit donor pool.

    The schedule builder's contract is the donor COLUMNS, not the frame it
    came from, so the fixture is built directly rather than sampled out of a
    synthetic frame -- that keeps these tests independent of how thinly a
    random frame happens to populate the recent-arrival band.
    The native frame-reader path remains outside this source-only slice.
    """
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {
            "person_id": np.arange(n),
            "weight": rng.uniform(500.0, 5000.0, size=n),
            "entry_age": rng.integers(0, 80, size=n).astype(np.int64),
            "is_female": rng.random(n) < 0.5,
            "source_year": np.full(n, 2024, dtype=np.int64),
            "peinusyr": np.full(n, 28, dtype=np.int64),
            "prcitshp": rng.choice([4, 5], size=n).astype(np.int64),
            "penatvty": rng.integers(100, 556, size=n).astype(np.int64),
            "foreign_born": np.ones(n, dtype=bool),
        }
    )


def _schedule(years=(2026, 2027), start_id: int = 90_000_000, **kwargs):
    donor = _donor()
    inflow = {year: 1000.0 + 10 * index for index, year in enumerate(years)}
    allocator = SyntheticPersonIdAllocator(start_id)
    return (
        esm.build_entrant_schedule(
            donor, inflow, allocator=allocator, **kwargs
        ),
        donor,
        allocator,
    )


# --------------------------------------------------------------------------
# The seam contract, which loop.py enforces
# --------------------------------------------------------------------------
def test_frames_carry_the_year_before_activation():
    schedule, _, _ = _schedule(years=(2026, 2027))
    for year, frame in schedule.frames.items():
        assert set(frame["year"].unique()) == {year - 1}


def test_person_ids_are_unique_across_every_activation_year():
    schedule, _, _ = _schedule(years=(2026, 2027, 2028))
    pooled = pd.concat(schedule.frames.values(), ignore_index=True)
    assert not pooled["person_id"].duplicated().any()


def test_ids_come_from_the_allocator_and_advance_it():
    schedule, donor, allocator = _schedule(years=(2026, 2027))
    assert allocator.next_id == 90_000_000 + 2 * len(donor)
    pooled = pd.concat(schedule.frames.values(), ignore_index=True)
    assert pooled["person_id"].min() >= 90_000_000


def test_the_allocator_still_guards_the_reserved_real_namespace():
    donor = _donor()
    allocator = SyntheticPersonIdAllocator(
        10, reserved_real_ids=frozenset({12})
    )
    with pytest.raises(RuntimeError, match="overlap the reserved real-person"):
        esm.build_entrant_schedule(donor, {2026: 1000.0}, allocator=allocator)


def test_rows_are_person_sorted():
    schedule, _, _ = _schedule()
    for frame in schedule.frames.values():
        assert frame["person_id"].is_monotonic_increasing


def test_birth_year_is_consistent_with_the_frame_coordinate():
    schedule, _, _ = _schedule(years=(2026,))
    frame = schedule.frames[2026]
    assert (
        frame["birth_year"].to_numpy()
        == frame["year"].to_numpy() - frame["age"].to_numpy()
    ).all()


def test_sex_uses_the_roster_string_encoding():
    schedule, _, _ = _schedule()
    for frame in schedule.frames.values():
        assert set(frame["sex"].unique()) <= {"female", "male"}


# --------------------------------------------------------------------------
# Sizing
# --------------------------------------------------------------------------
def test_cohort_weight_equals_the_control_in_persons():
    schedule, _, _ = _schedule(years=(2026,))
    record = schedule.alignment[2026]
    assert record["target_weighted_persons"] == 1000.0 * 1000.0
    assert record["scheduled_weighted_persons"] == pytest.approx(
        1_000_000.0, rel=1e-12
    )
    assert abs(record["relative_residual"]) < 1e-12


def test_reweighting_preserves_the_donor_composition_exactly():
    schedule, donor, _ = _schedule(years=(2026,))
    frame = schedule.frames[2026]
    donor_share = donor["weight"].to_numpy() / donor["weight"].sum()
    merged = frame.sort_values("donor_person_id")
    scheduled_share = merged["weight"].to_numpy() / merged["weight"].sum()
    expected = (
        donor.sort_values("person_id")["weight"].to_numpy()
        / donor["weight"].sum()
    )
    assert np.allclose(np.sort(donor_share), np.sort(scheduled_share))
    assert np.allclose(scheduled_share, expected)


def test_no_rng_is_consumed():
    """Two builds from independent allocators agree row for row."""
    donor = _donor()
    first = esm.build_entrant_schedule(
        donor, {2026: 1340.0}, allocator=SyntheticPersonIdAllocator(1_000)
    )
    second = esm.build_entrant_schedule(
        donor, {2026: 1340.0}, allocator=SyntheticPersonIdAllocator(1_000)
    )
    pd.testing.assert_frame_equal(first.frames[2026], second.frames[2026])


def test_negative_or_nonfinite_control_is_rejected():
    donor = _donor()
    with pytest.raises(ValueError, match="negative control inflow"):
        esm.build_entrant_schedule(
            donor, {2026: -1.0}, allocator=SyntheticPersonIdAllocator(10)
        )


def test_empty_donor_is_rejected():
    donor = _donor().iloc[0:0]
    with pytest.raises(ValueError, match="donor pool is empty"):
        esm.build_entrant_schedule(
            donor, {2026: 1.0}, allocator=SyntheticPersonIdAllocator(10)
        )


def test_no_activation_years_is_rejected():
    with pytest.raises(ValueError, match="no activation years"):
        esm.build_entrant_schedule(
            _donor(), {}, allocator=SyntheticPersonIdAllocator(10)
        )


# --------------------------------------------------------------------------
# Provenance counters
# --------------------------------------------------------------------------
def test_counters_read_the_entry_kind_column_not_id_arithmetic():
    schedule, donor, _ = _schedule(years=(2026, 2027))
    counters = esm.entrant_provenance_counters(schedule.frames)
    assert counters["immigrant_cohorts"] == 2 * len(donor)
    assert counters["n_rows_by_entry_kind"] == {
        esm.ENTRY_KIND_IMMIGRANT: 2 * len(donor)
    }
    assert "not ID arithmetic" in counters["counter_basis"]


def test_counters_reject_a_frame_without_the_provenance_column():
    schedule, _, _ = _schedule(years=(2026,))
    frame = schedule.frames[2026].drop(columns=[esm.ENTRY_KIND_COLUMN])
    with pytest.raises(ValueError, match="entrant provenance cannot be"):
        esm.entrant_provenance_counters({2026: frame})


def test_provenance_states_the_sizing_basis_and_exclusions():
    schedule, _, _ = _schedule()
    provenance = schedule.provenance
    assert provenance["sizing_basis"] == "trustees_va2_gross_positive_inflow"
    assert provenance["report_only"] is True
    assert provenance["gated"] is False
    joined = " ".join(provenance["sizing_excludes"])
    assert "emigration" in joined and "reclassification" in joined


def test_provenance_refuses_to_call_the_control_an_arrival_count():
    """The control is a stock-accounting proxy, and must say so.

    V.A2's temporary-or-unlawfully-present inflow counts only those who
    remain to year-end, so the gross total is not a count of physical
    arrivals.  Naming the basis without that qualification would invite the
    cohort to be read as arrivals, which is the same class of error as
    reading an ssa_area_proxy as resident-aligned.
    """
    schedule, _, _ = _schedule()
    disclosure = schedule.provenance["sizing_basis_disclosure"]
    assert "NOT a count of physical" in disclosure
    assert "remain to year-end" in disclosure


# --------------------------------------------------------------------------
# The loop actually accepts it
# --------------------------------------------------------------------------
def test_a_built_schedule_activates_through_the_real_projection_engine():
    donor = _donor(n=200, seed=4)
    allocator = SyntheticPersonIdAllocator(90_000_000)
    schedule = esm.build_entrant_schedule(
        donor, {2026: 1340.0, 2027: 1350.0}, allocator=allocator
    )

    def mortality(frame, context, rng):
        del context, rng
        return frame.sort_values("person_id").reset_index(drop=True)

    def marital(frame, context, rng):
        del frame, context, rng
        return MaritalStepResult(pd.DataFrame(), pd.DataFrame())

    def passthrough(frame, context, rng):
        del context, rng
        return frame.copy()

    modules = PeriodModules(
        mortality=mortality,
        aging=advance_age,
        marital_core=marital,
        fertility=lambda frame, context, result, rng: frame.copy(),
        disability=passthrough,
        earnings=passthrough,
        claiming=passthrough,
        household_composition=(
            lambda frame, context, result, rng: frame.copy()
        ),
    )
    initial = pd.DataFrame(
        {
            "person_id": [1, 2],
            "year": [2025, 2025],
            "age": [40, 41],
            "sex": ["female", "male"],
            "weight": [1.0, 1.0],
        }
    )
    result = ProjectionEngine(modules).project(
        initial,
        end_year=2027,
        draw_index=0,
        metadata={SCHEDULED_ENTRIES_KEY: schedule.as_metadata()},
    )

    # 2 incumbents, then + one cohort in 2026, then + another in 2027.
    assert [len(frame) for frame in result.slices] == [
        2,
        2 + len(donor),
        2 + 2 * len(donor),
    ]
    final = result.slices[-1]
    assert set(final["year"].unique()) == {2027}
    assert not final["person_id"].duplicated().any()
    entrants = final[final[esm.ENTRY_KIND_COLUMN].notna()]
    assert len(entrants) == 2 * len(donor)


def test_the_entrant_faces_mortality_at_its_entry_age_before_aging():
    """The seam's fixed convention, pinned rather than assumed.

    A row scheduled with ``age = entry_age`` at ``year = y - 1`` is seen by
    the mortality step at ``entry_age``; only then does aging advance it.
    """
    donor = _donor(n=120, seed=6)
    schedule = esm.build_entrant_schedule(
        donor, {2026: 1000.0}, allocator=SyntheticPersonIdAllocator(90_000_000)
    )
    seen: list[np.ndarray] = []

    def mortality(frame, context, rng):
        del context, rng
        ordered = frame.sort_values("person_id").reset_index(drop=True)
        seen.append(ordered["age"].to_numpy(dtype=np.int64).copy())
        return ordered

    def marital(frame, context, rng):
        del frame, context, rng
        return MaritalStepResult(pd.DataFrame(), pd.DataFrame())

    def passthrough(frame, context, rng):
        del context, rng
        return frame.copy()

    modules = PeriodModules(
        mortality=mortality,
        aging=advance_age,
        marital_core=marital,
        fertility=lambda frame, context, result, rng: frame.copy(),
        disability=passthrough,
        earnings=passthrough,
        claiming=passthrough,
        household_composition=(
            lambda frame, context, result, rng: frame.copy()
        ),
    )
    initial = pd.DataFrame(
        {
            "person_id": [1],
            "year": [2025],
            "age": [30],
            "sex": ["female"],
            "weight": [1.0],
        }
    )
    result = ProjectionEngine(modules).project(
        initial,
        end_year=2026,
        draw_index=0,
        metadata={SCHEDULED_ENTRIES_KEY: schedule.as_metadata()},
    )
    scheduled_ages = np.sort(
        schedule.frames[2026]["age"].to_numpy(dtype=np.int64)
    )
    # The mortality step saw the entry ages themselves, alongside the one
    # incumbent (age 30).  Compare the full multiset so an entrant aged 0 is
    # not silently confused with the incumbent by position.
    expected_seen = np.sort(np.concatenate([scheduled_ages, [30]]))
    assert np.array_equal(np.sort(seen[0]), expected_seen)
    # ...and the activation-year slice carries entry_age + 1.
    final = result.slices[-1]
    entrant_ages = np.sort(
        final.loc[final[esm.ENTRY_KIND_COLUMN].notna(), "age"].to_numpy(
            dtype=np.int64
        )
    )
    assert np.array_equal(entrant_ages, scheduled_ages + 1)


def test_zero_inflow_has_an_alignment_record_without_rows_or_ids():
    allocator = SyntheticPersonIdAllocator(90_000_000)
    schedule = esm.build_entrant_schedule(
        _donor(), {2026: 0.0, 2027: 0.0}, allocator=allocator
    )
    assert schedule.frames == schedule.as_metadata() == {}
    assert schedule.total_rows() == schedule.total_weight() == 0
    assert allocator.next_id == 90_000_000
    assert set(schedule.alignment) == {2026, 2027}
    assert all(record["n_rows"] == 0 for record in schedule.alignment.values())
    assert schedule.provenance["zero_inflow_years"] == [2026, 2027]
    assert schedule.provenance["scheduled_activation_years"] == []


def test_zero_years_and_donors_do_not_change_later_cohort_ids():
    donor = _donor()
    donor.loc[0, "weight"] = 0.0
    first = esm.build_entrant_schedule(
        donor,
        {2026: 0.0, 2027: 1000.0},
        allocator=SyntheticPersonIdAllocator(90_000_000),
    )
    direct = esm.build_entrant_schedule(
        donor.iloc[1:],
        {2027: 1000.0},
        allocator=SyntheticPersonIdAllocator(90_000_000),
    )
    assert set(first.frames) == {2027}
    pd.testing.assert_frame_equal(first.frames[2027], direct.frames[2027])
    assert first.total_rows() == len(donor) - 1
    assert (first.frames[2027]["weight"] > 0).all()


@pytest.mark.parametrize("control", [-1.0, np.nan, np.inf, 1e308])
def test_all_controls_are_checked_before_allocating_any_ids(control):
    allocator = SyntheticPersonIdAllocator(1000)
    with pytest.raises(ValueError, match="control inflow"):
        esm.build_entrant_schedule(
            _donor(), {2026: 1.0, 2027: control}, allocator=allocator
        )
    assert allocator.next_id == 1000


@pytest.mark.parametrize("year", [2026.5, "2026", True])
def test_activation_years_are_not_silently_coerced(year):
    allocator = SyntheticPersonIdAllocator(1000)
    with pytest.raises(ValueError, match="activation years must be integers"):
        esm.build_entrant_schedule(_donor(), {year: 1.0}, allocator=allocator)
    assert allocator.next_id == 1000


@pytest.mark.parametrize("age", [-1, 10.5, np.nan, np.inf])
def test_invalid_donor_ages_do_not_become_integer_demographic_states(age):
    donor = _donor().astype({"entry_age": "float64"})
    donor.loc[0, "entry_age"] = age
    with pytest.raises(ValueError, match="entry_age must be nonnegative"):
        esm.build_entrant_schedule(
            donor, {2026: 1.0}, allocator=SyntheticPersonIdAllocator(1000)
        )


@pytest.mark.parametrize("column", ["is_female", "foreign_born"])
@pytest.mark.parametrize("value", ["False", pd.NA, 2])
def test_donor_flags_are_not_truthiness_coerced(column, value):
    donor = _donor().astype({column: "object"})
    donor.loc[0, column] = value
    with pytest.raises(ValueError, match=f"{column} must contain booleans"):
        esm.build_entrant_schedule(
            donor, {2026: 1.0}, allocator=SyntheticPersonIdAllocator(1000)
        )


def test_a_mislabeled_immigrant_schedule_is_rejected():
    with pytest.raises(ValueError, match="require immigrant_cohort kind"):
        esm.build_entrant_schedule(
            _donor(),
            {2026: 1.0},
            allocator=SyntheticPersonIdAllocator(1000),
            entry_kind=esm.ENTRY_KIND_BIRTH,
        )


@pytest.mark.parametrize("kind", [None, "immgrant_cohort"])
def test_provenance_counts_reject_missing_or_unknown_kinds(kind):
    schedule, _, _ = _schedule(years=(2026,))
    schedule.frames[2026].loc[0, esm.ENTRY_KIND_COLUMN] = kind
    with pytest.raises(ValueError, match="missing or unknown entry_kind"):
        esm.entrant_provenance_counters(schedule.frames)


@pytest.mark.parametrize("weight,inflow", [(1e-300, 1e300), (1e300, 1e-300)])
def test_unrepresentable_scaling_fails_before_cohort_allocation(
    weight, inflow
):
    donor = _donor(n=1)
    donor["weight"] = weight
    allocator = SyntheticPersonIdAllocator(1000)
    with pytest.raises(ValueError, match="finite positive donor weights"):
        esm.build_entrant_schedule(donor, {2026: inflow}, allocator=allocator)
    assert allocator.next_id == 1000


def test_large_integer_donor_weights_use_the_validated_float_sum():
    donor = _donor(n=2)
    donor["weight"] = np.array([2**62, 2**62], dtype=np.int64)
    schedule = esm.build_entrant_schedule(
        donor, {2026: 1.0}, allocator=SyntheticPersonIdAllocator(1000)
    )
    assert schedule.frames[2026]["weight"].tolist() == [500.0, 500.0]
    assert schedule.alignment[2026]["residual_persons"] == 0.0


def test_positive_subnormal_scale_does_not_distort_the_control():
    donor = _donor(n=1)
    donor["weight"] = 2.0**1023
    allocator = SyntheticPersonIdAllocator(1000)
    schedule = esm.build_entrant_schedule(
        donor, {2026: 1.0, 2027: 2.0**-60}, allocator=allocator
    )
    assert schedule.frames[2026]["weight"].iloc[0] == 1000.0
    assert schedule.frames[2027]["weight"].iloc[0] == 1000.0 * 2.0**-60
    assert schedule.alignment[2027]["residual_persons"] == 0.0
    assert allocator.next_id == 1002


def test_later_cohorts_activate_after_extinction_with_unknown_benefits():
    """Real loop mechanics with synthetic survival and benefit placeholders.

    The placeholder values test output suppression only; no statutory benefit
    calculator or native fitted transition is exercised.
    """
    donor = _donor(n=3)
    allocator = SyntheticPersonIdAllocator(1000)
    schedule = esm.build_entrant_schedule(
        donor, {2026: 0.0, 2027: 1.0, 2028: 2.0}, allocator=allocator
    )
    seen = {}

    def mortality(frame, context, rng):
        seen[context.year] = frame.copy()
        if context.year == 2026:
            return frame.iloc[:0].copy()
        # A later cohort must activate even when the previous cohort dies.
        if context.year == 2028:
            return frame.loc[frame["entry_year"] == 2028].copy()
        return frame.copy()

    def forbidden_claiming(*args):
        raise AssertionError("unsupported entrants reached claiming behavior")

    def passthrough(frame, context, rng):
        return frame.copy()

    def marital(frame, context, rng):
        return MaritalStepResult(frame.copy(), pd.DataFrame())

    modules = PeriodModules(
        mortality=mortality,
        aging=advance_age,
        marital_core=marital,
        fertility=lambda f, c, m, r: f.copy(),
        disability=passthrough,
        earnings=lambda f, c, r: f.assign(aime=10.0, pia=20.0, benefit=30.0),
        claiming=EntrantClaimingAdapter(
            lambda f, c, r: f if f.empty else forbidden_claiming(f, c, r)
        ),
        household_composition=lambda f, c, m, r: suppress_entrant_benefit_outputs(
            f
        ),
    )
    initial = pd.DataFrame(
        {"person_id": [1], "year": [2025], "age": [30], "sex": ["female"]}
    )
    result = ProjectionEngine(modules).project(
        initial,
        end_year=2028,
        draw_index=0,
        metadata={SCHEDULED_ENTRIES_KEY: schedule.as_metadata()},
    )
    assert [len(frame) for frame in result.slices] == [1, 0, 3, 3]
    assert allocator.next_id == 1006
    for year in (2027, 2028):
        observed = seen[year].loc[seen[year]["entry_year"] == year]
        assert observed["age"].tolist() == donor["entry_age"].tolist()
        frame = result.slices[year - 2025]
        assert (frame["age"] == frame["entry_age"] + 1).all()
        assert frame[["aime", "pia", "benefit"]].isna().all().all()
        assert frame["claim_age"].isna().all()
        assert not frame["claimed"].any()
        assert frame["weight"].sum() == pytest.approx((year - 2026) * 1000.0)
    assert set(result.slices[-1]["person_id"]) == {1003, 1004, 1005}
