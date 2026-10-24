"""B0.2's version-1 protocol, tested solely on invented frames."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from contextlib import contextmanager
from itertools import combinations
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from hypothesis import event, example, given, settings
from hypothesis import strategies as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import track_b_b0_2_counts as script  # noqa: E402

from scripts import track_b_b0_1_counts as b01  # noqa: E402

PROTOCOL_SHA256 = (
    "e9a39f445c8674ac3e0298239d2f8b5473c148495bb24d82870b9a3d70c799b6"
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
    # 62.5 is an interior fraction: unknown, not in a band (review 2).
    ages = [0, 999, -1, 125.5, 62.5, 126, float("nan"), 1, 24, 80, 81, 125]
    counts = _counts(
        _inputs([_row(i, age=age) for i, age in enumerate(ages, 1)])
    )
    roster = counts["rosters"]["R_FULL"]
    assert roster["overall"]["persons"] == 12
    assert roster["unknown_age"]["persons"] == 7
    assert roster["by_age_band"]["1_24"]["persons"] == 2
    assert roster["by_age_band"]["80_plus"]["persons"] == 3
    assert (
        sum(item["persons"] for item in roster["by_age_band"].values())
        + roster["unknown_age"]["persons"]
        == 12
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


def _atom_table(rows, sizes):
    """Published sets built from atoms of the given sizes: atom ``a`` holds
    the units ``(a, 0)`` to ``(a, sizes[a] - 1)``."""
    return _table_registry(
        {
            f"row_{j}": {(a, i) for a in row for i in range(sizes[a])}
            for j, row in enumerate(rows)
        }
    )


def _release_public_bytes(inputs):
    people, labor, anchor, design = inputs
    validity = _validity(labor)
    raw = script.structural_counts(people, validity, anchor, design)
    registry = script.disclosure_registry(people, validity, anchor, design)
    published, disclosure, private = script.release_counts(raw, registry)
    public = _bytes({"counts": published, "disclosure": disclosure})
    return public, disclosure, private["audit"]


def _own_strata(inputs):
    """Give every person a stratum of their own. One shared stratum makes
    the strata count of a one-person band, which is at most its clusters
    and persons, narrow, so the audit rightly withholds."""
    people, labor, anchor, design = inputs
    design = design.copy()
    design["stratum"] = design["person_id"]
    return people, labor, anchor, design


def _release_panel(persons=60, *, b0_1_domain=True):
    """Persons in every wave, ages spread over the bands, some sharing a
    household; large enough that the audit releases.

    B0.1's counts of this panel include small exact cells that are B0.2's
    sets too (five persons under 25), so with them in the audit it rightly
    withholds. Without a B0.1 domain (every 2011-wave labor row invalid),
    B0.1 counts only the full anchor, and the panel releases."""
    rows = [
        _row(
            person,
            wave,
            20 + (person * 7) % 55 + wave - 2011,
            relationship=10 if person % 3 else 20,
            weight=1.0 + person % 4,
            interview=person if person % 3 else person - 1,
        )
        for person in range(1, persons + 1)
        for wave in WAVES
    ]
    invalid = ()
    if not b0_1_domain:
        interviews = {row["interview"] for row in rows} | {999_999}
        invalid = [
            (2011, interview, role)
            for interview in interviews
            for role in ("head", "spouse")
        ]
    return _own_strata(_inputs(rows, invalid=invalid))


def _sensitive(audit):
    return [
        target
        for target in audit["targets"]
        if 1 <= target["true_size"] < script.DISCLOSURE_THRESHOLD
    ]


# An enumeration oracle for the disclosure rule, written independently of
# the script's integer programs: one unit type, atoms of any size from 0.
def _oracle_coarsen(value):
    if value == 0:
        return 0
    if value < 10:
        return "<10"
    return (2 * value + 10) // 20 * 10


def _oracle_targets(rows, atoms):
    found = {(a,) for a in range(atoms)}
    sets = [frozenset(row) for row in rows]
    for big in sets:
        for small in sets:
            if small and small < big:
                found.add(tuple(sorted(big - small)))
    return sorted(found)


def _oracle_candidates(rows, sizes):
    """Every atom-size vector whose publication equals the truth's."""
    from itertools import product

    published = [_oracle_coarsen(sum(sizes[a] for a in row)) for row in rows]
    highest = [
        max(v for v in range(100) if _oracle_coarsen(v) == value)
        for value in published
    ]
    caps = [
        min(highest[j] for j, row in enumerate(rows) if a in row)
        for a in range(len(sizes))
    ]
    grid = np.array(list(product(*(range(cap + 1) for cap in caps))))
    totals = [grid[:, list(row)].sum(axis=1) for row in rows]
    keep = np.ones(len(grid), dtype=bool)
    for total, value in zip(totals, published, strict=True):
        keep &= np.array([_oracle_coarsen(int(t)) == value for t in total])
    return grid[keep]


def _oracle_class(values):
    if values.max() - values.min() >= 4:
        return "wide"
    if not np.any((values >= 1) & (values <= 9)):
        return "irrelevant"
    return "narrow"


def _oracle_release(rows, sizes, grid, targets):
    """The rule by enumeration: status, disclosed targets, the final
    candidate mask and each target's final classification."""
    values = {t: grid[:, list(t)].sum(axis=1) for t in targets}
    mask = np.ones(len(grid), dtype=bool)
    disclosed = []
    while True:
        classes = {
            t: _oracle_class(values[t][mask])
            for t in targets
            if t not in disclosed
        }
        narrow = [t for t, result in classes.items() if result == "narrow"]
        if any(1 <= sum(sizes[a] for a in t) <= 9 for t in narrow):
            return "withheld", disclosed, mask, classes
        if not narrow:
            classes.update({t: "narrow" for t in disclosed})
            return "released", disclosed, mask, classes
        disclosed.extend(narrow)
        for t in narrow:
            mask &= ~((values[t] >= 1) & (values[t] <= 9))


@st.composite
def _atom_tables(draw):
    """Two or three atoms, each given a distinct nonempty set of rows to
    belong to, so every draw is a valid table. Rows left empty or repeated
    are dropped; distinct atoms leave at least two rows."""
    width = draw(st.integers(2, 4))
    atoms = draw(st.integers(2, 3))
    subsets = [
        frozenset(rows)
        for size in range(1, width + 1)
        for rows in combinations(range(width), size)
    ]
    signatures = draw(st.permutations(subsets))[:atoms]
    rows = []
    for j in range(width):
        row = tuple(a for a in range(atoms) if j in signatures[a])
        if row and row not in rows:
            rows.append(row)
    sizes = draw(st.lists(st.integers(1, 14), min_size=atoms, max_size=atoms))
    return rows, sizes


def _script_atoms(rows, atoms, registry):
    """Map the script's atom columns to the oracle's atoms by the rows
    each belongs to."""
    model = script.build_model(registry)
    matrix = model["matrix"].toarray()
    mapping = {}
    for column in range(matrix.shape[1]):
        names = {
            model["paths"][r][0] for r in np.flatnonzero(matrix[:, column])
        }
        (atom,) = [
            a
            for a in range(atoms)
            if {f"row_{j}" for j, row in enumerate(rows) if a in row} == names
        ]
        mapping[column] = atom
    return mapping


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


@pytest.mark.parametrize("base", [10, 50])
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


@pytest.mark.parametrize("value", [-1, -0.5, float("nan"), float("inf")])
def test_coarsening_refuses_negative_and_nonfinite_values(value):
    with pytest.raises(ValueError, match="finite and nonnegative"):
        script.coarsen(value, 10)


def test_the_fixed_base_is_ten_with_no_ladder():
    assert script.DISCLOSURE_BASE == 10
    assert script.DISCLOSURE_THRESHOLD == 10
    assert script.PROTECTION_WIDTH == 4
    assert not hasattr(script, "DISCLOSURE_BASES")


@pytest.mark.parametrize(
    ("published", "bound"),
    [(0, 0), ("<10", 1), (10, 10), (20, 15), (30, 25), (100, 95)],
)
def test_an_effective_size_bounds_its_count_from_below(published, bound):
    """An effective size never exceeds its count, and a positive one needs
    a unit; a published multiple e means at least max(B, e - B/2)."""
    assert script.effective_count_bound(published, 10) == bound


def test_a_published_effective_size_lifts_its_count_interval(monkeypatch):
    counts, registry = _table_registry(
        {"persons": set(range(12)), "part": set(range(5))}
    )
    counts["kish_n_eff"] = 10.0
    registry.effective(("kish_n_eff",), ("persons",))
    original = script.count_interval
    # Broaden the count intervals so only the effective bound can lift
    # the persons row's lower bound above 0.
    monkeypatch.setattr(
        script,
        "count_interval",
        lambda value, base: (0, original(value, base)[1]),
    )
    model = script.build_model(registry)
    lower, upper = script.published_bounds(counts, registry, model, 10)
    row = model["path_rows"][("persons",)]
    assert lower[row] == 10 and upper[row] == 14
    system = script.AuditSystem(model, lower, upper, [], [])
    remainder = next(t for t in model["targets"] if t["true_size"] == 7)
    minimum, _ = system.extreme(
        remainder["columns"], -1, None, None, seconds=60
    )
    assert minimum == 1  # 10 persons less at most 9 in the part


@pytest.mark.parametrize("size", range(13))
def test_only_a_narrow_target_of_true_size_one_to_nine_withholds(
    size, monkeypatch
):
    """Pin one atom exactly: the release is withheld only when its true
    size is from 1 to 9."""
    counts, registry = _table_registry({"persons": set(range(size))})
    monkeypatch.setattr(
        script,
        "count_interval",
        lambda value, base: (size, size),
    )
    audit = script.audit_counts(counts, registry, 10)
    assert audit["status"] == ("withheld" if 1 <= size <= 9 else "released")
    if size:
        (target,) = audit["targets"]
        assert target["result"] == ("narrow" if size <= 9 else "irrelevant")


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
    # Complete rows guarantee all six relations for every frame.
    relations = {
        (kind, left[-1], right[-1])
        for kind, left, right in registry.relations
        if left[:-1] == prefix
    }
    assert relations == {
        ("at_most", "households", "persons"),
        ("at_most", "design_clusters", "persons"),
        ("at_most", "design_strata", "design_clusters"),
        ("nonempty", "persons", "households"),
        ("nonempty", "persons", "design_clusters"),
        ("nonempty", "persons", "design_strata"),
    }


@pytest.mark.parametrize(
    ("change", "lost"),
    [
        ("none", set()),
        (
            "missing_person",
            {
                ("at_most", "households", "persons"),
                ("at_most", "design_clusters", "persons"),
            },
        ),
        (
            "repeated_person",
            {
                ("at_most", "households", "persons"),
                ("at_most", "design_clusters", "persons"),
            },
        ),
        ("missing_interview", {("nonempty", "persons", "households")}),
        ("missing_stratum", {("nonempty", "persons", "design_strata")}),
    ],
)
def test_relations_are_registered_only_where_rows_guarantee_them(change, lost):
    frame = pd.DataFrame(
        {
            "person_id": [1.0, 2.0, 3.0],
            "interview": [10.0, 10.0, 20.0],
            "stratum": [1.0, 1.0, 2.0],
            "cluster": [5.0, 5.0, 6.0],
        }
    )
    if change == "missing_person":
        frame.loc[2, "person_id"] = np.nan
    elif change == "repeated_person":
        frame.loc[2, "person_id"] = 1.0
    elif change == "missing_interview":
        frame.loc[2, "interview"] = np.nan
    elif change == "missing_stratum":
        frame.loc[2, "stratum"] = np.nan
    relations = script.frame_relations(frame)
    assert len(relations) == 6
    assert {key for key, held in relations.items() if not held} == lost


def test_a_relation_the_rows_do_not_guarantee_is_not_registered():
    """One person with no design stratum, alone in the 62-64 bands: those
    sets hold a person and no stratum, so "persons only with strata" is
    not guaranteed for them. The registry omits it there, and the model
    builds; registering it anyway would stop the script as a defect."""
    rows = [_row(1, wave, 62 + wave - 2011) for wave in WAVES] + [
        _row(person, wave, 30 + wave - 2011)
        for person in (2, 3, 4)
        for wave in WAVES
    ]
    people, labor, anchor, design = _inputs(rows)
    design.loc[design["person_id"] == 1, "stratum"] = np.nan
    registry = script.disclosure_registry(
        people, _validity(labor), anchor, design
    )
    unguaranteed = []
    for path, (_, members) in registry.sets.items():
        strata = registry.sets.get((*path[:-1], "design_strata"))
        if path[-1] == "persons" and members and strata and not strata[1]:
            unguaranteed.append(path[:-1])
    assert ("rosters", "R_FULL", "by_age_band", "62_64") in unguaranteed
    registered = {
        left[:-1]
        for kind, left, right in registry.relations
        if kind == "nonempty" and right[-1] == "design_strata"
    }
    assert registered and not registered & set(unguaranteed)
    script.model_relations(registry, script.build_model(registry))


def test_a_violated_relation_is_a_defect_not_data():
    counts, registry = _table_registry({"few": {1}, "many": {1, 2}})
    registry.relate("at_most", ("many",), ("few",))
    with pytest.raises(ValueError, match="guaranteed relation fails"):
        script.audit_counts(counts, registry)
    with pytest.raises(ValueError, match="unknown relation"):
        registry.relate("equal", ("many",), ("few",))


def test_relations_constrain_counts_across_unit_types():
    """With every count free from 0 to 9, "at most" excludes more
    households than persons, and "nonempty" excludes persons without a
    household."""
    counts, registry = _table_registry({"persons": set(range(3))})
    registry.add(("households",), "households_2011", {"h1", "h2"})
    counts["households"] = 2
    registry.relate("at_most", ("households",), ("persons",))
    registry.relate("nonempty", ("persons",), ("households",))
    model = script.build_model(registry)
    relations = script.model_relations(registry, model)
    rows = model["matrix"].shape[0]
    system = script.AuditSystem(
        model,
        np.zeros(rows, dtype=np.int64),
        np.full(rows, 9, dtype=np.int64),
        relations,
        [],
    )
    persons = model["unit_types"].index("persons")
    households = model["unit_types"].index("households_2011")
    point = np.zeros(system.atoms, dtype=np.int64)
    point[persons], point[households] = 1, 2
    assert not system.feasible(point)  # two households, one person
    point[persons], point[households] = 2, 0
    assert not system.feasible(point)  # persons but no household
    point[persons], point[households] = 2, 2
    assert system.feasible(point)
    point[persons], point[households] = 0, 0
    assert system.feasible(point)


def test_disclosure_integer_hidden_band_attack_is_blocked_on_full_release():
    inputs = _own_strata(
        _inputs(
            [
                *[_row(person, age=29) for person in range(1, 19)],
                _row(19, age=63),
                _row(20, age=66),
            ]
        )
    )
    raw = _counts(inputs)
    assert raw["rosters"]["R_FULL"]["overall"]["persons"] == 20
    assert raw["rosters"]["R_FULL"]["by_age_band"]["25_44"]["persons"] == 18
    people, labor, anchor, design = inputs
    registry = script.disclosure_registry(
        people, _validity(labor), anchor, design
    )
    published, disclosure, private = script.release_counts(raw, registry)
    assert disclosure["status"] == "released" and published
    assert all(t["result"] == "wide" for t in _sensitive(private["audit"]))
    assert (
        published["rosters"]["R_FULL"]["by_age_band"]["25_44"]["persons"] == 20
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
    published, disclosure, private = script.release_counts(raw, registry)
    assert disclosure["status"] == "released" and published
    remainder = [
        t
        for t in private["audit"]["targets"]
        if t["unit_type"] == "persons" and t["true_size"] == 1
    ]
    assert remainder and all(t["result"] == "wide" for t in remainder)


def _coresident_remainder_inputs(coresidents):
    """Round 2's attack: ten heads aged 29, the first with weight 10, and
    ``coresidents`` more persons aged 29 in the first head's household."""
    return _inputs(
        [
            *[
                _row(person, age=29, weight=10.0 if person == 1 else 1.0)
                for person in range(1, 11)
            ],
            *[
                _row(100 + i, age=29, relationship=30, interview=1)
                for i in range(coresidents)
            ],
        ]
    )


def test_the_committed_file_is_identical_for_every_protected_remainder():
    """Round 2 read a remainder of 1 to 4 from public audit counts. The
    public block now holds only the base, the rules and the status, so
    every remainder the audit protects gives the same bytes."""
    released = [
        _release_public_bytes(_coresident_remainder_inputs(r))
        for r in range(5)
    ]
    assert {disclosure["status"] for _, disclosure, _ in released} == {
        "released"
    }
    assert len({public for public, _, _ in released}) == 1
    for _, disclosure, _ in released:
        assert set(disclosure) == {
            "base",
            "coarsening_rule",
            "protection_rule",
            "status",
        }


def test_disclosure_audits_multi_atom_published_subset_differences():
    counts, registry = _table_registry(
        {
            "total": set(range(15)),
            "subset": set(range(10)),
            "distinguish": {10, 11},
        }
    )
    model = script.build_model(registry)
    differences = [t for t in model["targets"] if t["kind"] == "difference"]
    assert any(
        t["true_size"] == 5 and len(t["columns"]) == 2 for t in differences
    )
    # An empty published set is no one's subset.
    counts, registry = _table_registry({"total": {1, 2}, "none": set()})
    assert [t["kind"] for t in script.build_model(registry)["targets"]] == [
        "atom"
    ]


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
    published, disclosure, _ = script.release_counts(counts, registry)
    assert disclosure["status"] == "released" and published


def test_disclosure_public_block_holds_only_base_rules_and_status():
    people, labor, anchor, design = _release_panel()
    validity = _validity(labor)
    raw = script.structural_counts(people, validity, anchor, design)
    registry = script.disclosure_registry(people, validity, anchor, design)
    published, disclosure, private = script.release_counts(raw, registry)
    assert disclosure == {
        "base": 10,
        "coarsening_rule": script.COARSENING_RULE,
        "protection_rule": script.PROTECTION_RULE,
        "status": "released",
    }
    for path, value in script._leaves(published):
        assert not isinstance(value, (set, frozenset))
        if isinstance(value, (int, float)):
            assert value == 0 or value >= 10, (path, value)
    public_bytes = _bytes({"counts": published, "disclosure": disclosure})
    for forbidden in (
        b'"sets"',
        b'"atoms"',
        b'"atom_sizes"',
        b'"true_size"',
        b'"targets"',
        b'"rounds"',
        b'"range"',
    ):
        assert forbidden not in public_bytes
    assert "atom_sizes" in private["audit"]


def test_a_withheld_release_publishes_status_and_no_counts(monkeypatch):
    counts, registry = _table_registry({"persons": {1, 2, 3}})
    monkeypatch.setattr(script, "count_interval", lambda value, base: (3, 3))
    published, disclosure, private = script.release_counts(counts, registry)
    assert published == {}
    assert disclosure["status"] == "withheld"
    assert set(disclosure) == {
        "base",
        "coarsening_rule",
        "protection_rule",
        "status",
    }
    assert private["audit"]["atom_sizes"] == {"persons": [3]}


@settings(max_examples=100, deadline=None)
@given(_atom_tables())
@example(([(0, 1), (0,), (1,)], [9, 7]))
@example(([(0, 1), (0,), (1,)], [10, 1]))
def test_audit_agrees_with_an_exhaustive_reader(table):
    """The integer-program audit and the enumeration oracle reach the same
    decision, disclosures and classifications. Then the oracle checks the
    rule itself: a reader who reruns it on every vector with the same
    publication keeps exactly the final candidates, and every sensitive
    target keeps a range of width 4 or more among them."""
    rows, sizes = table
    counts, registry = _atom_table(rows, sizes)
    audit = script.audit_counts(counts, registry, 10)
    mapping = _script_atoms(rows, len(sizes), registry)
    grid = _oracle_candidates(rows, sizes)
    targets = _oracle_targets(rows, len(sizes))
    status, disclosed, mask, classes = _oracle_release(
        rows, sizes, grid, targets
    )
    script_targets = {
        tuple(sorted(mapping[c] for c in t["columns"])): t
        for t in audit["targets"]
    }
    assert set(script_targets) == set(targets)
    assert audit["status"] == status
    event(f"{status} after {len(audit['rounds'])} round(s)")
    if status != "released":
        return
    assert {
        tuple(sorted(mapping[c] for c in audit["targets"][i]["columns"]))
        for i in audit["disclosed"]
    } == set(disclosed)
    for target, result in classes.items():
        assert script_targets[target]["result"] == result, target
    kept = np.array(
        [
            _oracle_release(rows, list(point), grid, targets)[0] == "released"
            for point in grid
        ]
    )
    assert np.array_equal(kept, mask)
    for target in targets:
        if 1 <= sum(sizes[a] for a in target) <= 9:
            values = grid[kept][:, list(target)].sum(axis=1)
            assert values.max() - values.min() >= 4, target


def _program_transcript(rows, sizes):
    """Every program the audit hands the solver, in order."""
    counts, registry = _atom_table(rows, sizes)
    transcript = []
    original = script.AuditSystem._program

    def recording(self, objective, extra, seconds, integral=True, gap=0.0):
        parts = [np.asarray(objective, dtype=float).tobytes()]
        for constraint in (self.constraint, *extra):
            matrix = constraint.A
            matrix = matrix.toarray() if hasattr(matrix, "toarray") else matrix
            for array in (matrix, constraint.lb, constraint.ub):
                parts.append(np.asarray(array, dtype=float).tobytes())
        transcript.append(
            (hashlib.sha256(b"|".join(parts)).hexdigest(), integral, gap)
        )
        return original(self, objective, extra, seconds, integral, gap)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(script.AuditSystem, "_program", recording)
        audit = script.audit_counts(counts, registry, 10)
    return transcript, audit


@settings(max_examples=60, deadline=None)
@given(_atom_tables(), st.data())
def test_audit_programs_depend_only_on_the_publication(table, data):
    """Two tables with the same publication and the same atoms hand the
    solver the same programs in the same order, up to the point where one
    of them withholds. True sizes enter only the withholding test."""
    rows, sizes = table
    grid = _oracle_candidates(rows, sizes)
    grid = grid[np.all(grid > 0, axis=1)]  # same atoms exist
    other = [int(v) for v in grid[data.draw(st.integers(0, len(grid) - 1))]]
    first, first_audit = _program_transcript(rows, sizes)
    second, second_audit = _program_transcript(rows, other)
    shorter = min(len(first), len(second))
    assert first[:shorter] == second[:shorter]
    if first_audit["status"] == second_audit["status"] == "released":
        assert first == second
        assert first_audit["disclosed"] == second_audit["disclosed"]
        assert [t["result"] for t in first_audit["targets"]] == [
            t["result"] for t in second_audit["targets"]
        ]


def test_targets_are_classified_in_one_order_whatever_their_sizes(
    monkeypatch,
):
    """Two tables with one publication, 11 and 14 units in opposite atoms:
    the first round classifies every target in the model's order, which
    is the same for both. An order taken from true sizes would differ."""
    calls = []
    original = script.classify

    def recording(system, target, pool, *, seconds):
        calls.append(tuple(target["columns"]))
        return original(system, target, pool, seconds=seconds)

    monkeypatch.setattr(script, "classify", recording)
    orders = []
    for sizes in ([11, 14], [14, 11]):
        counts, registry = _atom_table([(0, 1), (0,)], sizes)
        model = script.build_model(registry)
        expected = [tuple(target["columns"]) for target in model["targets"]]
        calls.clear()
        audit = script.audit_counts(counts, registry, 10)
        assert audit["status"] == "released"
        assert calls[: len(expected)] == expected
        orders.append(expected)
    assert orders[0] == orders[1]


@pytest.mark.parametrize(
    "sizes", [(1, 1, 1), (1, 2, 3), (3, 3, 4), (3, 7, 8), (1, 2, 10)]
)
def test_integer_audit_extrema_agree_with_bruteforce(sizes):
    rows = [(0, 1), (0, 2), (1, 2)]
    counts, registry = _atom_table(rows, list(sizes))
    model = script.build_model(registry)
    lower, upper = script.published_bounds(counts, registry, model, 10)
    system = script.AuditSystem(model, lower, upper, [], [])
    mapping = _script_atoms(rows, len(sizes), registry)
    grid = _oracle_candidates(rows, list(sizes))
    assert len(grid)
    for target in model["targets"]:
        atoms = [mapping[c] for c in target["columns"]]
        values = grid[:, atoms].sum(axis=1)
        maximum, _ = system.extreme(
            target["columns"], 1, None, None, seconds=60
        )
        minimum, _ = system.extreme(
            target["columns"], -1, None, None, seconds=60
        )
        assert (minimum, maximum) == (values.min(), values.max())
    if sizes == (1, 1, 1):
        # The continuous relaxation's maximum is 8.5, at (8.5, .5, .5).
        column = model["targets"][0]["columns"]
        assert system.extreme(column, 1, None, None, seconds=60)[0] == 8


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
    model = script.build_model(registry)
    assert issparse(model["matrix"])
    assert len(model["sizes"]) <= len(groups)
    assert model["matrix"].shape[0] < len(sets)  # duplicate sets share rows
    published, disclosure, private = script.release_counts(counts, registry)
    assert disclosure["status"] == "released" and published
    assert _sensitive(private["audit"])


def test_witnesses_are_checked_exactly_and_never_taken_from_the_solver(
    monkeypatch,
):
    """A solver answer that is fractional or breaks a constraint is no
    witness, so it can never make a target wide."""
    from types import SimpleNamespace

    counts, registry = _table_registry({"persons": {1, 2, 3}})
    model = script.build_model(registry)
    lower, upper = script.published_bounds(counts, registry, model, 10)
    system = script.AuditSystem(model, lower, upper, [], [])
    for answer in ([2.5], [12.0], [-1.0], [0.0]):
        result = SimpleNamespace(status=0, x=np.array(answer), fun=0.0)
        assert system._witness(result) is None, answer
    good = SimpleNamespace(status=0, x=np.array([5.0 + 1e-9]), fun=0.0)
    assert system._witness(good).tolist() == [5]
    assert system._witness(good, [0], 6, None) is None  # outside window


def test_programs_use_one_thread_sixty_seconds_and_exact_optima(monkeypatch):
    calls = []
    original = script.milp

    def recording(objective, **kwargs):
        calls.append(kwargs["options"])
        return original(objective, **kwargs)

    monkeypatch.setattr(script, "milp", recording)
    counts, registry = _atom_table([(0, 1), (0,)], [3, 9])
    audit = script.audit_counts(counts, registry, 10)
    assert audit["status"] == "released" and calls
    assert all(call["threads"] == 1 for call in calls)
    assert all(call["time_limit"] == 60 for call in calls)
    directions = calls[: 1 + script.POOL_DIRECTIONS]
    assert all(call["mip_rel_gap"] == 1.0 for call in directions)
    assert all(call["mip_rel_gap"] == 0.0 for call in calls[len(directions) :])


def test_unanswered_programs_withhold(monkeypatch):
    from types import SimpleNamespace

    def no_answer(objective, **kwargs):
        return SimpleNamespace(status=1, success=False, x=None, fun=None)

    monkeypatch.setattr(script, "milp", no_answer)
    counts, registry = _table_registry({"persons": {1}})
    published, disclosure, private = script.release_counts(counts, registry)
    assert published == {} and disclosure["status"] == "withheld"
    assert private["audit"]["pool"] == 0


def test_an_undetermined_sensitive_target_withholds(monkeypatch):
    """Seed points exist, but no later program answers: a sensitive target
    the pool cannot show wide is narrow, so the release is withheld."""
    from types import SimpleNamespace

    original = script.milp
    calls = []

    def first_seed_only(objective, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            return original(objective, **kwargs)
        return SimpleNamespace(status=1, success=False, x=None, fun=None)

    monkeypatch.setattr(script, "milp", first_seed_only)
    counts, registry = _table_registry({"persons": {1}})
    audit = script.audit_counts(counts, registry, 10)
    (target,) = audit["targets"]
    assert audit["status"] == "withheld" and audit["pool"] == 1
    assert target["result"] == "narrow"
    assert target["proof"] == "undetermined"


def test_a_target_the_pool_shows_wide_runs_no_program():
    pool = script.WitnessPool(2)
    pool.add(np.array([1, 0]))
    pool.add(np.array([6, 0]))
    record, witness = script.classify(
        None, {"columns": (0,), "true_size": 3}, pool, seconds=60
    )
    assert record == {"programs": [], "result": "wide", "proof": "pool"}
    assert witness is None
    with pytest.raises(ValueError):
        script.WitnessPool(2).values([0])  # an empty pool proves nothing


@pytest.mark.parametrize(
    ("relaxed", "result"),
    [(9.6, "irrelevant"), (9.5, "narrow"), (9.0, "narrow"), (None, "narrow")],
)
def test_the_relaxation_proves_irrelevance_only_above_nine_and_a_half(
    relaxed, result
):
    """With every pool value 10 or more, a relaxation minimum above 9.5
    settles the target; anything else falls through to the programs, here
    stubbed to give an integer range of 9 to 11."""

    class Stub:
        def relaxed_minimum(self, columns, *, seconds):
            return relaxed

        def search(self, columns, low=None, high=None, *, seconds):
            return 2, None

        def extreme(self, columns, sense, low, high, *, seconds):
            return (11 if sense == 1 else 9), np.array([10])

    pool = script.WitnessPool(1)
    pool.add(np.array([10]))
    pool.add(np.array([11]))
    record, _ = script.classify(
        Stub(), {"columns": (0,), "true_size": 10}, pool, seconds=60
    )
    assert record["result"] == result
    assert record["programs"][0] == "relaxation"


@pytest.mark.parametrize("statuses", [(1, 2), (2, 1), (1, 1)])
def test_a_timed_out_search_proves_nothing(statuses):
    """HiGHS status 2 proves a window empty; status 1, a time limit,
    proves nothing. A target whose search timed out without a point stays
    narrow, and no extreme program runs for it."""
    answers = iter(statuses)

    class Stub:
        def relaxed_minimum(self, columns, *, seconds):
            raise AssertionError("the pool's least value is below 10")

        def search(self, columns, low=None, high=None, *, seconds):
            return next(answers), None

        def extreme(self, columns, sense, low, high, *, seconds):
            raise AssertionError("an unproven window ran an extreme")

    pool = script.WitnessPool(1)
    pool.add(np.array([5]))
    record, witness = script.classify(
        Stub(), {"columns": (0,), "true_size": 5}, pool, seconds=60
    )
    assert record["result"] == "narrow"
    assert record["proof"] == "undetermined"
    assert record["programs"] == list(statuses)
    assert witness is None


def _two_atom_disclosure():
    """Atom 0 holds 12 units and atom 1 holds 3, published as their union
    (20, so 15-24) and atom 1 alone (<10), so atom 0 can take 6 to 23."""
    rows = [(0, 1), (1,)]
    counts, registry = _atom_table(rows, [12, 3])
    column = {atom: c for c, atom in _script_atoms(rows, 2, registry).items()}
    return counts, registry, column


def test_a_disclosed_target_stays_outside_one_to_nine():
    """A disclosed target's size is 0 or at least 10, in the exact check
    and in every program the solver runs."""
    counts, registry, column = _two_atom_disclosure()
    model = script.build_model(registry)
    lower, upper = script.published_bounds(counts, registry, model, 10)
    (target,) = [
        t
        for t in model["targets"]
        if t["kind"] == "atom" and list(t["columns"]) == [column[0]]
    ]
    before = script.AuditSystem(model, lower, upper, [], [])
    after = script.AuditSystem(model, lower, upper, [], [target])
    point = np.zeros(2, dtype=np.int64)
    point[column[0]], point[column[1]] = 7, 9
    assert before.feasible(point) and not after.feasible(point)
    assert before.search([column[0]], 1, 9, seconds=60)[1] is not None
    status, witness = after.search([column[0]], 1, 9, seconds=60)
    assert status == 2 and witness is None
    assert before.extreme([column[0]], -1, None, None, seconds=60)[0] == 6
    assert after.extreme([column[0]], -1, None, None, seconds=60)[0] == 10


def test_a_narrow_target_outside_one_to_nine_starts_another_round(
    monkeypatch,
):
    """Round 1 finds atom 0 (true size 12) narrow, forced here since small
    tables rarely produce one. It is disclosed; the pool drops the points
    the disclosure rules out; and every other target is classified again
    under it, in a second round that discloses nothing more."""
    counts, registry, column = _two_atom_disclosure()
    original = script.classify
    calls = []

    def forcing(system, target, pool, *, seconds):
        points = pool.points[: pool.size]
        calls.append(
            {
                "disclosed": list(system.disclosed),
                "pool_feasible": all(system.feasible(p) for p in points),
                "pool_low": bool(np.any(points[:, column[0]] <= 9)),
            }
        )
        if not system.disclosed and target["columns"] == (column[0],):
            return {
                "programs": [],
                "result": "narrow",
                "proof": "forced",
            }, None
        return original(system, target, pool, seconds=seconds)

    monkeypatch.setattr(script, "classify", forcing)
    audit = script.audit_counts(counts, registry, 10)
    forced = [
        i for i, t in enumerate(audit["targets"]) if t.get("proof") == "forced"
    ]
    assert len(forced) == 1
    assert audit["status"] == "released"
    assert audit["disclosed"] == forced
    assert [r["disclosed"] for r in audit["rounds"]] == [forced, []]
    first = [c for c in calls if not c["disclosed"]]
    second = [c for c in calls if c["disclosed"]]
    assert len(first) == len(audit["targets"])
    assert second and all(c["disclosed"] == [(column[0],)] for c in second)
    # The first round's pool held a point with atom 0 at 9 or less, which
    # the disclosure rules out; the second round's pool holds none.
    assert any(c["pool_low"] for c in first)
    assert all(c["pool_feasible"] for c in calls)
    assert not any(c["pool_low"] for c in second)
    assert all(
        audit["targets"][i]["round"] == 2
        for i in range(len(audit["targets"]))
        if i not in forced and audit["targets"][i]["result"] != "irrelevant"
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
    """main() on the worked rosters. Their design counts are small enough
    that the audit withholds them."""
    return _main_environment(tmp_path, monkeypatch, _worked_rosters())


@pytest.fixture
def released_main(tmp_path, monkeypatch):
    """main() on a panel the audit releases with B0.1's counts in it."""
    return _main_environment(
        tmp_path, monkeypatch, _release_panel(b0_1_domain=False)
    )


def _main_environment(tmp_path, monkeypatch, inputs):
    people, labor, anchor, design = inputs
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
    baseline.write_text(json.dumps(_b01_record(people, supplied[1])))
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


def test_main_records_provenance_and_checks_b01_size(tmp_path, released_main):
    supplied, baseline, calls = released_main
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
    script.register_b0_1(
        registry,
        script.b0_1_sets(*supplied[:2]),
        json.loads(baseline.read_text())["counts"],
    )
    assert registry.prior
    coarsened, disclosure, local_audit = script.release_counts(
        raw_counts, registry
    )
    assert record["counts"] == coarsened
    assert record["disclosure"] == disclosure
    assert disclosure["status"] == "released" and disclosure["base"] == 10
    assert "disclosure_audit" not in record
    local_record = json.loads((tmp_path / "local.json").read_text())
    assert local_record["counts"] == raw_counts
    # Everything in the local audit but its timing is reproducible.
    for audit in (local_record["disclosure_audit"], local_audit):
        audit["audit"].pop("seconds")
    assert local_record["disclosure_audit"] == local_audit
    assert local_record["repository_head"] == record["repository_head"]
    assert record["geometry"]["collection_waves"] == list(WAVES)
    assert record["geometry"]["reference_years"] == [
        wave - 1 for wave in WAVES
    ]
    assert record["geometry"]["age_convention"] == "collection_wave"
    assert record["geometry"]["lag_years"] == [2, 4]
    _assert_no_forbidden_output(record)


def test_a_small_b0_1_cell_that_is_a_b0_2_set_withholds(tmp_path, monkeypatch):
    """B0.1 counts the plain release panel's domain persons under 25
    exactly, as five, and that set is also B0.2's 1-24 band of R_FULL.
    Through main() the release is withheld; the same panel releases when
    B0.1's counts are left out of the audit."""
    inputs = _release_panel()
    _main_environment(tmp_path, monkeypatch, inputs)
    out = tmp_path / "counts.json"
    local = tmp_path / "local.json"
    assert script.main(["--out", str(out), "--local-copy", str(local)]) == 0
    assert json.loads(out.read_text())["disclosure"]["status"] == "withheld"
    people, labor, anchor, design = inputs
    validity = _validity(labor)
    earlier = b01.structural_counts(people, validity)
    assert earlier["domain_by_anchor_wave_age"]["under_25"] == 5
    registry = script.disclosure_registry(people, validity, anchor, design)
    band = ("rosters", "R_FULL", "by_age_band", "1_24", "persons")
    under_25 = ("domain_by_anchor_wave_age", "under_25")
    assert (
        registry.sets[band][1]
        == script.b0_1_sets(people, validity)[under_25][1]
    )
    counts = script.structural_counts(people, validity, anchor, design)
    assert script.release_counts(counts, registry)[1]["status"] == "released"


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


def _partials(directory):
    return sorted(path.name for path in directory.glob(".*.partial"))


def test_main_never_overwrites_an_output_that_appears_during_read(
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
    assert not _partials(tmp_path)


def test_main_never_overwrites_a_local_copy_that_appears_during_read(
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
    assert not out.exists() and not _partials(tmp_path)


@pytest.mark.parametrize("failure", ["write", "fsync", "close", "link"])
def test_write_new_leaves_no_file_under_its_name_on_failure(
    failure, tmp_path, monkeypatch
):
    """Round 2 left a 20-byte public file after a disk-full error. Now a
    failure at any step leaves neither the final name nor the temporary."""
    target = tmp_path / "counts.json"
    original = getattr(script.os, failure)

    def failing(*args, **kwargs):
        if failure == "close":
            original(*args, **kwargs)
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(script.os, failure, failing)
    with pytest.raises(OSError, match="No space left"):
        script.write_new(target, b'{"counts": {}}\n' * 1000)
    monkeypatch.undo()
    assert not target.exists() and not _partials(tmp_path)


def test_write_new_writes_every_byte_and_refuses_an_existing_name(tmp_path):
    target = tmp_path / "counts.json"
    data = bytes(range(256)) * 4096
    script.write_new(target, data)
    assert target.read_bytes() == data
    with pytest.raises(FileExistsError):
        script.write_new(target, b"other")
    assert target.read_bytes() == data and not _partials(tmp_path)


def test_write_new_completes_short_writes(tmp_path, monkeypatch):
    original = script.os.write
    sizes = []

    def short(descriptor, view):
        sizes.append(len(view))
        return original(descriptor, view[:7])

    monkeypatch.setattr(script.os, "write", short)
    target = tmp_path / "counts.json"
    script.write_new(target, b"0123456789" * 5)
    monkeypatch.undo()
    assert target.read_bytes() == b"0123456789" * 5 and len(sizes) == 8


def test_main_public_write_failure_keeps_complete_local_copy_and_attempt(
    tmp_path, monkeypatch, invented_main
):
    out = tmp_path / "counts.json"
    local = tmp_path / "local.json"
    original = script.write_new

    def public_fails(path, data):
        if path == out:
            raise OSError(28, "No space left on device")
        original(path, data)

    monkeypatch.setattr(script, "write_new", public_fails)
    with pytest.raises(OSError, match="No space left"):
        script.main(["--out", str(out), "--local-copy", str(local)])
    assert not out.exists() and not _partials(tmp_path)
    assert json.loads(local.read_text())["counts"]
    assert script._attempt_path(local).exists()
    with pytest.raises(SystemExit, match="refusing to overwrite"):
        script.main(["--out", str(out), "--local-copy", str(local)])


def test_attempt_record_is_flushed_to_disk(tmp_path, monkeypatch):
    synced = []
    original = script.os.fsync

    def recording(descriptor):
        synced.append(descriptor)
        original(descriptor)

    monkeypatch.setattr(script.os, "fsync", recording)
    script._start_attempt(tmp_path / "local.json", "b" * 40, "c" * 64)
    assert len(synced) == 1
    record = json.loads(
        script._attempt_path(tmp_path / "local.json").read_text()
    )
    assert record["repository_head"] == "b" * 40


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


def test_main_withheld_release_commits_provenance_and_status_only(
    tmp_path, invented_main
):
    """The worked rosters' audit withholds: the committed file holds the
    provenance and the status, and the counts stay in the local copy."""
    disclosure = {
        "base": 10,
        "coarsening_rule": script.COARSENING_RULE,
        "protection_rule": script.PROTECTION_RULE,
        "status": "withheld",
    }
    out = tmp_path / "counts.json"
    local = tmp_path / "local.json"
    assert script.main(["--out", str(out), "--local-copy", str(local)]) == 0
    record = json.loads(out.read_text())
    assert "counts" not in record and "disclosure_audit" not in record
    assert record["disclosure"] == disclosure
    assert record["schema"] == script.SCHEMA
    assert record["repository_head"] == "b" * 40
    assert set(record) == {
        "schema",
        "repository_head",
        "worktree_clean",
        "script_sha256",
        "b0_1_counts_sha256",
        "psid_files_opened_sha256",
        "requested_label_allowlist",
        "geometry",
        "disclosure",
    }
    local_record = json.loads(local.read_text())
    assert local_record["counts"] == script.structural_counts(
        *invented_main[0][:-1]
    )
    audit = local_record["disclosure_audit"]["audit"]
    assert audit["status"] == "withheld"
    assert any(
        target["result"] == "narrow" and 1 <= target["true_size"] <= 9
        for target in audit["targets"]
    )


# --------------------------------------------------------------------------
# The earlier release: B0.1's published counts as exact constraints
# --------------------------------------------------------------------------
B01_LEDGERS = (
    "m6_qstar_train_only_selection_results.json",
    "m6_rhostar_train_only_selection_results.json",
)


def _b01_record(people, validity, *, fit_input_rows=321_500):
    """A B0.1 record as its script writes one: the structural counts, and
    the ledger counts it copies, which repeat some of them."""
    counts = b01.structural_counts(people, validity)
    scored = {
        year: counts["scored_support"][year]["scored_rows"]
        for year in ("2010", "2012", "2014")
    }
    ledger = {
        "anchor_wave": counts["anchor_wave"],
        "endpoint_support_rows": scored["2012"] + scored["2014"],
        "fit_input_rows": fit_input_rows,
        "n_domain": counts["domain_persons"],
        "n_full_anchor": counts["full_anchor_persons"],
        "support_age_max": 64,
        "support_age_min": 25,
        "truth_support_rows": counts["scored_rows_total"],
        "truth_support_rows_by_period": scored,
    }
    return {
        "counts": counts,
        "ledger_support_counts": {name: dict(ledger) for name in B01_LEDGERS},
    }


@st.composite
def _b01_frames(draw):
    """Invented persons at B0.1's three waves, reaching every disposition:
    present or not, each sequence group, head, spouse, partner or other,
    zero weights, missing and fractional ages, shared households, invalid
    or missing family records and positive accuracy codes."""
    persons = draw(st.integers(1, 9))
    rows = []
    for person in range(1, persons + 1):
        for wave in (2011, 2013, 2015):
            if wave != 2011 and not draw(st.booleans()):
                continue
            rows.append(
                _row(
                    person,
                    wave,
                    draw(
                        st.sampled_from(
                            [19, 24, 25, 30, 44, 44.5, 45, 60, 64, 65, 70, 999]
                        )
                    ),
                    sequence=draw(st.sampled_from([1, 2, 0, 55, 75, 85])),
                    relationship=draw(st.sampled_from([10, 20, 22, 30])),
                    weight=draw(st.sampled_from([0.0, 1.0, 2.5])),
                    interview=draw(st.integers(1, 3)),
                )
            )
    keys = [
        (wave, interview, role)
        for wave in (2011, 2013, 2015)
        for interview in (1, 2, 3)
        for role in ("head", "spouse")
    ]
    people, labor, _, _ = _inputs(
        rows,
        invalid=draw(st.sets(st.sampled_from(keys))),
        missing=draw(st.sets(st.sampled_from([k[:2] for k in keys]))),
        accuracy=draw(st.sets(st.sampled_from(keys))),
    )
    return people, _validity(labor)


@settings(max_examples=150, deadline=None)
@given(_b01_frames())
def test_b0_1_sets_are_the_sets_b0_1_counts(frames):
    """Differential: on invented frames, every rebuilt set's size is the
    count B0.1's own ``structural_counts`` publishes for it (rows minus
    persons for a change pair's rows), and the record check accepts the
    record those frames give, so every B0.1 count is modeled."""
    people, validity = frames
    counts = b01.structural_counts(people, validity)
    sets = script.b0_1_sets(people, validity)
    for path, (unit_type, units, terms) in sets.items():
        value = sum(sign * _path_value(counts, part) for sign, part in terms)
        assert len(units) == value, path
        assert unit_type == (
            "households_2011" if path[-1].endswith("households") else "persons"
        ), path
    script.check_b0_1_record(_b01_record(people, validity), counts, sets)
    event(f"domain persons: {counts['domain_persons']}")
    event(
        "dispositions seen: "
        + str(
            sum(
                value > 0
                for year in ("2012", "2014")
                for value in counts["domain_dispositions"][year].values()
            )
        )
    )


def _b01_example():
    rows = [
        _row(1, 2011, 40),
        _row(1, 2013, 42, interview=7),
        _row(1, 2015, 44),
        _row(2, 2011, 50, relationship=20, interview=1),
        _row(2, 2013, 52, relationship=20, interview=1, sequence=85),
        _row(3, 2011, 70),
        _row(4, 2011, 30, relationship=30, interview=3),
        _row(4, 2013, 32, interview=4),
    ]
    people, labor, _, _ = _inputs(rows)
    validity = _validity(labor)
    counts = b01.structural_counts(people, validity)
    return people, validity, counts, script.b0_1_sets(people, validity)


def test_b0_1_sets_on_a_hand_counted_example():
    """Person 1 is scored at every wave, and moves to interview 7 at 2013;
    person 2, a spouse in person 1's household, dies by 2013; person 3 is
    a domain head aged 70; person 4 enters at 2013 from inside the
    anchor. B0.1 counts households at each person's 2011 interview, so
    person 1's level cells hold household 1, not 7."""
    people, validity, counts, sets = _b01_example()
    assert sets[("domain_persons",)][1] == {1, 2, 3}
    assert sets[("domain_by_role", "spouse")][1] == {2}
    assert sets[("domain_by_anchor_wave_age", "65_plus")][1] == {3}
    assert sets[("full_anchor_households",)][1] == {1, 3}
    assert sets[("domain_weights", "households")][1] == {1, 3}
    assert sets[("scored_support", "2010", "scored_rows")][1] == {1, 2}
    assert sets[
        ("scored_support", "2010", "valid_domain_rows_outside_age_support")
    ][1] == {3}
    assert sets[("domain_dispositions", "2012", "died")][1] == {2}
    assert sets[("domain_dispositions", "2012", "scored")][1] == {1}
    assert sets[("domain_dispositions", "2012", "not_in_responding_family")][
        1
    ] == {3}
    assert sets[("change_pairs", "pooled_one_step", "persons")][1] == {1}
    assert sets[("change_pairs", "pooled_one_step", "rows")][1] == {1}
    assert counts["change_pairs"]["pooled_one_step"]["rows"] == 2
    assert sets[
        (
            "entrants_not_scored",
            "2012",
            "in_2011_anchor_without_valid_boundary_row",
            "prime",
        )
    ][1] == {4}
    assert sets[("level_cells", "prime", "households")][1] == {1}
    assert counts["level_cells"]["prime"]["households"] == 1


def test_the_b0_1_record_must_be_the_one_these_inputs_give():
    """The record check stops on a count these inputs do not give, a count
    nothing models, a failed sum, a ledger copy that differs or carries a
    new field, and a modeled set B0.1 never published. The M6 fit's row
    count is not modeled, so its value does not matter."""
    from copy import deepcopy

    people, validity, counts, sets = _b01_example()
    record = _b01_record(people, validity)
    script.check_b0_1_record(record, counts, sets)
    script.check_b0_1_record(
        _b01_record(people, validity, fit_input_rows=7), counts, sets
    )

    changed = deepcopy(record)
    changed["counts"]["domain_persons"] += 1
    with pytest.raises(AssertionError, match="rerun"):
        script.check_b0_1_record(changed, counts, sets)

    for edit, message in (
        (lambda c: c.update(new_count=1), "not modeled"),
        (
            lambda c: c.update(scored_rows_total=c["scored_rows_total"] + 1),
            "sum does not hold",
        ),
        (
            lambda c: c["level_cells"]["prime"].update(rows=99),
            "sum does not hold",
        ),
    ):
        edited = deepcopy(record)
        edit(edited["counts"])
        with pytest.raises(AssertionError, match=message):
            script.check_b0_1_record(edited, edited["counts"], sets)

    for edit in (
        lambda ledger: ledger.update(n_domain=ledger["n_domain"] + 1),
        lambda ledger: ledger["truth_support_rows_by_period"].update(
            {"2012": -1}
        ),
        lambda ledger: ledger.update(extra_rows=4),
        lambda ledger: ledger.pop("endpoint_support_rows"),
    ):
        edited = deepcopy(record)
        edit(edited["ledger_support_counts"][B01_LEDGERS[1]])
        with pytest.raises(AssertionError, match="ledger counts differ"):
            script.check_b0_1_record(edited, counts, sets)

    extra = dict(sets)
    extra[("level_cells", "prime", "unpublished")] = (
        "persons",
        frozenset(),
        ((1, ("level_cells", "prime", "unpublished")),),
    )
    with pytest.raises(AssertionError, match="publishes no count"):
        script.check_b0_1_record(record, counts, extra)


def _prior_table(current, prior, sizes):
    """This release's rows and an earlier release's, over atoms of the
    given sizes; an earlier row carries its exact size."""
    units = {a: {(a, i) for i in range(sizes[a])} for a in range(len(sizes))}
    registry = script.SetRegistry()
    counts = {}
    for name, row in current.items():
        members = set().union(*(units[a] for a in row))
        registry.add((name,), "persons", members)
        counts[name] = len(members)
    for name, row in prior.items():
        members = set().union(*(units[a] for a in row))
        registry.add_prior((name,), "persons", members, len(members))
    return counts, registry


def test_an_earlier_exact_count_narrows_a_hidden_band():
    """Review round 3's attack in miniature. This release publishes ages
    45-61 (12 units, so 10-14) and ages 62-64 (2 units, "<10"); the
    earlier release published ages 45-64 exactly, 14. The small band can
    then be only 1 or 2, so the release is withheld. Without the earlier
    count the audit releases."""
    current = {"45_61": (0,), "62_64": (1,)}
    alone = script.audit_counts(*_prior_table(current, {}, [12, 2]), 10)
    assert alone["status"] == "released"
    audit = script.audit_counts(
        *_prior_table(current, {"45_64": (0, 1)}, [12, 2]), 10
    )
    assert audit["status"] == "withheld"
    (narrow,) = [
        t
        for t in audit["targets"]
        if t["result"] == "narrow" and 1 <= t["true_size"] <= 9
    ]
    assert narrow["true_size"] == 2


def test_earlier_sets_refine_atoms_but_set_no_targets_of_their_own():
    """An earlier set splits this release's set into two atoms, which stay
    one target. A difference against an earlier set is a target; one
    between two earlier sets, which that release fixed exactly, is not;
    and the earlier counts bound their rows exactly."""
    counts, registry = _prior_table(
        {"all": (0, 1, 2)},
        {"early": (0, 1), "earliest": (0,)},
        [11, 4, 5],
    )
    model = script.build_model(registry)
    assert model["matrix"].shape[1] == 3
    column = {int(model["sizes"][c]): c for c in range(3)}
    found = {
        (t["kind"], tuple(sorted(t["columns"]))): t for t in model["targets"]
    }
    assert ("atom", (0, 1, 2)) in found
    assert not any(
        kind == "atom" and len(columns) < 3 for kind, columns in found
    )
    assert ("difference", (column[5],)) in found  # all minus early
    assert ("difference", tuple(sorted((column[4], column[5])))) in found
    assert ("difference", (column[4],)) not in found  # early minus earliest
    lower, upper = script.published_bounds(counts, registry, model, 10)
    rows = model["path_rows"]
    assert (lower[rows[("early",)]], upper[rows[("early",)]]) == (15, 15)
    assert (lower[rows[("earliest",)]], upper[rows[("earliest",)]]) == (
        11,
        11,
    )
    assert (lower[rows[("all",)]], upper[rows[("all",)]]) == (15, 24)


def test_an_earlier_count_must_be_its_sets_size():
    counts, registry = _prior_table({"a": (0,)}, {}, [12])
    registry.add_prior(("b",), "persons", {(0, 0)}, 2)
    with pytest.raises(ValueError, match="earlier release's count"):
        script.audit_counts(counts, registry, 10)
    with pytest.raises(ValueError, match="duplicate"):
        registry.add_prior(("a",), "persons", set(), 0)


@st.composite
def _prior_atom_tables(draw):
    """An atom table whose rows are each this release's, an earlier
    release's, or both, with at least one of this release's."""
    rows, sizes = draw(_atom_tables())
    kinds = draw(
        st.lists(
            st.sampled_from(["current", "prior", "both"]),
            min_size=len(rows),
            max_size=len(rows),
        ).filter(lambda kinds: "prior" in kinds or "both" in kinds)
    )
    if all(kind == "prior" for kind in kinds):
        kinds[0] = "both"
    return rows, kinds, sizes


def _prior_registry(rows, kinds, sizes):
    current = {
        f"row_{j}": row
        for j, (row, kind) in enumerate(zip(rows, kinds, strict=True))
        if kind != "prior"
    }
    prior = {
        f"prior_{j}": row
        for j, (row, kind) in enumerate(zip(rows, kinds, strict=True))
        if kind != "current"
    }
    return _prior_table(current, prior, sizes)


def _oracle_prior_candidates(rows, kinds, sizes):
    """Every atom-size vector with the truth's publication: this release's
    rows coarsened, the earlier rows exact."""
    from itertools import product

    truth = [sum(sizes[a] for a in row) for row in rows]
    highest = [
        (
            max(
                v
                for v in range(100)
                if _oracle_coarsen(v) == _oracle_coarsen(t)
            )
            if kind == "current"
            else t
        )
        for t, kind in zip(truth, kinds, strict=True)
    ]
    caps = [
        min(highest[j] for j, row in enumerate(rows) if a in row)
        for a in range(len(sizes))
    ]
    grid = np.array(list(product(*(range(cap + 1) for cap in caps))))
    keep = np.ones(len(grid), dtype=bool)
    for row, t, kind in zip(rows, truth, kinds, strict=True):
        total = grid[:, list(row)].sum(axis=1)
        if kind != "current":
            keep &= total == t
        if kind != "prior":
            keep &= np.array(
                [_oracle_coarsen(int(v)) == _oracle_coarsen(t) for v in total]
            )
    return grid[keep]


def _oracle_prior_targets(rows, kinds, atoms):
    """This release's classes, and differences unless both sets are the
    earlier release's."""
    own = {}
    for a in range(atoms):
        signature = tuple(
            j
            for j, (row, kind) in enumerate(zip(rows, kinds, strict=True))
            if a in row and kind != "prior"
        )
        if signature:
            own.setdefault(signature, []).append(a)
    found = {tuple(sorted(group)) for group in own.values()}
    sets = [
        (frozenset(row), kind != "current")
        for row, kind in zip(rows, kinds, strict=True)
    ]
    for big, big_early in sets:
        for small, small_early in sets:
            if small and small < big and not (big_early and small_early):
                found.add(tuple(sorted(big - small)))
    return sorted(found)


@settings(max_examples=150, deadline=None)
@given(_prior_atom_tables())
@example(([(0, 1), (0,), (1,)], ["prior", "current", "current"], [12, 2]))
@example(([(0, 1), (0,), (1,)], ["both", "current", "prior"], [9, 7]))
def test_audit_with_earlier_counts_agrees_with_an_exhaustive_reader(table):
    """With an earlier release's exact counts among the constraints, the
    audit and the enumeration oracle reach the same targets, decision,
    disclosures and classifications. A reader who reruns the rule on
    every vector with both publications keeps exactly the final
    candidates, and every sensitive target spans 4 or more among them."""
    rows, kinds, sizes = table
    counts, registry = _prior_registry(rows, kinds, sizes)
    audit = script.audit_counts(counts, registry, 10)
    model = script.build_model(registry)
    matrix = model["matrix"].toarray()
    mapping = {}
    for c in range(matrix.shape[1]):
        member = {
            int(path[0].split("_")[1])
            for path, r in model["path_rows"].items()
            if matrix[r, c]
        }
        (mapping[c],) = [
            a
            for a in range(len(sizes))
            if {j for j, row in enumerate(rows) if a in row} == member
        ]
    grid = _oracle_prior_candidates(rows, kinds, sizes)
    targets = _oracle_prior_targets(rows, kinds, len(sizes))
    script_targets = {
        tuple(sorted(mapping[c] for c in t["columns"])): t
        for t in audit["targets"]
    }
    assert set(script_targets) == set(targets)
    status, disclosed, mask, classes = _oracle_release(
        rows, sizes, grid, targets
    )
    assert audit["status"] == status
    event(f"{status} after {len(audit['rounds'])} round(s)")
    if status != "released":
        return
    assert {
        tuple(sorted(mapping[c] for c in audit["targets"][i]["columns"]))
        for i in audit["disclosed"]
    } == set(disclosed)
    for target, result in classes.items():
        assert script_targets[target]["result"] == result, target
    kept = np.array(
        [
            _oracle_release(rows, list(point), grid, targets)[0] == "released"
            for point in grid
        ]
    )
    assert np.array_equal(kept, mask)
    for target in targets:
        if 1 <= sum(sizes[a] for a in target) <= 9:
            values = grid[kept][:, list(target)].sum(axis=1)
            assert values.max() - values.min() >= 4, target


@settings(max_examples=60, deadline=None)
@given(_prior_atom_tables(), st.data())
def test_programs_with_earlier_counts_depend_only_on_the_publications(
    table, data
):
    """Two tables with the same two publications and the same atoms hand
    the solver the same programs, up to the point where one withholds."""
    rows, kinds, sizes = table
    grid = _oracle_prior_candidates(rows, kinds, sizes)
    grid = grid[np.all(grid > 0, axis=1)]
    other = [int(v) for v in grid[data.draw(st.integers(0, len(grid) - 1))]]
    transcripts = []
    for vector in (sizes, other):
        counts, registry = _prior_registry(rows, kinds, vector)
        transcript = []
        original = script.AuditSystem._program

        def recording(
            self,
            objective,
            extra,
            seconds,
            integral=True,
            gap=0.0,
            transcript=transcript,
            original=original,
        ):
            parts = [np.asarray(objective, dtype=float).tobytes()]
            for constraint in (self.constraint, *extra):
                matrix = constraint.A
                if hasattr(matrix, "toarray"):
                    matrix = matrix.toarray()
                for array in (matrix, constraint.lb, constraint.ub):
                    parts.append(np.asarray(array, dtype=float).tobytes())
            transcript.append(hashlib.sha256(b"|".join(parts)).hexdigest())
            return original(self, objective, extra, seconds, integral, gap)

        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(script.AuditSystem, "_program", recording)
            audit = script.audit_counts(counts, registry, 10)
        transcripts.append((transcript, audit["status"]))
    (first, first_status), (second, second_status) = transcripts
    shorter = min(len(first), len(second))
    assert first[:shorter] == second[:shorter]
    if first_status == second_status == "released":
        assert first == second


def _b2_heads(persons, older):
    """Invented B2 heads at 2011, ``older`` of them aged 62 and the rest 60,
    each with a household, stratum and cluster of their own."""
    return _own_strata(
        _inputs(
            [
                _row(person, age=62 if person <= older else 60)
                for person in range(1, persons + 1)
            ]
        )
    )


@pytest.mark.parametrize(
    ("persons", "splits"), [(97, (1, 2)), (5, (1, 2, 3, 4))]
)
def test_b0_1_counts_enter_the_audit_through_main(
    tmp_path, monkeypatch, persons, splits
):
    """Review round 3's executed attack. B0.1 publishes the B2 heads aged
    45-64 exactly, the same for every split between ages 60 and 62. With
    97 heads, this release would publish ages 45-61 as 100 (95-104) and
    62-64 as "<10", leaving 62-64 only 1 or 2; with five, both bands
    "<10", leaving 1 to 4. Through main(), every split now withholds, and
    the committed files are identical. Without B0.1's counts in the
    audit, the same tables release."""
    publications = set()
    for older in splits:
        directory = tmp_path / str(older)
        directory.mkdir()
        _main_environment(directory, monkeypatch, _b2_heads(persons, older))
        out = directory / "counts.json"
        local = directory / "local.json"
        assert (
            script.main(["--out", str(out), "--local-copy", str(local)]) == 0
        )
        record = json.loads(out.read_text())
        assert record["disclosure"]["status"] == "withheld"
        assert "counts" not in record
        publications.add(out.read_bytes())
        audit = json.loads(local.read_text())["disclosure_audit"]["audit"]
        # The audit stops at the first sensitive narrow target: a band of
        # the split, 62-64 (``older``) or, with five heads, 45-61 too.
        assert any(
            t["result"] == "narrow"
            and t["true_size"] in {older, persons - older}
            and 1 <= t["true_size"] < script.DISCLOSURE_THRESHOLD
            for t in audit["targets"]
        )
    assert len(publications) == 1
    people, labor, anchor, design = _b2_heads(persons, splits[0])
    validity = _validity(labor)
    released = script.release_counts(
        script.structural_counts(people, validity, anchor, design),
        script.disclosure_registry(people, validity, anchor, design),
    )
    assert released[1]["status"] == "released"


def test_main_stops_when_b0_1_counts_differ_from_the_inputs(
    tmp_path, invented_main
):
    _, baseline, _ = invented_main
    record = json.loads(baseline.read_text())
    record["counts"]["domain_by_role"]["head"] += 1
    baseline.write_text(json.dumps(record))
    out = tmp_path / "counts.json"
    local = tmp_path / "local.json"
    with pytest.raises(AssertionError, match="rerun on these inputs"):
        script.main(["--out", str(out), "--local-copy", str(local)])
    assert not out.exists() and not local.exists()


# --------------------------------------------------------------------------
# An emptied pool, the seed directions and the directory flush
# --------------------------------------------------------------------------
def test_an_empty_pool_proves_nothing_and_runs_no_program():
    def fail(*args, **kwargs):
        raise AssertionError("no program may run")

    system = SimpleNamespace(
        relaxed_minimum=fail, search=fail, extreme=fail, direction=fail
    )
    record, witness = script.classify(
        system,
        {"columns": (0,), "true_size": 3},
        script.WitnessPool(2),
        seconds=60,
    )
    assert record == {
        "programs": [],
        "result": "narrow",
        "proof": "undetermined",
    }
    assert witness is None


def _emptied_pool(monkeypatch, reseeds):
    """Two atoms: a (10 units) and b (3), published as a + b (13, so
    10-14) and b ("<10"). The solver stub hands the first seeding the
    points (6, 8) and (9, 1), which give b sizes 7 apart, and times out
    every search, so a (true size 10) is narrow in round 1 and is
    disclosed. That rules out both points. The second seeding gets
    ``reseeds``."""
    counts = {"total": 13, "small": 3}
    registry = script.SetRegistry()
    registry.add(("total",), "persons", range(13))
    registry.add(("small",), "persons", range(10, 13))
    model = script.build_model(registry)
    a = int(np.flatnonzero(model["sizes"] == 10)[0])
    b = 1 - a

    def point(av, bv):
        p = np.zeros(2)
        p[a], p[b] = av, bv
        return p

    first = [point(6, 8), point(9, 1)]
    later = [point(*values) for values in reseeds]
    calls = []

    def stub(self, objective, extra, seconds, integral=True, gap=0.0):
        if extra:
            calls.append("search")
            return SimpleNamespace(x=None, status=1, fun=None)
        seeding = sum(c == "seed" for c in calls) // (
            1 + script.POOL_DIRECTIONS
        )
        calls.append("seed")
        points = first if seeding == 0 else later
        if not points:
            return SimpleNamespace(x=None, status=1, fun=None)
        return SimpleNamespace(
            x=points[len(calls) % len(points)], status=1, fun=0.0
        )

    monkeypatch.setattr(script.AuditSystem, "_program", stub)
    return counts, registry, calls


def test_disclosures_that_empty_the_pool_seed_it_again(monkeypatch):
    """Round 2 starts with no point left, so the nine seed programs run
    again under the disclosure, and their points classify b: with a at
    least 10, b is 1 to 4, so it is narrow and the release is withheld.
    The pool keeps each seed program's point, repeats included."""
    counts, registry, calls = _emptied_pool(monkeypatch, [(10, 4), (12, 1)])
    audit = script.audit_counts(counts, registry, 10)
    assert calls.count("seed") == 2 * (1 + script.POOL_DIRECTIONS)
    assert [r["reseeded"] for r in audit["rounds"]] == [False, True]
    assert audit["pool"] == 1 + script.POOL_DIRECTIONS
    assert audit["status"] == "withheld"
    small = [t for t in audit["targets"] if t["true_size"] == 3]
    assert small and small[0]["round"] == 2 and small[0]["programs"]


def test_an_empty_reseeding_withholds_with_complete_files(
    tmp_path, monkeypatch
):
    """Review round 3's crash: when the disclosures rule out every point
    and seeding again finds none, main() completes, writing both files,
    and the release is withheld."""
    counts, registry, calls = _emptied_pool(monkeypatch, [])
    _main_environment(tmp_path, monkeypatch, _b2_heads(12, 0))
    # main() reads and checks the invented panel as usual; its audit is
    # the two-atom table whose second seeding finds nothing.
    real_release = script.release_counts
    monkeypatch.setattr(
        script, "release_counts", lambda *args: real_release(counts, registry)
    )
    out = tmp_path / "counts.json"
    local = tmp_path / "local.json"
    assert script.main(["--out", str(out), "--local-copy", str(local)]) == 0
    record = json.loads(out.read_text())
    assert record["disclosure"]["status"] == "withheld"
    audit = json.loads(local.read_text())["disclosure_audit"]["audit"]
    assert audit["pool"] == 0
    assert audit["rounds"][-1] == {
        "round": 2,
        "disclosed": [],
        "reseeded": True,
    }
    assert calls.count("seed") == 2 * (1 + script.POOL_DIRECTIONS)


def test_seed_directions_come_from_the_fixed_seed(monkeypatch):
    """The nine seed programs push along zero, then eight directions drawn
    from a generator seeded with 20261024, the same at every seeding."""
    seen = []

    def direction(self, weights, *, seconds):
        seen.append(np.asarray(weights).copy())

    monkeypatch.setattr(script.AuditSystem, "direction", direction)
    counts, registry = _atom_table(
        [(0, 1, 2, 3, 4), (0,), (1,), (2,), (3,)], [11, 12, 13, 14, 15]
    )
    model = script.build_model(registry)
    lower, upper = script.published_bounds(counts, registry, model, 10)
    system = script.AuditSystem(model, lower, upper, [], [])
    for _ in range(2):
        script.seed_pool(system, script.WitnessPool(5), seconds=1)
    generator = np.random.default_rng(20261024)
    expected = [np.zeros(5)] + [
        generator.choice([-1.0, 1.0], size=5) for _ in range(8)
    ]
    assert len(seen) == 18
    for got, want in zip(seen, expected + expected, strict=True):
        assert np.array_equal(got, want)


def test_write_new_flushes_the_directory_after_linking(tmp_path, monkeypatch):
    import stat

    flushed = []
    real = os.fsync
    path = tmp_path / "out.json"

    def fsync(descriptor):
        flushed.append(
            (stat.S_ISDIR(os.fstat(descriptor).st_mode), path.exists())
        )
        real(descriptor)

    monkeypatch.setattr(script.os, "fsync", fsync)
    script.write_new(path, b"{}\n")
    assert flushed == [(False, False), (True, True)]


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
            # A stratum per person: six persons in one design cluster
            # would pin that cluster's count, and the audit would withhold.
            "ER31996": person,
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
    published, disclosure, _ = script.release_counts(counts, registry)
    assert disclosure["status"] == "released" and published
