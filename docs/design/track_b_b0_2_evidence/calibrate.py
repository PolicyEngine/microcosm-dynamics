"""Time B0.2's disclosure audit on an invented panel.

INVENTED DATA ONLY. ``invented_panel.py`` builds the panel from a seeded
generator; no PSID file is read. The script builds the count script's
registry and model, runs its audit at the fixed base, and prints the
model's size, the audit's status and results, and its slowest targets.
As ``main()`` does, it registers B0.1's sets, rebuilt from the same panel,
at the counts B0.1's own script gives; ``--without-b0-1`` leaves them out,
as the runs before review round 3's answer did.
It wraps ``classify`` and ``AuditSystem.direction`` only to time them; the
audit itself is unchanged.

Run from the repository root, with the thread settings the protocol uses::

    OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 OMP_WAIT_POLICY=PASSIVE \\
    PYTHONPATH=src:. python docs/design/track_b_b0_2_evidence/calibrate.py \\
        HOUSEHOLDS SEED [--without-b0-1]

The output for the report is committed beside it as ``calibration.txt``.
"""

from __future__ import annotations

import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "scripts"))
sys.path.insert(0, str(HERE))

import track_b_b0_2_counts as script  # noqa: E402
from invented_panel import invented_inputs  # noqa: E402


def main(households: int, seed: int, with_b0_1: bool = True) -> None:
    started = time.monotonic()
    people, labor, anchor, design = invented_inputs(households, seed)
    validity = {
        wave: script.validity_frame(frame) for wave, frame in labor.items()
    }
    counts = script.structural_counts(people, validity, anchor, design)
    registry = script.disclosure_registry(people, validity, anchor, design)
    earlier = {}
    if with_b0_1:
        earlier = script.b0_1_sets(people, validity)
        script.register_b0_1(
            registry, earlier, script.b0_1_structural_counts(people, validity)
        )
    model = script.build_model(registry)
    sensitive = sum(1 <= t["true_size"] < 10 for t in model["targets"])
    print(
        f"households={households} seed={seed} "
        f"persons/wave~{len(people) // 13} sets={len(registry.sets)} "
        f"b0_1_sets={len(earlier)} "
        f"rows={model['matrix'].shape[0]} "
        f"atoms={dict(Counter(model['unit_types']))} "
        f"targets={len(model['targets'])} sensitive={sensitive} "
        f"build={time.monotonic() - started:.1f}s",
        flush=True,
    )
    slow = []
    classify = script.classify
    direction = script.AuditSystem.direction

    def timed_classify(system, target, pool, *, seconds):
        start = time.monotonic()
        outcome = classify(system, target, pool, seconds=seconds)
        elapsed = time.monotonic() - start
        record = outcome[0]
        slow.append(
            (
                round(elapsed, 1),
                target["kind"],
                target["true_size"],
                record["result"],
                record.get("proof"),
            )
        )
        return outcome

    def timed_direction(self, weights, *, seconds):
        start = time.monotonic()
        point = direction(self, weights, seconds=seconds)
        print(
            f"  seed program {time.monotonic() - start:.1f}s "
            f"point={point is not None}",
            flush=True,
        )
        return point

    script.classify = timed_classify
    script.AuditSystem.direction = timed_direction
    start = time.monotonic()
    audit = script.audit_counts(counts, registry, script.DISCLOSURE_BASE)
    results = Counter(t["result"] for t in audit["targets"])
    proofs = Counter(t.get("proof") for t in audit["targets"])
    narrow_sensitive = sum(
        t["result"] == "narrow" and 1 <= t["true_size"] < 10
        for t in audit["targets"]
    )
    print(
        f"B={audit['base']} status={audit['status']} "
        f"rounds={[len(r['disclosed']) for r in audit['rounds']]} "
        f"results={dict(results)} proofs={dict(proofs)} "
        f"pool={audit['pool']} narrow_sensitive={narrow_sensitive} "
        f"audit={time.monotonic() - start:.1f}s",
        flush=True,
    )
    print("  slowest targets:", sorted(slow, reverse=True)[:5], flush=True)
    withholding = [
        (t["kind"], t["unit_type"], t["true_size"], t["earlier"])
        for t in audit["targets"]
        if t["result"] == "narrow" and 1 <= t["true_size"] < 10
    ]
    print("  narrow sensitive (kind, unit, size, earlier):", withholding)


if __name__ == "__main__":
    main(
        int(sys.argv[1]),
        int(sys.argv[2]),
        with_b0_1="--without-b0-1" not in sys.argv[3:],
    )
