"""The F17 published-source readers against the committed files.

Reads two committed files under ``data/external``: the SSI capture and the
SSA Annual Statistical Supplement 2025 section 5.A snapshot.  The Table
5.A4 cells below were transcribed by hand from that snapshot (they are
published SSA figures, not PSID values or comparator values); the test
checks that the parser returns exactly them.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from populace_dynamics.estimates import adjusted_poverty as ap
from populace_dynamics.uniform_cut_track_u import diagnostics as dg

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_MANIFEST = (
    ROOT
    / "data"
    / "external"
    / "snapshots"
    / "ssa_level_anchors_vintage1"
    / "capture_manifest.txt"
)


def test_the_snapshot_pin_is_the_capture_manifest_hash():
    manifest = SNAPSHOT_MANIFEST.read_text(encoding="utf-8")
    line = next(
        entry
        for entry in manifest.splitlines()
        if entry.endswith("supplement2025_5a.html")
    )
    assert line.split()[1] == dg.SSA_5A_SNAPSHOT_SHA256


def test_table_5a4_cells_as_published():
    cells = dg.ssa_table_5a4([2003, 2004, 2010, 2012])
    # Retired workers, December: number and total monthly benefits
    # (thousands of dollars), as printed.
    assert cells[2004]["retired_workers"]["number"] == 29_952_465
    assert cells[2004]["retired_workers"]["total_monthly_thousands"] == (
        28_601_329
    )
    assert cells[2010]["retired_workers"]["number"] == 34_593_080
    assert cells[2010]["retired_workers"]["total_monthly_thousands"] == (
        40_662_492
    )
    assert cells[2003]["widowers"]["number"] == 4_707_215
    assert cells[2012]["wives_and_husbands"]["number"] == 2_443_212
    # the average is the division 1000 * total / number
    assert cells[2004]["retired_workers"]["average_monthly"] == (
        pytest.approx(1000 * 28_601_329 / 29_952_465)
    )
    combined = cells[2003]["aged_types_combined"]
    assert combined["number"] == 29_531_611 + 2_772_577 + 4_707_215
    assert combined["total_monthly_thousands"] == (
        27_230_634 + 1_247_504 + 4_110_963
    )


def test_table_5a4_refuses_a_changed_snapshot(tmp_path):
    copy = tmp_path / "supplement2025_5a.html"
    shutil.copy(dg.SSA_5A_SNAPSHOT_PATH, copy)
    with copy.open("a", encoding="utf-8") as handle:
        handle.write("\n")
    with pytest.raises(ValueError, match="sha256"):
        dg.ssa_table_5a4([2004], copy)
    with pytest.raises(ValueError, match="December 1939"):
        dg.ssa_table_5a4([1939])


def test_federal_benefit_rates_equal_the_income_concepts_capture():
    assert dg.SSI_PARAMETERS_SHA256 == ap.SSI_PARAMETERS_SHA256
    assert dg.SSI_PARAMETERS_PATH == ap.SSI_PARAMETERS_PATH
    rates = dg.federal_benefit_rates()
    ssi = ap.load_ssi_parameters()
    assert rates["individual"] == dict(ssi.fbr_individual_monthly)
    assert rates["couple"] == dict(ssi.fbr_couple_monthly)
    assert rates["rule"] == "value in force on January 1 of the income year"
    assert rates["source"]["sha256"] == ap.SSI_PARAMETERS_SHA256
