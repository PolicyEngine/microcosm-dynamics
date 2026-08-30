<!-- GENERATED FILE - DO NOT EDIT. Edit docs/progress/progress.json and run scripts/build_progress_page.py -->

# Development progress

*Snapshot as of 2026-08-30T11:15:00Z (UTC); updated at least daily while the evidence campaign is active. The data behind this page is committed at [`docs/progress/progress.json`](progress/progress.json).*

This page tracks the evidence campaign behind Amendment 20 (two-arm evidence charter for the covered-earnings correction design): three verification arms that must complete before the A4 evidence freeze and the ratification ceremony. The design itself is under review in PR #405 (open; draft ratified through round 6.2); the next ceremony step is the A4 evidence freeze, then the C20 ratification chain toward revision 22.

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
  Rank-by-rank purpose adjudication over the residual prompt domain. Each block runs a full pass, a dense audit, and a correction sweep before its entries are adopted into the governing ledger (now v1.42).</div>
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
  Systematic classification of the compiled 41,103-row variable queue under the class library (v1.19), in 800-rank blocks with 20% dense audits and correction sweeps.</div>
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
  Per-document binding-array annotation of the PSID questionnaire corpus: two independent lanes per document, then a reconciliation that seals a table of record.</div>
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
