"""The sample-household script's own checks, on INVENTED inputs.

No policyengine-us interpreter is started: the bridge's runner functions
are replaced with fakes, parameter files are written to a temporary
release directory, and decompositions are built from small invented
trees.  These pin the script's logic itself; the committed results are
pinned in ``test_pe_us_bridge_artifact.py``.
"""

from __future__ import annotations

import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

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


@pytest.mark.parametrize(
    "name", ["federal_refundable_credits", "state_refundable_credits"]
)
def test__given_a_refundable_credit_rising__then_writing_is_refused(name):
    """Round 2's L4: the check covers the refundable credits the design
    doc lists, not only benefits and income taxes."""

    row = _row()
    decomposition = row["decomposition"]
    categories = decomposition.by_category()
    # Move a dollar from SSI (still falling) to the credit, so the
    # identity and the Social Security check still hold.
    categories["ssi"]["change"] -= 100
    categories[name]["change"] += 100
    row["decomposition"] = row["with_health"] = _Categories(
        decomposition, categories
    )
    with pytest.raises(script.InvariantError, match=f"{name} rose"):
        script.check_invariants([row])


class _Categories:
    """A decomposition whose categories are replaced (one moved up)."""

    def __init__(self, decomposition, categories):
        self._decomposition = decomposition
        self._categories = categories
        self.components = decomposition.components
        self.net_change_cents = decomposition.net_change_cents
        self.reported_gap_cents = decomposition.reported_gap_cents

    def by_category(self):
        return self._categories


def test__wrong_way_categories__then_they_cover_benefits_taxes_and_credits():
    assert set(script.WRONG_WAY_CATEGORIES) == {
        "ssi",
        "snap",
        "csfp",
        "state_benefits",
        "federal_income_tax",
        "state_income_tax",
        "federal_refundable_credits",
        "state_refundable_credits",
    }
    assert set(script.WRONG_WAY_CATEGORIES) <= set(bridge.CATEGORY_ORDER)


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


# ---------------------------------------------------------------------------
# Money display
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("cents", "signed", "text"),
    [
        (188_650, True, "+1,887"),
        (-188_650, True, "−1,887"),
        (188_649, True, "+1,886"),
        (50, False, "1"),
        (150, False, "2"),
        (250, False, "3"),
        (49, True, "0"),
        (-49, True, "0"),
        (0, True, "0"),
        (-273_744, True, "−2,737"),
        (1_234_567_850, False, "12,345,679"),
    ],
)
def test__given_cents__then_half_dollars_round_up(cents, signed, text):
    """Round 2's rounding nit: C-MT's +1,886.50 shows as +1,887, where
    ``format`` rounds half to even (1,886)."""

    assert script._money(cents, signed=signed) == text


@given(st.integers(-(10**12), 10**12), st.booleans())
def test__given_any_cents__then_money_is_the_half_up_dollar(cents, signed):
    text = script._money(cents, signed=signed)
    dollars = int(text.lstrip("+−").replace(",", ""))
    # Half up in magnitude, from exact decimal arithmetic.
    assert dollars == int(
        (Decimal(abs(cents)) / 100).quantize(Decimal(1), ROUND_HALF_UP)
    )
    if dollars == 0:
        assert text == "0"
    elif cents < 0:
        assert text.startswith("−")
    else:
        assert text.startswith("+") is signed


@pytest.mark.parametrize(
    "cents", [1.5, True, float("nan"), float("inf"), "188650"]
)
def test__given_non_whole_cents__then_money_is_refused(cents):
    with pytest.raises(ValueError):
        script._money(cents)


# ---------------------------------------------------------------------------
# The Medicaid valuation
# ---------------------------------------------------------------------------
def _medicaid_release(tmp_path, enrollment_entry="2024-10-01"):
    totals = tmp_path / script.PARAMETER_PREFIX / script.MEDICAID_TOTALS
    totals.mkdir(parents=True)
    spending = {"CA": 124_063_730_563, "FL": 34_641_023_901, "MT": 1_000}
    enrollment = {
        "CA": (14_176_618, 13_431_928),
        "FL": (4_924_826, 3_765_231),
        "MT": (10, 8),
    }
    totals.joinpath("spending.yaml").write_text(
        "".join(
            f"{state}:\n  2022-01-01: 1\n  2023-01-01: {value}\n"
            for state, value in spending.items()
        )
    )
    totals.joinpath("enrollment.yaml").write_text(
        "".join(
            f"{state}:\n  2023-01-01: {same}\n  {enrollment_entry}: {later}\n"
            for state, (same, later) in enrollment.items()
        )
    )
    return tmp_path


def test__given_the_release_totals__then_both_ratios_are_computed(tmp_path):
    """Round 2's L2: Florida is $9,200 as the release computes it (2023
    spending over October 2024 enrollment) and $7,034 with 2023
    enrollment."""

    out = script.medicaid_per_enrollee(_medicaid_release(tmp_path))
    florida = out["FL"]
    assert florida["release"] == pytest.approx(9_200.24, abs=0.005)
    assert florida["same_year"] == pytest.approx(7_033.96, abs=0.005)
    assert florida["spending_entry"] == "2023-01-01"
    assert florida["enrollment_entry"] == "2024-10-01"
    assert out["MT"]["release"] == 125 and out["MT"]["same_year"] == 100


def test__given_other_enrollment_dates__then_the_valuation_is_refused(
    tmp_path,
):
    """The text names 2023 spending and October 2024 enrollment; a release
    with other entries cannot reuse it."""

    with pytest.raises(ValueError, match="not the entries"):
        script.medicaid_per_enrollee(
            _medicaid_release(tmp_path, enrollment_entry="2025-10-01")
        )


def test__valuation_text__then_it_is_exact_and_two_sided(tmp_path):
    per_enrollee = script.medicaid_per_enrollee(_medicaid_release(tmp_path))
    text = script.medicaid_valuation_text(per_enrollee)
    assert text.startswith(script.MEDICAID_VALUATION)
    assert (
        "2023 Medicaid spending divided by its October 2024 Medicaid and "
        "CHIP enrollment"
    ) in text
    assert "overstate or understate" in text
    assert "not a cash loss" in text
    assert "upper-end" not in text and "may understate" not in text
    # Florida first: the one case where the valuation moves a result.
    assert "it would be $7,034 in Florida (not $9,200), $8,751 in " in text


def test__given_memo_off_the_ratio__then_writing_is_refused(tmp_path):
    per_enrollee = script.medicaid_per_enrollee(_medicaid_release(tmp_path))
    row = _medicaid_row()
    row["memo"]["baseline"]["medicaid_cost"] = 9_200.24
    row["memo"]["reform"]["medicaid_cost"] = 0.0
    script.check_medicaid_memo([row], per_enrollee)
    row["memo"]["baseline"]["medicaid_cost"] = 7_033.96
    with pytest.raises(script.InvariantError, match="spending over"):
        script.check_medicaid_memo([row], per_enrollee)


def test__given_with_health_medicaid_off_the_ratio__then_it_is_refused(
    tmp_path,
):
    """The with-health column counts the ``medicaid_cost`` leaf; it is
    checked against the ratio as the memo is."""

    per_enrollee = script.medicaid_per_enrollee(_medicaid_release(tmp_path))
    tree = bridge.ComponentTree(
        "household_net_income",
        {
            "household_net_income": bridge.NET_INCOME_DEFINITION,
            "household_benefits": (
                ("social_security", 1),
                ("ssi", 1),
                ("medicaid_cost", 1),
            ),
        },
    )

    def values(medicaid):
        leaves = {**ZERO, "social_security": 8_916.0, "ssi": 0.0}
        leaves["medicaid_cost"] = medicaid
        leaves["household_benefits"] = 8_916.0 + medicaid
        leaves["household_net_income"] = 8_916.0 + medicaid
        return leaves

    row = _medicaid_row()
    row["memo"]["baseline"]["medicaid_cost"] = 0.0
    row["memo"]["reform"]["medicaid_cost"] = 0.0
    row["with_health"] = bridge.decompose(tree, values(9_200.24), values(0))
    script.check_medicaid_memo([row], per_enrollee)
    row["with_health"] = bridge.decompose(tree, values(7_033.96), values(0))
    with pytest.raises(script.InvariantError, match="with-health baseline"):
        script.check_medicaid_memo([row], per_enrollee)


# ---------------------------------------------------------------------------
# State evidence
# ---------------------------------------------------------------------------
def test__montana_evidence__then_income_and_its_reduction_are_separate():
    """Round 2's M1: the credit subtracts an income reduction (5 percent
    of net household income), not net household income itself."""

    evidence = " ".join(script.STATES["MT"]["evidence"])
    assert "less net household income" not in evidence
    assert "less an income reduction" in evidence
    assert "despite its name, this variable is the income reduction" in (
        evidence
    )
    assert "15-30-2337(8)" in evidence and "15-30-2340(4)" in evidence
