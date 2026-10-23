# Track B B0.2: landscape

**Status: synthesis of five landscape lanes, 2026-10-23. It computes
nothing and freezes nothing.** It feeds B0.2's structural-audit
protocol, which is frozen before any count, and the questions for Max.

Five read-only lanes ran on 2026-10-21 and 2026-10-22, as set out in the
B0.2 plan (`docs/design/track_b_b0_2_plan.md`, section 3, step 1):

| Lane | Subject | Output |
|---|---|---|
| a1 | Repository and staged-data inventory | `lanes/a1-repo-inventory-out.md` |
| a2 | Microdata sources and access | `lanes/a2-microdata-access-out.md` |
| a3 | Public aggregate and administrative sources | `lanes/a3-aggregate-sources-out.md` |
| a4 | Exposure catalogue for each gate's candidate holdouts | `lanes/a4-exposure-catalog-out.md` |
| a5 | Per-gate requirements and J's joint record | `lanes/a5-gate-requirements-out.md` |

The outputs are in
`microcosm-launch-evidence/dynasim-parity-20260909/trackb-b0-2-20261021/`.
No lane read survey microdata, computed a count or ran a script. Where a
lane could not open a source page, it marked the fact **UNVERIFIED**, and
this synthesis keeps that label.

## 1. What each gate can draw on now

**Staged and readable on this machine** (a1, section 1):
- PSID family files 1968-2023, the cross-year individual file, the
  marriage history, childbirth history and relationship matrix;
- SSA's 2006 Earnings Public-Use File (EPUF), hash-pinned;
- committed SSA, Trustees, CBO, NCHS and DI ASR tables under
  `data/external/`.

**Not staged:** SIPP, CPS ASEC and CPS tenure files. **Absent:** any HRS
file or HRS loader, and any reader for SSA's Benefits and Earnings
Public-Use File (BEPUF), the Master Beneficiary Record or another
SSA-linked file.

| Gate | What exists | What is missing |
|---|---|---|
| B3 | Head and spouse earnings at all ages from the family files; odd income years; EPUF through 2006; B2's and M6's cell and support helpers | A cell family for ages 62-69; other family members' earnings; an HRS loader if B3 uses HRS; evidence of an unused partition |
| B3L | The panel through income year 2022; boundary and origin already parameters | A 2006-origin domain reaching ages 62-69; everything B3 lacks |
| B4 | Marriage histories and transitions; candidate 16's port; roster-only widowhood; the DI engine; self-reported disability; deaths by year; forward support | A person-level administrative DI holdout; deaths separated from attrition; widowhood linked to the spouse's death; entrants |
| I's timing gate | Marriage months; DI award year; aggregate tables by month of entitlement; a SIPP job-month reader (data not staged) | Dated person-level death, award, claim and conversion events; a monthly-receipt loader; an event journal |
| B5-empirical | R1, R2 and R3 statutory modules; annual PSID Social Security amounts | Any withholding or deduction observation; RET-countable earnings |
| B6a | A marginal claiming distribution; first observed receipt year; receipt history; years of coverage | Insured status; an insured, unclaimed person-month risk set with entitlement months |
| B6b | The FRA schedule and B6a's pieces | Identifying policy variation, and B6a's gaps |
| J | Self-reported benefit types; opening status; spouse links; the G layer; exposed aggregate SSA tables | Estimands and limits; a holdout independent of B2; a joint truth builder; administrative payment and recipient denominators |

**External candidates** (a2, a3), all still to be chosen:

| Source | Strongest use | Access | Status |
|---|---|---|---|
| HRS public files and the RAND HRS longitudinal file | B3 at ages 62-69; B4 deaths separated from attrition; self-reported claim and DI dates for I; joint states for J | Registration; whether an agent lane may work on files a person registers is UNVERIFIED | Pages refused automated fetches |
| HRS files linked to SSA records | Administrative earnings, insured status and entitlement dates for B3, B6a and I | Virtual-desktop enclave run by a named person; 6-8 week decision (search snippet); likely an institutional sponsor and IRB | UNVERIFIED |
| SIPP public-use panels | Monthly receipt, earnings and marital status | Public download | Variables verified through the Census API |
| SIPP Synthetic Beta, validated on the Gold Standard File | Insured status and claim timing for older cohorts, to 2014 | Application approved in about five business days; real results only through Census validation | Verified on census.gov |
| FSRDC files linking SIPP, CPS or ACS to SSA records | Everything, including possible deduction fields | Person with Special Sworn Status on site; 6-12 months; $15,000-20,000 a year per project | Verified on the SAP catalog and RDC pages |
| BEPUF 2020 | Structural and recipient-side sanity checks only | Public CC0 download | **Fully synthetic** (section 5): not observed data, so not a holdout for J, B5-empirical or I |
| Disability Analysis File | Monthly disability participation, with birth and death dates | "Restricted public" | Access UNVERIFIED |
| SSA Supplement, DI ASR, OACT series, Monthly Snapshot | Aggregate stocks, flows, awards, withholding (6.E) | Public | Section and table indexes verified; several sections already exposed (section 2) |
| NCHS life tables, mortality files and HMD | B4 mortality | Public; HMD needs registration | HMD and NCHS share vital-registration inputs, so they are not independent of each other |
| ACS and CPS marital and earnings tables | B4 state shares; B3 employment margins | Public | Metadata verified |

BEPUF 2020 was the strongest public candidate for J. It is fully
synthetic (section 5), which leaves these gaps.

**Gaps no verified public source closes:**
- the insured, unclaimed person-month risk set (B6a);
- observed annual deductions and withholding (B5-empirical);
- a complete joint holdout for J.

Each of these needs either a restricted linked source or the design's
narrower fallback:
- B6a: a marginal claiming distribution, under `NO_RISK_DENOMINATOR`;
- B5: statutory conformance and sensitivities only;
- J: `JOINT_VALIDATION_FAIL` or a declared narrower scope.

## 2. Exposure

**Prior uses recorded by a4.** Each gate's candidate data has already
been used as follows. None of these can be an unused holdout (design
section 5.2).

- **M6 candidates and floors:**
  - PSID earnings reference years 2016 and 2018, anchored 2014;
  - flows 2015-2019;
  - diagnostics on earnings 2020 and 2022 and flows 2020 and 2021;
  - cohorts 25-44 and 45-64.

  These bear on B3 (its 62-64 band), B3L, B4 and J.
- **The q\* and ρ\* selectors:** pseudo-boundaries 2006, 2008 and 2010,
  scored on reference years b, b + 2 and b + 4 at ages 25-64. These bear
  on B3L and J.
- **B0.1's protocol v2:** fitted at origin 2006 and projected to 2008
  and 2010, ages 25-64, with derived summaries published. This bears on
  B3L's 62-64 band.
- **Marital selectors:** first marriage and remarriage at boundaries 2006,
  2008 and 2010. This bears on B4 and J.
- **M4 disability floors:** PSID waves through 2023, ages 20-66.
- **Mortality floors:** waves 1969-2023, ages 25-85+.
- **The DI-entitlement diagnostic:** validated against the DI ASR 2023.
- **The claiming reference:** fitted 1998-2019, evaluated 2020-2022.
- **EPUF and `gate_epuf_fill`:** earnings 1951-2006, ages 22-74, with DEV
  and TEST scores published.
- **B2:** PSID income years 2012 and 2014, cohorts 25-44 and 45-64; gated
  p90 and zero-earnings rate.
- **The SSA Supplement:** design participants opened 2023 §6.B, 2024 §4.B
  and §6.E, and 2025 §6.E, including numeric tables (design lines
  290-297).
- **SSA tables committed in the repository:** a1 adds those not on the
  design's list:
  - Supplement 6.B for 2014, 2025 and 2026;
  - the 2025 4A, 4B, 5A and 6A snapshots;
  - 2008 4C;
  - DI ASR tables for 2007, 2008 and 2023;
  - 2024 Supplement captures staged under
    `psid-data/legal-capture-staging/`.

The held-out data registry (PR #560,
`docs/design/track_b_holdout_registry.json`) records the scored gates
among these. B0.2's mechanical exposure inventory completes it.

**HRS exposure is UNVERIFIED.** No executed HRS exercise was found, but
issue and PR threads were not searched.

**Accidental exposures during the lanes.** Each lane recorded them. No
value was copied into any output.
- a1 and a2: source files print microdata or codebook counts (for
  example `deaths.py`'s codebook tallies and `epuf.py`'s row counts). The
  lanes read them and copied nothing.
- a3: four web pages showed numbers before the lane stopped reading:
  - the Monthly Statistical Snapshot for September 2026;
  - the DI ASR 2025 highlights;
  - an OACT chart's alternative text;
  - an NSFG methods page.

  A numeric erratum also appeared on the 2024 Supplement contents page,
  and some search snippets showed outcomes.
- a4: a content search with no exclusions (`git grep -il HRS`) read the
  restricted B2 outcome files' bytes. It displayed file names only.
  Masking also failed on several files, showing outcome counts or figures:
  - `docs/amendments/gate_epuf_fill_registration_proposal.md`;
  - `docs/design/di_entitlement.md`;
  - comments in `harness/m6_cells.py`;
  - assertions in `scripts/build_m6_holdout_floors_v4.py`.
- a5: excerpts of the B0.1 audit and addendum showed planning and power
  figures, and `b2.py:229-235` showed inherited outcome text.

These lanes are author-side landscape roles, not blinded reviewers, so
none can serve as J's blinded reviewer. B0.2's exposure record carries
each incident. The exposed web pages (the Snapshot for September 2026
and the DI ASR 2025 highlights) are exposure for any gate that would use
them.

**What the mechanical inventory must add** (a4, section "A B0.2
mechanical inventory"):
- **A candidate registry per gate:** source, reference year, interview
  wave, event period, age, partition, denominator, concept and estimand.
- **Exclusions first:** apply them before any content is read.
- **Pattern families:** B0.1's families, plus families for earnings,
  marital events, disability, mortality, claiming, RET, dates and joint
  states.
- **Classification of each artifact,** separately by evidence content
  and by role. Content is one of names or rules, observed values,
  projected values, derived values, transient computation, or
  unverified. Role is one of training, selection, floor, development,
  diagnostic, regression or holdout.
- **Integers and code in scope:** cover hard-coded counts and code, not
  only decimals.
- **An off-repository register** supplied by outcome-aware holders, for
  issue and PR threads and external directories.

## 3. Requirements per gate

a5 sets out, for each gate, the ten section 5.2 elements and the power
procedure. For each element it gives what the design fixes, what B0.1's
rulings carry over, and the open options with a recommended default.
Its summary table marks almost every element of every gate "open: needs
Max" or "open: needs counts". Only exposure history is "carried over".

Its main recommendations:
- **A common power procedure,** for Max's approval: prospective
  whole-gate equivalence power. The operating characteristic is the
  probability that a faithful candidate passes the entire registered
  conjunction, evaluated over a frozen grid of nuisance assumptions, with
  a conservative dependence treatment and finite-design and estimation
  uncertainty included.
- **Permissible structural counts and forbidden outcome disclosures,**
  per gate. a5's table "What the structural-audit protocol should allow
  and forbid" becomes the protocol's core. Missingness and availability
  flags can reveal outcomes (a "date available" flag can identify an
  event), so the protocol must test that no permitted output reconstructs
  a target truth cell. B0.1's death-disposition counts were structural
  for B2 but would reveal part of B4's mortality surface.
- **J:** six candidate joint estimands (J1-J6):
  - J1, a common-date earnings, claiming and DI table;
  - J2, the earnings-claiming association by DI history;
  - J3, joint transition pathways;
  - J4, recipients and payment within joint states;
  - J5, survivor-path cumulative incidence;
  - J6, post-bereavement payment persistence.

  Each has limit options drawn from the design's styles (2-3 percentage
  points for probabilities, 5-10% for amounts). a5 also states what
  blinded ratification must certify.
- **B2's medians:** ask Max whether to assign a separately named
  cohort-median component to B3, with matching regression cells in B3L,
  or to leave medians unadmitted. The current p50 is a weighted
  positive-earner median. No gate holds ages 25-61 earnings to a fixed
  limit (`b2.py:215-216`).
- **The single §5.3 feasibility review for B3 and B3L:** its inputs and
  procedure are set out (a5, final section). It uses B0.1 audit section
  11.3's figures only through a cleared review process.

**H's start roster** (a1, section 4). No H specification exists. Three
rosters are candidates:
- B2's 2010 head-and-spouse domain, defined in code;
- the full 2011 anchor roster;
- Track A's 2011 closed cohort (`cohorts/psid2010.py`).

Each changes B4's coverage declaration. The choice is a question for Max
or for H's design, and the count runs under B0.2's protocol.

## 4. Pricing of the design's still-unpriced items

These are estimates in engineer-days (d) of reviewed output, or calendar
time, with their basis in the cited lane:

| Item (design §3.3) | Access | Loader and gate work | Source |
|---|---|---|---|
| HRS loader and access, public | About one week of registration; agent use of a person's registration UNVERIFIED | Loader 4-8 d; B0.2 adds 1-2 d to freeze HRS elements per gate | a1 4-7 d, a2 5-8 d |
| HRS linked to SSA records | 2-4 months, about 6 if a sponsor is needed; 1-3 weeks of disclosure review per output | 6-10 d by a person in the enclave | a2 |
| Linked withholding data (B5-empirical) | Public: none, if BEPUF 2020 carries a deduction field (UNVERIFIED). Otherwise HRS-SSA (2-4 months) or an FSRDC (6-12 months, $15,000-20,000 a year) | 1 d documentation check; then 8-12 d to rebuild annual deductions; 4-6 d to freeze and run | a2 |
| I's timing gate: data, loaders, gate | Public HRS and SIPP: about one week; restricted fallback as above | SIPP extension 3-5 d; BEPUF 3-4 d; freezing estimands, limits and power 3-5 d; running the gate 4-6 d. About 10-20 d beyond B0.2's own 5-7 d | a1, a2 |
| Entrant initialization | Public ACS, CPS and EPUF | **Cited from the open-population lane: OP8, 25-39 d; 34-52 d with the demographic packets** (draft, PR #557 at `2acd0bed`, pending its review) | `inputs/entrant-initialization.md` |
| B6b access | Public HRS about one week; restricted 2-4 months; FSRDC 6-12 months | Shared with the HRS rows | a2 |
| 2032 and 2050 horizons | — | Not re-priced here. Design B priced its B8 at 40-70 d, for scale only (design line 203). The open-population lane prices its economic horizon separately (OP10b, OP11b; draft) | design; #557 |

The insured-status rule that B6a, entrant initialization and OP12 need is
on the rules lane under d1802. a1's 2-3 d estimate for it is for scale
only.

## 5. What must be verified before the protocol relies on it

These are facts the lanes could not open. Verify them in a browser,
which works where automated fetches are refused, and open no numeric
table:
1. **BEPUF 2020: settled, 2026-10-23.** SSA's landing page
   (https://www.ssa.gov/policy/docs/microdata/bepuf-2020/index.html, opened
   in a browser; it showed no outcome figures) describes the file as "fully
   synthetic microdata records statistically representing a self-weighted
   10 percent sample of the current adult OASDI beneficiary population as
   of December 2020". It says each record's earnings history and benefit
   credited are related "by statistical modeling rather than by applying
   Social Security program rules", and cautions against using them
   together for individual-level analysis. A synthetic file is not
   observed data, so it cannot serve as an observed holdout for J,
   B5-empirical or I's timing gate, whatever its fields. The user guide
   PDF did not render as text in the browser, and its field list is
   unread; nothing above depends on it.
2. **HRS terms:** whether an agent lane may analyse public files that a
   person registered, and the restricted-data access route, eligibility
   and lead time.
3. **The Disability Analysis File's access route.**
4. **Two staged files that may be restricted** (a1, section 7). Do not
   open them until someone rules:
   - `psid-data/validation-sources/urban-favreault2007-311436.pdf`;
   - the `ssa-mint-*` captures.

## 6. What the protocol can count, and what waits for Max

PSID is the only staged source whose structure B0.2 can count now. So
protocol version 1 covers structural counts on the staged PSID files for:
- B3: support at ages 62-69 by wave, households and design units;
- B3L: the 2006-origin roster and later availability;
- B4: the opening roster, linkage coverage and design fields;
- H's candidate rosters;
- J: PSID-side linkage coverage outside B2's evaluation households.

It applies a5's forbidden-disclosure lists. Gates with no staged source
(I, B5-empirical, B6a, B6b) get a source decision first. Their protocol
sections follow once Max chooses sources and the access questions above
are answered.

Questions for Max, gathered from a2 and a5, go to him through
`cos add-decision` when the records are written. They include:
- the common power procedure;
- each gate's source;
- whether to pursue restricted HRS-SSA or FSRDC access;
- HRS terms for agent work;
- H's roster;
- B2's medians;
- J's estimands and limits;
- the percentage-error conventions.

## 7. A decision needed now: restricted linked data

Design Q4 (line 606, approved in d515) sets the order: evaluate public
HRS and SSA sources first, and request restricted linked data "only if
B0 shows that public sources cannot supply the risk denominator, the
timing observations or the withholding observations".

The landscape shows that condition is met for three of those needs:
- **No verified public source supplies B6a's risk denominator:** an
  insured, unclaimed person-month risk set with entitlement dates.
  Public HRS does not observe insured status (a2, section 2.1).
- **No verified public source supplies observed withholding or annual
  deductions for B5-empirical.** Supplement table 6.E4 is a December
  status diagnostic (design line 224), and BEPUF 2020 is synthetic
  (section 5).
- **No verified public source supplies J's joint holdout,** with
  observed payment and recipient denominators.

Restricted access is slow:
- HRS linked to SSA records: about 2-4 months, through a named
  person's virtual desktop in an enclave, probably with an institutional
  sponsor (UNVERIFIED);
- an FSRDC: 6-12 months and $15,000-20,000 a year per project, with a
  person holding Special Sworn Status working on site (verified on the
  RDC pages).

These lead times would fall on the path to B6a and J, and so to B7.
Neither route can be worked by an agent lane: a person has to do the
analysis inside the enclave or data center.

The options:
1. **Apply for HRS-SSA access now,** in parallel with B0.2. It supplies
   insured status, entitlement dates and administrative earnings. It
   leaves B5's withholding UNVERIFIED (it depends on the benefit file's
   detail).
2. **Apply for an FSRDC project now.** This is the only verified route to
   Master Beneficiary Record payment data. Whether that data carries
   work-deduction fields is UNVERIFIED.
3. **Both.**
4. **Neither, and accept the design's fallbacks:**
   - B5 publishes statutory conformance and sensitivities only;
   - B6a keeps a marginal claiming distribution (`NO_RISK_DENOMINATOR`);
   - J is narrowed to what PSID or public HRS can observe, or stays
     blocked, and B7 is limited accordingly.

Public HRS registration is cheap, takes about a week, and is needed
under every option. Whether an agent lane may work on files a person
registers is UNVERIFIED and should be confirmed with HRS.
