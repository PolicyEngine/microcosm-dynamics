# Erratum: the delayed-retirement-credit window

**Verification class: statutory conformance.** This note records a statutory
float credit function beside the unchanged sealed oracle for cohorts from
1917. The original impact audit below is a static audit of model code and
committed metadata. The appended d1408 section is a separately authorized,
labelled diagnostic using local PSID. Neither admits a new registered
result, behavioral estimate or forecast claim.

11 October 2026. Issue #494 identified a four-year cap in
`ss.benefits.delayed_credit` that shortened the statutory credit window for
birth cohorts 1917–1942. Registered computations can reach those cohorts
with late entitlement. The oracle is inside the first-estimates
birth-evidence source seal and remains byte-identical to the reviewed
implementation. Registered results on the reachable paths were computed
with the legacy 48-month cap and stand as registered. Their committed bytes,
the seal's reviewed commit and all registered callers are unchanged. No
registered computation was rerun.

## Statutory and sealed legacy windows

The sealed oracle continues to use
`min(params.max_delayed_months, 840 - params.fra_months(birth_year))`.
The captured parameter bundle supplies 48 for `max_delayed_months`.
Section 202(w)(2)(A) of the Social Security Act, 42 USC 402(w)(2)(A),
counts increment months from the month of attaining full retirement age
through the month before attaining age 70. The statutory window is therefore
`840 - FRA`, which is 60 months at FRA 65 and falls by two months per cohort
for births 1938–1942, to 50 months for births in 1942. POMS RS 00615.692E
states those maxima. Section 202(w)(6), 42 USC 402(w)(6), and POMS
RS 00615.692D determine the rate.

The sources are the existing captures
`tests/data/track_b/gross_benefit_sources/lii_usc_402_415_excerpts.txt`
(402(w)(2) at line 18 and 402(w)(6) at line 21) and
`poms_rs_00615_692.html` (sections D and E), whose bytes are listed in that
folder's source manifest. No external source was fetched for this audit.

## The isolated statutory computation

For births from 1917, the new
`ss.statutory_delayed_credit.delayed_credit` uses `840 - FRA` and returns a
float fraction. `months_late` measures months from FRA to the first month
of entitlement. A claim after 70 earns no additional credit; its months
after the window are truncated. Zero and negative delays return zero before
parameter lookup. Positive delay for a birth before 1917 raises
`ValueError` naming 402(w)(6)(A). The parameter bundle and
`ss.benefits.delayed_credit` retain their sealed legacy behavior.

This follows `ss/statutory_aime.py`: `DelayedCreditWindow.STATUTORY`
selects the new function; `LEGACY_48_MONTH_CAP` selects the unchanged
oracle through `oracle_delayed_credit`. The caller must pass `window`
explicitly. New statutory work and any later registered statutory rerun
must select `DelayedCreditWindow.STATUTORY` and state that convention in
its registration and report. Nothing registered changes by import or by
default. The sibling module is added to the birth-evidence seal's explicit
post-review exclusions; the seal's reviewed commit is not moved.

Track B G already implements the statutory window with exact arithmetic.
G's pin of `ss.benefits.delayed_credit(60, 1935) == 0.24` now names the
sealed legacy convention. Its differential against that function covers
`min(48, window)`, and its differential against the statutory function
covers the complete window. G continues to refuse positive delayed
credits for births before 1917.

The year-only oracle follows POMS' January 2 through January 1 cohort bands:
callers representing a January 1 birth must supply the preceding cohort
year. This correction does not add a date-of-birth interface.

## Registered results with reachable legacy undercredits

“Reachable” means the population and claim rules admit an input in the
region where the two conventions differ. It does not mean a person in
that region has been counted in a committed run. The committed summaries do not give the necessary
joint birth-year and claim-age distribution.

| Registered result | Model path and evidence | Reachability |
|---|---|---|
| First estimates, `runs/first_estimates_v1.json`, registration `populace-dynamics#307` | `scripts/run_first_estimates.py:257` enters the coordinator; `estimates/preparation.py:558` builds the benefit ledger; `estimates/ledgers.py:544` calls `claiming.benefit_factor`. `estimates/career.py:1582` excludes eligibility before 1979, so included births begin at 1917. The opening-stock claim distribution includes age 70 (`claiming.py:294`); `career.py:1520` supplies the opening draw and `:1528` places it at birth plus claim age. The artifact's configuration echo records the unsplit 2014–2022 panel and registration #307. | Births 1917–1942 with a sufficiently late opening or modeled claim are reachable. Births before 1917 are excluded from the production ledger. |
| First-estimates registrations 2–7 | `docs/registrations/first_estimates_registration_{2,3,4,5,6,7}_configuration.json`, each line 1, binds the same report family, including the stock-imputation namespace. References are #289, #292, #295, #299, #305, and #307. The production birth-timing sensitivity also reruns inclusion before building each alternative ledger (`estimates/preparation.py:453–476`). | The 1917–1942 late-credit region is reachable in the registered mechanism. This is no claim that an earlier failed attempt published numeric results. |
| Track A COLA, `runs/replication_urban2010_cola_v1.json`, issue #42 comment 5804420283 | `scripts/run_track_a_registered.py:304–312,362` builds and runs the 2011/2009 cohorts. `cohorts/psid2010.py:1365–1379` excludes unresolved births and births above 1980, with no lower cutoff; `:1935–1950` draws opening retired-worker claim ages. `cola_track_a/benefits.py:345` calls the factor for worker records, including linked spouse/deceased records at `:619` and `:385`. Artifact `/config/populations` records starts 2010/2008, `born_max=1980`, and projection to 2030. | Births 1917–1942 claiming at 70 are reachable. An intact opening recipient's own payment is carried from its observed amount (`cola_track_a/benefits.py:822–836`), so the existence of an old recipient alone does not imply its own payment changes. Other worker-record paths still reach the oracle. |
| FRA 68, `runs/replication_urban2010_fra68_v1.json`, issue #42 comment 5840600730 | `scripts/run_fra68_registered.py` runs the same recorded 2011/2009 population. `fra68_track/benefits.py:432–433` inherits Track A's worker-record calculation; `:402` also recalculates a moved claim's factor. `fra68_track/reform.py:517–518` compares baseline and reform factors. The artifact's `/config/populations` retains `born_max=1980`, starts 2010/2008, and reference year 2030. | The old-cohort late-credit region is reachable in baseline and inherited worker-record calculations. The reform's cohort schedule may change a particular person's window; no aggregate change is inferred here. |
| Track M minimum benefit, `runs/replication_urban2006_minimum_benefit_v1.json`, issue #42 comment 5855753783 | `scripts/run_track_m_registered.py:345–358` builds both own-receipt readings and their career inputs. `min_benefit_track_m/careers.py:268–277` checks the oracle domain then computes every worker record's factor; `:100–111` uses `rules.claim_factor` only for old age. `rules.py:739–742` uses whole-year entitlement minus birth against FRA. `cohort.py:443–449` permits a boundary-derived late entitlement year. The committed all-record old-age ages span 62–87 (`runs/replication_urban2006_minimum_benefit_v1.json:7256–7278`); the d430 sensitivity spans 62–87 as well (`:6573–6596`). | Births 1917–1942 with entitlement after FRA plus four years are reachable. Disability- and death-basis records have factor 1. The age histogram alone does not prove which older cohorts are late. MS5 divides an observed benefit by the claim factor (`rules.py:692–720`), so selecting the statutory convention in a later rerun can also change its inferred PIA. |
| R7 earnings sharing, `runs/replication_r7_sharing_v1.json`, issue #42 comment 4911171806 | `scripts/replication_r7_sharing.py:389–396` restricts the career frame to births 1943–1957. The separate PIA-supply loop (`replication_r7_sharing.py:398–410`) admits older linked workers with positive earnings and an indexable history. `score_population` iterates the career frame at `:723`, checks linked PIA coverage at `:730`, and evaluates the baseline at `:740` and package 1a at `:747`. The baseline deceased-record path at `:619–641` and the package-1a deceased shared-vector path at `:676–705` both call `household.survivor_benefit_at_death` (`:632,696`), whose deceased factor at `household.py:218` reaches `claiming.py:375`. | Older linked deceased workers born 1917–1942 with late claims can reach the differing window in both baseline and 1a survivor evaluations, despite being outside the career frame. Indexable pre-1917 linked records can also reach positive-credit evaluations. The artifact's career-frame metadata does not restrict the linked PIA supply. |
| Cost ordering, R7 component of `runs/replication_cost_ordering_v1.json` | `scripts/replication_cost_ordering.py:586` constructs R7's `StudyData`; `replication_cost_ordering.py:587` calls R7's `score_population`, including the baseline and 1a survivor evaluations above. The descriptive output uses the 1b aggregate cost change at `:588–610`; `replication_r7_sharing.py:1035–1046` puts the R7 baseline in its denominator. | The R7 component reaches the same older linked deceased records, including possible pre-1917 evaluations. A baseline change can enter the reported 1b cost ratio; 1a is evaluated during scoring even though this descriptive output reports 1b. The separate Mermin component remains outside the differing region. |
| Track A v2 registered entry point, `scripts/track_a_v2_registered.py` | `track_a_v2/protocol.py:313–359` builds the inherited Track A cohort; `track_a_v2/benefits.py` composes its calculators from the inherited Track A/FRA 68 calculators and calls `worker_record` at `:152,220`. `track_a_v2/runner.py:259–267` uses the inherited projector. | The mechanism can reach the same old-cohort window. There is no Track A v2 numeric artifact under `runs/` in this checkout, and this audit does not assert that a one-shot has executed. |
| Anchor-context registrations 1–5 and `runs/anchor_context_report_v1.json` | Each `docs/registrations/anchor_context_registration_{1,2,3,4,5}_configuration.json:1` binds the already committed `runs/first_estimates_v1.json` at SHA-256 `719604ca4364e7cdef2293329ed0beb0e011e5d4d1c34f0e508c8f2fd9932977`; the runner fixes that input at `scripts/run_anchor_context_report.py:62,87,206`. | These consumers read the committed first-estimates results, rather than executing a credit function. Their input can carry the older-window error. Their bytes do not change automatically. |

The first-estimates milestone in `docs/forecasts/timeline_ledger.json:138`
also binds the committed report and registration #307. It is a completion
record, not a fresh computation under the statutory convention. No forecast
verdict is changed by this patch.

The repository contains frozen first-estimates configurations 2–7, but no
configuration 1. The repository also contains incident artifacts 1–6
(`runs/first_estimates_incident_{1..6}.json`). They record aborted
preparation or computation attempts, with no retained model headline
tables, so they add no registered money result to reconstruct. The published #307 report and
its report mechanism remain the first-estimates numeric scope.

## Other call paths and results outside the differing region

The three direct production callers are `claiming.benefit_factor`
(`claiming.py:375`), Track M `rules.claim_factor` (`rules.py:742`), and
`scripts/replication_mermin_rows.py:281`.

| Path or committed artifact family | Evidence and conclusion |
|---|---|
| Mermin rows, `runs/replication_mermin_rows_v1.json` | Both the direct delayed-credit call and PMF baseline deliberately use birth year 1988 (`scripts/replication_mermin_rows.py:206,279–305`) and a 36-month window. The underlying career supply is the same 1943–1957 frame. The region where the windows differ is unreachable. |
| Cost ordering, Mermin component of `runs/replication_cost_ordering_v1.json` | `scripts/replication_cost_ordering.py:307–309` builds the caregiver/Mermin common frame and reuses the Mermin score. `replication_mermin_rows.py:298–305,448` uses the fixed 1988 factor cohort, with no linked deceased-record factor. This component is outside the differing region; the separately scored R7 component is reachable as recorded above. |
| M2, `runs/m2_pseudo_projection_v1.json` | The common-frame Mermin score is reused at `scripts/m2_pseudo_projection.py:363–364`; the own-record baseline uses birth 1988 at `:409` and its FRA-72 alternative uses Mermin's explicit-FRA helper at `:413`. The region where the windows differ is unreachable. |
| Deployment W1 candidates 1–4 and forensics 1–3 | Family B calls `disability_conversion.assign_claim_or_conversion` at `models/transport_deployment_v1.py:792`, for frame ages 62–66 (`:764`) with birth `2024-age` (`:50,757`), hence births 1958–1962. Choice claimers call the factor (`disability_conversion.py:185`), while conversions use 1 (`:163–164`). Family C uses transported birth cohorts 1943–1957 (`transport_deployment_v1.py:867–868,953`) and runs M2 (`:1089`); v2/v3 delegate to these routines. `scripts/gate_w1_forensics3.py:183–201` reuses the same transport and M2 path. Therefore the region where the windows differ is unreachable for `runs/gate_w1_candidate{1,2,3,4}_v1.json` and `runs/gate_w1_forensics{1,2,3}_v1.json`. |
| Illustrative auxiliary benefits, `runs/aux_benefit_examples_v1.json` | `household.py:108,218` calls the factor for own and deceased benefits. Its builder fixes the FRA-66 worked-example/deceased birth at 1954 (`scripts/build_aux_benefit_examples.py:71,149–153,495`) and the couple/surviving worker births at 1960 (`:444,494`). The region where the windows differ is unreachable. |
| Public helper surfaces without their own registered result | `claiming.expected_reduction_factor`, `household.couple_benefit`, `household.survivor_benefit_at_death`, `disability_conversion.assign_claim_or_conversion`, and `fra68_track.reform.worker_factor_ratio` accept caller-supplied cohorts. Old births and late claims can reach the legacy undercredit if a new caller supplies them. These helpers remain unchanged; a later statutory caller must explicitly select the new convention. Their registered callers are classified above. |
| Invented Track M and PolicyEngine bridge examples | `min_benefit_track_m/invented.py:191,286` calls `rules.claim_factor`; `scripts/pe_us_minimum_benefit_sample_households.py:779` and `scripts/pe_us_depletion_cut_sample_households.py:565` call it for illustrative worker inputs. `scripts/pe_us_population_invented.py` builds the invented M4/M5 inputs. These are invented-input surfaces, without a registered real-population result under `runs/` on these paths. These callers still exercise the legacy oracle; statutory comparison requires an explicit opt-in to the new function. No population claim follows. |
| Imports of shared study code without credit calculations | `scripts/replication_ppi_shared.py` reuses `StudyData` and relevant marriage episodes but does not call R7 scoring or its expected claim factor. `replication_caregiver.py`, `replication_ppi_mermin.py`, `w2_seam_caregiver.py`, and `reform_delta_diagnostic.py` do not call the delayed-credit machinery. Track U/U2 use observed-benefit reductions and poverty tabulations rather than Track M's claim-factor computation. Their artifacts are outside the call graph. |
| Artifact-only downstream consumers | Tranche-2 benchmark builders and first-estimates/anchor-context publication readers consume the retained JSON bytes. Their citations to a registered artifact do not execute the statutory credit function. |

The 12 October 2026 review correction rechecked every row above for a
restriction applied to the scored career frame but omitted from linked
worker records. It found that pattern in R7 and its cost-ordering caller;
the other classifications remain supported by their actual factor paths.
Mermin iterates its career frame (`replication_mermin_rows.py:441`) and
passes the fixed 1988 cohort to its factor calculations (`:298–305,448`).
M2's calendar ledger and common-frame calculations use those own-record
paths (`m2_pseudo_projection.py:363–364,409–413`); importing cost-ordering
helpers does not call its separate R7 scorer. Deployment family B passes
only its age-masked records into conversion
(`transport_deployment_v1.py:764,785–792`); family C and forensics call M2
(`:1089` and
`gate_w1_forensics3.py:228`), with no R7 scoring. The auxiliary builder's
foundation grid fixes births 1954 and 1960
(`build_aux_benefit_examples.py:293,386`); its separate linked-coverage
metadata calls only
`household.both_spouse_coverage` (`:525–533`), not a benefit factor.
PPI-shared imports R7's study/episode machinery
(`replication_ppi_shared.py:166–170`) but computes scheduled PIAs
(`:397–398`) without a delayed-credit or survivor-factor call. Imports and
linked coverage alone therefore do not make those additional results
reachable.

`tests/test_delayed_credit_reachability.py` executes the R7 constructor
with invented earnings and marriage loaders. A survivor born 1945 is in
the career frame, while a linked deceased worker born 1937 is outside it
and remains in the PIA supply. Both baseline and 1a survivor paths evaluate
the deceased's 60-month credit at age 70. The baseline using the constructed
PIAs $225.00 and $259.20 is $218.41231551242228 under the sealed convention
and $218.6072054833109 under the statutory convention, before payment
rounding. Isolating invented PIAs $1 and $1,000 and claims at 70 gives
exactly $1,260 versus $1,325. This is the 1937 statutory arithmetic below,
reached through an older linked worker rather than a career-frame member.
The property test covers deceased cohorts 1913–1942 and both survivor paths;
it checks that linked PIA supply and factor evaluation do not inherit the
career cutoff. The audit-consistency test pins the reachable R7 and
cost-ordering rows to this executed counterexample.

## Births before 1917: statutory refusal and retained registered behavior

Section 202(w)(6)(A), as captured at
`lii_usc_402_415_excerpts.txt:21`, specifies:

> 1 ⁄ 12 of 1 percent in the case of an individual who first becomes
> eligible for an old-age insurance benefit in any calendar year before 1979

POMS RS 00615.692D assigns that rate to births before January 2, 1917;
section E includes windows longer than 60 months for the earliest cohorts.
The parameter loader reads
`policyengine_us/parameters/gov/ssa/social_security/retirement_age_adjustment/delayed_retirement/credit_rates.yaml`
at `ss/params.py:283–297`. Its `(1900, 0.03)` first bracket gives these
cohorts 3 percent annually. This is an upstream parameter defect, not a
statutory alternative. The PolicyEngine checkout is not edited.

The static audit found three registered mechanisms that admit pre-1917
positive-month inputs to the sealed oracle:

- **Track A and inherited FRA 68/v2 calculators.** The cohort has no lower
  birth cutoff (`psid2010.py:1365–1379`). For an invented linked retired
  worker born 1916 who first claimed at 70 and dies after opening,
  `deceased_record` retrieves the last state before death (`:384–385`). Its
  `worker_record` call obtains a missing PIA from `_level`
  (`cola_track_a/benefits.py:268–270`) and still evaluates the claim factor
  (`:345–347`) before the projected widow's caller rejects the missing
  level (`:694–697`). This path does not require the older worker to survive
  to 2030. Intact opening own payments use their observed amount; that
  bypass does not remove the linked-worker path.
- **Track M.** `careers.check_oracle_domain` accepts births from 1913
  (`careers.py:167–175`) and refuses a pre-1979 PIA formula only when the
  record's window is 2004 or later (`:176–185`). It computes the factor for
  every record, including outside-window records (`:273–277`). An invented
  birth 1916, old-age entitlement 1983, threshold 1978 passes this existing
  domain check and reaches 24 positive months. This domain-check
  counterexample was executed using only the invented one-row frame.
- **R7 and the R7 component of cost ordering.** The career-frame restriction
  does not apply to linked PIA supply (`replication_r7_sharing.py:389–410`).
  A linked worker born 1916 with positive invented earnings from 1951
  through 1977 has an indexable age-60 year of 1976 and a PIA of $116.10,
  while remaining outside the career frame. A survivor born 1945 has PIA
  $225.00 and observed widowhood before eligibility. Both the baseline
  (`:632`) and 1a (`:696`) evaluate the older deceased factor through
  `household.py:218`, including 60 positive months at age 70. The invented
  legacy baseline is $187.2862853209459 before payment rounding. Selecting
  the statutory function for either survivor path raises its pre-1917
  refusal. Cost ordering inherits both evaluations through R7 scoring
  (`replication_cost_ordering.py:587`); its reported 1b cost ratio uses the
  baseline. These cases use only invented loaders and do not establish a
  pre-1917 record in either committed population.

The allowed metadata cannot determine whether any of these counterexamples
occurred in a committed population. The sealed oracle preserves its legacy
rate and 48-month cap for those paths; those credits have no
statutory-conformance admission. The new function refuses positive delay
before 1917 without changing any registered caller. Its refusal is
implemented and tested, including the 1917 boundary. Zero and negative
delays remain zero under both conventions.

The committed diagnostic `runs/first_estimates_birth_evidence_draw0.json`
has another model-possible early-cohort path: its fixed-age factor
sensitivity calls the oracle after shifting a baseline-included birth
down one year, even if that shifted person was excluded by the production
inclusion rerun (`scripts/first_estimates_birth_evidence.py:2347–2357`).
Thus an included 1917 birth can be priced diagnostically as 1916. The
production first-estimates sensitivity, in contrast, prices only included
alternative records (`estimates/preparation.py:453–476`). This diagnostic
has no one-shot registration pointer and was not rerun.

## Largest possible per-person difference between the conventions

These are statutory arithmetic examples, not estimates of actual people.
All figures describe entitlement at 70, before payment rounding:

| Birth cohort | Annual rate | Legacy months | Statutory months | Extra share of PIA | At PIA $1,000 |
|---|---:|---:|---:|---:|---:|
| 1935 | 6% | 48 | 60 | 6 percentage points | Credit $240 → $300; worker amount $1,240 → $1,300 |
| 1937 | 6.5% | 48 | 60 | **6.5 percentage points**, the largest in 1917–1942 | Credit $260 → $325; worker amount $1,260 → $1,325 |
| 1941 | 7.5% | 48 | 52 | 2.5 percentage points | Credit $300 → $325; worker amount $1,300 → $1,325 |

The maximum is found by comparing the rate multiplied by the missing
months in each POMS D/E cohort. Later annual rates are higher, but the
missing window falls to ten, eight, six, four, and two months for
1938–1942. For 1943 and later, the old 48-month bound never shortened the
statutory window.

Tests pin the maximum at 1937 and the exact additional fraction `13/200`.
This bound is for a worker's gross credit as a fraction of PIA. It is not a
bound on a population total, on a ratio or test verdict, or on Track M's
inverse MS5 calculation. COLAs and downstream dollar/dime floors can alter
the dollar effect. Where a mechanism carries observed opening benefits,
an unchanged observed amount can produce no own-payment change despite
the older worker-record path.

## Retained artifacts

No committed `runs/*.json`, registration configuration, committed-result pin,
forecast verdict, or protected engine/gate file is edited. In particular,
the reachable registered artifact families above and
`runs/first_estimates_birth_evidence_draw0.json` retain their original
bytes. Anchor-context readers retain their original first-estimates input
hash.

## The d1408 diagnostic

**Verification class: labelled diagnostic under ruling d1408; no registered
artifact rerun or replaced.** On 12 October 2026 Max ruled (d1408): "run the
#494 erratum diagnostic as a labelled diagnostic (affected people, weights
and the change under the statutory window in the four reachable registered
results), posted on #42 as an erratum note; no rerun or replacement of any
registered artifact." The R7 and cost-ordering paths found reachable after
the ruling are included, so the scope is six results. The conditions were
local PSID only, nothing opened from the restricted-file list, and counts
and changes only.

For each result the diagnostic exported the code at the commit the artifact
records, rebuilt the admitted records and claim inputs through the original
input builders and benefit functions (never a registered entry point), and
flagged every old-age factor evaluation with
`1917 <= birth_year <= 1942 and late_months > 48` or
`birth_year < 1917 and late_months > 0`, computing `late_months` as the
original caller does (Track M keeps whole-year entitlement ages). For five
results it reproduced the committed model headlines with
`LEGACY_48_MONTH_CAP`, then replaced only the credit window with
`DelayedCreditWindow.STATUTORY` and carried the result through the original
rounding and payment paths. First estimates is the exception: it is bounded
from the seed roster and the registered claim-age distribution, not
reproduced (see the table). External benchmark values are not used or
reported, and every change is in the model's own values. While the R7
builder was locating metadata, it displayed external-anchor fields that are
embedded in the committed R7 artifact and script. The reconstruction
executes model code and cross-checks model fields only.

The publication is deliberately small. For each result and wave it gives
at most one flagged subtotal (first estimates gives its support,
actual-person and expected bounds instead) and the denominator its share
uses (the seed cohort
for COLA and FRA 68, the admitted population for Track M and R7; first
estimates' per-draw denominators stay in its committed artifact); row
denominators and the Track M sensitivity reading's denominators are not
published. Each
payment path is reported only as none, fewer than ten, ten or more, or
withheld. Cells under ten people are withheld with their weights, shares
and changes. Every published count names the population it measures; the
R7 frame, which cost ordering also scores, is the one population
published twice, and both copies must match. No signed combination (each
population added, subtracted or left out) of the published populations
among results that describe the same people (COLA with FRA 68, R7 with
cost ordering), across rows, waves and both Track M readings, and with
people and worker-record counts pooled together, equals one through nine.
Each such family publishes at most 20 distinct populations, and a test
checks every sign pattern. Rounded population-level aggregates (R7's and
cost ordering's aggregate cost change) are published even where fewer than
ten people's payments change; they show only that the combined effect
stays below the reported precision. The full output is
`docs/errata/2026-10-11-delayed-credit-window-diagnostic.json`. The method,
its invariants and tests are in
`docs/design/d1408_delayed_credit_diagnostic.md` and `scripts/d1408_*.py`.

| Result (code commit) | Legacy reproduction | Flagged supported evaluations (1917–1942) | Change in the model's headline values under the statutory window |
|---|---|---|---|
| Track M minimum benefit (`2e4e08be`) | Exact in every cell: 84 in the scored reading, 12 in the d430 sensitivity reading | 34 people, weight 776,587: 1.72% of the 45,064,829 admitted weight (2,135 people). The flagged worker-record count is not published: beside the people count, which includes linked beneficiaries, it would narrow a withheld cell | None. In both readings, no person's receipt changes and every model share changes by 0.0 percentage points |
| R7 earnings sharing (`a8704357`, the artifact's recorded build pin) | Exact, 1,267 quantities | 12 admitted recipients through 24 linked deceased worker records, weight 462,445: 2.06% of the 22,432,859 admitted weight (1,016 people). Fewer than ten enter a changed computed payment | Aggregate 1b cost change 0.0 percentage points, with and without the scalar. In packages 1a, 1b and 1b without the scalar, every married, divorced and never-married cell shows no change; the widowed cells are withheld |
| Cost ordering, R7 component (`e86ec0c6`) | Exact, 5 quantities | As R7 | 0.0 percentage points in the reported 1b cost ratio |
| Track A COLA (`002264d9`) | Exact: every registered draw and every model headline, rows R0–R6 | 2011 cohort: 75 people, one flagged worker record each, weight 1,176,152 (0.68% of the seed cohort's 171,855,006). 2009 cohort: 62, weight 948,185 (0.54% of 175,961,799) | 0.0 in the 50–61, 62–64 and 65–69 groups in every row. The 70–79 and 80+ groups are withheld: fewer than ten people change at 70–79 in six of seven rows (none in R5), and the 80+ cells would reveal small cells by comparison with the row totals and other rows. In R6, 35 recipients change across the registered draws |
| FRA 68 (`08a695a4`) | Exact: every registered draw and every model headline, rows F0–F8 | Withheld: each subtotal would reveal a cell of fewer than ten by comparison with COLA, which shares its seed cohorts | 0.0 in the 50–61, 62–64 and 65–69 groups in every row, and in F6's 70–79 group, where none changed; the other older groups are withheld as for COLA |
| First estimates, #307 (`e31eca40`) | Not computed. Actual inclusion needs the registered fitted projection; its fitting stack (populace-fit, populace-frame, policyengine-us, scikit-learn 1.8.0) is not installed in the diagnostic environment, and the diagnostic did not refit it | Unverified upper bound: at most 21 people, weight 571,250, at most 1.58–1.65% of each draw's committed admitted weight | Not computed |

No result has a flagged pre-1917 evaluation. First estimates excludes those
births before the ledger (its pre-1979 eligibility rule); the other five
emit no pre-1917 flag.

So under the statutory window Track M's model values are unchanged, and
the R7 and cost-ordering aggregate cost changes are 0.0 at their reported
precision; R7's widowed share cells, where its flagged survivors sit, are
withheld. COLA and FRA 68 are unchanged in every group under 70, and in
COLA R5's and FRA 68 F6's 70–79 groups; their other older groups are
withheld, so this note cannot say how much those cells move. For any one supported worker, the added gross delayed credit before
payment rounding is at most 6.5 percentage points of PIA ("Largest
possible per-person difference between the conventions" above); dime and
dollar rounding can move the paid difference slightly past that (on a PIA
of $1,001 at 70 for a 1937 birth, $1,261.20 becomes $1,326.30, a $65.10
difference). That section's limits on totals, ratios and inverse MS5
apply here too. The
first-estimates exposure is bounded but not reproduced. Every registered
artifact stands as registered.

An earlier version of this note said the first-estimates incident artifacts
1–6 were absent from the repository. They are committed
(`runs/first_estimates_incident_{1..6}.json`); see the corrected paragraph
above.

## Not in scope

Beyond the d1408 diagnostic above, no real-data diagnostic, registered
rerun, comparator, upstream PolicyEngine parameter edit, revision of
committed results, or change to claiming behavior is part of this
correction. Neither an unchanged artifact test nor static reachability
establishes an unchanged population outcome.
