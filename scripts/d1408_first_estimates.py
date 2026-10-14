"""Bound first-estimates exposure for the labelled d1408 diagnostic.

Verification class: labelled diagnostic. Local PSID only; no population or
forecast validation is admitted. The registered artifact and configurations
are read, never executed or replaced. If the registered fitting stack is
unavailable, the historical real seed roster supplies a support bound and
the registered opening-stock distribution supplies an expected bound. These
are explicitly unverified counts, never reconstructed payment changes.

The differing window is 42 USC 402(w)(2)(A). Before-1917 positive credits
are unsupported under 402(w)(6)(A), and the historical production inclusion
already excludes those birth years through its pre-1979 eligibility rule.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
import subprocess
import sys
from pathlib import Path

from d1408_common import (
    HEADER,
    PE_ROOT,
    PSID_ROOT,
    ROOT,
    SCRATCH,
    aggregate_group,
    export_history,
    install_read_guard,
    write_aggregate,
)

MODEL_COMMIT = "e31eca40ddb00afe0eb82507307b10315e0035be"
CLAIM_REFERENCE = "data/external/ssa_claim_ages_2014supplement.json"
CLAIM_REFERENCE_SHA256 = (
    "b88e45a08909f0f88a0ff37074c757891759ec988fd7e9fe14362eebd0abe462"
)


def window_support(ages, birth_year: int, fra_months: int) -> list[bool]:
    """Flag the historical caller's changed ages for admitted birth cohorts."""
    return [
        1917 <= birth_year <= 1942 and age * 12 - fra_months > 48
        for age in ages
    ]


def window_probability(ages, probability, birth_year, fra_months) -> float:
    """Sum full-PMF changed-region mass without removing unaffected ages."""
    selected = window_support(ages, birth_year, fra_months)
    if len(selected) != len(probability):
        raise ValueError("claim-age support and probabilities differ")
    if any(not math.isfinite(value) or value < 0 for value in probability):
        raise ValueError(
            "claim-age probability must be finite and nonnegative"
        )
    if abs(sum(probability) - 1.0) > 1e-12:
        raise ValueError("claim-age probabilities must sum to one")
    return float(
        sum(p for keep, p in zip(selected, probability, strict=True) if keep)
    )


def complete_stock_support(exposure_age: int, ages) -> bool:
    """The strict exposure truncation preserves all ages only above max age."""
    return bool(len(ages)) and exposure_age > max(ages)


def publish_replay_group(replay: dict, complementary_people: int) -> dict:
    """Withhold overlapping subtotals that reveal a small complementary cell."""
    published = dict(replay)
    if 0 < complementary_people < 10:
        for key in (
            "people",
            "worker_records",
            "weight",
            "roster_weight_share",
        ):
            published[key] = "suppressed_complementary"
        published["publication"] = (
            "withheld because its difference from the reported upper bound "
            "contains fewer than ten people"
        )
    return published


def environment_limitations() -> dict:
    """Describe dependency misses without replacing the registered stack."""
    missing = []
    for name in ("populace.fit", "populace.frame", "policyengine_us"):
        try:
            available = importlib.util.find_spec(name) is not None
        except (ImportError, ModuleNotFoundError):
            available = False
        if not available:
            missing.append(name)
    return {
        "missing_registered_packages": missing,
        "sklearn_live": importlib.metadata.version("scikit-learn"),
        "sklearn_registered": "1.8.0",
        "known_gate_environments_present": [
            name
            for name in (
                ".venv-gate",
                ".venv-gate-m6",
                ".venv-gate1",
                ".venv-gate8",
            )
            if (Path(sys.executable).parents[2] / name).is_dir()
        ],
    }


def configuration_inventory() -> list[dict]:
    """Keep unsuccessful registrations separate from the published result."""
    incidents = []
    for index in range(1, 7):
        path = ROOT / f"runs/first_estimates_incident_{index}.json"
        if not path.exists():
            continue
        incident = json.loads(path.read_text())
        incidents.append(
            {
                "path": str(path.relative_to(ROOT)),
                "registration": incident["registration_reference"],
                "phase": incident["phase"],
                "reason": incident["reason"],
                "headline_sections_present": [
                    key
                    for key in (
                        "tables",
                        "counts",
                        "diagnostics",
                        "results",
                        "partial_results",
                        "model_results",
                    )
                    if key in incident
                ],
            }
        )
    latest_path = ROOT / (
        "docs/registrations/"
        "first_estimates_registration_7_configuration.json"
    )
    latest = json.loads(latest_path.read_text())
    records = []
    for index in range(2, 8):
        path = ROOT / (
            "docs/registrations/"
            f"first_estimates_registration_{index}_configuration.json"
        )
        raw = path.read_bytes()
        configuration = json.loads(raw)
        records.append(
            {
                "configuration": str(path.relative_to(ROOT)),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "registration": configuration["registration_reference"],
                "same_projection_as_published": (
                    configuration["projection"] == latest["projection"]
                ),
                "same_opening_stock_as_published": (
                    configuration["stock_imputation"]
                    == latest["stock_imputation"]
                ),
                "same_design_as_published": (
                    configuration["design"] == latest["design"]
                ),
                "same_parameters_as_published": (
                    configuration["parameters"] == latest["parameters"]
                ),
                "incident_metadata": [
                    incident
                    for incident in incidents
                    if incident["registration"]
                    == configuration["registration_reference"]
                ],
                "actual_count_claim": (
                    "published artifact is diagnosed below"
                    if index == 7
                    else "none: retained metadata records an aborted "
                    "attempt without retained model headline quantities"
                ),
            }
        )
    return records


def compute_bound(history: Path) -> dict:
    """Use the original readers, birth precedence and stock RNG only."""
    print("first estimates: importing historical inputs", flush=True)
    reads = install_read_guard()
    supplied_psid = os.environ.get("POPULACE_DYNAMICS_PSID_DIR")
    if supplied_psid and Path(supplied_psid).expanduser().resolve() != (
        PSID_ROOT.resolve()
    ):
        raise ValueError("d1408 accepts only the authorized local PSID root")
    from populace_dynamics import claiming
    from populace_dynamics.data import deaths, family, marriage, panels
    from populace_dynamics.engine.refit import (
        _truncate_marriage_records,
        claiming_pmfs_from_reference,
    )
    from populace_dynamics.engine.steps import ClaimingSchedule
    from populace_dynamics.estimates import career
    from populace_dynamics.estimates import parameters as parameter_module
    from populace_dynamics.harness.m6_cells import build_anchor_frame
    from populace_dynamics.harness.m6_population import (
        _anchor_rows,
        _person_sex_map,
    )
    from populace_dynamics.ss.params import load_ssa_parameters

    if not Path(career.__file__).resolve().is_relative_to(history.resolve()):
        raise RuntimeError("first-estimates historical code was not selected")
    print("first estimates: historical modules selected", flush=True)
    artifact = json.loads((ROOT / "runs/first_estimates_v1.json").read_text())
    reference_path = history / CLAIM_REFERENCE
    if hashlib.sha256(reference_path.read_bytes()).hexdigest() != (
        CLAIM_REFERENCE_SHA256
    ):
        raise ValueError("registered claim-age reference changed")
    reference = claiming.load_claim_age_reference(reference_path)
    schedule = ClaimingSchedule(
        claiming_pmfs_from_reference(reference, boundary_year=2014)
    )
    # Use only the historical loader's mandatory registered file hashes.
    # A local checkout is a valid byte source only when every hash matches.
    parameter_module._verify_files(
        PE_ROOT,
        parameter_module.SSA_PARAMETER_SHA256,
        expected_bundle_sha256=(parameter_module.SSA_PARAMETER_BUNDLE_SHA256),
    )
    params = load_ssa_parameters(PE_ROOT)
    print(
        "first estimates: registered SSA parameter hashes verified", flush=True
    )
    demo = panels.demographic_panel()
    print(
        "first estimates: historical demographic reader complete", flush=True
    )
    anchor = build_anchor_frame(demo)
    sex = _person_sex_map(deaths.read_death_records())
    seed = _anchor_rows(
        demo.assign(sex=demo["person_id"].map(sex)),
        anchor,
        period_column="period",
        columns=("age", "sex", "interview"),
    )
    seed = anchor.merge(seed, on="person_id", validate="one_to_one")
    seed["year"] = seed["anchor_wave"] - 1
    print("first estimates: historical real seed roster built", flush=True)
    earnings = family.family_earnings_panel()
    print("first estimates: historical earnings reader complete", flush=True)
    births = career.derive_birth_years(
        _truncate_marriage_records(marriage.marriage_history(), 2014),
        earnings,
        seed_coordinates=seed,
        required_person_ids=set(anchor["person_id"]),
    )
    birth_by_person = {row.person_id: row for row in births}
    print("first estimates: historical birth precedence complete", flush=True)
    weights = dict(zip(anchor["person_id"], anchor["weight"], strict=True))
    potential = set()
    replayed = set()
    uncertain_exposure = set()
    expected_people = 0.0
    expected_weight = 0.0
    supported_births = set()
    pre1917 = set()
    for row in seed.itertuples(index=False):
        born = birth_by_person[row.person_id].birth_year
        if born is None:
            continue
        if born < 1917:
            pre1917.add(row.person_id)
            continue
        if born > 1942:
            continue
        supported_births.add(row.person_id)
        ages, probability = schedule.distribution(row.sex, born + 62)
        # The actual first post-seed exposure may be later if early presence
        # is lost. Taking the full support gives an upper bound in that case.
        mass = window_probability(
            ages, probability, born, params.fra_months(born)
        )
        if mass <= 0:
            continue
        potential.add(row.person_id)
        expected_people += mass
        expected_weight += mass * row.weight
        # For these cohorts, source age >=71 ensures complete age62-70
        # support in the truncated opening draw. Other rows stay in the
        # support bound but cannot receive an exact stock replay assertion.
        if not complete_stock_support(row.age, ages):
            uncertain_exposure.add(row.person_id)
            continue
        chosen, _year, _snap = career._opening_stock_draw(
            person_id=row.person_id,
            birth_year=born,
            sex=row.sex,
            exposure_age=int(row.age),
            schedule=schedule,
            root_seed=8108,
        )
        if chosen * 12 - params.fra_months(born) > 48:
            replayed.add(row.person_id)
    denominator = float(sum(weights.values()))
    assert replayed <= potential <= supported_births
    assert uncertain_exposure <= potential
    assert not (supported_births & pre1917)
    support = aggregate_group(potential, (), weights, denominator)
    support["roster_weight_share"] = support.pop("admitted_weight_share")
    support["worker_records"] = None
    support["weight_share_denominator"] = "real report seed roster"
    support["classification"] = "unverified support upper bound"
    replay = aggregate_group(replayed, (), weights, denominator)
    replay["roster_weight_share"] = replay.pop("admitted_weight_share")
    replay["worker_records"] = None
    replay["classification"] = (
        "unverified potential opening-stock draws; Stage A-D and "
        "realized payments have not been reconstructed"
    )
    replay["weight_share_denominator"] = "real report seed roster"
    replay = publish_replay_group(replay, len(uncertain_exposure - replayed))
    final_bound = aggregate_group(
        replayed | uncertain_exposure, (), weights, denominator
    )
    final_bound["roster_weight_share"] = final_bound.pop(
        "admitted_weight_share"
    )
    final_bound["worker_records"] = None
    final_bound["classification"] = (
        "unverified actual-person upper bound: complete-support stock "
        "replays plus rows whose seed age does not preserve complete support"
    )
    final_bound["weight_share_denominator"] = "real report seed roster"
    supported = aggregate_group(supported_births, (), weights, denominator)
    supported["roster_weight_share"] = supported.pop("admitted_weight_share")
    supported["worker_records"] = None
    supported["weight_share_denominator"] = "real report seed roster"
    expected = {
        "people": expected_people,
        "weight": expected_weight,
        "roster_weight_share": expected_weight / denominator,
        "classification": (
            "expected upper bound under the registered full opening-stock "
            "PMF, conditional on all support people becoming non-DI "
            "opening claimants; not an expectation of admitted claimants"
        ),
    }
    if 0 < len(potential) < 10:
        expected.update(people="<10", weight="<10", roster_weight_share="<10")
    admitted = [
        {
            "draw_index": row["draw_index"],
            "people": row["inclusion__included__unweighted"],
            "weight": row["inclusion__included__weighted"],
        }
        for row in artifact["counts"]["per_draw"]
    ]
    bound_ids = replayed | uncertain_exposure
    bound_weight = sum(weights[person] for person in sorted(bound_ids))
    admitted_bounds = []
    for row in admitted:
        upper_people = min(len(bound_ids), row["people"])
        upper_weight = min(bound_weight, row["weight"])
        small = 0 < upper_people < 10
        admitted_bounds.append(
            {
                "draw_index": row["draw_index"],
                "people_upper_bound": "<10" if small else upper_people,
                "weight_upper_bound": "<10" if small else upper_weight,
                "admitted_weight_share_upper_bound": (
                    "<10" if small else upper_weight / row["weight"]
                ),
                "classification": "unverified upper bound",
            }
        )
    return {
        "header": HEADER,
        "result": "first_estimates",
        "artifact": "runs/first_estimates_v1.json",
        "code_commit": MODEL_COMMIT,
        "code_commit_basis": "committed environment sidecar contract.head_sha",
        "verification": "unverified bound; exact reproduction unavailable",
        "reproduction_check": {
            "passed": False,
            "computed": False,
            "reason": "registered fitting stack is unavailable",
            "environment": environment_limitations(),
        },
        "counts": {
            "affected_people": None,
            "affected_worker_records": None,
            "affected_weight": None,
            "affected_admitted_weight_share": None,
            "real_roster_people": len(anchor),
            "real_roster_weight": denominator,
            "supported_birth_cohort": supported,
            "support_upper_bound": support,
            "potential_stock_rng_replay": replay,
            "actual_person_upper_bound": final_bound,
            "upper_bounds_with_committed_admitted_denominators": (
                admitted_bounds
            ),
            "expected_support_bound": expected,
            "pre1917_evaluations": 0,
            "pre1917_reason": "excluded_pre1979_eligibility before ledger",
            "committed_admitted_denominators": admitted,
        },
        "payment_paths": {
            "own_old_age": "potentially reachable; actual inclusion unverified",
            "linked_auxiliary": "out of scope in registered first estimates",
            "disability": "excluded_di_conversion or excluded_di_unknown",
            "death_basis": "out of scope in registered first estimates",
            "inverse_ms5": "not used",
        },
        "headline_changes": None,
        "headline_changes_reason": (
            "No statutory amount is claimed without an exact legacy "
            "reconstruction; revenue is independent of the credit function."
        ),
        "method": (
            "Historical demographic/sex/marriage/family earnings readers; "
            "historical realized-anchor and birth precedence from "
            "cutoff-2014 train-context marriage records and the full-window "
            "family earnings panel, exactly as original preparation reads "
            "batch.inputs.refit_inputs.family_context.marriage_records and "
            "batch.inputs.earnings_panel respectively. The original full "
            "loader replaces only refit_inputs, leaving the full earnings "
            "panel unchanged. Seed coordinates retain the pre-draw "
            "collection-wave age and anchor_wave minus one; frozen "
            "claim-age reference; opening-stock person-keyed seed8108. "
            "No registered coordinator, projection or artifact assembler "
            "was executed. Full PMF support bounds all Stage A-D admitted "
            "old-cohort claimants; synthetic entrants cannot attain age62 "
            "within 2014-2022. Actual inclusion and payment presence require "
            "the unavailable registered fitted projection."
        ),
        "parameter_bundle_verified": (
            parameter_module.SSA_PARAMETER_BUNDLE_SHA256
        ),
        "registration_configurations": configuration_inventory(),
        "real_data_files_read": sorted(reads),
        "record_level_files_written": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--historical-child", type=Path)
    arguments = parser.parse_args()
    if arguments.historical_child is not None:
        result = compute_bound(arguments.historical_child)
        write_aggregate(SCRATCH / "first-estimates-aggregate.json", result)
        print("first-estimates aggregate diagnostic written")
        return 0
    history = export_history(MODEL_COMMIT, (CLAIM_REFERENCE,))
    print("first estimates: historical sources exported", flush=True)
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        (str(history / "src"), str(ROOT / "scripts"))
    )
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "--historical-child",
            str(history),
        ],
        env=environment,
        check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
