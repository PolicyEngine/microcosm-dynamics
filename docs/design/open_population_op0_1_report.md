# OP0.1 build report

## 1. What was produced

- [Maintainer audit](open_population_op0_1.md): six draft records, exposure inventory, donor comparison, source access, proposed conventions and coordinator questions.
- [Machine-readable records](open_population_op0_1_records.json): schema `open_population_op0_record.v1`, six records with `status: draft`, source-specific tolerances, candidate uncertainty, named unrun power procedures, manifest statuses and the exact registry pin.
- [Unit test](../../tests/open_population/test_op0_1_records.py): reads only the documentation JSON; validates completeness, draft state, pending years, registry snapshot, manifest/power shapes and access fields.

Commits already preserved on `openpop-op0-1-audit-20261024` in the workspace-local Git store:

- `a04617e1b948161f16300a920613ca24667cd6e4` — docs: draft OP0.1 birth audit and registry boundary.
- `d131cebcb0f50af9fa2269cd3046a3710eb7ee4e` — docs: draft migration, target, population and horizon records.
- `99d4f6fabca7c45744b21791431513473a2ff51d` — docs: complete OP0.1 exposure audit and validate draft records.

The following handoff commit adds this report and the final transitive-consumer citations; its SHA is in the verified bundle head and the final response. No history was rewritten and nothing was pushed. Normal `git add`/`git commit` failed because this linked worktree’s administrative Git directory is in the caller clone outside the writable boundary. The original worktree HEAD therefore remains at the assigned base. To preserve coherent commits without writing there, the build used `.venv/op0-commit-store` and exported `open_population_op0_1_commits.bundle` in this workspace. That bundle contains only commits after `b51ffb576090155adc2befd2715c58b27bb2afa9` and requires that base.

The main session can import the bundle into its assigned branch (these commands are a handoff, not commands run in the caller checkout):

```sh
git fetch /Users/maxghenis/.subfleet/worktrees/20261024-075734-openpop-op0-1-build-r3/open_population_op0_1_commits.bundle refs/heads/openpop-op0-1-audit-20261024
git cherry-pick b51ffb576090..FETCH_HEAD
```

Validation: `.venv/bin/python -m pytest -q -m unit tests/open_population/test_op0_1_records.py` — **5 passed**; `.venv/bin/black --check -l 79 tests/open_population/test_op0_1_records.py` and `.venv/bin/ruff check tests/open_population/test_op0_1_records.py` — **passed**. Python is 3.14.7. The test was run in one process. No power simulation or real-data calculation ran. `tests/tier_counts.json` and `tests/README-tiers.md` remain untouched; the coordinator owns the expected global tier-count update.

## 2. Settled facts, proposals and open points per record

| Record | Settled documentary facts / approved boundaries | Proposal for review | Open before freeze |
| --- | --- | --- | --- |
| `gate_birth` | NCHS 2016–2024 age-group rates exposed;2024 selected within TR2026 baseline shape. Historical kernel ages 15–49/parity3+ and cohort support documented. | Regression age-rate companion;2015/unused sex/nativity/observed-single-age candidates; CPS June 2012 parity fit. | External nonuse, disjoint sex-ratio pin, future cohorts, native denominators/bridges, numeric allowances and power. |
| `gate_imm` |2010–2013 fit/2014 stock-proxy design; no in-repository PUMS reader found. Upstream PSID/frame/Census dependencies prevent a blanket unused claim. | Annual separately weighted files, observed family packets, component-specific timing/survival bridge. | J/registry, possible2014 upstream exit-assumption exposure, resident/SSA-area bridge, recent-arrival cell sizes and pooling. |
| Emigration check | Census 2023 documents residual assumptions using ACS 2011–2015/2015–2019; no independently observed exit holdout found. | Keep composition report-only, `EMIGRATION_UNIDENTIFIED`; post-death exit step. | Same-year entrant eligibility/exposure, family exit unit, resident/SSA-area mapping and independent exit evidence. |
| Demographic target manifest | OACT CY catalog publishes single-age population; V.A3 has coarse age groups/no nativity. Mortality lane owns death alignment; OP6 never selects deaths. | Derived NCHS or verified CBO fertility bridge; population validation-only; whole-unit nondeath selection. | Single-age OACT fertility unlocated; bridge choice, exact captured rows/bytes/terms, target-unit tolerances/corridors. |
| `gate_pop` | DHC PCT12 is sex by single-year age; DA full-resident/PES household universes differ.2020 household estimands and upstream ACS 2019 uses are exposed. | July 1,2013 start, separate GQ strata, April 1/calendar-year mapping;2013-vintage fitted-law primary arm if feasible, realized-control companion. | Max chooses arms/conventions; exact coverage allowance, independence by estimand, file capture and power. |
| Demographic horizon | Post2030 conditional principle approved; Census 2023 publishes nativity through 2100. OACT V.A3 no nativity; CBO requested population-nativity margins not established in inspected documentation. | One 2100 production horizon; invented Leslie differential precision procedure; explicit component continuation/refusal. | Max’s continuation rules, B4/mortality support, separately documented CBO long-horizon nativity product and capture. |

All six records are drafts. J has not recorded candidates in `daf02425`; every proposed held-out year remains `pending_registry`. No gate was registered, no registry was edited and no scientific admission was made.

## 3. Official pages and repository citations

Every page below was read or attempted on **2026-10-24**. Confirmed means documentation, metadata or a catalog was readable; it never means a linked data file was opened. Unverified attempts are included for completeness. The two generic source URLs initially proposed for CPS/population estimates were superseded by the exact confirmed documentation below; no data-file access was attempted.

| Official URL | Reachability | Scope |
| --- | --- | --- |
| [https://www2.census.gov/programs-surveys/popproj/technical-documentation/methodology/methodstatement23.pdf](https://www2.census.gov/programs-surveys/popproj/technical-documentation/methodology/methodstatement23.pdf) | confirmed | Methodology only, especially pp.2, 11–12; no table/workbook opened |
| [https://www.census.gov/data/tables/2023/demo/popproj/2023-summary-tables.html](https://www.census.gov/data/tables/2023/demo/popproj/2023-summary-tables.html) | confirmed | Main-series catalog names/scope, no linked tables opened |
| [https://www.census.gov/programs-surveys/acs/microdata/documentation.html](https://www.census.gov/programs-surveys/acs/microdata/documentation.html) | confirmed | Documentation index |
| [https://www2.census.gov/programs-surveys/acs/tech_docs/pums/data_dict/](https://www2.census.gov/programs-surveys/acs/tech_docs/pums/data_dict/) | confirmed | Dictionary directory index |
| [https://www2.census.gov/programs-surveys/acs/tech_docs/pums/](https://www2.census.gov/programs-surveys/acs/tech_docs/pums/) | confirmed | Documentation directory index |
| [https://www2.census.gov/programs-surveys/acs/tech_docs/pums/data_dict/PUMS_Data_Dictionary_2019.txt](https://www2.census.gov/programs-surveys/acs/tech_docs/pums/data_dict/PUMS_Data_Dictionary_2019.txt) | confirmed | 2019 variable definitions/codes, not records |
| [https://www2.census.gov/programs-surveys/acs/tech_docs/pums/data_dict/PUMSDataDict10.pdf](https://www2.census.gov/programs-surveys/acs/tech_docs/pums/data_dict/PUMSDataDict10.pdf) | confirmed | 2010 dictionary |
| [https://www2.census.gov/programs-surveys/acs/tech_docs/pums/data_dict/PUMSDataDict14.pdf](https://www2.census.gov/programs-surveys/acs/tech_docs/pums/data_dict/PUMSDataDict14.pdf) | confirmed | 2014 dictionary |
| [https://www2.census.gov/programs-surveys/acs/tech_docs/pums/ACS 2019_PUMS_README.pdf](https://www2.census.gov/programs-surveys/acs/tech_docs/pums/ACS 2019_PUMS_README.pdf) | confirmed | 2019 ReadMe, especially pp.11–13 and 16 |
| [https://www2.census.gov/programs-surveys/acs/tech_docs/pums/ACS 2014_PUMS_README.pdf](https://www2.census.gov/programs-surveys/acs/tech_docs/pums/ACS 2014_PUMS_README.pdf) | confirmed | 2014 ReadMe |
| [https://www2.census.gov/programs-surveys/acs/tech_docs/pums/accuracy/2019AccuracyPUMS.pdf](https://www2.census.gov/programs-surveys/acs/tech_docs/pums/accuracy/2019AccuracyPUMS.pdf) | confirmed | Sample design/accuracy documentation |
| [https://api.census.gov/data/2011/acs/acs1/pums/variables.html](https://api.census.gov/data/2011/acs/acs1/pums/variables.html) | confirmed | Metadata dictionary only |
| [https://api.census.gov/data/2012/acs/acs1/pums/variables.html](https://api.census.gov/data/2012/acs/acs1/pums/variables.html) | confirmed | Metadata dictionary only |
| [https://api.census.gov/data/2013/acs/acs1/pums/variables.html](https://api.census.gov/data/2013/acs/acs1/pums/variables.html) | confirmed | Metadata dictionary only |
| [https://api.census.gov/data/2010/acs/acs1/pums/variables.json](https://api.census.gov/data/2010/acs/acs1/pums/variables.json) | confirmed | Metadata dictionary only; printed selected variable names/presence |
| [https://api.census.gov/data/2011/acs/acs1/pums/variables.json](https://api.census.gov/data/2011/acs/acs1/pums/variables.json) | confirmed | Metadata dictionary only; printed selected variable names/presence |
| [https://api.census.gov/data/2012/acs/acs1/pums/variables.json](https://api.census.gov/data/2012/acs/acs1/pums/variables.json) | confirmed | Metadata dictionary only; printed selected variable names/presence |
| [https://api.census.gov/data/2013/acs/acs1/pums/variables.json](https://api.census.gov/data/2013/acs/acs1/pums/variables.json) | confirmed | Metadata dictionary only; printed selected variable names/presence |
| [https://api.census.gov/data/2014/acs/acs1/pums/variables.json](https://api.census.gov/data/2014/acs/acs1/pums/variables.json) | confirmed | Metadata dictionary only; printed selected variable names/presence |
| [https://api.census.gov/data/2019/acs/acs1/pums/variables.json](https://api.census.gov/data/2019/acs/acs1/pums/variables.json) | confirmed | Metadata dictionary only; printed selected variable names/presence |
| [https://www.census.gov/newsroom/blogs/random-samplings/2022/03/period-estimates-american-community-survey.html](https://www.census.gov/newsroom/blogs/random-samplings/2022/03/period-estimates-american-community-survey.html) | confirmed | Calendar-period/reference-date explanation |
| [https://www.census.gov/topics/income-poverty/income/guidance/group-quarters.html](https://www.census.gov/topics/income-poverty/income/guidance/group-quarters.html) | confirmed | ACS/census residence and GQ treatment |
| [https://www.census.gov/programs-surveys/acs/methodology/sample-size-and-data-quality/sample-size-definitions.html](https://www.census.gov/programs-surveys/acs/methodology/sample-size-and-data-quality/sample-size-definitions.html) | confirmed | Sample-size definitions/design history |
| [https://www.census.gov/programs-surveys/acs/methodology/sample-size-and-data-quality.html](https://www.census.gov/programs-surveys/acs/methodology/sample-size-and-data-quality.html) | confirmed | Redirects to https://www.census.gov/acs/www/methodology/sample-size-and-data-quality/ ; quality-measure catalog only |
| [https://www.census.gov/help/topics/faq.information-on-the-number-of-people-in-my-area-surveyed-by-acs.html](https://www.census.gov/help/topics/faq.information-on-the-number-of-people-in-my-area-surveyed-by-acs.html) | confirmed | Published unweighted-count table IDs and coverage |
| [https://www.census.gov/programs-surveys/decennial-census/about/coverage-measurement/similarities-differences-da-pes.html](https://www.census.gov/programs-surveys/decennial-census/about/coverage-measurement/similarities-differences-da-pes.html) | confirmed | DA/PES universe, categories and uncertainty |
| [https://www.census.gov/programs-surveys/decennial-census/about/coverage-measurement/da.html](https://www.census.gov/programs-surveys/decennial-census/about/coverage-measurement/da.html) | confirmed | Release scope/date and coverage product catalog |
| [https://www2.census.gov/geo/pdfs/maps-data/data/tiger/tgrshp2023/TGRSHP2023_TechDoc_Ch1.pdf](https://www2.census.gov/geo/pdfs/maps-data/data/tiger/tgrshp2023/TGRSHP2023_TechDoc_Ch1.pdf) | confirmed | §1.2 federal-work reuse/attribution statement |
| [https://www.census.gov/programs-surveys/decennial-census/about/coverage-measurement/pes.html](https://www.census.gov/programs-surveys/decennial-census/about/coverage-measurement/pes.html) | unverified | Search result readable; explicit page fetch timed out |
| [https://www2.census.gov/programs-surveys/acs/tech_docs/pums/data_dict/PUMSDataDict14.txt](https://www2.census.gov/programs-surveys/acs/tech_docs/pums/data_dict/PUMSDataDict14.txt) | unverified | Web tool could not decode text; equivalent PDF above confirmed |
| [https://www2.census.gov/programs-surveys/acs/tech_docs/pums/2019ACS_PUMS_User_Guide.pdf](https://www2.census.gov/programs-surveys/acs/tech_docs/pums/2019ACS_PUMS_User_Guide.pdf) | unverified | Guessed filename unavailable; correct 2019 ReadMe above confirmed |
| [https://www.census.gov/about/policies/copyright.html](https://www.census.gov/about/policies/copyright.html) | unverified | HTTP 404 |
| [https://www.ssa.gov/oact/Downloadables/CY/index.html](https://www.ssa.gov/oact/Downloadables/CY/index.html) | confirmed | Single-age population, date/universe definitions; catalog only. |
| [https://www.ssa.gov/oact/tr/2026/lrIndex.html](https://www.ssa.gov/oact/tr/2026/lrIndex.html) | confirmed | Demographic table catalog only; ordinary HTTP request403. |
| [https://www.ssa.gov/oact/TR/2026/V_A_demo.html](https://www.ssa.gov/oact/TR/2026/V_A_demo.html) | unverified | Header-only HTTP attempt403; no report table opened. |
| [https://www.cbo.gov/publication/61879](https://www.cbo.gov/publication/61879) | confirmed | Demographic release landing page and correction notice. |
| [https://www.cbo.gov/publication/61994](https://www.cbo.gov/publication/61994) | confirmed | HTML demographic report definitions/horizon only; no workbook. |
| [https://www.cbo.gov/data/budget-economic-data](https://www.cbo.gov/data/budget-economic-data) | confirmed | Demographic catalog, canonical recurring-data/57059. |
| [https://www.cbo.gov/recurring-data/57059](https://www.cbo.gov/recurring-data/57059) | confirmed | Canonical demographic catalog dimensions. |
| [https://www.cdc.gov/nchs/data_access/vitalstatsonline.htm](https://www.cdc.gov/nchs/data_access/vitalstatsonline.htm) | confirmed | NVSS annual guide catalog. |
| [https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/DVS/natality/UserGuide2015.pdf](https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/DVS/natality/UserGuide2015.pdf) | confirmed | 2015 codebook pp.5–6,27; no microdata. |
| [https://wonder.cdc.gov/wonder/help/natality.html](https://wonder.cdc.gov/wonder/help/natality.html) | confirmed | NCHS natality documentation only, no query/extract. |
| [https://www.cdc.gov/nchs/nvss/dvs_data_release.htm](https://www.cdc.gov/nchs/nvss/dvs_data_release.htm) | confirmed | Public-use release policy; no data file. |
| [https://www.census.gov/data/tables/2023/dec/2020-census-dhc.html](https://www.census.gov/data/tables/2023/dec/2020-census-dhc.html) | confirmed | 2020 DHC table catalog only: PCT12 Sex by Single-Year Age. |
| [https://www2.census.gov/programs-surveys/popest/technical-documentation/methodology/2010-2013/2013-natstcopr-meth.pdf](https://www2.census.gov/programs-surveys/popest/technical-documentation/methodology/2010-2013/2013-natstcopr-meth.pdf) | confirmed | Vintage 2013 methodology; resident universe and July 1 reference. |
| [https://www.census.gov/data/developers/data-sets/popest-popproj/popest/popest-vars.Vintage_2013.html](https://www.census.gov/data/developers/data-sets/popest-popproj/popest/popest-vars.Vintage_2013.html) | confirmed | Vintage 2013 DATE metadata only; no estimates data. |
| [https://www.census.gov/programs-surveys/cps/technical-documentation/complete/2012.html](https://www.census.gov/programs-surveys/cps/technical-documentation/complete/2012.html) | confirmed | June 2012 Fertility Use File documentation catalog. |
| [https://www.census.gov/programs-surveys/cps/technical-documentation/complete/2014.html](https://www.census.gov/programs-surveys/cps/technical-documentation/complete/2014.html) | confirmed | June 2014 fertility supplement documentation catalog. |
| [https://www2.census.gov/programs-surveys/cps/techdocs/cpsjun12.pdf](https://www2.census.gov/programs-surveys/cps/techdocs/cpsjun12.pdf) | confirmed | June 2012 codebook/questionnaire/accuracy: PESF1,PXSF1,PWSSWGT; no outcome appendix used. |
| [https://www2.census.gov/programs-surveys/cps/techdocs/cpsjun14.pdf](https://www2.census.gov/programs-surveys/cps/techdocs/cpsjun14.pdf) | confirmed | June 2014 codebook: parity and allocation metadata only. |

Repository references are to the assigned base `b51ffb576090` unless a different commit is explicit. The approved design exists in Git at `5c82dbd9`, even though that path is absent from the assigned working tree. Listed ranges describe code or metadata inspected; none authorizes reading a restricted artifact mentioned by a source.

- `5c82dbd9:docs/design/open_population.md:159-160,291-363`.
- `5c82dbd9:docs/design/open_population.md:161,350-363,464-483`.
- `5c82dbd9:docs/design/open_population.md:162,164,291-363`.
- `5c82dbd9:docs/design/open_population.md:163,325-363,424-435`.
- `5c82dbd9:docs/design/open_population.md:291-307`.
- `5c82dbd9:docs/design/open_population.md:291-363`.
- `5c82dbd9:docs/design/open_population.md:95-105,140-146,167,170,352-363,444-451,515-540`.
- `CLAUDE.md (read in full)`.
- `daf02425:docs/design/track_b_holdout_registry.json (full permitted registry; SHA-256 in audit)`.
- `daf02425:docs/design/track_b_holdout_registry_mutations.json (full permitted mutation record; SHA-256 in audit)`.
- `daf02425:src/populace_dynamics/track_b/holdout_registry.py:8-44,76-159,283-334,396-410,756-804,1004-1014,1033-1078,1105-1171`.
- `daf02425:tests/test_track_b_holdout_registry.py:254-405,506-558,959-1028 (module read in full)`.
- `daf02425:tests/test_track_b_holdout_registry_committed.py:24-91 (module read in full)`.
- `data/external/cbo2026/provenance.md:29-56`.
- `data/external/census_gate2b_anchor_sources.md:50-64`.
- `data/external/nchs_asfr_2024.json (keys/provenance/hash only)`.
- `data/external/tr2026/provenance.md:54`.
- `data/external/tr2026/sources.json:1`.
- `data/external/track_u2/weights.json:149,337,344,350,424`.
- `docs/baselines.md:555-557`.
- `docs/calibration-targets.md:45-62`.
- `docs/funder-summary.md:174-175`.
- `docs/infrastructure.md:104-106`.
- `docs/methodology.md:9-11`.
- `docs/plans/microcosm-start.md:109-123`.
- `docs/progress.md:331`.
- `docs/progress/progress.json:115`.
- `docs/public-validation-inventory.md:34,57,75,147`.
- `gates.yaml:1298`.
- `paper/paper.qmd (included only in an interrupted value-suppressed search whitelist; whether reached is unknown; no content displayed)`.
- `runs/gate2_hazard_v16.json:8732-8759,12485-12512,16238-16265,19990-20017,23742-23769 (age/parity/cohort metadata only)`.
- `runs/gate2_hazard_v16.json:8732-8759,12485-12512,16238-16265,19990-20017,23742-23769 (metadata only)`.
- `scripts/build_gate2_floors.py:626-674,693-743,924-931`.
- `scripts/build_gate2_floors.py:696,1222`.
- `scripts/build_gate2_floors.py:78,626-674,693-743,924-931`.
- `scripts/build_gate2b_floors.py:818-872`.
- `scripts/build_gate2c_floors.py:1031-1069`.
- `scripts/build_gate_w1_floors.py:649-660,696-704`.
- `scripts/extract_di_asr_2008.py:21-22,241-272,675,863-865`.
- `scripts/fetch_nchs_asfr.py:119 (incidental hardcoded constant display; value omitted)`.
- `scripts/fetch_nchs_asfr.py:52-62,257-293,309-360`.
- `scripts/fetch_nchs_asfr.py:9-25,52-62,82-90,257-293,309-360`.
- `scripts/gate2b_anchor_decomposition.py:59,253-265`.
- `scripts/gate2b_anchor_decomposition.py:59,253-265,402-404`.
- `scripts/gate2b_anchor_decomposition.py:8-14,55-59`.
- `scripts/gate2c_anchor_decomposition.py:271,303-307`.
- `scripts/run_gate2_candidate5.py:189-194,235-249`.
- `src/populace_dynamics/baselines/__init__.py:72-76`.
- `src/populace_dynamics/baselines/asfr.py:22,124 (incidental hardcoded constant display; values omitted)`.
- `src/populace_dynamics/baselines/asfr.py:67-135`.
- `src/populace_dynamics/baselines/cbo2026_long_term.py:330`.
- `src/populace_dynamics/baselines/common2026.py:25,97,113`.
- `src/populace_dynamics/baselines/fertility.py:169-174`.
- `src/populace_dynamics/baselines/tr2026_intermediate.py:21-28,84,165-168,222-233`.
- `src/populace_dynamics/baselines/tr2026_intermediate.py:245`.
- `src/populace_dynamics/baselines/tr2026_intermediate.py:84,165-168`.
- `src/populace_dynamics/baselines/track_a.py:286-287`.
- `src/populace_dynamics/data/tr2026.py:3-4`.
- `src/populace_dynamics/data/transitions.py:113`.
- `src/populace_dynamics/data/u2_source_registry.py:1-3,26-28`.
- `src/populace_dynamics/data/u2_source_registry.py:1-3,26-28,392-394`.
- `src/populace_dynamics/engine/di_entitlement_rates.py:740`.
- `src/populace_dynamics/engine/entrant_schedule.py:14-22,37-48,359-371`.
- `src/populace_dynamics/engine/entrant_schedule.py:3-6,37-42,185-200`.
- `src/populace_dynamics/engine/entrant_schedule.py:359-371`.
- `src/populace_dynamics/engine/marital.py:352-374`.
- `src/populace_dynamics/models/family_transitions/components/fertility.py:28-45,80-94,123-157,170-194`.
- `tests/baselines/test_asfr_and_claim_tables.py:41,49,53,59,73`.
- `tests/test_gate2_floors.py:42,454`.
- `tests/test_nchs_asfr.py:21`.

Instruction sources outside the repository: the full `RESTRICTED-FILES.md` and Track B design revision3 §5.1–§5.2/§7 at `/Users/maxghenis/microcosm-launch-evidence/dynasim-parity-20260909/`. No other evidence working folders were opened.

Issue42 source-specific registration inspection used `gh issue view 42`; the installed CLI rejected `--comments` together with `--json`, so comments were read through its JSON field with filtering before output. Known restricted result IDs were excluded, and numeric text was redacted before display. Relevant prior-use references were [Census household concept](https://github.com/PolicyEngine/microcosm-dynamics/issues/42#issuecomment-4939453260), [partner-inclusion registration](https://github.com/PolicyEngine/microcosm-dynamics/issues/42#issuecomment-4939456379), [NCHS mortality trend](https://github.com/PolicyEngine/microcosm-dynamics/issues/42#issuecomment-4911788302) and [later mortality-trend selection](https://github.com/PolicyEngine/microcosm-dynamics/issues/42#issuecomment-4928232089). These concern mortality or household concepts, not a second natality input. No named use of the other requested sources was established by that scoped search.

## 4. What could not be established

- No off-repository, upstream frame or other-lane nonexposure certification. The registry is incomplete, lacks the required source vocabulary and has no J candidate entry. All independent-holdout claims remain conditional on coordinator review.
- No published OACT single-age fertility series was established from safe catalogs. The single-age population series **was** established. Existing shape or CBO bridge selection is for Max/coordinator.
- CBO 2050/2065/2070 population by nativity was not established in inspected release documentation; this is a bounded unavailable result, not a claim that CBO never publishes such a product. No workbook was opened.
- No independently admissible exit holdout: ACS cohort residuals mix mortality/coverage/return migration and overlap the Census assumption construction. `EMIGRATION_UNIDENTIFIED` remains.
- No matched recent-arrival critical-cell counts or demonstrated 0.90 power. Overall ACS sizes do not resolve PUMS recent-arrival support; numerical allowances, effect profiles and pooling ladders need blinded prospective review.
- No captured target bytes, data-file reachability, complete file-specific terms, actual run cell values or exact output worksheet headers were verified. Manifest hashes therefore remain `to capture`; public documentation reachability is recorded separately.
- Exit timing/entry-year risk, universe/date/GQ bridges, gate_pop arms, continuation rules and displacement corridors remain explicit proposals or questions rather than builder rulings.

## 5. Restricted-files statement

No restricted local file was opened. In particular, no listed B2 outcome, DYNASIM/MINT output file, Urban report, issue113, PR554 body, B0.2/successor folder, U2 step4 run2 output, other session transcript/scratchpad or other Subfleet job folder was opened. No microdata or data download was opened; no real-data statistic was computed. The NCHS JSON was accessed only by a key/provenance/hash parser, and the candidate16 run only through age/parity/cohort metadata. On #560’s branch the only files read were exactly:

- `docs/design/track_b_holdout_registry.json`;
- `docs/design/track_b_holdout_registry_mutations.json`;
- `src/populace_dynamics/track_b/holdout_registry.py`;
- `tests/test_track_b_holdout_registry.py`;
- `tests/test_track_b_holdout_registry_committed.py`, all at `daf02425`.

The following incidents prevent an unqualified statement that no restricted content was encountered:

- A subagent code-only search incidentally displayed hardcoded published NCHS TFR constants from scripts/fetch_nchs_asfr.py:119, tests/test_nchs_asfr.py:46, baselines/asfr.py:22,124. Parent received value-free disclosure only; no values retained here. No restricted local file or data table was opened.

- An official SSA fertility-publication search returned cost/income/balance-section snippets. The subagent opened no such page/table/PDF, stopped general SSA search, and used only safe exact catalogs thereafter. Parent received value-free disclosure only. This prevents an unqualified no-restricted-text-exposure statement.

  Search-result snippet URLs (pages themselves were not opened):

  - [https://www.ssa.gov/OACT/TR/2026/IV_B_LRest.html](https://www.ssa.gov/OACT/TR/2026/IV_B_LRest.html).
  - [https://www.ssa.gov/oact/TR/2026/VI_D_LRsens.html](https://www.ssa.gov/oact/TR/2026/VI_D_LRsens.html).
  - [https://www.ssa.gov/oact/TR/2024/IV_B_LRest.html](https://www.ssa.gov/oact/TR/2024/IV_B_LRest.html).
  - [https://www.ssa.gov/OACT/TR/2024/IV_B_LRest.html](https://www.ssa.gov/OACT/TR/2024/IV_B_LRest.html).
  - [https://www.ssa.gov/oact/TR/2025/IV_B_LRest.html](https://www.ssa.gov/oact/TR/2025/IV_B_LRest.html).

- An initial filename whitelist included paper/paper.qmd, which the restrictions list separately labels cleared at an earlier commit. The subagent interrupted that value-suppressed scan; it cannot establish whether that path was reached, and no paper content/value was displayed. The completed broad scan excluded paper/ and benchmarks/ entirely. No standing restricted-list path was included in either whitelist.

No incident value is reproduced, used for a target or used to choose a tolerance. The parent received only value-free disclosures. PSID use follows the project's data-access record.
