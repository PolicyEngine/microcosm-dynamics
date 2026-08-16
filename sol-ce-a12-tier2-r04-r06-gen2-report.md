# A12-T2-R04/R05/R06 generation-2 certification ceremony report

## Status

**INTERRUPTED** — live execution checkpoint after Stage 1. This status is
replaced at Stage 7, or earlier if an enacted fail-closed condition requires a
lawful stop.

No Q5 input, authority, full G17-C01 row, production output, or other
forbidden downstream object has been emitted.

## Ordered plan and disposition

| Stage | Required operation | Disposition |
|---|---|---|
| 0 | Reauthenticate revision-20 operativity, read the controlling law and precedent, fingerprint the checkout, and resolve the former revision-binding gap. | Complete. |
| 1 | Reconstruct the exact 279-row build-input domain and reauthenticate all six source comparands. | Complete. |
| 2 | Implement the independent `R04X-7F2A` builder. | Pending. |
| 3 | Implement the independent `R04X-C91D` validator and its static/runtime independence audits. | Pending. |
| 4 | Build, commit, and publicly validate the fixed-path R04/R05 certificate. | Pending. |
| 5 | Execute every inherited and Amendment-18 mutation attack. | Pending. |
| 6 | Reproduce the Amendment-11 expected abort in the enacted sandbox and first-add the durable R06 result. | Pending. |
| 7 | Run pinned and full verification, formatting and hygiene; finalize this report. | Pending. |

Each stage is one topology-preserving commit. The fixed R06 result will not be
first-added until the committed R05 certificate passes from a strict-ancestor
commit.

## Stage 0 — reconnaissance and revision binding

### Checkout fingerprint

- Branch: `sol/a12-tier2-r04-r05-r2`.
- Starting `HEAD`: `ae68be83dc564e8ce49d725fffa8621c857f5446`.
- Starting tree: `420f1e1c295d0bdd0da00b88f666f355d427379e`.
- Sole parent: `0262efacf88e86771e31910102d083824354bc2e`.
- `HEAD` and `origin/master` selected the same revision-20 commit at
  reconnaissance time. The local `master` branch label was stale and was not
  used as an authority.
- The only pre-existing untracked ceremony-support paths were
  `.ceremony-log/` and `CEREMONY_PROMPT.txt`; both are preserved and excluded
  from governed commits.
- Revision-20 design: mode `100644`, 3,964,278 bytes, Git blob
  `016c0fff757b54da730ae0044216416cde2d2c33`, raw SHA-256
  `631d3b2b8ecab1c29ec0595550a6d2b798f49ff96e74c722801d24c48ab111ec`.
- Amendment-18 closure: mode `100644`, 842 bytes, Git blob
  `19855c8d3f2cf2322d35fa67a330e96fc1afa913`, raw SHA-256
  `0080de3cc529d2f732835316a5566e58c887a9bd7592259acfe35ecaa3813fca`.

### Controlling law and precedent

The controlling text was read in the required order: §32 in full; §29.4 and
§29.5.2 as composed by §§30–32; §26.11.2; and §27.2.3. The generation-1
Stage-0 report, the ordered R03 archive/master witness, and the revision-20
registry state were also inspected. Design bytes, `gates.yaml`, `runs/`, and
all committed ceremony artifacts remain immutable.

The source-member boundary is the prospective G17-C01
`hierarchy_annotation_authority` subpayload only. Certification remains
pre-Q5 source-only NONAUTHORITY. R06 must reproduce the independent
Amendment-11 abort and terminate at `A19_SUCCESSOR_PROGRAM_STOP`.

### Public-oracle result

The unmodified public `validate_ratification_operativity()` was called from a
clean revision-20 checkout. It completed full pin, Git, artifact, and design
verification and returned the ordered closure domain:

```text
revision=20
ordered_domain=(13, 14, 15, 16, 17, 18)
closure_count=6
selected_position=2
selected_amendment_number=15
```

This exactly satisfies §32.3: `20 >= 18`, and the domain deep-equals
`tuple(range(13, 20 - 1))`. Only after the complete current snapshot passed
was the historical Amendment-15 closure selected at zero-based position 2.

### Revision-binding memo

The generation-1 stop is conclusively resolved. Section 32.3 expressly
supersedes the revision-17/revision-18-literal R05 locator and requires the
complete current terminal snapshot at every revision `R >= 18`, followed by
selection of Amendment 15 at proved position 2. It forbids a historical
loader, caller-supplied or cached snapshot, closest-revision fallback,
partial A15-only validation, and a fixed current maximum.

The serialized 11-key historical Amendment-15 binding is unchanged; the
enclosing current revision is deliberately not serialized. Revision 18
remains the required historical first-operativity ancestor, while the
certificate first-add must also descend from the current operative
revision-20 state. There is therefore one mandatory execution and no residual
composition choice.

### Environment and baseline reference

- Required setup was attempted with `uv venv --allow-existing` and
  `uv pip install -e ".[dev]"`.
- The sandbox forbade the default `~/.cache/uv` write, so `UV_CACHE_DIR` was
  relocated to `/private/tmp`. Package resolution was then blocked by the
  sandbox's intentional DNS/network denial.
- The worktree was linked to the repository's shared ratification environment
  and all Python/test commands use `uv run --no-sync`; Python is 3.14.4 and
  pytest is 9.1.1. Repository-global `black` and `ruff` executables are
  available for Stage 7.
- The controlling repin baseline reference is 5,571 passed, 91 skipped, and
  the same two known historical failures. Stage 7 will compare a fresh full
  run against that fingerprint rather than treating either historical failure
  as a ceremony regression.

## Stage 1 — build-input domain

The complete §32.2 envelope was constructed ephemerally and was not written
to the repository. The reconstruction authenticated the two Git-root
artifacts, all four registered questionnaire-capture inputs, both complete
upstream disposition relations, every included source file under
`/Users/maxghenis/PolicyEngine/psid-data`, and every one of the 22
repair/seal/evidence paths against both `HEAD` and working bytes.

The source projection had exactly these role counts:

| Role | Rows | Authenticated bytes |
|---|---:|---:|
| `questionnaire_flow` | 81 | 1,226,736,045 |
| `dictionary_layout` | 86 | included below |
| `codebook` | 47 | included below |
| `raw_fixed_width_data` | 43 | included below |
| Three field-source roles combined | 176 | 1,514,409,083 |
| Complete source domain | 257 | 2,741,145,128 |

The questionnaire link dispositions reproduced `81 / 1 / 383` for included,
out-of-wave 2025, and other. The accepted-document dispositions reproduced
`81 / 1 / 374`. All 81 selected documents and all 176 field-source files
were regular, nonsymlink files whose complete bytes matched their registered
sizes and SHA-256 values.

The six enacted comparands were freshly recomputed, not copied:

| Comparand | Derived value |
|---|---|
| `questionnaire_document_count` | `81` |
| `questionnaire_document_keyset_sha256` | `3326c9ba70b7f83f19b0ea934630d26ced73f230be1628cb74031d17160cb1a5` |
| `questionnaire_document_domain_sha256` | `b06139b147391d06b4f90a8f28de472a936ec08b3e9eb37001a5a70e2b3c3543` |
| `source_document_count` | `257` |
| `source_document_keyset_sha256` | `8b7cad855b791c5cd7d235a74d4a0f1ecc7511dc0458db11d6b04c1b6af2c36a` |
| `source_document_domain_sha256` | `9d7a98db7c2889eba150f70935f492aebbc41cd521e4139dc1ec886ecd9945ce` |

The 22 repair/seal/evidence identities totaled 4,345,235 bytes. Their paths
were sorted once by unsigned UTF-8 and reproduced path-array SHA-256
`504159116708ee4d5e2cc8abec130ca8679d22cce928dca42af12be305361c17`.
The final class boundary was exactly 257 `source_document` rows followed by
22 `repair_seal_evidence` rows.

Python sorted-key, compact, ASCII, no-NaN serialization with one terminal LF
produced exactly 168,504 envelope bytes and the newly derived digest:

```text
tier2_build_input_domain_sha256=
f34ced6e80e1bf72e68635b4f729c5b983c094fd25d16105a6c161ccd52fff63
```

The envelope itself remains ephemeral as §32.2.3 requires.

## Stage 2 — `R04X-7F2A` builder

Pending.

## Stage 3 — `R04X-C91D` validator

Pending.

## Stage 4 — committed R04/R05 certification

Pending.

## Stage 5 — mutation census

Pending.

## Stage 6 — durable R06 expected-abort result

Pending.

## Stage 7 — final verification and hygiene

Pending.

## Exact resumption commands for this checkpoint

```sh
cd /Users/maxghenis/PolicyEngine/social-security-model-worktrees/a12-t2-r04-r2
git status --short --branch
git log --oneline --decorate -3
UV_CACHE_DIR=/private/tmp/a12-t2-r04-r2-uv-cache \
  uv run --no-sync python -m pytest -k amendment18 -ra
```

Resume at Stage 1 only if the Stage-0 commit remains the unique tip and the
public oracle again returns `(13, 14, 15, 16, 17, 18)`.
