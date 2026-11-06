"""Derive variable metadata from captured Census PDFs and storage schemas.

This script reads documentation only. It does not open any survey record file.
Run pdftotext -layout YEAR_dictionary.pdf YEAR_dictionary.txt first. Dictionary
page numbers are one-based PDF page indices, with the printed page retained.
Only dictionary entries with a recognized value list or numeric range count as
verified. Census schema labels and dtypes remain separate from printed labels.
"""

import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path

BASE = Path(__file__).resolve().parent
FIELDS = (
    "Universe Description|Description|Universe|Length|Status Flag|Record Level|"
    "Minimum|Maximum|Min|Max|Answer List|Possible Values|Value"
)
FIELD_RE = re.compile(rf"^\s*({FIELDS}):?\s*(.*)$")


def numeric(text):
    """Keep the source precision and remove currency presentation characters."""
    candidate = text.replace("$", "").replace("%", "").strip()
    match = re.fullmatch(r"(-?[\d,]+(?:\.\d+)?)(?:\.\s+[^\d].*)?", candidate)
    if match:
        number = match.group(1)
        if "," in number and not re.fullmatch(
            r"-?\d{1,3}(?:,\d{3})+(?:\.\d+)?", number
        ):
            return None
        return number.replace(",", "")
    return None


def parse_page(page, year):
    lines = page.splitlines()
    if year <= 2020:
        first = next((s.strip() for s in lines if s.strip()), "")
        head = re.fullmatch(
            r"(?:Variable\s+([A-Z][A-Z0-9_]*)|"
            r"([A-Z][A-Z0-9_]*)\s+Variable)",
            first,
        )
        if not head or "Description:" not in page:
            return None
        name = head.group(1) or head.group(2)
    else:
        head = re.search(r"^Name: ([A-Z][A-Z0-9_]*)\s*$", page, re.M)
        if not head:
            return None
        name = head.group(1)
    # Remove the footer before collecting multiline fields/value descriptions.
    body = re.split(r"^Printed On:", page, flags=re.M)[0]
    body_lines = body.splitlines()
    if year >= 2021:
        while body_lines and (
            not body_lines[-1].strip() or body_lines[-1].strip().isdigit()
        ):
            body_lines.pop()
    fields = {}
    active = None
    value_lines = []
    in_values = False
    for line in body_lines:
        match = FIELD_RE.match(line)
        if match:
            key, value = match.groups()
            if key in {"Answer List", "Possible Values"}:
                in_values = True
                active = None
            elif key == "Value":
                continue
            else:
                in_values = False
                fields[key] = value.strip()
                active = key
            continue
        if in_values:
            value_lines.append(line)
        elif active and line.strip():
            fields[active] += " " + line.strip()
    minimum = numeric(fields.get("Min", fields.get("Minimum", "")))
    maximum = numeric(fields.get("Max", fields.get("Maximum", "")))
    values = {"item": {}}
    current = None
    unparsed = []
    if minimum is not None and maximum is not None:
        # An inverted range is a misprint with an empty domain; it can
        # neither verify nor be repaired by guessing the intended bound.
        if Decimal(minimum) > Decimal(maximum):
            unparsed.append(f"Minimum {minimum} exceeds Maximum {maximum}")
        else:
            values["range"] = [
                {
                    "min": minimum,
                    "max": maximum,
                    "description": "Dictionary numeric range",
                }
            ]
    for line in value_lines:
        ranged = re.match(
            r"^\s*(-?\$?[\d,]+(?:\.\d+)?%?)\s*:\s*"
            r"(-?\$?[\d,]+(?:\.\d+)?%?)(?:\.\s+|\s+)?(.*)$",
            line,
        )
        if ranged:
            lower, upper, description = ranged.groups()
            lower, upper = numeric(lower), numeric(upper)
            if (
                lower is not None
                and upper is not None
                and Decimal(lower) > Decimal(upper)
            ):
                unparsed.append(line.strip())
                current = None
                continue
            if lower is not None and upper is not None:
                values.setdefault("range", []).append(
                    {
                        "min": lower,
                        "max": upper,
                        "description": description.strip()
                        or "Dictionary numeric range",
                    }
                )
                current = None
                continue
        # Codes may be comma-grouped ("9,999,999. Not possible to ...").
        pattern = (
            r"^\s*(-?[\d,]+(?:\.\d+)?)\s{2,}(\S.*)$"
            if year <= 2020
            else r"^\s*(-?[\d,]+(?:\.\d+)?)\.\s+(\S.*)$"
        )
        m = re.match(pattern, line)
        code = numeric(m.group(1)) if m else None
        if code is not None:
            current = code
            values["item"][current] = m.group(2).strip()
        elif re.match(r"^\s*-?\$?\d", line):
            unparsed.append(line.strip())
        elif current and line.strip():
            values["item"][current] += " " + line.strip()
    fields["Unparsed values"] = unparsed
    printed = re.search(r"Page\s+(\d+)\s*$", page)
    if year >= 2021:
        printed = re.search(r"\n\s*(\d+)\s*$", page)
    return name, fields, values, int(printed.group(1)) if printed else None


def derive(year):
    txt_path = BASE / f"{year}_dictionary.txt"
    schema_path = BASE / f"pu{year}_schema.json"
    schema = {v["name"]: v for v in json.loads(schema_path.read_text())}
    variables = {}
    rejected = []
    pages = txt_path.read_text().split("\f")
    for pdf_page, page in enumerate(pages, 1):
        parsed = parse_page(page, year)
        if not parsed:
            continue
        source_pages = [pdf_page]
        if year >= 2021:
            continuation = []
            next_index = pdf_page
            while next_index < len(pages):
                following = pages[next_index]
                first = next(
                    (s.strip() for s in following.splitlines() if s.strip()),
                    "",
                )
                if not first or first.startswith(
                    ("Topic:", "Subtopic", "Topic")
                ):
                    break
                if re.search(r"^Name:", following, re.M):
                    break
                if not re.match(r"^-?\$?\d", first):
                    break
                continuation.append(re.sub(r"\n\s*\d+\s*$", "", following))
                source_pages.append(next_index + 1)
                next_index += 1
            if continuation:
                without_footer = re.sub(r"\n\s*\d+\s*$", "", page)
                joined = without_footer + "\n" + "\n".join(continuation)
                joined += "\n" + str(parsed[3])
                parsed = parse_page(joined, year)
        elif (
            pdf_page < len(pages) and parse_page(pages[pdf_page], year) is None
        ):
            # 2018-2020 pages are not joined: an entry whose value list runs
            # onto a following page without a variable header is incomplete.
            first = next(
                (s.strip() for s in pages[pdf_page].splitlines() if s.strip()),
                "",
            )
            if re.match(r"^-?\$?\d", first):
                parsed[1]["Unparsed values"].append(
                    "continuation page not joined"
                )
        name, fields, values, printed_page = parsed
        if name not in schema:
            rejected.append({"name": name, "reason": "Not in storage schema"})
            continue
        stored = schema[name]
        valid = (
            bool(values["item"] or values.get("range"))
            and not fields["Unparsed values"]
        )
        if name in variables:
            raise ValueError(f"Duplicate dictionary entry: {year}/{name}")
        variables[name] = {
            "label": stored["label"],
            "dictionary_label": fields.get("Description", ""),
            "predicateType": {
                "integer": "int",
                "float": "float",
                "string": "string",
            }[stored["dtype"]],
            "storage_type": stored["dtype"],
            "values": values,
            "universe": fields.get("Universe", ""),
            "universe_description": fields.get("Universe Description", ""),
            "length": fields.get("Length", ""),
            "status_flag": fields.get("Status Flag", ""),
            "record_level": fields.get("Record Level", ""),
            "verified": valid,
            "unparsed_value_lines": fields["Unparsed values"],
            "dictionary_pdf_page": pdf_page,
            "dictionary_pdf_pages": source_pages,
            "dictionary_printed_page": printed_page,
        }
    document = {
        "derived_from": {
            "dictionary": f"{year}_dictionary.pdf",
            "dictionary_sha256": hashlib.sha256(
                (BASE / f"{year}_dictionary.pdf").read_bytes()
            ).hexdigest(),
            "text": txt_path.name,
            "text_sha256": hashlib.sha256(txt_path.read_bytes()).hexdigest(),
            "schema": schema_path.name,
            "schema_sha256": hashlib.sha256(
                schema_path.read_bytes()
            ).hexdigest(),
            "generator": Path(__file__).name,
        },
        "variables": variables,
        "not_parsed_schema_names": sorted(set(schema) - set(variables)),
        "rejected_dictionary_entries": rejected,
    }
    dest = BASE / f"{year}_dictionary_variables.json"
    dest.write_text(json.dumps(document, indent=2) + "\n")
    print(
        year,
        len(variables),
        "parsed;",
        sum(v["verified"] for v in variables.values()),
        "with values;",
        len(document["not_parsed_schema_names"]),
        "schema names absent from PDF",
    )


def refresh_derived_manifest():
    """Re-pin every file the derived manifest lists, this script included."""
    path = BASE / "derived_manifest.json"
    entries = json.loads(path.read_text())
    for entry in entries:
        payload = (BASE / entry["path"]).read_bytes()
        entry["bytes"] = len(payload)
        entry["sha256"] = hashlib.sha256(payload).hexdigest()
    path.write_text(json.dumps(entries, indent=2) + "\n")


if __name__ == "__main__":
    for release in range(2018, 2026):
        if (BASE / f"{release}_dictionary.txt").exists():
            derive(release)
    refresh_derived_manifest()
