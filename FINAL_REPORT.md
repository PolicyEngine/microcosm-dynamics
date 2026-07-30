# Unit 1 Round 3 Final Report

## Outcome

The three exact recheck edits are complete. The disposition remains
**SHIP WITH EDITS — V-B7 adjudication confirmed**.

No committed construction satisfies the ratified covered-worker-incidence
target, and the committed bytes still do not establish the complete B2/B11
membership or model-side authority required for final registration.
Accordingly:

- no `ssa_covered_earnings_calibration_targets.vintage2` artifact exists;
- no evidence-only row can enter a final-registry ingestion path;
- build, render, final getters, and full registration remain fail-closed; and
- no vintage-2 identity was minted.

## Edit 1 — evidence-only registries

Disposition: **complete**.

- Removed the evidence getter and validator from
  `scripts/covered_earnings_correction_registry.py` and its `__all__`.
- Renamed the nested collections and schema IDs to:
  `physical_source_cell_evidence.v1`,
  `official_source_alias_evidence.v1`, and
  `official_source_arithmetic_rule_evidence.v1`.
- Added tests proving each evidence row type is rejected by the row,
  collection, and frozen-final-registry ingestion APIs.
- Regenerated the canonical evidence file as 1,515,381 bytes with SHA-256
  `1080acc9672abf209bb9c5ec06170ca351b26200ba1727652fd515b25b216380`.

The evidence remains source-reproduced and useful, but is no longer
authority-shaped or publicly exposed through the authoritative module.

## Edit 2 — exact nested-schema validator

Disposition: **complete**.

`validate_calibration_target_row_schema()` now enforces the full row-local
law for:

- the two exact seven-key tagged-rounding shapes;
- literal artifact-vintage identity, ASCII source years, and exact ordered
  family/year source-cell IDs;
- status, role, source-class, and availability derivation;
- all 15 target-family loss assignments;
- hard-zero versus positive-weight domains and selection eligibility;
- the exact validation-year matrices and family tolerances; and
- available/unavailable model selector, reduction, unit, and concordance
  fields.

The passing fixture now uses the valid seven-key null-tagged rounding shape.
Opaque resolved IDs remain the full registry's responsibility: row-local
schema validation does not invent an ID grammar, while full registration
continues to abort before claiming foreign-key or normalized-weight
authority.

## Edit 3 — exhaustive V-B7 adjudication

Disposition: **complete; rejection confirmed**.

The executable adjudication now includes source-hash-reproduced rejection
rows and tests for every omitted concrete candidate:

| Candidate | Reproduced evidence | Rejection |
|---|---|---|
| Trustees VI.G1 | Published taxable-payroll/GDP ratios and exact definition/header fragments | Dollar macro ratio, not worker incidence; incomplete target-year coverage and no worker denominator |
| Trustees IV.B4 workers per beneficiary | Direct published 1968–2022 ratios and exact coalesced definition/header fragments | Beneficiary-burden ratio, not a worker-incidence share |
| Trustees IV.B4 beneficiaries per 100 workers | Direct published 1968–2022 ratios and exact coalesced definition/header fragments | Beneficiary-burden ratio, not a worker-incidence share |
| Supplement 4.B10 OASDI workers / 4.B12 HI workers | `182,689 / 186,620 = 0.9789358054`; exact operand, CWHS, unduplicated-worker, and preliminary-status fragments | Synthesized, preliminary, 2023-only, outside registered roles/eras, and no HI model-denominator analogue |

Candidate (b) now explicitly records
`one_as_published_covered_share_observation_per_year` among its failures.
Independent review reproduced the document and fragment hashes, ratio cells,
and quotient and returned **APPROVE** with no actionable findings.

## Verification tails

Formatting and lint:

```text
black --check -l 79 <6 changed Python files>
6 files would be left unchanged.

ruff check --no-cache .
All checks passed!

git diff --check
clean
```

Four-file source/registry suite:

```text
153 passed in 4.77s
```

Full estimates suite:

```text
508 passed in 20.84s
```

Complete entry-11 suite:

```text
130 passed in 4.17s
130 tests collected as artifact
```

Explicit fail-closed tail selection:

```text
13 passed in 1.70s
```

Tier-policy manifest assertion:

```text
1 passed, 4072 deselected in 1.47s
```

Full tier collection:

| Tier | Collected |
|---|---:|
| unit | 822 |
| artifact | 1,768 |
| integration-PSID | 804 |
| legacy reproduction | 520 |
| PolicyEngine oracle | 159 |
| **Total** | **4,073** |

The 78 new cases are artifact-only. Both `tests/tier_counts.json` and
`tests/README-tiers.md` carry the new inventory.

## Commits and hygiene

Coherent-step commits before this report:

1. `a1e734b` — track Unit 1 round 3 progress;
2. `7b1795e` — separate source identity evidence from authority;
3. `0341af1` — enforce exact calibration target row laws;
4. `8140ae9` — make V-B7 adjudication exhaustive; and
5. `74ec89e` — repin the round-3 artifact tier inventory.

The branch remains local. No push was performed.
