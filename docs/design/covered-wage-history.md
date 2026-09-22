# Recording covered-wage observations

`CoveredWageHistory` attaches explicit source observations to one exact
`ForwardEarningsHistory`. It records a separate concept: source-reported,
uncapped employee wages declared OASDI-covered. It does not classify generated
labor income, calculate creditable earnings or verify statutory coverage.

Every person/year in the declared forward history must have one observation.
An amount requires a typed source value and receipt digest. An unavailable
amount requires a receipt digest and one reason: `source_field_unavailable`,
`coverage_unresolved` or `crosswalk_registration_required`. Omitting a row
refuses; it never creates a zero. A source-reported zero remains distinct from
unavailability. Odd-year labor carries do not create covered-wage observations.

The observations are independent of the generator's labor concept. Covered
wages may differ from labor income, including when the person is outside the
forward generator's domain. This sidecar performs no reconciliation, component
allocation, copying of control zeros or change to the original history.

## Source values and provenance

`SourceAmount(logical_dtype, serialization)` supports `int64`, `uint64`,
`decimal` and `binary64`. Integer strings are canonical and range checked.
Decimal strings retain their fractional scale; binary64 retains canonical
`float.hex()` values, including signed zero. Negative, nonfinite and ambiguous
values refuse. No floating-point conversion of source integers or decimals,
monetary rounding, indexing or cap occurs.

The sidecar inherits the history's explicit nominal measurement unit. The
caller must supply a source-contract digest declaring that unit and the
uncapped covered-employee-wage concept. Each observation's source digest must
identify a retained receipt binding the artifact, stable record/field locator,
original amount and dtype, reference year, unit and information date. The
module checks digest syntax; it does not read or admit those receipts. A
source declaration does not establish legal correctness or authorize use of
future information in a fit.

## Exact history binding

Construct `CoveredWageHistory(history, source_contract_digest, observations)`
with immutable `CoveredWageObservation` rows. `for_person` uses the history's
typed `PersonIdentityMap`, preserving source strings and large unsigned IDs.
`missing_coordinates` reports unavailable `(private key, year)` pairs.

`to_json` and `digest` retain the exact external history digest, identity-map
digest, realization, unit, price basis, source contract and source values.
The loader requires `from_json(text, history=..., expected_digest=...)`;
the expected digest is optional, while the actual history is mandatory.
Rebinding the serialized observations to another draw, identity map, changed
history or appended history refuses. Duplicate members, unknown fields,
missing rows and inconsistent amount states also refuse.

There is no implicit append or correction operation. Construct and retain a
new bundle for each explicit revision. Row order does not change its digest;
changing a source value's serialization or provenance does.

## Limits

Even a sidecar with no missing observations does not establish complete
OASDI coverage. The original history retains `not_materialized` coverage and
`registration_required` crosswalk status. Pre-2014 records, empirical source
admission, self-employment facts, full component reconciliation, event dates
and accepted Axiom input rules remain separate work. This module calculates
no benefits, payroll or population estimates and does not feed the frozen
historical estimates runner.
