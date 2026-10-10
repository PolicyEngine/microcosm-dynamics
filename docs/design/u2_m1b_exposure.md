# U2 milestone 1b: exposure and reading record

Complete list of the files, directories and URLs that the milestone-1b builder opened on 2026-09-28 (Claude Code, Opus 5.5, headless Subfleet job `20260928-150318-u2-m1b`), and of the independent reviewer it dispatched. The builder worked blind: it did not open the Boomers 2004 report, any comparator lane or seal, any public result memo, or anything else that `EV/RESTRICTED-FILES.md` restricts, and it states and guesses no 1946–55 value or direction. No raw PSID data file was opened, and no poverty, benefit or estimator run was made.

Roots: `EV` = `/Users/maxghenis/microcosm-launch-evidence/dynasim-parity-20260909`; `PSID` = `/Users/maxghenis/PolicyEngine/psid-data`; `WS` = the job workspace `/Users/maxghenis/.subfleet/worktrees/20260928-150318-u2-m1b` (a checkout of branch `dynamics-u2-impl-20260928` at `79451eb4`); `SCRATCH` = `/tmp/u2m1b` (builder scratch outside the workspace; see Procedural notes).

## Instructions and cleared material

- `EV/RESTRICTED-FILES.md`: read in full, first.
- `EV/phase2-20260927/prompts/common.md`: read in full.
- `EV/u2-target-availability-cleared-20260928.md`: read in full; it is on the cleared-for-builders list.
- `EV/phase2-20260927/out/u2-adjudicate.md`: read in full and hashed (SHA-256 `a891762bf9be39e05509e59c5b7cd3fdab0eb34feb9ad5b9bb4a8ec3afc39662`, 26,564 bytes).
- `/Users/maxghenis/.claude/CLAUDE.md` and `WS/CLAUDE.md`: injected at session start.

The four public result memos, `EV/parity-phase2-plan-20260927.md`, its review and `EV/dynasim-scorecard.md` were not opened.

## Repository files (workspace)

Read in full:

- `src/populace_dynamics/data/u2_source_registry.py`
- `tests/track_u2/test_source_registries.py`
- `tests/track_u2/test_pension_registry.py`
- `tests/data/test_track_u2_income_wealth.py`
- `data/external/track_u2/u1_identity.json`
- `data/external/track_u2/support.json`
- `data/external/track_u2/weights.json`
- `tests/data/track_u2/psid_sources/weights17_manifest.json`

Read in part:

- `docs/design/boomers2004_1946_55_comparison.md` (draft 3): lines 1–419, 637–657 and 1037–1606, plus heading and `U7` search hits. Lines 420–636 and 658–1036 were not read.
- `docs/design/u2_m1_source_adjudication.md`: lines 1–80, 1788–1838, every TO VERIFY row and the rows the edits touched.
- `data/external/track_u2/roles.json`: every entry, printed through a JSON dump (long output partly truncated on screen).
- `data/external/track_u2/pension.json`: the source list and all route entries for 2013, 2015 and 2017, plus the `other_current_plan` and `inherited_route_amendment` entries for every wave.
- `data/external/track_u2/wealth.json`: metadata, every TO VERIFY entry and the 2013 WEALTH1, WEALTH2 and checking/saving entries.
- `data/external/track_u2/income.json`: the 2017 `wife_age`, `wife_sex`, `wife_retirement_annuities` and `ofum_asset` entries.
- All eight registries were also loaded by scripts that counted statuses, dependencies and specification citations.
- `docs/design/u2_m1_exposure.md`: search hits only (psidonline, download and browser lines).
- `scripts/capture_track_u2_income_wealth.py`: lines 140–200 and its function list.
- `scripts/capture_track_u2_ssi_sources.py`: lines 20–40.
- `src/populace_dynamics/data/family_income.py`: lines 40–80 and 895–910, plus accuracy-flag search hits. This file is protected; it was read and not edited.
- `tests/conftest.py`: lines 1–60.
- `pyproject.toml`: the pytest section.
- `tests/data/track_u2/psid_sources/cross_sec_weights_17.pdf`: full text extraction.
- Git metadata: `git show --stat` for the two milestone-1 commits; `git show HEAD:` for the draft-3 specification, the eight registries and `u1_identity.json`; `git grep` for references to the U2 specification.

Listed by directory name only: `WS/`, `WS/docs/design/`, `WS/tests/`, `WS/tests/data/track_u2/` and its subdirectories.

## PSID documentation (staged, local)

- `PSID/documentation/capture1/`:
  - `UserGuide2013.pdf` to `UserGuide2023.pdf` (six files): full text extraction and searches. Sections read: 2015 §§2.4–2.6 and 6.1; 2017 §§2.4–2.6, 6.1 and p. 62; 2019 p. 38.
  - `q2013.pdf`: p. 97.
  - `q2015.pdf`, `q2017.pdf`, `q2019.pdf`, `q2021.pdf`, `q2023.pdf`: full text extraction and searches. Pages read:
    - q2015 pp. 5, 89, 104 and 166;
    - q2017 pp. 5, 95 and 152;
    - q2019 pp. 102, 103, 125, 131 and 163;
    - q2021 pp. 204, 205, 243, 251, 292 and 304;
    - q2023 pp. 202, 203, 241, 249, 290 and 302.
  - `fam2015_QxQs.pdf`: full text search; pp. 3 and 144 read. `qxq2015_QxQs.pdf`: full text search; it has the same bytes as `fam2015_QxQs.pdf`.
  - `cross_sec_weights_17.pdf`, `_19.pdf` and `_21.pdf`, `long_weight_17.pdf` and `long_weight_19.pdf`: full text extraction and searches. The 2019 reports' introductions and reference lists were read.
  - `IND2023ER_intro.pdf`: searched for 'weight'.
  - `psid_documents_inventory.json`, `browser_digests.txt`, `capture_completed_utc.txt` and `name_disambiguation.txt`: capture metadata.
  - Directory listing.
- `PSID/ind2023er/IND2023ER_codebook.pdf`: printed pp. 977–979.
- `PSID/family/2015/FAM2015ER_codebook.pdf`: full text extraction, searches, and the p. 692 entry for ER62057.
- `PSID/family/2019/fam2019er_codebook.pdf`: full text extraction and searches; pp. 591, 2015, 2058, 2059 and 2064 displayed.
- `PSID/family/2021/FAM2021ER_codebook.pdf` and `PSID/family/2023/FAM2023ER_codebook.pdf`: full text extraction and searches for 'uncooperative'.
- `PSID/family/2013/FAM2013ER.sps`, `PSID/family/2015/FAM2015ER.sps` and `PSID/family/2017/FAM2017ER.sps`: setup metadata. Scripts counted occurrences of 18 variable-ID tokens, and two 2013 label lines were displayed.
- `PSID/ind2023er/` and `PSID/documentation/`: directory listings. The listing shows the name of the raw file `IND2023ER.txt`, which was not opened.

Codebook text was displayed with published whole-file frequency columns stripped. The one exception was the first display of IND2023ER codebook p. 978, which showed the printed count and percent beside ER34304 code 1. That number was not used for any finding and is not reproduced anywhere. Published codebook value ranges, for example weight ranges and dollar domains, appear in registry text that milestone 1 wrote. No raw PSID record was read.

## Online sources

Live requests to `psidonline.isr.umich.edu`, all returning HTTP 403 with a Cloudflare security challenge:

- `https://psidonline.isr.umich.edu/`
- `https://psidonline.isr.umich.edu/data/Documentation/UserGuide2017.pdf`
- `https://psidonline.isr.umich.edu/data/weights/cross_sec_weights_17.pdf`
- `https://psidonline.isr.umich.edu/Guide/FAQ.aspx`, including one WebFetch attempt
- The eleven source URLs attempted at 2026-09-28T23:10:55Z–23:11:00Z, recorded per source in `tests/data/track_u2/psid_docs/manifest.json`

Internet Archive:

- Availability query: `https://archive.org/wayback/available?url=psidonline.isr.umich.edu/Guide/FAQ.aspx`.
- CDX index queries: `https://web.archive.org/cdx/search/cdx` for these psidonline paths:
  - `Guide/FAQ.aspx*`, `guide/faq.aspx*`, `Guide/*`, `*` (full site list), `help/*`, `data/weights/*`;
  - `data/Documentation/UserGuide2015.pdf` to `UserGuide2023.pdf`;
  - `data/weights/cross_sec_weights_17.pdf`, `cross_sec_weights_19.pdf`, `long_weight_19.pdf`;
  - `help/DataRelease-May2019.pdf`, `Guide/documents.aspx`, `Publications/Papers/*`, `Publications/Papers/tsp/*`, `Publications/Papers/`.
- Raw snapshots fetched (`id_`):
  - `https://web.archive.org/web/20190615165826id_/https://psidonline.isr.umich.edu/help/DataRelease-May2019.pdf`
  - `https://web.archive.org/web/20240616183623id_/https://psidonline.isr.umich.edu/Guide/FAQ.aspx?ID=1040.For` (read, not saved; superseded by the 2026 snapshot)
  - `https://web.archive.org/web/20260813185816id_/https://psidonline.isr.umich.edu/Guide/FAQ.aspx`
  - `https://web.archive.org/web/20260813185816id_/https://psidonline.isr.umich.edu/Guide/documents.aspx`
  - `https://web.archive.org/web/20250917085636id_/https://psidonline.isr.umich.edu/publications/Papers/`
  - `https://web.archive.org/web/20240927062358id_/https://psidonline.isr.umich.edu/data/Documentation/UserGuide2015.pdf`
  - `https://web.archive.org/web/20260302094310id_/https://psidonline.isr.umich.edu/data/Documentation/UserGuide2017.pdf`
  - `https://web.archive.org/web/20250715011806id_/https://psidonline.isr.umich.edu/data/Documentation/UserGuide2023.pdf`
  - `https://web.archive.org/web/20220617123829id_/https://psidonline.isr.umich.edu/data/weights/cross_sec_weights_19.pdf`
  - `https://web.archive.org/web/20220617123840id_/https://psidonline.isr.umich.edu/data/weights/long_weight_19.pdf`

Web searches (result titles and snippets only; no result page was opened):

- 'PSID 2017 immigrant refresher sample cross-sectional weights technical report psidonline' (restricted to psidonline.isr.umich.edu)
- 'PSID "uncooperative spouse" income family file reference person 2019'
- 'PSID same-sex couples 2015 2017 spouse partner OFUM "same-sex" Panel Study of Income Dynamics'

Every saved source, with URL, retrieval time, bytes and SHA-256, is in `tests/data/track_u2/psid_docs/manifest.json`.

## Files written

- Registries: `data/external/track_u2/{income,wealth,pension,roles,support,weights,u1_identity}.json`.
- Documents:
  - `docs/design/boomers2004_1946_55_comparison.md` (`u2-draft-4`)
  - `docs/design/u2_m1_source_adjudication.md`
  - `docs/design/u2_m1b_psid_research.md`
  - this file
- Tests:
  - `tests/track_u2/test_adjudication_applied.py`
  - `tests/track_u2/test_source_registries.py`
  - `tests/track_u2/test_pension_registry.py`
  - `tests/data/test_track_u2_income_wealth.py`
- Sources: `tests/data/track_u2/psid_docs/` (twelve source files, `manifest.json`, and a directory `.gitattributes` that marks the archived PDF and HTML bytes binary so Git never normalizes their line endings).

No engine file, `gates.yaml`, `runs/*.json`, `data/family.py`, `data/psid.py`, `estimates/career.py`, loader code or other milestone-2 module was edited.

## Procedural notes

- **Scratch outside the workspace.** Scratch work went to `SCRATCH` (`/tmp/u2m1b`), outside the workspace:
  - text extractions of the PSID documentation listed above;
  - the Internet Archive downloads before they were copied into `psid_docs`;
  - two failed-download stubs (`test.pdf` and `t2.bin`, both the Cloudflare challenge page);
  - five edit scripts: `apply_part_a.py`, `apply_part_a2.py`, `update_master.py`, `apply_part_c.py` and `pin_spec.py`.

  The edit scripts assert the milestone-1 pre-state before editing. Their effect is fully recorded in the committed diffs: every changed registry entry carries an `adjudication` or `citation_correction` object. No caller-worktree file was written.
- **Tool calls moved to background.** The machine's load average was above 200 throughout, so several tool calls ran past their time limit and were moved to the background by the harness; each result was read when it completed. The first registry test run took 40 minutes.
- **Virtual environment.** The workspace `.venv` was created with `uv venv -p cpython-3.14t .venv` and `uv pip install -e '.[dev,model]' hypothesis pyyaml`.

## Revision after the independent review (2026-09-29)

Complete list of what the revision builder opened (Claude Code, Opus 5.5, headless Subfleet job `20260928-230312-u2-m1b-fix`), working blind. It did not open the Boomers 2004 report, any comparator lane or seal, the cleared or uncleared U2 availability statement, any public result memo, `EV/parity-phase2-plan-20260927.md`, its review, `EV/dynasim-scorecard.md`, the adjudication `EV/phase2-20260927/out/u2-adjudicate.md`, or anything else `EV/RESTRICTED-FILES.md` restricts. It states and guesses no 1946–55 value or direction. No raw PSID data file was opened, no web request was made, and no poverty, benefit or estimator run was made.

Roots as above, except `WS` = the revision workspace `/Users/maxghenis/.subfleet/worktrees/20260928-230312-u2-m1b-fix` (a detached checkout of branch `dynamics-u2-impl-20260928` at `883ea488`) and `SCRATCH2` = `/tmp/u2m1bfix`.

### Instructions and review

- `EV/RESTRICTED-FILES.md`: read in full, first.
- `EV/phase2-20260927/prompts/common.md`: read in full.
- `EV/phase2-20260927/out/u2-m1b-review.md`: read in full.
- `/Users/maxghenis/.claude/CLAUDE.md` and `WS/CLAUDE.md`: injected at session start.

### Repository files (workspace)

Read in full:

- `docs/design/u2_m1b_psid_research.md`
- `docs/design/u2_m1b_exposure.md`
- `tests/track_u2/test_adjudication_applied.py`
- `tests/data/track_u2/psid_docs/manifest.json`
- `tests/data/track_u2/psid_sources/weights23_manifest.json`
- `tests/conftest.py`
- `tests/tier_counts.json`

Read in part:

- `docs/design/boomers2004_1946_55_comparison.md`: lines 1–240 and 1352 to the end, plus lines 134 and 152–160 again. Draft 3 (`git show f7412e00:docs/design/boomers2004_1946_55_comparison.md`, saved to `SCRATCH2/draft3.md`): lines 134, 152–160 and 1391, and a full diff against draft 4.
- `src/populace_dynamics/data/u2_source_registry.py`: lines 1–200 and 355–439.
- `src/populace_dynamics/data/psid.py`: lines 75–125.
- `src/populace_dynamics/__init__.py` and `src/populace_dynamics/data/__init__.py`: first 30 lines.
- `pyproject.toml`: lines 1–80 and 115–140.
- `tests/test_tier_policy.py`: lines 1–80.
- `.github/workflows/tests.yml`: lines 1–60.
- `tests/track_u2/test_source_registries.py`: lines 264–330 and 360–401, plus search hits.
- `data/external/track_u2/weights.json`: the `2017.cross_section_weight` entry.
- `data/external/track_u2/roles.json`: lines 535–565 and 820–888 (the 2015 and 2017 code-90 and code-92 entries).
- `data/external/track_u2/u1_identity.json`: its keys, the `u2_specification` record, and its 50 U1 hashes through a script.
- All eight registries: top-level keys and `sources` lists, through scripts.
- `docs/design/u2_m1_source_adjudication.md`: lines 1–30, 36, 50–60, 1777 and 1815–1825.
- `docs/design/u2_m1_captured_sources.md`: lines 1–20 and line 114. `docs/design/u2_m1_exposure.md` lines 269 and 439 and `docs/design/u2_m1_report.md` line 102: search hits only.
- A search for 'served at' also printed eight unrelated lines of `docs/design/boomers2004_uniform_cut_comparison.md` (lines 221, 222, 800, 881, 895, 991 and 992) and `docs/design/minimum_benefits_comparison.md` (line 1104). Neither concerns the 1946–55 cohort.
- Git metadata: logs, `git diff origin/master...HEAD --stat` and `--name-status`, and the diffs of `scripts/first_estimates_birth_evidence.py` and `tests/estimates/test_birth_evidence_artifact.py`.

Archived and pinned sources in the workspace:

- `tests/data/track_u2/psid_sources/cross_sec_weights_23.pdf`: full text extraction. PDF pp. 1–3 and 6–10 read; p. 13 read as text and as a rendered page image (110 dpi, `SCRATCH2/csw23_p13-13.png`); p. 14 read. Search hits displayed one Table A1 row.
- `tests/data/track_u2/psid_docs/cross_sec_weights_19.pdf`: full text extraction. Pages 1–13: paragraphs mentioning 2017 or the construction steps. PDF p. 14, Table A1 on p. 16, and Tables A2a to A7 on pp. 17–22 displayed.
- `tests/data/track_u2/psid_docs/FAQ_20260813.html`: lines 788–875 displayed as text; `grep -n` searches; byte counts of CR and LF.
- `tests/data/track_u2/psid_docs/UserGuide2017.pdf` p. 62, `DataRelease-May2019.pdf` p. 1, `long_weight_19.pdf` pp. 1–2 and `tests/data/track_u2/psid_sources/cross_sec_weights_17.pdf` p. 1 read. `documents_20260813.html`: searched for weight-report links.
- Every PDF in `tests/data/track_u2/psid_docs/` and `psid_sources/`: text layers searched by scripts that printed only the pages holding each research quote.
- Every file in the manifest: hashed.

### PSID documentation (staged, local)

- `PSID/documentation/`: directory listing. Its only subdirectory is `capture1`.
- `PSID/documentation/capture1/`: all 494 PDFs text-extracted to `SCRATCH2/txt/` and searched for the 2015 RTH Lookup List. For non-codebook files, the matching lines were displayed. For codebooks, only file and page were displayed, except one variable-header line on `IND2023ER_codebook.pdf` p. 523 (ER33219, labelled 'RELATIONSHIP TO RESPONDENT 95').
  - Pages read: q2015 pp. 5, 131 and 217 (context around the matches), q2017 p. 5, fam2015 QxQs p. 3, and the first 1,500 characters and four matching lines (pp. 27, 28 and 137) of `2014_FieldManual.pdf`, a Child Development Supplement manual.
  - Matching lines displayed from q1999, q2001, q2003, q2011, q2013, q2019, q2021, q2023, q2025, `Coverscreen.pdf`, `CDS2019_Coverscreen-Qnaire.pdf`, `cds-19_child.pdf`, `cds-19_pcg.pdf`, `dust13_Questionnaire.pdf`, `TA11_UserGuide.pdf` and `fam1978_78FAM.PDF`.
  - `psid_documents_index.html`, `psid_documents_inventory.json`, `browser_digests.txt`, `capture_completed_utc.txt` and `name_disambiguation.txt`: searched or read in part. `__test.bin` and `__test2.bin`: file type and size only.
- `PSID/ind2023er/IND2023ER_codebook.pdf`, `PSID/family/2015/FAM2015ER_codebook.pdf` and `PSID/documentation/capture1/q2011.pdf` to `q2023.pdf`: text layers searched by scripts that printed only page numbers for each quote. No codebook page text was displayed.
- `PSID/family/2019/fam2019er_codebook.pdf`, `PSID/family/2021/FAM2021ER_codebook.pdf` and `PSID/family/2023/FAM2023ER_codebook.pdf`: hashed only.

### Incidental exposure

Published whole-sample PSID documentation statistics were displayed:

- the 2023 cross-sectional report's Table A2 and one row of its Table A1;
- the 2019 cross-sectional report's Tables A1 to A7: sample sizes, weight distributions, and weighted age, sex, race and region shares for PSID, the ACS and the CPS.

None concerns the 1946–55 cohort or the Boomers report, none is used for a finding, and none is reproduced in any document. A process listing, run to check a package install, showed other jobs' command lines; nothing from it was used.

### Files written

- `docs/design/boomers2004_1946_55_comparison.md` (§§16a, 17 and 19 and the version line; nothing before §16a except line 3)
- `docs/design/u2_m1b_psid_research.md`
- `docs/design/u2_m1_source_adjudication.md` (the 2017 weight rows and one FAQ citation)
- `data/external/track_u2/weights.json`, `roles.json` and `u1_identity.json` (the U2 specification pin only; the 50 U1 hashes are unchanged)
- `tests/data/track_u2/psid_docs/manifest.json`
- `tests/track_u2/test_adjudication_applied.py` and the new `tests/track_u2/test_psid_research_sources.py`
- this section

No U1 file, engine file, `gates.yaml`, `runs/*.json` or milestone-2 module was edited. `SCRATCH2` holds the draft-3 copy, the text extractions, the search scripts and their output, and the page image. The workspace `.venv` (Python 3.13; `uv pip install -e . pytest hypothesis`) is ignored by Git.

### Verification pass and follow-up reading (2026-09-29)

An in-session verifier (Claude Code subagent, Opus 5.5, told to obey `EV/RESTRICTED-FILES.md` and write nothing) reviewed commits `4f3e911..f9845ff`. By its own report it opened:

- `EV/RESTRICTED-FILES.md` and `EV/phase2-20260927/out/u2-m1b-review.md`;
- in `WS`: the specification (current and draft 3 through `git show f7412e00`, copied to `/tmp/u2verify/draft3.md`), the research record, the diffs of the master record, this file, the manifest and the `roles`, `weights` and `u1_identity` registries, the 2015 and 2017 code-90 and code-92 role entries, `weights23_manifest.json`, both touched test files, and `.github/workflows/tests.yml` (search only);
- PDF text of `cross_sec_weights_23.pdf` pp. 1–10, 13 (numbers masked) and 14, `psid_docs/cross_sec_weights_19.pdf` pp. 1–4 and 6–18, `UserGuide2017.pdf` p. 62, `DataRelease-May2019.pdf` p. 1, the title page of `cross_sec_weights_17.pdf`, and the cited lines of `FAQ_20260813.html`, plus a link search of `documents_20260813.html`;
- `PSID/documentation/` (listing only) and the text layers of all 494 PDFs in `PSID/documentation/capture1/`, extracted to `/tmp/u2verify/txt` and searched, with closer reads of `cross_sec_weights_21.pdf` (parts), `long_weight_17.pdf` and `long_weight_19.pdf` (search) and the q2019 and ta25 search hits.

It opened no raw data file. It reported seeing published whole-sample statistics (`cross_sec_weights_19` Table A1; one Table A1 row and a few PSID-to-ACS ratios from `cross_sec_weights_21`), none about the 1946–55 cohort, and reproduced none. It ran the two touched test files and mutation copies under `/tmp/u2verify/repo`.

The builder's follow-up reads:

- `/tmp/u2m1bfix/draft3.md`: lines 1380–1385.
- `tests/data/track_u2/psid_docs/cross_sec_weights_19.pdf`: pp. 6, 7, 12 and 13 again.
- `PSID/documentation/capture1/cross_sec_weights_21.pdf`: full text extraction. Pages 1–7, 10, 11, 13 and 14 were displayed through a paragraph search, including its Tables A1 and A2 (published whole-sample sample sizes and weight distributions). Also hashed.
- `PSID/documentation/capture1/q2009.pdf`: the context of its lookup hits on pp. 51, 109, 167, 177, 180, 183, 185 and 188. Also hashed.
- Page-level searches, with whitespace collapsed across line breaks, of all 494 extracted documentation PDFs for `RTH Lookup` and for printed three-digit relationship values. Contexts were displayed for non-codebook files only.
- Lookup-list hits from the same extraction, displayed for non-codebook files. For codebooks, only the matching phrase was shown.
- Quote locations, page numbers only, in `PSID/family/2013/FAM2013ER_codebook.pdf` (p. 1852), the 2015, 2017, 2019, 2021 and 2023 family codebooks (pp. 6, 7 and 689–698), q2015 p. 164, q2017 p. 152, q2019 p. 163, q2021 p. 304, q2023 p. 302, and `IND2023ER_codebook.pdf` pp. 916 and 1224.
- `src/populace_dynamics/data/family_income.py` line 45 and search hits for 'WIFE RETIREMENT' (lines 272, 394, 516, 638 and 761). `data/external/track_u2/income.json` search hits for 'RETIREMENT/ANNUIT'. `PSID/family/2013/FAM2013ER.sps` line 6956. The `wealth.2013.wealth2_acc` entry of `data/external/track_u2/wealth.json`.
- The ranges of the two touched test files needed for editing, and the `sources` lists of all eight registries through scripts.

The verification pass exposed nothing more about the 1946–55 cohort or the Boomers report.

## Resumed revision: second-pass completion and third verification (2026-09-29)

The first revision job stopped at a session limit while applying the second verification pass's fixes, leaving them uncommitted on `dd7a057`. A resumed job (Claude Code, Opus 5.5, headless Subfleet job `20260928-230312-u2-m1b-fix`, same workspace `WS2` = `/Users/maxghenis/.subfleet/worktrees/20260928-230312-u2-m1b-fix`) completed them in `ce14db6`, ran a third verification with three in-session subagents and fixed its findings in `c2c386c` and the commit that adds this section. It worked blind under `EV/RESTRICTED-FILES.md`, opened nothing that file restricts, opened no raw PSID data file, and states and guesses no 1946–55 value or direction. `SCRATCH3` = `/tmp/u2m1bfix3`.

### Instructions and job records

- `EV/RESTRICTED-FILES.md` and `EV/phase2-20260927/prompts/common.md`: read in full, first.
- `EV/phase2-20260927/out/u2-m1b-review.md`: read in full.
- The first job's session log (`~/.claude/projects/-Users-maxghenis--subfleet-worktrees-20260928-230312-u2-m1b-fix/bbade00e-d149-442d-b1cd-021d5f659501.jsonl`): its last 60 actions, by script. Its second verifier's log (`…/subagents/agent-af7bd50ecb8573f7f.jsonl`): the final report only, which lists the files that verifier opened (dd7a057's section above does not; they were the specification and draft 3, the research record, the master record, the weights, roles, pension and identity registries, the manifest, both test files, `src/populace_dynamics/data/u2_source_registry.py` and `family_income.py` line 45, and PSID documentation text only, including `long_weight_17` and `long_weight_21` p. 4, the FAM2015–FAM2023 codebooks' pp. 6–7 and the DUST 2009 and 2013 household codebooks). That verifier reported displaying one whole-sample row of Table A1 of `cross_sec_weights_21` and whole-sample DUST relationship frequencies.
- `/Users/maxghenis/.claude/CLAUDE.md` and `WS2/CLAUDE.md`: injected at session start.

### Repository files (workspace)

- Read in full: `docs/design/u2_m1b_psid_research.md`, `tests/track_u2/test_adjudication_applied.py`, `tests/track_u2/test_psid_research_sources.py`.
- Read in part: `docs/design/boomers2004_1946_55_comparison.md` (lines 60–170, 650–660, 1352–1600 and 1687–1770, plus searches); draft 3 through `git show f7412e00:…` (saved to `SCRATCH3/draft3.md`; lines 100–105, 650–660, 1378–1392) and line 1563 of `9a93560` and `883ea48`; `docs/design/u2_m1_source_adjudication.md` (lines 20–40 and the registry rows, by script); this file (lines 1–30 and 150–249); `data/external/track_u2/*.json` (the `sources` lists, the `2017.cross_section_weight`, `2015.relationship.20`, `2015.relationship.90`, `2017.relationship.90`, `2017.relationship.92` and `2015.route.respondent_slots` entries, by script); `tests/data/track_u2/psid_docs/manifest.json` and `tests/data/track_u2/psid_sources/weights{17,23}_manifest.json` (parsed); `src/populace_dynamics/data/u2_source_registry.py` (lines 330–440); `tests/track_u2/test_source_registries.py` (lines 356–420 and searches); `.github/workflows/tests.yml` (lines 1–80).
- Git metadata: logs, the blob of every spec revision (hashed), `git diff origin/master...HEAD --name-only` and `--stat`, `git diff 883ea48 HEAD --stat`.

### PSID documentation (text layers only)

- `PSID/documentation/capture1/`: all 494 PDFs extracted to `SCRATCH3/txt/` and searched for `RTH Lookup`, lookup lists and printed three-digit relationship values; directory listing. Contexts displayed, with numbers masked where a page holds tables: q2015 pp. 5, 150, 161–163, 190, 201 and every CYAQRTH condition; q2017 pp. 5, 89, 184, 201, 255 and 265 and every page naming 201; q2013 CYAQRTH conditions; q1999 p. 147, q2001 p. 143, q2003 pp. 1 and 102; `cross_sec_weights_11` p. 13, `_13` p. 12, `_15` p. 14 and `_17` pp. 13–14 (calibration-table contexts); `fam1977_77FAM` p. 98, `psid77w10` p. 188, `psid87w20v1` p. 109, `fam2011_QxQs` and `qxq2011_QxQs` p. 101; `dust09_hh_codebook` pp. 1 and 3–6 and `dust13_hh_codebook` pp. 1 and 4–7 (codes and labels only); `dust09_UserGuide` p. 1; `dust13_UserGuide` pp. 1–3; `long_weight_17` pp. 1 and 9; `long_weight_21` pp. 1 and 4; `cross_sec_weights_21` p. 11; the capture's copy of `IND2023ER_codebook.pdf` p. 523. `psid_documents_inventory.json` and `browser_digests.txt`: searched.
- `PSID/ind2023er/IND2023ER_codebook.pdf` p. 523 (ER33219's note and code labels; counts masked).
- `PSID/family/2015/FAM2015ER_codebook.pdf` pp. 1966–1980 (variable scan; pp. 1968–1969 displayed with numbers masked, and ER65317's definition unmasked), `PSID/family/2017/FAM2017ER_codebook.pdf` pp. 2 and 2019–2029 (p. 2021 masked; the Release 2 lines of pp. 2 and 2090), `PSID/family/2017/Fam2017er_readme.pdf` p. 1 (release notes), `PSID/family/2019/fam2019er_codebook.pdf` pp. 2005–2015 (p. 2006 masked), and the full text of the 2019, 2021 and 2023 family codebooks, searched for `uncooperative` (page numbers only). `ls` of `PSID/family/2017` showed data file names; none was opened.
- Archived sources: `long_weight_19` pp. 8 and 13–16 (masked) and a full-text search; `cross_sec_weights_19` pp. 9, 10 and 14; `cross_sec_weights_17` pp. 1 and 5 and keyword page lists; `cross_sec_weights_23` pp. 2 and 10; `UserGuide2019` p. 38; `documents_20260813.html` (search for DUST).
- Through the tests and probe scripts, which print only booleans or page numbers: every page cited in the research record, §16a and the registry quotes and anchors, and their neighbouring pages.
- GitHub's public `actions/runner-images` Ubuntu 24.04 readme, fetched with `gh api` and searched for Poppler.

### Third verification (three in-session Opus 5.5 subagents)

Each was told to obey `EV/RESTRICTED-FILES.md`, write nothing in the workspace and list what it opened. By their reports:

- **Logic:** `EV/RESTRICTED-FILES.md`; the review; the specification (lines 60–170, 96, 104, 656, 1375–1600, 1688–1767) and draft 3 (lines 1, 12, 104, 134, 150–162, 188, 656, 660, 751, 1083–1084, 1358, 1369, 1376–1394, 1475, 1528, 1566, 1581, 1606, some shown by a search) and `883ea48`'s lines 84, 1423, 1425, 1437, 1439, 1443, 1516, 1526 and 1563; the research record; the roles and weights registries (entries named above) and all registries by script; the master record (lines 1–101); both test files in part; both weights manifests; `cross_sec_weights_17` p. 9 (masked); q2015 p. 190; a search of this file; incidental search lines of the saved FAQ (lines 420 and 508) and `tests/test_gate1_qrf_candidate6.py` line 192.
- **Sources:** `EV/RESTRICTED-FILES.md`; the research record; the specification (§16a); the weights and roles entries; the saved FAQ, documents page and technical-paper list; `DataRelease-May2019`, the five user guides, `fam2015_QxQs`, `cross_sec_weights_23` and the weights manifests; `FAM2015ER` pp. 6 and 1967–1980, `FAM2017ER` pp. 2020–2029, its readme and introduction (p. 1), the 2019, 2021 and 2023 family codebooks (search; 2019 pp. 2005–2015 viewed), `IND2023ER_codebook` pp. 523, 916, 978 and 1224 with its readme and introduction; the text of all 494 capture PDFs (searched), with pages viewed in q1999, q2001, q2003, q2009 and q2015–q2023, the weight reports of 2009–2021, the DUST household codebooks and `dust13_UserGuide` p. 1. It reported displaying small whole-file percentages for the 2015 OFUM accuracy codes, DUST 2009 household counts, whole-file counts on `IND2023ER_codebook` pp. 523 and 916, two ACS population totals from Table A2a of `cross_sec_weights_19`, and `long_weight_19` p. 20's remark that the 2017 immigrant sample's average weights exceed the Core sample's.
- **Tests and provenance:** `EV/RESTRICTED-FILES.md`; the review; the three test files; the manifest; the research record; the specification (lines 68–94 and 1375–1599); the registries (parsed); `.github/workflows/tests.yml`; draft 3; the text layers of every cited PDF (counts and page numbers only); the 50 U1-pinned files (hashed). It ran mutation copies under `/tmp/u2verify3-tests/`, reading draft 3 from the workspace's Git objects without writing to them.

### Incidental exposure

Whole-sample PSID documentation figures were displayed: the numeric cells that matched the value search in the 2011–2017 cross-sectional weight reports' calibration tables, the DUST 2013 file sizes in its user guide's contents, and, by the verifiers, the items listed above. None concerns the 1946–55 cohort or the Boomers report, none is used for a finding, and none is reproduced in any document.

### Files written

- `docs/design/boomers2004_1946_55_comparison.md` (§§16a, 17 and 19 only), `docs/design/u2_m1b_psid_research.md`, `docs/design/u2_m1_source_adjudication.md` (two summary rows and two registry rows), this section.
- `data/external/track_u2/weights.json` (`2017.cross_section_weight`), `roles.json` (`2015.relationship.20`) and `u1_identity.json` (the specification pin only).
- `tests/data/track_u2/psid_docs/manifest.json`, `tests/track_u2/test_adjudication_applied.py`, `tests/track_u2/test_psid_research_sources.py`.
- Scratch: `SCRATCH3`. Early in the job three helper scripts (`page.sh`, `varscan.py`, `pagesof.py`) were written into the first job's scratch `/tmp/u2m1bfix`, and its `lw19.txt` was rewritten with the same extraction.

No U1 file, engine file, `gates.yaml`, `runs/*.json` or milestone-2 module was edited.

### Checks the review could not run

Run at the final state:

- SHA-256 and byte size: all 12 archived sources match the manifest, and all 24 pinned documents match their SHA-256 and byte size. Every `identical: true` local-capture claim holds.
- U1: the branch's merge base with `origin/master` is `d978d966`, the pinned `base_commit`. None of the 50 U1-pinned files is among the 164 files that `git diff origin/master...HEAD` lists, all 50 hash to their pins, and `origin/master` has not changed any of them since. No engine, `gates.yaml` or `runs/` file changed.

## Rulings recorded (2026-09-30, d637)

A Claude Code session (Opus 5.5) recorded Max's ruling d637 on §16a as the specification's §16b. It edited only record text; no rule in §§3–16a changed. It is not a U2 builder, referee or forecaster, and it computed nothing.

### Read

- `EV/RESTRICTED-FILES.md`, the list itself, in full, to know what not to open.
- `EV/phase2-20260927/out/u2-m1b-verify-max-brief.md`, the verifier's brief (SHA-256 `958ad848…`), and the d637 entry in the chief-of-staff decision log.
- In the repository: the specification (its headings, header, §§16, 16a, 17, 19 and 20), the research record (header and question labels), the master record's pointer to §16a, `data/external/track_u2/u1_identity.json`, the assertions that `tests/track_u2/test_adjudication_applied.py`, `test_psid_research_sources.py` and `test_u2_isolation.py` make on the specification, `src/populace_dynamics/uniform_cut_track_u2/identity.py`, and the description of PR #486.
- The sent PSID message in Max's mailbox (headers, labels and text), to record that it was sent.
- For the session's other two rulings (d649 on the PIA-source validation, d660 on the roadmap), none concerning U2: the PIA-source registration package (`EV/pia-registration-package-rev11-20260929-r2.md`: header, §§0–2, §16 and parts of §18), its appointments log, issue #113, issue #74, and issue #42 comments as described under Incidental exposure.

### Not opened

No file the restricted list names was opened for reading: no page of the Boomers 2004 report, no U2 or exercise-2 comparator, seal, values scan or result, and no PSID data file. One recursive file-name search (`grep -rl` for PIA-source terms, 2026-09-30 about 22:23 UTC) ran over the whole evidence folder, restricted folders and files included, so it read their bytes to search them. Its output was filtered only for the scratchpad archives and the PIA package files and cut to the first 40 names; none of the names it printed is on the restricted list. An earlier attempt at the same search failed before running.

### Incidental exposure

- **Issue #42, a listing.** A listing of #42 comments posted since 2026-09-09 (2026-09-30, about 22:22 UTC) excluded result comments 5841142710, 5853001916 and 5856068881 but not 5804799227, the exercise-1 result comment (posted 2026-09-23). It printed that comment's id, date and the first 70 characters of its first line, which name it as Registration 13's result and contain no value. The restricted list describes the exercise-1 result as public. It is not a U2 source.
- **Issue #42, a scan.** An earlier scan (about 22:22 UTC) tested every #42 comment body for PIA-related terms and printed only each match's id, date, author, body length and a match flag. One match was the exercise-4 result comment 5856068881; none of its text was printed. The session then printed only the matching lines of seven non-restricted registration comments (13 to 18 and the 2026-09-30 correction): one line of Registration 17's diagnostics list, and nothing from the others. It also printed the matching passage of one July comment (4967433717, a gate_m6 stop), about a claiming reference.
- **The restricted list's changelog.** Its entry of 2026-09-29 02:40 paraphrases the Boomers report's PDF metadata summary (qualitative; no table value, nothing about the 1946–55 column or the 13% cut). The session read it there, as any reader of the list does.
- **Public exercise-1, -3 and -4 figures.** These appeared in passing in:
  - `EV/parity-phase2-plan-20260927.md` (SHA-256 `95b0e5af6a31b335672f41e2b8db7d396b7c5fbc4df836ff243dc19e285797c3`; lines 54, 62, 66 and 70);
  - `EV/dynasim-scorecard.md` (SHA-256 `1c2a6fffb68ce7c0a6c9d658498205ed346e59c213a2e5590515919b7274cba7`; lines matching "PIA");
  - `EV/scorecard/scorecard-data.json` (two row labels, no figure);
  - the microcosm.institute `dynamics/scorecard/copy.json` (the passages around "PIA");
  - the PIA package's §2.2 (exercise-4 artifact counts).
  No exercise-2 figure (Boomers 2004 Tables 19 and 21) appeared in any of them, and none concerns U2.

### Files written

- `docs/design/boomers2004_1946_55_comparison.md` (lines 3 and 4, §16b, and §§17, 19 and 20), `docs/design/u2_m1b_psid_research.md` (the header sentence and the three question labels), `docs/design/u2_m1_source_adjudication.md` (the pointer to §16a), `data/external/track_u2/u1_identity.json` (the specification pin and its note), and this section.

No registry entry, §15 line, test, U1 file, engine file, `gates.yaml` or `runs/*.json` was edited.

## Ruling recorded and applied (2026-10-10, d1090)

A Claude Code session (Opus 5.5) recorded Max's ruling d1090 on blockers B1 and B2 as the specification's §16c and applied it to the U2 source registries and the cohort builder. It is not a U2 forecaster or referee, and it computed nothing from real data.

### Read

- `EV/RESTRICTED-FILES.md` (SHA-256 `2e1b5c2a…`), in full and first, to know what not to open.
- The chief-of-staff decision log's entries for d637, d745 and d1090, and a listing of decisions filtered for those ids.
- `EV/rulings-records-20260930/README.md` (`29f9b525…`) and `registry-followup-brief.md` (`aefefe0c…`), the d637 registry brief, and that folder's file listing.
- In the repository: the specification (its header, the §3 lines on family units and sequences, and §§15–20), the research record in full, the master record (summary tables, blocker rows and the rows of the entries this work changes), this file's 2026-09-30 section, the eight registries, `u1_identity.json`, `src/populace_dynamics/data/u2_source_registry.py`, the U2 package's `sources.py`, `cohort.py`, `loader.py` and `invented.py`, `scripts/track_u2_dry_run.py`, and the tests under `tests/track_u2/`.
- `git worktree list` and the titles of the repository's open pull requests.

### Not opened

No file on the restricted list was opened: no page of the Boomers 2004 report, no comparator, seal, values scan or result, and no PSID data file. PSID's reply and its screenshots (`EV/phase2-20260927/psid-help-reply-20261007/`) were not opened; the research record's account of them was used. No issue #42 comment was listed or read, and no Subfleet job folder other than this session's own review runs was opened.

### Tests

The U2 tests ran with the PSID root staged. They read staged PSID documentation (setup files, codebooks and questionnaires, through text extraction) and invented records; the loader tests' audit hook refuses any open under the PSID data roots. No raw PSID record was read and no statistic was computed on real data.

### Incidental exposure

- The decision listing printed one-line summaries of unrelated decisions (travel, other repositories); none concerns a comparator or U2's outcome.
- The d1090 decision record paraphrases PSID's answer. Besides the whole-file count of two that the research record already discloses, it gives one record-level detail about one of the two people, which the research record withholds. It is not reproduced in the specification, the registries or here.
