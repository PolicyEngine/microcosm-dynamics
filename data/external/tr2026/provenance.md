# TR2026 intermediate baseline inputs

The 2026 OASDI Trustees Report was released June 9, 2026. The captures
used here were retrieved October 1, 2026 into the authorized NASI follow-up
`inputs/baseline-inputs/` directory. This builder fetched nothing from the
network and transcribed no cost, income, cost-rate, income-rate or balance
cells. Files are rebuilt by `scripts/extract_tr2026_parameters.py`.

## Capture and identity

The capture lane used curl with `User-Agent: Wget/1.21.4`: SSA served these
files, while a browser user agent received Akamai HTTP 403. CSV and PDF
payload hashes were stable at capture (a repeated projected male q download
matched). HTML hashes are unstable across live fetches because Akamai adds
per-request markup. `sources.json` pins the captured byte SHA-256; the typed
accessor separately pins each compact parsed JSON file by SHA-256. No new
live download is needed to reproduce these artifacts.

The OACT current-year Downloadables URLs use `/CY/`. A durable annual
locator is expected to be
`https://www.ssa.gov/OACT/Downloadables/2026/TR2026.html` after TR2027 is
released; this expectation is recorded separately from the exact captured
URL. A changing live URL does not replace the captured hash.

Only raw CSV/PDF payloads under 2,000,000 bytes are retained. Period-life
CSVs above 500,000 bytes are stored with deterministic gzip `mtime=0`;
source digests identify the decompressed bytes. HTML is recorded by URL and
SHA-256 rather than committed. V.C1's chapter capture exceeds 2 MB. The
extractor selects only Table V.C1 (anchor #1047210) from it. Other raw
captures can be supplied with `--input-dir`; the builder's default is the
authorized staged follow-up input directory.

## Values, units and coverage

`tr2026_parameters.json` contains compact arrays with explicit columns:
V.C1 COLA percent (determination year 1975-2035) and overlapping AWI;
V.B1 annual CPI-W growth percent (1960-2100); VI.G1 AWI dollars and adjusted
CPI (1970-2100, CPI indexed to 2026=100); V.A1 TFR births per woman and
ASADR deaths per 100,000 (1940-2100, standardized to the April 1, 2010
population); V.A4 period life expectancy at birth and 65 by sex
(1940-2100). Historical and Intermediate sections are preserved. V.C1's
2025 COLA is actual (footnote g); VI.G1's 2025 AWI is estimated; V.B1's
2025 row is estimated. V.A1 2023 total/65+ ASADR is preliminary (footnote d); its under-65 rate is final. The 2024 ASADRs are preliminary (e), while the unmarked TFR is historical. The 2025 TFR/ASADRs are partial-year provisional (f). Per-cell footnotes are retained and source classes distinguish these standings.

`tr2026_death_probabilities.json` preserves all DeathProbsE q values for
exact ages 0-119 and both sexes: historical 1900-2023, Alternative II
2024-2100. The terminal probability is kept as published, even when below
one. Check-only f0 and published e0/e65 values are also retained, with
`f0=(l0-L0)/(l0*q0)` inferred from the printed life-table integers. This is
a derived check input, not a published mortality probability or an
accessor default.

TR2026 has no published single-age fertility schedule in these sources.
No ASFR schedule was invented. Optional SS-area population was omitted.

## Builder defaults awaiting ratification

`post_2035_cola_annual_cpiw`: V.C1 ends in 2035; use V.B1 annual-average
CPI-W growth as COLA for determination years 2036-2100. This approximates
the Q3-to-Q3 statutory adjustment; entries are tagged
`derived_annual_cpiw_cola`. No extrapolation beyond 2100 is allowed.

`constant_terminal_q` in the shared life-table helper: hold the age-119 q
at later ages solely to close the life-expectancy computation. The actual
q vector is never changed. The equations, limitation and builder-default
standing are documented in `src/populace_dynamics/data/life_table.py`.

## Invariants and transcription checks

The extractor verifies every captured payload hash, reparses every numeric
input source, and checks unique consecutive year/age coverage. Every q is
finite and in [0,1]. All q columns equal the corresponding period-life
CSV q cells exactly. Overlapping V.C1/VI.G1 AWI cells agree exactly.
The life-table checks use the f0 inferred above and the named terminal
rule: e0/e65 agree with OACT's two-decimal period-life values within .006
years, and with V.A4's one-decimal values within .051 years. Ages 0-109
with positive printed survivors agree with period-life e within .006;
OACT prints zero for extinct cohorts and uses different conventions at
some ages 110-119. Neither convention is silently substituted for q.
The observed maxima and coverage are recorded below and in the pinned
`transcription_check.json`.

Property tests cover path partitioning, positive AWI and singleton
consistency, bounded q and the historical/Alt2 source boundary. Example
and differential tests reparse all committed q sources, verify exact
terminal q preservation, recompute e0/e65, verify captured and JSON hashes,
refuse invalid years/sex/group selectors, verify immutable arrays/records,
and check continuity across the COLA extension with rounded CPI indices.

Run the deterministic transcription check (writes nothing):

```sh
PYTHONPATH=src /Users/maxghenis/PolicyEngine/microcosm-dynamics/.venv/bin/python scripts/extract_tr2026_parameters.py --check
```

| Check | Maximum error (years) | Tolerance (years) |
|---|---:|---:|
| male_Hist_life_table_e0_to_e109 | 0.005137236 | 0.006 |
| male_Alt2_life_table_e0_to_e109 | 0.005176972 | 0.006 |
| female_Hist_life_table_e0_to_e109 | 0.005122680 | 0.006 |
| female_Alt2_life_table_e0_to_e109 | 0.005164487 | 0.006 |
| male_q_reproduces_V_A4 | 0.049965548 | 0.051 |
| male_q_reproduces_PerLifeTables_e0_e65 | 0.005074466 | 0.006 |
| female_q_reproduces_V_A4 | 0.049510023 | 0.051 |
| female_q_reproduces_PerLifeTables_e0_e65 | 0.005050713 | 0.006 |

## Captured source ledger

- **DeathProbsE_F_Alt2_TR2026.csv**: [q](https://www.ssa.gov/OACT/Downloadables/CY/DeathProbsE_F_Alt2_TR2026.csv); Header Year,0..119; one row per year. SHA-256 `e3178487512f23666ca05754246798557275bc0728f3f937bbca97358f32532b`; 84,092 bytes. Committed `sources/DeathProbsE_F_Alt2_TR2026.csv`.
- **DeathProbsE_F_Hist_TR2026.csv**: [q](https://www.ssa.gov/OACT/Downloadables/CY/DeathProbsE_F_Hist_TR2026.csv); Header Year,0..119; one row per year. SHA-256 `1e2ecd7d24233310108da582ae922c53205d1d239ce3a484ecc5fd6cdb88d0c8`; 135,134 bytes. Committed `sources/DeathProbsE_F_Hist_TR2026.csv`.
- **DeathProbsE_M_Alt2_TR2026.csv**: [q](https://www.ssa.gov/OACT/Downloadables/CY/DeathProbsE_M_Alt2_TR2026.csv); Header Year,0..119; one row per year. SHA-256 `4e2a632a964fadb4cc3fe6127a97ef656eafd43348bf8c7408b018b83840db27`; 84,090 bytes. Committed `sources/DeathProbsE_M_Alt2_TR2026.csv`.
- **DeathProbsE_M_Hist_TR2026.csv**: [q](https://www.ssa.gov/OACT/Downloadables/CY/DeathProbsE_M_Hist_TR2026.csv); Header Year,0..119; one row per year. SHA-256 `ee423873ef2b532fc53c97312a9d6162b876f56e50bd227d45f6c9d9a1cefc8f`; 135,132 bytes. Committed `sources/DeathProbsE_M_Hist_TR2026.csv`.
- **LifeTableDefinitions.pdf**: [life_table_definitions](https://www.ssa.gov/OACT/Downloadables/LifeTableDefinitions.pdf); Life-table function definitions and separation factor at age zero. SHA-256 `94c8fd5806cdb5be3762d1284155e4827a2971d3845088943e3f96a14f26e889`; 130,536 bytes. Committed `sources/LifeTableDefinitions.pdf`.
- **PerLifeTables_F_Alt2_TR2026.csv**: [life_table_check](https://www.ssa.gov/OACT/Downloadables/CY/PerLifeTables_F_Alt2_TR2026.csv); Header line 5; Year,x,q(x),l(x),d(x),L(x),T(x),e(x),...; ages 0..119. SHA-256 `80f612185a269069d097fc32b52ba8f65cb24e5605c2201068d4ca414728bef8`; 777,447 bytes. Committed `sources/PerLifeTables_F_Alt2_TR2026.csv.gz`.
- **PerLifeTables_F_Hist_TR2026.csv**: [life_table_check](https://www.ssa.gov/OACT/Downloadables/CY/PerLifeTables_F_Hist_TR2026.csv); Header line 5; Year,x,q(x),l(x),d(x),L(x),T(x),e(x),...; ages 0..119. SHA-256 `a5e71b5a5011468e87b6c0407d60eef956039eb09524c94a3cc5bf6cf165ab97`; 1,225,687 bytes. Committed `sources/PerLifeTables_F_Hist_TR2026.csv.gz`.
- **PerLifeTables_M_Alt2_TR2026.csv**: [life_table_check](https://www.ssa.gov/OACT/Downloadables/CY/PerLifeTables_M_Alt2_TR2026.csv); Header line 5; Year,x,q(x),l(x),d(x),L(x),T(x),e(x),...; ages 0..119. SHA-256 `0d3f38d38d7428e286bb00ae5a318df4eb100e2c801e1487a0410c2f917bc938`; 773,818 bytes. Committed `sources/PerLifeTables_M_Alt2_TR2026.csv.gz`.
- **PerLifeTables_M_Hist_TR2026.csv**: [life_table_check](https://www.ssa.gov/OACT/Downloadables/CY/PerLifeTables_M_Hist_TR2026.csv); Header line 5; Year,x,q(x),l(x),d(x),L(x),T(x),e(x),...; ages 0..119. SHA-256 `bcf123b13a107e3a5d55a3e47e5129b470624e047346171cf1ee3a0a1542d1a5`; 1,216,677 bytes. Committed `sources/PerLifeTables_M_Hist_TR2026.csv.gz`.
- **V_C_prog.html**: [V.C1](https://www.ssa.gov/oact/TR/2026/V_C_prog.html#1047210); Table V.C1, anchor #1047210; historical and Intermediate rows. SHA-256 `b6af98b6e8f131ef17b3208ef0fbfb8f9fbc494bc6d33dbee5c1bcbbfc99d93a`; 2,748,991 bytes. Captured HTML is recorded only.
- **lr5a1.html**: [V.A1](https://www.ssa.gov/oact/TR/2026/lr5a1.html); Single-year V.A1; historical and Intermediate; TFR and ASADR. SHA-256 `7476bb5e9e99a04bd1b7e77afd6f367c4f94d6eb9aff74e33724b5db9d1dc357`; 180,149 bytes. Captured HTML is recorded only.
- **lr5a4.html**: [V.A4](https://www.ssa.gov/oact/TR/2026/lr5a4.html); Single-year V.A4; historical table and first alternative in projected table. SHA-256 `ab45c5e84253cea122ba0f8a284335d03a5819051914422f5980412822a2b919`; 171,472 bytes. Captured HTML is recorded only.
- **lr5b1.html**: [V.B1](https://www.ssa.gov/oact/TR/2026/lr5b1.html); Single-year V.B1; historical and Intermediate; final CPI column. SHA-256 `f1e1347ac2e9013d53a517e0acf05e692660113acd6cbe7554f0efd7c1aaa3a4`; 258,383 bytes. Captured HTML is recorded only.
- **lr6g1.html**: [VI.G1](https://www.ssa.gov/oact/TR/2026/lr6g1.html); Single-year VI.G1; historical and Intermediate; AWI and adjusted CPI. SHA-256 `2e0214278e0b2271616093af02280277f6e363d112c47a90b49fe7168e795e75`; 226,764 bytes. Captured HTML is recorded only.
