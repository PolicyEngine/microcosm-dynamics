# SSDI entitlement inputs, data years 2008 and earlier: provenance

These files are the fitting inputs for the Track A item A4 disabled-worker
entitlement component (`src/populace_dynamics/engine/di_entitlement_rates.py`).
Every data year is 2008 or earlier, the DYNASIM information date. They are SSA
administrative statistics, an SSA actuarial study, and Census Bureau
population estimates. They are not DYNASIM or Urban Institute comparator
values. The 2023 DI Annual Statistical Report in `../di_asr_2023/` remains
validation-only and is not read by the fit.

## Acquisition

- Fetched 2026-09-22 by a Claude Code session (Track A lane A4) with `curl`
  from the Internet Archive Wayback Machine, using the `id_` modifier, which
  returns the archived response body unmodified. ssa.gov returned HTTP 403 to
  `curl` for the live Table 36 and Actuarial Study URLs on 2026-09-22 (as
  `../di_asr_2023/provenance.md` also records), so the SSA pages were taken
  from Wayback captures made in 2006, 2008, and 2009.
- The two Census files were also downloaded from the live
  `www2.census.gov/programs-surveys/popest/datasets/2000-200{7,8}/national/asrh/`
  directories. Their SHA-256 values are identical to the Wayback captures.
- Each capture is committed under `raw/` as gzip (compression level 9,
  mtime 0, no stored file name). The SHA-256 below in the "original bytes"
  column is of the decompressed bytes, which equal the Wayback response body.
  `scripts/extract_di_asr_2008.py` verifies it before parsing.
- `scripts/extract_di_asr_2008.py` parses the captures into `tables.json`
  (verbatim cell text converted to numbers; label and total checks). It does no
  fitting. `--check` confirms that `tables.json` is current.

## Captures

Wayback URL pattern: `https://web.archive.org/web/<capture>id_/<original URL>`.

| Source id | Document and table | Data year | Released | Original URL | Wayback capture | SHA-256 of original bytes | Committed file | SHA-256 of committed file |
|---|---|---|---|---|---|---|---|---|
| asr2008_table19 | DI ASR 2008, Table 19: disabled workers, percentage distribution by sex and age, December 1960–2008 | 1960–2008 | 2009-07 | http://www.ssa.gov/policy/docs/statcomps/di_asr/2008/table19.html | 20090827105022 | 20716375cdb398cf00cdaef6325708d9a60ae5908f007e13a78183368cfe0a96 | raw/asr2008_table19.html.gz | e412f2ba9472c10b425966ba7fc4551e216085b4b9c840affd2530467b1bc623 |
| asr2008_table20 | DI ASR 2008, Table 20: disabled workers by age and sex, December 2008 | 2008 | 2009-07 | http://www.ssa.gov/policy/docs/statcomps/di_asr/2008/table20.html | 20090827104934 | ce35283fa048f3158a563e3d4fa3fa82b5b8dbe3ae930e830b1cc377a2e108c8 | raw/asr2008_table20.html.gz | 0dbb550ff0fbc5708e9054be17776a02d498ad672fe25611b3310317b444839b |
| asr2008_table35 | DI ASR 2008, Table 35: awards, selected years 1960–2008 | 1960–2008 | 2009-07 | http://www.ssa.gov/policy/docs/statcomps/di_asr/2008/table35.html | 20090827104955 | 5343c4a6b26cb47cb67a216c22253d46dbf33a74babcaa3f0eca000d7a8b341d | raw/asr2008_table35.html.gz | 243ce9e7e3f9b439a74ec2ead8f66ec65e2cbf199e6aa2ac059df247c7479514 |
| asr2008_table36 | DI ASR 2008, Table 36: awards by basis of entitlement, age, and sex, 2008 | 2008 | 2009-07 | http://www.ssa.gov/policy/docs/statcomps/di_asr/2008/table36.html | 20090827105038 | 856eabc7e0be8e522847751b49336a87a189c28d886267c33e3fd7557547d7c9 | raw/asr2008_table36.html.gz | 97032192c23089fc6d1b462b4e1fdbafa85c36ed735f4de63f36473010634eab |
| asr2008_table49 | DI ASR 2008, Table 49: terminations, number and rate, 1960–2008 | 1960–2008 | 2009-07 | http://www.ssa.gov/policy/docs/statcomps/di_asr/2008/table49.html | 20090827105059 | 85b70dd7a95a28d36bdcd0596ed12e1a4e3810e219fbd64a760460faf5586f24 | raw/asr2008_table49.html.gz | 5b48cce59177b03234259fdf7c1117f9706ab16adc1054c6f41a6278c40141e2 |
| asr2008_table50 | DI ASR 2008, Table 50: terminations by reason, 2008 | 2008 | 2009-07 | http://www.ssa.gov/policy/docs/statcomps/di_asr/2008/table50.html | 20090827104920 | dd0815a9b7b3e73eb803f45fd2231e17ac99c7f934b4f1f117dfe4159fde7123 | raw/asr2008_table50.html.gz | 832a0ed4362ed1b253d1e8cd6f41026db18b1c64ea63a15f73500f78df935bb4 |
| asr2008_table57 | DI ASR 2008, Table 57: workers withheld or terminated for work, by sex and age, 2008 | 2008 | 2009-07 | http://www.ssa.gov/policy/docs/statcomps/di_asr/2008/table57.html | 20090827105023 | 5ab2c2f8ce6dc383c0ea849ed32e057cd4fffc67374f1346008964a292ae59da | raw/asr2008_table57.html.gz | 06e836e23c7eb89555d904ed78da254be03219eddc24a45b84b9d78033e6089f |
| asr2007_table19 | DI ASR 2007, Table 19: disabled workers, percentage distribution by sex and age, December 1960–2007 | 1960–2007 | 2008-09 | http://www.ssa.gov/policy/docs/statcomps/di_asr/2007/table19.html | 20080925083358 | 501997ae0b4d361c80a36e73a27187d271195d8b1f055a32455225f131f7f28f | raw/asr2007_table19.html.gz | 335d3008ae3c9704c496184ff5051b46f0d73d477284074333df255053b3e76e |
| asr2007_table20 | DI ASR 2007, Table 20: disabled workers by age and sex, December 2007 | 2007 | 2008-09 | http://www.ssa.gov/policy/docs/statcomps/di_asr/2007/table20.html | 20080925090141 | b4a45d5f907860a522ce65da170cf42f2729b5499a1d3e0678d789913c15da59 | raw/asr2007_table20.html.gz | ccac48a48f13bddccb7ceb6931f8e565162ecf5761d45b2da022baab8173c989 |
| asr2007_table36 | DI ASR 2007, Table 36: awards by basis of entitlement, age, and sex, 2007 | 2007 | 2008-09 | http://www.ssa.gov/policy/docs/statcomps/di_asr/2007/table36.html | 20080925085809 | 61a0f693269bace888a07555b7a10efd30df6d75543887c82c4e20237a919d3c | raw/asr2007_table36.html.gz | 00e05d980c7eb27f592c1c8124e51a78e1331ca2e2d898a658b1f7ca552b80c6 |
| asr2007_table50 | DI ASR 2007, Table 50: terminations by reason, 2007 | 2007 | 2008-09 | http://www.ssa.gov/policy/docs/statcomps/di_asr/2007/table50.html | 20080925085433 | d721a61f483be5f51525656b8685bcd1c7f8bd6a9bfd221e1b023eb071af6c09 | raw/asr2007_table50.html.gz | 0a326c5d87b9614797fe2db888ad2d0efbcdc2a56e36db482b0886a2261a9774 |
| census_v2008_r_file18 | Census NC-EST2008-alldata, resident population, File 18 (July–December 2008; July 1, 2008 rows used) | 2008 | 2009-05-14 | http://www.census.gov:80/popest/national/asrh/files/NC-EST2008-ALLDATA-R-File18.csv | 20090617025147 | 24a601a9ae9d01d2c0263c4cc5004dc9efece556a72877f2916a5b68a05772ea | raw/census_nc_est2008_alldata_r_file18.csv.gz | 1235f9a7d8971cdd300b22aadfda9f27a19400e940d13950d680e033d71d8810 |
| census_v2008_layout | Census NC-EST2008-alldata file layout (PDF) | 2008 | 2009-05-14 | http://www.census.gov:80/popest/national/asrh/files/NC-EST2008-ALLDATA.pdf | 20090617153131 | e8aa72077b9f3633fc3cd8888efbb6ab9b80e6d9be76ca88fa71c1d530bfbbd1 | raw/census_nc_est2008_alldata_layout.pdf.gz | 5ec22efeae77424bff6554fb860f90febd3d24f93a4fd870fc7ce2e2df1b3626 |
| census_v2007_r_file16 | Census NC-EST2007-alldata, resident population, File 16 (July–December 2007; July 1, 2007 rows used) | 2007 | 2008-05 | http://www.census.gov:80/popest/national/asrh/files/NC-EST2007-ALLDATA-R-File16.csv | 20080606035911 | 4929eee2c75f642ee9083d4f93e3787961ebcf48002283e356ad8aa37b8a77a4 | raw/census_nc_est2007_alldata_r_file16.csv.gz | 574bd25dba650bafcf8d66a085fcc563f0674855f0f1000d6a5f8efd25000bbf |
| as118_death_tables | SSA OCACT Actuarial Study No. 118 (Zayatz, June 2005), death tables: Tables 7A, 7B, 7C, 12 used (1996–2000 experience) | 1996–2000 | 2005-06 | http://www.ssa.gov/OACT/NOTES/as118/DI-WrkerExper_DeathTbls.html | 20060930030715 | 32943f7e1c7ac13f2163a8f2fae3ca7b43c0a54f39abd1cb69bb0495bbd4a153 | raw/as118_death_tables.html.gz | be878cb64845f1618f12e5a2efc98034a5ec16d3f510b543eb8def3e430ab024 |
| as118_recovery_tables | SSA OCACT Actuarial Study No. 118, recovery tables: Tables 14A, 14B, 19 used (1996–2000 experience) | 1996–2000 | 2005-06 | http://www.ssa.gov/OACT/NOTES/as118/DI-WrkerExper_RecoveryTbls.html | 20060930030754 | faf9bad87b4b849463103a35810a34835057857d1f06e748205616ca84f4bd92 | raw/as118_recovery_tables.html.gz | 719655fd8d565418bcfdeb9ced5ec963f3120a090d3167dd8d8cc0d59e445721 |

The 2008 report pages were captured in August 2009, after the report's July
2009 release. The 2007 report pages were captured in September 2008 and the
Vintage 2007 Census file in June 2008, so the `fit_year="2007"` alternative
uses only information public during 2008.

Release dates, checked on 2026-09-22 by the independent review against
sources outside the table captures (not committed; read-only Wayback and
Census requests):

- DI ASR 2008: the report index page reads "released July 2009" in Wayback
  capture `20090724161104` of
  `http://www.ssa.gov:80/policy/docs/statcomps/di_asr/2008/index.html`.
- DI ASR 2007: the index page reads "released September 2008" in Wayback
  capture `20080913083354` of
  `http://www.ssa.gov:80/policy/docs/statcomps/di_asr/2007/index.html`.
- Census Vintage 2008: the committed layout PDF
  (`raw/census_nc_est2008_alldata_layout.pdf.gz`) states "Release Date: May
  14, 2009".
- Census Vintage 2007: the "2008-05" release month was not checked; the
  capture shows the file was public by 2008-06-06.

The same review confirmed each table capture above against the Wayback CDX
index: for every row, the CDX SHA-1 digest of that capture equals the SHA-1
of the decompressed committed file. It also re-downloaded both Census CSVs
from `www2.census.gov` and reproduced the SHA-256 values above.

## What the fit uses

- **Award incidence** (per non-entitled population, by age band and sex):
  Table 36 worker awards (age at entitlement, per the table note) divided by
  Census July 1 resident population minus the Table 20 December worker stock,
  both summed over the ages of each band ("Under 25" is ages 18–24; "65–FRA"
  is age 65).
- **Recovery**: Actuarial Study No. 118 Table 19 (attained age) or Tables
  14A/14B (select age and duration). The level factor fits Table 50 "does not
  meet medical standards" worker terminations (medical improvement, work above
  SGA, and miscellaneous) on the average-year exposure (Table 20 December
  stock, rescaled with the Table 19 prior and current December totals).
- **Death**: Actuarial Study No. 118 Table 12 (attained ages 16–74) and Table 7C
  (ages 75–110), or Tables 7A/7B/7C (select and ultimate). Table 50 worker
  deaths give a diagnostic level factor, applied only in the explicit
  `asr_fitted` mode. The multiplier base is the NCHS 2000 life table already
  committed at `../nchs_life_tables_2000.json`.
- Tables 35, 49, and 57 are extracted for diagnostics and are not used in the
  fit.

## 2008 Trustees Report anchors (recorded, not used)

The 2008 OASDI Trustees Report (builder copy at
`microcosm-launch-evidence/dynasim-parity-20260909/tr2008-inputs-20260922/tr08-2008-oasdi-trustees-report.pdf`,
SHA-256 `517de81a7eb57dc5bc6e14c4dd9f635bce954701b28fa05dafd9bef1ae16172f`),
section V.C.6 "Disability Insurance Beneficiaries", report pages 117–123
(PDF pages 125–131), states these intermediate assumptions. They are
summary rates, not age-sex tables, and the fit does not use them:

- ultimate age-sex-adjusted incidence of 5.2 awards per thousand
  disability-exposed (insured) workers (report page 119);
- an age-sex-adjusted death rate of 27.9 per thousand disabled-worker
  beneficiaries in 2007, projected to fall to about 23.9 by 2017 and then to
  change with general-population death rates (pages 120–121);
- an age-sex-adjusted recovery rate of 10 per thousand in 2007, rising to 12
  by 2017, with an ultimate of about 10.8 (page 121);
- the statement that the termination analysis was based on Actuarial Study
  118 (page 121, footnote 2).

## Still not captured

- Per-insured incidence tables (Actuarial Study No. 118 Table 4 exists, but the
  model has no insured-status variable, so `per_insured` is refused).
- Trustees Report age-sex tables of incidence and termination assumptions.
