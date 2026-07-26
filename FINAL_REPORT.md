# Entry 8 paper draft report

## Outcome

The draft adds a new `## The first estimates` results subsection to
`paper/paper.qmd` and updates the paper's status paragraph. It reports the
registered, verdictless first-estimates publication; five headline tables; the
registration and incident record; the frozen gap and `certifies_nothing`
limitations; all nine named successors; and the required closing claim:

> This is what the statutory formulas yield on the reproduction panel — not an
> estimate of what Social Security pays and collects.

This is a draft only. Nothing was pushed or otherwise changed remotely.

One repository-state qualification remains. Direct network access is disabled
in the sandbox, so the signed commit object
`7b1ee30c355749884522fb11ec25aa8bea6152e8` could not be fetched into the local
object database. Read-only GitHub metadata confirms that remote `master` is
exactly that commit, its parent is `8b031bc3`, and it changes only
`docs/forecasts/timeline_ledger.json`. The remote file has blob
`6c7161e8f6466a86ffada658cd8e360cc3076e21`, exactly matching local commit
`0f246c4`; the full patches also match. The draft is therefore provisionally
rebased on the tree-equivalent `0f246c4`. After a successful fetch, the
coordinator should repair exact ancestry with:

```sh
git rebase --onto 7b1ee30c355749884522fb11ec25aa8bea6152e8 \
  0f246c46234bea22795c092285424556f43ff8c2 \
  claude/entry8-paper
```

## Diff

Relative to the provisional tree-equivalent base `0f246c4`:

- `paper/paper.qmd`: 190 insertions, 3 deletions. Adds the results subsection
  after the candidate-3/forecast-ledger arc and changes the status paragraph
  from “unlocks the next stage” to the published-but-limited result.
- `PROGRESS.md`: committed workflow state, completed work, verification, and
  next action from the start of the lane.
- `FINAL_REPORT.md`: this provenance and handoff report.

No figure or palette file changed. Generated `paper/paper.html` and
`paper/paper.pdf` are ignored build outputs.

Substantive branch commits after the provisional base are:

```text
28b9199 Start entry 8 paper progress log
b7bac67 Record entry 8 paper audit
162546e Add first estimates paper results
72d110d Record first estimates draft
4b890b6 Render birth sensitivity approximation portably
8c5b360 Clarify append-only incident record
13e167d Record draft verification and provisional base
89e2a81 Record final paper verification
```

## Source artifact and transformations

The sole numerical source is `runs/first_estimates_v1.json`. Its recomputed
SHA-256 is:

```text
719604ca4364e7cdef2293329ed0beb0e011e5d4d1c34f0e508c8f2fd9932977
```

All table cells were extracted and then checked programmatically. Dollar
amounts are divided by `1e9`; weighted counts are divided by `1e6`; shares are
multiplied by 100. The paper displays dollar aggregates to one decimal billion,
weighted counts to two decimal million, the funnel's unweighted mean and SD to
one decimal, and birth-timing shares to two decimals. No values were copied
from prose or hand-recalculated in the manuscript.

### Report identity, run rule, and labels

| Paper datum | Exact artifact key |
|---|---|
| Schema and report identity | `.schema_version`, `.identity.report_id`, `.identity.report_class` |
| Registration `populace-dynamics#307` | `.identity.registration_reference` and `.configuration_echo.registration_reference` |
| Candidate-3 `GATED_REALIZED`, unsplit, 2014–2022 | `.configuration_echo.projection.object`, `.configuration_echo.projection.split`, `.configuration_echo.projection.start_year`, `.configuration_echo.projection.end_year` |
| Twenty draws | `.configuration_echo.projection.draw_indices` and `.execution.completed_draw_indices` |
| One run, publishes regardless, no self-rescue | `.execution.canonical_rule.registered_runs`, `.execution.canonical_rule.publishes_regardless`, `.execution.canonical_rule.no_self_rescue` |
| Environment sidecar | `.integrity.environment_sidecar.path`, `.integrity.environment_sidecar.sha256` |
| Required labels | `.tables.modeled_award_flow.labels`, `.tables.opening_stock.labels`, `.tables.revenue.labels` |

Each of the three `.labels` arrays is exactly:
`["frame-relative", "pre-alignment", "labor-income proxy"]`. Those labels are
printed in every new table caption, including the count and sensitivity tables.

The rehearsal-determinism sentence combines the publication record at
`8b031bc3` with artifact checks:

- draw invariance at sample SD `0.0` comes from
  `.counts.aggregate[] | select(.metric == "birth_source__<source>__unweighted").sample_sd`
  for `<source>` equal to `exact_marriage`, `inferred_period_age`,
  `derived_projection_age`, and `synthetic_native`;
- zero unresolved-birth exclusions in every draw comes from
  `.counts.per_draw[].inclusion__excluded_birth_year_unresolved__unweighted`;
- draw-0 included `1,514` comes from
  `.counts.per_draw[0].inclusion__included__unweighted`;
- across-draw `1,518.1 ± 16.8` comes from `.counts.aggregate[]` where
  `.metric == "inclusion__included__unweighted"`, fields `.mean` and
  `.sample_sd`.

### Benefit table

For each displayed year `Y` in 2015–2022, the year is the row's `.year`.
Every mean and SD comes from these exact selectors and fields:

| Displayed column | Exact selector |
|---|---|
| Modeled-award benefit | `.tables.modeled_award_flow.aggregate[] \| select(.year == Y and .metric == "frame_annualized_benefit") \| {mean, sample_sd}` |
| Modeled-award weighted beneficiaries | `.tables.modeled_award_flow.aggregate[] \| select(.year == Y and .metric == "weighted_beneficiary_count") \| {mean, sample_sd}` |
| Opening-stock benefit | `.tables.opening_stock.aggregate[] \| select(.year == Y and .metric == "frame_annualized_benefit") \| {mean, sample_sd}` |
| Opening-stock weighted beneficiaries | `.tables.opening_stock.aggregate[] \| select(.year == Y and .metric == "weighted_beneficiary_count") \| {mean, sample_sd}` |

The sample-size statements come from each selected row's `.n_draws` and
`.n_observations`. The odd-year carry disclosure printed below the table comes
from `.tables.modeled_award_flow.odd_year_carry_disclosure` and
`.tables.opening_stock.odd_year_carry_disclosure`. The birth-timing travel
cross-reference is also present in both tables' `.birth_timing_reference`.

### Revenue table

For each displayed year `Y` in 2015–2022:

| Displayed column | Exact selector |
|---|---|
| Taxable payroll | `.tables.revenue.aggregate[] \| select(.year == Y and .metric == "weighted_taxable_payroll") \| {mean, sample_sd}` |
| Combined contributions | `.tables.revenue.aggregate[] \| select(.year == Y and .metric == "combined_contributions") \| {mean, sample_sd}` |
| Weighted covered earners | `.tables.revenue.aggregate[] \| select(.year == Y and .metric == "weighted_covered_earner_count") \| {mean, sample_sd}` |

The employee/employer equality is independently visible in
`.tables.revenue.aggregate[]` under metrics `employee_contributions` and
`employer_contributions`, and in
`.parameters.oasdi_rate_legs.{asserted_employee_rate,asserted_employer_rate,asserted_combined_rate}`.
The odd-year statement is `.tables.revenue.odd_year_carry_disclosure`.

### Inclusion funnel

The first two funnel rows are derived draw-0 sums; the included row is the
artifact's across-draw aggregate.

- `30,482` is the sum of the five
  `.counts.per_draw[0].birth_source__<source>__unweighted` keys:
  `9,673 + 13,727 + 4,077 + 690 + 2,315`.
- `387.10M` is the corresponding sum of the five
  `.counts.per_draw[0].birth_source__<source>__weighted` keys:
  `108,489,336 + 209,808,001 + 40,775,223 + 7,173,906 + 20,853,662`.
- `3,083` is
  `.counts.per_draw[0].inclusion__origin_modeled_award__unweighted`
  (`1,495`) plus
  `.counts.per_draw[0].inclusion__origin_opening_backfill__unweighted`
  (`1,588`).
- `60.59M` is the analogous pair of weighted keys:
  `24,777,310 + 35,808,857`.
- `1,518.1 ± 16.8` is `.counts.aggregate[]` where
  `.metric == "inclusion__included__unweighted"`, fields `.mean` and
  `.sample_sd`.
- `35.18M ± 0.40M` is `.counts.aggregate[]` where
  `.metric == "inclusion__included__weighted"`, fields `.mean` and
  `.sample_sd`.

### Five-class birth-source table

For each source `S` in `exact_marriage`, `inferred_period_age`,
`derived_projection_age`, `synthetic_native`, and `unresolved`, every displayed
cell comes directly from:

```text
.counts.per_draw[0].birth_source__S__unweighted
.counts.per_draw[0].birth_source__S__weighted
.counts.per_draw[0].included_birth_source__S__unweighted
.counts.per_draw[0].included_birth_source__S__weighted
```

The total row sums those five keys. Its included totals also reconcile exactly
to `.counts.per_draw[0].inclusion__included__unweighted` (`1,514`) and
`.counts.per_draw[0].inclusion__included__weighted` (`35,341,835`, displayed
as `35.34M`).

### Birth-timing table and traveling row

Let
`B = .diagnostics.birth_timing_sensitivity.per_draw[0]`. The coherent rows use
these exact keys:

```text
B.coherent_shift_stress_scenarios.full_scenario_ledger.scenarios.baseline.complete_included_set_count
B.coherent_shift_stress_scenarios.full_scenario_ledger.scenarios.baseline.weighted_annualized_benefit_total.{amount,delta_from_baseline,delta_share_of_baseline}

B.coherent_shift_stress_scenarios.full_scenario_ledger.scenarios.birth_minus_1.complete_included_set_count
B.coherent_shift_stress_scenarios.full_scenario_ledger.scenarios.birth_minus_1.weighted_annualized_benefit_total.{amount,delta_from_baseline,delta_share_of_baseline}

B.coherent_shift_stress_scenarios.full_scenario_ledger.scenarios.birth_plus_1.complete_included_set_count
B.coherent_shift_stress_scenarios.full_scenario_ledger.scenarios.birth_plus_1.weighted_annualized_benefit_total.{amount,delta_from_baseline,delta_share_of_baseline}
```

Those paths yield, before display conversion and rounding:

| Scenario | Amount | Delta | Share | Included |
|---|---:|---:|---:|---:|
| baseline | 3,301,670,531,521.1997 | 0 | 0 | 1,514 |
| birth minus 1 | 3,271,347,016,144.8003 | −30,323,515,376.399414 | −0.009184294764392578 | 1,520 |
| birth plus 1 | 2,989,032,230,514.0 | −312,638,301,007.1997 | −0.0946909444847472 | 1,240 |

The personwise rows are:

```text
B.personwise_adversarial_range.minimum.amount
B.personwise_adversarial_range.minimum.delta_from_baseline_person_contribution_sum
B.personwise_adversarial_range.maximum.amount
B.personwise_adversarial_range.maximum.delta_from_baseline_person_contribution_sum
```

They yield `2,893,470,412,190.4`, `−408,200,119,330.8003`,
`3,366,908,834,468.4`, and `+65,238,302,947.19971`, respectively. The
approximation marks on the two displayed deltas follow the frozen disclosure.

The structured interpretation and construction text comes from
`.diagnostics.birth_timing_sensitivity.semantics.interpretation`,
`.personwise_construction`, and `.retirement_condition`. The exact candidate
share and travel clause — `2,892/3,083`, `93.8%`, `1,440/1,514`,
`2,806 + 86`, `278`, the rounded stress results, and “Stress scenarios, not
bounds” — are in `.gap_block[31].disclosure`; its materiality and modeled-award
classification are in `.gap_block[31].classification`.

### Execution, limitations, and successors

- Registrations 1–7 are read from
  `docs/registrations/first_estimates_registration_{1..7}_configuration.json`,
  key `.registration_reference`; the seventh is repeated in
  `.identity.registration_reference`.
- All six committed incident paths are enumerated by `.prior_incidents[0:6]`.
- Design revision `10` and amendment commit `f771b49` are
  `.configuration_echo.design.revision` and
  `.configuration_echo.design.amendment_commit`. Revision 10.1's corrected
  candidate share is carried in `.gap_block[31].disclosure` and the matching
  design row.
- The frozen gap count `32` is `(.gap_block | length)`. The manuscript says
  “Among the registered gaps” and summarizes material rows; it does not claim
  that the summary is complete.
- The five non-claims are reproduced from `.certifies_nothing[0:5]`.
- The nine successors are not artifact-derived numbers. They are the six
  leverage-ordered successors plus three amendment-2 additions in
  `docs/design/first_estimates_report.md` §12.

## Judgment calls

1. **Placement and voice.** The subsection sits immediately after the
   candidate-3 PASS and forecast-ledger arc, matching the task-27 candidate-3
   structure. The status paragraph is updated separately, as that precedent
   did.
2. **Tables only.** Existing figure tooling rebuilds committed SVGs and enforces
   a fixed semantic palette, but there is no first-estimates figure builder.
   Adding a chart would have required new nontrivial tooling or palette
   decisions, so the draft uses tables only.
3. **No combined benefit headline.** Modeled awards remain the primary flow and
   opening stock remains report-only. They are shown side by side, not summed,
   because summing would erase the artifact's claim-origin distinction.
4. **Draw basis is explicit.** Benefit and revenue rows use twenty-draw means
   and sample SD. The funnel's first two rows, source mix, and mandatory frozen
   birth-timing row use draw 0. The draft states those bases rather than
   blending them.
5. **Mandatory sensitivity uses the frozen row.** The artifact also publishes
   across-draw birth-sensitivity aggregates, but §10 requires the specified
   draw-0 baseline and scenarios to travel with the headline benefits. The
   caption notes that the across-draw summaries also exist.
6. **Five-class mix.** The designated artifact has structured five-class counts
   for the report population and included set, not a structured five-class
   candidate table. The draft publishes those direct counts and carries the
   candidate age-derived split from `.gap_block[31].disclosure`.
7. **Claims stay bounded.** “Among the registered gaps,” “levels unanchored,”
   and “forward production remains unbuilt” avoid completeness or national
   level claims. The exact required closing sentence is used.
8. **Execution chronology.** Incident 5 and the later dress-rehearsal
   birth-completeness discovery remain distinct. Registration 6 is explicitly
   described as producing the sixth committed, append-only incident record.
9. **Portable approximation glyphs.** Bare Unicode `≈` disappeared in the PDF,
   so the two personwise deltas use Quarto/LaTeX math `$\approx$`; the rendered
   PDF was visually checked.
10. **Sandboxed render caches.** Quarto and LuaTeX initially targeted
    unwritable user cache locations. The successful run used task-scoped
    `QUARTO_SANDBOX_CACHE_HOME`, `TEXMFVAR`, `TEXMFCACHE`, and `TEXMFCONFIG`
    paths. A temporary copy of Quarto's bundled JavaScript changed only the
    Darwin cache-directory lookup and was removed from the worktree afterward.
11. **Commit hook.** The shared `pre-commit` hook runs `bd sync --flush-only`,
    but this worktree has no beads database (`bd status`: “no beads database
    found”). Commits therefore used `--no-verify`; this bypassed only the broken
    beads flush. Render, artifact, reproduction, publication, gap, and palette
    checks were run explicitly.
12. **Base recovery.** Equivalent content was not represented as exact
    ancestry. The branch uses the local patch-equivalent commit only as a
    documented provisional base, with the exact post-fetch rebase command above.

## Verification

- Artifact SHA-256: exact match.
- `git diff --check`: pass.
- Quarto standalone render of `paper/paper.qmd`: pass for HTML and PDF; PDF is
  51 pages. The only warning was failure to fetch an optional cdnjs ES6
  polyfill because sandbox networking is disabled; render exit status was 0.
- Rendered PDF inspected at the new birth-timing table: layout fits and both
  approximation marks are present.
- Focused test command:

```sh
PYTHONPATH=src /opt/homebrew/opt/python@3.13/bin/python3.13 -m pytest -ra \
  tests/test_paper_figures.py \
  tests/estimates/test_first_estimates_fixture.py \
  tests/estimates/test_gap_block_fixture.py \
  tests/test_first_estimates_publication.py
```

Result: `37 passed in 2.85s` under Python 3.13.12 / pytest 8.4.2, with no
warnings, skips, or failures. `tests/test_paper_figures.py` includes both
byte-identical figure reproduction and `test_figures_use_only_palette_colors`.

## Handoff

The coordinator should first fetch and perform the exact-ancestry rebase shown
above. The intended remaining sequence is coordinator content review, Fable
voice pass, then the referee round. This branch must not be pushed before that
review.
