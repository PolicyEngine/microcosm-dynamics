"""Invented mortality steps; no native population or fitted-data execution."""

import json
from dataclasses import FrozenInstanceError, replace
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from populace_dynamics.engine.loop import PeriodContext
from populace_dynamics.engine.rng import ProjectionRNGRegistry
from populace_dynamics.engine.steps import (
    AgeSexMortalityModel,
    apply_mortality,
)
from populace_dynamics.mortality_observer import (
    MortalityStepObservation,
    observe_mortality,
)
from populace_dynamics.person_identity import PersonIdentity, PersonIdentityMap


@pytest.fixture
def inputs():
    identities = [
        PersonIdentity("int64", 2**53 + 1),
        PersonIdentity("uint64", 2**64 - 1),
        PersonIdentity("string", "01"),
        PersonIdentity("string", "1"),
    ]
    mapping = PersonIdentityMap.from_identities(identities)
    frame = pd.DataFrame(
        {
            "person_id": np.array([3, 1, 0, 2], dtype="int64"),
            "age": np.array([120, 0, 30, 65], dtype="int64"),
            "year": np.full(4, 2014, dtype="int64"),
            "sex": ["male", "female", "female", "male"],
            "untouched": pd.array([1, None, 3, 4], dtype="Int64"),
        },
        index=[11, 12, 13, 14],
    )
    model = AgeSexMortalityModel(
        ((0, 64), (65, 120)),
        {
            ("0-64", "female"): 0.3,
            ("0-64", "male"): 0.7,
            ("65+", "female"): 0.2,
            ("65+", "male"): 0.8,
        },
    )
    context = PeriodContext(1, 2015, 3, {})
    kwargs = dict(
        model=model,
        identity_map=mapping,
        realization_id="invented-draw-3",
        source_contract_digest="a" * 64,
    )
    return frame, context, kwargs


@pytest.mark.parametrize("registry", [False, True])
@pytest.mark.parametrize("probability", [None, 0.0, 1.0])
@pytest.mark.parametrize("empty", [False, True])
def test_actual_step_matches_output_and_rng(
    inputs, registry, probability, empty
):
    frame, context, kwargs = inputs
    if empty:
        frame = frame.iloc[:0]
    if probability is not None:
        kwargs["model"] = AgeSexMortalityModel(
            kwargs["model"].bands,
            dict.fromkeys(kwargs["model"].probability, probability),
        )
    if registry:
        context = replace(
            context,
            rng_registry=ProjectionRNGRegistry(3, 5),
            person_ordinals={0: 8, 1: 6, 2: 9, 3: 7},
        )
    direct_rng, observed_rng = np.random.default_rng(
        81
    ), np.random.default_rng(81)
    original = frame.copy(deep=True)
    expected = apply_mortality(
        frame, context, direct_rng, model=kwargs["model"]
    )
    with patch(
        "populace_dynamics.mortality_observer.apply_mortality",
        wraps=apply_mortality,
    ) as called:
        actual, record = observe_mortality(
            frame, context, observed_rng, **kwargs
        )
    assert called.call_count == 1
    assert_frame_equal(actual, expected)
    assert_frame_equal(frame, original)
    assert direct_rng.bit_generator.state == observed_rng.bit_generator.state
    assert record.pre_keys == tuple(sorted(frame.person_id))
    assert record.post_keys == tuple(actual.person_id)
    assert record.target_year == 2015
    assert record.identity_map.reverse_rows(record.pre_keys) == kwargs[
        "identity_map"
    ].reverse_rows(record.pre_keys)
    restored = MortalityStepObservation.from_json(
        record.to_json(),
        identity_map=kwargs["identity_map"],
        expected_digest=record.digest,
    )
    assert restored == record
    assert restored.to_json() == record.to_json()


@pytest.mark.parametrize(
    "column,values",
    [
        ("age", [-1, 0, 30, 65]),
        ("age", [121, 0, 30, 65]),
        ("age", [120.0, 0.0, 30.0, 65.0]),
        ("age", [120, 0, 30.9, 65]),
        ("age", [120, 0, None, 65]),
        ("sex", ["other"] * 4),
        ("sex", [None] * 4),
        ("person_id", [0, 0, 1, 2]),
        ("person_id", [0, 1, 2, 99]),
        ("person_id", [0.0, 1.0, 2.0, 3.0]),
        ("person_id", [True, False, True, False]),
        ("year", [2013] * 4),
    ],
)
def test_invalid_frame_fails_before_rng(inputs, column, values):
    frame, context, kwargs = inputs
    frame[column] = values
    rng = np.random.default_rng(22)
    state = rng.bit_generator.state
    with patch(
        "populace_dynamics.mortality_observer.apply_mortality"
    ) as called:
        with pytest.raises(ValueError):
            observe_mortality(frame, context, rng, **kwargs)
        called.assert_not_called()
    assert state == rng.bit_generator.state


@pytest.mark.parametrize(
    "changes",
    [
        {"period_index": 0},
        {"period_index": 1.0},
        {"draw_index": -1},
        {"year": True},
        {"rng_registry": ProjectionRNGRegistry(2, 5)},
        {"rng_registry": ProjectionRNGRegistry(3, 0)},
        {"person_ordinals": {0: 0, 1: 0, 2: 2, 3: 3}},
        {"person_ordinals": {0: 0, 1: 1}},
        {"person_ordinals": {0: 0, 1: 1, 2: 2, 3: -1}},
        {"person_ordinals": {0: 0, 1: 1, 2: 2, 3: 3.0}},
    ],
)
def test_invalid_context_fails_without_generators(inputs, changes):
    frame, context, kwargs = inputs
    context = replace(
        context,
        rng_registry=ProjectionRNGRegistry(3, 5),
        person_ordinals={i: i for i in range(4)},
    )
    context = replace(context, **changes)
    rng = np.random.default_rng(22)
    state = rng.bit_generator.state
    with patch.object(ProjectionRNGRegistry, "person_generator") as generator:
        with patch(
            "populace_dynamics.mortality_observer.apply_mortality"
        ) as called:
            with pytest.raises(ValueError):
                observe_mortality(frame, context, rng, **kwargs)
            called.assert_not_called()
        generator.assert_not_called()
    assert state == rng.bit_generator.state


def test_snapshot_death_identity_and_permutation(inputs):
    frame, context, kwargs = inputs
    kwargs["model"].probability.update(
        dict.fromkeys(kwargs["model"].probability, 1.0)
    )
    _, record = observe_mortality(
        frame, context, np.random.default_rng(2), **kwargs
    )
    _, reordered = observe_mortality(
        frame.iloc[::-1], context, np.random.default_rng(2), **kwargs
    )
    assert record == reordered
    before = record.to_json(), record.digest
    assert record.post_keys == ()
    assert len(record.identity_map.reverse_rows(record.pre_keys)) == 4
    kwargs["model"].probability[("0-64", "female")] = 0.0
    frame.loc[:, "age"] = 1
    assert (record.to_json(), record.digest) == before
    with pytest.raises(FrozenInstanceError):
        record.target_year = 2000
    with pytest.raises(FrozenInstanceError):
        record.rows[0].survived = True


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d.update(target_year="2016"),
        lambda d: d.update(extra=True),
        lambda d: d["rows"][0].update(survived="false"),
        lambda d: d["rows"][0].update(age="030"),
        lambda d: d["rows"].append(d["rows"][0]),
        lambda d: d["model"][0].__setitem__(2, "nan"),
        lambda d: d["model"][0].__setitem__(2, "0x1.0000000000000p-1"),
    ],
)
def test_json_tampering_is_rejected(inputs, mutation):
    frame, context, kwargs = inputs
    _, record = observe_mortality(
        frame, context, np.random.default_rng(2), **kwargs
    )
    document = json.loads(record.to_json())
    mutation(document)
    with pytest.raises(ValueError):
        MortalityStepObservation.from_json(
            json.dumps(document),
            identity_map=kwargs["identity_map"],
            expected_digest=record.digest,
        )


def test_json_external_map_and_duplicate_fields(inputs):
    frame, context, kwargs = inputs
    _, record = observe_mortality(
        frame, context, np.random.default_rng(2), **kwargs
    )
    other = PersonIdentityMap.from_identities(
        [PersonIdentity("string", str(i)) for i in range(4)]
    )
    with pytest.raises(ValueError, match="identity map"):
        MortalityStepObservation.from_json(
            record.to_json(), identity_map=other
        )
    duplicate = record.to_json().replace("{", '{"schema":"duplicate",', 1)
    with pytest.raises(ValueError, match="duplicate"):
        MortalityStepObservation.from_json(
            duplicate, identity_map=kwargs["identity_map"]
        )


def test_mutated_model_fails_before_call(inputs):
    frame, context, kwargs = inputs
    kwargs["model"].probability[("0-64", "female")] = float("nan")
    with patch(
        "populace_dynamics.mortality_observer.apply_mortality"
    ) as called:
        with pytest.raises(ValueError):
            observe_mortality(
                frame, context, np.random.default_rng(2), **kwargs
            )
        called.assert_not_called()


@pytest.mark.parametrize(
    "field,value",
    [
        ("realization_id", ""),
        ("source_contract_digest", "invalid"),
        ("identity_map", {}),
    ],
)
def test_bad_provenance_is_rejected_before_call(inputs, field, value):
    frame, context, kwargs = inputs
    kwargs[field] = value
    with patch(
        "populace_dynamics.mortality_observer.apply_mortality"
    ) as called:
        with pytest.raises(ValueError):
            observe_mortality(
                frame, context, np.random.default_rng(2), **kwargs
            )
        called.assert_not_called()


def test_one_registry_draw_per_input_row(inputs):
    frame, context, kwargs = inputs
    context = replace(
        context,
        rng_registry=ProjectionRNGRegistry(3, 5),
        person_ordinals={0: 5, 1: 8, 2: 13, 3: 9},
    )
    real_generator = ProjectionRNGRegistry.person_generator
    with patch.object(
        ProjectionRNGRegistry,
        "person_generator",
        autospec=True,
        side_effect=real_generator,
    ) as generators:
        _, record = observe_mortality(
            frame, context, np.random.default_rng(2), **kwargs
        )
    assert generators.call_count == len(frame)
    assert [call.args[-1] for call in generators.call_args_list] == [
        5,
        8,
        13,
        9,
    ]
    assert [row.person_ordinal for row in record.rows] == [5, 8, 13, 9]


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d.update(schema="unsupported"),
        lambda d: d.update(model_digest="0" * 64),
        lambda d: d["rows"][0].update(extra=0),
        lambda d: d["rows"][0].update(dynamics_person_key="99"),
        lambda d: d["rows"][0].update(person_ordinal="0"),
        lambda d: d["model"][0].__setitem__(2, "0x1p999999999"),
        lambda d: d["model"][0].__setitem__(2, "0x1.0p-1"),
        lambda d: d["model"].__setitem__(
            0, ["0", "60", "0x0.0p+0", "0x0.0p+0"]
        ),
    ],
)
def test_invalid_json_rejected_without_expected_digest(inputs, change):
    frame, context, kwargs = inputs
    _, record = observe_mortality(
        frame, context, np.random.default_rng(2), **kwargs
    )
    document = json.loads(record.to_json())
    change(document)
    with pytest.raises(ValueError):
        MortalityStepObservation.from_json(
            json.dumps(document), identity_map=kwargs["identity_map"]
        )


def test_detached_parameters_cannot_mutate_and_preserve_effective_hex(inputs):
    frame, context, kwargs = inputs
    kwargs["model"].probability[("0-64", "female")] = np.float32(0.3)
    _, record = observe_mortality(
        frame, context, np.random.default_rng(2), **kwargs
    )
    assert record.model.cells[0][2] == float(np.float32(0.3)).hex()
    detached = record.model.to_model()
    with pytest.raises(TypeError):
        detached.probability[("0-64", "female")] = 0.0


def test_float_band_endpoints_refused_even_if_native_model_accepts(inputs):
    frame, context, kwargs = inputs
    kwargs["model"] = AgeSexMortalityModel(
        ((0.0, 120.0),), {("0.0+", "female"): 0.5, ("0.0+", "male"): 0.5}
    )
    with patch(
        "populace_dynamics.mortality_observer.apply_mortality"
    ) as called:
        with pytest.raises(ValueError):
            observe_mortality(
                frame, context, np.random.default_rng(2), **kwargs
            )
        called.assert_not_called()
