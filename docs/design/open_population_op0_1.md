# Open population OP0.1 source, exposure, access and power audit

**Status: draft records, not frozen; held-out years pending the shared registry and Track B’s J. A blinded feasibility and power review comes before any registration. Registrations go to issue #42 only through the coordinator on Max’s go.**

Audit date: 2026-10-24. This is a documentation and exposure audit, not a population estimate, power result or gate registration. It reads no microdata and computes no real-data statistic. Proposed choices and unestablished inputs block freeze; they do not become defaults by appearing here. PSID use follows the project's data-access record.

## Authority and registry boundary

The approved revision-12 design is `5c82dbd9:docs/design/open_population.md`, SHA-256 `964356ad282e86bc1b128b93ec226b38fc3bb9bd6fe8a84162179bd608600154`; its §10 records Max’s revision-11 approval and ruling d1922. Its §3.1, §3.2, §4 and §5.2–§5.4 define these records. Track B design revision 3, §5.1–§5.2 and §7, supplies the audit and power protocol (read 2026-10-24).

The permitted registry snapshot is `daf02425:docs/design/track_b_holdout_registry.json`, SHA-256 `084b8d50ba3c0fe7cf9bd70e3c7c700c60ae682644ead99cca2bb116bfb2ef88`. Its mutation evidence is `daf02425:docs/design/track_b_holdout_registry_mutations.json`, SHA-256 `0be8a0c8be8eb7d014587d7bbb58a2b980374a334ccaedf5cd0e25d588fbfa1f`. These are draft PR #560 bytes, not a merged snapshot.

Only H001–H005 historical uses appear; J has no candidate entry and `complete` is false. The source vocabulary has no ACS PUMS, NCHS natality, Census count/estimate/projection, OACT demographic or CBO projection source yet. Absence does not clear a year. The coordinator must add reviewed source/family definitions, reserve J first, review underlying-data overlaps, append OP candidate entries before freeze, and cite the merged registry by commit and byte hash. Scopes never narrow same-source overlapping years; unresolved relations need symmetric named disclosure; disjoint same-family relations need substantive citations (`daf02425:src/populace_dynamics/track_b/holdout_registry.py:8–44,76–159,396–410,756–804,1033–1078,1105–1171`). This lane edits neither the registry nor Track B code.

## Reading the records

The JSON companion is authoritative for field completeness; this audit states the same drafts for review. `available` means documentation establishes a source/variable, not that data bytes were accessed or a target approved. `validation_only` excludes selection. `not_available` means the requested margin was not established in the inspected release. Every uncaptured target byte hash remains `to capture`. A source’s reachable documentation does not confirm its data file: those checks remain unverified under this lane’s no-data rule.

The common statistical proposal is a simultaneous 95 percent bound with Bonferroni over a frozen cell family, Monte Carlo error below one-tenth of each tolerance, and an inconclusive result for inadequate precision. Survey tolerances use the source design; vital/administrative aggregates use measurement/concept/coverage/vintage allowances; census counts use matching published coverage measurement. No real-data power or tolerance was calculated. The named power procedures below require prospective blinded review and a 0.90 operating-characteristic requirement; effect sizes, cell families and pooling ladders remain proposals until that review.

<!-- records:start -->
