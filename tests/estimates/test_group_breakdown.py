"""Group-breakdown tabulation core (NASI package G3), on INVENTED rows only.

Every row in this module is invented for testing.  No PSID record, model
projection, oracle benefit or comparator value is read or produced, and no
number here is a model result.  Expected values are hand-computed in the
comments next to each assertion, or come from the existing tabulators
(``cola_age_profile``, ``uniform_cut_tabulation``, Track M's
``tabulation``) run on the same invented rows, or from an independent
plain-Python recomputation written in this file.

Invariants exercised with hypothesis:

* within each dimension, classified categories plus unclassified rows
  partition Total, in unweighted and weighted counts (per draw);
* the ratio of scenario means and every MINT8 statistic are invariant to
  scaling all weights (exactly, for powers of two);
* Total and age-group cells equal ``tabulate_cola_age_profile``; Total and
  sex/marital cells equal ``tabulate_uniform_cut``; Total and sex cells
  equal ``tabulate_track_m`` (differential tests);
* the percentile rule equals an independent exact-Fraction reference and
  agrees with ``uniform_cut_track_u.diagnostics.weighted_quantile`` away
  from exact ties; percentiles lie within [min, max] of the changes;
* percent decrease + unaffected + increase = 100;
* floors are undefined, never zero, with fewer than two usable seeds;
* a group's halves are the full-sample split restricted to the group.
"""

from __future__ import annotations

import dataclasses
import json
import math
from fractions import Fraction

import numpy as np
import pandas as pd
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from populace_dynamics.estimates import cola_age_profile as a7
from populace_dynamics.estimates import group_breakdown as gb
from populace_dynamics.estimates import uniform_cut_tabulation as ut
from populace_dynamics.min_benefit_track_m import tabulation as track_m
from populace_dynamics.uniform_cut_track_u.diagnostics import (
    weighted_quantile,
)

SLOW = settings(
    max_examples=40,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
POINTER = (
    "https://github.com/PolicyEngine/microcosm-dynamics/issues/42"
    "#issuecomment-123"
)


# =========================================================================
# Invented-row builders
# =========================================================================
def _projection_row(
    draw,
    person_id,
    *,
    birth_year,
    base,
    reform,
    weight=1.0,
    family_unit_id=None,
    **attributes,
):
    """One INVENTED cola_age_profile row; one component carries it all."""

    components = (
        {"retired_worker": {"base": base, "reform": reform}}
        if base > 0 or reform > 0
        else {}
    )
    return {
        "draw": draw,
        "person_id": person_id,
        "family_unit_id": (
            person_id if family_unit_id is None else family_unit_id
        ),
        "weight": weight,
        "birth_year": birth_year,
        "beneficiary_base": base > 0,
        "beneficiary_reform": reform > 0,
        "benefit_base": base,
        "benefit_reform": reform,
        "benefit_components": components,
        "age": 2030 - birth_year,
        **attributes,
    }


def _sex_age_scheme(scheme_id="sex_age", age=None):
    """MINT8's Total, Sex and Age dimensions (age bands swappable)."""

    base = gb.get_scheme("mint8_beneficiary_annual")
    keep = {"total", "sex", "age"}
    return gb.derive_scheme(
        base,
        scheme_id=scheme_id,
        title="test: total, sex, age",
        drop=[d.key for d in base.dimensions if d.key not in keep],
        replace={} if age is None else {"age": age},
    )


def _sex_marital_scheme(scheme_id="sex_marital"):
    base = gb.get_scheme("mint8_beneficiary_annual")
    keep = {"total", "sex", "marital_status"}
    return gb.derive_scheme(
        base,
        scheme_id=scheme_id,
        title="test: total, sex, marital status",
        drop=[d.key for d in base.dimensions if d.key not in keep],
    )


def _project(frame, scheme, config, **kwargs):
    assignment = gb.assign_groups(
        frame,
        scheme,
        {"sex": "sex", "age": "age"},
        key_columns=("draw", "person_id"),
        unclassified_codes=kwargs.pop("unclassified_codes", None),
    )
    return gb.tabulate_projection_breakdown(
        frame,
        assignment,
        data_provenance="invented",
        config=config,
        **kwargs,
    )


@st.composite
def projection_frames(draw, allow_difference=False):
    """INVENTED per-person-per-draw rows with sex and age attributes."""

    n_persons = draw(st.integers(1, 9))
    n_draws = draw(st.integers(1, 3))
    persons = [
        {
            "family": draw(st.integers(0, 4)),
            "birth_year": draw(st.integers(1935, 1985)),
            "weight": draw(st.sampled_from([0.0, 0.5, 1.0, 2.0, 3.0, 7.25])),
            "sex": draw(st.sampled_from(["female", "male", None])),
        }
        for _ in range(n_persons)
    ]
    bases = [0.0, 100.0, 495.0, 500.0, 777.0, 1234.5]
    factors = [0.9, 0.99, 1.0, 1.01, 1.05]
    rows = []
    for d in range(n_draws):
        for p, info in enumerate(persons):
            base = draw(st.sampled_from(bases))
            reform = base * draw(st.sampled_from(factors))
            if allow_difference:
                kind = draw(st.sampled_from(["same", "lost", "gained"]))
                if kind == "lost":
                    reform = 0.0
                elif kind == "gained" and base == 0.0:
                    reform = 250.0
            rows.append(
                _projection_row(
                    d,
                    p,
                    birth_year=info["birth_year"],
                    base=base,
                    reform=reform,
                    weight=info["weight"],
                    family_unit_id=info["family"],
                    sex=info["sex"],
                )
            )
    frame = pd.DataFrame(rows)
    config = a7.ColaAgeProfileConfig(
        draw_indices=tuple(range(n_draws)),
        allow_membership_difference=allow_difference,
    )
    return frame, config


def _poverty_frame(rng, n):
    """INVENTED Track U-style observations (not PSID)."""

    statuses = ["married", "widowed", "divorced", "never_married"]
    return pd.DataFrame(
        {
            "observation_id": [f"o{i}" for i in range(n)],
            "person_id": np.arange(n) + 1,
            "family_unit_id": rng.integers(0, max(1, n // 2), n),
            "weight": rng.choice([0.5, 1.0, 2.0, 4.0], n),
            "sex": rng.choice(["female", "male"], n),
            "marital_status_4": rng.choice([*statuses, ut.UNCLASSIFIED], n),
            "birth_year": rng.choice([1937, 1939, 1941], n),
            "stratum": rng.integers(1, 4, n),
            "cluster": rng.integers(1, 3, n),
            "poor_baseline": rng.random(n) < 0.3,
            "poor_reform": rng.random(n) < 0.5,
        }
    )


def _design(rows, *extra):
    pairs = rows[["stratum", "cluster"]].drop_duplicates()
    if extra:
        pairs = pd.concat(
            [pairs, pd.DataFrame(extra, columns=["stratum", "cluster"])],
            ignore_index=True,
        )
    return pairs.reset_index(drop=True)


def _track_m_frame(rng, n):
    """INVENTED Track M-style evaluation rows (not PSID)."""

    frame = pd.DataFrame(
        {
            "person_id": [str(i) for i in range(n)],
            "family_unit_id": rng.integers(0, max(1, n // 2), n),
            "weight": rng.choice([0.5, 1.0, 3.0], n),
            "sex": rng.choice(["female", "male", "unknown"], n),
            "stratum": rng.integers(1, 4, n),
            "cluster": rng.integers(1, 3, n),
            **{f"receives_{k}": rng.random(n) < 0.4 for k in (2, 3, 4, 5)},
        }
    )
    frame.attrs["provenance_kind"] = track_m.INVENTED
    return frame


# =========================================================================
# Category schemes
# =========================================================================
def test_mint8_scheme_rows_follow_the_brief_in_page_order():
    scheme = gb.MINT8_SCHEME
    assert [(d.label, list(d.labels)) for d in scheme.dimensions] == [
        ("Total", ["Total"]),
        ("Sex", ["Female", "Male"]),
        (
            "Race and ethnicity",
            [
                "Hispanic or Latino, any race",
                "White, non-Hispanic",
                "Black or African American, non-Hispanic",
                "All other races, non-Hispanic",
            ],
        ),
        ("Country of birth", ["United States", "Other countries"]),
        ("Age", ["60–69", "70–79", "80–89", "90 or older"]),
        (
            "Marital status",
            ["Married", "Divorced", "Widowed", "Never married"],
        ),
        (
            "Highest education level",
            [
                "Graduate",
                "Bachelor",
                "Associate",
                "High school",
                "Less than high school",
            ],
        ),
        ("Current-law poverty status", ["Above poverty", "In poverty"]),
        (
            "Current-law household income quintile",
            ["Highest", "Second highest", "Middle", "Second lowest", "Lowest"],
        ),
        (
            "Current-law benefit type",
            [
                "Retired worker only",
                "Widow(er) (includes dually entitled)",
                "Spousal (includes dually entitled)",
                "Disabled worker only",
            ],
        ),
    ]
    assert not scheme.composite
    assert any("user-guide.html" in c for c in scheme.citations)
    assert any("increase-payroll-tax-rate" in c for c in scheme.citations)


def test_education_bands_follow_ssa_year_definitions():
    education = gb.MINT8_SCHEME.dimension("education")
    # Graduate > 16, Bachelor 16, Associate 14-15, High school 12-13,
    # Less than high school < 12 (MINT8 Table User Guide).
    expected = {
        0: "less_than_high_school",
        11: "less_than_high_school",
        12: "high_school",
        13: "high_school",
        14: "associate",
        15: "associate",
        16: "bachelor",
        17: "graduate",
        20: "graduate",
    }
    for years, key in expected.items():
        hits = [c.key for c in education.categories if c.contains(years)]
        assert hits == [key], years


def test_poverty_and_cohort_schemes():
    poverty = gb.MINT8_POVERTY_SCHEME
    assert "household_income_quintile" not in poverty.keys
    assert poverty.keys == tuple(
        k for k in gb.MINT8_SCHEME.keys if k != "household_income_quintile"
    )
    cohort = gb.MINT8_COHORT_SCHEME
    assert cohort.keys == (
        "total",
        "sex",
        "race_ethnicity",
        "country_of_birth",
        "education",
        "initial_aime_quintile",
        "lifetime_payroll_tax_quintile",
        "lifetime_payroll_tax_quintile_shared",
    )
    for scheme in (
        gb.MINT8_ANNUAL_WITH_LIFETIME_SCHEME,
        gb.MINT8_POVERTY_WITH_LIFETIME_SCHEME,
    ):
        assert scheme.composite
        assert scheme.keys[-3:] == cohort.keys[-3:]
        assert any("composite" in note for note in scheme.notes)


def test_quintile_rows_are_ranked_highest_first():
    quintile = gb.MINT8_SCHEME.dimension("household_income_quintile")
    assert [(c.label, c.rank) for c in quintile.categories] == [
        ("Highest", 5),
        ("Second highest", 4),
        ("Middle", 3),
        ("Second lowest", 2),
        ("Lowest", 1),
    ]


def test_age_band_sets_include_the_exercise_bands():
    bands = gb.AGE_BAND_SETS["dynasim3_exercises_1_3"]
    assert bands.labels == tuple(g.label for g in a7.DEFAULT_AGE_GROUPS)
    assert [(c.lower, c.upper) for c in bands.categories] == [
        (g.lower, g.upper) for g in a7.DEFAULT_AGE_GROUPS
    ]
    derived = gb.with_age_bands(gb.MINT8_SCHEME, "dynasim3_exercises_1_3")
    assert derived.dimension("age") is bands
    assert derived.composite
    assert derived.keys == gb.MINT8_SCHEME.keys
    taxpayer = gb.AGE_BAND_SETS["mint8_taxpayer"]
    assert taxpayer.labels[-1] == "70 or older"
    with pytest.raises(gb.GroupBreakdownError, match="band_set"):
        gb.with_age_bands(gb.MINT8_SCHEME, "nope")
    with pytest.raises(gb.GroupBreakdownError, match="no dimension"):
        gb.with_age_bands(gb.MINT8_COHORT_SCHEME, "mint8_beneficiary")


def test_registry_takes_an_alternate_scheme_from_existing_row_labels():
    # Butrica and Uccello (2004) rows, as uniform_cut_tabulation records
    # them (labels only; the race codes are this test's own).
    race_rows = ut.NOT_COMPUTED_REPORT_ROWS["race_ethnicity"]["rows"]
    race = gb.Dimension(
        key="race_ethnicity",
        label=ut.NOT_COMPUTED_REPORT_ROWS["race_ethnicity"]["section"],
        kind=gb.CATEGORICAL,
        categories=tuple(
            gb.Category(f"race_{i}", label, codes=(f"r{i}",))
            for i, label in enumerate(race_rows)
        ),
        source="uniform_cut_tabulation.NOT_COMPUTED_REPORT_ROWS",
    )
    scheme = gb.CategoryScheme(
        scheme_id="test_boomers2004_rows",
        title="test alternate scheme",
        population="test population",
        dimensions=(
            gb.MINT8_SCHEME.dimension("total"),
            race,
        ),
        citations=("Butrica and Uccello (2004), labels via Track U",),
    )
    try:
        assert gb.register_scheme(scheme) is scheme
        assert gb.get_scheme("test_boomers2004_rows") is scheme
        assert gb.register_scheme(scheme) is scheme  # idempotent
        twin = gb.CategoryScheme(
            scheme_id="test_boomers2004_rows",
            title="another",
            population="p",
            dimensions=scheme.dimensions,
            citations=scheme.citations,
        )
        with pytest.raises(gb.GroupBreakdownError, match="already"):
            gb.register_scheme(twin)
        assert gb.register_scheme(twin, replace=True) is twin
    finally:
        gb._REGISTRY.pop("test_boomers2004_rows", None)
    with pytest.raises(gb.GroupBreakdownError, match="already"):
        gb.register_scheme(
            gb.derive_scheme(
                gb.MINT8_SCHEME,
                scheme_id="mint8_beneficiary_annual",
                title="x",
            ),
            replace=True,
        )
    with pytest.raises(gb.GroupBreakdownError, match="no registered"):
        gb.get_scheme("missing_scheme")


@pytest.mark.parametrize(
    ("build", "match"),
    [
        (
            lambda: gb.Dimension(
                "x",
                "X",
                gb.BAND,
                (
                    gb.Category("a", "A", lower=0, upper=10),
                    gb.Category("b", "B", lower=10, upper=20),
                ),
            ),
            "overlap",
        ),
        (
            lambda: gb.Dimension(
                "x",
                "X",
                gb.CATEGORICAL,
                (
                    gb.Category("a", "A", codes=("c",)),
                    gb.Category("b", "B", codes=("c",)),
                ),
            ),
            "two categories",
        ),
        (
            lambda: gb.Dimension(
                "x",
                "X",
                gb.QUINTILE,
                tuple(gb.Category(f"q{i}", f"Q{i}", rank=1) for i in range(5)),
            ),
            "ranks 1-5",
        ),
        (
            lambda: gb.Dimension(
                "x", "X", gb.CATEGORICAL, (gb.Category("a", "A", rank=1),)
            ),
            "may not carry",
        ),
        (lambda: gb.Category("a", gb.UNCLASSIFIED), "unclassified"),
        (lambda: gb.Category("Bad Key", "A"), "lower-case"),
        (
            lambda: gb.CategoryScheme(
                "s",
                "t",
                "p",
                (gb.SEX_DIMENSION,),
                ("c",),
            ),
            "first dimension is Total",
        ),
        (
            lambda: gb.CategoryScheme(
                "s", "t", "p", (gb.TOTAL_DIMENSION,), ()
            ),
            "citation",
        ),
        (
            lambda: gb.derive_scheme(
                gb.MINT8_SCHEME, scheme_id="s", title="t", drop=("total",)
            ),
            "cannot be dropped",
        ),
        (
            lambda: gb.derive_scheme(
                gb.MINT8_SCHEME,
                scheme_id="s",
                title="t",
                replace={"age": gb.SEX_DIMENSION},
            ),
            "with that key",
        ),
    ],
)
def test_scheme_validation_refuses(build, match):
    with pytest.raises(gb.GroupBreakdownError, match=match):
        build()


# =========================================================================
# Group assignment
# =========================================================================
def _assignment_frame():
    """INVENTED: six persons with every unclassified route."""

    return pd.DataFrame(
        {
            "person_id": [1, 2, 3, 4, 5, 6],
            "weight": [1.0, 2.0, 3.0, 4.0, 0.0, 5.0],
            "sex": ["female", "male", None, "female", "male", np.nan],
            "marital": [
                "married",
                "separated",
                "widowed",
                None,
                "never_married",
                "divorced",
            ],
            "age": [59, 65, 75.0, 92, np.nan, 85],
            "income": [10.0, 20.0, 30.0, 40.0, 50.0, None],
        }
    )


def _assignment_scheme():
    base = gb.MINT8_SCHEME
    keep = {
        "total",
        "sex",
        "marital_status",
        "age",
        "household_income_quintile",
    }
    return gb.derive_scheme(
        base,
        scheme_id="assignment_test",
        title="t",
        drop=[d.key for d in base.dimensions if d.key not in keep],
    )


def _assign(frame=None, **kwargs):
    frame = _assignment_frame() if frame is None else frame
    options = {
        "key_columns": ("person_id",),
        "unclassified_codes": {"marital_status": ("separated",)},
        **kwargs,
    }
    return gb.assign_groups(
        frame,
        _assignment_scheme(),
        {
            "sex": "sex",
            "marital_status": "marital",
            "age": "age",
            "household_income_quintile": "income",
        },
        **options,
    )


def test_assignment_counts_every_unclassified_route():
    assignment = _assign()
    summaries = {s["key"]: s for s in assignment.dimension_summaries}
    assert summaries["sex"]["unclassified_reasons"] == {"missing": 2}
    assert summaries["marital_status"]["unclassified_reasons"] == {
        "code:separated": 1,
        "missing": 1,
    }
    # age 59 is below 60-69; NaN is missing
    assert summaries["age"]["unclassified_reasons"] == {
        "missing": 1,
        "outside_bands": 1,
    }
    assert summaries["age"]["n_by_category"] == {
        "age_60_69": 1,
        "age_70_79": 1,
        "age_80_89": 1,
        "age_90_plus": 1,
    }
    assert list(assignment.mask("sex", "female")) == [
        True,
        False,
        False,
        True,
        False,
        False,
    ]
    long = assignment.long
    assert len(long) == 6 * len(assignment.scheme.dimensions)
    assert set(long.columns) == {
        "row_id",
        "dimension",
        "label",
        "category",
        "classified",
    }
    row3 = long[(long.row_id == 2) & (long.dimension == "sex")].iloc[0]
    assert (row3.label, row3.category, bool(row3.classified)) == (
        gb.UNCLASSIFIED,
        gb.UNCLASSIFIED,
        False,
    )
    total = long[long.dimension == "total"]
    assert set(total.label) == {"Total"} and total.classified.all()
    json.dumps(assignment.as_dict(), allow_nan=False)


def test_quintiles_by_hand():
    # Weights 1, 2, 3, 4, 0 over incomes 10..50 (the sixth is missing):
    # W = 10; cumulative 1, 3, 6, 10 (50 has no mass).  t1: 2 -> 20;
    # t2: 4 -> 30; t3: 6 hits exactly at 30 -> midpoint (30 + 40) / 2 =
    # 35; t4: 8 -> 40.  Ranks: 10 -> 1, 20 -> 1 (equal to t1 is lower),
    # 30 -> 2, 40 -> 4, 50 -> 5.
    assignment = _assign()
    (summary,) = [
        s
        for s in assignment.dimension_summaries
        if s["key"] == "household_income_quintile"
    ]
    (record,) = summary["quintile_partitions"]
    assert record["thresholds"] == [20.0, 30.0, 35.0, 40.0]
    assert record["n_rows"] == 5 and record["n_positive_weight"] == 4
    codes = [
        assignment._category_index["household_income_quintile"][i]
        for i in range(6)
    ]
    assert codes == [
        "lowest",
        "lowest",
        "second_lowest",
        "second_highest",
        "highest",
        gb.UNCLASSIFIED,
    ]


def test_quintiles_are_cut_within_partitions():
    frame = pd.DataFrame(
        {
            "draw": [0, 0, 0, 0, 0, 1, 1, 1, 1, 1],
            "person_id": [1, 2, 3, 4, 5] * 2,
            "weight": [1.0] * 10,
            "income": [1.0, 2.0, 3.0, 4.0, 5.0, 10.0, 20.0, 30.0, 40.0, 50.0],
        }
    )
    scheme = gb.derive_scheme(
        gb.MINT8_SCHEME,
        scheme_id="partition_test",
        title="t",
        drop=[
            d.key
            for d in gb.MINT8_SCHEME.dimensions
            if d.key not in {"total", "household_income_quintile"}
        ],
    )
    assignment = gb.assign_groups(
        frame,
        scheme,
        {"household_income_quintile": "income"},
        key_columns=("draw", "person_id"),
        quintile_partition=("draw",),
    )
    codes = list(assignment._category_index["household_income_quintile"])
    order = ["lowest", "second_lowest", "middle", "second_highest", "highest"]
    assert codes == order + order


@pytest.mark.parametrize(
    ("change", "match"),
    [
        ({"marital": "cohabiting"}, "no category"),
        ({"age": 65.5}, "integers"),
        ({"age": True}, "boolean"),
        ({"sex": 1}, "strings"),
        ({"income": np.inf}, "finite"),
        ({"person_id": 2}, "identify each row"),
    ],
)
def test_assignment_refuses_bad_values(change, match):
    frame = _assignment_frame()
    for column, value in change.items():
        frame[column] = frame[column].astype(object)
        frame.loc[0, column] = value
    with pytest.raises(gb.GroupBreakdownError, match=match):
        _assign(frame)


def test_assignment_refuses_bad_maps():
    frame = _assignment_frame()
    with pytest.raises(gb.GroupBreakdownError, match="missing"):
        gb.assign_groups(
            frame,
            _assignment_scheme(),
            {"sex": "sex"},
            key_columns=("person_id",),
        )
    with pytest.raises(gb.GroupBreakdownError, match="a category's"):
        _assign(unclassified_codes={"marital_status": ("married",)})
    with pytest.raises(gb.GroupBreakdownError, match="categorical"):
        _assign(unclassified_codes={"age": ("x",)})
    zero = frame.assign(weight=0.0)
    with pytest.raises(gb.GroupBreakdownError, match="no positive weight"):
        _assign(zero)


@st.composite
def attribute_frames(draw):
    n = draw(st.integers(1, 30))
    return pd.DataFrame(
        {
            "person_id": list(range(n)),
            "weight": draw(
                st.lists(
                    st.sampled_from([0.0, 0.5, 1.0, 2.0, 9.0]),
                    min_size=n,
                    max_size=n,
                ).filter(lambda ws: any(w > 0 for w in ws))
            ),
            "sex": draw(
                st.lists(
                    st.sampled_from(["female", "male", None]),
                    min_size=n,
                    max_size=n,
                )
            ),
            "marital": draw(
                st.lists(
                    st.sampled_from(
                        [
                            "married",
                            "divorced",
                            "widowed",
                            "never_married",
                            "separated",
                            None,
                        ]
                    ),
                    min_size=n,
                    max_size=n,
                )
            ),
            "age": draw(
                st.lists(
                    st.one_of(st.integers(40, 105), st.none()),
                    min_size=n,
                    max_size=n,
                )
            ),
            "income": draw(
                st.lists(
                    st.one_of(
                        st.sampled_from([0.0, 1.0, 2.5, 7.0, 100.0]),
                        st.none(),
                    ),
                    min_size=n,
                    max_size=n,
                )
            ),
        }
    )


@SLOW
@given(attribute_frames())
def test_assignment_partitions_every_dimension(frame):
    if (
        frame["income"].isna().all()
        or not (frame.loc[frame["income"].notna(), "weight"] > 0).any()
    ):
        return  # no quintile population: refused, tested above
    assignment = _assign(frame)
    n = len(frame)
    for dimension in assignment.scheme.dimensions:
        masks = [
            assignment.mask(dimension.key, c.key) for c in dimension.categories
        ]
        unclassified = assignment.unclassified_mask(dimension.key)
        stacked = np.vstack([*masks, unclassified]).astype(int)
        # every row is in exactly one category or unclassified
        assert (stacked.sum(axis=0) == 1).all()
        summary = [
            s
            for s in assignment.dimension_summaries
            if s["key"] == dimension.key
        ][0]
        assert summary["n_classified"] + summary["n_unclassified"] == n
        assert sum(summary["unclassified_reasons"].values()) == int(
            unclassified.sum()
        )
    assert not assignment.unclassified_mask("total").any()


# =========================================================================
# Weighted percentiles
# =========================================================================
def _reference_percentile(values, weights, level):
    """Independent exact reference: Fractions, no numpy."""

    pairs = sorted(
        (float(v), Fraction(float(w)))
        for v, w in zip(values, weights, strict=True)
        if w > 0
    )
    total = sum(w for _, w in pairs)
    running = Fraction(0)
    for index, (value, weight) in enumerate(pairs):
        running += weight
        if running >= level * total:
            if running == level * total and index + 1 < len(pairs):
                return (value + pairs[index + 1][0]) / 2
            return value
    raise AssertionError("unreachable")


def test_percentiles_by_hand():
    # values 10, 20, 30, 40, weights 1 each: W = 4.  p10: 0.4 -> 10;
    # median: 2 is hit exactly at 20 -> (20 + 30) / 2 = 25; p90: 3.6 -> 40.
    assert gb.weighted_percentiles(
        [40, 10, 30, 20], [1, 1, 1, 1], (gb.P10, gb.P50, gb.P90)
    ) == [10.0, 25.0, 40.0]
    # weights 1, 1, 2 over 1, 2, 3: W = 4; median 2 hit exactly at 2 ->
    # (2 + 3) / 2 = 2.5; p10 0.4 -> 1; p90 3.6 -> 3
    assert gb.weighted_percentiles(
        [1, 2, 3], [1, 1, 2], (gb.P10, gb.P50, gb.P90)
    ) == [1.0, 2.5, 3.0]
    # a zero-weight value carries no mass and is never the "next" value
    assert gb.weighted_percentiles([1, 2, 3], [1, 0, 1], (gb.P50,)) == [2.0]
    # equal values: the midpoint of a value with itself is the value
    assert gb.weighted_percentiles([5, 5], [1, 1], (gb.P50,)) == [5.0]


@pytest.mark.parametrize(
    ("values", "weights", "levels", "match"),
    [
        ([1.0], [1.0], (0.5,), "Fraction"),
        ([1.0], [1.0], (Fraction(1),), "Fraction"),
        ([1.0], [0.0], (gb.P50,), "all be zero"),
        ([1.0], [-1.0], (gb.P50,), "non-negative"),
        ([np.nan], [1.0], (gb.P50,), "finite"),
        ([], [], (gb.P50,), "non-empty"),
    ],
)
def test_percentile_refusals(values, weights, levels, match):
    with pytest.raises(gb.GroupBreakdownError, match=match):
        gb.weighted_percentiles(values, weights, levels)


_VALUES = st.lists(
    st.sampled_from([-100.0, -5.0, -1.0, 0.0, 0.5, 1.0, 2.0, 37.5]),
    min_size=1,
    max_size=25,
)


@st.composite
def weighted_samples(draw, integer_weights=False):
    values = draw(_VALUES)
    weight = (
        st.integers(0, 6).map(float)
        if integer_weights
        else st.sampled_from([0.0, 0.1, 0.25, 1.0, 1.5, 3.0, 1e-3])
    )
    weights = draw(
        st.lists(weight, min_size=len(values), max_size=len(values)).filter(
            lambda ws: any(w > 0 for w in ws)
        )
    )
    return values, weights


_LEVELS = (gb.P10, gb.P50, gb.P90, *gb.QUINTILE_LEVELS)


@settings(max_examples=300, deadline=None)
@given(weighted_samples())
def test_percentiles_equal_the_exact_reference(sample):
    values, weights = sample
    got = gb.weighted_percentiles(values, weights, _LEVELS)
    expected = [_reference_percentile(values, weights, p) for p in _LEVELS]
    assert got == expected
    positive = [v for v, w in zip(values, weights, strict=True) if w > 0]
    assert all(min(positive) <= g <= max(positive) for g in got)
    p10, p50, p90 = got[:3]
    assert p10 <= p50 <= p90


@settings(max_examples=300, deadline=None)
@given(weighted_samples(integer_weights=True))
def test_percentiles_agree_with_track_u_away_from_exact_ties(sample):
    values, weights = sample
    total = sum(Fraction(w) for w in weights)
    for level in _LEVELS:
        running, tie = Fraction(0), False
        for _value, weight in sorted(zip(values, weights, strict=True)):
            if weight == 0:
                continue
            running += Fraction(weight)
            tie = tie or running == level * total
        got = gb.weighted_percentiles(values, weights, (level,))[0]
        theirs = weighted_quantile(values, weights, float(level))
        if not tie:
            assert got == theirs
        else:
            assert got >= theirs  # the midpoint lies above the lower value


@settings(max_examples=200, deadline=None)
@given(weighted_samples(), st.integers(-8, 8), st.randoms())
def test_percentiles_ignore_weight_scale_and_row_order(sample, power, rnd):
    values, weights = sample
    scaled = [w * 2.0**power for w in weights]
    order = list(range(len(values)))
    rnd.shuffle(order)
    base = gb.weighted_percentiles(values, weights, _LEVELS)
    assert gb.weighted_percentiles(values, scaled, _LEVELS) == base
    assert (
        gb.weighted_percentiles(
            [values[i] for i in order], [weights[i] for i in order], _LEVELS
        )
        == base
    )


@settings(max_examples=300, deadline=None)
@given(weighted_samples())
def test_quintile_thresholds_split_the_weight_exactly(sample):
    values, weights = sample
    ranks, thresholds = gb.weighted_quintile_ranks(values, weights)
    assert set(ranks.tolist()) <= {1, 2, 3, 4, 5}
    total = sum(Fraction(w) for w in weights)
    for k, t in enumerate(thresholds, start=1):
        below = sum(
            Fraction(w) for v, w in zip(values, weights, strict=True) if v < t
        )
        at_or_below = sum(
            Fraction(w) for v, w in zip(values, weights, strict=True) if v <= t
        )
        assert below <= Fraction(k, 5) * total <= at_or_below
    # rank is monotone in value
    pairs = sorted(zip(values, ranks.tolist(), strict=True))
    assert [r for _, r in pairs] == sorted(r for _, r in pairs)


# =========================================================================
# Change classes
# =========================================================================
def test_change_classes_are_exact_at_the_one_percent_threshold():
    base = np.array([500.0, 500.0, 777.0, 100.0, 100.0, 0.0, 200.0])
    reform = np.array([495.0, 505.0, 769.23, 99.5, 101.0, 50.0, 0.0])
    population, change, decrease, increase = gb.classify_changes(base, reform)
    assert population.tolist() == [True] * 5 + [False, True]
    # 495/500 is exactly -1 percent: a decrease; 505/500 exactly +1: an
    # increase.  769.23 (as a float, 769.2300000000000182...) is above
    # 0.99 * 777 = 769.23, so the change is just above -1 percent and
    # unaffected, although the float change rounds to -1.0000000000000009.
    assert change[2] <= -1.0
    assert decrease.tolist() == [True, False, False, False, False, False, True]
    assert increase.tolist() == [False, True, False, False, True, False, False]
    assert math.isnan(change[5])
    assert change[6] == -100.0


@settings(max_examples=300, deadline=None)
@given(
    st.lists(
        st.tuples(
            st.floats(0.01, 1e6, allow_nan=False),
            st.floats(0.0, 2e6, allow_nan=False),
        ),
        min_size=1,
        max_size=20,
    )
)
def test_change_classes_equal_exact_rational_arithmetic(pairs):
    base = np.array([b for b, _ in pairs])
    reform = np.array([r for _, r in pairs])
    _, _, decrease, increase = gb.classify_changes(base, reform)
    for i, (b, r) in enumerate(pairs):
        assert decrease[i] == (100 * Fraction(r) <= 99 * Fraction(b))
        assert increase[i] == (100 * Fraction(r) >= 101 * Fraction(b))


# =========================================================================
# Projection breakdowns (exercises 1 and 3)
# =========================================================================
def _a7_group(result, label):
    (group,) = [g for g in result["groups"] if g["label"] == label]
    return group


def _assert_matches_a7(cell, a7_group):
    for statistic in a7.STATISTICS:
        ours = cell.statistic(statistic)
        theirs = a7_group[statistic]
        assert ours.defined == theirs["defined"]
        assert ours.value == theirs["mean"]
        assert ours.uncertainty["sample_sd"] == theirs["sample_sd"]
        assert ours.uncertainty["per_draw"] == theirs["per_draw"]
        assert ours.uncertainty["floor"] == theirs["floor"]
        assert ours.uncertainty["n_defined_draws"] == (
            theirs["n_defined_draws"]
        )


@SLOW
@given(st.booleans().flatmap(lambda b: projection_frames(b)))
def test_total_and_age_cells_equal_cola_age_profile(sample):
    frame, config = sample
    scheme = _sex_age_scheme(age=gb.AGE_BAND_SETS["dynasim3_exercises_1_3"])
    result = _project(frame, scheme, config)
    by_age = a7.tabulate_cola_age_profile(
        frame, data_provenance="invented", config=config
    )
    for group in a7.DEFAULT_AGE_GROUPS:
        _assert_matches_a7(
            result.cell("age", group.label), _a7_group(by_age, group.label)
        )
    everyone = dataclasses.replace(config, age_groups=(a7.AgeGroup("all", 0),))
    total = a7.tabulate_cola_age_profile(
        frame, data_provenance="invented", config=everyone
    )
    _assert_matches_a7(result.cell("total", "total"), _a7_group(total, "all"))


@SLOW
@given(projection_frames(allow_difference=True))
def test_scenario_specific_membership_matches_cola_age_profile(sample):
    frame, config = sample
    scheme = _sex_age_scheme(age=gb.AGE_BAND_SETS["dynasim3_exercises_1_3"])
    result = _project(frame, scheme, config)
    by_age = a7.tabulate_cola_age_profile(
        frame, data_provenance="invented", config=config
    )
    for group in a7.DEFAULT_AGE_GROUPS:
        _assert_matches_a7(
            result.cell("age", group.label), _a7_group(by_age, group.label)
        )


@SLOW
@given(projection_frames(allow_difference=True))
def test_projection_partitions_and_mint_identities(sample):
    frame, config = sample
    result = _project(frame, _sex_age_scheme(), config)
    total = result.cell("total", "total")
    k = len(config.draw_indices)
    for key in ("sex", "age"):
        dimension = result.dimension(key)
        for d in range(k):
            n = sum(
                c.counts["unweighted_n_current_law_per_draw"][d]
                for c in dimension.cells
            )
            w = math.fsum(
                c.counts["weighted_n_current_law_per_draw"][d]
                for c in dimension.cells
            )
            extra = dimension.unclassified["per_draw"][d]
            assert n + extra["n_current_law"] == (
                total.counts["unweighted_n_current_law_per_draw"][d]
            )
            assert math.isclose(
                w + extra["weight_current_law"],
                total.counts["weighted_n_current_law_per_draw"][d],
                rel_tol=1e-12,
                abs_tol=1e-9,
            )
    for dimension in result.dimensions:
        for cell in dimension.cells:
            stats = {s.statistic: s for s in cell.statistics}
            per_draw = {
                name: stats[name].uncertainty["per_draw"]
                for name in gb.MINT_BENEFIT_STATISTICS
            }
            for d in range(k):
                shares = [
                    per_draw[name][d]
                    for name in (
                        gb.PERCENT_DECREASE,
                        gb.PERCENT_UNAFFECTED,
                        gb.PERCENT_INCREASE,
                    )
                ]
                if shares[0] is None:
                    assert all(s is None for s in shares)
                    continue
                assert math.isclose(sum(shares), 100.0, rel_tol=1e-12)
                p10, p50, p90 = (
                    per_draw[name][d]
                    for name in (
                        gb.CHANGE_P10,
                        gb.CHANGE_MEDIAN,
                        gb.CHANGE_P90,
                    )
                )
                assert p10 <= p50 <= p90
    json.dumps(result.as_dict(), allow_nan=False)


@SLOW
@given(projection_frames(), st.integers(-6, 6))
def test_projection_statistics_ignore_weight_scale(sample, power):
    frame, config = sample
    scaled = frame.assign(weight=frame["weight"] * 2.0**power)
    a = _project(frame, _sex_age_scheme(), config)
    b = _project(scaled, _sex_age_scheme(), config)
    for dim_a, dim_b in zip(a.dimensions, b.dimensions, strict=True):
        for cell_a, cell_b in zip(dim_a.cells, dim_b.cells, strict=True):
            for s_a, s_b in zip(
                cell_a.statistics, cell_b.statistics, strict=True
            ):
                assert s_a.value == s_b.value
                assert s_a.uncertainty["floor"] == s_b.uncertainty["floor"]


@SLOW
@given(projection_frames(), st.sampled_from([0.3, 3.7, 1e3]))
def test_ratio_of_means_ignores_any_weight_scale(sample, factor):
    frame, config = sample
    scaled = frame.assign(weight=frame["weight"] * factor)
    a = _project(frame, _sex_age_scheme(), config)
    b = _project(scaled, _sex_age_scheme(), config)
    for dim_a, dim_b in zip(a.dimensions, b.dimensions, strict=True):
        for cell_a, cell_b in zip(dim_a.cells, dim_b.cells, strict=True):
            s_a = cell_a.statistic(gb.RATIO_OF_SCENARIO_MEANS)
            s_b = cell_b.statistic(gb.RATIO_OF_SCENARIO_MEANS)
            assert s_a.defined == s_b.defined
            if s_a.defined:
                assert math.isclose(
                    s_a.value, s_b.value, rel_tol=1e-9, abs_tol=1e-9
                )


def _manual_side_ratio(frame, side_rows, draws):
    """Plain-Python mean over draws of the ratio of weighted means."""

    values = []
    for d in draws:
        part = frame[side_rows & (frame["draw"] == d).to_numpy()]
        base = part[part["benefit_base"] > 0]
        reform = part[part["benefit_reform"] > 0]
        if base["weight"].sum() <= 0 or reform["weight"].sum() <= 0:
            return None
        mu_b = math.fsum(base["weight"] * base["benefit_base"]) / math.fsum(
            base["weight"]
        )
        mu_r = math.fsum(
            reform["weight"] * reform["benefit_reform"]
        ) / math.fsum(reform["weight"])
        values.append(100 * (mu_r / mu_b - 1))
    return math.fsum(values) / len(values)


@SLOW
@given(projection_frames())
def test_group_floor_uses_the_full_split_restricted_to_the_group(sample):
    frame, config = sample
    result = _project(frame, _sex_age_scheme(), config)
    split = gb.half_split_masks(
        frame["family_unit_id"].tolist(), config.floor_seeds
    )
    for sex in ("female", "male"):
        in_group = (frame["sex"] == sex).to_numpy()
        gaps = []
        for in_a in split.values():
            a = _manual_side_ratio(frame, in_group & in_a, config.draw_indices)
            b = _manual_side_ratio(
                frame, in_group & ~in_a, config.draw_indices
            )
            if a is not None and b is not None:
                gaps.append(abs(a - b))
        floor = (
            result.cell("sex", sex)
            .statistic(gb.RATIO_OF_SCENARIO_MEANS)
            .uncertainty["floor"]
        )
        assert floor["n_seeds"] == len(gaps)
        for ours, manual in zip(floor["values"], gaps, strict=True):
            assert math.isclose(ours, manual, rel_tol=1e-9, abs_tol=1e-9)


def test_a_resplit_of_the_group_would_differ():
    # Ten one-person family units 0-9; women are the even-numbered units.
    # Use interleaved IDs: a prefix would reuse the RNG stream's prefix.
    # The full
    # split restricted to women differs from re-splitting the five women's
    # units alone (seed 0), which is why the group floor never re-splits.
    units = list(range(10))
    full = gb.half_split_masks(units, (0,))[0]
    women = np.array([u % 2 == 0 for u in units])
    resplit = gb.half_split_masks(units[::2], (0,))[0]
    assert full[women].tolist() != resplit.tolist()


def test_floor_is_undefined_not_zero_with_one_seed():
    rows = [
        _projection_row(0, p, birth_year=1960, base=1000.0, reform=990.0)
        for p in range(6)
    ]
    frame = pd.DataFrame([{**r, "sex": "female"} for r in rows])
    config = a7.ColaAgeProfileConfig(draw_indices=(0,), floor_seeds=(0,))
    result = _project(frame, _sex_age_scheme(), config)
    for dimension in result.dimensions:
        for cell in dimension.cells:
            for statistic in cell.statistics:
                floor = statistic.uncertainty["floor"]
                assert floor["defined"] is False
                assert floor["mean"] is None and floor["sd"] is None
                assert floor["n_seeds"] <= 1


def test_projection_by_hand():
    # Draw 0 only.  Women: p0 w1 1000 -> 990 (-1%: decrease), p1 w3
    # 2000 -> 2100 (+5%: increase).  mu_base = (1000 + 6000) / 4 = 1750;
    # mu_reform = (990 + 6300) / 4 = 1822.5; ratio 100 * (1822.5 / 1750 -
    # 1) = 4.142857...  Decrease share 25%, increase 75%; changes -1 (w1)
    # and +5 (w3): p10 -> -1, median: 2 of 4 reached at +5 -> 5, p90 5.
    frame = pd.DataFrame(
        [
            _projection_row(
                0, 0, birth_year=1960, base=1000.0, reform=990.0, sex="female"
            ),
            _projection_row(
                0,
                1,
                birth_year=1960,
                base=2000.0,
                reform=2100.0,
                weight=3.0,
                sex="female",
            ),
            _projection_row(
                0, 2, birth_year=1960, base=500.0, reform=500.0, sex=None
            ),
        ]
    )
    config = a7.ColaAgeProfileConfig(draw_indices=(0,))
    result = _project(frame, _sex_age_scheme(), config)
    women = result.cell("sex", "Female")
    stats = {s.statistic: s.value for s in women.statistics}
    assert stats[gb.RATIO_OF_SCENARIO_MEANS] == pytest.approx(
        100 * (1822.5 / 1750 - 1)
    )
    assert stats[gb.PERCENT_DECREASE] == 25.0
    assert stats[gb.PERCENT_INCREASE] == 75.0
    assert stats[gb.PERCENT_UNAFFECTED] == 0.0
    assert stats[gb.CHANGE_P10] == pytest.approx(-1.0)
    assert stats[gb.CHANGE_MEDIAN] == pytest.approx(5.0)
    assert stats[gb.CHANGE_P90] == pytest.approx(5.0)
    men = result.cell("sex", "male").statistic(gb.RATIO_OF_SCENARIO_MEANS)
    assert not men.defined and men.value is None
    assert "empty_baseline_membership" in men.undefined_reason
    sex = result.dimension("sex")
    assert sex.unclassified["reasons"] == {"missing": 1}
    assert sex.ssa_subgroup_suppressed
    assert set(sex.suppressed_by) == {"Female", "Male"}
    assert women.flags == {
        "ssa_disclosure_below_100": True,
        "below_30": True,
        "ssa_numerator_1_to_9": True,
    }
    decrease = women.statistic(gb.PERCENT_DECREASE)
    assert decrease.flags["ssa_numerator_1_to_9"] is True
    assert decrease.unweighted_n == 2 and decrease.weighted_n == 4.0


def test_membership_difference_is_refused_unless_configured():
    frame = pd.DataFrame(
        [
            _projection_row(
                0, 0, birth_year=1960, base=1000.0, reform=0.0, sex="female"
            ),
            _projection_row(
                0, 1, birth_year=1960, base=1000.0, reform=990.0, sex="male"
            ),
        ]
    )
    with pytest.raises(gb.GroupBreakdownError, match="only one scenario"):
        _project(
            frame,
            _sex_age_scheme(),
            a7.ColaAgeProfileConfig(draw_indices=(0,)),
        )


def test_projection_refuses_rows_the_assignment_was_not_built_from():
    frame, config = _small_projection()
    assignment = gb.assign_groups(
        frame,
        _sex_age_scheme(),
        {"sex": "sex", "age": "age"},
        key_columns=("draw", "person_id"),
    )
    reordered = frame.iloc[::-1]
    with pytest.raises(gb.GroupBreakdownError, match="key digest"):
        gb.tabulate_projection_breakdown(
            reordered, assignment, data_provenance="invented", config=config
        )
    static_keys = gb.assign_groups(
        frame.assign(row=range(len(frame))),
        _sex_age_scheme(),
        {"sex": "sex", "age": "age"},
        key_columns=("row",),
    )
    with pytest.raises(gb.GroupBreakdownError, match="keyed on"):
        gb.tabulate_projection_breakdown(
            frame, static_keys, data_provenance="invented", config=config
        )


def _small_projection():
    frame = pd.DataFrame(
        [
            _projection_row(
                d,
                p,
                birth_year=1950 + p,
                base=1000.0 + p,
                reform=990.0 + p,
                sex="female" if p % 2 else "male",
            )
            for d in (0, 1)
            for p in range(4)
        ]
    )
    return frame, a7.ColaAgeProfileConfig(draw_indices=(0, 1))


# =========================================================================
# Static breakdowns (exercises 2 and 4)
# =========================================================================
def _poverty(rows, **kwargs):
    assignment = gb.assign_groups(
        rows,
        _sex_marital_scheme(),
        {"sex": "sex", "marital_status": "marital_status_4"},
        key_columns=("observation_id",),
        unclassified_codes={"marital_status": (ut.UNCLASSIFIED,)},
    )
    return gb.tabulate_poverty_breakdown(
        rows,
        assignment,
        design=kwargs.pop("design", _design(rows, (9, 1))),
        data_provenance="invented",
        id_column="observation_id",
        **kwargs,
    )


_TRACK_U_CELLS = {
    ("total", "total"): "all",
    ("sex", "female"): "women",
    ("sex", "male"): "men",
    ("marital_status", "married"): "married",
    ("marital_status", "widowed"): "widowed",
    ("marital_status", "divorced"): "divorced",
    ("marital_status", "never_married"): "never_married",
}
_TRACK_U_STATISTICS = {
    gb.POVERTY_RATE_CURRENT_LAW: "baseline_rate",
    gb.POVERTY_RATE_PROPOSAL: "reform_rate",
    gb.POVERTY_RATE_CHANGE: "delta",
}


@SLOW
@given(st.integers(0, 2**32 - 1), st.integers(1, 40))
def test_poverty_cells_equal_uniform_cut_tabulation(seed, n):
    rows = _poverty_frame(np.random.default_rng(seed), n)
    design = _design(rows, (9, 1))
    ours = _poverty(rows, design=design)
    theirs = {
        cell["cell"]: cell
        for cell in ut.tabulate_uniform_cut(
            rows, data_provenance="invented", design=design
        )["cells"]
    }
    for (dimension, category), name in _TRACK_U_CELLS.items():
        cell = ours.cell(dimension, category)
        reference = theirs[name]
        assert cell.counts["unweighted_n"] == reference["n_observations"]
        assert cell.counts["weighted_n"] == reference["weight_total"]
        for statistic, key in _TRACK_U_STATISTICS.items():
            value = cell.statistic(statistic)
            assert value.defined == reference["defined"]
            if reference["defined"]:
                assert value.value == reference[key]
                assert value.uncertainty["design_se"] == (
                    reference["design_se"][key]
                )
            assert value.uncertainty["floor"] == reference["floor"][key]
    # partition of the weighted total within each dimension
    total = ours.cell("total", "total").counts["weighted_n"]
    for key in ("sex", "marital_status"):
        dimension = ours.dimension(key)
        parts = math.fsum(c.counts["weighted_n"] for c in dimension.cells)
        assert math.isclose(
            parts + dimension.unclassified["weighted_n"],
            total,
            rel_tol=1e-12,
            abs_tol=1e-12,
        )


def test_poverty_numbers_by_hand():
    rows = pd.DataFrame(
        {
            "observation_id": ["o1", "o2", "o3", "o4"],
            "person_id": [1, 2, 3, 4],
            "family_unit_id": [1, 1, 2, 3],
            "weight": [1000.0, 3000.0, 2000.0, 4000.0],
            "sex": ["female", "female", "male", "male"],
            "marital_status_4": ["married", "widowed", "married", "divorced"],
            "birth_year": [1941] * 4,
            "stratum": [1, 1, 2, 2],
            "cluster": [1, 2, 1, 2],
            "poor_baseline": [True, False, False, False],
            "poor_reform": [True, True, False, True],
        }
    )
    result = _poverty(rows)
    total = result.cell("total", "total")
    values = {s.statistic: s.value for s in total.statistics}
    # W = 10000; poor under current law 1000 (10%); with the proposal
    # 1000 + 3000 + 4000 = 8000 (80%); change 70 points; in thousands 1
    # and 8, change 7; percent change in the number 700%.
    assert values == {
        gb.POVERTY_RATE_CURRENT_LAW: 10.0,
        gb.POVERTY_RATE_PROPOSAL: 80.0,
        gb.POVERTY_RATE_CHANGE: 70.0,
        gb.NUMBER_POOR_CURRENT_LAW: 1.0,
        gb.NUMBER_POOR_PROPOSAL: 8.0,
        gb.NUMBER_POOR_CHANGE: 7.0,
        gb.NUMBER_POOR_PERCENT_CHANGE: 700.0,
    }
    men = result.cell("sex", "male").statistic(gb.NUMBER_POOR_PERCENT_CHANGE)
    assert not men.defined
    assert (
        men.undefined_reason == "nobody in the cell is poor under current law"
    )
    count = total.statistic(gb.NUMBER_POOR_CURRENT_LAW)
    assert count.uncertainty["design_se"] is None
    assert "weighted count" in count.uncertainty["design_se_note"]
    assert count.uncertainty["floor"] is not None
    assert "half the full" in count.uncertainty["floor_note"]
    json.dumps(result.as_dict(), allow_nan=False)


def _shares(rows, **kwargs):
    base = gb.MINT8_SCHEME
    scheme = gb.derive_scheme(
        base,
        scheme_id="share_test",
        title="t",
        drop=[d.key for d in base.dimensions if d.key not in {"total", "sex"}],
    )
    assignment = gb.assign_groups(
        rows,
        scheme,
        {"sex": "sex"},
        key_columns=("person_id",),
        unclassified_codes={"sex": ("unknown",)},
    )
    return gb.tabulate_share_breakdown(
        rows,
        assignment,
        indicator_column=kwargs.pop("indicator_column", "receives_2"),
        design=kwargs.pop("design", _design(rows)),
        data_provenance="invented",
        **kwargs,
    )


@SLOW
@given(st.integers(0, 2**32 - 1), st.integers(1, 40))
def test_share_cells_equal_track_m(seed, n):
    rows = _track_m_frame(np.random.default_rng(seed), n)
    design = _design(rows, (7, 1))
    theirs = track_m.tabulate_track_m(
        rows, row_id="MS0", data_provenance="invented", design=design
    )
    for option in track_m.TABLE6_OPTIONS:
        ours = _shares(
            rows, indicator_column=f"receives_{option}", design=design
        )
        for row, key in (
            ("all", "total"),
            ("men", "male"),
            ("women", "female"),
        ):
            (reference,) = [
                c
                for c in theirs["cells"]
                if c["option"] == option and c["row"] == row
            ]
            dimension = "total" if row == "all" else "sex"
            share = ours.cell(dimension, key).statistic(gb.SHARE)
            assert share.defined == reference["defined"]
            if reference["defined"]:
                assert share.value == reference["share_percent"]
                assert share.weighted_n == reference["weighted_n"]
                assert share.unweighted_n == reference["unweighted_n"]
                assert share.uncertainty["design_se"] == (
                    reference["design_se"]
                )
            assert share.uncertainty["floor"] == reference["floor"]


def test_suppression_flags_never_drop_cells():
    # INVENTED: 100 women, 29 men, 1 unknown sex.
    n = 130
    rows = pd.DataFrame(
        {
            "person_id": [str(i) for i in range(n)],
            "family_unit_id": list(range(n)),
            "weight": [1.0] * n,
            "sex": ["female"] * 100 + ["male"] * 29 + ["unknown"],
            "stratum": [1, 2] * (n // 2),
            "cluster": [1] * 65 + [2] * 65,
            "receives_2": [i % 3 == 0 for i in range(n)],
        }
    )
    result = _shares(rows)
    sex = result.dimension("sex")
    assert [c.label for c in sex.cells] == ["Female", "Male"]
    assert sex.cell("female").flags == {
        "ssa_disclosure_below_100": False,
        "below_30": False,
    }
    assert sex.cell("male").flags == {
        "ssa_disclosure_below_100": True,
        "below_30": True,
    }
    assert sex.ssa_subgroup_suppressed and sex.suppressed_by == ("Male",)
    assert sex.unclassified["unweighted_n"] == 1
    assert sex.unclassified["reasons"] == {"code:unknown": 1}
    total = result.dimension("total")
    assert not total.ssa_subgroup_suppressed
    assert sex.cell("male").statistic(gb.SHARE).value is not None


def _static_benefits(rows, **kwargs):
    base = gb.MINT8_SCHEME
    scheme = gb.derive_scheme(
        base,
        scheme_id="static_benefit_test",
        title="t",
        drop=[d.key for d in base.dimensions if d.key not in {"total", "sex"}],
    )
    assignment = gb.assign_groups(
        rows, scheme, {"sex": "sex"}, key_columns=("person_id",)
    )
    return gb.tabulate_static_benefit_breakdown(
        rows,
        assignment,
        design=_design(rows),
        data_provenance="invented",
        **kwargs,
    )


def _static_benefit_frame(rng, n):
    base = rng.choice([0.0, 100.0, 500.0, 777.0], n)
    return pd.DataFrame(
        {
            "person_id": np.arange(n),
            "family_unit_id": rng.integers(0, max(1, n // 2), n),
            "weight": rng.choice([0.0, 1.0, 2.5], n),
            "sex": rng.choice(["female", "male"], n),
            "stratum": rng.integers(1, 3, n),
            "cluster": rng.integers(1, 3, n),
            "benefit_base": base,
            "benefit_reform": base * rng.choice([0.87, 0.99, 1.0, 1.01], n),
        }
    )


def test_static_benefit_by_hand():
    # Uniform 13% cut for three beneficiaries; a fourth has no benefit.
    rows = pd.DataFrame(
        {
            "person_id": [1, 2, 3, 4],
            "family_unit_id": [1, 2, 3, 4],
            "weight": [1.0, 1.0, 2.0, 5.0],
            "sex": ["female", "male", "female", "male"],
            "stratum": [1, 1, 2, 2],
            "cluster": [1, 2, 1, 2],
            "benefit_base": [1000.0, 2000.0, 1500.0, 0.0],
            "benefit_reform": [870.0, 1740.0, 1305.0, 0.0],
        }
    )
    result = _static_benefits(rows)
    total = result.cell("total", "total")
    values = {s.statistic: s.value for s in total.statistics}
    assert values[gb.PERCENT_DECREASE] == 100.0
    assert values[gb.PERCENT_INCREASE] == 0.0
    for name in (gb.CHANGE_P10, gb.CHANGE_MEDIAN, gb.CHANGE_P90):
        assert values[name] == pytest.approx(-13.0)
    assert total.statistic(gb.PERCENT_DECREASE).unweighted_n == 3
    assert total.statistic(gb.PERCENT_DECREASE).weighted_n == 4.0
    median = total.statistic(gb.CHANGE_MEDIAN)
    assert median.uncertainty["design_se"] is None
    assert "percentile" in median.uncertainty["design_se_note"]
    assert total.statistic(gb.PERCENT_DECREASE).uncertainty["design_se"]
    json.dumps(result.as_dict(), allow_nan=False)


@SLOW
@given(st.integers(0, 2**32 - 1), st.integers(1, 30))
def test_static_benefit_identities(seed, n):
    rows = _static_benefit_frame(np.random.default_rng(seed), n)
    result = _static_benefits(rows)
    population = rows["benefit_base"].to_numpy() > 0
    weights = rows["weight"].to_numpy()
    total_w = math.fsum(weights[population].tolist())
    sex = result.dimension("sex")
    parts = math.fsum(
        c.statistic(gb.PERCENT_DECREASE).weighted_n for c in sex.cells
    )
    assert math.isclose(
        parts + sex.unclassified["weighted_n"], total_w, abs_tol=1e-12
    )
    for dimension in result.dimensions:
        for cell in dimension.cells:
            stats = {s.statistic: s for s in cell.statistics}
            if not stats[gb.PERCENT_DECREASE].defined:
                continue
            assert math.isclose(
                stats[gb.PERCENT_DECREASE].value
                + stats[gb.PERCENT_UNAFFECTED].value
                + stats[gb.PERCENT_INCREASE].value,
                100.0,
                rel_tol=1e-12,
            )
            mask = population & (
                np.ones(n, dtype=bool)
                if dimension.key == "total"
                else (rows["sex"] == cell.category).to_numpy()
            )
            mask &= weights > 0
            changes = 100 * (
                rows["benefit_reform"].to_numpy()[mask]
                / rows["benefit_base"].to_numpy()[mask]
                - 1
            )
            for name in (gb.CHANGE_P10, gb.CHANGE_MEDIAN, gb.CHANGE_P90):
                assert changes.min() <= stats[name].value <= changes.max()


# =========================================================================
# Provenance and the result schema
# =========================================================================
def test_registration_pointer_pattern_equals_track_m():
    assert gb.REGISTRATION_POINTER.pattern == (
        track_m.REGISTRATION_POINTER.pattern
    )


def test_invented_results_carry_labels_scheme_and_definitions():
    frame, config = _small_projection()
    result = _project(
        frame,
        _sex_age_scheme(),
        config,
        labels=("PSID-seeded closed cohort",),
        post_hoc_labels=("post hoc, not blind",),
        upstream={"row": "R0"},
    )
    out = result.as_dict()
    assert out["labels"] == [
        gb.INVENTED_DATA_LABEL,
        "PSID-seeded closed cohort",
    ]
    assert out["post_hoc_labels"] == ["post hoc, not blind"]
    assert out["scheme"]["citations"]
    assert out["statistic_definitions"][gb.CHANGE_MEDIAN]["mint8_column"] == (
        "Percent change in Social Security benefits at the— Median"
    )
    assert out["conventions"]["percentile_definition"] == (
        gb.PERCENTILE_DEFINITION
    )
    assert out["upstream"] == {"row": "R0"}
    assert out["schema_version"] == gb.SCHEMA_VERSION
    again = _project(
        frame,
        _sex_age_scheme(),
        config,
        labels=("PSID-seeded closed cohort",),
        post_hoc_labels=("post hoc, not blind",),
        upstream={"row": "R0"},
    )
    assert json.dumps(again.as_dict(), sort_keys=True) == json.dumps(
        out, sort_keys=True
    )


@pytest.mark.parametrize(
    ("overrides", "match"),
    [
        ({"registration_pointer": None}, "registration pointer"),
        (
            {"registration_pointer": "https://example.org/42"},
            "registration pointer",
        ),
        ({"labels": ()}, "needs labels"),
        ({"post_hoc_labels": ()}, "post hoc labels"),
        ({"labels": (gb.INVENTED_DATA_LABEL,)}, "invented label"),
        ({"labels": "one string"}, "sequence"),
    ],
)
def test_registered_real_refusals(overrides, match):
    frame, config = _small_projection()
    assignment = gb.assign_groups(
        frame,
        _sex_age_scheme(),
        {"sex": "sex", "age": "age"},
        key_columns=("draw", "person_id"),
    )
    options = {
        "registration_pointer": POINTER,
        "labels": ("label",),
        "post_hoc_labels": ("registered, one-shot, post hoc, not blind",),
        **overrides,
    }
    with pytest.raises(gb.GroupBreakdownError, match=match):
        gb.tabulate_projection_breakdown(
            frame,
            assignment,
            data_provenance="registered_real",
            config=config,
            **options,
        )


def test_provenance_kind_guards():
    rows = _track_m_frame(np.random.default_rng(3), 12)
    rows.attrs["provenance_kind"] = gb.PSID_FILES
    with pytest.raises(gb.GroupBreakdownError, match="staged PSID"):
        _shares(rows)
    rows.attrs["provenance_kind"] = track_m.INVENTED
    base = gb.MINT8_SCHEME
    scheme = gb.derive_scheme(
        base,
        scheme_id="guard_test",
        title="t",
        drop=[d.key for d in base.dimensions if d.key != "total"],
    )
    assignment = gb.assign_groups(rows, scheme, {}, key_columns=("person_id",))
    with pytest.raises(gb.GroupBreakdownError, match="marked invented"):
        gb.tabulate_share_breakdown(
            rows,
            assignment,
            indicator_column="receives_2",
            design=_design(rows),
            data_provenance="registered_real",
            registration_pointer=POINTER,
            labels=("label",),
            post_hoc_labels=("post hoc",),
        )


def test_static_inputs_are_refused_when_malformed():
    rows = _track_m_frame(np.random.default_rng(5), 10)
    with pytest.raises(gb.GroupBreakdownError, match="not in the design"):
        _shares(rows, design=pd.DataFrame({"stratum": [99], "cluster": [1]}))
    with pytest.raises(gb.GroupBreakdownError, match="boolean"):
        _shares(rows.assign(receives_2=1))
    with pytest.raises(gb.GroupBreakdownError, match="floor_split_unit"):
        _shares(rows, floor_split_unit="household")
    with pytest.raises(gb.GroupBreakdownError, match="floor seeds"):
        _shares(rows, floor_seeds=(0, 0))
