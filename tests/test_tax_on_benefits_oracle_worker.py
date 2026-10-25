"""The persistent oracle worker dies with the process that launched it.

The worker source is plain Python, so these checks run it under the repo
interpreter with invented jobs; no tax interpreter is needed. A throwaway
launcher, never pytest itself, starts the worker and is then killed by its
exact pid. The test holds the worker's stdin open, so stdin EOF cannot end
the worker: only the parent-death watchdog and its kernel-side backstop
can. The third state holds the GIL in a C call, which the watchdog thread
alone cannot interrupt.
"""

import json
import os
import select
import signal
import subprocess
import sys
import time

import pytest

from tests.test_tax_on_benefits_oracle import _WORKER_SOURCE

_LAUNCHER = r"""
import os
import subprocess
import sys
import time

source = sys.stdin.read()
worker = subprocess.Popen(
    [sys.executable, "-u", "-c", source, str(os.getpid())],
    stdin=int(sys.argv[1]),
    stdout=subprocess.DEVNULL,
)
print(worker.pid, flush=True)
while True:
    time.sleep(60)
"""
# Writes bypass the worker's captured sys.stderr, reaching the test's pipe.
_READY_JOB = "import os\nos.write(2, b'ready\\n')\n"
_BUSY_JOB = "import os, time\nos.write(2, b'busy\\n')\ntime.sleep(600)\n"
# ctypes.PyDLL keeps the GIL for the whole foreign call.
_GIL_JOB = (
    "import ctypes, os\nos.write(2, b'busy\\n')\n"
    "ctypes.PyDLL(None).sleep(600)\n"
)
_STARTUP_SECONDS = 120
_EXIT_SECONDS = 10


def _readline(stream, timeout):
    """Read one line from a pipe, failing instead of blocking past timeout."""
    deadline = time.monotonic() + timeout
    line = bytearray()
    while not line.endswith(b"\n"):
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not select.select([stream], [], [], remaining)[0]:
            raise TimeoutError(f"no line within {timeout}s; got {line!r}")
        chunk = os.read(stream.fileno(), 1)
        if not chunk:
            raise EOFError(f"pipe closed; got {line!r}")
        line.extend(chunk)
    return bytes(line)


def _alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def _guards(launcher_pid, worker_pid):
    """Live guard processes for this launcher and worker, by command line."""
    marker = f"f1-oracle-guard {launcher_pid} {worker_pid}"
    listing = subprocess.run(
        ["ps", "-axo", "pid=,command="],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [line for line in listing.splitlines() if marker in line]


def _send(write_end, source):
    job = json.dumps({"source": source, "stdin": ""}) + "\n"
    os.write(write_end, job.encode("utf-8"))


@pytest.mark.parametrize("state", ["idle", "mid-job", "mid-c-call"])
def test_worker_exits_when_its_launcher_is_killed(state):
    read_end, write_end = os.pipe()
    launcher = subprocess.Popen(
        [sys.executable, "-c", _LAUNCHER, str(read_end)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        pass_fds=(read_end,),
    )
    os.close(read_end)
    worker_pid = None
    try:
        launcher.stdin.write(_WORKER_SOURCE.encode("utf-8"))
        launcher.stdin.close()
        worker_pid = int(_readline(launcher.stdout, _STARTUP_SECONDS))
        # A completed job proves the worker is running its request loop.
        _send(write_end, _READY_JOB)
        assert _readline(launcher.stderr, _STARTUP_SECONDS) == b"ready\n"
        if state != "idle":
            _send(write_end, _BUSY_JOB if state == "mid-job" else _GIL_JOB)
            assert _readline(launcher.stderr, _STARTUP_SECONDS) == b"busy\n"
        assert _alive(worker_pid)

        os.kill(launcher.pid, signal.SIGKILL)
        launcher.wait(timeout=_EXIT_SECONDS)
        deadline = time.monotonic() + _EXIT_SECONDS
        while _alive(worker_pid) and time.monotonic() < deadline:
            time.sleep(0.1)
        assert not _alive(
            worker_pid
        ), f"{state} worker {worker_pid} outlived its launcher"
        while _guards(launcher.pid, worker_pid) and (
            time.monotonic() < deadline + _EXIT_SECONDS
        ):
            time.sleep(0.1)
        assert not _guards(launcher.pid, worker_pid)
    finally:
        # Never leave a process behind, even when an assertion failed.
        os.close(write_end)
        if launcher.poll() is None:
            launcher.kill()
            launcher.wait(timeout=_EXIT_SECONDS)
        for stream in (launcher.stdin, launcher.stdout, launcher.stderr):
            stream.close()
        if worker_pid is not None and _alive(worker_pid):
            os.kill(worker_pid, signal.SIGKILL)
