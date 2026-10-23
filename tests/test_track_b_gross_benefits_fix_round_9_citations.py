"""G round 9: the disabled-widow instruction retains its captured location.

Verification class: statutory conformance of source citations only. No real
data, population, behavioral or forecast claim is admitted. The .301B.1.e
instruction and separate .310B.3 recalculation rule remain distinct.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

import pytest

from tests.track_b_gross_benefit_support import SOURCES, manifest

ROOT = Path(__file__).resolve().parents[1]


def _captured_section(source_id, anchor, next_anchor):
    entry = next(s for s in manifest()["sources"] if s["id"] == source_id)
    capture = (SOURCES / entry["file"]).read_text()
    section = capture.split(f'<a name="{anchor}">', 1)[1].split(
        f'<a name="{next_anchor}">', 1
    )[0]
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", section)))


def test_disabled_widow_instruction_is_under_captured_b1e_and_b3_is_separate():
    section = _captured_section("poms_rs_00615_301", "b1e", "b2")
    assert "e. Additional reduction for months prior to age 60" in section
    assert (
        "all disabled widow(er)s under age 60 receive .715 of the full "
        "unreduced WIB for 1/84 and later."
    ) in section
    recalculation = _captured_section("poms_rs_00615_310", "b3", "c")
    assert "3. 1/84 DWB Recalculation" in recalculation
    assert (
        "Beneficiaries who were entitled to DWB prior to 1/84 had their "
        "benefits recalculated effective 1/84 as if the reduction for "
        "the period prior to age 60 did not exist."
    ) in recalculation


@pytest.mark.parametrize(
    "relative_path",
    (
        "docs/design/track_b_g_gross_benefits.md",
        "src/populace_dynamics/track_b/gross_benefits.py",
    ),
)
def test_disabled_widow_citation_matches_capture_in_design_and_module(
    relative_path,
):
    text = (ROOT / relative_path).read_text()
    assert "RS 00615.301B.3" not in text
    assert "RS 00615.301B.1.e" in text
    assert "RS 00615.310B.1/B.3" in text
