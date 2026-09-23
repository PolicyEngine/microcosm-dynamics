"""Committed-input and diagnostic-artifact checks for the SSDI component.

These tests read the <=2008 inputs committed under
``data/external/di_asr_2008`` and the validation-only diagnostic
``runs/di_entitlement_asr2023_validation_v1.json``.  The published values
pinned below were read from the SSA and Census captures themselves.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import sys
from functools import partial
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from populace_dynamics.engine.di_entitlement import (
    apply_di_aware_mortality,
    apply_di_entitlement,
    di_stock_flow,
    prepare_opening_di_state,
)
from populace_dynamics.engine.di_entitlement_rates import (
    DEFAULT_INPUTS_PATH,
    FIT_YEARS,
    NCHS_2000_PATH,
    DIEntitlementSpec,
    load_di_entitlement_rates,
)
from populace_dynamics.engine.loop import (
    MaritalStepResult,
    PeriodContext,
    PeriodModules,
    ProjectionEngine,
)
from populace_dynamics.engine.steps import AgeSexMortalityModel, advance_age

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "external" / "di_asr_2008"
RUN = ROOT / "runs" / "di_entitlement_asr2023_validation_v1.json"
sys.path.insert(0, str(ROOT / "scripts"))

import extract_di_asr_2008 as extract  # noqa: E402

GZ_SHA256 = {
    "asr2008_table19": (
        "e412f2ba9472c10b425966ba7fc4551e216085b4b9c840affd2530467b1bc623"
    ),
    "asr2008_table20": (
        "0dbb550ff0fbc5708e9054be17776a02d498ad672fe25611b3310317b444839b"
    ),
    "asr2008_table35": (
        "243ce9e7e3f9b439a74ec2ead8f66ec65e2cbf199e6aa2ac059df247c7479514"
    ),
    "asr2008_table36": (
        "97032192c23089fc6d1b462b4e1fdbafa85c36ed735f4de63f36473010634eab"
    ),
    "asr2008_table49": (
        "5b48cce59177b03234259fdf7c1117f9706ab16adc1054c6f41a6278c40141e2"
    ),
    "asr2008_table50": (
        "832a0ed4362ed1b253d1e8cd6f41026db18b1c64ea63a15f73500f78df935bb4"
    ),
    "asr2008_table57": (
        "06e836e23c7eb89555d904ed78da254be03219eddc24a45b84b9d78033e6089f"
    ),
    "asr2007_table19": (
        "335d3008ae3c9704c496184ff5051b46f0d73d477284074333df255053b3e76e"
    ),
    "asr2007_table20": (
        "ccac48a48f13bddccb7ceb6931f8e565162ecf5761d45b2da022baab8173c989"
    ),
    "asr2007_table36": (
        "00e05d980c7eb27f592c1c8124e51a78e1331ca2e2d898a658b1f7ca552b80c6"
    ),
    "asr2007_table50": (
        "0a326c5d87b9614797fe2db888ad2d0efbcdc2a56e36db482b0886a2261a9774"
    ),
    "census_v2008_r_file18": (
        "1235f9a7d8971cdd300b22aadfda9f27a19400e940d13950d680e033d71d8810"
    ),
    "census_v2008_layout": (
        "5ec22efeae77424bff6554fb860f90febd3d24f93a4fd870fc7ce2e2df1b3626"
    ),
    "census_v2007_r_file16": (
        "574bd25dba650bafcf8d66a085fcc563f0674855f0f1000d6a5f8efd25000bbf"
    ),
    "as118_death_tables": (
        "be878cb64845f1618f12e5a2efc98034a5ec16d3f510b543eb8def3e430ab024"
    ),
    "as118_recovery_tables": (
        "719655fd8d565418bcfdeb9ced5ec963f3120a090d3167dd8d8cc0d59e445721"
    ),
}


@pytest.fixture(scope="module")
def inputs():
    return json.loads(DEFAULT_INPUTS_PATH.read_text(encoding="utf-8"))


def test_default_paths_point_at_the_committed_inputs():
    assert DEFAULT_INPUTS_PATH == DATA / "tables.json"
    assert NCHS_2000_PATH == ROOT / "data" / "external" / (
        "nchs_life_tables_2000.json"
    )
    assert "di_asr_2023" not in str(DEFAULT_INPUTS_PATH)


def test_raw_captures_match_their_pinned_hashes():
    assert set(GZ_SHA256) == set(extract.SOURCES)
    provenance = (DATA / "provenance.md").read_text(encoding="utf-8")
    for source_id, source in extract.SOURCES.items():
        path = DATA / source["file"]
        compressed = path.read_bytes()
        assert hashlib.sha256(compressed).hexdigest() == GZ_SHA256[source_id]
        original = gzip.decompress(compressed)
        digest = hashlib.sha256(original).hexdigest()
        assert digest == source["sha256_uncompressed"]
        for value in (
            source_id,
            source["url"],
            source["wayback_capture"],
            digest,
            GZ_SHA256[source_id],
        ):
            assert value in provenance
    committed = {path.name for path in (DATA / "raw").iterdir()}
    assert committed == {
        Path(source["file"]).name for source in extract.SOURCES.values()
    }


def test_extraction_reproduces_the_committed_tables():
    committed = DEFAULT_INPUTS_PATH.read_text(encoding="utf-8")
    assert extract.serialize(extract.build()) == committed
    assert extract.main(["--check"]) == 0


def test_every_input_is_within_the_2008_information_boundary(inputs):
    assert inputs["information_boundary_year"] == 2008
    for source in inputs["sources"].values():
        assert int(source["data_year"].split("-")[-1]) <= 2008
        assert "2023" not in source["url"]
        assert int(source["wayback_capture"][:4]) <= 2009


def test_published_values_are_pinned(inputs):
    asr = inputs["asr"]
    awards = asr["2008"]["awards_workers"]
    assert awards["totals"] == {
        "total": 877_226,
        "male": 466_966,
        "female": 410_260,
    }
    assert awards["male"][7] == 109_444  # 55-59
    stock = asr["2008"]["stock_workers_december"]
    assert stock["totals"] == {
        "total": 7_426_691,
        "male": 3_924_524,
        "female": 3_502_167,
    }
    reasons = asr["2008"]["terminations_workers_by_reason"]
    assert reasons["death"] == 215_445
    assert reasons["fra_conversion"] == 269_794
    assert reasons["does_not_meet_medical_standards"] == 59_643
    assert reasons["total"] == 563_314
    assert asr["2007"]["awards_workers"]["totals"]["total"] == 804_787
    assert asr["2007"]["stock_workers_december"]["totals"]["total"] == (
        7_098_723
    )
    assert asr["2008"]["stock_distribution"]["men"]["2007"] == {
        "number_thousands": 3774.0,
        "percent": [3.1, 3.1, 5.1, 8.3, 12.8, 17.0, 21.9, 28.6],
        "average_age": 52.5,
    }
    census = inputs["census_resident_population_july1"]
    assert sum(census["2008"]["male"]) == 149_924_604
    assert sum(census["2008"]["female"]) == 154_135_120
    assert census["2008"]["male"][60] == 1_673_823
    assert sum(census["2007"]["male"]) == 148_658_898
    death = inputs["as118"]["death"]
    assert death["aggregate_by_attained_age"]["male"][50 - 16] == 0.033308
    assert death["ultimate_75_plus"]["male"][0] == 0.094433
    assert death["select_ultimate"]["male"]["select"][0][0] == 0.004751
    recovery = inputs["as118"]["recovery"]
    assert recovery["aggregate_by_attained_age"]["male"][50 - 16] == 0.007685
    assert recovery["select_ultimate"]["male"]["select"][-1][:2] == [
        0.000182,
        None,
    ]


def test_default_fit_is_pinned(inputs):
    rates = load_di_entitlement_rates()
    census = inputs["census_resident_population_july1"]["2008"]
    male_55_59 = sum(census["male"][55:60])
    assert rates.incidence[1, 57] == pytest.approx(
        109_444 / (male_55_59 - 851_524), rel=1e-12
    )
    assert rates.incidence[1, 57] == pytest.approx(0.013407, abs=5e-7)
    assert rates.incidence[0, 52] == pytest.approx(0.007900, abs=5e-7)
    assert rates.incidence[:, :18].sum() == 0.0
    assert rates.recovery_level_factor == pytest.approx(1.0627519, abs=1e-7)
    assert rates.death_level_factor == 1.0
    death = rates.diagnostics["death_level"]
    assert death["fitted_factor"] == pytest.approx(0.8518149, abs=1e-7)
    assert rates.death_attained[1, 50] == pytest.approx(0.033308)
    assert rates.recovery_attained[1, 50] == pytest.approx(
        0.007685 * rates.recovery_level_factor
    )
    assert (
        rates.provenance["inputs_sha256"]
        == hashlib.sha256(DEFAULT_INPUTS_PATH.read_bytes()).hexdigest()
    )


@pytest.mark.parametrize(
    ("fit_year", "years"),
    [
        ("2008", ("2008",)),
        ("2007", ("2007",)),
        ("2007-2008", ("2007", "2008")),
    ],
)
def test_provenance_lists_only_the_sources_the_fit_reads(fit_year, years):
    """Regression: every ``asr<year>_`` capture was listed as used.

    That included ASR 2008 Tables 35, 49, and 57, which are extracted for
    diagnostics and never read by the fit.
    """
    rates = load_di_entitlement_rates(DIEntitlementSpec(fit_year=fit_year))
    census_file = {
        "2008": "census_v2008_r_file18",
        "2007": "census_v2007_r_file16",
    }
    expected = {"as118_death_tables", "as118_recovery_tables"}
    for year in years:
        expected |= {f"asr{year}_table{n}" for n in (19, 20, 36, 50)}
        expected.add(census_file[year])
    assert rates.provenance["sources_used"] == sorted(expected)


def test_sequential_timing_realizes_fewer_recoveries_than_targeted(inputs):
    """Committed 2008 inputs and default rates (a documented named delta).

    The ``asr_fitted`` recovery level makes exposure x q_recovery equal ASR
    Table 50's 59,643 recoveries.  The Actuarial Study probabilities are
    multiple-decrement probabilities, but the loop draws recovery only for
    the survivors of its mortality step, so on the same exposure it
    realizes exposure x (1 - q_death) x q_recovery: about 2.5 percent fewer.
    The exposure rule and the simple within-group means repeat the fit's.
    If the fit starts correcting for survival, update this test and
    ``docs/design/di_entitlement.md``.
    """
    rates = load_di_entitlement_rates()
    asr = inputs["asr"]["2008"]
    stock = asr["stock_workers_december"]
    group_ages = {
        "Under 25": (18, 24),
        "25–29": (25, 29),
        "30–34": (30, 34),
        "35–39": (35, 39),
        "40–44": (40, 44),
        "45–49": (45, 49),
        "50–54": (50, 54),
        "55–59": (55, 59),
        "60–64": (60, 64),
        "65–FRA": (65, 65),
    }
    targeted = 0.0
    realized = 0.0
    for index, (sex, section) in enumerate(
        (("female", "women"), ("male", "men"))
    ):
        totals = asr["stock_distribution"][section]
        prior = totals["2007"]["number_thousands"]
        current = totals["2008"]["number_thousands"]
        scale = (prior + current) / (2.0 * current)
        for label, count in zip(stock["age_groups"], stock[sex], strict=True):
            lower, upper = group_ages[label]
            recovery = rates.recovery_attained[index, lower : upper + 1]
            death = rates.death_attained[index, lower : upper + 1]
            targeted += count * scale * float(recovery.mean())
            realized += count * scale * float((recovery * (1 - death)).mean())
    assert targeted == pytest.approx(59_643, rel=1e-9)
    assert realized / targeted == pytest.approx(0.975, abs=0.001)


@pytest.mark.parametrize("fit_year", FIT_YEARS)
def test_every_fit_year_loads_and_stays_in_range(fit_year):
    rates = load_di_entitlement_rates(DIEntitlementSpec(fit_year=fit_year))
    assert (rates.incidence[:, 18:66] > 0).all()
    assert (rates.incidence < 0.05).all()
    assert rates.diagnostics["fit_years"] == (
        ["2007", "2008"] if fit_year == "2007-2008" else [fit_year]
    )


def test_per_insured_incidence_is_refused():
    with pytest.raises(ValueError, match="per-insured"):
        load_di_entitlement_rates(
            DIEntitlementSpec(incidence_basis="per_insured")
        )


def test_select_basis_loads_from_the_committed_tables():
    rates = load_di_entitlement_rates(
        DIEntitlementSpec(termination_basis="select_and_ultimate")
    )
    first_year = rates.reference_death_probability(
        np.array([50]),
        np.array([1]),
        select_age=np.array([50]),
        duration=np.array([0]),
    )
    assert first_year[0] == pytest.approx(0.077080)


def test_select_basis_gives_no_recovery_past_64_at_any_duration():
    """Committed Actuarial Study No. 118 Tables 14A-14B.

    The tables publish no recovery probability past attained age 64, in the
    select cells or in the "10 or more" ultimate column.  Regression: the
    blank select cells gave zero, but the ultimate column held its age-64
    value, so a worker aged 65 or 66 recovered only after ten years on the
    rolls.  Published cells are unchanged.
    """
    rates = load_di_entitlement_rates(
        DIEntitlementSpec(termination_basis="select_and_ultimate")
    )

    def recovery(sex_index, attained, select_age, duration):
        return float(
            rates.recovery_probability(
                np.array([attained]),
                np.array([sex_index]),
                select_age=np.array([select_age]),
                duration=np.array([duration]),
            )[0]
        )

    factor = rates.recovery_level_factor
    for sex_index, ultimate_64, select_55_at_64 in (
        (1, 0.000335, 0.000439),  # Table 14A (male)
        (0, 0.000333, 0.000536),  # Table 14B (female)
    ):
        assert recovery(sex_index, 64, 54, 10) == pytest.approx(
            ultimate_64 * factor
        )
        assert recovery(sex_index, 64, 55, 9) == pytest.approx(
            select_55_at_64 * factor
        )
        assert recovery(sex_index, 65, 56, 9) == 0.0
        assert recovery(sex_index, 65, 55, 10) == 0.0
        assert recovery(sex_index, 66, 55, 11) == 0.0
        assert recovery(sex_index, 66, 40, 26) == 0.0
    # The attained-age default still holds the age-64 value (named delta).
    default = load_di_entitlement_rates()
    assert default.recovery_attained[1, 66] == default.recovery_attained[1, 64]
    assert default.recovery_attained[1, 66] > 0


def _passthrough(frame, context, rng):
    return frame


def test_committed_rates_run_through_the_loop_and_reconcile():
    """INVENTED cohort and FRA schedule; committed rates."""
    rates = load_di_entitlement_rates()

    def fra(birth_year):  # INVENTED: 66 years, then 67 from 1960
        return 792 if birth_year < 1960 else 804

    rng = np.random.default_rng(3)
    n = 600
    cohort = pd.DataFrame(
        {
            "person_id": np.arange(1, n + 1),
            "year": 2010,
            "sex": rng.choice(["female", "male"], n),
            "birth_year": rng.integers(1950, 1985, n),
        }
    )
    cohort["age"] = 2010 - cohort["birth_year"]
    cohort["di_entitled"] = rng.random(n) < 0.08
    log = {}
    mortality = AgeSexMortalityModel(
        ((0, 120),), {("0+", "female"): 0.01, ("0+", "male"): 0.012}
    )
    modules = PeriodModules(
        mortality=partial(
            apply_di_aware_mortality,
            population_model=mortality,
            rates=rates,
            death_log=log,
            weight_column=None,
        ),
        aging=advance_age,
        marital_core=lambda frame, context, rng: MaritalStepResult(
            sim_years=pd.DataFrame(), births=pd.DataFrame()
        ),
        fertility=lambda frame, context, marital, rng: frame,
        disability=partial(
            apply_di_entitlement, rates=rates, fra_schedule=fra
        ),
        earnings=_passthrough,
        claiming=_passthrough,
        household_composition=lambda frame, context, marital, rng: frame,
        initialize=partial(
            prepare_opening_di_state, rates=rates, fra_schedule=fra
        ),
    )
    result = ProjectionEngine(modules).project(
        cohort, end_year=2030, draw_index=0
    )
    flows = di_stock_flow(result.slices, death_log=log)
    assert flows["awards"].sum() > 0
    assert flows["conversions"].sum() > 0


class _ZeroDraw:
    """Batch generator whose uniforms are all zero: every q > 0 dies."""

    def random(self, size):
        return np.zeros(size)


@pytest.mark.filterwarnings(
    "ignore:.*DI-origin expected deaths exceed:RuntimeWarning"
)
def test_multiplier_reproduces_as118_under_banded_nchs_2000_mortality():
    """Committed rates; INVENTED 10-year banding shaped like the engine's.

    A population model equal to NCHS 2000 averaged (l_x-weighted, from the
    committed life table's own l_x column) over 10-year bands must leave
    disabled-worker death probabilities at the Actuarial Study No. 118
    Table 12 values at every single age.  Regression for the multiplier
    base, which used to be single-age NCHS 2000 whatever the population
    model's resolution: at age 55 that inflated male DI mortality by about
    half and at age 64 deflated it by about 30 percent.
    """
    rates = load_di_entitlement_rates()
    life = json.loads(NCHS_2000_PATH.read_text(encoding="utf-8"))
    bands = (
        (0, 24),
        (25, 34),
        (35, 44),
        (45, 54),
        (55, 64),
        (65, 74),
        (75, 84),
        (85, 120),
    )
    probability = {}
    for sex in ("female", "male"):
        rows = {int(row["age"]): row for row in life["tables"][sex]}
        for lower, upper in bands:
            ages = range(lower, min(upper, 99) + 1)
            weight = np.array([float(rows[a]["lx"]) for a in ages])
            q = np.array([float(rows[a]["qx"]) for a in ages])
            label = AgeSexMortalityModel.band_label(lower, upper)
            probability[(label, sex)] = float(
                (weight * q).sum() / weight.sum()
            )
    model = AgeSexMortalityModel(bands, probability)
    frame = pd.DataFrame(
        {
            "person_id": np.arange(1, 41),
            "year": 2010,
            "sex": ["male", "female"] * 20,
            "birth_year": np.repeat(2010 - np.arange(45, 65), 2),
            "di_entitled": True,
        }
    )
    frame["age"] = 2010 - frame["birth_year"]

    def fra(birth_year):  # INVENTED: 66 years for these cohorts
        return 792

    start = prepare_opening_di_state(frame, rates=rates, fra_schedule=fra)
    log = {}
    apply_di_aware_mortality(
        start,
        PeriodContext(1, 2011, 0, {}),
        _ZeroDraw(),
        population_model=model,
        rates=rates,
        death_log=log,
        weight_column=None,
    )
    logged = log[2011]
    assert len(logged) == 40
    sex_index = np.where(logged["sex"] == "male", 1, 0)
    published = rates.death_attained[sex_index, logged["start_age"]]
    # l_x in the committed table is rounded, so allow 1e-4 relative.
    assert logged["q_applied"].to_numpy() == pytest.approx(published, rel=1e-4)
    # Actuarial Study No. 118 Table 12, attained ages 55 and 64 (capture).
    applied = logged.set_index(["sex", "start_age"])["q_applied"]
    assert applied[("male", 55)] == pytest.approx(0.040662, rel=1e-4)
    assert applied[("male", 64)] == pytest.approx(0.056410, rel=1e-4)
    assert applied[("female", 55)] == pytest.approx(0.030052, rel=1e-4)


def test_population_total_would_inflate_all_person_mortality(inputs):
    """Committed 2008 prevalence, AS118 rates, NCHS 2000 single ages.

    The population model is all-person mortality.  Regression: keeping it
    for non-DI-origin persons (now the ``population_total`` alternative)
    raised expected deaths in every ASR age group from 45 to 64 by about 25
    to 35 percent at the December 2008 disabled-worker prevalence (Table 20
    stock spread evenly within groups over Census July 1, 2008 population).
    The default ``net_of_di_origin`` keeps them at the population model's.
    """
    life = json.loads(NCHS_2000_PATH.read_text(encoding="utf-8"))
    bands = tuple((age, age) for age in range(100)) + ((100, 120),)
    probability = {}
    for sex in ("female", "male"):
        rows = {int(r["age"]): float(r["qx"]) for r in life["tables"][sex]}
        for lower, upper in bands:
            label = AgeSexMortalityModel.band_label(lower, upper)
            probability[(label, sex)] = rows[lower]
    model = AgeSexMortalityModel(bands, probability)
    census = inputs["census_resident_population_july1"]["2008"]
    stock = inputs["asr"]["2008"]["stock_workers_december"]
    groups = {"45–49": (45, 49), "50–54": (50, 54), "55–59": (55, 59)}
    groups["60–64"] = (60, 64)
    records = []
    for sex in ("female", "male"):
        counts = dict(zip(stock["age_groups"], stock[sex], strict=True))
        for label, (lower, upper) in groups.items():
            per_age = counts[label] / (upper - lower + 1)
            for age in range(lower, upper + 1):
                population = float(census[sex][age])
                records.append((sex, age, False, population - per_age))
                records.append((sex, age, True, per_age))
    frame = pd.DataFrame(
        records, columns=["sex", "age", "di_entitled", "weight"]
    )
    frame["person_id"] = np.arange(1, len(frame) + 1)
    frame["year"] = 2008
    frame["birth_year"] = 2008 - frame["age"]

    def fra(birth_year):  # INVENTED: 66 years, then 67 from 1960
        return 792 if birth_year < 1960 else 804

    ratios = {}
    for choice in ("population_total", "net_of_di_origin"):
        rates = load_di_entitlement_rates(
            DIEntitlementSpec(non_di_mortality=choice)
        )
        start = prepare_opening_di_state(frame, rates=rates, fra_schedule=fra)
        log = {}
        apply_di_aware_mortality(
            start,
            PeriodContext(1, 2009, 0, {}),
            _ZeroDraw(),
            population_model=model,
            rates=rates,
            death_log=log,
            weight_column="weight",
        )
        applied = log[2009].merge(start[["person_id", "age", "weight"]])
        for sex in ("female", "male"):
            for label, (lower, upper) in groups.items():
                cell = applied[
                    (applied["sex"] == sex)
                    & applied["age"].between(lower, upper)
                ]
                ratios[(choice, sex, label)] = float(
                    (cell["weight"] * cell["q_applied"]).sum()
                    / (cell["weight"] * cell["q_population"]).sum()
                )
    for sex in ("female", "male"):
        for label in groups:
            assert 1.24 < ratios[("population_total", sex, label)] < 1.36
            assert ratios[("net_of_di_origin", sex, label)] == pytest.approx(
                1.0, rel=1e-9
            )


@pytest.fixture(scope="module")
def run_artifact():
    return json.loads(RUN.read_text(encoding="utf-8"))


def test_validation_artifact_is_labeled_validation_only(run_artifact):
    assert run_artifact["validation_only"] is True
    assert run_artifact["fitting_target"] is False
    assert run_artifact["computes_cola_statistic"] is False
    assert run_artifact["reads_comparator_values"] is False
    assert run_artifact["opening_population"]["kind"] == "SYNTHETIC"
    assert "VALIDATION-ONLY" in run_artifact["label"]
    assert run_artifact["comparison_source"]["path"] == (
        "data/external/di_asr_2023/tables.json"
    )
    assert (
        run_artifact["comparison_source"]["sha256"]
        == hashlib.sha256(
            (ROOT / run_artifact["comparison_source"]["path"]).read_bytes()
        ).hexdigest()
    )


def test_validation_artifact_is_bound_to_the_committed_inputs(run_artifact):
    import validate_di_entitlement_asr2023 as validation

    assert run_artifact["inputs"]["di_asr_2008_tables_sha256"] == (
        hashlib.sha256(DEFAULT_INPUTS_PATH.read_bytes()).hexdigest()
    )
    assert set(run_artifact["variants"]) == set(validation.VARIANTS)
    for name, spec in validation.VARIANTS.items():
        variant = run_artifact["variants"][name]
        assert variant["spec"] == spec.as_dict()
        current = json.loads(
            json.dumps(load_di_entitlement_rates(spec).summary())
        )
        assert variant["rates"] == current
        years = [row["year"] for row in variant["years"]]
        assert years == list(range(2008, 2024))
        opening = variant["years"][0]["stock_thousands"]
        stock = run_artifact["opening_population"]["asr2008_table20_stock"]
        assert opening["male"] * 1000 == pytest.approx(stock["male"])
        assert opening["female"] * 1000 == pytest.approx(stock["female"])
        comparison_years = [row["year"] for row in variant["comparison"]]
        assert comparison_years == years
