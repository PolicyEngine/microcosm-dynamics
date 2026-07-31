"""Off-machine-skippable checks against staged PSID family bytes."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from populace_dynamics.data import psid_job_context

PSID_ROOT = Path("~/PolicyEngine/psid-data").expanduser()
needs_psid = pytest.mark.skipif(
    not (PSID_ROOT / "family" / "2003").is_dir(),
    reason="PSID family files not staged",
)


def _stage_real_2003_setup(tmp_path: Path) -> Path:
    staged = tmp_path / "family" / "2003"
    staged.mkdir(parents=True)
    shutil.copyfile(
        PSID_ROOT / "family" / "2003" / "FAM2003ER.sps",
        staged / "FAM2003ER.sps",
    )
    return staged


@needs_psid
def test_all_eleven_real_waves_read_declared_physical_subset():
    waves = psid_job_context.psid_job_context_registry.MODERN_INTERVIEW_WAVES
    assert len(waves) == 11
    observed_counts = {}
    for wave in waves:
        frame = psid_job_context.read_family_job_context_raw(
            wave,
            data_dir=PSID_ROOT,
            nrows=1,
        )
        expected_count = 297 if wave in (2003, 2005) else 281
        observed_counts[wave] = len(frame)
        assert len(frame) == expected_count
        assert frame["family_record_index"].nunique() == 1
        assert (frame.raw_token_hex.str.len() == 2 * frame.raw_width).all()
        assert set(frame.reader_role) == {"shared", "head", "spouse"}
        assert frame.raw_extraction_key.nunique() == expected_count
    assert sum(observed_counts.values()) == 3_123


@needs_psid
def test_same_size_dictionary_sha_mutation_fails_closed(tmp_path: Path):
    staged = _stage_real_2003_setup(tmp_path)
    setup_path = staged / "FAM2003ER.sps"
    original = setup_path.read_bytes()
    mutated = bytearray(original)
    mutated[0] ^= 1
    setup_path.write_bytes(mutated)
    (staged / "FAM2003ER.txt").touch()
    assert setup_path.stat().st_size == len(original)

    with pytest.raises(
        psid_job_context.RawJobContextReadError,
        match="SPSS dictionary SHA/size drift",
    ):
        psid_job_context.read_family_job_context_raw(
            2003,
            data_dir=tmp_path,
            nrows=1,
        )


@needs_psid
def test_raw_text_source_path_identity_fails_closed(tmp_path: Path):
    staged = _stage_real_2003_setup(tmp_path)
    (staged / "renamed.txt").symlink_to(
        PSID_ROOT / "family" / "2003" / "FAM2003ER.txt"
    )

    with pytest.raises(
        psid_job_context.RawJobContextReadError,
        match="raw fixed-width source path drift",
    ):
        psid_job_context.read_family_job_context_raw(
            2003,
            data_dir=tmp_path,
            nrows=1,
        )


@needs_psid
def test_same_size_raw_text_sha_mutation_fails_closed(tmp_path: Path):
    staged = _stage_real_2003_setup(tmp_path)
    authoritative = PSID_ROOT / "family" / "2003" / "FAM2003ER.txt"
    raw_path = staged / "FAM2003ER.txt"
    with raw_path.open("wb") as raw:
        raw.truncate(authoritative.stat().st_size)
    assert raw_path.stat().st_size == authoritative.stat().st_size

    with pytest.raises(
        psid_job_context.RawJobContextReadError,
        match="raw fixed-width SHA/size drift",
    ):
        psid_job_context.read_family_job_context_raw(
            2003,
            data_dir=tmp_path,
            nrows=1,
        )


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
            "raw_width": 3,
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
    assert actual["reader_field_id"] == "occupation_raw"
    assert actual["raw_field_id"] == "ER21145"
    assert actual["exact_short_label"] == (
        "BC20 MAIN OCC FOR JOB 1: 2000 CODE (HD)"
    )
    assert (
        actual["layout_start_1indexed"],
        actual["layout_end_1indexed"],
    ) == (268, 270)
    assert actual["raw_token_hex"] == "202030"


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
