"""Element 8's merged-stratum rule, on invented designs only."""

from __future__ import annotations

import itertools
import math
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import track_b_b0_1_planning_values as planning  # noqa: E402
import track_b_b0_1_ruled_power as ruled  # noqa: E402

from populace_dynamics.track_b import b2  # noqa: E402


def invented_design(codes, sizes):
    rows = []
    for code, size in zip(codes, sizes, strict=True):
        for cluster in range(size):
            for _ in range(2):
                rows.append(
                    {
                        "person_id": len(rows) + 1,
                        "stratum": code,
                        "cluster": cluster,
                    }
                )
    return pd.DataFrame(rows)


@st.composite
def designs(draw):
    codes = draw(
        st.lists(st.integers(-50, 50), min_size=1, max_size=7, unique=True)
    )
    sizes = draw(
        st.lists(st.integers(1, 5), min_size=len(codes), max_size=len(codes))
    )
    return invented_design(codes, sizes)


@settings(max_examples=100, deadline=None)
@given(designs(), st.integers(0, 2**32 - 1))
def test_merges_are_simultaneous_deterministic_and_conserve_clusters(
    design, shuffle_seed
):
    merged, merges = b2.merge_design_strata(design)
    shuffled, shuffled_merges = b2.merge_design_strata(
        design.sample(frac=1, random_state=shuffle_seed)
    )
    pd.testing.assert_frame_equal(
        merged.sort_values("person_id").reset_index(drop=True),
        shuffled.sort_values("person_id").reset_index(drop=True),
    )
    assert merges == shuffled_merges
    before = design.groupby("stratum")["cluster"].nunique()
    after = merged.groupby("stratum")["cluster"].nunique()
    assert after.sum() == before.sum()
    assert after.sum() == 1 or (after >= 2).all()
    targets = [int(code) for code in before.index[before >= 2]]
    expected = {}
    for code in before.index[before == 1]:
        target = (
            min(targets, key=lambda other: (abs(other - code), other))
            if targets
            else int(before.index.min())
        )
        if code != target:
            expected[int(code)] = target
    assert merges == [
        {"from_stratum": source, "to_stratum": target}
        for source, target in sorted(expected.items())
    ]
    if (before >= 2).all():
        pd.testing.assert_frame_equal(merged, design)


def test_merge_ties_and_all_singletons_use_the_original_codes():
    design = invented_design([10, 20, 30, 21], [2, 1, 2, 1])
    merged, merges = b2.merge_design_strata(design)
    assert merges == [
        {"from_stratum": 20, "to_stratum": 10},
        {"from_stratum": 21, "to_stratum": 30},
    ]
    assert merged.groupby("stratum")["cluster"].nunique().to_dict() == {
        10: 3,
        30: 3,
    }
    singleton, merges = b2.merge_design_strata(
        invented_design([9, 4, 7], [1, 1, 1])
    )
    assert set(singleton["stratum"]) == {4}
    assert singleton["cluster"].nunique() == 3
    assert merges == [
        {"from_stratum": 7, "to_stratum": 4},
        {"from_stratum": 9, "to_stratum": 4},
    ]


@settings(max_examples=100, deadline=None)
@given(designs(), st.integers(0, 9999), st.integers(0, 2**31))
def test_integer_copies_conserve_every_merged_stratum(design, replicate, root):
    merged, _ = b2.merge_design_strata(design)
    summary = b2.design_summary(design)
    if summary["design_degrees_of_freedom"] == 0:
        with pytest.raises(ValueError, match="no degree of freedom"):
            b2.design_multiplicities(design, replicate, root=root)
        return
    scale = summary["scale_l"]
    sizes = merged.groupby("stratum")["cluster"].nunique()
    assert scale == math.lcm(*(int(size) - 1 for size in sizes))
    copies = b2.design_multiplicities(design, replicate, root=root)
    per_cluster = merged.assign(copies=merged["person_id"].map(copies))
    grouped = per_cluster.groupby(["stratum", "cluster"])["copies"]
    assert (grouped.nunique() == 1).all()
    for stratum, size in sizes.items():
        values = grouped.first().loc[stratum].to_numpy()
        assert values.sum() == scale * size
        assert (values % (scale * size // (size - 1)) == 0).all()
    shuffled = design.sample(frac=1, random_state=replicate)
    assert copies == b2.design_multiplicities(shuffled, replicate, root=root)


class EnumeratedGenerator:
    """A prescribed sequence of equally likely ordered cluster draws."""

    def __init__(self, sizes, draws):
        self.sizes = iter(sizes)
        self.draws = iter(draws)

    def integers(self, low, high):
        assert (low, high, next(self.sizes)) == (0, 2, 2)
        return next(self.draws)[0]

    def multinomial(self, count, probabilities):
        size = next(self.sizes)
        assert count == size - 1
        assert np.array_equal(probabilities, np.full(size, 1.0 / size))
        return np.bincount(next(self.draws), minlength=size)


@lru_cache
def exact_copies(sizes):
    """Run the registered sampler for every equally likely small draw."""
    design = invented_design(range(len(sizes)), sizes)
    representatives = design.drop_duplicates(["stratum", "cluster"])[
        "person_id"
    ]
    possibilities = [
        list(itertools.product(range(size), repeat=size - 1)) for size in sizes
    ]
    copies = []
    original_stream = b2.stream
    try:
        for draws in itertools.product(*possibilities):
            generator = EnumeratedGenerator(sizes, draws)
            b2.stream = lambda *_args, generator=generator: generator
            multiplicities = b2.design_multiplicities(design, 0, root=1234)
            copies.append(
                [multiplicities[person] for person in representatives]
            )
    finally:
        b2.stream = original_stream
    return np.asarray(copies, dtype=np.int64)


@settings(max_examples=30, deadline=None)
@given(st.integers(2, 4))
def test_exact_enumeration_is_unbiased_for_small_strata(size):
    copies = exact_copies((size,))
    scale = size - 1
    assert copies.shape == (size ** (size - 1), size)
    np.testing.assert_allclose(copies.mean(axis=0), scale, rtol=0, atol=0)


@settings(max_examples=40, deadline=None)
@given(st.lists(st.integers(-20, 20), min_size=9, max_size=9))
def test_exact_mixed_design_variance_equals_the_textbook_estimator(totals):
    sizes = (2, 3, 4)
    scale = math.lcm(*(size - 1 for size in sizes))
    copies = exact_copies(sizes)
    values = np.asarray(totals, dtype=np.float64)
    replicate_totals = copies @ values
    assert replicate_totals.mean() == pytest.approx(scale * values.sum())
    textbook = 0.0
    offset = 0
    for size in sizes:
        stratum = values[offset : offset + size]
        textbook += (
            size / (size - 1) * np.square(stratum - stratum.mean()).sum()
        )
        offset += size
    assert replicate_totals.var(ddof=0) / scale**2 == pytest.approx(textbook)


@settings(max_examples=10, deadline=None)
@given(st.integers(1, 8))
def test_scale_one_matches_arm_d_for_replicates_zero_through_99(strata):
    design = invented_design(range(strata), [2] * strata)
    assert b2.design_summary(design)["scale_l"] == 1
    for replicate in range(100):
        assert b2.design_multiplicities(
            design, replicate, root=20260930
        ) == planning.design_multiplicities(design, replicate)


@settings(max_examples=100, deadline=None)
@given(designs())
def test_nu_and_published_summary_use_the_merged_strata(design):
    merged, merges = b2.merge_design_strata(design)
    record = b2.design_summary(design)
    sizes = merged.groupby("stratum")["cluster"].nunique()
    assert record["before_merges"] == b2.stratum_census(design)
    assert record["after_merges"] == b2.stratum_census(merged)
    assert record["merges"] == merges
    assert record["design_degrees_of_freedom"] == sizes.sum() - len(sizes)
    if (sizes <= 2).all() and record["design_degrees_of_freedom"]:
        assert record["design_degrees_of_freedom"] == (
            ruled.design_degrees_of_freedom(record["after_merges"])
        )


@settings(max_examples=40, deadline=None)
@given(st.integers(1, 8), st.integers(1, 7))
def test_common_copy_scale_preserves_the_six_level_cells(scale, rotation):
    rows = []
    for person in range(1, 49):
        for year in b2.SCORED_PERIODS:
            rows.append(
                {
                    "person_id": person,
                    "period": year,
                    "cohort": "prime" if person <= 24 else "older",
                    "weight": float(1 + person % 5),
                    "earnings": (
                        0.0
                        if (person + rotation) % 6 == 0
                        else float(1000 + person * 137 + year)
                    ),
                }
            )
    panel = pd.DataFrame(rows)
    multiplicities = {person: 1 + person % 3 for person in range(1, 49)}
    original = b2.cell_values(planning.copy_persons(panel, multiplicities))
    scaled = b2.cell_values(
        planning.copy_persons(
            panel,
            {
                person: count * scale
                for person, count in multiplicities.items()
            },
        )
    )
    for name in b2.LEVEL_CELLS:
        assert original[name] is not None
        assert scaled[name] == original[name]


@pytest.mark.parametrize("column", ["person_id", "stratum", "cluster"])
def test_design_variables_are_required_before_any_resampling(column):
    design = invented_design([4], [2])
    with pytest.raises(ValueError, match="lacks"):
        b2.design_summary(design.drop(columns=column))
    for invalid in (None, 0.5, float("inf")):
        malformed = design.copy()
        malformed[column] = malformed[column].astype(object)
        malformed.loc[0, column] = invalid
        with pytest.raises(ValueError, match="finite integers"):
            b2.design_summary(malformed)


def test_one_cluster_publishes_zero_nu_and_refuses_resampling():
    design = invented_design([42], [1])
    record = b2.design_summary(design)
    assert record["merges"] == []
    assert record["before_merges"] == record["after_merges"]
    assert record["design_degrees_of_freedom"] == record["scale_l"] == 0
    with pytest.raises(ValueError, match="no degree of freedom"):
        b2.design_multiplicities(design, 0, root=20261002)


# The copier at scale L (Q: the pinned copier refuses 1,000 copies or more).


def _panel(persons):
    rows = []
    for person in range(1, persons + 1):
        for year in b2.SCORED_PERIODS:
            rows.append(
                {
                    "person_id": person,
                    "period": year,
                    "cohort": "prime" if person % 2 else "older",
                    "weight": float(1 + person % 5),
                    "earnings": (
                        0.0
                        if person % 7 == 0
                        else float(1000 + person * 137 + year)
                    ),
                }
            )
    return pd.DataFrame(rows)


def test_the_copy_scale_is_the_pinned_one_below_it():
    assert b2.ID_SCALE == planning.ID_SCALE
    assert b2.copy_scale(0) == b2.copy_scale(999) == planning.ID_SCALE
    assert b2.copy_scale(1000) == 10_000
    assert b2.copy_scale(9999) == 10_000
    assert b2.copy_scale(10_000) == 100_000


@settings(max_examples=60, deadline=None)
@given(st.lists(st.integers(0, 999), min_size=12, max_size=12))
def test_below_the_scale_the_copier_is_arm_fs(counts):
    """Differential: below 1,000 copies the frames equal the pinned
    ``copy_persons`` exactly (section 13, "To B2")."""
    panel = _panel(12)
    multiplicity = {person: count for person, count in enumerate(counts, 1)}
    pd.testing.assert_frame_equal(
        b2.copy_persons(panel, multiplicity, planning.copy_persons),
        planning.copy_persons(panel, multiplicity),
    )


@settings(max_examples=20, deadline=None)
@given(
    st.lists(st.integers(0, 3), min_size=6, max_size=6),
    st.integers(1000, 2500),
)
def test_above_the_scale_the_copier_keeps_every_row_and_person(counts, factor):
    """Above 1,000 copies: each person's rows appear exactly c times, in
    the pinned order, under distinct identifiers that decode to the
    person, and every other column is unchanged."""
    panel = _panel(6)
    multiplicity = {
        person: count * factor for person, count in enumerate(counts, 1)
    }
    copied = b2.copy_persons(panel, multiplicity, planning.copy_persons)
    scale = b2.copy_scale(max(multiplicity.values()))
    assert len(copied) == sum(multiplicity[int(p)] for p in panel["person_id"])
    person = copied["person_id"] // scale
    index = copied["person_id"] % scale
    for original, count in multiplicity.items():
        rows = copied[person == original]
        assert sorted(set(index[person == original])) == list(range(count))
        source = panel[panel["person_id"] == original]
        assert len(rows) == count * len(source)
    pairs = copied[["person_id", "period"]]
    assert not pairs.duplicated().any()
    assert copied.equals(
        copied.sort_values(["person_id", "period"], kind="stable")
    )
    restored = copied.assign(person_id=person).drop_duplicates()
    pd.testing.assert_frame_equal(
        restored.sort_values(["person_id", "period"]).reset_index(drop=True),
        panel[panel["person_id"].map(multiplicity).fillna(0) > 0]
        .sort_values(["person_id", "period"])
        .reset_index(drop=True),
        check_dtype=False,
    )


def test_the_level_cells_are_the_same_at_scale_1001():
    """Section 7: a common copy scale leaves the six level cells
    unchanged, including past the pinned copier's limit."""
    panel = _panel(30)
    base = {person: 1 + person % 3 for person in range(1, 31)}
    small = b2.cell_values(b2.copy_persons(panel, base, planning.copy_persons))
    large = b2.cell_values(
        b2.copy_persons(
            panel,
            {person: count * 1001 for person, count in base.items()},
            planning.copy_persons,
        )
    )
    for name in b2.LEVEL_CELLS:
        assert small[name] is not None
        assert large[name] == small[name]


@pytest.mark.parametrize("replicate", [0, 1, 7])
def test_the_sampler_to_copier_path_works_at_l_1001(replicate):
    """The reviewer's design: merged strata of 2, 8, 12 and 14 clusters
    give L = lcm(1, 7, 11, 13) = 1,001, so every positive multiplicity is
    past the pinned copier's limit. The full path still copies each
    stratum's clusters to L * n_h copies in total."""
    design = invented_design([1, 2, 3, 4], [2, 8, 12, 14])
    summary = b2.design_summary(design)
    assert summary["scale_l"] == 1001
    multiplicity = b2.design_multiplicities(
        design, replicate, root=b2.ROOT_SEED
    )
    assert max(multiplicity.values()) >= planning.ID_SCALE
    panel = pd.DataFrame(
        {
            "person_id": design["person_id"].astype("int64"),
            "period": b2.LEVEL_YEARS[0],
        }
    )
    copied = b2.copy_persons(panel, multiplicity, planning.copy_persons)
    scale = b2.copy_scale(max(multiplicity.values()))
    persons = copied["person_id"] // scale
    by_stratum = (
        design.set_index("person_id")["stratum"].reindex(persons).to_numpy()
    )
    totals = pd.Series(1, index=by_stratum).groupby(level=0).sum()
    sizes = design.groupby("stratum")["cluster"].nunique()
    # two persons per invented cluster
    for stratum, size in sizes.items():
        assert totals[stratum] == 2 * 1001 * size
