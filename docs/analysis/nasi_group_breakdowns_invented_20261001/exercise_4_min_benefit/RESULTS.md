INVENTED DATA - NOT A COMPARISON

# Exercise 4 (Track M) by MINT8 subgroups: INVENTED dry run

INVENTED DATA - NOT A COMPARISON. Every number below comes from an INVENTED PSID-shaped cohort, INVENTED parameters and an INVENTED side frame. None is a PSID, SSA, Census or comparator value, and none is a result.

## What ran

- An INVENTED stand-in for the committed run (the registered computation, once).
- Re-execution and exact reproduction: 32 checks, all identical (exact: both sides are encoded with json.dumps(allow_nan=False) and decoded, then every leaf must be equal in type and value, every float bit for bit (float.hex, so -0.0 differs from 0.0), every mapping with the same keys and every list with the same length and order).
- Consistency of G3's Total/Female/Male cells with Track M's All/Women/Men cells: 96 checks, all identical.
- Refusal shown: a parent with `$.rows.MS0.tabulation.cells[0].share_percent` moved one ulp was refused (side-frame loader called: False).
- Location rule (for the real parent, which records the COLA history by an absolute path): the location fields ($.inputs.source.cola_history.path) are compared by their repository-relative path: an absolute path ending in /data/external/ssa_cola_history.json reads as data/external/ssa_cola_history.json on both sides, any other path is compared as written; the same record's sha256 and content_sha256 are compared exactly, and nothing else is normalized.

## Group attributes (INVENTED)

| Dimension | Classified | Unclassified | Reasons |
|---|---:|---:|---|
| Total | 120 | 0 | - |
| Sex | 120 | 0 | - |
| Race and ethnicity | 105 | 15 | code:attribute_unknown:dk_na_refused: 8, code:attribute_unknown:never_head_or_spouse: 7 |
| Country of birth | 111 | 9 | code:attribute_unknown:dk_na_refused: 1, code:attribute_unknown:never_head_or_spouse: 7, code:unresolved:us_territory: 1 |
| Age | 120 | 0 | - |
| Marital status | 120 | 0 | - |
| Highest education level | 116 | 4 | missing: 4 |
| Current-law benefit type | 120 | 0 | - |
| Current-law initial AIME quintile | 106 | 14 | missing: 14 |
| Lifetime payroll tax quintile | 106 | 14 | missing: 14 |
| Lifetime payroll tax quintile (shared) | 106 | 14 | missing: 14 |

## MS0, share receiving a minimum by group (INVENTED, percent)

| Group | Row | Option 2 | Option 3 | Option 4 | Option 5 | n |
|---|---|---:|---:|---:|---:|---:|
| Total | Total | 0.0 | 2.4 | 4.3 | 12.1 | 120 |
| Sex | Female | 0.0 | 1.0 | 1.9 | 5.8 | 66 |
| Sex | Male | 0.0 | 4.3 | 7.5 | 20.6 | 54 |
| Race and ethnicity | Hispanic or Latino, any race | 0.0 | 11.7 | 11.7 | 29.0 | 17 |
| Race and ethnicity | White, non-Hispanic | 0.0 | 1.5 | 1.5 | 8.0 | 47 |
| Race and ethnicity | Black or African American, non-Hispanic | 0.0 | 0.0 | 3.2 | 13.3 | 19 |
| Race and ethnicity | All other races, non-Hispanic | 0.0 | 0.0 | 4.4 | 9.6 | 22 |
| Country of birth | United States | 0.0 | 2.9 | 4.5 | 11.0 | 101 |
| Country of birth | Other countries | 0.0 | 0.0 | 6.9 | 38.6 | 10 |
| Age | 60–69 | 0.0 | 9.7 | 9.7 | 29.3 | 30 |
| Age | 70–79 | 0.0 | 0.0 | 6.3 | 6.3 | 28 |
| Age | 80–89 | 0.0 | 0.0 | 1.2 | 7.7 | 51 |
| Age | 90 or older | 0.0 | 0.0 | 0.0 | 0.0 | 11 |
| Marital status | Married | 0.0 | 3.0 | 3.9 | 16.3 | 70 |
| Marital status | Divorced | 0.0 | 2.6 | 8.6 | 8.6 | 28 |
| Marital status | Widowed | 0.0 | 0.0 | 0.0 | 2.8 | 15 |
| Marital status | Never married | 0.0 | 0.0 | 0.0 | 0.0 | 7 |
| Highest education level | Graduate | 0.0 | 0.0 | 0.0 | 0.0 | 11 |
| Highest education level | Bachelor | 0.0 | 0.0 | 8.9 | 27.1 | 11 |
| Highest education level | Associate | 0.0 | 0.0 | 9.1 | 24.0 | 17 |
| Highest education level | High school | 0.0 | 0.0 | 0.0 | 4.2 | 25 |
| Highest education level | Less than high school | 0.0 | 5.5 | 5.5 | 13.2 | 52 |
| Current-law benefit type | Retired worker only | 0.0 | 3.0 | 5.3 | 14.1 | 95 |
| Current-law benefit type | Widow(er) (includes dually entitled) | 0.0 | 0.0 | 0.0 | 2.8 | 15 |
| Current-law benefit type | Spousal (includes dually entitled) | 0.0 | 0.0 | 0.0 | 0.0 | 7 |
| Current-law benefit type | Disabled worker only | 0.0 | 0.0 | 0.0 | 30.3 | 3 |
| Current-law initial AIME quintile | Highest | 0.0 | 0.0 | 0.0 | 0.0 | 21 |
| Current-law initial AIME quintile | Second highest | 0.0 | 0.0 | 0.0 | 0.0 | 20 |
| Current-law initial AIME quintile | Middle | 0.0 | 0.0 | 0.0 | 0.0 | 21 |
| Current-law initial AIME quintile | Second lowest | 0.0 | 0.0 | 5.9 | 28.9 | 20 |
| Current-law initial AIME quintile | Lowest | 0.0 | 12.7 | 17.0 | 36.3 | 24 |
| Lifetime payroll tax quintile | Highest | 0.0 | 0.0 | 0.0 | 0.0 | 21 |
| Lifetime payroll tax quintile | Second highest | 0.0 | 0.0 | 0.0 | 0.0 | 20 |
| Lifetime payroll tax quintile | Middle | 0.0 | 0.0 | 0.0 | 0.0 | 21 |
| Lifetime payroll tax quintile | Second lowest | 0.0 | 0.0 | 0.0 | 16.4 | 19 |
| Lifetime payroll tax quintile | Lowest | 0.0 | 12.0 | 21.3 | 46.2 | 25 |
| Lifetime payroll tax quintile (shared) | Highest | 0.0 | 0.0 | 0.0 | 0.0 | 20 |
| Lifetime payroll tax quintile (shared) | Second highest | 0.0 | 0.0 | 0.0 | 0.0 | 23 |
| Lifetime payroll tax quintile (shared) | Middle | 0.0 | 0.0 | 0.0 | 12.2 | 20 |
| Lifetime payroll tax quintile (shared) | Second lowest | 0.0 | 11.9 | 15.4 | 31.2 | 19 |
| Lifetime payroll tax quintile (shared) | Lowest | 0.0 | 2.7 | 9.1 | 24.7 | 24 |

## Not computed

- `poverty_status`: not computed: MINT8's poverty status and household income quintile need each person's 2022 household (family) money income and, for poverty, the official threshold of the family's size and composition; Track M's inputs (min_benefit_track_m.structure.TrackMStructureInputs: the 2023 anchor, the family file's 2022 Social Security of the reference person and spouse, death records, marriage history, the labor-income panel and the design; and the receipt and next-wave labor-income frames of cohort.TrackMCohortInputs) carry neither, and this package reads no new PSID item
- `household_income_quintile`: not computed: MINT8's poverty status and household income quintile need each person's 2022 household (family) money income and, for poverty, the official threshold of the family's size and composition; Track M's inputs (min_benefit_track_m.structure.TrackMStructureInputs: the 2023 anchor, the family file's 2022 Social Security of the reference person and spouse, death records, marriage history, the labor-income panel and the design; and the receipt and next-wave labor-income frames of cohort.TrackMCohortInputs) carry neither, and this package reads no new PSID item
- `mint8_benefit_statistics`: not computed: MINT8's benefit statistics compare each person's benefit under the option with the same person's current-law benefit.  Track M's evaluate() returns, per person, only the receipt flags receives_2..receives_5, the receipt basis and the exposure flags (min_benefit_track_m/evaluation.py evaluate); per worker record it returns the PIA under the row's PIA rule, before any option's cut or minimum (WorkerOutcome.pia), and each option's PIA (WorkerOutcome.outcomes[k].option_pia, rules.evaluate_worker), but no person-level benefit: the own benefit after the claim factor is not formed, and a spouse's or survivor's benefit is decided only as paid or not (rules.spouse_excess_paid and rules.survivor_excess_paid return booleans).  The registered options also have no current-law column: option 1 is 'Reduced current law', a 12.45 percent uniform cut (policy.OPTIONS[1]).  Computing these statistics would need a person-level benefit model this breakdown does not add
- `mint8_poverty_statistics`: not computed: MINT8's poverty status and household income quintile need each person's 2022 household (family) money income and, for poverty, the official threshold of the family's size and composition; Track M's inputs (min_benefit_track_m.structure.TrackMStructureInputs: the 2023 anchor, the family file's 2022 Social Security of the reference person and spouse, death records, marriage history, the labor-income panel and the design; and the receipt and next-wave labor-income frames of cohort.TrackMCohortInputs) carry neither, and this package reads no new PSID item

## Reproduce

```
python scripts/min_benefit_groups_dry_run.py
```

`result.json` holds the full document. INVENTED DATA - NOT A COMPARISON.
