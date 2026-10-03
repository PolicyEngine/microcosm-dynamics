#!/usr/bin/env bash
# Build only the recorded environment; never read PSID or run a pipeline.
# Projection exercises pin Python 3.14.4; observational exercises 3.14.7.
# Track U did not record SciPy: an explicit supplemental pin is opt-in.
set -euo pipefail

repo_root=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
main_checkout=/Users/maxghenis/PolicyEngine/microcosm-dynamics
target_dir=${NASI_REPRO_VENV_DIR:-${NASI_REPRO_VENV:-$main_checkout/.venv-nasi-repro}}
source_python=${NASI_REPRO_BOOTSTRAP_PYTHON:-$main_checkout/.venv/bin/python}
scipy_version=${NASI_REPRO_SCIPY_VERSION:-}
exercise=cola
check_only=0

usage() {
    cat <<'EOF'
Usage: scripts/make_nasi_repro_venv.sh [--exercise EXERCISE]
       [--target-dir PATH|--venv-dir PATH] [--source-python PATH]
       [--scipy-version VERSION] [--check-only]

EXERCISE is cola (default), fra68, uniform-cut, or min-benefit. All four
pinned artifact/sidecar bindings are checked before selecting one exercise's
exact recorded versions. Existing environment paths are refused.
--check-only checks pins without building an environment or reading PSID.

One environment cannot match both recorded Python versions. Track U's
original SciPy version is unrecorded; --scipy-version is supplemental only.
The editable project uses --no-deps to avoid guessing unrecorded dependencies.
Standard UV_CACHE_DIR and UV_PYTHON_INSTALL_DIR overrides are honored.
EOF
}

while (($#)); do
    case "$1" in
        --exercise|--target-dir|--venv-dir|--source-python|--scipy-version)
            if (($# < 2)) || [[ -z "$2" ]]; then usage >&2; exit 2; fi
            case "$1" in
                --exercise) exercise=$2 ;;
                --target-dir|--venv-dir) target_dir=$2 ;;
                --source-python) source_python=$2 ;;
                --scipy-version) scipy_version=$2 ;;
            esac
            shift 2 ;;
        --check-only) check_only=1; shift ;;
        --help|-h) usage; exit 0 ;;
        *) usage >&2; exit 2 ;;
    esac
done
if [[ -e "$target_dir" || -L "$target_dir" ]] && ((check_only == 0)); then
    printf 'Refusing existing environment: %s\n' "$target_dir" >&2
    exit 1
fi
scratch_dir=$(mktemp -d "${TMPDIR:-/tmp}/nasi-repro.XXXXXX")
trap 'rm -rf -- "$scratch_dir"' EXIT

"$source_python" - "$repo_root" "$scratch_dir" "$exercise" "$scipy_version" <<'PY'
import hashlib
import json
import re
import sys
from pathlib import Path

root, scratch = map(Path, sys.argv[1:3])
exercise, supplemental_scipy = sys.argv[3:]
pins = {
    "cola": (
        "replication_urban2010_cola_v1",
        "270acf292682b8111133f9047f366c93173e713bc422cb7e108bd064ac33d53e",
        "a79b54ec5d3aadaacee41e8877e5a985821fbd3bba82b97fe8fa962d8aa8e6f9",
    ),
    "fra68": (
        "replication_urban2010_fra68_v1",
        "9c768fff17bfd828d16bdca738f92d8487f082ec99cd94ee0c73959bb050746e",
        "8c04da45818cc88ece6693b12fd630b624c3c8d6843829ed92dec258af81fab6",
    ),
    "uniform-cut": (
        "replication_boomers2004_uniform_cut_v1",
        "48fb6cb108b09e19ed10c32586bd1b0d9521ec7746f693ba0241963ac24a4de3",
        "4041a19ada1cb4c05628cf31bf10cbfdb364bdd2d5d62455a3121143913e0ed9",
    ),
    "min-benefit": (
        "replication_urban2006_minimum_benefit_v1",
        "b2c2806254618bc8c4cf6c20e652ec2a06ce8a7c05de01a82c151a5d7921cafc",
        "e40f10bb025734a7dfa91476a851d06efeffa9fe7ab24adaff3dc22f0c9f7107",
    ),
}
if exercise not in pins:
    raise SystemExit("Unknown exercise; use cola, fra68, uniform-cut, min-benefit")
if supplemental_scipy and not re.fullmatch(r"\d+\.\d+\.\d+", supplemental_scipy):
    raise SystemExit("Supplemental SciPy version must be an exact numeric release")
environments, bindings = {}, {}
for name, (stem, artifact_pin, sidecar_pin) in pins.items():
    artifact = root / "runs" / f"{stem}.json"
    sidecar_path = artifact.with_suffix(".env.json")
    # Hash only model artifact bytes; parse version metadata only.
    if hashlib.sha256(artifact.read_bytes()).hexdigest() != artifact_pin:
        raise SystemExit(f"{name}: parent artifact SHA-256 differs")
    raw = sidecar_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != sidecar_pin:
        raise SystemExit(f"{name}: environment sidecar SHA-256 differs")
    sidecar = json.loads(raw)
    if sidecar["artifact"] != artifact.name or sidecar["artifact_sha256"] != artifact_pin:
        raise SystemExit(f"{name}: sidecar does not bind its parent artifact")
    environments[name] = sidecar["environment"]
    bindings[name] = {"sidecar": str(sidecar_path), "sha256": sidecar_pin}
recorded = environments[exercise]
versions = {"python": recorded["python"]}
for package in ("numpy", "pandas", "scipy", "policyengine-social-security-model"):
    version = recorded["packages"].get(package)
    if version is not None:
        versions[package] = version
if "scipy" in versions:
    if supplemental_scipy and versions["scipy"] != supplemental_scipy:
        raise SystemExit("Supplemental SciPy pin conflicts with recorded version")
    scipy_provenance = "recorded sidecar"
elif supplemental_scipy:
    versions["scipy"] = supplemental_scipy
    scipy_provenance = "explicit supplemental pin; original version unrecorded"
else:
    scipy_provenance = "original version unrecorded; not installed"
for version in versions.values():
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise SystemExit("Refusing malformed or non-exact version pin")
manifest = {
    "purpose": "environment build verification only; no pipeline run",
    "exercise": exercise,
    "source_sidecars": bindings,
    "versions": versions,
    "scipy_pin_provenance": scipy_provenance,
    "complete_original_environment_reproduced": False,
    "recorded_core_versions_complete": exercise != "uniform-cut",
    "gil_disabled": False,
    "parameter_revision": "a03e82e503",
}
(scratch / "pins.json").write_text(json.dumps(manifest, indent=2) + "\n")
(scratch / "python-version").write_text(versions["python"])
(scratch / "requirements.txt").write_text("".join(
    f"{name}=={versions[name]}\n"
    for name in ("numpy", "pandas", "scipy") if name in versions
))
print(json.dumps(manifest, sort_keys=True))
PY
if ((check_only)); then exit 0; fi
command -v uv >/dev/null
PYTHON_VERSION=$(cat "$scratch_dir/python-version")
# Keep any downloaded interpreter alive after scratch cleanup, next to the
# requested venv. Respect existing standard uv-directory overrides.
export UV_CACHE_DIR=${UV_CACHE_DIR:-$scratch_dir/uv-cache}
export UV_PYTHON_INSTALL_DIR=${UV_PYTHON_INSTALL_DIR:-${target_dir}.python}
uv venv --python "${PYTHON_VERSION}+gil" "$target_dir"
uv pip install --python "$target_dir/bin/python" --requirements "$scratch_dir/requirements.txt"
uv pip install --python "$target_dir/bin/python" --no-deps --editable "$repo_root"
"$target_dir/bin/python" - "$scratch_dir/pins.json" "$repo_root" <<'PY'
import importlib.metadata
import json
import platform
import sys
import sysconfig
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text())
expected = manifest["versions"]
actual = {"python": platform.python_version()}
for package in expected:
    if package != "python":
        actual[package] = importlib.metadata.version(package)
if actual != expected or bool(sysconfig.get_config_var("Py_GIL_DISABLED")):
    raise SystemExit("Environment differs from exact recorded GIL-build versions")
import populace_dynamics

source = Path(populace_dynamics.__file__).resolve()
if not source.is_relative_to(Path(sys.argv[2]).resolve() / "src"):
    raise SystemExit("Editable install points outside assigned source")
manifest["recorded_versions_verified"] = True
manifest["editable_source"] = str(source)
(Path(sys.prefix) / "nasi-reproduction-environment.json").write_text(
    json.dumps(manifest, indent=2) + "\n"
)
print("Verified exact recorded versions, GIL build and assigned editable source")
PY
parameter_checkout=${PE_US_DIR:-$main_checkout/.claude/pe-us-a03e82e503}
if [[ ! -d "$parameter_checkout" ]]; then
    printf 'Missing existing parameter checkout: %s\n' "$parameter_checkout" >&2
    exit 1
fi
parameter_revision=$(git -C "$parameter_checkout" rev-parse HEAD)
if [[ ! "$parameter_revision" =~ ^a03e82e503[0-9a-f]{30}$ ]]; then
    printf 'Parameter checkout revision differs: %s\n' "$parameter_revision" >&2
    exit 1
fi
if [[ -n "$(git -C "$parameter_checkout" status --porcelain --untracked-files=no)" ]]; then
    printf 'Parameter checkout has changed tracked files\n' >&2
    exit 1
fi
printf 'Built %s for %s\n' "$target_dir" "$exercise"
printf 'export POPULACE_DYNAMICS_PE_US_DIR=%q\n' "$parameter_checkout"
printf 'Use only after a new issue #42 registration.\n'
