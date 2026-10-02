"""Extract the SSA sources behind the G2 lifetime-earnings measures.

Package G2 of the NASI follow-ups (group breakdowns of the four blind
tests) needs three external inputs that the repository did not hold:

* the OASDI payroll tax rate schedule from 1937 (SSA OACT, "Social
  Security Tax Rates", ``oasdiRates.html``);
* the trust fund interest rates from 1940, both the effective rate
  earned by the combined OASI and DI trust funds and the average annual
  special-issue rate on new issues (SSA OACT, "Average and Effective
  Interest Rates", ``annualinterestrates.html``), cross-checked against
  the two per-fund effective-rate pages (``effectiveRates.html`` for
  1980 on and ``effectiveRts1940-79.html``);
* the verbatim MINT8 definitions of the lifetime-earnings quintile rows
  (SSA, "MINT8 Table User Guide", ``user-guide.html``).

Every HTML source is the exact HTTP 200 response body fetched from ssa.gov on
2026-10-01 with ``curl -A 'Wget/1.21.4'`` (ssa.gov refuses some default
clients).  The pages carry a per-request Akamai mPulse script in
``<head>``, so a second fetch has different bytes; two fetches taken
minutes apart on 2026-10-01 parsed to identical tables.  The committed
bytes are pinned by SHA-256 below and verified before parsing.

``ssa_effective_interest_rates_2014.json`` (the M7 vintage file, 1980-2013)
is not edited.  The new rate file is a 2026 vintage: it must not be used
by any code path bound to the M7 2014 information boundary
(``engine.refit.validate_external_vintage`` rejects vintage 2026).

The MINT8 table row-group labels ("Current-law initial AIME quintile",
...) are not on the user guide page. They are read from the committed,
SHA-256-pinned label-only extraction of SSA's payroll-tax option table
made by the MINT-categories lane (no data cell was extracted); its
provenance is recorded in :data:`MINT8_TABLE_LABEL_PROVENANCE`. The source
guide and label extraction are certified 2026-04-01, a later version
than the 2025-10-01 guide identified in the G2 brief.

Run from the repository root::

    .venv/bin/python scripts/extract_lifetime_measure_sources.py

Add ``--check`` to verify all artifacts without rewriting them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXTERNAL = ROOT / "data" / "external"

RETRIEVAL_DATE = "2026-10-01T22:31:33Z"
FETCH_METHOD = (
    "Direct HTTPS GET of the live ssa.gov page with curl -A "
    "'Wget/1.21.4' on 2026-10-01 (HTTP 200, content-type text/html; "
    "charset=UTF-8; response Date header Thu, 01 Oct 2026 22:31:33-34 "
    "GMT). The body is committed byte for byte. A per-request Akamai "
    "mPulse script in <head> changes between fetches; an earlier fetch "
    "the same day parsed to the identical tables."
)
ACQUIRED_BY = (
    "Claude Code (Opus 5.5), NASI follow-up package G2 "
    "(branch nasi/g2-lifetime-measures)"
)

#: Committed source bodies, each pinned by SHA-256 and length.
SOURCES: dict[str, dict[str, Any]] = {
    "trust_fund_interest_rates": {
        "file": "ssa_trust_fund_interest_rates_2026.source.html",
        "url": "https://www.ssa.gov/oact/ProgData/annualinterestrates.html",
        "title": "Average and Effective Interest Rates",
        "sha256": (
            "7c11df685faaf0602dd77c5e4e124d64709e8cffd58e463d938f35e7254a0d18"
        ),
        "bytes": 41498,
    },
    "effective_rates_1980_on": {
        "file": "ssa_effective_interest_rates_1980_2025.source.html",
        "url": "https://www.ssa.gov/oact/ProgData/effectiveRates.html",
        "title": "Effective Interest Rates",
        "sha256": (
            "eaa8870898da2907bbc39da55d6a4c14f349e38c518aefb0ff87be2ddae09322"
        ),
        "bytes": 39756,
    },
    "effective_rates_1940_1979": {
        "file": "ssa_effective_interest_rates_1940_1979.source.html",
        "url": "https://www.ssa.gov/oact/ProgData/effectiveRts1940-79.html",
        "title": "Effective Interest Rates, 1940-79 (historical document)",
        "sha256": (
            "fb16fdaff44b3427eec2216740734792aab3b94e2851acde57c26e4057094e3d"
        ),
        "bytes": 19037,
    },
    "oasdi_tax_rates": {
        "file": "ssa_oasdi_tax_rates_2026.source.html",
        "url": "https://www.ssa.gov/oact/ProgData/oasdiRates.html",
        "title": "Social Security Tax Rates",
        "sha256": (
            "7aad3e899ab2ee4e2dfd91c2dc9208c79e40bf4cb7f3315867a11ba7efd8a9a4"
        ),
        "bytes": 41837,
    },
    "mint8_user_guide": {
        "file": "ssa_mint8_user_guide_2026.source.html",
        "url": "https://www.ssa.gov/policy/docs/projections/user-guide.html",
        "title": "MINT8 Table User Guide",
        "sha256": (
            "8d5bc3f0de17831c2ed07383003257a63bb657df179d0c54868fda052f23f100"
        ),
        "bytes": 73967,
    },
    "mint8_table_row_labels": {
        "file": "mint8_row_categories_2026.source.json",
        "url": (
            "https://www.ssa.gov/policy/docs/projections/policy-options/"
            "increase-payroll-tax-rate.html"
        ),
        "title": "MINT8 payroll-tax option table labels (labels only)",
        "sha256": (
            "23fbfbc8dbc14b06144a83bf0583ea0a6c89505638f3f7dc5fd6b34a3a4ac650"
        ),
        "bytes": 37524,
    },
}

#: Every rate is located by its named table, year/period row and column;
#: definitions are located by paragraph id or an exact identifying sentence.
SOURCE_LOCATORS = {
    "trust_fund_interest_rates": (
        "table caption: Average annual special-issue interest rates on "
        "new issues and effective annual interest rates (percent); Year "
        "row; Average and Effective columns; definition paragraphs above "
        "the table"
    ),
    "effective_rates_1980_on": (
        "table caption: Effective Interest Rates Earned By the Invested "
        "Assets of the OASI and DI Trust Funds [Percent]; Calendar year "
        "row; OASI, DI and OASDI columns"
    ),
    "effective_rates_1940_1979": (
        "table caption: Estimated Effective Interest Rates Earned By the "
        "Assets of the OASI and DI Trust Funds, 1940-79[Percent]; Calendar "
        "year row in either panel; OASI, DI and OASDI columns"
    ),
    "oasdi_tax_rates": (
        "table summary: Tax rate table for Social Security trust funds; "
        "Calendar years period row; OASI, DI and Total columns under "
        "employee/employer-each and self-employed headers; footnote "
        "anchors fna-fnd"
    ),
    "mint8_user_guide": (
        "meta DCTERMS:dateCertified; paragraphs id=AIME, lifetime-tax, "
        "lifetime-tax-shared and taxes; other paragraphs identified by "
        "the exact sentences in MINT8_PARAGRAPHS"
    ),
    "mint8_table_row_labels": (
        "label-only JSON: dateCertified; tables.13 through tables.20; "
        "groups whose group is Current-law initial AIME quintile, "
        "Lifetime payroll tax quintile or Lifetime payroll tax quintile "
        "(shared); their labels arrays"
    ),
}

INTEREST_OUT = EXTERNAL / "ssa_trust_fund_interest_rates_2026.json"
TAX_OUT = EXTERNAL / "ssa_oasdi_tax_rates_2026.json"
MINT8_OUT = EXTERNAL / "mint8_lifetime_quintile_definitions.json"
PROVENANCE_OUT = EXTERNAL / "lifetime_measure_sources.provenance.json"

INTEREST_SCHEMA = "ssa_trust_fund_interest_rates.v1"
TAX_SCHEMA = "ssa_oasdi_tax_rates.v1"
MINT8_SCHEMA = "mint8_lifetime_quintile_definitions.v1"
PROVENANCE_SCHEMA = "external_source_provenance_set.v1"

VINTAGE_YEAR = 2026
FIRST_INTEREST_YEAR = 1940
LATEST_INTEREST_YEAR = 2025
INTEREST_CAPTION = (
    "Average annual special-issue interest rates on new issues and "
    "effective annual interest rates (percent)"
)
INTEREST_HEADERS = ("Year", "Average", "Effective")
EFFECTIVE_1980_CAPTION = (
    "Effective Interest Rates Earned By the Invested Assets of the OASI "
    "and DI Trust Funds [Percent]"
)
EFFECTIVE_1940_CAPTION = (
    "Estimated Effective Interest Rates Earned By the Assets of the OASI "
    "and DI Trust Funds, 1940-79[Percent]"
)
EFFECTIVE_HEADERS = ("Calendar year", "OASI", "DI", "OASDI")
EFFECTIVE_1940_HEADERS = ("Calendaryear", "OASI", "DI", "OASDI")
INTEREST_DEFINITIONS = {
    "average_new_issue": (
        "The average special-issue interest rate for a calendar year is "
        "the average of the 12 monthly interest rates on new issues "
        "during the year."
    ),
    "effective_oasdi": (
        "An effective interest rate for a calendar year is the interest "
        "earned in that year divided by the average level of assets held "
        "during the year. This rate reflects the entire portfolio of "
        "securites held by the Social Security trust funds"
    ),
}

TAX_SUMMARY = "Tax rate table for Social Security trust funds"
TAX_GROUP_HEADERS = (
    "Tax rate for employees and employers, each",
    "Tax rate for self-employed workers",
)
TAX_PREAMBLE_SENTENCE = (
    "The rates shown reflect the amounts received by the trust funds."
)
FIRST_TAX_YEAR = 1937
OPEN_ENDED_TAX_YEAR = 2019

#: Footnote sentences that set an effective employee rate below the
#: trust-fund rate for every covered employee in a year (the only footnote
#: provisions that apply to wage earners as a class).  Each value is
#: parsed from its quoted sentence, and the quote is asserted verbatim.
PAID_RATE_QUOTES: dict[str, dict[str, Any]] = {
    "a": {
        "years": (1984,),
        "quote": (
            "resulting in an effective employee tax rate of 5.4 percent"
        ),
        "pattern": r"effective employee tax rate of (\d+\.\d) percent",
    },
    "c": {
        "years": (2011, 2012),
        "quote": (
            "resulting in a 4.2 percent effective tax rate for employees"
        ),
        "pattern": (
            r"resulting in a (\d+\.\d) percent effective tax rate for "
            r"employees"
        ),
    },
}
#: Footnote provisions recorded but not encoded: none applies to every
#: covered wage earner, or they concern self-employment, which the careers
#: frames do not separate from wages.
TAX_NOT_ENCODED = {
    "a": (
        "the 1984-89 credits against the combined OASDI and HI taxes on "
        "net earnings from self-employment (self-employment income is not "
        "separated in the careers frames)"
    ),
    "b": (
        "the self-employment deduction from 1990 (self-employment income "
        "is not separated in the careers frames)"
    ),
    "c": (
        "the 2010 employer exemption, which applied only to wages paid to "
        "certain qualified individuals hired after February 3"
    ),
    "d": (
        "the 2016-18 reallocation between OASI and DI, which leaves the "
        "OASDI total unchanged"
    ),
}

#: Paragraphs of the MINT8 user guide that G2 uses, located by element id
#: or by a sentence that only that paragraph contains.
MINT8_PARAGRAPHS: dict[str, dict[str, str]] = {
    "initial_aime_quintile": {"element_id": "AIME"},
    "lifetime_payroll_tax_quintile": {"element_id": "lifetime-tax"},
    "lifetime_payroll_tax_quintile_shared": {
        "element_id": "lifetime-tax-shared"
    },
    "current_law_payroll_taxes_quintile": {"element_id": "taxes"},
    "present_value_convention": {
        "contains": (
            "We use the Social Security Trust Fund interest rate to adjust "
            "benefits and taxes to their present values at age 62."
        )
    },
    "ten_year_birth_cohorts": {
        "contains": "We use 10-year birth cohorts to increase the sample size"
    },
    "household_income_quintile_assignment": {
        "contains": "determine the dollar thresholds for each income quintile"
    },
    "sample_size_restriction": {
        "contains": "suppress an entire characteristic subgroup"
    },
}

#: Provenance of the MINT8 cohort-table row-group labels, transcribed from
#: the label-only extraction (tables 13-20 of the payroll-tax option page).
MINT8_TABLE_LABEL_PROVENANCE = {
    "source_url": (
        "https://www.ssa.gov/policy/docs/projections/policy-options/"
        "increase-payroll-tax-rate.html"
    ),
    "retrieved_via": (
        "http://web.archive.org/web/20260519190449id_/https://www.ssa.gov/"
        "policy/docs/projections/policy-options/"
        "increase-payroll-tax-rate.html"
    ),
    "raw_sha256": (
        "3cfb6eb636cad6d062eb22734c533fb349a0bc4761014eee8f2ccb0eb6e28d8c"
    ),
    "date_certified": "2026-04-01",
    "label_file": "mint8_row_categories.json (MINT-categories lane)",
    "label_file_sha256": (
        "23fbfbc8dbc14b06144a83bf0583ea0a6c89505638f3f7dc5fd6b34a3a4ac650"
    ),
    "committed_label_file": (
        "data/external/mint8_row_categories_2026.source.json"
    ),
    "tables": "13-20 (benefit/tax ratios and initial replacement rates)",
    "note": (
        "Labels only. The lane's parser emitted th, caption and heading "
        "text and no data cell; the option table itself is not committed "
        "and supplies no input to this package."
    ),
}
MINT8_COHORT_ROW_GROUPS = {
    "initial_aime_quintile": "Current-law initial AIME quintile",
    "lifetime_payroll_tax_quintile": "Lifetime payroll tax quintile",
    "lifetime_payroll_tax_quintile_shared": (
        "Lifetime payroll tax quintile (shared)"
    ),
}
MINT8_QUINTILE_LABELS = (
    "Highest",
    "Second highest",
    "Middle",
    "Second lowest",
    "Lowest",
)


def _normalize(text: str) -> str:
    """Collapse whitespace and unify dashes; keep every other character."""
    for dash in "‐‑‒–—−":
        text = text.replace(dash, "-")
    return " ".join(text.replace("\xa0", " ").split())


def _page_text(source: str) -> str:
    """Tag-stripped, whitespace-normalized page text."""
    return _normalize(re.sub(r"<[^>]+>", " ", source))


class _PageParser(HTMLParser):
    """Collect table rows, captions, summaries, paragraphs and footnotes."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self.captions: list[str] = []
        self.summaries: list[str] = []
        self.paragraphs: list[tuple[str | None, str]] = []
        self.footnotes: dict[str, list[str]] = {}
        self._row_stack: list[dict[str, Any]] = []
        self._caption: list[str] | None = None
        self._paragraph: tuple[str | None, list[str]] | None = None
        self._footnote: str | None = None

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = dict(attrs)
        if tag == "table" and attributes.get("summary"):
            self.summaries.append(_normalize(attributes["summary"] or ""))
        if tag == "tr":
            self._row_stack.append({"cells": [], "cell": None})
        elif tag in {"th", "td"} and self._row_stack:
            self._row_stack[-1]["cell"] = []
        elif tag == "caption":
            self._caption = []
        elif tag == "p":
            self._paragraph = (attributes.get("id"), [])
        elif tag == "a":
            match = re.fullmatch(r"fn([a-z])", attributes.get("name") or "")
            if match:
                self._footnote = match.group(1)
                if self._footnote in self.footnotes:
                    raise ValueError(f"duplicate footnote {self._footnote}")
                self.footnotes[self._footnote] = []
        elif tag == "br" and self._footnote is not None:
            self.footnotes[self._footnote].append(" ")

    def handle_data(self, data: str) -> None:
        if self._row_stack and self._row_stack[-1]["cell"] is not None:
            self._row_stack[-1]["cell"].append(data)
        if self._caption is not None:
            self._caption.append(data)
        if self._paragraph is not None:
            self._paragraph[1].append(data)
        if self._footnote is not None:
            self.footnotes[self._footnote].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"th", "td"} and self._row_stack:
            context = self._row_stack[-1]
            if context["cell"] is not None:
                context["cells"].append(_normalize("".join(context["cell"])))
                context["cell"] = None
            self._footnote = None
        elif tag == "tr" and self._row_stack:
            self.rows.append(self._row_stack.pop()["cells"])
        elif tag == "caption" and self._caption is not None:
            self.captions.append(_normalize("".join(self._caption)))
            self._caption = None
        elif tag == "p" and self._paragraph is not None:
            element_id, parts = self._paragraph
            self.paragraphs.append((element_id, _normalize("".join(parts))))
            self._paragraph = None


def read_source(key: str) -> str:
    """Return a committed source body after checking its SHA-256."""
    spec = SOURCES[key]
    raw = (EXTERNAL / spec["file"]).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != spec["sha256"] or len(raw) != spec["bytes"]:
        raise ValueError(
            f"{spec['file']} sha256 {digest} ({len(raw)} bytes) != pinned "
            f"{spec['sha256']} ({spec['bytes']} bytes); re-verify the "
            "source before rebuilding"
        )
    return raw.decode("utf-8")


def _parse(key: str) -> _PageParser:
    parser = _PageParser()
    parser.feed(read_source(key))
    parser.close()
    return parser


def _percent(text: str) -> float | None:
    """A printed percent cell; ``--`` (no such tax or fund) is None."""
    if text == "--":
        return None
    if not re.fullmatch(r"\d+\.\d+", text):
        raise ValueError(f"non-numeric rate cell {text!r}")
    return float(text)


# ---------------------------------------------------------------------------
# Trust fund interest rates
# ---------------------------------------------------------------------------
def parse_interest_rates() -> dict[int, dict[str, float | None]]:
    """Parse the combined table and cross-check the per-fund pages."""
    combined = _parse("trust_fund_interest_rates")
    if INTEREST_CAPTION not in combined.captions:
        raise ValueError(f"caption {INTEREST_CAPTION!r} not found")
    headers = sum(tuple(row) == INTEREST_HEADERS for row in combined.rows)
    if headers != 3:
        raise ValueError(f"expected three {INTEREST_HEADERS!r} panels")
    rates: dict[int, dict[str, float | None]] = {}
    for cells in combined.rows:
        if len(cells) != 3 or not re.fullmatch(r"\d{4}", cells[0]):
            continue
        year = int(cells[0])
        if year in rates:
            raise ValueError(f"duplicate year {year}")
        rates[year] = {
            "average_new_issue": _percent(cells[1]),
            "effective_oasdi": _percent(cells[2]),
        }
        if any(value is None for value in rates[year].values()):
            raise ValueError(f"{year}: missing combined interest rate")
    expected = list(range(FIRST_INTEREST_YEAR, LATEST_INTEREST_YEAR + 1))
    if sorted(rates) != expected:
        raise ValueError(f"years {sorted(rates)} != {expected}")

    per_fund: dict[int, list[float | None]] = {}
    recent = _parse("effective_rates_1980_on")
    if EFFECTIVE_1980_CAPTION not in recent.captions:
        raise ValueError(f"caption {EFFECTIVE_1980_CAPTION!r} not found")
    if sum(tuple(row) == EFFECTIVE_HEADERS for row in recent.rows) != 2:
        raise ValueError("expected two per-fund header rows (1980 on)")
    for cells in recent.rows:
        if len(cells) == 4 and re.fullmatch(r"\d{4}", cells[0]):
            year = int(cells[0])
            if year in per_fund:
                raise ValueError(f"duplicate per-fund year {year}")
            per_fund[year] = [_percent(cell) for cell in cells[1:]]
    early = _parse("effective_rates_1940_1979")
    if EFFECTIVE_1940_CAPTION not in early.captions:
        raise ValueError(f"caption {EFFECTIVE_1940_CAPTION!r} not found")
    header = (*EFFECTIVE_1940_HEADERS, "", *EFFECTIVE_1940_HEADERS)
    if sum(tuple(row) == header for row in early.rows) != 1:
        raise ValueError("expected one two-panel header row (1940-79)")
    for cells in early.rows:
        for offset in (0, 5):
            if len(cells) < offset + 4:
                continue
            match = re.fullmatch(r"(\d{4})\.*", cells[offset])
            if match:
                year = int(match.group(1))
                if year in per_fund:
                    raise ValueError(f"duplicate per-fund year {year}")
                per_fund[year] = [
                    _percent(cell) for cell in cells[offset + 1 : offset + 4]
                ]
    if sorted(per_fund) != expected:
        raise ValueError("per-fund pages do not cover 1940-2025 exactly")
    for year in expected:
        oasi, di, oasdi = per_fund[year]
        if oasi is None or oasdi is None:
            raise ValueError(f"{year}: missing OASI/OASDI interest rate")
        if (di is None) != (year < 1957):
            raise ValueError(f"{year}: DI must be absent only before 1957")
        if oasdi != rates[year]["effective_oasdi"]:
            raise ValueError(
                f"{year}: combined effective "
                f"{rates[year]['effective_oasdi']} != per-fund OASDI {oasdi}"
            )
        rates[year]["effective_oasi"] = oasi
        rates[year]["effective_di"] = di
    return rates


def build_interest() -> dict[str, Any]:
    """The trust fund interest-rate artifact (percent, as printed)."""
    rates = parse_interest_rates()
    text = _page_text(read_source("trust_fund_interest_rates"))
    for key, sentence in INTEREST_DEFINITIONS.items():
        if sentence not in text:
            raise ValueError(f"definition sentence for {key} not found")
    return {
        "schema_version": INTEREST_SCHEMA,
        "table": INTEREST_CAPTION,
        "unit": "percent",
        "vintage_year": VINTAGE_YEAR,
        "latest_observation_year": LATEST_INTEREST_YEAR,
        "series": {
            "effective_oasdi": {
                "label": "Effective (combined OASI and DI trust funds)",
                "definition": INTEREST_DEFINITIONS["effective_oasdi"],
                "source": "trust_fund_interest_rates",
            },
            "average_new_issue": {
                "label": "Average annual special-issue rate on new issues",
                "definition": INTEREST_DEFINITIONS["average_new_issue"],
                "source": "trust_fund_interest_rates",
            },
            "effective_oasi": {
                "label": "Effective (OASI trust fund)",
                "source": (
                    "effective_rates_1940_1979, effective_rates_1980_on"
                ),
            },
            "effective_di": {
                "label": "Effective (DI trust fund; none before 1957)",
                "source": (
                    "effective_rates_1940_1979, effective_rates_1980_on"
                ),
            },
        },
        "vintage_note": (
            "Fetched 2026-10-01; covers 1940-2025. A post-2014 vintage, so "
            "not for code bound to the M7 2014 information boundary."
        ),
        "validation": {
            "first_observation_year": FIRST_INTEREST_YEAR,
            "latest_observation_year": LATEST_INTEREST_YEAR,
            "n_observations": len(rates),
            "continuous_calendar_years": True,
            "combined_effective_equals_per_fund_oasdi": True,
        },
        "build": {
            "built_by": "scripts/extract_lifetime_measure_sources.py",
            "sources": [
                "trust_fund_interest_rates",
                "effective_rates_1980_on",
                "effective_rates_1940_1979",
            ],
            "provenance_file": (
                "data/external/lifetime_measure_sources.provenance.json"
            ),
        },
        "data": {str(year): rates[year] for year in sorted(rates)},
    }


# ---------------------------------------------------------------------------
# OASDI tax rates
# ---------------------------------------------------------------------------
def _period(label: str) -> tuple[int, int | None, list[str]]:
    """``"1937-49"`` -> (1937, 1949, []); ``"2019 and later b"`` -> open."""
    match = re.fullmatch(
        r"(\d{4})(?:-(\d{2}))?( and later)?((?: ?,? ?[a-d])*)", label
    )
    if not match:
        raise ValueError(f"unparsed period label {label!r}")
    first = int(match.group(1))
    last: int | None
    if match.group(3):
        last = None
    elif match.group(2):
        last = (first // 100) * 100 + int(match.group(2))
        if last < first:
            raise ValueError(f"period {label!r} runs backwards")
    else:
        last = first
    notes = re.findall(r"[a-d]", match.group(4) or "")
    if len(notes) != len(set(notes)):
        raise ValueError(f"duplicate footnotes in period {label!r}")
    return first, last, notes


def parse_tax_rates() -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Parse the rate rows and footnotes; check labels and coverage."""
    page = _parse("oasdi_tax_rates")
    if TAX_SUMMARY not in page.summaries:
        raise ValueError(f"table summary {TAX_SUMMARY!r} not found")
    flat = [cell for row in page.rows for cell in row]
    for label in TAX_GROUP_HEADERS:
        if label not in flat:
            raise ValueError(f"header {label!r} not found")
    if ["OASI", "DI", "Total", "OASI", "DI", "Total"] not in page.rows:
        raise ValueError("OASI/DI/Total header row not found")
    rows: list[dict[str, Any]] = []
    for cells in page.rows:
        if len(cells) != 7 or not re.match(r"\d{4}", cells[0]):
            continue
        first, last, notes = _period(cells[0])
        values = [_percent(cell) for cell in cells[1:]]
        each = dict(zip(("oasi", "di", "total"), values[:3], strict=True))
        self_employed = dict(
            zip(("oasi", "di", "total"), values[3:], strict=True)
        )
        if each["total"] is None or each["oasi"] is None:
            raise ValueError(f"{cells[0]}: no employee/employer total")
        parts = [part for part in (each["oasi"], each["di"]) if part]
        if abs(sum(parts) - each["total"]) > 1e-9:
            raise ValueError(f"{cells[0]}: OASI + DI != total")
        if any(value is not None for value in self_employed.values()):
            if self_employed["total"] is None or self_employed["oasi"] is None:
                raise ValueError(f"{cells[0]}: incomplete self-employed rate")
            parts = [
                part
                for part in (self_employed["oasi"], self_employed["di"])
                if part is not None
            ]
            if abs(sum(parts) - self_employed["total"]) > 1e-9:
                raise ValueError(
                    f"{cells[0]}: self-employed OASI + DI != total"
                )
        rows.append(
            {
                "period": cells[0],
                "first_year": first,
                "last_year": last,
                "footnotes": notes,
                "employee_employer_each": each,
                "self_employed": self_employed,
            }
        )
    if not rows:
        raise ValueError("the tax table contains no rate rows")
    expected_first = FIRST_TAX_YEAR
    for index, row in enumerate(rows):
        if row["first_year"] != expected_first:
            raise ValueError(
                f"tax periods not contiguous at {row['period']!r}"
            )
        if row["last_year"] is None:
            if index != len(rows) - 1:
                raise ValueError("open-ended period is not the last row")
            break
        expected_first = row["last_year"] + 1
    last_row = rows[-1]
    if (
        last_row["first_year"] != OPEN_ENDED_TAX_YEAR
        or last_row["last_year"] is not None
    ):
        raise ValueError("the last row must be '2019 and later'")
    footnotes = {}
    for key, parts in sorted(page.footnotes.items()):
        text = _normalize("".join(parts))
        # The anchor's own superscript marker opens each footnote.
        if not text.startswith(f"{key} "):
            raise ValueError(f"footnote {key} does not open with its marker")
        footnotes[key] = text[len(key) + 1 :]
    if sorted(footnotes) != ["a", "b", "c", "d"]:
        raise ValueError(f"footnotes {sorted(footnotes)} != a-d")
    return rows, footnotes


def _paid_adjustments(
    rows: list[dict[str, Any]], footnotes: dict[str, str]
) -> list[dict[str, Any]]:
    adjustments = []
    for key, spec in PAID_RATE_QUOTES.items():
        text = footnotes[key]
        if spec["quote"] not in text:
            raise ValueError(f"footnote {key} quote not found")
        match = re.search(spec["pattern"], text)
        if not match:
            raise ValueError(f"footnote {key} rate not parsed")
        employee = float(match.group(1))
        for year in spec["years"]:
            row = next(
                row
                for row in rows
                if row["first_year"] <= year
                and (row["last_year"] is None or year <= row["last_year"])
            )
            if key not in row["footnotes"]:
                raise ValueError(f"{year}: row lacks footnote {key}")
            adjustments.append(
                {
                    "year": year,
                    "footnote": key,
                    "quote": spec["quote"],
                    "employee_effective_rate": employee,
                    "employer_rate": row["employee_employer_each"]["total"],
                }
            )
    return adjustments


def build_tax() -> dict[str, Any]:
    """The OASDI tax rate artifact (percent of taxable earnings)."""
    rows, footnotes = parse_tax_rates()
    if TAX_PREAMBLE_SENTENCE not in _page_text(read_source("oasdi_tax_rates")):
        raise ValueError("the trust-fund preamble sentence is missing")
    return {
        "schema_version": TAX_SCHEMA,
        "table": TAX_SUMMARY,
        "unit": "percent of taxable earnings",
        "vintage_year": VINTAGE_YEAR,
        "rates_reflect": TAX_PREAMBLE_SENTENCE,
        "rows": rows,
        "footnotes": footnotes,
        "paid_rate_adjustments": _paid_adjustments(rows, footnotes),
        "not_encoded": TAX_NOT_ENCODED,
        "validation": {
            "first_year": FIRST_TAX_YEAR,
            "open_ended_from": OPEN_ENDED_TAX_YEAR,
            "n_rows": len(rows),
            "contiguous_periods": True,
            "oasi_plus_di_equals_total": True,
        },
        "build": {
            "built_by": "scripts/extract_lifetime_measure_sources.py",
            "sources": ["oasdi_tax_rates"],
            "provenance_file": (
                "data/external/lifetime_measure_sources.provenance.json"
            ),
        },
    }


# ---------------------------------------------------------------------------
# MINT8 definitions
# ---------------------------------------------------------------------------
def parse_mint8_labels() -> tuple[dict[str, str], tuple[str, ...]]:
    """Read only the cleared label JSON and verify every cohort table.

    The cleared extraction contains headings, captions and labels, never
    outcome cells. All eight cohort tables must have the same lifetime
    dimension labels and quintile ordering. The archived option-table
    body is neither read nor needed to reproduce this artifact.
    """
    document = json.loads(read_source("mint8_table_row_labels"))
    source_record = MINT8_TABLE_LABEL_PROVENANCE
    for field, provenance_field in (
        ("source_url", "source_url"),
        ("retrieved_via", "retrieved_via"),
        ("raw_sha256", "raw_sha256"),
        ("dateCertified", "date_certified"),
    ):
        if document.get(field) != source_record[provenance_field]:
            raise ValueError(f"label source {field} disagrees with provenance")
    if not document.get("note", "").startswith("LABELS ONLY."):
        raise ValueError("the label extraction must be marked LABELS ONLY")
    names: dict[str, str] = {}
    labels: tuple[str, ...] | None = None
    for number in range(13, 21):
        groups = document["tables"][str(number)]["groups"]
        for key, section in MINT8_COHORT_ROW_GROUPS.items():
            matches = [group for group in groups if group["group"] == section]
            if len(matches) != 1:
                raise ValueError(
                    f"table {number}: {section!r} has {len(matches)} matches"
                )
            names[key] = matches[0]["group"]
            actual = tuple(matches[0]["labels"])
            if actual != MINT8_QUINTILE_LABELS:
                raise ValueError(f"table {number}: quintile labels changed")
            labels = actual
    if labels is None:
        raise ValueError("no cohort quintile labels were extracted")
    return names, labels


def build_mint8() -> dict[str, Any]:
    """Verbatim MINT8 definitions used by the lifetime-earnings rows."""
    page = _parse("mint8_user_guide")
    certified = re.search(
        r'<meta name="DCTERMS:dateCertified" content="([0-9-]+)"',
        read_source("mint8_user_guide"),
    )
    if not certified:
        raise ValueError("dateCertified meta tag not found")
    row_groups, quintile_labels = parse_mint8_labels()
    definitions: dict[str, dict[str, str]] = {}
    for key, locator in MINT8_PARAGRAPHS.items():
        if "element_id" in locator:
            found = [
                text
                for element_id, text in page.paragraphs
                if element_id == locator["element_id"]
            ]
        else:
            found = [
                text
                for _, text in page.paragraphs
                if locator["contains"] in text
            ]
        if len(found) != 1:
            raise ValueError(f"{key}: {len(found)} paragraphs match")
        definitions[key] = {**locator, "text": found[0]}
    return {
        "schema_version": MINT8_SCHEMA,
        "document": SOURCES["mint8_user_guide"]["title"],
        "date_certified": certified.group(1),
        "definitions": definitions,
        "cohort_table_row_groups": row_groups,
        "quintile_labels_high_to_low": list(quintile_labels),
        "cohort_table_label_provenance": MINT8_TABLE_LABEL_PROVENANCE,
        "build": {
            "built_by": "scripts/extract_lifetime_measure_sources.py",
            "sources": ["mint8_user_guide", "mint8_table_row_labels"],
            "provenance_file": (
                "data/external/lifetime_measure_sources.provenance.json"
            ),
        },
    }


def build_provenance() -> dict[str, Any]:
    """Provenance for the five HTML captures and cleared label extraction."""
    for key in SOURCES:
        read_source(key)
    return {
        "schema_version": PROVENANCE_SCHEMA,
        "source": "Social Security Administration",
        "retrieval_date": RETRIEVAL_DATE,
        "fetch_method": FETCH_METHOD,
        "acquired_by": ACQUIRED_BY,
        "sources": {
            key: {
                "committed_source_file": f"data/external/{spec['file']}",
                "source_url": spec["url"],
                "document": spec["title"],
                "source_sha256": spec["sha256"],
                "source_length_bytes": spec["bytes"],
                "locator": SOURCE_LOCATORS[key],
                "acquisition": (
                    "Copied byte for byte from the cleared MINT-categories "
                    "lane's followup/inputs/mint/mint8_row_categories.json; "
                    "label-only extraction of the archived source named "
                    "in MINT8_TABLE_LABEL_PROVENANCE, never a table body."
                    if key == "mint8_table_row_labels"
                    else FETCH_METHOD
                ),
            }
            for key, spec in SOURCES.items()
        },
        "consumed_by": {
            "scripts/extract_lifetime_measure_sources.py": [
                "data/external/ssa_trust_fund_interest_rates_2026.json",
                "data/external/ssa_oasdi_tax_rates_2026.json",
                "data/external/mint8_lifetime_quintile_definitions.json",
            ]
        },
        "reproducible": (
            "parsed deterministically from the committed, sha256-verified "
            "HTML bodies; no network or wall-clock timestamp is used"
        ),
    }


def render(document: dict[str, Any]) -> str:
    """The committed JSON text of an artifact."""
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def build_all() -> dict[Path, dict[str, Any]]:
    """Every artifact this script writes, keyed by output path."""
    return {
        PROVENANCE_OUT: build_provenance(),
        INTEREST_OUT: build_interest(),
        TAX_OUT: build_tax(),
        MINT8_OUT: build_mint8(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify byte identity without writing any artifact.",
    )
    args = parser.parse_args()
    for path, document in build_all().items():
        rendered = render(document)
        if args.check:
            if (
                not path.is_file()
                or path.read_text(encoding="utf-8") != rendered
            ):
                parser.error(f"{path.relative_to(ROOT)} needs rebuilding")
        else:
            path.write_text(rendered, encoding="utf-8")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        action = "verified" if args.check else "wrote"
        print(f"{action} {path.relative_to(ROOT)} sha256 {digest}")


if __name__ == "__main__":
    main()
