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
