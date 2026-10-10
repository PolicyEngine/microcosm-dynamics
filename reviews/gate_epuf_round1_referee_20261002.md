<!-- Round-1 adversarial referee report on PR #509 (gate_epuf registration).
Reviewer: independent Opus 5.5 lane, subfleet job 20261002-095515-epuf-gate-r1b,
reviewing branch head ce8d5000 (2026-10-02). Committed verbatim as the round's record. -->

# Referee report: `gate_epuf` registration (PR #509, branch `epuf-gate-registration-20261001`)

## Verdict: AMEND. Do not lock as proposed: reject option (a) and adopt option (c)

As measurement code, the rules-first machinery is mostly sound: the reader, operator, cells, gate algebra and ladder hold up. The gated surface should not lock. The pre-registered pause fired. The remedy the drafting session recommends, (a), relaxes a pre-registered requirement after the result was seen, and it would lock a gate whose first verdict can largely be predicted from public information. Publish tranche G as a report-only benchmark (option (c)), after the record fixes below. If a pass-or-fail EPUF gate is still wanted, it should come from a fresh registration whose rules are fixed before anything is recomputed (option (b), gate_m6 style).

**What I could not do.** This session had no shell, so I ran no tests and no Python. The evidence is code reading plus hand arithmetic on the values committed in `runs/epuf_gate_floors_v1.json`. I read no PSID microdata. I also could not check the push-time chronology against git.

---

## Findings

### 1. SERIOUS: Option (a) is a self-serving fork; the right remedy is (c)

- **It rescues the gate after the fact.** (a) restates the bite requirement "at what the gate demonstrably detects" (proposal §7.5). Any gate passes a requirement written to match its own demonstrated power, so the requirement no longer tests anything.
  - `no_self_rescue` (`gates.yaml:565-568`) literally covers only committed candidate verdicts, so it is not breached.
  - The proposal's own rule is breached: "Any later change to a rule is recorded… no cell may be redefined on account of its own bridge" (§10). So is the purpose the forks ledger exists for.
- **The first verdict is largely predictable.** §10 discloses that candidate 11's log autocorrelation is above the PSID at 2 and 4 years. Both r6 bridges are negative: EPUF persists more than the PSID (`B = -0.043` for men, `-0.032` for women). The interval stretches from the PSID's position to `t = 0.079` past EPUF, which is about 0.12 above the PSID. A candidate that persists more than the PSID therefore moves toward EPUF and lands inside. Choosing to lock now, with the bridge signs known, picks a gate the registered candidate very likely passes.
- **House precedent for a pause is a candidate-blind redesign, not a relaxed requirement.** gate_m6 v1 hit its OC pause. It went through a pinned-ladder redesign that used only truth-side arithmetic, adjudicated publicly before v2 (`gates.yaml:5858-5866`).
- **(b) cannot be done blind here.** Every redesign the proposal names is informed by the bridges: pooled-sex r6 has a bridge roughly equal to the mean of the two known ones. The proposal concedes this in §7.5.
- **Required fix:**
  - Adopt (c). Publish the per-cell table with its model/source decomposition on every gate-1 run, and set the draft block's status to report-only.
  - Record the pause and this ruling in the forks ledger.
  - Any future gate needs a new registration id, rules fixed before any recomputation, and a gate-1-orthogonal bite (see finding 4).

### 2. SERIOUS: The bite requirement could not be met by design, so the pause was foreseeable

- **The arithmetic.** For roughly normal `e`, the formula gives `mean|e| + 4 sd|e| ≈ (0.798 + 4×0.603)σ = 3.21σ`.
  - With `σ = 0.0246`, `t = 0.079`. Artifact check for r6.men: 0.01982 + 4×0.01469 = 0.0786.
  - Giving 10% of persons a donor's early years (bd1) cuts r6 by about 0.1 × 0.668 ≈ 0.067. That is less than `t`.
  - Reaching a 90% fail rate would need about `t + 1.28σ_bite ≤ 0.067`, which means `σ ≲ 0.016`. The PSID cannot deliver that.
- **The bite and eligibility rules disagree.** Eligibility promises 80% power at a shortfall of about 0.10 from the PSID (`t + 0.84σ`). The bite demanded 90% power at 0.067. The drafting session had seen EPUF subsampled to PSID scale (§10), which gives σ, so this was knowable before the build.
- **Required fix:** In the forks ledger and §7.4, describe the pause as an internal inconsistency in the registration, not a data surprise. Any future registration must check that the bite dose sits above the cell's own 90% detection point before the floor build.

### 3. SERIOUS: The bite fail shares do not measure the gate's power against a broken generator

- **No shared noise.** `bite_demonstrations` (`scripts/build_epuf_gate_floors.py:755-822`) perturbs the realised PSID support and scores it on the 20 fixed gate holdouts. The term the floor says dominates (78% of variance for men, 73% for women) is therefore absent from the bites.
- **Anchored to where the 20 holdouts happen to sit.** The real-holdout estimate for women is −0.0448 against `B = −0.0323`, a gap of −0.0125. For men it is −0.0438 against −0.0428. This is why women fail 0.30 against men's 0.16 even though women get the smaller dose (0.064 against 0.067).
  - For a generator, those holdout realisations do not carry over: its window values are generated.
- **The shifts are not stored.** The artifact keeps only fail counts, not the per-bite shifts.
- **Required fix:**
  - Store per-seed bite estimates and each bite's mean shift `δ̂`.
  - Report the power under the gate's own noise model, `Φ((δ̂ − (distance to edge))/σ)`. For bd1 on men that is about `Φ((0.067 − 0.079)/0.0246) ≈ 0.31`.
  - Express any bite requirement in those terms.

### 4. SERIOUS: What the gated surface adds beyond gate 1 is not demonstrated

- **Gate 1 already polices persistence.** It sets tolerances of 0.05, 0.06 and 0.07 on log-earnings autocorrelation at lags of 2, 4 and 10 years (`gates.yaml:372-374`). The two gated cells are sex-level 6-year rank correlations whose lower edge is 0.079 below the PSID.
- **The by-sex split adds no catch.** bd2 and bd2c fail at 0.00 (artifact lines 6636-6651). Yet §3 sells the by-sex cells as "where this gate tests something gate 1 does not".
- **The bd2 design limits that conclusion.** Donors are matched on pooled-sex 2004 deciles, which preserves most of the rank correlation by construction. It tests pooling of a decile-conditional law, nothing finer.
- **No bite is scored on gate 1.** So no evidence shows a generator that passes gate 1 and fails `gate_epuf`.
- **Required fix:** Before any future lock, show a perturbation that passes gate 1's battery but fails `gate_epuf`. Otherwise `covers` must say the gated cells add no demonstrated bite beyond gate 1.

### 5. SERIOUS (record honesty): The draft block names the wrong rules-first commit

- **The error.** `docs/design/gate_epuf_block_draft.yaml:189-190` says "rules committed before the floor build (commit 970a9db721bf)".
  - The renderer fills this from `revision_pins.head_sha` (`scripts/render_gate_epuf_block_draft.py:227-229`).
  - 970a9db7 is the AIME fix made *after* the first floor build. The rules-first commit is `eec910d6` (proposal §10).
- **Required fix:** Have the renderer cite the rules commit and the build commit separately. Bind both in `tests/test_gate_epuf_block_draft.py`.

### 6. SERIOUS: The blindness chronology cannot be audited from the PR

- **The first build is not in the repository.** The proposal points to `epuf-20261001/first-floor-build/` and gives only a truncated hash (`369bf5ec…7e378`). Nothing in the repository references either.
- **No build time.** The artifact records no build timestamp, only `elapsed_seconds`.
- **The key claim is unverifiable.** "Window cells, floors, partition and bites identical" across the two builds cannot be checked.
- **Required fix:**
  - Commit the first build as frozen lineage (as gate_m6 kept v1 and v2), with its full SHA-256.
  - Add a test that its window-cell, partition and bite blocks equal v1's.
  - Add a UTC build timestamp to future artifacts.

### 7. SERIOUS (ceremony): The scoring path is not pinned

- **The gap.** `DERIVATION_CORE` (`scripts/build_epuf_gate_floors.py:109-115`) and the pin test (`tests/test_gate_epuf_block_draft.py:78-89`) cover five files. Neither covers `harness/epuf_run.py`, which the draft block names as the scoring path (`scoring: populace_dynamics.harness.epuf_run.score_candidate`), nor the renderer. The scoring code could drift after lock without tripping a test.
- **Required fix:** Pin `epuf_run.py`'s SHA-256 in the draft block and add a binding test. The artifact is exclusive-create, so a separate pin is cleaner than a rebuild.

### 8. MINOR: The floor bounds the shared noise rather than pricing it for this generator

- **Calibrated to an oracle.** The half-split term is the right size for a generator that draws from the true law (Var = σ²/N). The simulation (`tests/harness/test_epuf_gate.py:294-340`) uses such an oracle, and it conditions on one of the two scored variables.
- **Likely conservative for candidate 11.** That generator copies donor ranks from training data drawn from 80% of the same sample (`run_gate1_candidate10.py:495-562`), so it partly tracks the realised sample. The shared residual is then smaller.
  - Result: the OC is conservative, which is safe, but power is lost, and that feeds the pause.
- **The other term roughly offsets.** The averaging term's `m(H) − m(T)` has variance 6.25σ²/N per split. A candidate's holdout deviation is 4σ²/N plus its own draw noise.
- **The artifact matches the variance accounting.** Predicted shared share = 1/(1 + 6.25/20) = 0.76; observed 0.73-0.78.
- **Required fix:** Change "prices" to "bounds (exact for an oracle law)" in §4 and §11.5.

### 9. MINOR: k = 4 is called "the house formula", but house precedent picks k by OC

- **Precedent.** gate_m4 chooses k against the OC (`gates.yaml:3248-3266`); gate_m6 uses k = 3.
- **Over-conservative for one decision.** For a single 20-seed decision, k = 4 gives a per-cell false-fail rate of about 7e-4, far stricter than the 0.90 OC floor. This is the lever that made the bite unreachable.
- **Required fix:** Correct the wording. Changing k now would be a fork; any future registration should declare an OC rule for k before the floor build.

### 10. MINOR: The reproduction clause is weak for seeds 5-19

- **The gap.** `gate1_rank_knn_v5.json` stores only pairs C2ST for seeds 5-19 (`scripts/run_gate1_candidate11.py:61-62`). "Reproduces exactly" therefore checks one scalar per seed.
- **Required fix:** Commit SHA-256 digests of the generated panels at registration and compare them.

### 11. MINOR: The birth-year rule shifts cohort bands

- **The bias.** `period = wave − 1` while age is measured at the wave (`data/family.py:796-800, 843`). So `period − age` gives b−1 or b, about half a year below EPUF's YOB.
- **House precedence is not followed.** The repository uses the marriage-history birth year first (`estimates/career.py:650-656`).
- **Within-band age mix differs.** The age-59 ceiling combined with the anchor ≥ 2006 rule thins the oldest c0 years.
- **Effect.** Both end up in the bridge, which is legitimate, but the bands are systematically shifted.
- **Required fix:** Adopt the house precedence or document the gap. Report the support's within-band birth-year distribution beside EPUF's.

### 12. MINOR: The minimum-events rule for sex-level cells sums band events

- **The issue.** `epuf_cells.py:330-334` sums events across bands. A band mean is only as precise as its weakest band.
- **House rule.** It is per cell, on the weaker half of the worst seed (`gates.yaml:3232-3234`).
- **Effect.** Moot for r6 (hundreds of pairs). It could admit sparse share cells.
- **Required fix:** Use the minimum over bands.

### 13. MINOR: Bite doses are mislabelled

- **bd3 moves more than labelled.** It ranks with `searchsorted(side="right")` (`build_epuf_gate_floors.py:720-723`), so every at-cap value gets rank 1.0.
  - Men's at-cap share is 17.8%, so "top 8%" becomes "all at-cap values plus anything above 0.92".
  - It is also pooled across sex and band.
- **bd1 is slightly under-dosed.** Donors are drawn with replacement and can include the person themselves (`rng.choice(index)`, line 671).
- **Required fix:** Correct the labels, or rank ties at their lower midrank.

### 14. MINOR: Some §7 claims are not in the artifact or state a mechanism without evidence

- **"Roughly 0.07" is not stored.** The shift is consistent with theory (0.1 × 0.668), but §7 says all its numbers come from the artifact.
- **Mechanisms stated as explanations:**
  - "a more attached group" for the q_atmax bridge;
  - "EPUF counts noncovered spells and years before arrival as zeros" for the zero-years bridge.
- **Mismatched comparison.** "Comparable to gate 1's 0.06-0.07" compares an 80% power point (0.10) with tolerances, on a different statistic, under a per-seed 4-of-5 rule. The like-for-like figure is `t = 0.079`.
- **Overstated certification.** "A pass certifies a distance below the cap" is too strong: a candidate at the cap still passes 20% of the time.
- **Required fix:** Hedge these statements and store the bite shifts.

### 15. MINOR: The scope of "nothing generates a career" is overstated

- **The issue.** The forward earnings law generates earnings for 2015 onward (`engine/forward_earnings.py:1-7`). `build_career` appends them as PROJECTED (`estimates/career.py:1032-1047`).
- **Required fix:** Say "nothing generates earnings for years before 1998 / a historical career".

### 16. MINOR: The tranche R mask applies two of the assembler's rules, not all of them

- **Not emulated:**
  - the coverage ≥ 0.80 exclusion and the domain exclusions (`career.py:1580-1598`);
  - the one-neighbour fallback (`career.py:972-975`), which is moot on EPUF.
- **Within the cohorts used, the 1968 start is right:** `max(1968, birth year + 22)` equals 1968 for everyone born 1930-1944.
- **Required fix:** Call it "two of the assembler's rules" and name the exclusions it does not apply.

### 17. MINOR: Housekeeping

- **Seed reuse contradicts the docstring.** `half_split_seed(b) = b` reuses gate seeds 0-19 (`epuf_gate.py:121-131`). On the same RNG stream, half A contains gate seed b's holdout. This is harmless, but it contradicts the "never reuses a gate seed" rationale.
- **Non-finite values are not stripped everywhere.** `_finite` wraps only the floor and bite blocks. `json.dumps` allows NaN by default (`artifacts.py:23`), so a NaN in tranche R would write invalid JSON. The current artifact has no NaN or Infinity.

---

## Checked and found sound

- **Split function.** `holdout_mask` matches `split_panel_by_person` (`harness/panel.py:207-209`). The builder asserts it on seeds 0-19, and the block test checks holdout sizes.
- **Calendar years.** Period is the income year, so capping at the year's wage base by period is correct.
- **Support and conditioning.**
  - The anchor is the last in-filter period (`run_gate1_candidate2.py:276-285`).
  - The chain keeps only that anchor at its real value (`run_gate1_candidate10.py:277-279, 384-569`). With anchor ≥ 2006, every scored window value is generated.
  - The support comes from the real panel only (`epuf_run.py:56`).
- **Measurement.**
  - The operator preserves whether a value is positive and whether it is at the cap.
  - Wage bases for 1998-2004 are not multiples of $1,000, so rounding cannot land on the cap.
  - EPUF tops out exactly at the wage base (`tests/data/test_epuf.py:157`).
  - Weighted midranks are correct (a constant offset is irrelevant), and the unit-weight case is tested against scipy.
- **Gate algebra.**
  - `[m(A) − m(B)]/2` has the variance of the full-sample estimate.
  - The interval, eligibility rule, faithful OC and partition are recomputed by the binding test.
  - My hand checks of r6.men and r6.women agree with the artifact: tolerances 0.079 and 0.078, OCs 0.99935 and 0.99925, minimum detectable gap 0.1425 for men.
  - The bridge cannot widen acceptance beyond the cap, so the gate cannot become vacuous.
  - The ladder is mechanical and was fixed before the build.
- **Tranche R AIME.** It uses 35 years, indexes to age 60, and ranks every year after 1950 through age 61. This is consistent with `ss.statutory_aime` for the 1930-1944 cohorts.
- **§7 counts match the artifact.** Support counts (22,300 → 5,769), the bite fail shares and the training-copy estimates (−0.044 for men, −0.045 for women) all agree.