"""Verify data/external legal captures and generated RMD parameters.

No population records or empirical model outputs are read.
"""

import hashlib
import json
import runpy
from datetime import datetime
from pathlib import Path

import pytest

from populace_dynamics.income_resources import retirement_rules

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "external" / "income_resources" / "retirement_rules_v1"


def test_capture_manifests_pin_every_retained_source():
    for manifest in DATA.glob("*/capture_manifest.json"):
        rows = json.loads(manifest.read_text())
        assert rows
        for row in rows:
            assert row["url"].startswith("https://")
            assert (
                datetime.fromisoformat(
                    row.get("retrieved_at_utc", row.get("retrieved_utc"))
                )
                .utcoffset()
                .total_seconds()
                == 0
            )
            if (
                row.get("file")
                and row.get("status")
                not in ("SOURCE_BLOCKED", "SOURCE_UNAVAILABLE")
                and row.get("result") != "SOURCE_BLOCKED"
            ):
                body = (manifest.parent / row["file"]).read_bytes()
                assert len(body) == row.get("bytes", row.get("size_bytes"))
                assert hashlib.sha256(body).hexdigest() == row["sha256"]


def test_rmd_parameter_source_differential():
    source = runpy.run_path(str(DATA / "rmd/build_parameters.py"))
    actual = json.loads((DATA / "rmd/parameters.json").read_text())
    assert actual["schema_version"] == 1
    for vintage in ("2003", "2022"):
        assert source["extract"](vintage) == actual[vintage]


def test_unknown_rmd_parameter_version_raises(monkeypatch):
    retirement_rules._tables.cache_clear()
    monkeypatch.setattr(
        retirement_rules.json, "loads", lambda _: {"schema_version": 2}
    )
    try:
        with pytest.raises(ValueError, match="schema"):
            retirement_rules.rmd_divisor(2026, 75)
    finally:
        retirement_rules._tables.cache_clear()


def test_all_covered_table_fractions_and_bounds():
    tables = json.loads((DATA / "rmd/parameters.json").read_text())
    for vintage, minimum in (("2003", 70), ("2022", 72)):
        uniform = tables[vintage]["uniform"]
        joint = tables[vintage]["joint"]
        for age in range(minimum, 121):
            assert uniform[str(age)] >= 1
            assert set(joint[str(age)]) == {str(s) for s in range(121)}
            if age < 120:
                assert uniform[str(age)] >= uniform[str(age + 1)]
            for spouse in range(121):
                assert joint[str(age)][str(spouse)] >= 1
                if age < 120:
                    left = joint[str(age)][str(spouse)]
                    right = joint[str(age + 1)][str(spouse)]
                    if (vintage, age, spouse) == ("2003", 97, 20):
                        # Explicit, sourced CFR/IRS conflict; no silent fix.
                        assert (left, right) == (60.3, 63.0)
                        left = tables["disputed_historical_joint_cell"][
                            "irs_publication_63_0"
                        ]
                    assert left >= right
