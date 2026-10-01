"""PolicyEngine-US over an INVENTED population: exercise 4's minimum benefit.

INVENTED DATA - NOT A COMPARISON, NOT THE US.  Nothing here opens a PSID
file, a projection or a comparator value.  The population is invented by
design until the registered real-data analysis exists (cos decision d727,
under Max's d479: "Development checks use invented cases").

For each population size (300 and 3,000 family units by default):

1. **Track M.**  ``invented_psid``'s seeded PSID-shaped frames run through the
   M4 cohort and M5 careers with provenance ``invented``, and Track M's
   rules evaluate every record under row MS0
   (:mod:`populace_dynamics.bridge.invented_population`, which refuses any
   other provenance before ``evaluate`` runs).  Each person's 2026 benefit
   under current law and under option 2 follows from the PIAs, carried
   forward with statutory COLAs as the bridge carries them.
2. **Invented inputs.**  State, rent, assets and income other than Social
   Security are drawn from documented, seeded, INVENTED distributions
   (``invented_population.INVENTED_DISTRIBUTIONS``) and mapped to
   PolicyEngine-US inputs by ``estimates.adjusted_poverty``'s conventions
   (``INPUT_CONCEPTS``).
3. **One weighted simulation per scenario.**  The families become
   PolicyEngine-US households (:class:`~populace_dynamics.bridge.population.
   PopulationFrame`), and each scenario runs as one ``Microsimulation``
   over the whole population (:func:`~populace_dynamics.bridge.population.
   run_population`), with health coverage outside net income (the
   default) and inside it (a sensitivity).  The runs use policyengine-us
   2.18.0 from PyPI with the bridge's pin and California's 2026 SSI
   payment standard, as the sample-household script applies them.
4. **Outputs.**  Every household's change in ``household_net_income`` is
   split into leaves that sum exactly to it; weighted totals by leaf,
   category and level of government; the share of the Social Security
   change taken back; distributions by SSI status and income decile; the
   federal and state cost of Medicaid, CHIP and the Medicare Savings
   Programs; runtime and memory.  JSON, Markdown and a stacked-bar chart
   per size go to ``--docs-dir``.

Run from the repository root::

    POPULACE_DYNAMICS_PE_US_PYTHON=~/.venvs/policyengine-us-2.18.0/bin/python \\
    OMP_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python \\
        scripts/pe_us_population_invented.py
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import platform
import sys
import textwrap
import time
from collections import Counter
from fractions import Fraction
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402

from populace_dynamics.bridge import (  # noqa: E402
    invented_population as invented,
)
from populace_dynamics.bridge import policyengine_us as bridge  # noqa: E402
from populace_dynamics.bridge import population as pop  # noqa: E402
from populace_dynamics.bridge import (  # noqa: E402
    population_summary as summary,
)
from populace_dynamics.estimates.parameters import (  # noqa: E402
    load_cola_history,
)
from populace_dynamics.min_benefit_track_m import (  # noqa: E402
    coverage,
    rules,
)
from populace_dynamics.min_benefit_track_m.evaluation import (  # noqa: E402
    TrackMParameters,
)
from populace_dynamics.min_benefit_track_m.policy import (  # noqa: E402
    OPTIONS,
)
from populace_dynamics.ss.params import load_ssa_parameters  # noqa: E402


def _sample_script():
    """The sample-household script: its release pin, parameter updates,
    COLAs and provenance helpers, reused unchanged."""

    name = "pe_us_minimum_benefit_sample_households"
    if name in sys.modules:
        return sys.modules[name]
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


sample = _sample_script()

SCHEMA_VERSION = "pe_us_bridge.population_invented.v1"
LABEL = invented.INVENTED_POPULATION_LABEL
PAYMENT_YEAR = invented.PAYMENT_YEAR
DEFAULT_SEED = 20260930
DEFAULT_SIZES = (300, 3_000)
DEFAULT_DOCS_DIR = (
    ROOT / "docs" / "analysis" / "pe_us_population_invented_20260930"
)
OUTPUT_STEM = "pe_us_population_invented"
BASELINE, REFORM = invented.SIMULATED_SCENARIOS
VARIANTS = ("default", "with_health")
#: Stated bounds on each size's run, checked before writing and by the
#: scale test: wall-clock seconds of the whole policyengine-us child (import,
#: source checks, four simulations) and its peak resident memory.  Set
#: with ample room over the measured runs (see the committed JSON's
#: ``scale``), since the machine's load moves the time.
SCALE_BOUNDS: dict[int, dict[str, float]] = {
    300: {"pe_wall_seconds": 1_200.0, "peak_rss_bytes": 8 * 2**30},
    3_000: {"pe_wall_seconds": 2_400.0, "peak_rss_bytes": 12 * 2**30},
}
#: The household-level memo variables: the baseline decile and the
#: weights and sizes it is computed from (``household_income_decile.py``).
HOUSEHOLD_MEMO = (
    "household_income_decile",
    "household_weight",
    "household_count_people",
)
RUN_TIMEOUT_SECONDS = 7_200.0


# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------
def parameter_overrides(updates: list[dict[str, Any]]) -> dict[str, Any]:
    """The sample script's updates as one population-wide override set.

    The bridge applies each update to its states' cases only.  One
    simulation holds every state, so an update applies to all of it; each
    must therefore be a parameter of its own states' namespace
    (``gov.states.<state>.``), which no other state reads.  Refuses one
    that is not.
    """

    overrides = {}
    for update in updates:
        prefixes = [f"gov.states.{s.lower()}." for s in update["states"]]
        if not all(update["parameter"].startswith(p) for p in prefixes):
            raise ValueError(
                f"{update['parameter']} is not in the namespace of "
                f"{update['states']} and would reach other states"
            )
        overrides[update["parameter"]] = update["value"]
    return overrides


def track_m_parameters(parameter_root: Path) -> TrackMParameters:
    """The oracle's parameters from the pinned release, the committed QC
    amounts and the pinned Census thresholds."""

    return TrackMParameters(
        load_ssa_parameters(parameter_root),
        coverage.load_qc_amounts(),
        rules.load_aged_thresholds(),
    )


# ---------------------------------------------------------------------------
# One size
# ---------------------------------------------------------------------------
def chart_series(leaf: tuple[str, tuple[str, ...], int, str, str | None]):
    """The chart's series of a leaf (name, path, sign, category, level).

    Social Security and SSI are their own series; every other federal,
    state or local leaf is a benefit or a tax (or credit) of its level.
    Health and market-income leaves are ``"other"``, which the chart
    refuses to drop if one changes (:func:`chart_values`).
    """

    _, _, _, category, level = leaf
    if category == "social_security":
        return "social_security"
    if category == "ssi":
        return "ssi"
    taxes = {
        "federal_income_tax",
        "federal_refundable_credits",
        "state_income_tax",
        "state_refundable_credits",
        "other_taxes",
    }
    if level == "federal":
        return "federal_taxes" if category in taxes else "federal_benefits"
    if level == "state":
        return "state_local_taxes" if category in taxes else "state_benefits"
    if level == "local":
        return "state_local_taxes"
    return "other"


CHART_SERIES = (
    ("social_security", "Social Security"),
    ("ssi", "SSI"),
    ("federal_benefits", "SNAP and other federal benefits"),
    ("federal_taxes", "Federal income and payroll taxes, credits"),
    ("state_benefits", "State benefits, incl. SSI supplements"),
    ("state_local_taxes", "State and local taxes, credits"),
)


def social_security_check(
    decomposition: pop.PopulationDecomposition,
    frames: dict[str, pop.PopulationFrame],
) -> dict[str, Any]:
    """PolicyEngine-US's ``social_security`` leaf equals the Track M side.

    A differential check, per household and scenario: the leaf (cents) is
    the household's sum of the three Social Security inputs.
    """

    for scenario, cents in (
        (BASELINE, decomposition.baseline_cents),
        (REFORM, decomposition.reform_cents),
    ):
        frame = frames[scenario]
        expected = np.zeros(frame.n_households, dtype=np.int64)
        for name in (
            "social_security_retirement",
            "social_security_disability",
            "social_security_survivors",
            "social_security_dependents",
        ):
            np.add.at(
                expected,
                frame.units["household"],
                pop.to_cents_array(frame.amounts[name]),
            )
        got = np.zeros(frame.n_households, dtype=np.int64)
        for j, leaf in enumerate(decomposition.leaves):
            if leaf[0] == "social_security":
                got += leaf[2] * cents[j]
        if not np.array_equal(got, expected):
            bad = np.flatnonzero(got != expected)
            raise AssertionError(
                f"{scenario}: social_security differs from the Track M "
                f"inputs in households {bad[:10].tolist()}"
            )
    return {"households_checked": decomposition.n_households, "equal": True}


def household_checks(
    decomposition: pop.PopulationDecomposition,
    states: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Separability and direction, household by household.

    * A household whose Social Security does not change must not change
      at all: nothing else differs between the scenarios, so a change
      would be one household's result leaking into another's (a
      population-level formula).  Refused.
    * Where Social Security changes, each means-tested benefit, income tax
      and refundable credit (the sample script's ``WRONG_WAY_CATEGORIES``)
      should move against it or not at all.  Recorded, not refused: a
      program's rules can move either way.
    * Leaves that change by a nonzero amount under $2 (the bridge's
      ``small_changes`` threshold), where a float32 step at a bracket
      edge would show.  Recorded.
    """

    n = decomposition.n_households
    ss = np.zeros(n, dtype=np.int64)
    any_change = np.zeros(n, dtype=bool)
    by_category: dict[str, np.ndarray] = {}
    for j, leaf in enumerate(decomposition.leaves):
        change = decomposition.change_cents(j)
        any_change |= change != 0
        if leaf[0] == "social_security":
            ss += change
        by_category[leaf[3]] = by_category.get(leaf[3], 0) + change
    leaked = np.flatnonzero((ss == 0) & any_change)
    if len(leaked):
        raise AssertionError(
            f"households {leaked[:10].tolist()} change although their Social "
            "Security does not"
        )
    wrong = []
    for category in sample.WRONG_WAY_CATEGORIES:
        change = by_category.get(category)
        if change is None:
            continue
        against = np.sign(change) * np.sign(ss)
        for h in np.flatnonzero(against > 0).tolist():
            wrong.append(
                {
                    "household": h,
                    "state": states[h] if states is not None else None,
                    "category": category,
                    "social_security_change": int(ss[h]) / 100,
                    "category_change": int(change[h]) / 100,
                }
            )
    small = 0
    for j in range(len(decomposition.leaves)):
        change = np.abs(decomposition.change_cents(j))
        small += int(
            ((change > 0) & (change < bridge.SMALL_CHANGE_CENTS)).sum()
        )
    return {
        "unchanged_social_security_households": int((ss == 0).sum()),
        "unchanged_social_security_households_that_change": 0,
        "wrong_way_changes": len(wrong),
        "wrong_way_by_state": dict(
            sorted(Counter(w["state"] for w in wrong).items())
        ),
        "wrong_way_cases": wrong,
        "small_leaf_changes": small,
    }


def _timed(label: str, timings: dict[str, float], call):
    started = time.perf_counter()
    value = call()
    timings[label] = time.perf_counter() - started
    return value


def run_size(
    n_family_units: int,
    *,
    seed: int,
    python: str | None,
    context: dict[str, Any],
    timeout: float = RUN_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Everything for one population size (module docstring, 1-4)."""

    timings: dict[str, float] = {}
    parameters = context["track_m"]
    cohort = _timed(
        "track_m_cohort_seconds",
        timings,
        lambda: invented.build_invented_cohort(
            seed=seed,
            n_family_units=n_family_units,
            params=parameters.params,
            cola_rates=context["cola_history"],
        ),
    )
    result = _timed(
        "track_m_evaluate_seconds",
        timings,
        lambda: invented.evaluate_headline(cohort.inputs, parameters),
    )
    benefit_table = _timed(
        "benefits_seconds",
        timings,
        lambda: invented.person_benefits(
            cohort.inputs,
            result,
            parameters,
            context["cola_rates"],
            persons=cohort.cohort.persons,
        ),
    )
    population = _timed(
        "population_seconds",
        timings,
        lambda: invented.build_population(cohort, benefit_table, seed=seed),
    )
    frames = dict(population.frames)
    run = pop.run_population(
        frames,
        year=PAYMENT_YEAR,
        variants={
            "default": context["overrides"],
            "with_health": {
                **context["overrides"],
                **sample.HEALTH_OVERRIDE,
            },
        },
        person_memo=summary.HEALTH_MEMO,
        household_memo=HOUSEHOLD_MEMO,
        python=python,
        timeout=timeout,
        expected_package_record_digest=sample.PE_US_RELEASE[
            "package_record_digest"
        ],
    )
    if run.installation != context["installation"]:
        raise ValueError("policyengine-us changed during the run")
    decompositions = {
        variant: pop.decompose_population(
            run.trees[variant],
            run.values[variant][BASELINE],
            run.values[variant][REFORM],
            reform_tree=run.trees[variant],
        )
        for variant in VARIANTS
    }
    frame = frames[BASELINE]
    people = np.bincount(frame.units["household"])
    default = decompositions["default"]
    memo = run.household_memo["default"][BASELINE]
    deciles = memo["household_income_decile"].astype(np.int64)
    recomputed = pop.decile_ranks(
        default.reported_baseline_net,
        memo["household_weight"] * memo["household_count_people"],
    )
    decile_mismatches = int((recomputed != deciles).sum())
    if decile_mismatches:
        raise AssertionError(
            f"{decile_mismatches} households' deciles differ from "
            "policyengine-us's household_income_decile"
        )
    groupings = {
        "ssi_status": (
            summary.ssi_status(default),
            summary.SSI_STATUS_ORDER,
        ),
        "income_decile": (
            np.asarray([str(d) for d in deciles.tolist()], dtype=object),
            tuple(str(d) for d in (-1, *range(1, 11))),
        ),
        "social_security_direction": (
            summary.social_security_direction(default),
            summary.DIRECTION_ORDER,
        ),
    }
    summaries = {
        variant: summary.summarize(
            decompositions[variant],
            frame.weight,
            people,
            groupings if variant == "default" else None,
        )
        for variant in VARIANTS
    }
    checks = {
        "social_security_equals_track_m": social_security_check(
            default, frames
        ),
        "households": {
            variant: household_checks(decompositions[variant], frame.state)
            for variant in VARIANTS
        },
        "deciles_match_policyengine_us": {
            "households": int(len(deciles)),
            "mismatches": decile_mismatches,
        },
    }
    person_weights = frame.weight[frame.units["household"]]
    health = summary.health_split(
        run.person_memo["default"], person_weights, (BASELINE, REFORM)
    )
    bounds = SCALE_BOUNDS.get(n_family_units)
    scale = {
        "family_units": n_family_units,
        "households": frame.n_households,
        "people": frame.n_people,
        "track_m_and_population_seconds": timings,
        "pe_wall_seconds": run.wall_seconds,
        "pe_import_seconds": run.import_seconds,
        "pe_simulations": {
            variant: {
                scenario: {
                    key: value
                    for key, value in run.timings[variant][scenario].items()
                }
                for scenario in (BASELINE, REFORM)
            }
            for variant in VARIANTS
        },
        "peak_rss_bytes": run.peak_rss_bytes,
        "peak_rss_gib": run.peak_rss_bytes / 2**30,
        "bounds": bounds,
        "within_bounds": (
            None
            if bounds is None
            else run.wall_seconds <= bounds["pe_wall_seconds"]
            and run.peak_rss_bytes <= bounds["peak_rss_bytes"]
        ),
    }
    if scale["within_bounds"] is False:
        raise AssertionError(f"{n_family_units} units: outside bounds {scale}")
    benefits = {
        scenario: {
            "annual_social_security_weighted": summary.dollars(
                pop.ExactWeights.from_floats(person_weights).dollars(
                    pop.to_cents_array(
                        population.people[f"{scenario}__social_security"]
                    )
                )
            ),
        }
        for scenario in invented.BENEFIT_SCENARIOS
    }
    counts = {
        "persons_in_window": int(benefit_table["exposed"].sum()),
        "persons_receiving_minimum_option_2": int(
            benefit_table["receives_2"].sum()
        ),
        "own_records_on_minimum_option_2": int(
            benefit_table["own_on_minimum"].sum()
        ),
        "persons_whose_social_security_rises": int(
            (
                benefit_table["option_2__social_security"]
                > benefit_table["current_law__social_security"]
            ).sum()
        ),
        "persons_whose_social_security_falls": int(
            (
                benefit_table["option_2__social_security"]
                < benefit_table["current_law__social_security"]
            ).sum()
        ),
        "unlinked_auxiliaries": int(benefit_table["unlinked_auxiliary"].sum()),
        "own_benefits_from_observed_2022_amount": int(
            (
                benefit_table["own_benefit_source"] == "observed_2022_amount"
            ).sum()
        ),
    }
    changed_leaves = {
        variant: sorted(
            {
                decompositions[variant].leaves[j][0]
                for j in decompositions[variant].changed_leaves()
            }
        )
        for variant in VARIANTS
    }
    return {
        "family_units": n_family_units,
        "seed": seed,
        "label": LABEL,
        "track_m": {
            "row": invented.HEADLINE_ROW,
            "counts": counts,
            "diagnostics": _json_safe(result.diagnostics),
            "social_security_by_scenario": benefits,
            "invented_generator": dict(cohort.frames.provenance),
        },
        "households": {
            "count": frame.n_households,
            "people": frame.n_people,
            "states": len(set(frame.state)),
            "renters": int(population.households["renter"].sum()),
        },
        "results": {
            "default": summaries["default"],
            "with_health": summaries["with_health"]["population"],
        },
        "changed_leaves": changed_leaves,
        "health_split": health,
        "checks": checks,
        "scale": scale,
        "_internal": {
            "decompositions": decompositions,
            "groupings": groupings,
            "frame": frame,
        },
    }


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


# ---------------------------------------------------------------------------
# The whole run
# ---------------------------------------------------------------------------
def build(
    sizes: tuple[int, ...],
    *,
    seed: int,
    python: str | None,
    timeout: float = RUN_TIMEOUT_SECONDS,
) -> tuple[dict[str, Any], dict[int, dict[str, Any]]]:
    installation, pe_provenance = sample.pinned_release(python)
    parameter_root = Path(installation.location)
    updates = sample.parameter_updates(parameter_root)
    rates, cola_provenance = sample.cola_rates(PAYMENT_YEAR, parameter_root)
    context = {
        "installation": installation,
        "overrides": parameter_overrides(updates),
        "cola_rates": rates,
        "cola_history": load_cola_history(),
        "track_m": track_m_parameters(parameter_root),
    }
    runs = {
        size: run_size(
            size, seed=seed, python=python, context=context, timeout=timeout
        )
        for size in sizes
    }
    pe_provenance["parameter_updates"] = [dict(u) for u in updates]
    pe_provenance["population_overrides"] = context["overrides"]
    option = OPTIONS[invented.HEADLINE_OPTION]
    document = {
        "schema_version": SCHEMA_VERSION,
        "label": LABEL,
        "phase0": "permitted",
        "phase0_reasoning": "option A: invented data only, per d479",
        "reform": (
            f"Exercise 4's headline option: option {option.number}, "
            f"{option.label.lower()} (Favreault, Mermin and Steuerle 2006), "
            f"with its {option.uniform_cut:.2%} uniform cut, against "
            "current-law benefits (the PIA with no cut), under Track M row "
            f"{invented.HEADLINE_ROW}"
        ),
        "provenance": {
            "microcosm_dynamics": {
                "repository": "PolicyEngine/microcosm-dynamics",
                "commit": sample._git(ROOT, "rev-parse", "HEAD"),
                "code_dirty": bool(
                    sample._git(
                        ROOT, "status", "--porcelain", "--", "src", "scripts"
                    )
                ),
                "script": "scripts/pe_us_population_invented.py",
                "modules": [
                    "src/populace_dynamics/bridge/population.py",
                    "src/populace_dynamics/bridge/population_summary.py",
                    "src/populace_dynamics/bridge/invented_population.py",
                ],
            },
            "policyengine_us": pe_provenance,
            "payment_year": PAYMENT_YEAR,
            "cola": cola_provenance,
            "track_m_parameters": {
                "ssa": (
                    "policyengine_us/parameters/gov/ssa in the pinned "
                    "policyengine-us release"
                ),
                "quarter_of_coverage": dict(context["track_m"].qc.source),
                "thresholds": dict(context["track_m"].thresholds.source),
            },
            "python": platform.python_version(),
        },
        "invented_inputs": {
            "distributions": invented.INVENTED_DISTRIBUTIONS,
            "input_concepts": list(invented.INPUT_CONCEPTS),
            "stream": [seed, invented.OTHER_INPUTS_STREAM],
            "flags": {
                "has_heating_cooling_expense": True,
                "takes_up_housing_assistance_if_eligible": False,
                "living_arrangements_allow_for_food_preparation": True,
            },
        },
        "method": {
            "source_references": {
                "invented-only guard": (
                    "src/populace_dynamics/bridge/invented_population.py:296"
                ),
                "cohort and careers": (
                    "src/populace_dynamics/bridge/invented_population.py:271"
                ),
                "benefit carry and auxiliary mapping": (
                    "src/populace_dynamics/bridge/invented_population.py:384"
                ),
                "invented distributions and income conventions": (
                    "src/populace_dynamics/bridge/invented_population.py:140"
                ),
                "family-to-household mapper": (
                    "src/populace_dynamics/bridge/invented_population.py:609"
                ),
                "release pin and California override": (
                    "scripts/pe_us_minimum_benefit_sample_households.py:407"
                ),
                "dataset layout": (
                    "src/populace_dynamics/bridge/population.py:616; "
                    "policyengine_core/simulations/simulation.py:405"
                ),
                "one simulation per scenario": (
                    "src/populace_dynamics/bridge/population.py:980"
                ),
                "household Medicaid valuation": (
                    "src/populace_dynamics/bridge/population.py:919"
                ),
                "income deciles": (
                    "policyengine_us/variables/household/income/household/"
                    "household_income_decile.py:12"
                ),
                "exact weighted decomposition": (
                    "src/populace_dynamics/bridge/population_summary.py:310"
                ),
                "take-back by government level": (
                    "src/populace_dynamics/bridge/population_summary.py:122"
                ),
                "health federal/state cost split": (
                    "src/populace_dynamics/bridge/population_summary.py:365"
                ),
                "uniform cut and minimum": (
                    "src/populace_dynamics/min_benefit_track_m/rules.py:358"
                ),
            },
            "simulation": (
                "One policyengine-us Microsimulation per scenario and "
                "variant over the whole population, from a policyengine-core "
                "Dataset in the TIME_PERIOD_ARRAYS layout"
            ),
            "medicaid_valuation": (
                "household: medicaid_slcsp_state_average_cost_index and "
                "medicaid_slcsp_state_denominator pinned to each household's "
                "single-household values, so no household's result depends "
                "on the rest of the population"
            ),
            "deciles": (
                "policyengine-us's household_income_decile from the baseline "
                "simulation (person-weighted net income; -1 for negative "
                "income), recomputed here and checked equal"
            ),
            "take_back": summary.__doc__.split("\n\n")[1].replace("\n", " "),
        },
        "sizes": {
            str(size): {k: v for k, v in run.items() if k != "_internal"}
            for size, run in runs.items()
        },
        "caveats": caveats(parameter_root, updates),
    }
    document = _json_safe(document)
    sample._no_absolute_paths(document)
    return document, runs


def release_caveats(parameter_root: Path) -> list[str]:
    """Caveats whose amounts are read from the pinned release.

    The sample script's own caveats name its three states; these name the
    whole population's.
    """

    fy27 = f"{PAYMENT_YEAR}-10-01"
    snap = "gov/usda/snap/"
    allotment = sample._parameter(
        parameter_root,
        snap + "max_allotment.yaml",
        "main",
        "CONTIGUOUS_US",
        1,
        on=fy27,
    )
    deduction = sample._parameter(
        parameter_root,
        snap + "income/deductions/standard.yaml",
        "CONTIGUOUS_US",
        1,
        on=fy27,
    )
    csfp = sample._parameter(
        parameter_root, "gov/usda/csfp/amount.yaml", on=f"{PAYMENT_YEAR}-01-01"
    )
    main = (
        parameter_root
        / sample.PARAMETER_PREFIX
        / (snap + "income/deductions/utility/standard/main.yaml")
    )
    if fy27 in main.read_text():
        raise ValueError(
            "the standard utility allowances now have fiscal-2027 entries; "
            "revise this caveat"
        )
    version = sample.PE_US_RELEASE["version"]
    return [
        "SNAP for October-December 2026 uses USDA's fiscal-2027 maximum "
        f"allotment (${allotment:,.0f} a month for one person in the "
        f"contiguous states) and standard deduction (${deduction:,.0f}) as "
        f"policyengine-us {version} encodes them "
        "(gov/usda/snap/max_allotment.yaml:33, "
        "income/deductions/standard.yaml:17). No state's standard utility "
        "allowance has a fiscal-2027 entry there "
        "(income/deductions/utility/standard/main.yaml has none dated "
        f"{fy27}), so those months use each state's fiscal-2026 amount.",
        f"In policyengine-us {version} SNAP counts California's SSI "
        "supplement as unearned income "
        "(gov/usda/snap/income/sources/unearned_spm_unit.yaml:13).",
        "Take-up is PolicyEngine-US's default: full for SSI, SNAP and "
        "Medicaid (takes_up_ssi_if_eligible.py:9, "
        "takes_up_snap_if_eligible.py:9, takes_up_medicaid_if_eligible.py:9"
        "). The Commodity Supplemental Food Program has no take-up input: "
        "every eligible person gets USDA's cost per caseload slot, "
        f"${csfp:,.0f} in {PAYMENT_YEAR} "
        "(commodity_supplemental_food_program.py:10-11, "
        "gov/usda/csfp/amount.yaml:11), though the program is "
        "caseload-limited and serves far fewer people than are eligible; "
        "its change here is a notch at 150 percent of the poverty "
        "guideline. As in the bridge, housing-voucher take-up is switched "
        "off (vouchers are rationed), and every household pays heating or "
        "cooling costs and can prepare food at home.",
    ]


def caveats(parameter_root: Path, updates: list[dict[str, Any]]) -> list[str]:
    return [
        f"{LABEL}. Every person, family, weight, state, income, asset and "
        "rent amount is invented; the totals describe that invented "
        "population and nothing else. They are not estimates for the US, "
        "not a comparison with DYNASIM3 and not a registered result.",
        "The population is invented by design until the registered "
        "real-data analysis (cos decision d727, under Max's d479).",
        "Social Security amounts come from Track M's rules on invented "
        "records (row MS0), carried to 2026 with statutory COLAs as the "
        "bridge carries them. Every own worker benefit enters as "
        "social_security_retirement, spouse's excesses as "
        "social_security_dependents and widow(er)'s excesses as "
        "social_security_survivors; a disability-origin record's benefit "
        "is not entered as disability benefits (a mapping choice; everyone "
        "is 66 or older in 2026, so aged for SSI and Medicare either way).",
        "Two groups keep their invented 2022 amount, carried by the COLAs, "
        "in both scenarios, because Track M computes no benefit for them: "
        "unlinked auxiliaries, and people paid an own benefit whose "
        "records hold no observed covered earnings (the invented "
        "generator, like the PSID panel, has labor income for reference "
        "persons and spouses only). The reform cannot reach them here.",
        "The reform cuts every in-window PIA by the option's uniform cut "
        "unless the minimum is higher, so most in-window people lose "
        "against current-law benefits; the share taken back therefore "
        "mostly measures how much of a cut other programs and taxes "
        "cushion. The groupings split rises from falls.",
        "Each family unit is one household, SPM unit and family. The "
        "reference person and spouse form one marital unit and file one "
        "joint return; any other member is a single filer in a marital unit "
        "of their own, never a dependent. Medicare quarters of coverage are "
        "policyengine-us's default of 40 for everyone, since every person "
        "receives OASDI.",
        "Default net income excludes health coverage. The with-health "
        "sensitivity counts Medicaid at the release's state spending over "
        "enrollment per enrollee (as for one household alone), not "
        "policyengine-us's dataset allocation of each state's calibrated "
        "spending across the simulated enrollees, which is meaningless for "
        "an invented population.",
        "No behavioral, claiming or take-up response to the reform. No "
        "float32 trace guard runs over the population (the bridge traces "
        "one household at a time); leaf changes under $2 are counted "
        "instead.",
        "Where Social Security changes, a means-tested benefit, income tax "
        "or refundable credit that moves the same way is recorded, not "
        "refused: some are mechanisms (Alabama deducts federal income tax, "
        "so a lower federal tax raises Alabama's), and the JSON lists every "
        "case with its state.",
        *release_caveats(parameter_root),
        *[
            f"{sample.STATES[u['states'][0]]['name']}'s {u['year']} aged or "
            "disabled payment standard is set to the published "
            f"${u['value']:,.2f} a month for the whole population "
            f"(policyengine-us {sample.PE_US_RELEASE['version']} holds "
            f"${u['installed_value']:,.2f} from "
            f"{u['installed_value_dated']}). Only {u['states'][0]}'s "
            "households read it: every variable that reads the parameter is "
            "under variables/gov/states/ca/ (ca_state_supplement is defined "
            "for California only, ca_state_supplement.py:10)."
            for u in updates
        ],
    ]


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------
def _money(value: float, *, signed: bool = False) -> str:
    return sample._money(round(value * 100), signed=signed)


def _share(value: float | None, mixed: bool = False) -> str:
    if value is None:
        return "n/a"
    return f"{100 * value:.1f}%" + (" \u2020" if mixed else "")


LEVEL_ROWS = ("federal", "state", "local")


def _distribution_text(spec: dict[str, Any]) -> str:
    """One invented distribution in words (its keys, in order)."""

    parts = []
    probability = spec.get("probability")
    if isinstance(probability, dict):
        parts.append(
            "drawn with probability "
            + ", ".join(f"{p:g} ({role})" for role, p in probability.items())
        )
    elif probability is not None:
        parts.append(f"drawn with probability {probability:g}")
    if "low_probability" in spec:
        parts.append(
            f"with probability {spec['low_probability']:g} uniform on "
            f"$0-${spec['low_uniform_max']:,.0f}"
        )
    if "median" in spec:
        parts.append(
            ("otherwise " if "low_probability" in spec else "")
            + f"lognormal, median ${spec['median']:,.0f}, "
            f"log sigma {spec['sigma']:g}"
        )
    if "rule" in spec:
        parts.append(spec["rule"])
    return "; ".join(parts) + f" (per {spec['unit']})"


def invented_inputs_markdown(inputs: dict[str, Any]) -> list[str]:
    """The invented inputs, each labelled, and how each enters the model."""

    lines = [
        "## Invented inputs",
        "",
        "The invented generator draws no state, income other than Social "
        "Security, assets or rent. Each is drawn here from the distribution "
        "below (seed stream "
        f"{inputs['stream']}), rounded to the dollar. None is a survey, "
        "Census or program value.",
        "",
        "| Item | Label | Distribution |",
        "|---|---|---|",
    ]
    for item, spec in inputs["distributions"].items():
        lines.append(
            f"| `{item}` | {spec['label']} | {_distribution_text(spec)} |"
        )
    lines += [
        "",
        "| Invented item | PolicyEngine-US input | Label | Convention |",
        "|---|---|---|---|",
    ]
    for concept in inputs["input_concepts"]:
        lines.append(
            f"| {concept['item']} | `{concept['input']}` | "
            f"{concept['label']} | {concept['convention']} |"
        )
    flags = ", ".join(
        f"`{name}` = {value}" for name, value in inputs["flags"].items()
    )
    lines += ["", f"Flags set for every household: {flags}.", ""]
    return lines


def markdown(document: dict[str, Any]) -> str:
    lines = [
        f"# {LABEL}",
        "",
        "PolicyEngine-US over an invented population: exercise 4's headline "
        "minimum benefit",
        "",
        f"**{LABEL}.** {document['reform']}. Payment year "
        f"{document['provenance']['payment_year']}; annual dollars, "
        "weighted by the invented household weights.",
        "",
        "Code: `scripts/pe_us_population_invented.py`, "
        "`src/populace_dynamics/bridge/population.py`. Design: "
        "`docs/design/pe_us_population_run.md`.",
        "",
        f"Phase 0: **{document['phase0']}** — "
        f"{document['phase0_reasoning']}.",
        "",
        "Mechanism references below use repository-relative paths; "
        "`policyengine_us/` and `policyengine_core/` paths refer to the "
        "pinned interpreter's installed source.",
        "",
        "| Mechanism | Source (file:line) |",
        "|---|---|",
    ]
    for mechanism, source in document["method"]["source_references"].items():
        lines.append(f"| {mechanism} | `{source}` |")
    lines += [
        "",
        "Dollar tables are rounded for display. JSON's `*_exact` fields "
        "preserve rational dollar totals for the exact identities; "
        "independently rounded entries can differ by cents when added "
        "(`population_summary.py:61-73,264-302`).",
        "",
    ]
    for size, run in document["sizes"].items():
        result = run["results"]["default"]["population"]
        health = run["results"]["with_health"]
        counts = run["track_m"]["counts"]
        lines += [
            f"## {int(size):,} invented family units ({LABEL})",
            "",
            f"{run['households']['count']:,} households, "
            f"{run['households']['people']:,} people, "
            f"{run['households']['states']} states; weighted "
            f"{result['weighted_households']:,.0f} households and "
            f"{result['weighted_people']:,.0f} people (invented weights).",
            "",
            f"Track M (row {run['track_m']['row']}): "
            f"{counts['persons_in_window']:,} people have an own or linked "
            "worker record in the policy window; "
            f"{counts['persons_receiving_minimum_option_2']:,} receive the "
            "minimum under option 2; Social Security rises for "
            f"{counts['persons_whose_social_security_rises']:,} people and "
            f"falls for {counts['persons_whose_social_security_falls']:,}. "
            f"{counts['unlinked_auxiliaries']:,} unlinked auxiliaries and "
            f"{counts['own_benefits_from_observed_2022_amount']:,} people "
            "whose records hold no observed covered earnings keep their 2022 "
            "amount, carried by the COLAs, in both scenarios.",
            "",
            "| Total | Change |",
            "|---|---:|",
            "| Social Security | "
            f"{_money(result['social_security_change'], signed=True)} |",
            "| Net income | " f"{_money(result['net_change'], signed=True)} |",
            "| Net income, with health coverage | "
            f"{_money(health['net_change'], signed=True)} |",
            "| Share of the Social Security change taken back | "
            f"{_share(result['take_back']['share'], result['take_back']['mixes_rises_and_falls'])} |",  # noqa: E501
            "",
            "### By level of government",
            "",
            "| Level | Baseline | Reform | Change | Share taken back |",
            "|---|---:|---:|---:|---:|",
        ]
        for level in (*LEVEL_ROWS, "market_income"):
            entry = result["by_level"][level]
            share = result["take_back"]["by_level"].get(level)
            lines.append(
                f"| {pop.LEVEL_LABELS[level]} | {_money(entry['baseline'])} "
                f"| {_money(entry['reform'])} | "
                f"{_money(entry['change'], signed=True)} | {_share(share)} |"
            )
        lines += [
            "",
            "Federal includes Social Security; its share taken back excludes "
            "it. Shares sum exactly to the total share.",
            "",
            "### By component",
            "",
            "| Component | Level | Baseline | Reform | Change |",
            "|---|---|---:|---:|---:|",
        ]
        for leaf in result["by_leaf"]:
            lines.append(
                f"| `{leaf['variable']}` | {leaf['level']} | "
                f"{_money(leaf['baseline'])} | {_money(leaf['reform'])} | "
                f"{_money(leaf['change'], signed=True)} |"
            )
        for grouping, title in (
            ("ssi_status", "By SSI receipt"),
            ("income_decile", "By baseline net income decile"),
            ("social_security_direction", "By direction of Social Security"),
        ):
            groups = run["results"]["default"]["groupings"][grouping]["groups"]
            lines += [
                "",
                f"### {title}",
                "",
                "| Group | Households | Mean Social Security change | "
                "Mean net change | Federal | State | Local | Taken back |",
                "|---|---:|---:|---:|---:|---:|---:|---:|",
            ]
            for label, entry in groups.items():
                lines.append(
                    f"| {label} | {entry['households']:,} | "
                    f"{_money(entry['mean_social_security_change_per_household'], signed=True)} | "  # noqa: E501
                    f"{_money(entry['mean_net_change_per_household'], signed=True)} | "  # noqa: E501
                    + " | ".join(
                        _money(entry["by_level"][lv]["change"], signed=True)
                        for lv in LEVEL_ROWS
                    )
                    + " | "
                    + _share(
                        entry["take_back"]["share"],
                        entry["take_back"]["mixes_rises_and_falls"],
                    )
                    + " |"
                )
            lines.append("")
            lines.append(
                "Federal, state and local are weighted total changes; the "
                "means are per weighted household. \u2020 The group's Social "
                "Security rises for some households and falls for others, so "
                "its share taken back is a ratio of net sums, not a share of "
                "either direction."
            )
        lines += [
            "",
            "### Medicaid, CHIP and Medicare Savings Programs: federal and "
            "state cost",
            "",
            "From policyengine-us 2.18.0's own cost-share variables, in the "
            "default simulations (Medicaid at the release's spending over "
            "enrollment per enrollee).",
            "",
            "| Program | Scenario | Total | Federal | State |",
            "|---|---|---:|---:|---:|",
        ]
        for program in summary.HEALTH_PROGRAMS:
            entry = run["health_split"][program]
            for scenario in (BASELINE, REFORM, "change"):
                values = entry[scenario]
                signed = scenario == "change"
                lines.append(
                    f"| {program.upper() if program != 'medicaid' else 'Medicaid'}"  # noqa: E501
                    f" | {scenario.replace('_', ' ')} | "
                    f"{_money(values['total'], signed=signed)} | "
                    f"{_money(values['federal'], signed=signed)} | "
                    f"{_money(values['state'], signed=signed)} |"
                )
        scale = run["scale"]
        sims = scale["pe_simulations"]
        bound = (
            "no stated bound for this size"
            if scale["bounds"] is None
            else "stated bounds: "
            f"{scale['bounds']['pe_wall_seconds']:.0f} s and "
            f"{scale['bounds']['peak_rss_bytes'] / 2**30:.0f} GiB"
        )
        lines += [
            "",
            "### Runtime and memory",
            "",
            "- Track M and the population: "
            + ", ".join(
                f"{k.replace('_seconds', '').replace('_', ' ')} {v:.1f} s"
                for k, v in scale["track_m_and_population_seconds"].items()
            )
            + ".",
            f"- policyengine-us child: {scale['pe_wall_seconds']:.0f} s wall "
            f"(import {scale['pe_import_seconds']:.0f} s), peak resident "
            f"memory {scale['peak_rss_gib']:.2f} GiB; {bound}.",
        ]
        for variant in VARIANTS:
            for scenario in (BASELINE, REFORM):
                t = sims[variant][scenario]
                lines.append(
                    f"- {variant}, {scenario}: one simulation, built in "
                    f"{t['build_seconds']:.1f} s, calculated in "
                    f"{t['calculate_seconds']:.1f} s."
                )
        checks = run["checks"]
        lines += [
            "",
            "### Checks",
            "",
            "- Every household's leaves sum exactly (in cents) to its net "
            "change; weighted, the leaves, categories and levels each sum "
            "exactly to the weighted net change, and each grouping's groups "
            "to the population's.",
            "- PolicyEngine-US's `social_security` equals the Track M "
            "benefits in every household and scenario.",
            "- Households whose Social Security does not change do not "
            "change at all (no result leaks between households).",
            f"- Deciles equal policyengine-us's `household_income_decile` in "
            f"all {checks['deciles_match_policyengine_us']['households']:,} "
            "households.",
            f"- Means-tested benefits, income taxes or refundable credits "
            f"moving the same way as Social Security: "
            f"{checks['households']['default']['wrong_way_changes']} "
            "household-category pairs ("
            + (
                ", ".join(
                    f"{state} {n}"
                    for state, n in checks["households"]["default"][
                        "wrong_way_by_state"
                    ].items()
                )
                or "none"
            )
            + "; recorded, not refused). Leaf changes under $2: "
            f"{checks['households']['default']['small_leaf_changes']}.",
        ]
        lines.append("")
    lines += invented_inputs_markdown(document["invented_inputs"])
    lines += ["## Notes", ""]
    lines += [f"- {note}" for note in document["caveats"]]
    lines.append("")
    return "\n".join(lines)


#: Colors: the dataviz skill's reference palette, categorical slots 1-6 in
#: their fixed order (validated light, adjacent pairs), with its ink and
#: surface; the net marker is ink.
SERIES_COLORS = (
    "#2a78d6",
    "#eb6834",
    "#1baf7a",
    "#eda100",
    "#e87ba4",
    "#008300",
)
INK = "#0b0b0b"
MUTED = "#52514e"
GRID = "#e4e3df"
SURFACE = "#fcfcfb"


def chart_values(
    run: dict[str, Any], grouping: str, order: tuple[str, ...]
) -> tuple[list[str], np.ndarray, np.ndarray]:
    """Mean change per weighted household by chart series, per group.

    Exact before the final division to floats: each series' weighted
    change is a sum of cents times exact weights.  Refuses a group whose
    series do not sum exactly to its net change (a changed leaf the chart
    has no series for).
    """

    internal = run["_internal"]
    decomposition = internal["decompositions"]["default"]
    labels, _ = internal["groupings"][grouping]
    weights = pop.ExactWeights.from_floats(internal["frame"].weight)
    series = [key for key, _ in CHART_SERIES]
    groups = [g for g in order if (labels == g).any()]
    values = np.zeros((len(groups), len(series)))
    net = np.zeros(len(groups))
    for g, group in enumerate(groups):
        mask = labels == group
        total_weight = weights.total_weight(mask)
        exact = dict.fromkeys(series, Fraction(0))
        other = Fraction(0)
        for j, leaf in enumerate(decomposition.leaves):
            change = weights.dollars(decomposition.change_cents(j), mask)
            key = chart_series(leaf)
            if key in exact:
                exact[key] += change
            else:
                other += change
        group_net = weights.dollars(decomposition.net_change_cents, mask)
        if other != 0 or sum(exact.values(), Fraction(0)) != group_net:
            raise AssertionError(
                f"{grouping}={group}: the chart's series do not sum to the "
                "net change"
            )
        for k, key in enumerate(series):
            values[g, k] = float(exact[key] / total_weight)
        net[g] = float(group_net / total_weight)
    return groups, values, net


#: The chart's panels: a grouping, its labels in order, and a title.
CHART_PANELS = (
    (
        "income_decile",
        tuple(str(d) for d in (-1, *range(1, 11))),
        "By baseline net income decile (person-weighted)",
    ),
    (
        "ssi_status",
        summary.SSI_STATUS_ORDER,
        "By SSI receipt",
    ),
)
_SSI_TICKS = {
    "SSI in both": "In both",
    "SSI at baseline only": "Baseline\nonly",
    "SSI under the reform only": "Reform\nonly",
    "no SSI": "Neither",
}


def _money_tick(value: float, _: Any) -> str:
    return f"\u2212${abs(value):,.0f}" if value < 0 else f"${value:,.0f}"


def draw_chart(
    run: dict[str, Any], document: dict[str, Any], stem: Path
) -> list[Path]:
    """Two rows of stacked bars per grouping (deciles, SSI receipt).

    The top row stacks every series' mean change per household, Social
    Security included; the bottom row leaves Social Security out, so the
    offsets (what other programs and taxes give back or take) are
    legible.  Each row shares one y-axis across its panels.  Each
    series keeps its color in both rows; the dot is the stack's sum.
    """

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker

    matplotlib.rcParams["svg.hashsalt"] = "pe-us-population"
    matplotlib.rcParams["font.family"] = "DejaVu Sans"
    matplotlib.rcParams["text.parse_math"] = False
    data = [
        chart_values(run, grouping, order)
        for grouping, order, _ in CHART_PANELS
    ]
    ss = [key for key, _ in CHART_SERIES].index("social_security")
    rows = (
        ("all", "Every component, Social Security included"),
        (
            "offsets",
            "Everything but Social Security: what other programs and taxes "
            "offset",
        ),
    )
    widths = [max(len(groups), 1) + 1.5 for groups, _, _ in data]
    fig = plt.figure(figsize=(12.0, 10.0), facecolor=SURFACE)
    grid = fig.add_gridspec(
        2, 2, width_ratios=widths, wspace=0.22, hspace=0.42
    )
    for r, (row, row_title) in enumerate(rows):
        shown = []
        for groups, values, net in data:
            values = values.copy()
            dots = net.copy()
            if row == "offsets":
                dots = net - values[:, ss]
                values[:, ss] = 0.0
            shown.append((groups, values, dots))
        low = min(
            min(0.0, float(np.where(v < 0, v, 0).sum(axis=1).min(initial=0)))
            for _, v, _ in shown
        )
        high = max(
            max(0.0, float(np.where(v > 0, v, 0).sum(axis=1).max(initial=0)))
            for _, v, _ in shown
        )
        span = high - low or 1.0
        for c, ((_, _, title), (groups, values, dots)) in enumerate(
            zip(CHART_PANELS, shown, strict=True)
        ):
            ax = fig.add_subplot(grid[r, c])
            ax.set_facecolor(SURFACE)
            x = np.arange(len(groups))
            up = np.zeros(len(groups))
            down = np.zeros(len(groups))
            for k, (_, label) in enumerate(CHART_SERIES):
                column = values[:, k]
                positive = np.where(column > 0, column, 0.0)
                negative = np.where(column < 0, column, 0.0)
                first = r == 0 and c == 0
                for part, bottom in ((positive, up), (negative, down)):
                    ax.bar(
                        x,
                        part,
                        bottom=bottom,
                        width=0.6,
                        color=SERIES_COLORS[k],
                        edgecolor=SURFACE,
                        linewidth=1.0,
                        label=label if first and part is positive else None,
                        zorder=2,
                    )
                up += positive
                down += negative
            ax.scatter(
                x,
                dots,
                s=40,
                color=INK,
                edgecolors=SURFACE,
                linewidths=1.8,
                zorder=4,
                label=(
                    "Net change (the stack's sum)"
                    if r == 0 and c == 0
                    else None
                ),
            )
            ax.axhline(0, color=MUTED, linewidth=1, zorder=3)
            ax.set_xticks(x)
            ticks = [
                "Neg." if g == "-1" else _SSI_TICKS.get(g, g) for g in groups
            ]
            ax.set_xticklabels(ticks, fontsize=8.5, color=MUTED)
            ax.set_ylim(low - 0.08 * span, high + 0.08 * span)
            ax.yaxis.set_major_formatter(
                matplotlib.ticker.FuncFormatter(_money_tick)
            )
            ax.tick_params(axis="y", labelsize=8.5, colors=MUTED, length=0)
            ax.tick_params(axis="x", length=0)
            ax.grid(axis="y", color=GRID, linewidth=1, zorder=0)
            for side in ("top", "right", "left", "bottom"):
                ax.spines[side].set_visible(False)
            ax.set_title(title, fontsize=9.5, color=INK, loc="left", pad=6)
            if c == 0:
                ax.set_ylabel(
                    "Mean change per household, 2026 $",
                    fontsize=8.5,
                    color=MUTED,
                )
                ax.text(
                    0.0,
                    1.16,
                    row_title,
                    transform=ax.transAxes,
                    fontsize=10.5,
                    fontweight="bold",
                    color=INK,
                    va="bottom",
                )
    handles, labels = fig.axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper left",
        bbox_to_anchor=(0.01, 0.885),
        ncol=4,
        frameon=False,
        fontsize=8.5,
        labelcolor=INK,
        handlelength=1.2,
        columnspacing=1.4,
    )
    size = run["family_units"]
    fig.text(
        0.01,
        0.985,
        f"{LABEL}",
        fontsize=10,
        fontweight="bold",
        color=INK,
        va="top",
    )
    fig.text(
        0.01,
        0.96,
        "Change in 2026 net income from the minimum benefit, by component "
        f"and level of government: {size:,} invented family units",
        fontsize=13,
        fontweight="bold",
        color=INK,
        va="top",
    )
    fig.text(
        0.01,
        0.935,
        textwrap.fill(
            f"{document['reform']}. One weighted PolicyEngine-US simulation "
            "per scenario; health coverage outside net income.",
            width=170,
        ),
        fontsize=8.5,
        color=MUTED,
        va="top",
    )
    pe = document["provenance"]["policyengine_us"]
    footer = [
        f"{LABEL}: invented people, weights, states, incomes, assets and "
        "rents; not estimates for the US and not a comparison.",
        f"PolicyEngine-US {pe['release']['version']} (PyPI), with "
        "California's published 2026 SSI payment standard; Microcosm "
        f"Dynamics {document['provenance']['microcosm_dynamics']['commit'][:10]}"
        ".",
        "Bars stack each series' mean change per weighted household (above "
        "zero, gains; below, losses). Tables: the Markdown file beside this "
        "chart.",
    ]
    fig.text(
        0.01,
        0.012,
        "\n".join(footer),
        fontsize=7.5,
        color=MUTED,
        va="bottom",
        linespacing=1.4,
    )
    fig.subplots_adjust(left=0.08, right=0.99, top=0.8, bottom=0.12)
    paths = []
    # The label also goes in each file's metadata, so a reader of the file
    # (and the artifact test) finds it without rendering the chart.
    described = {
        "Title": LABEL,
        "Description": f"{LABEL}: {size:,} invented family units",
    }
    for suffix, kwargs in (
        (".png", {"dpi": 200, "metadata": {"Software": None, **described}}),
        (
            ".svg",
            {"metadata": {"Date": None, "Creator": None, **described}},
        ),
    ):
        path = stem.with_suffix(suffix)
        fig.savefig(path, facecolor=SURFACE, **kwargs)
        paths.append(path)
    plt.close(fig)
    return paths


def write(
    document: dict[str, Any],
    runs: dict[int, dict[str, Any]],
    directory: Path,
) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    written = []
    path = directory / f"{OUTPUT_STEM}.json"
    path.write_text(json.dumps(document, indent=1, sort_keys=False) + "\n")
    written.append(path)
    path = directory / f"{OUTPUT_STEM}.md"
    path.write_text(markdown(document))
    written.append(path)
    for size, run in runs.items():
        written += draw_chart(
            run, document, directory / f"{OUTPUT_STEM}_{size}_by_level"
        )
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--family-units",
        type=int,
        nargs="+",
        default=list(DEFAULT_SIZES),
        help="population sizes in family units",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--docs-dir", type=Path, default=DEFAULT_DOCS_DIR)
    parser.add_argument(
        "--pe-us-python",
        default=None,
        help=f"interpreter with policyengine-us (else ${bridge.PE_US_PYTHON_ENV})",
    )
    parser.add_argument("--timeout", type=float, default=RUN_TIMEOUT_SECONDS)
    args = parser.parse_args(argv)
    document, runs = build(
        tuple(args.family_units),
        seed=args.seed,
        python=args.pe_us_python,
        timeout=args.timeout,
    )
    for path in write(document, runs, args.docs_dir):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
