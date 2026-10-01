"""Pin the B0.1 addendum to its frozen protocol, constants and figures.

The addendum (docs/design/track_b_b0_1_addendum.md) freezes elements 5-9
for B2 and carries protocol v2, which was committed and pushed before any
planning value was computed. These tests read the addendum, the two
addendum scripts and the frozen count record. They read no PSID file, no
selection ledger and no file on the audit's Q6 exclusion list.
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import track_b_b0_1_addendum_power as power  # noqa: E402
import track_b_b0_1_planning_values as pv  # noqa: E402

ADDENDUM = ROOT / "docs" / "design" / "track_b_b0_1_addendum.md"
GATE_LEAK = ROOT / "docs" / "design" / "track_b_b0_1_gate_leak_check.txt"

#: SHA-256 of the protocol-v2 block at the freeze commit, markers included.
PROTOCOL_V2_SHA256 = (
    "2a1681cdb3b6e28f30a8c1a319895b95f25c2fb27a175c50ded8a196d8488fe9"
)


@pytest.fixture(scope="module")
def text():
    return ADDENDUM.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def prose(text):
    return " ".join(text.split())


@pytest.fixture(scope="module")
def protocol(text):
    start = text.index(pv.PROTOCOL_BEGIN)
    stop = text.index(pv.PROTOCOL_END) + len(pv.PROTOCOL_END)
    return " ".join(text[start:stop].split())


def test_protocol_block_is_byte_identical_to_the_freeze(text):
    digest = pv.protocol_block_sha256(text)
    assert digest == PROTOCOL_V2_SHA256 == pv.PROTOCOL_V2_SHA256
    start = text.index(pv.PROTOCOL_BEGIN)
    stop = text.index(pv.PROTOCOL_END) + len(pv.PROTOCOL_END)
    assert digest == hashlib.sha256(text[start:stop].encode()).hexdigest()
    assert text.rstrip().endswith(pv.PROTOCOL_END)


def test_protocol_constants_equal_the_script_s(protocol):
    assert pv.PSEUDO_ORIGIN == 2006 and "b = 2006" in protocol
    assert f"seed={pv.FIT_SEED}, boundary_year={pv.PSEUDO_ORIGIN}" in protocol
    assert pv.DRAW_SEEDS == tuple(range(6200, 6220)) and pv.K == 20
    assert "| Fit seed; draw seeds | 5200; 6200-6219 |" in protocol
    assert (pv.B_F, pv.B_D) == (4000, 1000)
    assert "| Arm F, arm D replicates | 4,000; 1,000 |" in protocol
    assert (pv.B_R_MIN, pv.B_R_MAX) == (60, 200)
    assert "at most 200, at least 60 |" in protocol
    assert pv.ARM_R_BUDGET_SECONDS == 36 * 3600
    assert "| Arm R budget | 36 hours from arm R's first start" in protocol
    assert f"| Root seed | {pv.BOOTSTRAP_ROOT_SEED} |" in protocol
    assert pv.N_CI_RESAMPLES == 2000 and pv.CI_LEVELS == (0.05, 0.95)
    assert pv.UCL_LEVEL == 0.975
    assert (
        "| Limit resamples; percentiles | 2,000; 5th and 95th, and 97.5th"
        in protocol
    )
    assert pv.MIN_DEFINED_SHARE_F == 0.99
    assert "| Defined share needed in arm F | 0.99 |" in protocol
    assert pv.MAX_FAILED_SHARE == 0.10
    assert "above 0.10 of an arm |" in protocol
    assert pv.DESIGN_RATIO_LIMIT == 1.10
    assert "| Design-ratio limit | 1.10 |" in protocol
    assert pv.TRUTH_AGREEMENT_RTOL == 1e-9
    assert "| Truth-agreement tolerance | 1e-9 relative |" in protocol
    assert pv.ID_SCALE == 1000
    assert "| Identifier scale for copies | 1000 |" in protocol
    assert pv.REFIT_SCHEME == "half"
    assert "Arm R: refit, household half-samples, 60 to 200" in protocol
    assert max(pv.COLLECTION_WAVES) == 2011
    assert "collection waves 1969-2011" in protocol
    assert pv.B2_EXPECTED == {
        "fit_input_rows": 321_500,
        "n_full_anchor": 23_134,
        "n_domain": 13_542,
    }
    assert (
        "321,500 fit-input rows, 23,134 full-anchor persons and 13,542 "
        "domain persons" in protocol
    )
    assert pv.RUNTIME["python"] == "3.14.4"
    assert "Python 3.14.4, NumPy 2.5.1, pandas 3.0.3" in protocol
    assert pv.selector.EXPECTED_POPULACE_HEAD in protocol


def test_protocol_stream_words_match_the_code(protocol):
    assert (
        "[root, b, 0] arm F households; [root, b, 2] and [root, b, 3] arm R "
        "full-anchor and other half-samples; [root, b, 4] arm D; "
        "[root, 2^20] limits" in protocol
    )
    import inspect

    assert '"anchor", replicate, 0' in inspect.getsource(
        pv.anchor_multiplicities
    )
    source = inspect.getsource(pv.refit_multiplicities)
    assert '(("anchor", 2), ("other", 3))' in source
    assert "int(replicate), 4" in inspect.getsource(pv.design_multiplicities)


def test_protocol_power_constants_match_the_power_script(protocol):
    assert f"{power.TAU_UNCAPPED:.4f}" == "5.0870"
    assert "2.60632 × 2 / √(1 + 1/K) = 5.0870" in protocol
    assert round(power.FLOOR_RATIO, 5) == 2.60632
    assert power.seed_conjunction_bound(6) == pytest.approx(0.025)
    assert "C(5, 2) × 0.05² = 0.025" in protocol
    assert power.MIN_GATED_CELLS == 4 and power.POWER_TARGET == 0.90
    assert power.BASES[0] == "binding"
    assert "r_c = the arm-F point estimate and v_c = v_reg,c = s²_gate,c" in (
        protocol
    )


def test_gate_leak_evidence_matches_the_recorded_output(protocol):
    lines = GATE_LEAK.read_text(encoding="utf-8").splitlines()
    assert "pairs 37552" in lines[0]
    assert lines[1] == "full n_iter 23"
    assert lines[2].startswith("copies n_iter mean 100.0 min 100 max 100")
    assert lines[3].startswith("half n_iter mean 19.1 min 11 max 30")
    assert lines[4].endswith("median 3.04 geometric mean 3.45")
    assert (
        "(37,552 pairs, 24 refits per scheme) the full fit stopped at 23 "
        "boosting iterations, half-sample refits at 11-30, and every copied "
        "refit ran to the cap of 100, with about three times the prediction "
        "variance" in protocol
    )


def test_record_table_freezes_ten_elements_and_the_procedure(text):
    rows = re.findall(
        r"^\| (\d+\. [^|]+|Named power procedure) \| ([^|]+) \|", text, re.M
    )
    assert [name.split(".")[0] for name, _ in rows[:10]] == [
        str(n) for n in range(1, 11)
    ]
    assert rows[10][0] == "Named power procedure"
    assert {status.strip() for _, status in rows} == {"Frozen", "Rule frozen"}
    assert [s.strip() for n, s in rows if n.startswith(("6", "7"))] == [
        "Rule frozen",
        "Rule frozen",
    ]


@pytest.mark.parametrize(
    "sentence",
    [
        # d693 as ruled
        "Yes: accept all eight B0.1 defaults with the riders in",
        # d622
        "a B1 v2 reconstructed-reproduction pass may unlock B2 (and H), "
        "with the weaker label carried into B2's registration.",
        # Q1 sub-question
        "These rulings cite no boundary-2008 or boundary-2010 candidate "
        "result. PRs #255 and #273, which published those results, merged "
        "under Max's account",
        # Q4
        "No Track B gate holds ages 25-61 earnings to a fixed limit",
        "§5.3 feasibility is reviewed once, for B3 and B3L",
        # Q5
        "M6's published floor is used only as a labelled illustration",
        # Q7
        "B2's bridge hands its frozen 13,542-person domain to H, and B2 "
        "scores no one outside ages 25-64 at the scored waves",
        "H's spec names and counts its 2010 start roster, and B4's coverage "
        "declaration cites it",
        # Q8
        "2010→2014 continuity on the stated surface, ages 25–64. Not a "
        "2010-vintage forecast",
        "H and B3L may rely on B2 only within that scope",
        "removing this statement after any candidate run requires a dated "
        "amendment",
        # d622 label
        "reconstructed reproduction (weaker than bit-for-bit)",
        # element 9
        "INVALID and INCONCLUSIVE are non-passes with FAIL's consequences",
        "no rerun, no new draw or bootstrap seed, no larger K, and no "
        "re-pruning, tolerance change or rescoping",
    ],
)
def test_addendum_carries_each_ruled_sentence(prose, sentence):
    assert sentence in prose


def test_structural_power_table_matches_the_power_script(text):
    record = power.structural_record()["by_family_size"]
    for m in (1, 4, 5, 6, 16):
        row = record[str(m)]
        room = row["estimation_room_gate_bound_only"]
        room_text = (
            "none"
            if room < 0
            else (
                f"{round(room * 100):d}%" if m == 1 else f"{room * 100:.1f}%"
            )
        )
        line = (
            f"| {m} | {row['p_bound_rule_only']:.3f} | "
            f"{row['p_gate_joint']:.3f} | {room_text} | "
            f"{row['m6_seed_convention_with_bound_rule']:.3f} |"
        )
        assert line in text, line
        assert row["p_seeds_fail_given_bound_passes"] < 0.001


def test_q2_correction_figures(prose):
    record = power.structural_record()["by_family_size"]
    assert round(record["6"]["estimation_room_per_cell"], 3) == 0.411
    assert "the room is 41.1% at m = 6" in prose
    assert (
        "for the whole gate it is 2.8% at six cells, 8.4% at five and 16.0% "
        "at four" in prose
    )
    assert (
        "the bound rule passes all six cells with probability 0.917, and "
        "all 16 with 0.584" in prose
    )


def test_concept_families_and_retained_six_match_m6():
    import ast

    source = (ROOT / "scripts" / "build_m6_holdout_floors_v2.py").read_text(
        encoding="utf-8"
    )
    literal = re.search(r"^CONCEPT_FAMILY = (\{.*?^\})", source, re.M | re.S)
    assert power.CONCEPT_FAMILY == ast.literal_eval(literal.group(1))
    assert set(power.CONCEPT_FAMILY_CELLS) == set(pv.CELLS)
    assert set(power.M6_RETAINED) <= set(pv.CELLS)
    assert len(power.M6_RETAINED) == 6


def test_exposure_labels_name_the_retained_six(prose):
    for cell in power.M6_RETAINED:
        assert f"`{cell}`" in prose
