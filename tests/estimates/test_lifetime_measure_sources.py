"""The captured SSA sources behind the G2 lifetime-earnings measures.

Reader-free: these tests read only committed source bodies and their
extractions (SSA OACT tax and interest-rate pages, the MINT8 Table User
Guide), never PSID data and never a comparator source.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import pandas as pd
import pytest

from populace_dynamics.engine.refit import validate_external_vintage
from populace_dynamics.estimates import lifetime_measures as lm
from populace_dynamics.ss.params import SSAParameters

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
EXTERNAL = ROOT / "data" / "external"
VINTAGE_2014 = EXTERNAL / "ssa_effective_interest_rates_2014.json"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import extract_lifetime_measure_sources as extractor  # noqa: E402


@pytest.mark.parametrize("key", sorted(extractor.SOURCES))
def test_sources_have_their_pinned_sha256_and_length(key):
    spec = extractor.SOURCES[key]
    raw = (EXTERNAL / spec["file"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == spec["sha256"]
    assert len(raw) == spec["bytes"]


def test_extractions_rebuild_byte_for_byte():
    for path, document in extractor.build_all().items():
        assert extractor.render(document) == path.read_text(encoding="utf-8")


def test_module_pins_match_the_committed_extractions():
    for path, pinned in (
        (lm.OASDI_TAX_RATES_PATH, lm.OASDI_TAX_RATES_SHA256),
        (
            lm.TRUST_FUND_INTEREST_RATES_PATH,
            lm.TRUST_FUND_INTEREST_RATES_SHA256,
        ),
        (lm.MINT8_DEFINITIONS_PATH, lm.MINT8_DEFINITIONS_SHA256),
    ):
        assert path.parent == EXTERNAL
        assert hashlib.sha256(path.read_bytes()).hexdigest() == pinned


def test_provenance_names_every_source_and_output():
    record = json.loads(extractor.PROVENANCE_OUT.read_text())
    assert record["schema_version"] == "external_source_provenance_set.v1"
    assert set(record["sources"]) == set(extractor.SOURCES)
    for key, entry in record["sources"].items():
        assert entry["source_sha256"] == extractor.SOURCES[key]["sha256"]
        assert entry["source_url"].startswith("https://www.ssa.gov/")
        assert entry["locator"] == extractor.SOURCE_LOCATORS[key]
        assert entry["acquisition"]
    outputs = record["consumed_by"][
        "scripts/extract_lifetime_measure_sources.py"
    ]
    assert sorted(outputs) == sorted(
        f"data/external/{path.name}"
        for path in (
            extractor.INTEREST_OUT,
            extractor.TAX_OUT,
            extractor.MINT8_OUT,
        )
    )


def test_extractor_refuses_changed_source_bytes(tmp_path, monkeypatch):
    spec = extractor.SOURCES["oasdi_tax_rates"]
    changed = tmp_path / spec["file"]
    changed.write_bytes((EXTERNAL / spec["file"]).read_bytes() + b" ")
    monkeypatch.setattr(extractor, "EXTERNAL", tmp_path)
    with pytest.raises(ValueError, match="re-verify the source"):
        extractor.read_source("oasdi_tax_rates")


def _tamper_page(monkeypatch, key, change):
    """INVENTED parser perturbation; the committed bytes stay unchanged."""
    original = extractor._parse

    def parse(source_key):
        page = original(source_key)
        if source_key == key:
            change(page)
        return page

    monkeypatch.setattr(extractor, "_parse", parse)


# ---------------------------------------------------------------------------
# Interest rates
# ---------------------------------------------------------------------------
def test_interest_rates_cover_1940_2025_and_pin_rows():
    data = json.loads(extractor.INTEREST_OUT.read_text())["data"]
    assert [int(year) for year in data] == list(range(1940, 2026))
    assert data["1940"] == {
        "average_new_issue": 2.5,
        "effective_oasdi": 2.4,
        "effective_oasi": 2.4,
        "effective_di": None,
    }
    assert data["1957"]["effective_di"] == 2.3
    assert data["2025"] == {
        "average_new_issue": 4.3,
        "effective_oasdi": 2.6,
        "effective_oasi": 2.5,
        "effective_di": 3.6,
    }


def test_effective_rates_agree_with_the_committed_2014_vintage():
    """Differential: two captures, 12 years apart, of the same SSA series."""
    old = json.loads(VINTAGE_2014.read_text())["data"]
    new = json.loads(extractor.INTEREST_OUT.read_text())["data"]
    for year, row in old.items():
        assert new[year]["effective_oasdi"] == row["oasdi"]
        assert new[year]["effective_oasi"] == row["oasi"]
        assert new[year]["effective_di"] == row["di"]


def test_interest_file_is_a_post_boundary_vintage():
    doc = json.loads(extractor.INTEREST_OUT.read_text())
    assert doc["vintage_year"] == 2026
    with pytest.raises(ValueError, match="post-T"):
        validate_external_vintage(
            doc["schema_version"], doc["vintage_year"], boundary_year=2014
        )


@pytest.mark.parametrize(
    ("source", "match"),
    [
        ("trust_fund_interest_rates", "duplicate year"),
        ("effective_rates_1980_on", "duplicate per-fund year"),
        ("effective_rates_1940_1979", "duplicate per-fund year"),
    ],
)
def test_interest_parser_refuses_duplicate_year(monkeypatch, source, match):
    def duplicate(page):
        row = next(row for row in page.rows if row and row[0].startswith("19"))
        page.rows.append(row[:])

    _tamper_page(monkeypatch, source, duplicate)
    with pytest.raises(ValueError, match=match):
        extractor.parse_interest_rates()


def test_interest_parser_refuses_disagreeing_tables(monkeypatch):
    def disagree(page):
        row = next(row for row in page.rows if row[0] == "2025")
        row[-1] = "99.9"  # INVENTED disagreement, not a source rate.

    _tamper_page(monkeypatch, "effective_rates_1980_on", disagree)
    with pytest.raises(ValueError, match="combined effective"):
        extractor.parse_interest_rates()


def test_interest_parser_refuses_missing_required_rate(monkeypatch):
    def missing(page):
        row = next(row for row in page.rows if row[0] == "2025")
        row[1] = "--"

    _tamper_page(monkeypatch, "trust_fund_interest_rates", missing)
    with pytest.raises(ValueError, match="missing combined interest rate"):
        extractor.parse_interest_rates()


@pytest.mark.parametrize("series", list(lm.InterestSeries))
def test_interest_loader_reads_each_series(series):
    rates = lm.load_trust_fund_interest_rates(series=series)
    assert rates.series == series.value
    assert rates.covers(1940) and rates.covers(2025)
    assert not rates.covers(2026)
    expected = {
        lm.InterestSeries.EFFECTIVE_OASDI: 0.026,
        lm.InterestSeries.AVERAGE_NEW_ISSUE: 0.043,
    }[series]
    assert rates.rate_for(2025) == pytest.approx(expected)
    assert rates.provenance["sha256"] == lm.TRUST_FUND_INTEREST_RATES_SHA256


def test_loaders_refuse_a_changed_extraction(tmp_path):
    changed = tmp_path / "rates.json"
    changed.write_text(lm.OASDI_TAX_RATES_PATH.read_text() + " ")
    with pytest.raises(ValueError, match="pinned"):
        lm.load_oasdi_tax_rates(changed)
    with pytest.raises(ValueError, match="pinned"):
        lm.load_trust_fund_interest_rates(changed)


# ---------------------------------------------------------------------------
# Tax rates
# ---------------------------------------------------------------------------
def test_tax_schedule_rows_and_footnotes():
    doc = json.loads(extractor.TAX_OUT.read_text())
    assert doc["rates_reflect"] == (
        "The rates shown reflect the amounts received by the trust funds."
    )
    assert doc["rows"][0]["period"] == "1937-49"
    assert doc["rows"][-1]["period"] == "2019 and later b"
    assert doc["rows"][-1]["last_year"] is None
    assert sorted(doc["footnotes"]) == ["a", "b", "c", "d"]
    assert doc["footnotes"]["a"].startswith("In 1984 only")
    adjustments = {
        row["year"]: row["employee_effective_rate"]
        for row in doc["paid_rate_adjustments"]
    }
    assert adjustments == {1984: 5.4, 2011: 4.2, 2012: 4.2}


@pytest.mark.parametrize(
    ("year", "received", "paid"),
    [
        (1937, 2.0, 2.0),
        (1949, 2.0, 2.0),
        (1950, 3.0, 3.0),
        (1968, 7.6, 7.6),
        (1983, 10.8, 10.8),
        (1984, 11.4, 11.1),
        (1990, 12.4, 12.4),
        (2010, 12.4, 12.4),
        (2011, 12.4, 10.4),
        (2012, 12.4, 10.4),
        (2013, 12.4, 12.4),
        (2017, 12.4, 12.4),
        (2060, 12.4, 12.4),
    ],
)
def test_combined_rates_by_basis(year, received, paid):
    trust_fund = lm.load_oasdi_tax_rates()
    employee_employer = lm.load_oasdi_tax_rates(
        basis=lm.TaxRateBasis.EMPLOYEE_EMPLOYER_PAID
    )
    assert trust_fund.combined_percent_for(year) == pytest.approx(received)
    assert employee_employer.combined_percent_for(year) == pytest.approx(paid)


def test_tax_schedule_refuses_years_before_1937():
    with pytest.raises(KeyError):
        lm.load_oasdi_tax_rates().combined_for(1936)


@pytest.mark.parametrize("problem", ["no_rows", "gap", "self_total"])
def test_tax_parser_refuses_invalid_table(monkeypatch, problem):
    def change(page):
        rows = [row for row in page.rows if len(row) == 7]
        if problem == "no_rows":
            page.rows = [row for row in page.rows if row not in rows]
        elif problem == "gap":
            page.rows.remove(rows[0])
        else:
            row = next(row for row in rows if row[-1] != "--")
            row[-1] = "99.9"  # INVENTED arithmetic mismatch.

    _tamper_page(monkeypatch, "oasdi_tax_rates", change)
    match = {
        "no_rows": "no rate rows",
        "gap": "not contiguous",
        "self_total": "self-employed OASI",
    }[problem]
    with pytest.raises(ValueError, match=match):
        extractor.parse_tax_rates()


def test_credit_rate_requires_its_exact_source_quote():
    rows, footnotes = extractor.parse_tax_rates()
    # INVENTED quote corruption; 5.4 is the captured source value.
    footnotes["a"] = footnotes["a"].replace("5.4 percent", "5.6 percent")
    with pytest.raises(ValueError, match="footnote a quote not found"):
        extractor._paid_adjustments(rows, footnotes)


def test_pv_example_on_the_captured_schedules():
    # INVENTED career: 10,000 in 2023 and 2024, born 1962 (Y = 2024), no
    # binding base.  Tax 12.4 percent = 1,240 each year; the 2023 tax
    # earns the 2024 effective rate.
    params = SSAParameters(
        nawi={y: 10_000.0 for y in range(1951, 2071)},
        wage_base={1937: 1.0e12},
        pia_factors=(0.9, 0.32, 0.15),
        fra_months_by_birth_year=[(1900, 804)],
        early_monthly_rates=(5 / 900, 5 / 1200),
        early_first_bracket_months=36,
        pe_us_revision="INVENTED",
    )
    interest = lm.load_trust_fund_interest_rates()
    careers = pd.DataFrame(
        {"person_id": [1, 1], "year": [2023, 2024], "earnings": [1e4, 1e4]}
    )
    result = lm.lifetime_payroll_tax_pv_at_62(
        careers,
        pd.DataFrame({"person_id": [1], "birth_year": [1962]}),
        params,
        shared=False,
        rates=lm.load_oasdi_tax_rates(),
        interest=interest,
    )
    expected = 1_240.0 * (1.0 + interest.rate_for(2024)) + 1_240.0
    assert result.frame.at[0, "pv_at_62"] == pytest.approx(expected)
    record = result.provenance
    assert record["tax_rates"]["sha256"] == lm.OASDI_TAX_RATES_SHA256
    assert record["interest_rates"]["series"] == "effective_oasdi"
    assert math.isclose(interest.rate_for(2024), 0.025)


# ---------------------------------------------------------------------------
# MINT8 definitions
# ---------------------------------------------------------------------------
def test_mint8_definitions_are_verbatim_and_certified():
    doc = lm.load_mint8_definitions()
    assert doc["date_certified"] == "2026-04-01"
    definitions = doc["definitions"]
    assert definitions["initial_aime_quintile"]["text"].startswith(
        "Current-Law Initial AIME Quintile: Represents an individual's "
        "average indexed monthly earnings (AIME) under current law at age 62"
    )
    assert (
        "the payroll taxes paid while married are shared equally between "
        "them" in definitions["lifetime_payroll_tax_quintile_shared"]["text"]
    )
    assert definitions["present_value_convention"]["text"].endswith(
        "We use the Social Security Trust Fund interest rate to adjust "
        "benefits and taxes to their present values at age 62."
    )
    assert "less than 100 individuals" in (
        definitions["sample_size_restriction"]["text"]
    )


def test_mint8_scheme_is_registered_and_data_driven():
    scheme = lm.load_mint8_scheme()
    assert scheme.registered
    assert [dimension.section for dimension in scheme.dimensions] == [
        "Current-law initial AIME quintile",
        "Lifetime payroll tax quintile",
        "Lifetime payroll tax quintile (shared)",
    ]
    shared = scheme.dimension("lifetime_payroll_tax_quintile_shared")
    assert shared.shared and shared.measure == "lifetime_payroll_tax_pv_at_62"
    assert shared.labels() == lm.QUINTILE_LABELS
    cells = shared.cells(pd.Series([1965, 1984]))
    assert cells.tolist() == ["1960–1969", "1980–1989"]
    provenance = lm.load_mint8_definitions()["cohort_table_label_provenance"]
    assert provenance["label_file_sha256"].startswith("23fbfbc8")
    path = ROOT / provenance["committed_label_file"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == (
        provenance["label_file_sha256"]
    )


@pytest.mark.parametrize("problem", ["date", "duplicate", "order"])
def test_mint_label_parser_refuses_changed_labels(monkeypatch, problem):
    original = extractor.read_source
    document = json.loads(original("mint8_table_row_labels"))
    if problem == "date":
        document["dateCertified"] = "INVENTED"
    else:
        groups = document["tables"]["13"]["groups"]
        group = next(
            group
            for group in groups
            if group["group"] == "Lifetime payroll tax quintile"
        )
        if problem == "duplicate":
            groups.append(group)
        else:
            group["labels"].reverse()

    def changed_source(key):
        if key == "mint8_table_row_labels":
            return json.dumps(document)
        return original(key)

    monkeypatch.setattr(extractor, "read_source", changed_source)
    with pytest.raises(ValueError):
        extractor.parse_mint8_labels()
