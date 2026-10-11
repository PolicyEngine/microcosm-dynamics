#!/usr/bin/env python3
"""Track B B2: the floor comparator (B0.1 addendum, section 9).

A separate script, not the floor builder. After B2's floor artifact is
committed, it reads two fields of each boundary-2010 selection ledger and
nothing else:

- the six M6-retained cells' person-split floor block,
  ``boundaries["2010"]["floor"]``;
- the seed 0-4 floor detail, ``boundaries["2010"]["floor_gate_seed_detail"]``.

The key paths are the selectors' own: both ``select_m6_qstar_train_only``
(lines 2274-2291) and ``select_m6_rhostar_train_only`` (lines 1852-1875)
store the ``_boundary_context`` floor and detail there, and both reducers
leave ``boundaries`` untouched.

It prints only whether each field's canonical SHA-256 equals the builder's.
The seed detail is compared in two forms, the six cells' detail and the
whole field. A mismatch is published and gates nothing. The ledgers are on
the Q6 exclusion list, so a run of this script is recorded as a ledger
read.

The JSON parser has to tokenize the whole ledger; the script keeps the two
fields, drops the rest at once, and prints no value.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from populace_dynamics.track_b import b2  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FLOOR = ROOT / "runs" / "track_b_b2_floor.json"
#: The boundary-2010 selection ledgers (audit section 5.2).
LEDGERS = (
    ROOT / "docs" / "analysis" / "m6_qstar_train_only_selection_results.json",
    ROOT
    / "docs"
    / "analysis"
    / "m6_rhostar_train_only_selection_results.json",
)
BOUNDARY = str(b2.ORIGIN)
FLOOR_PATH = ("boundaries", BOUNDARY, "floor")
DETAIL_PATH = ("boundaries", BOUNDARY, "floor_gate_seed_detail")


def ledger_fields(path: Path) -> tuple[Any, Any]:
    """The two fields of one ledger; nothing else is kept."""
    with Path(path).open("rb") as stream:
        document = json.load(stream)
    node = document
    for key in FLOOR_PATH[:-1]:
        node = node[key]
    floor, detail = node[FLOOR_PATH[-1]], node[DETAIL_PATH[-1]]
    del document, node
    return floor, detail


def compare(
    builder: Mapping[str, Any], floor: Any, detail: Sequence[Any]
) -> dict[str, bool]:
    """Equality of each field's canonical SHA-256 with the builder's."""
    return {
        "floor_block_six_cells_equal": b2.canonical_sha256(floor)
        == builder["floor_block_six_cells_sha256"],
        "seed_detail_six_cells_equal": b2.canonical_sha256(
            b2.six_cell_seed_detail(detail)
        )
        == builder["seed_detail_six_cells_sha256"],
        "seed_detail_all_cells_equal": b2.canonical_sha256(detail)
        == builder["seed_detail_all_cells_sha256"],
    }


def run(floor_artifact: Path, ledgers: Sequence[Path]) -> dict[str, Any]:
    builder = json.loads(Path(floor_artifact).read_text(encoding="utf-8"))
    hashes = builder["person_split"]
    out: dict[str, Any] = {"ledgers": {}}
    for path in ledgers:
        floor, detail = ledger_fields(path)
        out["ledgers"][Path(path).name] = compare(hashes, floor, detail)
        del floor, detail
    return out


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--floor-artifact", type=Path, default=FLOOR)
    parser.add_argument("--ledger", type=Path, action="append")
    args = parser.parse_args(argv)
    pin = b2.committed_sha256(ROOT, args.floor_artifact)
    result = run(args.floor_artifact, args.ledger or LEDGERS)
    print(
        json.dumps({"floor_artifact": pin, **result}, indent=1, sort_keys=True)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
