# Entry 8 referee round-1 fixes

## State

The official determination-year COLA correction, SSA stepwise benefit
rounding, and the nonpersistent production coordinator are implemented and
focused-tested. No projection has been run.

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
- Added independent mutation tests for Stage-D predicate ordering, empty PMFs,
  RNG namespace, future-earnings exclusion, the birth-plus-62 PIA year,
  pre-claim payment exclusion, and positive post-claim earnings counts.

## Next

- Add the verbatim frozen gap-block fixture and correct its three current
  section 10 paraphrases.
- Complete the frozen incident-schema mutation battery.
- Run formatting, lint, and fast tests; push the branch and write the final
  report to the requested output file.
