# Recording annual forward earnings

`ForwardEarningsHistory` records the existing generator's annual labor-income
outputs for one realization. Previously the projection kept current earnings
and a few private lag values; this opt-in observer retains a dated history
without changing those inputs, drawing randomness or computing policy.

The first implementation covers the existing 2014–22 forward contract on a
fixed roster. It starts from an already materialized 2014 frame and appends
exactly one year at a time. The caller supplies the realization ID, generator,
source-contract and per-snapshot lineage digests, nominal measurement unit,
and exact identity manifest. Those digests identify the claimed inputs; they
do not verify a fitted artifact, grant source admission or register a crosswalk.

The recorder consumes the existing `person_id`, `year`, `earnings` and
`earnings_domain` columns. IDs and years must already be int64, earnings
binary64, and domain membership a complete Boolean column. The private IDs
reverse through `PersonIdentityMap`, preserving original uint64 and string
identities. Row order is irrelevant; duplicate IDs, missing markers and
implicit dtype conversion refuse.

## Values and missingness

A supported zero is recorded as `known_zero`. The outside-domain wrapper's
control zero is recorded as `unavailable`, with no amount and reason
`outside_forward_earnings_domain`. A nonzero outside-domain value refuses;
the recorder cannot discard an unexplained amount. Missing or nonfinite
supported values also refuse, rather than creating a zero or a guessed reason.

Amounts retain their exact `float.hex()` serialization, including the sign of
zero. There is no monetary rounding. This narrow version accepts the existing
generator's binary64 output only; integer, decimal, coverage-allocation and
signed self-employment concepts need separate source contracts.

Supported 2014 observations are labeled `boundary_method`, subsequent even
years `biennial_draw`, and odd years `odd_year_carry`. Carries must preserve the
previous year's exact amount bits. These labels describe the producer's
declared schedule; they do not establish how an arbitrary caller produced a
frame. The private 2012 lag is never read or converted into a historical record.

## Persistence and append

The immutable history declares its roster and last reference year separately
from its observations. Every declared person must have exactly one row in
every year from 2014 through that end year. Removing a complete last year or
an entire person therefore cannot silently shrink the declared envelope.

`append` returns a new history, preserving every prior row and metadata field.
It refuses overlap, gaps, roster/domain changes and extension past 2022.
Canonical JSON encodes private keys and years as decimal strings and amounts
as hexadecimal strings. The loader validates the embedded identity digest,
closed field set, dense envelope, amount values and carry semantics. An optional
expected digest verifies the whole history; an optional `previous` history
enforces the same append-only prefix and metadata binding after loading.

## Integration and limits

Invented tests run the actual `ForwardEarningsGenerator`, domain adapter and
`apply_earnings` functions with and without the observer, then compare frames.
Recording leaves the generated values and private state unchanged. Additional
cases exercise invalid states, source identities above signed int64, exact
floating-point transport, input-frame preservation and serialized refusals.

The history always reports coverage as `not_materialized` and the official
crosswalk as `registration_required`. Known labor income is not evidence of
Social Security covered earnings. No AIME, benefit, payroll, national estimate
or empirical score is produced. This module does not replace the proposed
full OASDI history bundle: pre-2014 observations, changing rosters, death and
entry events, coverage classification and the accepted Axiom input contract
remain separate work.

The historical estimates runner does not import this module. Its addition is
explicitly excluded from the historical source inventory, with the existing
transitive reachability test guarding that separation. Registered research
inputs, outputs, thresholds and generator implementation remain unchanged.
