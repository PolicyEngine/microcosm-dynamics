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
    assert len(frame) == 2 * 281
    assert frame["family_record_index"].nunique() == 2
    assert (frame.raw_token_hex.str.len() == 2 * frame.raw_width).all()
    assert set(frame.reader_role) == {"shared", "head", "spouse"}
    assert frame.raw_extraction_key.nunique() == 281


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
