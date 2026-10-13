"""Tests of B2's floor comparator on invented ledgers.

No selection ledger is read: every ledger here is invented in the test,
with the selectors' key layout (``boundaries -> "2010" -> floor`` and
``floor_gate_seed_detail``) and their JSON form (``_plain``, sorted keys).
The tests check that the comparator

- reads exactly the two boundary-2010 fields and nothing else matters;
- reports equality when the six-cell fields are the builder's, and
  inequality on any change to them;
- prints booleans only, and refuses a floor artifact that is not
  committed.
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import select_m6_qstar_train_only as selector  # noqa: E402
import track_b_b2_compare_floor as comparator  # noqa: E402

from populace_dynamics.track_b import b2  # noqa: E402

REPORT_ONLY = (
    "earn_autocorr_lag5",
    "earn_dlog_kurt.older",
    "earn_dlog_kurt.prime",
    "earn_dlog_skew.older",
    "earn_dlog_skew.prime",
)
ALL_CELLS = tuple(sorted((*b2.CELLS, *REPORT_ONLY)))


def _floor(scale: float = 1.0) -> dict:
    return {
        name: {
            "mean": 0.01 * scale * (index + 1),
            "sd": 0.003 * scale * (index + 2),
            "realized_sigma": 0.02 * scale * (index + 1),
            "n_defined_seeds": 100,
            "min_events_weaker_half": 40 + index,
        }
        for index, name in enumerate(b2.M6_RETAINED)
    }


def _detail() -> list[dict]:
    return [
        {
            "seed": seed,
            "cells": {
                name: {
                    "score": (
                        None
                        if name == "earn_autocorr_lag5"
                        else round(0.0013 * (seed + 1) * (index + 1), 6)
                    ),
                    "n_events_a": 50 + seed,
                    "n_events_b": 51 + index,
                }
                for index, name in enumerate(ALL_CELLS)
            },
        }
        for seed in b2.GATE_SEEDS
    ]


def _builder(floor: dict, detail: list[dict]) -> dict:
    return {
        "floor_block_six_cells_sha256": b2.canonical_sha256(
            b2.six_cell_floor_block(floor)
        ),
        "seed_detail_six_cells_sha256": b2.canonical_sha256(
            b2.six_cell_seed_detail(detail)
        ),
    }


def _ledger(floor: dict, detail: list[dict]) -> dict:
    """An invented ledger in the selectors' layout, other fields included."""
    boundary = {
        "cutoff": 2010,
        "floor": floor,
        "floor_gate_seed_detail": detail,
        "truth_moments": {"invented": {"value": 1.0}},
        "standardizers": {name: 1.0 for name in b2.M6_RETAINED},
    }
    return {
        "schema": "invented",
        "boundaries": {
            "2006": {**boundary, "floor": _floor(2.0)},
            "2008": {**boundary, "floor": _floor(3.0)},
            "2010": boundary,
        },
        "rungs": {"0.00": {"boundaries": {"2010": {"floor": _floor(5.0)}}}},
    }


def _write(path: Path, value: dict) -> Path:
    path.write_text(
        json.dumps(selector._plain(value), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return path


def test_key_paths_are_the_selectors():
    assert comparator.FLOOR_PATH == ("boundaries", "2010", "floor")
    assert comparator.DETAIL_PATH == (
        "boundaries",
        "2010",
        "floor_gate_seed_detail",
    )
    assert [path.name for path in comparator.LEDGERS] == [
        "m6_qstar_train_only_selection_results.json",
        "m6_rhostar_train_only_selection_results.json",
    ]


def test_ledger_fields_reads_the_two_boundary_2010_fields(tmp_path):
    floor, detail = _floor(), _detail()
    floor["unretained"] = {"malformed": "ignored"}
    detail[0]["unrelated"] = "ignored"
    detail[0]["cells"]["unretained"] = "malformed but ignored"
    path = _write(tmp_path / "ledger.json", _ledger(floor, detail))
    got_floor, got_detail = comparator.ledger_fields(path)
    assert got_floor == b2.six_cell_floor_block(floor)
    assert got_detail == b2.six_cell_seed_detail(detail)
    broken = _ledger(floor, detail)
    del broken["boundaries"]["2010"]
    with pytest.raises(KeyError):
        comparator.ledger_fields(_write(tmp_path / "broken.json", broken))
    broken = _ledger({}, detail)
    with pytest.raises(KeyError):
        comparator.ledger_fields(
            _write(tmp_path / "partial_floor.json", broken)
        )
    broken = _ledger(floor, [{"seed": 0, "cells": {}}])
    with pytest.raises(KeyError):
        comparator.ledger_fields(
            _write(tmp_path / "partial_detail.json", broken)
        )


def test_equal_fields_compare_equal_and_any_change_does_not(tmp_path):
    floor, detail = _floor(), _detail()
    builder = {"person_split": _builder(floor, detail)}
    artifact = tmp_path / "floor.json"
    artifact.write_text(json.dumps(builder), encoding="utf-8")
    same = _write(tmp_path / "same.json", _ledger(floor, detail))
    result = comparator.run(artifact, [same])
    assert result == [(True, True)]
    # Only another boundary's floor moved: still equal.
    other = _ledger(floor, detail)
    other["boundaries"]["2008"]["floor"] = _floor(9.0)
    other_path = _write(tmp_path / "other.json", other)
    assert comparator.run(artifact, [other_path]) == [(True, True)]
    # A report-only cell's seed detail moved: both fields still equal.
    moved = json.loads(json.dumps(detail))
    moved[2]["cells"]["earn_dlog_skew.prime"]["score"] += 0.001
    path = _write(tmp_path / "moved.json", _ledger(floor, moved))
    assert comparator.run(artifact, [path]) == [(True, True)]
    # A retained cell's seed detail moved: only its field differs.
    moved = json.loads(json.dumps(detail))
    moved[0]["cells"]["earn_p10.prime"]["n_events_a"] += 1
    path = _write(tmp_path / "retained.json", _ledger(floor, moved))
    assert comparator.run(artifact, [path]) == [(True, False)]
    # The floor block moved.
    shifted = json.loads(json.dumps(floor))
    shifted["earn_zero_rate.older"]["sd"] *= 1.0 + 1e-15
    path = _write(tmp_path / "floor_moved.json", _ledger(shifted, detail))
    assert comparator.run(artifact, [path]) == [(False, True)]


def test_each_ledger_is_compared_even_with_duplicate_names(tmp_path):
    floor, detail = _floor(), _detail()
    artifact = _write(
        tmp_path / "floor.json", {"person_split": _builder(floor, detail)}
    )
    first, second = tmp_path / "first", tmp_path / "second"
    first.mkdir()
    second.mkdir()
    shifted = json.loads(json.dumps(floor))
    shifted["earn_p10.prime"]["mean"] += 0.001
    ledgers = [
        _write(first / "ledger.json", _ledger(floor, detail)),
        _write(second / "ledger.json", _ledger(shifted, detail)),
    ]
    assert comparator.run(artifact, ledgers) == [(True, True), (False, True)]


@settings(max_examples=150, deadline=None)
@given(
    st.lists(
        st.floats(min_value=0, max_value=1, allow_subnormal=True),
        min_size=18,
        max_size=18,
    )
)
def test_json_round_trip_keeps_the_canonical_hash(values):
    """The ledger stores floats as JSON; the hash survives the trip."""
    floor = {
        name: {
            "mean": values[3 * index],
            "sd": values[3 * index + 1],
            "realized_sigma": values[3 * index + 2],
            "n_defined_seeds": 100,
            "min_events_weaker_half": 20,
        }
        for index, name in enumerate(b2.M6_RETAINED)
    }
    stored = json.loads(json.dumps(selector._plain(floor), sort_keys=True))
    assert b2.canonical_sha256(stored) == b2.canonical_sha256(floor)
    assert b2.canonical_sha256(stored) == selector._canonical_sha256(floor)


def _git_repo(path: Path):
    def run(*args):
        return subprocess.run(
            ["git", *args],
            cwd=path,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    run("init", "-q")
    run("config", "user.email", "test@example.org")
    run("config", "user.name", "Test")
    return run


def test_main_prints_booleans_only_for_a_committed_artifact(
    tmp_path, monkeypatch
):
    repo = tmp_path / "repo"
    repo.mkdir()
    run = _git_repo(repo)
    floor, detail = _floor(), _detail()
    artifact = repo / "floor.json"
    artifact.write_text(
        json.dumps({"person_split": _builder(floor, detail)}),
        encoding="utf-8",
    )
    run("add", "floor.json")
    run("commit", "-q", "-m", "floor")
    ledger = _write(tmp_path / "ledger.json", _ledger(floor, detail))
    shifted = json.loads(json.dumps(detail))
    shifted[0]["cells"]["earn_p10.prime"]["score"] += 0.001
    changed = _write(tmp_path / "changed.json", _ledger(floor, shifted))
    monkeypatch.setattr(comparator, "ROOT", repo)
    stream = io.StringIO()
    with redirect_stdout(stream):
        assert (
            comparator.main(
                [
                    "--floor-artifact",
                    str(artifact),
                    "--ledger",
                    str(ledger),
                    "--ledger",
                    str(changed),
                ]
            )
            == 0
        )
    assert stream.getvalue() == "true\ntrue\ntrue\nfalse\n"


def test_main_refuses_an_uncommitted_artifact(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    run = _git_repo(repo)
    (repo / "readme").write_text("x", encoding="utf-8")
    run("add", "readme")
    run("commit", "-q", "-m", "init")
    artifact = repo / "floor.json"
    artifact.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(comparator, "ROOT", repo)
    with pytest.raises(RuntimeError, match="not committed"):
        comparator.main(["--floor-artifact", str(artifact)])
