"""Standalone, explicit-dataset PE-US child for Registration 19.

This file is executed by path in the pinned PE-US interpreter.  It imports
no Dynamics module and accepts one JSON job on stdin.  Invented generation
is deterministic array logic; only this child needs HDFStore support.
"""

from __future__ import annotations

import contextlib
import gc
import hashlib
import json
import os
import resource
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

FRAME_SHA256 = (
    "6496cc4393d4d3c6574f76eca231de5898c803b9067645591fd5c4d3e65aee84"
)
COMPONENTS = (
    "social_security_retirement",
    "social_security_survivors",
    "social_security_dependents",
    "social_security_disability",
)
GROUPS = ("household", "tax_unit", "spm_unit", "family", "marital_unit")
FRAME_COLUMNS = (
    "A_MARITL",
    "cps_race",
    "is_hispanic",
    "is_female",
    "person_support_channel",
    "A_LINENO",
)
PERSON_VARIABLES = (
    "social_security",
    *COMPONENTS,
    "ssi_if_takes_up",
    "ssi",
    "ssi_countable_resources",
    "ssi_claim_is_joint",
    "is_ssi_aged_blind_disabled",
    "is_ssi_qualified_noncitizen",
    "immigration_status",
    "takes_up_ssi_if_eligible",
)
HOUSEHOLD_VARIABLES = (
    "household_weight",
    "household_count_people",
    "household_market_income",
    "household_benefits",
    "household_health_benefits",
    "household_income_decile",
    "household_state_benefits",
    "household_net_income",
)


# Set by run_job once a registered job's registration record has been
# validated. Without it, no helper here will build a simulation on the
# real frame.
_REGISTRATION: dict[str, str] | None = None
_HASHES: dict[tuple[str, int, int], str] = {}
_POINTER = (
    r"https://github\.com/PolicyEngine/microcosm-dynamics/issues/42"
    r"#issuecomment-[0-9]+"
)


def _registration(job: dict[str, Any]) -> dict[str, str] | None:
    """Validate the registration record a registered job must carry."""
    import re

    if not job.get("registered", False):
        return None
    record = job.get("registration")
    if (
        not isinstance(record, dict)
        or not re.fullmatch(_POINTER, str(record.get("pointer", "")))
        or not re.fullmatch(r"[0-9a-f]{40}", str(record.get("commit", "")))
        or not re.fullmatch(
            r"[0-9a-f]{64}", str(record.get("specification_sha256", ""))
        )
    ):
        raise ValueError("registered job lacks a valid registration record")
    return {key: str(record[key]) for key in sorted(record)}


def _cached_sha256(path: Path) -> str:
    """Hash a dataset once per (path, size, modification time)."""
    stat = path.stat()
    key = (str(path.resolve()), stat.st_size, stat.st_mtime_ns)
    if key not in _HASHES:
        _HASHES[key] = _sha256(path)
    return _HASHES[key]


def _sha256(path: Path) -> str:
    """Hash a file incrementally, without interpreting its contents."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _check_frame(path: Path, *, expected_sha256: str, registered: bool) -> str:
    """Refuse unexpected bytes and unmarked data before PE-US is imported."""
    actual = _sha256(path)
    if actual != expected_sha256:
        raise ValueError(
            "frame SHA-256 differs from the parent's expected hash"
        )
    if actual == FRAME_SHA256:
        if not registered or _REGISTRATION is None:
            raise ValueError("real frame requires a registered entry point")
    else:
        with pd.HDFStore(path, mode="r") as store:
            if "/invented" not in store.keys():
                raise ValueError(
                    "non-real frame lacks an invented marker table"
                )
            marker = store["invented"]
            if (
                "invented" not in marker
                or len(marker) != 1
                or not isinstance(marker["invented"].iloc[0], (bool, np.bool_))
                or not marker["invented"].iloc[0]
            ):
                raise ValueError("invalid invented marker table")
    return actual


def _microsimulation(dataset: str | Path | None, reform: Any = None) -> Any:
    """Build only an explicitly supplied dataset, extended through 2026."""
    if dataset is None:
        raise ValueError(
            "an explicit dataset is required; defaults are unsafe"
        )
    if _cached_sha256(Path(dataset)) == FRAME_SHA256 and _REGISTRATION is None:
        raise ValueError("real frame requires a registered entry point")
    from policyengine_us import Microsimulation

    options = {}
    if reform is not None:
        # PE-US's SPMSimulationMixin clones a supplied system before a
        # reform writes to it (spm.py::_prepare_spm_system). This keeps
        # policy state private while reusing the already loaded parameters.
        options["tax_benefit_system"] = (
            Microsimulation.default_tax_benefit_system_instance
        )
    return Microsimulation(
        dataset=str(dataset),
        reform=reform,
        dataset_end_year=2026,
        **options,
    )


def _no_asset_test_reform() -> Any:
    """Replace the resource-test formula structurally with an all-true array."""
    from policyengine_core.reforms import Reform
    from policyengine_us.model_api import MONTH, Person, Variable

    class meets_ssi_resource_test(Variable):
        value_type = bool
        entity = Person
        definition_period = MONTH
        label = "SSI resource test removed for Registration 19"

        def formula(person, period, parameters):
            return np.ones(person.count, dtype=bool)

    class NoAssetTest(Reform):
        def apply(self):
            self.update_variable(meets_ssi_resource_test)

    return NoAssetTest


def _calculated(sim: Any, name: str, period: str = "2026") -> np.ndarray:
    """Keep calculation values unweighted and decode enumerations to strings."""
    values = sim.calculate(name, period, use_weights=False)
    if hasattr(values, "decode_to_str"):
        return np.asarray(values.decode_to_str(), dtype=str)
    array = np.asarray(values)
    if array.dtype.kind == "f":
        return array.astype(np.float64)
    if array.dtype.kind in "OUS":
        return array.astype(str)
    return array.copy()


def _memberships(sim: Any) -> dict[str, np.ndarray]:
    """Entity ids and dense person memberships in simulation order."""
    out = {
        f"{entity}_id": np.asarray(sim.populations[entity].ids).copy()
        for entity in ("person", "household", "marital_unit")
    }
    for entity in ("household", "marital_unit"):
        out[f"{entity}_index"] = np.asarray(
            sim.populations[entity].members_entity_id, dtype=np.int64
        ).copy()
    out["unit_index"] = out["marital_unit_index"].copy()
    return out


def _probe(path: Path) -> tuple[dict[str, np.ndarray], dict[str, float]]:
    """Read baseline components and verified frame columns from one simulation."""
    started = time.perf_counter()
    sim = _microsimulation(path)
    built = time.perf_counter()
    out = _memberships(sim)
    with pd.HDFStore(path, mode="r") as store:
        frame = store["person"]
        # Column names only, for the parent's guard against stored
        # variables that would shadow the formulas the run calculates.
        names = set(frame.columns)
        for key in store.keys():
            if key in ("/person", "/invented"):
                continue
            # Some tables are a Series (the frame's time period) and have
            # no columns; an empty read costs nothing either way.
            table = store.select(key, start=0, stop=0)
            names |= {str(name) for name in getattr(table, "columns", ())}
    out["frame_column_names"] = np.asarray(sorted(names), dtype=str)
    if not np.array_equal(frame["person_id"].to_numpy(), out["person_id"]):
        raise ValueError("HDFStore person order differs from simulation order")
    for name in COMPONENTS:
        values = sim.calculate(name, "2026", use_weights=False)
        if np.asarray(values).dtype != np.dtype("float32"):
            raise ValueError(
                f"{name}: baseline calculate did not return float32"
            )
        out[name] = np.asarray(values, dtype=np.float64)
        out[f"frame_{name}"] = frame[name].to_numpy(dtype=np.float64)
    out["age"] = _calculated(sim, "age")
    out["frame_age"] = frame["age"].to_numpy()
    for name in FRAME_COLUMNS:
        array = frame[name].to_numpy()
        out[name] = (
            array.astype(str) if array.dtype.kind == "O" else array.copy()
        )
    done = time.perf_counter()
    del sim, frame
    gc.collect()
    return out, {
        "build_seconds": built - started,
        "calculate_seconds": done - built,
        "total_seconds": done - started,
    }


def _scenario(
    path: Path, *, variant: str, components_path: Path
) -> tuple[dict[str, np.ndarray], dict[str, float]]:
    """Re-probe, set every component before calculation, then calculate SSI."""
    started = time.perf_counter()
    baseline, probe_timings = _probe(path)
    reform = {
        "asset_test_as_encoded": None,
        "no_asset_test": _no_asset_test_reform,
    }
    if variant not in reform:
        raise ValueError(f"unknown SSI variant: {variant}")
    selected_reform = reform[variant]
    sim = _microsimulation(
        path, selected_reform() if selected_reform is not None else None
    )
    built = time.perf_counter()
    out = _memberships(sim)
    # Entity order and exact inputs are the parent's refusal checks 3 and 4
    # (specification section 10); the child returns the arrays and lets the
    # parent record a failure under its registered number.
    with np.load(components_path, allow_pickle=False) as components:
        inputs = {
            name: np.asarray(components[name], dtype=np.float64).copy()
            for name in COMPONENTS
        }
    for name, values in inputs.items():
        if values.shape != (sim.populations["person"].count,):
            raise ValueError(f"{name}: incorrect input-array length")
        if not np.isfinite(values).all() or (values < 0).any():
            raise ValueError(
                f"{name}: component input is not finite/nonnegative"
            )
        sim.set_input(name, "2026", values)
        out[f"baseline_{name}"] = baseline[name]
    del baseline
    gc.collect()
    for name in PERSON_VARIABLES:
        out[name] = _calculated(sim, name)
    out["meets_ssi_resource_test"] = _calculated(
        sim, "meets_ssi_resource_test", "2026-01"
    )
    if variant == "no_asset_test" and not out["meets_ssi_resource_test"].all():
        raise ValueError(
            "structural no-asset-test reform did not pass everyone"
        )
    for name in HOUSEHOLD_VARIABLES:
        out[name] = _calculated(sim, name)
    limits = sim.tax_benefit_system.parameters(
        "2026-01-01"
    ).gov.ssa.ssi.eligibility.resources.limit
    out["individual_limit"] = np.asarray(float(limits.individual))
    out["couple_limit"] = np.asarray(float(limits.couple))
    done = time.perf_counter()
    del sim
    gc.collect()
    return out, {
        "baseline_probe_seconds": probe_timings["total_seconds"],
        "build_seconds": built - started - probe_timings["total_seconds"],
        "calculate_seconds": done - built,
        "total_seconds": done - started,
    }


def invented_arrays(
    households: int, persons: int, seed: int
) -> dict[str, dict[str, np.ndarray]]:
    """Invent deterministic entity arrays, including the registered edge cases.

    At frame size, exactly 5,924 records have the fixed four-component
    proportions. Small frames keep a scaled invented count. The first six
    households, when counts permit, are single low/high/bank-stock cases,
    joint ABD and non-ABD-spouse couples, and an older-parent household.
    """
    if (
        isinstance(households, bool)
        or isinstance(persons, bool)
        or not isinstance(households, int)
        or not isinstance(persons, int)
        or not 0 < households <= persons
    ):
        raise ValueError("invented counts need 0 < households <= persons")
    rng = np.random.default_rng(seed)
    sizes = np.ones(households, dtype=np.int64)
    special = households >= 7 and persons >= households + 4
    if special:
        sizes[:6] = [1, 1, 1, 2, 2, 3]
        first_generic = 6
    else:
        first_generic = 0
    remaining = persons - int(sizes.sum())
    generic = households - first_generic
    sizes[first_generic:] += remaining // generic
    sizes[first_generic : first_generic + remaining % generic] += 1
    starts = np.concatenate(([0], np.cumsum(sizes)[:-1]))
    household_index = np.repeat(np.arange(households), sizes)
    lines = np.arange(persons) - np.repeat(starts, sizes) + 1
    paired = sizes[household_index] >= 2
    marital_start = lines == 1
    marital_start |= (lines > 2) | ~paired
    unit_index = np.cumsum(marital_start, dtype=np.int64) - 1
    units = int(unit_index[-1]) + 1
    age = rng.choice(
        [8, 16, 30, 60, 62, 64, 65, 68, 70, 74, 78, 80, 85], persons
    ).astype(np.int32)
    age[(lines <= 2) & paired] = rng.choice(
        [30, 64, 68, 70, 74], int(((lines <= 2) & paired).sum())
    )
    age[(lines > 2)] = rng.choice([8, 16, 30, 80, 85], int((lines > 2).sum()))
    marital = rng.choice([4, 5, 6, 7], persons).astype(np.int32)
    marital[(lines <= 2) & paired] = 1
    female = rng.random(persons) < 0.5
    disabled = (age < 65) & (rng.random(persons) < 0.2)
    blind = rng.random(persons) < 0.025
    immigration = rng.choice(
        ["CITIZEN", "REFUGEE", "UNDOCUMENTED"],
        persons,
        p=[0.9, 0.05, 0.05],
    )
    takeup = rng.random(persons) < 0.8
    employment = np.where(age < 62, rng.uniform(0, 70000, persons), 0)
    pension = np.where(age >= 62, rng.uniform(0, 18000, persons), 0)
    total_ss = np.where(
        (age >= 62) | disabled, rng.uniform(600, 24000, persons), 0
    )
    kinds = rng.integers(0, 4, persons)
    components = {
        name: np.where(kinds == index, total_ss, 0.0)
        for index, name in enumerate(COMPONENTS)
    }
    holder = lines == 1
    bank = np.where(
        holder,
        rng.choice([0.0, 1500.0, 2500.0, 5000.0, 50000.0], persons),
        0.0,
    )
    stock = np.where(holder, rng.choice([0.0, 0.0, 2500.0], persons), 0.0)
    bond = np.where(holder, rng.choice([0.0, 0.0, 500.0], persons), 0.0)
    if special:
        age[:10] = [68, 68, 68, 70, 70, 70, 64, 70, 68, 85]
        marital[:3] = 7
        marital[9] = 4
        female[:10] = [False, False, False, False, True] * 2
        disabled[:10] = blind[:10] = False
        immigration[:10] = "CITIZEN"
        takeup[:10] = True
        # Potential SSI is positive for this non-taker without an asset
        # test; the eligibility-basis worked examples are unchanged.
        takeup[1] = False
        employment[:10] = pension[:10] = 0.0
        bank[:10] = [1500, 50000, 0, 2500, 0, 2500, 0, 5000, 0, 0]
        stock[:10] = [0, 0, 2500, 0, 0, 0, 0, 0, 0, 0]
        bond[:10] = 0
        for values in components.values():
            values[:10] = 0
        components[COMPONENTS[0]][:10] = [
            8916,
            8916,
            8916,
            4000,
            4000,
            4000,
            0,
            4000,
            4000,
            0,
        ]
    split_count = (
        5924
        if (households, persons) == (57240, 166321)
        else max(1, round(persons * 5924 / 166321))
    )
    available = np.arange(10 if special else 0, persons)
    split_count = min(split_count, len(available))
    chosen = rng.choice(available, split_count, replace=False)
    split_total = rng.uniform(600, 24000, split_count)
    for name, proportion in zip(
        COMPONENTS, [0.2496, 0.3793, 0.1355, 0.2356], strict=True
    ):
        components[name][chosen] = split_total * proportion
    support = np.full(persons, "cps", dtype="U14")
    support[chosen] = "puf_tax_detail"
    person = {
        "person_id": np.arange(1, persons + 1, dtype=np.int64),
        "age": age,
        "A_MARITL": marital,
        "cps_race": rng.choice([1, 2, 4, 8], persons).astype(np.int32),
        "is_hispanic": rng.random(persons) < 0.2,
        "is_female": female,
        "person_support_channel": support,
        "A_LINENO": lines.astype(np.int32),
        **components,
        "bank_account_assets": bank,
        "stock_assets": stock,
        "bond_assets": bond,
        "employment_income": employment,
        "taxable_private_pension_income": pension,
        "takes_up_ssi_if_eligible": takeup,
        "meets_ssi_disability_criteria": disabled,
        "is_blind": blind,
        "immigration_status_str": immigration,
        "rent": np.where(holder, 9600.0, 0.0),
    }
    for name in GROUPS:
        indices = unit_index if name == "marital_unit" else household_index
        person[f"person_{name}_id"] = indices.astype(np.int64) + 1
        person[f"person_{name}_role"] = np.full(persons, "member")
    tables = {"person": person}
    for name in GROUPS:
        count = units if name == "marital_unit" else households
        tables[name] = {f"{name}_id": np.arange(1, count + 1, dtype=np.int64)}
    tables["household"].update(
        {
            "household_weight": rng.uniform(0.5, 3.0, households),
            "state_fips": rng.choice([6, 12, 30, 36, 48], households),
        }
    )
    if special:
        tables["household"]["state_fips"][:6] = 12
    # Both are PE-US household inputs. Keep the enum consistent with the
    # frame's FIPS input so every geography reader sees the same state.
    fips_to_code = {6: "CA", 12: "FL", 30: "MT", 36: "NY", 48: "TX"}
    tables["household"]["state_code"] = np.asarray(
        [fips_to_code[int(fips)] for fips in tables["household"]["state_fips"]]
    )
    return tables


def write_invented_frame(
    path: Path,
    households: int,
    persons: int,
    seed: int,
    *,
    labels: Any = (),
    named_differences: Any = (),
) -> str:
    """Write invented 2024 entity tables exclusively and return their hash."""
    tables = invented_arrays(households, persons, seed)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb"):
        pass
    try:
        with pd.HDFStore(path, mode="w") as store:
            for entity, arrays in tables.items():
                store.put(entity, pd.DataFrame(arrays), format="table")
            store.put("_time_period", pd.Series([2024]), format="table")
            store.put(
                "invented",
                pd.DataFrame(
                    {
                        "invented": [True],
                        "seed": [seed],
                        "label": ["INVENTED DRY RUN - NOT RESULTS"],
                        "households": [households],
                        "persons": [persons],
                        "metadata_labels": [json.dumps(list(labels))],
                        "metadata_named_differences": [
                            json.dumps(list(named_differences))
                        ],
                    }
                ),
                format="table",
            )
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return _sha256(path)


def _peak_rss_bytes() -> int:
    """Normalize resource.getrusage's Linux KiB and macOS byte units."""
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(peak if sys.platform == "darwin" else peak * 1024)


def run_job(job: dict[str, Any]) -> dict[str, Any]:
    """Execute one parent job, exchanging arrays solely through an NPZ file."""
    global _REGISTRATION
    started = time.perf_counter()
    _REGISTRATION = _registration(job)
    path = Path(job.get("frame_path", job.get("path", "")))
    if not str(path) or str(path) == ".":
        raise ValueError("a frame_path is required")
    if job["mode"] == "write-invented":
        digest = write_invented_frame(
            path,
            int(job["households"]),
            int(job["persons"]),
            int(job["seed"]),
            labels=job.get("labels", ()),
            named_differences=job.get("named_differences", ()),
        )
        return {
            "frame_path": str(path),
            "sha256": digest,
            "timings": {"total_seconds": time.perf_counter() - started},
            "peak_rss_bytes": _peak_rss_bytes(),
        }
    digest = _check_frame(
        path,
        expected_sha256=job["expected_sha256"],
        registered=job.get("registered", False),
    )
    if job["mode"] == "probe":
        arrays, timings = _probe(path)
    elif job["mode"] == "scenario":
        arrays, timings = _scenario(
            path,
            variant=job["variant"],
            components_path=Path(job["components_path"]),
        )
    else:
        raise ValueError(f"unknown child mode: {job['mode']}")
    arrays["metadata_labels"] = np.asarray(job.get("labels", []), dtype=str)
    arrays["metadata_named_differences"] = np.asarray(
        json.dumps(job.get("named_differences", []))
    )
    output = Path(job["output_path"])
    handle = output.open("xb")
    try:
        with handle:
            np.savez(handle, **arrays)
    except BaseException:
        # Opening exclusively proves ownership; an existing destination
        # raises before this cleanup can remove another process's file.
        output.unlink(missing_ok=True)
        raise
    return {
        "array_path": str(output),
        "frame_sha256": digest,
        "dataset_end_year": 2026,
        "reform_construction": (
            "supplied_default_system_cloned_by_spm_mixin"
            if job.get("variant") == "no_asset_test"
            else "shared_default_system"
        ),
        "timings": {
            **timings,
            "process_seconds": time.perf_counter() - started,
        },
        "peak_rss_bytes": _peak_rss_bytes(),
        "checks": {"explicit_dataset": True, "frame_guard": True},
    }


def main() -> None:
    """Reserve stdout for the single JSON result; send package output to stderr."""
    # Executing this file by path otherwise places bridge/policyengine_us.py
    # ahead of the installed package with the same top-level name.
    directory = Path(__file__).resolve().parent
    sys.path[:] = [
        entry for entry in sys.path if Path(entry).resolve() != directory
    ]
    job = json.load(sys.stdin)
    with contextlib.redirect_stdout(sys.stderr):
        result = run_job(job)
    json.dump(result, sys.stdout, allow_nan=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
    # This one-job worker has closed its output files and finished JSON
    # serialization. Complete the successful process after flushing both
    # streams; exceptions above continue to produce a nonzero exit.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)
