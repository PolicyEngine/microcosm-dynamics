"""The persistent oracle worker dies with the process that launched it.

The worker source is plain Python, so these checks run it under the repo
interpreter with invented jobs; no tax interpreter is needed. A throwaway
launcher, never pytest itself, starts the worker and is then killed by its
exact pid. The test holds the worker's stdin open, so stdin EOF cannot end
the worker: only the parent-death watchdog and its kernel-side backstop
can. The third state holds the GIL in a C call, which the watchdog thread
alone cannot interrupt.

The Linux startup is checked by injecting each condition rather than
racing a real parent death: a stand-in ``prctl`` that fails, and a
launcher pid that is not the worker's parent. The stand-in also sets
``sys.platform``, so those checks run the Linux branch on any host; the
checks with the real ``PR_SET_PDEATHSIG`` run only on Linux.
"""

import errno
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


# PR_GET_PDEATHSIG (2) reports the armed signal; the job writes it to fd 2.
_DEATH_SIGNAL_JOB = (
    "import ctypes, os\n"
    "armed = ctypes.c_int()\n"
    "ctypes.CDLL(None).prctl(2, ctypes.byref(armed))\n"
    "os.write(2, b'pdeathsig %d\\n' % armed.value)\n"
)
_ORPHANED_AT_STARTUP = 71
_ON_LINUX = sys.platform.startswith("linux")


def _stand_in(result, error):
    """An INVENTED libc whose ``prctl`` returns ``result`` with ``error``.

    Prepended to the worker source, it reports each call on fd 2 and sets
    ``sys.platform`` after importing the worker's modules, so the worker's
    Linux startup runs on any host.
    """
    return (
        "import ctypes, os, select, signal, subprocess, sys, threading\n"
        "class _StandInLibc:\n"
        "    def prctl(self, option, value):\n"
        "        os.write(2, b'prctl %d %d\\n' % (option, value))\n"
        f"        ctypes.set_errno({error})\n"
        f"        return {result}\n"
        "ctypes.CDLL = lambda name, use_errno=False: _StandInLibc()\n"
        "sys.platform = 'linux'\n"
    )


def _not_the_parent():
    """A live pid that is not the worker's parent: this process's parent."""
    return os.getppid()


def _start_and_offer_one_job(program, launcher_pid, job=_READY_JOB):
    """Start a worker, offer one job, close stdin, and collect its exit."""
    worker = subprocess.Popen(
        [sys.executable, "-u", "-c", program, str(launcher_pid)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        request = json.dumps({"source": job, "stdin": ""}) + "\n"
        stdout, stderr = worker.communicate(
            request.encode("utf-8"), timeout=_STARTUP_SECONDS
        )
    finally:
        # Never leave a process behind, even when an assertion failed.
        if worker.poll() is None:
            worker.kill()
            worker.wait(timeout=_EXIT_SECONDS)
    return worker.returncode, stdout, stderr


@pytest.mark.parametrize(
    "result,error,launcher,code",
    [
        # INVENTED failure: the stand-in returns -1 with EINVAL.
        (-1, errno.EINVAL, "parent", 1),
        # Armed, but the launcher is no longer the parent.
        (0, 0, "not-parent", _ORPHANED_AT_STARTUP),
        # Armed under its launcher: the startup returns and serves a job.
        (0, 0, "parent", 0),
    ],
    ids=["prctl-fails", "launcher-not-parent", "armed-under-launcher"],
)
def test_linux_startup_with_an_injected_prctl(result, error, launcher, code):
    pid = os.getpid() if launcher == "parent" else _not_the_parent()
    returncode, stdout, stderr = _start_and_offer_one_job(
        _stand_in(result, error) + _WORKER_SOURCE, pid
    )
    assert returncode == code
    assert f"prctl 1 {int(signal.SIGKILL)}\n".encode() in stderr
    if code == 0:
        assert json.loads(stdout)["ok"] is True
        assert b"ready\n" in stderr
    else:
        # The startup ended before the request loop: no job was served.
        assert stdout == b""
        assert b"ready" not in stderr
    if code == 1:
        message = f"PR_SET_PDEATHSIG failed with errno {errno.EINVAL}"
        assert message.encode() in stderr


@pytest.mark.skipif(not _ON_LINUX, reason="PR_SET_PDEATHSIG is Linux-only")
def test_real_death_signal_is_armed_under_its_launcher():
    returncode, stdout, stderr = _start_and_offer_one_job(
        _WORKER_SOURCE, os.getpid(), _DEATH_SIGNAL_JOB
    )
    assert returncode == 0
    assert json.loads(stdout)["ok"] is True
    assert f"pdeathsig {int(signal.SIGKILL)}\n".encode() in stderr


@pytest.mark.skipif(not _ON_LINUX, reason="PR_SET_PDEATHSIG is Linux-only")
def test_real_death_signal_with_a_launcher_that_is_not_the_parent():
    returncode, stdout, stderr = _start_and_offer_one_job(
        _WORKER_SOURCE, _not_the_parent(), _DEATH_SIGNAL_JOB
    )
    assert returncode == _ORPHANED_AT_STARTUP
    assert stdout == b""
    assert b"pdeathsig" not in stderr
