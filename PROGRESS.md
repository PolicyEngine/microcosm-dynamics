# Progress

## State

Implementation and the one-sentence §11 amendment are complete. Formatting,
lint, and fast-suite verification remain before publication.

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
- Amended the single §11 artifact-content sentence to distinguish the stable
  registered echo from the top-level run-time provenance block.

## Next

- Run formatting, lint, and fast tests; push and open the requested PR.
