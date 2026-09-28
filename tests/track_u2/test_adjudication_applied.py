"""Pin the independent adjudication applied by U2 milestone 1b.

Documentary checks only: no survey records, counts or outcome calculations.
"""

import hashlib
import json
import re
from pathlib import Path

import pytest

from populace_dynamics.data import u2_source_registry as registry

ROOT = Path(__file__).resolve().parents[2]
ADJUDICATION = "EV/phase2-20260927/out/u2-adjudicate.md"
ADJUDICATION_SHA256 = (
    "a891762bf9be39e05509e59c5b7cd3fdab0eb34feb9ad5b9bb4a8ec3afc39662"
)
SPEC = "docs/design/boomers2004_1946_55_comparison.md"
MASTER = ROOT / "docs/design/u2_m1_source_adjudication.md"
DOCS = ROOT / "tests/data/track_u2/psid_docs"

# Registry: (RESOLVED mappings, REFUSED by disposition F, TO VERIFY).
EXPECTED_COUNTS = {
    "income": (748, 0, 16),
    "wealth": (234, 0, 0),
    "individual": (59, 0, 0),
    "pension": (646, 1, 1),
    "roles": (23, 7, 6),
    "support": (16, 0, 0),
    "weights": (6, 0, 1),
    "design": (2, 0, 0),
}
SSI_AND_CENSUS_RESOLVED = 26

D_ITEMS = {
    "wealth": {
        f"wealth.{wave}.{route}"
        for wave in (2013, 2015, 2017, 2019, 2021, 2023)
        for route in ("wealth2_acc", "checking_saving_acc")
        if route == "wealth2_acc" or wave < 2019
    },
    "roles": {
        "2015.relationship.90",
        "2017.relationship.90",
        "2017.relationship.92",
    },
    "pension": {
        f"{wave}.route.inherited_route_amendment"
        for wave in (2017, 2019, 2021, 2023)
    },
}
F_ITEMS = {
    "roles": {"2015.relationship.20"}
    | {
        f"{wave}.relationship.{code}"
        for wave in (2019, 2021, 2023)
        for code in (90, 92)
    },
    "pension": {"2015.route.respondent_slots"},
}
RELEASED = {
    "roles:2015.relationship.90",
    "roles:2017.relationship.90",
    "roles:2017.relationship.92",
}


@pytest.fixture(scope="module")
def documents():
    return {
        name: registry.load_registry(name) for name in registry.REGISTRY_NAMES
    }


def disposition(entry):
    return entry.get("adjudication", {}).get("disposition")


def master_status(entry):
    return "REFUSED" if disposition(entry) == "F" else entry["status"]


def test_status_counts_after_independent_adjudication(documents):
    totals = {"RESOLVED": 0, "REFUSED": 0, "TO VERIFY": 0}
    for name, document in documents.items():
        counts = {"RESOLVED": 0, "REFUSED": 0, "TO VERIFY": 0}
        for entry in document["entries"]:
            counts[master_status(entry)] += 1
        assert (
            counts["RESOLVED"],
            counts["REFUSED"],
            counts["TO VERIFY"],
        ) == EXPECTED_COUNTS[name], name
        for key in totals:
            totals[key] += counts[key]
    totals["RESOLVED"] += SSI_AND_CENSUS_RESOLVED
    assert totals == {"RESOLVED": 1760, "REFUSED": 8, "TO VERIFY": 24}
    # Milestone 1: 1744 RESOLVED and 48 TO VERIFY over the same records.
    assert sum(totals.values()) == 1744 + 48


def test_dispositions_match_the_adjudication(documents):
    found = {"D": {}, "F": {}, "A": {}}
    changed = [
        name
        for name, document in documents.items()
        if "independent_adjudication" in document
    ]
    for name, document in documents.items():
        for entry in document["entries"]:
            if disposition(entry) in found:
                found[disposition(entry)].setdefault(name, set()).add(
                    entry["id"]
                )
    assert found["D"] == D_ITEMS
    assert found["F"] == F_ITEMS
    assert sum(len(v) for v in found["A"].values()) == 24
    for name in changed:
        meta = documents[name]["independent_adjudication"]
        assert meta["file"] == ADJUDICATION
        assert meta["sha256"] == ADJUDICATION_SHA256
    assert set(changed) == {
        "income",
        "wealth",
        "pension",
        "roles",
        "support",
        "weights",
    }


def test_every_adjudicated_entry_cites_its_adjudication_line(documents):
    for document in documents.values():
        for entry in document["entries"]:
            record = entry.get("adjudication") or entry.get(
                "citation_correction", {}
            ).get("adjudication")
            if record is None:
                continue
            assert record["source"] == ADJUDICATION
            assert {"file": ADJUDICATION, "line": record["line"]} in entry[
                "citations"
            ], entry["id"]


def test_refusals_name_the_adjudication(documents, monkeypatch):
    for name, keys in F_ITEMS.items():
        document = documents[name]
        monkeypatch.setattr(
            registry, "load_registry", lambda _n, d=document: d
        )
        for entry in document["entries"]:
            if entry["id"] not in keys:
                continue
            assert entry["status"] == "RESOLVED"
            assert entry["action"].startswith("refuse_")
            assert entry["action"].endswith("_per_u2_adjudicate_F")
            assert ADJUDICATION in entry["refusal"]
            assert "disposition F" in entry["refusal"]
            assert "question" not in entry
            assert entry["open_question"].endswith("?")
            assert entry["part_b_finding"].startswith(("PARTIAL", "See "))
            with pytest.raises(
                registry.SourceAdjudicationError, match="u2_adjudicate_F"
            ):
                registry.require_resolved(name, entry["id"])


def test_documentary_resolutions_carry_evidence(documents):
    for name, keys in D_ITEMS.items():
        by_id = {e["id"]: e for e in documents[name]["entries"]}
        for key in keys:
            entry = by_id[key]
            assert entry["status"] == "RESOLVED"
            assert "question" not in entry
            assert entry["resolution"].startswith(
                "Independent adjudication D (amendment "
            )
            if name == "roles":
                assert entry["action"] == "documented_rule"
                assert entry["income_role"] == "ofum"
                assert not entry["spouse_slot"]
            if name == "pension":
                assert entry["action"] == "refuse_pending_amendment_5_ruling"
                assert "amendment 5" in entry["refusal"]


def test_open_items_name_their_amendment(documents, monkeypatch):
    open_items = 0
    for name, document in documents.items():
        monkeypatch.setattr(
            registry, "load_registry", lambda _n, d=document: d
        )
        for entry in document["entries"]:
            if entry["status"] != "TO VERIFY":
                continue
            open_items += 1
            record = entry["adjudication"]
            assert record["disposition"] == "A"
            assert f"amendment {record['amendment']}" in entry["question"]
            with pytest.raises(registry.SourceAdjudicationError):
                registry.require_resolved(name, entry["id"])
    assert open_items == 24


def test_corrected_specification_citations(documents):
    spec = (ROOT / SPEC).read_text(encoding="utf-8").split("\n")
    corrected = 0
    for entry in documents["support"]["entries"]:
        if "birth_year" not in entry:
            continue
        lines = [c["line"] for c in entry["citations"] if c["file"] == SPEC]
        assert lines and 67 not in lines, entry["id"]
        assert all(
            spec[line - 1].startswith(f"| {entry['birth_year']} |")
            for line in lines
        ), entry["id"]
        corrected += "citation_correction" in entry
    roles = {e["id"]: e for e in documents["roles"]["entries"]}
    lines = [
        c["line"]
        for c in roles["2013.relationship.90"]["citations"]
        if c["file"] == SPEC
    ]
    assert lines == [147, 150, 156, 175]
    corrected += 1
    pension = {e["id"]: e for e in documents["pension"]["entries"]}
    for wave, page in ((2021, 292), (2023, 290)):
        entry = pension[f"{wave}.route.other_current_plan"]
        pages = [
            c["page"]
            for c in entry["citations"]
            if c["file"].endswith(f"q{wave}.pdf")
        ]
        assert pages == [page - 1, page, page + 1]
        corrected += "citation_correction" in entry
    assert corrected == 18
    for wave in registry.U2_SOURCE_WAVES:
        entry = roles[f"{wave}.relationship.88"]
        assert {"file": SPEC, "line": 190} in entry["citations"]
        assert entry["citation_correction"]["found_by"].startswith("u2-m1b")


def test_specification_revision_keeps_cited_lines(documents):
    pins = json.loads(
        (registry.REGISTRY_DIRECTORY / "u1_identity.json").read_text()
    )
    record = pins["u2_specification"]
    assert record["path"] == SPEC and SPEC not in pins["sha256"]
    raw = (ROOT / SPEC).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == record["sha256"]
    assert record["draft_3_sha256"] == (
        "7badf89e896ece28abcea1cb2db9bd55d468346b405ed06eb357aaf5c7b51df2"
    )
    lines = raw.decode("utf-8").split("\n")
    assert lines[2].startswith("- **Version:** `u2-draft-4`")
    cited = {
        citation["line"]
        for document in documents.values()
        for entry in document["entries"]
        for citation in entry["citations"]
        if citation["file"] == SPEC
    }
    assert {int(line) for line in record["cited_lines_sha256"]} == cited
    for line in cited:
        text = lines[line - 1]
        assert text.strip(), line
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        assert digest == record["cited_lines_sha256"][str(line)], line


def test_released_dependencies(documents):
    for document in documents.values():
        for entry in document["entries"]:
            assert not RELEASED & set(entry.get("blocking_dependencies", []))
    pension = {e["id"]: e for e in documents["pension"]["entries"]}
    assert pension["2015.route.respondent_slots"]["blocking_dependencies"] == [
        "roles:2015.relationship.20"
    ]
    assert (
        "blocking_dependencies" not in pension["2017.route.respondent_slots"]
    )
    for wave in (2017, 2019, 2021, 2023):
        for person in ("head", "wife"):
            for plan in (1, 2):
                entry = pension[f"{wave}.{person}_prev{plan}_dc_amount"]
                assert (
                    f"pension:{wave}.route.inherited_route_amendment"
                    in entry["blocking_dependencies"]
                )


def test_master_record_matches_registries(documents):
    text = MASTER.read_text(encoding="utf-8")
    rows = dict(
        re.findall(r"^\| `([a-z]+:[^`]+)` \| ([A-Z ]+?) \| ", text, re.M)
    )
    expected = {
        f"{name}:{entry['id']}": master_status(entry)
        for name, document in documents.items()
        for entry in document["entries"]
    }
    assert rows == expected
    assert "**1760 RESOLVED; 8 REFUSED; 24 TO VERIFY**" in text
    for name, (resolved, refused, open_) in EXPECTED_COUNTS.items():
        assert f"| {name} | {resolved} | {refused} | {open_} |" in text


def test_psid_documentation_manifest():
    manifest = json.loads((DOCS / "manifest.json").read_text())
    blockers = {
        "male_code20_2015",
        "uncooperative_90_92_2019_2023",
        "revised_2017_weights",
    }
    saved = sorted(p.name for p in DOCS.iterdir() if p.name != "manifest.json")
    assert saved == sorted(
        Path(source["file"]).name for source in manifest["sources"]
    )
    for source in manifest["sources"]:
        raw = (ROOT / source["file"]).read_bytes()
        assert len(raw) == source["bytes"], source["file"]
        assert hashlib.sha256(raw).hexdigest() == source["sha256"]
        assert source["url"].startswith("https://psidonline.isr.umich.edu/")
        assert re.fullmatch(
            r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", source["retrieved_at_utc"]
        )
        assert set(source["blockers"]) <= blockers and source["blockers"]
        if source["file"].endswith(".pdf"):
            assert raw.startswith(b"%PDF")
        if "archive_url" in source:
            assert source["archive_url"].startswith(
                "https://web.archive.org/web/"
            )
            assert source["archive_url"].endswith(source["url"])
    covered = {b for s in manifest["sources"] for b in s["blockers"]}
    assert covered == blockers
    for pinned in manifest["pinned_elsewhere"]:
        path = ROOT / pinned["file"]
        if pinned["file"].startswith("tests/"):
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            assert digest == pinned["sha256"]
