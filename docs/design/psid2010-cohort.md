# PSID 2010 starting cohort (Track A, work item A3)

`populace_dynamics.cohorts.psid2010` builds the closed starting population
proposed for DynaSim scorecard exercise 1 in the critical-path plan
(`critical-path-cola-20260922.md`, section 3 and work item A3). Every output
is a *PSID-seeded closed cohort*. The builder computes no benefit, no COLA
scenario and no comparison statistic.

## Population

- **Universe.** Persons in the 2011 individual file with sequence 1-20
  (present in a responding family at the 2011 interview) and a positive
  2011 cross-sectional weight. `presence=in_family_or_institution` adds
  sequence 51-59.
- **Weight.** `ER34155`, label "CORE/IMM INDIVIDUAL CROSS-SECTION WT 11" in
  both `IND2023ER.sas` and `IND2023ER.sps` (checked 2026-09-22). The reader
  verifies the label and that it is the only "CROSS-SECTION WT 11" label.
  The codebook gives a range of 55-88,308 and 0 for "not response in 2011".
- **Positive weights outside the universe.** On the staged file ER34155 is
  also positive for every 2011 mover-out (sequence 71-80) and every person
  who died between the 2009 and 2011 interviews (81-89), not only for
  persons in a family or an institution. Neither presence option admits
  movers-out or decedents, and these persons get no disposition. The
  diagnostic `positive_weight_outside_presence` reports their count and
  weight by sequence group so the exclusion is accounted, not silent.
- **Membership.** A universe person is a member when the section 3.1 birth
  year is at most 1980 and sex is coded. Every universe person gets exactly
  one disposition: `member`, `excluded_birth_year_unresolved`,
  `outside_birth_cohort` or `excluded_sex_unknown`, in that precedence.

## Laws reused, not re-implemented

- **Birth year.** `estimates.career.derive_birth_years` (first-estimates
  §3.1). The seed coordinate uses the 2011 wave as anchor, so clause 3 is
  `2010 - age`. By default clause 2 reads every staged earnings wave, as the
  first-estimates run did (`birth_inference_max_wave=None`).
- **Careers.** `estimates.career.build_career` with `claim_year=2010` as the
  information cutoff. The inputs are observed head/spouse labor income
  1968-2010 and the biennial gap law. The career runs from
  `max(1968, birth_year + 22)` through 2010. Each year carries one
  provenance class.

## New reader: Social Security income 2008-2012

`data.social_security_income` verifies every variable by its exact label,
following the `family.py` and `deaths.py` pattern. It also requires each
concept to be the only label of its kind in the wave.

- **Family files.** Waves 2009, 2011 and 2013 (income years 2008, 2010 and
  2012) carry the head and wife amounts with accuracy flags, the OFUM
  family-unit total, and the family-level R20 item on receipt in the year
  before last. Income years 2009 and 2011 have no amount.
- **Individual file.** The same waves carry a person-level amount
  (`ER34031`, `ER34143`, `ER34250`) and a self-reported benefit type. In
  2009 this is one code (`ER34030`); from 2011 it is six mention flags
  (`ER34137`-`ER34142`, `ER34244`-`ER34249`). The type codes are verified
  against `IND2023ER_formats.sas`. A new block parser keeps semicolons that
  appear inside labels; `disability.parse_sas_value_labels` truncates at the
  2009 label "Survivor benefits; dependent of deceased recipient".

On the staged data the person-level item agrees with the family head and
wife amounts for every cohort head/wife row: 30,837 rows, no receipt
disagreement, 30,713 exact matches, largest difference $12. The plan's
section 3 lists the benefit type as unobserved; its label search covered the
2011 family file only. The individual file carries a type item in every wave
from 2005 (labels checked), and this reader resolves 2009-2013.

## Choices awaiting a ruling

Each choice is a `Psid2010CohortSpec` field.
`psid2010.pending_decisions()` returns the same list with its basis text.
None of these choices is ratified.

| Field | Default | Alternatives | Basis of the default |
|---|---|---|---|
| `presence` | `in_family` | `in_family_or_institution` | Builder choice (the plan says only "observed in the 2011 wave") |
| `max_birth_year` | 1980 | — | Plan §3 |
| `retirement_age` | 62 | — | Plan A3 ("62+ with SS") |
| `status_rule` | `plan_age_m4_widowhood` | `reported_type` | Plan A3 |
| `under_62_precedence` | `m4_then_widowhood` | `widowhood_then_m4` | Builder choice (the plan gives no order) |
| `under_62_residual` | `disabled_worker` | `unclassified` | Plan A3 (under 62 → DI or survivor) |
| `aged_m4_disabled_di_below_age` | none | 66 | Plan A3 (every 62+ recipient is retired or survivor) |
| `m4_waves` | (2011,) | (2009, 2011), (2009,) | Builder choice; restricted to the waves whose M4 value codes the loader verifies (2009, 2011). A member with no ascertained status in any consulted wave counts as not M4-disabled and is flagged `m4_status_unknown` |
| `reported_type_precedence` | disability, survivor, retirement, dependents, other | — | Builder choice (used only under `reported_type`) |
| `ofum_ss_source` | `individual_file` | `unobserved` | Builder choice (the plan's reader covers only head and wife) |
| `bracket_resolution` | `first_observed` | `fu_prior_year_indicator` | Plan A3 ("from observed first SS receipt") |
| `claim_table_max_year` | 2008 | — | Plan A3 (§6 law restricted to rows ≤2008; the rows come from the later 2014 Supplement) |
| `stock_imputation_root_seed` | 2010 | — | Builder choice; unregistered and must be fixed at registration |
| `separated_is_married` | true | false | Builder choice. "Separated" uses the MH16 separation year of every marriage, including one that ended in divorce only after 2010 |
| `birth_inference_max_wave` (loader) | none (all waves) | 2011 | Builder choice (first-estimates precedent) |

## Opening stock

- **Plan rule (default).** A 2010 recipient aged 62+ is a survivor if widowed
  at the end of 2010 (MH85_23) and a retired worker otherwise. Under 62, the
  person is a disabled worker if M4 self-reports "permanently disabled", then
  a survivor if widowed, and otherwise the residual (DI by default).
- **Reported-type rule.** Under `reported_type`, the first mentioned G33A
  type is used. A person who reported no type falls back to the plan rule.
- **Opening claim year.**
  - *Bracketed receipt* (none observed in 2008, some in 2010): the claim year
    follows `bracket_resolution`.
  - *Censored retired worker*: the claim age is drawn under the §6 law. The
    draw uses the engine's nearest-year snap on rows ≤2008 and a
    person-keyed RNG in the namespace
    `psid2010_cohort.opening_stock.person.v1`. It is truncated so the claim
    year does not follow the latest year the first receipt is known to
    precede.
  - *Censored DI or survivor*: only that upper bound is recorded.
  - *Empty truncated mass*: the §6 law fails closed. This builder records
    `imputation_empty_mass` instead, because a misclassified status can make
    the mass empty legitimately.

## Structural counts on the staged data (2026-09-22, default spec)

These are counts only.

- **Members.** 11,405 persons, weighted total 171,855,006. Birth years span
  1912-1980.
- **Dispositions.**
  - 10,868 outside the birth cohort.
  - 861 with an unresolved birth year: 856 with age code 1 and 5 with age
    code 999.
  - None excluded for sex.
- **Birth source.**
  - `exact_marriage`: 11,206
  - `inferred_period_age`: 11
  - `derived_projection_age`: 188
- **2010 receipt.** 2,190 recipients (weighted 43,927,189). By 2010 age:

  | 2010 age | Persons | Recipients |
  |---|---:|---:|
  | 30-49 | 6,046 | 227 |
  | 50-61 | 3,167 | 277 |
  | 62-64 | 572 | 270 |
  | 65-69 | 556 | 449 |
  | 70-79 | 627 | 572 |
  | 80+ | 437 | 395 |

- **Opening status under the plan rule.** Retired worker 1,340; disabled
  worker 485; survivor 365.
- **Plan rule against the reported type.** The comparison uses each
  recipient's first reported type under the default precedence.
  - Of 1,340 plan-rule retired workers, 144 mention disability.
  - Of 365 plan-rule survivors, 201 have retirement as the first reported
    type and 122 have survivor.
- **Marital status at the end of 2010.**
  - Married 7,475; widowed 515; divorced 1,340; never married 1,630.
  - Unknown 262; no marriage history 183.
  - For 6,926 of the 7,395 married members with a joinable spouse, the
    spouse in MH85_23 is also the 2011 co-resident head or wife.
  - 317 married members were living apart from the spouse at the end of
    2010 (`separated_2010`). Of these, 191 separated by 2010 but divorced
    only later; the first version of the builder missed them because
    `marriage_episodes` drops the separation year of a divorce. Under
    `separated_is_married=false` the counts become married 7,158,
    separated 313 and unknown 266.
  - For 5 married members, the MH85_23 spouse carries a death year of
    2010 or earlier in the death file
    (`married_with_linked_spouse_dead_by_2010`). They are flagged, not
    reclassified.
- **Positive ER34155 weights outside the default universe** (all ages,
  not only members): institution 464 persons (weighted 5,914,684);
  moved out since 2009, 946 (7,503,972); died since 2009, 117
  (1,847,636). The in-family universe carries 290,843,397 of the
  306,109,689 total.
- **M4 status.** 114 members have no ascertained M4 status in 2011
  (`m4_status_unknown`), 11 of them 2010 recipients.
- **Other flags.** Two members carry a death year before 2011 despite their
  2011 presence; they are flagged, not dropped.

To regenerate these counts, run
`python scripts/psid2010_cohort_structure.py --output <path>`.

## Limits

- **Immigration.** Immigrants who arrived after the 1997 refresher are
  under-covered (plan §3); the 2017 refresher postdates the 2011 wave.
- **Closed cohort.** The cohort is conditioned on being present at the
  2011 interview. Persons who died after the 2009 interview (during 2010,
  or in 2011 before their interview) and persons who moved out of a PSID
  family between the 2009 and 2011 interviews without being re-interviewed
  are absent, although ER34155 weights them (see the positive-weight counts
  above).
- **Realized information after the start.** `death_status` and the
  death-year columns come from the 2023 individual file's year of death
  (`ER32050`) and include deaths after 2010; `ss_2012`, the 2011 M4 status, the 2010 type flags read in
  2011 and (by default) birth-year clause 2 also use information collected
  after the end of 2010. The opening-stock rules read only 2008 and 2010
  amounts, M4 and marital state. A projection must draw mortality rather
  than read the realized death columns, which are for validation only.
- **Earnings.** Labor income is a proxy for covered earnings (first-estimates
  §3.4). A year in which the person was not an interviewed head or spouse is
  `unknown`; the mean career coverage ratio is 0.69.
- **Odd years.** Income years 2009 and 2011 have no Social Security amount.
- **OFUM totals.** Across the whole 2011 wave, the family OFUM total is
  positive in 452 families. The sum of the present OFUMs' person amounts is
  positive in 375 families, and the two are equal and positive in 326. This
  one-off check is not part of the builder.
- **Linked spouses outside the universe.** For these spouses only
  birth-year clauses 1-2 apply. A spouse with conflicting marriage-history
  birth years is named, not resolved.
