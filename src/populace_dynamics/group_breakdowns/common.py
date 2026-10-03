"""Shared pieces of the post hoc group-breakdown adapters (NASI follow-up).

Every adapter in :mod:`populace_dynamics.group_breakdowns` follows one
order, and this module holds what the order needs that is not specific to
a test:

1. **Exact reproduction before any group work.**  The adapter re-executes
   its test's registered computation and compares what it recomputes with
   the committed artifact (:func:`compare_exact`): every JSON leaf must be
   equal in type and value, and every float equal bit for bit
   (``float.hex``), after both sides pass through the same JSON encoding
   the registered runners use (``json.dumps(..., allow_nan=False)``).  No
   tolerance is applied (:data:`EXACT_COMPARISON`).  A difference raises
   :class:`ReproductionMismatchError` (:func:`require_identical`) before
   any group attribute is read; the error and the check records name the
   differing paths only, never a value, so a refusal on real data prints
   no outcome.
2. **Labels.**  Every output carries the test's own labels plus
   :data:`POST_HOC_LABELS` ("registered, one-shot, post hoc, not blind",
   the d479 label of Track A v2, ``track_a_v2/manifest.py``; and
   "report-only", the paper's term for cells published with no tolerance).
3. **The cohort side frame on the MINT8 scheme.**  The person attributes
   of :mod:`populace_dynamics.cohorts.group_attributes` (G1) carry SSA's
   verbatim MINT8 row labels; :func:`side_frame_codes` maps each to the
   category of :mod:`populace_dynamics.estimates.group_breakdown` (G3)
   whose label equals it, and names every row G1 does not place
   (``attribute_unknown:<G1 status>`` or G1's ``unresolved:<reason>``) as
   a declared unclassified code, so G3 counts it by reason and enters it
   in Total only.  Education enters G3 as G1's integer years, and
   :func:`education_agreement` holds G3's band equal to G1's own MINT8
   label for every person.
4. **INVENTED inputs.**  :func:`invented_group_attribute_inputs` draws
   head/spouse reports and education rows in the shapes and code domains
   G1's builder validates, so a dry run passes INVENTED data through G1's
   real builder.  Its provenance says INVENTED.

This module reads no PSID file and computes no outcome.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from populace_dynamics.cohorts import group_attributes as g1
from populace_dynamics.data import group_attributes_psid as gap
from populace_dynamics.estimates import group_breakdown as g3

__all__ = [
    "CommittedArtifact",
    "EXACT_COMPARISON",
    "INVENTED_DATA_HEADER",
    "MARITAL_STATUS_CODES",
    "POST_HOC_LABEL",
    "POST_HOC_LABELS",
    "REGISTRATION_POINTER",
    "REPORT_ONLY_LABEL",
    "ReproductionCheck",
    "ReproductionMismatchError",
    "SchemeCodes",
    "age_in_year",
    "compare_exact",
    "education_agreement",
    "education_years",
    "file_sha256",
    "invented_group_attribute_inputs",
    "json_normalized",
    "leaf_differences",
    "load_committed_artifact",
    "marital_codes",
    "require_identical",
    "side_frame_codes",
    "write_new",
]

#: Max's d479 label for a post hoc rerun (``track_a_v2/manifest.py``).
POST_HOC_LABEL = "registered, one-shot, post hoc, not blind"
#: The paper's term for cells published with no tolerance (paper.qmd).
REPORT_ONLY_LABEL = "report-only"
POST_HOC_LABELS: tuple[str, ...] = (POST_HOC_LABEL, REPORT_ONLY_LABEL)
#: The header of every invented-data output: Track M's ``DRY_RUN_HEADER``
#: and Track A v2's ``INVENTED_HEADER`` (a test holds the three equal).
#: G3 also puts its own invented label first among its labels.
INVENTED_DATA_HEADER = "INVENTED DATA - NOT A COMPARISON"
#: An issue #42 comment, the registration issue (G3's pattern).
REGISTRATION_POINTER = g3.REGISTRATION_POINTER

#: How a recomputed result is compared with the committed artifact.
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


class ReproductionMismatchError(ValueError):
    """A recomputed cell differs from the committed artifact: refuse."""


# =========================================================================
# Exact comparison
# =========================================================================
def json_normalized(value: Any) -> Any:
    """``value`` through the registered runners' JSON encoding."""

    return json.loads(json.dumps(value, allow_nan=False))


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


def compare_exact(
    name: str, committed: Any, recomputed: Any
) -> ReproductionCheck:
    """``recomputed`` against ``committed`` (:data:`EXACT_COMPARISON`)."""

    found, n = leaf_differences(
        json_normalized(committed), json_normalized(recomputed)
    )
    return ReproductionCheck(name, n, tuple(found))


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


# =========================================================================
# Files
# =========================================================================
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
    digest = file_sha256(path)
    if digest != expected_sha256:
        raise ValueError(
            f"{path.name} has SHA-256 {digest}, not the committed "
            f"{expected_sha256}"
        )
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


# =========================================================================
# The cohort side frame (G1) on G3's MINT8 codes
# =========================================================================
#: Per side-frame dimension: G1's MINT8 label column, its status column
#: and the attribute's own status column.
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


#: MINT8's four marital statuses, as G3's codes.
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


# =========================================================================
# INVENTED side-frame inputs
# =========================================================================
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
