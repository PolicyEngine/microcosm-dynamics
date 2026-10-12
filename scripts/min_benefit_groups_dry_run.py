"""Exercise 4 (Track M) group breakdowns on INVENTED data: the dry run.

INVENTED DATA - NOT A COMPARISON.  Runs
:func:`populace_dynamics.group_breakdowns.min_benefit.run_group_breakdowns`
end to end on an INVENTED PSID-shaped cohort
(``min_benefit_track_m.invented_psid``), INVENTED parameters
(``min_benefit_track_m.invented.invented_parameters``: no policyengine-us
checkout is read) and an INVENTED side frame passed through G1's real
builder (``group_breakdowns.common.invented_group_attribute_inputs``):

1. the same code runs once to stand in for the committed parent run (its
   result, JSON-encoded as the registered runner encodes it);
2. the adapter re-executes it, proves the reproduction exact, and only
   then reads the side frame and computes every row's, option's and d430's
   MINT8 cells, checking G3's Total/Female/Male cells against Track M's
   All/Women/Men cells;
3. the refusal is shown: with one committed cell moved by one unit in the
   last place, the adapter refuses before the side-frame loader is called
   and returns nothing to write.

Writes ``result.json`` and ``RESULTS.md`` to ``--output-dir`` (default
``docs/analysis/nasi_group_breakdowns_invented_20261001/
exercise_4_min_benefit``).  No PSID file, Census value, SSA value or
comparator value is read.

Usage::

    python scripts/min_benefit_groups_dry_run.py [--output-dir DIR]
"""

from __future__ import annotations

import argparse
import copy
import datetime
import hashlib
import json
import math
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from populace_dynamics.group_breakdowns import common  # noqa: E402
from populace_dynamics.group_breakdowns import (  # noqa: E402
    min_benefit as mb,
)
from populace_dynamics.min_benefit_track_m import (  # noqa: E402
    invented,
    invented_psid,
)
from populace_dynamics.min_benefit_track_m.evaluation import (  # noqa: E402
    INVENTED,
)

HEADER = common.INVENTED_DATA_HEADER
DEFAULT_OUTPUT_DIR = (
    ROOT
    / "docs"
    / "analysis"
    / "nasi_group_breakdowns_invented_20261001"
    / "exercise_4_min_benefit"
)
DEFAULT_SEED = 20261001
DEFAULT_FAMILY_UNITS = 80
DEFAULT_SIDE_FRAME_SEED = 4


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def invented_parent(
    frames: Any, parameters: Any, cola: Any
) -> common.CommittedArtifact:
    """The INVENTED stand-in for the committed run: the registered
    computation once, through the registered runner's JSON encoding."""

    run = mb.reexecute_track_m(
        frames,
        parameters,
        cola_rates=cola,
        data_provenance=INVENTED,
        registration_pointer=None,
        provenance_kind=INVENTED,
        source=dict(frames.provenance),
    )
    return common.CommittedArtifact(
        document=common.json_normalized(dict(run.result))
    )


def tampered(
    parent: common.CommittedArtifact,
) -> tuple[common.CommittedArtifact, str]:
    """``parent`` with MS0's first defined share moved by one ulp."""

    document = copy.deepcopy(dict(parent.document))
    cells = document["rows"]["MS0"]["tabulation"]["cells"]
    index = next(i for i, cell in enumerate(cells) if cell["defined"])
    value = cells[index]["share_percent"]
    cells[index]["share_percent"] = math.nextafter(value, math.inf)
    return (
        common.CommittedArtifact(document=document),
        f"$.rows.MS0.tabulation.cells[{index}].share_percent",
    )


def refusal_check(
    frames: Any, parameters: Any, cola: Any, parent: common.CommittedArtifact
) -> dict[str, Any]:
    """Run against a tampered parent: it must refuse before the loader."""

    bad, path = tampered(parent)
    calls: list[int] = []

    def loader(person_ids):
        calls.append(len(person_ids))
        raise AssertionError("the side frame was requested")

    try:
        mb.run_group_breakdowns(
            parameters=parameters,
            parent=bad,
            data_provenance=INVENTED,
            registration_pointer=None,
            load_cohort_inputs=lambda: frames,
            load_side_frame=loader,
            cola_rates=cola,
            provenance_kind=INVENTED,
            source=dict(frames.provenance),
        )
    except common.ReproductionMismatchError as error:
        return {
            "tampered_path": path,
            "tampering": "one unit in the last place (math.nextafter)",
            "refused": True,
            "side_frame_loader_called": bool(calls),
            "document_returned": False,
            "error": str(error),
        }
    raise AssertionError("the tampered parent was not refused")


def _cell_value(cell: dict[str, Any]) -> str:
    statistic = cell["statistics"][0]
    if not statistic["defined"]:
        return "undefined"
    return f"{statistic['value']:.1f}"


def _markdown(document: dict[str, Any]) -> str:
    result = document["result"]
    ms0 = result["breakdowns"]["MS0"]
    lines = [
        HEADER,
        "",
        "# Exercise 4 (Track M) by MINT8 subgroups: INVENTED dry run",
        "",
        HEADER + ". Every number below comes from an INVENTED PSID-shaped "
        "cohort, INVENTED parameters and an INVENTED side frame. None is "
        "a PSID, SSA, Census or comparator value, and none is a result.",
        "",
        "## What ran",
        "",
        "- An INVENTED stand-in for the committed run (the registered "
        "computation, once).",
        f"- Re-execution and exact reproduction: "
        f"{len(result['reproduction']['checks'])} checks, all identical "
        f"({result['reproduction']['comparison']['rule']}).",
        f"- Consistency of G3's Total/Female/Male cells with Track M's "
        f"All/Women/Men cells: "
        f"{result['consistency_with_registered_cells']['n_checks']} checks, "
        "all identical.",
        f"- Refusal shown: a parent with "
        f"`{document['refusal']['tampered_path']}` moved one ulp was "
        f"refused (side-frame loader called: "
        f"{document['refusal']['side_frame_loader_called']}).",
        f"- Location rule (for the real parent, which records the COLA "
        f"history by an absolute path): "
        f"{result['reproduction']['location_fields']['rule']}.",
        "",
        "## Group attributes (INVENTED)",
        "",
        "| Dimension | Classified | Unclassified | Reasons |",
        "|---|---:|---:|---|",
    ]
    for summary in result["breakdown"]["assignment"]["dimensions"]:
        reasons = ", ".join(
            f"{reason}: {count}"
            for reason, count in summary["unclassified_reasons"].items()
        )
        lines.append(
            f"| {summary['label']} | {summary['n_classified']} | "
            f"{summary['n_unclassified']} | {reasons or '-'} |"
        )
    lines += [
        "",
        "## MS0, share receiving a minimum by group (INVENTED, percent)",
        "",
        "| Group | Row | Option 2 | Option 3 | Option 4 | Option 5 | n |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    by_option = {
        number: {d["key"]: d for d in ms0[number]["dimensions"]}
        for number in ("2", "3", "4", "5")
    }
    for dimension in ms0["2"]["dimensions"]:
        for position, cell in enumerate(dimension["cells"]):
            values = [
                _cell_value(by_option[n][dimension["key"]]["cells"][position])
                for n in ("2", "3", "4", "5")
            ]
            n = cell["statistics"][0]["unweighted_n"]
            lines.append(
                f"| {dimension['label']} | {cell['label']} | "
                + " | ".join(values)
                + f" | {n} |"
            )
    lines += [
        "",
        "## Not computed",
        "",
    ]
    for name, reason in result["not_computed"]["dimensions"].items():
        lines.append(f"- `{name}`: {reason}")
    for name, item in result["not_computed"]["statistics"].items():
        lines.append(f"- `{name}`: {item['reason']}")
    lines += [
        "",
        "## Reproduce",
        "",
        "```",
        document["run"]["command"],
        "```",
        "",
        f"`result.json` holds the full document. {HEADER}.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--family-units", type=int, default=DEFAULT_FAMILY_UNITS
    )
    parser.add_argument(
        "--side-frame-seed", type=int, default=DEFAULT_SIDE_FRAME_SEED
    )
    args = parser.parse_args(argv)
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    parameters, cola = invented.invented_parameters()
    frames = invented_psid.invented_cohort_inputs(
        seed=args.seed, n_family_units=args.family_units
    )
    parent = invented_parent(frames, parameters, cola)
    side_frames = mb.invented_group_attribute_loader(
        frames, seed=args.side_frame_seed
    )
    result = mb.run_group_breakdowns(
        parameters=parameters,
        parent=parent,
        data_provenance=INVENTED,
        registration_pointer=None,
        load_cohort_inputs=lambda: frames,
        load_side_frame=side_frames,
        cola_rates=cola,
        provenance_kind=INVENTED,
        source=dict(frames.provenance),
    )
    document = {
        "header": HEADER,
        "description": (
            "Exercise 4 (Track M) group breakdowns on an INVENTED "
            "PSID-shaped cohort with INVENTED parameters and an INVENTED "
            "side frame, through the real Track M, G1, G2 and G3 code. Not "
            "PSID values, not a result, not a comparison."
        ),
        "inputs": {
            "cohort": (
                "min_benefit_track_m.invented_psid.invented_cohort_inputs"
            ),
            "seed": args.seed,
            "family_units": args.family_units,
            "parameters": (
                "min_benefit_track_m.invented.invented_parameters (INVENTED)"
            ),
            "side_frame": (
                "group_breakdowns.common.invented_group_attribute_inputs "
                "through cohorts.group_attributes.build_group_attributes"
            ),
            "side_frame_seed": args.side_frame_seed,
        },
        "refusal": refusal_check(frames, parameters, cola, parent),
        "result": result,
        "run": {
            "started": started,
            "finished": datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat(),
            "git_head": _git("rev-parse", "HEAD"),
            "git_clean": _git("status", "--porcelain") == "",
            "python": platform.python_version(),
            "command": " ".join(
                [
                    "python",
                    "scripts/min_benefit_groups_dry_run.py",
                    *(sys.argv[1:] if argv is None else argv),
                ]
            ),
        },
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    path = args.output_dir / "result.json"
    path.write_text(
        json.dumps(document, indent=1, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "RESULTS.md").write_text(
        _markdown(document), encoding="utf-8"
    )
    print(path, hashlib.sha256(path.read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
