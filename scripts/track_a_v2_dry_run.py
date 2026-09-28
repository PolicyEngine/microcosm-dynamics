"""INVENTED DATA - NOT A COMPARISON: all 68 rows and an intended refusal."""

from __future__ import annotations

import argparse
import copy
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from populace_dynamics.track_a_v2 import INVENTED_HEADER
from populace_dynamics.track_a_v2.histories import HistoryValidator
from populace_dynamics.track_a_v2.invented import invented_inputs
from populace_dynamics.track_a_v2.manifest import (
    build_manifest,
    runtime_parameter_bundle,
)
from populace_dynamics.track_a_v2.runner import _canonical, legacy, run_joint

ROOT = Path(__file__).resolve().parents[1]


def _output_directory(path: Path) -> Path:
    path = path.resolve()
    allowed = (
        (ROOT / ".cache").resolve(),
        Path(tempfile.gettempdir()).resolve(),
    )
    if not any(path.is_relative_to(parent) for parent in allowed):
        raise ValueError(
            "invented output must be under .cache or a temp directory"
        )
    return path


def dry_run(output_dir: Path, *, progress=None) -> dict:
    """Exercise real projection/calculation paths on invented inputs only."""
    output_dir = _output_directory(output_dir)
    inputs = invented_inputs()
    captured = {}
    project = legacy._project_population

    def capture(*args, **kwargs):
        value = project(*args, **kwargs)
        captured["projection"] = value
        return value

    with patch.object(legacy, "_project_population", capture):
        result = run_joint(inputs, progress=progress)
    if result["attempt"]["status"] != "completed" or len(result["rows"]) != 68:
        raise AssertionError(
            f"invented complete run refused: {result['attempt']}"
        )

    # Intended violation (§12.7/§17.4): two invented award events replace
    # immutable events in a COPY, to prove step 2 precedes all tabulations.
    projected, diagnostics = copy.deepcopy(captured["projection"])
    draw = min(projected)
    validator = HistoryValidator(projected[draw], inputs.cohort)
    person_id = next(iter(validator.requested_di_levels()))
    for frame in projected[draw].slices[1:3]:
        frame.loc[frame["person_id"] == person_id, "di_event"] = "award"
    with patch.object(
        legacy, "_project_population", return_value=(projected, diagnostics)
    ):
        refusal = run_joint(inputs)
    assert refusal["attempt"]["status"] == "refused"
    assert refusal["attempt"]["step"] == 2
    assert len(refusal["attempt"]["uncomputed_rows"]) == 68
    assert not refusal["rows"]

    output_dir.mkdir(parents=True, exist_ok=True)
    input_path = output_dir / "invented-inputs.json"
    input_record = {
        "header": INVENTED_HEADER,
        "seed": 7,
        "cohort_seal": inputs.cohort.seal,
        "persons": _canonical(inputs.cohort.persons.to_dict("records")),
        "initial_slice": _canonical(
            inputs.cohort.initial_slice.to_dict("records")
        ),
        "careers": _canonical(dict(inputs.cohort.careers)),
        "opening": {
            str(pid): record.as_dict()
            for pid, record in inputs.cohort.opening.items()
        },
    }
    input_path.write_text(
        json.dumps(input_record, indent=2, allow_nan=False) + "\n"
    )
    manifest = build_manifest(
        root=ROOT,
        implementation=[
            *sorted((ROOT / "src/populace_dynamics/track_a_v2").glob("*.py")),
            *sorted((ROOT / "scripts").glob("track_a_v2_*.py")),
        ],
        inputs={"invented_population": input_path},
        parameter_bundles={"runtime": runtime_parameter_bundle(inputs)},
        invented=True,
    )
    for name, artifact in (
        ("result.json", result),
        ("forced-refusal.json", refusal),
        ("hash-manifest.json", manifest),
    ):
        (output_dir / name).write_text(
            json.dumps(artifact, indent=2, allow_nan=False) + "\n"
        )
    lines = [
        INVENTED_HEADER,
        "registered, one-shot, post hoc, not blind",
        "PSID-seeded closed cohort; Python oracle (not Axiom)",
        "68 tabulations; 5 age cells each; 20 shared invented draws",
        "Fixed headlines: D×R0 and D×F0",
        "Forced refusal: step 2; 68 uncomputed rows; no tabulations",
        "",
        "The forced refusal is an intended unsupported-history violation.",
        "See result.json for every row, undefined cell and counter.",
    ]
    (output_dir / "RESULTS.md").write_text("\n".join(lines) + "\n")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / ".cache" / "track_a_v2_dry_run",
    )
    args = parser.parse_args(argv)
    print(INVENTED_HEADER, file=sys.stderr, flush=True)
    dry_run(
        args.output_dir,
        progress=lambda message: print(message, file=sys.stderr, flush=True),
    )
    print((args.output_dir / "RESULTS.md").read_text(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
