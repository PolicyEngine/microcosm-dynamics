<!-- Round-2 verification report on PR #509 (gate_epuf registration).
Reviewer: independent Opus 5.5 lane, subfleet job 20261002-170235-epuf-gate-r2,
reviewing branch head d606ddea (2026-10-02). Committed verbatim as the round's record. -->

**Verdict: MERGE AFTER LISTED FIXES.** No blockers. One serious finding and several small ones. The fixes are wording changes in the proposal, the paper, the PR body and possibly one docstring. No rule, threshold or artifact needs to change.

The record is honest where it matters. The gate does not lock, `gated_cells: {}` is tested, option (a) is withdrawn, and both the pause and the ruling are in the forks ledger. The status of every committed number is below. The serious problem is that the proposal and the block describe a reporting path that the code does not provide. The small ones are mostly overstated or imprecise sentences, three of them in the plain-words outcome and one in the public paper.

## Round-1 findings 1-17

| # | Finding | Status | Evidence |
|---|---|---|---|
| 1 | Option (a) is a self-serving fork; adopt (c) | **PARTLY RESOLVED** | (a) is rejected and withdrawn (`proposal.md:416-436`, `:571-572`). Status is `unlocked_report_only` and `gated_cells: {}` (`block.yaml:16-17,107`). Fork 2 is in the ledger (`proposal.md:528`) and a new id is required (`:583`). **But** the referee's fix "publish the per-cell table with its model/source decomposition on every gate-1 run" is not implemented. See new finding S1. |
| 2 | Bite requirement unreachable by design | RESOLVED | §7.4 calls it an internal inconsistency (`proposal.md:396-406`). The block ruling says the same (`block.yaml:188-191`). §12.2 asks future registrations to check the dose. The test asserts the bite sits below the 90% point (`test_gate_epuf_block_draft.py:171-176`). Fork 2's ledger row does not repeat the wording, which is minor. |
| 3 | Bite fail shares do not measure power | RESOLVED | The supplement stores per-seed estimates, shifts and power `Φ` under the gate's noise model. The formula is two-sided and correct (`build_epuf_gate_supplement.py:70-78`). I recomputed all of it (see below). |
| 4 | No catch beyond gate 1 demonstrated | RESOLVED in §7.4 (`:413-414`) and §12.3 | **But it is overstated in the headline.** See new finding M1. |
| 5 | Wrong rules commit | RESOLVED | `rules_commit: eec910d6…` and `floor_build_commit: 970a9db7…` (`block.yaml:20-21`). Test at `test_gate_epuf_block_draft.py:80-91`, including first-build `head_sha == rules_commit`. |
| 6 | Chronology not auditable | RESOLVED; timestamp DEFERRED-AND-DISCLOSED | The first build is committed with its full SHA-256 and an equality test (`test:102-130`). The full hash `369bf5ec…1847e378` matches the truncated form round 1 saw at `ce8d5000`, which is good evidence. The supplement has `built_utc`. A builder timestamp is listed for future work (§12.5). |
| 7 | Scoring path not pinned | RESOLVED, weakly bound | `scoring_path.sha256` is in the block (`block.yaml:32-34`), with a test at `test:94-99`. The expected hash comes from a fresh render, so re-running the renderer silently re-pins it. See M6. |
| 8 | "Prices" should be "bounds" | RESOLVED | §4 (`:209-213`) and §11.5. One sentence is still unhedged: "A generator that copies donors… has less of it" (`:211-213`). Round 1 said "likely"; that word should come back (M5). |
| 9 | k = 4 is not "the house formula" | RESOLVED in the doc (`:217-220`) | The docstring at `epuf_gate.py:179` still says "the house formula". That file is pinned as derivation core, so it cannot be edited without breaking the artifact binding. This is acceptable, but the proposal should say so. |
| 10 | Reproduction is weak for seeds 5-19 | DEFERRED-AND-DISCLOSED | `proposal.md:277-279`, §12.5. |
| 11 | Birth-year rule shifts the bands | PARTLY RESOLVED | Disclosed (`:136-141`) and listed in §12.5. The supplement adds the within-band mix. **But** the "within 0.25 years" comparison (I checked it: largest gap 0.238, women c2) compares birth-year *labels* after each side was selected on its own label. It cannot show the half-year shift is harmless. See M4. |
| 12 | Minimum events summed over bands | DEFERRED-AND-DISCLOSED | `:246-247`, §12.5. |
| 13 | Bite doses mislabelled | RESOLVED | The §6 table describes what the code does (`:289-293`), matching `build_epuf_gate_floors.py:671,721`. |
| 14 | §7 claims not in artifacts; unsupported mechanisms | PARTLY RESOLVED | The 0.07 shift is now stored. The q_atmax and zero-year mechanisms are hedged (`:350-360`). The "0.06-0.07" comparison and "certifies" are gone. **New unsupported claim:** "EPUF subsampled to PSID scale… gave sigma near this size" (`:403-405`). No artifact or doc in the repo records that subsample (grep finds nothing besides these sentences). See M3. |
| 15 | "Nothing generates a career" overstated | PARTLY RESOLVED | §1 is fixed (`:77-81`). `:100-101` still says "nothing generates earnings for a career". `build_career` appends PROJECTED forward-law years from 2015 (`career.py:25,1043-1046`). Suggested wording: "nothing generates a career's earnings before 1998". |
| 16 | Tranche R mask applies only some rules | RESOLVED | "two of the career assembler's rules" and the exclusions not applied are named (`:474-478`). The pre-1979, empty-span and chronology exclusions and the one-neighbour fallback are not named, but `career.py:1581-1598` is cited. |
| 17 | Seed reuse; NaN in JSON | Seed reuse DEFERRED-AND-DISCLOSED (§12.5); NaN NOT RESOLVED, not disclosed | Harmless: neither committed artifact contains NaN. Add one line to §12.5. |

## New findings

**S1 — SERIOUS: the claimed report-only publication path does not exist in code.**
- **What the documents say.** "Every cell publishes report-only with each gate-1 candidate run: the candidate's 20-seed estimate, its distance from EPUF, and that distance split…" with `score_candidate` named as the path (`proposal.md:53-55`, `:430-434`, `:490-493`; `block.yaml:42-45`).
- **What the code does.**
  - `score_candidate` → `gate.score_run(per_seed, registered)` computes the estimate, the gap and the decomposition only for cells in `registered`, which is the floor artifact's two r6 cells (`epuf_gate.py:351-367`). The other 39 cells get only raw per-seed values (`epuf_run.py:112-114`).
  - It still returns `"pass"`, `"n_gated": 2`, `"n_pass"` — a pass/fail verdict on the two cells. That contradicts "no pass or fail, on any cell" (§9) and creates a risk that someone cites "passes gate_epuf".
  - Its docstring still reads "the post-lock run… to a verdict" (`epuf_run.py:3-6`).
  - No gate-1 run script calls it: the only caller is `tests/test_epuf_gate_floor_builder.py:355`.
- **Fix.** Either:
  - **(a, wording only):** say these comparisons *will* be published once a run script calls the scoring path. Say `score_candidate` today decomposes only `r6.men`/`r6.women`, and that its `pass` field is not a verdict. Or:
  - **(b, code):** add a report-only wrapper that computes estimate, gap and decomposition for every cell from the artifact's `cells` block and returns no `pass`. Then re-pin `epuf_run.py` and re-render. This is safe because `epuf_run.py` is not derivation core.

**M1 — MINOR (headline accuracy): "cannot fail" overstates "not demonstrated".**
- The outcome says "**As registered, it cannot fail the generator for anything gate 1 does not already catch**" (`proposal.md:30-31`). The block header comment (`block.yaml:4-5`), the PR body and the paper say the same.
- The evidence (§7.4 `:413-414`) supports only "no perturbation was shown to pass gate 1 and fail these cells". No bite was ever scored on gate 1.
- **Fix:** "it has not been shown to catch anything gate 1 does not already catch".

**M2 — MINOR: errors in §7 and the outcome against the artifacts.**
- **Double-rounded bridges.** The `q_atmax.men` bridge is 0.42447, which rounds to **+0.424**, not +0.425. The `q_atmax.women` bridge is 0.08645, which rounds to **+0.086**, not +0.087 (`floors_v1.json:5012,5145`).
- **False claim about cohort cells.** "No cohort-band cell is powered within the caps" (`:362-363`) is wrong. `r6.women.c1` is `eligible` and was reported only as `cohort_rung_not_adopted` (`floors_v1.json:880-882`).
- **The bd2 men's shift overshoots EPUF.** It is +0.056 from 0.667, which lands at about 0.723, roughly 0.012 *past* EPUF's 0.711. "Toward EPUF's value" (`:43`, `:410-411`) should say it moves to about EPUF's level and slightly past it. bd2 is also a perturbation, not "a generator that ignores sex" (`:43`).
- **"About 0.07" is the men's figure only.** The bd1 shift is 0.067 for men and 0.057 for women (`:399-400`); state both.
- **"Only when" ignores the upper edge.** "Fail a generator only when its persistence falls about 0.10 below the PSID's" (`:36-37`) leaves out failure past the upper edge, which is 0.079 above EPUF and about 0.12 above the PSID.
- **"About 2,500 people per sex" (§12) fits men only.** The support has 2,503 men and 3,266 women; the r6 pairs are 2,182 and 2,376.

**M3 — MINOR: unsupported claim.** "EPUF subsampled to PSID scale… gave sigma near this size" (`:403-405`). Either commit the subsample result or rephrase as "would have given".

**M4 — MINOR: the birth-year comparison is mislabelled as reassurance** (`:139-141`). Say that it compares labels and does not measure the shift.

**M5 — MINOR: band means are presented as raw figures.**
- 0.668/0.711, 17.8/11.6% and 9.7/12.8% are unweighted means of three cohort-band values, not pooled statistics. Check: (0.2256+0.1955+0.1116)/3 = 0.1776.
- The "PSID persists less" result holds in 5 of 6 bands; women c1 goes the other way (+0.017).
- Add "averaged over the three birth-cohort bands" in the outcome, §7.2 and the PR table. Hedge the §4 "has less of it" sentence as round 1 asked.

**M6 — MINOR: test binding.**
- `test_scoring_path_is_pinned` and the supplement hash check compare against a fresh render. Hard-code both literals, as is already done for the first build.
- The supplement test recomputes the 90% detection point but not the 80% one, the distance, or `birth_year_mix`. That falls short of §7's claim that it recomputes "every… power figure" (`:305-307`).
- The supplement asserts only the overall fail share, not `cell_fail_share` (`build_epuf_gate_supplement.py:134-139`).

**M7 — MINOR: the paper is not quite accurate** (`paper.qmd:366`).
- "We registered the rules… before computing any of it" is not true: per §10, EPUF-only values of every cell and EPUF subsamples had been computed. Say "before computing any PSID value on the file's terms".
- "The PSID is too small for the comparison to pass or fail the generator on anything gate 1 does not already test" has the same overstatement as M1. It also leaves out that some cells dropped because the PSID's own gap from EPUF was too large (`bridge_exceeds_budget`).
- Suggested sentence: "On that overlap only two cells had enough power, and we found nothing they would catch that gate 1 does not, so we report the comparison without a pass or fail."

**M8 — MINOR: stale "pending lock" wording in immutable or pinned files.**
- `floors_v1.json:5661` has `gate_partition.status: "lockable_pending_referee_round"`.
- The tranche R note says "computed once, after lock" (`:6680`).
- There is also the `epuf_run.py` docstring.
- The artifacts are exclusive-create, so add one sentence to §10 saying the block supersedes these strings.

## Checked and sound

- **§7 numbers.** Every number in §7.1, §7.2 (except M2), §7.3, §7.4 and §7.6 matches the two artifacts. Hand checks:
  - Tolerances 0.0786 → 0.079 and 0.0784 → 0.078.
  - Outward-rounded intervals: −0.1218 → −0.122 and −0.1103 → −0.111.
  - Faithful pass probability 0.99935 and 0.99925, product 0.9986.
  - 80% points 0.0999 and 0.0995; 90% points 0.1107 and 0.1104.
  - Powers: bd1 0.304/0.188, bd1 at 5% 0.031/0.024, bd2 men 0.0038 (upper edge), bd3 men 0.448.
- **§7.6 tranche R table.** All 18 values match; the drops of 10% and 36% (35.5%) are right.
- **§12 arithmetic.** 2σ + 1.2816σ ≈ 0.082. Even a one-sided 95% tolerance (1.645σ) gives 0.073, still above the 0.067 dose. "Cannot be rescued by retuning" holds.
- **Block.** `unlocked_report_only`, `locked: false`, `gated_cells: {}`, `lock_ceremony.exists: false`. Rules and build commits are named separately; the first build, supplement and scoring path are hashed. The selected cells sit under `selected_by_registered_rules` with reason `not_locked_referee_round_1`. Nothing in the block reads as a pending lock.
- **Supplement builder.** It imports the pinned builder by path and reuses its perturbations in the same order, seeds, masks and `score_run`. It asserts the floor's fail shares, and its real-holdout estimate equals the floor's to every digit (0.6670465436202722). The frame is one row per person, so the birth-year weighting is right.
- **Birth-evidence reducer.** The five EPUF modules are excluded with a comment and an exact-tuple test, and a reachability assertion (`test_birth_evidence_artifact.py:464-475`) follows the pattern of the bridge and graph exclusions. Grep finds no import of any EPUF module outside the EPUF files.
- **Code references.** `career.py:650-656` (birth-year precedence), `:1580-1598` (exclusions), `PROJECTED_START_YEAR = 2015`, and the sex-pooled `(bin, period)` marginals at `run_gate1_candidate10.py:557-562` all support the proposal's statements.
- **Terminology.** "Gate" is defined in plain words where a reader first meets it (`:26-27`). "Benchmark" appears in no EPUF document of this PR except the verbatim referee report.

## What I could not check

This session had no shell, so I ran no tests and no git commands.

- **Rules unchanged since `eec910d6`.** I could not diff §§2-6 against the rules-first commit. Indirect evidence: the test asserts the first build (at `eec910d6`) has the same `design` block as the rebuild. Every §2-6 edit I can see is a wording correction or disclosure round 1 asked for, but I cannot rule out other changes.
- **Derivation-core diff.** I could not run `git diff ce8d5000 d606ddea` on the derivation-core files or compute any SHA-256. The binding rests on `test_derivation_files_are_the_ones_the_floor_was_built_with`, which I did not run.
- **Commit chronology.** I could not verify the 13:37 UTC push time or commit 52e10128's precedent directly.
- **PR body.** I read it only through a summarising fetch, so the PR body notes (missing support qualifier on the table, "cannot fail", "144 new tests") are approximate.
- **PSID data.** I read no PSID microdata.