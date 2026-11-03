"""Check whether a sensitive target's possible sizes leave gaps.

INVENTED TABLES ONLY. The protocol's rule is a range: a released table's
sensitive targets each take sizes at least 4 apart among the vectors a
reader cannot rule out. It does not promise every size in between. This
script counts, over random released tables, the sensitive targets whose
possible sizes skip a value in that range, and those with fewer than five
possible sizes. Each trial draws two to four atoms, two to six published
rows over them (a repeated row counts once) and atom sizes from 1 to 16,
and keeps the table if every atom has a distinct nonempty signature and
the reader has at most 4,000 candidate vectors.

Run from the repository root::

    python docs/design/track_b_b0_2_evidence/ranges.py SEED TRIALS

The output for seed 5 and 3,000 trials is committed as ``ranges.txt``.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import oracle  # noqa: E402


def main(seed: int, trials: int) -> None:
    rng = random.Random(seed)
    stats = dict.fromkeys(["released", "sensitive", "gaps", "under5"], 0)
    for _ in range(trials):
        atoms = rng.choice([2, 3, 3, 4])
        rows = set()
        for _ in range(rng.randint(2, 6)):
            size = rng.randint(1, atoms)
            rows.add(tuple(sorted(rng.sample(range(atoms), size))))
        rows = sorted(rows)
        signatures = [
            frozenset(j for j, row in enumerate(rows) if a in row)
            for a in range(atoms)
        ]
        if not all(signatures) or len(set(signatures)) != atoms:
            continue
        sizes = [rng.randint(1, 16) for _ in range(atoms)]
        grid = oracle.candidates(rows, sizes, limit=4000)
        if grid is None:
            continue
        target_list = oracle.targets(rows, atoms)
        status, disclosed, mask = oracle.release(
            rows, sizes, grid, target_list
        )
        if status != "released":
            continue
        stats["released"] += 1
        for t in target_list:
            if not 1 <= sum(sizes[a] for a in t) < oracle.THRESHOLD:
                continue
            stats["sensitive"] += 1
            values = sorted(set(grid[mask][:, list(t)].sum(axis=1).tolist()))
            if len(values) != values[-1] - values[0] + 1:
                stats["gaps"] += 1
                print("GAP", rows, sizes, t, values, disclosed)
            if len(values) < 5:
                stats["under5"] += 1
                print("UNDER5", rows, sizes, t, values, disclosed)
    print(stats)


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]))
