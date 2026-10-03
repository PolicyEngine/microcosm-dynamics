<!-- Re-review of the round-2 fixes on PR #509 (gate_epuf registration).
Reviewer: independent Opus 5.5 lane, subfleet job 20261002-172832-epuf-gate-r3,
reviewing branch head 93848324 (2026-10-02). Committed verbatim as the round's record. -->

**APPROVE**

# Re-review of PR #509 (gate_epuf registration) at head `93848324`

Head `93848324` is an accurate record of a registration that does not lock, and it is safe to merge to `master`. S1 is fixed in code: `report_candidate` reports all 41 window cells and returns no pass or fail. Its arithmetic matches the pinned algebra. M1–M8 and the round-1 residue are resolved. The fixes introduced no blockers and no serious problems. Five minor points are listed below. One is a sentence in the public paper that now disagrees with §7.2, so I'd fix that one before merge, but it doesn't block.

## What was checked

- **Diffs.** I read the round-2 fix delta and the proposal diff since `eec910d6`. The derivation-core diff since `ce8d5000` is empty, as stated.
- **Hashes.** The hash list in `.diag/hashes-and-tests.txt` matches all of these:
  - the block (`gate_epuf_block_draft.yaml:25,28,33,36`);
  - the literals in `tests/test_gate_epuf_block_draft.py:100-102,147-149,111-113`;
  - the artifact's `revision_pins.derivation_core_sha256` (`runs/epuf_gate_floors_v1.json:7316-7322`).
- **Tests.** The drafting session reports 152 targeted tests passing. I did not run them.

## S1, M1–M8

| Item | Status | Evidence |
|---|---|---|
| **S1**: a reporting path that covers every cell and gives no verdict | **RESOLVED** | See the S1 details below. |
| **M1**: "cannot fail" | **RESOLVED** | No "cannot fail" claim is left in any EPUF document; the phrase survives only inside the record of round 2's fix (`block.yaml:206`) and in the review files. The new wording is "has not been shown to catch… and it could not meet its own check on its bite" (`proposal.md:31-33`, `block.yaml:4-5`), plus "No perturbation was shown to pass gate 1 and fail these cells" (`proposal.md:49,430-431`). |
| **M2**: §7 and the outcome against the artifacts | **RESOLVED** (small residue in the block) | See the M2 details below. |
| **M3**: the subsample sentence | **RESOLVED** | It is now stated as a counterfactual (`proposal.md:416-418`), and the algebra supports it. The distance from the PSID to the lower edge is `max(0,B)+t`, which is at least `t` whatever the bridge. So the 90% detection point is at least about `t + 1.28σ`, roughly 4.5σ. Sigma alone was enough to show that a 0.067 dose could not be caught nine times in ten. |
| **M4**: the birth-year sentence | **RESOLVED** | `proposal.md:148-151` now says the comparison "compares the two sides' own labels… so it does not measure the shift". |
| **M5**: band means shown as raw figures | **RESOLVED** in the proposal | The labels are at `proposal.md:55-58` and `:317-318`. This matches the code: `epuf_cells.py:29-31` defines a sex-level cell as the unweighted mean of its three bands. The §4 sentence is hedged ("likely has less of it", `:222`). For the PR-body table, see "What I could not check". |
| **M6**: test binding | **RESOLVED** | See the M6 details below. Minor gaps remain (new finding 3). |
| **M7**: the paper | **RESOLVED**, with new finding 1 | `paper.qmd:366` now says "before computing any PSID value on the file's terms", which matches the chronology (`proposal.md:530-533`). It adopts round 2's suggested sentence. But "only two cells had enough power" now contradicts §7.2 (finding 1). |
| **M8**: superseded strings | **RESOLVED** (one small misquote) | `proposal.md:565-571` names both strings, which exist at `floors_v1.json:5661` and `:6680`. The docstring is quoted as "the house formula" but actually reads "the house floor formula" (`epuf_gate.py:179`; also "house tolerance" at `:38`). |

**S1 details**

- **What the code does.** `epuf_run.py::report_candidate` loops over every cell in the floor artifact's `cells` block. That is all 41 window cells (`test_gate_epuf_block_draft.py:225`). It returns only `status`, `n_cells` and `cells`.
- **Arithmetic.**
  - The estimate is `gate.pooled_estimate`: the mean of the 20 seeds, then `transform`, and NaN if any seed is not finite (`epuf_gate.py:134-143`).
  - The gap and the source term match `score_cell` and `score_run` term for term (`epuf_gate.py:320-321,360-366`).
  - I checked a nonzero case by hand. For `q_atmax.men`, ln(0.177582/0.116159) = 0.42447, which equals `bridge_psid_minus_epuf` (`floors_v1.json:5008-5012`).
- **Undefined values.** A missing (None) PSID or EPUF value becomes NaN through `_on_scale`. `transform` gives NaN for a share ≤ 0. NaN then carries through the gap and both terms.
- **Seeds.** Anything other than seeds 0–19 is refused, and that is tested.
- **Docstring.** The verdict wording is gone, and it says "No run script calls this module yet".
- **Tests.** "No pass" is asserted on the report and on every cell (`test_epuf_gate_floor_builder.py`, in the round-2 diff). The synthetic tests are weak, though (new finding 2).
- **Documents.** They say exactly what the code does, including that nothing calls it yet:
  - proposal: `:12`, `:60-64`, `:447-454`, `:513-517`;
  - block: `covers` (`:44-47`), `candidate_protocol.reporting` (`:91`), header (`:7-8`);
  - the paper does not name the path and makes no claim about it.

**M2 details**

- **Bridges.** +0.424 and +0.086 (`proposal.md:348-349`) match `floors_v1.json:5012`.
- **Cohort cell.** `r6.women.c1` is now said to be eligible but not adopted (`:374-377`). The block agrees (`block.yaml:140`).
- **bd2.** Men's persistence goes 0.6670 + 0.0561 = 0.7231, which is 0.012 past EPUF's 0.7109 (`:424-425`, supplement `:307`). bd2 is now called a perturbation, not a generator. Its description at `:47-48` matches `build_epuf_gate_floors.py:681-688`.
- **bd1.** The shift is −0.0665 for men and −0.0568 for women (supplement `:69,126`), shown as 0.067/0.057 (`:414`) and 0.07/0.06 (`:43`).
- **Upper edge.** It is 0.079/0.078 (`floors_v1.json:5715,5721`), described as "ends 0.08 above EPUF" (`:40-41`).
- **Pair counts.** 2,182 and 2,376 (`:609`) equal `psid_n` at `floors_v1.json:4215,4347`.
- **Five of six cells.** The bridges of the six `r6` cohort cells (`floors_v1.json:237…902`) are negative in five; women c1 is +0.0173 (`:769`), as stated at `:358-359`.
- **Residue.** The block's ruling text still says "about 0.07", which is the men's figure only (`block.yaml:193`).

**M6 details**

- Literal hashes are now asserted (`test_gate_epuf_block_draft.py:100-102,147-149`), and they equal the hash list.
- The 80% and 90% detection points, the distance and sigma are recomputed (`:191-200`).
- The per-cell fail share is recomputed from the 50 stored estimates (`:161-173`).
- A test of the birth-year mix was added (`:334-357`).

## Round-1 residue

| # | Status | Evidence |
|---|---|---|
| 1 | **RESOLVED** | The table published per cell is implemented (S1). Status is `unlocked_report_only` and `gated_cells: {}` (`block.yaml:18,109`). |
| 8 | **RESOLVED** | "likely has less of it" (`proposal.md:222`). |
| 9 | **RESOLVED** | Superseded in §10 (`:569-571`); it misquotes the docstring slightly (see M8). |
| 11 | **RESOLVED** | Same as M4 (`:148-151`). |
| 14 | **RESOLVED** | Same as M3 (`:416-418`). |
| 15 | **RESOLVED** | "nothing generates a career's earnings before 1998" (`:109`). |
| 16 | **RESOLVED** | All five exclusions are named (`:498-501`) and match `career.py:1580-1598`. |
| 17 | **RESOLVED** | NaN is disclosed as future work in §12.5 (`:633-634`). |

## Rules unchanged, nothing locked

- **§§2–6 since `eec910d6`.** Every change is wording, a disclosure, or a description brought into line with code that was already pinned (the §6 bd1/bd3 rows). No threshold, cap, `k`, seed rule or ladder rule changed. The first-build equality test (`test_gate_epuf_block_draft.py:119-132`) also requires the build at `eec910d6` to have the same `design`, partition and bites as the rebuild.
- **The added §2 sentence.** "EPUF enters nothing upstream of the model" (`:164`) tightens the validation-only rule. It does not loosen anything.
- **Nothing locks.**
  - `gates.yaml` has no EPUF match, and the test asserts this (`:74-77`).
  - The block has `locked: false` (`:19`), `gated_cells: {}` (`:109`) and `lock_ceremony.exists: false` (`:210`).
  - The two selected cells are listed under `report_only` as `not_locked_referee_round_1`.

## New findings

1. **MINOR: "only two cells had enough power" contradicts §7.2.**
   - `paper.qmd:366` says "only two cells had enough power", and `proposal.md:36` says "only two cells had the power the rules demand".
   - The M2 fix made §7.2 say that `r6.women.c1` is *eligible*: it passed the power and cap rules and was not adopted only because of the ladder (`proposal.md:374-377`, `block.yaml:140`). The paper is public.
   - **Fix:** in both places, say "only two cells were selected under the rules" (or "met the rules for gating").
2. **MINOR: the synthetic tests of `report_candidate` cannot catch errors in the source or model term.**
   - The `built` fixture uses the support's own values as the EPUF reference, so every bridge is zero (`test_epuf_gate_floor_builder.py:163-165`).
   - That makes the check `source == bridge` a check of 0 == 0. It would pass even with the sign reversed or on the wrong scale.
   - `gap == source + model` is true by construction.
   - The comparison with `training_copy` covers only the synthetic build's gated cells, and nothing asserts that set is non-empty.
   - The code is right (checked by hand above), but no test proves it.
   - **Fix:** add a unit test that monkeypatches `candidate_window_cells` to return fixed per-seed values and passes in the committed artifact's `cells` block. Assert, for every defined cell:
     - `source_term_psid_minus_epuf == bridge_psid_minus_epuf` (the bridges are nonzero there);
     - `estimate == gate.pooled_estimate(...)`;
     - a NaN seed gives a NaN estimate, and a missing `psid_value` gives NaN terms.

     Then re-pin nothing, since the test file is not pinned.
3. **MINOR: three supplement checks could pass vacuously.**
   - `test_supplement_belongs_to_the_floor_run_and_matches_its_bites` loops over `bites[name]["cells"]` and `bites["detection_points"]` without asserting they are non-empty (`test_gate_epuf_block_draft.py:157,187`).
   - The birth-year test does not tie `years[0]` to the band's first year (`:344`).
   - **Fix:**
     - `assert set(bites[name]["cells"]) == set(artifact["registered"])`;
     - `assert set(bites["detection_points"]) == {"r6.men", "r6.women"}`;
     - `assert years[0] == COHORT_BANDS[band][0]`.
4. **MINOR: the record of commits stops at round 1.**
   - §10 "Order of commits" ends at item 4 (`proposal.md:544-545`) and does not list `93848324`. Round 2 appears only in §7.5 and the block.
   - The §13 checklist still says "a pinned scoring path" (`:641`).
   - **Fix:** add "5. The round-2 commit adds `report_candidate`, the round-2 report and these corrections", and change "scoring path" to "reporting path".
5. **MINOR: three small wording points.**
   - The block's round-1 ruling says "about 0.07"; it should say "0.067 for men, 0.057 for women" (`render_gate_epuf_block_draft.py`, then re-render).
   - §10 should quote "the house floor formula" exactly.
   - §7.4 says bd2c "moves the cells by 0.01 or less", but women's figure is +0.0102 (supplement `:483`). "About 0.01" would be exact.
   - Optional: §9's "Tranche R reports the career statistics" (`:516-517`) is in the present tense, but no code computes tranche R's PSID side. "Would report" is more accurate; §10 `:562-563` already says it has not been computed.

## What I could not check

- **Tests.** I had no shell, so I ran no tests, no git commands and no hashing. The hashes and the 152-pass result are taken from `.diag/hashes-and-tests.txt`; I only compared them for consistency.
- **Synthetic `training_copy`.** I could not confirm that the synthetic build's `training_copy` holds any cells (finding 2).
- **PR body.** I read it only through a summarising fetch. It shows "not shown to catch", `report_candidate` and "No run script calls it yet". I could not confirm that its PSID/EPUF table carries the "means over the three birth-cohort bands" label.
- **Push time.** I could not check the 13:37 UTC push time directly. The branch log shows `eec910d6` at 09:36 −04:00, before the build commits.
- **PSID data.** I read no PSID microdata.