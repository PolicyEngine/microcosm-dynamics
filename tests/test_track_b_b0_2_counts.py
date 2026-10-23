"""B0.2's version-1 protocol, tested solely on invented frames."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import track_b_b0_2_counts as script  # noqa: E402

from scripts import track_b_b0_1_counts as b01  # noqa: E402

PROTOCOL_SHA256 = (
    "f2fd0a3eaf7cbfd99da21d7f885ca05e9e6b62764fe4db895b0f28b84ccd4bc6"
)
WAVES = tuple(range(1999, 2024, 2))
SENTINEL = 9_999_998
PERSON_COLUMNS = [
    "person_id",
    "period",
    "age",
    "sequence",
    "relationship",
    "weight",
    "interview",
]
FORBIDDEN_COLUMNS = (
    "marital_status",
    "death_year",
    "social_security_amount",
    "disability_status",
)


def _row(
    person,
    wave=2011,
    age=62,
    *,
    sequence=1,
    relationship=10,
    weight=1.0,
    interview=None,
):
    return dict(
        zip(
            PERSON_COLUMNS,
            (
                person,
                wave,
                age,
                sequence,
                relationship,
                weight,
                person if interview is None else interview,
            ),
            strict=True,
        )
    )


def _inputs(rows, *, invalid=(), missing=(), accuracy=()):
    """Make complete wave mappings; no person or income is observed."""
    people = pd.DataFrame(rows, columns=PERSON_COLUMNS)
    labor = {}
    invalid = set(invalid)
    missing = set(missing)
    accuracy = set(accuracy)
    for wave in WAVES:
        interviews = set(people.loc[people["period"] == wave, "interview"])
        records = []
        for interview in sorted(interviews | {999_999}):
            if (wave, interview) in missing:
                continue
            records.append(
                {
                    "interview": interview,
                    "head_labor": (
                        float(SENTINEL)
                        if (wave, interview, "head") in invalid
                        else 123.0
                    ),
                    "spouse_labor": (
                        float(SENTINEL)
                        if (wave, interview, "spouse") in invalid
                        else 0.0
                    ),
                    "head_acc": int((wave, interview, "head") in accuracy),
                    "spouse_acc": int((wave, interview, "spouse") in accuracy),
                }
            )
        labor[wave] = pd.DataFrame(records)
    anchor = people.loc[people["period"] == 2011].drop(columns="period")
    ids = sorted(people["person_id"].unique())
    design = pd.DataFrame({"person_id": ids, "stratum": 1, "cluster": ids})
    return people, labor, anchor, design


def _validity(labor):
    return {
        wave: script.validity_frame(frame) for wave, frame in labor.items()
    }


def _counts(inputs):
    people, labor, anchor, design = inputs
    return script.structural_counts(people, _validity(labor), anchor, design)


def _bytes(record):
    return json.dumps(record, sort_keys=True, allow_nan=False).encode()


def _worked_rosters():
    inputs = _inputs(
        [
            _row(1, age=29, weight=1.0, interview=10),
            _row(2, age=30, relationship=20, weight=2.0, interview=10),
            _row(3, age=64, relationship=30, weight=3.0, interview=10),
            _row(4, age=65, relationship=30, weight=4.0, interview=20),
            _row(5, age=80, weight=5.0, interview=30),
            _row(6, age=62, sequence=21, weight=6.0, interview=40),
            _row(7, age=62, weight=0.0, interview=50),
            _row(1, 2013, age=31, interview=101),
            _row(2, 2013, age=32, interview=102),
            _row(3, 2013, age=66, interview=103),
            _row(1, 2015, age=33, sequence=21, interview=201),
            _row(2, 2015, age=34, relationship=30, weight=0, interview=202),
        ],
        invalid={(2011, 30, "head")},
    )
    people, labor, anchor, _ = inputs
    anchor = anchor.copy()
    anchor.loc[anchor["person_id"] == 1, "age"] = 30
    anchor.loc[anchor["person_id"] == 2, "age"] = 29
    anchor.loc[anchor["person_id"] == 3, "age"] = 65
    anchor["weight"] = [7.0, 1.0, 3.0, 0.0, 5.0, 6.0, 0.0]
    design = pd.DataFrame(
        {
            "person_id": list(range(1, 8)),
            "stratum": [1, 1, 2, 2, 2, 2, 2],
            "cluster": [10, 10, 20, 20, 10, 30, 40],
        }
    )
    return people, labor, anchor, design


def _invariance_inputs():
    """Exercise nonempty rosters, older support, both lags and B3L."""
    return _inputs(
        [
            _row(
                person,
                wave,
                base_age + wave - 2007,
                relationship={103: 20, 104: 30}.get(person, 10),
                weight=float(person - 99 + (wave % 3)),
                interview=101 if person == 103 else person,
            )
            for wave in WAVES
            for person, base_age in (
                (101, 60),
                (102, 43),
                (103, 62),
                (104, 35),
            )
        ],
        invalid={(2013, 101, "spouse")},
        accuracy={(2009, 101, "head"), (2009, 101, "spouse")},
    )


# --------------------------------------------------------------------------
# Protocol and outcome blindness
# --------------------------------------------------------------------------
def test_protocol_block_is_pinned():
    text = (ROOT / "docs/design/track_b_b0_2_protocol.md").read_bytes()
    begin = b"<!-- protocol:begin -->"
    end = b"<!-- protocol:end -->"
    block = text[text.index(begin) : text.index(end) + len(end)]
    assert hashlib.sha256(block).hexdigest() == PROTOCOL_SHA256
    assert script.PROTOCOL_SHA256 == PROTOCOL_SHA256


def test_b01_helpers_are_imported_unchanged():
    for name in (
        "validity_frame",
        "earnings_rows",
        "kish_n_eff",
        "cluster_worst_n_eff",
        "_individual_variables",
    ):
        assert getattr(script, name) is getattr(b01, name)


@settings(max_examples=25, deadline=None)
@given(
    st.lists(
        st.floats(
            min_value=-1e9,
            max_value=SENTINEL - 1,
            allow_nan=False,
            allow_infinity=False,
        ),
        min_size=8 * len(WAVES),
        max_size=8 * len(WAVES),
    )
)
def test_counts_are_byte_invariant_to_valid_labor_values(values):
    inputs = _invariance_inputs()
    people, labor, anchor, design = inputs
    changed = {}
    replacements = iter(values)
    for wave, frame in labor.items():
        frame = frame.copy()
        for column in ("head_labor", "spouse_labor"):
            frame[column] = [
                replacement if value < SENTINEL else value
                for value, replacement in zip(
                    frame[column], replacements, strict=False
                )
            ]
        changed[wave] = frame
    original = _counts(inputs)
    assert original["b3"]["by_wave"]["2011"]["62_64"]["persons"] > 0
    assert original["b3"]["lag_pairs"]["4"]["2007_2011"]["62_64"] > 0
    assert original["b3l"]["rosters"]["D2006"]["overall"]["persons"] > 0
    assert original["b3l"]["later_support"]["2009"]["62_64"]["persons"] > 0
    assert original["outside_b2"]["overall"]["persons"] > 0
    assert _bytes(original) == _bytes(
        _counts((people, changed, anchor, design))
    )


@settings(max_examples=25, deadline=None)
@given(
    st.lists(
        st.one_of(
            st.integers(),
            st.text(max_size=20),
            st.booleans(),
            st.none(),
        ),
        min_size=len(FORBIDDEN_COLUMNS),
        max_size=len(FORBIDDEN_COLUMNS),
    )
)
def test_counts_are_byte_invariant_to_forbidden_columns(values):
    people, labor, anchor, design = _invariance_inputs()
    additions = dict(zip(FORBIDDEN_COLUMNS, values, strict=True))
    baseline = script.structural_counts(
        people, _validity(labor), anchor, design
    )
    changed_labor = {
        wave: frame.assign(**additions) for wave, frame in labor.items()
    }
    # Test both read-time reduction and extra columns on already-read frames.
    changed_validity = {
        wave: frame.assign(**additions)
        for wave, frame in _validity(changed_labor).items()
    }
    changed = script.structural_counts(
        people.assign(**additions),
        changed_validity,
        anchor.assign(**additions),
        design.assign(**additions),
    )
    assert _bytes(baseline) == _bytes(changed)


def _assert_no_forbidden_output(value):
    forbidden = (
        "disposition",
        "death",
        "died",
        "transition",
        "earnings_level",
        "earnings level",
        "labor_level",
        "labor level",
        "income_level",
        "income level",
        "quantile",
        "positive_pair",
        "participation",
        "marital",
        "disability",
        "payment",
        "recipient",
        "power",
    )

    def check(value):
        if isinstance(value, dict):
            for key, item in value.items():
                check(key)
                check(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                check(item)
        elif isinstance(value, str):
            assert not any(word in value.lower() for word in forbidden)

    check(value)


def test_no_forbidden_output_keys_or_values():
    _assert_no_forbidden_output(_counts(_worked_rosters()))


# --------------------------------------------------------------------------
# Hand-derived rows, rosters and bands
# --------------------------------------------------------------------------
def test_valid_rows_require_present_role_positive_weight_and_role_validity():
    people, labor, _, _ = _inputs(
        [
            _row(1),
            _row(2, sequence=20, relationship=20),
            _row(3, relationship=22),
            _row(4, relationship=30),
            _row(5, sequence=0),
            _row(6, sequence=21),
            _row(7, weight=0),
            _row(8, relationship=20),
            _row(9),
            _row(10, weight=-1),
        ],
        invalid={(2011, 8, "spouse")},
        missing={(2011, 9)},
        accuracy={(2011, 2, "spouse"), (2011, 3, "head")},
    )
    rows = script.valid_rows(people, _validity(labor))
    assert set(rows["person_id"]) == {1, 2, 3}
    assert set(rows["period"]) == {2011}
    assert rows.set_index("person_id")["acc_flag"].to_dict() == {
        1: False,
        2: True,
        3: False,
    }


def test_rosters_and_age_30_proxy_boundary_use_their_own_weights_and_ages():
    people, labor, anchor, design = _worked_rosters()
    counts = script.roster_counts(people, _validity(labor), anchor, design)
    full = counts["R_FULL"]
    assert full["overall"] == {
        "persons": 5,
        "households": 3,
        "design_strata": 2,
        "design_clusters": 3,
        "kish_n_eff": pytest.approx(225 / 55),
        "household_cluster_worst_n_eff": pytest.approx(225 / 77),
        "design_cluster_worst_n_eff": pytest.approx(225 / 83),
    }
    assert {
        band: count["persons"] for band, count in full["by_age_band"].items()
    } == {
        "1_24": 0,
        "25_44": 2,
        "45_61": 0,
        "62_64": 1,
        "65_66": 1,
        "67_69": 0,
        "70_79": 0,
        "80_plus": 1,
    }
    b2 = counts["R_B2"]["overall"]
    assert b2["persons"] == 2
    assert b2["households"] == 1
    assert b2["kish_n_eff"] == 1.8
    assert b2["household_cluster_worst_n_eff"] == 1.0
    proxy = counts["R_TA_PROXY"]
    assert proxy["overall"]["persons"] == 3
    assert proxy["overall"]["kish_n_eff"] == pytest.approx(225 / 83)
    assert proxy["overall"]["household_cluster_worst_n_eff"] == 1.8
    assert proxy["by_age_band"]["25_44"]["persons"] == 1
    assert proxy["by_age_band"]["62_64"]["persons"] == 0
    assert proxy["by_age_band"]["65_66"]["persons"] == 1


def test_band_edges_and_b3_support_are_hand_counted():
    ages = [1, 24, 25, 44, 45, 61, 62, 64, 65, 66, 67, 69, 70, 79, 80, 81, 125]
    people, labor, anchor, design = _inputs(
        [_row(i, age=age) for i, age in enumerate(ages, 1)],
        accuracy={(2011, 7, "head"), (2011, 9, "head")},
    )
    counts = script.structural_counts(people, _validity(labor), anchor, design)
    roster_bands = counts["rosters"]["R_FULL"]["by_age_band"]
    assert {key: value["persons"] for key, value in roster_bands.items()} == {
        "1_24": 2,
        "25_44": 2,
        "45_61": 2,
        "62_64": 2,
        "65_66": 2,
        "67_69": 2,
        "70_79": 2,
        "80_plus": 3,
    }
    support = counts["b3"]["by_wave"]["2011"]
    for band in ("62_64", "65_66", "67_69"):
        assert support[band]["valid_rows"] == 2
        assert support[band]["persons"] == 2
        assert support[band]["households"] == 2
        assert support[band]["design_strata"] == 1
        assert support[band]["design_clusters"] == 2
        assert support[band]["kish_n_eff"] == 2.0
        assert support[band]["household_cluster_worst_n_eff"] == 2.0
        assert support[band]["design_cluster_worst_n_eff"] == 2.0
    assert [support[band]["accuracy_positive_rows"] for band in support] == [
        1,
        1,
        0,
    ]
    assert counts["b3"]["distinct_persons_by_band"] == {
        "62_64": 2,
        "65_66": 2,
        "67_69": 2,
    }


def test_b3_lag_pairs_use_exact_lags_and_later_wave_band():
    people, labor, _, design = _inputs(
        [
            _row(1, 1999, 60),
            _row(1, 2001, 62),
            _row(1, 2003, 64),
            _row(2, 1999, 61),
            _row(2, 2001, 63),
            _row(2, 2003, 65),
            _row(3, 1999, 63),
            _row(3, 2001, 65),
            _row(3, 2003, 67),
            _row(4, 2001, 67),
            _row(4, 2003, 69),
            _row(5, 1999, 69),
            _row(5, 2001, 71),
        ],
        invalid={(2001, 3, "head")},
    )
    counts = script.b3_counts(people, _validity(labor), design)
    pairs = counts["lag_pairs"]
    assert set(pairs) == {"2", "4"}
    assert set(pairs["2"]) == {f"{wave}_{wave + 2}" for wave in WAVES[:-1]}
    assert set(pairs["4"]) == {f"{wave}_{wave + 4}" for wave in WAVES[:-2]}
    assert pairs["2"]["1999_2001"] == {
        "62_64": 2,
        "65_66": 0,
        "67_69": 0,
    }
    assert pairs["2"]["2001_2003"] == {
        "62_64": 1,
        "65_66": 1,
        "67_69": 1,
    }
    assert pairs["4"]["1999_2003"] == {
        "62_64": 1,
        "65_66": 1,
        "67_69": 1,
    }
    assert counts["distinct_persons_by_band"] == {
        "62_64": 3,
        "65_66": 1,
        "67_69": 3,
    }


def test_b3l_uses_2007_origin_and_fixed_origin_weights_for_later_support():
    people, labor, _, design = _inputs(
        [
            _row(1, 2007, 60, weight=2),
            _row(1, 2009, 62, weight=100),
            _row(1, 2011, 64),
            _row(1, 2023, 76),
            _row(2, 2007, 25, relationship=30),
            _row(2, 2009, 27),
            _row(3, 2007, 43, weight=4),
            _row(3, 2009, 45),
            _row(3, 2011, 47, weight=8),
            _row(4, 2007, 64),
            _row(4, 2009, 66, weight=0),
            _row(5, 2007, 60, sequence=21),
            _row(5, 2011, 64),
            _row(6, 2007, 59),
            _row(6, 2009, 62, weight=999),
        ]
    )
    counts = script.b3l_counts(people, _validity(labor), design)
    assert counts["origin_wave"] == 2007
    rosters = counts["rosters"]
    assert rosters["R2006_FULL"]["overall"]["persons"] == 5
    assert rosters["D2006"]["overall"]["persons"] == 4
    assert rosters["D2006"]["by_age_band"]["25_44"]["persons"] == 1
    assert rosters["D2006"]["by_age_band"]["45_61"]["persons"] == 2
    assert rosters["D2006"]["by_age_band"]["62_64"]["persons"] == 1
    support = counts["later_support"]
    assert set(support) == {str(wave) for wave in WAVES if wave >= 2009}
    assert support["2009"] == {
        "25_44": {"persons": 0, "kish_n_eff": 0.0},
        "45_61": {"persons": 1, "kish_n_eff": 1.0},
        "62_64": {"persons": 2, "kish_n_eff": 1.8},
        "65_66": {"persons": 0, "kish_n_eff": 0.0},
        "67_69": {"persons": 0, "kish_n_eff": 0.0},
    }
    assert support["2011"]["62_64"] == {
        "persons": 1,
        "kish_n_eff": 1.0,
    }
    assert all(item["persons"] == 0 for item in support["2023"].values())


def test_outside_b2_excludes_entire_anchor_households_and_counts_later_units():
    people, labor, _, design = _worked_rosters()
    counts = script.outside_b2_counts(people, _validity(labor), design)
    # Persons 1 and 2 form B2; their household also excludes person 3.
    assert counts["overall"] == {
        "persons": 2,
        "households": 2,
        "design_strata": 1,
        "design_clusters": 2,
        "kish_n_eff": pytest.approx(81 / 41),
        "household_cluster_worst_n_eff": pytest.approx(81 / 41),
        "design_cluster_worst_n_eff": pytest.approx(81 / 41),
    }
    assert counts["by_age_band"]["62_64"]["persons"] == 0
    assert counts["by_age_band"]["65_66"]["persons"] == 1
    assert counts["by_age_band"]["80_plus"]["persons"] == 1
    # The 2015 row for person 2 has zero weight and another relationship,
    # but is present, and therefore still identifies a B2 household.
    assert counts["b2_households_by_wave"] == {"2013": 2, "2015": 1}


def test_effective_sizes_match_hand_formulas_and_composite_design_clusters():
    weights = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    assert script.kish_n_eff(weights) == pytest.approx(225 / 55)
    assert script.cluster_worst_n_eff(
        weights, np.array([10, 10, 10, 20, 30])
    ) == pytest.approx(225 / 77)
    counts = _counts(_worked_rosters())
    full = counts["rosters"]["R_FULL"]["overall"]
    # Cluster label 10 occurs in two different strata: three design units.
    assert full["design_clusters"] == 3
    assert full["design_cluster_worst_n_eff"] == pytest.approx(225 / 83)


def test_zero_weight_sets_have_zero_effective_size():
    inputs = _inputs([_row(1, 2007, weight=0), _row(1, weight=0)])
    counts = _counts(inputs)
    for roster in counts["rosters"].values():
        assert roster["overall"]["persons"] == 0
        for key in (
            "kish_n_eff",
            "household_cluster_worst_n_eff",
            "design_cluster_worst_n_eff",
        ):
            assert roster["overall"][key] == 0.0
    assert counts["b3"]["by_wave"]["2011"]["62_64"]["kish_n_eff"] == 0
    assert counts["b3l"]["later_support"]["2011"]["62_64"] == {
        "persons": 0,
        "kish_n_eff": 0.0,
    }


def test_b3_lag_pairs_keep_nonempty_2009_origins():
    people, labor, _, design = _inputs(
        [
            _row(1, 2007, 60),
            _row(1, 2009, 62),
            _row(1, 2011, 64),
            _row(1, 2013, 66),
            _row(2, 2009, 63),
            _row(2, 2011, 65),
            _row(2, 2013, 67),
        ]
    )
    pairs = script.b3_counts(people, _validity(labor), design)["lag_pairs"]
    assert pairs["2"]["2007_2009"] == {"62_64": 1, "65_66": 0, "67_69": 0}
    assert pairs["2"]["2009_2011"] == {"62_64": 1, "65_66": 1, "67_69": 0}
    assert pairs["4"]["2009_2013"] == {"62_64": 0, "65_66": 1, "67_69": 1}


def test_known_age_partition_and_reader_maximum_are_hand_counted():
    ages = [0, 999, -1, 125.5, 126, float("nan"), 1, 24, 80, 81, 125]
    counts = _counts(
        _inputs([_row(i, age=age) for i, age in enumerate(ages, 1)])
    )
    roster = counts["rosters"]["R_FULL"]
    assert roster["overall"]["persons"] == 11
    assert roster["unknown_age"]["persons"] == 6
    assert roster["by_age_band"]["1_24"]["persons"] == 2
    assert roster["by_age_band"]["80_plus"]["persons"] == 3
    assert (
        sum(item["persons"] for item in roster["by_age_band"].values())
        + roster["unknown_age"]["persons"]
        == 11
    )
    proxy = counts["rosters"]["R_TA_PROXY"]
    assert proxy["overall"]["persons"] == 3
    assert proxy["unknown_age"]["persons"] == 0
    assert script.age67._MAX_AGE_CODE == 125
    assert script.ROSTER_BANDS[-1][2] == script.age67._MAX_AGE_CODE


def test_effective_sizes_are_coarsened_from_their_own_unrounded_values():
    inputs = _inputs(
        [_row(i, age=29, weight=1.02 if i == 15 else 1) for i in range(1, 16)]
    )
    counts = _counts(inputs)
    kish = counts["rosters"]["R_FULL"]["overall"]["kish_n_eff"]
    assert 14.999 < kish < 15
    assert script.coarsen(kish, 10) == 10
    assert script.coarsen(round(kish, 3), 10) == 20


# --------------------------------------------------------------------------
# Disclosure, using invented counts and structural frames only
# --------------------------------------------------------------------------
def _path_value(value, path):
    for key in path:
        value = value[key]
    return value


def _table_registry(sets, *, unit_type="persons"):
    registry = script.SetRegistry()
    counts = {}
    for name, members in sets.items():
        registry.add((name,), unit_type, members)
        counts[name] = len(members)
    return counts, registry


@pytest.mark.parametrize(
    ("base", "values", "expected"),
    [
        (
            10,
            [0, 1, 9, 10, 14, 15, 24, 25],
            [0, "<10", "<10", 10, 10, 20, 20, 30],
        ),
        (
            50,
            [0, 1, 49, 50, 74, 75, 124, 125],
            [0, "<50", "<50", 50, 50, 100, 100, 150],
        ),
    ],
)
def test_coarsening_boundaries_round_halves_up(base, values, expected):
    assert [script.coarsen(value, base) for value in values] == expected
    assert script.coarsen(base + base / 2 - 0.001, base) == base
    assert script.coarsen(base + base / 2, base) == 2 * base
    assert script.count_interval(0, base) == (0, 0)
    assert script.count_interval(f"<{base}", base) == (1, base - 1)
    assert script.count_interval(2 * base, base) == (
        2 * base - base // 2,
        2 * base + base // 2 - 1,
    )
    assert script.count_interval(base, base) == (base, base + base // 2 - 1)


@pytest.mark.parametrize("base", script.DISCLOSURE_BASES)
def test_count_intervals_are_exact_preimages_of_coarsening(base):
    """Each interval is exactly the integers that coarsen to its value,
    found by enumeration rather than from the interval rule."""
    preimages = {}
    for value in range(0, 4 * base):
        preimages.setdefault(script.coarsen(value, base), []).append(value)
    for published, values in preimages.items():
        if published != 4 * base:
            low, high = script.count_interval(published, base)
            assert values == list(range(low, high + 1)), published


def test_a_published_base_bounds_its_effective_count_from_base(
    monkeypatch,
):
    """An effective size published as B means the size is at least B,
    so its count is at least B, not B/2. A remainder of 7 inside a set
    of 12 whose Kish size is 10 therefore has a minimum of 1."""
    counts, registry = _table_registry(
        {"persons": set(range(12)), "part": set(range(5))}
    )
    counts["kish_n_eff"] = 10.0
    registry.effective(("kish_n_eff",), ("persons",))
    original = script.count_interval
    # Broaden the count intervals so only the effective bound can lift
    # the remainder's minimum above 0.
    monkeypatch.setattr(
        script,
        "count_interval",
        lambda value, base: (0, original(value, base)[1]),
    )
    audit = script.audit_counts(counts, registry, 10)
    remainder = [q for q in audit["quantities"] if q["true_size"] == 7]
    assert remainder and remainder[0]["minimum"] == 1


@pytest.mark.parametrize("size", range(11))
def test_sensitive_atom_threshold_includes_one_through_nine(size):
    counts, registry = _table_registry({"persons": set(range(size))})
    audit = script.audit_counts(counts, registry, 10)
    assert audit["audited"] == int(1 <= size <= 9)
    assert audit["failed"] == 0


def test_disclosure_registry_covers_all_statistics_and_correct_unit_types():
    people, labor, anchor, design = _invariance_inputs()
    validity = _validity(labor)
    counts = script.structural_counts(people, validity, anchor, design)
    registry = script.disclosure_registry(people, validity, anchor, design)
    leaves = dict(script._leaves(counts))
    assert set(leaves) == set(registry.sets) | set(registry.effective_bounds)
    for path, (_, units) in registry.sets.items():
        assert leaves[path] == len(units), path
    prefix = ("rosters", "R_FULL", "overall")
    assert registry.sets[(*prefix, "persons")][0] == "persons"
    assert registry.sets[(*prefix, "households")][0] == "households_2011"
    assert registry.sets[(*prefix, "design_strata")][0] == "strata"
    assert registry.sets[(*prefix, "design_clusters")][0] == "clusters"
    assert registry.effective_bounds[(*prefix, "kish_n_eff")] == (
        *prefix,
        "persons",
    )
    assert registry.effective_bounds[
        (*prefix, "household_cluster_worst_n_eff")
    ] == (*prefix, "households")
    assert registry.effective_bounds[
        (*prefix, "design_cluster_worst_n_eff")
    ] == (*prefix, "design_clusters")
    clusters = registry.sets[(*prefix, "design_clusters")][1]
    assert all(
        isinstance(cluster, tuple) and len(cluster) == 2
        for cluster in clusters
    )


def test_disclosure_integer_hidden_band_attack_is_blocked_on_full_release():
    inputs = _inputs(
        [
            *[_row(person, age=29) for person in range(1, 19)],
            _row(19, age=63),
            _row(20, age=66),
        ]
    )
    people, labor, anchor, design = inputs
    raw = _counts(inputs)
    assert raw["rosters"]["R_FULL"]["overall"]["persons"] == 20
    assert raw["rosters"]["R_FULL"]["by_age_band"]["25_44"]["persons"] == 18
    registry = script.disclosure_registry(
        people, _validity(labor), anchor, design
    )
    published, disclosure, private = script.release_counts(raw, registry)
    assert published and disclosure["base"] in (10, 50, 100, 500)
    assert private["audits"][-1]["failed"] == 0
    assert all(
        item["maximum"] - item["minimum"] >= 4
        for item in private["audits"][-1]["quantities"]
    )
    assert (
        published["rosters"]["R_FULL"]["by_age_band"]["25_44"]["persons"] != 18
    )


def test_disclosure_unpublished_coresident_remainder_is_audited():
    inputs = _inputs(
        [
            *[_row(person, age=40) for person in range(1, 21)],
            _row(21, age=40, relationship=30, interview=1),
        ]
    )
    people, labor, anchor, design = inputs
    raw = _counts(inputs)
    assert raw["rosters"]["R_FULL"]["overall"]["persons"] == 21
    assert raw["rosters"]["R_B2"]["overall"]["persons"] == 20
    assert raw["outside_b2"]["overall"]["persons"] == 0
    registry = script.disclosure_registry(
        people, _validity(labor), anchor, design
    )
    full = registry.sets[("rosters", "R_FULL", "overall", "persons")][1]
    domain = registry.sets[("rosters", "R_B2", "overall", "persons")][1]
    assert full - domain == {21}
    published, _, private = script.release_counts(raw, registry)
    assert published
    sensitive = [
        q
        for q in private["audits"][-1]["quantities"]
        if q["unit_type"] == "persons" and q["true_size"] == 1
    ]
    assert sensitive and all(q["protected"] for q in sensitive)


def test_disclosure_audits_multi_atom_published_subset_differences():
    counts, registry = _table_registry(
        {
            "total": set(range(15)),
            "subset": set(range(10)),
            "distinguish": {10, 11},
        }
    )
    audit = script.audit_counts(counts, registry, 10)
    differences = [q for q in audit["quantities"] if q["kind"] == "difference"]
    assert any(
        q["true_size"] == 5 and len(q["atoms"]) == 2 for q in differences
    )


def test_effective_size_attack_registers_household_and_design_lower_bounds():
    inputs = _inputs(
        [
            _row(
                person,
                age=20 if person <= 10 else 25,
                relationship=30,
                interview=(person + 1) // 2 if person <= 10 else person - 5,
            )
            for person in range(1, 31)
        ]
    )
    people, labor, anchor, design = inputs
    design["stratum"] = design["person_id"]
    counts = _counts(inputs)
    registry = script.disclosure_registry(
        people, _validity(labor), anchor, design
    )
    prefix = ("rosters", "R_FULL", "by_age_band", "25_44")
    assert _path_value(counts, (*prefix, "households")) == 20
    assert (
        _path_value(counts, (*prefix, "household_cluster_worst_n_eff")) == 20
    )
    assert registry.effective_bounds[
        (*prefix, "household_cluster_worst_n_eff")
    ] == (*prefix, "households")
    published, _, private = script.release_counts(counts, registry)
    assert published and private["audits"][-1]["failed"] == 0


def test_audit_applies_effective_bound_independently_of_count_interval(
    monkeypatch,
):
    counts, registry = _table_registry({"persons": set(range(5))})
    counts["kish_n_eff"] = 5.0
    registry.effective(("kish_n_eff",), ("persons",))
    original = script.count_interval
    # With identical monotone coarsening, a valid effective bound is
    # redundant with its count's lower bound. Broaden only that count
    # interval to exercise the required effective-size constraint itself.
    monkeypatch.setattr(
        script,
        "count_interval",
        lambda value, base: (0, original(value, base)[1]),
    )
    audit = script.audit_counts(counts, registry, 10)
    assert audit["quantities"][0]["minimum"] == 1


def _singleton_table(size, *, partial=None):
    sets = {"total": set(range(size))}
    sets.update({f"cell_{i}": {i} for i in range(size)})
    if partial is not None:
        for size_part in (partial,) if isinstance(partial, int) else partial:
            sets[f"partial_{size_part}"] = set(range(size_part))
    return _table_registry(sets)


def test_disclosure_ladder_reaches_50_and_requires_width_four():
    counts, registry = _singleton_table(21)
    initial = script.audit_counts(counts, registry, 10)
    assert initial["failed"] == 21
    assert all(q["maximum"] - q["minimum"] == 3 for q in initial["quantities"])
    published, disclosure, private = script.release_counts(counts, registry)
    assert disclosure["base"] == 50
    assert [attempt["base"] for attempt in disclosure["attempts"]] == [10, 50]
    assert private["audits"][-1]["failed"] == 0
    assert set(published.values()) == {"<50"}


def test_disclosure_no_base_passes_and_names_no_failing_quantity():
    # Positive cells in the 14/74/149 subsets fill their count upper
    # bounds at B=10/50/100; at B=500 the 499-person total does so.
    counts, registry = _singleton_table(499, partial=(14, 74, 149))
    published, disclosure, private = script.release_counts(counts, registry)
    assert published == {}
    assert disclosure["base"] is None
    assert [attempt["base"] for attempt in disclosure["attempts"]] == [
        10,
        50,
        100,
        500,
    ]
    assert all(attempt["failed"] for attempt in disclosure["attempts"])
    assert all(
        set(attempt) == {"base", "audited", "failed"}
        for attempt in disclosure["attempts"]
    )
    assert private["audits"][0]["atom_sizes"]["persons"] == [1] * 499
    assert "cell_" not in json.dumps(disclosure)
    assert "atoms" not in json.dumps(disclosure)


def test_disclosure_public_has_no_small_values_sets_or_atom_fields():
    people, labor, anchor, design = _invariance_inputs()
    validity = _validity(labor)
    raw = script.structural_counts(people, validity, anchor, design)
    registry = script.disclosure_registry(people, validity, anchor, design)
    published, disclosure, private = script.release_counts(raw, registry)
    base = disclosure["base"]
    assert base is not None
    for path, value in script._leaves(published):
        assert not isinstance(value, (set, frozenset))
        if isinstance(value, (int, float)):
            assert value == 0 or value >= base, (path, value)
    public_bytes = _bytes({"counts": published, "disclosure": disclosure})
    for forbidden in (
        b'"sets"',
        b'"atoms"',
        b'"atom_sizes"',
        b'"true_size"',
        b'"minimum"',
        b'"maximum"',
    ):
        assert forbidden not in public_bytes
    assert "atom_sizes" in private["audits"][0]


@pytest.mark.parametrize(
    "sizes", [(1, 1, 1), (1, 2, 3), (3, 3, 4), (3, 7, 8), (1, 2, 10)]
)
def test_integer_audit_extrema_agree_with_bruteforce(sizes):
    from itertools import product

    a, b, c = (
        set(range(sum(sizes[:i]), sum(sizes[: i + 1]))) for i in range(3)
    )
    counts, registry = _table_registry({"ab": a | b, "ac": a | c, "bc": b | c})
    model = script.build_atom_models(registry)["persons"]
    matrix = model["matrix"].toarray().astype(int)

    def preimage(published):
        values = [
            v for v in range(0, 60) if script.coarsen(v, 10) == published
        ]
        return min(values), max(values)

    bounds = [preimage(script.coarsen(count, 10)) for count in counts.values()]
    maximum = max(upper for _, upper in bounds)
    feasible = [
        np.array(candidate)
        for candidate in product(range(maximum + 1), repeat=3)
        if all(
            low <= observed <= high
            for observed, (low, high) in zip(
                matrix @ candidate, bounds, strict=True
            )
        )
    ]
    assert feasible
    audit = script.audit_counts(counts, registry, 10)
    for quantity in audit["quantities"]:
        values = [
            int(candidate[quantity["atoms"]].sum()) for candidate in feasible
        ]
        assert quantity["minimum"] == min(values)
        assert quantity["maximum"] == max(values)
    if sizes == (1, 1, 1):
        # Continuous relaxation has maximum 8.5, attained at (8.5,.5,.5).
        assert {q["maximum"] for q in audit["quantities"]} == {8}


def test_atom_grouping_and_sparse_matrix_on_test_sized_population():
    from scipy.sparse import issparse

    groups = [set(range(30 * i, 30 * (i + 1))) for i in range(6)]
    groups[0] = {0, 1, 2}
    sets = {
        f"set_{i}": set().union(
            *(groups[j] for j in range(6) if ((i % 20) >> j) & 1)
        )
        for i in range(40)
    }
    counts, registry = _table_registry(sets)
    model = script.build_atom_models(registry)["persons"]
    assert issparse(model["matrix"])
    assert len(model["sizes"]) <= len(groups)
    assert model["matrix"].shape[0] < len(sets)  # duplicate sets share rows
    published, disclosure, _ = script.release_counts(counts, registry)
    assert published and disclosure["attempts"][-1]["failed"] == 0
    assert disclosure["attempts"][-1]["audited"] > 0


def test_audit_requires_proven_optimum_and_sixty_second_integer_programs(
    monkeypatch,
):
    from types import SimpleNamespace

    calls = []

    def no_optimum(objective, **kwargs):
        calls.append(kwargs)
        return SimpleNamespace(status=1, success=False, fun=None)

    monkeypatch.setattr(script, "milp", no_optimum)
    counts, registry = _table_registry({"persons": {1}})
    published, disclosure, private = script.release_counts(counts, registry)
    assert published == {}
    assert len(calls) == 8
    assert all(np.all(call["integrality"] == 1) for call in calls)
    assert all(call["options"]["time_limit"] == 60 for call in calls)
    assert all(attempt["failed"] == 1 for attempt in disclosure["attempts"])
    assert all(
        q["minimum"] is None and q["maximum"] is None
        for audit in private["audits"]
        for q in audit["quantities"]
    )


# --------------------------------------------------------------------------
# Output guards, checked before a reader can be reached
# --------------------------------------------------------------------------
def test_main_refuses_to_overwrite(tmp_path, monkeypatch):
    existing = tmp_path / "counts.json"
    existing.write_text("{}")

    def no_read(*args, **kwargs):
        pytest.fail("output refusal must happen before any input is read")

    monkeypatch.setattr(script.psid, "_resolve_data_dir", no_read)
    with pytest.raises(SystemExit, match="refusing to overwrite"):
        script.main(
            [
                "--out",
                str(existing),
                "--local-copy",
                str(tmp_path / "local.json"),
            ]
        )
    assert existing.read_text() == "{}"


def test_main_refuses_committed_evidence_directory(tmp_path, monkeypatch):
    evidence = tmp_path / "".join(("ru", "ns"))
    monkeypatch.setattr(script, "RUNS_DIR", evidence)

    def no_read(*args, **kwargs):
        pytest.fail("output refusal must happen before any input is read")

    monkeypatch.setattr(script.psid, "_resolve_data_dir", no_read)
    target = evidence / "nested" / "counts.json"
    with pytest.raises(SystemExit, match="writes no file"):
        script.main(
            [
                "--out",
                str(target),
                "--local-copy",
                str(tmp_path / "local.json"),
            ]
        )
    assert not target.exists()


def test_main_requires_local_copy_before_any_input_read(tmp_path, monkeypatch):
    def no_read(*args, **kwargs):
        pytest.fail(
            "missing local-copy refusal must happen before input reads"
        )

    monkeypatch.setattr(script.psid, "_resolve_data_dir", no_read)
    with pytest.raises(SystemExit) as error:
        script.main(["--out", str(tmp_path / "counts.json")])
    assert error.value.code == 2


@pytest.mark.parametrize("relative", [False, True])
def test_main_refuses_local_copy_inside_repository_before_read(
    relative, tmp_path, monkeypatch
):
    def no_read(*args, **kwargs):
        pytest.fail("local-copy refusal must happen before input reads")

    monkeypatch.setattr(script.psid, "_resolve_data_dir", no_read)
    # Isolate repository exclusion from the independent evidence-folder
    # guard, and stop before any attempt file can be created by a mutant.
    monkeypatch.setattr(script, "EVIDENCE_DIR", ROOT)
    monkeypatch.setattr(script, "_check_runtime", lambda: None)
    monkeypatch.setattr(script, "_start_attempt", no_read)
    local = Path("invented_private_counts.json")
    if not relative:
        local = ROOT / local
    with pytest.raises(SystemExit, match="outside.*repository"):
        script.main(
            [
                "--out",
                str(tmp_path / "counts.json"),
                "--local-copy",
                str(local),
            ]
        )
    assert not (ROOT / "invented_private_counts.json").exists()


def test_main_refuses_local_copy_through_repository_symlink_before_read(
    tmp_path, monkeypatch
):
    alias = tmp_path / "repository_alias"
    alias.symlink_to(ROOT, target_is_directory=True)

    def no_read(*args, **kwargs):
        pytest.fail("local-copy refusal must happen before input reads")

    monkeypatch.setattr(script.psid, "_resolve_data_dir", no_read)
    monkeypatch.setattr(script, "EVIDENCE_DIR", ROOT)
    monkeypatch.setattr(script, "_check_runtime", lambda: None)
    monkeypatch.setattr(script, "_start_attempt", no_read)
    with pytest.raises(SystemExit, match="outside.*repository"):
        script.main(
            [
                "--out",
                str(tmp_path / "counts.json"),
                "--local-copy",
                str(alias / "invented_private_counts.json"),
            ]
        )
    assert not (ROOT / "invented_private_counts.json").exists()


def test_main_refuses_to_overwrite_local_copy_before_read(
    tmp_path, monkeypatch
):
    local = tmp_path / "local.json"
    local.write_text("preserve local bytes")
    out = tmp_path / "counts.json"

    def no_read(*args, **kwargs):
        pytest.fail("local-copy refusal must happen before input reads")

    monkeypatch.setattr(script.psid, "_resolve_data_dir", no_read)
    with pytest.raises(SystemExit, match="refusing to overwrite"):
        script.main(["--out", str(out), "--local-copy", str(local)])
    assert local.read_text() == "preserve local bytes"
    assert not out.exists()


@pytest.mark.parametrize("target", ["out", "local"])
def test_main_refuses_dangling_output_symlinks_before_read(
    target, tmp_path, monkeypatch
):
    out = tmp_path / "counts.json"
    local = tmp_path / "local.json"
    guarded = out if target == "out" else local
    guarded.symlink_to(tmp_path / "absent.json")

    def no_read(*args, **kwargs):
        pytest.fail("symlink refusal must happen before input reads")

    monkeypatch.setattr(script.psid, "_resolve_data_dir", no_read)
    with pytest.raises(SystemExit, match="refusing to overwrite"):
        script.main(["--out", str(out), "--local-copy", str(local)])
    assert guarded.is_symlink()
    assert not (tmp_path / "absent.json").exists()


@pytest.fixture
def invented_main(tmp_path, monkeypatch):
    people, labor, anchor, design = _worked_rosters()
    allowlist = {"invented": {"variable": "X1", "label": "AGE"}}
    supplied = (people, _validity(labor), anchor, design, allowlist)
    input_root = tmp_path / "synthetic_inputs"
    calls = []

    def read_inputs(path):
        assert path == input_root
        calls.append(path)
        return supplied

    @contextmanager
    def record_files_read(path):
        assert path == input_root
        # Only a mocked audit record is supplied; no input file is opened.
        yield {"invented.txt": "a" * 64}

    monkeypatch.setattr(script, "read_inputs", read_inputs)
    monkeypatch.setattr(
        script, "_git", lambda *args: "" if args[0] == "status" else "b" * 40
    )
    monkeypatch.setattr(
        script.psid, "_resolve_data_dir", lambda arg: input_root
    )
    monkeypatch.setattr(
        script.psid2010, "record_files_read", record_files_read
    )
    baseline = tmp_path / "b01.json"
    baseline.write_text(json.dumps({"counts": {"domain_persons": 2}}))
    monkeypatch.setattr(script, "B0_1_COUNTS", baseline)
    monkeypatch.setattr(script, "EVIDENCE_DIR", tmp_path)
    protocol = tmp_path / "protocol.md"
    protocol.write_text(
        (ROOT / "docs/design/track_b_b0_2_protocol.md")
        .read_text()
        .replace("version 1, DRAFT,", "version 1, FROZEN,", 1)
    )
    monkeypatch.setattr(script, "PROTOCOL_PATH", protocol)
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        monkeypatch.setenv(name, "1")
    monkeypatch.setenv("OMP_WAIT_POLICY", "PASSIVE")
    return supplied, baseline, calls


def test_main_records_provenance_and_checks_b01_size(tmp_path, invented_main):
    supplied, baseline, calls = invented_main
    out = tmp_path / "counts.json"
    assert (
        script.main(
            ["--out", str(out), "--local-copy", str(tmp_path / "local.json")]
        )
        == 0
    )
    record = json.loads(out.read_text())
    assert len(calls) == 1
    assert record["schema"] == "track_b_b0_2_counts.v1"
    assert record["repository_head"] == "b" * 40
    assert record["worktree_clean"] is True
    assert (
        record["script_sha256"]
        == hashlib.sha256(Path(script.__file__).read_bytes()).hexdigest()
    )
    assert (
        record["b0_1_counts_sha256"]
        == hashlib.sha256(baseline.read_bytes()).hexdigest()
    )
    assert record["psid_files_opened_sha256"] == {"invented.txt": "a" * 64}
    assert record["requested_label_allowlist"] == supplied[-1]
    raw_counts = script.structural_counts(*supplied[:-1])
    registry = script.disclosure_registry(*supplied[:-1])
    coarsened, disclosure, local_audit = script.release_counts(
        raw_counts, registry
    )
    assert record["counts"] == coarsened
    assert record["disclosure"] == disclosure
    assert disclosure["base"] in (10, 50, 100, 500)
    assert disclosure["attempts"][-1]["failed"] == 0
    assert "disclosure_audit" not in record
    local_record = json.loads((tmp_path / "local.json").read_text())
    assert local_record["counts"] == raw_counts
    assert local_record["disclosure_audit"] == local_audit
    assert local_record["repository_head"] == record["repository_head"]
    assert record["geometry"]["collection_waves"] == list(WAVES)
    assert record["geometry"]["reference_years"] == [
        wave - 1 for wave in WAVES
    ]
    assert record["geometry"]["age_convention"] == "collection_wave"
    assert record["geometry"]["lag_years"] == [2, 4]
    _assert_no_forbidden_output(record)


def test_main_allows_relative_local_copy_resolving_outside_repository(
    tmp_path, invented_main
):
    out = tmp_path / "counts.json"
    local = tmp_path / "local.json"
    relative_local = os.path.relpath(local, ROOT)
    assert not (ROOT / relative_local).resolve().is_relative_to(ROOT)
    assert (
        script.main(["--out", str(out), "--local-copy", relative_local]) == 0
    )
    assert out.exists()
    assert local.exists()
    assert json.loads(local.read_text())["counts"] == script.structural_counts(
        *invented_main[0][:-1]
    )


def test_main_rejects_b01_size_mismatch(tmp_path, invented_main):
    _, baseline, _ = invented_main
    baseline.write_text(json.dumps({"counts": {"domain_persons": 99}}))
    out = tmp_path / "counts.json"
    with pytest.raises(AssertionError, match="R_B2 size differs"):
        script.main(
            ["--out", str(out), "--local-copy", str(tmp_path / "local.json")]
        )
    assert not out.exists()


def test_main_uses_exclusive_open_if_output_appears_during_read(
    tmp_path, monkeypatch, invented_main
):
    supplied, _, _ = invented_main
    out = tmp_path / "counts.json"

    def racing_read(path):
        out.write_text("preserve these bytes")
        return supplied

    monkeypatch.setattr(script, "read_inputs", racing_read)
    with pytest.raises(FileExistsError):
        script.main(
            ["--out", str(out), "--local-copy", str(tmp_path / "local.json")]
        )
    assert out.read_text() == "preserve these bytes"


def test_main_uses_exclusive_open_if_local_copy_appears_during_read(
    tmp_path, monkeypatch, invented_main
):
    supplied, _, _ = invented_main
    out = tmp_path / "counts.json"
    local = tmp_path / "local.json"

    def racing_read(path):
        local.write_text("preserve local race bytes")
        return supplied

    monkeypatch.setattr(script, "read_inputs", racing_read)
    with pytest.raises(FileExistsError):
        script.main(["--out", str(out), "--local-copy", str(local)])
    assert local.read_text() == "preserve local race bytes"
    assert not out.exists()


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("OMP_NUM_THREADS", "0"),
        ("OMP_NUM_THREADS", "5"),
        ("OPENBLAS_NUM_THREADS", "invalid"),
        ("OMP_WAIT_POLICY", "ACTIVE"),
    ],
)
def test_runtime_rejects_thread_settings_before_read(
    name, value, tmp_path, monkeypatch, invented_main
):
    _, _, calls = invented_main
    monkeypatch.setenv(name, value)
    with pytest.raises(SystemExit, match=f"set {name}"):
        script.main(
            [
                "--out",
                str(tmp_path / "counts.json"),
                "--local-copy",
                str(tmp_path / "local.json"),
            ]
        )
    assert not calls


def test_runtime_rejects_dirty_worktree_before_read(
    tmp_path, monkeypatch, invented_main
):
    _, _, calls = invented_main
    monkeypatch.setattr(script, "_git", lambda *args: " M invented.py")
    with pytest.raises(SystemExit, match="clean protocol-freezing worktree"):
        script.main(
            [
                "--out",
                str(tmp_path / "counts.json"),
                "--local-copy",
                str(tmp_path / "local.json"),
            ]
        )
    assert not calls


@pytest.mark.parametrize("failure", ["draft", "pin"])
def test_main_requires_frozen_pinned_protocol_before_any_input(
    failure, tmp_path, monkeypatch, invented_main
):
    _, _, calls = invented_main
    text = script.PROTOCOL_PATH.read_text()
    if failure == "draft":
        text = text.replace("version 1, FROZEN,", "version 1, DRAFT,", 1)
        message = "FROZEN"
    else:
        text = text.replace("### Scope", "### Revised scope", 1)
        message = "SHA-256"
    script.PROTOCOL_PATH.write_text(text)
    with pytest.raises(SystemExit, match=message):
        script.main(
            [
                "--out",
                str(tmp_path / "counts.json"),
                "--local-copy",
                str(tmp_path / "local.json"),
            ]
        )
    assert not calls
    assert not script._attempt_path(tmp_path / "local.json").exists()


def test_attempt_record_survives_failed_start_and_refuses_retry(
    tmp_path, monkeypatch, invented_main
):
    _, _, calls = invented_main
    local = tmp_path / "local.json"
    out = tmp_path / "counts.json"
    attempted = []

    def failed_resolve(_):
        record = json.loads(script._attempt_path(local).read_text())
        attempted.append(record)
        assert record["repository_head"] == "b" * 40
        assert (
            record["script_sha256"]
            == hashlib.sha256(Path(script.__file__).read_bytes()).hexdigest()
        )
        from datetime import datetime

        assert (
            datetime.fromisoformat(record["started_at"])
            .utcoffset()
            .total_seconds()
            == 0
        )
        raise RuntimeError("invented pre-read failure")

    monkeypatch.setattr(script.psid, "_resolve_data_dir", failed_resolve)
    with pytest.raises(RuntimeError, match="invented pre-read failure"):
        script.main(["--out", str(out), "--local-copy", str(local)])
    assert len(attempted) == 1
    assert not calls and not out.exists() and not local.exists()
    with pytest.raises(SystemExit, match="attempt record"):
        script.main(
            [
                "--out",
                str(out),
                "--local-copy",
                str(tmp_path / "other-local.json"),
            ]
        )
    assert len(attempted) == 1


def test_main_refuses_attempt_record_through_existing_symlink(
    tmp_path, invented_main
):
    local = tmp_path / "local.json"
    attempt = script._attempt_path(local)
    attempt.symlink_to(tmp_path / "absent-attempt.json")
    with pytest.raises(SystemExit, match="attempt record"):
        script.main(
            [
                "--out",
                str(tmp_path / "counts.json"),
                "--local-copy",
                str(local),
            ]
        )
    assert attempt.is_symlink()
    assert not (tmp_path / "absent-attempt.json").exists()


def test_main_refuses_local_copy_outside_fixed_evidence_folder(
    tmp_path, invented_main
):
    _, _, calls = invented_main
    local = tmp_path / "other-folder" / "local.json"
    with pytest.raises(SystemExit, match="B0.2 evidence folder"):
        script.main(
            [
                "--out",
                str(tmp_path / "counts.json"),
                "--local-copy",
                str(local),
            ]
        )
    assert not calls and not local.exists()


def test_main_failed_disclosure_writes_only_disclosure_block(
    tmp_path, monkeypatch, invented_main
):
    disclosure = {
        "base": None,
        "coarsening_rule": "fixture",
        "protection_rule": "fixture",
        "attempts": [
            {"base": base, "audited": 1, "failed": 1}
            for base in (10, 50, 100, 500)
        ],
    }
    monkeypatch.setattr(
        script,
        "release_counts",
        lambda counts, registry: ({}, disclosure, {"audits": []}),
    )
    out = tmp_path / "counts.json"
    local = tmp_path / "local.json"
    assert script.main(["--out", str(out), "--local-copy", str(local)]) == 0
    assert json.loads(out.read_text()) == {"disclosure": disclosure}
    assert json.loads(local.read_text())["counts"] == script.structural_counts(
        *invented_main[0][:-1]
    )


def test_module_stays_in_unit_tier(tier_policy_collection):
    own = [
        markers
        for node, markers in tier_policy_collection["items"]
        if node.startswith("tests/test_track_b_b0_2_counts.py::")
    ]
    assert own and all(markers == ("unit",) for markers in own)


_READER_CONCEPTS = {
    "age": (r"^AGE OF INDIVIDUAL",),
    "sequence": (r"^SEQUENCE NUMBER",),
    "relationship": (r"^RELATION(SHIP)? TO (HEAD|REFERENCE PERSON)",),
    "weight": (
        r"^INDIVIDUAL WEIGHT|CROSS-SECTION WT",
        r"^CORE IND WEIGHT",
        r"LONGITUDINAL W",
    ),
    "interview": (r"INTERVIEW NUMBER",),
}

_READER_ACCURACY = {
    1999: {
        "head": (("ER16464", "ACC LABOR INCOME-HD"),),
        "spouse": (("ER16466", "ACC LABOR INCOME-WF"),),
    },
    2001: {
        "head": (
            ("ER20426", "ACC WAGES AND SALARIES OF HEAD-2000"),
            ("ER20440", "ACC MISC LABOR INCOME OF HEAD-2000"),
        ),
        "spouse": (("ER20448", "ACC LABOR INCOME OF WIFE-2000"),),
    },
    2003: {
        "head": (
            ("ER24118", "ACC WAGES AND SALARIES OF HEAD LAST YEAR"),
            ("ER24134", "ACC MISC LABOR INCOME OF HEAD LAST YEAR"),
        ),
        "spouse": (("ER24136", "ACC LABOR INCOME OF WIFE LAST YEAR"),),
    },
    2005: {
        "head": (
            ("ER27914", "ACC WAGES AND SALARIES OF HEAD-2004"),
            ("ER27930", "ACC MISC LABOR INCOME OF HEAD-2004"),
        ),
        "spouse": (("ER27944", "ACC LABOR INCOME OF WIFE-2004"),),
    },
    2007: {
        "head": (
            ("ER40904", "ACC WAGES AND SALARIES OF HEAD-2006"),
            ("ER40920", "ACC MISC LABOR INCOME OF HEAD-2006"),
        ),
        "spouse": (("ER40934", "ACC LABOR INCOME OF WIFE-2006"),),
    },
    2009: {
        "head": (
            ("ER46812", "ACC WAGES AND SALARIES OF HEAD-2008"),
            ("ER46828", "ACC MISC LABOR INCOME OF HEAD-2008"),
        ),
        "spouse": (("ER46842", "ACC LABOR INCOME OF WIFE-2008"),),
    },
    2011: {
        "head": (
            ("ER52220", "ACC WAGES AND SALARIES OF HEAD-2010"),
            ("ER52236", "ACC MISC LABOR INCOME OF HEAD-2010"),
        ),
        "spouse": (("ER52250", "ACC LABOR INCOME OF WIFE-2010"),),
    },
    2013: {
        "head": (
            ("ER58021", "ACC WAGES AND SALARIES OF HEAD-2012"),
            ("ER58037", "ACC MISC LABOR INCOME OF HEAD-2012"),
        ),
        "spouse": (("ER58051", "ACC LABOR INCOME OF WIFE-2012"),),
    },
    2015: {
        "head": (
            ("ER65201", "ACC WAGES AND SALARIES OF HEAD-2014"),
            ("ER65215", "ACC MISC LABOR INCOME OF HEAD-2014"),
        ),
        "spouse": (
            ("ER65229", "ACC WAGES AND SALARIES OF SPOUSE-2014"),
            ("ER65243", "ACC MISC LABOR INCOME OF SPOUSE-2014"),
        ),
    },
    2017: {
        "head": (
            ("ER71278", "ACC WAGES AND SALARIES OF RP-2016"),
            ("ER71292", "ACC MISC LABOR INCOME OF RP-2016"),
        ),
        "spouse": (
            ("ER71306", "ACC WAGES AND SALARIES OF SPOUSE-2016"),
            ("ER71320", "ACC MISC LABOR INCOME OF SPOUSE-2016"),
        ),
    },
    2019: {
        "head": (
            ("ER77300", "ACC WAGES AND SALARIES OF RP-2018"),
            ("ER77314", "ACC MISC LABOR INCOME OF RP-2018"),
        ),
        "spouse": (
            ("ER77328", "ACC WAGES AND SALARIES OF SPOUSE-2018"),
            ("ER77342", "ACC MISC LABOR INCOME OF SPOUSE-2018"),
        ),
    },
    2021: {
        "head": (
            ("ER81627", "ACC WAGES AND SALARIES OF RP-2020"),
            ("ER81641", "ACC MISC LABOR INCOME OF RP-2020"),
        ),
        "spouse": (
            ("ER81655", "ACC WAGES AND SALARIES OF SPOUSE-2020"),
            ("ER81669", "ACC MISC LABOR INCOME OF SPOUSE-2020"),
        ),
    },
    2023: {
        "head": (
            ("ER85481", "ACC WAGES AND SALARIES OF RP-2022"),
            ("ER85495", "ACC MISC LABOR INCOME OF RP-2022"),
        ),
        "spouse": (
            ("ER85509", "ACC WAGES AND SALARIES OF SPOUSE-2022"),
            ("ER85523", "ACC MISC LABOR INCOME OF SPOUSE-2022"),
        ),
    },
}


def _reader_metadata():
    """Invent totals/demographics; pin source-defined identities/accuracy."""
    identifiers = {
        "interview_1968": {
            "variable": "ER30001",
            "label": "1968 INTERVIEW NUMBER",
        },
        "person_number": {"variable": "ER30002", "label": "PERSON NUMBER 68"},
    }
    anchor = {
        **identifiers,
        "interview": {"variable": "ER34101", "label": "2011 INTERVIEW NUMBER"},
        "sequence": {"variable": "ER34102", "label": "SEQUENCE NUMBER 11"},
        "relationship": {
            "variable": "ER34103",
            "label": "RELATION TO HEAD 11",
        },
        "age": {"variable": "ER34104", "label": "AGE OF INDIVIDUAL 11"},
        "reported_birth_year": {
            "variable": "ER34106",
            "label": "YEAR INDIVIDUAL BORN 11",
        },
        "weight": {
            "variable": "ER34155",
            "label": "CORE/IMM INDIVIDUAL CROSS-SECTION WT 11",
        },
    }
    design = {
        **identifiers,
        "stratum": {"variable": "ER31996", "label": "SAMPLING ERROR STRATUM"},
        "cluster": {"variable": "ER31997", "label": "SAMPLING ERROR CLUSTER"},
    }
    labels = {
        entry["variable"]: entry["label"]
        for entry in [*anchor.values(), *design.values()]
    }
    by_wave = {}
    stems = {
        "age": "AGE OF INDIVIDUAL",
        "sequence": "SEQUENCE NUMBER",
        "relationship": "RELATION TO HEAD",
        "weight": "INDIVIDUAL WEIGHT",
        "interview": "INTERVIEW NUMBER",
    }
    for wave in range(1999, 2024, 2):
        by_wave[str(wave)] = {}
        for concept, stem in stems.items():
            if wave == 2011:
                entry = anchor[concept]
            else:
                entry = {
                    "variable": f"INVENTED_{concept}_{wave}",
                    "label": (
                        f"{wave} {stem}"
                        if concept == "interview"
                        else f"{stem} {wave % 100:02d}"
                    ),
                }
            by_wave[str(wave)][concept] = entry
            labels[entry["variable"]] = entry["label"]
    labels["FORBIDDEN_INDIVIDUAL"] = "MARITAL STATUS 11"
    family_labels = {}
    families = {}
    for wave in range(1999, 2024, 2):
        entries = {
            "interview": {
                "variable": f"INVENTED_INTERVIEW_{wave}",
                "label": f"{wave} FAMILY INTERVIEW (ID) NUMBER",
            },
            "head_labor": {
                "variable": f"INVENTED_HEAD_{wave}",
                "label": f"LABOR INCOME OF HEAD-{wave - 1}",
            },
            "spouse_labor": {
                "variable": f"INVENTED_SPOUSE_{wave}",
                "label": f"LABOR INCOME OF WIFE-{wave - 1}",
            },
            "head_accuracy": [
                {"variable": var, "label": label}
                for var, label in _READER_ACCURACY[wave]["head"]
            ],
            "spouse_accuracy": [
                {"variable": var, "label": label}
                for var, label in _READER_ACCURACY[wave]["spouse"]
            ],
        }
        families[str(wave)] = entries
        flat = [
            entries["interview"],
            entries["head_labor"],
            entries["spouse_labor"],
            *entries["head_accuracy"],
            *entries["spouse_accuracy"],
        ]
        family_labels[wave] = {
            entry["variable"]: entry["label"] for entry in flat
        }
        family_labels[wave]["FORBIDDEN_FAMILY"] = "SOCIAL SECURITY AMOUNT"
    expected = {
        "individual": {
            "identifiers": identifiers,
            "concepts": {
                name: list(patterns)
                for name, patterns in _READER_CONCEPTS.items()
            },
            "by_wave": by_wave,
        },
        "anchor_2011": anchor,
        "design": design,
        "family": families,
    }
    return labels, family_labels, expected


def test_readers_request_the_pinned_allowlist(monkeypatch, tmp_path):
    """Exercise the named readers with mocked metadata and fixed-width IO."""
    import hashlib
    import json

    labels, family_labels, expected = _reader_metadata()
    waves = list(range(1999, 2024, 2))
    source_dir = tmp_path / "invented_survey"
    calls = []
    low_level = []
    family_reads = []
    by_wave = expected["individual"]["by_wave"]

    def resolve(data_dir):
        assert data_dir == source_dir
        return source_dir

    def parse_labels(path):
        if path.name == "IND2023ER.sps":
            return labels.copy()
        return family_labels[int(path.parent.name)].copy()

    def family_paths(wave, data_dir):
        assert data_dir == source_dir
        base = source_dir / "family" / str(wave)
        return base / "invented.sps", base / "invented.txt"

    def parse_layout(path):
        names = list(family_labels[int(path.parent.name)])
        return pd.DataFrame(
            {
                "name": names,
                "start": range(1, len(names) + 1),
                "end": range(1, len(names) + 1),
            }
        )

    individual_values = {
        "ER30001": 1,
        "ER30002": 1,
        "ER34106": 1950,
        "ER31996": 5,
        "ER31997": 7,
    }
    values = {
        "age": 62,
        "sequence": 1,
        "relationship": 10,
        "weight": 2,
        "interview": 1,
    }
    for entries in by_wave.values():
        for concept, entry in entries.items():
            individual_values[entry["variable"]] = values[concept]

    def read_psid(product, *, columns, data_dir, nrows):
        assert product == "ind2023er"
        assert data_dir == source_dir
        assert nrows is None
        low_level.append(columns)
        return pd.DataFrame(
            {name: [individual_values[name]] for name in columns}
        )

    def read_fwf(path, *, colspecs, names, header, nrows):
        wave = int(path.parent.name)
        assert header is None
        assert nrows is None
        assert colspecs == [(i, i + 1) for i in range(len(names))]
        family_reads.append((wave, names))
        return pd.DataFrame({name: [1] for name in names})

    original_panel = script.panels.ind_person_period
    original_anchor = script.psid2010.read_anchor_wave
    original_design = script.age67.read_design_variables
    original_family = script.family.read_family_labor

    def read_panel(concepts, **kwargs):
        calls.append(("panel", concepts, kwargs))
        return original_panel(concepts, **kwargs)

    def read_anchor(**kwargs):
        calls.append(("anchor", kwargs))
        return original_anchor(**kwargs)

    def read_design(**kwargs):
        calls.append(("design", kwargs))
        return original_design(**kwargs)

    def read_family(wave, **kwargs):
        calls.append(("family", wave, kwargs))
        return original_family(wave, **kwargs)

    monkeypatch.setattr(script.psid, "_resolve_data_dir", resolve)
    monkeypatch.setattr(script.psid, "parse_sps_labels", parse_labels)
    monkeypatch.setattr(script.psid, "parse_sps_layout", parse_layout)
    monkeypatch.setattr(script.psid, "read_psid", read_psid)
    monkeypatch.setattr(script.family, "_family_paths", family_paths)
    monkeypatch.setattr(pd, "read_fwf", read_fwf)
    monkeypatch.setattr(script.panels, "ind_person_period", read_panel)
    monkeypatch.setattr(script.psid2010, "read_anchor_wave", read_anchor)
    monkeypatch.setattr(script.age67, "read_design_variables", read_design)
    monkeypatch.setattr(script.family, "read_family_labor", read_family)

    person_wave, validity, anchor, design, allowlist = script.read_inputs(
        source_dir
    )
    assert calls == [
        ("panel", _READER_CONCEPTS, {"data_dir": source_dir, "waves": waves}),
        ("anchor", {"data_dir": source_dir, "anchor_wave": 2011}),
        ("design", {"data_dir": source_dir}),
        *[("family", wave, {"data_dir": source_dir}) for wave in waves],
    ]
    assert low_level == [
        ["ER30001", "ER30002"]
        + [
            by_wave[str(wave)][concept]["variable"]
            for wave in waves
            for concept in _READER_CONCEPTS
        ],
        [
            "ER30001",
            "ER30002",
            "ER34101",
            "ER34102",
            "ER34103",
            "ER34104",
            "ER34106",
            "ER34155",
        ],
        ["ER30001", "ER30002", "ER31996", "ER31997"],
    ]
    assert family_reads == [
        (
            wave,
            [
                name
                for name in family_labels[wave]
                if name != "FORBIDDEN_FAMILY"
            ],
        )
        for wave in waves
    ]
    assert allowlist == expected
    _assert_no_forbidden_output(allowlist)
    encoded = json.dumps(
        allowlist, sort_keys=True, separators=(",", ":")
    ).encode()
    assert hashlib.sha256(encoded).hexdigest() == (
        "04b0d7683e935a8a841dea9e866a228ef643aa6e799bcff47f1ed16d20bf9425"
    )
    assert person_wave["period"].tolist() == waves
    assert set(validity) == set(waves)
    assert "reported_birth_year" not in anchor.columns
    assert anchor["person_id"].tolist() == [1001]
    assert design.to_dict("records") == [
        {"person_id": 1001, "stratum": 5, "cluster": 7}
    ]
    for frame in validity.values():
        assert frame.columns.tolist() == [
            "interview",
            "head_valid",
            "spouse_valid",
            "head_acc_flag",
            "spouse_acc_flag",
        ]
        assert frame.iloc[0].tolist() == [1, True, True, True, True]


def _write_invented_product(directory, labels, rows, stem):
    """Generate fixed-width bytes and matching labels solely from fixtures."""
    directory.mkdir(parents=True, exist_ok=True)
    names = list(labels)
    width = 12
    layout = "\n".join(
        f"{name} {i * width + 1} - {(i + 1) * width}"
        for i, name in enumerate(names)
    )
    variables = "\n".join(f'{name} "{labels[name]}"' for name in names)
    (directory / f"{stem}.sps").write_text(
        "DATA LIST FILE = INVENTED /\n"
        + layout
        + "\n.\nVARIABLE LABELS\n"
        + variables
        + "\n.\n"
    )
    (directory / f"{stem}.txt").write_text(
        "\n".join(
            "".join(str(row.get(name, 0)).rjust(width) for name in names)
            for row in rows
        )
        + "\n"
    )


def test_missing_999_and_zero_ages_through_actual_named_readers(tmp_path):
    labels, family_labels, expected = _reader_metadata()
    source = tmp_path / "invented_reader_inputs"
    ages = [999, 0, 29, 80, 81, 125]
    rows = []
    for person, age in enumerate(ages, 1):
        row = {
            "ER30001": 1,
            "ER30002": person,
            "ER34106": 1950,
            "ER31996": 5,
            "ER31997": 7,
            "FORBIDDEN_INDIVIDUAL": 999,
        }
        for entries in expected["individual"]["by_wave"].values():
            values = {
                "age": age,
                "sequence": 1,
                "relationship": 10,
                "weight": 2,
                "interview": person,
            }
            row.update(
                {
                    entry["variable"]: values[concept]
                    for concept, entry in entries.items()
                }
            )
        rows.append(row)
    _write_invented_product(source / "ind2023er", labels, rows, "IND2023ER")
    for wave in WAVES:
        entries = expected["family"][str(wave)]
        records = []
        for person in range(1, len(ages) + 1):
            record = {
                entries["interview"]["variable"]: person,
                entries["head_labor"]["variable"]: 0,
                entries["spouse_labor"]["variable"]: 0,
                "FORBIDDEN_FAMILY": 999,
            }
            record.update(
                {
                    entry["variable"]: 0
                    for entry in entries["head_accuracy"]
                    + entries["spouse_accuracy"]
                }
            )
            records.append(record)
        _write_invented_product(
            source / "family" / str(wave),
            family_labels[wave],
            records,
            "INVENTED",
        )
    people, validity, anchor, design, _ = script.read_inputs(source)
    assert anchor["age"].tolist() == ages
    counts = script.structural_counts(people, validity, anchor, design)
    for section in (counts["rosters"], counts["b3l"]["rosters"]):
        for roster in section.values():
            expected_unknown = (
                0 if roster is counts["rosters"]["R_TA_PROXY"] else 2
            )
            assert roster["unknown_age"]["persons"] == expected_unknown
            assert roster["by_age_band"]["80_plus"]["persons"] == 3
            assert (
                sum(item["persons"] for item in roster["by_age_band"].values())
                + roster["unknown_age"]["persons"]
                == roster["overall"]["persons"]
            )
    assert counts["rosters"]["R_TA_PROXY"]["overall"]["persons"] == 3
    registry = script.disclosure_registry(people, validity, anchor, design)
    unknown = ("rosters", "R_FULL", "unknown_age", "persons")
    old = ("rosters", "R_FULL", "by_age_band", "80_plus", "persons")
    assert registry.sets[unknown][1] == {1001, 1002}
    assert registry.sets[unknown][1].isdisjoint(registry.sets[old][1])
    published, _, private = script.release_counts(counts, registry)
    assert published and private["audits"][-1]["failed"] == 0
