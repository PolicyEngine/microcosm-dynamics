# Observed firm-microdata source provenance

Provenance sidecar for the **observed firm microdata** staged by
`scripts/fetch_firm_microdata.py` and read by
`src/populace_dynamics/data/form5500.py` and
`src/populace_dynamics/data/osha_ita.py` (issue #192, ADR 0003,
Workstream B).

These are **not** the aggregate target extracts documented in
`employer_firm_target_sources.md`. Those are small tidy derivatives of
published aggregate tables, committed to the repository. These are
record-level microdata: one row per Form 5500 filing, one row per OSHA
Form 300A establishment summary. Following the SIPP/PSID convention,
the raw files stay **outside Git** and are pinned by sha256 recorded at
fetch time rather than by committed bytes.

All three sources are US federal government works, downloaded by
keyless HTTPS GET on **2026-08-11**.

## Why these sources exist in the design

Every firm-side source previously in the repository (SUSB, BDS, QWI,
J2J, J2JOD) is a published *aggregate*. These two are observed firm
records, which is what a firm frame built from real rather than
generated firms requires.

Coverage of the SUSB 2022 sector x canonical-band grid, measured
2026-08-11 across both sources combined:

| | |
|---|---|
| SUSB target cells (20 NAICS sectors x 5 canonical bands) | 97 |
| Cells with zero real records | **0** |
| Cells with fewer than 10 real records | **0** |
| SUSB employment in uncovered cells | **0.00%** |
| Real firm records available | **987,039** |

Implied cell weights (SUSB firms / real records): median 1.7,
p90 14.7, max 225.2 (NAICS 99 `1-9`, an 8,332-firm cell).

Record density is thinnest in the `1-9` band (74 records per 1,000
SUSB firms) and highest in `100-499` (941 per 1,000 — near-census).

## 1. `f_5500_2023_latest.csv` — Form 5500 main filings

- **Source URL:** https://askebsa.dol.gov/FOIA%20Files/2023/Latest/F_5500_2023_Latest.zip
- **Landing page:** https://www.dol.gov/agencies/ebsa/about-ebsa/our-activities/public-disclosure/foia/form-5500-datasets
- **Raw sha256:** `cc89e54c57cb6549ab23842bccc6f4ad20e531ebc42a394732359f6a42b7f595`
- **Raw size:** 29,317,144 bytes (zip); 140,375,556 bytes extracted
- **Rows:** 231,725 filings; 147,302 distinct sponsor EINs
- **Columns read:** `SPONS_DFE_EIN`, `BUSINESS_CODE`,
  `SPONS_DFE_LOC_US_STATE`, `TYPE_PLAN_ENTITY_CD`,
  `TOT_PARTCP_BOY_CNT`, `TOT_ACTIVE_PARTCP_CNT` — names verified
  against the layout sidecar `f_5500_2023_latest_layout.txt` shipped
  inside the published zip.

## 2. `f_5500_sf_2023_latest.csv` — Form 5500-SF (short form)

- **Source URL:** https://askebsa.dol.gov/FOIA%20Files/2023/Latest/F_5500_SF_2023_Latest.zip
- **Raw sha256:** `fa9ff9b15f0eef01dba7533121f33dfa5cc8befca9ce885db9b97063b32fb828`
- **Raw size:** 131,009,006 bytes (zip); 547 MB extracted
- **Rows:** 763,552 filings; 695,685 distinct sponsor EINs
- **Columns read:** `SF_SPONS_EIN`, `SF_BUSINESS_CODE`,
  `SF_SPONS_US_STATE`, `SF_TOT_ACT_PARTCP_BOY_CNT`.
- **Why it is not optional:** plans under 100 participants generally
  file the SF form, so reading the main file alone truncates the
  firm-size distribution rather than merely shrinking the sample.

### Combined Form 5500 universe (2023)

995,277 filings, 828,330 distinct sponsor EINs, 790,028 with at least
one active participant (12.4% of SUSB firms; 130,218,853 summed
active participants, 95.9% of SUSB 2022 employment).

**Unit caveats (pre-registered):**

- The sponsor EIN is a **filer** key, not the SUSB enterprise.
  23,813 sponsors report 500+ active participants while SUSB counts
  21,041 firms with 500+ employees — more large sponsors than large
  firms exist, so the units provably differ.
- **Active participants are a lower bound on employment**: the count
  covers plan-covered workers only.
- 122,173 sponsors file more than one form. Participant counts across
  a sponsor's plans **overlap and must never be summed**; the reader
  aggregates by maximum.
- Sponsors are selected on plan sponsorship. Reweighting to SUSB
  margins corrects the margins, not within-cell selection.

## 3. `ITA_300A_Summary_Data_2025.csv` — OSHA Form 300A summaries

- **Source URL:** https://www.osha.gov/sites/default/files/ITA_300A_Summary_Data_2025_through_03-15-2026_v2.csv
- **Landing page:** https://www.osha.gov/Establishment-Specific-Injury-and-Illness-Data
- **Data dictionary:** https://www.osha.gov/sites/default/files/ITA_Data_Dictionary.pdf
- **Raw sha256:** `986f7025c54599c5d022fc472181a013e231b2df0c6e6b8ef5f4f9192d1ff50a`
- **Raw size:** 84,600,899 bytes
- **Rows:** 383,283 establishment summaries; 106,224 distinct EINs;
  134,682 distinct company names
- **Coverage:** CY2025 submissions received through 2026-03-15.

**Universe caveat:** the ITA reporting universe is hazard-selected
(broadly 250+ employees in recordkeeping industries, or 20-249 in
designated higher-hazard industries). Employment concentrates in NAICS
62, 33, 23, 44, 32 and 49; finance, professional services and
information are essentially absent. It is not a firm frame.

**Data-quality caveat — the consequential one.** The raw
`annual_average_employees` column sums to **321,889,014**, or 237% of
total US employment. The excess is not diffuse:

| Rule | Surviving employment |
|---|---|
| raw | 321,889,014 |
| after hours/employee <= 8,760 (1,996 records, 235,875 employees) | 321,653,139 |
| + cap at 50,000 (drops 103 records) | 47,838,489 |
| + cap at 100,000 (drops 59 records) | 51,026,423 |
| + cap at 613,000 (drops 12 records) | 61,188,048 |
| + cap at 1,000,000 (drops 10 records) | 62,912,901 |

The objective physical test (annual hours per employee cannot exceed
24 x 365) removes almost nothing. **About a dozen records carry roughly
260 million phantom employees**, and the cap chosen to remove them
swings the national total by 32%.

The cap is therefore a **referee choice with a quantified effect on
every downstream margin**, and `osha_ita.apply_quality_rule` requires
it as an explicit argument with no default so it is recorded in the
artifact that used it. `read_ita` applies no cleaning and attaches
`hours_per_employee`, `hours_implausible` and `bandable` flags instead.

4,468 summaries report zero employees; the canonical bands partition
`[1, inf)`, so these are dropped rather than coerced into `1-9`.

## Banding

Both sources carry **integer** employment counts, so
`firms.banding.band_of_count` maps them onto the canonical IC2 bands
exactly. Neither produces a straddling `BandSpan` — unlike CPS `NOEMP`,
SIPP `EJB1_EMPSIZE`, BDS `fsize` ("20 to 99") or LEHD `firmsize`
("0-19"), all of which straddle canonical edges.

## Cross-source join

43,001 EINs appear in both the Form 5500 and OSHA universes. The two
observed employment measures agree on the canonical band for **66.3%**
of them; the median ratio (5500 active participants / OSHA employment)
is 0.89. Disagreement runs in **both** directions — 1,451 firms are
OSHA `100-499` but 5500 `500+` — which is impossible if participants
were merely a subset of employees, and confirms the EIN does not
identify the same unit across the two sources.

That 66.3% agreement rate is a measurement-floor observation: two
independent *administrative* firm-size measures disagree on the band
one time in three. It bounds how tightly any firm-size gate can be set
and is registered here as evidence, not as a threshold.

## Licensing

All three are works of the US federal government (DOL/EBSA and
DOL/OSHA), published without stated redistribution restriction — unlike
the Kauffman Firm Survey (#339), whose public-use archive carries no
explicit redistribution license. They could be committed; they are kept
outside Git for size, and pinned by digest.

The `.../Latest/...` DOL URLs are refreshed in place as amended filings
arrive, so a recorded digest identifies **the vintage actually read**
rather than a stable publisher artifact. A digest mismatch after a DOL
refresh is expected and requires a deliberate pin update plus a rebuild
of every artifact that read the old bytes.
