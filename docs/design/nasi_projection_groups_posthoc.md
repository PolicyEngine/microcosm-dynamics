# NASI projection group breakdowns: exercises 1 and 3

Package G4a implements the 2026-10-01 NASI follow-up request for group
breakdowns of the completed COLA and FRA-68 projection tests. This is a
methodology specification for a new registration on issue #42. Every
real-data output must carry the original test labels plus **registered,
one-shot, post hoc, not blind** and **report-only**. The development outputs
carry **INVENTED DATA - NOT A COMPARISON**. No comparator value is read, no
acceptance gate is added, and no real-data group output was produced while
building the package.

The existing registered specifications remain the authorities for the
projection and benefit mechanisms:

- Exercise 1: `docs/design/urban2010_cola_comparison.md`,
  `cola_track_a/runner.py`, and
  `runs/replication_urban2010_cola_v1.json`.
- Exercise 3: `docs/design/urban2010_fra68_comparison.md`,
  `fra68_track/runner.py`, and
  `runs/replication_urban2010_fra68_v1.json`.
- G1: `cohorts/group_attributes.py` for person attributes and its pinned
  category schemes and reader provenance.
- G2: `estimates/lifetime_measures.py` for every lifetime measure.
- G3: `estimates/group_breakdown.py` for every group assignment and cell,
  including the MINT8 schemes, definitions, uncertainty and suppression.

Paths to source modules above are relative to `src/populace_dynamics/`.
The MINT8 labels and definitions come from the source captures already
pinned by G3; this package does not capture another source or implement
another lifetime measure. The canonical User Guide capture is
`data/external/mint8_table_user_guide.source.html`, certified 2026-04-01;
the canonical labels-only artifact is
`data/external/mint8_row_categories.json`. Their provenance records
preserve the hashes and acquisition records of all three original
copies. The guide's main-content bytes are identical across the
2025-10-01 and 2026-04-01 certifications, and all three original label
files were byte-identical. G1, G2 and G3 use these same canonical pins.

## Frozen replay and the reproduction gate

`group_breakdowns.cola.reproduce_cola` replays R0-R6, and
`group_breakdowns.fra68.reproduce_fra68` replays F0-F8. The populations are
unchanged: the 2011-wave opening cohort for R0-R5/F0-F7, and the 2009-wave
opening cohort for R6/F8. Each population is projected once per registered
draw, using the frozen `_project_population`. All of its rows share that
projection. Exercise 1 calls the frozen `StateLookups` and
`reference_benefit_rows`; exercise 3 calls the frozen scenario calculators
and `union_benefit_rows`. The frozen runners' guards, five-age-group
statistics, draw diagnostics, counters, membership diagnostics, floors and
provenance remain part of the replayed result.

The replay returns a frozen `ProjectionReplay` containing the aggregate
result, the already-computed benefit rows by registered row, and the final
projected state by anchor wave. Retention adds no group attribute and
computes no group cell. Its frames stay in memory; person rows are not
serialized into the output artifact.

`ProjectionReplay` also seals every retained benefit and state frame when
constructed. The SHA-256 covers column order, dtypes and CSV values,
including the component mappings. The reproduction gate refuses any later
mutation before calling a loader or tabulator and records the retention
seal on success. An aggregate match therefore cannot certify person rows
that were altered after the frozen calculation.

`common.verify_reproduction` compares **every field returned by the frozen
runner** against the corresponding field in the committed parent
artifact. The entry script's wrapper fields, such as wall-clock run times,
are outside that runner result. Nested mappings, sequences and scalar
values must match as canonical JSON, with **absolute tolerance 0 and
relative tolerance 0**. This includes all five age cells and every draw's
diagnostics. No floating summation tolerance is proposed in this version.
The check records the verified fields, row manifest, comparison rule and
SHA-256 of the matched canonical payload. A failure reports a field path
without printing outcome values.

On any mismatch, the adapter raises `ReproductionMismatch` before calling
a G1 attribute loader, G2 lifetime measure, G3 group assignment or G3 cell
tabulator. No artifact or environment sidecar is written. An invented test
changes a committed-cell stand-in and verifies both that the attribute
loader is never called and that neither output file is created. This
ordering is binding even if the real-data replay fails because the host
environment or frozen code no longer reproduces the original result.

The frozen replay uses the original parent's registration pointer so that
its result can match the original registration metadata exactly. The
new issue #42 pointer authorizes the post hoc group calculation and is
recorded separately on the new output. The old pointer alone does not
authorize a real-data group run.

## Person attributes and current-law benefit type

After the reproduction gate succeeds, G1 supplies a side frame for every
opening person, joined by `person_id`. Its labels are translated to the
codes of G3's existing MINT8 dimensions; no category label is invented.
The frame must retain each requested person exactly once and must match
its recorded content seal when present. The output carries G1 provenance.

Race and ethnicity and country of birth use G1's documented resolution of
its head/spouse reports. Education uses G1's anchor-wave cutoff, separately
for each population. Missing reports and unresolved placements, including
G1's treatment of U.S.-territory births, remain unclassified. There is no
imputation or guessed category.

Sex and marital status come from the retained reference-year projected
state, joined on `(draw, person_id)`. Age is reference year minus birth
year. The projection carries opening divorced and never-married statuses
forward and changes married to widowed when its existing linked-spouse
mortality mechanism requires it. Its default opening specification treats
separated people as married; the separate original separation flag is not
retained in `TrackACohort`. Therefore this analysis **inherits that frozen
married treatment**. A literal `separated` code, `unknown`, or
`no_marriage_history` is unclassified. This is a disclosed projection
convention; MINT8 does not supply a placement rule for separated people.

Current-law benefit type uses the positive baseline amounts in the frozen
`benefit_components` mapping:

| Positive baseline components | MINT8 category |
|---|---|
| Aged or disabled widow component, with or without an own-worker component | Widow(er) (includes dually entitled) |
| Spouse excess component, with or without an own-worker component | Spousal (includes dually entitled) |
| Retired worker component alone | Retired worker only |
| Disabled worker component alone | Disabled worker only |

A baseline nonrecipient is unclassified for current-law benefit type.
Concurrent spouse and widow components, unknown components, or concurrent
retired and disabled worker components are refused. No alternative
entitlement mechanism is inferred from the group labels.

The closed projection does not calculate household income or an official
poverty measure. Current-law poverty status, current-law household income
quintiles, household income statistics and official poverty statistics are
explicitly **not computed** with that reason. Their missing group inputs
remain unclassified; they never become zero income or above-poverty codes.

## Lifetime dimensions and their limitations

The annual MINT8 beneficiary scheme has no lifetime-earnings dimension.
This report appends G3's three MINT8 cohort-table dimensions: current-law
initial AIME quintile, lifetime payroll tax quintile, and lifetime payroll
tax quintile (shared). The result is labeled as a composite scheme, not
presented as an unchanged SSA annual-table layout.

Every measure calls G2 over the existing cohort careers, cut at the
opening year: 2010 for the 2011 wave and 2008 for the 2009 wave. No earnings
are projected or added. Initial AIME calls `initial_aime_at_62` with the
explicit `mint8_initial_aime` convention: statutory computation years and
a last-earnings-age cutoff of 61, also capped at the opening year. G2
identifies younger persons' values as provisional through the last
observed year and exposes truncated-history flags. These opening-career
measures do not establish a fully observed lifetime history for younger
members of the closed cohort. The output carries the supplied parameter
revision, source/input/output hashes and G2 coverage flags.

Own payroll-tax present value calls G2 with
`TaxRateBasis.EMPLOYEE_EMPLOYER_PAID`: combined OASDI taxes actually paid,
including the effective employee reductions in the captured credit years,
rather than general-revenue reimbursements to the trust funds. G2 applies
the contribution and benefit base and its explicit end-of-year timing,
valuing each year's tax at age 62 with the captured trust-fund interest
rates. The source loaders enforce their inherited SHA-256 pins. No future
interest rate is invented or silently extended; a person needing a rate
outside the captured coverage is not computed under
`MissingRatePolicy.NOT_COMPUTED`.

Shared taxes call the same G2 present-value function with an already-loaded
marriage-episode frame. Taxes paid while married are shared equally using
G2's stated convention; unmarried years retain own taxes. The adapter uses
`MissingSpousePolicy.NOT_COMPUTED`. Missing marriage histories are not
interpreted as never-married: those persons' shared values are excluded
from classification and their unavailable count is recorded separately,
without mutating G2's measure frame or provenance. If no episode loader is
supplied, the shared dimension is not computed for that reason. Real-data
history loading remains in cohort code; measure and tabulation code never
open PSID files.

Quintile thresholds are computed once per dimension and **ten-year birth
cohort of the entire opening population**, with opening weights, by G3's
weighted-percentile rule. Ties use that rule, including its midpoint at an
exact cumulative-weight tie. The resulting category is fixed by
`person_id` across registered rows, projection draws, scenarios and
population variants. A survivor subset is not re-ranked. Missing measures
remain unclassified. Labels retain G3's MINT8 order: Highest, Second
highest, Middle, Second lowest, Lowest.

## Populations, statistics and disclosure

Each registered row has two separately labeled variants:

| Variant | Population |
|---|---|
| Test population | Persons alive in the reference year with a positive frozen benefit in either scenario; the original row's scenario membership rules are retained |
| MINT population | The row's current-law beneficiaries aged 60 or older in the reference year, with positive baseline benefit |

For exercise 1, the frozen rows have positive benefits in both scenarios.
Exercise 3 retains the union and its registered scenario-specific membership
differences. The age threshold is an additional report population filter;
it does not change the replayed five-age-group parent cells.

G3 computes every reported cell. It reuses the existing A7 ratio of
scenario means, the mean of individual ratios, registered draw dispersion
and floor conventions. It also reports the MINT8 benefit statistics:
percent with a decrease of at least 1 percent, percent with an increase of
at least 1 percent, the unaffected remainder, and the weighted 10th,
50th and 90th percentiles of each individual's percent change relative to
current law. The MINT change statistics use current-law recipients with a
positive selected baseline benefit. Empty or undefined statistics remain
explicitly undefined.

Within each variant, G3 computes the family-unit half split once on its
full input frame and intersects that split with each group. It never
re-splits a group's subset. G3 reports unweighted sample sizes, the
under-100 SSA flag, the under-30 flag, numerator flags, uncertainty and
unclassified counts. If any category in a dimension is below SSA's
disclosure minimum, the **whole subgroup** is flagged suppressed. Cells
remain in this research artifact with their flags; no small row is silently
dropped.

## Entry points, artifacts and permitted verification

`scripts/run_projection_groups_registered.py` selects one exercise and
requires a new issue #42 comment URL, a full 40-hex registered commit equal
to HEAD, a clean tree, the ratified frozen specification, and a new output
pair. It imports the Track A `_environment` resolver through `importlib`.
The real input builder reproduces the frozen cohort/parameter construction;
recorded PSID hashes and frozen output values are verified before groups.
The entry script also pins this methodology specification.

There is **one artifact per exercise**. This preserves independent parent
identities, row manifests, source specifications and one-shot registrations
and makes a failed reproduction of one exercise unable to certify the
other. Each output is a new `runs/<name>_groups_posthoc_v1.json`, with an
exclusive-created `.env.json` sidecar. Both files are created only after
the full replay and group computation succeed. The prior committed run
artifacts are read-only and are never rewritten.

`scripts/projection_groups_dry_run.py` runs only the inherited invented
cohorts and supplied invented group reports, rates and interest factors.
Its artifacts go under
`docs/analysis/nasi_group_breakdowns_invented_20261001/<test>/` with the
invented-data header. These runs verify mechanics and do not compare any
model outcome to DYNASIM or SSA policy-option values.

`scripts/make_nasi_repro_venv.sh` builds the reproduction environment from
the versions recorded in the parents' environment sidecars, with an
editable install. Reproduction requires the existing policyengine-us
checkout at revision `a03e82e503`, selected by
`POPULACE_DYNAMICS_PE_US_DIR`, and the original PSID file hashes. Building
the environment is permitted during development; running a real-data
entry point to produce group cells is deferred to the new registration.

Development verification is targeted and invented-only: adapter
comparisons with both frozen runners, property tests for row/draw
selection, joins and classification invariants, the mismatch-before-loader
and no-write test, and entry-point guard tests. Run only one pytest process
at a time. Black at 79 columns and Ruff apply to the new Python files.

No existing frozen engine, Track A, FRA68, SS or A7 module is edited. No
new branch or worktree is created; changes stay uncommitted in the assigned
`nasi/g4a-projection-groups` worktree for the orchestrator. The integrator
alone updates `POST_REVIEW_SOURCE_EXCLUSIONS` in
`scripts/first_estimates_birth_evidence.py`, its corresponding artifact
test, `tests/tier_counts.json`, and any required development extras in
`pyproject.toml`. New source modules and test modules with tiers are listed
in the package's final report.
