"""Revision-9 pre-Q5 A7-R10a and A7-R11 regression vectors."""

from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import zlib
from pathlib import Path
from typing import Any

import pytest

from populace_dynamics.data.psid_source_guard import (
    CLOSED_FAILURE_REFERENCE_ROW_KEYS,
    ClosedFailureReferenceError,
    ConsumerKind,
    canonical_json_bytes,
    guard_physical_consumption,
    numeric_grammar_derivation_sha256,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DESIGN_PATH = REPO_ROOT / "docs/design/covered_earnings_correction.md"
PSID_ROOT = Path("~/PolicyEngine/psid-data").expanduser()
MANDATED_PYTHON = Path(
    "~/PolicyEngine/social-security-model/.venv/bin/python"
).expanduser()

DESIGN_BYTES = 2_423_590
DESIGN_SHA256 = (
    "2064f47b181ec21ec9b786b9a17a7a489e3b4732751edf794d6bd545bd9546b9"
)

A7_R11_ANCHOR = (
    b"The exact executable route-probe preimage is the zlib-compressed "
    b"RFC 4648\nBase64 payload below."
)
A7_R11_ENCODED_BYTES = 11_513
A7_R11_ENCODED_SHA256 = (
    "ddd5a010aa12f79e8f217f77adaa0a155fd66275e1d1204abdbe11050ea0c3fe"
)
A7_R11_COMPRESSED_BYTES = 8_632
A7_R11_COMPRESSED_SHA256 = (
    "99cd07791a36a6c7a30fd1151674821166cf495c528babd7959a170408f99615"
)
A7_R11_SOURCE_BYTES = 36_601
A7_R11_SOURCE_SHA256 = (
    "3287c293b3e7f954f044fdc70176f169dbae9416232fbf1f1f72284c1bda9e4f"
)
A7_R11_FIXTURE_BYTES = 92_919
A7_R11_FIXTURE_SHA256 = (
    "ac6cbc4a270f4dea44a29aa2721cdf7902d02ed5239f60f1116ed76e569414c8"
)

A7_R10A_GRAPH_ANCHOR = (
    b"The following terminal-LF Python source is the sole canonical "
    b"preimage for\nthe graph topology and ordered basis fixture."
)
A7_R10A_GRAPH_BYTES = 93_657
A7_R10A_GRAPH_SHA256 = (
    "3ff2f3191b8b23ae5f1b70346b889a9853720dd8677f528ab9d3314ab12f42c7"
)
A7_R10A_MARKER_ANCHOR = b"A7-R10a has vector_kind"
A7_R10A_MARKER_BYTES = 154
A7_R10A_MARKER_SHA256 = (
    "9a80d56587beb49afeafa3b897ba5e4351fc59f1c4cb870f28cb4e0e99be4429"
)
A7_R10A_MARKER = {
    "carrier_stage": "carrier_deferred",
    "next_stage": "A7-R10b_expected_absence_gate",
    "source_adjudication_status": ("nonpassing_forbidden_physical_dependency"),
}

A7_R11_CONSUMER_ID = "amendment_7_a7_r11_physical_consumer_fixture.v1"
A7_R11_SOURCE_CONSUMER_ID = (
    "amendment_4_v_b6_documented_inclusive_total_evidence_projection.v1"
)
A7_R11_FAILURE_REASON = "literal_only_zero_diagnostic_padding_capacity"
A7_R11_FAILURE_STATUS = "incomplete_source_numeric_authority"
A7_R11_FIELD_KEYS = (
    (1976, "V4519"),
    (1976, "V4902"),
    (1977, "V5429"),
    (1978, "V5916"),
)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _fenced_payload_after(
    document: bytes,
    anchor: bytes,
    fence_kind: bytes,
) -> bytes:
    assert document.count(anchor) == 1
    anchor_position = document.index(anchor)
    opening = b"~~~" + fence_kind + b"\n"
    start = document.index(opening, anchor_position + len(anchor)) + len(
        opening
    )
    closing_lf = document.index(b"\n~~~\n", start)
    return document[start : closing_lf + 1]


@pytest.fixture(scope="session")
def revision_9_design() -> bytes:
    payload = DESIGN_PATH.read_bytes()
    assert len(payload) == DESIGN_BYTES
    assert _sha256(payload) == DESIGN_SHA256
    return payload


@pytest.fixture(scope="session")
def a7_r11_source(revision_9_design: bytes) -> bytes:
    wrapped = _fenced_payload_after(
        revision_9_design,
        A7_R11_ANCHOR,
        b"text",
    )
    lines = wrapped.splitlines(keepends=True)
    assert len(wrapped) == 11_628
    assert len(lines) == 116
    assert all(line.endswith(b"\n") for line in lines)
    assert [len(line) - 1 for line in lines] == [100] * 115 + [12]

    encoded = b"".join(line[:-1] for line in lines)
    encoded_with_lf = encoded + b"\n"
    assert len(encoded_with_lf) == A7_R11_ENCODED_BYTES
    assert _sha256(encoded_with_lf) == A7_R11_ENCODED_SHA256

    compressed = base64.b64decode(encoded, validate=True)
    assert len(compressed) == A7_R11_COMPRESSED_BYTES
    assert _sha256(compressed) == A7_R11_COMPRESSED_SHA256

    source = zlib.decompress(compressed)
    assert len(source) == A7_R11_SOURCE_BYTES
    assert _sha256(source) == A7_R11_SOURCE_SHA256
    assert source.endswith(b"\n")
    return source


@pytest.fixture(scope="session")
def a7_r11_fixture_rows(a7_r11_source: bytes) -> tuple[dict[str, Any], ...]:
    assert MANDATED_PYTHON.is_file()
    assert (PSID_ROOT / "family/1976/FAM1976.txt").is_file()
    assert (PSID_ROOT / "family/1977/FAM1977.txt").is_file()
    assert (PSID_ROOT / "family/1978/FAM1978.txt").is_file()

    completed = subprocess.run(
        [str(MANDATED_PYTHON), "-", "--fixture"],
        input=a7_r11_source,
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
        timeout=120,
    )
    assert completed.returncode == 0, completed.stderr.decode(
        "utf-8", errors="replace"
    )
    assert completed.stderr == b""
    assert len(completed.stdout) == A7_R11_FIXTURE_BYTES
    assert _sha256(completed.stdout) == A7_R11_FIXTURE_SHA256
    assert completed.stdout.endswith(b"\n")

    rows = json.loads(completed.stdout)
    assert canonical_json_bytes(rows) == completed.stdout
    assert [row["case_number"] for row in rows] == list(range(32))
    return tuple(rows)


def _mapped_failure_row(diagnostic: dict[str, Any]) -> dict[str, Any]:
    wave = diagnostic["interview_wave"]
    raw_field_id = diagnostic["raw_field_id"]
    return {
        "numeric_grammar_derivation_id": (
            f"psid-numeric-grammar-derivation:{wave}:{raw_field_id}"
        ),
        "interview_wave": wave,
        "raw_field_id": raw_field_id,
        "dictionary_field_row_ids": [],
        "dictionary_field_rows_sha256": "0" * 64,
        "codebook_field_row_ids": [],
        "codebook_field_rows_sha256": "0" * 64,
        "source_format_projection": [],
        "source_meaning_projection": [],
        "dictionary_field_meaning": None,
        "derived_parse_kind": "closed_failure",
        "normalized_format_profile": None,
        "nonmissing_observation_count": 0,
        "derivation_status": diagnostic["derivation_status"],
        "padding_rule": None,
        "registered_numeric_grammar": None,
    }


@pytest.fixture(scope="session")
def a7_r11_failure_relation(
    a7_r11_fixture_rows: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    rows_by_key: dict[tuple[int, str], dict[str, Any]] = {}
    reasons: dict[tuple[int, str], str] = {}
    for case_number, fixture_row in enumerate(a7_r11_fixture_rows):
        diagnostic = fixture_row["discovered_diagnostic"]
        field_position = case_number // 8
        key = (diagnostic["interview_wave"], diagnostic["raw_field_id"])

        assert fixture_row["case_number"] == case_number
        assert diagnostic["field_reference_position"] == field_position
        assert key == A7_R11_FIELD_KEYS[field_position]
        assert (
            diagnostic["dependency_graph_node_position"] == 109 + case_number
        )
        assert diagnostic["physical_dependency_position"][0] == case_number
        assert diagnostic["source_adjudication_consumer_id"] == (
            A7_R11_SOURCE_CONSUMER_ID
        )
        assert diagnostic["derivation_status"] == A7_R11_FAILURE_STATUS
        assert diagnostic["resolution_reason"] == A7_R11_FAILURE_REASON

        if key not in rows_by_key:
            rows_by_key[key] = _mapped_failure_row(diagnostic)
            reasons[key] = diagnostic["resolution_reason"]
        else:
            assert (
                rows_by_key[key]["derivation_status"]
                == diagnostic["derivation_status"]
            )
            assert reasons[key] == diagnostic["resolution_reason"]

    assert tuple(rows_by_key) == A7_R11_FIELD_KEYS
    assert set(reasons.values()) == {A7_R11_FAILURE_REASON}
    return {
        "rows": tuple(rows_by_key.values()),
        "rows_by_key": rows_by_key,
        "reasons": reasons,
    }


def _expected_guard_row(
    *,
    case_number: int,
    consumer_reference_position: int,
    key: tuple[int, str],
    relation: dict[str, Any],
) -> dict[str, Any]:
    derivation_row = relation["rows_by_key"][key]
    expected = {
        "consumer_kind": ConsumerKind.CROSSWALK.value,
        "consumer_row_identity": [A7_R11_CONSUMER_ID, case_number],
        "consumer_reference_position": consumer_reference_position,
        "interview_wave": key[0],
        "raw_field_id": key[1],
        "numeric_grammar_derivation_id": derivation_row[
            "numeric_grammar_derivation_id"
        ],
        "numeric_grammar_derivation_sha256": (
            numeric_grammar_derivation_sha256(derivation_row)
        ),
        "derivation_status": A7_R11_FAILURE_STATUS,
        "resolution_reason": A7_R11_FAILURE_REASON,
    }
    assert tuple(expected) == CLOSED_FAILURE_REFERENCE_ROW_KEYS
    return expected


@pytest.mark.parametrize(
    "case_number",
    range(32),
    ids=lambda case_number: f"case-{case_number:02d}",
)
def test_a7_r11_each_physical_route_aborts_before_resolver(
    case_number: int,
    a7_r11_fixture_rows: tuple[dict[str, Any], ...],
    a7_r11_failure_relation: dict[str, Any],
) -> None:
    source_diagnostic = a7_r11_fixture_rows[case_number][
        "discovered_diagnostic"
    ]
    key = (
        source_diagnostic["interview_wave"],
        source_diagnostic["raw_field_id"],
    )
    resolver_calls: list[Any] = []

    with pytest.raises(ClosedFailureReferenceError) as caught:
        guard_physical_consumption(
            consumer_kind=ConsumerKind.CROSSWALK,
            consumer_row_identity=[A7_R11_CONSUMER_ID, case_number],
            references=[key],
            derivation_rows=a7_r11_failure_relation["rows"],
            resolution_reason_by_field_key=a7_r11_failure_relation["reasons"],
            consume=lambda resolved: resolver_calls.append(resolved),
        )

    expected = _expected_guard_row(
        case_number=case_number,
        consumer_reference_position=0,
        key=key,
        relation=a7_r11_failure_relation,
    )
    assert resolver_calls == []
    assert caught.value.closed_failure_reference_rows == (expected,)
    assert caught.value.diagnostic_bytes == canonical_json_bytes([expected])
    assert (
        expected["derivation_status"] == source_diagnostic["derivation_status"]
    )
    assert (
        expected["resolution_reason"] == source_diagnostic["resolution_reason"]
    )


def test_a7_r11_aggregate_four_field_route_aborts_atomically(
    a7_r11_fixture_rows: tuple[dict[str, Any], ...],
    a7_r11_failure_relation: dict[str, Any],
) -> None:
    aggregate_cases = (0, 8, 16, 24)
    references = [
        (
            a7_r11_fixture_rows[case]["discovered_diagnostic"][
                "interview_wave"
            ],
            a7_r11_fixture_rows[case]["discovered_diagnostic"]["raw_field_id"],
        )
        for case in aggregate_cases
    ]
    route_invocation_counts = [0, 0, 0, 0]

    def resolve_routes(resolved: Any) -> None:
        assert len(resolved) == 4
        for position in range(4):
            route_invocation_counts[position] += 1

    with pytest.raises(ClosedFailureReferenceError) as caught:
        guard_physical_consumption(
            consumer_kind=ConsumerKind.CROSSWALK,
            consumer_row_identity=[A7_R11_CONSUMER_ID, 32],
            references=references,
            derivation_rows=a7_r11_failure_relation["rows"],
            resolution_reason_by_field_key=a7_r11_failure_relation["reasons"],
            consume=resolve_routes,
        )

    expected = tuple(
        _expected_guard_row(
            case_number=32,
            consumer_reference_position=position,
            key=key,
            relation=a7_r11_failure_relation,
        )
        for position, key in enumerate(references)
    )
    assert route_invocation_counts == [0, 0, 0, 0]
    assert caught.value.closed_failure_reference_rows == expected
    assert caught.value.diagnostic_bytes == canonical_json_bytes(
        list(expected)
    )
    assert [row["consumer_reference_position"] for row in expected] == [
        0,
        1,
        2,
        3,
    ]


def test_a7_r10a_graph_preimage_and_deferred_marker_are_exact(
    revision_9_design: bytes,
) -> None:
    graph_source = _fenced_payload_after(
        revision_9_design,
        A7_R10A_GRAPH_ANCHOR,
        b"python",
    )
    assert len(graph_source) == A7_R10A_GRAPH_BYTES
    assert _sha256(graph_source) == A7_R10A_GRAPH_SHA256
    assert graph_source.endswith(b"\n")
    assert b"assert len(node_rows) == 3365" in graph_source
    assert b"assert len(edge_rows) == 6351" in graph_source
    assert b"assert len(basis_rows) == 810" in graph_source

    marker = _fenced_payload_after(
        revision_9_design,
        A7_R10A_MARKER_ANCHOR,
        b"json",
    )
    assert len(marker) == A7_R10A_MARKER_BYTES
    assert _sha256(marker) == A7_R10A_MARKER_SHA256
    assert marker == canonical_json_bytes(A7_R10A_MARKER)
