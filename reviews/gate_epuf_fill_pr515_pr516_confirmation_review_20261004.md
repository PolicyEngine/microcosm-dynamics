# Confirmation review: PRs #515 and #516 after code review

**Verdicts (provisional):**
- **PR #515: APPROVE WITH NITS.**
- **PR #516: APPROVE WITH NITS.**

Every finding from both reviews is either fixed or left on purpose and recorded. I found no new correctness bug in the fixes. I found two new Low findings, both best fixed before the TEST run rather than before merge, and a few nits.

**This session had read and search tools only, with no shell.** So I could not run `git diff`, `git show 61349f0b:…`, `sha256sum` or pytest. Everything below comes from reading the files at `2cebe01e`. The checks that need a shell are listed at the end; the verdicts hold only if they pass.

## Prior findings

### PR #515 review

| # | Sev | Finding | Status | Evidence |
|---|---|---|---|---|
| 1 | Med | A run with injected inputs looks like the registered one; a `None` SHA was accepted | **Fixed** | `epuf_fill_scoring.py:196-205` requires a 64-character lowercase hex SHA-256 for every role before anything loads. `:219-224` adds `injected` and sets `registered_test_scoring` to false whenever either input is injected. Tests at `test_epuf_fill_scoring.py:150-159` and `:177-194`. `load_fill(sha256=None)` still skips its check silently (`epuf_fill.py:1695`), but `score_registered` can no longer reach that path. |
| 2 | Low | #515 alone cannot import `epuf_fill` | **Disclosed** | `registration_proposal.md:12` says "#516 merges before TEST is read". I could not see the GitHub PR description. |
| 3 | Low | The hash-check test never reached a hash check | **Fixed** | `test_epuf_fill_scoring.py:162-174` writes a real file with the wrong bytes and expects `ValueError` matching "SHA-256". |
| 4 | Low | Nothing tested the "smaller of the two readings" rule end to end | **Fixed in substance** | `:197-290` checks the per-cell minimum on real fallback and two-sided readings. `:312-334` shows the combined reference changing a tier. The review asked for the opposite direction, which `adoption_tier` makes impossible; the new test checks the correct one. Its docstring is wrong (N3). |
| 5 | Nit | The odd-oracle test did not check strata | **Fixed** | `test_epuf_fill_gate.py:399-421` compares the multiset of values within each stratum. Its key matches `odd_oracle_fill` (`epuf_fill_gate.py:1262-1269`; the age edges are `range(20,85,5)` in both). |
| 6 | Nit | A malformed `gates.yaml` raises `AttributeError` | **Left on purpose, recorded** | `epuf_fill_gate.py:1427-1429` is unchanged. Recorded in `registration_proposal.md:754-755`. |
| 7 | Nit | Tolerance table rounding | **Fixed** | `registration_proposal.md:542-550`: q50 0.074, pzero 0.128, r1 0.0025 (0.00248 at the lower bound). |
| 8 | Nit | Literal `2` in the builder | **Left on purpose, recorded** | `build_epuf_fill_gate_floors.py:228` is unchanged. Recorded in `registration_proposal.md:756-757`. |

### PR #516 review

| # | Sev | Finding | Status | Evidence |
|---|---|---|---|---|
| 1 | Med | Learned odd fills break on PSID gap years with no visible neighbour | **Fixed** | `psid2010_epuf_fill.py:139-157`: `odd_years` defaults to `SCORED_ODD_YEARS` (1997-2005). Every gap year is hidden from the fills, whether filled or not. A gap year is filled only if a neighbour in `given` is finite, and `given` already hides pre-career years and `boundary_2014`. Both `OddKnnFill` (`epuf_fill.py:970-990`) and `OddForestFill` (`:657`) handle a right neighbour only, so neither can return NaN on a row that reaches them. The docstring states the extrapolation (`:11-20`). Tests: the seam and the no-neighbour start at `test_psid2010_epuf_fill.py:188-224`, and the default scope at `:164-185`. |
| 2 | Med | The donor cache was keyed by `id(self)` | **Fixed** | `bank_digest` (`epuf_fill.py:1225-1240`) hashes sex, birth year, match vector, block and `k`. The cache key (`:1249-1255`) uses that digest instead of `id`. A test covers it, weakly (N4). |
| 3 | Med-low | The fit script overwrote staged files before refusing | **Fixed** | `fit_epuf_fills.py:169-173` refuses an existing manifest before reading TRAIN. `:188-196` never replaces a staged file with other bytes and writes new files with `"xb"`. |
| 4 | Low | float32 thresholds can leave a leaf empty | **Fixed for the quantile forest** | `epuf_fill.py:536-541` raises at fit if a leaf is empty; `test_epuf_fill.py:198-200` checks it. Thresholds stay float32, so the bytes are unchanged. There is no comparison against `apply`, which is acceptable because the stored traversal is used for both fitting and drawing. The zero forest is not checked (N5). |
| 5 | Low | Uncoded sex got no copula | **Fixed** | `BySexFill.fill` passes `np.full(len(rows), value)` (`:1643-1653`). Tested at `test_epuf_fill.py:182-195`. |
| 6 | Low | "Byte-reproducible" depends on the environment | **Fixed** | `fit_epuf_fills.py:218-224` records the Python version, zlib runtime and platform, and the manifest carries them. The registration document qualifies the claim (`:26-31`). |
| 7 | Low | Provenance gaps in the scripts | **Fixed** | Score script: pins the manifest SHA-256 (`:35-38`, `:76-80`), records `code_files_clean` (`:82-89`), writes file names only (`:115-117`), writes a started marker (`:97-109`), and checks the lock first (`:92-96`). Fit script: `CODE_FILES` now includes `epuf_fill_gate.py` and `epuf_operator.py` (`:45-50`). |
| 8a | Nit | Stale `PreDonorFill` docstring | **Fixed** | `:1137-1153` now describes seven features, `bank_size`, and "scaled by seven". |
| 8b | Nit | `start_year` was really the last year | **Fixed** | Renamed to `last_year` and documented (`:99`, `:107-108`). |
| 8c | Nit | `bank_block` was not clipped | **Fixed** | `np.clip(values, 0, 1)` at `:1218-1220`. |
| 8d | Nit | `ok` always True in `PreChainFill` | **Fixed** | It is no longer in `PreChainFill.fill` (`:1508-1564`). |
| 8e | Nit | `match_vector` used PSID years after 2006 | **Fixed** | `_BANK_LAST_YEAR` limits the summaries (`:1078`, `:1089-1093`). |
| 8f | Nit | The copula test did not check the coded-sex row | **Fixed** | `test_epuf_fill_candidates_manifest.py:101-105` asserts each coded-sex row is nonzero in the registered manifest. |
| 8g | Nit | `n_units` applies per sex | **Fixed** | `candidates_registration.md:57`. |

## New findings

**N1. Low: the started marker can record a TEST read that never happened, and block the one run.** `scripts/score_epuf_fill_test.py:97-113`, `epuf_fill_scoring.py:206-221`
- **What happens:** the marker is written before `score_registered` runs. `score_registered` loads and hash-checks the candidate files before it calls `test_part`. So a wrong `--fills-dir`, an unstaged file or a SHA mismatch leaves `<output>.started.json` behind although TEST was never read.
- **Effect:** a rerun with the same `--output` fails on `open("x")`. The operator then has to delete a marker whose whole purpose is to be a trace of the read.
- **Fix:** hash-check the staged files against the manifest before writing the marker, or give the marker a `phase` field and update it after `test_part` returns. `score_epuf_fill_test.py` is not a pinned file, so this needs no refit. It should land before the TEST run.

**N2. Low: no test ties `REGISTERED_MANIFEST_SHA256` to the committed manifest, and the score script has no tests.** `scripts/score_epuf_fill_test.py:36-38`
- **Fix:** in `tests/test_epuf_fill_candidates_manifest.py`, assert that the SHA-256 of `MANIFEST` equals the script's constant. Also test that the script refuses another manifest, refuses before lock, and refuses an existing output.

**N3. Nit: a test's docstring contradicts the rule it tests.** `tests/harness/test_epuf_fill_scoring.py:198-205`
- **What's wrong:** it says the combined reference "admits it as 'improves' where the fallback alone would not". `adoption_tier` (`epuf_fill_gate.py:1072-1083`) makes that impossible: a smaller current gap and a smaller failing count can only tighten the tier. That is what the test at `:312` correctly checks.
- **Also:** the test never asserts that some gating cell actually differs between the two readings.
- **Fix:** reword the docstring, and assert that at least one cell's fallback and two-sided gaps differ.

**N4. Nit: `_BANK_DIGESTS` keeps every digested `PreDonorFill` alive forever.** `epuf_fill.py:1069`, `:1229-1240`
- **Effect:** the registered run uses one fill, but anything that fits fills in a loop holds every bank in memory.
- **Test gap:** the cache test (`test_epuf_fill.py:162-179`) keeps both fills alive, so it never reproduces the original address-reuse bug. It only checks that the digests differ.
- **Fix:** use `functools.cached_property`, which works on a frozen dataclass without slots. This file is pinned, so either record the nit or fix it together with a refit.

**N5. Nit: the zero forest has no empty-leaf check.** `epuf_fill.py:831-833`
- **Effect:** an empty leaf silently gets `p = 0` through `hits / np.maximum(total, 1)`. This is the same float32 cause as #516's finding 4.
- **Fix:** raise there as `fit` now does for the quantile forest. If no leaf is empty, the bytes do not change. The file is pinned, so either record the nit or fix it with a refit.

**N6. Nit: the score record can claim the registered scoring under a non-default `gates_path` or `data_dir`.** `epuf_fill_scoring.py:223`
- **Effect:** neither argument is recorded, so a run pointed at a substitute `gates.yaml` would still set `registered_test_scoring` to true. The score script never passes them.
- **Fix:** add both to `injected`. Separately, the score script's `CODE_FILES` (`:40-45`) leaves out `epuf_cells.py` and `epuf_operator.py`, which scoring uses.

**N7. Nit, older than the fixes: the module docstring overstates the pre-career fill.** `psid2010_epuf_fill.py:21-23`
- **What's wrong:** it says every year before the career start becomes the pre-career draw. Years the PSID recorded before the career start keep their value, because only `pre_mask & ~in_career` is added (`:190`).
- **Fix:** reword the docstring.

## Questions 2-4

**2. The fixes introduce no new bug that I found.** Item by item:
- `score_registered`: the SHA-256 check runs before any load, and the `injected` flags are correct.
- `fill_careers`: the `odd_years` scope, the no-visible-neighbour rule and `last_year` all index correctly (`years[columns]`, with the `inside` filter applied before `gap`).
- `bank_digest` and `_NEAREST_CACHE`: the digest is keyed by content and the cache is bounded at 4 entries. Only N4 remains.
- `BySexFill` routing is correct.
- The empty-leaf check is correct where it applies (N5 is the gap).
- `match_vector`'s 2006 limit is correct.
- The fit script refuses before reading TRAIN and never overwrites a staged file.
- The score script pins the manifest and checks the lock before writing the marker. N1 is about where the marker sits.

**3. The refit:**
- **Manifest:** `code_commit` is `598e4436…`, which comes after the fixes commit `358ad0d2`, and `code_files_clean` is `true`.
- **Artifact SHA-256 values:** they match the registration document's table. The untracked `.diag/epuf-fill/dev_registered_dryrun.json`, which looks like the dry run's output record, also contains all four. That supports the claim that the DEV dry run loaded these same bytes. I could not compare against `git show 61349f0b:runs/epuf_fill_candidates_v1.json`. The committed log records only the old manifest's SHA, `8d421536…` (`dev_scores_after_round_2.jsonl:17`).
- **Manifest pin:** the score script pins `a3043113…`, the same value the registration document gives. I could not compute the file's actual hash.

**4. The DEV dry-run claim holds.** No fix changes a draw for a scored person:
- **Uncoded sex:** EPUF codes sex 3 as unspecified (`data/epuf.py:11`). Every population is restricted to `_coded` sex, 1 or 2 (`epuf_fill_gate.py:472-473`), so the persons whose draws changed are never in a cell.
- **`match_vector`:** EPUF's years end at 2006, so the new limit changes nothing on EPUF.
- **The cache:** only its key changed, not the values.
- **The clip and the leaf check:** neither changes the bytes, which the matching SHA-256 values confirm.
- **Other persons:** draws are keyed by person, and an existing test (`test_epuf_fill.py:100-113`) shows they do not depend on the other persons' order.
- **The PSID path:** EPUF scoring does not use it.

**5. Merge readiness.** Apart from the known blockers (#509 first, ratification d927, CI shard 1), both PRs are ready once the commands below pass. N1 and N2 should land before the TEST run, not necessarily before merge. N4 and N5 touch the pinned `epuf_fill.py`, so the simplest course is to record them as #515's two nits were recorded.

## What I verified, and what I could not

**Verified by reading at `2cebe01e`:**
- every prior finding, against the code and tests cited above;
- both proposal notes for the nits left in bound files;
- the manifest fields and the registration document's SHA-256 values, environment and claims;
- the birth-evidence exclusions (`first_estimates_birth_evidence.py:356-361`);
- that the oracle test's strata match the code.

**Not run (needs a shell):**
```
git diff e1f10808 2cebe01e --stat
git diff 598e4436 2cebe01e -- src/populace_dynamics/estimates/epuf_fill.py src/populace_dynamics/harness/epuf_fill_gate.py src/populace_dynamics/harness/epuf_operator.py scripts/fit_epuf_fills.py   # expect empty
git show 61349f0b:runs/epuf_fill_candidates_v1.json | grep '"sha256"'   # expect 37a9ea76…, 8c7d323d…, 8bb48b02…, 3c31fbd3…
shasum -a 256 runs/epuf_fill_candidates_v1.json                            # expect a304311343f3…62d0
git diff 70553e70 e1f10808 -- src/populace_dynamics/harness/epuf_fill_gate.py scripts/build_epuf_fill_gate_floors.py   # expect empty (bound files)
PYTHONPATH=src .venv/bin/python -m pytest tests/estimates/test_epuf_fill.py tests/cohorts/test_psid2010_epuf_fill.py tests/test_epuf_fill_candidates_manifest.py tests/harness/test_epuf_fill_scoring.py tests/harness/test_epuf_fill_gate.py tests/test_epuf_fill_gate_floors.py tests/estimates/test_birth_evidence_artifact.py -q -p no:cacheprovider
```

I made no edits, commits or GitHub posts, and I read no EPUF microdata. This session had no Write tool or plan-mode exit, so this review is the whole output.