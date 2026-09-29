# Erratum: provenance of two replication anchors

Date: 2026-09-29. Issue: [PolicyEngine/microcosm-dynamics#488](https://github.com/PolicyEngine/microcosm-dynamics/issues/488).

Two external anchors in the replication scripts carried the wrong model label. This erratum corrects the labels in the scripts and the paper. Committed evidence artifacts under `runs/` are never edited in place, so they keep the old labels. Where a committed artifact and this erratum disagree about provenance, this erratum governs.

No anchor value, model output, test result, forecast grade or pass/fail status changes. Tests T1 to T3 of the cost-ordering synthesis keep their committed results and statuses (see "What does not change" below).

## What was mislabelled

| Anchor | Old label | Correct provenance |
|---|---|---|
| Mermin (2005), Urban Institute report 411260, Table 1, "75-year deficit/surplus (percentage of taxable payroll)" row | "DYNASIM3 Runid 432" | Congressional Budget Office (2005) estimates, as reported in Mermin (2005). The benefit rows of the same table are DYNASIM3 (Runid: 432) output; the deficit row is not. |
| Smith, Johnson and Favreault (2020), *Five Democratic Approaches to Social Security Reform*, Urban Institute report 103050, Tables 3 and 15 | "DYNASIM3 ID980" | DYNASIM4 ID980. Table 3's source line reads "Source: DYNASIM4 ID980."; Table 15's reads "Source: DYNASIM ID980."; the report says its analysis "is based on DYNASIM4". |

### 1. Mermin (2005) Table 1: the 75-year deficit row is CBO 2005

The Mermin deficit row is the anchor for test T2 of the cost-ordering synthesis (`scripts/replication_cost_ordering.py`, `MERMIN_ANCHOR_CITE`) and for the four Mermin-quartet checks of T1. T2 is therefore a comparison against the Congressional Budget Office's 2005 estimates, not against DYNASIM3. It was registered in advance (issue #42 comment 4931034068, posted 2026-07-10 01:09 UTC; the artifact was committed at 02:03 UTC), but it was not blind: the five figures T2 uses (the scheduled deficit and the four reform balances) were published in 2005 and were already transcribed in committed artifacts, `runs/replication_ppi_mermin_v1.json` (2026-07-07) and `runs/replication_mermin_rows_v1.json` (2026-07-08). The registration itself names the anchor as "Mermin's 75-year payroll effects" and carries no model label.

Mermin's text, `411260-benefit-reductions.txt` lines 212–214:

```text
The last row of table 1 presents Congressional Budget Office (CBO) estimates of the
Social Security trust funds’ cumulative deficit over the next 75 years as a percentage of
taxable payroll. 13 Under scheduled benefits payroll taxes would need to be immediately
```

Footnote 13, `411260-benefit-reductions.txt` lines 231–233:

```text
13
   The analysis uses CBO as opposed to SSA estimates of solvency because CBO scored all of these policy
options under the same set of assumptions.
```

The row and the table's source line, `411260-benefit-reductions.txt` lines 514–521 (Table 1 is on PDF page 15):

```text

 75-year
deficit/surplus
(percentage of
taxable payroll)         -1.69                0               +0.68              -0.14              -1.12           -0.5


Source : Author's calculations from DYNASIM3 (Runid: 432) and the Congressional Budget Office (2005).
```

The source line credits two sources, and the text assigns them. The report's projections "are based on the Urban Institute’s DYNASIM3 model" (line 127), and the last row of Table 1 is CBO's (lines 212–214). So the benefit rows are DYNASIM3 (Runid: 432) output and the deficit row is CBO's. `runs/replication_ppi_mermin_v1.json` already labels the row correctly (`/anchor_provenance/table1_75yr_payroll_effect_pct/citation`: "percent of taxable payroll, CBO 2005 scoring").

### 2. Five Approaches Tables 3 and 15: DYNASIM4, not DYNASIM3

The Table 3 "Provide caregiver credits" row is the anchor for test T3 of the cost-ordering synthesis (`CAREGIVER_ANCHOR_CITE`). The Table 15 "Create caregiver credit" row is the anchor of the caregiver replication (`scripts/replication_caregiver.py`).

Table 3's source line, `103050-five-dem.txt` line 1052:

```text
Source: DYNASIM4 ID980.
```

Table 15's source line, `103050-five-dem.txt` line 3299:

```text
Source: DYNASIM ID980.
```

The report's statement of its model, `103050-five-dem.txt` line 906:

```text
Our analysis of the candidates’ Social Security reform proposals is based on DYNASIM4. The model
```

Two bibliographic details in the caregiver script's `paper` field were also wrong and are corrected here. The report's subtitle, `103050-five-dem.txt` lines 11–13:

```text
Five Democratic Approaches to
Social Security Reform
Estimated Impact of Plans from the 2020 Presidential Campaign
```

Its assumptions vintage, `103050-five-dem.txt` lines 330–331:

```text
microsimulation tool. The current version of DYNASIM4 uses the 2019 Social Security trustees’
intermediate demographic and economic assumptions (Board of Trustees 2019), which do not
```

The committed field read "Estimated Impact of Plans by 2020 Presidential Candidates" and "2020 Trustees intermediate assumptions".

### Source files

The quotes are from the archived copies in `~/PolicyEngine/dynasim-refs` (outside this repository):

| File | SHA-256 |
|---|---|
| `411260-benefit-reductions.txt` | `4b9f3becd99718948f97265222ecb2f2065a1fe6a18a5a0a6be62d5df994504c` |
| `411260-benefit-reductions.pdf` | `88934782c267fb0d7f08106ef930a19866c41c89504d04ad7a6d77d454d034ae` |
| `103050-five-dem.txt` | `955d4376bb6951815e028467a3eccc2822f2d6dced08bdcff8c94c6719e16706` |
| `103050-five-dem.pdf` | `659e331b37306b220aec668425518eb613e24faf9852397b2845ffb935753a5f` |

`tests/test_anchor_provenance_erratum.py` checks every quote above against these files when they are present, and pins the corrected strings in the scripts.

## What this change corrects

- `scripts/replication_cost_ordering.py`: `MERMIN_ANCHOR_CITE` now attributes the row to CBO (2005) as reported in Mermin (2005); `CAREGIVER_ANCHOR_CITE` reads DYNASIM4 ID980; the module docstring, the anchor comments and the T2-swap named delta say the same.
- `scripts/replication_caregiver.py`: the module docstring, the `paper` field and the Table 15 citation read DYNASIM4 ID980, with the report's subtitle and 2019 Trustees assumptions.
- `scripts/replication_mermin_rows.py`: the Table 1 citation in `anchor_provenance()` and the comment on `ANCHOR_TABLE1_PAYROLL_PCT` name CBO (2005) for the deficit row, and the citation now gives the page (PDF p.15) that the old citation left blank.
- `paper/paper.qmd`: the cost-ordering paragraph said "DYNASIM ranks them the other way". It now says the anchor column is CBO's 2005 scoring, which Mermin reports in the same table as the DYNASIM3 benefits, and that DYNASIM3's 2050 benefit row for ages 62 to 67 orders the pair the same way.

A rerun of the edited scripts would emit the corrected strings. No computation, numeric constant or output key changed.

## Committed artifacts that keep the old labels

These bytes are not edited. Read them through this erratum.

| Artifact | JSON pointer or location | Old label |
|---|---|---|
| `runs/replication_cost_ordering_v1.json` | `/anchor_provenance/mermin_cite`, `/provisions/0/anchor_cite` to `/provisions/3/anchor_cite` | "Mermin (2005), Urban Institute 411260, DYNASIM3 Runid 432, Table 1 …" |
| `runs/replication_cost_ordering_v1.json` | `/anchor_provenance/caregiver_cite`, `/provisions/4/anchor_cite` to `/provisions/7/anchor_cite` | "… Urban Institute 103050, DYNASIM3 ID980, Table 3 …" |
| `runs/replication_cost_ordering_v1.json` | `/named_deltas/4` | "flipping PPI and NRA versus DYNASIM's fuller projected careers" (the anchor is CBO's column) |
| `runs/replication_caregiver_v1.json` | `/anchor_provenance/paper` | "… Plans by 2020 Presidential Candidates … DYNASIM3, ID980. 2020 Trustees intermediate assumptions." |
| `runs/replication_caregiver_v1.json` | `/anchor_provenance/table15_bottom_fifth_2065/citation` | "… scheduled scenario; DYNASIM3 ID980" |
| `runs/replication_mermin_rows_v1.json` | `/anchor_provenance/table1_ages_62_67_by_year/citation` | "Table 1 (printed p., DYNASIM3 Runid 432); 2050 row", which also covers the block's `seventy_five_year_payroll_pct` (the CBO row) |
| `benchmarks/registry.json` (built by `benchmarks/build_registry.py`) | row `dynasim.mermin.four_reform_cost_ordering`: `/external_reference`, `/source_pin/exact_locators/0/document` and `/concept_mismatch/frame` | "DYNASIM3 / CBO 2005 actuarial scoring"; "… report 411260, DYNASIM3 Runid 432"; "the published order comes from DYNASIM/CBO actuarial scoring" |
| `benchmarks/history.jsonl` lines 41 and 83, `benchmarks/wall.md` | the same row id | `dynasim.mermin.four_reform_cost_ordering` |

The registry is left alone because its append protocol (`benchmarks/README.md`) requires a spec change to carry a `spec_revisions` note, and `benchmarks/build_wall.py` requires the latest history record set to use the current registry SHA-256. A relabel therefore has to ride on the next evaluation append. Until then the row's published order is CBO's 2005 estimates as reported in Mermin (2005) Table 1.

## Identifiers kept, not renamed

Row ids and output keys that `benchmarks/history.jsonl`, `gates.yaml` or other artifacts point into keep their names. Each is an alias for the corrected provenance:

- `dynasim.mermin.four_reform_cost_ordering` (registry and history row id): "mermin" names the report that publishes the ordering; the ordering is CBO's 2005 estimates.
- `/tests/T2_mermin_kendall_tau` in `runs/replication_cost_ordering_v1.json` (read by `benchmarks/build_registry.py`): "mermin" means the Mermin (2005) Table 1 deficit row, that is, CBO's 2005 estimates.
- `/anchor_provenance/mermin_payroll_pct` in the same artifact (read by `gates.yaml`, W1 family C fingerprint `c1`) and `/anchor_provenance/mermin_cite`: the same CBO row.
- `seventy_five_year_payroll_pct` (`scripts/replication_mermin_rows.py`) and `ANCHOR_TABLE1_PAYROLL_PCT`: the same CBO row.

`gates.yaml` names the W1 `c1` anchor "Mermin Table 1 (75-yr payroll savings ordering)". That label is accurate and is not changed; its values are the same CBO 2005 estimates.

## What does not change

- Every anchor value is unchanged: the Mermin deficit row (scheduled −1.69, price indexing +0.68, progressive price indexing −0.14, reduced COLA −1.12, NRA raised to 70 −0.5) and the Table 3 caregiver row (Biden −0.12, Buttigieg −0.51, Klobuchar −0.12, Warren −0.30).
- Cost-ordering results, as committed in `runs/replication_cost_ordering_v1.json`: T1 sign agreement 100% (forecast 100%, met); T2 Kendall tau 0.667 against the CBO column (forecast 1.0, not met); T3 Kendall tau 0.913 against the DYNASIM4 Table 3 row (forecast at least 0.8, met). The committed T2 cross-check against Mermin's DYNASIM3 2050 percent-of-scheduled row (`kendall_tau_pct_scheduled_xcheck`) is also 0.667, so T2's tau is the same against CBO's deficit row and against DYNASIM3's own benefit row.
- The caregiver replication, the Mermin-rows replication and their committed results are unchanged; only citation text changes.
- `docs/references.bib` is unchanged. The `mermin2005benefitreductions` note ("DYNASIM3, Runid 432") correctly names the report's own microsimulation run, and `smith2020fivedem` already reads "DYNASIM4, ID980".
