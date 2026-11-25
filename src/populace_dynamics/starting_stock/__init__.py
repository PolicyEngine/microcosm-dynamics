"""The starting stock: the PIA behind a benefit already in payment.

The projections start from Microcosm's US population. A person there
who already draws a retired-worker or disabled-worker benefit keeps it
as state, and later rules (recomputations, a spouse's or survivor's
benefit on that worker's record) need the primary insurance amount
(PIA) behind it. The frame records the benefit and no PIA, claim age or
year of entitlement, so the model infers the PIA. This package holds
that inference as pure functions of plain values; it reads no frame and
no file.

* :mod:`~populace_dynamics.starting_stock.pia`: the forward rule from a
  PIA to a benefit, its inverse, and the bound on the gap statutory
  rounding opens between them.
* :mod:`~populace_dynamics.starting_stock.claim_age`: the claim-age
  posterior and a counter-based draw from it, and the single year of age
  behind a top-coded age.
* :mod:`~populace_dynamics.starting_stock.limits`: named limits the
  starting stock reports beside each inferred PIA.

Invariants, each a Hypothesis test in
``tests/starting_stock/test_pia_properties.py``:

1. **The unrounded inverse is exact.** For any finite PIA of zero or
   more, any COLA path and any positive claim factor,
   ``infer_pia(benefit_from_pia(pia, statutory_rounding=False))``
   returns the PIA to floating-point precision, and the other order
   returns the benefit.
2. **Rounding stays inside its bound.** With statutory rounding,
   ``benefit_from_pia(infer_pia(b))`` differs from ``b`` by at most
   ``rounding_bound``, for every benefit ``b`` the forward rule can
   produce.
3. **No negative PIA.** ``infer_pia`` never returns a negative number.
4. **Monotone.** A higher benefit never infers a lower PIA, with the
   factors held fixed.
5. **The posterior is a distribution.** Its weights are non-negative,
   sum to one, and cover only claim ages from 62 to the smaller of 70
   and the person's age.
6. **Draws are a function of the key.** The same seed and person id
   give the same claim age, and a draw doesn't change when other people
   join the batch.
7. **Draws follow the posterior.** Over many person ids, the share
   drawn at each claim age falls within a stated tolerance of the
   posterior.
8. **Disabled workers.** With a claim factor of 1, the inferred PIA is
   the benefit over the COLA factor.
"""

from __future__ import annotations

from populace_dynamics.starting_stock.claim_age import (
    claim_age_posterior,
    draw_claim_age,
    single_year_age,
)
from populace_dynamics.starting_stock.limits import (
    has_all_four_components,
    has_two_reasons,
    is_top_coded,
    needs_linked_pia,
)
from populace_dynamics.starting_stock.pia import (
    benefit_from_pia,
    cola_factor,
    disabled_worker_claim_factor,
    infer_pia,
    retired_worker_claim_factor,
    rounding_bound,
)

__all__ = [
    "benefit_from_pia",
    "claim_age_posterior",
    "cola_factor",
    "disabled_worker_claim_factor",
    "draw_claim_age",
    "has_all_four_components",
    "has_two_reasons",
    "infer_pia",
    "is_top_coded",
    "needs_linked_pia",
    "retired_worker_claim_factor",
    "rounding_bound",
    "single_year_age",
]
