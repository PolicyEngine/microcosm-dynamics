"""DEV-only, post hoc: sensitivity of gate_epuf_fill's verdicts to K.

Shown to Max before he ruled on d927 (ratify K = 1), and disclosed in the
DEV log for that reason. K = 1 was registered at 14045be4, before any DEV
score; this sweep does not change it.

Reads only gate_epuf_fill_dev_registered_dryrun.json (the registered TEST
procedure dry-run on DEV, with every cell) and the registered floor build
(hash-checked via epuf_fill_scoring.load_registered_floors). No EPUF
microdata, no TEST. Run from the repository root with PYTHONPATH=src;
its output is gate_epuf_fill_dev_k_sweep.txt.

For each K, every gating cell's tolerance is K times the registered
(K=1) tolerance, and each recorded score is re-scored with the
repository's own epuf_fill_gate.score / adoption_tier / adopt and
epuf_fill_scoring.combined_current.

Reconstruction: score() takes truth CellValues and per-draw filled
CellValues and uses only .value (epuf_fill_gate.py:1015-1053). The dry run
recorded each cell's truth and the mean filled value over draws, so one
"draw" equal to the recorded mean reproduces the recorded gap exactly
(the mean of one value is that value; gap() is recomputed from it).
"""

import json
import math
import sys
from pathlib import Path

import numpy as np

from populace_dynamics.harness import epuf_fill_gate as g
from populace_dynamics.harness import epuf_fill_scoring as scoring
from populace_dynamics.harness.epuf_cells import CellValue

DRY = Path("docs/amendments/gate_epuf_fill_dev_registered_dryrun.json")
KS = (0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0)
GRID = np.round(np.arange(0.25, 4.0001, 0.005), 3)


def num(x):
    return float(x) if not isinstance(x, str) else float(x)  # "inf"/"nan"


rec = json.loads(DRY.read_text())
floors = scoring.load_registered_floors()  # SHA-256 checked
assert rec["floors_sha256"] == floors["sha256"]
assert g.K_TOLERANCE == 1.0

fams = {}
for fam, e in rec["families"].items():
    truth = {
        c: CellValue(num(v["value"]), int(v["events"]), int(v["events"]))
        for c, v in e["truth"].items()
    }
    gating = [
        c
        for c in floors["gating"]
        if c.startswith(f"{fam}.") and c not in e["dropped_undefined_truth"]
    ]
    rec_gating = sorted(
        c for c, r in e["primary"]["cells"].items() if "tolerance" in r
    )
    assert rec_gating == sorted(gating), fam
    for c in gating:  # recorded tolerances are the floor build's (K=1)
        assert e["primary"]["cells"][c]["tolerance"] == floors["tolerance"][c]

    def draws(block):
        return [
            {c: CellValue(num(r["filled"]), 0, 0) for c, r in block.items()}
        ]

    roles = {r: draws(e[r]["cells"]) for r in ("primary", "alternative")}
    readings = {k: draws(v["cells"]) for k, v in e["current_rule"].items()}
    fams[fam] = dict(
        e=e, truth=truth, gating=gating, roles=roles, readings=readings
    )


def run(fam, k):
    f = fams[fam]
    tol = {c: k * floors["tolerance"][c] for c in f["gating"]}
    sc = lambda d: g.score(f["truth"], d, tol, f["gating"])  # noqa: E731
    cur = {n: sc(d) for n, d in f["readings"].items()}
    ref = scoring.combined_current(*cur.values())
    out = {
        "current": {n: s["n_failing"] for n, s in cur.items()},
        "ref_failing": ref["n_failing"],
        "scores": {},
    }
    tiers = {}
    for role, d in f["roles"].items():
        s = sc(d)
        tiers[role] = g.adoption_tier(s, ref)
        out["scores"][role] = s
        out[role] = {"n_failing": s["n_failing"], "tier": tiers[role]}
    out["adopted"] = g.adopt(tiers["primary"], tiers["alternative"])
    return out


# ---- K = 1 must reproduce the record exactly --------------------------------
mismatch = []
for fam, f in fams.items():
    e, r = f["e"], run(fam, 1.0)
    if r["adopted"] != e["adopted"]:
        mismatch.append((fam, "adopted", r["adopted"], e["adopted"]))
    for role in ("primary", "alternative"):
        for key in ("n_failing", "tier"):
            if r[role][key] != e[role][key]:
                mismatch.append((fam, role, key, r[role][key], e[role][key]))
        for c, row in r["scores"][role]["cells"].items():
            want = e[role]["cells"][c]
            same_gap = (row["gap"] == num(want["gap"])) or (
                math.isnan(row["gap"]) and math.isnan(num(want["gap"]))
            )
            if not same_gap or row.get("passes") != want.get("passes"):
                mismatch.append((fam, role, c))
    for n, v in r["current"].items():
        if v != e["current_rule"][n]["n_failing"]:
            mismatch.append(
                (fam, "current", n, v, e["current_rule"][n]["n_failing"])
            )
print("K=1 reproduction mismatches:", mismatch or "none")
if mismatch:
    sys.exit(1)

# ---- table ------------------------------------------------------------------
print(
    "\n| K | odd primary | odd alt | odd cur fb/2s | odd adopted "
    "| pre primary | pre alt | pre cur | pre adopted |"
)
print("|---|---|---|---|---|---|---|---|---|")
for k in KS:
    o, p = run("odd", k), run("pre", k)
    cell = lambda r, role: f"{r[role]['n_failing']} {r[role]['tier']}"  # noqa
    print(
        f"| {k} | {cell(o,'primary')} | {cell(o,'alternative')} | "
        f"{o['current']['fallback']}/{o['current']['two_sided']} | "
        f"{o['adopted']} | {cell(p,'primary')} | {cell(p,'alternative')} "
        f"| {p['current']['fallback']} | {p['adopted']} |"
    )

# ---- odd primary worst cells, |gap| / sigma (sigma = K=1 tolerance) ---------
e = fams["odd"]["e"]
ratios = sorted(
    (
        (abs(num(r["gap"])) / r["tolerance"], c)
        for c, r in e["primary"]["cells"].items()
        if "tolerance" in r
    ),
    reverse=True,
)
print("\nodd primary worst 10 |gap|/sigma:")
for x, c in ratios[:10]:
    print(f"  {x:.3f}  {c}")
kmin = ratios[0][0]
print(f"smallest K certifying odd primary = max |gap|/sigma = {kmin:.4f}")
r = run("odd", kmin)
print(
    "  check at that K:",
    r["primary"],
    "; at K-1e-9:",
    run("odd", kmin - 1e-9)["primary"],
)

# ---- fine grid: tier transitions -------------------------------------------
print("\ntransitions on K grid 0.25..4.0 step 0.005:")
for fam in ("odd", "pre"):
    prev = None
    for k in GRID:
        r = run(fam, float(k))
        state = (r["primary"]["tier"], r["alternative"]["tier"], r["adopted"])
        if state != prev:
            print(
                f"  {fam} K>={k}: primary={state[0]} "
                f"(fail {r['primary']['n_failing']}), "
                f"alt={state[1]} (fail {r['alternative']['n_failing']}), "
                f"cur={r['current']}, adopted={state[2]}"
            )
            prev = state

# odd primary: which cells block "improves" below K=1
for k in (0.5, 0.75):
    f = fams["odd"]
    tol = {c: k * floors["tolerance"][c] for c in f["gating"]}
    cur = [
        g.score(f["truth"], d, tol, f["gating"])
        for d in f["readings"].values()
    ]
    ref = scoring.combined_current(*cur)
    s = g.score(f["truth"], f["roles"]["primary"], tol, f["gating"])
    blockers = []
    for c, row in s["cells"].items():
        if "passes" not in row:
            continue
        b = float(ref["cells"][c]["gap"])
        b = abs(b) if np.isfinite(b) else np.inf
        allowed = max(
            row["tolerance"], min(b, g.IMPROVES_CAP * row["tolerance"])
        )
        if abs(row["gap"]) > allowed:
            blockers.append(
                (
                    c,
                    round(abs(row["gap"]) / floors["tolerance"][c], 3),
                    round(b / floors["tolerance"][c], 3),
                )
            )
    print(
        f"\nodd primary improves-blockers at K={k} "
        f"(cell, |gap|/sigma, |cur gap|/sigma): {blockers}"
    )

# pre primary: max |gap|/sigma (headroom of the certification)
pr = sorted(
    (
        (abs(num(r["gap"])) / r["tolerance"], c)
        for c, r in fams["pre"]["e"]["primary"]["cells"].items()
        if "tolerance" in r
    ),
    reverse=True,
)
print(
    "\npre primary worst 5 |gap|/sigma:", [(round(x, 3), c) for x, c in pr[:5]]
)
