"""Track M's local delayed-credit diagnostic under ruling d1408.

Verification class: labelled diagnostic. Admitted scope: reconstruct the
retained Track M model records with their registered code and local PSID,
check the legacy model's own shares, and report aggregate changes under
42 USC 402(w)(2)(A)'s FRA-to-70 window. This admits no registered rerun,
replacement, forecast, behavioral or statutory population-validation claim.
No registered entry point or pipeline is called. Positive pre-1917 delay
is reported as unsupported under 402(w)(6)(A), without a statutory amount.
Admitted input checkpoints are temporary, confined to scratch/d1408 and
deleted after verified completion. Published outputs contain aggregates.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from pathlib import Path

from d1408_common import (
    HEADER,
    PSID_ROOT,
    ROOT,
    SCRATCH,
    aggregate_group,
    credit_convention,
    export_history,
    flagged,
    install_read_guard,
    load_pinned_parameters,
    suppressed_count,
    write_aggregate,
)
from d1408_projection import checkpoint_load, checkpoint_path, checkpoint_write

ARTIFACT = ROOT / "runs/replication_urban2006_minimum_benefit_v1.json"
COMMIT = "2e4e08beaad1614da089d76b2ad639d0a4884e2e"
EXTRA_PATHS = (
    "data/external/ssa_cola_history.json",
    "data/external/ssa_quarter_of_coverage_amounts.json",
    "data/external/census_poverty_thresholds_1982_2022.json",
)


def late_months(record, params) -> int:
    """Preserve Track M rules.claim_factor's whole-year convention."""
    return 12 * (record.window_year - record.birth_year) - params.fra_months(
        record.birth_year
    )


def flagged_records(records, params, *, unsupported: bool = False) -> set:
    """Only old-age records call delayed_credit; DI/death factors are 1."""
    return {
        key
        for key, record in records.workers.items()
        if record.basis == "old_age"
        and flagged(late_months(record, params), record.birth_year)
        and (record.birth_year < 1917) == unsupported
    }


def dependent_people(records, worker_ids: set) -> set:
    """Deduplicate admitted owners and beneficiaries of flagged records."""
    return {
        person.person_id
        for person in records.persons
        if person.own_record_id in worker_ids
        or any(link.worker_record_id in worker_ids for link in person.links)
    }


def usage_groups(records, ids: set, denominator: float) -> dict:
    """Keep factor evaluation distinct from the original payment gates."""
    weights = {person.person_id: person.weight for person in records.persons}

    def group(people, keys):
        people, keys = set(people), set(keys)
        if 0 < len(keys) < 10:
            return {
                "people": "<10",
                "worker_records": "<10",
                "weight": "<10",
                "admitted_weight_share": "<10",
                "worker_records_associated_beneficiary_weight": "<10",
            }
        result = aggregate_group(people, keys, weights, denominator)
        if result["people"] == "<10":
            result["worker_records_associated_beneficiary_weight"] = "<10"
        else:
            result["worker_records_associated_beneficiary_weight"] = math.fsum(
                weights[person]
                for key in sorted(keys)
                for person in sorted(dependent_people(records, {key}))
            )
        return result

    owners = {
        person.person_id
        for person in records.persons
        if person.own_record_id in ids
    }
    linked = {
        person.person_id
        for person in records.persons
        if any(link.worker_record_id in ids for link in person.links)
    }
    survivor_gate = set()
    survivor_keys = set()
    for person in records.persons:
        for link in person.links:
            if link.kind != "survivor":
                continue
            if link.worker_record_id in ids:
                survivor_gate.add(person.person_id)
                survivor_keys.add(link.worker_record_id)
            if person.own_record_id in ids and person.paid_own_worker_benefit:
                survivor_gate.add(person.person_id)
                survivor_keys.add(person.own_record_id)
    ms5_keys = {key for key in ids if records.workers[key].ms5_in_scope}
    ms5_people = {
        person.person_id
        for person in records.persons
        if person.own_record_id in ms5_keys
    }
    result = {
        "all_flagged_evaluations": group(dependent_people(records, ids), ids),
        "admitted_flagged_worker_owners": group(
            owners,
            {
                p.own_record_id
                for p in records.persons
                if p.person_id in owners
            },
        ),
        "linked_auxiliary_basis": group(
            linked,
            {
                link.worker_record_id
                for p in records.persons
                for link in p.links
                if link.worker_record_id in ids
            },
        ),
        "factor_entered_survivor_payment_gate": group(
            survivor_gate, survivor_keys
        ),
        "factor_entered_inverse_ms5_pia": group(ms5_people, ms5_keys),
    }
    if result["linked_auxiliary_basis"]["people"] == "<10":
        result["admitted_flagged_worker_owners"] = {
            key: "suppressed_complementary"
            for key in result["admitted_flagged_worker_owners"]
        }
    if 0 < len(ids) - len(ms5_keys) < 10:
        result["factor_entered_inverse_ms5_pia"] = {
            key: "suppressed_complementary"
            for key in result["factor_entered_inverse_ms5_pia"]
        }
    return result


def shares(evaluated) -> dict:
    """Use the original tabulator's exact fsum and person-row ordering."""
    from populace_dynamics.min_benefit_track_m import tabulation

    return {
        f"option_{option}/{cell}": tabulation._share(
            evaluated.rows, tabulation._mask(evaluated.rows, cell), option
        )
        for option in (2, 3, 4, 5)
        for cell in ("all", "men", "women")
    }


def share_changes(legacy, statutory, reference) -> tuple[dict, dict]:
    """Compare each published model cell; suppress small changed groups."""
    from populace_dynamics.min_benefit_track_m import tabulation

    left = shares(legacy)
    right = shares(statutory)
    committed = {
        f"option_{cell['option']}/{cell['row']}": cell
        for cell in reference["cells"]
    }
    checks, changes = {}, {}
    for key, value in left.items():
        option = int(key.split("/")[0].split("_")[1])
        cell = key.split("/")[1]
        wanted = committed[key]
        fields = (
            "share_percent",
            "weighted_receiving",
            "weighted_n",
            "unweighted_n",
            "unweighted_receiving",
        )
        checks[key] = {
            "exact_match": all(value[f] == wanted[f] for f in fields),
            "difference_in_model_share_percentage_points": (
                value["share_percent"] - wanted["share_percent"]
            ),
        }
        mask = tabulation._mask(legacy.rows, cell)
        moves = (
            legacy.rows[f"receives_{option}"].to_numpy()
            != statutory.rows[f"receives_{option}"].to_numpy()
        ) & mask
        count = int(moves.sum())
        small = 0 < count < 10
        changes[key] = {
            "admitted_people": value["unweighted_n"],
            "admitted_weight": value["weighted_n"],
            "changed_receiving_people": suppressed_count(count),
            "supported_subset_change_percentage_points": (
                "<10"
                if small
                else right[key]["share_percent"] - value["share_percent"]
            ),
            "supported_subset_change_in_weight_receiving": (
                "<10"
                if small
                else right[key]["weighted_receiving"]
                - value["weighted_receiving"]
            ),
            "supported_subset_change_in_receiving_people": (
                "<10"
                if small
                else right[key]["unweighted_receiving"]
                - value["unweighted_receiving"]
            ),
            "change_in_admitted_people": (
                right[key]["unweighted_n"] - value["unweighted_n"]
            ),
            "change_in_admitted_weight": (
                right[key]["weighted_n"] - value["weighted_n"]
            ),
        }
    return checks, changes


def positive_survivor_flows(records, evaluated, params, ids):
    """Observe the original positive excess boolean for each option.

    A survivor's own old-age factor can enter the offset; the deceased
    old-age factor can enter its auxiliary basis. Both are attributed only
    when the original survivor_excess_paid says a positive excess is paid.
    """
    from populace_dynamics.min_benefit_track_m import rules

    weights = {person.person_id: person.weight for person in records.persons}
    total = math.fsum(weights.values())
    result = {}
    for option in (2, 3, 4, 5):
        people, keys = set(), set()
        for person in records.persons:
            own = (
                evaluated.workers[person.own_record_id].outcomes[option]
                if person.own_record_id is not None
                else None
            )
            for link in person.links:
                if link.kind != "survivor":
                    continue
                affected = {link.worker_record_id} & ids
                if person.paid_own_worker_benefit:
                    affected |= {person.own_record_id} & ids
                if not affected:
                    continue
                deceased = evaluated.workers[link.worker_record_id].outcomes[
                    option
                ]
                own_amount = rules.survivor_own_amount(
                    own.option_pia if own else None,
                    person.own_claim_factor,
                    receives_own_benefit=person.paid_own_worker_benefit,
                )
                if rules.survivor_excess_paid(
                    own_amount,
                    deceased.option_pia,
                    link.months_early,
                    link.worker_claim_factor,
                    params,
                ):
                    people.add(person.person_id)
                    keys.update(affected)
        group = aggregate_group(people, keys, weights, total)
        if (
            isinstance(group["people"], int)
            and group["people"] >= 10
            and 0 < len(ids - keys) < 10
        ):
            group = {name: "suppressed_complementary" for name in group}
        result[str(option)] = group
    return result


def protect_reading_overlap(
    result, left_people, right_people, left_records, right_records
):
    """Withhold a sensitivity subtotal when differencing reveals a small cell."""
    differences = (
        left_people - right_people,
        right_people - left_people,
        left_records - right_records,
        right_records - left_records,
    )
    if not any(0 < len(values) < 10 for values in differences):
        return
    sensitivity = result["readings"]["d430_sensitivity"]
    sensitivity["supported_flagged_worker_people"] = "suppressed_complementary"
    sensitivity["supported"] = {
        role: {key: "suppressed_complementary" for key in group}
        for role, group in sensitivity["supported"].items()
    }
    for row in sensitivity["rows"].values():
        row["supported_positive_survivor_payment"] = {
            option: {key: "suppressed_complementary" for key in group}
            for option, group in row[
                "supported_positive_survivor_payment"
            ].items()
        }
    result["method"]["cross_reading_suppression"] = (
        "Sensitivity flagged subtotals withheld because overlap differencing "
        "could disclose a small person or worker-record cell."
    )


def compute() -> dict:
    """Build admitted inputs and call benefit functions, never a one-shot."""
    reads = install_read_guard()
    from populace_dynamics.estimates.parameters import load_cola_history
    from populace_dynamics.min_benefit_track_m import (
        careers,
        cohort,
        coverage,
        evaluation,
        policy,
        rules,
    )

    artifact = json.loads(ARTIFACT.read_text())
    if artifact["run"]["registered_commit"] != COMMIT:
        raise ValueError("Track M registered code commit changed")
    if (
        not Path(evaluation.__file__)
        .resolve()
        .is_relative_to((SCRATCH / f"src-{COMMIT}").resolve())
    ):
        raise ValueError(
            "real diagnostic must use its artifact's historical code"
        )
    params = load_pinned_parameters(
        artifact["parameters"]["oracle_pe_us_revision"]
    )
    parameters = evaluation.TrackMParameters(
        params, coverage.load_qc_amounts(), rules.load_aged_thresholds()
    )
    pinned_files = artifact["inputs"]["source"]["psid_files_sha256"]
    cache = checkpoint_path("minimum", COMMIT, "inputs", 2023)
    prepared = checkpoint_load(
        cache, commit=COMMIT, kind="minimum", reads=reads
    )
    if prepared is None:
        raw = cohort.load_cohort_inputs(data_dir=PSID_ROOT)
        print("Track M diagnostic: admitted input frames loaded", flush=True)
        if dict(raw.provenance["psid_files_sha256"]) != pinned_files:
            raise ValueError(
                "Track M PSID files do not match the retained artifact"
            )
        cola = load_cola_history()
        source = {"cola_history": dict(cola.provenance)}
        prepared = {}
        for name, reading in (
            ("scored", policy.OWN_RECEIPT_UNKNOWN_OR_OTHER_IS_OWN),
            (
                "d430_sensitivity",
                policy.OWN_RECEIPT_PRE62_UNKNOWN_OR_OTHER_UNOBSERVED,
            ),
        ):
            built = cohort.build_cohort(raw, own_receipt_reading=reading)
            pair = []
            for statutory in (False, True):
                with credit_convention(statutory=statutory):
                    pair.append(
                        careers.build_track_m_inputs(
                            built,
                            earnings=raw.earnings,
                            prior_year=raw.prior_year_labor,
                            params=params,
                            cola_rates=cola,
                            provenance_kind=evaluation.PSID_FILES,
                            source=source,
                        )
                    )
            prepared[name] = {
                "inputs": pair,
                "worker_people": built.records.set_index("record_id")[
                    "person_id"
                ].to_dict(),
            }
        checkpoint_write(
            cache, prepared, commit=COMMIT, kind="minimum", reads=reads
        )
        del raw, built
    for reading in prepared.values():
        if (
            dict(reading["inputs"][0].source["psid_files_sha256"])
            != pinned_files
        ):
            raise ValueError(
                "minimum cached input hashes differ from retained artifact"
            )
    result = {
        "header": HEADER,
        "result": "track_m_minimum_benefit",
        "artifact": str(ARTIFACT.relative_to(ROOT)),
        "code_commit": COMMIT,
        "commit_basis": "artifact run.registered_commit and run.git_head",
        "parameter_commit": params.pe_us_revision,
        "method": {
            "claim_age": "12 * (entitlement_year - birth_year) - FRA months",
            "rng": "none in cohort, entitlement classification or benefit shares",
            "rounding": (
                "original history PIA dime floor; original MS5 inverse PIA "
                "has no rounding; original payment-gate and fsum share paths"
            ),
            "weights": (
                "admitted beneficiary weights, deduplicated within each group; "
                "linked deceased worker records have no independent 2023 weight"
            ),
            "unsupported_handling": (
                "pre-1917 legacy factors retained solely as placeholders for "
                "supported-subset differences; no statutory amount assigned"
            ),
            "no_registered_entry_point_or_pipeline_called": True,
        },
        "readings": {},
    }
    for name, prepared_reading in prepared.items():
        legacy_inputs, statutory_inputs = prepared_reading["inputs"]
        print(f"Track M diagnostic: {name} records reconstructed", flush=True)
        supported = flagged_records(legacy_inputs, params)
        unsupported = flagged_records(legacy_inputs, params, unsupported=True)
        weight = math.fsum(p.weight for p in legacy_inputs.persons)
        record_people = prepared_reading["worker_people"]
        entry = {
            "admitted_people": len(legacy_inputs.persons),
            "admitted_worker_records": len(legacy_inputs.workers),
            "admitted_weight": weight,
            "supported_flagged_worker_people": suppressed_count(
                len({record_people[key] for key in supported})
            ),
            "unsupported_flagged_worker_people": suppressed_count(
                len({record_people[key] for key in unsupported})
            ),
            "supported": usage_groups(legacy_inputs, supported, weight),
            "pre1917_unsupported": usage_groups(
                legacy_inputs, unsupported, weight
            ),
            "rows": {},
        }
        row_names = tuple(artifact["rows"]) if name == "scored" else ("MS0",)
        for row_name in row_names:
            row_policy = policy.policy_for_row(row_name)
            legacy = evaluation.evaluate(legacy_inputs, row_policy, parameters)
            statutory = evaluation.evaluate(
                statutory_inputs, row_policy, parameters
            )
            reference = (
                artifact["rows"][row_name]["tabulation"]
                if name == "scored"
                else artifact["sensitivities"]["own_receipt_reading_d430"][
                    "tabulation"
                ]
            )
            checks, changes = share_changes(legacy, statutory, reference)
            entry["rows"][row_name] = {
                "legacy_reproduction": checks,
                "changes": changes,
                "supported_positive_survivor_payment": positive_survivor_flows(
                    legacy_inputs, legacy, params, supported
                ),
                "unsupported_positive_survivor_payment": positive_survivor_flows(
                    legacy_inputs, legacy, params, unsupported
                ),
            }
            print(f"Track M diagnostic: {name}/{row_name} checked", flush=True)
        entry["legacy_reproduction_verified"] = all(
            check["exact_match"]
            for row in entry["rows"].values()
            for check in row["legacy_reproduction"].values()
        )
        entry["counts_verified"] = entry["legacy_reproduction_verified"]
        result["readings"][name] = entry
    result["real_data_files_read"] = sorted(reads)
    result["psid_files_match_artifact_sha256"] = True
    result["legacy_reproduction_verified"] = all(
        entry["legacy_reproduction_verified"]
        for entry in result["readings"].values()
    )
    left = prepared["scored"]["inputs"][0]
    right = prepared["d430_sensitivity"]["inputs"][0]
    left_ids, right_ids = flagged_records(left, params), flagged_records(
        right, params
    )
    protect_reading_overlap(
        result,
        dependent_people(left, left_ids),
        dependent_people(right, right_ids),
        left_ids,
        right_ids,
    )
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--worker", action="store_true", help=argparse.SUPPRESS
    )
    args = parser.parse_args(argv)
    if not args.worker:
        history = export_history(COMMIT, extra_paths=EXTRA_PATHS)
        env = dict(os.environ)
        env["PYTHONPATH"] = f"{history / 'src'}:{ROOT / 'scripts'}"
        env["OMP_NUM_THREADS"] = "1"
        env["POLARS_MAX_THREADS"] = "1"
        subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--worker"],
            check=True,
            cwd=ROOT,
            env=env,
        )
        return 0
    result = compute()
    write_aggregate(SCRATCH / "minimum-aggregate.json", result)
    if result["legacy_reproduction_verified"]:
        cache = checkpoint_path("minimum", COMMIT, "inputs", 2023)
        cache.unlink(missing_ok=True)
        cache.with_suffix(".retain").unlink(missing_ok=True)
    print("scratch/d1408/minimum-aggregate.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
