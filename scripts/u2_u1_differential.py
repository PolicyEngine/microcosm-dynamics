"""The exact U1 differential harness of U2 specification section 13.

Runs U1's own code at two clean checkouts -- the U1 base (``9cee2423f048``
by default) and the U2 candidate -- with the same Python executable,
dependencies and invented seed, and compares:

1. **The dry run** (``scripts/track_u_dry_run.py --seed 20260924``): the
   entire canonical ``result.json`` with only ``/run/git_head`` and
   ``/run/date`` removed, and the complete ``RESULTS.md`` with only the
   date sentence and the code line normalized; the identical absolute
   output directory is reused sequentially, so ``run.command`` (with its
   output path), ``run.python``, ``run.git_clean`` and the seeds are
   compared.  Tolerance zero: byte equality.
2. **Additional exact contract checks**, with no exclusions:
   ``age67.WAVES``; ``observation_plan`` for U0, U1 and U0-F; the
   ``pending_decisions()`` of ``age67``, ``adjusted_poverty`` and
   ``uniform_cut_tabulation``; ``rows.MAX_RULINGS``;
   ``runner.NAMED_DELTAS``; ``uniform_cut_tabulation.REPORT_ROWS`` and
   ``COMPARATOR_COLUMN``; ``input_frames_sha256`` on seed-20260924
   invented inputs with the supplements staged and refused; and the
   actual loader's input-frame hash and loader-seal hash, with every
   reader dependency of ``age67.load_age67_inputs`` patched to the same
   invented frames, a fixed nonempty invented file manifest, refused
   supplements raising ``WealthSupplementNotStagedError("INVENTED
   supplement absent")`` for 2005 and 2007, and any file access under the
   fake PSID directory refused (``open``, ``os.listdir``, ``os.scandir``,
   ``glob`` and ``os.stat``/``os.lstat``, which ``Path.exists`` and
   ``is_file`` call); frame names, columns, dtypes, order and hashes
   compared without normalization.  Every access list must be empty.
3. **Fixed refusal parity**: the ten section 13 cases, each compared by
   exception module, class and complete message, and each held to its
   fixed expectation (:data:`EXPECTED_REFUSALS`): the seed case must
   raise ``ValueError("seed_wave_rule must be earliest_presence_wave")``,
   both existing-output cases the one-shot ``ValueError`` naming the
   artifact, the two hash cases ``runner.TrackURunError``; no case may
   pass or fail on the harness's own ``AssertionError`` stubs.

The probe encodes with the section 13 canonical form (sorted keys,
compact separators, ``allow_nan=False``) and no ``default``: a value the
encoding cannot represent fails the probe instead of being stringified.
Nothing here reads PSID data or a comparator.  Usage::

    python scripts/u2_u1_differential.py --base <checkout at 9cee2423> \\
        --candidate <clean checkout at the U2 commit> --output <json>
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

BASE_COMMIT = "9cee2423f048"
SEED = 20260924
EXCLUDED_JSON_PATHS = ("/run/git_head", "/run/date")
_ONE_SHOT = (
    "/INVENTED/u1-refusal-parity/replication_boomers2004_uniform_cut_v1.json "
    "already exists: the registered run is one-shot"
)
_U1_RUNNER = "populace_dynamics.uniform_cut_track_u.runner"
#: Section 13's fixed outcomes.  A full dict is the exact expected
#: exception; ``{"module", "class"}`` fixes the exception type only (the
#: message is held by base/candidate parity).  Every case must refuse.
EXPECTED_REFUSALS: dict[str, dict[str, str]] = {
    "invalid_provenance": {"module": _U1_RUNNER, "class": "TrackURunError"},
    "invented_with_pointer": {
        "module": _U1_RUNNER,
        "class": "TrackURunError",
    },
    "invalid_registration_url": {
        "module": _U1_RUNNER,
        "class": "TrackURunError",
    },
    "invented_labeled_registered": {
        "module": _U1_RUNNER,
        "class": "TrackURunError",
    },
    "wrong_registered_headline": {"module": "builtins", "class": "ValueError"},
    "wrong_threshold_hash": {"module": _U1_RUNNER, "class": "TrackURunError"},
    "wrong_ssi_hash": {"module": _U1_RUNNER, "class": "TrackURunError"},
    "existing_artifact": {
        "module": "builtins",
        "class": "ValueError",
        "message": _ONE_SHOT,
    },
    "existing_sidecar": {
        "module": "builtins",
        "class": "ValueError",
        "message": _ONE_SHOT,
    },
    "u2_seed_under_u1": {
        "module": "builtins",
        "class": "ValueError",
        "message": "seed_wave_rule must be earliest_presence_wave",
    },
}

#: The probe's definitions (U1 code only): imports, the canonical
#: encoding, the frame records, the patched actual-loader run and the
#: refusal-parity cases.
PROBE_DEFINITIONS = r"""
import contextlib, dataclasses, hashlib, json, os, sys
from dataclasses import replace
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from populace_dynamics.cohorts import age67, psid2010
from populace_dynamics.data import (
    deaths, employer_dc, family, family_income, marriage, psid,
)
from populace_dynamics.estimates import adjusted_poverty as ap
from populace_dynamics.estimates import uniform_cut_tabulation as ut
from populace_dynamics.uniform_cut_track_u import invented, rows, runner

SEED = 20260924


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      allow_nan=False)


def frame_record(frame):
    return {
        "columns": [str(c) for c in frame.columns],
        "dtypes": [str(t) for t in frame.dtypes],
        "n_rows": int(len(frame)),
        "sha256": hashlib.sha256(
            frame.to_csv(index=False, lineterminator="\n").encode()
        ).hexdigest(),
    }


def inputs_record(inputs):
    frames = {}
    for wave in sorted(inputs.anchors):
        frames[f"anchor_{wave}"] = frame_record(inputs.anchors[wave])
    for name in ("design", "death_records", "marriage_history",
                 "observed_earnings"):
        frames[name] = frame_record(getattr(inputs, name))
    for label, table in (("income", inputs.family_income),
                         ("wealth", inputs.family_wealth),
                         ("employer_dc", inputs.employer_dc)):
        for wave in sorted(table):
            frames[f"{label}_{wave}"] = frame_record(table[wave])
    return {
        "frame_order": list(frames),
        "frames": frames,
        "wealth_refusals": {str(k): v for k, v in
                            sorted(inputs.wealth_refusals.items())},
        "input_frames_sha256": age67.input_frames_sha256(inputs),
    }


def loader_record(staged):
    source = invented.invented_age67_inputs(
        seed=SEED, supplement_waves_staged=True)
    fake_root = Path("/INVENTED/psid-data")
    manifest = {"INVENTED/ind2023er/IND2023ER.txt": "0" * 64}
    opened = []
    guard = {"active": True}

    def under_root(value):
        if isinstance(value, int):
            return False
        try:
            return os.fsdecode(value).startswith(str(fake_root))
        except TypeError:
            return False

    def hook(event, args):
        if not guard["active"] or event not in (
                "open", "os.listdir", "os.scandir", "glob.glob",
                "glob.glob/2", "pathlib.Path.glob", "pathlib.Path.rglob"):
            return
        if args and under_root(args[0]):
            opened.append(f"{event}:{os.fsdecode(args[0])}")
            raise PermissionError(f"unpatched file access: {args[0]}")

    sys.addaudithook(hook)
    real_stat, real_lstat = os.stat, os.lstat

    def guarded(real, name):
        def call(path, *args, **kwargs):
            if guard["active"] and under_root(path):
                opened.append(f"{name}:{os.fsdecode(path)}")
                raise PermissionError(f"unpatched file access: {path}")
            return real(path, *args, **kwargs)
        return call

    @contextlib.contextmanager
    def record(root):
        yield dict(manifest)

    def wealth(wave, data_dir=None):
        if not staged and wave in (2005, 2007):
            raise family_income.WealthSupplementNotStagedError(
                "INVENTED supplement absent")
        return source.family_wealth[wave]

    patches = [
        (psid, "_resolve_data_dir", lambda data_dir=None: fake_root),
        (psid2010, "record_files_read", record),
        (age67, "verify_relationship_codes",
         lambda data_dir=None, waves=age67.WAVES:
         {wave: f"INVENTED{wave}F" for wave in waves}),
        (age67, "read_wave_anchor",
         lambda wave, data_dir=None, nrows=None: source.anchors[wave]),
        (age67, "read_design_variables",
         lambda data_dir=None, nrows=None: source.design),
        (deaths, "read_death_records",
         lambda data_dir=None: source.death_records),
        (marriage, "marriage_history",
         lambda data_dir=None: source.marriage_history),
        (family, "family_earnings_panel",
         lambda waves=None, data_dir=None: source.observed_earnings),
        (family_income, "read_family_income",
         lambda wave, data_dir=None: source.family_income[wave]),
        (employer_dc, "read_employer_dc",
         lambda wave, data_dir=None: source.employer_dc[wave]),
        (family_income, "read_family_wealth", wealth),
    ]
    patches += [(os, "stat", guarded(real_stat, "os.stat")),
                (os, "lstat", guarded(real_lstat, "os.lstat"))]
    saved = [(module, name, getattr(module, name))
             for module, name, _ in patches]
    try:
        for module, name, value in patches:
            setattr(module, name, value)
        loaded = age67.load_age67_inputs()
    finally:
        for module, name, value in saved:
            setattr(module, name, value)
        guard["active"] = False
    return {
        "opened_under_fake_root": opened,
        "provenance": {k: v for k, v in loaded.provenance.items()},
        "loader_seal": dict(loaded.loader_seal),
        **inputs_record(loaded),
    }


def refusal(call):
    try:
        call()
    except BaseException as error:
        return {"module": type(error).__module__,
                "class": type(error).__qualname__,
                "message": str(error)}
    return {"refused": False}


def refusal_parity(ratified_u1):
    POINTER = ("https://github.com/PolicyEngine/microcosm-dynamics/issues/42"
               "#issuecomment-1")
    REGISTERED_COMMIT = "a" * 40
    FIXED_ARTIFACT = Path("/INVENTED/u1-refusal-parity/"
                          "replication_boomers2004_uniform_cut_v1.json")
    FIXED_SIDECAR = Path("/INVENTED/u1-refusal-parity/"
                         "replication_boomers2004_uniform_cut_v1.env.json")
    assert FIXED_SIDECAR == FIXED_ARTIFACT.with_suffix(".env.json")

    def fake_git(*args):
        if args == ("rev-parse", "HEAD"):
            return REGISTERED_COMMIT
        if args == ("status", "--porcelain"):
            return ""
        raise AssertionError(args)

    def exists_artifact_only(path):
        if path not in (FIXED_ARTIFACT, FIXED_SIDECAR):
            raise AssertionError(path)
        return path == FIXED_ARTIFACT

    def exists_sidecar_only(path):
        if path not in (FIXED_ARTIFACT, FIXED_SIDECAR):
            raise AssertionError(path)
        return path == FIXED_SIDECAR

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_u1_registered", ROOT / "scripts" / "run_track_u_registered.py")
    registered = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(registered)
    inputs = invented.invented_age67_inputs(
        seed=SEED, supplement_waves_staged=True)
    refused = invented.invented_age67_inputs(seed=SEED)

    def params_with(**provenance):
        params = runner.committed_parameters(ap.load_poverty_thresholds())
        if "thresholds" in provenance:
            params = replace(params, thresholds=replace(
                params.thresholds, provenance=provenance["thresholds"]))
        if "ssi" in provenance:
            params = replace(params, ssi=replace(
                params.ssi, provenance=provenance["ssi"]))
        return params

    def with_exists(function):
        def call():
            original = Path.exists
            Path.exists = lambda self: function(self)
            try:
                registered.preflight(
                    registration_pointer=POINTER,
                    registered_commit=REGISTERED_COMMIT,
                    output=FIXED_ARTIFACT, git=fake_git,
                    specification=ratified_u1)
            finally:
                Path.exists = original
        return call

    cases = {
        "invalid_provenance": lambda: runner._check_inputs(
            inputs, "bad", None, False),
        "invented_with_pointer": lambda: runner._check_inputs(
            inputs, ap.INVENTED, POINTER, False),
        "invalid_registration_url": lambda: runner._check_inputs(
            inputs, ap.REGISTERED_REAL, "https://example.org/x", False),
        "invented_labeled_registered": lambda: runner._check_inputs(
            inputs, ap.REGISTERED_REAL, POINTER, False),
        "wrong_registered_headline": lambda: registered.check_headline(
            "U0", refused),
        "wrong_threshold_hash": lambda: runner._check_parameters(
            params_with(thresholds={"kind": "census_capture",
                                    "sha256": "0" * 64}),
            ap.REGISTERED_REAL),
        "wrong_ssi_hash": lambda: runner._check_parameters(
            params_with(ssi={"kind": "policyengine_us_capture",
                             "sha256": "0" * 64}),
            ap.REGISTERED_REAL),
        "existing_artifact": with_exists(exists_artifact_only),
        "existing_sidecar": with_exists(exists_sidecar_only),
        "u2_seed_under_u1": lambda: age67.Age67Spec(
            seed_wave_rule="earliest_presence_in_common_support_waves"),
    }
    return {name: refusal(call) for name, call in cases.items()}
"""

#: The probe's main part: every contract check on stdout as JSON.
PROBE_MAIN = r"""
ratified_u1 = json.loads(sys.stdin.read())
staged = invented.invented_age67_inputs(
    seed=SEED, supplement_waves_staged=True)
refused_inputs = invented.invented_age67_inputs(seed=SEED)
record = {
    "age67.WAVES": list(age67.WAVES),
    "observation_plan": {
        row: [list(cell) for cell in age67.observation_plan(
            age67.Age67Spec(row=row))]
        for row in ("U0", "U1", "U0-F")
    },
    "pending_decisions": {
        "age67": [d.as_dict() for d in age67.pending_decisions()],
        "adjusted_poverty": [d.as_dict() for d in ap.pending_decisions()],
        "uniform_cut_tabulation": [
            d.as_dict() for d in ut.pending_decisions()],
    },
    "rows.MAX_RULINGS": rows.MAX_RULINGS,
    "runner.NAMED_DELTAS": list(runner.NAMED_DELTAS),
    "uniform_cut_tabulation.REPORT_ROWS": ut.REPORT_ROWS,
    "uniform_cut_tabulation.COMPARATOR_COLUMN": ut.COMPARATOR_COLUMN,
    "input_frames_sha256": {
        "supplements_staged": inputs_record(staged),
        "supplements_refused": inputs_record(refused_inputs),
    },
    "actual_loader": {
        "supplements_staged": loader_record(True),
        "supplements_refused": loader_record(False),
    },
    "refusal_parity": refusal_parity(ratified_u1),
}
sys.stdout.write(canonical(record))
"""
#: The probe run inside each checkout (stdout is canonical JSON).
PROBE = PROBE_DEFINITIONS + PROBE_MAIN

#: Reads U1's full section 15 block once at the base commit.
BLOCK_PROBE = r"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "src"))
from populace_dynamics.uniform_cut_track_u import rows
sys.stdout.write(json.dumps(rows.specification_block(), sort_keys=True))
"""


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def normalize_json(value: dict[str, Any]) -> bytes:
    value = copy.deepcopy(value)
    del value["run"]["git_head"]
    del value["run"]["date"]
    return canonical(value)


def normalize_markdown(raw: bytes, result: dict[str, Any]) -> bytes:
    text = raw.decode("utf-8")
    date_text = (
        "Track U (DynaSim exercise 2, plan item U9) end-to-end dry run, "
        + result["run"]["date"]
        + "."
    )
    commit_text = "- Code: `" + result["run"]["git_head"] + "`"
    if text.count(date_text) != 1 or text.count(commit_text) != 1:
        raise AssertionError("the date or code line is not unique")
    text = text.replace(
        date_text,
        "Track U (DynaSim exercise 2, plan item U9) end-to-end dry run, "
        "<DATE>.",
        1,
    )
    return text.replace(commit_text, "- Code: `<COMMIT>`", 1).encode("utf-8")


def _head(checkout: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=checkout, text=True
    ).strip()


def run_dry_run(checkout: Path, output: Path) -> tuple[bytes, bytes, dict]:
    subprocess.run(
        [
            sys.executable,
            "scripts/track_u_dry_run.py",
            "--output-dir",
            str(output),
            "--seed",
            str(SEED),
        ],
        cwd=checkout,
        check=True,
    )
    result = json.loads((output / "result.json").read_text())
    if result["run"]["git_clean"] is not True:
        raise AssertionError(f"{checkout} is not clean")
    if result["run"]["invented_seed"] != SEED:
        raise AssertionError("the invented seed differs")
    if result["cohort_provenance"]["seed"] != SEED:
        raise AssertionError("the cohort seed differs")
    return (
        normalize_json(result),
        normalize_markdown((output / "RESULTS.md").read_bytes(), result),
        result["run"],
    )


def run_probe(checkout: Path, ratified_u1: str) -> bytes:
    return subprocess.run(
        [sys.executable, "-c", PROBE],
        cwd=checkout,
        input=ratified_u1,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.encode("utf-8")


def check_refusal_expectations(
    parity: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Hold one side's refusal-parity record to :data:`EXPECTED_REFUSALS`.

    Returns ``{"met": bool, "failures": {case: reason}}``: a case fails
    when it is missing, did not refuse, refused with the harness's own
    ``AssertionError`` (the fake ``git`` or ``Path.exists`` stubs), or
    differs from a fixed module, class or message.
    """

    failures: dict[str, str] = {}
    if set(parity) != set(EXPECTED_REFUSALS):
        missing = sorted(set(EXPECTED_REFUSALS) ^ set(parity))
        failures["cases"] = f"case sets differ: {missing}"
    for case, expected in EXPECTED_REFUSALS.items():
        observed = parity.get(case)
        if observed is None:
            continue
        if "class" not in observed:
            failures[case] = "did not refuse"
            continue
        if observed["class"] == "AssertionError":
            failures[case] = (
                "refused with the harness's own AssertionError: "
                f"{observed.get('message')}"
            )
            continue
        for key, value in expected.items():
            if observed.get(key) != value:
                failures[case] = (
                    f"{key} {observed.get(key)!r} is not the fixed {value!r}"
                )
                break
    return {"met": not failures, "failures": failures}


def _first_difference(left: bytes, right: bytes) -> dict[str, Any] | None:
    if left == right:
        return None
    index = next(
        (
            i
            for i, (a, b) in enumerate(zip(left, right, strict=False))
            if a != b
        ),
        min(len(left), len(right)),
    )
    return {
        "offset": index,
        "base": left[max(0, index - 80) : index + 80].decode(errors="replace"),
        "candidate": right[max(0, index - 80) : index + 80].decode(
            errors="replace"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--skip-dry-run",
        action="store_true",
        help=(
            "run only the contract and refusal-parity probes (a partial "
            "run: it never passes)"
        ),
    )
    args = parser.parse_args(argv)
    base = args.base.resolve()
    candidate = args.candidate.resolve()
    base_head = _head(base)
    if not base_head.startswith(BASE_COMMIT):
        raise AssertionError(f"base HEAD {base_head} is not {BASE_COMMIT}")
    candidate_head = _head(candidate)
    ratified_u1 = subprocess.run(
        [sys.executable, "-c", BLOCK_PROBE],
        cwd=base,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    report: dict[str, Any] = {
        "base": {"path": str(base), "head": base_head},
        "candidate": {"path": str(candidate), "head": candidate_head},
        "python": sys.executable,
        "seed": SEED,
        "tolerance": "zero: byte equality",
        "excluded_json_paths": list(EXCLUDED_JSON_PATHS),
        "ratified_u1_block_sha256": hashlib.sha256(
            ratified_u1.encode()
        ).hexdigest(),
    }
    if not args.skip_dry_run:
        with tempfile.TemporaryDirectory(prefix="u1-differential-") as tmp:
            output = Path(tmp) / "same-output"
            expected_json, expected_md, base_run = run_dry_run(base, output)
            observed_json, observed_md, candidate_run = run_dry_run(
                candidate, output
            )
        report["dry_run"] = {
            "result_json_equal": expected_json == observed_json,
            "results_md_equal": expected_md == observed_md,
            "result_json_sha256": {
                "base": hashlib.sha256(expected_json).hexdigest(),
                "candidate": hashlib.sha256(observed_json).hexdigest(),
            },
            "results_md_sha256": {
                "base": hashlib.sha256(expected_md).hexdigest(),
                "candidate": hashlib.sha256(observed_md).hexdigest(),
            },
            "first_json_difference": _first_difference(
                expected_json, observed_json
            ),
            "first_md_difference": _first_difference(expected_md, observed_md),
            "run": {"base": base_run, "candidate": candidate_run},
        }
    expected = run_probe(base, ratified_u1)
    observed = run_probe(candidate, ratified_u1)
    parsed = json.loads(expected)
    candidate_parsed = json.loads(observed)
    accesses = {
        f"{side}:{key}": record["actual_loader"][key]["opened_under_fake_root"]
        for side, record in (("base", parsed), ("candidate", candidate_parsed))
        for key in record["actual_loader"]
    }
    report["refusal_expectations"] = {
        "base": check_refusal_expectations(parsed["refusal_parity"]),
        "candidate": check_refusal_expectations(
            candidate_parsed["refusal_parity"]
        ),
    }
    report["loader_file_accesses_empty"] = not any(accesses.values())
    report["contract_checks"] = {
        "equal": expected == observed,
        "sha256": {
            "base": hashlib.sha256(expected).hexdigest(),
            "candidate": hashlib.sha256(observed).hexdigest(),
        },
        "first_difference": _first_difference(expected, observed),
        "checked": sorted(parsed),
        "refusal_parity": parsed["refusal_parity"],
        "loader_opened_under_fake_root": accesses,
    }
    report["all_equal"] = all(
        [
            report["contract_checks"]["equal"],
            *(
                [
                    report["dry_run"]["result_json_equal"],
                    report["dry_run"]["results_md_equal"],
                ]
                if "dry_run" in report
                else []
            ),
        ]
    )
    report["dry_run_skipped"] = "dry_run" not in report
    # A run without the dry-run comparison is partial, never a pass: the
    # section 13 differential's main comparison did not run.
    report["all_checks_passed"] = (
        report["all_equal"]
        and not report["dry_run_skipped"]
        and report["refusal_expectations"]["base"]["met"]
        and report["refusal_expectations"]["candidate"]["met"]
        and report["loader_file_accesses_empty"]
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {
                "all_equal": report["all_equal"],
                "all_checks_passed": report["all_checks_passed"],
            }
        )
    )
    return 0 if report["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
