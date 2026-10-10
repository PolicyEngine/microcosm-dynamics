<!-- Confirmation review of the final head on PR #509 (gate_epuf registration).
Reviewer: independent Opus 5.5 lane, subfleet job 20261002-173551-epuf-gate-r4,
reviewing branch head 95291e75 (2026-10-02). Committed verbatim as the round's record. -->

**APPROVE**

All five of round 3's points are fixed at `95291e75`. The delta adds no false claim and nothing that reads as a lock or a certification. `gates.yaml` still has no EPUF entry, and the block still has `locked: false` and `gated_cells: {}`. I had no shell, so this rests on reading the files; I didn't run the tests.

| # | Round-3 point | Status | Evidence |
|---|---|---|---|
| 1 | "only two cells had enough power" in the paper and the proposal's outcome | **RESOLVED** | Both now say "only two cells met the rules for gating" (`paper/paper.qmd:366`, `proposal.md:36`), the wording round 3 suggested. The sentence is now true and matches §7.2–7.3. §7.2 says `r6.women.c1` is eligible but not gated, because the ladder gates cohort cells only when all six are eligible (`proposal.md:374-377`). §7.3 says "The ladder fell back to sex-level persistence and selected two cells" (`:381`). The rest of the paper sentence ("we found nothing they would catch that gate 1 does not… without a pass or fail") matches §7.4 (`:430-431`). No "enough power" or "had the power" is left in the paper, proposal, block or renderer. |
| 2 | `report_candidate` tests: source and model terms on nonzero bridges, and the NaN paths | **RESOLVED** | See the notes below the table. |
| 3 | Supplement tests could pass vacuously | **RESOLVED** | See the notes below the table. |
| 4 | §10 commit record and the checklist wording | **RESOLVED** | Item 4 now names `d606ddea`. A new item 5 names `93848324` (`report_candidate`, the round-2 report and its corrections) and mentions the final commit. The checklist says "a pinned reporting path" and adds the re-review line. "Scoring path" survives only in the block's round-2 record (`block.yaml:206`, renderer `:73`), where it correctly describes what was replaced. |
| 5 | Four wording fixes | **RESOLVED** | • Block ruling (rendered from the script, `block.yaml:190-199`): "0.067 for men and 0.057 for women". This matches §7.4 and the supplement's −0.0665/−0.0568.<br>• §10 quotes "the house floor formula", the docstring's exact text (`epuf_gate.py:179`).<br>• §7.4 says bd2c moves the cells "about 0.01", matching the table's +0.007/+0.010 (`proposal.md:402`).<br>• §9 says tranche R "would report… no code computes its PSID side yet". `career_cells` is called only on EPUF data (`build_epuf_gate_floors.py:295-296`), so this is accurate. |

**Point 2 in detail.** The new tests cannot pass vacuously:

- **Real bridges, not the synthetic fixture.** `test_report_candidate_terms_against_the_committed_bridges` feeds the committed artifact's `cells` into `report_candidate`. `candidate_window_cells` is stubbed out (monkeypatched); `report_candidate` calls it through the module, so the stub takes effect.
- **Nonzero bridges.** I counted the artifact's 41 bridges: 38 have |b| > 0.01, against the test's floor of 25. Only three are below 0.01 (0.0045, −0.0097, −0.0095).
- **Source term.** The test compares the code's `psid − epuf` on the cell's scale with the stored `bridge_psid_minus_epuf`. A flipped sign or a wrong scale would now fail.
- **Model term.** It is checked as `estimate − transform(psid)`, which is computed separately from the code's `gap − source`.
- **Coverage.** The test asserts that the report's cell ids equal `cell_ids()`, so all 41 cells are checked. It also asserts that neither the report nor any cell carries a `pass` key.
- **Defined values only.** `pytest.approx` never treats NaN as equal to NaN, so the test cannot pass by producing NaN.
- **NaN paths.** `test_report_candidate_propagates_undefined_values` sets one seed of `r6.men` to NaN, which makes its estimate and gap NaN. It sets `r6.women`'s `psid_value` to None, which leaves the gap defined but makes both split terms NaN (via `_on_scale`, `epuf_run.py:102-103`).

**Point 3 in detail.**

- `set(bites[name]["cells"]) == set(artifact["registered"])` is added (`test:161`). It can't hold for empty sets: the detection-point loop indexes `bites["bd1_persistence_loss_0.10"]["cells"]["r6.men"]` and `["r6.women"]` (`:209`), which would fail if those cells were missing.
- `set(bites["detection_points"]) == {"r6.men", "r6.women"}` is a literal (`:192`).
- The band years are now tied to `COHORT_BANDS` (`:350-351`), which defines c0 = 1947–1955, c1 = 1956–1964 and c2 = 1965–1973.

**New findings.** Nothing blocks merge. Three optional nits:

- **The pooled estimate is checked against itself.** Test 1 compares `estimate` with `gate.pooled_estimate`, the same function the code calls, so an error in that function would go unnoticed. Fix (optional): also assert `row["estimate"] == pytest.approx(transform(cell_id, statistics.fmean(per_seed)))`.
- **The round-3 verdict mixes in the drafting session's claim.** The block records `verdict: APPROVE (five minor points, applied)` (`block.yaml` `rereview_round_3`), but "applied" is the drafting session's claim, not the reviewer's verdict. Round 2's record uses the same pattern. Fix (optional): `verdict: APPROVE (five minor points)` and `fixes: applied in 95291e75`.
- **One long line.** `proposal.md:574` ("the house floor formula" line) now runs past the wrap width.

**Lock and certification check.**

- `gates.yaml` has 0 EPUF matches.
- The block has `status: unlocked_report_only` (`:18`), `locked: false` (`:19`), `gated_cells: {}` (`:109`) and `lock_ceremony.exists: false` (`:216`).
- The header says it "gates nothing" and "edits no gates.yaml byte".
- The diff adds no wording about passing, locking or certifying. The phrase "met the rules for gating" sits beside "report the comparison without a pass or fail".

**What I could not check:**

- **Tests.** I ran no tests. So I couldn't confirm that the two new tests pass, that the tier count of +2 (3,359 → 3,361) is right, or that the block equals a fresh render.
- **Git.** I ran no git commands. I took the delta from `.diag/round3-fix-delta.diff`, and the claim that the derivation-core diff since `ce8d5000` is empty from the drafting session.
- **Hashes.** I computed none. The supplement and artifact hash literals are unchanged in the diff.
- **PR body.** I didn't read it.
- **PSID data.** I read no PSID microdata.