# 2008 OASDI Trustees Report (TR2008) parameters: extraction provenance

- **Sources of record.**
  - *The 2008 Annual Report of the Board of Trustees of the Federal OASI and DI Trust Funds*, House Document 110-104 (110th Congress, 2d Session). PDF from Wayback capture `20100331224612` of `http://www.ssa.gov/OACT/TR/TR08/tr08.pdf`: 1,295,810 bytes, 235 pages, SHA-256 `517de81a7eb57dc5bc6e14c4dd9f635bce954701b28fa05dafd9bef1ae16172f`. Its SHA-1 (base32) `3763FHME6PHT7EBSHGDRUWB4FYNIC7OR` equals the Wayback CDX digest for that capture. The CDX index records the same digest for the capture `20080920012308` of that URL, so this file was on ssa.gov by September 20, 2008. Builder copy (not committed): `~/microcosm-launch-evidence/dynasim-parity-20260909/tr2008-inputs-20260922/tr08-2008-oasdi-trustees-report.pdf`.
  - SSA Office of the Chief Actuary, *Actuarial Study No. 118, Social Security Disability Insurance Program Worker Experience* (June 2005). TR2008 section V.C.6.b cites it as the base of its long-range DI termination rates. PDF from Wayback capture `20080326052706` of `http://www.ssa.gov/OACT/NOTES/pdf_studies/study118.pdf`: 679,311 bytes, 102 pages, SHA-256 `ecf8af4de3ae6746d79da9da5597b2b4fc550c6d3c18f0fccce0bce31a15ba0b`, CDX SHA-1 `HDNKVLGFHW3C5TOTMKXXINODJHUNTPKA`. Builder copy (not committed): `~/microcosm-launch-evidence/dynasim-parity-20260909/tr2008-a2-sources-20260922/actuarial-study-118.pdf`. It is not committed because the repository's `.pre-commit-config.yaml` runs `check-added-large-files` (500 KB default) and the PDF is 637 KB even gzip-compressed.
- **Method.** `scripts/extract_tr2008_parameters.py` runs `pdftotext -layout` (poppler 26.09.0 at build) one page at a time and parses each table with explicit row, section and footnote rules. The build fails on any unexpected row shape, missing year or unconsumed token. Each PDF is refused unless its SHA-256, SHA-1 and length match the pins. Series the printed report does not carry come from 2008-vintage SSA pages recovered from the Internet Archive; ssa.gov answers HTTP 403 to programmatic fetches, as in `../di_asr_2023/provenance.md`. Every web capture is committed gzip-compressed under `sources/` and pinned by SHA-256 and by its Wayback CDX SHA-1.
- **Vintage.** `tr2008_report.json` carries `trustees_report_year` and `vintage_year` 2008 (the repository's external-vintage convention). PDF page 1 records House referral on April 10, 2008. Every other source was published by 2009 and describes 2008 or earlier.
- **Extracted.** 2026-09-22. No value was typed by hand; every number is parsed from a pinned PDF or capture.
- **Purpose.** DynaSim scorecard exercise 1 (COLA −1pp, 2030 age profile), Track A work item A2 in `critical-path-cola-20260922.md`. These are model inputs under the TR2008 information vintage. None is a DYNASIM comparator value, and no comparator material was opened to find or build them.
- **Reader.** `src/populace_dynamics/data/tr2008.py` (typed accessors; verifies the SHA-256 of every JSON file it reads). Tests: `tests/test_tr2008_parameters.py` (artifact tier) and `tests/test_extract_tr2008_parsing.py` (unit tier, invented inputs only).
- **Rebuild.** Run `.venv/bin/python scripts/extract_tr2008_parameters.py --pdf <tr2008.pdf> --as118-pdf <study118.pdf>`. The flags default to the builder copies above or to `POPULACE_DYNAMICS_TR2008_PDF` / `POPULACE_DYNAMICS_AS118_PDF`. `--check` rebuilds in memory and fails if any committed JSON differs, without writing.

## Files

| File | Contents |
|---|---|
| `tr2008_report.json` | Tables II.C1, V.A1, V.A3, V.A4, V.B1, V.C1, V.C5 and VI.F6 parsed from the PDF, every row with its `pdf_page`. Also 22 prose-stated assumptions (`text_values`), each with PDF and printed page numbers and the matched sentence. |
| `tr2008_single_year.json` | SSA's online "Single-Year Tables Consistent with 2008 OASDI Trustees Report" for VI.F6, V.B1, V.A1, V.A3, V.A4 and V.C5. Also the plot points of Figures V.C3–V.C6 (DI incidence, termination, conversion, prevalence). |
| `actuarial_study_118.json` | Actuarial Study 118, with page locators and the quoted reading rules (`notes`). Tables:<br>• 4: DI incidence per 1,000 exposed by age group and sex, 1980–2004<br>• 5: terminations by reason and sex, 1980–2004<br>• 6: disabled workers by age group and sex, 1980–2004<br>• 7A–7C: probability of death by select age, sex and duration, 1996–2000<br>• 8A–8C, 15A–15B: survival tables, used for the check<br>• 14A–14B: probability of recovery<br>• 21A–21B: probability of death or recovery, used for the check |
| `ssa_2008_vintage.json` | 2008-vintage SSA tables that TR2008 does not contain:<br>• SSA period life table for 2004 (parsed)<br>• DI Annual Statistical Report 2008 Tables 2, 19, 20, 35, 36, 39, 49, 50 and 57<br>• Annual Statistical Supplement 2008 Tables 4.C2 and 4.C6<br>The ASR and Supplement tables are verbatim cell text, tab-separated, in the style of `../di_asr_2023/tables.json`. |
| `transcription_check.json` | Cell-by-cell check results and recorded observations (below). |
| `sources.json` | Manifest: both PDFs' identities, each capture's original URL, Wayback timestamp, raw-capture URL, CDX SHA-1, payload SHA-256 and bytes, plus located-but-uncommitted sources. |
| `sources/*.html.gz` | The 25 captured payloads, gzip (mtime 0). Digests are of the decompressed payload. |

SHA-256 of the committed JSON (also pinned in the reader and tests):

```
c16161f1ee99d94d97648da078d686325fb05a0d44653b76bc609158e63f6d62  tr2008_report.json
6ada61d3f8a3b693939763cbe142d191d81468f73022fb3450ab69f817ab596e  tr2008_single_year.json
78c5e55b29615e21f60dc6345572ab06206245246394e2a2791d82358c45d7d7  ssa_2008_vintage.json
0cff75e67257f75630f1fb2cbdf7e6b266f47109b5c95e56a976a195f161aa9b  actuarial_study_118.json
18066387c4879135978608c53a2f5309e083a2fc89acc7469399712f2ec9b45d  transcription_check.json
ac09e00eadb5935f36a6a52a808b0a49bd5c76dac0d594e0fb820bbb3373fbc5  sources.json
```

On 2026-09-22 each of the 25 committed captures and the 4 PDFs listed in `sources.json` was re-checked against the live Wayback CDX API: the TR2008 report, Actuarial Studies 118 and 120, and the release-day PDF. The recorded CDX SHA-1 was returned with HTTP status 200 at the recorded timestamp in every case. A second resume repeated all 29 queries later the same day with the same result. `sources.json` also records a fifth located PDF, the TR2008 long-range methods documentation, by CDX digest only; it was never downloaded (sections 3 and 4 below).

## Page locators

TR2008: PDF page = printed page + 8.

| Table | PDF pages | Printed pages | What it gives Track A |
|---|---|---|---|
| II.C1 | 14 | 6 | Ultimate values, in the order intermediate / low cost / high cost:<br>• CPI: 2.8 / 1.8 / 3.8<br>• covered-wage growth: 3.9 / 3.4 / 4.4<br>• death-rate reduction 2032–82: .73 / .32 / 1.21<br>• other ultimate assumptions |
| V.A1 | 88–89 | 80–81 | Age-sex-adjusted death rates (total, under 65, 65+): historical 1940–2007 and projected 2010–2085 every 5 years |
| V.A3 | 93 | 85 | Period life expectancy at birth and at 65 |
| V.A4 | 94 | 86 | Cohort life expectancy at birth and at 65 |
| V.B1 | 100–101 | 92–93 | CPI and average covered-wage growth for 2008–2017, plus 2015–20 and 2020–82 averages |
| V.C1 | 110–111 | 102–103 | COLA 1975–2017, AWI 1975–2017, contribution base, earnings-test amounts |
| V.C5 | 132–133 | 124–125 | DI beneficiaries and prevalence rates |
| VI.F6 | 192–193 | 184–185 | AWI and adjusted CPI for 2007–2017 and every 5 years to 2085 |
| Text | 82–84, 97, 99, 111, 126–135, 165, 171–172, 193 | 74–76, 89, 91, 103, 118–127, 157, 163–164, 185 | Stated assumptions:<br>• CPI and wage ultimates<br>• mortality reduction rules<br>• DI incidence, recovery, death and prevalence<br>• COLA timing (V.C1 footnote 1) |

Actuarial Study 118: PDF page = printed page + 12.

| Table | PDF page | Printed page |
|---|---|---|
| 4, 5, 6 | 29, 30, 31 | 17, 18, 19 |
| 7A, 7B, 7C (death) | 35, 36, 37 | 23, 24, 25 |
| 8A, 8B, 8C (survival from death) | 38, 39, 40 | 26, 27, 28 |
| 14A, 14B (recovery) | 53, 54 | 41, 42 |
| 15A, 15B (survival from recovery) | 55, 56 | 43, 44 |
| 21A, 21B (death or recovery) | 67, 68 | 55, 56 |

V.C1 footnote markers inside cells are removed by an explicit rule and recorded per row:
- footnote 6 on the 1999 COLA;
- footnote 7 ("actual amount") on the 2007 COLA and on the 2007–2008 base and exempt amounts in every alternative.

## Transcription check

The check makes 10,441 comparisons and finds 0 mismatches.

**TR2008 checks.** The independent renderings of TR2008 are:
- the HTML chapters SSA published with the report (`tr08_II_assump`, `tr08_V_*`, `tr08_VI_OASDHI_dollars` and `tr08_VI_LRsensitivity`, captured 2008-03-26);
- the single-year tables.

Row coverage (the set of years in each section) is compared too, so a row the PDF parse skipped fails the check. Every text-stated value is re-read from the same sentence in the report's own HTML chapter. The regexes accept both renderings, because the two differ in three ways:
- line-break hyphens appear as "- " in the PDF and as a space in the HTML;
- footnote numbering differs (the DI incidence sentence carries footnote 2 in the PDF and 3 in the HTML);
- the PDF glues a footnote marker to "age-sex-adjusted".

**Study 118 checks.** Study 118 has no second rendering. Each of its grids is instead checked against another printed table that the study says was computed from it:
- the survival tables "decrement lives" using the probability tables (notes to Tables 8A–8C and 15A–15B);
- Table 21 is "derived from" Tables 7 and 14 (note 2 to Tables 21A/21B).

| Check | Cells | Mismatches |
|---|---:|---:|
| V.C1 PDF vs HTML chapter | 394 | 0 |
| V.C1 AWI increase column = half-up rounded AWI growth | 64 | 0 |
| V.C1 AWI = VI.F6 AWI, 2007–2017, all alternatives | 33 | 0 |
| VI.F6 PDF vs HTML chapter | 378 | 0 |
| VI.F6 PDF vs single-year table | 375 | 0 |
| V.B1 PDF vs HTML chapter (single years and ranges) | 400 | 0 |
| V.B1 PDF vs single-year table | 210 | 0 |
| II.C1 PDF vs HTML chapter | 27 | 0 |
| V.A1 PDF vs HTML chapter | 436 | 0 |
| V.A1 PDF vs single-year table | 432 | 0 |
| V.A3 PDF vs HTML chapter | 329 | 0 |
| V.A3 PDF vs single-year table | 288 | 0 |
| V.A4 PDF vs HTML chapter | 521 | 0 |
| V.A4 PDF vs single-year table | 480 | 0 |
| V.C5 PDF vs HTML chapter | 460 | 0 |
| V.C5 PDF vs single-year table | 438 | 0 |
| Figure V.C5 = intermediate Figures V.C3/V.C4 (separate pages) | 464 | 0 |
| Figure V.C6 prevalence, rounded half-up = V.C5 table prevalence | 534 | 0 |
| Text-stated ultimates = II.C1 / V.B1 values | 13 | 0 |
| All 22 text-stated assumptions: PDF vs HTML chapter (71 values + id set) | 72 | 0 |
| 2004 life table: OACT page = Supplement 4.C6; e0 and e65 round to V.A3 2004 | 5 | 0 |
| Study 118: 8A/8B survivors = prior cell × (1 − 7A/7B), select cells along the row and the ultimate column down (±1 rounding) | 980 | 0 (all exact) |
| Study 118: 15A/15B survivors = prior cell × (1 − 14A/14B), same rules (±1 rounding) | 980 | 0 (largest difference 1) |
| Study 118: 8C survivors at 75–110 = prior age × (1 − 7C), continuing from the select-64 ultimate cell | 72 | 0 |
| Study 118: 21A/21B = 7A/7B + 14A/14B cell by cell (±0.000001) | 1,078 | 0 |
| Study 118 Table 5: total = sum of reasons (numbers exact, rates ±0.02); Total = Male + Female | 275 | 0 |
| Study 118 Table 6: total = sum of age groups; Total = Male + Female | 375 | 0 |
| Study 118 Table 4: Total rate between the Male and Female rates (±0.01); adjusted = gross in 2000 | 328 | 0 |

Outside the JSON check, `tests/test_tr2008_parameters.py` does four more things:
- It compares the V.C1 COLAs for 1975–2007 with the repository's independent SSA series `../ssa_cola_history.json`. All are equal.
- It records that the realized 2008–2010 COLAs in that series (5.8, 0.0, 0.0) differ from TR2008's projections (2.7, 2.5, 2.8).
- It corrupts one committed Study 118 cell or one text value at a time and asserts that exactly the expected checks fail (mutation tests).
- It re-parses the pinned PDFs with a second, minimal parser that shares no parsing code with the extractor, and compares every cell it reads with the reader's accessors. The cells are V.C1 COLA, AWI and AWI increase (65 rows); VI.F6 adjusted CPI and AWI (75 rows); II.C1 (27 cells); Study 118 Table 4 (975 cells); and Tables 7A, 7B, 14A and 14B (2,156 cells). That is 3,503 printed cells, with 0 mismatches. It also asserts the set of years or select ages in every section, so a skipped row fails. These two tests skip when `pdftotext` or the PDFs are absent. They guard against parser defects, not against errors in the PDFs' text layer.

**Defects the check or its review caught.**
- Dot leaders consumed the decimal point of V.B1's high-cost 2011 productivity ".1", producing 1. The row regex was fixed and a regression test added (`test__year_row__keeps_a_leading_decimal_value_after_dot_leaders`).
- The verbatim-table collector required table ids of at least two characters, so single-digit ASR tables such as "Table 2" were silently skipped. The nine ASR and Supplement tables captured earlier were unaffected, because every one has an id of two or more characters; their JSON is unchanged. Fixed, with a regression test (`test__captioned_tables__keeps_single_digit_ids_and_joins_continued`).
- Each text value's `quote` was cut to 400 characters. In six of the 22 entries the cut hid twelve of the entries' values, among them the low- and high-cost DI ultimate incidence (4.2, 6.2) and the 2027 ultimate years. The extractor now keeps the whole matched text (at most 1,056 characters), and a test asserts that every value appears in its quote (`test__text_values__quote_is_the_full_sentence_showing_every_value`). Only those six quotes changed in `tr2008_report.json`; every value is unchanged.

**Release-day PDF.** Wayback capture `20080325214024` of the same URL is a different file: the March 2008 release, 1,111,230 bytes, SHA-256 `c3344158551835b7abbdf4e047f741ecb2f634c0f204f586cf74c27f7b90e2ca`, CDX SHA-1 `ESPELEJP2GMGTFGUIOBDRMBY7YCMAVLN`. `extract_tr2008_parameters.py --compare-release-pdf` found identical numeric tokens on all 27 transcribed pages. The release PDF is not committed.

## What the sources provide, by Track A need

### 1. CPI-W and the COLA path

V.C1 prints COLAs by determination year:
- historical 1975–2006;
- the 2007 actual, 2.3;
- projections for 2008–2017.

The projected COLAs are:

| Alternative | Projected COLAs |
|---|---|
| Intermediate | 2.7 (2008), 2.5 (2009), 2.8 (2010–2017) |
| Low cost | 2.4, 1.9, then 1.8 |
| High cost | 3.5, 2.8, 3.1, 4.6, 5.9, 5.5, 4.6, 3.9, 3.8, 3.8 |

- **Timing** (V.C1 footnote 1): increases are effective for June in 1975–82 and for December after 1982.
- **Ultimate CPI** (II.C1; V.B.2 text): 2.8 / 1.8 / 3.8.
- **After 2017.** TR2008 prints no COLA after 2017. The reader returns the ultimate CPI for 2018 and later and tags it `derived_ultimate_cpi`.
- **Caveat on V.B1.** The single-year V.B1 CPI change equals the ultimate value in every year 2018–2082 of each alternative (tested). But V.B1 is an annual-average rate, not the statutory third-quarter basis. In 2008, for example, the V.B1 CPI is 2.8 while the V.C1 COLA is 2.7.

### 2. Average wage index to 2030

- **V.C1:** historical through 2006 (38,651.41), then TR2008 estimates from 2007 (intermediate 40,307.02) to 2017 (59,376.44).
- **Printed VI.F6:** gives 2020, 2025 and 2030 (97,201.39).
- **Single-year VI.F6:** gives every year 2018–2085 (2018: 61,660.93). Its values equal the printed ones wherever both exist.

The reader's `awi_path` returns TR2008 levels by default. With `realized=` and `last_realized_year=`, it chains TR2008 growth onto a caller's realized level.

### 3. Mortality

**What TR2008 publishes:**
- age-sex-adjusted death rates (total, under 65, 65+), with single years in `tr2008_single_year.json`;
- period and cohort life expectancy at 0 and 65;
- ultimate annual reductions for 2032–82 (alternatives I / II / III): total 0.32 / 0.73 / 1.21 percent, and ages 65+ 0.28 / 0.65 / 1.13 percent;
- the 2007–82 average reduction (I / II / III): 0.30 / 0.75 / 1.26;
- the transition rule: reductions move from those observed in 1984–2004 to the 2032+ ultimate, with alternatives I and III starting at 50 and 150 percent of the observed reductions;
- historical death rates for 1900–2004 (V.A.2).

**Not in TR2008:** death probabilities by single age, sex and year, and the reduction rates by age group, sex and cause.

**2008-vintage substitutes:**
- **(a)** SSA's *Period Life Table, 2004*, captured and parsed here. The OACT page was last modified March 27, 2008. It is identical to Supplement 2008 Table 4.C6, and its e0 (74.83 / 79.96) and e65 (16.67 / 19.5) round to V.A3's 2004 values.
- **(b)** Actuarial Study 120, *Life Tables for the United States Social Security Area 1900–2100* (Wayback `20080326052709`, SHA-256 `f9aadc8cad678b2febd8658b6f5aedfe6cc5496fa5894b7cbaf9250560225003`). Located but not transcribed. It projects age-specific rates on 2005 Trustees Report assumptions, so it is a different vintage.
- **(c) Located, not examined.** SSA's TR08 index page (Wayback `20080914130458`) links `documentation_2008.pdf` as the "Description of the methods used in the long range projections that determine the actuarial status of the trust funds". The file is recorded in `sources.json` (`located_not_committed`) with Wayback `20080921133142` and CDX SHA-1 `EUNJVAMTFCUTPS4MB2LXXSYPVFU5XEVG`. It was not downloaded, so whether it tabulates death probabilities or reductions by age and sex is unknown. It is the most direct unexamined lead for this gap.

The reader's `mortality_improvement_ratio` scales by the published broad-age-group ASADR path. It is a proposed substitute awaiting ratification. With its default base year 2004, the 65-and-over ratio is above 1 in 2005–2012 on the intermediate path (1.0127 in 2010), in 2005–2024 on low cost and in 2005–2009 on high cost, because V.A1's 2004 rate at 65+ (4,940.6) is below its 2003 value (5,148.2) and its 2005–2007 estimates (5,098.4, 5,079.9, 5,062.9). The under-65 ratio is below 1 in every year after 2004 (tested). The `base_year` ruling records this.

### 4. DI incidence and termination

**What TR2008 publishes (aggregates only):**
- **Ultimate age-sex-adjusted incidence** (intermediate / low / high): 5.2 / 4.2 / 6.2 awards per 1,000 exposed (ages through 64, adjusted to the 2000 exposed population), reached in 2027.
- **Death rate:** 27.9 (2007) falling to about 23.9 (2017); 21.4 / 12.2 / 7.7 in 2085 (low / intermediate / high).
- **Recovery rate:** 10 (2007) rising to 12 (2017); ultimate (intermediate / low / high) 10.8 / 13.1 / 8.6, reached in 2027.
- **Termination base:** the long-range base period is 1996–2000, by age, sex and duration, citing Actuarial Study 118.
- **Prevalence:** 40.0 (2007) to 47.4 / 35.6 / 59.6 (2085; intermediate / low / high).
- **Annual series:** gross and age-sex-adjusted incidence, termination, conversion and prevalence (figure plot points), plus the V.C5 counts.

**Not in TR2008:** any DI rate by age or sex, historical or projected, and the insured (exposed) population by age.

**Substitutes captured here:**
- **Actuarial Study 118 (parsed; the base TR2008 names).**
  - Tables 7A–7C and 14A–14B give 1996–2000 select-and-ultimate probabilities of death and of recovery, by select age (16–64), sex and duration. Death continues to attained age 110 in Table 7C. Recovery is "not considered beyond normal retirement age", so those cells are `null`.
  - Table 4 gives incidence per 1,000 exposed by five-year age group and sex, 1980–2004.
  - Table 5 gives terminations by reason (death, recovery, other, conversion) and sex, 1980–2004.
  - Table 6 gives disabled workers by age group and sex, 1980–2004.
  - Reader: `di_termination_probability`, `di_incidence_by_age`, `di_terminations_by_reason`, `di_workers_by_age`. The select-and-ultimate reading rule is quoted from the study's note 3.
- **DI ASR 2008 (verbatim).**
  - Tables 19–20: disabled workers by sex and age.
  - Table 2: all disabled beneficiaries by basis of entitlement, age and sex.
  - Tables 35 and 39: awards, and awards by sex and age. Table 36: awards by basis, age and sex.
  - Tables 49–50: terminations by beneficiary type and by reason. Neither has an age or sex breakdown.
  - Table 57: terminations *because of successful return to work*, by sex and age.
  - Table 53 counts the same 37,711 return-to-work terminations by diagnostic group and age. It is in the committed `di_asr2008_sect03g` capture but is not extracted. Tables 53 and 57 are the only ASR 2008 tables that count terminations by age or sex, and both cover return to work only. (An earlier version of this file called Table 57 the only one.)
  - Tables 2, 20 and 57 agree on 7,426,691 disabled workers in December 2008 (tested).
- **Supplement 2008 (verbatim).** Table 4.C2: fully and disability insured persons by sex and age, selected years to 2008.
- **Located, not examined.** The TR2008 long-range methods documentation (section 3, item (c)) may describe the DI incidence and termination methods by age and sex. Its contents are unknown.

No rates are computed from the verbatim tables here; that is A4's job.

## Choices awaiting Max's ruling (reader keyword arguments)

The plan's section 6 decisions and the A1 specification have not been ruled on. Each choice below is a parameter; the default is the plan's proposed primary where the plan names one.

| Parameter | Default | Basis for the default |
|---|---|---|
| `alternative` | `intermediate` | Plan A1 "Rate path" proposal (TR2008 intermediate) |
| `post_2017` (COLA) | `ultimate_cpi` | Plan A1 "V.C1 through 2017, then 2.8% ultimate"; `none` refuses unprinted years |
| `realized` / `last_realized_year` (COLA, AWI) | none: pure TR2008 | COLA: the plan's TR2008 path. AWI: the plan names no choice; this default is the reader's proposal by analogy |
| `basis` (mortality substitute) | `asadr_broad_age_group` | Reader's proposal for the plan's "named substitute" row; not adopted |
| `base_year` (mortality substitute) | 2004 | Last year of TR2008 historical death rates and of the 2008-vintage life table |

Study 118's tables are exposed as published, with no default. Whether and how A4 uses them, and how to move from the 1996–2000 base to TR2008's projected aggregate levels, is A4's and A1's choice.

## Observations recorded, not reconciled

**DI text and figures.**
- The DI ultimate incidence in the text (intermediate / low / high: 5.2 / 4.2 / 6.2) and Figure V.C3's age-sex-adjusted 2030 plot points (5.22 / 4.17 / 6.26) differ in the high-cost rounding. The text specifies ages through 64 and an award basis; the figure page does not state its age range.
- Figure V.C6 age-sex-adjusted prevalence (40.04 in 2007; 47.41 / 35.56 / 59.56 in 2085) rounds to the text values.

**Study 118 against itself.**
- In survivor Tables 8A/8B/15A/15B, the ultimate cell of select ages 17–64 follows the ultimate column down (checked).
- But decrementing the same row's duration-9 cell by its duration-9 probability reproduces that cell only to within 2. The difference is at most 1 in 160 of 172 cells; the 12 exceptions are listed in `transcription_check.json`.
- So the select rows and the ultimate column are not an exact identity in the printed tables.

**Study 118 (2005) against TR2008's (2008) history, 1980–2004:**

| Comparison | Years equal | Largest difference |
|---|---|---|
| Table 6 total disabled workers (in thousands) vs single-year V.C5 | 25 of 25 | none |
| Table 4 total gross incidence vs Figure V.C3 | 16 of 25 | 0.03 |
| Table 4 age-sex-adjusted incidence vs Figure V.C3 | 7 of 25 | 0.04 |
| Table 5 death + recovery + other rates vs Figure V.C4 gross termination | 14 of 25 | 0.49, in 2003–2004; below 0.03 elsewhere |

SSA revised these historical series between the two publications.

**Table 57 caption.** SSA's DI ASR page prints Table 57's caption after the next section's heading ("Reinstatement Status for Disabled Workers …"). The caption is kept verbatim. The table's columns are the work-related withholding and termination counts of the "Disabled Workers Who Work" section.

## Not verified / limits

- That OACT's 2004 period life table is the exact base table inside the TR2008 projection. Verified only that TR2008's historical rates end in 2004 and that the table's e0 and e65 round to V.A3's 2004 values.
- The figure plot points are SSA's accessibility descriptions of the charts, not values printed in the PDF. They were checked only against each other and against V.C5 (above).
- The ASR and Supplement tables are kept as verbatim text; their column semantics were not re-derived.
- **Study 118 Table 4's age-specific cells** have no second rendering or arithmetic identity. They are checked only against the pooled-ratio bound (Total between Male and Female) and the 2000 adjusted = gross identity. That bound would miss a transcription error that stays inside the bound. The independent re-parse in the tests (above) now reads all 975 cells a second time and matches the reader. That rules out a defect in the extractor's parser, but it reads the same PDF text layer.
- **Study 118 is a base, not a projection.** It holds 1996–2000 experience and 1980–2004 history. TR2008's projected rates by age, sex and duration, and the age profile of its projected incidence, were not found in any source examined. The TR2008 long-range methods documentation was located but not examined.
- **Terminations by age and sex for 2005–2008** from death or medical recovery were not found in:
  - the DI ASR 2008 (all 68 tables in its expanded table of contents, read from Wayback capture `20090827055830`);
  - Supplement 2008 section 6.F (Tables 6.F1–6.F3).
- Actuarial Study 120 is located and hashed only.
- The TR2008 long-range methods documentation is located by CDX digest only. It was not downloaded: downloading another file needed explicit permission from Max, which this lane could not obtain (compare plan section 6, item 7).
- AWI before 1975 is not in TR2008.
- This branch is based on `land-dynamics-stack-20260922` (#449, `bed07225`, plus the formatting-only commit `46ec08b1`), not `origin/master` as the plan recommends for Track A. The reader and extractor import nothing from #449.

## History

- A first builder staged the TR2008, single-year, 2008-vintage and check files and was interrupted before committing.
- On resume (2026-09-22) every staged capture was re-verified: gzip payload hashes and sizes, the page each capture claims to be, and the CDX digests queried live. The extractor's `--check` reproduced the staged outputs from the PDF.
- The resume then added:
  - Actuarial Study 118;
  - DI ASR 2008 Tables 2 and 57;
  - the VI.D HTML chapter;
  - the text-value HTML check.
- It also fixed the single-digit caption defect and corrected the DI gaps. The staged gaps had listed ASR Tables 49–50 as a substitute for terminations by age and sex, which they are not.
- `tr2008_report.json` and `tr2008_single_year.json` are byte-identical to the staged versions.
- A second resume on 2026-09-22 found that work committed as `03cd7e43` and checked it independently:
  - it recomputed the payload SHA-256, SHA-1 and size of all 25 captures and of both PDFs, confirmed gzip mtime 0, and compared each capture's page title with its recorded role;
  - it re-ran the 29 live CDX queries (all returned status 200 with the recorded digest) and the extractor's `--check` (outputs current);
  - it re-parsed 3,503 printed cells with the separate parser, now committed as two tests;
  - it re-read the DI ASR 2008 expanded table of contents (Wayback `20090827055830`; the payload SHA-1 equals the CDX digest `SF6EC464S3H2LV5XTJFBB6BVJLX6WLQW`). The only termination tables are 49–51 (no age or sex; 51 is by state), 53 and 55 (return to work, by diagnostic group and age; 55 is average benefits) and 57 (return to work, by sex and age). This corrected the "only table" statement about Table 57.
- The second resume also recorded the TR2008 long-range methods documentation, which it located through SSA's TR08 index pages and the CDX API. It did not download the file.
- The only data file it changed is `sources.json` (one added `located_not_committed` entry). The other five JSON files are byte-identical to `03cd7e43`.
- An independent review on 2026-09-22 re-read the reader's values with its own parser, using `pdftotext -raw` rather than `-layout`: Study 118 Tables 4–6, 7A–7C and 14A–14B (4,853 cells), and TR2008 V.A1, V.A3, V.A4 and V.C5 (1,602 cells). All matched. It also re-parsed the 2004 life table from its capture (all 120 ages, both sexes) and spot-checked the Figure V.C3–V.C6 plot points. It re-queried the CDX index for the TR2008 PDF, Study 118 and the methods documentation, and confirmed the TR08 index links (`documentation_2008.pdf` in `20080914130458`, `documentation_2007.pdf` in `20080509192827`).
- That review changed:
  - `tr2008_report.json`: full text-value quotes (above);
  - the reader: `cola_path` and `cola_percent` now refuse an unknown `post_2017`, and `di_conversion_ratios` refuses an unknown `basis`. Both used to accept one silently;
  - the `base_year` ruling and this file: they now record the base-2004 behavior of the 65+ mortality ratio (section 3).
