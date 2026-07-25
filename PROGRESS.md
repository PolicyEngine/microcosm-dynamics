# Progress

## State

The reducer's reproducible loader, corrected source law, Stage-A/B funnel, and
production Stage-C/D birth sensitivity are implemented and exercised
successfully against the cached draw-0 object.

## Done

- Attempted `git fetch origin`; network DNS was unavailable, so the cached
  reference was used.
- Reset branch `sol/entry8-birth-evidence` to cached `origin/master`.
- Verified the cached master SHA is the required `daf3ff5`.
- Traced the registered loader and bounded scripts-path context through the
  candidate-3 fit/materialization/projection prefix.
- Verified the seed convention from `m6_population.py`: seed `year` is the
  reference year immediately before the collection-wave `anchor_wave`, while
  `age` is the collection-wave PSID code. Clause 3 therefore uses
  `seed.year - seed.age == (anchor_wave - 1) - seed.age`: 2014 for the 2015
  initial slice and 2016/2018 for 2017/2019 entrants.
- Reconciled the source-law oracle: 6,392 initially unresolved split into
  4,077 actual ages, 2,298 coarse infant codes, and 17 sentinels; the corrected
  whole-population mix totals 30,482.
- Reconciled the Stage-A-respecting funnel: 276 raw claim-year carriers among
  the initially unresolved split into 190 `di_unknown` and 86 true Stage-B
  candidates; the latter split 69 opening backfills / 17 modeled awards.
  Canonical candidates total 3,083, including 2,784 domain residents.
- Verified the production inclusion seam can run on the resolved candidate
  universe without changing candidate semantics; all 86 clause-3 candidates
  land at the first Stage-D predicate (`excluded_domain_incomplete`).
- Verified the pinned runner environment loads policyengine-us 1.752.2 and the
  full report parameter bundle; baseline included clause-2 claimants total
  1,440.
- Added `scripts/first_estimates_birth_evidence.py` with pinned repository and
  interpreter guards, cache SHA validation, and the registered one-real-draw
  regeneration path.
- Implemented seed-frame invariants, PSID code dispositions, derived-birth
  plausibility assertions, whole-population reconciliation, full Stage-A DI
  partitioning, Stage B, and production Stage-C/D baseline transport.
- Exercised the implementation: all section A/B counts match the referee
  oracle, and all 86 newly dated candidates land at the first domain predicate.
- Re-ran the production Stage-C opening-stock draw and ordered Stage D under
  birth-minus-one and birth-plus-one for every canonical candidate, perturbing
  only imprecise age-derived sources.
- Reconciled the sensitivity oracle exactly: one era flip, no empty-span
  flips, 600 chronology flips (294 inclusion-changing), 15 coverage flips,
  and 310 inclusion-changing directions across 304 distinct people, all
  clause-2 dated.
- Asserted that the extracted ordered predicates reproduce the unperturbed
  production result exactly before using them for flip accounting.

## Next

- Add the pinned-parameter benefit-ledger sensitivity and canonical writer.
- Run draw 0 with the pinned runner interpreter, reconcile every oracle row,
  and commit the canonical JSON.
- Write and commit `FINAL_REPORT.md` with commands, outputs, reconciliation,
  and judgment calls.
