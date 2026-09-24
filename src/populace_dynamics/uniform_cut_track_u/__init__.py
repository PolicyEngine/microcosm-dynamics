"""Track U assembly for DynaSim scorecard exercise 2 (uniform 13% cut).

Plan ``critical-path-uniform-cut-20260923.md`` (work items U5, U9, U10
and field F17).  The Track U layer itself lives in
:mod:`populace_dynamics.data.family_income`,
:mod:`populace_dynamics.cohorts.age67`,
:mod:`populace_dynamics.estimates.adjusted_poverty` and
:mod:`populace_dynamics.estimates.uniform_cut_tabulation`; this package
composes it:

* :mod:`.rows` -- the registered rows (U0-U10, U-inst) as builder and
  income-concept parameters, checked against the specification block;
* :mod:`.invented` -- the INVENTED age-67 cohort generator and the
  INVENTED threshold table (dry runs and tests only);
* :mod:`.runner` -- the row pipeline (cohort, income rows, income
  concept, tabulation) and the official-concept diagnostic, with the
  provenance guards;
* :mod:`.diagnostics` -- the F17 component summaries (Social Security,
  SSI, WEALTH1) against committed published aggregates.  It imports
  neither the income concept nor the tabulation, so the pre-registration
  diagnostics script can prove it computed no poverty statistic.

Submodules are imported explicitly, never re-exported here, so importing
:mod:`.diagnostics` does not load the income concept.

Every output is a *PSID-realized outcome (not a projection)* computed
with a *Python income concept (not Axiom)* under *mechanical
incidence*.
"""

from __future__ import annotations

#: The first line of every invented-data dry-run output.
DRY_RUN_HEADER = "INVENTED DATA - NOT A COMPARISON"
#: The first line of the registered one-shot artifact.
REGISTERED_HEADER = (
    "REGISTERED ONE-SHOT RUN - Track U, DynaSim exercise 2 (uniform 13% "
    "cut, adjusted poverty at 67, 1936-45 cohort). PSID-realized outcomes "
    "(not a projection); Python income concept (not Axiom); mechanical "
    "incidence. Publishes regardless of outcome."
)

__all__ = ["DRY_RUN_HEADER", "REGISTERED_HEADER"]
