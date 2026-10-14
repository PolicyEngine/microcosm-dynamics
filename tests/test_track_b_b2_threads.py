"""Candidate 3's real fit and selector loop on invented data, run twice.

Each probe starts a fresh interpreter with B2's registered thread settings
(``b2.thread_settings``: one BLAS, OpenMP and numexpr thread, PASSIVE) and
its own ``PYTHONHASHSEED``. It fits the default (unstubbed) law and projects
every registered draw seed.

Invariant: the fitted law and its projections are a function of the data
and the registered seeds alone. Two processes with different hash seeds
must give byte-identical projected frames, identical gate probability
surfaces, and an equal whole fitted state, field by field.

B2 runs one thread per process because, in its pinned environment, the
projection loop hangs in the participation gates'
``HistGradientBoostingClassifier.predict_proba`` with more than one OpenMP
thread (see ``b2.thread_settings``), so no multi-threaded run is compared.
Field by field, the only thread-dependent state is the thread count that
``HistGradientBoostingClassifier`` records on its bin mapper
(``_BinMapper.n_threads``). ``state_digest`` leaves it out and returns its
values, and the probe records them.
"""

from __future__ import annotations

import hashlib
import json
import os
import pickle
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]

#: The one field allowed to differ: the thread count a
#: ``HistGradientBoostingClassifier`` records on its bin mapper.
RECORDED_THREADS = ("_BinMapper", "n_threads")
_SCALARS = (int, float, complex, str, bytes, bool, type(None), np.generic)


def state_digest(value: Any) -> tuple[str, list[Any]]:
    """A deterministic digest of an object's whole state, field by field.

    It walks dicts, sequences, arrays, frames and objects' ``__dict__``,
    ``__getstate__`` or ``__reduce_ex__`` state, and hashes each leaf with
    its path and type. ``RECORDED_THREADS`` is left out and its values are
    returned, so a caller can check the exception occurred.
    """
    digest = hashlib.sha256()
    skipped: list[Any] = []
    # Visited objects are kept alive, so a freed temporary's id is never
    # reused for a later object and mistaken for one already seen.
    seen: dict[int, Any] = {}

    def leaf(path: str, kind: str, payload: bytes) -> None:
        for part in (path, kind):
            digest.update(part.encode())
            digest.update(b"\0")
        digest.update(len(payload).to_bytes(8, "little"))
        digest.update(payload)

    def walk(item: Any, path: str) -> None:
        if isinstance(item, _SCALARS):
            leaf(path, type(item).__name__, repr(item).encode())
            return
        if isinstance(item, np.ndarray):
            if item.dtype.hasobject:
                walk(item.tolist(), f"{path}<object {item.shape}>")
                return
            array = np.ascontiguousarray(item)
            leaf(
                path,
                f"ndarray {array.dtype.str} {array.shape}",
                array.tobytes(),
            )
            return
        if isinstance(item, (pd.DataFrame, pd.Series)):
            frame = item.to_frame() if isinstance(item, pd.Series) else item
            walk([str(c) for c in frame.columns], f"{path}.columns")
            walk(frame.index.to_numpy(), f"{path}.index")
            for name in frame.columns:
                walk(frame[name].to_numpy(), f"{path}[{name!r}]")
            return
        if id(item) in seen:
            leaf(path, "seen", type(item).__qualname__.encode())
            return
        seen[id(item)] = item
        if isinstance(item, Mapping):
            for key in sorted(item, key=repr):
                walk(item[key], f"{path}[{key!r}]")
            return
        if isinstance(item, (list, tuple, set, frozenset)):
            items = (
                sorted(item, key=repr)
                if isinstance(item, (set, frozenset))
                else item
            )
            leaf(path, type(item).__name__, str(len(items)).encode())
            for index, element in enumerate(items):
                walk(element, f"{path}[{index}]")
            return
        if (
            isinstance(item, type)
            or callable(item)
            and not hasattr(item, "__dict__")
        ):
            leaf(path, "callable", repr(item).encode())
            return
        name = type(item).__qualname__
        if hasattr(item, "__dict__"):
            state = dict(vars(item))
            if name == RECORDED_THREADS[0] and RECORDED_THREADS[1] in state:
                skipped.append(state.pop(RECORDED_THREADS[1]))
            walk(state, f"{path}<{name}>")
            if hasattr(type(item), "__getstate__") and not isinstance(
                item, np.random.Generator
            ):
                try:
                    extra = item.__getstate__()
                except Exception:
                    extra = None
                if isinstance(extra, dict):
                    extra = dict(extra)
                    if name == RECORDED_THREADS[0]:
                        extra.pop(RECORDED_THREADS[1], None)
                    walk(extra, f"{path}<{name}>.getstate")
            return
        try:
            reduced = item.__reduce_ex__(5)
        except Exception:
            reduced = None
        if isinstance(reduced, tuple) and len(reduced) > 1:
            walk(list(reduced[1:]), f"{path}<{name}>.reduce")
            return
        try:
            payload = pickle.dumps(item, protocol=5)
        except (TypeError, pickle.PicklingError, AttributeError):
            # A repr that carries a memory address differs between
            # processes, so it can only make the test fail, never pass.
            payload = repr(item).encode()
        leaf(path, name, payload)

    walk(value, "fitted")
    return digest.hexdigest(), skipped


def _probe(output: Path) -> None:
    """Use only generated rows and a generated wage-index mapping."""
    import numpy as np
    import pandas as pd

    sys.path.insert(0, str(ROOT / "scripts"))
    import select_m6_qstar_train_only as selector
    import track_b_b2_score as scorer

    from populace_dynamics.track_b import b2

    settings = b2.thread_settings()
    rng = np.random.default_rng(2137)
    rows = []
    for person in range(1, 241):
        age_2010 = 29 + (person % 35)
        person_level = float(rng.normal(10.2, 0.6))
        for year in range(1998, 2015, 2):
            age = age_2010 + year - 2010
            zero = rng.random() < (0.30 if age >= 55 else 0.15)
            level = (
                0.0
                if zero
                else float(np.exp(person_level + rng.normal(0, 0.4)))
            )
            rows.append(
                {
                    "person_id": person,
                    "period": year,
                    "earnings": level,
                    "age": age,
                    "weight": float(1 + person % 5),
                }
            )
    earnings = pd.DataFrame(rows)
    anchor_demo = earnings[earnings["period"] == 2010].assign(
        period=2011, interview=lambda frame: (frame["person_id"] + 1) // 2
    )
    full_anchor = b2.full_anchor_frame(anchor_demo)
    fit_input = earnings[earnings["period"] <= 2010].copy()
    nawi = {
        year: 30_000.0 * 1.03 ** (year - 1990) for year in range(1960, 2011)
    }
    fitted = scorer.fit_law(fit_input, nawi)
    assert fitted.q_invariant_fit_signature_sha256 is not None
    assert fitted.zero_anchor_gate is not None
    _, stable_audit = selector._stable_pools(fitted)
    fit_audit = selector._fit_audit(fitted, stable_audit, 2010)
    digest, recorded_threads = state_digest(fitted)
    gates = {
        name: {
            key: value
            for key, value in gate.items()
            if key != "gate_state_sha256"
        }
        for name, gate in fit_audit["participation_gates"].items()
    }
    signatures = {
        "fitted_state_sha256": digest,
        "participation_gates_without_pickle_hash": gates,
    }
    recorded = {
        "recorded_threads": [int(value) for value in recorded_threads],
        "pickle_signatures": {
            "engine": fitted.q_invariant_fit_signature_sha256,
            "selector": fit_audit["q_invariant_fit_signature_sha256"],
        },
    }
    context = scorer.build_context(fitted, earnings, full_anchor)

    def frame_bytes(frame):
        columns = []
        for name in frame.columns:
            array = frame[name].to_numpy()
            if array.dtype.kind in "biufc":
                array = np.ascontiguousarray(
                    array.astype(array.dtype.newbyteorder("<"), copy=False)
                )
                values = array.tobytes().hex()
            else:
                values = frame[name].tolist()
            columns.append(
                {"name": name, "dtype": str(array.dtype), "values": values}
            )
        return {"n_rows": len(frame), "columns": columns}

    draws = []
    for seed in b2.DRAW_SEEDS:
        scored, annual = selector._project(fitted.generator, context, seed)
        draws.append(
            {
                "seed": seed,
                "scored": frame_bytes(scored),
                "annual": frame_bytes(annual),
            }
        )
    output.mkdir()
    for name, payload in (
        ("settings", settings),
        ("fit_signatures", signatures),
        ("recorded", recorded),
        ("projected_draws", draws),
    ):
        (output / f"{name}.json").write_text(
            json.dumps(payload, sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )


def test_candidate3_fit_and_projection_are_deterministic(tmp_path):
    """Two fresh processes, different hash seeds, the same law and draws."""
    # Candidate 3's fitting stack lives only in the gate environment.
    pytest.importorskip("populace.fit")
    pytest.importorskip("quantile_forest")
    from populace_dynamics.track_b import b2

    outputs = []
    for hash_seed in ("0", "1"):
        output = tmp_path / f"hash_seed_{hash_seed}"
        environment = dict(os.environ)
        environment.update({name: "1" for name in b2.THREAD_VARIABLES})
        environment["OMP_WAIT_POLICY"] = "PASSIVE"
        environment["PYTHONHASHSEED"] = hash_seed
        environment["PYTHONPATH"] = os.pathsep.join(
            (str(ROOT / "src"), str(ROOT / "scripts"))
        )
        completed = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), str(output)],
            cwd=ROOT,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
            timeout=600,
        )
        assert completed.returncode == 0, completed.stderr[-4000:]
        settings = json.loads((output / "settings.json").read_bytes())
        assert all(settings[name] == "1" for name in b2.THREAD_VARIABLES)
        assert settings["OMP_WAIT_POLICY"] == "PASSIVE"
        outputs.append(output)
    for name in ("fit_signatures", "projected_draws", "recorded"):
        assert (outputs[0] / f"{name}.json").read_bytes() == (
            outputs[1] / f"{name}.json"
        ).read_bytes(), f"candidate-3 {name} differ between processes"
    recorded = json.loads((outputs[0] / "recorded.json").read_bytes())
    assert recorded["recorded_threads"]
    assert set(recorded["recorded_threads"]) == {1}


def test_state_digest_sees_every_field_but_the_recorded_threads():
    """The digest changes with any field, except the named exception."""
    from sklearn.ensemble import HistGradientBoostingClassifier

    rng = np.random.default_rng(7)
    features = rng.normal(size=(200, 2))
    labels = (features[:, 0] > 0).astype(int)
    model = HistGradientBoostingClassifier(max_iter=5, random_state=0)
    model.fit(features, labels)
    base, skipped = state_digest({"gate": model, "w": np.arange(3.0)})
    assert skipped and all(isinstance(value, int) for value in skipped)

    model._bin_mapper.n_threads = skipped[0] + 3
    assert state_digest({"gate": model, "w": np.arange(3.0)})[0] == base

    model._bin_mapper.n_bins_non_missing_[0] += 1
    assert state_digest({"gate": model, "w": np.arange(3.0)})[0] != base
    model._bin_mapper.n_bins_non_missing_[0] -= 1
    assert state_digest({"gate": model, "w": np.arange(3.0)})[0] == base
    assert state_digest({"gate": model, "w": np.arange(3.0) + 1})[0] != base
    frame = pd.DataFrame({"a": [1.0, 2.0]})
    other = pd.DataFrame({"a": [1.0, 2.5]})
    assert state_digest(frame)[0] != state_digest(other)[0]


if __name__ == "__main__":
    _probe(Path(sys.argv[1]))
