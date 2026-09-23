"""Track A assembly tests on INVENTED data only.

Every person, earnings amount, Social Security amount, weight, rate, life
table, DI probability, claim-age PMF, wage index and COLA below is
INVENTED for testing.  No test reads PSID, a committed parameter file or
a comparator value; the one exception is the A1 specification document,
whose registered-row and rulings block the assembly must agree with.
"""

from __future__ import annotations

import math
from dataclasses import replace
from functools import lru_cache
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from populace_dynamics import claiming
from populace_dynamics import scenario_benefits as sb
from populace_dynamics.cohorts import psid2010
from populace_dynamics.cola_track_a import (
    INVENTED_COHORT_LABEL,
    REGISTERED_ROWS,
    TrackAConfig,
    TrackAInputs,
    invented,
    prepare_track_a_cohort,
    run_track_a,
)
from populace_dynamics.cola_track_a import benefits as track_benefits
from populace_dynamics.cola_track_a import opening as opening_module
from populace_dynamics.cola_track_a.adapters import (
    adopt_marital_state,
    claiming_schedule,
    di_aware_claiming,
    widowhood_marital_step,
)
from populace_dynamics.cola_track_a.config import (
    MAX_RULINGS,
    TRACK_A_LABELS,
    LevelPolicy,
    builder_defaults,
    max_rulings,
    rulings_departures,
)
from populace_dynamics.cola_track_a.mortality import (
    Tr2008YearAwareMortality,
)
from populace_dynamics.cola_track_a.opening import (
    OpeningStockRecord,
    TrackACohort,
    track_a_cohort_sha256,
)
from populace_dynamics.cola_track_a.runner import (
    _check_output_labels,
    _check_source_provenance,
    _component_shares,
    a1_parameter_block,
)
from populace_dynamics.engine.di_entitlement_rates import (
    MAX_AGE,
    DIEntitlementRates,
    DIEntitlementSpec,
)
from populace_dynamics.engine.loop import (
    PeriodContext,
    ProjectionResult,
)
from populace_dynamics.engine.rng import ProjectionRNGRegistry
from populace_dynamics.engine.steps import AgeSexMortalityModel
from populace_dynamics.estimates.cola_age_profile import (
    INVENTED_DATA_LABEL,
)
from populace_dynamics.estimates.parameters import COLASeries
from populace_dynamics.ss import benefits
from populace_dynamics.ss.params import SSAParameters

SHAPE = (2, MAX_AGE + 1)


# --------------------------------------------------------------------------
# INVENTED parameters
# --------------------------------------------------------------------------
def invented_params() -> SSAParameters:
    """INVENTED oracle parameters: 4 percent wage growth from 1951."""
    return SSAParameters(
        nawi={
            year: 2_800.0 * 1.04 ** (year - 1951) for year in range(1951, 2061)
        },
        wage_base={1937: 3_000.0, 1975: 14_100.0, 1990: 51_300.0},
        pia_factors=(0.9, 0.32, 0.15),
        fra_months_by_birth_year=[(1900, 792), (1955, 804)],
        early_monthly_rates=(5 / 900, 5 / 1200),
        early_first_bracket_months=36,
        pe_us_revision="INVENTED",
        delayed_credit_by_birth_year=[(1900, 0.08)],
    )


def invented_cola() -> COLASeries:
    """INVENTED determination-year COLA fractions (every one above 1%)."""
    return COLASeries(
        by_determination_year={
            year: 0.02 + 0.002 * (year % 5) for year in range(1979, 2032)
        },
        provenance={"invented": True},
    )


def invented_di_rates(**spec_changes) -> DIEntitlementRates:
    incidence = np.zeros(SHAPE)
    incidence[:, 18:70] = 0.006
    return DIEntitlementRates(
        spec=DIEntitlementSpec(**spec_changes),
        incidence=incidence,
        recovery_attained=np.full(SHAPE, 0.01),
        death_attained=np.full(SHAPE, 0.02),
        population_reference_death=np.full(SHAPE, 0.01),
        recovery_select=None,
        death_select=None,
        recovery_level_factor=1.0,
        death_level_factor=1.0,
    )


def invented_mortality(ratio: float = 1.0) -> Tr2008YearAwareMortality:
    ages = np.arange(MAX_AGE + 1)
    qx = np.minimum(0.0001 * np.exp(0.085 * ages), 1.0)
    return Tr2008YearAwareMortality(
        qx_by_sex={"female": qx * 0.8, "male": qx},
        ratio_by_year={year: (ratio, ratio) for year in range(2009, 2032)},
        alternative="INVENTED",
        base_year=2004,
    )


CONFIG = TrackAConfig(draw_indices=(0, 1))


@lru_cache(maxsize=1)
def _cohort_2009() -> TrackACohort:
    """The INVENTED people read as the 2009 wave (row R6's population)."""
    return prepare_track_a_cohort(
        psid2010.build_psid2010_cohort(
            invented.invented_psid2010_inputs(seed=7, anchor_wave=2009),
            psid2010.Psid2010CohortSpec(anchor_wave=2009),
        ),
        data_provenance="invented",
        config=CONFIG,
    )


def _inputs(cohort: TrackACohort, **changes) -> TrackAInputs:
    values = {
        "cohort": cohort,
        "params": invented_params(),
        "baseline": invented_cola(),
        "di_rates": invented_di_rates(),
        "population_mortality": invented_mortality(),
        "claiming_pmf": invented.invented_claiming_pmf(),
        "additional_cohorts": (_cohort_2009(),),
    }
    values.update(changes)
    return TrackAInputs(**values)


@pytest.fixture(scope="module")
def a3_cohort() -> psid2010.Psid2010Cohort:
    return psid2010.build_psid2010_cohort(
        invented.invented_psid2010_inputs(seed=7)
    )


@pytest.fixture(scope="module")
def cohort(a3_cohort) -> TrackACohort:
    return prepare_track_a_cohort(
        a3_cohort, data_provenance="invented", config=CONFIG
    )


@pytest.fixture(scope="module")
def result(cohort) -> dict:
    return run_track_a(_inputs(cohort), config=CONFIG)


# --------------------------------------------------------------------------
# Opening state
# --------------------------------------------------------------------------
def test_initial_slice_carries_no_realized_death_columns(cohort):
    columns = set(cohort.initial_slice.columns)
    assert not {c for c in columns if c.startswith("death")}
    assert set(cohort.initial_slice["year"]) == {2010}
    assert (
        cohort.initial_slice["age"]
        == 2010 - cohort.initial_slice["birth_year"]
    ).all()


def test_opening_clocks_follow_the_a1_rules(cohort):
    persons = cohort.persons.set_index("person_id")
    rules = set()
    for person_id, record in cohort.opening.items():
        row = persons.loc[person_id]
        rules.add(record.clock_rule)
        if record.status == "retired_worker":
            assert record.clock_year == row["birth_year"] + 62
        if record.status == "disabled_worker" or row["age_opening"] < 62:
            receipt = row["opening_claim_year"]
            if pd.isna(receipt):
                receipt = row["opening_claim_year_upper_bound"]
            assert record.clock_year == receipt
        if record.clock_rule == "linked_worker_birth_plus_62":
            assert record.clock_year == row["linked_spouse_birth_year"] + 62
        assert record.clock_year <= 2010
        assert record.entitlement_year >= record.clock_year
        assert record.observed_annual_amount == row["ss_opening"]
    assert {"own_birth_plus_62", "a3_receipt_start"} <= rules
    assert rules & {
        "linked_worker_birth_plus_62",
        "linked_worker_death_before_eligibility",
    }


def test_opening_di_stock_is_the_a3_disabled_workers(cohort):
    frame = cohort.initial_slice.set_index("person_id")
    persons = cohort.persons.set_index("person_id")
    disabled = persons["opening_status"] == "disabled_worker"
    assert (
        frame["di_entitled"].to_numpy(dtype=bool)
        == disabled.reindex(frame.index).to_numpy(dtype=bool)
    ).all()
    assert frame["di_entitled"].any()
    assert not frame.loc[frame["di_entitled"], "claimed"].any()


def test_2009_wave_opening_state_is_as_of_2008():
    r6 = _cohort_2009()
    a3 = psid2010.build_psid2010_cohort(
        invented.invented_psid2010_inputs(seed=7, anchor_wave=2009),
        psid2010.Psid2010CohortSpec(anchor_wave=2009),
    ).persons.set_index("person_id")
    assert (r6.anchor_wave, r6.start_year) == (2009, 2008)
    assert set(r6.initial_slice["year"]) == {2008}
    persons = r6.persons.set_index("person_id")
    assert (persons["age_opening"] == 2008 - persons["birth_year"]).all()
    assert (
        persons["family_unit_id"] == a3.loc[persons.index, "interview_2009"]
    ).all()
    assert r6.opening
    for person_id, record in r6.opening.items():
        assert record.clock_year <= 2008
        assert record.observed_annual_amount == a3.loc[person_id, "ss_2008"]


def test_prepare_refuses_unknown_provenance(a3_cohort):
    with pytest.raises(ValueError, match="data_provenance"):
        prepare_track_a_cohort(a3_cohort, data_provenance="psid")


# --------------------------------------------------------------------------
# Provenance: the label must agree with what the A3 builder recorded
# --------------------------------------------------------------------------
def _psid_files_a3() -> psid2010.Psid2010Cohort:
    """The INVENTED frames under an INVENTED psid_files provenance: what
    the A3 builder records for a cohort read from PSID files.  The loader's
    seal is applied the way ``load_psid2010_inputs`` applies it, standing
    in for a PSID read."""
    inputs = invented.invented_psid2010_inputs(seed=7)
    stamped = replace(
        inputs,
        provenance={
            "kind": psid2010.PSID_FILES,
            "psid_data_dir": "/invented/psid",
            "psid_files_sha256": {"ind2023er/IND2023ER.txt": "ab" * 32},
            "psid_files_bundle_sha256": "cd" * 32,
        },
    )
    return psid2010.build_psid2010_cohort(
        psid2010._seal_loaded_inputs(stamped)
    )


def test_a_psid_files_cohort_cannot_be_labeled_invented():
    a3 = _psid_files_a3()
    assert a3.provenance["kind"] == psid2010.PSID_FILES
    with pytest.raises(ValueError, match="cannot be labeled invented"):
        prepare_track_a_cohort(a3, data_provenance="invented", config=CONFIG)
    # The label the provenance supports is accepted and recorded.
    real = prepare_track_a_cohort(
        a3, data_provenance="registered_real", config=CONFIG
    )
    assert real.data_provenance == "registered_real"
    assert real.source_provenance["kind"] == psid2010.PSID_FILES
    assert real.source_provenance["psid_files_sha256"] == {
        "ind2023er/IND2023ER.txt": "ab" * 32
    }
    assert real.diagnostics["source_provenance_kind"] == psid2010.PSID_FILES


def test_an_invented_cohort_cannot_be_labeled_registered_real(a3_cohort):
    assert a3_cohort.provenance["kind"] == psid2010.INVENTED
    with pytest.raises(ValueError, match="recorded PSID files"):
        prepare_track_a_cohort(
            a3_cohort, data_provenance="registered_real", config=CONFIG
        )


def _reseal(cohort: TrackACohort) -> TrackACohort:
    """Forge the preparation seal on a replaced cohort (a deliberate
    bypass of the frozen dataclass), to reach the checks behind it."""
    object.__setattr__(cohort, "seal", track_a_cohort_sha256(cohort))
    return cohort


def test_a_relabelled_prepared_cohort_is_refused_by_the_runner():
    # The prepared real cohort relabelled invented after preparation:
    # without the runner's check it would skip the registration pointer.
    real = prepare_track_a_cohort(
        _psid_files_a3(), data_provenance="registered_real", config=CONFIG
    )
    relabelled = replace(real, data_provenance="invented")
    config = TrackAConfig(draw_indices=(0,), rows=("R0",))
    with pytest.raises(ValueError, match="source provenance is 'psid_files'"):
        run_track_a(_inputs(relabelled, additional_cohorts=()), config=config)
    # Relabelled on every field the runner reads (the label, the output
    # labels and the source provenance's kind): the preparation seal no
    # longer matches, since dataclasses.replace resets it.
    everywhere = replace(
        real,
        data_provenance="invented",
        labels=(INVENTED_COHORT_LABEL, *TRACK_A_LABELS[1:]),
        source_provenance={
            **dict(real.source_provenance),
            "kind": psid2010.INVENTED,
        },
    )
    assert everywhere.seal is None
    with pytest.raises(ValueError, match="does not match the seal"):
        run_track_a(_inputs(everywhere, additional_cohorts=()), config=config)


def test_a_prepared_cohort_edited_in_place_is_refused_by_the_runner():
    # INVENTED cohort, edited in place after preparation (no field is
    # replaced, so the frozen dataclass does not stop it): every kind of
    # edit breaks the preparation seal.
    config = TrackAConfig(draw_indices=(0,), rows=("R0",))

    def prepared() -> TrackACohort:
        return prepare_track_a_cohort(
            psid2010.build_psid2010_cohort(
                invented.invented_psid2010_inputs(seed=7)
            ),
            data_provenance="invented",
            config=config,
        )

    untouched = prepared()
    assert untouched.seal == track_a_cohort_sha256(untouched)

    def weight(cohort):
        cohort.initial_slice.loc[cohort.initial_slice.index[0], "weight"] *= 2

    def opening_amount(cohort):
        person_id = next(iter(cohort.opening))
        cohort.opening[person_id] = replace(
            cohort.opening[person_id], observed_annual_amount=1.0e6
        )

    def career(cohort):
        person_id = next(p for p, c in cohort.careers.items() if c)
        year = next(iter(cohort.careers[person_id]))
        cohort.careers[person_id][year] += 1.0

    def persons(cohort):
        cohort.persons.loc[cohort.persons.index[0], "ss_opening"] = 1.0e6

    for edit in (weight, opening_amount, career, persons):
        cohort = prepared()
        edit(cohort)
        with pytest.raises(ValueError, match="does not match the seal"):
            run_track_a(_inputs(cohort, additional_cohorts=()), config=config)


def test_a_run_refuses_output_labels_its_label_does_not_call_for():
    check = _check_output_labels
    invented_labels = (INVENTED_COHORT_LABEL, *TRACK_A_LABELS[1:])
    check(TRACK_A_LABELS, "registered_real")
    check(invented_labels, "invented")
    for labels, provenance in (
        (invented_labels, "registered_real"),
        # Dropping "Python oracle (not Axiom)" departs from Max's ruling on
        # decision 1 (d074).
        (TRACK_A_LABELS[:1] + TRACK_A_LABELS[2:], "registered_real"),
        (TRACK_A_LABELS, "invented"),
    ):
        with pytest.raises(ValueError, match="must carry the labels"):
            check(labels, provenance)
    # End to end: an INVENTED cohort whose labels were replaced and whose
    # seal was forged reaches the label check.
    config = TrackAConfig(draw_indices=(0,), rows=("R0",))
    cohort = prepare_track_a_cohort(
        psid2010.build_psid2010_cohort(
            invented.invented_psid2010_inputs(seed=7)
        ),
        data_provenance="invented",
        config=config,
    )
    relabelled = _reseal(replace(cohort, labels=TRACK_A_LABELS))
    with pytest.raises(ValueError, match="must carry the labels"):
        run_track_a(_inputs(relabelled, additional_cohorts=()), config=config)


def test_cohorts_without_a_verifiable_provenance_are_refused():
    inputs = invented.invented_psid2010_inputs(seed=7)
    # Frames with no recorded provenance (assembled by the caller).
    bare = psid2010.build_psid2010_cohort(replace(inputs, provenance={}))
    assert bare.provenance["kind"] == psid2010.CALLER_FRAMES
    for label in ("invented", "registered_real"):
        with pytest.raises(ValueError, match="'caller_frames'"):
            prepare_track_a_cohort(bare, data_provenance=label)
    # A cohort replaced after the build loses the builder's seal.
    built = psid2010.build_psid2010_cohort(inputs)
    unsealed = replace(built, persons=built.persons.copy())
    with pytest.raises(ValueError, match="'unsealed'"):
        prepare_track_a_cohort(unsealed, data_provenance="invented")
    # A cohort edited in place no longer matches its sealed content.
    built.persons.loc[built.persons.index[0], "weight"] += 1.0
    with pytest.raises(ValueError, match="changed after the build"):
        prepare_track_a_cohort(built, data_provenance="invented")


def test_a_forged_invented_provenance_on_a_psid_cohort_is_refused():
    # A cohort built from (stand-in) PSID files whose provenance record is
    # overwritten with a genuine invented seed and frame digest: every
    # recorded field checks out, but the invented generator does not
    # reproduce the cohort's data, so prepare refuses the invented label.
    a3 = _psid_files_a3()
    # The record itself cannot be edited in place.
    with pytest.raises(TypeError):
        a3.provenance["kind"] = psid2010.INVENTED
    assert not hasattr(a3.provenance, "update")
    nested = a3.provenance["psid_files_sha256"]
    nested["ind2023er/IND2023ER.txt"] = "00" * 32
    assert a3.provenance["psid_files_sha256"] == {
        "ind2023er/IND2023ER.txt": "ab" * 32
    }
    seed = 20260922
    forged = {
        **dict(a3.provenance),
        "kind": psid2010.INVENTED,
        "seed": seed,
        "input_frames_sha256": invented.invented_frames_sha256(
            seed=seed, anchor_wave=2011
        ),
    }
    object.__setattr__(a3, "provenance", psid2010.ReadOnlyProvenance(forged))
    with pytest.raises(ValueError, match="persons or careers are not what"):
        prepare_track_a_cohort(a3, data_provenance="invented", config=CONFIG)
    # A record with no seed (and so no digest to re-generate) is refused.
    object.__setattr__(
        a3,
        "provenance",
        psid2010.ReadOnlyProvenance(
            {**forged, "seed": None, "input_frames_sha256": None}
        ),
    )
    with pytest.raises(ValueError, match="does not produce its input"):
        prepare_track_a_cohort(a3, data_provenance="invented", config=CONFIG)


def test_a_relabelled_psid_cohort_with_forged_source_is_refused_by_runner():
    # A prepared PSID-provenance cohort whose label, labels and source
    # provenance are all replaced to read as invented, with the
    # preparation seal forged as well: the runner re-generates the
    # invented population and refuses it.
    real = prepare_track_a_cohort(
        _psid_files_a3(), data_provenance="registered_real", config=CONFIG
    )
    forged = _reseal(
        replace(
            real,
            data_provenance="invented",
            labels=(INVENTED_COHORT_LABEL, *real.labels[1:]),
            source_provenance=psid2010.ReadOnlyProvenance(
                {
                    **dict(real.source_provenance),
                    "kind": psid2010.INVENTED,
                    "seed": 20260922,
                }
            ),
        )
    )
    config = TrackAConfig(draw_indices=(0,), rows=("R0",))
    with pytest.raises(ValueError, match="not the invented generator's"):
        run_track_a(_inputs(forged, additional_cohorts=()), config=config)
    # The genuine invented cohort of that seed passes the same check ...
    genuine = prepare_track_a_cohort(
        psid2010.build_psid2010_cohort(
            invented.invented_psid2010_inputs(seed=20260922)
        ),
        data_provenance="invented",
        config=config,
    )
    _check_source_provenance({2011: genuine}, "invented")
    # ... but not with the stand-in PSID persons swapped in.
    swapped = _reseal(replace(genuine, persons=real.persons))
    with pytest.raises(ValueError, match="not the invented generator's"):
        run_track_a(_inputs(swapped, additional_cohorts=()), config=config)


def test_invented_provenance_must_regenerate_from_its_seed():
    # INVENTED: the seed-7 frames stamped as if seed 8 had produced them.
    inputs = invented.invented_psid2010_inputs(seed=7)
    misstamped = replace(
        inputs, provenance={**dict(inputs.provenance), "seed": 8}
    )
    a3 = psid2010.build_psid2010_cohort(misstamped)
    assert a3.provenance["kind"] == psid2010.INVENTED
    with pytest.raises(ValueError, match="does not produce its input"):
        prepare_track_a_cohort(a3, data_provenance="invented")


# --------------------------------------------------------------------------
# Adapters
# --------------------------------------------------------------------------
def _context(year: int, ids) -> PeriodContext:
    return PeriodContext(
        period_index=year - 2010,
        year=year,
        draw_index=0,
        metadata={},
        rng_registry=ProjectionRNGRegistry(0, 20),
        person_ordinals={pid: i for i, pid in enumerate(sorted(ids))},
    )


def _marital_frame(rows) -> pd.DataFrame:
    frame = pd.DataFrame(
        rows,
        columns=[
            "person_id",
            "marital_status",
            "spouse_person_id",
            "widowhood_year",
            "late_spouse_person_id",
        ],
    )
    frame["year"] = 2015
    frame["marital_status"] = frame["marital_status"].astype(object)
    for column in (
        "spouse_person_id",
        "widowhood_year",
        "late_spouse_person_id",
    ):
        frame[column] = frame[column].astype("Int64")
    frame["widowed_in_projection"] = False
    return frame


def test_marital_step_widows_only_survivors_of_roster_deaths():
    # 1 and 2 married (2 died this year); 3 married to 9, outside roster;
    # 4 married to 5, both alive.
    frame = _marital_frame(
        [
            (1, "married", 2, pd.NA, pd.NA),
            (3, "married", 9, pd.NA, pd.NA),
            (4, "married", 5, pd.NA, pd.NA),
            (5, "married", 4, pd.NA, pd.NA),
        ]
    )
    context = _context(2015, [1, 2, 3, 4, 5])
    marital = widowhood_marital_step(
        frame, context, None, roster_ids=frozenset({1, 2, 3, 4, 5})
    )
    out = adopt_marital_state(frame, context, marital, None).set_index(
        "person_id"
    )
    assert out.at[1, "marital_status"] == "widowed"
    assert out.at[1, "widowhood_year"] == 2015
    assert out.at[1, "late_spouse_person_id"] == 2
    assert pd.isna(out.at[1, "spouse_person_id"])
    assert bool(out.at[1, "widowed_in_projection"])
    for person_id in (3, 4, 5):
        assert out.at[person_id, "marital_status"] == "married"
        assert not bool(out.at[person_id, "widowed_in_projection"])
    assert marital.births.empty


def test_claiming_skips_entitled_disabled_workers():
    frame = pd.DataFrame(
        {
            "person_id": [1, 2, 3],
            "year": 2015,
            "age": [55, 55, 67],
            "sex": ["male", "female", "male"],
            "di_entitled": [True, False, False],
            "di_converted": [False, False, True],
            "claimed": [False, False, False],
            "claim_age": pd.array([pd.NA] * 3, dtype="Int64"),
            "claim_year": pd.array([pd.NA] * 3, dtype="Int64"),
        }
    )
    schedule = claiming_schedule(
        invented.invented_claiming_pmf(), max_table_year=2008
    )
    out = di_aware_claiming(
        frame, _context(2015, [1, 2, 3]), None, schedule=schedule
    ).set_index("person_id")
    assert pd.isna(out.at[1, "claim_age"]) and not out.at[1, "claimed"]
    assert not pd.isna(out.at[2, "claim_age"])
    assert out.at[3, "claimed"] and out.at[3, "claim_year"] == 2015
    assert pd.isna(out.at[3, "claim_age"])


def test_claiming_schedule_keeps_only_rows_at_or_before_the_cap():
    pmf = invented.invented_claiming_pmf()
    pmf[("male", 2012)] = {70: 1.0}
    schedule = claiming_schedule(pmf, max_table_year=2008)
    assert max(year for _, year in schedule.pmf) == 2008
    ages, _ = schedule.distribution("male", 2025)
    assert 62 in ages


def test_year_aware_mortality_scales_by_year_and_group():
    model = Tr2008YearAwareMortality(
        qx_by_sex={
            "female": np.full(MAX_AGE + 1, 0.01),
            "male": np.full(MAX_AGE + 1, 0.02),
        },
        ratio_by_year={2020: (0.5, 0.8)},
        alternative="INVENTED",
        base_year=2004,
    )
    frame = pd.DataFrame({"age": [40, 64, 65, 90], "sex": ["male"] * 4})
    values = model(frame, _context(2020, [1]))
    assert np.allclose(values, [0.01, 0.01, 0.016, 0.016])
    assert not hasattr(model, "probabilities")
    with pytest.raises(KeyError):
        model.probabilities_for_year(frame, 2021)


# --------------------------------------------------------------------------
# The end-to-end run
# --------------------------------------------------------------------------
def test_run_labels_every_output_invented(result):
    assert result["data_provenance"] == "invented"
    assert result["labels"][0] == INVENTED_COHORT_LABEL
    assert "PSID-seeded closed cohort" not in result["labels"]
    for row in result["rows"].values():
        assert row["status"] == "tabulated", row["status"]
        labels = row["tabulation"]["labels"]
        assert labels[0] == INVENTED_DATA_LABEL
        assert "Python oracle (not Axiom)" in labels
        assert "fixed-path mechanical incidence" in labels
    assert result["scheduled_entrants"] == 0
    assert result["rows_not_built"] == {}
    assert set(result["rows"]) == {f"R{i}" for i in range(7)}


def test_every_group_is_populated_in_every_draw(result):
    for group in result["rows"]["R0"]["tabulation"]["groups"]:
        assert len(group["cells"]) == len(CONFIG.draw_indices)
        assert all(cell["n_base"] > 0 for cell in group["cells"])


def test_di_stock_flow_reconciles_every_draw(result):
    assert set(result["draws"]) == {"2011", "2009"}
    for wave, first in (("2011", 2011), ("2009", 2009)):
        for diagnostics in result["draws"][wave].values():
            flows = diagnostics["di_stock_flow"]
            assert [row["year"] for row in flows] == list(range(first, 2031))


def test_reduced_counts_match_the_clock_arithmetic(result):
    counts = {
        row_id: result["rows"][row_id]["reduced_increases_by_age_group"]
        for row_id in ("R0", "R1", "R4")
    }
    # A clock that started by 2009 carries 21 reduced increases in 2030
    # payments under R0, 20 under R1 and 22 in the December 2030 amount.
    assert counts["R0"]["80+"]["max"] == 21
    assert counts["R1"]["80+"]["max"] == 20
    assert counts["R4"]["80+"]["max"] == 22
    for row_id in ("R0", "R1", "R4"):
        for group in counts[row_id].values():
            assert group["max"] <= 22


def test_baseline_amounts_are_shared_by_rows_with_the_same_period(result):
    # Fixed paths: rows that change only the reform, the clock or the
    # statistic see the same members and the same baseline means.
    for row_id in ("R1", "R2", "R3"):
        for left, right in zip(
            result["rows"]["R0"]["tabulation"]["groups"],
            result["rows"][row_id]["tabulation"]["groups"],
            strict=True,
        ):
            for a, b in zip(left["cells"], right["cells"], strict=True):
                assert a["n_base"] == b["n_base"]
                assert a["mean_benefit_base"] == pytest.approx(
                    b["mean_benefit_base"]
                )


def test_projection_is_reproducible_by_draw(cohort):
    config = TrackAConfig(draw_indices=(1,), rows=("R0",))
    first = run_track_a(_inputs(cohort), config=config)
    second = run_track_a(_inputs(cohort), config=config)
    assert first["draws"] == second["draws"]
    assert first["rows"]["R0"]["tabulation"]["groups"] == (
        second["rows"]["R0"]["tabulation"]["groups"]
    )


def test_registered_real_cohort_needs_the_registration_pointer(cohort):
    real = replace(cohort, data_provenance="registered_real")
    real_2009 = replace(_cohort_2009(), data_provenance="registered_real")
    with pytest.raises(ValueError, match="registration"):
        run_track_a(
            _inputs(real, additional_cohorts=(real_2009,)), config=CONFIG
        )


def test_populations_must_share_one_kind_of_data(cohort):
    real_2009 = replace(_cohort_2009(), data_provenance="registered_real")
    with pytest.raises(ValueError, match="one kind of data"):
        run_track_a(_inputs(cohort, additional_cohorts=(real_2009,)))


def test_r6_needs_the_2009_wave_cohort(cohort):
    with pytest.raises(ValueError, match=r"\['R6'\] \(anchor wave 2009\)"):
        run_track_a(_inputs(cohort, additional_cohorts=()), config=CONFIG)
    # Without R6 the 2011 cohort alone runs.
    config = TrackAConfig(draw_indices=(0,), rows=("R0",))
    alone = run_track_a(_inputs(cohort, additional_cohorts=()), config=config)
    assert set(alone["draws"]) == {"2011"}
    with pytest.raises(ValueError, match="two cohorts"):
        run_track_a(
            _inputs(cohort, additional_cohorts=(cohort,)), config=config
        )


@pytest.mark.parametrize(
    "change",
    [
        {"claim_class": "hold_for_track_b_m6_forward"},
        {"oracle_cola_horizon_extension_to_2030": False},
        {"acceptance_rule": "within 1 point"},
    ],
)
def test_unratified_alternatives_refuse_to_run(cohort, change):
    with pytest.raises(ValueError):
        run_track_a(_inputs(cohort), config=replace(CONFIG, **change))


def test_nonpositive_reduced_rate_fails_closed(cohort):
    low = COLASeries(
        by_determination_year={year: 0.005 for year in range(1979, 2032)},
        provenance={"invented": True},
    )
    with pytest.raises(ValueError, match="positive"):
        run_track_a(_inputs(cohort, baseline=low), config=CONFIG)


def test_excluded_di_level_drops_projected_awards(cohort):
    config = TrackAConfig(
        draw_indices=(0,),
        rows=("R0",),
        di_benefit_level=LevelPolicy.EXCLUDE,
    )
    excluded = run_track_a(_inputs(cohort), config=config)
    counters = excluded["rows"]["R0"]["benefit_counters"]
    assert counters.get("level_excluded_di", 0) > 0


def test_registered_rows_match_the_a1_block():
    block = a1_parameter_block()
    rows = block["rows"]
    assert set(rows) == set(REGISTERED_ROWS)
    for row_id, row in REGISTERED_ROWS.items():
        expected = {**rows["R0"], **rows[row_id]}
        assert expected["first_reduced_determination_year"] == (
            row.first_reduced_determination_year
        )
        assert expected["exposure_clock"] == row.exposure_clock.value
        assert list(expected["components"]) == list(row.components)
        assert expected.get("last_determination_year", 2029) == (
            sb.payment_year_for_reference(2030, row.benefit_period) - 1
        )
        assert expected["population"] == row.population.as_dict(2030)
    assert block["decisions"]["di_benefit_level"]["ruling"] == (
        TrackAConfig().di_benefit_level.value
    )


def test_max_rulings_are_the_a1_block_rulings():
    block = dict(a1_parameter_block()["decisions"])
    assert (block.pop("ruled_by"), block.pop("ruled_on")) == (
        "Max",
        "2026-09-23",
    )
    rulings = {item["field"]: item for item in max_rulings()}
    assert set(rulings) == set(MAX_RULINGS)
    # Referee question 10 (the page-3 contact) has no assembly field.
    assert set(block) - set(rulings) == {"page_3_run_metadata_contact"}
    for name, item in rulings.items():
        assert item["follows_ruling"] is True, name
        assert item["value"] == item["ruling"] == block[name]["ruling"]
        assert item["decision_record"] == block[name]["decision_record"]
        assert [str(v) for v in item["declined"]] == [
            str(v) for v in block[name]["declined"]
        ]
        assert item["ruled_by"].startswith("Max, 2026-09-23")
    assert rulings_departures(TrackAConfig()) == []


def test_builder_defaults_are_kept_apart_from_max_rulings():
    defaults = builder_defaults()
    fields = {item["field"] for item in defaults}
    assert not fields & set(MAX_RULINGS)
    assert fields == {
        "preeligibility_death_level",
        "auxiliary_entitlement_clock",
        "survivor_entitlement_rule",
        "spouse_entitlement_rule",
        "opening_aged_widow_min_age",
        "mortality_base_year",
        "claim_table_max_year",
        "wage_base_2009_2010",
    }
    for item in defaults:
        assert "awaiting" not in item
        assert "A1 ratification" in item["fixed_by"]
        assert "issue #42 registration" in item["fixed_by"]


def test_a_registered_run_refuses_a_departure_from_a_ruling(cohort):
    config = TrackAConfig(
        draw_indices=(0,),
        rows=("R0",),
        di_benefit_level=LevelPolicy.EXCLUDE,
    )
    assert rulings_departures(config) == ["di_benefit_level"]
    real = replace(cohort, data_provenance="registered_real")
    with pytest.raises(ValueError, match="departs from Max's rulings"):
        run_track_a(
            _inputs(real, additional_cohorts=()),
            config=config,
            registration_pointer="INVENTED-POINTER",
        )
    with pytest.raises(ValueError, match="fixed_at_opening_year"):
        TrackAConfig(opening_stock_basis="rebased_on_later_simulated_events")


def test_rows_split_the_floor_by_the_opening_wave_family_unit(
    result, cohort, a3_cohort
):
    a3 = a3_cohort.persons.set_index("person_id")
    persons = cohort.persons.set_index("person_id")
    assert (
        persons["family_unit_id"] == a3.loc[persons.index, "interview_2011"]
    ).all()
    # The invented cohort has family units of several members.
    assert persons.groupby("family_unit_id").size().max() > 1
    for row_id, row in result["rows"].items():
        tabulation = row["tabulation"]
        population = row["row"]["population"]
        assert population["family_unit_id"] == (
            "ER34001" if row_id == "R6" else "ER34101"
        )
        assert tabulation["upstream_conventions"]["family_unit_id"] == (
            population["family_unit_id"]
        )
        assert tabulation["config"]["floor_split_unit"] == "family_unit_id"
        total = tabulation["input_summary"]["n_family_units"]
        for seed in tabulation["floor_per_seed"]:
            assert seed["split_unit"] == "family_unit_id"
            # No family unit lies on both sides.
            assert (
                seed["side_a"]["n_family_units"]
                + seed["side_b"]["n_family_units"]
                == total
            )


def test_r6_projects_the_2009_wave_from_2008(result):
    r6 = result["rows"]["R6"]
    assert r6["status"] == "tabulated"
    assert r6["row"]["population"] == {
        "wave": 2009,
        "weight": "ER34046",
        "born_max": 1980,
        "start_year": 2008,
        "periods": 22,
        "family_unit_id": "ER34001",
    }
    upstream = r6["tabulation"]["upstream_conventions"]
    assert upstream["population_start_year"] == 2008
    assert upstream["population_periods"] == 22
    assert result["cohorts"]["2009"]["start_year"] == 2008
    assert result["cohorts"]["2009"]["source_provenance"]["kind"] == (
        psid2010.INVENTED
    )
    # Every other row reads the 2011 wave.
    for row_id in ("R0", "R1", "R2", "R3", "R4", "R5"):
        assert result["rows"][row_id]["row"]["population"]["wave"] == 2011


def test_an_undefined_cell_is_reported_and_the_row_kept(cohort, monkeypatch):
    # INVENTED age bands: the open 80+ band is split at 110, and nobody in
    # the invented cohort is 110 or older in 2030, so that cell is
    # undefined in every draw (A1 section 7); the row still tabulates and
    # every other cell keeps its value.
    from populace_dynamics.cola_track_a import runner as runner_module
    from populace_dynamics.estimates import cola_age_profile as cap

    groups = (
        *cap.DEFAULT_AGE_GROUPS[:-1],
        cap.AgeGroup("80-109", 80, 109),
        cap.AgeGroup("110+", 110),
    )

    def with_groups(**kwargs):
        return cap.ColaAgeProfileConfig(age_groups=groups, **kwargs)

    monkeypatch.setattr(runner_module, "ColaAgeProfileConfig", with_groups)
    config = TrackAConfig(draw_indices=(0, 1), rows=("R0",))
    run = run_track_a(_inputs(cohort, additional_cohorts=()), config=config)
    row = run["rows"]["R0"]
    assert row["status"].startswith("tabulated with undefined cells: ")
    assert "110+ ratio_of_scenario_means (0 of 2 draws defined)" in (
        row["status"]
    )
    tabulation = row["tabulation"]
    by_label = {group["label"]: group for group in tabulation["groups"]}
    old = by_label["110+"]["ratio_of_scenario_means"]
    assert old["defined"] is False and old["mean"] is None
    assert old["undefined_draws"] == [
        {"draw": 0, "reason": "empty_baseline_membership"},
        {"draw": 1, "reason": "empty_baseline_membership"},
    ]
    for label in ("50-61", "62-64", "65-69", "70-79", "80-109"):
        kept = by_label[label]["ratio_of_scenario_means"]
        assert kept["defined"] is True
        assert kept["mean"] is not None
    assert {cell["group"] for cell in tabulation["undefined_cells"]} == {
        "110+"
    }


# --------------------------------------------------------------------------
# Arithmetic against A6
# --------------------------------------------------------------------------
@pytest.mark.parametrize("clock_year", [1995, 2004, 2009, 2010])
@pytest.mark.parametrize("exposure", [None, 2006, 2010])
@pytest.mark.parametrize("round_to_dime", [False, True])
def test_opening_stock_amounts_equal_the_a6_function(
    clock_year, exposure, round_to_dime
):
    baseline = invented_cola()
    reform = sb.COLAReform()
    entitlement = max(clock_year, exposure or clock_year)
    record = OpeningStockRecord(
        person_id=1,
        status="retired_worker",
        component="retired_worker",
        observed_annual_amount=15_432.0,
        clock_year=clock_year,
        clock_rule="INVENTED",
        entitlement_year=entitlement,
        entitlement_clamped=False,
    )
    clock = sb.WorkerClock(
        basis=sb.EligibilityBasis.AGE_62,
        eligibility_year=clock_year,
        entitlement_year=entitlement,
    )
    exposure_clock = (
        sb.ExposureClock.ELIGIBILITY
        if exposure is None
        else sb.ExposureClock.ENTITLEMENT
    )
    a6 = sb.opening_stock_scenario_paths(
        observed_monthly_amount=15_432.0 / 12,
        clock=clock,
        baseline=baseline,
        reform=reform,
        exposure_clock=exposure_clock,
        horizon_year=2030,
        round_to_dime=round_to_dime,
    )
    ours = track_benefits.opening_stock_amounts(
        record,
        baseline=baseline,
        reform=reform,
        exposure_start_year=clock.exposure_start_year(exposure_clock),
        observed_payment_year=2010,
        payment_year=2030,
        round_to_dime=round_to_dime,
    )
    assert ours == (
        a6.baseline_monthly_by_payment_year[2030],
        a6.reform_monthly_by_payment_year[2030],
    )


def test_r6_opening_amount_carries_forward_from_2008():
    # A1 section 11 rule 4 with opening year 2008 (R6): the 2008 amount
    # already carries the determination-year-2007 increase, so the level
    # product starts at 2008; the reduced increases are 2009-2029.
    baseline = invented_cola()
    record = OpeningStockRecord(
        person_id=1,
        status="retired_worker",
        component="retired_worker",
        observed_annual_amount=9_600.0,
        clock_year=2004,
        clock_rule="INVENTED",
        entitlement_year=2006,
        entitlement_clamped=False,
    )
    base, reform = track_benefits.opening_stock_amounts(
        record,
        baseline=baseline,
        reform=sb.COLAReform(),
        exposure_start_year=2004,
        observed_payment_year=2008,
        payment_year=2030,
        round_to_dime=False,
    )
    assert base == pytest.approx(
        800.0 * math.prod(1 + baseline[y] for y in range(2008, 2030)),
        rel=1e-12,
    )
    product = math.prod(
        (1 + baseline[year] - 0.01) / (1 + baseline[year])
        for year in range(2009, 2030)
    )
    assert reform / base == pytest.approx(product, rel=1e-12)


def test_unrounded_opening_ratio_is_the_reduced_increase_product():
    baseline = invented_cola()
    record = OpeningStockRecord(
        person_id=1,
        status="survivor",
        component="aged_widow",
        observed_annual_amount=9_000.0,
        clock_year=2003,
        clock_rule="INVENTED",
        entitlement_year=2003,
        entitlement_clamped=False,
    )
    base, reform = track_benefits.opening_stock_amounts(
        record,
        baseline=baseline,
        reform=sb.COLAReform(),
        exposure_start_year=2003,
        observed_payment_year=2010,
        payment_year=2030,
        round_to_dime=False,
    )
    product = math.prod(
        (1 + baseline[year] - 0.01) / (1 + baseline[year])
        for year in range(2009, 2030)
    )
    assert reform / base == pytest.approx(product, rel=1e-12)
    assert base == pytest.approx(
        750.0 * math.prod(1 + baseline[y] for y in range(2010, 2030)),
        rel=1e-12,
    )


def _handmade_cohort(persons, careers, final_rows, last_rows):
    """INVENTED two-slice projection for the auxiliary composition tests."""
    static = pd.DataFrame(persons)
    for column in (
        "opening_claim_year",
        "opening_claim_year_upper_bound",
        "opening_claim_age",
        "spouse_person_id",
        "late_spouse_person_id",
        "late_spouse_death_year",
        "widowhood_year",
        "linked_spouse_birth_year",
    ):
        static[column] = pd.array([pd.NA] * len(static), dtype="Int64")
    static["ss_receipt_opening"] = pd.array([False] * len(static), "boolean")
    initial = pd.DataFrame(last_rows)
    cohort = TrackACohort(
        persons=static,
        careers=careers,
        initial_slice=initial,
        opening={},
        data_provenance="invented",
        labels=(INVENTED_COHORT_LABEL,),
        diagnostics={},
    )
    result = ProjectionResult(
        slices=(initial, pd.DataFrame(final_rows)),
        traces=(),
        draw_index=0,
    )
    return cohort, result


def _state(person_id, birth, year, **values):
    row = {
        "person_id": person_id,
        "year": year,
        "age": year - birth,
        "sex": "female",
        "birth_year": birth,
        "weight": 1_000.0,
        "di_entitled": False,
        "di_award_year": pd.NA,
        "di_conversion_year": pd.NA,
        "di_recovery_year": pd.NA,
        "claimed": False,
        "claim_age": pd.NA,
        "claim_year": pd.NA,
        "marital_status": "married",
        "spouse_person_id": pd.NA,
        "widowhood_year": pd.NA,
        "late_spouse_person_id": pd.NA,
        "widowed_in_projection": False,
    }
    row.update(values)
    return row


def _career(level: float, birth: int) -> dict[int, float]:
    return {year: level for year in range(birth + 22, 2011)}


def _static(person_id, birth):
    return {
        "person_id": person_id,
        "family_unit_id": 1,
        "weight": 1_000.0,
        "sex": "female",
        "birth_year": birth,
        "age_opening": 2010 - birth,
        "opening_status": "none",
        "ss_opening": 0,
        "marital_status_opening": "married",
    }


def test_spouse_excess_equals_the_a6_composition():
    # INVENTED couple: 1 (born 1962, low earner) claims 2026; worker 2
    # (born 1960) claimed 2024.
    persons = [_static(1, 1962), _static(2, 1960)]
    careers = {1: _career(9_000.0, 1962), 2: _career(60_000.0, 1960)}
    final = [
        _state(
            1, 1962, 2030, claimed=True, claim_year=2026, spouse_person_id=2
        ),
        _state(
            2, 1960, 2030, claimed=True, claim_year=2024, spouse_person_id=1
        ),
    ]
    initial = [
        _state(1, 1962, 2010, spouse_person_id=2),
        _state(2, 1960, 2010, spouse_person_id=1),
    ]
    cohort, projection = _handmade_cohort(persons, careers, final, initial)
    params = invented_params()
    context = track_benefits.BenefitContext(
        cohort=cohort, params=params, baseline=invented_cola(), config=CONFIG
    )
    rows, _ = track_benefits.reference_benefit_rows(
        projection, draw=0, row=REGISTERED_ROWS["R0"], context=context
    )
    by_id = {row["person_id"]: row for row in rows}

    def pia(pid, birth):
        return sb.eligibility_pia_for_clock(
            sb.WorkerClock.at_age_62(birth),
            history=careers[pid],
            birth_year=birth,
            params=params,
        )

    own = sb.OwnBenefit(
        eligibility_pia=pia(1, 1962),
        claim_age_factor=claiming.benefit_factor(64 * 12, 1962, params),
        clock=sb.WorkerClock.at_age_62(1962, entitlement_year=2026),
    )
    spouse = sb.spouse_scenario_paths(
        worker_eligibility_pia=pia(2, 1960),
        worker_clock=sb.WorkerClock.at_age_62(1960, entitlement_year=2024),
        own=own,
        months_early=params.fra_months(1962) - 64 * 12,
        entitlement_year=2026,
        params=params,
        baseline=invented_cola(),
    )
    worker = sb.worker_scenario_paths(
        eligibility_pia=own.eligibility_pia,
        claim_age_factor=own.claim_age_factor,
        clock=own.clock,
        baseline=invented_cola(),
    )
    components = by_id[1]["benefit_components"]
    assert components["spouse"]["base"] == pytest.approx(
        12 * spouse.baseline_monthly_by_payment_year[2030]
    )
    assert components["spouse"]["reform"] == pytest.approx(
        12 * spouse.reform_monthly_by_payment_year[2030]
    )
    assert components["retired_worker"]["reform"] == pytest.approx(
        12 * worker.reform_monthly_by_payment_year[2030]
    )


def test_widow_benefit_equals_the_a6_composition():
    # INVENTED: worker 2 (born 1955) claimed 2019 and died in 2021;
    # widow 1 (born 1958) has no own claim.
    persons = [_static(1, 1958), _static(2, 1955)]
    careers = {1: _career(0.0, 1958), 2: _career(50_000.0, 1955)}
    last_worker = _state(
        2, 1955, 2020, claimed=True, claim_year=2019, spouse_person_id=1
    )
    final = [
        _state(
            1,
            1958,
            2030,
            marital_status="widowed",
            widowhood_year=2021,
            late_spouse_person_id=2,
            widowed_in_projection=True,
        )
    ]
    cohort, projection = _handmade_cohort(
        persons,
        careers,
        final,
        [_state(1, 1958, 2020, spouse_person_id=2), last_worker],
    )
    params = invented_params()
    context = track_benefits.BenefitContext(
        cohort=cohort, params=params, baseline=invented_cola(), config=CONFIG
    )
    rows, _ = track_benefits.reference_benefit_rows(
        projection, draw=0, row=REGISTERED_ROWS["R0"], context=context
    )
    (row,) = rows
    deceased_pia = sb.eligibility_pia_for_clock(
        sb.WorkerClock.at_age_62(1955),
        history=careers[2],
        birth_year=1955,
        params=params,
    )
    a6 = sb.widow_scenario_paths(
        deceased_eligibility_pia=deceased_pia,
        deceased_clock=sb.WorkerClock.at_age_62(1955, entitlement_year=2019),
        deceased_claim_age_factor=claiming.benefit_factor(
            64 * 12, 1955, params
        ),
        own=None,
        survivor_months_early=params.survivor_reduction_period_months
        - 12 * (2021 - 1958 - 60),
        entitlement_year=2021,
        params=params,
        baseline=invented_cola(),
    )
    assert row["benefit_components"]["aged_widow"]["base"] == pytest.approx(
        12 * a6.baseline_monthly_by_payment_year[2030]
    )
    assert row["benefit_components"]["aged_widow"]["reform"] == (
        pytest.approx(12 * a6.reform_monthly_by_payment_year[2030])
    )
    assert row["reduced_increases"] == 2029 - 2017 + 1


def test_widowhood_dated_before_the_roster_death_is_not_paid():
    # INVENTED disagreement: A3 dates 1's widowhood 2005, but the "late"
    # spouse 2 is in the opening roster and dies only in 2021.
    persons = [_static(1, 1950), _static(2, 1948)]
    careers = {1: _career(0.0, 1950), 2: _career(40_000.0, 1948)}
    final = [
        _state(
            1,
            1950,
            2030,
            marital_status="widowed",
            widowhood_year=2005,
            late_spouse_person_id=2,
        )
    ]
    cohort, projection = _handmade_cohort(
        persons,
        careers,
        final,
        [
            _state(1, 1950, 2020, marital_status="widowed"),
            _state(2, 1948, 2020, claimed=True, claim_year=2012),
        ],
    )
    context = track_benefits.BenefitContext(
        cohort=cohort,
        params=invented_params(),
        baseline=invented_cola(),
        config=CONFIG,
    )
    rows, counters = track_benefits.reference_benefit_rows(
        projection, draw=0, row=REGISTERED_ROWS["R0"], context=context
    )
    assert rows == []
    assert counters["widow_death_year_disagrees_with_roster"] == 1


def test_a_flat_population_mortality_is_recorded_as_a_gap(cohort):
    band_model = AgeSexMortalityModel(
        bands=((0, 64), (65, 120)),
        probability={
            ("0-64", "female"): 0.002,
            ("0-64", "male"): 0.003,
            ("65+", "female"): 0.03,
            ("65+", "male"): 0.04,
        },
    )
    config = TrackAConfig(draw_indices=(0,), rows=("R0",))
    flat = run_track_a(
        _inputs(cohort, population_mortality=band_model), config=config
    )
    assert flat["population_mortality"]["class"] == "AgeSexMortalityModel"
    assert flat["population_mortality"]["year_aware"] is False
    assert "no year axis" in flat["population_mortality"]["gap"]
    aware = run_track_a(_inputs(cohort), config=config)
    assert aware["population_mortality"]["year_aware"] is True


# --------------------------------------------------------------------------
# Review fixes (all INVENTED data)
# --------------------------------------------------------------------------
def test_approximate_pia_indexes_to_the_second_year_before_eligibility():
    params = invented_params()
    career = _career(40_000.0, 1970)
    # At the age-62 year the approximation is the oracle's retirement PIA.
    retirement = sb.eligibility_pia_for_clock(
        sb.WorkerClock.at_age_62(1970),
        history=career,
        birth_year=1970,
        params=params,
    )
    assert track_benefits.approximate_pia(
        career,
        birth_year=1970,
        computation_end_year=2032,
        eligibility_year=2032,
        params=params,
    ) == pytest.approx(retirement, abs=0.0)
    # An onset in 2015 (age 45) indexes to 2013, the second year before
    # the onset year whose bend points the PIA uses.
    kept = {year: value for year, value in career.items() if year <= 2015}
    assert benefits.indexed_history(kept, 2015 - 62, params)[2000] == (
        pytest.approx(40_000.0 * params.nawi[2013] / params.nawi[2000])
    )
    expected = benefits.pia(
        benefits.aime(kept, 2015 - 62, params), 2015, params
    )
    approximation = track_benefits.approximate_pia(
        career,
        birth_year=1970,
        computation_end_year=2015,
        eligibility_year=2015,
        params=params,
    )
    assert approximation == pytest.approx(expected, abs=0.0)
    # Indexing to age 60 (2030) against 2015 bend points overstated it.
    age_60_indexed = benefits.pia(
        benefits.aime(kept, 1970, params), 2015, params
    )
    assert age_60_indexed > approximation


def _di_state(person_id, birth, **values):
    return _state(
        person_id, birth, 2030, marital_status="never_married", **values
    )


def test_di_award_after_62_keeps_the_age_62_clock():
    # INVENTED: 1 (born 1954) claimed at 62 in 2016, was awarded DI in
    # 2019 and converted at FRA (66) in 2020.  2 (born 1960) was awarded
    # DI in 2015 at 55 and converted in 2026.
    persons = [_static(1, 1954), _static(2, 1960)]
    careers = {1: _career(45_000.0, 1954), 2: _career(30_000.0, 1960)}
    final = [
        _di_state(
            1,
            1954,
            claimed=True,
            claim_year=2016,
            di_award_year=2019,
            di_conversion_year=2020,
        ),
        _di_state(
            2,
            1960,
            claimed=True,
            claim_year=2026,
            di_award_year=2015,
            di_conversion_year=2026,
        ),
    ]
    initial = [
        _state(1, 1954, 2010, marital_status="never_married"),
        _state(2, 1960, 2010, marital_status="never_married"),
    ]
    cohort, projection = _handmade_cohort(persons, careers, final, initial)
    params = invented_params()
    context = track_benefits.BenefitContext(
        cohort=cohort, params=params, baseline=invented_cola(), config=CONFIG
    )
    by_row = {}
    for row_id in ("R0", "R2"):
        rows, _ = track_benefits.reference_benefit_rows(
            projection, draw=0, row=REGISTERED_ROWS[row_id], context=context
        )
        by_row[row_id] = {row["person_id"]: row for row in rows}
    # R0: the PIA runs from 2016 (age 62), not from the 2019 award.
    assert by_row["R0"][1]["reduced_increases"] == 2029 - 2016 + 1
    assert set(by_row["R0"][1]["benefit_components"]) == {"retired_worker"}
    level = track_benefits.approximate_pia(
        careers[1],
        birth_year=1954,
        computation_end_year=2016,
        eligibility_year=2016,
        params=params,
    )
    path = sb.monthly_benefit_path(
        eligibility_pia=level,
        claim_age_factor=1.0,
        eligibility_year=2016,
        cola=sb.ScenarioCOLARates(
            baseline=invented_cola(), reform=None, exposure_start_year=2016
        ),
        horizon_year=2030,
    )
    assert by_row["R0"][1]["benefit_base"] == pytest.approx(12 * path[2030])
    # R2 keeps the award year as the entitlement year.
    assert by_row["R2"][1]["reduced_increases"] == 2029 - 2019 + 1
    # An award before 62 keeps the award clock under both rows.
    assert by_row["R0"][2]["reduced_increases"] == 2029 - 2015 + 1
    assert by_row["R2"][2]["reduced_increases"] == 2029 - 2015 + 1


def test_converted_opening_disabled_worker_is_reported_as_retired_worker():
    # INVENTED opening disabled workers: 1 (born 1950) converted at FRA in
    # 2016; 2 (born 1975) is still entitled in 2030.
    persons = [_static(1, 1950), _static(2, 1975)]
    careers = {1: _career(0.0, 1950), 2: _career(0.0, 1975)}
    final = [
        _di_state(
            1,
            1950,
            claimed=True,
            claim_year=2016,
            di_award_year=2004,
            di_conversion_year=2016,
        ),
        _di_state(2, 1975, di_entitled=True, di_award_year=2006),
    ]
    initial = [
        _state(1, 1950, 2010, marital_status="never_married"),
        _state(2, 1975, 2010, marital_status="never_married"),
    ]
    cohort, projection = _handmade_cohort(persons, careers, final, initial)
    cohort.persons["opening_status"] = "disabled_worker"
    cohort.persons["ss_receipt_opening"] = pd.array([True, True], "boolean")
    opening = {
        pid: OpeningStockRecord(
            person_id=pid,
            status="disabled_worker",
            component="disabled_worker",
            observed_annual_amount=12_000.0,
            clock_year=clock,
            clock_rule="a3_receipt_start",
            entitlement_year=clock,
            entitlement_clamped=False,
        )
        for pid, clock in ((1, 2004), (2, 2006))
    }
    cohort = replace(cohort, opening=opening)
    context = track_benefits.BenefitContext(
        cohort=cohort,
        params=invented_params(),
        baseline=invented_cola(),
        config=CONFIG,
    )
    rows, counters = track_benefits.reference_benefit_rows(
        projection, draw=0, row=REGISTERED_ROWS["R0"], context=context
    )
    by_id = {row["person_id"]: row for row in rows}
    assert counters["beneficiaries_opening_stock"] == 2
    assert set(by_id[1]["benefit_components"]) == {"retired_worker"}
    assert set(by_id[2]["benefit_components"]) == {"disabled_worker"}
    expected = track_benefits.opening_stock_amounts(
        opening[1],
        baseline=invented_cola(),
        reform=sb.COLAReform(),
        exposure_start_year=2004,
        observed_payment_year=2010,
        payment_year=2030,
        round_to_dime=False,
    )
    assert by_id[1]["benefit_base"] == pytest.approx(12 * expected[0])
    assert by_id[1]["benefit_reform"] == pytest.approx(12 * expected[1])
    assert by_id[1]["reduced_increases"] == 21


def test_opening_disabled_worker_receiving_after_62_keeps_the_age_62_clock():
    # INVENTED row shapes: a non-default A3 spec can classify a 64-year-old
    # first observed receiving in 2010 as a disabled worker.
    config = TrackAConfig(draw_indices=(0,))

    def row(age, receipt):
        return SimpleNamespace(
            person_id=1,
            opening_status="disabled_worker",
            age_opening=age,
            birth_year=2010 - age,
            opening_claim_year=receipt,
            opening_claim_year_upper_bound=2010,
            ss_opening=9_000,
            linked_spouse_birth_year=pd.NA,
        )

    aged, _ = opening_module._opening_record(row(64, 2010), config, 2010)
    assert (aged.clock_year, aged.clock_rule) == (
        1946 + 62,
        "own_birth_plus_62_di",
    )
    assert aged.entitlement_year == 2010
    young, _ = opening_module._opening_record(row(50, 2010), config, 2010)
    assert (young.clock_year, young.clock_rule) == (2010, "a3_receipt_start")


def test_parameter_consistency_is_recorded(result):
    record = result["parameter_consistency"]
    # Unit tests use invented parameters and never read the TR2008 capture.
    assert record["committed_values_compared"] is False
    checks = record["checks"]
    assert set(checks) == {"di_spec", "mortality", "claim_table_max_year"}
    assert checks["di_spec"]["consistent"] is True
    assert checks["claim_table_max_year"]["consistent"] is True
    # The invented mortality model is labelled INVENTED, not intermediate.
    assert checks["mortality"]["consistent"] is False
    assert record["consistent"] is False


def test_mismatched_di_spec_is_recorded(cohort):
    config = TrackAConfig(
        draw_indices=(0,),
        rows=("R0",),
        di_spec=DIEntitlementSpec(post_conversion_mortality="population"),
    )
    run = run_track_a(_inputs(cohort), config=config)
    check = run["parameter_consistency"]["checks"]["di_spec"]
    assert check["consistent"] is False
    assert check["runtime"]["post_conversion_mortality"] == "di_origin"


def test_component_shares_are_weighted_baseline_amount_shares(result):
    # INVENTED rows: draw 0 has a retired worker (weight 2, $10,000) and a
    # widow with $6,000 own and $4,000 widow's excess (weight 1), both 70.
    rows = [
        {
            "draw": 0,
            "age_reference": 70,
            "weight": 2.0,
            "benefit_components": {
                "retired_worker": {"base": 10_000.0, "reform": 1.0}
            },
        },
        {
            "draw": 0,
            "age_reference": 70,
            "weight": 1.0,
            "benefit_components": {
                "retired_worker": {"base": 6_000.0, "reform": 1.0},
                "aged_widow": {"base": 4_000.0, "reform": 1.0},
            },
        },
    ]
    shares = _component_shares(rows, ("retired_worker", "aged_widow"), (0,))
    cell = shares["by_group"]["70-79"]
    assert cell["draws_defined"] == 1
    assert cell["mean_share"] == pytest.approx(
        {"retired_worker": 26_000 / 30_000, "aged_widow": 4_000 / 30_000}
    )
    assert shares["by_group"]["50-61"] == {
        "draws_defined": 0,
        "mean_share": None,
    }
    for row_id, row in result["rows"].items():
        for cell in row["component_shares_by_age_group"]["by_group"].values():
            if cell["mean_share"] is None:
                continue
            assert set(cell["mean_share"]) == set(
                REGISTERED_ROWS[row_id].components
            )
            assert sum(cell["mean_share"].values()) == pytest.approx(1.0)


def test_opening_disabled_widow_is_an_aged_widow_from_60():
    # INVENTED opening survivors labelled disabled widow(er)s in 2010:
    # 1 (born 1955) is 75 in 2030; 2 (born 1975) is 55.
    persons = [_static(1, 1955), _static(2, 1975)]
    careers = {1: _career(0.0, 1955), 2: _career(0.0, 1975)}
    final = [
        _state(1, 1955, 2030, marital_status="widowed", claimed=True),
        _state(2, 1975, 2030, marital_status="widowed", claimed=True),
    ]
    initial = [
        _state(1, 1955, 2010, marital_status="widowed", claimed=True),
        _state(2, 1975, 2010, marital_status="widowed", claimed=True),
    ]
    cohort, projection = _handmade_cohort(persons, careers, final, initial)
    cohort.persons["opening_status"] = "survivor"
    cohort.persons["ss_receipt_opening"] = pd.array([True, True], "boolean")
    opening = {
        pid: OpeningStockRecord(
            person_id=pid,
            status="survivor",
            component="disabled_widow",
            observed_annual_amount=8_000.0,
            clock_year=2007,
            clock_rule="a3_receipt_start",
            entitlement_year=2007,
            entitlement_clamped=False,
        )
        for pid in (1, 2)
    }
    cohort = replace(cohort, opening=opening)
    context = track_benefits.BenefitContext(
        cohort=cohort,
        params=invented_params(),
        baseline=invented_cola(),
        config=CONFIG,
    )
    rows, _ = track_benefits.reference_benefit_rows(
        projection, draw=0, row=REGISTERED_ROWS["R0"], context=context
    )
    by_id = {row["person_id"]: row for row in rows}
    assert set(by_id[1]["benefit_components"]) == {"aged_widow"}
    assert set(by_id[2]["benefit_components"]) == {"disabled_widow"}
    assert by_id[1]["benefit_base"] == pytest.approx(by_id[2]["benefit_base"])
    assert by_id[1]["reduced_increases"] == 21


def test_converted_disabled_worker_spouse_excess_starts_at_own_claim():
    # INVENTED couple.  1 (born 1960, low earner) was awarded DI in 2014
    # at 54 and converted at FRA (67) in 2027, which the claiming step
    # records as 1's claim.  Worker 2 (born 1956) claimed in 2019, when 1
    # was 59.  The spouse's excess starts at the later of 1's own claim
    # (2027) and 2's entitlement (2019); the DI award is not a claim.
    persons = [_static(1, 1960), _static(2, 1956)]
    careers = {1: _career(8_000.0, 1960), 2: _career(60_000.0, 1956)}
    final = [
        _state(
            1,
            1960,
            2030,
            claimed=True,
            claim_year=2027,
            di_award_year=2014,
            di_conversion_year=2027,
            spouse_person_id=2,
        ),
        _state(
            2, 1956, 2030, claimed=True, claim_year=2019, spouse_person_id=1
        ),
    ]
    initial = [
        _state(1, 1960, 2010, spouse_person_id=2),
        _state(2, 1956, 2010, spouse_person_id=1),
    ]
    cohort, projection = _handmade_cohort(persons, careers, final, initial)
    params = invented_params()
    context = track_benefits.BenefitContext(
        cohort=cohort, params=params, baseline=invented_cola(), config=CONFIG
    )
    rows, counters = track_benefits.reference_benefit_rows(
        projection, draw=0, row=REGISTERED_ROWS["R0"], context=context
    )
    by_id = {row["person_id"]: row for row in rows}
    components = by_id[1]["benefit_components"]
    assert set(components) == {"retired_worker", "spouse"}
    assert counters["spouse_excess_paid"] == 1
    own_level = track_benefits.approximate_pia(
        careers[1],
        birth_year=1960,
        computation_end_year=2014,
        eligibility_year=2014,
        params=params,
    )
    worker_level = sb.eligibility_pia_for_clock(
        sb.WorkerClock.at_age_62(1956),
        history=careers[2],
        birth_year=1956,
        params=params,
    )
    spouse = sb.spouse_scenario_paths(
        worker_eligibility_pia=worker_level,
        worker_clock=sb.WorkerClock.at_age_62(1956, entitlement_year=2019),
        own=sb.OwnBenefit(
            eligibility_pia=own_level,
            claim_age_factor=1.0,
            clock=sb.WorkerClock.at_di_onset(2014, entitlement_year=2014),
        ),
        months_early=max(0, params.fra_months(1960) - 12 * (2027 - 1960)),
        entitlement_year=2027,
        params=params,
        baseline=invented_cola(),
    )
    assert spouse.baseline_monthly_by_payment_year[2030] > 0
    assert components["spouse"]["base"] == pytest.approx(
        12 * spouse.baseline_monthly_by_payment_year[2030]
    )
    assert components["spouse"]["reform"] == pytest.approx(
        12 * spouse.reform_monthly_by_payment_year[2030]
    )


def test_excluded_di_level_leaves_r3_as_documented(cohort):
    # The LevelPolicy docstring: an excluded own level drops the person
    # from every row, R3 included (A1 section 22 differs; recorded).
    config = TrackAConfig(
        draw_indices=(0,),
        rows=("R0", "R3"),
        di_benefit_level=LevelPolicy.EXCLUDE,
    )
    run = run_track_a(_inputs(cohort), config=config)
    dropped = {
        row_id: run["rows"][row_id]["benefit_counters"].get(
            "person_excluded_own_level_unavailable", 0
        )
        for row_id in ("R0", "R3")
    }
    assert dropped["R0"] > 0
    assert dropped["R3"] == dropped["R0"]
    (entry,) = [
        item
        for item in run["max_rulings"]
        if item["field"] == "di_benefit_level"
    ]
    assert "R3" in entry["note"]
    assert entry["ruling"] == "disclosed_oracle_approximation"
    assert entry["follows_ruling"] is False


def test_reduced_increase_summary_counts_the_rows_members(result):
    # A7 keeps a person in R5 only with a positive worker benefit; the
    # summary must count the same persons (it counted widow(er)s and
    # other auxiliary-only persons under R5 before the fix).
    fewer = False
    for row_id, row in result["rows"].items():
        members = {
            group["label"]: sum(cell["n_base"] for cell in group["cells"])
            for group in row["tabulation"]["groups"]
        }
        summary = row["reduced_increases_by_age_group"]
        assert {
            label: summary[label]["rows"] for label in members
        } == members, row_id
        if row_id == "R5":
            r0 = result["rows"]["R0"]["reduced_increases_by_age_group"]
            fewer = any(
                summary[label]["rows"] < r0[label]["rows"] for label in members
            )
    assert (
        fewer
    ), "the invented cohort should put auxiliary-only persons outside R5"


def test_repeated_rows_are_refused():
    with pytest.raises(ValueError, match="unique"):
        TrackAConfig(rows=("R0", "R0"))
    with pytest.raises(ValueError, match="unique"):
        TrackAConfig(rows=())


def test_result_records_the_statutory_parameter_revision(result):
    assert result["ssa_parameters_revision"] == "INVENTED"


def test_dry_run_records_the_date_it_ran():
    import datetime
    import importlib.util
    from pathlib import Path

    path = (
        Path(__file__).resolve().parents[2] / "scripts" / "track_a_dry_run.py"
    )
    spec = importlib.util.spec_from_file_location("track_a_dry_run", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.run_date() == datetime.date.today().isoformat()
    items = [gap["item"] for gap in module.GAPS]
    assert "Insured status" in items


def _claimant_rows(persons, careers, final, initial):
    cohort, projection = _handmade_cohort(persons, careers, final, initial)
    context = track_benefits.BenefitContext(
        cohort=cohort,
        params=invented_params(),
        baseline=invented_cola(),
        config=CONFIG,
    )
    return cohort, projection, context


def test_spouses_the_run_cannot_assess_are_counted():
    # INVENTED: claimant 1's linked spouse (999) is outside the opening
    # roster and claimant 3 has no linked spouse, so neither can draw a
    # spouse's excess.  Both were dropped without a count before the fix.
    persons = [_static(1, 1955), _static(3, 1956)]
    careers = {1: _career(9_000.0, 1955), 3: _career(9_000.0, 1956)}
    final = [
        _state(
            1, 1955, 2030, claimed=True, claim_year=2020, spouse_person_id=999
        ),
        _state(3, 1956, 2030, claimed=True, claim_year=2021),
    ]
    initial = [
        _state(1, 1955, 2010, spouse_person_id=999),
        _state(3, 1956, 2010),
    ]
    _, projection, context = _claimant_rows(persons, careers, final, initial)
    rows, counters = track_benefits.reference_benefit_rows(
        projection, draw=0, row=REGISTERED_ROWS["R0"], context=context
    )
    assert counters["spouse_outside_roster"] == 1
    assert counters["spouse_unlinked"] == 1
    assert counters["spouse_rostered_but_absent"] == 0
    assert all(
        set(row["benefit_components"]) == {"retired_worker"} for row in rows
    )


def test_beneficiaries_with_unobserved_2010_social_security_are_counted():
    # INVENTED: person 1's 2010 Social Security is unobserved (A3 status
    # "unobserved"), so the opening state has no record and the benefit
    # is projected; the count names how many such beneficiaries enter.
    persons = [_static(1, 1950), _static(2, 1952)]
    careers = {1: _career(30_000.0, 1950), 2: _career(30_000.0, 1952)}
    final = [
        _state(
            1,
            1950,
            2030,
            claimed=True,
            claim_year=2012,
            marital_status="never_married",
        ),
        _state(
            2,
            1952,
            2030,
            claimed=True,
            claim_year=2014,
            marital_status="never_married",
        ),
    ]
    initial = [
        _state(1, 1950, 2010, marital_status="never_married"),
        _state(2, 1952, 2010, marital_status="never_married"),
    ]
    cohort, projection, context = _claimant_rows(
        persons, careers, final, initial
    )
    cohort.persons["ss_receipt_opening"] = pd.array([pd.NA, False], "boolean")
    rows, counters = track_benefits.reference_benefit_rows(
        projection, draw=0, row=REGISTERED_ROWS["R0"], context=context
    )
    assert {row["person_id"] for row in rows} == {1, 2}
    assert counters["beneficiaries_ss_opening_year_unobserved"] == 1
    assert counters["opening_recipient_without_record"] == 0


def test_rows_define_the_reduced_increase_diagnostic(result):
    for row in result["rows"].values():
        definition = row["reduced_increases_definition"]
        assert "dually entitled" in definition
        assert "own worker benefit" in definition


def test_dry_run_names_unassessed_spouses_unobserved_ss_and_refusals():
    import importlib.util
    from pathlib import Path

    path = (
        Path(__file__).resolve().parents[2] / "scripts" / "track_a_dry_run.py"
    )
    spec = importlib.util.spec_from_file_location("track_a_dry_run", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    gaps = {gap["item"]: gap["gap"] for gap in module.GAPS}
    assert "no spouse's benefit" in (
        gaps["Linked spouses outside the opening roster"]
    )
    assert "spouse_outside_roster" in (
        gaps["Linked spouses outside the opening roster"]
    )
    unobserved = gaps["Opening-year Social Security unobserved"]
    assert "beneficiaries_ss_opening_year_unobserved" in unobserved
    assert "ss_opening_year_unobserved" in unobserved
    # Fixed, so no longer named as gaps: A7's per-cell undefined cells
    # (A1 section 7), the family-unit floor split and the two-seed floor
    # (A1 section 16), and R6.
    assert not {
        "Undefined cells",
        "Half-split floor unit",
        "Floor with one usable seed",
        "R6 (PSID 2009 wave)",
    } & set(gaps)
    assert not any("not built" in gap for gap in gaps.values())
    assert "censored at 2008" in gaps["R6 opening receipt start"]


def test_dry_run_lists_undefined_cells_and_floors_with_reasons():
    import importlib.util
    from pathlib import Path

    path = (
        Path(__file__).resolve().parents[2] / "scripts" / "track_a_dry_run.py"
    )
    spec = importlib.util.spec_from_file_location("track_a_dry_run", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def floor(defined, n_seeds, dropped, reason=None):
        return {
            "defined": defined,
            "undefined_reason": reason,
            "mean": 1.0 if defined else None,
            "n_seeds": n_seeds,
            "dropped_seeds": dropped,
        }

    # INVENTED tabulation fragments: one undefined cell, one undefined
    # floor and one floor that dropped a seed.
    groups = [
        {
            "label": "80+",
            "ratio_of_scenario_means": {
                "floor": floor(False, 1, [1, 2, 3, 4], "fewer than 2")
            },
            "mean_of_individual_ratios": {"floor": floor(True, 4, [3])},
        }
    ]
    result = {
        "rows": {
            "R0": {
                "tabulation": {
                    "groups": groups,
                    "undefined_cells": [
                        {
                            "group": "80+",
                            "statistic": "ratio_of_scenario_means",
                            "n_defined_draws": 1,
                            "undefined_draws": [
                                {
                                    "draw": 2,
                                    "reason": "empty_baseline_membership",
                                }
                            ],
                        }
                    ],
                }
            },
            "R1": {"tabulation": None},
        }
    }
    lines = module._undefined_lines(result)
    assert lines == [
        "- R0, 80+, ratio_of_scenario_means: 1 draws defined (draw 2: "
        "empty_baseline_membership).",
        "- R0, 80+, ratio_of_scenario_means floor: undefined (fewer than "
        "2; 1 usable seeds).",
        "- R0, 80+, mean_of_individual_ratios floor: defined on 4 usable "
        "seeds; seeds [3] dropped because a half's cell is undefined (A1 "
        "section 16).",
    ]
    stat = {
        "defined": False,
        "n_defined_draws": 1,
        "floor": floor(False, 1, [1, 2, 3, 4], "fewer than 2"),
    }
    assert module._cell_text(stat, 3) == (
        "undefined (1 of 3 draws defined) [undefined]"
    )
