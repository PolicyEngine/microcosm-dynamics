"""Random search of larger tables against the protocol's guarantees.

INVENTED TABLES ONLY. Each trial draws three to five atoms and three to
six published rows over them (a repeated row counts once), then a size for
each atom from ``SIZES`` (1 to 14) or zero. It keeps the table if no atom
is empty, every atom has a distinct nonempty signature, and the reader has
at most 6,000 candidate vectors. For each released table it checks, by
enumeration with ``oracle``:

- the replay theorem: the reader's posterior (every candidate whose own
  run of the rule releases) equals the candidates left after the rounds;
- the width guarantee: every target of true size 1 to 9 spans at least
  the protection width over that posterior;
- the closure rounds' necessity: whether a rule that stopped after its
  first round would leave a sensitive target narrow.

Run from the repository root::

    python docs/design/track_b_b0_2_evidence/search.py SEED TRIALS

The output for seed 2 and 1,500 trials is committed as ``search.txt``.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import oracle  # noqa: E402

SIZES = [1, 1, 2, 3, 4, 5, 6, 8, 9, 10, 12, 14]


def single_round(rows, sizes, grid, target_list) -> bool:
    """Whether a rule with no closure round releases this vector."""
    values = {t: grid[:, list(t)].sum(axis=1) for t in target_list}
    narrow = [t for t in target_list if oracle.classify(values[t]) == "narrow"]
    return not any(
        1 <= sum(sizes[a] for a in t) < oracle.THRESHOLD for t in narrow
    )


def narrow_sensitive(sizes, grid, mask, target_list):
    """The sensitive targets that span less than the protection width."""
    found = []
    for t in target_list:
        if 1 <= sum(sizes[a] for a in t) < oracle.THRESHOLD:
            values = grid[mask][:, list(t)].sum(axis=1)
            if values.max() - values.min() < oracle.WIDTH:
                found.append((t, sorted(set(values.tolist()))))
    return found


def main(seed: int, trials: int) -> None:
    rng = random.Random(seed)
    stats = dict.fromkeys(
        [
            "tables",
            "released",
            "multi_round",
            "theorem_fail",
            "width_fail",
            "single_unsound",
        ],
        0,
    )
    for _ in range(trials):
        atoms = rng.choice([3, 3, 4, 4, 5])
        rows = set()
        for _ in range(rng.randint(3, 6)):
            size = rng.randint(1, atoms)
            rows.add(tuple(sorted(rng.sample(range(atoms), size))))
        rows = sorted(rows)
        signatures = [
            frozenset(j for j, row in enumerate(rows) if a in row)
            for a in range(atoms)
        ]
        if not all(signatures) or len(set(signatures)) != atoms:
            continue
        sizes = [rng.choice([0, *SIZES]) for _ in range(atoms)]
        if 0 in sizes:
            continue
        grid = oracle.candidates(rows, sizes, limit=6000)
        if grid is None:
            continue
        grid, target_list, released = oracle.reader(rows, sizes, grid)
        stats["tables"] += 1
        status, disclosed, mask = oracle.release(
            rows, sizes, grid, target_list
        )
        if status != "released":
            continue
        stats["released"] += 1
        stats["multi_round"] += bool(disclosed)
        if not np.array_equal(released, mask):
            stats["theorem_fail"] += 1
            print("THEOREM FAIL", rows, sizes)
        for found in narrow_sensitive(sizes, grid, released, target_list):
            stats["width_fail"] += 1
            print("WIDTH FAIL", rows, sizes, found)
        single = np.array(
            [single_round(rows, list(p), grid, target_list) for p in grid]
        )
        found = narrow_sensitive(sizes, grid, single, target_list)
        if found:
            stats["single_unsound"] += 1
            print("SINGLE-ROUND NARROW", rows, sizes, found[0])
    print(stats)


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]))
