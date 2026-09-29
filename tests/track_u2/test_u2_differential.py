"""The U1 differential harness of section 13 (review finding 3).

``scripts/u2_u1_differential.py`` compares U1's own code at the U1 base
commit and the U2 candidate.  These tests exercise the harness itself on
this checkout, without a second checkout: the fixed refusal expectations
reject every failure mode (no refusal, the harness's own
``AssertionError`` stubs, a changed class or message); the JSON and
Markdown normalizations remove exactly the fixed metadata; the probe
runs, encodes canonically without a ``default`` and meets the fixed
expectations with no file access under the fake PSID root; and the
probe's loader guard records ``open``, ``os.listdir`` and ``os.stat``
under that root.  INVENTED DATA - NOT A COMPARISON: the probe reads
U1's invented inputs only.
"""

from __future__ import annotations

import contextlib
import copy
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def differential():
    path = ROOT / "scripts" / "u2_u1_differential.py"
    spec = importlib.util.spec_from_file_location("_u2_u1_differential", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _good_parity(differential) -> dict:
    out = {}
    for case, expected in differential.EXPECTED_REFUSALS.items():
        out[case] = {"message": f"INVENTED message for {case}", **expected}
    return out


def test_expectations_cover_the_ten_section_13_cases(differential):
    assert list(differential.EXPECTED_REFUSALS) == [
        "invalid_provenance",
        "invented_with_pointer",
        "invalid_registration_url",
        "invented_labeled_registered",
        "wrong_registered_headline",
        "wrong_threshold_hash",
        "wrong_ssi_hash",
        "existing_artifact",
        "existing_sidecar",
        "u2_seed_under_u1",
    ]
    expected = differential.EXPECTED_REFUSALS
    assert expected["u2_seed_under_u1"]["message"] == (
        "seed_wave_rule must be earliest_presence_wave"
    )
    for case in ("existing_artifact", "existing_sidecar"):
        assert expected[case]["message"] == (
            "/INVENTED/u1-refusal-parity/"
            "replication_boomers2004_uniform_cut_v1.json already exists: "
            "the registered run is one-shot"
        )
    for case in ("wrong_threshold_hash", "wrong_ssi_hash"):
        assert expected[case]["class"] == "TrackURunError"


def test_refusal_expectations_reject_every_failure_mode(differential):
    good = _good_parity(differential)
    assert differential.check_refusal_expectations(good) == {
        "met": True,
        "failures": {},
    }
    cases = {
        "not refused": ("invalid_provenance", {"refused": False}),
        "harness stub": (
            "existing_artifact",
            {
                "module": "builtins",
                "class": "AssertionError",
                "message": "PosixPath('/x')",
            },
        ),
        "wrong message": (
            "u2_seed_under_u1",
            {
                "module": "builtins",
                "class": "ValueError",
                "message": "seed_wave_rule must be something else",
            },
        ),
        "wrong class": (
            "wrong_ssi_hash",
            {"module": "builtins", "class": "ValueError", "message": "x"},
        ),
    }
    for label, (case, value) in cases.items():
        parity = copy.deepcopy(good)
        parity[case] = value
        outcome = differential.check_refusal_expectations(parity)
        assert not outcome["met"], label
        assert case in outcome["failures"], label
    missing = copy.deepcopy(good)
    del missing["wrong_threshold_hash"]
    assert not differential.check_refusal_expectations(missing)["met"]


def test_normalizations_remove_exactly_the_fixed_metadata(differential):
    assert differential.EXCLUDED_JSON_PATHS == ("/run/git_head", "/run/date")
    result = {
        "run": {
            "git_head": "a" * 40,
            "date": "2026-09-29",
            "git_clean": True,
            "command": "python scripts/track_u_dry_run.py --output-dir /x",
        },
        "rows": {"U0": 1.5},
    }
    normalized = json.loads(differential.normalize_json(result))
    assert normalized == {
        "run": {
            "git_clean": True,
            "command": "python scripts/track_u_dry_run.py --output-dir /x",
        },
        "rows": {"U0": 1.5},
    }
    with pytest.raises(KeyError):
        differential.normalize_json({"run": {"date": "d"}})
    with pytest.raises(ValueError):
        differential.normalize_json(
            {"run": {"git_head": "a", "date": "d"}, "x": float("nan")}
        )
    text = (
        "Track U (DynaSim exercise 2, plan item U9) end-to-end dry run, "
        "2026-09-29.\n- Code: `" + "a" * 40 + "`\nrest 2026-09-29\n"
    )
    out = differential.normalize_markdown(text.encode(), result).decode()
    assert out == (
        "Track U (DynaSim exercise 2, plan item U9) end-to-end dry run, "
        "<DATE>.\n- Code: `<COMMIT>`\nrest 2026-09-29\n"
    )
    with pytest.raises(AssertionError, match="not unique"):
        differential.normalize_markdown((text + text).encode(), result)


def test_first_difference(differential):
    assert differential._first_difference(b"abc", b"abc") is None
    assert differential._first_difference(b"abc", b"abd")["offset"] == 2
    assert differential._first_difference(b"ab", b"abc")["offset"] == 2


def test_the_probe_meets_the_expectations_at_this_checkout(differential):
    """The probe, run as the harness runs it (a fresh interpreter in the
    checkout, U1's section 15 block on stdin), completes with the
    canonical encoding and no ``default``, meets every fixed refusal
    expectation and touches nothing under the fake PSID root."""

    environment = {**os.environ, "OMP_NUM_THREADS": "1"}
    block = subprocess.run(
        [sys.executable, "-c", differential.BLOCK_PROBE],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        env=environment,
    ).stdout
    raw = subprocess.run(
        [sys.executable, "-c", differential.PROBE],
        cwd=ROOT,
        input=block,
        capture_output=True,
        text=True,
        check=True,
        env=environment,
    ).stdout
    record = json.loads(raw)
    assert raw.encode("utf-8") == differential.canonical(record)
    outcome = differential.check_refusal_expectations(record["refusal_parity"])
    assert outcome == {"met": True, "failures": {}}
    for key, loaded in record["actual_loader"].items():
        assert loaded["opened_under_fake_root"] == [], key
    assert record["age67.WAVES"] == [2005, 2007, 2009, 2011, 2013]
    assert set(record["observation_plan"]) == {"U0", "U1", "U0-F"}


def test_the_loader_guard_records_every_access_under_the_fake_root(
    differential, monkeypatch
):
    """The probe's loader guard, run in this process: an unpatched
    ``Path.exists`` (``os.stat``), ``os.listdir`` and ``open`` under
    ``/INVENTED/psid-data`` are each refused and recorded, so the
    harness's empty-access requirement is not vacuous."""

    namespace: dict = {"__name__": "_probe_definitions"}
    exec(differential.PROBE_DEFINITIONS, namespace)  # noqa: S102
    age67 = namespace["age67"]
    original = age67.load_age67_inputs

    def touching(*args, **kwargs):
        assert not Path("/INVENTED/psid-data/x").exists()
        with contextlib.suppress(OSError):
            os.listdir("/INVENTED/psid-data")
        with contextlib.suppress(OSError):
            open("/INVENTED/psid-data/y")  # noqa: SIM115
        return original(*args, **kwargs)

    monkeypatch.setattr(age67, "load_age67_inputs", touching)
    record = namespace["loader_record"](True)
    assert record["opened_under_fake_root"] == [
        "os.stat:/INVENTED/psid-data/x",
        "os.listdir:/INVENTED/psid-data",
        "open:/INVENTED/psid-data/y",
    ]
    # The guard is inert once the load returns.
    assert not Path("/INVENTED/psid-data/z").exists()


def test_the_probe_encoding_has_no_default(differential):
    """The probe's canonical encoder has no ``default``: a value JSON
    cannot represent fails the probe instead of being stringified."""

    namespace: dict = {"__name__": "_probe_definitions"}
    exec(differential.PROBE_DEFINITIONS, namespace)  # noqa: S102
    canonical = namespace["canonical"]
    assert canonical({"b": [1, 2], "a": None}) == '{"a":null,"b":[1,2]}'
    with pytest.raises(TypeError):
        canonical({"x": {1, 2}})
    with pytest.raises(TypeError):
        canonical({"path": Path("/INVENTED")})
    with pytest.raises(ValueError):
        canonical({"x": float("nan")})


def test_a_skipped_dry_run_is_not_a_pass(differential, tmp_path, monkeypatch):
    """Review 2, finding 6: ``--skip-dry-run`` runs only the probes; the
    report then records the skip and the harness exits nonzero, because
    section 13's main comparison did not run."""

    monkeypatch.setattr(differential, "_head", lambda path: "9cee2423f048ab")
    monkeypatch.setattr(
        differential,
        "run_probe",
        lambda checkout, block: differential.canonical(
            {
                "refusal_parity": _good_parity(differential),
                "actual_loader": {
                    "supplements_staged": {"opened_under_fake_root": []},
                    "supplements_refused": {"opened_under_fake_root": []},
                },
            }
        ),
    )

    class _Block:
        stdout = "{}"

    monkeypatch.setattr(
        differential.subprocess, "run", lambda *a, **k: _Block()
    )
    output = tmp_path / "report.json"
    code = differential.main(
        [
            "--base",
            str(tmp_path),
            "--candidate",
            str(tmp_path),
            "--output",
            str(output),
            "--skip-dry-run",
        ]
    )
    report = json.loads(output.read_text())
    assert report["dry_run_skipped"] is True
    assert report["contract_checks"]["equal"] is True
    assert report["all_checks_passed"] is False
    assert code == 1
