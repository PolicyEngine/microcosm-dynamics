"""Find which published sets pin a target that withholds B0.2's release on
an invented panel.

INVENTED DATA ONLY. ``invented_panel.py`` builds the panel from a seeded
generator; no PSID file is read. For HOUSEHOLDS and SEED, the script builds
the registry as ``calibrate.py`` does, with B0.1's sets registered at the
counts B0.1's own script gives, and runs the audit at the fixed base. Then,
for each target of true size 1 to 9 found narrow (one withholds the
release), it prints:

- the target, the audit round that classified it, its proof and its
  proven range;
- this release's sets that hold it (for a difference, its two ends);
- each B0.1 set that holds any of its atoms, with that set's size and its
  exact published value;
- the same target classified under the publication with every B0.1 set
  left out; with only the B0.1 sets that hold its atoms kept; with every
  B0.1 set kept except those; and with each of those left out in turn.

A target is matched across publications by its kind, unit type and this
release's sets, which do not depend on B0.1's sets (``build_model``). Each
classification uses a fresh system with no disclosures, as the audit's
first round does, and its own pool from the seed programs; so it answers
for the first round's constraints, not for a whole audit of the reduced
publication. A "wide" verdict rests on two verified integer points, and
"narrow" with proof "optima" on two proven optima. "Narrow" with proof
"undetermined" proves nothing: no proof was obtained, because a program
timed out, a search neither found a point nor proved there was none, or
the pool was empty. The pool can move a verdict between a proof and
"undetermined", never between two proofs. A narrow range of [1, 1]
identifies the target's size exactly; narrow only needs a width under 4.

Run from the repository root, with the thread settings the protocol uses::

    OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 OMP_WAIT_POLICY=PASSIVE \\
    PYTHONPATH=src:. python docs/design/track_b_b0_2_evidence/singleton.py \\
        HOUSEHOLDS SEED
"""

from __future__ import annotations

import copy
import hashlib
import sys
import time
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "docs/design/track_b_b0_2_evidence"))

import track_b_b0_2_counts as script  # noqa: E402
from invented_panel import invented_inputs  # noqa: E402

#: At most this many B0.1 sets are left out one at a time.
SINGLE_LIMIT = 24


def build(households: int, seed: int):
    people, labor, anchor, design = invented_inputs(households, seed)
    validity = {
        wave: script.validity_frame(frame) for wave, frame in labor.items()
    }
    counts = script.structural_counts(people, validity, anchor, design)
    registry = script.disclosure_registry(people, validity, anchor, design)
    earlier = script.b0_1_sets(people, validity)
    script.register_b0_1(
        registry, earlier, script.b0_1_structural_counts(people, validity)
    )
    return counts, registry


def key(target: dict) -> tuple:
    return (
        target["kind"],
        target["unit_type"],
        tuple(tuple(path) for path in target.get("sets", ())),
        tuple(target.get("superset", ())),
        tuple(target.get("subset", ())),
    )


def name(path) -> str:
    return "/".join(str(part) for part in path)


def classify_under(counts, registry, wanted, seconds) -> str:
    started = time.monotonic()
    model = script.build_model(registry)
    matches = [t for t in model["targets"] if key(t) == wanted]
    if len(matches) != 1:
        return f"no single match ({len(matches)} targets match)"
    target = matches[0]
    lower, upper = script.published_bounds(
        counts, registry, model, script.DISCLOSURE_BASE
    )
    relations = script.model_relations(registry, model)
    system = script.AuditSystem(model, lower, upper, relations, [])
    if not system.feasible(model["sizes"]):
        return "true sizes infeasible"
    pool = script.WitnessPool(len(model["sizes"]))
    script.seed_pool(system, pool, seconds=seconds)
    outcome, _ = script.classify(system, target, pool, seconds=seconds)
    return (
        f"{outcome['result']} (proof {outcome.get('proof')}, range"
        f" {outcome.get('range')}, true size {target['true_size']},"
        f" {len(target['columns'])} atoms, pool {pool.size},"
        f" {time.monotonic() - started:.1f}s)"
    )


def main(households: int, seed: int) -> None:
    seconds = script.PROGRAM_SECONDS
    print(
        f"singleton.py sha256 "
        f"{hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}; count"
        " script sha256 "
        f"{hashlib.sha256(Path(script.__file__).read_bytes()).hexdigest()}",
        flush=True,
    )
    counts, registry = build(households, seed)
    started = time.monotonic()
    audit = script.audit_counts(counts, registry, script.DISCLOSURE_BASE)
    print(
        f"households={households} seed={seed} b0_1_sets="
        f"{len(registry.prior)} status={audit['status']}"
        f" audit={time.monotonic() - started:.1f}s",
        flush=True,
    )
    model = script.build_model(registry)
    csc = model["matrix"].tocsc()
    prior_in_row: dict[int, list] = {}
    for path in registry.prior:
        prior_in_row.setdefault(model["path_rows"][path], []).append(path)
    narrow = [
        t
        for t in audit["targets"]
        if t["result"] == "narrow"
        and 1 <= t["true_size"] < script.DISCLOSURE_THRESHOLD
    ]
    for target in narrow:
        print(
            f"narrow target: {target['kind']} {target['unit_type']}, true"
            f" size {target['true_size']}, round {target.get('round')},"
            f" proof {target.get('proof')}, range {target.get('range')},"
            f" {len(target['columns'])} atoms, earlier {target['earlier']}",
            flush=True,
        )
        if target["kind"] == "difference":
            print(f"  superset {name(target['superset'])}")
            print(f"  subset {name(target['subset'])}")
        print(
            "  this release's sets holding it"
            f" ({len(target.get('sets', ()))}):"
        )
        for path in target.get("sets", ()):
            print(f"    {name(path)}")
        rows = sorted(
            {
                int(row)
                for column in target["columns"]
                for row in csc.indices[
                    csc.indptr[column] : csc.indptr[column + 1]
                ]
            }
        )
        holding = [path for row in rows for path in prior_in_row.get(row, [])]
        print(f"  B0.1 sets holding any of its atoms ({len(holding)}):")
        for path in holding:
            unit_type, units, value = registry.prior[path]
            print(
                f"    {name(path)}: {unit_type}, size {len(units)},"
                f" published {value}"
            )
        wanted = key(target)
        none = copy.deepcopy(registry)
        none.prior.clear()
        print(
            "  without every B0.1 set:",
            classify_under(counts, none, wanted, seconds),
            flush=True,
        )
        only = copy.deepcopy(registry)
        for path in list(only.prior):
            if path not in holding:
                del only.prior[path]
        print(
            "  with only the B0.1 sets holding it:",
            classify_under(counts, only, wanted, seconds),
            flush=True,
        )
        rest = copy.deepcopy(registry)
        for path in holding:
            del rest.prior[path]
        print(
            "  with every B0.1 set but those holding it:",
            classify_under(counts, rest, wanted, seconds),
            flush=True,
        )
        if len(holding) > SINGLE_LIMIT:
            print(
                f"  leaving out one at a time: the first {SINGLE_LIMIT} of"
                f" {len(holding)} only"
            )
        for path in holding[:SINGLE_LIMIT]:
            less = copy.deepcopy(registry)
            del less.prior[path]
            print(
                f"  without {name(path)}:",
                classify_under(counts, less, wanted, seconds),
                flush=True,
            )
    if not narrow:
        print("no narrow target of true size 1 to 9")


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]))
