REQUEST CHANGES

**High:** None. No prohibited statistic or outcome was encountered.

**Medium — the shell-expansion gap remains partly open.**  
Where: `scripts/track_b_b0_1_review_root.py:461`, `:333`; claim at `docs/design/track_b_b0_1_addendum.md:1381`.

An invented Codex event containing a nested `sh -c 'cat $FILE'` inside the normal shell wrapper returns `review_counts=True`. The scanner ignores the quoted inner script, although the inner shell expands it. Brace expansion and ANSI-C quoting also evade the matcher. This can count a review that reads outside its root. No escaping command was executed.

Smallest fix: reject nested shell execution unless its script is rescanned, reject unsupported expansion forms, and add invented regressions while preserving ordinary single-quoted `sed` and `awk` arguments.

**Low — the resampler instructions conflict.**  
Where: `docs/design/track_b_b0_1_addendum.md:298`, `:1034`.

Element 8 says to import `design_multiplicities`; the handoff says the scorer must use its own copies with an explicit root parameter. The imported function uses the planning root, so the conflicting instruction could select the wrong stream.

Smallest fix: change element 8 to reference the copies specified in section 13.

1. **Are the round-2 findings resolved?**

   | Finding | Assessment |
   |---|---|
   | Stratum fallback | Resolved. The restriction appears in element 8, builder steps and handoff: `docs/design/track_b_b0_1_addendum.md:308`, `:423`, `:1045`. |
   | Revision-prefixed output | Resolved. Counter and regression cover it: `scripts/track_b_b0_1_addendum_reads.py:381`; `tests/test_track_b_b0_1_addendum_reads.py:316`. Record entries at `docs/design/track_b_b0_1_addendum_reads.json:859`, `:864` agree with section 14 at `docs/design/track_b_b0_1_addendum.md:1143`. |
   | Shell expansions | Partly resolved; medium finding above. Ordinary wrapped, single-quoted `sed` and `awk` examples pass: `tests/test_track_b_b0_1_review_root.py:304`. |
   | Fourteen scope calls | Resolved and pinned: `tests/test_track_b_b0_1_addendum_reads.py:238`. |
   | Lane/context description | Resolved: `docs/design/track_b_b0_1_addendum.md:1334`, `:1342`. |
   | Root-seed interface | Specified substantively at `docs/design/track_b_b0_1_addendum.md:1034`; the low wording conflict remains. |

2. **Did changes introduce inconsistencies?**  
   The seed instructions conflict as described above. I found no substantive conflict with the five rulings or preserved protocol block (`docs/design/track_b_b0_1_addendum.md:79`, `:101`, `:111`, `:1389`). Read-only checks confirmed the protocol and planning-script hashes, both power-input hashes, and all nine rendered blocks. The original transcript export was unavailable, limiting independent verification of regeneration.

3. **Is the record complete and correct now?**  
   All ten elements and the named procedure are present (`docs/design/track_b_b0_1_addendum.md:143`), but the remaining findings prevent approval. d1342 and a B1 pass correctly remain registration preconditions; pending decisions do not block addendum merge (`:891`, `:895`, `:902`).

4. **Any remaining findings?**  
   One medium and one low, listed above. No others found.

**Read log:** All paths are relative to the root. Includes delegated work.

Opened or content-searched:

```text
_review_context/d622-ruling.md
_review_context/d693-RECOMMENDATION.md
_review_context/d693-ruling.md
_review_context/d765-ruling.md
_review_context/d781-ruling.md
_review_context/d782-ruling.md
docs/design/track_b_b0_1_addendum.md
docs/design/track_b_b0_1_addendum_power.json
docs/design/track_b_b0_1_addendum_q6_readlog_r2.json
docs/design/track_b_b0_1_addendum_q6_review_r1.md
docs/design/track_b_b0_1_addendum_q6_review_r2.md
docs/design/track_b_b0_1_addendum_reads.json
docs/design/track_b_b0_1_audit.md
docs/design/track_b_b0_1_planning_values.json
docs/design/track_b_b0_1_ruled_power.json
scripts/track_b_b0_1_addendum_reads.py
scripts/track_b_b0_1_addendum_tables.py
scripts/track_b_b0_1_planning_values.py
scripts/track_b_b0_1_review_root.py
scripts/track_b_b0_1_ruled_power.py
tests/test_track_b_b0_1_addendum_reads.py
tests/test_track_b_b0_1_addendum_record.py
tests/test_track_b_b0_1_planning_values.py
tests/test_track_b_b0_1_review_root.py
tests/test_track_b_b0_1_revision1_tools.py
tests/test_track_b_b0_1_ruled_power.py
```

Additional filename-only matches; contents unopened:

```text
_review_context/OPTIONS.md
docs/design/track_b_b0_1_addendum_q6_readlog_r1.json
docs/design/track_b_b0_1_addendum_q6_root_r1.json
docs/design/track_b_b0_1_addendum_q6_root_r2.json
docs/design/track_b_b0_1_counts.json
docs/design/track_b_b0_1_exposure_inventory.json
docs/design/track_b_b0_1_exposure_inventory_addendum.json
docs/design/track_b_b0_1_exposure_inventory_r2.json
docs/design/track_b_b0_1_gate_leak_check.txt
pyproject.toml
scripts/track_b_b0_1_addendum_power.py
scripts/track_b_b0_1_counts.py
scripts/track_b_b0_1_exposure_inventory.py
scripts/track_b_b0_1_gate_leak_check.py
scripts/track_b_b0_1_review_power.py
tests/test_track_b_b0_1_addendum_power.py
tests/test_track_b_b0_1_audit_record.py
tests/test_track_b_b0_1_counts.py
```

Filename searches covered the root, `tests`, `scripts` and `_review_context`, using Track B filenames, ruling filenames, `OPTIONS.md`, `pyproject.toml` and `AGENTS.md`. No `AGENTS.md` matched.