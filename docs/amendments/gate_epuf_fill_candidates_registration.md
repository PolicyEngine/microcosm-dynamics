# gate_epuf_fill: registered candidates

- **Registration id**: `2026-10-03-epuf-career-fill`
- **Gate**: `gate_epuf_fill`
  (`docs/amendments/gate_epuf_fill_registration_proposal.md`). A gate here is
  a pass-or-fail test whose rules and thresholds are fixed and published
  before anything is scored against it.
- **Stage**: candidates registered before any TEST read. TEST is scored once,
  by `scripts/score_epuf_fill_test.py`, after `gates.yaml` locks the gate on
  Max's ratification (decision d927).
- **Code**: `src/populace_dynamics/estimates/epuf_fill.py` at the manifest's
  `code_commit`.
- **Fitted artifacts**: `runs/epuf_fill_candidates_v1.json` records each
  file's SHA-256, size, parameters and diagnostics, and the library versions.
  - The files are fitted on EPUF TRAIN only, by `scripts/fit_epuf_fills.py`.
  - They are byte-reproducible `.npz` files, staged outside the repository
    as EPUF is (`~/PolicyEngine/epuf-data/fills`).
  - `epuf_fill_scoring.score_registered` loads each one through `load_fill`
    and refuses other bytes.

## The registered artifacts

- **Manifest**: `runs/epuf_fill_candidates_v1.json`, SHA-256 `a304311343f3c78f7702ec6918b991b6bea30dad2a23529df6f0f975ce7f62d0`.
- **Fitted at**: `598e4436` on TRAIN, with the code files clean.
- **Environment**: numpy 2.5.1, scipy 1.18.0, scikit-learn 1.9.0, Python 3.14.4, zlib 1.2.12, on macOS-26.6.2-arm64-arm-64bit-Mach-O.
- **Reproducibility**:
  - A second fit at the same commit reproduced all four files byte for
    byte.
  - The refit after code review (below) did too.
  - Reproducing the bytes needs the same library, zlib and platform
    versions. The deflate output can depend on the zlib build.

| Name | Role | File | SHA-256 | Bytes |
|---|---|---|---|---:|
| `odd_forest` | odd primary | `odd_forest_v1.npz` | `37a9ea76c9cac3692efb4e6b29b184a1a480f4b3caa8b15462133f5af659ebfa` | 44,836,853 |
| `odd_knn` | odd alternative | `odd_knn_v1.npz` | `8c7d323ded317dc336189feb7c0779cef149ce15a67dc7467008a7fad7175291` | 4,076,580 |
| `pre_donor` | pre primary | `pre_donor_v1.npz` | `3c31fbd3e93484470210d451eaca62c8fb99cf13d051fba7e648f931bd3218f7` | 31,768,107 |
| `pre_chain` | pre alternative | `pre_chain_v1.npz` | `8bb48b022d9d0d27cb9f6d0517384c3b7839f636469106b30253d9b495b13724` | 236,450 |

## The four candidates

| Family | Role | Name | What it is |
|---|---|---|---|
| odd | primary | `odd_forest` | Two-part random-forest draw, fitted per sex |
| odd | alternative | `odd_knn` | kNN triples |
| pre | primary | `pre_donor` | Rank-kNN donor careers |
| pre | alternative | `pre_chain` | Chained one-sided draw |

**`odd_forest`** (odd primary) is fitted per sex.
- **Part one**: a probability forest gives the chance of a zero year.
- **Part two**: a quantile regression forest gives the positive share. Its
  leaves keep the true TRAIN shares, so its draws are true values.
- **Features**: the recorded shares at `t-1`, `t+1`, `t-3` and `t+3`; their
  mean, geometric mean and count positive; the mean positive share and the
  share of positive years at offsets 5-9; sex; age; and the year.
- **Training units**: TRAIN units inside the career, with contexts that see
  the career only. `n_units`, 3,000,000, applies to each sex's forest.
- **Copula**: a person-level Gaussian copula with correlation by sex and
  age band. It is calibrated on one TRAIN person in ten, held out of the
  forests, to match two- and four-year persistence between masked years.

**`odd_knn`** (odd alternative) draws the share at `t` from one of the 10
nearest TRAIN career units in the shares at `t-1` and `t+1`, by sex and
five-year age band.

**`pre_donor`** (pre primary) copies a whole masked block from one of the 3
nearest TRAIN donors of the same sex and birth year.
- **Bank**: every TRAIN donor in the `pre` universe, up to 100,000 per sex
  and birth year.
- **Distance**: percentile ranks over the first five recorded career years,
  plus the career's mean share and share of positive years.

**`pre_chain`** (pre alternative) draws year `y` from the next known later
year's share, sex and age, backward from the career start. Ages 15-24 are
single years.

Each candidate's exact fit parameters are in the manifest and in
`scripts/fit_epuf_fills.py` (`REGISTERED`).

## DEV development, disclosed

Candidates were developed against DEV, as the registration allows. Every DEV
score is disclosed:
- `docs/amendments/gate_epuf_fill_dev_scores_before_amendment_1.json`;
- `docs/amendments/gate_epuf_fill_dev_scores_after_amendment_1.json`;
- `docs/amendments/gate_epuf_fill_dev_scores_after_round_2.jsonl`, which
  logs every later score through the registered scoring path.

The candidate code behind each later score is kept in
`docs/amendments/gate_epuf_fill_candidate_code/`.

The last DEV scores of the four registered designs, against the v3
tolerances, are below. They are scored on the registered artifacts with 20
draw seeds; see the dry run below.

| Candidate | Gating cells failed on DEV | Tier on DEV (fallback current rule) |
|---|---:|---|
| `odd_forest` | 7 of 183 (worst: `odd.men.a22_29.r1`, 2.69 tolerances) | improves |
| `odd_knn` | 46 of 183 (worst: `wint`, up to 10 tolerances) | not adopted |
| `pre_donor` | 0 of 136 (worst: 0.77 tolerances) | certified |
| `pre_chain` | 50 of 136 (worst: youth `ylevel`, 20 tolerances) | not adopted |

**The registered procedure, dry-run on DEV.** On 2026-10-04,
`epuf_fill_scoring.score_registered` ran with the DEV matrix in place of
TEST, the registered artifacts loaded by SHA-256, and all 20 draw seeds. It
is logged in `docs/amendments/gate_epuf_fill_dev_scores_after_round_2.jsonl`.

| Family | Current rule failing | Primary | Alternative | Adopted |
|---|---|---|---|---|
| odd | 100 (fallback reading), 99 (two-sided) | improves, 7 of 183 failing | not adopted, 46 failing | primary, uncertified |
| pre | 131 | certified, 0 of 136 failing | not adopted, 50 failing | primary |

The odd primary's seven failing cells on DEV:

| Cell | Tolerances |
|---|---:|
| `odd.men.a22_29.r1` | 2.69 |
| `odd.women.a22_29.r1` | 2.02 |
| `odd.women.a22_29.zint` | 1.58 |
| `odd.men.a22_29.zint` | 1.37 |
| `odd.women.a22_74.zint` | 1.23 |
| `odd.women.a60_74.r1` | 1.17 |
| `odd.women.a22_74.r1` | 1.09 |

**What DEV predicts, stated before TEST.** DEV and TEST are disjoint random
fifths of EPUF of nearly equal size, so their scores should agree closely.
- The pre-career primary should certify.
- The odd primary should be adopted as an uncertified improvement, unless
  its young-band cells move.
- Most of the odd primary's residual misses are at ages 22-29, where the year
  before the career is hidden from every fill. The oracle O1 misses there
  too.

## Code review and refit

An independent code review of PR #516 returned REQUEST CHANGES
(`reviews/gate_epuf_fill_pr516_code_review_20261004.md`). The fixes:

**`fill_careers` (PSID-2010).**
- It fills only the gap years the gate scored (1997-2005) unless the
  caller opts into every gap year, which is an uncertified extrapolation.
- A gap year with no neighbour the fill can see keeps the assembler's
  value.

**`epuf_fill.py`.**
- The donor cache is keyed by the bank's content.
- Persons of uncoded sex take the routed part's copula.
- A forest leaf can never be empty: none is, and the smallest holds 16
  values.
- The career summaries in the donor match stop at 2006.

**The scripts.**
- The fit script refuses an existing manifest before fitting and never
  replaces a staged file with other bytes.
- The score script pins this manifest's SHA-256, records whether its code
  was clean, and publishes no local paths.

**The manifest.** The first manifest (SHA-256 `8d42153...`) was withdrawn
and refitted at the reviewed code (`598e4436`). The four artifacts'
SHA-256 values are unchanged.

**The DEV dry run still stands.** It scored the same artifacts, and none of
the fixes changes a draw for a person the gate scores. They touch the PSID
application, which EPUF scoring does not use; the cache's key; the draws
for persons of uncoded sex, who are never scored; and the bank summaries'
years, which on EPUF end in 2006 anyway.

## Procedure on TEST (after lock)

1. Confirm that `gates.yaml` locks `gate_epuf_fill` and that the staged files
   match the manifest's SHA-256.
2. Run `scripts/score_epuf_fill_test.py --manifest
   runs/epuf_fill_candidates_v1.json --output runs/epuf_fill_gate_test_v1.json`
   once.
3. Publish the result whether it passes or fails. Record each family's tier
   and adoption under the registered rule.
4. Record the adoption in this document. A family whose primary and
   alternative both fail to be adopted keeps the current rule.
