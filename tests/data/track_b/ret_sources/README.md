# RET historical-source captures

`manifest.json` records each source URL, retrieval timestamp in UTC, decoded
HTTP response byte count, and SHA-256. The HTML files are the complete decoded
response bodies, downloaded with `curl --compressed`, browser headers, and
`Accept-Encoding: gzip, deflate`. No downloaded page was rewritten.

The source roles are:

| Source ID | Evidence |
| --- | --- |
| `ssa_ret_history` | SSA's annual lower/higher exemptions for 2000–2026 and current withholding rates |
| `ssa_ret_determination` | SSA's published indexing method and 2026 worked calculations |
| `ssa_nawi_history` | Published national average wage indexes, 1951–2024 |
| `ssa_cola_history` | Published COLAs, with December-effective years beginning in 1983 |
| `ssa_act_203` | Social Security Act §203(f)(3) and §203(f)(8)(A)–(E) |

The machine-readable transcription in `../ret_history.json` is exclusively
for historical-source checks. It contains retrospective published observations
retrieved in 2026. It is not a registered forecast vintage, and loading
production parameters must not automatically make this fixture available as
forecast inputs.

## Statutory method

[Social Security Act §203(f)(8)](https://www.ssa.gov/OP_Home/ssact/title02/0203.htm)
and [SSA's determination method](https://www.ssa.gov/OACT/COLA/rtdet.html)
specify the modern formula. For exemption year `y`, a COLA effective in
December `y-1` enables the wage-indexing calculation. Without that increase,
the previous exemption continues.

When the trigger is met, the lower monthly amount is based on `$670`
(1994) times `NAWI[y-2] / 22935.42` (the 1992 wage index). The higher monthly
amount is based on `$2500` (2002) times `NAWI[y-2] / 32154.82` (the 2000 wage
index). Each indexed monthly product is rounded to the nearest `$10`, with
exact halfway cases rounded upward, and cannot fall below the corresponding
prior amount. Multiplying by 12 yields the annual exemption; equivalently,
the annual products use bases `$8040` and `$30000` and round to `$120`.
Section 203(f)(8)(C) provides that a new legislated increase overrides this
automatic determination. The modern higher-amount indexing formula applies
after 2002; statutory overrides supplied its earlier amounts.

The 2000 and 2001 higher annual amounts (`$17000` and `$25000`) are published
legislative exceptions and are not multiples of `$120`. They must not be
subjected to the rounding invariant for the modern projection formula. A
back-test of both indexed series therefore starts in 2003 and ends in 2026.
The COLA trigger holds both exemptions unchanged in 2010, 2011, and 2016.

Section 203(f)(3) supplies the exact withholding ratios `1/2` below FRA in all
months of the year and `1/3` in the year of FRA attainment. The latter test
counts only earnings before the FRA month. R1 pins these rates; benefit
deductions, month allocation, and benefit eligibility are later milestones.

These checks establish statutory conformance and published historical values
for listed years. They admit no population, behavioral, or forecast-validation
claim.
