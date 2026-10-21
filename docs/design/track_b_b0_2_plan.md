# Track B B0.2: plan

**Status: plan, 2026-10-21. This is not an audit record, and no gate can
register on it.** Max ruled in d1802 (2026-10-21) that B0.2 starts now,
on the Track B lane, after the B2 successor memo. This file sets out what
B0.2 must deliver, the order of work and the rules that keep it apart
from the successor design. It changes as the work goes; the audit
records that follow it are the frozen artifacts.

"The design" means
`microcosm-launch-evidence/dynasim-parity-20260909/trackb-design-20260928.md`
(revision 3), which sits outside this repository. Line numbers refer to
that file.

## 1. What B0.2 must deliver

- **One frozen record per gate** (design line 288): B3, B3L, B4, I's
  observational timing gate, B5-empirical RET, B6a, B6b and J. Each
  record lists the ten §5.2 elements, read as B0.1 read them
  (`docs/design/track_b_b0_1_audit.md`, section 2): source release,
  variables, population, exposure history, holdout partition, critical
  cells, numerical tolerances, uncertainty treatment, pass conjunction,
  and reference dates kept separate from interview and publication
  availability. Each record also names its power procedure. A gate
  cannot register until its record is frozen.
- **A structural-audit protocol frozen before any count or power
  summary** (line 286). The record keeps reference dates apart from
  availability. Outcomes that were already inspected stay regression
  evidence, and "later" or "external" does not by itself establish an
  unused holdout.
- **A blinded review of prospective feasibility and power** for the
  §5.3 limits (line 120). It may find a limit infeasible before any
  candidate result, which leads to prospective rescoping; it may never
  loosen a limit after candidate results (line 308).
- **J's joint estimands and numerical limits**, frozen in B0.2 and
  ratified by a blinded reviewer before B3 registers (lines 230, 320,
  365-368; Q10, line 615). J's holdout must be independent of B2's
  evaluation data.
- **Exposure.** B2's result is recorded as exposed before J's holdout is
  chosen (lines 297, 368). So are the SSA Annual Statistical Supplement
  pages that Track B participants have already opened (lines 290-295).
- **Pricing of the still-unpriced items** (§3.3, line 198; Q13, line
  618): data access, loaders and gate work for I's observational timing
  gate; the HRS loader and access; linked-withholding data access and
  loaders for empirical RET; entrant initialization; B6b's access time;
  and the 2032 and 2050 horizon extensions. Q4 (line 606) sets the order
  for data: public HRS and SSA sources are evaluated first, and
  restricted linked data are requested only if public sources cannot
  supply the risk denominator, the timing observations or the
  withholding observations.
- **B0.1's handoffs** (`docs/design/track_b_b0_1_addendum.md`, "To
  B0.2"):
  - the marital selectors' pseudo-boundaries 2008 and 2010 bear on B4;
  - B3L's 2006 boundary is a q\* and ρ\* pseudo-boundary whose floors
    and outcomes are in the ledgers, and protocol v2 projected candidate
    3's law from 2006 to 2008 and 2010 at ages 25-64, which includes
    B3L's 62-64 band;
  - §5.3 feasibility is reviewed once, for B3 and B3L, with B0.1's
    section 11.3 figures as inputs;
  - H's spec names and counts its 2010 start roster, and B4's coverage
    declaration cites it;
  - the addendum's design rule (its section 16, item 10: household
    resampling stands only if every cell's design-ratio 95th percentile
    is at most 1.10) did not hold at the 2006 pseudo-origin, so the
    choice between inflating standard errors and resampling design
    clusters arises again for every later gate.
- **B2's medians.** Under d1606 option C1, B2 gates the 90th percentile
  and the zero-earnings rate by cohort; its two median cells are
  report-only (`src/populace_dynamics/track_b/b2.py`, `GATE_SURFACE` and
  `HEADLINE_SCOPE`). B0.2 records which later gate, if any, covers the
  medians, and states that nothing downstream may rely on B2 for them.

## 2. Separation from the successor design

Under d1659 a B2 successor is designed on evidence independent of B2's
outcome. Its design inputs live in
`microcosm-launch-evidence/dynasim-parity-20260909/trackb-b2-successor-20261018/`.
B0.2 and that lane must not see each other's evidence.

- No B0.2 lane or reviewer reads the successor folder, or anything
  derived from it.
- The successor lane must not read B0.2's counts, planning values or
  records. Before any B0.2 file holding real-data counts reaches
  master, B0.2 adds an exclusion inventory in the format
  `scripts/track_b_b0_1_review_root.py` reads (`q6_exclusions`), which
  successor-lane review roots name.
- B2's outcome is not restricted for B0.2. The 2026-10-18 entry in
  `RESTRICTED-FILES.md` restricts B2's outcome files for roles building
  or proposing a successor blind, and B0.2 must record that exposure.
  B0.2's blinded roles still get roots built by the review-root
  builder, which always drops the standing B2-outcome record
  (`docs/design/track_b_b2_outcome_exclusions.json`); they read B2's
  exposure from B0.2's own record.

## 3. Order of work

1. **Landscape (no counts).** Separate lanes, none of which sees
   another's output before synthesis:
   - a repository and staged-data inventory: loaders, staged sources
     and what each gate needs against what exists, from listings and
     code only, with no survey values read;
   - external sources and access: public and restricted HRS, SIPP
     public-use and SSA-linked files, SSA public-use files, sources of
     withholding and event-timing observations, and inputs for entrant
     initialization, each with access steps, lead time, cost and the
     gates it could serve;
   - a mechanical exposure inventory for the candidate holdouts of each
     gate, extending B0.1's inventory approach;
   - a per-gate requirements table drawn from the design text.
2. **Protocol.** One B0.2 structural-audit protocol, reviewed by GPT-6.1
   Sol (`--tier hard`), then committed and hash-pinned before any count
   runs, as B0.1's section 16 was.
3. **Counts and power.** One-shot count scripts, run once from a clean
   worktree at the protocol commit, writing exclusive outputs. Tests
   include value-invariance tests in the style of
   `test_counts_are_invariant_to_valid_earnings_values`, Hypothesis
   property tests and mutation checks.
4. **Records.** The per-gate records, the pricing table and questions
   for Max with recommended defaults, queued with `cos add-decision`.
5. **Reviews.** A Sol review of each record; the blinded
   feasibility-and-power review; the blinded ratification of J's record
   before B3 registers.

The work may split into several pull requests (plan and protocol,
counts, records). This draft pull request opens with the plan.

## 4. Rules

- Design §5.1: no edits to `engine/loop.py`, `engine/steps.py`,
  `gates.yaml` or committed `runs/*.json`.
- B0.2 fits no model, runs no projection and computes no candidate
  outcome. What it may compute from real data is fixed by its protocol.
- Local runs use at most four BLAS and OpenMP threads with
  `OMP_WAIT_POLICY=PASSIVE`, and at most four test workers.
- Any change to `tests/tier_counts.json` waits for a merge slot from the
  Microcosm dynamics coordinator.
- B0.2's 5-7 engineer-day estimate (line 120) predates the timing gate
  and is not re-priced in the design (line 201). B0.2 reports its actual
  effort beside that estimate.
