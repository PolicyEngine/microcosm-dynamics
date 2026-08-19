# Amendment 20 Fix-4b report

Date: 2026-08-19
Branch: claude/ce-design-amendment20
Status: **LAWFUL-STOP**

## Change inventory

- §34.4.1 adds `source_underdetermined`, its reconciled-ruling field, the
  authenticated-source standard, and the express prohibition on treating it
  as `no_applicable_purpose`.
- §34.4.2 replaces the unchanged-ontology object with a total completed-
  ontology disposition object. The denominator and both evidence censuses are
  A4 freeze-slots; `U` counts prompts with no lawful completed-ontology
  disposition and must equal zero.
- Calibration law gates authority on reconciled outcomes. Exact-row agreement
  is an alert; macro per-prompt Jaccard ≥90% is diagnostic only.
- §§34.5.3 and 34.6.1 extend the selector, `O_P`, expansion, exact-token joins,
  reverse covers, and rule projections to the completed ontology.
- §34.10 adds four independently rejected malformed-vector groups and repins
  the 14-name mutation domain to 667 bytes / SHA-256
  `e00e567040a3525f0ecf121cacf12c8aeeac90d31b63ad686d18e3ce1ffe9762`.
- §34.11 updates the supersession map to the A4-frozen denominator and
  fourteen-name inventory. §34.12 carries the matching canonical manifest.
- The validator enforces the completed ontology, freeze-slots, ruling and
  nonconflation requirements, selector/`O_P` propagation, and all four new
  mutations. `purpose_totality_alone_passes_r04` remains false.
- The test module adds the completed-ontology contract regression and exact
  14-row mutation pin, increasing the pinned collection from 219 to 220.

## Exact projection

| Field | Value |
|---|---|
| Immutable revision-21 prefix | 4,025,587 bytes / `38139b8ddd24ef7be09e8f149960e8e0b6e39699d84f3783827eff6c294a9ae9` |
| Final design | 4,170,813 bytes / `cb7c96b0b9b2fcf85fd13bf1e7be5de927f2427eb0fb232d45586174018528aa` / blob `5633652debd76805c6a39175bab01b7727f23b1f` |
| Raw / normalized A20 suffix | 145,226 / 145,028 bytes |
| Normalized §34 SHA-256 | `21e8e4bd2753b0ae1a5caf496323725c56fcb537232b60de449bed2a26c1071e` |
| §34.12 canonical manifest | 54,005 bytes / `366011726a0c9543d8118081adfda9eeb6f8d38fa25d51a3c57b8e155bc9a8c8` |

## §34.9.1 implementation pins

| Path | Git blob | Bytes | Raw SHA-256 |
|---|---|---:|---|
| `scripts/validate_amendment13_execution_law.py` | `a980d3883e0b9f970688734483021cc22dccaf5c` | 662,294 | `ea29c2a5f50e113ef427ac12dc3a8988e0e0367ba0ef1da2090159beb20114d4` |
| `tests/test_validate_amendment13_execution_law.py` | `a6f2501f93417e3131d3df36913746fe0dd1b4c7` | 185,060 | `fdea7cd33074a3f20b9e22dc73924c9ec5fb7c8c19de81e9754c6c6263d6e5ed` |
| `scripts/build_amendment13_tier2_repairs.py` | `8e7550ff71cd43f3acd39b7fd1779b6e3a223581` | 111,145 | `2ff0ff39d7ca316fb78c1beb8164300991ea194e803795e642b544bd78b5ef1b` |

## Verification results

| Gate | Result |
|---|---|
| Full pinned battery | PASS — 220/220 in 585.98s; zero failed, skipped, deselected, xfailed, or xpassed |
| Sweeps | PASS — 22 tests |
| Repairs | PASS — 75 tests |
| Replay | PASS — 21 tests |
| Rebuild | PASS — 31 tests |
| Benchmarks | PASS — 10 tests |
| Five-family combined run | PASS — 159/159 in 1,282.90s |
| Repository-established Black, line length 79 | PASS — complete repository |
| Ruff | PASS — complete repository |
| Revision-21 prefix | PASS — exact SHA-256 before and after |
| Suffix shape | PASS — one Amendment-20 boundary, one suffix `\n## `, terminal LF |
| Diff whitespace | PASS |

No byte in `scripts/covered_earnings_correction_registry.py`, `runs/`, or
`gates.yaml` changed. The `FIX4B_*` staging files and all unrelated untracked
files remain outside the commit. No push was performed.
