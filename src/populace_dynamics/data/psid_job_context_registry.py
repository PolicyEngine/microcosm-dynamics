"""Byte-pinned raw extraction specs for modern PSID job context.

This reader-only registry is deliberately not a covered-earnings crosswalk.
It binds source field IDs, labels, and fixed-width coordinates for exact raw
byte slicing.  It does not claim questionnaire-slot completeness, typed code
maps, missing tokens, source dispositions, timing, remuneration types, or
production admissibility.

The expected physical domain is independently reconstructed from the
source-only dictionary audit with a closed parser for the documented BC/DE
questions.  Missing, extra, duplicated, ambiguous, or mistagged rows fail.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from populace_dynamics.data import psid_questionnaire_inventory

SCHEMA_VERSION = "psid_modern_job_context_raw_extraction_specs.v1"
ARTIFACT_ID = SCHEMA_VERSION
AUTHORITY_SCOPE = "physical_extraction_only"
DICTIONARY_AUDIT_PATH = (
    "data/external/"
    "psid_questionnaire_dictionary_inventory_"
    "registration_required_v1.json"
)
MODERN_INTERVIEW_WAVES: tuple[int, ...] = tuple(range(2003, 2024, 2))
SOURCE_BLOCK_ROLE_MAP = {
    "FAMILY": "shared",
    "BC": "head",
    "DE": "spouse",
}

ROW_COLUMNS: tuple[str, ...] = (
    "raw_extraction_key",
    "source_field_key",
    "interview_wave",
    "earnings_reference_year",
    "source_block",
    "reader_role",
    "reader_job_slot",
    "source_context_scope",
    "source_question_id",
    "reader_field_id",
    "field_ordinal",
    "raw_field_id",
    "exact_short_label",
    "layout_start_1indexed",
    "layout_end_1indexed",
    "raw_width",
    "source_document_ids",
)

FORBIDDEN_OFFICIAL_ROW_FIELDS = frozenset(
    {
        "source_inventory_key",
        "questionnaire_slot_id",
        "field_purpose",
        "source_disposition",
        "value_code_map",
        "typed_parse_specs",
        "missing_raw_tokens",
        "reference_periodicity",
        "information_date_basis",
        "inventory_year_disposition",
        "crosswalk_use",
        "remuneration_type",
        "year_source_class",
    }
)

_MONTH_ORDINALS = {
    month: ordinal
    for ordinal, month in enumerate(
        (
            "JAN",
            "FEB",
            "MAR",
            "APR",
            "MAY",
            "JUN",
            "JUL",
            "AUG",
            "SEP",
            "OCT",
            "NOV",
            "DEC",
        ),
        start=1,
    )
}
_ROLE_TOKEN_BLOCK = {
    "HD": "BC",
    "RP": "BC",
    "WF": "DE",
    "SP": "DE",
}
_RELEVANT_QUESTION_RE = re.compile(
    r"^(BC|DE)"
    r"(?:16-17|6|20|21|22|23|24|29|30|31|32A?|33|34A?|36|37|38|"
    r"39|41|43|44|45|46)"
    r"(?:\s|-)"
)
_ZERO_SHA256 = "0" * 64


class RawExtractionRegistryError(ValueError):
    """Raised when physical extraction evidence is incomplete or drifts."""


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _normalise_label(value: str) -> str:
    return " ".join(value.split())


def _role_for_block(block: str) -> str:
    return SOURCE_BLOCK_ROLE_MAP[block]


def _parsed(
    *,
    source_block: str,
    reader_job_slot: str | None,
    source_context_scope: str,
    source_question_id: str,
    reader_field_id: str,
    field_ordinal: int = 1,
) -> dict[str, Any]:
    return {
        "source_block": source_block,
        "reader_role": _role_for_block(source_block),
        "reader_job_slot": reader_job_slot,
        "source_context_scope": source_context_scope,
        "source_question_id": source_question_id,
        "reader_field_id": reader_field_id,
        "field_ordinal": field_ordinal,
    }


def _parse_shared_label(wave: int, label: str) -> dict[str, Any] | None:
    matches = {
        f"{wave} FAMILY INTERVIEW (ID) NUMBER": (
            "FAMILY_INTERVIEW_ID",
            "family_interview_id_raw",
        ),
        "PSID STATE OF RESIDENCE CODE": (
            "STATE_PSID",
            "state_of_residence_psid_raw",
        ),
        "CURRENT STATE": (
            "STATE_CURRENT",
            "state_of_residence_current_raw",
        ),
    }
    matched = matches.get(label)
    if matched is None:
        return None
    source_question_id, reader_field_id = matched
    return _parsed(
        source_block="FAMILY",
        reader_job_slot=None,
        source_context_scope="family_shared_interview_current",
        source_question_id=source_question_id,
        reader_field_id=reader_field_id,
    )


def _parse_accuracy_label(label: str) -> dict[str, Any] | None:
    match = re.fullmatch(
        r"(CALCULATED|ACCURACY OF) ELAPSED WEEKS--"
        r"(HD|RP|WF|SP) JOB ([1-4])",
        label,
    )
    if match is not None:
        field_kind, role_token, job_number = match.groups()
        block = _ROLE_TOKEN_BLOCK[role_token]
        reader_field_id = (
            "calculated_elapsed_weeks_raw"
            if field_kind == "CALCULATED"
            else "calculated_elapsed_weeks_accuracy_raw"
        )
        return _parsed(
            source_block=block,
            reader_job_slot=f"job_{job_number}",
            source_context_scope="explicit_job_label",
            source_question_id=f"{block}6-CALCULATED-ELAPSED",
            reader_field_id=reader_field_id,
        )
    match = re.fullmatch(
        r"ACCURACY OF HR/WK WORKED--(HD|RP|WF|SP) JOB ([1-4])",
        label,
    )
    if match is not None:
        role_token, job_number = match.groups()
        block = _ROLE_TOKEN_BLOCK[role_token]
        return _parsed(
            source_block=block,
            reader_job_slot=f"job_{job_number}",
            source_context_scope="explicit_job_label",
            source_question_id=f"{block}43-ACCURACY",
            reader_field_id="usual_hours_per_week_accuracy_raw",
        )
    match = re.fullmatch(
        r"ACCURACY OF OT--(HD|RP|WF|SP) JOB ([1-4])",
        label,
    )
    if match is None:
        return None
    role_token, job_number = match.groups()
    block = _ROLE_TOKEN_BLOCK[role_token]
    return _parsed(
        source_block=block,
        reader_job_slot=f"job_{job_number}",
        source_context_scope="explicit_job_label",
        source_question_id=f"{block}45-ACCURACY",
        reader_field_id="overtime_accuracy_raw",
    )


def _parse_explicit_job_label(label: str) -> dict[str, Any] | None:
    match = re.fullmatch(
        r"(BC|DE)6 (BEGINNING|ENDING) (MONTH|YEAR)--JOB ([1-4])",
        label,
    )
    if match is not None:
        block, boundary, coordinate, job_number = match.groups()
        reader_field_id = f"job_{boundary.lower()}_{coordinate.lower()}_raw"
        return _parsed(
            source_block=block,
            reader_job_slot=f"job_{job_number}",
            source_context_scope="explicit_job_label",
            source_question_id=f"{block}6",
            reader_field_id=reader_field_id,
        )

    match = re.fullmatch(
        r"(BC|DE)6 WTR EMPLOYED--JOB ([1-4]) "
        r"(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)",
        label,
    )
    if match is not None:
        block, job_number, month = match.groups()
        return _parsed(
            source_block=block,
            reader_job_slot=f"job_{job_number}",
            source_context_scope="explicit_job_label",
            source_question_id=f"{block}6",
            reader_field_id="employed_in_month_raw",
            field_ordinal=_MONTH_ORDINALS[month],
        )

    rules = (
        (
            r"(BC|DE)20 MAIN OCC FOR JOB ([1-4]): .+",
            "20",
            "occupation_raw",
        ),
        (
            r"(BC|DE)21 MAIN IND FOR JOB ([1-4]): .+",
            "21",
            "industry_raw",
        ),
        (
            r"(BC|DE)22 WORK SELF/OTR\?--JOB ([1-4])",
            "22",
            "employee_self_or_other_raw",
        ),
        (
            r"(BC|DE)23 CORP/UNCORP BUS--JOB ([1-4])",
            "23",
            "incorporation_raw",
        ),
        (
            r"(BC|DE)24 WORK FOR GOVT\?--JOB ([1-4])",
            "24",
            "government_employer_raw",
        ),
        (
            r"(BC|DE)43 HOURS/WEEK WORKED--JOB ([1-4])",
            "43",
            "usual_hours_per_week_raw",
        ),
        (
            r"(BC|DE)44 WTR WORKED OT--JOB ([1-4])",
            "44",
            "overtime_worked_raw",
        ),
        (
            r"(BC|DE)45 AMT OF OT WORKED--JOB ([1-4])",
            "45",
            "overtime_amount_raw",
        ),
        (
            r"(BC|DE)45 OT TIME UNIT--JOB ([1-4])",
            "45",
            "overtime_reporting_unit_raw",
        ),
        (
            r"(BC|DE)46 AMOUNT EARNED LAST YEAR--JOB ([1-4])",
            "46",
            "prior_year_job_earnings_amount_raw",
        ),
        (
            r"(BC|DE)46 PER FOR AMT EARNED LAST YR--JOB ([1-4])",
            "46",
            "prior_year_job_earnings_reporting_unit_raw",
        ),
    )
    for pattern, question_number, reader_field_id in rules:
        match = re.fullmatch(pattern, label)
        if match is None:
            continue
        block, job_number = match.groups()
        return _parsed(
            source_block=block,
            reader_job_slot=f"job_{job_number}",
            source_context_scope="explicit_job_label",
            source_question_id=f"{block}{question_number}",
            reader_field_id=reader_field_id,
        )
    return None


def _parse_role_block_label(label: str) -> dict[str, Any] | None:
    match = re.fullmatch(r"(BC|DE)16-17 MAIN JOB INDICATOR", label)
    if match is not None:
        block = match.group(1)
        return _parsed(
            source_block=block,
            reader_job_slot=None,
            source_context_scope="role_block_unadjudicated",
            source_question_id=f"{block}16-17",
            reader_field_id="main_job_indicator_raw",
        )

    simple_rules = (
        (r"(BC|DE)29 SLRY/HRLY/OTR .+", "29", "pay_basis_raw"),
        (r"(BC|DE)30 SALARY AMOUNT", "30", "salary_amount_raw"),
        (
            r"(BC|DE)30 SALARY PER WHAT",
            "30",
            "salary_reporting_unit_raw",
        ),
        (
            r"(BC|DE)31 WTR SAL PD OT .+",
            "31",
            "salaried_overtime_paid_raw",
        ),
        (r"(BC|DE)32 HOW PAID FOR OT", "32", "overtime_pay_basis_raw"),
        (
            r"(BC|DE)32A EXACT OT PAY IF SALARIED",
            "32A",
            "salaried_overtime_amount_raw",
        ),
        (
            r"(BC|DE)32A EXACT OT PAY PER",
            "32A",
            "salaried_overtime_reporting_unit_raw",
        ),
        (r"(BC|DE)33 HOURLY REGULAR RATE", "33", "hourly_rate_raw"),
        (
            r"(BC|DE)34A EXACT OT PAY IF HOURLY",
            "34A",
            "hourly_overtime_amount_raw",
        ),
        (
            r"(BC|DE)34A EXACT OT PAY PER",
            "34A",
            "hourly_overtime_reporting_unit_raw",
        ),
        (
            r"(BC|DE)36 AVG TIPS/COMM",
            "36",
            "tips_commission_first_amount_raw",
        ),
        (
            r"(BC|DE)36 TIPS/COMM PER WHAT",
            "36",
            "tips_commission_first_reporting_unit_raw",
        ),
        (
            r"(BC|DE)37 AVG TIPS/COMM",
            "37",
            "tips_commission_second_amount_raw",
        ),
        (
            r"(BC|DE)37 TIPS/COMM PER WHAT",
            "37",
            "tips_commission_second_reporting_unit_raw",
        ),
        (r"(BC|DE)38 HOW PAID-OTR .+", "38", "other_pay_basis_raw"),
        (r"(BC|DE)39 OT RATE", "39", "other_pay_rate_raw"),
    )
    for pattern, question_number, reader_field_id in simple_rules:
        match = re.fullmatch(pattern, label)
        if match is None:
            continue
        block = match.group(1)
        return _parsed(
            source_block=block,
            reader_job_slot=None,
            source_context_scope="role_block_unadjudicated",
            source_question_id=f"{block}{question_number}",
            reader_field_id=reader_field_id,
        )

    match = re.fullmatch(
        r"(BC|DE)34 OT DIFFERENTIAL (1ST|2ND|3RD)",
        label,
    )
    if match is not None:
        block, ordinal_label = match.groups()
        ordinal = {"1ST": 1, "2ND": 2, "3RD": 3}[ordinal_label]
        return _parsed(
            source_block=block,
            reader_job_slot=None,
            source_context_scope="role_block_unadjudicated",
            source_question_id=f"{block}34",
            reader_field_id="overtime_differential_raw",
            field_ordinal=ordinal,
        )

    match = re.fullmatch(r"(BC|DE)41 (YRS|MOS|WKS) PRES EMP .+", label)
    if match is None:
        return None
    block, unit = match.groups()
    unit_name = {"YRS": "years", "MOS": "months", "WKS": "weeks"}[unit]
    return _parsed(
        source_block=block,
        reader_job_slot=None,
        source_context_scope="role_block_unadjudicated",
        source_question_id=f"{block}41",
        reader_field_id=f"present_employer_tenure_{unit_name}_raw",
    )


def parse_source_label(wave: int, exact_label: str) -> dict[str, Any] | None:
    """Parse one exact short label into a reader-only coordinate."""

    label = _normalise_label(exact_label)
    parsers = (
        lambda value: _parse_shared_label(wave, value),
        _parse_accuracy_label,
        _parse_explicit_job_label,
        _parse_role_block_label,
    )
    matches = [
        parsed for parser in parsers if (parsed := parser(label)) is not None
    ]
    if len(matches) > 1:
        raise RawExtractionRegistryError(
            f"ambiguous extraction label in wave {wave}: {label!r}"
        )
    return matches[0] if matches else None


def _is_relevant_candidate(wave: int, exact_label: str) -> bool:
    label = _normalise_label(exact_label)
    if _parse_shared_label(wave, label) is not None:
        return True
    if label.startswith("ACCURACY OF HR/WK WORKED--"):
        return True
    if label.startswith("ACCURACY OF OT--"):
        return True
    if label.startswith("CALCULATED ELAPSED WEEKS--"):
        return True
    if label.startswith("ACCURACY OF ELAPSED WEEKS--"):
        return True
    return _RELEVANT_QUESTION_RE.match(label) is not None


def _role_block_expected(block: str) -> list[dict[str, Any]]:
    specs = [
        ("16-17", "main_job_indicator_raw", 1),
        ("29", "pay_basis_raw", 1),
        ("30", "salary_amount_raw", 1),
        ("30", "salary_reporting_unit_raw", 1),
        ("31", "salaried_overtime_paid_raw", 1),
        ("32", "overtime_pay_basis_raw", 1),
        ("32A", "salaried_overtime_amount_raw", 1),
        ("32A", "salaried_overtime_reporting_unit_raw", 1),
        ("33", "hourly_rate_raw", 1),
        ("34", "overtime_differential_raw", 1),
        ("34", "overtime_differential_raw", 2),
        ("34", "overtime_differential_raw", 3),
        ("34A", "hourly_overtime_amount_raw", 1),
        ("34A", "hourly_overtime_reporting_unit_raw", 1),
        ("36", "tips_commission_first_amount_raw", 1),
        ("36", "tips_commission_first_reporting_unit_raw", 1),
        ("37", "tips_commission_second_amount_raw", 1),
        ("37", "tips_commission_second_reporting_unit_raw", 1),
        ("38", "other_pay_basis_raw", 1),
        ("39", "other_pay_rate_raw", 1),
        ("41", "present_employer_tenure_years_raw", 1),
        ("41", "present_employer_tenure_months_raw", 1),
        ("41", "present_employer_tenure_weeks_raw", 1),
    ]
    return [
        _parsed(
            source_block=block,
            reader_job_slot=None,
            source_context_scope="role_block_unadjudicated",
            source_question_id=f"{block}{question}",
            reader_field_id=reader_field,
            field_ordinal=ordinal,
        )
        for question, reader_field, ordinal in specs
    ]


def _explicit_job_expected(
    block: str,
    job_number: int,
    *,
    include_calculated_elapsed: bool,
) -> list[dict]:
    slot = f"job_{job_number}"
    result = [
        _parsed(
            source_block=block,
            reader_job_slot=slot,
            source_context_scope="explicit_job_label",
            source_question_id=f"{block}6",
            reader_field_id=reader_field,
        )
        for reader_field in (
            "job_beginning_month_raw",
            "job_beginning_year_raw",
            "job_ending_month_raw",
            "job_ending_year_raw",
        )
    ]
    result.extend(
        _parsed(
            source_block=block,
            reader_job_slot=slot,
            source_context_scope="explicit_job_label",
            source_question_id=f"{block}6",
            reader_field_id="employed_in_month_raw",
            field_ordinal=month_ordinal,
        )
        for month_ordinal in range(1, 13)
    )
    for question, reader_field in (
        ("20", "occupation_raw"),
        ("21", "industry_raw"),
        ("22", "employee_self_or_other_raw"),
        ("23", "incorporation_raw"),
        ("24", "government_employer_raw"),
        ("43", "usual_hours_per_week_raw"),
        ("43-ACCURACY", "usual_hours_per_week_accuracy_raw"),
        ("44", "overtime_worked_raw"),
        ("45", "overtime_amount_raw"),
        ("45", "overtime_reporting_unit_raw"),
        ("45-ACCURACY", "overtime_accuracy_raw"),
        ("46", "prior_year_job_earnings_amount_raw"),
        ("46", "prior_year_job_earnings_reporting_unit_raw"),
    ):
        result.append(
            _parsed(
                source_block=block,
                reader_job_slot=slot,
                source_context_scope="explicit_job_label",
                source_question_id=f"{block}{question}",
                reader_field_id=reader_field,
            )
        )
    if include_calculated_elapsed:
        for reader_field in (
            "calculated_elapsed_weeks_raw",
            "calculated_elapsed_weeks_accuracy_raw",
        ):
            result.append(
                _parsed(
                    source_block=block,
                    reader_job_slot=slot,
                    source_context_scope="explicit_job_label",
                    source_question_id=f"{block}6-CALCULATED-ELAPSED",
                    reader_field_id=reader_field,
                )
            )
    return result


def expected_reader_coordinates() -> tuple[tuple[Any, ...], ...]:
    """Return the declared physical-reader subset, never the slot universe."""

    rows: list[dict[str, Any]] = []
    for wave in MODERN_INTERVIEW_WAVES:
        for question, reader_field in (
            ("FAMILY_INTERVIEW_ID", "family_interview_id_raw"),
            ("STATE_PSID", "state_of_residence_psid_raw"),
            ("STATE_CURRENT", "state_of_residence_current_raw"),
        ):
            rows.append(
                _parsed(
                    source_block="FAMILY",
                    reader_job_slot=None,
                    source_context_scope="family_shared_interview_current",
                    source_question_id=question,
                    reader_field_id=reader_field,
                )
                | {"interview_wave": wave}
            )
        for block in ("BC", "DE"):
            rows.extend(
                row | {"interview_wave": wave}
                for row in _role_block_expected(block)
            )
            for job_number in range(1, 5):
                rows.extend(
                    row | {"interview_wave": wave}
                    for row in _explicit_job_expected(
                        block,
                        job_number,
                        include_calculated_elapsed=wave in (2003, 2005),
                    )
                )
    return tuple(_coordinate(row) for row in rows)


def _coordinate(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        row["interview_wave"],
        row["source_block"],
        row["reader_role"],
        row["reader_job_slot"],
        row["source_context_scope"],
        row["source_question_id"],
        row["reader_field_id"],
        row["field_ordinal"],
    )


def _extraction_key(
    source_field_key: str,
    coordinate: tuple[Any, ...],
) -> str:
    digest = _sha256(canonical_json_bytes([source_field_key, *coordinate]))
    return f"psid-raw-job-context:{digest}"


def _audit_field_dicts(
    dictionary_audit: Mapping[str, Any],
) -> Iterable[dict[str, Any]]:
    columns = dictionary_audit["physical_field_columns"]
    for row in dictionary_audit["physical_fields"]:
        yield dict(zip(columns, row, strict=True))


def _derive_rows(
    dictionary_audit: Mapping[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for field in _audit_field_dicts(dictionary_audit):
        wave = field["interview_wave"]
        if wave not in MODERN_INTERVIEW_WAVES:
            continue
        relevant = _is_relevant_candidate(wave, field["exact_short_label"])
        parsed = parse_source_label(wave, field["exact_short_label"])
        if relevant and parsed is None:
            raise RawExtractionRegistryError(
                "relevant source field does not match exactly one closed "
                f"reader rule: wave={wave}, raw_field_id="
                f"{field['raw_field_id']}, label="
                f"{field['exact_short_label']!r}"
            )
        if parsed is None:
            continue
        coordinate_source = parsed | {"interview_wave": wave}
        coordinate = _coordinate(coordinate_source)
        rows.append(
            {
                "raw_extraction_key": _extraction_key(
                    field["source_field_key"],
                    coordinate,
                ),
                "source_field_key": field["source_field_key"],
                "interview_wave": wave,
                "earnings_reference_year": wave - 1,
                **parsed,
                "raw_field_id": field["raw_field_id"],
                "exact_short_label": field["exact_short_label"],
                "layout_start_1indexed": field["start"],
                "layout_end_1indexed": field["end"],
                "raw_width": field["raw_width"],
                "source_document_ids": field["source_document_ids"],
            }
        )

    expected_coordinates = expected_reader_coordinates()
    actual_coordinates = tuple(_coordinate(row) for row in rows)
    if len(actual_coordinates) != len(set(actual_coordinates)):
        raise RawExtractionRegistryError(
            "duplicate modern reader coordinate derived from source labels"
        )
    expected_set = set(expected_coordinates)
    actual_set = set(actual_coordinates)
    if (
        len(actual_coordinates) != len(expected_coordinates)
        or actual_set != expected_set
    ):
        missing = sorted(expected_set - actual_set, key=repr)
        extra = sorted(actual_set - expected_set, key=repr)
        raise RawExtractionRegistryError(
            "modern reader domain mismatch; "
            f"missing={missing[:3]}, extra={extra[:3]}, "
            f"expected_count={len(expected_coordinates)}, "
            f"actual_count={len(actual_coordinates)}"
        )
    return rows


def _keyset_hash(keys: Iterable[str]) -> str:
    return _sha256(canonical_json_bytes(list(keys)))


def build_raw_extraction_registry(
    dictionary_audit: Mapping[str, Any],
    *,
    dictionary_audit_file_sha256: str,
) -> dict[str, Any]:
    """Build the physical-only reader registry from the independent audit."""

    psid_questionnaire_inventory.validate_integrity(dict(dictionary_audit))
    rows = _derive_rows(dictionary_audit)
    reader_field_ids = list(
        dict.fromkeys(row["reader_field_id"] for row in rows)
    )
    artifact: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_id": ARTIFACT_ID,
        "authority_scope": AUTHORITY_SCOPE,
        "dictionary_audit_identity": {
            "path": DICTIONARY_AUDIT_PATH,
            "schema_version": dictionary_audit["schema_version"],
            "artifact_id": dictionary_audit["artifact_id"],
            "file_sha256": dictionary_audit_file_sha256,
            "content_sha256": dictionary_audit["integrity"]["content_sha256"],
            "physical_field_count": dictionary_audit["physical_field_count"],
            "physical_field_keyset_sha256": dictionary_audit[
                "physical_field_keyset_sha256"
            ],
        },
        "interview_waves": list(MODERN_INTERVIEW_WAVES),
        "source_block_role_map": SOURCE_BLOCK_ROLE_MAP,
        "reader_field_ids": reader_field_ids,
        "rows": rows,
        "row_count": len(rows),
        "row_keyset_sha256": _keyset_hash(
            row["raw_extraction_key"] for row in rows
        ),
        "canonical_order": [
            "interview_wave",
            "physical_layout_coordinate",
        ],
        "official_artifact_status": {
            "psid_questionnaire_slot_specs.v1": (
                "not_emitted_registration_required"
            ),
            "psid_covered_earnings_source_field_inventory.v1": (
                "not_emitted_registration_required"
            ),
            "psid_covered_earnings_crosswalk.v2": (
                "not_emitted_upstream_registration_required"
            ),
            "g17_inventory_crosswalk_evidence.v1": (
                "not_emitted_upstream_registration_required"
            ),
            "registration_required_item_ids": ["V-B5", "V-B6", "V-B8"],
        },
        "integrity": {
            "canonicalization": (
                "UTF-8 JSON; keys sorted; no insignificant whitespace; "
                "content_sha256 computed with itself set to 64 zeroes"
            ),
            "content_sha256": _ZERO_SHA256,
            "builder_source_sha256": _sha256(Path(__file__).read_bytes()),
            "reproduced_from_dictionary_audit_bytes": True,
        },
    }
    artifact["integrity"]["content_sha256"] = _sha256(
        canonical_json_bytes(artifact)
    )
    return artifact


def validate_raw_extraction_registry(
    registry: Mapping[str, Any],
    dictionary_audit: Mapping[str, Any],
    *,
    dictionary_audit_file_sha256: str,
) -> None:
    """Run physical-scope G17-style independent-domain checks."""

    expected = build_raw_extraction_registry(
        dictionary_audit,
        dictionary_audit_file_sha256=dictionary_audit_file_sha256,
    )
    required_top_keys = set(expected)
    if set(registry) != required_top_keys:
        raise RawExtractionRegistryError(
            "raw extraction registry top-level schema drifted"
        )
    rows = registry["rows"]
    if registry["row_count"] != len(rows):
        raise RawExtractionRegistryError("raw extraction row count mismatch")
    keys = [row["raw_extraction_key"] for row in rows]
    if len(keys) != len(set(keys)):
        raise RawExtractionRegistryError("duplicate raw extraction key")
    if registry["row_keyset_sha256"] != _keyset_hash(keys):
        raise RawExtractionRegistryError("raw extraction keyset hash mismatch")
    for row in rows:
        if set(row) != set(ROW_COLUMNS):
            raise RawExtractionRegistryError(
                "raw extraction row schema drifted"
            )
        forbidden = set(row).intersection(FORBIDDEN_OFFICIAL_ROW_FIELDS)
        if forbidden:
            raise RawExtractionRegistryError(
                f"reader row claims forbidden official semantics: "
                f"{sorted(forbidden)}"
            )
        if row["earnings_reference_year"] != row["interview_wave"] - 1:
            raise RawExtractionRegistryError("wave/reference mismatch")
        if (
            row["raw_width"]
            != row["layout_end_1indexed"] - row["layout_start_1indexed"] + 1
        ):
            raise RawExtractionRegistryError("raw width/coordinate mismatch")
    if dict(registry) != expected:
        raise RawExtractionRegistryError(
            "raw extraction rows or authority projection differ from the "
            "independently reconstructed physical domain"
        )


def render_registry(
    registry: Mapping[str, Any],
    dictionary_audit: Mapping[str, Any],
    *,
    dictionary_audit_file_sha256: str,
) -> bytes:
    validate_raw_extraction_registry(
        registry,
        dictionary_audit,
        dictionary_audit_file_sha256=dictionary_audit_file_sha256,
    )
    return canonical_json_bytes(dict(registry)) + b"\n"
