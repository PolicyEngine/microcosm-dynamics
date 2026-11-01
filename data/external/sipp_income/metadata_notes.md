# SIPP income and resources: metadata evidence

This folder holds the Census documentation that verifies
`src/populace_dynamics/data/sipp_income_registry.py`. Review found survey
case records in eight published user-note captures; those whole-page
bodies have been removed. Their inventory entries retain only URL, title,
release, named variables and an exclusion reason. The capture guard checks
the remaining stored notes for identifier columns and identifier/value
text before the branch treats them as metadata. No `pu`/`rw` data archive or
`*_validate` workbook was requested, downloaded or opened.

## Captures

`capture_manifest.json` and `capture_manifest.txt` list every captured URL
with its UTC retrieval time, byte size and SHA-256. Every request used plain
`requests.get` with default headers, and none was refused (no
`SOURCE_BLOCKED`). `capture_supplementary.py` added the release notes,
Census's release-to-release crosswalks (2018 to 2019 through 2021 to 2022),
the 2018 metadata file and the 2018 Programs and Poverty/Income topic
dictionaries. The original capture screened 355 user-note pages for
2018-2025. The retained captures comprise 8 index pages and 93 notes that
name an admitted variable. `user_notes_manifest.json` inventories all 355
pages; eight entries are marked `excluded_record_bearing`, with no stored
body, retrieval time, size or hash. Stored-page hashes cover uncompressed
bytes. This revision rebuilt the inventory and pins from committed files
without running the capture script or requesting any page.

## Record-bearing user notes

`capture_user_notes.py` refuses these Census URLs before requesting them.
The titles below come from their existing inventory metadata; no text
extract or case-specific correction is retained. The same script refuses
to store any new page that holds a case record in any of the forms
`record_bearing_note` lists:

- an identifier column, or a cell that has a cell of digits alone below
  it and begins with an identifier name or, in a first-row or header cell,
  names one anywhere;
- an identifier name followed by a digit with only spaces or simple marks
  between, or by a run of three or more digits that is not a year, with at
  most 40 characters and no period between;
- a table row with a cell that begins with an identifier name, or in a
  first-row or header cell names one anywhere, and, in any other cell, even
  one that names an identifier too, a run of three or more digits that is
  not a year, even in a variable-definition table;
- a table row, or a preformatted line, of three or more numbers;
- a run of nine or more digits in the text a reader sees, or of 14 or
  more, an SSUID's length, anywhere in the page;
- a preformatted block with an identifier and a digit.

The two rules that follow an identifier name read three things, all with
entities decoded, apart from xmp and plaintext contents in the browser
views:

- the visible text, read four times, each time with a tag counted as a
  space. Twice it keeps HTML comments as text: once with every span from a
  `<` to the next `>` taken for a tag and each script or style element
  that an end tag closes left out, and once as a browser with scripting
  off reads it, where a tag opens only with an ASCII letter, `!` or `/`, an
  element's name, folded as ASCII, ends at whitespace, `/` or `>`, script
  and style contents are left out, and title, textarea and xmp contents
  are text, each up to `</` and its name followed by whitespace, `/` or
  `>`, or to the end of the page, as are plaintext contents, to the end of
  the page. The third and fourth times it reads the text as a browser with
  scripting on and with scripting off shows it: the same way, but with
  comments left out where a browser starts and ends them, at `-->` or
  `--!>`, with `<!-->` and `<!--->` empty, and `<?` instructions up to the
  next `>`; with iframe, noembed, noframes and template contents left out
  too, and with scripting on noscript contents, all but template contents
  read as raw text, as a browser reads them, so that a script opening
  inside one opens nothing; with xmp and plaintext contents not decoded;
  and with a NUL dropped from the text outside title, textarea, xmp and
  plaintext contents, where it is shown as U+FFFD;
- the page source with its tags, attributes and scripts, where the 40
  characters also hold no angle bracket, quote or equals sign. href and src
  values, whose slugs name identifiers without values, are removed first
  from every tag outside scripts and styles and from their opening tags.
  Script and style contents, up to their end tag or the end of the page,
  are read as they stand, so no `<` in script code hides a `src`
  assignment. The source is read twice: once with those elements found
  where a browser starts and ends them, in one scan from the start of the
  page, so that a `<script` inside a quoted value opens none, and once with
  one starting at every `<script` or `<style`, even inside another tag;
- one at a time, each quoted attribute value other than href and src; each
  double- or single-quoted string in a script, as a scan from the script's
  start finds them, even one that an escaped quote mark opens; each
  template literal in a script; and each quoted string in a style, all
  read past their backslash escapes.

The text and the source are each read more than one way because the
browser's way, alone, would admit some pages that the first way refuses,
and the text with comments kept reads comment text, which no browser
shows, and noscript contents, which a browser with scripting on does not
show. A tag opens with an ASCII
letter, `!` or `/`. The table and preformatted rules read each
cell's or block's text without its tags; the row-header exemption also
reads a header cell's `scope` attribute. The nine-digit rule skips comments
and noscript blocks, whose tracking numbers are not page content. Each
reading takes time linear in the page's length. A test times invented
pages of 100 kB to 3 MB in the forms found to take quadratic time before
(a long word in a tag, escaped quotes after an unpaired quote in a script,
unclosed tags and comments, script start tags with no end tag, and table
rows and cells that name an identifier) and in those where a slower form of
a linear helper, found in review, does (a hyphenated word in a tag,
unclosed tags after closed ones, script start tags with no `>`, after end
tags or before one end tag, identifier rows after rows of digits, scripts
that end tags close, empty or each holding a string, one script of many
strings, many quoted attribute values, comments and style strings, and
unclosed comments before tags).

These forms are out of scope: a value before its identifier name;
`<br>`-separated CSV text without an identifier; div grids; an identifier
name split by a tag or an invisible character, as in `PN<b></b>UM` or
`SS&shy;UID`, or written in other characters, such as fullwidth letters;
text that a style or the `hidden` attribute hides between an identifier and
its value, since a browser hides it by its styles rather than as it parses
the page; an identifier name and its value in different attribute values,
script strings or style strings, or one of them in a string and the other
in script code; a script string after a lone quote mark in a comment, a
regular expression or a template literal, which the scan of double- and
single-quoted strings takes to open one, as in a comment such as `// it's`;
an identifier and its value split by a tag, quote or equals sign in script
or style code outside a quoted string, as in a comparison `PNUM < 101` or
markup in a `text/template` script, or in an unquoted attribute value, as
in `alt=PNUM's-101`; a value inside a tag after an identifier in the text,
as in `PNUM <i 101`; a run of digits split by a tag, which the readings
count as a space, after a mark the adjacency rule does not allow, a plural
name or other words, as in `PNUM &gt;1&#49;<th>7` or `PNUMs 10<b>1`; a
script that a `<!--` and a `<script` inside it double-escape, which a
browser runs on past its first `</script>`, as in
`<script><!--<script>.</script> . </script>` between an identifier and its
value, where every reading ends it at that end tag and shows the period;
template contents that a browser ends after the first `</template>`, in a
template nested in another or where that end tag sits inside a tag, as in
`<e</template>`, which the views take to end the template there; markup
inside svg or math, where a browser reads a CDATA section as text and the
name of a raw-text or plaintext element as an ordinary element's; markup
that a browser ignores inside a select element, such as a style, noembed or
plaintext opening; nine digits after a comment closed by `--!>`, which the
nine-digit rule reads as still open; a quoted attribute value in an end tag
or a `<!` declaration, or after a name with marks other than `_ : . -`, as
in `[alt]`; an attribute value that holds a raw `>`, which ends its tag; a
value in an href or src value, unless it is a run of 14 or more digits; and
a cell outside a table's first row and header cells that names an
identifier after other words.

The rules in turn refuse some pages that hold no case record, and such a
page stops the capture loudly:

- definition and index tables that name an identifier in a heading cell
  with digits below it, or beside a run of three or more digits that is not
  a year in its row, as in a definition row whose description reads
  `SSUID. Values start at 101.` or an index row `SSUIDs. See 112 notes.`;
- a quoted value that names an identifier before a count across an
  apostrophe or decoded markup, as in a page summary `The SSUID's format in
  the 2018 panel, as 112 notes say`;
- a template literal that holds JSON naming an identifier before a count,
  as in `` `{"name": "SSUID", "pages": "112"}` ``, since a template literal
  is read whole;
- a link slug such as `ssuid-2024` in a script string or a `text/template`
  script, or in an `xlink:href`, `:href` or `img.src` value: the source
  reading removes those values as link targets, but the quoted-value
  reading skips only values named href or src;
- a malformed tag whose quoted href value holds a script opening, as in
  `<a href="<script src="/ssuid-2024.js">`: the browser scan of the source
  removes the href value, which closes at the quote mark before the slug,
  and reads the slug;
- a definition that prints a comparison such as `PNUM < 101` in the
  visible text;
- a `-->` in a quoted attribute value, as in an arrow `alt="Next -->"`,
  after an identifier and before a value in the value's rest, as in
  `PNUM<img alt="--> 7">`: the browser views end the tag at that `>` and
  read the rest of the value as text;
- markup that the readings take another way than a browser does, which
  brings together an identifier and a value that a browser shows apart or
  not at all: a `<plaintext>` tag inside a comment or inside iframe,
  noembed, noframes or template contents, which the text with comments
  kept takes to open plaintext there, as in `<!--<plaintext>PNUM<e101>`;
  character references in plaintext contents, which that text decodes, as
  in `<plaintext>PNUM<!&#49;01>`; a plaintext or xmp opening or a NUL
  inside svg, math or select, or a NUL after a frameset opening; a NUL
  after a reference to a control character, such as `&#4`, which Python's
  `html.unescape` drops; an empty end tag `</>`, which a browser drops and
  the readings count as a space, as in `PNUM</>a567`; and a page that ends
  inside a tag, whose rest a browser drops, as in
  `<a/b="><plaintext><PNUM>101`.

A decimal character reference of more than 4,300 digits makes Python's
`html.unescape` raise, which stops the capture too.

Excluded notes remain attached to relevant registry entries by URL and
title only.

- [2019 SIPP: One Case with Negative Hourly Earning Values](https://www.census.gov/programs-surveys/sipp/tech-documentation/user-notes/2019-usernotes/2019-one-case-neg-hrly-earn-val.html).
- [2021 SIPP: Child Care Assistance Errors](https://www.census.gov/programs-surveys/sipp/tech-documentation/user-notes/2021-usernotes/child-care-assist-errors.html).
- [2022 SIPP: Child Care Assistance Error for a Small Number of Cases](https://www.census.gov/programs-surveys/sipp/tech-documentation/user-notes/2022-usernotes/2022-child-care-assist-err-sm-numb-case.html).
- [2023 SIPP: Incorrect Child Care Assistance Case](https://www.census.gov/programs-surveys/sipp/tech-documentation/user-notes/2023-usernotes/2023-incorrect-child-care-assistance-case.html).
- [SIPP 2023: Minor Discrepancies in School Meals Data](https://www.census.gov/programs-surveys/sipp/tech-documentation/user-notes/2023-usernotes/2023-minor-discrepancies-school-meals.html).
- [2023 SIPP: Inconsistent Case for Social Security on Behalf of a Child](https://www.census.gov/programs-surveys/sipp/tech-documentation/user-notes/2023-usernotes/2023-inconsistent-case-soc-behalf-child.html).
- [2024 SIPP: Inconsistency in One Case in Other Support Paid](https://www.census.gov/programs-surveys/sipp/tech-documentation/user-notes/2024-usernotes/2024-inconsistency-other-support-paid.html).
- [2025 SIPP: Incorrect Top-Coding of Medicare Deductions](https://www.census.gov/programs-surveys/sipp/tech-documentation/user-notes/2025-usernotes/2025-inc-top-cod-mcr-ded.html).

## Other captures

- The Census variable API exists for releases 2022-2025. Its 2018-2021
  endpoints return HTTP 404; those response bodies are kept.
- `*_dictionary.pdf` is each release's data dictionary. `*_dictionary.txt` is
  its `pdftotext -layout` output and `*_dictionary_notes.txt` its first ten
  pages. `parse_dictionary_metadata.py` derives `*_dictionary_variables.json`
  from the text and the storage schema; `derived_manifest.json` pins the
  derived files and the parser. An entry is marked `verified: false` if it
  has an unparsed value line, a range whose minimum exceeds its maximum, or
  (2018-2020, whose pages the parser does not join) a value list that runs
  onto the next page. Comma-grouped codes such as `9,999,999.` parse as
  codes.
- Census's Python input examples are stored byte for byte as
  `*_python_input_example.py.txt`, so the repository's black and ruff checks
  never rewrite them. Several captured pages and the 2022-2025 input
  examples use CRLF line endings; `.gitattributes` here keeps every byte as
  fetched.

## How the registry is verified

`build_registry.py` regenerates the registry and four records from these
files alone.

- **2022-2025.** The variable API supplies each variable's label, type and
  codes. The same release's dictionary supplies a second domain, and a value
  must satisfy both, except the API's own missing codes (`NA-Missing`,
  `NA or Missing`). Where the API lists only a missing code (`GHLFSAM`,
  `GVARSTR`, `SHHADID`, `SSUID`, and `PNUM` in 2022), the dictionary's domain
  governs. `domain_checks.json` lists all 64 concept-years where the two
  sources differ.
- **2018-2021.** The release dictionary verifies label and domain; the
  storage schema (`pu{year}_schema.json`, read by Census's own input example)
  gives the type. The schema's label is checked against the dictionary's
  under NFKC case-folding with punctuation dropped (pdftotext drops some
  characters, such as the `*` of the business formulas) and allowing for the
  schema's 255-256 character truncation. The same check compares the
  2022-2025 API labels with the dictionary's, reading the API's "equals"
  and "or" as `=` and `/`. `label_checks.json` lists every disagreement,
  including a variable one source suppresses and another documents.
- **Every release.** Universes come from the release's dictionary. A domain
  is never taken from another release. The registry's API type
  (`predicateType`) and storage type are kept apart because they disagree for
  some variables (`WPFINWGT`, `ERESIDENCEID` and `EHRESIDENCID` in
  2022-2025, and `SPANEL`, `SWAVE`, `MONTHCODE` and `PNUM` in 2022).
- **Rulings.** `source_rulings.json` holds every hand ruling with the
  evidence it cites. Its 13 named domain rulings list all 64 affected
  release-variable pairs and cite both sources' locations. They retain
  the existing intersections and the API missing-code exception. The
  generator requires a matching ruling for every domain disagreement and
  stops when one is missing; an open ruling refuses the concept. The same
  refusal rule applies to schema-dictionary label conflicts.
- **Crosswalk.** `release_changes.json` lists every change in an admitted
  concept's name, dictionary label, universe, codes, domain, missing codes,
  storage type or admission across releases.
- **Refusals.** `refused_concepts.json` gives each refused concept-year and
  its reason.

## Rulings and open questions

- **Settled.** For 2018 `EJSOWNRE` and `EJSOWNRP` the label and universe are
  quoted from Census's user note "2018 SIPP: Metadata for Rental Properties
  and Other Real Estate", which calls the originally published metadata
  incorrect and states the correct text. The schema still carries the
  original "without a spouse" description, and the 2018 dictionary's
  `EJSOWNRP` universe reads "or" where the note reads "and".
- **Open: 2018 `EDIS8MNYN`.** The storage schema labels it "Suppressed" and
  the dictionary documents it in full; refused in 2018.
- **Open: disability sources in 2020.** For 2020 `TDIS6AMT` the dictionary
  says local government pension and the schema says state government
  pension. For 2020 `EDIS8MNYN` the dictionary says railroad retirement and
  the schema says military retirement. Both are refused in 2020.
- **Open: `ESSI_BRSN` in 2021 and 2022.** These releases publish 1 = Aged,
  2 = Blind or disabled. Census's 2018 user note calls that order a listing
  error, and 2018-2020 and 2023-2025 publish the reverse. Both releases are
  refused, with both readings named.
- **Open: joint holdings in 2020.** The 2020 dictionary and schema print the
  2019 definitions of the `EJS`/`TJS` and `EJO`/`TJO` families (spouse or
  civil union partner). Census's user note "2020 SIPP: Universe for Jointly
  Held Assets and Debts" says `EREGDOMPART` was dropped in 2020 and `EJS`
  became spouse-only: assets held jointly with a civil union partner are
  `EJO`/`TJO`, and civil union partners report unsecured debt only in the
  individual `EO`/`TO` items. The 70 affected concept-years are refused; the
  person-level recodes and household totals stay admitted.
- **Misprinted universes.** The 2021 dictionary gives every `ERETTYPnYN` the
  universe `ERETANY = 1 and EPENANY = 1`, which `ERETANY`'s own 2021
  universe (`EPENANY=2`) makes empty; 2022-2025 print `OR`. The 2024 and
  2025 dictionaries give `TRET1AMT`-`TRET7AMT` the universe of source 8
  (`ERETTYP8YN`). The registry carries no universe for these concept-years
  and cites the ruling instead.
- **Codes inside an amount range.** `TSCNTAMT1` and `TSCNTAMT2` (2022-2025)
  document 9,999,999 as "Not possible to distinguish the amount contributed
  to a defined-benefit pension from the amount contributed to a cash
  balance plan" inside a $0-$9,999,998 amount range. The reader carries the
  code unchanged and `code_label` names it; it is not a dollar amount.
- **Corrected re-release.** Census re-released the 2014-2021 files on
  2025-07-24 to correct `TSSSAMT`, which had double-counted Medicare
  deductions. The reader reads `TSSSAMT` for 2018-2021 only when the caller
  gives a download date on or after the correction.
- **Not verifiable.** The 2018-2020 dictionaries print `ESSSMNYN` without
  value codes, and so do the 2018 metadata file and Programs topic
  dictionary. The 2021 dictionary omits value codes for `TSSI_ERSN` and
  `EBOATOWNER3`. The 2021 dictionary prints `EHRESIDENCID`'s range as
  100001 to 40999. The 2022 dictionary prints `THEQ_BUS`'s range as
  `-$999,999,999:$999,999,1000`, so in 2022 the API's domain alone governs
  `THEQ_BUS`.
- **Census crosswalk anomaly.** Census's 2018-to-2019 crosswalk maps 2018
  `TMHLOAN_STD` (a top-code standard deviation) to 2019 `TMHLOAN_NUM`. Both
  releases carry `TMHLOAN_NUM` with the same label and codes, and the
  registry follows the dictionaries.
- **Stale replicate dictionary.** The 2025 replicate dictionary lists panel
  years 2021-2024 while the 2025 API lists 2022-2025. The reader joins
  replicate weights on `SSUID`, `PNUM` and `MONTHCODE`, as Census's input
  examples do, and infers no panel coverage from the replicate dictionary.
  The 2019 replicate schema omits `SPANEL` and `SWAVE`.

The 2018-2021 dictionaries document numeric not-in-universe values as `.`
and character values as blank. The 2022-2025 dictionary notes describe
internal `.N` and `N` codes, which do not authorize those codes in public
files.
