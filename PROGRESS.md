# Progress

## State

The parameter loader now separates stable registered provenance from
run-time identity. Targeted loader and runner tests pass.

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

## Next

- Bind run-time provenance through the coordinator and artifact separately
  from the compared configuration echo.
- Add the later-commit/stable-hash regression and update §11.
- Run formatting, lint, and fast tests; push and open the requested PR.
