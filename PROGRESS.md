# Progress

## State

The coordinator now compares only stable registered provenance, freezes the
separate run-time record before compute, and publishes both as distinctly
labeled artifact blocks. The requested later-checkout regression passes.

## Done

- Created the requested branch from the adjudicated baseline.
- Read the latest incident-2 adjudication on issue #289.
- Kept versions, relative file/directory identities, hashes, and asserted
  actuals in `ReportParameters.provenance`.
- Moved the git revision and all 12 absolute paths into
  `ReportParameters.runtime_provenance`.
- Added a registered-parameter guard against run-time fields and absolute
  paths.
- Verified 16 targeted tests pass in the main virtual environment.
- Froze canonical run-time provenance bytes in the pre-compute token.
- Added top-level artifact `runtime_provenance` while keeping the registered
  configuration echo stable and byte-compared.
- Added regression coverage showing changed revision/roots pass while a
  changed nested parameter-file hash aborts before compute.
- Updated the unit-tier count from 829 to 830.
- Verified 132 coordinator/artifact/preparation tests pass.

## Next

- Update the one §11 artifact-content sentence as an amendment-class change.
- Run formatting, lint, and fast tests; push and open the requested PR.
