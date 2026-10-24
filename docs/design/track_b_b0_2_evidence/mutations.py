"""Run B0.2's mutation checks against the count script's full test module.

Each check in ``mutation_specs.json`` makes one deliberate change to
``scripts/track_b_b0_2_counts.py``, runs all of
``tests/test_track_b_b0_2_counts.py`` in a fresh pytest process with its
own Hypothesis database, then restores the script's bytes and verifies
their SHA-256. A check is killed when pytest exits nonzero. The script
must be unmodified in git before the run starts. The record is written in
the format of ``docs/design/track_b_b0_2_counts_mutations.json``.

Run from the root of a clean clone, with the interpreter that runs the
tests::

    OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 OMP_WAIT_POLICY=PASSIVE \\
    PYTHONDONTWRITEBYTECODE=1 \\
    python docs/design/track_b_b0_2_evidence/mutations.py RECORD
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TARGET = ROOT / "scripts/track_b_b0_2_counts.py"
PROTOCOL = ROOT / "docs/design/track_b_b0_2_protocol.md"
TESTS = "tests/test_track_b_b0_2_counts.py"
ARGUMENTS = ["-m", "pytest", "-q", "-rf", "-p", "no:cacheprovider", TESTS]
FAILED = re.compile(r"^FAILED (\S+?\[[^\]]*\]|\S+)")
TIMEOUT = 1800


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def protocol_sha256() -> str:
    text = PROTOCOL.read_bytes()
    begin, end = b"<!-- protocol:begin -->", b"<!-- protocol:end -->"
    return sha256(text[text.index(begin) : text.index(end) + len(end)])


def mutate(text: str, replacements) -> tuple[str, list[int]]:
    anchors = []
    for replacement in replacements:
        old, new = replacement["old"], replacement["new"]
        count = text.count(old)
        if count == 0:
            raise SystemExit(f"anchor missing: {old!r}")
        anchors.append(count)
        if replacement["occurrence"] == "all":
            text = text.replace(old, new)
        else:
            start = -1
            for _ in range(replacement["occurrence"]):
                start = text.index(old, start + 1)
            text = text[:start] + new + text[start + len(old) :]
    return text, anchors


def main(record_path: Path) -> None:
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--", str(TARGET)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    if dirty:
        raise SystemExit(
            "the count script is modified; run from a clean clone"
        )
    specs = json.loads((HERE / "mutation_specs.json").read_text())
    original = TARGET.read_bytes()
    original_sha = sha256(original)
    environment = dict(
        os.environ,
        OMP_NUM_THREADS="1",
        OPENBLAS_NUM_THREADS="1",
        OMP_WAIT_POLICY="PASSIVE",
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONPATH=f"{ROOT / 'src'}:{ROOT}",
    )
    checks = []
    for number, spec in enumerate(specs, 1):
        text, anchors = mutate(original.decode(), spec["replacements"])
        started = time.monotonic()
        try:
            TARGET.write_bytes(text.encode())
            with tempfile.TemporaryDirectory() as storage:
                run = subprocess.run(
                    [sys.executable, *ARGUMENTS],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    env=dict(
                        environment, HYPOTHESIS_STORAGE_DIRECTORY=storage
                    ),
                    timeout=TIMEOUT,
                )
            code, output = run.returncode, run.stdout + run.stderr
        except subprocess.TimeoutExpired as error:
            stdout = error.stdout
            code = "timeout"
            output = stdout if isinstance(stdout, str) else ""
        finally:
            TARGET.write_bytes(original)
        restored = sha256(TARGET.read_bytes())
        if restored != original_sha:
            raise SystemExit("restore failed")
        lines = output.strip().splitlines()
        failed = sorted(
            {match.group(1) for line in lines if (match := FAILED.match(line))}
        )
        status = "killed" if code != 0 else "survived"
        checks.append(
            {
                "mutation": spec["mutation"],
                "replacements": [
                    dict(replacement, anchor_occurrences=count)
                    for replacement, count in zip(
                        spec["replacements"], anchors, strict=True
                    )
                ],
                "exit_code": code,
                "failed_tests": failed,
                "summary": lines[-1] if lines else "",
                "status": status,
                "restored": True,
                "restored_source_sha256": restored,
                "elapsed_seconds": round(time.monotonic() - started, 1),
            }
        )
        print(
            f"{number:2d} {status:8s} {len(failed):3d} {spec['mutation']}"
            f" | {checks[-1]['summary']}",
            flush=True,
        )
    killed = sum(check["status"] == "killed" for check in checks)
    record = {
        "schema_version": 1,
        "verification_class": "structural-count protocol conformance",
        "admitted_scope": "Invented frames only; no real-data run.",
        "mutation_method": (
            "One deliberate production behavior change per check, from "
            "docs/design/track_b_b0_2_evidence/mutation_specs.json. Each "
            "check runs the whole count test module in a fresh pytest "
            "process with its own Hypothesis database; a nonzero exit "
            "kills it. The original source bytes are restored and their "
            "SHA-256 verified after every check. No mutated "
            "implementation is committed."
        ),
        "protocol_sha256": protocol_sha256(),
        "restored_source_sha256": {
            "scripts/track_b_b0_2_counts.py": original_sha
        },
        "result": f"{killed}/{len(checks)} mutations killed",
        "runner_command": (
            "OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 "
            "OMP_WAIT_POLICY=PASSIVE PYTHONDONTWRITEBYTECODE=1 "
            ".venv/bin/python docs/design/track_b_b0_2_evidence/"
            "mutations.py RECORD"
        ),
        "test_command": (
            "PYTHONPATH=$PWD/src:$PWD python " + " ".join(ARGUMENTS)
        ),
        "checks": checks,
    }
    record_path.write_text(json.dumps(record, indent=2) + "\n")
    print(f"FINAL: {record['result']}; restored {original_sha}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
