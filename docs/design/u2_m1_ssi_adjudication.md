# U2 milestone 1: SSI and Census source adjudication

Documentary work only. No PSID records, benefits, incomes, poverty measures, cohort construction or estimators were run. The restriction ledger was read first. This record does not alter U1 or authorize a U2 outcome run.

Route counts: **26 RESOLVED, 0 TO VERIFY**. Blocker `SSI-capture`: **RESOLVED** for source capture and documentary checks; independent review remains outstanding.

Every row cites a staged source below. The parameter capture contains each annual notice's printed page and quoted monthly-rate passage, the eleven historical editions' section-text hashes and amendment histories, all seven YAML hashes and effective dates. The source manifest records every URL, actual UTC retrieval time, byte count and SHA-256.

| Route or blocker | Status | Adjudication | Checkable source |
|---|---|---|---|
| SSI-FBR-2012 | RESOLVED | January individual/couple FBR independently matches the exact-revision YAML snapshots. | `tests/data/track_u2/ssi_sources/fr_ssi_2012.html`, printed p. 66113 (76 FR 66111). |
| SSI-FBR-2013 | RESOLVED | January individual/couple FBR independently matches the exact-revision YAML snapshots. | `tests/data/track_u2/ssi_sources/fr_ssi_2013.html`, printed p. 65756 (77 FR 65754). |
| SSI-FBR-2014 | RESOLVED | January individual/couple FBR independently matches the exact-revision YAML snapshots. | `tests/data/track_u2/ssi_sources/fr_ssi_2014.html`, printed p. 66414 (78 FR 66413). |
| SSI-FBR-2015 | RESOLVED | January individual/couple FBR independently matches the exact-revision YAML snapshots. | `tests/data/track_u2/ssi_sources/fr_ssi_2015.html`, printed p. 64457 (79 FR 64455). |
| SSI-FBR-2016 | RESOLVED | January individual/couple FBR independently matches the exact-revision YAML snapshots. | `tests/data/track_u2/ssi_sources/fr_ssi_2016.html`, printed p. 66964 (80 FR 66963). |
| SSI-FBR-2017 | RESOLVED | January individual/couple FBR independently matches the exact-revision YAML snapshots. | `tests/data/track_u2/ssi_sources/fr_ssi_2017.html`, printed p. 74856 (81 FR 74854). |
| SSI-FBR-2018 | RESOLVED | January individual/couple FBR independently matches the exact-revision YAML snapshots. | `tests/data/track_u2/ssi_sources/fr_ssi_2018.html`, printed p. 59939 (82 FR 59937). |
| SSI-FBR-2019 | RESOLVED | January individual/couple FBR independently matches the exact-revision YAML snapshots. | `tests/data/track_u2/ssi_sources/fr_ssi_2019.html`, printed p. 53703 (83 FR 53702). |
| SSI-FBR-2020 | RESOLVED | January individual/couple FBR independently matches the exact-revision YAML snapshots. | `tests/data/track_u2/ssi_sources/fr_ssi_2020.html`, printed p. 56516 (84 FR 56515). |
| SSI-FBR-2021 | RESOLVED | January individual/couple FBR independently matches the exact-revision YAML snapshots. | `tests/data/track_u2/ssi_sources/fr_ssi_2021.html`, printed p. 67415 (85 FR 67413). |
| SSI-FBR-2022 | RESOLVED | January individual/couple FBR independently matches the exact-revision YAML snapshots. | `tests/data/track_u2/ssi_sources/fr_ssi_2022.html`, printed p. 58717 (86 FR 58715). |
| SSI-general | RESOLVED | General exclusion; unearned first, remainder applied to earnings: §§416.1124(c)(12), 416.1112(c)(4). | `tests/data/track_u2/ssi_sources/CFR-2012-title20-vol2-sec416-1124.xml:41`; all eleven editions: capture `verification.historical_cfr.416.1124` |
| SSI-earned | RESOLVED | Monthly flat earned exclusion: §416.1112(c)(5). | `tests/data/track_u2/ssi_sources/CFR-2012-title20-vol2-sec416-1112.xml:54`; all eleven editions: capture `verification.historical_cfr.416.1112` |
| SSI-share | RESOLVED | Share of remaining earnings excluded: §416.1112(c)(7). | `tests/data/track_u2/ssi_sources/CFR-2012-title20-vol2-sec416-1112.xml:58`; all eleven editions: capture `verification.historical_cfr.416.1112` |
| SSI-resources-individual | RESOLVED | Individual resource limit: final §416.1205(c) row, effective January 1, 1989. | `tests/data/track_u2/ssi_sources/CFR-2012-title20-vol2-sec416-1205.xml:54`; all eleven editions: capture `verification.historical_cfr.416.1205` |
| SSI-resources-couple | RESOLVED | Couple resource limit: final §416.1205(c) row, effective January 1, 1989. | `tests/data/track_u2/ssi_sources/CFR-2012-title20-vol2-sec416-1205.xml:54`; all eleven editions: capture `verification.historical_cfr.416.1205` |
| SSI-unearned-types | RESOLVED | Historical classification of annuities, Social Security, royalties and rents; U2 retains its declared asset-income omission. | `tests/data/track_u2/ssi_sources/CFR-2012-title20-vol2-sec416-1121.xml:25`; all eleven editions: capture `verification.historical_cfr.416.1121` |
| SSI-deeming-exclusions | RESOLVED | Historical income exclusions applicable to deeming: §416.1161. | `tests/data/track_u2/ssi_sources/CFR-2012-title20-vol2-sec416-1161.xml:25`; all eleven editions: capture `verification.historical_cfr.416.1161` |
| SSI-deeming | RESOLVED | No spouse income deemed at/below couple-minus-individual FBR after allocations; benefit cannot exceed the computation without deeming: §416.1163(d), (e)(2). | `tests/data/track_u2/ssi_sources/CFR-2012-title20-vol2-sec416-1163.xml:35`; all eleven editions: capture `verification.historical_cfr.416.1163` |
| SSI-vehicles | RESOLVED | One transportation automobile excluded; other automobile equity counted. U2 vehicle proxy remains an explicit approximation. | `tests/data/track_u2/ssi_sources/CFR-2012-title20-vol2-sec416-1218.xml:27`; all eleven editions: capture `verification.historical_cfr.416.1218` |
| SSI-spouse-definition | RESOLVED | Historical section includes state-law marriage, Social Security entitlement and holding-out criteria. No U2 role/annuity rule is changed here. | `tests/data/track_u2/ssi_sources/CFR-2012-title20-vol2-sec416-1806.xml:26`; all eleven editions: capture `verification.historical_cfr.416.1806` |
| SSI-source-identity | RESOLVED | Seven snapshots equal clean Git objects at the exact full revision. January-1 selection and effective dates recorded. | `tests/data/track_u2/ssi_sources/manifest.json:1190`; `data/external/track_u2_ssi_parameters_2012_2022.json:73`. |
| SSI-U1-overlap | RESOLVED | All seven 2012 parameters equal U1; five scalars pass constancy checks in all eleven years. | `data/external/track_u_ssi_parameters.json:66`; `data/external/track_u2_ssi_parameters_2012_2022.json:929`; `data/external/track_u2_ssi_parameters_2012_2022.json:996`. |
| Census-coverage | RESOLVED | Full weighted-average, all-ages and size-by-children schemas cover 2003–2022 and all six U2 income years. No download or recapture. | `data/external/census_poverty_thresholds_1982_2022.json:8`; `data/external/track_u2_ssi_parameters_2012_2022.json:998`. |
| Census-U1-overlap | RESOLVED | Every 2012 weighted-average, all-ages average and matrix cell equals U1. | `data/external/census_poverty_thresholds_2004_2012.json:117`; `data/external/track_u2_ssi_parameters_2012_2022.json:1011`. |
| Census-2022-precision | RESOLVED | Weighted-average unit is 10 dollars. Stored dollar amounts are retained, with no multiplication by ten. | `data/external/census_poverty_thresholds_1982_2022.json:788`; capture `verification.census_reuse`. |
| BLOCKER-SSI-capture | RESOLVED | Capture, annual notice checks, historical rules, full revision, hashes, effective dates and immutable pins complete; independent adjudication follows. | `tests/data/track_u2/ssi_capture_manifest.json:3`; `tests/track_u2/test_ssi_capture.py:113`. |

## Historical-law check

All eight sections—20 CFR §§416.1112, 416.1121, 416.1124, 416.1161, 416.1163, 416.1205, 416.1218 and 416.1806—were retrieved for every annual edition 2012–2022. These are April 1 editions. Each recorded amendment history ends before 2012. Complete normalized section texts agree across all eleven editions, except spaces around `+` in §416.1163 example 4 (`$80+$86.` versus `$80 + $86.`), which the verifier explicitly isolates. This establishes the historical text used here, without asserting that U2 implements every legal eligibility or deeming rule. See each staged XML's `FDSYS/DATE`, `SECTION/CITA`, and the capture's `verification.historical_cfr`.

Historical §416.1112(c)(4) retains a reference to §416.1124(c)(10), while the $20 exclusion appears at (c)(12) in every captured edition. Both texts are recorded. Section 416.1124(c)(22), excluding interest/dividends on countable resources, also appears in every edition. The five scalar parameters were extracted independently from legal paragraphs/table rows and compared with YAML values (`verification.historical_parameter_values`).

The 2017 source is the full notice `2016-26026`, not a contents page. The 2018 source is corrected republication `2017-27105`. The 2019 govinfo notice `2018-23193` was retrieved successfully. Each annual comparison uses its explicit monthly rates; the 2016 notice states that the rates remain unchanged. See the annual source rows and `verification.annual_notices`.

## Pins and reproduction

| Capture | SHA-256 |
|---|---|
| U2 SSI | `a58d55c160b48cd3e21f730d45265374bd3c8a9eb7eae947469a5a5dc0b23762` |
| U2 SSI source manifest | `a7d09d735fa595e3c7060fb7972d088f0ee062a4c8bb31f739ef3ee578e82e53` |
| Unchanged U1 SSI | `79e641a10d95afba81c8d831852fb52ef0a801e7175e06df17e6cc7cc3e3c523` |
| Reused Track M Census | `288399c475ae3ff02e6d8367425ee0a568b50d239da5656f24d0d2dfafabfb53` |
| Unchanged U1 Census | `dc21a78736f5085872cf56c9cf291258034c1293572b77455cba689a1ed0eec5` |

```sh
.venv/bin/python scripts/capture_track_u2_ssi_parameters.py --check
POPULACE_DYNAMICS_PSID_DIR=/INVENTED/no-psid .venv/bin/python -m pytest tests/track_u2/test_ssi_capture.py -q
```

The default parameter capture is offline and reproduces committed bytes. `scripts/capture_track_u2_ssi_sources.py --pe-us-dir DIR` separately downloads sources and records new retrieval times; refreshing sources requires reviewing and updating the pins. Request headers omit brotli. The five unchanged scalar values are checked across every year, and missing, empty, `unknown` or abbreviated source revisions refuse.

Validation: **31 passed** (focused parameter suite); Black and Ruff clean for the two new capture scripts and the test file. The parent's final combined check supplies the milestone's complete pytest summary. No item in this parameter subtask remains TO VERIFY; independent review and milestone-2 implementation remain outside this source capture.

## Every captured source and hash

The source manifest provides the full URL, UTC time and bytes for every row. Paths below are relative to `tests/data/track_u2/ssi_sources/`.

| Captured source | SHA-256 |
|---|---|
| `CFR-2012-title20-vol2-sec416-1112.xml` | `6562439cf114938ac43677490ec7c58013386404553faca351037e32b9fc31f5` |
| `CFR-2012-title20-vol2-sec416-1121.xml` | `5982d0f31630ac9180b0ddf3dfa3a7df90fec56720362e1819c980e9b1fa86e3` |
| `CFR-2012-title20-vol2-sec416-1124.xml` | `465b3c892e3b1367707b1d9608ebb4fef92aa7df0842e5f328e8e6c075153117` |
| `CFR-2012-title20-vol2-sec416-1161.xml` | `2f8f67dedde9925ed250aadb533804402e7f6446316547917ae213ec8071fc59` |
| `CFR-2012-title20-vol2-sec416-1163.xml` | `0ba9d9148b489929473a6e6a583f902151c11274525c6cb56b34cd9e03fd25fd` |
| `CFR-2012-title20-vol2-sec416-1205.xml` | `efe8165474b95cf94299534aca34c316c4622a3ebdb3db84b5ed49e8fcf25d23` |
| `CFR-2012-title20-vol2-sec416-1218.xml` | `a3ef5e7959fb53ca7cf3b23e9273eed0bfa3a2cdba05355d6824d2cfbba9c94f` |
| `CFR-2012-title20-vol2-sec416-1806.xml` | `fb22a2a8b3efc84ee259bba462271ab4aa6fc0f1abe475ecd7a50fdbd91cf4d8` |
| `CFR-2013-title20-vol2-sec416-1112.xml` | `83109d1f8a96490acf44a1b598577ebbf6eff161fdad4704d01337e45903b92d` |
| `CFR-2013-title20-vol2-sec416-1121.xml` | `83d897ff232ed77c2efe517e4cdb560d1aa8a7ad0a69d34185d295f32d06ba74` |
| `CFR-2013-title20-vol2-sec416-1124.xml` | `776b6028f50e10375af9d2d19fc91f8d630f3b4e9d410edba8b4407e64d04a52` |
| `CFR-2013-title20-vol2-sec416-1161.xml` | `bcfbaefdddcd21167ddeedf5e78c87f46653a81ecff2e6fe211bd44594ad58ba` |
| `CFR-2013-title20-vol2-sec416-1163.xml` | `e1185128a03d3b2fff5ce21582bb1f5b7b1ba8531f0063238d32a653dab2ddda` |
| `CFR-2013-title20-vol2-sec416-1205.xml` | `fecf128d1446504bbcbe8c0d082cfef4d334392bfe9a39c2ce200b3c054c19cf` |
| `CFR-2013-title20-vol2-sec416-1218.xml` | `82fd4b22573a38674d711cdc733a81cbfc779a2f6d3ec092b62852d057c0c64b` |
| `CFR-2013-title20-vol2-sec416-1806.xml` | `df8ba4c056cef5f76ddd27d0da6c612588db2cb3d6872b20d1c2616aecacc741` |
| `CFR-2014-title20-vol2-sec416-1112.xml` | `d69e58c628bdc3ddd4c68aa07e0363cff2c22156b31d524dbff17984c2b9211b` |
| `CFR-2014-title20-vol2-sec416-1121.xml` | `af2ed69d091f15bb2472f060c93e0292bba55a20176daf9e331a3cebb9ab1303` |
| `CFR-2014-title20-vol2-sec416-1124.xml` | `912dd10dff11c3878d0d83b1366bbd0afa7b1a57cbe1528f2613d5a94f86eb36` |
| `CFR-2014-title20-vol2-sec416-1161.xml` | `0ed8f149312d5c31f052a6f3af65a27aca082033dd2ed4c9930885cfdf7524ad` |
| `CFR-2014-title20-vol2-sec416-1163.xml` | `3e68c1a21abba53760139bc098d8ca6f6cf91d8d51798a2d981333a185962eb5` |
| `CFR-2014-title20-vol2-sec416-1205.xml` | `e896f64556a464e95f3b78653eac47ee6b8a894289730f5c4ff459a7ad640e99` |
| `CFR-2014-title20-vol2-sec416-1218.xml` | `605d753c32e611fab88c444cf2b8e4a1be48e630bbce0c9af01c624557db114e` |
| `CFR-2014-title20-vol2-sec416-1806.xml` | `d6f56d2e5ecf79eca5b64211b20a6f3e77ac2a1b369fcfb81d4a12f922a139b3` |
| `CFR-2015-title20-vol2-sec416-1112.xml` | `4e678f01d0e18707f2426a8ae679d846505db1a130e888a6369ef44e02e2b2e0` |
| `CFR-2015-title20-vol2-sec416-1121.xml` | `8795081fa5d6ae450526331e40302ede5e099e1cc2a1486a62757a04bacd6156` |
| `CFR-2015-title20-vol2-sec416-1124.xml` | `e412bc52433431159526f6f4dfcf1b0b99cd1a3a3db9e5ea4931ff3dd66dc4c5` |
| `CFR-2015-title20-vol2-sec416-1161.xml` | `7eb59293caee66140fe8555b82f1a7166976506a607db924c23fe3a82b502b4e` |
| `CFR-2015-title20-vol2-sec416-1163.xml` | `c836e029839a7c54df144993912c09d7b41be7d315680757252216c36bda57ea` |
| `CFR-2015-title20-vol2-sec416-1205.xml` | `60d7cd5fef22f510cbe0266e38abc2d130224f3d96f1599b47266e12a69c2e8c` |
| `CFR-2015-title20-vol2-sec416-1218.xml` | `4b1abcb19e66a9e37810f35f5db4dde3fddb7073e8069b08bd833fe5fa6e6690` |
| `CFR-2015-title20-vol2-sec416-1806.xml` | `52e7f82c7e91ed27d1315ad29067097a698490732fc7240072e5d238e60fc089` |
| `CFR-2016-title20-vol2-sec416-1112.xml` | `60561cd846f3e2ca62896b41c2c8ae971e047056f0e5834ce9538bd99400b434` |
| `CFR-2016-title20-vol2-sec416-1121.xml` | `4e670af438b9716ad169a8d2c5daab945a80a26904a232b53eb16a6d7e35d75d` |
| `CFR-2016-title20-vol2-sec416-1124.xml` | `cda86d4341093fb2663db6308dc8adc2229c109063a78f1a66c71e16f339f67b` |
| `CFR-2016-title20-vol2-sec416-1161.xml` | `14b0a68fb1ea2e293548eee0af596b71c0ba8ba37ccddbfd540ed11fc66441f5` |
| `CFR-2016-title20-vol2-sec416-1163.xml` | `4bcbd24f7a600e70f840f797658fdee7033564bb9cd9d5c920cc16759e32d424` |
| `CFR-2016-title20-vol2-sec416-1205.xml` | `22d4fc527fa9ef36f4f61cd54c18b40b075cda23ca25aedc8d9b853ba619629e` |
| `CFR-2016-title20-vol2-sec416-1218.xml` | `16bd4168413e0d933f43309204fe080361ad4102217c40f17f7f1a143070c184` |
| `CFR-2016-title20-vol2-sec416-1806.xml` | `74f1321ebdfb323f7b9f048bbd249845d0256b80a7a1866f58bd151612e506d7` |
| `CFR-2017-title20-vol2-sec416-1112.xml` | `5b3c9ee04093c62fb97f786b0eecef42bc7828722d14b6786071179fba71a041` |
| `CFR-2017-title20-vol2-sec416-1121.xml` | `af2bb483801c13f97cf68812856f44f39301a87cb3eb80e912aaaabb138f86d0` |
| `CFR-2017-title20-vol2-sec416-1124.xml` | `e653a7aa33a6bcf7f65549c0926913beadf321ec4500ac29819ce56c3b01bc6b` |
| `CFR-2017-title20-vol2-sec416-1161.xml` | `b00148b45228d93b7ffe94661c72b4bab60cb03ee90eca48f68ea6f0cfdae097` |
| `CFR-2017-title20-vol2-sec416-1163.xml` | `4bbacfede623db2527ebcb0b5cb2d9fc90b2199d0ab42b6fca4649229b1ad78a` |
| `CFR-2017-title20-vol2-sec416-1205.xml` | `17c00e89b1aa1e13898bc341e57ac9cc19131a61e6442b38e15ac2a152392280` |
| `CFR-2017-title20-vol2-sec416-1218.xml` | `ed1cb6742d196dfe6c7a4134a3ffa7c08f18088cb64476e2769772d10cbfdba3` |
| `CFR-2017-title20-vol2-sec416-1806.xml` | `b564034faabf8f704f4ea39943373d8584afb7ab0543e92402d60e32893942d7` |
| `CFR-2018-title20-vol2-sec416-1112.xml` | `07a625600691642e58cfd4fa22a5c858c15fef577bad4b2c7a2e1ed9463941ae` |
| `CFR-2018-title20-vol2-sec416-1121.xml` | `7b20d15e2eff95ba9509c66fa9cd96873ff8fb3b674e7860d9eb645dc4c251c5` |
| `CFR-2018-title20-vol2-sec416-1124.xml` | `cf23a4fe7f2d1eac3aeed343bcd8f5834c45541e5285606430ed5081b6fb73a0` |
| `CFR-2018-title20-vol2-sec416-1161.xml` | `f83125c90b742c600b51d768767c7b839329968bc52e3cfd08a9d1139b563786` |
| `CFR-2018-title20-vol2-sec416-1163.xml` | `ec3e0e8ec8551abd8f9bcb243ce41d414ae6def3d99736873c064dd5b493dce6` |
| `CFR-2018-title20-vol2-sec416-1205.xml` | `98516c9974fecf5a490aee1cc849193c916014f79d31a1c7e55870a11d213f68` |
| `CFR-2018-title20-vol2-sec416-1218.xml` | `80b6ffad30f912fa068ab1e48ffbfb87f930684dd6c44cd4e64078bad43cb9c6` |
| `CFR-2018-title20-vol2-sec416-1806.xml` | `41dae20e7e54283f516375dbe137eea418c481390916d302918d04215cc319d6` |
| `CFR-2019-title20-vol2-sec416-1112.xml` | `464b8f1425faea2d100cdb8e222a0939e058b430d67c9a7159a1cdd4d16d048d` |
| `CFR-2019-title20-vol2-sec416-1121.xml` | `a41ac724b7c9b73a3286aecc23a34af9c512ac707efa13cd8fb333b85a9b4a54` |
| `CFR-2019-title20-vol2-sec416-1124.xml` | `30d164cd500dcad4f86606403ed95d664a7a8fb4dd2bf69578e8af11e399802d` |
| `CFR-2019-title20-vol2-sec416-1161.xml` | `625bfb572e127ec90f8ad40b9f2a3e7fdb205ca7c2a754765596a24155da182a` |
| `CFR-2019-title20-vol2-sec416-1163.xml` | `f072032a1f0255ea74cb44405aec65e4732a178b3332362668ea27e313c080f3` |
| `CFR-2019-title20-vol2-sec416-1205.xml` | `c1c1893cddbc3c3687a1dbc87937b1fde801c59ff5cd26c418983289b4aedb08` |
| `CFR-2019-title20-vol2-sec416-1218.xml` | `17c63ccfa8b317addae6dec80990e649c400da6a0ab8ad74aa11229dadeb340c` |
| `CFR-2019-title20-vol2-sec416-1806.xml` | `a220efbf1191500ca90ec7fae6758bcc7ed249726d2edb86a02db40df845b0e7` |
| `CFR-2020-title20-vol2-sec416-1112.xml` | `4fd606f164727948dd13b7364c66aacde200c400f0eb9c7cb7f7d68bf237798f` |
| `CFR-2020-title20-vol2-sec416-1121.xml` | `1d05e92edd247c25b3eea8e078304b0fcfa69bfdacf3e6c041e4ff2edbe32b03` |
| `CFR-2020-title20-vol2-sec416-1124.xml` | `a575fc081f9a86779ec7ed760c142de86df68206225e8943d696498cdb23035c` |
| `CFR-2020-title20-vol2-sec416-1161.xml` | `35d154bb6ec3e2a5cf07b47bd1aee62a43d9efacc06b008fc16a2e8ffc55b0c1` |
| `CFR-2020-title20-vol2-sec416-1163.xml` | `ddcd31b6fcd673715fc04a149a52d302bb0e01e27c14d725c2bf487a546b74bd` |
| `CFR-2020-title20-vol2-sec416-1205.xml` | `387d5b7f778e998775053a26d06591bd1aab79a9611b6ccf6663eadb16a814d5` |
| `CFR-2020-title20-vol2-sec416-1218.xml` | `a9ac71dedb29a68a4d24216aec7773c4a8f85dd2be74a86216dc09c103b2ac4f` |
| `CFR-2020-title20-vol2-sec416-1806.xml` | `11fa5a8a1596528e62a074c0b37c10b48be31abaf563d36bf66d01bff6268a20` |
| `CFR-2021-title20-vol2-sec416-1112.xml` | `e89c8b3d1551d04fed7fc32cf298e05fa6343172a197826c2c48be969730b134` |
| `CFR-2021-title20-vol2-sec416-1121.xml` | `95e4ae35e61cd8557c1ad8423cb26eb40610525ce9585ca9fa3e0d285b34e4e6` |
| `CFR-2021-title20-vol2-sec416-1124.xml` | `86c3630410dbfadbdf2da729b6836fb4494603d590597da1f02725675a123b58` |
| `CFR-2021-title20-vol2-sec416-1161.xml` | `b6fa1e91f64eca1cf80da3854798f25ccada86799eaec212d1fdae957c62ac23` |
| `CFR-2021-title20-vol2-sec416-1163.xml` | `531441b6cfde848fd6cbdbf3fd448504eca29de54eb8c7a8ff47455fa1f18045` |
| `CFR-2021-title20-vol2-sec416-1205.xml` | `90d94e81a3be992aea6716b07d892b1f5bc6806b5b059c352ba59c5f5ba69d26` |
| `CFR-2021-title20-vol2-sec416-1218.xml` | `cdc23a513012003cd64aa9f7da19d5c6ee60698977131fcd53215e25fae00f95` |
| `CFR-2021-title20-vol2-sec416-1806.xml` | `1a5a866bdf1d63e97b4cf34a4f051979af252d71d19294213ebc6eb4aaa8e288` |
| `CFR-2022-title20-vol2-sec416-1112.xml` | `0fd5a56af4d5a258d980a03dbd5ae6a672c964c3f7980121c65a5869fc86edad` |
| `CFR-2022-title20-vol2-sec416-1121.xml` | `e30eba523f2cf39d7a0408489346266275edf919421398a4d66fc611b1f947e8` |
| `CFR-2022-title20-vol2-sec416-1124.xml` | `6a1287d0bc11dbf205b73ee0275804868499d93a4acdd5869ad39895d9514c36` |
| `CFR-2022-title20-vol2-sec416-1161.xml` | `64dfd528ea78e87e2f9b444e14c93d69655e0477eb8991a30b4634ced13bab3b` |
| `CFR-2022-title20-vol2-sec416-1163.xml` | `e60b70d2fc652ada9db1ede2e85b7721ce72ac6f03bbf24e6bd97c8d4c2273d6` |
| `CFR-2022-title20-vol2-sec416-1205.xml` | `02df752dce8f1ee8cb96668ba9ffc63fc2bf2b90a41d73832bacf211dc6effd1` |
| `CFR-2022-title20-vol2-sec416-1218.xml` | `afb518cb455136e1b068f052be28364481f52bd0406571fa03996e13a862c026` |
| `CFR-2022-title20-vol2-sec416-1806.xml` | `4503ac339756fb29a51382a68080979b60c0b5878210dd0712a9d652ff7e1848` |
| `fr_ssi_2012.html` | `13c161631f42b85d5c08bae0fcfd078792fc29081dcec06155b1d7466be3c55b` |
| `fr_ssi_2013.html` | `53dd828de99163cec069f3b398cfe9871c249863a1ecc1489528298060ce252a` |
| `fr_ssi_2014.html` | `a97ca41984de59d4ab7e1ebac91128d3de3d19141ec18072a1c8a4495b6deb29` |
| `fr_ssi_2015.html` | `98816a22e1e2380df24e6e1461ca4d7d376c44bc90c41874f22ccabd08ac0d32` |
| `fr_ssi_2016.html` | `668fabcce462eade1d1d8030295fee130e63ef908fdfd57f0ec481bc9a47bb65` |
| `fr_ssi_2017.html` | `efaba020476f8df6713f1c56c5963e53d24d6db76327c874439a2d58136f5bb8` |
| `fr_ssi_2018.html` | `bbff750f2bc36e279e12a5f89ce23dd582fc8cc52e322822af902f4336bc2f2e` |
| `fr_ssi_2019.html` | `058d1f78b6f7c19d567dac418a9a21ca853140e59438e724b05b4bc77e93e8e2` |
| `fr_ssi_2020.html` | `58ff9e9cf4ec28adb85801ec5f968a330237f33e212089e05e34853b4dbbebe0` |
| `fr_ssi_2021.html` | `b9a7c7e04ecf210153283a7ff1748ef4c9c336737c2e3f15435d4abbea211101` |
| `fr_ssi_2022.html` | `246c83ecda7d914833f385f4acbd8127a2b1426e0e6b35681d6d8650a030ac6b` |
| `policyengine_us/amount/couple.yaml` | `fa8d7cee418f6b4c02df757f2cc591936eb835efcdde17534dffd9d9d90e459e` |
| `policyengine_us/amount/individual.yaml` | `9dc3d2ed15f1f86e073e7ef06e06bd79c43d8d8b48419dcee87de25a5cdd0eaf` |
| `policyengine_us/eligibility/resources/limit/couple.yaml` | `341b821e70c50a269741152f2e616cc4dc0663bfeab5fcfe0ded1b32a316dfc9` |
| `policyengine_us/eligibility/resources/limit/individual.yaml` | `155d6728a2ae00ea5da441ada685ad638f21d1faaa8cadd0e991ef6a40b94cc7` |
| `policyengine_us/income/exclusions/earned.yaml` | `50bc791fec4bf24b444a394e23f5ad19b86f758e71739bfd17665b3c11a96f4b` |
| `policyengine_us/income/exclusions/earned_share.yaml` | `f9efb4c19445cbc5fc38dcbeabcde0920396365fb3ba5de4e29a93e469257ec6` |
| `policyengine_us/income/exclusions/general.yaml` | `dc77f88b148bd06771a267ab0775e80898043ec7581adea5b9431eff8267f9b1` |
