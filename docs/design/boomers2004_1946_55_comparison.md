# Boomers 2004, 1946–55: specification for held-out target U2

- **Version:** `u2-draft-4` (milestone 1b, 2026-09-28; revised 2026-09-29 after the independent review): proposed amendments 1–6 in §16a, pending Max's ruling. Previous version: `u2-draft-3` (round 2).
- **Status:** decisions ruled for `u2-draft-3`. On 2026-09-28 Max approved the §16 defaults and ratification of that draft (d514, in chat). Per §20, the version becomes `u2-ratified-1` by the merge that completes §20 steps 2–5 and materializes the final parameter block; that merge needs no further ruling unless it changes this document's substance. `u2-draft-4` adds §16a, whose proposed amendments change substance, so each needs Max's ruling first. Not registered or authorized for execution.
- **Intended file:** `docs/design/boomers2004_1946_55_comparison.md`.
- **Specification identity:** `boomers2004_1946_55_uniform_cut`.
- **Target identity:** `U2`. Row identifiers are local to this specification: **row U2** means “no SSI response.”
- **Repository reference:** `9cee2423f048`.
- **Template:** `docs/design/boomers2004_uniform_cut_comparison.md`, version `u1-ratified-1`, SHA-256 `830b0ab4c18273563add529fecf21f843eb418996da741d087d785c4f882781f`.
- **Claim class:** static simulation on PSID-observed incomes. Observed income and wealth supply the inputs; annuitization, the benefit cut and SSI responses are mechanical counterfactual calculations.
- **Required output labels:** **PSID-realized outcomes (not a projection)**; **Python income concept (not Axiom)**; **mechanical incidence**.
- **Builder boundary:** no held-out comparator value or direction is stated or inferred. Section 18 records reading and exposure.

This specification inherits U1’s income concept, statistics, uncertainty methods and comparison rules, with the explicit amendments below. U1’s specification, registered behavior, parameter captures and committed artifacts remain unchanged.

## 1. Target

The source is Butrica and Uccello, *How Will Boomers Fare at Retirement?*, AARP Public Policy Institute report 2004-05, May 2004.

The target comprises fifteen rows in the **“1946-55”** column under **Birth Cohort** in:

- Table 19, *Adjusted Poverty Rates at Age 67*: baseline.
- Table 21, *Adjusted Poverty Rates at Age 67, Assuming 13 Percent Reduction in Social Security Benefits*: reform.

The headline is the reform-minus-baseline change in adjusted poverty for `all`, using model row U0. Baseline and reform levels are secondary statistics. Section 9 defines seven primary and eight secondary cells. The other twenty-one Report rows are named omissions.

The column is printed '1946-55' (hyphen, abbreviated end year; cleared extract line 49). The cleared U2 statement's '1946–55' is the body-text form of the same column.

The source identifies DYNASIM3. This exercise tests transfer of the inherited static measurement to another cohort. It does not test the Dynamics projection engine or establish DYNASIM4 parity.

The cleared definitions establish individual observations when each person reaches age 67; inclusion of spouses’ resources for married individuals; official Census thresholds, including the 65-and-over thresholds; annuitization of 80 percent of financial assets with a 50 percent survivor annuity for married couples; exclusion of imputed rent from poverty income; and the uniform 13 percent Social Security reduction beginning in 2004, without behavioral response.

Poverty-family membership, nonspouse co-resident income, poverty-income tax treatment and SSI recomputation remain incompletely specified by the Report. Their treatment here is an explicit modeling convention.

The validation-only lane has confirmed the column, the fifteen row mappings and printed precision, and published a definition-only statement: `EV/u2-target-availability-cleared-20260928.md` (`2ffa3092…`), cleared 2026-09-28 by an independent values scan (0 genuine leaks). §§1, 9 and 10a cite it.

## 2. Sources and verification status

`EV` and `EVID` both denote the orchestrating session's evidence folder (`dynasim-parity-20260909`, outside this repository).

`PSID` denotes the staged PSID directory (the one `POPULACE_DYNAMICS_PSID_DIR` points to).

`S` denotes `src/populace_dynamics/` in the assigned repository. Repository citations below refer to `9cee2423f048`. Verification statuses inherited from rev1 are retained; §18 distinguishes earlier reading from this round’s source checks.

| Source | Use | Status |
|---|---|---|
| U1 specification at the header’s hash | Inherited methods and compatibility contract | Read; rehashed |
| `EV/RESTRICTED-FILES.md` | Reading boundary and exposure ledger | Read first |
| `EV/exercise2-definitions-cleared-20260924.md` | Report definitions and labels | Read; rehashed to `a3978b683b4275424b6d12e9fe45f021fae277ccf9731a7883952564b6ed0384` |
| `EV/u2-target-availability-cleared-20260928.md`, SHA-256 `2ffa3092d297418c58868f7e5326c3e4c8047b129171b40b66fde5ee07702211` | Rows, tables, units, rounding, cohort | Read in full; rehashed and matched |
| `EV/heldout-feasibility-20260927.md` | Observation calendar, feasibility and exposure | Read |
| `EV/heldout-target-pick-20260928.md` | Target choice and process | Read |
| Draft and adversarial review | Earlier revision requirements | Rev1 reading retained in §18 |
| `EV/phase2-20260927/out/u2-spec-rev1.md` and `u2-rev1-check.md` | Round-2 revision requirements | Read; R1–R8 addressed |
| Four authorized public result memos | Related-result exposure and precedent | Draft-1 exposure retained in §18 |
| Repository specification, readers, estimators, runners and tests | Implementation contract | Relevant sections inspected |
| Staged PSID setup/format files and selected codebook entries | Metadata and mapping adjudication | Partial verification, §§3–4 |
| Committed Census and life-table captures | Reusable parameters | Hashes reverified, §§5–6 |
| Later SSI capture | U2 SSI parameters | **TO VERIFY**; capture not yet created |
| Official COLA notice metadata | Annual SSI source citations | Citations verified; downloaded bytes and parameter cross-checks remain **TO VERIFY** |

No Boomers Report PDF was opened for this revision. Definitions come from the cleared files and the pinned U1 specification.

“Label-verified” does not mean that routing, missing-value codes, units and all uses of a variable have been adjudicated. Unverified items remain **TO VERIFY** and block registration where required.

## 3. Population, identification and roles

### Primary row U0: exact age 67

Only even income years are observed within the cohort’s age-67 calendar span, 2013–2022.

| Birth year | Income year | Interview wave | Multiplier |
|---:|---:|---:|---:|
| 1947 | 2014 | 2015 | 1 |
| 1949 | 2016 | 2017 | 1 |
| 1951 | 2018 | 2019 | 1 |
| 1953 | 2020 | 2021 | 1 |
| 1955 | 2022 | 2023 | 1 |

These are planned calendar cells, not observed counts. U0 represents five birth years at exact age 67.

### Alternative row U1: all ten birth years

Odd birth years use their U0 observation. Even birth years use half-weighted age-66 and age-68 observations.

| Birth year | Age 66: income year / wave | Age 68: income year / wave | Multiplier per observation |
|---:|---|---|---:|
| 1946 | 2012 / 2013 | 2014 / 2015 | 0.5 |
| 1948 | 2014 / 2015 | 2016 / 2017 | 0.5 |
| 1950 | 2016 / 2017 | 2018 / 2019 | 0.5 |
| 1952 | 2018 / 2019 | 2020 / 2021 | 0.5 |
| 1954 | 2020 / 2021 | 2022 / 2023 | 0.5 |

The plan contains fifteen birth-year/wave cells covering ten birth years. Planned multipliers sum to one for each birth year.

Unlike U1’s old-cohort endpoint exception, 1946 receives both observations: the required 2013 wave is staged and already supported. A missing observation retains its disposition; its weight is not transferred to another observation. There is no birth-year population equalization or subsequent normalization.

### Row-set amendment

U0-F and the eight `-F` alternatives are omitted from U2. In U1 they isolated the contrast between wealth supplements and family-file wealth. Every U2 observation wave uses family-file wealth, so translating them into a restriction to births 1951/1953/1955 would introduce an unrelated population contrast.

U2 therefore has **ten rows**, listed in §11. The review’s parenthetical “11 rows” is an arithmetic error: nineteen minus nine is ten. U1 retains all nineteen registered rows.

There is no automatic headline fallback.

### Identification, weights and design frames

Use the common support-wave set:

```text
2013, 2015, 2017, 2019, 2021, 2023
```

Use `estimates.career.derive_birth_years` with its existing history inputs and precedence. For target-person identification, seed from the earliest positive-weight, in-family presence in this common set, using the inherited income-year/age coordinate. Derive births once and reuse them across U2 rows.

The parameter is:

```text
seed_wave_rule = earliest_presence_in_common_support_waves
```

This is an explicit departure from U1, whose rule is `earliest_presence_wave` over each row’s observation waves. Support waves can affect identification; they cannot add observations or sampling-design units to a row.

Preserve:

- In-family sequence codes 1–20 and positive wave-specific core/immigrant individual cross-section weights.
- Counted dispositions for institutions, movers-out, decedents and other nonresponding-family sequences.
- Observation weight equal to the reporting wave’s cross-section weight times its planned multiplier.
- No calibration, outcome-driven exclusion or discretionary removal of immigrant refreshment samples.
- Family-unit identity `wave × 100000 + interview`, subject to identifier-domain and uniqueness checks.
- Legal marital status at income-year end, with separated counted as married.
- Unresolved marital states excluded and counted in marital cells while retained in `all` and the applicable sex cell.

The weight construction and immigrant-refreshment coverage must be documented before registration.

### Relationship-code amendment

From 2015 the relationship codes change meaning (formats lines cited). The U1 rules for code 90 and for a 'wife' are **not** carried over. A pre-registration amendment must define: the income role and spouse-slot membership of code 20 of either sex and of code 90 (uncooperative legal spouse); annuity lives and marital resolution for both; and label tests for codes 10, 20, 22, 88 and 90 in every wave, 2013–2023, plus code 92’s absence in 2013/2015 and presence in 2017–2023. Code 92’s income role, annuity treatment and marital-resolution rule are also explicit below.

This draft supplies that amendment:

| Relationship | Income role and spouse income slot | Primary annuity and marital resolution |
|---|---|---|
| 10 | Head/reference person | Head/reference-person annuity life |
| 20 | Spouse income role, irrespective of sex; occupies the designated family-file spouse slot | Co-resident legal-spouse life; eligible for relationship-based marital resolution |
| 22 | Designated cohabitor occupying the family-file spouse income slot | Does not become a legal-spouse annuity life merely by occupying that slot; retains legal marital status |
| 90 | OFUM income role; does not occupy the standard spouse income slot; uses family-unit basis in row U4 | Co-resident legal-spouse life; eligible for relationship-based marital resolution |
| 92 (2017–2023 only) | OFUM income role; does not occupy the spouse income slot | Not a legal-spouse annuity life; retains legal marital status; never resolves a head's marital history as married |

The 2013 meanings remain those documented for 2013. From 2015, legacy implementation identifiers such as `wife`, `wife_present` and `head_wife` name an income slot, not a sex.

Code 92 does not exist in 2013 or 2015. From 2017 it is 'Uncooperative partner of Reference Person' (`IND2023ER_formats.sps` lines 24478, 26005, 27587, 29183). Its OFUM income routing is **TO VERIFY** from family-file documentation under the same standard as the 2015 male code-20 blocker.

Code 90’s OFUM assignment is an explicit U2 interpretation. Its 2015 full definition concerns inability or unwillingness to be designated Head; the 2017–2023 full definitions concern designation as Reference Person **or Spouse**. Do not describe these definitions as identical. The claim that code 90 is excluded from the family-file spouse income slot and included in OFUM totals is **TO VERIFY** from 2015–2023 family-file documentation before registration, like the 2015 male code-20 blocker (rev1 line 156); it may not be established from counts.

For the primary annuity, identify the unique in-family code-10 person and unique co-resident legal spouse, code 20 or 90. Use each person’s recorded sex and derived income-year age; never infer sex from role. A uniquely paired head and code-20/code-90 spouse resolves otherwise unresolved marital histories as married, with each identifying the other as spouse. Resolved history retains its inherited precedence. Missing or ambiguous pairing remains unresolved and counted.

The SSI income units follow the income slots, not annuity pairing. Under the declared interpretation, codes 90 and 92 are included through OFUM totals under the family basis, subject to documentary routing confirmation before registration; they are not silently transferred into the head/spouse SSI unit. Code 92 uses the family basis in row U4.

**Source-verification blocker:** the 2015 individual format calls code 20 “Legal Spouse,” but the family codebook’s spouse-sex variable ER60020 lists only female; ER60019 also retains older female-head inapplicability wording. Consequently, family-file income routing for a male code-20 record in 2015 remains **TO VERIFY**. Source documentation must resolve this before registration. Counts cannot establish routing, justify assuming such records absent, or waive this blocker. Any resulting change to the declared interpretation requires an explicit reviewed amendment.

Relevant codebook entries are:

- `IND2023ER_codebook.pdf`: ER34303, printed pages 977–978; ER34503, printed pages 1095–1097; corresponding ER34703, ER34903 and ER35103 entries.
- `FAM2015ER_codebook.pdf`: ER60019 and ER60020, printed page 6.
- `FAM2017ER_codebook.pdf`: ER66019, printed page 6; ER66020, printed page 7.
- `FAM2023ER_codebook.pdf`: ER82020, printed page 6; inherited wording also requires care.

### Mandatory relationship-label tests

Check every entry below after case folding and whitespace normalization. Require the documented prefixes; do not replace them with a generic “spouse” match.

| Wave | Relationship variable | Code 10 prefix | Code 20 prefix | Code 22 prefix | Code 88 prefix | Code 90 prefix | Code 92 prefix |
|---:|---|---|---|---|---|---|---|
| 2013 | ER34203 | `Head in 2013` | `Legal Wife in 2013` | `"Wife"--female cohabitor` | `First-year cohabitor of Head` | `Legal husband of Head` | must be absent |
| 2015 | ER34303 | `Head in 2015` | `Legal Spouse in 2015` | `Partner--female cohabitor` | `First-year cohabitor of Head` | `Uncooperative legal spouse of Head` | must be absent |
| 2017 | ER34503 | `Reference Person in 2017` | `Legal Spouse in 2017` | `Partner--cohabitor` | `First-year cohabitor of Reference Person` | `Uncooperative legal spouse of Reference Person` | `Uncooperative partner of Reference Person` |
| 2019 | ER34703 | `Reference Person in 2019` | `Legal Spouse in 2019` | `Partner--cohabitor` | `First-year cohabitor of Reference Person` | `Uncooperative legal spouse of Reference Person` | `Uncooperative partner of Reference Person` |
| 2021 | ER34903 | `Reference Person in 2021` | `Legal Spouse in 2021` | `Partner--cohabitor` | `First-year cohabitor of Reference Person` | `Uncooperative legal spouse of Reference Person` | `Uncooperative partner of Reference Person` |
| 2023 | ER35103 | `Reference Person in 2023` | `Legal Spouse in 2023` | `Partner--cohabitor` | `First-year cohabitor of Reference Person` | `Uncooperative legal spouse of Reference Person` | `Uncooperative partner of Reference Person` |

Sources: `PSID/ind2023er/IND2023ER_formats.sps`, blocks beginning at lines 21917, 22968, 24448, 25975, 27557 and 29153. Code-88 lines are 21945, 22996, 24476, 26003, 27585 and 29181; code-92 lines are 24478, 26005, 27587 and 29183, with absence checked across the complete 2013 and 2015 blocks.

The existing verifier’s docstring mentions only 10/20/22, but its actual prefix dictionary and loop already include 90 (`S/cohorts/age67.py:351`, `:635`). The required change is wave-specific semantics and expectations.

### Annuitant ages

Preserve birth-year derivation for qualifying in-family heads and spouses, including zero-weight spouses, and marriage-history spouses. Use the common support set. If derivation does not resolve an annuitant’s age, apply and count the inherited wave-age fallback.

The inherited administrative birth-support selection includes codes 10, 20, 22, 88 and 90 (`S/cohorts/age67.py:327`, `:946`). Inclusion in that support selection does not confer legal-spouse annuity status. Code 88’s documented label change is verified and tested above; any remaining routing or substantive use beyond inherited administrative support remains **TO VERIFY**. Code 92 is absent from the inherited administrative selection and is not added to it by this amendment; its explicit OFUM rule does not confer legal-spouse annuity status.

### Staged materials

Filename listings establish the following staging; raw-data contents were not read.

| Directory | Materials |
|---|---|
| `PSID/family/2013/` | Family setup files, raw file, codebook, archive, introduction and readme |
| `PSID/family/2015/` | Same categories |
| `PSID/family/2017/` | Same categories |
| `PSID/family/2019/` | Same categories; codebook filename is lowercase `fam2019er_codebook.pdf` |
| `PSID/family/2021/` | Same categories plus `FAM2021ER_formats.{do,sas,sps}` |
| `PSID/family/2023/` | Same categories plus `FAM2023ER_formats.{do,sas,sps}` |
| `PSID/ind2023er/` | Individual setup files, codebook, introduction, readme and `IND2023ER_formats.{do,sas,sps}` |
| `PSID/mh85_23/` | Marriage-history setup files, codebook, formats, introduction and readme |
| `PSID/documentation/capture1/` | Questionnaires and user guides for 2013–2023 odd waves; cross-section-weight documentation for 2013–2021 odd waves; family and individual QxQs including 2013 and 2015 |

The 2013 documentation includes `q2013.pdf`, `UserGuide2013.pdf`, `cross_sec_weights_13.pdf`, `fam2013_QxQs.pdf` and `qxq2013_QxQs.pdf`.

**`cross_sec_weights_23.pdf` is absent** and is on the future download list.

### Individual anchors

| Wave | Interview | Sequence | Relationship | Interview age | Reported birth year | Cross-section weight |
|---:|---|---|---|---|---|---|
| 2013 | ER34201 | ER34202 | ER34203 | ER34204 | ER34206 | ER34269 |
| 2015 | ER34301 | ER34302 | ER34303 | ER34305 | ER34307 | ER34414 |
| 2017 | ER34501 | ER34502 | ER34503 | ER34504 | ER34506 | ER34651 |
| 2019 | ER34701 | ER34702 | ER34703 | ER34704 | ER34706 | ER34864 |
| 2021 | ER34901 | ER34902 | ER34903 | ER34904 | ER34906 | ER35065 |
| 2023 | ER35101 | ER35102 | ER35103 | ER35104 | ER35106 | ER35265 |

The 2013 mapping is inherited from U1. Later anchor identities and labels are verified. Birth-month anchors ER34306 for 2015 and ER34505 for 2017 are also label-verified. Birth-year label citations in `IND2023ER.sps` are lines 2950, 3093, 3244, 3408 and 3573.

Also label-verified: sampling-error stratum **ER31996**, cluster **ER31997**, and sex **ER32000**.

Complete sentinel domains, persistent-identifier semantics, weight construction and any additional history anchors remain **TO VERIFY** where not established by the inherited reader or staged metadata review.

## 4. Income concept and mapping verification

Retain U1’s pre-tax family money-income basis:

```text
B = money income
    − reported asset income selected for replacement
    − head/reference-person annuity and IRA income
    − imputed farm asset income
    + asset annuity
```

Under the primary family basis:

- Money income is `TOTAL FAMILY INCOME`.
- Remove head/reference-person and spouse rent, dividends, interest, trusts/royalties and business asset income, plus OFUM asset income.
- Remove head/reference-person annuity and IRA income.
- Retain spouse and OFUM pension/annuity income under the inherited convention. More detailed later fields do not silently change the concept.
- Remove half of positive farm income and all of a farm loss; preserve the inherited business labor/asset convention.
- Exclude imputed rent.
- Use WEALTH1, excluding home equity, as primary financial assets.

Row U4 uses the head/reference-person-and-spouse basis for those income roles; OFUM members retain the family basis. Its spouse-presence flag refers to the designated income slot in §3. Annuity lives remain separately defined.

### Verified composite entries

| Wave | Total family income | WEALTH1 | Census needs standard |
|---:|---|---|---|
| 2015 | ER65349; codebook PDF p. 1977 | ER65406; p. 1992 | ER65449; p. 2011 |
| 2017 | ER71426; p. 2030 | ER71483; p. 2045 | ER71528; p. 2066 |
| 2019 | ER77448; p. 2015 | ER77509; p. 2030 | ER77589; p. 2051 |
| 2021 | ER81775; p. 1379 | ER81836; p. 1394 | ER81916; p. 1415 |
| 2023 | ER85629; p. 1297 | ER85690; p. 1312 | ER85770; p. 1333 |

The inherited draft’s codebook checks establish income year = wave − 1 and the seven-aggregate total-income identity: head/spouse taxable income; head/spouse transfers; OFUM taxable income; OFUM transfers; and separate head, spouse and OFUM Social Security totals.

Separate component definitions and code domains remain **TO VERIFY**.

### Required income manifests

For each wave, independently verify exact IDs, labels, positions, widths, units, reference periods, universes, sentinels, loss permissions, accuracy/imputation flags and reconciliation identities for:

| Group | Required contents |
|---|---|
| Money-income aggregates | The seven aggregates and total family income |
| Social Security and SSI | Separate reference-person, spouse and OFUM totals; indicators where used |
| Labor, farm and business | Labor coverage, business labor/asset split and losses |
| Asset income | Rent, dividends, interest, trusts/royalties, business assets and OFUM assets |
| Retirement income | Reference-person annuity/IRA fields and spouse/OFUM combinations |
| Other transfers | Reconciliation and full-static SSI components |
| Family composition | Size, children, ages, sex, spouse slot and family join |

Later component IDs not explicitly verified in this specification remain **TO VERIFY**. Never infer an ID by extrapolating another wave’s numbering.

### Wealth and debt

The documented WEALTH1 identity has seven asset components in 2015/2017 and eight from 2019. The later split separates checking/savings/money-market balances from CDs, bonds and Treasury bills.

| Wave | Checking/savings/money market | CDs/bonds/Treasury bills |
|---:|---|---|
| 2019 | ER77457 | ER77461 |
| 2021 | ER81784 | ER81788 |
| 2023 | ER85638 | ER85642 |

These separately inspected items are imputed interview-time balances.

| Wave | Asset components | Debt components |
|---:|---|---|
| 2015 | ER65352, ER65358, ER65362, ER65368, ER65370, ER65374, ER65378 | ER65354, ER65364, ER65382, ER65386, ER65390, ER65394, ER65398, ER65402 |
| 2017 | ER71429, ER71435, ER71439, ER71445, ER71447, ER71451, ER71455 | ER71431, ER71441, ER71459, ER71463, ER71467, ER71471, ER71475, ER71479 |
| 2019 | ER77451, ER77457, ER77461, ER77465, ER77471, ER77473, ER77477, ER77481 | ER77453, ER77467, ER77485, ER77489, ER77493, ER77497, ER77501, ER77505 |
| 2021 | ER81778, ER81784, ER81788, ER81792, ER81798, ER81800, ER81804, ER81808 | ER81780, ER81794, ER81812, ER81816, ER81820, ER81824, ER81828, ER81832 |
| 2023 | ER85632, ER85638, ER85642, ER85646, ER85652, ER85654, ER85658, ER85662 | ER85634, ER85648, ER85666, ER85670, ER85674, ER85678, ER85682, ER85686 |

Composite membership is verified. Except for the six separately inspected account entries, individual component definitions, accuracy flags, sentinels, loss permissions and top codes remain **TO VERIFY**.

Implement each wave’s documented identity, including separate farm/business and other-real-estate debt. Do not double-subtract debt already represented in a net component.

### Employer DC: row U7

Retain the inherited scope: observed employer DC balances outside IRAs for the reference person and spouse income slot.

All later-wave employer-DC variable IDs, widths, codes and routes remain **TO VERIFY** at codebook/questionnaire level. Verify current-job account and combined plans; both previous-employer slots; amounts left to accumulate; IRA rollovers; formula/account/combined/unknown-plan routes; the checkpoint corresponding to U1’s P62A branch; duplicate questions; nonresponse; top codes; brackets; and respondent universes.

Use questionnaires as well as codebooks. Preserve exclusions of IRA rollovers, duplicate combined-plan accounts and off-route amounts; count unreported amounts as zero with dispositions. Do not extend `_NEW_CODES_WAVES` by assumption.

### Pre-registration mapping pass

Before registration:

1. Pin source release, filenames and hashes.
2. Complete variable and routing manifests.
3. Cross-check setup formats independently.
4. Resolve questionnaire routing and the §3 role-source inconsistencies.
5. Test invented fixed-width records covering normal values, losses, sentinels and every route.
6. Obtain independent mapping review.
7. Perform the authorized structural, join, reconciliation and F17 component pass; resolve failures before the forecast and registration.

As in U1 (plan §8), before registration and counts only: structural counts, dispositions, join and reconciliation counts, and the F17 component summaries. No income concept, threshold assignment or poverty status. Real-data statistics follow registration.

Here “counts only” governs the structural/reconciliation pass. The specifically named F17 summaries in §9 are the inherited exception allowing component means, shares and quantiles. “Threshold assignment” means poverty-threshold assignment; the inherited SSI component comparison with federal benefit rates remains allowed.

This draft imposes **no stricter prohibition on pre-registration component checks than U1**. It does impose explicit completion gates for new mappings, role semantics and parameter identity, because those are new inputs. Those gates are satisfied before the one-shot.

No real-data check was performed for this revision.

## 5. Annuity

Retain:

```text
annuity = 0.8 × max(financial assets, 0) / annuity price
```

Use a real annuity-immediate, three percent real interest, no load, the §3 family-head/legal-spouse lives, income-year ages and inherited terminal closure. A co-resident legal couple receives a joint annuity with a 50 percent survivor benefit. Two percent interest remains a reported, unscored sensitivity.

For survival probability \(p_x(t)\),

\[
a_x=\sum_{t\ge1}(1.03)^{-t}p_x(t).
\]

At the registered 50 percent survivor share, the joint price is \(0.5(a_x+a_y)\). Preserve the inherited independent-lives implementation.

| Use | Source | SHA-256 |
|---|---|---|
| Primary | `data/external/nchs_life_tables_2000.json` | `067ac331d26a56f5f6c120e361771be1c890e74c412b5561ca45c87302059142` |
| Row U9 | `data/external/tr2008/ssa_2008_vintage.json`, period table 2004 | `78c5e55b29615e21f60dc6345572ab06206245246394e2a2791d82358c45d7d7` |

Hashes were reverified; **provenance inherited from U1 §2; no download**. Preserve the SSA loader’s companion-file verification.

Retain the NCHS closure at age 100 and SSA table through age 119. These fixed mortality assumptions are not replaced with later tables.

## 6. Poverty thresholds

Use:

```text
data/external/census_poverty_thresholds_1982_2022.json
SHA-256 288399c475ae3ff02e6d8367425ee0a568b50d239da5656f24d0d2dfafabfb53
```

The capture contains the required full weighted-average and size-by-children tables. Use its full schema; Track M’s specialized one-person-65+ accessor is insufficient.

The threshold is the official Census threshold for ages 65 and over, varying by family size, **indexed to consumer prices (cleared U2 statement)**.

Preserve:

- Primary: income-year weighted-average threshold by family size.
- Sizes one and two: 65-and-over rows regardless of actual reference-person age.
- Sizes three through eight: the corresponding size row; nine or more: nine-plus.
- Row U10: size-by-related-children matrix, using PSID children-in-FU as the inherited proxy.
- Row U8: PSID Census needs standard, with its composition-change and householder-age conventions.
- Poverty: income **strictly below** the threshold.

Require coverage for income years 2012, 2014, 2016, 2018, 2020 and 2022.

**Workbooks pinned in `CENSUS_WORKBOOK_SHA256`; captured under d194 (thresh03–12) and d279 (the rest).** See `scripts/capture_track_u_parameters.py:244`.

**Income year 2012 must equal U1's capture (`dc21a787…`). Refuse on any difference.** The full U1 hash is:

```text
dc21a78736f5085872cf56c9cf291258034c1293572b77455cba689a1ed0eec5
```

Require equality of every 2012 weighted average, all-ages weighted average and matrix entry. This metadata comparison was performed in memory and matched. The one-person-65+ 2012 parameter is 11,011 in both captures.

For 2022, preserve `weighted_average_unit_dollars: 10`. Read stored dollar amounts as captured; do not multiply them by ten again or invent finer precision.

No new Census download is required.

## 7. Benefit cut

Retain:

```text
cut_rate = 0.13
cut_start_year = 2004
cut_applies = birth_year + 67 >= cut_start_year
R = B − cut_rate × included Social Security + SSI response
```

The base is all Social Security of the selected income unit. There is no behavioral response.

The trigger uses the member’s age-67 year, including observations at ages 66 and 68. Every planned U2 birth satisfies that trigger by calendar arithmetic. This is a policy-assignment property, not a statement about a Report cell.

The old cohort’s uncut endpoint exception does not arise. Row U6 remains withdrawn.

## 8. SSI response and parameter capture

### Primary: existing recipients

For an SSI unit with reported baseline SSI:

```text
G = 12 × monthly general exclusion
fall = max(0, S − G) − max(0, (1 − c) × S − G)
offset = min(fall, max(0, 12 × monthly FBR − reported SSI))
```

Otherwise its primary offset is zero. There is no new enrollment.

Preserve these approximations:

- Reference-person and spouse income slots form one unit.
- Couple FBR applies when both receive SSI; otherwise individual FBR.
- Spouse-slot Social Security is fully attributed.
- OFUM SSI totals form one individual unit under the family basis.
- Annual accounting uses twelve times the January FBR.
- Reported SSI may include state supplements.

Row U2 has no SSI response.

### Row U3: full-static response

Retain the existing-recipient offset. Additionally enroll a head/spouse unit only when it has no reported SSI, is baseline income-ineligible, becomes income-eligible under the cut, and satisfies the inherited resource proxy:

```text
resources = max(0, WEALTH1 − vehicles)
```

Let \(C\) and \(C'\) be baseline and reform annual countable income, and \(F\) the applicable annual FBR. New enrollment requires \(C\ge F\), \(C'<F\), and eligible resources; its amount is \(F-C'\).

Apply the general exclusion to unearned income first, any remainder to earnings, then the earned exclusion and earned-share exclusion. Preserve U1’s component selection: transfers excluding SSI, TANF and other welfare, plus Social Security; labor, farm and business-labor income for earnings; and the inherited omission of asset-income components from this calculation.

Spouse-slot presence determines the couple convention for new enrollment. OFUMs do not newly enroll. This approximation is not asserted to bound the Report’s simulation.

### Separate U2 capture

Proposed file:

```text
data/external/track_u2_ssi_parameters_2012_2022.json
```

**Capture, source revision, source hashes and final SHA-256: TO VERIFY.**

Use a separate configuration covering **exactly every year 2012–2022**. Preserve U1’s global `YEARS` and existing capture behavior.

Source paths under `policyengine_us/parameters/gov/ssa/ssi/`:

- `amount/individual.yaml`
- `amount/couple.yaml`
- `income/exclusions/general.yaml`
- `income/exclusions/earned.yaml`
- `income/exclusions/earned_share.yaml`
- `eligibility/resources/limit/individual.yaml`
- `eligibility/resources/limit/couple.yaml`

Refuse a missing, empty or `"unknown"` source revision. Record the exact revision, seven source hashes, effective dates, January-1 selection rule, references, generator and capture digest.

Apply the existing `constant()` check across all eleven years separately to general exclusion, earned exclusion, earned share excluded and both resource limits. Variation requires an explicit schema/method amendment; do not silently select one year’s value.

The complete 2012 parameter projection must equal U1’s capture, excluding provenance-envelope differences:

| Parameter | U1 2012 value |
|---|---:|
| Individual monthly FBR | 698 |
| Couple monthly FBR | 1,048 |
| Monthly general exclusion | 20 |
| Monthly earned exclusion | 65 |
| Earned share excluded | 0.5 |
| Individual resource limit | 2,000 |
| Couple resource limit | 3,000 |

Preserve U1’s file and hash:

```text
data/external/track_u_ssi_parameters.json
79e641a10d95afba81c8d831852fb52ef0a801e7175e06df17e6cc7cc3e3c523
```

### Independent annual source verification

Check January FBR parameters against the annual *Cost-of-Living Increase and Other Determinations* notices.

| SSI year | Federal Register citation |
|---:|---|
| 2012 | [76 FR 66111, October 25, 2011](https://www.govinfo.gov/content/pkg/FR-2011-10-25/pdf/FR-2011-10-25.pdf) |
| 2013 | [77 FR 65754, October 30, 2012](https://www.govinfo.gov/link/fr/77/65754) |
| 2014 | [78 FR 66413, November 5, 2013](https://www.govinfo.gov/content/pkg/FR-2013-11-05/pdf/FR-2013-11-05.pdf) |
| 2015 | [79 FR 64455, October 29, 2014](https://www.govinfo.gov/content/pkg/FR-2014-10-29/pdf/FR-2014-10-29.pdf) |
| 2016 | [80 FR 66963, October 30, 2015](https://www.govinfo.gov/content/pkg/FR-2015-10-30/pdf/FR-2015-10-30.pdf) |
| 2017 | [81 FR 74854, October 27, 2016; official contents listing](https://www.govinfo.gov/content/pkg/FR-2016-10-27/pdf/FR-2016-10-27-FrontMatter.pdf) |
| 2018 | [82 FR 59937, December 15, 2017; corrected republication](https://www.govinfo.gov/content/pkg/FR-2017-12-15/pdf/2017-27105.pdf) |
| 2019 | [83 FR 53702, October 24, 2018; SSA republication and citation](https://www.ssa.gov/OP_Home/comp2/G-APP-B.html) |
| 2020 | [84 FR 56515, October 22, 2019](https://www.govinfo.gov/content/pkg/FR-2019-10-22/html/2019-22921.htm) |
| 2021 | [85 FR 67413, October 22, 2020](https://www.govinfo.gov/content/pkg/FR-2020-10-22/pdf/FR-2020-10-22.pdf) |
| 2022 | [86 FR 58715, October 22, 2021](https://www.govinfo.gov/content/pkg/FR-2021-10-22/html/2021-23031.htm) |

Citation metadata was checked online in rev1 on 2026-09-28 UTC. It does not establish completion of parameter verification. The 2017 link establishes notice metadata only; retrieve the notice itself for verification. Use the corrected 2018 republication. The 2019 govinfo retrieval timed out; SSA’s republication supplied citation verification.

For every downloaded notice, record URL, actual retrieval date, SHA-256 and staging path. These records remain **TO VERIFY**. Use govinfo where possible; U1 records that ssa.gov refused programmatic fetches.

Verify the applicable exclusion, resource and deeming provisions identified by U1, including 20 CFR §§416.1112, 416.1124, 416.1205 and 416.1163, for the required historical period. Do not presume constancy from current wording.

**Downloads need no approval (Max, 2026-09-28). Each is recorded with URL, retrieval date, SHA-256 and staging path.** Candidates include `cross_sec_weights_23.pdf` and the 2013–2022 COLA notices. No files were downloaded or staged during this no-files revision.

## 9. Statistics, cells and diagnostics

For cell \(c\), use identical baseline/reform observations and weights:

\[
P_B[c]=100\frac{\sum_{i\in c}w_i1(B_i<T_i)}{\sum_{i\in c}w_i},
\qquad
P_R[c]=100\frac{\sum_{i\in c}w_i1(R_i<T_i)}{\sum_{i\in c}w_i},
\]

\[
\Delta[c]=P_R[c]-P_B[c].
\]

Levels are percentages; changes and gaps are percentage points. The mappings below follow both cleared extracts, including `EV/u2-target-availability-cleared-20260928.md`.

| Cell | Report row | Role |
|---|---|---|
| `all` | Total | Primary; headline |
| `women` | Gender: Female | Primary |
| `men` | Gender: Male | Primary |
| `married` | Marital Status: Married | Primary |
| `widowed` | Marital Status: Widowed | Primary |
| `divorced` | Marital Status: Divorced | Primary |
| `never_married` | Marital Status: Never married | Primary |
| `women_married` | Gender and Marital Status: Female: Married | Secondary |
| `women_widowed` | Gender and Marital Status: Female: Widowed | Secondary |
| `women_divorced` | Gender and Marital Status: Female: Divorced | Secondary |
| `women_never_married` | Gender and Marital Status: Female: Never married | Secondary |
| `men_married` | Gender and Marital Status: Male: Married | Secondary |
| `men_widowed` | Gender and Marital Status: Male: Widowed | Secondary |
| `men_divorced` | Gender and Marital Status: Male: Divorced | Secondary |
| `men_never_married` | Gender and Marital Status: Male: Never married | Secondary |

Report weighted denominators, unweighted observations, distinct persons and unresolved-marital exclusions. Empty or zero-weight cells are undefined with reasons, never imputed. Birth-year cells are unscored diagnostics.

The twenty-one omitted Report rows comprise race/ethnicity, education, labor-force experience, own lifetime-earnings quintiles and shared lifetime-earnings quintiles. Their classification work is outside this extension. U1’s old-cohort age-22 rationale is not carried over.

### F17 diagnostics

**Registered run only:** official-concept poverty on the same sample—money income with reported asset income retained, no annuity and no cut, against the row’s threshold.

**Permitted before registration:** the inherited component summaries, without poverty-threshold assignment or poverty status:

- By income year, own Social Security receipt and mean amounts for head/spouse members, plus inherited family-level receipt summaries. OFUM own amounts are not identified.
- SSI receipt, recipient means, and recipient units above twelve times the applicable federal rate.
- WEALTH1 weighted quantiles at 10/25/50/75/90 percent, selecting the smallest value reaching the cumulative share; nonpositive, negative and imputed shares.
- Family-size versus individual-record counts.

Preserve the SSA comparison’s limitations: December retired-worker aggregates cover all ages, while PSID uses annual reported amounts. Report prior-December and income-year-December comparisons as inherited.

The committed snapshot:

```text
data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_5a.html
SHA-256 d61e9484d271aec0126d8897a780668adf55f5d86f5b440a0f69782de968aa8e
```

was rehashed. Both required Table 5.A4 panels contain 2011–2022, covering both December conventions, including row U1’s 2012 observation. This verification inspected year and panel labels; it computed no published average or PSID statistic.

No SCF comparison is introduced.

## 10. Uncertainty

**Draws:** \(K=1\), deterministic.

**Design SE:** Taylor linearization of each weighted ratio. For the change, use the paired indicator difference and preserve baseline/reform covariance.

The design frame contains every distinct sampling-error stratum/cluster pair among positive-cross-section-weight persons in that row’s observation waves. Clusters without a cell observation contribute zero. Support-only waves do not expand the frame.

The 2017/2019 refresher adds strata 88–94. Refuse if any positive-weight person lacks a valid stratum or cluster. The staged formats identify those strata at `IND2023ER_formats.sps:11710` and cluster codes 1 and 2 at line 11719. Validate against the documented domains rather than assuming a continuous range of stratum codes.

Singleton strata are excluded, counted and listed. Do not reuse U1’s observed stratum or cluster counts.

**Half-split floor:**

- Seeds `0, 1, 2, 3, 4`; fraction `0.5`.
- Use the inherited split implementation.
- Transitively merge family units sharing an observed person; label each component by its smallest family-unit ID.
- Keep every observation of a person on the same side.
- Recompute each statistic in each half.
- Summarize absolute half differences by mean and sample SD, `ddof=1`, retaining per-seed and inherited ancillary results.
- Require at least two usable seeds; otherwise report undefined with a reason.
- Do not rescale to full-sample precision.

## 10a. Comparison and acceptance

The cleared U2 availability statement establishes percentages for levels, percentage points for changes, whole-number printed levels and the inherited rounding allowance.

- Comparator change: Table 21 minus Table 19 for the registered row and column.
- Gap: model statistic minus corresponding Report statistic.
- Each printed level: ±0.5 percentage point rounding allowance.
- Derived change: open interval `(printed difference − 1, printed difference + 1)`.
- An exact change-interval endpoint is “on the edge,” not “inside.”
- Rounding intervals appear only in the comparison memo, never in the model artifact.
- No acceptance threshold or pass/fail certification.
- Publish every registered row regardless of outcome.
- No tuning, rerun or headline promotion after outcome inspection; changed methods require a new registered version.

The memo reports levels, change, denominators, design SE, floor, comparator precision and gaps.

Flag every cell with `n_observations < 30`. For a no-switcher cell, report **“uncertainty not estimable”** for the change; preserve the artifact’s mechanical calculations and report level uncertainty separately.

Two explicit additions are **clarification; not in U1; changes no U1 classification**:

1. Compare using unrounded model values; display rounding must not change classifications.
2. Do not divide gaps by undefined or noninformative zero uncertainty measures.

The U2 machine-readable interval identifier ends in `_open`; U1’s existing identifier remains unchanged.

## 11. Proposed registered rows

| Row | Change from U0 |
|---|---|
| **U0** | Primary, exact age 67 |
| U1 | All ten births using §3’s observation plan |
| U2 | No SSI response |
| U3 | Full-static SSI response |
| U4 | Head/reference-person-and-spouse income basis; OFUM members retain family basis |
| U5 | Keep reported asset, retirement-account and farm income, and add annuity, as in U1 |
| U7 | WEALTH1 plus verified employer DC balances |
| U8 | PSID Census needs standard |
| U9 | SSA period mortality table 2004 |
| U10 | Census size-by-children matrix |

There are ten rows. U0-F and all eight `-F` rows are omitted by the explicit §3 amendment. U6 and U-inst remain withdrawn.

The two-percent interest sensitivity is reported and unscored.

**Headline is fixed as U0.** Missing mappings, parameters or required sources block execution. They cannot trigger fallback or silent omission.

## 12. Named deltas

The following are the complete proposed output texts. The text following each identifier is a literal string to be held equal to U2’s own `NAMED_DELTAS` tuple before ratification. U1’s tuple remains byte-identical. Literal strings carry no terminal period; the Markdown renderer appends one (`track_u_dry_run.py:491`).

- **D01:** PSID and SIPP differ in population coverage and in the collection and measurement of income and wealth
- **D02:** U2 uses realized 2014–2022 incomes, with income year 2012 additionally entering row U1, rather than DYNASIM3's projection from the 1990–93 SIPP under 2002 Trustees assumptions
- **D03:** Realized COLAs, asset histories and economic conditions enter the observed PSID inputs; the Report uses its stated projection assumptions
- **D04:** income year 2020: pandemic-era transfers (expanded UI; how the PSID records Economic Impact Payments) under the PSID money-income concept
- **D05:** The observed universe reflects attrition, survival to the interview after the income year, immigrant coverage and later immigrant refreshment; registered cross-section weights are used without additional calibration
- **D06:** Institutionalized persons are outside the observation universe and appear only in counted dispositions
- **D07:** The primary assigns family-unit resources to individuals, while the Report establishes inclusion of spouse resources without fully specifying poverty-family membership or nonspouse co-resident treatment
- **D08:** Family wealth includes OFUM-owned assets and stands in for an OFUM cohort member's resources; the primary does not identify and allocate each asset to its individual owner
- **D09:** The primary retains PSID money-income sources other than the explicitly replaced asset, reference-person retirement-account and imputed farm components; the Report's treatment of every corresponding poverty-income source is not established
- **D10:** Members whose marital state remains unresolved are retained in all and applicable sex cells but excluded and counted in marital cells
- **D11:** Social Security is self-reported and may reflect Medicare-premium netting; the cut is applied to the reported amount rather than a reconstructed gross entitlement
- **D12:** Reference-person annuity and IRA income is removed while spouse and OFUM pension-annuity combinations remain under the inherited convention; balance-income overlap and annuities already in payment are not fully identified
- **D13:** WEALTH1 excludes employer DC balances outside IRAs; row U7 adds only the reference-person and spouse balances covered by verified questionnaire routes, retaining documented omissions and unreported-amount dispositions
- **D14:** PSID other-assets coverage includes categories whose correspondence to the Report's stated financial-asset definition is not established
- **D15:** Interview-time wealth is paired with income from the preceding calendar year
- **D16:** Annuities use fixed population period life tables, the registered real interest rate and terminal closure, and family-head/legal-spouse lives rather than individually projected mortality histories
- **D17:** Row U0 samples five alternate birth years at exact age 67 and does not represent all ten birth years in the Report's column
- **D18:** Row U1 represents even birth years with half-weighted observations at ages 66 and 68; income, claiming, family composition and survival need not vary linearly between those ages
- **D19:** Row U1 includes the 1946 birth year's age-66 observation in income year 2012; all U2 rows share identification support waves 2013–2023 while retaining row-specific observation and design frames
- **D20:** Farm asset income is imputed using the registered positive-income share and whole-loss rule; business labor and asset income retain the PSID allocation convention
- **D21:** SSI units are approximated from reference-person, spouse-slot and OFUM totals, with full attribution of spouse-slot Social Security and one aggregate OFUM individual unit
- **D22:** SSI response uses annual amounts against twelve times the January federal benefit rate; reported SSI can include state supplements, while the response cap uses the federal rate
- **D23:** Row U3 adds deterministic enrollment only for newly income-eligible head/spouse units under the inherited countable-income and resource proxies; OFUM new enrollment, complete resource ownership and full legal deeming are not modeled
- **D24:** PSID children-in-family is a proxy for related children; weighted-average Census thresholds, the size-by-children matrix and the PSID needs standard use distinct composition conventions
- **D25:** Relationship labels change in 2015 and 2017; U2 explicitly separates income-slot membership, legal-spouse annuity lives and marital resolution, with required source-routing ambiguities resolved before registration
- **D26:** WEALTH1 uses seven asset components in 2015/2017 and eight from 2019, with separately identified debts; each wave's documented identity is preserved

Structural and component counts may be attached as separate metadata from the authorized pre-registration pass. They do not silently alter these literal texts. No old-cohort counts, birth-year means, endpoint descriptions or `-F` exposure text are copied into U2.

## 13. Invented cases, tests and U1 compatibility

All invented fixtures must be headed **INVENTED DATA - NOT A COMPARISON** and contain no PSID-derived quantities or comparator values.

Retain the applicable U1 worked cases for annuity prices, strict-threshold poverty, SSI caps and exclusions, new enrollment, farm losses, retirement-account removal, unresolved marital status, annuitant ages and employer-DC routing. Adapt relationship cases to §3 rather than retaining the old sex-based description.

### Required U2 tests

| Group | Assertions |
|---|---|
| Observation plans | U0 has five pairs; row U1 has fifteen pairs and ten births; planned multipliers sum to one per birth year |
| Boundary wave | Wave 2013 appears as an observation only for 1946 at age 66 in row U1 |
| Missing observations | No transfer or renormalization of a missing half weight |
| Support separation | Support-only waves never enter U0 observations or its design frame |
| Identification | Shared observations have identical derived births and annuitant attributes across rows |
| Cohort bounds | Exact birth-year, age, income-year and wave relationships; outside births excluded with dispositions |
| Labels | Codes 10/20/22/88/90 in every support wave; code 92 absent in 2013/2015 and present 2017–2023; reported-birth-year anchor labels |
| Roles | Code 20 of either sex, code 90, code 92’s explicit OFUM assignment and exclusion from legal-spouse annuity/marital resolution, code 88’s administrative-support distinction, cohabitor income slots, zero-weight legal spouses, unresolved/ambiguous pairings |
| Income/wealth maps | Exact labels and widths, losses, sentinels, seven/eight-asset identities, debt once, home equity excluded |
| Employer DC | All verified current/previous-plan routes, checkpoint branches, IRA rollovers and duplicate accounts |
| Design | Strata 88–94, invalid-design refusal, zero-contribution clusters, singleton reporting and paired change SE |
| Floor | Transitive person/family linkage, both observations on one side, undefined floors and required seed count |
| Parameters | Complete years, 2022 precision, exact 2012 threshold/SSI overlap, unknown revision refusal and constant checks |
| Memo | Small cells, no-switcher wording, undefined cells and rounding endpoints |
| Identity | Wrong cohort, seed, column, rulings, parameters, provenance and artifact destination refuse |
| Historical isolation | Exact exclusions and transitive non-reachability of new modules |

For every observation in every row—including row U1, U3 and U4—and in each half-split, require:

\[
R_i\le B_i,\qquad 1(R_i<T_i)\ge1(B_i<T_i).
\]

For valid nonnegative Social Security and \(0\le c\le1\), require:

\[
0\le\text{offset}\le\text{fall}\le cS,
\]

with `fall = 0` when \(S\le G\), and offset no greater than available FBR room.

For newly eligible units:

\[
0\le SSI_{\text{new}}\le\min(F-C',\,C-C').
\]

Also test zero-cut identity, poverty rates within `[0,100]`, positive common weight-scaling invariance and rejection of malformed plans or missing parameters. These are calculation properties, not statements about Report cells.

Mirror `test_nobody_leaves_poverty_under_the_cut` in `tests/test_replication_boomers2004_uniform_cut.py:133` for the eventual U2 artifact.

### U1 differential test: exact outputs and tolerance

Run the existing `scripts/track_u_dry_run.py` at `9cee2423f048` and at the candidate commit with the same Python executable, dependencies and invented seed **20260924**.

It emits:

- `result.json`
- `RESULTS.md`

The main run uses invented staged supplements. Its `checks.fallback_rule_with_supplements_refused` repeats the same seed with supplements refused and records fallback headline, blocked rows, dispositions, refusal and headline cell.

Compare the **entire** canonical JSON and the complete normalized Markdown, including all nineteen U1 rows, all cells and uncertainty, F17 diagnostics, undefined reasons, parameters, provenance, labels, decisions, named deltas and checks.

**Tolerance: zero. Registered U1 behavior must be byte-identical.** No float rounding, relative tolerance or absolute epsilon is allowed.

The fixed metadata exclusion list is exactly:

```text
/run/git_head
/run/date
```

Reuse the identical absolute output-directory argument sequentially, so `run.command`, including its output path, remains compared. Also compare `run.python`, `run.git_clean` and seeds. No wildcard timestamp or provenance removal is permitted.

The following procedure is runnable once the two clean checkouts and common dependency environment exist. It is specified for future verification and was not executed during this revision.

```sh
python - "$U1_BASE" "$U2_CANDIDATE" <<'PY'
import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

base = Path(sys.argv[1]).resolve()
candidate = Path(sys.argv[2]).resolve()

head = subprocess.check_output(
    ["git", "rev-parse", "--short=12", "HEAD"], cwd=base, text=True
).strip()
assert head == "9cee2423f048"

def canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")

def normalize_json(value):
    value = copy.deepcopy(value)
    del value["run"]["git_head"]
    del value["run"]["date"]
    return canonical(value)

def normalize_markdown(raw, result):
    text = raw.decode("utf-8")
    date_text = (
        "Track U (DynaSim exercise 2, plan item U9) end-to-end dry run, "
        + result["run"]["date"] + "."
    )
    commit_text = "- Code: `" + result["run"]["git_head"] + "`"
    assert text.count(date_text) == 1
    assert text.count(commit_text) == 1
    text = text.replace(
        date_text,
        "Track U (DynaSim exercise 2, plan item U9) end-to-end dry run, "
        "<DATE>.",
        1,
    )
    return text.replace(
        commit_text, "- Code: `<COMMIT>`", 1
    ).encode("utf-8")

def run(checkout, output):
    subprocess.run(
        [
            sys.executable, "scripts/track_u_dry_run.py",
            "--output-dir", str(output), "--seed", "20260924",
        ],
        cwd=checkout, check=True,
    )
    result = json.loads((output / "result.json").read_text())
    assert result["run"]["git_clean"] is True
    assert result["run"]["invented_seed"] == 20260924
    assert result["cohort_provenance"]["seed"] == 20260924
    return (
        normalize_json(result),
        normalize_markdown((output / "RESULTS.md").read_bytes(), result),
    )

with tempfile.TemporaryDirectory(prefix="u1-differential-") as directory:
    output = Path(directory) / "same-output"
    expected = run(base, output)
    observed = run(candidate, output)
    assert observed == expected
PY
```

### Additional exact contract checks

Before ratification, the differential harness must additionally serialize and compare, with the same canonical encoding and **no exclusions**:

- `age67.WAVES`, exactly `(2005, 2007, 2009, 2011, 2013)`.
- `observation_plan(Age67Spec(row=...))` for U0, U1 and U0-F.
- `pending_decisions()` from `age67`, `adjusted_poverty` and `uniform_cut_tabulation`.
- `rows.MAX_RULINGS`.
- `runner.NAMED_DELTAS`.
- `uniform_cut_tabulation.REPORT_ROWS` and `COMPARATOR_COLUMN`.
- `input_frames_sha256()` on seed-20260924 invented inputs with supplements staged and refused.
- The actual loader’s input-frame hash and loader-seal hash on those invented reader fixtures.

For the actual-loader test, patch every reader dependency in `age67.load_age67_inputs` to the same invented frames at both commits, use a fixed nonempty invented file manifest, and refuse any unpatched file access. For refused supplements, raise `WealthSupplementNotStagedError("INVENTED supplement absent")` for waves 2005 and 2007. Compare frame names, columns, dtypes, order and hashes without normalization.

This supplemental cross-commit loader/refusal harness is **to build**; it is a mandatory implementation deliverable, not an existing test claimed to have run.

### Fixed refusal-parity cases

At both commits, invoke the same case and compare exception module, class and complete message byte-for-byte. Use fixed synthetic paths and the pointer:

```text
https://github.com/PolicyEngine/microcosm-dynamics/issues/42#issuecomment-1
```

| Case | Fixed input |
|---|---|
| Invalid provenance | `runner._check_inputs(inputs, "bad", None, False)` |
| Invented run carrying a registration pointer | `_check_inputs(inputs, ap.INVENTED, POINTER, False)` |
| Invalid registration URL | `_check_inputs(inputs, ap.REGISTERED_REAL, "https://example.org/x", False)` |
| Invented inputs labeled registered | `_check_inputs(inputs, ap.REGISTERED_REAL, POINTER, False)` |
| Wrong registered headline | `check_headline("U0", refused_supplement_inputs)` |
| Wrong threshold hash | Call `runner._check_parameters(params, ap.REGISTERED_REAL)` after `params = replace(params, thresholds=replace(params.thresholds, provenance={"kind": "census_capture", "sha256": "0" * 64}))`; all other committed parameters unchanged |
| Wrong SSI hash | Call `runner._check_parameters(params, ap.REGISTERED_REAL)` after `params = replace(params, ssi=replace(params.ssi, provenance={"kind": "policyengine_us_capture", "sha256": "0" * 64}))`; all other committed parameters unchanged |
| Existing artifact | Patch `Path.exists` to `exists_artifact_only`; call `run_track_u_registered.preflight(registration_pointer=POINTER, registered_commit=REGISTERED_COMMIT, output=FIXED_ARTIFACT, git=fake_git, specification=RATIFIED_U1)` |
| Existing sidecar | Patch `Path.exists` to `exists_sidecar_only`; call `run_track_u_registered.preflight(registration_pointer=POINTER, registered_commit=REGISTERED_COMMIT, output=FIXED_ARTIFACT, git=fake_git, specification=RATIFIED_U1)` |
| U2 seed under U1 | `Age67Spec(seed_wave_rule="earliest_presence_in_common_support_waves")` |

The last case must retain `ValueError("seed_wave_rule must be earliest_presence_wave")`. Existing-output cases retain `ValueError("<fixed path> already exists: the registered run is one-shot")`.

The exact setup for these future refusal tests is:

```python
from dataclasses import replace
from pathlib import Path

POINTER = (
    "https://github.com/PolicyEngine/microcosm-dynamics/issues/42"
    "#issuecomment-1"
)
REGISTERED_COMMIT = "a" * 40
FIXED_ARTIFACT = Path(
    "/INVENTED/u1-refusal-parity/"
    "replication_boomers2004_uniform_cut_v1.json"
)
FIXED_SIDECAR = Path(
    "/INVENTED/u1-refusal-parity/"
    "replication_boomers2004_uniform_cut_v1.env.json"
)
assert FIXED_SIDECAR == FIXED_ARTIFACT.with_suffix(".env.json")

def fake_git(*args):
    if args == ("rev-parse", "HEAD"):
        return REGISTERED_COMMIT
    if args == ("status", "--porcelain"):
        return ""
    raise AssertionError(args)

def exists_artifact_only(path):
    if path not in (FIXED_ARTIFACT, FIXED_SIDECAR):
        raise AssertionError(path)
    return path == FIXED_ARTIFACT

def exists_sidecar_only(path):
    if path not in (FIXED_ARTIFACT, FIXED_SIDECAR):
        raise AssertionError(path)
    return path == FIXED_SIDECAR
```

For each hash-refusal case, start afresh with `params = runner.committed_parameters(ap.load_poverty_thresholds())` and use the table’s `replace` expression to change only the specified provenance. These calls load committed public parameters, not PSID records. Both calls raise `runner.TrackURunError`, a `ValueError` subclass; the threshold and SSI hash branches are at `S/uniform_cut_track_u/runner.py:243` and `:254`, respectively, and the exception class is at `:175`.

For preflight, read the full ratified U1 §15 block once at `9cee2423f048` using `rows.specification_block()`; freeze it and pass identical copies as `RATIFIED_U1` in both checkout processes. Do not substitute the U2 draft block. Scope each `Path.exists` patch to its table call and restore it afterward. Only the two exact synthetic paths above are accepted; no filesystem fixture is created.

The existing-artifact case returns true only for `FIXED_ARTIFACT`; the existing-sidecar case returns false for `FIXED_ARTIFACT` and true only for `FIXED_SIDECAR`. The artifact case short-circuits before checking the sidecar. Both cases raise built-in `ValueError` with this complete message:

```text
/INVENTED/u1-refusal-parity/replication_boomers2004_uniform_cut_v1.json already exists: the registered run is one-shot
```

The sidecar case’s message names the artifact path. Its suffix replaces `.json`; it does not append `.env.json` to the existing suffix. Source: `scripts/run_track_u_registered.py:98` for the artifact basename and `:167–199` for the signature, prerequisites, exact existence checks and exception. The same fixed pointer, HEAD and clean porcelain output pass all earlier preflight gates at both commits.

U1 currently rejects an **existing** output, rather than every arbitrary fresh path. U2’s refusal of U1’s artifact identity is a new guard, tested separately.

### Existing U1 suite and immutable artifacts

All existing U1 test files remain unmodified:

```sh
python -m pytest \
  tests/track_u \
  tests/cohorts/test_age67*.py \
  tests/estimates/test_adjusted_poverty*.py \
  tests/estimates/test_uniform_cut_tabulation.py \
  tests/data/test_family_income*.py \
  tests/data/test_employer_dc*.py \
  tests/test_boomers2004_uniform_cut_spec.py \
  tests/test_replication_boomers2004_uniform_cut.py
```

Run the invented/artifact suite in an environment where raw PSID is absent or inaccessible. Existing integration tests automatically read staged data when present. Report intentional raw-data skips as **skipped**, not passed. Any separately authorized real integration work is limited to structural, reconciliation and component checks; do not rerun U1 poverty outcomes.

Require unchanged bytes for U1’s specification, parameter captures, registered artifact and environment sidecar. Do not regenerate them.

Optional, only with Max’s explicit OK: a structure-only U1 load may verify the artifact’s input-frame pin:

```text
43c41f444128ecf72ce9f8c5e64a7cda61a6fccaa2a58ff60ae7ce91356c4271
```

It computes no statistic. It was not performed here.

## 14. Implementation, isolation and refusal gates

This specification does not implement U2.

| Area | Required work and source basis |
|---|---|
| Cohort configuration | Introduce explicit U2 support/observation plans and identity while preserving U1’s API and defaults; current constants at `S/cohorts/age67.py:204`, specification at `:362`, plan at `:514` |
| Birth-year law | Call existing `S/estimates/career.py:642`; do not edit it |
| Income and DC mappings | Add independently adjudicated U2 registries/adapters; preserve U1 wave registries and defaults |
| `data/family.py` | **read only; no edit** |
| `data/psid.py` | **read only; no edit** |
| `estimates/career.py` | **read only; no edit** |
| Income estimator | Explicit U2 parameter and role context; preserve U1 pins at `S/estimates/adjusted_poverty.py:196` and IRA-year behavior at `:290` |
| Threshold access | Read the full registered capture; Track M’s specialized interface is at `S/min_benefit_track_m/thresholds.py:50` |
| Tabulation identity | Preserve U1 `COMPARATOR_COLUMN` at `S/estimates/uniform_cut_tabulation.py:159`; provide separate U2 identity |
| Runner | Separate U2 rows, literal deltas, rulings and fixed headline; U1 currently emits its column at `S/uniform_cut_track_u/runner.py:703` |
| Capture configuration | Separate U2 SSI years/output; preserve U1 defaults |
| Invented dry run | Build `scripts/track_u2_dry_run.py` |
| Structural/component entry points | Build `scripts/track_u2_structure.py` and `scripts/track_u2_component_diagnostics.py`, without importing poverty computation |
| Registered entry point | Build `scripts/run_track_u2_registered.py` |
| Artifact | `runs/replication_boomers2004_1946_55_v1.json` |
| Environment sidecar | `runs/replication_boomers2004_1946_55_v1.env.json` |

### Historical source protection

Any new module is added to `POST_REVIEW_SOURCE_EXCLUSIONS` and the transitive reachability test. `family.py`, `psid.py` and `career.py` are not edited.

Use exact file exclusions, not directory exclusions. Preserve the historical input-identity pin. Required checks are:

- `scripts/first_estimates_birth_evidence.py:135`.
- `tests/estimates/test_birth_evidence_artifact.py:63`, `test_reducer_input_identity_matches_reviewed_branch`.
- The exact-exclusion tuple test at line 67.
- Package-initializer reachability at line 243.
- Transitive exclusion reachability at line 274.

Engine files and existing committed runs remain unchanged.

### Wave isolation

U1 explicitly pins waves `(2005, 2007, 2009, 2011, 2013)`. Test that pin.

Do not extend a shared `INCOME_WAVES` tuple and thereby alter U1’s loader, IRA-year checks or frame hash. The current coupling is documented at `S/cohorts/age67.py:204`, `:678`, `:714` and `S/estimates/adjusted_poverty.py:290`.

Use separate U2 registries/configuration or equally strict cohort-specific adapters. Preserve U1’s public constants, serialized defaults and registered behavior.

### Invented U2 dry run

The new dry run must emit `result.json` and `RESULTS.md`, both headed **INVENTED DATA - NOT A COMPARISON**. Use invented persons, families, income, wealth, weights, design and poverty thresholds. Exercise all ten rows, all relevant mapping/role branches and required refusals, including rejection of invented inputs by the registered runner.

Completion is required before ratification and forecast.

### Cross-cohort refusals

- U1’s registered loaders and runner refuse the Track M threshold capture and any U2 SSI capture.
- U2’s loaders and runner refuse U1 threshold hash `dc21a787…` and SSI hash `79e641a1…`, even where years overlap.
- U1’s `Age67Spec` refuses U2 seed/cohort settings; U2’s corresponding configuration refuses U1 identities and seed settings.
- U2 refuses U1’s specification, column, row/rulings record, `MAX_RULINGS` and artifact path.
- U2 has its own rulings record; copying U1’s authorization is insufficient.
- Caller-supplied expected hashes cannot bypass the target-bound parameter bundle.

### Registered-run preflight

Before reading raw PSID records, verify:

- Ratified specification, completed decisions and empty blockers.
- Exact registered commit and clean execution checkout.
- Registration binding target, specification hash, rows, plans, maps, source identities and parameter pins.
- Fixed U0 headline and exact output identity.
- Nonexisting artifact and sidecar.
- Complete parameter coverage, including 2012.
- Completed independent mapping review and pre-registration evidence.

Propagate and validate target identity through loader, cohort, income rows, estimator, tabulation rows, tabulator and runner. Preserve invented-versus-real provenance guards.

Changed source bytes, changed frame digests, duplicate identifiers, failed joins or unregistered omissions refuse execution. Pre-registration mapping checks resolve these before the one-shot; execution rechecks their frozen identities.

## 15. Machine-readable parameter block

This is the complete draft parameter contract, with explicit unresolved pins. It uses U1’s key names where the concepts are inherited. Additional keys describe U2-specific identity and amendments.

Ratification requires code/block equality, completed manifests and replacement of every required `TO_VERIFY`. This block does not authorize execution.

```json
{
  "specification": "boomers2004_1946_55_uniform_cut",
  "target_id": "U2",
  "version": "u2-draft-4",
  "status": "draft",
  "inherits": {
    "file": "docs/design/boomers2004_uniform_cut_comparison.md",
    "version": "u1-ratified-1",
    "sha256": "830b0ab4c18273563add529fecf21f843eb418996da741d087d785c4f882781f"
  },
  "claim_class": {
    "class": "track_u_psid_realized_measurement_not_a_projection"
  },
  "target": {
    "report": "Butrica and Uccello (2004), How Will Boomers Fare at Retirement?, AARP PPI #2004-05",
    "tables": ["19", "21"],
    "column": "1946-55",
    "birth_years": [1946, 1955],
    "age": 67,
    "cut_rate": 0.13,
    "report_rows": 36,
    "unit": "individual_with_household_income_and_wealth_including_spouse",
    "financial_assets": "non_pension_wealth_plus_ira_keogh_401k_balances",
    "comparator_values": "sealed_comparator_side_not_opened_by_builder",
    "printed_precision": "whole_numbers",
    "definitions_extract": [
      {
        "file": "EVID/exercise2-definitions-cleared-20260924.md",
        "sha256": "a3978b683b4275424b6d12e9fe45f021fae277ccf9731a7883952564b6ed0384"
      },
      {
        "file": "EVID/u2-target-availability-cleared-20260928.md",
        "sha256": "2ffa3092d297418c58868f7e5326c3e4c8047b129171b40b66fde5ee07702211"
      }
    ]
  },
  "population": {
    "primary_row": "U0",
    "headline": {
      "rule": "fixed_u0_no_fallback",
      "fallback_row": null
    },
    "support_waves": [2013, 2015, 2017, 2019, 2021, 2023],
    "primary_waves": [2015, 2017, 2019, 2021, 2023],
    "primary_birth_years": [1947, 1949, 1951, 1953, 1955],
    "u1_birth_years": [1946, 1955],
    "u1_even_birth_year_weight": 0.5,
    "u1_single_observation_weight": 1.0,
    "u1_even_birth_ages": [66, 68],
    "missing_observation_reweighting": false,
    "waves": {
      "2013": {
        "income_year": 2012,
        "weight": "ER34269",
        "family_unit_id": "ER34201",
        "wealth1": "ER58209",
        "wealth_source": "family_file"
      },
      "2015": {
        "income_year": 2014,
        "weight": "ER34414",
        "family_unit_id": "ER34301",
        "wealth1": "ER65406",
        "wealth_source": "family_file"
      },
      "2017": {
        "income_year": 2016,
        "weight": "ER34651",
        "family_unit_id": "ER34501",
        "wealth1": "ER71483",
        "wealth_source": "family_file"
      },
      "2019": {
        "income_year": 2018,
        "weight": "ER34864",
        "family_unit_id": "ER34701",
        "wealth1": "ER77509",
        "wealth_source": "family_file"
      },
      "2021": {
        "income_year": 2020,
        "weight": "ER35065",
        "family_unit_id": "ER34901",
        "wealth1": "ER81836",
        "wealth_source": "family_file"
      },
      "2023": {
        "income_year": 2022,
        "weight": "ER35265",
        "family_unit_id": "ER35101",
        "wealth1": "ER85690",
        "wealth_source": "family_file"
      }
    },
    "presence": "in_family",
    "birth_year_law": "estimates.career.derive_birth_years",
    "seed_wave_rule": "earliest_presence_in_common_support_waves",
    "separated_is_married": true,
    "unresolved_marital_status": "relationship_code",
    "annuitant_age_source": "derived_birth_year",
    "institution_income_rule": "excluded",
    "relationship_rules": "section_3_u2_wave_specific_role_amendment",
    "relationship_codes_tested": [10, 20, 22, 88, 90, 92],
    "design": {
      "stratum": "ER31996",
      "cluster": "ER31997"
    }
  },
  "income_concept": {
    "income_unit": "family_unit",
    "money_income": "TOTAL FAMILY INCOME",
    "asset_income_rule": "replace",
    "asset_income_items": [
      "head_rent", "head_dividends", "head_interest", "head_trusts",
      "head_business_asset", "wife_rent", "wife_dividends",
      "wife_interest", "wife_trusts", "wife_business_asset", "ofum_asset"
    ],
    "retirement_account_income_rule": "remove_head",
    "retirement_account_income_items": ["head_annuities", "head_iras"],
    "farm_asset_share": 0.5,
    "farm_loss": "removed_whole_when_share_positive",
    "financial_assets": "wealth1",
    "employer_dc": {
      "row": "U7",
      "reader": "TO_VERIFY_u2_employer_dc_adapter",
      "persons": ["head", "wife"],
      "role_meaning": "reference_person_and_designated_spouse_income_slot",
      "current_job": "account_amount_when_plan_type_has_an_account",
      "previous_plans": [1, 2],
      "previous_routes": {
        "both_items": ["both"],
        "account_items": ["account", "formula", "dk"]
      },
      "route_source": "later_wave_questionnaire_adjudication",
      "later_wave_mapping_status": "TO_VERIFY",
      "counted_disposition": "left_to_accumulate",
      "excluded": [
        "rolled_over_into_ira",
        "both_plan_account_items_reasked",
        "off_route"
      ],
      "unreported_amount": "zero_counted",
      "top_code": "as_recorded",
      "brackets": "not_used"
    },
    "annuitized_share": 0.8,
    "annuity": {
      "real_interest_rate": 0.03,
      "timing": "immediate",
      "load": 0.0,
      "survivor_share": 0.5,
      "mortality_basis": "nchs_2000",
      "terminal_closure": "table_end",
      "lives": "fu_head_rule",
      "negative_wealth": "annuity_floored_at_zero"
    },
    "sensitivities_unscored": {
      "real_interest_rate": [0.02]
    }
  },
  "threshold": {
    "rule": "census_weighted_average_65plus",
    "years": [2012, 2022],
    "required_income_years": [2012, 2014, 2016, 2018, 2020, 2022],
    "values": "weighted_averages_as_printed_in_thresh_workbooks",
    "capture_status": "captured",
    "capture": {
      "file": "data/external/census_poverty_thresholds_1982_2022.json",
      "sha256": "288399c475ae3ff02e6d8367425ee0a568b50d239da5656f24d0d2dfafabfb53"
    },
    "overlap_2012": "exact_equality_with_u1_capture",
    "poor_if": "income_below_threshold"
  },
  "cut": {
    "rate": 0.13,
    "base": "all_social_security_of_the_unit",
    "behavior": "none",
    "start_year": 2004,
    "start_year_rule": "cut_when_birth_year_plus_67_at_or_after_start"
  },
  "ssi": {
    "rule": "offset_existing_recipients",
    "deeming": "spouse_social_security_counted",
    "ofum_unit": "single_individual",
    "parameters": {
      "file": "data/external/track_u2_ssi_parameters_2012_2022.json",
      "sha256": "TO_VERIFY",
      "years": [
        2012, 2013, 2014, 2015, 2016, 2017,
        2018, 2019, 2020, 2021, 2022
      ],
      "checked_against": "section_8_federal_register_cola_notices",
      "revision_rule": "refuse_missing_empty_or_unknown",
      "overlap_2012": "all_seven_parameters_equal_u1"
    }
  },
  "statistic": {
    "headline": "delta",
    "secondary": ["baseline_rate", "reform_rate"],
    "unit": "percentage_points"
  },
  "cells": {
    "column": "1946-55",
    "scored": [
      "all", "women", "men", "married",
      "widowed", "divorced", "never_married"
    ],
    "secondary": [
      "women_married", "women_widowed",
      "women_divorced", "women_never_married",
      "men_married", "men_widowed",
      "men_divorced", "men_never_married"
    ],
    "diagnostic": "birth_year",
    "report_labels": "tables_19_21_stub_labels_cleared_extract",
    "unclassified_marital_cells": "excluded_counted",
    "not_computed": [
      "race_ethnicity", "education", "labor_force_experience",
      "lifetime_earnings_own", "lifetime_earnings_shared"
    ]
  },
  "uncertainty": {
    "draws": 1,
    "floor": {
      "seeds": [0, 1, 2, 3, 4],
      "fraction": 0.5,
      "split_unit": "family_unit_id_linked_by_person_id",
      "summary": ["mean", "sample_sd"],
      "min_usable_seeds": 2
    },
    "design_se": {
      "method": "taylor_linearization",
      "domain": "full_sample_design",
      "outside_cell": "zero",
      "singleton_strata": "excluded_counted_and_listed"
    }
  },
  "comparison": {
    "gap": "model_minus_report",
    "comparator_interval": "whole_number_rounding_level_0_5_difference_1_open",
    "acceptance": {
      "rule": null
    },
    "memo_small_cells": {
      "flag_unweighted_n_below": 30,
      "unweighted_n": "n_observations",
      "no_switcher_cell": "uncertainty_not_estimable"
    }
  },
  "rows": {
    "U0": {},
    "U1": {"population": "all_ten_birth_years"},
    "U2": {"ssi_rule": "none"},
    "U3": {"ssi_rule": "full_static_recomputation"},
    "U4": {"income_unit": "head_wife"},
    "U5": {"asset_income_rule": "keep"},
    "U7": {"financial_assets": "wealth1_plus_employer_dc"},
    "U8": {"threshold_rule": "psid_census_needs_standard"},
    "U9": {"mortality_basis": "ssa_period_2004"},
    "U10": {"threshold_rule": "census_matrix_65plus"}
  },
  "diagnostics_f17": {
    "row": "headline",
    "official_concept_poverty_rate": "registered_run_only",
    "components": [
      "social_security", "ssi", "wealth1", "fu_size_record_counts"
    ],
    "component_timing": "permitted_before_registration",
    "social_security_published": "ssa_supplement_2025_table_5a4_december_retired_workers",
    "ssi_published": "federal_benefit_rate_capture_only",
    "wealth1_published": null
  },
  "entry_points": {
    "dry_run": "scripts/track_u2_dry_run.py",
    "registered_run": "scripts/run_track_u2_registered.py",
    "registered_artifact": "runs/replication_boomers2004_1946_55_v1.json",
    "environment": "runs/replication_boomers2004_1946_55_v1.env.json",
    "structure": "scripts/track_u2_structure.py",
    "component_diagnostics": "scripts/track_u2_component_diagnostics.py"
  },
  "acceptance_rule": null,
  "labels": [
    "PSID-realized outcomes (not a projection)",
    "Python income concept (not Axiom)",
    "mechanical incidence"
  ],
  "decisions": {
    "u2_ratification": "pending_Max",
    "prior_u1_rulings": "precedent_not_u2_execution_authorization",
    "rulings_record": "separate_u2_record_required",
    "row_set_amendment": "omit_u0f_and_eight_f_rows",
    "downloads": "no_approval_required_Max_2026_09_28"
  },
  "blocked_by": [
    "later_wave_component_and_role_adjudication",
    "2015_male_code20_family_slot_source_resolution",
    "code90_code92_income_routing_source_resolution",
    "later_wave_employer_dc_routing_adjudication",
    "mapping_manifests_and_independent_review",
    "ssi_capture_verification_and_pin",
    "cohort_isolation_and_identity_guards",
    "invented_dry_run_and_u1_differential_evidence",
    "preregistration_structure_reconciliation_and_f17_pass",
    "u2_ratification_forecast_and_registration"
  ]
}
```

## 16. Decisions and explicit departures from U1

| Decision | Proposed U2 rule |
|---|---|
| Observation convention | U0 exact-age five-birth primary; row U1 includes both half-weighted observations for every even birth |
| Common identification support | 2013–2023 support for all rows; observation and design frames remain row-specific |
| Rows and fallback | Ten rows; omit U0-F and eight `-F` rows; fixed U0 headline |
| Income and mortality | Inherited economic concept and life tables, with explicit §3 relationship amendment and later wealth identities |
| SSI capture | Separate, independently verified 2012–2022 capture; exact overlap; preserved U1 capture |
| Downloads | No new approval required; record URL, retrieval date, SHA-256 and staging path |
| Comparison/publication | Fifteen cells; inherited precision and memo rules; no acceptance threshold; publish regardless |
| Process | Mapping review, invented/differential tests and pre-registration structural/component pass before forecast and registration |

**Departure from U1: U1's rows shared their waves, so the rule was common by construction.**

The common-support rule can change identification relative to a row-specific seed; it is a deliberate U2 choice, not a renamed U1 default.

Other explicit departures are the two-sided 1946 boundary, removal of the supplement-based row contrast and fallback, new relationship semantics, later wealth identities and a separate parameter/authorization identity.

The pre-registration allowance matches U1. Additional mapping-completion requirements concern new sources and are completed before the one-shot.

These are proposed U2 defaults. U1’s d189/d411 rulings are precedent, not U2 execution authorization.

## 16a. Proposed amendments for `u2-draft-4` (pending Max's ruling)

> **PROPOSED — not ratified.** Every amendment in this section is a proposal for Max's ruling. Until he rules on an amendment, §§3–15 govern exactly as written in `u2-draft-3`, and the source registries keep refusing every route this section leaves open. Ruling on one amendment does not rule on another.

The amendments carry out the independent adjudication of milestone 1 (`EV/phase2-20260927/out/u2-adjudicate.md`, SHA-256 `a891762bf9be39e05509e59c5b7cd3fdab0eb34feb9ad5b9bb4a8ec3afc39662`; its amendment numbers are kept). Milestone 1b's documentary research updates them (`docs/design/u2_m1b_psid_research.md`; sources in `tests/data/track_u2/psid_docs/manifest.json`). Amendment 7 of the adjudication (18 citation corrections) needed no ruling and is already applied to the registries and `docs/design/u2_m1_source_adjudication.md`.

**How options are recommended.** Where a blocker stays open, the recommended option is the one that puts no undocumented assumption about PSID's processing into any estimate, is fixed before any count or outcome exists, and does not let a count decide what draft 3 says only documents may decide. No option here was chosen, or may be chosen, by its effect on any result. No result, count or outcome has been computed for this draft. A count enters only through the authorized pre-registration structural pass (§4), and only where an option Max has ratified names it.

**Proceeding before documents resolve B1 or B2 amends draft 3.** Draft 3 requires documentary resolution of both blockers before registration and bars counts from supplying it. The governing lines read, verbatim, with draft-3 line numbers (lines 152 to 160 are unchanged in this draft; draft-3 line 1391 is line 1563 here):

> 152: Code 92 does not exist in 2013 or 2015. From 2017 it is 'Uncooperative partner of Reference Person' (`IND2023ER_formats.sps` lines 24478, 26005, 27587, 29183). Its OFUM income routing is **TO VERIFY** from family-file documentation under the same standard as the 2015 male code-20 blocker.

> 154: Code 90’s OFUM assignment is an explicit U2 interpretation. Its 2015 full definition concerns inability or unwillingness to be designated Head; the 2017–2023 full definitions concern designation as Reference Person **or Spouse**. Do not describe these definitions as identical. The claim that code 90 is excluded from the family-file spouse income slot and included in OFUM totals is **TO VERIFY** from 2015–2023 family-file documentation before registration, like the 2015 male code-20 blocker (rev1 line 156); it may not be established from counts.

> 158: The SSI income units follow the income slots, not annuity pairing. Under the declared interpretation, codes 90 and 92 are included through OFUM totals under the family basis, subject to documentary routing confirmation before registration; they are not silently transferred into the head/spouse SSI unit. Code 92 uses the family basis in row U4.

> 160: **Source-verification blocker:** the 2015 individual format calls code 20 “Legal Spouse,” but the family codebook’s spouse-sex variable ER60020 lists only female; ER60019 also retains older female-head inapplicability wording. Consequently, family-file income routing for a male code-20 record in 2015 remains **TO VERIFY**. Source documentation must resolve this before registration. Counts cannot establish routing, justify assuming such records absent, or waive this blocker. Any resulting change to the declared interpretation requires an explicit reviewed amendment.

> 1391: Required fields remain **TO VERIFY** until source adjudication is complete. Neither empty empirical categories nor observed outputs may substitute for documentary resolution.

Every option in 1d and 1e except the two holds (1d-3 and 1e-3) lets registration proceed while a documentary question is still open, so each amends one or more of these lines; each option names the lines it amends. Adopting such an option means Max ratifies that amendment explicitly. A ruling that picks an option without ratifying its amendment leaves draft 3's blocker in force.

### Amendment 1 (proposed): relationship routing by wave

Replace the single rule set in the §3 relationship table with the wave-specific routing below. Income roles, spouse-slot membership, annuity lives and marital resolution are recorded separately for each wave.

| Code | 2013 | 2015 | 2017 | 2019, 2021, 2023 |
|---|---|---|---|---|
| 10 | Head | Head | Reference person | Reference person |
| 20 | Spouse slot (legal wife) | Spouse slot; see blocker B1 | Spouse slot, either sex | Spouse slot, either sex |
| 22 | Spouse slot ("wife" cohabitor) | Spouse slot (female cohabitor) | Spouse slot (partner, either sex) | Spouse slot (partner, either sex) |
| 88 | OFUM (1c) | OFUM (1c) | OFUM (1c) | OFUM (1c) |
| 90 | OFUM; inherited 2013 rule | OFUM (documented) | OFUM (documented) | Financial route refused; see blocker B2 |
| 92 | Absent | Absent | OFUM, nonspouse (documented) | Financial route refused; see blocker B2 |

**1a. Documented routes accepted.** Accept the routes the adjudication resolved from documents (disposition D):

- 2015 code 90 is an OFUM income role outside the spouse loop. The spouse income and pension loops admit only 'CYAQRTH=202, 222' (q2015 pp. 89, 166), and the Big OFUM series admits 'FUP1YEAR[I].AQRTH.ORD>222' (q2015 p. 104). The PSID FAQ (question 74) adds that a Husband of Head, code 9 or 90, 'was asked the same questions as an Ofum'.
- 2017 codes 90 and 92 are OFUM income roles outside the spouse loop. q2017 p. 5 lists 901/902 and 921/922, and p. 95 sends the spouse repeat to 'CYAQRTH=201-222' and the OFUM series to 'AQRTH>222'.
- Code 90 keeps the co-resident legal-spouse annuity life and relationship-based marital resolution. Code 92 keeps §3's nonspouse conventions: it is not a legal-spouse life and never resolves a head's history as married.

**1b. 2013.** 2013 keeps the inherited meanings: code 90 is 'Legal husband of Head' (IND2023ER codebook p. 916), with the rules on the §3 lines 147, 150, 156 and 175.

**1c. Code 88 convention (adjudication A, all six waves).** A first-year cohabitor:

- has an OFUM income role on the family basis, and its SSI falls in §8's OFUM unit ('OFUM SSI totals form one individual unit');
- does not occupy the spouse slot;
- is not a legal-spouse annuity life;
- never resolves the head's or reference person's marital history as married by relationship code alone;
- keeps the recorded legal marital history;
- keeps the inherited administrative birth support.

The OFUM income gates include codes 881/882 in every wave (q2013 p. 97; q2015 p. 104; q2017 p. 95; q2019 p. 103; q2021 p. 205; q2023 p. 203). FAQ question 75 says 'Boyfriends and Girlfriends are treated like other family members who are not Reference Person ('Head' prior to 2017), Spouse or Partner.' A 2015 same-sex partner is code 98 with ER34304=1 (IND2023ER codebook p. 978). Such a person keeps the ordinary OFUM role, and no legal-spouse life follows from the code.

**1d. Blocker B1: a male legal spouse in 2015 code 20.** Part B verdict: **PARTIAL.** Official documentation routes every documented kind of male legal spouse in 2015 away from code 20:

- A husband in a heterosexual couple is Head: UserGuide2017 PDF p. 13, 'From 1968-2015, PSID conformed to the Census Bureau conventions' ... by designating the husband in households with heterosexual married adults, the 'Head''. FAQ question 73 says the same.
- A husband who is not Head is 'Husband of Head', code 9 or 90, and 'was asked the same questions as an Ofum' (FAQ question 74). The 2015 interviewer instructions call making 'a male spouse into Husband of Head instead of Head' a rare designation that needs study-staff permission (fam2015 QxQs p. 144).
- A same-sex partner is code 98, 'Other nonrelatives (includes same-sex partners ...)', flagged by ER34304 (IND2023ER codebook p. 978; UserGuide2015 PDF p. 33). Only 'As of 2017' are same-sex partners 'designated as Spouse/Partner ... rather than as an OFUM' (UserGuide2017 PDF p. 35).

What remains open: no document says in words that 2015 code 20 is never male, and FAQ question 70 says generally that from 2015 'Spouse indicates a legal marriage, while Partner is a cohabiting, non-legally married partner, where the couple can consist of heterosexual or same sex couples'. So the documents do not settle how the legally married same-sex spouse of a male Head was coded in 2015. If he was coded 20 (CYAQRTH 201), the 2015 spouse loops (202 and 222 only) and the OFUM gate (>222) would both have skipped him. Options:

1. **Documented rule plus a halting guard. Amends draft-3 lines 154, 160 and 1391.** 2015 code 20 occupies the spouse slot as documented. The authorized structural pass counts, and counts only, 2015 code-20 persons recorded male (ER32000=1) in family units that supply any U2 observation. If the count is zero, registration proceeds and nothing is routed or assumed for a male code-20 person. If it is nonzero, registration stops and the question in `docs/design/u2_m1b_psid_research.md` §1 goes to PSID; there is no exclusion, reassignment, zero-fill or imputation. Trade-off: a count decides whether registration proceeds without documentary resolution. Line 160 forbids exactly that ('Counts cannot establish routing, justify assuming such records absent, or waive this blocker'), and so do line 1391 ('Neither empty empirical categories nor observed outputs may substitute for documentary resolution') and line 154 ('it may not be established from counts'), so the option exists only as an explicitly ratified amendment to those lines. If the guard trips, registration stops for every row and Max rules again.
2. **Documented rule plus exclusion. Amends draft-3 line 160.** As option 1, but a 2015 family-unit observation containing a male code-20 person is excluded from every row under a named disposition, and the count is disclosed after the structural pass. Trade-off: registration always proceeds and the count decides nothing, but line 160's 'Source documentation must resolve this before registration' is replaced by a population rule. The population loses these units inside the 2015 cells listed under option 3, by a number unknown now, and each excluded record is one to which no document gives a meaning (1f).
3. **Hold the 2015 wave for PSID's answer. Draft 3 as written; amends nothing.** Trade-off: registration waits until PSID answers. By the §3 plan tables (lines 74–92), 2015 supplies U0's 1947 cell, one of its five, and three of U1's fifteen cells: the 1947 observation that U1 reuses from U0 and the 1946 age-68 and 1948 age-66 half-observations. Together these carry two of U1's ten birth-year weights. U0 is the headline row, so the headline waits indefinitely. Contact with PSID is Max's call.

**Recommendation for B1: send the PSID question in `docs/design/u2_m1b_psid_research.md` §1 now, and adopt option 1 only as an explicitly ratified amendment to draft-3 lines 154, 160 and 1391.** Until PSID answers or Max ratifies that amendment, option 3 governs: draft 3's blocker stands and the 2015 wave is held. If Max wants registration to proceed before PSID answers, option 1 is the proceed-option recommended here, for the reason in 1f: it never routes an undocumented category and never changes the population, at the price of letting a count decide.

**1e. Blocker B2: codes 90 and 92 in 2019–2023.** Part B verdict: **PARTIAL.** The instruments document that these persons get no Section G income questions:

- The spouse series admits 'CYAQRTH=201-222' (q2019 p. 102; q2021 p. 204; q2023 p. 202).
- The Big and Little OFUM series admit 'CYAQRTH=301-882 or 951-982' (q2019 pp. 103, 125; q2021 pp. 205, 243; q2023 pp. 203, 241).
- FAQ question 74 says codes 90 and 92 'are used when one half of the couple is adamant about not giving information about the other half, or when one half adamantly refuses to have their information included'.

No online document states whether any of their income, Social Security or SSI is edited or imputed into the family-file aggregates. The 2019, 2021 and 2023 codebooks mention uncooperative spouses only in relationship-code lists, marital and couple status, sample status and fertility variables. Options:

1. **Exclude and disclose. Amends draft-3 lines 152, 154 and 158 for 2019–2023.** Every 2019, 2021 or 2023 family-unit observation containing a code-90 or code-92 person is excluded from every row under a named disposition ('uncooperative spouse or partner in family unit'). This applies whether the target person is the reference person, the uncooperative spouse or partner, or another member. The rule is fixed now, before any count, and is vacuous if no such unit supplies an observation. The count is disclosed after the authorized structural pass and decides nothing. Trade-off: the documentary confirmation that lines 152, 154 and 158 require before registration is replaced, for these waves, by a population rule. The population loses these units inside the cells listed under option 3, by a number unknown now; FAQ question 74 describes only the institutional use of these codes as rare.
2. **Stated convention. Amends draft-3 lines 152, 154 and 158 for 2019–2023.** Use the family-file aggregates as released. The code-90 or code-92 person gets no separately recorded income, Social Security or SSI and no SSI unit of their own. Code 90 keeps the legal-spouse annuity life and marital resolution; code 92 keeps its nonspouse conventions. The count is disclosed. Trade-off: the persons stay in, but the estimate embeds undocumented processing, and family resources may fall short of the Report's concept, which includes a spouse's resources (cleared U2 statement).
3. **Wait for PSID documentation. Draft 3 as written; amends nothing.** Trade-off: registration waits. By the §3 plan tables (lines 74–92), 2019, 2021 and 2023 supply U0's 1951, 1953 and 1955 cells, three of its five, and eight of U1's fifteen cells: the 1951, 1953 and 1955 observations that U1 reuses from U0, both half-observations of 1952 and of 1954, and 1950's age-68 half-observation. Together these carry 5.5 of U1's ten birth-year weights, so U1 keeps only 1946–1949 and 1950's age-66 half. Most of the target waits indefinitely. Contact with PSID is Max's call.
4. **Documented rule plus a halting guard. Amends draft-3 lines 152, 154, 158 and 1391.** The authorized structural pass counts, and counts only, code-90 and code-92 persons in 2019, 2021 and 2023 family units that supply any U2 observation. If the count is zero, registration proceeds with nothing assumed. If it is nonzero, registration stops and the question in `docs/design/u2_m1b_psid_research.md` §2 goes to PSID; there is no exclusion or imputation. Trade-off: the population never changes, but a count decides whether registration proceeds without documentary resolution, which lines 154 and 1391 forbid. And unlike B1's guard, this one tests for a category the documents describe as in use in these waves: every 2019–2023 instrument lists codes 901/902 and 921/922, and FAQ question 74 says when the codes are used. Finding such a unit would add nothing to the documentary question, so the guard would work as option 3's hold, with a count choosing whether the hold applies. Not recommended.

**Recommendation for B2: option 1, adopted only as an explicitly ratified amendment to draft-3 lines 152, 154 and 158, with the question in `docs/design/u2_m1b_psid_research.md` §2 sent to PSID in parallel.** It is the only immediate option that places no assumption about the undocumented processing into any estimate and lets no count decide anything. Until Max ratifies it, option 3 governs. If PSID documents the processing before registration, Max may replace the exclusion with the documented rule by a reviewed amendment, never by reference to a count or outcome.

**1f. One standard for B1 and B2.** Draft 3 holds both blockers to one standard: code 92's routing is TO VERIFY 'under the same standard as the 2015 male code-20 blocker' (line 152), and code 90's is 'like the 2015 male code-20 blocker' (line 154). Every option in 1d and 1e is judged on the same four questions:

- **Does it put an undocumented assumption about PSID's processing into an estimate?** Only 1e-2 does.
- **Does a count decide anything?** Only the halting guards (1d-1, 1e-4) let a count decide: a zero count lets registration proceed without documentary resolution. The exclusions (1d-2, 1e-1) fix their rule before any count and use the count only for disclosure.
- **Does the population change?** The exclusions can change it, by a number unknown now. The guards and holds never do.
- **What coverage does a hold cost?** The costs are stated under 1d-3 and 1e-3 from the §3 plan tables.

On the second question an exclusion is the more conservative proceed-option wherever the excluded category is documented, and B2's is. Codes 90 and 92 are listed in every 2019–2023 instrument and codebook, FAQ question 74 says when they are used, and only the processing of their income is undocumented. Excluding their units removes exactly what is undocumented; a guard would only make a documented category into a stopping rule.

B1 differs in one respect. No document gives any route into 2015 code 20 for a male. Every documented kind of male legal spouse in 2015 goes elsewhere (1d), so a male code-20 record would be one the documents give no meaning to: a same-sex legal spouse, a recording error or something else. Excluding it would give it one, a unit to drop, and continue on the routing premise the record itself calls into question. The guard instead treats the record's existence as the documentary question it is and sends that question to PSID.

That is why B1's proceed-option is the guard and B2's is the exclusion. Both are amendments to draft 3, and neither exists until Max ratifies it. If Max prefers exclusion for B1 as well, option 1d-2 applies the B2 rule to B1 and amends line 160 only.

**1g. Counts and waivers.** Under draft 3, and under every option Max has not ratified, no refusal in amendment 1 is waived by observed absence and no count enters. The halting guards are the only options in which a count decides anything. A zero count that lets registration proceed is a waiver by observed absence, so a guard exists only as the explicitly ratified amendment its option names. A count enters only as a ratified option states, inside the authorized structural pass.

### Amendment 2 (proposed): annuitant input precedence

For annuity lives and every age- or sex-dependent rule, use each person's recorded sex (ER32000) and derived income-year age (§3 Annuitant ages). The family-file spouse age and sex variables are slot metadata only:

| Wave | Spouse age | Spouse sex |
|---|---|---|
| 2015 | ER60019 | ER60020 |
| 2017 | ER66019 | ER66020 |
| 2019 | ER72019 | ER72020 |
| 2021 | ER78019 | ER78020 |
| 2023 | ER82020 | ER82021 |

Their 'Head is female or single male' or 'Reference Person is female or single male' inapplicability wording never decides whether a person occupies the spouse slot. Slot occupancy comes from amendment 1. This amendment repairs no refused financial mapping.

Registry effect after a ruling: the ten `wife_age` and `wife_sex` records become metadata-only records with a no-slot-inference rule.

### Amendment 3 (proposed): historical spouse-retirement crosswalk

The six `wife_retirement_annuities` crosswalk records (2013–2023) stay non-executable. No scalar equivalence is asserted between U1's combined 'WIFE RETIREMENT/ANNUITIES' item and the later separately documented spouse pension, annuity, IRA and other-retirement items (for example 2017 ER71369, ER71371, ER71373 and ER71375; FAM2017ER pp. 2015–2016). Those components, spouse IRA income included, stay inside total family money income under §4. They are never added a second time. No row changes.

### Amendment 4 (proposed): wealth accuracy-flag erratum

The registries already record the nine corrected targets (adjudication D). The literal codebook wording is preserved in `codebook_text` and `source_wording_conflict`.

| Flag | Codebook says 'Accuracy of' | Corrected target |
|---|---|---|
| 2013 ER58212 (WEALTH2) | ER58209 | ER58211 |
| 2013 ER58162 (checking/saving) | ER581614 (no such variable) | ER58161 |
| 2015 ER65409 (WEALTH2) | ER65406 | ER65408 |
| 2015 ER65359 (checking/saving) | ER653584 (no such variable) | ER65358 |
| 2017 ER71486 (WEALTH2) | ER71483 | ER71485 |
| 2017 ER71436 (checking/saving) | ER714354 (no such variable) | ER71435 |
| 2019 ER77512 (WEALTH2) | ER77509 | ER77511 |
| 2021 ER81839 (WEALTH2) | ER81836 | ER81838 |
| 2023 ER85693 (WEALTH2) | ER85690 | ER85692 |

Proposed rule: use these flags only for the specified imputation diagnostics. The corrections never change an amount or a sample-inclusion decision.

### Amendment 5 (proposed): pension predicates and source precedence

**5a. 2017–2023 (adjudication D).** Replace the generic previous-employer account route in §15 with wave-specific routes. Only P46=5 (DC only) reaches P64/P65. Formula (P46=1), combined (7), DK, refused and NA plans are off-route for P64/P65 and carry a named disposition. Evidence: P62ACKPT on q2017 p. 152, q2019 p. 163, q2021 p. 304 and q2023 p. 302, which reads '1. DB Only (P46=1)', '3. DC Only (P46=5)' and '5. All Others'; the first and third go to P69. Combined plans use P48/P49 once; disposition 3 (left to accumulate) is counted and disposition 2 (IRA rollover) is excluded.

**5b. 2015 (adjudication A).** Admit the documentary intersection: P46=5 reaches P64/P65, and P46=7 reaches P48/P49. Refuse the disputed P62ACKPT branch, pending PSID clarification. Its heading reads 'P46=1 AND P52=1 AND P62AMT= DK/RF', while its branch label reads only '1. P62AMT =DK/RF' (q2015 p. 164), and FAM2015ER p. 692 (ER62057) makes P65 inapplicable for 'defined benefit retirement plan or combination plan (ER61990=1 or 7)' and 'NA or RF type of retirement plan (ER61990=9)', but not for DK (8). An amount reached only through that branch is off-route under a named disposition, never zero-filled.

**5c. U7's 2015 spouse slot.** The adjudication's F refusal stands: P70CKPT admits only 'CYAQRTH=202, 222' (q2015 p. 166). If Max adopts option 1d-1 or 1d-2, U7's 2015 spouse slot is the documented female spouse or partner slot, and the same guard or exclusion applies to U7. Without a ruling on 1d, U7 stays unavailable, and no assumption of absence or zero balance is permitted. Removing U7 would need its own reviewed amendment.

Proposed replacement for §15 `income_concept.employer_dc.previous_routes`:

```json
"previous_routes": {
  "both_items": ["both"],
  "account_items_by_wave": {
    "2013": ["account", "formula", "dk"],
    "2015": ["account"],
    "2017": ["account"],
    "2019": ["account"],
    "2021": ["account"],
    "2023": ["account"]
  },
  "refused_branches": {
    "2015": "P62ACKPT: P46=1 AND P52=1 AND P62AMT=DK/RF"
  }
}
```

2013 keeps the route inherited from U1 (registry `pension:2013.route.formula_unknown_checkpoint`). After a ruling, the registry releases the P64/P65 records blocked by `pension:{2017,2019,2021,2023}.route.inherited_route_amendment`.

### Amendment 6 (proposed): 2017 individual cross-sectional weight

**Identity.** The 2017 observation weight is ER34651, 'CORE/IMM INDIVIDUAL CROSS-SECTION WT 17', as released in the 1968–2023 individual file. Its codebook note reads 'This variable has been updated for all individuals in 2017 including the Immigrant 2017 sample' (IND2023ER codebook p. 1224). Selection is positive weight. There is no immigrant exclusion, no reconstructed weight and no recalibration.

**Blocker B3: construction documentation.** Part B verdict: **PARTIAL.** The first version of this draft said NOT DOCUMENTED ONLINE; it missed the 2023 cross-sectional report that milestone 1 had already pinned (research record §3, item 7).

- The May 2019 release notes say 'the weights for the 2017 Immigrant individuals remain zero and will be updated in Release 3' (DataRelease-May2019 p. 1). UserGuide2017 PDF p. 62 documents the update but dates it to 'Release 2 of PSID-2017 data'. The documents conflict on the release number, not on the update, which the 1968–2023 codebook confirms (research record §3, item 3).
- The June 2026 report on the 2023 cross-sectional weights (`tests/data/track_u2/psid_sources/cross_sec_weights_23.pdf`) documents the 2017 population control. Table A3 (PDF p. 14) names ER34651 as the 2017 individual weight. Table A2 (PDF p. 13) prints the 2017 sum of the individual weights beside the ACS one-year PUMS population total and marks the CPS column 'Not Used'. Its note says that donut-hole families and post-1997 immigrants living in group quarters 'were excluded from the ACS estimate in 2017'. PDF p. 6 says PSID 'started to use a different approach to select the calibration variables since 2017', and PDF p. 3 points to Chang et al. (2021), the 2019 longitudinal report, for the 2017 Immigrant sample's recruitment.
- The February 2019 construction report has the same content digest as the Internet Archive capture of 15 June 2019, the only archived version. It post-stratifies 2017 to 'population totals that excluded the foreign-born individuals who entered the U.S. after 1997'. It says the 2017 sample's 'weighting methodology will be available from the PSID website' (cross_sec_weights_17 PDF pp. 3, 9). It predates the revision.
- The 2019 report says only that 'A cross-sectional family weight was created in 2017' to include that sample (cross_sec_weights_19 PDF p. 2).
- **Still undocumented:** the 2017 base weights, in particular for the 2017 Immigrant sample, whose 2017 longitudinal family weight is zero (cross_sec_weights_23 PDF p. 2, note 3); and the 2017 raking dimensions, meaning the calibration variables, interactions and trimming that the 2017 selection produced. Neither the official documents page (Internet Archive, 13 August 2026) nor the technical-paper list (Internet Archive, 17 September 2025) lists a document on them. The documents page also omits the June 2026 report above, so its silence does not show that no such document exists online.

Options:

1. **Use the released weight and disclose. Amends draft-3 line 134.** Use ER34651 as released. Registration states what PSID has documented about the revised 2017 weight (its identity, the ACS one-year PUMS control with its two named exclusions, and the calibration-variable selection approach used since 2017) and that PSID has not published its 2017 base weights or raking dimensions. Line 134 reads, verbatim: 'The weight construction and immigrant-refreshment coverage must be documented before registration.' Under this option that sentence is met for 2017 by the documented coverage and population control plus the disclosure. That is a reading of line 134 as satisfied by partial documentation, so it too needs Max's explicit ratification. The exact question in `docs/design/u2_m1b_psid_research.md` §3, now limited to the base weights and raking dimensions, is queued for Max to send or not. Trade-off: the 2017 base weights and raking dimensions stay unknown; the builder changes nothing in PSID's released weight.
2. **Hold registration for PSID's construction document.** Trade-off: registration waits. By the §3 plan tables (lines 74–92), 2017 supplies U0's 1949 cell, one of its five, and three of U1's fifteen cells: the 1949 observation that U1 reuses from U0 and the 1948 age-68 and 1950 age-66 half-observations. Together these carry two of U1's ten birth-year weights. The headline row waits indefinitely.
3. **Substitute the documented longitudinal weight ER34650 for 2017.** Trade-off: a different estimand. The weight is zero for the 2017 immigrant sample and its construction differs from the other waves' cross-sectional weights; this contradicts §3. Not recommended.

**Recommendation for B3: option 1, adopted as an explicitly ratified amendment to draft-3 line 134.** It follows the adjudication, and the builder makes no assumption about or modification to the released weight. Option 2 is the stricter alternative if Max wants line 134 kept literally.

### Registry effect of the rulings

| Amendment | On ruling |
|---|---|
| 1 | Record 1a–1c. Replace the eight F refusals with the chosen B1 and B2 options. Release dependents accordingly |
| 2 | Resolve the ten spouse age/sex records as metadata-only |
| 3 | Resolve the six crosswalk records as non-executable metadata |
| 4 | None; already recorded |
| 5 | Resolve the 2015 checkpoint as 5b. Release the 2017–2023 P64/P65 records. Replace the §15 fragment |
| 6 | Resolve the 2017 weight record under the chosen option |

Each registry change after a ruling is its own reviewed commit. No ruling changes a U1 file.

## 17. Review record and outstanding work

The adversarial review of `u2-draft-1` returned **RATIFIABLE AFTER EDITS**. Rev1 (`u2-draft-2`) applied those edits. Its round-diff check returned **REVISE**, identifying R1–R8. Round 2 (`u2-draft-3`) applied every exact edit and retained the earlier resolutions.

Milestone 1 then built the documentary source registries (`data/external/track_u2/`, master record `docs/design/u2_m1_source_adjudication.md`). The independent adjudication of that work (`EV/phase2-20260927/out/u2-adjudicate.md`) returned **ERRORS FOUND**: 18 wrong citations, now corrected; 16 items resolvable from documents, now resolved; 8 routes refused, now encoded as explicit refusals; and 24 items that need conventions, still open. Milestone 1b researched the three documentary blockers from official PSID documentation and wrote `u2-draft-4` (§16a). No amendment in §16a is ratified, and this document claims no new referee verdict and no completed implementation.

What remains before ratification:

1. Max rules on amendments 1–6 in §16a, choosing one option each for blocker B1 (2015 male code 20; Part B PARTIAL), B2 (codes 90 and 92 in 2019–2023; Part B PARTIAL) and B3 (construction of the revised 2017 weight; Part B PARTIAL). An option that lets registration proceed before documents resolve B1 or B2 takes effect only if Max also ratifies the amendment to draft-3 lines 152–160 or 1391 that the option names; otherwise that blocker's hold governs.
2. Each ruling is applied to the registries in its own reviewed commit. Until then the 24 TO VERIFY records stay open, the 8 refusals stand and the 2017–2023 P64/P65 records stay blocked.
3. The B1 and B2 recommendations ask Max to send PSID the questions in `docs/design/u2_m1b_psid_research.md` §§1–2 now; §3 holds the B3 question. Sending them is Max's call. Nobody has contacted PSID.
4. Verify identification support, observation plans and refreshed design domains; weight documentation follows the amendment 6 ruling.
5. Pin the SSI parameter file in §15. The capture exists and the adjudication reconfirmed all 106 source hashes.
6. Complete historical-isolation and cross-cohort refusal tests (milestone 2).
7. Produce U2 invented dry-run and exact U1 differential evidence (milestone 2).
8. Complete the pre-registration structural, reconciliation and F17 component pass, including only the counts that the chosen B1 and B2 options name.
9. Check the specification, literal named deltas, parameter block (with the amendment 5 fragment if ruled), manifests and ten-row implementation for equality.
10. Obtain ratification, then a fresh forecast and an independent forecast check.

Required fields remain **TO VERIFY** until source adjudication is complete. Neither empty empirical categories nor observed outputs may substitute for documentary resolution.

## 18. Reading record, blindness and exposure

### Evidence-directory inventory

Draft-1’s reported inventory is retained as historical exposure:

1. `EV/RESTRICTED-FILES.md`
2. `EV/exercise2-definitions-cleared-20260924.md`
3. `EV/heldout-feasibility-20260927.md`
4. `EV/heldout-target-pick-20260928.md`
5. `EV/track-a-oneshot-20260923/COMPARISON.md`
6. `EV/fra68-oneshot-reg15-20260925/COMPARISON.md`
7. `EV/track-u-oneshot-reg16-20260927/COMPARISON.md`
8. `EV/track-m-oneshot-reg17-20260927/COMPARISON.md`

Rev1’s parent and three read-only audit agents reported accessing only these EV files:

1. `EV/RESTRICTED-FILES.md`, first.
2. `EV/phase2-20260927/out/u2-spec-draft.md`.
3. `EV/phase2-20260927/out/u2-spec-review.md`.
4. `EV/u2-target-availability-cleared-20260928.md`, SHA-256 `2ffa3092d297418c58868f7e5326c3e4c8047b129171b40b66fde5ee07702211`: rows, tables, units, rounding, cohort. **Read in full; rehashed and matched.**
5. `EV/exercise2-definitions-cleared-20260924.md`.
6. `EV/heldout-feasibility-20260927.md`.
7. `EV/heldout-target-pick-20260928.md`.

The four public memos were not reopened for rev1 or round 2; their draft-1 exposure and the permitted inputs’ discussion of related results remain disclosed. Some other reads were selected excerpts or truncated displays.

No comparator directory, comparator seal, uncleared U2 availability statement, U2 values scan, restricted scratchpad or Boomers Report PDF was opened.

### Repository and PSID reading

Rev1’s repository content inspected included:

- U1 specification and `pyproject.toml`.
- `S/cohorts/age67.py`.
- `S/data/family_income.py`, `data/tr2008.py`.
- `S/estimates/adjusted_poverty.py`, `uniform_cut_tabulation.py`, `career.py`.
- Track U `runner.py`, `invented.py`, `diagnostics.py`.
- Track M `thresholds.py`.
- `scripts/track_u_dry_run.py`, `run_track_u_registered.py`, `capture_track_u_parameters.py`, `first_estimates_birth_evidence.py`; search hits in `track_u_structure.py`.
- U1 specification, artifact, dry-run, runner, registered-script and integration tests; historical reducer identity/reachability tests.
- The committed U1 artifact’s input-frame-hash field.
- The parameter captures and SSA snapshot named in §§5–9.

Repository searches also returned isolated matching lines in existing tests. No raw PSID contents were searched.

Rev1’s PSID content reads were confined to metadata:

- `IND2023ER.sps`, `IND2023ER_formats.sps` and selected individual-codebook entries.
- Family setup files and selected family-codebook entries for 2015, 2017 and 2023.
- Filename-only documentation listings.

Draft-1’s earlier metadata reading included all five later family setup files and selected entries in their codebooks. The revised verification statuses distinguish those inherited checks from new checks.

One rev1 revision-lane codebook search incidentally displayed published whole-sample frequency columns beside relationship definitions. Those counts were not used, reproduced as findings or computed from raw data. Draft-1 reported a similar incidental metadata display.

The team also read the machine's global agent-rules file (`AGENTS.md`).

### Public parameter sources

Rev1’s parameter audit inspected official govinfo notice/index metadata and SSA republications identified in §8. These establish source citations; notice staging, downloaded-byte hashes and full U2 parameter verification remain unfinished.

### Round-2 reading and verification

This round’s parent and three read-only audit agents accessed only these EV files:

1. `EV/RESTRICTED-FILES.md`, first.
2. `EV/phase2-20260927/out/u2-spec-rev1.md`.
3. `EV/phase2-20260927/out/u2-rev1-check.md`.
4. `EV/u2-target-availability-cleared-20260928.md`, read in full and rehashed to the recorded `2ffa3092…` hash.
5. `EV/exercise2-definitions-cleared-20260924.md`, hash-only access; the recorded `a3978b68…` hash matched.

The U1 specification was rehashed to the header’s pin. Current source inspection covered its employer-DC block; `S/cohorts/age67.py`; Track U `runner.py` and `rows.py`; `S/estimates/adjusted_poverty.py` and `cola_age_profile.py`; `scripts/track_u_dry_run.py` and `run_track_u_registered.py`; and `tests/track_u/test_runner.py` and `test_registered_script.py`. Repository-only searches returned additional matching source/test lines. The team also read the machine's global agent-rules file (`AGENTS.md`).

PSID reads remained documentary: the six relationship-format blocks in `IND2023ER_formats.sps`, family-codebook pages 6–8 for 2015 and 2017, and in-memory full-text searches for “uncooperative” in the 2015, 2017, 2019, 2021 and 2023 family codebooks. The first twenty matching snippets per codebook were requested; displays were partly truncated. These searches do not establish the still-blocking family-file income routing. Published whole-file frequency columns appeared incidentally in codebook excerpts; they were not used to adjudicate routing or reproduced as findings. No raw PSID records were read.

The code-88/code-92 label checks, corrected annuitant-support citations, R5 hash-refusal call, R6 preflight signature and path expressions, employer-DC key and named-delta renderer were checked directly against these sources. The 2017 spouse-sex citation is corrected to printed page 7. No public result memo, restricted source or Boomers Report PDF was reopened, and no web retrieval or file staging occurred in round 2.

### Inherited exposure and forecast requirement

The feasibility review establishes no blanket certification of earlier builder blindness. It distinguishes prior restricted-page exposure, uncleared-definition exposure, validation-lane comparator access and possible exposure through shared scratchpads.

This revision reports its own bounded reading; it does not infer that every earlier builder saw the held-out cells.

Use a fresh, isolated forecaster with no inherited comparator-reading context. The forecaster must read the restriction ledger first, disclose all reading and prior exposure, explicitly disclose reading all four authorized public result memos, remain outside restricted sources, freeze its forecast before the real outcome run, and obtain an independent check.

No forecast is supplied here.

## 19. Changelog and work report

**`u2-draft-2`:**

- Read and rehashed the cleared target-availability statement.
- Corrected target confirmation, labels, schema and precision metadata.
- Defined the relationship-code amendment and documented remaining source-routing blockers.
- Added birth anchors, refreshed design strata and missing documentation.
- Restored U1’s pre-registration structural/component allowance.
- Removed the unsupported nine-row `-F` population contrast, leaving ten rows.
- Supplied complete named-delta texts.
- Added annual SSI citations, capture requirements and exact overlap checks.
- Protected historical source identity and U1 wave/default behavior.
- Specified actual differential outputs, zero tolerance, fixed metadata exclusions and refusal parity.
- Added invented dry-run, testing, isolation and ratification requirements.
- Corrected the review’s row-count and verifier-docstring inaccuracies.

Rev1 verification comprised read-only source inspection, metadata hashing, parameter-entry equality and source-label/citation checks.

**`u2-draft-3` (round 2):**

- Added code 92’s explicit role and source-routing blocker, and code 88/92 wave-specific label tests.
- Required documentary confirmation of code 90/92 income routing; retained the 2015 male-code-20 blocker.
- Corrected administrative birth-support citations and the 2017 spouse-sex codebook page.
- Specified both hash-refusal calls and complete existing-artifact/sidecar preflight calls, exact paths and mocks.
- Restored the employer-DC `reader` key.
- Removed terminal periods from all 26 literal named deltas and documented renderer punctuation.
- Retained the earlier review appendix and appended the round-diff check mapping.

Round-2 verification comprised read-only source inspection, the three metadata hash checks in §18, and in-memory document checks for JSON syntax, required additions, all 26 delta strings and preservation of unaffected sections. The specification’s model tests and future refusal/differential harnesses were not executed.

**No files were written, no commit was made, no model test or model run was executed, and no outcome or structural statistic was computed on real PSID data.** Existing workspace changes were preserved. The explicit no-files instruction governs this deliverable.

**`u2-draft-4` (milestone 1b, proposed; pending Max's ruling):**

- Applied the independent adjudication to the source registries and master record: 18 citation corrections (amendment 7), 16 documentary resolutions and 8 explicit refusals. 24 items stay TO VERIFY. A builder-found fix points the six code-88 citations at line 190 instead of line 198.
- Researched the three documentary blockers from official PSID documentation: B1 PARTIAL, B2 PARTIAL, B3 NOT DOCUMENTED ONLINE, revised to PARTIAL on 2026-09-29 (`docs/design/u2_m1b_psid_research.md`; sources and hashes in `tests/data/track_u2/psid_docs/manifest.json`).
- Added §16a: proposed amendments 1–6, each open blocker's options with trade-offs, and a recommendation chosen by the stated conservatism rule and never by effect on results.
- Rewrote §17's outstanding work, updated §20 and bumped the version line and the §15 `version` key.
- Changed no line that a registry cites. Lines 1–1374 keep their draft-3 numbering, and every cited line keeps its draft-3 text; `tests/track_u2/test_adjudication_applied.py` pins both.

Milestone-1b verification comprised documentary source checks, the registry and birth-evidence tests, and Black and Ruff. No model run was made, no estimator was executed and no statistic was computed on real PSID data. Reading and exposure are recorded in `docs/design/u2_m1b_exposure.md`.

**`u2-draft-4`, revised after the independent review (2026-09-29; `EV/phase2-20260927/out/u2-m1b-review.md`, REQUEST CHANGES):**

- §16a quotes draft-3 lines 152, 154, 158, 160 and 1391 verbatim, and each B1 and B2 option names the lines it amends. The B1 halting guard is marked as an amendment to lines 154, 160 and 1391. The B1 recommendation is now to send the PSID question at once and adopt the guard only as an explicitly ratified amendment (review finding 1).
- Every hold option states its coverage cost from the §3 plan tables, including the odd-birth observations U1 reuses from U0; the exclusion options name the same cells (finding 4).
- B2 gains a halting-guard option, judged not viable. The new 1f states one standard for B1 and B2 and why their proceed-options differ. 1g replaces the old 1f, whose 'No refusal in amendment 1 is waived by observed absence' contradicted the guard (findings 1 and 5).
- B3's verdict is PARTIAL, not NOT DOCUMENTED ONLINE. The June 2026 report on the 2023 cross-sectional weights, already pinned by milestone 1, documents ER34651's identity, the ACS one-year PUMS population control for 2017 (CPS not used) with its two named exclusions, and the calibration-variable selection approach in use since 2017. The 2017 base weights and raking dimensions remain undocumented. Amendment 6 option 1 is marked as an amendment to draft-3 line 134; the PSID question drops its population-control part; the release-number conflict between UserGuide2017 p. 62 and the May 2019 notes is recorded (findings 2 and 10).

## 20. Ratification and execution record

**Pending.**

1. Resolve the proposed decisions and source-verification blockers. **Decisions: done (Max, d514, 2026-09-28, adopting every §16 default).** Source-verification blockers remain for steps 2–5. **`u2-draft-4` amendments 1–6 (§16a): proposed, pending Max's ruling**, including the options for blockers B1, B2 and B3.
2. Complete implementation, manifests and parameter capture.
3. Complete independent mapping review, invented tests, historical-isolation checks and exact U1 differential evidence.
4. Complete the authorized pre-registration structural, reconciliation and F17 component pass; resolve mapping failures.
5. Materialize the final parameter block and U2 rulings record; require exact code/specification agreement.
6. Ratify the specification by merge.
7. Obtain and independently check the fresh forecast.
8. Post the issue #42 registration with exact commit, specification hash, input and parameter pins, rows, headline, plans and exposure disclosure.
9. Execute the one-shot under the required launchd process.
10. Verify and commit the new artifact and sidecar without changing existing runs.
11. Only then may the validation lane open the held-out comparator for comparison.
12. Publish every registered result regardless of outcome.

Registration must state that U0 observes five birth years at exact age 67; row U1 covers all ten births through its registered age approximation; and the exercise is a static simulation on PSID-observed incomes.

## Appendix: Review item → where resolved

| Review item | Where resolved |
|---|---|
| E1.1: read, rehash and inventory cleared U2 statement | §§1–2, 18; exact matching SHA-256 recorded |
| E1.2: formats-file reading inventory | §§3, 18 |
| E2.1: replace pending validation confirmation | §1; required replacement text |
| E2.2: remove confirmation blocker | §15 `blocked_by` |
| E2.3: report rows, unit and two definition extracts | §15 `target` |
| E2.4: complete Gender and Marital Status labels | §9 |
| E2.5: printed hyphenated column label | §1 |
| E2.6: consumer-price indexing | §6 |
| E3.1: pre-registration checks and F17 summaries | §§4, 9, 14, 16, 20; exact replacement plus clarification of allowed aggregates |
| E3.2: `seed_wave_rule` and explicit departure | §§3, 15–16 |
| E3.3: U1 parameter-block keys | §15; `scored`, `registered_artifact`, nested uncertainty and comparison keys included |
| E3.3: conditional `-F` population keys | Superseded explicitly by §§3, 11 and 16’s removal of all nine `-F` rows; U1 unchanged |
| E3.4: label new memo clarifications | §10a |
| E3.5: full delta texts, projection wording, row U1 and pandemic qualification | §12; literal-text equality required before ratification |
| E3.6: invented U2 dry run | §§13–15, 20 |
| E3.7: loose “partner” wording | §3 annuitant-age wording; actual inherited administrative support selection distinguished from legal annuity lives |
| E4.1: relationship-code change and amendment | §3 role rules, wave-label table, source citations and explicit 2015 routing blocker |
| E4.1: verifier factual correction | §3; code already checks 90, despite its docstring |
| E4.2: reported-birth-year anchors | §3 anchor table |
| E4.3: strata 88–94 and invalid-design refusal | §§10, 13 |
| E4.4: 2013 documentation and missing 2023 weights document | §§3, 8 |
| E4.5: code `file:line` citations | §14 implementation table and wave-isolation section |
| E5.1: Census workbook provenance | §6; required replacement text |
| E5.2: exact 2012 Census overlap | §§6, 13 |
| E5.3: inherited mortality provenance | §5 |
| E5.4: separate SSI capture, revision refusal, annual citations, retrieval records, overlap and constancy | §§8, 13, 15 |
| E5.5: download authorization | §§8, 16; required replacement text |
| E6.1: protected source files and exclusions | §14; exact exclusions and reachability checks |
| E6.2: U1 wave pin and coupling | §§13–14 |
| E6.3.1: same invented seed and supplement-refused fallback | §13 runnable differential procedure |
| E6.3.2: canonical serialization and fixed exclusions | §13; entire JSON/Markdown byte equality, zero tolerance |
| E6.3.3: plans, decisions, rulings, deltas, rows, column and loader hashes | §13 additional contract checks |
| E6.3.4: fixed refusal table | §13 refusal-parity cases |
| E6.3.5: unmodified U1 tests | §13 command, integration boundary and explicit skip reporting |
| E6.3.6: optional real structure-only U1 hash check | §13; explicit OK required; full pin recorded |
| E6.4: reciprocal cohort, parameter, seed, rulings and path refusals | §14 |
| Review §7: per-observation monotonicity, every row and half | §13 |
| Review §7: tighter SSI bounds | §13 |
| Review §7: plan invariants and support/design separation | §§3, 10, 13 |
| Review §7: parameter coverage, precision and revision tests | §§6, 8, 13 |
| Review §7: relationship and birth-anchor label tests | §§3, 13 |
| Review §7: exclusion/reachability tests | §§13–14 |
| Review §8: observation convention | §§3, 16 |
| Review §8: common support departure | §§3, 16 |
| Review §8: row-set amendment and fallback | §§3, 11, 16; ten-row arithmetic corrected |
| Review §8: income/mortality conditional on role amendment now | §§3–5, 16 |
| Review §8: SSI capture and downloads | §§8, 16 |
| Review §8: comparison/publication | §§10a, 16, 20 |
| Review §8: dry run and pre-registration checks before forecast | §§14, 16–17, 20 |

## Appendix: Check item → where resolved

| Check item | Where resolved |
|---|---|
| R1: explicit code-92 role, 2017–2023 scope, no legal-spouse annuity or married resolution, source-routing status | §3 role table and following code-92 paragraph; §13 role cases; §15’s `relationship_rules` references the amended §3 |
| R2: code-88 and code-92 label columns, absence/presence tests and exact source lines | §3 mandatory relationship-label table and Sources; code 88’s label change is explicitly verified |
| R2: required test coverage and machine-readable code set | §13 Labels retains reported-birth-year checks and adds all required relationship tests; §15 `population.relationship_codes_tested` is `[10,20,22,88,90,92]` |
| R3: code-90 documentary evidence standard and shared routing blocker | §3 code-90 paragraph and conditional SSI routing; §15 `code90_code92_income_routing_source_resolution`; §17 item 2; counts cannot substitute for documentation |
| R4: both administrative birth-support line corrections | §3 Annuitant ages cites `age67.py:327` and `:946`; inclusion is separate from legal-spouse status |
| R5: threshold and SSI hash-refusal functions | §13 Fixed refusal-parity cases names `runner._check_parameters(params, ap.REGISTERED_REAL)` for both, exact provenance replacements, fresh committed parameters and source-confirmed exception type |
| R6: existing-artifact preflight call and existence target | §13 refusal table and exact mock setup; full keyword arguments, fixed artifact path, `exists_artifact_only`, scoped patch and exact exception |
| R6: existing-sidecar preflight call and existence target | §13 refusal table and exact mock setup; same full call, artifact absent, exact `.env.json` sidecar present, `exists_sidecar_only` and exact exception |
| R7: employer-DC reader key | §15 `income_concept.employer_dc.reader = "TO_VERIFY_u2_employer_dc_adapter"` |
| R8: literal-delta punctuation | §12 exact renderer explanation and D01–D26 without terminal periods; all other delta text preserved |
| Check §1: retain every earlier resolution, ten-row arithmetic and existing verifier coverage | Earlier review appendix retained in full; §§3, 11 and 13 preserve ten U2 rows, nineteen U1 rows and existing code-90 verifier coverage |
| Check §2: wave-specific semantics, harmless code-10 source typo, code-88 support versus code-92 role | §3 requires exact documented prefixes, keeps administrative support distinct and does not silently add code 92 |
| Check §3: exact U1 differential procedure and supplemental harness status | §13 original runnable procedure, fixed exclusions, zero tolerance and “to build” disclosure retained; R5/R6 close the call-site gaps |
| Check §4: mapping checks before the one-shot | §§4, 9, 14, 15, 16 and 20 preserve the pre-registration pass, blocker and frozen-identity recheck |
| Check §5: U1-compatible parameter keys | §15 preserves inherited keys and explicit U2 departures; R7 supplies the missing reader key |
| Check §6: bounded verification and blindness | §§2, 17–19 distinguish inherited verification, current documentary checks, outstanding routing/parameter work and unexecuted model tests; no held-out value or direction is supplied |
