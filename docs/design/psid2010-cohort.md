# PSID 2010 starting cohort (Track A, work item A3)

`populace_dynamics.cohorts.psid2010` builds the closed starting population
proposed for DynaSim scorecard exercise 1 in the critical-path plan
(`critical-path-cola-20260922.md`, section 3 and work item A3). Every output
is a *PSID-seeded closed cohort*. The builder computes no benefit, no COLA
scenario and no comparison statistic.

The same builder also materializes the registered alternative population
of the A1 specification (section 14, row R6): the 2009 wave, opening at the
end of 2008 (see "The 2009 wave" below). Everything else in this document
describes the default 2011 wave unless it says otherwise.

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

## Family unit and provenance

- **Family unit.** `persons.family_unit_id` is the anchor wave's interview
  number (`ER34101` for 2011, `ER34001` for 2009), label-verified with the
  other anchor variables. A1 section 16 splits the half-sample noise floor
  on it, so the members of a family unit always fall in the same half.
- **Provenance, set by the builder.** `Psid2010Cohort.provenance` is not a
  constructor argument; `build_psid2010_cohort` sets it from the inputs,
  and `dataclasses.replace` resets it to `unsealed`.
  - `psid_files`: `load_psid2010_inputs` records the SHA-256 of every file
    under the PSID data directory that its readers opened (a Python audit
    hook on `open`, `record_files_read`) and a bundle hash of that mapping.
    The loader refuses to return inputs when it recorded no PSID file.
  - `invented`: the invented generator records the SHA-256 of its frames;
    the builder recomputes it and refuses inputs whose frames differ.
  - `caller_frames`: anything else.
  - Every provenance also carries `content_sha256`, a hash of the built
    persons and careers, so a later edit is detectable.
- The A5 assembly (`cola_track_a.opening.prepare_track_a_cohort`) refuses a
  `data_provenance` label that contradicts this provenance: a cohort built
  from PSID files cannot be labelled `invented` and so cannot skip the
  issue #42 registration check, and a `registered_real` label needs a
  `psid_files` cohort. It also re-generates an `invented` cohort's frames
  from the recorded seed and refuses an unsealed, caller-assembled or
  edited cohort under either label.

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

## The 2009 wave (A1 row R6)

`Psid2010CohortSpec(anchor_wave=2009)` with
`load_psid2010_inputs(anchor_wave=2009)` builds the 2009-wave population.
`ANCHOR_LAYOUTS` holds each wave's variables with their exact labels,
verified at read time. The 2009 labels were checked against
`IND2023ER.sps` on 2026-09-23:

| Role | 2011 wave | 2009 wave |
|---|---|---|
| Interview number (family unit) | `ER34101` "2011 INTERVIEW NUMBER" | `ER34001` "2009 INTERVIEW NUMBER" |
| Sequence number | `ER34102` | `ER34002` |
| Relation to head | `ER34103` | `ER34003` |
| Age | `ER34104` | `ER34004` |
| Reported birth year | `ER34106` | `ER34006` |
| Cross-section weight | `ER34155` "CORE/IMM INDIVIDUAL CROSS-SECTION WT 11" | `ER34046` "CORE/IMM INDIVIDUAL CROSS-SECTION WT 09" |

The weight must be the only "CROSS-SECTION WT 09" label, as for 2011. The
relationship codes 10, 20 and 22 and the sequence groups (1-20 in a family,
51-59 in an institution, 71-80 moved out and 81-89 died since the previous
interview) have the same meaning in `ER34003F`/`ER34002F` as in the 2011
formats (`IND2023ER_formats.sas`).

Under the 2009 wave:

- The opening year is 2008: ages, marital status, Social Security receipt
  and opening status are as of 2008, and every wave-specific column carries
  its own year (`interview_2009`, `age_2008`, `ss_receipt_2008`,
  `marital_status_2008`, ...).
- Careers run through 2008 (`build_career` with `claim_year=2008`).
- M4 status defaults to the 2009 wave (`m4_waves=(2009,)`); no wave after
  the anchor wave may be consulted.
- Opening Social Security amounts are the 2008 amounts of the 2009 family
  and individual files (`ER46929`/`ER46931` head and wife, `ER34031`
  person-level), which `data.social_security_income` already reads and
  label-verifies.
- **Receipt start.** The reader resolves income years 2008, 2010 and 2012,
  so the income year before 2008 that would bracket a first receipt (2006)
  is not observed. Every 2008 recipient's first receipt is censored at
  2008: a retired worker's claim year is imputed at or before 2008, and
  other statuses keep 2008 as the upper bound. The R20 item of the 2009
  family file (receipt in 2007) is not used. A1 section 6 allows this
  because the start is never placed earlier than the observations allow.
- The claim-table cap (2008) may not follow the opening year.

`scripts/psid2010_cohort_structure.py --anchor-wave 2009` writes the
2009-wave structural counts. On the staged data (2026-09-23, default spec;
counts only, no benefit or statistic):

- **Members.** 12,034 persons, weighted total 175,961,799, born 1905-1980;
  10,402 outside the birth cohort and 492 with an unresolved birth year.
- **2008 receipt.** 2,067 recipients (weighted 40,128,093). Opening status:
  retired worker 1,236, disabled worker 448, survivor 383. Every recipient's
  claim year is censored at 2008 (1,236 imputed, 831 with the upper bound
  only); no imputation had an empty mass.
- **Structural cross-checks of the 2009 anchor read.** The reported 2009
  birth year (`ER34006`) equals the section 3.1 birth year for 11,915 of
  12,021 comparable members and is within one year for 12,013. For 7,315 of
  the 7,822 married members with a joinable spouse, the MH85_23 spouse is
  also the 2009 co-resident head or wife (from `ER34001` and `ER34003`).
  The family-file and individual-file amounts (income years 2008, 2010 and
  2012) agree in receipt on all 31,390 member head and wife rows (largest
  difference $12).
- **Positive `ER34046` weights outside the universe.** Institution 499
  persons, moved out since 2007 847, died since 2007 110.

Rebuilding the 2011 wave with the same code reproduced every count of the
2026-09-22 structure file above.

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
