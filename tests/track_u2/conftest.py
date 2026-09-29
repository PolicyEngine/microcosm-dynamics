"""Shared INVENTED fixtures for the U2 milestone-2 tests.

INVENTED DATA - NOT A COMPARISON.  The inputs come from the seeded U2
generator; the thresholds are invented; the SSI capture and life tables
are the committed public parameters.  Session scope keeps the one full
ten-row invented run shared by every test that inspects it.
"""

from __future__ import annotations

import pytest

from populace_dynamics.estimates import adjusted_poverty as ap
from populace_dynamics.uniform_cut_track_u2 import (
    cohort,
    invented,
    parameters,
    runner,
    sources,
)


@pytest.fixture(scope="session")
def u2_inputs():
    return invented.invented_u2_inputs()


@pytest.fixture(scope="session")
def u2_params():
    return parameters.committed_u2_parameters(
        invented.invented_poverty_thresholds()
    )


@pytest.fixture(scope="session")
def declared():
    return sources.RoleContext.declared()


@pytest.fixture(scope="session")
def committed_registries():
    return sources.RegistrySet.committed()


@pytest.fixture(scope="session")
def u2_births(u2_inputs):
    return cohort.derive_u2_births(u2_inputs)


@pytest.fixture(scope="session")
def u0_cohort(u2_inputs, declared, u2_births):
    return cohort.build_u2_cohort(
        u2_inputs,
        cohort.U2CohortSpec(),
        role_context=declared,
        births=u2_births,
    )


@pytest.fixture(scope="session")
def u1_cohort(u2_inputs, declared, u2_births):
    return cohort.build_u2_cohort(
        u2_inputs,
        cohort.U2CohortSpec(row="U1"),
        role_context=declared,
        births=u2_births,
    )


@pytest.fixture(scope="session")
def u2_run(u2_inputs, u2_params, declared):
    return runner.run_track_u2(
        u2_inputs,
        u2_params,
        data_provenance=ap.INVENTED,
        role_context=declared,
    )
