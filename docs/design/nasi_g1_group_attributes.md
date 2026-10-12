# G1: cohort-side group attributes

G1 adds a separate `person_id` side frame for the 2009/2011 projection cohorts, age-67 observations, and the Track M 2023 universe. It preserves the existing cohort frames and their pinned digests. The package computes person attributes; it does not produce reform outcomes, group shares, or new blind-test cells.

## Adjudication and resolution

Race and Hispanic origin use every asked race mention of present heads/reference persons and wives/spouses/partners in family waves 1985–2023. Sequence 1–20 identifies people present at interview; relationships 10 and 20/22 identify the two roles. The individual roster retains OFUMs. Race and nativity for a person never in an eligible role remain explicitly unknown, with availability counts in provenance.

Race frames are wave-specific: 1985–1989 has two mentions and no Latino race code; 1990–1993 adds race codes 5 (Latino origin) and 6 (color other than black or white), with 8 meaning more than two races. From 1994, race code 8 means DK. There are three race mentions in 1994–1996 and four from 1997. Waves 1997–2003 ask no Spanish-descent item: a Latino race mention establishes Hispanic origin, while its absence leaves origin unknown. From 2005, code 5 means Native Hawaiian/Pacific Islander and the Spanish-descent question returns. Direct Spanish-origin answers take precedence over Latino race mentions when that question is asked.

For the 1994–1996 wife Spanish-origin variables ER3880, ER6750, and ER8996, the captured codebook describes 0 only as no wife in the family unit. It supplies no non-Hispanic meaning for a present wife. Such reports have `hispanic=None` and `hispanic_basis="undocumented_zero_meaning"`; documentation frequencies are never used to infer an omitted meaning.

Static race/ethnicity uses the most recent complete head/spouse report in the full window; Hispanic reports are complete regardless of race, while non-Hispanic reports need a known full race set. Conflicts remain visible in report and distinct-reading counts. If no complete report exists, the latest known Hispanic-origin answer is retained separately. Nativity uses the latest classifiable 2013–2023 report. Sources after an anchor are explicitly counted; no modal fallback or imputation is used.

Education uses the latest known individual-file answer at or before `max(anchor_waves)`, including OFUMs aged 16 or older. Codes 1–16 give completed grades and 17 means at least some postgraduate work. Individual code 0 is Inap.; it establishes zero years only when a present head/spouse also has the family completed-education recode 0, whose text explicitly documents completed no grades. Otherwise it remains inapplicable. Missing and undocumented codes remain distinct.

Nativity is first available for both roles in 2013. The state/year-came pair identifies a U.S. state when state is 1–56 and year-came is 0, a U.S. territory when both codes are 0, and a foreign country when state is 0 and year-came records a year or an applicable nonzero response. Inconsistent skip pairs and unknown reports do not decide birthplace. U.S. territory births remain unresolved in MINT because the guide does not define their placement. Earlier immigrant-supplement and grew-up items are not substituted.

Each selected variable must match its exact whitespace-normalized SPSS label. Every observed code must belong to its captured codebook or SAS-format domain. Invalid integer types, undocumented codes, ambiguous label changes, duplicate role joins, missing family rows, and changed pinned documentation are refused.

The pure builder enforces the same wave-specific education and family-item domains on supplied frames, including source role and question availability. The reader partitions the long individual roster once by wave before selecting head/spouse rows; an independent synthetic row-join oracle checks that this preserves the earlier whole-frame selection semantics.

## Schemes and lifetime dimensions

`group_category_schemes_v1.json` records MINT four-way race/ethnicity and five education bands, report four-way race/ethnicity, and unresolved report education definitions. The cleared exercise-2 definitions extract (SHA-256 `a3978b683b4275424b6d12e9fe45f021fae277ccf9731a7883952564b6ed0384`) gives race rows at lines 58/86, education rows at 59/87, and labor-force rows at 60/88. Line 229 defines Other as other minority groups, including Asian and Native American people. Lines 231 and 327 explicitly leave education and labor-force definitions open: `report_education_mapping` and `report_labor_force_experience` remain unavailable pending registration, with no inferred schooling boundaries or positive-earnings-years substitute. Report multiracial, Hispanic precedence and residual Other assignments are named builder conventions. The canonical MINT guide is certified 2026-04-01. The MINT convention placing non-Hispanic multiple-race reports in All other races is an explicit builder assumption pending registration. Alternate report schemes can replace this rule without changing the reader.

Lifetime measures (initial AIME at 62 and lifetime payroll-tax present values, own and shared) live in `estimates/lifetime_measures.py`, documented in `docs/design/lifetime_measures.md`. This package supplies only the person attributes and the category schemes those measures are tabulated under.

## Provenance and source pins

`load_group_attribute_inputs` performs all PSID reads inside the cohort file-audit context. Provenance seals the opened files, raw input frames, requested identifiers, schemes, and final attribute frame with SHA-256. Frozen wrappers carry the frames; builders verify recorded input seals, and lifetime quintile assignment refuses a changed frame. Label/codebook inspection and captured-domain regeneration read documentation only. No restricted comparator, policy-option data table, Urban results source, or outcome was read for this package.

| Capture | SHA-256 | Locator |
|---|---|---|
| `data/external/psid_group_attribute_codebook_values_v1.json` | `09fce5627b0271a68eadb2e8748e33fe1ff3e6b0e025bfef9575bb2804ebef63` | Per-wave family variable, exact label, one-based PDF page and value table; documentation counts removed |
| `data/external/group_category_schemes_v1.json` | `243833aa0fa1cca8968df4b8e93753d92e77beeee8939f3782310812a3016797` | Per-scheme categories, education bands, explicit assumptions and unresolved definitions |
| `data/external/mint8_table_user_guide.source.html` | `8d5bc3f0de17831c2ed07383003257a63bb657df179d0c54868fda052f23f100` | Definitions—Table Rows and Columns > Characteristic Subgroups—Table Rows |
| `data/external/mint8_row_categories.json` | `23fbfbc8dbc14b06144a83bf0583ea0a6c89505638f3f7dc5fd6b34a3a4ac650` | Tables 1–3 (benefits), 7–9 (household income), 10–12 (official poverty), 13–16 (benefit/tax ratio), and 17–20 (initial replacement rate): captions and row labels only; no data cells. |

The source paths below are relative to the staged PSID root. Each family inventory row gives the one-based PDF page locating that variable; the captured JSON preserves exact value/range texts. Family SAS formats, when captured, have an additional SHA-256 pin in that JSON. Individual domains and role descriptions are verified in `IND2023ER_formats.sas`, with its actual file SHA-256 included in the runtime file audit.

| Wave | Family codebook source | PDF SHA-256 |
|---|---|---|
| 1985 | `family/1985/FAM1985_codebook.pdf` | `ef9cdf2eafccf167b5ab0495cab085877dce4787ccb9a2c01fdf4a868d13909a` |
| 1986 | `family/1986/FAM1986_codebook.pdf` | `6483a31953e3f969b8757c97779ff6f2c45734b54a2806e8fd506db72c220112` |
| 1987 | `family/1987/FAM1987_codebook.pdf` | `86065d5cb127766a27037735ee428d1cec5afeeac554bfc9cc2cabfebd300056` |
| 1988 | `family/1988/FAM1988_codebook.pdf` | `4e2a75c05ee4b2ca9d44a31063096567f45c97285127a124d2d98a913f772c8f` |
| 1989 | `family/1989/FAM1989_codebook.pdf` | `1dff0473a8df0b7564f1716fd01ef67d276920105d17a986f6f167de5e1a049a` |
| 1990 | `family/1990/FAM1990_codebook.pdf` | `4e6e0d3c22eedc50137b3d8a8b33e949064681b5bf42275d51da4b349734b32f` |
| 1991 | `family/1991/FAM1991_codebook.pdf` | `cb25d86256acb143cbc7b6f400702dc6a20787af9476dfbe9fc277ccecca424c` |
| 1992 | `family/1992/FAM1992_codebook.pdf` | `249b4c1a9a333792df66511c4fc63ae2ac51a28bb764f38aff4bc04a6d389d52` |
| 1993 | `family/1993/fam1993_codebook.pdf` | `a4659bad3b0d2a4ec0040f9ad63994060d1d98c5924327853dfc7899ac172411` |
| 1994 | `family/1994/FAM1994ER_codebook_public.pdf` | `ecf8667f3b6d2a5ac7e312ecd9761a00ae7c1d2db6bee2f8af049e495ff1cf56` |
| 1995 | `family/1995/FAM1995ER_codebook_public.pdf` | `c4a161e935244487d26d7a581ff68b1c7f844c8032fe756eda82c035f51cb985` |
| 1996 | `family/1996/FAM1996ER_codebook_public.pdf` | `aa52222228e4ecc3d7309c39c61929a7603951615c6a80b3ba3423e7f3ba8300` |
| 1997 | `family/1997/FAM1997ER_codebook_public.pdf` | `9716779d9b1102fb5be611e620525759a6cb8676714ba9722a34da8c7287bb3d` |
| 1999 | `family/1999/FAM1999ER_codebook.pdf` | `5accefc4c1b50b3447b1a674ac2750de94568c538873f9bab34c2049c80c6107` |
| 2001 | `family/2001/FAM2001ER_codebook.pdf` | `13ae45ce24125c2ac30c15e62f1efeddc7842dc924b3415fe5aaa058666029a0` |
| 2003 | `family/2003/FAM2003ER_codebook.pdf` | `5a69ee0e605aec1305a23931330da97d75dd21c32d183b8d67c3b6597f23a201` |
| 2005 | `family/2005/FAM2005ER_codebook.pdf` | `eec8de3c04ac88ffce0495622f0cbe0ac621780b201ce6bd0b4b54344a3a6243` |
| 2007 | `family/2007/FAM2007ER_codebook.pdf` | `d92bc05151cf1b77513e4520578402305d356a669c7998f10f91ad48ac66c89e` |
| 2009 | `family/2009/FAM2009ER_codebook.pdf` | `2639c0cad9d5b6e1a08eae57c578d9698a249ed331475b79df525a0caa7c4c6b` |
| 2011 | `family/2011/FAM2011ER_codebook.pdf` | `00c0517569b94efcc7fc6594529a263feb9e3bb9a88efff3becf5b8aaeebdd3c` |
| 2013 | `family/2013/FAM2013ER_codebook.pdf` | `40cc2de6af801b94b93518f7252e24c7c95098e713fc97f9ead1af74c4ce25d6` |
| 2015 | `family/2015/FAM2015ER_codebook.pdf` | `7dcb71f823e309a286b904531410243d58cde48b8f50079401856de9ac762238` |
| 2017 | `family/2017/FAM2017ER_codebook.pdf` | `19bfba9f7a3fecc82a18711466e2b2a5f00b49c9d3db0f9f8587795fad2bf8c1` |
| 2019 | `family/2019/fam2019er_codebook.pdf` | `ce637e37e0f5e306dd7f10455e85069b56c9b13d5c138d3eb4b9c8d6a8452406` |
| 2021 | `family/2021/FAM2021ER_codebook.pdf` | `e3b88ef394952fa05b9b98eb7f05bf9a99896840515942562aa37399e1bcd462` |
| 2023 | `family/2023/FAM2023ER_codebook.pdf` | `85a4078ebb79146d023df3d9d4e2d2ef6017eced849656ca39f4b740cb5a5688` |

## Public API

```python
load_group_attributes(person_ids: Iterable[int], *, anchor_waves: Iterable[int],
                      psid_dir: Path | None = None) -> GroupAttributes
load_group_attribute_inputs(*, psid_dir: Path | None = None) -> GroupAttributeInputs
build_group_attributes(inputs: GroupAttributeInputs, person_ids: Iterable[int], *,
                       anchor_waves: Iterable[int],
                       schemes: Mapping[str, Any] | None = None) -> GroupAttributes
```

`GroupAttributes(frame, provenance)` supplies the required scheme columns plus source wave, role, variables, mentions, conflict counts, and availability reasons. `GroupAttributeInputs(reports, education, universe, provenance)` supports pure synthetic or previously audited inputs. Join side frames by `person_id`; age-67 observations may legitimately repeat a person.

## Tests and integration follow-ups

| Test module | Tier | Coverage |
|---|---|---|
| `tests/data/test_group_attributes_psid.py` | artifact | INVENTED fixed-width products; exact labels; domains; role joins; ambiguous and unknown answers; education/nativity properties; differential domain representations; captured table identity; codebook extraction and documentation pins |
| `tests/cohorts/test_group_attributes.py` | artifact | Synthetic resolution, conflicts, unknown preservation, joins, anchor education cutoff, seals and property tests; reads committed schemes |
| `tests/cohorts/test_group_category_schemes.py` | artifact | Captured source/label identity and scheme mappings, unresolved definitions, boundaries and property tests |
| `tests/cohorts/test_group_attributes_integration.py` | integration_psid | Staged labels, domains, pins and coverage for 2009/2011 cohorts, age-67 observations and Track M 2023; skips when sources are absent |

Run only targeted tests with the main venv and one pytest process at a time. Host integration checks availability totals and identifier coverage only; it computes no policy outcome or distribution by group. A later #42 registration is required before any real group breakdown. The integrator must update `tests/tier_counts.json` and the source-exclusion/artifact-test inventory in `scripts/first_estimates_birth_evidence.py` and `tests/estimates/test_birth_evidence_artifact.py`; G1 does not edit those shared files or `pyproject.toml`.

## Validation in the assigned workspace

All pytest commands used `PYTHONPATH=src /Users/maxghenis/PolicyEngine/microcosm-dynamics/.venv/bin/python -m pytest`, with one process at a time:

| Arguments | Result |
|---|---|
| `tests/data/test_group_attributes_psid.py tests/cohorts/test_group_attributes.py tests/cohorts/test_group_category_schemes.py -q -x` | 151 passed in 358.48 seconds before final validation/performance additions |
| `tests/cohorts/test_group_attributes.py -q` | Final: 73 passed in 1425.64 seconds |
| `tests/data/test_group_attributes_psid.py -q` | Final: 39 passed in 386.66 seconds |
| `tests/cohorts/test_group_attributes.py tests/cohorts/test_group_attributes_integration.py -q -x` | Interrupted after 8296.62 seconds to limit shared-host load; 48 synthetic cases passed, no host population case completed |

The final unchanged scheme/lifetime tests and final cohort/reader tests account for 183 distinct passing synthetic cases. Black at 79 columns and Ruff passed for all nine Python files, including rechecks after the final source/test edits. The captured codebook table regenerated exactly from staged documentation. Host population coverage remains unverified; no outcome or group-share pipeline was run.

The branch remains `nasi/g1-group-attributes` at `75cd35245f1a0c12e7a23b048a7d126c74ad8ecb`. All package files remain uncommitted: Git staging was denied when creating `/Users/maxghenis/PolicyEngine/microcosm-dynamics/.git/worktrees/nasi-g1/index.lock`, which lies outside the writable workspace. Existing tracked files were preserved. Nothing was pushed and no PR was opened.

## Exact individual-file inventory

All variables below are in `ind2023er/IND2023ER.sps`; every label was verified against the staged file. Wave-independent identifiers are ER30001 — 1968 INTERVIEW NUMBER and ER30002 — PERSON NUMBER 68. Sequence and relationship domains come from the assigned SAS VALUE blocks; education domains have their wave-specific DK/NA codes.

| Wave | Item | Variable | Exact SPSS label |
|---|---|---|---|
| 1985 | interview | `ER30463` | 1985 INTERVIEW NUMBER |
| 1985 | sequence | `ER30464` | SEQUENCE NUMBER 85 |
| 1985 | relationship | `ER30465` | RELATIONSHIP TO HEAD 85 |
| 1985 | education | `ER30478` | COMPLETED EDUCATION 85 |
| 1986 | interview | `ER30498` | 1986 INTERVIEW NUMBER |
| 1986 | sequence | `ER30499` | SEQUENCE NUMBER 86 |
| 1986 | relationship | `ER30500` | RELATIONSHIP TO HEAD 86 |
| 1986 | education | `ER30513` | COMPLETED EDUCATION 86 |
| 1987 | interview | `ER30535` | 1987 INTERVIEW NUMBER |
| 1987 | sequence | `ER30536` | SEQUENCE NUMBER 87 |
| 1987 | relationship | `ER30537` | RELATIONSHIP TO HEAD 87 |
| 1987 | education | `ER30549` | COMPLETED EDUCATION 87 |
| 1988 | interview | `ER30570` | 1988 INTERVIEW NUMBER |
| 1988 | sequence | `ER30571` | SEQUENCE NUMBER 88 |
| 1988 | relationship | `ER30572` | RELATION TO HEAD 88 |
| 1988 | education | `ER30584` | COMPLETED EDUC-IND 88 |
| 1989 | interview | `ER30606` | 1989 INTERVIEW NUMBER |
| 1989 | sequence | `ER30607` | SEQUENCE NUMBER 89 |
| 1989 | relationship | `ER30608` | RELATION TO HEAD 89 |
| 1989 | education | `ER30620` | COMPLETED EDUC-IND 89 |
| 1990 | interview | `ER30642` | 1990 INTERVIEW NUMBER |
| 1990 | sequence | `ER30643` | SEQUENCE NUMBER 90 |
| 1990 | relationship | `ER30644` | RELATION TO HEAD 90 |
| 1990 | education | `ER30657` | COMPLETED EDUC-IND 90 |
| 1991 | interview | `ER30689` | 1991 INTERVIEW NUMBER |
| 1991 | sequence | `ER30690` | SEQUENCE NUMBER 91 |
| 1991 | relationship | `ER30691` | RELATION TO HEAD 91 |
| 1991 | education | `ER30703` | COMPLETED EDUC-IND 91 |
| 1992 | interview | `ER30733` | 1992 INTERVIEW NUMBER |
| 1992 | sequence | `ER30734` | SEQUENCE NUMBER 92 |
| 1992 | relationship | `ER30735` | RELATION TO HEAD 92 |
| 1992 | education | `ER30748` | COMPLETED EDUCATION 92 |
| 1993 | interview | `ER30806` | 1993 INTERVIEW NUMBER |
| 1993 | sequence | `ER30807` | SEQUENCE NUMBER 93 |
| 1993 | relationship | `ER30808` | RELATION TO HEAD 93 |
| 1993 | education | `ER30820` | YRS COMPLETED EDUCATION 93 |
| 1994 | interview | `ER33101` | 1994 INTERVIEW NUMBER |
| 1994 | sequence | `ER33102` | SEQUENCE NUMBER 94 |
| 1994 | relationship | `ER33103` | RELATION TO HEAD 94 |
| 1994 | education | `ER33115` | YRS COMPLETED EDUC 94 |
| 1995 | interview | `ER33201` | 1995 INTERVIEW NUMBER |
| 1995 | sequence | `ER33202` | SEQUENCE NUMBER 95 |
| 1995 | relationship | `ER33203` | RELATION TO HEAD 95 |
| 1995 | education | `ER33215` | YEARS COMPLETED EDUCATION 95 |
| 1996 | interview | `ER33301` | 1996 INTERVIEW NUMBER |
| 1996 | sequence | `ER33302` | SEQUENCE NUMBER 96 |
| 1996 | relationship | `ER33303` | RELATION TO HEAD 96 |
| 1996 | education | `ER33315` | YEARS COMPLETED EDUCATION 96 |
| 1997 | interview | `ER33401` | 1997 INTERVIEW NUMBER |
| 1997 | sequence | `ER33402` | SEQUENCE NUMBER 97 |
| 1997 | relationship | `ER33403` | RELATION TO HEAD 97 |
| 1997 | education | `ER33415` | YEARS COMPLETED EDUCATION 97 |
| 1999 | interview | `ER33501` | 1999 INTERVIEW NUMBER |
| 1999 | sequence | `ER33502` | SEQUENCE NUMBER 99 |
| 1999 | relationship | `ER33503` | RELATION TO HEAD 99 |
| 1999 | education | `ER33516` | YEARS COMPLETED EDUCATION 99 |
| 2001 | interview | `ER33601` | 2001 INTERVIEW NUMBER |
| 2001 | sequence | `ER33602` | SEQUENCE NUMBER 01 |
| 2001 | relationship | `ER33603` | RELATION TO HEAD 01 |
| 2001 | education | `ER33616` | YEARS COMPLETED EDUCATION 01 |
| 2003 | interview | `ER33701` | 2003 INTERVIEW NUMBER |
| 2003 | sequence | `ER33702` | SEQUENCE NUMBER 03 |
| 2003 | relationship | `ER33703` | RELATION TO HEAD 03 |
| 2003 | education | `ER33716` | YEARS COMPLETED EDUCATION 03 |
| 2005 | interview | `ER33801` | 2005 INTERVIEW NUMBER |
| 2005 | sequence | `ER33802` | SEQUENCE NUMBER 05 |
| 2005 | relationship | `ER33803` | RELATION TO HEAD 05 |
| 2005 | education | `ER33817` | YEARS COMPLETED EDUCATION 05 |
| 2007 | interview | `ER33901` | 2007 INTERVIEW NUMBER |
| 2007 | sequence | `ER33902` | SEQUENCE NUMBER 07 |
| 2007 | relationship | `ER33903` | RELATION TO HEAD 07 |
| 2007 | education | `ER33917` | YEARS COMPLETED EDUCATION 07 |
| 2009 | interview | `ER34001` | 2009 INTERVIEW NUMBER |
| 2009 | sequence | `ER34002` | SEQUENCE NUMBER 09 |
| 2009 | relationship | `ER34003` | RELATION TO HEAD 09 |
| 2009 | education | `ER34020` | YEARS COMPLETED EDUCATION 09 |
| 2011 | interview | `ER34101` | 2011 INTERVIEW NUMBER |
| 2011 | sequence | `ER34102` | SEQUENCE NUMBER 11 |
| 2011 | relationship | `ER34103` | RELATION TO HEAD 11 |
| 2011 | education | `ER34119` | YEARS COMPLETED EDUCATION 11 |
| 2013 | interview | `ER34201` | 2013 INTERVIEW NUMBER |
| 2013 | sequence | `ER34202` | SEQUENCE NUMBER 13 |
| 2013 | relationship | `ER34203` | RELATION TO HEAD 13 |
| 2013 | education | `ER34230` | YEARS COMPLETED EDUCATION 13 |
| 2015 | interview | `ER34301` | 2015 INTERVIEW NUMBER |
| 2015 | sequence | `ER34302` | SEQUENCE NUMBER 15 |
| 2015 | relationship | `ER34303` | RELATION TO HEAD 15 |
| 2015 | education | `ER34349` | YEARS COMPLETED EDUCATION 15 |
| 2017 | interview | `ER34501` | 2017 INTERVIEW NUMBER |
| 2017 | sequence | `ER34502` | SEQUENCE NUMBER 17 |
| 2017 | relationship | `ER34503` | RELATION TO REFERENCE PERSON 17 |
| 2017 | education | `ER34548` | YEARS COMPLETED EDUCATION 17 |
| 2019 | interview | `ER34701` | 2019 INTERVIEW NUMBER |
| 2019 | sequence | `ER34702` | SEQUENCE NUMBER 19 |
| 2019 | relationship | `ER34703` | RELATION TO REFERENCE PERSON 19 |
| 2019 | education | `ER34752` | YEARS COMPLETED EDUCATION 19 |
| 2021 | interview | `ER34901` | 2021 INTERVIEW NUMBER |
| 2021 | sequence | `ER34902` | SEQUENCE NUMBER 21 |
| 2021 | relationship | `ER34903` | RELATION TO REFERENCE PERSON 21 |
| 2021 | education | `ER34952` | YEARS COMPLETED EDUCATION 21 |
| 2023 | interview | `ER35101` | 2023 INTERVIEW NUMBER |
| 2023 | sequence | `ER35102` | SEQUENCE NUMBER 23 |
| 2023 | relationship | `ER35103` | RELATION TO REFERENCE PERSON 23 |
| 2023 | education | `ER35152` | YEARS COMPLETED EDUCATION 23 |

## Exact family-file inventory

Wave directories are `family/<wave>/`; interview numbers join the individual roster to family records. Race mention numbers are one-based and preserve question order. Missing items in a wave are genuinely unasked and are not filled with another variable. Every listed label was verified against its staged SPSS setup file.

| Wave | Role | Item | Variable | Exact SPSS label | PDF page |
|---|---|---|---|---|---|
| 1985 | family | interview | `V11102` | 1985 INTERVIEW NUMBER | — |
| 1985 | head | hispanic | `V11937` | G31 SPANISH DESCENT-HEAD | 277 |
| 1985 | head | race mention 1 | `V11938` | G32 RACE OF HEAD (1 MEN) | 277 |
| 1985 | head | race mention 2 | `V11939` | G32 RACE OF HEAD (2 MEN) | 278 |
| 1985 | spouse | hispanic | `V12292` | N31 SPANISH DESCENT-WIFE | 413 |
| 1985 | spouse | race mention 1 | `V12293` | N32 RACE OF WIFE (1 MEN) | 413 |
| 1985 | spouse | race mention 2 | `V12294` | N32 RACE OF WIFE (2 MEN) | 414 |
| 1986 | family | interview | `V12502` | 1986 INTERVIEW NUMBER | — |
| 1986 | head | hispanic | `V13564` | L31 SPANISH DESCENT HD | 376 |
| 1986 | head | race mention 1 | `V13565` | L32 RACE OF HEAD 1 | 376 |
| 1986 | head | race mention 2 | `V13566` | L32 RACE OF HEAD 2 | 377 |
| 1986 | spouse | hispanic | `V13499` | K18 SPANISH DESCENT WF | 344 |
| 1986 | spouse | race mention 1 | `V13500` | K19 RACE OF WIFE 1 | 345 |
| 1986 | spouse | race mention 2 | `V13501` | K19 RACE OF WIFE 2 | 345 |
| 1987 | family | interview | `V13702` | 1987 INTERVIEW NUMBER | — |
| 1987 | head | hispanic | `V14611` | L31 SPANISH DESCENT HD | 326 |
| 1987 | head | race mention 1 | `V14612` | L32 RACE OF HEAD 1 | 326 |
| 1987 | head | race mention 2 | `V14613` | L32 RACE OF HEAD 2 | 327 |
| 1987 | spouse | hispanic | `V14546` | K18 SPANISH DESCENT WF | 296 |
| 1987 | spouse | race mention 1 | `V14547` | K19 RACE OF WIFE 1 | 296 |
| 1987 | spouse | race mention 2 | `V14548` | K19 RACE OF WIFE 2 | 297 |
| 1988 | family | interview | `V14802` | 1988 INTERVIEW NUMBER | — |
| 1988 | head | hispanic | `V16085` | L31 SPANISH DESCENT HD | 437 |
| 1988 | head | race mention 1 | `V16086` | L32 RACE OF HEAD 1 | 438 |
| 1988 | head | race mention 2 | `V16087` | L32 RACE OF HEAD 2 | 438 |
| 1988 | spouse | hispanic | `V16020` | K18 SPANISH DESCENT WF | 406 |
| 1988 | spouse | race mention 1 | `V16021` | K19 RACE OF WIFE 1 | 406 |
| 1988 | spouse | race mention 2 | `V16022` | K19 RACE OF WIFE 2 | 407 |
| 1989 | family | interview | `V16302` | 1989 INTERVIEW NUMBER | — |
| 1989 | head | hispanic | `V17482` | L31 SPANISH DESCENT HD | 389 |
| 1989 | head | race mention 1 | `V17483` | L32 RACE OF HEAD 1 | 389 |
| 1989 | head | race mention 2 | `V17484` | L32 RACE OF HEAD 2 | 390 |
| 1989 | spouse | hispanic | `V17417` | K18 SPANISH DESCENT WF | 358 |
| 1989 | spouse | race mention 1 | `V17418` | K19 RACE OF WIFE 1 | 359 |
| 1989 | spouse | race mention 2 | `V17419` | K19 RACE OF WIFE 2 | 359 |
| 1990 | family | interview | `V17702` | 1990 INTERVEW NUMBER | — |
| 1990 | head | hispanic | `V18813` | M31 SPANISH DESCENT HD | 355 |
| 1990 | head | race mention 1 | `V18814` | M32 RACE OF HEAD 1 | 355 |
| 1990 | head | race mention 2 | `V18815` | M32 RACE OF HEAD 2 | 356 |
| 1990 | spouse | hispanic | `V18748` | L18 SPANISH DESCENT WF | 326 |
| 1990 | spouse | race mention 1 | `V18749` | L19 RACE OF WIFE 1 | 327 |
| 1990 | spouse | race mention 2 | `V18750` | L19 RACE OF WIFE 2 | 327 |
| 1991 | family | interview | `V19002` | 1991 INTERVIEW NUMBER | — |
| 1991 | head | hispanic | `V20113` | L31 SPANISH DESCENT HD | 351 |
| 1991 | head | race mention 1 | `V20114` | L32 RACE OF HEAD 1 | 351 |
| 1991 | head | race mention 2 | `V20115` | L32 RACE OF HEAD 2 | 352 |
| 1991 | spouse | hispanic | `V20048` | K18 SPANISH DESCENT WF | 326 |
| 1991 | spouse | race mention 1 | `V20049` | K19 RACE OF WIFE 1 | 327 |
| 1991 | spouse | race mention 2 | `V20050` | K19 RACE OF WIFE 2 | 327 |
| 1992 | family | interview | `V20302` | 1992 INTERVIEW NUMBER | — |
| 1992 | head | hispanic | `V21419` | M31 SPANISH DESCENT HD | 353 |
| 1992 | head | race mention 1 | `V21420` | M32 RACE OF HEAD 1 | 354 |
| 1992 | head | race mention 2 | `V21421` | M32 RACE OF HEAD 2 | 354 |
| 1992 | spouse | hispanic | `V21354` | L18 SPANISH DESCENT WF | 329 |
| 1992 | spouse | race mention 1 | `V21355` | L19 RACE OF WIFE 1 | 329 |
| 1992 | spouse | race mention 2 | `V21356` | L19 RACE OF WIFE 2 | 329 |
| 1993 | family | interview | `V21602` | 1993 INTERVIEW NUMBER | — |
| 1993 | head | hispanic | `V23275` | L31 WTR HD OF SPANISH DESCENT | 432 |
| 1993 | head | race mention 1 | `V23276` | L32 RACE OF HD-1ST MENTION | 432 |
| 1993 | head | race mention 2 | `V23277` | L32 RACE OF HD-2ND MENTION | 433 |
| 1993 | head | completed_education | `V23333` | COMPLETED ED-HD 1993 | 459 |
| 1993 | spouse | hispanic | `V23211` | K18 WTR WF OF SPANISH DESCENT | 409 |
| 1993 | spouse | race mention 1 | `V23212` | K19 RACE OF WF-1ST MENTION | 409 |
| 1993 | spouse | race mention 2 | `V23213` | K19 RACE OF WF-2ND MENTION | 410 |
| 1993 | spouse | completed_education | `V23334` | COMPLETED ED-WF 1993 | 460 |
| 1994 | family | interview | `ER2002` | 1994 INTERVIEW # | — |
| 1994 | head | hispanic | `ER3941` | L31 SPANISH DESCENT 1 HD | 566 |
| 1994 | head | race mention 1 | `ER3944` | L32 RACE OF HEAD 1 | 567 |
| 1994 | head | race mention 2 | `ER3945` | L32 RACE OF HEAD 2 | 568 |
| 1994 | head | race mention 3 | `ER3946` | L32 RACE OF HEAD 3 | 568 |
| 1994 | head | completed_education | `ER4158` | COMPLETED ED-HD | 669 |
| 1994 | spouse | hispanic | `ER3880` | K18 SPANISH DESCENT 1 WF | 545 |
| 1994 | spouse | race mention 1 | `ER3883` | K19 RACE OF WIFE 1 | 546 |
| 1994 | spouse | race mention 2 | `ER3884` | K19 RACE OF WIFE 2 | 546 |
| 1994 | spouse | race mention 3 | `ER3885` | K19 RACE OF WIFE 3 | 547 |
| 1994 | spouse | completed_education | `ER4159` | COMPLETED ED-WF | 669 |
| 1995 | family | interview | `ER5002` | 1995 INTERVIEW # | — |
| 1995 | head | hispanic | `ER6811` | L31 SPANISH DESCENT 1 HD | 517 |
| 1995 | head | race mention 1 | `ER6814` | L32 RACE OF HEAD 1 | 518 |
| 1995 | head | race mention 2 | `ER6815` | L32 RACE OF HEAD 2 | 519 |
| 1995 | head | race mention 3 | `ER6816` | L32 RACE OF HEAD 3 | 519 |
| 1995 | head | completed_education | `ER6998` | COMPLETED ED-HD | 612 |
| 1995 | spouse | hispanic | `ER6750` | K18 SPANISH DESCENT 1 WF | 496 |
| 1995 | spouse | race mention 1 | `ER6753` | K19 RACE OF WIFE 1 | 497 |
| 1995 | spouse | race mention 2 | `ER6754` | K19 RACE OF WIFE 2 | 498 |
| 1995 | spouse | race mention 3 | `ER6755` | K19 RACE OF WIFE 3 | 498 |
| 1995 | spouse | completed_education | `ER6999` | COMPLETED ED-WF | 612 |
| 1996 | family | interview | `ER7002` | 1996 INTERVIEW # | — |
| 1996 | head | hispanic | `ER9057` | L31 SPANISH DESCENT 1 HD | 625 |
| 1996 | head | race mention 1 | `ER9060` | L32 RACE OF HEAD 1 | 626 |
| 1996 | head | race mention 2 | `ER9061` | L32 RACE OF HEAD 2 | 627 |
| 1996 | head | race mention 3 | `ER9062` | L32 RACE OF HEAD 3 | 627 |
| 1996 | head | completed_education | `ER9249` | COMPLETED ED-HD | 719 |
| 1996 | spouse | hispanic | `ER8996` | K18 SPANISH DESCENT 1 WF | 604 |
| 1996 | spouse | race mention 1 | `ER8999` | K19 RACE OF WIFE 1 | 605 |
| 1996 | spouse | race mention 2 | `ER9000` | K19 RACE OF WIFE 2 | 605 |
| 1996 | spouse | race mention 3 | `ER9001` | K19 RACE OF WIFE 3 | 606 |
| 1996 | spouse | completed_education | `ER9250` | COMPLETED ED-WF | 720 |
| 1997 | family | interview | `ER10002` | 1997 INTERVIEW # | — |
| 1997 | head | race mention 1 | `ER11848` | L40/95 RACE OF HEAD 1 | 504 |
| 1997 | head | race mention 2 | `ER11849` | L40/95 RACE OF HEAD 2 | 504 |
| 1997 | head | race mention 3 | `ER11850` | L40/95 RACE OF HEAD 3 | 504 |
| 1997 | head | race mention 4 | `ER11851` | L40/95 RACE OF HEAD 4 | 505 |
| 1997 | head | completed_education | `ER12222` | COMPLETED ED-HD | 660 |
| 1997 | spouse | race mention 1 | `ER11760` | K34/87 RACE OF WIFE 1 | 470 |
| 1997 | spouse | race mention 2 | `ER11761` | K34/87 RACE OF WIFE 2 | 471 |
| 1997 | spouse | race mention 3 | `ER11762` | K34/87 RACE OF WIFE 3 | 471 |
| 1997 | spouse | race mention 4 | `ER11763` | K34/87 RACE OF WIFE 4 | 471 |
| 1997 | spouse | completed_education | `ER12223` | COMPLETED ED-WF | 660 |
| 1999 | family | interview | `ER13002` | 1999 FAMILY INTERVIEW (ID) NUMBER | — |
| 1999 | head | race mention 1 | `ER15928` | L40/95 RACE OF HEAD 1 | 858 |
| 1999 | head | race mention 2 | `ER15929` | L40/95 RACE OF HEAD 2 | 858 |
| 1999 | head | race mention 3 | `ER15930` | L40/95 RACE OF HEAD 3 | 858 |
| 1999 | head | race mention 4 | `ER15931` | L40/95 RACE OF HEAD 4 | 859 |
| 1999 | head | completed_education | `ER16516` | COMPLETED ED-HD | 1079 |
| 1999 | spouse | race mention 1 | `ER15836` | K34/87 RACE OF WIFE 1 | 818 |
| 1999 | spouse | race mention 2 | `ER15837` | K34/87 RACE OF WIFE 2 | 819 |
| 1999 | spouse | race mention 3 | `ER15838` | K34/87 RACE OF WIFE 3 | 819 |
| 1999 | spouse | race mention 4 | `ER15839` | K34/87 RACE OF WIFE 4 | 819 |
| 1999 | spouse | completed_education | `ER16517` | COMPLETED ED-WF | 1079 |
| 2001 | family | interview | `ER17002` | 2001 FAMILY INTERVIEW (ID) NUMBER | — |
| 2001 | head | race mention 1 | `ER19989` | L40/95 RACE OF HEAD 1 | 860 |
| 2001 | head | race mention 2 | `ER19990` | L40/95 RACE OF HEAD 2 | 861 |
| 2001 | head | race mention 3 | `ER19991` | L40/95 RACE OF HEAD 3 | 861 |
| 2001 | head | race mention 4 | `ER19992` | L40/95 RACE OF HEAD 4 | 862 |
| 2001 | head | completed_education | `ER20457` | COMPLETED ED-HD | 1037 |
| 2001 | spouse | race mention 1 | `ER19897` | K34/87 RACE OF WIFE 1 | 821 |
| 2001 | spouse | race mention 2 | `ER19898` | K34/87 RACE OF WIFE 2 | 822 |
| 2001 | spouse | race mention 3 | `ER19899` | K34/87 RACE OF WIFE 3 | 822 |
| 2001 | spouse | race mention 4 | `ER19900` | K34/87 RACE OF WIFE 4 | 822 |
| 2001 | spouse | completed_education | `ER20458` | COMPLETED ED-WF | 1038 |
| 2003 | family | interview | `ER21002` | 2003 FAMILY INTERVIEW (ID) NUMBER | — |
| 2003 | head | race mention 1 | `ER23426` | L40/95 RACE OF HEAD 1 | 714 |
| 2003 | head | race mention 2 | `ER23427` | L40/95 RACE OF HEAD 2 | 714 |
| 2003 | head | race mention 3 | `ER23428` | L40/95 RACE OF HEAD 3 | 714 |
| 2003 | head | race mention 4 | `ER23429` | L40/95 RACE OF HEAD 4 | 715 |
| 2003 | head | completed_education | `ER24148` | COMPLETED ED-HD | 1004 |
| 2003 | spouse | race mention 1 | `ER23334` | K34/87 RACE OF WIFE 1 | 673 |
| 2003 | spouse | race mention 2 | `ER23335` | K34/87 RACE OF WIFE 2 | 674 |
| 2003 | spouse | race mention 3 | `ER23336` | K34/87 RACE OF WIFE 3 | 674 |
| 2003 | spouse | race mention 4 | `ER23337` | K34/87 RACE OF WIFE 4 | 674 |
| 2003 | spouse | completed_education | `ER24149` | COMPLETED ED-WF | 1005 |
| 2005 | family | interview | `ER25002` | 2005 FAMILY INTERVIEW (ID) NUMBER | — |
| 2005 | head | hispanic | `ER27392` | L39A SPANISH DESCENT-HEAD | 708 |
| 2005 | head | race mention 1 | `ER27393` | L40 RACE OF HEAD-MENTION 1 | 708 |
| 2005 | head | race mention 2 | `ER27394` | L40 RACE OF HEAD-MENTION 2 | 708 |
| 2005 | head | race mention 3 | `ER27395` | L40 RACE OF HEAD-MENTION 3 | 709 |
| 2005 | head | race mention 4 | `ER27396` | L40 RACE OF HEAD-MENTION 4 | 709 |
| 2005 | head | completed_education | `ER28047` | COMPLETED ED-HD | 961 |
| 2005 | spouse | hispanic | `ER27296` | K33A SPANISH DESCENT-WIFE | 665 |
| 2005 | spouse | race mention 1 | `ER27297` | K34 RACE OF WIFE-MENTION 1 | 666 |
| 2005 | spouse | race mention 2 | `ER27298` | K34 RACE OF WIFE-MENTION 2 | 666 |
| 2005 | spouse | race mention 3 | `ER27299` | K34 RACE OF WIFE-MENTION 3 | 666 |
| 2005 | spouse | race mention 4 | `ER27300` | K34 RACE OF WIFE-MENTION 4 | 667 |
| 2005 | spouse | completed_education | `ER28048` | COMPLETED ED-WF | 962 |
| 2007 | family | interview | `ER36002` | 2007 FAMILY INTERVIEW (ID) NUMBER | — |
| 2007 | head | hispanic | `ER40564` | L39 SPANISH DESCENT-HEAD | 1399 |
| 2007 | head | race mention 1 | `ER40565` | L40 RACE OF HEAD-MENTION 1 | 1399 |
| 2007 | head | race mention 2 | `ER40566` | L40 RACE OF HEAD-MENTION 2 | 1399 |
| 2007 | head | race mention 3 | `ER40567` | L40 RACE OF HEAD-MENTION 3 | 1400 |
| 2007 | head | race mention 4 | `ER40568` | L40 RACE OF HEAD-MENTION 4 | 1400 |
| 2007 | head | completed_education | `ER41037` | COMPLETED ED-HD | 1590 |
| 2007 | spouse | hispanic | `ER40471` | K39 SPANISH DESCENT-WIFE | 1357 |
| 2007 | spouse | race mention 1 | `ER40472` | K40 RACE OF WIFE-MENTION 1 | 1358 |
| 2007 | spouse | race mention 2 | `ER40473` | K40 RACE OF WIFE-MENTION 2 | 1358 |
| 2007 | spouse | race mention 3 | `ER40474` | K40 RACE OF WIFE-MENTION 3 | 1358 |
| 2007 | spouse | race mention 4 | `ER40475` | K40 RACE OF WIFE-MENTION 4 | 1359 |
| 2007 | spouse | completed_education | `ER41038` | COMPLETED ED-WF | 1591 |
| 2009 | family | interview | `ER42002` | 2009 FAMILY INTERVIEW (ID) NUMBER | — |
| 2009 | head | hispanic | `ER46542` | L39 SPANISH DESCENT-HEAD | 1500 |
| 2009 | head | race mention 1 | `ER46543` | L40 RACE OF HEAD-MENTION 1 | 1501 |
| 2009 | head | race mention 2 | `ER46544` | L40 RACE OF HEAD-MENTION 2 | 1501 |
| 2009 | head | race mention 3 | `ER46545` | L40 RACE OF HEAD-MENTION 3 | 1501 |
| 2009 | head | race mention 4 | `ER46546` | L40 RACE OF HEAD-MENTION 4 | 1502 |
| 2009 | head | completed_education | `ER46981` | COMPLETED ED-HD | 1671 |
| 2009 | spouse | hispanic | `ER46448` | K39 SPANISH DESCENT-WIFE | 1458 |
| 2009 | spouse | race mention 1 | `ER46449` | K40 RACE OF WIFE-MENTION 1 | 1459 |
| 2009 | spouse | race mention 2 | `ER46450` | K40 RACE OF WIFE-MENTION 2 | 1459 |
| 2009 | spouse | race mention 3 | `ER46451` | K40 RACE OF WIFE-MENTION 3 | 1459 |
| 2009 | spouse | race mention 4 | `ER46452` | K40 RACE OF WIFE-MENTION 4 | 1460 |
| 2009 | spouse | completed_education | `ER46982` | COMPLETED ED-WF | 1672 |
| 2011 | family | interview | `ER47302` | 2011 FAMILY INTERVIEW (ID) NUMBER | — |
| 2011 | head | hispanic | `ER51903` | L39 SPANISH DESCENT-HEAD | 1655 |
| 2011 | head | race mention 1 | `ER51904` | L40 RACE OF HEAD-MENTION 1 | 1655 |
| 2011 | head | race mention 2 | `ER51905` | L40 RACE OF HEAD-MENTION 2 | 1656 |
| 2011 | head | race mention 3 | `ER51906` | L40 RACE OF HEAD-MENTION 3 | 1656 |
| 2011 | head | race mention 4 | `ER51907` | L40 RACE OF HEAD-MENTION 4 | 1656 |
| 2011 | head | completed_education | `ER52405` | COMPLETED ED-HD | 1861 |
| 2011 | spouse | hispanic | `ER51809` | K39 SPANISH DESCENT-WIFE | 1610 |
| 2011 | spouse | race mention 1 | `ER51810` | K40 RACE OF WIFE-MENTION 1 | 1610 |
| 2011 | spouse | race mention 2 | `ER51811` | K40 RACE OF WIFE-MENTION 2 | 1611 |
| 2011 | spouse | race mention 3 | `ER51812` | K40 RACE OF WIFE-MENTION 3 | 1611 |
| 2011 | spouse | race mention 4 | `ER51813` | K40 RACE OF WIFE-MENTION 4 | 1611 |
| 2011 | spouse | completed_education | `ER52406` | COMPLETED ED-WF | 1862 |
| 2013 | family | interview | `ER53002` | 2013 FAMILY INTERVIEW (ID) NUMBER | — |
| 2013 | head | hispanic | `ER57658` | L39 SPANISH DESCENT-HEAD | 1677 |
| 2013 | head | race mention 1 | `ER57659` | L40 RACE OF HEAD-MENTION 1 | 1677 |
| 2013 | head | race mention 2 | `ER57660` | L40 RACE OF HEAD-MENTION 2 | 1678 |
| 2013 | head | race mention 3 | `ER57661` | L40 RACE OF HEAD-MENTION 3 | 1678 |
| 2013 | head | race mention 4 | `ER57662` | L40 RACE OF HEAD-MENTION 4 | 1678 |
| 2013 | head | completed_education | `ER58223` | COMPLETED ED-HD | 1876 |
| 2013 | head | birth_state | `ER57651` | L33 STATE HEAD WAS BORN | 1675 |
| 2013 | head | year_came | `ER57652` | L33YR YEAR CAME TO UNITED STATES-HD | 1675 |
| 2013 | spouse | hispanic | `ER57548` | K39 SPANISH DESCENT-WIFE | 1620 |
| 2013 | spouse | race mention 1 | `ER57549` | K40 RACE OF WIFE-MENTION 1 | 1621 |
| 2013 | spouse | race mention 2 | `ER57550` | K40 RACE OF WIFE-MENTION 2 | 1621 |
| 2013 | spouse | race mention 3 | `ER57551` | K40 RACE OF WIFE-MENTION 3 | 1621 |
| 2013 | spouse | race mention 4 | `ER57552` | K40 RACE OF WIFE-MENTION 4 | 1622 |
| 2013 | spouse | completed_education | `ER58224` | COMPLETED ED-WF | 1877 |
| 2013 | spouse | birth_state | `ER57541` | K33 STATE WIFE WAS BORN | 1618 |
| 2013 | spouse | year_came | `ER57542` | K33YR YEAR CAME TO UNITED STATES-WF | 1619 |
| 2015 | family | interview | `ER60002` | 2015 FAMILY INTERVIEW (ID) NUMBER | — |
| 2015 | head | hispanic | `ER64809` | L39 SPANISH DESCENT-HEAD | 1771 |
| 2015 | head | race mention 1 | `ER64810` | L40 RACE OF HEAD-MENTION 1 | 1771 |
| 2015 | head | race mention 2 | `ER64811` | L40 RACE OF HEAD-MENTION 2 | 1772 |
| 2015 | head | race mention 3 | `ER64812` | L40 RACE OF HEAD-MENTION 3 | 1772 |
| 2015 | head | race mention 4 | `ER64813` | L40 RACE OF HEAD-MENTION 4 | 1772 |
| 2015 | head | completed_education | `ER65459` | COMPLETED ED-HD | 2017 |
| 2015 | head | birth_state | `ER64802` | L33 STATE HEAD WAS BORN | 1769 |
| 2015 | head | year_came | `ER64803` | L33YR YEAR CAME TO UNITED STATES-HD | 1769 |
| 2015 | spouse | hispanic | `ER64670` | K39 SPANISH DESCENT-SPOUSE | 1679 |
| 2015 | spouse | race mention 1 | `ER64671` | K40 RACE OF SPOUSE-MENTION 1 | 1679 |
| 2015 | spouse | race mention 2 | `ER64672` | K40 RACE OF SPOUSE-MENTION 2 | 1680 |
| 2015 | spouse | race mention 3 | `ER64673` | K40 RACE OF SPOUSE-MENTION 3 | 1680 |
| 2015 | spouse | race mention 4 | `ER64674` | K40 RACE OF SPOUSE-MENTION 4 | 1680 |
| 2015 | spouse | completed_education | `ER65460` | COMPLETED ED-SP | 2018 |
| 2015 | spouse | birth_state | `ER64663` | K33 STATE SPOUSE WAS BORN | 1677 |
| 2015 | spouse | year_came | `ER64664` | K33YR YEAR CAME TO UNITED STATES-SP | 1677 |
| 2017 | family | interview | `ER66002` | 2017 FAMILY INTERVIEW (ID) NUMBER | — |
| 2017 | head | hispanic | `ER70881` | L39 SPANISH DESCENT-RP | 1801 |
| 2017 | head | race mention 1 | `ER70882` | L40 RACE OF REFERENCE PERSON-MENTION 1 | 1802 |
| 2017 | head | race mention 2 | `ER70883` | L40 RACE OF REFERENCE PERSON-MENTION 2 | 1802 |
| 2017 | head | race mention 3 | `ER70884` | L40 RACE OF REFERENCE PERSON-MENTION 3 | 1802 |
| 2017 | head | race mention 4 | `ER70885` | L40 RACE OF REFERENCE PERSON-MENTION 4 | 1803 |
| 2017 | head | completed_education | `ER71538` | COMPLETED ED-RP | 2071 |
| 2017 | head | birth_state | `ER70874` | L33 STATE REFERENCE PERSON WAS BORN | 1799 |
| 2017 | head | year_came | `ER70875` | L33YR YEAR CAME TO UNITED STATES-RP | 1799 |
| 2017 | spouse | hispanic | `ER70743` | K39 SPANISH DESCENT-SPOUSE | 1709 |
| 2017 | spouse | race mention 1 | `ER70744` | K40 RACE OF SPOUSE-MENTION 1 | 1710 |
| 2017 | spouse | race mention 2 | `ER70745` | K40 RACE OF SPOUSE-MENTION 2 | 1710 |
| 2017 | spouse | race mention 3 | `ER70746` | K40 RACE OF SPOUSE-MENTION 3 | 1710 |
| 2017 | spouse | race mention 4 | `ER70747` | K40 RACE OF SPOUSE-MENTION 4 | 1711 |
| 2017 | spouse | completed_education | `ER71539` | COMPLETED ED-SP | 2072 |
| 2017 | spouse | birth_state | `ER70736` | K33 STATE SPOUSE WAS BORN | 1708 |
| 2017 | spouse | year_came | `ER70737` | K33YR YEAR CAME TO UNITED STATES-SP | 1708 |
| 2019 | family | interview | `ER72002` | 2019 FAMILY INTERVIEW (ID) NUMBER | — |
| 2019 | head | hispanic | `ER76896` | L39 SPANISH DESCENT-RP | 1792 |
| 2019 | head | race mention 1 | `ER76897` | L40 RACE OF REFERENCE PERSON-MENTION 1 | 1793 |
| 2019 | head | race mention 2 | `ER76898` | L40 RACE OF REFERENCE PERSON-MENTION 2 | 1793 |
| 2019 | head | race mention 3 | `ER76899` | L40 RACE OF REFERENCE PERSON-MENTION 3 | 1793 |
| 2019 | head | race mention 4 | `ER76900` | L40 RACE OF REFERENCE PERSON-MENTION 4 | 1794 |
| 2019 | head | completed_education | `ER77599` | COMPLETED ED-RP | 2056 |
| 2019 | head | birth_state | `ER76889` | L33 STATE REFERENCE PERSON WAS BORN | 1791 |
| 2019 | head | year_came | `ER76890` | L33YR YEAR CAME TO UNITED STATES-RP | 1791 |
| 2019 | spouse | hispanic | `ER76751` | K39 SPANISH DESCENT-SPOUSE | 1707 |
| 2019 | spouse | race mention 1 | `ER76752` | K40 RACE OF SPOUSE-MENTION 1 | 1708 |
| 2019 | spouse | race mention 2 | `ER76753` | K40 RACE OF SPOUSE-MENTION 2 | 1708 |
| 2019 | spouse | race mention 3 | `ER76754` | K40 RACE OF SPOUSE-MENTION 3 | 1708 |
| 2019 | spouse | race mention 4 | `ER76755` | K40 RACE OF SPOUSE-MENTION 4 | 1709 |
| 2019 | spouse | completed_education | `ER77600` | COMPLETED ED-SP | 2057 |
| 2019 | spouse | birth_state | `ER76744` | K33 STATE SPOUSE WAS BORN | 1706 |
| 2019 | spouse | year_came | `ER76745` | K33YR YEAR CAME TO UNITED STATES-SP | 1706 |
| 2021 | family | interview | `ER78002` | 2021 FAMILY INTERVIEW (ID) NUMBER | — |
| 2021 | head | hispanic | `ER81143` | L39 SPANISH DESCENT-RP | 1123 |
| 2021 | head | race mention 1 | `ER81144` | L40 RACE OF REFERENCE PERSON-MENTION 1 | 1124 |
| 2021 | head | race mention 2 | `ER81145` | L40 RACE OF REFERENCE PERSON-MENTION 2 | 1124 |
| 2021 | head | race mention 3 | `ER81146` | L40 RACE OF REFERENCE PERSON-MENTION 3 | 1124 |
| 2021 | head | race mention 4 | `ER81147` | L40 RACE OF REFERENCE PERSON-MENTION 4 | 1125 |
| 2021 | head | completed_education | `ER81926` | COMPLETED ED-RP | 1420 |
| 2021 | head | birth_state | `ER81136` | L33 STATE REFERENCE PERSON WAS BORN | 1122 |
| 2021 | head | year_came | `ER81137` | L33YR YEAR CAME TO UNITED STATES-RP | 1122 |
| 2021 | spouse | hispanic | `ER81016` | K39 SPANISH DESCENT-SPOUSE | 1050 |
| 2021 | spouse | race mention 1 | `ER81017` | K40 RACE OF SPOUSE-MENTION 1 | 1050 |
| 2021 | spouse | race mention 2 | `ER81018` | K40 RACE OF SPOUSE-MENTION 2 | 1050 |
| 2021 | spouse | race mention 3 | `ER81019` | K40 RACE OF SPOUSE-MENTION 3 | 1051 |
| 2021 | spouse | race mention 4 | `ER81020` | K40 RACE OF SPOUSE-MENTION 4 | 1051 |
| 2021 | spouse | completed_education | `ER81927` | COMPLETED ED-SP | 1421 |
| 2021 | spouse | birth_state | `ER81009` | K33 STATE SPOUSE WAS BORN | 1048 |
| 2021 | spouse | year_came | `ER81010` | K33YR YEAR CAME TO UNITED STATES-SP | 1048 |
| 2023 | family | interview | `ER82002` | 2023 FAMILY INTERVIEW (ID) NUMBER | — |
| 2023 | head | hispanic | `ER85120` | L39 SPANISH DESCENT-RP | 1114 |
| 2023 | head | race mention 1 | `ER85121` | L40 RACE OF REFERENCE PERSON-MENTION 1 | 1115 |
| 2023 | head | race mention 2 | `ER85122` | L40 RACE OF REFERENCE PERSON-MENTION 2 | 1115 |
| 2023 | head | race mention 3 | `ER85123` | L40 RACE OF REFERENCE PERSON-MENTION 3 | 1115 |
| 2023 | head | race mention 4 | `ER85124` | L40 RACE OF REFERENCE PERSON-MENTION 4 | 1116 |
| 2023 | head | completed_education | `ER85780` | COMPLETED ED-RP | 1338 |
| 2023 | head | birth_state | `ER85113` | L33 STATE REFERENCE PERSON WAS BORN | 1113 |
| 2023 | head | year_came | `ER85114` | L33YR YEAR CAME TO UNITED STATES-RP | 1113 |
| 2023 | spouse | hispanic | `ER84993` | K39 SPANISH DESCENT-SPOUSE | 1041 |
| 2023 | spouse | race mention 1 | `ER84994` | K40 RACE OF SPOUSE-MENTION 1 | 1041 |
| 2023 | spouse | race mention 2 | `ER84995` | K40 RACE OF SPOUSE-MENTION 2 | 1041 |
| 2023 | spouse | race mention 3 | `ER84996` | K40 RACE OF SPOUSE-MENTION 3 | 1042 |
| 2023 | spouse | race mention 4 | `ER84997` | K40 RACE OF SPOUSE-MENTION 4 | 1042 |
| 2023 | spouse | completed_education | `ER85781` | COMPLETED ED-SP | 1339 |
| 2023 | spouse | birth_state | `ER84986` | K33 STATE SPOUSE WAS BORN | 1039 |
| 2023 | spouse | year_came | `ER84987` | K33YR YEAR CAME TO UNITED STATES-SP | 1039 |
