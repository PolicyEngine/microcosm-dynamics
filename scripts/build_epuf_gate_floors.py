"""Pre-lock floors for the proposed EPUF covered-earnings gate.

Writes ``runs/epuf_gate_floors_v1.json`` (exclusive-create, with the
``.env.json`` sidecar) and ``runs/epuf_gate_floors_v1.inputs.json``.
The artifact holds, for every window cell of
:mod:`populace_dynamics.harness.epuf_cells`:

- the EPUF reference value and EPUF's own sampling sd;
- the real-PSID value on the gate's support and the bridge (PSID minus
  EPUF);
- the 100 real-data floor replicates, the tolerance and the realised
  sigma (:mod:`populace_dynamics.harness.epuf_gate`);
- the acceptance interval, the demotion reason or the gated flag, and
  the faithful-candidate pass probability;
- the real gate-seed holdouts scored as a training copy, and the bite
  demonstrations (perturbed real data).

It also holds the EPUF-only reference values of the report-only career
tranche, on true EPUF careers and on EPUF careers masked the way the
repository's career assembler builds a PSID career.

**Candidate-blind.** This builder generates no candidate and imports no
generator: it reads EPUF and, through the existing loaders
``data.family.family_earnings_panel`` and
``data.deaths.read_death_records``, the real PSID panel of gate 1's
view. The partition rules, ``k``, the caps and the bite doses are code
constants committed before the first PSID floor was computed.

Usage::

    uv run python scripts/build_epuf_gate_floors.py --stage epuf   # EPUF only
    uv run python scripts/build_epuf_gate_floors.py                # full build
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from collections.abc import Callable, Mapping
from pathlib import Path

import numpy as np
import pandas as pd

from populace_dynamics.artifacts import write_new
from populace_dynamics.cola_track_a.statutory import captured_ssa_parameters
from populace_dynamics.data import epuf
from populace_dynamics.harness import epuf_gate as gate
from populace_dynamics.harness.epuf_cells import (
    CAREER_AGES,
    CAREER_COHORT_BANDS,
    COHORT_BANDS,
    SEXES,
    WINDOW_YEARS,
    WindowArrays,
    career_cells,
    cell_ids,
    mask_as_career_assembler,
    metric,
    transform,
    window_frame,
)
from populace_dynamics.harness.epuf_operator import (
    CONSTANTS_SHA256,
    disclosure_constants,
    epuf_measure,
)

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "runs" / "epuf_gate_floors_v1.json"
INPUTS = ROOT / "runs" / "epuf_gate_floors_v1.inputs.json"
SCHEMA_VERSION = "epuf_gate_floors.v1"

#: Gate 1's locked view filter (gates.yaml views.psid_family_earnings_*).
AGE_MIN, AGE_MAX = 25, 59
PERIOD_MIN, PERIOD_MAX = 1998, 2022
#: The filtered panel's committed size (runs/noise_floor_psid_family_9822.json).
PANEL_REFERENCE = "runs/noise_floor_psid_family_9822.json"
GATE1_RUN = "runs/gate1_rank_knn_v5.json"
#: A support person's anchor (last in-filter period) must lie after the
#: window, so that every window value of a candidate is generated.
MIN_ANCHOR_PERIOD = 2006
PSID_SEX_LABELS = {"male": "men", "female": "women"}
EPUF_SEX_LABELS = {1: "men", 2: "women"}

EPUF_GROUPS = 50
EPUF_GROUP_SEED = 20261001

#: Bite demonstrations: perturbations of real PSID histories, each
#: scored on the 20 gate holdouts exactly as a candidate would be.
BITE_SEEDS = tuple(range(50))
BITE_SEED_BASE = 7300
BITE_REQUIRED_FAIL_SHARE = 0.90
BD1_SHARES = (0.10, 0.05)
BD3_RANK_ABOVE = 0.92
BD3_MOVE_PROBABILITY = 0.5
BD3_TARGET_RANKS = (0.5, 0.92)
BD4_ZERO_PROBABILITY = 0.03
#: Which bite a gated family needs to see fail before the gate may lock.
BITE_REQUIREMENT = {
    "persistence": "bd1_persistence_loss_0.10",
    "tail": "bd3_top_tail_compression",
    "participation": "bd4_participation_loss",
}

DERIVATION_CORE = (
    "src/populace_dynamics/data/epuf.py",
    "src/populace_dynamics/harness/epuf_operator.py",
    "src/populace_dynamics/harness/epuf_cells.py",
    "src/populace_dynamics/harness/epuf_gate.py",
    "scripts/build_epuf_gate_floors.py",
)

CONCEPT_DELTAS = [
    {
        "delta": "deaths, departures and arrivals",
        "direction": (
            "EPUF records none of them, so an EPUF year without earnings "
            "may follow death or precede arrival"
        ),
        "handling": (
            "every statistic conditions on covered earnings at one or both "
            "ends of its span; what remains is in the bridge"
        ),
    },
    {
        "delta": "noncovered employment",
        "direction": (
            "PSID labor income counts it; EPUF shows no earnings (6.4 "
            "percent of 2006 workers were noncovered, Compson 2011 Table 3)"
        ),
        "handling": "in the bridge; the repository's crosswalk is unbuilt",
    },
    {
        "delta": "frame",
        "direction": (
            "the PSID panel is heads and spouses of responding families who "
            "stay through 2006; EPUF is every Social Security number issued "
            "before 2007"
        ),
        "handling": "in the bridge; cells are within sex and cohort band",
    },
    {
        "delta": "reporting",
        "direction": (
            "PSID earnings are survey reports and EPUF's are employer and "
            "tax filings; whether that lowers the PSID's rank persistence "
            "is measured by the r6 bridge, not assumed"
        ),
        "handling": "in the bridge",
    },
    {
        "delta": "birth year",
        "direction": (
            "the PSID birth year is derived from age at interview and can "
            "sit one year below EPUF's year of birth"
        ),
        "handling": "nine-year cohort bands; in the bridge",
    },
    {
        "delta": "posting",
        "direction": (
            "EPUF 2005-2006 are short from late posting and 1998-2004 drift "
            "down slightly against the Supplement (Compson 2012)"
        ),
        "handling": "the window ends in 2004; the drift is in the bridge",
    },
    {
        "delta": "disclosure",
        "direction": "EPUF values are bottom-coded, banded and rounded",
        "handling": "the same operator is applied to PSID-side earnings",
    },
]


# --- splits ---------------------------------------------------------------


def holdout_mask(
    universe_ids: np.ndarray, *, seed: int, fraction: float
) -> np.ndarray:
    """Which persons of the sorted universe a split draws.

    Identical to ``populace_dynamics.harness.panel.split_panel_by_person``
    on a panel with those persons (the gate-1 split function); the
    builder asserts the equality on the gate seeds.
    """
    return np.random.default_rng(seed).random(len(universe_ids)) < fraction


def _sha256_ids(ids: np.ndarray) -> str:
    text = "\n".join(str(int(value)) for value in np.sort(ids))
    return hashlib.sha256(text.encode()).hexdigest()


# --- EPUF side ------------------------------------------------------------


def wage_bases() -> dict[int, float]:
    return {
        year: float(row["wage_base"])
        for year, row in disclosure_constants().items()
    }


def epuf_window(
    demographic: pd.DataFrame, annual: pd.DataFrame
) -> tuple[WindowArrays, dict[str, object]]:
    """EPUF's window frame: every person with a coded sex in the bands."""
    persons = pd.DataFrame(
        {
            "person_id": demographic["person_id"],
            "sex": demographic["sex"].map(EPUF_SEX_LABELS),
            "birth_year": demographic["birth_year"],
            "weight": 1.0,
        }
    )
    frame = window_frame(annual, persons, wage_bases=wage_bases())
    counts = {
        "n_persons": int(len(frame)),
        "n_sex_unspecified_dropped": int((demographic["sex"] == 3).sum()),
        "by_sex_and_band": _support_counts(frame),
    }
    return WindowArrays(frame, wage_bases=wage_bases()), counts


def _support_counts(frame: pd.DataFrame) -> dict[str, int]:
    out = {}
    for sex in SEXES:
        for band, (low, high) in COHORT_BANDS.items():
            out[f"{sex}.{band}"] = int(
                (
                    (frame["sex"] == sex)
                    & frame["birth_year"].between(low, high)
                ).sum()
            )
    return out


def epuf_sampling_sd(arrays: WindowArrays) -> dict[str, float]:
    """EPUF's own sampling sd per cell, by random groups.

    Persons are dealt at random into 50 groups; a cell's sd is the sd of
    its 50 transformed group values over the square root of 50.
    """
    rng = np.random.default_rng(EPUF_GROUP_SEED)
    group = rng.integers(0, EPUF_GROUPS, size=len(arrays))
    values: dict[str, list[float]] = {cell_id: [] for cell_id in cell_ids()}
    for index in range(EPUF_GROUPS):
        for cell_id, cell in arrays.cells(group == index).items():
            values[cell_id].append(transform(cell_id, cell.value))
    return {
        cell_id: float(np.std(series, ddof=1) / np.sqrt(EPUF_GROUPS))
        for cell_id, series in values.items()
    }


def career_reference(
    demographic: pd.DataFrame, annual: pd.DataFrame
) -> dict[str, object]:
    """EPUF-only reference values of the report-only career tranche."""
    low = min(a for a, _ in CAREER_COHORT_BANDS.values())
    high = max(b for _, b in CAREER_COHORT_BANDS.values())
    persons = demographic[
        demographic["sex"].isin(EPUF_SEX_LABELS)
        & demographic["birth_year"].between(low, high)
    ].reset_index(drop=True)
    years = np.arange(epuf.EPUF_FIRST_YEAR, epuf.EPUF_LAST_YEAR + 1)
    annual = annual[annual["person_id"].isin(persons["person_id"])]
    row = pd.Series(
        np.arange(len(persons)), index=persons["person_id"].to_numpy()
    )
    matrix = np.zeros((len(persons), len(years)), dtype=np.float64)
    matrix[
        row.loc[annual["person_id"].to_numpy()].to_numpy(),
        annual["year"].to_numpy() - years[0],
    ] = annual["earnings"].to_numpy()
    masked = mask_as_career_assembler(matrix, years)
    nawi = captured_ssa_parameters().nawi
    out: dict[str, object] = {}
    for sex_code, sex in EPUF_SEX_LABELS.items():
        for band, (band_low, band_high) in CAREER_COHORT_BANDS.items():
            select = (
                (persons["sex"] == sex_code)
                & persons["birth_year"].between(band_low, band_high)
            ).to_numpy()
            birth = persons.loc[select, "birth_year"].to_numpy()
            kwargs = dict(wage_bases=wage_bases(), nawi=nawi)
            out[f"{sex}.{band}"] = {
                "epuf": career_cells(matrix[select], years, birth, **kwargs),
                "epuf_masked_as_career_assembler": career_cells(
                    masked[select], years, birth, **kwargs
                ),
            }
    return out


# --- PSID side ------------------------------------------------------------


def psid_support() -> tuple[pd.DataFrame, np.ndarray, dict[str, object]]:
    """The gate's PSID support, its split universe and its counts.

    Reads the real PSID only through the existing loaders. The universe
    is every person of gate 1's filtered panel (the persons a gate split
    draws from); the support is the subset the window cells score.
    """
    from populace_dynamics.data.deaths import read_death_records
    from populace_dynamics.data.family import family_earnings_panel

    raw = family_earnings_panel()
    panel = raw[
        (raw["age"] >= AGE_MIN)
        & (raw["age"] <= AGE_MAX)
        & (raw["period"] >= PERIOD_MIN)
        & (raw["period"] <= PERIOD_MAX)
        & (raw["weight"] > 0)
    ].reset_index(drop=True)
    reference = json.loads((ROOT / PANEL_REFERENCE).read_text())
    observed = {
        "n_person_periods": int(len(panel)),
        "n_persons": int(panel["person_id"].nunique()),
    }
    expected = {key: int(reference[key]) for key in observed}
    if observed != expected:
        raise ValueError(
            f"filtered panel {observed} is not gate 1's {expected} "
            f"({PANEL_REFERENCE})"
        )
    sex = read_death_records()[["person_id", "sex"]]
    return support_from_panel(panel, sex)


def support_from_panel(
    panel: pd.DataFrame, sex_records: pd.DataFrame
) -> tuple[pd.DataFrame, np.ndarray, dict[str, object]]:
    """Apply the support rules to a filtered panel (real or synthetic)."""
    if panel.duplicated(["person_id", "period"]).any():
        raise ValueError("panel has duplicate person-periods")
    universe = np.sort(panel["person_id"].unique())
    grouped = panel.groupby("person_id")
    anchor = grouped["period"].max()
    in_window = panel[panel["period"].isin(WINDOW_YEARS)]
    n_window = in_window.groupby("person_id")["period"].nunique()
    all_four = n_window.reindex(universe, fill_value=0) == len(WINDOW_YEARS)
    late_anchor = anchor.reindex(universe) >= MIN_ANCHOR_PERIOD
    birth = np.floor(
        (panel["period"] - panel["age"]).groupby(panel["person_id"]).median()
        + 0.5
    ).astype(int)
    coded = sex_records[sex_records["sex"].isin(PSID_SEX_LABELS)]
    coded = coded.drop_duplicates(["person_id", "sex"])
    if coded["person_id"].duplicated().any():
        raise ValueError("a person has two coded sexes")
    sex = (
        coded.set_index("person_id")["sex"]
        .map(PSID_SEX_LABELS)
        .reindex(universe)
    )
    low = min(a for a, _ in COHORT_BANDS.values())
    high = max(b for _, b in COHORT_BANDS.values())
    in_bands = birth.reindex(universe).between(low, high)
    keep = (
        all_four.to_numpy()
        & late_anchor.to_numpy()
        & sex.notna().to_numpy()
        & in_bands.to_numpy()
    )
    ids = universe[keep]
    weight = (
        panel[panel["period"] == WINDOW_YEARS[-1]]
        .set_index("person_id")["weight"]
        .reindex(ids)
    )
    persons = pd.DataFrame(
        {
            "person_id": ids,
            "sex": sex.reindex(ids).to_numpy(),
            "birth_year": birth.reindex(ids).to_numpy(),
            "weight": weight.to_numpy(),
        }
    )
    rows = in_window[in_window["person_id"].isin(ids)]
    measured = pd.DataFrame(
        {
            "person_id": rows["person_id"].to_numpy(),
            "year": rows["period"].to_numpy(),
            "earnings": _measure_rows(rows),
        }
    )
    frame = window_frame(measured, persons, wage_bases=wage_bases())
    counts = {
        "n_universe_persons": int(len(universe)),
        "n_present_all_four_years": int(all_four.sum()),
        "n_and_anchor_2006_or_later": int((all_four & late_anchor).sum()),
        "n_and_sex_coded": int(
            (
                all_four.to_numpy()
                & late_anchor.to_numpy()
                & sex.notna().to_numpy()
            ).sum()
        ),
        "n_support_persons": int(len(frame)),
        "by_sex_and_band": _support_counts(frame),
    }
    return frame, universe, counts


def _measure_rows(rows: pd.DataFrame) -> np.ndarray:
    """Apply the EPUF operator to window rows, year by year, in place."""
    out = np.empty(len(rows), dtype=np.float64)
    periods = rows["period"].to_numpy()
    earnings = rows["earnings"].to_numpy(dtype=np.float64)
    for year in WINDOW_YEARS:
        select = periods == year
        out[select] = epuf_measure(earnings[select], year)
    return out


# --- floors ---------------------------------------------------------------


def _finite(value):
    """Replace non-finite floats with None, recursively (strict JSON)."""
    if isinstance(value, dict):
        return {key: _finite(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_finite(item) for item in value]
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def _values(cells) -> dict[str, float]:
    return {cell_id: cell.value for cell_id, cell in cells.items()}


def _events(cells) -> dict[str, int]:
    return {cell_id: cell.events for cell_id, cell in cells.items()}


def build_floors(
    arrays: WindowArrays,
    universe: np.ndarray,
    epuf_values: Mapping[str, float],
    epuf_sd: Mapping[str, float],
    *,
    n_replicates: int = gate.N_FLOOR_REPLICATES,
    progress: Callable[[str], None] | None = None,
) -> dict[str, object]:
    """Floors, tolerances, partition, OC and the training copy.

    ``arrays`` is the PSID support (real or, in tests, synthetic);
    ``universe`` the sorted person ids every split draws from.
    """
    ids = cell_ids()
    position = np.searchsorted(universe, arrays.person_id)
    if not (universe[position] == arrays.person_id).all():
        raise ValueError("support persons are not all in the split universe")

    def on(seed: int, fraction: float) -> np.ndarray:
        return holdout_mask(universe, seed=seed, fraction=fraction)[position]

    full = arrays.cells()
    replicates: dict[str, list[float]] = {cell_id: [] for cell_id in ids}
    common_terms: dict[str, list[float]] = {cell_id: [] for cell_id in ids}
    min_events = {cell_id: np.iinfo(np.int64).max for cell_id in ids}

    def track(cells) -> None:
        for cell_id, count in _events(cells).items():
            min_events[cell_id] = min(min_events[cell_id], count)

    for b in range(n_replicates):
        half = on(gate.half_split_seed(b), gate.HALF_FRACTION)
        side_a, side_b = arrays.cells(half), arrays.cells(~half)
        track(side_a)
        track(side_b)
        holdouts: dict[str, list[float]] = {cell_id: [] for cell_id in ids}
        complements: dict[str, list[float]] = {cell_id: [] for cell_id in ids}
        for j in range(len(gate.GATE_SEEDS)):
            drawn = on(gate.holdout_split_seed(b, j), gate.HOLDOUT_FRACTION)
            held, rest = arrays.cells(drawn), arrays.cells(~drawn)
            track(held)
            for cell_id in ids:
                holdouts[cell_id].append(held[cell_id].value)
                complements[cell_id].append(rest[cell_id].value)
        for cell_id in ids:
            common, averaging = gate.floor_terms(
                cell_id,
                side_a[cell_id].value,
                side_b[cell_id].value,
                holdouts[cell_id],
                complements[cell_id],
            )
            replicates[cell_id].append(common + averaging)
            common_terms[cell_id].append(common)
        if progress and (b + 1) % 10 == 0:
            progress(f"floor replicate {b + 1}/{n_replicates}")

    gate_seed_cells = {}
    for seed in gate.GATE_SEEDS:
        held = arrays.cells(on(seed, gate.HOLDOUT_FRACTION))
        track(held)
        gate_seed_cells[seed] = held

    floors: dict[str, gate.CellFloor] = {}
    cell_block: dict[str, dict[str, object]] = {}
    for cell_id in ids:
        series = np.asarray(replicates[cell_id], dtype=np.float64)
        psid_value = full[cell_id].value
        epuf_value = float(epuf_values[cell_id])
        bridge = transform(cell_id, psid_value) - transform(
            cell_id, epuf_value
        )
        defined = bool(np.isfinite(series).all() and np.isfinite(bridge))
        t = gate.tolerance(series) if defined else float("nan")
        sigma = gate.realized_sigma(series) if defined else float("nan")
        floors[cell_id] = gate.CellFloor(
            cell_id=cell_id,
            defined=defined,
            min_events=int(min_events[cell_id]),
            bridge=float(bridge),
            t=t,
            sigma=sigma,
            epuf_sampling_sd=float(epuf_sd[cell_id]),
        )
        magnitude = np.abs(series)
        cell_block[cell_id] = {
            "metric": metric(cell_id),
            "cap": gate.CAPS[metric(cell_id)],
            "epuf_value": epuf_value,
            "epuf_sampling_sd": float(epuf_sd[cell_id]),
            "psid_value": float(psid_value),
            "psid_n": int(full[cell_id].n),
            "bridge_psid_minus_epuf": float(bridge),
            "min_events": int(min_events[cell_id]),
            "floor": {
                "replicates": [float(value) for value in series],
                "mean_abs": float(magnitude.mean()) if defined else None,
                "sd_abs": float(magnitude.std(ddof=1)) if defined else None,
                "realized_sigma": sigma if defined else None,
                "shared_noise_variance_share": (
                    float(
                        np.mean(np.square(common_terms[cell_id]))
                        / np.mean(np.square(series))
                    )
                    if defined and np.any(series != 0)
                    else None
                ),
                "tolerance": t if defined else None,
            },
        }

    reasons = {
        cell_id: gate.demotion_reason(floor)
        for cell_id, floor in floors.items()
    }
    gated, report_only = gate.adopt_ladder(reasons)

    per_seed_real = {
        seed: _values(cells) for seed, cells in gate_seed_cells.items()
    }
    registered = {}
    for cell_id in ids:
        floor = floors[cell_id]
        block = cell_block[cell_id]
        block["eligibility"] = reasons[cell_id] or "eligible"
        block["gated"] = cell_id in gated
        if cell_id in report_only:
            block["report_reason"] = report_only[cell_id]
        if not floor.defined:
            continue
        lower, upper = gate.hull(floor.bridge, floor.t)
        block["lower"] = lower
        block["upper"] = upper
        block["minimum_detectable_gap_80"] = gate.minimum_detectable_gap(
            floor.bridge, floor.t, floor.sigma
        )
        block["faithful_pass_probability"] = gate.faithful_pass_probability(
            floor.bridge, floor.sigma, lower, upper
        )
        block["real_gate_holdouts"] = gate.score_cell(
            cell_id,
            [per_seed_real[seed][cell_id] for seed in gate.GATE_SEEDS],
            epuf_value=block["epuf_value"],
            lower=lower,
            upper=upper,
        )
        if cell_id in gated:
            registered[cell_id] = {
                "epuf_value": block["epuf_value"],
                "psid_value": block["psid_value"],
                "lower": lower,
                "upper": upper,
            }

    analytic = float(
        np.prod(
            [cell_block[c]["faithful_pass_probability"] for c in gated] or [1]
        )
    )
    joint = [
        all(
            cell_block[c]["lower"]
            <= floors[c].bridge + replicates[c][b]
            <= cell_block[c]["upper"]
            for c in gated
        )
        for b in range(n_replicates)
    ]
    training_copy = gate.score_run(per_seed_real, registered)
    status = (
        "lockable_pending_referee_round"
        if gated
        else "report_only_bridge_dominated"
    )
    return _finite(
        {
            "cells": cell_block,
            "gate_partition": {
                "status": status,
                "gated": gated,
                "n_gated": len(gated),
                "report_only": report_only,
                "n_report_only": len(report_only),
            },
            "registered": registered,
            "faithful_candidate_oc": {
                "method": (
                    "per cell, the normal probability that bridge + noise "
                    "falls inside the interval at the cell's realised sigma; "
                    "analytic_product multiplies the gated cells; "
                    "empirical_joint is the share of floor replicates in "
                    "which every gated cell's bridge + e_b is inside"
                ),
                "analytic_product": analytic,
                "empirical_joint": float(np.mean(joint)) if gated else None,
                "n_replicates": n_replicates,
                "pause_below": gate.OC_PAUSE,
                "pause": bool(gated) and analytic < gate.OC_PAUSE,
            },
            "training_copy": training_copy,
            "real_gate_seed_values": {
                str(seed): values for seed, values in per_seed_real.items()
            },
        }
    )


# --- bite demonstrations --------------------------------------------------


def _year_columns() -> list[str]:
    return [f"e{year}" for year in WINDOW_YEARS]


def perturb_persistence(
    frame: pd.DataFrame, rng: np.random.Generator, share: float
) -> pd.DataFrame:
    """BD1: a share of persons take a same-sex, same-band donor's 1998-2002."""
    out = frame.copy()
    early = _year_columns()[:3]
    band = _band_labels(frame)
    for _, index in frame.groupby([frame["sex"], band]).indices.items():
        chosen = index[rng.random(len(index)) < share]
        donors = rng.choice(index, size=len(chosen))
        out.iloc[chosen, [out.columns.get_loc(c) for c in early]] = frame.iloc[
            donors
        ][early].to_numpy()
    return out


def perturb_sex_blind(
    frame: pd.DataFrame, rng: np.random.Generator, *, same_sex: bool
) -> pd.DataFrame:
    """BD2 / BD2c: everyone takes a donor's 1998-2002 path.

    The donor shares the person's cohort band and 2004 class (no
    earnings, or the decile of 2004 earnings among the band's positive
    persons). BD2 draws donors from both sexes, as a generator that never
    sees sex would; BD2c restricts them to the person's own sex and is
    the control that isolates what pooling the sexes does.
    """
    out = frame.copy()
    early = _year_columns()[:3]
    last = frame[_year_columns()[3]].to_numpy()
    band = _band_labels(frame).to_numpy()
    klass = np.zeros(len(frame), dtype=int)
    for label in COHORT_BANDS:
        positive = (band == label) & (last > 0)
        if positive.sum() == 0:
            continue
        edges = np.quantile(last[positive], np.linspace(0.1, 0.9, 9))
        klass[positive] = 1 + np.searchsorted(
            edges, last[positive], side="right"
        )
    keys = [band, klass] + ([frame["sex"].to_numpy()] if same_sex else [])
    groups = pd.DataFrame({i: key for i, key in enumerate(keys)})
    for _, index in groups.groupby(list(groups.columns)).indices.items():
        donors = rng.choice(index, size=len(index))
        out.iloc[index, [out.columns.get_loc(c) for c in early]] = frame.iloc[
            donors
        ][early].to_numpy()
    return out


def perturb_top_tail(
    frame: pd.DataFrame, rng: np.random.Generator
) -> pd.DataFrame:
    """BD3: half of each early year's top 8 percent move down the ranks."""
    out = frame.copy()
    for column in _year_columns()[:3]:
        values = frame[column].to_numpy()
        positive = np.flatnonzero(values > 0)
        ordered = np.sort(values[positive])
        rank = np.searchsorted(ordered, values[positive], side="right") / len(
            ordered
        )
        move = (rank > BD3_RANK_ABOVE) & (
            rng.random(len(positive)) < BD3_MOVE_PROBABILITY
        )
        target = rng.uniform(*BD3_TARGET_RANKS, size=int(move.sum()))
        replacement = np.quantile(ordered, target, method="lower")
        column_values = values.copy()
        column_values[positive[move]] = replacement
        out[column] = column_values
    return out


def perturb_participation(
    frame: pd.DataFrame, rng: np.random.Generator
) -> pd.DataFrame:
    """BD4: each positive 1998-2002 person-year becomes zero at random."""
    out = frame.copy()
    for column in _year_columns()[:3]:
        values = frame[column].to_numpy().copy()
        drop = (values > 0) & (rng.random(len(values)) < BD4_ZERO_PROBABILITY)
        values[drop] = 0.0
        out[column] = values
    return out


def _band_labels(frame: pd.DataFrame) -> pd.Series:
    labels = pd.Series("", index=frame.index, dtype=object)
    for label, (low, high) in COHORT_BANDS.items():
        labels[frame["birth_year"].between(low, high)] = label
    return labels


def bite_demonstrations(
    frame: pd.DataFrame,
    universe: np.ndarray,
    registered: Mapping[str, Mapping[str, float]],
) -> dict[str, object]:
    """Score each perturbation on the 20 gate holdouts, 50 times."""
    position = np.searchsorted(universe, frame["person_id"].to_numpy())
    masks = {
        seed: holdout_mask(
            universe, seed=seed, fraction=gate.HOLDOUT_FRACTION
        )[position]
        for seed in gate.GATE_SEEDS
    }
    perturbations: dict[str, Callable] = {
        f"bd1_persistence_loss_{share:.2f}": (
            lambda f, r, share=share: perturb_persistence(f, r, share)
        )
        for share in BD1_SHARES
    }
    perturbations["bd2_sex_blind_donors"] = lambda f, r: perturb_sex_blind(
        f, r, same_sex=False
    )
    perturbations["bd2c_same_sex_donors_control"] = (
        lambda f, r: perturb_sex_blind(f, r, same_sex=True)
    )
    perturbations["bd3_top_tail_compression"] = perturb_top_tail
    perturbations["bd4_participation_loss"] = perturb_participation

    out: dict[str, object] = {}
    for index, (name, perturb) in enumerate(perturbations.items()):
        fails = 0
        cell_fails = {cell_id: 0 for cell_id in registered}
        for seed in BITE_SEEDS:
            rng = np.random.default_rng([BITE_SEED_BASE, index, seed])
            arrays = WindowArrays(perturb(frame, rng), wage_bases=wage_bases())
            per_seed = {
                s: _values(arrays.cells(mask)) for s, mask in masks.items()
            }
            scored = gate.score_run(per_seed, registered)
            fails += not scored["pass"]
            for cell_id, cell in scored["cells"].items():
                cell_fails[cell_id] += not cell["pass"]
        out[name] = {
            "fail_share": fails / len(BITE_SEEDS) if registered else None,
            "cell_fail_share": {
                cell_id: count / len(BITE_SEEDS)
                for cell_id, count in cell_fails.items()
            },
            "n_perturbation_seeds": len(BITE_SEEDS),
        }
    gated_families = {
        family
        for family, stats in gate.FAMILIES.items()
        if any(cell_id.split(".")[0] in stats for cell_id in registered)
    }
    requirements = {}
    for family in sorted(gated_families):
        name = BITE_REQUIREMENT[family]
        share = out[name]["fail_share"]
        requirements[family] = {
            "bite": name,
            "required_fail_share": BITE_REQUIRED_FAIL_SHARE,
            "fail_share": share,
            "met": share is not None and share >= BITE_REQUIRED_FAIL_SHARE,
        }
    out["requirements"] = requirements
    out["pause"] = any(not row["met"] for row in requirements.values())
    return _finite(out)


# --- artifact -------------------------------------------------------------


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def _file_sha256(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def design_block() -> dict[str, object]:
    return {
        "window_years": list(WINDOW_YEARS),
        "cohort_bands": {k: list(v) for k, v in COHORT_BANDS.items()},
        "gate_seeds": list(gate.GATE_SEEDS),
        "holdout_fraction": gate.HOLDOUT_FRACTION,
        "floor": {
            "n_replicates": gate.N_FLOOR_REPLICATES,
            "half_split_seed": "b",
            "holdout_split_seed": "1000 + 20 * b + j",
            "replicate": (
                "e_b = [m(A_b) - m(B_b)] / 2 + pooled(m(H_bj)) - "
                "pooled(m(T_bj)), j = 0..19"
            ),
        },
        "k": gate.K_TOLERANCE,
        "tolerance": "round(mean|e_b| + k * sd|e_b| (ddof=1), 3)",
        "interval": "[min(0, bridge) - t, max(0, bridge) + t]",
        "eligibility": "abs(bridge) + t + 0.8416 * sigma <= cap",
        "caps": gate.CAPS,
        "min_events": gate.MIN_EVENTS,
        "epuf_noise_share_max": gate.EPUF_NOISE_SHARE_MAX,
        "oc_pause_below": gate.OC_PAUSE,
        "support": {
            "universe": (
                "gate 1's filtered PSID family panel: age 25-59, reference "
                "years 1998-2022, positive weight"
            ),
            "rules": [
                "a row at each of 1998, 2000, 2002 and 2004",
                "last in-filter period 2006 or later",
                "sex coded male or female (ER32000)",
                "birth year floor(median(period - age) + 0.5) in 1947-1973",
            ],
            "weight": "the person's 2004-row weight",
            "epuf": (
                "every EPUF person with sex 1 or 2 born 1947-1973, weight 1"
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--stage",
        choices=("epuf", "full"),
        default="full",
        help="'epuf' computes and prints the EPUF side only and writes nothing",
    )
    args = parser.parse_args()
    started = time.time()

    def say(message: str) -> None:
        print(f"[{time.time() - started:6.1f}s] {message}", flush=True)

    demographic = epuf.read_demographic()
    annual = epuf.read_annual()
    say("EPUF read")
    epuf_arrays, epuf_counts = epuf_window(demographic, annual)
    epuf_cells = epuf_arrays.cells()
    epuf_values = _values(epuf_cells)
    epuf_sd = epuf_sampling_sd(epuf_arrays)
    say(f"EPUF window: {len(epuf_arrays):,} persons")
    if args.stage == "epuf":
        print(json.dumps(epuf_values, indent=1))
        return

    careers = career_reference(demographic, annual)
    del demographic, annual
    say("EPUF career reference done")
    frame, universe, psid_counts = psid_support()
    arrays = WindowArrays(frame, wage_bases=wage_bases())
    say(f"PSID support: {len(arrays):,} persons")

    from populace_dynamics.harness.panel import split_panel_by_person

    gate1 = json.loads((ROOT / GATE1_RUN).read_text())
    committed_holdouts = {
        int(row["seed"]): int(row["n_persons"]) for row in gate1["per_seed"]
    }
    ids_frame = pd.DataFrame({"person_id": universe})
    holdout_ids = {}
    for seed in gate.GATE_SEEDS:
        drawn = holdout_mask(
            universe, seed=seed, fraction=gate.HOLDOUT_FRACTION
        )
        left, _ = split_panel_by_person(
            ids_frame, "person_id", fraction=gate.HOLDOUT_FRACTION, seed=seed
        )
        if set(left["person_id"]) != set(universe[drawn]):
            raise AssertionError(f"seed {seed}: not the gate-1 split")
        if seed in committed_holdouts and (
            int(drawn.sum()) != committed_holdouts[seed]
        ):
            raise AssertionError(
                f"seed {seed}: {int(drawn.sum())} holdout persons, "
                f"{GATE1_RUN} has {committed_holdouts[seed]}"
            )
        holdout_ids[str(seed)] = {
            "n_persons": int(drawn.sum()),
            "n_support_persons": int(
                np.isin(arrays.person_id, universe[drawn]).sum()
            ),
            "sha256_sorted_person_ids": _sha256_ids(universe[drawn]),
        }

    built = build_floors(arrays, universe, epuf_values, epuf_sd, progress=say)
    bites = bite_demonstrations(frame, universe, built["registered"])
    say("bite demonstrations done")

    payload = {
        "schema_version": SCHEMA_VERSION,
        "run": "epuf_gate_floors_v1",
        "status": "DRAFT_NOT_OPERATIVE",
        "purpose": (
            "Pre-lock floors, bridges, partition and operating "
            "characteristic of the proposed EPUF covered-earnings gate "
            "(docs/amendments/gate_epuf_registration_proposal.md). No "
            "candidate was generated or scored to build it."
        ),
        "ceremony": {
            "step": "pre-lock floor",
            "draft_block": "docs/design/gate_epuf_block_draft.yaml",
            "gates_yaml_untouched": True,
        },
        "candidate_blind": {
            "generated_candidates": 0,
            "psid_read_through": [
                "populace_dynamics.data.family.family_earnings_panel",
                "populace_dynamics.data.deaths.read_death_records",
            ],
        },
        "design": design_block(),
        "inputs": {
            "epuf_sha256": dict(epuf.EPUF_SHA256),
            "disclosure_constants_sha256": CONSTANTS_SHA256,
            "psid_panel": {**psid_counts, "reference": PANEL_REFERENCE},
            "gate1_run": GATE1_RUN,
        },
        "epuf_support": epuf_counts,
        "holdout_ids": holdout_ids,
        **built,
        "bite_demonstrations": bites,
        "ceremony_pause": bool(
            built["faithful_candidate_oc"]["pause"] or bites["pause"]
        ),
        "tranche_r_epuf_reference": {
            "note": (
                "EPUF only. Report-only career tranche: the original four "
                "career statistics on true EPUF careers and on EPUF careers "
                "masked as the career assembler builds a PSID career "
                "(nothing before 1968; odd years from 1997 filled with the "
                "neighbour mean). The PSID side is computed once, after "
                "lock."
            ),
            "ages": list(CAREER_AGES),
            "cells": careers,
        },
        "concept_deltas": CONCEPT_DELTAS,
        "revision_pins": {
            "head_sha": _git("rev-parse", "HEAD"),
            "origin_master_sha": _git("rev-parse", "origin/master"),
            "derivation_core_sha256": {
                path: _file_sha256(path) for path in DERIVATION_CORE
            },
        },
        "elapsed_seconds": round(time.time() - started, 1),
    }
    write_new(ARTIFACT, payload, sidecar=True)
    INPUTS.write_text(
        json.dumps(
            {
                "artifact": ARTIFACT.name,
                "status": "SOURCE_INPUT_DIGESTS",
                "official_source": {
                    "url": (
                        "https://www.ssa.gov/policy/docs/microdata/epuf/"
                        "epuf2006_csv_files.zip"
                    ),
                    "archive_sha256": (
                        "0bb97275cc35a1bb42d34d26acbc9df720d4f875854ba1d02c"
                        "50323d2357003b"
                    ),
                    "archive_bytes": 291602034,
                    "archive_members": [
                        epuf.DEMOGRAPHIC_FILE,
                        epuf.ANNUAL_FILE,
                    ],
                    "retrieved": "2026-10-01",
                    "provenance": "data/external/epuf_2006/provenance.md",
                },
                "staged_inputs": [
                    {"path": name, "sha256": digest}
                    for name, digest in epuf.EPUF_SHA256.items()
                ],
            },
            indent=2,
        )
        + "\n"
    )
    say(f"wrote {ARTIFACT.relative_to(ROOT)}")
    print(json.dumps(built["gate_partition"], indent=1))


if __name__ == "__main__":
    main()
