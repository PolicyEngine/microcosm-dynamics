#!/usr/bin/env bash
# Build the recorded Track U environment without reading PSID or running it.
# Source: runs/replication_boomers2004_uniform_cut_v1.env.json.
# The sidecar does not record SciPy: a supplemental version is opt-in only.
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_dir=$(cd -- "$script_dir/.." && pwd)
venv_dir=${NASI_REPRO_VENV_DIR:-/Users/maxghenis/PolicyEngine/microcosm-dynamics/.venv-nasi-repro}
sidecar=${NASI_REPRO_ENV_SIDECAR:-$repo_dir/runs/replication_boomers2004_uniform_cut_v1.env.json}
bootstrap_python=${NASI_REPRO_BOOTSTRAP_PYTHON:-python3}
scipy_version=${NASI_REPRO_SCIPY_VERSION:-}

usage() {
    cat <<'EOF'
Usage: make_nasi_repro_venv.sh [--venv-dir PATH] [--scipy-version VERSION]

Creates a NEW environment with the Python, NumPy, pandas, and project
versions recorded in the Track U sidecar, then verifies each exact version.
The project is installed editable with --no-deps; unrecorded dependencies
are not guessed. No cohort or outcome pipeline is run.

SciPy is absent from the recorded sidecar. --scipy-version supplies an
explicit supplemental pin; this does not establish its original version.
The build manifest labels the missing SciPy provenance and does not claim
that the complete original environment has been reproduced.

Environment overrides: NASI_REPRO_VENV_DIR, NASI_REPRO_SCIPY_VERSION,
NASI_REPRO_BOOTSTRAP_PYTHON, NASI_REPRO_ENV_SIDECAR. Standard uv cache and
Python installation directory overrides are also honored.
EOF
}

while (($#)); do
    case "$1" in
        --venv-dir|--scipy-version)
            if (($# < 2)) || [[ -z "$2" ]]; then
                printf 'Missing value for %s\n' "$1" >&2
                exit 2
            fi
            if [[ "$1" == --venv-dir ]]; then
                venv_dir=$2
            else
                scipy_version=$2
            fi
            shift 2
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            printf 'Unknown argument: %s\n' "$1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if [[ -e "$venv_dir" || -L "$venv_dir" ]]; then
    printf 'Refusing existing environment path: %s\n' "$venv_dir" >&2
    exit 1
fi
command -v uv >/dev/null || { printf 'uv is required\n' >&2; exit 1; }

# Validate first; printing only version pins prevents shell interpretation
# of sidecar strings. The optional SciPy version must be a numeric release.
pins=$("$bootstrap_python" - "$sidecar" "$scipy_version" <<'PY'
import json
import hashlib
import re
import sys
from pathlib import Path

source = Path(sys.argv[1])
source_bytes = source.read_bytes()
expected_sha256 = (
    "4041a19ada1cb4c05628cf31bf10cbfdb364bdd2d5d62455a3121143913e0ed9"
)
if hashlib.sha256(source_bytes).hexdigest() != expected_sha256:
    raise SystemExit("Refusing changed Track U environment sidecar")
sidecar = json.loads(source_bytes)
environment = sidecar["environment"]
packages = environment["packages"]
versions = [
    environment["python"],
    packages["numpy"],
    packages["pandas"],
    packages["policyengine-social-security-model"],
]
for version in versions + ([sys.argv[2]] if sys.argv[2] else []):
    if not isinstance(version, str) or not re.fullmatch(
        r"\d+\.\d+\.\d+", version
    ):
        raise SystemExit("Refusing malformed or non-exact version pin")
recorded_scipy = packages.get("scipy", "")
if recorded_scipy:
    if not re.fullmatch(r"\d+\.\d+\.\d+", recorded_scipy):
        raise SystemExit("Refusing malformed recorded SciPy pin")
    if sys.argv[2] and sys.argv[2] != recorded_scipy:
        raise SystemExit("Supplemental SciPy pin conflicts with sidecar")
print("\n".join(versions + [recorded_scipy or sys.argv[2]]))
PY
)
python_version=$(printf '%s\n' "$pins" | sed -n '1p')
numpy_version=$(printf '%s\n' "$pins" | sed -n '2p')
pandas_version=$(printf '%s\n' "$pins" | sed -n '3p')
project_version=$(printf '%s\n' "$pins" | sed -n '4p')
scipy_version=$(printf '%s\n' "$pins" | sed -n '5p')

uv venv --python "$python_version" "$venv_dir"
requirements=("numpy==$numpy_version" "pandas==$pandas_version")
if [[ -n "$scipy_version" ]]; then
    requirements+=("scipy==$scipy_version")
fi
uv pip install --python "$venv_dir/bin/python" "${requirements[@]}"
uv pip install --python "$venv_dir/bin/python" --no-deps --editable "$repo_dir"

"$venv_dir/bin/python" - "$sidecar" "$scipy_version" "$project_version" <<'PY'
import hashlib
import importlib.metadata
import json
import platform
import sys
from pathlib import Path

source = Path(sys.argv[1]).resolve()
source_bytes = source.read_bytes()
sidecar = json.loads(source_bytes)
recorded = sidecar["environment"]
expected = {
    "numpy": recorded["packages"]["numpy"],
    "pandas": recorded["packages"]["pandas"],
    "policyengine-social-security-model": sys.argv[3],
}
if sys.argv[2]:
    expected["scipy"] = sys.argv[2]
actual = {
    name: importlib.metadata.version(name) for name in sorted(expected)
}
if platform.python_version() != recorded["python"] or actual != expected:
    raise SystemExit("Refusing environment whose versions differ from pins")
recorded_scipy = recorded["packages"].get("scipy")
manifest = {
    "purpose": "environment build verification only; no pipeline run",
    "source_sidecar": str(source),
    "source_sidecar_sha256": hashlib.sha256(source_bytes).hexdigest(),
    "python": platform.python_version(),
    "packages": actual,
    "editable_project": True,
    "recorded_versions_verified": True,
    "complete_original_environment_reproduced": False,
    "scipy_pin_provenance": (
        "recorded sidecar" if recorded_scipy else
        "explicit supplemental pin; original version unrecorded"
        if sys.argv[2] else "not installed; original version unrecorded"
    ),
    "limitation": (
        "Only sidecar-recorded versions and an optional supplemental "
        "SciPy pin are installed; other project dependencies are not "
        "reconstructed from unrecorded versions."
    ),
}
destination = Path(sys.prefix) / "nasi_repro_build.json"
with destination.open("x", encoding="utf-8") as handle:
    json.dump(manifest, handle, indent=2, allow_nan=False)
    handle.write("\n")
print(json.dumps(manifest, indent=2, allow_nan=False))
PY
