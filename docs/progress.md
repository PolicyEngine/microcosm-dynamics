<!-- GENERATED FILE - DO NOT EDIT. Edit docs/progress/progress.json and run scripts/build_progress_page.py -->

# Development progress

*Snapshot as of 2026-08-30T13:30:00Z (UTC); updated at least daily while the evidence campaign is active. The data behind this page is committed at [`docs/progress/progress.json`](progress/progress.json).*

Dynamics builds Social Security earnings histories from the PSID, and the corrected covered-earnings series is only as credible as the reading of the source documentation beneath it. Before that series ships, every piece of documentation the construction relies on is independently verified by the three arms below; the design is pre-registered and ratifies only when they complete. (Internally: the evidence campaign behind Amendment 20 (two-arm evidence charter for the covered-earnings correction design), under review in PR #405, open; draft ratified through round 6.2; next step, the A4 evidence freeze, then the C20 ratification chain toward revision 22.)

## Already built

The foundations below are complete and in the repository today; the campaign tracked on this page is the verification layer on top of them.

- [The Dynamics paper: the full design, the benchmark comparison against DYNASIM, MINT, and CBOLT, and the evaluation plan.](https://microcosm.institute/dynamics/paper)
- [The population-view scoring harness: geometry blocks, trajectory windows, and the moment battery that scores candidate models.](https://github.com/PolicyEngine/microcosm-dynamics/tree/master/src/populace_dynamics/harness)
- [Label-verified PSID readers building the 1968–2022 head/spouse earnings panel, plus the demographic and earnings data modules around it.](https://github.com/PolicyEngine/microcosm-dynamics/tree/master/src/populace_dynamics/data)
- [A statutory Social Security benefit oracle (AIME/PIA) whose parameters load from PolicyEngine-US.](https://github.com/PolicyEngine/microcosm-dynamics/tree/master/src/populace_dynamics/ss)
- [A locked, pre-registered evaluation contract: gate-1 thresholds are ratified and change only through public amendment plus a fresh referee round.](https://github.com/PolicyEngine/microcosm-dynamics/blob/master/gates.yaml)
- [145 committed evidence artifacts — noise floors, gate runs, sensitivities — each pinned by reproduction tests.](https://github.com/PolicyEngine/microcosm-dynamics/tree/master/runs)
- [The covered-earnings correction design itself, advanced through adversarial referee review to registry revision 21, with Amendment 20 in the ceremony pipeline.](https://github.com/PolicyEngine/microcosm-dynamics/pull/405)
- [A public timeline-forecast ledger: 21 registered entries, every revision with its reasons on the record.](https://github.com/PolicyEngine/microcosm-dynamics/blob/master/docs/forecasts/timeline_ledger.json)

## Verification arms


<div style="margin: 1.1em 0 1.4em 0;">
  <div style="display: flex; justify-content: space-between;
              align-items: baseline;">
    <strong>Prompt-purpose census</strong>
    <span style="font-variant-numeric: tabular-nums;">
      11,576 / 20,815 &middot; 55.6%</span>
  </div>
  <div style="background: #e9ecef; border-radius: 6px; height: 14px;
              margin: 0.35em 0;">
    <div style="background: #2c6496; border-radius: 6px; height: 14px;
                width: 55.6%;"></div>
  </div>
  <div style="font-size: 0.9em; color: #555;">prompts adopted (contiguous R1–R11576).
  Establishing what each of the ~21,000 remaining items in the PSID's 1968–2023 questionnaires and codebooks is actually asking, so the model only uses variables whose meaning has been adjudicated rather than assumed. Each block runs a full pass, an independent dense audit, and a correction sweep before its entries are adopted into the governing ledger.</div>
</div>


<div style="margin: 1.1em 0 1.4em 0;">
  <div style="display: flex; justify-content: space-between;
              align-items: baseline;">
    <strong>A3 classification arm</strong>
    <span style="font-variant-numeric: tabular-nums;">
      35,200 / 41,103 &middot; 85.6%</span>
  </div>
  <div style="background: #e9ecef; border-radius: 6px; height: 14px;
              margin: 0.35em 0;">
    <div style="background: #2c6496; border-radius: 6px; height: 14px;
                width: 85.6%;"></div>
  </div>
  <div style="font-size: 0.9em; color: #555;">queue rows final-adopted.
  Deciding how zeros and missing readings in the source data should be interpreted — a true zero, a question that was never asked, or an inapplicable route — across a 41,103-row queue of PSID variable readings, in 800-row blocks with 20% independent audits and correction sweeps.</div>
</div>


<div style="margin: 1.1em 0 1.4em 0;">
  <div style="display: flex; justify-content: space-between;
              align-items: baseline;">
    <strong>Q5 semantic annotation</strong>
    <span style="font-variant-numeric: tabular-nums;">
      33 / 257 &middot; 12.8%</span>
  </div>
  <div style="background: #e9ecef; border-radius: 6px; height: 14px;
              margin: 0.35em 0;">
    <div style="background: #2c6496; border-radius: 6px; height: 14px;
                width: 12.8%;"></div>
  </div>
  <div style="font-size: 0.9em; color: #555;">documents sealed.
  Verifying which survey questions connect to which data fields, document by document across the PSID questionnaire corpus: two independent annotators per document, then a reconciliation that seals its table of record.</div>
</div>

## Inside the numbers

The three drill-down tables below decompose each arm's progress bar row by row. Every row was extracted from the campaign's evidence archive and independently re-verified against the artifact named in its source column.

### Purpose census, document by document

*What one unit is*: One rank = one row of the pinned 20,815-row residual index (e8-ops/sol-ce-purpose-residual-index-v1.txt, file SHA b35519702e6f...) = one prompt occurrence keyed `psid-questionnaire-occurrence:<sha256>` — a single printed questionnaire item in a sealed official PSID questionnaire/QxQ-codebook PDF (staged under ~/PolicyEngine/psid-data/documentation/capture1), located by an exact page/character-span receipt, e.g. `q88:p4[2538,2708)#10bc6b307d41`. What is adjudicated per rank is the prompt's "purpose": per sol-ce-purpose-evidence-scope-report.md, purpose "is the closed model-law classification saying which factual dimension a `field_purpose_prompt` establishes for `O_P`" — not survey designers' motivation. Each rank is disposed either D (determined: an ordered purpose array over the closed 35-literal space, e.g. `[M]`) or SU (source-underdetermined, with a named condition such as U_ONTOLOGY, U_CONFLICT, or U_SCOPE). Example full row from sol-ce-purpose-ledger-pass-R6172-6576-report.md: "R6176 | Q7316 | psid-questionnaire-occurrence:091095d3... | E3.CALENDAR_EXPOSURE | D | [M] | q88:p4[2538,2708)#10bc6b307d41". Documents are the per-wave PSID instruments: f-docs are family-interview QxQ codebooks (e.g. f94 = fam1994_QxQs.pdf) and q-docs are questionnaires (e.g. q94 = q94.pdf, "1994 Questionnaire", per the e4-era build's source table).

*Why the denominator is 20,815*: 20,815 = 21,971 − 1,156. sol-ce-purpose-residual-index-v2-report.md states the domain law verbatim: "The domain law yields **20,815**, not 20,809: E ⊂ D; |C − D − E| = 21,971 − 1,156 = 20,815", where C is the canonical corpus (sol-ce-purpose-residual-index-report.md: "The canonical corpus contains 21,971 prompts. Subtracting the same IDs yields **20,815**") and the 1,156 is the already dual-covered calibration relation from sol-ce-purpose-grand-reconcile-report.md ("Unique dual-covered prompts: 1,156" = production ranks 1–1,130 plus 26 unique rubric-sample rows; the six calibration-only exclusions are inside those 26). So the artifacts state the relation to 21,971 directly: 21,971 canonical prompts = 1,156 dual-covered in the pre-census calibration phase + 20,815 residual ranks R1–R20815 that the census adjudicates. The index was pinned 2026-08-23 (board: "PURPOSE RESIDUAL INDEX PINNED: e8-ops/sol-ce-purpose-residual-index-v1.txt (20,815 rows; R-Q SHA 858a5aa9; file SHA b35519702e6f2e2a2541c25f62878d0125f86c31b383fbc681b5369d0c272c90)"). Distinct nearby numbers, per the same artifacts: 21,099 is the established-Q `fail_closed_no_rule` queue (an earlier Q namespace; "Subtracting 1,156 yields **19,943** rows, not approximately 20,815" — that derivation was explicitly rejected in favor of the canonical 21,971 ordinal), and 21,153 is the evidence-scope report's "operative burden" of underdetermined prompts. Board percentage milestones are rank_end/20,815 (e.g. R11260/20,815 = 54.10%, matching "contiguous R1–R11260 = 54.10%").

| Document | Ranks | Count | Status | Dispositions | Audit | Adopted |
|---|---|---|---|---|---|---|
| early blocks R1-R4350 (aggregate: pilot rounds r1-r6 + pre-index production blocks + 452-rank gap block, re-keyed to the pinned index) | R1–R4,350 | 4,350 | adopted | 3,898 re-keyed rulings = 3,487 D / 411 SU; plus 452 gap-block rulings (D/SU split not stated) | coverage audit vs the pinned index: 0 duplicates, 452 gaps in R1-R4350 -> gap block dispatched; gap block reconciled 83.6% | 2026-08-23 |
| block R4351-R4650 | R4,351–R4,650 | 300 | adopted | — | reconciled 270/300 = 90.000% (below cal-3 reference 93.333%); adopted as table of record under the explicit policy change | 2026-08-23 |
| block R4651-R4950 | R4,651–R4,950 | 300 | adopted | — | reconciled 260/300 = 86.667% (24 application failures + 16 coverage gaps) -> triggered stop-and-diagnose | 2026-08-23 |
| block R4951-R5250 (f87 opening, families B-D) | R4,951–R5,250 | 300 | adopted | — | reconciled 264/300 = 88.000% RECALIBRATE - the last dual-pass block, folded as coverage data | 2026-08-23 |
| block R5251-R5550 (f87 close + q87 open; first ledger-first calibration block) | R5,251–R5,550 | 300 | adopted | 300 = 294 D / 6 SU (corrected block final, 31 corrections) | 82/99 = 82.83% NOT CALIBRATED (ledger-first calibration) -> corrected via sweep; adopted at the v1.8 fold | 2026-08-24 |
| block R5551-R5614 (q87 completion) | R5,551–R5,614 | 64 | adopted | 64/64 (61 executable + 3 UNCOVERED proposals), 0 SU | dense re-calibration audit CALIBRATED 28/28 = 100% (zero contradictions) | 2026-08-24 |
| f88 | R5,615–R6,171 | 557 | adopted | 557 = 484 D / 73 SU (sum of corrected block finals: R5615-5914 = 256 D / 44 SU; R5915-6171 = 228 D / 29 SU) | R5915-6171 audit 93/100 = 93.00% NOT CALIBRATED (family-concentrated); R5615-5914 audit NOT CALIBRATED -> both blocks sweep-corrected; adopted at the v1.10 fold | 2026-08-24 |
| q88 | R6,172–R6,632 | 461 | adopted | 461 = 440 D / 21 SU (sum: R6172-6576 corrected final 405 = 391 D / 14 SU; tail R6577-6632 = 49 D / 7 SU) | R6172-6576 audit 87/92 = 94.57% NOT CALIBRATED (family-concentrated) -> corrected (75 corrections); tail audit CALIBRATED 28/28 = 100%; adopted at the v1.12 fold | 2026-08-25 |
| f89 | R6,633–R7,210 | 578 | adopted | opener R6633-6903 corrected final 271 = 233 D / 38 SU; block-2 R6904-7210 pass census 307 = 259 D / 48 SU, adopted with the single R7041 -> U_CONFLICT correction | opener audit 118/150 = 78.67% NOT CALIBRATED -> corrected (118 corrections); block-2 CALIBRATED 99.32% (145/146) | 2026-08-25 |
| q89 | R7,211–R7,558 | 348 | adopted | 348 = 313 D / 35 SU (corrected block final; 60 routing-only + 10 semantic+routing corrections) | 113/123 = 91.87% NOT CALIBRATED -> corrected; adopted at the v1.18 fold | 2026-08-25 |
| f90 | R7,559–R8,084 | 526 | adopted | opener R7559-7820 corrected 262 = 229 D / 33 SU; block-2 R7821-8084 = 225 D / 39 SU (sum 454 D / 72 SU) | opener audit 116/121 = 95.87% NOT CALIBRATED (family-concentrated) -> corrected; block-2 CALIBRATED 99.08% | 2026-08-26 |
| q90 | R8,085–R8,552 | 468 | adopted | B+C R8085-8295 corrected census 211 = 173 D / 38 SU; D-M R8296-8552 corrected 257 = 182 D / 75 SU (sum 355 D / 113 SU) | B+C dual audits split -> geometry adjudication CALIBRATED 85/86 = 98.84%; D-M corrected under the geometry law | 2026-08-26 |
| f91 | R8,553–R8,974 | 422 | adopted | 422 = 368 D / 54 SU (corrected final; 28 sealed semantic corrections) | 166/194 = 85.57% NOT CALIBRATED -> corrected; adopted at the v1.26 fold | 2026-08-28 |
| q91 | R8,975–R9,571 | 597 | adopted | opener R8975-9245 corrected 271 = 261 D / 10 SU; block-3 R9246-9571 corrected 326 = 311 D / 15 SU (sum 572 D / 25 SU) | opener audit 85/90 = 94.44% NOT CALIBRATED (concentrated defects); block-3 audit 96.55% NOT CALIBRATED (transition-date family) -> both corrected | 2026-08-28 |
| f92 | R9,572–R9,795 | 224 | adopted | 224 = 193 D / 31 SU (corrected final; sweep found 12 contradictions, 4 beyond the audit) | 100/108 = 92.59% NOT CALIBRATED -> corrected; adopted at the v1.32 fold | 2026-08-28 |
| q92 | R9,796–R10,217 | 422 | adopted | 422 = 405 D / 17 SU (corrected final; UNCOVERED=0) | 140/145 = 96.55% numeric pass but all six SEE-router checkpoint rows misruled -> NOT CALIBRATED -> corrected; adopted at the v1.33 fold | 2026-08-28 |
| q93 | R10,218–R10,749 | 532 | adopted | opener R10218-10457 corrected 240 = 222 D / 18 SU; block-7 R10458-10749 corrected 292 = 269 D / 23 SU (sum 491 D / 41 SU) | opener audit 79/89 = 88.76% NOT CALIBRATED; block-7 audit 95/99 = 95.96% NOT CALIBRATED (overlap/reclassification gateway family) -> both corrected | 2026-08-29 |
| f94 | R10,750–R11,260 | 511 | adopted | block-1 R10750-11039 corrected 290 = 271 D / 19 SU; block-2 R11040-11260 corrected 221 = 198 D / 23 SU (sum 469 D / 42 SU) | block-1 audit 132/139 = 94.96% NOT CALIBRATED (family-concentrated); block-2 audit 96/112 = 85.71% sample / 203/221 = 91.86% guard sweep NOT CALIBRATED -> both corrected | 2026-08-30 |
| q94 (B+C opener block) | R11,261–R11,576 | 316 | adopted | corrected final 316 = 303 D / 13 SU (UNCOVERED=0; supersedes the provisional pass census 316 = 301 D / 15 SU with 221 ledger-matched / 95 UNCOVERED) | 241/288 = 83.68% sample / 268/316 = 84.81% full NOT CALIBRATED - central simultaneity frame REVERSED (q94 has no simultaneity sentence) -> frame-reversal correction sweep applied; corrected final adopted at the v1.44 fold, q94 B+C CLOSED, contiguous R1-R11576 = 55.61% | 2026-08-30 |
| q94 (D+E block) | R11,577–R11,894 | 318 | in_cycle | — | — | — |
| q94 (remainder) | R11,895–R11,974 | 80 | pending | — | — | — |

### A3 classification, block by block

*What one unit is*: One queue row is one compiled-variable "family" from the A3 document-local review queue: a single PSID codebook value-meaning (e.g. rank 1's "Major assignment; probable error of greater than $300 or 10 percent of assignment value (whichever is greater)", per sol-ce-a3-reconcile-1-300-report.md's scope receipts, which identify each rank by stage/global/lexeme/meaning) grouping all uncovered occurrences of that meaning within one document. Per sol-ce-a3-queue-characterization.md the queue is "41,103 families / 86,840 uncovered occurrences (mean 2.11, max 38; 31,588 single-occurrence rows). All rows source_document_count = 1 (document-LOCAL...)". Each rank is adjudicated to a missingness disposition — per sol-ce-a3-reconcile-1-300-report.md: "T = true/missing; U = underdetermined; F = false/nonmissing" — with a fourth outcome X/UNCLASSIFIED (fail-closed quarantine where O>0 or R=0) adopted from block 24001 onward under the v1.14 X-vocabulary ruling ("block finals are now four-set T/U/F/UNCLASSIFIED partitions").

| Block | Final census | Audit | Status |
|---|---|---|---|
| 1–800 | T 729 / U 24 / F 47 | — | final |
| 801–1,600 | T 28 / U 759 / F 13 | — | final |
| 1,601–2,400 | T 81 / U 686 / F 33 | — | final |
| 2,401–3,200 | T 545 / U 69 / F 186 | — | final |
| 3,201–4,000 | T 568 / U 24 / F 208 | — | final |
| 4,001–4,800 | T 563 / U 26 / F 211 | — | final |
| 4,801–5,600 | T 545 / U 61 / F 194 | — | final |
| 5,601–6,400 | T 665 / U 92 / F 43 | — | final |
| 6,401–7,200 | — | — | unresolved |
| 7,201–8,000 | T 673 / U 86 / F 41 | — | final |
| 8,001–8,800 | T 578 / U 62 / F 160 | — | final |
| 8,801–9,600 | T 102 / U 22 / F 676 | — | final |
| 9,601–10,400 | T 701 / U 96 / F 3 | — | final |
| 10,401–11,200 | T 408 / U 391 / F 1 | — | final |
| 11,201–12,000 | T 503 / U 98 / F 199 | CLEAN 154/154 (contradictions 0) | final |
| 12,001–12,800 | T 482 / U 72 / F 246 | CLEAN 152/152 (library-defect set ∅) | final |
| 12,801–13,600 | T 784 / U 10 / F 6 | CLEAN 160/160 (contradictions ∅) | final |
| 13,601–14,400 | T 665 / U 131 / F 4 | CLEAN 147/147 covered predictions (100%) | final |
| 14,401–15,200 | T 323 / U 54 / F 423 | CLEAN 150/150 (100%) | final |
| 15,201–16,000 | T 625 / U 126 / F 49 | CLEAN 148/148 (100%) (v2 audit) | final |
| 16,001–16,800 | T 687 / U 38 / F 75 | CLEAN 154/154 (100%) | final |
| 16,801–17,600 | T 800 / U 0 / F 0 | CLEAN 160/160 (100%) | final |
| 17,601–18,400 | T 800 / U 0 / F 0 | CLEAN 160/160 (100%) | final |
| 18,401–19,200 | T 535 / U 222 / F 43 | LIBRARY DEFECT — 156/158 = 98.73% (2 contradictions) | final |
| 19,201–20,000 | T 743 / U 41 / F 16 | LIBRARY DEFECT — 160/161 = 99.38% (1 contradiction) | final |
| 20,001–20,800 | T 699 / U 100 / F 1 | CLEAN 148/148 (no library-class defect) | final |
| 20,801–21,600 | T 706 / U 91 / F 3 | NOT CLEAN — 3 library-class defects; 141/144 agree | final |
| 21,601–22,400 | T 666 / U 134 / F 0 | NOT CLEAN — 7 library-class defects; 141/148 agree (frontier paused: 4.7% > bound) | final |
| 22,401–23,200 | T 549 / U 248 / F 3 | CALIBRATED — 40% audit, 264/264 agree, 0.00% contradictions | final |
| 23,201–24,000 | T 686 / U 114 / F 0 | v1 NOT CALIBRATED 65.69%; v2 NOT CLEAN 154/160 agree | final |
| 24,001–24,800 | T 738 / U 59 / F 0 / X 3 | NOT CLEAN — 154 agreements / 5 claimed defects (sweep: 4 audit errors, 1 real) | final |
| 24,801–25,600 | T 217 / U 530 / F 2 / X 51 | NOT CLEAN 151/160 = 94.38% (corrected 150/160 after 2 claims overturned) | final |
| 25,601–26,400 | T 416 / U 126 / F 127 / X 131 | NOT CLEAN 110/163 = 67.48% (v2; corrected score 148/163 = 90.80%, OFUM claim SUSTAINED) | final |
| 26,401–27,200 | T 752 / U 47 / F 1 / X 0 | CLEAN 161/161 = 100.00% (first perfect audit of the arm) | final |
| 27,201–28,000 | T 338 / U 15 / F 0 / X 447 | NOT CLEAN 160/165 = 96.97% (27503 claim overturned by sweep) | final |
| 28,001–28,800 | T 205 / U 294 / F 38 / X 263 | NOT CLEAN 110/162 = 67.90% | final |
| 28,801–29,600 | T 314 / U 265 / F 45 / X 176 | NOT CLEAN 145/162 = 89.51% | final |
| 29,601–30,400 | T 0 / U 691 / F 0 / X 109 | NOT CLEAN 139/160 = 86.88% | final |
| 30,401–31,200 | T 0 / U 675 / F 0 / X 125 | NOT CLEAN 136/160 = 85.00% | final |
| 31,201–32,000 | T 437 / U 160 / F 3 / X 200 | NOT CLEAN 136/166 = 81.93% | final |
| 32,001–32,800 | T 290 / U 60 / F 0 / X 450 | CONTRADICT 77/161 = 47.83% (audit's 69-row over-quarantine claim later OVERTURNED by sweep) | final |
| 32,801–33,600 | T 215 / U 47 / F 0 / X 538 | CONTRADICT 147/166 = 88.55% class/decision (sweep: SUSTAIN, audit vindicated 166/166) | final |
| 33,601–34,400 | T 484 / U 70 / F 1 / X 245 | CONTRADICT 130/162 = 80.25% agreement (32/162 contradictions; sweep SUSTAIN 32/32) | final |
| 34,401–35,200 | T 59 / U 135 / F 183 / X 423 | NOT CLEAN 145/180 = 80.56% | final |

### Q5 annotation, sealed documents

*What one unit is*: Sealing one document is the Q5 arm's per-document closure. Two independent lanes (A and B) each annotate every extracted questionnaire occurrence in one PSID document with semantic-binding arrays, source-only; per the cal2 law ruling on the board, pre-freeze Q5 scope is 'binding arrays only (NE universally), one-document dual blocks'. A reconcile lane then aligns the two lane tables row-by-row, resolves every disagreement against the PSID source PDF (dispositions tallied AB/A/B/SRC), runs an agreed-row seam audit, and emits a canonical table of record — compact sorted-key JSON, one row per occurrence, with a pinned SHA-256 (e.g. sol-ce-q5-doc-1991f-reconcile-report.md: 'Result: reconciliation COMPLETE; canonical annotation SEALED'). The ladder is defined in sol-ce-q5-cal2-reconcile-report.md: 'Dual independent annotation; reconcile all disagreements; 10% agreed-row seam audit', with promotion requiring 'Two consecutive clean blocks'. SEALED is therefore distinct from the clean-block verdict: every one of the 33 sealed documents so far also ruled RECALIBRATE (most FAIL/RECALIBRATE — raw lane agreement below the clean bar), so the ladder has stayed at one document per dual-annotation block with clean streak 0 throughout.

| Document | Rows sealed | Verdict | Sealed |
|---|---|---|---|
| 1969 family questionnaire (q69) | 268 | SEALED / RECALIBRATE | 2026-08-21 |
| 1970 family questionnaire (q70) | 263 | SEALED / RECALIBRATE | 2026-08-22 |
| 1971 family questionnaire (q71) | 252 | SEALED / RECALIBRATE | 2026-08-23 |
| 1972 family questionnaire (q72) | 181 | RECALIBRATE | 2026-08-23 |
| 1973 family questionnaire (q73) | 277 | RECALIBRATE | 2026-08-23 |
| 1974 family questionnaire (q74) | 243 | COMPLETE / RECALIBRATE | 2026-08-23 |
| 1975 family questionnaire (q75) | 346 | COMPLETE / RECALIBRATE | 2026-08-23 |
| 1976 family questionnaire (q76) | 453 | COMPLETE / RECALIBRATE | 2026-08-23 |
| 1977 family questionnaire (q77) | 357 | RECALIBRATE | 2026-08-23 |
| 1978 family questionnaire (q78) | 362 | COMPLETE / RECALIBRATE | 2026-08-23 |
| 1979 family questionnaire (q79.pdf) | 281 | COMPLETE / RECALIBRATE | 2026-08-23 |
| 1980 family questionnaire (q80) | 444 | COMPLETE / Q5 FAIL / RECALIBRATE | 2026-08-23 |
| 1981 family questionnaire (q81) | 468 | COMPLETE / Q5 FAIL / RECALIBRATE | 2026-08-23 |
| 1982 family questionnaire (q82) | 466 | COMPLETE / Q5 FAIL / RECALIBRATE | 2026-08-23 |
| 1983 family questionnaire QxQ companion (fam1983_QxQs.pdf) | 1,025 | COMPLETE / Q5 FAIL / RECALIBRATE | 2026-08-24 |
| 1983 family questionnaire (q83.pdf) | 501 | COMPLETE / Q5 FAIL / RECALIBRATE | 2026-08-24 |
| 1984 family questionnaire (q84) | 88 | COMPLETE / Q5 FAIL / RECALIBRATE | 2026-08-24 |
| 1984 family questionnaire QxQ companion (fam1984_QxQs.pdf) | 3,125 | COMPLETE / Q5 FAIL / RECALIBRATE | 2026-08-24 |
| 1985 family questionnaire (q85) | 306 | COMPLETE / Q5 FAIL / RECALIBRATE | 2026-08-25 |
| 1985 family questionnaire QxQ companion (fam1985_QxQs) | 5,634 | COMPLETE / Q5 FAIL / RECALIBRATE | 2026-08-25 |
| 1986 family questionnaire QxQ companion (fam1986_QxQs) | 1,815 | COMPLETE / SEALED / FAIL — RECALIBRATE | 2026-08-25 |
| 1986 family questionnaire (q86) | 390 | COMPLETE / RECALIBRATE | 2026-08-25 |
| 1987 family questionnaire QxQ companion (fam1987_QxQs) | 1,741 | COMPLETE / SEALED / Q5 FAIL / RECALIBRATE | 2026-08-25 |
| 1987 family questionnaire (q87) | 435 | COMPLETE / RECALIBRATE | 2026-08-25 |
| 1988 family questionnaire QxQ companion (fam1988_QxQs) | 1,830 | COMPLETE / SEALED / Q5 FAIL / RECALIBRATE | 2026-08-25 |
| 1988 family questionnaire (q88) | 1,847 | COMPLETE / SEALED / Q5 FAIL / RECALIBRATE | 2026-08-25 |
| 1989 family questionnaire QxQ companion (fam1989_QxQs) | 1,875 | COMPLETE / SEALED / Q5 FAIL / RECALIBRATE | 2026-08-25 |
| 1989 family questionnaire (q89) | 951 | FAIL / RECALIBRATE (table complete and reproduced) | 2026-08-26 |
| 1990 family questionnaire QxQ companion (fam1990_QxQs) | 1,723 | COMPLETE / SEALED / FAIL / RECALIBRATE | 2026-08-26 |
| 1990 family questionnaire (q90.pdf) | 1,256 | COMPLETE (seal) / FAIL / RECALIBRATE | 2026-08-27 |
| 1991 family questionnaire QxQ companion (fam1991_QxQs.pdf) | 1,476 | COMPLETE / SEALED / FAIL / RECALIBRATE | 2026-08-27 |
| 1991 family questionnaire (q91.pdf) | 2,474 | FAIL / RECALIBRATE (annotation complete and sealed) | 2026-08-29 |
| 1992 family questionnaire QxQ companion (fam1992_QxQs.pdf) | 1,158 | RECALIBRATE (annotation complete and sealed) | 2026-08-30 |

## Development scorecard

Eight pre-registered gates; all seven locked gates have a registered first pass; 48 one-shot candidate runs on the public record.

Every candidate model is registered before its single scored run, and every run — pass or fail — is committed. The failures are part of the record.

| Gate | What it tests | Candidates | First pass |
|---|---|---|---|
| **Earnings-history credibility** | The backcast earnings process scores against held-out PSID panel moments and geometry blocks, judged against the same-panel noise floor. | 13 | Candidate 13 (rank_knn_v5, 2026-07-07): 5/5 seeds geometry, 4/5 battery, C2ST 0.523 ≤ 0.53 — after 12 committed failing runs. |
| **Family transitions (marital and fertility)** | Marriage, divorce, remarriage, widowhood, occupancy, cohort nuptiality, and fertility transitions scored against the PSID marital and childbirth history files. | 16 | Candidate 16 (hazard_v16, 2026-07-09): 4/5 seeds across all 46 gated cells — after 15 committed failing runs. |
| **Household composition** | Who lives with whom: coresidence stocks and wave-to-wave transitions from the PSID relationship matrix — spouse/partner, parent, child, grandchild, household size, multigenerational entry and exit. | 9 | Candidate 9 (hazard_v9, 2026-07-11): 4/5 seeds — after 8 committed failing runs. |
| **Marriage × earnings joint** | Who marries whom by earnings — assortative mating, earnings-conditional marriage hazards, and couple shared-earnings shape, on which spousal and survivor benefit levels depend. | 2 | Candidate 2 (hazard_v2, 2026-07-12): 4/5 seeds. |
| **Disability** | Work-limitation incidence and recovery hazards, disabled-occupancy prevalence, and near-retirement disability exit, anchored against SSA Disability Annual Statistical Report tables. | 1 | Candidate 1 (2026-07-12): 5/5 seeds, all 12 gated cells — passed on the first attempt. |
| **Representative-frame transport** | The PSID-estimated generators transported onto the certified CPS representative frame: 44 gated cross-sectional cells plus SSA administrative margins. | 4 | Candidate 4 (2026-07-13): 43/43 cells in-band on 5/5 seeds — after 3 failing candidates. |
| **Temporal-holdout projection drift** | The projection engine fits on data through 2014 only, then projects and is scored on the held-out 2015–2022 window — a genuine out-of-time test. | 3 | Candidate 3 (2026-07-24): 4/5 seeds across the 11 gated cells. |
| **Forward projection** | Near-term components resolve against future administrative publications on named resolution rules — scored when the numbers come out. | — | — (thresholds not yet locked) |

### Comparisons against the incumbent models

Direct number-for-number comparisons against the incumbent models are registered as a benchmark inventory that fills in as modules land — shown here before launch, deliberately.

- **MINT / CBO / SSA benchmark inventory (tranche 2)** — *2 of 60 rows computable*. 60 registered comparison rows against published MINT (19), CBO (30), and SSA Statistical Supplement (11) figures; 58 rows await the modules that compute them. Each row is pinned to the captured source file by hash. ([source](https://github.com/PolicyEngine/microcosm-dynamics/blob/master/runs/benchmark_tranche2_evaluation_v1.json))
- **Cross-sectional incumbent replacement (Enhanced CPS)** — *candidate beats incumbent*. Archived scorecard: a Microcosm-US candidate against the certified Enhanced CPS 2024 production incumbent on 3,704 calibration targets — candidate loss 0.228 vs incumbent 1.405 (holdout 0.038 vs 0.317). Publication pending in microcosm-benchmarks. ([source](https://github.com/PolicyEngine/microcosm-benchmarks))
- **DYNASIM output comparisons** — *not yet*. No quantitative DYNASIM-output rows exist yet; today's DYNASIM comparison is the capability table below. Quantitative rows begin at the projection and benefit stages.

### Capability scorecard vs DYNASIM

Component-by-component against DYNASIM, the main non-governmental dynamic benchmark (from the public record; full matrix in the design book).

| Component | DYNASIM | This project |
|---|---|---|
| Historical earnings | Lifetime histories from survey plus linked administrative inputs | PSID 1968–2022 panel; gate 1 passed (13th candidate) |
| Family structure | Marriage, divorce, and family in the annual simulation | Gates 2, 2b, 2c passed across three tranches |
| Disability | Documented health and work-limitation modules | Gate m4 passed, anchored to SSA administrative tables |
| Base population | SIPP-based starting sample | Certified CPS synthetic frame; transport gate w1 passed |
| Forward projection | Annual updating and alignment | Temporal-holdout gate m6 passed; forward gate pre-lock |
| Social Security rule engine | Rule-based, code not public | Open PolicyEngine-US engine plus AIME/PIA oracle (built, not gated) |
| Claiming behavior | Retirement-and-timing model | Reduced-form claim-age distribution (built, reported, not gated) |
| Auxiliary benefits | Spouse and survivor analysis in natural domain | Spousal, survivor, widow incl. dual-entitlement logic (built, not gated) |
| Wealth, assets, and LTSS | Major documented strength | Design-only — a later extension track |

## Timeline forecast

From the pre-registered timeline ledger, entry 21 (registered 2026-08-20). Dates are point-in-time forecasts, not commitments; the ledger records every revision with its reasons.

| Milestone | p50 | p80 |
|---|---|---|
| Milestone A — revision-22 ratification (A20 framework operative) | 2026-09-08 | 2026-09-22 |
| Milestone B — corrected-earnings successor authority and publication (the resolution event) | 2026-10-14 | 2026-12-02 |

- **Milestone A**: Not gated by the Q5 program; requires the A4 evidence freeze and the C20 ceremony chain.
- **Milestone B**: Gated by the Q5 program, the span/collapse cure (discharged), and completion of the purpose census.

## Recent milestones

- **2026-08-30** — Purpose census reaches 55.61% (q94 B+C closed under ledger v1.44 after the audit reversed the opener’s imported simultaneity frame — the cross-document transfer prohibition holding under pressure); A3 frontier reaches 35,200/41,103 (85.6%).
- **2026-08-30** — E3 questionnaire era completed and the E4 era opened overnight; f94 complete; purpose census reaches 54.10% contiguous. A3 reaches the 1968-era queue boundary (83.7%). Q5 seals documents 048–049 (33/257).
- **2026-08-29** — Purpose census crosses 50% of the residual domain (contiguous R1–R10457 = 50.24%); q93 B+C complete.
- **2026-08-28** — f91 complete; purpose census at 43.11% contiguous; governing ledger reaches v1.26.
- **2026-08-26** — f89-era tranche closed: contiguous R1–R8552 = 41.09%; every rank of the 1,920-rank tranche went through pass, dense audit, adjudication where audits split, and correction sweep.
- **2026-08-20** — Timeline-forecast entry 21 registered: scope bifurcation into milestones A and B.

## How these numbers are produced

Every block of work moves through the same pipeline before it counts here: a full pass over the block, an independent dense audit, an adjudication step where audits disagree, and a correction sweep whose output is folded into the governing ledger. Q5 documents are annotated by two independent lanes and sealed only by a reconciliation of both. Nothing on this page is self-reported by the lane that produced it.

## Links

- [Amendment 20 draft (PR #405)](https://github.com/PolicyEngine/microcosm-dynamics/pull/405)
- [Pre-registered gate contract (gates.yaml)](https://github.com/PolicyEngine/microcosm-dynamics/blob/master/gates.yaml)
- [Timeline forecast ledger (machine-readable)](https://github.com/PolicyEngine/microcosm-dynamics/blob/master/docs/forecasts/timeline_ledger.json)
- [The Populace dynamics paper](https://populace.dev/papers/dynamics)
