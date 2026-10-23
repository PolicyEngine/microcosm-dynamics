# Track B B0.2: structural-audit protocol

**Status: version 1, DRAFT, 2026-10-23. Not yet frozen. No count has run.**

Design section 5.2 (line 286) says B0's structural-audit protocol is
frozen before any count or power summary is computed. This file is that
protocol for B0.2. Version 1 covers only what the staged PSID can
answer. It is the first count step the landscape synthesis identifies
(`docs/design/track_b_b0_2_landscape.md`, section 6).

A later version, recorded as such, will cover the other sources (HRS,
SIPP, SSA tables) once Max chooses them.

The counting script `scripts/track_b_b0_2_counts.py` and its tests
arrived in `be7d4f42`. The unit test `tests/test_track_b_b0_2_counts.py`
pins the block's SHA-256, taken over the text from the begin marker
through the end marker. Adding the script did not freeze the protocol.
The freeze is a later commit that changes only the status line above
to FROZEN and states the pinned SHA-256. It follows an independent
review of the block and the script that leaves no blocking finding. The
script then runs once, from a clean worktree at that commit. If the
review changes the block, the pin and the script change with it before
the freeze.

Review round 1 (Sol, at `ec9eb486`) asked for changes, and the block was
revised before any freeze:
- **Ages:** a known-age definition, so a missing age (999) is in no band
  and not in the Track A proxy.
- **Disclosure:** coarsening and an integer-programming audit, which
  replace subtraction-based complementary suppression, after two
  executed recoveries of small cells.
- **One run:** a frozen-status check and an attempt record.

<!-- protocol:begin -->
## Structural-audit protocol, version 1 (frozen before any count)

### Scope

Version 1 counts the structure of the staged PSID for four purposes:

1. **H's candidate start rosters.** B4's coverage declaration cites H's
   roster (B0.1 addendum, "To B0.2").
2. **B3's support at ages 62-69.** These are B3's bands, design line 127.
3. **B3L's 2006-origin roster and its later support.** B3L is the
   2006→2022 backtest, design line 128.
4. **The PSID persons and households outside B2's evaluation units.**
   J needs a holdout independent of B2's evaluation data (design lines
   365-368).

It computes no power quantity. The power procedure waits for Max's
ruling on it.

### What this audit may and may not compute

**It may compute:**
- counts of persons, of households (interview numbers) and of survey
  design strata and clusters;
- counts of valid head and spouse labor-income rows, and of same-person
  valid-row pairs at fixed lags;
- Kish and cluster-worst effective sizes from weights;
- SHA-256 hashes of the files it opens.

**It may not:**
- read or compute any labor-income level, sign, zero or positive
  indicator, quantile or change;
- read any marital, marriage-history, death, disability,
  employment-status, Social Security, wealth or other income variable;
- count dispositions that separate death from attrition, or any
  transition;
- compute any planning value, power probability, model fit, projection,
  floor, gap or candidate outcome.

These rules apply the forbidden-disclosure list in landscape lane a5
("What the structural-audit protocol should allow and forbid") to the
PSID. In particular, for B3 and B3L no earnings sign, positive-pair
count, participation, transition, crossing, quantile, cumulative-earnings
or persistence value is computed. For B4, no marital state, transition,
DI status, death, survival or widowhood frequency is computed. For J, no
joint state, recipient or payment value is computed.

### Inputs

1. **The staged PSID directory,** resolved by the repository's own rule
   (`populace_dynamics.data.psid`).
2. **The cross-year individual file `IND2023ER`,** read through
   `panels.ind_person_period` with exactly the concept labels B0.1's
   counting script uses for age, sequence number, relationship to the
   reference person, individual weight and interview number
   (`scripts/track_b_b0_1_counts.py`, `_individual_variables`). It covers
   collection waves 1999 to 2023, every second year, plus 2007, 2009 and
   2011 where those are not already included.
3. **The 2011 anchor-wave variables,** read through
   `cohorts.psid2010.read_anchor_wave(anchor_wave=2011)`: interview,
   sequence, relationship, reported age and the 2011 cross-sectional
   weight. Its `reported_birth_year` column is dropped as soon as it is
   read.
4. **The survey design variables,** read through
   `cohorts.age67.read_design_variables`: sampling error stratum
   (ER31996) and cluster (ER31997).
5. **The family files for collection waves 1999 to 2023,** read through
   `family.read_family_labor` with its label verification, then reduced
   at once by B0.1's `validity_frame`
   (`scripts/track_b_b0_1_counts.py`), which is imported unchanged.

No other file or variable is opened. The script records the label of
every variable it requests, and a test pins that list as an allowlist.

### Reduction at read time

Each family file's labor-income levels are replaced by one flag per
role, "below the PSID missing sentinel", using B0.1's `validity_frame`.
The accuracy codes are replaced by "positive". No later step sees a
level.

A unit test replaces every valid level with an arbitrary valid level and
requires every output to stay byte-identical. A second unit test adds
arbitrary extra columns of a forbidden kind to the input frames (marital
status, death year, Social Security amount) and requires every output to
stay byte-identical.

### Definitions

- **Collection wave and reference year.** Collection wave *w* collects
  reference year *w* − 1. Ages are collection-wave ages, as in B2
  (`src/populace_dynamics/track_b/b2.py`, `cohort`). The B3 and B3L
  records may choose another age convention; version 1 counts at
  collection-wave age and says so.
- **Valid row.** At wave *w*, a person present (sequence 1-20) who is the
  head or reference person, or the wife, spouse or partner, under that
  wave's relationship codes, with a positive weight at *w*, and whose
  role's labor income is below the sentinel. This is B0.1's
  `earnings_rows` rule, imported unchanged.
- **Known age.** An age is known when it is an integer from 1 to 125,
  the range the repository's readers accept
  (`cohorts.age67._MAX_AGE_CODE`, which treats larger values, such as
  999, as missing). Any other value, including 0 and 999, is an unknown
  age. A person of unknown age is in no age band and in no age-defined
  roster.
- **Age bands,** on known ages only.
  - Older bands: 62-64, 65-66, 67-69 (B3's bands).
  - Context bands: 25-44, 45-61.
  - Roster bands: 1-24, 25-44, 45-61, 62-64, 65-66, 67-69, 70-79, 80 and
    over.
- **Rosters at the 2011 wave** (H's candidates):
  - `R_FULL`: persons present (sequence 1-20) with a positive individual
    weight at 2011. This is B0.1's full anchor.
  - `R_B2`: B2's domain, `R_FULL` persons with a valid 2010-reference row
    (`b2.domain_person_ids`). The script asserts that its size equals
    B0.1's committed count (`docs/design/track_b_b0_1_counts.json`);
    this is a consistency check only.
  - `R_TA_PROXY`: persons present at 2011 with a positive 2011
    cross-sectional weight and a known 2011 age of 30 or over.
    - It is a proxy for Track A's closed cohort (persons born in 1980 or
      earlier, `cohorts/psid2010.py`).
    - Track A's own birth-year law reads marriage histories and earnings,
      so version 1 does not reproduce it. The H record cites Track A's
      own record for the exact cohort.
- **Roster counts.** For each roster, overall, by roster band at 2011,
  and for unknown age at 2011, so that the bands and unknown age
  partition the roster:
  - persons;
  - households (2011 interview numbers);
  - design strata and clusters;
  - Kish effective size;
  - cluster-worst effective size, with households as clusters, and again
    with design clusters as clusters.

  Weights are the roster's own weight: individual weight for `R_FULL`
  and `R_B2`, the cross-sectional weight for `R_TA_PROXY`.
- **B3 support.** For each wave *w* from 1999 to 2023 and each older
  band:
  - valid rows, persons and households;
  - design strata and clusters;
  - Kish and cluster-worst effective sizes, using the wave's individual
    weight;
  - the number of those rows whose accuracy code is positive (a
    data-quality count).

  Across waves: distinct persons per older band.
- **B3 lag pairs.** For lags of 2 and 4 years, and for each pair of waves
  (*w*, *w* + lag) inside 1999-2023, count persons with a valid row at
  both waves, by older band at the later wave. These are structural
  support for transition and persistence estimands; no earnings value
  enters.
- **B3L roster and later support.**
  - `R2006_FULL`: persons present with a positive individual weight at
    the 2007 wave.
  - `D2006`: those `R2006_FULL` persons with a valid row at 2007 (income
    year 2006).
  - Roster counts for both, as above, by roster band at 2007.
  - Then, for each later wave *w* from 2009 to 2023: the number of
    `D2006` persons with a valid row at *w*, by band at collection-wave
    age (context and older bands), and the weighted Kish size of those
    rows using `D2006`'s 2007 weight.
  - No disposition (death, move-out, nonresponse) is counted.
- **Outside B2's evaluation units.**
  - B2's evaluation units are the `R_B2` persons and every 2011 household
    containing one.
  - Count the `R_FULL` persons outside those households, overall and by
    roster band: persons, households, design strata and clusters, and
    Kish and cluster-worst effective sizes.
  - Separately, at waves 2013 and 2015, count the households (wave
    interview numbers) containing at least one `R_B2` person. These
    count households, not outcomes.
- **Effective sizes.** Kish size (Σw)² / Σw². Cluster-worst size
  (Σw)² / Σ_c W_c², where W_c is cluster *c*'s total weight. These are
  B0.1's `kish_n_eff` and `cluster_worst_n_eff`, imported unchanged. A
  set with no positive weight reports 0.

### Disclosure rule

PSID's Conditions of Use, as agreed at the July 2026 download, allow
"aggregate statistical reporting" only. Max's ruling d1899 adds "no
small-cell counts on GitHub". Suppressing small cells, and their
complements by subtraction, is not enough: integer and nonnegativity
bounds, and remainders that are never published, can still pin a small
cell exactly (review round 1 of this protocol). So the committed output
is coarsened, then audited, by these rules.

- **Coarsening at base B.**
  - A count of 0 is written as 0.
  - A count from 1 to B − 1 is written as the string `"<B"`.
  - A count of B or more is written as the nearest multiple of B,
    rounding halves up.
  - Effective sizes are coarsened in the same way, from their own values.
  - Every count type is coarsened alike: persons, rows, pairs,
    households, strata and clusters.
  - B starts at 10.
- **Sets and atoms.**
  - Every published count is the size of one set of units of one type.
    The types are persons; one wave's households; strata; and clusters
    (stratum and cluster together). A row, a pair or an
    accuracy-positive row is counted by its person, since a person has at
    most one row per wave.
  - For each unit type, the atoms are the classes of units that belong
    to exactly the same published sets. Every published count is a sum
    of atom sizes.
  - Sets and atoms stay in memory, and their sizes stay in the local
    copy. Neither is committed.
- **Sensitive quantities.** These are:
  - every atom whose true size is from 1 to 9; and
  - every difference between a published set and a published subset of
    it whose true size is from 1 to 9. Examples are a roster's persons in
    no band, and `R_FULL` persons in B2 households who are not in `R_B2`.
- **The audit.** For each sensitive quantity, the script solves two
  integer programs for the quantity's size: a minimum and a maximum.
  Integer, because an attacker may use integrality; a continuous
  relaxation's range can be wider than the integer one.
  - **Variables:** nonnegative integer atom sizes.
  - **Published counts:** every published value constrains the sum of
    its set's atoms to an interval:
    - exactly 0 for 0;
    - from 1 to B − 1 for `"<B"`;
    - from m − B/2 to m + B/2 − 1 for a published multiple m.
  - **Effective sizes:** each published effective size e also bounds a
    count from below, because an effective size never exceeds the count
    of units, or clusters, it is computed over. A Kish size bounds its
    set's persons. A cluster-worst size bounds its households, or its
    design clusters. The bound is max(0, e − B/2) for a multiple e, and
    1 for `"<B"`.
  - **Protection:** a quantity is protected when its maximum and minimum
    differ by at least 4, so that at least five sizes remain possible. A
    program that does not reach a proven optimum within 60 seconds
    counts as unprotected. The release passes when every sensitive
    quantity is protected.
- **The ladder.**
  - If the audit fails at B = 10, B becomes 50, then 100, then 500. The
    audit reruns each time on the same counts.
  - The first B that passes is used for the whole committed file.
  - If none passes, the committed file holds only the disclosure block,
    and the counts stay in the local copy.
- **The disclosure block.** It records:
  - B and the coarsening rule;
  - the protection rule;
  - for each B tried, how many quantities were audited and how many
    failed.

  It never names a failing quantity.
- **Local copy.** The unsuppressed counts, the atom sizes and the audit
  results are written to a second file, outside the repository, in
  B0.2's evidence folder. That file is never committed.
- **Tests.** Unit tests check coarsening and the audit on invented
  tables. They include each attack review round 1 executed:
  - integer bounds pinning hidden bands;
  - an unpublished remainder;
  - an effective size bounding a count.

  They also include a table that needs the ladder to reach B = 50.

The threshold of 10, the protection width of 4 and the ladder are
version 1's. If Max or the coordinator sets others before the freeze,
this section changes before it freezes; after the freeze, a change is a
new version.

### Output and stop rules

- **The output.** The script writes one exclusive file,
  `docs/design/track_b_b0_2_counts.json`, with schema
  `track_b_b0_2_counts.v1`. It holds the coarsened counts and the
  disclosure block, under the disclosure rule. The unsuppressed copy
  goes outside the repository. The script refuses to overwrite a file,
  or to write under `runs/`. The record carries:
  - the repository head;
  - the script's SHA-256;
  - every opened PSID file's SHA-256;
  - the requested-label allowlist.
- **One run.** It runs once, from a clean worktree at the commit that
  freezes this protocol, with at most four BLAS and OpenMP threads and
  `OMP_WAIT_POLICY=PASSIVE`.
  - It refuses to start unless this file's status line reads FROZEN and
    the block's SHA-256 equals the pin in its tests.
  - Before it opens any PSID file, it creates an attempt record,
    exclusively, beside the local copy. The record holds the repository
    head, the script's SHA-256 and the start time.
  - It refuses to start if an attempt record for this protocol version
    already exists, so a failed run cannot be retried silently.
  - If it fails, the failure is published, and the protocol is revised in
    a new, dated version before any rerun.
- **No changes after counts.** No definition above changes once counts
  are seen. A change is a new protocol version, recorded as such, with
  the reason.
- **Separation.** Before the counts file reaches master, an exclusion
  inventory naming it, in `scripts/track_b_b0_1_review_root.py`'s
  `q6_exclusions` format, is committed, so that successor-design review
  roots can exclude it (B0.2 plan, section 2).
<!-- protocol:end -->
