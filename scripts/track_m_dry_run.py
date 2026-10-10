"""Track M end-to-end DRY RUN on INVENTED cohorts (plan item M10).

INVENTED DATA - NOT A COMPARISON.  Two invented cohorts run through the
real Track M code for every registered row MS0-MS6
(:func:`populace_dynamics.min_benefit_track_m.pipeline.run_track_m`):
section 4a's years, the one history, years of coverage, the PIA through
the oracle, the options, receipt and the Table 6 tabulation with its
floors and design-based standard errors.  The first is the invented
population of :mod:`populace_dynamics.min_benefit_track_m.invented`
(records built directly).  The second is
:mod:`populace_dynamics.min_benefit_track_m.invented_psid`'s PSID-shaped
frames (the 2023 anchor, receipt histories, family-level items, marriage
history, deaths, earnings panel and next-wave labor income, all
invented), run through the same M4 cohort
(:func:`~populace_dynamics.min_benefit_track_m.cohort.build_cohort`) and M5
careers (:func:`~populace_dynamics.min_benefit_track_m.careers.
build_track_m_inputs`) code the registered run uses on the PSID.  The
parameters are real and committed or read from the policyengine-us
checkout the oracle reads: the oracle's wage index, bend points and
reductions, the quarter-of-coverage amounts, the Census one-person 65+
thresholds of 1982, 1986, 1988-1992 and 1994-2022 (the pinned capture)
and the SSA COLA history (for the invented MS5 benefits).  No PSID file
is opened and no comparator value is read.

The checks record that the specification block equals the code and that
the committed block passes the registered-run gate (its registered-commit
edit of 2026-09-27 emptied ``blocked_by``), while a copy that still lists
the blockers it was ratified with is refused; that every threshold year
the invented cohort
needs is captured, that records needing a year before 2003 the capture
holds (1998; 1990, the year d430's sensitivity needs) pass the threshold
check, and that records needing a year it lacks (1993, inside the
captured span; 1981, before it) are refused before anything is computed
(referee R8); that MS5 read benefit-implied
PIAs and MS0 none; that the registered path refuses invented records,
PSID-kind records without the issue #42 pointer or under a block that
lists a blocker, a subset of rows and other floor seeds; that records
carrying PSID file hashes are refused outside the registered run,
without the issue #42 pointer or with a pointer to another issue, and
with a supplied specification block other than the committed one (even
one the gate would pass); that an invented M4 cohort drawn
without the capture constraint (as the PSID is) is refused for the
threshold years it needs that the capture lacks, before anything is
computed; that the one-shot entry point finds every component, and that
its preflight passes the committed block at the registered commit on a
clean tree but refuses another pointer, another ``HEAD``, a dirty tree,
an existing output and a block that lists a blocker (a stand-in ``git``;
nothing is written); and the plan's INVENTED worked cases (M1 section
16).

Cos d430's sensitivity (M1 sections 4c, 11 and 19) runs on the invented
PSID-shaped cohort twice: on the default draw, whose type items are all
known, so that no record or person may differ between the readings; and
on a draw with receipt of unknown or "other" type before 62
(``invented_psid``'s ``unknown_or_other_before_62``), which shows MS0's
cells under both readings, the share of the universe resting on a record
the readings classify differently and the bound that share sets.  The
checks record that the rows MS0-MS6 are the same with and without the
sensitivity, that the registered path refuses a run without it, scored
records built under the sensitivity's reading and a sensitivity of another
universe, and that no window year is earlier under the sensitivity.

Usage::

    python scripts/track_m_dry_run.py --output-dir <dir> [--seed N]
        [--family-units N]

Writes ``result.json`` and ``RESULTS.md`` into ``--output-dir``.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime
import hashlib
import importlib.util
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from populace_dynamics.estimates.parameters import (  # noqa: E402
    load_cola_history,
)
from populace_dynamics.min_benefit_track_m import (  # noqa: E402
    DRY_RUN_HEADER,
    careers,
    cohort,
    coverage,
    invented,
    invented_psid,
    pipeline,
    rules,
    specification,
    structure,
    tabulation,
)
from populace_dynamics.min_benefit_track_m.evaluation import (  # noqa: E402
    INVENTED,
    PSID_FILES,
    TrackMInputs,
    TrackMParameters,
    WorkerRecord,
    needed_threshold_years,
)
from populace_dynamics.min_benefit_track_m.policy import (  # noqa: E402
    OWN_RECEIPT_PRE62_UNKNOWN_OR_OTHER_UNOBSERVED,
    OWN_RECEIPT_SENSITIVITY_ID,
    REGISTERED_ROWS,
    SENSITIVITIES,
    TABLE6_OPTIONS,
    TABLE6_ROWS,
    policy_for_row,
)
from populace_dynamics.ss.params import load_ssa_parameters  # noqa: E402

#: A syntactically valid registration pointer used only to show that the
#: registered path refuses invented inputs (no such comment is implied).
_GUARD_POINTER = (
    "https://github.com/PolicyEngine/microcosm-dynamics/issues/42"
    "#issuecomment-0"
)
DEFAULT_SEED = 20260925
#: The share of invented persons given receipt of an unknown or "other"
#: type before 62 in the d430 sensitivity's second invented cohort.
SENSITIVITY_SHARE = 0.5
#: The blockers ``m1-ratified-1``'s block listed when it was ratified;
#: the registered-commit edit (2026-09-27) dropped both.  A copy that
#: still lists them shows the gate's refusal of a blocked block.
BLOCKERS_AT_RATIFICATION = (
    "registration_package_m10_needs_the_comparator_seal_hash",
    "issue_42_registration_absent",
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _refusal(call: Any) -> dict[str, Any]:
    try:
        call()
    except Exception as error:  # recorded, not swallowed
        return {
            "refused": True,
            "error": type(error).__name__,
            "message": str(error),
        }
    return {"refused": False}


def _entry_script():
    path = ROOT / "scripts" / "run_track_m_registered.py"
    spec = importlib.util.spec_from_file_location("_track_m_entry", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def committed_parameters() -> tuple[TrackMParameters, dict[str, Any]]:
    """The oracle's, the QC amounts, the Census capture and the COLAs."""

    params = load_ssa_parameters()
    qc = coverage.load_qc_amounts()
    thresholds = rules.load_aged_thresholds()
    cola = load_cola_history()
    return TrackMParameters(params, qc, thresholds), {
        "cola_rates": cola,
        "cola_provenance": dict(cola.provenance),
    }


#: The plan's INVENTED cases of the M1 specification's section 16: (P, Y,
#: DI onset).  Every case is born 1948 with its PIA first calculated in
#: 2010 against an invented threshold of $10,000.
PLAN_CASES: dict[str, tuple[float, int, int | None]] = {
    "A": (600.0, 30, None),
    "B": (600.0, 9, None),
    "C": (900.0, 40, None),
    "D": (500.0, 15, 1948 + 44),
    "H": (953.0, 40, None),
    "I": (700.0, 20, None),
}


def plan_cases() -> dict[str, Any]:
    """The section 16 table recomputed: options 1, 2 and 4, both orders.

    The cases define a price-indexed threshold only, so the wage-indexed
    options 3 and 5 (which need an average wage index) are not evaluated,
    as section 16 does not.
    """

    thresholds = rules.AgedThresholds({2010: 10_000.0}, {"kind": "INVENTED"})
    ms2 = policy_for_row("MS2")
    out = {}
    for name, (pia, years, onset) in PLAN_CASES.items():
        worker = rules.WorkerInputs(
            pia=pia,
            work_years=years,
            first_pia_year=2010,
            threshold_year=2010,
            birth_year=1948,
            di_onset_year=onset,
        )

        def run(number, policy=None, worker=worker):
            return rules.evaluate_worker(
                worker, number, thresholds=thresholds, nawi={}, policy=policy
            )

        one, two, four = run(1), run(2), run(4)
        out[name] = {
            "work_years_star": round(two.work_years_star, 2),
            "minimum_option_2": round(two.minimum, 2),
            "flag_option_2": {
                "floor_after_cut": two.on_minimum,
                "cut_after_floor_ms2": run(2, ms2).on_minimum,
            },
            "flag_option_4": {
                "floor_after_cut": four.on_minimum,
                "cut_after_floor_ms2": run(4, ms2).on_minimum,
            },
            "option_2_against_option_1_percent": round(
                100 * rules.relative_to_option_1(two, one), 2
            ),
        }
    return out


def checks(
    inputs: TrackMInputs,
    parameters: TrackMParameters,
    result: dict[str, Any],
) -> dict[str, Any]:
    """The dry run's checks, each recorded (none reads a PSID file)."""

    block = specification.m1_parameter_block()
    needed = needed_threshold_years(
        inputs.workers.values(),
        [policy_for_row(row) for row in REGISTERED_ROWS],
    )

    # Old-age workers entitled in 2004 whose year of attaining 62 is a
    # year the capture holds (1998, born 1936, entitled at 68; 1990, born
    # 1928, entitled at 76, the year d430's sensitivity needs), a year
    # inside the captured span it lacks (1993, born 1931) and a year before
    # it (1981, born 1919).
    def early_worker(birth: int) -> WorkerRecord:
        return WorkerRecord(
            f"INVENTED-EARLY-{birth + 62}",
            birth,
            rules.BASIS_OLD_AGE,
            2004,
            {year: 30_000.0 for year in range(1968, 1997)},
        )

    def with_worker(worker: WorkerRecord) -> TrackMInputs:
        return dataclasses.replace(
            inputs, workers={**inputs.workers, worker.record_id: worker}
        )

    def needed_with(worker: WorkerRecord) -> dict[int, int]:
        return needed_threshold_years(
            [*inputs.workers.values(), worker],
            [policy_for_row(row) for row in REGISTERED_ROWS],
        )

    captured_1998 = early_worker(1936)
    captured_1990 = early_worker(1928)
    gap_1993 = early_worker(1931)
    before_1981 = early_worker(1919)
    psid_kind = dataclasses.replace(inputs, provenance_kind=PSID_FILES)
    ratified = json.loads(json.dumps(block))
    ratified["status"], ratified["version"] = (
        "ratified_frozen",
        "m1-ratified-1",
    )
    unblocked = {**ratified, "blocked_by": []}
    # The committed block as it was ratified, before the registered-commit
    # edit: the gate refuses it.
    blocked = {**ratified, "blocked_by": list(BLOCKERS_AT_RATIFICATION)}
    entry = _entry_script()
    sources = {
        row: entry_["diagnostics"]["pia_source_by_record"]
        for row, entry_ in result["rows"].items()
    }

    def preflight(**changes: Any) -> dict[str, Any]:
        """The entry point's preflight in the registered state (the
        committed block, a stand-in ``git`` at the registered commit on a
        clean tree, an output that does not exist), with ``changes``."""

        arguments = {
            "registration_pointer": _GUARD_POINTER,
            "registered_commit": "0" * 40,
            "output": ROOT / "runs" / "track-m-dry-run-never-written.json",
            "git": _clean_git("0" * 40),
            **changes,
        }
        return _refusal(lambda: entry.preflight(**arguments))

    return {
        "specification_block_equals_code": (
            specification.specification_code_check(block)
        ),
        "the_committed_block_passes_the_specification_gate": _refusal(
            lambda: specification.check_specification_for_registered_run(block)
        ),
        "the_committed_block_equals_a_ratified_unblocked_copy": {
            "passed": block == unblocked
        },
        "a_ratified_copy_still_listing_blockers_is_refused": _refusal(
            lambda: specification.check_specification_for_registered_run(
                blocked
            )
        ),
        "threshold_years_needed_by_the_invented_cohort": {
            str(year): count for year, count in needed.items()
        },
        "threshold_years_all_captured": _refusal(
            lambda: rules.check_threshold_years(needed, parameters.thresholds)
        )
        | {
            "captured": parameters.thresholds.source.get(
                "captured_years", parameters.thresholds.source["years"]
            )
        },
        "a_record_needing_1998_passes_the_threshold_check": _refusal(
            lambda: rules.check_threshold_years(
                needed_with(captured_1998), parameters.thresholds
            )
        )
        | {"threshold_year": captured_1998.birth_year + 62},
        "a_record_needing_1990_passes_the_threshold_check": _refusal(
            lambda: rules.check_threshold_years(
                needed_with(captured_1990), parameters.thresholds
            )
        )
        | {"threshold_year": captured_1990.birth_year + 62},
        "a_record_needing_1993_is_refused_before_any_computation": _refusal(
            lambda: pipeline.run_track_m(
                with_worker(gap_1993), parameters, data_provenance="invented"
            )
        ),
        "a_record_needing_1981_is_refused_before_any_computation": _refusal(
            lambda: pipeline.run_track_m(
                with_worker(before_1981),
                parameters,
                data_provenance="invented",
            )
        ),
        "ms5_reads_benefit_implied_pias_and_ms0_none": {
            "passed": (
                sources["MS5"]["benefit_implied"] > 0
                and all(
                    counts["benefit_implied"] == 0
                    for row, counts in sources.items()
                    if row != "MS5"
                )
            ),
            "pia_source_by_row": sources,
        },
        "registered_path_refuses_invented_records": _refusal(
            lambda: pipeline.run_track_m(
                inputs,
                parameters,
                data_provenance=tabulation.REGISTERED_REAL,
                registration_pointer=_GUARD_POINTER,
            )
        ),
        "psid_kind_records_refused_as_invented": _refusal(
            lambda: pipeline.run_track_m(
                psid_kind, parameters, data_provenance="invented"
            )
        ),
        "psid_kind_records_refused_without_the_42_pointer": _refusal(
            lambda: pipeline.run_track_m(
                psid_kind,
                parameters,
                data_provenance=tabulation.REGISTERED_REAL,
            )
        ),
        "psid_kind_records_refused_with_a_pointer_under_a_blocked_block": (
            _refusal(
                lambda: pipeline.run_track_m(
                    psid_kind,
                    parameters,
                    data_provenance=tabulation.REGISTERED_REAL,
                    registration_pointer=_GUARD_POINTER,
                    specification=blocked,
                )
            )
        ),
        "a_registered_subset_of_rows_is_refused": _refusal(
            lambda: pipeline.run_track_m(
                psid_kind,
                parameters,
                data_provenance=tabulation.REGISTERED_REAL,
                registration_pointer=_GUARD_POINTER,
                specification=unblocked,
                rows=("MS0",),
            )
        ),
        "registered_floor_seeds_cannot_be_changed": _refusal(
            lambda: pipeline.run_track_m(
                psid_kind,
                parameters,
                data_provenance=tabulation.REGISTERED_REAL,
                registration_pointer=_GUARD_POINTER,
                specification=unblocked,
                floor_seeds=(0, 1),
            )
        ),
        "entry_point_missing_components": entry.missing_components(),
        # The preflight writes nothing: it passes the registered state and
        # refuses each departure from it.
        "entry_point_preflight_passes_the_registered_state": preflight(),
        "entry_point_preflight_refuses_a_pointer_to_another_issue": (
            preflight(
                registration_pointer=_GUARD_POINTER.replace("/42#", "/420#")
            )
        ),
        "entry_point_preflight_refuses_another_head": preflight(
            git=_clean_git("1" * 40)
        ),
        "entry_point_preflight_refuses_a_dirty_tree": preflight(
            git=_clean_git("0" * 40, porcelain=" M INVENTED.py")
        ),
        # an output that exists: the committed specification itself, which
        # the preflight refuses to overwrite (it opens nothing for writing)
        "entry_point_preflight_refuses_an_existing_output": preflight(
            output=specification.M1_SPECIFICATION_PATH
        ),
        "entry_point_preflight_refuses_a_blocked_block": preflight(
            specification=blocked
        ),
        "plan_invented_cases": plan_cases(),
    }


def _clean_git(head: str, porcelain: str = ""):
    """A stand-in ``git`` for the preflight check: ``head`` as ``HEAD``
    and ``porcelain`` as the tree's status (clean by default)."""

    def fake(*args: str) -> str:
        if args == ("rev-parse", "HEAD"):
            return head
        if args == ("status", "--porcelain"):
            return porcelain
        raise AssertionError(args)

    return fake


def m4_m5_run(
    parameters: TrackMParameters,
    extra: dict[str, Any],
    *,
    seed: int,
    n_family_units: int,
    unknown_or_other_before_62: float = 0.0,
) -> dict[str, Any]:
    """The invented PSID-shaped cohort through M4, M5 and the pipeline,
    under the scored reading, with cos d430's sensitivity (the same frames
    under the sensitivity reading)."""

    frames = invented_psid.invented_cohort_inputs(
        seed=seed,
        n_family_units=n_family_units,
        unknown_or_other_before_62=unknown_or_other_before_62,
    )
    built = cohort.build_cohort(frames)
    built_sensitivity = cohort.build_cohort(
        frames,
        own_receipt_reading=OWN_RECEIPT_PRE62_UNKNOWN_OR_OTHER_UNOBSERVED,
    )

    def records_of(built_cohort: cohort.TrackMCohort) -> TrackMInputs:
        return careers.build_track_m_inputs(
            built_cohort,
            earnings=frames.earnings,
            prior_year=frames.prior_year_labor,
            params=parameters.params,
            cola_rates=extra["cola_rates"],
            provenance_kind=INVENTED,
            source={**dict(frames.provenance)},
        )

    records = records_of(built)
    sensitivity = records_of(built_sensitivity)
    result = pipeline.run_track_m(
        records,
        parameters,
        data_provenance=INVENTED,
        own_receipt_sensitivity=sensitivity,
    )
    return {
        "frames": frames,
        "cohort": built,
        "cohort_sensitivity": built_sensitivity,
        "records": records,
        "records_sensitivity": sensitivity,
        "result": result,
    }


def d430_checks(
    run: dict[str, Any],
    run_with_unknown: dict[str, Any],
    parameters: TrackMParameters,
) -> dict[str, Any]:
    """Cos d430's sensitivity guards and properties, each recorded."""

    block = specification.m1_parameter_block()
    unblocked = {
        **json.loads(json.dumps(block)),
        "status": "ratified_frozen",
        "version": "m1-ratified-1",
        "blocked_by": [],
    }
    records = run["records"]
    without = pipeline.run_track_m(
        records, parameters, data_provenance=INVENTED
    )
    same_rows = json.dumps(without["rows"], allow_nan=False) == json.dumps(
        run["result"]["rows"], allow_nan=False
    )
    default_sensitivity = run["result"]["sensitivities"][
        OWN_RECEIPT_SENSITIVITY_ID
    ]
    sensitivity = run_with_unknown["result"]["sensitivities"][
        OWN_RECEIPT_SENSITIVITY_ID
    ]
    bound_holds = True
    for cell in sensitivity["receipt_under_both_readings"].values():
        if not cell["defined"]:
            continue
        resting = cell["resting_weighted_share_percent"]
        for option in cell["options"].values():
            bound_holds &= (
                abs(option["change_percent_points"]) <= resting + 1e-9
                and option["moved_out_percent"] <= resting + 1e-9
                and option["moved_in_percent"] <= resting + 1e-9
            )
    psid_kind = dataclasses.replace(records, provenance_kind=PSID_FILES)
    # the sensitivity reading's records with one weight changed: another
    # universe (the readings share the universe and its weights)
    moved = run["records_sensitivity"].persons
    other_universe = dataclasses.replace(
        run["records_sensitivity"],
        persons=(
            dataclasses.replace(moved[0], weight=moved[0].weight + 1.0),
            *moved[1:],
        ),
    )
    changes = sensitivity["reclassification"]["worker_record_changes"]

    # The sensitivity reading's records with one invented old-age record
    # added, entitled in 2004, whose year of attaining 62 is 1990 (born
    # 1928; the year d430's sensitivity needs on the PSID, captured
    # 2026-09-26) or 1993 (born 1931; a year the capture lacks).  The
    # universe is unchanged, so the pipeline's first refusal is the
    # sensitivity's threshold-year check.
    def sensitivity_with(birth: int) -> TrackMInputs:
        worker = WorkerRecord(
            f"INVENTED-SENSITIVITY-{birth + 62}",
            birth,
            rules.BASIS_OLD_AGE,
            2004,
            {year: 30_000.0 for year in range(1968, 1997)},
        )
        base = run["records_sensitivity"]
        return dataclasses.replace(
            base, workers={**base.workers, worker.record_id: worker}
        )

    needs_1990 = needed_threshold_years(
        sensitivity_with(1928).workers.values(),
        [policy_for_row(SENSITIVITIES[OWN_RECEIPT_SENSITIVITY_ID]["row"])],
    )
    return {
        "d430_rows_ms0_to_ms6_identical_with_and_without_the_sensitivity": {
            "passed": same_rows
        },
        "d430_default_draw_no_record_or_person_differs": {
            "passed": (
                default_sensitivity["reclassification"][
                    "worker_records_classified_differently"
                ]
                == 0
                and default_sensitivity["reclassification"][
                    "persons_resting_on_a_record_classified_differently"
                ]
                == 0
            )
        },
        "d430_draw_with_unknown_or_other_receipt_differs": {
            "passed": sensitivity["reclassification"][
                "worker_records_classified_differently"
            ]
            > 0,
            "reclassification": sensitivity["reclassification"],
        },
        "d430_share_gap_within_the_resting_share": {"passed": bound_holds},
        "d430_no_window_year_earlier_under_the_sensitivity": {
            "passed": changes.get(
                "window_year_earlier_under_the_sensitivity", 0
            )
            == 0
        },
        "d430_a_registered_run_without_the_sensitivity_is_refused": _refusal(
            lambda: pipeline.run_track_m(
                psid_kind,
                parameters,
                data_provenance=tabulation.REGISTERED_REAL,
                registration_pointer=_GUARD_POINTER,
                specification=unblocked,
            )
        ),
        "d430_scored_records_under_the_sensitivity_reading_are_refused": (
            _refusal(
                lambda: pipeline.run_track_m(
                    run["records_sensitivity"],
                    parameters,
                    data_provenance=INVENTED,
                )
            )
        ),
        "d430_a_sensitivity_of_another_universe_is_refused": _refusal(
            lambda: pipeline.run_track_m(
                records,
                parameters,
                data_provenance=INVENTED,
                own_receipt_sensitivity=other_universe,
            )
        ),
        "d430_a_sensitivity_under_the_scored_reading_is_refused": _refusal(
            lambda: pipeline.run_track_m(
                records,
                parameters,
                data_provenance=INVENTED,
                own_receipt_sensitivity=records,
            )
        ),
        # the check the pipeline applies to the sensitivity's records
        # (its window, MS0's), on the real capture
        "d430_a_sensitivity_record_needing_1990_passes_the_threshold_check": (
            _refusal(
                lambda: rules.check_threshold_years(
                    needs_1990, parameters.thresholds
                )
            )
            | {
                "threshold_year": 1990,
                "needed_before_2003": sorted(
                    year for year in needs_1990 if year < 2003
                ),
            }
        ),
        "d430_a_sensitivity_record_needing_1993_is_refused_first": _refusal(
            lambda: pipeline.run_track_m(
                records,
                parameters,
                data_provenance=INVENTED,
                own_receipt_sensitivity=sensitivity_with(1931),
            )
        ),
    }


def m4_m5_checks(
    run: dict[str, Any],
    parameters: TrackMParameters,
    extra: dict[str, Any],
    *,
    seed: int,
    n_family_units: int,
) -> dict[str, Any]:
    """The M4/M5 path's guards, each recorded (no PSID file is read)."""

    block = specification.m1_parameter_block()
    # A supplied block the gate would pass but that is not the committed
    # one (another snapshot, a field the gate does not hold to the code):
    # records carrying PSID file hashes are refused under it all the same.
    supplied = {
        **json.loads(json.dumps(block)),
        "snapshot": {"wave": 2021, "income_year": 2020},
    }
    records = run["records"]
    hashed = dataclasses.replace(
        records,
        provenance_kind=PSID_FILES,
        source={
            **dict(records.source),
            pipeline.PSID_FILES_SOURCE_KEY: {"INVENTED.txt": "0" * 64},
        },
    )
    hashed_cohort = dataclasses.replace(
        run["cohort"],
        provenance={
            **dict(run["cohort"].provenance),
            pipeline.PSID_FILES_SOURCE_KEY: {"INVENTED.txt": "0" * 64},
        },
    )
    # At least 600 family units, so that the unconstrained draw holds
    # records needing threshold years the capture lacks (as the PSID
    # would, were a year it needs not captured).  Since the capture holds
    # 1982, 1986, 1988-1992 and 1994-2022, only a draw that
    # reaches a gap year (or one before 1982) is refused; the check
    # records those years so that a draw reaching none shows as such.
    unconstrained = invented_psid.invented_cohort_inputs(
        seed=seed,
        n_family_units=max(n_family_units, 600),
        threshold_years_from=None,
    )

    def unconstrained_records() -> TrackMInputs:
        return careers.build_track_m_inputs(
            cohort.build_cohort(unconstrained),
            earnings=unconstrained.earnings,
            prior_year=unconstrained.prior_year_labor,
            params=parameters.params,
            cola_rates=extra["cola_rates"],
            provenance_kind=INVENTED,
        )

    unconstrained_needed = needed_threshold_years(
        unconstrained_records().workers.values(),
        [policy_for_row(row) for row in REGISTERED_ROWS],
    )

    def unconstrained_run() -> None:
        pipeline.run_track_m(
            unconstrained_records(), parameters, data_provenance=INVENTED
        )

    return {
        "m4_universe_equals_the_structural_funnel": {
            "passed": len(run["cohort"].persons)
            == structure.structural_counts(run["frames"].structure_inputs)[
                "funnel"
            ]["receives_oasdi_person_level"],
        },
        "psid_hashed_records_refused_outside_the_registered_run": _refusal(
            lambda: pipeline.run_track_m(
                hashed, parameters, data_provenance=INVENTED
            )
        ),
        "psid_hashed_records_refused_with_a_supplied_block": _refusal(
            lambda: pipeline.run_track_m(
                hashed,
                parameters,
                data_provenance=tabulation.REGISTERED_REAL,
                registration_pointer=_GUARD_POINTER,
                specification=supplied,
            )
        )
        | {
            "supplied_block_passes_the_gate": not _refusal(
                lambda: specification.check_specification_for_registered_run(
                    supplied
                )
            )["refused"]
        },
        "psid_hashed_records_refused_without_the_42_pointer": _refusal(
            lambda: pipeline.run_track_m(
                hashed,
                parameters,
                data_provenance=tabulation.REGISTERED_REAL,
            )
        ),
        "psid_hashed_records_refused_with_a_pointer_to_another_issue": (
            _refusal(
                lambda: pipeline.run_track_m(
                    hashed,
                    parameters,
                    data_provenance=tabulation.REGISTERED_REAL,
                    registration_pointer=_GUARD_POINTER.replace(
                        "/42#", "/420#"
                    ),
                )
            )
        ),
        "a_psid_hashed_cohort_cannot_be_marked_invented": _refusal(
            lambda: careers.build_track_m_inputs(
                hashed_cohort,
                earnings=run["frames"].earnings,
                prior_year=run["frames"].prior_year_labor,
                params=parameters.params,
                cola_rates=extra["cola_rates"],
                provenance_kind=INVENTED,
            )
        ),
        "an_unconstrained_m4_cohort_needing_years_not_captured_is_refused": (
            _refusal(unconstrained_run)
            | {
                "needed_years_not_captured": sorted(
                    set(unconstrained_needed)
                    - set(parameters.thresholds.annual)
                )
            }
        ),
    }


def _summary(result: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for row, entry in result["rows"].items():
        table = entry["tabulation"]
        out[row] = {
            f"{cell['option']}:{cell['row']}": {
                "share_percent": cell.get("share_percent"),
                "floor_mean": cell["floor"]["mean"],
                "design_se": (cell.get("design_se") or {}).get("se"),
                "unweighted_n": cell.get("unweighted_n"),
            }
            for cell in table["cells"]
        }
        out[row]["y3"] = {
            key: table["y3_option_3_women_to_men"].get(key)
            for key in ("ratio_of_rates", "ratio_of_weighted_counts")
        }
    return out


def _sensitivity_summary(result: dict[str, Any]) -> dict[str, Any]:
    """d430's sensitivity in brief: MS0 under both readings by cell, and
    the resting shares."""

    entry = result["sensitivities"][OWN_RECEIPT_SENSITIVITY_ID]
    out = {
        "weighted_share_of_the_universe_resting_percent": entry[
            "weighted_share_of_the_universe_resting_percent"
        ],
        "reclassification": entry["reclassification"],
        "cells": {},
    }
    for cell, value in entry["receipt_under_both_readings"].items():
        if not value["defined"]:
            continue
        out["cells"][cell] = {
            "resting_weighted_share_percent": value[
                "resting_weighted_share_percent"
            ],
            **{
                number: {
                    key: option[key]
                    for key in (
                        "share_percent_scored_reading",
                        "share_percent_sensitivity_reading",
                        "change_percent_points",
                        "moved_out_percent",
                        "moved_in_percent",
                    )
                }
                for number, option in value["options"].items()
            },
        }
    return out


def _sensitivity_table(summary: dict[str, Any]) -> list[str]:
    lines = [
        "| Cell | Resting | "
        + " | ".join(
            f"Opt {n}: scored / sensitivity / change" for n in TABLE6_OPTIONS
        )
        + " |",
        "|---|---:|" + "---:|" * len(TABLE6_OPTIONS),
    ]
    for cell, value in summary["cells"].items():
        parts = []
        for number in TABLE6_OPTIONS:
            option = value[str(number)]
            parts.append(
                f"{option['share_percent_scored_reading']:.1f} / "
                f"{option['share_percent_sensitivity_reading']:.1f} / "
                f"{option['change_percent_points']:+.1f}"
            )
        lines.append(
            f"| {cell} | {value['resting_weighted_share_percent']:.1f} | "
            + " | ".join(parts)
            + " |"
        )
    return lines


def provenance(
    parameters: TrackMParameters, extra: dict[str, Any]
) -> dict[str, Any]:
    """What a registration package pins, as far as the dry run knows it.

    The specification and code, the parameter files and the invented
    generator.  The PSID file hashes are recorded by the M3-M5 readers'
    structural run (``scripts/track_m_structure.py``); the comparator seal
    is not opened or hashed by a builder lane (the orchestrator's hash of
    its bytes is in the M1 specification, section 18 item 3).
    """

    return {
        "m1_specification": {
            "path": str(specification.M1_SPECIFICATION_PATH.relative_to(ROOT)),
            "sha256": _sha256(specification.M1_SPECIFICATION_PATH),
            "version": specification.m1_parameter_block()["version"],
            "status": specification.m1_parameter_block()["status"],
        },
        "oracle_pe_us_revision": parameters.params.pe_us_revision,
        "quarter_of_coverage": dict(parameters.qc.source),
        "census_thresholds": dict(parameters.thresholds.source),
        "cola_history": {
            key: extra["cola_provenance"][key]
            for key in ("path", "sha256", "content_sha256")
        },
        "psid_files": (
            "none read: both cohorts are invented (the M3-M5 readers' "
            "structural run, scripts/track_m_structure.py, records the "
            "PSID file hashes)"
        ),
        "comparator_seal": (
            "not opened and not hashed by this lane; the orchestrator's "
            "SHA-256 of its bytes is recorded in the M1 specification "
            "(section 18 item 3)"
        ),
    }


def _share_table(summary: dict[str, Any]) -> list[str]:
    lines = [
        "| Row | "
        + " | ".join(
            f"Opt {n} {r}" for n in TABLE6_OPTIONS for r in TABLE6_ROWS
        )
        + " |",
        "|---|" + "---:|" * (len(TABLE6_OPTIONS) * len(TABLE6_ROWS)),
    ]
    for row, cells in summary.items():
        values = [
            cells[f"{n}:{r}"]["share_percent"]
            for n in TABLE6_OPTIONS
            for r in TABLE6_ROWS
        ]
        lines.append(
            f"| {row} | "
            + " | ".join("—" if v is None else f"{v:.1f}" for v in values)
            + " |"
        )
    return lines


def _markdown(document: dict[str, Any]) -> str:
    result = document["result"]
    checks_ = document["checks"]
    lines = [
        f"# {DRY_RUN_HEADER}",
        "",
        "Track M (DynaSim exercise 4, the minimum benefit) end-to-end dry "
        "run on two **INVENTED** cohorts. Every person, family "
        "unit, weight, design variable, entitlement, death, earnings "
        "history and observed benefit is invented; the numbers below are "
        "not PSID values and not a result, and they compare with nothing. "
        "The parameters are real: the oracle's (policyengine-us), the "
        "quarter-of-coverage amounts, the pinned Census one-person 65+ "
        "thresholds (1982, 1986, 1988-1992 and 1994-2022) and "
        "the SSA COLA history.",
        "",
        f"- Labels: {'; '.join(result['labels'])}",
        f"- Disclosure (d280): {result['disclosure']}",
        f"- Code: `{document['run']['git_head']}` (tree clean: "
        f"{document['run']['git_clean']})",
        f"- M1 specification: `{document['provenance']['m1_specification']['version']}` "
        f"(`{document['provenance']['m1_specification']['sha256']}`)",
        f"- Invented cohort: {result['inputs']['n_persons']} persons, "
        f"{result['inputs']['n_worker_records']} worker records, "
        f"{result['inputs']['source']['n_family_units']} family units, seed "
        f"{result['inputs']['source']['seed']}",
        "- Census threshold capture: "
        f"`{result['parameters']['thresholds']['sha256']}`",
        "",
        "## Invented shares receiving a minimum (percent), by row",
        "",
        *_share_table(document["summary"]),
    ]
    m45 = document["m4_m5"]
    structure_ = m45["cohort_structure"]
    lines += [
        "",
        "## The invented PSID-shaped cohort through M4 and M5",
        "",
        "The same code the registered run applies to the PSID (the M4 "
        "cohort and the M5 careers) on INVENTED PSID-shaped frames: "
        f"{structure_['persons']} persons, {structure_['records']} worker "
        f"records ({', '.join(f'{k} {v}' for k, v in structure_['records_by_basis'].items())}), "
        f"{sum(structure_['links_by_kind'].values())} links. Invented "
        "shares, percent:",
        "",
        *_share_table(m45["summary"]),
    ]
    d430 = document["m4_m5_own_receipt_sensitivity"]
    changes = d430["sensitivity_summary"]["reclassification"]
    lines += [
        "",
        "## Cos d430's sensitivity on invented data (unscored)",
        "",
        "MS0 under the scored own-receipt reading (section 4c item 1: "
        "receipt of an unknown or 'other' type counts as own receipt) and "
        "under d430's sensitivity reading (such receipt before 62 read as "
        "neither own receipt nor non-receipt), on an INVENTED PSID-shaped "
        "cohort drawn with receipt of those types before 62 "
        f"({d430['persons_changed_by_the_draw']['persons_changed']}). "
        f"{changes['worker_records_classified_differently']} worker "
        "records are classified differently and "
        f"{changes['persons_resting_on_a_record_classified_differently']} "
        "persons rest on one. Resting: the weighted share of the cell "
        "whose A_k rests on such a record, which bounds each change. "
        "Invented shares, percent:",
        "",
        *_sensitivity_table(d430["sensitivity_summary"]),
        "",
        "On the default invented draw (every type item known) no record "
        "or person differs between the readings.",
    ]
    head = document["summary"]["MS0"]["2:all"]
    floor = head["floor_mean"]
    lines += [
        "",
        "Invented headline cell (MS0, option 2, All): "
        f"{head['share_percent']:.1f}, five-seed floor mean "
        + ("undefined" if floor is None else f"{floor:.2f}")
        + f", design SE {head['design_se']:.2f} percentage points.",
        "",
        "## Checks",
        "",
    ]
    for name, value in checks_.items():
        if isinstance(value, dict) and "refused" in value:
            state = "refused" if value["refused"] else "passed"
            detail = value.get("message", "")
            lines.append(
                f"- `{name}`: {state}"
                + (f" ({value['error']}: {detail[:200]})" if detail else "")
            )
        elif isinstance(value, dict) and "passed" in value:
            lines.append(f"- `{name}`: passed = {value['passed']}")
        elif name == "entry_point_missing_components":
            lines.append(f"- `{name}`: {', '.join(value) or 'none'}")
        elif name == "specification_block_equals_code":
            lines.append(f"- `{name}`: {value['consistent']}")
        elif name == "threshold_years_needed_by_the_invented_cohort":
            lines.append(
                f"- `{name}`: "
                + ", ".join(f"{year} ({n})" for year, n in value.items())
            )
    lines += [
        "",
        "## The plan's INVENTED worked cases (M1 section 16)",
        "",
        "| Case | Y* | M, option 2 | Option 2 flag (G10 / MS2) | "
        "Option 4 flag (G10 / MS2) | Option 2 against option 1 |",
        "|---|---:|---:|---|---|---:|",
    ]
    for name, case in checks_["plan_invented_cases"].items():
        two, four = case["flag_option_2"], case["flag_option_4"]
        lines.append(
            f"| {name} | {case['work_years_star']:.2f} | "
            f"{case['minimum_option_2']:.2f} | "
            f"{int(two['floor_after_cut'])} / "
            f"{int(two['cut_after_floor_ms2'])} | "
            f"{int(four['floor_after_cut'])} / "
            f"{int(four['cut_after_floor_ms2'])} | "
            f"{case['option_2_against_option_1_percent']:+.2f}% |"
        )
    lines += [
        "",
        "`result.json` holds every cell, floor, standard error, Y3, N "
        "column and diagnostic of every row, each check in full, and the "
        "provenance a registration package pins.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--family-units", type=int, default=600)
    args = parser.parse_args(argv)
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    parameters, extra = committed_parameters()
    inputs = invented.invented_track_m_inputs(
        seed=args.seed,
        n_family_units=args.family_units,
        params=parameters.params,
        cola_rates=extra["cola_rates"],
    )
    result = pipeline.run_track_m(
        inputs, parameters, data_provenance="invented"
    )
    m45 = m4_m5_run(
        parameters,
        extra,
        seed=args.seed,
        n_family_units=args.family_units,
    )
    m45_unknown = m4_m5_run(
        parameters,
        extra,
        seed=args.seed,
        n_family_units=args.family_units,
        unknown_or_other_before_62=SENSITIVITY_SHARE,
    )
    document = {
        "header": DRY_RUN_HEADER,
        "description": (
            "Track M end-to-end dry run on an INVENTED PSID-shaped cohort: "
            "every registered row MS0-MS6 through the real Track M code, "
            "with real committed parameters. Not PSID values, not a "
            "result, not a comparison."
        ),
        "summary": _summary(result),
        "checks": {
            **checks(inputs, parameters, result),
            **m4_m5_checks(
                m45,
                parameters,
                extra,
                seed=args.seed,
                n_family_units=args.family_units,
            ),
            **d430_checks(m45, m45_unknown, parameters),
        },
        "provenance": provenance(parameters, extra),
        "result": result,
        "m4_m5": {
            "description": (
                "An INVENTED PSID-shaped cohort (min_benefit_track_m."
                "invented_psid) through the M4 cohort, the M5 careers and "
                "the pipeline, the code the registered run applies to the "
                "PSID"
            ),
            "summary": _summary(m45["result"]),
            "cohort_structure": cohort.cohort_structure(m45["cohort"]),
            "result": m45["result"],
        },
        "m4_m5_own_receipt_sensitivity": {
            "description": (
                "Cos d430's sensitivity on an INVENTED PSID-shaped cohort "
                "drawn with receipt of unknown or 'other' type before 62 "
                "(invented_psid, unknown_or_other_before_62 = "
                f"{SENSITIVITY_SHARE}): every registered row under the "
                "scored reading, and MS0 under the sensitivity reading"
            ),
            "persons_changed_by_the_draw": dict(
                m45_unknown["frames"].provenance["unknown_or_other_before_62"]
            ),
            "first_own_receipt_type_before_62": (
                cohort.first_own_receipt_type_before_62(m45_unknown["cohort"])
            ),
            "summary": _summary(m45_unknown["result"]),
            "sensitivity_summary": _sensitivity_summary(m45_unknown["result"]),
            "cohort_structure": cohort.cohort_structure(m45_unknown["cohort"]),
            "cohort_structure_sensitivity_reading": cohort.cohort_structure(
                m45_unknown["cohort_sensitivity"]
            ),
            "result": m45_unknown["result"],
        },
        "run": {
            "started": started,
            "finished": datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat(),
            "git_head": _git("rev-parse", "HEAD"),
            "git_clean": _git("status", "--porcelain") == "",
            "python": platform.python_version(),
            "command": " ".join(
                [
                    "python",
                    "scripts/track_m_dry_run.py",
                    *(sys.argv[1:] if argv is None else argv),
                ]
            ),
        },
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    path = args.output_dir / "result.json"
    path.write_text(
        json.dumps(document, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "RESULTS.md").write_text(
        _markdown(document), encoding="utf-8"
    )
    print(path, hashlib.sha256(path.read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
