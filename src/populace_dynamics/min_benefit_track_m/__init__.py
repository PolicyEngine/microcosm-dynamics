"""Track M: DynaSim exercise 4 (minimum benefits), labelled Python rules.

Exercise 4 of the DynaSim scorecard compares with Favreault, Mermin and
Steuerle, *Minimum Benefits in Social Security* (Urban Institute, 2006).
The only outcome it prints for 2025 is Table 6's share of OASDI
beneficiaries aged 62 and older who receive a minimum benefit, for Table
5's options 2-5 by All, Men and Women (the cleared availability statement,
``exercise4-target-availability-cleared-20260924.md``, item Y1).  The blind
plan ``critical-path-minimum-benefit-20260924.md`` (revision 2) measures
that share on a static PSID snapshot for income year 2022: Track M.  Max
accepted all nine defaults of the plan's card on 2026-09-24 (cos decision
d219), ruled PSID labor income covered earnings on 2026-09-25 (d280) and
had the 2013-2022 Census thresholds downloaded (d279).  The M1
specification (``docs/design/minimum_benefits_comparison.md``,
``m1-draft-2``) is not ratified yet: an independent check of the referee's
changes comes first, then the merge.

What this package holds:

* :mod:`.policy`: the Table 5 options 1-5 (schedules and uniform cuts, used
  exactly as printed; clearance ruling C1), the registered rows MS0-MS6,
  Max's rulings (:data:`.policy.MAX_RULINGS`) and the frozen choices.
* :mod:`.coverage`: years of coverage from the one history per worker
  (field G6; referee R6 and R7).
* :mod:`.thresholds`: the pinned Census one-person 65+ thresholds,
  2003-2022 (plan item M2).
* :mod:`.rules`: the minimum-benefit arithmetic (fields G5, G7-G13, G22 and
  G23) and the years that define each record (section 4a).  It computes
  the PIA and the auxiliary benefits by calling the existing oracle
  (:mod:`populace_dynamics.ss`) unchanged; it adds nothing to ``ss/``.
* :mod:`.evaluation`: worker and person records to each person's receipt
  flags under each option (the rules side of plan items M5 and M8).
* :mod:`.tabulation`: the Table 6 statistic, the share of the universe
  receiving a minimum, with the five-seed floor and the design-based
  standard error (plan item M8).  It refuses PSID-built rows without the
  issue #42 registration pointer and a ratified M1 specification.
* :mod:`.pipeline`: every registered row MS0-MS6 end to end, after the
  threshold-year check (plan item M10).
* :mod:`.invented`: an INVENTED PSID-shaped cohort for the dry run.
* :mod:`.specification`: reads the M1 specification's parameter block and
  refuses a registered run the block does not authorize.
* :mod:`.structure`: structural counts of the plan's population.  It
  computes no years of coverage, no PIA, no threshold, no minimum and no
  share receiving a minimum.

The PSID readers of plan items M3-M5 (the beneficiary cohort and the
realized careers) are not built, so nothing here can compute the share on
real data.

Submodules are imported explicitly; this initializer imports none of them,
so the structural-count script can prove it never loaded the rules.

Labels every output carries (:data:`OUTPUT_LABELS`, plan bottom line 2):
PSID-realized outcomes, not a projection; income year 2022, not 2025;
Python rules, not Axiom; static.  Every result also carries
:data:`COVERED_EARNINGS_DISCLOSURE` (d280).
"""

from __future__ import annotations

__all__ = [
    "COVERED_EARNINGS_DISCLOSURE",
    "DRY_RUN_HEADER",
    "OUTPUT_LABELS",
]

#: The four labels every Track M output carries (plan bottom line 2; d219
#: item 2, ruled 2026-09-24: default accepted).
OUTPUT_LABELS: tuple[str, ...] = (
    "PSID-realized outcomes (not a projection)",
    "income year 2022 (not 2025)",
    "Python rules (not Axiom)",
    "static",
)
#: Max's d280 ruling (2026-09-25): the covered-earnings convention is
#: "disclosed in the spec and every result".
COVERED_EARNINGS_DISCLOSURE = (
    "PSID labor income is treated as covered earnings: the PSID does not "
    "observe Social Security coverage, so noncovered earnings count "
    "(cos decision d280, 2026-09-25, as in exercises 1 and 3 and Track C)"
)
#: The header of every invented-data dry-run output (plan item M10).
DRY_RUN_HEADER = "INVENTED DATA - NOT A COMPARISON"
