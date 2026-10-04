# SSA 2006 Earnings Public-Use File (EPUF): provenance

Source for the proposed EPUF covered-earnings gate. Read by
`src/populace_dynamics/data/epuf.py`, which refuses any staged member whose
SHA-256 differs from the pins below.

## The file

- Landing page: https://www.ssa.gov/policy/docs/microdata/epuf/index.html,
  "Earnings Public-Use File, 2006 (released August 2011)", Federal Data
  Catalog identifier US-GOV-SSA-336.
- Data: https://www.ssa.gov/policy/docs/microdata/epuf/epuf2006_csv_files.zip
- Dictionary: https://www.ssa.gov/policy/docs/microdata/epuf/epuf_dictionary.pdf

| File | Bytes | SHA-256 |
|---|---:|---|
| `epuf2006_csv_files.zip` | 291,602,034 | `0bb97275cc35a1bb42d34d26acbc9df720d4f875854ba1d02c50323d2357003b` |
| member `EPUF2006_DEMOGRAPHIC.csv` | 151,016,999 | `195db459ca7b7c810162cb6e432371e8787eba8331787d2ba1eace1a0da2ccb0` |
| member `EPUF2006_ANNUAL.csv` | 1,751,339,555 | `a47315b56214df66fb9f9abcb2caa60779c8b3d091ded199323672c27e3ea105` |
| member `epuf_dictionary.pdf` (2011) | 155,159 | `9aebb2c4310516dd6b8c9067b2f2d5264529f8162c8822c22982b41d3d18b990` |
| member `READ ME FIRST.doc` | 22,528 | `4b46bc26163b30664d1b535d407821e4a77bb52e287ab8020b566f5910f1e434` |
| `epuf_dictionary.pdf` (web copy, 2014) | 155,241 | `54210e2c9642fc2e3dba54c6c41de8be9055dfec2fe1c8f893775698c9db89ff` |

## Retrieval

- www.ssa.gov answers command-line clients with HTTP 403, so curl could not
  fetch the file. A Chrome download of the zip from the data URL (referrer:
  the landing page) dated 2026-03-18 20:00:07 UTC was on Max's machine.
- On 2026-10-01 at 21:13:53 UTC (server `Date`), the orchestrating Claude Code
  session fetched the zip and the dictionary from www.ssa.gov in the desktop
  app's built-in browser and hashed the response bytes in the page
  (`crypto.subtle.digest`). The server reported `content-length` 291,602,034,
  `last-modified` Fri, 07 Sep 2012 19:41:59 GMT and `etag`
  "11617e72-4c921cd1a4fc0" for the zip, and both hashes equal the staged
  copies above. The staged bytes are therefore what SSA serves today.
- Staging: members extracted to `~/PolicyEngine/epuf-data/csv/` (reader
  override `POPULACE_DYNAMICS_EPUF_DIR`). The download record, documentation
  text and pre-registration EPUF profile are in Max's evidence folder,
  `~/microcosm-launch-evidence/dynasim-parity-20260909/epuf-20261001/`.

## Documentation committed here

| File | Source | Retrieved | SHA-256 |
|---|---|---|---|
| `ssb_v71n4p33.source.txt` | Compson (2011), "The 2006 Earnings Public-Use Microdata File: An Introduction", *Social Security Bulletin* 71(4), https://www.ssa.gov/policy/docs/ssb/v71n4/v71n4p33.html | 2026-10-01, built-in browser: article text plus the page's hidden chart tables, each checked against the DOM | `b40a828cc44c57f25d95a05d467f4ff881948f4ee136ccb67bc9aee4264bbe35` |
| `rsn2012-01.source.txt` | Compson (2012), "Comparing Earnings Estimates from the 2006 Earnings Public-Use File and the Annual Statistical Supplement", Research and Statistics Note 2012-01, https://www.ssa.gov/policy/docs/rsnotes/rsn2012-01.html | 2026-10-01, same method | `886366c321d2abcaf600ba6b64b47af600f3e3a6672a66e6a07c26e7c5067bf7` |
| `epuf_dictionary.source.txt` | `pdftotext -layout` of the dictionary (the 2011 and 2014 PDFs give identical text) | 2026-10-01 | `35bd61b0336659d3cd75c0313519d70f8014540e326a16ae2051a26574b1ac97` |
| `published_tables.json` | SSB Table A1, Table 4, Charts 3 and 4; RSN Table 8; extracted by `scripts/extract_epuf_published_tables.py` | 2026-10-01 | see the file's `text_sha256` fields |

## Facts the reader asserts on the pinned bytes

- 4,384,254 persons. The "4,348,254" printed in parts of the SSB article and
  the research note is a digit transposition; the SSB article's own
  subtraction (4,413,024 sampled less 28,770 removed) and the dictionary give
  4,384,254.
- 3,131,424 persons with at least one annual row; 60,326,474 annual rows; a
  year with zero earnings has no row.
- Rows exist only at calendar-year ages 15-85.
- Every year's maximum equals that year's contribution and benefit base, and
  no value exceeds it.
- SSB Table A1 (records by year and sex), SSB Charts 3 and 4 (persons by
  birth year and sex) and the EPUF columns of RSN Table 8 (share of workers
  below the maximum) reproduce exactly. SSB Table 4 means and medians
  reproduce exactly for all workers, men and women; the sex-unknown group's
  rounded mean misses by $1 in 1963 and 1992.
