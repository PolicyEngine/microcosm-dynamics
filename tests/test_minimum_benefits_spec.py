"""Consistency checks for the exercise 4 (Track M) specification.

``docs/design/minimum_benefits_comparison.md`` is read by downstream code
through its machine-readable JSON block (section 19).  These tests hold
that block to the code (the options, the policy defaults, the registered
rows, the cells, the labels and the structural-count universe), check that
the committed block, whose ``blocked_by`` the registered-commit edit of
2026-09-27 emptied, passes the registered-run gate while any block that
names a blocker is refused, and recompute the specification's INVENTED
worked cases.  They use only the document and the code: no PSID
value, no model output and no comparator value.  One test also hashes the
statute capture the block pins, when its evidence folder is present; no
test opens or hashes the comparator seal, whose hash the text records.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.min_benefit_track_m import (
    OUTPUT_LABELS,
    rules,
    structure,
    tabulation,
)
from populace_dynamics.min_benefit_track_m import policy as pol
from populace_dynamics.min_benefit_track_m import specification as spec

SPEC_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "design"
    / "minimum_benefits_comparison.md"
)
#: ``EVID`` of the specification: the evidence folder outside this checkout.
EVIDENCE = (
    Path.home() / "microcosm-launch-evidence" / "dynasim-parity-20260909"
)
#: Every blocker the section 19 block named in the file's history, in the
#: order each first appeared (read from every commit of this file,
#: 2026-09-27); each left ``blocked_by`` when it was resolved (section 23).
FORMER_BLOCKERS = (
    "max_ruling_d219_open",
    "census_aged_thresholds_not_captured_m2",
    "statute_413_415_not_captured_m2",
    "person_level_social_security_readers_m3",
    "beneficiary_cohort_m4",
    "realized_careers_m5",
    "tabulation_m8",
    "issue_42_registration_absent",
    "independent_check_of_m1_draft_2_then_ratification_by_merge",
    "census_thresholds_before_2003_if_m4_needs_them",
    "statute_413_415_402_423_not_captured_m2",
    "tabulation_m8_and_dry_run_m10",
    "registration_package_m10_needs_m3_to_m5",
    "independent_check_of_m1_draft_2_and_the_m3_to_m5_readings_then_"
    "ratification_by_merge",
    "census_thresholds_1982_to_2002_needed_by_m4_not_captured",
    "registration_package_m10_needs_the_comparator_seal_hash",
    "independent_review_of_the_d430_sensitivity_build_m1_draft_3_then_"
    "ratification_by_merge",
    "census_threshold_1990_needed_by_the_d430_sensitivity_not_captured",
)
#: The two ``m1-ratified-1`` was ratified with; the registered-commit edit
#: (2026-09-27) dropped both.
BLOCKERS_AT_RATIFICATION = (
    "registration_package_m10_needs_the_comparator_seal_hash",
    "issue_42_registration_absent",
)
#: The comparator seal and the SHA-256 of its bytes, computed by the
#: orchestrating session on 2026-09-27 (section 18 item 3).  No test opens
#: or hashes the seal: builder lanes do not open it.
COMPARATOR_SEAL = "EVID/exercise4-comparator-seal-20260924.json"
COMPARATOR_SEAL_SHA256 = (
    "112dcf427671da5af54d436d10719f195c65596df42fcdb8ad0e9fe54f75e63c"
)


@pytest.fixture(scope="module")
def text() -> str:
    return SPEC_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def block(text: str) -> dict:
    blocks = re.findall(r"```json\n(.*?)\n```", text, re.DOTALL)
    assert len(blocks) == 1
    parsed = json.loads(blocks[0])
    assert parsed == spec.m1_parameter_block(SPEC_PATH)
    return parsed


def test_block_identity_and_status(block):
    assert spec.M1_SPECIFICATION_PATH == SPEC_PATH
    assert block["specification"] == pol.SPECIFICATION_ID
    assert block["version"] == "m1-ratified-1"
    assert block["status"] == "ratified_frozen"
    assert spec.unratified_fields(block) == []
    assert block["claim_class"] == {
        "ruled": pol.CLAIM_CLASS,
        "decision_record": pol.DECISION_RECORD,
        "item": 2,
    }
    assert block["acceptance_rule"] is None
    assert block["labels"] == list(OUTPUT_LABELS)
    assert block["target"]["comparator_values"] == (
        "sealed_comparator_side_not_opened_by_builder"
    )
    # Every blocker the block ever named is resolved: d219 was ruled, M3-M5,
    # M8 and the M10 dry run are built, the independent checks are done,
    # the Census thresholds (2003-2022, then the years before 2003 and
    # 1990), and the statute are captured, and the registration package
    # has the comparator seal's hash.  The registration names this commit
    # (section 18 item 3), so its block lists none (section 19).
    assert set(BLOCKERS_AT_RATIFICATION) <= set(FORMER_BLOCKERS)
    for resolved in FORMER_BLOCKERS:
        assert resolved not in block["blocked_by"], resolved
    assert block["blocked_by"] == []
    # the cleared blocker's year is in the recorded capture (another test
    # holds the recorded capture to the loader's)
    census = block["sources"]["census_thresholds"]
    assert 1990 in census["captured_years"]
    assert 1990 not in census["years_not_captured"]


def test_the_block_records_the_census_and_statute_captures(block):
    """Section 19's sources record the 1982-2022 Census capture as the
    loader reads it, with the capture it replaced and its cross-check,
    and the statute capture M2 made (evidence, not read by code)."""

    from populace_dynamics.min_benefit_track_m import thresholds

    census = block["sources"]["census_thresholds"]
    loaded = rules.load_aged_thresholds().source
    assert census["file"] == loaded["path"]
    assert census["sha256"] == loaded["sha256"]
    assert census["sha256"] == thresholds.TRACK_M_THRESHOLDS_SHA256
    assert census["years"] == loaded["years"] == [1982, 2022]
    assert census["captured_years"] == loaded["captured_years"]
    assert census["captured_years"] == list(thresholds.TRACK_M_THRESHOLD_YEARS)
    assert (
        sorted(set(range(1982, 2023)) - set(census["captured_years"]))
        == census["years_not_captured"]
    )
    assert census["replaces"]["sha256"].startswith("65bbcd83")
    # the pin before 1990 was captured (2026-09-26), and why it moved
    assert census["previous_pin"] == {
        "sha256": (
            "4493b8d5823ea12912212d892f98ef4777098ce34b01857cedc35d444a8b99cd"
        ),
        "lacked": [1990],
        "superseded_on": "2026-09-26",
        "why": "own_receipt_reading_d430_needs_1990",
    }
    assert census["previous_pin"]["sha256"] != census["sha256"]
    assert set(census["previous_pin"]["lacked"]) <= set(
        census["captured_years"]
    )
    assert census["internet_archive_copies"] == ["thresh95.xlsx"]
    root = SPEC_PATH.parents[2]
    import hashlib

    crosscheck = root / census["crosscheck"]["file"]
    assert (
        hashlib.sha256(crosscheck.read_bytes()).hexdigest()
        == census["crosscheck"]["sha256"]
    )
    statute = block["sources"]["statute"]
    assert statute["status"] == "captured_m2"
    assert statute["sections"] == [
        "42 USC 413",
        "42 USC 415",
        "42 USC 402",
        "42 USC 423",
    ]
    assert statute["findings_for_ratification"] == [
        "F1",
        "F2",
        "F3a",
        "F3b",
        "F4",
        "O1",
    ]
    assert len(statute["reading"]["sha256"]) == 64


def test_the_statute_pins_are_the_captured_files(block, text):
    """Section 19's statute pins are the files in the capture folder, and
    section 2 prints the same short hashes (independent review of
    2026-09-25: the lane corrected ``READING.md`` after writing the pins,
    so both pins named superseded bytes).  The folder is outside this
    checkout; without it only the section 2 check runs."""

    statute = block["sources"]["statute"]
    sums = statute["sha256sums_sha256"]
    reading = statute["reading"]["sha256"]
    sources = text[text.index("## 2. Sources") : text.index("## 3. Policy")]
    assert f"`SHA256SUMS` `{sums[:8]}…`" in sources
    assert f"`READING.md` (`{reading[:8]}…`)" in sources
    folder = EVIDENCE / statute["folder"]
    if not folder.is_dir():
        pytest.skip("the statute capture is outside this checkout")
    listing = (folder / "SHA256SUMS").read_bytes()
    assert hashlib.sha256(listing).hexdigest() == sums
    readme = (folder / statute["reading"]["file"]).read_bytes()
    assert hashlib.sha256(readme).hexdigest() == reading
    listed = {}
    for line in listing.decode("utf-8").splitlines():
        digest, name = line.split()
        listed[name] = digest
    assert statute["reading"]["file"] in listed
    for name, digest in listed.items():
        actual = hashlib.sha256((folder / name).read_bytes()).hexdigest()
        assert actual == digest, name


def test_statistic_and_uncertainty_are_the_tabulations(block):
    assert block["statistic"] == tabulation.STATISTIC
    assert block["uncertainty"] == tabulation.UNCERTAINTY
    assert block["statistic"]["id"] == tabulation.STATISTIC_ID
    assert block["uncertainty"]["design_se"]["stratum"] == (
        block["population"]["design"]["stratum"]
    )
    assert block["uncertainty"]["design_se"]["cluster"] == (
        block["population"]["design"]["cluster"]
    )
    assert block["uncertainty"]["design_se"]["frame"].endswith(
        block["population"]["weight"]
    )


def test_status_line_records_the_ratification_and_every_ruling(text):
    status = " ".join(text.split("- **Specification:**")[0].split())
    assert "ratified and frozen" in status
    assert "Nothing here is ratified" not in status
    for record in ("d219", "d279", "d280", "d430"):
        assert record in status
    assert "ruled 2026-09-24 21:44" in status
    assert "track-m-5-review-20260926.md" in status
    assert "refuses a block that lists any blocker" in status
    assert "pending" not in status


def test_no_d219_item_is_left_pending_in_the_text(text):
    flat = " ".join(text.split())
    assert "pending)" not in flat
    assert "d219, open" not in flat
    for item in (1, 2, 3, 5, 6, 7, 8):
        assert f"d219 item {item}, accepted 2026-09-24" in flat, item


def test_block_matches_the_code(block):
    assert spec.specification_code_check(block) == {
        "consistent": True,
        "mismatches": [],
    }
    assert block["snapshot"] == {
        "wave": pol.SNAPSHOT_WAVE,
        "income_year": pol.SNAPSHOT_INCOME_YEAR,
    }
    assert block["cells"]["headline"] == {"option": 2, "row": "all"}


def test_population_matches_the_structure_module(block):
    population = block["population"]
    assert population["weight"] == structure.ANCHOR_2023.weight_variable
    assert population["born_on_or_before"] == structure.LAST_BIRTH_YEAR
    assert population["receipt"] == {
        "person_level": structure.SOCIAL_SECURITY_2023["amount"][0],
        "family_file": [
            structure.FAMILY_2023["rp_amount"][0],
            structure.FAMILY_2023["spouse_amount"][0],
        ],
    }
    assert population["design"] == {"stratum": "ER31996", "cluster": "ER31997"}


def test_every_ruling_is_recorded_as_the_code_records_it(block):
    assert block["decisions_awaiting_max"] == {}
    decisions = block["decisions"]
    assert decisions == spec.expected_decisions()
    assert decisions["ruled_by"] == "Max"
    assert list(decisions)[1:] == list(pol.MAX_RULINGS)
    policy = pol.TrackMPolicy()
    for name in spec.ruled_fields():
        assert decisions[name]["ruling"] == spec.decision_value(policy, name)
    assert spec.d219_decision_fields() == tuple(
        field for _, (field, _) in sorted(pol.d219_items().items())
    )
    for name in spec.d219_decision_fields():
        assert decisions[name]["decision_record"] == "d219"
        assert decisions[name]["ruled_on"] == "2026-09-24"
    assert decisions["covered_earnings_rule"]["decision_record"] == "d280"
    assert decisions["census_threshold_download"]["decision_record"] == (
        "d279"
    )
    for name in ("own_receipt_reading", "odd_year_source", "onset_year_rule"):
        assert decisions[name]["decision_record"] == "d430"
        assert decisions[name]["ruled_on"] == "2026-09-26"
        assert decisions[name]["ruling_text"] == pol.D430_RULING
    assert decisions["own_receipt_reading"]["sensitivity_registered_as"] == (
        pol.OWN_RECEIPT_SENSITIVITY_ID
    )


def test_the_committed_block_authorizes_the_registered_run(block):
    """The registered commit's block (section 18 item 3, section 19): ratified,
    nothing awaiting Max, ``blocked_by`` empty, every ruling equal to the
    code's, the block equal to the code.  The gate accepts it under the
    default configuration, given or not, and still refuses a
    configuration that departs from a ruling."""

    assert spec.unratified_fields(block) == []
    assert spec.specification_code_check(block) == {
        "consistent": True,
        "mismatches": [],
    }
    assert spec.check_specification_for_registered_run(block) is None
    assert (
        spec.check_specification_for_registered_run(block, pol.TrackMPolicy())
        is None
    )
    with pytest.raises(ValueError, match="departs"):
        spec.check_specification_for_registered_run(
            block, pol.policy_for_row("MS1")
        )


def _ratified(block: dict) -> dict:
    """The ratified text changes the status and version only (R1)."""

    ratified = json.loads(json.dumps(block))
    ratified["status"] = "ratified_frozen"
    ratified["version"] = "m1-ratified-1"
    return ratified


def _blocked(block: dict, blockers=BLOCKERS_AT_RATIFICATION) -> dict:
    """The committed block with ``blocked_by`` naming ``blockers``: by
    default the block as ratified, before the registered-commit edit."""

    return {**_ratified(block), "blocked_by": list(blockers)}


def test_a_block_still_listing_blockers_authorizes_nothing(block):
    """The gate still refuses a block that names any blocker, or has no
    list: the block as ratified (the registration package and the
    registration), each of its two blockers alone, every blocker the
    block ever named, and a list that is not a list."""

    assert _ratified(block) == block
    for blockers in (
        BLOCKERS_AT_RATIFICATION,
        *((name,) for name in FORMER_BLOCKERS),
    ):
        with pytest.raises(ValueError, match="still blocked by"):
            spec.check_specification_for_registered_run(
                _blocked(block, blockers)
            )
    unlisted = {k: v for k, v in block.items() if k != "blocked_by"}
    with pytest.raises(ValueError, match="no blocked_by"):
        spec.check_specification_for_registered_run(unlisted)
    with pytest.raises(ValueError, match="still blocked by"):
        spec.check_specification_for_registered_run(
            {**block, "blocked_by": "none"}
        )


@settings(max_examples=150, deadline=None)
@given(
    st.one_of(
        st.lists(st.text(max_size=60), min_size=1, max_size=4),
        st.none(),
        st.booleans(),
        st.integers(),
        st.text(),
        st.dictionaries(st.text(max_size=8), st.text(max_size=8)),
        st.tuples(st.text(max_size=8)),
        st.just(()),
    )
)
def test_property_the_gate_passes_only_an_empty_blocked_by_list(blocked_by):
    """Invariant: holding every other field at the committed block, the
    gate accepts ``blocked_by`` exactly when it is the empty list.  Any
    non-empty list, and anything that is not a list (``None``, a string, a
    mapping, a tuple, even an empty one), is refused."""

    committed = spec.m1_parameter_block(SPEC_PATH)
    spec.check_specification_for_registered_run(committed)
    with pytest.raises(ValueError, match="still blocked by"):
        spec.check_specification_for_registered_run(
            {**committed, "blocked_by": blocked_by}
        )


def test_the_gate_checks_every_step(block):
    ratified = {**_ratified(block), "blocked_by": []}
    spec.check_specification_for_registered_run(ratified)
    referee = {**ratified, "version": "m1-ratified-after-referee-1"}
    with pytest.raises(ValueError, match="authorizes no"):
        spec.check_specification_for_registered_run(referee)
    pending = {**ratified, "decisions_awaiting_max": {"order": {}}}
    with pytest.raises(ValueError, match="awaiting Max"):
        spec.check_specification_for_registered_run(pending)
    unruled = {**ratified, "decisions": {}}
    with pytest.raises(ValueError, match="no ruling"):
        spec.check_specification_for_registered_run(unruled)
    missing = json.loads(json.dumps(ratified))
    del missing["decisions"]["covered_earnings_rule"]
    with pytest.raises(ValueError, match="covered_earnings_rule"):
        spec.check_specification_for_registered_run(missing)
    # A block recording another ruling than the code's is refused ...
    ruled_other = json.loads(json.dumps(ratified))
    ruled_other["decisions"]["order"]["ruling"] = pol.ORDER_CUT_AFTER_FLOOR
    with pytest.raises(ValueError, match="differ from the code's record"):
        spec.check_specification_for_registered_run(ruled_other)
    # ... and so is a configuration that departs from a ruling.
    with pytest.raises(ValueError, match="departs"):
        spec.check_specification_for_registered_run(
            ratified, pol.policy_for_row("MS2")
        )
    # A frozen choice the configuration changes makes the block differ.
    with pytest.raises(ValueError, match="differ"):
        spec.check_specification_for_registered_run(
            ratified, pol.policy_for_row("MS6")
        )
    # So does a statistic or an uncertainty other than the tabulation's.
    for key, change in (
        ("statistic", {"n_scored": True}),
        ("uncertainty", {"draws": 20}),
    ):
        other = {**ratified, key: {**ratified[key], **change}}
        with pytest.raises(ValueError, match=key):
            spec.check_specification_for_registered_run(other)


def test_the_decisions_section_lists_every_ruling(text):
    section = text.split("## 20. Decisions (ruled by Max")[1].split("## 21.")[
        0
    ]
    for record in ("d219", "d279", "d280", "d430"):
        assert record in section
    for name in pol.MAX_RULINGS:
        assert f"`{name}`" in section, name
    frozen = section.split("**Frozen by this version")[1]
    for phrase in (
        "statutory computation years",
        "statutory death computation",
        "$50 a quarter",
    ):
        assert phrase in frozen
    # d430 now rules the odd-year source and the onset year (kept
    # knowingly), so the frozen list no longer holds them
    ruled = section.split("**Frozen by this version")[0]
    for phrase in (
        "kept knowingly",
        pol.D430_RULING,
        pol.OWN_RECEIPT_SENSITIVITY_ID,
    ):
        assert phrase in " ".join(ruled.split()), phrase
    assert "next-wave labor income" not in frozen


def test_the_referee_section_records_every_required_change(text):
    section = text.split("## 21. Referee pass")[1].split("## 22.")[0]
    for number in range(1, 11):
        assert f"| R{number}. " in section, number
    assert "Declined in part" in section
    for question in range(1, 11):
        assert f"| Q{question} |" in section, question


def test_invented_cases_in_the_text_match_the_code(text):
    section = text.split("## 16. Invented worked cases")[1].split("## 17.")[0]
    thresholds = rules.AgedThresholds({2010: 10_000.0}, {"kind": "INVENTED"})
    cases = {
        "A": (600.0, 30, None),
        "B": (600.0, 9, None),
        "C": (900.0, 40, None),
        "D": (500.0, 15, 1948 + 44),
        "H": (953.0, 40, None),
        "I": (700.0, 20, None),
    }
    for name, (pia, years, onset) in cases.items():
        worker = rules.WorkerInputs(
            pia=pia,
            work_years=years,
            first_pia_year=2010,
            threshold_year=2010,
            birth_year=1948,
            di_onset_year=onset,
        )
        two = rules.evaluate_worker(worker, 2, thresholds=thresholds, nawi={})
        one = rules.evaluate_worker(worker, 1, thresholds=thresholds, nawi={})
        relative = 100 * rules.relative_to_option_1(two, one)
        row = next(
            line
            for line in section.splitlines()
            if line.startswith(f"| {name}.")
        )
        sign = "+" if relative >= 0 else "−"
        assert f"{sign}{abs(relative):.2f}%" in row, name
        if two.minimum:
            assert f"${two.minimum:,.2f}" in row, name


def test_the_block_registers_d430s_sensitivity(block):
    """Cos d430's unscored sensitivity is registered in the block, held to
    the code, and the gate refuses a block that drops or changes it."""

    assert block["sensitivities"] == pol.SENSITIVITIES
    assert list(block)[list(block).index("decisions") + 1] == "sensitivities"
    ratified = {**_ratified(block), "blocked_by": []}
    spec.check_specification_for_registered_run(ratified)
    dropped = {k: v for k, v in ratified.items() if k != "sensitivities"}
    with pytest.raises(ValueError, match="sensitivities"):
        spec.check_specification_for_registered_run(dropped)
    changed = json.loads(json.dumps(ratified))
    changed["sensitivities"][pol.OWN_RECEIPT_SENSITIVITY_ID]["scored"] = True
    with pytest.raises(ValueError, match="sensitivities"):
        spec.check_specification_for_registered_run(changed)
    without = json.loads(json.dumps(ratified))
    del without["decisions"]["own_receipt_reading"]
    with pytest.raises(ValueError, match="own_receipt_reading"):
        spec.check_specification_for_registered_run(without)


def test_the_text_records_d430s_sensitivity(text):
    """Sections 4c, 11, 14 and 19 describe the sensitivity; section 15
    names d430's deltas; section 23 records m1-draft-3 and
    m1-ratified-1, and section 20 the ratification."""

    from populace_dynamics.min_benefit_track_m import pipeline

    flat = " ".join(text.split())

    def section(start: str, end: str) -> str:
        return " ".join(text.split(start)[1].split(end)[0].split())

    for start, end in (
        ("### 4c. As built", "## 5. Years of coverage"),
        ("## 11. Statistic", "## 12. Uncertainty"),
        ("## 14. Registered rows", "## 15. Named deltas"),
        ("## 19. Machine-readable parameter block", "```json"),
    ):
        body = section(start, end)
        assert pol.OWN_RECEIPT_SENSITIVITY_ID in body, start
        assert "d430" in body, start
    deltas = section("## 15. Named deltas", "## 16. Invented worked cases")
    for name in ("F2", "F3a", "F3b", "O1"):
        assert f"**{name}**" in deltas, name
        assert any(
            delta.startswith(f"{name}: ") for delta in pipeline.NAMED_DELTAS
        ), name
    assert "F1" in deltas and "(j)" in deltas
    changelog = section("## 23. Changelog", "\n## 24")
    assert "`m1-draft-3`" in changelog
    assert "- `m1-ratified-1` (" in changelog
    assert "m1-ratified-1" in flat.split("- **Specification:**")[1][:200]
    assert "**Ratification record.**" in flat
    assert "This version is not that text" not in flat


def test_the_registered_commit_edit_is_recorded(text, block):
    """The registered-commit edit (2026-09-27; sections 18-20 and 23).

    The version and status stand.  Section 18 item 3 records the
    comparator seal's hash for the registration package, and every
    SHA-256 the text gives beside the seal's name, and every short form
    of it, is that hash.  The header, section 18 item 3 and section 19
    say the gate now accepts the block and that Registration 17 names the
    commit that carries the edit; section 23 lists the change.  Nothing
    here opens or hashes the seal.
    """

    flat = " ".join(text.split())

    def section(start: str, end: str) -> str:
        return " ".join(text.split(start)[1].split(end)[0].split())

    assert (block["version"], block["status"]) == (
        "m1-ratified-1",
        "ratified_frozen",
    )
    assert re.fullmatch(r"[0-9a-f]{64}", COMPARATOR_SEAL_SHA256)
    item_3 = section("3. **M10's registration package", "4. **Ratification")
    assert "complete (2026-09-27)" in item_3
    assert f"`{COMPARATOR_SEAL}`" in item_3
    assert f"`{COMPARATOR_SEAL_SHA256}`" in item_3
    assert "did not open the seal" in item_3
    assert "neither opened nor hashed the seal" in item_3
    assert "Registration 17" in item_3
    for name in BLOCKERS_AT_RATIFICATION:
        assert f"`{name}` leaves `blocked_by`" in item_3, name
    # every hash beside the seal's name, and every short form, is the one
    seal_name = COMPARATOR_SEAL.split("/")[-1]
    for after in flat.split(seal_name)[1:]:
        for digest in re.findall(r"\b[0-9a-f]{64}\b", after[:400]):
            assert digest == COMPARATOR_SEAL_SHA256
    for short in re.findall(r"\b112dcf4[0-9a-f]*", flat):
        assert COMPARATOR_SEAL_SHA256.startswith(short), short
    assert flat.count(COMPARATOR_SEAL_SHA256) == 1
    # the gate's verdict and the registration, where the text states them
    status = " ".join(text.split("- **Specification:**")[0].split())
    prose_19 = section("## 19. Machine-readable parameter block", "```json")
    for where, body in (("header", status), ("section 19", prose_19)):
        assert "registered-commit edit of 2026-09-27" in body, where
        assert "Registration 17" in body, where
    assert "the gate accepts this block" in prose_19
    assert "still names" not in prose_19
    assert "this block still lists" not in status
    entry = section(
        "- `m1-ratified-1`, registered-commit edit (2026-09-27)", "\n## 24"
    )
    for fragment in (
        "`blocked_by` is empty",
        "registration_package_m10_needs_the_comparator_seal_hash",
        "issue_42_registration_absent",
        "Registration 17",
        "112dcf42",
    ):
        assert fragment in entry, fragment
