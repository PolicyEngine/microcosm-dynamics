"""Regenerate embedded SIPP tables from committed documentation only.

No survey records are opened. A missing domain refuses a concept instead of
borrowing codes from another year. Run with the clone's Python from any cwd.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from pprint import pformat

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[2]
REGISTRY = REPO / "src/populace_dynamics/data/sipp_income_registry.py"


def read_json(filename):
    return json.loads((BASE / filename).read_text())


def definition(name, meta, storage, year, *, domain=(), domain_source=""):
    values = meta.get("values", {})
    # Numeric '.' is documented for the older public-use dictionaries.
    # Later dictionary .N/N examples explicitly refer to INTERNAL data.
    missing = ("", ".") if year <= 2021 and storage != "string" else ("",)
    return (
        name,
        meta["label"],
        meta["predicateType"],
        tuple(sorted(values.get("item", {}).items())),
        tuple(
            (x["min"], x["max"], x.get("description", ""))
            for x in values.get("range", [])
        ),
        storage,
        tuple(domain),
        domain_source,
        missing,
    )


def build_tables():
    selected = read_json("concept_selection.json")
    concepts = {
        k: (v["ownership_level"], v["period"])
        for k, v in selected["concepts"].items()
    }
    releases, replicates, refused = {}, {}, {}
    definitions, indices = [], {}
    sources = {"concept_selection.json"}

    def intern(value):
        if value not in indices:
            indices[value] = len(definitions)
            definitions.append(value)
        return indices[value]

    for year in range(2018, 2026):
        primary = (
            f"{year}_dictionary_variables.json"
            if year < 2022
            else f"{year}_variables.json"
        )
        variables = read_json(primary)["variables"]
        schema_file = f"pu{year}_schema.json"
        schema = {v["name"]: v for v in read_json(schema_file)}
        sources.update(
            (primary, schema_file, f"{year}_python_input_example.py")
        )
        if year < 2022:
            sources.update(
                (f"{year}_dictionary.pdf", f"{year}_dictionary.txt")
            )
        releases[year], refused[str(year)] = {}, {}
        for concept, name in selected["release_crosswalk"][str(year)].items():
            if name is None:
                refused[str(year)][concept] = "absent or suppressed in release"
                continue
            meta = variables.get(name)
            if meta is None or meta.get("verified") is False:
                refused[str(year)][concept] = "dictionary domain unverified"
                continue
            if not meta.get("values"):
                refused[str(year)][concept] = "no verified value domain"
                continue
            domain, domain_source = (), ""
            # 2022 API PNUM is an opaque string without its numeric range.
            # Preserve that API schema verbatim and explicitly supplement
            # its domain from this release's dictionary, not another year.
            if year == 2022 and name == "PNUM":
                supplementary = read_json("2022_dictionary_variables.json")[
                    "variables"
                ][name]
                assert supplementary["verified"]
                domain = tuple(
                    (v["min"], v["max"], v["description"])
                    for v in supplementary["values"]["range"]
                )
                domain_source = "2022_dictionary_variables.json#PNUM"
                sources.update(
                    (
                        "2022_dictionary_variables.json",
                        "2022_dictionary.pdf",
                        "2022_dictionary.txt",
                    )
                )
            releases[year][concept] = (
                intern(
                    definition(
                        name,
                        meta,
                        schema[name]["dtype"],
                        year,
                        domain=domain,
                        domain_source=domain_source,
                    )
                ),
                f"{primary}#{name}",
            )
        assert set(selected["core_concepts"]) <= releases[year].keys()
        rw_schema_file = f"rw{year}_schema.json"
        rw_dictionary = f"rw{year}_dictionary.txt"
        rw = {v["name"]: v for v in read_json(rw_schema_file)}
        dictionary = (BASE / rw_dictionary).read_text()
        # Check the documented replicate family and its published range;
        # the storage schema explicitly enumerates every column in between.
        assert "REPWGT1" in dictionary and "REPWGT240" in dictionary
        assert "0.000000:9999999.999999" in dictionary
        sources.update((rw_schema_file, rw_dictionary))
        replicates[year] = {}
        rw_keys = {
            "sample_unit_id": ("SSUID", "00000000000000", "99999999999999"),
            "person_number": ("PNUM", "101", "499"),
            "month": ("MONTHCODE", "1", "12"),
        }
        for concept, (name, low, high) in rw_keys.items():
            assert name in rw
            # The dictionary's D/T/V blocks verify these key definitions.
            assert f"D {name}" in dictionary and f"{low}:{high}" in dictionary
            meta = {
                "label": rw[name]["label"],
                "predicateType": {
                    "integer": "int",
                    "string": "string",
                    "float": "float",
                }[rw[name]["dtype"]],
                "values": {
                    "range": [
                        {
                            "min": low,
                            "max": high,
                            "description": "Calendar-year replicate key",
                        }
                    ]
                },
            }
            replicates[year][concept] = (
                intern(definition(name, meta, rw[name]["dtype"], year)),
                f"{rw_dictionary}+{rw_schema_file}#{name}",
            )
        for replicate in range(241):
            name = f"REPWGT{replicate}"
            concept = f"replicate_weight_{replicate}"
            assert rw[name]["dtype"] == "float"
            concepts[concept] = ("person", "weight")
            meta = {
                "label": rw[name]["label"],
                "predicateType": "float",
                "values": {
                    "range": [
                        {
                            "min": "0.000000",
                            "max": "9999999.999999",
                            "description": "Final person replicate weight",
                        }
                    ]
                },
            }
            replicates[year][concept] = (
                intern(definition(name, meta, "float", year)),
                f"{rw_dictionary}+{rw_schema_file}#{name}",
            )
    hashes = {
        name: hashlib.sha256((BASE / name).read_bytes()).hexdigest()
        for name in sorted(sources)
    }
    return concepts, tuple(definitions), releases, replicates, refused, hashes


def main():
    concepts, definitions, releases, replicates, refused, hashes = (
        build_tables()
    )
    original = REGISTRY.read_text()
    start, tail = original.split("# BEGIN GENERATED TABLES\n")
    _, end = tail.split("# END GENERATED TABLES")
    tables = [
        ("EVIDENCE_SHA256", hashes),
        ("_CONCEPTS", concepts),
        ("_DEFINITIONS", definitions),
        ("_RELEASES", releases),
        ("_REPLICATES", replicates),
    ]
    generated = "\n\n".join(
        f"{key} = {pformat(value, width=79, sort_dicts=True)}"
        for key, value in tables
    )
    REGISTRY.write_text(
        start
        + "# BEGIN GENERATED TABLES\n"
        + generated
        + "\n# END GENERATED TABLES"
        + end
    )
    (BASE / "refused_concepts.json").write_text(
        json.dumps(refused, indent=2) + "\n"
    )
    print({year: len(v) for year, v in releases.items()})


if __name__ == "__main__":
    main()
