"""Build the real PSID 2010 starting cohort and check structural invariants.

Skipped when the staged PSID products under ``~/PolicyEngine/psid-data``
are absent. The test asserts structure only (row counts, weight positivity,
birth-year range, unique identifiers, partition totals); it pins no count
and computes no benefit, reform or comparison statistic.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from populace_dynamics.cohorts import psid2010 as cohort
from populace_dynamics.data import family
from populace_dynamics.estimates import career

REAL_DATA = Path("~/PolicyEngine/psid-data").expanduser()
_NEEDED = (
    REAL_DATA / "ind2023er" / "IND2023ER.txt",
    REAL_DATA / "mh85_23" / "MH85_23.txt",
    *(REAL_DATA / "family" / str(wave) for wave in family.FAMILY_WAVES),
)
needs_real_psid = pytest.mark.skipif(
    not all(path.exists() for path in _NEEDED),
    reason="staged PSID individual, marriage and family files not present",
)


@needs_real_psid
def test_real_cohort_structural_invariants():
    inputs = cohort.load_psid2010_inputs(data_dir=REAL_DATA)
    built = cohort.build_psid2010_cohort(inputs)
    persons = built.persons
    dispositions = built.dispositions

    # Row counts and partition totals.
    assert len(persons) > 0
    assert persons["person_id"].is_unique
    assert dispositions["person_id"].is_unique
    anchor = inputs.anchor
    universe = anchor[
        anchor["sequence"].between(1, 20) & (anchor["weight"] > 0)
    ]
    assert set(dispositions["person_id"]) == set(universe["person_id"])
    members = dispositions[dispositions["disposition"] == "member"]
    assert set(members["person_id"]) == set(persons["person_id"])
    assert set(dispositions["disposition"]) <= {
        "member",
        "excluded_birth_year_unresolved",
        "outside_birth_cohort",
        "excluded_sex_unknown",
    }
    assert len(built.social_security) == len(cohort.SS_YEARS) * len(persons)
    assert not built.social_security.duplicated(
        ["person_id", "income_year"]
    ).any()

    # Weights: the 2011 cross-sectional weight is positive for every member.
    assert (persons["weight"] > 0).all()
    assert persons["weight"].notna().all()
    # Every positive ER34155 weight is either a disposition or counted in
    # the outside-presence diagnostic; no weight leaves silently.
    outside = built.diagnostics["positive_weight_outside_presence"]
    assert "in_family" not in outside
    accounted = dispositions["weight"].sum() + sum(
        group["weighted"] for group in outside.values()
    )
    assert accounted == pytest.approx(
        anchor.loc[anchor["weight"] > 0, "weight"].sum()
    )
    assert persons["m4_status_unknown"].dtype == bool

    # Birth years: resolved, within the section 3.1 support, born <= 1980.
    assert persons["birth_year"].notna().all()
    assert persons["birth_year"].max() <= cohort.DEFAULT_MAX_BIRTH_YEAR
    assert persons["birth_year"].min() >= career.DERIVED_BIRTH_MIN
    assert set(persons["sex"]) <= {"male", "female"}

    # Every member has one opening status; recipients are classified.
    assert persons["opening_status"].notna().all()
    receipt = persons["ss_receipt_2010"].fillna(False).astype(bool)
    assert (persons.loc[receipt, "opening_status"] != "none").all()
    assert (persons.loc[~receipt, "opening_status"] != "retired_worker").all()

    # Careers stay inside 1968-2010 and cover only members.
    careers = built.careers
    assert careers["year"].between(1968, 2010).all()
    assert set(careers["person_id"]) <= set(persons["person_id"])
    assert not careers.duplicated(["person_id", "year"]).any()
