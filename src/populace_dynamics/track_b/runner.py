"""Registered B1 earnings replay; importing this module reads no data.

The committed M6 artifact contains aggregate cells, not historical person
rows. Reconstructing the original loop is a differential witness only. An
absent authenticated historical reference must never become REPRODUCED.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import traceback
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from populace_dynamics.engine.support import PresenceBasis
from populace_dynamics.harness import m6_projection
from populace_dynamics.harness.m6_cells import earnings_cells
from populace_dynamics.harness.m6_projection import (
    prepare_gated_realized_support,
    project_earnings_on_realized_support,
)
from populace_dynamics.harness.m6_scoring import (
    EARNINGS_CELL_NAMES,
    restrict_earnings_domain_support,
)
from populace_dynamics.track_b.equality import compare_replay
from populace_dynamics.track_b.replay import (
    earnings_rng_signature,
    replay_earnings_on_realized_support,
)

SCHEMA_VERSION = "track_b_b1.v1"
DEFAULT_OUTPUT = Path("scratch/track_b/b1_v1")
BASELINE_PATH = Path("runs/gate_m6_candidate3_v1.json")
BASELINE_SHA256 = (
    "caf254925f44b27c1bd1131336055e27fbc311daec00b0050b2f9293a74e82cf"
)
BASELINE_COMMIT = "f10cca5457b16d12b9284d00628e7331871f23e7"
ENVIRONMENT_SHA256 = (
    "6a2559d053ef9da9abbcfc710f9d45b91b749c918b4e48a0fbee3c54003cb38f"
)
REGISTERED_SEEDS = tuple(range(5))
REGISTERED_DRAWS = tuple(range(20))
# SHA-256 of the only historical person-level reference B1 may read. Custody
# is bound by committing it here: source_guard hashes this file at the
# registered commit, and no command-line value can replace it. None refuses
# every reference, so no reference can yield REPRODUCED.
HISTORICAL_REFERENCE_SHA256: str | None = None
FIT_SIGNATURE_KEYS = (
    "q_invariant_fit_signature_sha256",
    "rank_refresh_fit_audit",
    "resolved_spec_sha256s",
    "refit_provenance",
)
BASELINE_SOURCES = (
    "src/populace_dynamics/harness/m6_projection.py",
    "src/populace_dynamics/harness/m6_runner.py",
    "src/populace_dynamics/harness/m6_candidate3_runner.py",
    "src/populace_dynamics/harness/m6_population.py",
    "src/populace_dynamics/harness/m6_inputs.py",
    "src/populace_dynamics/harness/m6_scoring.py",
    "src/populace_dynamics/harness/m6_cells.py",
    "src/populace_dynamics/engine/forward_earnings.py",
    "src/populace_dynamics/engine/earnings_domain.py",
    "src/populace_dynamics/engine/rng.py",
    "src/populace_dynamics/engine/loop.py",
    "src/populace_dynamics/engine/steps.py",
    "src/populace_dynamics/engine/refit.py",
    "src/populace_dynamics/engine/support.py",
    "scripts/registered_m6_inputs.py",
    "scripts/registered_m6_candidate2_inputs.py",
    "scripts/registered_m6_candidate3_inputs.py",
)
DISCLOSURE = (
    "Candidate 3 records a valid M6 pass; it certifies nothing about mortality "
    "drift. The artifact records four passing seeds, q=0.55 and rho=−0.6. "
    "Fits use data through 2014; gated demographic flows cover 2015–2019 and "
    "earnings cover 2016/2018. The 2020–2022 window is diagnostic only. "
    "Certification is conditional on prior structural and same-holdout "
    "surface selection. The v4 point estimate p_gate=0.9018301 clears 0.90 "
    "by 0.0018301, but its clearance is not statistically resolved: the "
    "reported jackknife SE is approximately 0.013–0.019. Synthesized "
    "support, redrawn initial states and endogenous widowhood require the "
    "decision-5 successor gate."
)


def json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
        + b"\n"
    )


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _scalar(value: Any) -> Any:
    if value is pd.NA:
        return {"missing": "pd.NA"}
    if isinstance(value, (float, np.floating)):
        return {"float64_hex": np.float64(value).tobytes().hex()}
    if isinstance(value, np.generic):
        return value.item()
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise TypeError(f"unsupported frame scalar {type(value).__name__}")


def frame_payload(frame: pd.DataFrame) -> dict:
    """Lossless typed columns; floating values retain their actual bits."""
    return {
        "columns": [
            {
                "name": name,
                "dtype": str(frame[name].dtype),
                "values": [_scalar(value) for value in frame[name]],
            }
            for name in frame.columns
        ]
    }


def _json_canonical(value: Any) -> Any:
    """``value`` in the JSON types a committed artifact records."""
    return json.loads(json_bytes(value))


def _fit_lineage_signature(lineage: Mapping[str, Any]) -> dict:
    """The registered fit-lineage fields, in the artifact's JSON types."""
    return _json_canonical({key: lineage[key] for key in FIT_SIGNATURE_KEYS})


@dataclass(frozen=True)
class HistoricalReference:
    """Raw reference bytes; records are parsed only after re-hashing them.

    No hash label or parsed record is stored, so a caller can neither
    relabel other bytes nor edit records after authentication.
    """

    payload: bytes

    @property
    def digest(self) -> str:
        return sha256(self.payload)


def _committed_reference_sha256() -> str:
    if HISTORICAL_REFERENCE_SHA256 is None:
        raise ValueError(
            "no HISTORICAL_REFERENCE_SHA256 is committed; B1 refuses every "
            "historical reference"
        )
    return HISTORICAL_REFERENCE_SHA256


def authenticated_records(reference: HistoricalReference) -> dict:
    """Re-hash the reference bytes against the committed constant, then parse.

    Every call parses afresh from the immutable payload, never infers the
    origin, and refuses any bytes whose SHA-256 is not committed.
    """
    expected_sha256 = _committed_reference_sha256()
    if reference.digest != expected_sha256:
        raise ValueError(
            f"historical reference SHA256 {reference.digest} differs from "
            f"the committed HISTORICAL_REFERENCE_SHA256 {expected_sha256}"
        )
    content = json.loads(reference.payload)
    if (
        content.get("schema_version") != "track_b_b1_historical_reference.v1"
        or content.get("baseline_sha256") != BASELINE_SHA256
        or content.get("origin") != "historical_candidate3_run"
    ):
        raise ValueError("historical reference identity is not candidate 3")
    records = {}
    for row in content["records"]:
        if type(row["seed"]) is not int or type(row["draw"]) is not int:
            raise ValueError("historical seed and draw must be integers")
        key = (row["seed"], row["draw"])
        if key in records:
            raise ValueError(f"duplicate historical reference draw {key}")
        columns = {}
        for column in row["scored"]["columns"]:
            name = column["name"]
            if name in columns:
                raise ValueError(f"duplicate reference column {name}")
            values = []
            for value in column["values"]:
                if isinstance(value, dict) and "float64_hex" in value:
                    bits = bytes.fromhex(value["float64_hex"])
                    if len(bits) != 8:
                        raise ValueError(
                            "reference float64 must have exactly eight bytes"
                        )
                    value = np.frombuffer(bits, dtype=np.float64)[0]
                elif value == {"missing": "pd.NA"}:
                    value = pd.NA
                values.append(value)
            columns[name] = pd.Series(values, dtype=column["dtype"])
        records[key] = {
            "scored": pd.DataFrame(columns),
            "fit_signature": row["fit_signature"],
            "rng_signature": row["rng_signature"],
        }
    return records


def read_historical_reference(path: Path) -> HistoricalReference:
    """Read the committed-hash archive; never infer its origin.

    Only bytes hashing to ``HISTORICAL_REFERENCE_SHA256`` are admitted, and
    that value changes only through a reviewed commit. While it is None the
    file is not read. A newly regenerated file cannot be promoted to a
    historical reference.
    """
    _committed_reference_sha256()
    reference = HistoricalReference(path.read_bytes())
    authenticated_records(reference)  # Fail before any data access.
    return reference


def _git(root: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-c", "core.fsmonitor=false", *args],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout


def reserve_output(root: Path, output: Path | str) -> Path:
    """Reserve only the B1 directory, exclusively, before loading any input."""
    root = root.resolve()
    requested = Path(output)
    if not requested.is_absolute():
        requested = root / requested
    expected = root / DEFAULT_OUTPUT
    if requested != expected:
        raise ValueError(f"B1 output must be {DEFAULT_OUTPUT}")
    for path in (expected, *expected.parents):
        if path == root:
            break
        if path.is_symlink():
            raise ValueError("B1 output and its parents must not be symlinks")
    if expected.resolve() != expected:
        raise ValueError("B1 output escaped its exclusive location")
    if _git(root, "ls-files", "--", DEFAULT_OUTPUT.as_posix()).strip():
        raise ValueError("B1 output collides with tracked files")
    expected.parent.mkdir(parents=True, exist_ok=True)
    expected.mkdir()  # exist_ok=False also closes the concurrent-run race.
    return expected


def _write_new(path: Path, value: Any) -> str:
    payload = json_bytes(value)
    with path.open("xb") as stream:
        stream.write(payload)
    return sha256(payload)


def _evidence_files(destination: Path) -> list[dict]:
    return [
        {"path": path.name, "sha256": sha256(path.read_bytes())}
        for path in sorted(destination.glob("seed_*_draw_*.json"))
    ]


def _publish(destination: Path, result: dict) -> dict:
    """Write result.json; an unserializable result publishes a fallback.

    ``json_bytes`` fails before the file is opened, so the fallback record is
    the only write. It keeps every top-level field that serializes on its
    own, plus a repr of the whole result, and it never reports a
    reproduction.
    """
    unserializable = (TypeError, ValueError, RecursionError)
    try:
        _write_new(destination / "result.json", result)
        return result
    except unserializable as error:
        try:
            attempted = repr(result)
        except Exception as repr_error:
            attempted = f"<repr failed: {type(repr_error).__name__}>"
        kept, dropped = {}, []
        for key, value in result.items():
            if key in {"status", "equal", "admitted_scope"}:
                continue
            try:
                json_bytes(value)
            except unserializable:
                dropped.append(str(key))
            else:
                kept[str(key)] = value
        fallback = {
            "schema_version": SCHEMA_VERSION,
            "registration_id": str(result.get("registration_id")),
            "verification_class": "reproduction",
            "status": "BASELINE_REPLAY_MISMATCH",
            "equal": False,
            "admitted_scope": "none",
            "disclosure": DISCLOSURE,
            "publishes_regardless": True,
            "publication_error": {
                "type": type(error).__name__,
                "message": str(error),
                "traceback": traceback.format_exc(),
            },
            "serializable_result_fields": kept,
            "unserializable_result_fields": sorted(dropped),
            "unserializable_result_repr": attempted,
            "partial_files": _evidence_files(destination),
        }
        _write_new(destination / "result.json", fallback)
        return fallback


def source_guard(root: Path, expected_commit: str) -> dict:
    """Bind the new registered commit and the untouched historical sources."""
    head = _git(root, "rev-parse", "HEAD").decode().strip()
    if head != expected_commit:
        raise ValueError("HEAD does not equal --expected-commit")
    for args in (("diff", "--exit-code"), ("diff", "--cached", "--exit-code")):
        _git(root, *args)
    imported = Path(__file__).resolve()
    if imported != root / "src/populace_dynamics/track_b/runner.py":
        raise ValueError("B1 imported code outside the registered worktree")
    hashes = {}
    for name in BASELINE_SOURCES:
        original = _git(root, "show", f"{BASELINE_COMMIT}:{name}")
        current = (root / name).read_bytes()
        if current != original:
            raise ValueError(
                f"historical source changed: {name}; "
                f"expected_sha256={sha256(original)}; actual_sha256={sha256(current)}"
            )
        hashes[name] = sha256(current)
    for name in (
        _git(
            root,
            "ls-files",
            "src/populace_dynamics/track_b",
            "scripts/run_track_b_b1.py",
        )
        .decode()
        .splitlines()
    ):
        hashes[name] = sha256((root / name).read_bytes())
    if "scripts/run_track_b_b1.py" not in hashes:
        raise ValueError("B1 runner must be committed before data access")
    baseline_bytes = (root / BASELINE_PATH).read_bytes()
    if sha256(baseline_bytes) != BASELINE_SHA256:
        raise ValueError("registered candidate-3 artifact hash changed")
    environment = root / f"{BASELINE_PATH}.env.json"
    if sha256(environment.read_bytes()) != ENVIRONMENT_SHA256:
        raise ValueError("registered environment sidecar hash changed")
    return {
        "commit": head,
        "baseline_commit": BASELINE_COMMIT,
        "baseline_sha256": BASELINE_SHA256,
        "source_sha256": hashes,
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
        },
    }


def _scored_surface(frame: pd.DataFrame, population: Any) -> pd.DataFrame:
    projection, truth = restrict_earnings_domain_support(
        frame, population.earnings_support, population.earnings_domain_ids
    )
    return prepare_gated_realized_support(
        projection,
        truth,
        realized_presence=truth[["person_id", "period"]].drop_duplicates(),
        start_weights=population.start_weights,
        presence_basis=PresenceBasis.EXACT_WAVE,
        period_column="period",
    ).projection


def run_differential(
    *,
    populations: Mapping[int, Any],
    generator: Any,
    fit_signature: Mapping[str, Any],
    baseline: Mapping[str, Any],
    output: Path,
    seeds: tuple[int, ...] = REGISTERED_SEEDS,
    draws: tuple[int, ...] = REGISTERED_DRAWS,
    historical_reference: HistoricalReference | None = None,
) -> dict:
    """Compare every original scored row to the copied loop on supplied data.

    This seam accepts invented populations. Production fixes seeds/draws to
    the registered full product; no best-seed selection or tolerances exist.
    """
    historical_records = (
        None
        if historical_reference is None
        else authenticated_records(historical_reference)
    )
    replay_fit = _json_canonical(fit_signature)
    # Both loops receive the one generator in ``arguments``, so neither has
    # a fit signature of its own. The original side carries the committed
    # candidate-3 lineage and the copy carries the supplied refit. These are
    # independent sources, but the check repeats production's
    # ``registered_fit`` comparison and cannot tell the two loops apart. A
    # per-loop fit signature would need a hook inside m6_projection.py, a
    # protected historical source that returns only the scored frame.
    original_fit = _fit_lineage_signature(baseline["lineage"])
    # The incumbent sizes its registry from its own PROJECTION_END_YEAR
    # (m6_projection.py:198-200); the copy uses replay.RNG_N_PERIODS. Only
    # n_periods is sourced independently: periods, ordinals and codes still
    # come from the copy's _rng_signature over the same IDs, and registry
    # size changes no stream (rng.py:66-67 spawns child ``period`` of a fresh
    # root). This check catches registry-size drift only; stream equality is
    # evidenced by the scored-frame comparison.
    original_n_periods = m6_projection.PROJECTION_END_YEAR - 2014
    expected, observed, files, cell_differences = {}, {}, [], []
    for seed in seeds:
        population = populations[seed]
        for draw in draws:
            arguments = dict(
                initial_slice=population.initial_slice,
                truth_support=population.earnings_support,
                generator=generator,
                domain_person_ids=population.earnings_domain_ids,
                all_person_ids=population.holdout_ids,
                draw_index=draw,
            )
            original = _scored_surface(
                project_earnings_on_realized_support(**arguments), population
            )
            replay = replay_earnings_on_realized_support(**arguments)
            copied = _scored_surface(replay.scored, population)
            original_rng = earnings_rng_signature(
                all_person_ids=population.holdout_ids,
                draw_index=draw,
                n_periods=original_n_periods,
            )
            expected[seed, draw] = dict(
                scored=original,
                fit_signature=original_fit,
                rng_signature=original_rng,
            )
            observed[seed, draw] = dict(
                scored=copied,
                fit_signature=replay_fit,
                rng_signature=replay.rng_signature,
            )
            cells = earnings_cells(original)
            registered_seed = next(
                row
                for row in baseline["family_a"]["per_seed"]
                if row["seed"] == seed
            )
            for cell in EARNINGS_CELL_NAMES:
                registered = registered_seed["gated_cells"][cell][
                    "per_draw_rate"
                ][draw]
                actual = float(cells[cell]["value"])
                if (
                    registered is None
                    or np.float64(registered).tobytes()
                    != np.float64(actual).tobytes()
                ):
                    cell_differences.append(
                        dict(
                            seed=seed,
                            draw=draw,
                            cell=cell,
                            expected=_scalar(registered),
                            actual=_scalar(actual),
                        )
                    )
            name = f"seed_{seed}_draw_{draw}.json"
            payload = {
                "seed": seed,
                "draw": draw,
                "annual_history": frame_payload(replay.history),
                "original_scored": frame_payload(original),
                "replay_scored": frame_payload(copied),
                "original_fit_signature": original_fit,
                "replay_fit_signature": replay_fit,
                "original_rng_signature": original_rng,
                "replay_rng_signature": replay.rng_signature,
            }
            files.append(
                {"path": name, "sha256": _write_new(output / name, payload)}
            )
    differential = compare_replay(
        expected, observed, registered_seeds=seeds, registered_draws=draws
    )
    differential["verification_class"] = "differential_test"
    if differential["equal"]:
        differential["status"] = "MATCH"
    if historical_records is not None:
        historical = compare_replay(
            historical_records,
            observed,
            registered_seeds=seeds,
            registered_draws=draws,
        )
        equal = (
            historical["equal"]
            and differential["equal"]
            and not cell_differences
        )
        return {
            "status": "REPRODUCED" if equal else "BASELINE_REPLAY_MISMATCH",
            "equal": equal,
            "verification_class": "reproduction",
            "admitted_scope": (
                "candidate-3 registered earnings reproduction only"
                if equal
                else "none"
            ),
            "baseline_kind": "authenticated_historical_person_level_reference",
            "historical_person_level_reference_available": True,
            "historical_equality": historical,
            "differential": differential,
            "registered_per_draw_cells": {
                "equal": not cell_differences,
                "differences": cell_differences,
            },
            "files": files,
        }
    # The original artifact provides no archived person-level or RNG witness.
    # Aggregate agreement cannot substitute for that missing evidence.
    return {
        "status": "BASELINE_REPLAY_MISMATCH",
        "equal": False,
        "verification_class": "reproduction",
        "admitted_scope": "none",
        "baseline_kind": "reconstructed_original_scored_path",
        "historical_person_level_reference_available": False,
        "differences": [
            {
                "reason": "historical_person_level_reference_unavailable",
                "message": "Committed candidate 3 has no archived per-person earnings, support, weights or RNG signatures.",
            }
        ],
        "differential": differential,
        "registered_per_draw_cells": {
            "equal": not cell_differences,
            "differences": cell_differences,
        },
        "files": files,
    }


def production_replay(
    root: Path,
    output: Path,
    baseline: dict,
    *,
    historical_reference: HistoricalReference | None = None,
) -> dict:
    """Lazy registered-input path; never called by invented-data tests."""
    import registered_m6_candidate3_inputs

    from populace_dynamics.harness import m6_candidate3_runner as candidate
    from populace_dynamics.harness.m6_population import (
        subset_realized_population,
    )
    from populace_dynamics.harness.m6_runner import materialize_m6_refit_phase
    from populace_dynamics.harness.m6_scoring import side_a_person_ids

    environment = candidate._frozen_gate_environment()
    plan = registered_m6_candidate3_inputs.build_input_plan()
    if not isinstance(plan, candidate.M6Candidate3InputPlan):
        raise TypeError(
            "registered factory did not return candidate-3 input plan"
        )
    bundle = candidate._fit_candidate3(plan.fit_inputs)
    fit_preflight = candidate._preflight_candidate3_first_marriage(bundle)
    inputs = plan.load_full_inputs()
    if inputs.refit_inputs is not plan.fit_inputs:
        raise ValueError("input plan replaced the preflighted fit inputs")
    phase = materialize_m6_refit_phase(inputs, bundle)
    fit = _fit_lineage_signature(phase.lineage)
    expected_fit = _fit_lineage_signature(baseline["lineage"])
    fit_equal = json_bytes(fit) == json_bytes(expected_fit)
    provenance = inputs.provenance.to_artifact()
    provenance_equal = json_bytes(provenance) == json_bytes(
        baseline["provenance"]
    )
    populations = {
        seed: subset_realized_population(
            phase.population,
            side_a_person_ids(
                phase.population.anchor, split_unit="person", seed=seed
            ),
        )
        for seed in REGISTERED_SEEDS
    }
    result = run_differential(
        populations=populations,
        generator=bundle.earnings.generator,
        fit_signature=fit,
        baseline=baseline,
        output=output,
        historical_reference=historical_reference,
    )
    result["registered_fit"] = {
        "equal": fit_equal,
        "expected": expected_fit,
        "actual": fit,
    }
    result["registered_input_provenance"] = {
        "equal": provenance_equal,
        "expected": baseline["provenance"],
        "actual": provenance,
    }
    result["fit_preflight"] = fit_preflight
    result["frozen_candidate3_environment"] = environment
    if not fit_equal or not provenance_equal:
        result.update(
            status="BASELINE_REPLAY_MISMATCH",
            equal=False,
            admitted_scope="none",
        )
    return result


def execute(
    *,
    root: Path,
    registration_id: str,
    expected_commit: str,
    output: Path | str = DEFAULT_OUTPUT,
    operation: Callable[[Path, Path, dict], dict] = production_replay,
    historical_reference: Path | None = None,
) -> dict:
    """Reserve output, check registration/source, then compute or record abort.

    A historical reference is admitted only when its bytes hash to the
    committed ``HISTORICAL_REFERENCE_SHA256``; there is no caller-supplied
    hash. While that constant is None, every reference aborts the attempt.
    No operation can publish REPRODUCED without such an admitted reference.
    """
    from populace_dynamics.harness.m6_candidate3_runner import (
        validate_candidate3_registration_id,
    )

    root = root.resolve()
    registration = validate_candidate3_registration_id(registration_id)
    if registration.rsplit("issuecomment-", 1)[-1] == "5064153427":
        raise ValueError("B1 requires a fresh reproduction registration")
    destination = reserve_output(root, output)
    result = {
        "schema_version": SCHEMA_VERSION,
        "registration_id": registration,
        "verification_class": "reproduction",
        "admitted_scope": "none",
        "disclosure": DISCLOSURE,
        "publishes_regardless": True,
    }
    try:
        source = source_guard(root, expected_commit)
        baseline = json.loads((root / BASELINE_PATH).read_text())
        if (
            tuple(baseline["protocol"]["gate_seeds"]) != REGISTERED_SEEDS
            or tuple(baseline["protocol"]["draw_index"]) != REGISTERED_DRAWS
            or baseline["protocol"]["draw_seeds"] != list(range(5200, 5220))
        ):
            raise ValueError("registered seed/draw protocol changed")
        result["source"] = source
        reference = None
        if historical_reference is not None:
            result["historical_reference"] = {
                "path": str(historical_reference),
                "committed_sha256": HISTORICAL_REFERENCE_SHA256,
            }
            reference = read_historical_reference(historical_reference)
            result["historical_reference"]["sha256"] = reference.digest
            if operation is not production_replay:
                raise ValueError(
                    "historical references require the production operation"
                )
            result.update(
                production_replay(
                    root, destination, baseline, historical_reference=reference
                )
            )
        else:
            result.update(operation(root, destination, baseline))
        if source_guard(root, expected_commit) != source:
            raise ValueError("registered source changed during replay")
        if result.get("status") == "REPRODUCED" and reference is None:
            raise ValueError(
                "REPRODUCED requires a historical reference admitted by the "
                "committed HISTORICAL_REFERENCE_SHA256"
            )
    except Exception as error:
        result.update(
            status="BASELINE_REPLAY_MISMATCH",
            equal=False,
            admitted_scope="none",
            abort={
                "type": type(error).__name__,
                "message": str(error),
                "traceback": traceback.format_exc(),
            },
        )
        result["partial_files"] = _evidence_files(destination)
    return _publish(destination, result)
