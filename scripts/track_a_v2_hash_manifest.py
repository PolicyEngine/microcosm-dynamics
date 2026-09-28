"""Emit the Track A v2 hash manifest from explicitly supplied frozen files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from populace_dynamics.track_a_v2.manifest import build_manifest  # noqa: E402
from populace_dynamics.track_a_v2.protocol import write_new  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--invented", action="store_true")
    args = parser.parse_args(argv)
    request = json.loads(args.request.read_text(encoding="utf-8"))
    implementation = sorted(
        (ROOT / "src/populace_dynamics/track_a_v2").glob("*.py")
    ) + sorted((ROOT / "scripts").glob("track_a_v2_*.py"))
    manifest = build_manifest(
        root=ROOT,
        implementation=implementation,
        inputs={name: Path(path) for name, path in request["inputs"].items()},
        parameter_bundles=request["parameter_bundles"],
        invented=args.invented,
        source_files={
            name: Path(path)
            for name, path in request.get("source_files", {}).items()
        },
    )
    write_new(args.output, manifest)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
