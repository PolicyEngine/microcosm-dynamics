"""Track M: DynaSim exercise 4 (minimum benefits), labelled Python rules.

Exercise 4 of the DynaSim scorecard compares with Favreault, Mermin and
Steuerle, *Minimum Benefits in Social Security* (Urban Institute, 2006).
The only outcome it prints for 2025 is Table 6's share of OASDI
beneficiaries aged 62 and older who receive a minimum benefit, for Table
5's options 2-5 by All, Men and Women (the cleared availability statement,
``exercise4-target-availability-cleared-20260924.md``, item Y1).  The blind
plan ``critical-path-minimum-benefit-20260924.md`` (revision 2) proposes to
measure that share on a static PSID snapshot for income year 2022: Track M.

What this package holds (plan work items M5 and M6, in part):

* :mod:`.policy`: the Table 5 options 1-5 (schedules and uniform cuts, used
  exactly as printed; clearance ruling C1), the registered rows MS0-MS6 and
  every open choice as an explicit parameter at the plan's recommended
  default (:func:`.policy.pending_decisions`).  None of it is ratified: Max
  has not ruled on cos decision d219.
* :mod:`.coverage`: years of coverage from an earnings history, under the
  plan's covered-earnings convention (field G6).
* :mod:`.rules`: the minimum-benefit arithmetic (fields G7-G13, G22 and
  G23): the schedules, price and wage indexing of the threshold, DI
  proration, the order of the uniform cut and the minimum, the scope
  window, the worker flag and who counts as receiving the minimum.  It
  computes the PIA and the auxiliary benefits by calling the existing
  oracle (:mod:`populace_dynamics.ss`) unchanged; it adds nothing to
  ``ss/``.
* :mod:`.structure`: structural counts of the plan's population (the 2023
  wave's beneficiaries aged 62 and older): persons, dispositions and the
  availability of the earnings years that years of coverage would count.
  It computes no years of coverage, no PIA, no threshold, no minimum and no
  share receiving a minimum.

Submodules are imported explicitly; this initializer imports none of them,
so the structural-count script can prove it never loaded the rules.

Labels every output carries (:data:`OUTPUT_LABELS`, plan bottom line 2):
PSID-realized outcomes, not a projection; income year 2022, not 2025;
Python rules, not Axiom; static.
"""

from __future__ import annotations

__all__ = ["OUTPUT_LABELS"]

#: The four labels every Track M output carries (plan bottom line 2; card
#: item 2 of cos decision d219, pending).
OUTPUT_LABELS: tuple[str, ...] = (
    "PSID-realized outcomes (not a projection)",
    "income year 2022 (not 2025)",
    "Python rules (not Axiom)",
    "static",
)
