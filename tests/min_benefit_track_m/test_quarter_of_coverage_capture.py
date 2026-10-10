"""The committed quarter-of-coverage capture (plan item M2) and 413(d).

The capture ``data/external/ssa_quarter_of_coverage_amounts.json`` is
pinned by SHA-256 and read by :func:`coverage.load_qc_amounts`.  These
tests read only the committed file; the statutory rule's properties run
on an INVENTED wage index.  The recapture from the policyengine-us
checkout is ``test_quarter_of_coverage_recapture.py``.
"""

from __future__ import annotations

import hashlib
import json
import math
import shutil
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.min_benefit_track_m import coverage

ROOT = Path(__file__).resolve().parents[2]
CAPTURE = ROOT / "data" / "external" / "ssa_quarter_of_coverage_amounts.json"
#: The policyengine-us file the capture was taken from (M1 specification,
#: section 2) and the statute copy its value check cites (section 21).
PE_US_FILE_SHA256 = (
    "12354a0585756dbffcd9fae6aa6b49b2420619e9ec8e47c5ef953c41693f242b"
)
STATUTE_COPY_SHA256 = (
    "7d226c0a476d5bf83f07c06deef8b4563cbdc633a6ddf4b5921bc0afc654671c"
)


def test_the_capture_is_the_pinned_file():
    assert CAPTURE == coverage.QC_CAPTURE_PATH
    digest = hashlib.sha256(CAPTURE.read_bytes()).hexdigest()
    assert digest == coverage.QC_CAPTURE_SHA256
    qc = coverage.load_qc_amounts()
    assert qc.source == {
        "kind": "committed_capture",
        "path": "data/external/ssa_quarter_of_coverage_amounts.json",
        "sha256": coverage.QC_CAPTURE_SHA256,
        "captured_from": str(coverage.QC_PARAMETER_PATH),
        "captured_from_sha256": PE_US_FILE_SHA256,
        "pe_us_revision": "a03e82e503",
    }
    assert sorted(qc.amounts) == list(range(1978, 2027))


def test_the_capture_records_its_value_check():
    document = json.loads(CAPTURE.read_text(encoding="utf-8"))
    check = document["value_check"]
    assert check["differences"] == []
    assert check["years_checked"] == [1978, 2026]
    assert check["statute"]["provision"] == "42 USC 413(d)(1)-(2)"
    assert check["statute"]["copy_sha256"] == STATUTE_COPY_SHA256
    assert check["table2_label_check"]["passes"] is True
    assert document["source"]["sha256"] == PE_US_FILE_SHA256
    assert document["schema_version"] == coverage.QC_CAPTURE_SCHEMA


def test_the_amounts_follow_the_statutes_shape():
    """413(d): $250 in 1978, never lower than the year before, and each
    later amount a multiple of $10; four quarters in 2006 is $3,880 (the
    Table 2 label, ruling C5)."""

    amounts = coverage.load_qc_amounts().amounts
    years = sorted(amounts)
    assert amounts[1978] == coverage.QC_1978 == 250.0
    for year in years[1:]:
        assert amounts[year] >= amounts[year - 1], year
        assert amounts[year] % 10 == 0, year
    assert 4 * amounts[2006] == 3_880.0


def test_a_changed_or_missing_capture_is_refused(tmp_path):
    copy = tmp_path / "qc.json"
    shutil.copy(CAPTURE, copy)
    assert coverage.load_qc_amounts(copy).amounts[2022] == 1_510.0
    copy.write_bytes(
        copy.read_bytes().replace(b'"2022": 1510', b'"2022": 1520')
    )
    with pytest.raises(ValueError, match="pinned"):
        coverage.load_qc_amounts(copy)
    other = tmp_path / "other.json"
    other.write_text(
        json.dumps({"schema_version": "x", "amounts": {}}), encoding="utf-8"
    )
    digest = hashlib.sha256(other.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="schema"):
        coverage.load_qc_amounts(other, expected_sha256=digest)
    with pytest.raises(FileNotFoundError, match="capture"):
        coverage.load_qc_amounts(tmp_path / "absent.json")


# ---------------------------------------------------------------------------
# 413(d)(2)'s rounding and recursion (properties; INVENTED wage indexes)
# ---------------------------------------------------------------------------
@given(st.floats(min_value=0, max_value=1e6, allow_nan=False))
def test_rounding_to_ten_is_to_the_nearest_ten(value):
    rounded = coverage.round_to_ten(value)
    assert rounded % 10 == 0
    assert abs(rounded - value) <= 5 + 1e-9
    assert coverage.round_to_ten(rounded) == rounded


@given(st.integers(min_value=0, max_value=100_000))
def test_a_multiple_of_five_not_ten_rounds_up(tens):
    value = 10 * tens + 5
    assert coverage.round_to_ten(value) == 10 * tens + 10
    assert coverage.round_to_ten(10 * tens) == 10 * tens


def test_rounding_refuses_what_is_not_finite():
    for value in (math.inf, math.nan):
        with pytest.raises(ValueError, match="finite"):
            coverage.round_to_ten(value)


_growth = st.lists(
    st.floats(min_value=-0.05, max_value=0.12, allow_nan=False),
    min_size=60,
    max_size=60,
)


@settings(max_examples=60, deadline=None)
@given(_growth, st.floats(min_value=5_000, max_value=15_000))
def test_the_statutory_amounts_are_a_ratchet_of_rounded_wage_ratios(
    growth, awi_1976
):
    """For any wage path: $250 in 1978; each year the larger of the year
    before and $250 x AWI(y - 2) / AWI(1976), rounded to $10; so the
    series never falls, is a multiple of $10 after 1978 and moves with
    the wage index."""

    nawi = {1975: awi_1976 / 1.07, 1976: awi_1976}
    for offset, rate in enumerate(growth):
        year = 1977 + offset
        nawi[year] = nawi[year - 1] * (1 + rate)
    last = 1977 + len(growth) + 1
    amounts = coverage.statutory_qc_amounts(nawi, last)
    assert amounts[1978] == 250.0
    for year in range(1979, last + 1):
        wage_amount = coverage.round_to_ten(250 * nawi[year - 2] / awi_1976)
        assert amounts[year] == max(amounts[year - 1], wage_amount)
        assert amounts[year] >= amounts[year - 1]
        assert amounts[year] % 10 == 0


def test_the_statutory_amounts_need_the_1976_wage_index():
    with pytest.raises(KeyError, match="1976"):
        coverage.statutory_qc_amounts({1977: 1.0}, 1980)
    with pytest.raises(KeyError, match="1977"):
        coverage.statutory_qc_amounts({1976: 9_000.0}, 1980)


def test_the_specification_records_the_committed_capture():
    """Differential: the M1 specification's ``sources`` record equals the
    capture the loader reads (file, SHA-256, and the policyengine-us file
    and revision it came from), so the registered entry point's parameter
    pins pass on the committed files, and fail on any other."""

    from populace_dynamics.min_benefit_track_m import rules
    from populace_dynamics.min_benefit_track_m import specification as m1

    block = m1.m1_parameter_block()["sources"]
    recorded = block["quarter_of_coverage_amounts"]
    source = coverage.load_qc_amounts().source
    assert recorded["file"] == source["path"]
    assert recorded["sha256"] == source["sha256"] == coverage.QC_CAPTURE_SHA256
    assert recorded["captured_from"] == source["captured_from"]
    assert recorded["captured_from_sha256"] == source["captured_from_sha256"]
    assert recorded["captured_from_pe_us_revision"] == (
        source["pe_us_revision"]
    )
    assert recorded["years"] == [
        min(coverage.load_qc_amounts().amounts),
        max(coverage.load_qc_amounts().amounts),
    ]
    census = rules.load_aged_thresholds().source
    assert block["census_thresholds"]["sha256"] == census["sha256"]
    assert block["census_thresholds"]["file"] == census["path"]
    assert block["census_thresholds"]["captured_years"] == (
        census["captured_years"]
    )
