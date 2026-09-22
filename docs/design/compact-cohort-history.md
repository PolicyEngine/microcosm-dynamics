# Compact closed-cohort history storage

The optional compact envelope stores an existing validated
`ClosedCohortEarningsHistory` without repeating its full identity map inside
every per-person `ForwardEarningsHistory`. It does not replace or reinterpret
either existing serializer. Legacy JSON bytes and legacy digests remain the
authoritative value representation for existing callers.

Use `compact_history_to_json(history)` to produce the distinct
`populace_dynamics.compact_closed_cohort_history.v1` envelope and
`compact_history_digest(history)` to identify those exact compact bytes.
Compact and legacy digests are separate namespaces.

Loading is explicit:

```python
restored = compact_history_from_json(
    compact_text,
    baseline=trusted_initial_history,
    expected_digest=trusted_compact_digest,
    previous=optional_previous_history,
)
```

The loader requires the externally trusted baseline because that object owns
the one identity map used by all reconstructed children. The envelope and
each child retain the identity-map digest. Loading checks the exact envelope,
child, observation and transition fields; canonical integer and binary64
representations; schema and status constants; provenance; baseline and map
digests; the expected compact digest; and a canonical byte-for-byte round
trip. It constructs `ForwardEarningsObservation`, `ForwardEarningsHistory`,
`MortalityStepObservation`, `CohortTransition` and
`ClosedCohortEarningsHistory` through their existing validators. When a
previous value is supplied, the existing extension validator runs unchanged.

The serializer reads already validated typed fields directly. It never
creates a legacy child JSON document merely to remove its identity map. The
mortality representation was already externally identity-map bound and is
retained unchanged.

This is storage normalization only. It performs no generator or model call,
source admission, coverage classification, observation arithmetic, or value
normalization. It does not make population-scale memory or runtime claims.
Bounded invented-record tests at 80 and 160 people verify that compact bytes
grow approximately linearly while the unchanged legacy envelope retains its
measured quadratic repeated-map term.
