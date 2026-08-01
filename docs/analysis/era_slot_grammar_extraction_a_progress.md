# Era slot/grammar extraction A progress

## State

- Branch: `claude/ce-era-extraction-a`
- Scope: questionnaire-slot and absence-domain extraction for 1968-1978,
  plus fixed-width grammar rows 0 and 4.
- Status: stopped fail-closed before artifact creation. Section 19 ratifies no
  standalone per-era authority, and the requested two-era domain cannot
  satisfy the global closure or grammar pass laws.

## Done

- Verified `covered_earnings_correction_registry.design_binding()` returns
  revision 7, ratification commit `985be84fdeec70ffd20aa1e60dec7d300b7a555b`,
  and design SHA-256
  `8f90dd1aee59e6857418d2a73b617e5cb3991eba3a237a78303586a8c2a9debc`.
- Confirmed the worktree did not contain forbidden root `PROGRESS.md` or
  `FINAL_REPORT.md` files before work began.
- Reproduced the exact residual predicates for Class-A indices 1, 2, and 5
  and Class-B indices 0 and 4 from the pinned adjudication artifact.
- Confirmed section 19.3.3 ratifies only
  `data/external/psid_questionnaire_slot_closure_evidence_v1.json`, whose
  exact domain is six era rows, all 43 waves, all 257 source documents, and a
  global questionnaire relationship catalog derived from all 81
  questionnaire-flow documents. There is no ratified per-era artifact schema
  or status.
- Confirmed the requested two eras cover 22 authenticated questionnaire/QxQ
  documents and 1,250 extracted pages, but their exhaustive hierarchy is not
  independently defined: `H = W x 2 roles x R_Q`, where `R_Q` is the global
  43-wave catalog.
- Reframed every 1968-1978 raw family file exactly. The 11 files contain
  58,357 CRLF-terminated fixed-width records and 5,706 fields (3,868 early;
  1,838 seam), matching the pinned residual denominators.
- Reproduced the V93 census: 4,802 width-771 records, with 1,069
  ASCII-space-padded one-digit V93 observations and no zero-padded one-digit
  observations.
- Found closed grammar conflicts that section 19.3.2 says prevent a passing
  source derivation: 3,783 `NUM(1.0)` fields have no possible shorter-value
  arm diagnostic; all 239 `NUM(w.d)` fields with `d > 0` contain a literal
  decimal point although the v3 payload language forbids it; and signed raw
  observations occur although the v3 constructor is unsigned-only. The
  existing evidence also records zero SPSS `MISSING VALUES` declarations.
- Did not create a partial Q5 file, invent an unratified era schema, claim an
  absence over a local instead of global hierarchy, or relabel the grammar
  conflicts as resolved.

## Next

- Ratify a contribution schema and an assembly law if separately committed
  era fragments are desired, or assign one coordinated lane the complete
  six-era Q5 construction so that `R_Q`, `H`, and every absence proof have
  their lawful global denominator.
- Amend or disposition the v3 grammar conflicts before any Q5 artifact can
  have `field_source_derivation.status: pass`. In particular, specify lawful
  treatments for nondiagnostic width-one fields, literal-decimal payloads,
  and signed payloads without weakening the authenticated V93 space-padding
  replay.
- After those prerequisites are ratified, restart extraction from the pinned
  source bytes. Until then, inventory blockers 0, 1, 2, 4, and 5 all survive.
