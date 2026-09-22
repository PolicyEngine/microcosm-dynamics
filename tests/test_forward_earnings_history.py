"""Invented projection records; no fitting, benefit or population scoring."""

import copy
import json
import pickle
from dataclasses import FrozenInstanceError, replace

import numpy as np
import pandas as pd
import pytest

from populace_dynamics.forward_earnings_history import ForwardEarningsHistory
from populace_dynamics.person_identity import PersonIdentity, PersonIdentityMap


def mapping():
    return PersonIdentityMap.from_identities(
        [PersonIdentity("uint64", 2**64 - 1), PersonIdentity("string", "001")]
    )


def frame(year=2014, values=(0.0, 0.0)):
    return pd.DataFrame(
        {
            "person_id": [0, 1],
            "year": [year, year],
            "earnings": np.asarray(values, dtype=np.float64),
            "earnings_domain": [True, False],
        }
    )


def start(data=None, **kwargs):
    return ForwardEarningsHistory.start(
        mapping(),
        frame() if data is None else data,
        realization_id="invented-career-draw-1",
        generator_digest="a" * 64,
        source_contract_digest="b" * 64,
        lineage_digest="c" * 64,
        unit="XTS",
        price_basis="nominal",
        **kwargs,
    )


def test_zero_and_outside_domain_control_zero_remain_distinct():
    history = start()
    known, missing = history.observations
    assert known.amount_state == "known_zero"
    assert known.amount_hex == float(0).hex()
    assert missing.amount_state == "unavailable"
    assert missing.amount_hex is None
    assert missing.missing_reason == "outside_forward_earnings_domain"
    assert history.identity_map.reverse_rows([1])[0].value == 2**64 - 1
    assert history.source_registry_status == "registration_required"
    assert history.coverage_status == "not_materialized"


def test_dense_append_keeps_realization_original_values_and_input_frame():
    initial = frame(values=(0.1, 0.0))
    original = initial.copy(deep=True)
    first = start(initial)
    old_json = first.to_json()
    second = first.append(frame(2015, (0.1, 0.0)), lineage_digest="d" * 64)
    third = second.append(frame(2016, (0.2, 0.0)), lineage_digest="e" * 64)
    pd.testing.assert_frame_equal(initial, original)
    assert first.to_json() == old_json
    assert third.observations[:4] == second.observations
    rows = third.for_person(PersonIdentity("string", "001"))
    assert [row.year for row in rows] == [2014, 2015, 2016]
    assert [row.generation_method for row in rows] == [
        "boundary_method",
        "odd_year_carry",
        "biennial_draw",
    ]
    assert rows[0].amount_hex == rows[1].amount_hex == (0.1).hex()
    assert rows[2].amount_hex == (0.2).hex()
    assert third.realization_id == first.realization_id
    restored = ForwardEarningsHistory.from_json(
        third.to_json(), expected_digest=third.digest
    )
    assert restored == third
    assert restored.to_json() == third.to_json()
    assert (
        ForwardEarningsHistory.from_json(third.to_json(), previous=second)
        == third
    )


def test_row_order_and_unrelated_private_lag_do_not_change_record():
    data = frame(values=(100.0, 0.0))
    data["realized_earn_2012"] = [np.nan, np.nan]
    assert start(data) == start(data.iloc[::-1].copy())
    assert start(data).observations[0].amount_hex == (100.0).hex()


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf, -1.0])
def test_invalid_supported_earnings_are_never_padded_or_floored(value):
    with pytest.raises(ValueError):
        start(frame(values=(value, 0.0)))


@pytest.mark.parametrize(
    "column,values",
    [
        ("person_id", [0.0, 1.0]),
        ("person_id", [0, 0]),
        ("person_id", [0, 2]),
        ("year", [2014.0, 2014.0]),
        ("year", [2014, 2015]),
        ("earnings_domain", [True, None]),
        ("earnings_domain", [1, 0]),
        ("earnings", [0, 0]),
    ],
)
def test_ambiguous_frame_contract_refuses(column, values):
    data = frame()
    data[column] = values
    with pytest.raises(ValueError):
        start(data)


def test_outside_domain_nonzero_is_not_discarded():
    with pytest.raises(ValueError, match="control zero"):
        start(frame(values=(0.0, 4.0)))


@pytest.mark.parametrize("year", [2014, 2016, 2023])
def test_append_requires_exact_next_year(year):
    with pytest.raises(ValueError):
        start().append(frame(year), lineage_digest="d" * 64)


def test_carry_must_preserve_exact_source_bits():
    first = start(frame(values=(-0.0, 0.0)))
    with pytest.raises(ValueError, match="carry"):
        first.append(frame(2015), lineage_digest="d" * 64)
    assert first.observations[0].amount_state == "known_zero"
    assert first.observations[0].amount_hex == (-0.0).hex()


def test_roster_or_domain_change_requires_a_separate_contract():
    first = start()
    with pytest.raises(ValueError, match="roster"):
        first.append(frame(2015).iloc[:1], lineage_digest="d" * 64)
    changed = frame(2015)
    changed["earnings_domain"] = [False, False]
    with pytest.raises(ValueError, match="domain"):
        first.append(changed, lineage_digest="d" * 64)


def test_projection_envelope_cannot_silently_extend_past_2022():
    history = start()
    for year in range(2015, 2023):
        history = history.append(frame(year), lineage_digest="d" * 64)
    with pytest.raises(ValueError, match="2022"):
        history.append(frame(2023), lineage_digest="d" * 64)


def test_loaded_missing_or_duplicate_years_refuse():
    history = start().append(frame(2015), lineage_digest="d" * 64)
    with pytest.raises(ValueError):
        replace(history, observations=history.observations[:-1])
    with pytest.raises(ValueError):
        replace(history, observations=history.observations * 2)
    with pytest.raises(ValueError):
        replace(history, observations=history.observations[:2])
    with pytest.raises(ValueError):
        replace(history, observations=history.observations[::2])


def test_serialized_tampering_and_unknown_claims_refuse():
    history = start()
    document = json.loads(history.to_json())
    document["coverage_status"] = "resolved"
    with pytest.raises(ValueError):
        ForwardEarningsHistory.from_json(json.dumps(document))
    document = json.loads(history.to_json())
    document["observations"][0]["amount_hex"] = (100.0).hex()
    with pytest.raises(ValueError, match="digest"):
        ForwardEarningsHistory.from_json(
            json.dumps(document), expected_digest=history.digest
        )
    with pytest.raises(ValueError, match="duplicate"):
        ForwardEarningsHistory.from_json('{"schema":"a","schema":"b"}')


def test_history_is_frozen_and_observation_inputs_are_snapshotted():
    history = start()
    with pytest.raises(FrozenInstanceError):
        history.realization_id = "different-career"
    with pytest.raises(FrozenInstanceError):
        history.observations[0].amount_hex = (100.0).hex()


@pytest.mark.parametrize(
    "copier",
    [
        pytest.param(
            lambda value: pickle.loads(pickle.dumps(value, protocol=5)),
            id="pickle",
        ),
        pytest.param(copy.deepcopy, id="deepcopy"),
    ],
)
def test_history_round_trips_through_pickle_and_deepcopy(copier):
    history = start(frame(values=(0.1, 0.0))).append(
        frame(2015, (0.1, 0.0)), lineage_digest="d" * 64
    )
    restored = copier(history)
    assert restored == history
    assert restored.to_json() == history.to_json()
    assert restored.digest == history.digest
    assert restored.identity_map.digest == history.identity_map.digest
    person = PersonIdentity("uint64", 2**64 - 1)
    assert restored.for_person(person) == history.for_person(person)
    restored.require_extension_of(history)
    successor = restored.append(
        frame(2016, (0.2, 0.0)), lineage_digest="e" * 64
    )
    successor.require_extension_of(history)


def test_person_id_column_is_read_as_private_keys_not_native_ids():
    """Invented native IDs 0..10: lexical admission gives native 10 key 2.

    The recorder reads ``person_id`` as this map's private key, so a caller
    holding native IDs must translate them with ``map_rows`` first.
    """
    identities = [PersonIdentity("int64", x) for x in range(11)]
    identity_map = PersonIdentityMap.from_identities(identities)
    assert identity_map.map_rows([PersonIdentity("int64", 10)]) == (2,)
    data = pd.DataFrame(
        {
            "person_id": np.asarray(
                identity_map.map_rows(identities), dtype=np.int64
            ),
            "year": np.full(11, 2014, dtype=np.int64),
            "earnings": np.asarray([1000.0 * x for x in range(11)]),
            "earnings_domain": np.ones(11, dtype=bool),
        }
    )
    history = ForwardEarningsHistory.start(
        identity_map,
        data,
        realization_id="invented-native-translation",
        generator_digest="a" * 64,
        source_contract_digest="b" * 64,
        lineage_digest="c" * 64,
        unit="XTS",
        price_basis="nominal",
    )
    for native, identity in enumerate(identities):
        (row,) = history.for_person(identity)
        assert float.fromhex(row.amount_hex) == 1000.0 * native


def test_loaded_successor_cannot_change_realization_or_erase_old_rows():
    first = start()
    second = first.append(frame(2015), lineage_digest="d" * 64)
    with pytest.raises(ValueError, match="provenance"):
        ForwardEarningsHistory.from_json(
            replace(second, realization_id="another-draw").to_json(),
            previous=first,
        )
    with pytest.raises(ValueError, match="prior rows"):
        first.require_extension_of(second)


def test_identity_digest_cannot_be_null_in_document():
    document = json.loads(start().to_json())
    document["identity_map_digest"] = None
    with pytest.raises(ValueError, match="identity map digest"):
        ForwardEarningsHistory.from_json(json.dumps(document))


def test_loaded_annual_snapshot_cannot_mix_lineage_digests():
    document = json.loads(start().to_json())
    document["observations"][1]["lineage_digest"] = "f" * 64
    with pytest.raises(ValueError, match="one lineage digest"):
        ForwardEarningsHistory.from_json(json.dumps(document))


def test_duplicate_frame_columns_refuse():
    data = frame()
    with pytest.raises(ValueError, match="columns"):
        start(pd.concat([data, data[["earnings"]]], axis=1))


@pytest.mark.parametrize(
    "field,value",
    [
        ("generator_digest", "unknown"),
        ("source_contract_digest", ""),
        ("realization_id", ""),
        ("unit", ""),
        ("price_basis", "unknown"),
    ],
)
def test_metadata_is_explicit(field, value):
    with pytest.raises(ValueError):
        replace(start(), **{field: value})
