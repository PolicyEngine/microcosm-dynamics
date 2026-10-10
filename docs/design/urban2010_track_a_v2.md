# Urban 2010 Track A v2: specification for the joint post hoc rerun of exercises 1 and 3

- **Status:** ratified. Version `a2-ratified-1`, ratified 2026-09-28 by Max's explicit ruling d513 (in chat) on items 5, 7, 8, 9 and this version (§16), and by the merge of PR #480. The text is revision 2 (`a2-draft-3`), unchanged except this line and §16's record of the ruling; Appendix A preserves the original review map and Appendix C the round-diff check.
- **Destination:** `docs/design/urban2010_track_a_v2.md`. On ratification the version becomes `a2-ratified-1`. Any later change is a new version.
- **Execution status:** this document is not a registration. No real-data computation was performed. Source inspection and in-memory invented-arithmetic checks were completed; implementation tests remain prerequisites. No files were written and no commit was created.
- **Authority:** Max’s ruling d479 of 2026-09-27, as the phase-2 brief records it:
  - (1) Post hoc v2 reruns are allowed. They are labelled post hoc, reported beside v1 and never replace it, under the no-tuning rules of the phase-2 plan §3(a), `P:76`.
  - (4) Track A v2 uses the statutory DI computation already in `ss/statutory_aime.py`, justified by fidelity to the statute rather than gap closure. Exercises 1 and 3 rerun together. DI/spouse dual entitlement is a separate mechanism.
- **Inherits:** A1 `a1-ratified-1` and E1 `e1-ratified-2` stay authoritative except where this document changes them. §15 lists the changes.
- **Citations:**
  - Repository code and design citations are repository-relative `path:line` references pinned to commit **`9cee2423f048683e15838aa5fee330afd072f85f`**, abbreviated `9cee2423`.
  - `A1` abbreviates `docs/design/urban2010_cola_comparison.md`; `E1` abbreviates `docs/design/urban2010_fra68_comparison.md`. Neither file changes between `2f75012e` and `9cee2423`. `A7` is `src/populace_dynamics/estimates/cola_age_profile.py`.
  - `EV` = the orchestrating session's evidence folder (`dynasim-parity-20260909`, outside this repository).
  - `T` = `EV/track-a-oneshot-20260923/COMPARISON.md`, exercise 1’s public result memo.
  - `F` = `EV/fra68-oneshot-reg15-20260925/COMPARISON.md`, exercise 3’s public result memo.
  - `P` = `EV/parity-phase2-plan-20260927.md`.
  - SSA’s Program Operations Manual System, POMS, is cited by section and displayed transmittal. Both cited pages were checked again for this revision.

Ratification decisions remain open at §16 items **5, 7, 8, 9 and 12**. In particular, S’s fixed application changes some reform amounts that E1’s conversion convention treated differently, and unsupported D histories can refuse the entire joint attempt. The proposed structural pre-count requires Max’s explicit authorization and its own frozen protocol.

## 1. Scope

One projection ensemble, four benefit mechanisms and 68 tabulations:

- **L, legacy:** v1’s benefit calculators, unchanged.
- **D, primary:** statutory DI computation years (§4).
- **S:** DI/spouse dual entitlement (§5).
- **DS:** D and S together.

Each mechanism is tabulated for exercise 1’s R0–R5, exercise 3’s F0–F7 and three union rows U0–U2 (§8). The headlines are **D×R0 and D×F0**.

## 2. Labels

Every v2 artifact, table, forecast, memo and dashboard entry carries **“registered, one-shot, post hoc, not blind”**, together with *PSID-seeded closed cohort* and *Python oracle (not Axiom)*.

Row labels are identical under every mechanism:

- **R0–R5, F0–F2, F5–F7 and U0**, fixed claim ages C0: *fixed-path mechanical incidence*.
- **F3, F4, U1 and U2**, C1 and C2: **“fixed paths; stylized claiming response (registered sensitivity)”**. E1:49–52 requires this label for F3 and F4; this delta also applies it to their union counterparts.

v2 is reported beside v1 and never replaces a v1 scorecard row. R6 and F8 remain historical v1 rows, marked **“not rerun: requires a second population”**. Their 2009-wave population would break this registration’s one-projection scope.

## 3. One projection and the benefit-only boundary

### 3.1 Population and draws

- **Population:** PSID 2011 wave, positive ER34155 weights, births through 1980, opening year 2010, reference year 2030, and age groups 50–61, 62–64, 65–69, 70–79 and 80+ (A1 §§9, 14).
- **Draws:** K = 20, root entropy 5200 + k for k = 0…19 (`src/populace_dynamics/engine/rng.py:16`; A1 §16).
- **Sampling floor:** family-unit half-split seeds 0–4, fraction 0.5, on opening-wave family unit ER34101, retaining A1 §16’s undefined-half rules.
- **Inputs and transitions:** Track A’s committed inputs and transition rules, unchanged.

### 3.2 The joint runner

The new joint runner creates the twenty projections once and supplies them to both exercises and all four mechanisms.

- It projects each draw with unchanged `cola_track_a.runner._project_population` (`src/populace_dynamics/cola_track_a/runner.py:893`).
- It builds the claiming schedule and `fra_schedule_from_parameters` from the baseline bundle, as both v1 runners do (`src/populace_dynamics/cola_track_a/runner.py:1019–1022`; `src/populace_dynamics/fra68_track/runner.py:904–907`), using A4’s assumed birth month 7 (`src/populace_dynamics/fra68_track/runner.py:903`).
- §5.2’s application function reads the same baseline bundle and birth month. Its conversion integrity check therefore follows the engine’s rule.

The v1 runners each project separately:

- `src/populace_dynamics/cola_track_a/runner.py:1029`, followed by benefits at `:1047`;
- `src/populace_dynamics/fra68_track/runner.py:915`, followed by benefits at `:945`.

`projection_identity_record` compares draw diagnostics with exercise 1’s committed artifact and never refuses (`src/populace_dynamics/fra68_track/runner.py:340–392`). It does not enforce person-state identity.

v2 therefore checks identity directly:

- For each draw, hash the canonical serialization of every slice of `ProjectionResult` (`src/populace_dynamics/engine/loop.py:142–152`, `:218`, `:357`, `:370`), once before benefit computation and again after every mechanism’s inputs to tabulation have been built.
- Any difference refuses the joint attempt (§10).
- Also record `projection_identity_record` against exercise 1’s artifact, as v1 did; that diagnostic remains recorded rather than refused.

### 3.3 What stays fixed

The mechanisms change benefit calculations only. The caller trace establishes this boundary:

- `approximate_pia` is called by `_Calculator._level` for both `"di"` and `"death_before_eligibility"` (`src/populace_dynamics/cola_track_a/benefits.py:261–299`, call at `:287`).
- DI reaches it through `worker_record` → `_di_record` → `_level` (`:302`, `:320–330`, `:360–365`). A deceased worker’s existing DI record can supply a linked auxiliary (`:378–387`).
- Exercise 3 inherits that calculator (`src/populace_dynamics/fra68_track/benefits.py:297`).
- Both exercises project before computing benefits (§3.2).
- Track M also calls `approximate_pia` for its legacy alternative (`src/populace_dynamics/min_benefit_track_m/rules.py:647`).

Fixed across mechanisms:

- person-year rosters, weights and deaths;
- earnings histories: benefits read 1968–2010 careers only, with no post-2010 earnings drawn (`src/populace_dynamics/cola_track_a/adapters.py:25–27`);
- spouse links, marital states, DI awards and recoveries.

**Baseline projected conversion events and claims remain fixed. Exercise 3 continues to determine disabled-versus-converted benefit labels using each scenario’s FRA, and C1/C2 retain their registered benefit-stage claim transformations.** Relabelling occurs at `src/populace_dynamics/fra68_track/benefits.py:356–366` and `:432–442`; claim transformations at `:368–411`.

### 3.4 What may change

Changed benefits can change positive-benefit membership, component shares and dollar weights. Their construction rules are frozen; their realized values are not. Recipients are not forced to remain identical across mechanisms. §9 determines which baseline/reform membership differences are allowed.

### 3.5 Exercise-specific conventions stay

A shared projection does not make the exercises’ baselines identical. Each retains its conventions. E1’s survivor reduction span is exact by cohort, whereas A1 uses the oracle’s fixed 84 months (E1:649–655, :1363–1368, :670).

## 4. Mechanism D: statutory DI computation years

### 4.1 Justification and statute text

Track A’s `approximate_pia` uses the highest 35 indexed years, counting missing years as zero. Its docstring says it “is not the statutory DI or pre-eligibility-death computation: the divisor is always 35 years (no elapsed or dropout years), so it understates short careers” (`src/populace_dynamics/cola_track_a/benefits.py:182–184`).

D replaces that calculation **for DI-derived PIAs** with `ss.statutory_aime.aime(..., disability_year=...)`. The justification is fidelity to 42 USC 415(b)(2), independent of comparator fit, under d479 (4).

The code quotes 415(b)(2)(A) (`src/populace_dynamics/ss/statutory_aime.py:37–44`):

> The number of an individual's benefit computation years equals the number of elapsed years reduced— (i) in the case of an individual who is entitled to old-age insurance benefits (except as provided in the second sentence of this subparagraph), or who has died, by 5 years, and (ii) in the case of an individual who is entitled to disability insurance benefits, by the number of years equal to one-fifth of such individual's elapsed years (disregarding any resulting fractional part of a year), but not by more than 5 years.

It also quotes (`:48–49`):

> The number of an individual's benefit computation years as determined under this subparagraph shall in no case be less than 2.

And 415(b)(2)(B)(iii) (`:60–66`):

> the term "number of elapsed years" means (except as otherwise provided by section 104(j)(2) of the Social Security Amendments of 1972) the number of calendar years after 1950 (or, if later, the year in which the individual attained age 21) and before the year in which the individual died, or, if it occurred earlier (but after 1960), the year in which he attained age 62; except that such term excludes any calendar year any part of which is included in a period of disability.

**Source:** uscode.house.gov release point 119-100, expression date 2026-06-26, text SHA-256:

`5b41d1cdacd39f4c49da7cf41dbbf22e1ea29b125be7105ca2daa12292e06eae`

The source metadata appears at `src/populace_dynamics/ss/statutory_aime.py:17–25`. The copy at:

`EV/parallel-oasdi-20260920/encoder-recovery/unsigned-415-b-reviewed-runtime-r4/candidate/_eval_workspaces/codex-gpt-5.6-terra/us-statute-42-415-b/workspace/source.txt`

was rehashed for this revision and matches. **With whitespace and typographic quotation marks normalized**, it contains all three passages verbatim. The code’s pointer names only the `encoder-recovery/` tree (`:21–23`); the registration pins this full path.

### 4.2 The computation

**D corrects the ordinary statutory DI computation-year count within Track A’s retained approximations. It does not implement a complete statutory DI determination. The elapsed-year window and retained earnings cutoff are distinct rules.**

For birth year b and disability-year argument d:

- **Elapsed years:**  
  E = max(0, min(b+62, d) − max(1950, b+21) − 1)  
  (`src/populace_dynamics/ss/statutory_aime.py:247–273`).
- **Computation years:**  
  N = max(2, E − min(5, ⌊E/5⌋)) (`:276–303`).
- **Indexing year:** min(b+62, d) − 2 (`:306–328`).
- **AIME:** cap each year at its wage base, index to the indexing year with later years nominal, select the highest N values with zero padding, and floor their sum divided by 12N (`:331–365`).

D does not divide the highest-35 sum by a shorter denominator. PIA is `ss.benefits.pia(AIME, e, params)` at the record’s eligibility year e (`src/populace_dynamics/ss/benefits.py:120–131`).

The disability-year argument is **d = e**:

- **Projected award:** e = min(award year, b+62) (`src/populace_dynamics/cola_track_a/benefits.py:329`).
- **Opening disabled worker:** e is the opening clock year (`:317`; §4.4). With an `OpeningStockRecord`, that year is at most b+62 (`src/populace_dynamics/cola_track_a/opening.py:338–345`). Without one, e is the cohort start year, which exceeds b+62 for an opening entitled worker born before 1948.

The helper itself uses min(b+62, d) for E and indexing. Clamping d at b+62 therefore changes neither quantity. It does not make a raw award cutoff interchangeable with the retained eligibility cutoff (§12.10).

### 4.3 Retained Track A inputs and implementation constraint

**Implement D through a new DI-specific calculation branch/version. Preserve `approximate_pia` for legacy and non-DI callers. Preserve Track A’s existing cutoff, indexing, bend-point and rounding inputs. Separate caches by computation convention and every input that can change the cached value.**

- **Cutoff:** pass history through e, **including e**. This preserves `approximate_pia`’s `computation_end_year` rule as `_level` calls it (`src/populace_dynamics/cola_track_a/benefits.py:192–196`, `:287–293`). The statutory helper leaves the cutoff to its caller (`src/populace_dynamics/ss/statutory_aime.py:132–135`, `:383–384`).
- **Indexing:** Track A indexes to min(b+60, e−2) through indexing birth year min(b, e−62) (`src/populace_dynamics/cola_track_a/benefits.py:197–200`; `src/populace_dynamics/ss/benefits.py:87`). The helper indexes to min(b+62, e)−2. These are identical, including the start-year fallback with e > b+62. For those opening fallback records E = 40 and N = 35, so D equals L.
- **Bend points and rounding:** use e’s bend points, dollar-floor AIME and dime-floor PIA (`src/populace_dynamics/ss/benefits.py:120–131`), retaining the existing increase and payment paths.
- **Eligibility floor and level policy:** retain the pre-1979 oracle eligibility floor (`src/populace_dynamics/cola_track_a/benefits.py:117–118`, `:268–270`) and `LevelPolicy` semantics (`src/populace_dynamics/cola_track_a/config.py:78–95`, `:279`).
- **Implementation:** new v2 subclasses of `_Calculator` for exercise 1 and `ScenarioCalculator` for exercise 3 override `_level` for tag `"di"` only. v1 dispatches on the tag and `LevelPolicy.EXCLUDE` (`src/populace_dynamics/cola_track_a/benefits.py:268–293`); introducing a policy value alone would still reach `approximate_pia`. Record the mechanism in v2 configuration; do not edit `cola_track_a/config.py`.
- **Global convention:** `TRACK_A_COMPUTATION_YEARS` stays `LEGACY_FIXED_35` for retirement (`src/populace_dynamics/cola_track_a/benefits.py:117–123`, `:277–285`).
  - The legacy pin test freezes modules naming `LEGACY_FIXED_35` (`tests/ss/test_statutory_aime.py:393–405`, `:417`).
  - Add the new module to that set and, if it directly calls `benefits.aime`, to `LEGACY_BENEFITS_AIME_CALLERS`. The test file is not a v1 module.
- **Do not import Track M’s wrapper:** its statutory `history_pia` clips through onset−1 (`src/populace_dynamics/min_benefit_track_m/rules.py:501–514`, specifically `:513`; call at `:630–660`). Importing it would add a second mechanism change.
- **Caches:**
  - v1 uses `(person_id, tag, year)` (`src/populace_dynamics/cola_track_a/benefits.py:274`).
  - One cache per wave is shared across draws (`src/populace_dynamics/cola_track_a/runner.py:1043`) and, in exercise 3, scenarios (`src/populace_dynamics/fra68_track/runner.py:929`, `:942`).
  - v2 adds computation convention, `legacy_fixed_35` or `statutory_415_b_2`, and a fingerprint of PIA-relevant parameters: AWI, wage bases, bend points and PIA factors. Birth years and histories remain fixed within the frozen cohort. D values cannot be served to L or S, or the reverse.

### 4.4 Which PIAs D changes

A DI level is requested through `_di_record` (`src/populace_dynamics/cola_track_a/benefits.py:360–376`). D changes these PIAs:

1. **Own DI records:** projected awards, active or converted (`:320–330`), and opening disabled workers routed through `worker_record`’s first branch (`:312–319`). Exercise 3’s relabelling preserves the level (`src/populace_dynamics/fra68_track/benefits.py:437–442`).
2. **A linked worker’s DI record** supporting spouse excess (`src/populace_dynamics/cola_track_a/benefits.py:619–626`).
3. **A deceased worker’s DI record** inherited from the last state before death and supporting widow(er) benefits (`:384–387`, `:694–697`).

D leaves these **level computations or observed payments** unchanged:

- ordinary retirement levels (`:277–285`, `:333–358`);
- standalone pre-eligibility-death levels (`:404–420`);
- intact opening observed payments (`:820–836`; A1 §11 rule 4), including an opening disabled worker’s own observed payment.

An opening disabled worker’s PIA used by a linked spouse or survivor can still change. Likewise, an unchanged ordinary worker or death level does not imply an unchanged auxiliary payment: the auxiliary’s own DI-derived offset may change (§12.4).

Opening observed-payment bases retain inherited treatment. No insured-status filter is added; the engine does not consult insured status (`src/populace_dynamics/engine/di_entitlement.py:13–18`).

**Disability-year proxies retained:**

- The engine records modeled award year, rather than statutory onset; entitlement can precede that year (`src/populace_dynamics/engine/di_entitlement.py:53–58`).
- Track A clamps projected eligibility at age 62 (`src/populace_dynamics/cola_track_a/benefits.py:329`).
- An opening disabled worker uses A3 receipt start, capped at the age-62 clock, from the opening record (`src/populace_dynamics/cola_track_a/opening.py:338–345`).
- Without an opening record, use cohort start year (`src/populace_dynamics/cola_track_a/benefits.py:317`).

Count and disclose DI levels by proxy rule:

`d_proxy_award_year`, `d_proxy_age_62_clamp`, `d_proxy_a3_receipt_start`, `d_proxy_opening_age_62`, `d_proxy_start_year_fallback`.

**Zero and small histories:**

- No positive indexed earnings through the cutoff gives AIME 0 under both conventions; zero padding cannot supply missing earnings (`src/populace_dynamics/ss/statutory_aime.py:363–365`).
- Positive indexed earnings with a top-35 sum below $420 give legacy AIME 0 (also E1:669). D becomes positive when its top-N sum reaches $12N.
- The sources read here do not establish which case applied to persons in E1 §27’s diagnostic.

### 4.5 Inheriting a DI-derived PIA versus a new death computation

- **Inheritance:** `deceased_record` first returns the last pre-death worker record (`src/populace_dynamics/cola_track_a/benefits.py:378–387`). A DI-origin record passes `disability_year` alone. D never supplies both `death_year` and `disability_year`; the helper refuses that combination (`src/populace_dynamics/ss/statutory_aime.py:237–243`). Test that the combined call never occurs.
- **New death computation:** a decedent without a DI record who dies before 62 receives tag `"death_before_eligibility"` (`src/populace_dynamics/cola_track_a/benefits.py:404–420`). Its level stays on legacy `approximate_pia` under every mechanism. Changing that level would expand D beyond DI (§16 item 8).

### 4.6 Supported histories and refusal

The helper does **not** detect multiple spells, ended spells or child-care eligibility. Its checks reject:

- birth before 1913, attaining 62 before 1975;
- disability or death before birth;
- disability and death arguments together;
- earnings years before 1951.

See `src/populace_dynamics/ss/statutory_aime.py:218–244`, `:353–358`. A later engine award overwrites `di_award_year` while preserving recovery history (`src/populace_dynamics/engine/di_entitlement.py:548–553`).

**Child-care dropouts and within-year statutory rules remain disclosed omissions. Before applying D, the adapter validates the supported single-spell history using immutable projection events, rather than assuming the final award year identifies the complete history. It distinguishes inheritance of an existing DI-derived PIA from a new death computation. Unsupported D computations stop the joint attempt before tabulation; the attempt and all uncomputed rows are reported. No recipient is dropped, latest spell substituted, or fallback selected.**

**Fields read.** For each draw, read the person’s row in every `ProjectionResult.slices` slice through their last slice:

- opening and annual slices 2011–2030 (`src/populace_dynamics/engine/loop.py:218`, `:357`, `:370`);
- opening state after initialization (`:203–206`), bound by Track A to `prepare_opening_di_state` (`src/populace_dynamics/cola_track_a/adapters.py:240–244`), which refuses an opening entitled worker who has already attained FRA (`src/populace_dynamics/engine/di_entitlement.py:363–368`);
- `di_event`, `di_entitled`, `di_award_year`, `di_recovery_year`, `di_conversion_year` (`:117–125`);
- event values `opening`, `none`, `continuing`, `award`, `recovery`, `conversion` (`:126–133`), initialized as `opening` (`:400`) and set annually (`:555–567`);
- birth year, opening status and any `OpeningStockRecord`.

A3 supplies opening entitlement and award fields and leaves recovery and conversion years null (`src/populace_dynamics/cola_track_a/opening.py:401–407`). Track A schedules no entrants (`src/populace_dynamics/cola_track_a/runner.py:907`) and no births (`src/populace_dynamics/cola_track_a/adapters.py:19–22`), so each history begins in the opening slice.

**Overwritten award detection.** Count annual events rather than relying on the final award field:

- a_p = number of projected `award` events;
- r_p = number of `recovery` events;
- c_p = number of `conversion` events.

The engine writes each new award year at `src/populace_dynamics/engine/di_entitlement.py:551`, retains recovery years at `:550`, `:553`, and exposes recovered workers to re-award at `:514–519`. Any a_p ≥ 2 detects overwritten projected awards. Cross-check event counts and dates against the final state.

**Projected-award records**, `worker_record`’s second branch (`src/populace_dynamics/cola_track_a/benefits.py:320–330`), must satisfy every condition:

- **S1:** opening `di_entitled` is false; award, recovery and conversion years are null.
- **S2:** a_p = 1 in year A; the last state’s award year equals A.
- **S3:** r_p = 0; the last recovery year is null.
- **S4:** c_p ≤ 1. If conversion occurs in C, C > A and the last conversion year equals C; otherwise that field is null.
- **S5:** entitlement is true from A through the slice before C, or the last slice if there is no conversion, and false from C onward.
- **S6:** helper dates/history are accepted: b ≥ 1913, e ≥ b, no history year ≤ 1950.

**Opening disabled-worker records**, the first branch (`:312–319`), must satisfy:

- **O1:** opening entitlement is true; recovery and conversion years are null.
- **O2:** a_p = 0 and r_p = 0 during projection.
- **O3:** c_p ≤ 1, with date/state consistency as in S4–S5 and entitlement beginning at opening.
- **O4:** use and count the §4.4 disability-year proxy.
- **O5:** satisfy S6.

Only projected history is validated. Treating the opening spell as the person’s only disability period is an assumption about unobserved pre-opening history, disclosed as a limitation.

Unsupported requested D histories include:

- multiple projected awards;
- recovery followed by re-award;
- opening DI followed by recovery and re-award, even though that has only one projected award and falls through the first `worker_record` branch (`:309–320`);
- conversion without prior entitlement;
- disagreement between events and stored state;
- helper refusal.

**Scope:**

- Validate every person whose DI level D or DS requests in any draw, row or scenario.
- L retains legacy levels without this validation.
- S computes the event counts for every record it reaches, to classify §5.4’s orderings, without imposing D’s level check.

### 4.7 What D omits

Retain and disclose the helper’s omissions (`src/populace_dynamics/ss/statutory_aime.py:114–135`):

- child-care dropout years (`:117–120`);
- the second sentence of 415(b)(2)(A) (`:121–124`);
- ended or multiple disability periods and the 12-month rule (`:125–127`);
- section 104(j)(2) of the 1972 amendments (`:128`);
- dates within a year (`:129–131`).

## 5. Mechanism S: DI/spouse dual entitlement

### 5.1 Scope

S is registered independently of D. It applies when the person:

- is on a projected basis, rather than an intact opening basis (`src/populace_dynamics/cola_track_a/benefits.py:820–837`; `src/populace_dynamics/fra68_track/benefits.py:905–928`);
- is married;
- has an own DI-origin record in the scenario: kind `"disabled"` or `"converted"`. A projected conversion may remain disabled in a reform scenario (`src/populace_dynamics/fra68_track/benefits.py:437–442`).

For these persons S changes two things:

1. Remove `own.kind != "disabled"` from spouse-excess suppression (`src/populace_dynamics/cola_track_a/benefits.py:571`).
2. Replace the excess’s own-claim start with §5.2’s application. The replaced rules are `src/populace_dynamics/cola_track_a/benefits.py:583–599`, `:628–639`, and `src/populace_dynamics/fra68_track/benefits.py:487–521`, `:567–614`.

Removing suppression alone is insufficient: the helper also requires a claim or conversion year (`src/populace_dynamics/cola_track_a/benefits.py:628–631`).

Retain the linked-spouse gaps and counters (`:604–626`), linked-worker record and C1/C2 moves, reference-year gate and amount arithmetic.

S does not change ordinary retirement claimants’ own excess rules, widow(er) benefits, intact opening payments or benefits for unlinked spouses. Track A requires an own `PiaRecord` before assessing a married person’s spouse excess (`:550–572`). The ordering rules below define scope; they do not establish an ordering error reachable in v1.

### 5.2 The hypothetical application-month function

**S uses one registered function returning a hypothetical application month from immutable baseline information. Its specification identifies the claim field, annual-date mapping, assumed birth month, scheduled baseline conversion beyond the projection horizon, missing-date behavior, and prior-application predicate. Spouse entitlement begins at the latest of application, age-62 eligibility, and applicable linked-worker entitlement. The application month remains fixed under C0/C1/C2; scenario FRA and linked-worker entitlement retain their registered changes.**

H(i) is defined for a person whose own record is DI-origin in some scenario. Its sources are **immutable baseline projection state, frozen cohort metadata and the baseline parameter bundle**. State supplies the claim and DI dates; cohort metadata supplies birth year, opening status, any `OpeningStockRecord` and cohort start year. These determine the baseline DI-origin record before scenario relabelling or claim response (`src/populace_dynamics/cola_track_a/benefits.py:211–218`, `:302–330`).

Explicit inputs:

- **b:** birth year.
- **c:** nullable `claim_year`.
  - The claiming step writes it when `claimed` newly becomes true through a reached claim age or conversion flag (`src/populace_dynamics/engine/claiming.py:85–89`).
  - Track A leaves DI-entitled rows untouched by ordinary claiming (`src/populace_dynamics/cola_track_a/adapters.py:185–206`).
  - Projected claims are drawn over ages 62–70 (`src/populace_dynamics/claiming.py:90`, `:262–275`; loaded at `src/populace_dynamics/cola_track_a/runner.py:167–190`).
  - A3 supplies opening `claim_year` for non-disabled recipients (`src/populace_dynamics/cola_track_a/opening.py:408–417`).
- **a:** baseline DI record’s `PiaRecord.entitlement_year`: projected award year (`src/populace_dynamics/cola_track_a/benefits.py:321`, `:330`), or opening entitlement year, else cohort start year (`:317–318`). It is at least eligibility year e and exceeds e for a projected award after 62.
- **q:** nullable baseline `di_conversion_year`. The integrity check below reads q. Scheduled conversion is computed even when q is null or beyond the horizon (`src/populace_dynamics/engine/di_entitlement.py:218–234`, `:554–565`).
- **FRA_base(b):** baseline FRA in months (`src/populace_dynamics/ss/params.py:162–170`).
- **m0 = 7:** A4’s assumed birth month (`src/populace_dynamics/engine/di_entitlement_rates.py:211`).

**Rule:**

- **Case P, prior application:** c is not null and c < a. Set Y_app = c.
  - c may be a projected retirement claim at 62–70.
  - It may instead be A3’s opening receipt start for a non-disabled opening recipient on a projected basis, without an `OpeningStockRecord` (`src/populace_dynamics/cola_track_a/opening.py:323–326`, `:408–417`).
  - The latter is a proxy: A3 does not classify that benefit, and receipt can begin before 62.
  - Count `s_prior_claim_projected` and `s_prior_claim_opening` separately.
- **Case Q, otherwise:** set  
  Y_app = Y_conv = b + (m0 − 1 + FRA_base(b)) // 12.  
  This uses the engine’s baseline conversion-year rule (`src/populace_dynamics/engine/di_entitlement.py:218–234`, `:512`, `:554`), even beyond 2030.
  - If c is not null and c ≥ a, require c = q = Y_conv. Otherwise refuse (§10). An ordinary claim is not drawn during active DI entitlement.

**Annual-to-month mapping:**

m_app = 12(Y_app − b).

This places an annual application at the birthday month under the July assumption, matching the retained whole-year mapping (`src/populace_dynamics/fra68_track/reform.py:538–583`; `src/populace_dynamics/cola_track_a/benefits.py:646–650`).

When FRA_base(b) mod 12 < 6, the conversion-year application precedes FRA by that remainder. Retain E1’s named whole-year conversion delta and diagnostics (E1:667, :797–799; `src/populace_dynamics/fra68_track/benefits.py:163–172`).

| Situation | Behavior |
|---|---|
| Missing b, or no FRA bracket covers b | Refuse (`src/populace_dynamics/ss/params.py:168–169`). |
| Missing a | Track A already refuses a DI-origin record lacking its required award (`src/populace_dynamics/cola_track_a/benefits.py:322–325`). |
| c is null | Select case Q and compute scheduled conversion. |
| Y_app > 2030 | No excess in 2030 in any scenario; count `s_application_after_reference`. This is not a refusal. |

**A null claim year selects case Q; payment depends on the computed conversion year and §5.3’s gates.** Null `claim_year` alone does not establish active entitlement: the claiming step writes a date only for a newly claimed person (`src/populace_dynamics/engine/claiming.py:85–89`).

H reads only immutable baseline state, frozen cohort metadata and the baseline bundle. It is fixed under C0/C1/C2 and S/DS. Only kind `"retired"` receives `_claim_response`; DI relabelling preserves entitlement information (`src/populace_dynamics/fra68_track/benefits.py:432–444`).

### 5.3 Spouse entitlement in each scenario

For linked worker w and scenario s, retain:

- y_w,s: the worker’s scenario entitlement year, including a C1/C2 move;
- y_w: baseline worker entitlement year;
- v_w,s: exact months moved by C1/C2.

Worker timing is read as in `src/populace_dynamics/fra68_track/benefits.py:540–565`. Exercise 1 and C0 use v = 0.

Define:

- **Entitlement year:** E_s = max(Y_app, b+62, y_w,s). Pay in 2030 only if E_s ≤ 2030.
- **Entitlement month of age:** e_s = max(m_app, 744, 12(y_w−b)+v_w,s).
- **Months early:** k_s = max(0, FRA_s(b)−e_s).

For DI-origin records, deferral to 62 replaces Track A’s refusal of an entitlement before 62 (`spouse_entitlement_before_62`, `src/populace_dynamics/cola_track_a/benefits.py:637–639`). L withholds even when the person is older by 2030.

The difference requires max(Y_app, y_w,s) < b+62, which needs an opening receipt start before 62 because projected claims begin at 62 or later. Count `s_entitlement_deferred_to_62`.

### 5.4 Entitlement orderings

**The excess-before-age-reduction formula applies when spouse entitlement begins during or concurrently with unreduced DI entitlement. The registration must separately specify prior spouse-only entitlement and prior RIB-to-DI treatment. Unsupported histories refuse before tabulation; they never silently receive the concurrent-entitlement formula. Retained own-benefit approximations are disclosed separately.**

Let OB = ½ PIA_w. Formula F is:

excess_s(t) = floor-to-dime[max(0, ½PIA_w,s(t) − PIA_i,s(t)) × (1−ρ(k_s))].

The separate ordering rules are grounded in [POMS RS 00615.260, TN 42](https://secure.ssa.gov/poms.nsf/lnx/0300615260).

| Ordering, at annual resolution | Predicate | S’s rule | POMS basis |
|---|---|---|---|
| **DI-first** | Q and E_s > a | Formula F; own DI unreduced | A.2 reduces the excess after unreduced DIB. |
| **Concurrent** | Q and E_s = a | Formula F; own DI unreduced | A.2 and B.2’s concurrent example. |
| **Prior RIB, then spouse, then DI** | P and E_s < a | Formula F, retaining original spouse entitlement e_s; own DI unreduced as a disclosed approximation | A.1 preserves excess for equal PIAs and recalculates it for changed DIB PIA using original spouse reduction months. |
| **Prior RIB, then DI, then spouse** | P and E_s ≥ a | Formula F; own DI unreduced as a disclosed approximation | B.1 reduces the excess over unreduced DIB separately. |
| **Spouse-only first** | E_s < a under Q, or E_s < c under P | Refuse before tabulation | A.1/B.2 require different ordering arithmetic. |
| **Earlier spell ended, then re-awarded** | DI-origin in 2030 with r_p ≥ 1 | Refuse under S and DS | B.2’s termination treatment is not implemented. |
| **DIB ended before FRA, without re-award** | Not DI-origin in 2030 | Outside S; retain Track A retirement rules | B.2’s further reduction remains omitted. |

Under H, concurrent and spouse-only-first cases are unreachable:

- Q gives E_s ≥ Y_conv > a: awards require year < FRA year and conversion occurs in the FRA year (`src/populace_dynamics/engine/di_entitlement.py:512–519`); an opening record’s entitlement is at or before opening.
- P gives E_s ≥ c.

Both cases still receive direct-dispatch tests.

The source’s ordering example distinguishes concurrent excess 90, total 370, from spouse-first excess 20, total 300, for OB 400 and DIB 280. Preserve that distinction in the tests. [POMS RS 00615.260 B.2](https://secure.ssa.gov/poms.nsf/lnx/0300615260)

Classify ordering separately in every scenario for records reaching S’s amount step: a linked, rostered, living worker with a record and available level, and E_s ≤ 2030. Under P, an opening receipt start represents the disclosed prior-RIB proxy.

Each reachable ordering has its own justification; Formula F is not a default for unsupported histories.

### 5.5 Amounts and retained approximations

- Use `spousal_benefit`: half the worker PIA less own PIA, floored at zero, then age-reduced (`src/populace_dynamics/ss/benefits.py:205–236`).
- Reduction is 25/36 of one percent per month for the first 36 months and 5/12 of one percent thereafter (`:185–202`; `src/populace_dynamics/ss/params.py:101–104`).
- Apply each PIA’s increased path on its own clock (`src/populace_dynamics/cola_track_a/benefits.py:644–645`) through `spouse_excess_path`, flooring each payment to the dime (`src/populace_dynamics/scenario_benefits.py:872–903`, especially `:900`).
- Own DI retains factor 1 (`src/populace_dynamics/cola_track_a/benefits.py:374`). A zero own DI amount does not bar eligible positive spouse excess.

Disclose retained approximations separately:

- The own-DIB reduction for prior reduced RIB is omitted; count `s_rib_to_di_own_reduction_not_modeled` by row and scenario. The source distinguishes that reduction from excess arithmetic. [POMS RS 00615.260 A.1](https://secure.ssa.gov/poms.nsf/lnx/0300615260)
- S uses L’s DI levels; DS uses D’s retained approximations.
- E1’s whole-year conversion mapping remains.
- Gross benefits retain no family maximum, earnings test or offsets (A1 §11 rule 5 and §12).
- Opening observed amounts and linkage limits remain inherited.

### 5.6 What S changes, by exercise

These are deductions from the cited code and registered rules, not outcome claims.

**Exercise 1:**

- For converted records, H returns a prior claim under P or scheduled baseline conversion under Q. With consistent baseline metadata, this matches Track A’s own claim or conversion fallback (`src/populace_dynamics/cola_track_a/benefits.py:594–599`).
- Where L pays, S pays the same amount whenever max(c, y_w) ≥ b+62.
- Where the opening proxy gives max(c, y_w) < b+62, L withholds and S defers to 62 (§5.3).
- A record still DI-entitled in the baseline projection without a prior application has scheduled conversion after 2030; otherwise the engine would have converted it (`src/populace_dynamics/engine/di_entitlement.py:505–512`). S and L both pay no spouse excess there.
- S therefore changes amounts for:
  1. active DI records with a prior application;
  2. DI-origin records whose entitlement L rejected as before 62.

**Exercise 3 baseline:** the same two groups. Where L pays, S’s baseline months-early count matches Track A, including conversion claims (`src/populace_dynamics/fra68_track/reform.py:584–641`).

**Exercise 3 reforms:** S changes those groups against reform FRA and additionally:

3. Records converted in baseline but still disabled in reform: S pays from Y_app, measuring reduction against reform FRA.
4. Records converted in both scenarios with an application at baseline conversion: replace E1 §11 rule 3’s baseline count with the fixed-application count against scenario FRA.

For group 4, where application starts the excess, reform months early exceed the baseline count by the FRA increase D when FRA_base(b) mod 12 < 6, and otherwise by max(0, D−12+FRA_base(b) mod 12).

Group 4 follows from fixing the application. §16 item 5 leaves that choice open for Max. E1 rule 3 and its diagnostics remain under L and D.

### 5.7 A hypothetical application, not statutory deemed filing

H is a behavioral assumption that an application is filed in its returned month. It does not reconstruct statutory deemed filing.

POMS distinguishes birth dates before January 2, 1954 from later births, exempts a DIB beneficiary’s reduced spouse application from deemed reduced-RIB filing, applies deemed filing when DIB terminates before FRA while spouse entitlement continues, and applies the birth-date rules at DIB-to-RIB conversion. [POMS GN 00204.035 B.1–B.2, TN 166](https://secure.ssa.gov/poms.nsf/lnx/0200204035)

H does not implement those rules:

- P resembles the prior application described in E1:668, but applies regardless of birth date or whether the linked worker was entitled when the person claimed.
- Q coincides with deemed filing at conversion only for some birth dates and only in baseline.

This filing assumption is neither observed behavior nor universal take-up. Some active DI recipients remain unpaid until their application date.

## 6. Hypothesis provenance

### 6.1 Timeline

| Date | Event | Source |
|---|---|---|
| 2026-09-23, 23:06–23:31 UTC | Exercise 1 one-shot run; T follows | T:15 |
| 2026-09-25, 02:14:13 UTC; 2026-09-24 22:14:13 −04:00 | E1 `e1-ratified-1`, commit `cd7c790b` | Git history |
| 2026-09-25, 21:25:27 UTC; 17:25:27 −04:00 | E1 `e1-ratified-2`, including §27, commit `2f75012e` | Git history |
| 2026-09-25, 22:36–23:07 UTC | Exercise 3 one-shot run | F:15 |
| 2026-09-25, 23:27:01 UTC | Exercise 3 artifact commit `aea61e22`; seal opening follows | F:188; Git history |
| 2026-09-25 | Public exercise 3 memo F | `EV/RESTRICTED-FILES.md` changelog |
| 2026-09-27 | Phase-2 plan P and ruling d479 | P:3; common brief |

E1 §27 predates exercise 3’s opening and postdates exercise 1’s public result. F’s passages postdate exercise 3’s opening. Earlier documentation of a convention does not make later gap interpretation pre-opening.

### 6.2 Exercise-3 estimand and claiming analysis

| Analysis | Exact v1 source | Timing |
|---|---|---|
| Averaging base | F:132: “a claiming response averaged over everyone in the age group rather than over recipients” | Post-opening hypothesis, 2026-09-25 |
| Zero treatment | F:134: “If that average runs over everyone in the age group, a postponed claimant counts as zero in the reform.” | Post-opening interpretation |
| Union ratio | F:138: “E1 §7 and §16 require this diagnostic, but it is not a registered row.” Also: “It is a question for a future registration, not a result.” | Diagnostic defined before opening in E1; scoring interpretation proposed afterward |
| C1 | F:103: “C1: claimants at 65 or later delay by the FRA increase” | Transform registered in E1 §13 before opening |
| C1 explanatory hypothesis | F:147: “Hypothesis (b), a claiming response at the retirement age. Claimants who move to the retirement age keep their factor.” | Post-opening hypothesis about the registered transform |
| C2 | F:104: “C2: every projected claimant delays”; F:133: “Our registered C1 and C2 rows average over recipients” | Transform pre-opening; joint averaging-base interpretation post-opening |

Public union diagnostics are already observed evidence. Registering v2 counterparts does not score v1 retroactively or restore blindness. These are the public memo’s hypotheses, not established DYNASIM mechanisms.

### 6.3 Mechanism D

- T, after exercise 1’s comparison, states: “DI levels are a disclosed approximation” (T:80).
- E1 §27, dated 2026-09-25, `e1-ratified-2`, commit `2f75012e`, listed option 2 before exercise 3’s opening (E1:1903–1906):

  > Replace the zero DI levels by a statutory DI computation. This departs from the DI-level ruling (d188 item (a), carrying over d074 decision 2(b)); with a positive level the person stays a recipient in both scenarios and only the withheld excess remains (§12).

- **Correction retained:** statutory computation years cannot repair an empty earnings history. “With a positive level” requires enough indexed earnings (§4.4).
- P:62, 2026-09-27: “Statutory computation years can change nonzero DI levels but do not repair empty earnings histories”.
- None establishes gap closure or DYNASIM’s mechanism. D is justified by statutory fidelity.

### 6.4 Mechanism S

- E1 §27 option 1, dated 2026-09-25, `e1-ratified-2`, commit `2f75012e`, before exercise 3’s opening (E1:1899–1902):

  > Pay a DI-entitled worker aged 62 or older the spouse's excess under 402(q)(3)(C), assuming the application is filed. This departs from running exercise 3 exactly like Track A (d188 item (a)) and changes baseline amounts relative to exercise 1.

- E1:668 records the statutory reading behind it.
- F:182, after opening, states: “Under the statute these people would be paid a spouse’s benefit once they filed (E1 §12, §27). Max kept the convention (d315) and deferred statute-following dual entitlement to a later Track A v2.”
- P:62 keeps S separate from D.
- F:141 and E1:668 also contain statements about the convention’s effect on the reform cut. This delta neither adopts nor tests those statements. They remain exposures for forecasters (§13).

## 7. Estimands, definedness and claiming responses

### 7.1 Statistics

For draw k and age cell g, T_s is weighted benefit total and W_s positive-recipient weight in scenario s, using the row’s selected components.

- **Exercise 1:** retain A1 §7—common membership, ratio of weighted totals for R0–R2, R4 and R5, and weighted mean of individual ratios for R3.
- **Exercise 3 recipient means:**

  R = 100[(T_R/W_R)/(T_B/W_B) − 1].

  Membership is scenario-specific (E1:511–521). F5 instead retains the weighted mean of individual ratios over recipients in both scenarios (E1:507, :520–523).

- **Registered common-base union statistic:**

  U = 100(T_R/T_B − 1),

  over everyone alive in the age cell.

U equals the percentage change in mean benefits over everyone alive, including zeros. Double-zero persons cancel from this percentage change, although population mean levels and denominators still require them. `union_benefit_rows` omits double-zero records (`src/populace_dynamics/fra68_track/benefits.py:946`, `:970–971`).

### 7.2 Definedness

**U is defined when the weighted baseline total is positive. A zero reform total gives U = −100%; a zero baseline total makes U undefined. R requires positive recipient-weight denominators in both scenarios and a positive baseline mean. Undefined per-draw statistics make that cell’s across-draw mean and SD undefined.**

- R retains A7’s rule (`src/populace_dynamics/estimates/cola_age_profile.py:1228–1261`).
- Implement U in a new module reusing A7 normalization; do not edit A7.
- Exercise 1 retains A1’s rule: no members or zero baseline total means undefined.

### 7.3 Aggregation and uncertainty

Use arithmetic mean and sample SD of 20 per-draw statistics, divisor K−1, rather than a pooled ratio.

For every statistic, including U, use A1 §16’s half-split floor. Exclude seeds with either half undefined and report usable-seed count. Fewer than two usable seeds gives an undefined floor, never zero.

### 7.4 Claiming responses

- **C0:** fixed claim ages.
- **C1:** move eligible projected retirement claims at age 65 or later.
- **C2:** move every eligible projected retirement claim.

Retain the FRA-increase shift, age-70 cap, exact moved months and factor recalculation (`src/populace_dynamics/fra68_track/benefits.py:368–411`; E1 §13). Claims at or before opening (`:380–382`), DI records and conversions stay outside the transform. H remains fixed.

## 8. Frozen row matrix and headlines

| Mechanism | DI computation | DI/spouse rule |
|---|---|---|
| L | Legacy `approximate_pia` | Legacy suppression while DI-entitled |
| **D, primary** | Statutory computation years | Legacy |
| S | Legacy | §5 dual entitlement |
| DS | Statutory computation years | §5 dual entitlement |

For each mechanism compute:

- **R0–R5:** A1 §18’s timing, clock, statistic and components.
- **F0–F7:** E1 §18’s schedule, survivor, claiming, statistic and components, subject to this delta.
- **U0–U2:** F0, F3 and F4 respectively, replacing recipient means with U and retaining F0’s five components.

Total: **4 × (6+8+3) = 68 tabulations, five age cells each**, using one projection ensemble.

**D×R0 and D×F0 remain the headlines. No variant may be selected, substituted or promoted because of comparator distance known from v1 or learned in v2. Publish the complete matrix in a fixed order regardless of fit.**

Order:

1. Mechanisms L, D, S, DS.
2. Within mechanism: R0–R5, F0–F7, U0–U2.
3. Within row: 50–61, 62–64, 65–69, 70–79, 80+.

## 9. Membership guards

**Membership guards are specified by mechanism, row and selected components. L/D retain the registered legacy predicate where applicable. S/DS cannot excuse a difference using the disabled-spouse suppression that S removes. Other C0 differences refuse before tabulation unless an independently justified predicate was registered beforehand. Refusal does not authorize broadening a predicate after inspecting the result.**

The legacy C0 exception requires **every** condition (`src/populace_dynamics/fra68_track/benefits.py:1036–1087`):

- baseline-only recipient;
- projected basis;
- converted in baseline and disabled in reform;
- conversion years straddling 2030;
- selected spouse excess positive in baseline and zero in reform;
- every other component zero in both scenarios.

**Exercise-1 filtering boundary:**

**Compute both scenarios’ selected-component recipient flags from unfiltered per-person components before discarding any person whose baseline total is nonpositive. Refuse either direction of membership difference before any tabulation.**

For each person-draw and exercise-1 row, construct truthful scenario beneficiary flags from unfiltered totals and apply A7’s `positive_benefit` rule to that row’s selected components. Reject unequal selected-component flags before the baseline-total filter. Keep the existing positive-baseline/nonpositive-reform check and A7’s later check on retained rows.

Implement this collection and guard in the new registered module or joint runner. Legacy Track A discards baseline-zero persons at `src/populace_dynamics/cola_track_a/benefits.py:840–841`; A7 can check only supplied rows (`src/populace_dynamics/estimates/cola_age_profile.py:1104–1129`, `:1899–1907`). This placement guarantees the injected refusal test; it does not assert a reachable reform-only case under the registered COLA arithmetic.

| Rows | Guard before any tabulation | L | D | S | DS |
|---|---|---|---|---|---|
| R0–R5 | Selected-component flags from unfiltered components; refuse either direction before baseline filtering. Retain Track A’s per-person check and A7’s retained-row check. | All checks; no exception | Same | Same | Same |
| F0, F1, F2, F5, F7, U0 | Classify A7 recipient flags (`src/populace_dynamics/fra68_track/benefits.py:1090–1204`; runner order `src/populace_dynamics/fra68_track/runner.py:998–1011`). U0 shares F0’s classification. | Admit only the exact legacy conjunction; otherwise refuse | Same | Every difference refuses, including a legacy-predicate match | Same |
| F6 | Same classifier; worker components only | Spouse exception cannot apply; refuse every difference | Same | Same | Same |
| F3, F4, U1, U2 | Classifier counts differences under C1/C2 | Count direction and legacy-predicate matches; allow | Same | Count and allow; legacy matches are diagnostic only | Same |

No other predicate is registered. In particular, there is **no dime-floor exception**. Positive reduction factors do not prove identical positive membership because spouse payments are floored (`src/populace_dynamics/scenario_benefits.py:900`).

S changes only spouse amounts. A7 counts positive selected benefits (`src/populace_dynamics/estimates/cola_age_profile.py:442`, `:1125–1126`), and exercise 3 requires that recipient rule (`src/populace_dynamics/fra68_track/runner.py:770–775`). Therefore, for every statistic:

- S×R5 = L×R5;
- DS×R5 = D×R5;
- S×F6 = L×F6;
- DS×F6 = D×F6.

## 10. Refusal order and the attempt record

Any refusal stops the **whole joint attempt before any of the 68 tabulations**.

1. Project twenty draws once and hash slices.
2. Under D/DS, validate every requested DI history.
3. Compute benefits for all mechanisms, exercises and scenarios. Apply:
   - Track A’s per-person check and exercise-1 selected-component membership check on unfiltered components, before discarding any baseline-zero person;
   - H’s missing-date and integrity refusals;
   - S’s spouse-only-first and ended-spell/re-award refusals.
4. Re-hash slices; refuse changes.
5. Classify every row’s membership under every mechanism.
6. Tabulate all 68 rows.

Publish a refused attempt with:

- the refusal, first failing person-draw and step;
- every uncomputed row;
- all counters computed before the stop.

The registration states re-execution allowances. Recommended: infrastructure failures only, matching Registration 14 (E1:1767–1768). A change after refusal requires a new version and registration.

## 11. Freeze and the new registration

Except for the separately authorized and frozen structural check below, freeze the following before any real-data replay, smoke result, benefit diagnostic or tabulation:

- ratified specification, implementation commit, input/parameter hashes, executor and environment;
- population, projection configuration, weights, links, careers, age groups and reference year;
- estimands, membership construction, zeros, components, definedness and draw aggregation;
- D’s proxies, event predicate, cutoff and cache keys;
- S’s application function, ordering rules and refusals;
- membership guards by mechanism, row and component;
- exact 68-row manifest, headlines, diagnostic definitions and reporting template;
- K = 20, seeds 5200–5219, half-split seeds 0–4 and fraction 0.5, retaining uncertainty rules;
- hypothesis chronology, exposure disclosures, conditional forecasts and attempt-recording procedure.

**The sole pre-registration exception is the structural check in §16 item 7, if Max explicitly authorizes it. Before that check, freeze and record its implementation, inputs, permitted count outputs and execution procedure. It computes no benefit amounts, weight sums or tabulations. Publish its attempt and counts, and bind them into the subsequent issue #42 registration.**

**A new issue #42 registration binds the following before any new real-data computation other than that separately frozen, explicitly authorized structural check:**

- final specification and hash;
- implementation commit;
- input and parameter hashes, including the statute source at §4.1’s full path;
- complete 68-row manifest;
- reporting template;
- participant exposure record;
- conditional forecasts;
- execution procedure;
- structural-check authorization, frozen protocol, attempt record and permitted counts, if authorized.

Development uses invented data, with the sole exception of that separately frozen structural check if explicitly authorized.

Use new modules or registered versions. Do not edit in place:

- `engine/loop.py`, `engine/steps.py`, `gates.yaml`;
- committed run artifacts;
- v1 modules under `cola_track_a/`, `fra68_track/`, `ss/`, or `estimates/cola_age_profile.py`.

Selection by comparator distance is prohibited for structure, income concepts, denominators, rows and parameters.

## 12. Invented-data tests

These tests are implementation requirements. This revision checked invented arithmetic but did not run the implementation suite. Use invented data and parameter bundles. Load-bearing invariants receive Hypothesis property tests alongside concrete examples; §12.10 specifies differential tests.

### 12.1 Statutory DI fixtures

Use flat invented AWI and nonbinding wage bases.

- **Birth 1960, disability year 1990:** E = 8, N = 7, indexing year 1988.
- **Death instead in 1990:** N = 8−5 = 3.
- **Ordinary age-62 calculation:** E = 40, N = 35.
- **Eight $12,000 earnings years, 1983–1990:** D top-seven sum $84,000, AIME $1,000; legacy sum $96,000, AIME ⌊96,000/420⌋ = $228.
- **One $12,000 year with N = 7:** AIME ⌊12,000/84⌋ = $142.
- **Boundaries:** E = 4/5, 9/10, 14/15, 19/20, 24/25; five-year cap at 29/30; minimum N = 2 at E ≤ 2. Include ties, zero padding and flooring.
- **Inclusion/refusal:** include eligibility year; reject b < 1913, d < b, simultaneous death/disability arguments and history years ≤ 1950.
- **Argument at or after 62:** birth 1950, disability year 2014 gives E = 40 and N = 35. With the same retained history and indexing, D equals legacy. Existing count coverage is at `tests/ss/test_statutory_aime.py:143–148`. The raw-award integration distinction is tested separately in §12.10.

### 12.2 Nonflat AWI and binding ceiling

Inputs:

- birth 1960, award/cutoff 1990, hence e = 1990;
- 1987–1991 earnings: $12,000, $6,000, $6,000, $12,000, $999,999;
- AWI: 100 in 1987, 200 in 1988, no other indexing years supplied;
- wage base $6,000 in 1987 and $10⁹ from 1988 onward; wage-base values persist until changed (`src/populace_dynamics/ss/params.py:150–159`).

Calculation:

1. Drop 1991.
2. Cap 1987 at $6,000.
3. Index 1987 by 200/100; later years remain nominal.
4. Retained indexed amounts: $12,000 + $6,000 + $6,000 + $12,000 = $36,000, plus three zeros.
5. AIME = ⌊36,000/84⌋ = **$428**.
6. With invented 1990 bend points (400, 2,000) and factors .90/.32/.15, PIA = floor-to-dime(360 + .32×28) = **$368.90**. Give 2022 different bend points so an incorrect bend-point year is detectable.

**Each error the fixture catches produces a detectable wrong result or indexing-year assertion:**

| Mutation | Expected wrong result |
|---|---|
| Clip through onset−1 | ⌊24,000/84⌋ = 285 |
| Include 1991 | ⌊1,035,999/84⌋ = 12,333 |
| Ignore ceiling | ⌊48,000/84⌋ = 571 |
| Omit indexing | ⌊30,000/84⌋ = 357 |
| Use legacy divisor | ⌊36,000/420⌋ = 85 |
| Index to 1987 | 357; direct indexing-year assertion distinguishes this from omitted indexing |
| Other indexing year | Missing AWI lookup raises (`src/populace_dynamics/ss/benefits.py:87–89`) |

### 12.3 Statutory DI invariants

- Zero histories remain zero.
- For fixed nonnegative indexed earnings, increasing earnings cannot reduce AIME.
- Reducing selected-year count cannot reduce the highest-years average.
- For identical retained history and indexing year, D AIME ≥ legacy AIME, with equality at N = 35. This concerns levels only and implies no direction for a tabulated statistic.
- 2 ≤ N ≤ 35.
- Earnings after the frozen cutoff have no effect.
- Components with no changed own or linked DI-derived input remain unchanged.
- Conversion preserves DI-origin PIA.

### 12.4 Integration coverage

**D may change an affected person’s own DI-derived payment and any spouse or widow excess that reads that person’s changed own PIA or payment, as well as auxiliaries that read a linked worker’s changed DI-derived PIA. Assert bit-for-bit equality only for components with no changed DI-derived input and for intact opening observed payments.**

The spouse dependency reads both PIAs (`src/populace_dynamics/cola_track_a/benefits.py:644–655`). The widow dependency reads and subtracts own payment (`:708–730`).

| Case | L → D may change | L → S may change |
|---|---|---|
| Active DI, projected award | Own disabled-worker amount and recipient’s widow excess | Spouse excess under P with E_s ≤ 2030 |
| Continuous conversion | Own retired-worker amount and recipient’s spouse or widow excess | Exercise 1/baseline: excess where L withheld entitlement before 62; where L pays, unchanged. Exercise-3 reform: §5.6’s spouse effects |
| Living auxiliary of DI-origin worker | Spouse excess through linked PIA, and through auxiliary’s own DI PIA if applicable | Nothing unless auxiliary’s own record is DI-origin |
| Survivor of deceased DI-origin worker | Widow excess through inherited PIA and, where applicable, changed own DI payment | Nothing |
| Opening disabled worker as linked worker or decedent | Auxiliary amount; worker’s intact observed payment stays identical | Nothing unless auxiliary’s own record is DI-origin and §5’s spouse scope applies |
| Intact opening observed amount | Nothing | Nothing |
| Ordinary retirement | Ordinary retirement level and own payment unchanged; auxiliaries involving another changed DI-derived input may change | Ordinary level/payment unchanged; a DI-origin recipient’s spouse excess using this ordinary linked-worker record may change |
| Standalone pre-eligibility death | Legacy death level unchanged; survivor’s widow excess may change through their own DI payment | Nothing |

**Invented integration cases with unchanged ordinary records.**

Use these baseline/null-policy fixtures in both exercise calculators:

- AWI 100 in every year 1951–2030;
- wage base $10⁹ from 1951;
- PIA factors `(1,1,1)`;
- FRA 804 months;
- zero COLAs and null reform;
- spousal share .5, survivor share 1, earliest survivor age 60;
- invented `survivor_reduction_floor = 1.0`, retaining each exercise’s survivor span.

The last setting makes survivor reduction zero regardless of months early (`src/populace_dynamics/ss/benefits.py:258–263`); it does not assert equal spans or zero early months. Exercise 3’s survivor-bundle adjustment changes the span while preserving that floor (`src/populace_dynamics/fra68_track/reform.py:494–503`).

A single $252,000 earnings year in 1987 gives:

- **Converted recipient:** born 1960, award 2017, continuous entitlement, conversion 2027.
- **Active recipient:** born 1965, award 2022, continuous entitlement through 2030.

Both have E = 35 and N = 30. Their own PIAs/payments are **$600 under L** and **$700 under D**: 252,000/420 and 252,000/360.

Test separately:

1. **Unchanged ordinary linked worker.** The converted recipient is married to an ordinary worker born 1960, claiming in 2027 with factor 1 and one $840,000 earnings year in 1987. The worker’s ordinary PIA stays $2,000. Spouse entitlement starts in 2027 without age reduction. Recipient own payment changes **600→700**, spouse excess **400→300**. Worker level and own payment remain identical.
2. **Unchanged ordinary decedent.** Run the converted and active recipients separately as survivors of an ordinary worker born 1960, claiming in 2027 with factor 1 and dying in 2030. One $672,000 earnings year in 1987 gives unchanged PIA $1,600. Recipient own payment changes **600→700**, widow excess **1,000→900**, combined payment stays **1,600**. Deceased record and PIA paths remain identical.
3. **Unchanged standalone death level.** Repeat the active-DI survivor with a linked worker born 1970, dying in 2030 before 62, without prior own entitlement or DI history, and the same $672,000 history. The standalone legacy death PIA stays **1,600** while the survivor’s own payment and widow excess change as above.

These fixtures test offsets without requiring a changed linked-worker or decedent PIA. The full integration suite also covers the table’s linked DI-origin and intact-opening cases.

### 12.5 Dual-entitlement fixtures and orderings

Unless stated otherwise:

- spousal monthly rates are 25/3600 and 5/1200, bracket 36 months;
- baseline/reform FRAs are 804/816 months;
- own DI or RIB PIA is $600; worker PIA is $2,000;
- OB = $1,000 and unreduced excess = $400.

**Test DI-first, concurrent, spouse-only-first and prior-RIB-to-DI histories separately, with expected amounts or an explicit unsupported-case refusal for each.**

- **DI-first and concurrent:** 36 months early gives factor .75, excess **$300**, and own-plus-excess **$900**. Test concurrent by direct dispatch.
- **Prior RIB, spouse, then DI:** spouse entitlement at 62 versus FRA 67 gives 60 months early, factor .65 and excess **$260**. Own DI stays $600; count omitted prior-RIB reduction. With DIB PIA $700, excess is **$195**.
- **Prior RIB, DI, then spouse:** claim at 62, award at 63, linked worker entitled at 64. e = 768, 36 months early, excess **$300**; own DI unreduced.
- **Spouse-only first:** direct-dispatch history refuses before tabulation and produces no amount. Its distinct ordering arithmetic would be $750−$600 = $150; it must not receive Formula F.
- **Ended spell and re-award:** award 2015, recovery 2018, re-award 2023, active in 2030. Refuse under S/DS and under D whenever D requests the level.

**Other fixtures:**

- Own PIA ≥ half worker PIA gives zero excess. Zero own DI does not bar positive excess.
- **Unpaid:** age below 62 in 2030, unlinked worker, outside-roster worker, or worker without a record. **The unlinked and outside-roster cases increment `spouse_unlinked` and `spouse_outside_roster`; a worker without a record produces no spouse payment.** See `src/populace_dynamics/cola_track_a/benefits.py:608–613`, `:622–623`.
- **Deferral:** b = 1960, opening receipt start 2008, award 2015, conversion 2027, worker entitled 2005. L withholds because 2008 < 2022. S defers to 2022, e = 744, pays **$260**, and counts both `s_entitlement_deferred_to_62` and `s_prior_claim_opening`.
- **Diagnostic configuration:** b = 1963, baseline conversion 2030, reform still disabled, own PIA zero, worker PIA $800, eligible linked spouse and common application. Baseline excess **$400**; reform 12 months early gives **$366.60** under S. L’s reform pays zero.

**Filing timing:**

- **Null claim with conversion beyond horizon:** b = 1965, active in 2030, null c. Q gives Y_conv = 2032; no excess in either scenario; count `s_application_after_reference`. These conditions coincide in this fixture, but null c alone does not imply conversion beyond 2030.
- **Null claim with conversion by reference year:** directly test H with b = 1963, baseline FRA 804, null c and q = 2030. H returns Y_app = 2030 and m_app = 804. Subsequent payment follows §5.3’s gates. This tests missing-date behavior without claiming this state is reachable in the frozen population.
- **Prior application:** b = 1964, claim 2026, award 2027, worker entitled 2020. e = 744. Baseline pays **$260**; reform, 72 months early, pays **$240**. L pays zero in both.
- **Fractional FRA:** b = 1955, FRA 794. Y_conv = 2021, m_app = 792, two months early; baseline excess **$394.40**, matching L’s baseline count.
- **Converted in both scenarios:** b = 1957, baseline FRA 798, reform FRA 810. Conversion years 2024/2025. Fixed application gives reform six months early and **$383.30** under S; L retains its baseline count and pays **$400**. This pins §5.6 group 4.
- **Linked ordinary worker moved under both C1 and C2:** recipient b = 1964, claim 2029, award 2030; linked worker b = 1964, ordinary retirement claim 2029 at age 65.
  - **Under both C1 and C2**, a 12-month FRA increase moves worker entitlement to 2030 with v_w = 12.
  - e = max(780, 744, 780+12) = 792.
  - Reform has 24 months early, paying **$333.30**.
  - Worker year 2030 passes the annual gate.
  - In the variant where the worker’s baseline claim is 2030, both responses move it to 2031 and reform spouse excess is zero. C1/C2 allow and count any resulting membership difference.
- **Integrity:** c ≥ a but c differing from q or scheduled conversion refuses.

### 12.6 Legacy replay and cache isolation

- L reproduces v1 calculators bit for bit on invented cohorts: Track A `reference_benefit_rows` for R0–R5, exercise-3 `scenario_benefits` and `union_benefit_rows` for F0–F7.
- D configured with legacy computation equals L.
- Mechanism orders L/D/S/DS, DS/S/D/L and draw-interleaved order give identical outputs with shared caches.
- No D cache value reaches L or vice versa.
- Projection-state hashes remain unchanged.

### 12.7 Membership refusal

- Inject unexplained baseline-only and reform-only C0 cases under every mechanism. Refuse before any of 68 tabulations.
- A case satisfying the exact legacy conjunction is admitted under L/D and refused under S/DS.
- For every mechanism and exercise-1 row, inject both directions into **unfiltered per-person components**:
  - reform-only fixture has baseline total zero and positive reform total;
  - baseline-only fixture has positive baseline and zero reform;
  - component-selection fixture has positive all-component totals in both scenarios but positive selected components in only one;
  - double-zero fixture has two false flags and does not cause refusal.
- Assert that the reform-only person reaches the guard and cannot disappear through the legacy baseline-zero `continue`.
- Count and allow C1/C2 membership differences.
- **Dime boundary:** worker PIA .30, own PIA zero, excess .15 and no other component. PIA dime flooring allows .05 excess increments (`src/populace_dynamics/ss/benefits.py:131`).
  - 48 months early: .15×.70 = .105 → **.10**.
  - 60 months early: .15×.65 = .0975 → **0**.
  - This C0 baseline-only difference refuses. No rounding exception applies.

### 12.8 Estimand definedness

| Case | U | R |
|---|---|---|
| T_B > 0, T_R = 0 | −100% | Undefined, empty reform membership |
| T_B = 0, T_R > 0 | Undefined | Undefined, empty baseline membership |
| Both totals zero | Undefined | Undefined |
| W_R = W_B > 0 with positive baseline mean | U = R | U = R |

Also test:

- One undefined draw makes across-draw mean and SD undefined; report defined-draw count.
- Undefined halves exclude the split seed; fewer than two usable seeds gives undefined floor.
- U equals all-alive mean-ratio change and is invariant to adding double-zero persons.
- Reject mismatched persons and weights. Existing person check: `src/populace_dynamics/fra68_track/benefits.py:963–964`; weight equality is an additional v2 check.

### 12.9 Cross-cutting invariants

- No duplicate own benefit.
- Nonnegative components.
- Null-reform identity under every mechanism.
- Deterministic results independent of row order.
- No cache leakage or projection-state mutation.
- Under C0, no individual benefit rises in exercise 3 under any mechanism, extending E1’s property to S.
- S×R5 = L×R5; DS×R5 = D×R5; S×F6 = L×F6; DS×F6 = D×F6.
- DS equals D levels combined with S timing, independent of application order.

### 12.10 Differential tests

**Compare D against Track M’s statutory `history_pia` using the same disability-year argument e, birth year, parameters and history. D retains years through e and Track M through e−1. Let T be the top-N indexed sum without year e and Δ the increase in that sum when year e is included, with zero padding. Assert**

**AIME_D − AIME_M = floor((T+Δ)/(12N)) − floor(T/(12N)).**

**This difference may be zero even when Δ is positive. Compare PIAs only when their bend-point years also match. Separately test raw awards after age 62; do not equate Track M’s raw onset cutoff with D’s age-62-clamped eligibility cutoff.**

Sources: `src/populace_dynamics/ss/statutory_aime.py:363–365`; `src/populace_dynamics/min_benefit_track_m/rules.py:501–514`, `:630–662`; `src/populace_dynamics/cola_track_a/benefits.py:329`.

Required differential fixtures:

- **Nonflat fixture:** T = $24,000, Δ = $12,000, N = 7. Assert **428−285 = 143**, not $12,000.
- **Positive displacement, zero AIME difference:** b = 1960, e = 1990, one dollar earned in 1990, flat AWI, nonbinding ceiling. N = 7, Δ = $1, both AIMEs zero.
- **Raw award after 62:** b = 1960, raw award 2024, D eligibility e = 2022. Use invented history `{2022: 4200, 2023: 8400, 2024: 16800}`, flat AWI and nonbinding ceiling.
  - D retains through 2022, N = 35, indexing year 2020: AIME **10**.
  - Track M with aligned onset argument e = 2022 retains through 2021: AIME **0**. The same-e identity holds with Δ = 4,200.
  - Separately, Track M with raw onset 2024 retains through 2023: AIME **30**, using bend-point year 2024 rather than D’s 2022.
  - Assert cutoff and bend-point years directly. Do not apply the same-e one-year identity to the raw-onset comparison or assert direct PIA equality.
  - This is an invented helper/adapter fixture, not an extension of the registered real-data earnings window.

Additional differentials:

- L against `approximate_pia`: bit for bit.
- S’s baseline months-early count against `spouse_excess_months_early` for records L already pays (`src/populace_dynamics/fra68_track/reform.py:538–583`).

## 13. Forecasts, exposure and reporting

**Forecasts:**

- Register before outcome execution, conditional on public v1 results.
- Cover v2 values, changes from v1, D−L, S−L, DS−D and comparator gaps for both exercises, with point estimates and 80% intervals.
- Cover every registered alternative through an explicit table or fully specified forecasting rule.
- Do not reuse v1 blind intervals as v2 forecasts or describe observed union diagnostics as predictions.

**Participant-specific exposure disclosures:** every builder, reviewer, forecaster and the orchestrator records what they have read or seen, including:

- T and F;
- P and `EV/parity-phase2-plan-review-20260927.md`, which restate public values and diagnostics;
- `EV/dynasim-scorecard.md`;
- E1 §27 and its underlying real-data diagnostic record at `EV/fra68-membership-diagnostic-20260925/`;
- F:141 and E1:668;
- earlier-session exposure, including running or reading real-data diagnostics or artifacts;
- anything listed in `EV/RESTRICTED-FILES.md`.

**Publication:** publish every variant and attempt, including refusals and partial execution, retaining cumulative version history. Report v2 beside unchanged v1 with:

- draw SD and sampling floor;
- membership diagnostics by mechanism and row;
- S application, ordering, prior-claim, deferral and omitted-own-reduction counters;
- D proxy counters;
- comparator intervals and signed gaps for every computed row.

Preserve undefined outcomes and comparator-resolution qualifications. Further changes require another registration.

After the artifact commit, a validation lane rechecks existing seals. Builders do not open restricted material. A seal recheck verifies comparator integrity; it does not restore blindness.

## 14. Interpretation limits

A smaller gap demonstrates **implementation sensitivity, not DYNASIM’s mechanism**. This exercise cannot establish which averaging base, claiming response, DI computation or dual-entitlement implementation DYNASIM3 used. S’s application month is an assumption.

There is no acceptance threshold, parity claim or certification. This rerun does not validate forward earnings, an earnings test, comprehensive statutory coverage or unscored outcomes. No value or direction is stated for an output that no exercise has scored.

## 15. Changes to A1 and E1

1. **DI levels under D/DS:** statutory count replaces `approximate_pia` for DI records, superseding A1 §22/d074 decision 2(b) and E1 §22 ruling 3/d188 item (a) for these mechanisms under d479 (4). L/S retain legacy levels.
2. **Spouse excess under S/DS:** §5 replaces DI suppression, E1 §11 rule 3’s conversion count for DI-origin records, and pre-62 withholding with deferral. S also refuses spouse-only-first and ended-spell/re-award histories.
3. **C0 legacy exception:** unavailable under S/DS. Exercise 1 additionally checks unfiltered selected-component membership in both directions.
4. **Union rows U0–U2:** registered with U and §7 definedness.
5. **Joint projection and refusal:** shared slices, direct identity checks and one attempt record.
6. **Labels:** §2’s post hoc and claiming-response labels.

## 16. Decisions required before ratification

Each item is resolved in the text or explicitly open for Max.

1. **Supported D histories:** resolved by S1–S6/O1–O5. Pre-opening history remains an assumption.
2. **Refusal scope:** resolved—joint stop before tabulation; no dropping, substitution or fallback.
3. **Application function:** resolved in §§5.2–5.3—prior claim before DI entitlement, otherwise scheduled baseline conversion; July annual mapping; fixed across C0/C1/C2; deferral to 62. Opening receipt is a separately counted proxy.
4. **Membership guards:** resolved in §9, including exercise-1 checks before filtering.
5. **Fixed application versus E1 conversion rule — ruled (d513, 2026-09-28): keep H fixed.** Recommendation adopted: keep H fixed, including records converted in reform (§5.6 group 4). The alternative would retain E1 rule 3 for converted records and use H only while disabled, making application scenario-dependent.
6. **Opening DI without an opening record:** resolved default—retain and count Track A’s start-year proxy. Max may instead require refusal under a changed registered version.
7. **Structural pre-count — ruled (d513, 2026-09-28): authorized.** Max authorized one lane that computes only the frozen structural counts below, before outcome registration, under its own frozen protocol.
   - Count D-unsupported histories and S ordering classes on the real projection before outcome registration, **after freezing the check’s own protocol**.
   - Include S-refused earlier spells and opening-proxy applications.
   - Require Max’s explicit authorization and pre-execution recording of implementation, inputs, permitted count outputs and procedure.
   - Compute projection and counts only: no benefits, weight sums or tabulations. P:76 expressly permits “explicitly authorized structural checks”.
   - Re-awards are reachable (`src/populace_dynamics/engine/di_entitlement.py:13–18`, `:514–519`); their frequency is unknown without real data.
   - Cover only histories whose level D would request or whose record S would reach.
   - **Recommended:** authorize a lane computing nothing else; publish its attempt and counts; bind its protocol and record into issue #42 registration.
   - If any D-unsupported-history or S-refused-ordering count is nonzero, Max chooses between registering an attempt that will refuse and first registering the required extension as a new version. Ordinary ordering/proxy counts do not themselves imply refusal.
   - If unauthorized, omit the pre-count. The registered joint attempt retains every history and ordering refusal.
8. **D’s scope — ruled (d513, 2026-09-28): DI computation years only.** Should D also change death computations, ordinary retirement counts or cutoff? Recommended: no; isolate DI computation years. Any expansion requires separate registration.
9. **S filing assumption — ruled (d513, 2026-09-28): the §5.2 prior-claim/conversion function.** E1 §27 option 1 could support filing at first eligibility. Recommended: retain §5.2’s prior-claim/conversion function. First-eligibility filing would broaden the intervention.
10. **Union as primary:** resolved—no. D×F0 remains headline; U rows remain alternatives.
11. **Matrix scope:** resolved—68 tabulations; R6/F8 stay historical only.
12. **Ratification route — ruled (d513, 2026-09-28): explicit ruling on items 5, 7, 8, 9 and this version, then merge.** Recommended: explicit ruling on items 5, 7, 8, 9 and this version. Merge alone does not resolve the behavioral choices in 5 and 9.

## 17. Execution prerequisites

1. Max’s ratification.
2. Implementation in new modules, independently reviewed.
3. Every §12 implementation test passing, including properties and differentials, with CI green at the implementation commit.
4. Invented dry run of all 68 tabulations and forced-refusal attempt recording.
5. Structural pre-count only if explicitly authorized and separately frozen under §11.
6. Hashes for specification, implementation, inputs, parameter bundles, A1/E1 parameter blocks, statute source and POMS source records.
7. Participant-specific exposure record.
8. Registered and hashed conditional forecasts.
9. Posted issue #42 registration binding the complete package.
10. Execution at the registered commit and procedure, followed by artifact commit, validation-lane seal recheck and comparison memo.

## Appendix A. Earlier review item → where resolved

| Earlier review item | Resolution retained |
|---|---|
| 1. Scope excess-before-reduction by entitlement ordering | §5.4’s explicit scope and ordering table |
| 1. Separate ordering tests with amounts/refusal | §12.5 |
| 1. Own `PiaRecord` prerequisite; scope versus reachable error | §5.1 |
| 1. Retained own-benefit approximations | §5.5 |
| 2. Deterministic filing proxy | §5.2 |
| 2. Claim field, annual mapping, July, future conversion, missing dates, prior application | §5.2 |
| 2. Latest of application, age 62 and linked entitlement; fixed C0/C1/C2 application | §§5.2–5.3 |
| 2. Distinguish proxy from deemed filing | §5.7 |
| 3. Ordinary statutory count within retained approximations | §4.2 |
| 3. Helper’s actual checks and omissions | §§4.6–4.7 |
| 3. Overwritten award detection | §4.6; write at `di_entitlement.py:551` |
| 3. Explicit refusal, no dropping/substitution/fallback | §§4.6, 10 |
| 3. Exact event predicate | §4.6, S1–S6/O1–O5 |
| 3. Unobserved pre-opening history | §4.6; §16 item 1 |
| 4. Caller trace, including DI/death and Track M | §3.3 |
| 4. New DI branch, retained inputs/callers, separate caches | §4.3 |
| 4. Fixed baseline events with scenario relabelling and claim transforms | §3.3 |
| 4. Twenty projections once; direct identity enforcement | §3.2 |
| 5. Guards by mechanism/row/components | §9 |
| 5. Exact legacy conjunction | §9 |
| 5. Both membership directions refuse before tabulation | §12.7 |
| 5. Dime-floor boundaries | §§9, 12.7 |
| 6. Original fixtures and restricted monotonicity | §§12.1, 12.3 |
| 6. Nonflat AWI, binding ceiling, inclusive cutoff and bend points | §12.2 |
| 6. Integration coverage | §12.4 |
| 6. Replay/cache isolation | §12.6 |
| 6. Filing timing | §12.5 |
| 6. Exact U/R definedness | §7.2 |
| 6. Zero totals, double zeros and person/weight mismatch | §12.8 |
| 7. d479, separate mechanisms, joint exercises, unchanged v1 | §§1–2, 8, 11, 13 |
| 7. Stylized labels on F3/F4/U1/U2 | §2 |
| 7. E1 §27 date/version/commit, D quotation and empty-history correction | §§6.1, 6.3–6.4 |
| 7. Fixed headlines and no promotion | §8 |
| 7. Full issue #42 package | §11 |
| 7. Participant-specific and earlier-session exposure | §13 |
| 7. Decisions versus prerequisites | §§16–17 |
| 7. Repository-relative commit pin | Header |
| Citation audit: Track M cutoff | §4.3; §12.10 |
| Citation audit: statute hash | §4.1, rehashed |
| Blindness and unscored outcomes | §§6.4, 13–14 |
| Orchestrator arithmetic and matrix count | §§8, 12 |
| Orchestrator: remove temporary-worktree citations | Header and repository-relative citations |
| Orchestrator: expanded D scope stays open | §16 item 8 |

## Appendix B. Verification, exposure and read record

This revision used source inspection, three parallel verification assignments and in-memory invented arithmetic. Checks passed for DI counts, the nonflat-AWI mutations, floored AIME differences, offset-fixture levels, filing amounts, dime boundaries, post-62 cutoff examples and the 68-row count.

No implementation or repository test suite was run. No real-data projection, benefit computation or tabulation was performed. No restricted comparator material was opened. The assigned workspace remained unchanged; no files or commits were created.

The revision was exposed to public T/F results, P and excerpts of its review, and E1’s recorded diagnostic discussion. The underlying membership-diagnostic files were not opened. Participant-specific disclosures for execution remain required.

**Files read, fully or through excerpts/searches, by this revision’s team:**

- the machine's global agent-rules file (`AGENTS.md`).
- `EV/phase2-20260927/prompts/common.md`.
- `EV/RESTRICTED-FILES.md`.
- `EV/phase2-20260927/out/a2-spec-rev1.md`.
- `EV/phase2-20260927/out/a2-rev1-check.md`.
- `EV/track-a-oneshot-20260923/COMPARISON.md`.
- `EV/fra68-oneshot-reg15-20260925/COMPARISON.md`.
- `EV/parity-phase2-plan-20260927.md`.
- `EV/parity-phase2-plan-review-20260927.md`.
- The full statutory `source.txt` path in §4.1.
- Repository design files:
  - `docs/design/urban2010_cola_comparison.md`;
  - `docs/design/urban2010_fra68_comparison.md`.
- Repository source files:
  - `src/populace_dynamics/cola_track_a/benefits.py`;
  - `src/populace_dynamics/cola_track_a/runner.py`;
  - `src/populace_dynamics/cola_track_a/adapters.py`;
  - `src/populace_dynamics/cola_track_a/opening.py`;
  - `src/populace_dynamics/cola_track_a/config.py`;
  - `src/populace_dynamics/fra68_track/benefits.py`;
  - `src/populace_dynamics/fra68_track/runner.py`;
  - `src/populace_dynamics/fra68_track/reform.py`;
  - `src/populace_dynamics/fra68_track/config.py`;
  - `src/populace_dynamics/ss/statutory_aime.py`;
  - `src/populace_dynamics/ss/benefits.py`;
  - `src/populace_dynamics/ss/params.py`;
  - `src/populace_dynamics/engine/di_entitlement.py`;
  - `src/populace_dynamics/engine/di_entitlement_rates.py`;
  - `src/populace_dynamics/engine/claiming.py`;
  - `src/populace_dynamics/engine/loop.py`;
  - `src/populace_dynamics/engine/rng.py`;
  - `src/populace_dynamics/min_benefit_track_m/rules.py`;
  - `src/populace_dynamics/scenario_benefits.py`;
  - `src/populace_dynamics/claiming.py`;
  - `src/populace_dynamics/estimates/cola_age_profile.py`.
- `tests/ss/test_statutory_aime.py`.

Git metadata was inspected for HEAD, `cd7c790b`, `2f75012e`, `aea61e22`, workspace status and the unchanged A1/E1 files between the pinned commits.

**Official pages read:**

- [POMS RS 00615.260](https://secure.ssa.gov/poms.nsf/lnx/0300615260), displaying TN 42.
- [POMS GN 00204.035](https://secure.ssa.gov/poms.nsf/lnx/0200204035), displaying TN 166.

The prior revision recorded these raw-page hashes from its 2026-09-27 retrieval:

- RS 00615.260: `d938b1f5f4a13903fd7004326a3c8cf305d9a72af958551d900e5a132951f72c`.
- GN 00204.035: `a935727e4fda4b4f18906a6530aba109a5a396fff21c3d19b50d842bf7fb01da`.

Those historical raw-page hashes are retained as provenance; their archived bytes were not independently rehashed in this revision. The statute text hash was independently rechecked.

## Appendix C. Check item → where resolved

| Round-diff check item | Where resolved |
|---|---|
| **Exact edit 1:** D may affect own-input spouse/widow offsets and linked DI auxiliaries; equality only without changed DI inputs or for intact opening payments | §12.4 opening assertion |
| Active-DI recipient’s widow excess | §12.4 table and active-survivor fixture |
| Continuous-conversion recipient’s spouse and widow excess | §12.4 table and converted-recipient fixtures |
| Ordinary retirement/death levels distinguished from auxiliary payments | §§4.4–4.5 and §12.4 table |
| Opening disabled worker’s auxiliary: S qualification for DI-origin own record | §12.4 table |
| Invented unchanged ordinary linked-worker and decedent cases | §12.4 fixtures 1–3 |
| **Exact edit 2:** correct floored AIME difference | §12.10 formula |
| Positive indexed displacement can give zero AIME difference | §12.10 one-dollar fixture |
| Compare PIAs only with matching bend-point years | §12.10 |
| Separate raw awards after 62 from D’s clamped eligibility cutoff | §12.10 post-62 fixture |
| Recompute 428−285 = 143, rather than $12,000 | §12.10 nonflat differential |
| **Exact edit 3:** exercise-1 flags before baseline-zero filtering | §9 filtering boundary and guard table |
| Refuse both membership directions before any tabulation | §10 step 3 and §12.7 injected tests |
| **Exact edit 4:** assert only existing unlinked/outside-roster counters; missing record gives no payment | §12.5 unpaid cases |
| **Exact edit 5:** sole expressly authorized structural exception | §11 exact exception paragraph |
| Freeze structural implementation, inputs, count outputs and procedure before checking | §11; §16 item 7 |
| No benefit amounts, weight sums or tabulations; publish attempt/counts and bind registration | §11; §16 item 7 |
| Keep structural-check choice open for Max | §16 item 7; §17 item 5 |
| Precision: immutable baseline state **and cohort metadata** | §5.2 input-source definition |
| Precision: explicit `di_conversion_year` | §5.2 input q and integrity rule |
| Precision: null claim selects Q, without inferring active entitlement | §5.2 missing-date rule; §12.5 |
| Precision: age-65 linked worker tested under **both C1 and C2** | §12.5 moved-worker fixtures |
| Precision: normalize whitespace **and typographic quotation marks** | §4.1 |
| Precision: mutation result or indexing assertion, not necessarily distinct values | §12.2 |
| Review 1 preserved: ordering scope, direct-dispatch cases, amounts/refusals, own-benefit approximation, own-record prerequisite | §§5.1, 5.4–5.5, 12.5 |
| Review 2 preserved: deterministic H, July mapping, horizon/missing dates, prior application, timing gates, fixed application, deemed-filing distinction | §§5.2–5.3, 5.7, 12.5 |
| Review 3 preserved: retained approximations, actual helper checks, immutable-event predicates, overwritten awards, DI inheritance/death distinction, joint refusal and unobserved-history limitation | §§4.2–4.7, 10 |
| Review 4 preserved: caller traces, DI-only override, unchanged other callers and inputs, caches, baseline events/scenario labels, twenty shared projections and direct hashes | §§3.2–3.3, 4.3, 12.6 |
| Review 5 preserved: exact legacy conjunction, S/DS refusal, F6 exclusion, C1/C2 counting, no rounding exception | §§9, 12.7 |
| Review 6 preserved: original fixtures, nonflat AWI/ceiling/cutoff/bend points, restricted monotonicity, integration, replay/cache and filing tests | §§12.1–12.7 |
| Review 6 preserved: exact U/R definedness, zeros, double zeros, person/weight mismatch, undefined draws and two-usable-seed floor | §§7.2–7.3, 12.8 |
| Review 7 preserved: separate mechanisms, joint exercises, unchanged v1, every attempt, conditional forecasts, no tuning and row labels | §§1–2, 8, 10–11, 13 |
| Review 7 preserved: E1 §27 date/version/commit, historical D quotation and empty-history correction | §§6.1, 6.3–6.4 |
| Review 7 preserved: fixed headlines/order, no distance-based promotion, full issue #42 package and participant-specific exposure | §§8, 11, 13 |
| Review 7 preserved: decisions separated from prerequisites; items 5, 7, 8, 9 and 12 open | §§16–17 |
| Arithmetic audit: original counts/payments, 68 tabulations, dime boundary, definedness and corrected differentials | §§8, 12; Appendix B verification |
| Citation audit: full commit pin, unchanged A1/E1, decisive Track M cutoff, verified statute hash and accurate POMS provenance | Header; §§4.1, 4.3, 12.10; Appendix B |
| Orchestrator: expanded D scope remains Max’s decision; temporary worktree links removed | §16 item 8; repository-relative citations |
| Blindness: no unscored value/direction, restricted access or real-data computation during revision | §§6.4, 13–14; Appendix B |
