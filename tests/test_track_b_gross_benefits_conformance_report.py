"""G's exhaustive finite invented denominator and refusal witnesses.

Verification class: statutory conformance. This report describes only the
documented invented configuration lattice, not a population or a forecast.
The statutory-example registry has a separate denominator. Monthly history
protection and multi-record refusals have separate named invented witnesses.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from math import comb

import pytest
import yaml
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from scripts import track_b_g_conformance_report as report


@pytest.fixture(scope="module")
def regenerated():
    return report.build_report()


@st.composite
def lattice_cases(draw):
    roles = draw(st.lists(st.sampled_from(tuple(g.Role)), max_size=2))
    roles = tuple(sorted(roles, key=report.ROLE_INDEX.__getitem__))
    scope, condition = draw(st.sampled_from(report.declared_conditions()))
    return report.Configuration(
        draw(st.sampled_from(tuple(g.FamilyKind))),
        roles,
        draw(st.sampled_from(report.DUAL_MODES)),
        draw(st.sampled_from(report.REDUCTION_FLAGS)),
        draw(st.sampled_from(tuple(report.PAYMENT_ERAS))),
        scope,
        condition,
    )


def _histogram(cases):
    statuses, reasons = Counter(), Counter()
    for case in cases:
        status, reason = report.classify_configuration(case)
        statuses[status] += 1
        if reason is not None:
            reasons[reason] += 1
    return statuses, reasons


def test_committed_invented_conformance_report_regenerates_byte_for_byte(
    regenerated,
):
    assert report.DEFAULT_OUTPUT.read_bytes() == report.report_bytes(
        regenerated
    )


def test_lattice_is_the_complete_documented_cartesian_product(regenerated):
    # Stars-and-bars counts multisets independently of the iterator. Keeping
    # all nine roles, including invalid record-role pairs, is intentional.
    multisets = sum(comb(len(g.Role) + size - 1, size) for size in range(3))
    condition_choices = (
        1 + len(g.RecordCondition) + len(g.BeneficiaryCondition)
    )
    expected = len(g.FamilyKind) * multisets * 8 * 2 * 3 * condition_choices
    keys = [case.key for case in report.configurations()]
    assert multisets == 55
    assert condition_choices == 15
    assert expected == 118800
    assert len(keys) == len(set(keys)) == expected
    assert regenerated["lattice"]["denominator"]["rows"] == expected
    definition = regenerated["lattice"]["definition"]
    assert definition["role_multiset_count"] == multisets
    assert definition["role_enum_order"] == [role.value for role in g.Role]
    assert set(definition["payment_eras"].values()) == {
        "1999-09",
        "2023-12",
        "2024-01",
    }


def test_lattice_preserves_supported_refused_and_invalid_denominators(
    regenerated,
):
    lattice = regenerated["lattice"]
    counts = lattice["denominator"]
    assert counts["rows"] == sum(
        counts[status] for status in ("supported", "refused", "invalid")
    )
    assert all(counts[status] > 0 for status in counts)
    assert sum(lattice["refused_by_reason"].values()) == counts["refused"]
    assert set(lattice["refused_by_reason"]) == {
        reason.value for reason in g.UnsupportedReason
    }
    by_era = lattice["by_payment_era"]
    for status in ("rows", "supported", "refused", "invalid"):
        assert sum(era[status] for era in by_era.values()) == counts[status]
    for era in by_era.values():
        assert era["rows"] == counts["rows"] // 3
        assert (
            era["rows"] == era["supported"] + era["refused"] + era["invalid"]
        )


def test_statutory_registry_counts_are_separate_and_source_file_is_pinned(
    regenerated,
):
    raw = report.DEFAULT_REGISTRY.read_bytes()
    registry = yaml.safe_load(raw)
    expected = Counter({tag: 0 for tag in registry["tag_vocabulary"]})
    for example in registry["examples"]:
        expected.update(example["tags"])
    actual = regenerated["registry"]
    assert actual["sha256"] == hashlib.sha256(raw).hexdigest()
    assert actual["examples"] == len(registry["examples"])
    assert actual["figures"] == sum(
        len(example["expected"]) for example in registry["examples"]
    )
    assert actual["counts_by_class"] == dict(expected)
    assert set(actual["supported_classes"]) == set(
        registry["supported_classes"]
    )
    assert actual["invented_only_classes"] == registry["invented_only_classes"]
    assert regenerated["verification_class"] == "statutory_conformance"
    assert "no population" in regenerated["admitted_scope"]
    assert "invented" in regenerated["denominator_kind"]


@pytest.mark.parametrize(
    "reason", tuple(g.UnsupportedReason), ids=lambda r: r.value
)
def test_every_retained_refusal_has_an_executed_named_witness(reason):
    _, compute = report.refusal_witnesses()[reason]
    with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
        compute()
    assert caught.value.reason is reason


def test_named_witness_denominator_is_separate_from_the_lattice(regenerated):
    witnesses = regenerated["supplemental_refusal_witnesses"]
    assert len(g.UnsupportedReason) == 23
    assert witnesses["denominator"] == {
        "rows": 23,
        "supported": 0,
        "refused": 23,
        "invalid": 0,
    }
    expected = {reason.value for reason in g.UnsupportedReason}
    assert set(witnesses["refused_by_reason"]) == expected
    assert set(witnesses["refused_by_reason"].values()) == {1}
    assert {row["id"] for row in witnesses["witnesses"]} == expected
    assert all(row["status"] == "refused" for row in witnesses["witnesses"])
    assert "separate denominator" in witnesses["scope"]


@given(st.lists(lattice_cases(), max_size=8))
@settings(max_examples=50, deadline=None)
def test_property_classification_counts_are_conserved_deterministic_and_order_independent(
    cases,
):
    statuses, reasons = _histogram(cases)
    assert sum(statuses.values()) == len(cases)
    assert sum(reasons.values()) == statuses["refused"]
    assert set(statuses) <= {"supported", "refused", "invalid"}
    assert set(reasons) <= {reason.value for reason in g.UnsupportedReason}
    assert _histogram(cases) == _histogram(list(reversed(cases)))
    assert _histogram(cases) == (statuses, reasons)
    summary = {
        "rows": len(cases),
        "statuses": dict(statuses),
        "refused_by_reason": dict(reasons),
    }
    encoded = report.report_bytes(summary)
    assert encoded.endswith(b"\n")
    assert encoded == report.report_bytes(json.loads(encoded))
    assert encoded == report.report_bytes(
        dict(reversed(list(summary.items())))
    )


@given(
    st.sampled_from(tuple(g.FamilyKind)),
    st.sampled_from(
        (
            g.RecordCondition.WORKERS_COMPENSATION_OFFSET,
            g.RecordCondition.ADMINISTRATIVE_FINALITY,
            g.RecordCondition.NON_AIME_FORMULA_PIA,
        )
    ),
    st.sampled_from(tuple(report.PAYMENT_ERAS)),
)
@settings(max_examples=30, deadline=None)
def test_property_invalid_record_role_pairs_precede_declared_coverage_refusals(
    kind, condition, era
):
    bad_role = g.Role.SPOUSE if kind is g.FamilyKind.SURVIVOR else g.Role.WIDOW
    case = report.Configuration(
        kind, (bad_role,), "none", 0, era, "record", condition
    )
    assert report.classify_configuration(case) == ("invalid", None)


@given(
    st.sampled_from(tuple(g.FamilyKind)),
    st.sampled_from(tuple(report.PAYMENT_ERAS)),
    st.one_of(
        st.tuples(
            st.sampled_from(report.DUAL_MODES[1:]),
            st.just(0),
            st.just(("none", None)),
        ),
        st.tuples(st.just("none"), st.just(36), st.just(("none", None))),
        st.tuples(
            st.just("none"),
            st.just(0),
            st.tuples(
                st.just("beneficiary"),
                st.sampled_from(tuple(g.BeneficiaryCondition)),
            ),
        ),
    ),
)
@settings(max_examples=30, deadline=None)
def test_property_empty_multiset_focal_flags_are_invalid(kind, era, fields):
    dual, reductions, (scope, condition) = fields
    case = report.Configuration(
        kind, (), dual, reductions, era, scope, condition
    )
    assert report.classify_configuration(case) == ("invalid", None)


def test_report_serialization_is_canonical_sorted_json(regenerated):
    encoded = report.report_bytes(regenerated)
    assert encoded.endswith(b"\n")
    assert encoded == report.report_bytes(json.loads(encoded))
