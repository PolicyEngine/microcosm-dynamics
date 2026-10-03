# G2 lifetime measures for NASI group breakdowns

`populace_dynamics.estimates.lifetime_measures` computes pure measures
over already-built cohort frames. It opens no PSID file and performs no
real-data tabulation. Development and validation use INVENTED careers.
Any real-data group outcomes require the separate issue #42 registration.

## Inputs and results

Careers have `person_id`, `year`, `earnings`, and optionally `provenance`.
There must be one row per person-year, with finite nonnegative nominal
earnings. Persons have unique `person_id` and `birth_year`; other columns,
including sex, are accepted but not used. Marriage episodes use the
already-loaded cohort marriage-episode schema, optionally including
`separation_year`. No reader is added.

Each measure returns a frozen `MeasureResult(measure, frame, provenance)`.
The frame contains one row per supplied person, in supplied order, with
the value, `status`, `reason`, and coverage flags. Missing histories are
`not computed` with missing values; an observed zero is a computed zero.
SHA-256 provenance pins normalized input frames, supplied NAWI and wage
base schedules, and result frames. Payroll results also pin applied tax
rates and available required interest rates, including custom schedules.

## AIME conventions

`initial_aime_at_62(careers, persons, params, *, analysis_year, convention)`
requires an explicit `AIME_CONVENTIONS` entry or `AimeConvention`:

| Name | Computation years | Earnings cutoff |
| --- | --- | --- |
| `mint8_initial_aime` | Statutory 415(b) | Year of attaining 61 |
| `exercise_1_cola` | Legacy fixed 35 | Supplied career through analysis year |
| `exercise_3_fra68` | Legacy fixed 35 | Supplied career through analysis year |
| `exercise_4_min_benefit` | Statutory 415(b), old-age at 62 | Year of attaining 61 |

The statutory choice composes `ss.statutory_aime.oracle_aime`; the
legacy choice dispatches to the unchanged `ss.benefits.aime`. Track U
uses reported benefits and has no AIME oracle convention. The Track M
choice matches an old-age entitlement at 62, not a worker's observed DI
or death-basis AIME. Statutory pre-1975 age-62 cases remain unsupported
and receive a reason rather than an invented formula.

People younger than 62 at the analysis year use earnings through that
year and are flagged `provisional_through_last_observed`. Earnings are
never projected. NAWI still indexes to age 60, so the caller must supply
that wage-index path. Left and right history censoring and imputed rows
are counted. `n_history_years_after_age_61` identifies legacy full-career
AIMEs containing supplied earnings after the initial-entitlement cutoff.

## Payroll taxes and age-62 present value

`lifetime_payroll_tax_pv_at_62(careers, persons, params, *, shared, rates,
interest, marriage_episodes=None, ...)` applies the combined employee
and employer OASDI rate to earnings capped at the contribution and
benefit base. Every supplied career year enters, including years after
62. A year's payment is valued at year end; reference year is birth year
plus 62. Accumulate with rates for payment year + 1 through reference
year, or discount with reference year + 1 through payment year.

The captured schedules supply two explicit tax bases. Default
`TRUST_FUND_RECEIVED` doubles SSA's employee/employer "each" rate.
`EMPLOYEE_EMPLOYER_PAID` accounts for the employee credits in 1984 and
2011–2012. Default interest is combined OASDI effective annual interest;
the annual average new-issue rate is an explicit alternative. These
choices, timing, self-employment treatment, and sharing conventions are
recorded as registered builder defaults for the downstream registration.
MINT's wording is taxes "paid": `EMPLOYEE_EMPLOYER_PAID` is the literal
interpretation in credit years. The default receipt basis includes general
revenue replacements in those years, so the downstream registration must
state its selected basis rather than claim those two bases are identical.

Shared taxes use the year-end marriage state from the unchanged cohort
helper. Over married years, each person receives half the sum of both
spouses' annual taxes, using the union of their career years. Missing
spouse careers use flagged `OWN_ONLY`, or `NOT_COMPUTED` if requested.
Absent individual years within an available career contribute zero and
are counted separately. Separated people count as married by default.
Unknown states, absent history-roster membership, overlapping marriages,
and disagreeing reciprocal spouse links are exposed in flags/defaults.
The latest-start marriage wins in overlaps; each person's recorded
history governs when reciprocal links disagree.

With reciprocal links, sharing conserves the couple's annual taxes.
Their two PVs conserve the total at the same reference date: same-birth
spouses can be added directly; different-age spouses must first be
valued at a common date. Disagreeing histories do not guarantee this.

Historical interest covers 1940–2025. Uncovered years refuse by default
or produce `not computed` if explicitly requested. Extend coverage only
with `TrustFundInterestRates.extended(..., source="named assumption")`;
there is no silently repeated future rate. Invalid rates fail explicitly.

## Report average and schemes

`report_average_indexed_earnings_22_62(careers, persons, params, *, shared,
marriage_episodes=None, conventions=None, ...)` follows the recorded
Butrica–Uccello measure: average wage-indexed earnings at ages 22–62,
uncapped for the own measure, including uncovered labor earnings.

The hash-verified cleared extract is
`exercise2-definitions-cleared-20260924.md`, SHA-256
`a3978b683b4275424b6d12e9fe45f021fae277ccf9731a7883952564b6ed0384`.
Own earnings are uncapped and include uncovered labor earnings (line 223).
Shared earnings assign half the couple's annual earnings while married
and own earnings otherwise (lines 66 and 223). Both average wage-indexed
earnings at ages 22–62 (lines 65–66 and 223), with **41 years for every
individual** (line 227). Default `REQUIRE_COMPLETE_AGES` preserves that
41-year divisor and returns `not computed` for incomplete supplied
histories; a missing year is never silently interpreted as zero. Default
`NOT_COMPUTED` also refuses unavailable married-year spouse earnings
or unknown marital states. Complete observed zero histories compute zero.

`COVERED_AGES` retains the earlier sparse-history average as an explicit
sensitivity, and `ALL_AGES` explicitly assigns zero to absent own ages.
`OWN_ONLY` explicitly retains the earlier missing-spouse treatment, with
missing spouse years counted. Each result records these departures from
the complete Report definition in `report_definition_departures`.

The extract leaves the wage-index base open. `report_nawi_index` and
`report_index_age` propose SSA NAWI to age 60 with later earnings nominal.
Other named builder conventions pending registration are
`report_year_end_marriage` (including separated as married),
`report_missing_earnings`, `report_missing_spouse`,
`report_missing_spouse_year`, `report_unknown_marriage`,
`report_history_roster` (provided roster gaps are unavailable; without a
roster the episode universe is treated as complete),
`report_spouse_history` (each person's own spouse links govern), and
`report_overlap_marriage` (latest-start marriage governs). The source
sharing formula and 41-year divisor are recorded definitions, not
builder defaults. No coverage or missing-earnings assumption is supplied
by the extract; incomplete records stay unavailable by default.

Exact Report race rows are White, non-hispanic; Black, non-hispanic;
Hispanic; Other (lines 58 and 86), with Other glossed as other minority
groups including Asian and Native American people (line 229). Exact
education rows are High school dropout; High school graduate; College
graduate (lines 59 and 87). Exact labor-force rows are Less than 20 years;
20 to 29 years; 30 to 34 years; 35 or more years (lines 60 and 88).
**Lines 231 and 327 explicitly say education and labor-force definitions
are not stated**. `report_education_mapping` and
`report_labor_force_experience` remain unavailable until registration:
no schooling boundary, some-college allocation, age window, earnings
threshold, or count of positive-earnings career years is invented.

Own/shared quintile labels are 1st Quintile through 5th Quintile (lines
61–62 and 89–90). `report_quintile_population` is unavailable (lines 231
and 327), and `report_quintile_order` and `report_quintile_ties` require
registration because the extract does not state direction or tie rules.
`report_marital_status_timing` is likewise unavailable (lines 231 and
327); this is distinct from the proposed annual shared-earnings convention.

`load_mint8_scheme()` reads the pinned category definitions for initial
AIME, own lifetime payroll tax, and shared lifetime payroll tax.
`quintile_cells(birth_years, scope)` exposes whole-population or ten-year
birth-cohort cells. `boomers2004_scheme()` retains the report's named
dimensions but refuses label order and quintile population until those
unrecorded conventions are specified. Scheme metadata does not authorize
a real-data run.

## Quintile invariants

`weighted_quintiles(values, weights, *, by=None, labels=QUINTILE_LABELS)`
returns categorical labels in MINT order: Highest, Second highest,
Middle, Second lowest, Lowest, followed by `not computed` for missing
values. Valued rows need finite positive weights and nonmissing cell keys.
Indexes must match; cells are cut independently.

Tied values stay together. Each tie group's weighted cumulative midpoint
determines its quintile. Exact fractional weight sums make the result
independent of row order. A midpoint within 1e-12 rank units of a boundary
takes the upper quintile, absorbing floating-point multiplication error
under weight scaling. Without ties, each quintile's deviation from 20%
is bounded by the largest row's weight share. Equal weights and a row
count divisible by five give exactly 20%. Higher values cannot receive
a lower quintile within a cell.

`quintile_summary` retains empty categorical quintiles as zero-case rows.
The `not computed` row is a coverage diagnostic; exclude it when applying
SSA's suppression rule to the five official quintile rows. If valued
weight totals zero, shares remain undefined.

## Captures and integration handoff

`scripts/extract_lifetime_measure_sources.py --check` reproduces pinned
JSON from captured SSA OACT tax/interest pages and the MINT user guide,
and checks effective interest against both per-fund historical pages.
The canonical guide is `data/external/mint8_table_user_guide.source.html`;
the canonical row-label capture is `data/external/mint8_row_categories.json`
and contains labels only, never data cells.
Source hashes and element/table locators accompany every extraction.
The captured MINT source is certified 2026-04-01; the dispatch brief's
2025-10-01 description is an older vintage.

Tests: `test_lifetime_measures.py` and
`test_lifetime_measures_properties.py` are `unit`;
`test_lifetime_measure_sources.py` is `artifact`. They include Hypothesis
invariants, independent PV/quintile formulas, and differential checks
against both SS oracles and the Track A/Track M benefit conventions.

The integrator must add the new source module to
`POST_REVIEW_SOURCE_EXCLUSIONS` and its pinned tuple test, update
`tests/tier_counts.json`, and add Hypothesis to dev extras if absent.
Those shared files are intentionally outside this package's write scope.
Hypothesis is already present in this checkout's dev extras.
