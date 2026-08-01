# Era slot/grammar extraction A progress

## State

- Branch: `claude/ce-era-extraction-a`
- Scope: questionnaire-slot and absence-domain extraction for 1968-1978,
  plus fixed-width grammar rows 0 and 4.
- Status: contract and source discovery in progress.

## Done

- Verified `covered_earnings_correction_registry.design_binding()` returns
  revision 7, ratification commit `985be84fdeec70ffd20aa1e60dec7d300b7a555b`,
  and design SHA-256
  `8f90dd1aee59e6857418d2a73b617e5cb3991eba3a237a78303586a8c2a9debc`.
- Confirmed the worktree did not contain forbidden root `PROGRESS.md` or
  `FINAL_REPORT.md` files before work began.

## Next

- Translate the ratified section 19 laws and inventory predicates into artifact
  schemas and validators.
- Extract and validate the 1968-1975 era artifact, then commit it.
- Extract and validate the 1976-1978 era artifact, then commit it.
- Run focused and full validation, update this ledger, and write the external
  final report.
