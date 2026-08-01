# Official PSID inventory registries — final report

Date: 2026-08-01  
Worktree: `/Users/maxghenis/PolicyEngine/social-security-model-worktrees/e11-inventory`  
Branch: `claude/ce-official-inventory`  
Design baseline: `13f84c99fb898eeaf70a8705bffacdf96e9795f4`

## State

**Blocked before either official registry blob.** The registered corpus removes
the missing-byte barrier, but it does not supply the complete, reviewed
questionnaire-slot taxonomy or the complete fixed-width token grammar that the
exact section 4.2 schemas require. Those schemas have no unresolved row
disposition. Emitting a partial, empty, reader-derived, inferred, or
`structural_missing`-by-default artifact would therefore be a false official
registration.

| Registry | Artifact blobs emitted | Lawful row count | Hard residuals from the 32 | Artifact SHA-256 |
|---|---:|---|---:|---|
| `psid_questionnaire_slot_specs.v1` | 0 | Not yet derivable | 7 | None — not emitted |
| `psid_covered_earnings_source_field_inventory.v1` | 0 | Not yet derivable; must equal the slot count | 13: the same 7 plus 6 fixed-width grammar gaps | None — not emitted |

“0 blobs emitted” does **not** mean either registry has a valid zero-row
artifact. Section 4.2 requires nonempty source-derived dimensions, a complete
expansion, and exact count/key hashes. Only 43 waves, 2 roles, and 35 purposes
are presently exact. The job-slot and questionnaire-component dimensions are
not established, so the only valid count equation currently available is

```text
expanded_slot_count = 35 × count(distinct source-derived questionnaire slots)
row_count = expanded_slot_count
```

The second factor is unknown. The 89,599 physical codebook fields and the
3,123 modern reader fields are not lawful substitutes for a questionnaire
slot universe.

## Controlling design laws

The operative design is revision 5 at the baseline commit above. Its full
file SHA-256 is
`eb24a36f4baa124f192e99f517982e7e723ca7e899957cd0acf02cf2d7e4a1ed`.
Section 17.1 changes only enumerated V-B source/design clauses and leaves all
other sections 1–16 controlling
([§17.1, lines 21689–21724](docs/design/covered_earnings_correction.md#L21689)).

### Slot-specification registry

Section 4.2 requires all of the following
([lines 706–807](docs/design/covered_earnings_correction.md#L706)):

1. The crosswalk cannot define its own completeness universe. A source-only
   extractor may read only registered PSID setup, layout, label,
   codebook/questionnaire, and fixed-width identities, with every source
   document bound by path, full SHA-256, and size (lines 706–718).
2. The registry is **independently ratified**. Its top-level object has exactly
   these 12 keys: `schema_version`, `artifact_id`,
   `source_authority_manifest`, `interview_waves`, `roles`, `job_slot_ids`,
   `questionnaire_component_slot_ids`, `field_purposes`, `expanded_slots`,
   `expanded_slot_count`, `expanded_slot_keyset_sha256`, and
   `canonical_order`. Both identity literals are
   `psid_questionnaire_slot_specs.v1` (lines 720–729).
3. The source-derived dimensions cover all 43 family interview waves
   `1968..1997,1999,2001,...,2023`, both roles, every questionnaire-defined
   job plus role-total/farm/business aggregate slots, every remuneration or
   context component, and the exact ordered 35-purpose array (lines 729–785):

   ```text
   interview_and_role_attachment, amount, reporting_unit,
   month_or_exposure, assignment, employee_self_or_mixed, incorporation,
   government_level, industry, occupation, enrollment, job_identifier,
   state_of_residence, section_218_group, section_218_position,
   public_retirement_system_participation, federal_retirement_system,
   federal_service, railroad_covered_employer, railroad_covered_service,
   ministerial_service, clergy_remuneration, church_employee_service,
   religious_order_service, clergy_or_religious_exemption,
   domestic_service, agricultural_service, election_work, family_service,
   casual_service, foreign_government_service,
   international_organization_service, nonresident_alien_status,
   employer_school_nexus, statutory_student_service
   ```

4. Every expanded row has exactly 12 keys: `source_inventory_key`,
   `questionnaire_slot_id`, `interview_wave`, `earnings_reference_year`,
   `role`, `job_slot`, `questionnaire_component_slot`, `slot_kind`,
   `field_purpose`, `questionnaire_presence`, `source_document_ids`, and
   `source_locator_sha256s`. Presence is only `asked |
   structural_query_slot`; slot kind is only `remuneration_component |
   role_total | farm_aggregate | business_aggregate | context_only`; both
   source arrays are ordered and nonempty (lines 787–800).
5. `source_inventory_key` is `psid-slot:` plus the canonical SHA-256 of
   `[wave, reference_year, role, job_slot, component_slot, slot_kind,
   purpose]`. `questionnaire_slot_id` uses the same tuple without purpose and
   the prefix `psid-questionnaire-slot:`. Stored dimension order controls the
   canonical expansion; the complete unique key stream controls the count and
   hash (lines 800–807).

### Source-field inventory

Section 4.2 separately requires
([lines 809–901](docs/design/covered_earnings_correction.md#L809)):

1. The exact path is
   `data/external/psid_covered_earnings_source_field_inventory_v1.json`; its
   schema and artifact literals are respectively
   `psid_source_field_inventory.v1` and
   `psid_covered_earnings_source_field_inventory.v1` (lines 706–718).
2. The top level has exactly 9 keys: `schema_version`, `artifact_id`,
   `questionnaire_slot_specs_identity`, `source_authority_manifest`, `rows`,
   `row_count`, `row_keyset_sha256`, `canonical_order`, and `integrity`.
   The slot identity has exactly 5 keys: `schema_version`, `artifact_id`,
   `sha256`, `expanded_slot_count`, and `expanded_slot_keyset_sha256`. It
   binds the separately ratified slot blob. The authority manifest is an
   exact deep copy; counts, ordered keys, key hash, and canonical order must
   match positionally (lines 809–826).
3. Every wave×role×job×component/context×purpose key has exactly one row with
   these 24 keys: `source_inventory_key`, `questionnaire_slot_id`,
   `interview_wave`, `earnings_reference_year`, `role`, `job_slot`,
   `questionnaire_component_slot`, `slot_kind`, `field_purpose`,
   `source_disposition`, `raw_field_ids`, `exact_label_texts`,
   `full_source_descriptions`, `value_code_map_id`, `value_code_map`,
   `typed_parse_specs`, `reporting_unit`, `reference_periodicity`,
   `information_date_basis`, `source_file_ids`, `source_byte_sha256s`,
   `layout_coordinates`, `missing_raw_tokens`, and `absence_proof`
   (lines 828–842).
4. Reference year is always interview wave minus one. Disposition is only
   `present | structural_missing`. A present row requires complete labels,
   descriptions, code maps, parse specs, timing, source coordinates, and
   exact missing-token grammar. A structural-missing row must empty every
   source/parser/token array and carry a nonempty exhaustive absence proof.
   Unknown evidence cannot be relabeled as structural absence. A missing or
   duplicate key, unscanned column, undesignated raw code, source drift, or
   wave/year mismatch aborts (lines 844–874).
5. `typed_parse_specs` is positional with `raw_field_ids` and has the exact
   nine-key grammar at lines 876–893. Parsing is exact-width ASCII and exact
   rational arithmetic; whitespace trimming, locale conversion, floating
   point, coercion, and inferred units are forbidden.
6. `integrity` has exactly `canonicalization`, `content_sha256`,
   `extraction_implementation_commit`, and `reproduced_from_source_bytes`.
   Canonical JSON and the zero-self content hash follow §6.1
   ([lines 1924–1935](docs/design/covered_earnings_correction.md#L1924));
   ingestion must reject duplicate JSON keys, nonfinite numbers, noncanonical
   bytes, and malformed types under the strict-parser law
   ([lines 5426–5439](docs/design/covered_earnings_correction.md#L5426)).
   Semantic arrays retain their declared order
   ([lines 5738–5745](docs/design/covered_earnings_correction.md#L5738)).

### Ordering and foreign-key closure

- Slot rows and inventory rows are positional one-to-one; both key hashes and
  both counts must agree (section 4.2 lines 809–832).
- Structural-missing consequence rows are exact one-for-one inventory foreign
  keys; the six executable rule registries are nonempty, ordered
  lexicographically by their first ID, contain exact inventory foreign keys,
  and permit no unreferenced rules
  ([lines 1087–1135](docs/design/covered_earnings_correction.md#L1087)).
- Amendment 2 adds exact questionnaire-component-slot foreign keys for the SE
  aggregation domain
  ([lines 11310–11341](docs/design/covered_earnings_correction.md#L11310)).
- V3 inherits the exact inventory/order binding. Every named prerequisite blob
  must already be immutable in the single-path crosswalk commit's parent and
  remain byte-identical through the authority cutoff
  ([lines 12149–12183](docs/design/covered_earnings_correction.md#L12149)).

## Controlling registered authorities

| Authority | Raw SHA-256 | Content/canonical identity |
|---|---|---|
| Codebook adjudication | `df73026bcf649d12ecb606501d64780f41567b6dc09d7029f9191111cab09c62` | content `359c7edac8c0b331c1a4d2a77ad2945974fa033e50e104d866e48b39a45b5a84`; canonical identity `518f25891172109e8f5ffd18ae09b2a9b16f73723f8d630b4e7c65177c86ab6f` |
| Corpus registration attempt | `07c5bad57d702416da7ee668f504646ba85b9868a7f38819cdec85638c97558c` | content `4c91ae30ef8b7ab8c776d4372a4717e7352913e8dd825ba85181ff02b11cef27` |
| Accepted nested corpus registry | carried by the registration blob | content `c82304267d254e81ab5d7e7e198f89d09056700a7429d7fcfa32fdab6bb99b03`; rows `fa4125a3f1d175628a1ab76dec43edde02960c2e0687b7a6ab9b7d90708133f3` |
| Questionnaire extraction | `5fb39a0ada3ccb0da0883e4db7bb6b36edeb60865d90ed061bc0b74e1fd12347` | content `18ec2e023152d179de68d72ebf1966549a6e46ef48743aa9ec607f565de3128c` |
| Questionnaire closure attempt | `00c4fb1e671503406dfec55d80b29379ad12f7b8bf330dfe74895724ab19a46c` | content `47c15dfe9018a4ae91c4f409378d2b85c3cdecf442c1ee752d8f7e8e3b125249` |

The accepted registry is `pass` for 456/456 documents and 455 unique document
identities. All staged files were re-hashed successfully without network
access. The 43 family questionnaires total 116,305,750 bytes and 5,692 pages.
Merge #345 is `c1899c9e3f156c411a6e62d2d9b57514c0d6bb2e`.

This proves document identity and availability. It does not itself assert a
job/component taxonomy, page-level positive attachment, exhaustive negative
domain, or fixed-width grammar. The committed semantic extraction is expressly
human-verified and contains 61 hard-coded passage locators, 37 whole-document
locators, 3 absence proofs, and only 8 targeted residual extractions. It
contains no `job_slot_ids`, `questionnaire_component_slot_ids`,
`expanded_slot_count`, `psid-slot:` keys, or complete source-locator expansion.

## Residual accounting: 32 = 7 resolved + 25 surviving

Every byte interval below is half-open and refers to the raw canonical file.
The codebook rows are in
`data/external/psid_codebook_inventory_adjudication_v1.json` under
`/registration_required_residuals/<index>` and inherit that file's full SHA
above. Questionnaire conclusions are in
`data/external/psid_questionnaire_corpus_extraction_v1.json` under
`/psid_vb_residual_extractions/<index>` and inherit its full SHA above.

### Seven resolved by #345 plus Amendment 3

| Original index | Resolution | Exact extraction-row locator |
|---:|---|---|
| 3 | Early occupation/industry meanings, attachment, and bounded unsupported-slot absence closed by `vb5_occind_p2..p6`, `vb5_codes_p649..p657`, and `vb5_1968_1975_unsupported_slot_absence`. | extraction row 0, bytes `[54182,55457)`, SHA `3dd2de0c1f9857d1ba8504cc8d6547d2d835ca324a48bd4ca9184145dd1d9632` |
| 6 | V5289/V5788 established as Wife wage/labor-income totals, with family-business labor/asset handled separately. | row 1, `[55458,56373)`, `626566e3e02e144915de06970551bae7c633654ae4f152541982bbd974925228` |
| 7 | Equivalent 1977/1978 Wife current-job context is structurally absent over the reviewed Wife-section domain. | row 2, `[56374,57438)`, `585cb29308eaec4bd0c6c82473ac189a121c062e6668080dbcf4e057e5260dd7` |
| 8 | The 1976 government item is only combined yes/no; no federal/state/local level is supplied by that branch. | row 3, `[57439,58278)`, `7c19da19118675188d002e963e988b47f50dd8e1e6573046ed1eebfd43d051e0` |
| 23 | 2013/2015 current-regular-school branch freshness closed. | row 5, `[59574,60732)`, `26faca530e23bbe66b191a2e6b36eefb28de7d10062da3361e866ac04c8d61fa` |
| 24 | Pre-2013 current-regular-school absence closed over the enumerated 1968–2011 questionnaire domain. | row 6, `[60733,61767)`, `92f2da832e559fa4cac9989d6165f0ceee31b67eaee2b36d6e5e5a2f1fcad253` |
| 31 | 2017/2019/2021/2023 branch freshness closed. | row 7, `[61768,62999)`, `7b4b28ceed67a4d3562a438dd97a2e5a8b718de9bdf5f7b70c584a383bd6024d` |

### Seven surviving slot-registry blockers

| Index | Residual and reason | Exact adjudication-row locator |
|---:|---|---|
| 1 | Early complete role/job/component/context hierarchy is not extracted. | `[1389605,1390112)`, `30a21ee27768f54232b18bb154e176094fdd29b94eca422bf44ea89d84ec39d1` |
| 2 | Early exhaustive absence for every unsupported job, component, context, and 35-purpose slot is not proved. | `[1390113,1390637)`, `6238c9dd4d01d830fe402b9ec3f15cc3abbf874b6122e84ccdefa70f195029bc` |
| 5 | 1976–1978 complete questionnaire-slot hierarchy and absence domain are not extracted. | `[1391742,1392220)`, `54091c19c5bcd11d4fac5a594ee0439d6e19578b7c34a01265ce692c78078395` |
| 11 | 1979–1993 complete questionnaire-slot hierarchy and absence domain are not extracted. | `[1395139,1395666)`, `0982136914a7cbed44c0ab644ff8b772bd911c4c3bb4f9a492cb62ae21138d08` |
| 14 | 1994–2001 complete questionnaire-slot hierarchy and absence domain are not extracted. | `[1396647,1397129)`, `5ab81ea5492a44b08b6756078954a315bf1c92f93aff91be002606232ae11c1d` |
| 18 | 2003–2015 complete questionnaire-slot hierarchy and absence domain are not extracted. | `[1398536,1399021)`, `54c73b57548bfd7f3e340a296b9904aab90dacd5d1dd7d986cf24e382903b9c7` |
| 26 | 2017–2023 complete questionnaire-slot hierarchy and absence domain are not extracted. | `[1402952,1403432)`, `f2cb59d1f99da24f392ce7d9ccf7f61cfd54c9b4dd77a239ee826f12c842a5ba` |

#345 did not target any of these seven. Its early absence proof is limited to
occupation/industry cells; its whole-document domain covers 37 questionnaires
through 2011, while later waves have selected passages. Generalizing either
scope to the complete slot universe would violate the absence-proof law.

### Six additional source-inventory blockers

These are era-wide exact fixed-width padding/sign/blank/sentinel grammar gaps.
They cannot be omitted, and a present row cannot carry unknown
`missing_raw_tokens`.

| Index | Waves | Fields searched | Explicit-missing fields / missing rows / unobserved rows | Exact row locator |
|---:|---|---:|---:|---|
| 0 | 1968–1975 | 3,868 | 2,555 / 4,358 / 159 | `[1389087,1389604)`, `02f97ac723adba1e94c2c8e14d73711380fb4df9541bd7580d1e302508eb9e36` |
| 4 | 1976–1978 | 1,838 | 1,507 / 2,807 / 164 | `[1391253,1391741)`, `b64a53597423bf9fb2f0b500a4358c89a5e65c831b6258d521976ad39496748a` |
| 10 | 1979–1993 | 15,745 | 14,180 / 28,211 / 2,657 | `[1394601,1395138)`, `06e797c7c4d113dc58ea7f7584ed1a3ef9501e50b4e40c56360811343f5debbc` |
| 13 | 1994–2001 | 15,983 | 15,517 / 40,372 / 11,163 | `[1396154,1396646)`, `679bf2376c235642f6957269616f97750f1c0e4c32acf1e45e964f08c651d7c0` |
| 17 | 2003–2015 | 33,154 | 31,777 / 82,019 / 25,174 | `[1398040,1398535)`, `065352bd6fd8a2da1a3734f3b0f1d419f8598474319628c6819ebb4a3835654b` |
| 25 | 2017–2023 | 19,011 | 18,327 / 45,537 / 12,619 | `[1402461,1402951)`, `8ed0001daecfe3338bf353122f811829a4139342a8b1648918197a71ec0b30cb` |

The setup audit found no SPSS `MISSING VALUES` declarations. Raw-file
observation cannot prove an allowed but unobserved token, and actual padding
varies by field width. Generic zero/8/9 conventions in later PDFs do not
exhaustively define every short wild code, signed/decimal token, blank, or
zero-frequency sentinel. The questionnaire extraction contains no fixed-width
grammar work.

### Twelve surviving downstream-only residuals

These remain honest residuals for later rule registries/crosswalk work. They
do not themselves require falsifying a raw source-field row, but they remain
part of the requested 32-row accounting.

| Index | Reason | Exact adjudication-row locator |
|---:|---|---|
| 9 | Partial only: no captured instruction gives the exact V4901–V4906 allocation to annual V4379/V5289/V5788 totals. | `[1393832,1394600)`, `ded6129ea010adc905233ed74e615f5bb1d9f1de7c7d831045ec3b7474c91172` |
| 12 | RY1978–1982 labor/asset split, spouse farm/business inclusion, and V8690 composition remain unresolved. | `[1395667,1396153)`, `6fcb2566511110d5cff454c223d0b198461dced9b3bab88af0c4f0ecefe82ed1` |
| 15 | ER-transition role-specific farm-labor allocation is unavailable. | `[1397130,1397587)`, `8b8681258508cf7eb95dcac4a19ac6e15d303e9ec0d5038efd991d882a2b2630` |
| 16 | ER-transition edited-total/component reconciliation is unavailable. | `[1397588,1398039)`, `c776206313897bab4c4b7e6bfc0eb53b43e235f426a122470e96bdd4e322a447` |
| 19 | Modern job chronology/exposure-to-stable-job attachment is unavailable. | `[1399022,1399534)`, `5a3bcb404d56440ad25e00117a36d18ff7517b67bee7280aadf75dfb411bb99d` |
| 20 | Modern job amounts/overtime-to-role-total reconciliation is unavailable. | `[1399535,1400010)`, `4fd2b0521f786faecbbbf6712350e4b3f1403f90d75130c2655004e2d4629863` |
| 21 | Modern role-specific farm-labor allocation is unavailable. | `[1400011,1400543)`, `320f4af3908734ce3ea0e22b837c2d074224f49670e3fe9f23ead19aa14d3095` |
| 22 | Modern edited-total/component reconciliation is unavailable. | `[1400544,1401014)`, `3077bbf6b8abf2c5d508ec1611c006d896a24782ab1872268c3f9b9279252a7f` |
| 27 | Postcutoff job chronology/exposure-to-stable-job attachment is unavailable. | `[1403433,1403913)`, `a2da228dd631ec6d52583e6d7235b859be1cd555f46c8de4b667be05aacf2eee` |
| 28 | Postcutoff job amounts/overtime-to-role-total reconciliation is unavailable. | `[1403914,1404384)`, `3f83f7588893e27c1184a984666ab97b6ec8ea3123c193dfd6c8c08d2fb69a30` |
| 29 | Postcutoff role-specific farm-labor allocation is unavailable. | `[1404385,1404769)`, `f13c5894fb41793ff90def62cb1b08faff142685f1061a3495225e7696d9ec43` |
| 30 | Postcutoff edited-total/component reconciliation is unavailable. | `[1404770,1405235)`, `317813fd5568a60cbbd6f891817379986e4682a3fb91a4fad435af28e65bb550` |

## Critical covered-earnings slot status

The design's 43 interview waves imply earnings reference years 1967–2022.
The wage, self-employment, farm, and business-labor domain is **not certified
complete** across that interval:

- Early edited role totals are source-established: 1968 V74/V75; 1969
  V514/V516; 1970 V1196/V1198; 1971 V1897/V1899; 1972 V2498/V2500; 1973
  V3051/V3053; 1974 V3463/V3465; and 1975 V3863/V3865. Head totals are mixed
  and spouse remuneration is not decomposed. No wage/SE split was inferred.
- At the spouse seam, V4379/V4382 establish a mixed RY1975 concept and #345
  establishes V5289/V5788 as Wife wage/labor totals. The 1976 current-context
  fields V4844/V4845/V4850/V4855/V4858 are present, but the exact
  V4901–V4906 allocation remains residual 9.
- Pre-ER role-total pairs are preserved as source facts from V6767/V6398
  through V23323/V23324. The RY1978–1982 split/inclusion and V8690 composition
  remain residual 12; no component allocation was fabricated.
- ER and modern wage-type role totals and person-specific business-labor
  fields are present. Examples include ER4140/ER4144 with shared farm ER4117
  and business ER4119/ER4141; ER24116/ER24135 with business ER24109/ER24111;
  and ER85496/ER85524 with farm ER85475 and business ER85477/ER85505. Farm is
  shared/combined and cannot be allocated by role under residuals 15/21/29.
  It must remain an aggregate source fact, never a fabricated role amount.
- Edited-total reconciliation and modern/postcutoff stable-job attachment
  remain residuals 16, 19–20, 22, 27–28, and 30. They belong in the later
  reconciliation/job-match registries, not in invented source facts.

Thus the critical fields are explicitly residual where required. Positive
field evidence does not cure the missing all-slot taxonomy or token grammar.

## Locator discipline for future rows

No official row exists, so no row citation was fabricated. A future builder
must preserve the established unit-1b discipline:

1. For codebook facts, retain `codebook_field_keys`, join every
   `source_locator_id` to the evidence artifact's `/source_locators`, and
   preserve document ID, exact byte start/end, range SHA, page/layout object,
   path, full-file SHA, and size.
2. For questionnaire positives, join evidence IDs to `/passage_locators`,
   which already bind full-file SHA/size plus exact byte range and range SHA.
3. For absences, join each named `/absence_proofs/*/searched_locator_ids` to
   its whole-document or passage locators and retain its exact reviewed scope.
   A narrow absence proof may never be generalized.
4. Registration candidates are full-file locators. Canonical row hashes in
   this repository include the trailing LF where the governing artifact law
   requires it.

## Builders, validators, tests, and tier counts

No target builder or artifact was added because no exact domain exists to
render or validate. The current source-only implementation affirmatively
refuses both outputs rather than inventing them
([`psid_questionnaire_inventory.py` lines 2019–2057](src/populace_dynamics/data/psid_questionnaire_inventory.py#L2019)
and [lines 5021–5040](src/populace_dynamics/data/psid_questionnaire_inventory.py#L5021)).
Existing artifact and mutation tests freeze that refusal. Once the missing
authority exists, the house pattern is strict parse → exact schema/type/domain
validation → zero-self canonical hash → byte-reproducible render → committed
artifact/mutation/reproduction tests.

Verification performed with
`/Users/maxghenis/PolicyEngine/social-security-model/.venv/bin/python`:

- Complete focused PSID codebook/questionnaire inventory, corpus extraction,
  corpus registration, and closure suite: **182 passed**.
- Broader pinned authority plus covered-earnings registry suite: **282 passed**.
- Collection-wide tier-policy selection: **1 passed, 4,470 deselected**.
- Full collection: **4,471 tests**.
- `tests/tier_counts.json` remains synchronized: `unit` 902, `artifact` 2,075,
  `integration_psid` 815, `reproduction_legacy` 520, and
  `oracle_policyengine` 159.
- A broad run was stopped at 54% after 28 minutes: 2,437 passed, 26 skipped,
  and 2 failed because the required shared virtualenv's editable install
  resolved package/Git roots to the main checkout rather than this worktree.
  Re-running those exact two tests with this worktree's `src` first on
  `PYTHONPATH` gave **2 passed**. Neither failure touched the PSID authority
  or registry code.
- `/opt/homebrew/bin/ruff check .`: **all checks passed**. No Python file was
  changed, so no formatting or tier-count mutation was applicable.

## Exact ratification path

**Yes, the exact registry bytes require referee-gated/separate review before
the v3 crosswalk may cite them.** The procedural law is:

1. Section 4.2 calls the slot registry “independently ratified” and requires
   the inventory identity to bind that **separately ratified** slot registry
   (lines 720 and 813–816).
2. Section 14.3 step 2 requires a separate **referee-gated
   authority/extraction PR** containing the slot registry, source inventory,
   dependent registries, crosswalk, builders, and offline rejection tests
   ([lines 8064–8108](docs/design/covered_earnings_correction.md#L8064)).
3. Section 16.10 step 4 requires every separately reviewed prerequisite
   registry to be merged and Git-tracked before the separately reviewed,
   single-path v3 crosswalk commit
   ([lines 14854–14884](docs/design/covered_earnings_correction.md#L14854)).
4. Section 16.5.1 then requires every registry identity named by the crosswalk
   to resolve to its exact immutable blob/digest in the crosswalk commit's
   parent and remain unchanged through the authority cutoff (lines
   12171–12183). Section 17 does not relax this order.

To the literal question about a referee round **between** these registries and
the nine dependent registry candidates, the answer is **no additional serial
round is expressly required**. Section 14.3 permits one referee-gated
authority/extraction package to contain both official registries and the
dependent registries that foreign-key them. The exact candidate targets must
resolve during that review. The answer is nevertheless **yes** that referee
approval is required before those bytes can become merged official immutable
prerequisites and before the v3 crosswalk can cite them. The design requires
the slot registry's independent ratification, the inventory's exact binding to
it, separate review of every prerequisite, and immutable Git identities before
the v3 crosswalk commit. A new exhaustive extraction may be authored in this
lane, but it cannot self-declare these official blobs ratified or authorize the
dependent crosswalk chain without that review/merge procedure.

## Next authorized work

1. Perform a new exhaustive source-only, human-reviewed extraction of all 43
   questionnaire flows (5,692 pages), reconciling QxQ/codebook/layout sources
   into a complete job/component taxonomy with exact positive locators and
   exhaustive negative-domain proofs.
2. Establish per-field fixed-width padding, sign, decimal, blank, and sentinel
   grammar across all six eras; preserve unresolvable tokens as registration
   blockers rather than observing/inventing a value.
3. Build and separately review the complete slot registry, then render the
   positionally identical source inventory from that immutable identity with
   strict parser, canonical renderer, SHA pins, mutation rejections, and
   reproduction tests.
4. Carry the 12 downstream allocation/reconciliation/job-attachment residuals
   into their proper separately reviewed rule registries and crosswalk work.

No PR, crosswalk, dependent registry, or production artifact was created.
