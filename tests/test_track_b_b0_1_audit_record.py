"""Pin the Track B B0.1 audit record to its frozen protocol and counts.

The audit (docs/design/track_b_b0_1_audit.md) quotes counts and power
figures from docs/design/track_b_b0_1_counts.json, which the count script
wrote once from the protocol-freeze commit. These tests read only those
two committed files and the script source.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import track_b_b0_1_counts as script  # noqa: E402

AUDIT = ROOT / "docs" / "design" / "track_b_b0_1_audit.md"
COUNTS = ROOT / "docs" / "design" / "track_b_b0_1_counts.json"
SCRIPT = ROOT / "scripts" / "track_b_b0_1_counts.py"

#: The commit that froze the protocol before any count ran.
FREEZE_COMMIT = "e51216fd59230e7eab3992ee22d7c0bdf61bcca8"
#: SHA-256 of the protocol block at FREEZE_COMMIT, markers included.
PROTOCOL_SHA256 = (
    "345c82ee74dcf89f2ae7021751d71ec17992e30d7aa4a1fff9060dd4fd707f89"
)
BEGIN, END = "<!-- protocol:begin -->", "<!-- protocol:end -->"


@pytest.fixture(scope="module")
def record():
    return json.loads(COUNTS.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def audit_text():
    return AUDIT.read_text(encoding="utf-8")


def test_protocol_block_is_byte_identical_to_the_freeze(audit_text):
    start = audit_text.index(BEGIN)
    stop = audit_text.index(END) + len(END)
    block = audit_text[start:stop]
    assert hashlib.sha256(block.encode()).hexdigest() == PROTOCOL_SHA256
    assert audit_text.count(BEGIN) == 1 and audit_text.count(END) == 1


def test_counts_were_written_by_the_frozen_script(record):
    assert record["schema"] == script.SCHEMA
    assert record["repository_head"] == FREEZE_COMMIT
    assert record["worktree_clean"] is True
    digest = hashlib.sha256(SCRIPT.read_bytes()).hexdigest()
    assert record["script_sha256"] == digest, (
        "the count script changed after the recorded run; a change is a "
        "new protocol version"
    )


def test_record_declares_no_outcome_was_computed(record):
    assert record["outcome_blind"] == {
        "b2_cell_or_floor_computed": False,
        "earnings_levels_read_into_counts": False,
        "projection_run": False,
        "zero_or_positive_earnings_counted": False,
    }


def test_nawi_prefix_matches_the_repository_pin(record):
    nawi = record["nawi"]
    assert nawi["checked"] is True
    assert nawi["matches_repository_pin"] is True
    assert nawi["maximum_admitted_key_year"] == script.BOUNDARY_YEAR
    assert nawi["fit_decade_keys_present"] is True


def test_read_set_covers_every_family_wave_through_2015(record):
    read_set = record["b2_read_set_sha256"]
    waves = [
        wave
        for wave in script.family.FAMILY_WAVES
        if wave - script.WAVE_OFFSET <= script.HORIZON_YEARS[-1]
    ]
    assert len(read_set) == 2 * len(waves) + 2
    for wave in waves:
        assert any(key.startswith(f"family/{wave}/") for key in read_set)
    for digest in read_set.values():
        assert len(digest) == 64
    for name, digest in record["psid_files_opened_sha256"].items():
        assert read_set[name] == digest


def test_counts_match_both_selector_ledgers(record):
    counts = record["counts"]
    by_period = {
        year: counts["scored_support"][year]["scored_rows"]
        for year in ("2010", "2012", "2014")
    }
    for ledger in record["ledger_support_counts"].values():
        assert ledger["anchor_wave"] == counts["anchor_wave"]
        assert ledger["n_full_anchor"] == counts["full_anchor_persons"]
        assert ledger["n_domain"] == counts["domain_persons"]
        assert ledger["truth_support_rows"] == counts["scored_rows_total"]
        assert ledger["truth_support_rows_by_period"] == by_period
        assert (
            ledger["endpoint_support_rows"]
            == counts["level_cells"]["pooled"]["rows"]
        )


def test_recorded_accounting_identities_hold(record):
    counts = record["counts"]
    domain = counts["domain_persons"]
    for year, labels in counts["domain_dispositions"].items():
        assert set(labels) == set(script.DISPOSITIONS)
        assert sum(labels.values()) == domain
        assert (
            labels["scored"] == counts["scored_support"][year]["scored_rows"]
        )
    for summary in (
        *counts["level_cells"].values(),
        *counts["change_pairs"].values(),
    ):
        assert summary["cluster_worst_n_eff"] <= summary["kish_n_eff"]
        assert summary["kish_n_eff"] <= summary["rows"]


def test_power_record_recomputes_exactly(record):
    assert script.power_record(record["counts"]) == record["power"]


def _thousands(value: float) -> str:
    return f"{round(value):,}"


def test_audit_quotes_the_recorded_figures(record, audit_text):
    counts = record["counts"]
    power = record["power"]
    prose = " ".join(audit_text.split())
    quoted = [
        counts["full_anchor_persons"],
        counts["domain_persons"],
        counts["domain_by_role"]["head"],
        counts["domain_by_role"]["spouse"],
        counts["domain_by_anchor_wave_age"]["under_25"],
        counts["domain_by_anchor_wave_age"]["65_plus"],
        counts["level_cells"]["pooled"]["rows"],
        counts["level_cells"]["pooled"]["kish_n_eff"],
        counts["level_cells"]["pooled"]["cluster_worst_n_eff"],
        counts["level_cells"]["prime"]["kish_n_eff"],
        counts["level_cells"]["older"]["kish_n_eff"],
        counts["level_cells"]["prime"]["cluster_worst_n_eff"],
        counts["level_cells"]["older"]["cluster_worst_n_eff"],
        counts["change_pairs"]["pooled_one_step"]["kish_n_eff"],
        counts["change_pairs"]["pooled_two_step"]["kish_n_eff"],
    ]
    for year in ("2010", "2012", "2014"):
        quoted.append(counts["scored_support"][year]["scored_rows"])
    for year in ("2012", "2014"):
        quoted.extend(
            value
            for value in counts["domain_dispositions"][year].values()
            if value >= 1_000
        )
    limits = power["section_5_3_limits_on_b2_support"]
    for m in ("1", "6", "16"):
        quoted.append(
            limits[m]["by_cohort"]["prime"][
                "participation_required_n_eff_worst_p"
            ]
        )
        quoted.append(
            limits[m]["persistence"]["lag1_pooled_one_step"][
                "required_positive_pair_n_eff"
            ]
        )
    missing = [
        _thousands(value) for value in quoted if _thousands(value) not in prose
    ]
    assert not missing, missing

    rule = power["m6_floor_rule"]
    for m, text in (("6", "0.9742"), ("16", "0.8590")):
        assert f"{rule['p_gate_by_family_size'][m]:.4f}" == text
        assert text in prose
    assert f"at most {rule['max_uncapped_cells_at_0_90']} uncapped" in (
        prose.lower()
    )
