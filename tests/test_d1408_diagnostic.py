"""Invented-input checks of aggregate diagnostic publication guards."""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from scripts.d1408_common import PSID_ROOT
from scripts.d1408_diagnostic import (
    projection_pre1917,
    psid_relative,
    validate_publication,
)


@settings(deadline=None)
@given(st.integers(min_value=0, max_value=8))
def test_nested_record_identifiers_are_refused(depth):
    value = {"person_id": "invented"}
    for _ in range(depth):
        value = {"aggregate": [value]}
    with pytest.raises(ValueError, match="record-level"):
        validate_publication(value)


@settings(deadline=None)
@given(st.integers(min_value=10, max_value=100000), st.integers(0, 8))
def test_aggregate_counts_and_suppression_are_admitted(count, depth):
    value = {"people": count, "worker_records": count, "change": 0.0}
    for _ in range(depth):
        value = {"results": [value]}
    assert validate_publication(value) is None


_PSID_PART = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789_.", min_size=1, max_size=12
).filter(lambda part: part not in {".", ".."})


@settings(deadline=None)
@given(st.lists(_PSID_PART, min_size=1, max_size=4))
def test_psid_reads_publish_relative_to_the_psid_root(parts):
    published = psid_relative(str(PSID_ROOT.joinpath(*parts)))
    assert published == "/".join(("psid-data", *parts))
    assert str(PSID_ROOT) not in published


def test_psid_reads_outside_the_root_are_refused():
    with pytest.raises(ValueError, match="outside the PSID root"):
        psid_relative("/invented/elsewhere/FAM1968.txt")
    assert psid_relative("psid-data/family/x.txt") == "psid-data/family/x.txt"


@settings(deadline=None)
@given(
    st.lists(
        st.sampled_from(
            ("factor_evaluation", "recipient", "positive_worker_payment")
        ),
        max_size=3,
    ),
    st.booleans(),
)
def test_projection_pre1917_states_zero_only_without_unsupported_cells(
    roles, unsupported
):
    wave = {"seed_cohort_weight": 10.0, "denominator": "invented"}
    wave.update({f"supported/{role}": {"people": 0} for role in roles})
    if unsupported:
        wave["unsupported_pre1917/factor_evaluation"] = {"people": "<10"}
    result = {"counts": {"2011": {"denominator": "invented"}, "2009": wave}}
    assert projection_pre1917(result) == ("see counts" if unsupported else 0)
    assert projection_pre1917({}) == 0
