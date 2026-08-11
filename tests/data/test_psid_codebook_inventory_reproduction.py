"""On-machine reproduction of all six locator-pinned codebook eras."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from populace_dynamics.data import psid_questionnaire_inventory as inventory

PSID_ROOT = Path("~/PolicyEngine/psid-data").expanduser()
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
ERA_DIRECTORY = (
    REPOSITORY_ROOT / "data" / "external" / "psid_codebook_field_evidence"
)
ADJUDICATION_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "external"
    / "psid_codebook_inventory_adjudication_v1.json"
)


@pytest.mark.skipif(
    not (PSID_ROOT / "family" / "2023").is_dir()
    or shutil.which("pdftotext") is None,
    reason="PSID family codebooks or pdftotext not staged",
)
def test_all_codebook_eras_and_adjudication_reproduce_byte_for_byte():
    artifacts = []
    for era_id, _ in inventory.CODEBOOK_ERA_SPECS:
        artifact = inventory.build_codebook_era_evidence(
            era_id,
            PSID_ROOT,
        )
        artifacts.append(artifact)
        assert (
            inventory.render_codebook_era_evidence(artifact)
            == (ERA_DIRECTORY / f"{era_id}_v1.json").read_bytes()
        )
    adjudication = inventory.build_codebook_inventory_adjudication(artifacts)
    assert (
        inventory.render_codebook_inventory_adjudication(adjudication)
        == ADJUDICATION_PATH.read_bytes()
    )
