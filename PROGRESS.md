# PR #286 fix round 2

## State

Implementation is in progress on `sol/entry8-impl`. The round-2 referee review
and coordinator adjudication are the controlling instructions. `origin/master`
has been merged, bringing design amendment `ee1221d`.

## Done

- Read the latest two PR #286 comments: the round-2 conformance review and the
  coordinator's scoped adjudication.
- Merged `origin/master` at `ee1221d`, preserving master's amended design text.
- Confirmed that LaunchAgent, `nohup`, and `caffeinate` mechanics are expressly
  run-time procedure and must not be installed by library or CLI code.
- Implemented the exact one-key deferred context-ratio disclosure.
- Copied the amended 33-line section 10 table byte-for-byte into the fixture
  and runtime gap block, pinned at SHA-256
  `b2330953bf4b517b1bc8f113c596fda0a5d6c60ca240a5cfd232a58346227977`.
- Bound the registered configuration to ratification `6586b92` and amendment
  `ee1221d`; 28 focused amendment tests, Black, Ruff, and diff checks pass.

## Next

- Move registration bootstrap failures inside incident accounting.
- Seal repository identity and path enforcement to the imported package root.
- Add the durable attempt claim and broaden abort handling to `BaseException`.
- Add the round-2 mutation battery, run formatting/lint/fast suites, update this
  file, and write `FINAL_REPORT.md`.
