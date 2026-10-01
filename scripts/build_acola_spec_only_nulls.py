#!/usr/bin/env python3
"""Write Registration 18's spec-only nulls from pinned, approved inputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from populace_dynamics.acola_track.nulls import (  # noqa: E402
    NULLS_PATH,
    build_nulls,
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=NULLS_PATH)
    args = parser.parse_args(argv)
    rendered = json.dumps(build_nulls(), indent=2, allow_nan=False) + "\n"
    args.output.write_text(rendered, encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
