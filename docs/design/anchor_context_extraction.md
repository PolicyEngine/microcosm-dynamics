# The anchor context extraction: pinned official SSA series and the context report

- **Status:** DRAFT for referee rounds. Nothing here authorizes an
  extraction commit or a report run.
- **Resolves:** the §12 successor named first in leverage order by the
  first estimates report ("the annual SSA/Trustees level-anchor
  extraction") and the amendment-1 deferral of the §7 context ratio
  (`deferred_to_anchor_extraction`). Forecast-ledger entry 10 registers
  against this design's resolution criterion when the design ratifies.
- **Evidence base:** the entry-8 published artifact
  (`runs/first_estimates_v1.json`, sha256 `719604ca…2977`) for the
  model-side concepts, and the anchor scoping survey (the sol lane
  report of 2026-07-26, reproduced in the ratification PR record) for
  the official-series determinations. Official values cited below were
  read from ssa.gov during scoping and are re-verified byte-level at
  extraction time; nothing in this design hard-codes them.

## 1. What this is — and the one thing it is not

A **context-anchor extraction**: a committed, provenance-pinned file of
official SSA/Trustees annual series for 2015-2022, plus a **context
report** that places the first estimates report's frame-relative
numbers next to their nearest official counterparts with an explicit
mismatch code on every pairing.

It is **not level alignment**. No model number is scaled, calibrated,
reweighted, or corrected toward an official value. The report's three
labels — frame-relative, pre-alignment, labor-income proxy — stand
untouched, and the W1 national bridge remains a separate, later
successor. A reader of the context report learns how far and in what
ways the model's closed-frame quantities sit from administrative
reality; they do not receive an aligned estimate.

## 2. The extraction (`data/external/ssa_level_anchors.json`)

Follows the committed `ssa_cola_history.json` precedent: explicit
schema, deterministic offline build, canonical content hash, coverage
assertions, and a verified-against statement — extended for the
level-anchor realities the scoping survey established.

**Schema law:**

- `schema_version`: `ssa_level_anchors.v1`.
- `artifact_role`: the literal string `official_context_only` — the
  file's own statement that it confers no alignment authority.
- `year_basis`: `calendar_year`. Observations are keyed by calendar
  year 2015-2022 exactly; coverage is asserted. (COLA-style
  determination-year keying would be false here and is not used.)
- One **series object** per reviewed series id, each carrying:
  - `series_id` (stable, reviewed; the frozen key set below),
  - `program_scope` (`retired_worker` | `oasi` | `oasdi`),
  - `unit` (explicit; dollars in millions unless the source publishes
    otherwise, counts in persons or thousands as published — never
    silently rescaled),
  - `accounting_basis` (e.g. `benefits_paid_supplement_allocation`,
    `trust_fund_cash`, `december_current_payment_stock`,
    `calendar_year_awards`, `reported_taxable_earnings`,
    `adjusted_taxable_payroll`),
  - `source`: publication (`ssa_supplement_2025` |
    `trustees_2026`), the exact table number as published, the
    resolved URL, the **retrieval timestamp**, and the **sha256 of the
    retrieved source bytes** (edition labels are not byte pins: the
    2025 Supplement was corrected in place in April 2026, and Trustees
    table numbers migrate across editions — IV.B3→IV.B4,
    VI.G6→VI.G1 — so URL-plus-edition citation without bytes is
    insufficient provenance),
  - `values`: the eight calendar-year observations,
  - `preliminary_years`: any source-flagged preliminary cells (the
    scoping survey found 2021-2022 marked preliminary in Supplement
    Table 4.B11),
  - `mismatch_code`: the frozen concept-mismatch key binding this
    series to its model counterpart (§4).

**The frozen series set (v1):** retired-worker awards (Supplement
6.A1); retired-worker and total-OASI benefits paid (Supplement 4.A5);
OASI and OASDI trust-fund benefit payments (4.A1/4.A3); December
current-payment stocks, retired-worker / OASI / OASDI (5.A4); workers
with taxable earnings, reported taxable earnings, and OASDI
contributions (4.B11); Trustees adjusted taxable payroll (VI.G1) and
covered workers (IV.B4); OASI and OASDI net payroll-tax contributions
(4.A1/4.A3). The Supplement's reported taxable earnings and the
Trustees' adjusted taxable payroll are **separate series with separate
mismatch codes** — the survey established they are not synonyms (the
Trustees series adjusts multi-employer excess wages).

**Exclusions, stated:** the §7 average-award ratio's official
denominator remains unpublishable from Supplement 6.A2 alone (each year
splits January-November and December, and collapsing them requires
subperiod award weights this design does not invent). The OACT dynamic
award query could provide annual cells, but only under captured and
pinned request-and-response bytes; that capture is **out of scope for
v1** and the §7 ratio remains deferred, now with its blocking reason on
the page.

## 3. The extraction build and verification

A committed builder script reads a **committed raw snapshot** of each
source page (the pinned bytes), parses the eight cells per series, and
emits the canonical JSON; a reproduction test pins the artifact's
sha256 and rebuilds it from the snapshots in CI. Network access happens
once, at snapshot time, by the coordinator; the build itself is
deterministic and offline. Any future refresh is a new vintage: a new
snapshot set, a new artifact version, and a re-run of the referee
round — values revise (the survey caught 2022 taxable payroll moving
$9,151B → $9,134B between Trustees editions), so vintage is identity.

## 4. The context report and its mismatch law

One table family per model concept, each row pairing a model quantity
(with its three labels and, for benefit quantities, the traveling
birth-timing sensitivity reference) against exactly one anchor series,
with the **mismatch code expanded in prose in the same table note**.
The frozen mismatch codes, from the scoping survey:

- `award_vs_claim_stamp`: SSA awards are administrative effectuations
  (payable-not-guaranteed); the model stamps mechanical claim-age
  crossings.
- `annualized_pia_vs_payments`: the model pays 12 × the COLA-stepped
  eligibility-PIA amount to every included claimant-year, with no
  partial years and no post-claim recomputation; official benefits-paid
  series record actual outlays to the in-force population.
- `population_scope`: retired-worker vs OASI vs OASDI scope of each
  pairing, named per row.
- `stock_definition`: December current-payment stock (or June 30 for
  Trustees IV.B4) vs the model's persons-with-annualized-payments
  count; the model's opening stock is a report-only imputation with no
  administrative counterpart.
- `proxy_vs_covered_earnings`: PSID labor-income proxy vs verified
  covered employment; the model's taxable amount is
  `min(proxy, wage base)` **with no zero floor**, so negative proxy
  earnings reduce model payroll while being absent from the model's
  covered-earner count — disclosed as a model-side property, whether or
  not a later revision changes it.
- `earnings_vs_payroll_adjustment`: reported taxable earnings vs
  multi-employer-adjusted taxable payroll on the official side.
- `cash_vs_accrual_rate_arithmetic`: trust-fund contribution income
  (estimated deposits and adjustments) vs the model's earnings-year
  rate multiplication; also carries the 2016-2018 internal OASI/DI
  reallocation (5.015/1.185 vs 5.300/0.900 per leg) inside the constant
  combined 12.4% the model applies.

**Permitted framings:** side-by-side levels with mismatch codes; ratios
of model to anchor presented as **context ratios, not error measures**
(the frame-relative label means the ratio conflates frame coverage with
model behavior, and the report says so); per-beneficiary and
per-worker intensity comparisons carrying the same codes. **Forbidden
framings:** any "coverage rate" or "capture rate" language implying the
anchor is the model's target; any scaling of a model number by an
anchor; any decomposition attributing the model-anchor gap to named
causes (that is the W1 bridge's and successors' work, and asserting it
here would be a fabricated mechanism).

## 5. Ceremony

The design ratifies through the standing adversarial referee rounds.
The extraction lands as its own PR (snapshots + builder + artifact +
reproduction test), referee-gated on source fidelity. The context
report is a **registered estimates report** under the class chartered
by the first estimates design — registered configuration, one
registered run, publishes-regardless, verdictless — consuming the
published `first_estimates_v1.json` and the committed anchors, with a
full out-of-ceremony rehearsal before any registration is spent and the
six-point launch checklist in force. Forecast-ledger entry 10 registers
at design ratification with resolution at the context report's
publication-PR merge.

## 6. What is unchanged

The first estimates artifact and its labels; design revision 10.1 and
every frozen key; the §10 gap block (the context report cites the
deferred-§7 row's new blocking reason rather than editing history); the
W1 bridge's position in the successor order; and §11's execution rule,
which governs the context report's run verbatim.
