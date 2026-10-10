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
RESEARCH = ROOT / "docs/design/u2_m1b_psid_research.md"
# Quote-mark, dash and soft-hyphen folding, by code point.
FOLD = (
    {c: "'" for c in (0x2018, 0x2019, 0x201A, 0x201B, 0x2032, 0x60, 0xB4)}
    | {c: '"' for c in (0x201C, 0x201D, 0x201E, 0x201F, 0x2033)}
    | {c: "-" for c in (*range(0x2010, 0x2016), 0x2212)}
    | {0xAD: None}
)
OPENING = re.compile(r"(?:^|(?<=[\s(\[:]))'(?=\S)")
CLOSING = re.compile(r"(?<=\S)'(?=[\s.,;:)\]]|$)")


def fold(text):
    return " ".join(text.translate(FOLD).split())


def quoted_spans(markdown):
    """Single-quoted spans outside code spans and verbatim blockquotes."""
    spans = []
    for line in re.sub(r"`[^`]*`", " ", markdown).split("\n"):
        if line.startswith(("> ", "**Question for PSID staff")):
            continue
        start = 0
        while opening := OPENING.search(line, start):
            closing = CLOSING.search(line, opening.end())
            if closing is None:
                break
            spans.append(line[opening.end() : closing.start()])
            start = closing.end()
    return spans


# Registry: (RESOLVED mappings, REFUSED by disposition F and not replaced
# by a ruling, TO VERIFY).  Max's d1090 ruling (2026-10-10; spec section
# 16c) replaced all eight F refusals (roles 7, pension 1).
EXPECTED_COUNTS = {
    "income": (748, 0, 16),
    "wealth": (234, 0, 0),
    "individual": (59, 0, 0),
    "pension": (647, 0, 1),
    "roles": (30, 0, 6),
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
#: The F refusals Max's d1090 ruling replaced (section 16c): every one.
D1090_RULED = {
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
} | {f"roles:{key}" for key in D1090_RULED["roles"]}
# §16a's inline quotes of draft 3: (quote, draft-3 line, the exact §16a
# text that joins the quote to its line citation).
DRAFT_3_INLINE_QUOTES = [
    (
        "the 2015 male code-20 blocker",
        154,
        "Line 154's count bar governs code 90's routing claim, and it ties "
        "that claim to 'the 2015 male code-20 blocker'",
    ),
    (
        "Resolve the explicit relationship-source inconsistencies, including "
        "2015 male-code-20 routing and code-90/code-92 OFUM versus "
        "spouse-slot routing",
        1382,
        "line 1382 for B1 and B2 ('Resolve the explicit",
    ),
    (
        "Verify identification support, observation plans, weight "
        "documentation and refreshed design domains",
        1383,
        "line 1383 for B3 ('Verify identification",
    ),
    (
        "OFUM SSI totals form one individual unit",
        436,
        "\N{SECTION SIGN}8's OFUM unit ('OFUM SSI totals",
    ),
    (
        "Counts cannot establish routing, justify assuming such records "
        "absent, or waive this blocker",
        160,
        "Line 160 forbids exactly that ('Counts cannot",
    ),
    (
        "Neither empty empirical categories nor observed outputs may "
        "substitute for documentary resolution",
        1391,
        "line 1391 ('Neither empty",
    ),
    (
        "it may not be established from counts",
        154,
        "line 154 ('it may not be established",
    ),
    (
        "Source documentation must resolve this before registration",
        160,
        "line 160's 'Source documentation",
    ),
    (
        "under the same standard as the 2015 male code-20 blocker",
        152,
        "code-20 blocker' (line 152)",
    ),
    (
        "like the 2015 male code-20 blocker",
        154,
        "'like the 2015 male code-20 blocker' (line 154)",
    ),
    ("Legal Spouse", 160, "'Legal Spouse' (draft-3 line 160)"),
    (
        "The weight construction and immigrant-refreshment coverage must be "
        "documented before registration.",
        134,
        "Line 134 reads, verbatim: 'The weight construction",
    ),
    (
        "block execution",
        656,
        "'block execution' and 'cannot trigger fallback or silent omission' "
        "(draft-3 line 656)",
    ),
    (
        "cannot trigger fallback or silent omission",
        656,
        "'cannot trigger fallback or silent omission' (draft-3 line 656)",
    ),
]
# What §16a asks Max to rule on: every recommendation and every option's
# amendment statement. A change here must be deliberate.
RECOMMENDATIONS = [
    "Recommendation for B1: send the PSID question in "
    "`docs/design/u2_m1b_psid_research.md` \N{SECTION SIGN}1 now, and adopt "
    "option 1 only as an explicitly ratified amendment to draft-3 lines 154, "
    "160 and 1391.",
    "Recommendation for B2: send the PSID question in "
    "`docs/design/u2_m1b_psid_research.md` \N{SECTION SIGN}2 now, and adopt "
    "option 1 only as an explicitly ratified amendment to draft-3 lines 152, "
    "154 and 158.",
    "Recommendation for B3: option 1, adopted as an explicitly ratified "
    "amendment to draft-3 line 134.",
]
OPTIONS = {
    "**1d. ": [
        "Documented rule plus a halting guard. Amends draft-3 lines 154, 160 "
        "and 1391.",
        "Documented rule plus exclusion. Amends draft-3 line 160.",
        "Hold registration for PSID's answer. Draft 3 as written; amends "
        "nothing.",
    ],
    "**1e. ": [
        "Exclude and disclose. Amends draft-3 lines 152, 154 and 158 for "
        "2019\N{EN DASH}2023.",
        "Stated convention. Amends draft-3 lines 152, 154 and 158 for "
        "2019\N{EN DASH}2023.",
        "Wait for PSID documentation. Draft 3 as written; amends nothing.",
        "Documented rule plus a halting guard. Amends draft-3 lines 152, 154, "
        "158 and 1391.",
    ],
    "### Amendment 6 ": [
        "Use the released weight and disclose. Amends draft-3 line 134.",
        "Hold registration for PSID's construction document.",
        "Substitute the documented longitudinal weight ER34650 for 2017.",
    ],
}


@pytest.fixture(scope="module")
def documents():
    return {
        name: registry.load_registry(name) for name in registry.REGISTRY_NAMES
    }


def disposition(entry):
    return entry.get("adjudication", {}).get("disposition")


def master_status(entry):
    """REFUSED: an adjudication F refusal that no ruling has replaced."""
    refused = disposition(entry) == "F" and "ruling" not in entry
    return "REFUSED" if refused else entry["status"]


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
    assert totals == {"RESOLVED": 1768, "REFUSED": 0, "TO VERIFY": 24}
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
    """An F refusal no ruling has replaced refuses and names the
    adjudication.  Since d1090 there is none; the check stays for any
    future F item."""
    unruled = {
        name: {
            e["id"]
            for e in documents[name]["entries"]
            if e["id"] in keys and "ruling" not in e
        }
        for name, keys in F_ITEMS.items()
    }
    assert not any(unruled.values()), unruled
    for name, keys in unruled.items():
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


def test_d1090_replaced_every_refusal_with_its_exclusion(
    documents, monkeypatch
):
    """Max's d1090 ruling (section 16c) on every F item: the ratified
    option and amended draft-3 lines, the exclusion, no refusal, the
    adjudication record kept and the superseded refusal preserved."""
    assert D1090_RULED == F_ITEMS
    b1 = "male code 20 in 2015 family unit"
    b2 = "uncooperative spouse or partner in family unit"
    for name, keys in D1090_RULED.items():
        document = documents[name]
        monkeypatch.setattr(
            registry, "load_registry", lambda _n, d=document: d
        )
        by_id = {e["id"]: e for e in document["entries"]}
        for key in keys:
            entry = by_id[key]
            ruling = entry["ruling"]
            assert (
                ruling["decision"],
                ruling["date"],
                ruling["specification_section"],
            ) == ("d1090", "2026-10-10", "16c")
            assert disposition(entry) == "F"
            assert "refusal" not in entry and "blocking_dependencies" not in (
                entry
            )
            assert ADJUDICATION in entry["superseded_refusal"]
            assert "disposition F" in entry["superseded_refusal"]
            assert entry["resolution"].startswith("Max's ruling d1090 ")
            assert "(Question for PSID staff" in entry["open_question"]
            assert "not sent" not in entry["open_question"]
            assert entry["part_b_finding"].startswith(("PARTIAL", "Follows "))
            assert registry.require_resolved(name, key) == entry
            b1_entry = key.startswith("2015.")
            assert ruling["option"] == ("1d-2" if b1_entry else "1e-1")
            if name == "pension":
                assert ruling["amendment"] == "5c"
                assert "action" not in entry
                continue
            if b1_entry:
                assert ruling["amends_draft_3_lines"] == [160]
                assert entry["action"] == (
                    "documented_rule_with_family_unit_exclusion"
                )
                assert entry["family_unit_exclusion"] == {
                    "disposition": b1,
                    "condition": {"sex": 1},
                }
                assert entry["income_role"] == "spouse"
                assert entry["spouse_slot"]
            else:
                assert ruling["amends_draft_3_lines"] == [152, 154, 158]
                assert ruling["amended_waves"] == [2019, 2021, 2023]
                assert entry["action"] == "exclude_family_unit_per_d1090"
                assert entry["family_unit_exclusion"] == {"disposition": b2}
                assert entry["income_role"] == "excluded"
                assert not entry["spouse_slot"]
    for name in ("roles", "income", "pension"):
        (applied,) = documents[name]["rulings_applied"]
        assert applied["decision"] == "d1090", name


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
    # §16a says draft-3 line 1391 "now closes §17": it is §17's last line.
    spec = (ROOT / SPEC).read_text(encoding="utf-8")
    section_17 = spec[spec.index("## 17. ") : spec.index("## 18. ")]
    assert section_17.strip().split("\n")[-1] == draft_3[1390]
    assert "draft-3 line 1391 now closes §17" in spec


def test_section_16a_quotes_are_sourced():
    """Every §16a quote is registered with a PSID source or is draft 3's."""
    record = json.loads(
        (registry.REGISTRY_DIRECTORY / "u1_identity.json").read_text()
    )["u2_specification"]
    draft_3 = fold(draft_3_bytes(record).decode("utf-8"))
    spec = (ROOT / SPEC).read_text(encoding="utf-8")
    section = spec[spec.index("## 16a. ") : spec.index("## 17. ")]
    registered = [
        fold(quote["text"])
        for quote in json.loads((DOCS / "manifest.json").read_text())[
            "spec_quotes"
        ]
    ]
    folded = fold(section)
    for text in registered:
        for part in re.split(r"\s*\.\.\.\s*", text):
            assert part in folded, part
    spans = quoted_spans(section)
    assert len(spans) >= 50
    unsourced = [
        span
        for span in spans
        if not any(fold(span) in text for text in registered)
        and fold(span) not in draft_3
    ]
    assert not unsourced, unsourced


def test_section_16a_cites_the_draft_3_lines_it_quotes():
    """Each inline draft-3 quote is on the line §16a cites beside it."""
    record = json.loads(
        (registry.REGISTRY_DIRECTORY / "u1_identity.json").read_text()
    )["u2_specification"]
    draft_3 = draft_3_bytes(record).decode("utf-8").split("\n")
    spec = (ROOT / SPEC).read_text(encoding="utf-8")
    section = spec[spec.index("## 16a. ") : spec.index("## 17. ")]
    folded = fold(section)
    for quote, line, context in DRAFT_3_INLINE_QUOTES:
        assert fold(quote) in fold(draft_3[line - 1]), (quote, line)
        # The exact joining text: a swapped or wrong line number fails.
        assert fold(context) in folded, context
        assert fold(quote)[:12] in fold(context) or (
            fold(quote)[-12:] in fold(context)
        ), context
        assert str(line) in context or "\N{SECTION SIGN}8's" in context
    # Line 436, cited by its section, lies in draft 3's section 8.
    section_8 = [
        number
        for number, text in enumerate(draft_3, 1)
        if text.startswith(("## 8. ", "## 9. "))
    ]
    assert section_8[0] < 436 < section_8[1]
    # Every §16a quote that no PSID source supplies is in the register.
    registered = [
        fold(quote["text"])
        for quote in json.loads((DOCS / "manifest.json").read_text())[
            "spec_quotes"
        ]
    ]
    unregistered = [
        span
        for span in quoted_spans(section)
        if not any(fold(span) in text for text in registered)
        and not any(
            fold(span) in fold(quote) for quote, _, _ in DRAFT_3_INLINE_QUOTES
        )
    ]
    assert not unregistered, unregistered


NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "ten": 10,
    "fifteen": 15,
}


def plan_cells(lines):
    """The §3 plan tables (spec lines 74-92): (row, birth, age, weight)."""
    assert lines[73].startswith("| 1947 |") and lines[91].startswith(
        "| 1954 |"
    )
    cells = []
    for line in lines[73:78]:
        birth, _, wave, multiplier = line.strip("| ").split(" | ")
        cells.append(("U0", int(birth), 67, int(wave), float(multiplier)))
    for line in lines[87:92]:
        birth, age_66, age_68, multiplier = line.strip("| ").split(" | ")
        for age, cell in ((66, age_66), (68, age_68)):
            wave = int(cell.split(" / ")[1])
            cells.append(("U1", int(birth), age, wave, float(multiplier)))
    return cells


def test_section_16a_coverage_costs_follow_the_plan_tables():
    """Review finding 4: each hold's cells, recomputed from lines 74-92."""
    lines = (ROOT / SPEC).read_text(encoding="utf-8").split("\n")
    cells = plan_cells(lines)
    u0 = [c for c in cells if c[0] == "U0"]
    # U1 reuses U0's odd-birth observations and adds the even-birth halves.
    u1 = u0 + [c for c in cells if c[0] == "U1"]
    assert (len(u0), len(u1), sum(c[4] for c in u1)) == (5, 15, 10)
    spec = "\n".join(lines)
    section = spec[spec.index("## 16a. ") : spec.index("## 17. ")]
    holds = {
        "3. **Hold registration for PSID's answer.": {2015},
        "3. **Wait for PSID documentation.": {2019, 2021, 2023},
        "2. **Hold registration for PSID's construction document.": {2017},
    }
    for start, waves in holds.items():
        text = section[section.index(start) :].split("\n", 1)[0]
        assert "(lines 74\N{EN DASH}92)" in text and "line 656" in text
        u0_held = sorted(c[1] for c in u0 if c[3] in waves)
        u1_held = [c for c in u1 if c[3] in waves]
        words = re.search(
            r"U0's ([\d, and]+) cells?, (\w+) of its five, and (\w+) of "
            r"U1's fifteen cells.*carry ([\d.]+|\w+) of U1's ten birth-year "
            r"weights",
            text,
        )
        assert words, start
        years, u0_count, u1_count, weight = words.groups()
        assert [int(y) for y in re.findall(r"\d{4}", years)] == u0_held
        assert NUMBER_WORDS[u0_count] == len(u0_held)
        assert NUMBER_WORDS[u1_count] == len(u1_held)
        stated = NUMBER_WORDS.get(weight) or float(weight)
        assert stated == sum(c[4] for c in u1_held), start
        # Every held U1 half-observation is named.
        halves = {(c[1], c[2]) for c in u1_held if c[0] == "U1"}
        named = {
            (int(b), int(a))
            for b, a in re.findall(r"(\d{4})(?:'s)? age-(66|68)", text)
        }
        for pair in re.findall(
            r"both half-observations of (\d{4}) and of (\d{4})", text
        ):
            named |= {(int(b), a) for b in pair for a in (66, 68)}
        assert named == halves, start


def test_section_16a_recommendations_and_options():
    """The options and recommendations put to Max, and their amendments."""
    spec = (ROOT / SPEC).read_text(encoding="utf-8")
    section = spec[spec.index("## 16a. ") : spec.index("## 17. ")]
    assert (
        re.findall(r"^\*\*(Recommendation for B[123]: .*?)\*\*", section, re.M)
        == RECOMMENDATIONS
    )
    for start, expected in OPTIONS.items():
        block = section[section.index(start) :]
        block = block[: block.index("**Recommendation for B")]
        assert re.findall(r"^\d\. \*\*(.*?)\*\*", block, re.M) == expected
    counts = section[section.index("**1g. ") :]
    assert "no refusal in amendment 1 is waived by observed absence" in counts
    assert (
        "a guard exists only as the explicitly ratified amendment its option "
        "names" in counts
    )
    outstanding = spec[spec.index("## 17. ") : spec.index("## 18. ")]
    assert (
        "takes effect only if Max also ratifies the amendment to draft-3 "
        "lines 152\N{EN DASH}160 or 1391 that the option names" in outstanding
    )
    assert (
        "B3's option 1 likewise takes effect only if Max ratifies its "
        "amendment to draft-3 line 134." in outstanding
    )


#: SHA-256 of the text of §16a (to "## 16b. ") and of §16b (to the next
#: section) as merged with Max's d637 ruling (PR #500; master 1fadf50a).
#: §16c records d1090 and leaves both unchanged, as the record of what was
#: proposed and first ruled.
SECTION_SHA256 = {
    "## 16a. ": (
        "e18c27687b6ece12bc4a8db091c01d732ea17067fb0a7f55b47191b0a0fb8cb8"
    ),
    "## 16b. ": (
        "312ac7673e2b3c16cd67b1fe8bb3c68cf1fc5e2e40c6055e9cf616e2043bcdab"
    ),
}
#: Max's d1090 ruling (2026-10-10): the §16a option each blocker takes,
#: the option's amendment statement as §16a words it, and its named
#: disposition.
D1090_OPTIONS = {
    "B1": (
        "**1d. ",
        "2. **Documented rule plus exclusion. Amends draft-3 line 160.**",
        "male code 20 in 2015 family unit",
    ),
    "B2": (
        "**1e. ",
        "1. **Exclude and disclose. Amends draft-3 lines 152, 154 and 158 "
        "for 2019\N{EN DASH}2023.**",
        "uncooperative spouse or partner in family unit",
    ),
}
D1090_ROWS = {
    "B1": "| 1d: blocker B1 (2015 male code 20) | Option 2, documented rule "
    "plus exclusion, ratified as an explicit amendment | Line 160 | 2015 "
    "code 20 occupies the spouse slot as documented. Every 2015 family-unit "
    "observation that contains a person recorded male (ER32000 = 1) with "
    "2015 relationship code 20 is excluded from every row under the named "
    "disposition `male code 20 in 2015 family unit`. Options 1 and 3 are "
    "not ratified: no guard lets a count decide anything, and option 3's "
    "hold no longer applies |",
    "B2": "| 1e: blocker B2 (codes 90 and 92 in 2019\N{EN DASH}2023) | "
    "Option 1, exclude and disclose, ratified as an explicit amendment | "
    "Lines 152, 154 and 158, for 2019\N{EN DASH}2023 only | Every 2019, "
    "2021 or 2023 family-unit observation that contains a code-90 or "
    "code-92 person is excluded from every row under the named disposition "
    "`uncooperative spouse or partner in family unit`, whether the target "
    "person is the reference person, the uncooperative spouse or partner, "
    "or another member. Options 2, 3 and 4 are not ratified: no income, "
    "Social Security or SSI is assigned to these persons, no OFUM routing "
    "is asserted for them, no guard lets a count decide anything, and "
    "option 3's hold no longer applies |",
    "5c": "| 5c: U7's 2015 spouse slot (amendment 5, ratified by d637) | "
    "Follows the B1 ruling, as 5c provides | None beyond amendment 5 | "
    "U7's 2015 spouse slot is the documented female spouse or partner "
    "slot, and B1's exclusion applies to U7 as to every other row |",
}
#: The operative lines of the d1090 record, complete, by where they
#: stand: each must be a whole line there, exactly once (reviews of
#: e4dd350 and 8103881, finding 2).
D1090_CLAUSES = {
    "header_version": [
        "- **Version:** `u2-draft-4` (milestone 1b, 2026-09-28; revised "
        "2026-09-29 after the independent review; Max's rulings recorded "
        "2026-09-30 and 2026-10-10): proposed amendments 1\N{EN DASH}6 in "
        "\N{SECTION SIGN}16a, ruled by Max on 2026-09-30 (d637) as recorded "
        "in \N{SECTION SIGN}16b, with blockers B1 and B2 ruled on "
        "2026-10-10 (d1090) as recorded in \N{SECTION SIGN}16c. Previous "
        "version: `u2-draft-3` (round 2).",
    ],
    "header_status": [
        "- **Status:** decisions ruled for `u2-draft-3`. On 2026-09-28 Max "
        "approved the \N{SECTION SIGN}16 defaults and ratification of that "
        "draft (d514, in chat). Per \N{SECTION SIGN}20, the version becomes "
        "`u2-ratified-1` by the merge that completes \N{SECTION SIGN}20 "
        "steps 2\N{EN DASH}5 and materializes the final parameter block; "
        "that merge needs no further ruling unless it changes this "
        "document's substance. `u2-draft-4` adds \N{SECTION SIGN}16a, whose "
        "proposed amendments change substance, so each needed Max's ruling "
        "first. He ruled on 2026-09-30 (d637; \N{SECTION SIGN}16b): B3 is "
        "resolved by option 1, amendments 2\N{EN DASH}5 are ratified as "
        "written, and blockers B1 and B2 were held until PSID answered. "
        "PSID answered on 2026-10-07, and on 2026-10-10 he ruled on B1 and "
        "B2 (d1090; \N{SECTION SIGN}16c): B1 takes option 2 and B2 option "
        "1, each an exclusion under a named disposition, ratified as "
        "amendments to draft-3 line 160 (B1) and to draft-3 lines 152, 154 "
        "and 158 for 2019\N{EN DASH}2023 (B2). No blocker hold remains. "
        "Amendment 1's parts 1a\N{EN DASH}1c, which the d637 ruling's list "
        "does not name, are read as ratified pending Max's confirmation "
        "(d745; \N{SECTION SIGN}16b). Not registered or authorized for "
        "execution.",
    ],
    "record": [
        *D1090_ROWS.values(),
        "> \"yes: Max 2026-10-10 in chat ('1090 yes'): B1 option 2 (exclude "
        "2015 family units with a male code-20 person, rule fixed before "
        "any count) and B2 option 1 (exclude 2019-2023 family units with a "
        'code-90/92 person, disclose the count)"',
        "Both rules are fixed by this ruling, before any count, and each is "
        "vacuous if no such unit supplies an observation. Each count is "
        "disclosed after the authorized structural pass (\N{SECTION SIGN}4) "
        "and decides nothing. B1's disclosed count is the count option 1d-1 "
        "specifies and option 1d-2 inherits: 2015 code-20 persons recorded "
        "male (ER32000 = 1) in family units that would otherwise supply any "
        "U2 observation. Option 1e-1 requires B2's count to be disclosed "
        "and to decide nothing, but does not specify its counting unit. "
        "Proposed clarification, pending Max's confirmation (d1242) before "
        "that count is computed: count code-90 and code-92 persons in 2019, "
        "2021 and 2023 family units that would otherwise supply any U2 "
        "observation. This record ratifies no additional B1 or B2 counting "
        "requirements; the structural pass's ordinary disposition counts "
        "(\N{SECTION SIGN}4) list the observations excluded under each "
        "named disposition. The trade-offs \N{SECTION SIGN}16a states for "
        "each option (a population loss of unknown size, confined to units "
        "with a spouse or partner present, and population rules that differ "
        "by wave) apply as stated there.",
        "- **To draft-3 line 160 (B1).** Line 160's requirement that "
        '"Source documentation must resolve this before registration" is '
        "replaced, for a male code-20 person in 2015, by the population "
        "rule above. The line's other sentences stand: no count establishes "
        "the routing, justifies assuming such records absent or waives the "
        "blocker, and the declared interpretation changes only through this "
        "ratified amendment. Lines 154 and 1391 are not amended for B1, "
        "because no ratified B1 option lets a count decide anything.",
        "- **To draft-3 lines 152, 154 and 158 (B2), for 2019, 2021 and "
        "2023.** The documentary confirmation of code-90 and code-92 income "
        "routing that these lines require before registration is replaced, "
        "in these three waves, by the population rule above. For 2013, 2015 "
        "and 2017 the lines are not amended: codes 90 and 92 there keep the "
        "status \N{SECTION SIGN}16b records (1a and 1b, pending d745). Line "
        "1391 is not amended.",
        "**How the rules apply.** A family unit is identified as `wave "
        "\N{MULTIPLICATION SIGN} 100000 + interview` (line 130), and its "
        "members are the in-family persons, sequence 1\N{EN DASH}20, of "
        "that interview in that wave (line 126); persons in institutions, "
        "movers-out and decedents keep their own counted dispositions (line "
        "127). The rules test those members, the persons whose relationship "
        "codes the builder classifies by \N{SECTION SIGN}3's role rules. An "
        "observation already disposed of before its family is classified "
        "(not in the file, not present, zero weight or sex unknown) keeps "
        "that disposition; each rule applies to the observations its family "
        "unit would otherwise supply. This is how the rules are applied, "
        "not a further amendment.",
        "- U2 stays unregistered and unauthorized. With B3's hold lifted by "
        "d637 and the B1 and B2 holds lifted here, no blocker hold remains, "
        "but registration still waits for the rest of "
        "\N{SECTION SIGN}\N{SECTION SIGN}17 and 20: the 24 TO VERIFY "
        "records, the registry commits for the ratified amendments, "
        "implementation, independent review, the structural pass and a "
        "fresh forecast.",
    ],
    "outstanding": [
        "1. Max rules on amendments 1\N{EN DASH}6 in \N{SECTION SIGN}16a, "
        "choosing one option each for blocker B1 (2015 male code 20; Part B "
        "PARTIAL), B2 (codes 90 and 92 in 2019\N{EN DASH}2023; Part B "
        "PARTIAL) and B3 (construction of the revised 2017 weight; Part B "
        "PARTIAL). An option that lets registration proceed before "
        "documents resolve B1 or B2 takes effect only if Max also ratifies "
        "the amendment to draft-3 lines 152\N{EN DASH}160 or 1391 that the "
        "option names; otherwise that blocker's hold governs. B3's option 1 "
        "likewise takes effect only if Max ratifies its amendment to "
        "draft-3 line 134. **Ruled 2026-09-30 (d637; "
        "\N{SECTION SIGN}16b):** B1 and B2 take option 3, the hold, with no "
        "amendment ratified; B3 takes option 1, with its amendment to "
        "draft-3 line 134 ratified; amendments 2\N{EN DASH}5 are ratified "
        "as written, and amendment 1's parts 1a\N{EN DASH}1c are read as "
        "ratified pending Max's confirmation (d745). **Ruled 2026-10-10 "
        "(d1090; \N{SECTION SIGN}16c), after PSID answered:** B1 takes "
        "option 2, with its amendment to draft-3 line 160 ratified, and B2 "
        "takes option 1, with its amendment to draft-3 lines 152, 154 and "
        "158 ratified for 2019\N{EN DASH}2023. This item stays open only "
        "for 1a\N{EN DASH}1c, until Max confirms.",
        "2. Each ruling is applied to the registries in its own reviewed "
        "commit. The d1090 commit (2026-10-10) replaced the eight B1 and B2 "
        "refusals with \N{SECTION SIGN}16c's exclusions and released their "
        "dependents. Until the registry commits for d637 (and, for code 88, "
        "d745) land, the 24 TO VERIFY records stay open and the "
        "2017\N{EN DASH}2023 P64/P65 records stay blocked.",
        "8. Complete the pre-registration structural, reconciliation and "
        "F17 component pass, including only the counts that the ratified B1 "
        "and B2 options name (under the 2026-10-10 ruling, the counts "
        "specified by \N{SECTION SIGN}16a options 1d-2 and 1e-1, each "
        "disclosed and deciding nothing; \N{SECTION SIGN}16c).",
    ],
    "execution": [
        "1. Resolve the proposed decisions and source-verification "
        "blockers. **Decisions: done (Max, d514, 2026-09-28, adopting every "
        "\N{SECTION SIGN}16 default).** Source-verification blockers remain "
        "for steps 2\N{EN DASH}5. **`u2-draft-4` amendments 1\N{EN DASH}6 "
        "(\N{SECTION SIGN}16a): ruled by Max on 2026-09-30 (d637; "
        "\N{SECTION SIGN}16b).** B3 is resolved by option 1. B1 and B2 were "
        "held until PSID answered; **Max ruled on them on 2026-10-10 "
        "(d1090; \N{SECTION SIGN}16c)**: B1 by option 2 and B2 by option 1, "
        "each an exclusion under a named disposition. This step stays open "
        "only because amendment 1's parts 1a\N{EN DASH}1c await Max's "
        "confirmation of the reading in \N{SECTION SIGN}16b (d745).",
    ],
}


def d1090_locations(spec):
    """The text of each place the d1090 record stands in ``spec``."""
    lines = spec.split("\n")
    return {
        "header_version": lines[2],
        "header_status": lines[3],
        "record": spec[spec.index("## 16c. ") : spec.index("## 17. ")],
        "outstanding": spec[spec.index("## 17. ") : spec.index("## 18. ")],
        "execution": spec[spec.index("## 20. ") :],
    }


def check_d1090_record(spec):
    """The semantic checks of the d1090 record, independent of any pin."""
    places = d1090_locations(spec)
    for place, clauses in D1090_CLAUSES.items():
        lines = places[place].split("\n")
        for clause in clauses:
            assert lines.count(clause) == 1, (place, clause[:60])
    record = places["record"]
    assert record.startswith(
        "## 16c. Max's ruling on blockers B1 and B2 (2026-10-10, d1090)\n"
    )
    for text in places.values():
        assert "decides whether" not in text
    assert (
        "The B1 and B2 holds stop registration" not in places["header_status"]
    )
    assert "B1 and B2 wait for the answers" not in places["outstanding"]
    assert "B1 and B2 stay on hold" not in places["execution"]


def test_section_16c_records_the_d1090_ruling():
    """§16c ratifies exactly the options and lines §16a states, and the
    header, §17 and §20 point to it; §16a and §16b are unchanged."""
    spec = (ROOT / SPEC).read_text(encoding="utf-8")
    starts = [
        spec.index(heading)
        for heading in ("## 16a. ", "## 16b. ", "## 16c. ", "## 17. ")
    ]
    assert starts == sorted(starts)
    for (heading, digest), end in zip(
        SECTION_SHA256.items(), starts[1:3], strict=True
    ):
        text = spec[spec.index(heading) : end]
        assert hashlib.sha256(text.encode()).hexdigest() == digest, heading
    proposals = spec[starts[0] : starts[1]]
    record = spec[starts[2] : starts[3]]
    for blocker, (start, option, disposition) in D1090_OPTIONS.items():
        block = proposals[proposals.index(start) :]
        block = block[: block.index("**Recommendation for B")]
        line = next(x for x in block.split("\n") if x.startswith(option))
        assert f"`{disposition}`" in line, blocker
        # The lines the record names are the lines the option amends.
        amended = re.search(r"Amends draft-3 lines? ([^.]+)\.", option)
        numbers = re.findall(r"\b\d{3,4}\b", amended.group(1))
        row = D1090_ROWS[blocker]
        assert row in record, blocker
        cell = row.split(" | ")[2]
        assert re.findall(r"\b\d{3,4}\b", cell) == numbers, blocker
        assert f"`{disposition}`" in row, blocker
    check_d1090_record(spec)


#: Mutations of the d1090 record that change what it says, each by
#: place: every one must fail ``check_d1090_record`` (review of e4dd350,
#: finding 2, and the counts of finding 1).
D1090_MUTATIONS = [
    ("record", "(ER32000 = 1)", "(ER32000 = 2)"),
    ("record", "code 20 is excluded from every row", "code 20 is kept in"),
    ("record", "Every 2019, 2021 or 2023 family", "Every 2023 family"),
    ("record", "a code-90 or code-92 person is", "a code-90 person is"),
    ("record", "and decides nothing.", "and decides whether to proceed."),
    ("record", "| Line 160 |", "| Line 154 |"),
    ("record", "for 2019\N{EN DASH}2023 only |", "for 2019 only |"),
    ("record", "and option 1d-2 inherits", "and option 1d-2 drops"),
    ("record", "sequence 1\N{EN DASH}20", "sequence 1\N{EN DASH}59"),
    ("record", "Lines 154 and 1391 are not", "Line 1391 is not"),
    ("record", "B1 option 2 (exclude", "B1 option 1 (exclude"),
    # The second review's accepted replacements (review of 8103881).
    (
        "record",
        "Option 1e-1 requires B2's count to be disclosed",
        "Option 1e-1 requires no count for B2 to be disclosed",
    ),
    (
        "record",
        "This record ratifies no additional B1 or B2 counting requirements; ",
        "",
    ),
    (
        "record",
        "pending Max's confirmation (d1242) before",
        "without waiting for Max (d1242) before",
    ),
    (
        "record",
        "The rules test those members",
        "The rules test only the target",
    ),
    (
        "record",
        "keeps that disposition",
        "instead takes the family-unit exclusion",
    ),
    (
        "outstanding",
        "including only the counts that the ratified B1 and B2 options name",
        "including any exploratory counts the builder requests",
    ),
    (
        "header_status",
        "Not registered or authorized for execution.",
        "Registered and authorized for execution.",
    ),
    (
        "execution",
        "of the reading in \N{SECTION SIGN}16b (d745).",
        "only if the structural pass finds nonzero exclusions.",
    ),
    (
        "header_version",
        "(d1090) as recorded in \N{SECTION SIGN}16c",
        "(d1090)",
    ),
    ("header_status", "B2 option 1, each", "B2 option 2, each"),
    ("outstanding", "and B2 takes option 1,", "and B2 takes option 2,"),
    ("outstanding", "each disclosed and deciding nothing", "each disclosed"),
    (
        "outstanding",
        "replaced the eight B1 and B2 refusals",
        "replaced the seven B1 and B2 refusals",
    ),
    (
        "execution",
        "B1 by option 2 and B2 by option 1",
        "B1 by option 1 and B2 by option 2",
    ),
]


@pytest.mark.parametrize(
    "place,old,new", D1090_MUTATIONS, ids=[m[1][:30] for m in D1090_MUTATIONS]
)
def test_the_d1090_checks_catch_each_mutation(place, old, new):
    spec = (ROOT / SPEC).read_text(encoding="utf-8")
    text = d1090_locations(spec)[place]
    assert old in text, (place, old)
    mutated = spec.replace(text, text.replace(old, new, 1), 1)
    assert mutated != spec
    with pytest.raises(AssertionError):
        check_d1090_record(mutated)


def test_part_b_verdicts_agree():
    """B1, B2 and B3 carry one verdict everywhere: PARTIAL."""
    research = RESEARCH.read_text(encoding="utf-8")
    rows = re.findall(
        r"^\| (B[123])\. [^|]+\| \*\*([A-Z ]+)\*\* \|", research, re.M
    )
    assert rows == [("B1", "PARTIAL"), ("B2", "PARTIAL"), ("B3", "PARTIAL")]
    headings = re.findall(r"^## [123]\. .*\(([A-Z ]+)\)$", research, re.M)
    assert headings == ["PARTIAL"] * 3
    assert "NOT DOCUMENTED ONLINE" not in research
    spec = (ROOT / SPEC).read_text(encoding="utf-8")
    section = spec[spec.index("## 16a. ") : spec.index("## 17. ")]
    verdicts = re.findall(r"Part B verdict: \*\*([A-Z ]+)\.\*\*", section)
    assert verdicts == ["PARTIAL"] * 3
    outstanding = spec[spec.index("## 17. ") : spec.index("## 18. ")]
    assert re.findall(r"Part B ([A-Z]+)\)", outstanding) == ["PARTIAL"] * 3
    weights = {
        e["id"]: e for e in registry.load_registry("weights")["entries"]
    }
    finding = weights["2017.cross_section_weight"]["part_b_finding"]
    assert finding.startswith("PARTIAL")
    master = MASTER.read_text(encoding="utf-8")
    assert (
        "| Revised 2017 individual-weight construction | TO VERIFY "
        "(adjudication A); Part B PARTIAL |" in master
    )
    assert "NOT DOCUMENTED ONLINE" not in master
    for blocker in (
        "2015 male code 20",
        "Code 90, 2015\N{EN DASH}2023",
        "Code 92, 2017\N{EN DASH}2023",
    ):
        status = re.search(rf"^\| {blocker} \| ([^|]+) \|", master, re.M)
        assert status.group(1).endswith("; Part B PARTIAL"), blocker
    # Verification pass 2: FAQ question 70 leaves room for a male code 20.
    roles = registry.load_registry("roles")
    for text in (master, json.dumps(roles), research):
        assert "places no male in 2015 code 20" not in text
    code_20 = next(
        e for e in roles["entries"] if e["id"] == "2015.relationship.20"
    )
    assert "FAQ question 70" in code_20["part_b_finding"]


def test_part_b_pointers_follow_dependencies(documents):
    """A finding that says 'See <registry>:<id>' points at its blocker."""
    for document in documents.values():
        for entry in document["entries"]:
            finding = entry.get("part_b_finding", "")
            if finding.startswith("See "):
                target = finding.split()[1].rstrip(".")
                assert target in entry["blocking_dependencies"], entry["id"]


def test_registry_prose_pages_are_cited():
    """Pages named in the 2017 weight's findings appear in its citations."""
    entry = next(
        e
        for e in registry.load_registry("weights")["entries"]
        if e["id"] == "2017.cross_section_weight"
    )
    cited = {c["page"] for c in entry["citations"] if "page" in c}
    for field in ("construction", "part_b_finding"):
        for found in re.finditer(
            r"\bpp?\. (\d+)(?:-(\d+))?((?:(?:,| and) \d+)*)", entry[field]
        ):
            pages = {int(found.group(1)), int(found.group(2) or 0)}
            pages |= {int(n) for n in re.findall(r"\d+", found.group(3))}
            assert pages - {0} <= cited, (field, found.group(0))


def test_released_dependencies(documents):
    for document in documents.values():
        for entry in document["entries"]:
            assert not RELEASED & set(entry.get("blocking_dependencies", []))
    pension = {e["id"]: e for e in documents["pension"]["entries"]}
    # d1090 released the 2015 spouse slot with B1 (amendment 5c).
    for wave in registry.U2_SOURCE_WAVES:
        entry = pension[f"{wave}.route.respondent_slots"]
        assert "blocking_dependencies" not in entry, wave
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
    assert "**1768 RESOLVED; 0 REFUSED; 24 TO VERIFY**" in text
    # Each per-route row states exactly its entry's remaining blocking
    # dependencies (review of 8103881, finding 3: d1090 released 554).
    sentences = dict(
        re.findall(
            r"^\| `([a-z]+:[^`]+)` \| [^\n]*?(?: Application also refuses "
            r"pending ([^|]*?)\.)? \| `[^\n]*$",
            text,
            re.M,
        )
    )
    assert set(sentences) == set(expected)
    for name, document in documents.items():
        for entry in document["entries"]:
            stated = sentences[f"{name}:{entry['id']}"]
            assert stated == ", ".join(
                entry.get("blocking_dependencies", [])
            ), (name, entry["id"])
    assert text.count("Application also refuses pending") == sum(
        bool(e.get("blocking_dependencies"))
        for d in documents.values()
        for e in d["entries"]
    )
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
    assert len(pinned_files) == len(set(pinned_files)) == 24
    assert not set(pinned_files) & {s["file"] for s in manifest["sources"]}
    for pinned in manifest["pinned_elsewhere"]:
        assert re.fullmatch(r"[0-9a-f]{64}", pinned["sha256"])
        assert set(pinned["blockers"]) <= blockers and pinned["blockers"]
        assert pinned["file"].startswith(("tests/", "PSID/")), pinned
        if pinned["file"].startswith("tests/"):
            # In the repository: hash it here. PSID/ files are hashed by
            # test_psid_research_sources.py against the staged root.
            raw = (ROOT / pinned["file"]).read_bytes()
            assert len(raw) == pinned["bytes"]
            assert hashlib.sha256(raw).hexdigest() == pinned["sha256"]
        # Wherever a registry pins the same file, the digests agree, and a
        # note that names a pinning registry is true.
        for digest in registry_hashes.get(pinned["file"], {}).values():
            assert digest == pinned["sha256"], pinned["file"]
        for claimed in re.findall(
            r"Pinned by the (\w+) registry", pinned["note"]
        ):
            assert claimed in registry_hashes[pinned["file"]], pinned["file"]
        if "Not pinned by any registry" in pinned["note"]:
            assert pinned["file"] not in registry_hashes, pinned["file"]
    assert "cross_sec_weights_23.pdf" in " ".join(pinned_files)
    # Every document the research record quotes is archived or pinned here.
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
        for quote in manifest["research_quotes"] + manifest["spec_quotes"]
        if quote["file"].endswith("FAQ_20260813.html")
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
    # The prose names the same saved-file lines as the citations.
    for entry in roles.values():
        stated = [
            int(n)
            for n in re.findall(r"saved-file line (\d+)", json.dumps(entry))
        ]
        cited = [
            c["line"]
            for c in entry["citations"]
            if c["file"].endswith("FAQ_20260813.html")
        ]
        assert sorted(stated) == sorted(set(stated)) and set(stated) <= set(
            cited
        ), entry["id"]
