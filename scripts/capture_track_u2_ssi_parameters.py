"""Capture U2's documentary SSI parameters, without importing an estimator.

Default operation rebuilds the capture from committed, hash-checked sources.
The source manifest records exact download URLs, times, bytes and digests.
The seven PolicyEngine parameter snapshots are checked independently against
eleven official SSA Federal Register notices and historical CFR editions.
No PSID records, cohort loader, benefit calculation or estimator is used.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "tests/data/track_u2/ssi_sources"
MANIFEST = SOURCE_DIR / "manifest.json"
OUTPUT = ROOT / "data/external/track_u2_ssi_parameters_2012_2022.json"
YEARS = tuple(range(2012, 2023))
SECTIONS = ("1112", "1121", "1124", "1161", "1163", "1205", "1218", "1806")
SSI_FILES = {
    "fbr_individual": "amount/individual.yaml",
    "fbr_couple": "amount/couple.yaml",
    "general_income_exclusion": "income/exclusions/general.yaml",
    "earned_income_exclusion": "income/exclusions/earned.yaml",
    "earned_income_share_excluded": "income/exclusions/earned_share.yaml",
    "resource_limit_individual": "eligibility/resources/limit/individual.yaml",
    "resource_limit_couple": "eligibility/resources/limit/couple.yaml",
}
CONSTANT_NAMES = tuple(SSI_FILES)[2:]
PE_PREFIX = "policyengine_us/parameters/gov/ssa/ssi/"
U1_SSI_SHA256 = (
    "79e641a10d95afba81c8d831852fb52ef0a801e7175e06df17e6cc7cc3e3c523"
)
CENSUS_SHA256 = (
    "288399c475ae3ff02e6d8367425ee0a568b50d239da5656f24d0d2dfafabfb53"
)
U1_CENSUS_SHA256 = (
    "dc21a78736f5085872cf56c9cf291258034c1293572b77455cba689a1ed0eec5"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def serialized(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, indent=2, ensure_ascii=False) + "\n").encode()


def checked_json(path: Path, expected: str) -> dict[str, Any]:
    if sha256(path) != expected:
        raise ValueError(f"capture hash mismatch: {path.name}")
    return json.loads(path.read_text())


def validate_revision(revision: str | None) -> str:
    if not isinstance(revision, str) or not re.fullmatch(
        r"[0-9a-f]{40}", revision
    ):
        raise ValueError("policyengine-us revision must be an exact git SHA")
    return revision


def selected(values: dict[Any, Any], year: int) -> tuple[str, float]:
    """Select the latest dated value no later than January 1, never extrapolate."""
    dates = sorted(
        (dt.date.fromisoformat(str(date)), float(value))
        for date, value in values.items()
        if dt.date.fromisoformat(str(date)) <= dt.date(year, 1, 1)
    )
    if not dates:
        raise ValueError(f"no parameter value in force on {year}-01-01")
    date, value = dates[-1]
    return date.isoformat(), value


def constant(name: str, values: dict[Any, Any]) -> float:
    """Apply U1's constancy rule independently over U2's eleven years."""
    annual = {selected(values, year)[1] for year in YEARS}
    if len(annual) != 1:
        raise ValueError(
            f"{name} changes within 2012-2022; amendment required"
        )
    return annual.pop()


def verify_manifest(manifest: dict[str, Any], root: Path = ROOT) -> None:
    if manifest.get("errors"):
        raise ValueError("source capture has unresolved retrieval errors")
    paths = [source["path"] for source in manifest["sources"]]
    if len(paths) != len(set(paths)):
        raise ValueError("duplicate source path")
    for source in manifest["sources"]:
        path = root / source["path"]
        if path.stat().st_size != source["bytes"]:
            raise ValueError(f"source byte-count mismatch: {path.name}")
        if sha256(path) != source["sha256"]:
            raise ValueError(f"source hash mismatch: {path.name}")
        when = dt.datetime.fromisoformat(source["retrieved_at_utc"])
        if when.utcoffset() != dt.timedelta(0):
            raise ValueError(f"retrieval time is not UTC: {path.name}")


def notice_rates(source: dict[str, Any]) -> dict[str, Any]:
    raw = (ROOT / source["path"]).read_text()
    text = html.unescape(re.sub(r"<[^>]+>", "", raw))
    year = source["income_year"]
    if year == 2016:
        pattern = (
            r"benefit amounts for 2016 under title XVI of the Act will remain "
            r"\$([\d,]+)\s+for an eligible individual, \$([\d,]+)"
        )
    else:
        pattern = (
            rf"monthly amounts for {year}\s*-+\s*" r"\$([\d,]+),\s*\$([\d,]+)"
        )
    match = re.search(pattern, text)
    if match is None:
        raise ValueError(f"cannot locate January FBR in {source['path']}")
    pages = re.findall(r"\[\[Page (\d+)\]\]", text[: match.start()])
    page = int(pages[-1]) if pages else int(source["citation"].split()[-1])
    return {
        "individual": float(match[1].replace(",", "")),
        "couple": float(match[2].replace(",", "")),
        "source": source["path"],
        "sha256": source["sha256"],
        "citation": source["citation"],
        "printed_page": page,
        "verified_excerpt": " ".join(match[0].split()),
    }


def cfr_section(path: Path) -> tuple[ET.Element, str]:
    section = ET.parse(path).find("SECTION")
    if section is None:
        raise ValueError(f"missing CFR section: {path.name}")
    text = " ".join(" ".join(section.itertext()).split())
    return section, text


def verify_historical_cfr() -> dict[str, Any]:
    result = {}
    for number in SECTIONS:
        annual = {}
        texts = []
        for year in YEARS:
            path = SOURCE_DIR / f"CFR-{year}-title20-vol2-sec416-{number}.xml"
            section, text = cfr_section(path)
            # The only within-period text difference is spaces around '+' in
            # 416.1163 example 4, printed as '$80+$86.' before 2016.
            normalized = text.replace("$80+$86.", "$80 + $86.")
            texts.append(normalized)
            annual[str(year)] = {
                "source": str(path.relative_to(ROOT)),
                "edition_date": ET.parse(path).findtext("FDSYS/DATE"),
                "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                "amendment_history": section.findtext("CITA"),
            }
        if len(set(texts)) != 1:
            raise ValueError(
                f"historical CFR 416.{number} changed; review required"
            )
        result[f"416.{number}"] = {
            "status": "RESOLVED",
            "annual_editions": annual,
            "constancy": "all eleven normalized section texts equal",
            "normalization": (
                "whitespace; 416.1163 example 4 '$80+$86.' -> '$80 + $86.'"
            ),
        }
    return result


def verify_cfr_parameter_values(constants: dict[str, float]) -> dict[str, Any]:
    """Read historical legal parameters separately from the YAML snapshots."""
    earned, _ = cfr_section(
        SOURCE_DIR / "CFR-2012-title20-vol2-sec416-1112.xml"
    )
    unearned, _ = cfr_section(
        SOURCE_DIR / "CFR-2012-title20-vol2-sec416-1124.xml"
    )
    resources, _ = cfr_section(
        SOURCE_DIR / "CFR-2012-title20-vol2-sec416-1205.xml"
    )

    def paragraph(section: ET.Element, prefix: str) -> str:
        matches = [
            " ".join("".join(item.itertext()).split())
            for item in section.findall("P")
            if " ".join("".join(item.itertext()).split()).startswith(prefix)
        ]
        if len(matches) != 1:
            raise ValueError(f"ambiguous historical legal paragraph: {prefix}")
        return matches[0]

    general = paragraph(unearned, "(12)")
    earned_flat = paragraph(earned, "(5)")
    earned_share = paragraph(earned, "(7)")
    carryover = paragraph(earned, "(4)")
    if earned_share != "(7) One-half of remaining earned income in a month;":
        raise ValueError("historical earned-share wording changed")
    if (
        "not been excluded from your unearned income in that same month"
        not in carryover
    ):
        raise ValueError(
            "historical general-exclusion carryover wording changed"
        )
    last_row = resources.findall("GPOTABLE/ROW")[-1]
    row = ["".join(item.itertext()) for item in last_row.findall("ENT")]
    if row[0] != "Jan. 1, 1989":
        raise ValueError("historical resource-limit effective date changed")
    observed = {
        "general_income_exclusion": float(re.search(r"\$(\d+)", general)[1]),
        "earned_income_exclusion": float(
            re.search(r"\$(\d+)", earned_flat)[1]
        ),
        "earned_income_share_excluded": 0.5,
        "resource_limit_individual": float(
            row[1].replace(",", "").replace("$", "")
        ),
        "resource_limit_couple": float(
            row[2].replace(",", "").replace("$", "")
        ),
    }
    if observed != constants:
        raise ValueError("historical CFR parameters differ from YAML capture")
    return {
        "status": "RESOLVED",
        "parameters": observed,
        "general_exclusion": {"section": "416.1124(c)(12)", "text": general},
        "earned_exclusion": {"section": "416.1112(c)(5)", "text": earned_flat},
        "earned_share": {"section": "416.1112(c)(7)", "text": earned_share},
        "carryover": {"section": "416.1112(c)(4)", "text": carryover},
        "resource_limits": {"section": "416.1205(c)", "row": row},
        "cross_reference_note": (
            "416.1112(c)(4) retains a reference to 416.1124(c)(10); "
            "the historical editions put the $20 exclusion at (c)(12)"
        ),
        "scope": (
            "Historical CFR text verification, not a claim that U2's "
            "income-unit, vehicle or full-attribution approximations "
            "implement all applicable SSI law"
        ),
    }


def parameter_projection(
    document: dict[str, Any], year: int
) -> dict[str, float]:
    return {
        "fbr_individual": document["federal_benefit_rate_monthly"][
            "individual"
        ][str(year)],
        "fbr_couple": document["federal_benefit_rate_monthly"]["couple"][
            str(year)
        ],
        "general_income_exclusion": document[
            "general_income_exclusion_monthly"
        ],
        "earned_income_exclusion": document["earned_income_exclusion_monthly"],
        "earned_income_share_excluded": document[
            "earned_income_share_excluded"
        ],
        "resource_limit_individual": document["resource_limit"]["individual"],
        "resource_limit_couple": document["resource_limit"]["couple"],
    }


def verify_census_reuse() -> dict[str, Any]:
    later_path = (
        ROOT / "data/external/census_poverty_thresholds_1982_2022.json"
    )
    old_path = ROOT / "data/external/census_poverty_thresholds_2004_2012.json"
    later = checked_json(later_path, CENSUS_SHA256)
    old = checked_json(old_path, U1_CENSUS_SHA256)
    fields = ("weighted_average", "weighted_average_all_ages", "matrix")
    required = (2012, 2014, 2016, 2018, 2020, 2022)
    for field in fields:
        if later[field]["2012"] != old[field]["2012"]:
            raise ValueError(f"2012 Census overlap differs: {field}")
        if not set(map(str, required)) <= set(later[field]):
            raise ValueError(f"Census coverage incomplete: {field}")
    precision = later["checks"]["layout_by_year"]["2022"][
        "weighted_average_unit_dollars"
    ]
    if precision != 10:
        raise ValueError("2022 weighted-average precision changed")
    return {
        "status": "RESOLVED",
        "path": str(later_path.relative_to(ROOT)),
        "sha256": CENSUS_SHA256,
        "required_income_years": list(required),
        "complete_2003_2022": all(
            set(map(str, range(2003, 2023))) <= set(later[field])
            for field in fields
        ),
        "overlap_2012": "every weighted average, all-ages average and matrix entry equal",
        "u1_sha256": U1_CENSUS_SHA256,
        "weighted_average_unit_dollars_2022": precision,
        "stored_dollars": "used as captured; no multiplication by ten",
    }


def build_capture(manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    if manifest is None:
        manifest = json.loads(MANIFEST.read_text())
    revision = validate_revision(manifest.get("policyengine_us_revision"))
    verify_manifest(manifest)
    records = {
        source["parameter"]: source
        for source in manifest["sources"]
        if source["kind"] == "policyengine_parameter"
    }
    if set(records) != set(SSI_FILES):
        raise ValueError("exactly seven parameter snapshots required")
    documents = {
        name: yaml.safe_load((ROOT / record["path"]).read_text())
        for name, record in records.items()
    }
    constants = {
        name: constant(name, documents[name]["values"])
        for name in CONSTANT_NAMES
    }
    fbr = {
        role: {
            str(year): selected(documents[f"fbr_{role}"]["values"], year)[1]
            for year in YEARS
        }
        for role in ("individual", "couple")
    }
    notices = {
        str(source["income_year"]): notice_rates(source)
        for source in manifest["sources"]
        if source["kind"] == "federal_register_notice"
    }
    if set(notices) != set(map(str, YEARS)):
        raise ValueError("all eleven annual notices required")
    for year, notice in notices.items():
        for role in ("individual", "couple"):
            if fbr[role][year] != notice[role]:
                raise ValueError(
                    f"Federal Register FBR mismatch: {year} {role}"
                )
    capture = {
        "schema_version": "populace_dynamics.track_u2_ssi_parameters.v1",
        "target_id": "U2",
        "years": list(YEARS),
        "source": {
            "policyengine_us_revision": revision,
            "policyengine_us_files_sha256": {
                PE_PREFIX + SSI_FILES[name]: records[name]["sha256"]
                for name in SSI_FILES
            },
            "references": {
                name: documents[name]["metadata"]["reference"]
                for name in SSI_FILES
            },
            "rule": "value in force on January 1 of the income year",
            "effective_dates": {
                name: {
                    str(year): selected(documents[name]["values"], year)[0]
                    for year in YEARS
                }
                for name in SSI_FILES
            },
            "generated_by": "scripts/capture_track_u2_ssi_parameters.py",
            "manifest": str(MANIFEST.relative_to(ROOT)),
            "manifest_sha256": sha256(MANIFEST),
        },
        "federal_benefit_rate_monthly": fbr,
        "general_income_exclusion_monthly": constants[
            "general_income_exclusion"
        ],
        "earned_income_exclusion_monthly": constants[
            "earned_income_exclusion"
        ],
        "earned_income_share_excluded": constants[
            "earned_income_share_excluded"
        ],
        "resource_limit": {
            "individual": constants["resource_limit_individual"],
            "couple": constants["resource_limit_couple"],
        },
        "verification": {
            "annual_notices": notices,
            "historical_cfr": verify_historical_cfr(),
            "historical_parameter_values": verify_cfr_parameter_values(
                constants
            ),
            "constant_parameters": {
                name: list(YEARS) for name in CONSTANT_NAMES
            },
            "u1_ssi_2012": "all seven parameters equal",
            "u1_ssi_sha256": U1_SSI_SHA256,
            "census_reuse": verify_census_reuse(),
        },
    }
    old = checked_json(
        ROOT / "data/external/track_u_ssi_parameters.json", U1_SSI_SHA256
    )
    if parameter_projection(capture, 2012) != parameter_projection(old, 2012):
        raise ValueError("complete 2012 SSI projection differs from U1")
    return capture


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify exact committed capture bytes",
    )
    args = parser.parse_args()
    content = serialized(build_capture())
    if args.check:
        if OUTPUT.read_bytes() != content:
            raise ValueError("committed capture does not reproduce")
    else:
        OUTPUT.write_bytes(content)
    print(f"{hashlib.sha256(content).hexdigest()}  {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
