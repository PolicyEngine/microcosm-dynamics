"""Shared reproduction gates and composition for all four NASI adapters.

Every adapter must verify all frozen parent cells before loading group
attributes or calculating group measures. Exact comparisons share one
JSON-tree implementation: scalar types and signed binary64 zero remain
exact, tuple/list array semantics agree, and non-string keys and nonfinite
values refuse. Refusals disclose paths only. Projection retained frames
also remain sealed until grouping.

Registration preflight requires clean registered HEAD and a new pair in
this checkout's runs directory. The exclusive paired writer serializes
both finite documents first and rolls back only the inodes it created.
Environment recording composes the frozen Track A resolver. G1 supplies
cohort-side attributes, G2 supplies measures, and G3 supplies assignments
and cells; no helper here reads PSID microdata directly.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import re
import subprocess
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from populace_dynamics.cohorts import group_attributes as g1
from populace_dynamics.cola_track_a.config import REGISTERED_ROWS
from populace_dynamics.data import group_attributes_psid as gap
from populace_dynamics.estimates import group_breakdown as g3
from populace_dynamics.estimates import lifetime_measures as g2
from populace_dynamics.estimates.cola_age_profile import ColaAgeProfileConfig

POST_HOC_LABEL = "registered, one-shot, post hoc, not blind"


REPORT_ONLY_LABEL = "report-only"


POST_HOC_LABELS: tuple[str, ...] = (POST_HOC_LABEL, REPORT_ONLY_LABEL)


INVENTED_DATA_HEADER = "INVENTED DATA - NOT A COMPARISON"


REGISTRATION_POINTER = g3.REGISTRATION_POINTER


EXACT_COMPARISON: dict[str, Any] = {
    "rule": (
        "exact: both sides are encoded with json.dumps(allow_nan=False) "
        "and decoded, then every leaf must be equal in type and value, "
        "every float bit for bit (float.hex, so -0.0 differs from 0.0), "
        "every mapping with the same keys and every list with the same "
        "length and order"
    ),
    "tolerance": None,
    "tolerance_note": (
        "none: the registered runners write floats with Python's "
        "shortest round-trip repr, so a reproduction in the recorded "
        "environment is bit-identical; any difference, including a "
        "last-bit difference from floating-point summation in another "
        "numpy build, refuses the run before any group attribute is read"
    ),
    "reports": (
        "differing paths only, never a value (a refusal on real data "
        "prints no outcome)"
    ),
}


def _same_leaf(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, float):
        return left.hex() == right.hex()
    return left == right


def leaf_differences(
    committed: Any, recomputed: Any, path: str = "$"
) -> tuple[list[str], int]:
    """``(paths that differ, leaves compared)`` of two decoded documents.

    Mappings must have the same keys (a key on one side only is a
    difference at that key's path), lists the same length; leaves must be
    equal in type and value, floats bit for bit.  Paths name keys and list
    positions only, never a value.
    """

    if isinstance(committed, dict) and isinstance(recomputed, dict):
        differences: list[str] = []
        compared = 0
        for key in sorted(set(committed) | set(recomputed), key=str):
            where = f"{path}.{key}"
            if key not in committed or key not in recomputed:
                differences.append(f"{where} (present on one side only)")
                continue
            found, n = leaf_differences(committed[key], recomputed[key], where)
            differences.extend(found)
            compared += n
        return differences, compared
    if isinstance(committed, list) and isinstance(recomputed, list):
        if len(committed) != len(recomputed):
            return [f"{path} (lengths differ)"], 0
        differences = []
        compared = 0
        for index, (left, right) in enumerate(
            zip(committed, recomputed, strict=True)
        ):
            found, n = leaf_differences(left, right, f"{path}[{index}]")
            differences.extend(found)
            compared += n
        return differences, compared
    if isinstance(committed, dict | list) or isinstance(
        recomputed, dict | list
    ):
        return [f"{path} (structure differs)"], 0
    return ([] if _same_leaf(committed, recomputed) else [path]), 1


@dataclass(frozen=True)
class ReproductionCheck:
    """One comparison of a recomputed block with the committed one."""

    name: str
    n_leaves: int
    differences: tuple[str, ...]

    @property
    def identical(self) -> bool:
        return not self.differences

    def as_dict(self, *, max_paths: int = 50) -> dict[str, Any]:
        return {
            "name": self.name,
            "identical": self.identical,
            "n_leaves_compared": self.n_leaves,
            "n_differences": len(self.differences),
            "differing_paths": list(self.differences[:max_paths]),
        }

    @property
    def compared_leaf_cells(self) -> int:
        """Compatibility with the uniform-cut adapter's evidence record."""
        return self.n_leaves

    @property
    def comparison(self) -> str:
        return "bit-exact binary64 floats and exact JSON scalars"

    @property
    def absolute_tolerance(self) -> float:
        return 0.0

    @property
    def relative_tolerance(self) -> float:
        return 0.0


def require_identical(
    checks: Iterable[ReproductionCheck], *, stage: str
) -> None:
    """Refuse unless every check is identical (paths only in the error)."""

    failed = [check for check in checks if not check.identical]
    if failed:
        listed = "; ".join(
            f"{check.name}: {len(check.differences)} differing paths, "
            f"first {list(check.differences[:5])}"
            for check in failed
        )
        raise ReproductionMismatchError(
            f"{stage}: the recomputed result differs from the committed "
            f"artifact ({listed}); refused before any group attribute or "
            "group cell, and nothing is written"
        )


def file_sha256(path: Path | str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path: Path, text: str) -> None:
    """Create ``path`` exclusively: never overwrite (one shot)."""

    with Path(path).open("x", encoding="utf-8") as handle:
        handle.write(text)


@dataclass(frozen=True)
class CommittedArtifact:
    """A committed run artifact, its SHA-256 and its sidecar.

    ``path``, ``sha256`` and ``sidecar`` are ``None`` for an INVENTED
    parent held in memory by a dry run.
    """

    document: Mapping[str, Any]
    path: Path | None = None
    sha256: str | None = None
    sidecar: Mapping[str, Any] | None = None

    def record(self, root: Path | None = None) -> dict[str, Any]:
        where = None
        if self.path is not None:
            where = str(self.path)
            if root is not None:
                try:
                    where = str(Path(self.path).relative_to(root))
                except ValueError:
                    pass
        return {
            "path": where,
            "sha256": self.sha256,
            "sidecar_artifact_sha256": (
                None
                if self.sidecar is None
                else self.sidecar.get("artifact_sha256")
            ),
            "registration_pointer": self.document.get("registration_pointer"),
            "registered_commit": (self.document.get("run") or {}).get(
                "registered_commit"
            ),
        }


def load_committed_artifact(
    path: Path, *, expected_sha256: str
) -> CommittedArtifact:
    """Read a committed artifact, refusing other bytes or an unbound sidecar.

    The file's SHA-256 must equal ``expected_sha256`` and its ``.env.json``
    sidecar must name the file and bind the same SHA-256.
    """

    path = Path(path)
    try:
        digest = assert_sha256(path, expected_sha256)
    except GroupBreakdownRefusal as error:
        raise GroupBreakdownRefusal(
            f"{path.name} is not the committed artifact (SHA-256 pin)"
        ) from error
    sidecar_path = path.with_suffix(".env.json")
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    if sidecar.get("artifact") != path.name:
        raise ValueError(f"{sidecar_path.name} does not name {path.name}")
    if sidecar.get("artifact_sha256") != digest:
        raise ValueError(
            f"{sidecar_path.name} does not bind {path.name}'s bytes"
        )
    return CommittedArtifact(
        document=json.loads(path.read_text(encoding="utf-8")),
        path=path,
        sha256=digest,
        sidecar=sidecar,
    )


_SIDE_FRAME_COLUMNS: dict[str, tuple[str, str, str]] = {
    "race_ethnicity": (
        "race_ethnicity_mint8",
        "race_ethnicity_mint8_status",
        "race_ethnicity_status",
    ),
    "country_of_birth": (
        "country_of_birth_mint8",
        "country_of_birth_mint8_status",
        "country_of_birth_status",
    ),
}


@dataclass(frozen=True)
class SchemeCodes:
    """Codes for one G3 dimension and the unclassified codes declared."""

    codes: tuple[Any, ...]
    unclassified_codes: tuple[str, ...]
    rule: str


def _text(value: Any) -> str | None:
    if value is None or value is pd.NA:
        return None
    if isinstance(value, float) and np.isnan(value):
        return None
    return str(value)


def side_frame_codes(
    attributes: pd.DataFrame, dimension: g3.Dimension
) -> SchemeCodes:
    """G1's MINT8 labels as the codes of G3's ``dimension``.

    A row G1 assigns takes the code of the G3 category whose printed
    label equals G1's label (both are SSA's verbatim MINT8 row labels; a
    label no category prints is refused).  A row G1 leaves unresolved
    takes G1's status (``unresolved:<reason>``, for example a U.S.
    territory birth); a row whose attribute is unknown takes
    ``attribute_unknown:<the attribute's G1 status>`` (for example
    ``never_head_or_spouse``: the PSID asks race and birthplace of heads
    and spouses only).  Those codes are declared unclassified.
    """

    if dimension.key not in _SIDE_FRAME_COLUMNS:
        raise ValueError(
            f"{dimension.key} is not a side-frame dimension "
            f"({sorted(_SIDE_FRAME_COLUMNS)})"
        )
    label_column, status_column, attribute_column = _SIDE_FRAME_COLUMNS[
        dimension.key
    ]
    by_label = {
        category.label: category.codes[0] for category in dimension.categories
    }
    codes: list[Any] = []
    declared: set[str] = set()
    for label, status, attribute in zip(
        attributes[label_column],
        attributes[status_column],
        attributes[attribute_column],
        strict=True,
    ):
        label, status, attribute = (
            _text(label),
            _text(status),
            _text(attribute),
        )
        if status == g1.ASSIGNED:
            if label not in by_label:
                raise ValueError(
                    f"{dimension.key}: G1 label {label!r} is not one of "
                    f"G3's labels {sorted(by_label)}"
                )
            codes.append(by_label[label])
            continue
        if label is not None:
            raise ValueError(
                f"{dimension.key}: a row G1 does not assign carries a label"
            )
        if status is not None and status.startswith("unresolved:"):
            code = status
        elif status == g1.ATTRIBUTE_UNKNOWN:
            code = f"{g1.ATTRIBUTE_UNKNOWN}:{attribute or 'unknown'}"
        else:
            raise ValueError(
                f"{dimension.key}: undocumented G1 status {status!r}"
            )
        codes.append(code)
        declared.add(code)
    return SchemeCodes(
        codes=tuple(codes),
        unclassified_codes=tuple(sorted(declared)),
        rule=(
            f"G1 column {label_column!r} (SSA's verbatim MINT8 label) to the "
            f"G3 {dimension.key!r} category printing that label; a row G1 "
            f"does not assign is unclassified with code "
            f"'unresolved:<reason>' ({status_column}) or "
            f"'attribute_unknown:<{attribute_column}>'"
        ),
    )


def education_years(attributes: pd.DataFrame) -> tuple[int | None, ...]:
    """G1's resolved years of schooling, ``None`` where unknown."""

    out: list[int | None] = []
    for value in attributes["education_years"]:
        if value is None or value is pd.NA or pd.isna(value):
            out.append(None)
        else:
            out.append(int(value))
    return tuple(out)


def education_agreement(
    attributes: pd.DataFrame, dimension: g3.Dimension
) -> dict[str, Any]:
    """Hold G3's MINT8 education band equal to G1's MINT8 label.

    Both encode SSA's definition (Graduate more than 16 years, Bachelor
    16, Associate 14-15, High school 12-13, Less than high school under
    12); this is the differential check between the two implementations.
    Refuses a person they place differently.
    """

    agree = 0
    for years, label in zip(
        education_years(attributes),
        attributes["education_mint8"],
        strict=True,
    ):
        label = _text(label)
        if years is None:
            if label is not None:
                raise ValueError("G1 labels an education it has no years for")
            continue
        hits = [c.label for c in dimension.categories if c.contains(years)]
        g3_label = hits[0] if hits else None
        if g3_label != label:
            raise ValueError(
                "G1's and G3's MINT8 education bands place a person "
                "differently"
            )
        agree += 1
    return {
        "n_with_years": agree,
        "g3_band_equals_g1_label": True,
        "rule": (
            "for every person with resolved years, the G3 band containing "
            "the years prints G1's education_mint8 label"
        ),
    }


MARITAL_STATUS_CODES: tuple[str, ...] = (
    "married",
    "divorced",
    "widowed",
    "never_married",
)


def marital_codes(
    statuses: Sequence[Any], *, unclassified: Sequence[str]
) -> SchemeCodes:
    """Marital statuses as G3 codes; ``unclassified`` statuses declared.

    A status that is neither one of MINT8's four nor declared is refused
    by G3 (``assign_groups``), never dropped.
    """

    declared = tuple(sorted(set(unclassified)))
    held = set(declared) & set(MARITAL_STATUS_CODES)
    if held:
        raise ValueError(f"MINT8 statuses {sorted(held)} cannot be declared")
    codes = tuple(_text(status) for status in statuses)
    present = tuple(code for code in declared if code in set(codes))
    return SchemeCodes(
        codes=codes,
        unclassified_codes=present,
        rule=(
            "the status in the analysis year, MINT8's four statuses as "
            f"themselves; {list(declared)} unclassified"
        ),
    )


def age_in_year(birth_years: Iterable[Any], year: int) -> tuple[int, ...]:
    """Age in ``year`` as ``year - birth_year`` (whole years)."""

    out = []
    for birth in birth_years:
        if isinstance(birth, bool | np.bool_):
            raise ValueError("birth years must be integers")
        out.append(int(year) - int(birth))
    return tuple(out)


_REPORT_COLUMNS = ["person_id", "wave", "role", *gap.REPORT_CODE_COLUMNS]


_EDUCATION_COLUMNS = [
    "person_id",
    "wave",
    "education_code",
    "role",
    "family_education_code",
]


def _frame(rows: list[dict[str, Any]], columns: list[str]) -> pd.DataFrame:
    frame = pd.DataFrame(rows, columns=columns)
    for column in frame:
        frame[column] = frame[column].astype(
            "string" if column == "role" else "Int64"
        )
    return frame


def invented_group_attribute_inputs(
    persons: pd.DataFrame, *, wave: int, seed: int = 0
) -> g1.GroupAttributeInputs:
    """INVENTED inputs for G1's builder (INVENTED DATA - NOT A COMPARISON).

    ``persons`` has ``person_id`` and ``role`` (``"head"``, ``"spouse"`` or
    missing for another family-unit member).  Each head and spouse gets one
    report in ``wave`` with a Spanish-descent code (0 not Hispanic, 1
    Hispanic, 9 DK/NA), one or two race mentions, a completed-education
    code and a birthplace pair (a state with year-came 0, a territory, a
    foreign country with a year of arrival, or DK/NA); every person gets an
    individual education row, with code 99 (NA) for a few.  Codes are
    drawn inside the wave's documented domains, which G1's builder checks
    against the committed codebook values.  No PSID value enters.
    """

    items = gap.FAMILY_ITEMS[int(wave)]
    if int(wave) not in gap.BIRTHPLACE_WAVES or not items.asks_hispanic_origin:
        raise ValueError(
            "invented side-frame inputs are drawn for a wave that asks "
            "Spanish descent and birthplace (2013-2023)"
        )
    rng = np.random.default_rng(seed)
    reports: list[dict[str, Any]] = []
    education: list[dict[str, Any]] = []
    for pid, role in zip(persons["person_id"], persons["role"], strict=True):
        pid = int(pid)
        role = _text(role)
        years = int(rng.choice(np.arange(6, 18)))
        code = 99 if rng.random() < 0.03 else years
        family_code = None
        if role is not None:
            if role not in gap.ROLES:
                raise ValueError(f"undocumented role {role!r}")
            family_code = code
            row: dict[str, Any] = dict.fromkeys(_REPORT_COLUMNS, pd.NA)
            row.update(person_id=pid, wave=int(wave), role=role)
            row["hispanic_code"] = int(
                rng.choice([0, 1, 9], p=[0.8, 0.14, 0.06])
            )
            first = int(
                rng.choice([1, 2, 4, 7, 9], p=[0.6, 0.2, 0.08, 0.1, 0.02])
            )
            second = int(rng.choice([1, 2, 3])) if rng.random() < 0.06 else 0
            mentions = [first, second if first != 9 else 0, 0, 0]
            for index in range(len(items.race[role])):
                row[f"race_code_{index + 1}"] = mentions[index]
            row["family_education_code"] = family_code
            place = rng.random()
            if place < 0.84:
                state, came = int(rng.integers(1, 57)), 0
            elif place < 0.87:
                state, came = 0, 0
            elif place < 0.98:
                state, came = 0, int(rng.integers(1950, 2016))
            else:
                state, came = 99, 0
            row["birth_state_code"] = state
            row["year_came_code"] = came
            reports.append(row)
        education.append(
            {
                "person_id": pid,
                "wave": int(wave),
                "education_code": code,
                "role": pd.NA if role is None else role,
                "family_education_code": (
                    pd.NA if family_code is None else family_code
                ),
            }
        )
    universe = pd.Series(
        np.sort(persons["person_id"].astype("int64").unique()),
        name="person_id",
        dtype="int64",
    )
    return g1.GroupAttributeInputs(
        reports=_frame(reports, _REPORT_COLUMNS),
        education=_frame(education, _EDUCATION_COLUMNS),
        universe=universe,
        provenance={
            "kind": "INVENTED",
            "label": INVENTED_DATA_HEADER,
            "generator": (
                "populace_dynamics.group_breakdowns.common."
                "invented_group_attribute_inputs"
            ),
            "wave": int(wave),
            "seed": int(seed),
        },
    )


# Historical adapter spellings share the same labels and refusal class.
POSTHOC_LABELS = POST_HOC_LABELS
INVENTED_HEADER = INVENTED_DATA_HEADER


class GroupBreakdownRefusal(ValueError):
    """A reproduction or registration invariant failed before grouping."""


ReproductionMismatch = GroupBreakdownRefusal
ReproductionMismatchError = GroupBreakdownRefusal


def json_normalized(value: Any) -> Any:
    """Normalize finite JSON arrays, refusing keys JSON would coerce.

    The stricter uniform-cut rule prevents 1 and "1" keys from collapsing
    during JSON encoding. Tuples and lists keep their common JSON-array
    meaning, as all registered runners serialize them.
    """

    def check_keys(node: Any) -> None:
        if isinstance(node, Mapping):
            if any(not isinstance(key, str) for key in node):
                raise GroupBreakdownRefusal("non-JSON mapping key")
            for child in node.values():
                check_keys(child)
        elif isinstance(node, (list, tuple)):
            for child in node:
                check_keys(child)

    check_keys(value)
    return json.loads(json.dumps(value, allow_nan=False))


def compare_exact(
    name: str, committed: Any, recomputed: Any, *, path: str = "$"
) -> ReproductionCheck:
    """Compare every normalized JSON leaf with no numeric tolerance."""
    found, n = leaf_differences(
        json_normalized(committed), json_normalized(recomputed), path
    )
    return ReproductionCheck(name, n, tuple(found))


def assert_exact_cells(
    committed: Any, recomputed: Any, *, path: str = "cells"
) -> ReproductionCheck:
    """Uniform-cut compatibility gate through the shared exact comparator."""
    try:
        checked = compare_exact(path, committed, recomputed, path=path)
    except (TypeError, ValueError) as error:
        raise GroupBreakdownRefusal(
            f"committed cell is non-JSON or nonfinite at {path}; no group cells allowed"
        ) from error
    require_identical([checked], stage=f"committed cell {path}")
    return checked


def _first_difference(actual: Any, expected: Any, path: str) -> str | None:
    """Projection compatibility path through the shared exact comparator."""
    checked = compare_exact(path, expected, actual, path=path)
    return checked.differences[0] if checked.differences else None


_ARTIFACT_NAME = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9_.-]*_groups_posthoc_v1\.json"
)


_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class RegisteredRun:
    """The checked checkout and new output pair bound by a registration."""

    registration_pointer: str
    registered_commit: str
    git_head: str
    git_clean: bool
    output_path: Path
    sidecar_path: Path


def assert_sha256(path: Path, expected_sha256: str) -> str:
    """Refuse to admit pinned non-microdata bytes with a different SHA-256."""

    if not isinstance(expected_sha256, str) or not re.fullmatch(
        r"[0-9a-f]{64}", expected_sha256
    ):
        raise GroupBreakdownRefusal("expected SHA-256 must be full 64-hex")
    actual = file_sha256(path)
    if actual != expected_sha256:
        raise GroupBreakdownRefusal(f"SHA-256 mismatch for {path}")
    return actual


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _exists(path: Path) -> bool:
    """Include dangling symlinks among paths that must not be replaced."""

    return path.exists() or path.is_symlink()


def preflight(
    *,
    registration_pointer: str,
    registered_commit: str,
    output: Path,
    root: Path,
    git: Callable[..., str] | None = None,
) -> RegisteredRun:
    """Check registration, clean HEAD, and new paired paths before reads.

    This verifies the pointer's form locally; it does not retrieve the
    comment or imply that a new real-data run has been authorized.  The
    orchestrator must obtain the issue #42 registration before execution.
    ``git`` is injectable solely to exercise guards on invented data.
    """

    if not isinstance(
        registration_pointer, str
    ) or not REGISTRATION_POINTER.fullmatch(registration_pointer):
        raise GroupBreakdownRefusal(
            "registration pointer must be an issue #42 comment URL"
        )
    if not isinstance(registered_commit, str) or not re.fullmatch(
        r"[0-9a-f]{40}", registered_commit
    ):
        raise GroupBreakdownRefusal(
            "--registered-commit must be a full 40-hex SHA"
        )
    root = Path(root).resolve()
    if git is None:

        def git(*args: str) -> str:
            return _git(root, *args)

    head = git("rev-parse", "HEAD")
    if head != registered_commit:
        raise GroupBreakdownRefusal(
            "HEAD is not the registered commit; no run allowed"
        )
    if git("status", "--porcelain", "--untracked-files=all") != "":
        raise GroupBreakdownRefusal(
            "working tree must be clean for a registered run"
        )
    runs = root / "runs"
    if runs.is_symlink():
        raise GroupBreakdownRefusal("runs directory must not be a symlink")
    candidate = Path(output)
    if not candidate.is_absolute():
        candidate = root / candidate
    if candidate.is_symlink():
        raise GroupBreakdownRefusal("output must not be a symlink")
    candidate = candidate.resolve()
    if candidate.parent != runs.resolve() or not _ARTIFACT_NAME.fullmatch(
        candidate.name
    ):
        raise GroupBreakdownRefusal(
            "output must be runs/<name>_groups_posthoc_v1.json"
        )
    sidecar = candidate.with_suffix(".env.json")
    if _exists(candidate) or _exists(sidecar):
        raise GroupBreakdownRefusal(
            "artifact or environment sidecar already exists: one-shot"
        )
    return RegisteredRun(
        registration_pointer,
        registered_commit,
        head,
        True,
        candidate,
        sidecar,
    )


def environment(
    *,
    ssa_parameters_revision: str,
    root: Path | None = None,
) -> dict[str, Any]:
    """Reuse Track A's installed-distribution resolver unchanged.

    Loading the entry-point module through ``importlib`` composes its
    resolver exactly as the frozen FRA-68 and Track M runners do.  The
    registered ``main`` function is never invoked.
    """

    script = (Path(root) if root is not None else _ROOT) / "scripts"
    script = script / "run_track_a_registered.py"
    spec = importlib.util.spec_from_file_location(
        "_group_breakdowns_track_a_registered", script
    )
    if spec is None or spec.loader is None:
        raise GroupBreakdownRefusal("cannot load Track A environment resolver")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module._environment(ssa_parameters_revision=ssa_parameters_revision)


def write_artifact_pair(
    *,
    output: Path,
    artifact: Mapping[str, Any],
    environment: Mapping[str, Any],
) -> tuple[Path, Path]:
    """Exclusively create artifact and SHA-bound sidecar, or roll back.

    Serialization happens before either file is opened.  On any failure,
    rollback removes only files this invocation created, and only while
    their inode still matches.  An existing artifact or sidecar is never
    changed.  A host interruption can leave an incomplete pair, which
    preflight refuses; publication is not a transactional filesystem.
    """

    output = Path(output)
    sidecar = output.with_suffix(".env.json")
    artifact_text = json.dumps(artifact, indent=2, allow_nan=False) + "\n"
    artifact_sha256 = hashlib.sha256(artifact_text.encode("utf-8")).hexdigest()
    sidecar_text = (
        json.dumps(
            {
                "artifact": output.name,
                "artifact_sha256": artifact_sha256,
                "environment": dict(environment),
            },
            indent=2,
            allow_nan=False,
        )
        + "\n"
    )
    created: list[tuple[Path, os.stat_result]] = []
    try:
        for path, content in (
            (output, artifact_text),
            (sidecar, sidecar_text),
        ):
            with path.open("x", encoding="utf-8") as handle:
                created.append((path, os.fstat(handle.fileno())))
                handle.write(content)
    except BaseException:
        for path, stat in reversed(created):
            try:
                current = path.lstat()
                if (current.st_dev, current.st_ino) == (
                    stat.st_dev,
                    stat.st_ino,
                ):
                    path.unlink()
            except FileNotFoundError:
                pass
        raise
    return output, sidecar


INCOME_REASON = (
    "The closed projection has no household income or official poverty "
    "measure; poverty status and household income quintiles are not computed."
)


@dataclass(frozen=True)
class ProjectionReplay:
    """Frozen result plus in-memory rows and final states, before grouping."""

    exercise: str
    result: Mapping[str, Any]
    benefit_rows: Mapping[str, pd.DataFrame]
    states: Mapping[int, pd.DataFrame]
    retention_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "retention_sha256", _retention_digest(self))


@dataclass(frozen=True)
class LifetimeOptions:
    """Sourced G2 inputs; marriage history is resolved only after the gate.

    The loader returns (episodes, history person ids) for an anchor wave.
    Absent history is explicitly unavailable, rather than never-married.
    """

    rates: Any = None
    interest: Any = None
    marriage_episode_loader: (
        Callable[[int], tuple[pd.DataFrame, tuple[int, ...]]] | None
    ) = None


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


def _retention_digest(replay: ProjectionReplay) -> str:
    """Seal retained content, including nested component dicts and keys."""
    digest = hashlib.sha256(replay.exercise.encode())
    for name, frames in (
        ("benefits", replay.benefit_rows),
        ("states", replay.states),
    ):
        for key in sorted(frames, key=str):
            frame = frames[key]
            digest.update(_canonical((name, key, list(frame.columns))))
            digest.update(_canonical([str(dtype) for dtype in frame.dtypes]))
            digest.update(
                frame.to_csv(index=False, lineterminator="\n").encode()
            )
    return digest.hexdigest()


def verify_reproduction(
    replay: ProjectionReplay, parent: Mapping[str, Any]
) -> dict[str, Any]:
    """Require exact JSON values for every recomputed frozen result field.

    Only the parent's entry-script wrapper (run times, environment, etc.)
    lies outside the frozen runner's returned result. No floating tolerance
    is used; differing summation requires a new reviewed convention.
    Failure identifies a path, without printing any outcome value.
    """

    if not replay.result.get("rows") or not replay.result.get("draws"):
        raise ReproductionMismatch("replay lacks frozen rows or draws")
    absent = set(replay.result) - set(parent)
    if absent:
        raise ReproductionMismatch(f"parent lacks fields {sorted(absent)}")
    expected = {key: parent[key] for key in replay.result}
    difference = _first_difference(replay.result, expected, "result")
    if difference:
        raise ReproductionMismatch(
            f"frozen reproduction mismatch at {difference}"
        )
    row_ids = set(replay.result["rows"])
    if set(replay.benefit_rows) != row_ids:
        raise ReproductionMismatch(
            "retained rows differ from frozen row manifest"
        )
    if _retention_digest(replay) != replay.retention_sha256:
        raise ReproductionMismatch(
            "retained projection frames changed after replay"
        )
    return {
        "identical": True,
        "comparison": "exact canonical JSON values; no floating tolerance",
        "absolute_tolerance": 0.0,
        "relative_tolerance": 0.0,
        "verified_result_fields": sorted(replay.result),
        "verified_rows": sorted(row_ids),
        "verified_payload_sha256": hashlib.sha256(
            _canonical(expected)
        ).hexdigest(),
        "ordering": "all frozen fields verified before G1/G2/G3 grouping",
        "retention_sha256": replay.retention_sha256,
    }


def benefit_type(components: Mapping[str, Mapping[str, float]]) -> str | None:
    """Map baseline components to G3's four MINT benefit types.

    A positive aged/disabled widow component takes the widow row, including
    own-worker dual entitlement; otherwise a positive spouse excess takes
    the spousal row. Worker-only means exactly one worker kind. A baseline
    nonrecipient is unclassified. Concurrent widow/spouse or two worker
    kinds are refused, since the frozen calculator should not emit them.
    """

    allowed = {
        "retired_worker",
        "disabled_worker",
        "spouse",
        "aged_widow",
        "disabled_widow",
    }
    if set(components) - allowed:
        raise ValueError("unknown benefit component")
    if any(
        isinstance(amounts["base"], bool)
        or not math.isfinite(amounts["base"])
        or amounts["base"] < 0
        for amounts in components.values()
    ):
        raise ValueError(
            "baseline components must be finite nonnegative amounts"
        )
    active = {
        name for name, amounts in components.items() if amounts["base"] > 0
    }
    widow = bool(active & {"aged_widow", "disabled_widow"})
    if widow and "spouse" in active:
        raise ValueError(
            "concurrent widow and spouse benefits have no mapping"
        )
    if {"retired_worker", "disabled_worker"} <= active:
        raise ValueError("concurrent worker benefit kinds have no mapping")
    if widow:
        return "widower"
    if "spouse" in active:
        return "spousal"
    if "retired_worker" in active:
        return "retired_worker_only"
    if "disabled_worker" in active:
        return "disabled_worker_only"
    return None


def _label_codes(series: pd.Series, dimension: g3.Dimension) -> pd.Series:
    codes = {category.label: category.key for category in dimension.categories}
    unknown = set(series.dropna()) - set(codes)
    if unknown:
        raise ValueError(f"G1 labels outside G3 {dimension.key} scheme")
    return series.map(codes)


def _fixed_lifetime_dimensions() -> tuple[g3.Dimension, ...]:
    return tuple(
        replace(
            dimension,
            kind=g3.CATEGORICAL,
            categories=tuple(
                replace(category, codes=(category.key,), rank=None)
                for category in dimension.categories
            ),
            notes=(*dimension.notes, "G3 categories fixed on opening cohort"),
        )
        for dimension in g3.LIFETIME_DIMENSIONS
    )


def _lifetime_side(
    cohort: Any, params: Any, options: LifetimeOptions
) -> tuple[pd.DataFrame, dict[str, Any]]:
    persons = cohort.persons[["person_id", "birth_year", "weight"]].copy()
    careers = pd.DataFrame(
        [
            (pid, year, earnings)
            for pid, history in cohort.careers.items()
            for year, earnings in history.items()
            if year <= cohort.start_year
        ],
        columns=["person_id", "year", "earnings"],
    )
    rates = options.rates
    if rates is None:
        rates = g2.load_oasdi_tax_rates(
            basis=g2.TaxRateBasis.EMPLOYEE_EMPLOYER_PAID
        )
    interest = options.interest
    if interest is None:
        interest = g2.load_trust_fund_interest_rates()
    aime = g2.initial_aime_at_62(
        careers,
        persons,
        params,
        analysis_year=cohort.start_year,
        convention=g2.AIME_CONVENTIONS["mint8_initial_aime"],
    )
    own = g2.lifetime_payroll_tax_pv_at_62(
        careers,
        persons,
        params,
        shared=False,
        rates=rates,
        interest=interest,
        missing_rate=g2.MissingRatePolicy.NOT_COMPUTED,
    )
    measures = {
        "initial_aime_quintile": (aime, "aime"),
        "lifetime_payroll_tax_quintile": (own, "pv_at_62"),
    }
    provenance: dict[str, Any] = {}
    absent_history_ids: set[int] = set()
    shared_key = "lifetime_payroll_tax_quintile_shared"
    if options.marriage_episode_loader is None:
        persons[shared_key] = float("nan")
        provenance[shared_key] = {
            "status": "not computed",
            "reason": "marriage history not supplied",
        }
    else:
        episodes, history_ids = options.marriage_episode_loader(
            cohort.anchor_wave
        )
        shared = g2.lifetime_payroll_tax_pv_at_62(
            careers,
            persons,
            params,
            shared=True,
            rates=rates,
            interest=interest,
            marriage_episodes=episodes,
            marriage_history_person_ids=history_ids,
            missing_spouse=g2.MissingSpousePolicy.NOT_COMPUTED,
            missing_rate=g2.MissingRatePolicy.NOT_COMPUTED,
        )
        # Do not mutate G2's measure frame/provenance. Its explicit history
        # coverage flag governs which values this adapter may classify.
        absent_history_ids = set(persons["person_id"]) - set(history_ids)
        measures[shared_key] = (shared, "pv_at_62")
    for key, (measure, column) in measures.items():
        side = measure.frame[["person_id", column]].rename(
            columns={column: key}
        )
        if key == shared_key:
            side.loc[side["person_id"].isin(absent_history_ids), key] = float(
                "nan"
            )
        persons = persons.merge(side, on="person_id", validate="one_to_one")
        provenance[key] = {
            "measure": measure.measure,
            "provenance": measure.provenance,
            "status_counts": measure.frame["status"].value_counts().to_dict(),
            "unavailable_reasons": measure.frame["reason"]
            .dropna()
            .value_counts()
            .to_dict(),
        }
        if key == shared_key:
            provenance[key]["adapter_unavailable_marriage_history"] = len(
                absent_history_ids
            )
    persons["birth_cohort"] = g2.ten_year_birth_cohort(persons["birth_year"])
    scheme = g3.derive_scheme(
        g3.MINT8_COHORT_SCHEME,
        scheme_id="projection_opening_lifetime",
        title="Opening-cohort lifetime categories",
        drop=("sex", "race_ethnicity", "country_of_birth", "education"),
    )
    assignment = g3.assign_groups(
        persons,
        scheme,
        {d.key: d.key for d in g3.LIFETIME_DIMENSIONS},
        key_columns=("person_id",),
        quintile_partition=("birth_cohort",),
    )
    for dimension in g3.LIFETIME_DIMENSIONS:
        codes = assignment.long.loc[
            assignment.long["dimension"] == dimension.key, "category"
        ].reset_index(drop=True)
        persons[dimension.key] = codes.where(codes != g3.UNCLASSIFIED, None)
    provenance["quintiles"] = assignment.as_dict()
    provenance["history_window"] = (
        f"careers through opening year {cohort.start_year}"
    )
    return (
        persons.drop(columns=["birth_year", "weight", "birth_cohort"]),
        provenance,
    )


def run_group_breakdown(
    replay: ProjectionReplay,
    parent: Mapping[str, Any],
    *,
    inputs: Any,
    config: Any,
    attribute_loader: Callable[..., g1.GroupAttributes] | None = None,
    lifetime_options: LifetimeOptions | None = None,
    parent_sha256: str | None = None,
    registration_pointer: str | None = None,
) -> dict[str, Any]:
    """Verify the entire replay, then join side frames and call G3.

    Returns a JSON-safe report with no person rows. The registered entry
    point handles exclusive writing; this function performs no writes.
    """

    identity = verify_reproduction(replay, parent)
    if _first_difference(
        config.as_dict(), replay.result.get("config"), "config"
    ):
        raise ReproductionMismatch(
            "group configuration differs from verified replay"
        )
    cohorts = {
        c.anchor_wave: c for c in (inputs.cohort, *inputs.additional_cohorts)
    }
    if any(c.data_provenance == g3.REGISTERED_REAL for c in cohorts.values()):
        if not isinstance(
            registration_pointer, str
        ) or not g3.REGISTRATION_POINTER.fullmatch(registration_pointer):
            raise ValueError(
                "real-data grouping requires a new issue #42 pointer"
            )
        if registration_pointer == parent.get("registration_pointer"):
            raise ValueError(
                "parent registration cannot authorize post hoc grouping"
            )
    loader = (
        g1.load_group_attributes
        if attribute_loader is None
        else attribute_loader
    )
    options = (
        LifetimeOptions() if lifetime_options is None else lifetime_options
    )
    scheme = g3.derive_scheme(
        g3.MINT8_SCHEME,
        scheme_id="projection_mint8_with_opening_lifetime",
        title="MINT8 annual rows with opening-cohort lifetime dimensions",
        append=_fixed_lifetime_dimensions(),
        notes=(
            "Lifetime quintiles use G3's weighted percentile rule within "
            "ten-year birth cohorts of the entire opening cohort, fixed "
            "across draws, scenarios and population variants.",
            INCOME_REASON,
        ),
    )
    attributes: dict[int, pd.DataFrame] = {}
    attribute_unclassified: dict[int, dict[str, tuple[str, ...]]] = {}
    attribute_provenance = {}
    lifetime_provenance = {}
    for wave, cohort in cohorts.items():
        ids = tuple(int(pid) for pid in cohort.persons["person_id"])
        loaded = loader(ids, anchor_waves=(wave,))
        if loaded.frame["person_id"].duplicated().any() or set(
            loaded.frame["person_id"]
        ) != set(ids):
            raise ValueError(
                "G1 side frame must retain each opening person exactly once"
            )
        recorded = loaded.provenance.get("content_sha256")
        if recorded is not None and recorded != g1.content_sha256(
            loaded.frame
        ):
            raise ValueError("G1 side frame changed after sealing")
        side = loaded.frame[
            [
                "person_id",
                "race_ethnicity_mint8",
                "education_years",
                "country_of_birth_mint8",
            ]
        ].copy()
        attribute_unclassified[wave] = {}
        for name, dimension in (
            ("race_ethnicity", g3.RACE_ETHNICITY_DIMENSION),
            ("country_of_birth", g3.COUNTRY_OF_BIRTH_DIMENSION),
        ):
            codes = side_frame_codes(loaded.frame, dimension)
            side.pop(f"{name}_mint8")
            side[name] = codes.codes
            attribute_unclassified[wave][name] = codes.unclassified_codes
        education_agreement(loaded.frame, g3.EDUCATION_DIMENSION)
        lifetime, provenance = _lifetime_side(cohort, inputs.params, options)
        attributes[wave] = side.merge(
            lifetime, on="person_id", validate="one_to_one"
        )
        attribute_provenance[str(wave)] = loaded.provenance
        lifetime_provenance[str(wave)] = provenance
    if replay.exercise == "cola":
        row_config = {key: REGISTERED_ROWS[key] for key in config.rows}
    elif replay.exercise == "fra68":
        row_config = {key: config.row(key) for key in config.rows}
    else:
        raise ValueError("unknown projection exercise")
    output_rows = {}
    for row_id, benefits in replay.benefit_rows.items():
        row = row_config[row_id]
        wave = row.anchor_wave
        state = replay.states[wave][
            ["draw", "person_id", "sex", "marital_status"]
        ]
        frame = benefits.merge(
            state,
            on=["draw", "person_id"],
            how="left",
            validate="one_to_one",
            indicator=True,
        )
        if not frame["_merge"].eq("both").all():
            raise ValueError("beneficiary absent from final projected state")
        frame = frame.drop(columns="_merge").merge(
            attributes[wave],
            on="person_id",
            how="left",
            validate="many_to_one",
            indicator=True,
        )
        if not frame["_merge"].eq("both").all():
            raise ValueError("beneficiary absent from opening attribute frame")
        frame = frame.drop(columns="_merge")
        frame["age"] = config.reference_year - frame["birth_year"]
        frame["benefit_type"] = frame["benefit_components"].map(benefit_type)
        frame["poverty_status"] = None
        frame["household_income_quintile"] = float("nan")
        columns = {
            d.key: d.key for d in scheme.dimensions if d.kind != g3.TOTAL
        }
        columns["education"] = "education_years"
        cohort = cohorts[wave]
        if replay.exercise == "cola":
            tab_config = ColaAgeProfileConfig(
                reference_year=config.reference_year,
                components=row.components,
                benefit_period=row.tabulation_benefit_period,
                headline_statistic=row.headline_statistic,
                draw_indices=config.draw_indices,
                floor_seeds=config.floor_seeds,
            )
        else:
            from populace_dynamics.fra68_track.runner import _tabulation_config

            tab_config = _tabulation_config(row, config)
        frozen_row = replay.result["rows"][row_id]
        frozen_tabulation = frozen_row.get("tabulation") or {}
        labels = (
            tuple(
                frozen_row.get(
                    "labels", frozen_tabulation.get("labels", cohort.labels)
                )
            )
            + POST_HOC_LABELS
        )
        variants = {
            "test_population": frame,
            "mint_population": frame.loc[
                (frame["age"] >= 60)
                & frame["beneficiary_base"]
                & (frame["benefit_base"] > 0)
            ].copy(),
        }
        output_variants = {}
        for name, selected in variants.items():
            if set(selected["draw"]) != set(tab_config.draw_indices):
                output_variants[name] = {
                    "status": "not computed",
                    "reason": "population absent in at least one registered draw",
                    "labels": list(labels),
                }
                continue
            assignment = g3.assign_groups(
                selected,
                scheme,
                columns,
                key_columns=("draw", "person_id"),
                unclassified_codes={
                    **attribute_unclassified[wave],
                    "marital_status": (
                        "unknown",
                        "no_marriage_history",
                        "separated",
                    ),
                },
            )
            result = g3.tabulate_projection_breakdown(
                selected,
                assignment,
                config=tab_config,
                data_provenance=cohort.data_provenance,
                registration_pointer=registration_pointer,
                labels=labels,
                post_hoc_labels=POST_HOC_LABELS,
                statistic_id=frozen_tabulation.get(
                    "statistic_id", g3.PROJECTION_STATISTIC_ID
                ),
                upstream={
                    "parent_sha256": parent_sha256,
                    "row": row_id,
                    "verified_payload_sha256": identity[
                        "verified_payload_sha256"
                    ],
                    "retention_sha256": replay.retention_sha256,
                    "reproduction_identical": True,
                    "absolute_tolerance": 0.0,
                    "relative_tolerance": 0.0,
                },
            ).as_dict()
            result["population_variant"] = name
            result["not_computed"] = {
                "poverty_status": INCOME_REASON,
                "household_income_quintile": INCOME_REASON,
                "household_income_statistics": INCOME_REASON,
                "official_poverty_statistics": INCOME_REASON,
            }
            output_variants[name] = result
        output_rows[row_id] = {
            "anchor_wave": wave,
            "row": frozen_row["row"],
            "labels": list(labels),
            "variants": output_variants,
        }
    invented = all(c.data_provenance == g3.INVENTED for c in cohorts.values())
    return {
        "header": (
            INVENTED_HEADER
            if invented
            else "Registered projection group breakdown"
        ),
        "exercise": replay.exercise,
        "labels": ([INVENTED_HEADER] if invented else [])
        + list(inputs.cohort.labels)
        + list(POST_HOC_LABELS),
        "report_only": True,
        "parent_sha256": parent_sha256,
        "reproduction": identity,
        "attribute_provenance": attribute_provenance,
        "lifetime_provenance": lifetime_provenance,
        "conventions": {
            "benefit_type": "baseline components; widow then spouse (dual entitlement included), otherwise worker only",
            "marital_status": "2030 projected state; opening divorced/never married carried forward; inherited opening convention counts separated as married; literal separated and unknown codes unclassified",
            "mint_population": "current-law beneficiaries aged 60 or older in 2030",
            "test_population": "alive in 2030 with a positive benefit in either scenario; original scenario membership retained",
            "artifact_choice": "one artifact per exercise, preserving separate parent identities and one-shot registrations",
            "lifetime": "opening-cohort careers only; no projected earnings or unsourced interest rates",
        },
        "rows": output_rows,
    }
