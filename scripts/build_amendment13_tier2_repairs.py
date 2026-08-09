"""Publish Amendment 13's operative tier-2 repair overlays and era seals.

The execution-law validator is the sole source of the repair objects.  This
publisher writes each of the fourteen document overlays and each of the six
successor-era seals as a separate canonical JSON artifact so that the two
enacted first-add commits remain distinguishable.  It emits no authority,
certification, Q5 input, or production output.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import validate_amendment13_execution_law as a13  # noqa: E402


class PublicationError(RuntimeError):
    """Raised when the operative repair publication fails closed."""


TIER2_ROOT_RELATIVE = Path("docs/analysis/amendment_12_rq_catalog_tier2")
TIER2_ROOT = ROOT / TIER2_ROOT_RELATIVE
OVERLAY_DIRECTORY = Path("amendment_13_repair_overlays_v1")
SEAL_DIRECTORY = Path("amendment_13_successor_era_seals_v1")
ARTIFACT_SELECTIONS = ("overlays", "seals", "all")

OVERLAY_POSITIONS = (
    7,
    10,
    11,
    12,
    13,
    15,
    17,
    19,
    36,
    52,
    56,
    58,
    66,
    70,
)
EXPECTED_REPAIR_COUNTS_BY_DOCUMENT = {
    7: 2,
    10: 1,
    11: 1,
    12: 1,
    13: 1,
    15: 2,
    17: 3,
    19: 2,
    36: 9,
    52: 5,
    56: 11,
    58: 3,
    66: 3,
    70: 2,
}
EXPECTED_ERA_REPAIR_PROJECTION = (8, 5, 9, 19, 5, 0)
SUCCESSOR_DOMAINS = (
    "semantically_incompatible_local_proof_successor_rows",
    "incomplete_fragment_terminal_successor_rows",
    "composed_fragment_successor_rows",
    "doc036_aggregate_domain_successor_rows",
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise PublicationError(message)


def overlay_relative_path(position: int) -> Path:
    """Return the fixed path for one exact document overlay."""

    return OVERLAY_DIRECTORY / (
        f"document_{position:03d}_repair_overlay_v1.json"
    )


def seal_relative_path(era_order_position: int) -> Path:
    """Return the fixed path for one exact successor-era seal."""

    return SEAL_DIRECTORY / (
        f"era_{era_order_position:02d}_successor_seal_v1.json"
    )


def _overlay_successors(overlay: Mapping[str, Any]) -> list[Any]:
    return [row for key in SUCCESSOR_DOMAINS for row in overlay[key]]


def _require_no_authority(value: Any, label: str) -> None:
    """Reject authority-like output anywhere in a published repair row."""

    if isinstance(value, Mapping):
        for key, member in value.items():
            if key == "authority_kind":
                _require(
                    member == "PROSPECTIVE_NONAUTHORITY",
                    f"{label} emits authority",
                )
            if key in {
                "authority_emitted",
                "certification_emitted",
                "q5_input_emitted",
                "production_output_emitted",
            }:
                _require(member is False, f"{label} emits forbidden output")
            _require_no_authority(member, label)
    elif isinstance(value, list):
        for member in value:
            _require_no_authority(member, label)


def validate_publication_law(law: Mapping[str, Any]) -> None:
    """Enforce the publication-level census and cross-file coherence."""

    _require(
        law["status"] == a13.RATIFICATION_BOUND_TEMPLATE_STATUS,
        "publication is not bound to the operative ratification closure",
    )
    _require(
        law["authority_emitted"] is False
        and law["certification_emitted"] is False,
        "execution law emits authority or certification",
    )
    integrity = law["integrity"]
    _require(
        (
            integrity["incompatible_proof_count"],
            integrity["incomplete_fragment_count"],
            integrity["composed_fragment_count"],
            integrity["doc036_aggregate_domain_count"],
            integrity["repair_count"],
            integrity["supersession_count"],
            integrity["overlay_count"],
            integrity["successor_era_seal_count"],
        )
        == (28, 8, 2, 8, 46, 46, 14, 6),
        "operative repair census is not 28 + 8 + 2 + 8 = 46",
    )

    overlays = law["repair_overlay_rows"]
    _require(
        tuple(row["document_source_position"] for row in overlays)
        == OVERLAY_POSITIONS,
        "repair overlay document domain or order drift",
    )
    counts_by_document = {
        row["document_source_position"]: len(_overlay_successors(row))
        for row in overlays
    }
    _require(
        counts_by_document == EXPECTED_REPAIR_COUNTS_BY_DOCUMENT,
        "per-document repair census drift",
    )
    all_successor_ids: list[str] = []
    all_supersession_successor_ids: list[str] = []
    for overlay in overlays:
        successors = _overlay_successors(overlay)
        edges = overlay["predecessor_supersession_rows"]
        _require(
            len(successors) == len(edges),
            "overlay does not contain one supersession edge per successor",
        )
        _require(
            overlay["predecessor_source_rows_retained"] is True
            and overlay["predecessor_source_row_erasure_permitted"] is False,
            "overlay violates append-only predecessor retention",
        )
        all_successor_ids.extend(row["successor_row_id"] for row in successors)
        all_supersession_successor_ids.extend(
            row["successor_row_id"] for row in edges
        )
        _require_no_authority(
            overlay,
            f"document {overlay['document_source_position']:03d} overlay",
        )
    _require(
        len(all_successor_ids) == 46
        and Counter(all_successor_ids)
        == Counter(all_supersession_successor_ids)
        == Counter({row_id: 1 for row_id in all_successor_ids}),
        "the overlays do not reconcile to 46 unique one-to-one repairs",
    )

    overlay_by_id = {row["repair_overlay_id"]: row for row in overlays}
    era_by_document_position = {
        row["document_source_position"]: row["predecessor_era_id"]
        for row in overlays
    }
    top_level_successors = [
        row for key in SUCCESSOR_DOMAINS for row in law[key]
    ]
    top_level_edges = law["predecessor_supersession_rows"]
    seals = law["successor_era_seal_rows"]
    _require(
        tuple(row["era_order_position"] for row in seals)
        == tuple(range(1, 7)),
        "successor-era seal domain or order drift",
    )
    _require(
        tuple(len(row["successor_row_ids"]) for row in seals)
        == EXPECTED_ERA_REPAIR_PROJECTION,
        "successor-era repair projection is not 8/5/9/19/5/0",
    )
    for seal in seals:
        era_id = seal["era_id"]
        era_overlays = [
            row for row in overlays if row["predecessor_era_id"] == era_id
        ]
        expected_overlay_ids = [
            row["repair_overlay_id"] for row in era_overlays
        ]
        expected_successor_ids = [
            row["successor_row_id"]
            for row in top_level_successors
            if era_by_document_position[row["document_source_position"]]
            == era_id
        ]
        expected_edge_ids = [
            row["supersession_row_id"]
            for row in top_level_edges
            if era_by_document_position[row["document_source_position"]]
            == era_id
        ]
        _require(
            seal["repair_overlay_ids"] == expected_overlay_ids
            and seal["successor_row_ids"] == expected_successor_ids
            and seal["supersession_row_ids"] == expected_edge_ids,
            f"era {seal['era_order_position']} seal projection drift",
        )
        _require(
            all(row_id in overlay_by_id for row_id in expected_overlay_ids),
            "successor-era seal references an unknown overlay",
        )
        _require_no_authority(
            seal, f"era {seal['era_order_position']} successor seal"
        )
    empty_era = seals[-1]
    _require(
        empty_era["repair_overlay_ids"] == []
        and empty_era["successor_row_ids"] == []
        and empty_era["supersession_row_ids"] == []
        and set(empty_era["repair_counts"].values()) == {0},
        "era 6 is not the enacted empty-but-sealed era",
    )


def build_artifact_values() -> (
    tuple[dict[str, Any], dict[Path, dict[str, Any]]]
):
    """Reconstruct and project the exact operative publication objects."""

    law = a13.build_ratification_bound_execution_template()
    validate_publication_law(law)
    values: dict[Path, dict[str, Any]] = {}
    for overlay in law["repair_overlay_rows"]:
        path = overlay_relative_path(overlay["document_source_position"])
        _require(path not in values, f"duplicate artifact path: {path}")
        values[path] = overlay
    for seal in law["successor_era_seal_rows"]:
        path = seal_relative_path(seal["era_order_position"])
        _require(path not in values, f"duplicate artifact path: {path}")
        values[path] = seal
    _require(len(values) == 20, "publication does not contain 20 artifacts")
    return law, values


def render_artifact_values(
    values: Mapping[Path, Mapping[str, Any]],
) -> dict[Path, bytes]:
    """Render exact rows with the execution law's canonical JSON codec."""

    return {
        path: a13.canonical_json_bytes(value) for path, value in values.items()
    }


def _selected_paths(values: Mapping[Path, Any], artifacts: str) -> set[Path]:
    _require(
        artifacts in ARTIFACT_SELECTIONS,
        f"unknown artifact selection: {artifacts}",
    )
    return {
        path
        for path in values
        if artifacts == "all"
        or (artifacts == "overlays" and path.parent == OVERLAY_DIRECTORY)
        or (artifacts == "seals" and path.parent == SEAL_DIRECTORY)
    }


def validate_artifact_bundle(
    actual: Mapping[Path, bytes],
    expected_values: Mapping[Path, Mapping[str, Any]],
    *,
    artifacts: str,
) -> None:
    """Require exact paths, strict canonical bytes, and deep equality."""

    expected_paths = _selected_paths(expected_values, artifacts)
    _require(
        set(actual) == expected_paths,
        f"{artifacts} artifact path domain drift",
    )
    for path in sorted(expected_paths):
        raw = actual[path]
        try:
            value = a13._strict_canonical_json(raw, path.as_posix())
        except a13.LawError as error:
            raise PublicationError(str(error)) from error
        _require(
            value == expected_values[path],
            f"{path.as_posix()} differs from the operative reconstruction",
        )
        _require(
            raw == a13.canonical_json_bytes(expected_values[path]),
            f"{path.as_posix()} has noncanonical or unequal bytes",
        )
        _require_no_authority(value, path.as_posix())


def read_artifact_bundle(
    output_root: Path,
    expected_values: Mapping[Path, Mapping[str, Any]],
    *,
    artifacts: str,
) -> dict[Path, bytes]:
    """Read exactly one selected artifact domain from disk."""

    selected = _selected_paths(expected_values, artifacts)
    directories = {path.parent for path in selected}
    actual: dict[Path, bytes] = {}
    for relative_directory in directories:
        directory = output_root / relative_directory
        if not directory.exists():
            continue
        _require(
            directory.is_dir(),
            f"artifact directory is not a directory: {directory}",
        )
        for candidate in directory.iterdir():
            _require(
                candidate.is_file() and not candidate.is_symlink(),
                f"unexpected non-file artifact entry: {candidate}",
            )
            actual[relative_directory / candidate.name] = (
                candidate.read_bytes()
            )
    return actual


def _require_no_unexpected_entries(
    output_root: Path,
    expected_values: Mapping[Path, Mapping[str, Any]],
    *,
    artifacts: str,
) -> None:
    selected = _selected_paths(expected_values, artifacts)
    expected_by_directory = {
        directory: {path.name for path in selected if path.parent == directory}
        for directory in {path.parent for path in selected}
    }
    for relative_directory, expected_names in expected_by_directory.items():
        directory = output_root / relative_directory
        if not directory.exists():
            continue
        _require(
            directory.is_dir(),
            f"artifact path is not a directory: {directory}",
        )
        actual_names = {entry.name for entry in directory.iterdir()}
        _require(
            actual_names <= expected_names,
            f"unexpected entries in {directory}",
        )


def write_artifact_bundle(
    output_root: Path,
    expected_values: Mapping[Path, Mapping[str, Any]],
    *,
    artifacts: str,
) -> dict[Path, bytes]:
    """Write one selected exact domain without deleting any artifact."""

    _require_no_unexpected_entries(
        output_root, expected_values, artifacts=artifacts
    )
    rendered = render_artifact_values(expected_values)
    selected = _selected_paths(expected_values, artifacts)
    for relative_path in sorted(selected):
        target = output_root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(rendered[relative_path])
    actual = read_artifact_bundle(
        output_root, expected_values, artifacts=artifacts
    )
    validate_artifact_bundle(actual, expected_values, artifacts=artifacts)
    return actual


def _run_git(
    repo_root: Path,
    *arguments: str,
) -> subprocess.CompletedProcess[bytes]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("GIT_")
    }
    environment["GIT_NO_REPLACE_OBJECTS"] = "1"
    return subprocess.run(
        ["git", "--no-replace-objects", *arguments],
        cwd=repo_root,
        check=False,
        capture_output=True,
        env=environment,
    )


def _git_output(repo_root: Path, *arguments: str) -> bytes:
    result = _run_git(repo_root, *arguments)
    _require(
        result.returncode == 0,
        f"git command failed: {' '.join(arguments)}",
    )
    return result.stdout


def _first_add_commit(repo_root: Path, relative_path: Path) -> str | None:
    result = _run_git(
        repo_root,
        "log",
        "--full-history",
        "--diff-filter=A",
        "--format=%H",
        "HEAD",
        "--",
        relative_path.as_posix(),
    )
    _require(
        result.returncode == 0, f"cannot inspect first-add for {relative_path}"
    )
    commits = result.stdout.decode("ascii").splitlines()
    _require(
        len(commits) <= 1,
        f"{relative_path.as_posix()} has more than one first-add commit",
    )
    return commits[0] if commits else None


def _require_exact_single_parent_commit(repo_root: Path, commit: str) -> None:
    resolved = (
        _git_output(repo_root, "rev-parse", "--verify", f"{commit}^{{commit}}")
        .decode("ascii")
        .strip()
    )
    _require(resolved == commit, f"{commit} is not an exact commit object")
    commit_line = (
        _git_output(repo_root, "rev-list", "--parents", "-n", "1", commit)
        .decode("ascii")
        .split()
    )
    _require(len(commit_line) == 2, f"{commit} is not a single-parent commit")


def _is_strict_ancestor(
    repo_root: Path, ancestor: str, descendant: str
) -> bool:
    if ancestor == descendant:
        return False
    result = _run_git(
        repo_root, "merge-base", "--is-ancestor", ancestor, descendant
    )
    _require(
        result.returncode in {0, 1},
        "git could not evaluate strict commit ancestry",
    )
    return result.returncode == 0


def _validate_first_add_relationships(
    *,
    governing_commit: str,
    overlay_commits: Mapping[int, str | None],
    seal_commits: Mapping[int, str | None],
    overlay_era_positions: Mapping[int, int],
    strict_ancestor: Callable[[str, str], bool],
    required: str = "none",
) -> str:
    """Validate the enacted commit ordering from resolved first-adds."""

    _require(required in {"none", "overlays", "all"}, "invalid required stage")
    present_overlays = {value for value in overlay_commits.values() if value}
    present_seals = {value for value in seal_commits.values() if value}
    if present_overlays:
        _require(
            all(overlay_commits.values()) and len(present_overlays) == 1,
            "the fourteen overlays are not one complete first-add batch",
        )
        overlay_commit = next(iter(present_overlays))
        _require(
            strict_ancestor(governing_commit, overlay_commit),
            "the governing Amendment-13 ratification is not a strict ancestor "
            "of the overlay first-add batch",
        )
    if present_seals:
        _require(
            all(seal_commits.values()) and len(present_seals) == 1,
            "the six seals are not one complete first-add batch",
        )
        _require(
            all(overlay_commits.values()),
            "a seal was first-added before every overlay",
        )
        for position, overlay_commit in overlay_commits.items():
            seal_commit = seal_commits[overlay_era_positions[position]]
            _require(
                overlay_commit is not None
                and seal_commit is not None
                and strict_ancestor(overlay_commit, seal_commit),
                "an overlay first-add is not a strict ancestor of its era seal",
            )
    if required in {"overlays", "all"}:
        _require(
            all(overlay_commits.values()), "overlay batch is not committed"
        )
    if required == "all":
        _require(all(seal_commits.values()), "seal batch is not committed")
    if present_seals:
        return "seals_committed"
    if present_overlays:
        return "overlays_committed"
    return "prospective"


def validate_git_publication_order(
    law: Mapping[str, Any],
    expected_values: Mapping[Path, Mapping[str, Any]],
    *,
    repo_root: Path = ROOT,
    required: str = "none",
) -> dict[str, Any]:
    """Validate first-add bytes, commit shape, and strict ancestry."""

    governing_commit = law["governing_amendment13_ratification_identity"][
        "ratification_commit"
    ]
    overlay_commits: dict[int, str | None] = {}
    seal_commits: dict[int, str | None] = {}
    overlay_era_positions: dict[int, int] = {}
    era_position_by_id = {
        row["era_id"]: row["era_order_position"]
        for row in law["successor_era_seal_rows"]
    }
    for overlay in law["repair_overlay_rows"]:
        position = overlay["document_source_position"]
        path = TIER2_ROOT_RELATIVE / overlay_relative_path(position)
        overlay_commits[position] = _first_add_commit(repo_root, path)
        overlay_era_positions[position] = era_position_by_id[
            overlay["predecessor_era_id"]
        ]
    for seal in law["successor_era_seal_rows"]:
        era_position = seal["era_order_position"]
        path = TIER2_ROOT_RELATIVE / seal_relative_path(era_position)
        seal_commits[era_position] = _first_add_commit(repo_root, path)

    path_commit_pairs = [
        (
            TIER2_ROOT_RELATIVE / overlay_relative_path(position),
            commit,
        )
        for position, commit in overlay_commits.items()
    ] + [
        (TIER2_ROOT_RELATIVE / seal_relative_path(position), commit)
        for position, commit in seal_commits.items()
    ]
    for path, commit in path_commit_pairs:
        if commit is None:
            continue
        _require_exact_single_parent_commit(repo_root, commit)
        relative_to_tier2 = path.relative_to(TIER2_ROOT_RELATIVE)
        expected_raw = a13.canonical_json_bytes(
            expected_values[relative_to_tier2]
        )
        first_add_raw = _git_output(
            repo_root, "show", f"{commit}:{path.as_posix()}"
        )
        head_raw = _git_output(repo_root, "show", f"HEAD:{path.as_posix()}")
        _require(
            first_add_raw == expected_raw and head_raw == expected_raw,
            f"{path.as_posix()} differs at first-add or HEAD",
        )

    status = _validate_first_add_relationships(
        governing_commit=governing_commit,
        overlay_commits=overlay_commits,
        seal_commits=seal_commits,
        overlay_era_positions=overlay_era_positions,
        strict_ancestor=lambda ancestor, descendant: _is_strict_ancestor(
            repo_root, ancestor, descendant
        ),
        required=required,
    )
    return {
        "status": status,
        "governing_amendment13_ratification_commit": governing_commit,
        "overlay_first_add_commits": overlay_commits,
        "seal_first_add_commits": seal_commits,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifacts",
        choices=ARTIFACT_SELECTIONS,
        default="all",
        help="artifact domain to write or check (default: all)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="compare existing artifacts instead of writing them",
    )
    parser.add_argument(
        "--require-committed",
        action="store_true",
        help="also require the selected first-add batch(es) in HEAD",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=TIER2_ROOT,
        help="artifact root (default: the committed tier-2 directory)",
    )
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    parser = _parser()
    options = parser.parse_args(arguments)
    output_root = options.output_root.resolve()
    is_repository_publication = output_root == TIER2_ROOT.resolve()
    if options.require_committed and not is_repository_publication:
        parser.error("--require-committed requires the repository output root")

    try:
        law, expected_values = build_artifact_values()
        required = "none"
        if options.require_committed:
            required = "overlays" if options.artifacts == "overlays" else "all"
        if options.artifacts == "seals" and not options.require_committed:
            required = "overlays"
        if is_repository_publication:
            order = validate_git_publication_order(
                law,
                expected_values,
                required=(
                    "overlays"
                    if not options.check and options.artifacts == "all"
                    else required
                ),
            )
        else:
            order = {"status": "external_output_root_not_git_checked"}

        if options.check:
            actual = read_artifact_bundle(
                output_root,
                expected_values,
                artifacts=options.artifacts,
            )
            validate_artifact_bundle(
                actual,
                expected_values,
                artifacts=options.artifacts,
            )
        else:
            if options.require_committed:
                raise PublicationError(
                    "--require-committed is only meaningful with --check"
                )
            if options.artifacts in {"seals", "all"}:
                _require(
                    order["status"]
                    in {"overlays_committed", "seals_committed"},
                    "commit the complete overlay batch before writing seals",
                )
            actual = write_artifact_bundle(
                output_root,
                expected_values,
                artifacts=options.artifacts,
            )
        print(
            json.dumps(
                {
                    "status": "PASS",
                    "mode": "check" if options.check else "write",
                    "artifacts": options.artifacts,
                    "artifact_count": len(actual),
                    "repair_count": 46,
                    "supersession_count": 46,
                    "era_projection": list(EXPECTED_ERA_REPAIR_PROJECTION),
                    "git_publication_status": order["status"],
                    "authority_emitted": False,
                    "certification_emitted": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
    except PublicationError as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
