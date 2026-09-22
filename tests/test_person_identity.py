"""Invented identity cases; no population, historical earnings or policy run."""

import copy
import json
import pickle
from dataclasses import FrozenInstanceError

import pytest

from populace_dynamics.person_identity import (
    IdentityEntry,
    PersonIdentity,
    PersonIdentityMap,
)


def test_lossless_mixed_identities_and_repeated_row_order():
    identities = (
        PersonIdentity("int64", -(2**63)),
        PersonIdentity("int64", 2**53 + 1),
        PersonIdentity("int64", 2**63 - 1),
        PersonIdentity("uint64", 2**63),
        PersonIdentity("uint64", 2**64 - 1),
        PersonIdentity("string", "1"),
        PersonIdentity("int64", 1),
        PersonIdentity("uint64", 1),
        PersonIdentity("string", ""),
        PersonIdentity("string", "é"),
        PersonIdentity("string", "e\u0301"),
    )
    mapping = PersonIdentityMap.from_identities(identities)
    reordered = identities[::-1] + (identities[0], identities[0])
    keys = mapping.map_rows(reordered)
    assert mapping.reverse_rows(keys) == reordered
    assert len(set(mapping.map_rows(identities))) == len(identities)
    assert all(type(key) is int and 0 <= key < 2**63 for key in keys)
    restored = PersonIdentityMap.from_json(
        mapping.to_json(), expected_digest=mapping.digest
    )
    assert restored == mapping
    assert restored.to_json() == mapping.to_json()
    assert restored.reverse_rows(keys) == reordered
    assert '"18446744073709551615"' in mapping.to_json()


def test_batch_order_is_irrelevant_and_appending_never_renumbers():
    people = [PersonIdentity("string", s) for s in ["z", "b", "a"]]
    original = PersonIdentityMap.from_identities(people)
    assert original == PersonIdentityMap.from_identities(reversed(people))
    old_json, old_digest = original.to_json(), original.digest
    entrants = [PersonIdentity("string", "0"), PersonIdentity("uint64", 0)]
    extended = original.append(entrants)
    assert extended == original.append(reversed(entrants))
    assert extended.entries[:3] == original.entries
    assert extended.map_rows(people) == original.map_rows(people)
    assert extended.reverse_rows(extended.map_rows(entrants)) == tuple(
        entrants
    )
    assert original.to_json() == old_json and original.digest == old_digest
    assert extended.digest != original.digest
    assert original.append([]) is original
    restored = PersonIdentityMap.from_json(
        extended.to_json(), previous=original, expected_digest=extended.digest
    )
    assert restored == extended


def test_empty_manifest_round_trip():
    empty = PersonIdentityMap()
    assert empty.map_rows([]) == empty.reverse_rows([]) == ()
    assert PersonIdentityMap.from_json(empty.to_json()) == empty
    empty.require_extension_of(empty)


def test_string_subclasses_are_snapshotted_before_admission():
    class MutableString(str):
        def __new__(cls, raw):
            result = super().__new__(cls, raw)
            result.rendered = raw
            return result

        def __str__(self):
            return self.rendered

    logical_type = MutableString("string")
    source = MutableString("person-A")
    source.rendered = "different-before-admission"
    identity = PersonIdentity(logical_type, source)
    mapping = PersonIdentityMap.from_identities([identity])
    before_json, before_digest = mapping.to_json(), mapping.digest
    before_hash = hash(identity)
    source.rendered = "person-B"
    logical_type.rendered = "uint64"

    assert type(identity.value) is str
    assert type(identity.logical_type) is str
    assert identity == PersonIdentity("string", "person-A")
    assert hash(identity) == before_hash
    assert mapping.to_json() == before_json
    assert mapping.digest == before_digest
    assert mapping.map_rows([PersonIdentity("string", "person-A")]) == (0,)
    assert mapping.reverse_rows([0]) == (identity,)


def test_identity_subclasses_cannot_supply_mutable_serialization():
    rendered = ["person-A"]

    class MutableIdentity(PersonIdentity):
        @property
        def canonical_value(self):
            return rendered[0]

    identity = MutableIdentity("string", "person-A")
    with pytest.raises(ValueError, match="explicit PersonIdentity"):
        PersonIdentityMap.from_identities([identity])
    with pytest.raises(ValueError, match="explicit PersonIdentity"):
        IdentityEntry(identity, 0)
    mapping = PersonIdentityMap.from_identities(
        [PersonIdentity("string", "person-A")]
    )
    rendered[0] = "person-B"
    with pytest.raises(ValueError, match="explicit PersonIdentity"):
        mapping.map_rows([identity])


def test_manifest_value_subclasses_refuse():
    class CustomEntry(IdentityEntry):
        pass

    with pytest.raises(ValueError, match="IdentityEntry values"):
        PersonIdentityMap((CustomEntry(PersonIdentity("string", "a"), 0),))
    with pytest.raises(ValueError, match="previous manifest"):
        PersonIdentityMap().require_extension_of(object())


def test_map_subclasses_cannot_override_digest_verification():
    with pytest.raises(TypeError, match="cannot be subclassed"):

        class ForgedDigestMap(PersonIdentityMap):
            @property
            def digest(self):
                return "forged expected digest"


@pytest.mark.parametrize("value", [True, False, None, 1.0, float("nan"), "1"])
@pytest.mark.parametrize("logical_type", ["int64", "uint64"])
def test_numeric_identity_never_coerces_ambiguous_values(value, logical_type):
    with pytest.raises(ValueError):
        PersonIdentity(logical_type, value)


@pytest.mark.parametrize(
    "logical_type,value",
    [
        ("int64", -(2**63) - 1),
        ("int64", 2**63),
        ("uint64", -1),
        ("uint64", 2**64),
        ("string", 1),
        ("string", None),
        ("string", "\ud800"),
        ("float64", 1),
        ("Int64", 1),
    ],
)
def test_invalid_type_or_range_refuses(logical_type, value):
    with pytest.raises(ValueError):
        PersonIdentity(logical_type, value)


def test_duplicate_admission_refuses_without_changing_original():
    identity = PersonIdentity("int64", 10)
    with pytest.raises(ValueError, match="duplicate"):
        PersonIdentityMap.from_identities([identity, identity])
    mapping = PersonIdentityMap.from_identities([identity])
    before = mapping.to_json()
    with pytest.raises(ValueError, match="already admitted"):
        mapping.append([PersonIdentity("int64", 11), identity])
    assert mapping.to_json() == before


@pytest.mark.parametrize("keys", [[0, 0], [1, 0], [0, 2], [-1, 0]])
def test_duplicate_non_dense_or_reordered_keys_refuse(keys):
    with pytest.raises(ValueError):
        PersonIdentityMap(
            tuple(
                IdentityEntry(PersonIdentity("string", str(i)), key)
                for i, key in enumerate(keys)
            )
        )


def test_duplicate_identity_in_loaded_entries_refuses():
    identity = PersonIdentity("string", "one")
    with pytest.raises(ValueError, match="duplicate person identity"):
        PersonIdentityMap(
            (IdentityEntry(identity, 0), IdentityEntry(identity, 1))
        )


def test_manifest_and_entries_are_immutable():
    identity = PersonIdentity("int64", 1)
    entries = [IdentityEntry(identity, 0)]
    mapping = PersonIdentityMap(entries)
    entries.clear()
    assert mapping.map_rows([identity]) == (0,)
    with pytest.raises(FrozenInstanceError):
        identity.value = 2
    with pytest.raises(FrozenInstanceError):
        mapping.entries = ()
    with pytest.raises(TypeError):
        mapping._forward[identity] = 8


@pytest.mark.parametrize("key", [True, 0.0, "0", None, -1, 1, 2**64])
def test_reverse_mapping_rejects_unknown_or_coerced_keys(key):
    mapping = PersonIdentityMap.from_identities([PersonIdentity("int64", 1)])
    with pytest.raises(ValueError):
        mapping.reverse_rows([key])


def test_unknown_person_and_untyped_inputs_refuse():
    mapping = PersonIdentityMap.from_identities([PersonIdentity("int64", 1)])
    for identity in [PersonIdentity("string", "1"), 1, None]:
        with pytest.raises(ValueError):
            mapping.map_rows([identity])
    with pytest.raises(ValueError):
        mapping.append(["1"])


@pytest.mark.parametrize("value", ["01", "+1", " 1", "1.0", "-0", "١", 1])
def test_noncanonical_serialized_integer_refuses(value):
    mapping = PersonIdentityMap.from_identities([PersonIdentity("int64", 1)])
    document = json.loads(mapping.to_json())
    document["entries"][0]["value"] = value
    with pytest.raises(ValueError, match="canonical decimal string"):
        PersonIdentityMap.from_json(json.dumps(document))


@pytest.mark.parametrize(
    "text",
    [
        "null",
        "[]",
        '{"schema":"unknown","entries":[]}',
        '{"schema":"x","schema":"x","entries":[]}',
        '{"schema":NaN,"entries":[]}',
    ],
)
def test_invalid_json_document_refuses(text):
    with pytest.raises(ValueError):
        PersonIdentityMap.from_json(text)


def test_unknown_fields_and_duplicate_entry_fields_refuse():
    mapping = PersonIdentityMap.from_identities(
        [PersonIdentity("string", "a")]
    )
    document = json.loads(mapping.to_json())
    document["entries"][0]["household_id"] = "not-a-person-key"
    with pytest.raises(ValueError, match="entry fields"):
        PersonIdentityMap.from_json(json.dumps(document))
    duplicated = mapping.to_json().replace(
        '"value":"a"', '"value":"a","value":"b"'
    )
    with pytest.raises(ValueError, match="duplicate JSON field"):
        PersonIdentityMap.from_json(duplicated)


def test_digest_and_prior_manifest_reject_remapping_or_deletion():
    a, b = PersonIdentity("string", "a"), PersonIdentity("string", "b")
    old = PersonIdentityMap.from_identities([a, b])
    remapped = PersonIdentityMap((IdentityEntry(b, 0), IdentityEntry(a, 1)))
    with pytest.raises(ValueError, match="digest mismatch"):
        PersonIdentityMap.from_json(
            remapped.to_json(), expected_digest=old.digest
        )
    with pytest.raises(ValueError, match="prior manifest"):
        PersonIdentityMap.from_json(remapped.to_json(), previous=old)
    with pytest.raises(ValueError, match="prior manifest"):
        PersonIdentityMap.from_json(
            PersonIdentityMap().to_json(), previous=old
        )


def _pickled(value, protocol=pickle.HIGHEST_PROTOCOL):
    return pickle.loads(pickle.dumps(value, protocol=protocol))


@pytest.mark.parametrize(
    "copier",
    [
        *(
            pytest.param(
                lambda value, p=p: _pickled(value, p), id=f"pickle-{p}"
            )
            for p in range(pickle.HIGHEST_PROTOCOL + 1)
        ),
        pytest.param(copy.deepcopy, id="deepcopy"),
        pytest.param(copy.copy, id="copy"),
    ],
)
def test_map_round_trips_through_pickle_and_copy(copier):
    identities = (
        PersonIdentity("uint64", 2**64 - 1),
        PersonIdentity("int64", -(2**63)),
        PersonIdentity("string", "é"),
        PersonIdentity("string", ""),
    )
    mapping = PersonIdentityMap.from_identities(identities).append(
        [PersonIdentity("string", "0")]
    )
    restored = copier(mapping)
    assert type(restored) is PersonIdentityMap
    assert restored == mapping
    assert restored.to_json() == mapping.to_json()
    assert restored.digest == mapping.digest
    assert restored.map_rows(identities) == mapping.map_rows(identities)
    assert restored.reverse_rows([4]) == (PersonIdentity("string", "0"),)
    with pytest.raises(ValueError, match="already admitted"):
        restored.append([PersonIdentity("string", "é")])
    with pytest.raises(TypeError):
        restored._forward[identities[0]] = 8
    assert copier(PersonIdentityMap()) == PersonIdentityMap()


def test_map_reduces_to_its_entries_so_loading_revalidates():
    mapping = PersonIdentityMap.from_identities(
        [PersonIdentity("string", "a"), PersonIdentity("string", "b")]
    )
    constructor, arguments = mapping.__reduce__()
    assert constructor is PersonIdentityMap
    assert arguments == (mapping.entries,)
    swapped = (IdentityEntry(PersonIdentity("string", "a"), 1),)
    with pytest.raises(ValueError, match="dense"):
        constructor(swapped)


def test_json_whitespace_does_not_change_canonical_digest():
    mapping = PersonIdentityMap.from_identities(
        [PersonIdentity("uint64", 2**64 - 1)]
    )
    pretty = json.dumps(json.loads(mapping.to_json()), indent=2)
    assert (
        PersonIdentityMap.from_json(pretty, expected_digest=mapping.digest)
        == mapping
    )
