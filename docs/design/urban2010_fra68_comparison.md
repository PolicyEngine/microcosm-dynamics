# Urban 2010 FRA-68 comparison: specification draft for DynaSim scorecard exercise 3

- **Status:** draft, refereed (§25); **not ratified**. Max has not ruled
  on exercise 3 (decision record d188 and its supplement d196, both open,
  deadline 2026-09-30), and ratification by merge awaits him (d188 item
  (c)). Every choice that awaits him is a field of §21 whose value is the
  plan's recommended default, and §22 lists them, including three that
  d188 as filed does not name (d196 names them). This draft authorizes
  no real-data run: the one-shot entry point
  (`scripts/run_fra68_registered.py`) refuses a block whose status or
  version is not ratified, that lists a decision awaiting Max, or that
  records no ruling of his on a decision field (§21).
- **Specification:** `urban2010_fra68_exercise3`, version `e1-draft-6`,
  drafted 2026-09-24 and revised the same day after the independent
  referee pass and after the independent reviews of `e1-draft-4` and
  `e1-draft-5` (§25). §26 is the changelog.
- **Plan item:** E1 of the blind plan
  `EVID/critical-path-fra68-20260923.md` (SHA-256 `d5e7a32f…`), where
  `EVID` = `~/microcosm-launch-evidence/dynasim-parity-20260909`. The
  plan's §7 table "Exercise 3 treatment" is the starting point; §20
  lists where this draft adds to or departs from the plan.
- **Template:** exercise 1's ratified specification A1,
  `docs/design/urban2010_cola_comparison.md`, version `a1-ratified-1`
  (SHA-256 `f674e8c6…`). This draft follows A1 section by section.
  Where a section says "carried over", A1's text applies unchanged and
  is not repeated.
- **Claim class (pending, d188 item (a)):** proposed as A1's: a
  registered, one-shot, reported-not-gated comparison on the Track A
  pipeline.
- **Labels every output carries:** *PSID-seeded closed cohort*; *Python
  oracle (not Axiom)*; and *fixed-path mechanical incidence* on rows
  F0-F2 and F5-F8, replaced by *fixed paths; stylized claiming response
  (registered sensitivity)* on rows F3 and F4.
- **Builder boundary:** model-builder lanes wrote this draft. The files
  model builders may not open are listed in `EVID/RESTRICTED-FILES.md`
  (created 2026-09-24). The list is a living file that the orchestrating
  session updates; this summary is of the version the `e1-draft-5` lane
  read, whose last changelog entry is dated 2026-09-24 13:55 (the
  `e1-draft-6` lane read the version whose last entry is dated 14:35;
  against the 13:55 copy, `EVID/revisions/RESTRICTED-FILES-20260924-pre-clearance-followup.md`
  (SHA-256 `812bde2b…`), it changes only exercise-2 and exercise-4
  entries): every copy
  of the Urban report beyond PDF pages 1-2 (text lines 1-120; pages 3-4,
  which carry Figure 2, the page-4 prose describing the FRA results and
  Figures 4-5, are restricted), `EVID/urban-2010-page3.png`,
  `EVID/cola-source-review.*`, the comparator lanes and seals of
  exercises 1-4 (among them `EVID/exercise3-comparator-20260924/`, first
  created at 02:14 on 2026-09-24, after `e1-draft-3` was committed at
  01:10), the exercise-1 result, the results of the 2004 Boomers report
  and of the minimum-benefit reports (as the list defines them), the
  uncleared exercise-4 definitions extract and target-availability
  statement, and the exercise-2 definitions working files and pending
  validation checks.
  - The lane that wrote `e1-draft-1` to `e1-draft-3` did not open
    `EVID/cola-comparator-20260922/`, `EVID/cola-comparator-b-20260922/`,
    `EVID/exercise2-comparator-20260923/`, any `*comparator-seal*` or
    `*comparator-reconciliation*` file, `EVID/track-a-oneshot-20260923/`,
    the issue #42 result comments, `EVID/urban-2010-page3.png`, the Urban
    PDF, page 3 (lines 121-207) or pages 4-5 (lines 208-358) of the Urban
    text extraction, any results table of the 2004 Boomers report, or the
    exercise-1 artifact `runs/replication_urban2010_cola_v1.json`. It read
    lines 1-120 (pages 1-2) of the Urban text extraction.
  - The lane that wrote `e1-draft-4` read `EVID/RESTRICTED-FILES.md`
    before any other file and opened nothing it lists, nor the exercise-1
    artifact. Of the Urban text extraction it read lines 58-90 (Table 1)
    only.
  - The lane that wrote `e1-draft-5` read `EVID/RESTRICTED-FILES.md`
    (the version above) before any other file and opened nothing it
    lists, nor the exercise-1 artifact or the exercise-3 forecasts. It
    did not open the Urban report or its text extraction.
  - The lane that wrote `e1-draft-6` (the independent review of
    `e1-draft-5`, §25) read `EVID/RESTRICTED-FILES.md` (the 14:35
    version) before any other file and opened nothing it lists, nor the
    exercise-1 artifact or the exercise-3 forecasts. It did not open the
    Urban report or its text extraction.
  - No lane computed a statistic on real data. §2 lists what the drafts
    read.

## 1. Target

The target is the second benefit-cut option of Urban Institute (2010),
*Distributional Effects of Alternative Social Security Reforms: Details
Matter* (publication 412102, per A1 §1), the publication and figure family of
exercise 1:

- **Option (Table 1, `EVID/urban-2010-reform-details.txt:64-68`,
  verbatim):** "Current law: FRA is 66 for those age 62 today and will
  increase to 67 beginning with those turning age 62 in 2022." "Option:
  Gradually increase FRA beginning in 2010 until it reaches 68 for those
  turning 62 in 2022 and later." "Rationale: Longevity gains are
  increasing lifetime benefit payouts."
- **Outcome:** "For each benefit reduction option, we show the impact on
  average benefits in 2030 and 2050 by age and lifetime earnings"
  (`:25-27`). This exercise scores 2030 by age only.
- **Age groups:** exercise 1's (50-61, 62-64, 65-69, 70-79, 80+). A1
  took them from the `proposed-1` target block; this draft did not check
  them against the figure (§24).
- **Disability beneficiaries:** included, as in A1.
- **Model and run (provisional):** A1 §1 records DYNASIM3 run 614 (April
  2009, 2008 Trustees' assumptions) from the page-3 source line, for the
  COLA option. Whether that line covers the FRA bars is not verified
  (§24): this draft did not read page 3. The run identity and the TR2008
  vintage are inherited provisionally.
- **Not the solvency chart:** Figure 1's source is "Office of the Chief
  Actuary, Social Security Administration, based on 2009 trustees'
  assumptions, plus Urban Institute calculations" (`:114`), and its note
  says "Phase-in provisions differ modestly from the options simulated
  here, so their costs would differ" (`:115`). So Figure 1 rests on SSA
  Office of the Chief Actuary scoring plus Urban calculations, not on
  the DYNASIM run (an inference from the source line), and the
  SSA-scored provision behind it cannot pin down Urban's phase-in.

**Baseline.** Scheduled benefits under the law TR2008 assumes, as A1 §1.
The baseline FRA schedule is the statute's (§3), not Table 1's
current-law sentence, which omits the 2017-2021 phase-in of 416(l)(1)(D).
The DYNASIM3 primer says the benefit calculator "includes all historic
and projected Social Security program rules" (p. 16); this draft infers,
and did not verify for run 614, that its baseline used the statutory
phase-in.

**`proposed-1`.** A case-insensitive search of the `proposed-1`
specification (`EVID/parallel-oasdi-20260920/deliverables/
dynasim-specification.md`, SHA-256 `c220b213…`) for "FRA", "full
retirement" and "exercise 3" found "fraction" (lines 15 and 82) and
"\frac" (lines 34 and 36) for "FRA", nothing for "exercise 3", and one
"full retirement", on line 45: a general payment convention of the COLA
target ("disability converts to retirement at full retirement age"). It
carries no exercise-3 entries. (`e1-draft-2` reported the "FRA" matches
only; the independent review of 2026-09-24 found line 45.) §20 maps its
field list, which A1 §20 records, to this draft.

## 2. Sources

This draft cites only the sources below.

| Source | Local file | SHA-256 | What this draft used |
|---|---|---|---|
| Blind plan | `EVID/critical-path-fra68-20260923.md` | `d5e7a32f…` | Whole file |
| A1 (template) | `docs/design/urban2010_cola_comparison.md` | `f674e8c6…` | Whole file |
| Track A design note | `docs/design/track-a-assembly.md` | `317927ad…` | Whole file |
| Urban (2010), text extraction | `EVID/urban-2010-reform-details.txt` | `0826fc19…` | Lines 1-120 only (pages 1-2): date (6), outcome sentence (25-27), Table 1 (58-86), Figure 1 source and note (114-115) |
| 42 U.S.C. 416(l), 402(q), 402(w), 423(a)(1), 403(f), 403(j); and 402(q)(9)(B)(ii), 402(e)(2)(C), 402(f)(2)(C) and 402(b)(1) from the full page text | `EVID/fra68-statute-20260924/usc-42-fra-excerpts.txt`; `EVID/fra68-statute-20260924/usc42_402.txt` lines 208, 258 and 419 | `2c7605ee…`; `84a2336f…` | Official text, uscode.house.gov, current ("prelim") edition, fetched 2026-09-24; the folder holds the pages, their text conversion and `SHA256SUMS`. Amendment notes checked (§20). `e1-draft-4` also cites 402(q)(3)(C) (`usc42_402.txt` lines 383-385) and 403(f)(9) (`usc42_403.txt` line 170); `e1-draft-5` cites 402(q)(1) and 402(q)(6)(B) at lines 371 and 406 of `usc42_402.txt` (`SHA256SUMS` verified 2026-09-24); `e1-draft-6` cites 402(b)(1), 402(q)(5)(C) and 402(q)(6)(A)(ii) at lines 58, 399 and 404 (`SHA256SUMS` verified again) |
| DYNASIM3 primer (Favreault and Smith 2004) | `~/PolicyEngine/dynasim-refs/410961-dynasim3-primer.txt` | `0ad06f68…` | p. 3 (fn. 5), Table 3 (p. 6, OASI row), p. 14 (OASI take-up), pp. 16-17 (benefit calculator, fns. 15-16) |
| 2008 Trustees Report (TR2008) | `EVID/tr2008-inputs-20260922/tr08-2008-oasdi-trustees-report.pdf` | `517de81a…` | `e1-draft-4`: pp. 111-112 (claiming at 63-69) and pp. 118-119 (ultimate DI incidence), read through `pdftotext -layout`, printed pages from the page footers |
| Referee report on `e1-draft-3` | `EVID/fra68-referee-20260924.md` | `943af2a3…` | Whole file (§25) |
| Independent review of `e1-draft-4` | `EVID/fra68-conversion-claim-20260924/review-e1-draft-4-20260924.json` (the review lane's record, copied verbatim from the workflow's results file) | `c6da180f…` | Whole record (§25) |
| Conversion-claim arithmetic | `EVID/fra68-conversion-claim-20260924/conversion_claim_arithmetic.py` and its output `conversion_claim_arithmetic.out` | `af508eb1…`; `e82b5e3f…` | Exact-integer months early of a converted spouse's excess by cohort, schedule and worker-entitlement year under each rule; imports nothing from the repository (§11, §25) |
| Independent review of `e1-draft-5`: arithmetic and calculator probe | `EVID/fra68-review2-b4d8732e-20260924/independent_arithmetic.py` and its output `independent_arithmetic.out.json`; `probe_moved_worker_calculator.py` and its output at `b4d8732e`, `probe_moved_worker_calculator.b4d8732e.json` | `481b76c9…`; `27fe381b…`; `f7f52618…`; `465c7eff…` | Exact-integer schedules, conversion-claim counts and moved-worker counts, importing nothing from the repository; the calculator's counts and 2030 amounts for three invented spouses whose worker's claim C1 or C2 moved (§13, §19, §25) |
| Builder restriction list | `EVID/RESTRICTED-FILES.md` | — (a living list; no hash is pinned) | Whole file, read first by each lane since `e1-draft-4`. The `e1-draft-5` lane read the version whose last changelog entry is dated 2026-09-24 13:55. `e1-draft-4` recorded SHA-256 `a7356057…`, which the list no longer matches and which the review of `e1-draft-4` could not verify for any version; this draft withdraws it (§25) |
| Decision records d188 and d196 | `~/chief-of-staff/state/decisions/decisions.jsonl`, entries `d188` and `d196` | — | Their filed wording, defaults and status (`open`); d188 read 2026-09-24 by the `e1-draft-4` lane, both read 2026-09-24 by the `e1-draft-5` lane (§22) |
| Claim-age reference | `data/external/ssa_claim_ages_2023supplement.json` | `f731c9a6…` | The 2008 rows through `claiming.claim_age_distribution`: `fra_at.at_age` = 65 for both sexes; age-62 shares 42.6 (male) and 48.0 (female); age-65 shares 25.8 and 19.3 |
| Statutory capture | `data/external/track_a_statutory_parameters.json` | `fd56a8aa…` | FRA schedule, early rates, credit schedule and cap, auxiliary constants (the baseline bundle) |
| Repo code, read this session | `ss/params.py` and `ss/benefits.py` (whole), `claiming.py` (`benefit_factor`, `months_early`, `months_late`, `claim_age_distribution`, `claim_age_pmf`), `scenario_benefits.py` (rates and path functions), `cola_track_a/` (`config`, `benefits`, `runner`, `opening`, `adapters` whole; `statutory` in part), `engine/di_entitlement.py` (FRA attainment, conversion and exposure), `engine/claiming.py`, `estimates/cola_age_profile.py` (configuration and tabulation). The `e1-draft-4` lane read `cola_track_a/benefits.py` (`_Calculator`: worker, decedent, spouse's and widow(er)'s records), `cola_track_a/config.py` (Max's exercise-1 rulings), `ss/benefits.py` (`spousal_benefit`, `widow_benefit`), `estimates/cola_age_profile.py` (`_membership_masks`, `_cell_values`, the ratification test) and `fra68_track/` whole. The `e1-draft-5` lane read `fra68_track/benefits.py` and `reform.py` whole, `cola_track_a/benefits.py` (`_Calculator`: worker record, own claim year, spouse's excess, exposure start and PIA paths), `engine/di_entitlement.py` (`fra_attainment_year` and the conversion step), `engine/steps.py` (`apply_claiming`), `scenario_benefits.spouse_excess_path` and `ss/benefits.py` (`spousal_benefit`, `spousal_early_reduction`). The `e1-draft-6` lane read `fra68_track/benefits.py` and `reform.py` whole, `cola_track_a/benefits.py` whole, `engine/di_entitlement.py` (`fra_attainment_year` and the conversion step), `engine/steps.py` (`apply_claiming`), `scenario_benefits.spouse_excess_path` and `ss/benefits.py` (`spousal_benefit`, `spousal_early_reduction`) | — | Mechanisms cited in §§3-16 |

**Not opened:** see the header. The DYNASIM scorecard
(`EVID/dynasim-scorecard.md`) is cited through the plan only (plan §1:
Table 1 and Figure 2 are the scorecard's source for "COLA and FRA", and
its exercise 3 is "Percentage change in adult benefits in 2030 by age");
this draft did not re-read it.

## 3. Policy

**The statute (baseline).** 416(l)(1) defines the "retirement age" (full
retirement age, FRA) by the calendar year in which a person attains
"early retirement age": 66 for those attaining it in 2005-2016
((l)(1)(C)), 66 plus the age increase factor in 2017-2021 ((l)(1)(D);
under (l)(3)(B) two-twelfths of the months from January 2017 through
December of that year, so two months per year), and 67 from 2022
((l)(1)(E)). 416(l)(2): early retirement age is "age 62 in the case of
an old-age, wife's, or husband's insurance benefit, and age 60 in the
case of a widow's or widower's insurance benefit." The committed capture
holds the worker schedule by birth year: 792 months (66) for 1943-1954,
794-802 for 1955-1959, 804 (67) from 1960.

**What Table 1 fixes.** FRA is 66 "for those age 62 today" (the fact
sheet is dated May 2010, `:6`), which the statute also gives every
cohort turning 62 in 2005-2016; the increase is gradual and begins "in
2010"; FRA is 68 "for those turning 62 in 2022 and later". "Age 62
today" does not say whether the cohort turning 62 in 2010 is reached,
which is the difference between P1 and P2/P3. Table 1 writes a cohort
start as such (PPI: "beginning with those turning age 62 in 2012",
`:73`) and a calendar start as "starting in" or "effective in" 2010
(`:62`, `:80-81`, `:86`); the referee reads the FRA option's
"beginning in 2010" as calendar phrasing, which places the first
affected claims in 2010 (P2, P3) rather than 2011 (P1) (§25). From 66 in
2009 to 68 in 2022 is 24 months over 13 cohorts, and 13k = 24 has no
integer solution, so no constant whole-month step meets both dates; the
two-month step of 416(l)(3) meets one or the other.

**The three frozen schedules** (by year Y of turning 62; birth year
Y - 62; months):

| Reading | Rule | "Beginning in 2010" | "68 for those turning 62 in 2022" |
|---|---|---|---|
| **P3 (proposed primary; pending, d188 item (b))** | 66 years + round(24 (Y - 2009) / 13) months for 2010-2021, rounded to the nearest whole month (no tie arises: a tie needs 48k congruent to 13 modulo 26); 68 from 2022 | Yes | Yes |
| P1 | 66 + 2 (Y - 2010) months for 2011-2021; 68 from 2022 | Only as an enactment date (the 2011 cohort is the first affected) | Yes |
| P2 | 66 + 2 (Y - 2009) months from 2010, capped at 68 | Yes | No (the 2021 cohort reaches 68) |

| Y (turns 62) | Birth | Baseline (416(l)) | P1 | P2 | P3 | Increase P1 / P2 / P3 (months) |
|---|---|---|---|---|---|---|
| 2009 | 1947 | 792 | 792 | 792 | 792 | 0 / 0 / 0 |
| 2010 | 1948 | 792 | 792 | 794 | 794 | 0 / 2 / 2 |
| 2011 | 1949 | 792 | 794 | 796 | 796 | 2 / 4 / 4 |
| 2012 | 1950 | 792 | 796 | 798 | 798 | 4 / 6 / 6 |
| 2013 | 1951 | 792 | 798 | 800 | 799 | 6 / 8 / 7 |
| 2014 | 1952 | 792 | 800 | 802 | 801 | 8 / 10 / 9 |
| 2015 | 1953 | 792 | 802 | 804 | 803 | 10 / 12 / 11 |
| 2016 | 1954 | 792 | 804 | 806 | 805 | 12 / 14 / 13 |
| 2017 | 1955 | 794 | 806 | 808 | 807 | 12 / 14 / 13 |
| 2018 | 1956 | 796 | 808 | 810 | 809 | 12 / 14 / 13 |
| 2019 | 1957 | 798 | 810 | 812 | 810 | 12 / 14 / 12 |
| 2020 | 1958 | 800 | 812 | 814 | 812 | 12 / 14 / 12 |
| 2021 | 1959 | 802 | 814 | 816 | 814 | 12 / 14 / 12 |
| 2022 and later | 1960 and later | 804 | 816 | 816 | 816 | 12 / 12 / 12 |

`fra68_track.reform.SCHEDULES` holds these tables and
`tests/test_urban2010_fra68_spec.py` holds them to this section and to
§21. Every schedule equals the baseline for cohorts turning 62 before
2010, is at or above the baseline for every cohort and is 816 months from
birth year 1960; `reform_parameters` refuses a schedule for which any of
this fails.

**Frozen policy.**

1. The reform replaces the worker schedule of 416(l)(1) by the chosen
   schedule. It is implemented as a parameter override of the oracle's
   `SSAParameters.fra_months_by_birth_year` (pending, d188 item (a)); it
   adds no statutory rule coverage.
2. **Survivors (416(l)(2) mapping).** The schedule is keyed to the year a
   person attains early retirement age, which for a widow(er) is 60, so a
   widow(er) born in b has the worker schedule's value for b - 2. Under
   P3 that is 66y2m for widow(er)s born in 1950, rising to 68 for those
   born in 1962 and later. The widow(er)'s reduction, 28.5 percent at 60
   falling linearly to 0 at retirement age (402(q)(9)(B)(ii),
   `usc42_402.txt` line 419), is spread over the months from 60 to that
   age. Row F0 applies the mapping; row F7
   keeps survivors' retirement age at the baseline (Table 1 speaks only
   of "those turning 62"). The span is exact by cohort in **both**
   scenarios (§11, §12).
3. **Spouses.** 416(l)(2) gives wife's and husband's benefits the same
   early retirement age as workers, so a spouse's months early are
   counted against the spouse's own-birth-year FRA under the reform
   schedule. No alternative is registered.
4. **Unchanged.** The early-reduction rates (5/9 and 5/12 of 1 percent;
   spouses 25/36 and 5/12), the 36-month break, the credit rate (2/3 of
   1 percent a month, 402(w)(6)(D)), the age-70 end of credits
   (402(w)(2)(A)), the 28.5 percent widow(er) reduction at 60, the PIA,
   the COLAs, the AWI, the bend points, the wage base and every
   earnings-test exempt amount. Consequences for a 12-month increase: a
   worker's reduction at 62 goes from 30 to 35 percent, a spouse's from
   35 to 40 percent, and the largest credit at 70 from 24 to 16 percent
   (the oracle's `delayed_credit` caps accrual at `min(48, 840 - FRA)`
   months).
5. **Absolute, not additive.** An additive reading (the baseline plus
   one month per year from the 2011 cohort) was considered and is not
   registered: Table 1 states the path as a level ("until it reaches
   68") from the 66 of its current-law sentence.
6. **DI.** 402(q)(1) reduces old-age, wife's, husband's, widow's and
   widower's benefits only, and only when the first month of entitlement
   "is a month before the month in which such individual attains
   retirement age" (`usc42_402.txt` line 371). 423(a)(1) ends DI
   entitlement with the month before the month of attaining retirement
   age, so an old-age benefit first payable in that month is not
   reduced. (This draft did not read 402(a); in the model the conversion
   is A4's, in the FRA attainment year.) A disabled worker's benefit
   ratio is exactly 1; the reform moves conversion from 67 to 68 (a
   component label) and extends DI eligibility to 68 (a named delta,
   §12). The same holds for a converted worker's spouse's excess, which
   Track A starts at the conversion: unreduced in both scenarios under
   the statute, ratio 1 in the model (§11, rule 3).

## 4. Rate path

**Carried over by reference.** A1 §4 (TR2008 intermediate; determination
years; the 2018-2030 reconstruction; the stabilizer check; the splice
rule) applies unchanged, with one difference: the path applies in **both**
scenarios. Exercise 3 changes no increase (`ScenarioCOLARates` with
`reform=None` in both scenarios), so A1's floor assertion and R0/R1
first-increase rows have no counterpart. They are replaced by one record
in every run (`cola_paths` in the artifact): both scenarios read the same
rate source object.

## 5. Phase-in schedule rows

The primary schedule (P3, pending) and the two registered alternatives
(P1 as F1, P2 as F2) are §3's. What the choice changes in 2030
(statute arithmetic, plan §3, recomputed by this draft through the code
for the worker factors):

- **62-69** (born 1961-1968): a 12-month increase under every schedule.
- **70-79** (born 1951-1960): increases of 6-12 months (P1), 8-14 (P2)
  or 7-13 (P3). The largest spread of an individual factor change between
  schedules is 1.19-1.28 percentage points by cohort for those born
  1951-1959, and none for 1960 (recomputed through the code for claim
  ages 62-70).
- **80+** (born 1950 or earlier): only the 1948-1950 cohorts (aged 80-82)
  are affected, by 0/2/4 months (P1) or 2/4/6 months (P2, P3).

If Max chooses another primary (d188 item (b)), F0 takes it and F1, F2
take the other two in the order P1, P2, P3 (`config.registered_rows`).

## 6. Who the reform reaches

Replaces A1 §6 (exposure clock; R2 does not carry over). The ratio of an
individual's reform to baseline benefit depends on the age factor only:
the PIA and the COLA path are the same in both scenarios and cancel,
apart from dime flooring.

- **Retired worker** (projected claim): the claim-age factor
  `claiming.benefit_factor(12 min(a, 70), b, bundle)`, a the claim age
  in years, under each scenario's bundle. For a 12-month increase:

  | Claim age | 62 | 63 | 64 | 65 | 66 | 67 | 68 | 69 | 70 |
  |---|---|---|---|---|---|---|---|---|---|
  | Change (%) | -7.14 | -6.67 | -6.25 | -7.69 | -7.14 | -6.67 | -7.41 | -6.90 | -6.45 |

  Phase-in cohorts, change at claim age 62 / 65 (%):

  | Birth | P1 | P2 | P3 |
  |---|---|---|---|
  | 1948 | 0 / 0 | -1.11 / -1.19 | -1.11 / -1.19 |
  | 1949 | -1.11 / -1.19 | -2.22 / -2.38 | -2.22 / -2.38 |
  | 1950 | -2.22 / -2.38 | -3.33 / -3.57 | -3.33 / -3.57 |
  | 1951 | -3.33 / -3.57 | -4.44 / -4.76 | -3.89 / -4.17 |
  | 1952 | -4.44 / -4.76 | -5.56 / -5.95 | -5.00 / -5.36 |
  | 1953 | -5.56 / -5.95 | -6.67 / -7.14 | -6.11 / -6.55 |
  | 1954 | -6.67 / -7.14 | -7.78 / -8.33 | -7.22 / -7.74 |

- **Spouse's excess**: months early against the scenario FRA for the
  spouse's birth year at the spouse's entitlement year; spouses born 1960
  or later: -7.69 at 62, -7.14 at 63, -6.67 at 64, -10.00 at 65, -9.09 at
  66, -8.33 at 67, 0 from 68 (no credits). A converted disabled worker's
  excess on its conversion claim: ratio 1 in every cohort whenever the
  scenario has converted the worker by 2030 (§11, rule 3; a worker still
  DI-entitled under the reform draws none, §12).
- **Aged widow(er)** (survivors born 1962 or later, survivor retirement
  age 67 to 68): 0 at 60 (the 71.5 percent floor holds in both), -0.67,
  -1.28, -1.82, -2.32, -2.77, -3.18 and -3.56 at 61-67, 0 at 68. The
  deceased's own claim-age factor also changes, which moves the RIB-LIM
  cap when the deceased claimed early and the credits a widow(er)
  inherits from a deceased who claimed after retirement age
  (`ss.benefits.widow_benefit`). A deceased who never claimed carries
  factor 1.0 in both scenarios (Track A's `deceased_unentitled` record),
  so the credits that 402(e)(2)(C) and 402(f)(2)(C) pass to the survivor
  of a worker who died after retirement age without claiming, which the
  reform reduces, are not modeled (§12).
- **Disabled worker**: ratio 1.
- **Opening stock**: recipients observed in the opening year claimed by
  then. The reform amount is the observed amount carried on the baseline
  path (A1 §11, rule 4; Max's ruling d075 for exercise 1; its carry-over
  is pending as `opening_stock_basis`, d188 item (a)) times the
  component's reform-to-baseline age-factor ratio for a retired-worker or
  spouse record claimed at 62 or later
  (`reform.opening_stock_factor_ratio`), and 1 for every other record.
  Under the 2011 wave (opening 2010) only retirement or spouse claimants
  born in 1948 who claimed at 62 in 2010 face a higher retirement age,
  and only under P2 or P3: -1.11 percent for a retired worker and -1.19
  percent for a spouse (§19). Under the 2009 wave (opening 2008) nobody
  in the opening stock is affected.

The tables above are the plan's §4 arithmetic; this draft recomputed
every entry through `fra68_track.reform` and the oracle and found the
same values (`tests/fra68_track/test_reform.py`).

## 7. Statistic

**Carried over** (A1 §7): the weighted ratio of scenario means per draw,
the mean and sample standard deviation (divisor K - 1) over K = 20 draws,
failing closed on undefined cells. The weighted mean of individual ratios
is registered as F5 (A1's R3 semantics: recipients in both scenarios).

**Membership is scenario-specific** (A7 `membership_basis =
"scenario_specific"`, `allow_membership_difference = true`): S_base is the
set of baseline recipients and S_reform the set of reform recipients, each
with a positive selected benefit in its scenario. For draw k and age group
g, the headline statistic of every row except F5 is

```text
Δ[g,k] = 100 × ( (Σ_{i∈S_reform[g,k]} w_i · B_reform[i,k] / Σ_{i∈S_reform[g,k]} w_i)
               / (Σ_{i∈S_base[g,k]} w_i · B_base[i,k] / Σ_{i∈S_base[g,k]} w_i) − 1 )
```

and F5's is

```text
Δ'[g,k] = 100 × ( Σ_{i∈S_alt[g,k]} w_i · (B_reform[i,k] / B_base[i,k]) / Σ_{i∈S_alt[g,k]} w_i − 1 ),
```

where S_alt holds the persons in both S_base and S_reform with
B_base > 0, and B is the row's selected components (A7 `_cell_values`).
Under C0 the two sets coincide (every factor is positive, and a
relabelled DI conversion keeps its amount), so Δ equals A1's
common-membership statistic. The runner refuses a C0 row whose A7 input
summary reports a membership difference. Under C1 and C2 (§13) the sets
differ, and the ratio of weighted totals over the union is reported as a
diagnostic, not registered.

**Statistic identifier:** `dynasim_exercise3_fra68_reference_year_age_profile`
(the A7 `statistic_id` argument).

## 8. Membership

Carried over (A1 §8): alive in the 2030 state of the draw with a positive
benefit in the scenario; person weights; decedents as A1. The A7 input
has one row per person positive in either scenario, with honest
`beneficiary_base` and `beneficiary_reform` flags.

## 9. Age

Carried over (A1 §9): age = 2030 - birth year; groups 50-61, 62-64,
65-69, 70-79, 80+. Statutory ages are annual: a claim at age a is 12a
months, and FRA months enter the factor exactly (§12, month
resolution).

## 10. Benefit period

R0's calendar-2030 payments are carried over (A1 §10). **R4 is not
registered**: both scenarios carry the same December 2030 increase, so in
the annual model the December row equals F0 up to dime flooring.

## 11. Benefit components, amount rules and rounding

**Components:** A1's five (retired workers including converted disabled
workers, disabled workers, spouses 62 or older, aged widow(er)s from 60,
disabled widow(er)s under 60); F6 keeps retired and disabled workers
only, with A1 R5's benefit-level semantics.

**Amount rules** (Track A's, `cola_track_a.benefits`, with the
scenario's bundle; `fra68_track.benefits`):

1. PIA paths, dime flooring after each increase and after the factor,
   dual entitlement through the oracle's `spousal_benefit` and
   `widow_benefit`, gross amounts: A1 §11 rules 1-3 and 5, unchanged.
2. **Per-scenario factors.** Retired worker: `benefit_factor` under the
   scenario bundle. Spouse's excess: months early against the scenario
   FRA of the spouse's birth year, from the later of the spouse's own
   claim and the worker's entitlement (under C1 and C2 a moved own claim
   and a moved worker entitlement each enter at their exact month, §13; a
   conversion claim follows rule 3). Aged widow(er): the oracle's `widow_benefit` with the reduction
   span of the survivor's cohort (§3, item 2), in both scenarios; the
   deceased's scenario factor feeds the RIB-LIM and the inherited credits
   (a deceased who never claimed carries factor 1.0, §12). DI: factor 1.
3. **Conversion.** A worker the projection converted at the baseline FRA
   (A4's `fra_attainment_year`, July birth month) is a disabled worker in
   a scenario whose FRA attainment year is after the state's year: only
   the component label changes. By Track A's convention a disabled worker
   still entitled to DI draws no spouse's excess, so under the reform a
   converted worker's excess can start later (§12). A converted worker's
   own claim for the excess is the conversion (Track A's rule, unless a
   retirement claim preceded it; `ScenarioCalculator.conversion_claim_year`),
   and the excess enters each scenario in that scenario's conversion
   year. Its months early are counted from the **baseline start moved by
   D(b)**:
   max(0, F'(b) - (max(12 (y_c - b), 12 (y_w - b)) + D(b))), where y_c is
   the baseline conversion (Track A's own claim year) and y_w the
   worker's baseline entitlement year, before any C1/C2 move
   (`reform.conversion_claim_excess_months_early`). This equals Track A's
   baseline count in every scenario and under every claiming response,
   so the reform-to-baseline ratio of these excesses is 1, the statute's
   answer: 402(q)(1) reduces a wife's or husband's benefit only "if the
   first month for which an individual is entitled to" it "is a month
   before the month in which such individual attains retirement age"
   (`usc42_402.txt` line 371), and the reduction period ends "with the
   last day of the month before the month in which such individual
   attains retirement age" (402(q)(6)(B), line 406). An excess that starts at the conversion, at FRA, is therefore
   unreduced in both scenarios. Where the conversion starts the baseline
   excess (y_w <= y_c), the rule is the conversion claim moved by exactly
   D months, 12 (y_c - b) + D, the device §13 uses for moved claims. Where
   the worker's later entitlement starts it (y_w > y_c), the baseline
   count is 0 and moving the whole start keeps it 0; moving the
   conversion claim alone would count 2 months for spouses born 1955 and
   4 for 1956 under every schedule when y_w = y_c + 1, a reduction the
   statute does not make. The baseline count itself is Track A's
   whole-year artifact, a named delta (§12). (`e1-draft-4` counted from
   the scenario's whole conversion year, which changed the months early
   by the change in FRA mod 12; §25.)
4. **Opening stock:** §6. The basis stays frozen at the opening year; no
   dime flooring.
5. **Survivor reduction span.** Exact by cohort in both scenarios:
   survivor retirement age (416(l)(2) mapping on the scenario schedule,
   or on the baseline schedule for F7's reform) minus 60 years. Exercise
   1 used the oracle's fixed 84 months; the two differ for survivors born
   before 1962 who were entitled after 60 (referee question 7). Pending
   as its own decision field, `survivor_reduction_span` (§22 item 2).

## 12. Named omitted deltas

A1 §12 is carried over, with these exercise-3 items:

| Item | What is known | Where it enters |
|---|---|---|
| Retirement earnings test to 68 | 403(f)(1)(B) charges no excess earnings to a month at or above retirement age, 403(f)(8)(E) makes no deduction from the month of attaining it, and 403(f)(9) makes the retirement age in paragraphs (3), (5)(D)(i), (8)(D) and (8)(E) the one that applies to old-age benefits, whatever benefit the person receives: raising the retirement age extends the test to 68. The primer says the calculator "checks current earnings to see whether a benefit is actually received" (p. 16) and that workers claim at the simulated take-up age unless their earnings would reduce the annual benefit to less than one month's benefit (pp. 16-17). Track A draws no earnings after the opening year and pays gross amounts | If run 614's 2030 benefits are net of the test, its reform lowers receipts of working claimants aged 67 beyond Track A (65-69). Needs forward earnings (a Track B prerequisite) |
| Adjusted reduction period | 402(q)(7)(A) excludes months with 403(b), (c)(1) or (d)(1) deductions from the adjusted reduction period; not modeled | Tied to the earnings test |
| DI window extension | 423(a)(1)(B) makes DI entitlement depend on not having attained retirement age, so the reform extends DI eligibility to 68. New reform-only awards would get 100 percent of PIA instead of a reduced retirement benefit. TR2008's ultimate DI incidence rates reflect "the impact of scheduled increases in the normal retirement age" (pp. 118-119) | Needs a second projection. Diagnostic in every run: persons alive, not DI-entitled and not converted in the years from the baseline to the reform FRA attainment year, with their expected awards at A4's rates (`di_window_diagnostic`) |
| DI recovery in the extended window | A4 draws no recovery after the baseline conversion | Membership only |
| Whole-year conversion claim (Track A) | Track A counts a converted worker's claim for the spouse's excess from the whole conversion year (the year of attaining FRA under A4's July birth month), as month 12 (y_c - b). That is FRA mod 12 months before the FRA when the remainder is below 6: 2 months for spouses born 1955 and 4 for 1956 under the statutory schedule (and for 1938 and 1939, who converted before either opening year). 402(q)(1) and (q)(6)(B) (`usc42_402.txt` lines 371 and 406) reduce an excess that starts at FRA not at all. Counting the conversion claim from its exact month (0 months early) in both scenarios would change exercise 1's baseline for these spouses, a choice for Max that this draft does not make (option (a) of the review of `e1-draft-4`, §25) | Baseline and reform levels only: the excess of a converted spouse born 1955 or 1956 whose conversion starts it is reduced by 1.39 or 2.78 percent (2 or 4 months at 25/36 of 1 percent) in both scenarios, and the reform ratio is 1 (§11, rule 3). Diagnostic in every run (benefit counters, by scenario): `fra68_spouse_excess_on_conversion_claim`, the paid spouse's excesses on a conversion claim, and `fra68_spouse_excess_on_conversion_claim_months_early`, those whose months early are positive |
| Spouse's excess of a DI beneficiary | Track A convention: none while DI-entitled. 402(q)(3)(C) (`usc42_402.txt` lines 383-385) would pay a DI beneficiary a reduced excess | Under the reform it starts at 68 instead of 67 for a converted worker, so the convention overstates the reform's cut for converted workers aged 67 in 2030 (born 1963) |
| Survivor reduction span | Exact by cohort here (pending, `survivor_reduction_span`, §22); fixed 84 months in exercise 1 | Baseline amounts of survivors born before 1962 entitled after 60 differ from exercise 1's |
| Credit timing | 402(w)(3) credits increment months from January of the following year; Track A applies the full factor at the claim | Small; both scenarios |
| Credits of a worker who died unclaimed | 402(e)(2)(C) and 402(f)(2)(C) (`EVID/fra68-statute-20260924/usc42_402.txt` lines 208 and 258): if the deceased "was (or upon application would have been) entitled to" a benefit increased by delayed retirement credits, the survivor's benefit rests on that increased benefit, counting increment months through the month before death. Track A's `deceased_unentitled` record uses factor 1.0 in both scenarios. The records carry an annual death year only, so the credits cannot be counted by month without a new convention | Survivors of workers who died unclaimed after the baseline retirement age inherit no credits in either scenario, so the reform's cut of up to D credit months (8 percentage points for D = 12) is missed. Under C1 and C2 a claimant who dies before the moved claim loses all credits in the reform scenario, where the statute would keep those accrued from the reform retirement age. Aged widow(er)s. Diagnostic in every run (benefit counters, by scenario): `fra68_widow_credits_not_inherited`, the paid aged widow(er)'s excesses resting on a never-entitled decedent who died in or after the calendar year of attaining the scenario's retirement age, and `fra68_widow_credits_not_inherited_claim_moved_past_death`, the subset whose claim C1 or C2 moved past death. The count is not a bound on the survivors the statute would pass credits to: the death month is unknown, so it can include a decedent who died in the attainment year before the retirement-age month, and it omits a survivor paid no excess without the credits whom the credits would have given one |
| Month resolution and birth month | Integer claim ages; the July birth month of A4 for conversion and for the C1/C2 dates | Odd-month increases enter exactly; the C1/C2 delay is 0 below 6 months |
| Claiming response | DYNASIM3's OASI take-up hazard uses "age, benefit amount, spousal characteristics, and Social Security policy parameters" (primer Table 3, p. 6; p. 14), with separate equations "for groups with different ratios of recent earnings to the Social Security exempt amount" (p. 14); its benefit calculator applies "statutory adjustment factors for retirement at ages other than the normal retirement age and the Retirement Earnings Test" (p. 16) | Registered as C1 and C2 (§13); 62-69 membership and weights |
| Claim-age mix | Track A snaps every projection year to the 2008 row of the claim table, whose at-FRA age is 65 for every cohort. TR2008 projects claiming at 63-69 "with an adjustment for changes in the portion of the primary insurance amount that is payable at each age of entitlement" (pp. 111-112) | 62-69 membership; the C1 anchor (referee question 3); the mix itself is referee question 5 |
| Phase-in and survivor mapping | Registered as F1, F2 and F7 | 70-79, 80+ and survivors |

## 13. Behavior (claiming)

**Primary, C0: fixed claim ages.** Every projected retirement claimant
keeps the integer claim age the shared projection gave; only the factor
changes. Opening-stock claim ages are A3's `opening_claim_age`.
Membership is identical in both scenarios. Basis: it isolates the
statutory change, and the primer says "changes in Social Security
benefits or pension provisions do not affect previously simulated
demographic or economic outcomes" (p. 3, fn. 5).

**Why alternatives are registered.** The primer's OASI take-up is a
discrete-time hazard from 62 in which "everyone who is eligible takes up
benefits by age 70", and it includes "Social Security policy parameters
(e.g., dual entitlement)" (p. 14; Table 3, p. 6). Whether its hazard has
a retirement-age term is not stated in what this draft read.

**C1 and C2** (deterministic transforms of the shared projection; no new
draw, no second projection). With D(b) the reform minus the baseline FRA
for birth year b, a projected claimant with claim age a (claim year minus
birth year, at most 70) gets:

- the reform claim month m' = min(12a + D, 840);
- the reform entitlement year: the baseline claim year plus
  floor((6 + m') / 12) - a (A4's July birth month), which adds a year
  exactly when D >= 6 and a < 70;
- the reform factor `benefit_factor(m', b, reform bundle)`. Months from
  the retirement age are preserved, so the factor is unchanged whenever
  12a + D <= 840; a claim at 70 keeps its age and its credit falls (24 to
  16 percent for a 12-month increase).

C1 applies the transform to claimants whose claim age is at least the
anchor age: the at-FRA age of the claim-table row the projection reads,
65 for both sexes in the 2008 row (`fra_at.at_age`; referee question 3).
The snap to the 2008 row puts the projection's FRA claimers at 65 in
every cohort, so the anchor moves the claimants the projection treats as
FRA claimants. An anchor at each cohort's own FRA (66 or 67) would move
only the 66-and-older categories (3.8 percent of male and 5.9 percent of
female 2008 awards) and leave the spike in place.
C2 applies it to every projected claimant. Rules common to both: claims
made at or before the opening year, DI records, conversions and the
survivors' entitlement rule are unchanged; a spouse's excess starts at
the later of the spouse's own reform claim year and the worker's reform
entitlement year, and is reduced for max(0, F'(b_s) - s) months, where
F'(b_s) is the reform FRA of the spouse's birth year,
s = max(m'_s, 12 (y_w - b_s) + v_w), m'_s is the spouse's own reform
claim month (12 a_s when the spouse's claim is not transformed), y_w is
the worker's entitlement year before any transform and
v_w = min(12 a_w + D(b_w), 840) - 12 a_w is the number of months the
transform moved the worker's claim (0 when it is not transformed). Both
moved claims enter at their exact months, A4's July birth month for both
spouses: 402(b)(1) entitles a wife only as the wife "of an individual
entitled to old-age or disability insurance benefits"
(`usc42_402.txt` line 58), and her reduction period begins with her first
month of entitlement (402(q)(5)(C) and (6)(A)(ii), lines 399 and 404), so
a worker's claim moved by v_w months moves the start of the spouse's
reduction by v_w months. Under C0 this is §11's rule. A transformed
spouse's excess therefore keeps its baseline distance from the retirement
age, as the worker's own factor does, when the spouse's own claim starts
it; when the worker's moved entitlement starts it, the reduction changes
by D(b_s) - v_w months, which is not 0 when the two spouses' FRA
increases differ. (Counting months early from the whole start year
instead would change a transformed excess's reduction by D(b_s) -
12 x (its start-year shift) months: a cut when D < 6 or D >= 13 and a
rise when 6 <= D <= 11, with no response behind either. `e1-draft-5`
still counted a moved worker entitlement that way, from y'_w, the
worker's reform entitlement year; §19 and §25.) A converted
worker's excess on its conversion claim follows §11 rule 3 under every
claiming response: its count reads the worker's baseline entitlement
year, so a C1/C2 move of the worker's claim changes when the excess is
paid (from y'_w) but not its months early. A worker who
dies before the reform claim year is a never-entitled decedent in the
reform scenario (Track A's `deceased_unentitled` record, factor 1.0: no
RIB-LIM and no inherited credits; §12).

Under C1 and C2 membership differs between scenarios: a baseline
claimant whose reform entitlement year falls after 2030 is not a reform
beneficiary. C0 and C2 bracket no response and full postponement; C1 is
anchored to a published category, not a fitted elasticity.

## 14. Population and vintage

Carried over (A1 §14): the 2011 wave (ER34155, opening 2010, 20 periods,
family unit ER34101) for F0-F7 and the 2009 wave (ER34046, opening 2008,
22 periods, family unit ER34001) for F8. With the same inputs, seeds and
Track A configuration the projection is exercise 1's, path for path; a
registered run records whether its draw diagnostics equal those of the
committed exercise-1 artifact (`projection_identity_with_exercise_1`,
never refused).

## 15. Parameters

Nothing new from TR2008: the COLA path, the AWI, the mortality
substitute and the DI rates are Track A's committed inputs, value-checked
as in exercise 1 (the baseline bundle is bound to the committed capture).
The only new frozen parameters are the three schedules (§3) and the
survivor mapping rule, held in §21 and in code constants tested against
it. Each reform bundle is derived from the baseline bundle and recorded
with its own SHA-256 (`age_factor_parameters`). The committed early rates
are rounded (0.00555556 for 5/9 of 1 percent); the worked cases (§19) use
them, and they move ratios by less than 10^-5.

## 16. Uncertainty

Carried over (A1 §16): K = 20 draws, root entropy 5200 + k; the
half-split floor over seeds 0-4 on the opening-wave family unit,
undefined with fewer than two usable seeds; the comparator interval only
in the memo. Diagnostics with every cell (reported, not registered): the
unweighted beneficiary count by scenario (A7), the weighted component
shares, the weighted mean FRA increase over baseline recipients, the
retired-worker rows by claim age in each scenario, the shares of benefit
dollars held by DI-entitled and by converted disabled workers, per
draw the ratio of weighted totals over the union of recipients, and, by
row and scenario, the counts of paid widow(er)'s excesses whose inherited
credits the model omits (§12, credits of a worker who died unclaimed) and
of paid spouse's excesses on a conversion claim, with those whose months
early are positive (§12, whole-year conversion claim).

## 17. Acceptance rule

**Proposed: none** (pending, d188 item (a)). The comparison would be
reported, not gated; it runs once and is published regardless. No rule
may be set after registration.

## 18. Registered rows

Each alternative differs from F0 in one field. All rows are computed in
the same one-shot and published together. F0 is the headline row,
designated before any result; no row may be promoted afterwards. The row
set awaits Max's confirmation (d188 item (b)).

| Row | Field changed | Value | New projection? |
|---|---|---|---|
| **F0** | — (primary) | Schedule P3; survivors under the 416(l)(2) mapping; claiming C0; ratio of scenario means; five components; 2011 wave; calendar-2030 payments | Yes (Track A R0's projection) |
| F1 | FRA schedule | P1 | No |
| F2 | FRA schedule | P2 | No |
| F3 | Claiming response | C1 (claimants at or after 65 delay) | No |
| F4 | Claiming response | C2 (all projected claimants delay) | No |
| F5 | Statistic | Weighted mean of individual ratios | No |
| F6 | Components | Retired and disabled workers only | No |
| F7 | Survivor retirement age | Unchanged from baseline (the reform's survivor span uses the baseline schedule; the deceased's factor and the survivor's own benefit follow the reform schedule) | No |
| F8 | Population and vintage | PSID 2009 wave, ER34046, 2008 to 2030 | Yes (Track A R6's projection) |

**Not registered:** A1's R1 and R2 (COLA timing and clock) do not apply;
R4 equals F0 up to rounding; combined rows (A1 §23, question 1); a DI
window reprojection (§12; referee question 4); a claim-age mix that
follows each cohort's FRA (referee question 5).

## 19. Invented worked cases

These cases are **invented** for the unit tests. They use no PSID data,
no model output and no comparator value: the oracle's committed rates,
the A1 §21 TR2008 rate path (2.7, 2.5, then 2.8 percent), dime flooring
after each increase and after the factor, and 2030 monthly amounts. PIA
amounts are at the worker's eligibility year (birth year + 62).
`tests/fra68_track/test_reform.py` recomputes each through
`fra68_track.reform`, `claiming.benefit_factor` and the A6 path functions,
and `tests/test_urban2010_fra68_spec.py` holds this table to them.

| Invented case | Baseline | Reform | Change, dime-floored (%) | Change, unrounded factor (%) |
|---|---|---|---|---|
| Worker, born 1966, PIA $1,000.00, claims at 62 (P3) | $739.60 | $686.80 | -7.1390 | -7.1429 |
| Worker, born 1963, PIA $1,000.00, claims at 67 (P3) | $1,147.80 | $1,071.20 | -6.6736 | -6.6667 |
| Worker, born 1954, PIA $1,000.00, claims at 66 (P1) | $1,471.10 | $1,373.00 | -6.6685 | -6.6667 |
| Worker, born 1954, PIA $1,000.00, claims at 66 (P2) | $1,471.10 | $1,356.60 | -7.7833 | -7.7778 |
| Worker, born 1954, PIA $1,000.00, claims at 66 (P3) | $1,471.10 | $1,364.80 | -7.2259 | -7.2222 |
| Worker, born 1950, PIA $1,000.00, claims at 62 (P1) | $1,232.00 | $1,204.60 | -2.2240 | -2.2222 |
| Worker, born 1950, PIA $1,000.00, claims at 62 (P2) | $1,232.00 | $1,190.90 | -3.3360 | -3.3333 |
| Worker, born 1950, PIA $1,000.00, claims at 62 (P3) | $1,232.00 | $1,190.90 | -3.3360 | -3.3333 |
| Spouse, born 1966, claims at 62, own PIA $0; worker born 1964 with PIA $2,000.00 (P3) | $725.80 | $670.00 | -7.6881 | -7.6923 |
| Widow(er), born 1965, widowed and entitled at 63; worker born 1963 with PIA $1,500.00 who never claimed (P3) | $1,441.40 | $1,415.10 | -1.8246 | -1.8238 |
| The same widow(er), entitled at 60 (P3) | $1,231.10 | $1,231.10 | 0 | 0 |

Six further invented cases have no dollar amount:

- **Opening-stock retired worker**, born 1948, claimed at 62 in 2010
  (P3): factor 0.75 (baseline, 48 months early) to 0.741667 (50 months
  early), a ratio applied to the observed amount without a dime floor:
  -1.1111 percent.
- **Disabled worker**, any onset: ratio 1.
- **Spouse's excess under C2**, spouse born 1951 (P3, D = 7), whose own
  claim at 62 in 2013 starts the excess: reform claim month 751
  (entitled 2014), 799 - 751 = 48 months early, as in the baseline
  (792 - 744 = 48): factor 0.70 in both, ratio 1.
- **Spouse's excess under C2**, spouse born 1954 (P3, D = 13), whose own
  claim at 62 in 2016 starts the excess: reform claim month 757
  (entitled 2017), 805 - 757 = 48 months early, as in the baseline
  (792 - 744 = 48): factor 0.70 in both, ratio 1.
- **Converted spouse's excess**, spouse born 1956 (P2, D = 14), converted
  at FRA in 2022 with the worker entitled earlier, so the conversion
  starts the excess: baseline 796 - 792 = 4 months early (Track A's
  whole-year count), reform 810 - (792 + 14) = 4 months early: factor
  0.972222 in both, ratio 1. `e1-draft-4` counted from the reform's whole
  conversion year, 2024 (month 816): 0 months early, factor 1, +2.8571
  percent, above both the baseline and P3.
- **Spouse's excess under C1, started by the worker's moved claim**,
  spouse born 1953 (P3, D = 11) who claimed at 62 in 2015, worker born
  1951 (D = 7) who claimed at 65 in 2016, a claim C1 moves to month 787
  (entitled 2017): the spouse is 756 + 7 = 763 months old when the
  worker's moved entitlement starts, so 803 - 763 = 40 months early,
  against the baseline's 792 - 756 = 36: factor 0.733333 against 0.75,
  -2.2222 percent. `e1-draft-5` counted from the whole year 2017
  (month 768): 35 months early, factor 0.756944, +0.9259 percent, above
  the baseline.

## 20. Resolution map

The field list of `proposed-1` `required_unresolved` (as A1 §20 records
it), and where this draft resolves each for exercise 3:

| `proposed-1` field | Resolution | Section |
|---|---|---|
| `law_cutoff_and_historical_versions` | Law as TR2008 assumes it (A1 §1). The captured statute is the current (prelim) edition. Its amendment notes list no amendment of 416(l) after Pub. L. 98-21 (1983), of 402(q) after Pub. L. 103-296 (1994), or of 403(f)(1)(B), (f)(8)(E), (f)(9) and 403(j) after Pub. L. 106-182 (2000). Later amendments of quoted or cited text change nothing this draft relies on: 402(w)(2)(B)(ii) (Pub. L. 114-74, 2015, inserted "under subsection (z)"), 423(a)(1) (Pub. L. 116-250, 2020, the ALS clause), and cross-references in 402(e)(2)(C)-(D) and 402(f)(2)(C)-(D) (Pub. L. 118-273, 2025). The reform replaces the 416(l)(1) worker schedule and, under F0, reaches survivors through 416(l)(2) | §1, §2, §3 |
| `population_vintage_coverage_and_weights` | A1's R0 and R6 populations (F0, F8) | §14 |
| `trustees_alternative_and_parameter_splice` | A1's, in both scenarios | §4 |
| `complete_dated_parameter_sequences` | The schedules by year turning 62, 2010-2022 | §3, §21 |
| `first_effective_and_payment_months` | The first affected cohort turns 62 in 2010 (P2, P3) or 2011 (P1); annual resolution | §3, §9 |
| `exposure_and_existing_beneficiary_rules` | Who the reform reaches: age-factor rules and the opening-stock ratio | §6 |
| `floor_or_verified_nonbinding_condition` | No COLA floor applies; the schedule guards (never below the baseline, 816 months from 1960) | §3, §4 |
| `aggregation_formula` | F0: ratio of scenario means; F5: mean of individual ratios | §7 |
| `beneficiary_membership_and_zero_treatment` | Scenario-specific; identical under C0 (refused otherwise) | §7, §8 |
| `age_reference_and_decedent_selection` | A1's | §8, §9 |
| `benefit_period_and_partial_year_rules` | Calendar-2030 payments; R4 not registered | §10 |
| `benefit_components_offsets_and_rounding` | A1's five components (F6: workers only); per-scenario factor rules; exact survivor span | §11 |
| `interacting_indexation` | The reform changes only the retirement age (and so the age factors); no COLA or AWI change | §3, §4 |
| `behavioral_configuration` | C0 primary; C1 and C2 registered | §13 |
| `comparator_series_precision_and_provenance` | A sealed comparator lane (plan item E8), validation only, opened after the artifact is committed | §16, §17 |

**Where this draft adds to or departs from the plan:**

1. The statute is quoted from the official text (uscode.house.gov), not
   Cornell LII, and 403(f)(1)(B), (f)(8)(E) and (f)(9) are quoted for
   the earnings-test delta, which the plan left for E1 (§12).
2. The C1/C2 reform entitlement year is the baseline claim year shifted
   by floor((6 + m') / 12) - a, not b + floor((6 + m')/12): the two agree
   except for a plan drawn after its age had passed (claimed the next
   year), which the shift keeps (§13). With a the realized claim age the
   two formulas are identical whenever the claim year minus the birth
   year is at most 70; they differ only from the plan's formula in
   planned age.
3. The claim age the transforms read is the realized claim age (claim
   year minus birth year, at most 70), which Track A's factor already
   uses; the plan wrote "planned age" (§13; builder default).
4. A primary other than P3 has a defined row map: F1 and F2 take the
   other two schedules in the order P1, P2, P3 (§5).
5. A spouse record in the opening stock takes the spouse's factor ratio
   on its whole observed amount (it cannot be split into own benefit and
   excess), and only when entitled at 62 or later (§6).
6. `proposed-1` was searched and carries no exercise-3 entries (§1).
7. A registered run also needs a `decisions` entry recording Max's
   ruling on every d188 decision field, which the configuration must
   follow (§21, §22), as exercise 1's registered run does for d074 and
   d075.
8. Under C1 and C2 the spouse's excess counts its months early from the
   exact moved claim month, as the spouse's own factor does (§13; referee
   required change 1), and from the exact month of a moved worker
   entitlement (§13; the review of `e1-draft-5`).
9. The per-cohort survivor span and the two exercise-1 carry-overs this
   draft relies on (the oracle COLA horizon, d074 decision 2(a), and the
   opening-stock basis, d075) are decision fields of their own, which
   d188 as filed does not name (§21, §22; referee required change 7).
10. A converted worker's spouse's excess on its conversion claim keeps
    Track A's baseline count in every scenario, the baseline start moved
    by D (§11, rule 3; the review of `e1-draft-4`). The plan does not
    address it.

## 21. Machine-readable parameter block

Downstream code reads this block: `fra68_track.runner.e1_parameter_block`
(the runner records `specification_check` against it in every run, and a
registered run refuses a mismatch in the schedules, the primary schedule,
each row's schedule, survivor rule, claiming response, statistic,
components, population, benefit period, benefit scale, behavior and
membership basis, the C1 anchor age or the statistic identifier) and
`tests/test_urban2010_fra68_spec.py`. The check does not read
`claiming.spouse_excess_months_early` or
`amounts.conversion_claim_spouse_excess_months_early`; the spec test
holds them to the code's statements of the rules
(`reform.SPOUSE_EXCESS_MONTHS_EARLY_RULE` and
`reform.CONVERSION_CLAIM_EXCESS_MONTHS_EARLY_RULE`) and
`tests/fra68_track` to their arithmetic.
`decisions_awaiting_max` lists the d188 items. A registered run refuses
while it is non-empty, and until a `decisions` entry records Max's ruling
on each decision field (`{field: {"ruling": value, ...}}`, the A1 §21
form) and the configuration follows every ruling.

```json
{
  "specification": "urban2010_fra68_exercise3",
  "version": "e1-draft-6",
  "status": "draft_refereed_not_ratified",
  "template": {
    "specification": "urban2010_cola_exercise1",
    "version": "a1-ratified-1"
  },
  "statistic_id": "dynasim_exercise3_fra68_reference_year_age_profile",
  "target": {
    "model": "DYNASIM3",
    "run": "614",
    "run_date": "2009-04",
    "run_provenance": "inherited_from_a1_not_verified_for_the_fra_bars",
    "trustees_vintage": 2008,
    "baseline": "scheduled_benefits_current_law_tr2008",
    "outcome_year": 2030,
    "age_groups": [[50, 61], [62, 64], [65, 69], [70, 79], [80, null]],
    "disability_included": true,
    "option_locator": "urban-2010-reform-details.txt:64-68"
  },
  "policy": {
    "changed_parameter": "retirement_age_42_usc_416_l",
    "implementation": "oracle_parameter_override_fra_months_by_birth_year",
    "schedule_key": "year_turning_62",
    "baseline_schedule": "statute_416_l_committed_capture",
    "survivor_mapping_rule": "survivor_retirement_age(b) = worker_schedule(b - 2)",
    "survivor_reduction_span": "exact_by_cohort_both_scenarios",
    "unchanged": [
      "early_reduction_rates",
      "early_first_bracket_months",
      "spousal_early_reduction_rates",
      "delayed_credit_rate",
      "credit_end_at_age_70",
      "widow_reduction_28_5_percent_at_60",
      "pia_awi_bend_points_wage_base",
      "cola_path",
      "earnings_test_exempt_amounts"
    ],
    "additive_reading": "considered_not_registered",
    "di_ratio": 1
  },
  "schedules": {
    "P1": {
      "rule": "66 years + 2*(Y-2010) months for Y (year turning 62) 2011-2021; 68 from 2022; unchanged through 2010",
      "months_by_year_turning_62": {
        "2010": 792, "2011": 794, "2012": 796, "2013": 798, "2014": 800,
        "2015": 802, "2016": 804, "2017": 806, "2018": 808, "2019": 810,
        "2020": 812, "2021": 814, "2022": 816
      },
      "months_from_year_turning_62": {"2022": 816}
    },
    "P2": {
      "rule": "66 years + 2*(Y-2009) months from Y = 2010, capped at 68",
      "months_by_year_turning_62": {
        "2010": 794, "2011": 796, "2012": 798, "2013": 800, "2014": 802,
        "2015": 804, "2016": 806, "2017": 808, "2018": 810, "2019": 812,
        "2020": 814, "2021": 816, "2022": 816
      },
      "months_from_year_turning_62": {"2022": 816}
    },
    "P3": {
      "rule": "66 years + round(24*(Y-2009)/13) months for Y (year turning 62) 2010-2021, rounded to the nearest whole month (no ties); 68 from 2022",
      "months_by_year_turning_62": {
        "2010": 794, "2011": 796, "2012": 798, "2013": 799, "2014": 801,
        "2015": 803, "2016": 805, "2017": 807, "2018": 809, "2019": 810,
        "2020": 812, "2021": 814, "2022": 816
      },
      "months_from_year_turning_62": {"2022": 816}
    }
  },
  "primary_schedule": "P3",
  "rate_path": {
    "carried_over_from": "urban2010_cola_exercise1 rate_path.baseline",
    "applies_to": "both_scenarios",
    "reform_changes_increases": false
  },
  "claiming": {
    "C0": "fixed_claim_ages",
    "C1": {
      "transform": "claim_month = min(12a + D, 840); entitlement_year = claim_year + floor((6 + claim_month) / 12) - a",
      "applies_to": "projected_claimants_with_claim_age_at_least_anchor",
      "anchor_age": 65,
      "anchor_source": "claim table 2008 row fra_at.at_age"
    },
    "C2": {
      "transform": "as C1",
      "applies_to": "every_projected_claimant"
    },
    "claim_age": "claim_year_minus_birth_year_at_most_70",
    "spouse_excess_months_early": "max(0, reform_fra(b_s) - max(m_s, 12*(worker_baseline_entitlement_year - b_s) + v_w)); m_s = the spouse's own reform claim month, 12*a_s if not transformed; v_w = the months C1/C2 moved the worker's claim, min(12*a_w + D(b_w), 840) - 12*a_w, 0 if not transformed; a converted worker's conversion claim follows amounts.conversion_claim_spouse_excess_months_early",
    "unchanged_under_c1_c2": [
      "claims_at_or_before_the_opening_year",
      "di_records",
      "conversions",
      "survivor_entitlement"
    ]
  },
  "rows": {
    "F0": {
      "schedule": "P3",
      "survivor_retirement_age": "statutory_416l2_mapping",
      "claiming_response": "c0_fixed_claim_ages",
      "statistic": "ratio_of_scenario_means",
      "membership_basis": "scenario_specific",
      "components": [
        "retired_worker", "disabled_worker", "spouse",
        "aged_widow", "disabled_widow"
      ],
      "benefit_period": "calendar_2030_payments",
      "benefit_scale": "annual_12_times_monthly",
      "behavior": "fixed_paths_shared_draws",
      "population": {
        "wave": 2011, "weight": "ER34155", "born_max": 1980,
        "start_year": 2010, "periods": 20, "family_unit_id": "ER34101"
      }
    },
    "F1": {"schedule": "P1"},
    "F2": {"schedule": "P2"},
    "F3": {
      "claiming_response": "c1_claimants_at_or_after_anchor_delay",
      "behavior": "fixed_paths_shared_draws_stylized_claiming_response"
    },
    "F4": {
      "claiming_response": "c2_all_claimants_delay",
      "behavior": "fixed_paths_shared_draws_stylized_claiming_response"
    },
    "F5": {"statistic": "mean_of_individual_ratios"},
    "F6": {"components": ["retired_worker", "disabled_worker"]},
    "F7": {"survivor_retirement_age": "unchanged_from_baseline"},
    "F8": {
      "population": {
        "wave": 2009, "weight": "ER34046", "born_max": 1980,
        "start_year": 2008, "periods": 22, "family_unit_id": "ER34001"
      }
    }
  },
  "amounts": {
    "pia_dime_floor_after_each_increase": true,
    "claim_age_factor_dime_floor_each_payment_year": true,
    "opening_stock": "observed_opening_year_annual_amount_x_baseline_increases_x_component_age_factor_ratio",
    "opening_stock_factor_ratio_components": ["retired_worker", "spouse"],
    "opening_stock_dime_floor": false,
    "opening_stock_basis": "fixed_at_opening_year",
    "di_conversion": "scenario_fra_attainment_year_label_only",
    "conversion_claim_spouse_excess_months_early": "max(0, reform_fra(b_s) - (max(12*(y_conv_base - b_s), 12*(worker_baseline_entitlement_year - b_s)) + D(b_s))), which equals Track A's baseline count in every scenario and under every claiming response; y_conv_base = Track A's own claim year of the converted worker (its baseline conversion year), worker_baseline_entitlement_year = the worker's entitlement year before any C1/C2 move, D(b_s) = reform_fra(b_s) - baseline_fra(b_s)",
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
      "proposed_default": "track_a_reported_not_gated_psid_oracle",
      "decision_record": "d188",
      "item": "(a)"
    },
    "oracle_fra_schedule_override": {
      "proposed_default": true,
      "scope": "fra_months_by_birth_year_override",
      "decision_record": "d188",
      "item": "(a)"
    },
    "survivor_reduction_span": {
      "proposed_default": "exact_by_cohort_both_scenarios",
      "scope": "survivor_reduction_period_months_override_by_survivor_cohort_in_both_scenarios",
      "named_in_d188_as_filed": false,
      "decision_record": "d188",
      "item": "(a)"
    },
    "oracle_cola_horizon_extension_to_2030": {
      "proposed_default": true,
      "carries_over": "d074 decision 2(a)",
      "named_in_d188_as_filed": false,
      "decision_record": "d188",
      "item": "(a)"
    },
    "opening_stock_basis": {
      "proposed_default": "fixed_at_opening_year",
      "carries_over": "d075 referee question 11",
      "named_in_d188_as_filed": false,
      "decision_record": "d188",
      "item": "(a)"
    },
    "di_benefit_level": {
      "proposed_default": "disclosed_oracle_approximation",
      "decision_record": "d188",
      "item": "(a)"
    },
    "acceptance_rule": {
      "proposed_default": null,
      "decision_record": "d188",
      "item": "(a)"
    },
    "primary_schedule_id": {
      "proposed_default": "P3",
      "decision_record": "d188",
      "item": "(b)"
    },
    "rows": {
      "proposed_default": ["F0", "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8"],
      "decision_record": "d188",
      "item": "(b)"
    },
    "ratification_and_registration": {
      "proposed_default": "ratify_by_merge_post_42_registration_run_one_shot",
      "decision_record": "d188",
      "item": "(c)"
    }
  },
  "labels": [
    "PSID-seeded closed cohort",
    "Python oracle (not Axiom)",
    "fixed-path mechanical incidence"
  ],
  "stylized_response_label": "fixed paths; stylized claiming response (registered sensitivity)",
  "stylized_response_rows": ["F3", "F4"]
}
```

## 22. Decisions awaiting Max (d188, open)

Max's decision record d188 (created 2026-09-23, deadline 2026-09-30)
asks whether to run exercise 3 exactly like Track A. Its default is "yes
to (a)-(c) with P3". Until he rules, each item below is a configuration
field whose default is the plan's recommendation
(`fra68_track.config.PENDING_DECISIONS`), and every run records it as not
ruled (`pending_decisions`).

1. **Claim class** (item (a); plan §11 item 1): Track A class, as A1's
   ruling d074 decision 1; alternatives: hold for Track B or Track C.
2. **Oracle scope** (item (a); plan §11 item 2):
   (a) the reform as an override of the oracle's FRA schedule
   (`oracle_fra_schedule_override`), which adds no statutory rule
   coverage.
   (b) the per-cohort survivor span (`survivor_reduction_span`): the
   widow(er)'s reduction spread over the survivor cohort's exact span in
   both scenarios, also an override that adds no statutory rule coverage.
   The d188 record as filed names only "the oracle FRA-schedule override
   (no new statutory coverage)". The span also changes baseline survivor
   amounts relative to exercise 1 (§11, rule 5), so it is a field of its
   own: a ruling that covers only the filed wording leaves it unruled,
   and a registered run refuses until Max rules on it by name.
   (c) the DI-level approximation carried over from d074 decision 2(b)
   (DI levels are weights only; every DI ratio is 1).
   (d) the other exercise-1 rulings this draft relies on, each its own
   field and neither named in d188 as filed: the oracle COLA path to 2030
   (d074 decision 2(a); `oracle_cola_horizon_extension_to_2030`) and the
   opening-stock basis frozen at the opening year (d075, referee question
   11; `opening_stock_basis`).
   Each of (b) and (d) is runnable only at its proposed default
   (`FRA68Config.check_runnable`).
3. **Acceptance rule** (item (a); plan §11 item 3): none.
4. **Primary schedule and row set** (item (b); plan §11 item 4): P3
   primary with P1 and P2 registered; rows F0-F8. d188 as filed names P3
   and the registered P1 and P2; rows F3-F8 are part of the `rows`
   field's proposed default, and d196 item (4) names rows F0-F8.
5. **Ratification and registration** (item (c); plan §11 items 6-7):
   ratify this specification by merging, post or authorize the #42
   registration, run the one-shot.
6. **Screening or request** (plan §11 item 5; not in d188): whether a
   screening lane may extract definitional text from Urban pages 3-5, or
   the Urban clarification request is sent. d196 item (5) proposes
   neither before the one-shot.

When Max rules, the ratified text moves each item from
`decisions_awaiting_max` to a `decisions` entry with his ruling; the
one-shot entry point refuses a block without a ruling on every decision
field or a configuration that departs from one
(`fra68_track.runner.check_specification_for_registered_run`).

Exercise 1's rulings (d074 and d075) cover the projection, the
benefit-level and auxiliary conventions and the opening-stock basis for
exercise 1 only; whether they carry over is part of item (a), and each
carry-over this draft relies on is a field of §21 (item 2). The Track A
builder defaults stay builder defaults, listed in every run.

A follow-up decision, d196 (created 2026-09-24, open, deadline
2026-09-30), is filed as a supplement to d188 "to rule on together with
d188". Its default, "accept all five", covers the per-cohort survivor
span (item 2(b) above), the two exercise-1 carry-overs (item 2(d)), rows
F0-F8 as §18 lists them (item 4) and no screening lane or clarification
request before the one-shot (item 6). The block still names d188 as each
field's decision record. A registered run needs a recorded ruling on
every field under `decisions`, whichever record carries it
(`check_specification_for_registered_run` keys rulings by field name).
This draft changes neither decision record.

## 23. Questions for the referee

The referee's answers are in §25.

1. P3 versus P1 as the primary schedule.
2. The survivor mapping (F0) versus no change for survivors (F7).
3. The C1 anchor: the table's at-FRA age 65, or the cohort's own FRA age.
4. Whether to register a DI-window reprojection row.
5. Whether a baseline claim-age mix that follows each cohort's FRA should
   replace Track A's 2008 snap (a new baseline projection).
6. For C1 and C2: ratio of scenario means versus ratio of totals over the
   union (reported as a diagnostic).
7. Whether the survivor reduction span, exact by cohort in both
   scenarios, is acceptable as a departure from exercise 1's fixed 84
   months.
8. Whether an opening-stock spouse record should take the spouse's factor
   ratio on its whole observed amount (§6), or ratio 1.

## 24. What this draft did not verify

- Whether page 3's source line (run 614) covers the FRA bars; run 614's
  phase-in schedule, survivor and DI treatment, claiming response, and
  whether its reported benefits are net of the earnings test.
- The age groups (inherited from A1 and `proposed-1`).
- PSID sample sizes in any cell; no PSID value was read and no statistic
  was computed on real data.
- Whether a rerun reproduces exercise 1's projection bit for bit in the
  current environment (a registered run records it).
- A4's last fitted DI incidence age (the runner records A4's incidence at
  start ages 65-67 with the DI-window diagnostic).
- 402(a) (conversion of a disabled worker's benefit) and 402(k): not
  read; the conversion rule is A4's and the dual-entitlement rules are
  the oracle's.
- The month of each projected death (the records carry the year only),
  which a count of the credits of §12's unclaimed decedents would need.
- Whether Max's ruling on d188 will cover the survivor span and the two
  exercise-1 carry-overs, which the record as filed does not name (§22;
  d196 names them).
- How DYNASIM dates a converted disabled worker's spouse's benefit (not
  read). The model keeps Track A's whole-year conversion count in both
  scenarios (§11, rule 3; §12).

## 25. Referee pass

**The report.** `EVID/fra68-referee-20260924.md`, SHA-256
`943af2a3b8f2ebc3a3ae7b8fcf10c43641211bbfa5f9317cf580d2eff27edec3`: an
independent Claude lane (Opus 5.5) on the model-builder side refereed
`e1-draft-3` at commit `454a89c1` on 2026-09-24 (plan §10, E1). It
reproduced every §3, §5 and §6 table and all §19 worked cases with exact
fractions in a script that imports nothing from the repository, verified
the 83 quoted statute lines and the §21 block against the code, and found
no comparator dependence in the content or the timing.

**Verdict:** not ratifiable as written; ratifiable after required changes
1-8. None of them changes a schedule, the proposed primary, the rows
F0-F8 or a §19 worked-case value.

**Answers to §23**, each adopted by this draft:

1. Keep P3 as the proposed primary, with P1 as F1 and P2 as F2 (Table
   1's phrasing; optional suggestion 1 adds it to §3).
2. Keep the 416(l)(2) survivor mapping as F0 and F7 as the registered
   alternative (416(l)(1)-(2), 402(q)(9)(B)(ii) and the 403(f)(9)
   contrast).
3. Keep the C1 anchor at 65 (optional suggestion 2 adds the reason to
   §13).
4. Register no DI-window reprojection; keep the diagnostic.
5. No baseline claim-age mix that follows each cohort's FRA in this
   exercise; keep it as a named delta.
6. Keep the ratio of scenario means for F3 and F4, with the ratio of
   union totals as a diagnostic (required change 5 writes the formula
   out).
7. Accept the exact survivor span in both scenarios.
8. Keep the spouse's ratio on an opening-stock spouse record's whole
   amount (it overstates the cut on the own-benefit part by at most 0.08
   points).

**Required changes.** The lane that wrote `e1-draft-4` checked each
against its cited source before applying it.

| Change | Checked against | Applied |
|---|---|---|
| 1. Spouse's excess under C1/C2 counted from the exact moved claim month | The code: `ScenarioCalculator` inherited Track A's `_spouse_excess`, whose months early are `fra_months(b_s) - 12 (start year - b_s)`, while `_claim_response` gives the worker's factor the month `min(12a + D, 840)`; the referee's two cases recomputed (0.720833 and 0.695833 under the old count) | §13, §19 (two cases), §21 `claiming.spouse_excess_months_early`, §20 item 8. Code: `reform.spouse_excess_months_early`, `benefits.MovedClaimRecord` and `ScenarioCalculator._spouse_excess`, a documented copy of Track A's with only the months-early count changed; Track A's calculator is unchanged. Tests: both §19 cases, the null identity with Track A's count, a calculator-level check on invented data and the null-reform identity under every claiming response |
| 2. Name the credits of a worker who died unclaimed | 402(e)(2)(C) and 402(f)(2)(C), `usc42_402.txt` lines 208 and 258; Track A's `deceased_unentitled` record (factor 1.0) | §6, §12 (new row), §13, §16. Named, not modeled: the records carry an annual death year only, so counting increment months through the month before death needs a death-month convention, and doing it in both scenarios would change exercise 1's baseline survivor amounts, a choice for Max rather than the builder. Code adds a diagnostic count (§12) that changes no amount |
| 3. State 403(f)(9) exactly | `usc42_403.txt` line 170 | §12, earnings-test row |
| 4. Statute edition and amendment history | The saved pages' edition selector ("prelim"); the amendment notes of `usc42_402.txt`, `usc42_403.txt`, `usc42_416.txt` and `usc42_423.txt` | §2 statute row, §20 `law_cutoff_and_historical_versions`, and §3 item 2 cites 402(q)(9)(B)(ii) at line 419 |
| 5. Write out the scenario-specific statistic | A7's `_membership_masks` (`scenario_specific`: S_base, S_reform, S_alt = both with B_base > 0) and `_cell_values` | §7, in `text` fences |
| 6. A1's two remaining amount rules | A1 §21 `amounts` | §21 `amounts` |
| 7. Every choice awaiting Max, including what d188 as filed does not name | The d188 record (`decisions.jsonl`, status `open`), whose item (a) names the claim class, "the oracle FRA-schedule override (no new statutory coverage)", the DI-level approximation and no threshold; A1 §21-22 and `cola_track_a.config.MAX_RULINGS` for d074 decision 2(a) and d075 | §6, §21, §22. **Applied with one change:** the survivor span is its own field, `survivor_reduction_span`, not a `scope` entry of `oracle_fra_schedule_override`, so a ruling on the override as filed cannot be read as covering it and a registered run refuses until Max rules on it by name. Code: `PENDING_DECISIONS` and `FRA68Config` gain `survivor_reduction_span`, `oracle_cola_horizon_extension_to_2030` and `opening_stock_basis`, each flagged `named_in_d188_as_filed` false and runnable only at its default; the survivor span leaves `builder_defaults`; the two carry-overs pass to the Track A configuration; the spec test and the runner tests follow |
| 8. Builder boundary | `EVID/RESTRICTED-FILES.md` (Urban pages 3-4 restricted) | Header |

**Optional suggestions.**

| Suggestion | Decision |
|---|---|
| 1. §3, Table 1 phrasing for P3 | Applied, as the referee's reading; lines 62, 66, 73, 80-81 and 86 of the Urban text checked |
| 2. §13, the C1 anchor's rationale | Applied; the 2008 claim-table shares checked (66, 67-69 and 70+: 1.7 + 1.4 + 0.7 male, 1.6 + 1.9 + 2.4 female) |
| 3. §12, TR2008 and primer citations | Applied: TR2008 pp. 111-112 and 118-119, primer pp. 14 and 16, each quotation checked. Not applied: the note that the hazard's "benefit amount" input is itself a function of the FRA, which is a statement about DYNASIM's mechanism that nothing read here shows |
| 4. §12, 402(q)(3)(C) on the spouse's excess of a DI beneficiary | Applied; `usc42_402.txt` lines 383-385 checked |
| 5. §1, Figure 1's basis | Applied, marked as an inference |
| 6. §21 `target.run_date` | Applied (A1's value, inherited provisionally as the run is) |
| 7. §21 preamble or the check | Both: `specification_code_check` now binds each row's benefit period, benefit scale and behavior and the membership basis, and the preamble lists what it binds |
| 8. §18, F7's value | Applied; checked against `Scenario.survivor_schedule` and `ScenarioCalculator._widow_excess` |
| 9. §5, the spread between schedules | Applied; recomputed through the code (1.19-1.28 points by cohort, 1951-1959; 0 for 1960) |
| 10. §12, question numbers in the claim-age-mix row | Applied |
| 11. §20 item 2 | Applied, stated for claim year minus birth year at most 70 |
| 12. Add 402(q)(9)(B)(ii) to the excerpt file | Declined: it would change an evidence file whose SHA-256 (`2c7605ee…`) E1 and the folder's `SHA256SUMS` record. This draft cites line 419 of `usc42_402.txt`, which `SHA256SUMS` already covers (§2, §3) |

**Left open by the referee and not done here.** The d188 card's
amendment or a follow-up decision naming the survivor span and the two
carry-overs (§22), and a decision record for §22 item 6 (screening or
request). Both are for whoever keeps Max's decision queue. The
orchestrating session has since filed d196 (§22), which covers both; it
is open.

**What the referee could not verify** (its report, "What I could not
verify") stands: run 614's phase-in, survivor, DI and claiming treatment
and whether its benefits are net of the earnings test; the age groups
against the figure; the drafting lane's process beyond content and
timing; the statute pages' fetch URL and date; and the code after
`454a89c1`, which this revision changed (§26).

**Independent review of `e1-draft-4`.**
`EVID/fra68-conversion-claim-20260924/review-e1-draft-4-20260924.json`
(SHA-256 `c6da180f…`): an independent Claude lane (Opus 5.5) reviewed
the branch at `070c59c7` on 2026-09-24 and did not approve it, for one
confirmed defect of the same kind as required change 1. It found
required changes 1-8 applied or soundly declined, the §3 and §5
arithmetic and the source citations correct, and the dry run
reproducible. Its probes used the invented cohort only.

| Finding | Checked against | Applied |
|---|---|---|
| 1. A converted worker's claim for the spouse's excess was counted from the scenario's whole conversion year (`_own_claim_year`, `own_claim_month`), so its months early were the leftover month, FRA mod 12, which the FRA increase changes. On invented data the reform moved converted spouses' excesses by -0.69 to -2.78 percent, and by +2.86 percent for a spouse born 1956 under P2, against the per-person ordering P2 <= P3 <= P1 <= baseline that the tests assert. 402(q)(1) reduces neither scenario's excess | The code at `070c59c7` (`ScenarioCalculator._own_claim_year` and `own_claim_month`), Track A's `_own_claim_year`, A4's `fra_attainment_year` and `apply_claiming`; `usc42_402.txt` lines 371 and 406; the exact-integer grid of `conversion_claim_arithmetic.py`, which also finds classes the review did not list (1948 and 1949 under P2, 1950 under P1) | The review's option (b): each reform keeps Track A's baseline count, the baseline start moved by D (§11 rule 3; §3 item 6, §6, §13, §19, §20 item 10, §21 `amounts.conversion_claim_spouse_excess_months_early`). **Applied with one extension.** Moving the conversion claim alone (12 (y_c - b) + D, the review's formula) would still cut the excess by 2 or 4 months where the worker's entitlement in the year after the baseline conversion starts the baseline excess (spouses born 1955-1956), so the whole baseline start moves by D; and the start reads the worker's baseline entitlement year, so a C1/C2 move of the worker's claim does not change the count either. Where the conversion starts the excess under C0 the two rules are identical. Track A's baseline whole-year count is a named delta with counters in both scenarios (§12). Option (a) (count from the exact conversion month, which changes exercise 1's baseline) and option (c) (name the defect only) were not taken. Code: `reform.conversion_claim_excess_months_early`, `ScenarioCalculator.conversion_claim_year` and `excess_months_early`, and the two counters; Track A is unchanged. Tests: every cohort 1938-1971 under P1-P3 against 16 worker-entitlement years; the 1956-under-P2 case; each affected cohort class (1948, 1949, 1950, 1954-1956) through the calculator, with the ordering; the later-worker case; a worker's claim moved by C2; a claim before the conversion; the null-reform identity against Track A's own calculator; the counters |
| 2. The dry-run text called the credits counter an upper bound on the survivors the statute would pass credits to, but it counts paid excesses only | `ScenarioCalculator._count_credits_not_inherited` | The dry-run script, the counter's docstring and §12 now say what it counts, and that it is not a bound either way |
| 3. §2 recorded `RESTRICTED-FILES.md` with a SHA-256 that the list no longer matches and that the review could not verify for any version (the list is a living file) | The file's header and changelog | §2 pins no hash and names the version read by its last changelog entry; the header summary follows that version |

The review also noted that d188 as filed does not name rows F3-F8
(d196 item (4) now does, §22) and that the branch's upstream is set to
`origin/master` (not a matter for this draft; the branch is not pushed).

**Independent review of `e1-draft-5`.** An independent Claude lane
(Opus 5.5) reviewed the branch at `b4d8732e` on 2026-09-24; its report is
`EVID/subfleet-briefs-20260924/ex3-review-report.md` and its scripts and
outputs are in `EVID/fra68-review2-b4d8732e-20260924/` (§2). With exact
integers and importing nothing from the repository, it confirmed the §3
table, the §5 spread, the §19 conversion and C2 cases, and that the
`e1-draft-5` conversion-claim rule equals Track A's baseline count for
every cohort 1938-1971 under P1, P2 and P3, including the later-worker
case (moving the conversion claim alone would count 2 months for spouses
born 1955 and 4 for 1956 under every schedule). It reproduced the dry run
byte for byte. It found one defect of the kind of required change 1:

| Finding | Checked against | Applied |
|---|---|---|
| 1. Under C1 and C2 a worker's moved claim entered the spouse's count as the whole reform year it falls in (`excess_months_early` passed the moved record's `entitlement_year`), so when the worker's entitlement starts the excess the reform changed the spouse's months early by D(b_s) - 12 x (the worker's year shift) instead of D(b_s) - v_w, the months the worker's claim moved. On invented data under P3 and C1, a spouse born 1953 whose worker born 1951 moved 7 months was counted 35 months early against the baseline's 36 (a 0.93 percent rise in the excess where the worker's delay gives a 2.22 percent cut at 40 months); the exact-integer grid (spouses born 1946-1966 claiming at 62-64, workers born 1944-1966 claiming at 65-69 in a later year up to 2030, under P1, P2 and P3, C1) finds 969 cases where the two counts differ, 95 of them rises above the baseline where the exact count cuts or holds | `ScenarioCalculator.excess_months_early` and `_claim_response` at `b4d8732e`; `reform.spouse_excess_months_early`; 402(b)(1), 402(q)(5)(C) and (6)(A)(ii) (`usc42_402.txt` lines 58, 399 and 404); the calculator probe on invented data (§2) | The worker's moved entitlement enters at its exact month, its baseline year plus the months moved (§13, §19 new case, §20 item 8, §21 `claiming.spouse_excess_months_early`). Code: `MovedClaimRecord.claim_move_months`, `ScenarioCalculator.worker_entitlement_start`, and `reform.spouse_excess_months_early(worker_claim_move_months=...)`; the whole reform year still gates the excess, and a conversion claim's count is unchanged (§11 rule 3). Rows F3 and F4 only: nothing moves under C0, so no baseline and no C0 row changes. Tests: a grid over schedules, cohorts and claim ages against calendar-month arithmetic; the three probe cases through the calculator, with the whole-year count they replace; a moved record without its move is refused; the new §19 case |

## 26. Changelog

- `e1-draft-1` (2026-09-24): first draft, from the plan's §7 and the A1
  template, with the invented worked cases recomputed through the code.
- `e1-draft-2` (2026-09-24, before any referee pass): a registered run
  also requires Max's recorded ruling on every d188 decision field
  (header, §20 item 7, §21, §22); §13 states when the C1/C2 factor is
  unchanged (12a + D <= 840) and that a claim at 70 keeps its age. No
  schedule, row, rule or parameter changed.
- `e1-draft-3` (2026-09-24, independent build review, before any referee
  pass): §1 corrects the `proposed-1` search result (one "full
  retirement" match on line 45, a general convention, not an exercise-3
  entry); §21 notes that the specification check now also binds the C1
  anchor age (`claiming.C1.anchor_age`) to the configuration. No
  schedule, row, rule or parameter changed.
- `e1-draft-4` (2026-09-24, after the referee pass, §25): required changes
  1-8 and optional suggestions 1-11. One rule changed: under C1 and C2
  the spouse's excess counts months early from the exact moved claim
  month (§13, §19, §21; rows F3 and F4 only). Three decision fields
  added (`survivor_reduction_span`, `oracle_cola_horizon_extension_to_2030`,
  `opening_stock_basis`), each at the value the draft already used. The
  credits of workers who died unclaimed are a named delta with a
  diagnostic count (§12). The block gains `target.run_date`, two A1
  amount rules and `claiming.spouse_excess_months_early`, and its status
  is `draft_refereed_not_ratified`; the specification check binds every
  row entry. No schedule, row, primary or worked-case dollar amount
  changed.
- `e1-draft-5` (2026-09-24, after the independent review of `e1-draft-4`,
  §25). One rule changed: a converted worker's spouse's excess on its
  conversion claim keeps Track A's baseline count in every scenario, the
  baseline start moved by D (§11 rule 3; §3 item 6, §6, §13, §19, §20
  item 10; §21 gains `amounts.conversion_claim_spouse_excess_months_early`
  and `claiming.spouse_excess_months_early` points to it). Reform amounts
  of converted spouses in the cohorts the old count moved (born 1948-1950
  and 1954-1956, by schedule; §25) change in every row except F6 (workers
  only); no baseline amount changes. Track A's whole-year conversion count is a
  named delta with two counters (§12, §16). The credits counter is
  described by what it counts, not as a bound (§12). §2 pins no hash for
  the living restriction list and adds the review record, the arithmetic
  check and d196; the header, §22, §24 and §25 note d196. No schedule,
  row, primary, decision field or §19 dollar amount changed; §19 gains
  one invented case.
- `e1-draft-6` (2026-09-24, after the independent review of `e1-draft-5`,
  §25). One rule changed: under C1 and C2 a worker's moved claim enters
  the spouse's months-early count at its exact month (the baseline
  entitlement year plus the months moved), as the spouse's own moved
  claim already did (§11 rule 2, §13, §20 item 8, §21
  `claiming.spouse_excess_months_early`). Reform amounts of spouses whose
  excess a moved worker entitlement starts change in rows F3 and F4 only;
  no baseline and no C0 row changes. §19 gains one invented case; §2 adds
  the statute lines and the review's scripts; the header records the
  lane. No schedule, row, primary, decision field or §19 dollar amount
  changed.
