"""Hold registration constants to the binding specification's JSON block."""

import hashlib
import json
import re

import pytest

from populace_dynamics.bridge import depletion_cut_population as core


def _block():
    text = core.SPECIFICATION_PATH.read_text()
    return json.loads(re.search(r"```json\n(.*?)\n```", text, re.S).group(1))


@pytest.mark.parametrize(
    "constant,key",
    [
        ("SPECIFICATION_NAME", "specification"),
        ("SPECIFICATION_VERSION", "version"),
        ("SPECIFICATION_STATUS", "status"),
        ("MAX_RULINGS", "decisions"),
        ("FRAME_PIN", "frame"),
        ("PR506_HEAD", "pr506_head"),
        ("PE_US_PIN", "policyengine_us"),
        ("SCENARIOS", "scenarios"),
        ("VARIANTS", "variants"),
        ("ROWS", "rows"),
        ("CELLS", "cells"),
        ("HEADLINE", "headline"),
        ("BOOTSTRAP", "uncertainty"),
        ("SMALL_CELL_N", "small_cell_n"),
        ("SMALL_CELL_N_COND", "small_cell_n_cond"),
        ("LABELS", "labels"),
    ],
)
def test_constants_equal_machine_readable_block(constant, key):
    assert getattr(core, constant) == _block()[key]


def test_specification_path_labels_tolerances_and_synthetic_split():
    assert core.SPECIFICATION_PATH.name == "pe_us_depletion_cut_population.md"
    assert core.FRAME_SHA256 == core.FRAME_PIN["sha256"]
    assert (
        core.TOLERANCE_DOLLARS
        == _block()["replacement"]["tolerance_dollars_per_year"]
        == 1.0
    )
    assert core.IDENTITY_TOLERANCE == core.BOUNDARY_TOLERANCE == 0.01
    assert len(core.LABELS) == 5
    assert core.SYNTHETIC_SPLIT["count"] == 5924
    assert list(core.SYNTHETIC_SPLIT["percent"]) == [
        "social_security_retirement",
        "social_security_survivors",
        "social_security_dependents",
        "social_security_disability",
    ]
    assert list(core.SYNTHETIC_SPLIT["percent"].values()) == [
        24.96,
        37.93,
        13.55,
        23.56,
    ]
    assert sum(core.SYNTHETIC_SPLIT["percent"].values()) == pytest.approx(100)


def test_named_differences_verbatim_after_source_line_wraps():
    text = core.SPECIFICATION_PATH.read_text()
    section = text.split(
        "## 12. Named differences, carried on every output\n\n"
    )[1].split("\n## 13.")[0]
    differences = [
        " ".join(part.split())
        for part in re.split(r"(?m)^(?=\d+\. )", section)
        if part.strip()
    ]
    assert core.NAMED_DIFFERENCES == differences
    assert len(differences) == 12


def test_status_version_and_ratification_hash_consistency():
    block = _block()
    if block["status"] == "ratified_frozen":
        assert block["version"] == "sa1-ratified-1"
        assert (
            core.SPECIFICATION_SHA256
            == hashlib.sha256(core.SPECIFICATION_PATH.read_bytes()).hexdigest()
        )
    else:
        assert block["status"] == "draft"
        assert block["version"].startswith("sa1-draft-")
        assert core.SPECIFICATION_SHA256 is None
