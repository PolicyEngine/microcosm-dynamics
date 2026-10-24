# Registration 18: A-COLA implementation

This is the microsimulation build for decision d658 and milestone F0 of
the mortality, groups and financing design (#558, approved revision
`2c19f5b6`, decision d1922). Registration 18 is the specification:
<https://github.com/PolicyEngine/microcosm-dynamics/issues/42#issuecomment-5919983573>.
`acola_registration18.md` preserves its posted bytes, SHA-256
`02287d54f12285c8dffcb94ba7dae9cbe3cc34ba338c602a5ad4afe14d598f20`.
The binding check records d658's authorization rather than applying A7's
ratification-wording test. This build authorizes no population run.

The local build instructions are the cleared
`EV/acola-builder-brief-cleared-20260930.md`,
`EV/acola-build-20260930/stage2-brief-20261024.md` with its erratum
`EV/acola-build-20260930/stage2-brief-20261024.erratum.md`, and, for
this blind replay of the stage-2 builder's tree,
`EV/acola-build-20260930/f0-blind-replay-brief-20261024.md`. EV denotes
`/Users/maxghenis/microcosm-launch-evidence/dynasim-parity-20260909`.
PSID use follows the project's data-access record. Tests use invented data.

## Implementation map

All package paths below are under `src/populace_dynamics/acola_track/`;
test paths are under `tests/acola_track/`.

| Registration element | Implementation | Tests |
| --- | --- | --- |
| Independent registry, R0 population, five components, labels, report-only status | `config.py`: `ACOLARow`, `REGISTERED_ROWS`, `ACOLAConfig` | `test_config.py`, `test_unchanged.py` |
| C0: 2027, eligibility clock, calendar payments, L | `config.py`, `runner.py`: `run_acola` | `test_config.py`, `test_timing_properties.py`, `test_runner.py` |
| C1: December 2030 monthly amount times 12 | `config.py`: C1 | `test_timing_properties.py` |
| M0: 2011; M1: 2010; M2: December; M3: entitlement; M4: completed start-year age | `config.py`: M0–M4 | `test_config.py`, `test_timing_properties.py`, `test_runner.py` |
| C0-D: mechanism D, deferred | `config.py`: `DEFERRED_ROWS`; `runner.py` artifact | `test_config.py`, `test_runner.py` |
| Twenty draws, seeds 5200+k, one shared projected state per draw | `runner.py`: unchanged Track A projection helpers and `reference_benefit_rows` | `test_runner.py` |
| All-ages T_base/T_reform and P; component totals; OASI/DI shares and P values; memberships | `statistics.py`: `summarize_cost`, `_cost_cell` | `test_statistics.py` |
| Spouse-on-DI weighted counts and annual dollars, both scenarios and three classes | `runner.py`: `spouse_worker_class`; `statistics.py`: `_cost_cell` | `test_runner.py`, `test_statistics.py` |
| MINT Total 62+, 62–69, 70–79, 80–89, 90+; all three estimands and three memo statistics | `statistics.py`: `summarize_mint`, `_mint_cell`, `weighted_median` | `test_statistics.py` |
| Draw means, sample SD (ddof=1), five family-half floors | `statistics.py`: `_summary`, `_summarize` | `test_statistics.py` |
| N, N_model, N_MINT and M1 null, provenance and model-null gaps | `nulls.py`, `runner.py`: `_add_null_gaps`; `scripts/build_acola_spec_only_nulls.py`; `acola_spec_only_nulls.json` | `test_nulls.py`, `test_runner.py` |
| Unscaled 2030 beneficiary-count context | `nulls.py`: `extract_context_count`; `runner.py` | `test_nulls.py`, `test_runner.py` |
| REFUSE, no-drop refusals and null serialization | `runner.py`: `_check_floor`, refusal records; `statistics.py`: `_refused_cell` | `test_runner.py`, `test_statistics.py` |
| Exact pointer, SHA, HEAD, clean tree, specification and one-shot output guards; artifact and environment hash sidecar | `scripts/run_acola_registered.py`: `preflight`, `write_artifact` | `test_registered_run_script.py`, `test_runner.py` |
| OACT/PWBM conversion, precision branches and four-corner intervals; MINT S/L readings, headline choice, gaps and metadata; seal and sidecar verification; JSON and Markdown | `scripts/compare_acola.py` | `test_compare.py` |
| Historical mechanism-L equivalence and delayed-credit disclosure | `scripts/acola_mechanism_l_equivalence.py`, historical golden and provenance | `test_mechanism_l_equivalence.py`, `test_delayed_credit_disclosure.py` |
| Independent TR 2026 COLA cross-check | `nulls.py`: capture extractor; `data.tr2026.cola_path(2027, 2029)` | `test_tr2026_crosscheck.py` |

The runner composes `TrackAConfig(rows=("R0",))` to select the population
and projection, and constructs public `RegisteredRow` instances outside
the legacy registry. It never calls `run_track_a` with A-COLA row IDs.
`cola_track_a`, `scenario_benefits.py`, the A7 tabulator, Track A v2,
FRA 68, the oracle, claiming and the shared engine remain unchanged.
New source files are enumerated individually in the birth-evidence
post-review exclusions and its exact-tuple and reachability tests.

## Mechanism preservation evidence

The requested `dd222b9..origin/master` check at master `2195258c`
(repeated at `f8ffc7d9`, with the same result)
found only two added files among the mechanism paths:
`engine/forward_earnings_s1_v1.py` (297 lines) and
`ss/statutory_delayed_credit.py` (125 lines). No existing file changed.
The A-COLA build edits none of those paths.

`scripts/acola_mechanism_l_equivalence.py` uses only legacy interfaces
present at both revisions. Its seed 20261024 supplies fixed invented
careers and projected states, including every birth cohort 1917–1942
claiming after FRA, dually entitled spouses, DI, conversion, survivors,
opening components and recent eligibility boundaries. All seven runnable
rows have 69 beneficiaries, giving 483 row/person records with baseline,
reform and component amounts. Their canonical JSON is bit-identical
between the registered source and current working source. The golden
`tests/acola_track/mechanism_l_dd222b9.json` has SHA-256
`07c59d69544503f87b43e8be5df57f01d773f597aa52b8f4027f40f7f9cc87de`.
Its adjacent provenance file pins the script, all imported historical
source files and exact commands. Any future difference raises
`REG18_MECHANISM_DRIFT` with row/person identifiers.

The registered side ran in a temporary `git worktree` of
`dd222b9af926c773a0f92732e2d08be507793378`, placed inside the clone and
removed afterwards, with the clone's venv and `PYTHONPATH` set to that
worktree's `src`. Every imported `populace_dynamics` module (117 files)
resolved inside the worktree. The build side ran at commit `a3806e56`
with `PYTHONPATH` set to the clone's `src`, importing the same 117 files,
whose SHA-256 is unchanged between the two commits. Both runs wrote
output byte-identical to the golden file. The provenance file records
the commands, both commits, the script and output hashes, the imported
files and the stage-2 builder's earlier export record. That builder's
sandbox could not create the worktree, so it had run the registered side
on a `git archive` export of the same 117 files, with the same result.
The golden was never regenerated from the current source.

## Arithmetic and invariants

P follows v2's operation order, `100 * (T_reform / T_base - 1)`.
Component accounting and the OASI/DI decomposition are checked per draw:
component totals sum to T_s; T_base equals its OASI and DI parts; and P
equals the baseline-share-weighted P_OASI/P_DI where both denominators
are positive. A zero component denominator makes that component's P
undefined, rather than zero. The decomposition is not asserted for
unweighted averages of draw-specific shares. Differential tests compare
P with v2's all-alive weighted-total cell, means with A7, and floors with
A7's convention. Equal scenario memberships imply identity of P and the
ratio of means, subject to floating arithmetic tolerance.

The weighted median uses the midpoint at exactly half the weight, with
exact `Fraction` representations of supplied binary-float weights.
Property tests cover permutation invariance, ordinary medians with equal
weights, range bounds, exact and near-half ties, and zero-weight handling.
Floor splits use the whole emitted normalized row table, with each opening
family assigned by the unchanged Bernoulli(0.5) splitter for seeds 0–4.
Every statistic and age band of a row therefore uses the same split.
Each side computes the mean across draws before its absolute gap is
taken. Fewer than two usable seeds gives a null floor and reason.

Zero reform makes all change statistics, falling shares and nulls zero;
benefit-level medians remain positive and equal. Seed determinism,
permutation invariance, shared draw states and the exact legacy source
pins have tests. Empty bands and refused draws serialize with
`allow_nan=False`, null values and reasons; valid draw results remain
visible when another draw refuses. No missing configured projection draw
can silently become an empty completed draw.

For an ordinary worker, dime flooring at each increase and after the
claim factor requires a benefit-level-dependent allowance for accumulated
rounding losses. Tests derive the allowance from monthly dime losses,
the number of increases and the actual baseline benefit. Common AIME
dollar rounding does not create a scenario difference. Intact opening
benefits are not dime-floored by default. Dual entitlement creates a
separate structural exception: a cut to the claimant's own full PIA can
increase the spouse excess by more than the loss in the age-reduced own
benefit. Thus individual benefits and P can rise under a cut; intended
bounds and monotonicity have an explicit tested exception, without a
universal rounding tolerance. The registered arithmetic is preserved.

The first-year tests exercise the actual legacy emitter with determination
years 2010, 2011 and 2027, both payment periods, and eligibility in 2008,
2010, 2011 and 2027–2030. In particular C0 carries 3, 2, 1 and 0 reduced
increases for eligibility in 2027, 2028, 2029 and 2030; C1 carries one
additional increase. C1 and M2 read payment year 2031, which is covered by
the baseline's determination-year 2030 rate. Registered model rates are
2.8% in every reduced year, leaving a strictly positive 1.8% reform rate.
The floor guard is stricter than REFUSE (strict positivity rather than
nonnegativity), and REFUSE cannot intervene for the registered rate path.

Comparison arithmetic uses `Decimal` for printed and stored decimal
strings. Four-corner tests check containment, monotonicity and positive
denominators; interval subtraction is `[a,b]-[c,d]=[a-d,b-c]`. Seal files
are checked before comparison, and the artifact is checked against its
sidecar. No acceptance threshold, pass band or verdict is computed.

## Disclosures for the second registration comment

The following choices and retained limitations must be disclosed before
the population run, together with the registered commit and exact command.

1. Scenario means and benefit-level medians use the scenario-specific
   positive-benefit sets S_base and S_reform. Individual percent-change
   medians use their intersection with positive baseline benefits S_alt.
   A benefit present in only one scenario enters only that scenario's
   mean or level median; the falling share uses baseline recipients.
   Its output unit is a fraction of baseline beneficiary weight.
2. Spouse amounts, including opening-stock amounts, are classified by
   the living 2030 worker in `spouse_person_id`: entitled, unconverted DI;
   another worker; or unclassified if no living link exists. Counts and
   annual dollars are reported in both scenarios. Spouse remains an OASI
   component even when its linked worker is on DI (ruling 4).
3. The legacy emitter drops a spouse or widow excess with zero baseline
   excess even if its reform excess is positive. This pushes P away from
   zero. No public counter exposes dropped cases; the artifact reports
   that counting is unavailable without copying private arithmetic or
   changing a shared module. The arithmetic is unchanged (ruling 5).
4. Under L the two positive-benefit sets are equal by construction: the
   emitter retains positive baseline benefits, refuses nonpositive reform
   totals, and sets both flags true. Equal counts are not evidence of
   independently equal membership (ruling 6).
5. Weighted medians exclude zero weights and report the exclusions;
   comparisons to W/2 use exact fractions of the supplied floats. Sorting
   is by value, then person ID. An exact W/2 tie takes the midpoint with
   the next positive-weight observation (ruling 7).
6. A7's public tabulator is bypassed. Intermediate mean-benefit values
   not registered as statistics are under `not_registered`; no
   unregistered mean of individual ratios is published (ruling 8).
7. The binding check pins the verbatim specification's SHA-256 and d658's
   authorization; it makes no ratification claim (ruling 9). The entry
   script pins the first comment's exact URL. The launcher records the
   second comment and enforces waiting for it (ruling 10).
8. C1 and M2 include the December 2030 increase, whereas the registered
   nulls stop at determination year 2029. No December-specific null is
   computed (ruling 11).
9. Weight variation is reported across draws over everyone alive in at
   least one 2030 state. This diagnostic is not limited to emitted
   beneficiaries (ruling 12).
10. C0-D remains registered but deferred. It runs after Track A v2's own
    real-data artifact is committed to master, at a commit registered by
    a further issue #42 comment. If run after publication of the primary
    comparison, it is labelled "registered before the comparator was
    public, run after it" (ruling 13).
11. Coordination checks list open PRs before work and at close-out.
    Only exclusion and tier bookkeeping shared files change; protected
    benefit modules are not edited (ruling 14).
12. The annual convention omits family maximums, earnings tests,
    recomputation and payment-month timing. The closed population omits
    children, later immigrants and post-2010 earnings; disabled widow(er)s
    enter only as opening stock. Benefit-only cost, baseline vintage,
    timing and auxiliary limitations remain named gaps. No adjustment or
    scaling is applied (ruling 15).
13. Undefined bands, floors and refused-draw values are null with reasons.
    A refusal preserves valid per-draw results but makes a summary that
    requires every draw undefined. Empty completed draws have zero
    totals and undefined ratios. JSON forbids NaN (ruling 16).
14. The zero-reform invariant concerns changes and falling shares;
    baseline/reform median benefit levels remain equal and positive.
    P uses `100*(T_reform/T_base-1)`, matching v2's operation order.
    Floors split every emitted row, including beneficiaries under 62.
15. Dual-entitlement spouse arithmetic can raise individual and aggregate
    benefits under a cut and violate the intended bounds and monotonicity.
    Worker-path bounds instead allow propagated dime losses plus the
    final claim-factor dime floor, scaled by that person's benefit level.
    No universal tolerance is asserted for dual entitlement.
16. MINT reading S uses the shortest decimal representation of the stored
    double, shifted two places for a percent format. Both half-up and
    half-even rounding are checked against the HTML precision, and the
    matching modes are reported. If either mode matches and the stored
    value has more decimals, the XLSX branch applies; otherwise HTML
    applies. Literal reading L is a sensitivity only. The sealed record
    supplies median type, start-date interpretation, timing and flags;
    the build never substitutes constants for them. Unknown fields are
    reported as unknown. The v1 schema defines no numeric split extension:
    if a record asserts an OASI/DI split, its raw fields are retained with
    an explicit schema limitation rather than guessed field mappings.
17. Mechanism L reaches `claiming.benefit_factor` at
    `src/populace_dynamics/cola_track_a/benefits.py:345` (the same line at
    `dd222b9`) for every retirement claimant's worker record. Its call to
    the sealed oracle retains the legacy 48-month delayed-credit cap for
    births 1917–1942. The cap also reaches an aged widow(er)'s benefit
    through the deceased worker's record, whose factor enters
    `widow_benefit_path` as `deceased_claim_age_factor`. A registered run
    carries the cap because it refuses parameters that differ from the
    committed statutory capture, which sets 48 months. R0's population
    can retain these people through 2030. The statutory window,
    `840 - FRA` months, is longer for those cohorts: 60 months at FRA 65,
    falling to 50 for births in 1942. Registration 18 keeps L and
    discloses the cap rather than changing the registered mechanism.
    See `docs/errata/2026-10-11-delayed-credit-window.md` and
    `docs/design/d1408_delayed_credit_diagnostic.md`, decision d1408.
    The new tests use invented people only; no d1408 script is run.
18. N uses the Table V.C1 COLA column, intermediate rows 2027, 2028 and
    2029, each 2.4%, effective December of its determination year. Source:
    <https://www.ssa.gov/oact/TR/2026/V_C_prog.html#1047210>.
    File: `data/external/snapshots/tr2026_v_c1_vintage1/trustees2026_v_c1_table.html`.
    SHA-256: `4d29f2b85d67b995eea25f0bdfb46b3755671c082d75a9855680836d4b80c46a`.
    Column: `Cost-of-living benefit increasea (percent)`.
    The preserved timing footnote says December after 1982. The capture
    is the exact table fragment from the chapter, with a separately
    preserved timing note; the rest of the chapter is not stored.
    The URL was located through the Report's List of Tables. No CPI
    fallback is used. `data.tr2026.cola_path(2027,2029)` is checked against
    these three captured COLAs without printing any other accessor value.
19. N_model uses the model's TR 2008 ultimate annual-average CPI, 2.8%
    in 2027–2029. N_MINT uses TR 2008 V.C1 through 2017 and ultimate CPI
    thereafter, 2.8% in every 2011–2029 year; M1 adds 2010 at 2.8%.
    N minus N_model therefore compares printed TR 2026 COLAs against
    the model's derived TR 2008 ultimate-CPI continuation.

The pre-run nulls in percent units are N = -2.9011704027652740478515625,
N_model = -2.8899919721197439019598290221155817992219312710473,
N_MINT = -16.950197597259551155011310281830073286124621211173 and
M1 = -17.758075052539127505643495979477640666609790265539.
Their exact rational values, factor counts (3, 3, 19, 20), input rates,
source files and hashes are in `acola_spec_only_nulls.json`.

## Review and release

The build is WIP until independent review and the coordinator's tier-count
slot. Do not merge. The coordinator lands this after independent review
and the tier-count slot. The run artifact later receives its own review
and CI cycle before any comparator seal is opened.
