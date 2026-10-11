# Track B R1: retirement earnings test parameters

Verification class: **statutory conformance plus a historical-source check**.
Success admits parameter values for the listed years only. A projection is
conditional on its explicitly permitted wage/COLA vintage. It does not admit
population effects, claiming behavior, payment mechanics, or forecast accuracy.

`parameters/ret_v1.yaml` pins SSA's published annual lower and higher exempt
amounts for **2000–2026**, plus exact withholding rates of **1/2** and **1/3**.
Every value records its realized/projected status and resolves to source URLs,
UTC retrieval times, and captured-file SHA-256 hashes. The returned table also
records the YAML's SHA-256. Source captures, their byte counts, and manifests
are in `tests/data/track_b/ret_sources/`; a separate historical fixture contains
the published NAWI and December COLA inputs used only in back-tests.

The lower amount applies below FRA throughout the year. The higher amount
applies in the year of FRA attainment to earnings before the FRA month. RET
does not apply beginning with the FRA month. These are annual dollar limits;
this module does not compute deductions, monthly payments, or grace-year rules.
Pre-2000 age-band regimes are outside this version's scope.

## Statutory method

Authority: [Social Security Act §203(f)(3) and (8)(A)–(E)](
https://www.ssa.gov/OP_Home/ssact/title02/0203.htm), and
[SSA's exempt-amount determination method](
https://www.ssa.gov/OACT/COLA/rtdet.html).

For year `y`, if a positive COLA takes effect in December `y - 1`:

```text
lower = max(previous lower, nearest_120(8040 × NAWI[y-2] / 22935.42))
higher = max(previous higher, nearest_120(30000 × NAWI[y-2] / 32154.82))
```

`nearest_120` rounds exact halfway cases upward. This is the annual equivalent
of the statute's monthly $10 rounding, including $5 ties upward. If that COLA
is zero, retain both previous amounts even when wages increase. COLA size is a
trigger, not the index multiplier. Calculations use exact rational arithmetic,
independent of floating-point rounding and Decimal context.

The combined current projection formula is supported from 2003 onward.
The 2000 and 2001 higher limits ($17,000 and $25,000) were legislated separately
and are not multiples of $120. The formula-era rounding invariant does not
apply to those historical exceptions. Projections assume unchanged law;
§203(f)(8)(C)'s override for newly enacted exempt amounts needs a new version.

## Reading and projecting

```python
from populace_dynamics.track_b.ret_params import load_ret_parameters

parameters = load_ret_parameters()
amount = parameters.for_year(2026).lower_exempt_amount
assert amount.value == 24480
assert amount.status == "realized"
```

`for_year` performs exact year lookup: no interpolation or carry-forward.
`for_year(2027)` raises `KeyError` on the bundled table.

No default forecast is bundled: R1 has no registered future wage/COLA vintage
to promote into published parameters. For projections, construct
`ProjectionInputs(vintage, nawi, december_cola_percent)` from explicitly pinned
`ParameterValue` inputs. NAWI keys are wage years and COLA keys are December
effective years (values in percent). Each input has a `SourcePin` with URL,
UTC retrieval timestamp, and hash. Then call:

```python
projected = parameters.project_through(
    2030, inputs, permitted_vintage="the-registered-vintage-id"
)
```

The named vintage must match; register its source hashes before empirical
use. The function copies mappings immutably, requires consecutive inputs,
refuses missing years even when COLA is zero, and refuses mixed-vintage
projection chains. A canonical SHA-256 binds the full input payload, so
reusing a vintage name with different values or source pins is also refused.
It reads only the supplied `y-2` wage and `y-1` COLA;
it never fills forecast gaps from the historical fixture. Output exemptions
are labelled projected and preserve prior, NAWI, and COLA source identities.
Existing realized rows remain unchanged. The exact current-law rates remain
realized statutory constants.

## Verification and limits

- Every realized row is compared with the captured SSA history.
- The 2003–2026 back-test uses published NAWI and effective-December COLAs.
- Boundary and Hypothesis tests cover the prior-amount floor, NAWI
  monotonicity, $120 rounding and ties, determinism, zero-COLA carry-forward,
  missing-year refusal, source integrity, and vintage isolation.
- Differential tests use four pinned PolicyEngine-US parameter files. Their
  modern exemptions agree; their stored higher rate `0.333333` differs from
  exact `1/3` by `1/3000000`. That precision difference is recorded explicitly.
  Differential agreement is diagnostic, not statutory acceptance.

No PSID data, empirical outcomes, or DYNASIM comparator values are used.
The engine, gates, and committed run artifacts are not part of R1.

## G: gross-benefit layer

`gross_benefits.py` computes gross monthly benefits on one worker's record:
the 403(a) family maximum (and the 403(a)(6) disability maximum), original
benefits, the proportional reduction for the maximum, the RS 00615.768
dual-entitlement redistribution, age reductions after the maximum, the
402(k)(3)(A) dual-entitlement offset and the 215(g) whole-dollar payment.
`household_benefits` is the integration entry point. It computes every
record a household draws on together, and refuses anyone entitled as an
auxiliary on two records rather than computing them one record at a time.
`family_benefits` computes a single record only with `standalone=True`.
Delayed-credit months run from full retirement age to 70 (`840 - FRA`),
and credits for births before 1917 are refused. `SavingsClauseGuard`
carries 403(a)(5)'s protected total across a record's months and refuses
any month it could change, which this one-month layer does not compute.
Input errors are raised before any refusal.

Verification class: **statutory conformance**, for supported family
configurations only. Unsupported configurations raise
`FAMILY_CONFIG_UNSUPPORTED` and stay in denominators. The design note is
`docs/design/track_b_g_gross_benefits.md`; the worked-example sources are
under `tests/data/track_b/gross_benefit_sources/`.
