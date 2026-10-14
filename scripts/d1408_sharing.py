"""R7 and cost-ordering model diagnostics under ruling d1408.

Verification class: labelled diagnostic. Admitted scope is affected counts,
weights, and aggregate model changes on the original admitted PSID records.
No registered artifact is rerun or replaced, and no population-validation
claim is made. Only 42 USC 402(w)(2)(A)'s credit window changes; historical
floating-point arithmetic and payment paths are preserved. Positive credits
before 1917 have no statutory amount under this diagnostic (402(w)(6)(A)).
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import pickle
import subprocess
import sys
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from types import ModuleType
from typing import Any

from d1408_common import (
    HEADER,
    ROOT,
    SCRATCH,
    aggregate_group,
    credit_convention,
    export_history,
    flagged,
    install_read_guard,
    load_pinned_parameters,
    write_aggregate,
)

# runs/replication_r7_sharing_v1.json revision_pins.populace_dynamics_sha.
R7_COMMIT = "a8704357f48bc491dc591834e86600cf98ab75f1"
COST_COMMIT = "e86ec0c6b3508ebb0d08afe24ba16282a99769a2"
PARAMETER_COMMIT = "bf71be3b"
R7_SCRIPT = "scripts/replication_r7_sharing.py"
EXTRA_PATHS = (
    R7_SCRIPT,
    "scripts/build_downstream_relevance.py",
    "scripts/reform_delta_diagnostic.py",
    "data/external/ssa_claim_ages_2023supplement.json",
)
MODEL_DEFINITIONS = {
    "_thresholds_from_buckets",
    "_person_history",
    "StudyData",
    "_expected_own_factor",
    "_claim_pmf",
    "shared_history",
    "_current_spouse_pia",
    "_last_widowhood_spouse",
    "baseline_benefit",
    "reformed_benefit",
    "score_population",
    "_bucket_of",
    "_weighted_bucket_shares",
    "cell_shares",
    "seed_half_shares",
    "build_floors",
    "aggregate_cost_change",
}
MODEL_CONSTANTS = {
    "ELIGIBILITY_LO",
    "ELIGIBILITY_HI",
    "AGE_LO",
    "AGE_HI",
    "N_CAREER_AGES",
    "COVERAGE_FLOOR",
    "ELIGIBILITY_AGE",
    "GLOBAL_INCREASE",
    "THRESHOLDS",
    "BUCKETS",
    "SEXES",
    "MARITAL",
    "SEEDS",
}


def selected_nodes(source: str, definitions, constants=()) -> ast.Module:
    """Select original model nodes without executing benchmark constants.

    The historical one-shot's module docstring, anchor transcription,
    comparison helpers, entry points, and output-path assignments are absent
    from the executable module. Selected node bodies remain unmodified.
    """
    nodes = [
        ast.ImportFrom(
            module="__future__", names=[ast.alias("annotations")], level=0
        )
    ]
    for node in ast.parse(source).body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            if node.name in definitions:
                nodes.append(node)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = (
                node.targets if isinstance(node, ast.Assign) else [node.target]
            )
            names = {
                n.id
                for t in targets
                for n in ast.walk(t)
                if isinstance(n, ast.Name)
            }
            if names and names <= set(constants):
                nodes.append(node)
    return ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[]))


def model_module(source_dir: Path) -> ModuleType:
    """Load only the historical model helpers and their historical imports."""
    import numpy as np
    import pandas as pd

    from populace_dynamics import claiming, household
    from populace_dynamics.data.family import family_earnings_panel
    from populace_dynamics.data.marriage import (
        marriage_episodes,
        marriage_history,
    )
    from populace_dynamics.harness import panel as hpanel
    from populace_dynamics.ss import benefits

    module = ModuleType("d1408_historical_r7")
    sys.modules[module.__name__] = module
    module.__dict__.update(
        Any=Any,
        np=np,
        pd=pd,
        claiming=claiming,
        household=household,
        hpanel=hpanel,
        benefits=benefits,
        family_earnings_panel=family_earnings_panel,
        marriage_history=marriage_history,
        marriage_episodes=marriage_episodes,
    )
    for path, names in (
        ("scripts/build_downstream_relevance.py", {"_weighted_mean"}),
        ("scripts/reform_delta_diagnostic.py", {"_summary"}),
    ):
        tree = selected_nodes((source_dir / path).read_text(), names)
        exec(compile(tree, str(source_dir / path), "exec"), module.__dict__)
    tree = selected_nodes(
        (source_dir / R7_SCRIPT).read_text(),
        MODEL_DEFINITIONS,
        MODEL_CONSTANTS,
    )
    exec(compile(tree, str(source_dir / R7_SCRIPT), "exec"), module.__dict__)
    return module


class CreditTrace:
    """Attribute flagged calls to admitted recipients and linked records.

    Trace rows remain in memory. A worker record is (worker person, earnings
    basis), where original and shared histories are separate records.
    The same call reached by several PMF combinations is deduplicated.
    """

    def __init__(self, module, study):
        self.module = module
        self.study = study
        self.recipient = None
        self.worker = None
        self.stage = None
        self.basis = None
        self.role = None
        self.events = set()
        self.collect = True

    @contextmanager
    def context(self, **values):
        before = {key: getattr(self, key) for key in values}
        for key, value in values.items():
            setattr(self, key, value)
        try:
            yield
        finally:
            for key, value in before.items():
                setattr(self, key, value)

    def callback(self, late, birth, _params):
        if not self.collect or not flagged(late, birth):
            return
        if self.recipient is None or self.worker is None:
            raise RuntimeError("flagged credit has no worker attribution")
        self.events.add(
            (
                self.recipient,
                self.worker,
                self.basis,
                self.stage,
                self.role,
                birth,
                late,
            )
        )

    @contextmanager
    def instrument(self):
        module = self.module
        household = module.household
        claiming = module.claiming
        original_baseline = module.baseline_benefit
        original_reform = module.reformed_benefit
        original_own = module._expected_own_factor
        original_survivor = household.survivor_benefit_at_death
        original_factor = claiming.benefit_factor

        def baseline(study, pid, *args, **kwargs):
            with self.context(
                recipient=pid, stage="baseline", basis="original"
            ):
                return original_baseline(study, pid, *args, **kwargs)

        def reform(study, pid, sex, status, package, **kwargs):
            stage = (
                package
                if kwargs.get("apply_scalar", True)
                else package + "_noscalar"
            )
            with self.context(recipient=pid, stage=stage, basis="shared"):
                return original_reform(
                    study, pid, sex, status, package, **kwargs
                )

        def own(study, pid, *args, **kwargs):
            with self.context(worker=pid, role="computed_own_payment"):
                return original_own(study, pid, *args, **kwargs)

        def survivor(*args, **kwargs):
            widow = module._last_widowhood_spouse(
                self.study,
                self.recipient,
                self.study.birth_year[self.recipient] + 62,
            )
            if widow is None:
                raise RuntimeError(
                    "survivor call has no original widowhood episode"
                )
            deceased = int(widow.spouse_person_id)
            ordinal = 0

            def factor(*factor_args, **factor_kwargs):
                nonlocal ordinal
                ordinal += 1
                if ordinal == 1:
                    worker, role = deceased, "linked_survivor_basis"
                elif ordinal == 2:
                    worker, role = self.recipient, "computed_own_payment"
                else:
                    raise RuntimeError(
                        "historical survivor factor order changed"
                    )
                with self.context(worker=worker, role=role):
                    return original_factor(*factor_args, **factor_kwargs)

            claiming.benefit_factor = factor
            try:
                result = original_survivor(*args, **kwargs)
            finally:
                claiming.benefit_factor = original_factor
            if ordinal != 2:
                raise RuntimeError("historical survivor factor count changed")
            return result

        module.baseline_benefit = baseline
        module.reformed_benefit = reform
        module._expected_own_factor = own
        household.survivor_benefit_at_death = survivor
        try:
            yield
        finally:
            module.baseline_benefit = original_baseline
            module.reformed_benefit = original_reform
            module._expected_own_factor = original_own
            household.survivor_benefit_at_death = original_survivor
            claiming.benefit_factor = original_factor


def model_headlines(module, frame) -> dict:
    """Model values only, including exactly the registered rounding."""
    shares = {}
    for variant, column in (
        ("1b", "delta_1b"),
        ("1a", "delta_1a"),
        ("1b_noscalar", "delta_1b_noscalar"),
    ):
        shares[variant] = {}
        for (status, sex), cell in module.cell_shares(frame, column).items():
            shares[variant][f"{status}:{sex}"] = {
                "people": cell["n_persons"],
                "buckets": {
                    key: round(value, 2)
                    for key, value in cell["buckets"].items()
                },
                "thresholds": cell["thresholds"],
            }
    aggregate = module.aggregate_cost_change(frame)
    per_seed = [
        {
            "seed": seed,
            "package_1b": module.seed_half_shares(frame, "delta_1b", seed),
            "package_1a": module.seed_half_shares(frame, "delta_1a", seed),
        }
        for seed in module.SEEDS
    ]
    floors = {
        variant: module.build_floors(per_seed, key)
        for variant, key in (("1b", "package_1b"), ("1a", "package_1a"))
    }
    return {
        "n_scored": len(frame),
        "aggregate": {
            key: value for key, value in aggregate.items() if key != "note"
        },
        "shares": shares,
        "floors": floors,
    }


def reproduction_check(module, frame, artifact, result_name):
    """Cross-check every admitted count and model headline without anchors."""
    actual = model_headlines(module, frame)
    differences = []
    comparisons = 0

    def check(name, got, expected):
        nonlocal comparisons
        comparisons += 1
        if got != expected:
            differences.append(
                {"quantity": name, "reconstructed": got, "committed": expected}
            )

    if result_name == "cost_ordering_r7":
        expected = artifact["earnings_sharing"]
        check(
            "n_scored", actual["n_scored"], expected["n_scored_couples_frame"]
        )
        agg = actual["aggregate"]
        for suffix, key in (
            ("1b", "our_delta_1b"),
            ("1b_noscalar", "our_delta_1b_noscalar"),
        ):
            value = agg["weighted_aggregate_pct_change_" + suffix]
            check(key, value / 100, expected[key])
            check(key + "_pct", value, expected[key + "_pct"])
    else:
        check(
            "n_scored",
            actual["n_scored"],
            artifact["study_population"]["n_scored"],
        )
        for key, value in actual["aggregate"].items():
            check(
                key,
                value,
                artifact["package_1b_primary"]["aggregate_cost_change"][key],
            )
        for variant, section in (
            ("1b", "package_1b_primary"),
            ("1a", "package_1a_descriptive"),
        ):
            for cell in artifact[section]["three_way_by_cell"]:
                name = f"{cell['status']}:{cell['sex']}"
                got = actual["shares"][variant][name]
                check(
                    f"{variant}.{name}.people",
                    got["people"],
                    cell["n_persons"],
                )
                for bucket, value in got["buckets"].items():
                    check(
                        f"{variant}.{name}.{bucket}",
                        value,
                        cell["our_buckets"][bucket],
                    )
                for threshold, value in got["thresholds"].items():
                    check(
                        f"{variant}.{name}.{threshold}",
                        value,
                        cell["thresholds"][threshold]["our_share_pct"],
                    )
                    for field in ("mean", "sd"):
                        check(
                            f"{variant}.{name}.{threshold}.floor_{field}",
                            round(
                                actual["floors"][variant][name][threshold][
                                    field
                                ],
                                2,
                            ),
                            cell["thresholds"][threshold]["floor_" + field],
                        )
        for name, expected in artifact["sensitivity_no_scalar"][
            "shares_by_cell"
        ].items():
            got = actual["shares"]["1b_noscalar"][name]
            check(
                f"1b_noscalar.{name}.people",
                got["people"],
                expected["n_persons"],
            )
            for group in ("buckets", "thresholds"):
                for key, value in got[group].items():
                    check(
                        f"1b_noscalar.{name}.{key}",
                        round(value, 2),
                        expected[group][key],
                    )
        # The registered RNG is used only by these deterministic half splits.
        for seed_record in artifact["per_seed"]:
            for key, column in (
                ("package_1b", "delta_1b"),
                ("package_1a", "delta_1a"),
            ):
                halves = module.seed_half_shares(
                    frame, column, seed_record["seed"]
                )
                for name, cell in halves.items():
                    expected = seed_record[key][name]
                    for side in ("side_a", "side_b"):
                        for threshold, value in cell[side].items():
                            check(
                                f"seed{seed_record['seed']}.{key}.{name}.{side}.{threshold}",
                                value,
                                expected[side][threshold],
                            )
                    for count in ("n_a", "n_b"):
                        check(
                            f"seed{seed_record['seed']}.{key}.{name}.{count}",
                            cell[count],
                            expected[count],
                        )
    return {
        "exact": not differences,
        "quantities_checked": comparisons,
        "mismatch_count": len(differences),
        "mismatch_names": [item["quantity"] for item in differences],
        "counts_verified": not differences,
        "tolerance": "Exact equality at original output precision; no tolerance.",
    }


def trace_group(trace, events, denominator):
    recipients = {event[0] for event in events}
    workers = {event[1] for event in events}
    records = {(event[1], event[2]) for event in events}
    recipient = aggregate_group(
        recipients, records, trace.study.weight, denominator
    )
    worker = aggregate_group(workers, records, trace.study.weight, 0.0)
    worker.pop("admitted_weight_share")
    return {"admitted_recipients": recipient, "workers": worker}


def suppress_complementary_cells(cells):
    """Withhold a sex-paired count and changes that expose a small residual."""
    for table in cells.values():
        suppressed = [
            name
            for name, cell in table.items()
            if cell.get("affected_people") == "<10"
        ]
        for name in suppressed:
            status, sex = name.rsplit(":", 1)
            opposite = "female" if sex == "male" else "male"
            partner = f"{status}:{opposite}"
            if partner not in table:
                continue
            count = table[partner].get("affected_people")
            if isinstance(count, int) and count > 0:
                table[partner] = {
                    "affected_people": "suppressed_complementary",
                    "model_share_changes_pp": "suppressed_complementary",
                }
    return cells


def headline_changes(module, legacy, statutory, affected, unsupported):
    """Changes in aggregate values, suppressing every small affected cell."""
    n_affected = len(affected)
    if 0 < n_affected < 10:
        return {
            "status": "suppressed",
            "reason": "<10 affected admitted recipients",
            "all_committed_model_headline_changes": "<10",
        }
    before = model_headlines(module, legacy)
    after = model_headlines(module, statutory)
    cells = {}
    for variant, table in before["shares"].items():
        cells[variant] = {}
        for name, cell in table.items():
            status, sex = name.split(":")
            local = (
                set(
                    legacy.loc[
                        (legacy.status == status) & (legacy.sex == sex),
                        "person_id",
                    ]
                )
                & affected
            )
            if 0 < len(local) < 10:
                cells[variant][name] = {
                    "affected_people": "<10",
                    "model_share_changes_pp": "<10",
                }
            else:
                cells[variant][name] = {
                    "affected_people": len(local),
                    "model_bucket_changes_pp": {
                        key: after["shares"][variant][name]["buckets"][key]
                        - value
                        for key, value in cell["buckets"].items()
                    },
                    "model_threshold_changes_pp": {
                        key: after["shares"][variant][name]["thresholds"][key]
                        - value
                        for key, value in cell["thresholds"].items()
                    },
                }
                if variant in before["floors"]:
                    cells[variant][name]["model_floor_changes_pp"] = {
                        threshold: {
                            field: round(
                                after["floors"][variant][name][threshold][
                                    field
                                ],
                                2,
                            )
                            - round(
                                before["floors"][variant][name][threshold][
                                    field
                                ],
                                2,
                            )
                            for field in ("mean", "sd")
                        }
                        for threshold in module.THRESHOLDS
                    }
    return {
        "status": "supported_subset_only" if unsupported else "computed",
        "full_statutory_amount_available": not unsupported,
        "aggregate_cost_change_pp": {
            key: after["aggregate"][key] - value
            for key, value in before["aggregate"].items()
        },
        "model_shares": suppress_complementary_cells(cells),
    }


def imported_source_identity(source_dir, other_dir):
    """Prove both pins supply identical bytes for the executed closure."""
    paths = {R7_SCRIPT, *EXTRA_PATHS}
    for module in tuple(sys.modules.values()):
        filename = getattr(module, "__file__", None)
        if filename is None:
            continue
        path = Path(filename)
        if path.is_relative_to(source_dir / "src") and path.suffix == ".py":
            paths.add(str(path.relative_to(source_dir)))
    proof = []
    for relative in sorted(paths):
        left = (source_dir / relative).read_bytes()
        right = (other_dir / relative).read_bytes()
        if left != right:
            raise RuntimeError("historical R7 imported closure differs")
        proof.append({"path": relative, "sha256": sha256(left).hexdigest()})
    return proof


def retain_unsupported_rows(legacy, statutory, unsupported_recipients):
    """Keep unsupported placeholders without mixing pandas column dtypes."""
    if not unsupported_recipients:
        return statutory
    mask = statutory.person_id.isin(unsupported_recipients)
    for column in statutory.columns:
        statutory.loc[mask, column] = legacy.loc[mask, column]
    return statutory


def worker(source_dir, result_name, commit, output):
    print(f"d1408 {result_name}: importing historical model", flush=True)
    reads = install_read_guard()
    module = model_module(source_dir)
    params = load_pinned_parameters(PARAMETER_COMMIT)
    print(
        f"d1408 {result_name}: building original admitted input frame",
        flush=True,
    )
    cache = SCRATCH / "sharing-study-records.pkl"
    if cache.exists():
        with cache.open("rb") as stream:
            cached = pickle.load(stream)
        if cached["code_commit"] != commit:
            raise RuntimeError("historical study cache commit differs")
        study = cached["study"]
        reads.update(cached["real_data_files_read"])
    else:
        study = module.StudyData(params)
        with cache.open("wb") as stream:
            pickle.dump(
                {
                    "code_commit": commit,
                    "study": study,
                    "real_data_files_read": sorted(reads),
                },
                stream,
            )
    print(
        f"d1408 {result_name}: tracing original benefit evaluations",
        flush=True,
    )
    trace = CreditTrace(module, study)
    with (
        trace.instrument(),
        credit_convention(statutory=False, callback=trace.callback),
    ):
        legacy = module.score_population(study)
    admitted = set(legacy.person_id)
    events = {event for event in trace.events if event[0] in admitted}
    supported = {event for event in events if event[5] >= 1917}
    unsupported = {event for event in events if event[5] < 1917}
    unsupported_recipients = {event[0] for event in unsupported}
    trace.collect = False
    print(
        f"d1408 {result_name}: carrying statutory convention through payments",
        flush=True,
    )
    with credit_convention(statutory=True):
        statutory = module.score_population(study)
    # A pre-1917 recipient has no statutory amount: retain the whole legacy
    # row only as a placeholder for supported-subset change accounting.
    statutory = retain_unsupported_rows(
        legacy, statutory, unsupported_recipients
    )
    if list(statutory.person_id) != list(legacy.person_id):
        raise RuntimeError("statutory convention changed admitted denominator")
    artifact_path = (
        ROOT
        / "runs"
        / (
            "replication_r7_sharing_v1.json"
            if result_name == "r7_sharing"
            else "replication_cost_ordering_v1.json"
        )
    )
    artifact = json.loads(artifact_path.read_text())
    reproduced = reproduction_check(module, legacy, artifact, result_name)
    denominator = float(legacy.weight.sum())
    changed = set(
        legacy.loc[
            (legacy.baseline != statutory.baseline)
            | (legacy.delta_1a != statutory.delta_1a)
            | (legacy.delta_1b != statutory.delta_1b),
            "person_id",
        ]
    )
    result = {
        "label": HEADER,
        "result": result_name,
        "artifact": str(artifact_path.relative_to(ROOT)),
        "code_commit": commit,
        "parameter_commit": PARAMETER_COMMIT,
        "code_commit_reason": (
            "The R7 artifact's revision_pins.populace_dynamics_sha records "
            "this code commit."
            if result_name == "r7_sharing"
            else "The committed cost-ordering artifact records this code commit. Only its R7 model component is reconstructed."
        ),
        "admitted": {"people": len(legacy), "weight": denominator},
        "flagged_supported": trace_group(trace, supported, denominator),
        "flagged_pre_1917": trace_group(trace, unsupported, denominator),
        "pre_1917_refusal": {
            "reason_code": "POSITIVE_DELAYED_CREDIT_BEFORE_1917_UNSUPPORTED",
            "authority": "42 USC 402(w)(6)(A); POMS RS 00615.692D-E",
            "statutory_amount": None,
        },
        "flagged_all": trace_group(trace, events, denominator),
        "flow": {
            "entered_changed_computed_payment": trace_group(
                trace,
                {event for event in supported if event[0] in changed},
                denominator,
            ),
            "computed_own_payment": trace_group(
                trace,
                {e for e in events if e[4] == "computed_own_payment"},
                denominator,
            ),
            "linked_survivor_basis": trace_group(
                trace,
                {e for e in events if e[4] == "linked_survivor_basis"},
                denominator,
            ),
            "inverse_ms5_pia": "Not on either historical R7 path.",
            "disability_basis": "Not on either historical R7 path; registered R7 excludes DI and disability conversions.",
        },
        "changes": headline_changes(
            module,
            legacy,
            statutory,
            {event[0] for event in supported},
            unsupported_recipients,
        ),
        "reproduction": reproduced,
        "method": {
            "input_building": "Original StudyData and benefit helpers selected unmodified from historical AST; no registered run/main or anchor helper is executed.",
            "claim_inputs": "Exact deterministic expectations over each original sex/year claim-age PMF. No sampled claim ages; registered seeds 0-4 drive only person-disjoint half-split floors, cross-checked exactly.",
            "late_months": "Original claiming.months_late: max(0,min(int(claim_age_months),840)-cohort FRA).",
            "flag": "1917<=birth_year<=1942 and late_months>48; or birth_year<1917 and late_months>0.",
            "worker_record_definition": "Unique worker person plus original/shared earnings basis; multiple PMF calls and admitted recipients are deduplicated.",
            "weight_definition": "Recipients: original admitted last observed PSID weights and share of all admitted weight. Workers: their own last observed PSID weights; linked workers can lie outside admitted frame, so no denominator share is assigned.",
            "rounding": "Historical PIA dollar/dime rules, float household operations, and headline rounding remain exactly as registered. No new G whole-dollar payment rounding is introduced.",
            "pre_1917": "Statutorily unsupported; kept in every denominator, no statutory amount. Headline changes cover supported records only if any such recipient exists.",
            "suppression": "Any positive affected group below 10 people has its entire count/weight/share/change cell suppressed as <10. Zero affected groups are structural zeros.",
        },
        "guard_findings": [
            "The initial source/artifact inspection inadvertently displayed embedded external-anchor fields and small original half-split cells from authorized repository files. No comparator path, restricted source, result comment or evidence artifact was opened. None of those fields is used or reproduced in the diagnostic.",
            "Subsequent historical execution selects model AST nodes only, and cross-checks model fields only. No registered one-shot entry point executes; committed artifacts are read only.",
            "A temporary historical StudyData cache is confined to scratch/d1408, keyed to its code commit, and deleted after successful aggregate output. Trace events and payment rows stay in memory.",
        ],
        "real_data_files_read": sorted(reads),
    }
    write_aggregate(output, result)
    print(f"d1408 {result_name}: aggregate diagnostics written", flush=True)
    cache.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--source-dir", type=Path)
    parser.add_argument("--result", choices=("r7_sharing", "cost_ordering_r7"))
    parser.add_argument("--commit")
    parser.add_argument(
        "--output", type=Path, default=SCRATCH / "sharing-aggregate.json"
    )
    args = parser.parse_args()
    if args.worker:
        worker(args.source_dir, args.result, args.commit, args.output)
        return
    results = []
    commands = []
    # Each result runs at its own recorded commit; neither borrows the
    # other's reconstruction.
    for result_name, commit in (
        ("r7_sharing", R7_COMMIT),
        ("cost_ordering_r7", COST_COMMIT),
    ):
        source_dir = export_history(commit, extra_paths=EXTRA_PATHS)
        output = SCRATCH / (result_name + "-aggregate.json")
        env = dict(os.environ)
        env.update(
            PYTHONPATH=f"{source_dir / 'src'}:{ROOT / 'scripts'}",
            OMP_NUM_THREADS="1",
            POLARS_MAX_THREADS="1",
            OPENBLAS_NUM_THREADS="1",
            MKL_NUM_THREADS="1",
            PYTHONDONTWRITEBYTECODE="1",
        )
        command = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--worker",
            "--source-dir",
            str(source_dir),
            "--result",
            result_name,
            "--commit",
            commit,
            "--output",
            str(output),
        ]
        subprocess.run(command, env=env, cwd=ROOT, check=True)
        commands.append(command)
        results.append(json.loads(output.read_text()))
    write_aggregate(
        args.output,
        {"label": HEADER, "results": results, "commands": commands},
    )
    print(
        "R7 and cost-ordering aggregates written; no registered artifact modified."
    )


if __name__ == "__main__":
    main()
