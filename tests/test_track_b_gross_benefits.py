"""Track B milestone G: statutory worked examples, boundaries and refusals.

Every expected amount below is either a published SSA figure captured in
``tests/data/track_b/gross_benefit_sources/`` (its manifest records each
URL, UTC retrieval time, byte count and SHA-256, and
:func:`test_worked_example_figures_are_quoted_from_the_captures` proves the
figures appear verbatim in the captures) or is derived arithmetically from
the statute in the test itself. Inputs are invented or published examples;
no survey data and no comparator values are used.
"""

from __future__ import annotations

import dataclasses
import hashlib
import re
from datetime import date
from fractions import Fraction as F

import pytest

from populace_dynamics.ss import benefits as oracle
from populace_dynamics.track_b import gross_benefits as g
from tests.track_b_gross_benefit_support import (
    SOURCES,
    manifest,
    poms_bend_point_table,
    source_text,
    ssa_params,
)

PARAMS = ssa_params()
NOW = g.YearMonth(2026, 1)
OLD_AGE = g.OwnBenefitKind.OLD_AGE
DISABILITY = g.OwnBenefitKind.DISABILITY


def _money(text: str) -> F:
    return F(text.replace(",", ""))


def _family(state, beneficiaries, month=NOW, params=PARAMS):
    return g.family_benefits(
        state, beneficiaries, payment_month=month, params=params
    )


def _payable(result) -> dict[str, F]:
    return {
        b.beneficiary_id: b.auxiliary_payable for b in result.beneficiaries
    }


def _retired(pia, maximum, **worker):
    return g.RecordState(
        g.FamilyKind.RETIREMENT,
        F(pia),
        F(maximum),
        worker=g.OwnBenefit(OLD_AGE, F(pia), **worker),
    )


# ===========================================================================
# Source integrity
# ===========================================================================
def test_manifest_pins_every_capture():
    document = manifest()
    assert document["schema_version"] == 1
    assert set(document["capture_formats"]) == {
        "http_body",
        "browser_text",
        "http_text_excerpt",
    }
    ids = [source["id"] for source in document["sources"]]
    assert len(ids) == len(set(ids))
    for source in document["sources"]:
        data = (SOURCES / source["file"]).read_bytes()
        assert len(data) == source["bytes"], source["id"]
        assert hashlib.sha256(data).hexdigest() == source["sha256"]
        assert source["url"].startswith("https://")
        assert re.fullmatch(
            r"2026-09-2\dT\d\d:\d\d:\d\dZ", source["retrieved_at_utc"]
        )
        assert source["capture"] in document["capture_formats"]
        if source["capture"] == "http_body":
            assert "served_bodies" not in source, source["id"]
            continue
        # Text captures record the full body served at the same time.
        urls = [source["url"], *source.get("additional_urls", [])]
        assert [body["url"] for body in source["served_bodies"]] == urls
        for body in source["served_bodies"]:
            host = (
                "https://www.ssa.gov/"
                if source["capture"] == "browser_text"
                else "https://www.law.cornell.edu/"
            )
            assert body["url"].startswith(host), source["id"]
            assert re.fullmatch(r"[0-9a-f]{64}", body["sha256"])
            assert body["bytes"] > len(data)
    captured = {path.name for path in SOURCES.iterdir()}
    listed = {s["file"] for s in document["sources"]}
    assert captured - listed == {"manifest.json", "README.md"}


WORKED_EXAMPLE_QUOTES = {
    "poms_rs_00615_756": [
        "D (age 65) and seven C's",
        "$492.90",
        "$862.60",
        "$3080.10",
        "$138.00",
        "$103.50 each",
        "$310.00",
        "$225.00",
        "PIA of $300.00",
        "FMAX of $450.00",
        "$260.70",
        "$189.20",
    ],
    "poms_rs_00615_768": [
        "The PIA is $400.00 and the maximum is $650.00",
        "$83.30 each",
        "Their PIA is $100.00",
        "C2 and C1 are each due $125.00",
        "The PIA is $600 and the maximum is $900",
        "own PIA of $120",
        "reduced to $30",
        "The rate payable to HC1 is then $270",
        "payable for 10/99 or later",
    ],
    "poms_rs_00615_682": [
        "$101.90 each",
        "PIA of $203.90 (Maximum $305.90)",
        "$145.70 ($203.90 reduced 60 months)",
        "$152.90 to each child",
    ],
    "poms_rs_00615_710": [
        "The PIA is $400. The family maximum is $700.",
        "$410 x 700/710 = 404.20",
        "$300 x 700/710 = 295.70",
    ],
    "poms_rs_00615_301": [
        "RF is 37 while the total possible RF is 62. The OB is $987.60.",
        "$819.60 payable",
        "1/2/40 - 1/1/41",
        "1/2/62 or later",
    ],
    "poms_rs_00615_320": [
        "reduced RIB of $350 (PIA $374.90)",
        "82 1/2 percent of the death PIA is $309.20",
        "($350 in this example.)",
    ],
    "poms_rs_00615_005": [
        "A PIA of $802.80 is to be reduced for 5 months",
        "MBA of $780.50",
        "the MBA would be $780.40",
    ],
    "poms_rs_00615_692": [
        "PIA = $1000.00",
        "30 DRCs apply at 7/12 of 1 percent per month",
        "$1000.00 + $175.00 = $1175.00",
    ],
    "poms_rs_00615_240": [
        "entitled to a reduced spouse benefit of $450.00",
        "After reduction the RIB is $200.00",
        "the difference between it and the spouse benefit - $250.00",
        "So their total benefit will still equal $450.00",
    ],
    "poms_rs_00615_694": [
        "DOB 3/02/35",
        "Toni's RIB PIA is $500.00",
        "RIB PIA is $1600.00",
        "$400.00 ($500 reduced for 36 RF)",
        "Spouse payment is $290 ($700 - $410)",
    ],
    "poms_rs_00615_736": [
        "Their PIA in 11/80 was $359.30",
        "$659.02 rounded to $659.10",
        "$647.89 rounded to $647.90",
        "Their DIB PIA in 3/79 was $341.10",
        "$625.23 rounded to $625.30",
        "DIB PIA in 10/79 is $423.70",
        "The family maximum in 12/80 is $759.30",
    ],
    "ssa_oact_familymax": [
        "$230 times 69,846.57 divided by $9,779.44 equals $1,642.70, "
        "which rounds to $1,643",
        "equals $2,371.21, which rounds to $2,371",
        "equals $3,092.57, which rounds to $3,093",
        "We then round this total amount to the next lower multiple of $.10",
    ],
    "ssa_ssb_v75n3_family_maximum": [
        "150% × $1,056 + 272% × $144 = $1,976",
        "Spouse 659",
        "Total family benefit 1,976",
        "150% × $1,200 = $1,800",
        "Spouse 200",
        "Child 1 300",
        "Child 1 250",
        "Spouse 100",
        "rounded down to the nearest dime",
    ],
}


@pytest.mark.parametrize(
    ("source_id", "quote"),
    [
        (source_id, quote)
        for source_id, quotes in WORKED_EXAMPLE_QUOTES.items()
        for quote in quotes
    ],
)
def test_worked_example_figures_are_quoted_from_the_captures(source_id, quote):
    assert quote in source_text(source_id)


# ===========================================================================
# Family maximum: bend points and the 403(a)(1) formula
# ===========================================================================
def test_2026_bend_points_reproduce_the_oact_determination():
    nawi_2024 = F("69846.57")
    nawi_1977 = F("9779.44")
    unrounded = [base * nawi_2024 / nawi_1977 for base in (230, 332, 433)]
    assert [round(x, 2) for x in unrounded] == [
        F("1642.70"),
        F("2371.21"),
        F("3092.57"),
    ]
    assert g.family_maximum_bend_points(2026, PARAMS) == (1643, 2371, 3093)


def test_bend_points_match_the_poms_table_for_every_year_1979_2026():
    table = poms_bend_point_table()
    assert sorted(table) == list(range(1979, 2027))
    for year, (pia1, pia2, fm1, fm2, fm3) in table.items():
        assert g.family_maximum_bend_points(year, PARAMS) == (fm1, fm2, fm3)
        # The same NAWI yields the PIA bend points the repository uses.
        assert PARAMS.bend_points(year) == (pia1, pia2)


def _poms_family_maximum_chart() -> dict[int, dict]:
    """RS 00605.910: per year, bend point 1 and the three segment rows.

    The chart's own typography varies (em dashes, a missing percent sign),
    so each segment is read as "<constant> plus <pct>% of excess of <bp>".
    """
    text = source_text("poms_rs_00605_910")
    heads = list(
        re.finditer(r"\b((?:19|20)\d\d) Up through ([\d,]+(?:\.\d+)?)", text)
    )
    chart = {}
    for index, head in enumerate(heads):
        end = heads[index + 1].start() if index + 1 < len(heads) else None
        segment = text[head.end() : end]
        rows = re.findall(
            r"([\d,]+(?:\.\d+)?) plus (272|134|175) ?%? of excess of ([\d,]+)",
            segment,
        )
        chart[int(head.group(1))] = {
            "first": _money(head.group(2)),
            "rows": [(_money(c), int(p), _money(x)) for c, p, x in rows],
        }
    return chart


#: RS 00605.910 prints 899.52 for 1981's third constant. The statute gives
#: 731.40 + 134% x (508 - 390) = 889.52; RS 00615.736B.3's 1981 example
#: uses the same 405.00 and 272 percent, so the chart digit is an erratum.
CHART_ERRATA = {(1981, 175): (F("899.52"), F("889.52"))}


def test_family_maximum_chart_constants_are_the_formula_at_each_bend_point():
    chart = _poms_family_maximum_chart()
    assert sorted(chart) == list(range(1979, 2027))
    for year, entry in chart.items():
        points = g.family_maximum_bend_points(year, PARAMS)
        assert entry["first"] == points[0]
        assert [row[1] for row in entry["rows"]] == [272, 134, 175]
        assert [row[2] for row in entry["rows"]] == list(points)
        for (constant, percent, point), expected_point in zip(
            entry["rows"], points, strict=True
        ):
            formula = g.family_maximum_formula(point, year, PARAMS)
            published, corrected = CHART_ERRATA.get(
                (year, percent), (constant, constant)
            )
            assert constant == published
            assert formula == corrected, (year, percent)
            assert point == expected_point


def test_chart_erratum_is_exactly_ten_dollars():
    published, corrected = CHART_ERRATA[(1981, 175)]
    assert published - corrected == 10
    assert corrected == F("731.40") + F("1.34") * (508 - 390)


@pytest.mark.parametrize(
    ("pia", "year", "shown", "rounded_up"),
    [
        ("359.30", 1979, "659.02", "659.10"),
        ("359.30", 1981, "647.89", "647.90"),
        ("341.10", 1980, "625.23", "625.30"),
        ("423.70", 1980, None, "759.30"),
    ],
)
def test_poms_736_formula_amounts_and_pre_june_1982_rounding(
    pia, year, shown, rounded_up
):
    exact = g.family_maximum_formula(F(pia), year, PARAMS)
    if shown is not None:
        # POMS shows the unrounded sum to the cent (truncated).
        assert F(int(exact * 100), 100) == F(shown)
    # Pre-June-1982 maximums were rounded up (RS 00615.736B.3) ...
    assert g.ceil_dime(exact) == F(rounded_up)
    # ... which this layer refuses rather than reproduces.
    with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
        g.retirement_survivor_family_maximum(F(pia), year, PARAMS)
    assert caught.value.reason is g.UnsupportedReason.ELIGIBILITY_BEFORE_1983


@pytest.mark.parametrize("year", [1983, 1999, 2015, 2022, 2026])
def test_family_maximum_boundaries_at_each_bend_point(year):
    b1, b2, b3 = g.family_maximum_bend_points(year, PARAMS)
    dime = F(1, 10)
    formula = g.family_maximum_formula
    assert formula(b1, year, PARAMS) == F(3, 2) * b1
    for point, below, above in (
        (b1, F("1.50"), F("2.72")),
        (b2, F("2.72"), F("1.34")),
        (b3, F("1.34"), F("1.75")),
    ):
        at = formula(point, year, PARAMS)
        assert formula(point - dime, year, PARAMS) == at - below * dime
        assert formula(point + dime, year, PARAMS) == at + above * dime
        for pia in (point - dime, point, point + dime):
            rounded = g.retirement_survivor_family_maximum(pia, year, PARAMS)
            assert rounded == g.floor_dime(formula(pia, year, PARAMS))
            assert rounded <= formula(pia, year, PARAMS) < rounded + dime


def test_2026_bend_point_boundaries_in_dollars():
    fm = g.retirement_survivor_family_maximum
    assert fm("1643.00", 2026, PARAMS) == F("2464.50")
    assert fm("1643.10", 2026, PARAMS) == F("2464.70")  # 2464.772
    assert fm("2371.00", 2026, PARAMS) == F("4444.60")  # 4444.66
    assert fm("2371.10", 2026, PARAMS) == F("4444.70")  # 4444.794
    assert fm("3093.00", 2026, PARAMS) == F("5412.10")  # 5412.14
    assert fm("3093.10", 2026, PARAMS) == F("5412.30")  # 5412.315


def test_bend_point_half_dollar_ties_round_up():
    # 215(a)(1)(B)(iii): a multiple of $0.50 that is not of $1 rounds up,
    # never to even. With a 7/4 wage ratio: 230 x 1.75 = 402.50 -> 403
    # (banker's rounding would give 402), 332 x 1.75 = 581, and
    # 433 x 1.75 = 757.75 -> 758.
    tied = ssa_params(nawi={1977: 4.0, 1998: 7.0})
    assert g.family_maximum_bend_points(2000, tied) == (403, 581, 758)


def test_missing_nawi_raises_instead_of_extrapolating():
    with pytest.raises(KeyError, match="NAWI for 2025"):
        g.family_maximum_bend_points(2027, PARAMS)


def test_family_maximum_stays_within_150_to_188_percent_of_pia():
    # SSB 75(3): the formula "yields a maximum ... between 150 percent and
    # 188 percent" of the PIA.
    for year in (1983, 2000, 2026):
        for dimes in range(1, 60_000, 37):
            pia = F(dimes, 10)
            ratio = g.family_maximum_formula(pia, year, PARAMS) / pia
            assert F(150, 100) <= ratio <= F(188, 100)


# ===========================================================================
# The disability maximum, 403(a)(6)
# ===========================================================================
def _disability_state(pia, aime, year=2015, colas=()):
    return g.record_state(
        g.WorkerRecord(
            g.FamilyKind.DISABILITY,
            year,
            F(pia),
            cola_percents=colas,
            aime=aime,
            first_dib_entitlement=g.YearMonth(year, 6),
        ),
        PARAMS,
    )


@pytest.mark.parametrize(
    ("pia", "aime", "expected"),
    [
        ("1200", 2253, "1800"),  # SSB Table 2: 85% x 2,253 exceeds 150%
        ("1000.00", 1300, "1105.00"),  # 85% of AIME binds
        ("1000.00", 1001, "1000.00"),  # 850.85 is below the PIA
        ("1000.00", 2000, "1500.00"),  # 1,700 is above 150% of the PIA
        ("1000.10", 5000, "1500.10"),  # 1,500.15 dime-floored
        ("1000.00", 1239, "1053.10"),  # 1,053.15 dime-floored
        ("1000.00", 0, "1000.00"),
    ],
)
def test_disability_family_maximum(pia, aime, expected):
    assert g.disability_family_maximum(F(pia), aime) == F(expected)
    assert _disability_state(pia, aime).family_maximum == F(expected)


def test_disability_maximum_refuses_pre_july_1980_entitlement():
    record = g.WorkerRecord(
        g.FamilyKind.DISABILITY,
        1990,
        F(500),
        aime=800,
        first_dib_entitlement=g.YearMonth(1980, 6),
    )
    with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
        g.record_state(record, PARAMS)
    reason = g.UnsupportedReason.DI_ENTITLEMENT_BEFORE_JULY_1980
    assert caught.value.reason is reason


def test_disability_record_needs_aime_and_entitlement_month():
    record = g.WorkerRecord(g.FamilyKind.DISABILITY, 2015, F(1200))
    with pytest.raises(g.InvalidFamilyInput):
        g.record_state(record, PARAMS)


# ===========================================================================
# COLAs: 215(i)(2)(A)(ii) applies to the PIA and the maximum alike
# ===========================================================================
def test_colas_floor_to_the_dime_after_each_increase():
    assert g.increase_by_colas(F("1000.00"), ["2.8"]) == F("1028.00")
    # 1,000 x 1.087 = 1,087.00; x 1.032 = 1,121.784 -> 1,121.70.
    assert g.increase_by_colas(F(1000), ["8.7", "3.2"]) == F("1121.70")
    # 999.90 x 1.013 = 1,012.8987 -> 1,012.80.
    assert g.increase_by_colas(F("999.90"), [1.3]) == F("1012.80")
    assert g.increase_by_colas(F("512.30"), ["0.0", "0.0"]) == F("512.30")
    with pytest.raises(g.InvalidFamilyInput):
        g.increase_by_colas(F(100), ["-0.5"])


def test_record_state_applies_the_same_colas_to_pia_and_maximum():
    colas = ("1.7", "0.0", "0.3", "2.0")
    record = g.WorkerRecord(
        g.FamilyKind.SURVIVOR, 2015, F(1200), cola_percents=colas
    )
    state = g.record_state(record, PARAMS)
    base = g.retirement_survivor_family_maximum(F(1200), 2015, PARAMS)
    assert base == F("1975.60")
    assert state.pia == g.increase_by_colas(F(1200), colas)
    assert state.family_maximum == g.increase_by_colas(base, colas)


# ===========================================================================
# Age adjustments (exact fractions)
# ===========================================================================
def test_poms_005_fractions_not_decimals():
    base, with_credits = g.worker_age_adjusted(F("802.80"), 5, 0, None, PARAMS)
    assert base == with_credits == F("780.50")
    # The float oracle multiplies by a decimal equivalent and, floored to
    # the dime, lands on the wrong answer POMS warns about.
    decimal_factor = 1 - oracle.early_reduction(5, PARAMS)
    assert g.floor_dime(F(repr(802.80 * decimal_factor))) == F("780.40")


@pytest.mark.parametrize("months", range(0, 61))
def test_reduction_chart_fractions(months):
    first = min(months, 36)
    arm = max(0, months - 36)
    worker = F(180 - first, 180) if months <= 36 else F(192 - arm, 240)
    spouse = F(144 - first, 144) if months <= 36 else F(180 - arm, 240)
    pia = F("1234.50")
    assert g.worker_age_adjusted(pia, months, 0, None, PARAMS)[0] == (
        g.floor_dime(pia * worker)
    )
    assert g.spouse_age_reduced(pia, months, PARAMS) == g.floor_dime(
        pia * spouse
    )


def test_poms_301_widow_reduction_example():
    assert g.widow_reduction_period_months(date(1940, 6, 15)) == 62
    assert g.survivor_age_reduced(F("987.60"), 37, 62, PARAMS) == F("819.60")


@pytest.mark.parametrize(
    ("birth", "period"),
    [
        (date(1939, 12, 31), 60),
        (date(1940, 1, 1), 60),
        (date(1940, 1, 2), 62),
        (date(1945, 1, 1), 70),
        (date(1945, 1, 2), 72),
        (date(1957, 1, 1), 72),
        (date(1957, 1, 2), 74),
        (date(1962, 1, 1), 82),
        (date(1962, 1, 2), 84),
        (date(1990, 7, 4), 84),
    ],
)
def test_widow_reduction_period_by_birth_date(birth, period):
    assert g.widow_reduction_period_months(birth) == period


def test_widow_reduction_rounds_the_reduction_up():
    # 203.90 x 60 x .285 / 60 = 58.1115 -> MAR 58.20 (RS 00615.682).
    assert g.survivor_age_reduced(F("203.90"), 60, 60, PARAMS) == F("145.70")
    # At the full period the floor is 71.5 percent, less the rounding up.
    assert g.survivor_age_reduced(F(1000), 84, 84, PARAMS) == F("715.00")


def test_poms_692_delayed_credits():
    base, credited = g.worker_age_adjusted(F(1000), 0, 30, 1940, PARAMS)
    assert (base, credited) == (F(1000), F(1175))


# ===========================================================================
# Families: SSA worked examples
# ===========================================================================
def test_poms_756_widow_and_seven_children():
    state = g.RecordState(g.FamilyKind.SURVIVOR, F("492.90"), F("862.60"))
    children = [g.Beneficiary(f"C{i}", g.Role.CHILD) for i in range(7)]
    result = _family(state, [g.Beneficiary("D", g.Role.WIDOW), *children])
    rows = result.by_id()
    assert rows["D"].original_benefit == F("492.90")
    assert rows["C0"].original_benefit == F("369.60")  # 369.675 floored
    assert result.total_original_benefits == F("3080.10")
    assert rows["D"].auxiliary_payable == F("138.00")
    assert {rows[f"C{i}"].auxiliary_payable for i in range(7)} == {F("103.50")}
    # 215(g): each benefit to the whole dollar.
    assert rows["D"].whole_dollar_auxiliary == 138
    assert result.record_total_whole_dollars == 138 + 7 * 103
    assert result.record_total == F("862.50") <= result.family_maximum


def test_poms_756_windexed_widow_and_child():
    state = g.RecordState(g.FamilyKind.SURVIVOR, F(300), F(450))
    nora = g.Beneficiary("Nora", g.Role.WIDOW, original_benefit_basis=F(310))
    michael = g.Beneficiary("Michael", g.Role.CHILD)
    result = _family(state, [nora, michael])
    assert _payable(result) == {"Nora": F("260.70"), "Michael": F("189.20")}


def test_poms_710_widow_delayed_credits_share_the_maximum():
    state = g.RecordState(g.FamilyKind.SURVIVOR, F(400), F(700))
    widow = g.Beneficiary("W", g.Role.WIDOW, original_benefit_basis=F(410))
    result = _family(state, [widow, g.Beneficiary("C", g.Role.CHILD)])
    assert _payable(result) == {"W": F("404.20"), "C": F("295.70")}


def test_poms_682_surviving_divorced_spouse_paid_outside_the_maximum():
    state = g.RecordState(g.FamilyKind.SURVIVOR, F("203.90"), F("305.90"))
    children = [g.Beneficiary(f"C{i}", g.Role.CHILD) for i in (1, 2)]
    before = _family(
        state, [g.Beneficiary("E1", g.Role.MOTHER_FATHER), *children]
    )
    assert set(_payable(before).values()) == {F("101.90")}
    d6 = g.Beneficiary(
        "D6",
        g.Role.SURVIVING_DIVORCED_SPOUSE,
        reduction_months=60,
        reduction_period_months=60,
    )
    after = _family(state, [d6, *children])
    assert _payable(after) == {
        "D6": F("145.70"),
        "C1": F("152.90"),  # capped at the OB (152.95 share > 152.90 OB)
        "C2": F("152.90"),
    }
    assert not after.by_id()["D6"].subject_to_family_maximum
    assert after.by_id()["D6"].counted_against_maximum == 0


def test_poms_768_dually_entitled_spouse_reduced_to_zero():
    state = _retired(400, 650)
    spouse = g.Beneficiary(
        "B", g.Role.SPOUSE, own_benefit=g.OwnBenefit(OLD_AGE, F(100))
    )
    children = [g.Beneficiary(c, g.Role.CHILD) for c in ("C2", "C1")]
    result = _family(state, [spouse, *children])
    rows = result.by_id()
    # The pre-Parisi rates, $83.30 each, are the standard shares.
    assert {row.standard_rate for row in rows.values()} == {F("83.30")}
    assert rows["B"].entitled and rows["B"].auxiliary_payable == 0
    assert rows["C1"].auxiliary_payable == rows["C2"].auxiliary_payable
    assert rows["C1"].auxiliary_payable == F(125)
    assert result.redistribution_applied
    assert result.worker_benefit == F(400)


def test_poms_768_dually_entitled_child_with_a_partial_payment():
    state = g.RecordState(g.FamilyKind.DISABILITY, F(600), F(900))
    hc2 = g.Beneficiary(
        "HC2", g.Role.CHILD, own_benefit=g.OwnBenefit(DISABILITY, F(120))
    )
    result = _family(state, [hc2, g.Beneficiary("HC1", g.Role.CHILD)])
    assert _payable(result) == {"HC2": F(30), "HC1": F(270)}
    assert result.record_total == F(900)
    assert result.by_id()["HC2"].total_received == F(150)


def test_poms_768_rule_starts_with_october_1999_payments():
    state = _retired(400, 650)
    spouse = g.Beneficiary(
        "B", g.Role.SPOUSE, own_benefit=g.OwnBenefit(OLD_AGE, F(100))
    )
    family = [spouse, g.Beneficiary("C1", g.Role.CHILD)]
    with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
        _family(state, family, month=g.YearMonth(1999, 9))
    reason = g.UnsupportedReason.PARISI_BEFORE_OCTOBER_1999
    assert caught.value.reason is reason
    assert _family(state, family, month=g.YearMonth(1999, 10))
    # When the maximum does not bind, the rule is irrelevant and allowed.
    roomy = _retired(400, 1000)
    assert _family(roomy, family, month=g.YearMonth(1990, 1))


def test_poms_768_all_dually_entitled_disregards_the_rule():
    state = _retired(400, 650)
    own = g.OwnBenefit(OLD_AGE, F(100))
    family = [
        g.Beneficiary("B", g.Role.SPOUSE, own_benefit=own),
        g.Beneficiary("C1", g.Role.CHILD, own_benefit=own),
    ]
    result = _family(state, family, month=g.YearMonth(1995, 1))
    assert not result.redistribution_applied
    assert {b.family_maximum_rate for b in result.beneficiaries} == {F(125)}


def test_poms_320_rib_lim():
    state = g.RecordState(
        g.FamilyKind.SURVIVOR, F("374.90"), F("600"), rib_lim_benefit=F(350)
    )
    result = _family(state, [g.Beneficiary("W", g.Role.WIDOW)])
    assert _payable(result) == {"W": F(350)}
    # With a smaller deceased RIB the 82.5 percent floor governs: 309.20.
    lower = g.RecordState(
        g.FamilyKind.SURVIVOR, F("374.90"), F("600"), rib_lim_benefit=F(300)
    )
    assert _payable(_family(lower, [g.Beneficiary("W", g.Role.WIDOW)])) == {
        "W": F("309.20")
    }


def test_poms_694_spouse_with_delayed_credits_on_the_own_rib():
    state = _retired(1600, 2400)
    toni = g.Beneficiary(
        "Toni",
        g.Role.SPOUSE,
        own_benefit=g.OwnBenefit(
            OLD_AGE,
            F(500),
            reduction_months=36,
            delayed_credit_months=5,
            birth_year=1935,
        ),
    )
    row = _family(state, [toni]).by_id()["Toni"]
    assert row.own_benefit == F(410)
    assert row.age_adjusted_rate == F(700)
    assert row.auxiliary_payable == F(290)
    assert row.total_received == F(700)


def test_ssb_table_1_survivor_family():
    state = g.record_state(
        g.WorkerRecord(g.FamilyKind.SURVIVOR, 2015, F(1200)), PARAMS
    )
    assert g.family_maximum_bend_points(2015, PARAMS)[:1] == (1056,)
    assert state.family_maximum == F("1975.60")  # 1,975.68 dime-floored
    family = [
        g.Beneficiary("Spouse", g.Role.MOTHER_FATHER),
        g.Beneficiary("Child 1", g.Role.CHILD),
        g.Beneficiary("Child 2", g.Role.CHILD),
    ]
    result = _family(state, family, month=g.YearMonth(2015, 6))
    assert set(_payable(result).values()) == {F("658.50")}
    # The Bulletin rounds to the nearest dollar for presentation only.
    assert {math_round(v) for v in _payable(result).values()} == {659}
    assert math_round(state.family_maximum) == 1976
    assert math_round(result.record_total) == 1976


def math_round(value: F) -> int:
    """Nearest dollar, halves up (the Bulletin's presentation rounding)."""
    return int(value + F(1, 2)) if value >= 0 else -math_round(-value)


def _ssb_disability_family(spouse_own=None):
    state = _disability_state("1200", 2253)
    spouse = g.Beneficiary(
        "Spouse",
        g.Role.SPOUSE,
        own_benefit=(
            None if spouse_own is None else g.OwnBenefit(OLD_AGE, spouse_own)
        ),
    )
    family = [spouse] + [
        g.Beneficiary(f"Child {i}", g.Role.CHILD) for i in (1, 2)
    ]
    return _family(state, family, month=g.YearMonth(2015, 6))


def test_ssb_table_2_disabled_worker_family():
    result = _ssb_disability_family()
    assert result.family_maximum == F(1800)
    assert set(_payable(result).values()) == {F(200)}
    assert result.record_total == F(1800)


def test_ssb_table_a1_spouse_not_entitled_on_the_record():
    result = _ssb_disability_family(spouse_own=F(1000))
    rows = result.by_id()
    assert not rows["Spouse"].entitled
    assert rows["Spouse"].own_benefit == F(1000)
    assert rows["Child 1"].auxiliary_payable == F(300)
    assert rows["Child 2"].auxiliary_payable == F(300)
    total = result.record_total + rows["Spouse"].own_benefit
    assert total == F(2800)


def test_ssb_table_a2_dually_entitled_spouse():
    result = _ssb_disability_family(spouse_own=F(100))
    assert _payable(result) == {
        "Spouse": F(100),
        "Child 1": F(250),
        "Child 2": F(250),
    }
    assert result.record_total + 100 == F(1900)


# ===========================================================================
# Statutory order and the maximum's exceptions
# ===========================================================================
def test_age_reduction_applies_to_the_family_maximum_share():
    state = _retired(1000, 1500)
    spouse = g.Beneficiary("S", g.Role.SPOUSE, reduction_months=60)
    children = [g.Beneficiary(c, g.Role.CHILD) for c in ("C1", "C2")]
    rows = _family(state, [spouse, *children]).by_id()
    assert rows["S"].family_maximum_rate == F("166.60")  # 500/3 floored
    # RS 00615.210: reduce the share (not the OB) for age.
    assert rows["S"].auxiliary_payable == F("108.20")  # 166.60 x .65
    # Reducing the OB first would have left 325.00 to share, not 166.60.
    assert g.spouse_age_reduced(F(500), 60, PARAMS) == F(325)
    # Age reduction does not free room for the children (no redistribution
    # without dual entitlement).
    assert rows["C1"].auxiliary_payable == F("166.60")


def test_worker_delayed_credits_are_outside_the_maximum():
    state = _retired(1000, 1500, delayed_credit_months=36, birth_year=1950)
    children = [g.Beneficiary(c, g.Role.CHILD) for c in ("C1", "C2")]
    result = _family(state, children)
    assert result.worker_benefit == F(1240)  # 1,000 + 24 percent
    # RS 00615.695: only the PIA is deducted from the maximum.
    assert result.available_for_auxiliaries == F(500)
    assert set(_payable(result).values()) == {F(250)}
    assert result.record_total == F(1740) > result.family_maximum


def test_divorced_spouse_is_ignored_by_everyone_else():
    state = _retired(1000, 1500)
    children = [g.Beneficiary(c, g.Role.CHILD) for c in ("C1", "C2")]
    divorced = g.Beneficiary("X", g.Role.DIVORCED_SPOUSE, reduction_months=12)
    without = _family(state, children)
    with_divorced = _family(state, [*children, divorced])
    for child in ("C1", "C2"):
        assert (
            with_divorced.by_id()[child].auxiliary_payable
            == without.by_id()[child].auxiliary_payable
        )
    # The divorced spouse gets the full OB reduced for age: 500 x 132/144.
    assert with_divorced.by_id()["X"].auxiliary_payable == F("458.30")
    assert with_divorced.subject_total == without.subject_total


def test_spouse_not_entitled_when_own_pia_reaches_half():
    state = _retired(1000, 1500)
    exact_half = g.Beneficiary(
        "S", g.Role.SPOUSE, own_benefit=g.OwnBenefit(OLD_AGE, F(500))
    )
    just_below = g.Beneficiary(
        "S", g.Role.SPOUSE, own_benefit=g.OwnBenefit(OLD_AGE, F("499.90"))
    )
    assert not _family(state, [exact_half]).by_id()["S"].entitled
    row = _family(state, [just_below]).by_id()["S"]
    assert row.entitled and row.auxiliary_payable == F("0.10")


def test_widow_entitlement_compares_own_rib_with_the_deemed_pia():
    state = g.RecordState(g.FamilyKind.SURVIVOR, F(1000), F(1500))
    own = g.OwnBenefit(OLD_AGE, F(1050))
    plain = g.Beneficiary("W", g.Role.WIDOW, own_benefit=own, birth_year=1960)
    assert not _family(state, [plain]).by_id()["W"].entitled
    # 202(e)(2)(C): a deceased's credits raise the PIA used for the test.
    credited = g.Beneficiary(
        "W",
        g.Role.WIDOW,
        original_benefit_basis=F(1240),
        own_benefit=own,
        birth_year=1960,
    )
    row = _family(state, [credited]).by_id()["W"]
    assert row.entitled
    assert row.auxiliary_payable == F(190)
    assert row.total_received == F(1240)


def test_widow_dual_entitlement_is_method_b():
    # RS 00615.020A.3 method B: both reduced independently, then offset.
    state = g.RecordState(g.FamilyKind.SURVIVOR, F(1000), F(1500))
    widow = g.Beneficiary(
        "W",
        g.Role.WIDOW,
        reduction_months=24,
        reduction_period_months=84,
        own_benefit=g.OwnBenefit(OLD_AGE, F(400), reduction_months=12),
        birth_year=1962,
    )
    row = _family(state, [widow]).by_id()["W"]
    # WIB: 1,000 - ceil(1,000 x 24 x .285 / 84 = 81.43) = 918.50.
    assert row.age_adjusted_rate == F("918.50")
    # RIB: 400 x 168/180 = 373.33 -> 373.30.
    assert row.own_benefit == F("373.30")
    assert row.auxiliary_payable == F("545.20")
    assert row.total_received == F("918.50")


def test_spouse_with_reduced_own_rib_is_method_c():
    # 402(q)(3)(B): reduce the spouse benefit by the RIB's own reduction
    # plus the spousal reduction of the excess over the RIB *PIA*.
    state = _retired(1200, 2100)
    spouse = g.Beneficiary(
        "S",
        g.Role.SPOUSE,
        reduction_months=36,
        own_benefit=g.OwnBenefit(OLD_AGE, F(400), reduction_months=36),
    )
    row = _family(state, [spouse]).by_id()["S"]
    assert row.own_benefit == F(320)  # 400 x 144/180
    # Excess 600 - 400 = 200, reduced by 36 x 25/36 percent: 150.
    assert row.auxiliary_payable == F(150)
    assert row.age_adjusted_rate == F(470)  # 600 - 80 - 50
    assert row.total_received == F(470)


def test_child_in_care_spouse_offset_uses_the_reduced_rib():
    state = _retired(1000, 2000)
    spouse = g.Beneficiary(
        "S",
        g.Role.SPOUSE_CHILD_IN_CARE,
        own_benefit=g.OwnBenefit(OLD_AGE, F(300), reduction_months=36),
    )
    row = _family(state, [spouse]).by_id()["S"]
    # RS 00615.020 note: unreduced spouse benefit less the reduced RIB.
    assert row.own_benefit == F(240)
    assert row.auxiliary_payable == F(260)


def test_disabled_worker_family_can_leave_nothing_for_auxiliaries():
    # AIME at or below the PIA / 0.85 leaves DMAX = PIA (SSB 75(3)).
    state = _disability_state("900.00", 1000)
    assert state.family_maximum == F(900)
    result = _family(state, [g.Beneficiary("C", g.Role.CHILD)])
    assert _payable(result) == {"C": F(0)}


# ===========================================================================
# Refusals: every unsupported configuration raises, by name
# ===========================================================================
def _survivor_state():
    return g.RecordState(g.FamilyKind.SURVIVOR, F(1000), F(1750))


def _unsupported_cases():
    widow_dib = g.OwnBenefit(DISABILITY, F(300))
    return {
        g.UnsupportedReason.ELIGIBILITY_BEFORE_1983: lambda: g.record_state(
            g.WorkerRecord(g.FamilyKind.SURVIVOR, 1982, F(500)), PARAMS
        ),
        g.UnsupportedReason.PAYMENT_MONTH_BEFORE_1983: lambda: _family(
            _survivor_state(), [], month=g.YearMonth(1982, 12)
        ),
        g.UnsupportedReason.DI_ENTITLEMENT_BEFORE_JULY_1980: lambda: (
            g.record_state(
                g.WorkerRecord(
                    g.FamilyKind.DISABILITY,
                    1985,
                    F(500),
                    aime=700,
                    first_dib_entitlement=g.YearMonth(1979, 12),
                ),
                PARAMS,
            )
        ),
        g.UnsupportedReason.COMBINED_FAMILY_MAXIMUM: lambda: _family(
            _survivor_state(),
            [
                g.Beneficiary(
                    "C",
                    g.Role.CHILD,
                    conditions={
                        g.BeneficiaryCondition.ENTITLED_ON_ANOTHER_RECORD
                    },
                )
            ],
        ),
        g.UnsupportedReason.DEEMED_SPOUSE: lambda: _family(
            _retired(1000, 1750),
            [
                g.Beneficiary(
                    "S",
                    g.Role.SPOUSE,
                    conditions={
                        g.BeneficiaryCondition.DEEMED_OR_PUTATIVE_SPOUSE
                    },
                )
            ],
        ),
        g.UnsupportedReason.PARENT_BENEFIT: lambda: _family(
            _survivor_state(), [g.Beneficiary("P", g.Role.PARENT)]
        ),
        g.UnsupportedReason.DISABLED_WIDOW_UNDER_60: lambda: _family(
            _survivor_state(), [g.Beneficiary("W", g.Role.DISABLED_WIDOW)]
        ),
        g.UnsupportedReason.DIB_GUARANTEE_PIA: lambda: g.record_state(
            g.WorkerRecord(
                g.FamilyKind.SURVIVOR,
                2000,
                F(900),
                conditions={g.RecordCondition.DIB_GUARANTEE_PIA},
            ),
            PARAMS,
        ),
        g.UnsupportedReason.DIB_AFTER_REDUCED_RIB: lambda: g.OwnBenefit(
            DISABILITY, F(500), reduction_months=12
        ),
        g.UnsupportedReason.WORKERS_COMPENSATION_OFFSET: lambda: _family(
            g.RecordState(
                g.FamilyKind.DISABILITY,
                F(1000),
                F(1500),
                conditions={g.RecordCondition.WORKERS_COMPENSATION_OFFSET},
            ),
            [],
        ),
        g.UnsupportedReason.GOVERNMENT_PENSION_OFFSET: lambda: _family(
            _survivor_state(),
            [
                g.Beneficiary(
                    "W",
                    g.Role.WIDOW,
                    conditions={
                        g.BeneficiaryCondition.GOVERNMENT_PENSION_OFFSET
                    },
                )
            ],
        ),
        g.UnsupportedReason.ADMINISTRATIVE_FINALITY: lambda: _family(
            _retired(750, 1312.50),
            [
                g.Beneficiary(
                    "C",
                    g.Role.CHILD,
                    conditions={
                        g.BeneficiaryCondition.RATE_PROTECTED_BY_FINALITY
                    },
                )
            ],
        ),
        g.UnsupportedReason.DUAL_ENTITLEMENT_SEQUENCE: lambda: _family(
            _survivor_state(),
            [
                g.Beneficiary(
                    "W", g.Role.WIDOW, own_benefit=widow_dib, birth_year=1960
                )
            ],
        ),
        g.UnsupportedReason.PARISI_AMBIGUOUS: lambda: _family(
            _retired(1000, 1500),
            [
                g.Beneficiary(
                    "S",
                    g.Role.SPOUSE,
                    own_benefit=g.OwnBenefit(
                        OLD_AGE,
                        F(100),
                        delayed_credit_months=12,
                        birth_year=1950,
                    ),
                ),
                g.Beneficiary("C1", g.Role.CHILD),
                g.Beneficiary("C2", g.Role.CHILD),
            ],
        ),
        g.UnsupportedReason.PARISI_BEFORE_OCTOBER_1999: lambda: _family(
            _retired(400, 650),
            [
                g.Beneficiary(
                    "B",
                    g.Role.SPOUSE,
                    own_benefit=g.OwnBenefit(OLD_AGE, F(100)),
                ),
                g.Beneficiary("C1", g.Role.CHILD),
            ],
            month=g.YearMonth(1998, 1),
        ),
        g.UnsupportedReason.INDEPENDENT_DIVORCED_SPOUSE: lambda: _family(
            g.RecordState(
                g.FamilyKind.RETIREMENT,
                F(1000),
                F(1750),
                worker=g.OwnBenefit(OLD_AGE, F(1000)),
                conditions={g.RecordCondition.WORKER_NOT_ENTITLED},
            ),
            [g.Beneficiary("X", g.Role.DIVORCED_SPOUSE)],
        ),
        g.UnsupportedReason.NON_AIME_FORMULA_PIA: lambda: g.record_state(
            g.WorkerRecord(
                g.FamilyKind.SURVIVOR,
                2000,
                F(900),
                conditions={g.RecordCondition.NON_AIME_FORMULA_PIA},
            ),
            PARAMS,
        ),
    }


def test_every_unsupported_reason_has_a_refusal_case():
    assert set(_unsupported_cases()) == set(g.UnsupportedReason)


@pytest.mark.parametrize("reason", list(g.UnsupportedReason))
def test_unsupported_configurations_raise_by_name(reason):
    with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
        _unsupported_cases()[reason]()
    assert caught.value.reason is reason
    assert caught.value.code == "FAMILY_CONFIG_UNSUPPORTED"
    assert str(caught.value).startswith("FAMILY_CONFIG_UNSUPPORTED[")


def test_poms_240_spouse_then_rib_is_method_b():
    # RS 00615.240: a reduced spouse benefit of $450.00, then a RIB of
    # $200.00 after reduction: $250.00 as a spouse, $450.00 in total. The
    # spouse benefit keeps its own 402(q)(1) reduction; 402(q)(3)(A) does
    # not apply because the RIB did not exist in the spouse's first month.
    state = _retired(1200, 2100)
    b_then_a = g.Beneficiary(
        "S",
        g.Role.SPOUSE,
        reduction_months=36,  # 600 x 108/144 = 450
        own_benefit=g.OwnBenefit(OLD_AGE, F(250), reduction_months=36),
        own_benefit_first=False,
    )
    row = _family(state, [b_then_a]).by_id()["S"]
    assert row.age_adjusted_rate == F(450)
    assert row.own_benefit == F(200)  # 250 x 144/180
    assert row.auxiliary_payable == F(250)
    assert row.total_received == F(450)
    # Method C for the same people (A then B) reduces only the excess over
    # the own PIA for the spouse months: 200 + (600 - 250) x 108/144.
    a_then_b = dataclasses.replace(b_then_a, own_benefit_first=True)
    method_c = _family(state, [a_then_b]).by_id()["S"]
    assert method_c.auxiliary_payable == F("262.50")
    assert method_c.total_received == F("462.50")


def test_other_refused_sequences():
    state = _retired(1000, 1500)
    b_then_ha = g.Beneficiary(
        "S",
        g.Role.SPOUSE,
        reduction_months=24,
        own_benefit=g.OwnBenefit(DISABILITY, F(200)),
        own_benefit_first=False,
    )
    with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
        _family(state, [b_then_ha])
    assert caught.value.reason is g.UnsupportedReason.DUAL_ENTITLEMENT_SEQUENCE
    early_widow = g.Beneficiary(
        "W",
        g.Role.WIDOW,
        own_benefit=g.OwnBenefit(OLD_AGE, F(200)),
        birth_year=1927,
    )
    with pytest.raises(g.FamilyConfigurationUnsupported):
        _family(_survivor_state(), [early_widow])
    reduced_own_widow = g.Beneficiary(
        "W",
        g.Role.WIDOW,
        own_benefit=g.OwnBenefit(OLD_AGE, F(200), reduction_months=12),
        birth_year=1960,
    )
    crowded = [reduced_own_widow] + [
        g.Beneficiary(f"C{i}", g.Role.CHILD) for i in range(3)
    ]
    with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
        _family(_survivor_state(), crowded)
    assert caught.value.reason is g.UnsupportedReason.PARISI_AMBIGUOUS
    assert caught.value.beneficiary_id == "W"


# ===========================================================================
# Invalid inputs are errors, not coverage gaps
# ===========================================================================
@pytest.mark.parametrize(
    "build",
    [
        lambda: _family(
            _survivor_state(), [g.Beneficiary("S", g.Role.SPOUSE)]
        ),
        lambda: _family(
            _retired(1000, 1500), [g.Beneficiary("W", g.Role.WIDOW)]
        ),
        lambda: _family(
            _retired(1000, 1500),
            [g.Beneficiary("C", g.Role.CHILD)] * 2,
        ),
        lambda: g.Beneficiary("C", g.Role.CHILD, reduction_months=3),
        lambda: g.Beneficiary("C", g.Role.CHILD, original_benefit_basis=F(9)),
        lambda: g.Beneficiary("S", g.Role.SPOUSE, reduction_period_months=84),
        lambda: _family(
            _survivor_state(),
            [g.Beneficiary("W", g.Role.WIDOW, reduction_months=12)],
        ),
        lambda: g.RecordState(g.FamilyKind.SURVIVOR, F("100.05"), F(200)),
        lambda: g.RecordState(g.FamilyKind.SURVIVOR, F(1000), F(999)),
        lambda: g.RecordState(g.FamilyKind.RETIREMENT, F(1000), F(1500)),
        lambda: g.spouse_age_reduced(F(100), 61, PARAMS),
        lambda: g.survivor_age_reduced(F(100), 10, 59, PARAMS),
        lambda: g.worker_age_adjusted(F(100), 0, 12, None, PARAMS),
        lambda: g.OwnBenefit(DISABILITY, F(100), delayed_credit_months=1),
        lambda: _family(
            _survivor_state(),
            [
                g.Beneficiary(
                    "W",
                    g.Role.WIDOW,
                    own_benefit=g.OwnBenefit(OLD_AGE, F(100)),
                )
            ],
        ),
    ],
)
def test_invalid_inputs_raise_invalid_family_input(build):
    with pytest.raises(g.InvalidFamilyInput):
        build()


def test_parameter_bundle_that_disagrees_with_the_statute_is_refused():
    bad = ssa_params(early_monthly_rates=(0.0056, 0.00416667))
    with pytest.raises(ValueError, match="disagrees with the statutory"):
        g.statutory_rates(bad)


# ===========================================================================
# Denominators: unsupported rows are counted and block totals
# ===========================================================================
def test_unsupported_rows_stay_in_the_denominator_and_block_totals():
    supported = g.evaluate_family(
        "a", 3, lambda: _family(_retired(1000, 1500), [])
    )
    unsupported = g.evaluate_family(
        "b",
        F(1, 2),
        lambda: _family(
            _survivor_state(), [g.Beneficiary("P", g.Role.PARENT)]
        ),
    )
    denominator = g.count_family_outcomes([supported, unsupported])
    assert denominator.rows == 2
    assert denominator.weight == F(7, 2)
    assert denominator.unsupported_rows == 1
    assert denominator.supported_weight_share == F(6, 7)
    assert denominator.unsupported_by_reason == {
        g.UnsupportedReason.PARENT_BENEFIT: (1, F(1, 2))
    }
    with pytest.raises(g.FamilyTargetBlocked, match="parent_benefit=1"):
        g.weighted_record_total([supported, unsupported])
    with pytest.raises(g.FamilyTargetBlocked):
        g.weighted_mean_record_total([supported, unsupported])
    assert g.weighted_record_total([supported]) == 3000
    assert g.weighted_mean_record_total([supported]) == 1000


def test_evaluate_family_does_not_swallow_invalid_inputs():
    with pytest.raises(g.InvalidFamilyInput):
        g.evaluate_family(
            "x",
            1,
            lambda: _family(
                _survivor_state(), [g.Beneficiary("S", g.Role.SPOUSE)]
            ),
        )


def test_duplicate_outcome_keys_are_refused():
    outcome = g.evaluate_family(
        "a", 1, lambda: _family(_retired(1000, 1500), [])
    )
    with pytest.raises(ValueError, match="Duplicate"):
        g.count_family_outcomes([outcome, outcome])
