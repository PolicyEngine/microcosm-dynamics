"""Fit gate_epuf_fill's four registered candidate fills on EPUF TRAIN.

Reads only the TRAIN part of the pinned EPUF
(``epuf_fill_gate.epuf_matrix(TRAIN)``) and fits, with the registered
parameters below:

- ``odd_forest`` (odd years, primary): :class:`BySexFill` of
  :class:`OddForestFill`;
- ``odd_knn`` (odd years, alternative): :class:`OddKnnFill`;
- ``pre_donor`` (pre-career years, primary): :class:`PreDonorFill`;
- ``pre_chain`` (pre-career years, alternative): :class:`PreChainFill`.

Each fill is written as a byte-reproducible ``.npz`` outside the repository
(``~/PolicyEngine/epuf-data/fills``, or ``POPULACE_DYNAMICS_EPUF_FILLS_DIR``),
as EPUF itself is. The manifest records each file's SHA-256, size and
parameters, the code commit, whether the fill code was clean, and the
library versions; ``epuf_fill_scoring`` loads the candidates by that
SHA-256. Usage::

    python scripts/fit_epuf_fills.py --manifest runs/epuf_fill_candidates_v1.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import os
import platform
import subprocess
import time
import zlib
from pathlib import Path

import numpy as np

from populace_dynamics.artifacts import write_new
from populace_dynamics.estimates import epuf_fill as F
from populace_dynamics.harness import epuf_fill_gate as g
from populace_dynamics.harness.epuf_operator import wage_base

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "populace_dynamics.epuf_fill_candidates.v1"
DEFAULT_DIR = Path("~/PolicyEngine/epuf-data/fills").expanduser()
CODE_FILES = (
    "src/populace_dynamics/estimates/epuf_fill.py",
    "src/populace_dynamics/harness/epuf_fill_gate.py",
    "src/populace_dynamics/harness/epuf_operator.py",
    "scripts/fit_epuf_fills.py",
)
ODD_UNIT_YEARS = tuple(range(1991, 2006))
PRE_UNIT_YEARS = tuple(range(1951, 2006))
#: The registered parameters of each candidate.
REGISTERED = {
    "odd_forest": {
        "family": "odd",
        "role": "primary",
        "params": {
            "unit_years": [ODD_UNIT_YEARS[0], ODD_UNIT_YEARS[-1]],
            "n_units": 3_000_000,
            "n_trees": 10,
            "min_leaf": 15,
            "max_features": 0.8,
            "seed": 0,
        },
    },
    "odd_knn": {
        "family": "odd",
        "role": "alternative",
        "params": {
            "unit_years": [ODD_UNIT_YEARS[0], ODD_UNIT_YEARS[-1]],
            "k": 10,
            "seed": 0,
        },
    },
    "pre_donor": {
        "family": "pre",
        "role": "primary",
        "params": {"k": 3, "bank_size": 100_000, "birth_years": [1905, 1985]},
    },
    "pre_chain": {
        "family": "pre",
        "role": "alternative",
        "params": {"unit_years": [PRE_UNIT_YEARS[0], PRE_UNIT_YEARS[-1]]},
    },
}


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _clean() -> bool:
    return (
        subprocess.run(
            ["git", "-C", str(ROOT), "diff", "--quiet", "HEAD", "--"]
            + list(CODE_FILES),
            check=False,
        ).returncode
        == 0
    )


def fit(name: str, shares, birth, sex, person_id):
    params = REGISTERED[name]["params"]
    if name == "odd_forest":
        return F.BySexFill.fit(
            F.OddForestFill,
            shares,
            g.YEARS,
            birth,
            sex,
            ODD_UNIT_YEARS,
            person_id,
            n_units=params["n_units"],
            n_trees=params["n_trees"],
            min_leaf=params["min_leaf"],
            max_features=params["max_features"],
            seed=params["seed"],
        )
    if name == "odd_knn":
        return F.OddKnnFill.fit(
            shares,
            np.asarray(g.YEARS),
            birth,
            sex,
            ODD_UNIT_YEARS,
            k=params["k"],
            seed=params["seed"],
        )
    if name == "pre_donor":
        return F.PreDonorFill.fit(
            shares,
            np.asarray(g.YEARS),
            birth,
            sex,
            person_id,
            k=params["k"],
            birth_years=tuple(params["birth_years"]),
            bank_size=params["bank_size"],
        )
    if name == "pre_chain":
        return F.PreChainFill.fit(
            shares, np.asarray(g.YEARS), birth, sex, PRE_UNIT_YEARS
        )
    raise ValueError(name)


def main() -> None:
    import scipy
    import sklearn

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path(
            os.environ.get("POPULACE_DYNAMICS_EPUF_FILLS_DIR", DEFAULT_DIR)
        ),
    )
    parser.add_argument("--only", nargs="*", default=sorted(REGISTERED))
    args = parser.parse_args()
    if args.manifest.exists():
        raise FileExistsError(
            f"{args.manifest} exists; a registered manifest is never refitted "
            "in place"
        )
    started = time.time()
    built_at = dt.datetime.now(dt.UTC).isoformat(timespec="seconds")
    matrix = g.epuf_matrix(g.TRAIN)
    caps = np.array([float(wage_base(year)) for year in g.YEARS])
    shares = matrix.earnings / caps[None, :]
    args.out_dir.mkdir(parents=True, exist_ok=True)
    fills = {}
    for name in args.only:
        t = time.time()
        fill, diagnostics = fit(
            name, shares, matrix.birth_year, matrix.sex, matrix.person_id
        )
        blob = fill.to_bytes()
        path = args.out_dir / f"{name}_v1.npz"
        if path.exists():
            # A staged file is never replaced: a refit must reproduce it.
            if path.read_bytes() != blob:
                raise FileExistsError(
                    f"{path} exists with other bytes; refusing to replace it"
                )
        else:
            with path.open("xb") as handle:
                handle.write(blob)
        fills[name] = {
            **REGISTERED[name],
            "file": path.name,
            "sha256": hashlib.sha256(blob).hexdigest(),
            "bytes": len(blob),
            "fit_seconds": round(time.time() - t, 1),
            "diagnostics": _jsonable(diagnostics),
        }
        print(f"{name}: {fills[name]['sha256']} {len(blob)} bytes", flush=True)
    document = {
        "schema": SCHEMA,
        "registration_id": g.REGISTRATION_ID,
        "code_commit": _git("rev-parse", "HEAD"),
        "code_files_clean": _clean(),
        "built_at_utc": built_at,
        "part": "train",
        "n_persons": int(len(matrix.birth_year)),
        "versions": {
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "scikit_learn": sklearn.__version__,
            "python": platform.python_version(),
            "zlib_runtime": zlib.ZLIB_RUNTIME_VERSION,
            "platform": platform.platform(),
        },
        "staging": "files live outside the repository, like EPUF; a refit "
        "with this script at code_commit, on the same library, zlib and "
        "platform versions, reproduces their bytes",
        "fills": fills,
        "elapsed_seconds": round(time.time() - started, 1),
    }
    write_new(args.manifest, document, sidecar=True)


def _jsonable(value):
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_jsonable(v) for v in value]
    if isinstance(value, np.ndarray):
        return _jsonable(value.tolist())
    if isinstance(value, float | np.floating):
        return float(value) if np.isfinite(value) else str(float(value))
    if isinstance(value, np.integer):
        return int(value)
    return value


if __name__ == "__main__":
    main()
