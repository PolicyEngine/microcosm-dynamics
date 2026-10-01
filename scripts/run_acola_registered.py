"""Registration 18: guarded one-shot A-COLA run; report-only."""

from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from populace_dynamics.acola_track.config import (  # noqa: E402
    REGISTRATION_POINTER,
    SPECIFICATION_PATH,
    ACOLAConfig,
    check_specification,
)
from populace_dynamics.acola_track.runner import run_acola  # noqa: E402
from populace_dynamics.cohorts import psid2010  # noqa: E402
from populace_dynamics.cola_track_a import (  # noqa: E402
    TrackAInputs,
    prepare_track_a_cohort,
)
from populace_dynamics.cola_track_a.mortality import (  # noqa: E402
    load_tr2008_mortality,
)
from populace_dynamics.cola_track_a.runner import (  # noqa: E402
    A1_SPECIFICATION_PATH,
    load_claiming_pmf,
    tr2008_baseline_cola,
    tr2008_ssa_parameters,
)
from populace_dynamics.cola_track_a.statutory import (  # noqa: E402
    CAPTURE_PATH,
    CAPTURE_SHA256,
)
from populace_dynamics.data import tr2008  # noqa: E402
from populace_dynamics.engine.di_entitlement_rates import (  # noqa: E402
    load_di_entitlement_rates,
)
from populace_dynamics.estimates.parameters import (  # noqa: E402
    load_cola_history,
)
from populace_dynamics.ss.params import load_ssa_parameters  # noqa: E402

REGISTERED_HEADER = (
    "REGISTERED ONE-SHOT RUN - A-COLA, Registration 18, 2030. "
    "Python oracle benefits: not Axiom. Report-only. "
    "Publishes regardless of outcome."
)
DEFAULT_OUTPUT = ROOT / "runs" / "trust_fund_acola_2030_v1.json"
_POINTER_PATTERN = re.compile(
    r"https://github\.com/PolicyEngine/microcosm-dynamics/issues/42"
    r"#issuecomment-[0-9]+"
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _script_module(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(
        "_acola_" + name, ROOT / "scripts" / (name + ".py")
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def preflight(
    *,
    registration_pointer: str,
    registered_commit: str,
    output: Path,
    git: Any = _git,
    specification_path: Path = SPECIFICATION_PATH,
    config: ACOLAConfig | None = None,
) -> dict[str, str]:
    """Read git and the committed specification; load no population data."""

    if not _POINTER_PATTERN.fullmatch(registration_pointer):
        raise ValueError(
            "the registration pointer must be an issue #42 comment URL"
        )
    if registration_pointer != REGISTRATION_POINTER:
        raise ValueError(
            "the pointer must be Registration 18's exact comment URL"
        )
    if not re.fullmatch(r"[0-9a-f]{40}", registered_commit):
        raise ValueError("--registered-commit must be a full 40-hex SHA")
    head = git("rev-parse", "HEAD")
    if head != registered_commit:
        raise ValueError(
            f"HEAD {head} is not the registered commit {registered_commit}"
        )
    if git("status", "--porcelain") != "":
        raise ValueError("the working tree must be clean for a registered run")
    configuration = config or ACOLAConfig()
    configuration.check_runnable()
    configuration.check_registered()
    binding = check_specification(specification_path)
    output = Path(output)
    if output.resolve() != DEFAULT_OUTPUT.resolve():
        raise ValueError("output must be the fixed registered artifact path")
    if output.exists() or output.with_suffix(".env.json").exists():
        raise ValueError(
            f"{output} already exists: the registered run is one-shot"
        )
    return {"head": head, "specification_sha256": binding["sha256"]}


def _write_new(path: Path, text: str) -> None:
    """Create a file exclusively, retaining the template's one-shot guard."""

    with Path(path).open("x", encoding="utf-8") as handle:
        handle.write(text)


def write_artifact(
    output: Path, artifact: dict[str, Any], environment: dict[str, Any]
) -> None:
    """Serialize the complete result and its hash-bound environment sidecar."""

    content = json.dumps(artifact, indent=2, allow_nan=False) + "\n"
    sidecar = (
        json.dumps(
            {
                "artifact": output.name,
                "artifact_sha256": hashlib.sha256(
                    content.encode()
                ).hexdigest(),
                "environment": environment,
            },
            indent=2,
            allow_nan=False,
        )
        + "\n"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    _write_new(output, content)
    _write_new(output.with_suffix(".env.json"), sidecar)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registration-pointer", required=True)
    parser.add_argument("--registered-commit", required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    config = ACOLAConfig()
    state = preflight(
        registration_pointer=args.registration_pointer,
        registered_commit=args.registered_commit,
        output=args.output,
        config=config,
    )
    track_config = config.track_a_config()
    claiming_pmf = load_claiming_pmf()
    raw = psid2010.load_psid2010_inputs(anchor_wave=2011)
    a3 = psid2010.build_psid2010_cohort(
        raw, psid2010.Psid2010CohortSpec(anchor_wave=2011)
    )
    cohort = prepare_track_a_cohort(
        a3, data_provenance="registered_real", config=track_config
    )
    base_params = load_ssa_parameters()
    params = tr2008_ssa_parameters(
        base_params, alternative=track_config.tr2008_alternative
    )
    environment = _script_module("run_track_a_registered")._environment(
        ssa_parameters_revision=base_params.pe_us_revision
    )
    realized = load_cola_history()
    baseline = tr2008_baseline_cola(
        realized,
        first_year=track_config.tr2008_first_rate_year,
        last_year=track_config.reference_year,
        alternative=track_config.tr2008_alternative,
    )
    rate_check = _script_module("track_a_dry_run")._spec_rate_check(baseline)
    di_rates = load_di_entitlement_rates(track_config.di_spec)
    mortality = load_tr2008_mortality(
        range(2011, track_config.reference_year + 1),
        alternative=track_config.tr2008_alternative,
        base_year=track_config.mortality_base_year,
    )
    provenance = {
        "ssa_parameters": params.pe_us_revision,
        "statutory_capture": {
            "path": str(CAPTURE_PATH.relative_to(ROOT)),
            "sha256": CAPTURE_SHA256,
        },
        "tr2008_file_sha256": dict(tr2008.FILE_SHA256),
        "di_rates": {
            key: value
            for key, value in di_rates.provenance.items()
            if key.endswith("sha256")
        },
        "cola_history_sha256": realized.provenance["sha256"],
        "claiming_reference_sha256": _sha256(psid2010.CLAIMING_REFERENCE_PATH),
        "a1_specification_sha256": _sha256(A1_SPECIFICATION_PATH),
        "acola_specification_sha256": state["specification_sha256"],
        "mortality": dict(mortality.provenance),
        "psid_inputs": {"2011": dict(raw.provenance)},
    }
    result = run_acola(
        TrackAInputs(
            cohort=cohort,
            params=params,
            baseline=baseline,
            di_rates=di_rates,
            population_mortality=mortality,
            claiming_pmf=claiming_pmf,
            provenance=provenance,
        ),
        config=config,
        registration_pointer=args.registration_pointer,
        progress=lambda message: print(message, file=sys.stderr),
        check_committed_parameters=True,
    )
    artifact = {
        "header": REGISTERED_HEADER,
        **result,
        "checks": {"a1_rate_path": rate_check, "acola_binding": state},
        "run": {
            "started": started,
            "finished": datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat(),
            "registration_pointer": args.registration_pointer,
            "registered_commit": args.registered_commit,
            "git_head": state["head"],
            "git_clean": True,
            "command": " ".join(
                [
                    "python",
                    "scripts/run_acola_registered.py",
                    *(sys.argv[1:] if argv is None else argv),
                ]
            ),
        },
    }
    write_artifact(args.output, artifact, environment)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
