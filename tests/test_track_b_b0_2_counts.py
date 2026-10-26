"""B0.2's version-1 protocol, tested solely on invented frames."""

from __future__ import annotations

import hashlib
import json
import os
import socket
import sqlite3
import subprocess
import sys
import time
from collections import Counter
from contextlib import contextmanager, nullcontext
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

#: The script's own host calls, kept before any test replaces them.
REAL_HOST = script._Host
PROTOCOL_SHA256 = (
    "b1ac4bc03b8dda41e88b42fadbdd5e9fb0fb09a3e7b78c0e9613af7a3af1b7c9"
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


def _verdict_holds(verdict, oracle, values):
    """Whether the script's final verdict on one target agrees with the
    oracle's. Narrow, a disclosure, and exempt must match exactly. A
    target whose final candidates ``values`` span 4 or more and stay out
    of 1 to 9 is wide and irrelevant at once, and the script may prove
    either, so a wide or irrelevant verdict must hold of those
    candidates."""
    if {"narrow", "exempt"} & {verdict, oracle}:
        return verdict == oracle
    if verdict == "wide":
        return values.max() - values.min() >= 4
    return verdict == "irrelevant" and not np.any(
        (values >= 1) & (values <= 9)
    )


def _oracle_release(rows, sizes, grid, targets, earlier=None):
    """The rule by enumeration: status, disclosed targets, the final
    candidate mask and each target's final classification. ``earlier``
    maps a target to its least and greatest size under an earlier
    release's exact counts alone; a narrow target whose candidates give
    the same two is exempt, neither withholding nor disclosed."""
    values = {t: grid[:, list(t)].sum(axis=1) for t in targets}
    mask = np.ones(len(grid), dtype=bool)
    disclosed = []
    while True:
        classes = {
            t: _oracle_class(values[t][mask])
            for t in targets
            if t not in disclosed
        }
        for t, result in classes.items():
            here = values[t][mask]
            if result == "narrow" and (earlier or {}).get(t) == (
                int(here.min()),
                int(here.max()),
            ):
                classes[t] = "exempt"
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


@pytest.mark.parametrize("related", [True, False])
def test_the_audit_uses_the_relations_it_registers(related):
    """Twelve households, and eleven of them, are both published as 10, so
    alone the twelfth is anywhere from 0 to 4: wide. An earlier release
    fixed the twelve persons exactly, and there are at most as many
    households as persons, so with that relation the twelfth is 0 to 2:
    narrow, at true size 1, and the release is withheld. The relation is
    what withholds it."""
    households = {f"h{index}" for index in range(12)}
    persons = set(range(12))
    registry = script.SetRegistry()
    registry.add(("households",), "households_2011", households)
    registry.add(("eleven",), "households_2011", households - {"h11"})
    registry.add(("persons",), "persons", persons)
    registry.add_prior(("b0_1", "persons"), "persons", persons, 12)
    if related:
        registry.relate("at_most", ("households",), ("persons",))
    counts = {"households": 12, "eleven": 11, "persons": 12}
    audit = script.audit_counts(counts, registry)
    assert audit["relations"] == int(related)
    (twelfth,) = [
        target
        for target in audit["targets"]
        if target["unit_type"] == "households_2011"
        and target["true_size"] == 1
    ]
    if related:
        assert audit["status"] == "withheld"
        assert twelfth["result"] == "narrow"
        assert twelfth["range"] == [0, 2]
    else:
        assert audit["status"] == "released"
        assert twelfth["result"] == "wide"


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
        b'"class_sizes"',
        b'"true_size"',
        b'"targets"',
        b'"rounds"',
        b'"range"',
    ):
        assert forbidden not in public_bytes
    assert "class_sizes" in private["audit"]
    assert "atom_sizes" not in private["audit"]


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
    assert private["audit"]["class_sizes"] == {"persons": [3]}


def test_the_class_sizes_are_this_releases_classes_alone():
    """Nested sets of 30, 20 and 10 make three classes of 10, which
    partition the 30 units. Their outer difference (30 less 10) is a
    target of its own, as no class holds exactly its units, but it is not
    a class: the local copy's class sizes leave it out and sum to 30."""
    counts, registry = _table_registry(
        {
            "outer": set(range(30)),
            "middle": set(range(20)),
            "inner": set(range(10)),
        }
    )
    audit = script.audit_counts(counts, registry, 10)
    assert any(
        target["kind"] == "difference" and target["true_size"] == 20
        for target in audit["targets"]
    )
    class_sizes = script.local_audit(audit)["class_sizes"]
    assert class_sizes == {"persons": [10, 10, 10]}
    assert sum(class_sizes["persons"]) == len(registry.sets[("outer",)][1])


@settings(max_examples=100, deadline=None)
@given(_atom_tables())
@example(([(0, 1), (0,), (1,)], [9, 7]))
@example(([(0, 1), (0,), (1,)], [10, 1]))
def test_audit_agrees_with_an_exhaustive_reader(table):
    """The integer-program audit and the enumeration oracle reach the same
    decision and disclosures, and every other verdict the audit gives holds
    of the final candidates (``_verdict_holds``). Then the oracle checks the
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
        assert _verdict_holds(
            script_targets[target]["result"],
            result,
            grid[mask][:, list(target)].sum(axis=1),
        ), target
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
    return _audit_transcript(*_atom_table(rows, sizes))


def _audit_transcript(counts, registry):
    """Every program the audit hands the solver for these counts, in order,
    the exemption's included, with the audit's record."""
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


def test_programs_use_one_thread_the_time_limit_and_exact_optima(monkeypatch):
    calls = []
    original = script.milp

    def recording(objective, **kwargs):
        # A copy: milp pops "disp" from the dict it is given.
        calls.append(dict(kwargs["options"]))
        return original(objective, **kwargs)

    monkeypatch.setattr(script, "milp", recording)
    counts, registry = _atom_table([(0, 1), (0,)], [3, 9])
    audit = script.audit_counts(counts, registry, 10)
    assert audit["status"] == "released" and calls
    assert all(call["threads"] == 1 for call in calls)
    assert script.PROGRAM_SECONDS == 300
    assert all(call["time_limit"] == 300 for call in calls)
    # HiGHS prints nothing: a solver log could carry atom sizes.
    assert all(call["disp"] is False for call in calls)
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
    assert script.audit_counts(counts, registry, 10)["pool"] == 0
    assert "pool" not in private["audit"]


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


class _FakeHost:
    """Stands in for the macOS calls behind the run's conditions: a host on
    AC power, at nice 0 with no background policy or QoS clamp, nearly
    idle, whose sleep assertions are held until released or set off.

    ``plan`` scripts the conditions check by check: each call of
    ``RunConditions.failing`` reads the next entry, a condition's name to
    make it fail at that check, or None; an empty plan fails nothing."""

    def __init__(self, *, power=None, state=None, refuse=False, plan=()):
        self.power = script.AC_POWER if power is None else power
        self.state = (0, 0, 0x21, 1.0, 18) if state is None else state
        self.refuse = refuse
        self.plan = list(plan)
        self.live = set()
        self.off = set()
        self.holds = []
        self.checks = []
        self.next_id = 1

    def read_state(self):
        """One check's reads, as the plan makes them."""
        name = self.plan.pop(0) if self.plan else None
        self.checks.append(name)
        power, state = self.power, self.state
        if name == "ac_power":
            power = "Battery Power"
        elif name == "sleep_assertions":
            self.live.clear()
        elif name in ("nice", "background", "qos", "load"):
            index = {"nice": 0, "background": 1, "qos": 2, "load": 3}[name]
            value = {"nice": 10, "background": 1, "qos": 0x09, "load": 18.0}
            state = tuple(
                value[name] if i == index else v for i, v in enumerate(state)
            )
        self.read_power = power
        return state

    def power_source(self):
        return self.read_power

    def hold(self, kind):
        if self.refuse:
            return 0
        assertion, self.next_id = self.next_id, self.next_id + 1
        self.live.add(assertion)
        self.holds.append(kind)
        return assertion

    def held(self, assertion):
        return assertion in self.live - self.off

    def release(self, assertion):
        self.live.discard(assertion)

    def qos_class(self):
        return self.state[2]


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
    # A host whose run conditions all hold, with stand-in assertions.
    monkeypatch.setattr(script, "_Host", _FakeHost)
    monkeypatch.setattr(script, "_host_state", _FakeHost.read_state)
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
    # The local audit holds no timing, so all of it is reproducible.
    assert local_record["disclosure_audit"] == local_audit
    assert local_record["repository_head"] == record["repository_head"]
    assert record["geometry"]["collection_waves"] == list(WAVES)
    assert record["geometry"]["reference_years"] == [
        wave - 1 for wave in WAVES
    ]
    assert record["geometry"]["age_convention"] == "collection_wave"
    assert record["geometry"]["lag_years"] == [2, 4]
    _assert_no_forbidden_output(record)


#: Every provenance field the committed file may hold: the requested shape,
#: fixed before any count (labels, dimensions and unit types), and SHA-256
#: hashes of inputs and code.
COMMITTED_PROVENANCE = {
    "schema",
    "repository_head",
    "worktree_clean",
    "requested_label_allowlist",
    "geometry",
    "script_sha256",
    "b0_1_counts_sha256",
    "psid_files_opened_sha256",
}


def test_committed_provenance_is_the_requested_shape_and_input_hashes(
    tmp_path, released_main
):
    """Provenance goes into the committed file, so it holds only the shape
    the run requested, fixed before any count, and hashes of inputs and
    code. A hash of the local copy, the attempt record or any other file
    holding a figure that is not committed could be inverted by
    enumerating the values the coarsened counts leave open, so no such
    hash appears in either file."""
    import re

    supplied, baseline, _ = released_main
    out = tmp_path / "counts.json"
    local = tmp_path / "local.json"
    assert script.main(["--out", str(out), "--local-copy", str(local)]) == 0
    record = json.loads(out.read_text())
    assert record["disclosure"]["status"] == "released"
    assert set(record) == COMMITTED_PROVENANCE | {"counts", "disclosure"}
    local_record = json.loads(local.read_text())
    assert set(local_record) == COMMITTED_PROVENANCE | {
        "counts",
        "disclosure_audit",
    }
    # The geometry is the requested shape, set by constants before any
    # count; the labels are the ones the run requested.
    assert record["geometry"] == {
        "collection_waves": list(script.WAVES),
        "reference_years": [wave - 1 for wave in script.WAVES],
        "age_convention": "collection_wave",
        "lag_years": list(script.LAGS),
    }
    assert record["requested_label_allowlist"] == supplied[-1]
    # Every hash either file holds is of an input or of code.
    inputs_and_code = {
        hashlib.sha256(Path(script.__file__).read_bytes()).hexdigest(),
        hashlib.sha256(baseline.read_bytes()).hexdigest(),
        "a" * 64,  # the invented input file's recorded hash
    }
    written = out.read_text() + local.read_text()
    hashes = set(re.findall(r"\b[0-9a-f]{64}\b", written))
    assert hashes == inputs_and_code
    uncommitted = {
        hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (local, script._attempt_path(local))
    }
    assert not uncommitted & hashes


def _nested_prior_release(died):
    """B0.2 publishes 30 persons and 20 of them; B0.1 counted ``died``, 12
    of the 20, exactly."""
    counts = {"total": 30, "part": 20}
    registry = script.SetRegistry()
    registry.add(("total",), "persons", range(30))
    registry.add(("part",), "persons", range(20))
    registry.add_prior(("b0_1", "died"), "persons", died, 12)
    return script.release_counts(counts, registry), registry, counts


def test_the_local_copy_writes_nothing_of_b0_1_sets_beyond_their_counts():
    """Which 12 of the 20 B0.1 counted is B0.1's to know, and the local
    copy must not say: it is the same for both splits. The audit itself
    holds the targets that involve B0.1's set; the local copy leaves them
    out, writes nothing about the rounds, and gives this release's class
    sizes rather than the atoms that B0.1's set refines."""
    records = []
    for died in (range(5, 17), range(12)):
        (_, disclosure, private), registry, counts = _nested_prior_release(
            died
        )
        assert disclosure["status"] == "released"
        full = script.audit_counts(counts, registry, 10)
        hidden = [t for t in full["targets"] if t["earlier"]]
        assert hidden and all(t["kind"] == "difference" for t in hidden)
        local = private["audit"]
        assert sorted(local["class_sizes"]["persons"]) == [10, 20]
        assert len(local["targets"]) == len(full["targets"]) - len(hidden)
        for target in local["targets"]:
            assert "columns" not in target and "earlier" not in target
        assert "rounds" not in local and "disclosed" not in local
        text = json.dumps(local, sort_keys=True)
        assert "b0_1" not in text and "died" not in text
        records.append(text)
    assert records[0] == records[1]


def test_a_small_b0_1_cell_that_is_a_b0_2_set_withholds(tmp_path, monkeypatch):
    """B0.1 counts the plain release panel's domain persons under 25
    exactly, as five, and that set is also B0.2's 1-24 band of R_FULL.
    The band's classes of persons are then exempt, since B0.1's counts
    already fix them. Its strata and clusters, five of each, are not:
    B0.1 counts neither, and this release's counts, B0.1's and the
    relations across unit types leave each 2 to 5. Through main() the
    release is withheld at the band's clusters; the same panel releases
    when B0.1's counts are left out of the audit."""
    inputs = _release_panel()
    _main_environment(tmp_path, monkeypatch, inputs)
    out = tmp_path / "counts.json"
    local = tmp_path / "local.json"
    assert script.main(["--out", str(out), "--local-copy", str(local)]) == 0
    assert json.loads(out.read_text())["disclosure"]["status"] == "withheld"
    (narrow,) = [
        t
        for t in json.loads(local.read_text())["disclosure_audit"]["audit"][
            "targets"
        ]
        if t["result"] == "narrow"
    ]
    assert (narrow["unit_type"], narrow["true_size"]) == ("clusters", 5)
    assert (
        "rosters",
        "R_FULL",
        "by_age_band",
        "1_24",
        "design_clusters",
    ) in [tuple(path) for path in narrow["sets"]]
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


def _household_prior_panel():
    """Review round 4's table: 122 heads and spouses at 2011, 120 aged 50
    in 96 households (24 with a spouse), and two heads aged 63 in
    households of their own."""
    rows = []
    person = 0
    for household in range(1, 97):
        person += 1
        rows.append(_row(person, age=50, interview=household))
        if household <= 24:
            person += 1
            rows.append(
                _row(person, age=50, relationship=20, interview=household)
            )
    for household in (201, 202):
        person += 1
        rows.append(_row(person, age=63, interview=household))
    return _own_strata(_inputs(rows))


def test_b0_1s_exact_household_count_withholds_a_small_bands_households(
    tmp_path, monkeypatch
):
    """Review round 4's executed attack on B0.1's household sets. B0.1
    publishes the anchor's 122 persons and 98 households exactly; this
    release publishes the 45-61 band as 120 persons (115-124) in 96
    households (95-104) and the 62-64 band "<10". The small band's persons
    can then be 1 to 7, which is wide, but its households only 1 to 3 once
    B0.1's household count is in the audit. Through main() the release is
    withheld on that class; without B0.1's household sets, the same table
    releases."""
    inputs = _household_prior_panel()
    people, labor, anchor, design = inputs
    validity = _validity(labor)
    earlier = b01.structural_counts(people, validity)
    assert earlier["full_anchor_persons"] == 122
    assert earlier["full_anchor_households"] == 98
    counts = script.structural_counts(people, validity, anchor, design)
    bands = counts["rosters"]["R_FULL"]["by_age_band"]
    assert (bands["45_61"]["persons"], bands["45_61"]["households"]) == (
        120,
        96,
    )
    assert (bands["62_64"]["persons"], bands["62_64"]["households"]) == (2, 2)
    _main_environment(tmp_path, monkeypatch, inputs)
    out = tmp_path / "counts.json"
    local = tmp_path / "local.json"
    assert script.main(["--out", str(out), "--local-copy", str(local)]) == 0
    assert json.loads(out.read_text())["disclosure"]["status"] == "withheld"
    audit = json.loads(local.read_text())["disclosure_audit"]["audit"]
    assert [
        (t["unit_type"], t["true_size"])
        for t in audit["targets"]
        if t["result"] == "narrow"
        and 1 <= t["true_size"] < script.DISCLOSURE_THRESHOLD
    ] == [("households_2011", 2)]
    registry = script.disclosure_registry(people, validity, anchor, design)
    persons_only = {
        path: entry
        for path, entry in script.b0_1_sets(people, validity).items()
        if entry[0] == "persons"
    }
    script.register_b0_1(registry, persons_only, earlier)
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
    with pytest.raises(SystemExit, match="AssertionError: R_B2 size differs"):
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
    with pytest.raises(SystemExit, match="write_new, line .*FileExistsError$"):
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
    with pytest.raises(SystemExit, match="write_new, line .*FileExistsError$"):
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
    # The message came from outside this script, so only its type is told.
    with pytest.raises(SystemExit, match="main, line .*: OSError$"):
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


def _main_args(tmp_path):
    return [
        "--out",
        str(tmp_path / "counts.json"),
        "--local-copy",
        str(tmp_path / "local.json"),
    ]


@pytest.mark.parametrize(
    ("host", "name"),
    [
        (_FakeHost(power="Battery Power"), "ac_power"),
        (_FakeHost(power=""), "ac_power"),
        (_FakeHost(refuse=True), "sleep_assertions"),
        (_FakeHost(state=(10, 0, 0x21, 1.0, 18)), "nice"),
        (_FakeHost(state=(0, 1, 0x21, 1.0, 18)), "background"),
        (_FakeHost(state=(0, 0, 0x11, 1.0, 18)), "qos"),
        (_FakeHost(state=(0, 0, 0x09, 1.0, 18)), "qos"),
        (_FakeHost(state=(0, 0, 0x05, 1.0, 18)), "qos"),
        (_FakeHost(state=(0, 0, 0x14, 1.0, 18)), "qos"),
        (_FakeHost(state=(0, 0, 0x01, 1.0, 18)), "qos"),
        (_FakeHost(state=(0, 0, 0x21, 18.0, 18)), "load"),
        (_FakeHost(state=(0, 0, 0x21, 40.5, 18)), "load"),
    ],
)
def test_runtime_refuses_to_start_unless_every_run_condition_holds(
    host, name, tmp_path, monkeypatch, invented_main
):
    """Each program's limit is wall-clock time, so the run refuses to start
    off AC power, without its sleep assertions, deprioritized (niceness,
    the Darwin background policy or a QoS clamp) or on a busy host: before
    any attempt record, so the version is not spent, and before any read.
    The assertions it took are given back."""
    _, _, calls = invented_main
    monkeypatch.setattr(script, "_Host", lambda: host)
    with pytest.raises(SystemExit) as caught:
        script.main(_main_args(tmp_path))
    assert str(caught.value) == (
        f"B0.2 refuses to start: run condition {name} fails"
    )
    assert not calls
    assert not script._attempt_path(tmp_path / "local.json").exists()
    assert not host.live


def test_an_assertion_at_the_off_level_is_given_back_and_taken_again(
    monkeypatch,
):
    """An assertion can exist at the off level, where it no longer
    prevents sleep (review round 5). The check counts it as not held,
    gives it back and takes a new one, and the other is kept."""
    monkeypatch.setattr(script, "_host_state", _FakeHost.read_state)
    host = _FakeHost()
    conditions = script.RunConditions(host)
    first = dict(conditions.assertions)
    host.off.add(first["PreventSystemSleep"])
    assert conditions.failing() is None
    assert first["PreventSystemSleep"] not in host.live
    assert conditions.assertions["PreventSystemSleep"] in host.live
    assert conditions.assertions["PreventUserIdleSystemSleep"] == (
        first["PreventUserIdleSystemSleep"]
    )
    assert host.holds == [*script.SLEEP_ASSERTIONS, "PreventSystemSleep"]


@pytest.mark.parametrize("qos", [0x00, 0x15, 0x19, 0x21])
def test_unclamped_qos_classes_meet_the_run_conditions(qos, monkeypatch):
    """Unspecified, default, user-initiated and user-interactive QoS all
    run at full speed; every class below the default fails, an unknown one
    included (the refusal cases above)."""
    monkeypatch.setattr(script, "_host_state", _FakeHost.read_state)
    host = _FakeHost(state=(0, 0, qos, 1.0, 18))
    assert script.RunConditions(host).failing() is None


def test_host_state_reads_niceness_darwin_priority_qos_load_and_cpus(
    monkeypatch,
):
    priorities = {
        (script.os.PRIO_PROCESS, 0): 7,
        (script.PRIO_DARWIN_PROCESS, 0): 1,
    }
    monkeypatch.setattr(
        script.os, "getpriority", lambda which, who: priorities[which, who]
    )
    monkeypatch.setattr(script.os, "getloadavg", lambda: (1.0, 2.0, 3.0))
    monkeypatch.setattr(script.os, "cpu_count", lambda: 18)
    host = SimpleNamespace(qos_class=lambda: 0x11)
    assert script._host_state(host) == (7, 1, 0x11, 2.0, 18)


def test_main_holds_its_sleep_assertions_from_before_the_attempt_to_the_end(
    tmp_path, monkeypatch, invented_main
):
    """The sleep assertions are taken before the attempt record, so a host
    that cannot hold them spends no version; both are held through every
    program and given back once both files are written."""
    local = tmp_path / "local.json"
    out = tmp_path / "counts.json"
    host = _FakeHost()
    events = []
    hold, release = host.hold, host.release

    def holding(kind):
        events.append(("hold", kind, script._attempt_path(local).exists()))
        return hold(kind)

    def releasing(assertion):
        events.append(("release", out.exists() and local.exists()))
        release(assertion)

    host.hold, host.release = holding, releasing
    held = []
    real_milp = script.milp

    def milp(*arguments, **options):
        held.append(len(host.live))
        return real_milp(*arguments, **options)

    monkeypatch.setattr(script, "_Host", lambda: host)
    monkeypatch.setattr(script, "milp", milp)
    assert script.main(_main_args(tmp_path)) == 0
    assert events == [
        ("hold", "PreventUserIdleSystemSleep", False),
        ("hold", "PreventSystemSleep", False),
        ("release", True),
        ("release", True),
    ]
    assert held and set(held) == {2}
    assert not host.live


@pytest.mark.parametrize("missing", ["library", "symbol"])
def test_main_refuses_without_iokit_before_the_attempt(
    missing, tmp_path, monkeypatch, invented_main
):
    _, _, calls = invented_main

    def cdll(name):
        if missing == "library":
            raise OSError(f"dlopen({name}) failed")
        return SimpleNamespace()

    monkeypatch.setattr(script, "_Host", REAL_HOST)
    monkeypatch.setattr(script.ctypes, "CDLL", cdll)
    with pytest.raises(SystemExit) as caught:
        script.main(_main_args(tmp_path))
    assert str(caught.value) == "B0.2 needs macOS IOKit for its run conditions"
    assert caught.value.__cause__ is None
    assert not calls
    assert not script._attempt_path(tmp_path / "local.json").exists()


@pytest.mark.skipif(sys.platform != "darwin", reason="IOKit is macOS's")
def test_the_host_calls_read_this_mac():
    """On the host that runs B0.2: the power source reads, both sleep
    assertions are held until released, and the QoS class and Darwin
    priority read."""
    host = REAL_HOST()
    assert isinstance(host.power_source(), str) and host.power_source()
    assertions = [host.hold(kind) for kind in script.SLEEP_ASSERTIONS]
    try:
        assert all(assertions) and len(set(assertions)) == 2
        assert all(host.held(assertion) for assertion in assertions)
    finally:
        for assertion in assertions:
            host.release(assertion)
    assert not any(host.held(assertion) for assertion in assertions)
    assert not host.held(0)
    assert script.PRIO_DARWIN_PROCESS == getattr(
        os, "PRIO_DARWIN_PROCESS", script.PRIO_DARWIN_PROCESS
    )
    niceness, background, qos, load, cpus = script._host_state(host)
    assert background in (0, 1) and cpus >= 1 and load >= 0
    assert qos in (0x00, 0x05, 0x09, 0x11, 0x15, 0x19, 0x21)


class _CoreFoundationLedger:
    """Stands in for IOKit, CoreFoundation and the C library behind
    ``_Host``, and keeps the ownership rule's ledger: a handle that a
    Create or Copy call returns is owned until ``CFRelease`` gives it back,
    and one that a Get call returns is borrowed and is never released."""

    def __init__(self, *, source, properties, level):
        self.source, self.properties, self.level = source, properties, level
        self.owned, self.borrowed_released = set(), []
        self.next_handle = 1

    def _create(self):
        handle, self.next_handle = self.next_handle, self.next_handle + 1
        self.owned.add(handle)
        return handle

    def CFStringCreateWithCString(self, allocator, text, encoding):
        return self._create()

    def CFStringGetCString(self, string, buffer, size, encoding):
        buffer.value = script.AC_POWER.encode()
        return True

    def CFRelease(self, handle):
        if handle in self.owned:
            self.owned.remove(handle)
        else:
            self.borrowed_released.append(handle)

    def CFDictionaryGetValue(self, dictionary, key):
        return -1

    def CFNumberGetValue(self, number, kind, pointer):
        pointer._obj.value = self.level
        return True

    def IOPSCopyPowerSourcesInfo(self):
        return self._create() if self.source else None

    def IOPSGetProvidingPowerSourceType(self, snapshot):
        return -2

    def IOPMAssertionCreateWithName(self, kind, level, name, pointer):
        pointer._obj.value = 77
        return 0

    def IOPMAssertionCopyProperties(self, assertion):
        return self._create() if self.properties else None

    def IOPMAssertionRelease(self, assertion):
        return 0


@pytest.mark.parametrize("level", [script._ASSERTION_ON, 0])
@pytest.mark.parametrize("properties", [True, False])
@pytest.mark.parametrize("source", [True, False])
def test_the_host_calls_give_back_every_object_they_own(
    source, properties, level
):
    """CoreFoundation's ownership rule, on every path through the host
    calls: the power-source snapshot, the strings and the copied
    properties are each given back, and the borrowed power-source name and
    level are not (review round 5 found the properties' release untested).
    An assertion counts as held only when its properties are copied and
    its level is on."""
    ledger = _CoreFoundationLedger(
        source=source, properties=properties, level=level
    )
    host = REAL_HOST.__new__(REAL_HOST)
    host.iokit = host.cf = host.libc = ledger
    assert host.power_source() == (script.AC_POWER if source else "")
    assert host.hold("PreventSystemSleep") == 77
    assert host.held(77) is (properties and level == script._ASSERTION_ON)
    assert host.held(0) is False
    assert ledger.owned == set()
    assert ledger.borrowed_released == []


@pytest.mark.skipif(sys.platform != "darwin", reason="IOKit is macOS's")
def test_an_assertion_set_to_the_off_level_reads_as_not_held():
    """Review round 5 set one of this process's assertions to the off
    level, which IOKit lets its owner do: it still exists, but no longer
    prevents sleep, so ``held`` reads it as not held."""
    import ctypes

    host = REAL_HOST()
    set_property = host.iokit.IOPMAssertionSetProperty
    set_property.argtypes = [ctypes.c_uint32, ctypes.c_void_p, ctypes.c_void_p]
    set_property.restype = ctypes.c_int
    create_number = host.cf.CFNumberCreate
    create_number.argtypes = [ctypes.c_void_p, ctypes.c_long, ctypes.c_void_p]
    create_number.restype = ctypes.c_void_p
    key = host.cf.CFStringCreateWithCString(None, b"AssertLevel", script._UTF8)
    off = ctypes.c_int32(0)
    number = create_number(None, script._SINT32, ctypes.byref(off))
    assertion = host.hold("PreventUserIdleSystemSleep")
    try:
        assert key and number and assertion
        assert host.held(assertion)
        assert set_property(assertion, key, number) == 0
        assert not host.held(assertion)
    finally:
        host.release(assertion)
        host.cf.CFRelease(number)
        host.cf.CFRelease(key)


@pytest.mark.skipif(
    not Path("/usr/sbin/taskpolicy").exists(), reason="no taskpolicy here"
)
@pytest.mark.parametrize(
    ("policy", "name"),
    [(["-b"], "background"), (["-c", "background"], "qos")],
)
def test_the_host_reads_see_a_background_policy_and_a_qos_clamp(policy, name):
    """Review round 4 measured the Darwin background policy slowing a CPU
    loop that niceness 0 let pass; a QoS clamp (``taskpolicy -c``) leaves
    the Darwin priority at 0 too. Under each, the real reads give the
    failing value."""
    code = (
        "import sys; sys.path.insert(0, 'scripts'); "
        "import track_b_b0_2_counts as s; "
        "print(list(s._host_state(s._Host())[:3]))"
    )
    run = subprocess.run(
        ["/usr/sbin/taskpolicy", *policy, sys.executable, "-c", code],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        env={
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": f"{ROOT / 'src'}:{ROOT}",
        },
    )
    niceness, background, qos = json.loads(run.stdout.strip().splitlines()[-1])
    if name == "background":
        assert background == 1
    else:
        assert background == 0 and qos == 0x09


def _audit_without_time(audit):
    return {key: value for key, value in audit.items() if key != "seconds"}


def test_the_run_conditions_are_checked_before_every_program(
    tmp_path, monkeypatch, invented_main
):
    """Through main(): after the start check, every program is preceded by
    a full check of the run conditions, and none runs during one."""
    host = _FakeHost()
    events = []
    real_milp = script.milp
    read_state = _FakeHost.read_state

    def checking(checked):
        events.append("check")
        return read_state(checked)

    def milp(*arguments, **options):
        events.append("program")
        return real_milp(*arguments, **options)

    monkeypatch.setattr(script, "_Host", lambda: host)
    monkeypatch.setattr(script, "_host_state", checking)
    monkeypatch.setattr(script, "milp", milp)
    assert script.main(_main_args(tmp_path)) == 0
    assert events[0] == "check" and "program" in events
    assert events[1:] == ["check", "program"] * (len(events[1:]) // 2)


@settings(max_examples=40, deadline=None)
@given(st.data())
def test_a_failed_condition_is_waited_out_and_changes_no_decision(data):
    """Whatever conditions fail before whichever programs, for fewer
    rechecks than the bound, the audit is the same, every program runs
    after a check that passed, each failed check costs one recheck a
    minute later, and a lapsed sleep assertion is taken again."""
    counts, registry, _ = _two_atom_disclosure()
    programs = []
    real_milp = script.milp

    def milp(*arguments, **options):
        programs.append(None)
        return real_milp(*arguments, **options)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(script, "milp", milp)
        unchecked = script.audit_counts(counts, registry, 10)
    plan = []
    for _ in programs:
        plan.extend(
            data.draw(
                st.lists(st.sampled_from(script.RUN_CONDITIONS), max_size=3)
            )
        )
        plan.append(None)
    events = []
    host = _FakeHost(plan=plan)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(script, "_host_state", _FakeHost.read_state)
        patch.setattr(script.time, "sleep", lambda s: events.append(s))
        patch.setattr(
            script,
            "milp",
            lambda *a, **k: (events.append("program"), real_milp(*a, **k))[1],
        )
        conditions = script.RunConditions(host)
        checked = script.audit_counts(
            counts, registry, 10, before_program=conditions.before_program
        )
    assert _audit_without_time(checked) == _audit_without_time(unchecked)
    failed = [name for name in plan if name is not None]
    assert host.checks == plan
    assert events.count(script.RECHECK_SECONDS) == len(failed)
    assert events.count("program") == len(programs)
    # Each check is followed by a recheck a minute later if it failed, or
    # by its program if it passed: no program runs while one fails.
    assert len(events) == len(host.checks)
    for happened, name in zip(events, host.checks, strict=True):
        assert happened == (
            "program" if name is None else script.RECHECK_SECONDS
        )
    lapses = failed.count("sleep_assertions")
    assert len(host.holds) == 2 * (1 + lapses)


def _raise_line(function, text):
    """The line where ``function``'s one raise statement holding ``text``
    starts, which is the line a traceback names."""
    import inspect

    lines, first = inspect.getsourcelines(function)
    (offset,) = [i for i, line in enumerate(lines) if text in line]
    while "raise " not in lines[offset]:
        offset -= 1
    return first + offset


@pytest.mark.parametrize("name", script.RUN_CONDITIONS)
def test_a_condition_failing_for_24_hours_stops_the_run_with_its_name(
    name, tmp_path, monkeypatch, invented_main
):
    """The start check passes; before the first program the condition
    fails, and keeps failing through 1,440 rechecks a minute apart. The
    run then stops in the release with the script's own message, naming
    the condition: the version is spent, and no program ran."""
    host = _FakeHost(plan=[None] + [name] * (script.RECHECKS + 1))
    sleeps, programs = [], []
    monkeypatch.setattr(script, "_Host", lambda: host)
    monkeypatch.setattr(script.time, "sleep", sleeps.append)
    monkeypatch.setattr(script, "milp", lambda *a, **k: programs.append(a))
    with pytest.raises(SystemExit) as caught:
        script.main(_main_args(tmp_path))
    line = _raise_line(script.RunConditions.before_program, "raise SystemExit")
    assert str(caught.value) == (
        f"B0.2 stopped in before_program, line {line}: SystemExit: run"
        f" condition {name} still failed after 1440 rechecks, 60 seconds"
        " apart, between programs"
    )
    assert caught.value.__cause__ is None
    assert sleeps == [script.RECHECK_SECONDS] * script.RECHECKS
    assert script.RECHECK_SECONDS * script.RECHECKS == 24 * 3600
    assert not programs
    assert script._attempt_path(tmp_path / "local.json").exists()
    assert not (tmp_path / "local.json").exists()
    assert not (tmp_path / "counts.json").exists()


@pytest.mark.parametrize("clears", [False, True], ids=["fails", "clears"])
def test_the_bounded_wait_runs_with_a_shortened_bound_and_real_waits(
    clears, tmp_path, monkeypatch, invented_main
):
    """The bounded wait as the run would meet it, shortened so it takes a
    fraction of a second: three rechecks a hundredth of a second apart,
    with real waits. A condition failing at the first check and through
    all three rechecks stops the run before any program, with a message
    naming it and the bound. One that clears at the third recheck lets the
    run go on and write both files."""
    monkeypatch.setattr(script, "RECHECKS", 3)
    monkeypatch.setattr(script, "RECHECK_SECONDS", 0.01)
    failures = ["qos"] * (3 if clears else 4)
    host = _FakeHost(plan=[None] + failures)
    programs = []
    real_milp = script.milp
    monkeypatch.setattr(script, "_Host", lambda: host)
    monkeypatch.setattr(
        script,
        "milp",
        lambda *a, **k: programs.append(host.checks[:]) or real_milp(*a, **k),
    )
    started = time.monotonic()
    if clears:
        assert script.main(_main_args(tmp_path)) == 0
        assert (tmp_path / "local.json").exists()
        assert (tmp_path / "counts.json").exists()
        assert programs[0][: len(failures) + 2] == [None] + failures + [None]
    else:
        with pytest.raises(SystemExit) as caught:
            script.main(_main_args(tmp_path))
        line = _raise_line(
            script.RunConditions.before_program, "raise SystemExit"
        )
        assert str(caught.value) == (
            f"B0.2 stopped in before_program, line {line}: SystemExit: run"
            " condition qos still failed after 3 rechecks, 0.01 seconds"
            " apart, between programs"
        )
        assert not programs
        assert host.checks == [None] + failures
        assert not (tmp_path / "local.json").exists()
    assert time.monotonic() - started >= 3 * 0.01


def _present_index(frame):
    present = frame["sequence"].between(1, 20) & (frame["weight"] > 0)
    return frame.index[present][0]


def _missing_identifier(supplied, case):
    """Take one identifier from a present unit of the inputs main() reads."""
    people, _, anchor, design, _ = supplied
    if case in ("person-wave", "anchor", "person id"):
        frame = anchor if case == "anchor" else people
        column = "person_id" if case == "person id" else "interview"
        frame[column] = frame[column].astype(float)
        frame.loc[_present_index(frame), column] = np.nan
    elif case == "design row":
        person = people.loc[_present_index(people), "person_id"]
        design.drop(design.index[design["person_id"] == person], inplace=True)
    else:
        column = "stratum" if case == "design stratum" else "cluster"
        person = people.loc[_present_index(people), "person_id"]
        design[column] = design[column].astype(float)
        design.loc[design["person_id"] == person, column] = np.nan


ROW_MESSAGE = "row has no person or interview number"
DESIGN_MESSAGE = "a present person has no design stratum or cluster"


@pytest.mark.parametrize(
    ("case", "text", "literal"),
    [
        ("person-wave", f"a present person-wave {ROW_MESSAGE}", ROW_MESSAGE),
        ("person id", f"a present person-wave {ROW_MESSAGE}", ROW_MESSAGE),
        ("anchor", f"a present anchor {ROW_MESSAGE}", ROW_MESSAGE),
        ("design row", DESIGN_MESSAGE, DESIGN_MESSAGE),
        ("design cluster", DESIGN_MESSAGE, DESIGN_MESSAGE),
        ("design stratum", DESIGN_MESSAGE, DESIGN_MESSAGE),
    ],
)
def test_a_present_unit_without_an_identifier_stops_the_run_while_reading(
    case, text, literal, tmp_path, invented_main
):
    """Review round 4 (S4): a missing person or interview number, or design
    variable, for a present person would count them as a person but in no
    household or design cluster, so an effective size could exceed the
    count it bounds. The run stops while reading, before any set is
    built, with the script's own message. (``literal`` is the message's
    text after its formatted field, as the source holds it.)"""
    supplied, _, calls = invented_main
    _missing_identifier(supplied, case)
    with pytest.raises(SystemExit) as caught:
        script.main(_main_args(tmp_path))
    line = _raise_line(script._require_unit_identifiers, literal)
    assert str(caught.value) == (
        f"B0.2 stopped in _require_unit_identifiers, line {line}:"
        f" ValueError: {text}"
    )
    assert calls
    assert script._attempt_path(tmp_path / "local.json").exists()
    assert not (tmp_path / "local.json").exists()


def test_a_missing_identifier_on_a_unit_no_set_counts_is_no_stop():
    """Only present rows are counted, so a row out of the sample (sequence
    0) or with no weight may lack an interview number."""
    people, labor, anchor, design = _worked_rosters()
    people = people.copy()
    people["interview"] = people["interview"].astype(float)
    absent = people.index[~people["sequence"].between(1, 20)]
    weightless = people.index[people["weight"] <= 0]
    assert len(absent) or len(weightless)
    people.loc[absent.union(weightless), "interview"] = np.nan
    script._require_unit_identifiers(people, anchor, design)


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
    with pytest.raises(SystemExit, match="main, line .*: RuntimeError$"):
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

    # A set B0.1 never published, though its size is a published count:
    # its terms all pass, so only the check of the sets' own paths stops it.
    alias = dict(sets)
    alias[("level_cells", "prime", "alias")] = sets[
        ("level_cells", "prime", "households")
    ]
    with pytest.raises(AssertionError, match=r"publishes no count for \["):
        script.check_b0_1_record(record, counts, alias)


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
    """This release's classes, every difference of two of this release's
    sets, and every other difference unless the earlier release published
    both sets."""
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
    # A set is this release's, or the earlier release's, when any row with
    # exactly its atoms is.
    flags = {}
    for row, kind in zip(rows, kinds, strict=True):
        own, early = flags.get(frozenset(row), (False, False))
        flags[frozenset(row)] = (
            own or kind != "prior",
            early or kind != "current",
        )
    for big, (big_own, big_early) in flags.items():
        for small, (small_own, small_early) in flags.items():
            if not small or not small < big:
                continue
            if (big_own and small_own) or not (big_early and small_early):
                found.add(tuple(sorted(big - small)))
    return sorted(found)


def _oracle_earlier_ranges(rows, kinds, sizes, targets):
    """Each target's least and greatest size under the earlier release's
    exact counts alone, by enumeration: every vector of the atoms those
    counts hold that meets each of them exactly. A target holding an atom
    none of them holds is left out, since they leave its size unbounded,
    and so is never exempt."""
    from itertools import product

    prior = [
        (row, sum(sizes[a] for a in row))
        for row, kind in zip(rows, kinds, strict=True)
        if kind != "current"
    ]
    counted = sorted({a for row, _ in prior for a in row})
    position = {a: i for i, a in enumerate(counted)}
    caps = [min(total for row, total in prior if a in row) for a in counted]
    grid = np.array(list(product(*(range(cap + 1) for cap in caps))))
    keep = np.ones(len(grid), dtype=bool)
    for row, total in prior:
        keep &= grid[:, [position[a] for a in row]].sum(axis=1) == total
    grid = grid[keep]
    ranges = {}
    for target in targets:
        if all(a in position for a in target):
            values = grid[:, [position[a] for a in target]].sum(axis=1)
            ranges[target] = (int(values.min()), int(values.max()))
    return ranges


@settings(max_examples=150, deadline=None)
@given(_prior_atom_tables())
@example(([(0, 1), (0,), (1,)], ["prior", "current", "current"], [12, 2]))
@example(([(0, 1), (0,), (1,)], ["both", "current", "prior"], [9, 7]))
# A difference whose range, 10 to 19, is both wide and irrelevant.
@example(
    (
        [(0, 1, 2), (0,), (1, 2), (1,)],
        ["current", "current", "current", "prior"],
        [1, 10, 14],
    )
)
# A class the earlier release published exactly: exempt, and released.
@example(([(0, 1), (0,)], ["current", "both"], [3, 12]))
# An exempt target of true size 10, which is not disclosed.
@example(
    ([(0, 1, 2), (0, 1), (1, 2)], ["current", "prior", "prior"], [10, 1, 1])
)
# A disclosure that narrows an exempt target ends its exemption.
@example(
    (
        [(0, 3, 5), (0, 4, 6), (0, 1), (1, 2), (3, 4), (5,), (6,)],
        ["current"] * 2 + ["prior"] * 5,
        [9, 1, 1, 1, 1, 3, 3],
    )
)
def test_audit_with_earlier_counts_agrees_with_an_exhaustive_reader(table):
    """With an earlier release's exact counts among the constraints, the
    audit and the enumeration oracle reach the same targets, decision,
    disclosures and exemptions, and every other verdict the audit gives
    holds of the final candidates. A reader who reruns the rule on every
    vector with both publications keeps exactly the final candidates.
    Among them every sensitive target spans 4 or more, or is exempt: its
    least and greatest sizes are those the earlier counts alone allow."""
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
    earlier = _oracle_earlier_ranges(rows, kinds, sizes, targets)
    status, disclosed, mask, classes = _oracle_release(
        rows, sizes, grid, targets, earlier
    )
    assert audit["status"] == status
    event(f"{status} after {len(audit['rounds'])} round(s)")
    if "exempt" in classes.values():
        event(f"{status} with an exempt target")
    if status != "released":
        return
    assert {
        tuple(sorted(mapping[c] for c in audit["targets"][i]["columns"]))
        for i in audit["disclosed"]
    } == set(disclosed)
    for target, result in classes.items():
        assert _verdict_holds(
            script_targets[target]["result"],
            result,
            grid[mask][:, list(target)].sum(axis=1),
        ), target
    kept = np.array(
        [
            _oracle_release(rows, list(point), grid, targets, earlier)[0]
            == "released"
            for point in grid
        ]
    )
    assert np.array_equal(kept, mask)
    for target in targets:
        if 1 <= sum(sizes[a] for a in target) <= 9:
            values = grid[kept][:, list(target)].sum(axis=1)
            if script_targets[target]["result"] == "exempt":
                assert earlier[target] == (values.min(), values.max())
            else:
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
    _assert_same_programs(
        [
            _audit_transcript(*_prior_registry(rows, kinds, vector))
            for vector in (sizes, other)
        ]
    )


def _assert_same_programs(transcripts):
    """The same programs, up to the point where one table withholds, and
    all of them when every table releases."""
    (first, first_audit), *others = transcripts
    for second, second_audit in others:
        shorter = min(len(first), len(second))
        assert first[:shorter] == second[:shorter]
        if first_audit["status"] == second_audit["status"] == "released":
            assert first == second


@pytest.mark.parametrize(
    "table",
    [
        ([(0, 1), (0,)], ["current", "both"], [3, 12]),
        (
            [(0, 1, 2), (0, 1), (1, 2)],
            ["current", "prior", "prior"],
            [10, 1, 2],
        ),
    ],
)
def test_the_exemption_programs_depend_only_on_the_publications(table):
    """Every table with both publications and the same atoms, the truth's
    included, has an exempt target and hands the solver the same
    programs, the two that test each exemption among them."""
    rows, kinds, sizes = table
    grid = _oracle_prior_candidates(rows, kinds, sizes)
    vectors = [
        [int(v) for v in point] for point in grid[np.all(grid > 0, axis=1)]
    ]
    assert sizes in vectors and len(vectors) >= 2
    transcripts = [
        _audit_transcript(*_prior_registry(rows, kinds, vector))
        for vector in vectors
    ]
    for _, audit in transcripts:
        assert any(t["result"] == "exempt" for t in audit["targets"])
    _assert_same_programs(transcripts)


def test_the_exemption_fails_closed(monkeypatch):
    """B0.1 publishes a0 + a1 = 3 exactly, so its counts alone leave a0 0
    to 3, and count no set holding a2. A target is exempt only when its
    range under the round is proven and is the same as theirs: a range
    this release narrowed further, an unproven one, a target holding a2
    and a program that proves no optimum are not exempt, and nothing is
    without an earlier release."""
    counts, registry = _prior_table(
        {"all": (0, 1, 2), "left": (0,)}, {"pair": (0, 1)}, [1, 2, 5]
    )
    model = script.build_model(registry)
    column = {int(model["sizes"][c]): c for c in range(3)}
    earlier = script.earlier_counts_system(registry, model)
    assert earlier[1].tolist() == [c == column[5] for c in range(3)]
    alone = _prior_table({"all": (0,)}, {}, [3])[1]
    assert script.earlier_counts_system(alone, script.build_model(alone)) is (
        None
    )

    def outcome(proof="optima", low=0, high=3):
        return {"programs": [], "proof": proof, "range": [low, high]}

    a0 = {"columns": [column[1]]}
    found = outcome()
    assert script.exempt(earlier, a0, found, seconds=30)
    assert found["programs"] == ["earlier maximum", "earlier minimum"]
    for narrower in (outcome(low=1), outcome(high=2)):
        assert not script.exempt(earlier, a0, narrower, seconds=30)
    assert not script.exempt(None, a0, outcome(), seconds=30)
    for proof in ("pool", "search", "undetermined"):
        assert not script.exempt(earlier, a0, outcome(proof), seconds=30)
    # The programs fix a2 at 0, so a0 + a2 would match; B0.1 leaves a2,
    # and so the target, unbounded.
    holding = {"columns": [column[1], column[5]]}
    assert not script.exempt(earlier, holding, outcome(), seconds=30)
    original = script.AuditSystem.extreme
    for unproven in (1, -1):

        def extreme(
            self, columns, sense, low, high, *, seconds, skip=unproven
        ):
            if sense == skip:
                return None
            return original(self, columns, sense, low, high, seconds=seconds)

        monkeypatch.setattr(script.AuditSystem, "extreme", extreme)
        assert not script.exempt(earlier, a0, outcome(), seconds=30)


def test_a_disclosure_that_narrows_an_exempt_target_ends_its_exemption(
    monkeypatch,
):
    """Seven invented atoms. B0.1 publishes a0 + a1 = 10, a1 + a2 = 2,
    b0 + b1 = 2, c = 3 and d = 3 exactly; this release publishes
    a0 + b0 + c and a0 + b1 + d, 13 each, so 10 to 14. In round 1 the
    class {b0, c}, of 4, can be 3 to 5, as under B0.1's counts alone, so
    it is exempt. The differences a0 + b0 and a0 + b1, 10 each, can be 8
    to 11, where B0.1's counts alone allow 8 to 12: they are narrow, not
    exempt, and disclosed. Under those disclosures {b0, c} can only be 4,
    so round 2 tests it again, finds it narrower than B0.1 leaves it, and
    the release is withheld."""
    counts, registry = _prior_registry(
        [(0, 3, 5), (0, 4, 6), (0, 1), (1, 2), (3, 4), (5,), (6,)],
        ["current"] * 2 + ["prior"] * 5,
        [9, 1, 1, 1, 1, 3, 3],
    )
    calls = {}
    original = script.exempt

    def recording(earlier, target, outcome, *, seconds):
        result = original(earlier, target, outcome, seconds=seconds)
        calls.setdefault(tuple(target["columns"]), []).append(result)
        return result

    monkeypatch.setattr(script, "exempt", recording)
    audit = script.audit_counts(counts, registry, 10)
    assert audit["status"] == "withheld"
    assert len(audit["rounds"]) == 2
    assert (
        sorted(
            (audit["targets"][i]["kind"], audit["targets"][i]["true_size"])
            for i in audit["disclosed"]
        )
        == [("difference", 10)] * 2
    )
    (ended,) = [
        t
        for i, t in enumerate(audit["targets"])
        if t["result"] == "narrow" and i not in audit["disclosed"]
    ]
    assert (ended["kind"], ended["true_size"], ended["range"]) == (
        "atom",
        4,
        [4, 4],
    )
    assert calls[tuple(ended["columns"])] == [True, False]


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
    with pytest.raises(SystemExit, match="AssertionError: .*rerun on these"):
        script.main(["--out", str(out), "--local-copy", str(local)])
    assert not out.exists() and not local.exists()


# --------------------------------------------------------------------------
# B0.1's sets in memory only (the coordinator's ruling of 2026-10-24): the
# rerun gate, the write boundary and the relabeling invariant
# --------------------------------------------------------------------------
def test_the_rerun_gate_stops_on_a_rebuilt_set_that_is_not_its_count():
    """Condition 1: each rebuilt set must have the size B0.1 published for
    it, as the signed sum of the counts its entry names, and the stop
    names the path, never a size."""
    people, validity, counts, sets = _b01_example()
    record = _b01_record(people, validity)
    path = ("domain_persons",)
    unit_type, units, terms = sets[path]
    assert units
    short = {**sets, path: (unit_type, frozenset(sorted(units)[1:]), terms)}
    with pytest.raises(
        AssertionError, match=r"not its count: \('domain_persons',\)$"
    ):
        script.check_b0_1_record(record, counts, short)
    # A change pair's rows set is its rows count less its persons count.
    pair = ("change_pairs", "pooled_one_step", "rows")
    unit_type, units, terms = sets[pair]
    assert len(terms) == 2
    grown = {**sets, pair: (unit_type, units | {-1}, terms)}
    with pytest.raises(AssertionError, match="not its count"):
        script.check_b0_1_record(record, counts, grown)


def test_main_stops_at_the_rerun_gate_before_any_count_is_written(
    tmp_path, monkeypatch
):
    """A rebuilt set that is not its count stops main() before the audit,
    naming the path. Neither file is written; the attempt record, written
    before any input is read, holds no count."""
    _main_environment(tmp_path, monkeypatch, _b2_heads(12, 6))
    rebuilt = script.b0_1_sets

    def short(person_wave, validity):
        sets = rebuilt(person_wave, validity)
        unit_type, units, terms = sets[("domain_persons",)]
        assert units
        sets[("domain_persons",)] = (
            unit_type,
            frozenset(sorted(units)[1:]),
            terms,
        )
        return sets

    monkeypatch.setattr(script, "b0_1_sets", short)
    out = tmp_path / "counts.json"
    local = tmp_path / "local.json"
    with pytest.raises(
        SystemExit,
        match=(
            r"^B0\.2 stopped in check_b0_1_record, line \d+: AssertionError:"
            r" a rebuilt B0\.1 set is not its count: \('domain_persons',\)$"
        ),
    ):
        script.main(["--out", str(out), "--local-copy", str(local)])
    assert not out.exists() and not local.exists()
    attempt = json.loads(script._attempt_path(local).read_text())
    assert set(attempt) == {"repository_head", "script_sha256", "started_at"}


def test_the_local_copy_holds_this_releases_counts_and_decisions_only():
    """Conditions 2 and 3: the local audit is the decision record. Each
    target of this release is what it is, its true size and its final
    classification; nothing computed from the atoms that is not a
    decision is written, and nothing about the rounds: not which round
    disclosed or settled a target, whether the pool was seeded again, or
    how many rounds ran."""
    (_, _, private), registry, counts = _nested_prior_release(range(12))
    audit = private["audit"]
    assert set(audit) == {"base", "status", "targets", "class_sizes"}
    assert script.TARGET_FIELDS == (
        "unit_type",
        "kind",
        "sets",
        "superset",
        "subset",
        "true_size",
        "result",
    )
    assert audit["targets"]
    for target in audit["targets"]:
        assert set(target) <= set(script.TARGET_FIELDS)
        assert {"unit_type", "kind", "true_size", "result"} <= set(target)
        if target["kind"] == "difference":
            assert {"superset", "subset"} <= set(target)
            assert "sets" not in target
        else:
            assert target["sets"] and "superset" not in target
    # The audit itself ran rounds and settled each target in one; none of
    # that reaches the record.
    full = script.audit_counts(counts, registry, 10)
    assert full["rounds"] and all("round" in t for t in full["targets"])
    text = json.dumps(audit, sort_keys=True)
    assert '"round' not in text and '"reseeded"' not in text


def _brute_classes(registry):
    """This release's classes by direct membership: units of one type that
    belong to exactly the same of this release's sets, with those sets'
    paths in registry order."""
    signatures = {}
    for path, (unit_type, units) in registry.sets.items():
        for unit in units:
            signatures.setdefault((unit_type, unit), []).append(list(path))
    classes = Counter(
        (unit_type, json.dumps(paths))
        for (unit_type, _), paths in signatures.items()
    )
    return sorted(
        (unit_type, json.loads(paths), size)
        for (unit_type, paths), size in classes.items()
    )


@pytest.mark.parametrize(
    "case",
    ["nested", "coinciding", "household", "release_panel", "worked_rosters"],
)
def test_each_class_names_this_releases_sets_that_hold_it(case):
    """Condition 3's "sets" for a class (review round 4, S1): the paths of
    this release's sets that hold it, exactly as direct membership gives
    them and in the release's order, and none of B0.1's, even when a B0.1
    set is the same set as one of this release's."""
    if case == "nested":
        _, registry, _ = _nested_prior_release(range(12))
    elif case == "coinciding":
        registry = script.SetRegistry()
        registry.add(("total",), "persons", range(30))
        registry.add(("part",), "persons", range(20))
        registry.add_prior(("b0_1", "died"), "persons", range(20), 20)
        assert (
            registry.prior[("b0_1", "died")][1] == registry.sets[("part",)][1]
        )
    else:
        inputs = {
            "household": _household_prior_panel,
            "release_panel": _release_panel,
            "worked_rosters": _worked_rosters,
        }[case]()
        people, labor, anchor, design = inputs
        validity = _validity(labor)
        registry = script.disclosure_registry(people, validity, anchor, design)
        script.register_b0_1(
            registry,
            script.b0_1_sets(people, validity),
            b01.structural_counts(people, validity),
        )
    classes = sorted(
        (target["unit_type"], target["sets"], target["true_size"])
        for target in script.build_model(registry)["targets"]
        if target["kind"] == "atom"
    )
    assert classes == _brute_classes(registry)
    assert all(
        tuple(path) in registry.sets for _, sets, _ in classes for path in sets
    )


def _three_target_table():
    """Three targets of this release, in order: A (true size 12), then S
    (true size 3, sensitive), then B."""
    counts, registry = _atom_table([(0, 1, 2), (1, 2), (2,)], [12, 3, 20])
    targets = script.build_model(registry)["targets"]
    sizes = [target["true_size"] for target in targets]
    a = sizes.index(12)
    s = sizes.index(3)
    b = next(i for i in range(s + 1, len(targets)))
    assert a < s < b
    return counts, registry, a, s, b


@pytest.mark.parametrize("withheld_in", [1, 2])
@pytest.mark.parametrize("b_first", ["wide", "irrelevant"])
def test_a_target_the_ending_round_did_not_reach_is_unreached(
    withheld_in, b_first, monkeypatch
):
    """Review round 4 (S1, exp17) found the targets after a withholding
    target written as "unclassified" after a round-1 withhold but with
    their round-1 result after a later one, so the record showed the
    round. Now a target the ending round did not reach is "unreached"
    whichever round withheld; a disclosed target keeps "narrow", and one
    proven irrelevant keeps "irrelevant", which no later round changes.

    Forced: S is wide in round 1 and narrow in round 2; A is narrow in
    round 1, and so disclosed, when the withhold comes in round 2."""
    counts, registry, a, s, b = _three_target_table()
    forced = {
        1: {s: "narrow"},
        2: {a: "narrow", s: "wide", b: b_first},
    }[withheld_in]

    def forcing(system, target, pool, *, seconds):
        index = [t["columns"] for t in targets].index(target["columns"])
        result = forced.get(index, b_first if index == b else "wide")
        if system.disclosed:
            result = "narrow" if index == s else "wide"
        return {"programs": [], "result": result, "proof": "forced"}, None

    targets = script.build_model(registry)["targets"]
    monkeypatch.setattr(script, "classify", forcing)
    audit = script.audit_counts(counts, registry, 10)
    assert audit["status"] == "withheld"
    assert len(audit["rounds"]) == withheld_in
    results = [target["result"] for target in audit["targets"]]
    # B is never reached in the ending round. After a round-1 withhold it
    # was never classified; after a round-2 one it keeps only a round-1
    # irrelevance.
    kept = withheld_in == 2 and b_first == "irrelevant"
    expected = {
        a: "narrow" if withheld_in == 2 else "wide",
        s: "narrow",
        b: "irrelevant" if kept else "unreached",
    }
    assert {index: results[index] for index in expected} == expected
    local = script.local_audit(audit)["targets"]
    assert local[b]["result"] == expected[b]
    assert '"round' not in json.dumps(local)


def test_every_target_of_an_audit_stopped_before_any_round_is_unreached(
    monkeypatch,
):
    """When no seed program finds a point, nothing is classified, and every
    target reads "unreached", as after a withhold in any round."""
    counts, registry, _, _, _ = _three_target_table()
    monkeypatch.setattr(
        script.AuditSystem,
        "_program",
        lambda self, *a, **k: SimpleNamespace(x=None, status=1, fun=None),
    )
    audit = script.audit_counts(counts, registry, 10)
    assert audit["status"] == "withheld" and audit["rounds"] == []
    assert {target["result"] for target in audit["targets"]} == {"unreached"}


def _settled_audit():
    """An audit whose rounds the local copy must not reflect: the nested
    release, with two or more targets of this release, one or more of them
    settled in round 1."""
    _, registry, counts = _nested_prior_release(range(12))
    audit = script.audit_counts(counts, registry, 10)
    own = [t for t in audit["targets"] if not t["earlier"]]
    assert len(own) >= 2 and any(t["round"] == 1 for t in own)
    return audit


@settings(max_examples=40, deadline=None)
@given(st.data())
def test_the_local_copy_is_the_same_whatever_the_rounds(data):
    """Condition 3 as a property (review round 4): whatever round settled
    each target, and whatever rounds ran, the local copy's record is the
    same byte for byte. Round information can then reach it through no
    field, not as a mark on a result and not through the targets' order."""
    from copy import deepcopy

    audit = _settled_audit()
    expected = json.dumps(script.local_audit(audit), sort_keys=True)
    changed = deepcopy(audit)
    settled = [t for t in changed["targets"] if "round" in t]
    for target, settling in zip(
        settled,
        data.draw(
            st.lists(
                st.integers(1, 9), min_size=len(settled), max_size=len(settled)
            )
        ),
        strict=True,
    ):
        target["round"] = settling
    changed["rounds"] = data.draw(
        st.lists(
            st.fixed_dictionaries(
                {
                    "round": st.integers(1, 9),
                    "disclosed": st.lists(
                        st.integers(0, len(changed["targets"]) - 1)
                    ),
                    "reseeded": st.booleans(),
                }
            ),
            min_size=1,
            max_size=4,
        )
    )
    assert json.dumps(script.local_audit(changed), sort_keys=True) == expected


@pytest.mark.parametrize("order", ["late", "rising", "falling"])
def test_the_local_copy_ignores_rounds_that_order_or_mark_targets(order):
    """The property's two executed attacks, fixed: every target of this
    release settled after round 1, which a mark on late results would
    show, or settled in rising or falling rounds along their order, which
    an order by round would show. None changes a byte of the local copy."""
    audit = _settled_audit()
    expected = json.dumps(script.local_audit(audit), sort_keys=True)
    own = [t for t in audit["targets"] if not t["earlier"]]
    for index, target in enumerate(own):
        target["round"] = {
            "late": 2,
            "rising": index + 1,
            "falling": len(own) - index,
        }[order]
    assert json.dumps(script.local_audit(audit), sort_keys=True) == expected


def _own_targets(registry):
    return [
        {key: value for key, value in target.items() if key != "columns"}
        for target in script.build_model(registry)["targets"]
        if not target["earlier"]
    ]


def test_this_releases_targets_do_not_depend_on_earlier_sets():
    """Which targets are this release's own, how they are named and their
    order are the same whatever the earlier sets are. An earlier
    difference, p minus q, holds the same units as this release's wide
    minus narrow and is reached first; and when the earlier release also
    published wide and narrow, their difference is still a target."""

    def registry(priors):
        built = script.SetRegistry()
        for name, units in (
            ("q", {5}),
            ("wide", {1, 2, 3, 4}),
            ("narrow", {1, 2}),
            ("mid", {3}),
        ):
            built.add((name,), "persons", units)
        for name, units in priors.items():
            built.add_prior((name,), "persons", units, len(units))
        return built

    alone = _own_targets(registry({}))
    assert {
        "kind": "difference",
        "unit_type": "persons",
        "superset": ["wide"],
        "subset": ["narrow"],
        "earlier": False,
        "true_size": 2,
    } in alone
    for priors in (
        {"p": {3, 4, 5}},
        {"wide_0": {1, 2, 3, 4}, "narrow_0": {1, 2}},
        {"p": {3, 4, 5}, "wide_0": {1, 2, 3, 4}, "narrow_0": {1, 2}},
    ):
        assert _own_targets(registry(priors)) == alone, priors


class _FixedClock:
    """The attempt record's clock, fixed so that two runs compare."""

    @staticmethod
    def now(tz=None):
        from datetime import datetime

        return datetime(2026, 10, 24, tzinfo=tz)


def _disposition_panel(ages, states):
    """B2 heads at 2011 with the given ages, each with a household, stratum
    and cluster of their own; at 2013 each is present (sequence 1), dead
    (85), moved out (75) or has no row, as ``states`` says."""
    codes = {"present": 1, "died": 85, "moved": 75}
    rows = []
    for person, (age, state) in enumerate(zip(ages, states, strict=True), 1):
        rows.append(_row(person, age=age))
        if state in codes:
            rows.append(_row(person, 2013, age + 2, sequence=codes[state]))
    return _own_strata(_inputs(rows))


def _atoms(inputs):
    """The atom sizes and types that B0.1's sets refine, in memory."""
    people, labor, anchor, design = inputs
    validity = _validity(labor)
    registry = script.disclosure_registry(people, validity, anchor, design)
    script.register_b0_1(
        registry,
        script.b0_1_sets(people, validity),
        b01.structural_counts(people, validity),
    )
    model = script.build_model(registry)
    return model["sizes"].tolist(), model["unit_types"]


#: Audit events that create, change or remove a file or its metadata,
#: with the positions of the paths each names. "open" counts only when
#: its mode or flags write.
FILE_EVENTS = {
    "open": (0,),
    "os.rename": (0, 1),
    "os.link": (1,),
    "os.symlink": (1,),
    "os.mkdir": (0,),
    "os.truncate": (0,),
    "os.remove": (0,),
    "os.rmdir": (0,),
    "os.chmod": (0,),
    "os.chown": (0,),
    "os.chflags": (0,),
    "os.utime": (0,),
    "os.setxattr": (0,),
    "os.removexattr": (0,),
}
#: Audit events that start a process, open a socket, a connection, a
#: database or the system log, or look up a name, any of which could carry
#: a value past every file check. main() makes none; its sleep assertions are
#: stand-ins in these tests.
PROCESS_EVENTS = {
    "subprocess.Popen",
    "os.system",
    "os.posix_spawn",
    "os.spawn",
    "os.exec",
    "os.fork",
    "os.forkpty",
    "socket.__new__",
    "socket.bind",
    "socket.connect",
    "socket.sendmsg",
    "socket.sendto",
    "socket.getaddrinfo",
    "socket.gethostbyname",
    "socket.gethostbyaddr",
    "socket.getnameinfo",
    "sqlite3.connect",
    "syslog.openlog",
    "syslog.syslog",
}
WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC
#: The one confinement in force, if any, and what it refused.
_confinement = {"directory": None, "names": frozenset(), "refused": []}
_confinement_hook = []


def _refuse_writes_outside(event, arguments):
    """The audit hook behind ``_writes_confined_to``."""
    directory = _confinement["directory"]
    if directory is None:
        return
    if event in PROCESS_EVENTS:
        _confinement["refused"].append((event, None))
        raise PermissionError(f"{event} while main() runs")
    if event not in FILE_EVENTS:
        return
    if event == "open":
        _, mode, flags = arguments
        if not (
            (isinstance(mode, str) and set(mode) & set("wxa+"))
            or (isinstance(flags, int) and flags & WRITE_FLAGS)
        ):
            return
    for position in FILE_EVENTS[event]:
        path = arguments[position]
        if path is None or isinstance(path, int):
            # An open descriptor, already checked when it was opened.
            continue
        path = os.path.abspath(os.fsdecode(path))
        parent, name = os.path.split(path)
        if path == os.devnull:
            # The guard's null device.
            continue
        if os.path.realpath(parent) == directory and (
            name in _confinement["names"]
            or any(
                name.startswith(f".{final}.") and name.endswith(".partial")
                for final in _confinement["names"]
            )
        ):
            # One of the outputs, or ``write_new``'s temporary file for one.
            continue
        _confinement["refused"].append((event, path))
        raise PermissionError(f"{event} outside the run's outputs: {path}")


@contextmanager
def _writes_confined_to(directory, names):
    """While it holds, refuse and record every file write that is not one
    of ``names`` in ``directory`` (or its temporary file), a bytecode
    cache's included, and every new process, socket, connection, database,
    name lookup or system log message. Bytecode writing is off meanwhile, so a lazy
    import writes no cache. An audit hook cannot be removed, so one hook,
    installed once, checks whether a confinement holds.

    The hook sees what Python's audit events report: a write that native
    code makes through a descriptor it opened itself, or a send on a
    socket opened before the confinement, raises none. For those the
    static check stands: the script imports no socket, database or log
    module, and its C calls are pinned."""
    if not _confinement_hook:
        sys.addaudithook(_refuse_writes_outside)
        _confinement_hook.append(_refuse_writes_outside)
    refused = []
    _confinement.update(
        directory=os.path.realpath(directory),
        names=frozenset(names),
        refused=refused,
    )
    bytecode = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        yield refused
    finally:
        _confinement["directory"] = None
        sys.dont_write_bytecode = bytecode


def test_the_write_confinement_refuses_writes_outside_the_outputs(tmp_path):
    """The confinement the relabeling tests run main() under: an output and
    its temporary file may be written, and reads and the null device pass;
    a file elsewhere, np.save into the temporary folder, a second file
    beside the outputs, a new process, a file in an existing bytecode
    cache folder, a database, a socket, a name lookup, a renamed or
    stamped file elsewhere and a removed one are each refused and recorded
    (review rounds 4 and 5). Bytecode writing is off while it holds."""
    inside = tmp_path / "run"
    inside.mkdir()
    (inside / "input.txt").write_text("read me")
    elsewhere = tmp_path / "elsewhere.npy"
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    stamped = tmp_path / "stamped.txt"
    stamped.write_text("")
    bytecode = sys.dont_write_bytecode
    with _writes_confined_to(inside, {"counts.json"}) as refused:
        assert sys.dont_write_bytecode
        script.write_new(inside / "counts.json", b"{}")
        assert (inside / "input.txt").read_text() == "read me"
        with open(os.devnull, "w") as null:
            null.write("passes")
        for attempt in (
            lambda: np.save(elsewhere, np.arange(3)),
            lambda: (inside / "extra.json").write_text("{}"),
            lambda: subprocess.run(["true"], check=False),
            lambda: (cache / "atoms.pyc").write_bytes(b"3"),
            lambda: sqlite3.connect(tmp_path / "atoms.db"),
            lambda: socket.socket(),
            lambda: socket.getaddrinfo("localhost", None),
            lambda: os.rename(stamped, inside / "moved.txt"),
            lambda: os.utime(stamped, (3, 3)),
            lambda: os.remove(stamped),
        ):
            with pytest.raises(PermissionError):
                attempt()
    assert sys.dont_write_bytecode == bytecode
    assert [event for event, _ in refused] == [
        "open",
        "open",
        "subprocess.Popen",
        "open",
        "sqlite3.connect",
        "socket.__new__",
        "socket.getaddrinfo",
        "os.rename",
        "os.utime",
        "os.remove",
    ]
    assert not elsewhere.exists() and not (inside / "extra.json").exists()
    assert not list(cache.iterdir()) and not (tmp_path / "atoms.db").exists()
    assert stamped.exists() and stamped.stat().st_mtime != 3
    # Outside the confinement nothing is refused.
    np.save(elsewhere, np.arange(3))
    assert elsewhere.exists()


def _written(directory, monkeypatch, inputs, capture):
    """Every byte main() writes or prints for ``inputs``: both files, the
    attempt record and its output, with the run's directory taken out. The
    run's directory is also its working directory, so a log or cache
    written there would be caught; and main() runs confined, so a write
    anywhere else, or a new process, fails the run. The B0.1 record it
    reads is returned too."""
    _main_environment(directory, monkeypatch, inputs)
    monkeypatch.setattr(script, "datetime", _FixedClock)
    monkeypatch.chdir(directory)
    capture()
    out = directory / "counts.json"
    local = directory / "local.json"
    outputs = {out.name, local.name, script._attempt_path(local).name}
    with _writes_confined_to(directory, outputs) as refused:
        try:
            status = script.main(
                ["--out", str(out), "--local-copy", str(local)]
            )
        except SystemExit as stop:
            status = stop
    assert refused == []
    assert status == 0
    printed = tuple(
        text.replace(str(directory), "<run>") for text in capture()
    )
    written = {
        path.name: path.read_bytes()
        for path in sorted(directory.iterdir())
        if path.name not in ("b01.json", "protocol.md")
    }
    assert set(written) == {
        "counts.json",
        "local.json",
        script._attempt_path(local).name,
    }
    return written, printed, (directory / "b01.json").read_bytes()


def _decisions(written):
    """The audit's decision record, as the local copy writes it."""
    audit = json.loads(written["local.json"])["disclosure_audit"]["audit"]
    return (
        audit["status"],
        [
            (t["kind"], t.get("superset"), t.get("subset"), t["result"])
            for t in audit["targets"]
        ],
    )


def _swap(states, died, moved):
    swapped = list(states)
    swapped[died], swapped[moved] = "moved", "died"
    return swapped


#: Twelve invented heads whose small classes B0.1's published counts
#: already fix: the release withholds without the exemption and releases
#: with it.
EXEMPT_PANEL = (
    [62] * 6 + [60] * 6,
    ["died", "moved"] + ["present"] * 4 + ["moved"] + ["present"] * 5,
)


@pytest.mark.parametrize(
    ("ages", "before", "died", "moved", "status"),
    [
        (
            [62, 62, 60, 62, 60, 60],
            ["moved", "present", "present", "moved", "died", "died"],
            4,
            3,
            "withheld",
        ),
        (
            [62, 60] * 30,
            ["died"] * 6 + ["moved"] * 6 + ["present"] * 48,
            0,
            7,
            "released",
        ),
        (*EXEMPT_PANEL, 0, 6, "released"),
    ],
)
def test_relabeling_a_death_and_a_move_changes_no_written_byte(
    tmp_path, monkeypatch, capfd, ages, before, died, moved, status
):
    """Condition 4. Swap a head who died by 2013 with one who moved out,
    between two of this release's classes: B0.1's published counts, this
    release's class sizes and the audit's decisions stay the same, while
    the atoms that B0.1's sets refine change. Every byte main() writes or
    prints, to either file, the attempt record, standard output or
    standard error, is then the same. One panel withholds and two
    release, so the committed file carries counts; the third releases
    only because B0.1's counts already fix its small classes, so its
    decisions include exempt targets."""
    after = _swap(before, died, moved)
    assert (before[died], before[moved]) == ("died", "moved")
    assert ages[died] != ages[moved]

    def capture():
        captured = capfd.readouterr()
        return captured.out, captured.err

    runs = []
    for name, states in (("before", before), ("after", after)):
        directory = tmp_path / name
        directory.mkdir()
        runs.append(
            _written(
                directory,
                monkeypatch,
                _disposition_panel(ages, states),
                capture,
            )
        )
    (first, printed_first, b01_first), (second, printed_second, b01_second) = (
        runs
    )
    # The premise: B0.1's record and the audit's decisions are unchanged,
    # and the atoms are not.
    assert b01_first == b01_second
    assert _decisions(first) == _decisions(second)
    assert _atoms(_disposition_panel(ages, before)) != _atoms(
        _disposition_panel(ages, after)
    )
    assert json.loads(first["counts.json"])["disclosure"]["status"] == status
    assert first == second
    assert printed_first == printed_second


def test_classes_b0_1_already_fixes_are_exempt_and_release(
    tmp_path, monkeypatch
):
    """Max's ruling of 2026-10-26, through main(). In this panel B0.1's
    published counts alone leave two classes of persons only 0 to 2 and
    1 to 3, and fix a difference of this release's sets at 3: they hold
    1, 2 and 3. This release narrows none of them further, so they are
    exempt and the counts are released. A difference against a B0.1 set,
    of true size 10, is exempt too, and so is not disclosed. With the
    exemption switched off the same panel withholds."""
    ages, states = EXEMPT_PANEL
    inputs = _disposition_panel(ages, states)
    _main_environment(tmp_path, monkeypatch, inputs)
    out = tmp_path / "counts.json"
    local = tmp_path / "local.json"
    assert script.main(["--out", str(out), "--local-copy", str(local)]) == 0
    assert json.loads(out.read_text())["disclosure"]["status"] == "released"
    targets = json.loads(local.read_text())["disclosure_audit"]["audit"][
        "targets"
    ]
    assert sorted(
        (t["kind"], t["true_size"]) for t in targets if t["result"] == "exempt"
    ) == [("atom", 1), ("atom", 2), ("difference", 3)]
    assert all(t["result"] != "narrow" for t in targets)
    people, labor, anchor, design = inputs
    validity = _validity(labor)
    counts = script.structural_counts(people, validity, anchor, design)

    def registry():
        built = script.disclosure_registry(people, validity, anchor, design)
        script.register_b0_1(
            built,
            script.b0_1_sets(people, validity),
            b01.structural_counts(people, validity),
        )
        return built

    audit = script.audit_counts(counts, registry())
    (large,) = [
        index
        for index, t in enumerate(audit["targets"])
        if t["result"] == "exempt" and t["true_size"] >= 10
    ]
    assert audit["targets"][large]["earlier"]
    assert large not in audit["disclosed"]
    monkeypatch.setattr(script, "exempt", lambda *_, **__: False)
    assert script.audit_counts(counts, registry())["status"] == "withheld"


def _draining(out, err):
    """What was printed to ``out`` and ``err`` since the last call."""

    def capture():
        printed = (out.getvalue(), err.getvalue())
        for stream in (out, err):
            stream.seek(0)
            stream.truncate()
        return printed

    return capture


@st.composite
def _relabelings(draw):
    """Heads aged 60 or 62, each present, dead, moved out or absent at
    2013, and one death and one move to swap, of different ages, so that
    the swap changes the atoms B0.1's sets refine. Six to ten heads mostly
    withhold; fifty to seventy with five or more deaths and five or more
    moves mostly release, so both statuses are tried."""
    if draw(st.booleans()):
        persons = draw(st.integers(6, 10))
        states = draw(
            st.lists(
                st.sampled_from(["present", "died", "moved", "absent"]),
                min_size=persons,
                max_size=persons,
            )
        )
    else:
        persons = draw(st.integers(50, 70))
        deaths, moves, absent = (
            draw(st.integers(5, 12)),
            draw(st.integers(5, 12)),
            draw(st.integers(0, 4)),
        )
        states = list(
            draw(
                st.permutations(
                    ["died"] * deaths
                    + ["moved"] * moves
                    + ["absent"] * absent
                    + ["present"] * (persons - deaths - moves - absent)
                )
            )
        )
    ages = draw(
        st.lists(st.sampled_from([60, 62]), min_size=persons, max_size=persons)
    )
    died, moved = draw(
        st.lists(
            st.integers(0, persons - 1), min_size=2, max_size=2, unique=True
        )
    )
    states[died], states[moved] = "died", "moved"
    # Review round 4: a swap between heads of one age leaves every atom as
    # it was, which made two thirds of the draws trivially pass.
    ages[moved] = 62 if ages[died] == 60 else 60
    return ages, states, died, moved


@settings(max_examples=16, deadline=None)
@given(_relabelings())
def test_relabeling_deaths_and_moves_changes_no_written_byte(relabeling):
    """Condition 4 over invented panels: whenever swapping a death and a
    move leaves the audit's decisions unchanged, every byte main() writes
    or prints is unchanged. (B0.1's counts and this release's class sizes
    cannot change under the swap; the test checks both.) The premise is
    checked too: a draw whose swap leaves the atoms as they were tests
    nothing, and is counted apart."""
    import io
    import tempfile
    from contextlib import redirect_stderr, redirect_stdout

    ages, states, died, moved = relabeling
    runs = []
    with (
        tempfile.TemporaryDirectory() as root,
        pytest.MonkeyPatch.context() as patch,
    ):
        for name, panel_states in (
            ("before", states),
            ("after", _swap(states, died, moved)),
        ):
            # Resolved, as main() resolves the input folder: on macOS the
            # temporary folder sits behind a symbolic link.
            directory = Path(root).resolve() / name
            directory.mkdir()
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                runs.append(
                    _written(
                        directory,
                        patch,
                        _disposition_panel(ages, panel_states),
                        _draining(out, err),
                    )
                )
    (first, printed_first, b01_first), (second, printed_second, b01_second) = (
        runs
    )
    assert b01_first == b01_second
    if _atoms(_disposition_panel(ages, states)) == _atoms(
        _disposition_panel(ages, _swap(states, died, moved))
    ):
        event("the swap left the atoms unchanged")
        return
    if _decisions(first) != _decisions(second):
        event("the swap changed a decision")
        return
    audit = json.loads(first["local.json"])["disclosure_audit"]["audit"]
    event(f"atoms changed, decisions kept, {audit['status']}")
    assert first == second
    assert printed_first == printed_second


def test_a_failure_from_outside_this_script_prints_no_value(
    tmp_path, monkeypatch, capfd
):
    """Condition 2 on failures: inside the release, a library's failure
    stops main() with a fixed text that names the phase alone, since its
    message can quote a size and where it strikes can depend on
    dispositions. Neither file is written, and the attempt record refuses
    a rerun of this version: the stop withholds it."""
    _main_environment(tmp_path, monkeypatch, _b2_heads(12, 6))

    def failing(*_):
        raise ValueError(
            "Length of values (7) does not match length of index (11)"
        )

    monkeypatch.setattr(script, "disclosure_registry", failing)
    out = tmp_path / "counts.json"
    local = tmp_path / "local.json"
    with pytest.raises(SystemExit) as caught:
        script.main(["--out", str(out), "--local-copy", str(local)])
    assert str(caught.value) == "B0.2 stopped in the release"
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__
    assert not out.exists() and not local.exists()
    assert capfd.readouterr() == ("", "")
    with pytest.raises(SystemExit, match="already has an attempt record"):
        script.main(["--out", str(out), "--local-copy", str(local)])
    assert not out.exists() and not local.exists()


def test_a_failure_deep_in_the_disposition_rebuild_names_the_phase_alone(
    tmp_path, monkeypatch, capfd
):
    """An invented failure inside the rebuild of B0.1's disposition sets,
    whose message quotes a size and which writes a size to both
    descriptors as it fails, reports the fixed text alone: no type, no
    line and no message, and nothing it wrote is seen."""
    _main_environment(tmp_path, monkeypatch, _b2_heads(12, 6))
    calls = []

    def failing(*arguments):
        calls.append(arguments)
        if len(calls) == 2:
            os.write(1, b"7 deaths\n")
            os.write(2, b"7 deaths\n")
            raise IndexError("index 7 is out of bounds for axis 0 with size 7")
        return b01._disposition(*arguments)

    monkeypatch.setattr(script, "_disposition", failing)
    out = tmp_path / "counts.json"
    local = tmp_path / "local.json"
    with pytest.raises(SystemExit) as caught:
        script.main(["--out", str(out), "--local-copy", str(local)])
    assert str(caught.value) == "B0.2 stopped in the release"
    assert len(calls) == 2
    assert not out.exists() and not local.exists()
    assert capfd.readouterr() == ("", "")


def test_a_failure_while_reading_the_inputs_keeps_its_type_and_line(
    tmp_path, monkeypatch
):
    """Reading and reducing the inputs builds no set and no atom, so a
    failure there names its type and this script's line that led to it.
    Its message, which can quote a value, is still dropped."""
    import inspect

    _main_environment(tmp_path, monkeypatch, _b2_heads(12, 6))

    def failing(_):
        raise IndexError("index 7 is out of bounds for axis 0 with size 7")

    monkeypatch.setattr(script, "read_inputs", failing)
    lines, start = inspect.getsourcelines(script.main)
    (line,) = [
        start + offset
        for offset, text in enumerate(lines)
        if "= read_inputs(" in text
    ]
    out = tmp_path / "counts.json"
    with pytest.raises(SystemExit) as caught:
        script.main(
            ["--out", str(out), "--local-copy", str(tmp_path / "local.json")]
        )
    assert str(caught.value) == (
        f"B0.2 stopped in main, line {line}: IndexError"
    )


@pytest.mark.parametrize(
    ("value", "phase", "expected"),
    [
        (
            -7,
            phase,
            r"^B0\.2 stopped in coarsen, line \d+: ValueError: counts and"
            r" effective sizes must be finite and nonnegative$",
        )
        for phase in (script.READING, script.RELEASE)
    ]
    + [
        ("7", phase, r"^B0\.2 stopped in coarsen, line \d+: TypeError$")
        for phase in (script.READING, script.WRITING)
    ]
    + [
        ("7", phase, r"^B0\.2 stopped in the release$")
        for phase in (script.RELEASE, "an unlisted phase")
    ],
)
def test_only_this_scripts_own_raise_keeps_its_message(value, phase, expected):
    """A message this script's ``raise`` wrote names no value and is kept
    in every phase, though the statement spans lines: which check fired is
    a gate decision. One a builtin wrote while running this script's code
    is dropped; outside the release its type and line are told, and inside
    the release, or in a phase not listed, only the phase."""
    with pytest.raises(SystemExit, match=expected):
        with script.count_free_failures(phase):
            script.coarsen(value, 10)


@pytest.mark.parametrize(
    ("phase", "expected"),
    [
        (
            script.READING,
            r"^B0\.2 stopped in .+, line \d+: (KeyboardInterrupt|SystemExit)$",
        ),
        (script.RELEASE, r"^B0\.2 stopped in the release$"),
    ],
)
@pytest.mark.parametrize(
    "interruption", [KeyboardInterrupt, lambda: SystemExit("size 7")]
)
def test_an_interruption_or_a_librarys_exit_prints_no_chain(
    interruption, phase, expected
):
    """An interruption, or a library's own exit, is a failure like any
    other: its report follows its phase's rule, and the error it
    interrupted, whose message may quote a size, is not chained to it."""

    def failing():
        try:
            raise ValueError("an atom of size 7")
        except ValueError:
            # Chained to the ValueError, as a library's would be.
            raise interruption()  # noqa: B904

    with pytest.raises(SystemExit, match=expected) as caught:
        with script.count_free_failures(phase):
            failing()
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__


def test_warnings_inside_the_guard_are_dropped_unseen(capsys):
    """A warning prints nothing, not even its place: whether one fires,
    and where, can depend on the data. Warnings outside the guard are
    untouched."""
    import warnings

    with warnings.catch_warnings(record=True) as seen:
        warnings.simplefilter("always")
        with script.count_free_failures(script.RELEASE):
            warnings.warn("an atom of size 7", RuntimeWarning, stacklevel=1)
        assert seen == []
        warnings.warn("outside the guard", RuntimeWarning, stacklevel=1)
        assert [str(warning.message) for warning in seen] == [
            "outside the guard"
        ]
    assert capsys.readouterr() == ("", "")


def _c_stdout(libc):
    """The C library's standard output stream (macOS, then glibc)."""
    import ctypes

    for name in ("__stdoutp", "stdout"):
        try:
            return ctypes.c_void_p.in_dll(libc, name)
        except ValueError:
            continue
    pytest.skip("this C library names no standard output stream")


@pytest.mark.parametrize("fails", [False, True])
def test_nothing_printed_inside_the_guard_is_seen(capfd, fails):
    """Condition 2 on output. Inside the guard, descriptors 1 and 2 point
    at the null device and Python's streams at a null stream, so nothing
    printed there is seen: not through Python, not through a write to a
    descriptor, and not through the C library's buffered stream, which is
    flushed before the descriptors are restored. A failure's report is
    the one line, raised after they are restored; output after the guard
    is seen again."""
    import ctypes

    libc = ctypes.CDLL(None)
    libc.fputs.argtypes = [ctypes.c_char_p, ctypes.c_void_p]
    stream = _c_stdout(libc)
    libc.fflush(None)
    capfd.readouterr()
    before = (os.fstat(1).st_ino, os.fstat(2).st_ino)
    with pytest.raises(SystemExit) if fails else nullcontext() as caught:
        with script.count_free_failures(script.RELEASE):
            print("atom 7")
            print("atom 7", file=sys.stderr)
            sys.__stdout__.write("atom 7")
            sys.__stderr__.write("atom 7")
            os.write(1, b"atom 7")
            os.write(2, b"atom 7")
            # Buffered with no newline, so it stays in the C library's
            # buffer until something flushes it.
            libc.fputs(b"atom 7", stream)
            if fails:
                raise ValueError("an atom of size 7")
    if fails:
        assert str(caught.value) == "B0.2 stopped in the release"
    assert (os.fstat(1).st_ino, os.fstat(2).st_ino) == before
    print("after")
    libc.fputs(b"after C\n", stream)
    libc.fflush(None)
    sys.__stdout__.flush()
    out, err = capfd.readouterr()
    assert "atom" not in out and "atom" not in err
    assert "after\n" in out and "after C\n" in out


#: The only names a ``raise`` in the count script may put into its message:
#: paths, relation kinds, setting names and file names.
SAFE_MESSAGE_NAMES = {
    "path",
    "kind",
    "left",
    "name",
    "attempt",
    "destination",
    "sorted(missing)",
    "RECHECKS",
    "RECHECK_SECONDS",
}


def test_every_output_the_script_can_make_names_no_value():
    """Condition 2, statically. Each ``raise`` message is a literal, or
    interpolates only names that hold paths and settings; the script
    prints only the output's path; and only ``write_new`` and the attempt
    record write files."""
    import ast

    tree = ast.parse(Path(script.__file__).read_text())
    parents = {
        child: node
        for node in ast.walk(tree)
        for child in ast.iter_child_nodes(node)
    }

    def function(node):
        while node in parents:
            node = parents[node]
            if isinstance(node, ast.FunctionDef):
                return node.name
        return None

    raises = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Raise) and node.exc is not None:
            raises += 1
            exc = node.exc
            if function(node) is None:
                assert ast.unparse(exc) == "SystemExit(main())"
                continue
            assert isinstance(exc, ast.Call), ast.unparse(node)
            assert len(exc.args) <= 1, ast.unparse(node)
            for arg in exc.args:
                if isinstance(arg, ast.Constant):
                    assert isinstance(arg.value, str)
                elif isinstance(arg, ast.JoinedStr):
                    for part in arg.values:
                        if isinstance(part, ast.FormattedValue):
                            assert (
                                ast.unparse(part.value) in SAFE_MESSAGE_NAMES
                            ), ast.unparse(node)
                else:
                    assert (
                        function(node) == "count_free_failures"
                        and ast.unparse(arg) == "failure"
                    ), ast.unparse(node)
    assert raises > 30
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    printed = sorted(
        (function(node), ast.unparse(node))
        for node in calls
        if isinstance(node.func, ast.Name) and node.func.id == "print"
    )
    assert printed == [("main", "print(out)")]
    writes = {
        "open",
        "write",
        "write_text",
        "write_bytes",
        "dump",
        "link",
        "rename",
        "replace",
        "symlink_to",
        "touch",
        "mkdir",
        "savez",
        "to_csv",
        "to_json",
        "to_parquet",
        # Review round 4: NumPy's, pandas', pickle's and shutil's writers.
        "save",
        "savez_compressed",
        "savetxt",
        "tofile",
        "to_pickle",
        "to_hdf",
        "to_excel",
        "to_feather",
        "to_stata",
        "to_sql",
        "to_orc",
        "to_xml",
        "writelines",
        "copyfile",
        "copy2",
        "copytree",
        "copyfileobj",
        "makedirs",
        "truncate",
    }
    writers = {
        function(node)
        for node in calls
        if isinstance(node.func, ast.Attribute) and node.func.attr in writes
    }
    # A writer imported by name, as ``from numpy import save`` would make
    # it, is a writer too; the builtin open() is checked below.
    assert not [
        ast.unparse(node)
        for node in calls
        if isinstance(node.func, ast.Name)
        and node.func.id in writes - {"open"}
    ]
    assert writers == {
        "write_new",
        "_start_attempt",
        "_sha256_file",
        "_silenced",
    }
    # The guard opens the null device and nothing else; no builtin open()
    # writes anywhere else; the C library is used only to flush.
    opened = sorted(
        (function(node), ast.unparse(node))
        for node in calls
        if (isinstance(node.func, ast.Name) and node.func.id == "open")
        or (
            function(node) == "_silenced"
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in writes
        )
    )
    assert opened == [
        ("_silenced", "open(os.devnull, 'w')"),
        ("_silenced", "os.open(os.devnull, os.O_WRONLY)"),
    ]
    assert sorted(
        (function(node), ast.unparse(node))
        for node in calls
        if ast.unparse(node.func).startswith("ctypes")
    ) == [
        ("__init__", "ctypes.CDLL(CORE_FOUNDATION)"),
        ("__init__", "ctypes.CDLL(IOKIT)"),
        ("__init__", "ctypes.CDLL(None)"),
        ("__init__", "ctypes.POINTER(ctypes.c_int)"),
        ("__init__", "ctypes.POINTER(ctypes.c_uint)"),
        ("__init__", "ctypes.POINTER(uint32)"),
        ("_flush_streams", "ctypes.CDLL(None)"),
        ("_flush_streams", "ctypes.CDLL(None).fflush(None)"),
        ("held", "ctypes.byref(level)"),
        ("held", "ctypes.c_int32(0)"),
        ("hold", "ctypes.byref(assertion)"),
        ("hold", "ctypes.c_uint32(0)"),
        ("power_source", "ctypes.create_string_buffer(64)"),
        ("qos_class", "ctypes.byref(qos)"),
        ("qos_class", "ctypes.byref(relative)"),
        ("qos_class", "ctypes.c_int(0)"),
        ("qos_class", "ctypes.c_uint(0)"),
    ]
    # The run's conditions call these C functions and no others: they read
    # the power source and the QoS class, and take, test (its level
    # included) and give back this process's sleep assertions.
    assert sorted(
        {
            node.func.attr
            for node in calls
            if isinstance(node.func, ast.Attribute)
            and ast.unparse(node.func.value)
            in ("self.iokit", "self.cf", "self.libc")
        }
    ) == [
        "CFDictionaryGetValue",
        "CFNumberGetValue",
        "CFRelease",
        "CFStringCreateWithCString",
        "CFStringGetCString",
        "IOPMAssertionCopyProperties",
        "IOPMAssertionCreateWithName",
        "IOPMAssertionRelease",
        "IOPSCopyPowerSourcesInfo",
        "IOPSGetProvidingPowerSourceType",
        "pthread_get_qos_class_np",
        "pthread_self",
    ]
    # main() runs three guarded phases, and the release phase holds only
    # the release.
    (main,) = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "main"
    ]
    phases = [
        (ast.unparse(item.context_expr), statement)
        for statement in main.body
        if isinstance(statement, ast.With)
        for item in statement.items
        if ast.unparse(item.context_expr).startswith("count_free_failures")
    ]
    assert [name for name, _ in phases] == [
        "count_free_failures(READING)",
        "count_free_failures(RELEASE)",
        "count_free_failures(WRITING)",
    ]
    assert [ast.unparse(line) for line in phases[1][1].body] == [
        "local_bytes, public_bytes = release_outputs(person_wave, validity,"
        " anchor, design, committed, provenance,"
        " conditions.before_program)"
    ]
    assert [ast.unparse(line) for line in phases[2][1].body] == [
        "write_new(local, local_bytes)",
        "write_new(out, public_bytes)",
    ]
    (read,) = [
        node
        for node in calls
        if function(node) == "_sha256_file"
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "open"
    ]
    assert ast.unparse(read) == "path.open('rb')"
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert "logging" not in imported and "pickle" not in imported
    # Nor a module that sends or stores a value outside a file the
    # confinement sees (review round 5).
    modules = {
        name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for name in (
            [alias.name for alias in node.names]
            if isinstance(node, ast.Import)
            else [node.module or ""]
        )
    }
    assert not modules & {
        "asyncio",
        "dbm",
        "ftplib",
        "http",
        "logging",
        "mmap",
        "multiprocessing",
        "pickle",
        "shelve",
        "smtplib",
        "socket",
        "sqlite3",
        "ssl",
        "syslog",
        "urllib",
    }


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
        script,
        "release_counts",
        lambda *args, **kwargs: real_release(counts, registry, **kwargs),
    )
    out = tmp_path / "counts.json"
    local = tmp_path / "local.json"
    assert script.main(["--out", str(out), "--local-copy", str(local)]) == 0
    record = json.loads(out.read_text())
    assert record["disclosure"]["status"] == "withheld"
    audit = json.loads(local.read_text())["disclosure_audit"]["audit"]
    # The second seeding ran, but the record says nothing of rounds or of
    # the pool.
    assert set(audit) == {"base", "status", "targets", "class_sizes"}
    assert audit["status"] == "withheld"
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
