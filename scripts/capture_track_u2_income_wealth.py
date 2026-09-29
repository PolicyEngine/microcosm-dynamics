"""Capture documentary U2 income/wealth routes; never open raw PSID records.

Run from the repository root. Only explicitly named .sps and codebook .pdf
files are opened in the staged PSID directory. Codebook frequency columns
are removed before excerpts are retained. This is a documentary generator,
not a reader or an estimator. Its mappings require independent review.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PSID = Path.home() / "PolicyEngine/psid-data"
WAVES = (2013, 2015, 2017, 2019, 2021, 2023)
EXPOSURE = ROOT / "docs/design/u2_m1_income_wealth_exposure.json"
READS: dict[str, dict] = {}


def record(path: Path, purpose: str) -> bytes:
    content = path.read_bytes()
    READS[str(path)] = {
        "file": str(path),
        "purpose": purpose,
        "sha256": hashlib.sha256(content).hexdigest(),
    }
    return content


def source_name(path: Path) -> str:
    if path.is_relative_to(PSID):
        return "PSID/" + str(path.relative_to(PSID))
    return str(path.relative_to(ROOT))


def normalize(label: str) -> str:
    label = re.sub(r"\b(?:19|20)\d\d\b", "YEAR", label)
    label = re.sub(
        r"\b(?:REF PERSN|REF PERSON|REFERENCE PERSON|RP|HEAD|HD)\b",
        "HEAD",
        label,
    )
    label = re.sub(r"\b(?:SPOUSE|WIFE|SP|WF)\b", "WIFE", label)
    label = label.replace("HEAD AND WIFE", "HEAD_WIFE")
    return " ".join(label.split())


def setup(path: Path) -> tuple[dict, dict]:
    text = record(
        path, "Family setup layouts and variable labels only"
    ).decode()
    positions = {}
    labels = {}
    for line_number, line in enumerate(text.splitlines(), 1):
        for match in re.finditer(r"\b(ER\d+)\s+(\d+)\s*-\s*(\d+)", line):
            positions[match[1]] = (int(match[2]), int(match[3]), line_number)
        match = re.match(r'\s*(ER\d+)\s+"(.*)"\s*$', line)
        if match:
            labels[match[1]] = (match[2], line_number)
    return positions, labels


def codebook(path: Path, ranges: tuple[tuple[int, int], ...] = ()) -> dict:
    record(
        path,
        "Documentary PDF parsed; retained excerpts strip frequency columns",
    )
    commands = (
        [
            [
                "pdftotext",
                "-layout",
                "-f",
                str(a),
                "-l",
                str(b),
                str(path),
                "-",
            ]
            for a, b in ranges
        ]
        if ranges
        else [["pdftotext", "-layout", str(path), "-"]]
    )
    text = "\f".join(
        subprocess.check_output(command, text=True) for command in commands
    )
    entries = {}
    current = None
    for pdf_page, page in enumerate(text.split("\f"), 1):
        printed = re.search(r"Page\s+(\d+)\s+of\s+\d+", page)
        page_number = int(printed[1]) if printed else pdf_page
        for line in page.splitlines():
            match = re.match(
                r'\s*(ER\d+[A-Z0-9]*)\s+"(.*?)"\s+NUM\((\d+)\.(\d+)\)', line
            )
            if match:
                current = {
                    "label": match[2],
                    "width": int(match[3]),
                    "decimals": int(match[4]),
                    "pages": [page_number],
                    "lines": [],
                }
                entries[match[1]] = current
                continue
            if current is None or not line.strip():
                continue
            if (
                "panel study of income dynamics:" in line.lower()
                or printed
                and printed[0] in line
            ):
                continue
            if re.search(r"Count\s+%\s+Value/Range", line):
                current["lines"].append("Value/Range Code Value/Range Text")
                continue
            # Only the published frequency columns, never a value domain.
            line = re.sub(r"^\s*(?:[\d,]+|-)\s+(?:\d*\.\d+|-)\s+", "", line)
            if page_number not in current["pages"]:
                current["pages"].append(page_number)
            current["lines"].append(line.strip())
    for entry in entries.values():
        entry["text"] = "\n".join(entry.pop("lines"))
    return entries


def template_maps() -> dict:
    path = ROOT / "src/populace_dynamics/data/family_income.py"
    tree = ast.parse(
        record(path, "U1 immutable route templates and constants").decode()
    )
    result = {}
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(
            node.target, ast.Name
        ):
            if node.target.id in (
                "_INCOME_VARS",
                "_ACCURACY_VARS",
                "_WEALTH_VARS",
            ):
                result[node.target.id] = ast.literal_eval(node.value)[2013]
    result["income"] = result["_INCOME_VARS"] | result["_ACCURACY_VARS"]
    result["wealth"] = result["_WEALTH_VARS"]
    return result


def main() -> None:
    evidence = Path(
        "/Users/maxghenis/microcosm-launch-evidence/dynasim-parity-20260909"
    )
    for path, purpose in (
        (
            evidence / "RESTRICTED-FILES.md",
            "Read first in this lane, full boundary ledger; rehashed",
        ),
        (
            evidence / "phase2-20260927/prompts/common.md",
            "Read full common instructions; rehashed",
        ),
        (ROOT / "CLAUDE.md", "Read full repository instructions; rehashed"),
        (
            ROOT / "docs/design/boomers2004_1946_55_comparison.md",
            "Read full U2 specification; rehashed",
        ),
        (
            ROOT / "docs/design/boomers2004_uniform_cut_comparison.md",
            "Read U1 template selected source/method sections and text-search matches; rehashed",
        ),
        (
            Path(__file__).resolve(),
            "Documentary generator authored, executed and inspected",
        ),
        (
            ROOT / "tests/data/test_track_u2_income_wealth.py",
            "Documentary schema, inherited-route and identity coverage tests authored and executed",
        ),
    ):
        record(path, purpose)
    maps = template_maps()
    registries = {
        name: {
            "schema_version": 1,
            "target_id": "U2",
            "registry": name,
            "generator": "scripts/capture_track_u2_income_wealth.py",
            "waves": list(WAVES),
            "entries": [],
            "sources": [],
            "source_releases": {},
            "status_scope": "RESOLVED means the family-file documentary variable mapping and its printed domain. Individual relationship-to-income-slot assignment is separately refused by the U2 role registry; this registry does not resolve that assignment.",
            "raw_data_read": False,
        }
        for name in ("income", "wealth")
    }
    source_pages = {
        2013: (1790, 1895),
        2015: (1920, 2012),
        2017: (1970, 2067),
        2019: (1950, 2052),
        2021: (1310, 1416),
        2023: (1230, 1334),
    }
    for wave in WAVES:
        folder = PSID / "family" / str(wave)
        positions, labels = setup(folder / f"FAM{wave}ER.sps")
        by_label = {}
        for variable, (label, _) in labels.items():
            by_label.setdefault(normalize(label), []).append(variable)
        name = f"FAM{wave}ER_codebook.pdf"
        if wave == 2019:
            name = name.lower()
        book_path = folder / name
        book = codebook(book_path, ((1, 10), source_pages[wave]))
        format_path = folder / f"FAM{wave}ER_formats.sps"
        formats = {}
        if format_path.exists():
            format_text = record(
                format_path,
                "Categorical family formats for independent domain citations",
            ).decode("latin-1")
            for match in re.finditer(
                r"VALUE LABELS\s*\n(ER\d+)\s*\n(.*?)\n\.", format_text, re.S
            ):
                formats[match[1]] = {
                    "line": format_text[: match.start(1)].count("\n") + 1,
                    "text": match[2].strip(),
                }
        for registry_name in ("income", "wealth"):
            route_map = dict(maps[registry_name])
            if registry_name == "income" and wave > 2013:
                route_map["head_farm"] = (
                    "",
                    "FARM INCOME OF HEAD AND WIFE-2012",
                )
                route_map["wife_va_pension"] = ("", "WIFE VA PENSION-2012")
                route_map["wife_alimony"] = ("", "WIFE ALIMONY-2012")
                route_map["wife_sex"] = ("", "SEX OF WIFE")
            if registry_name == "wealth" and wave >= 2019:
                route_map["checking_saving"] = (
                    "",
                    "IMP VAL CHECKING/SAVING (W28A) 2013",
                )
                route_map["cd_bonds_treasury"] = (
                    "",
                    "IMP VAL CD/BONDS/TB (W28) 2013",
                )
            matched = {}
            for route, (_, label) in route_map.items():
                candidates = by_label.get(normalize(label), [])
                if re.search(r"20\d\d$", label):
                    year = (
                        wave
                        if registry_name == "wealth" or route == "interview"
                        else wave - 1
                    )
                    candidates = [
                        variable
                        for variable in candidates
                        if str(year) in labels[variable][0]
                    ]
                assert len(candidates) == 1, (
                    wave,
                    registry_name,
                    route,
                    label,
                    candidates,
                )
                matched[route] = candidates[0]
            if registry_name == "wealth":
                for route, variable in tuple(matched.items()):
                    if route.endswith("_acc"):
                        continue
                    expected = labels[variable][0].replace("IMP ", "ACC ", 1)
                    candidates = [
                        var
                        for var, (label, _) in labels.items()
                        if " ".join(label.split())
                        == " ".join(expected.split())
                    ]
                    assert len(candidates) == 1, (wave, route, expected)
                    matched.setdefault(route + "_acc", candidates[0])
            # Accuracy relations come from the codebook's explicit target ID,
            # rather than from variable-number adjacency.
            for route, variable in tuple(matched.items()):
                if route.endswith("_acc"):
                    continue
                accuracy = [
                    var
                    for var, item in book.items()
                    if re.match(
                        rf"Accuracy of {variable}\b", item["text"], re.I
                    )
                ]
                if len(accuracy) == 1:
                    matched.setdefault(route + "_acc", accuracy[0])
                elif accuracy and route + "_acc" not in matched:
                    raise ValueError((wave, variable, accuracy))
            registry = registries[registry_name]
            release_var = next(
                var
                for var, (label, _) in labels.items()
                if "RELEASE NUMBER" in label
            )
            registry["source_releases"][str(wave)] = {
                "variable": release_var,
                "definition": book[release_var]["text"],
                "citations": [
                    {"file": source_name(book_path), "page": page}
                    for page in book[release_var]["pages"]
                ],
            }
            for route, variable in matched.items():
                entry = make_entry(
                    wave,
                    registry_name,
                    route,
                    variable,
                    positions,
                    labels,
                    book,
                    book_path,
                    formats,
                    format_path,
                )
                if route + "_acc" in matched:
                    entry["accuracy_variable"] = matched[route + "_acc"]
                if route.endswith("_acc") and route[:-4] in matched:
                    expected = matched[route[:-4]]
                    reference = re.match(
                        r"Accuracy of (ER\d+)", entry["codebook_text"], re.I
                    )
                    entry["accuracy_for_variable"] = expected
                    if reference and reference[1] != expected:
                        entry["status"] = "TO VERIFY"
                        entry["question"] = (
                            f"Setup label {entry['label']!r} links this flag to {expected}, but the codebook states Accuracy of {reference[1]}. Which target is correct? Retain both documentary claims and obtain source correction before applying this flag."
                        )
                if route == "total_family_income":
                    names = (
                        "hw_taxable",
                        "hw_transfer",
                        "ofum_taxable",
                        "ofum_transfer",
                        "head_ss",
                        "wife_ss",
                        "ofum_ss",
                    )
                    entry["identity"] = {
                        "operation": "sum",
                        "terms": [matched[key] for key in names],
                    }
                    assert all(
                        var in entry["codebook_text"]
                        for var in entry["identity"]["terms"]
                    )
                if route == "wealth1":
                    assets = (
                        "farm_business_asset",
                        "checking_saving",
                        "other_real_estate_asset",
                        "stocks",
                        "vehicles",
                        "other_assets",
                        "ira_annuity",
                    )
                    debts = (
                        "farm_business_debt",
                        "other_real_estate_debt",
                        "credit_card_debt",
                        "student_loan_debt",
                        "medical_debt",
                        "legal_debt",
                        "family_loan_debt",
                        "other_debt",
                    )
                    if wave >= 2019:
                        assets += ("cd_bonds_treasury",)
                    entry["identity"] = {
                        "operation": "sum_assets_minus_sum_debts",
                        "assets": [matched[key] for key in assets],
                        "debts": [matched[key] for key in debts],
                        "excluded_home_equity": matched["home_equity"],
                    }
                    assert all(
                        var in entry["codebook_text"]
                        for key in ("assets", "debts")
                        for var in entry["identity"][key]
                    )
                if (
                    registry_name == "income"
                    and wave > 2013
                    and route in ("wife_age", "wife_sex")
                ):
                    entry["status"] = "TO VERIFY"
                    affected_codes = (
                        "code 90 and a male code 20"
                        if wave == 2015
                        else "codes 90 and 92"
                    )
                    entry["question"] = (
                        f"In {wave}, how do the family-file spouse age/sex universe and spouse income slot treat individual {affected_codes}? These layout and domain matches do not settle person-to-slot routing; require documentary resolution and the reviewed section 3 amendment before use."
                    )
                registry["entries"].append(entry)
            print(
                wave,
                registry_name,
                len(matched),
                "documentary routes captured",
                flush=True,
            )
            add_historical_crosswalks(registry, wave)
    for registry_name, registry in registries.items():
        registry["sources"] = [
            {
                "file": source_name(Path(path)),
                "sha256": info["sha256"],
                "bytes": Path(path).stat().st_size,
            }
            for path, info in READS.items()
            if Path(path).is_relative_to(PSID)
        ]
        destination = ROOT / "data/external/track_u2" / f"{registry_name}.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(registry, indent=2) + "\n")
        READS[str(destination)] = {
            "file": str(destination),
            "purpose": "Generated documentary registry inspected by author",
            "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        }
    write_adjudication(registries)
    READS[str(EXPOSURE)] = {
        "file": str(EXPOSURE),
        "purpose": "Running exposure record authored and inspected; self-hash omitted",
    }
    EXPOSURE.write_text(
        json.dumps(
            {
                "lane": "income_wealth",
                "files": list(READS.values()),
                "incidental_exposure": "Published whole-sample frequency columns on family 2023 codebook printed pages 1290–1292 and 2023 setup header row count were incidentally displayed during initial format inspection. They were not used or reproduced as findings. Subsequent retained codebook excerpts remove frequency columns. Entire six family-codebook PDFs were also parsed in memory for a documentary uncooperative-spouse term search; only source definitions were displayed. No raw PSID records, report/comparator/seal, public result memo or restricted evidence file was opened.",
            },
            indent=2,
        )
        + "\n"
    )


def make_entry(
    wave,
    registry_name,
    route,
    variable,
    positions,
    labels,
    book,
    book_path,
    formats,
    format_path,
):
    label, label_line = labels[variable]
    start, end, layout_line = positions[variable]
    item = book[variable]
    assert end - start + 1 == item["width"], (wave, variable, item)
    assert " ".join(label.split()) == " ".join(item["label"].split()), (
        wave,
        variable,
        label,
        item["label"],
    )
    domain = (
        item["text"].split("Value/Range Code Value/Range Text", 1)[-1].strip()
    )
    citations = [
        {
            "file": f"PSID/family/{wave}/FAM{wave}ER.sps",
            "line": layout_line,
            "quote": f"{variable} {start} - {end}",
        },
        {
            "file": f"PSID/family/{wave}/FAM{wave}ER.sps",
            "line": label_line,
            "quote": label,
        },
    ] + [
        {"file": source_name(book_path), "page": page}
        for page in item["pages"]
    ]
    result = {
        "id": f"{registry_name}.{wave}.{route}",
        "wave": wave,
        "route": route,
        "variable": variable,
        "status": "RESOLVED",
        "citations": citations,
        "label": label,
        "position_start": start,
        "position_end": end,
        "width": end - start + 1,
        "decimals": item["decimals"],
        "reference_year": (
            wave
            if registry_name == "wealth"
            or route
            in (
                "interview",
                "fu_size",
                "head_age",
                "head_sex",
                "wife_age",
                "wife_sex",
                "n_children",
            )
            else wave - 1
        ),
        "codebook_text": item["text"],
        "documented_domain": domain,
        "negative_domain_documented": bool(
            re.search(
                r"^-\d|Actual (?:amount of )?(?:loss|negative)",
                domain,
                re.M | re.I,
            )
        ),
        "all_missing_assigned_statement_present": "all missing data were assigned"
        in " ".join(item["text"].lower().split()),
        "verification_scope": "Exact setup label, position/width, printed codebook definition and domain; not empirical validation or individual relationship routing",
    }
    if variable in formats:
        result["format_text"] = formats[variable]["text"]
        result["citations"].append(
            {
                "file": source_name(format_path),
                "line": formats[variable]["line"],
            }
        )
    if (
        registry_name == "income"
        and wave > 2013
        and route.startswith(("head_", "wife_", "hw_", "ofum_"))
    ):
        codes = [20, 90] if wave == 2015 else [90, 92]
        result["blocking_dependencies"] = [
            f"roles:{wave}.relationship.{code}" for code in codes
        ]
    return result


def add_historical_crosswalks(registry, wave):
    """Account explicitly for keys present only before U1's 2013 wave."""
    entries = {
        entry["route"]: entry
        for entry in registry["entries"]
        if entry["wave"] == wave
    }
    routes = (
        {
            "wife_retirement_annuities": (
                "wife_retirement_pensions",
                "wife_annuities",
                "wife_iras",
                "wife_other_retirement",
            )
        }
        if registry["registry"] == "income"
        else {
            "farm_business": (
                "farm_business_asset",
                "farm_business_debt",
            ),
            "other_real_estate": (
                "other_real_estate_asset",
                "other_real_estate_debt",
            ),
        }
    )
    for route, components in routes.items():
        sources = [entries[key] for key in components]
        item = {
            "id": f"{registry['registry']}.{wave}.{route}",
            "wave": wave,
            "route": route,
            "kind": "historical_route_crosswalk",
            "variables": [source["variable"] for source in sources],
            "status": "RESOLVED",
            "label": "Earlier U1 route represented by later split variables",
            "citations": [
                citation
                for source in sources
                for citation in source["citations"]
            ],
            "codebook_text": "\n\n".join(
                source["variable"] + ": " + source["codebook_text"]
                for source in sources
            ),
            "documented_domain": "Separate component domains apply; no scalar source variable is declared.",
            "usage": "Documentary crosswalk only; not an executable derived input",
        }
        if route == "wife_retirement_annuities":
            item["status"] = "TO VERIFY"
            item["question"] = (
                "The earlier U1 wife retirement/annuities item has no single "
                f"{wave} counterpart. Later documentation identifies pensions, "
                "annuities, IRAs and other retirement separately but does not "
                "establish which reproduce that earlier combined item's IRA "
                "coverage. Do not infer a scalar historical equivalence. U2 "
                "uses the separately documented later fields under its "
                "inherited spouse-retirement retention convention."
            )
            item["blocking_dependencies"] = sources[0].get(
                "blocking_dependencies", []
            )
        else:
            item["identity"] = {
                "operation": "asset_minus_separately_documented_debt",
                "asset": sources[0]["variable"],
                "debt": sources[1]["variable"],
            }
        registry["entries"].append(item)


def write_adjudication(registries):
    path = ROOT / "docs/design/u2_m1_income_wealth_adjudication.md"
    lines = [
        "# U2 milestone 1 income and wealth source adjudication",
        "",
        "Documentary mappings only. `PSID` is `/Users/maxghenis/PolicyEngine/psid-data`. Printed pages are the codebook's own Page labels. RESOLVED identifies a source variable, its exact setup layout and its documented domain; it does not settle the separate relationship-to-income-slot blockers. Every retained codebook excerpt omits published frequency columns. No raw data, income calculation or estimator was used.",
        "",
        "Every U1 2013 family-income and wealth route is mapped independently by documented label for all six U2 waves. Additional later spouse VA-pension and alimony routes are retained for reconciliation; their inclusion does not silently amend U1. Each amount's printed missing-value, loss, universe and endpoint text is retained verbatim in the JSON, with codebook page citations. Accuracy variables are linked through the codebook's explicit 'Accuracy of ER...' statement and, for wealth, independently matched IMP/ACC setup labels. Disagreements are retained as TO VERIFY, never repaired by variable-number adjacency. Source hashes and release-variable definitions are pinned in each registry.",
        "",
        "The seven-aggregate family-income identity and seven/eight-asset less eight-debt WEALTH1 identities are recorded on their composite entries. In particular, checking/savings is W28A from 2019 and CDs/bonds/Treasury bills is the separate W28 component. Farm/business and other-real-estate debts are subtracted once; home equity is excluded from WEALTH1.",
        "",
        "Income-slot status remains conditional on the separate role registry. The family-codebook full-text search for 'uncooperative' found no statement connecting codes 90/92 directly to the spouse-income slot or OFUM totals. The sample-membership definition's inclusion of an uncooperative spouse is expressly 'For this variable' (2017 ER71545 p. 2079; 2019 ER77606 p. 2064; 2023 ER85787 p. 1346) and cannot adjudicate income routing.",
        "",
        "| Route | Variable | Status | Checkable evidence / exact open question |",
        "|---|---|---|---|",
    ]
    for registry in registries.values():
        for entry in registry["entries"]:
            citations = "; ".join(
                (
                    f"`{item['file']}:{item['line']}`"
                    if "line" in item
                    else f"`{item['file']}` p. {item['page']}"
                )
                for item in entry["citations"]
            )
            evidence = citations + (
                ". " + entry["question"]
                if entry["status"] == "TO VERIFY"
                else ". " + entry["label"]
            )
            variables = entry.get("variable") or ", ".join(entry["variables"])
            lines.append(
                f"| `{entry['id']}` | `{variables}` | {entry['status']} | {evidence} |"
            )
    for name, registry in registries.items():
        resolved = sum(
            entry["status"] == "RESOLVED" for entry in registry["entries"]
        )
        unresolved = len(registry["entries"]) - resolved
        lines.extend(
            ["", f"{name}: {resolved} RESOLVED; {unresolved} TO VERIFY."]
        )
    path.write_text("\n".join(lines) + "\n")
    READS[str(path)] = {
        "file": str(path),
        "purpose": "Generated route-by-route source adjudication authored and inspected",
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


if __name__ == "__main__":
    main()
