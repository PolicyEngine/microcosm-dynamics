"""§22.4 Amendment-8 vectors against the real implementation."""

from __future__ import annotations

import hashlib
import json
from fractions import Fraction

import pytest

from populace_dynamics.data import psid_amendment8_vectors as a8
from populace_dynamics.data.psid_analytic_partition import (
    EMPTY_MEMBER_DOMAIN_SHA256,
    MEMBER_THRESHOLD,
    AnalyticRelation,
    LiteralEntry,
    NormalizedRange,
    RangeEntry,
    analytic_object,
    complement_runs,
    decode_atom,
    encode_atom,
    maximal_runs,
    member_domain_digest,
    merge_runs,
    serialize_relation,
    subtract_runs,
    validate_analytic_object,
)


def _independent_canonical(value: object) -> bytes:
    """Canonicalize without reusing the implementation's serializer."""

    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )


def _independent_large_rows() -> list[dict[str, object]]:
    """Materialize A8-R02's 4,097 rows from the fixture description alone."""

    return [
        {
            "physical_image_raw_token_hex": None,
            "source_member_index": value,
            "source_value": {
                "canonical_value": value,
                "source_meaning": "A8 large analytic partition fixture",
                "typed_disposition": "json_integer",
                "typed_value_unit": "a8_fixture_unit",
                "value_type": "json_integer",
            },
            "unrenderable_reason": "no_exact_width_selected_form_image",
        }
        for value in range(10_000, 14_097)
    ]


def test_a8_vector_relation_identity_is_exact() -> None:
    identity = a8.a8_vector_relation_identity()
    assert identity["vector_array_byte_count"] == 907
    assert identity["vector_array_sha256"] == a8.A8_VECTOR_ARRAY_SHA256
    assert identity["vector_id_array_sha256"] == a8.A8_VECTOR_ID_ARRAY_SHA256
    assert [row["vector_id"] for row in a8.A8_VECTOR_ROWS] == [
        "A8-R01",
        "A8-R02",
        "A8-R03",
        "A8-R04",
    ]


def test_a8_r01_small_explicit_analytic_byte_equivalence() -> None:
    result = a8.a8_r01()
    assert result["status"] == "pass"
    assert result["member_count"] == 3
    assert result["explicit_byte_count"] == 944
    assert result["explicit_sha256"] == a8.R01_EXPLICIT_SHA256
    assert result["analytic_byte_count"] == 207
    assert result["analytic_storage_sha256"] == a8.R01_ANALYTIC_SHA256
    # The two raw storage hashes intentionally differ; equality is at the
    # complete virtual-member byte layer.
    assert result["analytic_storage_sha256"] != result["explicit_sha256"]
    assert result["member_domain_sha256"] == a8.R01_EXPLICIT_SHA256
    assert result["production_arm"] == "explicit"


def test_a8_r01_analytic_fixture_expands_to_the_explicit_bytes() -> None:
    relation = a8.small_fixture_relation()
    explicit = _independent_canonical(list(relation.iter_rows()))
    analytic = _independent_canonical(analytic_object(relation))
    assert len(explicit) == 944
    assert hashlib.sha256(explicit).hexdigest() == a8.R01_EXPLICIT_SHA256
    assert len(analytic) == 207
    assert hashlib.sha256(analytic).hexdigest() == a8.R01_ANALYTIC_SHA256


def test_a8_r02_two_independent_digest_derivations_agree() -> None:
    materialized = _independent_large_rows()
    assert len(materialized) == 4_097
    materialized_bytes = _independent_canonical(materialized)
    assert len(materialized_bytes) == 1_315_139
    assert (
        hashlib.sha256(materialized_bytes).hexdigest()
        == a8.R02_EXPLICIT_SHA256
    )

    result = a8.a8_r02(materialized)
    assert result["status"] == "pass"
    assert result["member_count"] == 4_097
    assert result["analytic_byte_count"] == 222
    assert result["analytic_storage_sha256"] == a8.R02_ANALYTIC_SHA256
    assert result["streamed_byte_count"] == 1_315_139
    assert result["streamed_member_domain_sha256"] == a8.R02_EXPLICIT_SHA256
    assert result["materialized_byte_count"] == 1_315_139
    assert (
        result["materialized_member_domain_sha256"] == a8.R02_EXPLICIT_SHA256
    )
    assert result["production_arm"] == "analytic"
    assert 4_097 > MEMBER_THRESHOLD


def test_a8_r02_streaming_holds_no_member_array() -> None:
    relation = a8.large_fixture_relation()
    rows = relation.iter_rows()
    first = next(rows)
    assert first["source_member_index"] == 10_000
    # The relation is an O(1) description: its analytic arm is 222 bytes
    # while the member sequence it denotes is 1,315,139 bytes.
    length, digest = member_domain_digest(relation)
    assert (length, digest) == (1_315_139, a8.R02_EXPLICIT_SHA256)


def test_a8_r03_rejects_every_negative_before_a_semantic_digest() -> None:
    result = a8.a8_r03()
    assert result["status"] == "pass"
    assert result["negative_count"] == 4
    assert [row["negative_id"] for row in result["rejections"]] == [
        "arity_three_interval_omits_member_count",
        "split_maximal_run_is_noncanonical",
        "count_inconsistent_upper_bound",
        "floating_point_member_count_spelling",
    ]
    assert [row["byte_count"] for row in result["rejections"]] == [
        205,
        219,
        207,
        209,
    ]


@pytest.mark.parametrize("negative", a8.R03_NEGATIVES, ids=lambda row: row[0])
def test_a8_r03_negative_payload_bytes_are_exact(
    negative: tuple[str, dict[str, object], int, str],
) -> None:
    _, payload, byte_count, digest = negative
    raw = _independent_canonical(payload)
    assert len(raw) == byte_count
    assert hashlib.sha256(raw).hexdigest() == digest


def test_a8_r03_float_spelling_is_rejected_though_it_would_expand() -> None:
    """The `3.0` spelling denotes R01's member array but is still invalid."""

    payload = dict(a8.R03_NEGATIVES[3][1])
    with pytest.raises(ValueError, match="member_count must be an integer"):
        validate_analytic_object(
            payload,
            (
                NormalizedRange(
                    source_entry_ref=a8.FIXTURE_ENTRY_REF,
                    lower=Fraction(10),
                    step=Fraction(2),
                    source_member_count=3,
                    value_type="json_integer",
                ),
            ),
        )


def test_a8_r04_fact_table_arithmetic_from_pinned_counts() -> None:
    facts = a8.StorageFacts(
        status_decomposition=a8.R04_STATUS_DECOMPOSITION,
        total_members=a8.R04_TOTAL_MEMBERS,
        explicit_members=a8.R04_EXPLICIT_MEMBERS,
        analytic_members=a8.R04_ANALYTIC_MEMBERS,
        analytic_renderable_members=a8.R04_ANALYTIC_RENDERABLE_MEMBERS,
        analytic_unrenderable_members=a8.R04_ANALYTIC_UNRENDERABLE_MEMBERS,
        analytic_renderable_containers=(a8.R04_ANALYTIC_RENDERABLE_CONTAINERS),
        analytic_unrenderable_containers=(
            a8.R04_ANALYTIC_UNRENDERABLE_CONTAINERS
        ),
        arm_ambiguous_renderable_members=(
            a8.R04_ARM_AMBIGUOUS_RENDERABLE_MEMBERS
        ),
    )
    result = a8.a8_r04(facts)
    assert result["status"] == "pass"
    assert result["empty_object_floor_bytes"] == 2_462_127_537_263
    assert result["row_floor_bytes"] == 266_728_784_621_000
    assert result["row_floor_tib"] == (
        "242.5884164231320028193295001983642578125"
    )
    assert result["available_capacity_multiple"] > 185
    assert result["emitted_artifact"] is None


def test_a8_r04_rejects_the_counterfactual_renderability_placement() -> None:
    facts = a8.StorageFacts(
        status_decomposition=a8.R04_STATUS_DECOMPOSITION,
        total_members=a8.R04_TOTAL_MEMBERS,
        explicit_members=a8.R04_COUNTERFACTUAL_EXPLICIT_MEMBERS,
        analytic_members=a8.R04_COUNTERFACTUAL_ANALYTIC_MEMBERS,
        analytic_renderable_members=a8.R04_ANALYTIC_RENDERABLE_MEMBERS,
        analytic_unrenderable_members=a8.R04_ANALYTIC_UNRENDERABLE_MEMBERS,
        analytic_renderable_containers=(a8.R04_ANALYTIC_RENDERABLE_CONTAINERS),
        analytic_unrenderable_containers=(
            a8.R04_ANALYTIC_UNRENDERABLE_CONTAINERS
        ),
        arm_ambiguous_renderable_members=(
            a8.R04_ARM_AMBIGUOUS_RENDERABLE_MEMBERS
        ),
    )
    with pytest.raises(ValueError, match="A8-R04 fact mismatch"):
        a8.a8_r04(facts)


def test_empty_relation_digest_is_the_retained_value() -> None:
    assert a8.empty_relation_digest() == EMPTY_MEMBER_DOMAIN_SHA256
    empty = AnalyticRelation(entries=())
    assert member_domain_digest(empty) == (3, EMPTY_MEMBER_DOMAIN_SHA256)
    assert serialize_relation(empty) == []


def test_threshold_selects_exactly_one_arm_at_the_boundary() -> None:
    normalized = NormalizedRange(
        source_entry_ref="boundary:range:0",
        lower=Fraction(0),
        step=Fraction(1),
        source_member_count=MEMBER_THRESHOLD + 1,
        value_type="json_integer",
    )

    def build(item: NormalizedRange, index: int) -> dict[str, object]:
        return {"source_member_index": index}

    at_threshold = AnalyticRelation(
        entries=(RangeEntry(normalized, ((0, MEMBER_THRESHOLD),), build),)
    )
    over_threshold = AnalyticRelation(
        entries=(RangeEntry(normalized, ((0, MEMBER_THRESHOLD + 1),), build),)
    )
    assert isinstance(serialize_relation(at_threshold), list)
    assert isinstance(serialize_relation(over_threshold), dict)
    assert (
        serialize_relation(over_threshold)["representation"]
        == "analytic_closed_intervals_v1"
    )


def test_rational_atoms_are_reduced_ascii_strings() -> None:
    assert encode_atom(Fraction(1, 100), "rational") == "1/100"
    assert encode_atom(Fraction(10), "rational") == "10/1"
    assert encode_atom(Fraction(0), "rational") == "0/1"
    assert encode_atom(Fraction(-3, 2), "rational") == "-3/2"
    assert encode_atom(Fraction(10), "json_integer") == 10
    assert decode_atom("1/100", "rational") == Fraction(1, 100)
    for spelling in ("+1/2", "1/0", "01/2", "-0/1", "1 / 2", "1.5", "2/4"):
        with pytest.raises(ValueError):
            decode_atom(spelling, "rational")
    for spelling in (True, 1.0, "1"):
        with pytest.raises(ValueError):
            decode_atom(spelling, "json_integer")


def test_run_algebra_is_exact() -> None:
    assert maximal_runs([0, 1, 2, 5, 6, 9]) == ((0, 3), (5, 2), (9, 1))
    assert merge_runs([(0, 3), (3, 2), (7, 1)]) == ((0, 5), (7, 1))
    assert complement_runs(((0, 3), (5, 2)), 9) == ((3, 2), (7, 2))
    assert subtract_runs(((0, 10),), ((2, 3), (7, 1))) == (
        (0, 2),
        (5, 2),
        (8, 2),
    )
    assert subtract_runs(((0, 4),), ((0, 4),)) == ()


def test_literal_and_range_members_interleave_in_source_entry_order() -> None:
    normalized = NormalizedRange(
        source_entry_ref="mixed:range:1",
        lower=Fraction(0),
        step=Fraction(1),
        source_member_count=3,
        value_type="json_integer",
    )
    relation = AnalyticRelation(
        entries=(
            LiteralEntry("mixed:entry:0", {"tag": "literal-0"}),
            RangeEntry(
                normalized,
                ((0, 3),),
                lambda item, index: {"tag": f"range-{index}"},
            ),
            LiteralEntry("mixed:entry:2", {"tag": "literal-2"}),
        )
    )
    assert [row["tag"] for row in relation.iter_rows()] == [
        "literal-0",
        "range-0",
        "range-1",
        "range-2",
        "literal-2",
    ]
    obj = analytic_object(relation)
    assert obj["literal_member_rows"] == [
        {"tag": "literal-0"},
        {"tag": "literal-2"},
    ]
    assert obj["total_member_count"] == 5
    assert obj["range_interval_rows"] == [
        {
            "source_entry_ref": "mixed:range:1",
            "intervals": [[0, 2, 1, 3]],
            "member_count": 3,
        }
    ]


def test_run_amendment_8_vectors_executes_in_order() -> None:
    facts = a8.StorageFacts(
        status_decomposition=a8.R04_STATUS_DECOMPOSITION,
        total_members=a8.R04_TOTAL_MEMBERS,
        explicit_members=a8.R04_EXPLICIT_MEMBERS,
        analytic_members=a8.R04_ANALYTIC_MEMBERS,
        analytic_renderable_members=a8.R04_ANALYTIC_RENDERABLE_MEMBERS,
        analytic_unrenderable_members=a8.R04_ANALYTIC_UNRENDERABLE_MEMBERS,
        analytic_renderable_containers=(a8.R04_ANALYTIC_RENDERABLE_CONTAINERS),
        analytic_unrenderable_containers=(
            a8.R04_ANALYTIC_UNRENDERABLE_CONTAINERS
        ),
        arm_ambiguous_renderable_members=(
            a8.R04_ARM_AMBIGUOUS_RENDERABLE_MEMBERS
        ),
    )
    results = a8.run_amendment_8_vectors(
        facts,
        materialized_rows=_independent_large_rows(),
    )
    assert [row["vector_id"] for row in results] == [
        "A8-R01",
        "A8-R02",
        "A8-R03",
        "A8-R04",
    ]
    assert all(row["status"] == "pass" for row in results)
