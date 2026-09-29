"""Pin the independent adjudication applied by U2 milestone 1b.

Documentary checks only: no survey records, counts or outcome calculations.
"""

import hashlib
import html
import json
import re
import subprocess
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
            assert "(Question for PSID staff" in entry["open_question"]
            assert "never from observed records" in entry["open_question"]
            assert entry["part_b_finding"].startswith(("PARTIAL", "See "))
            # A refusal that also depends on another refusal is reported
            # through that dependency first; both are disposition F.
            dependencies = entry.get("blocking_dependencies", [])
            for dependency in dependencies:
                registry_name, key = dependency.split(":")
                assert key in F_ITEMS[registry_name], dependency
            with pytest.raises(
                registry.SourceAdjudicationError,
                match=(
                    "blocked by " + re.escape(", ".join(dependencies))
                    if dependencies
                    else "u2_adjudicate_F"
                ),
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


def draft_3_bytes(record):
    """Read ratified draft 3 from Git history (CI fetches full history)."""
    blob = f"{record['draft_3_commit']}:{SPEC}"
    found = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", blob],
        capture_output=True,
        text=True,
    )
    assert (
        found.returncode == 0
    ), f"draft 3 must come from Git history, not a copy: {found.stderr}"
    assert found.stdout.strip() == record["draft_3_git_blob"]
    raw = subprocess.run(
        ["git", "-C", str(ROOT), "cat-file", "blob", blob],
        capture_output=True,
        check=True,
    ).stdout
    assert hashlib.sha256(raw).hexdigest() == record["draft_3_sha256"]
    return raw


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
    lines = raw.split(b"\n")
    draft_3 = draft_3_bytes(record).split(b"\n")
    assert lines[2].startswith(b"- **Version:** `u2-draft-4`")
    assert draft_3[2].startswith(b"- **Version:** `u2-draft-3`")
    cited = {
        citation["line"]
        for document in documents.values()
        for entry in document["entries"]
        for citation in entry["citations"]
        if citation["file"] == SPEC
    }
    assert {int(line) for line in record["cited_lines_sha256"]} == cited
    for line in cited:
        # Byte-equal to draft 3's line with the same number.
        assert lines[line - 1] == draft_3[line - 1], line
        assert lines[line - 1].strip(), line
        digest = hashlib.sha256(lines[line - 1]).hexdigest()
        assert digest == record["cited_lines_sha256"][str(line)], line
    # §16a is inserted where draft 3 had §17, so every earlier line keeps its
    # draft-3 number and text except the version, status and §15 version.
    section_16a = lines.index(
        b"## 16a. Proposed amendments for `u2-draft-4` (pending Max's ruling)"
    )
    assert draft_3[section_16a].startswith(b"## 17. ")
    changed = {
        number
        for number in range(1, section_16a + 1)
        if lines[number - 1] != draft_3[number - 1]
    }
    assert changed == {3, 4, 1047}
    assert cited < set(range(1, section_16a + 1))


def test_section_16a_quotes_draft_3_verbatim():
    record = json.loads(
        (registry.REGISTRY_DIRECTORY / "u1_identity.json").read_text()
    )["u2_specification"]
    draft_3 = draft_3_bytes(record).decode("utf-8").split("\n")
    quoted = re.findall(
        r"^> (\d+): (.*)$",
        (ROOT / SPEC).read_text(encoding="utf-8"),
        re.M,
    )
    # Draft-3 lines that bar counts or require documents before registration.
    assert [int(number) for number, _ in quoted] == [152, 154, 158, 160, 1391]
    for number, text in quoted:
        assert text == draft_3[int(number) - 1], number
    assert draft_3[1390].startswith("Required fields remain **TO VERIFY**")


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
    saved = sorted(
        p.name
        for p in DOCS.iterdir()
        if p.name not in ("manifest.json", ".gitattributes")
    )
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
    root = manifest["psid_root"]
    assert root["symbol"] == "PSID"
    assert root["default"] == "~/PolicyEngine/psid-data"
    registry_hashes = {}
    for name in registry.REGISTRY_NAMES:
        for source in registry.load_registry(name)["sources"]:
            registry_hashes.setdefault(source["file"], {})[name] = source[
                "sha256"
            ]
    pinned_files = [pinned["file"] for pinned in manifest["pinned_elsewhere"]]
    assert len(pinned_files) == len(set(pinned_files)) == 14
    assert not set(pinned_files) & {s["file"] for s in manifest["sources"]}
    for pinned in manifest["pinned_elsewhere"]:
        assert re.fullmatch(r"[0-9a-f]{64}", pinned["sha256"])
        assert set(pinned["blockers"]) <= blockers and pinned["blockers"]
        assert pinned["file"].startswith(("tests/", "PSID/")), pinned
        if pinned["file"].startswith("tests/"):
            # In the repository: hash it here. PSID/ files are hashed by
            # test_psid_research_sources.py against the staged root.
            raw = (ROOT / pinned["file"]).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == pinned["sha256"]
        # Wherever a registry pins the same file, the digests agree, and a
        # note that names a pinning registry is true.
        for digest in registry_hashes.get(pinned["file"], {}).values():
            assert digest == pinned["sha256"], pinned["file"]
        for claimed in re.findall(
            r"Pinned by the (\w+) registry", pinned["note"]
        ):
            assert claimed in registry_hashes[pinned["file"]], pinned["file"]
    assert "cross_sec_weights_23.pdf" in " ".join(pinned_files)
    # Every quoted document is archived here or pinned.
    known = pinned_files + [s["file"] for s in manifest["sources"]]
    assert {quote["file"] for quote in manifest["research_quotes"]} <= set(
        known
    )


def faq_questions():
    """Map each saved-FAQ line (grep -n numbering) to its question number."""
    lines = (DOCS / "FAQ_20260813.html").read_bytes().decode("utf-8")
    question, owner = None, {}
    for number, line in enumerate(lines.split("\n"), 1):
        text = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", line)).split())
        heading = re.match(r"(\d+)\. \S", text)
        if heading:
            question = int(heading.group(1))
        elif text:
            owner[number] = question
    return owner


def test_faq_line_citations_count_lf_lines():
    """Finding 3: every FAQ line cited lies in the question it is cited for."""
    raw = (DOCS / "FAQ_20260813.html").read_bytes()
    # One bare CR, on line 625: splitlines() numbering runs one high after
    # it, which is how the first version of the research record miscounted.
    bare = [m.start() for m in re.finditer(rb"\r(?!\n)", raw)]
    assert [raw[:at].count(b"\n") + 1 for at in bare] == [625]
    owner = faq_questions()
    manifest = json.loads((DOCS / "manifest.json").read_text())
    pairs = [
        (quote["question"], quote["line"])
        for quote in manifest["research_quotes"]
        if "line" in quote
    ]
    research = (ROOT / manifest["research_record"]).read_text(encoding="utf-8")
    pairs += [
        (int(q), int(line))
        for q, line in re.findall(r"question (\d+) \(line (\d+)\)", research)
    ]
    pairs += [
        (int(q), int(line))
        for q, line in re.findall(
            r"question (\d+), saved-file line (\d+)",
            json.dumps(registry.load_registry("roles")),
        )
    ]
    assert len(pairs) >= 18
    for question, line in pairs:
        assert owner.get(line) == question, (question, line)
    faq = next(
        s
        for s in manifest["sources"]
        if s["file"].endswith("FAQ_20260813.html")
    )
    listed = re.search(r"lines ([\d, and]+) of the saved HTML", faq["cited"])
    cited = [int(n) for n in re.findall(r"\d+", listed.group(1))]
    assert cited == [792, 796, 829, 833, 835, 839, 841, 843, 845, 873]
    questions = {int(n) for n in re.findall(r"\b(\d\d)\b", faq["cited"][:40])}
    assert (
        {owner[line] for line in cited}
        == questions
        == {69, 70, 73, 74, 75, 79}
    )
    roles = {e["id"]: e for e in registry.load_registry("roles")["entries"]}
    faq_citations = [
        c["line"]
        for c in roles["2015.relationship.90"]["citations"]
        if c["file"].endswith("FAQ_20260813.html")
    ]
    assert faq_citations == [833] and owner[833] == 74
