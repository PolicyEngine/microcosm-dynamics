"""The depletion-cut script's own checks, on INVENTED inputs.

No policyengine-us interpreter is started: the bridge's tracer is replaced
with a fake and decompositions are built from small invented trees.  The
Trustees Report checks read the committed Highlights page and its fetch
record (copied to a temporary directory when a test tampers with them).
These pin the script's logic; the committed results are pinned in
``test_pe_us_depletion_cut_artifact.py``.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import pe_us_depletion_cut_sample_households as script  # noqa: E402

from populace_dynamics.bridge import depletion_cut as dc  # noqa: E402
from populace_dynamics.bridge import policyengine_us as bridge  # noqa: E402

SOURCES = script.DEFAULT_DOCS_DIR / script.SOURCES_DIRNAME


# ---------------------------------------------------------------------------
# The Trustees Report and the statutes
# ---------------------------------------------------------------------------
def test__given_the_committed_sources__then_the_citation_is_complete():
    citation = script.trustees_citation(SOURCES, None)
    assert citation["quotes"]["OASI"]["payable_share"] == "0.78"
    assert citation["quotes"]["OASI"]["depletion_year"] == 2032
    assert citation["quotes"]["OASDI"]["payable_share"] == "0.83"
    assert citation["quotes"]["OASDI"]["depletion_year"] == 2034
    assert citation["key_results_table"]["OASI"] == {
        "year": 2032,
        "percent": 78,
    }
    page = citation["highlights"]
    assert page["url"] == (
        "https://www.ssa.gov/oact/TR/2026/II_A_highlights.html"
    )
    assert page["retrieved_utc"] == "2026-10-01T02:35:26+00:00"
    assert (
        page["sha256"]
        == hashlib.sha256(
            (SOURCES / script.HIGHLIGHTS_FILE).read_bytes()
        ).hexdigest()
    )
    assert page["file"] == (
        "docs/analysis/pe_us_depletion_cut_20261001/sources/"
        "II_A_highlights.html"
    )
    full = citation["full_report"]
    assert full["committed"] is False
    assert full["url"] == "https://www.ssa.gov/oact/TR/2026/tr2026.pdf"
    assert len(full["sha256"]) == 64
    assert full["quotes_found_on_text_page"] is None
    assert citation["primary"] == "OASI"
    assert citation["sensitivity"] == "OASDI"


def _copy_sources(tmp_path) -> Path:
    target = tmp_path / "sources"
    shutil.copytree(SOURCES, target)
    return target


def test__given_a_changed_page__then_the_citation_is_refused(tmp_path):
    sources = _copy_sources(tmp_path)
    page = sources / script.HIGHLIGHTS_FILE
    data = page.read_bytes()
    changed = data.replace(b'name="141435">78<', b'name="141435">79<')
    assert changed != data
    page.write_bytes(changed)
    with pytest.raises(script.InvariantError, match="fetch record"):
        script.trustees_citation(sources, None)


def test__given_a_table_that_disagrees__then_the_citation_is_refused(
    tmp_path,
):
    """A page whose Table II.A1 and sentence differ is refused, even when
    its fetch record is rewritten to match the changed bytes."""

    sources = _copy_sources(tmp_path)
    page = sources / script.HIGHLIGHTS_FILE
    data = page.read_bytes()
    # The table's OASI cell "Upon reserve depletion": 78.
    cell = b'name="141435">78<'
    assert data.count(cell) == 1
    changed = data.replace(cell, b'name="141435">77<')
    page.write_bytes(changed)
    record = json.loads((sources / script.FETCH_RECORD_FILE).read_text())
    for entry in record:
        if entry["file"] == script.HIGHLIGHTS_FILE:
            entry["sha256"] = hashlib.sha256(changed).hexdigest()
            entry["bytes"] = len(changed)
    (sources / script.FETCH_RECORD_FILE).write_text(json.dumps(record))
    with pytest.raises(script.InvariantError, match="Table II.A1"):
        script.trustees_citation(sources, None)


def test__given_another_full_report_text__then_it_is_refused(tmp_path):
    text = tmp_path / "tr2026.txt"
    text.write_text("not the report")
    with pytest.raises(script.InvariantError, match="recorded extraction"):
        script.trustees_citation(SOURCES, text)


def test__given_no_law_pages__then_the_statutes_are_recorded_unchecked():
    statutes = script.statute_sources(SOURCES, None)
    assert [s["citation"] for s in statutes] == [
        "42 USC 1381",
        "42 USC 1382e(a), (d)(1)",
        "42 USC 415(g)",
        "7 USC 2013(a)",
    ]
    for statute in statutes:
        assert statute["url"].startswith("https://www.law.cornell.edu/")
        assert statute["phrases_found"] is None
        assert statute["committed"] is False


def _law_pages(tmp_path, *, drop_phrase=None):
    """Invented statute pages holding every quoted phrase, and a record."""

    law = tmp_path / "law"
    law.mkdir()
    sources = _copy_sources(tmp_path)
    records = json.loads((sources / script.LAW_FETCH_RECORD_FILE).read_text())
    for record in records:
        _, phrases = script.STATUTE_QUOTES[record["file"]]
        body = " ".join(
            f"<p>{phrase}</p>" for phrase in phrases if phrase != drop_phrase
        )
        data = f"<html><body>{body}</body></html>".encode()
        (law / record["file"]).write_bytes(data)
        record["sha256"] = hashlib.sha256(data).hexdigest()
        record["bytes"] = len(data)
    (sources / script.LAW_FETCH_RECORD_FILE).write_text(json.dumps(records))
    return sources, law


def test__given_pages_with_every_phrase__then_the_statutes_check(tmp_path):
    sources, law = _law_pages(tmp_path)
    statutes = script.statute_sources(sources, law)
    assert all(s["phrases_found"] is True for s in statutes)


def test__given_a_page_without_its_phrase__then_it_is_refused(tmp_path):
    phrase = script.STATUTE_QUOTES["lii_42_usc_415.html"][1][1]
    sources, law = _law_pages(tmp_path, drop_phrase=phrase)
    with pytest.raises(script.InvariantError, match="415"):
        script.statute_sources(sources, law)


def test__given_a_page_off_its_hash__then_it_is_refused(tmp_path):
    sources, law = _law_pages(tmp_path)
    (law / "lii_42_usc_1381.html").write_text("changed")
    with pytest.raises(script.InvariantError, match="fetch record"):
        script.statute_sources(sources, law)


def test__statute_quotes__then_they_are_the_ones_the_module_quotes():
    """Every phrase the script checks appears in the module's own text."""

    quoted = dc.ROUNDING_RULE + " ".join(
        basis for _, basis in dc.LEAF_LEVELS.values()
    )
    checked = {
        "lii_42_usc_415.html": ["next lower multiple of $1"],
        "lii_42_usc_1381.html": ["sums sufficient to carry out"],
        "lii_42_usc_1382e.html": ["as such supplementary payments"],
        "lii_7_usc_2013.html": [
            "through the facilities of the Treasury of the United States",
            "fiscal year 2028",
        ],
    }
    for file, fragments in checked.items():
        _, phrases = script.STATUTE_QUOTES[file]
        for fragment in fragments:
            assert fragment in quoted
            assert any(fragment in phrase for phrase in phrases)


# ---------------------------------------------------------------------------
# Benefits and households
# ---------------------------------------------------------------------------
def test__given_cola_rates_with_float_noise__then_percents_are_tenths():
    percents = script.december_cola_percents(
        {2018: 0.027999999999999997, 2021: 0.059000000000000004, 2023: 0.032}
    )
    assert percents == {
        2018: Fraction(28, 10),
        2021: Fraction(59, 10),
        2023: Fraction(32, 10),
    }


def test__given_a_rate_off_the_tenth__then_it_is_refused():
    with pytest.raises(script.InvariantError, match="tenth"):
        script.december_cola_percents({2020: 0.0283})


BENEFITS = {
    "low_earner": {
        "monthly_benefit": 743,
        "medicare_quarters_of_coverage": 88,
    },
    "medium_earner": {
        "monthly_benefit": 2_351,
        "inputs": dict(script.MEDIUM_WORKER),
        "medicare_quarters_of_coverage": 140,
    },
    "couple": {"spouse_monthly": 1_175},
}
SHARES = {
    "baseline": Decimal(1),
    "oasi": Decimal("0.78"),
    "oasdi": Decimal("0.83"),
}


def _spec(key):
    return next(spec for spec in script.HOUSEHOLDS if spec["key"] == key)


def test__households__then_a_to_c_are_496s_and_d_e_are_new():
    assert [spec["key"] for spec in script.HOUSEHOLDS] == list("ABCDE")
    for spec, original in zip(
        script.HOUSEHOLDS[:3], script.minimum.HOUSEHOLDS, strict=True
    ):
        assert {k: v for k, v in spec.items() if k != "worker"} == original
    assert _spec("D")["taxable_private_pension_income"] == (
        _spec("C")["taxable_private_pension_income"]
    )
    assert _spec("E")["spouse"] is True


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        ("A", {"oasi": {"worker": 579}, "oasdi": {"worker": 616}}),
        ("D", {"oasi": {"worker": 1_833}, "oasdi": {"worker": 1_951}}),
        (
            "E",
            {
                "oasi": {"worker": 1_833, "spouse": 916},
                "oasdi": {"worker": 1_951, "spouse": 975},
            },
        ),
    ],
)
def test__given_a_household__then_each_benefit_is_cut_on_its_own(
    key, expected
):
    cuts = script.household_cuts(_spec(key), BENEFITS, SHARES)
    assert all(cut.monthly_cut == 0 for cut in cuts["baseline"].values())
    for scenario, payable in expected.items():
        assert {
            person: cut.monthly_payable
            for person, cut in cuts[scenario].items()
        } == payable


def test__given_the_couple__then_the_household_is_a_joint_unit():
    built = script.build_household(
        _spec("E"), "MT", {"worker": 21_996.0, "spouse": 10_992.0}, BENEFITS
    )
    situation = bridge.to_situation(built, 2026)
    people = situation["people"]
    assert set(people) == {"worker", "spouse"}
    assert people["worker"]["age"] == {"2026": 72}
    assert people["spouse"]["age"] == {"2026": 73}
    assert people["worker"]["social_security_retirement"] == {"2026": 21_996.0}
    assert people["spouse"]["social_security_dependents"] == {"2026": 10_992.0}
    assert people["spouse"]["social_security_retirement"] == {"2026": 0.0}
    assert people["worker"]["taxable_private_pension_income"] == {
        "2026": 42_000.0
    }
    assert "medicare_quarters_of_coverage" not in people["spouse"]
    for kind in ("tax_units", "spm_units", "marital_units", "families"):
        [unit] = situation[kind].values()
        assert sorted(unit["members"]) == ["spouse", "worker"]


def test__given_household_a__then_it_is_496s_household():
    built = script.build_household(
        _spec("A"), "FL", {"worker": 6_948.0}, BENEFITS
    )
    original = script.minimum.household(
        script.minimum.HOUSEHOLDS[0], "FL", 6_948.0, 88
    )
    assert built == original


# ---------------------------------------------------------------------------
# Invariants, offsets and the float32 guard
# ---------------------------------------------------------------------------
TREE = bridge.ComponentTree(
    "household_net_income",
    {
        "household_net_income": bridge.NET_INCOME_DEFINITION,
        "household_market_income": (("pension_income", 1),),
        "household_benefits": (
            ("social_security", 1),
            ("ssi", 1),
            ("wic", 1),
        ),
        "household_tax_before_refundable_credits": (
            ("income_tax_before_refundable_credits", 1),
        ),
    },
)


def _values(social_security, ssi, tax=0.0, wic=0.0, pension=0.0):
    leaves = {
        "household_refundable_tax_credits": 0.0,
        "household_health_costs": 0.0,
        "social_security": social_security,
        "ssi": ssi,
        "wic": wic,
        "pension_income": pension,
        "income_tax_before_refundable_credits": tax,
    }
    leaves["household_market_income"] = pension
    leaves["household_benefits"] = social_security + ssi + wic
    leaves["household_tax_before_refundable_credits"] = tax
    leaves["household_net_income"] = (
        social_security + ssi + wic + pension - tax
    )
    return leaves


def _cuts(share):
    return dc.cut_household({"worker": 743}, Decimal(share))


def _row(reform="oasi", reform_values=None, uncaused=()):
    share = "0.78" if reform == "oasi" else "0.83"
    cuts = _cuts(share)
    reform_ss = 12.0 * cuts["worker"].monthly_payable
    baseline = _values(8_916.0, 3_252.0)
    reformed = reform_values or _values(
        reform_ss, 3_252.0 + 8_916.0 - reform_ss
    )
    decomposition = bridge.decompose(TREE, baseline, reformed)
    guard = {"uncaused_changes": list(uncaused)}
    return {
        "household": "A",
        "label": "Household A",
        "state": "FL",
        "reform": reform,
        "fund": script.REFORMS[reform],
        "cuts": cuts,
        "baseline_social_security_annual": 8_916.0,
        "reform_social_security_annual": reform_ss,
        "decomposition": decomposition,
        "with_health": decomposition,
        "float32_guard": {"default": guard, "with_health": guard},
        "situations": {"baseline": {"people": {"worker": {}}}, "reform": {}},
        "overrides": {"default": {}, "with_health": {}},
        "case_ids": {
            variant: {
                "baseline": script._case_id("A", "FL", "baseline", variant),
                "reform": script._case_id("A", "FL", reform, variant),
            }
            for variant in script.VARIANTS
        },
        "run_values": {
            variant: {"baseline": baseline, "reform": reformed}
            for variant in script.VARIANTS
        },
    }


def _rows():
    return [_row("oasi"), _row("oasdi")]


def test__given_consistent_rows__then_the_invariants_pass():
    checks = script.check_invariants(_rows())
    assert any("levels of government" in check for check in checks)
    assert any("float32 guard" in check for check in checks)


def test__given_ssi_offsetting_the_cut__then_the_offset_is_complete():
    result = script.offsets(_row()["decomposition"])
    assert result["social_security_change_cents"] == -196_800
    assert result["net_change_cents"] == 0
    assert result["offset_share"] == 1
    assert result["offset_shares_by_level"]["federal"] == 1


def test__given_ssi_falling_with_social_security__then_it_is_refused():
    rows = _rows()
    rows[0] = _row(reform_values=_values(6_948.0, 3_000.0))
    with pytest.raises(script.InvariantError, match="ssi fell"):
        script.check_invariants(rows)


def test__given_a_tax_rising_with_the_cut__then_it_is_refused():
    rows = _rows()
    rows[0] = _row(reform_values=_values(6_948.0, 5_220.0, tax=10.0))
    with pytest.raises(script.InvariantError, match="federal_income_tax"):
        script.check_invariants(rows)


@pytest.mark.parametrize(
    "values",
    [
        _values(6_948.0, 5_220.0, wic=5.0),  # an unreviewed leaf moves
        _values(6_948.0, 5_220.0, pension=1.0),  # market income moves
    ],
)
def test__given_a_change_outside_the_groups__then_it_is_refused(values):
    rows = _rows()
    rows[0] = _row(reform_values=values)
    with pytest.raises(script.InvariantError, match="no payer group"):
        script.check_invariants(rows)


def test__given_social_security_off_the_cut__then_it_is_refused():
    rows = _rows()
    rows[0] = _row(reform_values=_values(6_960.0, 5_208.0))
    with pytest.raises(script.InvariantError, match="the cut is"):
        script.check_invariants(rows)


def test__given_a_deeper_cut_leaving_more__then_it_is_refused():
    rows = _rows()
    rows[0]["reform_social_security_annual"] = 9_000.0
    with pytest.raises(script.InvariantError, match="deeper cut"):
        script.check_invariants(rows)


def test__given_an_uncaused_change__then_writing_is_refused():
    rows = _rows()
    rows[1] = _row("oasdi", uncaused=[{"variable": "x@2026"}])
    with pytest.raises(script.InvariantError, match="float32 guard"):
        script.check_invariants(rows)


def test__invariant_checks__then_they_raise_not_assert():
    """``python -O`` strips ``assert``; the checks must still raise."""

    source = (ROOT / "scripts" / f"{script.OUTPUT_STEM}.py").read_text()
    for name in ("check_invariants", "check_medicaid_memo", "_health_pattern"):
        body = source.split(f"def {name}", 1)[1].split("\ndef ", 1)[0]
        assert "assert " not in body, name
    assert issubclass(script.InvariantError, AssertionError)


def _trace(value, children=(), is_input=False):
    return bridge.TraceNode(
        value=(value,), children=tuple(children), input=is_input
    )


def _traces(ssi_traced):
    """Traces of the invented rows: SSI read from Social Security."""

    out = {}
    for scenario, ss, ssi in (
        ("baseline", 8_916.0, 3_252.0),
        ("oasi", 6_948.0, ssi_traced),
        ("oasdi", 7_392.0, 3_252.0 + 8_916.0 - 7_392.0),
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
    rows = _rows()
    seen = {}

    def fake(cases, **kwargs):
        seen["cases"] = cases
        return _traces(5_220.0)

    monkeypatch.setattr(bridge, "trace_policyengine_us", fake)
    script.float32_guard(rows, None)
    guard = rows[0]["float32_guard"]["default"]
    assert guard["traced_leaves"] == ["social_security", "ssi"]
    assert guard["uncaused_changes"] == []
    # The shared baseline is traced once per variant, not once per cut.
    ids = [case_id for case_id, _, _ in seen["cases"]]
    assert len(ids) == len(set(ids)) == 6


def test__given_a_traced_value_off_the_run__then_writing_is_refused(
    monkeypatch,
):
    monkeypatch.setattr(
        bridge, "trace_policyengine_us", lambda *a, **k: _traces(5_300.0)
    )
    with pytest.raises(script.InvariantError, match="traced"):
        script.float32_guard(_rows(), None)


# ---------------------------------------------------------------------------
# Medicaid
# ---------------------------------------------------------------------------
def _medicaid_row(costs, people=1):
    row = _row()
    row["situations"]["baseline"]["people"] = {
        f"p{i}": {} for i in range(people)
    }
    row["memo"] = {
        "baseline": {"medicaid_cost": costs[0]},
        "reform": {"medicaid_cost": costs[1]},
    }
    return row


@pytest.mark.parametrize(
    ("costs", "people"),
    [((0.0, 9_200.2), 1), ((18_400.4, 9_200.1), 2), ((0.0, 0.0), 1)],
)
def test__given_whole_enrollees__then_the_medicaid_memo_passes(costs, people):
    per_enrollee = {"FL": {"release": 9_200.2}}
    script.check_medicaid_memo([_medicaid_row(costs, people)], per_enrollee)


@pytest.mark.parametrize(
    ("costs", "people"),
    [((0.0, 9_000.0), 1), ((18_400.4, 0.0), 1), ((0.0, 13_800.3), 2)],
)
def test__given_a_memo_off_the_ratio__then_it_is_refused(costs, people):
    per_enrollee = {"FL": {"release": 9_200.2}}
    with pytest.raises(script.InvariantError, match="whole number"):
        script.check_medicaid_memo(
            [_medicaid_row(costs, people)], per_enrollee
        )


def _health_row(
    *, eligible=(0.0, 1.0), extra_leaf=False, income_before=15_000.0
):
    row = _row()
    tree = bridge.ComponentTree(
        "household_net_income",
        {
            **TREE.children,
            "household_benefits": (
                *TREE.children["household_benefits"],
                ("household_health_benefits", 1),
            ),
            "household_health_benefits": (
                ("medicaid_cost", 1),
                *((("chip", 1),) if extra_leaf else ()),
            ),
        },
    )

    def with_health(values, medicaid, chip=0.0):
        values = dict(values)
        values["medicaid_cost"] = medicaid
        values["chip"] = chip
        values["household_health_benefits"] = medicaid + chip
        values["household_benefits"] += medicaid + chip
        values["household_net_income"] += medicaid + chip
        return values

    row["with_health"] = bridge.decompose(
        tree,
        with_health(row["run_values"]["default"]["baseline"], 0.0),
        with_health(
            row["run_values"]["default"]["reform"],
            9_200.0,
            5.0 if extra_leaf else 0.0,
        ),
    )
    income = "medicaid_optional_senior_or_disabled_countable_income"
    limit = "medicaid_optional_senior_or_disabled_income_limit"
    row["memo_with_health"] = {
        "baseline": {
            "is_medicaid_eligible": eligible[0],
            "ssi": 0.0,
            income: income_before,
            limit: 14_044.8,
        },
        "reform": {
            "is_medicaid_eligible": eligible[1],
            "ssi": 420.0,
            income: 12_000.0,
            limit: 14_044.8,
        },
    }
    return row


LIMITS = {"FL": 0.88}


def test__given_medicaid_starting__then_the_text_explains_it():
    out = script.health_explanations([_health_row()], LIMITS, {"FL": False})
    assert list(out) == ["A-FL-oasi"]
    text = out["A-FL-oasi"]
    assert "optional aged Medicaid pathway from $15,000 to $12,000" in text
    assert "$2,045 under its limit of $14,045 (88% of the poverty" in text
    assert "Medicaid eligibility begins" in text
    assert "valued at cost at $9,200 a year" in text
    assert "$0 to $420" in text


@pytest.mark.parametrize(
    "row",
    [
        pytest.param(lambda: _health_row(eligible=(1.0, 1.0)), id="no-gain"),
        pytest.param(lambda: _health_row(extra_leaf=True), id="chip"),
        pytest.param(
            lambda: _health_row(income_before=14_000.0), id="not-the-limit"
        ),
    ],
)
def test__given_another_health_difference__then_it_is_refused(row):
    with pytest.raises(script.InvariantError):
        script.health_explanations([row()], LIMITS, {"FL": False})


def test__given_no_health_difference__then_there_is_no_text():
    assert script.health_explanations(_rows(), LIMITS, {"FL": False}) == {}


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("share", "text"),
    [
        (Fraction(1), "100%"),
        (Fraction(1, 200), "1%"),
        (Fraction(1, 201), "0%"),
        (Fraction(-1, 200), "−1%"),
        (Fraction(1271, 2000), "64%"),
        (None, "n/a"),
    ],
)
def test__given_a_share__then_the_percent_rounds_half_up(share, text):
    assert script.percent_text(share) == text


@settings(deadline=None)
@given(
    numerator=st.integers(min_value=-(10**7), max_value=10**7),
    denominator=st.integers(min_value=1, max_value=10**7),
)
def test__given_any_share__then_the_percent_is_the_half_up_whole(
    numerator, denominator
):
    share = Fraction(numerator, denominator)
    magnitude = abs(share) * 100
    expected = (magnitude + Fraction(1, 2)).__floor__()
    text = script.percent_text(share)
    if expected == 0:
        assert text == "0%"
    else:
        assert text == ("−" if share < 0 else "") + f"{expected}%"


def test__law_year_note__then_it_says_2026_law_and_not_a_projection():
    note = script.LAW_YEAR_NOTE
    assert "2026" in note and "would not happen in 2026" in note
    assert "not a projection" in note
    assert script.ILLUSTRATIVE_LABEL == (
        "ILLUSTRATIVE HOUSEHOLDS, NOT SURVEY DATA"
    )


# ---------------------------------------------------------------------------
# Review round 1: union tracing, groupings, QI, ticks, the write path
# ---------------------------------------------------------------------------
def test__given_cuts_changing_different_leaves__then_baselines_trace_both():
    """The shared baseline is traced for every leaf any comparison moves."""

    rows = _rows()
    oasdi = _values(7_392.0, 3_252.0 + 8_916.0 - 7_392.0 - 10.0, wic=10.0)
    rows[1] = _row("oasdi", reform_values=oasdi)
    cases, _ = script.trace_cases(rows)
    traced = {case_id: leaves for case_id, _, leaves in cases}
    baseline = script._case_id("A", "FL", "baseline", "default")
    assert traced[baseline] == ["social_security", "ssi", "wic"]
    assert traced[script._case_id("A", "FL", "oasi", "default")] == [
        "social_security",
        "ssi",
    ]


def test__given_a_leaf_in_the_wrong_level__then_it_is_refused(monkeypatch):
    """The leaf-name mapping is checked against the tree's categories."""

    levels = dict(dc.LEAF_LEVELS)
    levels["ssi"] = ("state", "deliberately wrong")
    monkeypatch.setattr(dc, "LEAF_LEVELS", levels)
    with pytest.raises(script.InvariantError, match="level is not"):
        script.check_invariants(_rows())


def _msp_row(federal):
    row = _row()
    tree = bridge.ComponentTree(
        "household_net_income",
        {
            **TREE.children,
            "household_benefits": (
                *TREE.children["household_benefits"],
                ("household_health_benefits", 1),
            ),
            "household_health_benefits": (("msp_cost", 1),),
        },
    )

    def with_msp(values, msp):
        values = dict(values)
        values["msp_cost"] = msp
        values["household_health_benefits"] = msp
        values["household_benefits"] += msp
        values["household_net_income"] += msp
        return values

    row["with_health"] = bridge.decompose(
        tree,
        with_msp(row["run_values"]["default"]["baseline"], 0.0),
        with_msp(row["run_values"]["default"]["reform"], 2_000.0),
    )
    row["memo_with_health"] = {
        "baseline": {"msp_cost": 0.0, "msp_federal_cost": 0.0},
        "reform": {"msp_cost": 2_000.0, "msp_federal_cost": federal},
    }
    return row


def test__given_a_joint_msp_value__then_it_passes():
    script._check_msp_joint(_msp_row(1_229.0))


def test__given_an_all_federal_msp_value__then_it_is_refused():
    with pytest.raises(script.InvariantError, match="QI"):
        script._check_msp_joint(_msp_row(2_000.0))


@pytest.mark.parametrize(
    ("value", "text"),
    [
        (0.0, "$0"),
        (2_000.0, "$2k"),
        (-12_000.0, "−$12k"),
        (1_500.0, "$1.5k"),
        (500.0, "$500"),
        (-200.0, "−$200"),
    ],
)
def test__given_a_tick__then_its_label_is_exact(value, text):
    assert script.tick_text(value) == text


def test__given_invented_rows__then_every_artifact_is_written(tmp_path):
    """A smoke test of the write path on INVENTED rows (no PE-US)."""

    rows = _rows()
    for row in rows:
        row["float32_guard"] = {
            variant: {
                "traced_leaves": ["social_security", "ssi"],
                "traced_nodes": 3,
                "small_changes": [],
                "uncaused_changes": [],
            }
            for variant in script.VARIANTS
        }
        row["memo"] = {"baseline": {}, "reform": {}}
        row["memo_with_health"] = {"baseline": {}, "reform": {}}
        row["situations"] = {
            "baseline": {"people": {"worker": {}}},
            "reform": {"people": {"worker": {}}},
        }
    trustees = script.trustees_citation(SOURCES, None)
    document = {
        "label": script.ILLUSTRATIVE_LABEL,
        "trustees_report": trustees,
        "provenance": {
            "microcosm_dynamics": {"commit": "0" * 40},
            "policyengine_us": {
                "release": script.minimum.PE_US_RELEASE,
                "installed": {"policyengine_core_version": "3.32.11"},
                "record_check": {"files_checked": 17_551},
                "parameter_updates": [],
            },
        },
        "medicaid_valuation": {"text": "Medicaid valuation (invented)."},
        "health_explanations": {},
        "float32_guard": script._guard_summary(rows),
        "caveats": [script.LAW_YEAR_NOTE],
    }
    report = script.markdown(rows, document)
    assert script.ILLUSTRATIVE_LABEL in report
    assert "| A | FL | −1,968 | 0 | 100% | 100% | 0% |" in report
    json.dumps([script._serialize_row(row) for row in rows])
    paths = script.draw_household_chart(
        rows, script.HOUSEHOLDS[0], document, tmp_path / "a"
    )
    paths += script.draw_summary_chart(rows, document, tmp_path / "s")
    for path in paths:
        data = path.read_bytes()
        assert script.ILLUSTRATIVE_LABEL.encode() in data, path


# ---------------------------------------------------------------------------
# Review round 2
# ---------------------------------------------------------------------------
def test__given_ssi_starting_where_it_confers_medicaid__then_both_routes():
    out = script.health_explanations([_health_row()], LIMITS, {"FL": True})
    text = out["A-FL-oasi"]
    assert "SSI goes from $0 to $420 a year" in text
    assert "SSI receipt is itself a Medicaid pathway" in text
    assert "either route qualifies" in text


def test__given_a_couple__then_the_health_text_is_refused():
    """Memo values are household sums; a couple's limit would double."""

    row = _health_row()
    row["situations"]["baseline"]["people"] = {"worker": {}, "spouse": {}}
    with pytest.raises(script.InvariantError, match="does not describe"):
        script.health_explanations([row], LIMITS, {"FL": False})


def test__given_docs_outside_the_repository__then_they_are_refused(
    tmp_path,
):
    with pytest.raises(ValueError, match="outside the repository"):
        script._docs_relative(tmp_path / "docs")
    assert script._docs_relative(script.DEFAULT_DOCS_DIR) == (
        "docs/analysis/pe_us_depletion_cut_20261001"
    )


def test__given_496s_release_caveats__then_the_snap_one_is_directionless(
    monkeypatch,
):
    original = [
        "SNAP fiscal 2027 amounts.",
        "In policyengine-us 2.18.0 SNAP counts California's SSI supplement "
        "as unearned income (...), so losing the supplement lowers the "
        "income SNAP counts, and SNAP falls by less.",
        "Take-up is the default.",
    ]
    monkeypatch.setattr(
        script.minimum, "_release_caveats", lambda root: list(original)
    )
    out = script.release_caveats(Path("."))
    assert out[0] == original[0] and out[2] == original[2]
    assert "losing" not in out[1]
    assert "unearned_spm_unit.yaml:13" in out[1]


def test__given_other_release_caveats__then_adapting_them_is_refused(
    monkeypatch,
):
    monkeypatch.setattr(
        script.minimum, "_release_caveats", lambda root: ["a", "b", "c"]
    )
    with pytest.raises(script.InvariantError, match="release caveats"):
        script.release_caveats(Path("."))


def test__given_a_joint_change_without_health__then_it_is_refused():
    rows = _rows()
    for row in rows:
        row["decomposition"] = row["with_health"] = _joint_decomposition()
    with pytest.raises(script.InvariantError):
        script.check_invariants(rows)


def _joint_decomposition():
    tree = bridge.ComponentTree(
        "household_net_income",
        {
            **TREE.children,
            "household_benefits": (
                *TREE.children["household_benefits"],
                ("medicaid_cost", 1),
            ),
        },
    )
    baseline = _values(8_916.0, 3_252.0)
    reform = _values(6_948.0, 5_220.0)
    for values, medicaid in ((baseline, 0.0), (reform, 100.0)):
        values["medicaid_cost"] = medicaid
        values["household_benefits"] += medicaid
        values["household_net_income"] += medicaid
    return bridge.decompose(tree, baseline, reform)
