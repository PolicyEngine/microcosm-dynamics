# Urban 2010 COLA comparison: specification for DynaSim scorecard exercise 1

- **Status:** draft for referee; not ratified. This draft authorizes no
  run, no registration comment and no computation of the five-group 2030
  statistic on real data. It becomes the frozen specification only if Max
  ratifies it by merging the PR that carries it (plan §6, item 4).
- **Specification:** `urban2010_cola_exercise1`, version `a1-draft-2`,
  drafted 2026-09-22; `a1-draft-2` carries the corrections of referee
  pass 1 (§25).
- **Plan item:** A1 of the Track A plan,
  `EVID/critical-path-cola-20260922.md` §4 (SHA-256 `e303ba57…`), where
  `EVID` = `~/microcosm-launch-evidence/dynasim-parity-20260909`.
- **Resolves:** the 15 null fields under `required_unresolved` in the
  `proposed-1` specification,
  `EVID/parallel-oasdi-20260920/deliverables/dynasim-specification.md`
  (SHA-256 `c220b213…`). §20 maps each field to the section that
  resolves it.
- **Starting point:** the plan's §4 table "Proposed specification entries
  for A1". §20 lists the places this draft adds to or departs from that
  table.
- **Claim class (pending decision 1, §22):** a registered, one-shot,
  reported-not-gated comparison, the evidence class of the six DYNASIM
  anchor replications (`paper/paper.qmd`, "The replication anchors";
  `runs/replication_*_v1.json`).
- **Labels every output carries:** *PSID-seeded closed cohort*; *Python
  oracle (not Axiom)*; *fixed-path mechanical incidence*.
- **Builder boundary:** a model-builder lane wrote this draft. It did not
  open the sealed comparator directory, the seal file, Figure 2, the
  page-3 image or the Urban PDF, and it did not look up Urban or DYNASIM
  results for this exercise. It did read three passages of page-3 *text*
  in the Urban text extraction: the outcome sentence (lines 125–126), the
  source line (line 160) and the opening clause of line 164. §2
  discloses them and states what rests on them; they are a question for
  Max (§23, question 10). §2 lists what it read.

## 1. Target

The target is the COLA option in Urban Institute (2010), *Distributional
Effects of Alternative Social Security Reforms: Details Matter*
(publication 412102):

- **Model and run:** DYNASIM3 run 614, dated April 2009, using the 2008
  Trustees' assumptions (source line,
  `EVID/urban-2010-reform-details.txt:160`).
- **Outcome:** the effect on benefits received in 2030 and 2050,
  measured relative to benefits scheduled under current law
  (`:125–126`). This exercise scores 2030 only.
- **Age groups:** 50–61, 62–64, 65–69, 70–79 and 80+.
- **Disability beneficiaries:** included.

The age groups and disability inclusion come from the `target` block of
the `proposed-1` specification. This builder did not re-verify them
against the figure, by design (§23, §24). The run identity and outcome
above rest on page-3 text (§2, disclosure); the same `target` block
records the same run, run date and Trustees vintage (`"run": "614"`,
`"run_date": "2009-04"`, `"trustees_vintage": 2008`), and its locators
cite the same two lines.

**Baseline.** The baseline is scheduled benefits under the law TR2008
assumes. TR2008 reports no legislation with a significant effect on OASDI
finances between April 23, 2007 and the 2008 report (§III.B, printed
p. 31), and counts as program cost "all benefits scheduled under current
law" (p. 32). Under the TR2008 intermediate assumptions the DI trust fund
is exhausted in 2025 (Table IV.B3, p. 55). The scheduled-benefit baseline
ignores that exhaustion, consistent with the Urban outcome wording.

## 2. Sources

This draft cites only the sources below. Page numbers are the printed
page numbers of each document.

| Source | Local file | SHA-256 | What this draft used |
|---|---|---|---|
| Track A plan | `EVID/critical-path-cola-20260922.md` | `e303ba57…` | §1, §3, §4 (A1 row and the "Proposed specification entries for A1" table), §6, §7, §9 |
| `proposed-1` specification | `EVID/parallel-oasdi-20260920/deliverables/dynasim-specification.md` | `c220b213…` | `target`, `required_unresolved`, `proposals_not_adopted` and the convention table |
| Urban (2010), text extraction | `EVID/urban-2010-reform-details.txt` | `0826fc19…` | Page 1: lines 44–55 (footnotes). Page 2: lines 56–90 (Table 1). Page 3: lines 125–126 (outcome sentence) and 160 (source line); see the disclosure below. Page 6: lines 406–417 (references) |
| 42 U.S.C. 415 excerpts | `EVID/tr2008-inputs-20260922/usc-42-415-excerpts.txt` | `a323ca47…` | Whole file: 415(a)(3)(B) and 415(i)(1)–(i)(2)(B) |
| 2008 OASDI Trustees Report (TR2008) | `EVID/tr2008-inputs-20260922/tr08-2008-oasdi-trustees-report.pdf` | `517de81a…` | Re-parsed with `pdftotext -layout`; pp. 31–32, 55, 75, 85–86, 89, 92–93, 100–106, 124–125, 163–165, 182–185 |
| DYNASIM3 primer (Favreault and Smith 2004) | `~/PolicyEngine/dynasim-refs/410961-dynasim3-primer.txt` | `0ad06f68…` | Whole file |
| DYNASIM3 brief overview (Urban, updated March 23, 2015) | `~/PolicyEngine/dynasim-refs/dynasim3-brief-overview.txt` | `1ca61f02…` | Whole file. It postdates run 614 |
| Repo precedent: Mermin-row replication | `runs/replication_mermin_rows_v1.json` | `c55c2f35…` | `anchor_provenance`, `conventions` |
| Mermin (2005), DYNASIM3 run 432 (a different exercise) | `~/PolicyEngine/dynasim-refs/411260-benefit-reductions.txt` | `4b9f3bec…` | Footnotes 6–7 (p. 2) and one passage on p. 7, to confirm the precedent's quotations |
| Realized SSA COLA series | `data/external/ssa_cola_history.json` | `12da7f0e…` | Determination-year values 1975–2022 and `historical_timing` |
| Repo code, for conventions only | `estimates/ledgers.py` (`_monthly_benefit_path`), `estimates/parameters.py` (`REPORT_YEARS`), `engine/rng.py` (`DRAW_SEED_BASE`), `estimates/first_report.py` (draw aggregates), `harness/panel.py` (`split_panel_by_person`), `ss/__init__.py`, `ss/benefits.py` (`spousal_benefit`, `widow_benefit`), `scripts/replication_mermin_rows.py` (`_abs_gaps`), `scripts/reform_delta_diagnostic.py` (`_summary`) | — | Read this session |
| Repo paper | `paper/paper.qmd` | — | "The replication anchors" (reported, not gated; registered before the run; published regardless) |
| PSID setup files, labels only | `~/PolicyEngine/psid-data/ind2023er/IND2023ER.sas`, `~/PolicyEngine/psid-data/family/2011/FAM2011ER.sas` | — | Labels of ER34001, ER34046, ER34101, ER34154, ER34155, ER48430 and ER52337–ER52342. No PSID values were read |

**Not opened:** `EVID/cola-comparator-20260922/`,
`EVID/cola-comparator-seal-20260922.json`, `EVID/urban-2010-page3.png`,
`~/PolicyEngine/dynasim-refs/412102-details-matter.pdf` (not opened at
all), `EVID/cola-comparison-draft.json`, `EVID/cola-source-*.md` and
`EVID/cola-metadata-followup.md`. SSA's web page for its TR2008 "A1"
solvency provision, which `proposed-1` cites, is outside this source set
and is not used as a basis.

**Disclosure: page-3 text.** In the Urban text extraction, page 3 is
lines 121–207 (the form feeds that open pages 2, 3 and 4 fall on lines
56, 121 and 208). Page 3 carries Figure 2. The drafting lane read three
passages there:

- lines 125–126, the outcome sentence (§1, "Outcome");
- line 160, the source line naming run 614, April 2009, and the 2008
  Trustees' assumptions (§1, "Model and run"; §4, rate-path basis);
- the opening clause of line 164, printed by a line-number search. The
  clause refers to Figure 2 qualitatively and contains no number. No
  field in this document relies on it.

The drafting lane recorded that the line-164 clause contains no number;
it recorded no such statement for lines 125–126 and 160. The run
identity, the 2030 outcome year and the scheduled-benefit baseline are
also in the `target` block of `proposed-1` (§1); the 2050 outcome year
is not. Referee pass 1 did not read any line from 121 to 207, so it did
not re-verify these quotations (§24, §25). Whether this contact is
acceptable under the builder rule is question 10 of §23.

## 3. Policy

Urban Table 1 (`:60–62`, p. 2):

- Current law, as Table 1 describes it: once benefits begin, they rise
  each year by the change in the CPI.
- Option, verbatim: "Reduce COLAs by 1 percentage point each year,
  starting in 2010."

The frozen policy:

1. The reform subtracts 0.01 from each annual benefit-increase rate
   expressed as a fraction (1.0 from the percentage). It changes a rate;
   it is not a one-time proportional cut in the benefit level.
2. It applies to the automatic increase of 415(i)(2)(A)(ii): the
   increase to "the primary insurance amount of each other individual on
   which benefit entitlement is based" and to the other amounts that
   clause lists (excerpt lines 47–55).
3. The subtraction applies after the CPI increase percentage is rounded
   to the nearest tenth of 1 percent (415(i)(1)(D), line 33). Every rate
   on the TR2008 path is a multiple of 0.1, so the order does not change
   any value.
4. Nothing else changes. CPI and AWI series, bend points, the
   contribution and benefit base, earnings-test exempt amounts and SSI
   stay at baseline. The reform does not reach any other program.
5. Each reduced increase applies to every amount that 415(i)(2)(A)
   increases at that date: the amounts of clause (ii), including
   benefits of people on the rolls before 2010, and, under clause (iii),
   the primary insurance amount of an individual who is eligible but not
   yet entitled: that amount, "without regard to the time of entitlement
   to that benefit", is increased "by the amount of that increase and
   subsequent applicable increases" (line 57; the clock of §6).
   Increases before the first reduced increase stay as they were.
   Table 1 states no exemption, and 415(i)(2)(A)(ii) applies each
   increase to each amount "as previously increased" (line 55).

## 4. Rate path

**Primary:** TR2008 intermediate assumptions (alternative II, "the
Trustees' best estimate", p. 32). No alternative row. Basis: the Urban
source line names the 2008 Trustees' assumptions (`:160`). The DYNASIM3
documentation says the model typically uses SSA's intermediate mortality
assumptions (primer pp. 6–7) and calibrates to the Trustees' inflation
assumptions (overview p. 2).

Increases are indexed by *determination year* `t`: the increase takes
effect in December of `t` and first appears in January `t+1` payments.
TR2008 Table V.C1, footnote 1 (p. 103): increases are "Effective with
benefits payable for June in each year 1975-82, and for December in each
year after 1982." The statute applies each increase to "monthly benefits
... for months after November" of the determination year (415(i)(2)(B),
line 59).

| Determination year `t` | Takes effect | First paid | Baseline (%) | Source | Reform, R0 (%) | Reform, R1 (%) |
|---|---|---|---|---|---|---|
| 2008 | Dec 2008 | Jan 2009 | 2.7 | V.C1 intermediate, p. 102 | 2.7 | 2.7 |
| 2009 | Dec 2009 | Jan 2010 | 2.5 | V.C1 intermediate, p. 102 | **1.5** | 2.5 |
| 2010–2017 | Dec `t` | Jan `t+1` | 2.8 | V.C1 intermediate, p. 102 | **1.8** | **1.8** |
| 2018–2030 | Dec `t` | Jan `t+1` | 2.8 | Reconstruction (below) | **1.8** | **1.8** |

Bold marks reduced rates. R0 and R1 are the two first-application rows
of §5.

**Reconstruction for 2018–2030.** Table V.C1 stops at 2017 (TR2008 shows
automatically adjusted parameters "through 2017", p. 100). This draft
sets every later increase to 2.8 percent. The TR2008 statements it rests
on:

- §V.B.2 (p. 89): under the intermediate assumptions "the annual change
  in the CPI is assumed to decrease from 2.8 percent for 2007 to
  2.5 percent for 2009, then rise gradually to the assumed ultimate rate
  of 2.8 percent for 2010 and later". The ultimate rates are 1.8, 2.8 and
  3.8 percent for the low cost, intermediate and high cost assumptions.
- Table V.B1 (p. 92): intermediate CPI change of 2.8 for each year
  2010–2017 and for the periods 2015–2020 and 2020–2082.
- Table VI.F6 (p. 184): the intermediate adjusted CPI-W is 127.81 (2017),
  138.85 (2020), 159.41 (2025) and 183.02 (2030). The implied annual
  growth rates are 2.800, 2.800 and 2.801 percent (computed by this
  draft). The CPI-W "is the index used to determine annual increases in
  OASDI monthly benefits payable after the year of initial eligibility"
  (p. 182).

With constant 2.8 percent CPI-W growth, the third-quarter-to-third-quarter
change that 415(i)(1)(A), (D) and (G) define is also 2.8 percent after
rounding. This is a reconstruction, not a published TR2008 value.

**Stabilizer check.** 415(i)(1)(C)(ii) replaces the CPI increase with the
lower of the CPI and wage increases when the OASDI fund ratio is below
20.0 percent (lines 29–31). The TR2008 intermediate OASDI trust fund
ratio is 378 (2010), 385 (2017), 361 (2020), 302 (2025) and 221 (2030)
(Table IV.B3, p. 55); no listed year from 2008 to 2030 is below 221. The
table lists every year from 2008 to 2017 and then only 2020, 2025 and
2030; this draft infers that 2018–2019, 2021–2024 and 2026–2029 also
stay far above 20. TR2008 defines its trust fund ratio as assets at the
beginning of a year as a percentage of the year's projected cost
(p. 32). This draft uses it as a proxy for the statutory OASDI fund
ratio of 415(i)(1)(F) (lines 37–41), whose denominator is the
Commissioner's estimate of the year's payments. This draft judges that
the difference in denominators cannot plausibly move a ratio of 221 or
more below 20. The table's note says that combined ratios for
years after the DI fund's 2025 exhaustion "are theoretical and are shown
for informational purposes only"; the scheduled-benefit baseline (§1)
uses them as they stand. The applicable increase is therefore the CPI
increase in every year of the window. The reform lowers outgo, which can
only raise the ratio.

**Floor check.** On this path the reduced rate never reaches zero:

- The lowest baseline rate in the reformed window is 2.5 (determination
  year 2009) under R0 and 2.8 under R1. The lowest reduced rate is 1.5
  under R0 and 1.8 under R1.
- Every reduced rate is therefore "greater than zero", so every year
  remains a cost-of-living computation quarter (415(i)(1)(B), line 25).
- For robustness only (not registered), the TR2008 low cost and high cost
  paths give lowest reduced rates of 0.8 and 1.8 under R0.
- **Frozen floor rule (inactive):** if a reduced rate were zero or
  negative, no increase would be paid that year, matching the (i)(1)(B)
  condition; the benefit would never fall in nominal terms.
  Implementations assert that the reduced rate is positive for every
  reduced determination year of every row, through 2030, and fail closed
  otherwise. A failed assertion means the parameter file differs from
  this specification.

**Splice rule.** This rule resolves the `proposed-1` field
`trustees_alternative_and_parameter_splice`:

- Every rate that enters a reform ratio (determination years 2009–2030)
  is the TR2008 intermediate value. No realized rate enters any ratio.
- The realized SSA series must not replace the TR2008 path.
  `data/external/ssa_cola_history.json` records 5.8 for 2008 and 0.0,
  0.0, 0.0 and 0.3 for 2009, 2010, 2015 and 2016. On that series the floor
  would bind in four years.
- Increases for determination years before 2008 enter only levels. For
  those years the realized series may be used: its 1975–2007 values
  equal TR2008 V.C1's historical and actual values (p. 102), including
  2.5 for 1999 (fn. 6), as referee pass 1 checked value by value.
- Levels that act only as weights may be observed. The opening stock's
  2010 Social Security amounts (§14) embed the realized increases for
  every determination year from the clock (§6) through 2009; for a clock
  that started in 2008 or earlier these include December 2008
  (5.8 percent) and December 2009 (0.0 percent). A PIA the oracle
  computes on the TR2008 path carries 2.7 and 2.5 for those two years
  only when its clock started in 2008 or earlier, 2.5 alone when the
  clock started in 2009, and neither when it started in 2010 or later.
  From the increases alone, the opening-stock level therefore differs
  from a TR2008-path level on the same clock by 1.058 / (1.027 × 1.025)
  − 1 ≈ +0.5 percent (clock 2008 or earlier) and 1.000 / 1.025 − 1 ≈
  −2.4 percent (clock 2009). This is a named delta (§12).

## 5. First reduced increase

| Row | First reduced increase | First reduced payment | Reduced increases in 2030 payments for a clock that started in 2009 or earlier |
|---|---|---|---|
| **R0 (primary)** | Takes effect December 2009 (determination year 2009) | January 2010 | 21 (determination years 2009–2029) |
| R1 | Takes effect December 2010 (determination year 2010) | January 2011 | 20 (determination years 2010–2029) |

**Basis.** The Table 1 phrase "starting in 2010" does not say whether
2010 is the year of the first reduced increase or of the first reduced
payment. R0 reads it in payment terms. R1 reads it as the first
increase that takes effect in calendar 2010. The December effective
month is statutory (415(i)(2)(B): benefits "for months after
November"). The excerpts do not state when a month's benefit is paid;
the January first payment is the timing the repo's realized series
records ("effective in December of the determination year and first
reflected in January payments of the following year",
`ssa_cola_history.json` `historical_timing`). The plan also reports,
citing `proposed-1`, that SSA's TR2008 A1 provision starts in December
2009; this draft did not verify that and does not rely on it.

Both rows are registered because neither reading is settled. Per the
plan's §1 arithmetic, the 80+ cell depends almost entirely on this
choice.

## 6. Exposure clock and existing beneficiaries

**Primary (R0): statutory eligibility clock.** Person *i*'s benefit
receives the reduced version of the increase for determination year `t`
exactly when `max(clock_i, first) ≤ t ≤ last`, where `first` comes from
§5 and `last` from §10. `clock_i` is the year from which the PIA that the
benefit rests on receives increases:

| Benefit | `clock_i` | Basis |
|---|---|---|
| Retired worker | Year of attaining 62; in the annual model, birth year + 62 | 415(a)(3)(B)(i), lines 10–12 |
| Disabled worker | Year the period of disability began; in the annual model, A4's onset year. If A4 simulates award years only, the award year. The period of disability cannot begin after the award, so this can only understate the count (named delta) | 415(a)(3)(B)(ii), line 14 |
| Worker who died before eligibility | Year of death | 415(i)(2)(A)(iii), "or who dies prior to becoming so eligible", line 57 |
| Disabled worker converted at full retirement age | Keeps the disability clock; the conversion does not reset accumulated increases | 415(i)(2)(A)(ii) carries amounts "as previously increased"; the conversion mechanics are outside this draft's excerpts |
| Spouse, aged widow(er), disabled widow(er) | The worker's clock, not the auxiliary's own age or entitlement date | The increase applies to "the primary insurance amount of each other individual on which benefit entitlement is based", 415(i)(2)(A)(ii)(II), line 51 |
| Dual entitlement | Each PIA keeps its own clock (§11) | Same |

415(i)(2)(A)(iii) also gives a person who becomes eligible in a year with
an increase that year's increase "without regard to the time of
entitlement" (line 57).

Precedent: Mermin (2005), a DYNASIM3 study, says in footnote 7 (p. 2)
that COLAs start in the year of first eligibility (age 62, disability or
death), not the year of first benefit receipt. On p. 7, in its
price-indexing discussion, it notes that spouses of older retirees often
receive benefits resting on a benefit computation made several years
before they reach retirement age. The
repo records the footnote in `replication_mermin_rows_v1.json`
(`anchor_provenance.cola_mechanics.paper_cola_start_note`).

**Alternative (R2): entitlement clock.** Only increases with
`max(first, entitle_i) ≤ t ≤ last` are reduced. `entitle_i` is the
beneficiary's own first year of entitlement to the benefit being paid:
the claim year for a retired worker, the award year for a disabled worker
and the auxiliary's own entitlement year for an auxiliary. Increases
between `clock_i` and `entitle_i` keep the baseline rate in both
scenarios, so baseline amounts are identical under R0 and R2; only the
reform's reach differs. Basis: Table 1 describes current-law COLAs as
increases that apply once benefits begin.

**Existing beneficiaries.** Anyone entitled before the first reduced
increase receives every reduced increase from `first` on. Under R0, a
2010 beneficiary whose clock started in 2009 or earlier has 21 reduced
increases in 2030 payments. Opening-stock clocks (the opening year is
2010, or 2008 under R6):

- Retired workers: birth year + 62.
- Spouses and widow(er)s aged 62 or older in the opening year, as A3
  classifies them: the linked worker's clock (the table above) when A3
  links the worker, otherwise the person's own birth year + 62. Every
  such clock is at or before the opening year, so the fallback can change
  a count only under R0 and its one-field variants that keep R0's first
  increase and opening year, and only when exactly one of the two clocks
  is 2010; the change is one increase.
- DI and survivor beneficiaries under 62 in the opening year: A3 freezes
  a rule that places the start of receipt no earlier than the
  observations allow, so the count is never overstated. Under R0 the
  understatement is at most one increase, for people first observed
  receiving in 2010; under R6 every such clock is at or before 2008 and
  so is not later than `first` (2009), and no increase is lost.

## 7. Statistic

**Primary (R0): weighted ratio of scenario means.** For draw *k* and age
group *g*:

```text
Δ[g,k] = 100 × ( Σ_{i∈S[g,k]} w_i · B_reform[i,k]
                / Σ_{i∈S[g,k]} w_i · B_base[i,k]  − 1 )
```

The run reports the mean of `Δ[g,k]` over k = 0…19 and its sample
standard deviation (divisor K − 1), the convention of the draw aggregates
in `estimates/first_report.py`. Membership `S[g,k]` is common to both
scenarios (§8) and `w_i` does not depend on the scenario, so this equals
the ratio of weighted totals.

**Alternative (R3): weighted mean of individual ratios.**

```text
Δ'[g,k] = 100 × ( Σ_{i∈S[g,k]} w_i · (B_reform[i,k] / B_base[i,k])
                 / Σ_{i∈S[g,k]} w_i  − 1 )
```

Precedent: the Mermin-row replication used a person-weighted mean of
benefit-independent factor ratios and named the difference from a
dollar-weighted aggregate as a delta
(`anchor_provenance.named_population_deltas`).

**Basis.** The primary is the `proposed-1` proposal
(`proposals_not_adopted.aggregation`). The Urban text this builder read
describes only the effect on benefits received in 2030 relative to
scheduled benefits, which fits either formula.

**Fail closed.** A cell with no members or a zero baseline total has no
statistic. The run reports it as undefined and never imputes it. The
draw summary of a cell requires all K draws to be defined: if any
`Δ[g,k]` is undefined, the cell's mean and standard deviation are
reported as undefined together with the number of defined draws. This
follows the draw aggregates of `estimates/first_report.py`, which raise
on a non-finite draw value rather than skip it.

## 8. Membership

`S[g,k]` is the set of persons who are alive in the 2030 state of draw
*k*, have a positive baseline 2030 benefit and fall in age group *g*
(§9). The reform uses the same set.

- Under fixed paths (§13) the reform benefit is positive exactly when the
  baseline benefit is, because every factor `1 + c_t − 0.01` is positive
  (§4). Baseline-recipient, reform-recipient and common-recipient
  definitions therefore coincide.
- Persons with zero benefits and non-beneficiaries are excluded.
- Weights are person weights (§14). No family-level aggregation.
- **Decedents:** a person counts as alive in 2030 when present in the
  2030 state, that is, after surviving every mortality step through the
  step that produces 2030. Deaths during 2030 are not pro-rated (named
  delta).
- No alternative row.

## 9. Age

- Age in 2030 is `2030 − birth year`. Groups: 50–61, 62–64, 65–69, 70–79
  and 80+.
- The cohort contains only people born in 1980 or earlier (§14), so
  everyone in it is at least 50 in 2030.
- Birth year follows the first-estimates §3.1 laws, as plan item A3
  specifies.
- Reporting age is separate from statutory age attainment. The
  eligibility clock uses birth year + 62; the rule that a person attains
  an age the day before the birthday is outside this draft's excerpts and
  is not modeled at annual resolution.
- No alternative row.

**Basis.** The model is annual. DYNASIM3 also works with integer
birth-year ages: it computes year of birth as 1992 minus age (primer
p. 2; overview p. 2).

## 10. Benefit period

**Primary (R0): payments in calendar 2030, annual model.**

- `B[i]` is 12 times the monthly benefit payable for the months December
  2029 through November 2030.
- Each of those payments carries the increases with determination years
  up to 2029, so `last` = 2029.
- This matches `estimates/ledgers.py` `_monthly_benefit_path`, which
  uses the determination-year-(t − 1) increase for payment year t.
- Everyone entitled in the 2030 annual state receives a full-year amount:
  no pro-ration for first entitlement or death within 2030, and no
  retroactive payments (named delta).

**Alternative (R4): the December 2030 monthly amount.**

- `B[i]` is 12 times the monthly benefit for December 2030, which
  includes the increase for determination year 2030 (415(i)(2)(B)). So
  `last` = 2030, and every count rises by one (22 under R0 for a clock
  started in 2009 or earlier).
- The factor of 12 keeps every row on the annual scale of the
  opening-stock amounts (§11, rule 4). Without it, the ratio of weighted
  means would weight opening-stock persons twelve times as heavily as
  oracle-computed persons in the same cell.
- Membership stays as in §8. People who die in 2030 before December stay
  in, because the annual model does not resolve months.

The calendar-year entitlement basis that `proposed-1` also lists (months
January through December 2030) lies between R0 and R4 and is not
registered.

## 11. Benefit components, amount rules and rounding

**Primary components (R0):**

- retired workers, including disabled workers converted at full
  retirement age;
- disabled workers;
- spouses aged 62 or older;
- aged widow(er)s, entitled at 60 or older (primer p. 14, footnote 12);
- disabled widow(er)s under 60, with entitlement ages as 402(e)/(f)
  define them (outside this draft's excerpts).

**Alternative (R5):** retired and disabled workers only. A component
row restricts the benefit, not only the person: under R5, `B[i]` is the
person's own retired-worker or disabled-worker benefit, excluding any
spouse's excess or widow(er)'s amount paid on another worker's record,
and `S[g,k]` (§8) requires a positive baseline worker benefit. Under R0,
`B[i]` is the person's total from all five components, combined by the
dual-entitlement rule below. An opening-stock person's observed amount
(rule 4) cannot be split by component, so under R5 the whole observed
amount is kept or dropped according to A3's frozen classification of
that person's benefit type (§6, §12): kept for a retired-worker or
disabled-worker classification, dropped otherwise. The unsplit
dual-entitlement amount of a kept person is a named delta (§12).

**Basis.** Disability inclusion is part of the target. The primer lists
retirement, disability, spouse and survivor benefits among the benefits
DYNASIM3 calculates (p. 16), and the 2015 overview adds former spouses
(Table I.6, p. 14). The 2004 version omitted children's benefits and the
family maximum (primer p. 16, footnote 15); that cannot be assumed for
run 614.

**Amount rules:**

1. Each PIA follows its own increase path in each scenario and is floored
   to the next lower multiple of $0.10 after each increase
   (415(i)(2)(A)(ii), line 55).
2. The claim-age factor applies to the increased PIA and is floored to
   the dime in each payment year, as `_monthly_benefit_path` does now.
3. **Dual entitlement.** In each scenario separately, compute each PIA on
   its own clock and combine them with the oracle's rules:
   `ss/benefits.py` `spousal_benefit` returns the excess spouse's benefit
   paid on top of the own benefit, and `widow_benefit` returns the larger
   of the own benefit and the widow(er)'s benefit. The 402(k) text itself
   is outside this draft's excerpts; the oracle docstrings cite it.
4. **Opening stock** (persons with observed Social Security income in
   the opening year `s`: 2010 under R0, 2008 under R6; §14): the monthly
   PIA is not observed, so
   `B_base = observed annual amount for year s × Π_{t=s..last} (1 + c_t)`
   and `B_reform = B_base × Π_{t∈T_i} (1 + c_t − 0.01) / (1 + c_t)`,
   where `T_i` is the person's set of reduced determination years. The
   amount received in year `s` already carries the increase for
   determination year `s − 1`, so the product starts at `s`. The result
   is on the annual scale that §10 uses for every row. No dime flooring
   applies. In the worked cases of §19 the flooring changes the
   percentage by less than 0.02 points. The rule fixes the person's
   benefit basis at the opening year: events the projection simulates
   later (widowhood, a spouse's entitlement, conversion at full
   retirement age) change neither the level path nor `T_i`, which comes
   from the opening-stock clocks of §6. The projection still decides
   whether the person is alive in 2030 (§8). Named delta (§12).
5. **Gross benefits:** amounts are before Medicare premium deductions,
   income tax, earnings-test withholding, WEP/GPO and the disability
   offset that `proposed-1` lists, all omitted (§12). Whole-dollar
   payment rounding is omitted.

## 12. Named omitted deltas

Each item is a named difference between Track A and DYNASIM3 run 614. The
third column says where the item enters Track A's statistic: through the
individual reform ratio, or only through membership and weights.

| Item | What the DYNASIM3 documentation says | Where it enters Track A |
|---|---|---|
| Family maximum | Omitted in the 2004 version (primer p. 16, fn. 15); unknown for run 614 | Weights. 415(i)(2)(A)(ii)(III) raises family totals by the same increase as the PIA; how capped benefits scale is set by 403, outside this draft's excerpts |
| Children's benefits, including adult disabled children | Omitted in the 2004 version (same footnote) | Membership of the 50–61 cell |
| Child-in-care spouse and widow(er) benefits | Not documented in the sources read | Membership of under-62 auxiliaries |
| Divorced spouse and divorced survivor benefits | Included: divorced spouses qualify after a marriage of at least 10 years (primer p. 16); former spouses listed (overview p. 14) | Membership and weights of the auxiliary components; their clock would be the ex-spouse worker's |
| Retirement earnings test | Included, with an annual approximation (primer pp. 16–17, fn. 16; overview p. 14) | Membership and weights below full retirement age |
| WEP and GPO | Not documented in the sources read | Weights; any effect on individual ratios is outside this draft's sources |
| Parents' benefits; special minimum PIA; frozen minimum | Not documented in the sources read | Membership and weights |
| Medicare premiums and income taxation | Not documented for this run; the Urban outcome refers to benefits received | Track A uses gross benefits |
| Whole-dollar payment rounding | Not documented | Under $1 a month |
| Immigration after 2010 | Included: reweighting (primer p. 8) or donor immigrants aligned to Trustees targets (overview p. 2; Table I.1, p. 9) | Membership and weights. The closed cohort excludes post-2010 arrivals, and PSID under-covers immigrants who arrived after 1997 (plan §3) |
| Claiming response to the reform | The OASI take-up hazard uses the benefit amount and Social Security policy parameters as predictors (primer Table 3, p. 6; overview Table I.6, p. 14) | Track A holds claiming fixed (§13). Membership at 62–69 and, under R2, the counts |
| Population origin | 1990–93 SIPP panels, dated as if interviewed in December 1992, then projected (primer p. 2; overview p. 2; Figure 1, p. 7) | Track A observes its 2010 population. Weights and membership |
| Opening-stock level splice | — | Opening-stock levels embed realized 2008–2009 increases: about +0.5 percent against a TR2008-path level on the same clock for clocks started by 2008, and about −2.4 percent for clocks started in 2009 (§4). The observed 2010 amount also understates a full-year level for anyone who began receiving during 2010 or had benefits withheld, and would overstate it if the reported amount includes retroactive payments (PSID's income concept was not checked for this draft). Weights only |
| Opening-stock benefit basis fixed at the opening year | — | Later widowhood, spouse's entitlement or conversion does not change an opening-stock person's level path or reduced-increase set (§11, rule 4). Weights, and the individual ratio only where a later benefit would rest on a PIA whose clock is after `first` |
| Benefit type unobserved in PSID 2010 | — | A3's classification rule for opening-stock recipients: under 62, DI versus survivor; 62 or older, worker versus spouse or widow(er). Membership by component, the clock of DI versus survivor records, and under R5 whether a person's unsplit observed amount is kept (§11) |
| Population coverage | Sample adjusted to align closely with Social Security Area Population targets (overview p. 2) | Track A covers the population that ER34155 represents; this draft did not characterize its treatment of institutionalized persons or of beneficiaries living abroad. Membership and weights |
| Disability offset | Not documented in the sources read | Listed among the unresolved offsets of `proposed-1`; Track A uses amounts before it. Weights |
| Partial-year entitlement and death in 2030 | Unknown | Weights (§8, §10) |
| DI onset timing | DI take-up is a discrete-time hazard that uses disability status in the prior period (primer Table 3, p. 6) | Counts for disabled workers when A4 uses award years (§6) |
| Survivor-reduction default | — | The oracle's 84-month default is exact only for cohorts born 1962 or later (plan §2, citing `ss/params.py`). The reduction is common to both scenarios, so it enters through dual-entitlement mixes and weights |
| Parameter substitutes | Trustees-aligned mortality and DI incidence (overview p. 2) | Per §15 |
| DI benefit level | Computed by the DYNASIM3 calculator | Weights; subject to decision 2(b) |

## 13. Behavior

**Primary: fixed paths (mechanical incidence).** Both scenarios share the
same K = 20 projected paths for mortality, DI onset and termination,
claiming, marriage and widowhood, and earnings. The reform changes only
benefit amounts, computed after the projection. No alternative row.

**Basis.** The primer states that in DYNASIM3's design, changes in
Social Security or pension provisions do not feed back into demographic
or economic outcomes already simulated (p. 3, fn. 5). The 2015 overview
computes Social Security benefits in a postprocessor after the annual
core loop (Figure 1, p. 7). But DYNASIM3's OASI take-up hazard depends on
the
benefit amount and policy parameters (§12), so run 614's claiming may
have responded to the reform. Track A does not model that response; it
is a named delta.

## 14. Population and vintage

**Primary (R0): PSID 2011 wave.**

- Universe: individuals in the 2011 wave (income year 2010) with a
  positive ER34155 ("CORE/IMM INDIVIDUAL CROSS-SECTION WT 11") who were
  born in 1980 or earlier.
- Projection: a closed cohort from the 2010 state to 2030 in 20 annual
  periods.
- Weights: ER34155, held fixed throughout. No reweighting or alignment.
- No births are needed: everyone aged 50 or older in 2030 was born in
  1980 or earlier.
- Opening Social Security levels come from the 2011 family file's 2010
  amounts: head (ER52337), wife (ER52339), and one amount for all other
  family-unit members together (ER52341, "OFUM SOCIAL SECURITY
  INCOME-2010"). A3 freezes how the OFUM amount is assigned to persons.

**Alternative (R6): PSID 2009 wave.**

- Universe: the 2009 wave (income year 2008), ER34046 ("CORE/IMM
  INDIVIDUAL CROSS-SECTION WT 09"), born in 1980 or earlier.
- Projection: 2008 → 2030 in 22 periods. Opening amounts are 2008
  amounts; A3 verifies their labels.
- The 2009 wave matches DYNASIM's 2008 information date (plan §3). Its
  2008 levels embed realized increases through determination year 2007
  only. TR2008 projects none of them: V.C1 gives 1975–2006 as historical
  data and 2007 (2.3) as an actual amount (fn. 7). R6 therefore has no
  level splice.
- Split unit for the floor (§16): the 2009 family unit, not the 2011
  one, because a person in this universe who died or left the sample
  before the 2011 interview has no 2011 family unit.

**Coverage.** Each row covers the population that its cross-section
weight represents. This draft did not characterize how that population
treats institutionalized persons or beneficiaries living abroad; DYNASIM3
aligns its sample to Social Security Area Population targets (overview
p. 2). Named delta (§12).

**DYNASIM3 vintage.** DYNASIM3's input file comes from the 1990–93 SIPP
panels (primer p. 2; overview pp. 1–2), and its core model loops annually
from 1992 (overview Figure 1, p. 7). The overview says DYNASIM4 would
start projecting from 2006 (p. 1, fn. 1). This draft infers, but cannot
confirm for run 614, that an April 2009 DYNASIM3 run projected from the
1992 file.

The longitudinal weight ER34154 is not registered (§23).

## 15. Parameters

Every substitute below is named, with its hash, in the registration
package. No substitute may be a comparator value or be chosen after any
real-data statistic exists.

| Parameter | Role in the statistic | TR2008 availability | Freeze |
|---|---|---|---|
| Benefit-increase rates, 2008–2030 | Individual ratios (counts and factors) | V.C1 for 2008–2017 (p. 102); later years reconstructed | §4 table |
| AWI | Weights (new entrants' PIAs) | V.C1 for 2007–2017 (p. 102); VI.F6 for 2020, 2025 and 2030 (p. 184) | Geometric interpolation between published points for 2018–2029; a reconstruction for A2 to confirm |
| Bend points; contribution and benefit base | Weights | V.C2 through 2017 (p. 105); V.C1 through 2017 | Later years by statutory AWI indexing, outside this draft's excerpts; A2 |
| Mortality by age and sex, including DI mortality, 2010–2030 | Membership and weights | Improvement assumptions described (p. 75) and life expectancy tabulated (V.A3–V.A4, pp. 85–86); no death rates by age | Substitute named by A2/A4 |
| DI incidence and termination by age and sex | Membership, and counts for DI and survivor records | Aggregate only: projected disabled-worker beneficiaries and gross and age-sex-adjusted prevalence rates (V.C5, pp. 124–125), and assumptions with sensitivity tests (VI.D7–VI.D8, pp. 163–165); no rates by age | A2/A4 substitute, fit on data through 2008 (plan A4) |
| Claim-age distribution | Membership under both clocks; counts under R2 | Not in TR2008 | Repo `claiming.py` Supplement table, restricted to rows through 2008 (plan A5) |
| Earnings, 2011–2030 | Weights | Not applicable | Plan A5 |
| DI benefit level | Weights | Not applicable | Decision 2(b), §22 |

## 16. Uncertainty

- **Draws:** K = 20, k = 0…19. Root entropy is `5200 + k`
  (`engine/rng.py`, `DRAW_SEED_BASE = 5200`). The run reports the mean and
  sample standard deviation across draws for every cell and every
  registered row.
- **Half-split floor:**
  - seeds 0–4, fraction 0.5, using `harness/panel.split_panel_by_person`
    on the family-unit identifier of the row's opening wave, so each
    family unit's persons fall on one side: the 2011 interview number
    (ER34101) under R0 and every row that keeps its population, the 2009
    interview number (ER34001) under R6 (§14);
  - in each half, compute the 20-draw mean `Δ[g]`;
  - the floor is the mean and standard deviation over seeds of
    `|Δ[g]^A − Δ[g]^B|`, the standard deviation with divisor (seeds − 1);
  - a seed in which either half's cell is undefined (§7) is excluded,
    and the number of seeds used is reported with the floor. With fewer
    than two usable seeds the floor is undefined, never zero.

  This is the `conventions.floor` rule of
  `replication_mermin_rows_v1.json`: its script drops seeds in which
  either half is undefined (`_abs_gaps` in
  `scripts/replication_mermin_rows.py`) and summarizes with `ddof=1`
  (`_summary` in `scripts/reform_delta_diagnostic.py`). Two things
  differ: the split unit (§23), and the last clause above, because that
  `_summary` returns a zero summary when no seed is usable and a zero
  standard deviation when one is, which this specification forbids.
- **Diagnostics with each cell:** the unweighted beneficiary count (mean
  over draws) and the weighted component shares.
- **Comparator interval:** A8's digitization interval, or Urban's own
  precision if Urban's series arrives, appears only in the comparison
  memo, after the sealed comparator is opened. It never enters the run
  artifact.

## 17. Acceptance rule

**Primary: none.** The comparison is reported, not gated; it runs once
and is published regardless of outcome (plan §7; `paper/paper.qmd`, "The
replication anchors"). For each cell and registered row, the memo reports
our mean and standard deviation, the floor, the comparator with its
interval, and the gap. It declares no pass or fail. There is no tuning
and no re-run; any change becomes a new registered version.

**Alternative:** Max sets a numerical rule before registration
(decision 3, §22). No rule may be set afterwards.

## 18. Registered rows

Each alternative row differs from R0 in exactly one field. No combined
rows are registered (§23, question 1). The run computes every row in the
same one-shot execution and publishes them together. R0 is the headline
row, designated now; no row may be promoted after results exist.

| Row | Field changed | Value | New projection needed? |
|---|---|---|---|
| **R0** | — (primary) | §§3–16 | Yes (the base run) |
| R1 | First reduced increase | Takes effect December 2010 | No; tabulation only |
| R2 | Exposure clock | Entitlement clock | No |
| R3 | Statistic | Weighted mean of individual ratios | No |
| R4 | Benefit period | December 2030 monthly amount, times 12 | No |
| R5 | Components | Retired and disabled workers only | No |
| R6 | Population and vintage | PSID 2009 wave, ER34046, 2008 → 2030 | Yes |

## 19. Invented worked cases

These cases are **invented** for A6 and A7 unit tests. They use no PSID
data, no model output and no comparator value. They are statute
arithmetic by this draft (Python `decimal`, lower-dime floor after each
increase, TR2008 intermediate rates from §4) applied to an invented PIA
of $1,000.00 at the start of the clock year.

| Clock start | Row | Reduced increases | Baseline PIA in 2030 payments | Reform PIA | Change, dime-floored (%) | Change, unrounded (%) |
|---|---|---|---|---|---|---|
| 2009 | R0 | 21 | $1,779.50 | $1,449.00 | −18.5726 | −18.5604 |
| 2009 | R1 | 20 | $1,779.50 | $1,463.20 | −17.7747 | −17.7581 |
| 2009 | R4 (with R0's first increase) | 22 | $1,829.30 | $1,475.00 | −19.3681 | −19.3526 |
| 2010 | R0 or R1 | 20 | $1,735.80 | $1,427.50 | −17.7613 | −17.7581 |
| 2020 | R0 or R1 | 10 | $1,317.50 | $1,194.80 | −9.3131 | −9.3127 |
| 2025 | R0 or R1 | 5 | $1,147.80 | $1,093.10 | −4.7656 | −4.7701 |
| 2029 | R0 or R1 | 1 | $1,028.00 | $1,018.00 | −0.9728 | −0.9728 |
| 2030 | R0 or R1 | 0 | $1,000.00 | $1,000.00 | 0 | 0 |

Invented clock cases (unrounded change in 2030 payments, R0 first
increase):

| Invented person | Clock under R0 | Count, R0 | Change, R0 (%) | Entitlement year | Count, R2 | Change, R2 (%) |
|---|---|---|---|---|---|---|
| Retired worker born 1950, claims 2016 | 2012 | 18 | −16.1344 | 2016 | 14 | −12.7902 |
| Disabled worker, onset 2015 at 52, converted at 67 in 2030 | 2015 | 15 | −13.6385 | 2015 or 2016 (set by A4) | 15 or 14 | −13.6385 or −12.7902 |
| Widow born 1948 of a worker born 1940 who died in 2012; widow entitled 2012 | 2002 (worker) | 21 | −18.5604 | 2012 | 18 | −16.1344 |

## 20. Resolution map

Each null field of `proposed-1` `required_unresolved`, and where this
draft resolves it:

| `proposed-1` field | Resolution | Section |
|---|---|---|
| `law_cutoff_and_historical_versions` | Law as TR2008 assumes it (no significant legislation after April 23, 2007). The excerpt file notes no amendment to 415(i) after Pub. L. 103-296 (1994) | §1, §2 |
| `population_vintage_coverage_and_weights` | R0: PSID 2011 wave, born ≤ 1980, ER34155, closed cohort. R6: 2009 wave. Coverage is what the cross-section weight represents; the difference from DYNASIM3's Social Security Area Population alignment is a named delta | §14, §12 |
| `trustees_alternative_and_parameter_splice` | TR2008 intermediate; no realized rate in any ratio; observed levels as weights only | §4 |
| `complete_dated_parameter_sequences` | Determination years 2008–2030, with effective and payment months | §4, §21 |
| `first_effective_and_payment_months` | R0: December 2009, paid January 2010. R1: December 2010, paid January 2011 | §5 |
| `exposure_and_existing_beneficiary_rules` | R0: eligibility clock; R2: entitlement clock; reduced increases apply prospectively to everyone | §6 |
| `floor_or_verified_nonbinding_condition` | Verified nonbinding (lowest reduced rate 1.5); inactive zero floor; fail-closed assertion | §4 |
| `aggregation_formula` | R0: ratio of weighted means; R3: mean of individual ratios | §7 |
| `beneficiary_membership_and_zero_treatment` | Alive in 2030 with a positive baseline benefit; common to both scenarios; zeros excluded; person weights | §8 |
| `age_reference_and_decedent_selection` | Age = 2030 − birth year; present in the 2030 state | §8, §9 |
| `benefit_period_and_partial_year_rules` | R0: 2030 payments, full year; R4: December 2030 amount; both on an annual scale | §10 |
| `benefit_components_offsets_and_rounding` | Five components (R5: worker benefits only; opening stock by A3 classification); dime flooring; oracle dual entitlement; gross benefits before every offset `proposed-1` lists | §11, §12 |
| `interacting_indexation` | The reform changes only the 415(i) increase | §3 |
| `behavioral_configuration` | Fixed paths, K = 20 shared draws | §13 |
| `comparator_series_precision_and_provenance` | A8 sealed digitization with an interval, or Urban's series; validation only; opened after the run artifact is committed | §16, §17 |

**Where this draft adds to or departs from the plan's §4 table:**

1. It adds the splice rule: no realized rate in any ratio, and observed
   levels as weights only (§4).
2. It gives the entitlement-clock row exact semantics: baseline amounts
   are identical across R0 and R2, and auxiliaries use their own
   entitlement year under R2 (§6).
3. It defines the December 2030 row to include the determination-year-2030
   increase, 22 increases under R0 (§10).
4. It makes the inactive floor rule fail closed (§4).
5. It states that the scheduled-benefit baseline ignores the 2025 DI
   trust fund exhaustion in TR2008 (§1).
6. It keeps family units whole in the half-split floor (§16).
7. The rate-path basis is TR2008 itself, re-parsed by this builder, not
   the `proposed-1` quotation.
8. The age basis is the primer directly, not `cola-metadata-followup.md`,
   which this builder did not open.
9. It adds the 415(i)(1)(C) stabilizer check (§4).
10. It adds the opening-stock amount rule: the observed opening-year
    amount carried forward on the baseline path, with no dime flooring,
    on the annual scale shared by every row (§10, §11).
11. It makes undefined cells fail closed, in each draw, in the draw
    summary and in the floor (§7, §16).
12. It extends the plan's eight named omissions to the table of §12.
13. It defines each alternative row as a one-field change from a
    headline R0 designated before any result (§18), and gives the
    component row a benefit-level meaning (§11).
14. It fixes an opening-stock person's benefit basis at the opening year
    and states how R5 treats an opening-stock amount that cannot be
    split by component (§11).
15. It gives opening-stock spouses and widow(er)s aged 62 or older a
    clock rule with a bounded fallback (§6).
16. It takes the floor's split unit from the row's opening wave, so R6
    has a family unit for every person (§14, §16).

Items 10 (annual scale), 11, the component meaning in 13, and items 14
to 16 were added or tightened by referee pass 1 (§25).

## 21. Machine-readable parameter block

Downstream lanes (A6, A7, A9) read this block. Values marked
`awaiting_max` are defaults pending §22. The registration package hashes
this file.

```json
{
  "specification": "urban2010_cola_exercise1",
  "version": "a1-draft-2",
  "status": "draft_for_referee_not_ratified",
  "target": {
    "model": "DYNASIM3",
    "run": "614",
    "run_date": "2009-04",
    "trustees_vintage": 2008,
    "baseline": "scheduled_benefits_current_law_tr2008",
    "outcome_year": 2030,
    "age_groups": [[50, 61], [62, 64], [65, 69], [70, 79], [80, null]],
    "disability_included": true
  },
  "rate_path": {
    "trustees_alternative": "intermediate_II",
    "unit": "percent",
    "index": "determination_year",
    "effective_month": "december_of_determination_year",
    "first_payment_month": "january_of_following_year",
    "reform_delta_percentage_points": -1.0,
    "baseline": {
      "2008": 2.7, "2009": 2.5, "2010": 2.8, "2011": 2.8, "2012": 2.8,
      "2013": 2.8, "2014": 2.8, "2015": 2.8, "2016": 2.8, "2017": 2.8,
      "2018": 2.8, "2019": 2.8, "2020": 2.8, "2021": 2.8, "2022": 2.8,
      "2023": 2.8, "2024": 2.8, "2025": 2.8, "2026": 2.8, "2027": 2.8,
      "2028": 2.8, "2029": 2.8, "2030": 2.8
    },
    "published_through": 2017,
    "reconstructed_from": 2018,
    "realized_series_substitution": "forbidden",
    "floor": {
      "rule": "no_increase_if_reduced_rate_not_positive",
      "binding_on_path": false,
      "min_reduced_rate_r0": 1.5,
      "min_reduced_rate_r1": 1.8,
      "assert_positive": "every_reduced_determination_year_of_the_row_through_2030"
    }
  },
  "rows": {
    "R0": {
      "first_reduced_determination_year": 2009,
      "exposure_clock": "eligibility",
      "statistic": "ratio_of_weighted_means",
      "benefit_period": "calendar_2030_payments",
      "benefit_scale": "annual_12_times_monthly",
      "last_determination_year": 2029,
      "components": [
        "retired_worker", "disabled_worker", "spouse",
        "aged_widow", "disabled_widow"
      ],
      "component_scope": "benefit_amounts_of_listed_components_only",
      "population": {
        "wave": 2011, "weight": "ER34155", "born_max": 1980,
        "start_year": 2010, "periods": 20,
        "family_unit_id": "ER34101"
      },
      "behavior": "fixed_paths_shared_draws"
    },
    "R1": {"first_reduced_determination_year": 2010},
    "R2": {"exposure_clock": "entitlement"},
    "R3": {"statistic": "weighted_mean_of_individual_ratios"},
    "R4": {
      "benefit_period": "december_2030_month",
      "last_determination_year": 2030
    },
    "R5": {"components": ["retired_worker", "disabled_worker"]},
    "R6": {
      "population": {
        "wave": 2009, "weight": "ER34046", "born_max": 1980,
        "start_year": 2008, "periods": 22,
        "family_unit_id": "ER34001"
      }
    }
  },
  "amounts": {
    "pia_dime_floor_after_each_increase": true,
    "claim_age_factor_dime_floor_each_payment_year": true,
    "opening_stock": "observed_opening_year_annual_amount_x_baseline_increases_from_opening_year",
    "opening_stock_dime_floor": false,
    "opening_stock_basis": "fixed_at_opening_year",
    "opening_stock_under_worker_only_components": "whole_observed_amount_kept_if_a3_classifies_a_worker_benefit",
    "gross_of_premiums_taxes_and_withholding": true,
    "gross_of_wep_gpo_and_disability_offset": true
  },
  "uncertainty": {
    "draws": 20,
    "draw_seed_base": 5200,
    "draw_summary": ["mean", "sample_sd"],
    "draw_summary_requires_all_draws_defined": true,
    "floor": {
      "seeds": [0, 1, 2, 3, 4],
      "fraction": 0.5,
      "split_unit": "population_family_unit_id_of_the_row",
      "summary": ["mean", "sample_sd"],
      "undefined_half_seed": "excluded_and_counted",
      "min_usable_seeds": 2
    },
    "comparator_interval": "comparison_memo_only"
  },
  "decisions_awaiting_max": {
    "claim_class": {
      "default": "track_a_reported_not_gated_psid_oracle",
      "alternatives": ["hold_for_track_b_m6_forward", "hold_for_track_c_axiom"],
      "awaiting_max": true
    },
    "oracle_cola_horizon_extension_to_2030": {
      "default": true,
      "alternatives": [false],
      "awaiting_max": true
    },
    "di_benefit_level": {
      "default": "disclosed_oracle_approximation",
      "alternatives": ["exclude_until_axiom_di_rule"],
      "awaiting_max": true
    },
    "acceptance_rule": {
      "default": null,
      "alternatives": ["numerical_rule_set_by_max_before_registration"],
      "awaiting_max": true
    }
  },
  "labels": [
    "PSID-seeded closed cohort",
    "Python oracle (not Axiom)",
    "fixed-path mechanical incidence"
  ]
}
```

## 22. Decisions awaiting Max

These are plan §6 items 1–3, restated in substance. This draft builds on
the proposed default of each and records it in §21 as a parameter. None
is decided.

1. **Claim class for the first score** (`claim_class`). Is Track A
   acceptable as exercise 1's first scored comparison: a
   reported-not-gated, PSID-seeded cohort whose benefits the Python
   oracle computes, labeled "not Axiom"? The alternative is to hold the
   first score for Track B (M6 FORWARD, months away) or Track C (Axiom,
   blocked).
   - **Proposed default:** accept Track A.
   - **Consequence:** the `proposed-1` implementation requirement
     `policy_executor: Axiom` does not hold for Track A; Track C would
     re-run this same specification with Axiom as the benefit executor.
     Tracks B and C reuse this specification under their own
     registrations.
2. **Scope of the transitional oracle.** `ss/__init__.py` says "Do not
   extend this module's rule coverage; extend the Axiom encodings." Two
   rulings are needed:
   - **(a)** (`oracle_cola_horizon_extension_to_2030`) May A6 extend the
     `estimates/ledgers.py` COLA path horizon (now capped at
     `REPORT_YEARS[-1] = 2022`) to 2030 with a scenario COLA series?
     **Proposed default:** yes, as a parameter override that adds no
     statutory coverage.
   - **(b)** (`di_benefit_level`) May the DI benefit level be a disclosed
     approximation that reuses existing oracle functions, since it serves
     only as a weight? The alternative excludes DI levels until an Axiom
     DI rule exists. **Proposed default:** the disclosed approximation.
     **Consequence of the alternative:** new DI awards after the opening
     year (2011–2030 under R0, 2009–2030 under R6) would have no level,
     so they could not enter any ratio-of-means row (R0, R1, R2, R4, R5,
     R6). Disabled workers already on the rolls in the opening year keep
     their observed levels (§11, rule 4), and R3, whose
     individual ratios need no level, could still include new awards.
     People aged 50–61 in 2030 were 30–41 in 2010, so most of that
     cell's disabled workers would be post-2010 awards (an inference
     from ages, not measured). The plan (§1) expects that cell to be
     almost all disabled workers, so it would lose most of its members
     on the headline row, and the disability-inclusive target could not
     be scored there.
3. **Acceptance rule** (`acceptance_rule`). Confirm "no numerical
   acceptance threshold; report gaps", or set a rule now, before any
   output exists. **Proposed default:** no threshold (§17).

Process steps that follow, not decisions on this draft's content:
ratifying A1 by merging (plan §6, item 4), and posting or authorizing the
issue #42 registration before the one-shot run (item 5).

## 23. Questions for the referee

1. **Combined rows.** Should the 2 × 2 cross of first application (R0/R1)
   and exposure clock (R0/R2) be registered as rows, since the plan
   (§1, §9) expects these two conventions to dominate the 80+ and 62–69
   cells? Both reuse the base projection.
2. **Floor split unit.** Is keeping opening-wave family units whole in
   the half-split an acceptable departure from the person-level split of
   the Mermin-row precedent? Spouse links drive widowhood in Track A.
3. **Opening-stock classification.** The plan's risk table (§9) calls for
   a sensitivity row on the classification of under-62 recipients in
   2010. Should A1 reserve a row (R7) now, with A3 defining its content
   before registration? The classification now also decides the clock
   fallback for recipients aged 62 or older (§6) and which opening-stock
   amounts R5 keeps (§11).
4. **Weight.** Should the longitudinal weight ER34154 be registered as a
   row alongside the cross-section weight ER34155?
5. **Draw pooling.** Is the per-draw statistic, summarized by the mean
   across draws, preferable to one ratio of totals pooled across draws?
6. **Age groups.** Can A8, which is allowed to open the sealed figure,
   confirm the five group labels without releasing any value?
7. **DI clock.** Should A4 be required to simulate onset years, rather
   than award years, so that the eligibility clock is exact for disabled
   workers?
8. **Auxiliaries under R2.** Is the auxiliary's own entitlement year the
   right clock for auxiliaries under the entitlement row, or should R2
   use the worker's entitlement year?
9. **Component row scope.** §11 now reads R5 as restricting benefit
   amounts (a dually entitled worker's spouse's excess or widow(er)'s
   amount is dropped), not only membership. Is that the intended row, or
   should R5 keep each worker's total benefit?
10. **Page-3 text (for Max).** The drafting lane read lines 125–126 and
    160 of the Urban text extraction, which lie on page 3, the page that
    carries Figure 2 (§2, disclosure). The plan cites line 160 as a
    source-line locator, and `proposed-1` records the same run identity.
    Is that contact acceptable under the builder rule, or should §1 rest
    on the `proposed-1` target block alone, with the contact recorded as
    a named deviation in the registration package?
11. **Opening-stock basis.** §11, rule 4 fixes an opening-stock person's
    benefit basis at the opening year. Should A3/A6 instead let later
    simulated events (widowhood, a spouse's entitlement) re-base the
    person's benefit through the oracle, at the cost of needing a PIA
    that PSID does not observe?

## 24. What this draft did not verify

- The age groups and disability inclusion. They come from `proposed-1`;
  checking them would need Figure 2.
- SSA's TR2008 "A1" provision start date, which is outside this source
  set.
- Whether run 614 used realized COLAs, the family maximum, the earnings
  test, divorced benefits or a claiming response. The DYNASIM3
  documentation read here is not run-specific; the 2015 overview
  postdates the run.
- TR2008 OASDI fund ratios for years that Table IV.B3 does not list.
- The statutory mechanics outside the 415 excerpts: 402(e)/(f), 402(k),
  403, 415(g), 223 and age attainment.
- Any PSID sample size, value or cell count. No PSID values were read,
  and no statistic was computed on real data.
- The plan's statement that PSID has no benefit-type item for 2010. This
  draft did not re-check it. Referee pass 1 searched the labels (not
  values) of `FAM2011ER.sas`: it found G31 "ANY FU MEMB GET SOCSEC"
  (ER48430), the head, wife and OFUM 2010 amounts with their accuracy
  flags (ER52337–ER52342) and separate SSI items, and no retired,
  disabled or survivor type item. Other waves and the individual file
  were not searched.
- The A2 and A4 substitutes, which are not yet chosen.
- The quotations from page-3 lines 125–126 and 160 of the Urban text
  extraction (§2, disclosure). Referee pass 1 did not read those lines.
- Whether PSID's reported Social Security amounts include retroactive
  payments, and how the cross-section weights treat institutionalized
  persons and beneficiaries living abroad (§12, §14).

## 25. Referee pass 1 (2026-09-22)

Referee pass 1 ran in two sittings. A first review lane edited the draft
and was interrupted before committing; a second, independent review lane
inspected those uncommitted edits, kept them after checking each one,
finished the review and committed the result. This section records what
the second lane verified itself. Neither lane opened the comparator
directory, the seal file, Figure 2, the page-3 image or the Urban PDF,
and neither computed anything on real data. The second lane did not read
any line from 121 to 207 of the Urban text extraction (page 3); it
located the page boundaries from the form-feed positions alone, printing
no line content.

**Verified against the sources:**

- Source hashes: every SHA-256 prefix in §2 and in the header matches
  the local file.
- TR2008, re-parsed with `pdftotext -layout`: the V.C1 intermediate,
  low cost and high cost benefit increases (p. 102) and footnotes 1 and 7
  (p. 103); the ultimate CPI rates and the intermediate CPI path (p. 89);
  Table V.B1 (p. 92); Table IV.B3 and its note (p. 55); pp. 31–32; the
  CPI-W statement (p. 182) and the VI.F6 CPI-W and AWI values (p. 184),
  including the 2.800, 2.800 and 2.801 percent growth rates; the
  content cited from pp. 75, 85–86, 105, 124–125 and 163–165. The low cost
  and high cost minima of §4 (0.8 and 1.8 under R0) follow from V.C1 and
  the ultimate rates.
- The 415 excerpt line references of §§3–6 and §11.
- Urban text lines 44–90 (pages 1–2) and the references on page 6.
- Primer pp. 2, 3 (fn. 5), 6–8, 14 (fn. 12), 16 (fn. 15) and 17
  (fn. 16); overview pp. 1 (fn. 1), 2, 7 (Figure 1), 9 (Table I.1) and
  14 (Table I.6); Mermin p. 2 (fns. 6–7), p. 7 and its run 432 source
  lines.
- Repo conventions: `_monthly_benefit_path` (payment year `t` uses the
  determination-year `t − 1` increase; lower-dime floors),
  `REPORT_YEARS`, `DRAW_SEED_BASE = 5200`, `_numeric_aggregate` in
  `estimates/first_report.py` (divisor K − 1; raises on a non-finite
  value), `split_panel_by_person`, `_abs_gaps`, `_summary`, the
  `ss/__init__.py` quotation, the `spousal_benefit` and `widow_benefit`
  docstrings, the Mermin-row artifact fields, the realized COLA values
  (and their equality with V.C1 for 1975–2007) and `historical_timing`,
  and the paper's anchor-replication wording.
- PSID labels of ER34001, ER34046, ER34101, ER34154, ER34155, ER48430
  and ER52337–ER52342, and the label search reported in §24.
- The §19 arithmetic, recomputed independently.
- The plan's §4 A1 row and proposed entries, and the 15
  `required_unresolved` fields of `proposed-1`.

**Corrections made by the first sitting and kept:**

1. **R4 scale (§10).** R4 measured `B` as a monthly amount while the
   opening-stock amounts of §11 are annual, which would have weighted
   opening-stock persons twelve times too heavily in R4's ratio of
   means. R4 is now 12 times the December 2030 amount, and the JSON
   block records `benefit_scale`.
2. **Opening-stock rule (§11, rule 4; §6).** Written for 2010 only; now
   stated for the opening year of R0 and R6.
3. **Level splice (§4, §12).** "New entrants' PIAs carry 2.7 and 2.5"
   held only for clocks started by 2008; the text now gives the
   difference by clock start, including −2.4 percent for 2009 clocks.
4. **Payment timing (§5).** The statute fixes the December effective
   month; the January first payment comes from the repo's realized
   series, not from 415(i)(2)(B).
5. **Undefined cells (§7, §16).** The draw summary and the floor had no
   rule for undefined cells or the floor's divisor; both now fail closed.
6. **Component row (§11).** R5's effect on dual entitlement was
   unstated; it is now explicit and raised as question 9 (§23).
7. **Decision 2(b) consequence (§22).** It said disabled workers could
   not enter the primary statistic; only awards after the opening year
   would lose their level, and R3 would not need one.
8. **Wording:** the §3 scope of reduced increases now includes, under
   415(i)(2)(A)(iii), the PIAs of eligible individuals not yet entitled
   (R0's clock); §4 quotes the Table IV.B3 note on theoretical
   post-exhaustion ratios; §6 places the Mermin p. 7 passage in its
   price-indexing context.

**Corrections made by the second sitting:**

9. **Builder boundary (header, §1, §2, §23 question 10).** The draft
   said it did not open page 3, but it cites lines 125–126 and 160 of
   the text extraction, which lie on page 3 with line 164 (form feeds at
   lines 121 and 208). The disclosure now names all three passages, the
   first sitting's "one disclosed contact" is withdrawn, and the question
   goes to Max.
10. **R6 split unit (§14, §16, §21).** The floor split on the 2011
    family unit, but R6's 2009-wave universe includes people who died or
    left the sample before 2011 and so have no 2011 family unit. The
    split now uses the row's opening-wave interview number (ER34101
    under R0, ER34001 under R6).
11. **R5 and the opening stock (§11, §21).** R5 kept only worker
    benefits, which an opening-stock amount cannot be split into; the
    whole observed amount now follows A3's classification.
12. **Opening-stock basis (§11, rule 4; §12; §23 question 11).** The
    rule implied, without saying, that later simulated events do not
    change an opening-stock benefit; it now says so and names the delta.
13. **Opening-stock auxiliaries aged 62 or older (§6).** Only retired
    workers and under-62 recipients had an opening-stock clock rule.
14. **Coverage and the disability offset (§11, §12, §14, §20).**
    `proposed-1` lists coverage and the disability offset among the
    fields to resolve; neither was addressed.
15. **Sources (§2).** The table omitted the plan, `proposed-1`, the paper
    and two scripts that the draft cites, although §2 says the draft
    cites only the sources listed; the Urban reference locator is now
    lines 406–417.
16. **Precision:** the Table IV.B3 years actually listed and the
    trust fund ratio's definition against 415(i)(1)(F) (§4); V.C5 among
    the TR2008 DI sources, and Table VI.D8's page (165, not 164) (§2,
    §15); the R6 splice sentence (§14); the 2(b) consequence under R6
    (§22); the pre-2008 increases in the splice rule (§4).

`tests/test_urban2010_cola_spec.py` holds the §21 block to the TR2008
V.C1 transcription, the §4 rate table, the declared floor minima, the
one-field row rule, the annual scale, the population horizons and split
units, the opening-stock amount fields, the plan's §6 defaults, the
fail-closed uncertainty fields and the §20 field list, and recomputes
every §19 worked case from the block's rate path.
