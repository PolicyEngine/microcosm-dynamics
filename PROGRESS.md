# Validation matrix referee fixes

## State

Round 1 referee corrections are in progress on `claude/validation-matrix`.
The starting revision is `e9fcf1b013acb7f8fd6584a554fd89944d8fabfc`.

## Done

- Read the referee verdict in full.
- Confirmed the worktree was clean before starting.
- Finding 1: removed all 20 Mermin rows from the 22-row canonical
  verified-source matrix; retained them in a separate
  `reported_not_verified` class with committed-artifact provenance, the
  explicitly unmanifested corroborating-copy SHA, and Mermin listed under
  `missing_after_refresh`.
- Finding 2: corrected Favreault Table 3 upstream provenance and all 12
  matrix rows for the 2049 adult OASDI beneficiary population, OASI-plus-DI
  scope, 2049 marital-status timing, and conditional denominators. Regenerated
  `replication_r7_sharing_v1.json` from SHA-256
  `5442fc41ad1eae1a7a1d67bb20d66691514fbab482399620d88486a4f7b6487d`
  to `85f7d1dfd680d7d23975046526f1972774719af302a414e02c2c9f19f53c559b`;
  all 1,870 numeric JSON leaves are unchanged.
- Finding 3: added exact `row_path` and `column_path` locators to all 32
  DYNASIM rows, with explicit derivations for the nine Favreault rounded-
  bucket sums and the Mermin reform ordering.
- Finding 4: separated the two SSA published units from the model units,
  qualified 5.A4 with the Number-panel row path, and restored 2021-2022
  preliminary status to every canonical 4.B11 locator.
- Finding 5: split the two COLA mismatch records so ages 62-67 and 80-85
  carry their correct 2050 populations, evaluation ages, year bases, and
  survival-weighting disclosures.
- Finding 6: completed WISH statutory locators across PDF pp. 16-18, marked
  combined wage-side 0.6% as derived `0.3 + 0.3` rather than printed,
  replaced operative language with introduced/not-enacted conditionals, and
  disclosed in the main table that zero deviation is by construction.

## Next

1. Finding 7: remove certification and completeness overclaims.
2. Implement fail-closed, non-writing `--check` modes for both builders and
   strengthen the drift test for both files, capture pins, and locators.
3. Regenerate `matrix.json` and `report.md`, update the drift SHA pin, run
   byte-reproducibility checks, affected tests, tier synchronization, Ruff,
   and Black.
4. Write the final closure report to the requested output file.
