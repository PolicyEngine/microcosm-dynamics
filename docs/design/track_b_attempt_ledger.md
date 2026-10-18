# Track B cumulative attempt ledger

The Track B design (§7, "Attempt ledger") requires this record:

> Maintain a cumulative attempt ledger by mechanism and gate family. Renaming a module or registration does not reset the counter. Restart after exhaustion requires new independent evidence and a new registration.

**Scope.** This ledger begins with B2. Earlier gates' candidates and attempts are recorded in their own registrations on issue #42.

**What counts as an attempt.** A scored candidate run under a registration. A floor build that stops before any candidate run is recorded here but is not an attempt.

**When the program pauses.** Two independently justified registered successors that fail trigger `SUCCESSOR_EXHAUSTED` (design §7).

## B2: the 2010→2014 earnings transport gate

- **Mechanism:** candidate 3's forward-earnings law, `m6_candidate3_engine_v1`, spec SHA-256 `c9be28a28d6fcc3911723872386906af559f6d0e0d5c89a87f741a5b2c3eacd6`.
- **Gate family:** B2's level cells.

| # | Date (UTC) | Registration | Run | Outcome | Attempt? |
|---|---|---|---|---|---|
| — | 2026-10-15 | #42 comment 6199723681 (d1342 A: the six level cells) | Floor build only: commit `7fdc8f91`, artifact `runs/track_b_b2_floor_v1_stopped.json` (`500f801e…`) | `WEAK_POWER_OR_VACUITY` at floor build (#42 comment 6200099988) | No. No candidate ran |
| 1 | 2026-10-18 | #42 comment 6252388925 (d1606 C1: p90 and the zero-earnings rate by cohort) | Floor commit `89c0ed9d`, score commit `430f8883`: `runs/track_b_b2_score.json` (`df82a102…`) | **`FAIL`** (#42 comment 6252752628) | **Yes, attempt 1** |

**Attempt 1's failure.**
- `earn_zero_rate.prime`'s full-support gap is 0.3034, against a tolerance of 0.202.
- No gate seed passes.
- Three of the four gated bounds exceed their tolerances.

**Its consequence.** Under `GATE_FAIL_OR_REGRESSION_FAIL` (design §7), B2 is not admitted, and its dependants (H, B3L) cannot rely on it. Any successor needs a new registration and is counted here.
