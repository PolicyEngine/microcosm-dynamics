"""The sample-household script's own checks, on INVENTED inputs.

No policyengine-us interpreter is started: the bridge's runner functions
are replaced with fakes, parameter files are written to a temporary
release directory, and decompositions are built from small invented
trees.  These pin the script's logic itself; the committed results are
pinned in ``test_pe_us_bridge_artifact.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import pe_us_minimum_benefit_sample_households as script  # noqa: E402

from populace_dynamics.bridge import policyengine_us as bridge  # noqa: E402

UPDATE = script.PARAMETER_UPDATES[0]
HEALTH = "gov.simulation.include_health_benefits_in_net_income"


# ---------------------------------------------------------------------------
# Parameter updates
# ---------------------------------------------------------------------------
def _release(tmp_path, values: str) -> Path:
    path = tmp_path / UPDATE["file"]
    path.parent.mkdir(parents=True)
    path.write_text(f"values:\n{values}")
    return tmp_path


def test__given_no_entry_for_the_year__then_the_update_applies(tmp_path):
    root = _release(tmp_path, "  1991-01-01: 630\n  2025-01-01: 1_206.94\n")
    [applied] = script.parameter_updates(root)
    assert applied["value"] == 1_233.94
    assert applied["installed_value"] == 1_206.94
    assert applied["installed_value_dated"] == "2025-01-01"
    assert len(applied["file_sha256"]) == 64


def test__given_the_published_entry__then_the_update_is_dropped(tmp_path):
    root = _release(
        tmp_path, "  2025-01-01: 1_206.94\n  2026-01-01: 1_233.94\n"
    )
    assert script.parameter_updates(root) == []


def test__given_a_different_entry__then_the_script_refuses(tmp_path):
    root = _release(tmp_path, "  2025-01-01: 1_206.94\n  2026-01-01: 1_250\n")
    with pytest.raises(ValueError, match="not the published"):
        script.parameter_updates(root)


@pytest.mark.parametrize(
    ("state", "variant", "expected"),
    [
        ("CA", "default", {UPDATE["parameter"]: 1_233.94}),
        ("CA", "with_health", {UPDATE["parameter"]: 1_233.94, HEALTH: True}),
        ("FL", "default", {}),
        ("MT", "with_health", {HEALTH: True}),
    ],
)
def test__given_state_and_variant__then_overrides_are_the_right_ones(
    state, variant, expected
):
    assert script._overrides_for(state, variant, [UPDATE]) == expected


@pytest.mark.parametrize(
    ("values", "on", "expected"),
    [
        ({"2018-01-01": 0.88}, "2026-01-01", 0.88),
        ({"2025-10-01": 298, "2026-10-01": 306}, "2026-10-01", 306),
        ({"2025-10-01": 298, "2026-10-01": 306}, "2026-09-30", 298),
    ],
)
def test__given_dated_values__then_the_one_in_force_is_read(
    values, on, expected
):
    assert script._dated_value(values, on) == expected


def test__given_no_value_in_force__then_reading_is_refused():
    with pytest.raises(ValueError, match="no value in force"):
        script._dated_value({"2027-01-01": 1}, "2026-01-01")


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "document",
    [
        {"path": "/abs/file.json"},
        {"nested": [{"python": "~/.venvs/x/bin/python"}]},
        {"text": "see /Users/someone/file"},
    ],
)
def test__given_a_local_path__then_writing_is_refused(document):
    with pytest.raises(ValueError, match="local path"):
        script._no_absolute_paths(document)


def test__given_relative_paths__then_writing_is_allowed():
    script._no_absolute_paths(
        {"a": "docs/analysis/x.md", "b": ["policyengine_us/p.yaml"]}
    )


# ---------------------------------------------------------------------------
# The pinned release
# ---------------------------------------------------------------------------
def _fake_installation(version="2.18.0"):
    return bridge.PolicyEngineUSInstallation(
        python="python",
        python_version="3.13.9",
        package_dir="site/policyengine_us",
        version=version,
        core_version="3.32.11",
        location="site",
        record_path="site/RECORD",
        record_sha256="0" * 64,
        direct_url=None,
        installer="uv",
    )


def _record(**overrides):
    record = {
        "prefix": "policyengine_us/",
        "files_checked": 17_551,
        "mismatched": [],
        "missing": [],
        "extra": [],
        "package_record_digest": script.PE_US_RELEASE["package_record_digest"],
        "package_record_lines": 17_551,
    }
    record.update(overrides)
    return record


@pytest.fixture
def fake_release(monkeypatch):
    state = {"installation": _fake_installation(), "record": _record()}
    monkeypatch.setattr(
        bridge, "inspect_installation", lambda python: state["installation"]
    )
    monkeypatch.setattr(
        bridge, "verify_record", lambda installation: state["record"]
    )
    return state


def test__given_the_pinned_release__then_provenance_is_recorded(
    fake_release,
):
    installation, provenance = script.pinned_release(None)
    assert installation.version == "2.18.0"
    assert provenance["release"] == script.PE_US_RELEASE
    assert provenance["source_check"]["published"] is True
    assert provenance["record_check"]["extra"] == 0


@pytest.mark.parametrize(
    ("change", "match"),
    [
        ({"installation": _fake_installation("2.17.3")}, "version 2.17.3"),
        ({"record": _record(mismatched=["policyengine_us/a.py"])}, "differ"),
        ({"record": _record(extra=["policyengine_us/p/x.yaml"])}, "not in"),
        ({"record": _record(package_record_digest="0" * 64)}, "RECORD"),
    ],
)
def test__given_anything_but_the_pinned_release__then_the_script_refuses(
    fake_release, change, match
):
    fake_release.update(change)
    with pytest.raises(ValueError, match=match):
        script.pinned_release(None)


# ---------------------------------------------------------------------------
# Invariants, the float32 guard and the Medicaid text
# ---------------------------------------------------------------------------
TREE = bridge.ComponentTree(
    "household_net_income",
    {
        "household_net_income": bridge.NET_INCOME_DEFINITION,
        "household_benefits": (("social_security", 1), ("ssi", 1)),
    },
)
ZERO = {
    "household_market_income": 0.0,
    "household_refundable_tax_credits": 0.0,
    "household_tax_before_refundable_credits": 0.0,
    "household_health_costs": 0.0,
}


def _values(social_security, ssi):
    leaves = {**ZERO, "social_security": social_security, "ssi": ssi}
    leaves["household_benefits"] = social_security + ssi
    leaves["household_net_income"] = social_security + ssi
    return leaves


def _row(baseline_ssi=3_252.0, reform_ssi=1_200.0, uncaused=()):
    baseline = _values(8_916.0, baseline_ssi)
    reform = _values(10_968.0, reform_ssi)
    decomposition = bridge.decompose(TREE, baseline, reform)
    guard = {"uncaused_changes": list(uncaused)}
    return {
        "household": "A",
        "state": "FL",
        "baseline_social_security_annual": 8_916.0,
        "reform_social_security_annual": 10_968.0,
        "decomposition": decomposition,
        "with_health": decomposition,
        "float32_guard": {"default": guard, "with_health": guard},
        "situations": {"baseline": {}, "reform": {}},
        "overrides": {"default": {}, "with_health": {}},
        "run_values": {
            variant: {"baseline": baseline, "reform": reform}
            for variant in script.VARIANTS
        },
    }


def test__given_a_consistent_row__then_the_invariants_pass():
    checks = script.check_invariants([_row()])
    assert any("float32 guard" in check for check in checks)


def test__given_ssi_rising_with_social_security__then_writing_is_refused():
    with pytest.raises(script.InvariantError, match="ssi rose"):
        script.check_invariants([_row(baseline_ssi=0.0, reform_ssi=100.0)])


def test__given_an_uncaused_change__then_writing_is_refused():
    row = _row(uncaused=[{"variable": "ca_use_tax@2026"}])
    with pytest.raises(script.InvariantError, match="float32 guard"):
        script.check_invariants([row])


def test__invariant_error__then_it_is_raised_not_asserted():
    """``python -O`` strips ``assert``; the checks must still raise."""

    source = (ROOT / "scripts" / f"{script.OUTPUT_STEM}.py").read_text()
    body = source.split("def check_invariants", 1)[1].split("\ndef ", 1)[0]
    assert "assert " not in body


def _trace(value, children=(), is_input=False):
    return bridge.TraceNode(
        value=(value,), children=tuple(children), input=is_input
    )


def _traces(ssi_traced):
    """Traces of the invented row: SSI read from Social Security."""

    out = {}
    for scenario, ss, ssi in (
        ("baseline", 8_916.0, 3_252.0),
        ("reform", 10_968.0, ssi_traced),
    ):
        nodes = {
            "social_security@2026": _trace(ss, ["ssr@2026"]),
            "ssr@2026": _trace(ss, is_input=True),
            "ssi@2026": _trace(ssi, ["social_security@2026"]),
        }
        for variant in script.VARIANTS:
            out[script._case_id("A", "FL", scenario, variant)] = nodes
    return out


def test__given_traced_values_equal_to_the_run__then_the_guard_records_them(
    monkeypatch,
):
    row = _row()
    monkeypatch.setattr(
        bridge, "trace_policyengine_us", lambda *a, **k: _traces(1_200.0)
    )
    script.float32_guard([row], None)
    guard = row["float32_guard"]["default"]
    assert guard["traced_leaves"] == ["social_security", "ssi"]
    assert guard["uncaused_changes"] == []
    assert guard["small_changes"] == []


def test__given_a_traced_value_off_the_run__then_writing_is_refused(
    monkeypatch,
):
    """The traced-versus-untraced differential check."""

    monkeypatch.setattr(
        bridge, "trace_policyengine_us", lambda *a, **k: _traces(1_250.0)
    )
    with pytest.raises(script.InvariantError, match="traced"):
        script.float32_guard([_row()], None)


def _medicaid_row(*, eligible_after=0.0, msp_after=5_335.0, qmb=1.0):
    row = _row()
    # With health counted the change differs from the default one.
    row["with_health"] = bridge.decompose(
        TREE, _values(8_916.0, 3_252.0), _values(10_968.0, 0.0)
    )
    qmb_months = {name: qmb for name in script.QMB_MONTHS}
    income = "medicaid_optional_senior_or_disabled_countable_income"
    limit = "medicaid_optional_senior_or_disabled_income_limit"
    row["memo"] = {
        "baseline": {
            "is_medicaid_eligible": 1.0,
            income: 13_476.0,
            limit: 14_044.8,
            "msp_cost": 0.0,
            **qmb_months,
        },
        "reform": {
            "is_medicaid_eligible": eligible_after,
            income: 15_528.0,
            limit: 14_044.8,
            "msp_cost": msp_after,
            **qmb_months,
        },
    }
    return row


def test__given_medicaid_ending_at_the_limit__then_the_text_explains_it():
    out = script.medicaid_explanations([_medicaid_row()], {"FL": 0.88})
    assert list(out) == [("A", "FL")]
    text = out[("A", "FL")]
    assert "$13,476 to $15,528" in text and "88%" in text
    assert "QMB-eligible in every month of both runs" in text


def test__given_no_msp_in_the_reform__then_the_qmb_sentence_is_left_out():
    """Finding 9 of the code review: the sentence needs MSP to appear."""

    out = script.medicaid_explanations(
        [_medicaid_row(msp_after=0.0)], {"FL": 0.88}
    )
    assert "QMB" not in out[("A", "FL")]


def test__given_another_reason_for_the_difference__then_it_is_refused():
    with pytest.raises(script.InvariantError, match="does not describe"):
        script.medicaid_explanations(
            [_medicaid_row(eligible_after=1.0)], {"FL": 0.88}
        )
