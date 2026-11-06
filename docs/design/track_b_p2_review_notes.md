# P2: notes on the frozen specification

`docs/design/track_b_p2_spec.md` is P2's frozen specification, copied
byte for byte from the blind choices lane's output (SHA-256
`df5df7f2de3992a95d24ae49cbc2924c6c415d9316472c7bdb0d75f254769681`).
Ruling d1803 (Max, 2026-10-21) required P2's choices to be fixed before
any S1 real-data result, by a lane blind to B2's outcome. The spec is not
edited; these notes sit beside it.

## The outcome-aware check (2026-10-23)

The outcome-aware reviewer (GPT-6.1 Sol) checked the frozen choices only
for fitting to B2's failure. Verdict: **no fitting found**, with no high
or medium findings. It classified each choice against the GPT-6.1 Sol
proposer's original P2:
- same as the proposal: features and nominal scale, standalone on v1, lag
  count, removed objects;
- necessary specification of it: indicator construction, missing-history
  coding, retained objects, tests, counterexample, reserve position;
- narrow departures with reasons independent of B2's outcome: the
  positive-earnings threshold aligned with the pinned classifier's 1e-6
  raw-value tolerance; whole-operation refusal of invalid older earnings;
  no support audit in development, per d1803.

Its two low findings are recorded here rather than by editing the spec:

1. **The proposer's support-audit condition is unmet.** The GPT-6.1 Sol
   proposer wanted a frozen PSID support audit before considering P2's
   registration. Development under d1803 reads no PSID data, so that
   condition remains unmet. Max must address it when P2's registration is
   considered.
2. **Blindness record.** The choices lane's context files are kept in its
   root with their hashes. Its root record, which names outcome-scan
   patterns, sits outside the root that the lane was confined to, and was
   not a lane input. The lane declares that it met no B2 cell result or
   gap.

## Amendment 1 (2026-10-23)

The first blind build stopped, as the spec requires, because frozen T4
could not run as written. On T4's all-positive fixture the pinned
estimator records `POSITIVE_ONLY` and fits no participation classifier,
and unchanged v1 then fails at its first gate query.

A lane blind to B2's outcome, on the same cleaned root at `2ef10532`,
verified that finding and wrote
`docs/design/track_b_p2_spec_amendment_1.md` (SHA-256
`b1c7c99313a2c50b815a8de8afba36fa901ea4b94a51f59711ef50697cd9374e`).
- It replaces only T4's unavailable v1 reference with a test-local
  evaluator of the inherited always-positive law. T4's fixture, seeds,
  exactness and mutation are kept.
- It checks that every other test and mutation runs as written.
- It leaves sections 1-6, 9-10 and the law unchanged.

The frozen spec file is not edited. The amendment is read together with
it.
