#!/usr/bin/env bash
# Build the environment a bit-for-bit reproduction of a committed blind-test
# run needs (NASI follow-ups, 2026-10-01; package G4c).
#
# The group-breakdown adapters (src/populace_dynamics/group_breakdowns/)
# re-execute a committed registered run and refuse unless every recomputed
# cell equals the committed artifact exactly, floats bit for bit.  Design
# standard errors go through numpy, so the reproduction needs the Python,
# numpy, pandas and scipy versions the committed run's .env.json sidecar
# records.  This script creates
#
#     <main checkout>/.venv-nasi-repro
#
# with uv at exactly those versions (the default, GIL-enabled CPython build:
# a free-threaded 3.14t interpreter takes other numpy, pandas and scipy
# wheels, so uv is asked for "+gil" and the build is checked), installs this
# repository editable
# (its other dependencies resolved under those pins) plus pytest and
# hypothesis, and then checks every pinned version against the sidecar.
# It reads no PSID file and runs no pipeline.
#
# The versions below are exercise 4's (Track M) sidecar,
# runs/replication_urban2006_minimum_benefit_v1.env.json;
# tests/group_breakdowns/test_min_benefit_parent_artifact.py holds them
# equal to it.  A reproduction also needs, outside this venv:
#   * the staged PSID files the committed artifact records by SHA-256
#     (inputs.source.psid_files_sha256), under POPULACE_DYNAMICS_PSID_DIR
#     or ~/PolicyEngine/psid-data;
#   * policyengine-us at revision a03e82e503, read as a git checkout by
#     populace_dynamics.ss.params (not installed): set
#     POPULACE_DYNAMICS_PE_US_DIR to it.  This script checks the checkout
#     named by PE_US_DIR (default below) when it exists and never creates
#     it.
#
# Usage:
#     scripts/make_nasi_repro_venv.sh [--force]
#
# --force rebuilds the venv even when it already matches.  Environment
# overrides: NASI_REPRO_VENV (venv path), PE_US_DIR (checkout to check).
set -euo pipefail

PYTHON_VERSION="3.14.7"
NUMPY_VERSION="2.5.3"
PANDAS_VERSION="3.0.6"
SCIPY_VERSION="1.18.1"
PE_US_REVISION="a03e82e503"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "${SCRIPT_DIR}/.." && pwd)"
# The main checkout: the first entry of `git worktree list` (a worktree's
# own path otherwise).  The venv and the policyengine-us checkout live
# beside the main checkout's .venv, shared by every worktree.
MAIN="$(git -C "${REPO}" worktree list --porcelain | awk 'NR==1 {print $2}')"
VENV="${NASI_REPRO_VENV:-${MAIN}/.venv-nasi-repro}"
PE_US_DIR="${PE_US_DIR:-${MAIN}/.claude/pe-us-a03e82e503}"
SIDECAR="${REPO}/runs/replication_urban2006_minimum_benefit_v1.env.json"

FORCE=0
for arg in "$@"; do
    case "${arg}" in
        --force) FORCE=1 ;;
        *)
            echo "unknown argument ${arg} (usage: $0 [--force])" >&2
            exit 2
            ;;
    esac
done

command -v uv >/dev/null 2>&1 || {
    echo "uv is required (https://docs.astral.sh/uv/)" >&2
    exit 1
}

# Print each pinned version the venv's interpreter sees, one per line.
installed() {
    "${VENV}/bin/python" - <<'PY'
import platform
import sysconfig
from importlib.metadata import version

print("python", platform.python_version())
print("gil_disabled", int(sysconfig.get_config_var("Py_GIL_DISABLED") or 0))
for name in ("numpy", "pandas", "scipy"):
    print(name, version(name))
PY
}

expected() {
    printf 'python %s\ngil_disabled 0\nnumpy %s\npandas %s\nscipy %s\n' \
        "${PYTHON_VERSION}" "${NUMPY_VERSION}" "${PANDAS_VERSION}" \
        "${SCIPY_VERSION}"
}

if [[ -x "${VENV}/bin/python" && "${FORCE}" -eq 0 ]] \
    && [[ "$(installed 2>/dev/null || true)" == "$(expected)" ]]; then
    echo "${VENV} already holds the pinned versions; --force rebuilds it"
else
    uv venv --clear --python "${PYTHON_VERSION}+gil" "${VENV}"
    CONSTRAINTS="$(mktemp)"
    trap 'rm -f "${CONSTRAINTS}"' EXIT
    printf 'numpy==%s\npandas==%s\nscipy==%s\n' \
        "${NUMPY_VERSION}" "${PANDAS_VERSION}" "${SCIPY_VERSION}" \
        >"${CONSTRAINTS}"
    uv pip install --python "${VENV}/bin/python" \
        --constraint "${CONSTRAINTS}" \
        "numpy==${NUMPY_VERSION}" \
        "pandas==${PANDAS_VERSION}" \
        "scipy==${SCIPY_VERSION}" \
        --editable "${REPO}" \
        pytest hypothesis
fi

# The venv's versions must equal the pins, and the pins the sidecar's.
if [[ "$(installed)" != "$(expected)" ]]; then
    echo "the venv's versions differ from the pins:" >&2
    installed >&2
    exit 1
fi
"${VENV}/bin/python" - "${SIDECAR}" "${PYTHON_VERSION}" "${NUMPY_VERSION}" \
    "${PANDAS_VERSION}" "${SCIPY_VERSION}" "${PE_US_REVISION}" <<'PY'
import json
import sys

sidecar, python, numpy, pandas, scipy, revision = sys.argv[1:]
environment = json.load(open(sidecar, encoding="utf-8"))["environment"]
recorded = {
    "python": environment["python"],
    "numpy": environment["packages"]["numpy"],
    "pandas": environment["packages"]["pandas"],
    "scipy": environment["packages"]["scipy"],
    "policyengine-us": environment["policyengine_us_parameters"]["revision"],
}
pinned = {
    "python": python,
    "numpy": numpy,
    "pandas": pandas,
    "scipy": scipy,
    "policyengine-us": revision,
}
if recorded != pinned:
    sys.exit(f"the pins {pinned} are not the sidecar's {recorded}")
print("pins equal the sidecar:", json.dumps(recorded, sort_keys=True))
import platform

# Recorded, not compared (the registered scripts compare the same fields).
print("platform: sidecar", environment["platform"], "| venv", platform.platform())
PY

# The editable install must import this repository's source.
"${VENV}/bin/python" - "${REPO}" <<'PY'
import sys
from pathlib import Path

import populace_dynamics

source = Path(populace_dynamics.__file__).resolve()
repo = Path(sys.argv[1]).resolve()
print("populace_dynamics from", source)
if not source.is_relative_to(repo):
    print(
        f"note: populace_dynamics resolves outside {repo}; the registered "
        "scripts put this checkout's src first on sys.path"
    )
PY

if [[ -d "${PE_US_DIR}/.git" || -f "${PE_US_DIR}/.git" ]]; then
    head="$(git -C "${PE_US_DIR}" rev-parse HEAD)"
    if [[ "${head}" != "${PE_US_REVISION}"* ]]; then
        echo "${PE_US_DIR} is at ${head}, not ${PE_US_REVISION}" >&2
        exit 1
    fi
    echo "policyengine-us checkout ${PE_US_DIR} is at ${head}"
else
    echo "note: no policyengine-us checkout at ${PE_US_DIR}; a" \
        "reproduction needs one at ${PE_US_REVISION}"
fi

cat <<EOF
Built ${VENV}.  A reproduction runs with:
    POPULACE_DYNAMICS_PE_US_DIR=${PE_US_DIR} \\
        ${VENV}/bin/python scripts/run_min_benefit_groups_registered.py ...
(only under its own issue #42 registration; see that script's docstring).
EOF
