<!-- GENERATED FILE - DO NOT EDIT. Edit docs/progress/progress.json and run scripts/build_progress_page.py -->

# Development progress

*Snapshot as of 2026-08-30T11:15:00Z (UTC); updated at least daily while the evidence campaign is active. The data behind this page is committed at [`docs/progress/progress.json`](progress/progress.json).*

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
      11,260 / 20,815 &middot; 54.1%</span>
  </div>
  <div style="background: #e9ecef; border-radius: 6px; height: 14px;
              margin: 0.35em 0;">
    <div style="background: #2c6496; border-radius: 6px; height: 14px;
                width: 54.1%;"></div>
  </div>
  <div style="font-size: 0.9em; color: #555;">prompts adopted (contiguous R1–R11260).
  Establishing what each of the ~21,000 remaining items in the PSID's 1968–2023 questionnaires and codebooks is actually asking, so the model only uses variables whose meaning has been adjudicated rather than assumed. Each block runs a full pass, an independent dense audit, and a correction sweep before its entries are adopted into the governing ledger.</div>
</div>


<div style="margin: 1.1em 0 1.4em 0;">
  <div style="display: flex; justify-content: space-between;
              align-items: baseline;">
    <strong>A3 classification arm</strong>
    <span style="font-variant-numeric: tabular-nums;">
      34,400 / 41,103 &middot; 83.7%</span>
  </div>
  <div style="background: #e9ecef; border-radius: 6px; height: 14px;
              margin: 0.35em 0;">
    <div style="background: #2c6496; border-radius: 6px; height: 14px;
                width: 83.7%;"></div>
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

## Timeline forecast

From the pre-registered timeline ledger, entry 21 (registered 2026-08-20). Dates are point-in-time forecasts, not commitments; the ledger records every revision with its reasons.

| Milestone | p50 | p80 |
|---|---|---|
| Milestone A — revision-22 ratification (A20 framework operative) | 2026-09-08 | 2026-09-22 |
| Milestone B — corrected-earnings successor authority and publication (the resolution event) | 2026-10-14 | 2026-12-02 |

- **Milestone A**: Not gated by the Q5 program; requires the A4 evidence freeze and the C20 ceremony chain.
- **Milestone B**: Gated by the Q5 program, the span/collapse cure (discharged), and completion of the purpose census.

## Recent milestones

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
