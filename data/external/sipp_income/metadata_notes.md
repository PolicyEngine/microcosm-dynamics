# SIPP metadata evidence

The capture manifests list every attempted source URL, UTC retrieval time, exact
response byte size and SHA-256. All requests used ordinary `requests.get`
without custom headers. No survey microdata file was requested, downloaded or
opened. The failed API requests and locator requests retain their response
bytes. No source returned `SOURCE_BLOCKED`.

The Census variables API exists for releases 2022–2025. Its 2018–2021 endpoints
returned HTTP 404, so those releases use Census dictionaries and pipe-delimited
storage schemas. API `predicateType` describes the API; the separate `pu*_schema`
and `rw*_schema` files describe storage types. They disagree for some variables,
including the final person weight and some identifiers. Keep these two types as
separate metadata fields.

`*_dictionary.pdf` contains the exact Census dictionary. `*_dictionary.txt`
comes from `pdftotext -layout`; `*_dictionary_notes.txt` extracts PDF pages 1–10.
`parse_dictionary_metadata.py` derives `*_dictionary_variables.json` from those
texts and the official storage schemas. Each parsed entry records the dictionary
label, schema label, storage type, value domain, universe, and PDF page indices.
The parser preserves numeric precision, recognizes ranges with currency and
percent signs, supports wrapped value lists and continuation pages, and refuses
entries with missing or unparsed value domains. `verified: false` entries must
not authorize reading a variable. `derived_manifest.json` pins derived files
and the generator. The generation process reads documentation only.

The 2018–2021 dictionaries specify numeric not-in-universe values as `.` and
character values as blank. The 2022–2025 dictionary notes instead describe
internal numeric `.N` and character `N`; this statement does not authorize those
codes in public files. Public API missing-value codes remain release- and
variable-specific.

The Census Python input examples document person-month records, pipe delimiters,
column selection, nullable numeric storage, person linkage using `SSUID` and
`PNUM`, household linkage using `SSUID` and `ERESIDENCEID`, and the separate
calendar-year replicate-weight file. Their documented join uses `SSUID`,
`PNUM`, and `MONTHCODE`. The replicate dictionaries and schemas verify
`REPWGT0` (the base person weight) and `REPWGT1` through `REPWGT240`. The 2019
replicate schema omits `SPANEL` and `SWAVE`; other captured schemas include them.
These example scripts are evidence and were never executed.

## Source ambiguities

- The 2025 replicate dictionary lists panel years 2021–2024, while the primary
  2025 API lists 2022–2025. These are named alternatives; retain the documented
  three-column merge layout and do not infer panel coverage from the stale
  replicate dictionary.
- The 2022 dictionary's `THEQ_BUS` page 207 prints the malformed range
  `-$999,999,999:$999,999,1000`. Its API range is
  `-9999999999:9999999999`. The parser refuses the malformed dictionary domain;
  the API remains a separately verified alternative.
- The 2018–2020 dictionaries list `ESSSMNYN` without a value domain. A storage
  schema label does not supply its codes. These entries remain refused.
- The 2021 dictionary omits value domains for `TSSI_ERSN` and `EBOATOWNER3`.
  These entries remain refused.
