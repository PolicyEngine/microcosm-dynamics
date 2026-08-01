"""Reproduction and source-integrity pin for the validation matrix."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATRIX_DIR = ROOT / "analysis" / "validation-matrix"
MATRIX_PATH = MATRIX_DIR / "matrix.json"
REPORT_PATH = MATRIX_DIR / "report.md"
MATRIX_BUILDER = MATRIX_DIR / "build_matrix.py"
REPORT_BUILDER = MATRIX_DIR / "build_report.py"

MATRIX_SHA256 = (
    "47c2e33ea799ead379088adf1013a95dfdbd74a634ddc90c7d8039898016e2a6"
)
REPORT_SHA256 = (
    "9ad213e83760aff235dd47b1b6ade317c36d9f4e5e6f0d51a9eada8972b95d3c"
)
VERIFIED_ROW_COUNT = 22
REPORTED_NOT_VERIFIED_ROW_COUNT = 20
UNMANIFESTED_MERMIN_SHA256 = (
    "88934782c267fb0d7f08106ef930a19866c41c89504d04ad7a6d77d454d034ae"
)
DERIVED_DYNASIM_ROW_IDS = {
    "dynasim.favreault_steuerle.package1b.married.male.lose_ge_5",
    "dynasim.favreault_steuerle.package1b.married.male.gain_ge_5",
    "dynasim.favreault_steuerle.package1b.married.female.lose_ge_5",
    "dynasim.favreault_steuerle.package1b.married.female.gain_ge_5",
    "dynasim.favreault_steuerle.package1b.divorced.male.lose_ge_5",
    "dynasim.favreault_steuerle.package1b.divorced.male.gain_ge_5",
    "dynasim.favreault_steuerle.package1b.divorced.female.gain_ge_5",
    "dynasim.favreault_steuerle.package1b.widowed.male.lose_ge_5",
    "dynasim.favreault_steuerle.package1b.widowed.female.lose_ge_5",
    "dynasim.mermin.four_reform_cost_ordering",
}


def _assert_sha256(value: str) -> None:
    assert len(value) == 64
    int(value, 16)


def test__validation_matrix__matches_reviewed_sha_and_row_count():
    matrix_raw = MATRIX_PATH.read_bytes()
    report_raw = REPORT_PATH.read_bytes()
    assert hashlib.sha256(matrix_raw).hexdigest() == MATRIX_SHA256
    assert hashlib.sha256(report_raw).hexdigest() == REPORT_SHA256

    matrix = json.loads(matrix_raw)
    reported = matrix["reported_not_verified"]
    assert matrix["row_count"] == VERIFIED_ROW_COUNT
    assert len(matrix["rows"]) == VERIFIED_ROW_COUNT
    assert reported["row_count"] == REPORTED_NOT_VERIFIED_ROW_COUNT
    assert len(reported["rows"]) == REPORTED_NOT_VERIFIED_ROW_COUNT
    assert matrix["total_row_count"] == (
        VERIFIED_ROW_COUNT + REPORTED_NOT_VERIFIED_ROW_COUNT
    )

    # Canonical rows must resolve to an accepted committed extraction or a
    # reviewed external capture. Unresolved and unmanifested pins fail closed.
    for row in matrix["rows"]:
        assert row["verification_class"] == "verified"
        assert ".mermin." not in row["row_id"]
        for locator in row["published"]["source_locators"]:
            assert "capture_status" not in locator
            assert "unmanifested_corroborating_copy" not in locator
            committed = locator.get("committed_extraction")
            reviewed = locator.get("reviewed_external_capture")
            assert (committed is None) != (reviewed is None)
            pin = committed if committed is not None else reviewed
            _assert_sha256(pin["sha256"])
            if reviewed is not None:
                assert reviewed["size_bytes"] > 0

    # Mermin stays visible only in the explicitly unverified class, with its
    # committed numeric provenance and the non-trusted corroborating-copy pin.
    assert (
        "mermin_2005_publisher_capture"
        in matrix["external_capture_review"]["missing_after_refresh"]
    )
    for row in reported["rows"]:
        assert row["verification_class"] == "reported_not_verified"
        assert ".mermin." in row["row_id"]
        provenance = row["published"]["provenance"]
        assert provenance["classification"] == "reported_not_verified"
        _assert_sha256(provenance["numeric_source"]["sha256"])
        for locator in row["published"]["source_locators"]:
            assert "missing after REFRESH" in locator["capture_status"]
            corroboration = locator["unmanifested_corroborating_copy"]
            assert corroboration["sha256"] == UNMANIFESTED_MERMIN_SHA256
            assert corroboration["manifested"] is False
            assert corroboration["accepted_as_verified_source"] is False

    # All 32 DYNASIM rows resolve to a source row and column. The nine
    # Favreault rounded-bucket sums and the Mermin ordering carry derivations.
    all_rows = [*matrix["rows"], *reported["rows"]]
    dynasim_rows = [
        row for row in all_rows if row["external_model"].startswith("DYNASIM")
    ]
    assert len(dynasim_rows) == 32
    derived_ids = set()
    for row in dynasim_rows:
        for locator in row["published"]["source_locators"]:
            assert locator["row_path"]
            assert locator["column_path"]
            if locator.get("derivation"):
                derived_ids.add(row["row_id"])
    assert derived_ids == DERIVED_DYNASIM_ROW_IDS

    # Both check modes compare in memory and leave the tracked files untouched.
    before = {MATRIX_PATH: matrix_raw, REPORT_PATH: report_raw}
    for builder in (MATRIX_BUILDER, REPORT_BUILDER):
        subprocess.run(
            [sys.executable, str(builder), "--check"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    assert {path: path.read_bytes() for path in before} == before
