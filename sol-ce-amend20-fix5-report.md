# Amendment 20 fix-5 report

**NONAUTHORITY · defensive validation-law drafting · 2026-08-20**

## Outcome

Fix-5 enacts the chartered three-cure delta without instantiating A4 evidence,
constructing an attack, emitting authority, changing a frozen evidence count,
or changing the 1985 C68 disposition.

## Cure inventory

1. Section 34.5.1 now gives `prompt_field_evidence_id` the exact
   `psid-prompt-field-evidence:` prefix and canonical-JSON SHA-256 preimage
   over all 12 remaining displayed members, including the span. It fixes
   complete row order and aborts exact duplicate emission.
2. The evidence schema is 13 keys. `questionnaire_span` is the minimal exact
   identifier-token match's half-open UTF-8 byte interval. Coordinate-distinct
   spans must remain distinct; collapse aborts.
3. The design and validator separately bind 46 historical same-coordinate
   leading-token conflicts among 818 complete-official prompts, 49 complete
   candidate multiples over those 818, and 2,349 `multiple_candidates` over
   all 21,971 prompts. All counts remain evidence-dependent freeze-slots.

## Worked V4632 example

At 1976 prompt position 1,843, the first and second literal `V4632` matches
receive their own minimal six-byte ASCII token intervals in the authenticated
prompt bytes. Each of the three canonical field-source rows therefore retains
two coordinate-distinct evidence bodies. Omitting or equating the spans
aborts. The same law covers the two `V4991` matches at position 1,938.

## Pin table

| Path | Git blob | Bytes | Raw SHA-256 |
|---|---|---:|---|
| `scripts/validate_amendment13_execution_law.py` | `8be8ee08046d66057bd5f7409b66d23941d0241e` | 666,439 | `e2ff05ae7deec7b152f320f750e0f5e1449304babf487d92083e6e3856d20bd7` |
| `tests/test_validate_amendment13_execution_law.py` | `b91f8a193589f11ad1de9a2cf294e24e7d01996a` | 185,950 | `0447d19588bf9a4a929844e2be1bf28e5127f48c2becb12625c2cde08c22a458` |
| `scripts/build_amendment13_tier2_repairs.py` | `8e7550ff71cd43f3acd39b7fd1779b6e3a223581` | 111,145 | `2ff0ff39d7ca316fb78c1beb8164300991ea194e803795e642b544bd78b5ef1b` |

The mutation name array is 738 bytes with SHA-256
`eab546538a26abac04f559b73646bbca9d240832ae9d9ee82c6295a1462d0e2b`.

## Verification

| Check | Result |
|---|---|
| Full pinned validator battery | PASS — 220 passed in 545.76s |
| Five historical A13 families plus estimates | 796 passed; one environment-only estimates import-root failure without `PYTHONPATH` |
| Estimates family with prescribed `PYTHONPATH=src:.` | PASS — 638 passed in 27.10s |
| Changed-file Black 25.11.0, line length 79 | PASS |
| `uvx black@latest -l 79 --check .` | NOT EXECUTED — PyPI DNS failed after three retries; repository-wide installed-Black check also identifies pre-existing unrelated drift in `scripts/build_amendment12_rq_catalog_pilot.py` |
| `ruff check .` | PASS |
| `git diff --check` | PASS |

The immutable 4,025,587-byte prefix remained
`38139b8ddd24ef7be09e8f149960e8e0b6e39699d84f3783827eff6c294a9ae9`.

## Protected surfaces

The production registry module, `runs/`, `gates.yaml`, staging evidence, and
the C68 `unresolved_multiple` disposition are untouched. Nothing is pushed.

## Post-lane formatting alignment (ceremony lane, 17:30 EDT)

The lane's sandbox could not reach PyPI, so the CI-exact Black check ran
post-lane: Black 26.5.1 reformatted `scripts/validate_amendment13_execution_law.py`
(the lane's installed 25.11.0 disagrees on one construct — the same skew class
fix-4 hit); the §34.9.1 row and this report's pin table now carry the
26.5.1-formatted identity (blob `8be8ee08…`, 666,439 bytes, SHA `e2ff05ae…`).
`uvx black@latest -l 79 --check .` now passes repository-wide (592 files);
the 25.11-only "drift" the lane saw in `build_amendment12_rq_catalog_pilot.py`
was the inverse skew and needs no change. Battery re-verified post-reformat on
the amended commit.
