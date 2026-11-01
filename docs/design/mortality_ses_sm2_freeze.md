# SM2 freeze: sources, mappings, joint route, paths and conformance

*Design record, 1 November 2026, branch `mgf-sm2-freeze-20261101`, written
from `origin/master` `1808285925a069143047ae7e7bb2412012db0ad7` by the
mortality, groups and financing lane's SM2 freeze job (Subfleet build,
Claude Code, Opus 5.5).*

## 1. Status and authority

**This record freezes SM2 under section 5.1 of the lane design**
(`docs/design/mortality_groups_financing.md`): "Source hashes, module
versions, seeds, populations, estimands, tolerances and alternatives are
frozen before any real-data outcome is computed." **It is not a
registration on #42, and it claims no blind status.** The job that wrote
it read every source it freezes, so it and this file count as exposed to
those sources; nothing here feeds a blind role.

- **Verification class.** External-target conformance, labeled
  **"calibrated, not validated"** (design section 3.2): SM2 admits that
  the fitted relative risks reproduce the targets they were fitted to,
  never that the model predicts. SM2 claims **no prospective prediction
  origin and no unused holdout** (S0.1 section 2.4). The held-out test of
  the gradient is SM3.
- **Authority.** Max approved the lane design, with its methodology, on
  23 October 2026 (decision d1922). S0.1's audit
  (`docs/design/s0_1_source_audit.md`, #588, merged 1 November 2026) is
  this record's input; its section 2 is SM2's record. Its header says a
  review and the gate's registration "confirm or amend" each
  **[proposed]** item before any outcome is computed, and "may tighten or
  rescope it but never loosen it". This record tightens or rescopes in
  the places section 2's table names, and loosens nothing.
- **Rulings that bind this record, unamended.**
  - **Q4:** relative risks are normalized within each single age × sex ×
    year cell to the baseline's expected deaths (SM1's normalizer,
    `src/populace_dynamics/mortality_ses/normalizer.py:328–382`).
  - **Q5:** lifetime earnings is the primary dimension; education and race
    and Hispanic origin are further dimensions of the same model.
  - **Q6:** the gradient holds at its last observed level as the primary
    path; a widening path is a registered alternative.
  - **Q11:** SM owns death alignment.
- **What it computes.** Nothing. This record states no fitted
  coefficient, no contrast between categories, no life expectancy and no
  comparison between sources' gradients, and it prints no source table
  value. It names tables, pages, age bands, years and categories only.
  Every number in it is a year, an age, a page, a count of table cells or
  targets, a code from a codebook, a tolerance the design or S0.1 sets, or
  a rule this record sets.
- **Data.** No PSID, HRS, SIPP or NHIS microdata file was opened, and
  nothing was computed on real data. PSID use follows the project's
  data-access record. DYNASIM, Urban Institute and PWBM material is not
  used or compared; it reaches these gates only through a validation lane
  (S0.1 scope). CBO publication 49659 stays closed; its methods count as
  open until a validation lane supplies a bounded definitions-only
  extract.
- **Markers.** **[frozen here]** marks a decision this record makes.
  **[frozen, S0.1 §x]** keeps a decision S0.1 already froze, with its
  pointer. **[open]** marks an item this record leaves unsettled and names
  what settles it. **[for Max]** marks a call section 12 sends up.

## 2. Item table

S0.1's section 2 runs from line 324 to line 707 of the audit at
`18082859`. This command recounts its bracketed markers that contain
"proposed" or "open":

```
sed -n '324,707p' docs/design/s0_1_source_audit.md \
  | grep -oE '\[[^]]*(proposed|open)[^]]*\]' | wc -l
```

It returns **20**. The rows S2-01 to S2-20 below take them in the audit's
order. A word search over the same lines
(`awk 'NR>=324 && NR<=707 && /(^|[^a-z])(open|proposed|pending|unsettled)([^a-z]|$)/'`)
finds five more lines that call something open or proposed without a
bracketed marker; rows S2-21 to S2-25 cover them, so the table has
**25 rows**. Where a row says "tightened" or "rescoped", the change is
narrower than S0.1's proposal or adds a requirement; no row loosens one.

| Row | Audit line | S0.1 item | Resolution | Where | State |
|---|---|---|---|---|---|
| S2-01 | 424 | **[proposed]** mapping assumption: OACT rate ratios used directly as annual-q multipliers, reported with the dynamic-AIME versus frozen-rank distinction and the beneficiary population difference | Confirmed and tightened: adds Study 129's exposure convention (deaths get a full year of exposure, so the published rates are initial-exposure probabilities, p. 5 and Appendix B pp. 13–14), the age-basis mapping, and three named mapping assumptions (M-E2 to M-E4) that every report carries | §4.1 | frozen here |
| S2-02 | 440 | **[open]** availability of earlier NCHS education editions | Settled by the NVSR listing and twelve earlier *Deaths: Final Data* reports: 2010–2017 cover reporting states only (31 rising to 49 states plus DC); 2018–2020 are national in the internet tables I–7 and I–19; 2021–2022 are national in printed Table 14 and Table VIII; no edition for 2023 is listed on 1 November 2026. The fit uses 2018–2022; 2010–2017 form a labeled sensitivity | §3.2 | frozen here |
| S2-03 | 474 | **[open]** harmonization of earlier NHIS years | Rescoped to NHIS 2009–2018 sample adults. The 2009, 2016 and 2018 layouts carry `EDUC1`, `HISPAN_I`, `RACERPI2`, `AGE_P`, `SEX`, `SRVY_YR`, `INTV_QRT` and `HHX`/`FMX`/`FPX` with identical code lists; the design variables are `STRAT_P`/`PSU_P` in 2009 and `PSTRAT`/`PPSU` in 2016 and 2018. The fit job checks each intervening year's layout against these names before use | §3.4 | frozen here (window and variables); intervening layouts checked by the fit job |
| S2-04 | 481 | **[open]** a three-dimension joint gradient conditional on lifetime earnings | Resolved by the joint route: joint marginal calibration on a public reference population, with the earnings–education–race dependence taken from a stated proxy. The dependence itself stays unidentified in public data, and §6.4 says so | §6 | frozen here (route); the dependence stays unidentified and named |
| S2-05 | 511 | **[open mapping]** Cristia's odds ratios | Frozen: predicted probabilities on a named reference population, then ratios to `q3`'s probability. Cristia enters only as a sensitivity and a source reported beside the fit; no log odds ratio enters as a log relative risk | §4.4 | frozen here |
| S2-06 | 520 | **[proposed]** CBO 41681 as context only | Confirmed. It supplies the reason the widening alternative leaves race and Hispanic origin flat (pp. 1–2) and no coefficient or target | §3.1, §7.4 | frozen here |
| S2-07 | 538 | **[proposed schema]** dimensions, columns, categories, references and unclassified treatment | Confirmed against `mortality_ses/specification.py`; tightened to one unclassified string per dimension, a fixed category order, and a crosswalk per source | §8 | frozen here |
| S2-08 | 564 | **[proposed loader]** OACT contrasts `log(r_q) − log(r_q3)`, band expansion, a source-year matrix that says what happens before a band first appears | Confirmed; tightened with the band-backcast rule, the figure-year rule and two independent table transcriptions | §3.1, §4.1, §5 | frozen here |
| S2-09 | 570 | **[open]** earnings ages below 62 and 90–120 | Frozen: the 62–64 coefficient holds down to age 25 and the age-25 value below; the 85–89 coefficient holds up to 120; three registered sensitivities | §5 | frozen here |
| S2-10 | 579 | **[open]** terminal 100+ rule and any unsupported other-group coefficient | Frozen: race contrasts at 100–120 hold the age-99 contrast, and the 100+ interval is not read as a contrast; `other_non_hispanic` comes from NHIS–LMF, with NCHS's AIAN and Asian tables reported beside as a partial group | §4.3, §5 | frozen here |
| S2-11 | 587 | **[open]** extraction and digitization of the 2022 gradient, its uncertainty, complete coverage | Frozen: vector extraction of Study 129 Figures 7–12, validated against Tables 7–12 at every table year, with a digitization half-width the validation sets; complete tables at every knot | §7.1–7.3 | frozen here |
| S2-12 | 591 | **[open]** widening `CoefficientPath`: slope, origin, ages, caps; knot years and synchronization | Frozen: origin 2024, slopes from a frozen estimator on OACT's pre-pandemic annual figures, caps of 30 years and a 1.5 multiplier, race held flat; annual knots 2010–2024 with one synchronization rule | §7.4–7.5 | frozen here |
| S2-13 | 602 | **[proposed]** `unclassified_rule="reference"` for SM3's overall denominator | Confirmed for SM3; `refuse` for conformance runs and for any projection until the frame carries the attributes | §8.3 | frozen here |
| S2-14 | 606 | **[open: identification]** marginal contrasts do not determine mutually adjusted coefficients; freeze a joint route and its reference distribution | Five candidate routes and one unavailable route; primary JR-C; JR-A (plain addition, labeled), JR-B, JR-D and JR-E as sensitivities | §6 | frozen here |
| S2-15 | 629 | **[open]** exact release dates of any earlier NHIS cohort used | Left open. The linked-mortality `.dat` files carry the listing date 26 April 2022; each NHIS year's release date settles from that year's survey description, which the fit job records. Nothing in SM2 depends on it, because SM2 claims no prospective origin | §3.4 | left open; settled by the fit job's per-year release ledger |
| S2-16 | 641 | **[frozen tolerance; proposed operationalization]** e65 target from source ratios on one baseline, with a fixed reference population, marginalization and tail rule | Frozen; the 0.1-year limit stays | §9.2 | frozen here (operationalization); tolerance frozen, S0.1 §2.5 |
| S2-17 | 649 | **[open]** whether the different source populations and baselines can satisfy the targets together | The procedure is frozen: one joint calibration per knot on one reference population, and a named failure when it cannot reproduce every target. Whether it can is an outcome, so this record does not settle it | §6.3, §9 | left open; settled by the fit under §9's rule |
| S2-18 | 659 | **[open until the loader plan is frozen]** the critical family's integer size and which joint-survey targets it holds | Frozen: **6,884** targets, itemized | §9.4 | frozen here |
| S2-19 | 677 | **[proposed named procedure]** `SM2_SOURCE_RECONSTRUCTION_AND_CLUSTER_BOOTSTRAP` | Filled in step by step | §9 | frozen here |
| S2-20 | 688 | **[proposed suppression]** at least 100 unweighted persons per published microdata subgroup | Confirmed and tightened: also at least 20 deaths in any published death-based cell, and the rule applies to ACS as well as NHIS aggregates | §11.5 | frozen here |
| S2-21 | 353 | Unmarked: CBO 49659's "safely bounded definitions remain open" | Left open as the brief requires; SM2 uses no part of 49659 | §3.1 | left open; settled by a validation lane's definitions-only extract |
| S2-22 | 523 | Unmarked: "CBO 49659's mixed-source methods remain open pending a safely bounded definitions-only extract" | Same item as S2-21 | §3.1 | left open; as S2-21 |
| S2-23 | 588 | Unmarked: "A 2020 table-only path is a proposed registered sensitivity" | Confirmed as sensitivity P-TABLE; it cannot become primary without amending Q6 | §7.3 | frozen here |
| S2-24 | 669 | Unmarked: a source that does not publish the uncertainty a target needs leaves that item "open or inconclusive" | Applied: OACT publishes no deaths or exposures, so OACT's random-variation component stays open, with the consequences §9.3 states | §9.3 | left open; settled by OACT exposure or death counts by sex × band × quintile × year |
| S2-25 | 698 | Unmarked: "`SOURCE_UNAVAILABLE` / open identification applies to the complete modern three-dimension joint source and missing source-age mappings" | Each trigger and fallback stated | §10 | frozen here |

**Counts.** Of the 25 rows, 20 are frozen here, 5 are left open with what
settles them (S2-15, S2-17, S2-21, S2-22, S2-24), and none goes to Max as
a row. S2-03 is frozen with a check the fit job performs. Section 12 holds
the two calls that go to Max; neither comes from a row of this table.
