REQUEST CHANGES

**High:** None. No prohibited statistic or outcome was encountered.

**Medium — the Codex read log still approves commands that can read outside the root.**

All examples below returned `review_counts=True` with no flags in in-memory checks. None was executed.

| Where | Invented example and defect | Smallest fix |
|---|---|---|
| `scripts/track_b_b0_1_review_root.py:428` | `cat<TAB>/invented-private/note.txt` escapes scanning because recursion recognizes only literal spaces. | Re-tokenize words containing any shell whitespace. |
| `scripts/track_b_b0_1_review_root.py:407` | `bash -o errexit -c 'cat $FILE'` hides the inner expansion: scanning stops at `errexit`. | Handle argument-taking shell options, or reject unsupported option syntax. |
| `scripts/track_b_b0_1_review_root.py:323`, `:424` | `cat ~reviewer/invented.txt` and zsh’s `cat =awk` use unrecognized expansions. | Flag named-user tilde and zsh program-path expansion. |
| `scripts/track_b_b0_1_review_root.py:490` | `cd; cat invented.txt` reads from the inherited home directory while every word passes. | Reject directory-changing commands unless their destination and subsequent working directory are accounted for. |
| `scripts/track_b_b0_1_review_root.py:488` | `cat /usr/bin/invented-tool` treats an outside-root data operand as an exempt executable. | Restrict executable exemptions to program positions. |

These gaps can count a review that violates Q6’s root restriction. Add invented regressions for each repair and correct the blanket coverage claims at `scripts/track_b_b0_1_review_root.py:440`, `:450`, `:458`.

**Low:** None separately.

1. **Round 3:** Element 8 is resolved: it explicitly requires section 13’s root-parameterised copy (`docs/design/track_b_b0_1_addendum.md:307`, `:1046`). The read-log finding is partly resolved; its original examples have coverage (`tests/test_track_b_b0_1_review_root.py:317`), but the escapes above remain. The docstring candidly admits code-generated paths escape detection (`scripts/track_b_b0_1_review_root.py:455`), while overstating ordinary shell coverage elsewhere.

2. **d1342:** Yes. The quotation matches `_review_context/d1342-ruling.md:5` exactly (`docs/design/track_b_b0_1_addendum.md:135`). The record preserves the six-cell starting surface, floor-fixed ladder, power ≥0.90 with ≥4 cells, and failure before candidate outcomes with B–D returning to Max on real tolerances (`:195`, `:780`, `:1063`). The surface is settled; retained cells await B2’s floor.

3. **Registration record:** Complete and correct at the rule level, subject to repairing the Q6 accounting defect. All ten elements and the named procedure are present (`docs/design/track_b_b0_1_addendum.md:150`), and post-outcome changes are forbidden (`:413`). B1 remains a registration precondition (`:905`), consistent with the stated merge distinction (`:912`). The preserved protocol hash matches its pin.

4. **Remaining findings:** The medium logger finding above; no others found.

Read log, including delegated work. Every path is relative to the root.

Opened or content-searched:

```text
_review_context/d1342-ruling.md
_review_context/d622-ruling.md
_review_context/d693-ruling.md
_review_context/d765-ruling.md
_review_context/d781-ruling.md
_review_context/d782-ruling.md
docs/design/track_b_b0_1_addendum.md
docs/design/track_b_b0_1_addendum_q6_review_r1.md
docs/design/track_b_b0_1_addendum_q6_review_r2.md
docs/design/track_b_b0_1_addendum_q6_review_r3.md
scripts/track_b_b0_1_planning_values.py
scripts/track_b_b0_1_review_root.py
tests/test_track_b_b0_1_addendum_record.py
tests/test_track_b_b0_1_review_root.py
```

Additional filename-only search matches; contents unopened:

```text
pyproject.toml
docs/design/track_b_b0_1_addendum_power.json
docs/design/track_b_b0_1_addendum_q6_inventory_r3.json
docs/design/track_b_b0_1_addendum_q6_readlog_r1.json
docs/design/track_b_b0_1_addendum_q6_readlog_r2.json
docs/design/track_b_b0_1_addendum_q6_readlog_r3.json
docs/design/track_b_b0_1_addendum_q6_root_r1.json
docs/design/track_b_b0_1_addendum_q6_root_r2.json
docs/design/track_b_b0_1_addendum_q6_root_r3.json
docs/design/track_b_b0_1_addendum_reads.json
docs/design/track_b_b0_1_audit.md
docs/design/track_b_b0_1_counts.json
docs/design/track_b_b0_1_exposure_inventory.json
docs/design/track_b_b0_1_exposure_inventory_addendum.json
docs/design/track_b_b0_1_exposure_inventory_r2.json
docs/design/track_b_b0_1_gate_leak_check.txt
docs/design/track_b_b0_1_planning_values.json
docs/design/track_b_b0_1_ruled_power.json
scripts/track_b_b0_1_addendum_power.py
scripts/track_b_b0_1_addendum_reads.py
scripts/track_b_b0_1_addendum_tables.py
scripts/track_b_b0_1_counts.py
scripts/track_b_b0_1_exposure_inventory.py
scripts/track_b_b0_1_gate_leak_check.py
scripts/track_b_b0_1_review_power.py
scripts/track_b_b0_1_ruled_power.py
```

Filename searches covered the root for `AGENTS.md`, `*SKILL.md`, `track_b_b0_1*`, `*d1342*` and `pyproject.toml`. No `AGENTS.md` or skill file matched.