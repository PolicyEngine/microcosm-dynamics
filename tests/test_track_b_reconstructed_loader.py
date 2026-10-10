"""Differential: the unchanged SSA loader against B1 v2's ssa_revision probe.

Rule (a) holds only if the probe reports exactly what
``load_ssa_parameters`` records as ``pe_us_revision``, which
``m6_inputs`` copies into ``external_details.ssa_revision``. Each case
creates minimal invented parameter files in an invented install directory
and runs both. No external parameter checkout or PSID is read.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from populace_dynamics.ss.params import load_ssa_parameters
from populace_dynamics.track_b import reconstructed


def _invented_parameters(site: Path) -> None:
    """Only the base-year index is fixed by the unchanged loader's guard."""
    ssa = site / "policyengine_us/parameters/gov/ssa"
    retirement = "social_security/retirement_age_adjustment"
    documents = {
        # The loader itself requires this literal at ss/params.py:336-342.
        "nawi.yaml": {"values": {"1977-01-01": 9779.44}},
        "social_security/wage_base.yaml": {"values": {"2014-01-01": 123456.0}},
        "social_security/pia/formula_factors.yaml": {
            "brackets": [
                {"rate": {"2014-01-01": rate}, "threshold": {}}
                for rate in (0.8, 0.3, 0.1)
            ]
        },
        "social_security/full_retirement_age_by_birth_year.yaml": {
            "brackets": [
                {
                    "threshold": {"2014-01-01": 1900},
                    "amount": {"2014-01-01": 800},
                }
            ]
        },
        f"{retirement}/early_retirement/reduction_rates.yaml": {
            "brackets": [
                {"rate": {"2014-01-01": 0.005}},
                {
                    "rate": {"2014-01-01": 0.004},
                    "threshold": {"2014-01-01": 30},
                },
            ]
        },
        f"{retirement}/delayed_retirement/credit_rates.yaml": {
            "brackets": [
                {
                    "threshold": {"2014-01-01": 1900},
                    "amount": {"2014-01-01": 0.07},
                }
            ]
        },
        f"{retirement}/max_delayed_years.yaml": {"values": {"2014-01-01": 3}},
    }
    for relative, document in documents.items():
        destination = ssa / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        # JSON is valid YAML, so these exercise the unchanged YAML reader.
        destination.write_text(json.dumps(document))


def _git(root: Path, *arguments: str) -> str:
    return subprocess.run(
        [
            "git",
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "user.name=Invented",
            "-c",
            "user.email=invented@example.invalid",
            *arguments,
        ],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.mark.parametrize(
    "layout", ["default", "abbrev-7", "abbrev-12", "none"]
)
def test_loader_records_exactly_what_the_probe_reports(
    tmp_path, monkeypatch, layout
):
    for key in list(os.environ):
        if key.startswith("GIT_"):
            monkeypatch.delenv(key)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.resolve()))
    root = tmp_path / "anchor"
    root.mkdir()
    if layout != "none":
        _git(root, "init", "--quiet")
        (root / ".gitignore").write_text(".venv/\n")
        _git(root, "add", ".gitignore")
        _git(root, "commit", "--quiet", "-m", "invented anchor")
        if layout.startswith("abbrev-"):
            _git(root, "config", "core.abbrev", layout.split("-")[1])
    site = root / ".venv" / "lib" / "site-packages"
    _invented_parameters(site)
    if layout == "none":
        # The probe's GIT_CEILING_DIRECTORIES is reported, not hidden.
        monkeypatch.delenv("GIT_CEILING_DIRECTORIES")
        monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(root.resolve()))

    recorded = load_ssa_parameters(site).pe_us_revision
    probe = reconstructed.ssa_revision_anchor(site)

    assert probe["loader_revision"] == recorded
    if layout == "none":
        assert recorded == "unknown"
        assert probe["head"] is None
    else:
        head = _git(root, "rev-parse", "HEAD")
        assert probe["head"] == head
        assert head.startswith(recorded)
        if layout.startswith("abbrev-"):
            assert len(recorded) == int(layout.split("-")[1])
