"""The mandatory §22.4 Amendment-8 representation vectors.

§22.9.1 step 4 requires the builder to run A8-R01 through A8-R04 in order,
after A6-R01 through A6-R11 and the pre-Q5 A7 sequence, reproducing every
payload byte count, storage SHA, virtual-member SHA, negative rejection, and
storage-bound fact.  These four rows are representation-layer fixtures: they
prove the explicit and analytic arms are one relation, never that a fixture
field could take a compiled terminal.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, localcontext
from fractions import Fraction
from typing import Any

from .psid_analytic_partition import (
    AnalyticRelation,
    MEMBER_THRESHOLD,
    NormalizedRange,
    RangeEntry,
    analytic_object,
    member_domain_digest,
    serialize_relation,
    validate_analytic_object,
)
from .psid_canonical_stream import canonical_stream_digest
from .psid_source_compiler import canonical_json_bytes, sha256_bytes

FIXTURE_ENTRY_REF = "a8-fixture:range:0"
FIXTURE_UNIT = "a8_fixture_unit"
SMALL_MEANING = "A8 small analytic partition fixture"
LARGE_MEANING = "A8 large analytic partition fixture"
UNRENDERABLE_REASON = "no_exact_width_selected_form_image"

A8_VECTOR_ROWS = (
    {
        "member_count": 3,
        "primary_sha256": (
            "fe48cb775d9a695a462834c807ef7b5ef773b1866ed558822d2fcce137514a78"
        ),
        "required_result": (
            "pass_byte_exact_bijection_and_equal_member_digest"
        ),
        "vector_id": "A8-R01",
        "vector_kind": "small_explicit_analytic_equivalence",
    },
    {
        "member_count": 4_097,
        "primary_sha256": (
            "063204ad9b973e0c74681aea5b7015cd1e5e868a6664de45de50943361eaac4e"
        ),
        "required_result": "pass_two_independent_digest_derivations",
        "vector_id": "A8-R02",
        "vector_kind": "large_analytic_two_way_streaming_digest",
    },
    {
        "member_count": 3,
        "primary_sha256": (
            "3160774b10614665daaa4222251fd5fa894a7c627fc04ebfa40444464d3e0ab9"
        ),
        "required_result": "reject_before_semantic_digest",
        "vector_id": "A8-R03",
        "vector_kind": "lossy_ambiguous_analytic_rejection",
    },
    {
        "member_count": 820_709_179_087,
        "primary_sha256": None,
        "required_result": "prove_explicit_storage_exceeds_available_storage",
        "vector_id": "A8-R04",
        "vector_kind": "revision_9_storage_impossibility",
    },
)
A8_VECTOR_ARRAY_BYTES = 907
A8_VECTOR_ARRAY_SHA256 = (
    "c405b3a7f228b3e3286714d21aadedcdd6e3df990714e2ddaef85c861e13a8c4"
)
A8_VECTOR_ID_ARRAY_SHA256 = (
    "0d6a8061baf6378bbb2ac20d05410dc2a12c0f096344445798159437238154f1"
)

R01_EXPLICIT_BYTES = 944
R01_EXPLICIT_SHA256 = (
    "fe48cb775d9a695a462834c807ef7b5ef773b1866ed558822d2fcce137514a78"
)
R01_ANALYTIC_BYTES = 207
R01_ANALYTIC_SHA256 = (
    "bc5a85e43ba6e26345bbf3e49fc9a9915b0fe4912580103c4f2172acc4ed338e"
)
R02_ANALYTIC_BYTES = 222
R02_ANALYTIC_SHA256 = (
    "6fe2c1613e97f6258873163601a61aa7737c34e60e62116ddac8863a595d15d5"
)
R02_EXPLICIT_BYTES = 1_315_139
R02_EXPLICIT_SHA256 = (
    "063204ad9b973e0c74681aea5b7015cd1e5e868a6664de45de50943361eaac4e"
)

R03_NEGATIVES = (
    (
        "arity_three_interval_omits_member_count",
        {
            "literal_member_rows": [],
            "range_interval_rows": [
                {
                    "intervals": [[10, 14, 2]],
                    "member_count": 3,
                    "source_entry_ref": FIXTURE_ENTRY_REF,
                }
            ],
            "representation": "analytic_closed_intervals_v1",
            "total_member_count": 3,
        },
        205,
        "3160774b10614665daaa4222251fd5fa894a7c627fc04ebfa40444464d3e0ab9",
    ),
    (
        "split_maximal_run_is_noncanonical",
        {
            "literal_member_rows": [],
            "range_interval_rows": [
                {
                    "intervals": [[10, 12, 2, 2], [14, 14, 2, 1]],
                    "member_count": 3,
                    "source_entry_ref": FIXTURE_ENTRY_REF,
                }
            ],
            "representation": "analytic_closed_intervals_v1",
            "total_member_count": 3,
        },
        219,
        "661df9d3afb6ec2dfa711727ae6d9ed890751db17f054a988cca951be9f848a7",
    ),
    (
        "count_inconsistent_upper_bound",
        {
            "literal_member_rows": [],
            "range_interval_rows": [
                {
                    "intervals": [[10, 14, 2, 2]],
                    "member_count": 2,
                    "source_entry_ref": FIXTURE_ENTRY_REF,
                }
            ],
            "representation": "analytic_closed_intervals_v1",
            "total_member_count": 2,
        },
        207,
        "560aa8ad616851bb14e1e15d9b411f1258fed769c171652d7b9660fc2decf66f",
    ),
    (
        "floating_point_member_count_spelling",
        {
            "literal_member_rows": [],
            "range_interval_rows": [
                {
                    "intervals": [[10, 14, 2, 3]],
                    "member_count": 3.0,
                    "source_entry_ref": FIXTURE_ENTRY_REF,
                }
            ],
            "representation": "analytic_closed_intervals_v1",
            "total_member_count": 3,
        },
        209,
        "ca4768c2ef8b67f4a63bdc3971dea3e1e7909a1c177bedc9b0a760e15faf0aef",
    ),
)

R04_STATUS_DECOMPOSITION = (
    ("compiled_source_numeric_grammar", 17_329, 30_452, 820_025_893_984),
    (
        "compiled_source_numeric_grammar_padding_underdetermined_"
        "exact_replay",
        1_853,
        1_853,
        865_268,
    ),
    (
        "compiled_source_numeric_grammar_finite_domain_arm_ambiguous_"
        "exact_replay",
        674,
        1_433,
        384_135,
    ),
    (
        "compiled_source_numeric_grammar_partial_range_exact_replay",
        47,
        48,
        682_035_700,
    ),
)
R04_COMPLETE_FIELDS = 19_903
R04_COMPLETE_RANGE_ENTRIES = 33_786
R04_TOTAL_MEMBERS = 820_709_179_087
R04_EXPLICIT_MEMBERS = 4_736_892
R04_ANALYTIC_MEMBERS = 820_704_442_195
R04_ANALYTIC_RENDERABLE_MEMBERS = 820_701_994_620
R04_ANALYTIC_UNRENDERABLE_MEMBERS = 2_447_575
R04_ANALYTIC_RENDERABLE_CONTAINERS = 9_019
R04_ANALYTIC_UNRENDERABLE_CONTAINERS = 36
R04_ANALYTIC_CONTAINERS = 9_055
R04_ARM_AMBIGUOUS_RENDERABLE_MEMBERS = 56_480
R04_EMPTY_OBJECT_FLOOR_BYTES = 2_462_127_537_263
R04_RENDERABLE_ROW_FLOOR_BYTES = 325
R04_UNRENDERABLE_ROW_FLOOR_BYTES = 260
R04_ROW_FLOOR_BYTES = 266_728_784_621_000
R04_ROW_FLOOR_TIB = "242.5884164231320028193295001983642578125"
R04_AVAILABLE_TIB = Fraction(163, 125)
R04_COUNTERFACTUAL_EXPLICIT_MEMBERS = 4_753_875
R04_COUNTERFACTUAL_ANALYTIC_MEMBERS = 820_704_425_212

_TIB = 2**40


def _fixture_row(
    normalized: NormalizedRange,
    index: int,
    meaning: str,
) -> dict[str, Any]:
    value = normalized.value(index)
    return {
        "physical_image_raw_token_hex": None,
        "source_member_index": index,
        "source_value": {
            "canonical_value": value.numerator,
            "source_meaning": meaning,
            "typed_disposition": "json_integer",
            "typed_value_unit": FIXTURE_UNIT,
            "value_type": "json_integer",
        },
        "unrenderable_reason": UNRENDERABLE_REASON,
    }


def small_fixture_relation() -> AnalyticRelation:
    """Return A8-R01's three-member ``json_integer`` fixture relation."""

    normalized = NormalizedRange(
        source_entry_ref=FIXTURE_ENTRY_REF,
        lower=Fraction(10),
        step=Fraction(2),
        source_member_count=3,
        value_type="json_integer",
    )
    return AnalyticRelation(
        entries=(
            RangeEntry(
                normalized=normalized,
                runs=((0, 3),),
                build_row=lambda item, index: _fixture_row(
                    item, index, SMALL_MEANING
                ),
            ),
        )
    )


def large_fixture_relation() -> AnalyticRelation:
    """Return A8-R02's 4,097-member subset of the 0–14,096 parent range."""

    normalized = NormalizedRange(
        source_entry_ref=FIXTURE_ENTRY_REF,
        lower=Fraction(0),
        step=Fraction(1),
        source_member_count=14_097,
        value_type="json_integer",
    )
    return AnalyticRelation(
        entries=(
            RangeEntry(
                normalized=normalized,
                runs=((10_000, 4_097),),
                build_row=lambda item, index: _fixture_row(
                    item, index, LARGE_MEANING
                ),
            ),
        )
    )


def _fixture_ranges() -> tuple[NormalizedRange, ...]:
    return (
        NormalizedRange(
            source_entry_ref=FIXTURE_ENTRY_REF,
            lower=Fraction(10),
            step=Fraction(2),
            source_member_count=3,
            value_type="json_integer",
        ),
    )


def a8_r01() -> dict[str, Any]:
    """Prove the small explicit and analytic arms are one member sequence."""

    relation = small_fixture_relation()
    explicit = list(relation.iter_rows())
    explicit_bytes = canonical_json_bytes(explicit)
    analytic = analytic_object(relation)
    analytic_bytes = canonical_json_bytes(analytic)
    member_length, member_digest = member_domain_digest(relation)

    # Inverse then forward: the validated analytic arm resolves back to the
    # same runs, and re-encoding those runs reproduces the analytic bytes.
    resolved = validate_analytic_object(analytic, _fixture_ranges())
    rebuilt = AnalyticRelation(
        entries=(
            RangeEntry(
                normalized=resolved["resolved_range_runs"][0][0],
                runs=resolved["resolved_range_runs"][0][1],
                build_row=lambda item, index: _fixture_row(
                    item, index, SMALL_MEANING
                ),
            ),
        )
    )
    rebuilt_explicit_bytes = canonical_json_bytes(list(rebuilt.iter_rows()))
    rebuilt_analytic_bytes = canonical_json_bytes(analytic_object(rebuilt))

    if len(explicit_bytes) != R01_EXPLICIT_BYTES:
        raise ValueError("A8-R01 explicit byte count mismatch")
    if sha256_bytes(explicit_bytes) != R01_EXPLICIT_SHA256:
        raise ValueError("A8-R01 explicit digest mismatch")
    if len(analytic_bytes) != R01_ANALYTIC_BYTES:
        raise ValueError("A8-R01 analytic byte count mismatch")
    if sha256_bytes(analytic_bytes) != R01_ANALYTIC_SHA256:
        raise ValueError("A8-R01 analytic storage digest mismatch")
    if member_digest != R01_EXPLICIT_SHA256 or member_length != (
        R01_EXPLICIT_BYTES
    ):
        raise ValueError("A8-R01 streaming member digest mismatch")
    if rebuilt_explicit_bytes != explicit_bytes:
        raise ValueError("A8-R01 inverse is not byte exact")
    if rebuilt_analytic_bytes != analytic_bytes:
        raise ValueError("A8-R01 forward transform is not byte exact")
    if serialize_relation(relation) != explicit:
        raise ValueError("A8-R01 production arm must be the explicit array")
    return {
        "vector_id": "A8-R01",
        "member_count": relation.member_count,
        "explicit_byte_count": len(explicit_bytes),
        "explicit_sha256": sha256_bytes(explicit_bytes),
        "analytic_byte_count": len(analytic_bytes),
        "analytic_storage_sha256": sha256_bytes(analytic_bytes),
        "member_domain_sha256": member_digest,
        "production_arm": "explicit",
        "status": "pass",
    }


def a8_r02(
    materialized_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Prove two independent derivations of one large member digest.

    ``materialized_rows`` is the caller's independently constructed complete
    array.  The streaming arm never sees it: it regenerates each row from the
    analytic description and holds no array, byte buffer, or digest state in
    common with the materialized arm.
    """

    relation = large_fixture_relation()
    analytic = analytic_object(relation)
    analytic_bytes = canonical_json_bytes(analytic)
    if len(analytic_bytes) != R02_ANALYTIC_BYTES:
        raise ValueError("A8-R02 analytic byte count mismatch")
    if sha256_bytes(analytic_bytes) != R02_ANALYTIC_SHA256:
        raise ValueError("A8-R02 analytic storage digest mismatch")
    if relation.member_count <= MEMBER_THRESHOLD:
        raise ValueError("A8-R02 must exceed the representation threshold")
    if serialize_relation(relation) != analytic:
        raise ValueError("A8-R02 production arm must be the analytic object")

    streamed_length, streamed_digest = member_domain_digest(relation)
    if streamed_length != R02_EXPLICIT_BYTES:
        raise ValueError("A8-R02 streamed byte count mismatch")
    if streamed_digest != R02_EXPLICIT_SHA256:
        raise ValueError("A8-R02 streamed member digest mismatch")

    result = {
        "vector_id": "A8-R02",
        "member_count": relation.member_count,
        "analytic_byte_count": len(analytic_bytes),
        "analytic_storage_sha256": sha256_bytes(analytic_bytes),
        "streamed_byte_count": streamed_length,
        "streamed_member_domain_sha256": streamed_digest,
        "production_arm": "analytic",
        "status": "pass",
    }
    if materialized_rows is not None:
        materialized = canonical_json_bytes(materialized_rows)
        if len(materialized) != R02_EXPLICIT_BYTES:
            raise ValueError("A8-R02 materialized byte count mismatch")
        if sha256_bytes(materialized) != R02_EXPLICIT_SHA256:
            raise ValueError("A8-R02 materialized member digest mismatch")
        result["materialized_byte_count"] = len(materialized)
        result["materialized_member_domain_sha256"] = sha256_bytes(
            materialized
        )
    return result


def a8_r03() -> dict[str, Any]:
    """Reject every lossy, ambiguous, or type-invalid encoding before hashing."""

    rejections = []
    for name, payload, byte_count, digest in R03_NEGATIVES:
        raw = canonical_json_bytes(payload)
        if len(raw) != byte_count:
            raise ValueError(f"A8-R03 payload byte count mismatch: {name}")
        if sha256_bytes(raw) != digest:
            raise ValueError(f"A8-R03 payload digest mismatch: {name}")
        try:
            validate_analytic_object(payload, _fixture_ranges())
        except ValueError as error:
            rejections.append(
                {
                    "negative_id": name,
                    "byte_count": byte_count,
                    "raw_storage_sha256": digest,
                    "rejection": str(error),
                }
            )
            continue
        raise ValueError(f"A8-R03 accepted an unlawful encoding: {name}")
    if len(rejections) != len(R03_NEGATIVES):
        raise ValueError("A8-R03 did not reject every negative")
    return {
        "vector_id": "A8-R03",
        "negative_count": len(rejections),
        "rejections": rejections,
        "status": "pass",
    }


@dataclass(frozen=True)
class StorageFacts:
    """Independently measured §22.4.5 population facts."""

    status_decomposition: tuple[tuple[str, int, int, int], ...]
    total_members: int
    explicit_members: int
    analytic_members: int
    analytic_renderable_members: int
    analytic_unrenderable_members: int
    analytic_renderable_containers: int
    analytic_unrenderable_containers: int
    arm_ambiguous_renderable_members: int


def a8_r04(facts: StorageFacts) -> dict[str, Any]:
    """Reproduce the exact storage contradiction from measured counts.

    R04 passes only by reproducing the census and arithmetic and refusing to
    emit the unlawful revision-9 artifact; no partial or truncated explicit
    array is a lawful substitute.
    """

    if facts.status_decomposition != R04_STATUS_DECOMPOSITION:
        raise ValueError("A8-R04 status decomposition mismatch")
    if sum(row[1] for row in facts.status_decomposition) != (
        R04_COMPLETE_FIELDS
    ):
        raise ValueError("A8-R04 complete field total mismatch")
    if sum(row[2] for row in facts.status_decomposition) != (
        R04_COMPLETE_RANGE_ENTRIES
    ):
        raise ValueError("A8-R04 complete range-entry total mismatch")
    if sum(row[3] for row in facts.status_decomposition) != (
        facts.total_members
    ):
        raise ValueError("A8-R04 status member subtotals do not cover")

    pins = (
        (facts.total_members, R04_TOTAL_MEMBERS),
        (facts.explicit_members, R04_EXPLICIT_MEMBERS),
        (facts.analytic_members, R04_ANALYTIC_MEMBERS),
        (
            facts.analytic_renderable_members,
            R04_ANALYTIC_RENDERABLE_MEMBERS,
        ),
        (
            facts.analytic_unrenderable_members,
            R04_ANALYTIC_UNRENDERABLE_MEMBERS,
        ),
        (
            facts.analytic_renderable_containers,
            R04_ANALYTIC_RENDERABLE_CONTAINERS,
        ),
        (
            facts.analytic_unrenderable_containers,
            R04_ANALYTIC_UNRENDERABLE_CONTAINERS,
        ),
        (
            facts.arm_ambiguous_renderable_members,
            R04_ARM_AMBIGUOUS_RENDERABLE_MEMBERS,
        ),
    )
    for measured, pinned in pins:
        if measured != pinned:
            raise ValueError(f"A8-R04 fact mismatch: {measured} != {pinned}")
    if facts.explicit_members + facts.analytic_members != (
        facts.total_members
    ):
        raise ValueError("A8-R04 threshold-partition identity fails")
    if (
        facts.analytic_renderable_members
        + (facts.analytic_unrenderable_members)
        != facts.analytic_members
    ):
        raise ValueError("A8-R04 analytic container population fails")
    containers = (
        facts.analytic_renderable_containers
        + facts.analytic_unrenderable_containers
    )
    if containers != R04_ANALYTIC_CONTAINERS:
        raise ValueError("A8-R04 analytic container count mismatch")

    empty_floor = 3 * facts.total_members + 2
    if empty_floor != R04_EMPTY_OBJECT_FLOOR_BYTES:
        raise ValueError("A8-R04 empty-object floor mismatch")
    row_floor = (
        facts.analytic_renderable_members * R04_RENDERABLE_ROW_FLOOR_BYTES
        + facts.analytic_unrenderable_members
        * R04_UNRENDERABLE_ROW_FLOOR_BYTES
    )
    if row_floor != R04_ROW_FLOOR_BYTES:
        raise ValueError("A8-R04 row floor mismatch")
    with localcontext() as context:
        # The exact binary-TiB expression terminates in 40 fractional
        # digits; a default 28-digit context would silently round it.
        context.prec = 80
        row_floor_tib = str(Decimal(row_floor) / Decimal(_TIB))
    if row_floor_tib != R04_ROW_FLOOR_TIB:
        raise ValueError("A8-R04 TiB expression mismatch")
    available = R04_AVAILABLE_TIB * _TIB
    if Fraction(empty_floor) <= available:
        raise ValueError("A8-R04 empty floor no longer exceeds capacity")
    multiple = Fraction(row_floor) / available
    if multiple <= 185:
        raise ValueError("A8-R04 row floor is not over 185x capacity")
    return {
        "vector_id": "A8-R04",
        "total_members": facts.total_members,
        "empty_object_floor_bytes": empty_floor,
        "row_floor_bytes": row_floor,
        "row_floor_tib": R04_ROW_FLOOR_TIB,
        "available_capacity_multiple": float(multiple),
        "emitted_artifact": None,
        "status": "pass",
    }


def a8_vector_relation_identity() -> dict[str, Any]:
    """Return the pinned four-row vector relation identity."""

    array = canonical_json_bytes(list(A8_VECTOR_ROWS))
    ids = canonical_json_bytes([row["vector_id"] for row in A8_VECTOR_ROWS])
    if len(array) != A8_VECTOR_ARRAY_BYTES:
        raise ValueError("A8 vector array byte count mismatch")
    if sha256_bytes(array) != A8_VECTOR_ARRAY_SHA256:
        raise ValueError("A8 vector array digest mismatch")
    if sha256_bytes(ids) != A8_VECTOR_ID_ARRAY_SHA256:
        raise ValueError("A8 vector ID array digest mismatch")
    return {
        "vector_array_byte_count": len(array),
        "vector_array_sha256": sha256_bytes(array),
        "vector_id_array_sha256": sha256_bytes(ids),
    }


def run_amendment_8_vectors(
    facts: StorageFacts,
    *,
    materialized_rows: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], ...]:
    """Run A8-R01 through A8-R04 in the one required order."""

    a8_vector_relation_identity()
    return (
        a8_r01(),
        a8_r02(materialized_rows),
        a8_r03(),
        a8_r04(facts),
    )


def empty_relation_digest() -> str:
    """Return the retained digest of the exact empty member array."""

    return canonical_stream_digest([])[1]
