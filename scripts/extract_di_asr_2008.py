"""Extract the <=2008 SSDI entitlement inputs from committed raw captures.

Track A item A4 (``critical-path-cola-20260922.md`` section 4) fits the
disabled-worker entitlement component on SSA information available at the
DYNASIM information date: data years no later than 2008.  This script turns
the sha256-pinned raw captures under ``data/external/di_asr_2008/raw/`` into
``data/external/di_asr_2008/tables.json``.  It performs no network access and
no fitting; the fit lives in :mod:`populace_dynamics.engine.di_entitlement_rates`.

Sources (URLs, Wayback capture timestamps, and hashes are in
``data/external/di_asr_2008/provenance.md`` and in ``SOURCES`` below):

* SSA, *Annual Statistical Report on the Social Security Disability
  Insurance Program, 2008* (released July 2009; data year 2008): Tables 19,
  20, 35, 36, 49, 50, 57.
* The same report for 2007 (released September 2008; data year 2007):
  Tables 19, 20, 36, 50.
* SSA Office of the Chief Actuary, Actuarial Study No. 118, *Social Security
  Disability Insurance Program Worker Experience* (June 2005; 1996-2000
  experience): Tables 7A, 7B, 7C, 12 (death) and 14A, 14B, 19 (recovery).
* U.S. Census Bureau, Vintage 2008 and Vintage 2007 national monthly
  resident-population estimates by single year of age and sex (July 1 rows).

Every number is parsed from verbatim cell text.  The script verifies each raw
capture's sha256 before parsing and checks the table labels and internal
totals it relies on, so a wrong file or a shifted column fails loudly.

Run from the repository root::

    .venv/bin/python scripts/extract_di_asr_2008.py
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import html
import io
import json
import re
import sys
from collections.abc import Mapping, Sequence
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "external" / "di_asr_2008"
RAW_DIR = DATA_DIR / "raw"
OUT_PATH = DATA_DIR / "tables.json"

SCHEMA_VERSION = "di_entitlement_inputs.v1"
INFORMATION_BOUNDARY_YEAR = 2008

_ASR = "http://www.ssa.gov/policy/docs/statcomps/di_asr"
_AS118 = "http://www.ssa.gov/OACT/NOTES/as118"
_CENSUS = "http://www.census.gov:80/popest/national/asrh/files"
_ASR_2008_DOC = (
    "SSA, Annual Statistical Report on the Social Security Disability "
    "Insurance Program, 2008 (released July 2009)"
)
_ASR_2007_DOC = (
    "SSA, Annual Statistical Report on the Social Security Disability "
    "Insurance Program, 2007 (released September 2008)"
)
_AS118_DOC = (
    "SSA Office of the Chief Actuary, Actuarial Study No. 118, Social "
    "Security Disability Insurance Program Worker Experience, by Tim "
    "Zayatz (June 2005)"
)
_CENSUS_2008_DOC = (
    "U.S. Census Bureau, NC-EST2008-alldata monthly national population "
    "estimates by age, sex, race and Hispanic origin (Vintage 2008, "
    "released May 14, 2009)"
)
_CENSUS_2007_DOC = (
    "U.S. Census Bureau, NC-EST2007-alldata monthly national population "
    "estimates by age, sex, race and Hispanic origin (Vintage 2007, "
    "released May 2008)"
)


def _source(
    raw_name: str,
    url: str,
    capture: str,
    sha256: str,
    *,
    document: str,
    table: str,
    data_year: str,
    released: str,
) -> dict[str, str]:
    return {
        "file": f"raw/{raw_name}.gz",
        "raw_name": raw_name,
        "url": url,
        "wayback_capture": capture,
        "wayback_url": f"https://web.archive.org/web/{capture}id_/{url}",
        "sha256_uncompressed": sha256,
        "document": document,
        "table": table,
        "data_year": data_year,
        "released": released,
    }


SOURCES: dict[str, dict[str, str]] = {
    "asr2008_table19": _source(
        "asr2008_table19.html",
        f"{_ASR}/2008/table19.html",
        "20090827105022",
        "20716375cdb398cf00cdaef6325708d9a60ae5908f007e13a78183368cfe0a96",
        document=_ASR_2008_DOC,
        table=(
            "Table 19. Disabled workers: percentage distribution, by sex "
            "and age, December 1960-2008, selected years"
        ),
        data_year="1960-2008",
        released="2009-07",
    ),
    "asr2008_table20": _source(
        "asr2008_table20.html",
        f"{_ASR}/2008/table20.html",
        "20090827104934",
        "ce35283fa048f3158a563e3d4fa3fa82b5b8dbe3ae930e830b1cc377a2e108c8",
        document=_ASR_2008_DOC,
        table=(
            "Table 20. Disabled workers: number, average PIA, and average "
            "monthly benefit, by age and sex, December 2008"
        ),
        data_year="2008",
        released="2009-07",
    ),
    "asr2008_table35": _source(
        "asr2008_table35.html",
        f"{_ASR}/2008/table35.html",
        "20090827104955",
        "5343c4a6b26cb47cb67a216c22253d46dbf33a74babcaa3f0eca000d7a8b341d",
        document=_ASR_2008_DOC,
        table="Table 35. Awards: number, selected years 1960-2008",
        data_year="1960-2008",
        released="2009-07",
    ),
    "asr2008_table36": _source(
        "asr2008_table36.html",
        f"{_ASR}/2008/table36.html",
        "20090827105038",
        "856eabc7e0be8e522847751b49336a87a189c28d886267c33e3fd7557547d7c9",
        document=_ASR_2008_DOC,
        table=(
            "Table 36. Awards: number and average monthly benefit, by basis "
            "of entitlement, age, and sex, 2008"
        ),
        data_year="2008",
        released="2009-07",
    ),
    "asr2008_table49": _source(
        "asr2008_table49.html",
        f"{_ASR}/2008/table49.html",
        "20090827105059",
        "85b70dd7a95a28d36bdcd0596ed12e1a4e3810e219fbd64a760460faf5586f24",
        document=_ASR_2008_DOC,
        table="Table 49. Terminations: number and rate, 1960-2008",
        data_year="1960-2008",
        released="2009-07",
    ),
    "asr2008_table50": _source(
        "asr2008_table50.html",
        f"{_ASR}/2008/table50.html",
        "20090827104920",
        "dd0815a9b7b3e73eb803f45fd2231e17ac99c7f934b4f1f117dfe4159fde7123",
        document=_ASR_2008_DOC,
        table="Table 50. Terminations: number, by reason for termination, 2008",
        data_year="2008",
        released="2009-07",
    ),
    "asr2008_table57": _source(
        "asr2008_table57.html",
        f"{_ASR}/2008/table57.html",
        "20090827105023",
        "5ab2c2f8ce6dc383c0ea849ed32e057cd4fffc67374f1346008964a292ae59da",
        document=_ASR_2008_DOC,
        table=(
            "Table 57. Disabled workers who work: distribution, by sex and "
            "age, 2008"
        ),
        data_year="2008",
        released="2009-07",
    ),
    "asr2007_table19": _source(
        "asr2007_table19.html",
        f"{_ASR}/2007/table19.html",
        "20080925083358",
        "501997ae0b4d361c80a36e73a27187d271195d8b1f055a32455225f131f7f28f",
        document=_ASR_2007_DOC,
        table=(
            "Table 19. Disabled workers: percentage distribution, by sex "
            "and age, December 1960-2007, selected years"
        ),
        data_year="1960-2007",
        released="2008-09",
    ),
    "asr2007_table20": _source(
        "asr2007_table20.html",
        f"{_ASR}/2007/table20.html",
        "20080925090141",
        "b4a45d5f907860a522ce65da170cf42f2729b5499a1d3e0678d789913c15da59",
        document=_ASR_2007_DOC,
        table=(
            "Table 20. Disabled workers: number, average PIA, and average "
            "monthly benefit, by age and sex, December 2007"
        ),
        data_year="2007",
        released="2008-09",
    ),
    "asr2007_table36": _source(
        "asr2007_table36.html",
        f"{_ASR}/2007/table36.html",
        "20080925085809",
        "61a0f693269bace888a07555b7a10efd30df6d75543887c82c4e20237a919d3c",
        document=_ASR_2007_DOC,
        table=(
            "Table 36. Awards: number and average monthly benefit, by basis "
            "of entitlement, age, and sex, 2007"
        ),
        data_year="2007",
        released="2008-09",
    ),
    "asr2007_table50": _source(
        "asr2007_table50.html",
        f"{_ASR}/2007/table50.html",
        "20080925085433",
        "d721a61f483be5f51525656b8685bcd1c7f8bd6a9bfd221e1b023eb071af6c09",
        document=_ASR_2007_DOC,
        table="Table 50. Terminations: number, by reason for termination, 2007",
        data_year="2007",
        released="2008-09",
    ),
    "census_v2008_r_file18": _source(
        "census_nc_est2008_alldata_r_file18.csv",
        f"{_CENSUS}/NC-EST2008-ALLDATA-R-File18.csv",
        "20090617025147",
        "24a601a9ae9d01d2c0263c4cc5004dc9efece556a72877f2916a5b68a05772ea",
        document=_CENSUS_2008_DOC,
        table=(
            "NC-EST2008-ALLDATA-R-File18: resident population, July-"
            "December 2008 (July 1, 2008 rows used)"
        ),
        data_year="2008",
        released="2009-05-14",
    ),
    "census_v2008_layout": _source(
        "census_nc_est2008_alldata_layout.pdf",
        f"{_CENSUS}/NC-EST2008-ALLDATA.pdf",
        "20090617153131",
        "e8aa72077b9f3633fc3cd8888efbb6ab9b80e6d9be76ca88fa71c1d530bfbbd1",
        document=_CENSUS_2008_DOC,
        table="NC-EST2008-alldata file layout",
        data_year="2008",
        released="2009-05-14",
    ),
    "census_v2007_r_file16": _source(
        "census_nc_est2007_alldata_r_file16.csv",
        f"{_CENSUS}/NC-EST2007-ALLDATA-R-File16.csv",
        "20080606035911",
        "4929eee2c75f642ee9083d4f93e3787961ebcf48002283e356ad8aa37b8a77a4",
        document=_CENSUS_2007_DOC,
        table=(
            "NC-EST2007-ALLDATA-R-File16: resident population, July-"
            "December 2007 (July 1, 2007 rows used)"
        ),
        data_year="2007",
        released="2008-05",
    ),
    "as118_death_tables": _source(
        "as118_death_tables.html",
        f"{_AS118}/DI-WrkerExper_DeathTbls.html",
        "20060930030715",
        "32943f7e1c7ac13f2163a8f2fae3ca7b43c0a54f39abd1cb69bb0495bbd4a153",
        document=_AS118_DOC,
        table=(
            "Tables 7A-7C (probability of death by select age and duration, "
            "1996-2000) and Table 12 (aggregate probability of death by "
            "attained age)"
        ),
        data_year="1996-2000",
        released="2005-06",
    ),
    "as118_recovery_tables": _source(
        "as118_recovery_tables.html",
        f"{_AS118}/DI-WrkerExper_RecoveryTbls.html",
        "20060930030754",
        "faf9bad87b4b849463103a35810a34835057857d1f06e748205616ca84f4bd92",
        document=_AS118_DOC,
        table=(
            "Tables 14A-14B (probability of recovery by select age and "
            "duration, 1996-2000) and Table 19 (aggregate probability of "
            "recovery by attained age)"
        ),
        data_year="1996-2000",
        released="2005-06",
    ),
}

ASR_STOCK_GROUPS = (
    "Under 25",
    "25–29",
    "30–34",
    "35–39",
    "40–44",
    "45–49",
    "50–54",
    "55–59",
    "60–64",
    "65–FRA",
)
ASR_2007_AWARD_GROUPS = (*ASR_STOCK_GROUPS[:-1], "65 or older")
ASR_TABLE19_GROUPS = (
    "Under 30",
    "30–34",
    "35–39",
    "40–44",
    "45–49",
    "50–54",
    "55–59",
    "60–FRA",
)
TABLE50_ROWS = {
    "Death of beneficiary": "death",
    "FRA by disabled workers": "fra_conversion",
    "Elected reduced retirement": "elected_reduced_retirement",
    "Does not meet medical standards b": "does_not_meet_medical_standards",
    "Medical improvement c": "medical_improvement",
    "Work above substantial gainful activity d": "work_above_sga",
    "Miscellaneous reasons e": "miscellaneous",
    "Other": "other",
    "Total": "total",
}


class _TableParser(HTMLParser):
    """Collect top-level HTML tables as caption plus rows of cell text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[dict[str, Any]] = []
        self._depth = 0
        self._table: dict[str, Any] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None
        self._caption: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        if tag == "table":
            self._depth += 1
            if self._depth == 1:
                self._table = {"caption": "", "rows": []}
        elif self._table is None:
            return
        elif tag == "caption":
            self._caption = []
        elif tag == "tr":
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []
        elif tag == "br" and self._cell is not None:
            self._cell.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag == "table":
            if self._depth == 1 and self._table is not None:
                self.tables.append(self._table)
                self._table = None
            self._depth -= 1
        elif tag == "caption" and self._caption is not None:
            if self._table is not None:
                self._table["caption"] = _clean("".join(self._caption))
            self._caption = None
        elif tag in ("td", "th") and self._cell is not None:
            if self._row is not None:
                self._row.append(_clean("".join(self._cell)))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._table is not None:
                self._table["rows"].append(self._row)
            self._row = None

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)
        elif self._caption is not None:
            self._caption.append(data)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def read_raw(source_id: str) -> bytes:
    """Return a capture's original bytes after verifying its sha256."""
    source = SOURCES[source_id]
    path = DATA_DIR / source["file"]
    data = gzip.decompress(path.read_bytes())
    digest = hashlib.sha256(data).hexdigest()
    if digest != source["sha256_uncompressed"]:
        raise ValueError(
            f"{source_id}: raw sha256 {digest} != pinned "
            f"{source['sha256_uncompressed']}"
        )
    return data


def html_tables(source_id: str) -> list[dict[str, Any]]:
    parser = _TableParser()
    parser.feed(read_raw(source_id).decode("latin-1"))
    return parser.tables


def _number(text: str) -> float | None:
    """Parse one published cell; ``None`` for SSA's not-applicable marks."""
    stripped = text.strip()
    if stripped in {"", "--", "—", ". . .", "(X)", "1/"}:
        return None
    cleaned = stripped.replace(",", "")
    if not re.fullmatch(r"-?\d+(\.\d+)?", cleaned):
        raise ValueError(f"unparseable numeric cell {text!r}")
    return float(cleaned)


def _integer(text: str) -> int:
    value = _number(text)
    if value is None or value != int(value):
        raise ValueError(f"expected an integer count, got {text!r}")
    return int(value)


def _nonblank_rows(rows: Sequence[Sequence[str]]) -> list[list[str]]:
    return [list(row) for row in rows if any(cell for cell in row)]


def _only_table(source_id: str) -> list[list[str]]:
    tables = html_tables(source_id)
    if len(tables) != 1:
        raise ValueError(f"{source_id}: expected one table, got {len(tables)}")
    return _nonblank_rows(tables[0]["rows"])


def _row_after(
    rows: Sequence[Sequence[str]], label: str, *, start: int = 0
) -> tuple[int, list[str]]:
    for index in range(start, len(rows)):
        if rows[index] and rows[index][0] == label:
            return index, list(rows[index])
    raise ValueError(f"row {label!r} not found")


def _section_start(rows: Sequence[Sequence[str]], title: str) -> int:
    for index, row in enumerate(rows):
        if len(row) >= 2 and row[0] == "" and row[1].startswith(title):
            return index
    raise ValueError(f"section {title!r} not found")


def parse_table20(source_id: str) -> dict[str, Any]:
    """December disabled-worker stock by age group and sex."""
    rows = _only_table(source_id)
    if rows[0][:4] != ["Age", "Total", "Men", "Women"]:
        raise ValueError(f"{source_id}: unexpected header {rows[0]}")
    _, total_row = _row_after(rows, "All disabled workers")
    out: dict[str, Any] = {
        "source": source_id,
        "concept": "disabled workers in current-payment status, December",
        "age_groups": list(ASR_STOCK_GROUPS),
        "total": [],
        "male": [],
        "female": [],
    }
    for group in ASR_STOCK_GROUPS:
        _, row = _row_after(rows, group)
        out["total"].append(_integer(row[1]))
        out["male"].append(_integer(row[4]))
        out["female"].append(_integer(row[7]))
    out["totals"] = {
        "total": _integer(total_row[1]),
        "male": _integer(total_row[4]),
        "female": _integer(total_row[7]),
    }
    for key in ("total", "male", "female"):
        if sum(out[key]) != out["totals"][key]:
            raise ValueError(f"{source_id}: {key} age groups do not sum")
    return out


def parse_table36(source_id: str, groups: Sequence[str]) -> dict[str, Any]:
    """Disabled-worker awards by age group and sex for one calendar year."""
    rows = _only_table(source_id)
    start = _section_start(rows, "Workers")
    end = _section_start(rows, "Spouses of disabled workers")
    section = rows[start:end]
    _, total_row = _row_after(section, "Total")
    out: dict[str, Any] = {
        "source": source_id,
        "concept": (
            "awards to disabled workers during the calendar year; age at "
            "entitlement (report note: starting with 2007, age is based on "
            "date of entitlement, not date of award)"
        ),
        "age_groups": list(groups),
        "total": [],
        "male": [],
        "female": [],
    }
    for group in groups:
        _, row = _row_after(section, group)
        out["total"].append(_integer(row[1]))
        out["male"].append(_integer(row[3]))
        out["female"].append(_integer(row[5]))
    out["totals"] = {
        "total": _integer(total_row[1]),
        "male": _integer(total_row[3]),
        "female": _integer(total_row[5]),
    }
    for key in ("total", "male", "female"):
        if sum(out[key]) != out["totals"][key]:
            raise ValueError(f"{source_id}: {key} award groups do not sum")
    notes = " ".join(" ".join(row) for row in rows[end:])
    if "age is based on date of entitlement" not in notes:
        raise ValueError(f"{source_id}: entitlement-age note not found")
    return out


def parse_table19(source_id: str) -> dict[str, Any]:
    """Disabled-worker stock totals (thousands) and age distribution."""
    rows = _only_table(source_id)
    header = [
        re.sub(r" [a-z]$", "", cell)
        for cell in rows[1][: len(ASR_TABLE19_GROUPS) + 1]
    ]
    if header != ["Total, all ages", *ASR_TABLE19_GROUPS]:
        raise ValueError(f"{source_id}: unexpected age header {rows[1]}")
    sections = {
        "all": _section_start(rows, "All disabled workers"),
        "men": _section_start(rows, "Men"),
        "women": _section_start(rows, "Women"),
    }
    order = sorted(sections.items(), key=lambda item: item[1])
    out: dict[str, Any] = {
        "source": source_id,
        "concept": (
            "disabled workers in current-payment status, December: number "
            "in thousands and percentage distribution by age"
        ),
        "age_groups": list(ASR_TABLE19_GROUPS),
    }
    for position, (name, begin) in enumerate(order):
        finish = (
            order[position + 1][1] if position + 1 < len(order) else len(rows)
        )
        years: dict[str, Any] = {}
        for row in rows[begin + 1 : finish]:
            if not re.fullmatch(r"\d{4}", row[0]):
                continue
            number = _number(row[1])
            # Footnote "a": ages 30-34 are included in 35-39 in early years.
            percents = [
                None if cell == "a" else _number(cell)
                for cell in row[3 : 3 + 8]
            ]
            years[row[0]] = {
                "number_thousands": number,
                "percent": percents,
                "average_age": _number(row[11]) if len(row) > 11 else None,
            }
        out[name] = years
    return out


def parse_table50(source_id: str) -> dict[str, Any]:
    """Disabled-worker terminations by reason for one calendar year."""
    rows = _only_table(source_id)
    if rows[1][0] != "Workers":
        raise ValueError(f"{source_id}: unexpected column header {rows[1]}")
    out: dict[str, Any] = {
        "source": source_id,
        "concept": "terminations of disabled-worker benefits in the year",
    }
    for label, key in TABLE50_ROWS.items():
        _, row = _row_after(rows, label)
        out[key] = _integer(row[2])
    components = (
        out["medical_improvement"]
        + out["work_above_sga"]
        + out["miscellaneous"]
    )
    if components != out["does_not_meet_medical_standards"]:
        raise ValueError(f"{source_id}: medical-standards components differ")
    listed = (
        out["death"]
        + out["fra_conversion"]
        + out["elected_reduced_retirement"]
        + out["does_not_meet_medical_standards"]
        + out["other"]
    )
    if listed != out["total"]:
        raise ValueError(
            f"{source_id}: worker termination reasons sum to {listed}, "
            f"not {out['total']}"
        )
    return out


def parse_table49(source_id: str) -> dict[str, Any]:
    rows = _only_table(source_id)
    years = {}
    for row in rows:
        if re.fullmatch(r"\d{4}", row[0]):
            years[row[0]] = {
                "number": _integer(row[3]),
                "rate_per_1000": _number(row[4]),
            }
    return {
        "source": source_id,
        "concept": (
            "disabled-worker terminations and rate per 1,000 beneficiaries "
            "in current-payment status"
        ),
        "years": years,
    }


def parse_table35(source_id: str) -> dict[str, Any]:
    rows = _only_table(source_id)
    if rows[1][0] != "Workers":
        raise ValueError(f"{source_id}: unexpected column header {rows[1]}")
    years = {
        row[0]: _integer(row[2])
        for row in rows
        if re.fullmatch(r"\d{4}", row[0])
    }
    return {
        "source": source_id,
        "concept": "awards to disabled workers during the calendar year",
        "years": years,
    }


def parse_table57(source_id: str) -> dict[str, Any]:
    rows = _only_table(source_id)
    out: dict[str, Any] = {
        "source": source_id,
        "concept": (
            "workers with benefits terminated because of successful return "
            "to work, calendar year; December stock alongside"
        ),
        "age_groups": ["Under 30", "30–39", "40–49", "50–59", "60–FRA"],
    }
    for name, title in (("male", "Men"), ("female", "Women")):
        begin = _section_start(rows, title)
        stock, withheld, terminated = [], [], []
        for group in out["age_groups"]:
            _, row = _row_after(rows, group, start=begin)
            stock.append(_integer(row[1]))
            withheld.append(_integer(row[2]))
            terminated.append(_integer(row[4]))
        out[name] = {
            "december_stock": stock,
            "withheld_substantial_work": withheld,
            "terminated_return_to_work": terminated,
        }
    return out


def parse_census(source_id: str, year: int) -> dict[str, Any]:
    """July 1 resident population by single year of age and sex."""
    text = read_raw(source_id).decode("ascii")
    rows = [
        row
        for row in csv.DictReader(io.StringIO(text))
        if row["MONTH"] == "7" and row["YEAR"] == str(year)
    ]
    if not rows or {row["UNIVERSE"] for row in rows} != {"R"}:
        raise ValueError(f"{source_id}: July resident rows not found")
    by_age = {int(row["AGE"]): row for row in rows}
    ages = list(range(0, 101))
    if set(by_age) != {*ages, 999}:
        raise ValueError(f"{source_id}: unexpected age coverage")
    male = [int(by_age[age]["TOT_MALE"]) for age in ages]
    female = [int(by_age[age]["TOT_FEMALE"]) for age in ages]
    total_row = by_age[999]
    if sum(male) != int(total_row["TOT_MALE"]) or sum(female) != int(
        total_row["TOT_FEMALE"]
    ):
        raise ValueError(f"{source_id}: single ages do not sum to totals")
    return {
        "source": source_id,
        "concept": "resident population, July 1",
        "reference_date": f"{year}-07-01",
        "ages": ages,
        "top_age_is_open_interval": True,
        "male": male,
        "female": female,
    }


def _caption_table(
    tables: Sequence[Mapping[str, Any]], caption_prefix: str
) -> list[list[str]]:
    matches = [
        table
        for table in tables
        if str(table["caption"]).startswith(caption_prefix)
    ]
    if len(matches) != 1:
        raise ValueError(f"expected one table captioned {caption_prefix!r}")
    return _nonblank_rows(matches[0]["rows"])


def _select_ultimate(rows: Sequence[Sequence[str]]) -> dict[str, Any]:
    header = rows[1]
    if header != [str(d) for d in range(10)] + ["10 or more"]:
        raise ValueError(f"unexpected duration header {header}")
    select_ages, rates, ultimate, attained = [], [], [], []
    for row in rows[2:]:
        if not re.fullmatch(r"\d+", row[0]):
            continue
        select_ages.append(int(row[0]))
        values = [_number(cell) for cell in row[1:12]]
        rates.append(values[:10])
        ultimate.append(values[10])
        attained.append(int(row[12]))
    if select_ages != list(range(16, 65)):
        raise ValueError(f"unexpected select ages {select_ages}")
    if attained != [age + 10 for age in select_ages]:
        raise ValueError("ultimate attained-age column is misaligned")
    return {
        "select_ages": select_ages,
        "durations": list(range(10)),
        "select": rates,
        "ultimate": ultimate,
        "ultimate_attained_ages": attained,
    }


def parse_as118_death() -> dict[str, Any]:
    tables = html_tables("as118_death_tables")
    male = _select_ultimate(
        _caption_table(tables, "Table 7A.—Male Disabled Workers")
    )
    female = _select_ultimate(
        _caption_table(tables, "Table 7B.—Female Disabled Workers")
    )
    old = _caption_table(tables, "Table 7C.—Disabled Workers Age 75")
    ages, old_male, old_female = [], [], []
    for row in old:
        cells = [cell for cell in row if cell]
        if cells and re.fullmatch(r"\d+", cells[0]):
            ages.append(int(cells[0]))
            old_male.append(_number(cells[1]))
            old_female.append(_number(cells[2]))
    if ages != list(range(75, 111)):
        raise ValueError(f"Table 7C ages {ages[:3]}...{ages[-3:]}")
    aggregate = _caption_table(tables, "Table 12.—Disabled Workers")
    agg_ages, agg_male, agg_female = [], [], []
    for row in aggregate:
        if re.fullmatch(r"\d+", row[0]):
            agg_ages.append(int(row[0]))
            agg_male.append(_number(row[1]))
            agg_female.append(_number(row[3]))
    if agg_ages != list(range(16, 75)):
        raise ValueError(f"Table 12 ages {agg_ages[:3]}...{agg_ages[-3:]}")
    return {
        "source": "as118_death_tables",
        "experience_period": "1996-2000",
        "select_ultimate": {"male": male, "female": female},
        "ultimate_75_plus": {
            "ages": ages,
            "male": old_male,
            "female": old_female,
        },
        "aggregate_by_attained_age": {
            "ages": agg_ages,
            "male": agg_male,
            "female": agg_female,
        },
    }


def parse_as118_recovery() -> dict[str, Any]:
    tables = html_tables("as118_recovery_tables")
    male = _select_ultimate(
        _caption_table(tables, "Table 14A.—Male Disabled Workers")
    )
    female = _select_ultimate(
        _caption_table(tables, "Table 14B.—Female Disabled Workers")
    )
    aggregate = _caption_table(tables, "Table 19.—Disabled Workers")
    ages, agg_male, agg_female = [], [], []
    for row in aggregate:
        if re.fullmatch(r"\d+", row[0]):
            ages.append(int(row[0]))
            agg_male.append(_number(row[1]))
            agg_female.append(_number(row[3]))
    if ages != list(range(16, 65)):
        raise ValueError(f"Table 19 ages {ages[:3]}...{ages[-3:]}")
    return {
        "source": "as118_recovery_tables",
        "experience_period": "1996-2000",
        "select_ultimate": {"male": male, "female": female},
        "aggregate_by_attained_age": {
            "ages": ages,
            "male": agg_male,
            "female": agg_female,
        },
    }


def build() -> dict[str, Any]:
    """Assemble the deterministic extracted-inputs artifact."""
    for source_id in SOURCES:
        read_raw(source_id)
    return {
        "schema_version": SCHEMA_VERSION,
        "information_boundary_year": INFORMATION_BOUNDARY_YEAR,
        "purpose": (
            "Fitting inputs for the Track A (A4) SSDI disabled-worker "
            "entitlement component. Every data year is <= 2008. These are "
            "SSA administrative statistics and Census population estimates, "
            "not DYNASIM or Urban Institute comparator values."
        ),
        "extracted_by": "scripts/extract_di_asr_2008.py",
        "sources": SOURCES,
        "asr": {
            "2008": {
                "awards_workers": parse_table36(
                    "asr2008_table36", ASR_STOCK_GROUPS
                ),
                "stock_workers_december": parse_table20("asr2008_table20"),
                "stock_distribution": parse_table19("asr2008_table19"),
                "terminations_workers_by_reason": parse_table50(
                    "asr2008_table50"
                ),
                "terminations_workers_series": parse_table49(
                    "asr2008_table49"
                ),
                "awards_workers_series": parse_table35("asr2008_table35"),
                "return_to_work_terminations": parse_table57(
                    "asr2008_table57"
                ),
            },
            "2007": {
                "awards_workers": parse_table36(
                    "asr2007_table36", ASR_2007_AWARD_GROUPS
                ),
                "stock_workers_december": parse_table20("asr2007_table20"),
                "stock_distribution": parse_table19("asr2007_table19"),
                "terminations_workers_by_reason": parse_table50(
                    "asr2007_table50"
                ),
            },
        },
        "census_resident_population_july1": {
            "2008": parse_census("census_v2008_r_file18", 2008),
            "2007": parse_census("census_v2007_r_file16", 2007),
        },
        "as118": {
            "death": parse_as118_death(),
            "recovery": parse_as118_recovery(),
        },
    }


def serialize(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, indent=1, ensure_ascii=False) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    text = serialize(build())
    if args == ["--check"]:
        current = OUT_PATH.read_text(encoding="utf-8")
        if current != text:
            print(f"{OUT_PATH} is stale", file=sys.stderr)
            return 1
        return 0
    if args:
        raise SystemExit("usage: extract_di_asr_2008.py [--check]")
    OUT_PATH.write_text(text, encoding="utf-8")
    print(f"wrote {OUT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
