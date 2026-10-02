REQUEST CHANGES

# Blinded review: Track B B0.1 addendum (PR #505)

I found no high findings, three medium and seven low.

The addendum, read with the audit, does freeze all ten §5.2 elements and the named power procedure. The script matches protocol v2 statement by statement. Nothing the run opened, computed or recorded is dated after collection wave 2011 or reveals a level or a gap. The power code computes the ruled pass rule correctly, and the section 11 verdict follows from the records.

The medium findings are about how the two queued decisions (d781, d782) are framed for Max and about one claim in section 14.

Blindness: I did not meet any gate statistic, floor, truth moment or candidate outcome for reference years 2012 or 2014. I also met no selector outcome at pseudo-boundary 2008 or 2010.

## Findings

### Medium

**M1. d781's options leave out choices that are Max's, and the framing tilts toward option (a).**
- Where: `docs/design/track_b_b0_1_addendum.md:514-519`, `:623-639`; protocol `:1094-1099`.
- What is wrong:
  - The menu offers only (a) gate the six level cells, (b) gate a three-family surface, or (c) stay unadmitted.
  - It does not offer amending d693's Q2 settings, though that is Max's call. Examples are the k = 3 tolerance multiplier or full-support scoring. Design §5.3 (`trackb-design-20260928.md:308`) and §7 (`:454`) allow rescoping before any candidate result.
  - The text says "d693's Q2 flip would let a four-cell surface stand." The flip (`d693-RECOMMENDATION.md:40`) only says when B2 becomes `WEAK_POWER_OR_VACUITY`. It says nothing about four cells being enough.
  - Calling the case one where "the two ruled texts then disagree" makes option (a) look like the ruling-backed default. In fact both texts lead to `WEAK_POWER_OR_VACUITY`, and section 11 itself says "Either way B2 stops here".
- Why it matters: d781 decides B2's gated surface, which is element 6.
- Smallest fix:
  - Add option (d): amend Q2's tolerance or scoring basis. Either give a power figure for it, or say why it is not recommended.
  - Reword the flip sentence: the flip does not fire, and the ladder makes B2 `WEAK_POWER_OR_VACUITY`.

**M2. The design ratio's limits cover only Monte Carlo error, and d782 leaves out that a design-based standard error from 63 strata is itself noisy.**
- Where: `scripts/track_b_b0_1_planning_values.py:1399-1413`; addendum `:433-438`, `:640-650`; record counts at `track_b_b0_1_planning_values.json:1320-1325` (63 strata, two clusters each).
- What is wrong:
  - The 5th and 95th percentiles of d resample the 1,000 arm D replicates. They measure the bootstrap's Monte Carlo error only.
  - They leave out that a variance built from 126 clusters in 63 strata has about 63 degrees of freedom. That means roughly ±9% relative uncertainty in d on its own.
  - So "nine cells fail" depends on noise near the limit. More importantly for d782:
    - under option (a), B2's se_boot would carry about 63 degrees of freedom, so a normal z\* under-covers (a t-type value is about 2.73 rather than 2.64 at m = 6);
    - option (b) multiplies by a noisy 2006 ratio.
  - d782's figure that "either (a) or (b) costs about one cell" leaves both effects out.
- Why it matters: d782 decides element 8.
- Smallest fix:
  - Add these facts to d782.
  - Add a line to section 10's "What the values do not establish".
  - If (a) is chosen, register a degrees-of-freedom-adjusted critical value.

**M3. Section 14's statement about the author's reads is contradicted by the reads record, and the extractor cannot see recursive or glob reads.**
- Where:
  - addendum `:725-731`, `:758-759`, `:776-779`;
  - `scripts/track_b_b0_1_addendum_reads.py:123-138` (it flags only paths named literally) and `:189-194` (it classifies by substring);
  - `docs/design/track_b_b0_1_addendum_reads.json` lines 1696-1697, 1719, 336 and 607.
- What is wrong:
  - Section 14 says the author "opened none of the 20 files on the audit's §15.4 list other than those two line ranges and one grep".
  - The record shows that before the freeze the author ran `grep -rl … .` over the whole worktree (lines 1696-1697) and `grep -ln … tests/*.py` (line 1719). Both open every excluded file in their scope.
  - Agents ran `grep -rn … --include=*.md .` (line 336) and a grep over `docs/design/*.md` (line 607), which takes in the m6_\* design documents.
  - None of these calls is flagged.
  - Their output looks limited to file names, token-matched lines, or lines filtered out (line 607 drops `^docs/design/m6_`). So I see no blindness breach. But the claim as written is not supported.
  - Lines 793 and 1037 are classed `mechanical_scan_or_exclusion_list` because the command contains "EXCL", "TWENTY" or the inventory's name. The command bodies are not recorded, so that classification cannot be checked from the record.
- Why it matters: element 4 (exposure history) and the Q1 sub-question depend on this record being accurate.
- Smallest fix:
  - Change "opened none" to "printed nothing from", and list the recursive and glob calls.
  - Add a rule that flags a recursive or glob scope covering an excluded path.
  - Keep the full command text for any call classified by heuristic.

### Low

- **L1. The audit's "upper bound" correction is only partly applied.**
  - The correction sits at `track_b_b0_1_audit.md:805-813`.
  - These places still state the old bounds: §1 (`:91-95`, "at least 0.898 … 0.998"), `:798-803` ("give upper bounds"), the §11.2 table (`:849-851`, "≥"), §11.4 (`:1001-1003`) and the Q2 facts (`:1043-1044`).
  - Addendum §12 (`:581-593`) says audit §11 "now says so", which overstates it.
  - Fix: reword these places as "reference points".
- **L2. "Uncapped tolerances bound every capped surface's power from above" is not true for B2's real floor.**
  - Where: addendum `:464-466`, `:1091-1092`; `track_b_b0_1_addendum_power.py:404`.
  - The tolerance in se_up units at floor time depends on two things:
    - the realized tolerance/σ (M6 achieved 2.35-2.64, audit `:831`);
    - σ/(2·truth SD), measured at 0.76-1.07 at 2006 (addendum `:392-409`).
  - So the tolerance can exceed 5.087 by several percent.
  - The verdict holds (0.331 is far from 0.90), but the d781 and d782 figures are nominal, not bounds.
  - Fix: call 5.087 "nominal" and add one sensitivity row.
- **L3. The `outcome_blind` flags are hard-coded literals.**
  - They are set at `planning_values.py:2280-2285`.
  - Section 10 (`:355-357`) presents them as checks that passed, and `test_track_b_b0_1_addendum_record.py:305-310` pins a constant.
  - The real evidence is elsewhere: the read guard, the opened-file list matched to the audit's pins, and `assert_record_shape`.
  - Fix: say that.
- **L4. B2's bootstrap root seed and streams and the candidate's draw seeds are not in the record.**
  - Section 7 says only "a registered seed" (`:225-230`).
  - They are fixed before any outcome (`:287-289`, `:296-297`), so this is not post-outcome freedom.
  - Fix: name them so the record is self-contained.
- **L5. The half-sample departure's evidence has no provenance.**
  - `track_b_b0_1_gate_leak_check.txt` records no commit, time or arguments. The 4,000 households and 24 refits are command-line arguments (`gate_leak_check.py:19-21`).
  - Fix: record the command and the commit.
- **L6. The protocol's Monte Carlo claim is slightly off against the measured values.**
  - The protocol (`:1078-1080`) says the Monte Carlo rule can bind only below 2.2 se_up.
  - The measured Monte Carlo error reaches 0.234 se_up (`earn_dlog_sd.older`), so the threshold is about 2.34.
  - It is immaterial at uncapped tolerances.
- **L7. A guard refusal inside a worker would be treated as an interruption.**
  - `_guarded` re-raises `OSError` as infrastructure (`planning_values.py:1763-1764`), and `PermissionError`, the guard's refusal, is an `OSError`.
  - So a forbidden open inside a worker would trigger a resume rather than ending the run.
  - It is moot because workers open no PSID file, but worth a comment.

## Answers to the seven questions

### 1. Completeness
- **What is frozen:**
  - Elements 1-4 and 10 are frozen in the audit; 5, 8 and 9 are frozen and 6 and 7 are rule-frozen in addendum §§4-8.
  - The named procedure is in protocol `:1052-1104`, and `test_record_table_freezes_ten_elements_and_the_procedure` pins it.
- **What is left open:**
  - d781, d782 and d765. B2 cannot register until Max rules on them (`:597-612`).
  - The seeds in L4.
- **Post-outcome choice:** none is possible. `:287-290` forbids reruns, new seeds, a larger K, re-pruning and rescoping after any candidate outcome.
- **Ladder ordering:** it orders by tolerance/σ, as Q1 ruled. On the ruled basis that ordering says little about power, because power is driven by s²_gate. d781 supersedes it in practice.

### 2. Fidelity to the rulings
- **What is carried:**
  - Q1-Q8 riders: carried at the places shown in the `:70-80` table, and each ruled sentence is pinned by the record test.
  - d622: carried.
  - The Q2 headroom correction: the figures 2.8%, 8.4%, 16.0%, 0.917 and 0.584 check out by hand, and `test_track_b_b0_1_addendum_power.py:47-70` pins them.
  - N1-N7: dispositioned at `:567-575`, but see L1.
- **The half-sample departure (d765):**
  - It was disclosed in the frozen protocol (`:1002-1004`) and queued for Max.
  - The invented-panel evidence supports it: every copied refit ran to the 100-iteration cap, against 23 for the full fit, with about 3× the prediction variance.
  - The addendum correctly says the half-samples' own validity is "not established in either direction" (`:448-451`).
  - Running the departure before Max ratified it is acceptable, because B2 cannot register without his ratification.
- **d781 and d782:** they decide nothing, but see M1 and M2.

### 3. Protocol and blindness
**What matches the protocol:**
- The read guard (`:432-478`) and the post-hoc file check (`:2059-2068`).
- Wave caps (`:124-128`, `:372-375`, `:406-407`) and NAWI capped at 2006 (`:1707-1741`).
- Individual-file fields limited to the listed waves (`panels.py:219-239`), and the two design variables only (`age67.py:593-617`).
- Domain equality (`:790`), the forest-skip check (`:744-770`), the arms (`:1012-1141`), the summaries (`:1258-1414`), transport (`:1231-1248`), the allow-list of record keys (`:1554-1616`), and the one-shot and pushed-head guards (`:1987-1999`).

**Provenance in the record supports the claim that the run followed the frozen protocol:**
- The repository head equals the pushed head, `0550d2f…` (record `:1358`, `:1531`).
- The protocol hash matches the pinned value.
- The script hash is unchanged since the run (record test `:288-291`).
- The 74 opened files are all within the audit's pinned read set (test `:315-322`).
- The run had one start and one completion and no resume (record `:1308-1316`).

**Whether a recorded field reveals a level or a gap:**
- I found none. The values are ratios, counts dated 2006-2010, and gap correlations.

### 4. Statistics
- **Arm F (shared-anchor ratio r):** a sound fixed-law household bootstrap of r.
- **Arm R (estimation variance e):**
  - Using half-samples without replacement for e is correct for smooth statistics: delete-n/2 has a variance factor of 1.
  - The simulation correction, using paired common-seed draws, is right. The w and wcov formulas are at `:1081-1086`.
- **Cross term:** it is computed correctly and left out unless its 5th percentile is above zero. That is conservative except where it is positive and unresolved.
- **Transport:** the rule's direction is correct, f = 1 checks by hand for every cell, and the floor of 1 is conservative.
- **What the values do not establish:**
  - transport from 2006 to 2012 and 2014, across a recession;
  - the validity of half-samples for this early-stopping law;
  - sampling uncertainty in d (M2);
  - B2's realized τ (L2).
- **What the limits mean:** the "upper limits" for r and e are Monte Carlo limits conditional on the 2006 sample.

### 5. Power
- **The formula:**
  - P = 5∏a₄ − 4∏a₅ correctly gives "bound rule on every cell and at least four of five seeds".
  - The conditional seed model, N(x, r²), is sound.
  - The Gaussian-correlation and C(5,2)·0.05² claims are correct.
- **The binding evaluation:** it is fixed (`:1082-1089`). Using s²_gate as both the true and the registered variance is conservative.
- **The section 11 verdict:** it follows from the power record (`family_floor_blocks` true, flip false).
- **What the tests pin:**
  - The tables are rendered from the records and required verbatim.
  - The prose figures are pinned by `test_hand_written_figures_come_from_the_records`.
  - The quadrature is checked against brute-force simulation.
  - Cell names in the prose (the best-four and option (b) surfaces) are not pinned, but they match the power record (`:642-649`, `:1625-1636`).

### 6. Consistency
- **Numbers:** all addendum figures I checked agree with both records.
- **Code citations:** those I checked resolve: `m6_scoring.py:394-425`, `:713-750`; `build_m6_holdout_floors_v2.py:330-373`.
- **Section 12's correction:** right in substance. With the law fixed, Var = Var(T) + Var(P̄) − 2Cov(T, P̄), and r > 1 for seven cells contradicts the old bound. It is only partly applied in the audit (L1).

### 7. Exposure
- **Calls it describes correctly:**
  - the counts (1,694 calls and 77 flagged, reads.json `:275`);
  - the own-transcript calls (26);
  - the ranged reads of `gates.yaml` (e.g. lines 1522 and 1718);
  - the codebook-structure calls.
- **Problems:** see M3 for the unflagged recursive and glob reads and the unverifiable heuristic classes.

## Could not check from inside the root
- The cited files that were removed from the root: `gates.yaml`, `m6_projection_engine.md`, the ledgers, the codebook evidence, the round-2 review and `RESTRICTED-FILES.md`.
- The contents of commit `0550d2f`, and whether sections 1-9 and 12-16 were complete there.
- Whether there was any earlier, aborted invocation of the script. Command first lines do not show one, but the record cannot rule it out.
- The bodies of the commands at reads lines 793 and 1037.
- Any numerical reproduction.

## Read log
All paths are relative to the review root.

**Reads:**
- `docs/design/track_b_b0_1_addendum.md` (1-920, 920-1159)
- `_review_context/d693-RECOMMENDATION.md`
- `_review_context/d693-ruling.md`
- `_review_context/d622-ruling.md`
- `_review_context/pr490-comments.md`
- `_review_context/trackb-design-20260928.md` (108-167, 271-470)
- `docs/design/track_b_b0_1_audit.md` (1-182, 518-1017, 1369-1388)
- `scripts/track_b_b0_1_planning_values.py` (1-700, 700-1259, 1258-1817, 1815-2292)
- `scripts/build_m6_holdout_floors_v2.py` (300-409)
- `scripts/track_b_b0_1_gate_leak_check.py`
- `docs/design/track_b_b0_1_gate_leak_check.txt`
- `tests/test_track_b_b0_1_addendum_record.py`
- `docs/design/track_b_b0_1_planning_values.json` (290-449, 1290-1589)
- `src/populace_dynamics/cohorts/age67.py` (560-649)
- `src/populace_dynamics/data/panels.py` (183-272)
- `src/populace_dynamics/cohorts/psid2010.py` (900-979)
- `scripts/track_b_b0_1_addendum_power.py`
- `tests/test_track_b_b0_1_addendum_power.py`
- `scripts/track_b_b0_1_addendum_tables.py`
- `scripts/track_b_b0_1_addendum_reads.py`
- `docs/design/track_b_b0_1_addendum_reads.json` (1-60; single lines 336-337, 607, 671, 793, 1006, 1037, 1474, 1696-1697, 1719, 1921)
- `tests/test_track_b_b0_1_addendum_reads.py`
- `src/populace_dynamics/harness/m6_scoring.py` (385-429, 700-754)

**Globs:**
- `**/*track_b*`
- `_review_context/**`

**Greps:**
- `^#` in the design copy.
- `^#` in the audit.
- `^(def |class |[A-Z_]+ = )` in the planning-values script.
- `37[,_]?552|d765|early.stop|n_iter_no_change|validation_fraction`, root-wide, file names only.
- `37[,_]?552|copies defeat|REFIT_SCHEME|"copies"` in `*.{py,md}`.
- Run-status keys in the planning record.
- `def (ind_person_period|read_design_variables|record_files_read)` in `src`.
- Verdict and surface keys in the power record (`-A 12`).
- `"flag_class"` in the reads record, as a count and as content.
- `"flag_class": \[[^\]]*\]` (`-o`) in the reads record.
- Two broad `command_first_line` extractions in the reads record. **Both outputs exceeded the size limit, and the harness saved them to `~/.claude/projects/…/tool-results/` outside the root. I did not open those files, but these two tool results do name a path outside the root, so the dispatcher should decide whether this review still counts.**
- A recursive-grep pattern in the reads record (count 0).
- `docs/design/\*|…` in the reads record (count, then `-o`).
- A worktree-path pattern in the reads record (count 0).
- `"tool": "(Grep|Glob)"` in the reads record (count 0).
- `"n_calls"|…` in the reads record.
- `def |CONTEXT|KEEP|refuse|frequenc` in `scripts/track_b_b0_1_review_root.py`.
- `at least|upper bound|…` in the audit.
- `--freeze-commit|--checkpoint-dir` in the reads record (0).
- A UTC 03-04h timestamp pattern in the reads record (count 97).
- `planning_values.py` in `command_first_line` in the reads record (count 162).
- `nohup|caffeinate|POPULACE_DYNAMICS_PSID_DIR=` in the reads record.