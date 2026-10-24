# SSI0 source-to-input contract

Contract version: `ssi0-v1`. The machine-readable table is
[`input_contract.json`](../../../src/populace_dynamics/income_resources/ssi/input_contract.json).
It contains one engine row per input in the committed SSI-chain inventory,
with separate decisions for PSID, SIPP and Microcosm. Additional context rows
cover typed links, resource ownership, retirement accounts and timing. Run
`.venv/bin/python scripts/build_ssi_input_contract.py` after regenerating the
inventory to reproduce the table. An input without a reviewed mapping becomes
an explicit refusal.

## What a decision means

`source` identifies a documented candidate and the milestone that will read or
adjudicate it. SSI0 reads no survey microdata. D1 supplies the PSID income and
wealth readers; D2 supplies SIPP readers; WP1 validates starting states and
person or marital-unit ownership. Existing `family_income.py` reads a narrower
2005–2013 family series. Neither its family totals nor other-family-member
totals establish each person's SSI income or resources. A source cell does
not certify a reader, a cross-wave concordance, or the allocation of a family
total to its owners.

`assumption` names a registered assumption that the caller must enable. The
sole engine-input assumption is `POTENTIAL_FULL_TAKEUP`: set
`takes_up_ssi_if_eligible=true` to compute potential benefits. It does not
estimate receipt. PSID's G25F/G26F/G26FPER and generated SSI amounts, and SIPP's
RSSI_YRYN/RSSI_MNYN/TSSI_AMT, remain receipt sources for D1/D2 and SSI4. The
Microcosm frame's calibrated take-up flag is not a projected take-up model;
the design's §3.3 requires SSI4 to replace it.

The context assumption `INTERFACE_NATIONAL_GEOGRAPHY` explicitly selects
`spm.geography_kind="national"` for the auxiliary SPM measurement requested by
the public household calculator. It requires caller opt-in and appears in
the assumption audit. SSI0 admits federal SSI outputs only.

`refuse` names the blocked configuration and a condition. An explicit,
validated input can fill an acquisition gap. It cannot bypass a rules-engine
capability guard or turn an unvalidated household vector into person
ownership. Missing or `None` values refuse with `INPUT_CONTRACT_GAP`,
`RULES_ENGINE_GAP` or `FRAME_LACKS_RESOURCES`; no missing value reaches an
engine default. The runner records one refused outcome per attempted case
and retains that case in its denominator.

## Coverage and boundaries

The inventory includes all three earned sources and fifteen unearned sources
on the pinned release's SSI lists, including self-employment and SSTB
self-employment. The source contract does not merge Social Security survivor
payments with a differently named survivor-benefit input, infer an SSI
disability determination from DI receipt, or infer qualifying quarters from
age. If the reviewed documentation does not establish the requested input or
crosswalk, its cell says `refuse`.

Household, marital-unit and tax-unit links remain distinct. PSID's “wife”
label includes a cohabiting partner (`family_income.py:46–49`); that label
alone does not establish legal marriage. Each person's resource leaves stay
with that person. Microcosm's household-vector carry is blocked pending WP1's
ownership repair and validation; see
[`microcosm#1215`](https://github.com/PolicyEngine/microcosm/issues/1215) and
its captured body in
[`microcosm-1215.json`](../../../data/external/snapshots/ssi0_sources/microcosm-1215.json).

Every retirement account carries its owner, balance, lump-sum access,
periodic-payment eligibility, whether employment must end to obtain payment,
withdrawal penalty, and taxes separately. An empty account list explicitly
states that the person has no retirement account. A balance by itself cannot
choose the branches in POMS SI 01120.210 A.3, B, C.1, E.1 and E.4. The pinned
engine's exclusion of retirement funds remains a `RULES_ENGINE_GAP` for
configurations requiring those branches. SSI2 must settle the treatment of
the 26 U.S.C. 72(t) additional tax before using it as a withdrawal penalty.

The contract records blindness, disability, immigration, qualifying quarters,
living arrangements and in-kind support even when a starting population has
no verified source. Blind and disabled adults remain outside the first
admission; SSI7 supplies their disability link. `Case.timing` declares the
frozen annual state: annual income in equal twelfths and resources fixed at
their annual values. Actual monthly receipt and payment timing wait for SSI9.

## Invariants and checks

- Each inventoried engine input has exactly one row and a decision for each
  starting population; its entity and period match the inventory.
- Missing values refuse unless the caller enables their registered
  assumption. Applied assumption identifiers appear in the result.
- Supplied values survive resolution unchanged; an assumption never replaces
  an explicit zero or false value.
- Booleans require boolean scalars; counts require nonnegative integral
  numbers; numeric inputs must be finite; resources are nonnegative; ages
  lie in the interface range 0–125. Reported income losses remain signed.
  Enum inputs must name a member of the pinned enum. The inventory reads the
  member names from the enum's source, the contract row carries them, and a
  row without them admits no value. So an invalid name refuses its own case
  as `INPUT_CONTRACT_GAP` before any calculation.
- Uncontracted inputs refuse instead of being passed through or silently
  dropped.
- Sources name D1, D2 or WP1 and a citation. Refusals name a condition and the
  configurations they block.
- Context rows preserve all three kinds of links, person ownership and every
  retirement-account fact.

`tests/income_resources/test_ssi_contract.py` checks these invariants with
example tests and Hypothesis over every input and population. Its fixtures
are invented scalars and metadata only; they are never sent to the engine.

## Sources read for this contract

- The approved design's §§2.3–2.4, 3.3, SSI0 row, 8.2, SSI invariants and 10.2.
- The lane's `research/data-sources.md`, §1 (PSID) and §4 (SIPP), in the
  evidence directory named in the assignment.
- `docs/plans/microcosm-start.md:253–302`, including the variable map and the
  warning that sparse and dense frames lack several required fields.
- `src/populace_dynamics/data/family_income.py:1–110,150–263` and its income
  variable names; `src/populace_dynamics/data/sipp_jobs.py:1–80` for reader
  conventions.
- The read-only GitHub API response for microcosm#1215, captured with retrieval
  metadata and a SHA-256 in the SSI0 source manifest.
- `/Users/maxghenis/PolicyEngine/CLAUDE.md:1–60`, for the interface and Axiom
  mirror rules.

PSID use follows the project's data-access record. This contract reads no
microdata and makes no population estimate.
