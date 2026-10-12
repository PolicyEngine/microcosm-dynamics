"""Pin Registration 19's one-shot outputs to the bytes fixed on issue #42.

The run (Modal call fc-01M48CG9VMP741AWN9A163FE9B, 2026-10-06) posted the
artifact's and sidecar's SHA-256 on issue #42 before any release decision;
these tests keep the committed copies identical to those bytes.
"""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "runs" / "pe_us_depletion_cut_population_v1.json"
SIDECAR = ROOT / "runs" / "pe_us_depletion_cut_population_v1.env.json"
DOCS = ROOT / "docs" / "analysis" / "pe_us_depletion_cut_population_20261001"
ARTIFACT_SHA256 = (
    "ef9366be4c867e5e63fc2bb011913c19dfaf08132a067905f1fbadc8f93d77d6"
)
SIDECAR_SHA256 = (
    "360a3b99b0426a7e461a84a8b9b027b41980a137449d6eaf0a92008fdf0d8536"
)
SPECIFICATION_SHA256 = (
    "4672d084aaf18d492eff30ca6961d511926086c8f73fc60368849b3589e11e1f"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test__given_committed_artifact__then_bytes_match_issue_42_record():
    assert _sha256(ARTIFACT) == ARTIFACT_SHA256


def test__given_committed_sidecar__then_bytes_match_issue_42_record():
    assert _sha256(SIDECAR) == SIDECAR_SHA256


def test__given_artifact__then_it_is_the_registered_real_run():
    document = json.loads(ARTIFACT.read_text())
    assert document["data_provenance"] == "registered_real"
    assert document["publication"] == {
        "computed_regardless": True,
        "release_held_for": "d905",
        "release_scope": "timing and wording only",
    }
    assert document["header"][0].startswith("FRAME-RELATIVE")
    assert SPECIFICATION_SHA256 in json.dumps(document["specification"])


def test__given_report_folder__then_report_and_chart_are_present():
    for name in ("report.md", "replacement.png", "replacement.svg"):
        assert (DOCS / name).is_file()
