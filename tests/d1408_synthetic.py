"""Seeded synthetic counts and weights for the d1408 publication tests.

Verification class: test fixtures only. Every count and summed weight in a
d1408 test fixture comes from this module (or from Hypothesis), never from
the diagnostic's outputs; ``tests/test_d1408_fixture_provenance.py``
enforces that. Each value is a pure function of ``SEED`` and a per-fixture
salt, so fixtures reproduce exactly and the provenance guard can recompute
every value a test asks for. Mechanism differences of one through nine are
written as arithmetic on these values (``base - 4``), not as counts.
"""

from __future__ import annotations

import hashlib
import random

SEED = 20261015
LOW = 1_000
HIGH = 99_999


def _rng(salt: str) -> random.Random:
    digest = hashlib.sha256(f"{SEED}:{salt}".encode()).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def counts(salt: str, n: int) -> list[int]:
    """``n`` distinct synthetic counts in [LOW, HIGH] for one fixture."""
    return _rng(f"count:{salt}").sample(range(LOW, HIGH + 1), n)


def weights(salt: str, n: int) -> list[float]:
    """``n`` synthetic summed weights (two decimals) for one fixture."""
    rng = _rng(f"weight:{salt}")
    return [round(rng.uniform(1e5, 1e8), 2) for _ in range(n)]
