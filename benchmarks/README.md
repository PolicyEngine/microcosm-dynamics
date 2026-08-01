# Standing benchmark harness

This directory is the append-mostly public progress tracker for cross-model
validation. The registry defines what may be compared; history records what a
specific immutable evaluation produced; and the generated wall presents the
latest record for every row. Large gaps are allowed. Unexplained gaps are not.

The numerical comparison rows from the merged `analysis/validation-matrix/`
lane were normalized for the standing harness. Their exact legacy scopes,
row-specific published metadata, and omitted matrix context are retained so the
merged matrix can be reconstructed losslessly. Superseded presentation artifacts
and shims were removed. The original offline source-capture request is retained
as [SOURCES-NEEDED.md](SOURCES-NEEDED.md).

## Artifacts

- [registry.json](registry.json) contains one specification per `row_id`,
  immutable source pins and exact locators, model-side artifact pointers,
  comparison scope, verification status, primary gap law, and a preserved
  `spec_revisions` changelog. Its schema-validated `migration_context` preserves
  the merged matrix's context blocks and source identity.
- [history.jsonl](history.jsonl) is append-only. Each line is one compact,
  sorted-key canonical JSON object for one row evaluation.
- [run_manifest.jsonl](run_manifest.jsonl) is append-only. It maps each
  `evaluated_at_run` SHA to one normalized repository-relative immutable
  evaluation artifact.
- [wall.md](wall.md) is the publishable generated view. It has no external
  assets or external links.
- `build_registry.py`, `build_history.py`, and `build_wall.py` reproduce-check
  generated artifacts. `append_history.py` validates and appends one complete
  future record set plus its run-manifest entry.
- `schema.py` is the fail-closed schema and alarm-law validator.

`registry.json` is append-mostly. Add new entries; do not silently repurpose an
existing `row_id`. If an existing specification's source pin or exact locator
changes, append a nonempty object to that entry's `spec_revisions` with
sequential `revision`, JSON-Pointer `changed_fields` that cover every actual
specification diff, and a one-sentence `note`. New rows are appended after all
existing rows regardless of tier, are appended to `REGISTRY_ROW_ORDER` in the
builder, and start with no revisions. Never erase an earlier revision note.

## Tiers

`admin_truth` contains published SSA, Trustees, IRS, or Census administrative
statistics. Its gaps are errors expected to shrink over evaluation runs.

`model_triangulation` contains DYNASIM, MINT, CBO, and other actuarial-model
comparisons. Its gaps are informative, never normative. A model-triangulation
row is never a target and is never “fixed toward.”

`statutory_parameter` contains small, direct identities from enacted or
proposed statutory text. A copied parameter can test implementation coverage,
but zero deviation is not independent validation.

## Validation-only law

Benchmark specifications, published values, evaluated values, deviations, gap
classes, notes, trends, and wall presentation are validation-only. They may
never inform model construction, parameter estimation, calibration targets,
priors, candidate or seed selection, loss functions, thresholds, tolerance
adjudication, or rescue decisions. The information boundary applies before,
during, and after a run.

This law anchors to the design's
[fitting and candidate-selection law](../docs/design/covered_earnings_correction.md#7-fitting-and-candidate-selection-law),
[strict pre-registration and fixture-only rehearsal doctrine](../docs/design/covered_earnings_correction.md#101-strict-registration-fixture-only-rehearsal-and-frozen-identities),
[closed context-domain doctrine](../docs/design/covered_earnings_correction.md#1672-adjudication-of-the-ten-no-fitting-loss-families),
and [fitting-free context law](../docs/design/covered_earnings_correction.md#1674-fitting-free-context-and-conditions-89).
The wall's label preamble is anchored to the
[exact evidentiary labels](../docs/design/covered_earnings_correction.md#1671-exact-evidentiary-labels).

## Gap law

Every history record must have exactly one `gap_class` from this closed enum:

```text
label_mismatch
frame_no_alignment
concept_mismatch
module_missing
small_cell
preliminary_source
unverified_source
unexplained
```

It must also carry a nonempty, one-sentence `gap_note`. The alarm law is
absolute: any evaluated `unexplained` row or any missing/blank note fails the
harness. Each row retains its complete mismatch-code ledger in the registry;
the singular history class identifies the primary blocker. Source authority
takes precedence for the 20 Mermin rows, which are `unverified_source` and
retain `verification_class: reported_not_verified`. `preliminary_source` is
reserved for accepted, provenance-pinned publisher data explicitly marked
preliminary. The five SSA rows containing preliminary 2021-2022 observations
have other primary gap classes. Favreault population differences are primarily
`concept_mismatch`; its disclosed small cells remain secondary facts.

All eight classes, including zero-count classes, appear in the wall's gap
ledger with their closure conditions.

## Seed record set

The first 42 history lines reproduce the migrated evaluation associated with
`runs/first_estimates_v1.json`, SHA-256
`719604ca4364e7cdef2293329ed0beb0e011e5d4d1c34f0e508c8f2fd9932977`.
That artifact explicitly creates no production certification or verdict. In
the seed, `evaluated_at_run` is the required immutable run-set identity; it
does not transfer certification to the anchor-context and replication
artifacts that supply individual row values.

The first run-manifest line permanently maps that identity to
`runs/first_estimates_v1.json`. Every committed check confines each manifested
path to the repository, requires it to be tracked with checkout bytes matching
the Git index, and hashes those bytes back to `evaluated_at_run`.

The permanent reproduction pin covers exactly the first 42 canonical lines,
not the whole growing file. `build_history.py --check` verifies that frozen
prefix independently of the current registry and never writes history. A
separate committed-history check requires every prior history byte to remain
the exact prefix of the current file.

## Append protocol

For every future evaluation run:

1. Prepare any new registry entries first. For an existing specification
   change, preserve the old specification history through a new
   `spec_revisions` note. Commit the registry, evaluation artifact,
   run-manifest entry, history append, and regenerated wall together so the
   harness never lands between states.
2. Produce the immutable evaluation artifact inside the repository, stage its
   final bytes, and compute its SHA-256. The append checker rejects missing,
   untracked, modified, or path-escaping artifacts.
   A run SHA may appear in only one record set and may never be reused.
3. Evaluate every active registry entry, in registry order, using the exact
   registry bytes whose SHA-256 becomes `registry_sha`. The evaluator is
   responsible for deriving and reviewing the candidate values from the
   immutable artifact; the append tool checks identities and invariants but is
   not a model evaluator.
4. Emit one canonical JSONL object per row with exactly `evaluated_at_run`,
   `registry_sha`, `row_id`, `our`, `published`, `deviation`, `gap_class`,
   `gap_note`, and `label_state`. Units, gap class, and gap note must match the
   registry. Under an unchanged registry, published values are immutable.
   Encode with UTF-8, sorted keys, compact separators, ASCII escapes, finite
   numbers only, and one trailing LF per object.
5. Validate the candidate set, then append it as one contiguous byte block:

   ```sh
   python benchmarks/append_history.py candidate.jsonl \
     --run-artifact runs/evaluation.json --check
   python benchmarks/append_history.py candidate.jsonl \
     --run-artifact runs/evaluation.json --append
   ```

6. Never edit, replace, reorder, or truncate an existing history or run-manifest
   byte. A row's deviation moving without a new `evaluated_at_run` SHA is a
   drift finding by law; the append validator rejects every reused run SHA.
   The supplied artifact's bytes must hash to `evaluated_at_run`. Appends
   revalidate under exclusive locks and append the manifest line and complete
   canonical history set with in-process rollback on failure.
7. Regenerate `wall.md`, run all checks, and commit the history append and wall
   together. The first evaluation for a row has trend `n/a`; later movement is
   labeled neutrally as `changed` or `unchanged` unless a separate directional
   law was pre-registered.

## Reproduction checks

All builders are offline and read only committed repository bytes:

```sh
python benchmarks/build_registry.py --check
python benchmarks/build_history.py --check
python benchmarks/build_wall.py --check
pytest -q tests/test_benchmarks.py
```

Run `build_registry.py` or `build_wall.py` without `--check` only to regenerate
their respective canonical output after an intentional input change.
