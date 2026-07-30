# Amendment 2, round 6 final report

## Outcome

All four round-5 critical findings are closed, the capture-success
serialization now completes uniquely through all nine steps, and the
mandatory §16 closure sweep passes.

1. **V-B verification results — PASS.** Section 16.12.1 names and freezes the
   adjudication source identity, result/spec envelopes, committed-byte source
   projection, expected/actual preimages, verifier, successor methodology
   manifests, role maps, noncapture predicate, cutoff identity, and
   applicability bundle. V-B5, V-B6, and V-B8 derive faithful negative rows
   from the pinned adjudication bytes. A producer-asserted `verified/pass`
   result cannot construct the expected value.
2. **Runner-node binding — PASS.** Section 16.12.2 freezes the runner/root
   equality and Python symbol-locator projection. For both roots, the runner
   node's principal, repository path, implementation digest, symbol locator,
   callable entrypoint, and root edge are exact equations over the same root
   identity.
3. **Expected A1 reconstruction — PASS.** Section 16.12.3 freezes the complete
   canonical A1 semantic object, including `selector_id` and all seven rule
   members, and independently reconstructs its input domain and support
   keyset from authorization, sidecar-bound Git bytes, and a fresh selector
   execution. The primary is only the actual comparand.
4. **Namespace parent and output version — PASS.** Section 16.12.4 makes
   \(J\), the unique parent of the candidate receipt/configuration commit,
   the sole `git_parent`; overrides the stale authority-cutoff-parent
   interpretation; freezes the complete history projection; gives
   `newly_ratified_output_version_required` its exact path/schema/member and
   generation/version predicate; and closes the receipt/configuration/
   namespace/claim equality.

## Re-walked nine-step capture-success serialization

1. Freeze the preliminary four-key design; source-v1, methodology-v3,
   claim-role-v1, role-v3, family-v1, noncapture-predicate-v2, and
   capture-predicate-v1 registries; the committed verification-claim
   projection; repository commit; and derived UTC. Construct and hash the
   complete v2 cutoff identity.
2. Construct source-v1 and methodology-v3 manifests with authenticated
   negative V-B rows, lawful preliminary A1/A3 legacy negatives, and all
   other typed authority results. Populate the full cutoff and unique
   preliminary adjudication \(P_n\).
3. Exact-bind \(P_n\) in the committed authorization, derive the unique
   accepted capture-triple commit \(T\) from raw ancestry, and revalidate its
   authorization/claim/primary/sidecar quartet at final cutoff \(C\).
4. Freeze the same design; source-v2, methodology-v4 with the exact
   four-projection A1 row, claim-role-v1, role-v4, family-v1,
   noncapture-predicate-v2, and capture-predicate-v1 registries; \(C\); and
   final UTC. Construct and hash the final v2 cutoff identity.
5. Construct the single expected A1 from the ratified semantic object,
   authorization, sidecar-bound Git bytes, independent selector execution,
   \(T\), and descriptor closure. Independently reconstruct A3 from its
   unique sidecar descriptor. Only then parse the primary comparands and
   append the typed A1/A3 final-manifest rows.
6. Hash the complete source-v2 and methodology-v4 manifests, populate the
   full final cutoff, and expand the exact role-v4 map. Every hash consumer
   now has its complete preimage.
7. Serialize the complete A1/A3 aggregation preimages/results and every
   remaining noncapture required-authority row from authenticated manifest
   projections. No required-authority row is producer-sourced.
8. Serialize only contiguous adjudication vintage \(n+1\) under the unique
   single-parent first-add and immutable-lineage law.
9. Bind that adjudication, the complete v2 applicability registry bundle,
   and every same-cutoff identity in the receipt before namespace or path
   derivation.

All nine steps have one reachable canonical serialization. A missing,
duplicate, mismatched, primary-only, or nonreconstructible input aborts
before final adjudication.

## Mandatory closure sweep

The normative appendix uses a conservative mechanical grammar over §16
backticked atoms and strict-JSON string leaves, subtracts exact pre-§16
atoms, and sorts by unsigned UTF-8 bytes.

- Token count: **618**
- Table rows: **618**
- Unique rows: **618**
- Set equality and byte order: **PASS**
- Real-definition anchors: **PASS**

The sweep found 15 underfrozen projection tokens and fixed all 15 before the
table:

- `coordinator:claim_authority_inventory_closure/0`
- `coordinator:claim_authority_inventory_closure/1`
- `coordinator:claim_authority_inventory_closure/2`
- `coordinator:claim_authority_inventory_closure/3`
- `coordinator:claim_authority_inventory_closure/4`
- `coordinator:claim_authority_inventory_closure/5`
- `coordinator:claim_authority_inventory_closure/7`
- `coordinator:claim_authority_inventory_closure/8`
- `coordinator:calibration_target_specs_resolved_source_projection`
- `coordinator:strict_parsed_inventory_identity`
- `coordinator:strict_parsed_crosswalk_identity`
- `live_prebranch:interpreter_lock_and_package_graph`
- `live_prebranch:interpreter_and_package_graph`
- `live_prebranch:descriptor_lstat_namespace_absence`
- `live_prebranch:descriptor_lstat_namespace_absence_rows`

The eight claim-closure projections now equal authenticated fitting-free
adjudication rows. The remaining seven now have exact canonical target,
strict-parse, environment-graph, or namespace-scan value schemas and hash
equations. No swept token remains undefined.

## Validation

- Requested branch and append-only lineage preserved from
  `f8e4bde8768bceb137dfe8900b65e4a599398bb7`.
- Round-6 design delta: 1,660 additions, zero deletions.
- Immutable 579,090-byte prefix SHA-256:
  `f882ea1d67a6d4991838d7b3a40120347d4b1cbb882de796f5d42be1acb40cd7`.
- Final design length: 19,612 lines; SHA-256
  `6e3397901475fc66d2e2d69bd0f2dc72598d63afeb7e6211b9af0f74a8e4aeb7`.
- All 53 §16 JSON fences strict-parse with duplicate-key rejection.
- `git diff --check`: PASS.
- `tests/test_forecast_ledger.py`: 5 passed.
- The full `pytest -q` collection is unavailable in this checkout's current
  environment: 73 modules fail collection because the
  `populace_dynamics` package is not installed. No test reached a
  round-6 document assertion before that environment failure.
- No push performed.

The four finding commits preceding the final sweep commit are `a20a6ff`,
`c8ce646`, `4bdde43`, and `96e7cad`; `27d67e2` started the committed progress
ledger. This report, the completed progress ledger, and the closure appendix
are part of the final sweep commit.
