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

## Next

1. Finding 2: correct Favreault upstream provenance, regenerate the R7
   artifact without numeric changes, update its pin, and correct all 12
   population/mismatch disclosures.
2. Finding 3: complete every DYNASIM row/column/derivation locator.
3. Finding 4: correct the two SSA published units, the 5.A4 Number-panel
   path, and 4.B11 preliminary flags.
4. Finding 5: split the NRA and age-80--85 COLA mismatch records.
5. Finding 6: complete WISH page/section locators, derivation metadata,
   introduced-bill wording, and by-construction disclosure.
6. Finding 7: remove certification and completeness overclaims.
7. Implement fail-closed, non-writing `--check` modes for both builders and
   strengthen the drift test for both files, capture pins, and locators.
8. Regenerate `matrix.json` and `report.md`, update the drift SHA pin, run
   byte-reproducibility checks, affected tests, tier synchronization, Ruff,
   and Black.
9. Write the final closure report to the requested output file.
