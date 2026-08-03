# Amendment 9 — fix round 1 (referee verdict: REWRITE, four blocking findings)

## State

Branch `claude/ce-design-amendment9`, worktree `e11-amend9`. Base HEAD `4380589`.
Doc-only lane. All fixes prose-only: no fixture, digest, count, floor, or
row-shape moved; all six A9 fixture digests reproduce unchanged.

| | before | after |
|---|---|---|
| doc bytes | 2,637,363 | 2,653,665 |
| doc SHA-256 | `8fca3354…` | `9154b5e8…` |
| §23 appended bytes | 115,663 | 131,965 |
| revision-10 prefix `[0,2521700)` | byte-equal to the full blob at `bea8b43` | byte-equal (reverified) |
| prefix SHA-256 | `4101260b…` | `4101260b…` |

## Done

- [x] Verdict read in full; prefix law verified BEFORE edits (byte comparison)
- [x] F1 — §23.2.2 restated in §20.3.3's true two-stage gate structure: four
      arm-independent first-stage conditions, one shared width test, and the
      four renderer-pair categories §20.3.2 actually partitions on. Category 2
      (exactly one null) empty by law is what makes §22.4.5's singular image
      well-defined. V945/1969 `-1040.01` cited; all 263,430 of that field's
      unrenderable negatives have the length expression = `w`. Builder emission
      rule stated explicitly (six-key ⇔ category 4; four-key wherever the gates
      null the image). A9-R03 gains a third equation: the four-category census.
- [x] F2 — leg 4 replaced with the two-arm representation law (§22.2.2 explicit
      arm serializes the inherited seven-key row; §22.2.3's lossiness test binds
      the analytic arm alone)
- [x] F3 — "674 fields cannot serialize" scoped to the member population at both
      sites (`§23.2.1`, `§23.9.1`)
- [x] F4 — "serialized exactly once" corrected at all five sites (§23.2.1,
      §23.2.3, §23.2.4, §23.4.2, §23.6.1)
- [x] F5 — `I` notation fixed via the magnitude string; `z=-0.1, d=2, w=3` case
- [x] F6 — §23.6.1 row added for
      `candidate_arm_results[*].complete_domain_member_results`
- [x] F7/F8 — report-only; neither figure appears in the doc (verified: 77 seeds,
      7 inherited digests). Corrected in the final report, doc untouched.
- [x] Concurrent-lane flag — bears on A9-R04; closed handling stated in §23.3.1
- [x] Prefix law reverified AFTER edits; `git diff --check` clean; fences parse;
      structural invariants hold (77 seeds, 19/7/12 digests, 9 headings, 53 DC)

## Next

- [ ] Remove PROGRESS.md and commit (lane rule: no PROGRESS.md at completion)
