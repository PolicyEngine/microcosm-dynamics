"""Capture the parameters Track U's income concept reads (plan item U3).

Two captures, each written to ``data/external`` and pinned by SHA-256 in
:mod:`populace_dynamics.estimates.adjusted_poverty`:

* ``--ssi`` writes ``track_u_ssi_parameters.json``: the federal SSI
  benefit rate (individual and couple, monthly) in force on January 1 of
  each income year 2004-2012, the $20 general and $65 earned income
  exclusions, the share of remaining earned income excluded, and the
  individual and couple resource limits.  The values come from the
  policyengine-us parameter files (``gov/ssa/ssi``) of the checkout given
  by ``--pe-us-dir`` (default ``POPULACE_DYNAMICS_PE_US_DIR`` or
  ``~/PolicyEngine/policyengine-us``); the capture records each file's
  SHA-256, the checkout revision and each file's cited reference.  These
  are assumptions for the SSI response rule, not comparator values.
* ``--census-dir DIR`` writes ``census_poverty_thresholds_2004_2012.json``
  from the Census Bureau's threshold workbooks for income years 2004-2012
  staged in ``DIR`` as ``thresh04.xlsx`` ... ``thresh12.xlsx`` (the file
  names the Census historical thresholds page lists under
  ``https://www2.census.gov/programs-surveys/cps/tables/time-series/
  historical-poverty-thresholds/``).  The nine workbooks were staged on
  2026-09-24 under cos decision d194 and are committed in
  ``data/external/census_poverty_thresholds/``; each one's SHA-256 is
  pinned in :data:`CENSUS_WORKBOOK_SHA256` and checked before it is
  parsed.  The parser was written against the real layout (inspected cell
  by cell in every workbook, ``thresh03.xlsx`` included), locates rows
  and columns by their printed labels and refuses any other layout, and
  checks every year's values within the year and against the previous
  year (:func:`parse_threshold_rows`, :func:`check_matrix_moves_together`).
  Re-running it on the committed workbooks reproduces the committed
  capture byte for byte (``tests/track_u/test_census_threshold_capture.py``).

Usage::

    python scripts/capture_track_u_parameters.py --ssi [--pe-us-dir DIR]
    python scripts/capture_track_u_parameters.py --census-dir DIR
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from populace_dynamics.estimates import adjusted_poverty  # noqa: E402

#: Income years the exact-age primary and the pooled row observe.
YEARS: tuple[int, ...] = tuple(range(2004, 2013))
_PE_US_ENV = "POPULACE_DYNAMICS_PE_US_DIR"
_PE_US_DEFAULT = Path("~/PolicyEngine/policyengine-us").expanduser()
_SSI_ROOT = Path("policyengine_us/parameters/gov/ssa/ssi")
SSI_FILES: dict[str, Path] = {
    "fbr_individual": _SSI_ROOT / "amount" / "individual.yaml",
    "fbr_couple": _SSI_ROOT / "amount" / "couple.yaml",
    "general_income_exclusion": _SSI_ROOT
    / "income"
    / "exclusions"
    / "general.yaml",
    "earned_income_exclusion": _SSI_ROOT
    / "income"
    / "exclusions"
    / "earned.yaml",
    "earned_income_share_excluded": _SSI_ROOT
    / "income"
    / "exclusions"
    / "earned_share.yaml",
    "resource_limit_individual": _SSI_ROOT
    / "eligibility"
    / "resources"
    / "limit"
    / "individual.yaml",
    "resource_limit_couple": _SSI_ROOT
    / "eligibility"
    / "resources"
    / "limit"
    / "couple.yaml",
}
CENSUS_URL_BASE = (
    "https://www2.census.gov/programs-surveys/cps/tables/time-series/"
    "historical-poverty-thresholds/"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def resolve_pe_us(pe_us_dir: Path | None) -> Path:
    if pe_us_dir is not None:
        return Path(pe_us_dir).expanduser()
    env = os.environ.get(_PE_US_ENV)
    return Path(env).expanduser() if env else _PE_US_DEFAULT


def _in_force(values: dict[Any, Any], year: int) -> float:
    """The value of a dated parameter in force on January 1 of ``year``."""

    dated = sorted(
        (dt.date.fromisoformat(str(key)), float(value))
        for key, value in values.items()
    )
    start = dt.date(year, 1, 1)
    eligible = [value for date, value in dated if date <= start]
    if not eligible:
        raise ValueError(f"no value in force on {start}")
    return eligible[-1]


def build_ssi_capture(pe_us_dir: Path | None = None) -> dict[str, Any]:
    root = resolve_pe_us(pe_us_dir).resolve()
    documents: dict[str, dict[str, Any]] = {}
    hashes: dict[str, str] = {}
    references: dict[str, list[dict[str, str]]] = {}
    for name, relative in SSI_FILES.items():
        path = root / relative
        if not path.is_file():
            raise FileNotFoundError(f"policyengine-us file missing: {path}")
        hashes[str(relative)] = _sha256(path)
        documents[name] = yaml.safe_load(path.read_text())
        references[name] = [
            {"title": ref.get("title", ""), "href": ref.get("href", "")}
            for ref in documents[name].get("metadata", {}).get("reference", [])
        ]
    try:
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        revision = "unknown"

    def year_map(name: str) -> dict[str, float]:
        return {
            str(year): _in_force(documents[name]["values"], year)
            for year in YEARS
        }

    def constant(name: str) -> float:
        values = {_in_force(documents[name]["values"], year) for year in YEARS}
        if len(values) != 1:
            raise ValueError(f"{name} changes within {YEARS[0]}-{YEARS[-1]}")
        return values.pop()

    return {
        "schema_version": adjusted_poverty.SSI_SCHEMA_VERSION,
        "description": (
            "Federal SSI parameters for the Track U SSI response rules "
            "(exercise 2; Python income concept, not Axiom): the federal "
            "benefit rate in force on January 1 of each income year, the "
            "general and earned income exclusions and the resource limits"
        ),
        "years": [YEARS[0], YEARS[-1]],
        "source": {
            "policyengine_us_revision": revision,
            "policyengine_us_files_sha256": hashes,
            "references": references,
            "rule": "value in force on January 1 of the income year",
            "generated_by": "scripts/capture_track_u_parameters.py --ssi",
        },
        "federal_benefit_rate_monthly": {
            "individual": year_map("fbr_individual"),
            "couple": year_map("fbr_couple"),
        },
        "general_income_exclusion_monthly": constant(
            "general_income_exclusion"
        ),
        "earned_income_exclusion_monthly": constant("earned_income_exclusion"),
        "earned_income_share_excluded": constant(
            "earned_income_share_excluded"
        ),
        "resource_limit": {
            "individual": constant("resource_limit_individual"),
            "couple": constant("resource_limit_couple"),
        },
    }


# ---------------------------------------------------------------------------
# Census thresholds
# ---------------------------------------------------------------------------
#: The committed copies of the Census workbooks the capture reads.
CENSUS_WORKBOOK_DIR = ROOT / "data" / "external" / "census_poverty_thresholds"
#: SHA-256 of each Census workbook the capture reads: the files staged on
#: 2026-09-24 under cos decision d194 from :data:`CENSUS_URL_BASE` and
#: committed in :data:`CENSUS_WORKBOOK_DIR`.  A workbook with other bytes
#: is refused before it is parsed.
CENSUS_WORKBOOK_SHA256: dict[str, str] = {
    "thresh04.xlsx": (
        "9cae1bcff6c3ff80faedaa11c28068d9a640f10f5a7679e3cfb0430779bbb5b8"
    ),
    "thresh05.xlsx": (
        "9c626a9757232d500167349c9c47dc254a5f1ac34c6ba3468acd1a624df52888"
    ),
    "thresh06.xlsx": (
        "7ace9e1c3990348b252698da9026aea082c7a52bcc073c0315721b01b9c09a45"
    ),
    "thresh07.xlsx": (
        "1209903a9c1071f9a76ee5a50dc9eb83faa93024134a72e73a3cdc6b558a4327"
    ),
    "thresh08.xlsx": (
        "7e7222d431411aa82734d9580cc8f6bce246d1cd330e688a8306748bc46f09ae"
    ),
    "thresh09.xlsx": (
        "7f997506d189bb1899bab1255ae5e991a384ffaf8d72d63ca4497d1912e1175e"
    ),
    "thresh10.xlsx": (
        "75360b3d852669c76f77df20d2292d1abe1d90e1b58a9d3e0611bb37570a45b9"
    ),
    "thresh11.xlsx": (
        "ec2758efc4b6797b171fbe4cda135e5f08396734bdc2d606f0b990219f42bab6"
    ),
    "thresh12.xlsx": (
        "26da2dc48de0a0799905c15aa6634d5b942dd57b801bdaf9564eacf4cc365f36"
    ),
}

#: The caption every real workbook prints in A1, above the title (lower
#: case, whitespace collapsed).
_CAPTION = (
    "table with row headings in column a and column headings in rows 5 to 6."
)
#: The table title, matched in full (lower case, whitespace collapsed).
_TITLE = re.compile(
    r"poverty thresholds for (\d{4}) by size of family and number of "
    r"related children under 18 years"
)
_UNITS = "(in dollars)"
_SOURCE = re.compile(r"source: u\.s\. census bureau, (\d{4})\.?")
#: The note's first sentence (the 2009 note adds two more).
_NOTE = re.compile(
    r"note: the source of the weighted average thresholds is the (\d{4}) "
    r"current population survey annual social and economic supplement "
    r"\(cps asec\)\."
)
#: The only text the note may carry after its first sentence: the two
#: sentences of the 2009 note (a year whose average annual CPI-U fell),
#: with ``{year}`` the table's year and ``{previous}`` the year before.
_NOTE_CPI_FALL = (
    "the poverty thresholds are updated each year using the change in the "
    "average annual consumer price index for all urban consumers (cpi-u). "
    "since the average annual cpi-u for {year} was lower than the average "
    "annual cpi-u for {previous}, poverty thresholds for {year} are "
    "slightly lower than the corresponding thresholds for {previous}."
)
#: The table's labelled rows in printed order: (label, key, number of
#: related-children columns the row fills).  ``one_all`` and ``two_all``
#: are the size-1 and size-2 rows over both age groups, which print a
#: weighted average only.
_TABLE_ROWS: tuple[tuple[str, str, int], ...] = (
    ("one person (unrelated individual)", "one_all", 0),
    ("under 65 years", "one_under_65", 1),
    ("65 years and over", "one_65_plus", 1),
    ("two people", "two_all", 0),
    ("householder under 65 years", "two_under_65", 2),
    ("householder 65 years and over", "two_65_plus", 2),
    ("three people", "three", 3),
    ("four people", "four", 4),
    ("five people", "five", 5),
    ("six people", "six", 6),
    ("seven people", "seven", 7),
    ("eight people", "eight", 8),
    ("nine people or more", "nine_plus", 9),
)
_ALL_AGES = {"one_all": "one", "two_all": "two"}
#: The related-children column headers, in printed order (0 ... 8).
_CHILD_HEADERS: tuple[str, ...] = (
    "none",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight or more",
)
#: Columns: row label, weighted average, then the nine children columns.
_LABEL_COL, _WEIGHTED_COL, _FIRST_CHILD_COL = 0, 1, 2
_TABLE_WIDTH = _FIRST_CHILD_COL + len(_CHILD_HEADERS)
#: Largest distance, in dollars, of a matrix cell from the previous
#: year's cell times the year's common ratio (whole-dollar rounding of
#: both years moves a cell by at most about $1).
_CROSS_YEAR_TOLERANCE = 2.0


def _text(value: Any) -> str:
    return " ".join(str(value).split()).lower()


def _label(value: Any) -> str:
    """A printed row or column label without its dot leaders or colon."""

    return re.sub(r"[\s.:…]+$", "", _text("" if value is None else value))


def _blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _dollars(value: Any, where: str) -> int:
    """A threshold cell: a positive whole number of dollars, or refused."""

    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{where}: {value!r} is not a number")
    if not float(value).is_integer() or value <= 0:
        raise ValueError(f"{where}: {value!r} is not a positive whole dollar")
    return int(value)


def parse_threshold_rows(rows: list[list[Any]], year: int) -> dict[str, Any]:
    """Parse one year's Census threshold table from its cell rows.

    The layout is the one every ``thresh03.xlsx`` ... ``thresh12.xlsx``
    shares (checked on the real workbooks, 2026-09-24): above the header
    exactly three lines in column A, the caption :data:`_CAPTION`, the
    title and "(In dollars)"; a header row "Size of family unit" |
    "Weighted average thresholds" | "Related children under 18 years"
    over a row of the nine children headers "None" ... "Eight or more";
    the thirteen labelled rows of :data:`_TABLE_ROWS` in order; then
    "Source: U.S. Census Bureau, <year + 1>." and a note naming the
    <year + 1> CPS ASEC, which may add only the two CPI-U sentences of
    :data:`_NOTE_CPI_FALL` (the 2009 note).  Everything else must be
    blank (whitespace-only cells count as blank).

    Refuses a table whose title does not name ``year``, whose source or
    note does not name ``year + 1``, with other text above the header or
    in the note, whose header or row labels differ, whose threshold cells
    are not positive whole numbers or fill other children columns than
    their row allows, with a value anywhere else, or whose values fail
    :func:`_validate_year`.

    Returns ``{"weighted_average": {row_key: dollars}, "all_ages":
    {"one": dollars, "two": dollars}, "matrix": {row_key: {children:
    dollars}}, "title": str, "source_line": str, "cps_asec_year": int}``.
    """

    width = max([_TABLE_WIDTH, *(len(row) for row in rows)])
    grid = [list(row) + [None] * (width - len(row)) for row in rows]

    def refuse(message: str) -> ValueError:
        return ValueError(f"{year}: {message}")

    titles = [
        (i, cell, match)
        for i, row in enumerate(grid)
        for cell in row
        if isinstance(cell, str) and (match := _TITLE.fullmatch(_text(cell)))
    ]
    if len(titles) != 1:
        raise refuse(
            "expected one 'Poverty Thresholds for <year> by Size of Family "
            "and Number of Related Children Under 18 Years' title, found "
            f"{len(titles)}"
        )
    title_row, title_cell, title_match = titles[0]
    if int(title_match.group(1)) != year:
        raise refuse(f"the title names {title_match.group(1)}")
    header = [
        i
        for i, row in enumerate(grid)
        if _label(row[_LABEL_COL]) == "size of family unit"
    ]
    if len(header) != 1:
        raise refuse("expected one 'Size of family unit' header row")
    h = header[0]
    if title_row >= h:
        raise refuse("the title is not above the header")
    above = [
        (column, cell)
        for row in grid[:h]
        for column, cell in enumerate(row)
        if not _blank(cell)
    ]
    if any(not isinstance(cell, str) for _, cell in above):
        raise refuse("a value above the header row")
    if any(column != _LABEL_COL for column, _ in above):
        raise refuse("text above the header outside column A")
    # Exactly the caption, the title and the units line, in that order
    # (each is a cell of its own in column A): no other text, formula or
    # line above the header.
    lines = [_text(cell) for _, cell in above]
    if (
        len(lines) != 3
        or lines[0] != _CAPTION
        or _TITLE.fullmatch(lines[1]) is None
        or lines[2] != _UNITS
    ):
        raise refuse(
            "the text above the header is not exactly the caption, the "
            "title and '(In dollars)', in that order"
        )
    top = grid[h]
    if _label(top[_WEIGHTED_COL]) != "weighted average thresholds":
        raise refuse("column B of the header is not 'Weighted average'")
    if _label(top[_FIRST_CHILD_COL]) != "related children under 18 years":
        raise refuse("column C of the header is not 'Related children'")
    if any(not _blank(cell) for cell in top[_FIRST_CHILD_COL + 1 :]):
        raise refuse("unexpected cells in the header row")
    if h + 1 >= len(grid):
        raise refuse("no children header row")
    children = grid[h + 1]
    printed = [
        _label(cell) for cell in children[_FIRST_CHILD_COL:_TABLE_WIDTH]
    ]
    if (
        printed != list(_CHILD_HEADERS)
        or not all(_blank(cell) for cell in children[:_FIRST_CHILD_COL])
        or not all(_blank(cell) for cell in children[_TABLE_WIDTH:])
    ):
        raise refuse(f"children headers {printed} != {list(_CHILD_HEADERS)}")
    sources = [
        i
        for i, row in enumerate(grid)
        if isinstance(row[_LABEL_COL], str)
        and _text(row[_LABEL_COL]).startswith("source:")
    ]
    if len(sources) != 1 or sources[0] <= h + 1:
        raise refuse("expected one 'Source:' line below the table")
    s = sources[0]
    source_line = " ".join(str(grid[s][_LABEL_COL]).split())
    source_match = _SOURCE.fullmatch(_text(source_line))
    if source_match is None or int(source_match.group(1)) != year + 1:
        raise refuse(
            f"source line {source_line!r} is not 'Source: U.S. Census "
            f"Bureau, {year + 1}.'"
        )
    note = grid[s + 1][_LABEL_COL] if s + 1 < len(grid) else None
    note_match = None if _blank(note) else _NOTE.match(_text(note))
    if note_match is None or int(note_match.group(1)) != year + 1:
        raise refuse(f"the note does not name the {year + 1} CPS ASEC")
    tail = _text(note)[note_match.end() :].strip()
    if tail not in ("", _NOTE_CPI_FALL.format(year=year, previous=year - 1)):
        raise refuse(
            "the note says more than the CPS ASEC sentence (and, for a "
            f"year whose CPI-U fell, the two CPI-U sentences): {tail!r}"
        )
    trailer = [grid[s][_LABEL_COL + 1 :], grid[s + 1][_LABEL_COL + 1 :]]
    trailer.extend(grid[s + 2 :])
    if any(not _blank(cell) for row in trailer for cell in row):
        raise refuse("a value beside or below the source and note")
    labelled = []
    for row in grid[h + 2 : s]:
        if _blank(row[_LABEL_COL]):
            if any(not _blank(cell) for cell in row):
                raise refuse("a value in an unlabelled row")
            continue
        labelled.append(row)
    labels = [_label(row[_LABEL_COL]) for row in labelled]
    expected = [label for label, _, _ in _TABLE_ROWS]
    if labels != expected:
        raise refuse(f"row labels {labels} != {expected}")
    weighted: dict[str, int] = {}
    all_ages: dict[str, int] = {}
    matrix: dict[str, dict[int, int]] = {}
    for (label, key, n_columns), row in zip(
        _TABLE_ROWS, labelled, strict=True
    ):
        where = f"{year} row {label!r}"
        value = _dollars(row[_WEIGHTED_COL], f"{where} weighted average")
        cells = {
            k: _dollars(cell, f"{where} column {_CHILD_HEADERS[k]!r}")
            for k, cell in enumerate(row[_FIRST_CHILD_COL:_TABLE_WIDTH])
            if not _blank(cell)
        }
        if sorted(cells) != list(range(n_columns)):
            raise refuse(
                f"row {label!r} fills children columns {sorted(cells)}, "
                f"expected {list(range(n_columns))}"
            )
        if any(not _blank(cell) for cell in row[_TABLE_WIDTH:]):
            raise refuse(f"row {label!r} has a value beyond the table")
        if key in _ALL_AGES:
            all_ages[_ALL_AGES[key]] = value
        else:
            weighted[key] = value
            matrix[key] = cells
    _validate_year(year, weighted, all_ages, matrix)
    return {
        "weighted_average": weighted,
        "all_ages": all_ages,
        "matrix": matrix,
        "title": " ".join(str(title_cell).split()),
        "source_line": source_line,
        "cps_asec_year": int(note_match.group(1)),
    }


def _validate_year(
    year: int,
    weighted: dict[str, int],
    all_ages: dict[str, int],
    matrix: dict[str, dict[int, int]],
) -> None:
    """Relations every Census threshold table satisfies, or refused.

    The 65-and-over rows lie below the under-65 rows (sizes 1 and 2); the
    size-1 and size-2 weighted averages over both ages lie between their
    two age rows; the weighted averages rise with size from two persons;
    and each row's weighted average lies within the range of that row's
    matrix cells (a weighted average of them), which for sizes 1 ties the
    two columns together.
    """

    if set(weighted) != set(adjusted_poverty.THRESHOLD_ROW_KEYS):
        raise ValueError(f"{year}: rows {sorted(weighted)}")
    for size in ("one", "two"):
        young, old = weighted[f"{size}_under_65"], weighted[f"{size}_65_plus"]
        if not old < young:
            raise ValueError(
                f"{year}: 65-and-over threshold not below under-65 ({size})"
            )
        if not old <= all_ages[size] <= young:
            raise ValueError(
                f"{year}: the {size}-person weighted average over both ages "
                "is not between its two age rows"
            )
    larger = ["three", "four", "five", "six", "seven", "eight", "nine_plus"]
    chain = [weighted["two_under_65"], *(weighted[key] for key in larger)]
    if any(b <= a for a, b in zip(chain, chain[1:], strict=False)):
        raise ValueError(f"{year}: weighted averages not increasing in size")
    for key, value in weighted.items():
        cells = matrix[key].values()
        if not min(cells) <= value <= max(cells):
            raise ValueError(
                f"{year}: row {key} weighted average {value} outside its "
                f"matrix cells {min(cells)}-{max(cells)}"
            )


def check_matrix_moves_together(
    earlier: dict[str, dict[int, int]],
    later: dict[str, dict[int, int]],
    year: int,
) -> float:
    """Refuse a year whose matrix cells do not all move by one ratio.

    The 2009 workbook's note says the thresholds are updated each year by
    the change in the average annual CPI-U, and every cell of the real
    2003-2012 workbooks moves year on year by one ratio to within about
    $1 of whole-dollar rounding; a cell read from the wrong row or column
    moves by far more.  Returns the median ratio of ``year`` to
    ``year - 1``.
    """

    pairs = [
        (earlier[key][k], later[key][k])
        for key in adjusted_poverty.THRESHOLD_ROW_KEYS
        for k in later[key]
    ]
    ratios = sorted(new / old for old, new in pairs)
    middle = len(ratios) // 2
    ratio = (
        ratios[middle]
        if len(ratios) % 2
        else 0.5 * (ratios[middle - 1] + ratios[middle])
    )
    worst = max(abs(new - ratio * old) for old, new in pairs)
    if worst > _CROSS_YEAR_TOLERANCE:
        raise ValueError(
            f"{year}: a matrix cell is ${worst:.2f} from {year - 1}'s times "
            f"the common ratio {ratio:.6f} (tolerance "
            f"${_CROSS_YEAR_TOLERANCE:.0f})"
        )
    return ratio


def read_workbook_rows(path: Path) -> tuple[str, list[list[Any]]]:
    """The one worksheet's title and cell values (formulas as text)."""

    import openpyxl

    workbook = openpyxl.load_workbook(path, data_only=False)
    try:
        if len(workbook.worksheets) != 1:
            raise ValueError(
                f"{path.name}: {len(workbook.worksheets)} worksheets, "
                "expected 1"
            )
        sheet = workbook.worksheets[0]
        rows = [list(row) for row in sheet.iter_rows(values_only=True)]
        return sheet.title, rows
    finally:
        workbook.close()


def build_threshold_capture(
    census_dir: Path,
    *,
    expected_sha256: dict[str, str] | None = CENSUS_WORKBOOK_SHA256,
) -> dict[str, Any]:
    """Parse the nine workbooks in ``census_dir`` into the capture.

    Each workbook's SHA-256 must equal ``expected_sha256`` (the pinned
    Census files) before it is parsed; ``None`` skips the pin and is for
    tests on INVENTED workbooks only (the command line always pins).
    """

    census_dir = Path(census_dir)
    weighted: dict[str, Any] = {}
    all_ages: dict[str, Any] = {}
    matrix: dict[str, Any] = {}
    sources: dict[str, Any] = {}
    ratios: dict[str, float] = {}
    previous: dict[str, dict[int, int]] | None = None
    for year in YEARS:
        name = f"thresh{year % 100:02d}.xlsx"
        path = census_dir / name
        if not path.is_file():
            raise FileNotFoundError(f"missing Census file {path}")
        digest = _sha256(path)
        if expected_sha256 is not None and digest != expected_sha256.get(name):
            raise ValueError(
                f"{path} sha256 {digest} != pinned "
                f"{expected_sha256.get(name)}: not the captured Census file"
            )
        sheet, rows = read_workbook_rows(path)
        parsed = parse_threshold_rows(rows, year)
        if previous is not None:
            ratios[f"{year - 1}-{year}"] = round(
                check_matrix_moves_together(previous, parsed["matrix"], year),
                6,
            )
        previous = parsed["matrix"]
        weighted[str(year)] = parsed["weighted_average"]
        all_ages[str(year)] = parsed["all_ages"]
        matrix[str(year)] = {
            key: {str(k): v for k, v in cells.items()}
            for key, cells in parsed["matrix"].items()
        }
        sources[str(year)] = {
            "file": name,
            "url": CENSUS_URL_BASE + name,
            "sha256": digest,
            "bytes": path.stat().st_size,
            "sheet": sheet,
            "title": parsed["title"],
            "source_line": parsed["source_line"],
            "cps_asec_year": parsed["cps_asec_year"],
        }
    return {
        "schema_version": adjusted_poverty.THRESHOLDS_SCHEMA_VERSION,
        "description": (
            "U.S. Census Bureau poverty thresholds for income years "
            "2004-2012, as printed in the Census historical threshold "
            "workbooks: weighted averages by family size (with the "
            "under-65 and 65-and-over rows for one and two persons), the "
            "size-1 and size-2 weighted averages over both ages, and the "
            "size-by-related-children matrix, in dollars"
        ),
        "years": [YEARS[0], YEARS[-1]],
        "sources": sources,
        "generated_by": "scripts/capture_track_u_parameters.py --census-dir",
        "checks": {
            "workbook_sha256": (
                "pinned (CENSUS_WORKBOOK_SHA256)"
                if expected_sha256 is not None
                else "not pinned (INVENTED workbooks)"
            ),
            "layout": (
                "title names the year, source and note name the next "
                "year's CPS ASEC, header and thirteen row labels as "
                "printed, whole-dollar cells in the expected columns, "
                "nothing else in the sheet"
            ),
            "within_year": (
                "65-and-over below under-65 (sizes 1, 2); size-1 and "
                "size-2 all-ages averages between their age rows; "
                "weighted averages rise with size from two; each weighted "
                "average within its row's matrix cells"
            ),
            "cross_year": (
                "every matrix cell moves by one ratio from the previous "
                f"year within ${_CROSS_YEAR_TOLERANCE:.0f}"
            ),
            "matrix_ratio_by_year_pair": ratios,
        },
        "weighted_average": weighted,
        "weighted_average_all_ages": all_ages,
        "matrix": matrix,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ssi", action="store_true")
    parser.add_argument("--pe-us-dir", type=Path, default=None)
    parser.add_argument("--census-dir", type=Path, default=None)
    parser.add_argument(
        "--ssi-output", type=Path, default=adjusted_poverty.SSI_PARAMETERS_PATH
    )
    parser.add_argument(
        "--census-output", type=Path, default=adjusted_poverty.THRESHOLDS_PATH
    )
    args = parser.parse_args(argv)
    if not args.ssi and args.census_dir is None:
        parser.error("pass --ssi and/or --census-dir")
    if args.ssi:
        capture = build_ssi_capture(args.pe_us_dir)
        args.ssi_output.write_text(
            json.dumps(capture, indent=2) + "\n", encoding="utf-8"
        )
        print(args.ssi_output, _sha256(args.ssi_output))
    if args.census_dir is not None:
        capture = build_threshold_capture(args.census_dir)
        args.census_output.write_text(
            json.dumps(capture, indent=2) + "\n", encoding="utf-8"
        )
        print(args.census_output, _sha256(args.census_output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
