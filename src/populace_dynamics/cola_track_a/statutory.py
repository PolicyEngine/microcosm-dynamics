"""Bind the Track A oracle's statutory inputs to their committed sources.

A registered Track A run (plan item A9) compares, value by value, what the
Python oracle (not Axiom) reads with a committed source:

* **Realized COLA history before the first TR2008 rate year.**  The
  runtime baseline's rate for every determination year of the committed
  realized series (``data/external/ssa_cola_history.json``, loaded through
  :func:`populace_dynamics.estimates.parameters.load_cola_history`, which
  refuses a file whose SHA-256 is not the committed pin) that precedes the
  first TR2008 rate year.  These increases enter levels only (A1 section 4,
  splice rule).
* **Statutory parameters beyond the AWI.**  The committed capture
  ``data/external/track_a_statutory_parameters.json`` (pinned here by
  :data:`CAPTURE_SHA256`; written by
  ``scripts/capture_track_a_statutory_parameters.py`` from the
  policyengine-us files whose SHA-256s the repository already pins) holds
  the contribution and benefit base, the PIA formula factors, the
  bend-point base amounts, the full retirement age schedule, the early
  reduction rates, the delayed retirement credits, the AWI before 1975 and
  the auxiliary constants.  The runtime ``SSAParameters`` must equal it on
  every value the run reads.
* **Bend points.**  For every eligibility year from 1979 through the
  reference year, the runtime bend points must equal 42 USC 415(a)(1)(B)
  applied to the TR2008 AWI (A2 capture) with the captured base amounts.
* **Contribution and benefit base against TR2008.**  For 1975-2008 the
  runtime base must also equal TR2008 Table V.C1 (historical and actual
  rows).  For 2009-2010 V.C1 prints projections, which differ from the
  realized bases the oracle uses; the check lists those years as a
  documented difference (a named gap of the dry run), not a mismatch.

Nothing here computes a benefit or reads PSID.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np

from populace_dynamics.data import tr2008
from populace_dynamics.estimates.parameters import (
    COLA_FILE_SHA256,
    COLA_HISTORY_PATH,
    load_cola_history,
)
from populace_dynamics.ss.params import SSAParameters

__all__ = [
    "AUXILIARY_CONSTANTS",
    "CAPTURE_PATH",
    "CAPTURE_SCHEMA_VERSION",
    "CAPTURE_SHA256",
    "FIRST_ORACLE_ELIGIBILITY_YEAR",
    "FIRST_TR2008_AWI_YEAR",
    "captured_ssa_parameters",
    "load_statutory_capture",
    "statutory_value_checks",
]

_ROOT = Path(__file__).resolve().parents[3]
CAPTURE_PATH = (
    _ROOT / "data" / "external" / "track_a_statutory_parameters.json"
)
CAPTURE_SCHEMA_VERSION = "populace_dynamics.track_a_statutory_parameters.v1"
#: SHA-256 of the committed capture; a changed capture is refused.
CAPTURE_SHA256 = (
    "fd56a8aa31f173d5cbe6e053538ec785c41d4c975f306bebad9d18cf76720856"
)
#: The runner replaces the oracle's AWI with TR2008's from this year.
FIRST_TR2008_AWI_YEAR = 1975
#: The oracle's PIA formula covers eligibility from 1979.
FIRST_ORACLE_ELIGIBILITY_YEAR = 1979
#: The statute-cited auxiliary constants of ``SSAParameters`` the spouse
#: and survivor paths read.
AUXILIARY_CONSTANTS: tuple[str, ...] = (
    "spousal_pia_share",
    "spousal_early_monthly_rates",
    "spousal_early_first_bracket_months",
    "survivor_pia_share",
    "survivor_reduction_floor",
    "survivor_reduction_period_months",
    "survivor_earliest_claim_age",
    "rib_lim_pia_share",
    "remarriage_protected_age",
    "remarriage_protected_age_disabled",
)
_FIRST_WAGE_BASE_YEAR = 1937
_TOLERANCE = 1e-12


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_statutory_capture(
    path: Path = CAPTURE_PATH, *, expected_sha256: str = CAPTURE_SHA256
) -> dict[str, Any]:
    """The committed statutory capture, refused unless its hash is pinned."""

    observed = _sha256(path)
    if observed != expected_sha256:
        raise ValueError(
            f"statutory capture {path} sha256 {observed} != pinned "
            f"{expected_sha256}; regenerate it with "
            "scripts/capture_track_a_statutory_parameters.py and re-pin"
        )
    capture = json.loads(Path(path).read_text(encoding="utf-8"))
    if capture.get("schema_version") != CAPTURE_SCHEMA_VERSION:
        raise ValueError(f"unexpected capture schema in {path}")
    return capture


def _year_map(values: Mapping[str, Any]) -> dict[int, float]:
    return {int(year): float(value) for year, value in values.items()}


def _step(schedule: list[list[Any]]) -> list[tuple[int, Any]]:
    return [(int(year), value) for year, value in schedule]


def captured_ssa_parameters(
    *,
    alternative: str = "intermediate",
    last_year: int = 2085,
    capture: Mapping[str, Any] | None = None,
) -> SSAParameters:
    """An ``SSAParameters`` bundle built from the committed sources only.

    The AWI is the capture's before 1975 and TR2008's from 1975 (the
    runner's A2 default); every other field is the capture's.  It reads no
    policyengine-us checkout.
    """

    capture = load_statutory_capture() if capture is None else capture
    nawi = _year_map(capture["nawi_before_1975"])
    nawi.update(
        {
            entry.year: entry.amount
            for entry in tr2008.awi_path(
                FIRST_TR2008_AWI_YEAR, last_year, alternative=alternative
            )
        }
    )
    auxiliary = {
        name: (tuple(value) if isinstance(value, list) else value)
        for name, value in capture["auxiliary_constants"].items()
    }
    return SSAParameters(
        nawi=dict(sorted(nawi.items())),
        wage_base=_year_map(capture["wage_base_change_points"]),
        pia_factors=tuple(capture["pia_factors"]),
        fra_months_by_birth_year=[
            (int(year), int(months))
            for year, months in capture["fra_months_by_birth_year"]
        ],
        early_monthly_rates=tuple(capture["early_monthly_rates"]),
        early_first_bracket_months=int(capture["early_first_bracket_months"]),
        pe_us_revision=(
            "committed_capture:"
            f"{capture['source']['policyengine_us_revision']}"
            f"+tr2008_awi_{alternative}_{FIRST_TR2008_AWI_YEAR}_{last_year}"
        ),
        delayed_credit_by_birth_year=[
            (int(year), float(rate))
            for year, rate in capture["delayed_credit_by_birth_year"]
        ],
        max_delayed_months=int(capture["max_delayed_months"]),
        **auxiliary,
    )


def _close(left: Any, right: Any) -> bool:
    try:
        return bool(
            np.allclose(
                np.asarray(left, dtype=np.float64),
                np.asarray(right, dtype=np.float64),
                rtol=0.0,
                atol=_TOLERANCE,
            )
        ) and np.shape(left) == np.shape(right)
    except (TypeError, ValueError):
        return False


def _check(
    expected: str, source: Mapping[str, Any], mismatched: dict
) -> dict[str, Any]:
    return {
        "expected": expected,
        "source": dict(source),
        "consistent": not mismatched,
        "mismatched": mismatched,
    }


def _realized_cola_check(
    baseline: Any, first_tr2008_rate_year: int
) -> dict[str, Any]:
    realized = load_cola_history()
    years = sorted(y for y in realized if y < first_tr2008_rate_year)
    mismatched: dict[str, Any] = {}
    for year in years:
        try:
            runtime = float(baseline.rate_for_determination_year(year))
        except (KeyError, ValueError):
            runtime = None
        if runtime is None or abs(runtime - realized[year]) > _TOLERANCE:
            mismatched[str(year)] = {
                "committed": realized[year],
                "runtime": runtime,
            }
    return _check(
        (
            "the committed realized COLA history for determination years "
            f"{years[0]}-{years[-1]} (before the first TR2008 rate year "
            f"{first_tr2008_rate_year}; they enter levels only)"
        ),
        {
            "path": str(COLA_HISTORY_PATH.relative_to(_ROOT)),
            "sha256": COLA_FILE_SHA256,
        },
        mismatched,
    )


def statutory_value_checks(
    params: SSAParameters,
    baseline: Any,
    *,
    first_tr2008_rate_year: int,
    reference_year: int,
    last_earnings_year: int,
    tr2008_alternative: str = "intermediate",
    capture: Mapping[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    """Each statutory input the oracle reads against its committed source.

    ``last_earnings_year`` is the last career year any population carries
    (the latest opening year), so the contribution and benefit base is
    compared for 1937 through it.  Returns one entry per check with
    ``consistent`` and the mismatched values; the runner refuses a
    ``registered_real`` run with any inconsistent check.
    """

    committed_file = capture is None
    capture = load_statutory_capture() if capture is None else capture
    source = {
        "path": (
            str(CAPTURE_PATH.relative_to(_ROOT))
            if committed_file
            else "a capture passed by the caller (not the committed file)"
        ),
        "sha256": CAPTURE_SHA256 if committed_file else None,
        "policyengine_us_revision": capture["source"][
            "policyengine_us_revision"
        ],
    }
    checks: dict[str, dict[str, Any]] = {
        "realized_cola_history": _realized_cola_check(
            baseline, first_tr2008_rate_year
        )
    }

    captured_base = _year_map(capture["wage_base_change_points"])
    mismatched: dict[str, Any] = {}
    for year in range(_FIRST_WAGE_BASE_YEAR, last_earnings_year + 1):
        applicable = [y for y in captured_base if y <= year]
        committed = captured_base[max(applicable)] if applicable else None
        try:
            runtime = params.wage_base_for(year)
        except KeyError:
            runtime = None
        if runtime is None or committed is None or runtime != committed:
            mismatched[str(year)] = {
                "committed": committed,
                "runtime": runtime,
            }
    checks["contribution_and_benefit_base"] = _check(
        f"the committed capture, {_FIRST_WAGE_BASE_YEAR}-{last_earnings_year}",
        source,
        mismatched,
    )

    tr2008_mismatched: dict[str, Any] = {}
    tr2008_differences: dict[str, Any] = {}
    for entry in tr2008.contribution_benefit_base_path(
        FIRST_TR2008_AWI_YEAR,
        min(last_earnings_year, tr2008.LAST_PRINTED_COLA_YEAR),
        alternative=tr2008_alternative,
    ):
        try:
            runtime = params.wage_base_for(entry.year)
        except KeyError:
            runtime = None
        if runtime == entry.amount:
            continue
        record = {
            "tr2008": entry.amount,
            "tr2008_source": entry.source,
            "runtime": runtime,
        }
        if entry.source == "tr2008_v_c1_projected":
            tr2008_differences[str(entry.year)] = record
        else:
            tr2008_mismatched[str(entry.year)] = record
    checks["contribution_and_benefit_base_tr2008"] = {
        **_check(
            "TR2008 V.C1 historical and actual rows (1975-2008)",
            {
                "table": "TR2008 V.C1",
                "files_sha256": dict(tr2008.FILE_SHA256),
            },
            tr2008_mismatched,
        ),
        "documented_differences": tr2008_differences,
        "documented_differences_note": (
            "V.C1 prints projections from 2009; the oracle reads the "
            "realized bases for the observed careers (a named gap)"
        ),
    }

    captured_nawi = _year_map(capture["nawi_before_1975"])
    checks["awi_before_1975"] = _check(
        "the committed capture (the oracle's AWI before TR2008's 1975 start)",
        source,
        {
            str(year): {"committed": value, "runtime": params.nawi.get(year)}
            for year, value in captured_nawi.items()
            if params.nawi.get(year) != value
        },
    )

    base = capture["bend_point_base"]
    base_year = int(base["nawi_year"])
    bend_mismatched: dict[str, Any] = {}
    for year in range(FIRST_ORACLE_ELIGIBILITY_YEAR, reference_year + 1):
        ratio = tr2008.awi(year - 2, alternative=tr2008_alternative) / (
            tr2008.awi(base_year, alternative=tr2008_alternative)
        )
        committed = (
            float(round(float(base["first"]) * ratio)),
            float(round(float(base["second"]) * ratio)),
        )
        try:
            runtime = params.bend_points(year)
        except KeyError:
            runtime = None
        if runtime is None or tuple(runtime) != committed:
            bend_mismatched[str(year)] = {
                "committed": list(committed),
                "runtime": None if runtime is None else list(runtime),
            }
    checks["bend_points"] = _check(
        (
            "42 USC 415(a)(1)(B) with the captured base amounts on the "
            f"TR2008 {tr2008_alternative} AWI, eligibility years "
            f"{FIRST_ORACLE_ELIGIBILITY_YEAR}-{reference_year}"
        ),
        {**source, "awi": "populace_dynamics.data.tr2008.awi"},
        bend_mismatched,
    )

    def scalar_check(name: str, runtime: Any, committed: Any) -> None:
        checks[name] = _check(
            "the committed capture",
            source,
            (
                {}
                if _close(runtime, committed)
                else {"committed": committed, "runtime": runtime}
            ),
        )

    scalar_check(
        "pia_factors", list(params.pia_factors), capture["pia_factors"]
    )
    committed_fra = _step(capture["fra_months_by_birth_year"])
    runtime_fra = [
        (int(year), int(months))
        for year, months in params.fra_months_by_birth_year
    ]
    checks["full_retirement_age"] = _check(
        "the committed capture (42 USC 416(l) schedule)",
        source,
        (
            {}
            if runtime_fra == committed_fra
            else {"committed": committed_fra, "runtime": runtime_fra}
        ),
    )
    early_runtime = [
        *params.early_monthly_rates,
        params.early_first_bracket_months,
    ]
    early_committed = [
        *capture["early_monthly_rates"],
        capture["early_first_bracket_months"],
    ]
    scalar_check("early_reduction", early_runtime, early_committed)
    committed_credit = _step(capture["delayed_credit_by_birth_year"])
    runtime_credit = [
        (int(year), float(rate))
        for year, rate in params.delayed_credit_by_birth_year
    ]
    credit_ok = (
        [y for y, _ in runtime_credit] == [y for y, _ in committed_credit]
        and _close(
            [r for _, r in runtime_credit], [r for _, r in committed_credit]
        )
        and params.max_delayed_months == capture["max_delayed_months"]
    )
    checks["delayed_retirement_credit"] = _check(
        "the committed capture (42 USC 402(w) schedule and cap)",
        source,
        (
            {}
            if credit_ok
            else {
                "committed": {
                    "schedule": committed_credit,
                    "max_delayed_months": capture["max_delayed_months"],
                },
                "runtime": {
                    "schedule": runtime_credit,
                    "max_delayed_months": params.max_delayed_months,
                },
            }
        ),
    )
    auxiliary_mismatched = {}
    for name in AUXILIARY_CONSTANTS:
        runtime = getattr(params, name)
        committed = capture["auxiliary_constants"][name]
        if not _close(runtime, committed):
            auxiliary_mismatched[name] = {
                "committed": committed,
                "runtime": (
                    list(runtime) if isinstance(runtime, tuple) else runtime
                ),
            }
    checks["auxiliary_constants"] = _check(
        "the committed capture (statute-cited spouse and survivor constants)",
        source,
        auxiliary_mismatched,
    )
    return checks
