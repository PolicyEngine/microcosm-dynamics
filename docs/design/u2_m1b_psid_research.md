# U2 milestone 1b: PSID documentation research on three blockers

Documentary research for held-out target U2 (Boomers 2004, 1946–55), done blind on 2026-09-28 and revised on 2026-09-29 to address the independent review (`EV/phase2-20260927/out/u2-m1b-review.md`, verdict REQUEST CHANGES). It answers the three documentary blockers that the independent adjudication (`EV/phase2-20260927/out/u2-adjudicate.md`) left open. Every finding comes from official PSID documentation. No survey record, observed data value, count or outcome was used, and nobody was contacted. The proposed amendments that follow from these findings are in §16a of `docs/design/boomers2004_1946_55_comparison.md` (`u2-draft-4`, pending Max's ruling).

## Verdicts

| Blocker | Verdict | What the documents settle | What remains |
|---|---|---|---|
| B1. 2015 relationship code 20, male legal spouse | **PARTIAL** | Every documented kind of male legal spouse in 2015 is routed away from code 20: husbands are Head; a husband who is not Head is code 90 and was asked the OFUM questions; same-sex partners are code 98 with ER34304 | No document says in words that code 20 is never male in 2015, and one FAQ sentence describes 2015-onward Spouse/Partner couples as possibly same-sex |
| B2. Codes 90 and 92 in 2019–2023 | **PARTIAL** | The instruments ask these persons no Section G income questions, and the FAQ says the codes mark a withheld member | Whether any of their income is edited or imputed into the family-file aggregates |
| B3. Revised 2017 individual weights (ER34651) | **PARTIAL** | The revision's existence, scope and timing; the variable name; the 2017 population control (ACS one-year PUMS, CPS not used) and its two named exclusions; the calibration-variable selection approach in use since 2017; where the 2017 Immigrant sample's recruitment is documented | The 2017 base weights, in particular for the 2017 Immigrant sample, and the 2017 raking dimensions: the calibration variables and interactions used, with their trimming |

## Access and provenance

Every live request that milestone 1b made to `psidonline.isr.umich.edu` on 2026-09-28 returned HTTP 403 with a Cloudflare security challenge. This held for curl and Python urllib with browser headers and for WebFetch; the attempts are recorded per source in the manifest. (Earlier that day, milestone 1 recorded retrieving the 2023 cross-sectional weights report from its official URL at 17:41:53Z; `tests/data/track_u2/psid_sources/weights23_manifest.json`.) The sources therefore come from two routes:

- Internet Archive raw snapshots (`id_`) of the official URLs, fetched 2026-09-28.
- The local browser capture of the official documentation page (`PSID/documentation/capture1`, completed 2026-07-31T01:02:48Z). Its SHA-256 digests are in `browser_digests.txt` and its URL inventory in `psid_documents_inventory.json`.

Where both routes hold a document, the bytes were compared. UserGuide2015, UserGuide2017, UserGuide2023, cross_sec_weights_19 and long_weight_19 from the Internet Archive are byte-identical to the local capture. UserGuide2019 and UserGuide2021 were copied from the local capture, whose versions are newer than any archived snapshot.

Everything consulted is saved under `tests/data/track_u2/psid_docs/`, with URL, retrieval time, bytes and SHA-256 in `manifest.json`. That manifest also lists the already pinned files cited here (codebooks, questionnaires, the 2017 and 2023 weights reports), which were not copied again.

`PSID` below means `/Users/maxghenis/PolicyEngine/psid-data`. `FAQ` means the saved snapshot `tests/data/track_u2/psid_docs/FAQ_20260813.html` of https://psidonline.isr.umich.edu/Guide/FAQ.aspx, whose numbered questions are cited by number and saved-file line. PDF pages are physical page numbers.

## 1. Male legal spouse in 2015 code 20 (PARTIAL)

**Question.** How were a male legal spouse's income and pension items collected and processed in 2015? The family-file spouse variables admit only female spouses (FAM2015ER p. 6, ER60020 '2 Female'), and the 2015 spouse income and pension loops admit only 'CYAQRTH=202, 222' (q2015 p. 89 G49CKPT; p. 166 P70CKPT).

**Evidence.**

1. UserGuide2017, PDF p. 13 (https://psidonline.isr.umich.edu/data/Documentation/UserGuide2017.pdf): 'From 1968-2015, PSID conformed to the Census Bureau conventions' in place at the time the study began by designating the husband in households with heterosexual married adults, the 'Head'.' The FAQ repeats this at question 69 (line 793).
2. FAQ question 73 (line 830): 'If this person is female and she has a (male) spouse or partner in the FU, then he is designated as Reference Person. ... However, if the husband or boyfriend is incapacitated and unable to fulfill the functions of Reference Person, then the FU will have a female Reference Person.'
3. FAQ question 74 (line 834): 'From 1968 to 2015, a married male Head ... might become incapacitated in some way. ... In these cases, the female half of the couple was made Head and the husband became Husband of Head. A Husband of Head was asked the same questions as an Ofum. ... A Husband of Head had the Relationship to Head code 9 or 90.'
4. The 2015 interviewer QxQs, p. 144, IO10 (`PSID/documentation/capture1/fam2015_QxQs.pdf`, official URL https://psidonline.isr.umich.edu/data/Documentation/Fam/2015/QxQs.pdf, SHA-256 `124dd164…43b7`): 'Here we are double-checking that you got permission from study staff to make a male spouse into Husband of Head instead of Head. ... It means that a lot of data that should have been collected about the person didn't get collected.'
5. FAQ question 75 (line 840), on waves before 2017: 'If the person who moves in is married to the Head, they are of course, male Head and Wife (code 20), regardless of time living in the FU.' Line 846: 'PSID did not distinctively label same sex cohabitors prior to 2017.'
6. `PSID/ind2023er/IND2023ER_codebook.pdf`, printed p. 978, 2015 relationship ER34303: '90 Uncooperative legal spouse of Head (this individual is unable or unwilling to be designated as Head)' and '98 Other nonrelatives (includes same-sex partners, friends of children of the FU, etc.)'. The same page defines ER34304, 'WTR SAME SEX PARTNER OF HD 15': 'Whether this person is the same-sex partner of Head. This variable was new for the 2015 Wave.' Its code 1 reads 'This person was identified by the interviewer as the same sex-partner of Head'.
7. UserGuide2015, PDF p. 33: 'The other new variable added to the Individual File in 2015 is an indicator whether an OFUM reported living in the Family Unit is the same-sex partner of Head (ER34304).'
8. UserGuide2017, PDF p. 35: 'As of 2017, same-sex partners of the Reference Person are now designated as Spouse/Partner in the Relation to Reference Person variable (ER34503) rather than as an OFUM. Therefore the 2015 indicator ... (ER34304) is redundant and has been dropped for 2017.' FAQ question 74 (line 836) agrees: 'Once the study started coding same sex relationships in 2017, the Husband of Head Relationship was dropped.'
9. q2015 p. 104: the Big OFUM income series admits 'FUP1YEAR[I].AQRTH.ORD>222'. FAQ question 79 (line 874): 'Considerably less detail is collected for other family unit members (OFUMs).'

**Deduction, labelled as such.** In 2015 a male legal spouse falls into one of three documented categories:

- the Head of a heterosexual couple (items 1, 2 and 5);
- code 90, 'Husband of Head', asked the OFUM questions (items 3, 4 and 6);
- the same-sex partner of a male Head, code 98 with ER34304=1 (items 6 to 8).

For the last two, income is collected in the OFUM series (item 9) and enters the OFUM aggregates. Neither is a pension-loop respondent, because P70CKPT admits only 202 and 222. No documented category puts a male in code 20, which matches the female-only spouse-sex domain of ER60020.

**What remains.** No document says in words that 2015 code 20 is never male. FAQ question 70 (line 797) reads: 'Starting with the 2015 wave, the term Spouse/Partner has replaced Wife/“Wife”. Spouse indicates a legal marriage, while Partner is a cohabiting, non-legally married partner, where the couple can consist of heterosexual or same sex couples.' That general sentence conflicts with the wave-specific statements in items 5 to 8, so the documents do not settle how the legally married same-sex spouse of a male Head was coded in 2015. If he was coded 20 (CYAQRTH 201), the 2015 spouse loops and the OFUM gate would both have skipped him.

**Question for PSID staff (not sent).** 'In the 2015 wave, how was the legally married same-sex spouse of a male Head coded: Relation to Head ER34303 = 20 (family-listing CYAQRTH 201), or 98 with ER34304 = 1? If any 2015 code-20 person is male, in which family-file variables were his income, Social Security, SSI and employer-pension items stored, given that the 2015 spouse income and pension loops admit only CYAQRTH 202 and 222?'

## 2. Codes 90 and 92 in 2019–2023 (PARTIAL)

**Question.** How is income processed for the uncooperative legal spouse (90) and uncooperative partner (92), given that these waves' OFUM gates exclude 901/902 and 921/922 (q2019 p. 103; q2021 p. 205; q2023 p. 203)?

**Evidence.**

1. The family-listing codes: q2019 p. 131, q2021 p. 251 and q2023 p. 249 list '901. Uncooperative Male Spouse', '902. Uncooperative Female Spouse', '921. Uncooperative Male Partner' and '922. Uncooperative Female Partner'.
2. The spouse income repeat admits 'Spouse/Partner (CYAQRTH=201-222, CYFUHU=FU, FUMI)' (q2019 p. 102 'G49 Rule'; q2021 p. 204 and q2023 p. 202 'G49 RULE: Whether Spouse-Partner in FU (CYAQRTH=201-222, CYFUHU=FU, FUMI)').
3. The Big OFUM income series admits 'CYAQRTH=301-882 or 951-982' (G73CKPT: q2019 p. 103; q2021 p. 205; q2023 p. 203). So does the Little OFUM series (G90BCKPT: q2019 p. 125; q2021 p. 243; q2023 p. 241).
4. For contrast, 2017 routed these codes into the OFUM series: q2017 p. 95, G73CKPT 'AQRTH>222', with the codes listed on p. 5.
5. FAQ question 74 (line 836): 'Once the study started coding same sex relationships in 2017, the Husband of Head Relationship was dropped. In its place, the study uses Uncooperative Spouse (... code 90), or Uncooperative Partner (... code 92). These designations are used when one half of the couple is adamant about not giving information about the other half, or when one half adamantly refuses to have their information included. In rare cases, these Relationships to Reference Person will be used when the sample half of a couple has moved out of the FU (family unit) and into an institution and is still in an institution the next wave.'
6. Total family income is defined as the sum of seven variables: reference person and spouse taxable income, their transfer income, OFUM taxable and transfer income, and three Social Security totals (2019: ER77448, `PSID/family/2019/fam2019er_codebook.pdf` p. 2015). The definition says nothing about uncooperative spouses or partners.
7. In full-text searches of the 2019, 2021 and 2023 family codebooks, 'uncooperative' appears only in these places, never in an income, Social Security or SSI definition:
   - relationship-code lists (2019 pp. 591–596; 2021 pp. 637–642; 2023 pp. 624–628);
   - marital-change and couple-status variables (2019 pp. 2058–2059; 2021 pp. 1422–1423; 2023 pp. 1340–1341);
   - the sample-status variable (2019 p. 2064; 2021 p. 1428; 2023 p. 1346);
   - fertility summaries (2019 pp. 2070–2075; 2021 pp. 1434–1439; 2023 pp. 1352–1357).
8. Full-text searches of UserGuide2019, UserGuide2021 and UserGuide2023 find no mention of 'uncooperative'. Nor does the technical-paper list (Internet Archive, 17 September 2025) contain a paper on the subject.

**Finding.** From 2019 the instruments ask codes 90 and 92 no Section G income questions (items 2 and 3), and the FAQ says the codes mark a member about whom information is withheld (item 5). What happens to such a member's income afterwards is not documented online: whether PSID leaves it out of the aggregates, or edits or imputes it into the OFUM totals or elsewhere.

**Question for PSID staff (not sent).** 'In 2019, 2021 and 2023, the Section G spouse series (G49 RULE, CYAQRTH=201–222) and the Big and Little OFUM series (G73CKPT and G90BCKPT, CYAQRTH=301–882 or 951–982) exclude uncooperative spouses and partners (CYAQRTH 901/902/921/922; Relation to Reference Person 90 and 92). Is any income, Social Security or SSI of these persons reported, edited or imputed into the family-file aggregates, that is, total family income and its seven components (for example ER77448, ER77420, ER77441 and ER77446 in 2019 and their 2021 and 2023 counterparts)? Or is it excluded from them?'

## 3. Revised 2017 individual weights, ER34651 (PARTIAL)

**Question.** Where is the construction or calibration documentation that matches the revised ER34651, starting from UserGuide2017 p. 62?

**Evidence.**

1. UserGuide2017, PDF p. 62: 'Weight variables CORE/IMM INDIVIDUAL CROSS-SECTION WT (ER34651) on the individual file and the 2017 CROSS-SECTIONAL FAMILY WEIGHT (ER71571) on the family file have been updated to include the NIS-2017 sample with Release 2 of PSID-2017 data.'
2. May 2019 release notes, p. 1 (https://psidonline.isr.umich.edu/help/DataRelease-May2019.pdf, Internet Archive 15 June 2019), under 'CROSS WAVE INDIVIDUAL FILE 1968-2017': 'Release 2 notes: ... Users should note the weights for the 2017 Immigrant individuals remain zero and will be updated in Release 3.' The individual cross-sectional weight was therefore updated after May 2019.
3. **Release-number conflict.** Items 1 and 2 disagree. UserGuide2017 p. 62 dates the update to 'Release 2 of PSID-2017 data'; the May 2019 notes, which are the Release 2 notes of the cross-wave individual file, say the 2017 Immigrant individuals' weights 'remain zero and will be updated in Release 3'. Neither document says whether the two refer to one release sequence, so the documents conflict on which release first carried the revised ER34651. The conflict concerns timing only. U2 reads the 1968–2023 individual file, whose codebook describes ER34651 as updated (item 9).
4. The construction report, `tests/data/track_u2/psid_sources/cross_sec_weights_17.pdf` (February 2019), PDF p. 3: 'This 2017 New Immigrant sample is not covered by this document but detailed information about the post-1997 immigrant sample will be available from the PSID website.' PDF p. 9: 'The 2017 cross-sectional weights were post-stratified to the population totals that excluded the foreign-born individuals who entered the U.S. after 1997 ... detailed information about 2017 New Immigrant sample and its weighting methodology will be available from the PSID website.' Its content digest equals the only Internet Archive capture (15 June 2019), so the report has not changed since then.
5. The 2019 cross-sectional report, `cross_sec_weights_19.pdf` (April 2021), PDF p. 2: 'A cross-sectional family weight was created in 2017 to represent U.S. families - including those with post-1997 immigrants added as part of the 2017 New Immigrant Sample.' This concerns the family weight, not the construction of the individual weight.
6. The 2019 longitudinal report, `long_weight_19.pdf` (April 2021; Chang, Nishimura, Heeringa, Johnson and Sastry, 'Construction and Evaluation of the 2019 Longitudinal Individual and Family Weights'), PDF p. 2: 'This technical report documents the sample design of the 2017 Immigrant sample and the methodological approach to creating the longitudinal weights constructed for the family units and individuals from the 2019 Panel Study of Income Dynamics (PSID-2019).' It documents the sample's design and joint inclusion probabilities for the 2019 longitudinal weights, not the revised 2017 cross-sectional weight.
7. **The 2023 cross-sectional report**, `tests/data/track_u2/psid_sources/cross_sec_weights_23.pdf` ('June 2026'; Chang, Nishimura, Insolera and Crossley; SHA-256 `58411f56…3983`). Milestone 1 recorded retrieving it from https://psidonline.isr.umich.edu/data/weights/cross_sec_weights_23.pdf (`weights23_manifest.json`) and adjudicated it for the 2023 weight. The first version of this record missed what it documents about 2017:
   - PDF p. 14, Table A3, 'Variable Names for PSID Cross-Sectional Weights': the 2017 row names the individual weight ER34651 and the family weight ER71571.
   - PDF p. 13, Table A2, 'Distribution of PSID Cross-Sectional Individual Weights: 1997-2023': the 2017 row prints the sum of the cross-sectional individual weights beside the ACS one-year PUMS population total, and the column for the CPS March Supplement population total reads 'Not Used' for 2017 to 2023 (the ACS column reads 'Not Used' for 1997 to 2013). The table's note says that 'recent immigrants born between 1960 and 1971 (as well as post-1997 immigrants who co-reside with individuals born in these years) were not part of the PSID NIS-2017 sample', calls them 'the ‘donut hole’ group', and ends: 'Individuals living in the donut hole families and individuals who are recent (post-1997) immigrants but live in group quarters were excluded from the ACS estimate in 2017'.
   - PDF p. 2, note 2: 'The population characteristics used for calibration were based on CPS estimates from 1997 to 2013 and have been based on ACS estimates since 2015.' Note 3: 'The 2017 new immigrant sample have zero longitudinal family weight in 2017 so they would be excluded from the estimates in 2017.'
   - PDF p. 6: 'we started to use a different approach to select the calibration variables since 2017 that ensures that calibration variables are ones that are correlated with both survey response and survey outcome variables.' PDF pp. 6–8 then give the 2023 outcomes, predictors and selected interactions and describe raking with simultaneous trimming. No list is given for 2017.
   - PDF p. 3: 'In 2017, a baseline sample of post-1997 immigrant families and individuals was added to PSID.' and 'See Chang et al. (2021) for the details of the sample recruitment of the 2017 Immigrant sample.' The reference list (PDF p. 10) identifies Chang et al. (2021) as the 2019 longitudinal report of item 6.
8. The official documents page (Internet Archive, 13 August 2026; the local capture of 31 July 2026 agrees) lists these weight reports and no document on the 2017 immigrant sample's weighting:
   - cross-sectional reports for 2009, 2011, 2013, 2015, 2017, 2019 and 2021;
   - longitudinal reports for 2009–2021;
   - the 1968–1992, 1993–2005 and 2007 reports.

   The page also lists no 2023 weight report, although milestone 1 retrieved the June 2026 report of item 7 from its official URL on 2026-09-28, and that report cites a report on the 2023 longitudinal weights (Chang et al., dated 2026 in its text on PDF p. 2 and 2025 in its reference list on PDF p. 10). The page's silence therefore cannot show that a document is absent online.
9. `PSID/ind2023er/IND2023ER_codebook.pdf` p. 1224, ER34651: 'This variable has been updated for all individuals in 2017 including the Immigrant 2017 sample.'
10. The technical-paper list (Internet Archive, 17 September 2025) has no paper on 2017 immigrant-sample weights. UserGuide2019, UserGuide2021 and UserGuide2023 say nothing about the construction of the 2017 weight; UserGuide2019 PDF p. 38 reports a correction to the 1997–2003 cross-sectional weights only.

**Deduction, labelled as such.** Table A2's note names only two groups as excluded from 'the ACS estimate in 2017'. The February 2019 report post-stratified 2017 to totals that 'excluded the foreign-born individuals who entered the U.S. after 1997' (item 4). The June 2026 note implies that the 2017 control printed beside the sum of the individual weights, which Table A3 names ER34651, includes the other post-1997 immigrants. It does not say so in words.

**Finding.** PARTIAL. Documented:

- the weight's identity, ER34651 (item 7, Table A3);
- the revision's existence, scope and timing (items 1, 2, 5 and 9), subject to the unresolved release-number conflict of item 3;
- the 2017 population-control source, the ACS one-year PUMS with the CPS not used, and its two named exclusions (item 7, Table A2 and note 2);
- that calibration variables have been selected by an outcome-correlation approach since 2017 (item 7, p. 6);
- where the 2017 Immigrant sample's design and recruitment are documented (items 6 and 7).

Not documented online:

- **the 2017 base weights**, in particular how initial weights were formed for the 2017 Immigrant sample, whose 2017 longitudinal family weight is zero (item 7, note 3), and how they were combined with the core sample's weights;
- **the 2017 raking dimensions**: which calibration variables and interactions the 2017 selection produced, and the trimming applied with them. The June 2026 report lists these for 2023 only, and the February 2019 report's 2017 dimensions predate the revision.

**Question for PSID staff (not sent).** 'Which PSID document describes the construction of the revised 2017 individual cross-sectional weight ER34651, which now includes the 2017 Immigrant (NIS-2017) sample? In particular, how were base weights formed for the 2017 Immigrant sample, whose 2017 longitudinal family weight is zero, and combined with the core weights? And which calibration (raking) variables, interactions and trimming settings were used for 2017?'

## Incidental exposure

One codebook extract displayed a published whole-file frequency column: the count and percent printed beside ER34304 code 1 on IND2023ER codebook p. 978. It was not used for any finding and is not reproduced here. Later extracts stripped the frequency columns before display. The 2026-09-29 revision displayed the published whole-sample weight statistics in Table A2 of the 2023 cross-sectional report (PDF p. 13, as text and as a page image) and, in one text search, a row of that report's sample sizes. None of these numbers is used for any finding or reproduced here. No raw PSID record was opened. The complete reading record is `docs/design/u2_m1b_exposure.md`.
