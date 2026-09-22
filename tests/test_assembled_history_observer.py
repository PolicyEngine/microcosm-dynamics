"""Invented observations through the actual eight-step assembly callbacks."""

import copy
import json
import pickle
from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from populace_dynamics.assembled_history_observer import (
    AssembledHistoryObservation,
    capture_fertility,
    observe_assembled_history,
)
from populace_dynamics.data import disability, household_composition
from populace_dynamics.engine import assembly, steps
from populace_dynamics.engine.assembly import (
    M6_DRAW_OUTPUTS_KEY,
    CertifiedEngineInputs,
    assemble_period_modules,
)
from populace_dynamics.engine.loop import (
    SCHEDULED_ENTRIES_KEY,
    MaritalStepResult,
    ProjectionEngine,
    SyntheticPersonIdAllocator,
)
from populace_dynamics.engine.steps import (
    AgeSexMortalityModel,
    ClaimingSchedule,
    FertilityDraws,
)
from populace_dynamics.engine.support import StartWaveWeightSnapshot
from populace_dynamics.mortality_observer import MortalityModelSnapshot
from populace_dynamics.person_identity import PersonIdentity, PersonIdentityMap
from tests.test_m6_engine_correlated_refresh import _correlated
from tests.test_m6_engine_forward_earnings import _generator


def assembled(
    monkeypatch,
    *,
    birth=False,
    entries=False,
    correlated=False,
    parent_id=1,
    extinction=False,
):
    """Reuse the assembly test's bounded fitted-core seams, actual callbacks."""
    empty = pd.DataFrame(
        {
            "parent_person_id": pd.Series(dtype="int64"),
            "birth_year": pd.Series(dtype="Int64"),
        }
    )
    births = (
        pd.DataFrame({"parent_person_id": [parent_id], "birth_year": [2015]})
        if birth
        else empty
    )
    calls = []
    family = SimpleNamespace(name="invented family")
    household = SimpleNamespace(family_transitions=family, male_gap=-2.0)

    def marital(*args, **kwargs):
        calls.append("marital")
        return MaritalStepResult(
            pd.DataFrame(
                {
                    "person_id": pd.Series(dtype="int64"),
                    "year": pd.Series(dtype="int64"),
                }
            ),
            empty,
            panel=object(),
        )

    def fertility(*args, **kwargs):
        return FertilityDraws(births.copy(), empty.copy())

    panel = disability.DisabilityPanel(
        pd.DataFrame(
            {
                "person_id": pd.Series(dtype="int64"),
                "period": pd.Series(dtype="int64"),
                "sex": pd.Series(dtype="str"),
                "age": pd.Series(dtype="int64"),
                "weight": pd.Series(dtype="float64"),
                **{
                    c: pd.Series(dtype="bool")
                    for c in ("disabled", "retired", "di_converted")
                },
                "status_code": pd.Series(dtype="int64"),
            }
        ),
        pd.DataFrame(),
    )

    def simulate_disability(*args, **kwargs):
        calls.append("disability")
        return panel

    def composition(*args, **kwargs):
        calls.append("household")
        rows = pd.DataFrame(
            {
                "person_id": pd.Series(dtype="int64"),
                "year": pd.Series(dtype="int64"),
                **{
                    c: pd.Series(dtype="float64")
                    for c in (
                        "coresident_spouse",
                        "coresident_parent",
                        "coresident_child",
                        "coresident_grandchild",
                        "multigen",
                        "hh_size",
                    )
                },
            }
        )
        return (
            household_composition.HouseholdCompositionPanel(
                rows, pd.DataFrame()
            ),
            {},
        )

    monkeypatch.setattr(assembly, "simulate_marital_step", marital)
    monkeypatch.setattr(steps, "simulate_fertility", fertility)
    monkeypatch.setattr(assembly, "simulate_fertility", fertility)
    monkeypatch.setattr(assembly, "simulate_reproduction", simulate_disability)
    monkeypatch.setattr(assembly, "simulate_candidate9_injected", composition)
    model = AgeSexMortalityModel(
        ((0, 120),),
        {("0+", "female"): (1.0 if extinction else 0.0), ("0+", "male"): 1.0},
    )
    if extinction:
        model = AgeSexMortalityModel(
            ((0, 29), (30, 120)),
            {
                ("0-29", "female"): 0.0,
                ("0-29", "male"): 0.0,
                ("30+", "female"): 1.0,
                ("30+", "male"): 1.0,
            },
        )
    generator = _correlated(rho=-0.5) if correlated else _generator()
    if parent_id != 1:
        generator = replace(
            generator,
            **{
                name: {
                    parent_id if key == 1 else key: value
                    for key, value in getattr(generator, name).items()
                }
                for name in (
                    "u_w_by_person",
                    "realized_earn_2014_by_person",
                    "realized_earn_2012_by_person",
                )
            },
        )
    initial = pd.DataFrame(
        {
            "person_id": np.array([20, parent_id, 10], dtype="int64"),
            "year": np.full(3, 2014, dtype="int64"),
            "age": np.array([35, 30, 31], dtype="int64"),
            "sex": ["male", "female", "female"],
            "weight": np.ones(3),
        }
    )
    scheduled = (
        {
            2016: pd.DataFrame(
                {
                    "person_id": np.array([2], dtype="int64"),
                    "year": np.array([2015], dtype="int64"),
                    "age": np.array([40], dtype="int64"),
                    "sex": ["male"],
                    "weight": [1.0],
                }
            )
        }
        if entries
        else {}
    )
    if entries and extinction:
        scheduled[2016]["age"] = np.array([10], dtype="int64")
        scheduled[2016]["sex"] = "female"
        scheduled[2016]["earnings_domain"] = False
        scheduled[2016]["earnings"] = 0.0
    inputs = CertifiedEngineInputs(
        family,
        object(),
        object(),
        household,
        model,
        object(),
        ClaimingSchedule(
            {("female", 2014): {62: 1.0}, ("male", 2014): {62: 1.0}}
        ),
        generator,
        lambda f, c: (object(), set(f.person_id)),
        lambda f, c: (object(), set(f.person_id)),
        panel,
        set(),
        StartWaveWeightSnapshot.from_frame(
            initial[["person_id", "weight"]], boundary_period=2014
        ),
        -2.0,
    )
    modules = assemble_period_modules(inputs)
    mapping = PersonIdentityMap.from_identities(
        PersonIdentity("int64", x) for x in initial.person_id
    )
    kwargs = dict(
        mode="original_2014_view",
        identity_map=mapping,
        realization_id="invented-assembly-person-side-draw3",
        generator_digest="a" * 64,
        earnings_source_contract_digest="b" * 64,
        mortality_snapshot=MortalityModelSnapshot.from_model(model),
        mortality_snapshot_after=MortalityModelSnapshot.from_model(model),
        mortality_source_contract_digest="c" * 64,
        unit="XTS",
        price_basis="nominal",
        lineage_by_year={y: "d" * 64 for y in range(2014, 2023)},
        initial_native_ids=tuple(initial.person_id),
        scheduled_entries_by_year=scheduled,
        reserved_real_ids=frozenset([parent_id, 2, 10, 20]),
        synthetic_id_start=100,
    )

    def run(*, capture=True, draw=3):
        selected, boundary = (
            capture_fertility(modules) if capture else (modules, None)
        )
        collector = {}
        result = ProjectionEngine(selected).project(
            initial,
            end_year=2022,
            draw_index=draw,
            metadata={
                M6_DRAW_OUTPUTS_KEY: collector,
                SCHEDULED_ENTRIES_KEY: scheduled,
                "synthetic_id_allocator": SyntheticPersonIdAllocator(
                    100, frozenset([parent_id, 2, 10, 20])
                ),
            },
        )
        return result, collector, boundary

    run.modules = modules
    return run, kwargs, calls, generator


@pytest.mark.parametrize("correlated", [False, True])
@pytest.mark.parametrize("entries", [False, True])
def test_actual_assembly_observation_preserves_every_frame_and_collector(
    monkeypatch, correlated, entries
):
    run, kwargs, calls, generator = assembled(
        monkeypatch, correlated=correlated, entries=entries
    )
    from populace_dynamics.engine.rng import ProjectionRNGRegistry

    streams = []
    for name in ("generator", "person_generator", "child_generator"):
        original = getattr(ProjectionRNGRegistry, name)

        def track(self, *args, _method=original, _name=name, **kw):
            rng = _method(self, *args, **kw)
            streams.append((_name, args, kw, rng))
            return rng

        monkeypatch.setattr(ProjectionRNGRegistry, name, track)
    control, control_outputs, _ = run(capture=False)
    control_states = [
        (name, args, kw, pickle.dumps(r.bit_generator.state))
        for name, args, kw, r in streams
    ]
    streams.clear()
    result, outputs, capture = run()
    assert [
        (name, args, kw, pickle.dumps(r.bit_generator.state))
        for name, args, kw, r in streams
    ] == control_states
    assert pickle.dumps(outputs, protocol=5) == pickle.dumps(
        control_outputs, protocol=5
    )
    for name in ("generator", "person_generator", "child_generator"):
        monkeypatch.setattr(
            ProjectionRNGRegistry,
            name,
            lambda *a, **k: pytest.fail("observer created RNG stream"),
        )
    before = pickle.dumps((result, outputs, generator), protocol=5)
    observed = observe_assembled_history(
        result, outputs, fertility_capture=capture, **kwargs
    )
    assert pickle.dumps((result, outputs, generator), protocol=5) == before
    for left, right in zip(control.slices, result.slices, strict=True):
        assert_frame_equal(left, right, check_exact=True)
    for left, right in zip(
        control_outputs["mortality_slices"],
        outputs["mortality_slices"],
        strict=True,
    ):
        assert_frame_equal(left, right, check_exact=True)
    assert calls == ["marital", "disability", "household"] * 2
    assert observed.history.last_year == 2022
    assert len(observed.history.histories) == 3
    assert (
        observed.history.for_person(PersonIdentity("int64", 20)).last_year
        == 2014
    )
    audit = json.loads(observed.audit_json)
    if entries:
        assert audit["excluded"] == [
            {
                "native_id": "2",
                "kind": "scheduled_entry",
                "entry_year": 2016,
                "death_year": 2016,
                "parent_id": None,
            }
        ]
        # Native numeric ordering includes entrant 2; lexical private keys do not.
        native10 = next(x for x in audit["identity_bindings"] if x[0] == "10")
        assert native10[2] == "2"
    text = observed.to_json()
    assert (
        AssembledHistoryObservation.from_json(
            text,
            baseline=observed.history.baseline,
            expected_digest=observed.digest,
        )
        == observed
    )


def test_births_require_matching_fertility_boundary(monkeypatch):
    run, kwargs, _, _ = assembled(monkeypatch, birth=True, entries=True)
    result, outputs, capture = run()
    assert all(
        t.authoritative_marital_state.births.empty for t in result.traces
    )
    with pytest.raises(ValueError, match="capture"):
        observe_assembled_history(result, outputs, **kwargs)
    observed = observe_assembled_history(
        result, outputs, fertility_capture=capture, **kwargs
    )
    births = [
        x
        for x in json.loads(observed.audit_json)["excluded"]
        if x["kind"] == "native_synthetic_birth"
    ]
    assert len(births) == 1 and births[0]["parent_id"] == "1"
    with pytest.raises(ValueError, match="strict"):
        observe_assembled_history(
            result,
            outputs,
            fertility_capture=capture,
            **{**kwargs, "mode": "strict_full_roster"},
        )


def test_capture_calls_original_once_by_identity_and_refuses_reuse(
    monkeypatch,
):
    run, kwargs, _, _ = assembled(monkeypatch)
    result, outputs, capture = run()
    observe_assembled_history(
        result, outputs, fertility_capture=capture, **kwargs
    )
    assert len(capture.records) == 8
    # Construction never evaluates a model or creates an RNG stream.
    monkeypatch.setattr(
        AgeSexMortalityModel,
        "probabilities",
        lambda *a: pytest.fail("model call"),
    )
    monkeypatch.setattr(
        MortalityModelSnapshot,
        "to_model",
        lambda *a: pytest.fail("model copy"),
    )
    observe_assembled_history(
        result, outputs, fertility_capture=capture, **kwargs
    )


@pytest.mark.parametrize(
    "change",
    [
        "missing_period",
        "death_flag",
        "baseline_age",
        "entrant_schedule",
        "disappearance",
    ],
)
def test_refuses_incomplete_or_contradictory_full_evidence(
    monkeypatch, change
):
    run, kwargs, _, _ = assembled(monkeypatch, entries=True)
    result, outputs, capture = run()
    outputs = copy.deepcopy(outputs)
    if change == "missing_period":
        outputs["mortality_slices"].pop()
    elif change == "death_flag":
        outputs["mortality_slices"][0].loc[0, "death"] = False
    elif change == "baseline_age":
        result.slices[0].loc[0, "age"] += 1
    elif change == "entrant_schedule":
        kwargs["scheduled_entries_by_year"] = {}
    elif change == "disappearance":
        result.slices[1].drop(result.slices[1].index[0], inplace=True)
    with pytest.raises(ValueError):
        observe_assembled_history(
            result, outputs, fertility_capture=capture, **kwargs
        )


def test_serialized_selection_audit_is_bound_with_history(monkeypatch):
    run, kwargs, _, _ = assembled(monkeypatch, entries=True)
    result, outputs, capture = run()
    observed = observe_assembled_history(
        result, outputs, fertility_capture=capture, **kwargs
    )
    data = json.loads(observed.to_json())
    data["audit"]["excluded"] = []
    with pytest.raises(ValueError):
        AssembledHistoryObservation.from_json(
            json.dumps(data),
            baseline=observed.history.baseline,
            expected_digest=observed.digest,
        )


@pytest.mark.parametrize("parent_id", [2**53, 2**53 + 1, 2**53 + 2])
def test_native_float_parent_ambiguity_refuses_even_with_capture(
    monkeypatch, parent_id
):
    run, kwargs, _, _ = assembled(monkeypatch, birth=True, parent_id=parent_id)
    result, outputs, capture = run()
    # Native concat promotes the nullable parent column to float64.
    assert result.slices[1].parent_person_id.dtype == np.dtype("float64")
    with pytest.raises(ValueError, match="parent"):
        observe_assembled_history(
            result, outputs, fertility_capture=capture, **kwargs
        )


def test_large_native_ids_roundtrip_without_unsafe_parent_column(monkeypatch):
    native = 2**53 + 1
    run, kwargs, _, _ = assembled(monkeypatch, parent_id=native)
    result, outputs, capture = run()
    observed = observe_assembled_history(
        result, outputs, fertility_capture=capture, **kwargs
    )
    assert (
        observed.history.for_person(PersonIdentity("int64", native)).last_year
        == 2022
    )
    bindings = json.loads(observed.audit_json)["identity_bindings"]
    assert str(native) in [row[0] for row in bindings]


def test_strict_mode_and_no_capture_work_for_unchanged_roster(monkeypatch):
    run, kwargs, _, _ = assembled(monkeypatch)
    result, outputs, _ = run(capture=False)
    observed = observe_assembled_history(
        result, outputs, **{**kwargs, "mode": "strict_full_roster"}
    )
    assert not json.loads(observed.audit_json)["excluded"]


def test_pre_post_parameter_binding_must_match(monkeypatch):
    run, kwargs, _, _ = assembled(monkeypatch)
    result, outputs, _ = run(capture=False)
    other = MortalityModelSnapshot(((0, 120, (0.1).hex(), (1.0).hex()),))
    with pytest.raises(ValueError, match="parameter"):
        observe_assembled_history(
            result, outputs, **{**kwargs, "mortality_snapshot_after": other}
        )


def test_capture_preserves_exact_callback_arguments_result_and_rng(
    monkeypatch,
):
    from populace_dynamics.engine.loop import PeriodContext
    from populace_dynamics.engine.rng import ProjectionRNGRegistry

    run, _, _, _ = assembled(monkeypatch)
    frame = pd.DataFrame({"x": [1]})
    context = PeriodContext(1, 2015, 3, {}, ProjectionRNGRegistry(3, 1))
    marital = object()
    rng, control = np.random.default_rng(4), np.random.default_rng(4)
    calls = []
    output = pd.DataFrame({"x": [2]})

    def original(f, c, m, r):
        assert f is frame and c is context and m is marital and r is rng
        calls.append(r.random())
        return output

    modules = replace(run.modules, fertility=original)
    wrapped, capture = capture_fertility(modules)
    for name in (
        "mortality",
        "aging",
        "marital_core",
        "disability",
        "earnings",
        "claiming",
        "household_composition",
        "initialize",
    ):
        assert getattr(wrapped, name) is getattr(modules, name)
    assert wrapped.fertility(frame, context, marital, rng) is output
    assert calls == [control.random()]
    assert rng.bit_generator.state == control.bit_generator.state
    saved = capture.records[0].after_json
    archived = json.loads(capture.to_json())
    assert archived["schema"] == "assembled-fertility-boundaries/v1"
    assert archived["records"][0][-1] == saved
    output.loc[0, "x"] = 7
    assert capture.records[0].after_json == saved
    with pytest.raises(ValueError, match="reused"):
        wrapped.fertility(frame, context, marital, rng)
    assert len(calls) == 1
    with pytest.raises(ValueError, match="failed"):
        capture._require_complete(3, 1)
    with pytest.raises(ValueError, match="failed"):
        capture.to_json()


def test_failed_callback_cannot_yield_accepted_capture(monkeypatch):
    from populace_dynamics.engine.loop import PeriodContext
    from populace_dynamics.engine.rng import ProjectionRNGRegistry

    run, _, _, _ = assembled(monkeypatch)

    def fail(*args):
        raise RuntimeError("callback failure")

    wrapped, capture = capture_fertility(replace(run.modules, fertility=fail))
    context = PeriodContext(1, 2015, 3, {}, ProjectionRNGRegistry(3, 1))
    with pytest.raises(RuntimeError, match="callback failure"):
        wrapped.fertility(
            pd.DataFrame({"x": [1]}),
            context,
            object(),
            np.random.default_rng(1),
        )
    with pytest.raises(ValueError, match="failed"):
        capture._require_complete(3, 1)
    assert capture.records == ()


@pytest.mark.parametrize(
    "change",
    [
        "wrong_capture",
        "incomplete_capture",
        "float_id",
        "age_jump",
        "unknown_added",
        "birth_parent",
        "resurrection",
    ],
)
def test_refuses_roster_or_capture_tampering(monkeypatch, change):
    run, kwargs, _, _ = assembled(monkeypatch, birth=True, entries=True)
    result, outputs, capture = run()
    if change == "wrong_capture":
        _, _, capture = run(draw=4)
    elif change == "incomplete_capture":
        capture._records.pop()
    elif change == "float_id":
        result.slices[1]["person_id"] = result.slices[1].person_id.astype(
            float
        )
    elif change == "age_jump":
        result.slices[1].loc[result.slices[1].person_id == 1, "age"] += 1
    elif change == "unknown_added":
        result.slices[1].loc[
            result.slices[1].person_id == 100, "person_id"
        ] = 101
    elif change == "birth_parent":
        result.slices[1].loc[
            result.slices[1].person_id == 100, "parent_person_id"
        ] = 10.0
    elif change == "resurrection":
        # Original 20 died in 2015. A changed label cannot resurrect that key.
        result.slices[2].loc[result.slices[2].person_id == 1, "person_id"] = 20
    with pytest.raises(ValueError):
        observe_assembled_history(
            result, outputs, fertility_capture=capture, **kwargs
        )


@pytest.mark.parametrize(
    "mutation", ["drop_exclusion", "ordinal", "extra_field", "mode"]
)
def test_canonical_audit_revalidates_internal_consistency(
    monkeypatch, mutation
):
    run, kwargs, _, _ = assembled(monkeypatch, entries=True)
    result, outputs, capture = run()
    observed = observe_assembled_history(
        result, outputs, fertility_capture=capture, **kwargs
    )
    audit = json.loads(observed.audit_json)
    if mutation == "drop_exclusion":
        audit["excluded"] = []
    elif mutation == "ordinal":
        audit["identity_bindings"][1][2] = "0"
    elif mutation == "extra_field":
        audit["unrecognized"] = 1
    elif mutation == "mode":
        audit["mode"] = "strict_full_roster"
    with pytest.raises(ValueError):
        AssembledHistoryObservation(
            observed.history,
            json.dumps(audit, sort_keys=True, separators=(",", ":")),
        )


def test_full_cohort_extinction_retains_each_history_and_empty_period(
    monkeypatch,
):
    run, kwargs, _, _ = assembled(monkeypatch, extinction=True)
    result, outputs, capture = run()
    assert all(frame.empty for frame in result.slices[1:])
    observed = observe_assembled_history(
        result, outputs, fertility_capture=capture, **kwargs
    )
    assert observed.history.last_year == 2022
    assert observed.history.active_keys == ()
    assert all(h.last_year == 2014 for h in observed.history.histories)
    assert len(observed.history.transitions) == 8


def test_original_cohort_definition_cannot_select_only_survivors(monkeypatch):
    run, kwargs, _, _ = assembled(monkeypatch)
    result, outputs, capture = run()
    with pytest.raises(ValueError, match="initial cohort"):
        observe_assembled_history(
            result,
            outputs,
            fertility_capture=capture,
            **{**kwargs, "initial_native_ids": (1, 10)},
        )


def test_changed_initial_demographics_refuse_even_first_mortality_step(
    monkeypatch,
):
    run, kwargs, _, _ = assembled(monkeypatch)
    result, outputs, capture = run()
    outputs["mortality_slices"][0].loc[0, "sex"] = "female"
    with pytest.raises(ValueError, match="demographic"):
        observe_assembled_history(
            result, outputs, fertility_capture=capture, **kwargs
        )


def test_validly_rehashed_bad_selection_still_refuses(monkeypatch):
    import hashlib

    run, kwargs, _, _ = assembled(monkeypatch, entries=True)
    result, outputs, capture = run()
    observed = observe_assembled_history(
        result, outputs, fertility_capture=capture, **kwargs
    )
    data = json.loads(observed.to_json())
    data["audit"]["excluded"] = []
    text = json.dumps(data, sort_keys=True, separators=(",", ":"))
    with pytest.raises(ValueError, match="excluded"):
        AssembledHistoryObservation.from_json(
            text,
            baseline=observed.history.baseline,
            expected_digest=hashlib.sha256(text.encode()).hexdigest(),
        )


@pytest.mark.parametrize("outside_int64", [-(2**63) - 1, 2**63])
def test_rehashed_noncohort_identity_must_remain_native_int64(
    monkeypatch, outside_int64
):
    import hashlib

    run, kwargs, _, _ = assembled(monkeypatch, birth=True)
    result, outputs, capture = run()
    observed = observe_assembled_history(
        result, outputs, fertility_capture=capture, **kwargs
    )
    data = json.loads(observed.to_json())

    def replace_birth(value):
        if isinstance(value, list):
            return [replace_birth(x) for x in value]
        if isinstance(value, dict):
            return {k: replace_birth(v) for k, v in value.items()}
        return str(outside_int64) if value == "100" else value

    data["audit"] = replace_birth(data["audit"])
    text = json.dumps(data, sort_keys=True, separators=(",", ":"))
    with pytest.raises(ValueError, match="signed int64"):
        AssembledHistoryObservation.from_json(
            text,
            baseline=observed.history.baseline,
            expected_digest=hashlib.sha256(text.encode()).hexdigest(),
        )


def test_original_cohort_extinction_does_not_hide_remaining_entrant(
    monkeypatch,
):
    run, kwargs, _, _ = assembled(monkeypatch, entries=True, extinction=True)
    result, outputs, capture = run()
    observed = observe_assembled_history(
        result, outputs, fertility_capture=capture, **kwargs
    )
    assert observed.history.active_keys == ()
    assert result.slices[-1].person_id.tolist() == [2]
    assert json.loads(observed.audit_json)["excluded"][0]["death_year"] is None
    assert all(h.last_year == 2014 for h in observed.history.histories)


def test_safe_exact_range_float_parent_is_supported(monkeypatch):
    native = 2**53 - 1
    run, kwargs, _, _ = assembled(monkeypatch, birth=True, parent_id=native)
    result, outputs, capture = run()
    observed = observe_assembled_history(
        result, outputs, fertility_capture=capture, **kwargs
    )
    birth = next(
        x
        for x in json.loads(observed.audit_json)["excluded"]
        if x["kind"] == "native_synthetic_birth"
    )
    assert birth["parent_id"] == str(native)
