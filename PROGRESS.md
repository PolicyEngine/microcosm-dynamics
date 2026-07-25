# Entry 8 referee round-1 fixes

## State

All adjudicated implementation fixes are complete and verified locally. The
branch is ready for PR re-review; no projection has been run. Push is blocked
only because this sandbox cannot resolve `github.com`.

## Done

- Read the adversarial implementation review and coordinator adjudication.
- Confirmed that findings 1, 2, 3, 5, 6, and 8 belong to this fix lane.
- Confirmed that finding 7 is limited here to the fixture mechanism and the
  three paraphrase corrections against the current frozen section 10 text.
- Replaced the shifted payment-year COLA anchor with SSA's official
  determination-year values for 1975-2022, ending at 2022=8.7.
- Removed the year-plus-one loader translation, regenerated provenance and
  hashes, and added an independent scattered-year official literal vector.
- Corrected benefit arithmetic to dime-floor each COLA-increased PIA before
  applying and independently dime-flooring the claim-age factor.
- Added a sealed production coordinator that binds the registered input
  factory, loads parameters only through `load_report_parameters()`, freezes
  exact registered bytes and sidecar provenance, executes all phases, and
  publishes every in-ceremony abort as an append-only incident.
- Enforced the canonical artifact path, validated the complete environment and
  contract sidecar schema, made production publication require an opaque
  precompute token, and recorded complete prior-incident history in artifacts.
- Enforced one initial run plus only one explicit retry for an eligible
  external pre-output incident, with changed bytes, publication, and any
  second failure requiring a fresh registration.
- Added narrow production classification for unavailable policyengine-us and
  registered-input dependencies, so the single external pre-output retry is
  reachable without making hash, schema, or other internal failures eligible.
- Serialized the complete production ceremony with a transient kernel lock on
  the existing `runs` directory (no state file), bound the full registered
  input-source chain to committed HEAD bytes, and revalidated both that chain
  and the frozen environment/contract identity before publication.
- Added independent mutation tests for Stage-D predicate ordering, empty PMFs,
  RNG namespace, future-earnings exclusion, the birth-plus-62 PIA year,
  pre-claim payment exclusion, and positive post-claim earnings counts.
- Corrected the three semantic gap-block paraphrases against the current
  frozen section 10 text and pinned the complete Markdown table as a
  byte-exact fixture with an independent literal SHA-256.
- Completed the section 11 incident mutation battery: exact schema keys and
  types, literal schema and phase values, filename/index and partial-path
  rules, precompute-echo drift, outside-echo numeric arrays, retry truth
  table, and contiguous append behavior.
- Passed repository-wide Black (`486` files) and Ruff, the complete focused
  fix-round suite (`146 passed`), unit tier (`824 passed, 5 skipped`), and
  artifact tier (`1,221 passed, 40 skipped`); recounted all `3,573` tests.
- Wrote the final handoff report to `FINAL_REPORT.md`.

## Next

- Push `sol/entry8-impl` from a network-enabled environment.
- After the coordinator's finding-7 design amendment lands, refresh the
  byte-exact gap-block fixture in the amendment's implementation pass.
