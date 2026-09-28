"""Fail-closed entry contracts for a2-ratified-1 §§10–11 and 16–17."""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .manifest import (
    REGISTERED_HEADER,
    SPECIFICATION_PATH,
    SPECIFICATION_SHA256,
    SPECIFICATION_VERSION,
    file_record,
    object_sha256,
    runtime_parameter_bundle,
    verify_manifest,
)

REGISTRATION_POINTER = re.compile(
    r"https://github\.com/PolicyEngine/microcosm-dynamics/issues/42"
    r"#issuecomment-[0-9]+"
)
STRUCTURAL_OUTPUTS = (
    "d_unsupported_histories",
    "s_ordering_classes",
    "s_refused_earlier_spells",
    "opening_proxy_applications",
)
FROZEN_ROWS = tuple(
    f"{mechanism}×{row}"
    for mechanism in ("L", "D", "S", "DS")
    for row in (
        *(f"R{i}" for i in range(6)),
        *(f"F{i}" for i in range(8)),
        *(f"U{i}" for i in range(3)),
    )
)


@dataclass(frozen=True)
class PreflightRecord:
    """Evidence that scripts validated the frozen protocol before loading."""

    head: str
    specification_sha256: str
    registration_pointer: str
    protocol_sha256: str
    mode: str
    frozen_manifest_json: str = ""
    repository_root: str = ""
    frozen_input_roots_json: str = ""

    def validate_inputs(self, inputs) -> None:
        """Actual source identities and all effective parameters must match."""
        if not self.frozen_manifest_json or not self.repository_root:
            raise ValueError("preflight has no frozen runtime-input binding")
        manifest = json.loads(self.frozen_manifest_json)
        root = Path(self.repository_root)
        verify_manifest(manifest, root=root)
        expected = {
            str((root / item["path"]).resolve()): item["sha256"]
            for item in manifest["inputs"].values()
        }
        provenance = inputs.cohort.source_provenance
        files = provenance.get("psid_files_sha256", {})
        if not files or not provenance.get("psid_data_dir"):
            raise ValueError("runtime cohort has no sealed source-file record")
        data_root = Path(provenance["psid_data_dir"])
        for name, digest in files.items():
            if expected.get(str((data_root / name).resolve())) != digest:
                raise ValueError(
                    f"runtime input absent or changed in manifest: {name}"
                )
        actual = runtime_parameter_bundle(inputs)
        runtime = manifest["parameter_bundles"].get("runtime")
        if not runtime or runtime["sha256"] != object_sha256(actual):
            raise ValueError(
                "effective runtime parameter bundle differs from manifest"
            )


def git_output(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def preflight(
    *,
    root: Path,
    registration_pointer: str,
    registered_commit: str,
    output: Path,
    protocol: Mapping[str, Any],
    protocol_sha256: str,
    mode: str = "registered",
    git: Callable[..., str] | None = None,
) -> PreflightRecord:
    """Refuse before population reads on every non-frozen state (§11).

    §§11/17 do not prescribe a transport schema. Conservatively require
    the complete package and its canonical digest, including a specific
    execution procedure, rather than treating an issue URL as sufficient.
    """
    if mode not in ("registered", "structural"):
        raise ValueError("unknown execution mode")
    if not REGISTRATION_POINTER.fullmatch(registration_pointer):
        raise ValueError("registration pointer must name an issue #42 comment")
    if not re.fullmatch(r"[0-9a-f]{40}", registered_commit):
        raise ValueError("registered commit must be a full 40-hex SHA")
    run_git = git or (lambda *args: git_output(root, *args))
    head = run_git("rev-parse", "HEAD")
    if head != registered_commit:
        raise ValueError("HEAD is not the exact registered commit")
    if run_git("status", "--porcelain"):
        raise ValueError("registered execution requires a clean checkout")
    if file_record(SPECIFICATION_PATH, root=root)["sha256"] != (
        SPECIFICATION_SHA256
    ):
        raise ValueError("specification is not ratified a2-ratified-1 bytes")
    if output.exists() or output.is_symlink():
        raise ValueError("one-shot artifact already exists")
    if protocol_sha256 != object_sha256(protocol):
        raise ValueError("frozen protocol hash mismatch")
    expected = {
        "version": SPECIFICATION_VERSION,
        "mode": mode,
        "implementation_commit": registered_commit,
        "specification_sha256": SPECIFICATION_SHA256,
        "registration_pointer": registration_pointer,
        "draw_indices": list(range(20)),
        "root_seeds": list(range(5200, 5220)),
        "anchor_wave": 2011,
        "reference_year": 2030,
        "output": str(output.resolve()),
    }
    for key, expected_value in expected.items():
        if protocol.get(key) != expected_value:
            raise ValueError(f"frozen protocol mismatch: {key}")
    for key in ("executor", "environment", "procedure", "attempt_policy"):
        if not protocol.get(key):
            raise ValueError(f"frozen protocol lacks {key}")
    manifest = protocol.get("hash_manifest", {})
    verify_manifest(manifest, root=root)
    expected_implementation = {
        str(path.relative_to(root))
        for path in (
            *sorted((root / "src/populace_dynamics/track_a_v2").glob("*.py")),
            *sorted((root / "scripts").glob("track_a_v2_*.py")),
        )
    }
    supplied_implementation = {
        str((root / item["path"]).resolve().relative_to(root.resolve()))
        for item in manifest.get("implementation", [])
        if (root / item["path"]).resolve().is_relative_to(root.resolve())
    }
    if not expected_implementation or not expected_implementation.issubset(
        supplied_implementation
    ):
        raise ValueError("manifest omits Track A v2 implementation files")
    if manifest.get("header") != REGISTERED_HEADER:
        raise ValueError("invented manifest cannot authorize a registered run")
    if "statute" not in manifest.get("source_files", {}):
        raise ValueError("registered manifest lacks hashed statute source")
    # §11 freezes sources, not just a caller-chosen list of irrelevant
    # files. Explicit roots prevent an environment-variable path fallback.
    roots = protocol.get("input_roots")
    if not isinstance(roots, dict) or set(roots) != {
        "psid",
        "policyengine_us",
    }:
        raise ValueError("frozen protocol requires exact input roots")
    if not all(
        isinstance(value, str) and Path(value).is_absolute()
        for value in roots.values()
    ):
        raise ValueError("frozen input roots must be absolute paths")
    for name in ("claiming_reference", "cola_history", "di_rates", "di_nchs"):
        if name not in manifest.get("inputs", {}):
            raise ValueError(f"frozen manifest lacks required input: {name}")
    if "runtime" not in manifest.get("parameter_bundles", {}):
        raise ValueError(
            "frozen manifest lacks the effective runtime parameter bundle"
        )
    if mode == "registered":
        if protocol.get("rows") != list(FROZEN_ROWS):
            raise ValueError("registered matrix must contain exactly 68 rows")
        if protocol.get("headlines") != ["D×R0", "D×F0"]:
            raise ValueError("registered headlines differ")
        if protocol.get("floor_seeds") != list(range(5)) or (
            protocol.get("floor_fraction") != 0.5
        ):
            raise ValueError("registered half-split protocol differs")
        for key in ("reporting_template", "exposure_record", "forecasts"):
            record = protocol.get(key)
            if (
                not isinstance(record, dict)
                or file_record(Path(record["path"]), root=root) != record
            ):
                raise ValueError(f"missing or changed frozen {key}")
    else:
        if protocol.get("authorization") != "Max d513, 2026-09-28, item 7":
            raise ValueError(
                "structural check requires explicit authorization"
            )
        if protocol.get("permitted_outputs") != list(STRUCTURAL_OUTPUTS):
            raise ValueError(
                "structural check permits only frozen count outputs"
            )
        if any(key in protocol for key in ("rows", "benefits", "weights")):
            raise ValueError(
                "structural protocol cannot request outcome fields"
            )
    return PreflightRecord(
        head,
        SPECIFICATION_SHA256,
        registration_pointer,
        protocol_sha256,
        mode,
        json.dumps(manifest, sort_keys=True),
        str(root.resolve()),
        json.dumps(roots, sort_keys=True),
    )


def write_new(path: Path, artifact: Mapping[str, Any]) -> None:
    """Never replace an attempt, including a refusal (§10)."""
    with path.open("x", encoding="utf-8") as handle:
        json.dump(artifact, handle, indent=2, allow_nan=False)
        handle.write("\n")


def load_registered_inputs(registration: PreflightRecord):
    """Load only the frozen 2011 cohort, called after script preflight.

    Composes the same input constructors used by the legacy registered
    entry (scripts/run_fra68_registered.py:218–259), without its second
    population or a projection/benefit invocation.
    """
    from populace_dynamics.cohorts import psid2010
    from populace_dynamics.cola_track_a import (
        TrackAInputs,
        prepare_track_a_cohort,
    )
    from populace_dynamics.cola_track_a.config import TrackAConfig
    from populace_dynamics.cola_track_a.mortality import load_tr2008_mortality
    from populace_dynamics.cola_track_a.runner import (
        load_claiming_pmf,
        tr2008_baseline_cola,
        tr2008_ssa_parameters,
    )
    from populace_dynamics.engine.di_entitlement_rates import (
        load_di_entitlement_rates,
    )
    from populace_dynamics.estimates.parameters import load_cola_history
    from populace_dynamics.ss.params import load_ssa_parameters

    if (
        not registration.frozen_manifest_json
        or not registration.frozen_input_roots_json
    ):
        raise ValueError("input loading requires a fully frozen protocol")
    manifest = json.loads(registration.frozen_manifest_json)
    roots = json.loads(registration.frozen_input_roots_json)
    root = Path(registration.repository_root)

    def input_path(name):
        return root / manifest["inputs"][name]["path"]

    config = TrackAConfig(rows=tuple(f"R{i}" for i in range(6)))
    raw = psid2010.load_psid2010_inputs(
        anchor_wave=2011,
        data_dir=Path(roots["psid"]),
        claiming_reference_path=input_path("claiming_reference"),
    )
    source = psid2010.build_psid2010_cohort(
        raw, psid2010.Psid2010CohortSpec(anchor_wave=2011)
    )
    cohort = prepare_track_a_cohort(
        source, data_provenance="registered_real", config=config
    )
    baseline_parameters = load_ssa_parameters(Path(roots["policyengine_us"]))
    params = tr2008_ssa_parameters(
        baseline_parameters, alternative=config.tr2008_alternative
    )
    baseline = tr2008_baseline_cola(
        load_cola_history(path=input_path("cola_history")),
        first_year=config.tr2008_first_rate_year,
        last_year=config.reference_year,
        alternative=config.tr2008_alternative,
    )
    inputs = TrackAInputs(
        cohort=cohort,
        params=params,
        baseline=baseline,
        di_rates=load_di_entitlement_rates(
            config.di_spec,
            inputs_path=input_path("di_rates"),
            nchs_path=input_path("di_nchs"),
        ),
        population_mortality=load_tr2008_mortality(
            range(cohort.start_year + 1, config.reference_year + 1),
            alternative=config.tr2008_alternative,
            base_year=config.mortality_base_year,
        ),
        claiming_pmf=load_claiming_pmf(path=input_path("claiming_reference")),
        provenance={"psid_inputs": dict(raw.provenance)},
    )
    registration.validate_inputs(inputs)
    return inputs
