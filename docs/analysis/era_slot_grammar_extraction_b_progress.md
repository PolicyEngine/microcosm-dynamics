# Era slot/grammar extraction B progress

## State

- Branch: `claude/ce-era-extraction-b`
- Scope: questionnaire-slot and absence-domain extraction for 1979-2001,
  plus fixed-width grammar rows 10 and 13.
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
- Identified the exact revision-7 Class-A and Class-B laws and inventory
  residual indices 10, 11, 13, and 14.
- Reproduced both committed codebook-era evidence artifacts byte-for-byte
  from the staged dictionary/codebook bytes and reproduced the registered
  questionnaire extraction in `--check` mode.
- Confirmed section 19.3.3 ratifies only
  `data/external/psid_questionnaire_slot_closure_evidence_v1.json`, whose
  exact domain is six era rows, all 43 waves, all 257 source documents, and a
  global questionnaire relationship catalog derived from all 81
  questionnaire-flow documents. There is no ratified per-era artifact schema
  or status.
- Reproduced the target questionnaire denominator with the pinned Poppler
  26.04.0 page derivation: 1979-1993 has 29 authenticated questionnaire/QxQ
  documents and 3,349 pages; 1994-2001 has 12 documents and 1,622 pages.
  Together with the 84 target field-source documents, the target slice has
  125 documents and 4,971 questionnaire pages, but it is not the global
  denominator.
- Reframed every target raw family file exactly. The 1979-1993 files contain
  113,917 terminal-CRLF fixed-width records and 15,745 fields; the 1994-2001
  files contain 50,826 records and 15,983 fields. Complete all-field censuses
  therefore cover 124,186,050 and 131,460,072 raw field observations.
- Confirmed the source evidence contains 14,180 fields and 28,211 rows with
  explicit missing meanings in 1979-1993, and 15,517 fields and 40,372 such
  rows in 1994-2001. No v3 grammar row is currently resolved.
- Found hard section 19.3.2 failures that prevent a passing source
  derivation. The 9,226 and 10,563 `NUM(1.0)` fields cannot produce the
  mandatory positive shorter-value padding diagnostic. Separately, 484 and
  1,052 decimal fields retain unequal nonnull SPSS `F<w>.<d>` and codebook
  `NUM(w.d)` declarations, which the byte-exact agreement law classifies as
  conflicting even when their numeric tuples agree. The two sets are
  disjoint, so at least 9,710 and 11,615 fields are hard failures; all 15,745
  and 15,983 remain unresolved without the absent global v3 derivation.
- Did not first-add a partial Q5 path, invent an unratified shard schema,
  claim an absence over a local instead of global hierarchy, or relabel a
  hard grammar failure as the closed-unobserved-value branch.

## Next

- Ratify a contribution schema and an assembly law if separately committed
  era fragments are desired, or assign one coordinated lane the complete
  six-era Q5 construction so that global `R_Q`, `H`, positive-field joins,
  and canonical absence proofs have their lawful denominators.
- Amend or disposition the v3 grammar conflicts before a global
  `field_source_derivation.status: pass` is possible, including the
  nondiagnostic width-one fields and byte-unequal `F<w>.<d>`/`NUM(w.d)`
  declarations without weakening the authenticated V93 space-padding replay.
- After those prerequisites are ratified, restart extraction from the pinned
  source bytes. Until then, inventory blockers 10, 11, 13, and 14 all survive.
