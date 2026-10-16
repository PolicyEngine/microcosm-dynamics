"""Exercise d1408's complete benefit/tabulation adapters on invented data.

Both retained projection paths are assembled from in-memory invented
cohorts, parameters, mortality, DI rates and claim PMFs. No PSID reader,
registration entry point, real parameter loader or public output writer
is called. Invented checkpoint round trips use pytest's temporary directory.
"""

from collections import defaultdict
from contextlib import nullcontext
from types import SimpleNamespace

import pandas as pd
import pytest

from populace_dynamics.cohorts import psid2010
from populace_dynamics.cola_track_a import (
    invented,
    prepare_track_a_cohort,
)
from populace_dynamics.cola_track_a import runner as track_runner
from populace_dynamics.cola_track_a.adapters import claiming_schedule
from populace_dynamics.cola_track_a.benefits import StateLookups
from populace_dynamics.cola_track_a.config import REGISTERED_ROWS
from populace_dynamics.cola_track_a.opening import track_a_cohort_sha256
from populace_dynamics.engine.di_entitlement import (
    fra_schedule_from_parameters,
)
from populace_dynamics.estimates.cola_age_profile import (
    INVENTED_DATA_LABEL,
    ColaAgeProfileConfig,
    _normalize,
    tabulate_cola_age_profile,
)
from populace_dynamics.fra68_track import runner as fra_runner
from scripts import d1408_projection as diagnostic
from scripts.d1408_common import credit_convention
from tests.cola_track_a import test_assembly as cola_fixtures
from tests.fra68_track import test_runner as fra_fixtures


@pytest.mark.parametrize("kind", ("cola", "fra68"))
def test_invented_projection_benefit_rows_and_headlines(
    kind, monkeypatch, tmp_path
):
    def forbidden(*_args, **_kwargs):
        raise AssertionError(
            "invented smoke must not read or write real inputs"
        )

    monkeypatch.setattr(psid2010, "load_psid2010_inputs", forbidden)
    monkeypatch.setattr(diagnostic, "load_pinned_parameters", forbidden)
    monkeypatch.setattr(diagnostic, "write_aggregate", forbidden)
    if kind == "fra68":
        stock_trace = diagnostic.Trace()
        stock_trace.wave = 2011
        stock_trace.cohort = SimpleNamespace(
            persons_by_id=pd.DataFrame({"weight": [1.0]}, index=[1])
        )

        def opening_stock_factor_ratio():
            stock_trace.callback(58, 1938, None)

        def opening_scenario(record):
            opening_stock_factor_ratio()

        opening_scenario(SimpleNamespace(person_id=1))
        assert stock_trace.events[
            ("supported", "opening_stock_adjustment")
        ] == {(2011, 1, "old_age")}
        config = fra_fixtures.CONFIG
        track = config.track_a_config()
        inputs = fra_fixtures._inputs()
    else:
        config = track = cola_fixtures.CONFIG
        cohort = prepare_track_a_cohort(
            psid2010.build_psid2010_cohort(
                invented.invented_psid2010_inputs(seed=7)
            ),
            data_provenance="invented",
            config=track,
        )
        inputs = cola_fixtures._inputs(cohort)
    schedule = claiming_schedule(
        inputs.claiming_pmf, max_table_year=track.claim_table_max_year
    )
    cohorts = (inputs.cohort, *inputs.additional_cohorts)
    all_rows = {False: defaultdict(list), True: defaultdict(list)}
    labels = {}
    row_waves = {}
    trace = diagnostic.Trace()
    for cohort in cohorts:
        original_hash = track_a_cohort_sha256(cohort)
        checkpoint = tmp_path / f"{kind}-{cohort.anchor_wave}-cohort.pickle"
        diagnostic.checkpoint_write(
            checkpoint,
            cohort,
            commit="invented_fixture",
            kind=kind,
            reads={"invented_audit_marker"},
        )
        restored_reads = set()
        restored = diagnostic.checkpoint_load(
            checkpoint,
            commit="invented_fixture",
            kind=kind,
            reads=restored_reads,
        )
        assert restored_reads == {"invented_audit_marker"}
        assert type(restored) is type(cohort)
        assert track_a_cohort_sha256(restored) == original_hash
        assert restored.seal == cohort.seal
        pd.testing.assert_frame_equal(restored.persons, cohort.persons)
        pd.testing.assert_frame_equal(
            restored.initial_slice, cohort.initial_slice
        )
        assert restored.source_provenance == cohort.source_provenance
        cohort = restored
        trace.wave, trace.cohort = cohort.anchor_wave, cohort
        print(f"invented {kind}: projecting wave {cohort.anchor_wave}")
        results, _ = track_runner._project_population(
            cohort,
            inputs,
            track,
            schedule=schedule,
            fra_schedule=fra_schedule_from_parameters(inputs.params),
            progress=print,
        )
        print(f"invented {kind}: projected wave {cohort.anchor_wave}")
        assert set(results) == set(track.draw_indices)
        checkpoint = (
            tmp_path / f"{kind}-{cohort.anchor_wave}-projection.pickle"
        )
        diagnostic.checkpoint_write(
            checkpoint,
            results,
            commit="invented_fixture",
            kind=kind,
            reads={"invented_audit_marker"},
        )
        restored_reads = set()
        restored_results = diagnostic.checkpoint_load(
            checkpoint,
            commit="invented_fixture",
            kind=kind,
            reads=restored_reads,
        )
        assert restored_reads == {"invented_audit_marker"}
        assert set(restored_results) == set(results)
        for draw in results:
            original, restored = results[draw], restored_results[draw]
            assert type(restored) is type(original)
            assert restored.draw_index == original.draw_index
            assert len(restored.slices) == len(original.slices)
            for first, second in zip(
                original.slices, restored.slices, strict=True
            ):
                pd.testing.assert_frame_equal(first, second)
        results = restored_results
        for statutory in (False, True):
            pia_cache = {}
            with (
                nullcontext() if statutory else trace.payment_flows(kind)
            ), credit_convention(
                statutory=statutory,
                callback=None if statutory else trace.callback,
            ):
                for draw, result in results.items():
                    rows = diagnostic.benefit_rows_for_draw(
                        kind,
                        config,
                        track,
                        cohort,
                        inputs,
                        result,
                        draw,
                        StateLookups(result, track.reference_year),
                        pia_cache,
                        trace=None if statutory else trace,
                    )
                    assert set(rows) == set(
                        config.rows_for_wave(cohort.anchor_wave)
                    )
                    for row_id, built in rows.items():
                        assert built
                        assert {item["draw"] for item in built} == {draw}
                        all_rows[statutory][row_id].extend(built)
                        labels[row_id] = cohort.labels
                        row_waves[row_id] = cohort.anchor_wave
    assert set(all_rows[False]) == set(config.rows)
    assert set(all_rows[True]) == set(config.rows)
    assert trace.row_id is None
    for (row_id, _support, _role), records in trace.row_events.items():
        if row_id in row_waves:
            assert all(record[0] == row_waves[row_id] for record in records)
    for row_id in config.rows:
        if kind == "cola":
            row = REGISTERED_ROWS[row_id]
            tab_config = ColaAgeProfileConfig(
                reference_year=track.reference_year,
                components=row.components,
                benefit_period=row.tabulation_benefit_period,
                headline_statistic=row.headline_statistic,
                draw_indices=track.draw_indices,
                floor_seeds=track.floor_seeds,
            )
            extra = {}
        else:
            tab_config = fra_runner._tabulation_config(
                config.row(row_id), config
            )
            extra = {
                "statistic_id": fra_runner.STATISTIC_ID,
                "pending_rulings": fra_runner.E1_RULINGS,
            }
        legacy_built = all_rows[False][row_id]
        admitted = diagnostic.row_admitted_counts(
            row_id,
            legacy_built,
            trace,
            draw_indices=track.draw_indices,
            baseline_mask=_normalize(legacy_built, tab_config).recipient_base,
        )
        assert {
            "admitted_people",
            "admitted_weight",
            "supported/factor_evaluation",
            "unsupported_pre1917/factor_evaluation",
        } <= set(admitted)
        pair = []
        for statutory in (False, True):
            built = all_rows[statutory][row_id]
            for item in built:
                item["age_reference"] = (
                    track.reference_year - item["birth_year"]
                )
            tabulation = tabulate_cola_age_profile(
                pd.DataFrame(built),
                data_provenance="invented",
                config=tab_config,
                labels=labels[row_id],
                **extra,
            )
            assert INVENTED_DATA_LABEL in tabulation["labels"]
            headline = diagnostic.model_headlines(tabulation)
            assert headline
            assert all(
                set(group)
                == {"ratio_of_scenario_means", "mean_of_individual_ratios"}
                for group in headline.values()
            )
            pair.append(headline)
        assert isinstance(diagnostic.headline_changes(*pair), dict)
    trace_summary = trace.summary({c.anchor_wave: c for c in cohorts})
    assert set(trace_summary) == {str(c.anchor_wave) for c in cohorts}
    if kind == "fra68":
        assert any(
            role == "opening_stock_adjustment"
            for _support, role in trace.events
        )
