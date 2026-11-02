"""An enumeration oracle for B0.2's disclosure rule.

INVENTED TABLES ONLY. This module reads no data. It restates the rule in
the protocol by brute force, without the count script's integer programs,
so the searches beside it can check the script's guarantees on tables too
large for the unit tests.

A table is ``(rows, sizes)``. Each row is a tuple of atom indices, one per
published set, and ``sizes`` holds the true atom sizes. The reader knows
the rows and their coarsened totals, and atoms may be empty, as in the
protocol's reader model. There is one unit type and no registered
relation beyond the rows themselves.
"""

from __future__ import annotations

import numpy as np

BASE = 10
THRESHOLD = 10
WIDTH = 4


def coarsen(value: int) -> int:
    """Publish 0 as 0, 1 to 9 as ``-1`` (below the base), and round
    everything else to the nearest multiple of the base, halves up."""
    if value == 0:
        return 0
    if value < BASE:
        return -1
    return (2 * value + BASE) // (2 * BASE) * BASE


def upper(published: int) -> int:
    """The largest count that publishes as ``published``."""
    return max(
        value
        for value in range(max(published, 0) + BASE + 1)
        if coarsen(value) == published
    )


def targets(rows, atoms: int) -> list[tuple[int, ...]]:
    """Every atom, and every difference of two nested published sets."""
    found = {(atom,) for atom in range(atoms)}
    sets = [frozenset(row) for row in rows]
    for big in sets:
        for small in sets:
            if small and small < big:
                found.add(tuple(sorted(big - small)))
    return sorted(found)


def coarsen_array(values: np.ndarray) -> np.ndarray:
    """``coarsen`` applied to every element of an integer array."""
    rounded = (2 * values + BASE) // (2 * BASE) * BASE
    return np.where(values == 0, 0, np.where(values < BASE, -1, rounded))


def candidates(rows, sizes, limit=None, chunk=1_000_000):
    """Every atom-size vector whose publication equals the truth's.

    Vectors are listed in lexicographic order, the first atom slowest, by
    decoding consecutive integers in chunks, so memory stays bounded
    however many vectors the caps allow. With ``limit``, returns None as
    soon as more than ``limit`` vectors are found.
    """
    atoms = len(sizes)
    published = np.array([coarsen(sum(sizes[a] for a in row)) for row in rows])
    caps = [
        min(upper(published[j]) for j, row in enumerate(rows) if a in row)
        for a in range(atoms)
    ]
    radices = np.array([cap + 1 for cap in caps], dtype=np.int64)
    strides = np.ones(atoms, dtype=np.int64)
    for a in range(atoms - 2, -1, -1):
        strides[a] = strides[a + 1] * radices[a + 1]
    total = int(np.prod(radices))
    matrix = np.array([[int(a in row) for a in range(atoms)] for row in rows])
    found = []
    count = 0
    for start in range(0, total, chunk):
        index = np.arange(start, min(start + chunk, total), dtype=np.int64)
        grid = index[:, None] // strides % radices
        keep = np.all(coarsen_array(grid @ matrix.T) == published, axis=1)
        found.append(grid[keep])
        count += int(keep.sum())
        if limit is not None and count > limit:
            return None
    return np.concatenate(found)


def classify(values: np.ndarray) -> str:
    """Wide if the values span the protection width; otherwise irrelevant
    if none lies in 1 to 9, and narrow if one does."""
    if values.size == 0:
        raise AssertionError("empty system")
    if values.max() - values.min() >= WIDTH:
        return "wide"
    if not np.any((values >= 1) & (values < THRESHOLD)):
        return "irrelevant"
    return "narrow"


def release(rows, sizes, grid=None, target_list=None):
    """Apply the rule by enumeration.

    Returns the status, the targets disclosed in closure rounds, and the
    mask of candidate vectors left after the disclosures.
    """
    if grid is None:
        grid = candidates(rows, sizes)
    if target_list is None:
        target_list = targets(rows, len(sizes))
    values = {t: grid[:, list(t)].sum(axis=1) for t in target_list}
    truth = {t: sum(sizes[a] for a in t) for t in target_list}
    mask = np.ones(len(grid), dtype=bool)
    disclosed = []
    while True:
        narrow = [
            t
            for t in target_list
            if t not in disclosed and classify(values[t][mask]) == "narrow"
        ]
        if any(1 <= truth[t] < THRESHOLD for t in narrow):
            return "withheld", disclosed, mask
        if not narrow:
            return "released", disclosed, mask
        disclosed.extend(narrow)
        for t in narrow:
            mask &= ~((values[t] >= 1) & (values[t] < THRESHOLD))


def reader(rows, sizes, grid=None):
    """The reader's posterior after a release.

    Returns the candidate grid, the targets, and a mask of the candidate
    vectors whose own run of the rule releases.
    """
    if grid is None:
        grid = candidates(rows, sizes)
    target_list = targets(rows, len(sizes))
    released = np.array(
        [
            release(rows, list(point), grid, target_list)[0] == "released"
            for point in grid
        ]
    )
    return grid, target_list, released
