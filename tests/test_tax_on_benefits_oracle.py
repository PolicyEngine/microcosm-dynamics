"""Invented F1 units against the pinned oracle; intended differences labeled."""

import json
import os
import selectors
import subprocess
import time
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

import pytest

from populace_dynamics.bridge import policyengine_us as bridge
from populace_dynamics.tax_on_benefits import (
    PE_US_PACKAGE_RECORD_DIGEST,
    PE_US_VERSION,
    TaxOnBenefitsInput,
    tax_on_benefits_batch,
)

PYTHON = os.environ.get("POPULACE_DYNAMICS_PE_US_PYTHON")
pytestmark = pytest.mark.skipif(not PYTHON, reason="PE-US interpreter not set")
CENT = Decimal("0.01")
_REAL_CHECKED_INSTALLATION = bridge._checked_installation


def _timed_pin_check(interpreter, **kwargs):
    """Run the bridge's real installation check, reporting its duration.

    Nothing is cached or substituted inside the check: it inspects the
    child, checks the published source and hashes every RECORD file.
    """
    started = time.monotonic()
    print("F1 oracle verification start", flush=True)
    try:
        return _REAL_CHECKED_INSTALLATION(interpreter, **kwargs)
    finally:
        print(
            "F1 oracle verification finish: "
            f"{time.monotonic() - started:.2f}s",
            flush=True,
        )


_WORKER_SOURCE = r"""
import gc
import io
import json
import os
import select
import signal
import subprocess
import sys
import threading
import time
import traceback

# Die with the launching process, whether idle or mid-job: stdin EOF is
# seen only between jobs, and an orphan is re-parented away from it.
_launcher = int(sys.argv[1]) if len(sys.argv) > 1 else os.getppid()


def _exit_when_orphaned():
    while True:
        if os.getppid() != _launcher:
            os._exit(70)
        time.sleep(1)


# The thread needs the GIL, so a long C call that holds it delays the exit
# until the call returns. The kernel-side backstop below does not wait.
_GUARD = '''
import os
import select
import signal
import sys

launcher, worker = int(sys.argv[2]), int(sys.argv[3])
queue = select.kqueue()


def watch(pid):
    try:
        queue.control(
            [
                select.kevent(
                    pid,
                    select.KQ_FILTER_PROC,
                    select.KQ_EV_ADD | select.KQ_EV_ONESHOT,
                    select.KQ_NOTE_EXIT,
                )
            ],
            0,
        )
    except ProcessLookupError:
        return False
    return True


# Wait for whichever exits first; then the worker must not outlive it.
if watch(worker) and (not watch(launcher) or queue.control(None, 1)):
    try:
        os.kill(worker, signal.SIGKILL)
    except ProcessLookupError:
        pass
'''
if sys.platform.startswith("linux"):
    import ctypes

    # PR_SET_PDEATHSIG: the kernel kills this worker when its parent dies.
    if ctypes.CDLL(None, use_errno=True).prctl(1, signal.SIGKILL) != 0:
        sys.exit(
            "f1 oracle worker: PR_SET_PDEATHSIG failed with errno "
            f"{ctypes.get_errno()}"
        )
    # The signal is armed only for a parent alive at the call. A launcher
    # that died first has already re-parented this worker, and no signal
    # will come, so exit before serving any job. Status 71, not the
    # watchdog's 70, marks an orphan found at startup.
    if os.getppid() != _launcher:
        os._exit(71)
elif hasattr(select, "kqueue"):
    # A small guard process with no pipes of ours waits on kernel exit
    # events for the launcher and this worker, and exits with the worker.
    subprocess.Popen(
        [
            sys.executable,
            "-I",
            "-S",
            "-c",
            _GUARD,
            "f1-oracle-guard",
            str(_launcher),
            str(os.getpid()),
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

# Started after the backstop, so on Linux an orphan found at startup exits
# through the check above instead of racing this thread to it.
threading.Thread(
    target=_exit_when_orphaned, name="f1-parent-watchdog", daemon=True
).start()

worker_stdin, worker_stdout, worker_stderr = (
    sys.stdin, sys.stdout, sys.stderr
)
for request_line in worker_stdin:
    request = json.loads(request_line)
    captured_stdout = io.StringIO()
    captured_stderr = io.StringIO()
    try:
        sys.stdin = io.StringIO(request["stdin"])
        sys.stdout = captured_stdout
        sys.stderr = captured_stderr
        exec(
            compile(request["source"], "<f1-pinned-oracle-job>", "exec"),
            {"__name__": "__main__"},
        )
        response = {
            "ok": True,
            "stdout": captured_stdout.getvalue(),
            "stderr": captured_stderr.getvalue(),
        }
    except BaseException as error:
        response = {
            "ok": False,
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
            "stderr": captured_stderr.getvalue(),
        }
    finally:
        sys.stdin, sys.stdout, sys.stderr = (
            worker_stdin, worker_stdout, worker_stderr
        )
    worker_stdout.write(json.dumps(response, allow_nan=False) + "\n")
    worker_stdout.flush()
    gc.collect()
"""


class _PinnedOracleWorker:
    """Retain imports while executing each real bridge job in fresh globals.

    Source, input, returned JSON, and per-job installation metadata are the
    original bridge protocol. Only interpreter startup is shared; each
    execution recreates the runner's systems dictionary and simulations.
    """

    def __init__(self, python):
        # Keep the virtualenv entry point: resolving its symlink would run
        # the base interpreter without the pinned environment's packages.
        self.python = Path(python).expanduser().absolute()
        env = dict(os.environ)
        env.update(
            PYTHONDONTWRITEBYTECODE="1",
            OMP_NUM_THREADS="1",
            OPENBLAS_NUM_THREADS="1",
            MKL_NUM_THREADS="1",
        )
        self.process = subprocess.Popen(
            [str(self.python), "-u", "-c", _WORKER_SOURCE, str(os.getpid())],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
            env=env,
        )
        self.selector = selectors.DefaultSelector()
        for stream, label in (
            (self.process.stdin, "stdin"),
            (self.process.stdout, "stdout"),
            (self.process.stderr, "stderr"),
        ):
            os.set_blocking(stream.fileno(), False)
            if label != "stdin":
                self.selector.register(stream, selectors.EVENT_READ, label)
        self.stdout_buffer = bytearray()
        self.stderr_tail = bytearray()
        self.closed = False

    def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    try:
                        self.process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        # Kill remains pending if the host blocks kernel I/O;
                        # release our pipes even in that exceptional state.
                        pass
        finally:
            self.selector.close()
            for stream in (
                self.process.stdin,
                self.process.stdout,
                self.process.stderr,
            ):
                stream.close()

    def _fail(self, message):
        details = self.stderr_tail.decode("utf-8", errors="replace")
        self.close()
        raise bridge.PolicyEngineUSUnavailable(
            f"persistent pinned oracle: {message}\n{details}"
        )

    def run(self, interpreter, source, stdin, timeout):
        category = "job"
        if source == bridge._INSPECT_SOURCE:
            category = "inspect"
        elif source == bridge._NAMED_VARIABLE_SOURCE:
            job = json.loads(stdin)
            category = f"named year={job['year']} cases={len(job['cases'])}"
        started = time.monotonic()
        print(f"F1 oracle worker start: {category}", flush=True)
        try:
            return self._run(interpreter, source, stdin, timeout)
        finally:
            print(
                f"F1 oracle worker finish: {category}, "
                f"{time.monotonic() - started:.2f}s",
                flush=True,
            )

    def _run(self, interpreter, source, stdin, timeout):
        if Path(interpreter).expanduser().absolute() != self.python:
            self._fail("requested a different interpreter")
        if self.closed:
            raise bridge.PolicyEngineUSUnavailable(
                "persistent pinned oracle is closed"
            )
        request = (
            json.dumps({"source": source, "stdin": stdin}) + "\n"
        ).encode("utf-8")
        deadline = time.monotonic() + timeout
        written = 0
        self.selector.register(
            self.process.stdin, selectors.EVENT_WRITE, "stdin"
        )
        while True:
            if b"\n" in self.stdout_buffer:
                line, _, rest = self.stdout_buffer.partition(b"\n")
                self.stdout_buffer = bytearray(rest)
                try:
                    response = json.loads(line)
                    if not response["ok"]:
                        raise bridge.PolicyEngineUSUnavailable(
                            "persistent pinned oracle job failed: "
                            f"{response['error_type']}: {response['error']}\n"
                            f"{response['traceback'][-4000:]}"
                        )
                    return json.loads(response["stdout"])
                except (KeyError, TypeError, json.JSONDecodeError) as error:
                    self._fail(f"malformed worker response: {error}")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                self._fail(f"job timed out after {timeout} seconds")
            for key, _ in self.selector.select(remaining):
                if key.data == "stdin":
                    try:
                        written += os.write(
                            key.fd, memoryview(request)[written:]
                        )
                    except BlockingIOError:
                        continue
                    except OSError as error:
                        self._fail(f"could not write job: {error}")
                    if written == len(request):
                        self.selector.unregister(key.fileobj)
                    continue
                try:
                    chunk = os.read(key.fd, 65536)
                except BlockingIOError:
                    continue
                if not chunk:
                    self.selector.unregister(key.fileobj)
                    if key.data == "stdout":
                        self._fail("worker closed its response pipe")
                    continue
                if key.data == "stdout":
                    self.stdout_buffer.extend(chunk)
                else:
                    self.stderr_tail.extend(chunk)
                    del self.stderr_tail[:-4000]


@pytest.fixture(scope="module", autouse=True)
def verified_pin_once():
    """Hash the pin once and retain imports; check each real job's metadata.

    The production bridge verifies files on every call. These oracle tests
    share a single immutable installation, so memoize the *real* check to
    avoid repeated 19,543-file walks; never substitute calculated values.
    Each original runner source executes with fresh globals in one pinned
    child, avoiding repeated cold imports on the heavily loaded host.
    """
    checked = lru_cache(maxsize=None)(_timed_pin_check)
    worker = _PinnedOracleWorker(PYTHON)

    def run(interpreter, source, stdin, timeout):
        # Oracle jobs have hit the thirty-minute bound under host I/O.
        # Leave production timeouts unchanged; give real oracle jobs room
        # to finish on this host rather than substituting tax results.
        if source == bridge._NAMED_VARIABLE_SOURCE:
            timeout = max(timeout, NAMED_JOB_SECONDS)
        return worker.run(interpreter, source, stdin, timeout)

    try:
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(bridge, "_checked_installation", checked)
            patch.setattr(bridge, "_run_child", run)
            yield
    finally:
        worker.close()


def household(
    benefits=20_000, *, age=70, joint=False, wages=0, child=False, interest=0
):
    people = [
        bridge.BridgePerson(
            "p",
            age,
            social_security_retirement=benefits if age >= 62 else 0,
            social_security_disability=benefits if age < 62 else 0,
            employment_income=wages,
            interest_income=interest,
        )
    ]
    if joint:
        people.append(bridge.BridgePerson("spouse", 70))
    if child:
        people.append(bridge.BridgePerson("child", 5))
    ids = tuple(p.person_id for p in people)
    marital_units = (("p", "spouse"),) if joint else (("p",),)
    if child:
        marital_units += (("child",),)
    return bridge.BridgeHousehold(
        "h", "TX", tuple(people), (ids,), (ids,), marital_units
    )


# The signed itemizer sequence kept live: its endpoints, the sign change
# from zero and the pin-check witness. $500 runs in pure Python.
SIGNED_LIVE_BENEFITS = (0, 250, 1000, 2000)
# Test-only budget per named-variable job. On the saturated build host a
# worker got about 2.5% of a CPU, and one unit's baseline clones the tax
# system three times for the native TOB branches.
NAMED_JOB_SECONDS = 4 * 3600


@pytest.fixture(scope="module")
def results():
    """Evaluate each unit on demand, with fresh simulations per case.

    Every unit is its own pair of bridge requests, computed when a test
    first needs it, so a slow unit delays only the tests that use it.
    No calculated values are supplied or cached outside this test module.
    Units moved to pure Python for the wall budget are in
    ``tests/test_tax_on_benefits.py``.
    """

    def plain(benefits=20_000, interest=30_000, status="SINGLE", **facts):
        return TaxOnBenefitsInput(
            household(benefits, joint=status == "JOINT", interest=interest),
            status,
            lived_apart_all_year=True if status == "SEPARATE" else None,
            tax_unit_inputs=facts,
        )

    inputs_2026 = {
        "base": plain(),
        "niit": plain(40_000, 190_000),
        "payroll": plain(
            unreported_payroll_tax=900,
            recapture_of_investment_credit=50,
            qualified_retirement_penalty=100,
        ),
        "JOINT": plain(40_000, 60_000, "JOINT"),
        "HEAD_OF_HOUSEHOLD": plain(status="HEAD_OF_HOUSEHOLD"),
        "SEPARATE": plain(status="SEPARATE"),
        # An independent fresh simulation using explicit interest components
        # also checks the single bridge total-interest normalization.
        "replay": TaxOnBenefitsInput(
            household(),
            "SINGLE",
            person_inputs={"p": {"taxable_interest_income": 30_000}},
        ),
    }
    gifts = {
        "p": {
            "taxable_interest_income": 11_500,
            "tax_exempt_interest_income": 23_000,
            "charitable_cash_donations": 20_000,
        }
    }
    inputs_2024 = {
        f"signed-{benefits}": TaxOnBenefitsInput(
            household(benefits, age=67),
            "SINGLE",
            person_inputs=gifts,
            tax_unit_inputs={
                "tax_unit_itemizes": True,
                "itemized_medical_expenses": 0,
                "salt_deduction": 0,
            },
        )
        for benefits in SIGNED_LIVE_BENEFITS
    }
    inputs_2024.update(
        {
            "actc": TaxOnBenefitsInput(
                household(
                    11_937.254901960784, age=40, wages=17_600, child=True
                ),
                "SINGLE",
                person_inputs={
                    "p": {"taxable_interest_income": 12_000},
                    "child": {"is_tax_unit_dependent": True},
                },
                tax_unit_inputs={"foreign_tax_credit": 1268},
            ),
            "eitc": TaxOnBenefitsInput(
                household(
                    31_117.77777777778, age=40, wages=14_669.869281045752
                ),
                "SINGLE",
                person_inputs={
                    "p": {"charitable_cash_donations": 3756.143790849673}
                },
                tax_unit_inputs={
                    "tax_unit_itemizes": True,
                    "itemized_medical_expenses": 0,
                    "salt_deduction": 0,
                    "foreign_tax_credit": 591.372549019608,
                },
            ),
        }
    )
    groups = {
        name: (year, {name: unit})
        for year, units in ((2026, inputs_2026), (2024, inputs_2024))
        for name, unit in units.items()
    }

    class LazyResults(dict):
        def __missing__(self, name):
            year, units = groups[name]
            print(f"F1 oracle: {year}, {tuple(units)}", flush=True)
            self.update(tax_on_benefits_batch(units, year, python=PYTHON))
            print(f"F1 oracle checked: {tuple(units)}", flush=True)
            return self[name]

    return LazyResults()


def amounts(allocation):
    return (allocation.oasdi, allocation.hi, allocation.total)


def assert_amounts(actual, expected):
    for a, e in zip(amounts(actual), expected, strict=True):
        assert abs(a - Decimal(str(e))) <= CENT
    assert abs(actual.oasdi + actual.hi - actual.total) <= CENT


def assert_native(result, expected):
    for name, value in zip(
        ("tob_revenue_oasdi", "tob_revenue_medicare_hi", "tob_revenue_total"),
        expected,
        strict=True,
    ):
        assert abs(result.pe_us[name] - Decimal(str(value))) <= CENT


def test_single_witness_and_intended_tier_1_meaning_difference(results):
    result = results["base"]
    assert result.inclusions.pre_1993 == 7500
    assert result.inclusions.current == 9600
    assert result.pe_us["taxable_social_security_tier_1"] == 4500
    assert_amounts(result.primary, (769, 252, 1021))
    assert_amounts(
        result.refundable_credits_netted_sensitivity, (769, 252, 1021)
    )
    assert_native(result, (769, 252, 1021))
    assert result.flags == ()
    assert result.installation.version == PE_US_VERSION
    assert (
        result.source["record_check"]["package_record_digest"]
        == PE_US_PACKAGE_RECORD_DIGEST
    )


def test_intended_niit_difference_in_each_fund_and_total(results):
    result = results["niit"]
    assert_amounts(result.primary, (4800, 3686, 8486))
    assert_amounts(
        result.refundable_credits_netted_sensitivity, (4800, 3686, 8486)
    )
    assert_native(result, (5180, 4218, 9398))
    assert [
        result.liabilities[k].components["net_investment_income_tax"]
        for k in ("none", "pre_1993", "current")
    ] == [0, 380, 912]
    for state in result.liabilities.values():
        assert state.components["income_tax_refundable_credits"] == 0


def test_unreported_payroll_excluded_recapture_and_penalty_retained(results):
    clean = results["base"]
    result = results["payroll"]
    assert_amounts(result.primary, amounts(clean.primary))
    assert_native(result, (769, 252, 1021))
    for label, expected in zip(
        ("none", "pre_1993", "current"), (735, 1504, 1756), strict=True
    ):
        state = result.liabilities[label]
        assert abs(state.before_refundable_credits - expected) <= CENT
        assert state.components["unreported_payroll_tax"] == 900
        assert state.components["recapture_of_investment_credit"] == 50
        assert state.components["qualified_retirement_penalty"] == 100
        assert abs(state.components["income_tax"] - expected - 900) <= CENT


@pytest.mark.parametrize(
    "status,expected",
    [
        ("JOINT", (2154, 1680, 3834)),
        ("HEAD_OF_HOUSEHOLD", (530, 210, 740)),
        ("SEPARATE", (897, 252, 1149)),
    ],
)
def test_supported_filing_configurations(results, status, expected):
    result = results[status]
    assert_amounts(result.primary, expected)
    assert_native(result, expected)


@pytest.mark.parametrize(
    "benefits,expected",
    [
        (0, (0, 0, 0)),
        (250, (-4.375, -3.0625, -7.4375)),
        (1000, (-17.5, -12.25, -29.75)),
        (2000, (-35, -24.5, -59.5)),
    ],
)
def test_intended_signed_itemizer_departures(results, benefits, expected):
    result = results[f"signed-{benefits}"]
    assert_amounts(result.primary, expected)
    assert_amounts(result.refundable_credits_netted_sensitivity, expected)
    assert_native(result, expected)


def test_deterministic_full_calculation(results):
    replay = results["replay"]
    assert replay.primary == results["base"].primary
    assert (
        replay.refundable_credits_netted_sensitivity
        == results["base"].refundable_credits_netted_sensitivity
    )
    assert replay.liabilities == results["base"].liabilities


def test_natural_actc_drop_never_enters_primary(results):
    result = results["actc"]
    assert_amounts(result.primary, (0, 0, 0))
    assert_amounts(
        result.refundable_credits_netted_sensitivity,
        (634.1176470588235, 65.8823529411765, 700),
    )
    for label, tax_before_credits, refundable_ctc in (
        ("none", 1568, 1700),
        ("pre_1993", 2202.1176470588234, 1065.8823529411766),
        ("current", 2268, 1000),
    ):
        state = result.liabilities[label]
        components = state.components
        tax_before_credits = Decimal(str(tax_before_credits))
        refundable_ctc = Decimal(str(refundable_ctc))
        assert abs(state.before_refundable_credits) <= CENT
        assert (
            abs(components["income_tax_before_credits"] - tax_before_credits)
            <= CENT
        )
        assert (
            abs(
                components["income_tax_capped_non_refundable_credits"]
                - tax_before_credits
            )
            <= CENT
        )
        assert abs(components["refundable_ctc"] - refundable_ctc) <= CENT
        assert (
            abs(components["income_tax_refundable_credits"] - refundable_ctc)
            <= CENT
        )
        assert components["eitc"] == 0
    assert result.flags == ()
    assert_native(
        result, amounts(result.refundable_credits_netted_sensitivity)
    )


def test_natural_eitc_drop_never_enters_primary(results):
    result = results["eitc"]
    assert_amounts(result.primary, (300, 0, 300))
    assert_amounts(result.refundable_credits_netted_sensitivity, (500, 0, 500))
    for label, liability, credit in (
        ("none", 500, 300),
        ("current", 800, 100),
    ):
        state = result.liabilities[label]
        assert abs(state.before_refundable_credits - liability) <= CENT
        assert abs(state.components["eitc"] - credit) <= CENT
    assert result.flags == ()
    assert_native(result, (500, 0, 500))
