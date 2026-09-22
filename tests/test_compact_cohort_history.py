"""Invented-record tests for optional compact closed-cohort persistence."""

import hashlib
import json

import numpy as np
import pandas as pd
import pytest

from populace_dynamics.closed_cohort_history import ClosedCohortEarningsHistory
from populace_dynamics.compact_cohort_history import (
    compact_history_digest,
    compact_history_from_json,
    compact_history_to_json,
)
from populace_dynamics.engine.steps import AgeSexMortalityModel
from populace_dynamics.forward_earnings_history import ForwardEarningsHistory
from populace_dynamics.person_identity import PersonIdentity, PersonIdentityMap
from tests.test_closed_cohort_history import setup, step


def baseline(identities):
    mapping = PersonIdentityMap.from_identities(identities)
    count = len(mapping.entries)
    frame = pd.DataFrame(
        {
            "person_id": np.arange(count, dtype="int64"),
            "year": np.full(count, 2014, dtype="int64"),
            "earnings": np.array(
                [0.0 if i % 2 == 0 else i + 0.25 for i in range(count)],
                dtype="float64",
            ),
            "earnings_domain": np.array(
                [i % 3 != 0 for i in range(count)], dtype="bool"
            ),
        }
    )
    frame.loc[~frame.earnings_domain, "earnings"] = 0.0
    return ForwardEarningsHistory.start(
        mapping,
        frame,
        realization_id="invented-compact",
        generator_digest="a" * 64,
        source_contract_digest="b" * 64,
        unit="XTS",
        price_basis="nominal",
        lineage_digest="c" * 64,
    )


def round_trip(history, *, baseline_history=None, previous=None):
    text = compact_history_to_json(history)
    restored = compact_history_from_json(
        text,
        baseline=baseline_history or history.baseline,
        expected_digest=hashlib.sha256(text.encode()).hexdigest(),
        previous=previous,
    )
    assert restored == history
    assert restored.digest == history.digest
    assert compact_history_to_json(restored) == text
    return text


def test_mixed_identity_missing_and_zero_round_trip_preserves_legacy_value():
    initial = baseline(
        [
            PersonIdentity("int64", -(2**63)),
            PersonIdentity("uint64", 2**64 - 1),
            PersonIdentity("string", "001"),
        ]
    )
    history = ClosedCohortEarningsHistory.start(initial, draw_index=7)
    legacy_text, legacy_digest = history.to_json(), history.digest
    text = round_trip(history)
    assert history.to_json() == legacy_text
    assert history.digest == legacy_digest
    assert (
        compact_history_digest(history)
        == hashlib.sha256(text.encode()).hexdigest()
    )
    assert "identity_map" not in json.loads(text)["histories"][0]


@pytest.mark.parametrize("death_year", [2015, 2016, None])
def test_observed_partial_death_and_extension_round_trip(death_year):
    frame, generator, initial, model = setup(death_year=death_year)
    previous = ClosedCohortEarningsHistory.start(initial, draw_index=3)
    history = previous
    for year in range(2015, 2023):
        frame, mortality, _, _ = step(frame, year, generator, initial, model)
        history = history.append(
            mortality=mortality,
            earnings_frame=frame,
            lineage_digest="e" * 64,
        )
    round_trip(history, previous=previous)


def test_full_extinction_and_later_empty_periods_round_trip():
    frame, generator, initial, _ = setup(death_year=None)
    model = AgeSexMortalityModel(
        ((0, 120),),
        {("0+", "female"): 1.0, ("0+", "male"): 1.0},
    )
    previous = ClosedCohortEarningsHistory.start(initial, draw_index=3)
    history = previous
    mortality_row_counts = []
    for year in range(2015, 2023):
        frame, mortality, _, _ = step(frame, year, generator, initial, model)
        mortality_row_counts.append(len(mortality.rows))
        history = history.append(
            mortality=mortality,
            earnings_frame=frame,
            lineage_digest="e" * 64,
        )
        round_trip(history, previous=previous)
    assert mortality_row_counts == [4, 0, 0, 0, 0, 0, 0, 0]
    assert history.active_keys == ()
    assert len(history.histories) == 4
    assert all(item.last_year == 2014 for item in history.histories)


def mutate(text, callback):
    document = json.loads(text)
    callback(document)
    changed = json.dumps(
        document,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )
    return changed, hashlib.sha256(changed.encode()).hexdigest()


@pytest.mark.parametrize(
    "change,match",
    [
        (lambda d: d.update(extra=True), "fields"),
        (lambda d: d["histories"][0].update(extra=True), "fields"),
        (lambda d: d["histories"][0].update(roster_keys=["00"]), "canonical"),
        (
            lambda d: d["histories"][0]["observations"][0].update(
                amount_hex="nan", earnings_domain=True
            ),
            "binary64",
        ),
        (
            lambda d: d["histories"][0].update(identity_map_digest="0" * 64),
            "identity",
        ),
        (lambda d: d.update(last_year="02014"), "canonical"),
    ],
)
def test_recomputed_digest_does_not_admit_invalid_internal_content(
    change, match
):
    initial = baseline([PersonIdentity("string", "invented")])
    history = ClosedCohortEarningsHistory.start(initial, draw_index=0)
    changed, digest = mutate(compact_history_to_json(history), change)
    with pytest.raises(ValueError, match=match):
        compact_history_from_json(
            changed, baseline=initial, expected_digest=digest
        )


def test_wrong_digest_baseline_duplicate_and_nonfinite_refuse():
    initial = baseline([PersonIdentity("string", "invented")])
    history = ClosedCohortEarningsHistory.start(initial, draw_index=0)
    text = compact_history_to_json(history)
    digest = compact_history_digest(history)
    with pytest.raises(ValueError, match="digest mismatch"):
        compact_history_from_json(
            text, baseline=initial, expected_digest="0" * 64
        )
    other = baseline([PersonIdentity("string", "other")])
    with pytest.raises(ValueError, match="baseline binding"):
        compact_history_from_json(text, baseline=other, expected_digest=digest)
    duplicate = text.replace(
        '{"baseline_digest":', '{"schema":"x","baseline_digest":'
    )
    with pytest.raises(ValueError, match="duplicate JSON field"):
        compact_history_from_json(
            duplicate,
            baseline=initial,
            expected_digest=hashlib.sha256(duplicate.encode()).hexdigest(),
        )
    nonfinite = text.replace('"draw_index":"0"', '"draw_index":NaN')
    with pytest.raises(ValueError, match="invalid JSON constant"):
        compact_history_from_json(
            nonfinite,
            baseline=initial,
            expected_digest=hashlib.sha256(nonfinite.encode()).hexdigest(),
        )


def test_previous_rewrite_refuses_existing_extension_check():
    initial = baseline([PersonIdentity("string", "invented")])
    previous = ClosedCohortEarningsHistory.start(initial, draw_index=0)
    replacement = baseline([PersonIdentity("string", "invented")])
    replacement = ForwardEarningsHistory(
        replacement.identity_map,
        "different-realization",
        replacement.generator_digest,
        replacement.source_contract_digest,
        replacement.unit,
        replacement.price_basis,
        replacement.roster_keys,
        replacement.last_year,
        replacement.observations,
    )
    changed = ClosedCohortEarningsHistory.start(replacement, draw_index=0)
    with pytest.raises(ValueError, match="baseline or draw"):
        round_trip(changed, previous=previous)


def test_previous_prefix_accepts_extension_and_rejects_rewritten_old_row():
    frame, generator, initial, model = setup(death_year=None)
    previous = ClosedCohortEarningsHistory.start(initial, draw_index=3)
    frame, mortality, _, _ = step(frame, 2015, generator, initial, model)
    current = previous.append(
        mortality=mortality,
        earnings_frame=frame,
        lineage_digest="e" * 64,
    )
    text = round_trip(current, previous=previous)
    changed, digest = mutate(
        text,
        lambda d: d["histories"][0]["observations"][0].update(
            amount_hex=float(1).hex(), earnings_domain=True
        ),
    )
    with pytest.raises(
        ValueError, match="fixed earnings domain|changed or removed prior rows"
    ):
        compact_history_from_json(
            changed,
            baseline=initial,
            expected_digest=digest,
            previous=previous,
        )


def test_bounded_storage_growth_removes_repeated_map_quadratic_term():
    sizes = {}
    for count in (80, 160):
        initial = baseline(
            PersonIdentity("string", f"invented-{i:03d}") for i in range(count)
        )
        history = ClosedCohortEarningsHistory.start(initial, draw_index=0)
        compact = compact_history_to_json(history).encode()
        legacy = history.to_json().encode()
        sizes[count] = (len(compact), len(legacy))
        assert round_trip(history).encode() == compact
    assert sizes[160][0] < 2.2 * sizes[80][0]
    assert sizes[160][1] > 3.5 * sizes[80][1]
    assert sizes[160][0] < sizes[160][1] / 5


@pytest.mark.parametrize("count", [1, 160])
def test_identity_map_serialization_is_constant_per_envelope(
    monkeypatch, count
):
    initial = baseline(
        PersonIdentity("string", f"invented-{i:03d}") for i in range(count)
    )
    history = ClosedCohortEarningsHistory.start(initial, draw_index=0)
    original = PersonIdentityMap.digest.fget
    calls = 0

    def counted(mapping):
        nonlocal calls
        calls += 1
        return original(mapping)

    monkeypatch.setattr(PersonIdentityMap, "digest", property(counted))
    text = compact_history_to_json(history)
    # One direct map digest plus the unchanged baseline digest, independent of N.
    assert calls == 2
    calls = 0
    restored = compact_history_from_json(
        text,
        baseline=initial,
        expected_digest=hashlib.sha256(text.encode()).hexdigest(),
    )
    assert restored == history
    # Loading, baseline binding and canonical reserialization remain constant.
    assert calls == 4


def test_nontext_input_refuses_with_value_error():
    initial = baseline([PersonIdentity("string", "invented")])
    with pytest.raises(ValueError, match="JSON text"):
        compact_history_from_json(
            b"{}", baseline=initial, expected_digest="0" * 64
        )
