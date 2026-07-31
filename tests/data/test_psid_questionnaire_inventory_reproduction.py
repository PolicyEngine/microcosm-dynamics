"""On-machine reproduction of the source-only PSID dictionary audit."""

from __future__ import annotations

from pathlib import Path

import pytest

from populace_dynamics.data import psid_questionnaire_inventory as inventory

PSID_ROOT = Path("~/PolicyEngine/psid-data").expanduser()
ARTIFACT_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "external"
    / "psid_questionnaire_dictionary_inventory_"
    "registration_required_v1.json"
)


@pytest.mark.skipif(
    not (PSID_ROOT / "family" / "2023").is_dir(),
    reason="PSID family dictionaries not staged",
)
def test_committed_dictionary_audit_reproduces_byte_for_byte():
    rebuilt = inventory.render_artifact(
        inventory.build_registration_required_audit(PSID_ROOT)
    )
    assert rebuilt == ARTIFACT_PATH.read_bytes()
