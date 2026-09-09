# Experimental entrant schedule and support restrictions

This source slice recovers the two engine modules and synthetic tests from
local commit `61bbf1c7e25a7e55033c134bbc2e846022b8850b`. It accepts an explicitly
supplied donor frame and annual controls in thousands. It does not include the
original native donor/control readers, snapshots, build script, or run artifact.
The original frame-reader round-trip test is deferred with that source path.

`build_entrant_schedule` returns frames for the existing
`metadata[SCHEDULED_ENTRIES_KEY]` interface, plus arithmetic alignment and
provenance records. Positive-weight donors are reweighted for each positive
control. Zero controls remain in alignment but produce no frame and consume
no person IDs; zero-weight donors do not become demographic actors. The input
boundary rejects noninteger ages/activation keys and ambiguous boolean flags.
Controls are validated before cohort allocation begins.

The schedule retains the historical gross-positive-inflow convention. That
control convention is not a count of observed border arrivals, a net migration
law, or a complete population stock model. The recorded donor composition and
control provenance describe caller-supplied inputs; this interface does not
admit their sources or fit/calibrate a population.

## Existing loop timing

A cohort scheduled for year Y carries `year=Y-1` and `age=entry_age`.
The existing loop activates it before mortality, then increments age. Its
activation-year slice therefore carries `entry_age+1`. This is the existing
engine convention, not a newly established arrival-exposure assumption.
The caller must reserve real IDs in the shared allocator. The loop rejects
duplicate scheduled IDs and builds stable person ordinals across cohorts.

## Explicit support boundaries

`EntrantClaimingAdapter(step)` calls a supplied claiming adapter only on
incumbents. It rejects existing entrant claim ages, claim years, claimed state,
or disability-conversion events before executing the incumbent step. Such
observations need a separately admitted claim-history path. The wrapper does
not erase possible observed entitlement or declare those people ineligible.
Supported exclusion inputs retain missing plans/years and a structural false
claiming flag. With only entrants, the incumbent step is not called.

Explicit synthetic rows require a known `entry_kind`; losing or misspelling
that marker is an error. Legacy closed panels without synthetic markers retain
their incumbent interpretation. Birth and realized-opener markers remain
distinct from immigrant cohorts. Provenance counts reject missing/unknown kinds.

The historical birth materializer leaves the new provenance column missing.
For this experimental path, `materialize_births_with_provenance` delegates to
that actual materializer and labels only the children it just allocated. It
validates existing rows first; it cannot retrospectively relabel unidentified
synthetic rows. It accepts supplied birth records and does not establish a
fitted fertility adapter or enforce the fertility risk-set restriction.

`suppress_entrant_benefit_outputs` marks specified unsupported outputs missing.
It does not calculate benefits. Consumers must report the unsupported population
separately; missing benefits must not become zero benefits in an average or be
used to label a partial-population result national.

The fertility/disability ID helpers and earnings-domain assertion express
support restrictions. `exclusion_report` is explicitly `inventory_only` with
`execution_verified=False`; it does not claim those restrictions were applied
in a projection. The actual claiming wrapper enforces its own narrower contract.
The historical fertility function treats an empty `holdout_ids` set as all
roster IDs and ignores that argument in its precomputed-birth branch. An ID-set
complement alone therefore cannot enforce the entrant fertility restriction.

## Validation and remaining work

Synthetic tests exercise the real scheduled-entry loop, cohort extinction and
later activation, mortality-before-ageing order, positive/zero cohort weights,
claiming exclusion, missing benefit outputs, and incumbent random consumption.
The mortality and other fitted transitions in those integration fixtures are
explicitly synthetic. Placeholder benefit values test output suppression only;
no policy calculation, Axiom runtime, or national score is claimed.

The historical registered assembly, engine steps, and scientific gates remain
unchanged. Exact historical source exclusions are justified by assertions that
these two experimental modules remain unreachable from the birth-evidence
reducer and its registered input roots.

An entrant-supported Social Security score still requires admitted donor and
control sources, migration-universe/exposure decisions, covered-work histories,
insured-status and benefit support, and coherent family, disability, earnings,
and other post-entry transitions. This recovery addresses an engineering
boundary; it does not establish DynaSim parity.
