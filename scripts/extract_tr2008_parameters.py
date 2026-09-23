"""Extract 2008 Trustees Report parameters for DynaSim exercise 1 (Track A2).

Every value in ``data/external/tr2008/tr2008_report.json`` is re-parsed from
the 2008 OASDI Trustees Report PDF (House Document 110-104) with
``pdftotext -layout``, one page at a time, and carries its PDF page index,
printed page number and table id.  Values the printed report does not carry
(single-year AWI after 2017, single-year life expectancy, the plot points of
the DI figures) come from 2008-vintage SSA web pages recovered from the
Internet Archive, because ssa.gov answers HTTP 403 to programmatic fetches.
Those captures are committed gzip-compressed under
``data/external/tr2008/sources/`` and each payload is pinned by SHA-256 and
by the Wayback CDX SHA-1 digest.

The transcription check compares every PDF table cell and every text-stated
value against an independent HTML rendering published with the report (the
report's own HTML chapters and the single-year supplemental tables).  The
build fails unless every compared cell agrees.

TR2008 publishes no DI rates by age.  The report cites Actuarial Study 118
(June 2005) as the 1996-2000 base of its long-range termination rates by
age, sex and duration; that PDF is parsed into ``actuarial_study_118.json``
and checked against itself (its survival tables are computed from its
probability tables, and its combined table from its death and recovery
tables).

Run from the repository root (needs poppler's ``pdftotext``)::

    .venv/bin/python scripts/extract_tr2008_parameters.py \
        --pdf /path/to/tr08-2008-oasdi-trustees-report.pdf \
        --as118-pdf /path/to/actuarial-study-118.pdf

``POPULACE_DYNAMICS_TR2008_PDF`` and ``POPULACE_DYNAMICS_AS118_PDF`` may be
used instead of the flags.  With ``--check`` the script rebuilds in memory
and fails if any committed JSON differs, without writing.
"""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import os
import re
import subprocess
import sys
from collections.abc import Iterable, Mapping, Sequence
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "external" / "tr2008"
SOURCES_DIR = OUT_DIR / "sources"
DEFAULT_PDF = (
    Path.home()
    / "microcosm-launch-evidence"
    / "dynasim-parity-20260909"
    / "tr2008-inputs-20260922"
    / "tr08-2008-oasdi-trustees-report.pdf"
)
PDF_ENV = "POPULACE_DYNAMICS_TR2008_PDF"

PDF_SHA256 = "517de81a7eb57dc5bc6e14c4dd9f635bce954701b28fa05dafd9bef1ae16172f"
PDF_WAYBACK_SHA1_B32 = "3763FHME6PHT7EBSHGDRUWB4FYNIC7OR"
PDF_BYTES = 1_295_810
PDF_PAGES = 235
# PDF page index (1-based) = printed page number + 8 throughout the body.
PRINTED_PAGE_OFFSET = 8

# Actuarial Study 118 (June 2005), the source TR2008 V.C.6.b cites for the
# 1996-2000 base of its long-range DI termination rates.  Not committed: the
# repository's pre-commit configuration rejects added files over 500 KB.
AS118_DEFAULT_PDF = (
    Path.home()
    / "microcosm-launch-evidence"
    / "dynasim-parity-20260909"
    / "tr2008-a2-sources-20260922"
    / "actuarial-study-118.pdf"
)
AS118_ENV = "POPULACE_DYNAMICS_AS118_PDF"
AS118_ORIGINAL_URL = "http://www.ssa.gov/OACT/NOTES/pdf_studies/study118.pdf"
AS118_WAYBACK_TIMESTAMP = "20080326052706"
AS118_SHA256 = (
    "ecf8af4de3ae6746d79da9da5597b2b4fc550c6d3c18f0fccce0bce31a15ba0b"
)
AS118_WAYBACK_SHA1_B32 = "HDNKVLGFHW3C5TOTMKXXINODJHUNTPKA"
AS118_BYTES = 679_311
AS118_PAGES = 102
# PDF page index (1-based) = printed page number + 12 in the table pages.
AS118_PRINTED_PAGE_OFFSET = 12

RETRIEVED = "2026-09-22"
ALTERNATIVES = ("intermediate", "low_cost", "high_cost")
SECTION_LABELS = {
    "Historical data:": "historical",
    "Intermediate:": "intermediate",
    "Low Cost:": "low_cost",
    "High Cost:": "high_cost",
    "Projected:": "projected",
}

REPORT_JSON = OUT_DIR / "tr2008_report.json"
SINGLE_YEAR_JSON = OUT_DIR / "tr2008_single_year.json"
SSA_2008_JSON = OUT_DIR / "ssa_2008_vintage.json"
AS118_JSON = OUT_DIR / "actuarial_study_118.json"
CHECK_JSON = OUT_DIR / "transcription_check.json"
SOURCES_JSON = OUT_DIR / "sources.json"

# name -> (wayback timestamp, original URL, CDX SHA-1 base32, payload
# sha256, payload bytes, what it is used for)
WAYBACK_SOURCES: dict[str, tuple[str, str, str, str, int, str]] = {
    "tr08_II_assump.html": (
        "20080326020650",
        "http://www.ssa.gov/OACT/TR/TR08/II_assump.html",
        "3GU5S4YX7TLGLBTDIPQG7EOIXWKW5P3P",
        "8c56352cf27f28f61c33afeea881eac2d8f58fb522bd11acba3eb393c19f2dbc",
        45591,
        "HTML rendering of Table II.C1 (transcription check)",
    ),
    "tr08_V_economic.html": (
        "20080326020638",
        "http://www.ssa.gov/OACT/TR/TR08/V_economic.html",
        "YGPINSMAZHNF62RNIJICDUJZFG6DJJUC",
        "d83f79078dfa1a048d6d96d1c0e63cdd109a3e7f5e585359c25a7698ea21b139",
        775403,
        "HTML rendering of Table V.B1 (transcription check)",
    ),
    "tr08_V_demographic.html": (
        "20080326020435",
        "http://www.ssa.gov/OACT/TR/TR08/V_demographic.html",
        "CM743TXXKHPV5J4RWERTWDCX77NCKCTA",
        "747a589dfe04cd93608ba0b16782da32970dc541ebf7ea0ba6dfdaa62657b2c7",
        1584351,
        "HTML rendering of Tables V.A1, V.A3, V.A4 (transcription check)",
    ),
    "tr08_V_programatic.html": (
        "20080326020449",
        "http://www.ssa.gov/OACT/TR/TR08/V_programatic.html",
        "Z4IT34VNTEHFSK3VLKESHBVGIMDOVN6Z",
        "8322fbec231e6c9fb62d0d80fcf878c6c16a15ce2e4b551f4b217d7715183961",
        1685552,
        "HTML rendering of Tables V.C1 and V.C5 (transcription check)",
    ),
    "tr08_VI_OASDHI_dollars.html": (
        "20080326020725",
        "http://www.ssa.gov/OACT/TR/TR08/VI_OASDHI_dollars.html",
        "5S4HM75GE7WO3KR2TDVKUKIOGSLD6S6U",
        "74131fb7f785bf123d72bf4f17283b9f61cdad341f1052ed62020ac874bfc54c",
        1622237,
        "HTML rendering of Table VI.F6 (transcription check)",
    ),
    "tr08_VI_LRsensitivity.html": (
        "20080326020635",
        "http://www.ssa.gov/OACT/TR/TR08/VI_LRsensitivity.html",
        "YWGKUFHTKFECNFSDK7RZ7QY63MXQ4WPB",
        "95b4517516b67ce1e4ad99b6b354b4c6bc94ddf7676642287b3dcb220f14625e",
        304583,
        "HTML rendering of section VI.D (transcription check of the "
        "VI.D2, VI.D7 and VI.D8 text assumptions)",
    ),
    "tr08_lrIndex.html": (
        "20080325214003",
        "http://www.ssa.gov/OACT/TR/TR08/lrIndex.html",
        "JVH4NRWV2KCNNO2Y2AM755D5CFFRTVWH",
        "562b665ce7b0d6cc612f223d75c463666a273845ba44e21969e853e612c224de",
        12026,
        "Index page: 'Single-Year Tables Consistent with 2008 OASDI "
        "Trustees Report'",
    ),
    "tr08_lr5a1.html": (
        "20080326020320",
        "http://www.ssa.gov/OACT/TR/TR08/lr5a1.html",
        "SAVGX6ODG5AOP34EPQKSUDWGFJDVEUKJ",
        "7a8904e27b4fa7bc4b433072587b1d53c93ea28e70a71ca560a52bba40d00194",
        120442,
        "Single-year V.A1 (age-sex-adjusted death rates, 1940-2085)",
    ),
    "tr08_lr5a3.html": (
        "20080326020330",
        "http://www.ssa.gov/OACT/TR/TR08/lr5a3.html",
        "GD3TN4G36Z3M4XMPC5KYO2JLOQANFQ3V",
        "9c541081d3d3eadb3c7e94ccb27a1a3e7207a1a6583ccad916135b88a16f0c02",
        96268,
        "Single-year V.A3 (period life expectancy)",
    ),
    "tr08_lr5a4.html": (
        "20080326020337",
        "http://www.ssa.gov/OACT/TR/TR08/lr5a4.html",
        "ECKY5GCV6ZEWFNQR6Z63CDNCYF2NVZWB",
        "d111bff7330e0e9fc7aa6e1867bcedbf6fd0a2bb5ef53aa141fc3c95f4430b15",
        107887,
        "Single-year V.A4 (cohort life expectancy)",
    ),
    "tr08_lr5b1.html": (
        "20080326020318",
        "http://www.ssa.gov/OACT/TR/TR08/lr5b1.html",
        "ISF37SI3EIAJRJMO2ELIHXLLL3JG36B7",
        "186ec9c3224d568162a5aca7dab20bc55e532bd665fb3a2695d4ef1ac6b139ea",
        120719,
        "Single-year V.B1 (CPI and average covered wage growth, 1960-2082)",
    ),
    "tr08_lr5c5.html": (
        "20080326020347",
        "http://www.ssa.gov/OACT/TR/TR08/lr5c5.html",
        "4PAN6TNRDLD7L36XVK2PXJEHHPHYWMQT",
        "58938c53d19b551930350569e5ef540016a6e2841f8b38aa7a24f8fabe308ac8",
        99287,
        "Single-year V.C5 (DI beneficiaries and prevalence, 1975-2085)",
    ),
    "tr08_lr6f6.html": (
        "20080326020333",
        "http://www.ssa.gov/OACT/TR/TR08/lr6f6.html",
        "LDF76UQCZLJHN4S6NSB2652WMJFMTDKX",
        "57bd597a0184bc5b95b03797ebe75eada22ee0d18386f8d24d45ad861b5d8082",
        87966,
        "Single-year VI.F6 (AWI and adjusted CPI, 2007-2085)",
    ),
    "tr08_LD_figVC3.html": (
        "20080326020509",
        "http://www.ssa.gov/OACT/TR/TR08/LD_figVC3.html",
        "EWYGHFYVYCKVAB7PCSDSJA6DZF5S7QQ6",
        "b19dd313f27f75bc86a43215189bfa3b72899e5a59e15ad55c0ef9642922dd24",
        370890,
        "Plot points of Figure V.C3 (DI incidence rates, 1970-2085)",
    ),
    "tr08_LD_figVC4.html": (
        "20080326020514",
        "http://www.ssa.gov/OACT/TR/TR08/LD_figVC4.html",
        "YQPBPOCEOKEZEFOUFA5XB5D6ALB47R6Q",
        "de26599c0980684d02d99f4e6814b328420da23b7e8fe5341f8ea1fe1478e2b0",
        371388,
        "Plot points of Figure V.C4 (DI termination rates, 1970-2085)",
    ),
    "tr08_LD_figVC5.html": (
        "20080326093218",
        "https://www.ssa.gov/OACT/TR/TR08/LD_figVC5.html",
        "EUDTOGGM5PKEBU45SXMEVQUBVPBA4AIF",
        "bb9fd6bac0c2a8899b9f3af13ed0eb0a5abd193221af711c05e6e8e03947dc9f",
        457114,
        "Plot points of Figure V.C5 (DI incidence, termination and "
        "conversion, intermediate)",
    ),
    "tr08_LD_figVC6.html": (
        "20080326020519",
        "http://www.ssa.gov/OACT/TR/TR08/LD_figVC6.html",
        "4TPJFHOB3O6GAQ74BBC63OE27SVAXL4Q",
        "8071e1ffe48169584c5f549f9afe256c8cd978ddcd284ac6e0261053d8705a4f",
        371360,
        "Plot points of Figure V.C6 (DI prevalence rates, 1970-2085)",
    ),
    "oact_stats_table4c6_20080410175446.html": (
        "20080410175446",
        "http://www.ssa.gov:80/OACT/STATS/table4c6.html",
        "UEUMCN7DHDCRY25C7VNVJCBTCGWH4ZH5",
        "0135d0123ab1a2457c8e075d91b97297e65d2cbce4ddbaa9025985c9119ec9ee",
        30117,
        "OACT 'Period Life Table, 2004' as posted March 27, 2008",
    ),
    "supplement2008_4c.html": (
        "20090409210138",
        "http://www.ssa.gov:80/policy/docs/statcomps/supplement/2008/4c.html",
        "Y2RBRJL6KDDRZAWFO3WZXRQKFTQEQKRX",
        "d220b70327c9e229f83eb31376c958fb512bdaf0f09468709e46c03b9dbdb47c",
        141060,
        "Annual Statistical Supplement 2008, section 4.C (insured status "
        "by sex and age; period life table 2004)",
    ),
    "di_asr2008_sect01a.html": (
        "20090827055808",
        "http://www.ssa.gov/policy/docs/statcomps/di_asr/2008/sect01a.html",
        "VWKIOT4ZHUQZWSMRUUC6DFNQYHD47DHK",
        "99c84f8e9eaa591834dd9583b6a0a8928770b85ac9231455d6688ddf0b6d4e97",
        30879,
        "DI Annual Statistical Report 2008, Tables 1-2 (all disabled "
        "beneficiaries in current-payment status; Table 2 by basis of "
        "entitlement, age and sex)",
    ),
    "di_asr2008_sect01c.html": (
        "20090827055731",
        "http://www.ssa.gov/policy/docs/statcomps/di_asr/2008/sect01c.html",
        "P6N3DFNAOXBWYL2QZM6WURCSMDLNJDQI",
        "c22c7d116bd1d07ca08c05c7aeff8ee3d06f69cfb022be23a55171548607df20",
        189712,
        "DI Annual Statistical Report 2008, Tables 19-20 (disabled workers "
        "in current-payment status by sex and age)",
    ),
    "di_asr2008_sect03a.html": (
        "20090827055740",
        "http://www.ssa.gov/policy/docs/statcomps/di_asr/2008/sect03a.html",
        "HM63AQEHSSQ55NZ4HOBVKVOMUOHT7ZLP",
        "9a58330d8a30780ac4fa773903ade83bba7ebd407b253a27458199503f106bce",
        30751,
        "DI Annual Statistical Report 2008, Tables 35-36 (awards)",
    ),
    "di_asr2008_sect03c.html": (
        "20090827055738",
        "http://www.ssa.gov/policy/docs/statcomps/di_asr/2008/sect03c.html",
        "5EYVQLVOAA5Z4HDWZ6UZBHJXVYZZND4M",
        "99e35d8ddc133356fe42aeab2fdbe0ec4876cd35efb0d220988e41f7c4126071",
        171638,
        "DI Annual Statistical Report 2008, Table 39 (awards to disabled "
        "workers by sex and age)",
    ),
    "di_asr2008_sect03f.html": (
        "20090827055729",
        "http://www.ssa.gov/policy/docs/statcomps/di_asr/2008/sect03f.html",
        "FFSEMMDNUND522QVF5EMVDVX55ZS4EQM",
        "8b26e9ec4bbcb6dcc92d71fee7b32d9d9539d47aae98e956f8e0500d67694546",
        47749,
        "DI Annual Statistical Report 2008, Tables 49-50 (terminations)",
    ),
    "di_asr2008_sect03g.html": (
        "20090827055722",
        "http://www.ssa.gov/policy/docs/statcomps/di_asr/2008/sect03g.html",
        "5BHRW5BLJT3RD6TJQPH73MJAXJFEZTOK",
        "ec10e14e504bd57aca0d6e1a3aa86d36c56c3bd56bdb0f600e1bce5c9cc412b7",
        66434,
        "DI Annual Statistical Report 2008, Tables 52-57 (disabled "
        "workers who work; Table 57: terminations because of successful "
        "return to work, by sex and age)",
    ),
}

# Located 2008-vintage sources that are recorded but not committed or
# transcribed (PDFs; see provenance.md for what each would supply).  An
# entry with ``sha256`` None was located through the Wayback CDX API but
# never downloaded; only its CDX digest is known.
LOCATED_EXTERNAL_SOURCES = {
    "tr08_release_pdf": {
        "original_url": "http://www.ssa.gov/OACT/TR/TR08/tr08.pdf",
        "wayback_timestamp": "20080325214024",
        "wayback_sha1_b32": "ESPELEJP2GMGTFGUIOBDRMBY7YCMAVLN",
        "sha256": (
            "c3344158551835b7abbdf4e047f741ecb2f634c0f204f586cf74c27f7b90e2ca"
        ),
        "bytes": 1111230,
        "role": (
            "Release-day (2008-03-25) PDF. Not the transcription source; "
            "used once to confirm that the numeric tokens on every page "
            "transcribed here are identical to the printed House Document "
            "version (see provenance.md)."
        ),
    },
    "actuarial_study_120": {
        "original_url": (
            "http://www.ssa.gov/OACT/NOTES/pdf_studies/study120.pdf"
        ),
        "wayback_timestamp": "20080326052709",
        "wayback_sha1_b32": "CFR6TTHSRZ4JX577UND4RXHQOCMO5NAL",
        "sha256": (
            "f9aadc8cad678b2febd8658b6f5aedfe6cc5496fa5894b7cbaf9250560225003"
        ),
        "bytes": 933405,
        "role": (
            "Actuarial Study 120 (2005), 'Life Tables for the United States "
            "Social Security Area 1900-2100'. Projected age-specific death "
            "probabilities, but on 2005 Trustees Report assumptions, not "
            "TR2008. Located; not transcribed here."
        ),
    },
    "tr08_long_range_methods_documentation": {
        "original_url": (
            "http://www.ssa.gov/OACT/TR/TR08/documentation_2008.pdf"
        ),
        "wayback_timestamp": "20080921133142",
        "wayback_sha1_b32": "EUNJVAMTFCUTPS4MB2LXXSYPVFU5XEVG",
        "sha256": None,
        "bytes": None,
        "examined": False,
        "role": (
            "SSA's TR08 index page (Wayback 20080914130458, CDX SHA-1 "
            "27K37ORAHG5SLVHSRFH4NC6MCMFPEDDQ) links this file as "
            "'Description of the methods used in the long range "
            "projections that determine the actuarial status of the trust "
            "funds'; in the release-period index (Wayback 20080509192827) "
            "the same link pointed to documentation_2007.pdf. Located "
            "through the Wayback CDX API and those index pages only. The "
            "PDF was not downloaded, so its payload SHA-256 and size are "
            "not recorded and its contents are unknown, including whether "
            "it tabulates death, DI incidence or DI termination rates by "
            "age and sex. A 2008-08-29 capture of http://ssa.gov/... has "
            "a different CDX digest (7Y5NCXRZVCT6VCHJ4M7WCLAAIWW6NKEC) "
            "and was not examined either."
        ),
    },
}


# --------------------------------------------------------------------------
# Generic helpers
# --------------------------------------------------------------------------


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha1_b32(data: bytes) -> str:
    return base64.b32encode(hashlib.sha1(data).digest()).decode("ascii")


def _normalize(text: str) -> str:
    """Collapse whitespace and drop soft hyphens and non-breaking spaces."""
    text = text.replace("\xad", "").replace("\xa0", " ")
    for dash in "\u2010\u2011\u2012\u2212":
        text = text.replace(dash, "-")
    return " ".join(text.split())


def _num(token: str) -> float | int | None:
    """Parse a printed numeric cell; ``None`` for not-available markers."""
    cleaned = token.strip().replace("$", "").replace(",", "")
    if cleaned in {"", "--", "...", ". . .", "(NA)"}:
        return None
    if not re.fullmatch(r"-?(\d+\.?\d*|\.\d+)", cleaned):
        raise ValueError(f"not a numeric cell: {token!r}")
    if "." in cleaned:
        return float(cleaned)
    return int(cleaned)


def _num_required(token: str) -> float | int:
    value = _num(token)
    if value is None:
        raise ValueError(
            f"missing value where a number is required: {token!r}"
        )
    return value


def _encode(value: Any, level: int) -> str:
    """Indented JSON whose scalar-only rows sit on one line each."""
    one_line = json.dumps(value, sort_keys=True, ensure_ascii=False)
    if not isinstance(value, (dict, list)) or len(one_line) <= 480:
        return one_line
    pad = "  " * (level + 1)
    if isinstance(value, dict):
        items = [
            f"{pad}{json.dumps(key, ensure_ascii=False)}: {_encode(value[key], level + 1)}"
            for key in sorted(value)
        ]
        if not items:
            return "{}"
        return "{\n" + ",\n".join(items) + "\n" + "  " * level + "}"
    items = [f"{pad}{_encode(item, level + 1)}" for item in value]
    if not items:
        return "[]"
    return "[\n" + ",\n".join(items) + "\n" + "  " * level + "]"


def _json_dump(payload: Any) -> str:
    text = _encode(payload, 0) + "\n"
    if json.loads(text) != payload:
        raise AssertionError("compact JSON encoding changed the payload")
    return text


# --------------------------------------------------------------------------
# PDF access
# --------------------------------------------------------------------------


class ReportPdf:
    """Page-level access to a pinned PDF through pdftotext.

    Defaults pin the TR2008 PDF; ``study_118_pdf`` pins Actuarial Study 118.
    """

    def __init__(
        self,
        path: Path,
        *,
        sha256: str = PDF_SHA256,
        sha1_b32: str = PDF_WAYBACK_SHA1_B32,
        size: int = PDF_BYTES,
        label: str = "TR2008",
    ) -> None:
        raw = path.read_bytes()
        digest = _sha256(raw)
        if digest != sha256:
            raise ValueError(
                f"{path} sha256 {digest} != pinned {sha256}; this is not "
                f"the reviewed {label} PDF"
            )
        if _sha1_b32(raw) != sha1_b32 or len(raw) != size:
            raise ValueError(
                f"{label} PDF SHA-1/length does not match the CDX record"
            )
        self.path = path
        self._cache: dict[int, str] = {}

    def page(self, index: int) -> str:
        """Return ``pdftotext -layout`` text for one 1-based PDF page."""
        if index not in self._cache:
            result = subprocess.run(
                [
                    "pdftotext",
                    "-layout",
                    "-f",
                    str(index),
                    "-l",
                    str(index),
                    str(self.path),
                    "-",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self._cache[index] = result.stdout
        return self._cache[index]

    def lines(self, indexes: Iterable[int]) -> list[tuple[int, str]]:
        return [
            (index, line)
            for index in indexes
            for line in self.page(index).splitlines()
        ]


def study_118_pdf(path: Path) -> ReportPdf:
    return ReportPdf(
        path,
        sha256=AS118_SHA256,
        sha1_b32=AS118_WAYBACK_SHA1_B32,
        size=AS118_BYTES,
        label="Actuarial Study 118",
    )


def _printed(pdf_page: int) -> int:
    return pdf_page - PRINTED_PAGE_OFFSET


def _locator(table: str, pdf_pages: Sequence[int]) -> dict[str, Any]:
    return {
        "table": table,
        "pdf_pages": list(pdf_pages),
        "printed_pages": [_printed(page) for page in pdf_pages],
    }


_YEAR_ROW = re.compile(
    r"^\s*(?P<year>\d{4})(?P<fn>\d)?(?:\s+(?P<fn2>\d))?\s*(?:\.(?!\d)\s*)+(?P<rest>.*\S)\s*$"
)
_RANGE_ROW = re.compile(
    r"^\s*(?P<first>\d{4}) to (?P<last>\d{4})\s*(?:\.(?!\d)\s*)+(?P<rest>.*\S)\s*$"
)


def _section(line: str) -> str | None:
    stripped = line.strip()
    return SECTION_LABELS.get(stripped)


# --------------------------------------------------------------------------
# Table V.C1 (COLA, AWI, contribution base, earnings-test amounts)
# --------------------------------------------------------------------------

VC1_PAGES = (110, 111)
VC1_COLUMNS = (
    "cola_percent",
    "awi",
    "awi_increase_percent",
    "contribution_benefit_base",
    "ret_exempt_under_nra",
    "ret_exempt_at_nra",
)
VC1_ACTUAL_COLUMNS = (
    "contribution_benefit_base",
    "ret_exempt_under_nra",
    "ret_exempt_at_nra",
)


def _vc1_footnotes(section: str, year: int) -> dict[str, str]:
    """Footnote markers printed inside V.C1 value cells.

    Footnote 6 marks the 1999 COLA (originally 2.4, effectively 2.5 under
    P.L. 106-554); footnote 7 ('Actual amount, as determined under
    automatic-adjustment provisions') marks the 2007 COLA and the 2007-2008
    base and exempt amounts in every alternative.
    """
    if section == "historical" and year == 1999:
        return {"cola_percent": "6"}
    if section in ALTERNATIVES and year == 2007:
        return {"cola_percent": "7", **dict.fromkeys(VC1_ACTUAL_COLUMNS, "7")}
    if section in ALTERNATIVES and year == 2008:
        return dict.fromkeys(VC1_ACTUAL_COLUMNS, "7")
    return {}


def _take_footnoted(
    tokens: list[str], columns: Sequence[str], markers: Mapping[str, str]
) -> dict[str, float | int]:
    """Consume one value per column, removing expected footnote markers."""
    values: dict[str, float | int] = {}
    queue = list(tokens)
    for column in columns:
        if not queue:
            raise ValueError(f"row ended before column {column}: {tokens}")
        marker = markers.get(column)
        token = queue.pop(0)
        if marker is not None:
            if token == marker:
                token = queue.pop(0)
            elif token.startswith(marker) and len(token) > len(marker):
                token = token[len(marker) :]
            else:
                raise ValueError(
                    f"expected footnote {marker} before {column}: {tokens}"
                )
        values[column] = _num_required(token)
    if queue:
        raise ValueError(f"unconsumed tokens {queue} in {tokens}")
    return values


def parse_vc1(pdf: ReportPdf) -> dict[str, Any]:
    sections: dict[str, list[dict[str, Any]]] = {}
    section = None
    for page, line in pdf.lines(VC1_PAGES):
        label = _section(line)
        if label:
            section = label
            sections.setdefault(section, [])
            continue
        match = _YEAR_ROW.match(line)
        if not match or section is None:
            continue
        year = int(match["year"])
        markers = _vc1_footnotes(section, year)
        values = _take_footnoted(match["rest"].split(), VC1_COLUMNS, markers)
        sections[section].append(
            {
                "year": year,
                "pdf_page": page,
                **values,
                **(
                    {"footnotes": dict(sorted(markers.items()))}
                    if markers
                    else {}
                ),
            }
        )
    expected = {
        "historical": list(range(1975, 2007)),
        "intermediate": list(range(2007, 2018)),
        "low_cost": list(range(2007, 2018)),
        "high_cost": list(range(2007, 2018)),
    }
    observed = {
        key: [row["year"] for row in rows] for key, rows in sections.items()
    }
    if observed != expected:
        raise ValueError(f"V.C1 year coverage {observed} != {expected}")
    return {
        **_locator("V.C1", VC1_PAGES),
        "title": (
            "Cost-of-Living Benefit Increases, Average Wage Index, "
            "Contribution and Benefit Bases, and Retirement Earnings Test "
            "Exempt Amounts, 1975-2017"
        ),
        "columns": {
            "cola_percent": (
                "OASDI benefit increase (percent); footnote 1: effective with "
                "benefits payable for June in each year 1975-82, and for "
                "December in each year after 1982"
            ),
            "awi": "Average wage index (AWI), dollars",
            "awi_increase_percent": "AWI increase (percent)",
            "contribution_benefit_base": "OASDI contribution and benefit base, dollars",
            "ret_exempt_under_nra": "Retirement earnings test exempt amount, under NRA, dollars",
            "ret_exempt_at_nra": "Retirement earnings test exempt amount, year of NRA, dollars",
        },
        "footnote_markers": {
            "6": "Originally determined as 2.4 percent, but pursuant to Public Law 106-554, is effectively 2.5 percent.",
            "7": "Actual amount, as determined under automatic-adjustment provisions.",
        },
        "sections": sections,
    }


# --------------------------------------------------------------------------
# Table V.B1 (principal economic assumptions)
# --------------------------------------------------------------------------

VB1_PAGES = (100, 101)
VB1_COLUMNS = (
    "productivity",
    "earnings_to_compensation",
    "average_hours_worked",
    "gdp_price_index",
    "average_covered_wage",
    "cpi",
    "real_wage_differential",
)


def parse_vb1(pdf: ReportPdf) -> dict[str, Any]:
    sections: dict[str, dict[str, list[dict[str, Any]]]] = {}
    section = None
    for page, line in pdf.lines(VB1_PAGES):
        label = _section(line)
        if label:
            section = label
            sections.setdefault(section, {"years": [], "ranges": []})
            continue
        if section is None:
            continue
        match = _RANGE_ROW.match(line)
        if match:
            values = dict(
                zip(
                    VB1_COLUMNS,
                    map(_num_required, match["rest"].split()),
                    strict=True,
                )
            )
            sections[section]["ranges"].append(
                {
                    "first_year": int(match["first"]),
                    "last_year": int(match["last"]),
                    "pdf_page": page,
                    **values,
                }
            )
            continue
        match = _YEAR_ROW.match(line)
        if match:
            values = dict(
                zip(
                    VB1_COLUMNS,
                    map(_num_required, match["rest"].split()),
                    strict=True,
                )
            )
            row: dict[str, Any] = {
                "year": int(match["year"]),
                "pdf_page": page,
                **values,
            }
            if match["fn"]:
                row["footnote"] = match["fn"]
            sections[section]["years"].append(row)
    for key in ALTERNATIVES:
        years = [row["year"] for row in sections[key]["years"]]
        if years != list(range(2008, 2018)):
            raise ValueError(f"V.B1 {key} years {years}")
        ranges = [
            (r["first_year"], r["last_year"]) for r in sections[key]["ranges"]
        ]
        if ranges != [(2015, 2020), (2020, 2082)]:
            raise ValueError(f"V.B1 {key} ranges {ranges}")
    return {
        **_locator("V.B1", VB1_PAGES),
        "title": "Principal Economic Assumptions",
        "units": (
            "Annual percentage change from the prior year for single-year "
            "rows; compound average annual percentage change for ranges "
            "(footnote 1). Real-wage differential: unrounded covered-wage "
            "growth less unrounded CPI growth (footnote 2)."
        ),
        "footnote_3": (
            "Historical data are not available for the full year [2007]. "
            "Estimated values vary slightly by alternative and are shown "
            "for the intermediate alternative."
        ),
        "cpi_concept": (
            "Annual-average CPI-W growth by calendar year. This is not the "
            "COLA, which V.C1 reports on the third-quarter-over-third-quarter "
            "statutory basis (e.g. 2008: V.B1 CPI 2.8, V.C1 COLA 2.7)."
        ),
        "sections": sections,
    }


# --------------------------------------------------------------------------
# Table VI.F6 (selected economic variables incl. AWI and adjusted CPI)
# --------------------------------------------------------------------------

VIF6_PAGES = (192, 193)
VIF6_COLUMNS = (
    "adjusted_cpi",
    "awi",
    "taxable_payroll_billions",
    "gdp_billions",
    "compound_interest_rate_factor",
)


def parse_vif6(pdf: ReportPdf) -> dict[str, Any]:
    sections: dict[str, list[dict[str, Any]]] = {}
    section = None
    for page, line in pdf.lines(VIF6_PAGES):
        label = _section(line)
        if label:
            section = label
            sections.setdefault(section, [])
            continue
        match = _YEAR_ROW.match(line)
        if not match or section is None:
            continue
        values = dict(
            zip(
                VIF6_COLUMNS,
                map(_num_required, match["rest"].split()),
                strict=True,
            )
        )
        sections[section].append(
            {"year": int(match["year"]), "pdf_page": page, **values}
        )
    expected = list(range(2007, 2018)) + list(range(2020, 2086, 5))
    for key in ALTERNATIVES:
        if [row["year"] for row in sections[key]] != expected:
            raise ValueError(f"VI.F6 {key} coverage")
    return {
        **_locator("VI.F6", VIF6_PAGES),
        "title": "Selected Economic Variables, Calendar Years 2007-85",
        "columns": {
            "adjusted_cpi": "Adjusted CPI: the CPI-W indexed to calendar year 2008 (footnote 1)",
            "awi": "Average wage index, dollars",
            "taxable_payroll_billions": "OASDI taxable payroll, billions of dollars",
            "gdp_billions": "Gross domestic product, billions of dollars",
            "compound_interest_rate_factor": "Compound interest-rate factor (2008 = 1.0000)",
        },
        "sections": sections,
    }


# --------------------------------------------------------------------------
# Table II.C1 (ultimate assumptions)
# --------------------------------------------------------------------------

IIC1_PAGE = 14
IIC1_ROWS = (
    ("total_fertility_rate", "Total fertility rate"),
    (
        "death_rate_reduction_2032_2082",
        "adjusted death rates from 2032 to 2082",
    ),
    ("net_immigration_thousands_2008_82", "the period 2008-82"),
    ("productivity", "Productivity (total U.S. economy)"),
    ("average_covered_wage", "Average wage in covered employment"),
    ("cpi", "Consumer Price Index (CPI)"),
    ("real_wage_differential", "Real-wage differential (percent)"),
    ("unemployment_rate", "Unemployment rate (percent)"),
    ("real_interest_rate", "Annual trust fund real interest rate (percent)"),
)
_THREE_VALUES = re.compile(
    r"(?P<int>-?[\d,]*\.?\d+)\s+(?P<low>-?[\d,]*\.?\d+)\s+(?P<high>-?[\d,]*\.?\d+)\s*$"
)


def parse_iic1(pdf: ReportPdf) -> dict[str, Any]:
    text = pdf.page(IIC1_PAGE)
    start = text.index("Table II.C1.")
    lines = text[start:].splitlines()
    value_lines = [
        line
        for line in lines
        if _THREE_VALUES.search(line) and "Ultimate assumptions" not in line
    ]
    if len(value_lines) != len(IIC1_ROWS):
        raise ValueError(f"II.C1 value lines {value_lines}")
    rows: dict[str, Any] = {}
    for (key, fragment), line in zip(IIC1_ROWS, value_lines, strict=True):
        if fragment not in line:
            raise ValueError(f"II.C1 {key}: {fragment!r} not in {line!r}")
        match = _THREE_VALUES.search(line)
        assert match is not None
        rows[key] = {
            "intermediate": _num_required(match["int"]),
            "low_cost": _num_required(match["low"]),
            "high_cost": _num_required(match["high"]),
        }
    return {
        **_locator("II.C1", (IIC1_PAGE,)),
        "title": (
            "Ultimate Values of Key Demographic and Economic Assumptions for "
            "the Long-Range (75-year) Projection Period"
        ),
        "footnote_1": (
            "Ultimate values are assumed to be reached within 25 years. See "
            "chapter V for details, including historical values and "
            "projected values prior to reaching the ultimate."
        ),
        "rows": rows,
    }


# --------------------------------------------------------------------------
# Tables V.A1, V.A3, V.A4 (mortality summaries)
# --------------------------------------------------------------------------

VA1_PAGES = (88, 89)
VA1_COLUMNS = (
    "total_fertility_rate",
    "asadr_total",
    "asadr_under_65",
    "asadr_65_and_over",
    "net_legal_immigration",
    "net_other_immigration",
)


def parse_va1(pdf: ReportPdf) -> dict[str, Any]:
    sections: dict[str, list[dict[str, Any]]] = {}
    section = None
    for page, line in pdf.lines(VA1_PAGES):
        label = _section(line)
        if label:
            section = label
            sections.setdefault(section, [])
            continue
        match = _YEAR_ROW.match(line)
        if not match or section is None:
            continue
        tokens = match["rest"].split()
        if len(tokens) == 5:
            tokens = [*tokens, "--"]
        values = dict(zip(VA1_COLUMNS, map(_num, tokens), strict=True))
        row: dict[str, Any] = {
            "year": int(match["year"]),
            "pdf_page": page,
            **values,
        }
        if match["fn"]:
            row["footnote"] = match["fn"]
        sections[section].append(row)
    projected = list(range(2010, 2086, 5))
    for key in ALTERNATIVES:
        if [row["year"] for row in sections[key]] != projected:
            raise ValueError(f"V.A1 {key} coverage")
    return {
        **_locator("V.A1", VA1_PAGES),
        "title": "Principal Demographic Assumptions, Calendar Years 1940-2085",
        "asadr_definition": (
            "Age-sex-adjusted death rate per 100,000: the crude rate that "
            "would occur in the enumerated total population as of April 1, "
            "2000, if that population were to experience the death rates by "
            "age and sex observed in, or assumed for, the selected year "
            "(footnote 2)."
        ),
        "footnote_5": "Estimated.",
        "sections": sections,
    }


LE_COLUMNS = tuple(
    f"{alternative}_{age}_{sex}"
    for alternative in ("low_cost", "intermediate", "high_cost")
    for age in ("at_birth", "at_65")
    for sex in ("male", "female")
)


def _parse_life_expectancy(
    pdf: ReportPdf, pages: Sequence[int], table: str
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for page, line in pdf.lines(pages):
        match = _YEAR_ROW.match(line)
        if not match:
            continue
        tokens = match["rest"].split()
        row: dict[str, Any] = {"year": int(match["year"]), "pdf_page": page}
        footnote = match["fn"] or match["fn2"]
        if footnote:
            row["footnote"] = footnote
        if len(tokens) == 4:
            row.update(
                dict(
                    zip(
                        LE_COLUMNS[4:8],
                        map(_num_required, tokens),
                        strict=True,
                    )
                )
            )
            row["historical"] = True
        elif len(tokens) == 12:
            row.update(
                dict(zip(LE_COLUMNS, map(_num_required, tokens), strict=True))
            )
        else:
            raise ValueError(f"{table} row {line!r}")
        rows.append(row)
    return {**_locator(table, pages), "rows": rows}


def parse_va3(pdf: ReportPdf) -> dict[str, Any]:
    table = _parse_life_expectancy(pdf, (93,), "V.A3")
    years = [row["year"] for row in table["rows"]]
    expected = [
        *range(1940, 1995, 5),
        *range(1995, 2008),
        *range(2010, 2086, 5),
    ]
    if years != expected:
        raise ValueError(f"V.A3 years {years}")
    table["title"] = "Period Life Expectancy"
    table["note"] = (
        "Historical rows (through 2007; 2005-2007 footnote 2 'Estimated') "
        "carry one series printed under the intermediate columns."
    )
    return table


def parse_va4(pdf: ReportPdf) -> dict[str, Any]:
    table = _parse_life_expectancy(pdf, (94,), "V.A4")
    years = [row["year"] for row in table["rows"]]
    expected = [
        *range(1940, 1995, 5),
        *range(1995, 2008),
        *range(2010, 2086, 5),
    ]
    if years != expected:
        raise ValueError(f"V.A4 years {years}")
    table["title"] = "Cohort Life Expectancy"
    table["note"] = (
        "At birth: for those born on January 1 of the year. At 65: for "
        "those attaining age 65 on January 1 of the year."
    )
    return table


# --------------------------------------------------------------------------
# Table V.C5 (DI beneficiaries and prevalence)
# --------------------------------------------------------------------------

VC5_PAGES = (132, 133)
VC5_COLUMNS = (
    "disabled_workers_thousands",
    "spouses_thousands",
    "children_thousands",
    "total_thousands",
    "prevalence_gross_per_1000",
    "prevalence_age_sex_adjusted_per_1000",
)


def parse_vc5(pdf: ReportPdf) -> dict[str, Any]:
    sections: dict[str, list[dict[str, Any]]] = {}
    section = None
    for page, line in pdf.lines(VC5_PAGES):
        label = _section(line)
        if label:
            section = label
            sections.setdefault(section, [])
            continue
        match = _YEAR_ROW.match(line)
        if not match or section is None:
            continue
        tokens = match["rest"].split()
        if len(tokens) == 4:
            tokens = [*tokens, "--", "--"]
        values = dict(zip(VC5_COLUMNS, map(_num, tokens), strict=True))
        sections[section].append(
            {"year": int(match["year"]), "pdf_page": page, **values}
        )
    for key in ALTERNATIVES:
        if [row["year"] for row in sections[key]] != list(
            range(2010, 2086, 5)
        ):
            raise ValueError(f"V.C5 {key} coverage")
    return {
        **_locator("V.C5", VC5_PAGES),
        "title": (
            "DI Beneficiaries With Benefits in Current-Payment Status at the "
            "End of Calendar Years 1960-2085"
        ),
        "units": "Beneficiaries in thousands; prevalence rates per thousand disability insured",
        "sections": sections,
    }


# --------------------------------------------------------------------------
# Text-stated assumptions
# --------------------------------------------------------------------------

_N = r"(-?\d+(?:\.\d+)?)"
# (id, pdf pages, regex over whitespace-normalized page text, group -> key,
#  unit, meaning)
TEXT_SPECS: tuple[
    tuple[str, tuple[int, ...], str, dict[str, str], str, str], ...
] = (
    (
        "cpi_ultimate_percent",
        (97,),
        rf"The ultimate annual increases in the CPI are assumed to be {_N}, {_N}, and {_N} percent for the low cost, intermediate, and high cost assumptions",
        {"1": "low_cost", "2": "intermediate", "3": "high_cost"},
        "percent per year",
        "Ultimate annual CPI increase (V.B.2).",
    ),
    (
        "cpi_intermediate_short_range",
        (97,),
        rf"For the intermediate assumptions, the annual change in the CPI is assumed to decrease from {_N} percent for 2007 to {_N} percent for 2009, then rise gradu(?:- | )?ally to the assumed ultimate rate of {_N} percent for 2010 and later",
        {"1": "2007", "2": "2009", "3": "2010_and_later"},
        "percent per year",
        "Intermediate CPI path stated in V.B.2 (annual-average basis).",
    ),
    (
        "covered_wage_ultimate_percent",
        (99,),
        rf"the assumed ultimate annual growth rates in the average covered wage are {_N}, {_N}, and {_N} percent for the low cost, intermediate, and high cost assumptions",
        {"1": "low_cost", "2": "intermediate", "3": "high_cost"},
        "percent per year",
        "Ultimate average covered wage growth (V.B.3).",
    ),
    (
        "mortality_historical_data_years",
        (82,),
        r"Historical death rates \(for years (\d{4})-(\d{4})\) used in developing estimates for this report",
        {"1": "first_year", "2": "last_year"},
        "calendar year",
        "Span of historical death rates underlying TR2008 (V.A.2).",
    ),
    (
        "mortality_ultimate_reduction_total_2032_2082",
        (84,),
        rf"projected to decline at ultimate average annual rates of about {_N} percent, {_N} percent, and {_N} percent between 2032 and 2082 for alternatives I, II, and III, respectively",
        {"1": "low_cost", "2": "intermediate", "3": "high_cost"},
        "percent per year",
        "Ultimate average annual decline in the total age-sex-adjusted death rate, 2032-2082 (V.A.2).",
    ),
    (
        "mortality_ultimate_reduction_65_plus_2032_2082",
        (84,),
        rf"age-sex-adjusted death rates for ages 65 and over are projected to decline at average annual rates of about {_N} percent, {_N} percent, and {_N} percent between 2032 and 2082 for alternatives I, II, and III, respectively",
        {"1": "low_cost", "2": "intermediate", "3": "high_cost"},
        "percent per year",
        "Ultimate average annual decline in the age-sex-adjusted death rate at 65+, 2032-2082 (V.A.2).",
    ),
    (
        "mortality_transition_rule",
        (83, 84),
        r"After (\d{4}), the reductions in central death rates for alternative II are assumed to change rapidly from the average annual reductions by age group, sex, and cause of death observed between (\d{4}) and (\d{4}), to the ultimate annual percentage reductions by age group, sex, and cause of death assumed for (\d{4}) and later\. The reductions in death rates under alternatives I and III are also assumed to change rapidly to their ultimate levels, but start from lev(?:-.*?)?els which are, respectively, (\d+) or (\d+) percent of the average annual reduc(?:- | )?tions observed between 1984 and 2004",
        {
            "1": "transition_start_after_year",
            "2": "observed_base_first_year",
            "3": "observed_base_last_year",
            "4": "ultimate_from_year",
            "5": "low_cost_start_percent_of_observed",
            "6": "high_cost_start_percent_of_observed",
        },
        "calendar year / percent",
        "How TR2008 moves from observed 1984-2004 reductions to the 2032+ ultimate reductions (V.A.2). The age-group/cause-specific reductions themselves are not published.",
    ),
    (
        "mortality_average_reduction_2007_2082",
        (165,),
        rf"The age-sex-adjusted death rates decline at average annual rates of {_N} percent, {_N} percent, and {_N} percent for alternatives I, II, and III, respectively",
        {"1": "low_cost", "2": "intermediate", "3": "high_cost"},
        "percent per year",
        "Average annual geometric decline in the age-sex-adjusted death rate, 2007-2082 (VI.D2).",
    ),
    (
        "di_incidence_short_range_and_ultimate_years",
        (126,),
        r"For the first 10 years of the projection period \(through (\d{4})\) incidence rates reflect several factors .* After (\d{4}), age-sex-specific incidence rates are assumed to trend toward the ultimate rates assumed for the long-range projections, reaching these ultimate rates in (\d{4})",
        {
            "1": "short_range_through",
            "2": "trend_after",
            "3": "ultimate_reached",
        },
        "calendar year",
        "Timing of DI incidence assumptions (V.C.6.a).",
    ),
    (
        "di_ultimate_incidence_per_1000_exposed",
        (127,),
        rf"For the intermediate alternative, the ultimate age-sex-adjusted incidence rate \(adjusted to the disability exposed population for the year 2000\) for ages through 64 is assumed to be {_N} awards per thousand exposed population\. \d This level is about (\d+) percent higher than the average rate for the historical period 1970 through 2007\. The ultimate age-sex-adjusted incidence rates for the low cost and high cost alternatives are assumed to be {_N} and {_N} awards per thousand exposed",
        {
            "1": "intermediate",
            "2": "intermediate_percent_above_1970_2007_average",
            "3": "low_cost",
            "4": "high_cost",
        },
        "awards per 1,000 disability-exposed (age-sex-adjusted to 2000 exposed population, ages through 64)",
        "Ultimate DI incidence (V.C.6.a).",
    ),
    (
        "di_death_rate_short_range_per_1000",
        (128, 129),
        rf"the age-sex-adjusted death rate \(adjusted to the 2000 disabled-worker population\) under the intermediate assumptions is projected to gradually decline from {_N} deaths per thousand.*?beneficiaries in 2007 to about {_N} per thousand by 2017",
        {"1": "2007", "2": "2017"},
        "deaths per 1,000 disabled-worker beneficiaries (age-sex-adjusted to 2000)",
        "Intermediate DI death-termination rate, short range (V.C.6.b).",
    ),
    (
        "di_recovery_rate_short_range_per_1000",
        (129,),
        rf"The age-sex- ?adjusted recovery rate under the intermediate assumptions is assumed to rise from a relatively low level of {_N} per thousand beneficiaries in 2007 \(reflect(?:- | )?ing temporarily lower levels of continuing disability reviews\) to {_N} per thou(?:- | )?sand beneficiaries by 2017",
        {"1": "2007", "2": "2017"},
        "recoveries per 1,000 disabled-worker beneficiaries (age-sex-adjusted)",
        "Intermediate DI recovery rate, short range (V.C.6.b).",
    ),
    (
        "di_termination_low_high_relative_percent",
        (129,),
        r"Under low cost \(high cost\) assumptions, total age-sex-adjusted termination rates due to death and recovery are assumed to increase \(decrease\) to levels roughly (\d+)-(\d+) percent higher \(lower\) than those under the intermediate assumptions",
        {"1": "lower_bound", "2": "upper_bound"},
        "percent relative to intermediate",
        "Short-range low/high-cost DI termination relative to intermediate (V.C.6.b).",
    ),
    (
        "di_long_range_termination_base_period",
        (129,),
        r"For the long-range period \(post-2017\), death and recovery rates are projected relative to rates by age, sex, and duration of entitlement over the base period (\d{4})-(\d{4})",
        {"1": "first_year", "2": "last_year"},
        "calendar year",
        "Base period of the long-range DI termination rates (V.C.6.b; footnote cites Actuarial Study 118).",
    ),
    (
        "di_ultimate_recovery_per_1000",
        (129,),
        rf"The ultimate age-sex- ?adjusted recovery rate for disabled work(?:- | )?ers is assumed to be about {_N} per thousand beneficiaries\. Ultimate age-sex- ?adjusted recovery rates for low cost and high cost alternatives are assumed to reach about {_N} and {_N} recoveries per thousand beneficiaries, respectively\. For all three sets of assumptions, the ultimate recovery rates are reached in the twentieth year of the projection period \((\d{{4}})\)",
        {
            "1": "intermediate",
            "2": "low_cost",
            "3": "high_cost",
            "4": "ultimate_reached",
        },
        "recoveries per 1,000 disabled-worker beneficiaries (age-sex-adjusted)",
        "Ultimate DI recovery rates (V.C.6.b).",
    ),
    (
        "di_death_rate_2085_per_1000",
        (129,),
        rf"From the age-sex- ?adjusted death rate of {_N} per thousand beneficiaries in 2007, rates of {_N}, {_N}, and {_N} per thousand disabled-worker beneficiaries are projected for 2085 under the low cost, intermediate, and high cost assumptions",
        {"1": "2007", "2": "low_cost", "3": "intermediate", "4": "high_cost"},
        "deaths per 1,000 disabled-worker beneficiaries (age-sex-adjusted)",
        "DI death-termination rates in 2085 (V.C.6.b); death rates change at the same rate as general-population death rates.",
    ),
    (
        "di_workers_millions",
        (131, 132),
        rf"The number of disabled workers in cur(?:- | )?rent-payment status is projected to grow from {_N} million at the end of 2007, to {_N} million, {_N} million, and {_N} million at the end of.*?2085, under the low cost, intermediate, and high cost assumptions",
        {
            "1": "2007",
            "2": "low_cost_2085",
            "3": "intermediate_2085",
            "4": "high_cost_2085",
        },
        "millions of disabled workers in current-payment status",
        "DI worker counts (V.C.6.d).",
    ),
    (
        "di_prevalence_age_sex_adjusted_per_1000",
        (135,),
        rf"The age-sex-adjusted disabled-worker prevalence rate for ages through 64 is projected to grow from {_N} per thousand disability insured at the end of 2007, to {_N} per thousand at the end of 2085 under the intermediate assump(?:- | )?tions\. .* Under the low cost and high cost assumptions, the age-sex-adjusted disabil(?:- | )?ity prevalence rate is projected to decrease to {_N} per thousand and increase to {_N} per thousand insured workers at the end of 2085",
        {
            "1": "2007",
            "2": "intermediate_2085",
            "3": "low_cost_2085",
            "4": "high_cost_2085",
        },
        "per 1,000 disability insured (age-sex-adjusted to 2000 insured population)",
        "DI prevalence (V.C.6.d).",
    ),
    (
        "di_incidence_sensitivity_relative_to_1970_2007",
        (171,),
        r"In comparison to the his(?:- | )?torical period 1970 through 2007, the ultimate age-sex-adjusted incidence rate is (\d+) percent higher for alternative II, (\d+) percent lower for alternative I, and (\d+) percent higher for alternative III",
        {
            "1": "intermediate_percent_higher",
            "2": "low_cost_percent_lower",
            "3": "high_cost_percent_higher",
        },
        "percent relative to 1970-2007 average",
        "VI.D7 statement of ultimate DI incidence.",
    ),
    (
        "di_termination_sensitivity",
        (172,),
        r"For alternative II, the age-sex-adjusted 1 death rate is assumed to decline to a level at the end of the 75-year period that is about (\d+) percent lower than the level in 2007\. For alternative I, the age-sex-adjusted death rate is assumed to decline to a level in 2085 that is about (\d+) percent lower than the level in 2007\. For alternative III, the age-sex-adjusted death rate is assumed to decline to a level at the end of the 75-year period that is about (\d+) percent lower than the level in 2007\..*For alternative II, the age-sex-adjusted ?1 recovery rate in 2027 is about (\d+) recoveries per thousand disabled-worker beneficiaries\. For alternative I, the age-sex-adjusted recovery rate in 2027 is about (\d+) recover(?:- | )?ies per thousand disabled-worker beneficiaries\. For alternative III, the age- ?sex-adjusted recovery rate in 2027 is about (\d+) recoveries per thousand dis(?:- | )?abled-worker beneficiaries",
        {
            "1": "intermediate_death_decline_percent_2007_2085",
            "2": "low_cost_death_decline_percent_2007_2085",
            "3": "high_cost_death_decline_percent_2007_2085",
            "4": "intermediate_recovery_2027",
            "5": "low_cost_recovery_2027",
            "6": "high_cost_recovery_2027",
        },
        "percent / recoveries per 1,000",
        "VI.D8 statement of DI termination assumptions (age adjusted to disabled workers in current-payment status in 2000).",
    ),
    (
        "vc1_footnotes_timing",
        (111,),
        r"1 Effective with benefits payable for June in each year (\d{4})-(\d{2}), and for December in each year after (\d{4})\. 2 See table VI\.F6 for projected dollar amounts of the AWI beyond (\d{4})\.",
        {
            "1": "june_first_year",
            "2": "june_last_year_2digit",
            "3": "december_after_year",
            "4": "awi_table_beyond_year",
        },
        "calendar year",
        "COLA effective-month convention and AWI continuation pointer (V.C1 footnotes 1-2).",
    ),
    (
        "vif6_adjusted_cpi_base",
        (193,),
        r"1 The adjusted CPI is the CPI-W indexed to calendar year (\d{4})\.",
        {"1": "base_year"},
        "calendar year",
        "Adjusted CPI index base (VI.F6 footnote 1).",
    ),
)


def parse_text_values(pdf: ReportPdf) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for key, pages, pattern, groups, unit, meaning in TEXT_SPECS:
        text = _normalize(" ".join(pdf.page(page) for page in pages))
        match = re.search(pattern, text)
        if match is None:
            raise ValueError(f"text value {key} not found on pages {pages}")
        values = {
            name: _num_required(match.group(int(group)))
            for group, name in groups.items()
        }
        quote = match.group(0)
        out.append(
            {
                "id": key,
                "pdf_pages": list(pages),
                "printed_pages": [_printed(page) for page in pages],
                "values": values,
                "unit": unit,
                "meaning": meaning,
                # The whole matched text, never shortened, so every value
                # the entry carries is visible in its locator quote.
                "quote": quote,
            }
        )
    return out


# --------------------------------------------------------------------------
# HTML sources
# --------------------------------------------------------------------------


def read_source(name: str) -> str:
    """Return a committed capture's text after verifying both digests."""
    ts, original, sha1_b32, sha256, size, _ = WAYBACK_SOURCES[name]
    raw = gzip.decompress((SOURCES_DIR / f"{name}.gz").read_bytes())
    if (
        len(raw) != size
        or _sha256(raw) != sha256
        or _sha1_b32(raw) != sha1_b32
    ):
        raise ValueError(f"source {name} does not match its pinned digests")
    return raw.decode("utf-8-sig", errors="strict")


class _TableCollector(HTMLParser):
    """Collect every table as (caption, rows of normalized cell strings)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[dict[str, Any]] = []
        self._stack: list[dict[str, Any]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None
        self._caption: list[str] | None = None
        self._skip = 0

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag in {"script", "style"}:
            self._skip += 1
        elif tag == "table":
            table = {"caption": "", "rows": []}
            self.tables.append(table)
            self._stack.append({"table": table, "row": None, "cell": None})
        elif not self._stack:
            return
        elif tag == "tr":
            self._stack[-1]["row"] = []
        elif tag in {"td", "th"}:
            self._stack[-1]["cell"] = []
        elif tag == "caption":
            self._caption = []
        elif tag == "br":
            if self._stack[-1]["cell"] is not None:
                self._stack[-1]["cell"].append(" ")
            if self._caption is not None:
                self._caption.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"}:
            self._skip -= 1
        elif not self._stack:
            return
        elif tag in {"td", "th"}:
            context = self._stack[-1]
            if context["cell"] is not None and context["row"] is not None:
                context["row"].append(_normalize("".join(context["cell"])))
            context["cell"] = None
        elif tag == "tr":
            context = self._stack[-1]
            if context["row"] is not None:
                context["table"]["rows"].append(context["row"])
            context["row"] = None
        elif tag == "caption" and self._caption is not None:
            self._stack[-1]["table"]["caption"] = _normalize(
                "".join(self._caption)
            )
            self._caption = None
        elif tag == "table":
            self._stack.pop()

    def handle_data(self, data: str) -> None:
        if self._skip or not self._stack:
            return
        if self._caption is not None:
            self._caption.append(data)
        context = self._stack[-1]
        if context["cell"] is not None:
            context["cell"].append(data)


def html_tables(name: str) -> list[dict[str, Any]]:
    collector = _TableCollector()
    collector.feed(read_source(name))
    collector.close()
    return collector.tables


class _VisibleText(HTMLParser):
    """Visible text of a page; every tag boundary becomes a space."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag in {"script", "style"}:
            self._skip += 1
        self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"}:
            self._skip -= 1
        self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.parts.append(data)


def html_text(name: str) -> str:
    collector = _VisibleText()
    collector.feed(read_source(name))
    collector.close()
    return _normalize("".join(collector.parts))


# The report's own HTML chapter that renders each text-stated assumption;
# the transcription check re-reads every value from it.
TEXT_HTML_SOURCES = {
    "cpi_ultimate_percent": "tr08_V_economic.html",
    "cpi_intermediate_short_range": "tr08_V_economic.html",
    "covered_wage_ultimate_percent": "tr08_V_economic.html",
    "mortality_historical_data_years": "tr08_V_demographic.html",
    "mortality_ultimate_reduction_total_2032_2082": "tr08_V_demographic.html",
    "mortality_ultimate_reduction_65_plus_2032_2082": "tr08_V_demographic.html",
    "mortality_transition_rule": "tr08_V_demographic.html",
    "mortality_average_reduction_2007_2082": "tr08_VI_LRsensitivity.html",
    "di_incidence_short_range_and_ultimate_years": "tr08_V_programatic.html",
    "di_ultimate_incidence_per_1000_exposed": "tr08_V_programatic.html",
    "di_death_rate_short_range_per_1000": "tr08_V_programatic.html",
    "di_recovery_rate_short_range_per_1000": "tr08_V_programatic.html",
    "di_termination_low_high_relative_percent": "tr08_V_programatic.html",
    "di_long_range_termination_base_period": "tr08_V_programatic.html",
    "di_ultimate_recovery_per_1000": "tr08_V_programatic.html",
    "di_death_rate_2085_per_1000": "tr08_V_programatic.html",
    "di_workers_millions": "tr08_V_programatic.html",
    "di_prevalence_age_sex_adjusted_per_1000": "tr08_V_programatic.html",
    "di_incidence_sensitivity_relative_to_1970_2007": (
        "tr08_VI_LRsensitivity.html"
    ),
    "di_termination_sensitivity": "tr08_VI_LRsensitivity.html",
    "vc1_footnotes_timing": "tr08_V_programatic.html",
    "vif6_adjusted_cpi_base": "tr08_VI_OASDHI_dollars.html",
}


def html_text_values() -> dict[str, dict[str, float | int]]:
    """Re-read every TEXT_SPECS value from the report's HTML chapters."""
    if set(TEXT_HTML_SOURCES) != {spec[0] for spec in TEXT_SPECS}:
        raise ValueError("TEXT_HTML_SOURCES must cover every text spec")
    texts = {name: html_text(name) for name in set(TEXT_HTML_SOURCES.values())}
    out: dict[str, dict[str, float | int]] = {}
    for key, _pages, pattern, groups, _unit, _meaning in TEXT_SPECS:
        match = re.search(pattern, texts[TEXT_HTML_SOURCES[key]])
        if match is None:
            raise ValueError(
                f"text value {key} not found in {TEXT_HTML_SOURCES[key]}"
            )
        out[key] = {
            name: _num_required(match.group(int(group)))
            for group, name in groups.items()
        }
    return out


def _all_rows(name: str) -> list[list[str]]:
    return [row for table in html_tables(name) for row in table["rows"]]


_HTML_YEAR = re.compile(r"^(?P<year>\d{4})(?:\s?(?P<fn>\d))?$")


def _sectioned_year_rows(
    rows: Iterable[list[str]],
) -> list[tuple[str | None, int, str | None, list[str]]]:
    """Yield (section, year, footnote, non-empty value cells) for year rows."""
    section = None
    out = []
    for row in rows:
        cells = [cell for cell in row if cell != ""]
        if not cells:
            continue
        if cells[0] in SECTION_LABELS and len(cells) == 1:
            section = SECTION_LABELS[cells[0]]
            continue
        match = _HTML_YEAR.match(cells[0])
        if match:
            out.append((section, int(match["year"]), match["fn"], cells[1:]))
    return out


def single_year_economic(
    name: str, columns: Sequence[str]
) -> dict[str, list[dict[str, Any]]]:
    sections: dict[str, list[dict[str, Any]]] = {}
    for section, year, footnote, cells in _sectioned_year_rows(
        _all_rows(name)
    ):
        if section is None:
            raise ValueError(f"{name}: year row before a section label")
        if (
            len(cells) == len(columns) - 1
            and columns[-1] == "net_other_immigration"
        ):
            cells = [*cells, "--"]
        values = dict(zip(columns, map(_num, cells), strict=True))
        row: dict[str, Any] = {"year": year, **values}
        if footnote:
            row["footnote"] = footnote
        sections.setdefault(section, []).append(row)
    return sections


def single_year_life_expectancy(name: str) -> list[dict[str, Any]]:
    rows = []
    for _section_label, year, footnote, cells in _sectioned_year_rows(
        _all_rows(name)
    ):
        row: dict[str, Any] = {"year": year}
        if footnote:
            row["footnote"] = footnote
        if len(cells) == 4:
            row.update(
                dict(
                    zip(
                        LE_COLUMNS[4:8], map(_num_required, cells), strict=True
                    )
                )
            )
            row["historical"] = True
        elif len(cells) == 12:
            row.update(
                dict(zip(LE_COLUMNS, map(_num_required, cells), strict=True))
            )
        else:
            raise ValueError(f"{name} {year}: {cells}")
        rows.append(row)
    return rows


def figure_plot_points(name: str) -> dict[str, Any]:
    """Parse an 'LD_fig' long-description page of DI rate plot points."""
    historical: list[dict[str, Any]] = []
    projected: list[dict[str, Any]] = []
    for _section_label, year, _fn, cells in _sectioned_year_rows(
        _all_rows(name)
    ):
        values = list(map(_num_required, cells))
        if len(values) == 2:
            historical.append(
                {
                    "year": year,
                    "gross": values[0],
                    "age_sex_adjusted": values[1],
                }
            )
        elif len(values) == 6:
            projected.append(
                {
                    "year": year,
                    "gross": dict(
                        zip(ALTERNATIVES_ROMAN_ORDER, values[:3], strict=True)
                    ),
                    "age_sex_adjusted": dict(
                        zip(ALTERNATIVES_ROMAN_ORDER, values[3:], strict=True)
                    ),
                }
            )
        else:
            raise ValueError(f"{name} {year}: {cells}")
    return {"historical": historical, "projected": projected}


# Figures label columns I, II, III: low cost, intermediate, high cost.
ALTERNATIVES_ROMAN_ORDER = ("low_cost", "intermediate", "high_cost")

VC5_FIGURE_COLUMNS = (
    "incidence_gross",
    "incidence_age_sex_adjusted",
    "termination_gross",
    "termination_age_sex_adjusted",
    "conversion_gross",
    "conversion_age_sex_adjusted",
)


def figure_vc5_points(name: str) -> list[dict[str, Any]]:
    rows = []
    for _section_label, year, _fn, cells in _sectioned_year_rows(
        _all_rows(name)
    ):
        rows.append(
            {
                "year": year,
                **dict(
                    zip(
                        VC5_FIGURE_COLUMNS,
                        map(_num_required, cells),
                        strict=True,
                    )
                ),
            }
        )
    return rows


def build_single_year() -> dict[str, Any]:
    index_rows = _all_rows("tr08_lrIndex.html")
    title = next(
        cell
        for row in index_rows
        for cell in row
        if "Single-Year Tables Consistent with 2008 OASDI Trustees Report"
        in cell
    )
    vif6 = single_year_economic("tr08_lr6f6.html", VIF6_COLUMNS)
    vb1 = single_year_economic("tr08_lr5b1.html", VB1_COLUMNS)
    va1 = single_year_economic("tr08_lr5a1.html", VA1_COLUMNS)
    vc5 = single_year_economic("tr08_lr5c5.html", VC5_COLUMNS)
    for key in ALTERNATIVES:
        if [row["year"] for row in vif6[key]] != list(range(2007, 2086)):
            raise ValueError(f"lr6f6 {key} coverage")
        if [row["year"] for row in vb1[key]] != list(range(2008, 2083)):
            raise ValueError(f"lr5b1 {key} coverage")
        if [row["year"] for row in va1[key]] != list(range(2008, 2086)):
            raise ValueError(f"lr5a1 {key} coverage")
        if [row["year"] for row in vc5[key]] != list(range(2008, 2086)):
            raise ValueError(f"lr5c5 {key} coverage")
    figures = {
        "V.C3": {
            **figure_plot_points("tr08_LD_figVC3.html"),
            "units": "awards per 1,000 disability exposed",
            "title": "DI Disabled-Worker Incidence Rates, 1970-2085",
            "source": "tr08_LD_figVC3.html",
        },
        "V.C4": {
            **figure_plot_points("tr08_LD_figVC4.html"),
            "units": "terminations per 1,000 disabled-worker beneficiaries",
            "title": "DI Disabled-Worker Termination Rates, 1970-2085",
            "source": "tr08_LD_figVC4.html",
        },
        "V.C6": {
            **figure_plot_points("tr08_LD_figVC6.html"),
            "units": "per 1,000 disability insured",
            "title": "DI Disabled-Worker Prevalence Rates, 1970-2085",
            "source": "tr08_LD_figVC6.html",
        },
    }
    for key in ("V.C3", "V.C4", "V.C6"):
        hist = [row["year"] for row in figures[key]["historical"]]
        proj = [row["year"] for row in figures[key]["projected"]]
        if hist != list(range(1970, 2008)) or proj != list(range(2008, 2086)):
            raise ValueError(f"figure {key} coverage")
    vc5_points = figure_vc5_points("tr08_LD_figVC5.html")
    if [row["year"] for row in vc5_points] != list(range(1970, 2086)):
        raise ValueError("figure V.C5 coverage")
    figures["V.C5"] = {
        "title": (
            "Comparison of DI Disabled-Worker Incidence Rates, Termination "
            "Rates and Conversion Ratios Under Intermediate Assumptions, "
            "1970-2085"
        ),
        "units": (
            "incidence per 1,000 disability exposed; terminations and "
            "conversions per 1,000 disabled-worker beneficiaries"
        ),
        "rows": vc5_points,
        "source": "tr08_LD_figVC5.html",
    }
    return {
        "schema_version": "tr2008_single_year.v1",
        "index_title": title,
        "note": (
            "Single-year tables and figure plot points that SSA published "
            "online with the 2008 Trustees Report (captured by the Internet "
            "Archive on 2008-03-25/26). The printed report carries these "
            "series only at five-year intervals or as charts."
        ),
        "tables": {
            "VI.F6": {
                "source": "tr08_lr6f6.html",
                "columns": list(VIF6_COLUMNS),
                "sections": vif6,
            },
            "V.B1": {
                "source": "tr08_lr5b1.html",
                "columns": list(VB1_COLUMNS),
                "sections": vb1,
            },
            "V.A1": {
                "source": "tr08_lr5a1.html",
                "columns": list(VA1_COLUMNS),
                "sections": va1,
            },
            "V.A3": {
                "source": "tr08_lr5a3.html",
                "rows": single_year_life_expectancy("tr08_lr5a3.html"),
            },
            "V.A4": {
                "source": "tr08_lr5a4.html",
                "rows": single_year_life_expectancy("tr08_lr5a4.html"),
            },
            "V.C5": {
                "source": "tr08_lr5c5.html",
                "columns": list(VC5_COLUMNS),
                "sections": vc5,
            },
        },
        "figures": figures,
    }


# --------------------------------------------------------------------------
# 2008-vintage SSA tables (life table, DI ASR 2008, Supplement 2008)
# --------------------------------------------------------------------------


def _verbatim_tsv(rows: Sequence[Sequence[str]]) -> str:
    return "\n".join(
        "\t".join(row) for row in rows if any(cell for cell in row)
    )


def _captioned(name: str, prefix: str) -> dict[str, dict[str, Any]]:
    """Return {'Table N': {caption, tsv}} for captioned tables in a source."""
    return _captioned_tables(html_tables(name), name, prefix)


def _captioned_tables(
    tables: Iterable[Mapping[str, Any]], name: str, prefix: str
) -> dict[str, dict[str, Any]]:
    """Key captioned tables by id; single-digit ids ('Table 2') included."""
    out: dict[str, dict[str, Any]] = {}
    for table in tables:
        caption = table["caption"]
        match = re.search(rf"{prefix}\s*([0-9A-Z.]*[0-9])", caption)
        if not match:
            continue
        key = f"Table {match.group(1)}"
        entry = {
            "caption": caption,
            "source": name,
            "tsv": _verbatim_tsv(table["rows"]),
        }
        if key in out:
            # 'Continued' tables are appended to the first part.
            out[key]["tsv"] += "\n" + entry["tsv"]
            out[key]["continued"] = True
        else:
            out[key] = entry
    return out


LIFE_TABLE_COLUMNS = (
    "age",
    "male_qx",
    "male_lx",
    "male_ex",
    "female_qx",
    "female_lx",
    "female_ex",
)


def _life_table_rows(rows: Iterable[Sequence[str]]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        cells = [cell for cell in row if cell != ""]
        if len(cells) == 7 and cells[0].isdigit():
            out.append(
                dict(
                    zip(
                        LIFE_TABLE_COLUMNS,
                        map(_num_required, cells),
                        strict=True,
                    )
                )
            )
    if [row["age"] for row in out] != list(range(120)):
        raise ValueError("period life table must cover ages 0-119")
    return out


def build_ssa_2008() -> dict[str, Any]:
    oact_tables = html_tables("oact_stats_table4c6_20080410175446.html")
    oact_text = _normalize(
        read_source("oact_stats_table4c6_20080410175446.html")
    )
    if (
        "Period Life Table, 2004" not in oact_text
        or "March 27, 2008" not in oact_text
    ):
        raise ValueError(
            "OACT capture is not the 2004 table posted 2008-03-27"
        )
    life_rows = _life_table_rows(
        row for table in oact_tables for row in table["rows"]
    )

    supplement = _captioned("supplement2008_4c.html", r"Table\s*")
    for key in ("Table 4.C2", "Table 4.C6"):
        if key not in supplement:
            raise ValueError(f"Supplement 2008 {key} missing")
    supp_life_rows = _life_table_rows(
        [
            line.split("\t")
            for line in supplement["Table 4.C6"]["tsv"].splitlines()
        ]
    )

    di_asr: dict[str, dict[str, Any]] = {}
    for name in (
        "di_asr2008_sect01a.html",
        "di_asr2008_sect01c.html",
        "di_asr2008_sect03a.html",
        "di_asr2008_sect03c.html",
        "di_asr2008_sect03f.html",
        "di_asr2008_sect03g.html",
    ):
        di_asr.update(_captioned(name, r"Table\s*"))
    wanted = (
        "Table 2",
        "Table 19",
        "Table 20",
        "Table 35",
        "Table 36",
        "Table 39",
        "Table 49",
        "Table 50",
        "Table 57",
    )
    missing = [key for key in wanted if key not in di_asr]
    if missing:
        raise ValueError(f"DI ASR 2008 tables missing: {missing}")
    return {
        "schema_version": "ssa_2008_vintage.v1",
        "note": (
            "2008-vintage SSA sources for series the 2008 Trustees Report "
            "does not publish. DI ASR and Supplement tables are verbatim cell "
            "text (whitespace-normalized), tab-separated, one table row per "
            "line, in the style of data/external/di_asr_2023/tables.json. "
            "They are inputs for model builders, not TR2008 assumptions."
        ),
        "period_life_table_2004": {
            "source": "oact_stats_table4c6_20080410175446.html",
            "title": "Period Life Table, 2004 (SSA OACT, last modified March 27, 2008)",
            "columns": {
                "qx": "Probability of dying within one year",
                "lx": "Number of survivors out of 100,000 born alive",
                "ex": "Period life expectancy at exact age",
            },
            "rows": life_rows,
            "identical_to_supplement_2008_table_4c6": life_rows
            == supp_life_rows,
        },
        "di_asr_2008": {key: di_asr[key] for key in wanted},
        "supplement_2008": {
            key: supplement[key] for key in ("Table 4.C2", "Table 4.C6")
        },
    }


# --------------------------------------------------------------------------
# Actuarial Study 118 (DI worker experience; TR2008's termination base)
# --------------------------------------------------------------------------

AS118_SEX_LABELS = {"Male": "male", "Female": "female", "Total": "total"}
AS118_YEARS = list(range(1980, 2005))
AS118_AGE_GROUPS = (
    "15_19",
    "20_24",
    "25_29",
    "30_34",
    "35_39",
    "40_44",
    "45_49",
    "50_54",
    "55_59",
    "60_64",
    "65_plus",
)
AS118_T4_COLUMNS = (
    *(f"age_{group}" for group in AS118_AGE_GROUPS),
    "total_gross",
    "total_adjusted",
)
AS118_REASONS = ("death", "recovery", "other", "conversion", "total")
AS118_T5_COLUMNS = (
    *(f"{reason}_number" for reason in AS118_REASONS),
    *(f"{reason}_rate" for reason in AS118_REASONS),
)
AS118_T6_COLUMNS = (
    *(f"age_{group}" for group in AS118_AGE_GROUPS),
    "total",
)
AS118_SELECT_AGES = list(range(16, 65))
# Index 10 is the table's "10 or more" (ultimate) column.
AS118_DURATION_LABELS = [*(str(d) for d in range(10)), "10_or_more"]
AS118_OLD_AGES = list(range(75, 111))
AS118_EXPERIENCE = "(1996-2000 Social Security DI disability experience)"
_AS118_DASH = "—"

# table id -> (pdf page, quantity heading, sex or None, integer cells)
AS118_SELECT_TABLES: dict[str, tuple[int, str, str, bool]] = {
    "7A": (35, "Probability of Death", "male", False),
    "7B": (36, "Probability of Death", "female", False),
    "8A": (38, "Survival Table", "male", True),
    "8B": (39, "Survival Table", "female", True),
    "14A": (53, "Probability of Recovery", "male", False),
    "14B": (54, "Probability of Recovery", "female", False),
    "15A": (55, "Survival Table", "male", True),
    "15B": (56, "Survival Table", "female", True),
    "21A": (67, "Probability of Death or Recovery", "male", False),
    "21B": (68, "Probability of Death or Recovery", "female", False),
}
AS118_OLD_AGE_TABLES: dict[str, tuple[int, str, bool]] = {
    "7C": (37, "Probability of Death", False),
    "8C": (40, "Survival Table", True),
}
AS118_SEX_TITLES = {
    "male": "Male Disabled Workers",
    "female": "Female Disabled Workers",
}


def _as118_cell(token: str, integer: bool) -> float | int | None:
    """A Study 118 grid cell; the em dash marks a cell the study omits."""
    if token == _AS118_DASH:
        return None
    value = _num_required(token)
    if integer != isinstance(value, int):
        raise ValueError(f"unexpected cell type {token!r}")
    return value


def _as118_page(pdf: ReportPdf, page: int, fragments: Sequence[str]) -> str:
    text = pdf.page(page)
    normalized = _normalize(text)
    for fragment in fragments:
        if fragment not in normalized:
            raise ValueError(
                f"Study 118 PDF page {page} lacks {fragment!r}; wrong page"
            )
    return text


def _as118_locator(table: str, page: int) -> dict[str, Any]:
    return {
        "table": table,
        "pdf_page": page,
        "printed_page": page - AS118_PRINTED_PAGE_OFFSET,
    }


_AS118_YEAR_ROW = re.compile(
    r"^\s*(?P<year>(?:19|20)\d\d)\s+(?P<rest>\S.*\S)\s*$"
)


def _as118_year_table(
    pdf: ReportPdf,
    page: int,
    fragments: Sequence[str],
    columns: Sequence[str],
) -> dict[str, list[dict[str, Any]]]:
    """Parse a Male / Female / Total table of 1980-2004 year rows."""
    sections: dict[str, list[dict[str, Any]]] = {}
    section = None
    for line in _as118_page(pdf, page, fragments).splitlines():
        if line.strip() in AS118_SEX_LABELS:
            section = AS118_SEX_LABELS[line.strip()]
            sections[section] = []
            continue
        match = _AS118_YEAR_ROW.match(line)
        if match is None or section is None:
            continue
        values = dict(
            zip(
                columns, map(_num_required, match["rest"].split()), strict=True
            )
        )
        sections[section].append({"year": int(match["year"]), **values})
    if list(sections) != ["male", "female", "total"]:
        raise ValueError(f"Study 118 page {page} sections {list(sections)}")
    for key, rows in sections.items():
        if [row["year"] for row in rows] != AS118_YEARS:
            raise ValueError(f"Study 118 page {page} {key} year coverage")
    return sections


_AS118_SELECT_ROW = re.compile(r"^\s*(?P<age>\d\d)\s+(?P<rest>\S.*\S)\s*$")


def _as118_select_table(pdf: ReportPdf, table: str) -> dict[str, Any]:
    page, quantity, sex, integer = AS118_SELECT_TABLES[table]
    text = _as118_page(
        pdf,
        page,
        (
            f"Table {table}.{_AS118_DASH}{AS118_SEX_TITLES[sex]}",
            quantity,
            AS118_EXPERIENCE,
            "Duration of disability",
        ),
    )
    rows = []
    for line in text.splitlines():
        match = _AS118_SELECT_ROW.match(line)
        if match is None:
            continue
        tokens = match["rest"].split()
        if len(tokens) != 12:
            raise ValueError(f"Study 118 table {table} row {line!r}")
        age = int(match["age"])
        if int(tokens[-1]) != age + 10:
            raise ValueError(f"Study 118 table {table}: attained age {line!r}")
        rows.append(
            {
                "select_age": age,
                "by_duration": [
                    _as118_cell(token, integer) for token in tokens[:11]
                ],
            }
        )
    if [row["select_age"] for row in rows] != AS118_SELECT_AGES:
        raise ValueError(f"Study 118 table {table} select-age coverage")
    return {
        **_as118_locator(table, page),
        "title": f"{AS118_SEX_TITLES[sex]}: {quantity}",
        "sex": sex,
        "durations": AS118_DURATION_LABELS,
        "rows": rows,
    }


_AS118_OLD_ROW = re.compile(
    r"^\s*(?P<age>\d{2,3})\s+(?P<male>\S+)\s+(?P<female>\S+)\s*$"
)


def _as118_old_age_table(pdf: ReportPdf, table: str) -> dict[str, Any]:
    page, quantity, integer = AS118_OLD_AGE_TABLES[table]
    text = _as118_page(
        pdf,
        page,
        (
            f"Table {table}.{_AS118_DASH}Disabled Workers Age 75 and Older",
            quantity,
            AS118_EXPERIENCE,
        ),
    )
    rows = []
    for line in text.splitlines():
        match = _AS118_OLD_ROW.match(line)
        if match is None:
            continue
        rows.append(
            {
                "attained_age": int(match["age"]),
                "male": _as118_cell(match["male"], integer),
                "female": _as118_cell(match["female"], integer),
            }
        )
    if [row["attained_age"] for row in rows] != AS118_OLD_AGES:
        raise ValueError(f"Study 118 table {table} attained-age coverage")
    return {
        **_as118_locator(table, page),
        "title": f"Disabled Workers Age 75 and Older: {quantity}",
        "rows": rows,
    }


# Reading rules quoted from the notes printed under the grid tables.
AS118_NOTE_SPECS = (
    (
        "select_age",
        35,
        r"Select age denotes age last birthday at entitlement to disability benefits\. Duration measured in years since selection\. Attained age calculated as sum of select age and duration\.",
    ),
    (
        "death_probability",
        35,
        r"The value q \[ x \] \+ t at duration t represents the probability of death.in a multiple-decrement environment.during the \(t\+1\) year of entitlement for those originally entitled to disability benefits at select age \[x\] who have attained age \[x\]\+t\.",
    ),
    (
        "select_and_ultimate",
        35,
        r"Select-and-ultimate table is read across the row for 0-10 years since selection, and down the last \(ultimate\) column for 10 or more years since selection\. See table 7C for attained ages beyond age 74\.",
    ),
    (
        "old_age_death_probability",
        37,
        r"The value at attained age x represents the probability of death within one year for those originally entitled to disability benefits who have attained that particular age\.",
    ),
    (
        "recovery_not_beyond_nra",
        53,
        r"Recovery is not considered beyond normal retirement age\.",
    ),
    (
        "recovery_probability",
        53,
        r"The value q \[ x \] \+ t at duration t represents the probability of recovery while on the DI rolls.in a multiple-decrement environment.during the \(t\+1\) year of entitlement for those originally entitled to disability benefits at select age \[x\] who have attained age \[x\]\+t\.",
    ),
    (
        "graduation",
        35,
        r"Results have been graduated using the Whittaker-Henderson Type B two-dimensional method\.",
    ),
    (
        "incidence_rates",
        29,
        r"Age-specific and gross rates computed as the ratio of annual awards, to exposure of the disability insured population not receiving benefits\.",
    ),
    (
        "termination_rates",
        30,
        r"Rates computed as the ratio of annual terminations, to the exposure of the disabled worker population\.",
    ),
)


def _as118_notes(pdf: ReportPdf) -> dict[str, dict[str, Any]]:
    out = {}
    for key, page, pattern in AS118_NOTE_SPECS:
        match = re.search(pattern, _normalize(pdf.page(page)))
        if match is None:
            raise ValueError(f"Study 118 note {key} not found on page {page}")
        out[key] = {
            "pdf_page": page,
            "printed_page": page - AS118_PRINTED_PAGE_OFFSET,
            "quote": match.group(0),
        }
    return out


def build_as118(pdf: ReportPdf) -> dict[str, Any]:
    title_page = _normalize(pdf.page(1))
    for fragment in (
        "DISABILITY INSURANCE PROGRAM WORKER EXPERIENCE",
        "ACTUARIAL STUDY NO. 118",
        "Office of the Chief Actuary June 2005",
    ):
        if fragment not in title_page:
            raise ValueError(f"Study 118 title page lacks {fragment!r}")
    tables: dict[str, Any] = {
        "4": {
            **_as118_locator("4", 29),
            "title": "Disabled Worker Incidence Rates Per Thousand Exposed",
            "units": (
                "Awards per 1,000 disability-insured persons not receiving "
                "benefits, by age group and year of award (source note 1). "
                "total_adjusted: age-adjusted by sex, age-sex-adjusted for "
                "the total, to the calendar-2000 exposure (notes 2-3)."
            ),
            "columns": list(AS118_T4_COLUMNS),
            "sections": _as118_year_table(
                pdf,
                29,
                (
                    f"Table 4.{_AS118_DASH}Disabled Worker Incidence Rates "
                    "Per Thousand Exposed",
                    "Awards per thousand grouped by age and year of award, "
                    "1980-2004",
                ),
                AS118_T4_COLUMNS,
            ),
        },
        "5": {
            **_as118_locator("5", 30),
            "title": (
                "Disabled Worker Benefits Terminated and Gross Termination "
                "Rates"
            ),
            "units": (
                "Numbers of terminations by reason; rates per 1,000 exposed "
                "disabled workers."
            ),
            "columns": list(AS118_T5_COLUMNS),
            "sections": _as118_year_table(
                pdf,
                30,
                (
                    f"Table 5.{_AS118_DASH}Disabled Worker Benefits "
                    "Terminated and Gross Termination Rates",
                    "Grouped by reason for termination and year, 1980-2004",
                ),
                AS118_T5_COLUMNS,
            ),
        },
        "6": {
            **_as118_locator("6", 31),
            "title": "Disabled Worker Benefits In Current-Payment Status",
            "units": "Disabled workers by age at end of year.",
            "columns": list(AS118_T6_COLUMNS),
            "sections": _as118_year_table(
                pdf,
                31,
                (
                    f"Table 6.{_AS118_DASH}Disabled Worker Benefits In "
                    "Current-Payment Status",
                    "Grouped by age at end of year, 1980-2004",
                ),
                AS118_T6_COLUMNS,
            ),
        },
    }
    for table in AS118_SELECT_TABLES:
        tables[table] = _as118_select_table(pdf, table)
    for table in AS118_OLD_AGE_TABLES:
        tables[table] = _as118_old_age_table(pdf, table)
    return {
        "schema_version": "actuarial_study_118.v1",
        "document": {
            "title": (
                "Social Security Disability Insurance Program Worker "
                "Experience"
            ),
            "series": "SSA Office of the Chief Actuary, Actuarial Study No. 118",
            "published": "June 2005",
            "pdf_sha256": AS118_SHA256,
            "pdf_bytes": AS118_BYTES,
            "pdf_pages": AS118_PAGES,
            "wayback_capture": (
                f"https://web.archive.org/web/{AS118_WAYBACK_TIMESTAMP}id_/"
                f"{AS118_ORIGINAL_URL}"
            ),
            "wayback_sha1_b32": AS118_WAYBACK_SHA1_B32,
            "page_locators": (
                "pdf_page is the 1-based page index in the PDF; printed_page "
                f"is the number printed on the page (pdf_page - "
                f"{AS118_PRINTED_PAGE_OFFSET})."
            ),
            "extraction": "pdftotext -layout, one page at a time; see scripts/extract_tr2008_parameters.py",
        },
        "role": (
            "TR2008 section V.C.6.b projects long-range DI death and "
            "recovery rates relative to rates by age, sex and duration of "
            "entitlement over the base period 1996-2000, citing this study. "
            "TR2008 itself publishes no rates by age. These tables are that "
            "published base, a 2005 publication inside the 2008 information "
            "vintage. They are not TR2008's projected rates."
        ),
        "cell_conventions": (
            "Grid rows are select ages 16-64; by_duration holds durations "
            "0-9 and, at index 10, the '10 or more' (ultimate) column, whose "
            "attained age is select age + 10. null marks an em-dash cell: "
            "recovery beyond normal retirement age is not tabulated (note "
            "recovery_not_beyond_nra), and table 8C prints no male "
            "survivors at 110."
        ),
        "notes": _as118_notes(pdf),
        "tables": tables,
    }


# --------------------------------------------------------------------------
# Transcription check
# --------------------------------------------------------------------------


class _Comparison:
    def __init__(
        self, check_id: str, description: str, left: str, right: str
    ) -> None:
        self.check_id = check_id
        self.description = description
        self.left = left
        self.right = right
        self.cells = 0
        self.mismatches: list[dict[str, Any]] = []

    def compare(self, where: str, a: Any, b: Any) -> None:
        self.cells += 1
        if a != b:
            self.mismatches.append(
                {"cell": where, self.left: a, self.right: b}
            )

    def result(self) -> dict[str, Any]:
        if self.cells == 0:
            raise ValueError(f"check {self.check_id} compared no cells")
        return {
            "id": self.check_id,
            "description": self.description,
            "left": self.left,
            "right": self.right,
            "cells_compared": self.cells,
            "mismatches": self.mismatches,
            "passed": not self.mismatches,
        }


def _html_vc1_rows() -> dict[str, dict[int, dict[str, Any]]]:
    tables = html_tables("tr08_V_programatic.html")
    target = next(
        table
        for table in tables
        if any(
            row
            and row[0] == "Calendar year"
            and "OASDI benefit increases" in " ".join(row)
            for row in table["rows"]
        )
    )
    out: dict[str, dict[int, dict[str, Any]]] = {}
    for section, year, _fn, cells in _sectioned_year_rows(target["rows"]):
        assert section is not None
        markers = _vc1_footnotes(section, year)
        tokens: list[str] = []
        for column, cell in zip(VC1_COLUMNS, cells, strict=True):
            parts = cell.split()
            marker = markers.get(column)
            if marker and len(parts) > 1:
                # HTML duplicates superscript digits ('77 2.3'); drop them.
                if set(parts[0]) != {marker}:
                    raise ValueError(f"unexpected V.C1 HTML cell {cell!r}")
                parts = [marker, *parts[1:]]
            tokens.extend(parts)
        out.setdefault(section, {})[year] = _take_footnoted(
            tokens, VC1_COLUMNS, markers
        )
    return out


def _html_table_rows(
    name: str,
    header_fragment: str,
    columns: Sequence[str],
    pad_to: int | None = None,
) -> dict[str, dict[int, dict[str, Any]]]:
    tables = html_tables(name)
    target = next(
        table
        for table in tables
        if any(header_fragment in " ".join(row) for row in table["rows"][:3])
    )
    out: dict[str, dict[int, dict[str, Any]]] = {}
    for section, year, _fn, cells in _sectioned_year_rows(target["rows"]):
        if pad_to is not None and len(cells) < pad_to:
            cells = [*cells, *(["--"] * (pad_to - len(cells)))]
        out.setdefault(section or "rows", {})[year] = dict(
            zip(columns, map(_num, cells), strict=True)
        )
    return out


def _html_life_expectancy(
    header_fragment_index: int,
) -> dict[int, dict[str, Any]]:
    tables = [
        table
        for table in html_tables("tr08_V_demographic.html")
        if any(
            "Low Cost" in " ".join(row) and "Intermediate" in " ".join(row)
            for row in table["rows"][:2]
        )
    ]
    target = tables[header_fragment_index]
    out = {}
    for _section, year, _fn, cells in _sectioned_year_rows(target["rows"]):
        values = list(map(_num_required, cells))
        if len(values) == 4:
            out[year] = dict(zip(LE_COLUMNS[4:8], values, strict=True))
        else:
            out[year] = dict(zip(LE_COLUMNS, values, strict=True))
    return out


def _round_half_up(value: float) -> int:
    from decimal import ROUND_HALF_UP, Decimal

    return int(Decimal(str(value)).quantize(Decimal("1"), ROUND_HALF_UP))


def _rounded_growth(current: float, previous: float) -> float:
    """Percent growth rounded half-up to one decimal, as printed."""
    from decimal import ROUND_HALF_UP, Decimal

    value = (Decimal(str(current)) / Decimal(str(previous)) - 1) * 100
    return float(value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def _compare_years(
    check: _Comparison,
    left: Mapping[str, Iterable[int]],
    right: Mapping[str, Iterable[int]],
) -> None:
    """Row coverage must match too, so a row the PDF parse skipped fails."""
    for section in sorted(set(left) | set(right)):
        check.compare(
            f"{section}/years",
            sorted(left.get(section, ())),
            sorted(right.get(section, ())),
        )


def _html_range_rows(
    name: str, header_fragment: str, columns: Sequence[str]
) -> dict[str, dict[tuple[int, int], dict[str, Any]]]:
    tables = html_tables(name)
    target = next(
        table
        for table in tables
        if any(header_fragment in " ".join(row) for row in table["rows"][:3])
    )
    out: dict[str, dict[tuple[int, int], dict[str, Any]]] = {}
    section = None
    for row in target["rows"]:
        cells = [cell for cell in row if cell != ""]
        if len(cells) == 1 and cells[0] in SECTION_LABELS:
            section = SECTION_LABELS[cells[0]]
            continue
        match = (
            re.fullmatch(r"(\d{4}) to (\d{4})", cells[0]) if cells else None
        )
        if match and section is not None:
            key = (int(match.group(1)), int(match.group(2)))
            out.setdefault(section, {})[key] = dict(
                zip(columns, map(_num_required, cells[1:]), strict=True)
            )
    return out


def build_checks(
    report: Mapping[str, Any],
    single: Mapping[str, Any],
    ssa: Mapping[str, Any],
    as118: Mapping[str, Any],
) -> dict[str, Any]:
    tables = report["tables"]
    results = []

    # V.C1: every PDF cell against the report's own HTML rendering.
    check = _Comparison(
        "V.C1_pdf_vs_html",
        "Every V.C1 cell: PDF (pp. 102-103) vs report HTML chapter V_programatic.html",
        "pdf",
        "html",
    )
    html_vc1 = _html_vc1_rows()
    for section, rows in tables["V.C1"]["sections"].items():
        for row in rows:
            for column in VC1_COLUMNS:
                check.compare(
                    f"{section}/{row['year']}/{column}",
                    row[column],
                    html_vc1[section][row["year"]][column],
                )
    _compare_years(
        check,
        {
            k: [r["year"] for r in v]
            for k, v in tables["V.C1"]["sections"].items()
        },
        {k: list(v) for k, v in html_vc1.items()},
    )
    results.append(check.result())

    # V.C1 arithmetic: printed AWI increase equals rounded AWI growth.
    check = _Comparison(
        "V.C1_awi_increase_arithmetic",
        "V.C1 AWI increase column equals round-half-up of AWI growth from the prior row",
        "printed",
        "recomputed",
    )
    for section, rows in tables["V.C1"]["sections"].items():
        previous = None
        if section in ALTERNATIVES:
            previous = tables["V.C1"]["sections"]["historical"][-1]
        for row in rows:
            if previous is not None:
                check.compare(
                    f"{section}/{row['year']}",
                    row["awi_increase_percent"],
                    _rounded_growth(row["awi"], previous["awi"]),
                )
            previous = row
    results.append(check.result())

    # V.C1 AWI vs VI.F6 AWI for the overlapping 2007-2017 rows.
    check = _Comparison(
        "V.C1_vs_VI.F6_awi",
        "V.C1 AWI equals VI.F6 AWI for 2007-2017 in each alternative (both PDF)",
        "V.C1",
        "VI.F6",
    )
    for alternative in ALTERNATIVES:
        f6 = {
            row["year"]: row
            for row in tables["VI.F6"]["sections"][alternative]
        }
        for row in tables["V.C1"]["sections"][alternative]:
            check.compare(
                f"{alternative}/{row['year']}",
                row["awi"],
                f6[row["year"]]["awi"],
            )
    results.append(check.result())

    # VI.F6: PDF vs HTML chapter and vs the single-year table.
    html_f6 = _html_table_rows(
        "tr08_VI_OASDHI_dollars.html", "Adjusted CPI", VIF6_COLUMNS
    )
    check = _Comparison(
        "VI.F6_pdf_vs_html",
        "Every VI.F6 cell: PDF (pp. 184-185) vs report HTML chapter",
        "pdf",
        "html",
    )
    for alternative in ALTERNATIVES:
        for row in tables["VI.F6"]["sections"][alternative]:
            for column in VIF6_COLUMNS:
                check.compare(
                    f"{alternative}/{row['year']}/{column}",
                    row[column],
                    html_f6[alternative][row["year"]][column],
                )
    _compare_years(
        check,
        {
            k: [r["year"] for r in v]
            for k, v in tables["VI.F6"]["sections"].items()
        },
        {k: list(v) for k, v in html_f6.items()},
    )
    results.append(check.result())
    check = _Comparison(
        "VI.F6_pdf_vs_single_year",
        "Every VI.F6 PDF cell vs the same year in single-year table lr6f6",
        "pdf",
        "single_year",
    )
    for alternative in ALTERNATIVES:
        sy = {
            row["year"]: row
            for row in single["tables"]["VI.F6"]["sections"][alternative]
        }
        for row in tables["VI.F6"]["sections"][alternative]:
            for column in VIF6_COLUMNS:
                check.compare(
                    f"{alternative}/{row['year']}/{column}",
                    row[column],
                    sy[row["year"]][column],
                )
    results.append(check.result())

    # V.B1: PDF vs HTML chapter and vs single-year table.
    html_b1 = _html_table_rows(
        "tr08_V_economic.html", "Productivity", VB1_COLUMNS
    )
    check = _Comparison(
        "V.B1_pdf_vs_html",
        "Every V.B1 single-year cell: PDF (pp. 92-93) vs report HTML chapter",
        "pdf",
        "html",
    )
    for section, content in tables["V.B1"]["sections"].items():
        for row in content["years"]:
            for column in VB1_COLUMNS:
                check.compare(
                    f"{section}/{row['year']}/{column}",
                    row[column],
                    html_b1[section][row["year"]][column],
                )
    _compare_years(
        check,
        {
            k: [r["year"] for r in v["years"]]
            for k, v in tables["V.B1"]["sections"].items()
        },
        {k: list(v) for k, v in html_b1.items()},
    )
    html_ranges = _html_range_rows(
        "tr08_V_economic.html", "Productivity", VB1_COLUMNS
    )
    for section, content in tables["V.B1"]["sections"].items():
        pdf_ranges = {
            (r["first_year"], r["last_year"]): r for r in content["ranges"]
        }
        check.compare(
            f"{section}/ranges",
            sorted(pdf_ranges),
            sorted(html_ranges.get(section, {})),
        )
        for key, row in pdf_ranges.items():
            for column in VB1_COLUMNS:
                check.compare(
                    f"{section}/{key[0]}-{key[1]}/{column}",
                    row[column],
                    html_ranges[section][key][column],
                )
    results.append(check.result())
    check = _Comparison(
        "V.B1_pdf_vs_single_year",
        "V.B1 PDF single-year rows (2008-2017) vs single-year table lr5b1",
        "pdf",
        "single_year",
    )
    for alternative in ALTERNATIVES:
        sy = {
            row["year"]: row
            for row in single["tables"]["V.B1"]["sections"][alternative]
        }
        for row in tables["V.B1"]["sections"][alternative]["years"]:
            for column in VB1_COLUMNS:
                check.compare(
                    f"{alternative}/{row['year']}/{column}",
                    row[column],
                    sy[row["year"]][column],
                )
    results.append(check.result())

    # II.C1: PDF vs HTML.
    html_rows = [
        row
        for table in html_tables("tr08_II_assump.html")
        for row in table["rows"]
    ]
    check = _Comparison(
        "II.C1_pdf_vs_html",
        "Every II.C1 cell: PDF (p. 6) vs report HTML chapter II_assump.html",
        "pdf",
        "html",
    )
    for key, fragment in IIC1_ROWS:
        html_row = next(
            row
            for row in html_rows
            if any(fragment.split(" (")[0] in cell for cell in row)
            and len([c for c in row if c]) >= 4
        )
        cells = [cell for cell in html_row if cell][-3:]
        for alternative, cell in zip(
            ("intermediate", "low_cost", "high_cost"), cells, strict=True
        ):
            check.compare(
                f"{key}/{alternative}",
                tables["II.C1"]["rows"][key][alternative],
                _num_required(cell),
            )
    results.append(check.result())

    # V.A1: PDF vs HTML chapter and single-year.
    html_a1 = _html_table_rows(
        "tr08_V_demographic.html", "Total fertility", VA1_COLUMNS, pad_to=6
    )
    check = _Comparison(
        "V.A1_pdf_vs_html",
        "Every V.A1 cell: PDF (pp. 80-81) vs report HTML chapter",
        "pdf",
        "html",
    )
    for section, rows in tables["V.A1"]["sections"].items():
        for row in rows:
            for column in VA1_COLUMNS:
                check.compare(
                    f"{section}/{row['year']}/{column}",
                    row[column],
                    html_a1[section][row["year"]][column],
                )
    _compare_years(
        check,
        {
            k: [r["year"] for r in v]
            for k, v in tables["V.A1"]["sections"].items()
        },
        {k: list(v) for k, v in html_a1.items()},
    )
    results.append(check.result())
    check = _Comparison(
        "V.A1_pdf_vs_single_year",
        "Every V.A1 PDF cell (historical and projected rows) vs the same year in single-year table lr5a1",
        "pdf",
        "single_year",
    )
    for alternative in ALTERNATIVES:
        sy = {
            row["year"]: row
            for row in single["tables"]["V.A1"]["sections"][alternative]
        }
        for row in tables["V.A1"]["sections"][alternative]:
            for column in VA1_COLUMNS:
                check.compare(
                    f"{alternative}/{row['year']}/{column}",
                    row[column],
                    sy[row["year"]][column],
                )
    sy_hist = {
        row["year"]: row
        for row in single["tables"]["V.A1"]["sections"]["historical"]
    }
    for row in tables["V.A1"]["sections"]["historical"]:
        for column in VA1_COLUMNS:
            check.compare(
                f"historical/{row['year']}/{column}",
                row[column],
                sy_hist[row["year"]][column],
            )
    results.append(check.result())

    # V.A3 / V.A4: PDF vs HTML chapter and single-year.
    for table_id, html_index, single_key in (
        ("V.A3", 0, "V.A3"),
        ("V.A4", 1, "V.A4"),
    ):
        html_le = _html_life_expectancy(html_index)
        sy = {row["year"]: row for row in single["tables"][single_key]["rows"]}
        check = _Comparison(
            f"{table_id}_pdf_vs_html",
            f"Every {table_id} cell: PDF vs report HTML chapter",
            "pdf",
            "html",
        )
        check_sy = _Comparison(
            f"{table_id}_pdf_vs_single_year",
            f"Every {table_id} PDF cell vs the same year in the single-year table",
            "pdf",
            "single_year",
        )
        for row in tables[table_id]["rows"]:
            pdf_columns = sorted(
                column for column in LE_COLUMNS if column in row
            )
            check.compare(
                f"{row['year']}/columns",
                pdf_columns,
                sorted(html_le[row["year"]]),
            )
            for column in pdf_columns:
                check.compare(
                    f"{row['year']}/{column}",
                    row[column],
                    html_le[row["year"]].get(column),
                )
                check_sy.compare(
                    f"{row['year']}/{column}",
                    row[column],
                    sy[row["year"]].get(column),
                )
        _compare_years(
            check,
            {"rows": [r["year"] for r in tables[table_id]["rows"]]},
            {"rows": list(html_le)},
        )
        results.append(check.result())
        results.append(check_sy.result())

    # V.C5: PDF vs HTML chapter and single-year.
    html_c5 = _html_table_rows(
        "tr08_V_programatic.html", "Disabled- worker", VC5_COLUMNS, pad_to=6
    )
    check = _Comparison(
        "V.C5_pdf_vs_html",
        "Every V.C5 cell: PDF (pp. 124-125) vs report HTML chapter",
        "pdf",
        "html",
    )
    for section, rows in tables["V.C5"]["sections"].items():
        for row in rows:
            for column in VC5_COLUMNS:
                check.compare(
                    f"{section}/{row['year']}/{column}",
                    row[column],
                    html_c5[section][row["year"]][column],
                )
    _compare_years(
        check,
        {
            k: [r["year"] for r in v]
            for k, v in tables["V.C5"]["sections"].items()
        },
        {k: list(v) for k, v in html_c5.items()},
    )
    results.append(check.result())
    check = _Comparison(
        "V.C5_pdf_vs_single_year",
        "V.C5 PDF rows (1975+) vs single-year table lr5c5",
        "pdf",
        "single_year",
    )
    for section, rows in tables["V.C5"]["sections"].items():
        sy = {
            row["year"]: row
            for row in single["tables"]["V.C5"]["sections"][section]
        }
        for row in rows:
            if row["year"] in sy:
                for column in VC5_COLUMNS:
                    check.compare(
                        f"{section}/{row['year']}/{column}",
                        row[column],
                        sy[row["year"]][column],
                    )
    results.append(check.result())

    # Figure plot points: V.C5 repeats the intermediate V.C3/V.C4 series,
    # and V.C6 prevalence rounds to the integer V.C5 table prevalence.
    figures = single["figures"]
    check = _Comparison(
        "figures_V.C5_vs_V.C3_V.C4",
        "Figure V.C5 incidence and termination plot points equal the "
        "intermediate series of Figures V.C3 and V.C4 (separate pages)",
        "V.C5",
        "V.C3/V.C4",
    )
    by_year = {row["year"]: row for row in figures["V.C5"]["rows"]}
    for kind, figure in (("incidence", "V.C3"), ("termination", "V.C4")):
        for row in figures[figure]["historical"]:
            for basis in ("gross", "age_sex_adjusted"):
                check.compare(
                    f"{kind}/{row['year']}/{basis}",
                    by_year[row["year"]][f"{kind}_{basis}"],
                    row[basis],
                )
        for row in figures[figure]["projected"]:
            for basis in ("gross", "age_sex_adjusted"):
                check.compare(
                    f"{kind}/{row['year']}/{basis}",
                    by_year[row["year"]][f"{kind}_{basis}"],
                    row[basis]["intermediate"],
                )
    results.append(check.result())
    check = _Comparison(
        "figure_V.C6_vs_table_V.C5_prevalence",
        "Figure V.C6 prevalence plot points, rounded half-up to integers, "
        "equal the single-year V.C5 table prevalence columns",
        "figure_rounded",
        "table",
    )
    table_rows = {
        (section, row["year"]): row
        for section, rows in single["tables"]["V.C5"]["sections"].items()
        for row in rows
    }
    columns = {
        "gross": "prevalence_gross_per_1000",
        "age_sex_adjusted": "prevalence_age_sex_adjusted_per_1000",
    }
    for row in figures["V.C6"]["historical"]:
        table_row = table_rows.get(("historical", row["year"]))
        if table_row is None:
            continue
        for basis, column in columns.items():
            check.compare(
                f"historical/{row['year']}/{basis}",
                _round_half_up(row[basis]),
                table_row[column],
            )
    for row in figures["V.C6"]["projected"]:
        for alternative in ALTERNATIVES:
            table_row = table_rows[(alternative, row["year"])]
            for basis, column in columns.items():
                check.compare(
                    f"{alternative}/{row['year']}/{basis}",
                    _round_half_up(row[basis][alternative]),
                    table_row[column],
                )
    results.append(check.result())

    # Text statements vs tables where the report states the same number.
    text = {entry["id"]: entry["values"] for entry in report["text_values"]}
    check = _Comparison(
        "text_vs_tables",
        "Text-stated ultimate values equal the tabulated values",
        "text",
        "table",
    )
    for alternative in ALTERNATIVES:
        check.compare(
            f"cpi/{alternative}",
            text["cpi_ultimate_percent"][alternative],
            tables["II.C1"]["rows"]["cpi"][alternative],
        )
        check.compare(
            f"covered_wage/{alternative}",
            text["covered_wage_ultimate_percent"][alternative],
            tables["II.C1"]["rows"]["average_covered_wage"][alternative],
        )
        check.compare(
            f"mortality/{alternative}",
            text["mortality_ultimate_reduction_total_2032_2082"][alternative],
            tables["II.C1"]["rows"]["death_rate_reduction_2032_2082"][
                alternative
            ],
        )
        range_row = tables["V.B1"]["sections"][alternative]["ranges"][-1]
        check.compare(
            f"cpi_vs_VB1_2020_2082/{alternative}",
            text["cpi_ultimate_percent"][alternative],
            range_row["cpi"],
        )
    check.compare(
        "cpi_2009_intermediate",
        text["cpi_intermediate_short_range"]["2009"],
        tables["V.B1"]["sections"]["intermediate"]["years"][1]["cpi"],
    )
    results.append(check.result())

    # Text statements: every value re-read from the report's HTML chapter.
    html_values = html_text_values()
    check = _Comparison(
        "text_values_pdf_vs_html",
        "Every text-stated value: PDF prose vs the same sentence in the "
        "report's HTML chapter (TEXT_HTML_SOURCES)",
        "pdf",
        "html",
    )
    check.compare(
        "ids",
        sorted(entry["id"] for entry in report["text_values"]),
        sorted(html_values),
    )
    for entry in report["text_values"]:
        for name, value in entry["values"].items():
            check.compare(
                f"{entry['id']}/{name}",
                value,
                html_values[entry["id"]].get(name),
            )
    results.append(check.result())

    # Period life table 2004: OACT page vs Supplement Table 4.C6, and vs V.A3.
    life = ssa["period_life_table_2004"]
    check = _Comparison(
        "life_table_2004_consistency",
        "OACT 2004 period life table equals Supplement 2008 Table 4.C6; its e0 and e65 rounded to 0.1 equal V.A3 2004",
        "life_table",
        "comparison",
    )
    check.compare(
        "identical_to_supplement_2008_table_4c6",
        life["identical_to_supplement_2008_table_4c6"],
        True,
    )
    va3_2004 = next(
        row for row in tables["V.A3"]["rows"] if row["year"] == 2004
    )
    by_age = {row["age"]: row for row in life["rows"]}
    for sex in ("male", "female"):
        for age, label in ((0, "at_birth"), (65, "at_65")):
            check.compare(
                f"{sex}/{label}",
                round(by_age[age][f"{sex}_ex"], 1),
                va3_2004[f"intermediate_{label}_{sex}"],
            )
    results.append(check.result())

    results.extend(build_as118_checks(as118))

    return {
        "schema_version": "tr2008_transcription_check.v1",
        "all_passed": all(result["passed"] for result in results),
        "cells_compared": sum(result["cells_compared"] for result in results),
        "checks": results,
    }


def _decimal(value: float | int) -> Any:
    from decimal import Decimal

    return Decimal(str(value))


def _survival_step(lives: int, probability: float) -> int:
    """Next printed survivor count: round-half-up of l * (1 - q)."""
    from decimal import ROUND_HALF_UP, Decimal

    value = _decimal(lives) * (1 - _decimal(probability))
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def build_as118_checks(as118: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Arithmetic identities that tie Study 118's tables to each other.

    Study 118 has no second rendering, so each grid is checked against a
    different printed table computed from it: survival tables decrement
    lives by the probability tables (notes to tables 8C and 15A/15B), and
    table 21 is derived from tables 7 and 14 (note 2 to table 21A/21B).
    Printed survivors are rounded, so a recomputed count may differ from
    the printed one by 1; the check records the largest difference and
    fails if any exceeds 1.
    """
    tables = as118["tables"]
    results = []

    def survival_check(
        check_id: str,
        probability_tables: Sequence[str],
        lives_tables: Sequence[str],
    ) -> None:
        check = _Comparison(
            check_id,
            f"Tables {', '.join(lives_tables)}: each select-period survivor "
            "count (durations 1-9) equals the prior duration decremented by "
            f"Tables {', '.join(probability_tables)}, and each ultimate "
            "('10 or more') survivor count equals the one above it "
            "decremented by the ultimate probability above it (note 3: the "
            "ultimate column is read down); the column starts from select "
            "age 16 at duration 10. Round half up; |difference| <= 1 allowed "
            "for rounding of the printed prior cell. An omitted survivor "
            "cell must sit where the probability is omitted too.",
            "printed",
            "within_one_of_recomputed",
        )
        exact = 0
        largest = 0

        def step(
            where: str,
            printed: int | None,
            lives: int | None,
            q: float | None,
            q_next: float | None,
        ) -> None:
            nonlocal exact, largest
            if printed is None:
                check.compare(f"{where}/omitted_with_q", q_next is None, True)
                return
            recomputed = _survival_step(lives, q)
            difference = abs(printed - recomputed)
            exact += difference == 0
            largest = max(largest, difference)
            check.compare(
                where, printed, printed if difference <= 1 else recomputed
            )

        for q_table, l_table in zip(
            probability_tables, lives_tables, strict=True
        ):
            q_rows = {r["select_age"]: r for r in tables[q_table]["rows"]}
            l_rows = tables[l_table]["rows"]
            for row in l_rows:
                lives = row["by_duration"]
                q = q_rows[row["select_age"]]["by_duration"]
                for t in range(9):
                    step(
                        f"{l_table}/{row['select_age']}/{t + 1}",
                        lives[t + 1],
                        lives[t],
                        q[t],
                        q[t + 1],
                    )
            first = l_rows[0]
            step(
                f"{l_table}/{first['select_age']}/10",
                first["by_duration"][10],
                first["by_duration"][9],
                q_rows[first["select_age"]]["by_duration"][9],
                q_rows[first["select_age"]]["by_duration"][10],
            )
            for above, row in zip(l_rows[:-1], l_rows[1:], strict=True):
                if above["by_duration"][10] is None:
                    check.compare(
                        f"{l_table}/{row['select_age']}/10/omitted_below_omitted",
                        row["by_duration"][10],
                        None,
                    )
                    continue
                step(
                    f"{l_table}/{row['select_age']}/10",
                    row["by_duration"][10],
                    above["by_duration"][10],
                    q_rows[above["select_age"]]["by_duration"][10],
                    q_rows[row["select_age"]]["by_duration"][10],
                )
        result = check.result()
        result["exact_matches"] = exact
        result["largest_difference"] = largest
        results.append(result)

    survival_check(
        "AS118_death_probability_vs_survival", ("7A", "7B"), ("8A", "8B")
    )
    survival_check(
        "AS118_recovery_probability_vs_survival",
        ("14A", "14B"),
        ("15A", "15B"),
    )

    # Table 8C extends the ultimate column of 8A/8B with Table 7C.
    check = _Comparison(
        "AS118_old_age_death_vs_survival",
        "Table 8C survivors at 75-110 equal the prior age decremented by "
        "Table 7C; age 75 continues from the ultimate (select 64, attained "
        "74) cells of Tables 8A/8B and 7A/7B",
        "printed",
        "within_one_of_recomputed",
    )
    exact = 0
    largest = 0
    old_q = {row["attained_age"]: row for row in tables["7C"]["rows"]}
    old_l = {row["attained_age"]: row for row in tables["8C"]["rows"]}
    for sex, grid_q, grid_l in (("male", "7A", "8A"), ("female", "7B", "8B")):
        previous_l = tables[grid_l]["rows"][-1]["by_duration"][10]
        previous_q = tables[grid_q]["rows"][-1]["by_duration"][10]
        for age in AS118_OLD_AGES:
            printed = old_l[age][sex]
            recomputed = _survival_step(previous_l, previous_q)
            if printed is None:
                check.compare(f"{sex}/{age}/omitted_at_zero", recomputed, 0)
                break
            difference = abs(printed - recomputed)
            exact += difference == 0
            largest = max(largest, difference)
            check.compare(
                f"{sex}/{age}",
                printed,
                printed if difference <= 1 else recomputed,
            )
            previous_l, previous_q = printed, old_q[age][sex]
    result = check.result()
    result["exact_matches"] = exact
    result["largest_difference"] = largest
    results.append(result)

    # Table 21 = Table 7 + Table 14 (dependent probabilities add).
    check = _Comparison(
        "AS118_combined_equals_death_plus_recovery",
        "Tables 21A/21B equal Tables 7A/7B plus 14A/14B cell by cell, an "
        "omitted recovery cell counting as 0 (|difference| <= 0.000001 for "
        "six-decimal rounding)",
        "printed",
        "within_rounding_of_sum",
    )
    for combined, death, recovery in (
        ("21A", "7A", "14A"),
        ("21B", "7B", "14B"),
    ):
        d_rows = {r["select_age"]: r for r in tables[death]["rows"]}
        r_rows = {r["select_age"]: r for r in tables[recovery]["rows"]}
        for row in tables[combined]["rows"]:
            for t, value in enumerate(row["by_duration"]):
                d = d_rows[row["select_age"]]["by_duration"][t]
                r = r_rows[row["select_age"]]["by_duration"][t] or 0.0
                total = _decimal(d) + _decimal(r)
                close = abs(_decimal(value) - total) <= _decimal(0.000001)
                check.compare(
                    f"{combined}/{row['select_age']}/{t}",
                    value,
                    value if close else float(total),
                )
    results.append(check.result())

    # Tables 5 and 6: row totals and Male + Female = Total.
    check = _Comparison(
        "AS118_table5_arithmetic",
        "Table 5: total terminations equal the sum of the four reasons; "
        "the total rate equals the sum of the four rates within 0.02 "
        "(four rounded terms); Total-section numbers equal Male + Female",
        "printed",
        "recomputed",
    )
    sections = tables["5"]["sections"]
    for sex, rows in sections.items():
        for row in rows:
            parts = [row[f"{r}_number"] for r in AS118_REASONS[:-1]]
            check.compare(
                f"{sex}/{row['year']}/total_number",
                row["total_number"],
                sum(parts),
            )
            rate_sum = sum(
                _decimal(row[f"{r}_rate"]) for r in AS118_REASONS[:-1]
            )
            close = abs(rate_sum - _decimal(row["total_rate"])) <= _decimal(
                0.02
            )
            check.compare(
                f"{sex}/{row['year']}/total_rate",
                row["total_rate"],
                row["total_rate"] if close else float(rate_sum),
            )
    for male, female, total in zip(
        sections["male"], sections["female"], sections["total"], strict=True
    ):
        for reason in AS118_REASONS:
            column = f"{reason}_number"
            check.compare(
                f"total/{total['year']}/{column}",
                total[column],
                male[column] + female[column],
            )
    results.append(check.result())

    check = _Comparison(
        "AS118_table6_arithmetic",
        "Table 6: the Total column equals the sum of the age groups, and "
        "Total-section counts equal Male + Female",
        "printed",
        "recomputed",
    )
    sections = tables["6"]["sections"]
    for sex, rows in sections.items():
        for row in rows:
            check.compare(
                f"{sex}/{row['year']}/total",
                row["total"],
                sum(row[f"age_{group}"] for group in AS118_AGE_GROUPS),
            )
    for male, female, total in zip(
        sections["male"], sections["female"], sections["total"], strict=True
    ):
        for column in AS118_T6_COLUMNS:
            check.compare(
                f"total/{total['year']}/{column}",
                total[column],
                male[column] + female[column],
            )
    results.append(check.result())

    check = _Comparison(
        "AS118_table4_consistency",
        "Table 4: every Total-section rate lies between the Male and Female "
        "rates (a pooled ratio; 0.01 rounding slack), and the adjusted rate "
        "equals the gross rate in 2000, the adjustment base year (notes 2-3)",
        "printed",
        "consistent",
    )
    sections = tables["4"]["sections"]
    for male, female, total in zip(
        sections["male"], sections["female"], sections["total"], strict=True
    ):
        for column in AS118_T4_COLUMNS:
            low = min(male[column], female[column]) - 0.01
            high = max(male[column], female[column]) + 0.01
            inside = low - 1e-9 <= total[column] <= high + 1e-9
            check.compare(
                f"total/{total['year']}/{column}",
                total[column],
                total[column] if inside else [low, high],
            )
    for sex, rows in sections.items():
        row_2000 = next(row for row in rows if row["year"] == 2000)
        check.compare(
            f"{sex}/2000/adjusted_equals_gross",
            row_2000["total_adjusted"],
            row_2000["total_gross"],
        )
    results.append(check.result())
    return results


def build_as118_observations(
    as118: Mapping[str, Any], single: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Study 118 (2005) history against TR2008's (2008) history.

    Informational: SSA revises historical series between publications, so
    differences are recorded, not reconciled.
    """
    tables = as118["tables"]
    figures = single["figures"]

    def compare(
        pairs: Iterable[tuple[int, float | int, float | int]],
    ) -> dict[str, Any]:
        pairs = list(pairs)
        differing = [
            {"year": year, "study_118": a, "tr2008": b}
            for year, a, b in pairs
            if a != b
        ]
        return {
            "years_compared": len(pairs),
            "equal": len(pairs) - len(differing),
            "differing": differing,
        }

    join_cells = 0
    join_within_one = 0
    join_largest = 0
    join_beyond_one = []
    for q_table, l_table in (
        ("7A", "8A"),
        ("7B", "8B"),
        ("14A", "15A"),
        ("14B", "15B"),
    ):
        q_rows = {r["select_age"]: r for r in tables[q_table]["rows"]}
        for row in tables[l_table]["rows"][1:]:
            lives = row["by_duration"]
            if lives[10] is None:
                continue
            q9 = q_rows[row["select_age"]]["by_duration"][9]
            recomputed = _survival_step(lives[9], q9)
            difference = abs(lives[10] - recomputed)
            join_cells += 1
            join_within_one += difference <= 1
            join_largest = max(join_largest, difference)
            if difference > 1:
                join_beyond_one.append(
                    {
                        "cell": f"{l_table}/{row['select_age']}/10",
                        "printed": lives[10],
                        "duration_9_decremented": recomputed,
                    }
                )
    select_join = {
        "id": "study_118_select_to_ultimate_join",
        "note": (
            "Survivor tables 8A/8B/15A/15B: the ultimate ('10 or more') "
            "cell of select ages 17-64 follows the ultimate column down "
            "(checked), but decrementing the same row's duration-9 cell by "
            "its duration-9 probability reproduces it only within 2. The "
            "select rows and the ultimate column are not an exact identity "
            "in the printed tables; recorded, not reconciled."
        ),
        "cells": join_cells,
        "within_one": join_within_one,
        "largest_difference": join_largest,
        "differing_by_more_than_one": join_beyond_one,
    }

    total4 = {row["year"]: row for row in tables["4"]["sections"]["total"]}
    fig3 = {row["year"]: row for row in figures["V.C3"]["historical"]}
    total5 = {row["year"]: row for row in tables["5"]["sections"]["total"]}
    fig4 = {row["year"]: row for row in figures["V.C4"]["historical"]}
    total6 = {row["year"]: row for row in tables["6"]["sections"]["total"]}
    vc5 = {
        row["year"]: row
        for row in single["tables"]["V.C5"]["sections"]["historical"]
    }
    return [
        select_join,
        {
            "id": "study_118_incidence_vs_tr2008_figure_v_c3",
            "note": (
                "Study 118 Table 4 total gross and age-sex-adjusted "
                "incidence vs TR2008 Figure V.C3 historical plot points."
            ),
            "gross": compare(
                (y, total4[y]["total_gross"], fig3[y]["gross"])
                for y in AS118_YEARS
            ),
            "age_sex_adjusted": compare(
                (y, total4[y]["total_adjusted"], fig3[y]["age_sex_adjusted"])
                for y in AS118_YEARS
            ),
        },
        {
            "id": "study_118_terminations_vs_tr2008_figure_v_c4",
            "note": (
                "Study 118 Table 5 total death + recovery + other rates "
                "(conversions excluded) vs TR2008 Figure V.C4 historical "
                "gross termination plot points."
            ),
            "gross": compare(
                (
                    y,
                    float(
                        sum(
                            _decimal(total5[y][f"{r}_rate"])
                            for r in ("death", "recovery", "other")
                        )
                    ),
                    fig4[y]["gross"],
                )
                for y in AS118_YEARS
            ),
        },
        {
            "id": "study_118_current_pay_vs_tr2008_v_c5",
            "note": (
                "Study 118 Table 6 total disabled workers, rounded half up "
                "to thousands, vs TR2008 single-year V.C5 historical "
                "disabled workers (thousands)."
            ),
            "disabled_workers_thousands": compare(
                (
                    y,
                    int(
                        (_decimal(total6[y]["total"]) / 1000).quantize(
                            _decimal(1), rounding="ROUND_HALF_UP"
                        )
                    ),
                    vc5[y]["disabled_workers_thousands"],
                )
                for y in AS118_YEARS
                if y in vc5
            ),
        },
    ]


def build_observations(
    report: Mapping[str, Any], single: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Informational cross-source comparisons (not pass/fail)."""
    text = {entry["id"]: entry["values"] for entry in report["text_values"]}
    fig3 = {row["year"]: row for row in single["figures"]["V.C3"]["projected"]}
    fig6 = {row["year"]: row for row in single["figures"]["V.C6"]["projected"]}
    fig6_hist = {
        row["year"]: row for row in single["figures"]["V.C6"]["historical"]
    }
    return [
        {
            "id": "di_ultimate_incidence_text_vs_figure_v_c3_2030",
            "text_per_1000": text["di_ultimate_incidence_per_1000_exposed"],
            "figure_v_c3_age_sex_adjusted_2030": fig3[2030][
                "age_sex_adjusted"
            ],
            "note": (
                "The text states ultimate rates for ages through 64 on an "
                "award basis adjusted to the 2000 exposed population. The "
                "figure plot points are not labeled with an age range; they "
                "are recorded side by side, not reconciled."
            ),
        },
        {
            "id": "di_prevalence_text_vs_figure_v_c6",
            "text_per_1000": text["di_prevalence_age_sex_adjusted_per_1000"],
            "figure_v_c6_age_sex_adjusted_2007": fig6_hist[2007][
                "age_sex_adjusted"
            ],
            "figure_v_c6_age_sex_adjusted_2085": fig6[2085][
                "age_sex_adjusted"
            ],
        },
    ]


# --------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------


def build_report(pdf: ReportPdf) -> dict[str, Any]:
    first_page = _normalize(pdf.page(1))
    if "House Document 110-104" not in first_page:
        raise ValueError("PDF page 1 does not identify House Document 110-104")
    referral = re.search(
        r"(April \d{1,2}, 2008)\.?\s*[-\u2014]+\s*Referred to the Committee "
        r"on Ways and Means",
        first_page,
    )
    if referral is None:
        raise ValueError("PDF page 1 lacks the committee referral line")
    return {
        "schema_version": "tr2008_report.v1",
        "trustees_report_year": 2008,
        "vintage_year": 2008,
        "document": {
            "title": (
                "The 2008 Annual Report of the Board of Trustees of the "
                "Federal Old-Age and Survivors Insurance and Federal "
                "Disability Insurance Trust Funds"
            ),
            "house_document": "110th Congress, 2d Session, House Document 110-104",
            "house_referral_date_pdf_page_1": referral.group(1),
            "pdf_sha256": PDF_SHA256,
            "pdf_bytes": PDF_BYTES,
            "pdf_pages": PDF_PAGES,
            "wayback_capture": (
                "https://web.archive.org/web/20100331224612id_/"
                "http://www.ssa.gov/OACT/TR/TR08/tr08.pdf"
            ),
            "wayback_sha1_b32": PDF_WAYBACK_SHA1_B32,
            "page_locators": (
                "pdf_page is the 1-based page index in the PDF; printed_page "
                f"is the number printed on the page (pdf_page - {PRINTED_PAGE_OFFSET})."
            ),
            "extraction": "pdftotext -layout, one page at a time; see scripts/extract_tr2008_parameters.py",
        },
        "alternatives": {
            "intermediate": "Alternative II (Trustees' best estimate)",
            "low_cost": "Alternative I",
            "high_cost": "Alternative III",
        },
        "tables": {
            "II.C1": parse_iic1(pdf),
            "V.A1": parse_va1(pdf),
            "V.A3": parse_va3(pdf),
            "V.A4": parse_va4(pdf),
            "V.B1": parse_vb1(pdf),
            "V.C1": parse_vc1(pdf),
            "V.C5": parse_vc5(pdf),
            "VI.F6": parse_vif6(pdf),
        },
        "text_values": parse_text_values(pdf),
    }


def build_sources() -> dict[str, Any]:
    captures = {}
    for name, (
        ts,
        original,
        sha1_b32,
        sha256,
        size,
        role,
    ) in WAYBACK_SOURCES.items():
        read_source(name)
        captures[name] = {
            "committed_file": f"data/external/tr2008/sources/{name}.gz",
            "compression": "gzip (mtime=0); digests are of the decompressed payload",
            "original_url": original,
            "wayback_timestamp": ts,
            "capture_url": f"https://web.archive.org/web/{ts}id_/{original}",
            "wayback_sha1_b32": sha1_b32,
            "sha256": sha256,
            "bytes": size,
            "retrieved": RETRIEVED,
            "role": role,
        }
    return {
        "schema_version": "tr2008_sources.v1",
        "fetch_method": (
            "Internet Archive raw-capture ('id_') URLs fetched with curl on "
            f"{RETRIEVED}; ssa.gov answers HTTP 403 to programmatic fetches. "
            "Each payload's SHA-1 (base32) equals the Wayback CDX digest for "
            "that capture."
        ),
        "report_pdf": {
            "local_path_at_build": (
                "~/microcosm-launch-evidence/dynasim-parity-20260909/"
                "tr2008-inputs-20260922/tr08-2008-oasdi-trustees-report.pdf "
                "(not committed)"
            ),
            "original_url": "http://www.ssa.gov/OACT/TR/TR08/tr08.pdf",
            "wayback_timestamp": "20100331224612",
            "wayback_sha1_b32": PDF_WAYBACK_SHA1_B32,
            "sha256": PDF_SHA256,
            "bytes": PDF_BYTES,
        },
        "actuarial_study_118_pdf": {
            "local_path_at_build": (
                "~/microcosm-launch-evidence/dynasim-parity-20260909/"
                "tr2008-a2-sources-20260922/actuarial-study-118.pdf (not "
                "committed: the repository's pre-commit configuration "
                "rejects added files over 500 KB)"
            ),
            "original_url": AS118_ORIGINAL_URL,
            "wayback_timestamp": AS118_WAYBACK_TIMESTAMP,
            "capture_url": (
                f"https://web.archive.org/web/{AS118_WAYBACK_TIMESTAMP}id_/"
                f"{AS118_ORIGINAL_URL}"
            ),
            "wayback_sha1_b32": AS118_WAYBACK_SHA1_B32,
            "sha256": AS118_SHA256,
            "bytes": AS118_BYTES,
            "retrieved": RETRIEVED,
            "role": (
                "Actuarial Study 118 (June 2005), 'Social Security "
                "Disability Insurance Program Worker Experience'. TR2008 "
                "section V.C.6.b bases its long-range DI termination rates "
                "on this study's 1996-2000 rates by age, sex and duration. "
                "Tables 4-6, 7A-7C, 8A-8C, 14A-14B, 15A-15B and 21A-21B are "
                "parsed into actuarial_study_118.json."
            ),
        },
        "wayback_captures": captures,
        "located_not_committed": LOCATED_EXTERNAL_SOURCES,
    }


def build_all(pdf_path: Path, as118_path: Path) -> dict[Path, str]:
    pdf = ReportPdf(pdf_path)
    report = build_report(pdf)
    single = build_single_year()
    ssa = build_ssa_2008()
    as118 = build_as118(study_118_pdf(as118_path))
    checks = build_checks(report, single, ssa, as118)
    if not checks["all_passed"]:
        failed = [c["id"] for c in checks["checks"] if not c["passed"]]
        raise SystemExit(f"transcription check failed: {failed}")
    checks["observations"] = [
        *build_observations(report, single),
        *build_as118_observations(as118, single),
    ]
    return {
        REPORT_JSON: _json_dump(report),
        SINGLE_YEAR_JSON: _json_dump(single),
        SSA_2008_JSON: _json_dump(ssa),
        AS118_JSON: _json_dump(as118),
        CHECK_JSON: _json_dump(checks),
        SOURCES_JSON: _json_dump(build_sources()),
    }


def compare_release_pdf(print_pdf: ReportPdf, release_path: Path) -> list[int]:
    """Return transcribed pages whose numeric tokens differ between PDFs."""
    release_raw = release_path.read_bytes()
    expected = LOCATED_EXTERNAL_SOURCES["tr08_release_pdf"]["sha256"]
    if _sha256(release_raw) != expected:
        raise ValueError("release PDF sha256 mismatch")
    pages = sorted(
        {
            *VC1_PAGES,
            *VB1_PAGES,
            *VIF6_PAGES,
            IIC1_PAGE,
            *VA1_PAGES,
            93,
            94,
            *VC5_PAGES,
            *(page for spec in TEXT_SPECS for page in spec[1]),
        }
    )
    token = re.compile(r"\d[\d,]*\.?\d*|\.\d+")
    differing = []
    for page in pages:
        release = subprocess.run(
            [
                "pdftotext",
                "-layout",
                "-f",
                str(page),
                "-l",
                str(page),
                str(release_path),
                "-",
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        if token.findall(release) != token.findall(print_pdf.page(page)):
            differing.append(page)
    print(f"compared numeric tokens on {len(pages)} pages: {pages}")
    return differing


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--pdf", type=Path, default=None)
    parser.add_argument(
        "--as118-pdf",
        type=Path,
        default=None,
        help=f"Actuarial Study 118 PDF (default: ${AS118_ENV} or {AS118_DEFAULT_PDF})",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify committed outputs; write nothing",
    )
    parser.add_argument("--compare-release-pdf", type=Path, default=None)
    args = parser.parse_args(argv)
    pdf_path = args.pdf or Path(os.environ.get(PDF_ENV, DEFAULT_PDF))
    as118_path = args.as118_pdf or Path(
        os.environ.get(AS118_ENV, AS118_DEFAULT_PDF)
    )
    if args.compare_release_pdf is not None:
        differing = compare_release_pdf(
            ReportPdf(pdf_path), args.compare_release_pdf
        )
        print(f"pages with differing numeric tokens: {differing}")
        return 1 if differing else 0
    outputs = build_all(pdf_path, as118_path)
    if args.check:
        stale = [
            str(path.relative_to(ROOT))
            for path, text in outputs.items()
            if not path.exists() or path.read_text(encoding="utf-8") != text
        ]
        if stale:
            print(f"stale outputs: {stale}", file=sys.stderr)
            return 1
        print("committed TR2008 outputs are current")
        return 0
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for path, text in outputs.items():
        path.write_text(text, encoding="utf-8")
        print(
            f"wrote {path.relative_to(ROOT)} sha256={_sha256(text.encode('utf-8'))}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
