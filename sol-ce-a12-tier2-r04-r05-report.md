# A12-T2-R04/R05 certification ceremony report

## Plan

| Stage | Planned operation | Disposition |
|---|---|---|
| 0 | Read the governing law and precedent, fingerprint the clean checkout and baseline suite, and resolve the revision binding before implementation. | Executed; first-order law gap found. |
| 1 | Authenticate the complete tier-2 source/build domain and newly derive `tier2_build_input_domain_sha256`. | Not started. |
| 2 | Implement the independent `R04X-7F2A` builder. | Not started. |
| 3 | Implement the independent `R04X-C91D` validator. | Not started. |
| 4 | Publish and validate the fixed-path certification artifact. | Not started. |
| 5 | Implement and execute the enacted mutation census. | Not started. |
| 6 | Rerun the Amendment-11 production gate and require the enacted expected abort. | Not started. |
| 7 | Run final hygiene and verification and finalize the completion report. | Not reached. |

The stages are ordered and fail-closed. Because Stage 0 found two equally
lawful revision-binding readings, this ceremony stops before Stage 1. No
implementation, certificate, mutation, Q5, authority, or R06 output is
created.

## Revision-binding memo

### Operative facts and preserved serialized binding

The tier-2 stage table is now at §26.11.2 in the revision-19 document.
Section 26.11.2(6) limits R04/R05 to two independent source-side
reconstructions of the prospective G17-C01
`hierarchy_annotation_authority` member, followed by raw-byte attestation;
§26.11.2(7) places the Amendment-11 expected abort after those gates.
Section 27.2.3 supplies the exact Git/source/reseal order and retains the
pre-Q5, nonauthority boundary.

Section 29.4.3 fixes an 11-key historical Amendment-15 binding. Sections
30.3.2, 30.3.5, and 31.4, together with the live revision-19 registry,
authenticate these exact values, which both candidate composition readings
would serialize:

| Key | Exact value |
|---|---|
| `amendment_number` | `15` |
| `closure_byte_size` | `842` |
| `closure_path` | `docs/analysis/amendment_15_ratification/closure_v1.json` |
| `closure_raw_sha256` | `f48ac7a42178f79665900540701e75bf3cb066778c9a0b75eae18b0fa774049a` |
| `design_blob_oid` | `50a2a14e1c8845d342dca83559688866e97dc4a7` |
| `design_byte_size` | `3881111` |
| `design_path` | `docs/design/covered_earnings_correction.md` |
| `design_raw_sha256` | `556311b72ec6c8e30eeda4b0f602e0f7f43b9d080c2454966fa3dda3a561d16e` |
| `design_revision` | `17` |
| `ratification_commit` | `c2ffe3e95152ff005485f55acaf75259e6095195` |
| `ratification_commit_sole_parent` | `a352e66284b60997210c634bb427141e7e523a75` |

The six source comparands in §29.4.3 also remain literal and unambiguous:

| Comparand | Exact value |
|---|---|
| `questionnaire_document_count` | `81` |
| `questionnaire_document_keyset_sha256` | `3326c9ba70b7f83f19b0ea934630d26ced73f230be1628cb74031d17160cb1a5` |
| `questionnaire_document_domain_sha256` | `b06139b147391d06b4f90a8f28de472a936ec08b3e9eb37001a5a70e2b3c3543` |
| `source_document_count` | `257` |
| `source_document_keyset_sha256` | `8b7cad855b791c5cd7d235a74d4a0f1ecc7511dc0458db11d6b04c1b6af2c36a` |
| `source_document_domain_sha256` | `9d7a98db7c2889eba150f70935f492aebbc41cd521e4139dc1ec886ecd9945ce` |

The present registry is revision `19`, with the ordered closure domain
`[13,14,15,16,17]`. A direct public call to
`validate_ratification_operativity()` at clean `HEAD` returned exactly that
ordered domain.

### Reading A: fixed historical revision-18 R05 snapshot

This reading follows the R05-specific successor text:

- §30.3.5 says, “For A12-T2-R05 only,” that the public validator first
  validates the complete operative revision-18 A13/A14/A15/A16 snapshot,
  selects Amendment 15 at position 2, and that the enclosing selected
  snapshot is revision 18.
- §30.4.2 separately enacts
  `historical_r05_snapshot_revision = 18`.
- §30.6 says the §29.4.3 selector is “superseded only by §30.3.5” and again
  describes validation of the full operative revision-18 snapshot.

No cited clause qualifies revision 18 as merely initial, descriptive, or
valid only until the next terminal revision.

### Reading B: complete current revision-19 snapshot

This reading follows the revision-general public oracle:

- §30.2.1 defines amendment `N` as revision `N + 2`, derives the closure
  domain as `range(13, R - 1)`, expressly gives revision 19 the five-member
  domain `[13,14,15,16,17]`, and forbids a fixed amendment tuple.
- §30.2.2 requires the public loader to obtain its context only from the
  current registry.
- §30.2.4 requires a selector to validate the complete current domain before
  returning one amendment and says the public loops grow with the registry
  revision.
- §31.2.1 independently fixes the revision-19 expected domain as
  `(13,14,15,16,17)`.
- §§31.1 and 31.5 preserve the general oracle but do not expressly supersede
  or recompose §30.3.5's R05-specific revision-18 selector for revision 19.

This reading validates revision 19 and then selects the unchanged historical
Amendment-15 row at position 2.

### Determination

The two readings are equally supported and require different mandatory
validation executions:

1. authenticate the fixed four-closure revision-18 snapshot; or
2. authenticate the current five-closure revision-19 snapshot.

Specific-over-general treatment favors Reading A. Permanent-generality,
current-registry, and later-state treatment favors Reading B. Section 31
preserves the general oracle but never supersedes or composes §30.3.5's exact
R05 revision-18 commands. Conversely, replaying revision 18 conflicts with
§30.2.2's current-registry-only public path. Validating both snapshots would
invent a third rule with no enacted loading mechanism or order.

The coincidence that both readings serialize the same 11-key A15 binding
does not resolve which mandatory execution proves that binding. Section
30.3.5 also forbids adding a snapshot key to the certificate, so artifact
bytes cannot adjudicate the choice. Under §26.11.2's conjunctive fail-closed
law and the ceremony instruction to stop on equally lawful composition
readings, this is a first-order law gap. Choosing either behavior in builder
or validator code would be an improvised amendment. A successor cure that
changes public-selector behavior would be activation-affecting under
§31.3.1.

A successor amendment must expressly choose one rule: either preserve and
provide an exact public locator for the historical revision-18 R05 snapshot,
or supersede the revision-18 literals and require complete-current-snapshot
validation before historical A15 selection at every later revision.

## Stage 0 — reconnaissance and baseline

### Checkout fingerprint

- Branch: `sol/a12-tier2-r04-r05`.
- Starting `HEAD`: `83df0ef836a74085e5151ffccdcf82cad281de31`.
- Starting tree: `b611367d8330695280bdf7003857187d9ca163b4`.
- Sole parent: `7d5c39619ed71b0c84129ab69e246c564eec91b5`.
- `HEAD...origin/master`: `0 0` after fetch.
- No tracked modification existed before the baseline. The pre-existing
  untracked ceremony-support paths `.ceremony-log/`, `CEREMONY_PROMPT.txt`,
  and `run-ceremony.sh` were preserved and excluded.
- Revision-19 design: mode `100644`, 3,934,849 bytes, Git blob
  `84b31290ecd2d1001b6ea802b9a97a86260cdfda`, raw SHA-256
  `29055c5606a54587107498e8adcdbc8546f93caceabe89238975288db72e7fe1`.
- Amendment-17 closure: mode `100644`, 842 bytes, Git blob
  `ff07eca79e0bd766d9274bb7ff52c7b2d7aa0b51`, raw SHA-256
  `24e2548a77b237ef97aabf6eec63926e3b80daa0759b2dfcb5fe62dc9499987e`.

### Law and precedent read

Read in the required order: the relocated §26.11.2 tier-2 stage law and
§27.2.3; §28; §29 in full, especially §§29.4.1–29.4.7, §29.5, and §29.8;
§30; §31; and the prospective-member scope in §26.11.2(6). The precedent
review included `a352e66`, `scripts/build_amendment13_tier2_repairs.py`, the
current tier-2 directory, the ordered archive ref, and the revision-19
ratification files.

The ordered R03 witness resolves to
`ba4bd4a734dc5ddd835bb7374bf5a37c12a190ae` and preserves the enacted chain
`cbc44fe1642106e1bfecee869de1b9c61f832756` ->
`c6091f06955a3dd8e554f38833fe2eb43e7b08e0` ->
`44c6641aa0ec57036a54e0988a5f18b50a15e50c` ->
`ba4bd4a734dc5ddd835bb7374bf5a37c12a190ae`. The master squash bridge is
`a352e66284b60997210c634bb427141e7e523a75`. If a successor law later permits
this ceremony to resume, §29.3 requires the new topology-bound publication
to retain its ordered commits and use a no-fast-forward merge; no R03 bridge
exception applies to new paths.

### Environment and baseline-suite fingerprint

- Environment command: `uv venv --allow-existing`, followed by
  `uv pip install -e ".[dev]"`. Plain `uv venv` first refused to overwrite
  the existing `.venv`; no environment was deleted.
- Python: `3.14.4`.
- pytest: `9.1.1`.
- Baseline command: `uv run pytest -q`.
- Observed result: **5,540 passed, 91 skipped, 2 failed, 115 warnings** in
  **6,489.98 seconds (1:48:09)**; exit code `1`.
- Failed tests:
  - `tests/test_historical_coverage_legal_sources_reproduction.py::test_staged_112_document_capture_reproduces_committed_audit`
  - `tests/test_historical_coverage_legal_sources_reproduction.py::test_resealed_source_identity_cannot_substitute_for_staged_bytes`
- Both failures terminate in
  `scripts/build_historical_coverage_rule_specs.py::verify_design_binding()`
  with `ValueError: covered-earnings design differs from revision 7`; the
  second test consequently misses its expected `does not reproduce` message.
  These occurred before any tracked ceremony edit and are recorded as the
  baseline fingerprint, not repaired in this stopped ceremony.

Read-only availability probes found the candidate source corpus and committed
repair/seal bytes available. Existing validators and probes reproduced the
six enacted §29.4.3 comparands, 46 repairs, six successor seals, era projection
`[8,5,9,19,5,0]`, and the 81-document targeted sweep with zero unexplained
hits. Those probes are reconnaissance only: no Stage-1 complete build-input
preimage was accepted and no `tier2_build_input_domain_sha256` was derived.

## Stages 1–7 — not executed

- Stage 1: no full-source build domain or new domain digest was produced.
- Stage 2: the `R04X-7F2A` builder path remains uninstantiated.
- Stage 3: the `R04X-C91D` validator path remains uninstantiated.
- Stage 4: the fixed certification artifact remains uninstantiated.
- Stage 5: no new mutation tests or certification census were created.
- Stage 6: the Amendment-11 production gate was not rerun because ordered
  stage law prevents reaching R06 after the Stage-0 stop. The design still
  requires `blocked_source_missing_disposition_underdetermined` when R06 is
  lawfully reached; that result is not claimed as executed here.
- Stage 7: not reached. Only Stage-0 report/cleanup verification is allowed.

## STATUS

**LAWFUL-STOP**

Blocking condition: unresolved first-order conflict between §30.3.5/§30.6's
fixed revision-18 R05 snapshot and §§30.2.1–30.2.4/§31.2.1's complete current
revision-19 public snapshot. No implementation workaround is lawful.

No ceremony-resumption command is lawful until a successor amendment resolves
that conflict and its registry repin is operative. After that merge, the next
command is:

```sh
git fetch origin --prune
```

Then begin again at Stage 0 in a fresh worktree from the updated
`origin/master`.
