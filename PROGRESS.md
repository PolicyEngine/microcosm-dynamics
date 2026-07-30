# Unit 1 Round 3 Progress

## State

- Branch: `claude/ce-impl-extraction`
- Baseline: `2ff590d`
- Current phase: complete.
- Constraints: use committed source bytes only; keep final registration
  fail-closed; commit each coherent edit; do not push.

## Done

- Confirmed the worktree is clean at the requested baseline.
- Recorded the three exact recheck edits and the required verification queue.
- Identified `FINAL_REPORT.md` as the established final output-file convention.
- Removed the evidence loader and validator from the authoritative registry
  module and its public exports.
- Renamed all three nested identity collections and schema IDs from final
  `*_specs.v1` authority names to explicit `*_evidence.v1` names.
- Regenerated and independently pinned 1,515,381 canonical evidence bytes at
  SHA-256
  `1080acc9672abf209bb9c5ec06170ca351b26200ba1727652fd515b25b216380`.
- Proved every evidence row shape is rejected by every final-registry
  ingestion path; the evidence/registry focused suite passes: `40 passed`.
- Replaced the passing fixture's invented one-key rounding object with the
  exact seven-key null-tagged shape.
- Enforced exact B2/B11 source-cell IDs and ordering, literal vintage-2
  identity, ASCII year equality, role/status/source-class derivation, all 15
  family loss assignments, hard-zero and positive-weight domains, exact
  selection matrices and tolerances, and available/unavailable selector laws.
- Enforced both rounding tags and prohibited verified rounding for every
  B2/B11-derived target whose committed operand rules are unverified.
- Kept opaque observation/physical/ancestry resolution at the full-registry
  boundary; row-local validation does not invent an ID grammar, and full
  registration still aborts before claiming foreign-key or weight authority.
- Exact-schema/evidence focused tests pass: `111 passed`.
- Added source-byte and fragment-hash reproduction for the VI.G1
  taxable-payroll/GDP series and both directly published IV.B4
  worker/beneficiary ratios.
- Added the exact 2023 4.B10/4.B12 quotient
  `182,689 / 186,620 = 0.9789358054`, together with its CWHS,
  unduplicated-worker, and preliminary-status source fragments.
- Recorded the quotient's synthesized, preliminary, 2023-only, and
  no-HI-model-analogue failures, and added
  `one_as_published_covered_share_observation_per_year` to candidate (b).
- The adjudication tests pass: `19 passed`; the combined four-file suite
  passes: `153 passed`.
- Repinned the artifact tier for the 78 added cases: full collection is
  `4,073` tests, comprising `822` unit, `1,768` artifact, `804`
  integration-PSID, `520` legacy-reproduction, and `159`
  PolicyEngine-oracle tests.
- Black at line length 79 leaves all six changed Python files unchanged;
  repository-wide Ruff and `git diff --check` pass.
- Required suites pass: four-file source/registry `153 passed`; full
  estimates `508 passed`; complete entry-11 `130 passed`.
- The explicit fail-closed tail passes all 13 parametrized cases, and the
  full tier-policy manifest assertion passes against all 4,073 tests.
- Independent review reproduced every new source and fragment hash and
  returned APPROVE with no actionable findings.
- Wrote the exact dispositions, verification tails, commits, and hygiene
  result to `FINAL_REPORT.md`.

## Next

1. No round-3 implementation work remains.
2. A future successful registration still requires the missing primary SSA
   membership/share evidence and frozen model-side universe, weight, digest,
   denominator-selector, and concordance authority.
