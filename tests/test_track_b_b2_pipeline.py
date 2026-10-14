"""Invented-panel tests of B2's floor builder and one-shot scorer.

No PSID file, selection ledger or candidate artifact is read. The PSID
readers are replaced by invented fields for collection waves 1993-2015, and
the fit uses an injected stochastic sign gate in place of populace-fit, so
these tests run without the fitting stack. To keep them quick, the floor
runs 5 seeds instead of 100 (gate seeds 0-4 stay inside them), the
projection 3 draws instead of 20, and the bootstraps a few replicates; the
registered counts are pinned separately and the scripts refuse to write an
artifact with any other.

What they establish:

- B2's data-only domain, truth support and person-split floor equal what
  the selectors' ``_boundary_context`` builds at boundary 2010, so the
  builder's canonical hashes equal those of the selectors' floor fields,
  after a JSON round trip as the ledgers store them;
- at the 2006 geometry the scorer's fit, context and frames equal the
  planning script's, and the scorer and arm F build identical copied frames
  and gaps for the same multiplicities;
- the floor builder merges singleton strata, uses exact Rao-Wu, scores an
  ineligible cell report-only, and stops on zero degrees of freedom or an
  eligible cell's undefined power;
- the scorer, end to end, scores every cell and returns section 8's
  outcome, and refuses a floor that is not the data's;
- both scripts refuse to run without their preconditions.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import select_m6_qstar_train_only as selector  # noqa: E402
import track_b_b0_1_planning_values as pv  # noqa: E402
import track_b_b0_1_ruled_power as ruled  # noqa: E402
import track_b_b2_compare_floor as comparator  # noqa: E402
import track_b_b2_floor as floor_builder  # noqa: E402
import track_b_b2_score as scorer  # noqa: E402

from populace_dynamics.data import family, panels  # noqa: E402
from populace_dynamics.harness import m6_cells, m6_scoring  # noqa: E402
from populace_dynamics.track_b import b2  # noqa: E402

PLANNING = ROOT / "docs" / "design" / "track_b_b0_1_planning_values.json"


@pytest.fixture(autouse=True)
def registered_thread_settings(monkeypatch, tmp_path):
    """The entry points refuse anything but one thread per process
    (``b2.thread_settings``); set it here, as a registered launch does.
    Tests of the refusal override one variable. The scripts' outputs and
    attempt log point into the test's own directory, so B2's committed run
    files never change what a test sees."""
    for name in b2.THREAD_VARIABLES:
        monkeypatch.setenv(name, "1")
    monkeypatch.setenv("OMP_WAIT_POLICY", "PASSIVE")
    monkeypatch.setenv("POPULACE_FIT_N_JOBS", "4")
    monkeypatch.setattr(floor_builder, "OUTPUT", tmp_path / "floor.json")
    monkeypatch.setattr(scorer, "OUTPUT", tmp_path / "score.json")
    monkeypatch.setattr(scorer, "ATTEMPT", tmp_path / "attempt.jsonl")


PROTOCOL_V2_ROOT = 20260930
FEW_FLOOR_SEEDS = tuple(range(5))
FEW_DRAW_SEEDS = (6200, 6201, 6202)
HEAD_CODES = (10,)
SPOUSE_CODES = (20, 22)


def _codes(_wave: int) -> tuple[tuple[int, ...], tuple[int, ...]]:
    return HEAD_CODES, SPOUSE_CODES


class _StochasticGate:
    """Participation depends on the current level; no populace-fit needed."""

    def draw_sign(self, current_level, target_age, uniforms):
        p_zero = np.where(np.asarray(current_level) > 0, 0.08, 0.55)
        return (np.asarray(uniforms) >= p_zero).astype(np.int64)


class _StochasticFactory:
    def __call__(self, *, seed: int):
        class Model:
            def fit(self, frame, **kwargs):
                return _StochasticGate()

        return Model()


def _invented_fields(n_households: int = 180, seed: int = 11):
    """Invented individual rows and family labor fields, waves 1993-2015.

    Interview numbers are household numbers, unique within each wave.
    """
    rng = np.random.default_rng(seed)
    waves = [
        wave for wave in selector.EARNINGS_COLLECTION_WAVES if wave >= 1993
    ]
    people: list[dict] = []
    labor: dict[int, list[dict]] = {wave: [] for wave in waves}
    for household in range(1, n_households + 1):
        size = 1 + int(rng.random() < 0.6)
        last_wave = (
            int(rng.choice([2009, 2011, 2013]))
            if rng.random() < 0.15
            else 2015
        )
        births = [int(rng.integers(1940, 1985)) for _ in range(size)]
        levels = [float(rng.normal(10.2, 0.6)) for _ in range(size)]
        for wave in waves:
            if wave > last_wave:
                continue
            row_labor = {"interview": household}
            for member in range(size):
                age = wave - births[member]
                people.append(
                    {
                        "person_id": household * 1000 + member + 1,
                        "period": wave,
                        "age": age,
                        "sequence": member + 1,
                        "relationship": (HEAD_CODES + SPOUSE_CODES)[member],
                        "weight": float(1.0 + household % 5),
                        "interview": household,
                    }
                )
                zero = rng.random() < (0.35 if age > 60 else 0.12)
                level = (
                    0.0
                    if zero
                    else float(np.exp(levels[member] + rng.normal(0, 0.45)))
                )
                key = "head_labor" if member == 0 else "spouse_labor"
                row_labor[key] = level
            row_labor.setdefault("spouse_labor", 0.0)
            labor[wave].append(row_labor)
    person_wave = pd.DataFrame(people)
    frames = {wave: pd.DataFrame(rows) for wave, rows in labor.items()}
    return person_wave, frames


def _design_for(person_wave: pd.DataFrame, extra_cluster: bool = False):
    """Ten strata of two clusters each, by household; optionally a third
    cluster in stratum 1."""
    persons = np.sort(person_wave["person_id"].unique())
    household = persons // 1000
    design = pd.DataFrame(
        {
            "person_id": persons,
            "stratum": (household - 1) % 10 + 1,
            "cluster": ((household - 1) // 10) % 2 + 1,
        }
    )
    if extra_cluster:
        third = (design["stratum"] == 1) & (household % 7 == 0)
        design.loc[third, "cluster"] = 3
    return design


@pytest.fixture(scope="module")
def fast_protocol():
    """Five floor seeds and three draws, module-wide."""
    with pytest.MonkeyPatch.context() as patch:
        for module in (m6_cells, selector, pv):
            patch.setattr(module, "FLOOR_SEEDS", FEW_FLOOR_SEEDS)
        patch.setattr(pv, "DRAW_SEEDS", FEW_DRAW_SEEDS)
        yield


@pytest.fixture(scope="module")
def invented(fast_protocol):
    person_wave, labor = _invented_fields()
    empty = labor[2015].iloc[:0]

    def fake_individual(concepts, *, data_dir, waves):
        return person_wave[person_wave["period"].isin(waves)].copy()

    def fake_family(wave, *, data_dir):
        return labor.get(wave, empty).copy()

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(panels, "ind_person_period", fake_individual)
        patch.setattr(selector, "_read_family_labor_levels", fake_family)
        patch.setattr(family, "_relationship_codes", _codes)
        earnings, anchor_demo = floor_builder.load_sources(
            Path("/invented-psid")
        )
    return {
        "person_wave": person_wave,
        "earnings": earnings,
        "anchor_demo": anchor_demo,
        "design": _design_for(person_wave),
        "planning": json.loads(PLANNING.read_text(encoding="utf-8")),
        "nawi_2010": {
            year: 30_000.0 * 1.03 ** (year - 1990)
            for year in range(1960, 2011)
        },
        "nawi_2006": {
            year: 30_000.0 * 1.03 ** (year - 1990)
            for year in range(1960, 2007)
        },
    }


@pytest.fixture(scope="module")
def measured(invented):
    return floor_builder.measure(
        invented["earnings"],
        invented["anchor_demo"],
        config=floor_builder.FloorConfig(b_household=8, workers=1),
    )


@pytest.fixture(scope="module")
def fit_2010(invented):
    """Candidate 3's law at 2010 (stub gate), its context and draws."""
    fit_input = selector.truncate_estimation_frame(
        invented["earnings"],
        boundary_year=2010,
        year_column="period",
        flow=False,
        label="invented",
    )
    fitted = scorer.fit_law(
        fit_input, invented["nawi_2010"], qrf_factory=_StochasticFactory()
    )
    full = b2.full_anchor_frame(invented["anchor_demo"])
    context = scorer.build_context(fitted, invented["earnings"], full)
    return {
        "fitted": fitted,
        "context": context,
        "draws": pv.project_draws(fitted.generator, context),
    }


@pytest.fixture(scope="module")
def selector_2010(invented, fit_2010):
    """The selectors' own boundary-2010 context on the invented panel."""
    return selector._boundary_context(
        fit_2010["fitted"],
        invented["earnings"],
        invented["anchor_demo"],
        2010,
    )


@pytest.fixture(scope="module")
def cleared_floor(invented, measured):
    """The floor record with the ladder's power held at 0.95, so the six
    clear at once, after a JSON round trip as the committed file would."""
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(
            floor_builder,
            "ladder_power",
            lambda planning, tau, nu: (lambda names: 0.95),
        )
        record = floor_builder.decide(
            measured, invented["design"], invented["planning"]
        )
    return json.loads(json.dumps(b2.plain(record), allow_nan=False))


# --------------------------------------------------------------------------
# Sources, domain and the selectors' floor fields
# --------------------------------------------------------------------------
def test_sources_reach_2014_and_anchor_at_2011(invented):
    earnings = invented["earnings"]
    assert int(earnings["period"].max()) == 2014
    assert set(invented["anchor_demo"]["period"]) <= {2007, 2009, 2011}
    full = b2.full_anchor_frame(invented["anchor_demo"])
    assert list(full.columns) == ["person_id", "household_id", "weight"]
    domain = b2.domain_person_ids(earnings, full)
    with_2010 = set(earnings.loc[earnings.period == 2010, "person_id"])
    assert domain == frozenset(set(full["person_id"]) & with_2010)


def test_domain_truth_and_floors_equal_the_selectors(
    invented, measured, selector_2010
):
    full = b2.full_anchor_frame(invented["anchor_demo"])
    domain = b2.domain_person_ids(invented["earnings"], full)
    truth = b2.truth_support(invented["earnings"], full, domain)
    assert full.equals(selector_2010.full_anchor)
    assert domain == selector_2010.domain_ids
    assert truth.equals(selector_2010.truth_support)
    hashes = measured["record"]["person_split"]
    assert hashes["floor_block_six_cells_sha256"] == (
        selector._canonical_sha256(selector_2010.floor)
    )
    assert hashes["seed_detail_six_cells_sha256"] == (
        selector._canonical_sha256(
            b2.six_cell_seed_detail(selector_2010.floor_gate_seed_detail)
        )
    )
    domain_record = measured["record"]["domain"]
    assert domain_record["domain_ids_sha256"] == (
        selector._id_checksum(selector_2010.domain_ids)
    )
    assert domain_record["truth_support_keys_sha256"] == (
        selector._key_checksum(selector_2010.truth_support)
    )


def test_the_comparator_matches_the_selectors_fields_after_json(
    measured, selector_2010
):
    """The ledgers hold the selectors' fields as JSON (``_plain``)."""
    ledger = json.loads(
        json.dumps(
            selector._plain(
                {
                    "floor": selector_2010.floor,
                    "detail": selector_2010.floor_gate_seed_detail,
                }
            ),
            sort_keys=True,
            allow_nan=False,
        )
    )
    result = comparator.compare(
        measured["record"]["person_split"], ledger["floor"], ledger["detail"]
    )
    assert result == (True, True)
    moved = json.loads(json.dumps(ledger))
    moved["floor"]["earn_p10.prime"]["mean"] += 1e-12
    assert (
        comparator.compare(
            measured["record"]["person_split"], moved["floor"], moved["detail"]
        )[0]
        is False
    )


# --------------------------------------------------------------------------
# The scorer's machinery against the planning script at the 2006 geometry
# --------------------------------------------------------------------------
@pytest.fixture(scope="module")
def at_2006(invented):
    earnings = invented["earnings"]
    fit_input = pv.truncate_estimation_frame(
        earnings,
        boundary_year=2006,
        year_column="period",
        flow=False,
        label="invented",
    )
    person_wave = invented["person_wave"]
    full = pv.anchor_frame(person_wave, 2007)
    fitted_pv = pv.fit_law(
        fit_input, invented["nawi_2006"], qrf_factory=_StochasticFactory()
    )
    fitted_b2 = scorer.fit_law(
        fit_input,
        invented["nawi_2006"],
        boundary=2006,
        qrf_factory=_StochasticFactory(),
    )
    context_pv = pv.build_context(fitted_pv, earnings, full)
    context_b2 = scorer.build_context(fitted_b2, earnings, full, boundary=2006)
    present = person_wave[person_wave["sequence"].between(1, 20)]
    return {
        "full": full,
        "fitted_pv": fitted_pv,
        "fitted_b2": fitted_b2,
        "context_pv": context_pv,
        "context_b2": context_b2,
        "draws_pv": pv.project_draws(fitted_pv.generator, context_pv),
        "draws_b2": pv.project_draws(fitted_b2.generator, context_b2),
        "clusters": pv.cluster_table(
            present, fit_input["person_id"].unique(), full
        ),
    }


def test_fit_and_context_equal_the_planning_scripts_at_2006(at_2006):
    assert at_2006["fitted_b2"].forward_pairs.equals(
        at_2006["fitted_pv"].forward_pairs
    )
    assert at_2006["fitted_b2"].anchors.equals(at_2006["fitted_pv"].anchors)
    left, right = at_2006["context_b2"], at_2006["context_pv"]
    assert left.boundary == right.boundary == 2006
    assert left.domain_ids == right.domain_ids
    assert left.truth_support.equals(right.truth_support)
    assert left.initial_slice.equals(right.initial_slice)
    for a, b in zip(at_2006["draws_b2"], at_2006["draws_pv"], strict=True):
        assert a.equals(b)


def test_cells_and_floors_equal_the_planning_scripts_at_2006(at_2006):
    truth = at_2006["context_pv"].truth_support
    years = {"level_years": pv.LEVEL_YEARS, "change_years": pv.CHANGE_YEARS}
    assert b2.cell_values(truth, **years) == {
        name: cell["value"] for name, cell in pv.cell_values(truth).items()
    }
    floor, _ = b2.split_floor(at_2006["full"], truth, "household_id", **years)
    assert {name: floor[name] for name in b2.CELLS} == pv.household_floor(
        at_2006["full"], truth
    )


@pytest.mark.parametrize("replicate", [0, 1])
def test_the_scorer_and_arm_f_build_identical_frames(at_2006, replicate):
    clusters = at_2006["clusters"]
    truth = at_2006["context_pv"].truth_support
    draws = at_2006["draws_pv"]
    mult = b2.anchor_multiplicities(clusters, replicate, root=PROTOCOL_V2_ROOT)
    assert mult == pv.anchor_multiplicities(clusters, replicate)
    copied_truth, copied_draws = scorer.copied_frames(truth, draws, mult)
    assert copied_truth.equals(pv.copy_persons(truth, mult))
    for frame, original in zip(copied_draws, draws, strict=True):
        assert frame.equals(pv.copy_persons(original, mult))
    reference = {
        name: cell["value"] for name, cell in pv.cell_values(truth).items()
    }
    expected = pv.arm_f_replicate(
        replicate, clusters, truth, draws, reference
    )["gaps"]
    assert (
        scorer.replicate_gaps(
            truth,
            draws,
            mult,
            level_years=pv.LEVEL_YEARS,
            change_years=pv.CHANGE_YEARS,
        )
        == expected
    )


# --------------------------------------------------------------------------
# The floor builder
# --------------------------------------------------------------------------
def test_measure_records_truth_side_values_only(invented, measured):
    full = b2.full_anchor_frame(invented["anchor_demo"])
    floor, _ = b2.split_floor(full, measured["truth"], "household_id")
    assert measured["floor_household"] == floor
    record = measured["record"]
    assert set(record) == {"counts", "domain", "person_split", "config"}
    assert record["config"]["b_household"] == 8
    assert record["person_split"]["gating"] is False
    assert record["person_split"]["seeds"] == list(b2.GATE_SEEDS)
    assert set(measured["se_up"]) == set(b2.CELLS)
    for value in measured["se_up"].values():
        assert value["replicates"] == 8


def test_household_replicate_is_deterministic_and_copies_households(
    invented, measured
):
    full = b2.full_anchor_frame(invented["anchor_demo"])
    truth = measured["truth"]
    clusters = b2.household_clusters(full)
    payload = {
        "clusters": clusters,
        "truth": truth,
        "reference": b2.cell_values(truth),
    }
    b2._worker_init(payload)
    try:
        first = floor_builder.household_replicate(3)
        again = floor_builder.household_replicate(3)
    finally:
        b2._worker_init({})
    assert first == again
    mult = b2.anchor_multiplicities(clusters, 3, root=b2.ROOT_SEED)
    values = b2.cell_values(pv.copy_persons(truth, mult))
    for name, metric in b2.CELL_METRICS.items():
        assert first["tdev"][name] == pv.truth_deviation(
            metric, values[name], payload["reference"][name]
        )


def test_the_six_level_cells_are_eligible_on_the_invented_floor(
    invented, measured
):
    cells = floor_builder.cell_records(
        measured["floor_household"],
        measured["se_up"],
        invented["planning"],
        len(m6_cells.FLOOR_SEEDS),
    )
    for name in b2.LEVEL_CELLS:
        assert cells[name]["eligible"], name
        assert cells[name]["tolerance"] > 0
        assert cells[name]["tau_se_up_units"] > 0


def test_decide_runs_the_ruled_ladder(invented, measured):
    record = floor_builder.decide(
        measured, invented["design"], invented["planning"]
    )
    assert record["outcome"] in (b2.LADDER_CLEARED, b2.WEAK_POWER_OR_VACUITY)
    assert record["design"]["after_merges"]["strata_with_two_clusters"] == 10
    assert record["design"]["design_degrees_of_freedom"] == 10
    ladder = record["ladder"]
    assert ladder["eligible"] == list(b2.LEVEL_CELLS)
    tau = {
        name: record["cells"][name]["tau_se_up_units"]
        for name in ladder["eligible"]
    }
    # The ladder's power is the ruled binding evaluation, term for term.
    power = floor_builder.ladder_power(invented["planning"], tau, 10)
    six = ruled.ruled_cells(invented["planning"], ruled.BINDING)
    direct = ruled.surface_power(
        [
            ruled.RuledCell(
                n, six[n].r, six[n].d, six[n].e_true, six[n].e_reg, tau[n]
            )
            for n in sorted(tau)
        ],
        10,
        ruled.BINDING,
    )["p_gate"]
    assert power(tuple(sorted(tau))) == direct
    assert ladder["p_gate_before_pruning"] == direct
    assert record["candidate_runs_permitted"] == (
        record["outcome"] == b2.LADDER_CLEARED
    )
    if record["outcome"] == b2.LADDER_CLEARED:
        assert ladder["p_gate"] >= 0.90 and len(ladder["retained"]) >= 4
    gated = {entry["cell"] for entry in record["surface"]["gated"]}
    report = {entry["cell"] for entry in record["surface"]["report_only"]}
    assert gated | report == set(b2.CELLS) and not gated & report


def test_cleared_floor_publishes_the_surface(cleared_floor):
    assert cleared_floor["outcome"] == b2.LADDER_CLEARED
    assert cleared_floor["candidate_runs_permitted"] is True
    gated = cleared_floor["surface"]["gated"]
    assert [entry["cell"] for entry in gated] == list(b2.LEVEL_CELLS)
    for entry in gated:
        assert entry["exposure_label"] == b2.exposure_label(entry["cell"])
        assert entry["plain_units"] == b2.plain_units(
            entry["metric"], entry["tolerance"]
        )
    headline = cleared_floor["surface"]["headline"]
    assert headline["scope"] == b2.HEADLINE_SCOPE
    assert headline["gated_by_exposure_label"] == {
        b2.EXPOSURE_PUBLISHED_OUTCOMES: 1,
        b2.EXPOSURE_FLOOR_DETAIL: 5,
    }
    reasons = {
        entry["cell"]: entry["reason"]
        for entry in cleared_floor["surface"]["report_only"]
    }
    assert len(reasons) == 10
    assert set(reasons.values()) == {"outside the ruled surface (d781 (a))"}
    power = cleared_floor["power"]
    assert power["m"] == 6 and power["design_degrees_of_freedom"] == 10
    assert power["t_star"] == b2.t_star(6, 10)


def test_floor_and_scorer_apply_singleton_merges_and_exact_rao_wu(
    invented, measured, fit_2010, monkeypatch
):
    design = _design_for(invented["person_wave"], extra_cluster=True)
    design.loc[design["stratum"] == 3, "cluster"] = 1
    monkeypatch.setattr(
        floor_builder, "ladder_power", lambda *args: lambda names: 0.95
    )
    record = floor_builder.decide(measured, design, invented["planning"])
    summary = record["design"]
    assert summary["before_merges"]["strata_with_one_cluster"] == 1
    assert summary["before_merges"]["strata_with_three_or_more_clusters"] == 1
    assert summary["merges"] == [{"from_stratum": 3, "to_stratum": 2}]
    assert summary["after_merges"]["strata_by_cluster_count"] == {
        "2": 7,
        "3": 2,
    }
    assert summary["scale_l"] == 2
    assert summary["design_degrees_of_freedom"] == 11
    assert record["outcome"] == b2.LADDER_CLEARED
    assert record["candidate_runs_permitted"] is True
    # Reuse the invented fit; run_score still performs all input checks and
    # invokes fit_law, the selectors' projection loop and the design workers.
    monkeypatch.setattr(
        scorer, "fit_law", lambda *args, **kwargs: fit_2010["fitted"]
    )
    scored = scorer.run_score(
        invented["earnings"],
        invented["anchor_demo"],
        design,
        invented["nawi_2010"],
        record,
        invented["planning"],
        config=scorer.ScoreConfig(b_design=2, workers=1),
    )
    assert scored["gate"]["design_degrees_of_freedom"] == 11
    assert scored["gate"]["critical_value"] == b2.t_star(6, 11)
    assert not scored["design_replicate_failures"]


def test_floor_stops_when_an_eligible_se_up_is_undefined(invented, measured):
    broken = dict(measured)
    broken["se_up"] = {
        **measured["se_up"],
        "earn_p50.prime": {
            **measured["se_up"]["earn_p50.prime"],
            "se_up": None,
        },
    }
    record = floor_builder.decide(
        broken, invented["design"], invented["planning"]
    )
    assert record["outcome"] == b2.WEAK_POWER_OR_VACUITY
    assert record["stop_causes"] == [
        {"cell": "earn_p50.prime", "quantity": "se_up"},
        {"cell": "earn_p50.prime", "quantity": "tau"},
    ]
    assert record["candidate_runs_permitted"] is False


def test_floor_stops_at_zero_nu_before_ladder_or_fit(
    invented, measured, monkeypatch
):
    def forbidden(*args, **kwargs):
        pytest.fail("the ladder or fit began")

    monkeypatch.setattr(floor_builder, "ladder_power", forbidden)
    monkeypatch.setattr(scorer, "fit_law", forbidden)
    design = invented["design"].assign(stratum=1, cluster=1)
    record = floor_builder.decide(measured, design, invented["planning"])
    assert record["outcome"] == b2.WEAK_POWER_OR_VACUITY
    assert record["design"]["design_degrees_of_freedom"] == 0
    assert record["stop_causes"] == [{"cell": None, "quantity": "nu"}]
    assert record["ladder"] is None and record["power"] is None
    assert record["candidate_runs_permitted"] is False
    with pytest.raises(ValueError, match="does not permit"):
        scorer.run_score(
            invented["earnings"],
            invented["anchor_demo"],
            design,
            invented["nawi_2010"],
            record,
            invented["planning"],
            config=scorer.ScoreConfig(b_design=1, workers=1),
        )


@pytest.mark.parametrize(
    "quantity, value",
    [
        ("se_up", 0),
        ("se_up", None),
        ("tau", math.nan),
        ("sigma", 0.0),
        ("sigma", None),
        ("zero_floor", 0.0),
    ],
)
def test_floor_stops_on_an_eligible_cells_undefined_power(
    invented, measured, monkeypatch, quantity, value
):
    """An eligible cell whose sigma, se_up or tau is zero or undefined has
    an uninformative tolerance or no power. Section 5 never drops an
    eligible cell, so B2 stops at floor build before the ladder (which
    would otherwise divide by sigma)."""
    broken = copy.deepcopy(measured)
    name = "earn_p50.prime"
    floor = broken["floor_household"][name]
    if quantity == "se_up":
        broken["se_up"][name]["se_up"] = value
    elif quantity == "tau":
        floor["mean"] = value
    elif quantity == "sigma":
        floor["realized_sigma"] = value
    else:
        # A consistent zero floor: every split score zero, so the mean, the
        # SD, sigma and the tolerance are all 0, with seeds and events
        # intact.
        floor.update(mean=value, sd=value, realized_sigma=value)
        quantity = "sigma"

    def forbidden(*args):
        pytest.fail("the ladder began")

    monkeypatch.setattr(floor_builder, "ladder_power", forbidden)
    record = floor_builder.decide(
        broken, invented["design"], invented["planning"]
    )
    assert record["cells"][name]["eligible"] is True
    assert record["outcome"] == b2.WEAK_POWER_OR_VACUITY
    assert {"cell": name, "quantity": quantity} in record["stop_causes"]
    assert record["ladder"] is None
    assert record["candidate_runs_permitted"] is False


@pytest.mark.parametrize(
    "change",
    ["seeds_undefined", "too_few_events", "uninformative_too"],
)
def test_an_ineligible_cell_is_report_only_and_the_ladder_runs(
    invented, measured, change
):
    """Section 5: a cell of the six that fails eligibility (its seeds or
    its events) is scored report-only, and the ladder runs on the eligible
    cells. Its own sigma, se_up or tau does not stop B2."""
    broken = copy.deepcopy(measured)
    name = "earn_p50.prime"
    floor = broken["floor_household"][name]
    if change == "seeds_undefined":
        floor["n_defined_seeds"] = 0
    elif change == "too_few_events":
        floor["min_events_weaker_half"] = 19
    else:
        floor["n_defined_seeds"] = 0
        floor["realized_sigma"] = 0.0
        broken["se_up"][name]["se_up"] = 0.0
    record = floor_builder.decide(
        broken, invented["design"], invented["planning"]
    )
    assert record["cells"][name]["eligible"] is False
    assert record.get("stop_causes") is None
    assert record["ladder"] is not None
    assert name not in record["ladder"]["eligible"]
    assert set(record["ladder"]["eligible"]) == set(b2.LEVEL_CELLS) - {name}
    report = {
        entry["cell"]: entry for entry in record["surface"]["report_only"]
    }
    assert report[name]["reason"] == "floor ineligible"
    gated = {entry["cell"] for entry in record["surface"]["gated"]}
    assert name not in gated


def test_floor_refuses_a_truth_person_without_design_variables(
    invented, measured
):
    person = int(measured["truth"]["person_id"].iloc[0])
    design = invented["design"]
    design = design[design["person_id"] != person]
    with pytest.raises(AssertionError, match="design variables"):
        floor_builder.decide(measured, design, invented["planning"])


def test_measure_refuses_counts_that_differ_from_the_frozen_record(invented):
    with pytest.raises(AssertionError, match="source reproduction"):
        floor_builder.measure(
            invented["earnings"],
            invented["anchor_demo"],
            config=floor_builder.FloorConfig(b_household=2, workers=1),
            expected_counts=floor_builder.frozen_counts(),
        )


def test_frozen_counts_are_the_audits():
    assert floor_builder.frozen_counts() == {
        "full_anchor_persons": 23_134,
        "full_anchor_households": 8_907,
        "domain_persons": 13_542,
        "scored_rows_by_period": {
            "2010": 11_066,
            "2012": 10_165,
            "2014": 9_310,
        },
    }


def test_read_set_is_the_audits_80_files():
    pinned = floor_builder.read_set()
    assert len(pinned) == 80
    waves = sorted({int(n.split("/")[1]) for n in pinned if n[:6] == "family"})
    assert waves[0] == 1968 and waves[-1] == 2015
    assert "ind2023er/IND2023ER.txt" in pinned
    assert not any("2017" in name or "2019" in name for name in pinned)


# --------------------------------------------------------------------------
# The scorer, end to end
# --------------------------------------------------------------------------
@pytest.fixture(scope="module")
def scored(invented, cleared_floor):
    return scorer.run_score(
        invented["earnings"],
        invented["anchor_demo"],
        invented["design"],
        invented["nawi_2010"],
        cleared_floor,
        invented["planning"],
        config=scorer.ScoreConfig(b_design=4, workers=1),
        qrf_factory=_StochasticFactory(),
    )


def test_score_end_to_end(scored, cleared_floor):
    assert scored["outcome"] in b2.OUTCOMES
    assert set(scored["cells"]) == set(b2.CELLS)
    assert scored["gate"]["gated_cells"] == list(b2.LEVEL_CELLS)
    assert scored["gate"]["m"] == 6
    assert scored["gate"]["critical_value"] == b2.t_star(6, 10)
    assert scored["law"]["fit_seed"] == 5200
    assert scored["law"]["boundary"] == 2010
    assert scored["law"]["fit_input_max_period"] == 2010
    assert scored["config"]["design_stream"] == "[20261002, b, 4]"
    for name, cell in scored["cells"].items():
        assert cell["design_replicates"] == 4
        assert len(cell["side_a"]) == 5
        floor_cell = cleared_floor["cells"][name]
        assert cell["tolerance"] == floor_cell["tolerance"]
        assert cell["a_c"] == floor_cell["registered_estimation_ratio"] > 0
        if cell["se"] is not None:
            assert cell["se"] == pytest.approx(
                math.sqrt(
                    cell["se_boot"] ** 2 + cell["a_c"] * cell["se_up"] ** 2
                )
            )
        if cell["gap"] is not None and cell["metric"] == "log_ratio":
            assert cell["gap"] == pytest.approx(
                math.log(cell["projected_mean"] / cell["truth"])
            )
        elif cell["gap"] is not None:
            assert cell["gap"] == pytest.approx(
                cell["projected_mean"] - cell["truth"]
            )
        if not cell["gated"]:
            interval = cell["report_interval_95"]
            if cell["se"] is not None and cell["gap"] is not None:
                half = b2.t_star(1, 10) * cell["se"]
                assert interval == pytest.approx(
                    [cell["gap"] - half, cell["gap"] + half]
                )


def test_score_outcome_is_section_8s_on_its_own_cells(scored):
    cells = scored["cells"]
    recomputed = b2.gate_outcome(
        [
            b2.GatedCell(
                name=name,
                tolerance=cells[name]["tolerance"],
                full_valid=cells[name]["valid_full_support"],
                full_gap=cells[name]["gap"],
                side_a_valid=tuple(s["valid"] for s in cells[name]["side_a"]),
                side_a_gap=tuple(s["gap"] for s in cells[name]["side_a"]),
                se=cells[name]["se"],
                mc_error=cells[name]["mc_error"],
                design_undefined=cells[name]["design_undefined"],
                design_replicates=cells[name]["design_replicates"],
                household_undefined=cells[name]["household_undefined"],
                household_replicates=cells[name]["household_replicates"],
            )
            for name in scored["gate"]["gated_cells"]
        ],
        b2.t_star(6, 10),
    )
    assert recomputed["outcome"] == scored["outcome"]
    assert recomputed["seed_passes"] == scored["gate"]["seed_passes"]


def test_side_a_is_the_household_split_of_the_full_2011_anchor(
    invented, scored
):
    full = b2.full_anchor_frame(invented["anchor_demo"])
    domain = b2.domain_person_ids(invented["earnings"], full)
    for seed in b2.GATE_SEEDS:
        side = m6_scoring.side_a_person_ids(
            full, split_unit="household", seed=seed
        )
        assert scored["side_a_persons"][str(seed)] == len(set(side) & domain)


def test_side_a_scores_restrict_the_full_projection(invented, fit_2010):
    """Side A is a household split of the full 2011 anchor, intersected
    with the domain, scored on the full projection's draws."""
    context, draws = fit_2010["context"], fit_2010["draws"]
    full = b2.full_anchor_frame(invented["anchor_demo"])
    sides = scorer.side_a_scores(
        full, context.domain_ids, context.truth_support, draws
    )
    assert [side["seed"] for side in sides] == list(b2.GATE_SEEDS)
    households = full.set_index("person_id")["household_id"]
    for side in sides[:2]:
        chosen = m6_scoring.side_a_person_ids(
            full, split_unit="household", seed=side["seed"]
        )
        persons = set(chosen) & set(context.domain_ids)
        assert side["persons"] == len(persons)
        # Every household lies wholly on one side.
        kept = set(households.loc[sorted(chosen)])
        assert set(households[households.isin(kept)].index) == set(chosen)
        truth = context.truth_support
        values, draw_values = scorer.frame_set_values(
            truth[truth["person_id"].isin(persons)],
            [frame[frame["person_id"].isin(persons)] for frame in draws],
        )
        assert side["gap"] == scorer.set_gaps(values, draw_values)
        assert side["valid"] == {
            name: b2.frame_valid(
                values[name], [draw[name] for draw in draw_values]
            )
            for name in b2.CELLS
        }


def test_scorer_context_is_the_selectors_at_2010(fit_2010, selector_2010):
    context = fit_2010["context"]
    assert context.boundary == 2010
    assert context.domain_ids == selector_2010.domain_ids
    assert context.truth_support.equals(selector_2010.truth_support)
    assert context.initial_slice.equals(selector_2010.initial_slice)
    for frame in fit_2010["draws"]:
        assert frame[["person_id", "period"]].equals(
            context.truth_support[["person_id", "period"]]
        )


def test_design_replicate_is_rao_wu_on_b2s_stream(invented, fit_2010):
    """On fixed frames, design replicate b copies by b2's multiplicities;
    moving protocol v2's root changes nothing."""
    truth = fit_2010["context"].truth_support
    draws = fit_2010["draws"]
    design = _design_for(invented["person_wave"])
    design = design[design["person_id"].isin(truth["person_id"])]
    b2._worker_init({"design": design, "truth": truth, "draws": draws})
    try:
        first = scorer.design_replicate(2)
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(pv, "BOOTSTRAP_ROOT_SEED", 1)
            again = scorer.design_replicate(2)
    finally:
        b2._worker_init({})
    assert first == again
    mult = b2.design_multiplicities(design, 2, root=b2.ROOT_SEED)
    assert first["gaps"] == scorer.replicate_gaps(truth, draws, mult)


def test_scorer_refuses_a_floor_that_is_not_the_datas(invented, cleared_floor):
    for key in (
        "full_anchor_ids_sha256",
        "domain_ids_sha256",
        "truth_support_keys_sha256",
    ):
        wrong = json.loads(json.dumps(cleared_floor))
        wrong["domain"][key] = "0" * 64
        with pytest.raises(AssertionError, match="differs from the floor"):
            scorer.run_score(
                invented["earnings"],
                invented["anchor_demo"],
                invented["design"],
                invented["nawi_2010"],
                wrong,
                invented["planning"],
                config=scorer.ScoreConfig(b_design=1, workers=1),
                qrf_factory=_StochasticFactory(),
            )
    wrong = json.loads(json.dumps(cleared_floor))
    wrong["design"]["after_merges"]["clusters"] += 1
    with pytest.raises(AssertionError, match="design summary"):
        scorer.run_score(
            invented["earnings"],
            invented["anchor_demo"],
            invented["design"],
            invented["nawi_2010"],
            wrong,
            invented["planning"],
            config=scorer.ScoreConfig(b_design=1, workers=1),
            qrf_factory=_StochasticFactory(),
        )


@pytest.mark.parametrize(
    "field", ["merges", "scale_l", "design_degrees_of_freedom"]
)
def test_scorer_refuses_changed_design_before_fit(
    invented, cleared_floor, monkeypatch, field
):
    wrong = copy.deepcopy(cleared_floor)
    wrong["design"][field] = (
        [{"from_stratum": 1, "to_stratum": 2}]
        if field == "merges"
        else wrong["design"][field] + 1
    )
    monkeypatch.setattr(
        scorer, "fit_law", lambda *a, **k: pytest.fail("fit began")
    )
    with pytest.raises(AssertionError, match="design summary"):
        scorer.run_score(
            invented["earnings"],
            invented["anchor_demo"],
            invented["design"],
            invented["nawi_2010"],
            wrong,
            invented["planning"],
            config=scorer.ScoreConfig(b_design=1, workers=1),
        )


@pytest.mark.parametrize(
    "missing",
    [
        "e_b2",
        "planning_cell",
        "tolerance",
        "plain_units",
        "se_up",
        "replicates",
        "undefined",
        "a_c",
    ],
)
def test_scorer_refuses_missing_report_only_input_before_fit(
    invented, cleared_floor, monkeypatch, missing
):
    floor = copy.deepcopy(cleared_floor)
    planning = copy.deepcopy(invented["planning"])
    name = "earn_autocorr_lag2"
    assert name not in b2.LEVEL_CELLS
    if missing == "e_b2":
        del planning["cells"][name]["estimation_variance"]["e_b2"]
    elif missing == "planning_cell":
        del planning["cells"][name]
    elif missing in ("replicates", "undefined"):
        del floor["cells"][name]["se_up"][missing]
    else:
        key = "registered_estimation_ratio" if missing == "a_c" else missing
        del floor["cells"][name][key]
    monkeypatch.setattr(
        scorer, "fit_law", lambda *a, **k: pytest.fail("fit began")
    )
    with pytest.raises(ValueError, match="scoring inputs"):
        scorer.run_score(
            invented["earnings"],
            invented["anchor_demo"],
            invented["design"],
            invented["nawi_2010"],
            floor,
            planning,
            config=scorer.ScoreConfig(b_design=1, workers=1),
        )


def test_candidate_3_disclosure_is_carried_verbatim():
    expected = (
        "**Candidate 3 records a valid M6 pass; it certifies nothing about "
        "mortality drift.** The artifact records four passing seeds, q=0.55 "
        "and rho=−0.6. Fits use data through 2014; gated demographic flows "
        "cover 2015–2019 and earnings cover 2016/2018. The 2020–2022 window "
        "is diagnostic only. Certification is conditional on prior structural "
        "and same-holdout surface selection. The v4 point estimate "
        "`p_gate=0.9018301` clears 0.90 by 0.0018301, but its clearance is not "
        "statistically resolved: the reported jackknife SE is approximately "
        "0.013–0.019. Synthesized support, redrawn initial states and endogenous "
        "widowhood require the decision-5 successor gate."
    )
    assert b2.CANDIDATE_3_DISCLOSURE == expected
    # The floor and score both carry statements() in their records.
    assert floor_builder.statements()["candidate_3_disclosure"] == expected


def test_report_only_undefined_tolerance_and_se_are_published(
    invented, cleared_floor, fit_2010, monkeypatch
):
    floor = copy.deepcopy(cleared_floor)
    name = "earn_autocorr_lag2"
    floor["cells"][name]["tolerance"] = None
    floor["cells"][name]["plain_units"] = "undefined tolerance"
    floor["cells"][name]["se_up"]["se_up"] = None
    monkeypatch.setattr(scorer, "fit_law", lambda *a, **k: fit_2010["fitted"])
    result = scorer.run_score(
        invented["earnings"],
        invented["anchor_demo"],
        invented["design"],
        invented["nawi_2010"],
        floor,
        invented["planning"],
        config=scorer.ScoreConfig(b_design=2, workers=1),
    )
    cell = result["cells"][name]
    assert cell["gated"] is False
    assert cell["tolerance"] is None
    assert cell["within_tolerance"] is False
    assert cell["monte_carlo_rule"] is False
    assert cell["se"] is None and cell["report_interval_95"] is None
    assert all(side["within_tolerance"] is False for side in cell["side_a"])


def test_scorer_refuses_zero_gated_tolerance_before_fit(
    invented, cleared_floor, monkeypatch
):
    floor = copy.deepcopy(cleared_floor)
    floor["cells"][b2.LEVEL_CELLS[0]]["tolerance"] = 0
    monkeypatch.setattr(
        scorer, "fit_law", lambda *a, **k: pytest.fail("fit began")
    )
    with pytest.raises(ValueError, match="scoring inputs"):
        scorer.run_score(
            invented["earnings"],
            invented["anchor_demo"],
            invented["design"],
            invented["nawi_2010"],
            floor,
            invented["planning"],
            config=scorer.ScoreConfig(b_design=1, workers=1),
        )


# --------------------------------------------------------------------------
# Preconditions and registered settings
# --------------------------------------------------------------------------
@pytest.mark.parametrize("script", [floor_builder, scorer])
def test_scripts_refuse_without_registration_or_commit(script):
    with pytest.raises(RuntimeError, match="registration"):
        script.main(["--registration-id", " ", "--expected-commit", "abc"])
    with pytest.raises(RuntimeError):
        script.main(["--registration-id", "r1", "--expected-commit", "0" * 40])


@pytest.mark.parametrize("script", [floor_builder, scorer])
def test_scripts_refuse_an_existing_output(script, monkeypatch, tmp_path):
    existing = tmp_path / "out.json"
    existing.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(b2, "require_clean_head", lambda root, commit: commit)
    monkeypatch.setattr(script, "OUTPUT", existing)
    with pytest.raises(FileExistsError):
        script.main(["--registration-id", "r1", "--expected-commit", "h"])


def test_scorer_refuses_an_uncommitted_floor(monkeypatch, tmp_path):
    monkeypatch.setattr(b2, "require_clean_head", lambda root, commit: commit)
    monkeypatch.setattr(scorer, "OUTPUT", tmp_path / "score.json")
    missing = ROOT / "docs" / "design" / "track_b_b2_floor_absent.json"
    with pytest.raises(RuntimeError, match="not committed"):
        scorer.main(
            [
                "--registration-id",
                "r1",
                "--expected-commit",
                "h",
                "--floor-artifact",
                str(missing),
            ]
        )


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _valid_floor_record(head: str) -> dict:
    return {
        "schema": floor_builder.SCHEMA,
        "outcome": b2.LADDER_CLEARED,
        "candidate_runs_permitted": True,
        "registration_id": "r1",
        "repository_head": head,
        "addendum_sha256": _sha(floor_builder.ADDENDUM),
        "planning_values_sha256": _sha(floor_builder.PLANNING),
        "counts_record_sha256": _sha(floor_builder.COUNTS),
        "code_sha256": {
            path: _sha(ROOT / path) for path in scorer.SHARED_CODE
        },
    }


@pytest.mark.parametrize(
    "change, message",
    [
        ({"schema": "other"}, "schema"),
        ({"outcome": b2.WEAK_POWER_OR_VACUITY}, "does not permit"),
        ({"outcome": "unregistered outcome"}, "does not permit"),
        ({"candidate_runs_permitted": False}, "does not permit"),
        ({"registration_id": "r2"}, "another registration"),
        ({"repository_head": "0" * 40}, "ancestor"),
        ({"addendum_sha256": "0" * 64}, "addendum_sha256"),
        ({"planning_values_sha256": "0" * 64}, "planning_values"),
        ({"counts_record_sha256": "0" * 64}, "counts_record"),
    ],
)
def test_scorer_checks_the_floor_record(change, message):
    head = b2.git(ROOT, "rev-parse", "HEAD")
    record = _valid_floor_record(head)
    scorer.check_floor_record(record, "r1", head)
    with pytest.raises(RuntimeError, match=message):
        scorer.check_floor_record({**record, **change}, "r1", head)


def test_scorer_refuses_shared_code_changed_since_the_floor():
    head = b2.git(ROOT, "rev-parse", "HEAD")
    record = _valid_floor_record(head)
    for path in scorer.SHARED_CODE:
        changed = json.loads(json.dumps(record))
        changed["code_sha256"][path] = "0" * 64
        with pytest.raises(RuntimeError, match="changed since"):
            scorer.check_floor_record(changed, "r1", head)


def test_statements_carry_section_13s_items():
    statements = floor_builder.statements()
    assert statements["headline_scope"] == b2.HEADLINE_SCOPE
    assert "levels and zero rates only" in statements["headline_scope"]
    assert "Not a 2010-vintage forecast" in statements["fallback_scope"]
    assert "25-61" in statements["section_5_3"]
    assert "recession" in statements["planning_caveat"]
    assert "collection wave" in statements["age_convention"]
    assert statements["wage_vintage_label"] != "ols_log_nawi_2005_2014"
    assert "6110674288" in statements["b1"]
    assert "6113379406" in statements["b1"]
    assert b2.B1_LABEL in statements["b1"]
    assert "no candidate output, projection or selection ledger" in (
        statements["reads"]
    )
    assert statements["candidate_3_disclosure"] == b2.CANDIDATE_3_DISCLOSURE


@pytest.mark.parametrize("module", ["track_b_b2_floor", "track_b_b2_score"])
@pytest.mark.parametrize("variable", b2.THREAD_VARIABLES)
def test_entry_points_refuse_more_than_one_thread_first(
    monkeypatch, module, variable
):
    """A launch with any thread variable above 1 stops before it reads,
    checks or writes anything (the projection would hang)."""
    script = __import__(module)
    for name in b2.THREAD_VARIABLES:
        monkeypatch.setenv(name, "1")
    monkeypatch.setenv("OMP_WAIT_POLICY", "PASSIVE")
    monkeypatch.setenv(variable, "4")

    def untouched(*args, **kwargs):
        raise AssertionError("ran before the thread guard")

    monkeypatch.setattr(b2, "require_registration", untouched)
    monkeypatch.setattr(b2, "require_clean_head", untouched)
    monkeypatch.setattr(b2, "committed_sha256", untouched)
    with pytest.raises(RuntimeError, match=variable):
        script.main(["--registration-id", "1", "--expected-commit", "x"])


@pytest.mark.parametrize("module", ["track_b_b2_floor", "track_b_b2_score"])
@pytest.mark.parametrize("workers", [0, 5, 18, -1])
def test_entry_points_refuse_workers_outside_one_to_four(
    monkeypatch, module, workers
):
    """With one thread per process, at most four workers keep a run inside
    the shared host's cap; the check runs before anything else."""
    script = __import__(module)
    for name in b2.THREAD_VARIABLES:
        monkeypatch.setenv(name, "1")
    monkeypatch.setenv("OMP_WAIT_POLICY", "PASSIVE")

    def untouched(*args, **kwargs):
        raise AssertionError("ran before the worker check")

    monkeypatch.setattr(b2, "require_registration", untouched)
    monkeypatch.setattr(b2, "require_clean_head", untouched)
    monkeypatch.setattr(b2, "committed_sha256", untouched)
    with pytest.raises(RuntimeError, match="workers"):
        script.main(
            [
                "--registration-id",
                "1",
                "--expected-commit",
                "x",
                "--workers",
                str(workers),
            ]
        )


@pytest.mark.parametrize("workers", [1, 2, 3, 4])
def test_one_to_four_workers_are_accepted(workers):
    assert b2.require_workers(workers) == workers
    for bad in (True, 2.0, "4"):
        with pytest.raises(RuntimeError, match="workers"):
            b2.require_workers(bad)


def test_the_attempt_log_is_one_shot_and_records_each_stage(tmp_path):
    """The attempt log is created exclusively and every later stage is
    appended, so an interrupted run's last stage survives on disk."""
    path = tmp_path / "logs" / "attempt.jsonl"
    try:
        b2.open_attempt(path, {"registration_id": "r1"})
        b2.progress("fitting candidate 3's law at origin 2010")
        b2.progress("full-support cells")
        with pytest.raises(FileExistsError):
            b2.open_attempt(path, {"registration_id": "r1"})
    finally:
        b2.close_attempt()
    b2.progress("after close")
    lines = [json.loads(line) for line in path.read_text().splitlines()]
    assert lines[0]["attempt"] == {"registration_id": "r1"}
    assert [line.get("stage") for line in lines[1:]] == [
        "fitting candidate 3's law at origin 2010",
        "full-support cells",
    ]
    assert all("utc" in line for line in lines)


def test_scorer_refuses_when_an_attempt_was_made(monkeypatch, tmp_path):
    attempt = tmp_path / "attempt.jsonl"
    attempt.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(b2, "require_clean_head", lambda root, commit: commit)
    monkeypatch.setattr(scorer, "OUTPUT", tmp_path / "score.json")
    monkeypatch.setattr(scorer, "ATTEMPT", attempt)

    def untouched(*args, **kwargs):
        raise AssertionError("read past the attempt check")

    monkeypatch.setattr(b2, "committed_sha256", untouched)
    with pytest.raises(FileExistsError, match="attempted"):
        scorer.main(["--registration-id", "r1", "--expected-commit", "h"])


@pytest.mark.parametrize("module", ["track_b_b2_floor", "track_b_b2_score"])
@pytest.mark.parametrize("jobs", ["8", "0", ""])
def test_entry_points_refuse_fit_jobs_outside_one_to_four(
    monkeypatch, module, jobs
):
    script = __import__(module)
    monkeypatch.setenv("POPULACE_FIT_N_JOBS", jobs)

    def untouched(*args, **kwargs):
        raise AssertionError("ran before the thread guard")

    monkeypatch.setattr(b2, "require_registration", untouched)
    with pytest.raises(RuntimeError, match="POPULACE_FIT_N_JOBS"):
        script.main(["--registration-id", "1", "--expected-commit", "x"])


def test_the_attempt_log_opens_after_the_data_free_checks(
    monkeypatch, tmp_path
):
    """The log is created after every check that needs no PSID data, and
    before any PSID data is read."""
    order = []
    floor_path = tmp_path / "floor_artifact.json"
    floor_path.write_text("{}", encoding="utf-8")
    psid = tmp_path / "psid"
    pe_us = tmp_path / "pe_us"
    psid.mkdir()
    pe_us.mkdir()
    monkeypatch.setenv(floor_builder.PSID_ENV, str(psid))
    monkeypatch.setenv(scorer.PE_US_ENV, str(pe_us))
    monkeypatch.setattr(b2, "require_clean_head", lambda root, commit: commit)
    monkeypatch.setattr(b2, "committed_sha256", lambda root, path: "pin")
    monkeypatch.setattr(scorer, "check_floor_record", lambda *args: None)
    monkeypatch.setattr(scorer, "assert_registered", lambda config: None)
    monkeypatch.setattr(pv, "runtime_record", lambda: {})

    def scoring_inputs(*args):
        assert not scorer.ATTEMPT.exists()
        order.append("scoring inputs")

    def nawi(directory):
        assert not scorer.ATTEMPT.exists()
        order.append("nawi")
        return {}, {}

    class Stop(Exception):
        pass

    def read_inputs(*args):
        lines = scorer.ATTEMPT.read_text().splitlines()
        assert json.loads(lines[0])["attempt"]["registration_id"] == "r1"
        order.append("read inputs")
        raise Stop

    monkeypatch.setattr(scorer, "check_scoring_inputs", scoring_inputs)
    monkeypatch.setattr(scorer, "nawi_2010", nawi)
    monkeypatch.setattr(floor_builder, "read_inputs", read_inputs)
    try:
        with pytest.raises(Stop):
            scorer.main(
                [
                    "--registration-id",
                    "r1",
                    "--expected-commit",
                    "h",
                    "--floor-artifact",
                    str(floor_path),
                ]
            )
    finally:
        b2.close_attempt()
    assert order == ["scoring inputs", "nawi", "read inputs"]


def test_a_scorer_replicate_copies_past_the_pinned_scale():
    """The scorer's own replicate, at L = 1,001 (merged strata of 2, 8, 12
    and 14 clusters): every copy count passes 1,000 and the replicate is
    defined."""
    rows, design_rows, person = [], [], 0
    for stratum, clusters in enumerate((2, 8, 12, 14), start=1):
        for cluster in range(clusters):
            person += 1
            design_rows.append(
                {"person_id": person, "stratum": stratum, "cluster": cluster}
            )
            for year in b2.SCORED_PERIODS:
                rows.append(
                    {
                        "person_id": person,
                        "period": year,
                        "cohort": "prime" if person % 2 else "older",
                        "weight": float(1 + person % 4),
                        "earnings": (
                            0.0
                            if person % 5 == 0
                            else float(2000 + 97 * person + year)
                        ),
                    }
                )
    truth = pd.DataFrame(rows)
    draws = [
        truth.assign(earnings=truth["earnings"] * factor)
        for factor in (0.9, 1.0, 1.1)
    ]
    design = pd.DataFrame(design_rows)
    assert b2.design_summary(design)["scale_l"] == 1001
    payload = {"design": design, "truth": truth, "draws": draws}
    multiplicity = b2.design_multiplicities(design, 0, root=b2.ROOT_SEED)
    assert min(c for c in multiplicity.values() if c) >= pv.ID_SCALE
    (result,) = b2.run_replicates(scorer.design_replicate, 1, payload, 1)
    assert "failed" not in result
    assert result["replicate"] == 0
