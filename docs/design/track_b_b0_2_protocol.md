# Track B B0.2: structural-audit protocol

**Status: version 1, FROZEN, 2026-10-27. Block SHA-256 `6840f5fa41c897407c5896d4c3729ca5a5c0f1d166faa294e65e42309908ad23`. No count has run.**

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
- **The program limit** is now 300 seconds, up from 60. Round 3's rerun
  of the 800-household calibration withheld on a loaded host when six of
  the nine seed programs found no point within 60 seconds. A limit sets
  no window and sees no size, so it changes only how often a slow
  machine withholds a release.
- **Nonblocking:** `write_new`'s docstring now says that a failure after
  the link leaves the complete file; and tests now kill the two focused
  mutants round 3 found alive (a shifted seed, an omitted directory
  flush).

After round 3, the coordinator ruled that B0.1's sets may constrain the
audit on conditions, which the block now states (Disclosure rule,
"B0.1's sets: the conditions on their use"): a rerun gate, a write
boundary over every output path, a decision record, a stated limit, an
invariant test and no precedent. Meeting them changed the script before
any freeze:
- **The local copy** now holds only this release's counts and the
  audit's final decisions. It had also held each target's proof,
  programs and range, the pool's size, the relation count and the times,
  which depend on atoms that B0.1's sets refine, and the rounds, which
  add resolution to the decisions.
- **Provenance** goes into the committed file, so it holds only the
  requested shape, fixed before any count, and hashes of inputs and
  code.
- **Failures and warnings** print no value. A library's message, which
  can quote a size, is dropped. A warning prints nothing, since whether
  one fires, and where, can depend on the data. The solver prints
  nothing.
- **The rerun gate** checks each rebuilt set against its count before the
  audit, where it had been checked only after registration.
- **Targets.** Two of this release's sets always make a target, and
  their differences come first. Before, a difference of two of this
  release's sets that both coincided with B0.1 sets was skipped, and a
  difference involving a B0.1 set that held the same units could be
  reached first, so which targets were this release's own depended on
  B0.1's sets.

The coordinator then ruled that a stop counts as a decision, a withhold
of the version, and narrowed its report:
- **A stop withholds the version.** The attempt record already refused
  a rerun; the block now says that the stop is a decision, and that the
  next attempt is a new version, ruled on before it runs, that treats the
  stop as public.
- **The report follows the phase.** A failure while reading the inputs
  or writing the files still names its type and the script's line. One
  in the release, where dispositions and atom sizes enter, names the
  phase alone. The script's own raises keep their fixed messages in
  every phase.
- **Nothing printed inside a phase is seen.** File descriptors 1 and 2
  point at the null device inside each phase, and every stream is
  flushed before they are restored, so output from compiled code is
  covered too.
- **The stated limit** now names the run's total time as a channel, and
  says that no time is written or printed.
- **Operations.** The one run is detached from the session that starts
  it, with no wall limit, since the number of programs is bounded. Since
  any stop spends the version, and each program's limit is wall-clock
  time, the coordinator set three conditions in its place, and the
  script enforces the first two before the attempt record:
  - it holds off sleep with `caffeinate` on its own process;
  - it runs at nice 0, and starts only when the five-minute load is below
    the CPU count;
  - an expected run time, extrapolated from the calibrations, goes to the
    coordinator before the freeze.

  The run prints nothing until it ends; its liveness is checked by its
  process ID.

Three tests failed when they first ran, and each was fixed in the
tests alone:
- the property-based relabeling test built its folder behind a symbolic
  link on macOS, which `main()` resolves;
- the exhaustive readers compared a target that is both wide and
  irrelevant by name, though the script may prove either;
- the test that records the solver's options kept the dicts it was
  given, from which SciPy's `milp` removes `disp`; it now keeps copies.

The relabeling test, and its fixed companion, now include panels that
release as well as panels that withhold.

Review round 4 (Opus, at `60d77cff`) approved the block and the script.
It found four test gaps (T1–T4), four script gaps (S1–S4) and three
points for the block (B1–B3), and the coordinator ruled that all eleven
go in before the freeze:
- **Tests (T1–T4):**
  - `main()` runs under an audit hook that refuses any write outside its
    three outputs, and any new process;
  - a property test checks that the local copy is the same whatever the
    rounds;
  - dropping B0.1's household sets now fails a test;
  - the relabeling property draws its swaps from heads of different ages
    and checks that the atoms change.
- **The decision record (S1):** a target the round that ended the audit
  did not reach is `unreached`, whichever round that was, and each class
  names this release's sets that hold it.
- **The run's conditions (S2):**
  - the sleep assertions are held in-process through IOKit, in place of
    `caffeinate`, whose death the script would not have seen;
  - AC power, the Darwin background policy and the QoS class are checked
    with niceness and the load. A measurement after the round added the
    QoS class: under `taskpolicy -c background` a CPU loop ran about a
    twelfth as fast, with niceness and Darwin priority both 0. The class
    must be unspecified, or the default or above;
  - every condition is checked again before every program, and a failure
    is waited out between programs for up to 24 hours before the run
    stops.
- **Separation (S3):** the evidence folder's twelve files are on the
  exclusion record, and the name rule and the exclusions both read full
  paths, which a test with same-basename decoys checks.
- **Identifiers (S4):** a present unit without its person or interview
  number, or its design variables, stops the run while reading.
- **The block (B1–B3):**
  - the status of a withheld release is listed among the audit's limits;
  - condition 4 names the script's own checks as part of the stop
    channel;
  - the operations rule says that running without a wall limit rests on
    the calibrations, not on the bound.

Review round 5 (Sol, at `c6aec979`) stopped before its report, but its
draft found two gaps in round 4's items, both fixed since:
- **The sleep assertions (S2):** the check counted an assertion that
  still existed as held, though IOKit lets its owner set it to the off
  level, where it no longer prevents sleep. It now reads each one's
  level, and one at the off level is given back and taken again.
- **The test confinement (T1):** it let a write into an existing
  bytecode cache folder pass, and did not see a database, the system
  log, a change to a file's metadata, or a socket until it connected or
  sent to an address. It now refuses each, and
  bytecode writing is off while it holds. A write that native code makes
  through its own descriptor raises no audit event, so the static check
  also refuses the modules that could make one.

Two sentences in the block were corrected: the identifier check can fire
on the real files, since the person-wave reader passes the interview
number through as read; and round 4's two status tables are described
separately.

Review round 5's second attempt (Sol, at `9b9d53f5`) found the second
table's description still wrong: the result for 0 to 2 heads is the
reader's rerun on one table's fixed atoms, not the natural tables', and
the block now says so. It also found two mutations no test caught, both
now caught: a properties dictionary the assertion check copies and does
not give back, and a design stratum the identifier check does not
require. The test confinement also refuses name lookups.

The invented-panel calibrations at `e79f41b5` then withheld at 800 and
3,000 households, each on one class of persons of true size 1 that the
audit left 0 to 3, and released with B0.1's sets left out
(`docs/design/track_b_b0_2_evidence/calibration.txt` and
`singleton.txt`). Max ruled on 2026-10-26 that a target is exempt when
this release's counts narrow it no further than B0.1's published counts
already do, and the block was revised before any freeze (Disclosure
rule, "Exempt targets"):
- **The test.** For each narrow target with a proven range, a class or
  a difference alike, two more programs find its least and greatest
  size under B0.1's published counts alone. They are set from the
  publications, like every other program. If they prove the same
  range, the target is exempt: it neither withholds the release nor is
  disclosed. A target holding an atom no B0.1 set counts is never
  exempt, and anything unproven fails closed.
- **Later rounds** test an exempt target again, so a disclosure that
  narrows it further ends its exemption.
- **Tests:**
  - the exhaustive reader with earlier counts also enumerates B0.1's
    counts alone, and the script's exemptions must match it;
  - the exemption programs are the same for every table with the same
    publications, and each fail-closed case has its own test;
  - through `main()`, a panel whose small classes, and a small
    difference, B0.1 already fixes releases, and switching off any one
    of those exemptions withholds on that target alone. That panel had
    been the relabeling test's withholding case, which now uses one this
    release narrows, and the test of a small B0.1 cell now names the
    target that still withholds it.
- **The program bound** grows to 9(T + 2) + 7T(T + 1)/2.

The mutation record and the calibrations run again on the final source.

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
  to constrain the audit, under the conditions the Disclosure rule sets
  out ("B0.1's sets: the conditions on their use"). Nothing derived from
  them beyond B0.1's own counts and the audit's decisions is written or
  printed anywhere;
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
   They are public and exact, so they constrain the audit, and they
   decide which narrow targets are exempt (Disclosure rule). Before any
   of B0.1's sets enters the audit, the script reruns B0.1's
   `structural_counts` (`scripts/track_b_b0_1_counts.py`) on its
   own inputs and stops unless the result equals the committed counts
   exactly and each rebuilt set's size is the count B0.1 published for
   it. Each ledger count B0.1 copied must equal the B0.1 count it
   repeats.

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

Every unit a published set counts must have its identifiers. Each present
row (sequence number 1 to 20 and a positive weight) needs its person and
interview number, and each present person a design stratum and cluster.
Without one, a person would be counted but sit in no household or design
cluster, so an effective size could exceed the count it bounds. A
missing identifier stops the run while reading, before any set is built.
Whether it fires on the real files is not known before the run:
`panels.ind_person_period` builds the person number as an integer, but
passes each wave's interview number through as `pandas.read_fwf` reads
it, and a blank field reads as missing.

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
      subset of it of the same unit type. Two of this release's sets
      always make a target. Any other difference is skipped when B0.1
      published both sets, which fixes it already.

    Examples of differences are a roster's persons in no band, and
    `R_FULL` persons in B2 households who are not in `R_B2`. A target that
    holds the same units as one before it is that target. The differences
    of this release's own sets come before the others, so which targets
    are this release's own (a class, or a difference of two of its sets),
    and their order, depend on this release's sets alone. A target is
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
    (`scipy.optimize.milp`, one HiGHS thread, 300 seconds per program)
    and checks each in exact integer arithmetic before using it.
  - A target is **irrelevant** when it is proven unable to take a size
    from 1 to 9.
  - Any other target is **narrow**, including one whose programs reach
    no answer in time.
  - A narrow target is **exempt** when this release narrows it no further
    than B0.1's published counts already do (Exempt targets, below).
- **No program sees a true size.** Every program, its window and the
  order of targets are set from the publications (this release's and
  B0.1's), the atoms, the relations and the targets disclosed so far:
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
    the window that holds every pool value, decide it. A narrow target
    whose minimum and maximum were found is then tested for exemption.
  - **The truth enters once:** a narrow target of true size 1 to 9 that
    is not exempt withholds the release. If no pool program finds a
    point in time, nothing can be shown wide, and the release is
    withheld.
  - A release with no atom has no target, and runs no program.
- **Exempt targets.** Max ruled on 2026-10-26 to exempt a target only
  when this release's counts narrow it no further than B0.1's published
  counts already do.
  - The exemption covers every audited target: each class and each
    published-set difference (Sets, atoms and targets, above), which
    is what the protection rule protects. The ruling's question names
    a class; it is read here as any audited target, because the test
    that grants the exemption is the same for both kinds.
  - The test runs on every narrow target whose exact minimum and maximum
    were found, whatever its true size. Two more programs find its exact
    minimum and maximum under B0.1's published counts alone: each B0.1
    set's count fixed at its published value, over the same nonnegative
    integer atom sizes, with none of this release's counts, effective
    sizes or relations, and no disclosure.
  - An atom in no B0.1 set is fixed at 0, unless the target holds one;
    a difference holds each atom of its superset outside its subset.
    Then B0.1's counts leave the target's size unbounded, and it is not
    exempt.
  - The target is exempt when both programs prove their optimum and give
    the same least and greatest size as its range under the round's
    constraints. B0.1's counts are among those constraints, so that range
    lies within theirs, and equal ranges mean this release narrows the
    target no further.
  - Anything unproven fails closed. A narrow target without proven
    optima, or one whose two programs prove no optimum in 300 seconds, is
    not exempt.
  - An exempt target neither withholds the release nor is disclosed.
    Every later round tests it again under that round's constraints, so a
    disclosure that narrows it further ends its exemption.
  - These programs are set from the publications alone too, so a reader
    can rerun the test. They add at most two programs per narrow target
    per round.
- **Disclosure rounds.** Since no program sees a true size, each round's
  narrow and exempt targets are the same for every atom-size vector with
  these publications, and a reader who knows this rule can rerun it for
  any of them. A release tells that reader exactly that every narrow
  target that is not exempt lies outside 1 to 9. So each such target,
  whose true size is then 10 or more, becomes **disclosed**: the
  constraints gain that its size is 0 or at least 10, and the pool drops
  any point this rules out. Every target not yet disclosed is then
  classified again, exempt targets included, and so on, until a round
  discloses no new target.
- **What a release guarantees.** The release passes when no sensitive
  target is ever narrow and not exempt. The vectors a reader holding the
  release cannot rule out are then exactly those satisfying every
  constraint and every disclosure. The sizes each sensitive target takes
  among them span at least 4, unless it is exempt: then their least and
  greatest are those B0.1's published counts alone allow. If a sensitive
  target is narrow and not exempt, the audit stops and the counts are
  withheld.
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
  - An exempt target keeps only the protection B0.1's published counts
    left it: this release adds none, and narrows its least and greatest
    size no further. The test compares those two sizes, not which sizes
    between them stay possible.
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
  - The committed status is evidence too, and the guarantee does not
    cover a withheld one. Read with B0.1's exact counts, "withheld" rules
    out every table whose rerun releases.
    - Review round 4 executed this on two 97-head tables. On the first,
      B0.1's record was the same at every split of the 62-64 band from 0
      to 97 heads, and the natural table withheld at only four of them.
    - On the second, B0.1's record was the same for 0 to 7 heads in the
      band. Holding the 3-head table's atoms fixed, and allowing them to
      be empty, the reader's rerun withheld only at 0 to 2. But a search
      over other household, cluster and stratum configurations found a
      table that withheld at each of 3 to 7.
    - So a reader who can rule out no configuration, as this block's
      reader cannot, learns no band from the status. A reader who
      believes some configurations likelier than others could narrow one.
    - The audit does not model that reader.
- **B0.1's sets: the conditions on their use.** The coordinator ruled on
  2026-10-24 that B0.1's sets, its disposition sets among them, may
  constrain the audit on these conditions:
  1. **The rerun gate.** The in-memory rebuild must reproduce B0.1's
     record exactly before the audit uses any of its sets (Inputs, item
     6). A mismatch stops the run before the audit, and nothing is
     written but the attempt record, which holds no count.
  2. **The write boundary.** Every byte the run writes or prints, on
     every path, a failure's included, is one of:
     - provenance that holds no count, within two limits, since it goes
       into the committed file:
       - its shape is only what the run requested, fixed before any
         count: the requested labels, and a geometry of the collection
         waves, the reference years, the age convention and the lags.
         Nothing in it is derived from the panel;
       - its hashes are SHA-256 hashes of inputs and code only: the
         opened PSID files, B0.1's committed counts and the script. There
         is no hash of the local copy, the attempt record or any other
         file that holds a figure not committed, since a hash of a small,
         structured file can be inverted by enumerating the values the
         coarsened counts leave open.

       The rest of the provenance is the schema, the repository head and
       the clean-worktree flag. The attempt record also holds the start
       time, and standard output the published file's path;
     - this release's own counts, exact in the local copy and coarsened
       in the committed file;
     - B0.1's published counts;
     - the audit's decisions: the status, released or withheld, and the
       decision record below;
     - if the run stops, its report, one line under the rule below.

     This covers both files, the attempt record, standard output and
     standard error, exception text, logs and caches. No atom size, no
     count of a set only B0.1 counts beyond B0.1's own, no value by
     disposition and no frequency of death or attrition is written or
     printed on any path. So:
     - the run has three phases: reading and reducing the inputs, the
       release (the rebuild of B0.1's sets, the rerun gate, the counts and
       the audit), and writing the two files. Reading builds no set,
       B0.1's disposition sets included, and no atom, and writing starts
       once both files' bytes are fixed;
     - a stop, including an interruption or a library's own exit,
       prints one line, and no earlier error is chained to it:
       - when the script's own `raise` stopped it, in any phase, the
         error's type, the script's line and the script's message, which
         names only paths and settings: which check fired is a gate
         decision;
       - otherwise, while reading or writing, the error's type and the
         script's line that led to it, and no message;
       - otherwise, in the release, the fixed text "B0.2 stopped in the
         release", with no type, no line and no message;
     - nothing printed inside a phase is seen: file descriptors 1 and 2
       point at the null device and Python's streams at a null stream,
       and every stream, the C library's included, is flushed before the
       descriptors are restored for the report;
     - a warning prints nothing, since whether one fires, and where, can
       depend on the data;
     - the solver prints nothing;
     - nothing but the two outputs and the attempt record writes a file.
  3. **The decision record.** The local copy's audit record holds:
     - the base and the status;
     - for each target of this release (a class of its units, or a
       difference of two of its sets): its kind, unit type and sets, its
       true size and its final classification (`wide`, `narrow`,
       `irrelevant`, `exempt` or `unreached`);
       - a class's sets are the paths of this release's sets that hold it,
         in the release's order, so they depend on this release's sets
         alone; a difference's are its superset and subset;
       - a target's final classification is the one from the round that
         ended the audit, or from the round that disclosed it or proved it
         irrelevant, which no later round changes. A target the ending
         round did not reach is `unreached`, whichever round that was;
     - the sizes of this release's classes, by unit type.

     Nothing about the rounds is written, on any path: not which round
     disclosed or settled a target, not whether the pool was seeded
     again, and not how many rounds ran. Rounds would add resolution to
     the one channel the decisions open, and a rerun of the frozen code
     on the frozen inputs gives them again.
  4. **The stated limit.** The decisions depend on atom sizes, which
     B0.1's sets refine. So which targets are narrow or exempt, whether
     the release is withheld, and whether the run stops inside the release
     can depend on dispositions.
     - So can which of the script's own checks stops it. The stop report
       names that check, by its fixed message and the path or run
       condition the message names. A stop in the release from any other
       cause prints only the fixed text.
     - So can the run's total time. Whoever runs it sees it, and the
       files' modification times and the commit that adds the published
       file show when it ended. No time is written into either file or
       printed.

     Those are the only channels from dispositions to the outputs.
  5. **The invariant.** On invented panels, relabeling deaths and
     move-outs so that B0.1's counts, this release's class sizes and
     every decision are unchanged must leave every byte the run writes
     or prints unchanged (Tests).
  6. **Not a precedent.** This covers B0.1's sets only. Any other earlier
     publication must be listed in this block and meet the same
     conditions before it constrains the audit.
- **The disclosure block.** It records B, the coarsening rule, the
  protection rule and the status, `released` or `withheld`. Nothing else
  about the audit is committed, since every other figure (targets,
  narrow, exempt or disclosed targets, rounds, programs, times) depends on
  true sizes.
- **A withheld release.** The committed file then holds the provenance
  record and the disclosure block, and no counts. The counts stay in the
  local copy. A later attempt is a new protocol version, ruled on before
  it runs, and must treat this version's withheld status as public.
- **Local copy.** A second file, outside the repository, in B0.2's
  evidence folder, holds the provenance record, the unsuppressed counts
  and the decision record (above).

  Targets that involve a set only B0.1 counts are audited but not
  written, and nothing about the rounds is. Nor are the atoms, which
  B0.1's sets refine, or anything computed from them that is not a
  decision: a target's atoms, proof, programs or range, the pool's size,
  the relations or the times. That file is never committed.
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
    script's decision and disclosures must match. Each other verdict must
    hold of the final candidates: a target whose candidates span 4 or
    more and stay out of 1 to 9 is both wide and irrelevant, and the
    script may prove either. The
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
    - a small B0.1 cell that is a B0.2 set withholds, at the band's
      clusters, which B0.1 does not count;
    - programs that depend only on the publications;
    - a local copy that is the same for every split of a B0.2 class by a
      B0.1 set of the same count;
  - **exempt targets:**
    - the exhaustive reader with earlier exact counts also enumerates
      every vector meeting B0.1's counts alone, and the script's
      exemptions, decision and disclosures must match it; among the
      final candidates each sensitive target spans 4 or more or is
      exempt with B0.1's least and greatest sizes;
    - the exemption programs too are the same for two tables with the
      same publications;
    - it fails closed: a range narrower than B0.1's counts alone give, a
      target holding an atom no B0.1 set counts, a narrow target without
      proven optima, and one whose B0.1 programs prove no optimum, are
      not exempt;
    - through `main()`, a panel whose small classes, and a small
      difference of this release's sets, this release narrows no
      further than B0.1's counts do releases, and withholds with the
      exemption switched off; review round 3's attacks, where this
      release narrows a band B0.1 left open, still withhold;
    - on that panel, switching off one exemption alone, of a class or
      of a difference, withholds on that target, in the same round,
      and every target that audit reaches is decided as in the
      release; a difference against a B0.1 set, of true size 10,
      disclosed in place of exempt, ends a class's exemption in the
      next round;
    - an exempt target whose true size is 10 or more is not disclosed,
      and a disclosure that narrows an exempt target further ends its
      exemption;
  - **an emptied pool:** disclosures that empty it reseed it, and an empty
    reseeding withholds while `main()` still writes both files;
  - **the conditions on B0.1's sets:**
    - the rerun gate: a rebuilt set that is not its count stops the record
      check, and stops `main()` before the audit with neither file
      written, naming its path;
    - this release's targets: which are its own, and their order, are the
      same with and without earlier sets that coincide with them or hold
      the same units as their differences;
    - the write boundary: the local copy holds only the decision record,
      the provenance and this release's counts, and nothing about the
      rounds; the committed provenance holds only the listed fields, its
      geometry is the requested shape, and every hash either file holds
      is of an input or of code. Its key set is exact;
    - the stop report: a library's failure in the release, and an
      invented one deep in the rebuild of B0.1's disposition sets that
      quotes a size, print only the fixed text, and a rerun of the version
      is refused; a failure while reading or writing prints its type and
      the script's line only; only the script's own `raise` keeps its
      message, in every phase; an interruption, or a library's own exit,
      prints no chain; a warning prints nothing; and nothing written
      inside a phase, through Python, a file descriptor or the C
      library's buffered stream, is seen, while output after it is;
    - the run's conditions:
      - it refuses to start, before the attempt record and any read, when
        any of the six fails or IOKit is missing;
      - the sleep assertions are held from before the attempt record to
        the end, through every program;
      - through `main()`, every program follows a check that passed;
      - whenever failures clear within the bound, the audit is unchanged,
        each failed check costs one recheck `RECHECK_SECONDS` later, and
        a lapsed assertion, or one at the off level, is given back and
        taken again;
      - on the host that runs it, an assertion set to the off level reads
        as not held;
      - a condition failing through 1,440 rechecks stops the run in the
        release with its name, before any program;
      - with the bound shortened to three rechecks a hundredth of a
        second apart, and real waits, a condition failing through all
        three stops the run, and one that clears at the third lets it
        finish;
      - every QoS class below the default fails `qos`, an unknown one
        included, and unspecified, default and above pass;
      - on the host that runs it, the real reads see the Darwin
        background policy and a QoS clamp;
    - the decision record: each class's sets are this release's sets that
      hold it, by direct membership and in the release's order, and none
      of B0.1's. A target the ending round did not reach is `unreached`
      after a withhold in round 1 or in round 2, and every target is when
      no seed program finds a point;
    - identifiers: a present row without its person or interview number,
      or a present person without a design stratum and cluster, stops the
      run while reading with the script's own message; a row no set
      counts may lack one;
    - a static check of the script, which finds that every `raise`
      message interpolates only paths and settings, that it prints only
      the output's path, that only the outputs, the attempt record and
      the null device are opened for writing, and that `main()` runs the
      three phases with the release alone in the second;
    - the invariant: swapping a death and a move-out on invented panels,
      where the atoms change and the decisions do not, in one panel that
      withholds, one that releases and one that releases with exempt
      targets, and again in property-based examples of both statuses,
      leaves every byte `main()` writes or prints
      unchanged, with the run's directory as its working directory. A
      mutant that writes or prints an atom size must fail these tests.

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
    head, the script's SHA-256 and the start time, and no count.
  - It refuses to start if an attempt record for this protocol version
    already exists, so a failed run cannot be retried silently.
  - A stop once the attempt record exists, for any reason and in any
    phase, is a decision: it withholds this version, since the attempt
    record refuses a rerun of it. The stop and its report are published.
    The next attempt is a new, dated protocol version, ruled on before it
    runs, that treats the stop and its report as public.
  - The run is started in a detached process that survives the end of
    the session that starts it, with standard output and standard error
    sent to a file in B0.2's evidence folder. It prints nothing until it
    ends, since a count of programs solved depends on sizes, so its
    liveness is checked by its process ID alone.
  - Each program has a limit of 300 seconds. The audit runs at most
    9(T + 2) + 7T(T + 1)/2 programs for T targets: nine seed programs at
    the start and at most nine more in each round, at most seven for each
    target in each round (five to classify it and two to test an
    exemption), and at most T + 1 rounds.
    - That bound is finite but says nothing useful about the run's
      length. At about 3,000 targets it allows about 3×10^7 programs,
      centuries at 300 seconds each.
    - So running without a wall limit rests on the calibrations' timings
      (below), not on the bound. None is set: a wall limit could only
      stop a run that would have finished, and a stop spends the version.
  - The limit is wall-clock time, so anything that slows the host can
    add a disclosure or withhold the release. So the script holds the run
    to six conditions, each with a fixed name:
    - `ac_power`: the host draws from AC power, by IOKit's providing
      power source;
    - `sleep_assertions`: the script's own process holds two IOKit sleep
      assertions, against idle sleep and against system sleep, each at
      the on level (its `AssertLevel` property reads 255). They are
      taken before the attempt record and held to the end, and the system
      drops them when the process ends;
    - `nice`: the process runs at nice 0;
    - `background`: the Darwin background policy is off, so
      `getpriority(PRIO_DARWIN_PROCESS, 0)` reads 0;
    - `qos`: the main thread's QoS class is unspecified, or the default
      or above (the script's `QOS_CLASS_UNSPECIFIED` and
      `QOS_CLASS_DEFAULT`). A `taskpolicy -c` clamp to utility,
      background or maintenance, all below the default, fails it;
    - `load`: the five-minute load average is below the host's CPU count
      (18 on the host that runs it).
  - Before the attempt record, the run refuses to start unless all six
    hold, so a refusal spends no version. If the load does not come down,
    Fleet ops is asked for a quiet window, which must last the whole run.
  - Before every program, never during one, the script checks all six
    again.
    - When one fails, no program starts. A sleep assertion that has
      lapsed, or is no longer at the on level, is given back and taken
      again; every other failure is left to clear. The six are
      rechecked every 60 seconds (the script's `RECHECK_SECONDS`), and
      the next program runs once all hold.
    - After 1,440 rechecks in a row (`RECHECKS`), 24 hours, have found
      one failing, the run stops. Its message names the one the last
      recheck found, and the bound. That stop, like any other once the
      attempt record exists, spends the version.
    - A wait changes nothing a program is given, so it cannot change an
      answer. The bound counts waiting, not programs.
  - The operator also keeps the host's lid open and schedules no restart
    for the run's length; the script checks neither.
  - Before the freeze, an expected run time, extrapolated from the
    calibrations' timings on invented panels of 800, 3,000 and 9,000
    households, goes to the coordinator, so that a run measured in weeks
    is caught while the protocol can still change.
- **No changes after counts.** No definition above changes once counts
  are seen. A change is a new protocol version, recorded as such, with
  the reason.
- **Separation.** Before the counts file reaches master, an exclusion
  inventory naming it, in `scripts/track_b_b0_1_review_root.py`'s
  `q6_exclusions` format, is committed, so that successor-design review
  roots can exclude it (B0.2 plan, section 2).
<!-- protocol:end -->
