# U2 milestone 2 exposure record

This record covers every lane that built or reviewed U2 milestone 2 (the implementation of specification §§13–14 on invented data), the lane that finished it on 2026-09-29, and the lane that fixed the round-1 review's findings ("Round-1 fix lane", below). The machine-readable inventory is [`u2_m2_exposure.json`](u2_m2_exposure.json). It holds every path each lane read, wrote, searched or named in a command, plus the restricted-path check.

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
