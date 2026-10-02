"""Pure-array registration arithmetic uses invented values only."""

from decimal import Decimal, localcontext

import numpy as np
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from populace_dynamics.bridge import depletion_cut as previous
from populace_dynamics.bridge import depletion_cut_population as core


@settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    st.lists(st.integers(0, 10**8), min_size=1, max_size=30),
    st.sampled_from(
        ["0", "1", "0.78", "0.83", "0.12345678901234567890123456789"]
    ),
)
def test_payable_matches_scalar_exactly(monthly, share):
    amount = np.asarray(monthly, dtype=np.int64)
    with localcontext() as context:
        context.prec = 3
        expected = [
            previous.payable_monthly_benefit(int(x), Decimal(share))
            for x in amount
        ]
        actual = core.payable_monthly_array(amount, Decimal(share))
    np.testing.assert_array_equal(actual, expected)
    assert actual.dtype == np.int64


@settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    st.lists(
        st.floats(min_value=0, max_value=1e9, width=32),
        min_size=1,
        max_size=30,
    )
)
def test_monthly_exact_float32_floor(annual):
    values = np.asarray(annual, dtype=np.float32).astype(np.float64)
    monthly = core.monthly_whole_dollars(values)
    assert monthly.dtype == np.int64
    assert np.all(12 * monthly <= values)
    assert np.all(values < 12 * (monthly + 1))


def test_monthly_boundaries_correctly_keep_remainder():
    values = np.asarray(
        [
            0,
            12,
            np.nextafter(12.0, 0.0),
            np.nextafter(12.0, np.inf),
            12 * 743 + 5.5,
        ]
    )
    np.testing.assert_array_equal(
        core.monthly_whole_dollars(values), [0, 1, 0, 1, 743]
    )


@pytest.mark.parametrize("values", [[-1], [np.nan], [np.inf], [12 * 2**50]])
def test_monthly_rejects_invalid_inputs(values):
    with pytest.raises(ValueError):
        core.monthly_whole_dollars(np.asarray(values))


@pytest.mark.parametrize(
    "share", [Decimal("-0.1"), Decimal("1.1"), Decimal("NaN")]
)
def test_payable_rejects_invalid_share(share):
    with pytest.raises(ValueError):
        core.payable_monthly_array(np.asarray([743]), share)


def test_payable_large_integer_uses_exact_overflow_fallback():
    values = np.asarray([np.iinfo(np.int64).max], dtype=np.int64)
    share = Decimal("0.83")
    np.testing.assert_array_equal(
        core.payable_monthly_array(values, share),
        [previous.payable_monthly_benefit(int(values[0]), share)],
    )


@settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(st.lists(st.integers(0, 500_000), min_size=1, max_size=20))
def test_share_one_preserves_every_component(values):
    baseline = {
        name: np.asarray(values, dtype=np.float64) + 0.25
        for name in core.COMPONENTS
    }
    reform, cuts, person_cut = core.cut_components(
        baseline, "oasdi17", Decimal(1)
    )
    for name in core.COMPONENTS:
        np.testing.assert_array_equal(reform[name], baseline[name])
        assert not cuts[name].any()
    assert not person_cut.any()


@settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(st.lists(st.integers(0, 100_000), min_size=1, max_size=20))
def test_cut_bounds_and_oasi_component_scope(monthly):
    values = 12 * np.asarray(monthly, dtype=np.float64) + 3.75
    baseline = {name: values for name in core.COMPONENTS}
    oasi, cuts, person_cut = core.cut_components(
        baseline, "oasi22", Decimal("0.78")
    )
    oasdi, _, _ = core.cut_components(baseline, "oasdi17", Decimal("0.83"))
    disability = "social_security_disability"
    np.testing.assert_array_equal(oasi[disability], values)
    assert not cuts[disability].any()
    for name in core.SCENARIOS["oasi22"]["components"]:
        m = np.asarray(monthly)
        assert np.all(Decimal("0.22") * m.astype(object) <= cuts[name] // 12)
        assert np.all(
            cuts[name] // 12 < Decimal("0.22") * m.astype(object) + 1
        )
        assert np.all(oasi[name] <= oasdi[name])
        np.testing.assert_array_equal(
            oasi[name] - 12 * core.monthly_whole_dollars(oasi[name]),
            np.full(len(m), 3.75),
        )
    np.testing.assert_array_equal(person_cut, sum(cuts.values()))


def test_baseline_does_not_cut():
    components = {name: np.asarray([8916.0]) for name in core.COMPONENTS}
    reform, _, cut = core.cut_components(
        components, "baseline", Decimal("0.78")
    )
    assert not cut.any()
    for name in components:
        np.testing.assert_array_equal(reform[name], components[name])


@settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    st.lists(
        st.tuples(st.integers(1, 1000), st.integers(-100, 1100)),
        min_size=1,
        max_size=30,
    )
)
def test_labels_partition_and_full_iff(records):
    cut = np.asarray([12 * item[0] for item in records])
    response = np.asarray([12 * item[1] for item in records], dtype=float)
    units = np.arange(len(cut))
    labels = core.replacement_labels(cut, np.zeros(len(cut)), response, units)
    np.testing.assert_array_equal(labels == core.FULL, response >= cut - 1)
    np.testing.assert_array_equal(
        labels == core.PART, (response > 1) & (response < cut - 1)
    )
    np.testing.assert_array_equal(labels == core.NONE, response <= 1)
    assert np.all(
        sum(labels == code for code in (core.FULL, core.PART, core.NONE)) == 1
    )


def test_unit_calculation_includes_excluded_spouse_for_r5():
    labels = core.replacement_labels(
        np.asarray([120, 240]),
        np.asarray([0, 0]),
        np.asarray([120, 0]),
        np.asarray([0, 0]),
    )
    np.testing.assert_array_equal(labels, [core.PART, core.PART])
    result = core.statistics(
        labels,
        np.asarray([core.FULL, core.FULL]),
        np.ones(2),
        np.asarray([True, False]),
    )
    assert result["n"] == 1
    assert result["P_test"] == 1
    assert result["B_part"] == 1


def test_tolerance_label_boundaries_and_ssi_decrease():
    changes = np.asarray([119, 1, 1.0001, -20, 122])
    labels = core.replacement_labels(
        np.full(5, 120), np.zeros(5), changes, np.arange(5)
    )
    np.testing.assert_array_equal(
        labels, [core.FULL, core.NONE, core.PART, core.NONE, core.FULL]
    )


@pytest.mark.parametrize("invalid", [np.nan, np.inf])
@pytest.mark.parametrize("position", ["cut", "baseline", "scenario"])
def test_replacement_labels_refuse_nonfinite_instead_of_assigning_none(
    invalid, position
):
    values = {
        "cut": np.asarray([120.0]),
        "baseline": np.asarray([0.0]),
        "scenario": np.asarray([120.0]),
    }
    values[position][0] = invalid
    with pytest.raises(ValueError, match="finite"):
        core.replacement_labels(
            values["cut"],
            values["baseline"],
            values["scenario"],
            np.asarray([0]),
        )


def test_replacement_labels_refuse_overflow_in_unit_ssi_change():
    with pytest.raises(ValueError, match="unit totals must be finite"):
        core.replacement_labels(
            np.asarray([120, 120]),
            np.zeros(2),
            np.asarray([1e308, 1e308]),
            np.asarray([0, 0]),
        )


@settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    st.lists(
        st.tuples(
            st.integers(0, 5000), st.integers(0, 5000), st.integers(0, 5000)
        ),
        min_size=1,
        max_size=20,
    )
)
def test_resource_household_monotonicity_and_unit_indicators(records):
    # Each invented household contains a couple and one separate unit.
    resources = np.asarray(records, dtype=float).reshape(-1)
    households = np.repeat(np.arange(len(records)), 3)
    units = np.asarray(
        [[2 * i, 2 * i, 2 * i + 1] for i in range(len(records))]
    ).reshape(-1)
    sizes = np.bincount(units)
    spousal = core.resource_test_spousal(resources, units, sizes, 2000, 3000)
    pooled = core.resource_test_household(
        resources, units, households, sizes, 2000, 3000
    )
    assert np.all(pooled <= spousal)
    for unit in np.unique(units):
        assert len(np.unique(spousal[units == unit])) == 1
        assert len(np.unique(pooled[units == unit])) == 1


@settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    st.lists(
        st.tuples(st.integers(0, 6000), st.integers(0, 6000), st.booleans()),
        min_size=1,
        max_size=20,
    )
)
def test_encoded_test_equals_bruteforce(records):
    resources = np.asarray(
        [[a, b] for a, b, _ in records], dtype=float
    ).reshape(-1)
    units = np.repeat(np.arange(len(records)), 2)
    joint = np.repeat([j for _, _, j in records], 2)
    expected = []
    for resource, unit, flag in zip(resources, units, joint, strict=True):
        expected.append(
            resources[units == unit].sum() <= 3000
            if flag
            else resource <= 2000
        )
    np.testing.assert_array_equal(
        core.resource_test_encoded(resources, units, joint, 2000, 3000),
        expected,
    )


def test_resource_boundaries_equality_and_tolerance():
    resources = np.asarray([1999.99, 2000.0, 2000.005, 2000.1, 2999.999, 0])
    units = np.asarray([0, 1, 2, 3, 4, 4])
    joint = np.asarray([False, False, False, False, True, True])
    passed = core.resource_test_encoded(resources, units, joint, 2000, 3000)
    np.testing.assert_array_equal(
        passed, [True, True, False, False, True, True]
    )
    np.testing.assert_array_equal(
        core.resource_boundary_mask(resources, units, joint, 2000, 3000),
        [True, True, True, False, True, True],
    )


def test_cells_partition_and_marital_codes_use_frame_mapping():
    ages = np.asarray(
        [0, 17, 18, 61, 62, 64, 65, 69, 70, 74, 75, 79, 80, 84, 85, 100]
    )
    np.testing.assert_array_equal(
        core.age_band(ages), np.repeat(core.CELLS["age"], 2)
    )
    np.testing.assert_array_equal(
        core.marital_cell(np.arange(1, 8)),
        [
            "married",
            "married",
            "married",
            "widowed",
            "divorced",
            "separated",
            "never_married",
        ],
    )
    np.testing.assert_array_equal(
        core.sex_cell(np.asarray([True, False])), ["female", "male"]
    )
    np.testing.assert_array_equal(
        core.race_cell(
            np.asarray([1, 2, 4, 3, 1]), np.asarray([0, 0, 0, 0, 1])
        ),
        ["white", "black", "asian", "other", "hispanic"],
    )


def test_income_definition_explicitly_excludes_health():
    actual = core.income_per_person(
        np.asarray([1000]),
        np.asarray([300]),
        np.asarray([100]),
        np.asarray([2]),
    )
    np.testing.assert_array_equal(actual, [600])


@settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    st.lists(
        st.tuples(st.integers(-100, 100), st.integers(1, 100)),
        min_size=1,
        max_size=50,
    )
)
def test_quintiles_exact_weighted_definition_ties_and_monotonicity(records):
    income = np.asarray([value for value, _ in records], dtype=float)
    weights = np.asarray([weight for _, weight in records], dtype=float)
    points = core.quintile_cutpoints(
        income, weights, np.ones(len(income), dtype=bool)
    )
    total = weights.sum()
    for k, point in enumerate(points, 1):
        assert weights[income <= point].sum() >= k * total / 5
        assert weights[income < point].sum() < k * total / 5
    assigned = core.assign_quintile(income, points)
    ranks = np.asarray([int(value[1]) for value in assigned])
    assert (np.diff(ranks[np.argsort(income)]) >= 0).all()
    for value in np.unique(income):
        assert len(np.unique(assigned[income == value])) == 1


def test_quintiles_equal_weights_give_equal_fifths():
    values = np.arange(100)
    points = core.quintile_cutpoints(
        values, np.ones(100), np.ones(100, dtype=bool)
    )
    np.testing.assert_array_equal(points, [19, 39, 59, 79])
    cells = core.assign_quintile(values, points)
    assert all(
        (cells == name).sum() == 20 for name in core.CELLS["income_quintile"]
    )


def test_quintiles_use_only_baseline_beneficiaries():
    points = core.quintile_cutpoints(
        np.arange(10), np.ones(10), np.arange(10) % 2 == 0
    )
    np.testing.assert_array_equal(points, [0, 2, 4, 6])


def test_quintiles_refuse_no_beneficiary_weight():
    with pytest.raises(ValueError, match="positive total"):
        core.quintile_cutpoints(
            np.arange(3), np.zeros(3), np.ones(3, dtype=bool)
        )


def test_pe_deciles_map_to_registered_quintiles():
    np.testing.assert_array_equal(
        core.pe_decile_quintile(np.asarray([-1, *range(1, 11)])),
        [
            "negative",
            "q1",
            "q1",
            "q2",
            "q2",
            "q3",
            "q3",
            "q4",
            "q4",
            "q5",
            "q5",
        ],
    )


def test_reason_partition_exhaustive_and_unit_level():
    units = np.repeat(np.arange(4), 2)
    abd = np.asarray([0, 0, 1, 0, 1, 1, 0, 1], dtype=bool)
    qualified = np.asarray([1, 1, 0, 1, 0, 1, 1, 1], dtype=bool)
    no = np.asarray([core.NONE] * 6 + [core.FULL] * 2)
    reasons = core.reason_partition(abd, qualified, units, no)
    np.testing.assert_array_equal(
        reasons,
        ["not_abd"] * 2
        + ["immigration"] * 2
        + ["no_positive_modeled_ssi_response"] * 2
        + [""] * 2,
    )


def test_statistics_weighted_transitions_and_shares():
    no = np.asarray([core.FULL, core.FULL, core.PART, core.NONE])
    test = np.asarray([core.FULL, core.PART, core.NONE, core.NONE])
    weights = np.asarray([1, 2, 3, 4])
    result = core.statistics(test, no, weights, np.ones(4, dtype=bool))
    assert result["n"] == 4
    assert result["W"] == 10
    assert result["n_cond"] == 3
    assert result["W_cond"] == 6
    assert result["B"] == pytest.approx(0.3)
    assert result["B_part"] == pytest.approx(0.2)
    assert result["B_cond"] == pytest.approx(0.5)
    for variant in ("test", "no"):
        assert sum(
            result[f"{name}_{variant}"] for name in ("F", "P", "N")
        ) == pytest.approx(1, abs=1e-12)
    np.testing.assert_array_equal(
        result["transition_table"]["unweighted"],
        [[1, 1, 0], [0, 0, 1], [0, 0, 1]],
    )
    assert result["small_cell"]
    assert result["small_cell_cond"]


def test_small_cell_conditional_threshold_is_separate():
    no = np.asarray([core.FULL] * 49 + [core.NONE] * 2)
    result = core.statistics(no, no, np.ones(51), np.ones(51, dtype=bool))
    assert not result["small_cell"]
    assert result["small_cell_cond"]


def test_statistics_undefined_denominators_are_explicit():
    none = np.full(3, core.NONE)
    result = core.statistics(none, none, np.ones(3), np.ones(3, dtype=bool))
    assert result["R_no"] == 0
    assert result["B_cond"] is None
    assert result["undefined_reasons"]["B_cond"] == "R_no is zero"
    empty = core.statistics(none, none, np.ones(3), np.zeros(3, dtype=bool))
    assert all(empty[name] is None for name in core.HEADLINE["statistics"])


def _bootstrap_jobs():
    return {
        "all": {
            "labels_test": np.asarray(
                [core.FULL, core.PART, core.NONE, core.NONE]
            ),
            "labels_no": np.asarray(
                [core.FULL, core.FULL, core.PART, core.NONE]
            ),
            "weights": np.asarray([2, 2, 3, 5]),
            "beneficiary_mask": np.ones(4, dtype=bool),
        }
    }


def test_bootstrap_seed_person_order_and_manual_household_reference():
    household_ids = np.asarray([90, 90, 10, 40])
    jobs = _bootstrap_jobs()
    actual = core.bootstrap_intervals(jobs, household_ids)
    assert actual == core.bootstrap_intervals(jobs, household_ids)
    order = np.asarray([1, 0, 3, 2])
    reordered = {
        key: {name: value[order] for name, value in job.items()}
        for key, job in jobs.items()
    }
    assert actual == core.bootstrap_intervals(reordered, household_ids[order])
    rng = np.random.default_rng(20261001)
    ids, membership = np.unique(household_ids, return_inverse=True)
    reference = {name: [] for name in core.HEADLINE["statistics"]}
    for _ in range(500):
        idx = rng.integers(0, len(ids), size=len(ids))
        k = np.bincount(idx, minlength=len(ids))
        job = dict(jobs["all"])
        job["weights"] = job["weights"] * k[membership]
        result = core.statistics(**job)
        for name in reference:
            if result[name] is not None:
                reference[name].append(result[name])
    for name, valid in reference.items():
        interval = actual["all"][name]
        assert interval["valid_replicates"] == len(valid)
        assert interval["omitted_replicates"] == 500 - len(valid)
        np.testing.assert_allclose(
            interval["interval"],
            np.quantile(valid, [0.025, 0.975], method="linear"),
        )


def test_bootstrap_common_multiplicities_and_empty_replicate_omission():
    jobs = _bootstrap_jobs()
    jobs["copy"] = dict(jobs["all"])
    jobs["one"] = dict(
        jobs["all"], cell_mask=np.asarray([False, False, True, False])
    )
    jobs["empty"] = dict(jobs["all"], cell_mask=np.zeros(4, dtype=bool))
    actual = core.bootstrap_intervals(jobs, np.asarray([90, 90, 10, 40]))
    assert actual["all"] == actual["copy"]
    assert 0 < actual["one"]["B"]["omitted_replicates"] < 500
    assert actual["one"]["B"]["interval"] == [1, 1]
    assert actual["empty"]["B"]["interval"] is None
    assert actual["empty"]["B"]["valid_replicates"] == 0
    assert actual["empty"]["B"]["omitted_replicates"] == 500
    assert actual["empty"]["B"]["undefined_reason"]


def test_bootstrap_conditional_zero_is_omitted_and_not_zero():
    job = {
        "labels_test": np.asarray([core.NONE, core.NONE]),
        "labels_no": np.asarray([core.FULL, core.NONE]),
        "weights": np.ones(2),
        "beneficiary_mask": np.ones(2, dtype=bool),
    }
    actual = core.bootstrap_intervals({"all": job}, np.asarray([1, 2]))["all"]
    assert actual["B_cond"]["interval"] == [1, 1]
    assert actual["B_cond"]["omitted_replicates"] > 0
    assert actual["B"]["valid_replicates"] == 500


def test_diagnostics_distinct_households_units_and_outside_response():
    units = np.asarray([0, 0, 1, 2, 3])
    households = np.asarray([0, 0, 0, 1, 2])
    cut = np.asarray([120, 120, 0, 120, 0])
    baseline = {
        "social_security": np.full(5, 1000.0),
        "ssi_if_takes_up": np.full(5, 100.0),
        "ssi": np.full(5, 100.0),
        "household_state_benefits": np.zeros(3),
        "household_net_income": np.zeros(3),
    }
    scenario = {
        "social_security": np.asarray([879.99, 879.99, 1000, 879.98, 1000]),
        "ssi_if_takes_up": np.asarray([230, 230, 150, 90, 500]),
        "ssi": np.asarray([230, 230, 150, 90, 500]),
        "household_state_benefits": np.asarray([5, 7, 100]),
        "household_net_income": np.asarray([30, -10, 1000]),
    }
    result = core.diagnostics(
        cut, baseline, scenario, units, households, np.asarray([2, 3, 4])
    )
    assert result["beneficiary_households"] == 2
    assert result["attributed_marital_units"] == 2
    assert result["weighted_totals"]["cut"] == 840
    assert result["weighted_totals"]["ssi"] == 590
    assert result["ssi_outside_attributed_units"]["ssi"] == 100
    assert result["weighted_totals"]["household_state_benefits"] == 31
    assert result["weighted_totals"]["household_net_income"] == 30
    assert result["weighted_totals"][
        "social_security_change"
    ] == pytest.approx(-840.1, abs=1e-10)
    assert result["weighted_totals"]["offset_share"] == pytest.approx(
        1 + 30 / 840.1, abs=1e-12, rel=0
    )
    assert result["weighted_totals"]["offset_share_undefined_reason"] is None
    assert result["unit_responses"]["ssi"]["over_replacing"] == {
        "n": 1,
        "W": 2,
    }
    assert result["unit_responses"]["ssi"]["ssi_falls"] == {
        "n": 1,
        "W": 3,
        "weighted_ssi_loss": 30,
    }
    undefined = core.diagnostics(
        np.zeros(5),
        baseline,
        baseline,
        units,
        households,
        np.asarray([2, 3, 4]),
    )
    assert undefined["weighted_totals"]["offset_share"] is None
    assert undefined["weighted_totals"]["offset_share_undefined_reason"] == (
        "no modeled Social Security change in beneficiary households"
    )


@pytest.mark.parametrize(
    "assets, expected", [(1500, True), (50_000, False), (2500, False)]
)
def test_worked_single_person_cases(assets, expected):
    reform, _, cut = core.cut_components(
        {
            name: np.asarray(
                [8916.0 if name == "social_security_retirement" else 0]
            )
            for name in core.COMPONENTS
        },
        "oasi22",
        Decimal("0.78"),
    )
    assert reform["social_security_retirement"][0] == 6948
    assert cut[0] == 1968
    passed = core.resource_test_encoded(
        np.asarray([assets]), np.asarray([0]), np.asarray([False]), 2000, 3000
    )
    assert passed[0] == expected
    no = core.replacement_labels(
        cut, np.asarray([3252]), np.asarray([5220]), np.asarray([0])
    )
    test = core.replacement_labels(
        cut,
        np.asarray([3252]) * passed,
        np.asarray([5220]) * passed,
        np.asarray([0]),
    )
    result = core.statistics(test, no, np.ones(1), np.ones(1, dtype=bool))
    assert result["F_no"] == 1
    assert result["B"] == int(not expected)


def test_worked_joint_and_non_abd_spouse_cases():
    resources, units = np.asarray([2500, 0]), np.asarray([0, 0])
    np.testing.assert_array_equal(
        core.resource_test_encoded(
            resources, units, np.asarray([True, True]), 2000, 3000
        ),
        [True, True],
    )
    np.testing.assert_array_equal(
        core.resource_test_encoded(
            resources, units, np.asarray([False, False]), 2000, 3000
        ),
        [False, True],
    )
    np.testing.assert_array_equal(
        core.resource_test_spousal(
            resources, units, np.asarray([2]), 2000, 3000
        ),
        [True, True],
    )


def test_worked_older_parent_couple_moves_from_full_to_part():
    cut = np.asarray([120, 120, 0])
    units = np.asarray([0, 0, 1])
    baseline, scenario = np.zeros(3), np.asarray([120, 120, 0])
    resources = np.asarray([5000, 0, 0])
    encoded = core.resource_test_encoded(
        resources, units, np.zeros(3, dtype=bool), 2000, 3000
    )
    spousal = core.resource_test_spousal(
        resources, units, np.asarray([2, 1]), 2000, 3000
    )
    no = core.replacement_labels(cut, baseline, scenario, units)
    r0 = core.replacement_labels(
        cut, baseline * encoded, scenario * encoded, units
    )
    r3 = core.replacement_labels(
        cut, baseline * spousal, scenario * spousal, units
    )
    result_r0 = core.statistics(r0, no, np.ones(3), cut > 0)
    result_r3 = core.statistics(r3, no, np.ones(3), cut > 0)
    assert result_r0["B_part"] == 1
    assert result_r0["B"] == 0
    assert result_r3["B"] == 1


def test_frame_hash_guard_never_needs_hdf(tmp_path, monkeypatch):
    path = tmp_path / "invented"
    path.write_bytes(b"invented bytes")
    digest = core.check_frame(path, registered=False)
    monkeypatch.setattr(core, "FRAME_SHA256", digest)
    with pytest.raises(ValueError, match="real frame"):
        core.check_frame(path, registered=False)
    assert core.check_frame(path, registered=True) == digest
    monkeypatch.setattr(core, "FRAME_SHA256", "f" * 64)
    with pytest.raises(ValueError, match="pinned SHA"):
        core.check_frame(path, registered=True)


def _split_frame(totals, percent):
    """Frame components for records splitting ``totals`` by ``percent``."""
    return {
        name: np.asarray(totals, dtype=np.float64) * share / 100
        for name, share in zip(core.COMPONENTS, percent, strict=True)
    }


def test_synthetic_split_accepts_the_registered_proportions():
    # The frame's fixed shares, to the precision a structural read gave.
    exact = [24.964697, 37.93265, 13.545444, 23.557209]
    frame = _split_frame([33528.09, 1200.0, 91234.5], exact)
    synthetic, wrong = core.synthetic_split(frame)
    assert synthetic.all()
    assert not wrong.any()


def test_synthetic_split_flags_other_splits_and_ignores_single_components():
    quarters = _split_frame([40000.0], [25.0, 25.0, 25.0, 25.0])
    synthetic, wrong = core.synthetic_split(quarters)
    assert synthetic.all() and wrong.all()
    single = {name: np.zeros(2) for name in core.COMPONENTS}
    single["social_security_retirement"] = np.array([18000.0, 0.0])
    synthetic, wrong = core.synthetic_split(single)
    assert not synthetic.any() and not wrong.any()
