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
    "94e22e3fff7b8ec541f87abe9890270a9893e0ec1653ce7b91fb0170b2732cb9"
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
        "kish_n_eff": 4.091,
        "household_cluster_worst_n_eff": 2.922,
        "design_cluster_worst_n_eff": 2.711,
    }
    assert {
        band: count["persons"] for band, count in full["by_age_band"].items()
    } == {
        "0_24": 0,
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
    assert proxy["overall"]["kish_n_eff"] == 2.711
    assert proxy["overall"]["household_cluster_worst_n_eff"] == 1.8
    assert proxy["by_age_band"]["25_44"]["persons"] == 1
    assert proxy["by_age_band"]["62_64"]["persons"] == 0
    assert proxy["by_age_band"]["65_66"]["persons"] == 1


def test_band_edges_and_b3_support_are_hand_counted():
    ages = [0, 24, 25, 44, 45, 61, 62, 64, 65, 66, 67, 69, 70, 79, 80]
    people, labor, anchor, design = _inputs(
        [_row(i, age=age) for i, age in enumerate(ages, 1)],
        accuracy={(2011, 7, "head"), (2011, 9, "head")},
    )
    counts = script.structural_counts(people, _validity(labor), anchor, design)
    roster_bands = counts["rosters"]["R_FULL"]["by_age_band"]
    assert {key: value["persons"] for key, value in roster_bands.items()} == {
        "0_24": 2,
        "25_44": 2,
        "45_61": 2,
        "62_64": 2,
        "65_66": 2,
        "67_69": 2,
        "70_79": 2,
        "80_plus": 1,
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
        "kish_n_eff": 1.976,
        "household_cluster_worst_n_eff": 1.976,
        "design_cluster_worst_n_eff": 1.976,
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
    assert full["design_cluster_worst_n_eff"] == round(225 / 83, 3)


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


# --------------------------------------------------------------------------
# Disclosure, using invented counts and structural frames only
# --------------------------------------------------------------------------
@pytest.mark.parametrize("count", range(11))
def test_disclosure_suppresses_counts_one_through_nine(count):
    raw = {"table": {"persons": count}}
    published, disclosure = script.suppress_counts(raw)
    expected = "<10" if 1 <= count <= 9 else count
    assert published == {"table": {"persons": expected}}
    assert raw == {"table": {"persons": count}}
    assert disclosure["threshold"] == 10
    assert disclosure["primary_suppressed"] == int(1 <= count <= 9)
    assert disclosure["complementary_suppressed"] == 0
    assert not any(disclosure["complementary_passes"])


@pytest.mark.parametrize("support", ["persons", "valid_rows"])
@pytest.mark.parametrize("effective_size", [0.0, 8.125, 12.0])
def test_disclosure_suppresses_effective_sizes_on_small_nonempty_sets(
    support, effective_size
):
    raw = {
        "table": {
            support: 9,
            "kish_n_eff": effective_size,
            "household_cluster_worst_n_eff": effective_size,
            "design_cluster_worst_n_eff": effective_size,
        }
    }
    published, disclosure = script.suppress_counts(raw)
    assert all(value == "<10" for value in published["table"].values())
    assert disclosure["primary_suppressed"] == 4
    assert raw["table"][support] == 9
    assert raw["table"]["kish_n_eff"] == effective_size


def test_disclosure_keeps_empty_effective_sizes_and_suppresses_small_values():
    published, _ = script.suppress_counts(
        {
            "empty": {"persons": 0, "kish_n_eff": 0.0},
            "large": {"persons": 10, "kish_n_eff": 10.0},
            "unequal_weights": {"persons": 20, "kish_n_eff": 9.001},
            "origin_wave": 2007,
        }
    )
    assert published == {
        "empty": {"persons": 0, "kish_n_eff": 0.0},
        "large": {"persons": 10, "kish_n_eff": 10.0},
        "unequal_weights": {"persons": 20, "kish_n_eff": "<10"},
        "origin_wave": 2007,
    }


def test_disclosure_complements_the_smallest_remaining_published_part():
    raw = {"total": 40, "small": 5, "larger": 20, "smallest": 15}
    relations = [(("total",), (("small",), ("larger",), ("smallest",)))]
    published, disclosure = script.suppress_counts(raw, relations)
    assert published == {
        "total": 40,
        "small": "<10",
        "larger": 20,
        "smallest": "<10",
    }
    assert disclosure["primary_suppressed"] == 1
    assert disclosure["complementary_suppressed"] == 1
    assert sum(disclosure["complementary_passes"]) == 1
    assert raw["smallest"] == 15


def test_disclosure_repeats_complementary_passes_until_chain_is_safe():
    raw = {
        "outer_total": 60,
        "inner_total": 30,
        "small": 5,
        "shared": 25,
        "other": 35,
    }
    # Outer is visited before the inner relation hides its shared part.
    relations = [
        (("outer_total",), (("shared",), ("other",))),
        (("inner_total",), (("small",), ("shared",))),
    ]
    published, disclosure = script.suppress_counts(raw, relations)
    assert published == {
        "outer_total": 60,
        "inner_total": 30,
        "small": "<10",
        "shared": "<10",
        "other": "<10",
    }
    assert disclosure["complementary_suppressed"] == 2
    assert len([n for n in disclosure["complementary_passes"] if n]) >= 2
    assert sum(disclosure["complementary_passes"]) == 2


def test_disclosure_hides_effective_sizes_when_support_is_complemented():
    raw = {
        "total": 25,
        "small": {"persons": 5, "kish_n_eff": 5.0},
        "large": {"persons": 20, "kish_n_eff": 20.0},
    }
    relations = [(("total",), (("small", "persons"), ("large", "persons")))]
    published, _ = script.suppress_counts(raw, relations)
    assert published["small"] == {"persons": "<10", "kish_n_eff": "<10"}
    assert published["large"] == {"persons": "<10", "kish_n_eff": "<10"}


def _path_value(value, path):
    for key in path:
        value = value[key]
    return value


def test_disclosure_relations_are_exact_structural_identities():
    from collections.abc import Mapping

    inputs = _worked_rosters()
    people, labor, anchor, design = inputs
    validity = _validity(labor)
    counts = _counts(inputs)
    relations = script.disclosure_relations(people, validity, anchor, design)
    assert relations
    for relation in relations:
        if isinstance(relation, Mapping):
            assert (
                sum(
                    coefficient * _path_value(counts, path)
                    for path, coefficient in relation.items()
                )
                == 0
            )
        else:
            total, parts = relation
            assert _path_value(counts, total) == sum(
                _path_value(counts, path) for path in parts
            )
    expected = (
        ("rosters", "R_FULL", "overall", "persons"),
        tuple(
            ("rosters", "R_FULL", "by_age_band", band, "persons")
            for band, _, _ in script.ROSTER_BANDS
        ),
    )
    assert expected in relations


def test_disclosure_published_counts_have_no_positive_value_below_ten():
    people, labor, anchor, design = _invariance_inputs()
    validity = _validity(labor)
    raw = script.structural_counts(people, validity, anchor, design)
    relations = script.disclosure_relations(people, validity, anchor, design)
    published, _ = script.suppress_counts(raw, relations)

    def check(value, path=()):
        if isinstance(value, dict):
            for key, item in value.items():
                check(item, (*path, key))
        elif isinstance(value, (int, float)) and path[-1] != "origin_wave":
            assert value == 0 or value >= 10, (path, value)

    check(published)


def test_disclosure_closes_recovery_from_coupled_equations():
    raw = {"a": 5, "b": 5, "c": 6, "ab": 10, "bc": 11, "ac": 11}
    relations = [
        (("ab",), (("a",), ("b",))),
        (("bc",), (("b",), ("c",))),
        (("ac",), (("a",), ("c",))),
    ]
    primary, _ = script.suppress_counts(raw)
    primary_hidden = {
        (name,) for name, value in primary.items() if value == "<10"
    }
    equations = [script._equation(relation) for relation in relations]
    assert all(len(primary_hidden.intersection(eq)) == 2 for eq in equations)
    # Each pair hides two cells, but together the three equations solve a,b,c.
    assert set(script._recoverable(equations, primary_hidden)) == {
        ("a",),
        ("b",),
        ("c",),
    }
    published, disclosure = script.suppress_counts(raw, relations)
    assert published["ab"] == "<10"
    assert published["bc"] == published["ac"] == 11
    assert disclosure["complementary_suppressed"] == 1
    hidden = {(name,) for name, value in published.items() if value == "<10"}
    assert not script._recoverable(equations, hidden)
    # Independently check every hidden coordinate remains underdetermined.
    columns = sorted(hidden)
    matrix = np.array(
        [[float(eq.get(path, 0)) for path in columns] for eq in equations]
    )
    rank = np.linalg.matrix_rank(matrix)
    for column in range(len(columns)):
        assert np.linalg.matrix_rank(np.delete(matrix, column, axis=1)) == rank


def test_disclosure_handles_overlapping_wave_pool_and_lag_intersection():
    # Five persons are in both waves; ten more occur only in each wave.
    inputs = _inputs(
        [
            *[_row(person, 2011, age=62) for person in range(1, 16)],
            *[
                _row(person, 2013, age=64)
                for person in [*range(1, 6), *range(16, 26)]
            ],
        ]
    )
    people, labor, anchor, design = inputs
    validity = _validity(labor)
    raw = _counts(inputs)
    relations = script.disclosure_relations(people, validity, anchor, design)
    first = ("b3", "by_wave", "2011", "62_64", "persons")
    second = ("b3", "by_wave", "2013", "62_64", "persons")
    pooled = ("b3", "distinct_persons_by_band", "62_64")
    overlap = ("b3", "lag_pairs", "2", "2011_2013", "62_64")
    assert [
        _path_value(raw, path) for path in (first, second, pooled, overlap)
    ] == [15, 15, 25, 5]
    # A distinct-person union must not be treated as a sum of overlapping waves.
    incorrect_addition = (
        pooled,
        tuple(
            ("b3", "by_wave", str(wave), "62_64", "persons") for wave in WAVES
        ),
    )
    assert incorrect_addition not in relations
    equations = [script._equation(relation) for relation in relations]

    def hidden_paths(value, prefix=()):
        if isinstance(value, dict):
            return set().union(
                *(
                    hidden_paths(item, (*prefix, key))
                    for key, item in value.items()
                )
            )
        return {prefix} if value == "<10" else set()

    primary, _ = script.suppress_counts(raw)
    # Wave1 + wave2 - pooled would otherwise recover the hidden overlap.
    assert overlap in script._recoverable(equations, hidden_paths(primary))
    published, _ = script.suppress_counts(raw, relations)
    assert _path_value(published, overlap) == "<10"
    assert any(
        _path_value(published, path) == "<10"
        for path in (first, second, pooled)
    )
    assert not script._recoverable(equations, hidden_paths(published))


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
    relations = script.disclosure_relations(*supplied[:-1])
    suppressed, disclosure = script.suppress_counts(raw_counts, relations)
    assert record["counts"] == suppressed
    assert record["disclosure"] == disclosure
    assert disclosure["threshold"] == 10
    assert isinstance(disclosure["rule"], str) and disclosure["rule"]
    assert disclosure["primary_suppressed"] > 0
    assert disclosure["complementary_suppressed"] >= 0
    assert (
        sum(disclosure["complementary_passes"])
        == disclosure["complementary_suppressed"]
    )
    local_record = json.loads((tmp_path / "local.json").read_text())
    assert local_record["counts"] == raw_counts
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
