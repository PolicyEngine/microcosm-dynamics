# Track B R1 delivery report

Built the new `src/populace_dynamics/track_b/` package: `ret_params.py`,
`parameters/ret_v1.yaml`, package initializers and README. `MANIFEST.in`
packages the YAML. SSA realized annual exemptions cover 2000–2026; rates
are exact 1/2 and 1/3. Each value carries source pins and status. Missing
years raise errors. No default forecast vintage was invented. Caller-supplied
projections are labelled projected and bind the permitted vintage name and
canonical payload SHA-256. Source captures are protected from Git normalization.

Verification class: statutory conformance plus historical-source checks.
Admitted scope: listed parameter years and projections conditional on their
registered vintage. No empirical or population validation claim.

## Tests

```text
.venv/bin/python -m pytest -q tests/test_track_b_ret_params.py tests/test_track_b_ret_differential.py
184 passed in 26.16s
```

The main module has 123 cases; the differential module has 61. Tests include
all 27 realized years against independently extracted SSA HTML; 48 band/year
back-test observations for 2003–2026 with published NAWI and December COLAs;
Hypothesis properties; source hashes/byte counts; exact ties; malformed inputs;
missing-year refusal; immutable state; no future-input substitution; and
vintage payload substitution refusal. Black and Ruff pass. A built wheel
loaded the module and all 27 YAML rows without using the editable source.
All nine committed source blobs were checked against their manifest hashes.

The repository's pytest marker inventory was recollected and both
`tests/tier_counts.json` and `tests/README-tiers.md` were updated: 8,632 total;
unit 3,848 (+184), artifact 3,152, integration PSID 930, legacy reproduction
520, PolicyEngine oracle 182. Only the tier policy assertion was executed:
`1 passed, 8631 deselected in 151.30s`. No PSID tests ran. The existing static
classifier assigns the new tests to unit; no classifier rules were changed.

## Invariants and limitations

- Projection never falls below the prior amount.
- Projection is nondecreasing in NAWI for fixed prior amount and COLA.
- Formula-era amounts are multiples of $120; exact ties round upward.
- Results are deterministic and use exact rational arithmetic.
- Zero preceding-December COLA preserves the previous amount.
- Only explicit, complete permitted-vintage inputs are read; missing years fail.
- Projected chains preserve the input payload fingerprint and source provenance.
- Realized values remain immutable and separate from projected values.

The higher 2000/2001 amounts are legislative exceptions to the rounding
invariant. The combined current formula is back-tested from 2003. Earlier
age-band regimes are unsupported. Projections assume unchanged law under
Act §203(f)(8); future legislation requires a new version. No registered
future wage/COLA vintage was supplied, so no numerical forecast is bundled.
No PSID computations or population outcomes were used; protected engine,
gate and run files are unchanged. The full empirical test suite was not run.

PolicyEngine-US modern thresholds agree. Its stored higher rate 0.333333
differs from the exact statutory 1/3 by 1/3000000; the differential test
records this precision difference rather than copying it.

## Captures (retrieved 2026-09-28 UTC)

Each manifest records its exact UTC timestamp, URL, bytes and SHA-256.
PolicyEngine captures come from commit
`a03e82e503f8e0285125ee0c5380410a964c8e8a`.

| Source | SHA-256 |
|---|---|
| [ssa_ret_history.html](https://www.ssa.gov/OACT/COLA/rtea.html) | `b03f940a2cfe7b12f7c0c5edaf1b5c46dc79786ffd22a023a154e4fec76b2b5d` |
| [ssa_ret_determination.html](https://www.ssa.gov/OACT/COLA/rtdet.html) | `bede06d5ab0aff9b620b143afb2e45cb1e0ab39de1aaeb5abdff08499c40c226` |
| [ssa_nawi_history.html](https://www.ssa.gov/OACT/COLA/AWI.html) | `ec58015bb689fbd8a1342eeda54f03b50656c60da1f9ddc8a660e5290fd23c18` |
| [ssa_cola_history.html](https://www.ssa.gov/OACT/COLA/colaseries.html) | `41bb09736bb40be233625d2c1c724dee643f16666ab59a01d5e68a1d6d70d14f` |
| [ssa_act_203.html](https://www.ssa.gov/OP_Home/ssact/title02/0203.htm) | `ea000092e140d2ff8ce058138a9f919fac4eeac0004bb71364d6e2bade53cf54` |
| [exempt_amount_under_fra.yaml](https://github.com/PolicyEngine/policyengine-us/blob/a03e82e503f8e0285125ee0c5380410a964c8e8a/policyengine_us/parameters/gov/ssa/social_security/earnings_test/exempt_amount_under_fra.yaml) | `fa5af0ddf0d43c69fcc01667cddd3e90f70609225bcdda0822ce7a1b84c8e88a` |
| [exempt_amount_year_of_fra.yaml](https://github.com/PolicyEngine/policyengine-us/blob/a03e82e503f8e0285125ee0c5380410a964c8e8a/policyengine_us/parameters/gov/ssa/social_security/earnings_test/exempt_amount_year_of_fra.yaml) | `bb0df7578fec0a959f2d7f34fc851aade8c82335076c4c150b761d31dd912865` |
| [reduction_rate_under_fra.yaml](https://github.com/PolicyEngine/policyengine-us/blob/a03e82e503f8e0285125ee0c5380410a964c8e8a/policyengine_us/parameters/gov/ssa/social_security/earnings_test/reduction_rate_under_fra.yaml) | `72b3f78d9b077bac39e6df00cb2cfca386e93152c2ed5b8a8ec8929b40b09d42` |
| [reduction_rate_year_of_fra.yaml](https://github.com/PolicyEngine/policyengine-us/blob/a03e82e503f8e0285125ee0c5380410a964c8e8a/policyengine_us/parameters/gov/ssa/social_security/earnings_test/reduction_rate_year_of_fra.yaml) | `98b21959c05daab71936c6864f4b467bbf6eaa37939b03056094c98a5a75cf02` |

Parameter YAML SHA-256:
`9b3715c53544da3c56626f9f60445127870da14358df04bbe73b53ffeb3be58b`.

## Commit delivery limitation

The assigned checkout is detached at `9cee2423f048683e15838aa5fee330afd072f85f`.
Its Git metadata lives outside the writable sandbox. A normal `git add`
failed creating that external `index.lock` with “Operation not permitted”.
No external Git metadata or caller checkout was modified. Instead, coherent
commits were created with `--no-verify` on branch
`dynamics-trackb-r1-20260928` in workspace-local `.cache/ret-r1.git`, preserving
the original commit as ancestor. `track-b-r1.bundle` delivers that sequence;
its final SHA is reported in the final response. The assigned checkout HEAD
remains unchanged. Nothing was pushed.
