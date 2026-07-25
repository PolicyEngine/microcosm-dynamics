# Progress

## State

Implementation, regression coverage, the §11 amendment, formatting, lint,
and both fast tiers are green. Publication is blocked outside the worktree:
terminal DNS/network access is disabled, and GitHub app branch/blob writes
were cancelled by the connector approval layer.

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
- Updated the artifact-tier count from 1,303 to 1,304.
- Verified 132 coordinator/artifact/preparation tests pass.
- Amended the single §11 artifact-content sentence to distinguish the stable
  registered echo from the top-level run-time provenance block.
- Verified the complete artifact tier: 1,264 passed, 40 skipped.
- Verified Ruff repository-wide and Black across all 486 Python files.
- Verified the complete unit tier: 824 passed, 5 skipped.
- Confirmed `git push` cannot resolve `github.com` in the terminal sandbox.
- Tried the connected GitHub app's blob and branch publication paths; both
  returned `user cancelled MCP tool call`.

## Next

- Approve GitHub app writes or provide terminal GitHub network access.
- Push `sol/entry8-echo-fix` and open the requested non-draft PR to `master`.
- Write the final report with file/line references, counts, and the PR URL.
