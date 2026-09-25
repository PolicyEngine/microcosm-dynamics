"""F17 component diagnostics on the staged PSID (no poverty statistic).

Skipped when the staged PSID products under ``~/PolicyEngine/psid-data``
are absent.  Runs ``scripts/track_u_component_diagnostics.py`` in a fresh
interpreter (the script refuses to run once the income concept is
imported, which other tests in this process do) and checks its structure:
the population, that no income-concept module was loaded, and the
``# IN FU`` record counts the institution rule relies on.  It asserts no
Social Security, SSI or WEALTH1 value.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from populace_dynamics.cohorts import age67

ROOT = Path(__file__).resolve().parents[2]
REAL_DATA = Path("~/PolicyEngine/psid-data").expanduser()

needs_real_psid = pytest.mark.skipif(
    not (REAL_DATA / "ind2023er").is_dir()
    or not all(
        (REAL_DATA / "family" / str(wave)).is_dir() for wave in age67.WAVES
    ),
    reason="staged PSID individual and family files not present",
)


@needs_real_psid
def test_component_diagnostics_on_the_staged_psid(tmp_path):
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "track_u_component_diagnostics.py"),
            "--output-dir",
            str(tmp_path),
            "--data-dir",
            str(REAL_DATA),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(
        (tmp_path / "track-u-component-diagnostics.json").read_text()
    )
    assert result["forbidden_modules_loaded"] == []
    assert result["provenance"]["kind"] == age67.PSID_FILES
    diag = result["diagnostics"]
    # structure found on the staged files 2026-09-24 (counts only)
    assert diag["population"]["n_observations"] == 483
    assert diag["population"]["income_years"] == [2004, 2006, 2008, 2010, 2012]
    # u1-draft-6: the 2005 and 2007 wealth supplements are staged and
    # adjudicated, so every income year has WEALTH1 and nothing is refused
    assert set(diag["wealth1"]) == {"2004", "2006", "2008", "2010", "2012"}
    assert result["wealth_refusals"] == {}
    for counts in diag["institution_record_counts"].values():
        assert counts["n_fu_size_equals_in_family_records"] == (
            counts["n_families"]
        )
        assert (
            counts["of_which_fu_size_equals_in_family_plus_institution"] == 0
        )
        assert counts["n_families_with_institution_records"] > 0
    assert "not_compared" in diag["published_sources"]["wealth1"]
    text = (tmp_path / "SUMMARY.md").read_text()
    for forbidden in ("poverty rate:", "threshold:", "annuity:"):
        assert forbidden not in text
