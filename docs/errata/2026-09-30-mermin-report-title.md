# Erratum: the title of Mermin (2005)

Date: 2026-09-30. This is a follow-up to the anchor-provenance erratum, [`2026-09-29-anchor-provenance.md`](2026-09-29-anchor-provenance.md) ([PolicyEngine/microcosm-dynamics#488](https://github.com/PolicyEngine/microcosm-dynamics/issues/488), [PolicyEngine/microcosm-dynamics#489](https://github.com/PolicyEngine/microcosm-dynamics/pull/489)). The benchmark-registry part of that follow-up is [PolicyEngine/microcosm-dynamics#497](https://github.com/PolicyEngine/microcosm-dynamics/issues/497).

Three replication scripts and the benchmark source-capture request gave the wrong title for Urban Institute report 411260. They called it "The Effect of Benefit Reductions on the Distribution of Social Security Benefits". The report's title is "Distributional Effects of Reforming Social Security through Benefit Reductions".

This erratum corrects the scripts and the request. It does not edit or regenerate the committed evidence artifacts under `runs/`, so three of them keep the old title. Where a committed artifact and this erratum disagree about the title, this erratum governs.

In the citations only the title changes. The author, year, report number, model run (DYNASIM3, Runid 432), assumptions and page citations stay as they were. The capture request also gets the report's landing URL and a note on Table 1's CBO row (below). No anchor value, result, forecast grade or pass/fail status changes.

## The report's title

Every source checked on 2026-09-30 gives the same title.

**The title page.** `411260-benefit-reductions.txt` lines 1–9, the start of the `pdftotext -layout` output for PDF page 1:

```text
   Distributional Effects of Reforming Social Security through Benefit Reductions

                                        Gordon B. T. Mermin

                                          The Urban Institute



                                            December 2005
```

**The PDF's own metadata.** The document-information `Title` field of the archived PDF, as `pdfinfo 411260-benefit-reductions.pdf` prints it, reads "Distributional Effects of Reforming Social Security through Benefit Reductions".

**The publisher's landing page.** Urban's page for the report is <https://www.urban.org/research/publication/distributional-effects-reforming-social-security-through-benefit-reductions>. It gives the same title in its `<title>` element, its `citation_title` meta tag and its schema.org `headline`, among other places. It also dates the report to 12 December 2005 (`citation_publication_date` 2005/12/12), and its `citation_pdf_url` points at the PDF below.

**The publisher's PDF.** The file on Urban's server is named `411260-Distributional-Effects-of-Reforming-Social-Security-through-Benefit-Reductions.PDF`. Fetched from <https://www.urban.org/sites/default/files/publication/51966/411260-Distributional-Effects-of-Reforming-Social-Security-through-Benefit-Reductions.PDF>, it has the same SHA-256 as the archived copy (table below), so the archived copy is byte-identical to the publisher's current file.

None of these sources uses the old title. An exact-phrase web search for it on 2026-09-30 found no publication of that name.

**The registry's capture status is older than this check.** The registry's capture review (`/external_capture_review/missing_after_refresh/mermin_2005_publisher_capture/status` in `benchmarks/registry.json`) says: "Publisher-controlled bytes were not retrieved; the modern Urban Institute URLs returned 404 and the web archive was unavailable." On that basis it keeps the 20 Mermin rows `reported_not_verified`.

On 2026-09-30 the exact PDF URL served the report, byte-identical to the archived copy, while the old landing URL returned 404. This erratum does not change the capture status or the rows' verification class. Accepting a publisher capture goes through the capture protocol in `benchmarks/SOURCES-NEEDED.md` and changes the registry, so it belongs with a later capture refresh and evaluation append ([PolicyEngine/microcosm-dynamics#497](https://github.com/PolicyEngine/microcosm-dynamics/issues/497) notes it).

### Source files

The archived copies are in `~/PolicyEngine/dynasim-refs`, outside this repository:

| File | SHA-256 |
|---|---|
| `411260-benefit-reductions.txt` | `4b9f3becd99718948f97265222ecb2f2065a1fe6a18a5a0a6be62d5df994504c` |
| `411260-benefit-reductions.pdf` | `88934782c267fb0d7f08106ef930a19866c41c89504d04ad7a6d77d454d034ae` |

`tests/test_mermin_report_title.py` checks the quote and both hashes against these files when they are present.

## Where the old title came from

The old title entered the repository on 2026-07-07 with the Phase-A replication (`scripts/replication_ppi_mermin.py`, #77). It then spread:

- Two later scripts copied it: `scripts/replication_mermin_rows.py` (#88) and `scripts/replication_ppi_shared.py` (#114).
- The paper's bibliography took it in #91.
- The validation-matrix lane wrote it into its source-capture request (#352), which #353 moved to `benchmarks/SOURCES-NEEDED.md`. That request's landing-page URL, `https://www.urban.org/research/publication/effect-benefit-reductions-distribution-social-security-benefits`, follows the old title's words, and it returned HTTP 404 on 2026-09-30.

The bibliography audit in #442 (2026-09-19) corrected `docs/references.bib`, but not the scripts or the capture request. The benchmark registry already carried the correct title in its Mermin locators.

## What this change corrects

- `scripts/replication_ppi_mermin.py`, `scripts/replication_mermin_rows.py` and `scripts/replication_ppi_shared.py`: the module docstrings (the first two) and the `paper` field of `anchor_provenance()` (all three) now give the report's title. No other part of those strings changed.
- `benchmarks/SOURCES-NEEDED.md`, item 8:
  - the title is corrected;
  - the landing URL now points at the report's page (the URL in `docs/references.bib`);
  - a sentence notes that Table 1's 75-year deficit/surplus row is Congressional Budget Office (2005) estimates, per the anchor-provenance erratum.
- `docs/references.bib` was already correct and is unchanged. Its `mermin2005benefitreductions` entry has the report's title, report number and landing page.

A rerun of the edited scripts would emit the new title. No computation, numeric constant, output key or reproduction pin changed; the scripts' seed-0 reproduction tests compare numbers only.

## Committed artifacts that keep the old title

These bytes are not edited. Read them through this erratum.

| Artifact | JSON pointer |
|---|---|
| `runs/replication_ppi_mermin_v1.json` | `/anchor_provenance/paper` |
| `runs/replication_mermin_rows_v1.json` | `/anchor_provenance/paper` |
| `runs/replication_ppi_shared_v1.json` | `/anchor_provenance/paper` |

In each of these fields, the text after the title is unchanged and correct: "Urban Institute report 411260. DYNASIM3, Runid 432. 2005 Trustees intermediate assumptions", which in the first two continues "; CBO (2005) solvency scoring." No other committed artifact contains the old title. `tests/test_mermin_report_title.py` checks this table against every tracked file under `runs/`, and checks every other tracked file for the old title and its URL.

## The registry follow-up

The anchor-provenance erratum leaves one change to the benchmark registry. The row `dynasim.mermin.four_reform_cost_ordering` still labels Table 1's deficit row DYNASIM3, and the relabel has to ride on the next evaluation append.

No evaluation append is due. `benchmarks/history.jsonl` holds two record sets, from 1 and 2 August 2026, and nothing schedules a third. So [PolicyEngine/microcosm-dynamics#497](https://github.com/PolicyEngine/microcosm-dynamics/issues/497) records what that append must change:

1. the row's four fields (`/external_reference`, `/source_pin/exact_locators/0/document`, `/concept_mismatch/frame` and `/concept_mismatch/population`) and their `spec_revisions` note;
2. a compatibility override that keeps the merged #352 matrix reconstructing byte-exact;
3. the two DYNASIM row counts that key on the label;
4. the pinned registry, history, run-manifest and wall SHA-256 constants, and the regenerated wall;
5. the checks that assume tranche 2 is the latest record set: the tranche-2 assertions in the seed-prefix test and the tranche-2 candidate replay, which needs a script change as well as a test change;
6. an addendum to the anchor-provenance erratum.

Items 1 to 4 were rehearsed in a throwaway checkout, never pushed. The rehearsed append used a placeholder artifact, not a real evaluation. The builders' checks, the #352 round trip and the append-mostly validator passed. The rehearsal also showed which checks in item 5 fail on any third record set; #497 describes the change they need but did not rehearse it.

The registry has no row sourced from the *Five Democratic Approaches* report (Urban 103050). Its DYNASIM4 ID980 correction therefore needs no registry change.
