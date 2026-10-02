"""G3 source artifacts: captured MINT8 definitions and labels only.

These artifact-tier checks read only the committed source captures under
``data/external`` and their provenance records.  They never fetch a page,
open microdata or read model outcomes or comparator values.
"""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

import pytest

from populace_dynamics.estimates import group_breakdown as gb

_ROOT = Path(__file__).resolve().parents[2]
_EXTERNAL = _ROOT / "data" / "external"
_CAPTURES = (
    (
        "mint8_row_categories.json",
        "mint8_row_categories.provenance.json",
        "https://www.ssa.gov/policy/docs/projections/policy-options/"
        "increase-payroll-tax-rate.html",
        "2026-04-01",
    ),
    (
        "mint8_table_user_guide.source.html",
        "mint8_table_user_guide.source.provenance.json",
        "https://www.ssa.gov/policy/docs/projections/user-guide.html",
        "2025-10-01",
    ),
)


@pytest.mark.parametrize(
    "filename,provenance_filename,source_url,date_certified", _CAPTURES
)
def test_capture_bytes_match_source_pins_and_provenance(
    filename, provenance_filename, source_url, date_certified
):
    raw = (_EXTERNAL / filename).read_bytes()
    relative = f"data/external/{filename}"
    provenance = json.loads(
        (_EXTERNAL / provenance_filename).read_text(encoding="utf-8")
    )
    digest = hashlib.sha256(raw).hexdigest()
    assert digest == gb.MINT8_SOURCE_SHA256[relative]
    assert digest == provenance["source_sha256"]
    assert len(raw) == provenance["source_length_bytes"]
    assert provenance["schema_version"] == "external_source_provenance.v1"
    assert provenance["committed_source_file"] == relative
    assert provenance["source_url"] == source_url
    assert provenance["date_certified"] == date_certified
    assert provenance["retrieval_date"] == "2026-10-01"


def test_label_capture_metadata_matches_its_provenance():
    labels = json.loads(
        (_EXTERNAL / "mint8_row_categories.json").read_text(encoding="utf-8")
    )
    provenance = json.loads(
        (_EXTERNAL / "mint8_row_categories.provenance.json").read_text(
            encoding="utf-8"
        )
    )
    assert labels["source_url"] == provenance["source_url"]
    assert labels["dateCertified"] == provenance["date_certified"]
    assert labels["raw_sha256"] == provenance["raw_page_sha256"]
    assert "LABELS ONLY" in labels["note"]
    # Only captions, headings and labels are retained from the option page.
    for table in labels["tables"].values():
        assert set(table) == {"caption", "columns", "groups"}
        for group in table["groups"]:
            assert set(group) == {"group", "labels"}


def test_guide_capture_matches_recorded_archive_digest_and_date_locator():
    raw = (_EXTERNAL / "mint8_table_user_guide.source.html").read_bytes()
    provenance = json.loads(
        (
            _EXTERNAL / "mint8_table_user_guide.source.provenance.json"
        ).read_text(encoding="utf-8")
    )
    digest = base64.b32encode(hashlib.sha1(raw).digest()).decode("ascii")
    assert digest == provenance["source_sha1_base32"]
    assert provenance["date_certified_locator"].split(" in ")[0] in (
        raw.decode("utf-8")
    )


def test_verification_checks_all_published_layouts_and_composites():
    verification = gb.verify_mint8_sources()
    assert verification["files_sha256"] == gb.MINT8_SOURCE_SHA256
    assert verification["schemes_checked"] == {
        "mint8_beneficiary_annual": ["1", "2", "3", "7", "8", "9"],
        "mint8_beneficiary_poverty": ["10", "11", "12"],
        "mint8_cohort": [str(number) for number in range(13, 21)],
        "mint8_beneficiary_annual_with_lifetime": [
            "mint8_beneficiary_annual + table 13"
        ],
        "mint8_beneficiary_poverty_with_lifetime": [
            "mint8_beneficiary_poverty + table 13"
        ],
    }
    assert verification["n_quotes_checked"] > 0


@pytest.mark.parametrize("relative", tuple(gb.MINT8_SOURCE_SHA256))
def test_verification_refuses_tampered_capture_bytes(tmp_path, relative):
    # Temporary copies contain captured definitions/labels only.  Do not
    # modify the committed source files to exercise their hash guard.
    for source in gb.MINT8_SOURCE_SHA256:
        target = tmp_path / source
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((_ROOT / source).read_bytes())
    target = tmp_path / relative
    target.write_bytes(target.read_bytes() + b"\nINVENTED tampering\n")
    with pytest.raises(gb.GroupBreakdownError, match="SHA-256.*pin"):
        gb.verify_mint8_sources(tmp_path)
