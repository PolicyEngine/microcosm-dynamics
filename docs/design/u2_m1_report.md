# U2 milestone 1 delivery report

Documentary groundwork for `u2-draft-3` is complete and ready for independent source adjudication. Eight separate registries cover 2013–2023 waves without extending U1's `(2005, 2007, 2009, 2011, 2013)` tuple. The loader validates each registry schema and refuses unresolved entries and application dependencies. No PSID raw records were opened, no income/poverty/benefit was computed, and no estimator was run. No held-out target value or direction was inferred.

The [master adjudication record](u2_m1_source_adjudication.md) contains **1,744 RESOLVED and 48 TO VERIFY** route/field records (1,766 registry records plus 26 SSI/Census records). A RESOLVED mapping can still have a blocking application dependency; it does not authorize execution. Every row has a source-file line or printed-page citation.

## Blocker status

| Blocker | Status |
|---|---|
| 2015 male code 20 spouse routing | TO VERIFY |
| Code 90 OFUM versus spouse financial routing, 2015–2023 | TO VERIFY |
| Code 92 OFUM versus spouse financial routing, 2017–2023 | TO VERIFY; absence in 2013/2015 RESOLVED |
| Code 88 substantive financial/marital routing | TO VERIFY; labels and inherited administrative birth support RESOLVED |
| 2015 pension P62A contradictory routing language | TO VERIFY |
| 2017–2023 P64/P65 pension contract versus documented DC-only routes | TO VERIFY; reviewed amendment required |
| Later spouse age/sex universes | TO VERIFY |
| Historical combined spouse-retirement crosswalk | TO VERIFY; metadata only |
| Wealth accuracy-variable references | TO VERIFY |
| Revised 2017 individual-weight construction | TO VERIFY |
| Missing 2023 weight documentation | RESOLVED; official report captured |
| SSI capture, annual notice verification and constancy | RESOLVED |
| Track M Census capture reuse and coverage | RESOLVED |

Exact questions, quotes, page references and required amendments appear in the master record and linked registry JSON. The fresh 2017 technical report is byte-identical to the older staged report and does not settle the updated individual-weight construction. All documentary birth-year/wave support and design domains, including strata 88–94, are recorded; empirical support checks remain outside this milestone.

## Captures and pins

The [complete captured-source ledger](u2_m1_captured_sources.md) lists **all 108 captured files**, each URL, UTC retrieval, byte count and full SHA-256: 11 annual SSA notices, 88 annual historical CFR sections, seven parameter YAMLs pinned to PolicyEngine-US revision `a03e82e503f8e0285125ee0c5380410a964c8e8a`, and the original 2017/2023 PSID weight PDFs. Captures and manifests are committed. All source bytes were rehashed successfully.

- U2 SSI parameter capture: `a58d55c160b48cd3e21f730d45265374bd3c8a9eb7eae947469a5a5dc0b23762`.
- U2 SSI source manifest: `a7d09d735fa595e3c7060fb7972d088f0ee062a4c8bb31f739ef3ee578e82e53`.
- Track M Census capture, reused without download: `288399c475ae3ff02e6d8367425ee0a568b50d239da5656f24d0d2dfafabfb53`.
- U1 SSI capture unchanged: `79e641a10d95afba81c8d831852fb52ef0a801e7175e06df17e6cc7cc3e3c523`.
- U1 threshold capture unchanged: `dc21a78736f5085872cf56c9cf291258034c1293572b77455cba689a1ed0eec5`.

The capture checks all 2012–2022 annual FBR notices, all eight historical CFR sections in every year, five parameter constants, and exact 2012 SSI overlap with U1. A synthetic substantive change to one annual CFR edition is refused. Census coverage includes every 2003–2022 year, full 2012 overlap and unchanged 2022 numeric precision.

## Validation

**150 tests passed in the final three root runs, with no warnings or failures:**

| Final run | Result |
|---|---|
| `tests/track_u2/test_ssi_capture.py tests/data/test_track_u2_income_wealth.py` | 51 passed in 54.47s |
| `tests/track_u2/test_source_registries.py` | 80 passed in 262.86s |
| Four historical identity/reachability test functions below plus `tests/track_u2/test_pension_registry.py` | 19 passed in 352.47s |

The four existing test functions are `test_reducer_input_identity_matches_reviewed_branch`, `test_post_review_sources_are_outside_historical_reducer_identity`, `test_source_reachability_includes_implicit_package_initializers`, and `test_post_review_exclusions_are_unreachable_from_birth_evidence`, all in `tests/estimates/test_birth_evidence_artifact.py`. Their parametrizations account for seven of the 19 tests. No estimator/reducer execution test was selected.

Each run used `.venv/bin/python -m pytest -q`, `PYTHONPATH=.u2-work:src`, `POPULACE_DYNAMICS_PSID_DIR="$PWD/.u2-work/no-psid"`, and a distinct explicit `--basetemp` under `.u2-work`. A task-local audit hook logged read opens and refused staged PSID `.txt`/`.zip` reads. The contributor also ran focused schema tests (78 passed across two runs), which are included in the 80-test final root run and are not counted twice.

Black and Ruff passed on all ten changed/new Python files. Authored-file Git whitespace checks passed; unmodified official HTML/XML captures retain their original trailing whitespace and are excluded from that formatting check. All 51 protected-file hashes match the assigned base commit, not merely a regenerated local expectation. New source paths appear in `POST_REVIEW_SOURCE_EXCLUSIONS` and matching transitive reachability tests. No engine, `gates.yaml`, run specification, shared family/PSID reader or career estimator changed.

## Exposure and limitations

The [complete task exposure record](u2_m1_exposure.md), its [machine-readable counterpart](u2_m1_exposure.json), and the [complete observed Python runtime file inventory](u2_m1_runtime_exposure.json) enumerate every recorded opened task/document/source file, hash-only read, generated source, search/online exposure, dependency and temporary Python read. Contributor ledgers retain source-specific details. Native operating-system/Git pack reads and package-install internals are distinguished from documentary exposure.

The restriction ledger was read first. No prohibited report pages/tables, comparator lane, seal/transcription, uncleared availability statement, or restricted scratchpad was opened. The permitted public result memos were not opened. Incidental published whole-file frequencies in early codebook/weight-document excerpts were not used to resolve routes.

One procedural exception is disclosed: a contributor briefly authored a new helper at `/tmp/u2_ssi_download.py` before moving it into this workspace and removing the temporary copy. Initial pytest also used its default temporary directory and emitted stale-directory cleanup permission warnings; final runs use workspace-local temporary directories. No caller-worktree file was written.

Not performed: independent reviewer adjudication; resolution of the 48 open documentary entries; any pre-registration amendment, structural data pass or ratification; milestone 2 cohort configuration, estimator, tabulation, runner or dry run; any push. The contract remains `u2-draft-3`.

## Git delivery

Implementation commit: `6b19670e5c0603072af5b5ff1781095da3b113c1`. Shared Git metadata rejected writes, so commits use workspace-local `.u2-git`, branch `dynamics-u2-m1-documentary`, based on `d978d966270f`. The following documentation commit adds this report and the complete adjudication/exposure records. Both commits use `--no-verify` and the requested coauthor trailer; history is not rewritten.

Bundle delivery path: `/Users/maxghenis/.subfleet/worktrees/20260928-131741-u2-m1/u2-m1.bundle`. Final bundle verification and final commit SHA are reported in the delivery message. The bundle is intentionally outside its own committed contents.

## Files added (143)

- `data/external/track_u2/design.json`
- `data/external/track_u2/income.json`
- `data/external/track_u2/individual.json`
- `data/external/track_u2/pension.json`
- `data/external/track_u2/roles.json`
- `data/external/track_u2/support.json`
- `data/external/track_u2/u1_identity.json`
- `data/external/track_u2/wealth.json`
- `data/external/track_u2/weights.json`
- `data/external/track_u2_ssi_parameters_2012_2022.json`
- `docs/design/u2_m1_captured_sources.md`
- `docs/design/u2_m1_exposure.json`
- `docs/design/u2_m1_exposure.md`
- `docs/design/u2_m1_income_wealth_adjudication.md`
- `docs/design/u2_m1_income_wealth_exposure.json`
- `docs/design/u2_m1_pension_adjudication.md`
- `docs/design/u2_m1_pension_exposure.json`
- `docs/design/u2_m1_report.md`
- `docs/design/u2_m1_root_exposure.json`
- `docs/design/u2_m1_runtime_exposure.json`
- `docs/design/u2_m1_source_adjudication.md`
- `docs/design/u2_m1_ssi_adjudication.md`
- `docs/design/u2_m1_ssi_exposure.json`
- `scripts/capture_track_u2_income_wealth.py`
- `scripts/capture_track_u2_ssi_parameters.py`
- `scripts/capture_track_u2_ssi_sources.py`
- `src/populace_dynamics/data/u2_source_registry.py`
- `tests/data/test_track_u2_income_wealth.py`
- `tests/data/track_u2/psid_sources/cross_sec_weights_17.pdf`
- `tests/data/track_u2/psid_sources/cross_sec_weights_23.pdf`
- `tests/data/track_u2/psid_sources/weights17_manifest.json`
- `tests/data/track_u2/psid_sources/weights23_manifest.json`
- `tests/data/track_u2/ssi_capture_manifest.json`
- `tests/data/track_u2/ssi_sources/CFR-2012-title20-vol2-sec416-1112.xml`
- `tests/data/track_u2/ssi_sources/CFR-2012-title20-vol2-sec416-1121.xml`
- `tests/data/track_u2/ssi_sources/CFR-2012-title20-vol2-sec416-1124.xml`
- `tests/data/track_u2/ssi_sources/CFR-2012-title20-vol2-sec416-1161.xml`
- `tests/data/track_u2/ssi_sources/CFR-2012-title20-vol2-sec416-1163.xml`
- `tests/data/track_u2/ssi_sources/CFR-2012-title20-vol2-sec416-1205.xml`
- `tests/data/track_u2/ssi_sources/CFR-2012-title20-vol2-sec416-1218.xml`
- `tests/data/track_u2/ssi_sources/CFR-2012-title20-vol2-sec416-1806.xml`
- `tests/data/track_u2/ssi_sources/CFR-2013-title20-vol2-sec416-1112.xml`
- `tests/data/track_u2/ssi_sources/CFR-2013-title20-vol2-sec416-1121.xml`
- `tests/data/track_u2/ssi_sources/CFR-2013-title20-vol2-sec416-1124.xml`
- `tests/data/track_u2/ssi_sources/CFR-2013-title20-vol2-sec416-1161.xml`
- `tests/data/track_u2/ssi_sources/CFR-2013-title20-vol2-sec416-1163.xml`
- `tests/data/track_u2/ssi_sources/CFR-2013-title20-vol2-sec416-1205.xml`
- `tests/data/track_u2/ssi_sources/CFR-2013-title20-vol2-sec416-1218.xml`
- `tests/data/track_u2/ssi_sources/CFR-2013-title20-vol2-sec416-1806.xml`
- `tests/data/track_u2/ssi_sources/CFR-2014-title20-vol2-sec416-1112.xml`
- `tests/data/track_u2/ssi_sources/CFR-2014-title20-vol2-sec416-1121.xml`
- `tests/data/track_u2/ssi_sources/CFR-2014-title20-vol2-sec416-1124.xml`
- `tests/data/track_u2/ssi_sources/CFR-2014-title20-vol2-sec416-1161.xml`
- `tests/data/track_u2/ssi_sources/CFR-2014-title20-vol2-sec416-1163.xml`
- `tests/data/track_u2/ssi_sources/CFR-2014-title20-vol2-sec416-1205.xml`
- `tests/data/track_u2/ssi_sources/CFR-2014-title20-vol2-sec416-1218.xml`
- `tests/data/track_u2/ssi_sources/CFR-2014-title20-vol2-sec416-1806.xml`
- `tests/data/track_u2/ssi_sources/CFR-2015-title20-vol2-sec416-1112.xml`
- `tests/data/track_u2/ssi_sources/CFR-2015-title20-vol2-sec416-1121.xml`
- `tests/data/track_u2/ssi_sources/CFR-2015-title20-vol2-sec416-1124.xml`
- `tests/data/track_u2/ssi_sources/CFR-2015-title20-vol2-sec416-1161.xml`
- `tests/data/track_u2/ssi_sources/CFR-2015-title20-vol2-sec416-1163.xml`
- `tests/data/track_u2/ssi_sources/CFR-2015-title20-vol2-sec416-1205.xml`
- `tests/data/track_u2/ssi_sources/CFR-2015-title20-vol2-sec416-1218.xml`
- `tests/data/track_u2/ssi_sources/CFR-2015-title20-vol2-sec416-1806.xml`
- `tests/data/track_u2/ssi_sources/CFR-2016-title20-vol2-sec416-1112.xml`
- `tests/data/track_u2/ssi_sources/CFR-2016-title20-vol2-sec416-1121.xml`
- `tests/data/track_u2/ssi_sources/CFR-2016-title20-vol2-sec416-1124.xml`
- `tests/data/track_u2/ssi_sources/CFR-2016-title20-vol2-sec416-1161.xml`
- `tests/data/track_u2/ssi_sources/CFR-2016-title20-vol2-sec416-1163.xml`
- `tests/data/track_u2/ssi_sources/CFR-2016-title20-vol2-sec416-1205.xml`
- `tests/data/track_u2/ssi_sources/CFR-2016-title20-vol2-sec416-1218.xml`
- `tests/data/track_u2/ssi_sources/CFR-2016-title20-vol2-sec416-1806.xml`
- `tests/data/track_u2/ssi_sources/CFR-2017-title20-vol2-sec416-1112.xml`
- `tests/data/track_u2/ssi_sources/CFR-2017-title20-vol2-sec416-1121.xml`
- `tests/data/track_u2/ssi_sources/CFR-2017-title20-vol2-sec416-1124.xml`
- `tests/data/track_u2/ssi_sources/CFR-2017-title20-vol2-sec416-1161.xml`
- `tests/data/track_u2/ssi_sources/CFR-2017-title20-vol2-sec416-1163.xml`
- `tests/data/track_u2/ssi_sources/CFR-2017-title20-vol2-sec416-1205.xml`
- `tests/data/track_u2/ssi_sources/CFR-2017-title20-vol2-sec416-1218.xml`
- `tests/data/track_u2/ssi_sources/CFR-2017-title20-vol2-sec416-1806.xml`
- `tests/data/track_u2/ssi_sources/CFR-2018-title20-vol2-sec416-1112.xml`
- `tests/data/track_u2/ssi_sources/CFR-2018-title20-vol2-sec416-1121.xml`
- `tests/data/track_u2/ssi_sources/CFR-2018-title20-vol2-sec416-1124.xml`
- `tests/data/track_u2/ssi_sources/CFR-2018-title20-vol2-sec416-1161.xml`
- `tests/data/track_u2/ssi_sources/CFR-2018-title20-vol2-sec416-1163.xml`
- `tests/data/track_u2/ssi_sources/CFR-2018-title20-vol2-sec416-1205.xml`
- `tests/data/track_u2/ssi_sources/CFR-2018-title20-vol2-sec416-1218.xml`
- `tests/data/track_u2/ssi_sources/CFR-2018-title20-vol2-sec416-1806.xml`
- `tests/data/track_u2/ssi_sources/CFR-2019-title20-vol2-sec416-1112.xml`
- `tests/data/track_u2/ssi_sources/CFR-2019-title20-vol2-sec416-1121.xml`
- `tests/data/track_u2/ssi_sources/CFR-2019-title20-vol2-sec416-1124.xml`
- `tests/data/track_u2/ssi_sources/CFR-2019-title20-vol2-sec416-1161.xml`
- `tests/data/track_u2/ssi_sources/CFR-2019-title20-vol2-sec416-1163.xml`
- `tests/data/track_u2/ssi_sources/CFR-2019-title20-vol2-sec416-1205.xml`
- `tests/data/track_u2/ssi_sources/CFR-2019-title20-vol2-sec416-1218.xml`
- `tests/data/track_u2/ssi_sources/CFR-2019-title20-vol2-sec416-1806.xml`
- `tests/data/track_u2/ssi_sources/CFR-2020-title20-vol2-sec416-1112.xml`
- `tests/data/track_u2/ssi_sources/CFR-2020-title20-vol2-sec416-1121.xml`
- `tests/data/track_u2/ssi_sources/CFR-2020-title20-vol2-sec416-1124.xml`
- `tests/data/track_u2/ssi_sources/CFR-2020-title20-vol2-sec416-1161.xml`
- `tests/data/track_u2/ssi_sources/CFR-2020-title20-vol2-sec416-1163.xml`
- `tests/data/track_u2/ssi_sources/CFR-2020-title20-vol2-sec416-1205.xml`
- `tests/data/track_u2/ssi_sources/CFR-2020-title20-vol2-sec416-1218.xml`
- `tests/data/track_u2/ssi_sources/CFR-2020-title20-vol2-sec416-1806.xml`
- `tests/data/track_u2/ssi_sources/CFR-2021-title20-vol2-sec416-1112.xml`
- `tests/data/track_u2/ssi_sources/CFR-2021-title20-vol2-sec416-1121.xml`
- `tests/data/track_u2/ssi_sources/CFR-2021-title20-vol2-sec416-1124.xml`
- `tests/data/track_u2/ssi_sources/CFR-2021-title20-vol2-sec416-1161.xml`
- `tests/data/track_u2/ssi_sources/CFR-2021-title20-vol2-sec416-1163.xml`
- `tests/data/track_u2/ssi_sources/CFR-2021-title20-vol2-sec416-1205.xml`
- `tests/data/track_u2/ssi_sources/CFR-2021-title20-vol2-sec416-1218.xml`
- `tests/data/track_u2/ssi_sources/CFR-2021-title20-vol2-sec416-1806.xml`
- `tests/data/track_u2/ssi_sources/CFR-2022-title20-vol2-sec416-1112.xml`
- `tests/data/track_u2/ssi_sources/CFR-2022-title20-vol2-sec416-1121.xml`
- `tests/data/track_u2/ssi_sources/CFR-2022-title20-vol2-sec416-1124.xml`
- `tests/data/track_u2/ssi_sources/CFR-2022-title20-vol2-sec416-1161.xml`
- `tests/data/track_u2/ssi_sources/CFR-2022-title20-vol2-sec416-1163.xml`
- `tests/data/track_u2/ssi_sources/CFR-2022-title20-vol2-sec416-1205.xml`
- `tests/data/track_u2/ssi_sources/CFR-2022-title20-vol2-sec416-1218.xml`
- `tests/data/track_u2/ssi_sources/CFR-2022-title20-vol2-sec416-1806.xml`
- `tests/data/track_u2/ssi_sources/fr_ssi_2012.html`
- `tests/data/track_u2/ssi_sources/fr_ssi_2013.html`
- `tests/data/track_u2/ssi_sources/fr_ssi_2014.html`
- `tests/data/track_u2/ssi_sources/fr_ssi_2015.html`
- `tests/data/track_u2/ssi_sources/fr_ssi_2016.html`
- `tests/data/track_u2/ssi_sources/fr_ssi_2017.html`
- `tests/data/track_u2/ssi_sources/fr_ssi_2018.html`
- `tests/data/track_u2/ssi_sources/fr_ssi_2019.html`
- `tests/data/track_u2/ssi_sources/fr_ssi_2020.html`
- `tests/data/track_u2/ssi_sources/fr_ssi_2021.html`
- `tests/data/track_u2/ssi_sources/fr_ssi_2022.html`
- `tests/data/track_u2/ssi_sources/manifest.json`
- `tests/data/track_u2/ssi_sources/policyengine_us/amount/couple.yaml`
- `tests/data/track_u2/ssi_sources/policyengine_us/amount/individual.yaml`
- `tests/data/track_u2/ssi_sources/policyengine_us/eligibility/resources/limit/couple.yaml`
- `tests/data/track_u2/ssi_sources/policyengine_us/eligibility/resources/limit/individual.yaml`
- `tests/data/track_u2/ssi_sources/policyengine_us/income/exclusions/earned.yaml`
- `tests/data/track_u2/ssi_sources/policyengine_us/income/exclusions/earned_share.yaml`
- `tests/data/track_u2/ssi_sources/policyengine_us/income/exclusions/general.yaml`
- `tests/track_u2/test_pension_registry.py`
- `tests/track_u2/test_source_registries.py`
- `tests/track_u2/test_ssi_capture.py`

## Existing files modified

- `scripts/first_estimates_birth_evidence.py` — append exact U2 historical-source exclusions or their reachability assertions.
- `tests/estimates/test_birth_evidence_artifact.py` — append exact U2 historical-source exclusions or their reachability assertions.
