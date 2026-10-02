"""Rebuild CBO2026 baseline inputs from pinned, captured source bytes.

Only demographic inputs, economic inputs and the covered-worker/earnings
rows of Additional-Info sheets 1-2 are parsed. No fiscal outcome tables or
Additional-Info footnotes are emitted. CBO files were recovered from raw
Wayback captures; SHA-1/base32 digests are checked against captured CDX
records as well as SHA-256. See ``data/external/cbo2026/provenance.md``.

``--inputs`` names the captured ``baseline-inputs`` directory. Small raw
sources may be bundled; larger sources remain external, by URL and hash.
``--check`` rebuilds in memory and compares every output byte, writing
nothing. Inputs are never downloaded by this script.
"""

from __future__ import annotations

import argparse
import base64
import csv
import gzip
import hashlib
import io
import json
import math
import re
import sys
import zipfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from populace_dynamics.data.life_table import life_expectancy

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "external" / "cbo2026"
DEFAULT_INPUTS = Path(
    "/Users/maxghenis/microcosm-launch-evidence/nasi-meeting-20261001/"
    "followup/inputs/baseline-inputs"
)
DEMOGRAPHIC_PREFIX = "cbo/extracted/57059-2026-01-Demographic-Projections/"
PLACES = ("all", "native-born", "foreign-born")
SEXES = ("male", "female")
LE_TOLERANCE = 0.0011
TFR_TOLERANCE = 0.0023
NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


@dataclass(frozen=True)
class Source:
    """An immutable captured-source identity, never a live URL request."""

    relative_path: str
    sha256: str
    url: str
    locator: str
    timestamp: str | None = None
    cdx_sha1_b32: str | None = None


ZIP_URL = (
    "https://www.cbo.gov/system/files/2026-01/"
    "57059-2026-01-Demographic-Projections.zip"
)
SOURCES: Mapping[str, Source] = {
    "demographic_archive": Source(
        "cbo/57059-2026-01-Demographic-Projections.zip",
        "083ea91701c1af901cd378211a34c8c8a941c8833c2507564af89551d63392bf",
        ZIP_URL,
        "Archive containing the demographic CSV files and workbook",
        "20260211074115",
        "AUU73LM3P3IH4ITJSNMHQM7T7UEHJCDD",
    ),
    "fertility": Source(
        DEMOGRAPHIC_PREFIX + "CSV Files/fertilityRates_byYearAgePlace.csv",
        "8ed8615ed7561d6c08c3005dc516b8dd78c16072020e8c106a5738a5563b0f1c",
        ZIP_URL,
        "CSV Files/fertilityRates_byYearAgePlace.csv: year,age,"
        "place_of_birth,births_per_1000_females",
    ),
    "mortality": Source(
        DEMOGRAPHIC_PREFIX + "CSV Files/mortalityRates_byYearAgeSex.csv",
        "378defc1d6eee7b6870cc7ddaf534dd782d51bf3f686a39a8fd7cd7cba2beb63",
        ZIP_URL,
        "CSV Files/mortalityRates_byYearAgeSex.csv: year,age,sex,"
        "deaths_per_1000_people",
    ),
    "demographic_workbook": Source(
        DEMOGRAPHIC_PREFIX + "61879-Demographic-Projections.xlsx",
        "aca3322e0a74fee39e669d953201075887da13e5e3792e08b8b6f7d1f86d1006",
        ZIP_URL,
        "61879-Demographic-Projections.xlsx: '1. Population and growth'; "
        "row 8 years; r39 TFR; r41 life expectancy at birth; r42 at 65",
    ),
    "long_term_economics": Source(
        "cbo/57054-2026-02-LTBO-econ.xlsx",
        "6f6e66d7e2aaf187e0d13aa90767a39e682a6a5ab2be87b0cc2221b7370e6929",
        "https://www.cbo.gov/system/files/2026-02/"
        "57054-2026-02-LTBO-econ.xlsx",
        "'1. Econ Vars_Annual Rates': r8 years,r31 real earnings growth,"
        "r40 CPI-U growth; '3. Econ Vars_Annual Levels': r7 years,r13 CPI-U",
        "20260726122828",
        "OWABBCNJ5O2UJGAZDVBAK2SLWSCHOFLK",
    ),
    "ten_year_economics": Source(
        "cbo/51135-2026-02-Economic-Projections.xlsx",
        "ae8f4920702fabf8fb3136bc94a42c53466cff5e890dec22396d8dc49dc2f776",
        "https://www.cbo.gov/system/files/2026-02/"
        "51135-2026-02-Economic-Projections.xlsx",
        "'2. Calendar Year': r7 years; r53 CPI-U (1982-84=100)",
        "20260802034021",
        "SLIHKFJTIHK62CO3YN5CYBRU4PIQCB4D",
    ),
    "covered_earnings": Source(
        "cbo/62556-2026-Additional-Info.xlsx",
        "7a7247651f3ae6820c9263a16f11b9cc9cf24cd7dcb9e18bb76e44711924d73b",
        "https://www.cbo.gov/system/files/2026-09/"
        "62556-2026-Additional-Info.xlsx",
        "'1. Covered Workers': numeric year rows,male/female/total "
        "(thousands); '2. Covered and Taxable Earnings': numeric year "
        "rows,covered earnings column B (trillions of dollars)",
        "20260919143154",
        "DTGXZD5RVUA4T4SH3HTVHBHFOFS3DR3I",
    ),
    "actual_awi_anchor": Source(
        "tr2026/lr6g1.html",
        "2e0214278e0b2271616093af02280277f6e363d112c47a90b49fe7168e795e75",
        "https://www.ssa.gov/oact/TR/2026/lr6g1.html",
        "TR2026 Table VI.G1, Historical data, CY2024 AWI column",
    ),
}


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha1_b32(raw: bytes) -> str:
    return base64.b32encode(hashlib.sha1(raw).digest()).decode("ascii")


def deterministic_gzip(raw: bytes) -> bytes:
    """Use a portable gzip header across supported Python versions."""
    buffer = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buffer, mtime=0) as f:
        f.write(raw)
    return buffer.getvalue()


def read_source(name: str, inputs: Path) -> bytes:
    """Verify captured or bundled payload before parsing any data value."""
    spec = SOURCES[name]
    captured = inputs / spec.relative_path
    bundled = OUT_DIR / "sources" / (Path(spec.relative_path).name + ".gz")
    if captured.is_file():
        raw = captured.read_bytes()
    elif bundled.is_file():
        raw = gzip.decompress(bundled.read_bytes())
    else:
        raise FileNotFoundError(
            f"source {name} is external: provide --inputs containing "
            f"{spec.relative_path}; expected sha256 {spec.sha256}"
        )
    if sha256(raw) != spec.sha256:
        raise ValueError(f"{name} captured-source SHA-256 mismatch")
    if spec.cdx_sha1_b32 and sha1_b32(raw) != spec.cdx_sha1_b32:
        raise ValueError(f"{name} Wayback CDX digest mismatch")
    return raw


def workbook_rows(
    raw: bytes, sheet: str, *, selected: set[int] | None = None
) -> dict[int, dict[str, str]]:
    """Read cached XLSX values from one named input sheet.

    XML row filtering avoids traversing fiscal sheets or printing workbook
    strings. ``selected`` is used for summaries; callers reading numeric
    year tables consume only rows whose column A is a year.
    """
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        strings = [
            "".join(node.itertext())
            for node in ET.fromstring(
                archive.read("xl/sharedStrings.xml")
            ).findall("s:si", NS)
        ]
        relationships = {
            node.attrib["Id"]: node.attrib["Target"]
            for node in ET.fromstring(
                archive.read("xl/_rels/workbook.xml.rels")
            )
        }
        sheets = ET.fromstring(archive.read("xl/workbook.xml")).findall(
            "s:sheets/s:sheet", NS
        )
        matching = [node for node in sheets if node.attrib["name"] == sheet]
        if len(matching) != 1:
            raise ValueError(f"expected one input sheet {sheet!r}")
        relationship = matching[0].attrib[
            "{http://schemas.openxmlformats.org/officeDocument/"
            "2006/relationships}id"
        ]
        target = relationships[relationship]
        path = target.lstrip("/") if target.startswith("/") else "xl/" + target
        rows = {}
        for node in ET.fromstring(archive.read(path)).findall(
            "s:sheetData/s:row", NS
        ):
            number = int(node.attrib["r"])
            if selected is not None and number not in selected:
                continue
            cells = {}
            for cell in node:
                value = cell.find("s:v", NS)
                if value is None or value.text is None:
                    continue
                text = value.text
                if cell.attrib.get("t") == "s":
                    text = strings[int(text)]
                cells[re.sub(r"[0-9]+$", "", cell.attrib["r"])] = text
            rows[number] = cells
        return rows


def year_columns(row: Mapping[str, str], first: int, last: int) -> dict:
    out = {
        int(value): column
        for column, value in row.items()
        if value.isdigit() and first <= int(value) <= last
    }
    selected_count = sum(
        value.isdigit() and first <= int(value) <= last
        for value in row.values()
    )
    if len(out) != selected_count:
        raise ValueError("duplicate year columns")
    if set(out) != set(range(first, last + 1)):
        raise ValueError(f"year columns do not cover {first}..{last}")
    return out


def parse_age_csv(
    raw: bytes,
    group_column: str,
    value_column: str,
    groups: Sequence[str],
    first_age: int,
    last_age: int,
) -> dict[str, dict[str, list[float]]]:
    """Refuse duplicate or missing age cells and preserve printed units."""
    cells: dict[tuple[int, str], dict[int, float]] = {}
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    expected = {"year", "age", group_column, value_column}
    if (
        len(reader.fieldnames or ()) != len(expected)
        or set(reader.fieldnames or ()) != expected
    ):
        raise ValueError("unexpected demographic CSV columns")
    for row in reader:
        year, age = int(row["year"]), int(row["age"])
        group = row[group_column]
        if not 2021 <= year <= 2099 or group not in groups:
            raise ValueError("demographic CSV has unexpected year/group")
        if not first_age <= age <= last_age:
            raise ValueError("demographic CSV has unexpected age")
        key = year, group
        ages = cells.setdefault(key, {})
        if age in ages:
            raise ValueError(f"duplicate demographic cell {key}, age {age}")
        value = float(row[value_column])
        if not math.isfinite(value) or value < 0:
            raise ValueError("demographic CSV has invalid rate")
        ages[age] = value
    out = {}
    for year in range(2021, 2100):
        out[str(year)] = {}
        for group in groups:
            ages = cells.get((year, group), {})
            if set(ages) != set(range(first_age, last_age + 1)):
                raise ValueError(
                    f"missing demographic ages for {year},{group}"
                )
            out[str(year)][group] = [
                ages[age] for age in range(first_age, last_age + 1)
            ]
    return out


class _Year2024(HTMLParser):
    """Select the AWI anchor row without extracting unrelated columns."""

    def __init__(self) -> None:
        super().__init__()
        self.in_cell = False
        self.row: list[str] = []
        self.text: list[str] = []
        self.anchors: list[float] = []
        self.has_awi_header = False

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        elif tag in ("td", "th"):
            self.in_cell = True
            self.text = []

    def handle_data(self, data):
        if self.in_cell:
            self.text.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th"):
            text = "".join(self.text).strip()
            if text:
                self.row.append(text)
            self.in_cell = False
        elif tag == "tr":
            label = re.sub(r"\s+", " ", " ".join(self.row)).casefold()
            if "wage index" in label:
                self.has_awi_header = True
            if len(self.row) >= 3 and re.fullmatch(
                r"2024\s*[a-z]?", self.row[0]
            ):
                # VI.G1 nonempty cells: year,adjusted CPI,AWI,...
                self.anchors.append(float(self.row[2].replace(",", "")))


def parse_awi_anchor(raw: bytes) -> float:
    parser = _Year2024()
    parser.feed(raw.decode("utf-8"))
    if (
        not parser.has_awi_header
        or len(parser.anchors) != 1
        or parser.anchors[0] <= 0
    ):
        raise ValueError("expected one positive actual 2024 AWI anchor")
    return parser.anchors[0]


def build_demographics(raw: Mapping[str, bytes]) -> dict[str, Any]:
    asfr = parse_age_csv(
        raw["fertility"],
        "place_of_birth",
        "births_per_1000_females",
        PLACES,
        14,
        49,
    )
    mortality = parse_age_csv(
        raw["mortality"],
        "sex",
        "deaths_per_1000_people",
        SEXES,
        0,
        119,
    )
    rows = workbook_rows(
        raw["demographic_workbook"],
        "1. Population and growth",
        selected={8, 39, 41, 42},
    )
    columns = year_columns(rows[8], 2026, 2099)
    summary = {
        str(year): {
            "tfr": float(rows[39][column]),
            "life_expectancy_birth": float(rows[41][column]),
            "life_expectancy_65": float(rows[42][column]),
        }
        for year, column in columns.items()
    }
    return {
        "schema_version": "cbo2026_demographics.v1",
        "asfr_ages": [14, 49],
        "asfr_units": "births_per_1000_females",
        "asfr": asfr,
        "mortality_ages": [0, 119],
        "mortality_units": "deaths_per_1000_people (empirically q*1000)",
        "mortality": mortality,
        "published_summary": summary,
        "source_keys": ["fertility", "mortality", "demographic_workbook"],
    }


def build_economics(raw: Mapping[str, bytes]) -> dict[str, Any]:
    rates = workbook_rows(
        raw["long_term_economics"],
        "1. Econ Vars_Annual Rates",
        selected={8, 31, 40},
    )
    levels = workbook_rows(
        raw["long_term_economics"],
        "3. Econ Vars_Annual Levels",
        selected={7, 13},
    )
    columns = year_columns(rates[8], 1996, 2056)
    level_columns = year_columns(levels[7], 1996, 2056)
    long_term = {
        str(year): {
            "cpiu_growth_percent": float(rates[40][column]),
            "real_earnings_growth_percent": float(rates[31][column]),
            "cpiu_index_1982_1984_100": (
                100.0 * float(levels[13][level_columns[year]])
            ),
        }
        for year, column in columns.items()
    }
    ten = workbook_rows(
        raw["ten_year_economics"], "2. Calendar Year", selected={7, 53}
    )
    ten_columns = year_columns(ten[7], 2023, 2036)
    ten_year = {
        str(year): float(ten[53][column])
        for year, column in ten_columns.items()
    }
    workers = workbook_rows(
        raw["covered_earnings"],
        "1. Covered Workers",
        selected=set(range(9, 90)),
    )
    earnings = workbook_rows(
        raw["covered_earnings"],
        "2. Covered and Taxable Earnings",
        selected=set(range(9, 90)),
    )
    covered = {}
    for row in workers.values():
        year = row.get("A", "")
        if year.isdigit() and 2026 <= int(year) <= 2100:
            if year in covered:
                raise ValueError(f"duplicate covered-worker year {year}")
            covered[year] = {
                "male_workers_thousands": float(row["B"]),
                "female_workers_thousands": float(row["C"]),
                "total_workers_thousands": float(row["D"]),
            }
    for row in earnings.values():
        year = row.get("A", "")
        if year.isdigit() and year in covered:
            if "covered_earnings_trillions" in covered[year]:
                raise ValueError(f"duplicate covered-earnings year {year}")
            covered[year]["covered_earnings_trillions"] = float(row["B"])
    if set(covered) != {str(y) for y in range(2026, 2101)}:
        raise ValueError("covered earnings/workers must cover 2026..2100")
    if any(len(row) != 4 for row in covered.values()):
        raise ValueError("covered earnings column missing")
    return {
        "schema_version": "cbo2026_economics.v1",
        "long_term": long_term,
        "ten_year_cpiu_index_1982_1984_100": ten_year,
        "covered": covered,
        "awi_anchor": {
            "year": 2024,
            "amount": parse_awi_anchor(raw["actual_awi_anchor"]),
            "source": "tr2026_vi_g1_actual",
        },
        "source_keys": [
            "long_term_economics",
            "ten_year_economics",
            "covered_earnings",
            "actual_awi_anchor",
        ],
    }


def build_checks(demographics: Mapping, economics: Mapping) -> dict:
    """Compare q and m interpretations to every published LE summary."""
    rows = []
    errors: dict[str, list[float]] = {"q": [], "m": []}
    for year, summary in demographics["published_summary"].items():
        interpretations = {}
        for kind in ("q", "m"):
            by_sex = {}
            for sex in SEXES:
                rate = [
                    x / 1000.0 for x in demographics["mortality"][year][sex]
                ]
                q = (
                    rate
                    if kind == "q"
                    else [x / (1.0 + x / 2.0) for x in rate]
                )
                by_sex[sex] = {
                    str(age): life_expectancy(q, age, f0=0.5)
                    for age in (0, 65)
                }
            interpretations[kind] = {}
            for age, field in (
                (0, "life_expectancy_birth"),
                (65, "life_expectancy_65"),
            ):
                estimate = sum(by_sex[s][str(age)] for s in SEXES) / 2.0
                error = estimate - summary[field]
                errors[kind].append(abs(error))
                interpretations[kind][str(age)] = {
                    "recomputed": estimate,
                    "published": summary[field],
                    "error": error,
                }
        rows.append({"year": int(year), "interpretations": interpretations})
    q_max = max(errors["q"])
    m_min = min(errors["m"])
    tfr_errors = [
        abs(sum(demographics["asfr"][y]["all"]) / 1000.0 - row["tfr"])
        for y, row in demographics["published_summary"].items()
    ]
    all_q = [
        value / 1000.0
        for sexes in demographics["mortality"].values()
        for rates in sexes.values()
        for value in rates
    ]
    checks = [
        {"id": "q_range", "passed": all(0 <= x <= 1 for x in all_q)},
        {
            "id": "q119_closed",
            "passed": all(
                rates[-1] == 1000.0
                for sexes in demographics["mortality"].values()
                for rates in sexes.values()
            ),
        },
        {"id": "q_reproduces_published_le", "passed": q_max <= LE_TOLERANCE},
        {"id": "m_interpretation_rejected", "passed": m_min > LE_TOLERANCE},
        {
            "id": "asfr_sums_to_published_tfr",
            "passed": max(tfr_errors) <= TFR_TOLERANCE,
            "max_error": max(tfr_errors),
            "tolerance": TFR_TOLERANCE,
        },
        {
            "id": "covered_inputs_positive",
            "passed": all(
                value > 0
                for row in economics["covered"].values()
                for value in row.values()
            ),
        },
    ]
    return {
        "schema_version": "cbo2026_transcription_check.v1",
        "all_passed": all(check["passed"] for check in checks),
        "checks": checks,
        "mortality_interpretation": {
            "selected": "q",
            "tolerance_years": LE_TOLERANCE,
            "q_max_absolute_error_years": q_max,
            "m_min_absolute_error_years": m_min,
            "m_max_absolute_error_years": max(errors["m"]),
            "method": (
                "Rates/1000 as q versus central m converted with "
                "q=m/(1+m/2); uniform deaths including age 0 (f0=.5); "
                "published total LE reproduced by arithmetic mean of "
                "male/female period LE at birth and 65, every 2026-2099 year"
            ),
            "inference": (
                "Empirical interpretation, not an explicit CBO units "
                "definition. q reproduces every summary; m does not."
            ),
            "rows": rows,
        },
        "reparse": (
            "--check re-parses all pinned CSV/XLSX/HTML inputs and compares "
            "every JSON byte; source SHA-256 and available CDX digests verified"
        ),
    }


def compact_json(payload: Any) -> str:
    """Keep scalar arrays on one line, following the TR2008 data pattern."""

    def encode(value: Any, level: int) -> str:
        direct = json.dumps(value, sort_keys=True, ensure_ascii=False)
        if not isinstance(value, (dict, list)) or len(direct) <= 1400:
            return direct
        pad = "  " * (level + 1)
        if isinstance(value, dict):
            entries = [
                f"{pad}{json.dumps(key)}: {encode(value[key], level + 1)}"
                for key in sorted(value)
            ]
            opening, closing = "{", "}"
        else:
            entries = [pad + encode(item, level + 1) for item in value]
            opening, closing = "[", "]"
        return (
            opening
            + "\n"
            + ",\n".join(entries)
            + "\n"
            + "  " * level
            + closing
        )

    text = encode(payload, 0) + "\n"
    if json.loads(text) != payload:
        raise AssertionError("JSON encoder changed values")
    return text


def build_all(inputs: Path = DEFAULT_INPUTS) -> dict[str, str]:
    raw = {name: read_source(name, inputs) for name in SOURCES}
    archive = zipfile.ZipFile(io.BytesIO(raw["demographic_archive"]))
    for name in ("fertility", "mortality", "demographic_workbook"):
        member = SOURCES[name].relative_path.removeprefix("cbo/extracted/")
        if archive.read(member) != raw[name]:
            raise ValueError(
                f"{name} differs from verified demographic archive"
            )
    archive.close()
    demographics = build_demographics(raw)
    economics = build_economics(raw)
    checks = build_checks(demographics, economics)
    if not checks["all_passed"]:
        failures = [c["id"] for c in checks["checks"] if not c["passed"]]
        raise ValueError(f"CBO2026 checks failed: {failures}")
    sources = {}
    for name, spec in SOURCES.items():
        bundled_name = Path(spec.relative_path).name + ".gz"
        compressed = (
            deterministic_gzip(raw[name])
            if len(raw[name]) < 2_000_000
            else b""
        )
        # User requests <~2MB payloads; the repository hook is stricter.
        bundled = (
            Path(spec.relative_path).suffix in (".csv", ".xlsx", ".pdf")
            and len(raw[name]) < 2_000_000
            and len(compressed) < 500_000
        )
        sources[name] = {
            "captured_relative_path": spec.relative_path,
            "sha256": spec.sha256,
            "bytes": len(raw[name]),
            "original_url": spec.url,
            "locator": spec.locator,
            "wayback_timestamp": spec.timestamp,
            "cdx_sha1_b32": spec.cdx_sha1_b32,
            "computed_sha1_b32": sha1_b32(raw[name]),
            "cdx_digest_matches": (
                sha1_b32(raw[name]) == spec.cdx_sha1_b32
                if spec.cdx_sha1_b32
                else None
            ),
            "committed_file": "sources/" + bundled_name if bundled else None,
            "compressed_sha256": sha256(compressed) if bundled else None,
            "archive_source_key": (
                "demographic_archive"
                if name in ("fertility", "mortality", "demographic_workbook")
                else None
            ),
            "capture_date": "2026-10-01",
        }
    return {
        "cbo2026_demographics.json": compact_json(demographics),
        "cbo2026_economics.json": compact_json(economics),
        "transcription_check.json": compact_json(checks),
        "sources.json": compact_json(
            {
                "schema_version": "cbo2026_sources.v1",
                "sources": sources,
                "capture_method": (
                    "CBO raw Internet Archive id_ captures; original cbo.gov "
                    "served DataDome CAPTCHA; no live download attempted by "
                    "this builder. Source identities from captured research "
                    "summary; computed SHA-1/base32 matches every stated CDX digest."
                ),
                "compression": "gzip mtime=0; hashes refer to uncompressed bytes",
                "retention": (
                    "Raw sources retained only if payload <2MB and deterministic "
                    "gzip <500KB (repository precommit limit); otherwise URL/hash only"
                ),
            }
        ),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--inputs", type=Path, default=DEFAULT_INPUTS)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    outputs = build_all(args.inputs)
    if args.check:
        stale = [
            name
            for name, text in outputs.items()
            if not (OUT_DIR / name).is_file()
            or (OUT_DIR / name).read_text(encoding="utf-8") != text
        ]
        sources = json.loads(outputs["sources.json"])["sources"]
        for source in sources.values():
            if source["committed_file"]:
                path = OUT_DIR / source["committed_file"]
                if (
                    not path.is_file()
                    or sha256(path.read_bytes()) != source["compressed_sha256"]
                ):
                    stale.append(source["committed_file"])
        if stale:
            print(f"stale CBO2026 outputs: {stale}", file=sys.stderr)
            return 1
        print("CBO2026 outputs re-parsed and current; all input checks passed")
        return 0
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sources_dir = OUT_DIR / "sources"
    sources_dir.mkdir(exist_ok=True)
    source_metadata = json.loads(outputs["sources.json"])["sources"]
    for name, spec in source_metadata.items():
        if spec["committed_file"]:
            (OUT_DIR / spec["committed_file"]).write_bytes(
                deterministic_gzip(read_source(name, args.inputs))
            )
    for name, text in outputs.items():
        (OUT_DIR / name).write_text(text, encoding="utf-8")
        print(f"wrote {name}, SHA-256={sha256(text.encode())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
