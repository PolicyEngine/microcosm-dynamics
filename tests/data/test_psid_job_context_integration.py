"""Off-machine-skippable checks against staged PSID family bytes."""

from __future__ import annotations

from pathlib import Path

import pytest

from populace_dynamics.data import psid_job_context

PSID_ROOT = Path("~/PolicyEngine/psid-data").expanduser()
needs_psid = pytest.mark.skipif(
    not (PSID_ROOT / "family" / "2003").is_dir(),
    reason="PSID family files not staged",
)


@needs_psid
def test_real_2003_raw_context_has_exact_record_field_product():
    frame = psid_job_context.read_family_job_context_raw(
        2003,
        data_dir=PSID_ROOT,
        nrows=2,
    )
    assert len(frame) == 2 * 297
    assert frame["family_record_index"].nunique() == 2
    assert (frame.raw_token_hex.str.len() == 2 * frame.raw_width).all()
    assert set(frame.reader_role) == {"shared", "head", "spouse"}
    assert frame.raw_extraction_key.nunique() == 297


@needs_psid
def test_cached_evidence_cannot_poison_er21145_with_er21146_coordinates():
    registry, _ = psid_job_context.load_raw_extraction_evidence()
    occupation = next(
        row
        for row in registry["rows"]
        if row["interview_wave"] == 2003
        and row["reader_role"] == "head"
        and row["reader_job_slot"] == "job_1"
        and row["reader_field_id"] == "occupation_raw"
    )
    occupation.update(
        {
            "raw_field_id": "ER21146",
            "exact_short_label": ("BC21 MAIN IND FOR JOB 1: 2000 CODE (HD)"),
            "layout_start_1indexed": 271,
            "layout_end_1indexed": 273,
        }
    )

    frame = psid_job_context.read_family_job_context_raw(
        2003,
        data_dir=PSID_ROOT,
        nrows=1,
        reader_field_ids=("occupation_raw",),
    )
    actual = frame.loc[
        (frame["reader_role"] == "head")
        & (frame["reader_job_slot"] == "job_1")
    ].squeeze()
    assert actual["raw_field_id"] == "ER21145"
    assert actual["exact_short_label"] == (
        "BC20 MAIN OCC FOR JOB 1: 2000 CODE (HD)"
    )
    assert (
        actual["layout_start_1indexed"],
        actual["layout_end_1indexed"],
    ) == (268, 270)


@needs_psid
def test_real_person_context_attachment_is_unique():
    panel = psid_job_context.family_job_context_panel(
        waves=(2003,),
        data_dir=PSID_ROOT,
        family_nrows=3,
    )
    assert len(panel) > 0
    assert set(panel.role).issubset({"head", "spouse"})
    assert not panel.duplicated(
        ["person_id", "interview_wave", "raw_extraction_key"]
    ).any()
    assert (panel.earnings_reference_year == 2002).all()
