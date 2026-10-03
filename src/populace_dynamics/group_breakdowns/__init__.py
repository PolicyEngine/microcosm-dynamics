"""Post hoc group breakdowns of the finished DYNASIM3 blind tests (NASI).

After the NASI meeting of 2026-10-01 Max asked for each finished blind
test's results by SSA's MINT8 characteristic subgroups.  Each module of
this package is the adapter of one test: it re-executes that test's frozen
registered computation exactly, composing the existing code read-only,
refuses unless every committed cell it recomputes equals the committed
artifact, and only then joins the person attributes (the cohort side frame
of :mod:`populace_dynamics.cohorts.group_attributes` and the lifetime
measures of :mod:`populace_dynamics.estimates.lifetime_measures`) and cuts
the MINT-scheme cells with :mod:`populace_dynamics.estimates.
group_breakdown`.

* :mod:`.common`: the post hoc labels, the exact comparison with a
  committed artifact, the mapping of the cohort side frame onto the MINT8
  scheme's codes, and INVENTED side-frame inputs for dry runs.
* :mod:`.min_benefit`: exercise 4 (Track M, the minimum-benefit share of
  OASDI beneficiaries 62 and older, PSID 2023 wave, income year 2022).

A real-data breakdown is new outcomes: it runs only through its registered
entry script, under its own issue #42 registration, and every output
carries the test's own labels plus "registered, one-shot, post hoc, not
blind" and "report-only".  Development uses INVENTED data.

Submodules are imported explicitly; this initializer imports none of them.
"""
