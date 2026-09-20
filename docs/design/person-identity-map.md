# Lossless person identity map

`populace_dynamics.person_identity` is an opt-in bridge between explicit source
identities and private nonnegative signed-int64 keys. It does not connect a
population to an earnings generator or calculate policy outcomes.

An identity contains its logical type (`int64`, `uint64` or `string`) and exact
value. Integer values never pass through floating point. Strings remain opaque:
`"1"`, integer `1`, and unsigned integer `1` are distinct identities; Unicode
normalization is not applied. Empty strings are preserved rather than treated
as missing. The producer must establish which source fields identify persons.
Household IDs and missing values are not substituted automatically.

```python
from populace_dynamics.person_identity import PersonIdentity, PersonIdentityMap

people = [
    PersonIdentity("uint64", 2**64 - 1),
    PersonIdentity("string", "person-A"),
]
original = PersonIdentityMap.from_identities(people)
keys = original.map_rows(people)
assert original.reverse_rows(keys) == tuple(people)

extended = original.append([PersonIdentity("string", "new-entrant")])
assert extended.map_rows(people) == keys
loaded = PersonIdentityMap.from_json(
    extended.to_json(),
    expected_digest=extended.digest,
    previous=original,
)
assert loaded == extended
```

Each admission batch is sorted lexically by logical type and canonical source
value. The first batch receives keys starting at zero. Later batches append
keys and never renumber existing entries, even when an entrant sorts before an
existing person. Input order within a batch does not affect the map. Admission
batch history does affect it and must remain pinned for reproducible careers.
Duplicate identities within an admission or already present in the map refuse;
repeated observations in `map_rows` are allowed and retain their row order.

The canonical JSON manifest encodes both original integer values and private
keys as decimal strings, avoiding precision loss in JSON consumers. It rejects
duplicate or unknown fields, noncanonical integers, unsupported logical types,
duplicate identities and non-dense keys. The SHA-256 digest covers canonical
UTF-8 JSON; insignificant input whitespace is not part of that identity.

On intake, use a separately pinned `expected_digest`. For an extension, also
provide the previous accepted map: `previous` checks that every old entry is
preserved. A new JSON document cannot prove its own provenance merely by
carrying a matching digest. Neither this digest nor successful loading admits
a baseline, certifies source person identity, or proves historical record
linkage.

All values are immutable snapshots. Accepted string subclasses are copied to
built-in strings, preserving their underlying text rather than overridden
rendering methods. Mapping refuses unknown identities, and reverse mapping
refuses unknown or coerced keys.
Identity, entry and prior-manifest boundaries require the declared value
classes; subclasses cannot supply mutable overridden identity semantics.
The map class cannot be subclassed, so its factories and digest verification
cannot dispatch to subclass overrides.
The original generator's integer handling is unchanged. A later adapter must
explicitly use these
private keys and restore the exact original identity on export; until then,
this module is a tested standalone prerequisite only.
