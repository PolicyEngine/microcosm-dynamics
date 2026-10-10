# CBO 2026 baseline input provenance

These are baseline demographic and economic inputs. No Social Security
cost, income, balance or policy-option table was parsed. Source captures
were provided read-only under `followup/inputs/baseline-inputs/`, captured
2026-10-01. This builder fetched nothing from the web.

## Captures and identities

`sources.json` records original URLs, captured relative paths, locators,
byte counts, full SHA-256, computed SHA-1/base32, archive attribution and
retained compressed-source hashes. Every CBO file came from Internet
Archive raw `id_` captures after direct requests served a DataDome CAPTCHA.
The captured research lane recorded the CDX digests; this builder computed
and matched those digests from the provided bytes. It did not re-query
CDX or assume that the live files still match the captured vintages.

| File | Wayback capture ID | Captured CDX SHA-1/base32 |
| --- | --- | --- |
| `57059-2026-01-Demographic-Projections.zip` | `20260211074115` | `AUU73LM3P3IH4ITJSNMHQM7T7UEHJCDD` |
| `57054-2026-02-LTBO-econ.xlsx` | `20260726122828` | `OWABBCNJ5O2UJGAZDVBAK2SLWSCHOFLK` |
| `51135-2026-02-Economic-Projections.xlsx` | `20260802034021` | `SLIHKFJTIHK62CO3YN5CYBRU4PIQCB4D` |
| `62556-2026-Additional-Info.xlsx` | `20260919143154` | `DTGXZD5RVUA4T4SH3HTVHBHFOFS3DR3I` |

The two demographic CSVs and `61879-Demographic-Projections.xlsx` were
checked byte-for-byte against their members of the verified archive.
Only these input rows are transcribed:

- `fertilityRates_byYearAgePlace.csv`: single ages 14-49, 2021-2099, all,
  native-born and foreign-born women; births per 1,000 females. JSON keeps
  printed units; the accessor divides by 1,000 and returns births per
  woman. It does not convert rates to Bernoulli probabilities.
- `mortalityRates_byYearAgeSex.csv`: ages 0-119, both sexes, 2021-2099;
  deaths per 1,000 people. The accessor divides by 1,000 to obtain q(x),
  following the empirical life-expectancy check below.
- `61879-Demographic-Projections.xlsx`, `1. Population and growth`: row 8
  years, row 39 TFR, row 41 period life expectancy at birth, row 42 at 65;
  2026-2099. This workbook remains external with a pinned hash.
- `57054-2026-02-LTBO-econ.xlsx`, `1. Econ Vars_Annual Rates`: row 8
  years, row 31 growth of real earnings per worker, row 40 CPI-U growth;
  `3. Econ Vars_Annual Levels`: row 7 years, row 13 CPI-U (1982-84=1).
  JSON converts the latter to 1982-84=100. Coverage is 1996-2056.
- `51135-2026-02-Economic-Projections.xlsx`, `2. Calendar Year`: row 7
  years, row 53 CPI-U levels (1982-84=100); 2023-2036.
- `62556-2026-Additional-Info.xlsx`, `1. Covered Workers`: numeric year
  rows, male/female/total workers in thousands; `2. Covered and Taxable
  Earnings`: numeric year rows, covered earnings column B in trillions
  of dollars; 2026-2100. Beneficiary, interest-rate and taxable-payroll
  columns are not transcribed; workbook footnotes are not displayed.
  The workbook's sheets are `Contents`, `1. Covered Workers`,
  `2. Covered and Taxable Earnings`, `3. OASDI Beneficiaries` and
  `4. Average Interest Rates`; only sheets 1 and 2 are read. It holds
  no outlay, revenue, cost-rate or balance table (CBO's main
  62556 projections workbook, which does, was not captured).
- The AWI anchor is CY2024 historical AWI, captured TR2026 single-year
  VI.G1 (`tr2026/lr6g1.html`), SHA-256
  `2e0214278e0b2271616093af02280277f6e363d112c47a90b49fe7168e795e75`.
  Nonempty cell order is year, adjusted CPI, AWI. An AWI header check and
  a differential test against the separate TR2026 accessor guard the
  column selection. The SSA capture lane used User-Agent `Wget/1.21.4`
  after a browser User-Agent returned 403. HTML has per-request Akamai
  markup; exact captured bytes and parsed values are pinned, without
  assuming future fetches will hash identically.

Stable raw CSV/XLSX/PDF captures are retained under `sources/` only when
the payload is below 2 MB and deterministic gzip is below 500 KB, the
repository's stricter precommit limit. Compression uses
`GzipFile(filename='', mtime=0)`; hashes of payload and compressed bytes
are recorded. Larger inputs and HTML carry URL, captured path and hash
only. Rebuilding external inputs requires the captures via `--inputs`.

## Mortality interpretation

CBO labels mortality "deaths per 1,000 people" without an explicit q/m
definition. Both interpretations were checked against every published
2026-2099 period life expectancy at birth and 65:

1. q(x) = printed rate / 1,000.
2. m(x) = printed rate / 1,000, converted using q = m/(1 + m/2).

For each sex, a period life table uses uniform deaths within each year,
including infancy (`f0=0.5`). Arithmetic mean male/female life expectancy
reproduces the combined-sex summary. This averaging convention and q
interpretation are empirical findings, not quoted CBO definitions. Every
source row has q(119)=1 in the q interpretation, with terminal
person-years l(119)/2.

`transcription_check.json` records all published/recomputed values and
both interpretations' errors. Maximum q error is 0.000703364 year;
minimum m error is 0.241771105 year. q passes every summary within
0.0011 year; every m interpretation fails. The tolerance allows rounded
CSV rates and three-decimal published life expectancy. Tests compare
forward life-table columns with independent backward recursion as well.

## Fertility check

Summed all-women ASFR over ages 14-49, divided by 1,000, matches each
published TFR within 0.0023 births per woman. The observed maximum error
is 0.0005. The conservative rounding bound is 36 age rates at half of
0.1 birth per 1,000 plus half of 0.001 in the summary TFR. Native-born
and foreign-born schedules remain published schedules; no unweighted
averaging creates the all-women schedule. Before 2026, TFR is explicitly
derived from the all-women ASFR sum.

## Builder defaults awaiting ratification

The module docstring and per-value metadata name these model-builder
defaults, each awaiting ratification:

- `ten_year_cpiu_then_long_term_growth`: ten-year CPI-U levels through
  2036, growth from adjacent levels; 2023 uses the 2022 LT denominator.
  After 2036 compound published LT growth on the final ten-year level.
- `hold_2056_economic_growth`: final LT CPI-U and real earnings growth
  held through 2100, with CPI levels compounded continuously. No
  demographic extension after 2099 is supplied.
- `cpiw_equals_cpiu_growth` and `cola_equals_annual_cpiu_growth`: annual
  CPI-U growth proxies for series CBO does not publish. This is not a
  statutory Q3-to-Q3 COLA computation. Derived COLA covers 2024-2100.
- `awi_bridge_2025_2026_real_earnings_times_cpiu`: compound the actual
  2024 AWI with `(1 + real_growth/100) * (1 + cpiu_growth/100)` in 2025
  and 2026. Both bridge years are needed because covered inputs begin
  in 2026 and have no 2025 denominator.
- `awi_growth_of_covered_earnings_per_worker`: from 2027 apply growth in
  covered earnings divided by covered workers to the 2026 bridge.
  1e12 dollars/1e3 workers gives nominal dollars per worker; the unit
  factor cancels in growth ratios. Covered inputs continue to 2100;
  AWI needs no post-2056 economic extrapolation. Every analog value is
  tagged derived; only the 2024 anchor is actual.
- `tfr_sum_asfr_before_2026`: use all-women ASFR sums in 2021-2025,
  when no summary TFR is published; published TFR thereafter.

## Deterministic reproduction

From the repository root:

```sh
PYTHONPATH=src /Users/maxghenis/PolicyEngine/microcosm-dynamics/.venv/bin/python scripts/extract_cbo2026_parameters.py --inputs /path/to/baseline-inputs --check
```

The builder re-parses every pinned source, verifies stated CDX digests
and demographic archive membership, and recomputes mortality/fertility
checks. `--check` compares every JSON byte and retained compressed hash,
and writes nothing. Without `--check`, it rebuilds JSON and eligible raw
captures. The accessor separately verifies `FILE_SHA256` for every
consumed JSON on first load. A changed source requires an intentional
rebuild and repin; stale or outside-coverage data are refused.
