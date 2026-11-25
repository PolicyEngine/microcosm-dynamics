"""Shared fixtures for the starting-stock tests, and an import guard.

The guard is a ``sys.meta_path`` finder, installed when this conftest is
imported, that refuses two modules no starting-stock test may load. If
it ever fires, its message names the module that tried the import.
"""

from __future__ import annotations

import sys

import pytest

from populace_dynamics.ss.params import SSAParameters

#: Modules no starting-stock test may import or load.
BARRED_MODULES = frozenset(
    {
        "populace_dynamics.estimates.adjusted_poverty",
        "populace_dynamics.uniform_cut_track_u.rows",
    }
)

_IMPORT_MACHINERY = ("importlib", "_frozen_importlib")


def _importer() -> str:
    """The first module on the stack outside the import machinery."""
    frame = sys._getframe(2)
    while frame is not None:
        name = frame.f_globals.get("__name__", "")
        if name != __name__ and not name.startswith(_IMPORT_MACHINERY):
            return name
        frame = frame.f_back
    return "<unknown>"


class _BarredModuleFinder:
    """Raise ImportError for a barred module before any finder looks."""

    def find_spec(self, fullname, path=None, target=None):
        if fullname in BARRED_MODULES:
            raise ImportError(
                f"import guard: {fullname} is barred (imported from "
                f"{_importer()})"
            )
        return None


if not any(isinstance(f, _BarredModuleFinder) for f in sys.meta_path):
    sys.meta_path.insert(0, _BarredModuleFinder())


@pytest.fixture(scope="session")
def barred_module_names() -> frozenset[str]:
    """The module names the import guard refuses."""
    return BARRED_MODULES


@pytest.fixture(scope="session")
def invented_ssa_parameters() -> SSAParameters:
    """INVENTED parameters with the shape of ``SSAParameters``.

    Every value is invented for these tests and stands for no year's
    law: a full-retirement-age schedule by birth year, the two early
    reduction rates and their bracket, and delayed credits by birth
    year. No checkout is read.
    """
    return SSAParameters(
        nawi={},
        wage_base={},
        pia_factors=(0.85, 0.30, 0.12),
        fra_months_by_birth_year=[(1900, 774), (1940, 786), (1958, 798)],
        early_monthly_rates=(0.006, 0.004),
        early_first_bracket_months=30,
        pe_us_revision="INVENTED",
        delayed_credit_by_birth_year=[(1900, 0.04), (1942, 0.07)],
        max_delayed_months=48,
    )
