# Validation matrix referee fixes

## State

Round 1 referee corrections are in progress on `claude/validation-matrix`.
The starting revision is `e9fcf1b013acb7f8fd6584a554fd89944d8fabfc`.

## Done

- Read the referee verdict in full.
- Confirmed the worktree was clean before starting.

## Next

1. Finding 1: demote the 20 Mermin rows to `reported_not_verified`, record
   honest artifact provenance, and list Mermin under `missing_after_refresh`.
2. Finding 2: correct Favreault upstream provenance, regenerate the R7
   artifact without numeric changes, update its pin, and correct all 12
   population/mismatch disclosures.
3. Finding 3: complete every DYNASIM row/column/derivation locator.
4. Finding 4: correct the two SSA published units, the 5.A4 Number-panel
   path, and 4.B11 preliminary flags.
5. Finding 5: split the NRA and age-80--85 COLA mismatch records.
6. Finding 6: complete WISH page/section locators, derivation metadata,
   introduced-bill wording, and by-construction disclosure.
7. Finding 7: remove certification and completeness overclaims.
8. Implement fail-closed, non-writing `--check` modes for both builders and
   strengthen the drift test for both files, capture pins, and locators.
9. Regenerate `matrix.json` and `report.md`, update the drift SHA pin, run
   byte-reproducibility checks, affected tests, tier synchronization, Ruff,
   and Black.
10. Write the final closure report to the requested output file.
