"""Local COLA and FRA-68 delayed-credit diagnostic under ruling d1408.

Verification class: labelled diagnostic. Scope: the two retained model
results, using local PSID and each result's historical code. No registered
entry point, output path, benchmark, or comparison specification is read.
42 USC 402(w)(2)(A)'s convention changes only the credit calculation.
Positive pre-1917 evaluations remain unsupported under 402(w)(6)(A).
Record-level checkpoints are temporary, confined to scratch/d1408, and
deleted after verified completion. Published outputs contain aggregates.
"""

from __future__ import annotations

import argparse
import contextlib
import faulthandler
import functools
import inspect
import json
import math
import os
import pickle
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

try:
    from scripts.d1408_common import (
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
        write_aggregate,
    )
except ModuleNotFoundError:
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
        write_aggregate,
    )

ARTIFACTS = {
    "cola": "replication_urban2010_cola_v1",
    "fra68": "replication_urban2010_fra68_v1",
}
EXTRAS = (
    "data/external/tr2008",
    "data/external/ssa_claim_ages_2014supplement.json",
    "data/external/ssa_cola_history.json",
    "data/external/di_asr_2008/tables.json",
    "data/external/nchs_life_tables_2000.json",
)


def artifact_commit(artifact):
    commit = artifact["run"]["registered_commit"]
    if artifact["run"]["git_head"] != commit:
        raise ValueError("artifact registered_commit and git_head differ")
    return commit


def checkpoint_path(kind, commit, stage, wave):
    """Record-level temporary checkpoints are confined to scratch/d1408."""
    return SCRATCH / f"{kind}-{commit}-{stage}-{wave}.pickle"


def checkpoint_load(path, *, commit, kind, reads):
    """Admit a cached frame only with the same model commit and result."""
    for suffix in (".retain", ".replay"):
        retained = path.with_suffix(suffix)
        if not path.exists() and retained.exists():
            retained.replace(path)
    if not path.exists():
        return None
    with path.open("rb") as handle:
        payload = pickle.load(handle)
    if payload["code_commit"] != commit or payload["kind"] != kind:
        raise ValueError("d1408 checkpoint code identity differs")
    reads.update(payload["real_data_files_read"])
    return payload["value"]


def checkpoint_write(path, value, *, commit, kind, reads):
    """Save a same-commit checkpoint atomically, without any public rows."""
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(".partial")
    with partial.open("wb") as handle:
        pickle.dump(
            {
                "code_commit": commit,
                "kind": kind,
                "real_data_files_read": sorted(reads),
                "value": value,
            },
            handle,
            protocol=pickle.HIGHEST_PROTOCOL,
        )
    partial.replace(path)


def protect_age_partition(groups):
    """Withhold large complements of a suppressed positive age cell."""
    if any(group["changed_recipients"] == "<10" for group in groups.values()):
        for group in groups.values():
            count = group["changed_recipients"]
            if isinstance(count, int) and count > 0:
                group["changed_recipients"] = "suppressed_complementary"
                group["model_headlines"] = "suppressed_complementary"


def small_associated_complement(people, associated):
    return people.issubset(associated) and 0 < len(associated - people) < 10


def protect_row_overlaps(changes, private_sets, row_waves):
    """Withhold overlapping totals when differencing reveals a small cell."""
    hidden = set()
    for first, left in private_sets.items():
        for second, right in private_sets.items():
            if first == second:
                continue
            if 0 < len(left - right) < 10 or 0 < len(right - left) < 10:
                hidden.update((first, second))
    for row in hidden:
        cell = changes[row]
        if (
            isinstance(cell["changed_recipients"], int)
            and cell["changed_recipients"] > 0
        ):
            cell["changed_recipients"] = "suppressed_complementary"
        for group in cell["groups"].values():
            if (
                isinstance(group["changed_recipients"], int)
                and group["changed_recipients"] > 0
            ):
                group["changed_recipients"] = "suppressed_complementary"
                group["model_headlines"] = "suppressed_complementary"


def selected_changed_people(left, right):
    """Compare original selected payments and recipient masks across windows."""

    def selected_rows(normalized):
        return {
            (int(draw), int(person)): (
                float(base),
                float(reform),
                bool(base_recipient),
                bool(reform_recipient),
            )
            for draw, person, base, reform, base_recipient, reform_recipient in zip(
                normalized.draw,
                normalized.person_id,
                normalized.selected_base,
                normalized.selected_reform,
                normalized.recipient_base,
                normalized.recipient_reform,
                strict=True,
            )
        }

    before, after = selected_rows(left), selected_rows(right)
    return {
        person
        for draw, person in before.keys() | after.keys()
        if before.get((draw, person)) != after.get((draw, person))
    }


def row_admitted_counts(
    row_id, data, trace, draw_indices, *, baseline_mask=None
):
    """Deduplicate the original tabulator's selected baseline recipients.

    Real reconstruction always supplies the historical normalized mask.
    Minimal invented adapter tests can omit it for a total-positive frame.
    """
    if baseline_mask is None:
        baseline_mask = [
            item["beneficiary_base"] and item["benefit_base"] > 0
            for item in data
        ]
        frame = "invented total-positive baseline frame"
    else:
        frame = "original tabulator selected-component baseline recipient mask"
    admitted = [
        item
        for item, recipient in zip(data, baseline_mask, strict=True)
        if recipient
    ]
    observations = defaultdict(list)
    for item in admitted:
        observations[int(item["person_id"])].append(float(item["weight"]))
    weights = {
        person: math.fsum(values) / len(values)
        for person, values in observations.items()
    }
    denominator = math.fsum(weights.values())
    result = {
        "admitted_people": len(weights),
        "admitted_weight": denominator,
        "mean_draw_admitted_weight": math.fsum(
            item["weight"] for item in admitted
        )
        / len(draw_indices),
        "denominator": f"{frame}; distinct people across draws, each person's weight averaged over their admitted draws; baseline frame is separate from the headline's common-recipient frame",
    }
    if 0 < len(weights) < 10:
        result.update(
            {
                key: "<10"
                for key in (
                    "admitted_people",
                    "admitted_weight",
                    "mean_draw_admitted_weight",
                )
            }
        )
    for support in ("supported", "unsupported_pre1917"):
        total_records = trace.row_events[
            (row_id, support, "factor_evaluation")
        ]
        associations = trace.row_events[(row_id, support, "recipient")]
        associated_people = {
            recipient
            for _, recipient, _ in associations
            if recipient in weights
        }
        for role in (
            "factor_evaluation",
            "available_pia",
            "linked_spouse_basis",
            "deceased_auxiliary_basis",
            "positive_worker_payment",
            "positive_survivor_payment",
            "positive_spouse_basis_factor_unused",
            "positive_opening_stock_adjustment",
        ):
            records = trace.row_events[(row_id, support, role)]
            links = trace.row_events[(row_id, support, f"{role}_recipient")]
            if not links:
                links = {
                    (wave, recipient, worker)
                    for wave, recipient, worker in associations
                    if (wave, worker, "old_age") in records
                }
            people = {
                recipient for _, recipient, _ in links if recipient in weights
            }
            selected = {
                (wave, worker, "old_age")
                for wave, recipient, worker in links
                if recipient in people
            }
            if role == "positive_opening_stock_adjustment":
                selected.update(
                    record for record in records if record[1] in weights
                )
                people.update(record[1] for record in selected)
            group = aggregate_group(people, selected, weights, denominator)
            if (0 < len(selected) < 10 and len(people) >= 10) or (
                len(people) >= 10
                and (
                    0 < len(total_records - selected) < 10
                    or 0 < len(set(weights) - people) < 10
                    or (small_associated_complement(people, associated_people))
                )
            ):
                group = {key: "suppressed_complementary" for key in group}
            result[f"{support}/{role}"] = group
    return result


class Trace:
    """Track original worker identity and payment role without disk rows."""

    def __init__(self):
        self.wave = None
        self.cohort = None
        self.events = defaultdict(set)
        self.row_events = defaultdict(set)
        self.row_id = None
        self.weights = {}
        self.latest_records = {}

    def emit(self, support, role, record):
        self.events[(support, role)].add(record)
        if self.row_id is not None:
            self.row_events[(self.row_id, support, role)].add(record)

    @contextlib.contextmanager
    def row(self, row_id):
        previous = self.row_id
        self.row_id = row_id
        try:
            yield
        finally:
            self.row_id = previous

    def copy_row(self, source, target):
        for (row, support, role), records in list(self.row_events.items()):
            if row == source:
                self.row_events[(target, support, role)].update(
                    record for record in records if record[0] == self.wave
                )

    def _record_region(self, calculator, record):
        """Use the final returned record, including any undone FRA credit."""
        if (
            record is None
            or record.kind != "retired"
            or record.entitlement_year is None
            or record.claim_age_factor <= 1.0
        ):
            return None
        birth = int(calculator.statics.at[record.person_id, "birth_year"])
        age = getattr(record, "reform_claim_month", None)
        if age is None:
            age = 12 * min(record.entitlement_year - birth, 70)
        late = age - calculator.ctx.params.fra_months(birth)
        if not flagged(late, birth):
            return None
        support = "unsupported_pre1917" if birth < 1917 else "supported"
        return support, (self.wave, int(record.person_id), "old_age")

    def _positive_record(self, calculator, record, role, *, recipient=None):
        region = self._record_region(calculator, record)
        if region is not None:
            support, key = region
            self.emit(support, role, key)
            if recipient is not None:
                self.emit(
                    support,
                    f"{role}_recipient",
                    (self.wave, int(recipient), int(record.person_id)),
                )

    @contextlib.contextmanager
    def payment_flows(self, kind):
        """Observe original positive returns; preserve every money operation.

        Final record returns distinguish an FRA credit that was undone
        after death. Spouse payments read PIA only, so their delayed factor
        is tagged unused. The observer runs only on legacy evaluations.
        """
        from populace_dynamics.cola_track_a.benefits import _Calculator

        classes = [_Calculator]
        if kind == "fra68":
            from populace_dynamics.fra68_track.benefits import (
                ScenarioCalculator,
            )

            classes.append(ScenarioCalculator)
        restored = []

        def wrap_record(original):
            @functools.wraps(original)
            def observed(calculator, *args, **kwargs):
                result = original(calculator, *args, **kwargs)
                record = (
                    result[0] if original.__name__ == "_decedent" else result
                )
                if record is not None:
                    self.latest_records[
                        (id(calculator), int(record.person_id))
                    ] = record
                return result

            return observed

        def wrap_paths(original):
            @functools.wraps(original)
            def observed(calculator, record, *args, **kwargs):
                result = original(calculator, record, *args, **kwargs)
                if any(
                    path.get(calculator.payment_year, 0.0) > 0
                    for path in result
                ):
                    self._positive_record(
                        calculator,
                        record,
                        "positive_worker_payment",
                        recipient=record.person_id,
                    )
                return result

            return observed

        def wrap_auxiliary(original, *, widow):
            @functools.wraps(original)
            def observed(calculator, person_id, state, *args, **kwargs):
                result = original(
                    calculator, person_id, state, *args, **kwargs
                )
                if result is not None:
                    amounts = result[0] if widow else result
                    if any(amount > 0 for amount in amounts):
                        field = (
                            "late_spouse_person_id"
                            if widow
                            else "spouse_person_id"
                        )
                        worker = state[field]
                        # A positive original excess requires a resolved worker.
                        record = self.latest_records.get(
                            (id(calculator), int(worker))
                        )
                        self._positive_record(
                            calculator,
                            record,
                            (
                                "positive_survivor_payment"
                                if widow
                                else "positive_spouse_basis_factor_unused"
                            ),
                            recipient=person_id,
                        )
                return result

            return observed

        def wrap_opening(original):
            @functools.wraps(original)
            def observed(calculator, record, *args, **kwargs):
                result = original(calculator, record, *args, **kwargs)
                if record.component == "retired_worker" and any(
                    v > 0 for v in result[0].values()
                ):
                    birth = int(
                        calculator.statics.at[record.person_id, "birth_year"]
                    )
                    age = calculator.opening_claim_age_months(record)
                    if age is not None:
                        for params in (
                            calculator.scenario.baseline_params,
                            calculator.ctx.params,
                        ):
                            if flagged(age - params.fra_months(birth), birth):
                                support = (
                                    "unsupported_pre1917"
                                    if birth < 1917
                                    else "supported"
                                )
                                self.emit(
                                    support,
                                    "positive_opening_stock_adjustment",
                                    (
                                        self.wave,
                                        int(record.person_id),
                                        "old_age",
                                    ),
                                )
                return result

            return observed

        try:
            for cls in classes:
                for name in (
                    "worker_record",
                    "deceased_record",
                    "_decedent",
                    "_worker_paths",
                    "_spouse_excess",
                    "_widow_excess",
                    "opening_scenario",
                ):
                    original = cls.__dict__.get(name)
                    if original is None:
                        continue
                    if name in (
                        "worker_record",
                        "deceased_record",
                        "_decedent",
                    ):
                        wrapper = wrap_record(original)
                    elif name == "_worker_paths":
                        wrapper = wrap_paths(original)
                    elif name == "opening_scenario":
                        wrapper = wrap_opening(original)
                    else:
                        wrapper = wrap_auxiliary(
                            original, widow=name == "_widow_excess"
                        )
                    restored.append((cls, name, original))
                    setattr(cls, name, wrapper)
            yield
        finally:
            for cls, name, original in reversed(restored):
                setattr(cls, name, original)

    def callback(self, late, birth, params):
        if not flagged(late, birth):
            return
        frame = inspect.currentframe().f_back
        worker = None
        recipient = None
        calculator = None
        names = set()
        pia_available = False
        while frame is not None:
            names.add(frame.f_code.co_name)
            values = frame.f_locals
            if frame.f_code.co_name == "worker_record" and worker is None:
                worker = values.get("person_id")
                calculator = values.get("self")
                pia_available = values.get("pia") is not None
            if frame.f_code.co_name == "_claim_response" and worker is None:
                record = values.get("record")
                worker = None if record is None else record.person_id
                calculator = values.get("self")
                pia_available = (
                    record is not None and record.eligibility_pia is not None
                )
            if (
                frame.f_code.co_name
                in (
                    "opening_scenario",
                    "opening_stock_factor_ratio",
                    "scenario_benefits",
                )
                and worker is None
            ):
                opener = values.get("opener")
                if (
                    opener is None
                    and frame.f_code.co_name == "opening_scenario"
                ):
                    opener = values.get("record")
                if opener is not None:
                    worker = opener.person_id
            if frame.f_code.co_name in (
                "projected_person",
                "opening_scenario",
                "reference_benefit_rows",
                "scenario_benefits",
            ):
                recipient = values.get("person_id", recipient)
                opener = values.get("opener")
                if recipient is None and opener is not None:
                    recipient = opener.person_id
            frame = frame.f_back
        if worker is None:
            raise RuntimeError(
                "flagged evaluation has no original worker identity"
            )
        worker = int(worker)
        support = "unsupported_pre1917" if birth < 1917 else "supported"
        record = (self.wave, worker, "old_age")
        self.emit(support, "factor_evaluation", record)
        self.weights[(self.wave, worker)] = float(
            self.cohort.persons_by_id.at[worker, "weight"]
        )
        role = "own_record"
        if "opening_stock_factor_ratio" in names:
            role = "opening_stock_adjustment"
        elif "deceased_record" in names:
            role = "deceased_auxiliary_basis"
        elif "_spouse_excess" in names:
            role = "linked_spouse_basis"
        self.emit(support, role, record)
        if pia_available:
            self.emit(support, "available_pia", record)
        if recipient is not None:
            self.emit(
                support, "recipient", (self.wave, int(recipient), worker)
            )
        # opening_person carries observed amounts; it does not enter a credit
        # evaluation. Auxiliary bases can be evaluated yet paid zero.
        del calculator

    def summary(self, waves):
        output = {}
        for wave, cohort in waves.items():
            weights = {
                (wave, int(pid)): float(row["weight"])
                for pid, row in cohort.persons_by_id.iterrows()
            }
            denominator = sum(weights.values())
            output[str(wave)] = {
                "seed_cohort_weight": denominator,
                "denominator": "full admitted seed cohort, before projected mortality or payment membership",
            }
            for (support, role), records in sorted(self.events.items()):
                selected = {r for r in records if r[0] == wave}
                people = {(r[0], r[1]) for r in selected}
                worker_records = (
                    {(r[0], r[2], "old_age") for r in selected}
                    if role == "recipient" or role.endswith("_recipient")
                    else selected
                )
                output[str(wave)][f"{support}/{role}"] = aggregate_group(
                    people, worker_records, weights, denominator
                )
                total_records = {
                    r
                    for r in self.events[(support, "factor_evaluation")]
                    if r[0] == wave
                }
                associated_people = {
                    (r[0], r[1])
                    for r in self.events[(support, "recipient")]
                    if r[0] == wave
                }
                group = output[str(wave)][f"{support}/{role}"]
                if (
                    0 < len(worker_records) < 10
                    and isinstance(group["people"], int)
                    and group["people"] >= 10
                ):
                    output[str(wave)][f"{support}/{role}"] = {
                        name: "suppressed_small_worker_cell" for name in group
                    }
                elif (
                    isinstance(group["people"], int)
                    and group["people"] >= 10
                    and (
                        0 < len(total_records - worker_records) < 10
                        or (
                            small_associated_complement(
                                people, associated_people
                            )
                        )
                    )
                ):
                    output[str(wave)][f"{support}/{role}"] = {
                        name: "suppressed_complementary" for name in group
                    }
            for support in ("supported", "unsupported_pre1917"):
                auxiliary_small = any(
                    output[str(wave)]
                    .get(f"{support}/{role}", {})
                    .get("people")
                    == "<10"
                    for role in (
                        "linked_spouse_basis",
                        "deceased_auxiliary_basis",
                    )
                )
                if auxiliary_small:
                    for role in ("own_record", "available_pia"):
                        key = f"{support}/{role}"
                        if key in output[str(wave)]:
                            output[str(wave)][key] = {
                                name: "suppressed_complementary"
                                for name in output[str(wave)][key]
                            }
        return output


def model_headlines(tabulation):
    """Select own mean, SD and floor summaries without record/benchmark rows."""
    return {
        group["label"]: {
            statistic: {
                **{
                    key: group[statistic][key] for key in ("mean", "sample_sd")
                },
                **(
                    {
                        "floor": {
                            key: value
                            for key, value in group[statistic]["floor"].items()
                            if key in ("mean", "sd", "min", "max", "n_seeds")
                        }
                    }
                    if "floor" in group[statistic]
                    else {}
                ),
            }
            for statistic in (
                "ratio_of_scenario_means",
                "mean_of_individual_ratios",
            )
        }
        for group in tabulation["groups"]
    }


def benefit_rows_for_draw(
    kind,
    config,
    track,
    cohort,
    inputs,
    result,
    draw,
    lookups,
    pia_cache,
    trace=None,
):
    """Call the original benefit interfaces for one already projected draw.

    Invented smoke tests supply every input and never enter a PSID reader.
    The caller selects the credit convention explicitly around this helper.
    """
    from populace_dynamics.cola_track_a.benefits import (
        BenefitContext,
        reference_benefit_rows,
    )
    from populace_dynamics.cola_track_a.config import REGISTERED_ROWS

    params, baseline = inputs.params, inputs.baseline
    if kind == "cola":
        context = BenefitContext(cohort, params, baseline, track)
        output = {}
        for row_id in track.rows_for_wave(cohort.anchor_wave):
            with (
                trace.row(row_id)
                if trace is not None
                else contextlib.nullcontext()
            ):
                output[row_id] = reference_benefit_rows(
                    result,
                    draw=draw,
                    row=REGISTERED_ROWS[row_id],
                    context=context,
                    pia_cache=pia_cache,
                    lookups=lookups,
                )[0]
        return output
    from populace_dynamics.fra68_track import runner as fr
    from populace_dynamics.fra68_track.benefits import union_benefit_rows

    base_scenario, reform_params, _ = fr._scenarios(config, params)
    shared = dict(
        cohort=cohort,
        inputs=inputs,
        track_config=track,
        track_row=REGISTERED_ROWS[fr.TRACK_A_ROW_BY_WAVE[cohort.anchor_wave]],
        result=result,
        lookups=lookups,
        pia_cache=pia_cache,
        assumed_birth_month=int(config.di_spec.assumed_birth_month),
    )
    with trace.row("base") if trace is not None else contextlib.nullcontext():
        base_people, _ = fr._compute_scenario(base_scenario, **shared)
    alternatives, output = {}, {}
    for row_id in config.rows_for_wave(cohort.anchor_wave):
        row = config.row(row_id)
        if row.reform_key not in alternatives:
            with (
                trace.row(row.reform_key)
                if trace is not None
                else contextlib.nullcontext()
            ):
                alternatives[row.reform_key], _ = fr._compute_scenario(
                    fr._reform_scenario(row, config, params, reform_params),
                    **shared,
                )
        if trace is not None:
            trace.copy_row("base", row_id)
            trace.copy_row(row.reform_key, row_id)
        output[row_id], _ = union_benefit_rows(
            base_people,
            alternatives[row.reform_key],
            draw=draw,
            context=BenefitContext(cohort, params, baseline, track),
            lookups=lookups,
            baseline_params=params,
            reform_params=reform_params[row.schedule_id],
        )
    return output


def run_child(kind):
    print(f"{kind}: diagnostic child pid {os.getpid()}", flush=True)
    faulthandler.enable()
    faulthandler.dump_traceback_later(300, repeat=True)
    reads = install_read_guard()
    import pandas as pd

    from populace_dynamics.cohorts import psid2010
    from populace_dynamics.cola_track_a import runner as tr
    from populace_dynamics.cola_track_a.adapters import claiming_schedule
    from populace_dynamics.cola_track_a.benefits import StateLookups
    from populace_dynamics.cola_track_a.config import (
        REGISTERED_ROWS,
        TrackAConfig,
    )
    from populace_dynamics.cola_track_a.mortality import load_tr2008_mortality
    from populace_dynamics.cola_track_a.opening import prepare_track_a_cohort
    from populace_dynamics.engine.di_entitlement import (
        fra_schedule_from_parameters,
    )
    from populace_dynamics.engine.di_entitlement_rates import (
        load_di_entitlement_rates,
    )
    from populace_dynamics.estimates.cola_age_profile import (
        ColaAgeProfileConfig,
        _normalize,
        tabulate_cola_age_profile,
    )
    from populace_dynamics.estimates.parameters import load_cola_history

    artifact = json.loads(
        (ROOT / "runs" / f"{ARTIFACTS[kind]}.json").read_text()
    )
    commit = artifact_commit(artifact)
    if (
        not Path(tr.__file__)
        .resolve()
        .is_relative_to((SCRATCH / f"src-{commit}").resolve())
    ):
        raise ValueError(
            "real diagnostic must use its artifact's historical code"
        )
    checkpoints = []
    if kind == "fra68":
        from populace_dynamics.fra68_track import runner as fr
        from populace_dynamics.fra68_track.config import FRA68Config

        config = FRA68Config()
        track = config.track_a_config()
    else:
        config = track = TrackAConfig()
    cohorts = {}
    for wave in track.anchor_waves:
        cached = checkpoint_path(kind, commit, "cohort", wave)
        checkpoints.append(cached)
        prepared = checkpoint_load(
            cached, commit=commit, kind=kind, reads=reads
        )
        if prepared is not None:
            cohorts[wave] = prepared
            print(f"{kind}: resumed prepared wave {wave}", flush=True)
            continue
        print(f"{kind}: reading wave {wave}", flush=True)
        raw = psid2010.load_psid2010_inputs(
            anchor_wave=wave, data_dir=PSID_ROOT
        )
        cohort = psid2010.build_psid2010_cohort(
            raw, psid2010.Psid2010CohortSpec(anchor_wave=wave)
        )
        cohorts[wave] = prepare_track_a_cohort(
            cohort, data_provenance="registered_real", config=track
        )
        checkpoint_write(
            cached, cohorts[wave], commit=commit, kind=kind, reads=reads
        )
        del raw, cohort
    tr._check_source_provenance(cohorts, "registered_real")
    for wave, cohort in cohorts.items():
        if (
            dict(cohort.source_provenance)["psid_files_sha256"]
            != artifact["inputs_provenance"]["psid_inputs"][str(wave)][
                "psid_files_sha256"
            ]
        ):
            raise ValueError(
                "projection PSID input hashes differ from the retained artifact"
            )
    pe_revision = artifact["inputs_provenance"]["ssa_parameters"].split("+")[0]
    params = tr.tr2008_ssa_parameters(load_pinned_parameters(pe_revision))
    baseline = tr.tr2008_baseline_cola(load_cola_history())
    first, *others = cohorts.values()
    inputs = tr.TrackAInputs(
        cohort=first,
        additional_cohorts=tuple(others),
        params=params,
        baseline=baseline,
        di_rates=load_di_entitlement_rates(track.di_spec),
        population_mortality=load_tr2008_mortality(
            range(
                min(track.start_years.values()) + 1, track.reference_year + 1
            ),
            alternative=track.tr2008_alternative,
            base_year=track.mortality_base_year,
        ),
        claiming_pmf=tr.load_claiming_pmf(),
    )
    schedule = claiming_schedule(
        inputs.claiming_pmf, max_table_year=track.claim_table_max_year
    )
    rows = {False: defaultdict(list), True: defaultdict(list)}
    tracer = Trace()
    projection_checks = []
    for wave, cohort in cohorts.items():
        tracer.wave, tracer.cohort = wave, cohort
        cached = checkpoint_path(kind, commit, "projection", wave)
        checkpoints.append(cached)
        projected = checkpoint_load(
            cached, commit=commit, kind=kind, reads=reads
        )
        if projected is None:
            projected = tr._project_population(
                cohort,
                inputs,
                track,
                schedule=schedule,
                fra_schedule=fra_schedule_from_parameters(params),
                progress=lambda message: print(
                    f"{kind}: {message}", flush=True
                ),
            )
            checkpoint_write(
                cached, projected, commit=commit, kind=kind, reads=reads
            )
        results, diagnostics = projected
        projection_checks.append(diagnostics == artifact["draws"][str(wave)])
        for statutory in (False, True):
            cache = {}
            with (
                credit_convention(
                    statutory=statutory,
                    callback=None if statutory else tracer.callback,
                ),
                (
                    tracer.payment_flows(kind)
                    if not statutory
                    else contextlib.nullcontext()
                ),
            ):
                for draw, result in results.items():
                    print(
                        f"{kind}: wave {wave} draw {draw} statutory={statutory}",
                        flush=True,
                    )
                    lookups = StateLookups(result, track.reference_year)
                    built_by_row = benefit_rows_for_draw(
                        kind,
                        config,
                        track,
                        cohort,
                        inputs,
                        result,
                        draw,
                        lookups,
                        cache,
                        trace=None if statutory else tracer,
                    )
                    for row_id, built in built_by_row.items():
                        rows[statutory][row_id].extend(built)
        del results
    checks, changes, private_changed, row_waves, admitted_counts = (
        {},
        {},
        {},
        {},
        {},
    )
    private_admitted = {}
    for row_id in config.rows:
        pair, normalized_pair = [], []
        for statutory in (False, True):
            data = rows[statutory][row_id]
            for item in data:
                item["age_reference"] = (
                    track.reference_year - item["birth_year"]
                )
            if kind == "cola":
                row = REGISTERED_ROWS[row_id]
                tabconfig = ColaAgeProfileConfig(
                    reference_year=track.reference_year,
                    components=row.components,
                    benefit_period=row.tabulation_benefit_period,
                    headline_statistic=row.headline_statistic,
                    draw_indices=track.draw_indices,
                    floor_seeds=track.floor_seeds,
                )
            else:
                tabconfig = fr._tabulation_config(config.row(row_id), config)
            normalized_pair.append(_normalize(data, tabconfig))
            tab = tabulate_cola_age_profile(
                pd.DataFrame(data),
                data_provenance="registered_real",
                config=tabconfig,
                registration_pointer=artifact["registration_pointer"],
                labels=artifact["rows"][row_id].get(
                    "labels", artifact["labels"]
                ),
                **(
                    {
                        "statistic_id": fr.STATISTIC_ID,
                        "pending_rulings": fr.E1_RULINGS,
                    }
                    if kind == "fra68"
                    else {}
                ),
            )
            pair.append(model_headlines(tab))
        committed = model_headlines(artifact["rows"][row_id]["tabulation"])
        checks[row_id] = pair[0] == committed
        # Store only differences, never person-level rows. Headline cells are
        # retained only when their admitted group is at least ten people.
        changed = selected_changed_people(*normalized_pair)
        private_changed[row_id] = changed
        private_admitted[row_id] = {
            int(person)
            for person, recipient in zip(
                normalized_pair[0].person_id,
                normalized_pair[0].recipient_base,
                strict=True,
            )
            if recipient
        }
        row_waves[row_id] = (
            int(config.row(row_id).anchor_wave)
            if kind == "fra68"
            else int(REGISTERED_ROWS[row_id].anchor_wave)
        )
        admitted_counts[row_id] = row_admitted_counts(
            row_id,
            rows[False][row_id],
            tracer,
            track.draw_indices,
            baseline_mask=normalized_pair[0].recipient_base,
        )
        group_changes = {}
        birth_by_person = {
            item["person_id"]: item["birth_year"]
            for item in rows[False][row_id] + rows[True][row_id]
        }
        for group in artifact["rows"][row_id]["tabulation"]["groups"]:
            label = group["label"]
            low, high = group["lower"], group["upper"]
            ids = {
                person
                for person in changed
                if low <= track.reference_year - birth_by_person[person]
                and (
                    high is None
                    or track.reference_year - birth_by_person[person] <= high
                )
            }
            group_changes[label] = {
                "changed_recipients": "<10" if 0 < len(ids) < 10 else len(ids),
                "model_headlines": (
                    "<10"
                    if 0 < len(ids) < 10
                    else headline_changes(pair[0][label], pair[1][label])
                ),
            }
        protect_age_partition(group_changes)
        changes[row_id] = {
            "changed_recipients": (
                "<10" if 0 < len(changed) < 10 else len(changed)
            ),
            "groups": group_changes,
        }
    protect_row_overlaps(changes, private_changed, row_waves)
    result = {
        "header": HEADER,
        "result": kind,
        "artifact": f"runs/{ARTIFACTS[kind]}.json",
        "code_commit": artifact["run"]["registered_commit"],
        "code_commit_reason": "artifact run.registered_commit and git_head agree",
        "parameter_commit": pe_revision,
        "counts": tracer.summary(cohorts),
        "admitted_beneficiary_counts_by_row": admitted_counts,
        "reproduction_check": {
            "projection_draws_exact": all(projection_checks),
            "model_headlines_exact_by_row": checks,
            "verified": all(projection_checks) and all(checks.values()),
        },
        "headline_changes": changes,
        "changed_recipient_definition": "original selected-component baseline or reform amount, or original recipient mask, changes under the statutory window; people deduplicated across registered draws",
        "method": "Historical admitted cohorts and exact registered engine draws; original benefit and rounding functions, no registered runner. Pre1917 legacy placeholders are excluded from statutory claims.",
        "real_data_files_read": sorted(reads),
    }
    result["counts_verified"] = result["reproduction_check"]["verified"]
    checkpoint_write(
        SCRATCH / f"{kind}-publication-memberships.pickle",
        {
            "events": dict(tracer.events),
            "row_events": dict(tracer.row_events),
            "changed_people_by_row": private_changed,
            "row_waves": row_waves,
            "admitted_people_by_row": private_admitted,
        },
        commit=commit,
        kind=kind,
        reads=reads,
    )
    write_aggregate(SCRATCH / f"{kind}-aggregate.json", result)
    if result["counts_verified"]:
        for path in checkpoints:
            path.unlink(missing_ok=True)
            path.with_suffix(".retain").unlink(missing_ok=True)
            path.with_suffix(".replay").unlink(missing_ok=True)


def headline_changes(left, right):
    """Report changed numeric headline quantities with whole-cell suppression."""

    def undefined(value):
        if value is None:
            return True
        if isinstance(value, float) and not math.isfinite(value):
            return True
        if isinstance(value, dict):
            return any(undefined(item) for item in value.values())
        if isinstance(value, list):
            return any(undefined(item) for item in value)
        return False

    if left == right and not undefined(left) and not undefined(right):
        return {"all_model_headline_changes": 0.0}
    if isinstance(left, dict) and isinstance(right, dict):
        return {
            k: headline_changes(left[k], right[k])
            for k in left
            if k in right
            and (
                left[k] != right[k]
                or undefined(left[k])
                or undefined(right[k])
            )
        }
    if isinstance(left, list) and isinstance(right, list):
        return [
            headline_changes(a, b)
            for a, b in zip(left, right, strict=True)
            if a != b or undefined(a) or undefined(b)
        ]
    if undefined(left) or undefined(right):
        return {
            "change": None,
            "defined_under_legacy": not undefined(left),
            "defined_under_statutory": not undefined(right),
        }
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return right - left
    return "changed_non_numeric_metadata"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("kind", choices=(*ARTIFACTS, "publication"))
    parser.add_argument("--child", action="store_true")
    args = parser.parse_args()
    if args.kind == "publication":
        finalize_publication()
        return
    if args.child:
        run_child(args.kind)
        return
    artifact = json.loads(
        (ROOT / "runs" / f"{ARTIFACTS[args.kind]}.json").read_text()
    )
    print(f"{args.kind}: diagnostic launcher pid {os.getpid()}", flush=True)
    history = export_history(artifact_commit(artifact), EXTRAS)
    env = dict(os.environ, OMP_NUM_THREADS="1", POLARS_MAX_THREADS="1")
    env["PYTHONPATH"] = f"{history / 'src'}:{ROOT / 'scripts'}"
    subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), args.kind, "--child"],
        check=True,
        cwd=ROOT,
        env=env,
    )


def finalize_publication():
    """Audit related results from transient memberships, then delete them."""
    try:
        from scripts.d1408_projection_publication import (
            protect_cross_result_privacy,
        )
    except ModuleNotFoundError:
        from d1408_projection_publication import protect_cross_result_privacy

    install_read_guard()
    aggregates, ledgers, paths = {}, {}, {}
    for kind in ARTIFACTS:
        aggregates[kind] = json.loads(
            (SCRATCH / f"{kind}-aggregate.json").read_text()
        )
        paths[kind] = SCRATCH / f"{kind}-publication-memberships.pickle"
        ledgers[kind] = checkpoint_load(
            paths[kind],
            commit=aggregates[kind]["code_commit"],
            kind=kind,
            reads=set(),
        )
        if ledgers[kind] is None:
            raise ValueError(
                "both final publication membership ledgers required"
            )
    explanation = protect_cross_result_privacy(
        aggregates["cola"],
        aggregates["fra68"],
        ledgers["cola"],
        ledgers["fra68"],
    )
    for path in paths.values():
        path.unlink(missing_ok=True)
        path.with_suffix(".retain").unlink(missing_ok=True)
        path.with_suffix(".replay").unlink(missing_ok=True)
    for kind in ARTIFACTS:
        aggregates[kind]["cross_result_publication_audit"] = {
            "completed": True,
            "method": explanation,
            "temporary_memberships_deleted": True,
        }
        write_aggregate(SCRATCH / f"{kind}-aggregate.json", aggregates[kind])
    print(
        "COLA/FRA membership audit complete; transient memberships deleted",
        flush=True,
    )


if __name__ == "__main__":
    main()
