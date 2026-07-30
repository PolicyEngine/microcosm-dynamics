"""Exact-byte reader for the modern PSID family job-context sidecar.

The legacy family earnings reader remains the sole source of its existing
seven-column panel.  This module emits a separate one-to-many relation of raw
BC/DE and shared family-context tokens.  Tokens are sliced from binary
fixed-width records and represented as lowercase hex; they are never
trimmed, coerced, classified, or interpreted as missing.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any, NamedTuple

import pandas as pd

from populace_dynamics.data import (
    panels,
    psid,
    psid_job_context_registry,
)

RAW_CONTEXT_COLUMNS: tuple[str, ...] = (
    "family_record_index",
    "family_interview_raw_token_hex",
    "interview_wave",
    "earnings_reference_year",
    "reader_role",
    "reader_job_slot",
    "reader_field_id",
    "field_ordinal",
    "source_block",
    "source_context_scope",
    "source_question_id",
    "raw_extraction_key",
    "source_field_key",
    "raw_field_id",
    "exact_short_label",
    "layout_start_1indexed",
    "layout_end_1indexed",
    "raw_width",
    "raw_token_hex",
    "source_document_ids",
)

PERSON_CONTEXT_COLUMNS: tuple[str, ...] = (
    "person_id",
    "interview_wave",
    "earnings_reference_year",
    "role",
    "reader_role",
    "reader_job_slot",
    "reader_field_id",
    "field_ordinal",
    "source_block",
    "source_context_scope",
    "source_question_id",
    "raw_extraction_key",
    "source_field_key",
    "raw_field_id",
    "raw_width",
    "raw_token_hex",
    "family_interview_raw_token_hex",
    "family_record_index",
)


class RawJobContextReadError(ValueError):
    """Raised when source bytes or setup metadata drift from the registry."""


class FamilyEarningsBundle(NamedTuple):
    """Separate legacy earnings and one-to-many raw context relations."""

    earnings: pd.DataFrame
    job_context: pd.DataFrame


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_registry_path() -> Path:
    return (
        _repository_root()
        / "data"
        / "external"
        / "psid_modern_job_context_raw_extraction_specs_v1.json"
    )


def default_dictionary_audit_path() -> Path:
    return _repository_root() / psid_job_context_registry.DICTIONARY_AUDIT_PATH


@lru_cache(maxsize=8)
def _load_evidence_cached(
    registry_path_string: str,
    dictionary_audit_path_string: str,
) -> tuple[bytes, bytes]:
    registry_path = Path(registry_path_string)
    audit_path = Path(dictionary_audit_path_string)
    registry_bytes = registry_path.read_bytes()
    audit_bytes = audit_path.read_bytes()
    registry = json.loads(registry_bytes)
    audit = json.loads(audit_bytes)
    psid_job_context_registry.validate_raw_extraction_registry(
        registry,
        audit,
        dictionary_audit_file_sha256=hashlib.sha256(audit_bytes).hexdigest(),
    )
    return registry_bytes, audit_bytes


def load_raw_extraction_evidence(
    *,
    registry_path: Path | None = None,
    dictionary_audit_path: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load and independently validate the two committed registry artifacts."""

    registry_file = (
        default_registry_path()
        if registry_path is None
        else Path(registry_path)
    ).resolve()
    audit_file = (
        default_dictionary_audit_path()
        if dictionary_audit_path is None
        else Path(dictionary_audit_path)
    ).resolve()
    registry_bytes, audit_bytes = _load_evidence_cached(
        str(registry_file),
        str(audit_file),
    )
    return json.loads(registry_bytes), json.loads(audit_bytes)


def _family_paths(wave: int, data_dir: Path | None) -> tuple[Path, Path]:
    base = psid._resolve_data_dir(data_dir) / "family" / str(wave)
    if not base.is_dir():
        raise FileNotFoundError(
            f"Family wave directory not found: {base} "
            f"({psid._README_POINTER})"
        )
    setup_paths = sorted(
        path
        for path in base.glob("*.sps")
        if not path.name.lower().endswith("_formats.sps")
    )
    text_paths = sorted(base.glob("*.txt"))
    if len(setup_paths) != 1 or len(text_paths) != 1:
        raise FileNotFoundError(
            f"Expected exactly one main .sps and one .txt in {base}; "
            f"found {len(setup_paths)} and {len(text_paths)}."
        )
    return setup_paths[0], text_paths[0]


def _wave_specs(
    registry: Mapping[str, Any],
    wave: int,
    reader_field_ids: Sequence[str] | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if isinstance(wave, bool) or not isinstance(wave, int):
        raise RawJobContextReadError("wave must be a JSON integer")
    if wave not in psid_job_context_registry.MODERN_INTERVIEW_WAVES:
        raise RawJobContextReadError(
            f"wave {wave} has no registered modern BC/DE raw extraction "
            "specs"
        )
    all_wave_specs = [
        row for row in registry["rows"] if row["interview_wave"] == wave
    ]
    interview_specs = [
        row
        for row in all_wave_specs
        if row["reader_field_id"] == "family_interview_id_raw"
    ]
    if len(interview_specs) != 1:
        raise RawJobContextReadError(
            f"wave {wave}: expected one family interview raw field"
        )
    if reader_field_ids is None:
        return all_wave_specs, interview_specs[0]
    requested = tuple(reader_field_ids)
    unknown = set(requested).difference(registry["reader_field_ids"])
    if unknown:
        raise RawJobContextReadError(
            f"unknown reader_field_ids: {sorted(unknown)}"
        )
    requested_set = set(requested)
    return (
        [
            row
            for row in all_wave_specs
            if row["reader_field_id"] in requested_set
        ],
        interview_specs[0],
    )


def _authority_row(
    dictionary_audit: Mapping[str, Any],
    wave: int,
    source_role: str,
) -> Mapping[str, Any]:
    authority_rows = [
        row
        for row in dictionary_audit["source_authority_manifest"]
        if row["interview_wave"] == wave
        and row["dictionary_role"] == source_role
    ]
    if len(authority_rows) != 1:
        raise RawJobContextReadError(
            f"wave {wave}: expected one SHA-pinned {source_role} "
            "authority row"
        )
    return authority_rows[0]


def _validate_authority_file(
    wave: int,
    source_path: Path,
    authority: Mapping[str, Any],
    description: str,
) -> None:
    observed_path = f"family/{wave}/{source_path.name}"
    if authority["path"] != observed_path:
        raise RawJobContextReadError(
            f"wave {wave}: staged {description} source path drift; "
            f"{observed_path!r} != {authority['path']!r}"
        )
    observed_size = source_path.stat().st_size
    digest = hashlib.sha256()
    with source_path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    observed_sha256 = digest.hexdigest()
    if (
        observed_size != authority["size_bytes"]
        or observed_sha256 != authority["sha256"]
    ):
        raise RawJobContextReadError(
            f"wave {wave}: staged {description} SHA/size drift; "
            f"observed ({observed_sha256}, {observed_size}) != "
            f"registered ({authority['sha256']}, "
            f"{authority['size_bytes']})"
        )


def _validate_staged_source_identity(
    wave: int,
    setup_path: Path,
    text_path: Path,
    dictionary_audit: Mapping[str, Any],
) -> None:
    """Validate all staged source identities before parsing or slicing."""

    _validate_authority_file(
        wave,
        setup_path,
        _authority_row(dictionary_audit, wave, "spss_setup"),
        "SPSS dictionary",
    )
    _validate_authority_file(
        wave,
        text_path,
        _authority_row(dictionary_audit, wave, "raw_fixed_width"),
        "raw fixed-width",
    )


def _validate_staged_setup(
    wave: int,
    setup_path: Path,
    text_path: Path,
    specs: Sequence[Mapping[str, Any]],
    interview_spec: Mapping[str, Any],
    dictionary_audit: Mapping[str, Any],
) -> int:
    _validate_staged_source_identity(
        wave,
        setup_path,
        text_path,
        dictionary_audit,
    )
    layout = psid.parse_sps_layout(setup_path)
    if layout["name"].duplicated().any():
        duplicates = sorted(
            layout.loc[layout["name"].duplicated(keep=False), "name"].unique()
        )
        raise RawJobContextReadError(
            f"wave {wave}: duplicate staged layout fields {duplicates[:4]}"
        )
    layout_by_name = layout.set_index("name")
    labels = psid.parse_sps_labels(setup_path)
    validate_specs = list(specs)
    if interview_spec["raw_extraction_key"] not in {
        row["raw_extraction_key"] for row in validate_specs
    }:
        validate_specs.append(interview_spec)
    for spec in validate_specs:
        raw_field_id = spec["raw_field_id"]
        if raw_field_id not in layout_by_name.index:
            raise RawJobContextReadError(
                f"wave {wave}: registered raw field {raw_field_id} is "
                "absent from the staged layout"
            )
        layout_row = layout_by_name.loc[raw_field_id]
        expected_layout = (
            spec["layout_start_1indexed"],
            spec["layout_end_1indexed"],
            spec["raw_width"],
        )
        actual_layout = (
            int(layout_row["start"]),
            int(layout_row["end"]),
            int(layout_row["width"]),
        )
        if actual_layout != expected_layout:
            raise RawJobContextReadError(
                f"wave {wave}: registered layout drift for {raw_field_id}: "
                f"{actual_layout} != {expected_layout}"
            )
        actual_label = " ".join(labels.get(raw_field_id, "").split())
        expected_label = " ".join(spec["exact_short_label"].split())
        if actual_label != expected_label:
            raise RawJobContextReadError(
                f"wave {wave}: registered label drift for {raw_field_id}: "
                f"{actual_label!r} != {expected_label!r}"
            )
    return int(layout["end"].max())


def _strip_record_terminator(line: bytes) -> bytes:
    if line.endswith(b"\r\n"):
        return line[:-2]
    if line.endswith(b"\n") or line.endswith(b"\r"):
        return line[:-1]
    return line


def _validate_nrows(nrows: int | None) -> int | None:
    if nrows is None:
        return None
    if isinstance(nrows, bool) or not isinstance(nrows, int) or nrows < 0:
        raise RawJobContextReadError(
            "nrows must be a nonnegative JSON integer or null"
        )
    return nrows


def _slice_token(
    record: bytes,
    spec: Mapping[str, Any],
) -> bytes:
    token = record[
        spec["layout_start_1indexed"] - 1 : spec["layout_end_1indexed"]
    ]
    if len(token) != spec["raw_width"]:
        raise RawJobContextReadError(
            f"raw slice width mismatch for {spec['raw_field_id']}"
        )
    return token


def _empty_raw_context_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=list(RAW_CONTEXT_COLUMNS))


def read_family_job_context_raw(
    wave: int,
    *,
    data_dir: Path | None = None,
    nrows: int | None = None,
    reader_field_ids: Sequence[str] | None = None,
    registry_path: Path | None = None,
    dictionary_audit_path: Path | None = None,
) -> pd.DataFrame:
    """Read one family wave's exact raw job-context tokens.

    The output is one row per source family record and selected registered
    field.  ``raw_token_hex`` and ``family_interview_raw_token_hex`` preserve
    every source byte.  No value, missing sentinel, reporting unit, timing
    relationship, or coverage class is interpreted.
    """

    row_limit = _validate_nrows(nrows)
    registry, dictionary_audit = load_raw_extraction_evidence(
        registry_path=registry_path,
        dictionary_audit_path=dictionary_audit_path,
    )
    specs, interview_spec = _wave_specs(
        registry,
        wave,
        reader_field_ids,
    )
    setup_path, text_path = _family_paths(wave, data_dir)
    record_width = _validate_staged_setup(
        wave,
        setup_path,
        text_path,
        specs,
        interview_spec,
        dictionary_audit,
    )
    if not specs or row_limit == 0:
        return _empty_raw_context_frame()

    output: dict[str, list[Any]] = {
        column: [] for column in RAW_CONTEXT_COLUMNS
    }
    with text_path.open("rb") as source:
        for family_record_index, line in enumerate(source):
            if row_limit is not None and family_record_index >= row_limit:
                break
            record = _strip_record_terminator(line)
            if len(record) != record_width:
                raise RawJobContextReadError(
                    f"wave {wave}, family record {family_record_index}: "
                    f"fixed-width record has {len(record)} bytes, expected "
                    f"{record_width}"
                )
            family_interview_hex = _slice_token(
                record,
                interview_spec,
            ).hex()
            for spec in specs:
                token_hex = _slice_token(record, spec).hex()
                output["family_record_index"].append(family_record_index)
                output["family_interview_raw_token_hex"].append(
                    family_interview_hex
                )
                for column in (
                    "interview_wave",
                    "earnings_reference_year",
                    "reader_role",
                    "reader_job_slot",
                    "reader_field_id",
                    "field_ordinal",
                    "source_block",
                    "source_context_scope",
                    "source_question_id",
                    "raw_extraction_key",
                    "source_field_key",
                    "raw_field_id",
                    "exact_short_label",
                    "raw_width",
                ):
                    output[column].append(spec[column])
                output["layout_start_1indexed"].append(
                    spec["layout_start_1indexed"]
                )
                output["layout_end_1indexed"].append(
                    spec["layout_end_1indexed"]
                )
                output["raw_token_hex"].append(token_hex)
                output["source_document_ids"].append(
                    tuple(spec["source_document_ids"])
                )
    frame = pd.DataFrame(output, columns=list(RAW_CONTEXT_COLUMNS))
    for column in (
        "family_record_index",
        "interview_wave",
        "earnings_reference_year",
        "field_ordinal",
        "layout_start_1indexed",
        "layout_end_1indexed",
        "raw_width",
    ):
        frame[column] = frame[column].astype("int64")
    return frame


def _role_people(
    wave_people: pd.DataFrame,
    wave: int,
    role: str,
) -> pd.DataFrame:
    from populace_dynamics.data import family

    head_codes, spouse_codes = family._relationship_codes(wave)
    codes = head_codes if role == "head" else spouse_codes
    people = wave_people.loc[
        wave_people["relationship"].isin(codes),
        ["person_id", "interview"],
    ].copy()
    if people["interview"].duplicated().any():
        duplicates = sorted(
            people.loc[
                people["interview"].duplicated(keep=False),
                "interview",
            ].unique()
        )
        raise RawJobContextReadError(
            f"wave {wave}: ambiguous {role} person attachment for family "
            f"interview(s) {duplicates[:4]}"
        )
    return people


def _validate_family_interview_token_agreement(
    wave: int,
    raw: pd.DataFrame,
) -> None:
    attachments = raw[
        [
            "family_record_index",
            "family_interview_raw_token_hex",
            "interview",
        ]
    ].drop_duplicates()
    if attachments["family_record_index"].duplicated().any():
        raise RawJobContextReadError(
            f"wave {wave}: inconsistent family interview attachment tokens"
        )
    for row in attachments.itertuples(index=False):
        try:
            token = bytes.fromhex(row.family_interview_raw_token_hex)
            token_text = token.decode("ascii")
        except (TypeError, ValueError, UnicodeDecodeError) as error:
            raise RawJobContextReadError(
                f"wave {wave}, family record {row.family_record_index}: "
                "family interview raw token is not canonical ASCII hex"
            ) from error
        if re.fullmatch(r" *[0-9]+", token_text) is None:
            raise RawJobContextReadError(
                f"wave {wave}, family record {row.family_record_index}: "
                f"family interview raw token is not numeric: {token_text!r}"
            )
        if pd.isna(row.interview):
            raise RawJobContextReadError(
                f"wave {wave}, family record {row.family_record_index}: "
                "typed family interview is missing"
            )
        raw_interview = int(token_text)
        try:
            typed_interview = int(row.interview)
        except (TypeError, ValueError, OverflowError) as error:
            raise RawJobContextReadError(
                f"wave {wave}, family record {row.family_record_index}: "
                f"typed family interview is invalid: {row.interview!r}"
            ) from error
        if (
            row.interview != typed_interview
            or raw_interview != typed_interview
        ):
            raise RawJobContextReadError(
                f"wave {wave}, family record {row.family_record_index}: "
                "raw/typed family interview token mismatch; "
                f"raw={token_text!r}, typed={row.interview!r}"
            )


def _empty_person_context_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=list(PERSON_CONTEXT_COLUMNS))


def family_job_context_panel(
    *,
    waves: Sequence[int] | None = None,
    data_dir: Path | None = None,
    family_nrows: int | None = None,
    individual_nrows: int | None = None,
    reader_field_ids: Sequence[str] | None = None,
    registry_path: Path | None = None,
    dictionary_audit_path: Path | None = None,
) -> pd.DataFrame:
    """Attach the raw family job-context relation to head/spouse persons.

    Shared family fields are repeated for each attached role.  The relation
    stays separate from :func:`family.family_earnings_panel`, because joining
    one-to-many context rows onto that seven-column panel would change its
    row and byte domain.
    """

    from populace_dynamics.data import family

    use_waves = (
        tuple(psid_job_context_registry.MODERN_INTERVIEW_WAVES)
        if waves is None
        else tuple(waves)
    )
    if not use_waves:
        return _empty_person_context_frame()
    for wave in use_waves:
        if wave not in psid_job_context_registry.MODERN_INTERVIEW_WAVES:
            raise RawJobContextReadError(
                f"wave {wave} has no registered modern raw context"
            )

    demo = panels.demographic_panel(
        data_dir=data_dir,
        nrows=_validate_nrows(individual_nrows),
        max_period=max(use_waves),
    )
    demo = demo[demo["period"].isin(use_waves)]
    registry, _ = load_raw_extraction_evidence(
        registry_path=registry_path,
        dictionary_audit_path=dictionary_audit_path,
    )
    registry_ordinal = {
        row["raw_extraction_key"]: ordinal
        for ordinal, row in enumerate(registry["rows"])
    }

    frames: list[pd.DataFrame] = []
    for wave in use_waves:
        raw = read_family_job_context_raw(
            wave,
            data_dir=data_dir,
            nrows=family_nrows,
            reader_field_ids=reader_field_ids,
            registry_path=registry_path,
            dictionary_audit_path=dictionary_audit_path,
        )
        if raw.empty:
            continue
        labor = family.read_family_labor(
            wave,
            data_dir=data_dir,
            nrows=family_nrows,
        ).reset_index(drop=True)
        if raw["family_record_index"].max() >= len(labor):
            raise RawJobContextReadError(
                f"wave {wave}: raw/labor family-record domains disagree"
            )
        family_interviews = labor[["interview"]].copy()
        family_interviews["family_record_index"] = family_interviews.index
        raw = raw.merge(
            family_interviews,
            on="family_record_index",
            how="left",
            validate="many_to_one",
        )
        _validate_family_interview_token_agreement(wave, raw)
        wave_people = demo[demo["period"] == wave]
        for role in ("head", "spouse"):
            people = _role_people(wave_people, wave, role)
            role_raw = raw[raw["reader_role"].isin(("shared", role))].copy()
            attached = role_raw.merge(
                people,
                on="interview",
                how="inner",
                validate="many_to_one",
            )
            if attached.empty:
                continue
            attached["role"] = role
            attached["_registry_ordinal"] = attached["raw_extraction_key"].map(
                registry_ordinal
            )
            if attached["_registry_ordinal"].isna().any():
                raise RawJobContextReadError(
                    "runtime extraction key absent from committed registry"
                )
            frames.append(attached)
    if not frames:
        return _empty_person_context_frame()
    panel = pd.concat(frames, ignore_index=True)
    if panel.duplicated(
        ["person_id", "interview_wave", "raw_extraction_key"]
    ).any():
        raise RawJobContextReadError(
            "duplicate person/wave/raw-extraction attachment"
        )
    panel["person_id"] = panel["person_id"].astype("int64")
    panel = panel.sort_values(
        [
            "person_id",
            "earnings_reference_year",
            "family_record_index",
            "_registry_ordinal",
        ]
    )
    return panel.loc[:, list(PERSON_CONTEXT_COLUMNS)].reset_index(drop=True)


def family_earnings_bundle(
    *,
    waves: Sequence[int] | None = None,
    data_dir: Path | None = None,
    reader_field_ids: Sequence[str] | None = None,
) -> FamilyEarningsBundle:
    """Return unchanged earnings beside, never merged with, raw context.

    The default domain is the modern 2003--2023 interview waves shared by
    both relations.  Keeping the one-to-many sidecar separate preserves the
    legacy earnings panel's exact row and column bytes.
    """

    from populace_dynamics.data import family

    use_waves = (
        tuple(psid_job_context_registry.MODERN_INTERVIEW_WAVES)
        if waves is None
        else tuple(waves)
    )
    return FamilyEarningsBundle(
        earnings=family.family_earnings_panel(
            waves=use_waves,
            data_dir=data_dir,
        ),
        job_context=family_job_context_panel(
            waves=use_waves,
            data_dir=data_dir,
            reader_field_ids=reader_field_ids,
        ),
    )
