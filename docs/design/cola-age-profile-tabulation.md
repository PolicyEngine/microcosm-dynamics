# Exercise-1 COLA age-profile tabulation

`populace_dynamics.estimates.cola_age_profile` is the tabulation step (Track A
item A7) for DynaSim scorecard exercise 1: the percent change in average
Social Security benefits by age group in the reference year (2030) when each
annual COLA from the first reformed increase is one percentage point lower.
It is post-compute. It does not project a population, compute or index a
benefit, read a comparator value, apply an acceptance rule or write an
artifact. It is not reachable from the historical birth-evidence reducer and
is outside the registered first-estimates estimator surface.

The specification is not frozen until A1 is ratified. Max's rulings of
2026-09-23 (plan section 6 items 1-3) cover no tabulation field. Every
convention awaiting ratification is a field of `ColaAgeProfileConfig` whose
default is the plan's proposed primary. Each result records the
configuration, the exact conventions, and, for each pending ruling, the value
used and whether it equals the proposed primary.

## Input

One row per `(draw, person_id)` for the reference period, carrying both
scenarios: `draw`, `person_id`, `family_unit_id`, `weight`, `birth_year`,
`beneficiary_base`,
`beneficiary_reform`, `benefit_base`, `benefit_reform` and
`benefit_components`. `benefit_components` maps a closed vocabulary
(`retired_worker`, `disabled_worker`, `spouse`, `aged_widow`,
`disabled_widow`) to `{"base": amount, "reform": amount}`. Components must sum
to the totals, and unknown names are refused. The statistic uses the benefit
summed over the selected components. The tabulation refuses duplicate
`(draw, person_id)` keys, a draw set different from the configured one,
non-finite or negative amounts or weights, a false beneficiary flag with a
positive benefit, a `person_id` whose birth year or family unit differs
between draws, and a DataFrame with repeated column names. `family_unit_id`
is the person's family unit in the population's opening wave (A1 section 16:
the 2011 interview number ER34101, or the 2009 interview number ER34001 for
row R6); like `person_id` it is an integer or a non-empty string, one type
for all rows. Persons whose weight differs between
draws are counted in the input summary, not refused.

## Statistics

Per draw and age group, with scenario memberships `S_base` and `S_reform`:

- **Ratio of scenario means** (proposed primary):
  `100 * (mu_reform / mu_base - 1)`, where `mu_s` is the weighted mean
  selected benefit over `S_s`.
- **Mean of individual ratios** (registered alternative):
  `100 * (weighted mean of B_reform / B_base over S_alt - 1)`.

Both are always computed. `headline_statistic` only chooses which one is
labelled primary. By default a person is a recipient in a scenario if flagged
with a positive selected benefit. Memberships must be identical in both
scenarios, checked on every row, or the run is refused. With
`allow_membership_difference=True`, `membership_basis` chooses
scenario-specific, baseline or common recipients.

A cell with no members, zero total weight or a non-positive baseline mean
has no statistic in that draw (A1 section 7). It is reported as undefined
with its reason (`empty_baseline_membership`, `nonpositive_baseline_mean`,
and so on) and never imputed. A group's draw summary of a statistic is
defined only when every draw is: otherwise its mean and SD are null, and it
lists the number of defined draws and each undefined draw with its reason.
The result's `undefined_cells` lists every such group and statistic. The
other groups and statistics are reported as usual, so one undefined cell
never withholds the rest of the row.

Age is `reference_year - birth_year` by default. The default groups are
50-61, 62-64, 65-69, 70-79 and 80+.

## Uncertainty

The reported value is the mean over draws of the per-draw statistic, with the
`ddof=1` sample SD (null for a single draw). Draws default to K = 20 (indices
0-19). A non-finite value anywhere (float64 overflow), including the
half-sample means and floor summaries, is refused with
`ColaTabulationError`, so every number in a result is finite JSON. The
noise floor follows `runs/replication_mermin_rows_v1.json`
`conventions.floor`, with the split unit of A1 section 16. For each of
seeds 0-4, `harness.panel.split_panel_by_person(fraction=0.5)` splits the
opening-wave family units (`family_unit_id`, the default `floor_split_unit`)
into two disjoint halves, so every draw of every member of a family unit
falls on one side. The reported estimator is recomputed on each half. The
floor is the summary of `|side_a - side_b|` over seeds where both halves are
defined: mean, sd (`ddof=1`), min, max, n_seeds and values, with dropped
seeds listed. Floors are at half sample and are not rescaled. Two deviations
from the Mermin-row precedent, both from A1 section 16: the split unit is the
family unit, not the person (`floor_split_unit="person_id"` reproduces the
precedent and is not registered); and with fewer than two usable seeds the
floor is undefined (`defined: false`, null summary fields and an
`undefined_reason`), never a zero summary or a zero SD. The usable seeds' gaps
are still listed.

## Governance

`data_provenance="invented"` results carry an invented-data label.
`"registered_real"` requires a registration pointer (the issue #42 comment
that must precede any real-data run) and output labels, and refuses the
invented-data label (for example, labels copied from an invented dry run).
The pointer is recorded, not verified. The module's tests use invented rows
only.

## Pending rulings (plan section 6)

| Parameter | Proposed primary (default) | Registered alternative | Awaiting |
|---|---|---|---|
| `headline_statistic` | ratio of scenario means | mean of individual ratios | A1 ratification (item 4) |
| `recipient_rule` | positive benefit | none (`flagged_recipient_including_zero` available) | A1 ratification |
| `allow_membership_difference` | false (identical membership) | none | A1 ratification |
| `membership_basis` | scenario-specific (operative only if differences are allowed) | none | A1 ratification |
| `age_rule` | reference year minus birth year | none | A1 ratification |
| `benefit_period` | calendar-year payments (declared label; not checkable here) | December monthly amount | A1 ratification |
| `components` | all five types | retired and disabled workers only | A1 ratification (item 2(b), the DI level, was ruled by Max on 2026-09-23) |
| `draw_indices` | 0-19 (K = 20) | none | A1 ratification |
| `floor_seeds` | 0-4 | none | A1 ratification |
| `floor_split_unit` | opening-wave family unit (A1 section 16) | none (`person_id`, the Mermin-row precedent, is available) | A1 ratification (referee question 2) |

No acceptance rule is applied: Max ruled on 2026-09-23 (plan section 6,
item 3) that there is no numerical acceptance threshold. Conventions upstream
of the rows (rate path, first reformed increase, exposure clock) can be
recorded verbatim through `upstream_conventions`. Each registered alternative
for those conventions is a separate set of input rows.
