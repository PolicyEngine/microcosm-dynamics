# Track B B1 v2: design amendment note

**Status: build-only amendment note, 2026-09-29. No real-data computation.**

The Track B design lives outside this repository, at
`microcosm-launch-evidence/dynasim-parity-20260909/trackb-design-20260928.md`
(revision 3, SHA-256 prefix `6fd6f4aa5a83da80`). This note does not edit that
file. It records how B1 v2 relates to the design's B1 requirement and what a
v2 result means for the milestones that depend on B1.

## What the design requires of B1

- The §3.1 milestone table's B1 row (design line 118) requires "Equality for
  every registered seed and draw: original per-person scored earnings,
  support, weights, and fit and RNG signatures, not just the six aggregate
  cells", and labels B1 "reproduction, not validation".
- §3.2 (line 145) admits B1 only for "That the replay reproduces candidate
  3's registered outputs bit for bit."
- §5.4 (lines 326–329) makes exact equality over those same components
  B1's only criterion.
- §7 (line 451) names `BASELINE_REPLAY_MISMATCH` / `RUN_INVALID`, triggered by
  "Changed draws, support, weights or signatures", as stopping "B2 and
  everything built on the replay".

## Why v1 cannot meet it

Candidate 3's per-person outputs and RNG signatures were never archived, so
no historical person-level reference exists for the equality those lines
require. The v1 runner (`--baseline-version bit-for-bit`, the default)
therefore records `BASELINE_REPLAY_MISMATCH` with reason
`historical_person_level_reference_unavailable`. It can report `REPRODUCED`
only when a reference whose bytes hash to the committed
`HISTORICAL_REFERENCE_SHA256` is supplied (`track_b/runner.py`, the v1 status
at line 640). That constant is `None`, so v1 has no route to admission.

## What v2 is

Max's ruling d571 (2026-09-28) registers a separate, weaker B1 version, v2
"reconstructed reproduction", selected only by
`--baseline-version reconstructed` (`track_b/runner.py:66–70`). It passes as
`RECONSTRUCTED_REPRODUCTION`, with admitted scope
"reconstructed reproduction (weaker than bit-for-bit)"
(`track_b/reconstructed.py:57–58`). It passes only when all four of the
following hold exactly, with no tolerances (`CONDITIONS`,
`track_b/reconstructed.py:60–65`; `admission`, line 790):

1. **Per-draw cells.** All 600 committed per-draw cells (5 seeds × 20 draws
   × 6 earnings cells) in `runs/gate_m6_candidate3_v1.json` equal both the
   copied loop's cells and the unchanged original loop's cells
   (`compare_cells`, line 183).
2. **Fit lineage.** The committed fit lineage is equal (`compare_lineage`,
   line 302).
3. **Person-level differential.** The unchanged original loop and the copy
   agree person by person on the same inputs: scored earnings, support and
   weights, plus fit and RNG signatures. Scored frames lacking earnings or
   weight fail (`compare_evidence_differential`, line 507).
4. **Provenance.** Every registered provenance record is equal, and the
   `ssa_revision` anchor reproduces `f10cca5` in the pinned environment
   rather than being normalized (`compare_provenance`, line 668;
   `anchor_problems`, line 617).

Any failure records `BASELINE_REPLAY_MISMATCH` and names the failed and
unevaluated conditions. The guard re-derives all four conditions from the
published evidence before admitting a v2 claim (`guard_claim`, line 1199).

## Reading taken

**§3.1's B1 row and §3.2's bit-for-bit scope are satisfied only by the v1
path.** A v2 pass does not satisfy them and must never be described as
bit-for-bit reproduction, or as equality to candidate 3's historical
person-level output.

**For §7, a v2 pass clears the `BASELINE_REPLAY_MISMATCH` stop for B2.** The
reasons:

- §7's trigger is changed draws, support, weights or signatures (line 451).
  Condition 3 checks each of these person by person against the unchanged
  original loop.
- Conditions 1 and 2 bind that loop to candidate 3's committed cells and
  fit lineage.
- d571 was ruled because bit-for-bit is unreachable. Reading §7 as
  requiring v1 would make B2 permanently unreachable, which the ruling did
  not intend.

This clearance is conditional: B2's registration must state that its
baseline is B1 v2, a reconstructed reproduction weaker than §3.2's
bit-for-bit, and carry that label into every downstream disclosure. A v2
`BASELINE_REPLAY_MISMATCH` stops B2 exactly as §7 says.

If the B2 registration review rejects this reading, B2 stays blocked until
an authenticated historical reference is recovered and v1 passes. v2 does not
change what v1 reports.
