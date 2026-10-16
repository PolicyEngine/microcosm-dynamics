"""Invented linked-record regressions for the #494 static source audit.

Verification class: statutory conformance and static source audit. These
cases admit code-path reachability only, with no population, behavioral,
forecast, or affected-person claim. All loaders supply invented frames.
"""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.ss import benefits
from populace_dynamics.ss.statutory_delayed_credit import delayed_credit
from tests.track_b_gross_benefit_support import ssa_params

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def r7():
    """Load actual R7 math without unrelated publication helper imports."""
    with pytest.MonkeyPatch.context() as patch:
        for module_name, helper_name in (
            ("build_downstream_relevance", "_weighted_mean"),
            ("reform_delta_diagnostic", "_summary"),
        ):
            stub = ModuleType(module_name)
            setattr(stub, helper_name, lambda *args, **kwargs: None)
            patch.setitem(sys.modules, module_name, stub)
        patch.setattr(sys, "path", list(sys.path))
        spec = importlib.util.spec_from_file_location(
            "track_b_494_r7_reachability",
            ROOT / "scripts" / "replication_r7_sharing.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module


def _invented_study(r7, patch, deceased_birth):
    # The scored survivor must already be widowed at age-62 eligibility.
    # This preserves the reviewer's 1945 survivor for the 1937/1916 cases.
    survivor_birth = max(1945, deceased_birth + 8)
    panel = pd.DataFrame(
        [
            {
                "person_id": pid,
                "period": birth + age,
                "age": age,
                "earnings": 1000.0,
                "weight": 1.0,
            }
            for pid, birth in ((1, survivor_birth), (2, deceased_birth))
            for age in range(max(22, 1951 - birth), 62)
        ]
    )
    marriage = pd.DataFrame(
        [
            {
                "person_id": 1,
                "sex": "female",
                "last_known_status": "widowed",
            },
            {
                "person_id": 2,
                "sex": "male",
                "last_known_status": "married",
            },
        ]
    )
    episodes = pd.DataFrame(
        [
            {
                "person_id": pid,
                "spouse_person_id": spouse,
                "start_year": 1967,
                "episode_end_year": deceased_birth + 70,
                "how_ended": how,
            }
            for pid, spouse, how in (
                (1, 2, "widowhood"),
                (2, 1, "death"),
            )
        ]
    )
    patch.setattr(r7, "family_earnings_panel", lambda: panel)
    patch.setattr(r7, "marriage_history", lambda: marriage)
    patch.setattr(r7, "marriage_episodes", lambda raw: episodes)
    return r7.StudyData(ssa_params(wage_base={1900: 1_000_000.0}))


def _payment(r7, study, path):
    if path == "baseline":
        return r7.baseline_benefit(study, 1, "female", "widowed", study.pia[1])
    return r7.reformed_benefit(study, 1, "female", "widowed", "1a")


@pytest.mark.parametrize("deceased_birth", [1937, 1916])
@pytest.mark.parametrize("path", ["baseline", "1a"])
def test_older_linked_deceased_outside_career_frame_reaches_credit_factor(
    r7, monkeypatch, deceased_birth, path
):
    study = _invented_study(r7, monkeypatch, deceased_birth)
    assert study.careers == {1}
    assert set(study.pia) == {1, 2}
    assert study.both_spouse_covered(1)
    assert study.status_at_eligibility(1) == "widowed"
    assert study.pia == {
        1: 225.0,
        2: 259.2 if deceased_birth == 1937 else 116.1,
    }
    assert r7._claim_pmf(study, 2, "male")[70] > 0

    evaluations = []
    legacy_credit = benefits.delayed_credit

    def record_credit(months_late, birth_year, params):
        evaluations.append((months_late, birth_year))
        return legacy_credit(months_late, birth_year, params)

    monkeypatch.setattr(benefits, "delayed_credit", record_credit)
    legacy = _payment(r7, study, path)
    assert (60, deceased_birth) in evaluations
    if path == "baseline":
        expected = (
            218.41231551242228 if deceased_birth == 1937 else 187.2862853209459
        )
        assert legacy == pytest.approx(expected, abs=1e-12, rel=0)

    monkeypatch.setattr(benefits, "delayed_credit", delayed_credit)
    if deceased_birth < 1917:
        with pytest.raises(ValueError, match=r"402\(w\)\(6\)\(A\)"):
            _payment(r7, study, path)
    else:
        statutory = _payment(r7, study, path)
        assert statutory > legacy
        if path == "baseline":
            assert statutory == pytest.approx(
                218.6072054833109, abs=1e-12, rel=0
            )


def test_linked_1937_age_70_case_preserves_the_65_dollar_difference(
    r7, monkeypatch
):
    study = _invented_study(r7, monkeypatch, 1937)
    # First establish actual loader admission; these simpler invented PIAs
    # then isolate the source-derived 60 versus 48 month window difference.
    assert study.careers == {1} and set(study.pia) == {1, 2}
    study.pia = {1: 1.0, 2: 1000.0}
    monkeypatch.setattr(r7, "_claim_pmf", lambda *args: {70: 1.0})
    assert _payment(r7, study, "baseline") == 1260.0
    monkeypatch.setattr(benefits, "delayed_credit", delayed_credit)
    assert _payment(r7, study, "baseline") == 1325.0


@settings(deadline=None)
@given(
    deceased_birth=st.integers(1913, 1942),
    path=st.sampled_from(["baseline", "1a"]),
)
def test_linked_pia_supply_and_survivor_factor_do_not_inherit_career_cutoff(
    r7, deceased_birth, path
):
    with pytest.MonkeyPatch.context() as patch:
        study = _invented_study(r7, patch, deceased_birth)
        assert study.careers == {1}
        assert set(study.pia) == {1, 2}
        assert study.both_spouse_covered(1)
        assert study.status_at_eligibility(1) == "widowed"
        evaluations = []
        legacy_credit = benefits.delayed_credit

        def record_credit(months_late, birth_year, params):
            evaluations.append((months_late, birth_year))
            return legacy_credit(months_late, birth_year, params)

        patch.setattr(benefits, "delayed_credit", record_credit)
        assert _payment(r7, study, path) > 0
        assert (
            840 - study.params.fra_months(deceased_birth),
            deceased_birth,
        ) in (evaluations)


def test_executed_linked_counterexample_is_in_the_reachable_audit(r7):
    with pytest.MonkeyPatch.context() as patch:
        study = _invented_study(r7, patch, 1937)
        legacy = _payment(r7, study, "baseline")
        patch.setattr(benefits, "delayed_credit", delayed_credit)
        assert _payment(r7, study, "baseline") > legacy

    erratum = (
        ROOT / "docs" / "errata" / "2026-10-11-delayed-credit-window.md"
    ).read_text()
    reachable = erratum.split(
        "## Registered results with reachable legacy undercredits", 1
    )[1].split("## Other call paths", 1)[0]
    assert "`runs/replication_r7_sharing_v1.json`" in reachable
    assert "`runs/replication_cost_ordering_v1.json`" in reachable
    assert "replication_r7_sharing.py:398" in reachable
    assert "replication_cost_ordering.py:587" in reachable
    r7_row = next(
        line
        for line in reachable.splitlines()
        if "`runs/replication_r7_sharing_v1.json`" in line
    )
    assert all(word in r7_row for word in ("linked", "baseline", "1a"))
    pre_1917 = erratum.split("## Births before 1917:", 1)[1].split(
        "## Largest possible", 1
    )[0]
    diagnostic = erratum.split("## Retained artifacts", 1)[1].split(
        "## Not in scope", 1
    )[0]
    for section in (pre_1917, diagnostic):
        assert all(word in section for word in ("R7", "cost ordering", "1a"))
    design = (
        ROOT / "docs" / "design" / "track_b_494_delayed_credit.md"
    ).read_text()
    assert "R7" in design and "cost ordering" in design
