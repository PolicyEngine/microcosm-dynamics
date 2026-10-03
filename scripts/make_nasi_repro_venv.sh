#!/usr/bin/env bash
# Build only the reproduction environment; never run a PSID pipeline.
# Pins are read from the bound exercise-1/3 model sidecars, not guessed.
set -euo pipefail

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
default_checkout=/Users/maxghenis/PolicyEngine/microcosm-dynamics
target_dir="$default_checkout/.venv-nasi-repro"
source_python="$default_checkout/.venv/bin/python"

usage() {
    cat <<'EOF'
Usage: scripts/make_nasi_repro_venv.sh [--target-dir PATH] [--source-python PATH]

Defaults to the main checkout's .venv-nasi-repro. --target-dir supports a
restricted-workspace build verification. Existing environments are refused.
The script checks both frozen sidecars, installs their exact Python/numpy/
pandas/scipy versions and this checkout editable, then verifies those versions.
No microdata or projected outcome is read or computed.
EOF
}

while (($#)); do
    case "$1" in
        --target-dir|--source-python)
            if (($# < 2)); then
                usage >&2
                exit 2
            fi
            if [[ "$1" == --target-dir ]]; then
                target_dir=$2
            else
                source_python=$2
            fi
            shift 2
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            usage >&2
            exit 2
            ;;
    esac
done

if [[ -e "$target_dir" ]]; then
    printf 'Refusing existing environment: %s\n' "$target_dir" >&2
    exit 1
fi
command -v uv >/dev/null
scratch_dir=$(mktemp -d "${TMPDIR:-/tmp}/nasi-repro.XXXXXX")
trap 'rm -rf -- "$scratch_dir"' EXIT
# uv's user cache and Python install directories are outside a worktree's
# write sandbox. Keep downloads in the assigned temporary directory.
export UV_CACHE_DIR="$scratch_dir/uv-cache"
export UV_PYTHON_INSTALL_DIR="$scratch_dir/uv-python"

"$source_python" - "$repo_root" "$scratch_dir" <<'PY'
import hashlib
import json
import platform
import sys
from pathlib import Path

root, scratch = map(Path, sys.argv[1:])
pins = {
    "cola": "270acf292682b8111133f9047f366c93173e713bc422cb7e108bd064ac33d53e",
    "fra68": "9c768fff17bfd828d16bdca738f92d8487f082ec99cd94ee0c73959bb050746e",
}
environment_pins = {
    "cola": "a79b54ec5d3aadaacee41e8877e5a985821fbd3bba82b97fe8fa962d8aa8e6f9",
    "fra68": "8c04da45818cc88ece6693b12fd630b624c3c8d6843829ed92dec258af81fab6",
}
environments = []
for exercise, expected_digest in pins.items():
    artifact = root / "runs" / f"replication_urban2010_{exercise}_v1.json"
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    sidecar_path = artifact.with_suffix(".env.json")
    if hashlib.sha256(sidecar_path.read_bytes()).hexdigest() != environment_pins[exercise]:
        raise SystemExit(f"{exercise}: environment sidecar SHA-256 differs")
    sidecar = json.loads(sidecar_path.read_text())
    if digest != expected_digest or sidecar["artifact_sha256"] != digest:
        raise SystemExit(f"{exercise}: parent/sidecar binding differs")
    if sidecar["artifact"] != artifact.name:
        raise SystemExit(f"{exercise}: sidecar names a different artifact")
    environment = sidecar["environment"]
    versions = {"python": environment["python"]}
    for package in ("numpy", "pandas", "scipy"):
        version = environment["packages"].get(package)
        if not version:
            raise SystemExit(f"{exercise}: missing {package} version")
        versions[package] = version
    environments.append(versions)
if environments[0] != environments[1]:
    raise SystemExit("Exercise-1 and exercise-3 environments differ")
versions = environments[0]
if platform.python_version() != versions["python"]:
    raise SystemExit("--source-python must match the exact recorded Python")
(scratch / "versions.json").write_text(json.dumps(versions))
(scratch / "requirements.txt").write_text(
    "".join(f"{key}=={versions[key]}\n" for key in ("numpy", "pandas", "scipy"))
)
print("Recorded versions: " + json.dumps(versions, sort_keys=True))
PY

# Reuse the exact interpreter already on the host rather than making the
# resulting environment depend on a temporary downloaded Python tree.
uv venv --python "$source_python" "$target_dir"
uv pip install --python "$target_dir/bin/python" \
    --requirements "$scratch_dir/requirements.txt" --editable "$repo_root"
"$target_dir/bin/python" - "$scratch_dir/versions.json" "$repo_root" <<'PY'
import importlib.metadata
import json
import platform
import sys
from pathlib import Path

expected = json.loads(Path(sys.argv[1]).read_text())
actual = {"python": platform.python_version()}
for package in ("numpy", "pandas", "scipy"):
    actual[package] = importlib.metadata.version(package)
if actual != expected:
    raise SystemExit(f"Version verification failed: {actual!r} != {expected!r}")
import populace_dynamics

source = Path(populace_dynamics.__file__).resolve()
if not source.is_relative_to(Path(sys.argv[2]) / "src"):
    raise SystemExit(f"Editable install points outside assigned source: {source}")
print("Verified exact recorded versions and assigned editable source")
PY

parameter_checkout="$default_checkout/.claude/pe-us-a03e82e503"
if [[ ! -d "$parameter_checkout" ]]; then
    printf 'Missing existing parameter checkout: %s\n' "$parameter_checkout" >&2
    exit 1
fi
parameter_revision=$(git -C "$parameter_checkout" rev-parse HEAD)
if [[ "$parameter_revision" != a03e82e503* ]]; then
    printf 'Parameter checkout revision differs: %s\n' "$parameter_revision" >&2
    exit 1
fi
printf 'Built %s\n' "$target_dir"
printf 'export POPULACE_DYNAMICS_PE_US_DIR=%q\n' "$parameter_checkout"
printf 'Use %s/bin/python only after a new issue #42 registration.\n' "$target_dir"
