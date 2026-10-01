"""What a Social Security cut at trust fund depletion does to households.

ILLUSTRATIVE HOUSEHOLDS, NOT SURVEY DATA.  APPLIED TO 2026 LAW AND PRICES.
Nothing here is drawn from the PSID, the projection or any DYNASIM3 value.
The script is the second use of :mod:`populace_dynamics.bridge.policyengine_us`
(the first is ``scripts/pe_us_minimum_benefit_sample_households.py``, PR
#496, whose reviewed pieces it imports unchanged):

1. **The cut.**  The 2026 Trustees Report's Highlights (section II.A,
   committed under ``docs/analysis/pe_us_depletion_cut_20261001/sources/``
   with its fetch record) state, under intermediate assumptions, the year
   the OASI Trust Fund's reserves deplete and the share of scheduled
   benefits payable then, and the same for the hypothetical combined OASDI
   funds.  :mod:`populace_dynamics.bridge.depletion_cut` reads both numbers
   from the quoted sentences, and checks them against the page's Table
   II.A1.  The primary reform cuts each Social Security benefit in the
   household to the OASI payable share (retired-worker and spouse's
   benefits are paid from OASI); the sensitivity uses the OASDI share.  The
   cut is applied to each beneficiary's 2026 monthly benefit and rounded
   down to a whole dollar (``depletion_cut.ROUNDING_RULE``).
2. **2026 law and prices.**  The cut is applied to the households' 2026
   benefits and run through PolicyEngine-US for 2026.  It would not happen
   in 2026.  The run shows how much of a cut of that size each household
   absorbs, and how much other programs and taxes offset, under current
   tax and benefit law.
3. **Households.**  #496's low earner in its three households (A: no other
   income; B: a $4,800 pension; C: a $31,200 pension), at the current-law
   benefit #496 derives (its ``worker_benefits``, unchanged); a medium
   earner (D: 100 percent of the national average wage index for 35 years,
   claiming at full retirement age, with C's $31,200 pension), whose
   benefit this script derives with the same Track M rules (``history_pia``,
   ``claim_factor``) and the bridge's statutory COLAs; and a married
   couple (E: that worker and a spouse with no covered earnings, whose
   spouse's benefit comes from the Track B gross-benefit layer, family
   maximum included).  Each in California, Montana and Florida.
4. **Offsets.**  The bridge decomposes the change in
   ``household_net_income`` into leaves that sum exactly, in cents, to the
   net change.  Each leaf is assigned to the level of government that pays
   it (``depletion_cut.LEAF_LEVELS``), and the share of the cut that other
   programs and taxes offset is ``1 - net change / Social Security
   change``.  The runs are repeated with health coverage counted in net
   income (a sensitivity, as in #496).
5. **Checks.**  The runs use policyengine-us 2.18.0 from PyPI, and the
   script refuses any other source.  Every changed component is traced
   through PolicyEngine-US's own calculation (the float32 guard), and the
   script refuses to write if any check fails.

Outputs (JSON with provenance, a Markdown table, a chart per household as
PNG and SVG, and a summary chart of the offset shares) go to
``--out-dir`` and ``--docs-dir``.

Run from the repository root::

    POPULACE_DYNAMICS_PE_US_PYTHON=~/.venvs/policyengine-us-2.18.0/bin/python \\
    OMP_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python \\
        scripts/pe_us_depletion_cut_sample_households.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import pickle
import sys
import textwrap
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import pe_us_minimum_benefit_sample_households as minimum  # noqa: E402

from populace_dynamics.bridge import depletion_cut as dc  # noqa: E402
from populace_dynamics.bridge import policyengine_us as bridge  # noqa: E402
from populace_dynamics.min_benefit_track_m import (  # noqa: E402
    coverage,
    rules,
)
from populace_dynamics.min_benefit_track_m.policy import (  # noqa: E402
    TrackMPolicy,
)
from populace_dynamics.ss.params import load_ssa_parameters  # noqa: E402
from populace_dynamics.track_b import gross_benefits as gross  # noqa: E402

SCHEMA_VERSION = "pe_us_bridge.depletion_cut_sample_households.v1"
ILLUSTRATIVE_LABEL = "ILLUSTRATIVE HOUSEHOLDS, NOT SURVEY DATA"
PAYMENT_YEAR = minimum.PAYMENT_YEAR
OUTPUT_STEM = "pe_us_depletion_cut_sample_households"
DEFAULT_DOCS_DIR = ROOT / "docs" / "analysis" / "pe_us_depletion_cut_20261001"
SOURCES_DIRNAME = "sources"
DEFAULT_EVIDENCE_DIR = Path(
    "~/microcosm-launch-evidence/dynasim-parity-20260909/"
    "pe-us-depletion-cut-20261001"
).expanduser()
DEFAULT_OUT_DIR = DEFAULT_EVIDENCE_DIR / "outputs"
#: The full report's text and the statute pages stay outside the
#: repository; the script checks them against their recorded hashes.
DEFAULT_FULL_REPORT_TEXT = DEFAULT_EVIDENCE_DIR / "sources" / "tr2026.txt"
DEFAULT_LAW_DIR = DEFAULT_EVIDENCE_DIR / "sources"

#: The plain statement every artifact carries about the year of law.
LAW_YEAR_NOTE = (
    "Applied to 2026 benefits under 2026 tax and benefit law and prices. "
    "The cut would not happen in 2026: the Trustees project the OASI Trust "
    "Fund's reserves to deplete in 2032. This shows how much of a cut of "
    "that size each household would absorb, and how much other programs "
    "and taxes would offset, under current law. It is not a projection."
)

# ---------------------------------------------------------------------------
# The Trustees Report
# ---------------------------------------------------------------------------
TRUSTEES_REPORT_TITLE = (
    "The 2026 Annual Report of the Board of Trustees of the Federal Old-Age "
    "and Survivors Insurance and Federal Disability Insurance Trust Funds"
)
HIGHLIGHTS_FILE = "II_A_highlights.html"
FETCH_RECORD_FILE = "fetch_record.json"
LAW_FETCH_RECORD_FILE = "fetch_record_law.json"
FULL_REPORT_FILE = "tr2026.pdf"
#: SHA-256 of the text extracted from ``tr2026.pdf`` (not committed), the
#: file the script searches for the quoted sentences.
FULL_REPORT_TEXT_SHA256 = (
    "789faa11edff9427e625c092516cadd94ab4f03553da803ae9bd39f0ef6bc7c1"
)
#: Other Highlights phrases the caveats quote; each must be on the page.
CONTEXT_QUOTES = (
    "adds a temporary additional standard deduction for taxpayers over age "
    "65",
    "$58 billion from income taxation of Social Security benefits",
)
#: The primary reform's fund and the sensitivity's, by scenario name.
REFORMS: dict[str, str] = {"oasi": "OASI", "oasdi": "OASDI"}
PRIMARY = "oasi"
SCENARIOS = ("baseline", *REFORMS)
VARIANTS = minimum.VARIANTS

#: Statute text each quoted phrase must be found in (the Legal Information
#: Institute's pages, recorded in ``fetch_record_law.json``; not
#: committed).  The phrases are the ones quoted in
#: ``depletion_cut.ROUNDING_RULE`` and ``depletion_cut.LEAF_LEVELS``.
STATUTE_QUOTES: dict[str, tuple[str, tuple[str, ...]]] = {
    "lii_42_usc_415.html": (
        "42 USC 415(g)",
        (
            "The amount of any monthly benefit computed under section 402 "
            "or 423 of this title",
            "is not a multiple of $1 shall be rounded to the next lower "
            "multiple of $1",
        ),
    ),
    "lii_42_usc_1381.html": (
        "42 USC 1381",
        (
            "there are authorized to be appropriated sums sufficient to "
            "carry out this subchapter",
        ),
    ),
    "lii_42_usc_1382e.html": (
        "42 USC 1382e(d)(1)",
        (
            "pay to the Commissioner of Social Security an amount equal to "
            "the expenditures made by the Commissioner of Social Security "
            "as such supplementary payments",
        ),
    ),
    "lii_7_usc_2013.html": (
        "7 USC 2013(a)",
        (
            "shall be redeemable at face value by the Secretary through the "
            "facilities of the Treasury of the United States",
            "Subject to clause (iii), beginning in fiscal year 2028",
        ),
    ),
}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _docs_relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


class InvariantError(minimum.InvariantError):
    """A property of the run failed; nothing is written."""


def _require(condition: bool, message: object) -> None:
    # An explicit raise, not ``assert``: ``python -O`` strips asserts, and
    # these checks gate what is written.
    if not condition:
        raise InvariantError(message)


def trustees_citation(
    sources_dir: Path, full_report_text: Path | None
) -> dict[str, Any]:
    """The Trustees Report's numbers, quotes and fetch provenance.

    Reads the committed Highlights page and its fetch record, refuses a
    page whose SHA-256 or size differs from the record, takes each fund's
    quote and numbers from the page (:func:`dc.depletion_quotes`), and
    requires Table II.A1 to state the same numbers.  When
    ``full_report_text`` is given, it must have
    :data:`FULL_REPORT_TEXT_SHA256`, and each quote must appear in it; the
    page of the extracted text it appears on is recorded.
    """

    records = {
        record["file"]: record
        for record in json.loads(
            (sources_dir / FETCH_RECORD_FILE).read_text(encoding="utf-8")
        )
    }
    page = records[HIGHLIGHTS_FILE]
    data = (sources_dir / HIGHLIGHTS_FILE).read_bytes()
    _require(
        _sha256_bytes(data) == page["sha256"] and len(data) == page["bytes"],
        f"{HIGHLIGHTS_FILE} does not match its fetch record",
    )
    _require(
        page["status"] == 200, f"{HIGHLIGHTS_FILE}: HTTP {page['status']}"
    )
    text = dc.highlights_text(data.decode("utf-8"))
    quotes = dc.depletion_quotes(text)
    parsed = {
        fund: dc.parse_depletion_sentence(quote)
        for fund, quote in quotes.items()
    }
    table = dc.key_results_table(text)
    for fund, quote in parsed.items():
        _require(
            table[fund] == {"year": quote.year, "percent": quote.percent},
            f"{fund}: Table II.A1 says {table[fund]}, the sentence "
            f"{quote.year} and {quote.percent} percent",
        )
    for phrase in CONTEXT_QUOTES:
        _require(phrase in text, f"{phrase!r} is not on the Highlights page")
    report = records[FULL_REPORT_FILE]
    full_report: dict[str, Any] = {
        "url": report["url"],
        "retrieved_utc": report["retrieved_utc"],
        "status": report["status"],
        "bytes": report["bytes"],
        "sha256": report["sha256"],
        "committed": False,
        "text_extraction_sha256": FULL_REPORT_TEXT_SHA256,
        "quotes_found_on_text_page": None,
    }
    if full_report_text is not None:
        raw = full_report_text.read_bytes()
        _require(
            _sha256_bytes(raw) == FULL_REPORT_TEXT_SHA256,
            "the full report's text is not the recorded extraction",
        )
        pages = [
            " ".join(part.replace("’", "'").split())
            for part in raw.decode("utf-8").split("\f")
        ]
        found = {}
        for fund, quote in quotes.items():
            needle = " ".join(quote.replace("’", "'").split())
            hits = [i + 1 for i, part in enumerate(pages) if needle in part]
            _require(
                len(hits) == 1,
                f"{fund}'s quote is on text pages {hits} of the full report",
            )
            found[fund] = hits[0]
        full_report["text_pages"] = len(pages)
        full_report["quotes_found_on_text_page"] = found
    return {
        "report": TRUSTEES_REPORT_TITLE,
        "publisher": (
            "The Board of Trustees, Federal Old-Age and Survivors "
            "Insurance and Federal Disability Insurance Trust Funds"
        ),
        "assumptions": "intermediate",
        "section": "II.A Highlights",
        "highlights": {
            "url": page["url"],
            "retrieved_utc": page["retrieved_utc"],
            "status": page["status"],
            "bytes": page["bytes"],
            "sha256": page["sha256"],
            "client": page.get("client"),
            "file": _docs_relative(sources_dir / HIGHLIGHTS_FILE),
            "fetch_record": _docs_relative(sources_dir / FETCH_RECORD_FILE),
        },
        "quotes": {
            fund: {"text": quotes[fund], **parsed[fund].as_dict()}
            for fund in quotes
        },
        "key_results_table": table,
        "context_quotes": list(CONTEXT_QUOTES),
        "full_report": full_report,
        "primary": REFORMS[PRIMARY],
        "sensitivity": REFORMS["oasdi"],
        "fund_choice": (
            "Retired-worker and spouse's benefits are paid from the OASI "
            "Trust Fund, so the primary reform pays each benefit at the "
            "OASI payable share. The hypothetical combined OASDI funds' "
            "share is the sensitivity."
        ),
    }


def statute_sources(
    sources_dir: Path, law_dir: Path | None
) -> list[dict[str, Any]]:
    """The statute pages quoted, from their fetch record.

    When ``law_dir`` holds the pages, each must match its recorded SHA-256
    and contain every phrase :data:`STATUTE_QUOTES` lists for it.
    """

    records = json.loads(
        (sources_dir / LAW_FETCH_RECORD_FILE).read_text(encoding="utf-8")
    )
    _require(
        sorted(record["file"] for record in records) == sorted(STATUTE_QUOTES),
        "the law fetch record does not list the quoted statutes",
    )
    out = []
    for record in sorted(records, key=lambda r: r["file"]):
        citation, phrases = STATUTE_QUOTES[record["file"]]
        checked = None
        if law_dir is not None:
            data = (law_dir / record["file"]).read_bytes()
            _require(
                _sha256_bytes(data) == record["sha256"],
                f"{record['file']} does not match its fetch record",
            )
            text = dc.highlights_text(data.decode("utf-8"))
            for phrase in phrases:
                _require(
                    " ".join(phrase.split()) in text,
                    f"{citation}: {phrase!r} is not in {record['file']}",
                )
            checked = True
        out.append(
            {
                "citation": citation,
                "url": record["url"],
                "retrieved_utc": record["retrieved_utc"],
                "status": record["status"],
                "bytes": record["bytes"],
                "sha256": record["sha256"],
                "committed": False,
                "phrases": list(phrases),
                "phrases_found": checked,
            }
        )
    return out


# ---------------------------------------------------------------------------
# Benefits (this repository's rules)
# ---------------------------------------------------------------------------
#: The medium earner.  Every number here is an input chosen for the
#: illustration; everything derived from them is computed below.
MEDIUM_WORKER: dict[str, Any] = {
    "birth_year": 1954,
    "first_earnings_year": 1980,
    "earnings_years": 35,
    "share_of_average_wage_index": 1.0,
    "entitlement_year": 2020,
}
#: The medium earner's spouse: no covered earnings of their own, entitled
#: to a spouse's benefit in the year the worker is entitled.  Born a year
#: before the worker, so the spouse is past full retirement age then and
#: the benefit is not reduced for age.
SPOUSE: dict[str, Any] = {
    "birth_year": 1953,
    "spouse_benefit_entitlement_year": 2020,
    "own_covered_earnings": "none",
}
#: Benefits paid in the payment year are those for December of the year
#: before through November of the payment year (paid the following month),
#: so they reflect the COLAs determined through the year before; #496 uses
#: the same convention (``carry_pia_forward`` through ``PAYMENT_YEAR - 1``).
BENEFIT_MONTHS = (
    gross.YearMonth(PAYMENT_YEAR - 1, 12),
    *(gross.YearMonth(PAYMENT_YEAR, month) for month in range(1, 12)),
)


def low_earner_benefit(parameter_root: Path) -> dict[str, Any]:
    """#496's worker at her current-law benefit, derived as #496 derives it.

    Calls ``worker_benefits`` of ``scripts/pe_us_minimum_benefit_sample_
    households.py`` unchanged and keeps its current-law part (the minimum
    benefit there is a different reform, not used here).
    """

    worker = minimum.worker_benefits(PAYMENT_YEAR, parameter_root)
    current = worker["current_law"]
    return {
        "derivation": (
            "scripts/pe_us_minimum_benefit_sample_households.py "
            "worker_benefits(), current_law (PR #496), unchanged"
        ),
        "inputs": worker["inputs"],
        "earnings_history": worker["earnings_history"],
        "earnings_rule": worker["earnings_rule"],
        "record_years": worker["record_years"],
        "years_of_coverage": worker["years_of_coverage"],
        "pia_record": worker["pia_record"],
        "claim_factor": worker["claim_factor"],
        "months_from_full_retirement_age": worker[
            "months_from_full_retirement_age"
        ],
        "current_law": current,
        "monthly_benefit": current["monthly_benefit"],
        "rounding": worker["rounding"],
        "medicare_quarters_of_coverage": 4
        * worker["years_of_coverage"]["years"],
    }


def medium_earner_benefit(
    parameter_root: Path, rates: dict[int, float]
) -> dict[str, Any]:
    """The medium earner's current-law 2026 benefit, as #496 derives one.

    Covered earnings of :data:`MEDIUM_WORKER`'s share of the national
    average wage index in each year, rounded to the cent; years of
    coverage from ``coverage.count_coverage_years``; the PIA from
    ``rules.history_pia`` on the old-age basis; statutory COLAs to the
    payment year (``bridge.carry_pia_forward``); the claim factor from
    ``rules.claim_factor``; the monthly benefit rounded down to the dollar.
    Refuses a history above the taxable maximum (every year must count in
    full) or a claim at any age but full retirement age.
    """

    params = load_ssa_parameters(parameter_root)
    qc = coverage.load_qc_amounts()
    birth = MEDIUM_WORKER["birth_year"]
    first = MEDIUM_WORKER["first_earnings_year"]
    share = MEDIUM_WORKER["share_of_average_wage_index"]
    history = {
        year: round(share * params.nawi[year], 2)
        for year in range(first, first + MEDIUM_WORKER["earnings_years"])
    }
    for year, amount in history.items():
        _require(
            amount <= params.wage_base[year],
            f"{year}: earnings {amount} exceed the taxable maximum",
        )
    policy = TrackMPolicy()
    years = rules.record_years(
        basis=rules.BASIS_OLD_AGE,
        birth_year=birth,
        window_year=MEDIUM_WORKER["entitlement_year"],
    )
    count = coverage.count_coverage_years(
        history,
        birth_year=birth,
        through_year=years.last_year,
        qc=qc,
        nawi=params.nawi,
        policy=policy,
        gap_years=(),
    )
    pia_record = rules.history_pia(
        history,
        birth_year=birth,
        params=params,
        basis=rules.BASIS_OLD_AGE,
        window_year=years.window_year,
        policy=policy,
    )
    months_from_fra = 12 * (years.window_year - birth) - params.fra_months(
        birth
    )
    _require(
        months_from_fra == 0,
        f"the medium earner claims {months_from_fra} months from full "
        "retirement age, not at it",
    )
    claim = rules.claim_factor(birth, years.window_year, params)
    amount, steps = bridge.carry_pia_forward(
        pia_record.pia,
        rates,
        first_determination_year=years.threshold_year,
        last_determination_year=PAYMENT_YEAR - 1,
    )
    monthly = math.floor(amount * claim + 1e-9)
    counted = count.as_dict()
    return {
        "derivation": (
            "this script's medium_earner_benefit(): the steps of #496's "
            "worker_benefits() current-law path (history_pia, "
            "count_coverage_years, claim_factor, carry_pia_forward)"
        ),
        "inputs": dict(MEDIUM_WORKER),
        "earnings_history": {
            str(year): value for year, value in sorted(history.items())
        },
        "earnings_rule": (
            f"{share:.0%} of the national average wage index "
            "(ss.params.load_ssa_parameters().nawi) in each year, rounded "
            "to the cent; every year is under the taxable maximum"
        ),
        "record_years": years.as_dict(),
        "years_of_coverage": {
            "years": counted["years"],
            "counted_years": counted["counted_years"],
            "through_year": counted["through_year"],
            "note": (
                "Invented history: covered earnings in every year "
                f"{first}-{first + MEDIUM_WORKER['earnings_years'] - 1} and "
                "none after, by construction. Each counted year's earnings "
                "reach four quarters of coverage "
                "(coverage.count_coverage_years)."
            ),
        },
        "pia_record": pia_record.as_dict(),
        "claim_factor": claim,
        "months_from_full_retirement_age": months_from_fra,
        "current_law": {
            "pia_at_eligibility": pia_record.pia,
            "cola_steps": list(steps),
            "pia_payment_year": amount,
            "monthly_benefit": monthly,
            "annual_benefit": 12 * monthly,
        },
        "monthly_benefit": monthly,
        "rounding": (
            "PIA: ss.benefits.pia floors to a dime; each COLA step floors to "
            "a dime (42 USC 415(i)(2)(A)(ii)); the monthly benefit is the "
            "PIA times the claim factor (1 at full retirement age) rounded "
            "down to the dollar, as in #496"
        ),
        "medicare_quarters_of_coverage": 4 * counted["years"],
    }


def december_cola_percents(rates: dict[int, float]) -> dict[int, Fraction]:
    """Each determination year's COLA as an exact percentage in tenths.

    COLAs are rounded to the nearest one-tenth of 1 percent (42 USC
    415(i)(1)(D)); a stored fraction such as ``0.027999999999999997`` is
    read as 2.8 percent.  Refuses a rate more than a millionth of a percent
    from a tenth.
    """

    out = {}
    for year, rate in rates.items():
        exact = Fraction(repr(float(rate))) * 100
        tenths = round(exact * 10)
        _require(
            abs(exact * 10 - tenths) < Fraction(1, 10**7),
            f"COLA {year} ({rate}) is not a tenth of a percent",
        )
        out[int(year)] = Fraction(tenths, 10)
    return out


def couple_benefits(
    parameter_root: Path,
    rates: dict[int, float],
    worker: dict[str, Any],
) -> dict[str, Any]:
    """The couple's 2026 benefits from the Track B gross-benefit layer.

    The worker's record (the medium earner's PIA at eligibility, the COLAs
    since) and a spouse's benefit (42 USC 402(b)/(c), one-half of the PIA,
    after the family maximum of 403(a)) for every benefit month paid in the
    payment year (:data:`BENEFIT_MONTHS`), through
    ``track_b.gross_benefits.household_benefits``.  Refuses months that
    differ, and refuses unless the layer's worker benefit and PIA equal the
    ones :func:`medium_earner_benefit` derived (a differential check of two
    implementations).
    """

    params = load_ssa_parameters(parameter_root)
    percents = december_cola_percents(rates)
    eligibility = worker["record_years"]["threshold_year"]
    spouse_age_months = 12 * (
        SPOUSE["spouse_benefit_entitlement_year"] - SPOUSE["birth_year"]
    )
    spouse_months_early = max(
        0, params.fra_months(SPOUSE["birth_year"]) - spouse_age_months
    )
    _require(
        SPOUSE["spouse_benefit_entitlement_year"]
        >= worker["inputs"]["entitlement_year"],
        "the spouse's benefit cannot begin before the worker's",
    )
    by_month = {}
    for month in BENEFIT_MONTHS:
        record = gross.WorkerRecord(
            kind=gross.FamilyKind.RETIREMENT,
            eligibility_year=eligibility,
            eligibility_pia=Fraction(repr(worker["pia_record"]["pia"])),
            cola_percents=gross.applicable_cola_percents(
                eligibility, month, percents
            ),
            worker_reduction_months=0,
            worker_birth_year=worker["inputs"]["birth_year"],
        )
        state = gross.record_state(record, params)
        spouse = gross.Beneficiary(
            beneficiary_id="spouse",
            role=gross.Role.SPOUSE,
            reduction_months=spouse_months_early,
        )
        result = gross.household_benefits(
            {"worker": gross.HouseholdRecord("worker", state, (spouse,))},
            payment_month=month,
            params=params,
        ).records["worker"]
        row = result.by_id()["spouse"]
        by_month[str(month)] = {
            "pia": str(result.pia),
            "family_maximum": str(result.family_maximum),
            "family_maximum_binding": result.family_maximum_binding,
            "worker_monthly": result.whole_dollar_worker,
            "spouse_original_benefit": str(row.original_benefit),
            "spouse_payable": str(row.auxiliary_payable),
            "spouse_monthly": row.whole_dollar_auxiliary,
        }
    distinct = {json.dumps(v, sort_keys=True) for v in by_month.values()}
    _require(len(distinct) == 1, f"benefit months differ: {by_month}")
    first = next(iter(by_month.values()))
    _require(
        first["worker_monthly"] == worker["monthly_benefit"]
        and Fraction(first["pia"])
        == Fraction(repr(worker["current_law"]["pia_payment_year"])),
        "Track B's worker benefit differs from the medium earner's: "
        f"{first} against {worker['current_law']}",
    )
    return {
        "derivation": (
            "track_b.gross_benefits.household_benefits (Track B milestone G, "
            f"{gross.GROSS_BENEFITS_VERSION}): the worker's retirement "
            "record and a spouse's benefit, for each benefit month paid in "
            f"{PAYMENT_YEAR}"
        ),
        "spouse_inputs": dict(SPOUSE),
        "spouse_months_before_full_retirement_age": spouse_months_early,
        "benefit_months": [str(month) for month in BENEFIT_MONTHS],
        "december_cola_percents": {
            str(year): str(percents[year])
            for year in range(eligibility, PAYMENT_YEAR)
        },
        "result": first,
        "worker_monthly": first["worker_monthly"],
        "spouse_monthly": first["spouse_monthly"],
        "differential_check": (
            "Track B's worker PIA and whole-dollar benefit equal "
            "carry_pia_forward's PIA and the medium earner's benefit"
        ),
        "rounding": (
            "The spouse's original benefit is one-half of the PIA, rounded "
            "down to a dime; the family maximum (403(a)) is checked before "
            "any age reduction; each monthly benefit is rounded down to a "
            "whole dollar (Track B's whole_dollars)"
        ),
    }


# ---------------------------------------------------------------------------
# Households
# ---------------------------------------------------------------------------
#: #496's three households (A, B and C), unchanged.
LOW_EARNER_HOUSEHOLDS: tuple[dict[str, Any], ...] = tuple(
    dict(spec, worker="low_earner") for spec in minimum.HOUSEHOLDS
)
MEDIUM_HOUSEHOLDS: tuple[dict[str, Any], ...] = (
    {
        "key": "D",
        "label": "Household D",
        "description": (
            "A medium earner living alone: covered earnings of 100 percent "
            "of the national average wage index in each of the 35 years "
            "1980-2014, a retired-worker benefit from full retirement age "
            "(66, in 2020), and the same $31,200-a-year ($2,600-a-month) "
            "private pension as household C"
        ),
        "taxable_private_pension_income": 31_200.0,
        "purpose": (
            "A taxable benefit: part of the medium earner's Social Security "
            "is taxable before and after the cut"
        ),
        "worker": "medium_earner",
    },
    {
        "key": "E",
        "label": "Household E",
        "description": (
            "The same medium earner, married to a spouse a year older with "
            "no covered earnings who receives a spouse's benefit from 2020, "
            "after full retirement age; the couple has a "
            "$42,000-a-year ($3,500-a-month) private pension"
        ),
        "taxable_private_pension_income": 42_000.0,
        "purpose": (
            "A married couple filing jointly: the worker's and the spouse's "
            "benefits are each cut, and part of them is taxable before and "
            "after the cut"
        ),
        "worker": "medium_earner",
        "spouse": True,
    },
)
HOUSEHOLDS: tuple[dict[str, Any], ...] = (
    *LOW_EARNER_HOUSEHOLDS,
    *MEDIUM_HOUSEHOLDS,
)
STATES = minimum.STATES


def scheduled_benefits(
    spec: dict[str, Any], benefits: dict[str, Any]
) -> dict[str, int]:
    """Each beneficiary's scheduled 2026 monthly benefit in a household."""

    if spec["worker"] == "low_earner":
        return {"worker": benefits["low_earner"]["monthly_benefit"]}
    out = {"worker": benefits["medium_earner"]["monthly_benefit"]}
    if spec.get("spouse"):
        out["spouse"] = benefits["couple"]["spouse_monthly"]
    return out


def household_cuts(
    spec: dict[str, Any], benefits: dict[str, Any], shares: dict[str, Decimal]
) -> dict[str, dict[str, dc.BenefitCut]]:
    """Each scenario's cut of each beneficiary's benefit.

    ``shares`` maps a scenario to its payable share; the baseline's is 1,
    so its "cut" leaves every benefit as scheduled.
    """

    scheduled = scheduled_benefits(spec, benefits)
    return {
        scenario: dc.cut_household(scheduled, shares[scenario])
        for scenario in SCENARIOS
    }


def build_household(
    spec: dict[str, Any],
    state: str,
    annual: dict[str, float],
    benefits: dict[str, Any],
) -> bridge.BridgeHousehold:
    """The PolicyEngine-US household for ``spec`` in ``state``.

    A-C are #496's (``household``, unchanged).  D and E use the same common
    facts (rent, bank balance, heating or cooling costs, food preparation,
    housing take-up off).  In E the spouse's benefit enters as
    ``social_security_dependents``; in policyengine-us 2.18.0 the four
    Social Security inputs differ only in child-care and TANF income lists
    that do not reach a household without children, and
    ``social_security`` adds all four (``social_security.py:11-14``).
    """

    if spec["worker"] == "low_earner":
        return minimum.household(
            spec,
            state,
            annual["worker"],
            benefits["low_earner"]["medicare_quarters_of_coverage"],
        )
    worker = benefits["medium_earner"]
    people = [
        bridge.BridgePerson(
            person_id="worker",
            age=PAYMENT_YEAR - worker["inputs"]["birth_year"],
            social_security_retirement=annual["worker"],
            taxable_private_pension_income=spec[
                "taxable_private_pension_income"
            ],
            bank_account_assets=minimum.BANK_ACCOUNT_ASSETS,
            pre_subsidy_rent=12 * minimum.MONTHLY_RENT,
            medicare_quarters_of_coverage=worker[
                "medicare_quarters_of_coverage"
            ],
        )
    ]
    if spec.get("spouse"):
        people.append(
            bridge.BridgePerson(
                person_id="spouse",
                age=PAYMENT_YEAR - SPOUSE["birth_year"],
                social_security_dependents=annual["spouse"],
            )
        )
    ids = tuple(person.person_id for person in people)
    return bridge.BridgeHousehold(
        household_id=f"household_{spec['key'].lower()}_{state.lower()}",
        state=state,
        people=tuple(people),
        tax_units=(ids,),
        spm_units=(ids,),
        marital_units=(ids,),
        has_heating_cooling_expense=True,
        takes_up_housing_assistance=False,
        food_preparation_allowed=True,
    )


# ---------------------------------------------------------------------------
# Running PolicyEngine-US
# ---------------------------------------------------------------------------
#: #496's memo variables, and PolicyEngine-US's federal shares of the two
#: joint programs (health sensitivity only).
MEMO_VARIABLES = (
    *minimum.MEMO_VARIABLES,
    "medicaid_federal_cost",
    "msp_federal_cost",
    "ssi",
)


def _case_id(key: str, state: str, scenario: str, variant: str) -> str:
    return f"{key}_{state}_{scenario}_{variant}"


def plan_cases(
    benefits: dict[str, Any],
    shares: dict[str, Decimal],
    updates: list[dict[str, Any]],
) -> tuple[list[bridge.RunCase], list[tuple[Any, ...]]]:
    """Every household, state, scenario and variant as a PolicyEngine-US case.

    Returns the cases and the plan :func:`rows_from_result` reads them back
    with.  Each baseline case is shared by both reforms' comparisons.
    """

    cases: list[bridge.RunCase] = []
    plan = []
    for spec in HOUSEHOLDS:
        cuts = household_cuts(spec, benefits, shares)
        for state in STATES:
            overrides = {
                variant: minimum._overrides_for(state, variant, updates)
                for variant in VARIANTS
            }
            situations = {}
            for scenario in SCENARIOS:
                annual = {
                    person: float(cut.annual_payable)
                    for person, cut in cuts[scenario].items()
                }
                built = build_household(spec, state, annual, benefits)
                situations[scenario] = bridge.to_situation(built, PAYMENT_YEAR)
                for variant in VARIANTS:
                    cases.append(
                        bridge.RunCase(
                            case_id=_case_id(
                                spec["key"], state, scenario, variant
                            ),
                            situation=situations[scenario],
                            expected_state=state,
                            memo=MEMO_VARIABLES,
                            parameter_overrides=overrides[variant],
                        )
                    )
            plan.append((spec, state, cuts, situations, overrides))
    return cases, plan


def job_sha256(payload: Any) -> str:
    """SHA-256 of a job's canonical JSON (sorted keys, no whitespace)."""

    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return _sha256_bytes(text.encode("utf-8"))


def digest() -> str:
    """The pinned release's RECORD digest (#496's ``PE_US_RELEASE``)."""

    return minimum.PE_US_RELEASE["package_record_digest"]


def _trace_sha(
    traced: list[tuple[str, Any, list[str]]], overrides: dict[str, Any]
) -> str:
    return job_sha256(
        {
            "year": PAYMENT_YEAR,
            "cases": [list(case) for case in traced],
            "overrides": overrides,
            "release": digest(),
        }
    )


def run_job(cases: list[bridge.RunCase]) -> list[dict[str, Any]]:
    """The cases as the runner sends them, for :func:`job_sha256`."""

    return [
        {
            "case_id": case.case_id,
            "situation": case.situation,
            "expected_state": case.expected_state,
            "memo": list(case.memo),
            "parameter_overrides": dict(case.parameter_overrides),
        }
        for case in cases
    ]


def rows_from_result(
    plan: list[tuple[Any, ...]], result: bridge.RunResult
) -> list[dict[str, Any]]:
    """One row per household, state and reform, against the shared
    baseline: the decompositions (default and with health), memos and the
    values the float32 guard compares."""

    rows = []
    for spec, state, cuts, situations, overrides in plan:
        runs = {
            (scenario, variant): result.runs[
                _case_id(spec["key"], state, scenario, variant)
            ]
            for scenario in SCENARIOS
            for variant in VARIANTS
        }
        for reform in REFORMS:
            decompositions = {
                variant: bridge.decompose(
                    runs[("baseline", variant)].tree,
                    runs[("baseline", variant)].values,
                    runs[(reform, variant)].values,
                    reform_tree=runs[(reform, variant)].tree,
                )
                for variant in VARIANTS
            }
            rows.append(
                {
                    "household": spec["key"],
                    "label": spec["label"],
                    "state": state,
                    "reform": reform,
                    "fund": REFORMS[reform],
                    "cuts": cuts[reform],
                    "baseline_social_security_annual": float(
                        sum(
                            c.annual_payable for c in cuts["baseline"].values()
                        )
                    ),
                    "reform_social_security_annual": float(
                        sum(c.annual_payable for c in cuts[reform].values())
                    ),
                    "decomposition": decompositions["default"],
                    "with_health": decompositions["with_health"],
                    "memo": {
                        "baseline": dict(runs[("baseline", "default")].memo),
                        "reform": dict(runs[(reform, "default")].memo),
                    },
                    "memo_with_health": {
                        "baseline": dict(
                            runs[("baseline", "with_health")].memo
                        ),
                        "reform": dict(runs[(reform, "with_health")].memo),
                    },
                    "overrides": overrides,
                    "situations": {
                        "baseline": situations["baseline"],
                        "reform": situations[reform],
                    },
                    "case_ids": {
                        variant: {
                            "baseline": _case_id(
                                spec["key"], state, "baseline", variant
                            ),
                            "reform": _case_id(
                                spec["key"], state, reform, variant
                            ),
                        }
                        for variant in VARIANTS
                    },
                    "tree": runs[("baseline", "default")].tree,
                    "run_values": {
                        variant: {
                            "baseline": runs[("baseline", variant)].values,
                            "reform": runs[(reform, variant)].values,
                        }
                        for variant in VARIANTS
                    },
                }
            )
    return rows


def _decomposition(row: dict[str, Any], variant: str) -> bridge.Decomposition:
    return row["decomposition"] if variant == "default" else row["with_health"]


def trace_cases(
    rows: list[dict[str, Any]],
) -> tuple[list[tuple[str, Any, list[str]]], dict[str, Any]]:
    """The cases the float32 guard traces, and each one's overrides.

    Each case (household, state, scenario, variant) is traced once, for
    every leaf that changes in any comparison it is part of.
    """

    leaves: dict[str, set[str]] = {}
    situations: dict[str, Any] = {}
    overrides: dict[str, Any] = {}
    for row in rows:
        for variant in VARIANTS:
            changed = {
                c.variable
                for c in _decomposition(row, variant).components
                if c.change_cents
            }
            for scenario in ("baseline", "reform"):
                case_id = row["case_ids"][variant][scenario]
                leaves.setdefault(case_id, set()).update(changed)
                situations[case_id] = row["situations"][scenario]
                overrides[case_id] = row["overrides"][variant]
    cases = [
        (case_id, situations[case_id], sorted(names))
        for case_id, names in sorted(leaves.items())
    ]
    return cases, overrides


def apply_float32_guard(
    rows: list[dict[str, Any]], traces: dict[str, dict[str, Any]]
) -> None:
    """Walk each comparison's traced leaves; record what the guard finds.

    #496's guard (``minimum.float32_guard``) for comparisons that share a
    baseline.  Each comparison's changed leaves are walked with
    :func:`bridge.uncaused_changes`, and each traced leaf must equal its
    untraced value within a cent (a differential check of the traced and
    untraced runs).  Adds ``row["float32_guard"][variant]``.
    """

    for row in rows:
        for variant in VARIANTS:
            decomposition = _decomposition(row, variant)
            changed = sorted(
                c.variable for c in decomposition.components if c.change_cents
            )
            nodes = {
                scenario: traces[row["case_ids"][variant][scenario]]
                for scenario in ("baseline", "reform")
            }
            for scenario, traced_nodes in nodes.items():
                untraced = row["run_values"][variant][scenario]
                for name in changed:
                    traced = math.fsum(
                        traced_nodes[f"{name}@{PAYMENT_YEAR}"].value
                    )
                    if abs(traced - untraced[name]) >= bridge.CENT_TOLERANCE:
                        raise InvariantError(
                            f"{row['household']}-{row['state']} "
                            f"{row['reform']} {scenario} {variant}: {name} "
                            f"is {traced} traced and {untraced[name]} "
                            "untraced"
                        )
            uncaused = bridge.uncaused_changes(
                nodes["baseline"],
                nodes["reform"],
                [f"{name}@{PAYMENT_YEAR}" for name in changed],
            )
            row.setdefault("float32_guard", {})[variant] = {
                "traced_leaves": changed,
                "traced_nodes": len(
                    set(nodes["baseline"]) | set(nodes["reform"])
                ),
                "small_changes": [
                    {"variable": c.variable, "change": c.change_cents / 100}
                    for c in bridge.small_changes(decomposition)
                ],
                "uncaused_changes": uncaused,
            }


def float32_guard(
    rows: list[dict[str, Any]],
    python: str | None,
    *,
    timeout: float = minimum.RUN_TIMEOUT_SECONDS,
) -> dict[str, dict[str, Any]]:
    """Trace every changed leaf of every comparison and apply the guard.

    Returns the traces (:func:`bridge.trace_policyengine_us`).
    """

    cases, overrides = trace_cases(rows)
    traces = bridge.trace_policyengine_us(
        cases,
        year=PAYMENT_YEAR,
        python=python,
        parameter_overrides=overrides,
        expected_package_record_digest=digest(),
        timeout=timeout,
    )
    apply_float32_guard(rows, traces)
    return traces


# ---------------------------------------------------------------------------
# Offsets and invariants
# ---------------------------------------------------------------------------
#: Categories whose contribution to net income must not fall when Social
#: Security falls: the means-tested benefits, the income taxes (a
#: contribution falls when the tax rises) and the refundable credits.  The
#: mirror of #496's ``WRONG_WAY_CATEGORIES`` for a cut.
WRONG_WAY_CATEGORIES = minimum.WRONG_WAY_CATEGORIES


def social_security_cut_cents(row: dict[str, Any]) -> int:
    """The household's annual cut in cents, from the benefit arithmetic."""

    return 100 * sum(cut.annual_cut for cut in row["cuts"].values())


def offsets(decomposition: bridge.Decomposition) -> dict[str, Any]:
    """The decomposition's levels and offset shares (exact)."""

    levels = dc.by_level(decomposition.components)
    social_security = levels["social_security"]["change"]
    share = dc.offset_share(decomposition.net_change_cents, social_security)
    by_level = dc.offset_shares_by_level(levels)
    return {
        "levels": levels,
        "social_security_change_cents": social_security,
        "net_change_cents": decomposition.net_change_cents,
        "offset_share": share,
        "offset_shares_by_level": by_level,
    }


def check_invariants(rows: list[dict[str, Any]]) -> list[str]:
    """Properties of this run, checked before anything is written."""

    for row in rows:
        tag = f"{row['household']}-{row['state']} ({row['fund']})"
        expected = -social_security_cut_cents(row)
        _require(expected < 0, f"{tag}: the cut is not a cut")
        for variant in VARIANTS:
            d = _decomposition(row, variant)
            where = f"{tag} {variant}"
            total = sum(c.change_cents for c in d.components)
            _require(total == d.net_change_cents, f"{where}: identity")
            categories = d.by_category()
            _require(
                sum(v["change"] for v in categories.values()) == total,
                f"{where}: categories",
            )
            levels = dc.by_level(d.components)
            for key in ("baseline", "reform", "change"):
                _require(
                    sum(level[key] for level in levels.values())
                    == sum(
                        {
                            "baseline": c.baseline_cents,
                            "reform": c.reform_cents,
                            "change": c.change_cents,
                        }[key]
                        for c in d.components
                    ),
                    f"{where}: levels do not partition the components",
                )
            ss = categories["social_security"]["change"]
            _require(
                ss == expected and levels["social_security"]["change"] == ss,
                f"{where}: Social Security changes by {ss} cents, the cut "
                f"is {expected}",
            )
            outside = dc.changed_outside_groups(d.components)
            _require(
                not outside,
                f"{where}: {outside} changed but no payer group holds them",
            )
            for name in WRONG_WAY_CATEGORIES:
                _require(
                    categories[name]["change"] >= 0,
                    f"{where}: {name} fell with Social Security",
                )
            share = dc.offset_share(d.net_change_cents, ss)
            shares = dc.offset_shares_by_level(levels)
            _require(
                share == 1 - Fraction(d.net_change_cents, ss)
                and sum(shares.values()) == share,
                f"{where}: offset shares",
            )
            _require(
                abs(d.reported_gap_cents) <= 1,
                f"{where}: household_net_income is off its definition by "
                f"{d.reported_gap_cents} cents",
            )
            guard = row["float32_guard"][variant]
            _require(
                not guard["uncaused_changes"],
                f"{where}: float32 guard: {guard['uncaused_changes']}",
            )
    by_key = {
        (row["household"], row["state"], row["reform"]): row for row in rows
    }
    for (key, state, reform), row in by_key.items():
        if reform == PRIMARY:
            continue
        deeper = by_key[(key, state, PRIMARY)]
        _require(
            deeper["reform_social_security_annual"]
            <= row["reform_social_security_annual"],
            f"{key}-{state}: the deeper cut raised Social Security",
        )
    return [
        "every household, state and reform, with and without health "
        "coverage: the leaf changes sum exactly (in cents) to the net "
        "change, and the categories and the levels of government to the "
        "same total; each leaf is in exactly one level",
        "the Social Security component equals minus the cut computed from "
        "the benefits (each beneficiary's monthly cut times 12)",
        "no leaf outside the federal, state and joint groups changes "
        "(market income and unreviewed leaves hold)",
        "when Social Security falls, SSI, SNAP, the Commodity Supplemental "
        "Food Program, state benefits and federal and state refundable tax "
        "credits never fall, and federal and state income taxes never rise",
        "the offset share is 1 - net change / Social Security change, "
        "exactly, and the levels' shares sum to it",
        "the OASI cut (the deeper one) never leaves more Social Security "
        "than the OASDI cut",
        "PolicyEngine-US's own household_net_income change is within one "
        "cent of the definition's sum",
        "float32 guard: every changed leaf traced through PolicyEngine-US's "
        "calculation; no variable changed by a cent or more (allowing one "
        "float32 step of rounding) while every variable it read held within "
        "float noise",
    ]


def check_medicaid_memo(
    rows: list[dict[str, Any]], per_enrollee: dict[str, dict[str, Any]]
) -> None:
    """Medicaid at cost is a whole number of enrollees at the release ratio.

    #496's differential check (``minimum.check_medicaid_memo``) for
    households of one or two: wherever someone is enrolled, the value
    PolicyEngine-US computed must be k times the release's spending over
    enrollment, within 50 cents an enrollee, for some k from 1 to the
    number of people.
    """

    for row in rows:
        expected = per_enrollee[row["state"]]["release"]
        people = len(row["situations"]["baseline"]["people"])
        where = f"{row['household']}-{row['state']} ({row['fund']})"
        costs = [
            (f"{scenario} memo", row["memo"][scenario]["medicaid_cost"])
            for scenario in ("baseline", "reform")
        ]
        for component in row["with_health"].components:
            if component.variable == "medicaid_cost":
                costs += [
                    ("with-health baseline", component.baseline_cents / 100),
                    ("with-health reform", component.reform_cents / 100),
                ]
        for label, cost in costs:
            _require(
                cost == 0
                or any(
                    abs(cost - k * expected) < 0.5 * k
                    for k in range(1, people + 1)
                ),
                f"{where} {label}: Medicaid at cost is {cost}, not a whole "
                f"number of enrollees at spending over enrollment "
                f"({expected})",
            )


def health_explanations(rows: list[dict[str, Any]]) -> dict[str, str]:
    """Why net income with health coverage differs, per affected row.

    Every row whose with-health net change differs from its default one
    must match one described pattern; any other is refused, so no row gets
    a text that does not fit it.  The patterns are those of
    :func:`_health_pattern`.
    """

    out = {}
    for row in rows:
        difference = (
            row["with_health"].net_change_cents
            - row["decomposition"].net_change_cents
        )
        if difference == 0:
            continue
        out[_row_key(row)] = _health_pattern(row)
    return out


def _health_change(row: dict[str, Any], variable: str) -> int:
    return sum(
        c.change_cents
        for c in row["with_health"].components
        if c.variable == variable
    )


def _health_pattern(row: dict[str, Any]) -> str:
    """The text for one row's health difference, or a refusal.

    Only the health leaves may differ between the two variants (every other
    leaf must change by the same amount in both).
    """

    default = {
        c.variable: c.change_cents for c in row["decomposition"].components
    }
    health_only = {}
    for c in row["with_health"].components:
        if c.category == "health_net":
            if c.change_cents:
                health_only[c.variable] = c.change_cents
            continue
        _require(
            c.change_cents == default.get(c.variable, 0),
            f"{_row_key(row)}: {c.variable} changes by {c.change_cents} with "
            f"health counted and {default.get(c.variable, 0)} without",
        )
    before = row["memo_with_health"]["baseline"]
    after = row["memo_with_health"]["reform"]
    name = STATES[row["state"]]["name"]
    medicaid = health_only.get("medicaid_cost", 0)
    msp = health_only.get("msp_cost", 0)
    _require(
        set(health_only) <= {"medicaid_cost", "msp_cost"},
        f"{_row_key(row)}: health leaves {sorted(health_only)} changed; "
        "only Medicaid and the Medicare Savings Program are described",
    )
    if (
        before["is_medicaid_eligible"] == 0
        and after["is_medicaid_eligible"] >= 1
        and medicaid > 0
    ):
        ssi_text = (
            f" SSI goes from ${minimum._money(bridge.to_cents(before['ssi']))}"
            f" to ${minimum._money(bridge.to_cents(after['ssi']))} a year."
            if before["ssi"] != after["ssi"]
            else ""
        )
        msp_text = (
            " The Medicare Savings Program value, counted only without full "
            f"Medicaid (msp_cost.py:28), changes by "
            f"{minimum._money(msp, signed=True)}."
            if msp
            else ""
        )
        return (
            f"In {name}, the cut makes the household eligible for Medicaid, "
            f"valued at cost at {minimum._money(medicaid, signed=True)} a "
            "year." + ssi_text + msp_text
        )
    raise InvariantError(
        f"{_row_key(row)}: net income with health coverage changes for a "
        "reason the text does not describe"
    )


def _row_key(row: dict[str, Any]) -> str:
    return f"{row['household']}-{row['state']}-{row['reform']}"


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------
_money = minimum._money


def percent_text(share: Fraction | None) -> str:
    """A share as a whole percent, a half rounded up in magnitude."""

    if share is None:
        return "n/a"
    hundredths = abs(Fraction(share)) * 100
    # floor(x + 1/2) in integers: a half rounds up in magnitude.
    whole = (2 * hundredths.numerator + hundredths.denominator) // (
        2 * hundredths.denominator
    )
    if whole == 0:
        return "0%"
    return f"−{whole}%" if share < 0 else f"{whole}%"


def _fraction_json(value: Fraction | None) -> dict[str, Any] | None:
    if value is None:
        return None
    return {
        "numerator": value.numerator,
        "denominator": value.denominator,
        "decimal": round(float(value), 6),
    }


def _offsets_json(decomposition: bridge.Decomposition) -> dict[str, Any]:
    result = offsets(decomposition)
    return {
        "social_security_change": result["social_security_change_cents"] / 100,
        "net_change": result["net_change_cents"] / 100,
        "offset_share": _fraction_json(result["offset_share"]),
        "levels": {
            level: {k: v / 100 for k, v in entry.items()}
            for level, entry in result["levels"].items()
        },
        "offset_shares_by_level": {
            level: _fraction_json(share)
            for level, share in (
                result["offset_shares_by_level"] or {}
            ).items()
        },
    }


def _serialize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "household": row["household"],
        "label": row["label"],
        "state": row["state"],
        "reform": row["reform"],
        "fund": row["fund"],
        "cuts": {person: cut.as_dict() for person, cut in row["cuts"].items()},
        "baseline_social_security_annual": row[
            "baseline_social_security_annual"
        ],
        "reform_social_security_annual": row["reform_social_security_annual"],
        "parameter_overrides": row["overrides"],
        "decomposition": row["decomposition"].as_dict(),
        "offsets": _offsets_json(row["decomposition"]),
        "with_health_benefits_in_net_income": {
            "net_change": row["with_health"].net_change_cents / 100,
            "baseline_net_income": row["with_health"].baseline_net_cents / 100,
            "reform_net_income": row["with_health"].reform_net_cents / 100,
            "categories": {
                name: {k: v / 100 for k, v in entry.items()}
                for name, entry in row["with_health"].by_category().items()
            },
            "components": [
                c.as_dict()
                for c in row["with_health"].components
                if c.baseline_cents or c.reform_cents
            ],
            "offsets": _offsets_json(row["with_health"]),
        },
        "memo": row["memo"],
        "memo_with_health": row["memo_with_health"],
        "float32_guard": row["float32_guard"],
        "situations": row["situations"],
    }


#: Rows of the per-household tables, in the order the analysis reports
#: them (the bridge's categories).
TABLE_LABELS = {
    **bridge.CATEGORY_LABELS,
    "state_benefits": "State supplement and other state benefits",
}


def table_categories(rows: list[dict[str, Any]]) -> list[str]:
    """Categories nonzero, at baseline or reform, in any comparison."""

    present: set[str] = set()
    for row in rows:
        categories = row["decomposition"].by_category()
        present.update(
            name
            for name, entry in categories.items()
            if entry["baseline"] or entry["reform"]
        )
    present.update(("social_security", "ssi", "state_benefits", "snap"))
    present.update(("federal_income_tax", "state_income_tax"))
    return [name for name in bridge.CATEGORY_ORDER if name in present]


def chart_categories(rows: list[dict[str, Any]]) -> list[str]:
    """Categories that change in any primary comparison, for every chart."""

    changed: set[str] = set()
    for row in rows:
        if row["reform"] != PRIMARY:
            continue
        categories = row["decomposition"].by_category()
        changed.update(
            name for name, entry in categories.items() if entry["change"]
        )
    return [name for name in bridge.CATEGORY_ORDER if name in changed]


def _cut_text(document: dict[str, Any], reform: str) -> str:
    quote = document["trustees_report"]["quotes"][REFORMS[reform]]
    cut = Decimal(quote["cut_share"]) * 100
    return f"{cut.normalize():f}%"


def reform_name(document: dict[str, Any], reform: str) -> str:
    quote = document["trustees_report"]["quotes"][REFORMS[reform]]
    fund = "OASI" if REFORMS[reform] == "OASI" else "combined OASDI"
    return (
        f"a {_cut_text(document, reform)} cut in every Social Security "
        f"benefit, leaving the {quote['payable_percent']} percent of "
        f"scheduled benefits the Trustees project {fund} income to pay at "
        f"depletion in {quote['depletion_year']}"
    )


def markdown(rows: list[dict[str, Any]], document: dict[str, Any]) -> str:
    provenance = document["provenance"]
    release = provenance["policyengine_us"]["release"]
    installed = provenance["policyengine_us"]["installed"]
    record = provenance["policyengine_us"]["record_check"]
    trustees = document["trustees_report"]
    lines = [
        "# A Social Security cut at trust fund depletion: sample households",
        "",
        f"**{ILLUSTRATIVE_LABEL}.** Five households, each in three states, "
        "run through PolicyEngine-US. Amounts are annual 2026 dollars.",
        "",
        f"**{LAW_YEAR_NOTE}**",
        "",
        "## The cut",
        "",
        f"From {trustees['report']}, section {trustees['section']}, "
        f"{trustees['assumptions']} assumptions ({trustees['highlights']['url']}, "
        f"retrieved {trustees['highlights']['retrieved_utc']}, SHA-256 "
        f"`{trustees['highlights']['sha256']}`):",
        "",
    ]
    for fund in ("OASI", "OASDI"):
        quote = trustees["quotes"][fund]
        lines.append(f"> {quote['text']}")
        lines.append("")
    lines += [
        f"- **Primary:** {reform_name(document, PRIMARY)}. "
        + trustees["fund_choice"],
        f"- **Sensitivity:** {reform_name(document, 'oasdi')}.",
        f"- **Rounding:** {dc.ROUNDING_RULE}",
        "",
        "Each household's Social Security, scheduled and after the cut "
        "(monthly):",
        "",
        "| Household | Beneficiary | Scheduled | After the OASI cut | After "
        "the OASDI cut |",
        "|---|---|---:|---:|---:|",
    ]
    seen = set()
    for row in rows:
        if row["household"] in seen or row["reform"] != PRIMARY:
            continue
        seen.add(row["household"])
        other = next(
            r
            for r in rows
            if r["household"] == row["household"] and r["reform"] == "oasdi"
        )
        for person, cut in row["cuts"].items():
            lines.append(
                f"| {row['household']} | {person} | "
                f"${cut.monthly_scheduled:,} | ${cut.monthly_payable:,} | "
                f"${other['cuts'][person].monthly_payable:,} |"
            )
    lines += [
        "",
        "## Summary: the OASI cut",
        "",
        "The offset share is the share of the Social Security cut that other "
        "programs and taxes return: 1 − (net change ÷ Social Security "
        "change). Federal, state and joint are the shares each level of "
        "government pays; they sum to the offset share. Health coverage is "
        "outside net income by default, as PolicyEngine-US computes it; the "
        "last column counts it (a sensitivity).",
        "",
    ]
    lines += _summary_table(rows, PRIMARY)
    lines += [
        "",
        "## Sensitivity: the OASDI cut",
        "",
    ]
    lines += _summary_table(rows, "oasdi")
    lines += ["", document["medicaid_valuation"]["text"], ""]
    names = table_categories(rows)
    for spec in HOUSEHOLDS:
        key = spec["key"]
        lines += [f"## {spec['label']}", "", spec["description"] + ".", ""]
        for row in rows:
            if row["household"] != key or row["reform"] != PRIMARY:
                continue
            lines += _component_table(row, names)
    explanations = document["health_explanations"]
    if explanations:
        lines += ["## Health coverage", ""]
        lines += [
            f"- {key}: {text}" for key, text in sorted(explanations.items())
        ]
        lines.append("")
    guard = document["float32_guard"]
    lines += [
        "## Float32 guard",
        "",
        guard["summary"],
        "",
        "## Provenance",
        "",
        f"- Microcosm Dynamics commit "
        f"`{provenance['microcosm_dynamics']['commit']}`",
        f"- PolicyEngine-US {release['version']} from PyPI (wheel SHA-256 "
        f"`{release['wheel_sha256']}`), with policyengine-core "
        f"{installed['policyengine_core_version']}. All "
        f"{record['files_checked']:,} installed `policyengine_us/` files "
        "match the wheel's RECORD.",
    ]
    for update in provenance["policyengine_us"]["parameter_updates"]:
        source = update["source"]
        lines.append(
            f"- Parameter update ({', '.join(update['states'])}): "
            f"`{update['parameter']}` is set to {update['value']:,.2f} "
            f"{update['unit']} for {update['year']}, from {source['publisher']}, "
            f"\"{source['title']}\" ({source['revision']}, effective "
            f"{source['effective']}; {source['url']}, retrieved "
            f"{source['retrieved']}), as in #496."
        )
    lines += [
        "",
        "## Notes",
        "",
        *[f"- {note}" for note in document["caveats"]],
        "",
    ]
    return "\n".join(lines)


def _summary_table(rows: list[dict[str, Any]], reform: str) -> list[str]:
    lines = [
        "| Household | State | Social Security | Net income | Offset share "
        "| Federal | State | Joint | Net income with health coverage |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        if row["reform"] != reform:
            continue
        result = offsets(row["decomposition"])
        shares = result["offset_shares_by_level"]
        lines.append(
            f"| {row['household']} | {row['state']} | "
            f"{_money(result['social_security_change_cents'], signed=True)} | "
            f"{_money(result['net_change_cents'], signed=True)} | "
            f"{percent_text(result['offset_share'])} | "
            f"{percent_text(shares['federal'])} | "
            f"{percent_text(shares['state'])} | "
            f"{percent_text(shares['joint'])} | "
            f"{_money(row['with_health'].net_change_cents, signed=True)} |"
        )
    return lines


def _component_table(row: dict[str, Any], names: list[str]) -> list[str]:
    d = row["decomposition"]
    categories = d.by_category()
    health = row["with_health"]
    health_categories = health.by_category()
    result = offsets(d)
    lines = [
        f"### {row['label']}, {STATES[row['state']]['name']}",
        "",
        "| Component | Baseline | After the cut | Change |",
        "|---|---:|---:|---:|",
    ]
    for name in names:
        entry = categories[name]
        lines.append(
            f"| {TABLE_LABELS[name]} | {_money(entry['baseline'])} | "
            f"{_money(entry['reform'])} | "
            f"{_money(entry['change'], signed=True)} |"
        )
    lines.append(
        f"| **Net income** | **{_money(d.baseline_net_cents)}** | "
        f"**{_money(d.reform_net_cents)}** | "
        f"**{_money(d.net_change_cents, signed=True)}** |"
    )
    entry = health_categories["health_net"]
    lines.append(
        "| Health benefits less health costs (sensitivity) | "
        f"{_money(entry['baseline'])} | {_money(entry['reform'])} | "
        f"{_money(entry['change'], signed=True)} |"
    )
    lines.append(
        "| Net income with health coverage (sensitivity) | "
        f"{_money(health.baseline_net_cents)} | "
        f"{_money(health.reform_net_cents)} | "
        f"{_money(health.net_change_cents, signed=True)} |"
    )
    levels = result["levels"]
    lines += [
        "",
        f"Offset share {percent_text(result['offset_share'])}: federal "
        f"{_money(levels['federal']['change'], signed=True)}, state "
        f"{_money(levels['state']['change'], signed=True)}, joint "
        f"{_money(levels['joint']['change'], signed=True)}, against a "
        f"Social Security change of "
        f"{_money(levels['social_security']['change'], signed=True)}.",
        "",
    ]
    return lines


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
POSITIVE = minimum.POSITIVE
NEGATIVE = minimum.NEGATIVE
NET = minimum.NET
INK = minimum.INK
MUTED = minimum.MUTED
GRID = minimum.GRID
SURFACE = minimum.SURFACE
#: The three payer groups in the summary chart.
GROUP_COLORS = {"federal": "#2a78d6", "state": "#d97a1f", "joint": "#7a5cc4"}
CHART_LABELS = {
    **minimum.CHART_LABELS,
    "state_benefits": "State supplement",
}
HEALTH_ROW_LABEL = "Net, with health coverage*"


def _matplotlib():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    matplotlib.rcParams["svg.hashsalt"] = "pe-us-depletion-cut"
    matplotlib.rcParams["font.family"] = "DejaVu Sans"
    # Dollar signs are text, not mathtext delimiters.
    matplotlib.rcParams["text.parse_math"] = False
    matplotlib.rcParams["hatch.color"] = SURFACE
    return matplotlib, plt


def _save(fig: Any, stem: Path, title: str) -> list[Path]:
    """Write PNG and SVG, each carrying the label in its metadata too.

    The label and the 2026-law note are drawn on every chart; they are also
    the file's title and description, which a reader of the bytes (and the
    artifact test) can find without rendering it.
    """

    description = f"{ILLUSTRATIVE_LABEL}. {LAW_YEAR_NOTE}"
    paths = []
    for suffix, kwargs in (
        (
            ".png",
            {
                "dpi": 200,
                "metadata": {
                    "Software": None,
                    "Title": title,
                    "Description": description,
                },
            },
        ),
        (
            ".svg",
            {
                "metadata": {
                    "Date": None,
                    "Creator": None,
                    "Title": title,
                    "Description": description,
                }
            },
        ),
    ):
        path = stem.with_suffix(suffix)
        fig.savefig(path, facecolor=SURFACE, **kwargs)
        paths.append(path)
    return paths


def chart_footnotes(document: dict[str, Any], key: str) -> list[str]:
    """The footnote paragraphs under a household's chart."""

    provenance = document["provenance"]
    pe = provenance["policyengine_us"]
    trustees = document["trustees_report"]
    notes = [
        LAW_YEAR_NOTE,
        "Blue raises net income and red lowers it; the gray bars are net "
        "changes. Each amount is rounded to the dollar on its own. *Health "
        "coverage counted: Medicaid valued at the state's 2023 Medicaid "
        "spending over its October 2024 Medicaid and CHIP enrollment, all "
        "ages, as in #496. It is coverage at average program cost, not "
        "cash.",
    ]
    for row_key, text in document["health_explanations"].items():
        if row_key.startswith(f"{key}-") and row_key.endswith(f"-{PRIMARY}"):
            notes.append(text)
    for update in pe["parameter_updates"]:
        notes.append(
            f"{STATES[update['states'][0]]['name']}: the 2026 SSI payment "
            f"standard is set to the published ${update['value']:,.2f} a "
            f"month ({update['source']['publisher']}, "
            f"{update['source']['title']}, {update['source']['revision']})."
        )
    notes.append(
        f"Cut: {trustees['report']}, {trustees['section']} "
        f"({trustees['highlights']['url']}). PolicyEngine-US "
        f"{pe['release']['version']} (PyPI); Microcosm Dynamics "
        f"{provenance['microcosm_dynamics']['commit'][:10]}."
    )
    return notes


def draw_household_chart(
    rows: list[dict[str, Any]],
    spec: dict[str, Any],
    document: dict[str, Any],
    stem: Path,
) -> list[Path]:
    """#496's waterfall, one panel per state, for the primary cut."""

    matplotlib, plt = _matplotlib()
    key = spec["key"]
    own = [
        row
        for row in rows
        if row["household"] == key and row["reform"] == PRIMARY
    ]
    names = chart_categories(rows)
    labels = (
        [CHART_LABELS[name] for name in names]
        + ["Net income"]
        + [HEALTH_ROW_LABEL]
    )
    changes_by_state = {}
    for row in own:
        categories = row["decomposition"].by_category()
        changes_by_state[row["state"]] = (
            [categories[name]["change"] / 100 for name in names]
            + [row["decomposition"].net_change_cents / 100]
            + [row["with_health"].net_change_cents / 100]
        )
    extent = max(
        max(abs(v) for v in values) for values in changes_by_state.values()
    )
    running_extent = 0.0
    for values in changes_by_state.values():
        cumulative = 0.0
        for value in values[:-2]:
            cumulative += value
            running_extent = max(running_extent, abs(cumulative))
    limit = max(extent, running_extent) * 1.5 or 1.0

    width = 4.1 * len(own)
    footer = [
        textwrap.fill(note, width=int(width * 16.5))
        for note in chart_footnotes(document, key)
    ]
    footer_lines = sum(note.count("\n") + 1 for note in footer)
    footer_height = 0.145 * footer_lines + 0.15
    plot_height = 0.5 * len(labels) + 0.6
    top_height = 1.55
    height = top_height + plot_height + footer_height + 0.45
    fig, axes = plt.subplots(
        1, len(own), figsize=(width, height), sharey=True, facecolor=SURFACE
    )
    axes = list(axes) if len(own) > 1 else [axes]
    y_positions = list(range(len(labels)))[::-1]
    net_index = len(labels) - 2
    health_index = len(labels) - 1
    for ax, row in zip(axes, own, strict=True):
        ax.set_facecolor(SURFACE)
        values = changes_by_state[row["state"]]
        cumulative = 0.0
        for index, (value, y) in enumerate(
            zip(values, y_positions, strict=True)
        ):
            is_total = index >= net_index
            start = 0.0 if is_total else cumulative
            color = NET if is_total else (POSITIVE if value >= 0 else NEGATIVE)
            if value != 0:
                thin = abs(value) < 0.02 * limit
                ax.barh(
                    y,
                    value,
                    left=start,
                    height=0.6,
                    color=color,
                    alpha=0.55 if index == health_index else 1.0,
                    hatch="///" if index == health_index else None,
                    edgecolor=color if thin else SURFACE,
                    linewidth=1.5,
                    zorder=3,
                )
            else:
                ax.plot(
                    [start, start],
                    [y - 0.3, y + 0.3],
                    color=MUTED,
                    linewidth=1.2,
                    zorder=3,
                )
            end = start + value
            offset = limit * 0.03
            ax.text(
                end + offset if value >= 0 else end - offset,
                y,
                _money(round(value * 100), signed=True),
                va="center",
                ha="left" if value >= 0 else "right",
                fontsize=9,
                color=INK,
                fontweight="bold" if is_total else "normal",
                bbox={"facecolor": SURFACE, "edgecolor": "none", "pad": 1.0},
                zorder=4,
            )
            if not is_total:
                cumulative = end
        result = offsets(row["decomposition"])
        ax.axvline(0, color=MUTED, linewidth=0.8, zorder=2)
        ax.set_xlim(-limit, limit)
        ax.set_title(
            f"{STATES[row['state']]['name']}\n"
            f"{percent_text(result['offset_share'])} of the cut offset",
            loc="left",
            fontsize=11,
            color=INK,
            fontweight="bold",
            linespacing=1.3,
        )
        ax.grid(axis="x", color=GRID, linewidth=0.6, zorder=0)
        ax.tick_params(axis="x", labelsize=8, colors=MUTED)
        ax.tick_params(axis="y", length=0, labelsize=9.5, colors=INK)
        step = 1000 if limit <= 6000 else 2000
        ax.xaxis.set_major_formatter(
            matplotlib.ticker.FuncFormatter(
                lambda v, _: (
                    "$0"
                    if v == 0
                    else (
                        f"−${abs(v) / 1000:,.0f}k"
                        if v < 0
                        else f"${v / 1000:,.0f}k"
                    )
                )
            )
        )
        ax.xaxis.set_major_locator(matplotlib.ticker.MultipleLocator(step))
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(GRID)
        ax.axhline(y_positions[net_index] + 0.5, color=GRID, linewidth=0.8)
    axes[0].set_yticks(y_positions)
    axes[0].set_yticklabels(labels)

    def from_top(inches: float) -> float:
        return 1 - inches / height

    fig.text(
        0.01,
        from_top(0.18),
        f"{spec['label']}: change in net income from a "
        f"{_cut_text(document, PRIMARY)} Social Security cut, 2026 law",
        ha="left",
        va="top",
        fontsize=13.5,
        fontweight="bold",
        color=INK,
    )
    subtitle = textwrap.fill(
        f"{ILLUSTRATIVE_LABEL}. {spec['description']}. The cut: "
        f"{reform_name(document, PRIMARY)}; annual dollars.",
        width=int(width * 13.4),
    )
    fig.text(
        0.01,
        from_top(0.52),
        subtitle,
        ha="left",
        va="top",
        fontsize=9,
        color=MUTED,
        linespacing=1.4,
    )
    fig.text(
        0.01,
        (footer_height + 0.05) / height,
        "\n".join(footer),
        ha="left",
        va="top",
        fontsize=7.5,
        color=MUTED,
        linespacing=1.35,
    )
    fig.subplots_adjust(
        left=0.16,
        right=0.98,
        top=from_top(top_height),
        bottom=(footer_height + 0.45) / height,
        wspace=0.12,
    )
    paths = _save(fig, stem, f"{spec['label']}: {ILLUSTRATIVE_LABEL}")
    plt.close(fig)
    return paths


def draw_summary_chart(
    rows: list[dict[str, Any]], document: dict[str, Any], stem: Path
) -> list[Path]:
    """The offset share by household and state, split by payer group."""

    matplotlib, plt = _matplotlib()
    primary = [row for row in rows if row["reform"] == PRIMARY]
    sensitivity = {
        (row["household"], row["state"]): row
        for row in rows
        if row["reform"] == "oasdi"
    }
    labels = []
    stacks = []
    markers = []
    for row in primary:
        labels.append(f"{row['household']}  {STATES[row['state']]['name']}")
        shares = offsets(row["decomposition"])["offset_shares_by_level"]
        stacks.append(
            {group: float(shares[group]) for group in dc.OFFSET_GROUPS}
        )
        other = offsets(
            sensitivity[(row["household"], row["state"])]["decomposition"]
        )
        markers.append(float(other["offset_share"]))
    upper = max(
        1.0,
        max(sum(v for v in s.values() if v > 0) for s in stacks),
        max(markers),
    )
    lower = min(
        0.0,
        min(sum(v for v in s.values() if v < 0) for s in stacks),
        min(markers),
    )
    width = 10.0
    notes = [
        LAW_YEAR_NOTE,
        "Offset share: 1 − (net change ÷ Social Security change), from "
        "PolicyEngine-US's household_net_income, which excludes health "
        "coverage by default. Federal: federal income tax, SSI and SNAP. "
        "State: state income tax, refundable credits and SSI supplements. "
        "Joint federal-state programs (Medicaid, Medicare Savings Programs) "
        "enter only when health coverage is counted (see the tables).",
        f"Cut: {document['trustees_report']['report']}, "
        f"{document['trustees_report']['section']}. PolicyEngine-US "
        f"{document['provenance']['policyengine_us']['release']['version']} "
        "(PyPI); Microcosm Dynamics "
        f"{document['provenance']['microcosm_dynamics']['commit'][:10]}.",
    ]
    footer = [textwrap.fill(note, width=int(width * 15.5)) for note in notes]
    footer_lines = sum(note.count("\n") + 1 for note in footer)
    footer_height = 0.145 * footer_lines + 0.15
    plot_height = 0.36 * len(labels) + 0.8
    top_height = 1.35
    height = top_height + plot_height + footer_height + 0.6
    fig, ax = plt.subplots(figsize=(width, height), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    y_positions = list(range(len(labels)))[::-1]
    for y, stack, marker in zip(y_positions, stacks, markers, strict=True):
        left_positive = 0.0
        left_negative = 0.0
        for group in dc.OFFSET_GROUPS:
            value = stack[group]
            if value == 0:
                continue
            left = left_positive if value > 0 else left_negative
            ax.barh(
                y,
                value,
                left=left,
                height=0.62,
                color=GROUP_COLORS[group],
                edgecolor=SURFACE,
                linewidth=0.8,
                zorder=3,
            )
            if value > 0:
                left_positive += value
            else:
                left_negative += value
        total = sum(stack.values())
        ax.text(
            max(left_positive, 0.0) + 0.012 * (upper - lower),
            y,
            percent_text(Fraction(total).limit_denominator(10**9)),
            va="center",
            ha="left",
            fontsize=9,
            color=INK,
            fontweight="bold",
            zorder=4,
        )
        ax.plot(
            [marker],
            [y],
            marker="D",
            markersize=5,
            markerfacecolor=SURFACE,
            markeredgecolor=INK,
            linestyle="none",
            zorder=5,
        )
    for boundary in range(3, len(labels), 3):
        ax.axhline(
            y_positions[boundary] + 0.5, color=GRID, linewidth=0.8, zorder=1
        )
    ax.axvline(0, color=MUTED, linewidth=0.8, zorder=2)
    ax.axvline(1, color=MUTED, linewidth=0.6, linestyle=":", zorder=2)
    ax.set_xlim(lower - 0.02, upper * 1.12)
    ax.set_ylim(-0.6, len(labels) - 0.4)
    ax.set_yticks(y_positions)
    ax.set_yticklabels(labels)
    ax.xaxis.set_major_formatter(
        matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.0%}")
    )
    ax.xaxis.set_major_locator(matplotlib.ticker.MultipleLocator(0.25))
    ax.grid(axis="x", color=GRID, linewidth=0.6, zorder=0)
    ax.tick_params(axis="x", labelsize=8.5, colors=MUTED)
    ax.tick_params(axis="y", length=0, labelsize=9.5, colors=INK)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    handles = [
        matplotlib.patches.Patch(
            color=GROUP_COLORS[group], label=dc.LEVEL_LABELS[group]
        )
        for group in dc.OFFSET_GROUPS
    ] + [
        matplotlib.lines.Line2D(
            [],
            [],
            marker="D",
            markersize=5,
            markerfacecolor=SURFACE,
            markeredgecolor=INK,
            linestyle="none",
            label=f"Total with the {_cut_text(document, 'oasdi')} "
            "(OASDI) cut",
        )
    ]
    ax.legend(
        handles=handles,
        loc="lower right",
        fontsize=8.5,
        frameon=False,
    )

    def from_top(inches: float) -> float:
        return 1 - inches / height

    fig.text(
        0.01,
        from_top(0.18),
        "How much of a Social Security cut other programs and taxes offset, "
        "2026 law",
        ha="left",
        va="top",
        fontsize=13.5,
        fontweight="bold",
        color=INK,
    )
    fig.text(
        0.01,
        from_top(0.55),
        textwrap.fill(
            f"{ILLUSTRATIVE_LABEL}. Bars: the "
            f"{_cut_text(document, PRIMARY)} (OASI) cut, by who pays the "
            "offset. Households A-C are a low earner (A: no other income; "
            "B: a $4,800 pension; C: a $31,200 pension); D is a medium "
            "earner with C's pension; E is that earner's one-earner couple, "
            "with a $42,000 pension.",
            width=int(width * 13.4),
        ),
        ha="left",
        va="top",
        fontsize=9,
        color=MUTED,
        linespacing=1.4,
    )
    fig.text(
        0.01,
        (footer_height + 0.05) / height,
        "\n".join(footer),
        ha="left",
        va="top",
        fontsize=7.5,
        color=MUTED,
        linespacing=1.35,
    )
    fig.subplots_adjust(
        left=0.17,
        right=0.98,
        top=from_top(top_height),
        bottom=(footer_height + 0.6) / height,
    )
    paths = _save(fig, stem, f"Offset share summary: {ILLUSTRATIVE_LABEL}")
    plt.close(fig)
    return paths


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def _guard_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    comparisons = 0
    leaves = 0
    nodes = 0
    small = []
    for row in rows:
        for variant in VARIANTS:
            guard = row["float32_guard"][variant]
            comparisons += 1
            leaves += len(guard["traced_leaves"])
            nodes += guard["traced_nodes"]
            small += [
                f"{row['household']}-{row['state']} {row['fund']} "
                f"({variant}): {item['variable']} {item['change']:+.2f}"
                for item in guard["small_changes"]
            ]
    small_text = (
        "No leaf changed by a nonzero amount under $2."
        if not small
        else "Leaves that changed by a nonzero amount under $2, each traced "
        "to a changed input: " + "; ".join(small) + "."
    )
    return {
        "comparisons": comparisons,
        "changed_leaves_traced": leaves,
        "traced_nodes": nodes,
        "small_changes": small,
        "uncaused_changes": 0,
        "summary": (
            f"Every changed leaf of the {comparisons} comparisons (five "
            "households in three states, two cuts, with and without health "
            f"coverage; {leaves} leaves) was traced through PolicyEngine-US's "
            f"own calculation ({nodes:,} traced variable-periods). No "
            "variable changed by a cent or more (from a cent less one "
            "float32 step at its size, never under half a cent) while every "
            "variable it read held within float noise (a cent, or four "
            "float32 steps at the read's size where that is more), the "
            "signature of a float32 step at a bracket edge. " + small_text
        ),
    }


def caveats(
    benefits: dict[str, Any],
    trustees: dict[str, Any],
    parameter_root: Path,
    valuation: str,
    updates: list[dict[str, Any]],
) -> list[str]:
    oasi = trustees["quotes"]["OASI"]
    return [
        "Illustrative households, not survey data: two invented workers "
        "(the low earner of #496 and a medium earner) in five living "
        "situations, each in three states. They show mechanisms, not how "
        "many beneficiaries are in each situation.",
        LAW_YEAR_NOTE,
        "Not a projection. Benefits, prices, tax brackets and program "
        "rules are 2026's. By the depletion date some will have changed "
        "under current law: for example, the State cost share of SNAP "
        "allotments in 7 USC 2013(a)(2)(B) begins in fiscal year 2028 at "
        "the earliest; from then a State whose payment error rate is 6 "
        "percent or more pays 5 to 15 percent of the cost of SNAP "
        "allotments. And the Trustees Report says the One Big Beautiful "
        "Bill Act 'adds a temporary additional standard deduction for "
        "taxpayers over age 65'.",
        f"The cut is the share of scheduled benefits the Trustees project "
        f"to be payable at depletion ({oasi['payable_percent']} percent "
        f"for OASI in {oasi['depletion_year']}), applied to every benefit "
        "at once. Current law does not say how benefits would be reduced at "
        "depletion; an across-the-board cut is one possibility. "
        + dc.ROUNDING_RULE,
        "No behavioral response: no change in work, claiming, saving, "
        "living arrangements or take-up.",
        "Take-up is PolicyEngine-US's default (as in #496): full take-up of "
        "SSI, SNAP and Medicaid. Housing assistance is switched off because "
        "vouchers are rationed.",
        "The offset is grouped by who pays it under 2026 law. Federal income "
        "tax is grouped as federal, although part of the income tax on "
        "Social Security benefits is credited to the trust funds (the "
        "Trustees Report counts '$58 billion from income taxation of Social "
        "Security benefits' as 2025 OASDI income); this analysis does not "
        "split that part out.",
        "Net income is PolicyEngine-US's household_net_income, which by "
        "default excludes health coverage (Medicaid at cost, Medicare "
        "Savings Programs); the with-health sensitivity and the memo lines "
        "report it, as in #496. " + valuation,
        *minimum._release_caveats(parameter_root),
        *[
            f"{STATES[update['states'][0]]['name']}'s {update['year']} aged "
            "or disabled payment standard is set to the published "
            f"${update['value']:,.2f} a month ({update['source']['publisher']}"
            f", {update['source']['title']}, {update['source']['revision']})"
            f"; policyengine-us {minimum.PE_US_RELEASE['version']} has no "
            f"{update['year']} entry and would hold "
            f"${update['installed_value']:,.2f} from "
            f"{update['installed_value_dated']}."
            for update in updates
        ],
        "The spouse in household E is left at PolicyEngine-US's default "
        "Medicare quarters of coverage; the workers carry four a year of "
        "covered work, as in #496.",
    ]


def build(
    python: str | None,
    *,
    docs_dir: Path = DEFAULT_DOCS_DIR,
    full_report_text: Path | None = DEFAULT_FULL_REPORT_TEXT,
    law_dir: Path | None = DEFAULT_LAW_DIR,
    timeout: float = minimum.RUN_TIMEOUT_SECONDS,
    raw_path: Path | None = None,
    reuse_raw: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Run everything, check it, and return the document and the rows.

    ``raw_path`` keeps PolicyEngine-US's raw outputs (the run and the
    traces, with the SHA-256 of each job) outside the repository, so a
    failed check can be diagnosed without rerunning.  ``reuse_raw`` reads
    them back instead of running, for development only: it refuses outputs
    whose jobs differ from this code's, and the document records that the
    outputs were reused (the committed artifacts are from a fresh run).
    """

    sources_dir = docs_dir / SOURCES_DIRNAME
    trustees = trustees_citation(sources_dir, full_report_text)
    statutes = statute_sources(sources_dir, law_dir)
    shares = {"baseline": Decimal(1)}
    for scenario, fund in REFORMS.items():
        shares[scenario] = Decimal(trustees["quotes"][fund]["payable_share"])
    installation, pe_provenance = minimum.pinned_release(python)
    parameter_root = Path(installation.location)
    updates = minimum.parameter_updates(parameter_root)
    rates, cola_provenance = minimum.cola_rates(PAYMENT_YEAR, parameter_root)
    benefits = {"low_earner": low_earner_benefit(parameter_root)}
    benefits["medium_earner"] = medium_earner_benefit(parameter_root, rates)
    benefits["couple"] = couple_benefits(
        parameter_root, rates, benefits["medium_earner"]
    )
    cases, plan = plan_cases(benefits, shares, updates)
    run_sha = job_sha256(
        {"year": PAYMENT_YEAR, "cases": run_job(cases), "release": digest()}
    )
    if reuse_raw:
        if raw_path is None:
            raise ValueError("reusing raw outputs needs their path")
        with raw_path.open("rb") as handle:
            raw = pickle.load(handle)  # noqa: S301 (this script's own file)
        _require(
            raw["run_job_sha256"] == run_sha,
            "the raw outputs are not this code's run job",
        )
        result = raw["result"]
        rows = rows_from_result(plan, result)
        traced, overrides = trace_cases(rows)
        _require(
            raw["trace_job_sha256"] == _trace_sha(traced, overrides),
            "the raw traces are not this code's trace job",
        )
        traces = raw["traces"]
    else:
        result = bridge.run_policyengine_us(
            cases,
            year=PAYMENT_YEAR,
            python=python,
            expected_package_record_digest=digest(),
            timeout=timeout,
        )
        rows = rows_from_result(plan, result)
        traced, overrides = trace_cases(rows)
        traces = bridge.trace_policyengine_us(
            traced,
            year=PAYMENT_YEAR,
            python=python,
            parameter_overrides=overrides,
            expected_package_record_digest=digest(),
            timeout=timeout,
        )
        if raw_path is not None:
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            with raw_path.open("wb") as handle:
                pickle.dump(
                    {
                        "run_job_sha256": run_sha,
                        "trace_job_sha256": _trace_sha(traced, overrides),
                        "result": result,
                        "traces": traces,
                    },
                    handle,
                )
    if result.installation != installation:
        raise ValueError("policyengine-us changed during the run")
    apply_float32_guard(rows, traces)
    checks = check_invariants(rows)
    per_enrollee = minimum.medicaid_per_enrollee(parameter_root)
    check_medicaid_memo(rows, per_enrollee)
    checks.append(
        "Medicaid at cost, wherever someone is enrolled (the memo and the "
        "with-health medicaid_cost leaf), is a whole number of enrollees at "
        "the state's spending over enrollment that the valuation text "
        "describes"
    )
    explanations = health_explanations(rows)
    valuation = minimum.medicaid_valuation_text(per_enrollee)
    pe_provenance["parameter_updates"] = [dict(update) for update in updates]
    code_paths = ["src", "scripts", "tests"]
    provenance = {
        "microcosm_dynamics": {
            "repository": "PolicyEngine/microcosm-dynamics",
            "commit": minimum._git(ROOT, "rev-parse", "HEAD"),
            "code_dirty": bool(
                minimum._git(ROOT, "status", "--porcelain", "--", *code_paths)
            ),
            "script": "scripts/pe_us_depletion_cut_sample_households.py",
            "modules": [
                "src/populace_dynamics/bridge/depletion_cut.py",
                "src/populace_dynamics/bridge/policyengine_us.py",
                "scripts/pe_us_minimum_benefit_sample_households.py",
                "src/populace_dynamics/track_b/gross_benefits.py",
            ],
            "python_version": sys.version.split()[0],
        },
        "policyengine_us": pe_provenance,
        "payment_year": PAYMENT_YEAR,
        "cola": cola_provenance,
        "statutes": statutes,
        "runs": {
            "cases": len(cases),
            "traced_cases": len(traced),
            "run_job_sha256": run_sha,
            "trace_job_sha256": _trace_sha(traced, overrides),
            "reused_raw_outputs": reuse_raw,
        },
    }
    guard = _guard_summary(rows)
    document = {
        "schema_version": SCHEMA_VERSION,
        "label": ILLUSTRATIVE_LABEL,
        "law_year_note": LAW_YEAR_NOTE,
        "reforms": {
            scenario: {
                "fund": fund,
                "payable_share": str(shares[scenario]),
                "cut_share": str(1 - shares[scenario]),
                "primary": scenario == PRIMARY,
            }
            for scenario, fund in REFORMS.items()
        },
        "rounding_rule": dc.ROUNDING_RULE,
        "trustees_report": trustees,
        "provenance": provenance,
        "benefits": benefits,
        "households": [dict(spec) for spec in HOUSEHOLDS],
        "states": STATES,
        "common_inputs": {
            "monthly_rent": minimum.MONTHLY_RENT,
            "bank_account_assets": minimum.BANK_ACCOUNT_ASSETS,
            "has_heating_cooling_expense": True,
            "takes_up_housing_assistance_if_eligible": False,
            "living_arrangements_allow_for_food_preparation": True,
        },
        "leaf_levels": {
            name: {"level": level, "basis": basis}
            for name, (level, basis) in dc.LEAF_LEVELS.items()
        },
        "level_labels": dc.LEVEL_LABELS,
        "net_income_tree": {
            name: [list(part) for part in parts]
            for name, parts in rows[0]["tree"].children.items()
        },
        "results": [_serialize_row(row) for row in rows],
        "medicaid_valuation": {
            "text": valuation,
            "per_enrollee": per_enrollee,
            "files": [
                minimum.PARAMETER_PREFIX + minimum.MEDICAID_TOTALS + name
                for name in ("spending.yaml", "enrollment.yaml")
            ],
        },
        "health_explanations": explanations,
        "float32_guard": guard,
        "invariants_checked": checks,
        "caveats": caveats(
            benefits, trustees, parameter_root, valuation, updates
        ),
    }
    minimum._no_absolute_paths(document)
    return document, rows


def write(
    document: dict[str, Any], rows: list[dict[str, Any]], directory: Path
) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    written = []
    json_path = directory / f"{OUTPUT_STEM}.json"
    json_path.write_text(
        json.dumps(document, indent=2, sort_keys=False) + "\n"
    )
    written.append(json_path)
    md_path = directory / f"{OUTPUT_STEM}.md"
    md_path.write_text(markdown(rows, document))
    written.append(md_path)
    for spec in HOUSEHOLDS:
        stem = directory / f"household_{spec['key'].lower()}_waterfall"
        written += draw_household_chart(rows, spec, document, stem)
    written += draw_summary_chart(
        rows, document, directory / "offset_share_summary"
    )
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--docs-dir", type=Path, default=DEFAULT_DOCS_DIR)
    parser.add_argument(
        "--full-report-text", type=Path, default=DEFAULT_FULL_REPORT_TEXT
    )
    parser.add_argument("--law-dir", type=Path, default=DEFAULT_LAW_DIR)
    parser.add_argument(
        "--raw",
        type=Path,
        default=DEFAULT_EVIDENCE_DIR / "raw" / f"{OUTPUT_STEM}.pkl",
        help="where PolicyEngine-US's raw outputs are kept (not committed)",
    )
    parser.add_argument(
        "--reuse-raw",
        action="store_true",
        help="development only: read the raw outputs instead of running",
    )
    parser.add_argument(
        "--pe-us-python",
        default=None,
        help=f"interpreter with policyengine-us (else ${bridge.PE_US_PYTHON_ENV})",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=minimum.RUN_TIMEOUT_SECONDS,
        help="seconds each policyengine-us child may take",
    )
    args = parser.parse_args(argv)
    document, rows = build(
        args.pe_us_python,
        docs_dir=args.docs_dir,
        full_report_text=args.full_report_text,
        law_dir=args.law_dir,
        timeout=args.timeout,
        raw_path=args.raw,
        reuse_raw=args.reuse_raw,
    )
    for directory in (args.out_dir, args.docs_dir):
        for path in write(document, rows, directory):
            print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
