"""Held-out target U2: Boomers 2004, 1946-55 column, uniform 13% cut.

Specification ``docs/design/boomers2004_1946_55_comparison.md``
(``u2-draft-4``), sections 3-15; section 16a's amendments are proposals
pending Max's ruling and change nothing here.  U2 extends U1's static
measurement (:mod:`populace_dynamics.uniform_cut_track_u`) to the
1946-55 birth cohort on the 2013-2023 PSID waves.  It never edits a U1 module: U1's
constants, defaults, registered behaviour, parameter captures and
artifacts stay byte-identical, and every U2 identity (target, column,
rows, rulings, parameters, artifact path) is separate and refuses its U1
counterpart.

Modules (imported explicitly, never re-exported here, so importing
:mod:`.diagnostics` or :mod:`.cohort` does not load the income concept):

* :mod:`.identity` -- the U2 target identity and the cross-cohort
  refusals;
* :mod:`.sources` -- the milestone-1 documentary registries bound to
  their pinned bytes, the section 3 role rules, the fixed-width adapters
  and the source gate that refuses every route still marked TO VERIFY;
* :mod:`.parameters` -- the Track M Census capture read in full, the
  separate U2 SSI capture and the life tables, bound to U2;
* :mod:`.cohort` -- the support and observation plans, the builder and
  the income rows;
* :mod:`.estimator` -- the U2 income concept with its explicit parameter
  and role context;
* :mod:`.tabulation` -- the frozen statistic under U2's own identity;
* :mod:`.rows`, :mod:`.runner` -- the ten registered rows, the literal
  named deltas, the U2 rulings record and the fixed U0 headline;
* :mod:`.invented` -- INVENTED inputs, thresholds and fixed-width records
  (dry runs and tests only);
* :mod:`.diagnostics` -- F17 component summaries (no poverty import);
* :mod:`.memo` -- the comparison-memo classification rules of section
  10a (no comparator value is held anywhere in the repository);
* :mod:`.loader` -- the registered real-data loader, which refuses before
  opening any PSID record while a required route is unresolved.

Every output is a *PSID-realized outcome (not a projection)* computed
with a *Python income concept (not Axiom)* under *mechanical incidence*.
"""

from __future__ import annotations

#: The first line of every invented-data U2 output (specification
#: sections 13 and 14).
DRY_RUN_HEADER = "INVENTED DATA - NOT A COMPARISON"
#: The first line of the eventual registered one-shot artifact.
REGISTERED_HEADER = (
    "REGISTERED ONE-SHOT RUN - held-out target U2 (Boomers 2004, 1946-55 "
    "column, uniform 13% cut, adjusted poverty at 67). PSID-realized "
    "outcomes (not a projection); Python income concept (not Axiom); "
    "mechanical incidence. Publishes regardless of outcome."
)

__all__ = ["DRY_RUN_HEADER", "REGISTERED_HEADER"]
