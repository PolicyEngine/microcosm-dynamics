# Era slot/grammar extraction B progress

## State

- Branch: `claude/ce-era-extraction-b`
- Scope: questionnaire-slot and absence-domain extraction for 1979-2001,
  plus fixed-width grammar rows 10 and 13.
- Status: contract and source discovery in progress.

## Done

- Verified `covered_earnings_correction_registry.design_binding()` returns
  revision 7, ratification commit `985be84fdeec70ffd20aa1e60dec7d300b7a555b`,
  and design SHA-256
  `8f90dd1aee59e6857418d2a73b617e5cb3991eba3a237a78303586a8c2a9debc`.
- Confirmed the worktree did not contain forbidden root `PROGRESS.md` or
  `FINAL_REPORT.md` files before work began.
- Identified the exact revision-7 Class-A and Class-B laws and inventory
  residual indices 10, 11, 13, and 14.

## Next

- Translate section 19's source-only grammar and filtered-H absence laws into
  era-artifact schemas, validators, and tests.
- Extract and validate the 1979-1993 era artifact, then commit it.
- Extract and validate the 1994-2001 era artifact, then commit it.
- Run focused and full validation, update this ledger, and write the external
  final report.
