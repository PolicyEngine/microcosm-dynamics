"""Release identity: mismatched versions never reach the rules engine.

Wheel SHA-256s record installed artifacts; RECORD digests additionally bind
the installation inspected in the child to this certified installation.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

PIN_PATH = Path(__file__).with_name("pin.json")


def load_pin() -> dict:
    pin = json.loads(PIN_PATH.read_text())
    environment = json.loads(
        PIN_PATH.with_name("environment_wheels.json").read_text()
    )
    pin["environment_versions"] = {
        name: wheel["version"] for name, wheel in environment["wheels"].items()
    }
    return pin


def check_versions(actual: Mapping[str, str], pin: Mapping) -> None:
    """Refuse before importing a model if any certified version differs."""
    expected_versions = {
        **pin.get("environment_versions", {}),
        **pin["versions"],
    }
    for name, expected in expected_versions.items():
        if actual.get(name) != expected:
            raise ValueError(
                f"{name}: installed {actual.get(name)!r}, pinned {expected!r}"
            )
