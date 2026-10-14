REQUEST CHANGES

I found no high finding, one medium and five low. I met no reference-year 2012 or 2014 gate statistic, floor, truth moment or candidate outcome, and no 2008 or 2010 selector outcome. Every path I named or got back lies inside the root, and none is on the round-4 denied list (`docs/design/track_b_b0_1_addendum_q6_root_r4.json:50-72`). A Glob for those paths returned nothing. Plan mode was active and no plan file was written; this review is the deliverable.

## Findings

### Medium

**M1. Section 14 does not record everything the 2026-10-11 revision session read.**
- **Where:** `docs/design/track_b_b0_1_addendum.md:1215-1248`, against `:905-916` and `:1074-1076`.
- **What is wrong:**
  - Section 13 reports what B1's result comment on #42 says: "All four conditions are exact, with zero differences", plus the launcher deviation. Its writer therefore read #42 comments 6110674288 and 6113379406, and apparently handled B1's launch.
  - Section 14's list for this session names B1 only as "`track_b/` and the candidate-3 runner's environment guard" and the candidate-3 artifact's keys. It leaves out:
    - the #42 comments, which the d693 Q6 rider treats as exposure material (`:97`);
    - any handling of B1's run or its output;
    - whether the session opened B1's raw output, which section 13 says "stays sealed";
    - the d1342 decision aid, which this session drafted, and its two GPT-6.1 Sol reviews (`_review_context/OPTIONS.md:3-4,130-144`).
  - Unlike the first author's reads, this session's reads have no record derived from a transcript. Section 14 does not say so.
- **Why it matters:** Question 7 and the d693 Q6 rider depend on an accurate exposure record. B1 replays a registered candidate run, so whether the session opened its sealed output is exactly the kind of fact the record must state. I can't tell from inside the root whether the output holds anything on B2's surface.
- **Smallest fix:** Add a bullet to section 14 for this session covering:
  - which #42 comments it read;
  - its role in launching B1;
  - an explicit statement on whether it opened any B1 output;
  - the d1342 aid and its reviews, and who else read what;
  - that this session's reads are recorded in prose only, with no extractor record.

### Low

**L1. Two sentences overstate the "only the most lenient" claim.**
- **Where:** `:69-71` and `:760-763`.
- **What is wrong:** "only the most lenient reaches it, at 0.907" sits next to a table row where household resampling reaches 0.952. The record lists two evaluations of the six that reach 0.90: `household_as_measured` and `most_lenient` (`track_b_b0_1_ruled_power.json:901-904`).
- **Why it matters:** The intended meaning is "of the evaluations on the ruled configuration", but the text does not say so.
- **Fix:** Say "of the evaluations on the ruled configuration (household resampling, d781's basis, excepted)".

**L2. The authority for the t value is cited only to the round-1 rider.**
- **Where:** `:66`, `:126`, `:351-357`.
- **What is wrong:** d782's ruling text does not mention a t value (`_review_context/d782-ruling.md:5`). Max did see the t value: d1342's question names "t at 63 df", and he ruled A (`_review_context/d1342-ruling.md:3-5`). The addendum never cites that.
- **Why it matters:** As written, the change from d693's z\* to t reads as an author addition to a ruled element.
- **Fix:** Add one sentence to section 2 saying d1342's question put "t at 63 df" to Max, and his option-A ruling covers it.

**L3. The stratum fallback is left open until after the floor is built.**
- **Where:** `:324-327`, `:432-434`, `:1063-1064`.
- **What is wrong:** If any stratum has one cluster or three or more, B2 stops and "a dated amendment registers how those strata are handled". That amendment would be written after B2's truth-only floor, its tolerances and its se_up are known. ν and the critical value would change with it.
- **Why it matters:** This is not freedom after a candidate outcome, and it is correctly marked as blocking B2's candidate run. But it is the one variance-method choice made after the floor that the record does not pre-specify.
- **Fix:** Pre-register the fallback now. For example:
  - n_h ≥ 3: Rao-Wu with m_h = n_h − 1 and weights rescaled by n_h/(n_h − 1), contributing n_h − 1 to ν;
  - singleton strata: collapse into a pre-named neighbouring stratum.

  Alternatively, state why this cannot be done before the floor.

**L4. Some wording is stale after the rulings and later rounds.**
- `:246-250`: "With six eligible families the ladder cannot go below six cells…" describes the 16-cell case. Inside d781's six there are two families, and `:205-207` already says the guard can bind after two prunes. Mark the sentence as applying to the d693 surface only.
- `:1266-1270`: "Five named files are copied in… They are the only launch-evidence material in the root." There are now ten, including `OPTIONS.md`. The copies are also a deliberate exception to the Q6 rider's exclusion of the launch-evidence directory (`:97`; `d693-RECOMMENDATION.md:53`). Update the count and say the exception is deliberate.

**L5. "Nothing after 2010 was recorded" is slightly too broad.**
- **Where:** `:490-497` and the protocol's input 7 (`:1582-1583`); `track_b_b0_1_planning_values.json:1570-1585`.
- **What is wrong:** `transport.support_2010` holds B2's scored-support counts at reference years 2012 and 2014, copied from the frozen audit record. For example, the older cohort's 9,055 equals 4,654 + 4,401 (`track_b_b0_1_counts.json:190,213-233`).
- **Why it matters:** These are presence counts, not split by earnings sign. They come from an already-frozen record, which protocol input 7 explicitly allows, so they reveal no level or gap. Still, the prose claim and the key name `support_2010` are inexact.
- **Fix:** In section 10, say that the record copies B2's 2012/2014 support counts from `track_b_b0_1_counts.json` and holds nothing else about those years.

## Answers to the seven questions

### 1. Completeness
- **Elements frozen.** The section 3 table (`:150-162`) marks all ten §5.2 elements and the named power procedure as Frozen or Rule frozen. A test pins this (`tests/test_track_b_b0_1_addendum_record.py:153-165`).
  - Element 6 is d781's six plus section 5's ladder inside them (`:195-216`), confirmed by d1342 (A).
  - Element 7's rule is at `:280-292`.
  - Element 8 is Rao-Wu se_boot, the refusal rule for strata that do not have two clusters, ν, and t (`:302-357`).
  - Element 9 is at `:385-416`.
- **Post-outcome freedom.** `:413-416` bars reruns, new seeds, larger K, re-pruning and rescoping after any candidate outcome. Seeds and streams are named at `:371-377`.
- **What remains open.** The only open choice is the stratum fallback (L3), which comes after the floor but before any candidate outcome.
- **Marking.** Section 13 lists every precondition for B2's registration and records each as ruled or passed (`:889-916`). It states "None blocks this addendum's merge" (`:918-921`). The floor-builder obligations are correctly placed under "To B2" (`:1038-1084`).

### 2. Fidelity to the rulings
- **Quotations.** The quotations at `:79-84`, `:101-103`, `:111-120` and `:135` match the context ruling texts word for word, and tests pin them (`test_track_b_b0_1_addendum_record.py:604-629, 707-711`).
- **d693 riders.** The table at `:89-99` matches `d693-RECOMMENDATION.md:26-60`.
- **d622.** The weaker label is carried at `:905-909` and `:1074-1076`.
- **d765.** The ruling's clause "the fixed-law arm stays a household bootstrap" is honoured, and se_up stays household (`:330-334`).
- **d781 (a).** Carried at `:195-203`, `:1067-1068` and `:1083-1084`.
- **d782.** The floor and gate-seed splits stay household (`:329`).
- **M2 rider.** The t value is carried (`:351-357`). Its authority should be traced to d1342 (L2).
- **d1342 (A).** Carried exactly (`:135-141`, `:1069-1073`).
- **Changes elsewhere.** I found nothing the rulings decided that is changed elsewhere. Moving from household to design clusters in Q2 is d782's own decision.

### 3. Protocol and blindness
- **Script against protocol.** The CI tests pin the script's constants, stream words and power constants to the protocol text (`test_track_b_b0_1_addendum_record.py:63-135`). They pin the script's SHA-256 to the run record (`:281-292`) and the protocol block's SHA-256 to `2a1681cd…` in both the test and the script (`:31-34, 54-60`).
- **Block untouched.** The block is the file's final text (`:1507-1841`). A test asserts the file ends with the end marker, so later edits cannot change it without failing CI. I could not compute the hash myself.
- **Reads.** The run opened only family files for collection waves 1969-2011 plus the individual file, and NAWI through its 2006 key (`planning_values.json:1439-1450`; test `:296-322`).
- **What is recorded.** The record holds ratios, counts, hashes and an arm-F correlation matrix. It holds no level or gap. The only post-2010 content is the support counts in L5.

### 4. Statistics
- **Planning arms.** Sound as specified (`:1651-1717`).
  - The half-sample variance claim holds for smooth statistics, and the addendum discloses that it is unproven for this early-stopping law (`:592-595`).
  - Taking the 97.5th-percentile upper limit for e is conservative.
- **Transport rule.** Sound. Estimation variance in se_up units scales as n/P. Every f is 1, and I checked this for the level and change supports (`planning_values.json:1319-1343` against `:1570-1585`).
- **Element 8.** Two-cluster Rao-Wu correctly means drawing one cluster and doubling it. The ordinary bootstrap's (n_h−1)/n_h bias for strata with three or more clusters is correctly identified. Refusing such strata is sound but leaves L3 open.
- **Student t.** ν = Σ(n_h − 1) is the standard design df. I approximated t₆₃⁻¹(1 − 0.05/12) ≈ 2.724 independently with a Cornish-Fisher expansion. Giving all of se_c ν df is conservative, as stated.
- **Ruled-power model.** Coherent.
  - It uses x ~ N(0, (rd)² + e) and registered variance V = (rd)²·χ²_ν/ν + a, and the bound term is 2Φ(c/s) − 1 (`ruled_power.py:298-300`).
  - At ν = ∞, d = 1 and z it reduces to protocol v2's evaluation, and a test checks that (`tests/test_track_b_b0_1_ruled_power.py:106-117`).
  - The ladder reproduces M6's (`build_m6_holdout_floors_v2.py:343-371`; `ruled_power.py:482-493`).
  - One small difference: the binding evaluation's registered estimation term is s²_gate − r² (0.510 for `earn_p50.older`), while B2 will register e_B2 (0.505). Section 11 states this (`:734-736`), and the effect is small and conservative.

### 5. Power
- **Original basis.** The verdict follows from `addendum_power.json`, which CI recomputes (`test_…_addendum_record.py:360-396`), and the rendered tables are pinned (`:398-400`).
- **Ruled configuration.** I checked every figure in section 11's ruled subsection by hand against `track_b_b0_1_ruled_power.json`:
  - the evaluation table: 0.813, 0.821, 0.854, 0.841, 0.852, 0.813, 0.907 and 0.952;
  - all 21 surface rows;
  - the tolerance-scale table;
  - 306 of 720 orders clearing, with the other 414 all ending on three cells (end surfaces 48×4 + 36 + 30×2 + 18×5 + 12×3);
  - option D: k = 3.26, width 1.06, power 0.901 / 0.956;
  - the weak cell's bound-pass probability of 0.892;
  - the seed-failure probability below 10⁻⁶ (maximum 2.24 × 10⁻⁷);
  - the maximum gap correlation of 0.18.
- **Verdict.** "Feasible, subject to B2's floor" follows from the four-cell surface at 0.964, which keeps both families.

### 6. Consistency
- The addendum, both power scripts, the tables renderer (`addendum_tables.py:180-273`), the records and the tests agree.
- `OPTIONS.md` agrees with the record (120 orders end on five cells and 186 on four, which sums to 306).
- The exceptions are the wording issues in L1, L4 and L5.

### 7. Exposure
- **First author.** Section 14's account matches the reads record's pinned counts: 1,801 calls, 14 with a scope flag (3 by the author, 11 by its agents, split 5/5/1), and 114 restricted entries checked (`addendum_reads.json:307-337`; `test_…_addendum_reads.py:177-239`).
- **Review history.** Section 15's root heads, manifest prefixes and removal lists match `q6_root_r{1..4}.json`.
- **The 2026-10-11 session.** Its account is incomplete (M1).
- **Additions since round 1.** Nothing added since round 1 that I read exposes a B2 outcome or a 2008/2010 selector outcome. The ruled-power record and `OPTIONS.md` are functions of the 2006 planning record alone.

## What I could not check from inside the root
- The protocol block's SHA-256, and whether CI passes. I ran no code.
- The design file's identity and the context copies' hashes against their sources.
- The transcript export behind `addendum_reads.json`, and the reads of the 2026-10-11 session.
- The content of #42 and B1's sealed output. The B1 claims and M1 rest on section 13's prose.
- Whether `0550d2f` was pushed before the run, and the run's timing.
- PSID's cluster structure at B2's 2011 truth support, so whether the refusal at `:324-327` will trigger.
- This round's own root record and read log, which do not exist yet (`:1490-1496`).

## Read log (relative to the root)
- Glob `**/*`, `**/*b0_1*`, `_review_context/**`, and a Glob for the denied paths, which returned nothing.
- Read `docs/design/track_b_b0_1_addendum.md` in full, in three parts.
- Read `_review_context/d1342-ruling.md`, `d781-ruling.md`, `d782-ruling.md`, `d765-ruling.md`, `d693-ruling.md`, `d622-ruling.md`, `d693-RECOMMENDATION.md` and `OPTIONS.md`.
- Read `_review_context/trackb-design-20260928.md` (lines 275-344 and 440-474); Grep of `_review_context/pr490-comments.md`.
- Read `scripts/track_b_b0_1_ruled_power.py` and `scripts/track_b_b0_1_addendum_tables.py` (lines 150-279); Grep of the latter.
- Read `docs/design/track_b_b0_1_ruled_power.json`.
- Read `docs/design/track_b_b0_1_planning_values.json` (lines 360-423, 1300-1359 and 1555-1589); two Greps of it.
- Read `docs/design/track_b_b0_1_counts.json` (lines 80-239); Grep of it.
- Grep and Read of `scripts/build_m6_holdout_floors_v2.py` (lines 325-374 and 460-471).
- Read `tests/test_track_b_b0_1_addendum_record.py`.
- Grep and Read of `tests/test_track_b_b0_1_ruled_power.py` (lines 55-134 and 285-364).
- Grep of `docs/design/track_b_b0_1_addendum_q6_review_r1.md`.
- Grep over `docs/design/track_b_b0_1_*` for the #42 comment IDs.
- Grep over `docs/design/track_b_b0_1_addendum_q6_root_r*.json`; Read of `docs/design/track_b_b0_1_addendum_q6_root_r4.json`.
- Grep and Read of `docs/design/track_b_b0_1_addendum_reads.json` (lines 290-337).
- Grep and Read of `tests/test_track_b_b0_1_addendum_reads.py` (lines 150-249).