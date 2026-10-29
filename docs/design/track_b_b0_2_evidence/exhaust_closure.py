"""Search every three-atom table for a release that needs a second round.

INVENTED TABLES ONLY. A table here is any set of two or more published
rows over three atoms whose signatures (the rows that hold each atom) are
distinct and nonempty, and every size vector with each atom in 1 to 14.
For each, ``oracle.release`` applies the rule, and the script prints each
table whose release discloses a target in a closure round. It found none,
which is why the closure rounds are tested by a forced-round unit test
instead (``test_a_narrow_target_outside_one_to_nine_starts_another_round``).

Run from the repository root::

    python docs/design/track_b_b0_2_evidence/exhaust_closure.py

The output is committed beside it as ``exhaust_closure.txt``.
"""

from __future__ import annotations

import sys
from itertools import combinations, product
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import oracle  # noqa: E402

ATOMS = 3


def main() -> None:
    rows_available = [
        row
        for size in range(1, ATOMS + 1)
        for row in combinations(range(ATOMS), size)
    ]
    structures = 0
    tables = 0
    multi = 0
    for count in range(2, len(rows_available) + 1):
        for rows in combinations(rows_available, count):
            signatures = {
                frozenset(j for j, row in enumerate(rows) if a in row)
                for a in range(ATOMS)
            }
            if len(signatures) != ATOMS or frozenset() in signatures:
                continue
            structures += 1
            target_list = oracle.targets(rows, ATOMS)
            for sizes in product(range(1, 15), repeat=ATOMS):
                tables += 1
                status, disclosed, _ = oracle.release(
                    list(rows), list(sizes), None, target_list
                )
                if disclosed:
                    multi += 1
                    print("MULTI", rows, sizes, status, disclosed)
    print(f"structures {structures} tables {tables} multi {multi}")


if __name__ == "__main__":
    main()
