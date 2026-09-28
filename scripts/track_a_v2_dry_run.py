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
    file_record,
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


def _implementation_files() -> list[Path]:
    return sorted(
        [
            *(ROOT / "src/populace_dynamics/track_a_v2").glob("*.py"),
            *(ROOT / "scripts").glob("track_a_v2_*.py"),
        ],
        key=str,
    )


def _implementation_records() -> list[dict]:
    return [file_record(path, root=ROOT) for path in _implementation_files()]


def _write_json(path: Path, artifact: dict) -> None:
    if artifact.get("header") != INVENTED_HEADER:
        raise ValueError("invented output requires its explicit header")
    path.write_text(json.dumps(artifact, indent=2, allow_nan=False) + "\n")


def _execute(output_dir: Path, implementation: list[dict], progress) -> dict:
    inputs = invented_inputs()
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
    _write_json(input_path, input_record)
    parameter_bundle = runtime_parameter_bundle(inputs)
    captured = {}
    project = legacy._project_population

    def capture(*args, **kwargs):
        value = project(*args, **kwargs)
        captured["projection"] = value
        return value

    with patch.object(legacy, "_project_population", capture):
        result = run_joint(inputs, progress=progress)
    # §§10/17.4 require the actual attempt even if this dry-run assertion
    # fails. Never lose a returned refusal by checking its status first.
    _write_json(output_dir / "result.json", result)
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
    _write_json(output_dir / "forced-refusal.json", refusal)
    assert refusal["attempt"]["status"] == "refused"
    assert refusal["attempt"]["step"] == 2
    assert len(refusal["attempt"]["uncomputed_rows"]) == 68
    assert not refusal["rows"]

    # §17.6 is silent on edits during an invented run. Conservatively
    # refuse a manifest rather than bind outputs to implementation bytes
    # different from those present when this attempt started.
    if _implementation_records() != implementation:
        raise ValueError("implementation changed during the invented run")
    manifest = build_manifest(
        root=ROOT,
        implementation=[ROOT / record["path"] for record in implementation],
        inputs={"invented_population": input_path},
        parameter_bundles={"runtime": parameter_bundle},
        invented=True,
    )
    if (
        manifest["implementation"] != implementation
        or _implementation_records() != implementation
    ):
        raise ValueError(
            "implementation changed while building the invented manifest"
        )
    _write_json(output_dir / "hash-manifest.json", manifest)
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


def dry_run(output_dir: Path, *, progress=None) -> dict:
    """Keep one invented attempt and bind its manifest to unchanged code."""
    output_dir = _output_directory(output_dir)
    # §17.4 does not authorize replacing earlier invented evidence. Reserve
    # a new directory before computing anything, including an empty prior
    # directory, so failed and interrupted attempts remain distinguishable.
    output_dir.mkdir(parents=True, exist_ok=False)
    try:
        implementation = _implementation_records()
        _write_json(
            output_dir / "implementation-start.json",
            {"header": INVENTED_HEADER, "implementation": implementation},
        )
        return _execute(output_dir, implementation, progress)
    except (Exception, KeyboardInterrupt) as error:
        _write_json(
            output_dir / "dry-run-failure.json",
            {
                "header": INVENTED_HEADER,
                "type": type(error).__name__,
                "reason": str(error),
            },
        )
        raise


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
