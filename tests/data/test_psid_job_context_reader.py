"""Synthetic-byte tests for the PSID raw job-context sidecar."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from populace_dynamics.data import family, psid_job_context

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = (
    REPO_ROOT
    / "data"
    / "external"
    / "psid_modern_job_context_raw_extraction_specs_v1.json"
)

LABOR_FIELDS = (
    (
        "ER24116",
        6028,
        6034,
        "LABOR INCOME OF HEAD LAST YEAR",
        (30_000, 40_000),
    ),
    (
        "ER24118",
        6042,
        6042,
        "ACC WAGES AND SALARIES OF HEAD LAST YEAR",
        (1, 5),
    ),
    (
        "ER24134",
        6101,
        6101,
        "ACC MISC LABOR INCOME OF HEAD LAST YEAR",
        (3, 0),
    ),
    (
        "ER24135",
        6102,
        6108,
        "LABOR INCOME OF WIFE LAST YEAR",
        (12_000, 0),
    ),
    (
        "ER24136",
        6109,
        6109,
        "ACC LABOR INCOME OF WIFE LAST YEAR",
        (2, 0),
    ),
)


def _write_sps(path: Path, fields: list[dict]) -> None:
    layout = "\n".join(
        f"      {row['name']:<15} {row['start']} - {row['end']}"
        for row in fields
    )
    labels = "\n".join(
        f'      {row["name"]:<12} "{row["label"]}"' for row in fields
    )
    path.write_text(
        "DATA LIST FILE = PSID FIXED /\n"
        + layout
        + "\n.\n\nVARIABLE LABELS\n"
        + labels
        + "\n.\n",
        encoding="utf-8",
    )


@pytest.fixture()
def modern_family_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(
        psid_job_context,
        "_validate_staged_source_identity",
        lambda *_args: None,
    )
    artifact = json.loads(REGISTRY_PATH.read_bytes())
    registry_rows = [
        row for row in artifact["rows"] if row["interview_wave"] == 2003
    ]
    fields = [
        {
            "name": row["raw_field_id"],
            "start": row["layout_start_1indexed"],
            "end": row["layout_end_1indexed"],
            "label": row["exact_short_label"],
        }
        for row in registry_rows
    ]
    fields.extend(
        {
            "name": name,
            "start": start,
            "end": end,
            "label": label,
        }
        for name, start, end, label, _ in LABOR_FIELDS
    )
    fields.sort(key=lambda row: row["start"])
    family_dir = tmp_path / "family" / "2003"
    family_dir.mkdir(parents=True)
    _write_sps(family_dir / "FAM2003ER.sps", fields)

    record_width = max(row["end"] for row in fields)
    records = []
    context_values = (
        {
            "ER21002": b"    7",
            "ER21003": b"06",
            "ER21004": b"42",
            "ER21129": b"01",
            "ER21145": b"123",
            "ER21278": b"     12345",
            "ER21279": b"1",
            "ER21379": b"02",
        },
        {
            "ER21002": b"    8",
            "ER21003": b"09",
            "ER21004": b"44",
            "ER21129": b"03",
            "ER21145": b"456",
            "ER21278": b"     54321",
            "ER21279": b"2",
            "ER21379": b"04",
        },
    )
    by_name = {row["name"]: row for row in fields}
    for record_index, values in enumerate(context_values):
        record = bytearray(b" " * record_width)
        for name, value in values.items():
            row = by_name[name]
            assert len(value) == row["end"] - row["start"] + 1
            record[row["start"] - 1 : row["end"]] = value
        for _name, start, end, _, source_values in LABOR_FIELDS:
            value = (
                f"{source_values[record_index]:>{end - start + 1}}".encode()
            )
            record[start - 1 : end] = value
        records.append(bytes(record))
    (family_dir / "FAM2003ER.txt").write_bytes(b"\r\n".join(records) + b"\r\n")

    individual_dir = tmp_path / "ind2023er"
    individual_dir.mkdir()
    individual_fields = [
        {
            "name": "ER30001",
            "start": 1,
            "end": 2,
            "label": "1968 INTERVIEW NUMBER",
            "values": (1, 1, 2),
        },
        {
            "name": "ER30002",
            "start": 3,
            "end": 5,
            "label": "PERSON NUMBER   68",
            "values": (1, 2, 1),
        },
        {
            "name": "A1",
            "start": 6,
            "end": 7,
            "label": "AGE OF INDIVIDUAL   03",
            "values": (40, 38, 50),
        },
        {
            "name": "S1",
            "start": 8,
            "end": 9,
            "label": "SEQUENCE NUMBER   03",
            "values": (1, 2, 1),
        },
        {
            "name": "R1",
            "start": 10,
            "end": 11,
            "label": "RELATIONSHIP TO HEAD   03",
            "values": (10, 20, 10),
        },
        {
            "name": "W1",
            "start": 12,
            "end": 13,
            "label": "CORE INDIVIDUAL LONGITUDINAL WEIGHT 03",
            "values": (15, 14, 16),
        },
        {
            "name": "I1",
            "start": 14,
            "end": 15,
            "label": "2003 INTERVIEW NUMBER",
            "values": (7, 7, 8),
        },
    ]
    _write_sps(individual_dir / "IND2023ER.sps", individual_fields)
    individual_records = []
    for record_index in range(3):
        individual_records.append(
            "".join(
                f"{row['values'][record_index]:>{row['end'] - row['start'] + 1}}"
                for row in individual_fields
            )
        )
    (individual_dir / "IND2023ER.txt").write_text(
        "\n".join(individual_records) + "\n",
        encoding="ascii",
    )
    return tmp_path


def test_raw_reader_emits_declared_physical_exact_byte_subset(
    modern_family_dir: Path,
):
    frame = psid_job_context.read_family_job_context_raw(
        2003,
        data_dir=modern_family_dir,
        nrows=1,
    )
    assert list(frame.columns) == list(psid_job_context.RAW_CONTEXT_COLUMNS)
    assert len(frame) == 297
    assert set(frame["family_record_index"]) == {0}
    assert set(frame["family_interview_raw_token_hex"]) == {"2020202037"}
    for row in frame.itertuples(index=False):
        assert len(row.raw_token_hex) == 2 * row.raw_width
        assert row.raw_token_hex == row.raw_token_hex.lower()
    assert not {
        "typed_value",
        "is_missing",
        "source_disposition",
        "remuneration_type",
        "year_source_class",
    }.intersection(frame.columns)


def test_public_reader_apis_expose_no_source_identity_bypass():
    for function in (
        psid_job_context.read_family_job_context_raw,
        psid_job_context.family_job_context_panel,
        psid_job_context.family_earnings_bundle,
    ):
        assert (
            "require_dictionary_sha"
            not in inspect.signature(function).parameters
        )


def test_raw_reader_preserves_spaces_and_source_widths(
    modern_family_dir: Path,
):
    frame = psid_job_context.read_family_job_context_raw(
        2003,
        data_dir=modern_family_dir,
        nrows=1,
    ).set_index("raw_field_id")
    assert frame.loc["ER21002", "raw_token_hex"] == b"    7".hex()
    assert frame.loc["ER21129", "raw_token_hex"] == b"01".hex()
    assert frame.loc["ER21130", "raw_token_hex"] == b"    ".hex()
    assert frame.loc["ER21145", "raw_token_hex"] == b"123".hex()
    assert frame.loc["ER21278", "raw_token_hex"] == b"     12345".hex()


def test_reader_field_filter_is_explicit_and_still_keeps_raw_join_key(
    modern_family_dir: Path,
):
    frame = psid_job_context.read_family_job_context_raw(
        2003,
        data_dir=modern_family_dir,
        reader_field_ids=("occupation_raw",),
    )
    assert len(frame) == 2 * 8
    assert set(frame["reader_field_id"]) == {"occupation_raw"}
    assert set(frame["family_interview_raw_token_hex"]) == {
        b"    7".hex(),
        b"    8".hex(),
    }


def test_person_sidecar_attaches_shared_and_role_fields(
    modern_family_dir: Path,
):
    panel = psid_job_context.family_job_context_panel(
        waves=(2003,),
        data_dir=modern_family_dir,
    )
    assert list(panel.columns) == list(psid_job_context.PERSON_CONTEXT_COLUMNS)
    assert len(panel) == 450
    assert panel.groupby("person_id").size().to_dict() == {
        1001: 150,
        1002: 150,
        2001: 150,
    }
    by_person = panel.groupby("person_id")
    assert set(by_person.get_group(1001)["reader_role"]) == {"shared", "head"}
    assert set(by_person.get_group(1002)["reader_role"]) == {
        "shared",
        "spouse",
    }
    assert not panel.duplicated(
        ["person_id", "interview_wave", "raw_extraction_key"]
    ).any()


def test_person_attachment_rejects_raw_typed_interview_token_mismatch(
    modern_family_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    read_family_labor = family.read_family_labor

    def mismatched_family_labor(*args, **kwargs):
        frame = read_family_labor(*args, **kwargs).copy()
        frame.loc[0, "interview"] = 9
        return frame

    monkeypatch.setattr(
        family,
        "read_family_labor",
        mismatched_family_labor,
    )
    with pytest.raises(
        psid_job_context.RawJobContextReadError,
        match="raw/typed family interview token mismatch",
    ):
        psid_job_context.family_job_context_panel(
            waves=(2003,),
            data_dir=modern_family_dir,
        )


def test_person_attachment_rejects_unmatched_head_interview(
    modern_family_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    demographic_panel = psid_job_context.panels.demographic_panel

    def missing_head(*args, **kwargs):
        frame = demographic_panel(*args, **kwargs)
        return frame[frame["person_id"] != 2001]

    monkeypatch.setattr(
        psid_job_context.panels,
        "demographic_panel",
        missing_head,
    )
    with pytest.raises(
        psid_job_context.RawJobContextReadError,
        match="unmatched head person attachment",
    ):
        psid_job_context.family_job_context_panel(
            waves=(2003,),
            data_dir=modern_family_dir,
        )


def test_bundle_keeps_earnings_and_context_as_separate_relations(
    modern_family_dir: Path,
):
    before = family.family_earnings_panel(
        waves=(2003,),
        data_dir=modern_family_dir,
    )
    before_bytes = before.to_csv(index=False, lineterminator="\n").encode()
    bundle = psid_job_context.family_earnings_bundle(
        waves=(2003,),
        data_dir=modern_family_dir,
    )
    after_bytes = bundle.earnings.to_csv(
        index=False,
        lineterminator="\n",
    ).encode()
    assert after_bytes == before_bytes
    assert list(bundle.earnings.columns) == [
        "person_id",
        "period",
        "earnings",
        "earnings_acc",
        "role",
        "age",
        "weight",
    ]
    assert list(bundle.job_context.columns) == list(
        psid_job_context.PERSON_CONTEXT_COLUMNS
    )
    assert len(bundle.earnings) == 3
    assert len(bundle.job_context) == 450


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("label", "label drift"),
        ("layout", "layout drift"),
        ("record", "fixed-width record"),
    ],
)
def test_source_drift_fails_closed(
    modern_family_dir: Path,
    mutation: str,
    message: str,
):
    setup_path = modern_family_dir / "family" / "2003" / "FAM2003ER.sps"
    text_path = modern_family_dir / "family" / "2003" / "FAM2003ER.txt"
    if mutation == "label":
        setup_path.write_text(
            setup_path.read_text().replace(
                "BC20 MAIN OCC FOR JOB 1: 2000 CODE (HD)",
                "BC20 CHANGED",
            )
        )
    elif mutation == "layout":
        setup_path.write_text(
            setup_path.read_text().replace(
                "ER21145         268 - 270",
                "ER21145         267 - 270",
            )
        )
    else:
        lines = text_path.read_bytes().splitlines()
        lines[0] = lines[0][:-1]
        text_path.write_bytes(b"\r\n".join(lines) + b"\r\n")
    with pytest.raises(psid_job_context.RawJobContextReadError, match=message):
        psid_job_context.read_family_job_context_raw(
            2003,
            data_dir=modern_family_dir,
            nrows=1,
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"wave": 2001},
        {"wave": True},
        {"wave": 2003, "nrows": True},
        {"wave": 2003, "reader_field_ids": ("not_registered",)},
    ],
)
def test_invalid_reader_requests_fail_closed(
    modern_family_dir: Path,
    kwargs: dict,
):
    with pytest.raises(psid_job_context.RawJobContextReadError):
        psid_job_context.read_family_job_context_raw(
            data_dir=modern_family_dir,
            **kwargs,
        )
