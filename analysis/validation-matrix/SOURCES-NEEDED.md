# Validation-source capture request

This is the first output of the validation-matrix lane. The lane has no network
authority. Please capture the sources below, preserve the downloaded bytes, and
stage them under:

`~/PolicyEngine/psid-data/validation-sources/`

For every capture, please add a sidecar manifest containing the requested URL,
the final URL after redirects, UTC retrieval time, media type, byte length, and
SHA-256. Preserve the publisher's PDF and spreadsheet attachments rather than a
print-to-PDF rendering. When all available items are staged, touch
`~/PolicyEngine/psid-data/validation-sources/REFRESH`.

The exact URLs below are publisher landing or document URLs already identified
in committed project references. For a landing URL, capture the landing HTML
and each PDF/XLSX/CSV attachment labelled as the named publication, recording
each attachment's exact final URL in the manifest. That avoids inventing an
attachment URL whose publisher-generated asset name is not present in the
committed evidence.

## Priority 1: rows blocked without the publication bytes

### SSA / MINT

1. **SSA, “Projection Methodology: Modeling Income in the Near Term,
   Version 8 (MINT8)”**
   - URL: https://www.ssa.gov/policy/docs/projections/methodology.html
   - Capture: the HTML and every linked MINT8 technical/report PDF on that
     page.
   - Establishes: MINT population, administrative-record inputs, projection
     year/cohort basis, earnings and benefit concepts, and therefore the
     mismatch notes required before any numerical MINT comparison.

2. **Urban Institute, “Modeling Income in the Near Term (MINT), Version 8”**
   - URL: https://www.urban.org/research/publication/modeling-income-near-term
   - Exact PDF URL: https://www.urban.org/sites/default/files/publication/104958/modeling-income-in-the-near-term.pdf
   - Capture: landing HTML and the PDF at the exact attachment URL.
   - Establishes: exact MINT8 universe and table definitions; inspect the
     captured tables for cohort replacement-rate, benefit-share, and
     distributional quantities that can be matched as ratios or shares.

3. **Urban Institute, “Modeling Income in the Near Term 6 (MINT6):
   Projecting Retirement Income Through 2060”**
   - URL: https://www.urban.org/research/publication/modeling-income-near-term-mint6
   - Capture: landing HTML, final report PDF, and any table appendix.
   - Establishes: published MINT cohort trajectories and distributional tables
     where MINT8 exposes method but no comparable numeric table. Keep MINT6 and
     MINT8 rows separate; their vintages must never be silently pooled.

4. **SSA Office of Retirement Policy, MINT projections collection**
   - URL: https://www.ssa.gov/policy/docs/projections/index.html
   - Capture: the index HTML and the PDFs/XLSX files for publications explicitly
     labelled as using MINT that contain Social Security replacement rates,
     benefits as a share of career earnings, or beneficiary shares by lifetime
     earnings group. Include the exact linked attachment URLs in the manifest.
   - Establishes: SSA/ORP-published numeric MINT tables, with the cohort,
     denominator, family-unit, and benefit definitions needed for canonical
     matrix rows.

### CBO / CBOLT

5. **CBO, “CBO's 2024 Long-Term Projections for Social Security”**
   - URL: https://www.cbo.gov/publication/60392
   - Capture: landing HTML, report PDF, and all supplemental-data XLSX/CSV
     attachments.
   - Establishes: CBOLT cost-rate, income-rate, taxable-payroll, beneficiary,
     worker, and replacement-rate trajectories. The spreadsheet is essential:
     the report's chart images are not adequate exact locators.

6. **CBO, “Social Security Replacement Rates and Other Benefit Measures:
   An In-Depth Analysis”**
   - URL: https://www.cbo.gov/publication/55038
   - Capture: landing HTML, report PDF, and all supplemental-data attachments.
   - Establishes: CBOLT initial-benefit replacement rates and present-value
     benefit/tax measures by cohort and lifetime-earnings group. Only ratios and
     shares will be used; published dollar levels will not be compared.

7. **CBO, “Social Security's Finances”**
   - URL: https://www.cbo.gov/system/files/2024-05/60281-Social-Security-Finances.pdf
   - Capture: the PDF at this exact URL.
   - Establishes: CBO's published fiscal concepts and chart/page locators needed
     to interpret the 2024 supplemental trajectories.

### DYNASIM / Urban lifetime and reform tables

8. **Mermin (2005), “The Effect of Benefit Reductions on the Distribution
   of Social Security Benefits,” Urban report 411260**
   - URL: https://www.urban.org/research/publication/effect-benefit-reductions-distribution-social-security-benefits
   - Exact PDF URL: https://www.urban.org/sites/default/files/publication/51966/411260-Distributional-Effects-of-Reforming-Social-Security-through-Benefit-Reductions.PDF
   - Capture: landing HTML and the PDF at the exact attachment URL.
   - Establishes: DYNASIM3 Table 1 and Table 2 source pages for the already
     committed PPI, price-indexing, NRA-to-70, and COLA replication values.

9. **Favreault and Steuerle (2007), “Social Security Spouse and Survivor
   Benefits for the Modern Family,” Urban report 311436**
   - URL: https://www.urban.org/research/publication/social-security-spouse-and-survivor-benefits-modern-family
   - Exact PDF URL: https://www.urban.org/sites/default/files/publication/46231/311436-Social-Security-Spouse-and-Survivor-Benefits-for-the-Modern-Family.PDF
   - Capture: landing HTML and the PDF at the exact attachment URL.
   - Establishes: DYNASIM3 winner/loser shares and poverty-change tables for the
     committed earnings-sharing replication, including the 2049 population and
     benefit-concept definitions.

10. **Urban Institute DYNASIM4 projections by birth cohort**
    - URL: https://www.urban.org/dynasim4-projections-birth-cohort
    - Exact workbook URL: https://www.urban.org/sites/default/files/futretsectablongid963.xlsx
    - Capture: landing HTML, the workbook at the exact attachment URL, and
      every other downloadable cohort table/data file.
    - Establishes: public DYNASIM cohort trajectories and any lifetime Social
      Security benefit/tax ratios. Capture the data downloads even when the
      landing page renders an interactive chart.

11. **Urban Institute, “The Dynamic Simulation of Income Model
    (DYNASIM): An Overview”**
    - URL: https://www.urban.org/research/publication/dynamic-simulation-income-model-dynasim
    - Capture: landing HTML and report PDF.
    - Establishes: DYNASIM population, alignment, calendar/cohort, earnings,
      claiming, and family-benefit definitions for explicit mismatch columns.

### WISH Act financing and adequacy

12. **Morningstar, “WISH Granted: How a National Long-Term Services and
    Supports Insurance Program Could Boost Retirement Outcomes”**
    - URL: https://www.morningstar.com/business/insights/research/wish-act-national-ltss-insurance-program
    - Exact full-report PDF URL exposed by the landing page's JSON-LD:
      https://www.morningstar.com/content/cs-assets/v3/assets/blt9415ea4cc4157833/bltbbad12f4cb956f93/68a338a0fd4281840b31bbf3/Morningstar_WISH_Act_Analysis.pdf
    - Capture: landing HTML, the full report at that exact URL, and any
      technical/data appendix. The JSON-LD marks the report as not freely
      accessible; record a failed/authenticated capture explicitly if the
      coordinator cannot preserve the bytes.
    - Establishes: published WISH adequacy effects and population/outcome
      definitions. This model currently lacks LTSS use, spend-down, retirement
      assets, and adequacy outcomes; the source is needed to document that honest
      non-comparability and to identify any financing trajectory it does publish.

13. **117th Congress, H.R. 4289, WISH Act**
    - URL: https://www.congress.gov/bill/117th-congress/house-bill/4289
    - Capture: bill landing HTML and the official introduced-text PDF/XML linked
      there.
    - Establishes: statutory payroll-contribution rate, covered earnings,
      effective dates, vesting, benefit eligibility, and benefit concept. This
      is the authority for the lane's single-side 0.3-percentage-point
      payroll-surtax scenario; the bill separately levies employees and
      employers at 0.3 percent each (0.6 percent combined), and an actuarial
      memo is not a substitute for bill text.

14. **WISH actuarial memoranda by Actuarial Research Corporation (ARC) and
    Oliver Wyman**
    - Discovery authority URL: https://www.congress.gov/bill/117th-congress/house-bill/4289
    - Capture: each ARC or Oliver Wyman PDF linked in the bill's official
      “Related Documents,” sponsor materials, or publisher materials, plus the
      linking page. Record the exact final PDF URL in the manifest; do not
      substitute a press quotation or a secondary summary.
    - Required identity: a memorandum that explicitly evaluates H.R. 4289/WISH
      financing or the 0.3-percentage-point payroll contribution, with author,
      date, assumptions, and projection results visible in the captured bytes.
    - Establishes: actuarial revenue/cost trajectory, balance or sufficiency
      claim, taxable-payroll definition, and projection horizon for the WISH
      comparison. If no such primary memo is linked or publicly retrievable,
      record `NOT PUBLICLY LOCATED` in the manifest rather than supplying a
      secondary source.

## Priority 2: useful interpretive controls

15. **CBO, “An Overview of CBOLT: The Congressional Budget Office
    Long-Term Model”**
    - URL: https://www.cbo.gov/publication/53667
    - Capture: landing HTML and report PDF.
    - Establishes: CBOLT sample, alignment, demographic, earnings, claiming, and
      family-benefit concepts for mismatch notes.

16. **Morningstar Model of U.S. Retirement Outcomes methodology paper**
    - URL: https://www.morningstar.com/content/cs-assets/v3/assets/blt9415ea4cc4157833/bltd4bb26598046aed4/66a1535de91a178e5c15872a/Introducing_the_Morningstar_Model_of_US_Retirement_Outcomes_-_July_2024_-_final.pdf
    - Capture: the PDF at this exact URL.
    - Establishes: Morningstar population, retirement-adequacy outcome, asset,
      mortality, health/LTSS, and simulation definitions needed to explain why
      its WISH adequacy results cannot be represented by the current certified
      Social Security artifact.

## Capture acceptance check

The capture is usable only if the staged manifest lets an offline reader map a
publisher URL to immutable bytes and the document itself exposes page/table (or
sheet/range) locators. A web summary without its underlying PDF/data attachment
does not unblock a numeric row. No captured source authorizes population-level
or absolute-dollar alignment claims in this lane.

## 2026-08-01 REFRESH review

The first staged refresh contained 30 manifested files. All 30 filenames were
unique, and every byte length and SHA-256 matched the manifest. The reviewed
manifest SHA-256 is
`72c180e8d162d9cc09017c355214ba0f9e1175b2d79f294ec2de96ee28cb2e1a`.
Some entries leave `media_type` blank, so content identity is accepted by
URL/hash/size while that manifest field remains incomplete.

Captured and usable: MINT8 method/report and selected SSA MINT tables; the CBO
2024 report and data workbooks; CBO replacement-rate and CBOLT materials;
Favreault-Steuerle (2007); the H.R. 4289 official PDF/XML; the Morningstar WISH
landing page; and generic Morningstar retirement-model documentation.

Still needed in a later refresh:

- Morningstar's full WISH report at the exact PDF URL added to item 12. The
  staged file named `morningstar-wish-technical-appendix.pdf` is only a generic
  July 2024 model appendix and contains no WISH analysis.
- Any primary ARC or Oliver Wyman WISH actuarial memorandum meeting item 14's
  identity rule. The refresh's `NOT-LOCATED.md` records that none was publicly
  located.
- The DYNASIM4 cohort workbook at item 10's exact URL. The publisher link
  returned 404; do not substitute an unverified mirror.
- Mermin (2005) at item 8's exact PDF URL and MINT6 at item 3's URL, if they can
  be recovered from publisher-controlled bytes. Existing committed replication
  artifacts remain the only Mermin numeric provenance in this lane.
- Numeric SSA/ORP MINT policy-option attachments containing replacement-rate
  or benefit/tax ratios. The captured policy-options index describes such
  outputs, but the linked output bytes did not land.
