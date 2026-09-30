"""Federal and state tax-benefit effect of the exercise-4 minimum benefit.

ILLUSTRATIVE HOUSEHOLDS, NOT SURVEY DATA.  Nothing here is drawn from the
PSID, the projection or any DYNASIM3 value.  The script is the first use of
:mod:`populace_dynamics.bridge.policyengine_us`:

1. **Microcosm side (this repository's code).**  One illustrative worker: a
   woman born 1958 with covered earnings of 25 percent of the national
   average wage index in each of the 22 years 1980-2001, first entitled to
   her retired-worker benefit in 2024 (at 66).  Her years of coverage come
   from ``min_benefit_track_m.coverage.count_coverage_years``, her PIA from
   ``min_benefit_track_m.rules.history_pia`` (the oracle's statutory AIME
   and ``ss.benefits.pia``), and her reform PIA from
   ``min_benefit_track_m.rules.evaluate_worker`` under exercise 4's
   headline option (``policy.HEADLINE_CELL``: option 2 of Favreault,
   Mermin and Steuerle (2006), the standard price-indexed minimum, with its
   printed uniform cut).  Both PIAs are carried to 2026 with statutory
   COLAs (42 USC 415(i)) from the committed SSA history (determination
   years through 2022) and the third-quarter CPI-W averages of the pinned
   policyengine-us release (2023-2025), then reduced by her claim factor
   (``rules.claim_factor``) and rounded down to the dollar.
2. **PolicyEngine-US side.**  Three households built from that worker (A:
   no other income; B: a $4,800 private pension; C: a $31,200 private
   pension), each in California, Montana and Florida, run for 2026 with
   the current-law benefit and with the reform benefit as
   ``social_security_retirement``.  The bridge decomposes the change in
   ``household_net_income`` into its components, which sum exactly to the
   net change, and repeats the runs with health coverage counted in net
   income (a sensitivity; PolicyEngine-US's default excludes it).
3. **Checks.**  The runs use policyengine-us 2.18.0 from PyPI, and the
   script refuses any other source (the installed files must match the
   wheel's RECORD).  California's 2026 SSI payment standard, missing from
   that release, is set from the California Department of Social Services'
   published table.  Every changed component is traced back through
   PolicyEngine-US's own calculation (the float32 guard), and the script
   refuses to write if any variable changed although every variable it read
   held within a cent.

Outputs (JSON with provenance, a Markdown table, and a chart per household
as PNG and SVG) go to ``--out-dir`` and ``--docs-dir``.

Run from the repository root::

    POPULACE_DYNAMICS_PE_US_PYTHON=~/.venvs/policyengine-us-2.18.0/bin/python \\
    OMP_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python \\
        scripts/pe_us_minimum_benefit_sample_households.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import yaml  # noqa: E402

from populace_dynamics.bridge import policyengine_us as bridge  # noqa: E402
from populace_dynamics.estimates.parameters import (  # noqa: E402
    load_cola_history,
)
from populace_dynamics.min_benefit_track_m import (  # noqa: E402
    coverage,
    rules,
)
from populace_dynamics.min_benefit_track_m.policy import (  # noqa: E402
    HEADLINE_CELL,
    OPTIONS,
    TrackMPolicy,
    policy_for_row,
)
from populace_dynamics.ss.params import load_ssa_parameters  # noqa: E402

SCHEMA_VERSION = "pe_us_bridge.minimum_benefit_sample_households.v2"
ILLUSTRATIVE_LABEL = "Illustrative household, not survey data"
PAYMENT_YEAR = 2026
#: ``gov/ssa/uprating.yaml`` in policyengine-us 2.18.0 marks its entries
#: dated 2022-01-01 through 2026-01-01 as actual third-quarter CPI-W
#: averages (lines 3-8: "Actuals"); later entries are forecasts.  A payment
#: year after 2026 would need a forecast COLA, which this script refuses.
LAST_ACTUAL_CPI_W_ENTRY = 2026
DEFAULT_OUT_DIR = Path(
    "~/microcosm-launch-evidence/dynasim-parity-20260909/"
    "pe-us-bridge-20260930"
).expanduser()
DEFAULT_DOCS_DIR = ROOT / "docs" / "analysis" / "pe_us_bridge_20260930"
OUTPUT_STEM = "pe_us_minimum_benefit_sample_households"

#: The one policyengine-us release the published results use: 2.18.0 on
#: PyPI, uploaded 2026-09-30.  ``wheel_sha256`` is PyPI's digest of the
#: wheel; ``package_record_digest`` is
#: :func:`bridge.package_record_digest` of that wheel's RECORD over its
#: 17,551 ``policyengine_us/`` lines, which equals the installed RECORD's
#: (checked by downloading the wheel on 2026-09-30).  The script refuses to
#: run unless the interpreter imports this release from a package index and
#: every installed ``policyengine_us/`` file matches its RECORD hash.
PE_US_RELEASE: dict[str, Any] = {
    "package": "policyengine-us",
    "version": "2.18.0",
    "index_url": "https://pypi.org/project/policyengine-us/2.18.0/",
    "wheel": "policyengine_us-2.18.0-py3-none-any.whl",
    "wheel_sha256": (
        "28e32bc1339e8ffc1ed676ac1c9ecd468d191685608039643915f63e1357085f"
    ),
    "package_record_digest": (
        "9f9f090894638e3d0e0dd5ad8ab34f36cf8cb2134ef3627407d0653381906007"
    ),
    "package_record_lines": 17_551,
}
PARAMETER_PREFIX = "policyengine_us/parameters/"

#: Payment-year values the release lacks, each from a published source.  An
#: update applies only to its states, and only when the installed parameter
#: has no entry dated in the payment year; the script refuses to run if it
#: has one that differs.  Values are monthly dollars, as the parameter is.
PARAMETER_UPDATES: tuple[dict[str, Any], ...] = (
    {
        "parameter": (
            "gov.states.ca.cdss.state_supplement.payment_standard."
            "aged_or_disabled.amount.single"
        ),
        "file": (
            PARAMETER_PREFIX + "gov/states/ca/cdss/state_supplement/"
            "payment_standard/aged_or_disabled/amount/single.yaml"
        ),
        "states": ["CA"],
        "year": PAYMENT_YEAR,
        "value": 1_233.94,
        "unit": "dollars a month",
        "source": {
            "publisher": "California Department of Social Services",
            "title": "SSI Total Monthly Payment Amounts 2026",
            "revision": "Rev. 1/26",
            "effective": "2026-01-01",
            "entry": (
                "Single Person, Aged or with Qualifying Disability; "
                "Independent Living - Residing in Own Household: $1,233.94"
            ),
            "url": (
                "https://cdss.ca.gov/Portals/13/SHD/ParaRegIndex/"
                "SSI%20Monthly%20Payment%20Amounts%202026.pdf"
            ),
            "retrieved": "2026-09-30",
            "sha256": (
                "75a9937075ed1891cf6a0dd481bd3f0516b1ad11331041555f1d8c04"
                "7bb57228"
            ),
        },
    },
)

#: The illustrative worker.  Every number here is an input chosen for the
#: illustration; everything derived from them is computed below.
WORKER: dict[str, Any] = {
    "birth_year": 1958,
    "sex": "female",
    "first_earnings_year": 1980,
    "earnings_years": 22,
    "share_of_average_wage_index": 0.25,
    "entitlement_year": 2024,
}
#: Common household facts (annual dollars; assets a stock).
MONTHLY_RENT = 800.0
BANK_ACCOUNT_ASSETS = 1_500.0
HOUSEHOLDS: tuple[dict[str, Any], ...] = (
    {
        "key": "A",
        "label": "Household A",
        "description": (
            "The worker alone: no income besides Social Security, $1,500 in "
            "the bank (under the SSI resource limit), renting for $800 a "
            "month"
        ),
        "taxable_private_pension_income": 0.0,
        "purpose": "SSI-eligible at baseline and under the reform",
    },
    {
        "key": "B",
        "label": "Household B",
        "description": (
            "The same worker with a $4,800-a-year ($400-a-month) private "
            "pension, which puts her countable income above the federal SSI "
            "benefit rate"
        ),
        "taxable_private_pension_income": 4_800.0,
        "purpose": "SSI-ineligible: the SNAP and state-supplement path",
    },
    {
        "key": "C",
        "label": "Household C",
        "description": (
            "The same worker with a $31,200-a-year ($2,600-a-month) private "
            "pension, enough for part of her Social Security to be taxable"
        ),
        # $31,200, not a round $30,000: at $30,000 California AGI sat on
        # the $30,000 edge of the use-tax table, and float32 subtraction
        # (35,761.3984 - 5,761.3999) put the reform run a fraction of a
        # cent below it, a $1 step that was noise, not a mechanism.  The
        # float32 guard below would now refuse that run.
        "taxable_private_pension_income": 31_200.0,
        "purpose": "The federal and state income-tax path",
    },
)
#: The state comparison, each state chosen for one mechanism verified in
#: the policyengine-us 2.18.0 code (paths under ``policyengine_us/``).
STATES: dict[str, dict[str, Any]] = {
    "CA": {
        "name": "California",
        "mechanism": "A state SSI supplement that PolicyEngine-US models",
        "evidence": [
            "variables/gov/states/ca/cdss/state_supplement/"
            "ca_state_supplement.py:13-17: the supplement is the payment "
            "standard less federal SSI less SSI countable income, floored at "
            "zero, so it is reduced dollar for dollar by countable income "
            "above the federal benefit rate",
            "parameters/gov/states/ca/cdss/state_supplement/payment_standard/"
            "aged_or_disabled/amount/single.yaml:12-13: the aged or disabled "
            "single payment standard is 1,206.94 a month from 2025-01-01, "
            "with no later entry; this script sets the 2026 value to CDSS's "
            "published 1,233.94 (PARAMETER_UPDATES)",
            "parameters/gov/usda/snap/income/sources/unearned_spm_unit.yaml"
            ":13: SNAP counts the California supplement as unearned income",
        ],
    },
    "MT": {
        "name": "Montana",
        "mechanism": (
            "An income tax that reaches federally taxable Social Security, "
            "and an elderly renter credit that counts all Social Security"
        ),
        "evidence": [
            "variables/gov/states/mt/tax/income/base/mt_agi_indiv.py: "
            "Montana AGI starts from federal AGI, which includes taxable "
            "Social Security; the separate Montana Social Security "
            "adjustment applies only when "
            "gov.states.mt.tax.income.social_security.applies is true",
            "parameters/gov/states/mt/tax/income/social_security/applies.yaml"
            ": false from 2024",
            "variables/gov/states/mt/tax/income/credits/"
            "mt_elderly_homeowner_or_renter/"
            "mt_elderly_homeowner_or_renter_credit.py: a refundable credit "
            "of countable rent less net household income, capped and "
            "multiplied by a gross-income schedule",
            "variables/gov/states/mt/tax/income/credits/"
            "mt_elderly_homeowner_or_renter/"
            "mt_elderly_homeowner_or_renter_credit_gross_household_income.py"
            ": gross household income adds the untaxed part of Social "
            "Security to federal AGI, so all of it counts",
        ],
    },
    "FL": {
        "name": "Florida",
        "mechanism": (
            "No state income tax, and no state supplement for a person in "
            "her own home"
        ),
        "evidence": [
            "parameters/gov/states/household/"
            "state_income_tax_before_refundable_credits.yaml: no entry for "
            "Florida",
            "variables/gov/states/fl/dcf/oss/fl_oss_eligible.py: Florida's "
            "optional state supplement requires a facility living "
            "arrangement, mapped from fl_oss_community_care_type, whose "
            "default is none",
            "parameters/gov/hhs/medicaid/eligibility/categories/"
            "senior_or_disabled/income/limit/individual.yaml:44-45: Florida's "
            "optional aged Medicaid pathway ends at 88 percent of the "
            "poverty guideline (reported as a memo; health coverage is "
            "outside default net income)",
        ],
    },
}
MEDICAID_LIMIT_FILE = (
    PARAMETER_PREFIX + "gov/hhs/medicaid/eligibility/categories/"
    "senior_or_disabled/income/limit/individual.yaml"
)
MEMO_VARIABLES = (
    "medicaid_cost",
    "msp_cost",
    "is_medicaid_eligible",
    "medicaid_optional_senior_or_disabled_countable_income",
    "medicaid_optional_senior_or_disabled_income_limit",
    f"is_qmb_eligible@{PAYMENT_YEAR}-01",
    "commodity_supplemental_food_program_eligible",
    "taxable_social_security",
)
HEALTH_OVERRIDE = {
    "gov.simulation.include_health_benefits_in_net_income": True
}
VARIANTS = ("default", "with_health")
SCENARIOS = ("baseline", "reform")


# ---------------------------------------------------------------------------
# Provenance helpers
# ---------------------------------------------------------------------------
def _git(path: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=path,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _repo_relative(path: str | Path) -> str:
    """``path`` relative to the repository root (refused if outside it)."""

    return str(Path(path).resolve().relative_to(ROOT))


def _dated_value(values: dict[Any, Any], on: str) -> float:
    """The value in force on ``on`` (ISO date) of a ``{date: value}`` map."""

    dated = sorted((str(key), value) for key, value in values.items())
    in_force = [value for key, value in dated if key <= on]
    if not in_force:
        raise ValueError(f"no value in force on {on}: {dated}")
    return float(in_force[-1])


def _parameter(root: Path, relative: str, *keys: Any, on: str) -> float:
    """A value of a policyengine-us parameter file, in force on ``on``."""

    node = yaml.safe_load((root / PARAMETER_PREFIX / relative).read_text())
    for key in keys:
        node = node[key]
    return _dated_value(node.get("values", node), on)


def _yaml_year_values(path: Path) -> dict[int, float]:
    document = yaml.safe_load(path.read_text())
    return {
        int(str(key)[:4]): float(value)
        for key, value in document["values"].items()
    }


def pinned_release(
    python: str | None,
) -> tuple[bridge.PolicyEngineUSInstallation, dict[str, Any]]:
    """The interpreter's policyengine-us, checked against the pinned release.

    Refuses (``ValueError``) unless it is a published index install of
    :data:`PE_US_RELEASE`'s version whose installed ``policyengine_us/``
    files all match the RECORD and whose RECORD matches the wheel's.
    """

    installation = bridge.inspect_installation(python)
    source = bridge.check_published_source(installation)
    problems = []
    if source["kind"] != "index":
        problems.append(f"installed from {source['kind']}, not PyPI")
    if installation.version != PE_US_RELEASE["version"]:
        problems.append(
            f"version {installation.version}, not {PE_US_RELEASE['version']}"
        )
    record = bridge.verify_record(installation)
    if record["mismatched"] or record["missing"]:
        problems.append(
            f"{len(record['mismatched'])} installed files differ from the "
            f"RECORD and {len(record['missing'])} are missing"
        )
    if record["package_record_digest"] != (
        PE_US_RELEASE["package_record_digest"]
    ):
        problems.append("the RECORD is not the pinned wheel's")
    if problems:
        raise ValueError(
            "the policyengine-us interpreter is not the pinned release ("
            + "; ".join(problems)
            + "); install it with `uv venv ~/.venvs/policyengine-us-2.18.0 && "
            "uv pip install --python ~/.venvs/policyengine-us-2.18.0 "
            "policyengine-us==2.18.0` and set "
            f"{bridge.PE_US_PYTHON_ENV}"
        )
    return installation, {
        "release": dict(PE_US_RELEASE),
        "installed": {
            "version": installation.version,
            "policyengine_core_version": installation.core_version,
            "python_version": installation.python_version,
            "installer": installation.installer,
            "record_sha256": installation.record_sha256,
        },
        "source_check": source,
        "record_check": {
            key: (len(value) if isinstance(value, list) else value)
            for key, value in record.items()
        },
        "interpreter": (
            f"{bridge.PE_US_PYTHON_ENV}: a uv virtual environment holding "
            "policyengine-us==2.18.0 from PyPI"
        ),
    }


def parameter_updates(parameter_root: Path) -> list[dict[str, Any]]:
    """The :data:`PARAMETER_UPDATES` to apply, each with the value it replaces.

    Refuses an update whose parameter already has an entry dated in its
    year with a different value; drops one whose entry already matches.
    """

    applied = []
    for update in PARAMETER_UPDATES:
        path = parameter_root / update["file"]
        document = yaml.safe_load(path.read_text())
        entries = sorted(
            (str(key), float(value))
            for key, value in document["values"].items()
        )
        year = str(update["year"])
        dated = [(key, value) for key, value in entries if key[:4] == year]
        if dated:
            if all(math.isclose(v, update["value"]) for _, v in dated):
                continue
            raise ValueError(
                f"{update['parameter']} has {dated} for {year}, not the "
                f"published {update['value']}"
            )
        held = [(key, value) for key, value in entries if key[:4] < year]
        held_date, held_value = held[-1]
        applied.append(
            {
                **update,
                "file_sha256": _sha256(path),
                "installed_value": held_value,
                "installed_value_dated": held_date,
            }
        )
    return applied


def _overrides_for(
    state: str, variant: str, updates: list[dict[str, Any]]
) -> dict[str, Any]:
    overrides: dict[str, Any] = {
        update["parameter"]: update["value"]
        for update in updates
        if state in update["states"]
    }
    if variant == "with_health":
        overrides.update(HEALTH_OVERRIDE)
    return overrides


def _no_absolute_paths(value: Any, where: str = "document") -> None:
    """Refuse an absolute or home path anywhere in the output."""

    if isinstance(value, dict):
        for key, item in value.items():
            _no_absolute_paths(item, f"{where}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _no_absolute_paths(item, f"{where}[{index}]")
    elif isinstance(value, str):
        if value.startswith(("/", "~")) or "/Users/" in value:
            raise ValueError(f"{where} holds a local path: {value}")


# ---------------------------------------------------------------------------
# The Microcosm side: the worker's PIA, the minimum and the COLAs
# ---------------------------------------------------------------------------
def cola_rates(
    payment_year: int, parameter_root: Path
) -> tuple[dict[int, float], dict[str, Any]]:
    """Determination-year COLAs through ``payment_year - 1``.

    1979-2022 from the committed SSA history
    (``estimates.parameters.load_cola_history``); 2023 onward derived from
    the release's third-quarter CPI-W averages by
    :func:`bridge.cola_rates_from_cpi_w`.  The two sources overlap in 2022
    and must agree there.
    """

    if payment_year > LAST_ACTUAL_CPI_W_ENTRY:
        raise ValueError(
            f"payment year {payment_year} needs a COLA determined after the "
            "last actual CPI-W average in this release"
        )
    history = load_cola_history()
    relative = PARAMETER_PREFIX + "gov/ssa/uprating.yaml"
    uprating_path = parameter_root / relative
    cpi_w = {
        year: value
        for year, value in _yaml_year_values(uprating_path).items()
        if year <= LAST_ACTUAL_CPI_W_ENTRY
    }
    derived = bridge.cola_rates_from_cpi_w(cpi_w)
    overlap = sorted(set(derived) & set(history))
    if not overlap:
        raise ValueError("the CPI-W series does not overlap the history")
    for year in overlap:
        if not math.isclose(derived[year], history[year], abs_tol=1e-12):
            raise ValueError(
                f"COLA {year}: CPI-W gives {derived[year]}, the committed "
                f"history {history[year]}"
            )
    rates = {int(year): float(history[year]) for year in history}
    for year, rate in derived.items():
        rates.setdefault(year, rate)
    missing = [year for year in range(1979, payment_year) if year not in rates]
    if missing:
        raise ValueError(f"no COLA for determination years {missing}")
    history_provenance = dict(history.provenance)
    if "path" in history_provenance:
        history_provenance["path"] = _repo_relative(history_provenance["path"])
    provenance = {
        "history": history_provenance,
        "history_years": [min(history), max(history)],
        "cpi_w_path": relative,
        "cpi_w_path_is_relative_to": "the installed policyengine-us release",
        "cpi_w_sha256": _sha256(uprating_path),
        "cpi_w_third_quarter_averages": {
            str(year): value for year, value in sorted(cpi_w.items())
        },
        "derived_rates": {
            str(year): rate for year, rate in sorted(derived.items())
        },
        "overlap_checked": overlap,
        "rule": (
            "42 USC 415(i)(1)(D): the percentage by which the third-quarter "
            "CPI-W exceeds that of the last cost-of-living computation "
            "quarter, rounded to the nearest one-tenth of 1 percent"
        ),
    }
    return rates, provenance


def worker_benefits(payment_year: int, parameter_root: Path) -> dict[str, Any]:
    """The worker's PIAs under current law and option 2, carried forward."""

    params = load_ssa_parameters(parameter_root)
    qc = coverage.load_qc_amounts()
    thresholds = rules.load_aged_thresholds()
    rates, cola_provenance = cola_rates(payment_year, parameter_root)

    birth = WORKER["birth_year"]
    first = WORKER["first_earnings_year"]
    share = WORKER["share_of_average_wage_index"]
    history = {
        year: round(share * params.nawi[year], 2)
        for year in range(first, first + WORKER["earnings_years"])
    }
    policy = TrackMPolicy()
    years = rules.record_years(
        basis=rules.BASIS_OLD_AGE,
        birth_year=birth,
        window_year=WORKER["entitlement_year"],
    )
    count = coverage.count_coverage_years(
        history,
        birth_year=birth,
        through_year=years.last_year,
        qc=qc,
        nawi=params.nawi,
        policy=policy,
        gap_years=(),
    )
    pia_record = rules.history_pia(
        history,
        birth_year=birth,
        params=params,
        basis=rules.BASIS_OLD_AGE,
        window_year=years.window_year,
        policy=policy,
    )
    inputs = rules.WorkerInputs(
        pia=pia_record.pia,
        work_years=count.years,
        first_pia_year=years.window_year,
        threshold_year=years.threshold_year,
        birth_year=birth,
    )
    option_number = HEADLINE_CELL[0]
    option = OPTIONS[option_number]
    outcomes = {}
    for row in ("MS0", "MS1", "MS4"):
        outcomes[row] = rules.evaluate_worker(
            inputs,
            option_number,
            thresholds=thresholds,
            nawi=params.nawi,
            policy=policy_for_row(row),
        )
    headline = outcomes["MS0"]
    for row, outcome in outcomes.items():
        if outcome != headline:
            raise AssertionError(
                f"{row} changes this worker's outcome: the window and "
                "policy year should not matter for a 2024 entitlement"
            )
    if not headline.on_minimum:
        raise AssertionError(
            f"the illustrative worker is not on the minimum: {headline}"
        )
    option_1 = rules.evaluate_worker(
        inputs, 1, thresholds=thresholds, nawi=params.nawi, policy=policy
    )
    claim = rules.claim_factor(birth, years.window_year, params)
    last_determination = payment_year - 1

    def carried(pia: float) -> dict[str, Any]:
        amount, steps = bridge.carry_pia_forward(
            pia,
            rates,
            first_determination_year=years.threshold_year,
            last_determination_year=last_determination,
        )
        monthly = math.floor(amount * claim + 1e-9)
        return {
            "pia_at_eligibility": pia,
            "cola_steps": list(steps),
            "pia_payment_year": amount,
            "monthly_benefit": monthly,
            "annual_benefit": 12 * monthly,
        }

    current_law = carried(pia_record.pia)
    reform = carried(headline.option_pia)
    reduced_current_law = carried(option_1.option_pia)
    counted = count.as_dict()
    return {
        "label": ILLUSTRATIVE_LABEL,
        "inputs": dict(WORKER),
        "earnings_history": {
            str(year): value for year, value in sorted(history.items())
        },
        "earnings_rule": (
            f"{share:.0%} of the national average wage index "
            "(ss.params.load_ssa_parameters().nawi) in each year, rounded "
            "to the cent"
        ),
        "record_years": years.as_dict(),
        # The count's PSID bookkeeping (observed, imputed and unobserved
        # years, the flag) describes survey coverage; this history is
        # invented and complete by construction, so only the count is kept.
        "years_of_coverage": {
            "years": counted["years"],
            "counted_years": counted["counted_years"],
            "through_year": counted["through_year"],
            "note": (
                "Invented history: covered earnings in every year "
                f"{first}-{first + WORKER['earnings_years'] - 1} and none "
                "after, by construction. Each counted year's earnings reach "
                "four quarters of coverage (coverage.count_coverage_years); "
                "the PSID observation fields do not apply."
            ),
        },
        "pia_record": pia_record.as_dict(),
        "threshold": {
            "year": years.threshold_year,
            "annual": thresholds.for_year(years.threshold_year),
            "source": dict(thresholds.source),
        },
        "option": option.as_dict(),
        "schedule_share": option.schedule.share(headline.work_years_star),
        "outcome": headline.as_dict(),
        "outcome_rows_checked": sorted(outcomes),
        "option_1_outcome": option_1.as_dict(),
        "claim_factor": claim,
        "months_from_full_retirement_age": (
            12 * (years.window_year - birth) - params.fra_months(birth)
        ),
        "current_law": current_law,
        "reform": reform,
        "reduced_current_law_memo": reduced_current_law,
        "cola": cola_provenance,
        "rounding": (
            "PIA: ss.benefits.pia floors to a dime; each COLA step floors to "
            "a dime (42 USC 415(i)(2)(A)(ii)); the monthly benefit is the "
            "PIA times the claim factor rounded down to the dollar (the "
            "415(g) reading recorded in min_benefit_track_m/policy.py's "
            "MINIMUM_ROUNDING_DIME note)"
        ),
        "parameters": {
            "ssa": (
                "policyengine_us/parameters/gov/ssa in the pinned "
                "policyengine-us release (see provenance.policyengine_us)"
            ),
            "quarter_of_coverage": dict(qc.source),
        },
    }


def reform_name(worker: dict[str, Any], *, short: bool = False) -> str:
    """The reform in words, from the worker's computed schedule share."""

    share = worker["schedule_share"]
    years = worker["years_of_coverage"]["years"]
    number = worker["option"]["number"]
    text = (
        f"a minimum benefit set at {share:.0%} of the aged poverty threshold "
        f"for {years} years of work"
    )
    if short:
        return text
    return f"{text} (Favreault, Mermin and Steuerle 2006, option {number})"


# ---------------------------------------------------------------------------
# The PolicyEngine-US side
# ---------------------------------------------------------------------------
def household(
    spec: dict[str, Any], state: str, social_security: float, quarters: int
) -> bridge.BridgeHousehold:
    person = bridge.BridgePerson(
        person_id="worker",
        age=PAYMENT_YEAR - WORKER["birth_year"],
        social_security_retirement=social_security,
        taxable_private_pension_income=spec["taxable_private_pension_income"],
        bank_account_assets=BANK_ACCOUNT_ASSETS,
        pre_subsidy_rent=12 * MONTHLY_RENT,
        medicare_quarters_of_coverage=quarters,
    )
    return bridge.BridgeHousehold(
        household_id=f"household_{spec['key'].lower()}_{state.lower()}",
        state=state,
        people=(person,),
        tax_units=(("worker",),),
        spm_units=(("worker",),),
        marital_units=(("worker",),),
        has_heating_cooling_expense=True,
        takes_up_housing_assistance=False,
        food_preparation_allowed=True,
    )


def _case_id(key: str, state: str, scenario: str, variant: str) -> str:
    return f"{key}_{state}_{scenario}_{variant}"


def run_households(
    worker: dict[str, Any],
    python: str | None,
    updates: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], bridge.RunResult]:
    baseline_ss = float(worker["current_law"]["annual_benefit"])
    reform_ss = float(worker["reform"]["annual_benefit"])
    quarters = 4 * int(worker["years_of_coverage"]["years"])
    cases: list[bridge.RunCase] = []
    plan: list[dict[str, Any]] = []
    for spec in HOUSEHOLDS:
        for state in STATES:
            entry = {
                "spec": spec,
                "state": state,
                "cases": {},
                "situations": {},
                "overrides": {
                    variant: _overrides_for(state, variant, updates)
                    for variant in VARIANTS
                },
            }
            for scenario, amount in zip(
                SCENARIOS, (baseline_ss, reform_ss), strict=True
            ):
                built = household(spec, state, amount, quarters)
                situation = bridge.to_situation(built, PAYMENT_YEAR)
                entry["situations"][scenario] = situation
                for variant in VARIANTS:
                    case_id = _case_id(spec["key"], state, scenario, variant)
                    cases.append(
                        bridge.RunCase(
                            case_id=case_id,
                            situation=situation,
                            expected_state=state,
                            memo=MEMO_VARIABLES,
                            parameter_overrides=entry["overrides"][variant],
                        )
                    )
                    entry["cases"][(scenario, variant)] = case_id
            plan.append(entry)
    result = bridge.run_policyengine_us(
        cases, year=PAYMENT_YEAR, python=python
    )
    rows = []
    for entry in plan:
        runs = {key: result.runs[cid] for key, cid in entry["cases"].items()}
        decompositions = {
            variant: bridge.decompose(
                runs[("baseline", variant)].tree,
                runs[("baseline", variant)].values,
                runs[("reform", variant)].values,
                reform_tree=runs[("reform", variant)].tree,
            )
            for variant in VARIANTS
        }
        spec = entry["spec"]
        rows.append(
            {
                "household": spec["key"],
                "label": spec["label"],
                "state": entry["state"],
                "baseline_social_security_annual": baseline_ss,
                "reform_social_security_annual": reform_ss,
                "decomposition": decompositions["default"],
                "with_health": decompositions["with_health"],
                "memo": {
                    scenario: dict(runs[(scenario, "default")].memo)
                    for scenario in SCENARIOS
                },
                "overrides": entry["overrides"],
                "situations": entry["situations"],
                "tree": runs[("baseline", "default")].tree,
                "run_values": {
                    variant: {
                        scenario: runs[(scenario, variant)].values
                        for scenario in SCENARIOS
                    }
                    for variant in VARIANTS
                },
            }
        )
    return rows, result


def float32_guard(rows: list[dict[str, Any]], python: str | None) -> None:
    """Trace every changed leaf of every comparison; record what it finds.

    Each comparison (household, state, with and without health coverage)
    is rerun with PolicyEngine-US's tracer on, and
    :func:`bridge.uncaused_changes` walks each changed leaf's calculation.
    Adds ``row["float32_guard"][variant]``: the traced leaves, the leaves
    that changed by less than $2 (:func:`bridge.small_changes`), and every
    variable that changed although each variable it read held within a
    cent.
    """

    cases = []
    overrides = {}
    plan = []
    for row in rows:
        for variant, decomposition in (
            ("default", row["decomposition"]),
            ("with_health", row["with_health"]),
        ):
            changed = sorted(
                {
                    c.variable
                    for c in decomposition.components
                    if c.change_cents
                }
            )
            for scenario in SCENARIOS:
                case_id = _case_id(
                    row["household"], row["state"], scenario, variant
                )
                cases.append((case_id, row["situations"][scenario], changed))
                overrides[case_id] = row["overrides"][variant]
            plan.append((row, variant, decomposition, changed))
    traces = bridge.trace_policyengine_us(
        cases,
        year=PAYMENT_YEAR,
        python=python,
        parameter_overrides=overrides,
    )
    for row, variant, decomposition, changed in plan:
        baseline = traces[
            _case_id(row["household"], row["state"], "baseline", variant)
        ]
        reform = traces[
            _case_id(row["household"], row["state"], "reform", variant)
        ]
        # A differential check: each traced leaf, run alone, equals its
        # value in the batched run (one person, so every unit is one row).
        for scenario, nodes in zip(SCENARIOS, (baseline, reform), strict=True):
            batched = row["run_values"][variant][scenario]
            for name in changed:
                traced = math.fsum(nodes[f"{name}@{PAYMENT_YEAR}"].value)
                if abs(traced - batched[name]) >= bridge.CENT_TOLERANCE:
                    raise AssertionError(
                        f"{row['household']}-{row['state']} {scenario} "
                        f"{variant}: {name} is {traced} traced alone and "
                        f"{batched[name]} batched"
                    )
        uncaused = bridge.uncaused_changes(
            baseline, reform, [f"{name}@{PAYMENT_YEAR}" for name in changed]
        )
        row.setdefault("float32_guard", {})[variant] = {
            "traced_leaves": changed,
            "traced_nodes": len(set(baseline) | set(reform)),
            "small_changes": [
                {"variable": c.variable, "change": c.change_cents / 100}
                for c in bridge.small_changes(decomposition)
            ],
            "uncaused_changes": uncaused,
        }


def check_invariants(rows: list[dict[str, Any]]) -> list[str]:
    """Properties of this run, checked before anything is written."""

    checks = []
    for row in rows:
        tag = f"{row['household']}-{row['state']}"
        for variant in VARIANTS:
            d: bridge.Decomposition = (
                row["decomposition"]
                if variant == "default"
                else row["with_health"]
            )
            total = sum(c.change_cents for c in d.components)
            assert total == d.net_change_cents, tag
            categories = d.by_category()
            assert sum(v["change"] for v in categories.values()) == total, tag
            ss = categories["social_security"]["change"]
            expected = bridge.to_cents(
                row["reform_social_security_annual"]
                - row["baseline_social_security_annual"]
            )
            assert ss == expected, (tag, ss, expected)
            for name in (
                "ssi",
                "snap",
                "csfp",
                "state_benefits",
                "federal_income_tax",
                "state_income_tax",
            ):
                assert categories[name]["change"] <= 0, (tag, variant, name)
            assert abs(d.reported_gap_cents) <= 1, tag
            guard = row["float32_guard"][variant]
            if guard["uncaused_changes"]:
                raise AssertionError(
                    f"{tag} ({variant}): float32 guard: "
                    f"{guard['uncaused_changes']}"
                )
    checks.append(
        "every household-state pair, with and without health coverage: the "
        "leaf changes sum exactly (in cents) to the net change, and the "
        "categories to the same total"
    )
    checks.append(
        "the Social Security component equals the Microcosm benefit change"
    )
    checks.append(
        "SSI, SNAP, the Commodity Supplemental Food Program, state benefits "
        "and the federal and state income-tax contributions never rise when "
        "Social Security rises"
    )
    checks.append(
        "PolicyEngine-US's own household_net_income change is within one "
        "cent of the definition's sum"
    )
    checks.append(
        "float32 guard: every changed leaf traced through PolicyEngine-US's "
        "calculation; no variable changed while every variable it read held "
        "within a cent"
    )
    return checks


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------
def _money(cents: int, *, signed: bool = False) -> str:
    value = cents / 100
    text = f"{abs(value):,.0f}"
    if signed:
        if cents > 0:
            return f"+{text}"
        if cents < 0:
            return f"−{text}"
        return "0"
    return f"−{text}" if cents < 0 else text


def table_categories(rows: list[dict[str, Any]]) -> list[str]:
    """Categories nonzero, at baseline or reform, in any of the nine cases.

    Every table shows the same rows, zeros included, so a program or tax
    that one state has and another lacks reads as a visible zero.
    """

    present: set[str] = set()
    for row in rows:
        categories = row["decomposition"].by_category()
        present.update(
            name
            for name, entry in categories.items()
            if entry["baseline"] or entry["reform"]
        )
    return [name for name in bridge.CATEGORY_ORDER if name in present]


def chart_categories(rows: list[dict[str, Any]]) -> list[str]:
    """Categories that change in any of the nine cases, for every chart.

    Every chart shows the same rows, zeros included; a category that
    changes in none of the nine cases is on no chart.
    """

    changed: set[str] = set()
    for row in rows:
        categories = row["decomposition"].by_category()
        changed.update(
            name for name, entry in categories.items() if entry["change"]
        )
    return [name for name in bridge.CATEGORY_ORDER if name in changed]


#: Shorter row labels for the charts (the tables keep the full labels).
CHART_LABELS = {
    **bridge.CATEGORY_LABELS,
    "state_benefits": "State benefits",
    "csfp": "Commodity food program",
    "federal_income_tax": "Federal income tax",
    "federal_refundable_credits": "Federal refundable credits",
    "state_income_tax": "State income tax",
    "state_refundable_credits": "State refundable credits",
    "other_taxes": "Other taxes",
    "health_net": "Health, net",
}
HEALTH_ROW_LABEL = "Net, with health coverage*"


def medicaid_explanations(
    rows: list[dict[str, Any]], limits: dict[str, float]
) -> dict[tuple[str, str], str]:
    """Why net income with health coverage differs, per affected case.

    Only one mechanism is described: Medicaid eligibility ending as the
    optional senior pathway's countable income passes its limit.  Any other
    difference is refused, so no case gets a text that does not fit it.
    """

    out = {}
    for row in rows:
        if row["with_health"].net_change_cents == (
            row["decomposition"].net_change_cents
        ):
            continue
        before, after = row["memo"]["baseline"], row["memo"]["reform"]
        income_key = "medicaid_optional_senior_or_disabled_countable_income"
        limit_key = "medicaid_optional_senior_or_disabled_income_limit"
        pattern = (
            before["is_medicaid_eligible"] == 1
            and after["is_medicaid_eligible"] == 0
            and before[income_key] <= before[limit_key]
            and after[income_key] > after[limit_key]
        )
        if not pattern:
            raise AssertionError(
                f"{row['household']}-{row['state']}: net income with health "
                "coverage changes for a reason the text does not describe"
            )
        share = limits[row["state"]]
        qmb = f"is_qmb_eligible@{PAYMENT_YEAR}-01"
        qmb_text = (
            " She is QMB-eligible in both runs, and PolicyEngine-US counts "
            "the Medicare Savings Program only once full Medicaid ends "
            "(msp_cost.py:28), so that benefit appears in the reform."
            if before[qmb] == 1 and after[qmb] == 1
            else ""
        )
        out[(row["household"], row["state"])] = (
            f"In {STATES[row['state']]['name']}, the increase raises her "
            "countable income for the optional aged Medicaid pathway from "
            f"${_money(bridge.to_cents(before[income_key]))} to "
            f"${_money(bridge.to_cents(after[income_key]))}, past the limit "
            f"of {share:.0%} of the poverty guideline "
            f"(${_money(bridge.to_cents(after[limit_key]))}), so Medicaid "
            "ends (PolicyEngine-US 2.18.0, "
            "is_optional_senior_or_disabled_income_eligible.py:23-32; "
            "individual.yaml:44-45)." + qmb_text
        )
    return out


def markdown(rows: list[dict[str, Any]], document: dict[str, Any]) -> str:
    provenance = document["provenance"]
    release = provenance["policyengine_us"]["release"]
    installed = provenance["policyengine_us"]["installed"]
    record = provenance["policyengine_us"]["record_check"]
    lines = [
        "# The minimum benefit after taxes and transfers: sample households",
        "",
        f"**{ILLUSTRATIVE_LABEL}.** Three households built around one "
        "illustrative worker, run through PolicyEngine-US for payment year "
        f"{PAYMENT_YEAR}. Amounts are annual 2026 dollars. Taxes and costs "
        "enter as negative contributions, so each column sums to net income "
        "(PolicyEngine-US's `household_net_income`, which by default "
        "excludes health coverage).",
        "",
        f"- Microcosm Dynamics commit `{provenance['microcosm_dynamics']['commit']}`",
        f"- PolicyEngine-US {release['version']} from PyPI (wheel SHA-256 "
        f"`{release['wheel_sha256']}`), with policyengine-core "
        f"{installed['policyengine_core_version']}. All "
        f"{record['files_checked']:,} installed `policyengine_us/` files "
        "match the wheel's RECORD.",
        f"- Reform: {document['reform']}, compared with current-law "
        "scheduled benefits",
        f"- Social Security: {_money(bridge.to_cents(rows[0]['baseline_social_security_annual']))} "
        f"a year under current law, "
        f"{_money(bridge.to_cents(rows[0]['reform_social_security_annual']))} "
        "under the reform",
    ]
    for update in provenance["policyengine_us"]["parameter_updates"]:
        source = update["source"]
        lines.append(
            f"- Parameter update ({', '.join(update['states'])}): "
            f"`{update['parameter']}` is set to {update['value']:,.2f} "
            f"{update['unit']} for {update['year']}, from {source['publisher']}, "
            f"\"{source['title']}\" ({source['revision']}, effective "
            f"{source['effective']}; {source['url']}, retrieved "
            f"{source['retrieved']}). PolicyEngine-US {release['version']} "
            f"has no {update['year']} entry and would hold "
            f"{update['installed_value']:,.2f} from "
            f"{update['installed_value_dated']}."
        )
    lines += [
        "",
        "## Summary",
        "",
        "| Household | State | Social Security | Net income | Share of the "
        "benefit increase kept | Net income with health coverage |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        d = row["decomposition"]
        ss = d.by_category()["social_security"]["change"]
        share = d.net_change_cents / ss if ss else float("nan")
        lines.append(
            f"| {row['household']} | {row['state']} | "
            f"{_money(ss, signed=True)} | "
            f"{_money(d.net_change_cents, signed=True)} | {share:.0%} | "
            f"{_money(row['with_health'].net_change_cents, signed=True)} |"
        )
    lines += [
        "",
        "Net income with health coverage values Medicaid at its average "
        "cost per enrollee: an upper-end valuation of coverage, not a cash "
        "loss.",
        "",
    ]
    names = table_categories(rows)
    qmb = f"is_qmb_eligible@{PAYMENT_YEAR}-01"
    for spec in HOUSEHOLDS:
        key = spec["key"]
        lines += [f"## {spec['label']}", "", spec["description"] + ".", ""]
        for row in rows:
            if row["household"] != key:
                continue
            d = row["decomposition"]
            categories = d.by_category()
            lines += [
                f"### {spec['label']}, {STATES[row['state']]['name']}",
                "",
                "| Component | Baseline | Reform | Change |",
                "|---|---:|---:|---:|",
            ]
            for name in names:
                entry = categories[name]
                lines.append(
                    f"| {bridge.CATEGORY_LABELS[name]} | "
                    f"{_money(entry['baseline'])} | "
                    f"{_money(entry['reform'])} | "
                    f"{_money(entry['change'], signed=True)} |"
                )
            lines.append(
                f"| **Net income** | **{_money(d.baseline_net_cents)}** | "
                f"**{_money(d.reform_net_cents)}** | "
                f"**{_money(d.net_change_cents, signed=True)}** |"
            )
            health = row["with_health"]
            memo_b = row["memo"]["baseline"]
            memo_r = row["memo"]["reform"]
            qmb_text = {
                (1.0, 1.0): "QMB-eligible in both runs",
                (0.0, 0.0): "not QMB-eligible in either run",
            }.get(
                (memo_b[qmb], memo_r[qmb]),
                f"QMB eligibility {memo_b[qmb]:.0f} → {memo_r[qmb]:.0f}",
            )
            lines += [
                "",
                "Memo (outside default net income): Medicaid at cost "
                f"{_money(bridge.to_cents(memo_b['medicaid_cost']))} → "
                f"{_money(bridge.to_cents(memo_r['medicaid_cost']))}; "
                "Medicare Savings Program "
                f"{_money(bridge.to_cents(memo_b['msp_cost']))} → "
                f"{_money(bridge.to_cents(memo_r['msp_cost']))} "
                f"({qmb_text}; counted only without full Medicaid). "
                "Net income with health coverage counted changes by "
                f"{_money(health.net_change_cents, signed=True)}.",
                "",
            ]
    explanations = document["medicaid_explanations"]
    if explanations:
        lines += ["## Health coverage", ""]
        lines += [f"- {text}" for text in explanations.values()]
        lines.append("")
    guard = document["float32_guard"]
    lines += [
        "## Float32 guard",
        "",
        guard["summary"],
        "",
        "## Notes",
        "",
        *[f"- {note}" for note in document["caveats"]],
        "",
    ]
    return "\n".join(lines)


def _serialize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "household": row["household"],
        "label": row["label"],
        "state": row["state"],
        "baseline_social_security_annual": row[
            "baseline_social_security_annual"
        ],
        "reform_social_security_annual": row["reform_social_security_annual"],
        "parameter_overrides": row["overrides"],
        "decomposition": row["decomposition"].as_dict(),
        "with_health_benefits_in_net_income": {
            "net_change": row["with_health"].net_change_cents / 100,
            "baseline_net_income": row["with_health"].baseline_net_cents / 100,
            "reform_net_income": row["with_health"].reform_net_cents / 100,
            "categories": {
                name: {k: v / 100 for k, v in entry.items()}
                for name, entry in row["with_health"].by_category().items()
            },
        },
        "memo": row["memo"],
        "float32_guard": row["float32_guard"],
        "situations": row["situations"],
    }


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
#: Colors from the dataviz skill's reference palette (diverging poles and
#: text inks, light surface).
POSITIVE = "#2a78d6"
NEGATIVE = "#e34948"
NET = "#52514e"
INK = "#0b0b0b"
MUTED = "#52514e"
GRID = "#e4e3df"
SURFACE = "#fcfcfb"


def chart_footnotes(
    spec: dict[str, Any], document: dict[str, Any]
) -> list[str]:
    """The footnote paragraphs under a household's chart."""

    provenance = document["provenance"]
    pe = provenance["policyengine_us"]
    notes = [
        "Blue raises net income and red lowers it; the gray bars are net "
        "changes. *Health coverage counted: Medicaid valued at its average "
        "cost per enrollee, an upper-end valuation of coverage, not a cash "
        "loss.",
    ]
    for (key, _state), text in document["medicaid_explanations"].items():
        if key == spec["key"]:
            notes.append(text)
    for update in pe["parameter_updates"]:
        notes.append(
            f"{STATES[update['states'][0]]['name']}: the 2026 SSI payment "
            f"standard is set to the published ${update['value']:,.2f} a "
            f"month ({update['source']['publisher']}, "
            f"{update['source']['title']}, {update['source']['revision']}); "
            f"PolicyEngine-US {pe['release']['version']} holds "
            f"${update['installed_value']:,.2f} from "
            f"{update['installed_value_dated'][:4]}."
        )
    notes.append(
        f"PolicyEngine-US {pe['release']['version']} (PyPI); Microcosm "
        f"Dynamics {provenance['microcosm_dynamics']['commit'][:10]}."
    )
    return notes


def draw_chart(
    rows: list[dict[str, Any]],
    spec: dict[str, Any],
    document: dict[str, Any],
    stem: Path,
) -> list[Path]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    matplotlib.rcParams["svg.hashsalt"] = "pe-us-bridge"
    matplotlib.rcParams["font.family"] = "DejaVu Sans"
    # Dollar signs are text, not mathtext delimiters.
    matplotlib.rcParams["text.parse_math"] = False
    matplotlib.rcParams["hatch.color"] = SURFACE
    key = spec["key"]
    own = [row for row in rows if row["household"] == key]
    names = chart_categories(rows)
    labels = (
        [CHART_LABELS[name] for name in names]
        + ["Net income"]
        + [HEALTH_ROW_LABEL]
    )
    changes_by_state = {}
    for row in own:
        categories = row["decomposition"].by_category()
        changes_by_state[row["state"]] = (
            [categories[name]["change"] / 100 for name in names]
            + [row["decomposition"].net_change_cents / 100]
            + [row["with_health"].net_change_cents / 100]
        )
    extent = max(
        max(abs(v) for v in values) for values in changes_by_state.values()
    )
    running_extent = 0.0
    for values in changes_by_state.values():
        cumulative = 0.0
        for value in values[:-2]:
            cumulative += value
            running_extent = max(running_extent, abs(cumulative))
    limit = max(extent, running_extent) * 1.5 or 1.0

    width = 4.1 * len(own)
    footer = [
        textwrap.fill(note, width=int(width * 16.5))
        for note in chart_footnotes(spec, document)
    ]
    footer_lines = sum(note.count("\n") + 1 for note in footer)
    footer_height = 0.145 * footer_lines + 0.15
    plot_height = 0.5 * len(labels) + 0.6
    top_height = 1.35
    height = top_height + plot_height + footer_height + 0.45
    fig, axes = plt.subplots(
        1,
        len(own),
        figsize=(width, height),
        sharey=True,
        facecolor=SURFACE,
    )
    axes = list(axes) if len(own) > 1 else [axes]
    y_positions = list(range(len(labels)))[::-1]
    net_index = len(labels) - 2
    health_index = len(labels) - 1
    for ax, row in zip(axes, own, strict=True):
        ax.set_facecolor(SURFACE)
        values = changes_by_state[row["state"]]
        cumulative = 0.0
        for index, (value, y) in enumerate(
            zip(values, y_positions, strict=True)
        ):
            is_total = index >= net_index
            start = 0.0 if is_total else cumulative
            color = NET if is_total else (POSITIVE if value >= 0 else NEGATIVE)
            if value != 0:
                # A thin bar keeps an outline in its own color, so a change
                # of a few dollars stays visible next to one of thousands.
                thin = abs(value) < 0.02 * limit
                ax.barh(
                    y,
                    value,
                    left=start,
                    height=0.6,
                    color=color,
                    alpha=0.55 if index == health_index else 1.0,
                    hatch="///" if index == health_index else None,
                    edgecolor=color if thin else SURFACE,
                    linewidth=1.5,
                    zorder=3,
                )
            else:
                ax.plot(
                    [start, start],
                    [y - 0.3, y + 0.3],
                    color=MUTED,
                    linewidth=1.2,
                    zorder=3,
                )
            end = start + value
            text = _money(round(value * 100), signed=True)
            offset = limit * 0.03
            ax.text(
                end + offset if value >= 0 else end - offset,
                y,
                text,
                va="center",
                ha="left" if value >= 0 else "right",
                fontsize=9,
                color=INK,
                fontweight="bold" if is_total else "normal",
                bbox={"facecolor": SURFACE, "edgecolor": "none", "pad": 1.0},
                zorder=4,
            )
            marked = (row["household"], row["state"]) in (
                document["medicaid_explanations"]
            )
            if index == health_index and marked:
                ax.text(
                    offset,
                    y,
                    "Medicaid ends\n(valued at cost)",
                    va="center",
                    ha="left",
                    fontsize=7.5,
                    style="italic",
                    color=INK,
                    linespacing=1.1,
                    zorder=4,
                )
            if not is_total:
                cumulative = end
        ax.axvline(0, color=MUTED, linewidth=0.8, zorder=2)
        ax.set_xlim(-limit, limit)
        ax.set_title(
            STATES[row["state"]]["name"],
            loc="left",
            fontsize=11,
            color=INK,
            fontweight="bold",
        )
        ax.grid(axis="x", color=GRID, linewidth=0.6, zorder=0)
        ax.tick_params(axis="x", labelsize=8, colors=MUTED)
        ax.tick_params(axis="y", length=0, labelsize=9.5, colors=INK)
        ax.xaxis.set_major_formatter(
            matplotlib.ticker.FuncFormatter(
                lambda v, _: (
                    "$0"
                    if v == 0
                    else (
                        f"−${abs(v) / 1000:,.0f}k"
                        if v < 0
                        else f"${v / 1000:,.0f}k"
                    )
                )
            )
        )
        ax.xaxis.set_major_locator(matplotlib.ticker.MultipleLocator(1000))
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(GRID)
        ax.axhline(y_positions[net_index] + 0.5, color=GRID, linewidth=0.8)
    axes[0].set_yticks(y_positions)
    axes[0].set_yticklabels(labels)

    def from_top(inches: float) -> float:
        return 1 - inches / height

    fig.text(
        0.01,
        from_top(0.18),
        f"{spec['label']}: change in 2026 net income from the minimum benefit",
        ha="left",
        va="top",
        fontsize=13.5,
        fontweight="bold",
        color=INK,
    )
    subtitle = textwrap.fill(
        f"{ILLUSTRATIVE_LABEL}. {spec['description']}. Reform: "
        f"{document['reform']}, against current-law benefits; annual "
        "dollars.",
        width=int(width * 13.4),
    )
    fig.text(
        0.01,
        from_top(0.52),
        subtitle,
        ha="left",
        va="top",
        fontsize=9,
        color=MUTED,
        linespacing=1.4,
    )
    fig.text(
        0.01,
        (footer_height + 0.05) / height,
        "\n".join(footer),
        ha="left",
        va="top",
        fontsize=7.5,
        color=MUTED,
        linespacing=1.35,
    )
    fig.subplots_adjust(
        left=0.16,
        right=0.98,
        top=from_top(top_height),
        bottom=(footer_height + 0.45) / height,
        wspace=0.12,
    )
    paths = []
    for suffix, kwargs in (
        (".png", {"dpi": 200, "metadata": {"Software": None}}),
        (".svg", {"metadata": {"Date": None, "Creator": None}}),
    ):
        path = stem.with_suffix(suffix)
        fig.savefig(path, facecolor=SURFACE, **kwargs)
        paths.append(path)
    plt.close(fig)
    return paths


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def _guard_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    comparisons = 0
    leaves = 0
    nodes = 0
    small = []
    for row in rows:
        for variant in VARIANTS:
            guard = row["float32_guard"][variant]
            comparisons += 1
            leaves += len(guard["traced_leaves"])
            nodes += guard["traced_nodes"]
            small += [
                f"{row['household']}-{row['state']} ({variant}): "
                f"{item['variable']} {item['change']:+.2f}"
                for item in guard["small_changes"]
            ]
    small_text = (
        "No leaf changed by a nonzero amount under $2."
        if not small
        else "Leaves that changed by a nonzero amount under $2, each traced "
        "to a changed input: " + "; ".join(small) + "."
    )
    return {
        "comparisons": comparisons,
        "changed_leaves_traced": leaves,
        "traced_nodes": nodes,
        "small_changes": small,
        "uncaused_changes": 0,
        "summary": (
            f"Every changed leaf of the {comparisons} comparisons (nine "
            "household-state pairs, with and without health coverage; "
            f"{leaves} leaves) was traced through PolicyEngine-US's own "
            f"calculation ({nodes:,} traced variable-periods). No variable "
            "changed while every variable it read held within a cent, the "
            "signature of a float32 step at a bracket edge. " + small_text
        ),
    }


def _release_caveats(root: Path) -> list[str]:
    """Caveats whose amounts are read from the pinned release."""

    fy27 = f"{PAYMENT_YEAR}-10-01"
    snap = "gov/usda/snap/"
    allotment = _parameter(
        root, snap + "max_allotment.yaml", "main", "CONTIGUOUS_US", 1, on=fy27
    )
    deduction = _parameter(
        root,
        snap + "income/deductions/standard.yaml",
        "CONTIGUOUS_US",
        1,
        on=fy27,
    )
    utility = {
        state: _parameter(
            root,
            snap + "income/deductions/utility/standard/main.yaml",
            state,
            on=fy27,
        )
        for state in ("CA", "FL", "MT")
    }
    csfp = _parameter(
        root, "gov/usda/csfp/amount.yaml", on=f"{PAYMENT_YEAR}-01-01"
    )
    version = PE_US_RELEASE["version"]
    return [
        "SNAP for October-December 2026 uses USDA's fiscal-2027 maximum "
        f"allotment (${allotment:,.0f} a month for one person) and standard "
        f"deduction (${deduction:,.0f}) as policyengine-us {version} encodes "
        "them (gov/usda/snap/max_allotment.yaml:33, "
        "income/deductions/standard.yaml:17). The state standard utility "
        "allowances have no fiscal-2027 entry there, so those months use "
        f"the fiscal-2026 amounts (California ${utility['CA']:,.0f}, "
        f"Florida ${utility['FL']:,.0f} and Montana "
        f"${utility['MT']:,.0f} a month; "
        "income/deductions/utility/standard/main.yaml:112, 179 and 387).",
        f"In policyengine-us {version} SNAP counts California's SSI "
        "supplement as unearned income "
        "(gov/usda/snap/income/sources/unearned_spm_unit.yaml:13), so a "
        "supplement lost to the benefit increase partly offsets SNAP's "
        "reduction.",
        "Take-up is PolicyEngine-US's default: full for SSI, SNAP and "
        "Medicaid (takes_up_ssi_if_eligible.py:9, "
        "takes_up_snap_if_eligible.py:9, takes_up_medicaid_if_eligible.py:9"
        "). The Commodity Supplemental Food Program has no take-up input: "
        "every eligible person gets USDA's cost per caseload slot, "
        f"${csfp:,.0f} in {PAYMENT_YEAR} "
        "(commodity_supplemental_food_program.py:10-11, "
        "gov/usda/csfp/amount.yaml:11), though the program is "
        "caseload-limited and serves far fewer people than are eligible. "
        "Housing assistance is switched off because vouchers are rationed, "
        "and the household can prepare food at home.",
    ]


def build(
    python: str | None,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[tuple[str, str], str]]:
    installation, pe_provenance = pinned_release(python)
    parameter_root = Path(installation.location)
    updates = parameter_updates(parameter_root)
    worker = worker_benefits(PAYMENT_YEAR, parameter_root)
    rows, result = run_households(worker, python, updates)
    if result.installation != installation:
        raise ValueError("policyengine-us changed during the run")
    float32_guard(rows, python)
    checks = check_invariants(rows)
    limits_document = yaml.safe_load(
        (parameter_root / MEDICAID_LIMIT_FILE).read_text()
    )
    limits = {
        state: _dated_value(limits_document[state], f"{PAYMENT_YEAR}-01-01")
        for state in STATES
    }
    explanations = medicaid_explanations(rows, limits)
    code_paths = ["src", "scripts", "tests"]
    pe_provenance["parameter_updates"] = [dict(update) for update in updates]
    provenance = {
        "microcosm_dynamics": {
            "repository": "PolicyEngine/microcosm-dynamics",
            "commit": _git(ROOT, "rev-parse", "HEAD"),
            "code_dirty": bool(
                _git(ROOT, "status", "--porcelain", "--", *code_paths)
            ),
            "script": "scripts/pe_us_minimum_benefit_sample_households.py",
            "bridge": "src/populace_dynamics/bridge/policyengine_us.py",
        },
        "policyengine_us": pe_provenance,
        "payment_year": PAYMENT_YEAR,
    }
    caveats = [
        "Illustrative households, not survey data: one worker, chosen so "
        "the minimum binds, in three living situations.",
        "The bridge passes Microcosm's Social Security amounts to "
        "PolicyEngine-US as inputs; it does not run over the projected "
        "population and applies no behavioral response.",
        f"The reform is {reform_name(worker)}: exercise 4's headline "
        "option, the standard price-indexed minimum with its printed 12.81 "
        "percent uniform cut for new entitlees. The worker is on the "
        "minimum, so the cut does not reach her; a worker above the minimum "
        "would lose 12.81 percent.",
        "The baseline is current-law scheduled benefits. Against option 1 "
        "(reduced current law, the Report's own benchmark) her gain would "
        "be larger; that PIA is in the JSON as a memo, not run through "
        "PolicyEngine-US.",
        "Net income is PolicyEngine-US's household_net_income, which by "
        "default excludes health coverage (Medicaid at cost, Medicare "
        "Savings Programs); the with-health sensitivity and the memo lines "
        "report it. Medicaid is valued at its average cost per enrollee, an "
        "upper-end valuation of coverage, not a cash loss.",
        *_release_caveats(parameter_root),
        *[
            f"{STATES[update['states'][0]]['name']}'s {update['year']} aged "
            "or disabled payment standard is set to the published "
            f"${update['value']:,.2f} a month ({update['source']['publisher']}"
            f", {update['source']['title']}, {update['source']['revision']})"
            f"; policyengine-us {PE_US_RELEASE['version']} has no "
            f"{update['year']} entry and would hold "
            f"${update['installed_value']:,.2f} from "
            f"{update['installed_value_dated']}."
            for update in updates
        ],
        "COLAs for 2023-2025 are derived from policyengine-us 2.18.0's "
        "third-quarter CPI-W averages under 42 USC 415(i)(1)(D); the "
        "derived 2022 COLA equals the committed SSA history's.",
        "Household C's pension is $31,200, clear of every bracket and "
        "eligibility edge on her path. At a round $30,000, California AGI "
        "sat on the $30,000 edge of the use-tax table and float32 noise "
        "moved the use tax by $1; the float32 guard now refuses such a run.",
    ]
    reform = reform_name(worker)
    guard = _guard_summary(rows)
    document = {
        "schema_version": SCHEMA_VERSION,
        "label": ILLUSTRATIVE_LABEL,
        "reform": reform,
        "provenance": provenance,
        "worker": worker,
        "households": [dict(spec) for spec in HOUSEHOLDS],
        "states": STATES,
        "common_inputs": {
            "monthly_rent": MONTHLY_RENT,
            "bank_account_assets": BANK_ACCOUNT_ASSETS,
            "has_heating_cooling_expense": True,
            "takes_up_housing_assistance_if_eligible": False,
            "living_arrangements_allow_for_food_preparation": True,
            "medicare_quarters_of_coverage": 4
            * worker["years_of_coverage"]["years"],
        },
        "net_income_tree": {
            name: [list(part) for part in parts]
            for name, parts in rows[0]["tree"].children.items()
        },
        "table_rows": table_categories(rows),
        "chart_rows": chart_categories(rows),
        "results": [_serialize_row(row) for row in rows],
        "medicaid_explanations": {
            f"{key}-{state}": text
            for (key, state), text in explanations.items()
        },
        "float32_guard": guard,
        "invariants_checked": checks,
        "caveats": caveats,
    }
    _no_absolute_paths(document)
    return document, rows, explanations


def write(
    document: dict[str, Any],
    rows: list[dict[str, Any]],
    explanations: dict[tuple[str, str], str],
    directory: Path,
) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    written = []
    json_path = directory / f"{OUTPUT_STEM}.json"
    json_path.write_text(
        json.dumps(document, indent=2, sort_keys=False) + "\n"
    )
    written.append(json_path)
    view = dict(document, medicaid_explanations=explanations)
    md_path = directory / f"{OUTPUT_STEM}.md"
    md_path.write_text(markdown(rows, view))
    written.append(md_path)
    for spec in HOUSEHOLDS:
        stem = directory / f"household_{spec['key'].lower()}_waterfall"
        written += draw_chart(rows, spec, view, stem)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--docs-dir", type=Path, default=DEFAULT_DOCS_DIR)
    parser.add_argument(
        "--pe-us-python",
        default=None,
        help=f"interpreter with policyengine-us (else ${bridge.PE_US_PYTHON_ENV})",
    )
    args = parser.parse_args(argv)
    document, rows, explanations = build(args.pe_us_python)
    for directory in (args.out_dir, args.docs_dir):
        for path in write(document, rows, explanations, directory):
            print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
