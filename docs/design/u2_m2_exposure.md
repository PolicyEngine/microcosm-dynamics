# U2 milestone 2 exposure record

This record covers every lane that built or reviewed U2 milestone 2 (the implementation of specification §§13–14 on invented data), the lane that finished it on 2026-09-29, the lanes that fixed the findings of review rounds 1 to 3, and the round-3 closeout lane (below). The machine-readable inventory is [`u2_m2_exposure.json`](u2_m2_exposure.json). It holds every path each lane read, wrote, searched or named in a command, plus the restricted-path check.

`EV` is the evidence directory `/Users/maxghenis/microcosm-launch-evidence/dynasim-parity-20260909`. `REFS` is `/Users/maxghenis/PolicyEngine/dynasim-refs`. `PSID` is `~/PolicyEngine/psid-data`.

## Summary

- **No lane opened anything `EV/RESTRICTED-FILES.md` restricts.** That covers the Boomers 2004 and Urban reports, every comparator lane and seal, the U2 and PPI availability and values-scan files, and the scratchpad archives. Every evidence-directory file any lane opened is on the builder-allowed list: the restriction ledger, `common.md`, the U2 m2 briefs, the salvaged journal, `recount-tiers.py` and the cleared U2 availability statement. There is one exception, and neither file is restricted: an unmodified U1 test run in this lane hashed two exercise-2 referee reports (bytes only; see "This lane").
- **No lane read a raw PSID record.** PSID access was documentary only. Every test run with real data absent was guarded, and the loader tests refuse any open under the PSID directory.
- **No lane stated or inferred a 1946–55 value or direction.** Every number in the code, tests and dry run is invented, a policy parameter or a committed public parameter capture.
- **Disclosed exposure:** the 2026-09-29 02:40 ledger entry (below) reached the last builder lane, its two in-session reviewers and the finishing lane. It carries no table value and nothing about the 1946–55 column or the cut, and no code depends on it.

## Lanes

Counts come from each lane's Claude stream-json transcript (tool-call inputs only; tool results were never printed).

| Lane | Transcript | Tool calls | Read tool | Written | Evidence-directory files opened |
|---|---|---:|---:|---:|---|
| u2-m2 a1 (built the salvaged WIP) | `~/.subfleet/jobs/20260928-144013-u2-m2/a1/stdout` | 150 | 6 | 33 | `RESTRICTED-FILES.md`, `common.md`, `u2-target-availability-cleared-20260928.md`, `merge-watchers/recount-tiers.py` |
| u2-m2-continue a1 | `~/.subfleet/jobs/20260928-204756-u2-m2-continue/a1/stdout` | 64 | 0 | 0 | `RESTRICTED-FILES.md`, `common.md`, `u2-target-availability-cleared-20260928.md` |
| u2-m2-resume a1 | `~/.subfleet/jobs/20260928-233117-u2-m2-resume/a1/stream.jsonl` | 143 | 27 | 2 | `RESTRICTED-FILES.md`, `common.md`, `prompts/u2-m2-continue.md`, `merge-watchers/recount-tiers.py` |
| u2-m2-resume a2 (with two in-session reviewer subagents; 180 of its calls) | `~/.subfleet/jobs/20260928-233117-u2-m2-resume/a2/stream.jsonl` | 362 | 15 | 3 | `RESTRICTED-FILES.md`, `common.md`, `prompts/u2-m2-continue.md`, `merge-watchers/recount-tiers.py` |
| u2m2-review a1 (independent reviewer; its findings were fixed in b84e479) | `~/.subfleet/jobs/20260929-020516-u2m2-review/a1/stream.jsonl` | 72 | 36 | 0 | `RESTRICTED-FILES.md`, `common.md` |
| This lane (finished the milestone, 2026-09-29) | this session | — | — | — | See "This lane" |

What each earlier lane read beyond the repository:

- **u2-m2 a1** kept its own running log at `~/.subfleet/worktrees/20260928-144013-u2-m2/.u2m2-work/exposure-log.md`. It lists the four evidence files above, `~/.claude/CLAUDE.md` and the repository files it read at `79451eb4`. It ran test and smoke scripts through a local worker (`.u2m2-work/jobs/*.py`, `worker.py`). A pattern search of those scripts for PSID, evidence-directory and loader paths finds no match.
- **u2-m2-resume a1 and a2** read the earlier lanes' session transcripts under `~/.claude/projects/-Users-maxghenis--subfleet-worktrees-2026092*` to build an exposure inventory. They also read the independent review's deliverable (`~/.subfleet/jobs/20260929-020516-u2m2-review/a1/deliverable.md`) and their own test logs under `/tmp/u2m2*`. They ran the unit tier with an empty HOME and an audit hook (`/tmp/u2m2/audit/sitecustomize.py`, `/tmp/u2m2r/audit/sitecustomize.py`).
- **The two in-session reviewers of resume a2** were told to read `RESTRICTED-FILES.md` and `common.md` first. They were told never to open the Boomers report or anything under REFS and never to read raw PSID data. They worked in `/tmp/u2m2-review2` and `/tmp/u2m2-review3` on invented data.

### Restricted-path check

Every path in the inventory was compared with the ledger: any REFS path, and any evidence-directory path not on the builder-allowed list. The check raised one flag, for resume a2 at the REFS directory itself. It is a false positive: the string occurs only in grep patterns, in the blindness rules of the two reviewer prompts and as a variable in that lane's own restricted-path check script. No call opened, listed or searched the directory. A marker scan for restricted file names and report identifiers (`900767`, `412102`, `411406`, `97646`, `comparator`, `values-scan`, `scratchpad-archive` and others) found no read. Its hits were the specification's own file name (`…_comparison.md`), the word "seal" in U2 code, U1's `COMPARATOR_COLUMN`, and grep patterns.

## Disclosure: the 2026-09-29 02:40 ledger entry

`EV/RESTRICTED-FILES.md` gained a changelog entry at 2026-09-29 02:40. In it the orchestrator records that `pdfinfo` on the Boomers 2004 PDF exposed it to the file's metadata Subject field, and the entry paraphrases that field. Every lane that read the ledger after 02:40 read that paraphrase:

- u2-m2-resume a2. Its transcript timestamps its first ledger read at 02:40:09 EDT, and its journal records the entry.
- Its two in-session reviewers, which read the ledger at 03:28 and 04:17 EDT.
- This lane.

The independent reviewer (u2m2-review) read the ledger at 02:05:33 EDT and exited at 02:16 EDT, before the entry. The earlier builder lanes ran on 2026-09-28.

The paraphrase is a qualitative, report-level summary. It states no table value and nothing about the 1946–55 column, the poverty rows or the 13% cut. This record deliberately does not restate it.

No code, test, parameter or document in milestone 2 depends on it. What each U2 row computes was fixed before 02:40 by the specification and by the commits authored up to `fa001c6` (01:34 EDT). Resume a2's four later commits changed none of `rows.py`, `parameters.py`, `identity.py`, `tabulation.py`, `memo.py` or `estimator.py`. Those commits are `b84e479` (03:22), `6689925` (03:28), `ccf32ab` (04:17) and `98c26d8` (05:28), and `git diff fa001c6 98c26d8` shows the untouched files. The commits changed only four kinds of thing:

- provenance, binding and refusal guards in `cohort.py`, `sources.py`, `loader.py`, `runner.py` and `diagnostics.py` (one `check_cohort_inputs` call);
- the invented generator;
- the differential harness and the dry run's records;
- tests, including U1's worked cases re-worked by hand on invented values.

This lane's changes are:

- a registry-pin update;
- a named refusal of duplicate identifiers;
- an accounting-identity test.

None of these changes computes, selects or tunes anything by outcome.

## This lane

The lane was a workflow subagent (Claude Opus 5.5) working in `/Users/maxghenis/PolicyEngine/_worktrees/dynamics-u2-m2-20260928`, branch `dynamics-u2-m2-20260928`, from head `98c26d8` (rebased onto `b948d6b`).

**Evidence directory (all builder-allowed):**

- `EV/RESTRICTED-FILES.md`: full, read first, including the 02:40 entry.
- `EV/phase2-20260927/prompts/common.md`, `u2-m2-continue.md` and `u2-m2-resume.md`: full.
- `EV/phase2-20260927/out/u2-m2-resume-PROGRESS-salvaged.md`: full.
- `EV/merge-watchers/recount-tiers.py`: full, then executed.

The lane did not open the cleared U2 availability statement or the public result memos; it did not need them.

**Earlier lanes' records:**

- The four m2 job manifests, parsed for keys and workspace only.
- The five transcripts above. They were parsed by script for event-type counts and tool-call inputs; no tool result was printed.
- The first lane's `.u2m2-work/exposure-log.md`, read in full.
- A pattern search of that lane's `jobs/*.py` and `worker.py`, which found no match.

**Names seen but not opened:**

- The listing of `~/.subfleet/jobs/*u2*`. It shows the names of the validation-only jobs `20260927-213944-u2-target-availability` and `20260927-223037-u2-values-scan`.
- The file names inside the four m2 job directories.
- The file names in this session's `~/.claude/projects/…/5375eb02-…/` directory. The orchestrator's session transcript there was not opened, because the orchestrator is not blind to U2.

**Repository:**

- `CLAUDE.md`.
- The specification: headings, §§4, 13, 14 and the §15 `decisions`/`blocked_by` lines.
- The m1 exposure record, first 80 lines, and the structure of its runtime JSON.
- The eight registries: hashes at three commits and a leaf diff of roles, weights and u1_identity. The lane printed the non-prose fields of three entries, which included one PSID codebook excerpt for `ER34651`, a documentary variable description.
- `u2_source_registry.py`, `psid.py` and `career.py` (named line ranges).
- Six U2 modules and five U2 scripts (named ranges).
- The birth-evidence script and its test.
- The U2 test files, with seven read in part.
- The root `tests/conftest.py`, `pyproject.toml`, `.gitignore` and the tier files.

Every range is listed in the JSON.

**Executed:**

- Every `tests/track_u2` file, one per command, with `-p no:xdist`.
- The same files under `-m unit`, with HOME and `POPULACE_DYNAMICS_PSID_DIR` pointed at an empty scratch directory and an audit hook that refused any open or listing under PSID. No access was refused.
- The §13 U1 suite under the same guard.
- `tests/estimates/test_birth_evidence_artifact.py`, `tests/test_benchmarks.py` and `tests/test_tier_policy.py`.
- `scripts/u2_u1_differential.py` on fresh detached checkouts of `9cee2423` and `12e1db0`.
- `scripts/track_u2_dry_run.py` at `12e1db0`, on invented data.
- `recount-tiers.py`, collection only.

The hook was active for the last three.

**Evidence-directory files opened by a test:** one run of the unmodified U1 test `tests/test_boomers2004_uniform_cut_spec.py` used the real HOME. It ran to check that the new `docs/design` files break nothing, and its three evidence-dependent tests ran instead of skipping:

- One read `EV/RESTRICTED-FILES.md` and checked for two strings about the 2026-09-24 16:10 exercise-2 values scan.
- One hashed `EV/exercise2-definitions-cleared-20260924.md`, which is cleared for builders.
- One hashed `EV/boomers2004-referee-20260924.md` and `EV/boomers2004-referee-2-20260924.md`. That was a SHA-256 comparison of bytes only, and neither file is on the restricted list.

The lane saw only the pass count. Logging audit hooks show that no `tests/track_u2` file, and no full test collection, opens anything under the evidence directory.

**PSID documentation opened by a test:** the plain per-file run of `tests/track_u2/test_psid_research_sources.py` (milestone 1b's documentary test) opens 32 documentation files under PSID. They are codebooks, questionnaires, user guides, weight reports and a digest list, all listed in the JSON. A logging audit hook on a repeat of the plain run shows that no other U2 test file opens anything under PSID. No survey record file was opened. The lane saw only pass counts.

## Reproducing the inventory

The inventory was built by two scratch scripts, `extract_calls.py` and `inventory.py`. They read each transcript line by line, keep only `tool_use` blocks from assistant messages (`Read`, `Write`, `Edit`, `Grep`, `Glob`, `Bash`, `Agent`), and resolve relative paths against the lane's worktree. `paths_named_in_commands` over-includes by design: it lists any existing path a command or subagent prompt names, whether the command read, wrote, ran, hashed or only mentioned it.

## Round-1 fix lane

This lane was a blind builder: a workflow subagent (Claude Opus 5.5), 2026-09-29. It fixed the independent review's findings on `f946334` in `0d742fd`, `8ec6953`, `9368931` and `b211ee7` (see the report's "Round 1 review fixes"). It worked in `/Users/maxghenis/PolicyEngine/_worktrees/dynamics-u2-m2-20260928` and kept scratch files in its session scratchpad. The machine-readable list is `round_1_fix_lane` in [`u2_m2_exposure.json`](u2_m2_exposure.json).

**Evidence directory (all builder-allowed):**

- `EV/RESTRICTED-FILES.md` in full, read first, including the 2026-09-29 02:40 entry (see the disclosure above; nothing here depends on it);
- `EV/phase2-20260927/prompts/common.md`, `u2-m2-continue.md` and `u2-m2-resume.md`, in full;
- `EV/phase2-20260927/out/u2-m2-build-and-review.json`:
  - its `review` part, which gives the verdict, findings, summary, evidence and the reviewer's files-opened list;
  - the `build` part was not printed;
- `EV/merge-watchers/recount-tiers.py`, read in full and run (collection only).

It did not open the cleared U2 availability statement or the public memos (not needed), any Boomers 2004 or Urban report page, any comparator lane or seal, any U2 or PPI availability or values-scan file, any scratchpad archive, or anything under REFS.

**Repository:** the files the fixes touch, in full or in the ranges needed. These are:

- `loader.py`, `parameters.py`, `identity.py`, `runner.py`, and parts of `sources.py`, `cohort.py` and `estimator.py`;
- the three U2 scripts it changed, and part of `u2_u1_differential.py`;
- the U2 test files it changed, and parts of `test_u2_pipeline.py` and `test_u2_isolation.py`;
- parts of `adjusted_poverty.py`, `data/psid.py` and `cohorts/psid2010.py`, read only;
- the specification's §14 and §20 and the §4 mapping-pass text;
- this record, the report and `CLAUDE.md`.

The registry `data/external/track_u2/individual.json` was parsed for entry ids, statuses, layouts, `codes` keys and the code lines of `codebook_text`. That text is PSID documentation, not survey values. No protected file was edited.

**Executed, all on invented data:**

- every `tests/track_u2` file, one per command, with `-p no:xdist` (the plain run);
- the same files again under two logging audit hooks: one on the PSID directory, one on the evidence directory and REFS;
- the §13 U1 suite and `tests/estimates/test_birth_evidence_artifact.py`. These ran with HOME and `POPULACE_DYNAMICS_PSID_DIR` pointed at an empty directory, and an audit hook refusing any open or listing under `~/PolicyEngine/psid-data`. It refused nothing, so the PSID-dependent U1 tests skipped. The three evidence-dependent U1 spec tests also skipped, because HOME was empty;
- `black` and `ruff`, and `recount-tiers.py` (collection only);
- two scratch scripts:
  - a before/after demonstration of the review's four cases, on invented staged files through the real loader with the tests' patches, against `f946334`'s code and the fixed code;
  - a floating-point probe of \(R-B\) over 1,500 drawn invented frames.

**Measured test exposure:**

- The logging hooks show that no test opens anything under the evidence directory or REFS.
- Under the PSID directory, only `tests/track_u2/test_psid_research_sources.py` opens anything: 32 documentation files, the same as the finishing lane recorded. They are 24 under `documentation/capture1` and 8 codebook or readme PDFs under `family/<wave>/` and `ind2023er/`. No survey record file was opened, and the lane saw only pass counts.
- One artifact of the measurement: under the PSID logging hook, `test_u2_differential.py` failed one test. The hook's own `realpath` call issues `lstat` calls that the test's access recorder counts. Without the hook the file passes 8 of 8.

**Values:** the lane stated and inferred no 1946–55 value or direction. Every number it added is one of these:

- an invented value, such as altered parameters, invented file digests or the invented population;
- a documented code or range copied from the registry's codebook text;
- a count of tests or of invented rows.

## Round-2 fix lane

This lane was a blind builder: a workflow subagent (Claude Opus 5.5), 2026-09-29. It fixed the round-2 review of `eeb4850` in `f78df52`, `b1d95c8` and `f16f1b9`, and recorded the fixes in the commit that adds this section (see the report's "Round 2 review fixes"). It worked in `/Users/maxghenis/PolicyEngine/_worktrees/dynamics-u2-m2-20260928` and kept scratch files in its session scratchpad. The machine-readable list is `round_2_fix_lane` in [`u2_m2_exposure.json`](u2_m2_exposure.json).

**Evidence directory (all builder-allowed):**

- `EV/RESTRICTED-FILES.md` in full, read first, including the 2026-09-29 02:40 entry (see the disclosure above; nothing here depends on it);
- `EV/phase2-20260927/prompts/common.md`, `u2-m2-continue.md` and `u2-m2-resume.md`, in full;
- `EV/merge-watchers/recount-tiers.py`, read in full and run (collection only).

The round-2 review reached this lane as text in its task. It did not open `EV/phase2-20260927/out/u2-m2-build-and-review.json`.

It did not open:

- the cleared U2 availability statement or the public memos (not needed);
- any Boomers 2004 or Urban report page;
- any comparator lane or seal;
- any U2 or PPI availability or values-scan file;
- any scratchpad archive;
- anything under REFS.

**Specification:** not opened. One repository grep for `u1_differential_` matched one line of `docs/design/boomers2004_1946_55_comparison.md` (line 1345). It printed only the key name `invented_dry_run_and_u1_differential_evidence`, with no value.

**Repository:** the files the fixes touch, in full or in the ranges needed. These are:

- `parameters.py` in full;
- parts of `runner.py` and `cohort.py`: the lines `check_person_joins` and the spouse-sex lookup use, for info 3;
- parts of `adjusted_poverty.py` (the life-table, threshold and SSI definitions and loaders) and of `data/tr2008.py` (the 2004 period-table reader), read only;
- the two U2 scripts it changed, and parts of `u2_u1_differential.py`;
- the U2 test files it changed, and part of `test_u2_pipeline.py`;
- path greps of the two Boomers U1 specification tests, to confirm an empty HOME makes their evidence-directory reads skip;
- this record, the report and `CLAUDE.md`.

No protected file and no milestone-1b-owned file was edited.

**Executed, all on invented data:**

- every `tests/track_u2` file, one per command, with `-p no:xdist`: the plain run, at `b1d95c8` and again at `f16f1b9`;
- the same files again under a logging audit hook on the PSID directory, the evidence directory and REFS.
  - The first attempt used `os.path.realpath`. It made `test_u2_differential.py` fail one test, the artifact round 1 also recorded.
  - The hook was changed to `os.path.abspath`, which touches no file, and the whole pass was rerun: every file passed.
- the §13 U1 suite and `tests/estimates/test_birth_evidence_artifact.py`, at `b1d95c8` and at `f16f1b9`.
  - They ran with HOME and `POPULACE_DYNAMICS_PSID_DIR` pointed at an empty directory, and an audit hook refusing any open, listing or stat under `~/PolicyEngine/psid-data`.
  - It refused nothing. Its self-test tried to open a nonexistent probe path there, and the hook refused that before any open.
- the U1 differential (`scripts/u2_u1_differential.py`), at `b1d95c8` and at `f16f1b9` against `9cee2423`, on `git clone --shared` clones in the scratchpad, with the refusing hook active;
- `black`, `ruff` and `recount-tiers.py` (collection only, `-p no:xdist`);
- scratch probes and temporary uncommitted tests:
  - a probe running eight altered-parameter routes against `eeb4850`'s check and the fixed one;
  - a temporary test on `eeb4850`'s runner (removed before commit);
  - the new parameter tests run once against `eeb4850`'s `parameters.py`, swapped in and restored from git;
  - the invented dry run, written into the scratchpad.

**Measured test exposure:**

- The logging hook shows that no test opens anything under the evidence directory or REFS.
- Under the PSID directory, only `tests/track_u2/test_psid_research_sources.py` opens anything: 32 documentation files, the same set as round 1. They are 24 under `documentation/capture1` (23 PDFs and `browser_digests.txt`) and 8 codebook or readme PDFs under `family/<wave>/` and `ind2023er/`. The lane printed their names and extensions, never their contents, and opened no survey record file.

**Values:** the lane stated and inferred no 1946–55 value or direction. Every number it added or printed is one of these:

- an invented value (1.0, or 12.0 a year);
- a count of tests;
- a hash;
- one of three public parameter values its probe printed from the committed captures: a Census weighted-average threshold, an SSI couple FBR and two NCHS 2000 survival values.

## Round-3 fix lane

This lane was a blind builder: the main session (Claude Opus 5.5), 2026-09-29 to 2026-10-11. A usage-limit cut-off paused it from 2026-09-29 to 2026-10-11. It fixed the round-3 review's three informational items and what its own verification found, in the commits from `5e8524c` to `c2f15bc` (see the report's "Round 3 informational fixes"). It worked in `/Users/maxghenis/PolicyEngine/_worktrees/dynamics-u2-m2-info-fixes-20260929`, first from `cd51fcb` and then rebased onto master (`dacbaa3`) after #487 merged. It merged master again (`db9725fe`) on 2026-10-11. The machine-readable list is `round_3_fix_lane` in [`u2_m2_exposure.json`](u2_m2_exposure.json).

**Evidence directory (all builder-allowed):**

- `EV/RESTRICTED-FILES.md`, read in full and first, including the 2026-09-29 02:40 entry. See the disclosure above; nothing here depends on it.
- `EV/phase2-20260927/out/u2-m2-review-r2.json`, read only through `jq`: the info-severity findings, the top-level key names and the verdict. The summary, evidence, files-opened list and other findings were not printed.
- Two name-only listings, from a `find` for `RESTRICTED*` under `EV` and a `grep -l` for `RESTRICTED-FILES` under `EV/phase2-20260927`. They printed file names only and opened nothing.

It did not open:

- the cleared U2 availability statement or any memo;
- any Boomers 2004 or Urban report page;
- any comparator lane or seal;
- any availability or values-scan file;
- any scratchpad archive;
- anything under REFS.

**Specification:** not opened.

**Repository:** the U2 package modules it changed or guarded, read in full or in the ranges needed: `runner.py`, `cohort.py`, `loader.py`, `sources.py`, `parameters.py`, `rows.py` and `estimator.py`. It also read:

- the definitions in `adjusted_poverty.py`, `identity.py`, and the return paths of `data/marriage.py` and `data/family.py`;
- the two U2 scripts it changed, and the U1 differential harness's docstring and runner;
- the U2 test files it changed, `conftest.py` and `test_u2_isolation.py`;
- this record, the report, the tier files, `CLAUDE.md` and PR #487's body.

No protected file and no milestone-1b-owned file was edited.

**Probes (invented data only):**

- A structure probe on the invented inputs and the loader-read invented staged files. It printed container, key, label, dtype, index and object-cell **types**, never values.
- A pandas probe of whether a `str` subclass survives in object and string dtypes, on the invented strings `male` and `female`.

**Executed, all on invented data:**

- Every `tests/track_u2` file, one per command, with `-p no:xdist`, after each pass.
- The fail-first runs of each pass's new tests. In the first and fourth passes it ran them against the earlier `src` in the worktree; in the third, in a `git clone --shared` scratch clone. It removed the clone afterwards.
- `tests/estimates/test_birth_evidence_artifact.py` and the §13 U1 suite. These ran with HOME and `POPULACE_DYNAMICS_PSID_DIR` pointed at an empty directory. An audit hook refused any open, listing or scan under the real `~/PolicyEngine/psid-data` and logged any under the evidence directory and REFS. It refused and logged nothing.
- The U1 differential (`scripts/u2_u1_differential.py`) against `9cee2423`, with the same hook active.
- `black`, `ruff`, and the tier recount (`pytest --collect-only -q -m <tier>`).

**Measured test exposure:** under the PSID directory, only `tests/track_u2/test_psid_research_sources.py` opens anything. As in rounds 1 and 2, those are documentation files (codebook and user-guide PDFs), never a data file. The lane saw only pass counts.

**Verification lanes:**

- Three rounds of in-session workflow subagents (Claude Opus 5.5, blind): `wf_0c8f41e8-01c` (four lanes), `wf_f7675756-346` (three lanes) and `wf_c037a7eb-127` (two lanes). The third round's mutation lane was cut off by the usage limit before it reported.
- A Subfleet mutation run (GPT-6.1 Sol, `20261011-113833-u2r3-mutation`).

Each lane read `EV/RESTRICTED-FILES.md`, worked in its own clone or an existing checkout on invented data, and opened nothing else under the evidence directory, REFS or PSID data. One second-round lane ran `test_psid_research_sources.py`, which opens the PSID documentation PDFs as above; it saw only counts and disclosed it. The lanes printed:

- invented offsets and invented-run counts, such as an invented U0 `n_poor_baseline` of 8 against 0;
- invented cells of the invented population;
- hashes and timings.

**Values:** the lane stated and inferred no 1946–55 value or direction. Every number it added or printed is invented, a count, a hash, a timing or a public parameter from the committed captures.

## Round-3 closeout lane

This lane finished PR #525 after the round-3 lane's owner session ended. It was the main session of a Claude Code session (Claude Opus 5.5, blind builder), 2026-10-15 to 2026-10-16, which the "Microcosm dynamics" coordinator handed the adopted PR. It merged master into the branch (`183c7ef3`), fixed what the closeout review, the mutation run and the delta review found (`e08b98dd`, `fcfc4025`, `ed82c02d`) and wrote the report's "Round 3 closeout" section and this entry. It worked in the worktree `.claude/worktrees/mystifying-nash-eec1cc` and in standalone clones under `~/reviews/pr525-closeout-20261015/`. The machine-readable list is `round_3_closeout_lane` in [`u2_m2_exposure.json`](u2_m2_exposure.json).

**Evidence directory (all builder-allowed):**

- `EV/coordinator/pr525-u2-m2-closeout-brief-20261015.md`, the coordinator's brief, read in full first.
- `EV/RESTRICTED-FILES.md`, read next: first its U2 and exercise-2 sections and a search of its text for U2, PSID and Boomers terms, then the whole file. The terminal view cut lines longer than about 300 characters. It includes the 2026-09-29 02:40 entry, so the disclosure above applies to this lane too; nothing here depends on it.

It did not open, list or search anything else under `EV`, `REFS` or `PSID`. In particular it did not open the cleared U2 availability statement, any Boomers 2004 or Urban report page, any comparator lane or seal, or any scratchpad archive.

**Outside the repository:**

- The round-3 lane's own Subfleet job folder for its fourth-pass mutation run (`~/.subfleet/jobs/20261011-113833-u2r3-mutation`): the job's prompt and its run metadata, to learn that the run had ended without a report. This lane adopted that work. It opened no other session's job folder except its own jobs' output and stream logs.
- `/private/tmp/claude-501/pr525-guard.log`, a guard log this lane created there, found empty and deleted; later logs went under the review folder. A host restart cleared the lane's scratchpad on 2026-10-16.

**Specification** (`docs/design/boomers2004_1946_55_comparison.md`): opened for the §20 follow-up, not for this PR's code. It read the header (lines 1–15), §3's identification paragraphs (lines 106–135), §4's required manifests and mapping pass (lines 267–334), §14's registered-run preflight (lines 1021–1036), §15's `ssi` entry and `blocked_by` list (lines 1220–1352), the section headings, §17, §19's changelog and §20. The parts it read state no comparator value.

**Repository:** the files the merge and the fixes touched or depend on, read in the ranges needed: `runner.py`, `cohort.py`, `loader.py` and `sources.py`, plus `parameters.py` around the SSI pin. It also read:

- the U2 test files it changed or ran (`test_u2_loader.py`, `test_u2_scripts.py`, `test_u2_parameters.py`, `test_adjudication_applied.py`);
- `scripts/u2_u1_differential.py`, `scripts/run_track_u2_registered.py` and `scripts/track_u2_dry_run.py` (line checks);
- this record, the report, `docs/design/u2_m1_source_adjudication.md` (header and blocker table), the tier files, the CI workflows, `CLAUDE.md` and PR #524, #525, #539 and #540's bodies and comments.

**Executed, all on invented data, every Python command under an audit hook** that refused any open, listing, scan or glob under `PSID`, `EV` or `REFS`, with HOME and `POPULACE_DYNAMICS_PSID_DIR` pointed at empty directories:

- the tier recount (`pytest --collect-only -q -m <tier>`) at `183c7ef3` and again after the fixes;
- every `tests/track_u2` file and the U2 data and birth-evidence files, at `183c7ef3` and after the fixes. One differential test first failed because the hook's own path resolution made the `lstat` calls that test records; the hook was changed to resolve paths without touching the file system, and the test passed;
- the §13 U1 suite at `183c7ef3`, `e08b98dd` and `ed82c02d`;
- the U1 differential (`scripts/u2_u1_differential.py`) against `9cee2423` at `183c7ef3`, `e08b98dd` and `ed82c02d`;
- probes of the rebuild on invented one-column frames (whitespace, tab, NUL, missing values), and a mutant-kill check that applies each closeout mutant by exact string replacement, runs its new tests and restores the file;
- `black` 26.5.1 and `ruff`.

The hook refused nothing at any of these runs. Its only refusals were the self-tests, on a nonexistent probe path under `PSID`.

**Verification lanes:**

- In-session workflow `wf_f2fc33e9-92a` (four mutation lanes and a reviewer, Claude Opus 5.5, own clones): stopped at the account's weekly limit during their baselines and returned nothing. Their transcripts name no restricted path except the reviewer's hook self-test (a nonexistent probe path under `PSID`, refused) and a search of the repository's test files for the three directory names.
- One in-session agent for the §20 evidence map: stopped before its first tool call.
- Subfleet, each in its own standalone clone with the same hook:
  - `20261015-145340-pr525-mut-a` (Claude Opus 5.5): finished; mutants 2–8.
  - `20261015-145341-pr525-mut-b`, `-mut-c` and `-mut-d` (Claude Opus 5.5): ended by provider errors when the host restarted, before their reports. Their stream logs and progress files hold their per-mutant results.
  - `20261015-145341-pr525-review` (GPT-6.1 Sol): cancelled before launch, as the Codex lanes were held.
  - `20261015-145546-pr525-review-opus` (Claude Opus 5.5): the closeout review, APPROVE.
  - `20261016-015339-pr525-delta-review` (Claude Opus 5.5): the delta review of `183c7ef3..a1858bb9`, APPROVE.
  - `20261015-225702-pr525-mut-b2` and `-mut-d2` (Claude Opus 5.5): finished; the mutants the restart left unrun, at `e08b98dd`.

    Lane b2 noted that `test_u2_roles.py::test_exclusion_dispositions_are_the_ratified_names` reads the U2 specification for its disposition names. So does `test_adjudication_applied.py`. Every run of those files (this lane's, the review's and the mutation lanes') read the specification through those tests only.

  Every lane read `EV/RESTRICTED-FILES.md`'s rules from its brief, not the file. No lane's stream log shows a refusal by the hook or a tool input that names a restricted directory; the only matches are listings of the hook's own source. The hook logs of mut-a, mut-c, b2, d2, both reviews and this lane are empty. This lane truncated the hook logs of mut-b and mut-d without reading them when it reset those clones for the finishing lanes; their stream logs are the record for those two.

**The §20 follow-up (#544).** The same lane then cut #544 from master `f7a84d0b`: the §17, §19 and §20 record; the SSI changed-bytes test; and, after its review asked for it, the frame environment in the pre-registration evidence record. It read only the specification ranges listed above and the merged PR records (#481, #486, #487, #500, #524, #525, #540). It ran the U1 differential at `f7a84d0b` and the U2 files under the same hook, which refused nothing. Its independent reviews (`20261016-140335-pr544-review` and `20261016-152540-pr544-review-r2`, Claude Opus 5.5, in the standalone review clone with the hook) read the specification too, and nothing else restricted; the second read its header, section headings, §15's `decisions` and `blocked_by`, the §17, §19 and §20 changes and §20, and saw one grep line of the first appendix, which holds no value.

**The d1242 change.** After #544 merged (`2ef10532`), the same lane applied Max's d1242 ruling: B2 joins `sources.PERSON_COUNTED_EXCLUSIONS`, with its tests and a §19 entry. It read only the decision ledger's d1242, d1597 and d1649 entries, the code it changed and the roles tests. It ran the U2 files under the same hook, which refused nothing. Answering #546's review, it added an invented variant (a second, sex-unknown code-92 member in one excluded 2019 unit) and a distinct-person form of each count. For this it read the review, the invented-data generator, the runner and the scripts test. It ran the reviewer's mutations and the U2 files under the same hook, which refused nothing.

**Values:** this lane and its lanes stated and inferred no 1946–55 value or direction. Every number they printed is invented (offsets, invented cells, invented-run counts and dispositions), a count, a hash, a timing or a public parameter from the committed captures.

## d1724 lane (2026-10-19)

A Claude Code session (Claude Opus 5.5), started by the dynamics coordinator session (`local_6085d52a-…`), applied Max's ruling d1724 (specification §16d) in a standalone clone of `origin/master` at `640adccf`. It read no PSID record and no comparator, and it does not forecast U2.

**Read:**

- `EV/RESTRICTED-FILES.md` itself, in full, as its brief required, to know what not to open. It opened nothing the file lists.
- The coordinator's shared notes folder: the step-4 pass session's value-free note and the d637 registry session's note.
- The chief-of-staff decision ledger's d1649 and d1724 entries (decision, ruling and status lines), and, on 2026-10-20, d1724's two notes (Max's approval of the widening, and the coordinating session's correction on code 999).
- In `EV/track-u2-step4-pass-20261019/`: the directory listing (file names only) and the SHA-256 of `MANIFEST.md`, computed without printing it. It did not open `track-u2-structure.stderr.txt` (restricted), its masked copy, or any other file there.
- The repository: the U2 package, `estimates/career.py` (`derive_birth_years` and its constants, unchanged), Track M's `structure.py` and `cohort.py` (the count-out precedent), the U2 scripts and tests, `tests/conftest.py`, the specification (its header and §§3, 16c, 17, 19 and 20, and the tests' pins) and this file.

**Ran:** the U2 test files, the new `tests/track_u2/test_u2_birth_bounds.py` among them, with `POPULACE_DYNAMICS_PSID_DIR` set to an empty directory, which stayed empty; so the checks that need PSID documentation skipped. It ran `career.derive_birth_years` and master's `cohort.derive_u2_births` (read from Git at `640adccf`) on invented inputs only, to show the fix equals master wherever master's law completes. It ran Black, Ruff, the tier recount by collection and the mutation checks listed in the PR.

**Values:** it stated and inferred no 1946–55 value or direction. Every number it printed is invented (generator persons, ages and counts), a test count, a hash, or a constant of the code (`career.DERIVED_BIRTH_MIN` and `DERIVED_BIRTH_MAX`, 1889 and 2016).

**2026-10-20, the widened rule.** The coordinating session asked that the rule also cover seeds whose age code the law refuses, and later reported that Max approved that widening, re-seeding of code 0 included. The lane read the coordinator's messages, d1724's two notes in the decision ledger (to cite the approval and its correction), the loader's documented age domain and its value check (`loader.py`), and the code and tests it changed. It read nothing else outside the repository, and its runs were as above: an empty PSID directory, invented inputs only, and the mutation check, all listed in the PR.

**Review lane.** Subfleet `20261020-030251-d1724-review-552b` reviewed head `8a6a8192` and returned APPROVE. No Codex lane could admit the job, so Subfleet served it on Claude Opus 5.5 (lane `claude-7`), in its own standalone clone with its own virtual environment. The lane reports that its empty PSID directory stayed empty and that it opened nothing under the evidence directory, `REFS` or `PSID`. It loaded master's `cohort.py` from Git and ran invented inputs only. Its scratch scripts were in `/tmp/review552`. Its findings (two test gaps, one record-accuracy point, nits) were addressed in the next commit, which declined one (the header's version line, pinned as d1090's `header_version` clause). The delta review (Subfleet `20261020-045107-d1724-review-552-delta`, GPT-6.1 Sol) approved that commit. Records: `EV/rulings-records-20261019-d1724/review-552-out.md`.

## §20 steps 4–6 lane (2026-10-21)

A Claude Code session (Claude Opus 5.5), started by the dynamics coordinator session (`local_6085d52a-…`), recorded §20 step 4, materialized the final parameter block and U2's rulings record (§20 step 5), and takes the ratifying merge through review (§20 step 6), in a worktree of `origin/master` at `1e739d32`. It read no PSID record, computed no PSID statistic and opened no comparator. It may later be asked to forecast U2 or check a U2 forecast, so everything it read is listed here.

**Read:**

- `EV/RESTRICTED-FILES.md`, in full and first, through a saved copy of the tool output in this session's own transcript folder. No other session's file in that project folder was opened. The harness also auto-loaded that project's memory index (`MEMORY.md`, one-line pointers); no memory file was opened.
- `EV/track-u2-step4-pass-20261021-run2/MANIFEST.md`, which the restricted list allows to be read and cited, and its SHA-256, which matched `acf5d8a4…e6d`. No other file in that folder and nothing in `EV/track-u2-step4-pass-20261019/` was opened or listed.
- The chief-of-staff decision ledger's entries for d514, d637, d745, d1090, d1242, d1597, d1649 and d1724 (decision, ruling, ruling time and notes), selected by id, and the names in its folder.
- On 2026-10-22, to check the review's finding 1: the field names of the d1597, d1649 and d1724 ledger records; d1724's `why` field, which states that the first pass (2026-10-19, `640adccf`) passed d1597's U1 load; and d1649's `ruling`, which requires that load to run before the pass.
- The coordinating session's brief, the message that started this lane, and its later messages of 2026-10-21 and 2026-10-22. They carry value-free facts only: the step-4 outcomes this lane records, the evidence record's SHA-256 as its MANIFEST pins it, and the tier-slot queue.
- The review lane's report, `EV/rulings-records-20261021-u2-step5/review-r1b-out.md`, and the names in the evidence folder that match `rulings-records` (names only).
- The repository at `1e739d32`: `CLAUDE.md`; the specification in full; the U1 specification's header, §15 block and §20; the U2 package, scripts and tests named in the PR; `data/external/track_u2/u1_identity.json` and the registries' entry ids and fields; the U2 SSI capture's provenance fields and its source manifest's records; `tests/README-tiers.md`; Track M's `specification.py` header; `estimates/cola_age_profile.specification_unratified_fields`. Also `~/PolicyEngine/CLAUDE.md`.

**Not opened:** any other evidence-folder path; any comparator folder, seal or Boomers Report copy; `runs/track_b_b2_*`, `docs/design/track_b_attempt_ledger.md` and `paper/paper.qmd`; other sessions' transcripts or scratchpads; `~/.subfleet/` other than this session's own review jobs; any PSID file or codebook.

**Who and where.** This lane is the Claude Code session `59b436cf-29b0-43ac-a811-411fcc960646`. Its scratchpad, `/private/tmp/claude-501/-Users-maxghenis-Library-Application-Support-Claude-scratch-workspaces-ee3763f4-…-scratch-2026-09-22-b65ec9/59b436cf-29b0-43ac-a811-411fcc960646/scratchpad/`, is its own. Until the host wiped it, on 2026-10-22, it held this lane's virtual environment (`venv/`), the empty PSID directory (`empty-psid/`), its mutation runners and its differential reports. From then on they live outside the repository: the virtual environment at `~/PolicyEngine/_clones/md-u2-step5-venv` (Python 3.14.7; pandas pinned to 3.0.6, the version the step-4 evidence froze), the empty PSID directory at `~/PolicyEngine/_clones/md-u2-step5-empty-psid`, and the mutation runners at `~/PolicyEngine/_clones/md-u2-step5-mut`. The lane opened no other session's scratchpad or transcript.

**Ran:**
- **Tests.** The U2 and U1 test files, the specification tests and the birth-evidence artifact test, with `POPULACE_DYNAMICS_PSID_DIR` set to the empty directory, which stayed empty, so the checks that need PSID documentation skipped. Also Black and Ruff, the tier recount by collection, and the mutation checks listed in the PR.
- **Block, rulings and appendix checks.** Every one reads only the specification, the committed registries and the code. After the PSID hold of 2026-10-23 was lifted (d1899), one identity test loads U1's committed artifact in memory to compare one hash, and prints nothing. While the hold stood, this lane ran only unit-tier and specification tests.
- **The U1 differential** (`scripts/u2_u1_differential.py`, invented data only, with the empty PSID directory and this lane's virtual environment). Its two checkouts are worktrees of this repository: the base, `~/PolicyEngine/_clones/md-u2-diff-base-9cee2423`, detached at `9cee2423`, and the candidate, `~/PolicyEngine/_clones/md-u2-diff-cand`, detached at the head under test.
  - **Trial at `690a1276`** (2026-10-21): equal in every check.
  - **At `1742efb1`** (2026-10-22): equal in every check; report committed as `docs/design/u2_m2_u1_differential_1742efb.json`.
  - **At `14d9576a`** (2026-10-23), the revision's last code change: equal in every check; report committed as `docs/design/u2_m2_u1_differential_14d9576.json`. This run and every later one used the relocated virtual environment and empty PSID directory.
  - Each run's dry run wrote only to a temporary directory the harness made and removed.

**Values:** it stated and inferred no 1946–55 value or direction. Every number it wrote is a hash, a commit, a CI run id, a date, a line number, a registry entry count, a test count or a constant of the code or the specification.

**Review lanes.**
- **Subfleet `20261021-104325-u2-step5-review-r1`.** It waited for capacity and was cancelled before it launched, so it read nothing.
- **Subfleet `20261021-105010-u2-step5-review-r1b`.** It reviewed `690a1276` and returned REQUEST CHANGES. It ran on Claude Opus 5.5, in a standalone clone (`~/PolicyEngine/_clones/md-u2-step5-review-20261021`) with its own virtual environment.
  - **What it read outside the clone:** `EV/RESTRICTED-FILES.md`, the run-2 `MANIFEST.md`, and the eight decision-ledger records selected by id.
  - **Its runs:** the test suites with the empty PSID directory, which stayed empty, and its own U1 differential in clones under `/tmp/u2rev-diff`.
  - **Its two disclosures:**
    - One early command wrote git-ignored bytecode caches under the review clone's `src/`.
    - Two `grep` searches over `docs/design/` scanned the bytes of `track_b_attempt_ledger.md` for fixed literals, with nothing from that file printed. That file is restricted for B2-successor work, not for U2; this record lists it for completeness.
  - It opened no other evidence path, PSID file or comparator. Its findings were addressed in the next commit (§19).
- **Subfleet `20261021-214735-u2-step5-review-r2`.** It ran on GPT-6.1 Sol and reviewed `9f79818a` in full. It returned REQUEST CHANGES: one blocking finding (§20 step 6 dated the merge) and should-fix and nit findings, all answered in the following commits (§19).
  - **What it read outside its worktree:** `EV/RESTRICTED-FILES.md`, the run-2 `MANIFEST.md`, the round-1 report and the eight decision-ledger records selected by id.
  - **Where it worked:** in its own Subfleet worktree, writing nothing into the review clone.
  - **Its three disclosures:**
    - A `grep -rln` over `runs/` for the U1 pin's hex scanned the bytes of `runs/track_b_b2_*` and `runs/m2_pseudo_projection_v1.json`. Nothing from either file was printed.
    - A `git archive` copy it started under `/tmp/r2rev/mut` may have included restricted files. It deleted the copy unopened.
    - It loaded U1's artifact in memory to compare one hash, printing a boolean.
  - It opened no PSID file, codebook or comparator, and the empty PSID directory stayed empty.
- **Subfleet `20261023-062935-u2-step5-review-r3`.** It waited for capacity and was cancelled before it launched, so that one review could also cover finding 6's commit. It read nothing.
- **Subfleet `20261023-063829-u2-step5-review-r3b`.** It ran on GPT-6.1 Sol and delta-reviewed `a2e2d688` against `9f79818a`. It returned APPROVE, with one nit about this record's wording, answered in the next commit.
  - **What it read outside its worktree:** `EV/RESTRICTED-FILES.md`, the run-2 `MANIFEST.md`, the round-2 report, the eight decision-ledger records selected by id, and a review-workflow skill file (`~/.agents/skills/gitnexus-pr-review/SKILL.md`). It also listed the empty PSID directory, which was empty.
  - **Its runs:** the full related suites with the empty PSID root, after the PSID hold was lifted. They read committed artifacts as CI does, and it printed no value from them.
  - It opened no PSID record or codebook and computed nothing from PSID records.
- **Subfleet `20261023-073938-u2-step5-review-r4`.** It ran on GPT-6.1 Sol and delta-reviewed `ac808d4a` against `a2e2d688`. It returned APPROVE, with one nit about the order of §19's entries, answered in the next commit. It read the round-3 reports, and in the clone it ran the specification tests with the empty PSID root. It opened no PSID file.
