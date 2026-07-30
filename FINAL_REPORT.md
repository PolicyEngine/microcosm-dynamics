# Unit 1 Round 2 Final Report

## Outcome

All five referee findings are closed under the ratified fail-closed law.
Committed primary-source bytes do **not** establish a lawful V-B7
covered-worker-share construction or all required model/source universe
authorities. The correct true-vintage-2 result is therefore:

- no `ssa_covered_earnings_calibration_targets.vintage2` artifact;
- no `calibration_target_specs.v2` rows;
- no positively certified final physical/alias registry;
- every final build, render, registry getter, and full-registration validator
  aborts; and
- all source identity that the bytes do establish is retained separately as
  explicitly non-authoritative, source-reproduced evidence.

This is the design-mandated consequence, not a successful empty
registration and not a staging vintage.

## Finding 1 — true vintage 2 and V-B7

Disposition: **closed, fail closed**.

The incomplete final artifact was deleted. The extractor retains all 825
verified Table 4.B2/4.B11 cells as identity-free source evidence, adjudicates
V-B7 from committed bytes, and makes `build()`, `render()`, legacy artifact
validation, and every registration entry point abort.

### V-B7 adjudication

| Clause | Establishing committed bytes | Verdict |
|---|---|---|
| Exact publication, table, edition, and source vintage | [Supplement 2025 Table 4.B1 caption and headers](data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L35); [Trustees 2026 Table IV.B4 caption and headers](data/external/snapshots/ssa_level_anchors_vintage1/trustees2026_lr4b4.html#L214); [capture manifest](data/external/snapshots/ssa_level_anchors_vintage1/capture_manifest.txt#L4) | The operand identities are exact and hash-verified. Identity alone does not establish a valid ratio. |
| Candidate (a) numerator | 4.B1 `Reported taxable > Amount` and `Percentage of total` headers at [lines 57–62](data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L57); footnote a at [line 935](data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L935) | Exact taxable-earnings-dollar numerator and published percentage established. |
| Candidate (a) denominator | 4.B1 `Total in covered employment` header and footnote d at [line 944](data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L944) | Exact same-table covered-employment earnings-dollar denominator established. |
| Candidate (a) every year | 1968 publishes `81.7` at [lines 300–308](data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L300); 2014 publishes `83.1` at [lines 806–814](data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L806); all 1968–2022 cells are uniquely parsed | Availability and same-system dollar-universe clauses pass. |
| Frozen target estimand | The design fixes a person-level worker-incidence ratio at [§3.1](docs/design/covered_earnings_correction.md#L237) and its target formula at [§6.2](docs/design/covered_earnings_correction.md#L2315) | Candidate (a) fails. An earnings-dollar share cannot replace the ratified worker-incidence target. |
| Candidate (b) numerator | 4.B1 total workers header at [lines 43–54](data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L43); 4.B11 footnote a says dual wage/SE workers count once in total at [line 15813](data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L15813) | Displayed annual OASDI taxable-worker count and dual-type treatment established. Same-type multiple-job uniqueness is not. |
| Candidate (b) denominator | IV.B4 `Covered workers` header at [lines 263–267](data/external/snapshots/ssa_level_anchors_vintage1/trustees2026_lr4b4.html#L263); footnote a at [lines 4913–4915](data/external/snapshots/ssa_level_anchors_vintage1/trustees2026_lr4b4.html#L4913) | Displayed annual covered-worker count and calendar-year timing established. |
| Annual timing, OASDI scope, and worker unit | Both tables publish calendar-year OASDI worker counts in thousands; IV.B4 says paid sometime during the year | Pass for the displayed timing, scope, and unit. This is not the prohibited SSA/CPS point-in-time mix. |
| Duplicate-worker treatment | 4.B11 settles wage/SE dual counting. IV.B4 does not settle unique-person, multiple-employer, same-type, or historical SE duplication. 4.B10's 2023 unduplicated note at [line 14818](data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L14818) does not establish every historical IV.B4/B1 cell. | Fail. |
| Population universe and numerator-subset law | 4.B1 cites MEF/BEA/BLS and includes SE; IV.B4 does not establish an exact matching frame/geography/SE rule. In 1978 the displayed ratio is `110,600 / 109,432 = 1.010673`; across 1968–2022 it is above one in 31 years, below one in 24, and equal in none. The computation is source-reproduced at [builder lines 680–842](scripts/build_ssa_covered_earnings_calibration_targets.py#L680). | Decisive fail. The displayed operands do not form an exact subset share; clipping or reconciliation is not source-authorized. |
| Every included year and §6.2 era minima | Raw B1 and IV.B4 operands exist across all required eras and 2009–2014 | Raw availability passes, but no year is registrable because duplicate, universe, subset, and published-observation clauses fail. Therefore every era minimum fails at registration. |
| One published covered-share observation per year | The observation law at [design lines 1860–1886](docs/design/covered_earnings_correction.md#L1860) requires an `as_published` covered-share cell | Candidate (b) is a synthesized cross-publication quotient, not a published covered-share cell. Fail. |
| Candidate (c), Trustees VI.G1 | VI.G1 publishes GDP and taxable-payroll dollars at [lines 242–286](data/external/snapshots/ssa_level_anchors_vintage1/trustees2026_lr6g1.html#L242); its multiple-employer adjustment note is at [lines 4566–4570](data/external/snapshots/ssa_level_anchors_vintage1/trustees2026_lr6g1.html#L4566) | Reject. It supplies dollars, begins in 1970, and provides no person/worker denominator or matching duplicate rule. |
| Other same-source ratios | B11 `T/(W+S)` is a transform of overlapping marginals; maximum-earner and entrant shares measure cap/entry status | Reject. They are not covered-worker incidence; `T/(W+S)` is also dependent on the registered B11 membership system. |
| SSA-unique-worker over CPS/BLS average prohibition | No committed annual-unique CPS/BLS denominator exists; the prohibition is explicit at [design lines 2026–2032](docs/design/covered_earnings_correction.md#L2026) | Pass by rejection: no prohibited mixed-system construction is used. |
| Final V-B7 disposition | The fixed law requires all clauses and every included year to be established from primary bytes | **No construction qualifies. `covered_share_required_years` remains empty only as a failure state; authoritative vintage 2 and target registration abort.** |

### B2/B11 worker-membership adjudication

| Family/clause | Establishing committed bytes | Verdict |
|---|---|---|
| B2 c5/c11 | Header at [lines 964–995](data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L964); c5 includes above-cap wages and c11 is the wage-worker marginal; footnotes at [lines 2111–2129](data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L2111) | Column grouping and wage-cap case pass. Zero/below-threshold and same-type duplicate membership do not. Family fails closed. |
| B2 c8/c12 | Same header/footer establishes reported SE net earnings, the SE-worker marginal, and dual-type inclusion in each type | Grouping passes. Signed losses, loss-only filers, below-threshold SE, and multiple-component aggregation are unresolved. Family fails closed. |
| B11 T/W/S | B11 headers at [lines 14838–14861](data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L14838) and footnote a at [line 15813](data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L15813) establish the union/marginal dual-type algebra | Official structural transforms pass. Exact model-side zero/loss/threshold/cap/multiple-job membership remains unresolved. Worker-distribution families fail closed. |
| §6.1 consequence | The registration prerequisite is at [design lines 2005–2015](docs/design/covered_earnings_correction.md#L2005) | B2 wage intensity, B2 SE intensity, B11 worker distributions, and covered share cannot register. |

## Finding 2 — exact `calibration_target_specs.v2`

Disposition: **closed by exact schema enforcement and abort**.

- The validator exposes and enforces the exact 30-field row law at
  [registry line 64](scripts/covered_earnings_correction_registry.py#L64),
  including exact nested `universe`, `universe_concordance`, mapping,
  transformation, selector, role, year, digest, and tolerance shapes.
- The reduced 25-field export and its test assertion were removed.
- The five formerly omitted fields are resolved as unavailable authority, not
  filled with placeholders:
  `universe`, `model_universe_id`, `model_weight_field`,
  `model_weight_source_sha256`, and `universe_concordance`.
- The field-by-field adjudication is frozen at
  [registry line 156](scripts/covered_earnings_correction_registry.py#L156).
- `calibration_target_specs()` and `frozen_registries()` abort at
  [registry lines 609–633](scripts/covered_earnings_correction_registry.py#L609).
  No object with missing or invented fields can claim the final schema.

## Finding 3 — physical cells and alias closure

Disposition: **closed for all source-established evidence; final authority
correctly remains aborted**.

- 945 source-reproduced physical occurrences have exactly the design's 12
  fields; they cover all 120 vintage-1 cells and all 825 entry-11 B2/B11
  cells.
- The exact seven-part structural-locator tuple hashes to 921 unique
  locators. The 24 repeated B11 cells share structural/token/semantic/source
  hashes across the vintage-1 and entry-11 extraction occurrences.
- The complete proven seven-field alias closure contains:

  - 24 `same_physical_cell`;
  - 24 `cross_vintage_republication` evidence pairs;
  - 220 `shared_primitive`;
  - 495 B11 total/component or membership
    `structural_formula_sibling`; and
  - 110 taxable-earnings/gross-contribution
    `structural_formula_sibling` rows.

- The complete proven arithmetic registry has 275 exact eleven-field rows,
  all `structural_dependence_only`.
- `exact_arithmetic_sibling` has zero rows. The primary source says displayed
  totals need not equal rounded components at
  [line 15807](data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L15807);
  the source never expressly guarantees displayed-precision equality for any
  candidate rule. The implementation records this rejection instead of
  inferring equality from numerical coincidences.
- Five definition commitments hash exact raw Table 4.B11 HTML cells selected
  after full-source verification. No normalized hard-coded quotation is the
  proof oracle.
- Because the design does not specify whether identical cross-artifact
  occurrences receive one physical ID or two, occurrence IDs are explicitly
  non-authoritative. The design-specified structural locator carries stable
  identity, and final physical/alias getters still abort.

The evidence implementation and field laws begin at
[source-identity builder line 73](scripts/build_covered_earnings_source_identity_evidence.py#L73).

## Finding 4 — coherent corruption and independent registry pins

Disposition: **closed**.

- Legacy artifact validation re-extracts and compares every observation
  against freshly opened, hash-verified source bytes at
  [builder lines 1339–1429](scripts/build_ssa_covered_earnings_calibration_targets.py#L1339).
  A coherently changed token, normalized value, and self-hash is rejected.
- Source-identity validation rebuilds all 945 occurrences, 873 aliases, 275
  rules, and five raw definition commitments before exact comparison at
  [identity builder line 1224](scripts/build_covered_earnings_source_identity_evidence.py#L1224).
- Independent canonical evidence is committed at
  `data/external/covered_earnings_source_identity_evidence_v1.json`:

  - size: `1,515,354` bytes;
  - SHA-256:
    `130fbcbdf1b78c871ac47391f6eaadb1a74f9f3eadcb8827c997f3a6982c8e3b`;
  - encoding: compact sorted-key ASCII JSON with one trailing LF.

- Literal size/SHA pins and canonical-byte checks run before registry
  validation at
  [identity builder lines 68–70 and 1235–1258](scripts/build_covered_earnings_source_identity_evidence.py#L68).
- Tests reject direct byte drift, coherent cell rehashing, coherent raw
  definition-fragment/rule rehashing, locator corruption, and omitted alias
  rows.

## Finding 5 — test tier and parser attacks

Disposition: **closed**.

- The classifier at [tests/conftest.py line 57](tests/conftest.py#L57)
  recognizes committed `data/external` readers and the entry-11 modules that
  read those bytes transitively.
- All 52 final entry-11 tests collect as `artifact`; none collect as `unit`.
- Crafted parser tests at
  [builder tests lines 327–357](tests/test_build_ssa_covered_earnings_calibration_targets.py#L327)
  bypass the outer source hash to exercise parser defense in depth:

  - selected-cell `colspan="2"` collapse;
  - selected-cell `rowspan="2"` collapse;
  - numeric footnote insertion;
  - malformed thousands grouping; and
  - nested-header drift.

All are rejected. Production also rejects any source-byte change before
parsing through the pinned source digest.

## Verification tails

Formatting and lint:

```text
$ black -l 79 <7 changed Python files>
All done! ✨ 🍰 ✨
7 files left unchanged.

$ ruff check --no-cache .
All checks passed!
```

Four-file source/registry suite:

```text
$ PYTHONPATH=src pytest -q \
    tests/test_build_ssa_level_anchors.py \
    tests/test_build_ssa_covered_earnings_calibration_targets.py \
    tests/test_build_covered_earnings_source_identity_evidence.py \
    tests/estimates/test_covered_earnings_correction_registry.py
....................................................................... [ 96%]
...                                                                      [100%]
75 passed in 6.92s
```

Full estimates suite:

```text
$ PYTHONPATH=src pytest -q tests/estimates
........................................... [ 82%]
........................................................................ [ 98%]
.....                                                                    [100%]
437 passed in 26.96s
```

Entry-11 tests:

```text
$ PYTHONPATH=src pytest -q \
    tests/test_build_ssa_covered_earnings_calibration_targets.py \
    tests/test_build_covered_earnings_source_identity_evidence.py \
    tests/estimates/test_covered_earnings_correction_registry.py
....................................................                     [100%]
52 passed in 4.18s
```

Tier collection:

```text
822/3995 tests collected (3173 deselected)
1690/3995 tests collected (2305 deselected)
804/3995 tests collected (3191 deselected)
520/3995 tests collected (3475 deselected)
159/3995 tests collected (3836 deselected)
3995 tests collected
```

The ordered tiers are unit, artifact, integration-PSID, legacy reproduction,
and PolicyEngine oracle. `tests/tier_counts.json` matches these counts.

## Commits and hygiene

Round-2 coherent-step commits before this report:

1. `2c46369` — track progress from the start;
2. `7f2e5bd` — fail closed unresolved vintage-2 authority;
3. `82cd254` — enforce the complete calibration-target schema;
4. `2299a28` — classify artifact tests and add parser attacks;
5. `f5452a8` — repin the full artifact-tier inventory;
6. `d06c77c` — build complete source-identity evidence; and
7. `865894a` — pin canonical registry-evidence bytes.

`git diff --check` and repository-wide Ruff pass. No network data was
captured, no push was performed, and no final/staging vintage-2 identity was
minted.
