"""Regenerate the embedded SIPP registry from committed documentation only.

No survey record is opened. For each release 2018-2025 and each concept in
``concept_selection.json`` this script decides admission and writes the
generated tables of ``sipp_income_registry.py`` plus four evidence records:

* ``refused_concepts.json``: every refused concept-year and its reason;
* ``label_checks.json``: 2018-2021 storage-schema labels that disagree with
  the release dictionary (the verifying source), and release metadata a
  Census user note contradicts, with the ruling applied;
* ``domain_checks.json``: 2022-2025 concepts whose variable-API domain and
  same-release dictionary domain differ, and the domain the reader admits;
* ``release_changes.json``: every change in an admitted concept's name,
  dictionary label, universe, codes, missing codes, storage type or
  admission between consecutive releases (the explicit crosswalk).

Sources per release. 2022-2025: the variable API is primary (label, type,
codes); the release dictionary is a second domain that every value must
also satisfy, except the API's own missing-value sentinels. 2018-2021 have
no API: the release dictionary verifies label and domain, the Census
storage schema the type. Universes come from each release's dictionary.
A domain is never borrowed from another release, a label conflict without
a ruling in ``source_rulings.json`` stops the build, and an open ruling
refuses the concept.

Run with the clone's Python from any working directory.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from decimal import Decimal
from pathlib import Path
from pprint import pformat

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[2]
REGISTRY = REPO / "src/populace_dynamics/data/sipp_income_registry.py"
YEARS = range(2018, 2026)
API_YEARS = range(2022, 2026)
#: Labels the variable API gives its missing-value codes.
SENTINEL_LABELS = frozenset({"NA-Missing", "NA or Missing"})
#: Census storage schemas cut labels at 255-256 characters.
SCHEMA_LABEL_LIMIT = 255
#: Structural keys: user notes that name them describe other variables.
NOTE_EXCLUDED = frozenset({"SSUID", "PNUM", "MONTHCODE", "SPANEL", "SWAVE"})


def read_json(filename):
    return json.loads((BASE / filename).read_text())


def label_key(text: str) -> str:
    """Compare labels ignoring case, Unicode forms and punctuation only.

    pdftotext drops some characters (the ``*`` of the 2021-2025 business
    formulas) and the dictionaries and schemas differ in quotes, ellipses
    and ligatures; words and numbers must still match exactly.
    """
    folded = unicodedata.normalize("NFKC", text).casefold()
    return "".join(re.findall(r"[a-z0-9]+", folded))


def label_agreement(schema: str, dictionary: str) -> str:
    """Classify a storage-schema label against the dictionary label."""
    if label_key(schema) == label_key(dictionary):
        return "equal"
    if len(schema) >= SCHEMA_LABEL_LIMIT and label_key(dictionary).startswith(
        label_key(schema)
    ):
        return "schema_truncated"
    return "conflict"


def suppressed(*labels: str) -> bool:
    return any(label.strip() == "Suppressed" for label in labels if label)


def number(text: str) -> Decimal:
    return Decimal(text)


def canonical(value: Decimal) -> str:
    """Decimal text without exponent or trailing zeros."""
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def intervals(items, ranges, *, integer: bool):
    """Merged closed intervals for codes and ranges (sentinels excluded)."""
    spans = sorted(
        [(number(code), number(code)) for code, label in items]
        + [(number(low), number(high)) for low, high in ranges]
    )
    merged: list[list[Decimal]] = []
    step = Decimal(1) if integer else Decimal(0)
    for low, high in spans:
        if merged and low <= merged[-1][1] + step:
            merged[-1][1] = max(merged[-1][1], high)
        else:
            merged.append([low, high])
    return [(low, high) for low, high in merged]


def intersect(left, right):
    out, i, j = [], 0, 0
    while i < len(left) and j < len(right):
        low = max(left[i][0], right[j][0])
        high = min(left[i][1], right[j][1])
        if low <= high:
            out.append((low, high))
        if left[i][1] < right[j][1]:
            i += 1
        else:
            j += 1
    return out


def text_intervals(spans):
    return [[canonical(low), canonical(high)] for low, high in spans]


def split_items(meta):
    """(non-sentinel items, sentinel items) of one metadata entry."""
    items = sorted(meta.get("values", {}).get("item", {}).items())
    return (
        tuple(
            (code, label)
            for code, label in items
            if label not in SENTINEL_LABELS
        ),
        tuple(
            (code, label) for code, label in items if label in SENTINEL_LABELS
        ),
    )


def meta_ranges(meta):
    return tuple(
        (x["min"], x["max"], x.get("description", ""))
        for x in meta.get("values", {}).get("range", [])
    )


def user_note_index():
    """{(release, variable): [note index]} and the note table."""
    notes, table, index = {}, [], {}
    for entry in read_json("user_notes_manifest.json"):
        if entry.get("kind") != "note" or not entry.get("stored_as"):
            continue
        key = (entry["title"], entry["url"], entry["stored_as"])
        if key not in index:
            index[key] = len(table)
            table.append(key)
        for variable in entry["variables"]:
            if variable in NOTE_EXCLUDED:
                continue
            notes.setdefault((entry["release"], variable), []).append(
                index[key]
            )
    return notes, tuple(table)


def build_tables():
    selected = read_json("concept_selection.json")
    rulings = read_json("source_rulings.json")
    concepts = {
        k: (v["ownership_level"], v["period"])
        for k, v in selected["concepts"].items()
    }
    note_map, note_table = user_note_index()
    releases, replicates, refused = {}, {}, {}
    label_checks, domain_checks, corrections = [], [], {}
    family_checks = []
    definitions, indices = [], {}
    sources = {
        "concept_selection.json",
        "source_rulings.json",
        "user_notes_manifest.json",
    }
    sources.update(path for _, _, path in note_table)
    observed_label_conflicts = set()
    effective = {}

    def intern(value):
        if value not in indices:
            indices[value] = len(definitions)
            definitions.append(value)
        return indices[value]

    for year in YEARS:
        dictionary = read_json(f"{year}_dictionary_variables.json")[
            "variables"
        ]
        api = (
            read_json(f"{year}_variables.json")["variables"]
            if year in API_YEARS
            else {}
        )
        schema = {v["name"]: v for v in read_json(f"pu{year}_schema.json")}
        sources.update(
            (
                f"{year}_dictionary_variables.json",
                f"{year}_dictionary.pdf",
                f"{year}_dictionary.txt",
                f"pu{year}_schema.json",
                f"{year}_python_input_example.py.txt",
            )
        )
        if year in API_YEARS:
            sources.add(f"{year}_variables.json")
        releases[year], refused[str(year)] = {}, {}

        def refuse(concept, reason, year=year):
            refused[str(year)][concept] = reason

        crosswalk = selected["release_crosswalk"][str(year)]
        for concept in sorted(crosswalk):
            name = crosswalk[concept]
            raw_name = selected["concepts"][concept]["raw_name"]
            candidate = name or raw_name
            labels = (
                schema.get(candidate, {}).get("label", ""),
                dictionary.get(candidate, {}).get("dictionary_label", ""),
                api.get(candidate, {}).get("label", ""),
            )
            present = candidate in schema and not suppressed(*labels)
            if name is None:
                # The crosswalk may only omit a variable this release's
                # own sources omit or suppress.
                assert not present, (year, concept, candidate)
                refuse(concept, "absent or suppressed in release")
                continue
            assert present, (year, concept, name)
            stored = schema[name]
            entry = dictionary.get(name)
            if year in API_YEARS:
                primary = api.get(name)
                assert primary is not None, (year, name)
                label, label_source = primary["label"], "api"
                predicate = primary["predicateType"]
                source = f"{year}_variables.json#{name}"
            else:
                primary = entry
                if primary is None or not primary["verified"]:
                    refuse(concept, "dictionary domain unverified")
                    continue
                label, label_source = primary["dictionary_label"], "dictionary"
                predicate = primary["predicateType"]
                source = f"{year}_dictionary_variables.json#{name}"
                agreement = label_agreement(stored["label"], label)
                if agreement == "conflict":
                    key = f"{year}/{name}"
                    observed_label_conflicts.add(key)
                    ruling = rulings["label_conflicts"].get(key)
                    assert ruling is not None, f"unruled label conflict {key}"
                    label_checks.append(
                        {
                            "release": year,
                            "concept": concept,
                            "variable": name,
                            "schema_label": stored["label"],
                            "dictionary_label": label,
                            "resolution": ruling["resolution"],
                            "evidence": ruling.get("evidence", []),
                        }
                    )
                    if ruling["resolution"] is None:
                        refuse(
                            concept,
                            "open conflict: schema and dictionary labels",
                        )
                        continue
                    if ruling["resolution"] == "schema":
                        label, label_source = stored["label"], "schema"
                    sources.update(ruling.get("evidence", []))
            items, sentinels = split_items(primary)
            ranges = meta_ranges(primary)
            integer = stored["dtype"] != "float" and (
                concepts[concept][1] != "weight"
            )
            primary_spans = intervals(
                items, [(lo, hi) for lo, hi, _ in ranges], integer=integer
            )
            check_items, check_ranges, check_source = (), (), ""
            check_spans = None
            if year in API_YEARS:
                if entry is not None and entry["verified"]:
                    check_items, _ = split_items(entry)
                    check_ranges = meta_ranges(entry)
                    check_source = f"{year}_dictionary_variables.json#{name}"
                    check_spans = intervals(
                        check_items,
                        [(lo, hi) for lo, hi, _ in check_ranges],
                        integer=integer,
                    )
            if not primary_spans and not check_spans:
                refuse(concept, "no verified value domain")
                continue
            if primary_spans and check_spans:
                admitted_spans = intersect(primary_spans, check_spans)
            else:
                admitted_spans = primary_spans or check_spans
            if not admitted_spans:
                refuse(concept, "API and dictionary domains do not overlap")
                continue
            if year in API_YEARS and (
                check_spans is None or primary_spans != check_spans
            ):
                domain_checks.append(
                    {
                        "release": year,
                        "concept": concept,
                        "variable": name,
                        "api": text_intervals(primary_spans),
                        "dictionary": (
                            None
                            if check_spans is None
                            else text_intervals(check_spans)
                        ),
                        "dictionary_verified": bool(
                            entry is not None and entry["verified"]
                        ),
                        "admitted": text_intervals(admitted_spans),
                    }
                )
            family = next(
                (
                    rule
                    for rule in rulings["release_family_conflicts"]
                    if rule["release"] == year
                    and re.search(
                        rule["pattern"],
                        " ".join(
                            (entry or {}).get(field, "")
                            for field in rule["fields"]
                        ),
                        re.I,
                    )
                ),
                None,
            )
            if family is not None:
                sources.update(family["evidence"])
                family_checks.append(
                    {
                        "release": year,
                        "concept": concept,
                        "variable": name,
                        "resolution": family["resolution"],
                        "evidence": family["evidence"],
                    }
                )
                if family["resolution"] is None:
                    refuse(
                        concept,
                        "open conflict: release metadata and user note",
                    )
                    continue
            code_ruling = rulings["code_conflicts"].get(f"{year}/{name}")
            if code_ruling is not None:
                published = {code: lab for code, lab in items}
                assert published == code_ruling["as_published"], (year, name)
                sources.update(code_ruling.get("evidence", []))
                if code_ruling["resolution"] is None:
                    refuse(concept, "open conflict: code meanings")
                    continue
            missing = (
                ("", ".")
                if year <= 2021 and stored["dtype"] != "string"
                else ("",)
            )
            universe = (entry or {}).get("universe", "")
            definition = (
                name,
                label,
                predicate,
                tuple(sorted(items + sentinels)),
                ranges,
                stored["dtype"],
                check_items,
                check_ranges,
                check_source,
                missing,
                universe,
                (
                    f"{year}_dictionary_variables.json#{name}"
                    if universe
                    else ""
                ),
                stored["label"],
                label_source,
            )
            releases[year][concept] = (intern(definition), source)
            effective[(year, concept)] = {
                "name": name,
                "dictionary_label": (entry or {}).get(
                    "dictionary_label", label
                ),
                # Whitespace only: operators such as <= and >= must differ.
                "universe": "".join(universe.split()).casefold(),
                "codes": {
                    code: label_key(lab)
                    for code, lab in sorted(
                        dict(
                            list(items)
                            + list(check_items if year in API_YEARS else ())
                        ).items()
                    )
                },
                "domain": text_intervals(admitted_spans),
                "missing_codes": sorted(code for code, _ in sentinels)
                + sorted(code for code in missing if code),
                "storage_type": stored["dtype"],
            }
        assert set(selected["core_concepts"]) <= releases[year].keys()
        for concept, rule in rulings["corrected_releases"].items():
            if year in rule["releases"] and concept in releases[year]:
                assert crosswalk[concept] == rule["variable"]
                corrections.setdefault(year, {})[concept] = rule[
                    "corrected_on"
                ]
                sources.update(rule["evidence"])
        replicates[year] = replicate_tables(year, concepts, intern, sources)
    unruled = set(rulings["label_conflicts"]) - observed_label_conflicts
    assert not unruled, f"rulings for conflicts not observed: {unruled}"
    notes = {
        year: {
            concept: tuple(
                sorted(
                    set(
                        note_map.get(
                            (year, releases[year][concept][1].split("#")[1]),
                            [],
                        )
                    )
                )
            )
            for concept in sorted(releases[year])
            if note_map.get((year, releases[year][concept][1].split("#")[1]))
        }
        for year in YEARS
    }
    changes = release_changes(selected, effective, refused)
    hashes = {
        name: hashlib.sha256((BASE / name).read_bytes()).hexdigest()
        for name in sorted(sources)
    }
    return {
        "concepts": concepts,
        "definitions": tuple(definitions),
        "releases": releases,
        "replicates": replicates,
        "notes": notes,
        "note_table": note_table,
        "corrections": corrections,
        "refused": refused,
        "label_checks": label_checks + family_checks,
        "domain_checks": domain_checks,
        "changes": changes,
        "hashes": hashes,
    }


def replicate_tables(year, concepts, intern, sources):
    """The calendar-year replicate sidecar's verified layout."""
    rw_schema_file = f"rw{year}_schema.json"
    rw_dictionary = f"rw{year}_dictionary.txt"
    rw = {v["name"]: v for v in read_json(rw_schema_file)}
    text = (BASE / rw_dictionary).read_text()
    # The dictionary documents the replicate family and its range; the
    # storage schema enumerates every column in between.
    assert "REPWGT1" in text and "REPWGT240" in text
    assert "0.000000:9999999.999999" in text
    sources.update((rw_schema_file, rw_dictionary))
    table = {}
    keys = {
        "sample_unit_id": ("SSUID", "00000000000000", "99999999999999"),
        "person_number": ("PNUM", "101", "499"),
        "month": ("MONTHCODE", "1", "12"),
    }
    for concept, (name, low, high) in keys.items():
        assert name in rw
        # The dictionary's D/T/V blocks verify these key definitions.
        assert f"D {name}" in text and f"{low}:{high}" in text
        dtype = rw[name]["dtype"]
        table[concept] = (
            intern(
                (
                    name,
                    rw[name]["label"],
                    {"integer": "int", "string": "string", "float": "float"}[
                        dtype
                    ],
                    (),
                    ((low, high, "Calendar-year replicate key"),),
                    dtype,
                    (),
                    (),
                    "",
                    ("",),
                    "",
                    "",
                    rw[name]["label"],
                    "replicate_dictionary",
                )
            ),
            f"{rw_dictionary}+{rw_schema_file}#{name}",
        )
    for replicate in range(241):
        name = f"REPWGT{replicate}"
        concept = f"replicate_weight_{replicate}"
        assert rw[name]["dtype"] == "float"
        concepts[concept] = ("person", "weight")
        table[concept] = (
            intern(
                (
                    name,
                    rw[name]["label"],
                    "float",
                    (),
                    (
                        (
                            "0.000000",
                            "9999999.999999",
                            "Final person replicate weight",
                        ),
                    ),
                    "float",
                    (),
                    (),
                    "",
                    ("",),
                    "",
                    "",
                    rw[name]["label"],
                    "replicate_dictionary",
                )
            ),
            f"{rw_dictionary}+{rw_schema_file}#{name}",
        )
    return table


def release_changes(selected, effective, refused):
    """Every change in each concept across releases, as an explicit list.

    ``admission`` records compare consecutive releases. Field records
    compare each admitted release with the previous admitted one, which
    can skip refused releases, so stacking any two admitted releases in
    order passes through every recorded change. Labels compare under
    :func:`label_key`; universes ignore whitespace only.
    """
    fields = (
        "name",
        "dictionary_label",
        "universe",
        "codes",
        "domain",
        "missing_codes",
        "storage_type",
    )
    changes = []
    for concept in sorted(selected["concepts"]):
        for before, after in zip(YEARS[:-1], YEARS[1:], strict=True):
            old = effective.get((before, concept))
            new = effective.get((after, concept))
            if (old is None) != (new is None):
                changes.append(
                    {
                        "concept": concept,
                        "from": before,
                        "to": after,
                        "field": "admission",
                        "before": (
                            "admitted"
                            if old
                            else refused[str(before)][concept]
                        ),
                        "after": (
                            "admitted" if new else refused[str(after)][concept]
                        ),
                    }
                )
        admitted = [year for year in YEARS if (year, concept) in effective]
        for before, after in zip(admitted[:-1], admitted[1:], strict=True):
            old, new = (
                effective[(before, concept)],
                effective[(after, concept)],
            )
            for field in fields:
                left, right = old[field], new[field]
                same = (
                    label_key(left) == label_key(right)
                    if field == "dictionary_label"
                    else left == right
                )
                if same:
                    continue
                if field == "codes":
                    shared = left.keys() & right.keys()
                    left = {
                        "changed": {
                            code: [left[code], right[code]]
                            for code in sorted(shared)
                            if left[code] != right[code]
                        },
                        "removed": sorted(left.keys() - right.keys()),
                        "added": sorted(right.keys() - left.keys()),
                    }
                    right = None
                changes.append(
                    {
                        "concept": concept,
                        "from": before,
                        "to": after,
                        "field": field,
                        "before": left,
                        "after": right,
                    }
                )
    return changes


def write_json(filename, payload):
    (BASE / filename).write_text(json.dumps(payload, indent=2) + "\n")


def main():
    tables = build_tables()
    original = REGISTRY.read_text()
    start, tail = original.split("# BEGIN GENERATED TABLES\n")
    _, end = tail.split("# END GENERATED TABLES")
    generated = [
        ("EVIDENCE_SHA256", tables["hashes"]),
        ("_CONCEPTS", tables["concepts"]),
        ("_DEFINITIONS", tables["definitions"]),
        ("_RELEASES", tables["releases"]),
        ("_REPLICATES", tables["replicates"]),
        ("_USER_NOTES", tables["notes"]),
        ("_NOTE_TABLE", tables["note_table"]),
        ("_CORRECTED_ON", tables["corrections"]),
    ]
    REGISTRY.write_text(
        start
        + "# BEGIN GENERATED TABLES\n"
        + "\n\n".join(
            f"{key} = {pformat(value, width=79, sort_dicts=True)}"
            for key, value in generated
        )
        + "\n# END GENERATED TABLES"
        + end
    )
    write_json("refused_concepts.json", tables["refused"])
    write_json("label_checks.json", tables["label_checks"])
    write_json("domain_checks.json", tables["domain_checks"])
    write_json("release_changes.json", tables["changes"])
    print({year: len(v) for year, v in tables["releases"].items()})


if __name__ == "__main__":
    main()
