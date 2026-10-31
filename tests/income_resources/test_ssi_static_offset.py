"""The static SSI offset against the pinned rules engine, on invented cases.

POPULACE_DYNAMICS_PE_US_PYTHON_SSI0 deliberately contains the static oracle
tier substring, as in test_ssi_engine.py. The check moved here from that
module, so that the engine checks there import nothing from the estimates
package.

Every literal is invented here or comes from ``ssi_invented``: the policy is
its ``INVENTED_POLICY``, the Social Security levels straddle the $20 monthly
general exclusion and run well above it, and the cut share is arbitrary.
The expected offsets are the pinned engine's own results.

The estimates import sits in the test body, after the interpreter skip, so
collecting this module where the SSI0 interpreter is absent does not load
the estimates package.
"""

import numpy as np
import pandas as pd

from .ssi_invented import INVENTED_POLICY, invented_case
from .test_ssi_engine import accepted, invented_runner

INCOME_YEAR = 2026
SOCIAL_SECURITY = (120, 240, 250, 2400, 6000)
CUT_SHARE = 0.25
CENT = 0.01


def test_static_offset_differential():
    runner = invented_runner()
    from populace_dynamics.estimates.adjusted_poverty import (
        AdjustedPovertySpec,
        SsiParameters,
        _ssi_response,
    )

    cases = []
    for index, amount in enumerate(SOCIAL_SECURITY):
        cases.extend(
            [
                invented_case(
                    f"INVENTED_BEFORE_{index}", social_security=amount
                ),
                invented_case(
                    f"INVENTED_AFTER_{index}",
                    social_security=amount * (1 - CUT_SHARE),
                ),
            ]
        )
    results = accepted(runner.run_many(cases))
    rows = pd.DataFrame(
        [
            dict(
                income_year=INCOME_YEAR,
                head_ssi=results[2 * i].total,
                wife_ssi=0,
                head_ss=amount,
                wife_ss=0,
                ofum_ssi=0,
            )
            for i, amount in enumerate(SOCIAL_SECURITY)
        ]
    )
    policy = INVENTED_POLICY
    parameters = SsiParameters(
        {INCOME_YEAR: policy["gov.ssa.ssi.amount.individual"]},
        {INCOME_YEAR: policy["gov.ssa.ssi.amount.couple"]},
        policy["gov.ssa.ssi.income.exclusions.general"],
        policy["gov.ssa.ssi.income.exclusions.earned"],
        policy["gov.ssa.ssi.income.exclusions.earned_share"],
        policy["gov.ssa.ssi.eligibility.resources.limit.individual"],
        policy["gov.ssa.ssi.eligibility.resources.limit.couple"],
        {"source": "INVENTED_POLICY"},
    )
    offset, newly_eligible = _ssi_response(
        rows,
        AdjustedPovertySpec(),
        {"fu": np.zeros(len(rows), dtype=bool)},
        parameters,
        np.full(len(rows), CUT_SHARE),
    )
    expected = np.array(
        [
            results[2 * i + 1].total - results[2 * i].total
            for i in range(len(SOCIAL_SECURITY))
        ]
    )
    # Two cents, as in test_ssi_engine's federal invariants.
    np.testing.assert_allclose(offset, expected, atol=2 * CENT, rtol=0)
    np.testing.assert_array_equal(newly_eligible, 0)
