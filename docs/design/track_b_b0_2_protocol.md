# Track B B0.2: structural-audit protocol

**Status: version 1, DRAFT, 2026-10-24. Not yet frozen. No count has run.**

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

Review round 2 (Sol, at `0644b717`) asked for changes again, and the
block was revised before any freeze:
- **Audit metadata:** the committed file had reported how many targets
  were audited, which an executed fixture used to narrow a remainder to
  four sizes. The disclosure block now holds only the base, the rules
  and the status. No program the audit runs depends on a true size, so
  a reader can rerun it, and every target it finds narrow is treated as
  disclosed.
- **Intervals:** a published multiple stands for max(B, m − B/2) to
  m + B/2 − 1, matching the coarsening rule.
- **Writes:** both files are written to temporary names, flushed and
  linked into place, so a failure leaves no partial file.
- **Nonblocking findings, also answered:** relations across unit types
  are part of the audit's model; a single fixed base replaces the
  ladder; a target is wide on two verified points, without a proven
  optimum; and tests now cover a fractional age of 62.5, negative
  inputs to coarsening, the solver's exact-optimum setting and the
  attempt record's flush.

Before round 3, three sentences of the block were corrected. They had
said a wide target keeps at least five possible sizes; the rule, and the
tests, guarantee a range of width at least 4. The evidence for the
revision (an enumeration oracle, searches, an invented-panel calibration
and the mutation runner) is in `docs/design/track_b_b0_2_evidence/`.

Review round 3 (Sol, at `2d0ed992`) asked for changes, and the block was
revised before any freeze:
- **B0.1's counts:** B0.1 had already published exact counts of the same
  persons, which the audit did not model. Two executed tables used them:
  - with 97 invented B2 heads, B0.1's exact count of those aged 45-64,
    against this release's 45-61 band published as 100 (95 to 104), left
    the 62-64 band one or two;
  - a five-head table, both bands under 10, left the 62-64 band one to
    four.

  B0.1's sets are now rebuilt in memory by its own rules and enter the
  audit at their exact counts, after a rerun of B0.1's script on the same
  inputs must reproduce its record. This required an exception to the
  rule against counting dispositions: B0.1's disposition sets are among
  them. Nothing derived from them beyond B0.1's own counts is written.
- **An emptied pool:** disclosures could rule out every pool point,
  leaving nothing to classify against. An empty pool now makes its
  target narrow, the seed programs run again under the disclosures, and
  the release is withheld if they find nothing.

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
  transition. The one exception is B0.1's published sets, its disposition
  sets among them. They are rebuilt in memory, by B0.1's own rules, only
  to constrain the audit (Disclosure rule). Nothing derived from them
  beyond B0.1's own counts is written to either file;
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

6. **B0.1's committed counts,** `docs/design/track_b_b0_1_counts.json`.
   They are public and exact, so they constrain the audit (Disclosure
   rule). The script reruns B0.1's `structural_counts`
   (`scripts/track_b_b0_1_counts.py`) on its own inputs and stops unless
   the result equals the committed counts exactly. Each ledger count B0.1
   copied must equal the B0.1 count it repeats.

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
    B0.1's committed count (`docs/design/track_b_b0_1_counts.json`).
    B0.1's counts also constrain the audit (Inputs, item 6).
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

PSID outputs are aggregate statistics only, and no small cell is
committed, per the project's data-access record. Suppressing small
cells, and their complements by subtraction, is not enough: integer and
nonnegativity bounds, and remainders that are never published, can still
pin a small cell exactly (review round 1 of this protocol). Auditing the
published values alone is not enough either: anything else the committed
file says about the audit, including whether it passed, is evidence a
reader can use (review round 2). So the committed output is coarsened at
one fixed base, then audited against everything it discloses, by these
rules.

- **Coarsening at base B = 10.**
  - A count of 0 is written as 0.
  - A count from 1 to B − 1 is written as the string `"<B"`.
  - A count of B or more is written as the nearest multiple of B,
    rounding halves up. So a published multiple m stands for every
    integer from max(B, m − B/2) to m + B/2 − 1; a published B stands
    for B to 3B/2 − 1.
  - Effective sizes are coarsened in the same way, from their own values.
  - Every count type is coarsened alike: persons, rows, pairs,
    households, strata and clusters.
  - B is fixed. There is no ladder of bases: publishing at a larger base
    after a smaller one failed would disclose that it failed.
- **Sets, atoms and targets.**
  - Every published count is the size of one set of units of one type.
    The types are persons; one wave's households; strata; and clusters
    (stratum and cluster together). A row, a pair or an
    accuracy-positive row is counted by its person, since a person has at
    most one row per wave.
  - For each unit type, the atoms are the classes of units that belong
    to exactly the same published sets. Every published count is a sum
    of atom sizes.
  - B0.1's published counts are sets too, each counted exactly (below).
    They refine the atoms.
  - The targets are this release's, whatever their true sizes:
    - each class of units that belong to exactly the same sets of this
      release (a union of atoms);
    - every difference between a published set and a published proper
      subset of it of the same unit type, unless B0.1 published both,
      which fixes the difference already.

    Examples of differences are a roster's persons in no band, and
    `R_FULL` persons in B2 households who are not in `R_B2`. A target is
    sensitive when its true size is from 1 to 9.
  - Sets and atoms stay in memory. Neither is committed, and the local
    copy holds only what its item below names.
- **What a reader can use.** The audit works over nonnegative integer
  atom sizes, subject to:
  - **published counts:** each published value confines its set's count
    to exactly the integers that coarsen to it: 0 for 0; 1 to B − 1 for
    `"<B"`; max(B, m − B/2) to m + B/2 − 1 for a multiple m;
  - **B0.1's counts:** each count B0.1 publishes is the size of a set,
    which the script rebuilds by B0.1's rules from the same inputs, and
    that set's count is fixed at its published value.
    - B0.1's other counts must follow from these, and the script checks
      that they do: its sums (a total of scored rows, a pooled level
      cell's rows, a change-pair count of rows), its effective sizes and
      its wave labels.
    - The M6 fit's input-row count, which B0.1 copied from the ledgers,
      is not modeled: it counts every reference year to 2010, which no set
      here counts;
  - **effective sizes:** an effective size never exceeds the count of
    units, or clusters, it is computed over, and a positive one needs at
    least one. So a published effective size e bounds a count from
    below: by 0 for 0, by 1 for `"<B"`, and by max(B, e − B/2) for a
    multiple e. A Kish size bounds its set's persons. A cluster-worst
    size bounds its households, or its design clusters;
  - **relations between unit types,** for each set counted in all four
    types: its households, and its design clusters, number at most its
    persons; its design strata number at most its design clusters; and
    it has no persons unless it has households, design clusters and
    design strata. A relation is registered for a set only where the
    rows that build the set guarantee it, whatever the counts:
    - households at most persons, when no person has two rows and every
      row with an interview number has a person;
    - design clusters at most persons, when no person has two rows and
      every row has a person;
    - persons only with households, when every person's row has an
      interview number; and persons only with design strata, when every
      person's row has a stratum;
    - strata at most clusters, and persons only with clusters, always,
      since each stratum comes with a cluster of its own and every row
      yields a cluster.

    So the relations are structure, fixed before any size is used. A
    registered relation that the true sets violate is a defect, and the
    script stops;
  - **the release's own disclosures,** below.
- **The audit.**
  - A target is **wide** when two integer atom-size vectors, each
    satisfying every constraint exactly, give it sizes at least 4 apart,
    so that no range of fewer than five sizes holds every size it can
    take. The script finds such vectors with integer programs
    (`scipy.optimize.milp`, one HiGHS thread, 60 seconds per program)
    and checks each in exact integer arithmetic before using it.
  - A target is **irrelevant** when it is proven unable to take a size
    from 1 to 9.
  - Any other target is **narrow**, including one whose programs reach
    no answer in time.
- **No program sees a true size.** Every program, its window and the
  order of targets are set from the publication, the atoms, the
  relations and the targets disclosed so far:
  - **A pool of points.** The script first solves one program for any
    feasible vector, and eight more pushed along fixed directions of
    ±1 per atom, drawn from a seeded generator (seed 20261024). Each
    accepts the first integer point found. Every verified point is kept,
    and so is every point a later search finds.
  - **An empty pool** sets no window, so a target classified with it is
    narrow. When a round's disclosures rule out every pool point, the
    nine seed programs run again under them; if none finds a point,
    nothing can be shown wide, and the release is withheld.
  - **Per target, in the registry's fixed order:** wide at once if the
    pool's points give it sizes 4 apart. Otherwise, if the pool's least
    value is 10 or more, a continuous relaxation whose minimum exceeds
    9.5 proves it irrelevant. Otherwise the script searches for a point
    at least 4 above the pool's least value, and one at least 4 below
    its greatest. A point found makes it wide. If both searches are
    proven infeasible, the target's exact minimum and maximum, within
    the window that holds every pool value, decide it.
  - **The truth enters once:** a narrow target of true size 1 to 9
    withholds the release. If no pool program finds a point in time,
    nothing can be shown wide, and the release is withheld.
  - A release with no atom has no target, and runs no program.
- **Disclosure rounds.** Since no program sees a true size, each round's
  narrow targets are the same for every atom-size vector with this
  publication, and a reader who knows this rule can rerun it for any of
  them. A release tells that reader exactly that every narrow target
  lies outside 1 to 9. So each narrow target of true size 10 or more
  becomes **disclosed**: the constraints gain that its size is 0 or at
  least 10, and the pool drops any point this rules out. Every target
  not yet disclosed is then classified again, and so on, until a round
  discloses no new target.
- **What a release guarantees.** The release passes when no sensitive
  target is ever narrow. The vectors a reader holding the release cannot
  rule out are then exactly those satisfying every constraint and every
  disclosure, and the sizes each sensitive target takes among them span
  at least 4. If a sensitive target is narrow, the audit stops and the
  counts are withheld.
- **What the audit assumes, and its limits.**
  - The reader is assumed to know the atoms, how they nest and the
    registered relations, which is more than the committed file shows,
    but not the atoms' sizes: any atom may be empty.
  - The atoms are the classes of units that occur in the data. A reader
    who could list every class that might occur, and rerun the audit
    for each choice of which ones are empty, could learn which classes
    occur, and so that each of those holds at least one unit. The audit
    does not model that channel. Assuming instead that every atom is
    nonempty pins atoms exactly in ordinary tables (a `"<10"` set of
    nine atoms forces each to 1), so no realistic release would pass.
  - The protected targets are atoms and single-subset differences. Other
    unions of atoms, such as a set minus the union of several of its
    subsets, are not targets: no release can protect every union of
    atoms. The natural complements in this release, such as the
    unknown-age cells, are published sets.
  - Relations across unit types are those listed. Others a reader might
    know, such as how many clusters each stratum has, are not modeled.
  - The one earlier release modeled is B0.1's counts. Under B0.1 §15.4
    this audit may not open the other committed files that count the same
    persons, so their counts enter only through the copies B0.1 made of
    them, its ledger-support fields. Any other committed count over these
    persons is not modeled. The exposure inventory names the committed
    runs. A count found later to constrain these sets needs a new
    protocol version.
  - An unanswered program counts against release, so machine speed can
    withhold a release or add a disclosure, but never weaken one. Time
    limits are the one input to a program's answer that the publication
    does not fix; the guarantee above treats a timed-out program as
    giving the same answer on every rerun.
- **The disclosure block.** It records B, the coarsening rule, the
  protection rule and the status, `released` or `withheld`. Nothing else
  about the audit is committed, since every other figure (targets,
  narrow or disclosed targets, rounds, programs, times) depends on true
  sizes.
- **A withheld release.** The committed file then holds the provenance
  record and the disclosure block, and no counts. The counts stay in the
  local copy. A later attempt is a new protocol version, ruled on before
  it runs, and must treat this version's withheld status as public.
- **Local copy.** A second file, outside the repository, in B0.2's
  evidence folder, holds:
  - the unsuppressed counts;
  - the sizes of this release's classes;
  - the audit's targets that involve only this release's sets, with their
    classifications;
  - the rounds and the times.

  Targets that involve a set only B0.1 counts are audited but not
  written, nor are their places in the rounds or any target's atoms:
  B0.1's sets refine the atoms, and their nesting and sizes would add to
  what B0.1 published. The number of rounds is written. That file is
  never committed.
- **Tests.** Unit tests check coarsening and the audit on invented
  tables. They include each attack reviews of this protocol executed:
  - integer bounds pinning hidden bands;
  - an unpublished remainder;
  - an effective size bounding a count;
  - public audit counts narrowing a remainder (round 2): the committed
    file must be byte-identical across every remainder the audit
    protects.

  They also check:
  - **against an exhaustive reader,** on small random tables and on
    tables that withhold: every atom-size vector with the same
    publication is enumerated, the rule is rerun on each, and the
    script's decision, disclosures and classifications must match. The
    vectors whose rerun releases must be exactly the final constraint
    set, and the sizes each sensitive target of a released table takes
    among them must span at least 4;
  - **that no program sees a true size:** two tables with the same
    publication and atoms hand the solver the same programs in the same
    order, up to the point where one withholds;
  - **that relations are structure:** each is registered only when its
    rows guarantee it, and a violated one stops the script;
  - **the output writes:** an interrupted or failed write leaves no
    partial file under a final name;
  - **B0.1's sets:**
    - each rebuilt set's size is the count B0.1's own script publishes,
      checked on invented frames and on a hand-counted example;
    - the record check stops on a count these inputs do not give, a count
      nothing models, a failed sum, a changed ledger copy, and a modeled
      set B0.1 never published;
  - **B0.1's counts in the audit:**
    - the exhaustive reader with earlier exact counts;
    - review round 3's executed attacks (97 and 5 heads), which now
      withhold through `main()` with identical committed files;
    - a small B0.1 cell that is a B0.2 set withholds;
    - programs that depend only on the publications;
    - a local copy that is the same for every split of a B0.2 class by a
      B0.1 set of the same count;
  - **an emptied pool:** disclosures that empty it reseed it, and an empty
    reseeding withholds while `main()` still writes both files.

The threshold of 10, the protection width of 4 and the base of 10 are
version 1's. If Max or the coordinator sets others before the freeze,
this section changes before it freezes; after the freeze, a change is a
new version.

### Output and stop rules

- **The output.** The script writes one exclusive file,
  `docs/design/track_b_b0_2_counts.json`, with schema
  `track_b_b0_2_counts.v1`. It holds the coarsened counts and the
  disclosure block, under the disclosure rule. The unsuppressed copy
  goes outside the repository. The script refuses to overwrite a file,
  or to write under `runs/`.
  - Both files are serialized in full, then each is written to a
    temporary file in its own directory, flushed to disk, and given its
    final name by a hard link that fails if the name exists. A failure
    leaves no partial file under a final name. The local copy is written
    first.
  - The record carries the repository head, the script's SHA-256, every
    opened PSID file's SHA-256 and the requested-label allowlist.
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
