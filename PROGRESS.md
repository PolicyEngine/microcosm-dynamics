# v3 compiler continuation lane — progress ledger

Removed before completion (standing order: no PROGRESS.md at completion).

## State

- Branch `claude/ce-v3-source-compiler`, base tip `04035dd`.
- Revision 10 verified: design blob
  `4101260b94b019fc9392898059138b90386784b60ea40b9039562d364592718a`,
  binding revision 10, ratification `bea8b43078ea6260beab368ee59e70ea53dff02b`.
- pdftotext 26.04.0 present; page 23 of `family/1968/fam1968_codebook.pdf`
  reproduces the pinned `derived_page_text_sha256`
  `22ea3467d32c12e76e2c73f2af20efbc050e2f1f130141d7dec697318ae847d4`.

## Corpus shape

47 codebook documents = 43 PDFs (`psid_family_codebook_pages_v1`) plus four
value-label files: `family/{2021,2023}/FAM{2021,2023}ER_formats.{do,sps}`
(`psid_stata_setup_statements_v1` / `psid_spss_setup_statements_v1`).
The two format languages are a genuine dual-language pair for 2021 and 2023.

## Design law located

- §19.3.2 L25793: canonical codebook row = 11 keys.
- §19.3.2 L26472: normalized entry tagged union; `entry_ref` is literal
  `<codebook-field-row-id>:entry:<zero-based-position>`.
- §19.3.2 L26491: a numeric range has type/disposition `rational |
  json_integer`, a nonempty unit.
- §20.3.2 L30938: member-row `source_value` is the exact range-derived
  `typed_disposition`, `value_type`, `typed_value_unit`, `canonical_value`,
  `source_meaning`; L30944 "entry reference remain[s] unchanged".
- §22.2.1 L37788 / §22.2.2 L37810: `source_entry_ref` exact-matches the
  normalized entry; interval atoms follow its retained value type.
- §19.3.2 L26090 / §20.3.5 L31309: an untyped or nonunitized `R` is
  `incomplete_source_numeric_authority`.

## Done

- Located every load-bearing section; recorded citations above.

## Next

1. Build `psid_codebook_extraction.py` (`extract_codebook_rows`).
2. Cross-check against committed evidence `code_map` and the 2021/2023
   dual-language pair.
3. Settle `typed_value_unit` empirically over all 47 documents.
